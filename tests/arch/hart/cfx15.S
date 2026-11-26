@@ cfx15.S — `cfx_hart`（cfxha 15）RTL 探针（`m16-chipyard-021` 起，`m18-testcases-004` 改到 R3，
@@ `m18-testcases-005` 改到 `DADAO-12` 0.8.1-rc / `ADR-0064`）
@@
@@ 目的：在 **Kaiwu-Vast RTL（chipyard `WumingVastConfig`）** 上验证
@@ `spec/DADAO-12 §3.6/§4.7/§5.4` 的 cfx_hart（**`cg15` 入口记录/捕获缓冲；`cg5 rc8`–`rc11` 出口意图**）：
@@   * cg8 管理寄存器：hart_id / cycle / insn（timer 已迁到 `cg16`）；
@@   * `cfx_hart cg16` 中断面：rc0 timer_ctrl（仅 bit0 ENABLE）/ rc1 timer_cmp /
@@     rc16 mask / rc17 pending（RO）/ rc18 ack（W1C）；
@@   * `cg15` **捕获缓冲**：rc0 prev_run_mode / rc1 prev_cfx_code / rc2 cause_ip /
@@     rc3 prev_intr_mask / rc4 src_frame（HW/RO，位 = 源 cfxha）/
@@     rc5 src_pending 汇总（HW/RO）/
@@     rc14 switch_run_mode（RW、复位 2 = supv） / rc15 excp_vector（RW）；
@@     rc6–rc13 reserved（访问 ⇒ CFXREG）；`cg9` 归 reserved；
@@   * 位图**软件写忽略、读回不变、不产生异常**（不报 CFXREG）；
@@   * 来源掩码在**当前运行模式 monitor** 的 `cg15 rc3`（bit15 = 源 cfxha 15，
@@     0 = 允许 / 1 = 屏蔽）：屏蔽期源只置 pending（`cg16 rc17` / 汇总 `cg15 rc5`），
@@     解除后异步进入；
@@   * 异步进入：一帧多源（本机只有一个源）→ `src_frame` = 位 15、
@@     `excp_async_num` +1；**进入不清 pending**；
@@   * **覆盖语义**：第一次进入后不搬走现场，再次到期 ⇒ 同一指令边界整体覆盖
@@     `cg15`（`prev_*`/`cause_ip`/`src_frame`），**不是**只置 pending；
@@   * 源 ack（`cg16 rc18` W1C）后 pending 落；handler 在 `escape` 前 ack；
@@   * `escape cfxHA`：`imms18` 必须为 0（SBZ，非 0 ⇒ ILLI）；正常异步返回按
@@     `cg5 rc8`–`rc11` 恢复模式/cfx/ip 并整字写目标 monitor 的 `cg15 rc3`；
@@     升权 / 目标未实现 / `cfxha` 不符 ⇒ 当前 cfx 的 `CFXESC`；
@@   * **精确点**：在 `jump` 目标处到期时 `cause_ip` = 目标（SimRISC-06 的
@@     `jump`，不是 RISC-V `jal`）；实现用「从 0 起逐步加 1 个 cycle」的有界
@@     搜索命中目标边界（各平台的读周期延迟不同，不能写死补偿）；
@@   * H/S/U 三模式下掩码都取**当前运行模式** monitor 的那一行（`--defsym
@@     TMODE=3/2/0`），投递目标都是 cfx_hart/supv。`PTW_UMAP`（仅 QEMU
@@     承载）在 U 模式下把镜像所在 512 MiB 超页的 PTE 置 U=1。
@@
@@ **一份 case、三种运行模式**：本文件是唯一载体，汇编期用 `-defsym TMODE=`
@@ 选择目标运行模式（0 = umon/U、2 = smon/S、3 = hmon/H）；H 模式额外做寄存器面
@@ 与非法编码探针。期望值见 `check_cfx15.py`（现场从 `spec/DADAO-12` §1/§3.6/§4.7/
@@ §5.1/§5.4、`.tao/adr/adr-0061-*.md`、`contract-see` §3/§6.1 与
@@ `contracts/opcodes.yaml` 派生）。
@@
@@ 入口约定：chipyard 固定 BootROM（`spec/Kaiwu §6.2`）以 cfx_power 在 hypv 跳到
@@ `ENTRY`。H 模式先 `trap cfx_hmon` 进入 hmon/hypv；U/S 模式按 `§5.2` 用
@@ `trap cfx_umon` / `trap cfx_smon` + 目标 cfx 的 hypv 行向量/切换值进入。
@@
@@ 不变量：
@@   * 签名槽顺序固定（见 checker 的 expected），漏跑/多跑都判红；
@@   * `cause_ip` 用 ELF 符号**精确**断言（投递发生在“下一条指令的边界”，该指令
@@     未执行 ⇒ 其地址就是 `cause_ip`）；
@@   * 两个位图的期望值全由源 cfxha 派生（TIMER = cfx_hart = 15 ⇒ `1 << 15`）；
@@   * 期望值不从 RTL 观测值反推；探针只 `REC` 实测值。
@@
@@ 寄存器约定：探针体用 rd5–rd7、rb1–rb3、rb5；handler 用 rd5/rd21/rd22/rd23、
@@ rb3/rb4；rb30 = 签名写指针（任何处理器都不得写）；rd16/rb16 = semihosting；
@@ rb20 = hmon SRAM 基址（仅 H 的寄存器面探针使用）。
@@ **只在 `WumingVastConfig` 上跑**（Tiny 无 cfx15、无 U/S 模式）。

	.include "tests/shared/asm/signature.inc"
	.include "tests/shared/asm/perm_hypv.inc"

	.ifndef	ENTRY
	.equ	ENTRY,   0xffffff010100
	.endif
	.ifndef	SIG_BUF
	.equ	SIG_BUF, 0xffffff015000
	.endif
	.equ	SIG_N,   96
	.ifndef	EXITB
	.equ	EXITB,   0xffffff015800
	.endif
	.ifndef	HMON_BASE
	.equ	HMON_BASE, 0xffffff018000
	.endif

	.ifndef	TMODE
	.equ	TMODE, 3
	.endif

	@@ 每个镜像的签名槽数（与 checker 的 `expected()` 一一对应）
	.if TMODE == 3
	.equ	SIG_SLOTS, 124
	.else
	.equ	SIG_SLOTS, 38
	.endif

	@@ `DADAO-12 §5.1`（R3）：escape 的 `imms18` 是 SBZ，必须为 0；非 0 ⇒ ILLI。
	@@ 汇编器拒绝非 0 写法，故用原始编码字直接喂给核（3/4 两档）。
	.equ	ESC_HART_IMM3, (0x7E000000 | (15 << 18) | 3)
	.equ	ESC_HART_IMM4, (0x7E000000 | (15 << 18) | 4)

	.equ	PATTERN64, 0x123456789ABCDEF0
.equ	ESC_BAD_MASK, 0xFFFF000000000000	@@ 非法 escape 不得落地到 monitor
.equ	ESC_RC11_PATTERN, 0x0123456789ABCDEF	@@ 正常异步返回写 rc11 的整字反例（bit15=1 ⇒ 屏蔽 TIMER）
	.equ	TIMER_SRC_BIT, 0x0000000000008000	@@ 1 << 15（源 cfxha = 15）
	.equ	MASK_PATTERN,  0xFFFFFFFFFFFF7FFF	@@ bit15 = 0（允许 TIMER）

@@ ---------------------------------------------------------------------------
@@ 文件专用宏
@@ ---------------------------------------------------------------------------
.macro REC reg
	st.o	\reg, [rb30, 0]
	add.si	rb30, 8
.endm

.macro WCFX_IMM ha, cg, rc, imm
	set.rd	rd6, \imm
	cfx2rc	\ha, \cg, \rc, rd6
.endm
.macro WCFX_LABEL ha, cg, rc, lab
	set.rb	rb2, \lab
	rb2rd	rd6, rb2, 1
	cfx2rc	\ha, \cg, \rc, rd6
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

@@ 计时等待：约 300 条指令（每迭代 3 条），覆盖 timer deadline。
.macro BURN rd, rb
	set.rd	\rd, 300
__burn_\@:
	add.si	\rb, 1
	add.si	\rd, -1
	br.nz	{\rd}?, [rb0, __burn_\@]
.endm

.macro BURN_SHORT rd, rb
	set.rd	\rd, 40
__spin_\@:
	add.si	\rb, 1
	add.si	\rd, -1
	br.nz	{\rd}?, [rb0, __spin_\@]
.endm

@@ ---------------------------------------------------------------------------
@@ 入口：cfx_power + hypv
@@ ---------------------------------------------------------------------------
	.text
	.globl	_start
_start:
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	@@ 启动链的 PMEM DMA 完成事件在新模型下留下 cg16 pending bit0；先 ack，
	@@ 否则 cg15 rc5 汇总会一直带 bit32（源 mask/ack 归源，进入不清）。
	WCFX_IMM   cfx_pmem, cg16, rc18, 1
	SIG_BEGIN SIG_BUF, SIG_N
	@@ 清 `hphase`（hmon 入口分派用）与 `phase`（async handler 分派用）
	set.rb	rb1, hphase
	set.rd	rd6, 0
	st.o	rd6, [rb1, 0]
	set.rb	rb1, phase
	st.o	rd6, [rb1, 0]
	@@ rd20 = 跳转精确点模式（0 = 捕获流程；1 = jump 目标到期搜索）
	set.rd	rd20, 0

	@@ ---- 共用初始化：cfx_hart 的异步入口 / 三行来源掩码 / 两轴放行 ----
	WCFX_LABEL cfx_hart, cg15, rc15, async_entry	@@ async_excp_vector
	@@ CFXESC 交当前 cfx（cfx_hart）；supv 行向量（cg2 rc15）指向 esc9_entry。
	WCFX_LABEL cfx_hart, cg2, rc15, esc9_entry
	@@ umon/smon 的 `cg15 rc3` 先放开源 cfxha 15（bit15 = 0）——U/S 体与 supv
	@@ handler 里的覆盖/屏蔽测试都靠这两行；hmon 行留到 H 体里先验复位值再改写。
	WCFX_IMM   cfx_umon, cg15, rc3, MASK_PATTERN
	WCFX_IMM   cfx_smon, cg15, rc3, MASK_PATTERN
	@@ supv handler 要写 cfx_smon 的 `cg15 rc3`（临时屏蔽当前模式）：放开源位 15
	@@ 在 cfx_smon 的 supv `cfxreg` 行（cg2 rc2），并在它自己的 `cg3 rc12`
	@@ deleg 里放开 cg15（supv 访问非当前 cfx 还受目标 cfx 的 deleg 约束）。
	WCFX_IMM   cfx_smon, cg2, rc2, MASK_PATTERN
	WCFX_IMM   cfx_smon, cg3, rc12, 0xFFFFFFFFFFFE7CF7
	@@ 兜底：supv 下的意外同步异常进 cfx_smon，落 smon_fault 快速失败
	WCFX_LABEL cfx_smon, cg3, rc15, smon_fault
	@@ timer 关：cmp 全 1、ctrl 0；源 mask 放开（本探针自己决定何时产生事件）
	WCFX_IMM   cfx_hart, cg16, rc1, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg16, rc0, 0
	WCFX_IMM   cfx_hart, cg16, rc16, 0
	@@ 两轴放行：目标 cfx（cfx_hart）的 user/jail/supv cfxreg 源位清 0
	WCFX_IMM   cfx_hart, cg0, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM   cfx_hart, cg1, rc2, 0xFFFFFFFFFFFFFFF8
	WCFX_IMM   cfx_hart, cg2, rc2, 0xFFFFFFFFFFFFFFF8
	@@ cg3 rc12 delegation：放开 cg4/cg5/cg15/cg16（bit3 硬件恒 1）
	WCFX_IMM   cfx_hart, cg3, rc12, 0xFFFFFFFFFFFE7CC7

	.if TMODE == 0 || TMODE == 3
	.ifdef	PTW_UMAP
	@@ QEMU step5 页表在 PA 0；镜像所在的 512 MiB 超页置 HSJU=0xF（U=1）
	@@ H 体尾段要进 user（`cg15 rc14=0`）取指/写签名，与 U 模式体同一份约定。
	set.rd	rd6, 0xF00000000000FFEF
	set.rb	rb2, 0
	st.o	rd6, [rb2, 0]
	set.rd	rd6, 2				@@ tlb_control = invalid all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.endif
	.endif
	.if TMODE == 3
	jump	[rb0, setup_h]
	.elseif TMODE == 2
	jump	[rb0, setup_s]
	.else
	jump	[rb0, setup_u]
	.endif

@@ ---------------------------------------------------------------------------
@@ H（hmon + hypv）：先进入 cfx_hmon，再在 h_entry 里跑寄存器面 + timer
@@ ---------------------------------------------------------------------------
setup_h:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 124*8			@@ H 模式检查点数（见 check_cfx15.expected）
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_hmon, cg3, rc15, h_entry
	WCFX_IMM   cfx_hmon, cg3, rc14, 3
h_trap:
	trap	cfx_hmon, 0
	swym	0

h_entry:
	@@ 同步异常（CFXTRAP 以外的 cause）走 h_fault；初次 trap 的低位是 CFXTRAP
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	set.rd	rd6, 1
	and.o	rd5, rd5, rd6
	br.nz	{rd5}?, [rb0, h_initial]
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	set.rd	rd6, 1
	and.o	rd5, rd5, rd6
	br.z	{rd5}?, [rb0, h_fault]
h_initial:
	set.rb	rb1, hphase
	ld.o	rd5, [rb1, 0]
	br.nz	{rd5}?, [rb0, h_fault]
	set.rd	rd5, 1
	st.o	rd5, [rb1, 0]
	@@ ---- 同步 trap 的入口记录（rc0-rc5）与出口意图（rc8-rc11）----
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
	cfx2rd	cfx_hmon, cg5, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc8, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc9, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc10, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc11, rd5
	REC	rd5
	jump	[rb0, h_body]

h_fault:
	@@ 故障处理：记 cause_id / cause_info，再把 rc10 = prev ip + 4 后 escape
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hmon, cg5, rc2, rd6
	add.si	rd6, 4
	cfx2rc	cfx_hmon, cg5, rc10, rd6
	escape	cfx_hmon
	swym	0

@@ ---------------------------------------------------------------------------
@@ H 测试体：寄存器面 + 保留/非法编码 + 屏蔽/pending
@@ ---------------------------------------------------------------------------
h_body:
	@@ 0 hart_id = 0
	cfx2rd	cfx_hart, cg8, rc0, rd5
	REC	rd5
	@@ 1/2 cycle 递增
	cfx2rd	cfx_hart, cg8, rc2, rd5
	REC	rd5
	add.si	rb1, 1
	add.si	rb1, 1
	add.si	rb1, 1
	cfx2rd	cfx_hart, cg8, rc2, rd5
	REC	rd5
	@@ 3/4 insn 递增
	cfx2rd	cfx_hart, cg8, rc3, rd5
	REC	rd5
	add.si	rb1, 1
	add.si	rb1, 1
	cfx2rd	cfx_hart, cg8, rc3, rd5
	REC	rd5
	@@ 5 timer_cmp RW
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_hart, cg16, rc1, rd6
	cfx2rd	cfx_hart, cg16, rc1, rd5
	REC	rd5
	@@ 先写全 1 关闭匹配，再测 timer_ctrl 的 [1:0] 读回
	WCFX_IMM   cfx_hart, cg16, rc1, 0xFFFFFFFFFFFFFFFF
	.set	__ctrl, 0
	.rept	5
	set.rd	rd6, __ctrl
	cfx2rc	cfx_hart, cg16, rc0, rd6
	cfx2rd	cfx_hart, cg16, rc0, rd5
	REC	rd5
	.set	__ctrl, __ctrl + 1
	.endr
	@@ ---- cg15 布局（DADAO-12 §4.7 / ADR-0064 D5）：rc0–rc5 入口记录（HW/RO，
	@@   软件写忽略、不产生异常），rc6–rc13 reserved（访问 ⇒ CFXREG），rc14/rc15 RW ----
	@@ 11-16 读：尚未发生异步进入 ⇒ 全 0
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	@@ 17/18 写忽略：rc0–rc5 全写 1，读回落 = 0（不产生异常）
	WCFX_IMM   cfx_hart, cg15, rc0, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg15, rc1, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg15, rc2, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg15, rc4, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg15, rc5, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	@@ 19 rc15 vector（原 rc5）：写全 1，读回 48 位且低 2 位 0
	WCFX_IMM   cfx_hart, cg15, rc15, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg15, rc15, rd5
	REC	rd5
	@@ 恢复真向量（后面的 timer 投递必须落到 async_entry）
	WCFX_LABEL cfx_hart, cg15, rc15, async_entry
	@@ 30-34 rc14 switch（原 rc6）：RW、复位 2 = supv；写 0/1/3 读回同值
	cfx2rd	cfx_hart, cg15, rc14, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg15, rc14, 0
	cfx2rd	cfx_hart, cg15, rc14, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg15, rc14, 1
	cfx2rd	cfx_hart, cg15, rc14, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg15, rc14, 3
	cfx2rd	cfx_hart, cg15, rc14, rd5
	REC	rd5
	@@ H 体在 hypv 下取异步进入，须把运行模式上限抬到 hypv（m18-spec-009：
	@@ 当前模式 ≤ cg15 rc14 才进入）；handler 首帧读出 rc14 后恢复 2，
	@@ 后续阶段在 supv 下按默认上限进入。写后读回 3。
	WCFX_IMM   cfx_hart, cg15, rc14, 3
	cfx2rd	cfx_hart, cg15, rc14, rd5
	REC	rd5

	@@ 25-36 保留 rc（cg15 rc6 / rc7 / rc8 / rc13）⇒ CFXREG：cause_id / cause_info / 见证
	cfx2rd	cfx_hart, cg15, rc6, rd5
	set.rd	rd5, 0xC0DE0013
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc7, rd5
	set.rd	rd5, 0xC0DE0014
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc8, rd5
	set.rd	rd5, 0xC0DE0015
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc13, rd5
	set.rd	rd5, 0xC0DE0016
	REC	rd5
	@@ 47-49 写 RO（cg8 rc0）⇒ CFXREG
	set.rd	rd6, 0
	cfx2rc	cfx_hart, cg8, rc0, rd6
	set.rd	rd5, 0xC0DE0017
	REC	rd5
	@@ 40-42 写入口记录（cg5 rc0，HW/RO）⇒ CFXREG
	set.rd	rd6, 0
	cfx2rc	cfx_hart, cg5, rc0, rd6
	set.rd	rd5, 0xC0DE0018
	REC	rd5
	@@ 43-45 读保留（cfx_hart 的 cg16 rc2，cg16 只定义 0/1/16/17/18）⇒ CFXREG
	cfx2rd	cfx_hart, cg16, rc2, rd5
	set.rd	rd5, 0xC0DE0019
	REC	rd5
	@@ 46-48 escape imms18=3（SBZ 非 0）⇒ ILLI
	.dd.t32	ESC_HART_IMM3
	set.rd	rd5, 0xC0DE001A
	REC	rd5
	@@ 49-51 escape imms18=4 ⇒ ILLI
	.dd.t32	ESC_HART_IMM4
	set.rd	rd5, 0xC0DE001B
	REC	rd5

	@@ ---- 52 cfx3（hmon）的 `cg15 rc3` 复位 = 全 1（尚未写过该行）----
	cfx2rd	cfx_hmon, cg15, rc3, rd5
	REC	rd5

	@@ ---- 53/54 屏蔽期：只置 pending、不投递 ----
	@@ 只屏蔽**当前运行模式**（hmon）的行；umon/smon 仍放行 —— 若投递错取
	@@ 别的行，这里会提前进入 handler
	WCFX_IMM   cfx_hmon, cg15, rc3, 0xFFFFFFFFFFFFFFFF	@@ bit15 = 1（屏蔽）
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM   cfx_hart, cg16, rc0, 1
	BURN	rd7, rb1
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	@@ 放开当前模式的掩码行 ⇒ **下一指令边界投递**（timer 仍到期、源尚未 ack）
	WCFX_IMM   cfx_hmon, cg15, rc3, MASK_PATTERN

wait_begin:
	set.rd	rd7, 300
wait_loop:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, wait_loop]
wait_end:
	@@ 投递未发生：签名缺槽 ⇒ 红
	set.rd	rd5, 0xDEAD0003
	REC	rd5
	jump	[rb0, fail_exit]

@@ ---------------------------------------------------------------------------
@@ U（umon + user）
@@ ---------------------------------------------------------------------------
setup_u:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 38*8			@@ S/U 模式检查点数（见 check_cfx15.expected）
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_umon, cg3, rc15, u_entry
	WCFX_IMM   cfx_umon, cg3, rc14, 0
	trap	cfx_umon, 0
	swym	0

u_entry:
	jump	[rb0, mode_body]

@@ ---------------------------------------------------------------------------
@@ S（smon + supv）
@@ ---------------------------------------------------------------------------
setup_s:
	set.rb	rb1, sig_bytes
	set.rd	rd6, 38*8			@@ S/U 模式检查点数（见 check_cfx15.expected）
	st.o	rd6, [rb1, 0]
	WCFX_LABEL cfx_smon, cg3, rc15, s_entry
	WCFX_IMM   cfx_smon, cg3, rc14, 2
	@@ supv 下访问自身 cg15/cg16 受 `cg3 rc12` deleg 约束（bit15/bit16 = 0 才允许）
	WCFX_IMM   cfx_smon, cg3, rc12, 0xFFFFFFFFFFFE7CF7
	trap	cfx_smon, 0
	swym	0

s_entry:
	jump	[rb0, mode_body]

@@ ---------------------------------------------------------------------------
@@ U/S 共用测试体：屏蔽 → pending → 放开 → 投递
@@ ---------------------------------------------------------------------------
mode_body:
	@@ 屏蔽**本模式**的掩码行（另两行仍放行）
	.if TMODE == 0
	WCFX_IMM   cfx_umon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	.else
	WCFX_IMM   cfx_smon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	.endif
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM   cfx_hart, cg16, rc0, 1
	BURN	rd7, rb1
	@@ 0/1 屏蔽期只置 pending（rc5）、src_frame 保持（rc4）
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5

	@@ 放开本模式的掩码行 ⇒ 下一指令边界投递（timer 仍到期、源尚未 ack）
	.if TMODE == 0
	WCFX_IMM   cfx_umon, cg15, rc3, MASK_PATTERN
	.else
	WCFX_IMM   cfx_smon, cg15, rc3, MASK_PATTERN
	.endif

umode_wait_begin:
	set.rd	rd7, 300
umode_wait:
	add.si	rb5, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, umode_wait]
umode_wait_end:
	@@ 投递未发生：签名缺槽 ⇒ 红
	set.rd	rd5, 0xDEAD0033
	REC	rd5
	jump	[rb0, fail_exit]

@@ ---------------------------------------------------------------------------
@@ 异步入口：cfx_hart 的 supv 单向量（三模式同一入口）
@@ 第一次进入记现场并做 escape/覆盖测试；第二次记覆盖并做屏蔽/ack；
@@ 第三次记放开掩码后的投递，然后收尾。
@@ ---------------------------------------------------------------------------
async_entry:
	@@ 精确点搜索阶段：rd20 = 1 时所有进入都走 jump 处理器
	br.nz	{rd20}?, [rb0, async_jump]
	set.rb	rb4, phase
	ld.o	rd22, [rb4, 0]
	add.si	rd22, 1
	st.o	rd22, [rb4, 0]
	set.rd	rd23, 1
	br.eq	{rd22, rd23}?, [rb0, async_phase1]
	set.rd	rd23, 2
	br.eq	{rd22, rd23}?, [rb0, async_phase2]
	jump	[rb0, async_phase3]

async_phase1:
	@@ 现场：rc0 prev_run_mode、rc1 prev_cfx_code、rc2 prev ip、
	@@ rc3 prev intr mask、rc4 src_frame、rc5 pending 汇总（进入不清，ack 前仍置位）、
	@@ rc14 switch 取该值、rc15 向量；一帧只计一次
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc14, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc15, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	@@ handler 在 escape 前 ack 已进入的源（`cg16 rc18` W1C；进入不清 pending）
	WCFX_IMM   cfx_hart, cg16, rc18, 1
	.if TMODE == 3
	@@ 首帧读出 rc14=3 后恢复默认上限 2：后续阶段在 supv 下进入
	WCFX_IMM   cfx_hart, cg15, rc14, 2
	.endif

	@@ ---- 正常异步返回：rc10 = async_ret、rc11 = 全 1（fail-safe），
	@@   然后 `escape cfx_hart`。U/S 的进入前模式是 user/supv ⇒ 复制来的
	@@   rc8/rc9 可直接返回被中断现场；H 的进入前模式是 hypv，从 supv handler
	@@   返回 hypv 属升权（§5.1 禁止）⇒ 显式把目标改为 supv/cfx_hart。
	@@   返回后第一条指令在 async_ret：此处读到的 mask 必须已是 rc11（整字），
	@@   证明 rc11 的写入与切模式/切 cfx/跳转原子完成（§5.1/§5.3）。 ----
	.if TMODE == 3
	set.rd	rd5, 2
	cfx2rc	cfx_hart, cg5, rc8, rd5
	set.rd	rd5, 15
	cfx2rc	cfx_hart, cg5, rc9, rd5
	.endif
	set.rd	rd5, async_ret
	cfx2rc	cfx_hart, cg5, rc10, rd5
	set.rd	rd5, ESC_RC11_PATTERN
	cfx2rc	cfx_hart, cg5, rc11, rd5
	escape	cfx_hart
	swym	0

async_ret:
	@@ 目标模式 monitor 的 cg15 rc3 = ESC_RC11_PATTERN（整字写入，反例：增量写）
	.if TMODE == 0
	cfx2rd	cfx_umon, cg15, rc3, rd5
	.else
	cfx2rd	cfx_smon, cg15, rc3, rd5
	.endif
	REC	rd5
	@@ escape_num 每次 escape +1（同步/异步一视同仁）：cfx_hart 的第一次
	cfx2rd	cfx_hart, cg4, rc5, rd5
	REC	rd5
	@@ ---- 覆盖语义 + 屏蔽期只置 pending：不搬走现场，再次到期整体覆盖 cg15 ----
	WCFX_IMM   cfx_hart, cg16, rc0, 0
	cfx2rd	cfx_hart, cg8, rc2, rd5
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM   cfx_hart, cg16, rc0, 1
	BURN	rd7, rb1
	@@ mask = 全 1 ⇒ 只置 pending，不投递
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	@@ 放开当前模式掩码 ⇒ 下一指令边界投递
	.if TMODE == 0
	WCFX_IMM   cfx_umon, cg15, rc3, MASK_PATTERN
	.else
	WCFX_IMM   cfx_smon, cg15, rc3, MASK_PATTERN
	.endif
rearm_fallback:
	@@ 覆盖/投递未发生（旧“帧活动期”只置 pending）时才会执行到这里
	set.rd	rd5, 0xDEAD0001
	REC	rd5
	jump	[rb0, fail_exit]

async_phase2:
	@@ 覆盖证据：prev = 进入前模式，cause_ip = 再次武装后的下一条；ecp_async_num = 2
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5

	@@ ---- supv 下屏蔽当前模式（smon 行）：只置 pending ----
	WCFX_IMM   cfx_smon, cg15, rc3, 0xFFFFFFFFFFFFFFFF
	cfx2rd	cfx_hart, cg8, rc2, rd5
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM   cfx_hart, cg16, rc0, 1
	BURN_SHORT	rd21, rb3
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	@@ ---- 源 ack：`cg16 rc18` W1C ⇒ pending 落（仍屏蔽）；写 cmp 不清 pending ----
	WCFX_IMM   cfx_hart, cg16, rc18, 1
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	@@ ---- 再武装（仍屏蔽）⇒ pending 重新置位 ----
	cfx2rd	cfx_hart, cg8, rc2, rd5
	cfx2rc	cfx_hart, cg16, rc1, rd5
	BURN_SHORT	rd21, rb3
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	@@ ---- 放开当前模式掩码 ⇒ 下一指令边界投递 ----
	WCFX_IMM   cfx_smon, cg15, rc3, MASK_PATTERN
pending_fallback:
	@@ 放开掩码后仍未投递时才会执行到这里
	set.rd	rd5, 0xDEAD0002
	REC	rd5
	jump	[rb0, fail_exit]

async_phase3:
	@@ 第三次进入：覆盖后的现场（进入不清 pending）
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc2, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg4, rc4, rd5
	REC	rd5
	@@ 源 ack（`cg16 rc18`）后 pending = 0
	WCFX_IMM   cfx_hart, cg16, rc18, 1
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	jump	[rb0, jump_setup]

@@ ---------------------------------------------------------------------------
@@ 精确点：在 `jump` 目标处到期（SimRISC-06 的 jump）
@@ 读 cycle 的延迟随平台不同（QEMU icount vs RTL 流水线），不能写死补偿；
@@ 从 delta=0 起每次 +1 cycle 重试，直到捕获到的 cause_ip == jump_target。
@@ 处理器在每次进入先 ack timer（电平源不会在读 cg15 期间重入）。
@@ ---------------------------------------------------------------------------
jump_setup:
	set.rd	rd20, 1
	set.rd	rd9, 0			@@ delta（cycle 偏移）
	set.rd	rd13, 0			@@ 尝试次数
	set.rb	rb2, jump_target	@@ 目标运行时地址（镜像不搬移）
	WCFX_IMM cfx_hart, cg16, rc1, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM cfx_hart, cg16, rc0, 1
	cfx2rd	cfx_hart, cg8, rc2, rd3
	add.uo	{rd0, rd5}, rd3, rd9
	cfx2rc	cfx_hart, cg16, rc1, rd5
	jump	[rb2, rd0, 0]

jump_target:
	add.si	rd15, 1
	jump	[rb0, jump_target]

async_jump:
	@@ 先 ack（`cg16 rc18` W1C 落 pending），再读捕获；电平源不会在读期间重入
	WCFX_IMM cfx_hart, cg16, rc18, 1
	cfx2rd	cfx_hart, cg15, rc2, rd5
	set.rb	rb2, jump_target
	rb2rd	rd6, rb2, 1
	cmp.uo	rd8, rd5, rd6
	set.rd	rd7, 0
	br.nz	{rd8}?, [rb0, jump_retry]
	@@ 命中目标边界：cause_ip == jump_target
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc1, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc3, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	set.rd	rd5, 1
	REC	rd5
	set.rd	rd20, 0
	.if TMODE == 3
	jump	[rb0, rc14_setup]
	.else
	jump	[rb0, done_ok]
	.endif

jump_retry:
	add.si	rd13, 1
	set.rd	rd7, 64
	br.eq {rd13, rd7}?, [rb0, jump_fail]
	add.si	rd9, 1			@@ 晚一个 cycle
	WCFX_IMM cfx_hart, cg16, rc0, 1
	cfx2rd	cfx_hart, cg8, rc2, rd3
	add.uo	{rd0, rd5}, rd3, rd9
	cfx2rc	cfx_hart, cg16, rc1, rd5
	set.rb	rb2, jump_target
	jump	[rb2, rd0, 0]

jump_fail:
	set.rd	rd5, 0xBAD00002
	REC	rd5
	jump	[rb0, fail_exit]


.if TMODE == 3
@@ ---------------------------------------------------------------------------
@@ 异步进入的运行模式上限 = `cg15 rc14`（`m18-spec-006/009`；ADR-0064 D9）
@@ 在 supv 下：rc14=0（低于当前模式）⇒ **不进入**，pending 与 `cg15 rc5`
@@ 保留；把 rc14 抬到 2 后同一边界进入 supv（prev 证明），再重复一次。
@@ timer 到期落在 BURN 内，本组不判投递边界地址。
@@ ---------------------------------------------------------------------------
rc14_setup:
	WCFX_IMM   cfx_hart, cg16, rc0, 0
	WCFX_IMM   cfx_hart, cg16, rc1, 0xFFFFFFFFFFFFFFFF
	WCFX_IMM   cfx_hart, cg15, rc14, 0
	WCFX_LABEL cfx_hart, cg15, rc15, rc14_bad_entry
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM   cfx_hart, cg16, rc0, 1
	BURN	rd7, rb1
	@@ 上限 0 < 当前 supv ⇒ 不得进入：pending 与汇总都保留（进入则先落
	@@ 到 rc14_bad_entry 的哨兵槽，后面的槽全错位）
	cfx2rd	cfx_hart, cg15, rc5, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc4, rd5
	REC	rd5
	@@ 抬到 supv（=2）并换回正常向量：下一指令边界进入；未进入则 DEAD0007
	WCFX_LABEL cfx_hart, cg15, rc15, rc14_s_entry
	WCFX_IMM   cfx_hart, cg15, rc14, 2
	BURN	rd21, rb3
	set.rd	rd5, 0xDEAD0007
	REC	rd5
	jump	[rb0, fail_exit]

rc14_bad_entry:
	@@ 上限未生效的负控：进入即写哨兵槽（正常路径不会到这里）
	set.rd	rd5, 0xBAD0C14
	REC	rd5
	jump	[rb0, fail_exit]

rc14_s_entry:
	@@ rc14=2、进入前在 supv：prev = supv；rc14 读数 = 2
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	cfx2rd	cfx_hart, cg15, rc14, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg16, rc18, 1	@@ ack before re-arming
	@@ 从 supv 再投递一次（rc14 仍 2）：下一次进入的 prev = supv
	WCFX_IMM   cfx_hart, cg16, rc0, 0
	WCFX_IMM   cfx_hart, cg16, rc1, 0xFFFFFFFFFFFFFFFF
	WCFX_LABEL cfx_hart, cg15, rc15, rc14_h_entry
	cfx2rd	cfx_hart, cg8, rc2, rd5
	add.si	rd5, 150
	cfx2rc	cfx_hart, cg16, rc1, rd5
	WCFX_IMM   cfx_hart, cg16, rc0, 1
	BURN	rd7, rb1
	set.rd	rd5, 0xDEAD0008
	REC	rd5
	jump	[rb0, fail_exit]

rc14_h_entry:
	@@ prev = supv（rc14=2 那次确实进 supv）；转 escape 判据
	cfx2rd	cfx_hart, cg15, rc0, rd5
	REC	rd5
	WCFX_IMM   cfx_hart, cg16, rc18, 1	@@ ack the last rc14 entry
	WCFX_IMM   cfx_hart, cg16, rc0, 0
	WCFX_IMM   cfx_hart, cg16, rc1, 0xFFFFFFFFFFFFFFFF
	WCFX_LABEL cfx_hart, cg15, rc15, async_entry
	jump	[rb0, esc_criteria]

.endif


@@ ---------------------------------------------------------------------------
@@ 同步 CFXESC 处理：escape 判据（升权 / 目标 cfx 未实现 / cfxha != 当前 cfx）
@@ 全部在 supv 的 async handler 里发起；CFXESC 进入当前 cfx（cfx_hart）的
@@ supv 行向量（cg2 rc15 = esc9_entry）。esc9_entry 记录帧后按 rd21 返回。
@@ ---------------------------------------------------------------------------
esc_criteria:
	@@ 1) 目标模式升权：rc8 = hypv(3) > 当前 supv(2) ⇒ CFXESC
	set.rd	rd21, 1
	WCFX_IMM   cfx_hart, cg5, rc8, 3
	WCFX_IMM   cfx_hart, cg5, rc9, 15
	WCFX_LABEL cfx_hart, cg5, rc10, esc_bad1
	WCFX_IMM   cfx_hart, cg5, rc11, ESC_BAD_MASK
esc_bad1:
	escape	cfx_hart
	set.rd	rd5, 0xDEAD000A
	REC	rd5
	jump	[rb0, fail_exit]
esc_cont1:
	@@ 2) 目标 cfx 未实现（rc9 = 6）⇒ CFXESC
	set.rd	rd21, 2
	WCFX_IMM   cfx_hart, cg5, rc8, 2
	WCFX_IMM   cfx_hart, cg5, rc9, 6
	WCFX_LABEL cfx_hart, cg5, rc10, esc_bad2
	WCFX_IMM   cfx_hart, cg5, rc11, ESC_BAD_MASK
esc_bad2:
	escape	cfx_hart
	set.rd	rd5, 0xDEAD000B
	REC	rd5
	jump	[rb0, fail_exit]
esc_cont2:
	@@ 3) cfxha != 当前 cfx（cfx_smon）⇒ 当前 cfx 的 CFXESC
	set.rd	rd21, 3
	WCFX_IMM   cfx_hart, cg5, rc8, 2
	WCFX_IMM   cfx_hart, cg5, rc9, 15
	WCFX_LABEL cfx_hart, cg5, rc10, esc_bad3
	WCFX_IMM   cfx_hart, cg5, rc11, ESC_BAD_MASK
esc_bad3:
	escape	cfx_smon
	set.rd	rd5, 0xDEAD000C
	REC	rd5
	jump	[rb0, fail_exit]
esc_cont3:
	jump	[rb0, done_ok]

esc9_entry:
	cfx2rd	cfx_hart, cg5, rc4, rd5		@@ cause id = CFXESC
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc5, rd5		@@ cause info = escape 指令编码
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc2, rd5		@@ prev ip = escape 地址
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc8, rd5		@@ 进入前的目标模式（非法值保持）
	REC	rd5
	cfx2rd	cfx_hart, cg5, rc9, rd5		@@ 进入前的目标 cfx（非法值保持）
	REC	rd5
	cfx2rd	cfx_smon, cg15, rc3, rd5		@@ 切换任何状态前报错 ⇒ mask 不变
	REC	rd5
	set.rd	rd5, 1
	br.eq	{rd21, rd5}?, [rb0, __e_cont1]
	set.rd	rd5, 2
	br.eq	{rd21, rd5}?, [rb0, __e_cont2]
	set.rd	rd5, esc_cont3
	jump	[rb0, __e_do]
__e_cont1:
	set.rd	rd5, esc_cont1
	jump	[rb0, __e_do]
__e_cont2:
	set.rd	rd5, esc_cont2
__e_do:
	set.rd	rd6, 2
	cfx2rc	cfx_hart, cg5, rc8, rd6
	set.rd	rd6, 15
	cfx2rc	cfx_hart, cg5, rc9, rd6
	cfx2rc	cfx_hart, cg5, rc10, rd5
	set.rd	rd6, MASK_PATTERN
	cfx2rc	cfx_hart, cg5, rc11, rd6
	escape	cfx_hart
	swym	0

@@ ---------------------------------------------------------------------------
@@ 收尾
@@ ---------------------------------------------------------------------------
smon_fault:
	@@ supv 下的意外同步异常（如 CFXPERM）：记见证后快速失败
	set.rd	rd5, 0xBAD00001
	REC	rd5
	jump	[rb0, fail_exit]

fail_exit:
	DUMP_AND_EXIT 1

done_ok:
	DUMP_AND_EXIT 0

	@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.balign 4
perm_mon:
	PERM_OPEN_DELEG	cfx_hart
	PERM_OPEN_DELEG	cfx_smon
	PERM_OPEN_DELEG	cfx_umon
	PERM_OPEN_DELEG	cfx_pmem
	PERM_OPEN	cfx_ptw
	PERM_MON_CLOSE

	.data
	.p2align 3
hphase:
	.dd.o64	0
phase:
	.dd.o64	0
sig_bytes:
	.dd.o64	0
