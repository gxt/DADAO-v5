@@ ftmax_orrr_rf — ftmax rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x27，单精 maximumNumber）
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
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（max(1.5, 2.5) = 2.5）
	TEST_FPENC	1, ft, 0x449C5187, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000040200000, 0x0000000040200000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（max(-max, max) = max）
	TEST_FPENC	2, ft, 0x449FFFBD, rf63, rf62, 0x00000000FF7FFFFF, rf61, 0x000000007F7FFFFF, 0x000000007F7FFFFF, 0x00

	@@ ---- semantic ----
	@@ max(1.5, 2.5) = 2.5
	TEST_FP3	3, ft, ftmax, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000040200000, 0, 0x0000000040200000, 0x00
	@@ max(-1.5, -2.5) = -1.5
	TEST_FP3	4, ft, ftmax, rf5, rf6, 0x00000000BFC00000, rf7, 0x00000000C0200000, 0, 0x00000000BFC00000, 0x00
	@@ max(1.5, 1.5) = 1.5
	TEST_FP3	5, ft, ftmax, rf5, rf6, 0x000000003FC00000, rf7, 0x000000003FC00000, 0, 0x000000003FC00000, 0x00
	@@ max(+Inf, 1.0) = +Inf
	TEST_FP3	6, ft, ftmax, rf5, rf6, 0x000000007F800000, rf7, 0x000000003F800000, 0, 0x000000007F800000, 0x00

	@@ ---- boundary ----
	@@ max(+0, -0) = +0（不得返回 -0）
	TEST_FP3	7, ft, ftmax, rf5, rf6, 0x0000000000000000, rf7, 0x0000000080000000, 0, 0x0000000000000000, 0x00
	@@ max(-0, +0) = +0（顺序无关）
	TEST_FP3	8, ft, ftmax, rf5, rf6, 0x0000000080000000, rf7, 0x0000000000000000, 0, 0x0000000000000000, 0x00
	@@ max(qNaN, 1.0) = 1.0，不置标志
	TEST_FP3	9, ft, ftmax, rf5, rf6, 0x000000007FC00000, rf7, 0x000000003F800000, 0, 0x000000003F800000, 0x00
	@@ max(1.0, qNaN) = 1.0，不置标志
	TEST_FP3	10, ft, ftmax, rf5, rf6, 0x000000003F800000, rf7, 0x000000007FC00000, 0, 0x000000003F800000, 0x00
	@@ max(sNaN, 1.0) = 1.0 + NV
	TEST_FP3	11, ft, ftmax, rf5, rf6, 0x000000007F800001, rf7, 0x000000003F800000, 0, 0x000000003F800000, 0x01
	@@ max(qNaN, qNaN) = canonical qNaN，不置标志
	TEST_FP3	12, ft, ftmax, rf5, rf6, 0x000000007FC00001, rf7, 0x000000007FC00000, 0, 0x000000007FC00000, 0x00
	@@ max(qNaN, sNaN) = canonical qNaN + NV
	TEST_FP3	13, ft, ftmax, rf5, rf6, 0x000000007F800001, rf7, 0x000000007FC00000, 0, 0x000000007FC00000, 0x01
	@@ max(-Inf, ft_max) = ft_max
	TEST_FP3	14, ft, ftmax, rf5, rf6, 0x00000000FF800000, rf7, 0x000000007F7FFFFF, 0, 0x000000007F7FFFFF, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = max(rf9, 2.5)）
	TEST_FP3	15, ft, ftmax, rf9, rf9, 0x000000003FC00000, rf7, 0x0000000040200000, 0, 0x0000000040200000, 0x00
	@@ 目的 = 源D（rf9 = max(2.5, rf9)）
	TEST_FP3	16, ft, ftmax, rf9, rf6, 0x0000000040200000, rf9, 0x000000003FC00000, 0, 0x0000000040200000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	17, ILLI, 0x449C0083

	__TEST_END

	__TEST_SECTIONS
