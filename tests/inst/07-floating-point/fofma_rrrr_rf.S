@@ fofma_rrrr_rf — fofma rfHA, rfHB, rfHC, rfHD（rrrr, opc 0x5F，fused multiply-add，单次舍入）
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
	@@ 规范编码字：dst=rf5 / b=rf6(2) / c=rf7(3) / d=rf8(4) ⇒ 10
	TEST_FPENC4	1, fo, 0x5F1461C8, rf5, rf6, 0x4000000000000000, rf7, 0x4008000000000000, rf8, 0x4010000000000000, 0x4024000000000000, 0x00
	@@ 字段边界：dst=rf63 / b=rf62(1) / c=rf61(1) / d=rf60(-1) ⇒ +0
	TEST_FPENC4	2, fo, 0x5FFFEF7C, rf63, rf62, 0x3FF0000000000000, rf61, 0x3FF0000000000000, rf60, 0xBFF0000000000000, 0x0000000000000000, 0x00

	@@ ---- semantic ----
	@@ 2 × 3 + 4 = 10
	TEST_FP4	3, fo, fofma, rf5, rf6, 0x4000000000000000, rf7, 0x4008000000000000, rf8, 0x4010000000000000, 0, 0x4024000000000000, 0x00
	@@ 双精反例：(1+2^-52)(1-2^-52) - 1 = -2^-104（单次舍入）
	TEST_FP4	4, fo, fofma, rf5, rf6, 0x3FF0000000000001, rf7, 0x3FEFFFFFFFFFFFFF, rf8, 0xBFF0000000000000, 0, 0x3C9FFFFFFFFFFFFE, 0x00
	@@ -2 × 3 + 1 = -5
	TEST_FP4	5, fo, fofma, rf5, rf6, 0xC000000000000000, rf7, 0x4008000000000000, rf8, 0x3FF0000000000000, 0, 0xC014000000000000, 0x00
	@@ 0.5 × 0.5 + 0.25 = 0.5
	TEST_FP4	6, fo, fofma, rf5, rf6, 0x3FE0000000000000, rf7, 0x3FE0000000000000, rf8, 0x3FD0000000000000, 0, 0x3FE0000000000000, 0x00

	@@ ---- boundary ----
	@@ 0 × Inf + qNaN ⇒ qNaN + NV
	TEST_FP4	7, fo, fofma, rf5, rf6, 0x0000000000000000, rf7, 0x7FF0000000000000, rf8, 0x7FF8000000000000, 0, 0x7FF8000000000000, 0x01
	@@ Inf × 2 + (-Inf) ⇒ qNaN + NV
	TEST_FP4	8, fo, fofma, rf5, rf6, 0x7FF0000000000000, rf7, 0x4000000000000000, rf8, 0xFFF0000000000000, 0, 0x7FF8000000000000, 0x01
	@@ Inf × 2 + 1 ⇒ +Inf
	TEST_FP4	9, fo, fofma, rf5, rf6, 0x7FF0000000000000, rf7, 0x4000000000000000, rf8, 0x3FF0000000000000, 0, 0x7FF0000000000000, 0x00
	@@ qNaN × 1 + 1 ⇒ qNaN，不置标志
	TEST_FP4	10, fo, fofma, rf5, rf6, 0x7FF8000000000000, rf7, 0x3FF0000000000000, rf8, 0x3FF0000000000000, 0, 0x7FF8000000000000, 0x00
	@@ sNaN × 1 + 1 ⇒ qNaN + NV
	TEST_FP4	11, fo, fofma, rf5, rf6, 0x7FF0000000000001, rf7, 0x3FF0000000000000, rf8, 0x3FF0000000000000, 0, 0x7FF8000000000000, 0x01
	@@ 1 × 1 + (-1) ⇒ +0（RNE）
	TEST_FP4	12, fo, fofma, rf5, rf6, 0x3FF0000000000000, rf7, 0x3FF0000000000000, rf8, 0xBFF0000000000000, 0, 0x0000000000000000, 0x00
	@@ 1 × 1 + (-1) ⇒ -0（RDN）
	TEST_FP4	13, fo, fofma, rf5, rf6, 0x3FF0000000000000, rf7, 0x3FF0000000000000, rf8, 0xBFF0000000000000, 2, 0x8000000000000000, 0x00
	@@ fo_max × 2 + 0 ⇒ +Inf + OF|NX（RNE）
	TEST_FP4	14, fo, fofma, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x4000000000000000, rf8, 0x0000000000000000, 0, 0x7FF0000000000000, 0x14
	@@ fo_max × 2 + 0 在 RTZ 下 ⇒ fo_max + OF|NX
	TEST_FP4	15, fo, fofma, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x4000000000000000, rf8, 0x0000000000000000, 1, 0x7FEFFFFFFFFFFFFF, 0x14
	@@ 最小次正规 × 0.5 + 0 ⇒ +0 + UF|NX
	TEST_FP4	16, fo, fofma, rf5, rf6, 0x0000000000000001, rf7, 0x3FE0000000000000, rf8, 0x0000000000000000, 0, 0x0000000000000000, 0x18

	@@ ---- overlap ----
	@@ 目的 = 第一乘数（rf9 = rf9 × 2 + 4）
	TEST_FP4	17, fo, fofma, rf9, rf9, 0x4000000000000000, rf7, 0x4000000000000000, rf8, 0x4010000000000000, 0, 0x4020000000000000, 0x00
	@@ 目的 = 第二乘数（rf9 = 2 × rf9 + 4）
	TEST_FP4	18, fo, fofma, rf9, rf6, 0x4000000000000000, rf9, 0x4000000000000000, rf8, 0x4010000000000000, 0, 0x4020000000000000, 0x00
	@@ 目的 = 加数（rf9 = 2 × 3 + rf9）
	TEST_FP4	19, fo, fofma, rf9, rf6, 0x4000000000000000, rf7, 0x4008000000000000, rf9, 0x4010000000000000, 0, 0x4024000000000000, 0x00

	@@ ---- 收窄补点（m13-testcases-044；原 C 探针覆盖、本载体缺的边界，依据 `spec/SimRISC-07 §2.5`）----
	@@ 轻微溢出（`§2.5`「溢出」末段）：精确和 = fo_max + 2^969（1/4 ulp，ulp = 2^971）> max，
	@@   但 RNE 的无限指数舍入结果仍为 fo_max ⇒ 不构成溢出 ⇒ 结果 fo_max、只置 NX
	TEST_FP4	20, fo, fofma, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x3FF0000000000000, rf8, 0x7C80000000000000, 0, 0x7FEFFFFFFFFFFFFF, 0x10
	@@ 同一输入在 RUP 下舍到 2^1024 > max ⇒ 溢出 ⇒ +Inf + OF|NX
	TEST_FP4	21, fo, fofma, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x3FF0000000000000, rf8, 0x7C80000000000000, 3, 0x7FF0000000000000, 0x14
	@@ 次正规结果且 inexact：精确和 = 2^-1074 × 1.25 = 1.25 单位 ⇒ RNE 舍到 1 单位（2^-1074），UF|NX
	TEST_FP4	22, fo, fofma, rf5, rf6, 0x0000000000000001, rf7, 0x3FF4000000000000, rf8, 0x0000000000000000, 0, 0x0000000000000001, 0x18
	@@ 同一输入在 RUP 下舍到 2 单位（2^-1073），UF|NX
	TEST_FP4	23, fo, fofma, rf5, rf6, 0x0000000000000001, rf7, 0x3FF4000000000000, rf8, 0x0000000000000000, 3, 0x0000000000000002, 0x18
	@@ Inf 作加数：1 × 2 + (−Inf) ⇒ −Inf，不置标志（`§2.5`「特例」第 3 条）
	TEST_FP4	24, fo, fofma, rf5, rf6, 0x3FF0000000000000, rf7, 0x4000000000000000, rf8, 0xFFF0000000000000, 0, 0xFFF0000000000000, 0x00

	@@ ---- 边界补齐（m20-testcases-010；0×±Inf / 加数 NaN / 次正规精确 / 负溢出，`SimRISC-07 §2.5/§1.3`）----
	@@ 0 × (−Inf) + qNaN ⇒ canonical qNaN + NV（零乘无穷无效运算优先于 NaN 传播，符号无关）
	TEST_FP4	25, fo, fofma, rf5, rf6, 0x0000000000000000, rf7, 0xFFF0000000000000, rf8, 0x7FF8000000000000, 0, 0x7FF8000000000000, 0x01
	@@ 加数为 sNaN：1 × 1 + sNaN ⇒ canonical qNaN + NV
	TEST_FP4	26, fo, fofma, rf5, rf6, 0x3FF0000000000000, rf7, 0x3FF0000000000000, rf8, 0x7FF0000000000001, 0, 0x7FF8000000000000, 0x01
	@@ 加数为负号 qNaN（含 payload）⇒ canonical 正 qNaN，不置标志
	TEST_FP4	27, fo, fofma, rf5, rf6, 0x3FF0000000000000, rf7, 0x3FF0000000000000, rf8, 0xFFF8000000000123, 0, 0x7FF8000000000000, 0x00
	@@ 最小次正规 × 1 + 最小次正规 = 2^-1073（精确次正规输出）⇒ 不置 UF/NX
	TEST_FP4	28, fo, fofma, rf5, rf6, 0x0000000000000001, rf7, 0x3FF0000000000000, rf8, 0x0000000000000001, 0, 0x0000000000000002, 0x00
	@@ 最大次正规 × 1 + 最小次正规 = 最小正规（精确进位）⇒ 不置 UF/NX
	TEST_FP4	29, fo, fofma, rf5, rf6, 0x000FFFFFFFFFFFFF, rf7, 0x3FF0000000000000, rf8, 0x0000000000000001, 0, 0x0010000000000000, 0x00
	@@ −fo_max × 2 + 0 在 RDN 下 ⇒ −Inf + OF|NX
	TEST_FP4	30, fo, fofma, rf5, rf6, 0xFFEFFFFFFFFFFFFF, rf7, 0x4000000000000000, rf8, 0x0000000000000000, 2, 0xFFF0000000000000, 0x14
	@@ 同一输入在 RTZ 下 ⇒ −fo_max + OF|NX（溢出 ≠ Inf）
	TEST_FP4	31, fo, fofma, rf5, rf6, 0xFFEFFFFFFFFFFFFF, rf7, 0x4000000000000000, rf8, 0x0000000000000000, 1, 0xFFEFFFFFFFFFFFFF, 0x14
	@@ 同一输入在 RUP 下 ⇒ −fo_max + OF|NX
	TEST_FP4	32, fo, fofma, rf5, rf6, 0xFFEFFFFFFFFFFFFF, rf7, 0x4000000000000000, rf8, 0x0000000000000000, 3, 0xFFEFFFFFFFFFFFFF, 0x14
	@@ +fo_max × 2 + 0 在 RDN 下 ⇒ +fo_max + OF|NX（溢出 ≠ Inf）
	TEST_FP4	33, fo, fofma, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x4000000000000000, rf8, 0x0000000000000000, 2, 0x7FEFFFFFFFFFFFFF, 0x14

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	34, ILLI, 0x5F0020C4

	__TEST_END

	__TEST_SECTIONS
