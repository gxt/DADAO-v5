@@ m5_perm_mask_cfxperm.S — M5 L3 execution vector: cfx cfxtrap mask forbidden => CFXPERM (TESTCASES-033t).
@@
@@ Capability / permission counter-example: a general `trap` to a *legal but
@@ denied* cfx raises CFXPERM.  DADAO-12 §3 (cfxtrap source mask, 1 = masked);
@@ DADAO-12 §5 / ADR-0045 D6 (permission denial => CFXPERM, current-mode monitor).
@@
@@ m16-testcases-017 (用户 2026-11-23)：执行环境起点改为 **cfx_hmon（源 cfx 3）**
@@ 且 J 模式不纳入 M16 ⇒ 本向量不再拿 `cfx_jmon` 当反例（它的缺省掩码对源 cfx3
@@ 是允许的），改为**自己把 `cfx_smon`（cfxha 2）hypv 行的 `cfxtrap` 源掩码
@@ bit3（源 cfx_hmon）置 1**，再 `trap cfx_smon, 0` ⇒ CFXPERM。
@@ 写掩码这一步本身合法：目标 cfx_smon 的 hypv 行 `cfxreg` 掩码 bit3 = 0。
@@
@@ The body runs in hypv, so CFXPERM is delivered to hypv's current-mode monitor
@@ (cfx_hmon), which records the cause in the profile fault-record slot and
@@ resumes after the faulting instruction (TESTCASES-092t §3/§4); the vector
@@ then reads that slot.
@@
@@ Expected: the whole 64-bit `excp_cause_id` == CFXPERM (0x80) — the flat
@@   bitmap has exactly one bit and `[39]` is deleted, so nothing is masked
@@   (contract-see §6.1/§6.1.1; ADR-0062 D1/D3) — and `excp_cause_info` ==
@@   `excp_cause_ip` (the triggering instruction address; ADR-0062 D4, ISS-469),
@@   read from this frame's `cfx_hmon cg5 rc3`/`rc4` after the resume.
@@   host $? = 0x21 (SYS_EXIT pass token).

@@ @m5 name=m5_perm_mask_cfxperm
@@ @m5 kind=permission
@@ @m5 rule=target_cfxtrap_denied
@@ @m5 cause=CFXPERM
@@ @m5 op=trap cfx_smon, 0 (mask bit3 set by this vector first)
@@ @m5 exit=0x21
@@ @m5 fail_exit=0x71


	.text
	.globl	_start
_start:
	@@ cfx_smon (cfxha 2) hypv 行 cfxtrap 掩码：置 bit3 = 拒绝源 cfx_hmon(3)
	cfx2rd	cfx_smon, cg3, rc0, rd6
	set.rd	rd7, 0x0000000000000008
	or.o	rd6, rd6, rd7
	cfx2rc	cfx_smon, cg3, rc0, rd6

	@@ legal cfxha (smon = 2) but its cfxtrap source bit 3 is now set -> CFXPERM
	trap	cfx_smon, 0
	set.rb rb4, FAULT_RECORD
	ld.o	rd10, [rb4, 0]			@@ fault-record[0] = whole cause id
	set.zw	rd12, wp0, 0x0080		@@ CFXPERM alone (no [39], no bitmap bit)
	cmp.so	rd11, rd10, rd12
	br.nz	{rd11}?, [rb0, fail]

	@@ ADR-0062 D4 / ISS-469: cause_info = the triggering instruction address,
	@@ i.e. the same value as excp_cause_ip (both in this frame's cg5).
	cfx2rd	cfx_hmon, cg5, rc4, rd14	@@ excp_cause_info
	cfx2rd	cfx_hmon, cg5, rc3, rd15	@@ excp_cause_ip
	cmp.so	rd11, rd14, rd15
	br.nz	{rd11}?, [rb0, fail]

	@@ pass: SYS_EXIT(0x21)
	set.rb rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0021
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0

fail:
	set.rb rb16, ENTRY + 0x2000
	set.zw	rd8, wp1, 0x0002
	or.w	rd8, wp0, 0x0026
	st.o	rd8, [rb16, 0]
	set.zw	rd9, wp0, 0x0071
	st.o	rd9, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_umon, 0x3FF00
	swym	0
