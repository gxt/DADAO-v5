@@ mode_entry.S — cfx0/cfx2/cfx3 运行模式进入路由 RTL 探针（`m16-chipyard-020`）
@@
@@ 目的：在 **Kaiwu-Vast RTL（chipyard `WumingVastConfig`）** 上验证 `DADAO-12
@@ §5.2/§5.3` 的运行模式进入主控制流：
@@   * 同步异常 / 异步中断的入口目标 = 异常前运行模式的 monitor
@@     （U→cfx0 umon、S→cfx2 smon、H→cfx3 hmon）；
@@   * 第 6 步 `inner_run_mode` 取**目标 cfx** 的 `<mode>_switch_run_mode`；
@@   * 异常帧 `excp_prev_run_mode / excp_prev_cfx_code / excp_cause_id /
@@     excp_cause_ip / excp_cause_info` 的保存，`escape` 的恢复；
@@   * `trap cfxHA` 的“目标 cfx”组合（U 下 trap 到 smon、H 下 trap 到 umon）；
@@   * U/S 下 `cfx2rd` 的两轴判权：目标 cfx 的 `<mode>_cfxreg` 源掩码 +
@@     `cg3 rc12` `cg_reg_deleg`，拒绝 ⇒ `CFXPERM`（扁平位图、无 `[39]`）；
@@ 异步中断**不在本探针**：`ADR-0061` 后异步统一投 `cfx_hart`（源位图 = 源
@@ cfxha、掩码在当前运行模式 monitor 的 `cg8 rc1`），由 `tests/arch/hart/cfx15.S`
@@ 按 H/S/U 三模式覆盖；本探针只保留同步进入/退出与两轴判权。
@@
@@ **一份 case、三种运行模式**：本文件是唯一载体，链接期用 `--defsym TMODE=`
@@ 选择目标模式（0 = umon/U、2 = smon/S、3 = hmon/H），同一份期望表见
@@ `check_mode_entry.py`。运行方式见运行期证据脚本。
@@
@@ 入口约定：chipyard 的固定 BootROM（`spec/Kaiwu §6.2`）以 `cfx_power` 在 hypv
@@ 直接跳到 `ENTRY`，所以本探针在 `_start` 正是 “cfx_power + hypv”。它按 TMODE
@@ 写目标 cfx 的 hypv 行（`switch_run_mode` / `excp_vector`），再 `trap` 进目标
@@ cfx —— 这就是 §5.2 第 1/6/7 步的“合法且被允许 → CFXTRAP, 目标 cfxha”路径。
@@ H 模式用 `trap cfx_hmon` 让测试体在 `cfx_hmon + hypv` 跑。
@@
@@ 不变量（判据侧同样使用）：
@@   * 每一处同步异常的 `excp_cause_ip` 都记为**完整 64 位地址**，期望值
@@     由 ELF 符号表（`llvm-nm`）给出，不从注入后的镜像反推；
@@   * `cause_id` 记**完整 64 位**（`ADR-0062` 扁平位图），期望由
@@     `spec/DADAO-12` + `.tao/contracts/contract-see.md §6.1.1` 现场派生；
@@   * 签名槽顺序固定（见 checker 的 SLOTS）；任何“本该发生却没有发生”的路径都会
@@     多记一个 FAIL 槽并以非零退出码结束（`0xE1` 无异常 / `0xE2` 误入 hmon /
@@     `0xE3` switch 未生效）。
@@
@@ 寄存器约定：探针体用 rd5–rd8、rb1–rb3；处理器用 rd20–rd23、rb20–rb21；
@@ rb30 = 签名写指针（任何处理器都不得写）；rd4/rd16/rb16 = SYS_EXIT。
@@ **只在 `WumingVastConfig` 上跑**（Tiny 不实现 cfx0/cfx2，且无 U/S 模式）。

	.include "tests/shared/asm/signature.inc"
	.include "tests/shared/asm/perm_hypv.inc"

	.equ	ENTRY,   0xffffff002000
	.equ	SIG_BUF, 0xffffff001000
	.equ	SIG_N,   32
	.equ	EXITB,   0xffffff000030

@@ ---------------------------------------------------------------------------
@@ 文件专用宏
@@ ---------------------------------------------------------------------------
.macro REC reg
	st.o	\reg, [rb30, 0]
	add.si	rb30, 8
.endm

.macro EXIT code
	set.rb	rb16, EXITB
	set.rd	rd4, 0x20026
	st.o	rd4, [rb16, 0]
	set.rd	rd4, \code
	st.o	rd4, [rb16, 8]
	set.zw	rd16, wp0, 0x18
	trap	cfx0, 0x3FF18
	swym	0
.endm

.macro DUMP_AND_EXIT code
	@@ 精确按 sig_bytes 输出（三个模式的槽数不同；缓冲区预填 0xdeadbeef 不算槽）
	set.rb	rb1, sig_bytes
	ld.o	rd17, [rb1, 0]
	set.rb	rb16, SIG_BUF
	set.zw	rd16, wp0, 0x03
__dump_\@:
	trap	cfx0, 0x3FF03
	add.si	rb16, 1
	add.si	rd17, -1
	br.nz	{rd17}?, [rb0, __dump_\@]
	EXIT	\code
.endm

@@ 写 cfx 寄存器（立即数 / 标签地址）
.macro WCFX_IMM ha, cg, rc, imm
	set.rd	rd6, \imm
	cfx2rc	\ha, \cg, \rc, rd6
.endm
.macro WCFX_LABEL ha, cg, rc, lab
	set.rb	rb2, \lab
	rb2rd	rd6, rb2, 1
	cfx2rc	\ha, \cg, \rc, rd6
.endm
@@ `exp_ip` / `phase` 数据槽（探针私有，见 .data）
.macro SET_EXP lab
	set.rb	rb2, \lab
	rb2rd	rd6, rb2, 1
	set.rb	rb1, exp_ip
	st.o	rd6, [rb1, 0]
.endm
.macro SET_PHASE imm
	set.rb	rb1, phase
	set.rd	rd6, \imm
	st.o	rd6, [rb1, 0]
.endm
@@ 改写当前 cfx 帧的 `excp_cause_ip`（cg5 rc3，RW）为恢复点，再 escape 0
.macro SET_CAUSEIP ha, lab
	set.rb	rb2, \lab
	rb2rd	rd20, rb2, 1
	cfx2rc	\ha, cg5, rc3, rd20
.endm

@@ 异常落点统一收尾：记一个 FAIL 槽 + 非零退出
.macro FAIL code, marker
	set.rd	rd20, \marker
	REC	rd20
	DUMP_AND_EXIT \code
.endm

@@ ---------------------------------------------------------------------------
@@ 入口：cfx_power + hypv（BootROM 固定跳转）⇒ 按 TMODE 选 setup
@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	SIG_BEGIN SIG_BUF, SIG_N
	set.rb	rb1, mode_word
	ld.o	rd6, [rb1, 0]
	set.rd	rd7, 0
	br.eq	{rd6, rd7}?, [rb0, setup_u]
	set.rd	rd7, 2
	br.eq	{rd6, rd7}?, [rb0, setup_s]
	jump	[rb0, setup_h]

@@ ---------------------------------------------------------------------------
@@ U 模式 setup：进 cfx_umon(user)，并给 U 体备好 smon 的 U 行
@@ ---------------------------------------------------------------------------
setup_u:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 112			@@ 14 槽（异步段移出后）
	st.o	rd6, [rb1, 0]
	@@ 误入 hmon 的检出器（若 U 异常被错误路由到 hmon，本向量会命中）
	WCFX_LABEL cfx_hmon, cg3, rc10, wrong_monitor
	@@ cfx_umon：hypv 行向量 + 切换值 = 0（user）；user 行向量/处理器运行模式
	WCFX_LABEL cfx_umon, cg3, rc10, u_entry
	WCFX_IMM   cfx_umon, cg3, rc8,  0
	WCFX_LABEL cfx_umon, cg0, rc10, u_fault
	WCFX_IMM   cfx_umon, cg0, rc8,  3
	@@ cfx_smon：允许源 cfx_umon(0) 的 trap / cfx2 访问（清 user 行 bit0）
	cfx2rd	cfx_smon, cg0, rc0, rd6
	set.rd	rd7, 0xFFFFFFFFFFFFFFFE
	and.o	rd6, rd6, rd7
	cfx2rc	cfx_smon, cg0, rc0, rd6
	cfx2rd	cfx_smon, cg0, rc2, rd6
	and.o	rd6, rd6, rd7
	cfx2rc	cfx_smon, cg0, rc2, rd6
	@@ U 下 trap 到 smon：user 行向量 + 切换值 = 2（supv）；deleg 放开 cg4/cg5
	WCFX_LABEL cfx_smon, cg0, rc10, s_from_u
	WCFX_IMM   cfx_smon, cg0, rc8,  2
	WCFX_IMM   cfx_smon, cg3, rc12, 8
	trap	cfx_umon, 0
	swym	0

@@ ---------------------------------------------------------------------------
@@ S 模式 setup：进 cfx_smon(supv)
@@ ---------------------------------------------------------------------------
setup_s:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 56			@@ 7 槽（异步段移出后）
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_hmon, cg3, rc10, wrong_monitor
	WCFX_LABEL cfx_smon, cg3, rc10, s_entry
	WCFX_IMM   cfx_smon, cg3, rc8,  2
	WCFX_LABEL cfx_smon, cg2, rc10, s_fault
	WCFX_IMM   cfx_smon, cg2, rc8,  2
	@@ S 访问自身 cg4/cg5：deleg 只留恒 1 的 bit3（cg3 在 S 恒 CFXPERM）
	WCFX_IMM   cfx_smon, cg3, rc12, 8
	trap	cfx_smon, 0
	swym	0

@@ ---------------------------------------------------------------------------
@@ H 模式 setup：进 cfx_hmon(hypv)
@@ ---------------------------------------------------------------------------
setup_h:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 112			@@ 14 槽
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_hmon, cg3, rc10, h_entry
	WCFX_IMM   cfx_hmon, cg3, rc8,  3
	@@ H 下 trap 到 cfx_umon：hypv 行向量 + 切换值 = 3
	WCFX_LABEL cfx_umon, cg3, rc10, trap_umon_h
	WCFX_IMM   cfx_umon, cg3, rc8,  3
	SET_PHASE 0
	trap	cfx_hmon, 0
	swym	0

@@ ---------------------------------------------------------------------------
@@ H 测试体（cfx_hmon + hypv）：h_entry 同时是异常向量，用 phase 区分
@@ ---------------------------------------------------------------------------
h_entry:
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	set.rd	rd6, 0xFFFF
	and.o	rd5, rd5, rd6
	set.rd	rd6, 1
	br.ne	{rd5, rd6}?, [rb0, h_fault]
	set.rb	rb1, phase
	ld.o	rd5, [rb1, 0]
	br.nz	{rd5}?, [rb0, h_fault]
	set.rd	rd5, 1
	st.o	rd5, [rb1, 0]
	@@ 槽 0：hypv 行 switch_run_mode 复位/读值 = 3
	cfx2rd	cfx_hmon, cg3, rc8, rd5
	REC	rd5
	@@ 槽 1：写 0 被忽略（Tiny/legacy 语义不变），仍读 3
	set.rd	rd6, 0
	cfx2rc	cfx_hmon, cg3, rc8, rd6
	cfx2rd	cfx_hmon, cg3, rc8, rd5
	REC	rd5
	@@ 槽 2/3：H 下访问 cfx0/cfx2 抽头（hypv 行不判权，见任务书口径）
	cfx2rd	cfx_umon, cg4, rc0, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg4, rc0, rd5
	REC	rd5
	@@ trap cfx_umon（目标 cfx 组合 + 帧 + escape 回 H 体）
	SET_EXP h_f_trap
h_f_trap:
	trap	cfx_umon, 0
	jump	[rb0, fail_no_fault]
h_resume_trap:
	@@ ILLI（保留 cfxha ⇒ 译码期 ILLI）：H 模式同步异常 → cfx3
	SET_EXP h_f_bad
h_f_bad:
	.dd.t32	0x7F180000
	jump	[rb0, fail_no_fault]
h_resume_bad:
	jump	[rb0, done_ok]

h_fault:
	@@ 只在测试体运行后（phase = 1）预期；setup 期异常 ⇒ 误判路径
	set.rb	rb1, phase
	ld.o	rd6, [rb1, 0]
	br.z	{rd6}?, [rb0, wrong_monitor]
	cfx2rd	cfx_hmon, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	REC	rd5
	SET_CAUSEIP cfx_hmon, h_resume_bad
	escape	cfx_hmon, [excp_cause_ip, 0]
	swym	0

@@ H 下 trap cfx_umon 的处理器（以 cfx_umon 在 hypv 运行）
trap_umon_h:
	cfx2rd	cfx_umon, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc1, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc3, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc4, rd5
	REC	rd5
	SET_CAUSEIP cfx_umon, h_resume_trap
	escape	cfx_umon, [excp_cause_ip, 0]
	swym	0

@@ ---------------------------------------------------------------------------
@@ U 测试体（cfx_umon + user）
@@ ---------------------------------------------------------------------------
u_entry:
	@@ 槽 0–3：U 下的同步异常 → cfx_umon 的 user 行；cg3 在 U ⇒ CFXREG
	SET_EXP u_f_cg3
	SET_PHASE 0
u_f_cg3:
	cfx2rd	cfx_umon, cg3, rc0, rd5
	jump	[rb0, fail_switch]
u_resume_cg3:
	@@ 槽 4：自身寄存器（self 绕 cfx 轴）
	cfx2rd	cfx_umon, cg4, rc0, rd5
	REC	rd5
	@@ 槽 5：U 行已开放 ⇒ 访问 cfx_smon 合法
	cfx2rd	cfx_smon, cg4, rc0, rd5
	REC	rd5
	@@ 槽 6–9：目标 cfx 无 U 行 / 未开放 ⇒ CFXPERM（只有 1<<7）
	SET_EXP u_f_cfx5
	SET_PHASE 1
u_f_cfx5:
	cfx2rd	cfx5, cg8, rc0, rd5
	jump	[rb0, fail_no_fault]
u_resume_cfx5:
	@@ U 下 trap 到 cfx_smon：目标 cfx + switch=2 + 帧
	SET_EXP u_f_trap
u_f_trap:
	trap	cfx_smon, 0
	jump	[rb0, fail_no_fault]

@@ U 的异常处理器（cfx_umon，runMode 由 user 行 switch = hypv）
u_fault:
	set.rb	rb1, phase
	ld.o	rd6, [rb1, 0]
	br.z	{rd6}?, [rb0, u_fault_phase0]
	jump	[rb0, u_fault_phase1]

u_fault_phase0:
	cfx2rd	cfx_umon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc1, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc3, rd5
	REC	rd5
	SET_CAUSEIP cfx_umon, u_resume_cg3
	escape	cfx_umon, [excp_cause_ip, 0]
	swym	0

u_fault_phase1:
	cfx2rd	cfx_umon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_umon, cg5, rc3, rd5
	REC	rd5
	SET_CAUSEIP cfx_umon, u_resume_cfx5
	escape	cfx_umon, [excp_cause_ip, 0]
	swym	0

@@ U 下 trap 到 smon 的处理器（cfx_smon + supv）
s_from_u:
	cfx2rd	cfx_smon, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc1, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc3, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc4, rd5
	REC	rd5
	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
@@ S 测试体（cfx_smon + supv）
@@ ---------------------------------------------------------------------------
s_entry:
	@@ 槽 0：self + deleg（bit4 = 0）⇒ 可访问自身 cg4
	cfx2rd	cfx_smon, cg4, rc0, rd5
	REC	rd5
	@@ 槽 1–3：S 下访问 cfx_umon 被其 supv_cfxreg 拒绝 ⇒ CFXPERM
	SET_EXP s_f_umon
	SET_PHASE 1
s_f_umon:
	cfx2rd	cfx_umon, cg4, rc0, rd5
	jump	[rb0, fail_no_fault]
s_resume_umon:
	@@ 槽 4–6：S 访问自身 cg3 被 deleg bit3 恒 1 拒绝（同时证明 runMode = 2）
	SET_EXP s_f_cg3
	SET_PHASE 2
s_f_cg3:
	cfx2rd	cfx_smon, cg3, rc0, rd5
	jump	[rb0, fail_switch]

s_fault:
	set.rb	rb1, phase
	ld.o	rd6, [rb1, 0]
	set.rd	rd7, 1
	br.eq	{rd6, rd7}?, [rb0, s_fault_perm]
	jump	[rb0, s_fault_mode]

s_fault_perm:
	cfx2rd	cfx_smon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc3, rd5
	REC	rd5
	SET_CAUSEIP cfx_smon, s_resume_umon
	escape	cfx_smon, [excp_cause_ip, 0]
	swym	0

	@@ 最后一个探针：运行模式证明（prev_mode = 2），记录后正常退出
s_fault_mode:
	cfx2rd	cfx_smon, cg5, rc2, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc0, rd5
	REC	rd5
	cfx2rd	cfx_smon, cg5, rc3, rd5
	REC	rd5
	jump	[rb0, done_ok]

@@ ---------------------------------------------------------------------------
@@ 共享收尾：正常退出 / 三类 fail-closed
@@ ---------------------------------------------------------------------------
done_ok:
	DUMP_AND_EXIT 0

fail_no_fault:
	FAIL	0xE1, 0xFA110001

wrong_monitor:
	FAIL	0xE2, 0xBAD00000

fail_switch:
	FAIL	0xE3, 0xE3E3E3E3

@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.balign 4
perm_mon:
	PERM_OPEN_DELEG	cfx_hart
	PERM_OPEN_DELEG	cfx_smon
	PERM_OPEN_DELEG	cfx_umon
	PERM_MON_CLOSE

@@ ---------------------------------------------------------------------------
@@ 私有数据槽（随镜像装入；运行期可写）
@@ ---------------------------------------------------------------------------
	.data
	.p2align 3
mode_word:
	.dd.o64	TMODE
	.p2align 3
exp_ip:
	.dd.o64	0
	.p2align 3
phase:
	.dd.o64	0
	.p2align 3
sig_bytes:
	.dd.o64	0
