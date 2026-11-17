@@ fodiv_orrr_rf — fodiv rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x1B，双精除法）
@@ 大类：07-floating-point（浮点运算，`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 每个用例：清 rf0[4:0] → 设 rf0[33:32] → 执行 → 断言 rf0[4:0]（NV=1/DZ=2/OF=4/UF=8/NX=16）
@@   → 比对结果（二者共用点号）；ft 只比低 32 位（高 32 位不作规定）
@@ 初值经 `set.fo` 装配（整 64 位：`rd2rf rf, rd0` + 非零 wyde 的 `set.w`；不经浮点指令）；期望值由独立 IEEE 754 参考模型复算
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（1.5 ÷ 2.25）
	TEST_FPENC	1, fo, 0x446C5187, rf5, rf6, 0x3FF8000000000000, rf7, 0x4002000000000000, 0x3FE5555555555555, 0x10
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（1.0 ÷ 1.0 = 1.0）
	TEST_FPENC	2, fo, 0x446FFFBD, rf63, rf62, 0x3FF0000000000000, rf61, 0x3FF0000000000000, 0x3FF0000000000000, 0x00

	@@ ---- semantic ----
	@@ 1.0 ÷ 2.0 = 0.5
	TEST_FP3	3, fo, fodiv, rf5, rf6, 0x3FF0000000000000, rf7, 0x4000000000000000, 0, 0x3FE0000000000000, 0x00
	@@ -6.0 ÷ 4.0 = -1.5
	TEST_FP3	4, fo, fodiv, rf5, rf6, 0x4018000000000000, rf7, 0x4010000000000000, 0, 0x3FF8000000000000, 0x00
	@@ 10.0 ÷ 4.0 = 2.5
	TEST_FP3	5, fo, fodiv, rf5, rf6, 0x4024000000000000, rf7, 0x4010000000000000, 0, 0x4004000000000000, 0x00
	@@ 1.0 ÷ 3.0 ⇒ 双精舍入值 + NX
	TEST_FP3	6, fo, fodiv, rf5, rf6, 0x3FF0000000000000, rf7, 0x4008000000000000, 0, 0x3FD5555555555555, 0x10

	@@ ---- boundary ----
	@@ 1.0 ÷ +0 ⇒ +Inf + DZ
	TEST_FP3	7, fo, fodiv, rf5, rf6, 0x3FF0000000000000, rf7, 0x0000000000000000, 0, 0x7FF0000000000000, 0x02
	@@ -1.0 ÷ +0 ⇒ -Inf + DZ
	TEST_FP3	8, fo, fodiv, rf5, rf6, 0xBFF0000000000000, rf7, 0x0000000000000000, 0, 0xFFF0000000000000, 0x02
	@@ 0 ÷ 0 ⇒ qNaN + NV
	TEST_FP3	9, fo, fodiv, rf5, rf6, 0x0000000000000000, rf7, 0x0000000000000000, 0, 0x7FF8000000000000, 0x01
	@@ Inf ÷ Inf ⇒ qNaN + NV
	TEST_FP3	10, fo, fodiv, rf5, rf6, 0x7FF0000000000000, rf7, 0x7FF0000000000000, 0, 0x7FF8000000000000, 0x01
	@@ qNaN ÷ 2.0 ⇒ canonical qNaN，不置标志
	TEST_FP3	11, fo, fodiv, rf5, rf6, 0x7FF8000000000000, rf7, 0x4000000000000000, 0, 0x7FF8000000000000, 0x00
	@@ Inf ÷ 2.0 ⇒ +Inf
	TEST_FP3	12, fo, fodiv, rf5, rf6, 0x7FF0000000000000, rf7, 0x4000000000000000, 0, 0x7FF0000000000000, 0x00
	@@ 2.0 ÷ Inf ⇒ +0
	TEST_FP3	13, fo, fodiv, rf5, rf6, 0x4000000000000000, rf7, 0x7FF0000000000000, 0, 0x0000000000000000, 0x00
	@@ -2.0 ÷ Inf ⇒ -0
	TEST_FP3	14, fo, fodiv, rf5, rf6, 0xC000000000000000, rf7, 0x7FF0000000000000, 0, 0x8000000000000000, 0x00
	@@ fo_max ÷ 0.5 ⇒ +Inf + OF|NX
	TEST_FP3	15, fo, fodiv, rf5, rf6, 0x7FEFFFFFFFFFFFFF, rf7, 0x3FE0000000000000, 0, 0x7FF0000000000000, 0x14
	@@ 最小正规 ÷ 2 ⇒ 次正规，不置 UF/NX
	TEST_FP3	16, fo, fodiv, rf5, rf6, 0x0010000000000000, rf7, 0x4000000000000000, 0, 0x0008000000000000, 0x00
	@@ 最小次正规 ÷ 2 ⇒ +0 + UF|NX
	TEST_FP3	17, fo, fodiv, rf5, rf6, 0x0000000000000001, rf7, 0x4000000000000000, 0, 0x0000000000000000, 0x18
	@@ 1 ÷ 3 在 RUP 下 ⇒ 上邻值 + NX
	TEST_FP3	18, fo, fodiv, rf5, rf6, 0x3FF0000000000000, rf7, 0x4008000000000000, 3, 0x3FD5555555555556, 0x10
	@@ 1 ÷ 3 在 RTZ 下 ⇒ 下邻值 + NX
	TEST_FP3	19, fo, fodiv, rf5, rf6, 0x3FF0000000000000, rf7, 0x4008000000000000, 1, 0x3FD5555555555555, 0x10

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 ÷ 2.0）
	TEST_FP3	20, fo, fodiv, rf9, rf9, 0x3FF0000000000000, rf7, 0x4000000000000000, 0, 0x3FE0000000000000, 0x00
	@@ 两源同名（rf9 = rf6 ÷ rf6 = 1.0）
	TEST_FP3	21, fo, fodiv, rf9, rf6, 0x4008000000000000, rf6, 0x4008000000000000, 0, 0x3FF0000000000000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	22, ILLI, 0x446C0083

	__TEST_END

	__TEST_SECTIONS
