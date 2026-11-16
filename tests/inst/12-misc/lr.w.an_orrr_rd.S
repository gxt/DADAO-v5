@@ lr.w.an_orrr_rd.S — lr.w.an（orrr，opc 0x47，mask 0xFFFC0000）
@@ 大类：12-misc（其它指令 · 原子 `spec/SimRISC-12 §1`）；册目录 `tests/inst/12-misc/`
@@ id：lr.w.an_orrr_rd　形式：orrr　opc：0x47　mask：0xFFFC0000　value：0x47180000
@@ 语义：lr 的读宽度 = 2 B；地址须按 2 B 自然对齐（否则 MALIGN）
@@ 合法性：lr 的 hb(rdHB) 是 SBZ 固定零字段 ⇒ hb != rd0 时 ILLI（encode_sbz）；数据目的 rdHC 可为 rd0
@@ 存储序：.an（获取）；单 hart 链例下只约束访存顺序，不改变数值结果
@@ 保留机制（contract-isa §14.2）：粒度 = 精确地址 + 访问宽度；另一条 lr / 每次 sc（成败）/
@@   异常或中断进入 清本 hart 全部标记；sc 失败不写内存并返回 1、成功返回 0（本文件一律内联期望）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA 零区；每例独立 8 B 拍（运行时置初值）
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 用例：encoding 3 / semantic 7 / boundary 6 / overlap 2（链例 18 + 故障例 2）
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

	@@ ---- encoding：规范编码字直接执行（opc 0x47 + ha 位域） ----
	@@! inputs: kind=lr-enc sym=A17 k=0 init=0x0123456789ABCDEF enc=0x47180083
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A17
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A17
	.dd.t32 0x47180083
	__CHECK_RD 1, rd2, 0x0000000000000123

	@@ ---- encoding：lr 装载宽度窗口并零扩展 ----
	@@! inputs: kind=lr sym=A0 k=0 init=0x0123456789ABCDEF
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A0
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A0
	lr.w.an	rd2, [rb3]
	__CHECK_RD 2, rd2, 0x0000000000000123

	@@ ---- encoding：寄存器字段（rdHC 数据目的 / rbHD 基址） ----
	@@! inputs: kind=lr sym=A1 k=2 init=0xFEDCBA9876543210
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, A1
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A1 + 2
	lr.w.an	rd2, [rb3]
	__CHECK_RD 3, rd2, 0x000000000000BA98

	@@ ---- semantic：lr 设标记 ⇒ sc 同地址同宽度成功（rdHB=0）并合并写入 ----
	@@! inputs: kind=lr+sc sym=A2 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A2
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A2
	lr.w.an	rd2, [rb3]
	__CHECK_RD 4, rd2, 0x0000000000000123
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.w.nn	rd5, rd2, [rb3]
	__VERIFY_RD 4, rd5, 0x0000000000000000
	__VERIFY_MEM 4, A2, 0, 0xF00D456789ABCDEF

	@@ ---- semantic：sc 写回 lr 读到的值 ⇒ 成功且内存逐字节不变 ----
	@@! inputs: kind=lr+sc sym=A3 k=0 init=0xFEDCBA9876543210 src=load
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, A3
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A3
	lr.w.an	rd2, [rb3]
	__CHECK_RD 5, rd2, 0x000000000000FEDC
	sc.w.nn	rd5, rd2, [rb3]
	__VERIFY_RD 5, rd5, 0x0000000000000000
	__VERIFY_MEM 5, A3, 0, 0xFEDCBA9876543210

	@@ ---- semantic：保留标记只在精确地址+宽度上命中 ⇒ 异字 sc 失败且不写内存 ----
	@@! inputs: kind=lr;sc@B sym=A4/B4 k=0 init=0x0123456789ABCDEF/0x0F1E2D3C4B5A6978 src=0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A4
	st.o	rd6, [rb3, 0]
	__LI	rd6, 0x0F1E2D3C4B5A6978
	LOAD_ADDR rb3, B4
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A4
	lr.w.an	rd2, [rb3]
	__CHECK_RD 6, rd2, 0x0000000000000123
	__LI	rd2, 0xDEADBEEFCAFEF00D
	LOAD_ADDR rb4, B4
	sc.w.nn	rd5, rd2, [rb4]
	__VERIFY_RD 6, rd5, 0x0000000000000001
	__VERIFY_MEM 6, A4, 0, 0x0123456789ABCDEF
	__VERIFY_MEM 6, B4, 0, 0x0F1E2D3C4B5A6978

	@@ ---- semantic：当前 hart 执行另一条 lr ⇒ 旧标记清除（sc 失败） ----
	@@! inputs: kind=lr;lr;sc@A sym=A5/B5 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A5
	st.o	rd6, [rb3, 0]
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, B5
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A5
	lr.w.an	rd2, [rb3]
	__CHECK_RD 7, rd2, 0x0000000000000123
	LOAD_ADDR rb3, B5
	lr.w.an	rd2, [rb3]
	LOAD_ADDR rb3, A5
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.w.nn	rd5, rd2, [rb3]
	__VERIFY_RD 7, rd5, 0x0000000000000001
	__VERIFY_MEM 7, A5, 0, 0x0123456789ABCDEF

	@@ ---- semantic：sc 成功后标记已消费 ⇒ 紧接着的 sc 失败（内存保留首次写） ----
	@@! inputs: kind=lr;sc;sc sym=A6 k=0 init=0x0123456789ABCDEF src=0x5A5A5A5A5A5A5A5A,0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A6
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A6
	lr.w.an	rd2, [rb3]
	__CHECK_RD 8, rd2, 0x0000000000000123
	__LI	rd2, 0x5A5A5A5A5A5A5A5A
	sc.w.nn	rd5, rd2, [rb3]
	__VERIFY_RD 8, rd5, 0x0000000000000000
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.w.nn	rd5, rd2, [rb3]
	__VERIFY_RD 8, rd5, 0x0000000000000001
	__VERIFY_MEM 8, A6, 0, 0x5A5A456789ABCDEF

	@@ ---- boundary：宽度窗口全 1 ⇒ 零扩展为 0x00..FF ----
	@@! inputs: kind=lr sym=A7 k=0 init=all1
	__LI	rd6, 0xFFFFFFFFFFFFFFFF
	LOAD_ADDR rb3, A7
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A7
	lr.w.an	rd2, [rb3]
	__CHECK_RD 9, rd2, 0x000000000000FFFF

	@@ ---- boundary：全 0 拍 ⇒ 读出 0 ----
	@@! inputs: kind=lr sym=A8 k=0 init=0
	__LI	rd6, 0x0000000000000000
	LOAD_ADDR rb3, A8
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A8
	lr.w.an	rd2, [rb3]
	__CHECK_RD 10, rd2, 0x0000000000000000

	@@ ---- boundary：窗口最高位为 1 ⇒ 零扩展（不符号扩展） ----
	@@! inputs: kind=lr sym=A9 k=0 init=msb
	__LI	rd6, 0x8000000000000000
	LOAD_ADDR rb3, A9
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A9
	lr.w.an	rd2, [rb3]
	__CHECK_RD 11, rd2, 0x0000000000008000

	@@ ---- boundary：数据区末拍（地址上界）装载 ----
	@@! inputs: kind=lr sym=L k=0 init=0x1122334455667788
	__LI	rd6, 0x1122334455667788
	LOAD_ADDR rb3, L
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, L
	lr.w.an	rd2, [rb3]
	__CHECK_RD 12, rd2, 0x0000000000001122

	@@ ---- boundary：窗口贴 8 B 字尾（k 最大） ----
	@@! inputs: kind=lr sym=A11 k=6 init=0xFEDCBA9876543210
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, A11
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A11 + 6
	lr.w.an	rd2, [rb3]
	__CHECK_RD 13, rd2, 0x0000000000003210

	@@ ---- overlap/legality：rdHC=rd0 合法，标记照设 ⇒ 后续 sc 成功 ----
	@@! inputs: kind=lr(rd0)+sc sym=A12 k=0 init=0x0123456789ABCDEF src=0xDEADBEEFCAFEF00D
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A12
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A12
	lr.w.an	rd0, [rb3]
	@@ lr 的数据目的 rdHC=rd0：丢弃装载值合法（dst_rd0 不适用）
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.w.nn	rd5, rd2, [rb3]
	__CHECK_RD 14, rd5, 0x0000000000000000
	__VERIFY_MEM 14, A12, 0, 0xF00D456789ABCDEF

	@@ ---- overlap：lr 目的 = sc 结果寄存器（同一 rd） ----
	@@! inputs: kind=lr(rd5)+sc sym=A13 k=0 init=0x0123456789ABCDEF
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A13
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A13
	lr.w.an	rd5, [rb3]
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.w.nn	rd5, rd2, [rb3]
	__CHECK_RD 15, rd5, 0x0000000000000000
	__VERIFY_MEM 15, A13, 0, 0xF00D456789ABCDEF

	@@ ---- semantic：失败的 sc 也清全部标记 ⇒ 之后 sc 原地址仍失败 ----
	@@! inputs: kind=lr;sc@B(fail);sc@A sym=A14/B14 k=0 init=0x0123456789ABCDEF
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A14
	st.o	rd6, [rb3, 0]
	__LI	rd6, 0x0F1E2D3C4B5A6978
	LOAD_ADDR rb3, B14
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A14
	lr.w.an	rd2, [rb3]
	__CHECK_RD 16, rd2, 0x0000000000000123
	__LI	rd2, 0xDEADBEEFCAFEF00D
	LOAD_ADDR rb4, B14
	sc.w.nn	rd5, rd2, [rb4]
	LOAD_ADDR rb3, A14
	sc.w.nn	rd5, rd2, [rb3]
	__VERIFY_RD 16, rd5, 0x0000000000000001
	__VERIFY_MEM 16, A14, 0, 0x0123456789ABCDEF

	@@ ---- boundary：sc 源 rd0 读出 0 ⇒ 仅宽度窗口清零 ----
	@@! inputs: kind=lr+sc(rd0) sym=A15 k=2 init=0xFEDCBA9876543210
	__LI	rd6, 0xFEDCBA9876543210
	LOAD_ADDR rb3, A15
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A15 + 2
	lr.w.an	rd2, [rb3]
	__CHECK_RD 17, rd2, 0x000000000000BA98
	sc.w.nn	rd5, rd0, [rb3]
	__VERIFY_RD 17, rd5, 0x0000000000000000
	__VERIFY_MEM 17, A15, 0, 0xFEDC000076543210

	@@ ---- semantic：窗口贴字尾的 lr→sc 往返 ----
	@@! inputs: kind=lr+sc sym=A16 k=6 init=0x0123456789ABCDEF
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A16
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A16 + 6
	lr.w.an	rd2, [rb3]
	__CHECK_RD 18, rd2, 0x000000000000CDEF
	__LI	rd2, 0xDEADBEEFCAFEF00D
	sc.w.nn	rd5, rd2, [rb3]
	__VERIFY_RD 18, rd5, 0x0000000000000000
	__VERIFY_MEM 18, A16, 0, 0x0123456789ABF00D

	__TEST_END

	@@ ---- fault（一例一镜像；原始编码）----
	@@ fault 19：lr 的 hb(rdHB) != rd0 ⇒ ILLI（原始编码）
	TEST_FAULT_CF1 19, rb3, A0, ILLI, 0x47185083

	@@ fault 20：lr 地址未按 2 B 自然对齐 ⇒ MALIGN（原始编码，rb6 = LMAL）
	TEST_FAULT_CF1 20, rb6, LMAL, MALIGN, 0x47180086

	__TEST_SECTIONS
