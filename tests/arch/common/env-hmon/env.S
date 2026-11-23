@@ tests/arch/common/env-hmon/env.S — hmon（hypv）运行模式环境（m16-testcases-015/017）
@@
@@ 进入：step5 BootROM 的 hmon 阶段已 `jump` 到 profile ENTRY，交付时
@@ `inner_cfx_code` = cfx_hmon（源 cfx = 3）、`inner_run_mode` = hypv
@@ （`m16-testcases-017`），本环境就是该 ENTRY 处的第一段代码，因此**无需再
@@ 进入**：设栈 + 权限准备后直接跳到 body（仍为 cfx_hmon / hypv，监视器 =
@@ cfx_hmon）。
@@
@@ 异常：body 在 hypv 的同步异常由当前模式监视器 cfx_hmon（BootROM 固件）处理；
@@ 固件把 cause / cause_ip 写进 profile 的 fault-record 槽并 `escape` 回
@@ `cause_ip + 4`（`tests/ee-vast/hmon_vast.S` 的 resume 策略），body 可读该槽。
@@ 本环境不改 cfx_hmon 的 hypv 向量（固件入口）。
@@
@@ 权限（见 `cfx_perm.inc`）：在 `.envperm` 里按 `cfx_access` 打开声明的 cfx、
@@ 收窄未声明的 cfx（未声明访问 ⇒ `CFXPERM`）；本模式不降模式，deleg 传 0
@@ （deleg 只约束 supv）。body 跳到 `rb6` 后在同一段里还原并回读校验。
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

	@@ 权限准备 / 收窄的宏与失败处理（依赖上面的 ENV_SIG_* 与 `-I` 传的 env 目录）
	.include "cfx_perm.inc"

	.section .envcode,"ax",@progbits
	.globl	_start
_start:
	set.rb	rb1, ENV_STACK

	@@ 权限准备（在 .envperm；row = 3 = hypv 行，deleg = 0）
	set.rb	rb3, hmon_body
	set.rb	rb9, env_perm_prep
	jump	[rb9, rd0, 0]

hmon_body:
	set.rb	rb6, ENV_TAIL
	set.rb	rb2, ENV_BODY_SRC
	jump	[rb2, rd0, 0]

	.section .envperm,"ax",@progbits
	.globl	env_perm_prep
env_perm_prep:
	ENV_PERM_PREP 3, 0
	jump	[rb3, rd0, 0]

	.globl	env_perm_restore
env_perm_restore:
	ENV_PERM_RESTORE_PREP 3, 0
	jump	[rb3, rd0, 0]

	.section .envtail,"ax",@progbits
	.globl	env_finish
env_finish:
	@@ 还原权限准备（仍在本模式 ⇒ 直接写回并回读校验）
	set.rb	rb3, hmon_dump
	set.rb	rb9, env_perm_restore
	jump	[rb9, rd0, 0]

hmon_dump:
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
