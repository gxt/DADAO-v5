@@ cfx5_regs.S — `cfx_cache`（cfx5）**寄存器面**探针（`m16-chipyard-016`）
@@
@@ 目的：只覆盖 `contract-cache` 的寄存器文件语义，不测 I/D 阵列、不测维护
@@ 命令对阵列的效果（那是下一件任务）。所有实测值经 `__REC` 写进结果缓冲，由
@@ `check_cfx5_regs.py` 从 `.tao/contracts/contract-cache.md` 现场派生的期望
@@ 逐条比对；本文件不把寄存器位号/存在值当判据（只按合约位定义填字段）。
@@
@@ 覆盖（CACHE-03/06/07/09/12/13/14/18/27）：
@@   1 `cache_exist`（cg8 rc0，RO）读回 I/D 两侧 = 0b11
@@   2 `cache_enable`（cg8 rc8，RW）复位 = exist；写 0/1/3/全 1 的读回
@@   3 `cache_addr_start`（cg8 rc10，RW）只存 `PA[55:0]`，`[63:56]` 读 0
@@   4 `cache_addr_size`（cg8 rc11，RW）整 64 位往返
@@   5 `cache_ctrl`（cg8 rc9，WO）在「选侧=00」或「op=none」时无条件 no-op，
@@     不检查范围编码与 `addr_size`；合法编码的写不得报异常
@@   6 非法编码（选侧≠0 且 op≠0 且范围=reserved）⇒ `CFXREG`
@@   7 读 `cache_ctrl`（WO）⇒ `CFXREG`；写 `cache_exist`（RO）⇒ `CFXREG`；
@@     保留 rc（`cg8 rc1`）⇒ `CFXREG`（CACHE-04）
@@
@@ 故障观察：固件 hmon 把 `excp_cause_id`/`excp_cause_info` 存在
@@ HMON_BASE+0xE0/+0xF0，并从 +0xF8 取回落点（Tiny/Vast 共用的 BootROM 固件）。
@@ 每个故障例先把回落点设成自己的 resume；程序入口先把 +0xF8 指向 `abort`
@@ ⇒ 「cfx5 未实现时第一条 cfx2rd 就 CFXREG」会以非零退出收场，不是死循环。
@@
@@ **只在 `WumingVastConfig` 上跑**：`Kaiwu-Tiny` 不实现 cfx5（CACHE-28）。
@@
@@ 用法：
@@   llvm-mc --triple=dadao-unknown-elf -filetype=obj -I . cfx5_regs.S -o cfx5_regs.o
@@   ld.lld -T cfx5_regs.lds cfx5_regs.o -o cfx5_regs.elf

	.include "tests/inst/macros/inst_test.inc"

	@@ 控制字（只用于把字段摆进指令；判据在 checker 里从合约重算）
	.equ CTRL_SEL_ID,     0xC000	@@ [15:14] = 11（I 与 D 都选）
	.equ CTRL_SEL_I,      0x8000	@@ [15] = I
	.equ CTRL_SEL_D,      0x4000	@@ [14] = D
	.equ CTRL_OP_NONE,    0x0
	.equ CTRL_OP_CLEAN,   0x1
	.equ CTRL_OP_INVAL,   0x2
	.equ CTRL_OP_FLUSH,   0x3
	.equ CTRL_SCOPE_ALL,  0x0
	.equ CTRL_SCOPE_LINE, 0x4
	.equ CTRL_SCOPE_RANGE, 0x8
	.equ CTRL_SCOPE_RESV, 0xC

	.equ PATTERN64, 0x123456789ABCDEF0

	__TEST_BEGIN
	set.rb rb20, HMON_BASE
	@@ 任何未预期异常都落到 abort（cfx5 未实现时第一条访问即走这里）
	set.rb rb21, abort
	st.o	rb21, [rb20, 0xF8]

	@@ 复位/只读：cache_exist = I|D（CACHE-06/27）
	cfx2rd	cfx_cache, cg8, rc0, rd5
	__REC	rd5

	@@ cache_enable 复位 = exist（CACHE-07/27）
	cfx2rd	cfx_cache, cg8, rc8, rd5
	__REC	rd5

	set.rd	rd6, 0
	cfx2rc	cfx_cache, cg8, rc8, rd6
	cfx2rd	cfx_cache, cg8, rc8, rd5
	__REC	rd5

	set.rd	rd6, 1
	cfx2rc	cfx_cache, cg8, rc8, rd6
	cfx2rd	cfx_cache, cg8, rc8, rd5
	__REC	rd5

	set.rd	rd6, 3
	cfx2rc	cfx_cache, cg8, rc8, rd6
	cfx2rd	cfx_cache, cg8, rc8, rd5
	__REC	rd5

	@@ exist 位为 0 的位置写 1 无效果；其余位读 0（CACHE-07）
	set.rd	rd6, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_cache, cg8, rc8, rd6
	cfx2rd	cfx_cache, cg8, rc8, rd5
	__REC	rd5

	@@ addr_start：完整 56 位 PA，[63:56] 读 0、写忽略（CACHE-18）
	set.rd	rd6, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_cache, cg8, rc10, rd6
	cfx2rd	cfx_cache, cg8, rc10, rd5
	__REC	rd5

	set.rd	rd6, PATTERN64
	cfx2rc	cfx_cache, cg8, rc10, rd6
	cfx2rd	cfx_cache, cg8, rc10, rd5
	__REC	rd5

	@@ addr_size：整 64 位字节数往返（CACHE-03）
	set.rd	rd6, PATTERN64
	cfx2rc	cfx_cache, cg8, rc11, rd6
	cfx2rd	cfx_cache, cg8, rc11, rd5
	__REC	rd5

	@@ ---- no-op：不检查范围编码与 size（CACHE-12/13） ----
	@@ a) 选侧 = 00，op = flush，范围 = reserved ⇒ no-op
	set.rd	rd6, (CTRL_OP_FLUSH | CTRL_SCOPE_RESV)
	cfx2rc	cfx_cache, cg8, rc9, rd6
	set.rd	rd5, 0xC0DE0001
	__REC	rd5

	@@ b) 选侧 = 11，op = none，范围 = PA 区间，size = 0 ⇒ no-op
	set.rd	rd6, 0
	cfx2rc	cfx_cache, cg8, rc11, rd6
	set.rd	rd6, (CTRL_SEL_ID | CTRL_OP_NONE | CTRL_SCOPE_RANGE)
	cfx2rc	cfx_cache, cg8, rc9, rd6
	set.rd	rd5, 0xC0DE0002
	__REC	rd5

	@@ ---- 合法编码：写即执行，不得报异常（CACHE-14/23） ----
	set.rd	rd6, (CTRL_SEL_ID | CTRL_OP_CLEAN | CTRL_SCOPE_ALL)
	cfx2rc	cfx_cache, cg8, rc9, rd6
	set.rd	rd5, 0xC0DE0003
	__REC	rd5

	set.rd	rd6, (CTRL_SEL_I | CTRL_OP_INVAL | CTRL_SCOPE_LINE)
	cfx2rc	cfx_cache, cg8, rc9, rd6
	set.rd	rd5, 0xC0DE0004
	__REC	rd5

	set.rd	rd6, 1
	cfx2rc	cfx_cache, cg8, rc11, rd6
	set.rd	rd6, (CTRL_SEL_D | CTRL_OP_FLUSH | CTRL_SCOPE_RANGE)
	cfx2rc	cfx_cache, cg8, rc9, rd6
	set.rd	rd5, 0xC0DE0005
	__REC	rd5

	@@ ---- 非法编码 ⇒ CFXREG（CACHE-14） ----
	@@ 选侧 = 11，op = clean，范围 = reserved
	set.rd	rd6, (CTRL_SEL_ID | CTRL_OP_CLEAN | CTRL_SCOPE_RESV)
	.globl	f1_aip
f1_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f1_fault
f1_fault:
	cfx2rc	cfx_cache, cg8, rc9, rd6
	.globl	f1_resume
f1_resume:
	ld.o	rd5, [rb20, 0xE0]		@@ excp_cause_id
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]		@@ excp_cause_info = 指令编码
	__REC	rd5

	@@ 读 cache_ctrl（WO）⇒ CFXREG（CACHE-03）
	.globl	f2_aip
f2_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f2_fault
f2_fault:
	cfx2rd	cfx_cache, cg8, rc9, rd5
	.globl	f2_resume
f2_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 写 cache_exist（RO）⇒ CFXREG（CACHE-03/04）
	.globl	f3_aip
f3_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f3_fault
f3_fault:
	cfx2rc	cfx_cache, cg8, rc0, rd6
	.globl	f3_resume
f3_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 保留 rc（cg8 rc1）⇒ CFXREG（CACHE-04）
	.globl	f4_aip
f4_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	f4_fault
f4_fault:
	cfx2rd	cfx_cache, cg8, rc1, rd5
	.globl	f4_resume
f4_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	__TEST_END

	@@ 未预期异常（含 cfx5 整体缺失）落点：显式失败，不是死循环
abort:
	__EXIT	126

	__TEST_SECTIONS
