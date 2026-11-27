@@ foadd_orrr_rf — foadd rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x18，双精加法）
@@ 大类：07-floating-point（浮点运算，`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 每个用例：清 rf0[4:0] → 设 rf0[33:32] → 执行 → 断言 rf0[4:0]（NV=1/DZ=2/OF=4/UF=8/NX=16）
@@   → 比对结果（二者共用点号）；ft 只比低 32 位（高 32 位不作规定）
@@ 初值经 `set.fo` 装配（整 64 位：`rd2rf rf, rd0` + 非零 wyde 的 `set.w`；不经浮点指令）；期望值由独立 IEEE 754 参考模型复算
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（1.5 + 2.25 = 3.75）
	TEST_FPENC	1, fo, 0x44605187, rf5, rf6, 0x3FF8000000000000, rf7, 0x4002000000000000, 0x400E000000000000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（1.0 + (-1.0) = +0）
	TEST_FPENC	2, fo, 0x4463FFBD, rf63, rf62, 0x3FF0000000000000, rf61, 0xBFF0000000000000, 0x0000000000000000, 0x00

	@@ ---- semantic ----
	@@ 1.0 + 2.0 = 3.0
	TEST_FP3	3, fo, foadd, rf5, rf6, 0x3FF0000000000000, rf7, 0x4000000000000000, 0, 0x4008000000000000, 0x00
	@@ -1.5 + 2.25 = 0.75
	TEST_FP3	4, fo, foadd, rf5, rf6, 0xBFF8000000000000, rf7, 0x4002000000000000, 0, 0x3FE8000000000000, 0x00
	@@ 0.1 + 0.2 ⇒ 双精舍入值 + NX
	TEST_FP3	5, fo, foadd, rf5, rf6, 0x3FB999999999999A, rf7, 0x3FC999999999999A, 0, 0x3FD3333333333334, 0x10
	@@ 1.5 + 0 = 1.5
	TEST_FP3	6, fo, foadd, rf5, rf6, 0x3FF8000000000000, rf7, 0x0000000000000000, 0, 0x3FF8000000000000, 0x00

	@@ ---- boundary ----
	@@ 1.5 + (-1.5) 精确抵消 ⇒ +0（RNE）
	TEST_FP3	7, fo, foadd, rf5, rf6, 0x3FF8000000000000, rf7, 0xBFF8000000000000, 0, 0x0000000000000000, 0x00
	@@ 同一抵消在 RDN 下 ⇒ -0
	TEST_FP3	8, fo, foadd, rf5, rf6, 0x3FF8000000000000, rf7, 0xBFF8000000000000, 2, 0x8000000000000000, 0x00
	@@ qNaN + 1.0 ⇒ canonical qNaN，不置标志
	TEST_FP3	9, fo, foadd, rf5, rf6, 0x7FF8000000000000, rf7, 0x3FF0000000000000, 0, 0x7FF8000000000000, 0x00
	@@ sNaN + 1.0 ⇒ canonical qNaN + NV
	TEST_FP3	10, fo, foadd, rf5, rf6, 0x7FF0000000000001, rf7, 0x3FF0000000000000, 0, 0x7FF8000000000000, 0x01
	@@ +Inf + (-Inf) ⇒ qNaN + NV
	TEST_FP3	11, fo, foadd, rf5, rf6, 0x7FF0000000000000, rf7, 0xFFF0000000000000, 0, 0x7FF8000000000000, 0x01
	@@ +Inf + 1.0 ⇒ +Inf
	TEST_FP3	12, fo, foadd, rf5, rf6, 0x7FF0000000000000, rf7, 0x3FF0000000000000, 0, 0x7FF0000000000000, 0x00
	@@ fo_max + fo_max ⇒ +Inf + OF|NX（RNE）
	TEST_FP3	13, fo, foadd, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x7FEFFFFFFFFFFFFF, 0, 0x7FF0000000000000, 0x14
	@@ fo_max + fo_max 在 RTZ 下 ⇒ fo_max + OF|NX
	TEST_FP3	14, fo, foadd, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x7FEFFFFFFFFFFFFF, 1, 0x7FEFFFFFFFFFFFFF, 0x14
	@@ 1.0 + 2^-54 恰在 RNE 中点 ⇒ 1.0 + NX
	TEST_FP3	15, fo, foadd, rf5, rf6, 0x3FF0000000000000, rf7, 0x3C90000000000000, 0, 0x3FF0000000000000, 0x10
	@@ 同一和在 RUP 下 ⇒ 1+2^-52 + NX
	TEST_FP3	16, fo, foadd, rf5, rf6, 0x3FF0000000000000, rf7, 0x3C90000000000000, 3, 0x3FF0000000000001, 0x10

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 + 2.25）
	TEST_FP3	17, fo, foadd, rf9, rf9, 0x3FF8000000000000, rf7, 0x4002000000000000, 0, 0x400E000000000000, 0x00
	@@ 两源同名（rf9 = rf6 + rf6）
	TEST_FP3	18, fo, foadd, rf9, rf6, 0x3FF8000000000000, rf6, 0x3FF8000000000000, 0, 0x4008000000000000, 0x00

	@@ ---- 边界补齐（m20-testcases-010；次正规 / NaN canonical 化 / 溢出剩余象限，`SimRISC-07 §1.3/§2.1`）----
	@@ 负号 qNaN（含 payload）+ 1.0 ⇒ canonical 正 qNaN，不置标志（payload/符号归零）
	TEST_FP3	19, fo, foadd, rf5, rf6, 0xFFF8000000000123, rf7, 0x3FF0000000000000, 0, 0x7FF8000000000000, 0x00
	@@ 最小次正规 + 最小次正规 = 2^-1073（精确次正规输出）⇒ 不置 UF/NX
	TEST_FP3	20, fo, foadd, rf5, rf6, 0x0000000000000001, rf7, 0x0000000000000001, 0, 0x0000000000000002, 0x00
	@@ 最大次正规 + 最小次正规 = 最小正规（精确进位）⇒ 不置 UF/NX
	TEST_FP3	21, fo, foadd, rf5, rf6, 0x000FFFFFFFFFFFFF, rf7, 0x0000000000000001, 0, 0x0010000000000000, 0x00
	@@ 最大次正规 + 最大次正规 = 0x001FFFFFFFFFFFFE（精确，和进入正规区）⇒ 不置 UF/NX
	TEST_FP3	22, fo, foadd, rf5, rf6, 0x000FFFFFFFFFFFFF, rf7, 0x000FFFFFFFFFFFFF, 0, 0x001FFFFFFFFFFFFE, 0x00
	@@ 正溢出 RUP ⇒ +Inf + OF|NX
	TEST_FP3	23, fo, foadd, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x7FEFFFFFFFFFFFFF, 3, 0x7FF0000000000000, 0x14
	@@ 正溢出 RDN ⇒ +fo_max + OF|NX（溢出 ≠ Inf）
	TEST_FP3	24, fo, foadd, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x7FEFFFFFFFFFFFFF, 2, 0x7FEFFFFFFFFFFFFF, 0x14
	@@ 负溢出 RDN ⇒ −Inf + OF|NX
	TEST_FP3	25, fo, foadd, rf5, rf6, 0xFFEFFFFFFFFFFFFF, rf7, 0xFFEFFFFFFFFFFFFF, 2, 0xFFF0000000000000, 0x14
	@@ 负溢出 RUP ⇒ −fo_max + OF|NX（溢出 ≠ Inf）
	TEST_FP3	26, fo, foadd, rf5, rf6, 0xFFEFFFFFFFFFFFFF, rf7, 0xFFEFFFFFFFFFFFFF, 3, 0xFFEFFFFFFFFFFFFF, 0x14
	@@ 次正规输入参与 RUP 舍入：1.0 + 2^-1074 ⇒ 1+2^-52 + NX（不置 UF；证明低位粘位未被丢弃）
	TEST_FP3	27, fo, foadd, rf5, rf6, 0x3FF0000000000000, rf7, 0x0000000000000001, 3, 0x3FF0000000000001, 0x10

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	28, ILLI, 0x44600083

	__TEST_END

	__TEST_SECTIONS
