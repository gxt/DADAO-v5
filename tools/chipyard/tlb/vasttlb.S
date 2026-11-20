@@ vasttlb.S — DADAO I/D TLB 探针（`m16-chipyard-008`）
@@
@@ 目的：在 `WumingVastConfig` 上覆盖「一级 I/D TLB」的语义面；页表几何、PTE
@@ 值、数据 magic 与所有期望值都由 `tools/chipyard/tlb/gen_vasttlb_tables.py`
@@ 独立算出（本文件不含手算的索引或位域）。
@@
@@   P1 I/D 命中与缺失
@@     1 首次读填表（走页表）
@@     2 改内存里的 PTE（不失效）后再读 ⇒ 仍读旧 PA 的数据（命中不重读 PTE）
@@     3 `invalid` + VA 后重读 ⇒ 新 PA 的数据（缺失重步查）
@@
@@   P2 2 组 × 8 路（set = VA[16]）
@@     4–11 P1..P8 同 set 各读一次（8 条共存）
@@     12 P1 改 PTE 后再读 ⇒ 旧数据（8 条都还在、命中）
@@     13 P9 填表淘汰 LRU（P1）后，P8 改 PTE 再读 ⇒ 旧数据（P8 未被淘汰）
@@     14 P1 再读 ⇒ 新数据（按 LRU 被淘汰并重步查）
@@
@@   P3 超页 4 条全相联 + LRU
@@     15–18 S1..S4 各读一次（4 条满）
@@     19 S1 再读 ⇒ 命中（置 MRU）
@@     20 S5 读 ⇒ 淘汰 LRU（S2）
@@     21 S2 改 PTE 后再读 ⇒ 新数据（已被淘汰、重步查）
@@     22 S1 改 PTE 后再读 ⇒ 旧数据（仍在表中）
@@
@@   P4 I-TLB 无 D 位
@@     23 取指后 `clean` ⇒ PTE 的 A=1、D 仍为 0
@@     24 再对该页做 store 后 `clean` ⇒ A=1、D=1（D 位只在数据表）
@@
@@   P5 A/D OR 合并（同一 PTE 在 I、D 两表各有一份）
@@     25 `clean` 之后 PTE 的 A=1、D=1（I 回写 A、D 回写 A+D，OR 到同一字）
@@     26/27 同一次 `clean` 若回写失败（实现层注入）⇒ 帧槽记录（未注入时为 0）
@@     28 `clean` 之后 PTE 的终值（未注入 A1D1 / 注入 A1D0）
@@
@@   P6 双表失效矩阵（invalid / clean / flush × I/D）
@@     每个操作 4 条记录：PI 的 PTE、PD 的 PTE、PI 取指落点标记、PD 读数据
@@     （PTE 读写经 L2 表自映射：`VA = VA_BASE + PA`）
@@
@@ 断言方式：数据 magic 用 `__VERIFY_RD`（不等即 `SYS_EXIT(点号)`）；观测量用
@@ `__REC` 写进结果缓冲，由宿主 `check_vasttlb.py` 逐条与生成器期望比对。
@@
@@ `.ifdef CASE_OR`：只跑 P5（ADWBFAIL 注入专用镜像；注入会让 D 侧命令回写
@@ 一直失败，其它阶段会落在未布置的故障回路上）。
@@
@@ 页表与数据由 `+loadmem=` 装入 PA RAM（`vasttlb.lds` 的段按生成器常量放置）；
@@ 探针自身在核内 SRAM（`addr[47:42] ≠ 0`，不经翻译）。

	.include "tests/inst/macros/inst_test.inc"
	.include "vasttlb_tables.inc"

	__TEST_BEGIN
	LOAD_ADDR rb25, HMON_BASE
	LOAD_ADDR rb5, VA_L2SELF		@@ L2 表自映射页（读写 PTE）
	LOAD_ADDR rb6, VA_L1SELF		@@ L1 表自映射页

	@@ PTBR = 0（PA 0 的 L1 表），开 PTW
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6

.ifdef CASE_OR

	@@ ================= P5 only（ADWBFAIL 注入专用） =================
	@@ 清空两表后让同一页在 I、D 两表各填一份，再 clean/all。
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb9, VA_OR
	@@ 取指（I 表）：落点桩把 rd7 置标记后跳回
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__VERIFY_RD	1, rd7, OR_STUB_MARK
	@@ 读 + 写（D 表）：A 与 D 都挂起
	LOAD_ADDR rb7, (VA_OR + 0x800)
	ld.o	rd5, [rb7, 0]
	__VERIFY_RD	2, rd5, M_OR
	LOAD_ADDR rb8, OR_STORE_VAL
	LOAD_ADDR rb7, (VA_OR + 0x808)
	st.o	rb8, [rb7, 0]

	@@ clean #1（故障可回落：注入时这里报 CFXMEM[56]）
	st.o	rd0, [rb25, 0xE0]
	st.o	rd0, [rb25, 0xF0]
	.globl	tl_or_aip1
tl_or_aip1:
	aip.si	rb21, 0
	add.si	rb21, 20
	st.o	rb21, [rb25, 0xF8]
	set.rd	rd6, 1				@@ clean / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.globl	tl_or_res1
tl_or_res1:
	ld.o	rd5, [rb25, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb25, 0xF0]
	__REC	rd5

	@@ clean #2：失败侧条目保留 ⇒ 注入时这里再报一次（同一个 PTE PA）
	st.o	rd0, [rb25, 0xE0]
	st.o	rd0, [rb25, 0xF0]
	.globl	tl_or_aip2
tl_or_aip2:
	aip.si	rb21, 0
	add.si	rb21, 20
	st.o	rb21, [rb25, 0xF8]
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.globl	tl_or_res2
tl_or_res2:
	ld.o	rd5, [rb25, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb25, 0xF0]
	__REC	rd5

	@@ 终值：未注入 A1D1；注入（D 侧回写不落地）A1D0
	ld.o	rd5, [rb5, OFF_L2_OR]
	__REC	rd5

.else

	@@ ================= P1 命中 / 缺失 =================
	LOAD_ADDR rb7, VA_P1
	ld.o	rd5, [rb7, 0]
	__VERIFY_RD	1, rd5, M_P1
	__REC	rd5				@@ r0 首次读（填充）
	LOAD_ADDR rb8, PTE_P1_NEW		@@ 改内存里的 PTE（不失效）
	st.o	rb8, [rb5, OFF_L2_P1]
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r1 命中 ⇒ 旧数据
	set.rd	rd6, 0x06			@@ invalid / VA
	set.rd	rd10, VA_P1
	cfx2rc	cfx_ptw, cg12, rc2, rd10
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r2 重步查 ⇒ 新数据

	@@ ================= P2 2 组 × 8 路 =================
	LOAD_ADDR rb8, PTE_P1			@@ P1 的 PTE 复位
	st.o	rb8, [rb5, OFF_L2_P1]
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb7, VA_P1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r3  P1 填充
	LOAD_ADDR rb7, VA_P2
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r4  P2
	LOAD_ADDR rb7, VA_P3
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r5  P3
	LOAD_ADDR rb7, VA_P4
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r6  P4
	LOAD_ADDR rb7, VA_P5
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r7  P5
	LOAD_ADDR rb7, VA_P6
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r8  P6
	LOAD_ADDR rb7, VA_P7
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r9  P7
	LOAD_ADDR rb7, VA_P8
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r10 P8
	@@ P1 改 PTE 后再读 ⇒ 命中（8 条都在）
	LOAD_ADDR rb8, PTE_P1_NEW
	st.o	rb8, [rb5, OFF_L2_P1]
	LOAD_ADDR rb7, VA_P1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r11 旧数据
	@@ 依次访问 P2..P8（把 P1 压成 LRU）
	LOAD_ADDR rb7, VA_P2
	ld.o	rd5, [rb7, 0]
	LOAD_ADDR rb7, VA_P3
	ld.o	rd5, [rb7, 0]
	LOAD_ADDR rb7, VA_P4
	ld.o	rd5, [rb7, 0]
	LOAD_ADDR rb7, VA_P5
	ld.o	rd5, [rb7, 0]
	LOAD_ADDR rb7, VA_P6
	ld.o	rd5, [rb7, 0]
	LOAD_ADDR rb7, VA_P7
	ld.o	rd5, [rb7, 0]
	LOAD_ADDR rb7, VA_P8
	ld.o	rd5, [rb7, 0]
	@@ P9 填表 ⇒ 淘汰 LRU（P1）
	LOAD_ADDR rb7, VA_P9
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r12 P9
	@@ P8 改 PTE 后再读 ⇒ 旧数据（未被淘汰）
	LOAD_ADDR rb8, PTE_P8_NEW
	st.o	rb8, [rb5, OFF_L2_P8]
	LOAD_ADDR rb7, VA_P8
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r13 旧数据
	@@ P1 再读 ⇒ 新数据（按 LRU 被淘汰）
	LOAD_ADDR rb7, VA_P1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r14 新数据

	@@ ================= P3 超页 4 条全相联 + LRU =================
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb7, VA_S1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r15 S1
	LOAD_ADDR rb7, VA_S2
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r16 S2
	LOAD_ADDR rb7, VA_S3
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r17 S3
	LOAD_ADDR rb7, VA_S4
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r18 S4
	LOAD_ADDR rb7, VA_S1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r19 S1 命中（MRU）
	@@ S1/S2 的 L1 PTE 改成新目标（不失效）
	LOAD_ADDR rb8, PTE_S2_NEW
	LOAD_ADDR rb6, (VA_L1SELF + OFF_L1_S2)
	st.o	rb8, [rb6, 0]
	LOAD_ADDR rb8, PTE_S1_NEW
	LOAD_ADDR rb6, (VA_L1SELF + OFF_L1_S1)
	st.o	rb8, [rb6, 0]
	LOAD_ADDR rb7, VA_S5
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r20 S5 填充（淘汰 S2）
	LOAD_ADDR rb7, VA_S2
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r21 S2 新数据（重步查）
	LOAD_ADDR rb7, VA_S1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r22 S1 旧数据（未淘汰）

	@@ ================= P4 I-TLB 无 D 位 =================
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb9, VA_PX
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__VERIFY_RD	2, rd7, PX_MARK
	set.rd	rd6, 1				@@ clean / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb5, OFF_L2_PX]
	__REC	rd5				@@ r23 取指后 A=1、D=0
	LOAD_ADDR rb8, OR_STORE_VAL
	LOAD_ADDR rb7, (VA_PX + 0x800)
	st.o	rb8, [rb7, 0]			@@ 数据访问（D 表）
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb5, OFF_L2_PX]
	__REC	rd5				@@ r24 写后 A=1、D=1

	@@ ================= P5 A/D OR 合并 =================
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb9, VA_OR
	@@ 取指（I 表）
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__VERIFY_RD	3, rd7, OR_STUB_MARK
	@@ 读 + 写（D 表）
	LOAD_ADDR rb7, (VA_OR + 0x800)
	ld.o	rd5, [rb7, 0]
	__VERIFY_RD	4, rd5, M_OR
	LOAD_ADDR rb8, OR_STORE_VAL
	LOAD_ADDR rb7, (VA_OR + 0x808)
	st.o	rb8, [rb7, 0]
	@@ clean #1（注入时此处报 CFXMEM[56]）
	st.o	rd0, [rb25, 0xE0]
	st.o	rd0, [rb25, 0xF0]
	.globl	tl_or_aip1
tl_or_aip1:
	aip.si	rb21, 0
	add.si	rb21, 20
	st.o	rb21, [rb25, 0xF8]
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.globl	tl_or_res1
tl_or_res1:
	ld.o	rd5, [rb25, 0xE0]
	__REC	rd5				@@ r25 帧 cause（未注入 0）
	ld.o	rd5, [rb25, 0xF0]
	__REC	rd5				@@ r26 帧 info
	@@ clean #2
	st.o	rd0, [rb25, 0xE0]
	st.o	rd0, [rb25, 0xF0]
	.globl	tl_or_aip2
tl_or_aip2:
	aip.si	rb21, 0
	add.si	rb21, 20
	st.o	rb21, [rb25, 0xF8]
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.globl	tl_or_res2
tl_or_res2:
	ld.o	rd5, [rb25, 0xE0]
	__REC	rd5				@@ r27 帧 cause
	ld.o	rd5, [rb25, 0xF0]
	__REC	rd5				@@ r28 帧 info
	ld.o	rd5, [rb5, OFF_L2_OR]
	__REC	rd5				@@ r29 PTE 终值

	@@ ================= P6 双表失效矩阵 =================
	@@ invalid × I/D
	set.rd	rd6, 0x02			@@ invalid / all（清两表）
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb8, PTE_PI
	st.o	rb8, [rb5, OFF_L2_PI]
	LOAD_ADDR rb8, PTE_PD
	st.o	rb8, [rb5, OFF_L2_PD]
	LOAD_ADDR rb9, VA_PI
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__VERIFY_RD	5, rd7, PI_MARK_OLD
	LOAD_ADDR rb7, VA_PD
	ld.o	rd5, [rb7, 0]
	__VERIFY_RD	6, rd5, M_PD
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb5, OFF_L2_PI]
	__REC	rd5				@@ r30 PI PTE（未回写 A=0）
	ld.o	rd5, [rb5, OFF_L2_PD]
	__REC	rd5				@@ r31 PD PTE（未回写 A=0）
	LOAD_ADDR rb8, PTE_PI_NEW
	st.o	rb8, [rb5, OFF_L2_PI]
	LOAD_ADDR rb8, PTE_PD_NEW
	st.o	rb8, [rb5, OFF_L2_PD]
	LOAD_ADDR rb9, VA_PI
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__REC	rd7				@@ r32 PI 取指 ⇒ 新桩（重步查）
	LOAD_ADDR rb7, VA_PD
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r33 PD ⇒ 新数据（重步查）

	@@ clean × I/D
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb8, PTE_PI
	st.o	rb8, [rb5, OFF_L2_PI]
	LOAD_ADDR rb8, PTE_PD
	st.o	rb8, [rb5, OFF_L2_PD]
	LOAD_ADDR rb9, VA_PI
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__VERIFY_RD	7, rd7, PI_MARK_OLD
	LOAD_ADDR rb7, VA_PD
	ld.o	rd5, [rb7, 0]
	__VERIFY_RD	8, rd5, M_PD
	set.rd	rd6, 0x01			@@ clean / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb5, OFF_L2_PI]
	__REC	rd5				@@ r34 PI PTE A=1
	ld.o	rd5, [rb5, OFF_L2_PD]
	__REC	rd5				@@ r35 PD PTE A=1
	LOAD_ADDR rb8, PTE_PI_NEW
	st.o	rb8, [rb5, OFF_L2_PI]
	LOAD_ADDR rb8, PTE_PD_NEW
	st.o	rb8, [rb5, OFF_L2_PD]
	LOAD_ADDR rb9, VA_PI
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__REC	rd7				@@ r36 仍命中 ⇒ 旧桩
	LOAD_ADDR rb7, VA_PD
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r37 仍命中 ⇒ 旧数据

	@@ flush × I/D
	set.rd	rd6, 0x02			@@ invalid / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb8, PTE_PI
	st.o	rb8, [rb5, OFF_L2_PI]
	LOAD_ADDR rb8, PTE_PD
	st.o	rb8, [rb5, OFF_L2_PD]
	LOAD_ADDR rb9, VA_PI
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__VERIFY_RD	9, rd7, PI_MARK_OLD
	LOAD_ADDR rb7, VA_PD
	ld.o	rd5, [rb7, 0]
	__VERIFY_RD	10, rd5, M_PD
	set.rd	rd6, 0x03			@@ flush / all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb5, OFF_L2_PI]
	__REC	rd5				@@ r38 PI PTE（回写 A=1 后删除）
	ld.o	rd5, [rb5, OFF_L2_PD]
	__REC	rd5				@@ r39 PD PTE A=1
	LOAD_ADDR rb8, PTE_PI_NEW
	st.o	rb8, [rb5, OFF_L2_PI]
	LOAD_ADDR rb8, PTE_PD_NEW
	st.o	rb8, [rb5, OFF_L2_PD]
	LOAD_ADDR rb9, VA_PI
	aip.si	rb12, 0
	add.si	rb12, 12
	jump	[rb9, rd0, 0]
	__REC	rd7				@@ r40 新桩（已删除、重步查）
	LOAD_ADDR rb7, VA_PD
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r41 新数据（已删除、重步查）

	@@ ================= P7 `invalid` + scope=VA 只清包含 start 的条目 =================
	@@ 同 set 放 P1、P2 两条相邻 VA；改两条 PTE 后 `invalid` start=P1 ⇒ P1 重步查、
	@@ P2 仍命中（读旧数据，证明只清一条）。
	set.rd	rd6, 0x02			@@ invalid / all（清两表）
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb8, PTE_P1
	st.o	rb8, [rb5, OFF_L2_P1]
	LOAD_ADDR rb8, PTE_P2
	st.o	rb8, [rb5, OFF_L2_P2]
	LOAD_ADDR rb7, VA_P1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r42 P1 填充
	LOAD_ADDR rb7, VA_P2
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r43 P2 填充
	LOAD_ADDR rb8, PTE_P1_NEW
	st.o	rb8, [rb5, OFF_L2_P1]
	LOAD_ADDR rb8, PTE_P2_NEW
	st.o	rb8, [rb5, OFF_L2_P2]
	set.rd	rd6, 0x06			@@ invalid / VA
	set.rd	rd10, VA_P1
	cfx2rc	cfx_ptw, cg12, rc2, rd10
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb7, VA_P1
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r44 P1 新数据（被清、重步查）
	LOAD_ADDR rb7, VA_P2
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r45 P2 旧数据（仍命中）

	@@ ================= P8 `asidAny` 与 `G` =================
	@@ G=1 与 G=0（ASID=1）两条；`flush` asidAny=0 只清 G=0 匹配条，G=1 存活；
	@@ 再发 asidAny=1 ⇒ G=1 也被清。
	set.rd	rd6, 0x02			@@ invalid / all（ASID 仍为 0，清两表）
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	set.rd	rd6, 1				@@ cfx_ptw_tlb_asid = 1
	cfx2rc	cfx_ptw, cg12, rc1, rd6
	LOAD_ADDR rb8, PTE_G
	st.o	rb8, [rb5, OFF_L2_G]
	LOAD_ADDR rb8, PTE_NG
	st.o	rb8, [rb5, OFF_L2_NG]
	LOAD_ADDR rb7, VA_G
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r46 G=1 填充
	LOAD_ADDR rb7, VA_NG
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r47 G=0/ASID=1 填充
	LOAD_ADDR rb8, PTE_G_NEW
	st.o	rb8, [rb5, OFF_L2_G]
	LOAD_ADDR rb8, PTE_NG_NEW
	st.o	rb8, [rb5, OFF_L2_NG]
	set.rd	rd6, 0x03			@@ flush / all / asidAny = 0
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb5, OFF_L2_G]
	__REC	rd5				@@ r48 G 的 PTE 未被回写（仍 A=0）
	LOAD_ADDR rb7, VA_G
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r49 G=1 仍命中（旧数据）
	LOAD_ADDR rb7, VA_NG
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r50 G=0 被清、重步查（新数据）
	ld.o	rd5, [rb5, OFF_L2_NG]
	__REC	rd5				@@ r51 G=0 的 PTE 已回写 A
	set.rd	rd6, 0x13			@@ flush / all / asidAny = 1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	LOAD_ADDR rb7, VA_G
	ld.o	rd5, [rb7, 0]
	__REC	rd5				@@ r52 G=1 被清、重步查（新数据）
	ld.o	rd5, [rb5, OFF_L2_G]
	__REC	rd5				@@ r53 G 的 PTE 已回写 A
	set.rd	rd6, 0				@@ ASID 复位
	cfx2rc	cfx_ptw, cg12, rc1, rd6

.endif	@@ CASE_OR

	@@ 收尾：关 PTW，打印结果缓冲并 SYS_EXIT(0)
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	__TEST_END

	__TEST_SECTIONS
