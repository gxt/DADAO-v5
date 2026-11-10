@@ tiny_hmon_handler.S — Machine-v5-Tiny 分派 hmon 段（m13-gem5-005）
@@
@@ 规范：spec/Machine-v5 §6.2 第 7 步（移交返回）+ §2（Tiny 恒 hypv）+
@@       §4.4（五类同步异常进 hmon 向量）；spec/DADAO-12 §5.1–§5.3
@@       （trap 进入 / escape 退出）；spec/DADAO-13 §1–§2（cg3/cg5）。
@@
@@ 位置：BootROM 镜像偏移 0x2000–0x3FFF（上限 8 KiB），链接在 hmon SRAM 起始
@@ 0x0fff_0000_0000；段首即 hmon 入口 = 异常向量初值（DADAO-13 §1）。
@@ 由 `build_tiny_bootrom.py` 与共享 power stub 一起装进 64 KiB 镜像；宿主
@@ loader 只装应用 ELF（§6.2）。
@@
@@ 入口分派（先固定三读现场，再按 cause 走）：
@@   1. mailbox = handler 入口 PC（应用用它记录移交帧的 handler PC）；
@@   2. 三读 cfx_hmon cg5 rc2/rc3/rc4 = excp_cause_id / ip / info；
@@   3. CFXTRAP（1 << 0）：校验 cause_info 的 immu18 = 表头 boot_magic
@@      （§6.1）；相等 ⇒ `escape +4` 回 power stub（移交路径，不记结果）；
@@      不等 ⇒ 记一条结果记录后同样 `escape +4`（诊断用）；
@@   4. 其余（同步异常）：记一条 {cause_id, cause_ip, cause_info, handler PC}
@@      结果记录；IALIGN（1 << 13）把 excp_cause_ip 改写为数据区 RECOVERY
@@      （应用给出的恢复地址）后 `escape 0`，其余 `escape +4`（跳过触发指令，
@@      精确异常 ⇒ 该指令不写回、不访存）；
@@   5. PROBE 非 0 时（应用在 Tiny 恒 hypv 用例里置 1）：清 PROBE，读一次
@@      cg3 rc10（hypv-only，DADAO-13 §1）并按 check id 37 记一条检查记录，
@@      证明异常进入后仍在 hypv。
@@ 被改写（clobber）的寄存器：rd4/rd10–rd16、rb4/rb5/rb7、rb20。

	.include "machine.inc"
	.include "machine-tiny.inc"
	.include "tiny_hmon_layout.inc"

	.text
	.globl	hmon_entry
hmon_entry:
	@@ mailbox = handler 入口 PC（rb0 = 当前 IP，只读）
	rb2rd	rd4, rb0, 1
	LOAD_ADDR rb4, MAILBOX
	st.o	rd4, [rb4, 0]

	@@ 现场三读（顺序固定，诊断日志据此逐次给出）
	cfx2rd	cfx_hmon, cg5, rc2, rd10	@@ excp_cause_id
	cfx2rd	cfx_hmon, cg5, rc3, rd11	@@ excp_cause_ip
	cfx2rd	cfx_hmon, cg5, rc4, rd12	@@ excp_cause_info

	@@ CFXTRAP（1 << 0）?  是 ⇒ 校验 magic，不是 ⇒ 记结果记录
	set.zw	rd13, wp0, 0x0001
	cmp.so	rd14, rd10, rd13
	br.nz	{rd14}?, [rb0, hmon_record]

	set.zw	rd15, wp0, 0xffff		@@ 0x0003_ffff（immu18 掩码）
	or.w	rd15, wp1, 0x0003
	and.o	rd15, rd12, rd15
	set.zw	rd16, wp0, 0x0001		@@ 0x0003_0001（boot_magic）
	or.w	rd16, wp1, 0x0003
	cmp.uo	rd14, rd15, rd16
	br.nz	{rd14}?, [rb0, hmon_record]	@@ magic 不符 ⇒ 记诊断记录

	@@ 移交：跳过 power stub 的 trap 指令（+4，DADAO-12 §5.3）
	escape	cfx_hmon, [excp_cause_ip, 4]

@@ ---------------------------------------------------------------------------
@@ hmon_record: 记 {cause_id, cause_ip, cause_info, handler PC} 到结果槽。
@@ IALIGN 的 cause_ip 是非法 IP 本身（§4.4）：改用应用的恢复地址 escape 0。
@@ ---------------------------------------------------------------------------
hmon_record:
	LOAD_ADDR rb4, SLOT_PTR
	ld.o	rb5, [rb4, 0]
	st.o	rd10, [rb5, 0]
	st.o	rd11, [rb5, 8]
	st.o	rd12, [rb5, 16]
	st.o	rd4, [rb5, 24]			@@ handler PC（入口处由 rb0 捕获）
	add.si	rb5, 32
	st.o	rb5, [rb4, 0]

	set.zw	rd13, wp0, 0x2000		@@ IALIGN（1 << 13）
	cmp.so	rd14, rd10, rd13
	br.nz	{rd14}?, [rb0, hmon_probe]

	LOAD_ADDR rb7, RECOVERY
	ld.o	rd15, [rb7, 0]
	cfx2rc	cfx_hmon, cg5, rc3, rd15	@@ excp_cause_ip = 恢复地址
	escape	cfx_hmon, [excp_cause_ip, 0]

@@ ---------------------------------------------------------------------------
@@ hmon_probe: PROBE 非 0 ⇒ 在异常上下文里读一次 cg3 并记 check id 37。
@@ ---------------------------------------------------------------------------
hmon_probe:
	LOAD_ADDR rb4, PROBE
	ld.o	rd15, [rb4, 0]
	cmp.so	rd16, rd15, rd0
	br.z	{rd16}?, [rb0, hmon_escape4]	@@ PROBE == 0 ⇒ 直接返回

	set.zw	rd14, wp0, 0			@@ 清 PROBE（只探一次）
	st.o	rd14, [rb4, 0]
	cfx2rd	cfx_hmon, cg3, rc10, rd10	@@ excp_vector（hypv-only）
	LOAD_ADDR rd11, HMON_BASE
	set.zw	rd12, wp0, 0x0025		@@ check id 37
	LOAD_ADDR rb20, RECORD_CHECK
	call	[rb20, rd0, 0]

hmon_escape4:
	escape	cfx_hmon, [excp_cause_ip, 4]
