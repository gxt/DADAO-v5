@@ tests/arch/common/env/hmon/env.S — hmon（hypv）运行模式环境（m16-testcases-015）
@@
@@ 进入：step5 BootROM 的 hmon 阶段已把 `cfx_umon.hypv.excp_vector` 指到 profile
@@ ENTRY 并以 `switch_run_mode = hypv` 交付，本环境就是该 ENTRY 处的第一段代码，
@@ 因此**无需再进入**：设栈后直接跳到 body（仍为 hypv，监视器 = cfx_hmon）。
@@
@@ 异常：body 在 hypv 的同步异常由当前模式监视器 cfx_hmon（BootROM 固件）处理；
@@ 固件把 cause / cause_ip 写进 profile 的 fault-record 槽并 `escape` 回
@@ `cause_ip + 4`（`tests/ee-vast/hmon_vast.S` 的 resume 策略），body 可读该槽。
@@ 本环境不改 cfx_hmon 的向量（源 cfx_umon 对其 cfxreg/cfxtrap 被缺省掩码拒绝）。
@@
@@ 与 body 的契约：`rb1` = 栈指针，`rb6` = 退出例程地址（`.envtail` 的 env_finish）。
@@ 签名区：`ENV_SIG_BUF` / `ENV_SIG_SLOTS` 由驱动按 profile 传入；body 用
@@ `tests/shared/asm/signature.inc` 预填并逐槽写；`.envtail` 负责整段输出与
@@ semihosting `SYS_EXIT(0)`。

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
	set.rb	rb6, ENV_TAIL
	set.rb	rb2, ENV_BODY_SRC
	jump	[rb2, rd0, 0]

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
