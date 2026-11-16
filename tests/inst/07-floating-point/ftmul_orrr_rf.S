@@ ftmul_orrr_rf — ftmul rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x12，单精乘法）
@@ 大类：07-floating-point（浮点运算，`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 每个用例：清 rf0[4:0] → 设 rf0[33:32] → 执行 → 断言 rf0[4:0]（NV=1/DZ=2/OF=4/UF=8/NX=16）
@@   → 比对结果（二者共用点号）；ft 只比低 32 位（高 32 位不作规定）
@@ 初值经 `__LI` + `rd2rf` 装配（不经浮点指令）；期望值由独立 IEEE 754 参考模型复算
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（1.5 × 2.25 = 3.375）
	TEST_FPENC	1, ft, 0x44485187, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000040100000, 0x0000000040580000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（1.0 × (-1.0) = -1.0）
	TEST_FPENC	2, ft, 0x444BFFBD, rf63, rf62, 0x000000003F800000, rf61, 0x00000000BF800000, 0x00000000BF800000, 0x00

	@@ ---- semantic ----
	@@ 1.5 × 2.0 = 3.0
	TEST_FP3	3, ft, ftmul, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000040000000, 0, 0x0000000040400000, 0x00
	@@ -1.5 × 2.5 = -3.75
	TEST_FP3	4, ft, ftmul, rf5, rf6, 0x00000000BFC00000, rf7, 0x0000000040200000, 0, 0x00000000C0700000, 0x00
	@@ 0.5 × 0.5 = 0.25（精确）
	TEST_FP3	5, ft, ftmul, rf5, rf6, 0x000000003F000000, rf7, 0x000000003F000000, 0, 0x000000003E800000, 0x00
	@@ 0.1 × 0.2 ⇒ ft 舍入值 + NX
	TEST_FP3	6, ft, ftmul, rf5, rf6, 0x000000003DCCCCCD, rf7, 0x000000003E4CCCCD, 0, 0x000000003CA3D70B, 0x10

	@@ ---- boundary ----
	@@ 0 × Inf ⇒ qNaN + NV（无效操作，优先于 NaN 传播）
	TEST_FP3	7, ft, ftmul, rf5, rf6, 0x0000000000000000, rf7, 0x000000007F800000, 0, 0x000000007FC00000, 0x01
	@@ qNaN × 0 ⇒ qNaN，不置 NV（NaN 优先于 0×Inf）
	TEST_FP3	8, ft, ftmul, rf5, rf6, 0x000000007FC00000, rf7, 0x0000000000000000, 0, 0x000000007FC00000, 0x00
	@@ sNaN × 2.0 ⇒ qNaN + NV
	TEST_FP3	9, ft, ftmul, rf5, rf6, 0x000000007F800001, rf7, 0x0000000040000000, 0, 0x000000007FC00000, 0x01
	@@ Inf × 2.0 ⇒ +Inf，不置标志
	TEST_FP3	10, ft, ftmul, rf5, rf6, 0x000000007F800000, rf7, 0x0000000040000000, 0, 0x000000007F800000, 0x00
	@@ ft_max × 2 ⇒ +Inf + OF|NX（RNE）
	TEST_FP3	11, ft, ftmul, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x0000000040000000, 0, 0x000000007F800000, 0x14
	@@ ft_max × 2 在 RTZ 下 ⇒ ft_max + OF|NX
	TEST_FP3	12, ft, ftmul, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x0000000040000000, 1, 0x000000007F7FFFFF, 0x14
	@@ 最小次正规 × 0.5 ⇒ +0 + UF|NX
	TEST_FP3	13, ft, ftmul, rf5, rf6, 0x0000000000000001, rf7, 0x000000003F000000, 0, 0x0000000000000000, 0x18
	@@ 最小正规 × 0.5 ⇒ 次正规 0x00400000，tiny 但精确 ⇒ 不置 UF/NX
	TEST_FP3	14, ft, ftmul, rf5, rf6, 0x0000000000800000, rf7, 0x000000003F000000, 0, 0x0000000000400000, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 × 2.0）
	TEST_FP3	15, ft, ftmul, rf9, rf9, 0x000000003FC00000, rf7, 0x0000000040000000, 0, 0x0000000040400000, 0x00
	@@ 两源同名（rf9 = rf6 × rf6）
	TEST_FP3	16, ft, ftmul, rf9, rf6, 0x000000003FC00000, rf6, 0x000000003FC00000, 0, 0x0000000040100000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	17, ILLI, 0x44480083

	__TEST_END

	__TEST_SECTIONS
