@@ cfx02_regs.S — `cfx_umon`（cfx0）/`cfx_smon`（cfx2）**寄存器面 + 两轴权限**
@@ RTL 探针（`m16-chipyard-019`）
@@
@@ 目的：只覆盖 `DADAO-12 §3` 的寄存器文件语义与 `cfxreg` 轴的权限判定，不测
@@ U/S 模式进入路由（`m16-chipyard-020`）、不测异步中断、不测 cfx0/cfx2 的
@@ 内部空间访问。所有实测值经 `__REC` 写进结果缓冲，由
@@ `check_cfx02_regs.py` 从 `spec/` 与 `.tao/contracts/` 现场派生的期望逐条
@@ 比对；本文件只按规范字段摆放地址/数据，不当判据。
@@
@@ 覆盖（`DADAO-12` §3.1–§3.8、`contract-see` §3/§6.1.1）：
@@   A cfx0 模式行：cg2 rc0 同步 mask 复位、cg1 rc8 switch_run_mode 复位、
@@     cg2 rc10 excp_vector 复位与「写丢低 2 位」
@@   B 四个同步 mask 互相独立：写 cg0 rc2 后 cg3 rc2 仍为复位值
@@   C cfx0 cg3 行（rc0/rc2 mask、rc12 deleg 复位与 bit3 恒 1）
@@   D cfx0 cg4 配置/计数（cfx_id / 三个计数 / escape_num / scratch_regs_num）、
@@     cg5 rc5 pending、cg6 rc0/rc1 暂存、cg8 rc1 异步来源掩码（`ADR-0061` D5）
@@   E cfx0 cg7 无内部空间（4 个字段全 0）；cfx0 空异常帧（prev_mode/cause_id）
@@   F cfx2：cg3 rc0/rc8/rc10（向量 = smon SRAM 起始）、cg0 rc8、
@@     cg3 rc12、cg4 cfx_id/scratch_regs_num、cg6 暂存、cg8 rc1、cg7 块 0
@@   G CFXREG：保留 rc（cg0 rc9 / cg4 rc7 / cg8 rc2）、写 RO（cg4 rc0）与
@@     `ADR-0061` D5 之后作废的 `cg0`/`cg3 rc4`（保留，访问 ⇒ CFXREG）
@@
@@ 两轴掩码的**存储面**（cg0-cg3 rc0-3 四个独立同步 mask、cg3 rc12 deleg）由本
@@ 探针覆盖；其**强制判定**（CFXPERM）不在本任务启用：chipyard 的 BootROM 链以
@@ `cfx_power`（cfx63）运行测试体，而规范复位掩码只允许 `cfx_hmon`（bit3），启用
@@ 后 cfx0/cfx2（以及既有 cfx4/cfx5）全部不可达；判定随 `m16-chipyard-020` 的
@@ U/S 进入链落地（见任务书「遗留问题」）。
@@
@@ 故障观察：固件 hmon 把 `excp_cause_id`/`excp_cause_info` 存在
@@ HMON_BASE+0xE0/+0xF0，并从 +0xF8 取回落点。每个故障例先把回落点设成自己的
@@ resume；程序入口先把 +0xF8 指向 `abort` ⇒ 寄存器整体缺失时会以非零退出。
@@
@@ **只在 `WumingVastConfig` 上跑**：`Kaiwu-Tiny` 不实现 cfx0/cfx2。
@@ **只跑 hmon（hypv）模式**：020 未合入前没有 U/S 进入路由；smon/umon 模式
@@ 的排除原因见 `tests/arch/umon/README.md`。
@@
@@ 用法：
@@   llvm-mc --triple=dadao-unknown-elf -filetype=obj -I . cfx02_regs.S -o cfx02_regs.o
@@   ld.lld -T cfx02_regs.lds cfx02_regs.o -o cfx02_regs.elf

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/shared/asm/perm_hypv.inc"

	.equ PATTERN64, 0x123456789ABCDEF0

	__TEST_BEGIN
	set.rb rb20, HMON_BASE
	set.rb rb20, HMON_BASE
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	@@ 任何未预期异常都落到 abort（cfx0/cfx2 整体缺失时第一条访问即走这里）
	set.rb rb21, abort
	st.o	rb21, [rb20, 0xF8]

	@@ ---- A. cfx0 模式行 ----
	cfx2rd	cfx_umon, cg2, rc0, rd5		@@ supv 行 cfxtrap mask 复位
	__REC	rd5
	cfx2rd	cfx_umon, cg1, rc8, rd5		@@ jail 行 switch_run_mode 复位 = 2
	__REC	rd5
	cfx2rd	cfx_umon, cg2, rc10, rd5	@@ supv 行 excp_vector 复位 = 0
	__REC	rd5
	set.rd	rd6, 0x123456789ABCDEFF
	cfx2rc	cfx_umon, cg2, rc10, rd6	@@ 写向量：低 2 位丢弃
	cfx2rd	cfx_umon, cg2, rc10, rd5
	__REC	rd5

	@@ ---- B. 四个同步 mask 互相独立（写 cg0 rc2 不影响 cg3 rc2）----
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_umon, cg0, rc2, rd6
	cfx2rd	cfx_umon, cg0, rc2, rd5
	__REC	rd5
	cfx2rd	cfx_umon, cg3, rc0, rd5		@@ hypv cfxtrap mask 复位
	__REC	rd5
	cfx2rd	cfx_umon, cg3, rc2, rd5		@@ hypv cfxreg mask 复位（未被上面写动）
	__REC	rd5

	@@ ---- C. cfx0 cg3 rc12 ----
	cfx2rd	cfx_umon, cg3, rc12, rd5		@@ 复位全 1
	__REC	rd5
	set.rd	rd6, 0
	cfx2rc	cfx_umon, cg3, rc12, rd6	@@ bit3 恒 1
	cfx2rd	cfx_umon, cg3, rc12, rd5
	__REC	rd5

	@@ ---- D. cfx0 cg4 / cg5 rc5 / cg6 / cg8 rc1 ----
	cfx2rd	cfx_umon, cg4, rc0, rd5		@@ cfx_id = 0
	__REC	rd5
	cfx2rd	cfx_umon, cg4, rc2, rd5		@@ trap_num
	__REC	rd5
	cfx2rd	cfx_umon, cg4, rc3, rd5		@@ excp_sync_num
	__REC	rd5
	cfx2rd	cfx_umon, cg4, rc4, rd5		@@ excp_async_num
	__REC	rd5
	cfx2rd	cfx_umon, cg4, rc5, rd5		@@ escape_num
	__REC	rd5
	cfx2rd	cfx_umon, cg4, rc6, rd5		@@ scratch_regs_num（checker 只查 2..64）
	__REC	rd5
	cfx2rd	cfx_umon, cg5, rc5, rd5		@@ pending 复位 = 0
	__REC	rd5
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_umon, cg5, rc5, rd6
	cfx2rd	cfx_umon, cg5, rc5, rd5
	__REC	rd5
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_umon, cg6, rc0, rd6
	cfx2rd	cfx_umon, cg6, rc0, rd5
	__REC	rd5
	set.rd	rd6, 0x0F1E2D3C4B5A6978
	cfx2rc	cfx_umon, cg6, rc1, rd6
	cfx2rd	cfx_umon, cg6, rc1, rd5
	__REC	rd5
	cfx2rd	cfx_umon, cg8, rc1, rd5		@@ 异步来源掩码复位 = 全 1（ADR-0061 D5）
	__REC	rd5
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_umon, cg8, rc1, rd6
	cfx2rd	cfx_umon, cg8, rc1, rd5
	__REC	rd5

	@@ ---- E. cfx0 cg7 无内部空间 + 空异常帧 ----
	cfx2rd	cfx_umon, cg7, rc0, rd5
	__REC	rd5
	cfx2rd	cfx_umon, cg7, rc1, rd5
	__REC	rd5
	cfx2rd	cfx_umon, cg7, rc2, rd5
	__REC	rd5
	cfx2rd	cfx_umon, cg7, rc3, rd5
	__REC	rd5
	cfx2rd	cfx_umon, cg5, rc0, rd5		@@ prev_run_mode 复位
	__REC	rd5
	cfx2rd	cfx_umon, cg5, rc2, rd5		@@ cause_id 复位（尚未进入过 cfx0）
	__REC	rd5

	@@ ---- G. cfx0 CFXREG：保留 rc / 写 RO ----
	.globl	f1_aip
f1_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f1_fault
f1_fault:
	cfx2rd	cfx_umon, cg0, rc9, rd5		@@ cg0 rc9 保留
	.globl	f1_resume
f1_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5

	.globl	f2_aip
f2_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f2_fault
f2_fault:
	cfx2rd	cfx_umon, cg4, rc7, rd5		@@ cg4 rc7 保留
	.globl	f2_resume
f2_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5

	.globl	f3_aip
f3_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f3_fault
f3_fault:
	cfx2rc	cfx_umon, cg4, rc0, rd6		@@ 写 RO cfx_id
	.globl	f3_resume
f3_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5

	@@ `cg0`–`cg3 rc4` 自 `ADR-0061` D5 起不定义（保留，访问 ⇒ CFXREG）
	.globl	f6_aip
f6_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f6_fault
f6_fault:
	cfx2rd	cfx_umon, cg0, rc4, rd5		@@ 模式行 rc4 保留
	.globl	f6_resume
f6_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5

	@@ cfx2 段之前把返回槽复位为 abort：cfx2 整体缺失时第一条访问即
	@@ CFXREG ⇒ 直接显式失败（否则会复用 f3 的回落点、回到 cfx2 段反复触发）。
	set.rb rb21, abort
	st.o	rb21, [rb20, 0xF8]

	@@ ---- F. cfx2 寄存器面 ----
	cfx2rd	cfx_smon, cg3, rc0, rd5
	__REC	rd5
	cfx2rd	cfx_smon, cg3, rc8, rd5		@@ hypv switch_run_mode = 3
	__REC	rd5
	cfx2rd	cfx_smon, cg3, rc10, rd5	@@ 向量复位 = smon SRAM 起始
	__REC	rd5
	cfx2rd	cfx_smon, cg0, rc8, rd5		@@ user switch_run_mode = 2
	__REC	rd5
	cfx2rd	cfx_smon, cg3, rc12, rd5
	__REC	rd5
	cfx2rd	cfx_smon, cg4, rc0, rd5		@@ cfx_id = 2
	__REC	rd5
	cfx2rd	cfx_smon, cg4, rc6, rd5		@@ scratch_regs_num
	__REC	rd5
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_smon, cg6, rc0, rd6
	cfx2rd	cfx_smon, cg6, rc0, rd5
	__REC	rd5
	cfx2rd	cfx_smon, cg8, rc1, rd5
	__REC	rd5
	cfx2rd	cfx_smon, cg7, rc0, rd5		@@ 块 0：exists | SRAM
	__REC	rd5
	cfx2rd	cfx_smon, cg7, rc1, rd5		@@ 内部起始偏移
	__REC	rd5
	cfx2rd	cfx_smon, cg7, rc2, rd5		@@ 64 KiB
	__REC	rd5
	cfx2rd	cfx_smon, cg7, rc3, rd5		@@ R | W | X
	__REC	rd5

	@@ ---- G'. cfx2 CFXREG：保留 rc ----
	.globl	f4_aip
f4_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f4_fault
f4_fault:
	cfx2rd	cfx_smon, cg5, rc6, rd5		@@ cg5 rc6 保留
	.globl	f4_resume
f4_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5

	.globl	f5_aip
f5_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f5_fault
f5_fault:
	cfx2rd	cfx_smon, cg8, rc2, rd5		@@ cg8 rc2 保留（monitor 只有 rc1）
	.globl	f5_resume
f5_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5

	.globl	f7_aip
f7_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f7_fault
f7_fault:
	cfx2rd	cfx_smon, cg3, rc4, rd5		@@ hypv 行 rc4 保留
	.globl	f7_resume
f7_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5

	__TEST_END

	@@ 未预期异常（含 cfx0/cfx2 整体缺失）落点：显式失败，不是死循环
abort:
	__EXIT	126

	@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.balign 4
perm_mon:
	PERM_OPEN_DELEG	cfx_smon
	PERM_OPEN_DELEG	cfx_umon
	PERM_MON_CLOSE

	__TEST_SECTIONS
