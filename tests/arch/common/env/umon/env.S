@@ tests/arch/common/env/umon/env.S — umon（user）运行模式环境（m16-testcases-015）
@@
@@ 进入：环境在 profile ENTRY 处仍以 hypv 运行（step5 BootROM 交付），把
@@ cfx_umon 的 **hypv 行** `switch_run_mode` 写成 user（0），再
@@ `trap cfx_umon, 0`（自身 cfx ⇒ cfx 轴绕过，只按模式行判定）⇒ body 在 **user**
@@ 运行，user 的当前模式监视器为 cfx_umon 自己。
@@
@@ 页权限（为什么本环境要改页表）：step5 BootROM 的 hmon 阶段建立的页表
@@ `HSJU = 0xC`（H=1/S=1，U=0；`tests/ee-vast/hmon_vast.S`），user 取指/访存
@@ 会 `CFXPERM` + `[32] NUPERM`。本环境在 hypv 下把 **L1[3]**（VA/PA
@@ `0x6000_0000`..`0x7fff_ffff`）的 PTE `HSJU` 改成 `0xF`（H/S/U/J 全允许），
@@ 把 body 与 `.envtail` 拷到该区间后再进 user：body 用到的每个页都以 U 允许
@@ 的 TLB 条目首次填充（未被 user 之外的模式先访问过），因此不改
@@ `cfx_ptw`/`cfx_pmem` 也不失效 TLB。
@@
@@ 异常：user 的同步异常进入 cfx_umon 的 **user 行**（cg0）；本环境把
@@ `cg0 rc10` 指到 `env_user_fault`、`cg0 rc8` = hypv（处理程序在 hypv 运行），
@@ 处理程序把 cause / cause_info 记进签名区并以 `0xE0` fail-closed。
@@
@@ 与 body 的契约：`rb1` = 栈指针，`rb6` = 退出例程地址（拷贝后的 `.envtail`）。

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
	.ifndef	ENV_COPY_OCTAS
	.equ	ENV_COPY_OCTAS, 512
	.endif
	.equ	ENV_UCOPY,     0x60000000
	.equ	ENV_UTAIL,     0x60001000
	.equ	ENV_UPAGE_PTE, 0xF00000006000FFEF

	.section .envcode,"ax",@progbits
	.globl	_start
_start:
	set.rb	rb1, ENV_STACK

	@@ 打开 L1[3] 的 U 位：写 PA 0 处的 PTE3（VA 0 + 24，PTBR=0）
	set.rb	rb4, 0
	set.rd	rd6, ENV_UPAGE_PTE
	st.o	rd6, [rb4, 24]

	@@ 把 body + .envtail 拷进 U 页（源 = 紧随 env 之后的镜像区间）
	set.rb	rb4, ENV_BODY_SRC
	set.rb	rb5, ENV_UCOPY
	set.rd	rd6, ENV_COPY_OCTAS
umon_copy:
	ld.o	rd7, [rb4, 0]
	st.o	rd7, [rb5, 0]
	add.si	rb4, 8
	add.si	rb5, 8
	add.si	rd6, -1
	br.nz	{rd6}?, [rb0, umon_copy]

	@@ user 的同步异常 -> cfx_umon 的 user 向量（处理程序在 hypv 运行）
	set.rb	rb2, env_user_fault
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_umon, cg0, rc10, rd6
	set.rd	rd6, 3
	cfx2rc	cfx_umon, cg0, rc8, rd6

	@@ hypv -> user：cfx_umon 的 hypv 行 switch_run_mode = 0
	set.rb	rb6, ENV_UTAIL
	set.rd	rd6, ENV_UCOPY
	cfx2rc	cfx_umon, cg3, rc10, rd6
	set.rd	rd6, 0
	cfx2rc	cfx_umon, cg3, rc8, rd6
	trap	cfx_umon, 0
	swym	0

	@@ user 同步异常（在 hypv 运行）：记 cause / info 并以 0xE0 fail-closed
env_user_fault:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS
	cfx2rd	cfx_umon, cg5, rc2, rd5
	SIGUPD	rd5
	cfx2rd	cfx_umon, cg5, rc4, rd6
	SIGUPD	rd6
	set.rd	rd9, 0xE0
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
