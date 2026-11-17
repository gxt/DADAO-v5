@@ ftroot_orri_rf — ftroot rfHB, rfHC, immu6（orri, opc 0x44 / ha 0x06，rootn(x, 2)）
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
	@@ 规范编码字：dst=rf5 / src=rf6 / n=2（sqrt(4) = 2）
	TEST_FPENC_ROOT	1, ft, 0x44185182, rf5, rf6, 0x0000000040800000, 0x0000000040000000, 0x00
	@@ 字段边界：dst=rf63 / src=rf62（sqrt(9) = 3）
	TEST_FPENC_ROOT	2, ft, 0x441BFF82, rf63, rf62, 0x0000000041100000, 0x0000000040400000, 0x00

	@@ ---- semantic ----
	@@ sqrt(4.0) = 2.0（精确）
	TEST_FPROOT	3, ft, ftroot, rf5, rf6, 0x0000000040800000, 2, 0, 0x0000000040000000, 0x00
	@@ sqrt(0.25) = 0.5（精确）
	TEST_FPROOT	4, ft, ftroot, rf5, rf6, 0x000000003E800000, 2, 0, 0x000000003F000000, 0x00
	@@ sqrt(1.0) = 1.0（精确）
	TEST_FPROOT	5, ft, ftroot, rf5, rf6, 0x000000003F800000, 2, 0, 0x000000003F800000, 0x00
	@@ sqrt(2.0) ⇒ 最近的 ft 值 + NX
	TEST_FPROOT	6, ft, ftroot, rf5, rf6, 0x0000000040000000, 2, 0, 0x000000003FB504F3, 0x10

	@@ ---- boundary ----
	@@ sqrt(+0) = +0，不置标志
	TEST_FPROOT	7, ft, ftroot, rf5, rf6, 0x0000000000000000, 2, 0, 0x0000000000000000, 0x00
	@@ sqrt(-0) = +0（rootn 对 ±0 一律 +0，与 IEEE squareRoot(-0) 不同）
	TEST_FPROOT	8, ft, ftroot, rf5, rf6, 0x0000000080000000, 2, 0, 0x0000000000000000, 0x00
	@@ sqrt(-1.0) ⇒ qNaN + NV
	TEST_FPROOT	9, ft, ftroot, rf5, rf6, 0x00000000BF800000, 2, 0, 0x000000007FC00000, 0x01
	@@ sqrt(-Inf) ⇒ qNaN + NV
	TEST_FPROOT	10, ft, ftroot, rf5, rf6, 0x00000000FF800000, 2, 0, 0x000000007FC00000, 0x01
	@@ sqrt(qNaN) = canonical qNaN，不置标志
	TEST_FPROOT	11, ft, ftroot, rf5, rf6, 0x000000007FC00000, 2, 0, 0x000000007FC00000, 0x00
	@@ sqrt(sNaN) = canonical qNaN + NV
	TEST_FPROOT	12, ft, ftroot, rf5, rf6, 0x000000007F800001, 2, 0, 0x000000007FC00000, 0x01
	@@ sqrt(+Inf) = +Inf，不置标志
	TEST_FPROOT	13, ft, ftroot, rf5, rf6, 0x000000007F800000, 2, 0, 0x000000007F800000, 0x00
	@@ sqrt(2.0) 在 RUP 下 ⇒ 上邻值 + NX
	TEST_FPROOT	14, ft, ftroot, rf5, rf6, 0x0000000040000000, 2, 3, 0x000000003FB504F4, 0x10
	@@ sqrt(2.0) 在 RDN 下 ⇒ 下邻值 + NX
	TEST_FPROOT	15, ft, ftroot, rf5, rf6, 0x0000000040000000, 2, 2, 0x000000003FB504F3, 0x10
	@@ sqrt(最小次正规) ⇒ 次正规开方后为正规数 + NX
	TEST_FPROOT	16, ft, ftroot, rf5, rf6, 0x0000000000000001, 2, 0, 0x000000001A3504F3, 0x10
	@@ sqrt(ft_max) ⇒ 舍入值 + NX
	TEST_FPROOT	17, ft, ftroot, rf5, rf6, 0x000000007F7FFFFF, 2, 0, 0x000000005F7FFFFF, 0x10

	@@ ---- overlap ----
	@@ 目的 = 源（rf9 = sqrt(rf9)）
	TEST_FPROOT	18, ft, ftroot, rf9, rf9, 0x0000000041100000, 2, 0, 0x0000000040400000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	19, ILLI, 0x44180082
	@@ n = 3 ⇒ ILLI（encode_fp_root_n；仅支持 n=2）
	TEST_FAULT_FP	20, ILLI, 0x44181083

	__TEST_END

	__TEST_SECTIONS
