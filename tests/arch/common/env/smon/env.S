@@ tests/arch/common/env/smon/env.S — smon（supv）运行模式环境（m16-testcases-015）
@@
@@ 进入：环境在 profile ENTRY 处仍以 hypv 运行（step5 BootROM 交付）。它把
@@ cfx_umon 的 **hypv 行** `switch_run_mode` 写成 supv（2）、`excp_vector` 写成
@@ 本文件的 `env_supv_entry`，再 `trap cfx_umon, 0`（目标 = 自身 cfx，两轴权限
@@ 的 cfx 轴被绕过）⇒ 硬件按该行切换运行模式，body 在 **supv** 运行，supv 的
@@ 当前模式监视器为 cfx_smon。
@@
@@ 异常：step5 测试链不装载 cfx_smon，且 cfx_smon 的 hypv 行 cfxreg/cfxtrap
@@ （源 cfx_umon）保持缺省掩码（bit0=1）⇒ 本环境**无法**安装 cfx_smon 的 supv
@@ 向量（显式限制，见 `README.md`「已知限制」）；supv 下**不得**依赖同步异常。
@@ 显式 `trap cfx_umon, immu18` 走 cfx_umon 的 supv 行，本环境把它指到
@@ `env_supv_fault`（在 hypv 运行），记 cause 后以 `0xE1` fail-closed。
@@
@@ 权限：supv 访问 cfx_umon 的 cg4-cg8 受该 cfx 的 `cg_reg_deleg`（cg3 rc12）
@@ 约束，故先把自身 deleg 置 `0x8`（除硬件恒 1 的 cg3 外整组开放；ADR-0045 D6
@@ 的软件写法，与 `tests/ee-vast/hmon_k0_vast.S` 同口径）。
@@
@@ 与 body 的契约：`rb1` = 栈指针，`rb6` = 退出例程地址。

	.include "machine-vast.inc"
	.include "signature.inc"

	.ifndef	ENV_SIG_BUF
	.equ	ENV_SIG_BUF,   0x62000000
	.endif
	.ifndef	ENV_SIG_SLOTS
	.equ	ENV_SIG_SLOTS, 8
	.endif
	.ifndef	ENV_STACK
	.equ	ENV_STACK,     0x61FFF000
	.endif
	.ifndef	ENV_BODY_SRC
	.equ	ENV_BODY_SRC,  ENTRY + 0x1000
	.endif
	.ifndef	ENV_TAIL
	.equ	ENV_TAIL,      ENTRY + 0x2000
	.endif

	.section .envcode,"ax",@progbits
	.globl	_start
_start:
	set.rb	rb1, ENV_STACK

	@@ supv 可读本 cfx 的 cg4-cg8：打开自身 cg_reg_deleg（cg3 硬件恒拒绝）
	set.rd	rd6, 0x8
	cfx2rc	cfx_umon, cg3, rc12, rd6

	@@ supv 的显式 trap 回落：cfx_umon 的 supv 向量 -> env_supv_fault（跑 hypv）
	set.rb	rb2, env_supv_fault
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_umon, cg2, rc10, rd6
	set.rd	rd6, 3
	cfx2rc	cfx_umon, cg2, rc8, rd6

	@@ hypv -> supv：cfx_umon 的 hypv 行 switch_run_mode = 2
	set.rb	rb2, env_supv_entry
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_umon, cg3, rc10, rd6
	set.rd	rd6, 2
	cfx2rc	cfx_umon, cg3, rc8, rd6
	trap	cfx_umon, 0
	swym	0

env_supv_entry:
	set.rb	rb1, ENV_STACK
	set.rb	rb6, ENV_TAIL
	set.rb	rb2, ENV_BODY_SRC
	jump	[rb2, rd0, 0]

	@@ 显式 trap 回落（在 hypv 运行）：记 cause 并以 0xE1 fail-closed
env_supv_fault:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS
	cfx2rd	cfx_umon, cg5, rc2, rd5
	SIGUPD	rd5
	set.rd	rd9, 0xE1
	set.rb	rb3, env_exit_code
	jump	[rb3, rd0, 0]

	.section .envtail,"ax",@progbits
	.globl	env_finish
env_finish:
	SIG_DUMP_CHARS ENV_SIG_BUF, ENV_SIG_SLOTS
	set.rd	rd9, 0x0

	.globl	env_exit_code
env_exit_code:
	set.rb	rb16, EXIT_BLOCK
	set.rd	rd8, 0x00020026
	st.o	rd8, [rb16, 0]
	st.o	rd9, [rb16, 8]
	set.rd	rd16, 0x18
	trap	cfx_umon, 0x3FF00
	swym	0
