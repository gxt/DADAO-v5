@@ fomul_orrr_rf — fomul rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x1A，双精乘法）
@@ 大类：07-floating-point（浮点运算，`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 每个用例：清 rf0[4:0] → 设 rf0[33:32] → 执行 → 断言 rf0[4:0]（NV=1/DZ=2/OF=4/UF=8/NX=16）
@@   → 比对结果（二者共用点号）；ft 只比低 32 位（高 32 位不作规定）
@@ 初值经 `__LI` + `rd2rf` 装配（不经浮点指令）；期望值由独立 IEEE 754 参考模型复算
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（1.5 × 2.25 = 3.375）
	TEST_FPENC	1, fo, 0x44685187, rf5, rf6, 0x3FF8000000000000, rf7, 0x4002000000000000, 0x400B000000000000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（1.0 × (-1.0) = -1.0）
	TEST_FPENC	2, fo, 0x446BFFBD, rf63, rf62, 0x3FF0000000000000, rf61, 0xBFF0000000000000, 0xBFF0000000000000, 0x00

	@@ ---- semantic ----
	@@ 1.5 × 2.0 = 3.0
	TEST_FP3	3, fo, fomul, rf5, rf6, 0x3FF8000000000000, rf7, 0x4000000000000000, 0, 0x4008000000000000, 0x00
	@@ -1.5 × 2.5 = -3.75
	TEST_FP3	4, fo, fomul, rf5, rf6, 0xBFF8000000000000, rf7, 0x4004000000000000, 0, 0xC00E000000000000, 0x00
	@@ 0.5 × 0.5 = 0.25
	TEST_FP3	5, fo, fomul, rf5, rf6, 0x3FE0000000000000, rf7, 0x3FE0000000000000, 0, 0x3FD0000000000000, 0x00
	@@ 0.1 × 0.2 ⇒ 双精舍入值 + NX
	TEST_FP3	6, fo, fomul, rf5, rf6, 0x3FB999999999999A, rf7, 0x3FC999999999999A, 0, 0x3F947AE147AE147C, 0x10

	@@ ---- boundary ----
	@@ 0 × Inf ⇒ qNaN + NV
	TEST_FP3	7, fo, fomul, rf5, rf6, 0x0000000000000000, rf7, 0x7FF0000000000000, 0, 0x7FF8000000000000, 0x01
	@@ qNaN × 0 ⇒ qNaN，不置 NV
	TEST_FP3	8, fo, fomul, rf5, rf6, 0x7FF8000000000000, rf7, 0x0000000000000000, 0, 0x7FF8000000000000, 0x00
	@@ sNaN × 2.0 ⇒ qNaN + NV
	TEST_FP3	9, fo, fomul, rf5, rf6, 0x7FF0000000000001, rf7, 0x4000000000000000, 0, 0x7FF8000000000000, 0x01
	@@ Inf × 2.0 ⇒ +Inf
	TEST_FP3	10, fo, fomul, rf5, rf6, 0x7FF0000000000000, rf7, 0x4000000000000000, 0, 0x7FF0000000000000, 0x00
	@@ fo_max × 2 ⇒ +Inf + OF|NX（RNE）
	TEST_FP3	11, fo, fomul, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x4000000000000000, 0, 0x7FF0000000000000, 0x14
	@@ fo_max × 2 在 RTZ 下 ⇒ fo_max + OF|NX
	TEST_FP3	12, fo, fomul, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x4000000000000000, 1, 0x7FEFFFFFFFFFFFFF, 0x14
	@@ 最小次正规 × 0.5 ⇒ +0 + UF|NX
	TEST_FP3	13, fo, fomul, rf5, rf6, 0x0000000000000001, rf7, 0x3FE0000000000000, 0, 0x0000000000000000, 0x18
	@@ 最小正规 × 0.5 ⇒ 次正规 0x0008000000000000，不置 UF/NX
	TEST_FP3	14, fo, fomul, rf5, rf6, 0x0010000000000000, rf7, 0x3FE0000000000000, 0, 0x0008000000000000, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 × 2.0）
	TEST_FP3	15, fo, fomul, rf9, rf9, 0x3FF8000000000000, rf7, 0x4000000000000000, 0, 0x4008000000000000, 0x00
	@@ 两源同名（rf9 = rf6 × rf6）
	TEST_FP3	16, fo, fomul, rf9, rf6, 0x3FF8000000000000, rf6, 0x3FF8000000000000, 0, 0x4002000000000000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	17, ILLI, 0x44680083

	__TEST_END

	__TEST_SECTIONS
