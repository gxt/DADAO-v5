@@ fomin_orrr_rf — fomin rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x2E，minimumNumber）
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
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（min(1.5, 2.5) = 1.5）
	TEST_FPENC	1, fo, 0x44B85187, rf5, rf6, 0x3FF8000000000000, rf7, 0x4004000000000000, 0x3FF8000000000000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（min(max, -max) = -max）
	TEST_FPENC	2, fo, 0x44BBFFBD, rf63, rf62, 0x7FEFFFFFFFFFFFFF, rf61, 0xFFEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF, 0x00

	@@ ---- semantic ----
	@@ min(1.5, 2.5) = 1.5
	TEST_FP3	3, fo, fomin, rf5, rf6, 0x3FF8000000000000, rf7, 0x4004000000000000, 0, 0x3FF8000000000000, 0x00
	@@ min(-1.5, -2.5) = -2.5
	TEST_FP3	4, fo, fomin, rf5, rf6, 0xBFF8000000000000, rf7, 0xC004000000000000, 0, 0xC004000000000000, 0x00
	@@ min(1.5, 1.5) = 1.5
	TEST_FP3	5, fo, fomin, rf5, rf6, 0x3FF8000000000000, rf7, 0x3FF8000000000000, 0, 0x3FF8000000000000, 0x00
	@@ min(-Inf, 1.0) = -Inf
	TEST_FP3	6, fo, fomin, rf5, rf6, 0xFFF0000000000000, rf7, 0x3FF0000000000000, 0, 0xFFF0000000000000, 0x00

	@@ ---- boundary ----
	@@ min(+0, -0) = -0
	TEST_FP3	7, fo, fomin, rf5, rf6, 0x0000000000000000, rf7, 0x8000000000000000, 0, 0x8000000000000000, 0x00
	@@ min(-0, +0) = -0（顺序无关）
	TEST_FP3	8, fo, fomin, rf5, rf6, 0x8000000000000000, rf7, 0x0000000000000000, 0, 0x8000000000000000, 0x00
	@@ min(qNaN, 1.0) = 1.0，不置标志
	TEST_FP3	9, fo, fomin, rf5, rf6, 0x7FF8000000000000, rf7, 0x3FF0000000000000, 0, 0x3FF0000000000000, 0x00
	@@ min(1.0, qNaN) = 1.0，不置标志
	TEST_FP3	10, fo, fomin, rf5, rf6, 0x3FF0000000000000, rf7, 0x7FF8000000000000, 0, 0x3FF0000000000000, 0x00
	@@ min(sNaN, 1.0) = 1.0 + NV
	TEST_FP3	11, fo, fomin, rf5, rf6, 0x7FF0000000000001, rf7, 0x3FF0000000000000, 0, 0x3FF0000000000000, 0x01
	@@ min(qNaN, qNaN) = canonical qNaN，不置标志
	TEST_FP3	12, fo, fomin, rf5, rf6, 0x7FF8000000000000, rf7, 0x7FF8000000000001, 0, 0x7FF8000000000000, 0x00
	@@ min(qNaN, sNaN) = canonical qNaN + NV
	TEST_FP3	13, fo, fomin, rf5, rf6, 0x7FF8000000000000, rf7, 0x7FF0000000000001, 0, 0x7FF8000000000000, 0x01
	@@ min(+Inf, fo_max) = fo_max
	TEST_FP3	14, fo, fomin, rf5, rf6, 0x7FF0000000000000, rf7, 0x7FEFFFFFFFFFFFFF, 0, 0x7FEFFFFFFFFFFFFF, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = min(rf9, 2.5)）
	TEST_FP3	15, fo, fomin, rf9, rf9, 0x3FF8000000000000, rf7, 0x4004000000000000, 0, 0x3FF8000000000000, 0x00
	@@ 目的 = 源D（rf9 = min(2.5, rf9)）
	TEST_FP3	16, fo, fomin, rf9, rf6, 0x4004000000000000, rf9, 0x3FF8000000000000, 0, 0x3FF8000000000000, 0x00

	@@ ---- 收窄补点（m13-testcases-044；原 C 探针覆盖、本载体缺的边界，依据 `spec/SimRISC-07 §2.4`）----
	@@ 单 NaN 的第 4 条对「带符号位的 qNaN」同样成立：min(−qNaN, 1.0) = 1.0，qNaN 不置标志
	TEST_FP3	17, fo, fomin, rf5, rf6, 0xFFF8000000000000, rf7, 0x3FF0000000000000, 0, 0x3FF0000000000000, 0x00
	@@ 第 1 条按数值序含次正规：min(minsub, maxsub) = minsub
	TEST_FP3	18, fo, fomin, rf5, rf6, 0x0000000000000001, rf7, 0x000FFFFFFFFFFFFF, 0, 0x0000000000000001, 0x00
	@@ min(minsub, +0) = +0（次正规 > 0，不是「任选」）
	TEST_FP3	19, fo, fomin, rf5, rf6, 0x0000000000000001, rf7, 0x0000000000000000, 0, 0x0000000000000000, 0x00
	@@ min(+Inf, −Inf) = −Inf（第 6 条：Inf 按数值序参与比较）
	TEST_FP3	20, fo, fomin, rf5, rf6, 0x7FF0000000000000, rf7, 0xFFF0000000000000, 0, 0xFFF0000000000000, 0x00
	@@ 单 NaN 的第二源分支（sNaN 在后）：min(1.0, sNaN) = 1.0 + NV（结果为数也置 NV）
	TEST_FP3	21, fo, fomin, rf5, rf6, 0x3FF0000000000000, rf7, 0x7FF0000000000001, 0, 0x3FF0000000000000, 0x01

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	22, ILLI, 0x44B80083

	__TEST_END

	__TEST_SECTIONS
