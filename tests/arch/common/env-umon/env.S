@@ tests/arch/common/env-umon/env.S — umon（user）运行模式环境（m16-testcases-015/017）
@@
@@ 进入：镜像由 step5 BootROM 的 hmon 阶段**直接跳转**交付（m16-testcases-017），
@@ 故环境在 ENTRY 处就以 **cfx_hmon（源 cfx = 3）**、hypv 运行。
@@
@@ 页权限（为什么本环境要改页表）：step5 BootROM 的 hmon 阶段建立的页表
@@ `HSJU = 0xC`（H=1/S=1，U=0；`tests/ee-vast/hmon_vast.S`），user 取指/访存
@@ 会 `CFXPERM` + `[32] NUPERM`。本环境在 hypv 下把 **L1[3]**（VA/PA
@@ `0x6000_0000`..`0x7fff_ffff`）的 PTE `HSJU` 改成 `0xF`（H/S/U/J 全允许），
@@ 把 body 与 `.envtail` 拷到该区间后再进 user：body 用到的每个页都以 U 允许
@@ 的 TLB 条目首次填充（未被 user 之外的模式先访问过），因此不改
@@ `cfx_ptw`/`cfx_pmem` 也不失效 TLB。
@@
@@ 降模式：把 **cfx_hmon** 的 hypv 行 `switch_run_mode` 写成 user（0）、
@@ `excp_vector` 写成 `ENV_UCOPY`，再 `trap cfx_hmon, 0`（目标 = 自身 cfx ⇒
@@ 源 cfx 保持 3）⇒ body 在 **user** 运行，user 的当前模式监视器为 cfx_umon。
@@
@@ 异常：user 的同步异常进入 cfx_umon 的 **user 行**（cg0）；本环境把
@@ `cg0 rc10` 指到 `env_user_fault`、`cg0 rc8` = hypv（处理程序在 hypv 运行），
@@ 处理程序把 cause / cause_info 记进签名区并以 `0xE0` fail-closed。
@@
@@ 权限（见 `cfx_perm.inc`）：在**降模式之前**（仍 hypv）按 `cfx_access` 打开目标
@@ cfx 的 **user 行**四类来源掩码；未声明的 arch cfx 一律**收窄**（未声明访问 ⇒
@@ `CFXPERM`）。`cg_reg_deleg` 只约束 supv，且 user 下访问 cg3 按寄存器组合规则
@@ 报 `CFXREG` ⇒ `<deleg>` 传 0（不产码）。
@@
@@ 收尾：body 跳到 `rb6`（被拷到 U 页的 `.envtail`）⇒ 用 **cfx_hmon 的 user 行**
@@ 回到 hypv 的 `env_hypv_return` 做还原（user 下 cg3 不可写，还原统一在 hypv），
@@ 再输出签名并退出。
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
	.ifndef	ENV_UCOPY
	.equ	ENV_UCOPY,     0x60000000
	.endif
	.ifndef	ENV_UTAIL
	.equ	ENV_UTAIL,     0x60001000
	.endif
	@@ 进 user 的跳转目标（缺省 = 拷贝到 U 页的 body 起点）；body 本来就在
	@@ user 可达处（cfx4 载体的 ROM）时由驱动覆写成 body 的真实地址。
	.ifndef	ENV_UENTRY
	.equ	ENV_UENTRY,    ENV_UCOPY
	.endif
	.equ	ENV_UPAGE_PTE, 0xF00000006000FFEF
	@@ L1[3] 的 U 位写进哪张表：缺省 PA 0x18（step5 固件 PTBR=0 的表）；
	@@ 表在别处时由驱动传（`m16-testcases-019`：cfx4 载体的 L1 在 0x7ff0_0000）。
	.ifndef	ENV_UPAGE_PTE_PA
	.equ	ENV_UPAGE_PTE_PA, 0x18
	.endif

	@@ 权限准备 / 收窄的宏与失败处理（依赖上面的 ENV_SIG_* 与 `-I` 传的 env 目录）
	.include "cfx_perm.inc"

	.section .envcode,"ax",@progbits
	.globl	_start
_start:
	set.rb	rb1, ENV_STACK

	@@ 打开 L1[3] 的 U 位：写该表 L1[3] 处（缺省 PA 0x18，即 PTBR=0 的表）
	set.rb	rb4, ENV_UPAGE_PTE_PA - 24
	set.rd	rd6, ENV_UPAGE_PTE
	st.o	rd6, [rb4, 24]

	@@ 改过页表项 ⇒ 丢掉旧转换：hypv 阶段的访存可能已经按旧 HSJU（0xC）填过该页
	@@ 的条目，user 下命中会按条目里的 HSJU 判 ⇒ `[32] NUPERM`。缺省不做（本环境
	@@ 的原始假设是「user 之前没人访问过该页」）；镜像在 hypv 阶段访问过该超页
	@@ 时由驱动传 `ENV_TLB_INVALIDATE=1`（`m16-testcases-019` 的 cfx4 载体）。
	.ifdef	ENV_TLB_INVALIDATE
	set.rd	rd6, 2			@@ op=invalid、scope=all、ASID_ANY=1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.endif

	@@ 把 body + .envtail 拷进 U 页（源 = 紧随 env 之后的镜像区间）。
	@@ `ENV_COPY_OCTAS = 0` 表示 body 已在 U 可达处（cfx4 载体的 body 在 ROM，
	@@ `m16-testcases-019`）⇒ 跳过拷贝（原循环是 do-while，0 会下溢成死循环）。
	set.rb	rb4, ENV_BODY_SRC
	set.rb	rb5, ENV_UCOPY
	set.rd	rd6, ENV_COPY_OCTAS
	br.z	{rd6}?, [rb0, umon_copy_done]
umon_copy:
	ld.o	rd7, [rb4, 0]
	st.o	rd7, [rb5, 0]
	add.si	rb4, 8
	add.si	rb5, 8
	add.si	rd6, -1
	br.nz	{rd6}?, [rb0, umon_copy]
umon_copy_done:

	@@ `cache-model=on`：上面的拷贝是**数据写**，落在 D-cache 的脏行里；user 的
	@@ 取指走真实内存（QEMU/gem5 的取指不经影子/写回），会读到旧内容（0 字 ⇒
	@@ UNDI）。只有声明了 cfx5 的用例（`ENV_CFX_ACCESS_5`）才在这里整侧
	@@ `D|flush|all`（CACHE-09：bit14 = D、`[1:0] = 11` = flush、`[3:2] = 00` = all）
	@@ 把 body 与 tail 写回内存；`cache-model=off` 时该命令被接受且无效果。
	.ifdef	ENV_CFX_ACCESS_5
	set.rd	rd6, 0x4003
	cfx2rc	cfx_cache, cg8, rc9, rd6
	.endif

	@@ 权限准备（在 .envperm；row = 0 = user 行，deleg = 0）
	set.rb	rb3, umon_vectors
	set.rb	rb9, env_perm_prep
	jump	[rb9, rd0, 0]

umon_vectors:
	@@ user 的同步异常 -> cfx_umon 的 user 行（处理程序在 hypv 运行）
	set.rb	rb2, env_user_fault
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_umon, cg0, rc10, rd6
	set.rd	rd6, 3
	cfx2rc	cfx_umon, cg0, rc8, rd6

	@@ 正常收尾：cfx_hmon 的 user 行 -> env_hypv_return（回到 hypv 还原）
	set.rb	rb2, env_hypv_return
	rb2rd	rd6, rb2, 1
	cfx2rc	cfx_hmon, cg0, rc10, rd6
	set.rd	rd6, 3
	cfx2rc	cfx_hmon, cg0, rc8, rd6

	@@ hypv -> user：cfx_hmon 的 hypv 行 switch_run_mode = 0、向量 = ENV_UENTRY
	set.rb	rb6, ENV_UTAIL
	set.rd	rd6, ENV_UENTRY
	cfx2rc	cfx_hmon, cg3, rc10, rd6
	set.rd	rd6, 0
	cfx2rc	cfx_hmon, cg3, rc8, rd6
	trap	cfx_hmon, 0
	swym	0

	@@ user 同步异常（在 hypv 运行）：记 cause / info 并以 0xE0 fail-closed
env_user_fault:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS
	cfx2rd	cfx_umon, cg5, rc2, rd5
	SIGUPD	rd5
	cfx2rd	cfx_umon, cg5, rc4, rd6
	SIGUPD	rd6
	SIG_DUMP_CHARS ENV_SIG_BUF, ENV_SIG_SLOTS
	set.rd	rd9, 0xE0
	jump	[rb0, env_exit_code]

	@@ 正常收尾（由 user 经 cfx_hmon 的 user 行回到 hypv）：还原后输出并退出
env_hypv_return:
	set.rb	rb3, env_umon_dump
	set.rb	rb9, env_perm_restore
	jump	[rb9, rd0, 0]

env_umon_dump:
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
	ENV_PERM_PREP 0, 0
	jump	[rb3, rd0, 0]

	.globl	env_perm_restore
env_perm_restore:
	ENV_PERM_RESTORE_PREP 0, 0
	jump	[rb3, rd0, 0]

	.section .envtail,"ax",@progbits
	@@ 本段被拷到 U 页、在 user 下运行：只做「回 hypv 收尾」，不含绝对地址
	.globl	env_finish
env_finish:
	trap	cfx_hmon, 0
	swym	0
