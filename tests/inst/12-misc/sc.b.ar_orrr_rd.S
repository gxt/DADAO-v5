@@ sc.b.ar_orrr_rd.S — sc.b.ar（orrr，opc 0x47，mask 0xFFFC0000）
@@ 大类：12-misc（其它指令 · 原子 `spec/SimRISC-12 §1`）；册目录 `tests/inst/12-misc/`
@@ id：sc.b.ar_orrr_rd　形式：orrr　opc：0x47　mask：0xFFFC0000　value：0x476c0000
@@ 语义：sc 的条件写宽度 = 1 B；地址须按 1 B 自然对齐（否则 MALIGN；.b 无对齐要求）
@@ 合法性：sc 的 rdHB 是成功/失败结果（目的）⇒ rdHB = rd0 时 ILLI（dst_rd0）
@@ 存储序：.ar（获取+释放）；单 hart 链例下只约束访存顺序，不改变数值结果
@@ 保留机制（contract-isa §14.2）：粒度 = 精确地址 + 访问宽度；另一条 lr / 每次 sc（成败）/
@@   异常或中断进入 清本 hart 全部标记；sc 失败不写内存并返回 1、成功返回 0（本文件一律内联期望）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA 零区；每例独立 8 B 拍（运行时置初值）
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 用例：encoding 2 / semantic 7 / boundary 5 / overlap 2（链例 16 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 期望来自 spec/SimRISC-12 §1 + contract-isa §14.2 + ADR-0034 D6（不从实现反推）
@@ 配对：链例里设置/消费标记用同宽度 nn 形式的 lr/sc（存储序提示不改变数值结果）
@@ GAP（不可测，见 MIGRATION §6/028）：多 hart 同址写清标记 / 异常或中断进入清标记 /
@@   保留粒度平台分歧 / 存储序强度 / sc 偶发失败 —— 均不写用例、不伪造

	.include "tests/inst/macros/inst_test.inc"

@@ 数据区（TEST_DATA 零区；每例独立 8 B 拍，例间不共享可写字节）
	.equ A0, TEST_DATA + 0x500
	.equ A1, TEST_DATA + 0x508
	.equ A2, TEST_DATA + 0x510
	.equ A3, TEST_DATA + 0x518
	.equ A4, TEST_DATA + 0x520
	.equ A5, TEST_DATA + 0x528
	.equ A6, TEST_DATA + 0x530
	.equ A7, TEST_DATA + 0x538
	.equ A8, TEST_DATA + 0x540
	.equ A9, TEST_DATA + 0x548
	.equ A10, TEST_DATA + 0x550
	.equ A11, TEST_DATA + 0x558
	.equ A12, TEST_DATA + 0x560
	.equ A13, TEST_DATA + 0x568
	.equ A14, TEST_DATA + 0x570
	.equ A15, TEST_DATA + 0x578
	.equ A16, TEST_DATA + 0x580
	.equ A17, TEST_DATA + 0x588
	.equ B0, TEST_DATA + 0x600
	.equ B1, TEST_DATA + 0x608
	.equ B2, TEST_DATA + 0x610
	.equ B3, TEST_DATA + 0x618
	.equ B4, TEST_DATA + 0x620
	.equ B5, TEST_DATA + 0x628
	.equ B6, TEST_DATA + 0x630
	.equ B7, TEST_DATA + 0x638
	.equ B8, TEST_DATA + 0x640
	.equ B9, TEST_DATA + 0x648
	.equ B10, TEST_DATA + 0x650
	.equ B11, TEST_DATA + 0x658
	.equ B12, TEST_DATA + 0x660
	.equ B13, TEST_DATA + 0x668
	.equ B14, TEST_DATA + 0x670
	.equ B15, TEST_DATA + 0x678
	.equ B16, TEST_DATA + 0x680
	.equ B17, TEST_DATA + 0x688
	.equ L, TEST_DATA + 0x7E8        @@ 数据区末拍（末字 0x7F0）
	.equ SCR, TEST_DATA + 0x7F8      @@ 清标记落点（全 0 拍）
	.equ LMAL, TEST_DATA + 0x7f1     @@ 故意不对齐（.w/.t/.o 的 MALIGN 例）

	__TEST_BEGIN

	@@ ---- encoding：规范编码字直接执行（opc 0x47 + ha + hb=rd5 位域） ----
	@@! inputs: kind=sc-enc sym=A17 k=0 init=0x0123456789ABCDEF enc=0x476c5083
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A17
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A17
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	.dd.t32 0x476c5083
	__CHECK_RD 1, rd5, 0x0000000000000000
	__VERIFY_MEM 1, A17, 0, 0x0D23456789ABCDEF

	@@ ---- encoding：无保留标记 ⇒ rdHB=1 且不写内存 ----
	@@! inputs: kind=sc sym=A0 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D resv=none
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A0
	st.o	rd6, [rb3, 0]
	@@ 清保留标记：lr SCR 后 sc SCR（成功消费，SCR 写 0）
	LOAD_ADDR rb5, SCR
	lr.b.nn	rd2, [rb5]
	sc.b.ar	rd5, rd2, [rb5]
	LOAD_ADDR rb3, A0
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 2, rd5, 0x0000000000000001
	__VERIFY_MEM 2, A0, 0, 0x0123456789ABCDEF

	@@ ---- semantic：命中标记 ⇒ rdHB=0，仅宽度窗口被写 ----
	@@! inputs: kind=sc sym=A1 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D resv=same
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A1
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A1
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 3, rd5, 0x0000000000000000
	__VERIFY_MEM 3, A1, 0, 0x0D23456789ABCDEF

	@@ ---- semantic：sc 写回同值 ⇒ 成功且字节不变 ----
	@@! inputs: kind=sc sym=A2 k=0 init=0xFEDCBA9876543210 src=load resv=same
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, A2
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A2
	lr.b.nn	rd2, [rb3]
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 4, rd5, 0x0000000000000000
	__VERIFY_MEM 4, A2, 0, 0xFEDCBA9876543210

	@@ ---- semantic：标记在 A、sc 指向 B（不同 8 B 字）⇒ 失败且都不写 ----
	@@! inputs: kind=sc@B sym=A3/B3 k=0 init=0x0123456789ABCDEF/0x0F1E2D3C4B5A6978 resv=A
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A3
	st.o	rd6, [rb3, 0]
	__LI	rd6, 0x0F1E2D3C4B5A6978
	LOAD_ADDR rb3, B3
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A3
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	LOAD_ADDR rb4, B3
	sc.b.ar	rd5, rd2, [rb4]
	__CHECK_RD 5, rd5, 0x0000000000000001
	__VERIFY_MEM 5, A3, 0, 0x0123456789ABCDEF
	__VERIFY_MEM 5, B3, 0, 0x0F1E2D3C4B5A6978

	@@ ---- semantic：lr A 后 lr B ⇒ A 的标记被清，sc A 失败 ----
	@@! inputs: kind=sc@A sym=A4/B4 k=0 init=0x0123456789ABCDEF resv=other
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A4
	st.o	rd6, [rb3, 0]
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, B4
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A4
	lr.b.nn	rd2, [rb3]
	LOAD_ADDR rb3, B4
	lr.b.nn	rd2, [rb3]
	LOAD_ADDR rb3, A4
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 6, rd5, 0x0000000000000001
	__VERIFY_MEM 6, A4, 0, 0x0123456789ABCDEF

	@@ ---- semantic：sc 成功后标记已消费 ⇒ 第二次 sc 失败，保留首次写 ----
	@@! inputs: kind=sc;sc sym=A5 k=0 init=0x0123456789ABCDEF src=0x5A5A5A5A5A5A5A5A,0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A5
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A5
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0x5A5A5A5A5A5A5A5A
	sc.b.ar	rd5, rd2, [rb3]
	__VERIFY_RD 6, rd5, 0x0000000000000000
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 7, rd5, 0x0000000000000001
	__VERIFY_MEM 7, A5, 0, 0x5A23456789ABCDEF

	@@ ---- semantic：失败的 sc 清全部标记 ⇒ 随后 sc 原地址仍失败 ----
	@@! inputs: kind=sc@B(fail);sc@A sym=A6/B6 k=0 init=0x0123456789ABCDEF
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A6
	st.o	rd6, [rb3, 0]
	__LI	rd6, 0x0F1E2D3C4B5A6978
	LOAD_ADDR rb3, B6
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A6
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	LOAD_ADDR rb4, B6
	sc.b.ar	rd5, rd2, [rb4]
	LOAD_ADDR rb3, A6
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 8, rd5, 0x0000000000000001
	__VERIFY_MEM 8, A6, 0, 0x0123456789ABCDEF

	@@ ---- boundary：全 1 源/拍 ⇒ 成功且仍全 1 ----
	@@! inputs: kind=sc sym=A7 k=0 init=all1 src=all1
	__LI	rd6, 0xFFFFFFFFFFFFFFFF
	LOAD_ADDR rb3, A7
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A7
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xFFFFFFFFFFFFFFFF
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 9, rd5, 0x0000000000000000
	__VERIFY_MEM 9, A7, 0, 0xFFFFFFFFFFFFFFFF

	@@ ---- boundary：零源 ⇒ 仅宽度窗口清零 ----
	@@! inputs: kind=sc sym=A8 k=0 init=0x0123456789ABCDEF src=0
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A8
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A8
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 10, rd5, 0x0000000000000000
	__VERIFY_MEM 10, A8, 0, 0x0023456789ABCDEF

	@@ ---- boundary：源高位在宽度外 ⇒ 只并低 8w 位 ----
	@@! inputs: kind=sc sym=A9 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A9
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A9
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 11, rd5, 0x0000000000000000
	__VERIFY_MEM 11, A9, 0, 0x0D23456789ABCDEF

	@@ ---- boundary：窗口贴 8 B 字尾的合并写入 ----
	@@! inputs: kind=sc sym=A10 k=7 init=0xFEDCBA9876543210 src=0x5A5A5A5A5A5A5A5A
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, A10
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A10 + 7
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0x5A5A5A5A5A5A5A5A
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 12, rd5, 0x0000000000000000
	__VERIFY_MEM 12, A10, 0, 0xFEDCBA987654325A

	@@ ---- boundary：数据区末拍的 sc（地址上界） ----
	@@! inputs: kind=sc sym=L k=0 init=0x0F1E2D3C4B5A6978 src=0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0F1E2D3C4B5A6978
	LOAD_ADDR rb3, L
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, L
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 13, rd5, 0x0000000000000000
	__VERIFY_MEM 13, L, 0, 0x0D1E2D3C4B5A6978

	@@ ---- overlap：rdHB == rdHC（源=结果）⇒ 源先读、结果后写 ----
	@@! inputs: kind=sc(rd5,rd5) sym=A11 k=0 init=0x0123456789ABCDEF src=0x5A5A5A5A5A5A5A5A
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A11
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A11
	lr.b.nn	rd2, [rb3]
	__LI	rd5, 0x5A5A5A5A5A5A5A5A
	sc.b.ar	rd5, rd5, [rb3]
	__CHECK_RD 14, rd5, 0x0000000000000000
	__VERIFY_MEM 14, A11, 0, 0x5A23456789ABCDEF

	@@ ---- overlap：rdHB == rdHC 且无标记 ⇒ 失败且不写 ----
	@@! inputs: kind=sc(rd5,rd5) sym=A12 k=0 init=0x0123456789ABCDEF resv=none
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A12
	st.o	rd6, [rb3, 0]
	@@ 清保留标记：lr SCR 后 sc SCR（成功消费，SCR 写 0）
	LOAD_ADDR rb5, SCR
	lr.b.nn	rd2, [rb5]
	sc.b.ar	rd5, rd2, [rb5]
	LOAD_ADDR rb3, A12
	__LI	rd5, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd5, [rb3]
	__CHECK_RD 15, rd5, 0x0000000000000001
	__VERIFY_MEM 15, A12, 0, 0x0123456789ABCDEF

	@@ ---- semantic：另一对齐偏移的 sc 合并位置 ----
	@@! inputs: kind=sc sym=A13 k=1 init=0xFEDCBA9876543210 src=0xDEADBEEFCAFEF00D
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, A13
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A13 + 1
	lr.b.nn	rd2, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.b.ar	rd5, rd2, [rb3]
	__CHECK_RD 16, rd5, 0x0000000000000000
	__VERIFY_MEM 16, A13, 0, 0xFE0DBA9876543210

	__TEST_END

	@@ ---- fault（一例一镜像；原始编码）----
	@@ fault 17：sc 的 rdHB = rd0 ⇒ ILLI（成功/失败结果不可丢弃，原始编码）
	TEST_FAULT_CF1 17, rb3, A0, ILLI, 0x476C0083

	__TEST_SECTIONS
