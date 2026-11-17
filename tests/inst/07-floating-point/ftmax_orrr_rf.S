@@ ftmax_orrr_rf — ftmax rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x27，单精 maximumNumber）
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

	@@ ---- 收窄补点（m13-testcases-044；原 C 探针覆盖、本载体缺的边界，依据 `spec/SimRISC-07 §2.4`）----
	@@ 单 NaN 的第 4 条对「带符号位的 qNaN」同样成立：max(−qNaN, 1.0) = 1.0，qNaN 不置标志
	TEST_FP3	17, ft, ftmax, rf5, rf6, 0x00000000FFC00000, rf7, 0x000000003F800000, 0, 0x000000003F800000, 0x00
	@@ 第 1 条按数值序含次正规：max(minsub, maxsub) = maxsub
	TEST_FP3	18, ft, ftmax, rf5, rf6, 0x0000000000000001, rf7, 0x00000000007FFFFF, 0, 0x00000000007FFFFF, 0x00
	@@ max(minsub, +0) = minsub
	TEST_FP3	19, ft, ftmax, rf5, rf6, 0x0000000000000001, rf7, 0x0000000000000000, 0, 0x0000000000000001, 0x00
	@@ max(+Inf, −Inf) = +Inf（第 6 条）
	TEST_FP3	20, ft, ftmax, rf5, rf6, 0x000000007F800000, rf7, 0x00000000FF800000, 0, 0x000000007F800000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	21, ILLI, 0x449C0083

	__TEST_END

	__TEST_SECTIONS
