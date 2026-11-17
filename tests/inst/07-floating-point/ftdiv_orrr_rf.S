@@ ftdiv_orrr_rf — ftdiv rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x13，单精除法）
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
	TEST_FPENC	1, ft, 0x444C5187, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000040100000, 0x000000003F2AAAAB, 0x10
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（1.0 ÷ 1.0 = 1.0）
	TEST_FPENC	2, ft, 0x444FFFBD, rf63, rf62, 0x000000003F800000, rf61, 0x000000003F800000, 0x000000003F800000, 0x00

	@@ ---- semantic ----
	@@ 1.0 ÷ 2.0 = 0.5（精确）
	TEST_FP3	3, ft, ftdiv, rf5, rf6, 0x000000003F800000, rf7, 0x0000000040000000, 0, 0x000000003F000000, 0x00
	@@ -6.0 ÷ 4.0 = -1.5
	TEST_FP3	4, ft, ftdiv, rf5, rf6, 0x0000000040C00000, rf7, 0x0000000040800000, 0, 0x000000003FC00000, 0x00
	@@ 10.0 ÷ 4.0 = 2.5
	TEST_FP3	5, ft, ftdiv, rf5, rf6, 0x0000000041200000, rf7, 0x0000000040800000, 0, 0x0000000040200000, 0x00
	@@ 1.0 ÷ 3.0 ⇒ ft 舍入值 + NX
	TEST_FP3	6, ft, ftdiv, rf5, rf6, 0x000000003F800000, rf7, 0x0000000040400000, 0, 0x000000003EAAAAAB, 0x10

	@@ ---- boundary ----
	@@ 1.0 ÷ +0 ⇒ +Inf + DZ（不是 NV）
	TEST_FP3	7, ft, ftdiv, rf5, rf6, 0x000000003F800000, rf7, 0x0000000000000000, 0, 0x000000007F800000, 0x02
	@@ -1.0 ÷ +0 ⇒ -Inf + DZ
	TEST_FP3	8, ft, ftdiv, rf5, rf6, 0x00000000BF800000, rf7, 0x0000000000000000, 0, 0x00000000FF800000, 0x02
	@@ 0 ÷ 0 ⇒ qNaN + NV
	TEST_FP3	9, ft, ftdiv, rf5, rf6, 0x0000000000000000, rf7, 0x0000000000000000, 0, 0x000000007FC00000, 0x01
	@@ Inf ÷ Inf ⇒ qNaN + NV
	TEST_FP3	10, ft, ftdiv, rf5, rf6, 0x000000007F800000, rf7, 0x000000007F800000, 0, 0x000000007FC00000, 0x01
	@@ qNaN ÷ 2.0 ⇒ canonical qNaN，不置标志
	TEST_FP3	11, ft, ftdiv, rf5, rf6, 0x000000007FC00000, rf7, 0x0000000040000000, 0, 0x000000007FC00000, 0x00
	@@ Inf ÷ 2.0 ⇒ +Inf，不置标志
	TEST_FP3	12, ft, ftdiv, rf5, rf6, 0x000000007F800000, rf7, 0x0000000040000000, 0, 0x000000007F800000, 0x00
	@@ 2.0 ÷ Inf ⇒ +0，不置标志
	TEST_FP3	13, ft, ftdiv, rf5, rf6, 0x0000000040000000, rf7, 0x000000007F800000, 0, 0x0000000000000000, 0x00
	@@ -2.0 ÷ Inf ⇒ -0
	TEST_FP3	14, ft, ftdiv, rf5, rf6, 0x00000000C0000000, rf7, 0x000000007F800000, 0, 0x0000000080000000, 0x00
	@@ ft_max ÷ 0.5 ⇒ +Inf + OF|NX
	TEST_FP3	15, ft, ftdiv, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x000000003F000000, 0, 0x000000007F800000, 0x14
	@@ 最小正规 ÷ 2 ⇒ 次正规 0x00400000，tiny 但精确 ⇒ 不置 UF/NX
	TEST_FP3	16, ft, ftdiv, rf5, rf6, 0x0000000000800000, rf7, 0x0000000040000000, 0, 0x0000000000400000, 0x00
	@@ 最小次正规 ÷ 2 ⇒ +0 + UF|NX
	TEST_FP3	17, ft, ftdiv, rf5, rf6, 0x0000000000000001, rf7, 0x0000000040000000, 0, 0x0000000000000000, 0x18
	@@ 1 ÷ 3 在 RUP 下 ⇒ 上邻值 + NX
	TEST_FP3	18, ft, ftdiv, rf5, rf6, 0x000000003F800000, rf7, 0x0000000040400000, 3, 0x000000003EAAAAAB, 0x10
	@@ 1 ÷ 3 在 RTZ 下 ⇒ 下邻值 + NX
	TEST_FP3	19, ft, ftdiv, rf5, rf6, 0x000000003F800000, rf7, 0x0000000040400000, 1, 0x000000003EAAAAAA, 0x10

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 ÷ 2.0）
	TEST_FP3	20, ft, ftdiv, rf9, rf9, 0x000000003F800000, rf7, 0x0000000040000000, 0, 0x000000003F000000, 0x00
	@@ 两源同名（rf9 = rf6 ÷ rf6 = 1.0）
	TEST_FP3	21, ft, ftdiv, rf9, rf6, 0x0000000040400000, rf6, 0x0000000040400000, 0, 0x000000003F800000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	22, ILLI, 0x444C0083

	__TEST_END

	__TEST_SECTIONS
