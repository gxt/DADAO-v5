@@ forem_orrr_rf — forem rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x1C，IEEE remainder）
@@ 大类：07-floating-point（浮点运算，`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 每个用例：清 rf0[4:0] → 设 rf0[33:32] → 执行 → 断言 rf0[4:0]（NV=1/DZ=2/OF=4/UF=8/NX=16）
@@   → 比对结果（二者共用点号）；ft 只比低 32 位（高 32 位不作规定）
@@ 初值经 `__LI` + `rd2rf` 装配（不经浮点指令）；期望值由独立 IEEE 754 参考模型复算
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（5 rem 2 = 1）
	TEST_FPENC	1, fo, 0x44705187, rf5, rf6, 0x4014000000000000, rf7, 0x4000000000000000, 0x3FF0000000000000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（7 rem 2 = -1，平局取偶）
	TEST_FPENC	2, fo, 0x4473FFBD, rf63, rf62, 0x401C000000000000, rf61, 0x4000000000000000, 0xBFF0000000000000, 0x00

	@@ ---- semantic ----
	@@ -5 rem 2 = -1（符号随被除数）
	TEST_FP3	3, fo, forem, rf5, rf6, 0xC014000000000000, rf7, 0x4000000000000000, 0, 0xBFF0000000000000, 0x00
	@@ 5 rem -2 = 1（除数符号不传递）
	TEST_FP3	4, fo, forem, rf5, rf6, 0x4014000000000000, rf7, 0xC000000000000000, 0, 0x3FF0000000000000, 0x00
	@@ 5.5 rem 2 = -0.5（n=3，精确余数）
	TEST_FP3	5, fo, forem, rf5, rf6, 0x4016000000000000, rf7, 0x4000000000000000, 0, 0xBFE0000000000000, 0x00
	@@ 5 rem Inf = 5
	TEST_FP3	6, fo, forem, rf5, rf6, 0x4014000000000000, rf7, 0x7FF0000000000000, 0, 0x4014000000000000, 0x00

	@@ ---- boundary ----
	@@ Inf rem 2 ⇒ qNaN + NV
	TEST_FP3	7, fo, forem, rf5, rf6, 0x7FF0000000000000, rf7, 0x4000000000000000, 0, 0x7FF8000000000000, 0x01
	@@ 5 rem 0 ⇒ qNaN + NV（不是 DZ）
	TEST_FP3	8, fo, forem, rf5, rf6, 0x4014000000000000, rf7, 0x0000000000000000, 0, 0x7FF8000000000000, 0x01
	@@ qNaN rem 0 ⇒ qNaN，不置 NV（NaN 优先）
	TEST_FP3	9, fo, forem, rf5, rf6, 0x7FF8000000000000, rf7, 0x0000000000000000, 0, 0x7FF8000000000000, 0x00
	@@ qNaN rem 2.0 ⇒ canonical qNaN（spec §1.4；不传播 payload）
	TEST_FP3	10, fo, forem, rf5, rf6, 0x7FF8000000000123, rf7, 0x4000000000000000, 0, 0x7FF8000000000000, 0x00
	@@ sNaN rem 0 ⇒ qNaN + NV
	TEST_FP3	11, fo, forem, rf5, rf6, 0x7FF0000000000001, rf7, 0x0000000000000000, 0, 0x7FF8000000000000, 0x01
	@@ +0 rem 2 = +0
	TEST_FP3	12, fo, forem, rf5, rf6, 0x0000000000000000, rf7, 0x4000000000000000, 0, 0x0000000000000000, 0x00
	@@ -0 rem 2 = -0
	TEST_FP3	13, fo, forem, rf5, rf6, 0x8000000000000000, rf7, 0x4000000000000000, 0, 0x8000000000000000, 0x00
	@@ 5 rem 5 = +0（零余数取被除数符号）
	TEST_FP3	14, fo, forem, rf5, rf6, 0x4014000000000000, rf7, 0x4014000000000000, 0, 0x0000000000000000, 0x00
	@@ 1.5 rem 1 = -0.5（平局取偶 n=2）
	TEST_FP3	15, fo, forem, rf5, rf6, 0x3FF8000000000000, rf7, 0x3FF0000000000000, 0, 0xBFE0000000000000, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 rem 2）
	TEST_FP3	16, fo, forem, rf9, rf9, 0x4014000000000000, rf7, 0x4000000000000000, 0, 0x3FF0000000000000, 0x00
	@@ 目的 = 源D（rf9 = 5 rem rf9）
	TEST_FP3	17, fo, forem, rf9, rf6, 0x4014000000000000, rf9, 0x4000000000000000, 0, 0x3FF0000000000000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	18, ILLI, 0x44700083

	__TEST_END

	__TEST_SECTIONS
