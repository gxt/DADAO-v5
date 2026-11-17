@@ ftrem_orrr_rf — ftrem rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x14，单精 remainder）
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
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（5 rem 2 = 1）
	TEST_FPENC	1, ft, 0x44505187, rf5, rf6, 0x0000000040A00000, rf7, 0x0000000040000000, 0x000000003F800000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（7 rem 2 = -1，平局取偶）
	TEST_FPENC	2, ft, 0x4453FFBD, rf63, rf62, 0x0000000040E00000, rf61, 0x0000000040000000, 0x00000000BF800000, 0x00

	@@ ---- semantic ----
	@@ -5 rem 2 = -1（符号随被除数）
	TEST_FP3	3, ft, ftrem, rf5, rf6, 0x00000000C0A00000, rf7, 0x0000000040000000, 0, 0x00000000BF800000, 0x00
	@@ 5 rem -2 = 1（除数符号不传递）
	TEST_FP3	4, ft, ftrem, rf5, rf6, 0x0000000040A00000, rf7, 0x00000000C0000000, 0, 0x000000003F800000, 0x00
	@@ 5.5 rem 2 = -0.5（商 3 ⇒ 精确余数，不置 NX）
	TEST_FP3	5, ft, ftrem, rf5, rf6, 0x0000000040B00000, rf7, 0x0000000040000000, 0, 0x00000000BF000000, 0x00
	@@ 1.5 rem 1 = -0.5（1.5/1 平局取偶 ⇒ n=2）
	TEST_FP3	6, ft, ftrem, rf5, rf6, 0x000000003FC00000, rf7, 0x000000003F800000, 0, 0x00000000BF000000, 0x00

	@@ ---- boundary ----
	@@ 5 rem Inf = 5（商 0，原样返回）
	TEST_FP3	7, ft, ftrem, rf5, rf6, 0x0000000040A00000, rf7, 0x000000007F800000, 0, 0x0000000040A00000, 0x00
	@@ Inf rem 2 ⇒ qNaN + NV（§7.2f 被除数为无穷）
	TEST_FP3	8, ft, ftrem, rf5, rf6, 0x000000007F800000, rf7, 0x0000000040000000, 0, 0x000000007FC00000, 0x01
	@@ 5 rem 0 ⇒ qNaN + NV（remainder 的除零是无效操作，不是 DZ）
	TEST_FP3	9, ft, ftrem, rf5, rf6, 0x0000000040A00000, rf7, 0x0000000000000000, 0, 0x000000007FC00000, 0x01
	@@ qNaN rem 0 ⇒ qNaN，不置 NV（NaN 优先于 §7.2f）
	TEST_FP3	10, ft, ftrem, rf5, rf6, 0x000000007FC00000, rf7, 0x0000000000000000, 0, 0x000000007FC00000, 0x00
	@@ qNaN rem 2.0 ⇒ canonical qNaN（spec §1.4；不传播 payload）
	TEST_FP3	11, ft, ftrem, rf5, rf6, 0x000000007FC00123, rf7, 0x0000000040000000, 0, 0x000000007FC00000, 0x00
	@@ sNaN rem 0 ⇒ qNaN + NV（sNaN 与另一操作数无关）
	TEST_FP3	12, ft, ftrem, rf5, rf6, 0x000000007F800001, rf7, 0x0000000000000000, 0, 0x000000007FC00000, 0x01
	@@ +0 rem 2 = +0（符号保留）
	TEST_FP3	13, ft, ftrem, rf5, rf6, 0x0000000000000000, rf7, 0x0000000040000000, 0, 0x0000000000000000, 0x00
	@@ -0 rem 2 = -0（符号保留）
	TEST_FP3	14, ft, ftrem, rf5, rf6, 0x0000000080000000, rf7, 0x0000000040000000, 0, 0x0000000080000000, 0x00
	@@ 5 rem 5 = +0（零余数取被除数符号）
	TEST_FP3	15, ft, ftrem, rf5, rf6, 0x0000000040A00000, rf7, 0x0000000040A00000, 0, 0x0000000000000000, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 rem 2）
	TEST_FP3	16, ft, ftrem, rf9, rf9, 0x0000000040A00000, rf7, 0x0000000040000000, 0, 0x000000003F800000, 0x00
	@@ 目的 = 源D（rf9 = 5 rem rf9）
	TEST_FP3	17, ft, ftrem, rf9, rf6, 0x0000000040A00000, rf9, 0x0000000040000000, 0, 0x000000003F800000, 0x00

	@@ ---- boundary：零余数取被除数符号（`SimRISC-07 §2.1` / IEEE 754-2019 §5.3.1）----
	@@ 4 rem 2 = +0（除尽 ⇒ 零余数，符号取 rfHC 的「+」；注意不能用「+0 == -0」的数值比较判）
	TEST_FP3	18, ft, ftrem, rf5, rf6, 0x0000000040800000, rf7, 0x0000000040000000, 0, 0x0000000000000000, 0x00
	@@ -4 rem 2 = -0（零余数保留被除数的负号 ⇒ 结果位型 0x80000000，与被除数为正时逐字节不同）
	TEST_FP3	19, ft, ftrem, rf5, rf6, 0x00000000C0800000, rf7, 0x0000000040000000, 0, 0x0000000080000000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	20, ILLI, 0x44500083

	__TEST_END

	__TEST_SECTIONS
