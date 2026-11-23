@@ tests/arch/common/env/cfx_perm.inc — cfx 访问权限准备 / 收窄（m16-testcases-017）
@@
@@ 由 `common/env/{hmon,smon,umon}/env.S` 各自 `.include` 一次；驱动给 llvm-mc 传
@@ `-I tests/arch/common/env`（llvm-mc **不搜索源文件所在目录**）。
@@
@@ 用法（每个 env 在 `.envperm` 段里各写三行入口）：
@@
@@     .section .envperm,"ax",@progbits
@@     env_perm_prep:      ENV_PERM_PREP <row>, <deleg>       ; jump [rb3, rd0, 0]
@@     env_perm_restore:   ENV_PERM_RESTORE_PREP <row>, <deleg> ; jump [rb3, rd0, 0]
@@
@@   `<row>` = 目标模式行（hmon 3 / smon 2 / umon 0，`DADAO-12 §3.1`–`§3.4`）；
@@   `<deleg>` = 1 时也处理 `cg_reg_deleg`（只有 supv 侧需要；user 下访问 cg3 按
@@   寄存器组合规则报 `CFXREG`，故 umon 传 0）。
@@   调用方用 `set.rb rb3, <返回标签>; set.rb rb9, env_perm_prep; jump [rb9, rd0, 0]`。
@@   这两段只在 **hypv** 跑（降模式之前准备、回到 hypv 之后还原），故放在
@@   `.envperm`（`ENTRY + 0x4000`），不挤占 `.envcode`/`.envtail` 的 4 KiB 窗口。
@@
@@ 掩码语义（本文件不另立口径）：
@@   * 目标 cfx 的 `cg<row> rc0`–`rc3` = `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe`
@@     来源掩码，**位索引 = 源 cfx**，0 = 允许、1 = 屏蔽；缺省
@@     `0xFFFF_FFFF_FFFF_FFF7`（只允许源 `cfx_hmon` = 3）。
@@   * 本测试链的源 cfx **就是 cfx_hmon(3)** ⇒ 缺省即允许；「权限准备」因此做两件：
@@       ① **声明**的 cfx：把源 cfx 位清 0（可验证的幂等写）+ 打开 `cg_reg_deleg`；
@@       ② **未声明**的 cfx：把源 cfx 位置 1（fail-closed ⇒ 未声明访问 `CFXPERM`）。
@@     两者都保存原值、写后**回读校验**；任何不符 ⇒ `0xE2` fail-closed。
@@   * 还原只针对①（打开的声明项）：收窄项不还原——镜像随后 `SYS_EXIT`，
@@     掩码不跨镜像持久（见 `README.md`）。
@@   * 豁免：`cfx_hmon`(3) 目标 = 源 ⇒ self 绕过，收窄无意义（不产码）；`cfx_umon`(0)
@@     的 `rc0`（`cfxtrap`）保持打开 —— 环境自用（supv 下显式 `trap cfx_umon` 的
@@     fail-closed 回落要能进 cfx_umon 的 supv 行）。
@@
@@ 交付契约（驱动侧）：声明了 cfx<N> ⇒ `--defsym ENV_CFX_ACCESS_<N>=1`。

	.equ	ENV_PERM_ALLOW, 0xFFFFFFFFFFFFFFF7	@@ 打开：只清源 cfx（cfx_hmon）位
	.equ	ENV_PERM_DENY,  0x0000000000000008	@@ 收窄：把源 cfx 位 1
	.equ	ENV_PERM_DELEG, 0x0000000000000008	@@ deleg 整组开放（唯一置位为恒 1 的 bit3）
	.equ	ENV_PERM_SENT,  0xDEADBEEF0BADF00D	@@ 回读哨兵（读被拒时保留）
	.equ	ENV_PERM_FAIL,  0xE2			@@ 权限准备失败（fail-closed）
	.ifndef	ENV_PERM_SAVE
	.equ	ENV_PERM_SAVE, ENV_SIG_BUF + 0x1000	@@ 打开项原值（9 cfx × 40 B）
	.endif
	.equ	ENV_PERM_VEC_SLOT,    ENV_PERM_SAVE + 0x170	@@ cfx_hmon.hypv.excp_vector 保存槽
	.equ	ENV_PERM_NARROW_SAVE, ENV_PERM_SAVE + 0x200	@@ 收窄项原值（8 cfx × 32 B）

	@@ 声明的 cfx 个数（汇编期求值）
	.set	__perm_declared, 0
	.ifdef	ENV_CFX_ACCESS_0
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_2
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_3
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_4
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_5
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_15
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_32
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_34
	.set	__perm_declared, __perm_declared + 1
	.endif
	.ifdef	ENV_CFX_ACCESS_63
	.set	__perm_declared, __perm_declared + 1
	.endif

@@ == 打开（声明的 cfx）====================================================
@@ 一类来源掩码：保存原值 → 清源 cfx 位写回 → 回读校验
.macro	ENV_PERM_OPEN_RC name, ha, row, rc, idx
	set.rd	rd5, ENV_PERM_SENT
	cfx2rd	\name, cg\row, \rc, rd5
	st.o	rd5, [rb7, 8 * \idx]
	set.rd	rd9, ENV_PERM_ALLOW
	and.o	rd5, rd5, rd9
	cfx2rc	\name, cg\row, \rc, rd5
	set.rd	rd6, ENV_PERM_SENT
	cfx2rd	\name, cg\row, \rc, rd6
	cmp.uo	rd10, rd6, rd5
	br.z	{rd10}?, [rb0, __perm_ok_\@]
	set.rd	rd11, \ha
	set.rd	rd12, ((\row << 8) | \idx)
	jump	[rb0, env_perm_fail]
__perm_ok_\@:
.endm

@@ cg_reg_deleg：supv 访问该 cfx 的任一 cg 的前提
.macro	ENV_PERM_OPEN_DELEG name, ha
	set.rd	rd5, ENV_PERM_SENT
	cfx2rd	\name, cg3, rc12, rd5
	st.o	rd5, [rb7, 32]
	set.rd	rd9, ENV_PERM_DELEG
	cfx2rc	\name, cg3, rc12, rd9
	set.rd	rd6, ENV_PERM_SENT
	cfx2rd	\name, cg3, rc12, rd6
	cmp.uo	rd10, rd6, rd9
	br.z	{rd10}?, [rb0, __perm_ok_\@]
	set.rd	rd11, \ha
	set.rd	rd12, (0x030C)			@@ row = 3（cg3）rc = 12
	jump	[rb0, env_perm_fail]
__perm_ok_\@:
.endm

.macro	ENV_PERM_OPEN name, ha, row, deleg
	ENV_PERM_OPEN_RC \name, \ha, \row, rc0, 0
	ENV_PERM_OPEN_RC \name, \ha, \row, rc1, 1
	ENV_PERM_OPEN_RC \name, \ha, \row, rc2, 2
	ENV_PERM_OPEN_RC \name, \ha, \row, rc3, 3
	.if	\deleg
	ENV_PERM_OPEN_DELEG \name, \ha
	.else
	add.si	rb7, 8
	.endif
	add.si	rb7, 32
.endm

@@ == 收窄（未声明的 cfx，fail-closed）=====================================
@@ 一类来源掩码：保存原值 → 置源 cfx 位写回 → 回读校验（rd12 bit13 = 收窄阶段）
.macro	ENV_PERM_NARROW_RC name, ha, row, rc, idx
	set.rd	rd5, ENV_PERM_SENT
	cfx2rd	\name, cg\row, \rc, rd5
	st.o	rd5, [rb7, 8 * \idx]
	set.rd	rd9, ENV_PERM_DENY
	or.o	rd5, rd5, rd9
	cfx2rc	\name, cg\row, \rc, rd5
	set.rd	rd6, ENV_PERM_SENT
	cfx2rd	\name, cg\row, \rc, rd6
	cmp.uo	rd10, rd6, rd5
	br.z	{rd10}?, [rb0, __perm_ok_\@]
	set.rd	rd11, \ha
	set.rd	rd12, (0x2000 | ((\row << 8) | \idx))
	jump	[rb0, env_perm_fail]
__perm_ok_\@:
.endm

@@ `cfxreg`（rc2）必须**最后**写且**不读回**：它一封，本环境的源 cfx 就再也读不到
@@ 该 cfx 的任何寄存器（self-lockout），回读校验必然失败。其余三类（trap/mem/exe）
@@ 不影响 `cfx2rd`/`cfx2rc`，照常回读校验。
.macro	ENV_PERM_NARROW_REG name, ha, row
	set.rd	rd5, ENV_PERM_SENT
	cfx2rd	\name, cg\row, rc2, rd5
	st.o	rd5, [rb7, 16]
	set.rd	rd9, ENV_PERM_DENY
	or.o	rd5, rd5, rd9
	cfx2rc	\name, cg\row, rc2, rd5
.endm

.macro	ENV_PERM_NARROW name, ha, row, keep_trap
	.if	\keep_trap
	add.si	rb7, 8			@@ rc0（cfxtrap）留给环境自用
	.else
	ENV_PERM_NARROW_RC \name, \ha, \row, rc0, 0
	.endif
	ENV_PERM_NARROW_RC \name, \ha, \row, rc1, 1
	ENV_PERM_NARROW_RC \name, \ha, \row, rc3, 3
	ENV_PERM_NARROW_REG \name, \ha, \row
	add.si	rb7, 8
.endm

@@ == 还原（打开的声明项）=================================================
.macro	ENV_PERM_RESTORE_RC name, ha, row, rc, idx
	ld.o	rd5, [rb7, 8 * \idx]
	cfx2rc	\name, cg\row, \rc, rd5
	set.rd	rd6, ENV_PERM_SENT
	cfx2rd	\name, cg\row, \rc, rd6
	cmp.uo	rd10, rd6, rd5
	br.z	{rd10}?, [rb0, __perm_ok_\@]
	set.rd	rd11, \ha
	set.rd	rd12, (0x1000 | ((\row << 8) | \idx))
	jump	[rb0, env_perm_fail]
__perm_ok_\@:
.endm

.macro	ENV_PERM_RESTORE_DELEG name, ha
	ld.o	rd5, [rb7, 32]
	cfx2rc	\name, cg3, rc12, rd5
	set.rd	rd6, ENV_PERM_SENT
	cfx2rd	\name, cg3, rc12, rd6
	cmp.uo	rd10, rd6, rd5
	br.z	{rd10}?, [rb0, __perm_ok_\@]
	set.rd	rd11, \ha
	set.rd	rd12, (0x130C)
	jump	[rb0, env_perm_fail]
__perm_ok_\@:
.endm

.macro	ENV_PERM_RESTORE name, ha, row, deleg
	ENV_PERM_RESTORE_RC \name, \ha, \row, rc0, 0
	ENV_PERM_RESTORE_RC \name, \ha, \row, rc1, 1
	ENV_PERM_RESTORE_RC \name, \ha, \row, rc2, 2
	ENV_PERM_RESTORE_RC \name, \ha, \row, rc3, 3
	.if	\deleg
	ENV_PERM_RESTORE_DELEG \name, \ha
	.else
	add.si	rb7, 8
	.endif
	add.si	rb7, 32
.endm

@@ == 按声明 / 未声明逐个处理 ==============================================
.macro	ENV_PERM_OPEN_ALL row, deleg
	set.rb	rb7, ENV_PERM_SAVE
	.ifdef	ENV_CFX_ACCESS_0
	ENV_PERM_OPEN cfx0, 0, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_2
	ENV_PERM_OPEN cfx2, 2, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_3
	ENV_PERM_OPEN cfx3, 3, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_4
	ENV_PERM_OPEN cfx4, 4, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_5
	ENV_PERM_OPEN cfx5, 5, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_15
	ENV_PERM_OPEN cfx15, 15, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_32
	ENV_PERM_OPEN cfx32, 32, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_34
	ENV_PERM_OPEN cfx34, 34, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_63
	ENV_PERM_OPEN cfx63, 63, \row, \deleg
	.endif
.endm

@@ 未声明的 arch cfx 一律收窄（cfx_hmon 是源 cfx 本身 ⇒ 跳过；cfx_umon 的 rc0 留用）
.macro	ENV_PERM_NARROW_ALL row
	set.rb	rb7, ENV_PERM_NARROW_SAVE
	.ifndef	ENV_CFX_ACCESS_0
	ENV_PERM_NARROW cfx0, 0, \row, 1
	.endif
	.ifndef	ENV_CFX_ACCESS_2
	ENV_PERM_NARROW cfx2, 2, \row, 0
	.endif
	.ifndef	ENV_CFX_ACCESS_4
	ENV_PERM_NARROW cfx4, 4, \row, 0
	.endif
	.ifndef	ENV_CFX_ACCESS_5
	ENV_PERM_NARROW cfx5, 5, \row, 0
	.endif
	.ifndef	ENV_CFX_ACCESS_15
	ENV_PERM_NARROW cfx15, 15, \row, 0
	.endif
	.ifndef	ENV_CFX_ACCESS_32
	ENV_PERM_NARROW cfx32, 32, \row, 0
	.endif
	.ifndef	ENV_CFX_ACCESS_34
	ENV_PERM_NARROW cfx34, 34, \row, 0
	.endif
	.ifndef	ENV_CFX_ACCESS_63
	ENV_PERM_NARROW cfx63, 63, \row, 0
	.endif
.endm

.macro	ENV_PERM_RESTORE_ALL row, deleg
	set.rb	rb7, ENV_PERM_SAVE
	.ifdef	ENV_CFX_ACCESS_0
	ENV_PERM_RESTORE cfx0, 0, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_2
	ENV_PERM_RESTORE cfx2, 2, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_3
	ENV_PERM_RESTORE cfx3, 3, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_4
	ENV_PERM_RESTORE cfx4, 4, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_5
	ENV_PERM_RESTORE cfx5, 5, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_15
	ENV_PERM_RESTORE cfx15, 15, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_32
	ENV_PERM_RESTORE cfx32, 32, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_34
	ENV_PERM_RESTORE cfx34, 34, \row, \deleg
	.endif
	.ifdef	ENV_CFX_ACCESS_63
	ENV_PERM_RESTORE cfx63, 63, \row, \deleg
	.endif
.endm

@@ == 组合入口 ============================================================
@@ 准备：先打开声明的，再把未声明的收窄（fail-closed）
.macro	ENV_PERM_PREP row, deleg
	.if	__perm_declared > 0
	ENV_PERM_OPEN_ALL \row, \deleg
	.endif
	ENV_PERM_NARROW_ALL \row
.endm

@@ 还原：只还原打开的声明项（收窄项不还原，见文件头）
.macro	ENV_PERM_RESTORE_PREP row, deleg
	.if	__perm_declared > 0
	ENV_PERM_RESTORE_ALL \row, \deleg
	.endif
.endm

@@ == 失败处理 =============================================================
@@ 记 (cfxha, row/rc/phase, 预期, 实测) 后以 0xE2 退出。两段权限代码都只在 hypv
@@ 运行 ⇒ 失败处理也放 `.envperm`（可达，且不挤占 4 KiB 窗口）。
	.section .envperm,"ax",@progbits
	.globl	env_perm_fail
env_perm_fail:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS
	SIGUPD	rd11
	SIGUPD	rd12
	SIGUPD	rd5
	SIGUPD	rd6
	SIG_DUMP_CHARS ENV_SIG_BUF, ENV_SIG_SLOTS
	set.rd	rd9, ENV_PERM_FAIL
	jump	[rb0, env_exit_code]
