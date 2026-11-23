@@ tests/arch/common/env-smon/env.S — smon（supv）运行模式环境（m16-testcases-015/017）
@@
@@ 进入：镜像由 step5 BootROM 的 hmon 阶段**直接跳转**交付（m16-testcases-017），
@@ 故环境在 ENTRY 处就以 **cfx_hmon（源 cfx = 3）**、hypv 运行；cfx_hmon 的 hypv
@@ 向量仍是固件入口 ⇒ body 的同步异常仍由 `hmon_fault` 记录并按 policy 恢复。
@@
@@ 降模式：把 **cfx_hmon** 的 hypv 行 `switch_run_mode` 写成 supv（2）、
@@ `excp_vector` 写成 `env_supv_entry`，再 `trap cfx_hmon, 0`（目标 = 自身 cfx
@@ ⇒ 源 cfx 保持 3）⇒ 硬件按该行切换运行模式，body 在 **supv** 运行，supv 的
@@ 当前模式监视器为 cfx_smon。
@@
@@ 异常：step5 测试链不装载 cfx_smon，故 supv 下的**同步异常不可依赖**（显式
@@ 限制，见 `README.md`「已知限制」）。body 显式 `trap cfx_umon, immu18` 走
@@ cfx_umon 的 supv 行，本环境把它指到 `env_supv_fault`（在 hypv 运行），记
@@ cause 后以 `0xE1` fail-closed。
@@
@@ 收尾：body 跳到 `rb6`（`.envtail` 的 `env_finish`）⇒ 用 **cfx_hmon 的 supv 行**
@@ 回到 hypv 的 `env_hypv_return`，在那里还原权限准备（supv 侧 `cg3` 恒拒，
@@ `cg_reg_deleg` 只能在 hypv 还原）、还原固件的 hypv 向量，再输出签名并退出。
@@
@@ 权限（见 `cfx_perm.inc`）：在**降模式之前**（仍 hypv）按 `cfx_access` 打开目标
@@ cfx 的 **supv 行**四类来源掩码与 `cg_reg_deleg`；未声明的 arch cfx 一律
@@ **收窄**（未声明访问 ⇒ `CFXPERM`）。回读不符 ⇒ `0xE2` fail-closed。
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

	@@ 权限准备 / 收窄的宏与失败处理（依赖上面的 ENV_SIG_* 与 `-I` 传的 env 目录）
	.include "cfx_perm.inc"

	.section .envcode,"ax",@progbits
	.globl	_start
_start:
	set.rb	rb1, ENV_STACK

	@@ 保存固件的 cfx_hmon.hypv 向量：降模式会临时改成 env_supv_entry
	cfx2rd	cfx_hmon, cg3, rc10, rd5
	set.rb	rb7, ENV_PERM_VEC_SLOT
	st.o	rd5, [rb7, 0]

	@@ 权限准备（在 .envperm；row = 2 = supv 行，deleg = 1：supv 访问 cg 要它）
	set.rb	rb3, smon_vectors
	set.rb	rb9, env_perm_prep
	jump	[rb9, rd0, 0]

smon_vectors:
	@@ supv 下显式 trap cfx_umon 的回落：cfx_umon 的 supv 行 -> env_supv_fault
	set.rb	rb2, env_supv_fault
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_umon, cg2, rc10, rd6
	set.rd	rd6, 3
	cfx2rc	cfx_umon, cg2, rc8, rd6

	@@ 正常收尾：cfx_hmon 的 supv 行 -> env_hypv_return（回到 hypv 还原）
	set.rb	rb2, env_hypv_return
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_hmon, cg2, rc10, rd6
	set.rd	rd6, 3
	cfx2rc	cfx_hmon, cg2, rc8, rd6

	@@ hypv -> supv：cfx_hmon 的 hypv 行 switch_run_mode = 2、向量 = env_supv_entry
	set.rb	rb2, env_supv_entry
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_hmon, cg3, rc10, rd6
	set.rd	rd6, 2
	cfx2rc	cfx_hmon, cg3, rc8, rd6
	trap	cfx_hmon, 0
	swym	0

env_supv_entry:
	set.rb	rb1, ENV_STACK
	set.rb	rb6, ENV_TAIL
	set.rb	rb2, ENV_BODY_SRC
	jump	[rb2, rd0, 0]

	@@ supv 下显式 trap 的回落（在 hypv 运行）：记 cause 并以 0xE1 fail-closed
env_supv_fault:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	SIGUPD	rd5
	SIG_DUMP_CHARS ENV_SIG_BUF, ENV_SIG_SLOTS
	set.rd	rd9, 0xE1
	jump	[rb0, env_exit_code]

	@@ 正常收尾（由 supv 经 cfx_hmon 的 supv 行回到 hypv）：还原后输出并退出
env_hypv_return:
	@@ 还原固件的 cfx_hmon.hypv 向量
	set.rb	rb7, ENV_PERM_VEC_SLOT
	ld.o	rd6, [rb7, 0]
	cfx2rc	cfx_hmon, cg3, rc10, rd6

	@@ 还原权限准备（在 hypv 才能写回 cg3 deleg；回读校验）
	set.rb	rb3, env_smon_dump
	set.rb	rb9, env_perm_restore
	jump	[rb9, rd0, 0]

env_smon_dump:
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

	.section .envperm,"ax",@progbits
	.globl	env_perm_prep
env_perm_prep:
	ENV_PERM_PREP 2, 1
	jump	[rb3, rd0, 0]

	.globl	env_perm_restore
env_perm_restore:
	ENV_PERM_RESTORE_PREP 2, 1
	jump	[rb3, rd0, 0]

	.section .envtail,"ax",@progbits
	@@ body 跳到 rb6 后先回 hypv 收尾（本模式不拷贝 .envtail）
	.globl	env_finish
env_finish:
	trap	cfx_hmon, 0
	swym	0
