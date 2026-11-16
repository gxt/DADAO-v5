@@ ftsub_orrr_rf — ftsub rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x11，单精减法）
@@ 大类：07-floating-point（浮点运算，`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 每个用例：清 rf0[4:0] → 设 rf0[33:32] → 执行 → 断言 rf0[4:0]（NV=1/DZ=2/OF=4/UF=8/NX=16）
@@   → 比对结果（二者共用点号）；ft 只比低 32 位（高 32 位不作规定）
@@ 初值经 `set.fo` 装配（整 64 位：`rd2rf rf, rd0` + 非零 wyde 的 `set.w`；不经浮点指令）；期望值由独立 IEEE 754 参考模型复算
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（1.5 - 2.25 = -0.75）
	TEST_FPENC	1, ft, 0x44445187, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000040100000, 0x00000000BF400000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（1.0 - 1.0 = +0）
	TEST_FPENC	2, ft, 0x4447FFBD, rf63, rf62, 0x000000003F800000, rf61, 0x000000003F800000, 0x0000000000000000, 0x00

	@@ ---- semantic ----
	@@ 2.0 - 1.0 = 1.0
	TEST_FP3	3, ft, ftsub, rf5, rf6, 0x0000000040000000, rf7, 0x000000003F800000, 0, 0x000000003F800000, 0x00
	@@ -1.5 - 2.25 = -3.75
	TEST_FP3	4, ft, ftsub, rf5, rf6, 0x00000000BFC00000, rf7, 0x0000000040100000, 0, 0x00000000C0700000, 0x00
	@@ 0.1 - 0.2 ⇒ ft 舍入值 + NX
	TEST_FP3	5, ft, ftsub, rf5, rf6, 0x000000003DCCCCCD, rf7, 0x000000003E4CCCCD, 0, 0x00000000BDCCCCCD, 0x00
	@@ 1.5 - 0 = 1.5
	TEST_FP3	6, ft, ftsub, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000000000000, 0, 0x000000003FC00000, 0x00

	@@ ---- boundary ----
	@@ 1.5 - 1.5 ⇒ +0（RNE）
	TEST_FP3	7, ft, ftsub, rf5, rf6, 0x000000003FC00000, rf7, 0x000000003FC00000, 0, 0x0000000000000000, 0x00
	@@ 1.5 - 1.5 ⇒ -0（RDN）
	TEST_FP3	8, ft, ftsub, rf5, rf6, 0x000000003FC00000, rf7, 0x000000003FC00000, 2, 0x0000000080000000, 0x00
	@@ qNaN - 1.0 ⇒ qNaN，不置标志
	TEST_FP3	9, ft, ftsub, rf5, rf6, 0x000000007FC00000, rf7, 0x000000003F800000, 0, 0x000000007FC00000, 0x00
	@@ sNaN - 1.0 ⇒ qNaN + NV
	TEST_FP3	10, ft, ftsub, rf5, rf6, 0x000000007F800001, rf7, 0x000000003F800000, 0, 0x000000007FC00000, 0x01
	@@ +Inf - +Inf ⇒ qNaN + NV
	TEST_FP3	11, ft, ftsub, rf5, rf6, 0x000000007F800000, rf7, 0x000000007F800000, 0, 0x000000007FC00000, 0x01
	@@ +Inf - 1.0 ⇒ +Inf
	TEST_FP3	12, ft, ftsub, rf5, rf6, 0x000000007F800000, rf7, 0x000000003F800000, 0, 0x000000007F800000, 0x00
	@@ ft_max - (-ft_max) ⇒ +Inf + OF|NX（RNE）
	TEST_FP3	13, ft, ftsub, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x00000000FF7FFFFF, 0, 0x000000007F800000, 0x14
	@@ 同一减在 RTZ 下 ⇒ ft_max + OF|NX
	TEST_FP3	14, ft, ftsub, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x00000000FF7FFFFF, 1, 0x000000007F7FFFFF, 0x14
	@@ 1.0 - 2^-25 恰在中点 ⇒ 1.0 + NX（RNE）
	TEST_FP3	15, ft, ftsub, rf5, rf6, 0x000000003F800000, rf7, 0x0000000033000000, 0, 0x000000003F800000, 0x10
	@@ 同一差在 RDN 下 ⇒ 1-2^-24 + NX
	TEST_FP3	16, ft, ftsub, rf5, rf6, 0x000000003F800000, rf7, 0x0000000033000000, 2, 0x000000003F7FFFFF, 0x10

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 - 2.25）
	TEST_FP3	17, ft, ftsub, rf9, rf9, 0x000000003FC00000, rf7, 0x0000000040100000, 0, 0x00000000BF400000, 0x00
	@@ 目的 = 源D（rf9 = rf6 - rf9）
	TEST_FP3	18, ft, ftsub, rf9, rf6, 0x0000000040000000, rf9, 0x000000003FC00000, 0, 0x000000003F000000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	19, ILLI, 0x44440083

	__TEST_END

	__TEST_SECTIONS
