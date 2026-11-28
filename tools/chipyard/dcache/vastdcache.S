@@ vastdcache.S — DADAO D-Cache 探针（`m16-chipyard-009`）
@@
@@ 目的：在 `WumingVastConfig` 上覆盖「8 路 × 128 组 × 64 B、写回 + 写分配、
@@ PTW 走 D-Cache 端口」的语义面。页表几何、PTE 值、数据 magic、组索引与
@@ 全部期望值都由 `tools/chipyard/dcache/gen_vastdcache_tables.py` 独立算出
@@（本文件不含手算的索引/位域）；cause one-hot 从 `contract-see §6.1` 现场解析。
@@
@@   A 命中 / 缺失
@@     r0..r4：同一行连续读 5 次（首次缺失填充、后 4 次命中，日志计数由判据核）
@@
@@   B 8 路同组 + LRU
@@     r5..r12：同组（PA[12:6] = 64）8 条不同 tag 的行各读一次（8 路共存）
@@     r13：re-touch B0（置 MRU）→ r14：L9 填表（淘汰 LRU = B1）
@@     r15：re-touch B7 → r16：L10 填表（淘汰 LRU = B2）
@@     r17：再读 B1 ⇒ 已被淘汰、重填（数据仍是自己的 magic）
@@
@@   C 写回 + 写穿时机（独立观测量 = 取指端口；`m16-chipyard-010` 起取指侧有
@@     I-Cache，因此把写回落地后要先按 LRU 把那条取指行挤出去再跳）
@@     r18：从核内 SRAM 读 8 B 指令字（`trap cfx_hmon, 0` + 占位指令）
@@     r19：把指令字**经 D-Cache 写**到代码页后，跳过去 —— 内存里仍是旧值 0
@@          ⇒ 取指（I-Cache 缺失、读到内存旧值）读到 0（UNDI）→ hmon →
@@          `__pad` 按期望 cause 回到 `dc_resume1`
@@     r20：核内再读同一行 ⇒ 命中、返回**新**值（写后读命中不回内存）
@@     r21：淘汰前再跳一次 —— I-Cache 命中那条旧行，仍读到旧值（UNDI）
@@     r22..r29：同组再填 8 条新行（把代码行按 LRU 淘汰并写回）
@@     IC_EVICT ×8：八条同组、不同 tag 的一行块把**代码行从 I-Cache 里挤出去**
@@     r30：淘汰后再跳 —— I-Cache 缺失、读到内存的 `trap cfx_hmon`（CFXTRAP）
@@          ⇒ 写回已落地
@@     r31：核内再读该行 ⇒ 缺失重填、读回新值
@@
@@   D PTW 端口（页表读经 D-Cache）
@@     r32：读 VA_PAGE ⇒ 旧 PTE 指向 `M_PAGE_OLD`
@@     经自映射页把 L2[7] 的 PTE **经 D-Cache 写**成 `PTE_PAGE_NEW`
@@     `invalid / all` 清 TLB 后重读 ⇒ r33 = `M_PAGE_NEW`（走查读到缓存里的新 PTE）
@@     r34：核内再读该 PTE ⇒ `PTE_PAGE_NEW`（同一行的核/PTW 视角一致）
@@
@@ 断言方式：数据 magic 用 `__CHECK_RD`（不等即 `SYS_EXIT(点号)`）；观测量用
@@ `__REC` 写进结果缓冲，由宿主 `check_vastdcache.py` 逐条与生成器期望比对；
@@ 事件（fill/hit/miss/victim/wb）从仿真日志逐条比对。
@@
@@ 页表与数据由 `+loadmem=` 按 `p_paddr` 装入 PA RAM；探针自身在核内 SRAM
@@（`addr[47:42] ≠ 0`，不经翻译、也不进 D-Cache）。

	.include "tests/inst/macros/inst_test.inc"
	.include "vastdcache_tables.inc"
	.include "tests/shared/asm/perm_hypv.inc"

@@ 期望一次故障并回到 `\resume`：TEST_FAULTV = cause，失败码 = 点号（= 槽索引）。
.macro EXPECT_FAULT cause, point, resume
	set.rb	rb11, TEST_FAULTV
	set.rd	rd20, \cause
	st.o	rd20, [rb11, 0]
	set.rd	rd20, \point
	st.o	rd20, [rb11, 8]
	set.rb	rb21, (FAULTTAB + 8)
	set.rd	rd20, \point
	shl.o	rd20, rd20, 3
	add.o	rb21, rb21, rd20
	set.rb	rb22, \resume
	st.o	rb22, [rb21, 0]
	set.rb	rb4, VA_CODE
	jump	[rb4, rd0, 0]
.endm

@@ m16-chipyard-010：把代码行从 **I-Cache** 里按 LRU 挤出去。
@@   每个淘汰块 = 一行（64 B），首条指令 `jump [rb10, rd0, 0]` 直接返回；
@@   八块同组（PA[12:6] = 64）、tag 互不相同 ⇒ 第 8 块淘汰最久未用的代码行。
@@   有了 I-Cache 之后，写回是否已落到内存不再能由「取指仍读到旧值」单独观测，
@@   必须先让取指行失效，再跳过去（`m16-chipyard-010`）。
.macro IC_EVICT va
	set.rb	rb9, \va
	set.rb	rb10, 1f
	jump	[rb9, rd0, 0]
1:
.endm

	__TEST_BEGIN
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	set.rb	rb25, HMON_DATA_BASE
	set.rb	rb22, TEST_PAD
	st.o	rb22, [rb25, HMON_FRAME_RETURN]  @@ 固件 hmon 的返回地址槽

	@@ PTBR = 0（PA 0 的 L1 表），开 PTW
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6

	@@ ================= A 命中 / 缺失 =================
	set.rb	rb4, VA_A
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 1, rd5, M_A
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 2, rd5, M_A
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 3, rd5, M_A
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 4, rd5, M_A
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 5, rd5, M_A

	@@ ================= B 8 路同组 =================
	set.rb	rb4, VA_B0
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 6, rd5, M_B0
	set.rb	rb4, VA_B1
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 7, rd5, M_B1
	set.rb	rb4, VA_B2
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 8, rd5, M_B2
	set.rb	rb4, VA_B3
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 9, rd5, M_B3
	set.rb	rb4, VA_B4
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 10, rd5, M_B4
	set.rb	rb4, VA_B5
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 11, rd5, M_B5
	set.rb	rb4, VA_B6
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 12, rd5, M_B6
	set.rb	rb4, VA_B7
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 13, rd5, M_B7
	@@ B0 置 MRU，L9 填表淘汰 LRU（B1）
	set.rb	rb4, VA_B0
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 14, rd5, M_B0
	set.rb	rb4, VA_L9
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 15, rd5, M_L9
	@@ B7 置 MRU，L10 填表淘汰 LRU（B2）
	set.rb	rb4, VA_B7
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 16, rd5, M_B7
	set.rb	rb4, VA_L10
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 17, rd5, M_L10
	@@ B1 已被淘汰：再读即重填
	set.rb	rb4, VA_B1
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 18, rd5, M_B1

	@@ ================= C 写回 / 写穿时机 =================
	@@ 从核内 SRAM（不进 D-Cache）取 8 B 指令字
	set.rb	rb7, STUB_WORD
	ld.o	rd8, [rb7, 0]
	__REC	rd8				@@ r18 指令字（期望由核内读出、判据自洽）
	@@ 经 D-Cache 写到代码页（写分配：先填充、再合并、置 dirty）
	set.rb	rb4, VA_CODE
	st.o	rd8, [rb4, 0]
	@@ 第一次跳：内存未回写 ⇒ 取指读到 0（UNDI）
	EXPECT_FAULT UNDI_ONEHOT, FAIL_POINT_1, dc_resume1
dc_resume1:
	set.rd	rd7, MARK_JUMP1
	__REC	rd7				@@ r19 旧值（UNDI）作为观察点
	@@ 写后读：命中、读到新值（不回内存）
	ld.o	rd5, [rb4, 0]
	__REC	rd5				@@ r20 = 指令字
	set.rd	rd20, 0
	br.eq	{rd8, rd5}?, [rb0, dc_rd_ok1]
	__EXIT	0x31
dc_rd_ok1:
	@@ 淘汰前再跳：仍读到旧值（UNDI）
	EXPECT_FAULT UNDI_ONEHOT, FAIL_POINT_1, dc_resume2
dc_resume2:
	set.rd	rd7, MARK_JUMP2
	__REC	rd7				@@ r21 写回仍未发生
	@@ 同组再填 8 条新行：按 LRU 把代码行（dirty）淘汰并写回
	set.rb	rb4, VA_F1
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 19, rd5, M_F1
	set.rb	rb4, VA_F2
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 20, rd5, M_F2
	set.rb	rb4, VA_F3
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 21, rd5, M_F3
	set.rb	rb4, VA_F4
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 22, rd5, M_F4
	set.rb	rb4, VA_F5
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 23, rd5, M_F5
	set.rb	rb4, VA_F6
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 24, rd5, M_F6
	set.rb	rb4, VA_F7
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 25, rd5, M_F7
	set.rb	rb4, VA_F8
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 26, rd5, M_F8
	@@ I-Cache：把代码行挤出去（8 条同组、不同 tag 的行）
	IC_EVICT VA_EV0
	IC_EVICT VA_EV1
	IC_EVICT VA_EV2
	IC_EVICT VA_EV3
	IC_EVICT VA_EV4
	IC_EVICT VA_EV5
	IC_EVICT VA_EV6
	IC_EVICT VA_EV7
	@@ 淘汰后再跳：内存已写回 ⇒ 取指读到 trap（CFXTRAP）
	EXPECT_FAULT CFXTRAP_ONEHOT, FAIL_POINT_1, dc_resume3
dc_resume3:
	set.rd	rd7, MARK_JUMP3
	__REC	rd7				@@ r30 写回已落地
	@@ 核内再读该行：缺失重填、读回写回后的值
	set.rb	rb4, VA_CODE
	ld.o	rd5, [rb4, 0]
	__REC	rd5				@@ r31 = 指令字
	set.rd	rd20, 0
	br.eq	{rd8, rd5}?, [rb0, dc_rd_ok2]
	__EXIT	0x32
dc_rd_ok2:

	@@ ================= D PTW 端口（页表读经 D-Cache） =================
	set.rb	rb4, VA_PAGE
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 27, rd5, M_PAGE_OLD
	@@ 经自映射页把 L2[7] 的 PTE 改成新目标（走 D-Cache 写）
	set.rb	rb4, (VA_L2SELF + OFF_L2_PAGE)
	set.rb	rb8, PTE_PAGE_NEW
	st.o	rb8, [rb4, 0]
	@@ 清 TLB，逼下一次访问重走查
	set.rd	rd6, 2				@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	set.rb	rb4, VA_PAGE
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 28, rd5, M_PAGE_NEW
	@@ 核内视角读该 PTE：同一缓存行
	set.rb	rb4, (VA_L2SELF + OFF_L2_PAGE)
	ld.o	rd5, [rb4, 0]
	__CHECK_RD 29, rd5, PTE_PAGE_NEW

	__TEST_END
	@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.text
	.balign 4
perm_mon:
	PERM_OPEN	cfx_ptw
	PERM_MON_CLOSE

	__TEST_SECTIONS

	@@ 核内 SRAM 里的 8 B 指令字（`ld.o` 从 SRAM 读，不经 D-Cache）
	.section .stubdata, "aw"
	.p2align 3
	.globl	STUB_WORD
STUB_WORD:
	trap	cfx_hmon, 0
	.dd.t32	0

	@@ ---- 数据块：magic 按生成器常量放在各自的 PA ----
	.section .pt_l1, "aw"
	.p2align 3
	.dd.o64	PTE_L1

	.section .pt_l2, "aw"
	.p2align 3
	.dd.o64	0				@@ L2[0]
	.dd.o64	PTE_SELF			@@ L2[1]
	.dd.o64	PTE_EV0				@@ L2[2]（I-Cache 淘汰块，m16-chipyard-010）
	.dd.o64	PTE_EV1				@@ L2[3]
	.dd.o64	PTE_DATA			@@ L2[4]
	.dd.o64	PTE_DATA1			@@ L2[5]
	.dd.o64	PTE_DATA2			@@ L2[6]
	.dd.o64	PTE_PAGE_OLD			@@ L2[7]
	.dd.o64	PTE_CODE			@@ L2[8]
	.dd.o64	0				@@ L2[9]（页 9 = 新目标页，无代码）
	.dd.o64	PTE_EV2				@@ L2[10]（页 10 = 0xA_0000）
	.dd.o64	PTE_EV3				@@ L2[11]
	.dd.o64	PTE_EV4				@@ L2[12]
	.dd.o64	PTE_EV5				@@ L2[13]
	.dd.o64	PTE_EV6				@@ L2[14]
	.dd.o64	PTE_EV7				@@ L2[15]

	.section .l_a, "aw"
	.p2align 3
	.dd.o64	M_A

	.section .l_b, "aw"
	.p2align 3
	.dd.o64	M_B0
	.space	0x1FF8, 0
	.dd.o64	M_B1
	.space	0x1FF8, 0
	.dd.o64	M_B2
	.space	0x1FF8, 0
	.dd.o64	M_B3
	.space	0x1FF8, 0
	.dd.o64	M_B4
	.space	0x1FF8, 0
	.dd.o64	M_B5
	.space	0x1FF8, 0
	.dd.o64	M_B6
	.space	0x1FF8, 0
	.dd.o64	M_B7

	.section .l9, "aw"
	.p2align 3
	.dd.o64	M_L9
	.space	0x1FF8, 0
	.dd.o64	M_L10
	.space	0x1FF8, 0
	.dd.o64	M_F1
	.space	0x1FF8, 0
	.dd.o64	M_F2
	.space	0x1FF8, 0
	.dd.o64	M_F3
	.space	0x1FF8, 0
	.dd.o64	M_F4
	.space	0x1FF8, 0
	.dd.o64	M_F5

	.section .l10, "aw"
	.p2align 3
	.dd.o64	M_F6
	.space	0x1FF8, 0
	.dd.o64	M_F7
	.space	0x1FF8, 0
	.dd.o64	M_F8

	.section .page_old, "aw"
	.p2align 3
	.dd.o64	M_PAGE_OLD

	.section .page_new, "aw"
	.p2align 3
	.dd.o64	M_PAGE_NEW

	@@ ---- I-Cache 淘汰块（每块一条 `jump [rb10, rd0, 0]`，占一行）----
	.macro IC_EVICTOR name
	.section .ev_\name, "ax"
	.p2align 6
\name:
	jump	[rb10, rd0, 0]
	.endm

	IC_EVICTOR EV0
	IC_EVICTOR EV1
	IC_EVICTOR EV2
	IC_EVICTOR EV3
	IC_EVICTOR EV4
	IC_EVICTOR EV5
	IC_EVICTOR EV6
	IC_EVICTOR EV7

	@@ 代码页初值 = 0（非法指令/UNDI）。PA RAM 上电不是 0（TLRAM 随机），
	@@ 必须显式装入，否则第一次取指会执行随机字。
	.section .code_old, "aw"
	.p2align 3
	.dd.o64	0
