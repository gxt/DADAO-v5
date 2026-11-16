@@ rf2rf_orri_rf.S — rf2rf {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}（orri, opc 0x40, ha 0x3C）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rf2rf_orri_rf　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40F00000
@@ 语义：rf[HB..HB+n-1] ← rf[HC..HC+n-1]（n = immu6，1..63）；**整 64 位逐位复制** ——
@@   不做数值换算、不舍入、不置标志（`SimRISC-02 §1` 注）；源 `rf0` 读出完整 64 位。
@@ 合法性（`SimRISC-02 §1`）：目的范围含 `rf0` ⇒ ILLI（`dst_rf0`；与 `rd2rf` 允许
@@   `rf0` 作目的的例外相对）；immu6=0 ⇒ ILLI（`mreg_zero`）；起始 + immu6 > 64 ⇒
@@   ILLI（`mreg_range_overflow`，源/目的两侧）；源/目的有任何交集 ⇒ ILLI
@@   （`mreg_range_overlap`，含完全重合）⇒ 同组复制最多 31 个元素。精确性：非法条件
@@   在处理任何元素之前判定，目的寄存器未被修改。
@@ 期望值来源：`SimRISC-02 §1`「块传输保持 64 位二进制不变」⇒ 逐元素「目的 == 源位型」，
@@   字面量直接取源常量，不经任何模型/实现反推。位型搬移与浮点宽度无关 ⇒ 本 id 是
@@   `rf` 组唯一的同组块复制（`SimRISC-07` 侧不再有分宽度的同组复制载体）。
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 SCRATCH（rf 目的实测落点，rb29 指）/
@@   MSTORE（最大个数例的源；判据「目的 == 源内存」，与宏层既有 31 元口径一致）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 4 / boundary 3 / overlap 1 / rf0 1（链例 11 + 故障例 6）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：rf 目的单元素经 `st.o` 落 SCRATCH 再 `ld.o` 比（`st_*_rrii_rf`，与被测指令无关）；
@@   多元素用 `__VERIFY_MEM_RF`/`__CHECK_MEM_RF`（`rf2rd` 跨组读回 + `ld.o`，见宏层）
@@ rf 初值经 `__LI_RF`（`__LI` + `rd2rf`）装配 —— 不经被测指令，也不经浮点运算指令
@@ 注：`rf0`（FCSR）位型由硬件定义（含只读 qNaN 字段）⇒ 含 `rf0` 的用例只断言
@@   「目的 == 同一时刻的 rf0」（运行期取，不钉字面量）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

@@ ---- 文件专用宏（m15-testcases-002 下沉；只被本文件使用）----
@@ 内存 beat vs **运行期** rf 期望（`rf2rf` 的 31 元边界例用「目的 == 源内存」判据）：
@@   探针 = `rf2rd` 跨组读回 + `ld.o`（两者都不是被测的块复制指令），不引入期望常量。
@@   命名/参数与 `__CHECK_MEM_RB` 对齐（baseval/off 在前、组内寄存器在后）。
@@   `__VERIFY_*` 不占点号，`__CHECK_*` 是最后一条、点号在这里（失败点号 = 用例序号）。
.macro __VERIFY_MEM_RF pt, baseval, off, rfsrc
	rf2rd	{rd21:rd21}, {\rfsrc:\rfsrc}
	LOAD_ADDR rb21, (((\baseval) + (\off)) / 8) * 8
	ld.o	rd20, [rb21, 0]
	br.eq	{rd20, rd21}?, [rb0, __vmrf_\@]
	__EXIT	\pt
__vmrf_\@:
.endm

.macro __CHECK_MEM_RF pt, baseval, off, rfsrc
	rf2rd	{rd21:rd21}, {\rfsrc:\rfsrc}
	LOAD_ADDR rb21, (((\baseval) + (\off)) / 8) * 8
	ld.o	rd20, [rb21, 0]
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __cmrf_\@]
	__EXIT	\pt
__cmrf_\@:
.endm

@@ 源为 rf0 的单寄存器用例（rf0 = FCSR，位型由硬件定义 ⇒ 期望运行期取自 rf0 自身，
@@   不钉字面量；`rf2rd` 读回同样是跨组复制，与被测的 `rf2rf` 不是同一 id）
.macro TEST_MOV_RF0 pt, mnem, dst
	rf2rd	{rd22:rd22}, {rf0:rf0}
	\mnem	{\dst:\dst}, {rf0:rf0}
	rf2rd	{rd23:rd23}, {\dst:\dst}
	__VERIFY_EQ_RD	\pt, rd22, rd23
	__REC	rd23
.endm

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf20 / src=rf40 / immu6=2（两个元素）⇒ 0x40F14A02
	__LI_RF	rf40, 0x3FF0000000000000
	__LI_RF	rf41, 0xC002000000000000
	.dd.t32	0x40F14A02
	st.o	rf21, [rb29, 0]
	__VERIFY_MEM	1, SCRATCH, 0, 0xC002000000000000
	st.o	rf20, [rb29, 0]
	__CHECK_MEM	1, SCRATCH, 0, 0x3FF0000000000000
	@@ 字段边界：dst=rf63 / src=rf62 / immu6=1 ⇒ 0x40F3FF81（最高号目的）
	__LI_RF	rf62, 0x7FF8000000000000
	.dd.t32	0x40F3FF81
	st.o	rf63, [rb29, 0]
	__CHECK_MEM	2, SCRATCH, 0, 0x7FF8000000000000

	@@ ---- semantic ----
	@@ 个数 1：位型原样搬移（NaN payload 逐位保留，不做 canonical 化）
	__LI_RF	rf40, 0x7FF8000000123456
	TEST_MOV1	3, rf2rf, rf20, rf40, 0x7FF8000000123456
	@@ 个数 2：两个元素逐对搬移（含负号 qNaN / payload 1）
	__LI_RF	rf40, 0x3FF0000000000000
	__LI_RF	rf41, 0xFFF8000000000001
	rf2rf	{rf20:rf21}, {rf40:rf41}
	st.o	rf21, [rb29, 0]
	__VERIFY_MEM	4, SCRATCH, 0, 0xFFF8000000000001
	st.o	rf20, [rb29, 0]
	__CHECK_MEM	4, SCRATCH, 0, 0x3FF0000000000000
	@@ 个数 3：±0 与次正规照搬，且**不置标志**（FCSR 位型复制前后不变）
	__LI_RF	rf40, 0x0000000000000000
	__LI_RF	rf41, 0x8000000000000000
	__LI_RF	rf42, 0x000FFFFFFFFFFFFF
	rf2rd	{rd22:rd22}, {rf0:rf0}
	rf2rf	{rf20:rf22}, {rf40:rf42}
	rf2rd	{rd23:rd23}, {rf0:rf0}
	__VERIFY_EQ_RD	5, rd22, rd23
	st.o	rf22, [rb29, 0]
	__VERIFY_MEM	5, SCRATCH, 0, 0x000FFFFFFFFFFFFF
	st.o	rf21, [rb29, 0]
	__VERIFY_MEM	5, SCRATCH, 0, 0x8000000000000000
	st.o	rf20, [rb29, 0]
	__CHECK_MEM	5, SCRATCH, 0, 0x0000000000000000
	@@ 个数 4：四个元素逐对搬移（值互不相同，顺序错位即红）
	__LI_RF	rf40, 0x0123456789ABCDEF
	__LI_RF	rf41, 0xFEDCBA9876543210
	__LI_RF	rf42, 0xAAAAAAAAAAAAAAAA
	__LI_RF	rf43, 0x5555555555555555
	rf2rf	{rf20:rf23}, {rf40:rf43}
	st.o	rf23, [rb29, 0]
	__VERIFY_MEM	6, SCRATCH, 0, 0x5555555555555555
	st.o	rf22, [rb29, 0]
	__VERIFY_MEM	6, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	st.o	rf21, [rb29, 0]
	__VERIFY_MEM	6, SCRATCH, 0, 0xFEDCBA9876543210
	st.o	rf20, [rb29, 0]
	__CHECK_MEM	6, SCRATCH, 0, 0x0123456789ABCDEF

	@@ ---- boundary ----
	@@ 寄存器窗口顶端：{rf60:rf63} ← {rf40:rf43}（起始 60 + 4 = 64，§1 上界）
	__LI_RF	rf40, 0x0F1E2D3C4B5A6978
	__LI_RF	rf41, 0x8000000000000000
	__LI_RF	rf42, 0x0000000000000001
	__LI_RF	rf43, 0x7FFFFFFFFFFFFFFF
	rf2rf	{rf60:rf63}, {rf40:rf43}
	st.o	rf63, [rb29, 0]
	__VERIFY_MEM	7, SCRATCH, 0, 0x7FFFFFFFFFFFFFFF
	st.o	rf62, [rb29, 0]
	__VERIFY_MEM	7, SCRATCH, 0, 0x0000000000000001
	st.o	rf61, [rb29, 0]
	__CHECK_MEM	7, SCRATCH, 0, 0x8000000000000000
	@@ 最高号单寄存器：rf63 ← rf40
	__LI_RF	rf40, 0xC002000000000000
	TEST_MOV1	8, rf2rf, rf63, rf40, 0xC002000000000000
	@@ 最大可行个数 31（{rf1:rf31} ← {rf32:rf62}；同组不许重叠 ⇒ 2n ≤ 63 ⇒ n ≤ 31），
	@@   逐元素核「目的 == 源内存」（源从 MSTORE 装入，不引入额外期望常量）
	LOAD_ADDR rb12, MSTORE
	ldm.o	{rf32:rf62}, [rb12, rd0]
	rf2rf	{rf1:rf31}, {rf32:rf62}
	__VERIFY_MEM_RF	9, MSTORE, 8, rf2
	__VERIFY_MEM_RF	9, MSTORE, 16, rf3
	__VERIFY_MEM_RF	9, MSTORE, 24, rf4
	__VERIFY_MEM_RF	9, MSTORE, 32, rf5
	__VERIFY_MEM_RF	9, MSTORE, 40, rf6
	__VERIFY_MEM_RF	9, MSTORE, 48, rf7
	__VERIFY_MEM_RF	9, MSTORE, 56, rf8
	__VERIFY_MEM_RF	9, MSTORE, 64, rf9
	__VERIFY_MEM_RF	9, MSTORE, 72, rf10
	__VERIFY_MEM_RF	9, MSTORE, 80, rf11
	__VERIFY_MEM_RF	9, MSTORE, 88, rf12
	__VERIFY_MEM_RF	9, MSTORE, 96, rf13
	__VERIFY_MEM_RF	9, MSTORE, 104, rf14
	__VERIFY_MEM_RF	9, MSTORE, 112, rf15
	__VERIFY_MEM_RF	9, MSTORE, 120, rf16
	__VERIFY_MEM_RF	9, MSTORE, 128, rf17
	__VERIFY_MEM_RF	9, MSTORE, 136, rf18
	__VERIFY_MEM_RF	9, MSTORE, 144, rf19
	__VERIFY_MEM_RF	9, MSTORE, 152, rf20
	__VERIFY_MEM_RF	9, MSTORE, 160, rf21
	__VERIFY_MEM_RF	9, MSTORE, 168, rf22
	__VERIFY_MEM_RF	9, MSTORE, 176, rf23
	__VERIFY_MEM_RF	9, MSTORE, 184, rf24
	__VERIFY_MEM_RF	9, MSTORE, 192, rf25
	__VERIFY_MEM_RF	9, MSTORE, 200, rf26
	__VERIFY_MEM_RF	9, MSTORE, 208, rf27
	__VERIFY_MEM_RF	9, MSTORE, 216, rf28
	__VERIFY_MEM_RF	9, MSTORE, 224, rf29
	__VERIFY_MEM_RF	9, MSTORE, 232, rf30
	__VERIFY_MEM_RF	9, MSTORE, 240, rf31
	__CHECK_MEM_RF	9, MSTORE, 0, rf1

	@@ ---- overlap / rf0 ----
	@@ 相邻不相交窗口：{rf40:rf41} ← {rf42:rf43}（合法，无交集）
	__LI_RF	rf42, 0x7FF8000000000000
	__LI_RF	rf43, 0x0000000000000001
	rf2rf	{rf40:rf41}, {rf42:rf43}
	st.o	rf41, [rb29, 0]
	__VERIFY_MEM	10, SCRATCH, 0, 0x0000000000000001
	st.o	rf40, [rb29, 0]
	__CHECK_MEM	10, SCRATCH, 0, 0x7FF8000000000000
	@@ rf0 作源合法：复制出的值 == 同一时刻 rf0 的位型（FCSR，含只读 qNaN 字段）
	TEST_MOV_RF0	11, rf2rf, rf20

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后；汇编器会拒绝的编码用原始字）----
	@@ 目的起始为 rf0 ⇒ ILLI（dst_rf0：同组复制不可写 FCSR）
	TEST_FAULT_ENC	12, ILLI, 0x40F00A01, rb3, TEST_DATA, rd19, 0x000
	@@ immu6=0 ⇒ ILLI（mreg_zero）
	TEST_FAULT_ENC	13, ILLI, 0x40F14A00, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 60 + immu6 8 = 68 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC	14, ILLI, 0x40F3CA08, rb3, TEST_DATA, rd19, 0x000
	@@ 源/目的范围完全重合（dst 20 / src 20 / n=2）⇒ ILLI（mreg_range_overlap）
	TEST_FAULT_ENC	15, ILLI, 0x40F14502, rb3, TEST_DATA, rd19, 0x000
	@@ 源/目的范围部分交错（dst 21..24 ∩ src 20..23）⇒ ILLI（mreg_range_overlap）
	TEST_FAULT_ENC	16, ILLI, 0x40F15504, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 60 + immu6 8 = 68 > 64 ⇒ ILLI（mreg_range_overflow，源侧）
	TEST_FAULT_ENC	17, ILLI, 0x40F01F08, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
