@@ ftscmp_orrr_rf — ftscmp（orrr, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 比较（§4）：结果写满 64 位的 -1/0/1；无序时 quiet compare 取 canonical qNaN、signaling compare 取 sNaN（符号位 0、payload 不限 ⇒ 用结构断言）。
@@ NV：signaling 只要无序即置；quiet 仅在含 sNaN 时置；有序不置。
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rd5 / rf6=0x000000003F800000 / rf7=0x0000000040000000，1.0 < 2.0 ⇒ -1
	TEST_FPCMP_ENC	1, 0x0000000044845187, rd5, rf6, 0x000000003F800000, rf7, 0x0000000040000000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ 字段边界：dst=rd63 / src=rf62 / rf61
	TEST_FPCMP_ENC	2, 0x000000004487FFBD, rd63, rf62, 0x000000003F800000, rf61, 0x0000000040000000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ 1.0 < 2.0 ⇒ -1（有序不置标志）
	TEST_FPCMP	3, ftscmp, rd5, rf6, 0x000000003F800000, rf7, 0x0000000040000000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ 2.0 > 1.0 ⇒ +1
	TEST_FPCMP	4, ftscmp, rd5, rf6, 0x0000000040000000, rf7, 0x000000003F800000, 0x0000000000000001, 0x00
	@@ 1.0 == 1.0 ⇒ 0
	TEST_FPCMP	5, ftscmp, rd5, rf6, 0x000000003F800000, rf7, 0x000000003F800000, 0x0000000000000000, 0x00
	@@ +0 == -0 ⇒ 0（比较不区分零的符号）
	TEST_FPCMP	6, ftscmp, rd5, rf6, 0x0000000000000000, rf7, 0x0000000080000000, 0x0000000000000000, 0x00
	@@ -Inf < +Inf ⇒ -1
	TEST_FPCMP	7, ftscmp, rd5, rf6, 0x00000000FF800000, rf7, 0x000000007F800000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ +Inf == +Inf ⇒ 0
	TEST_FPCMP	8, ftscmp, rd5, rf6, 0x000000007F800000, rf7, 0x000000007F800000, 0x0000000000000000, 0x00
	@@ 最小正次正规 > +0 ⇒ +1（次正规按数值参与比较）
	TEST_FPCMP	9, ftscmp, rd5, rf6, 0x0000000000000001, rf7, 0x0000000000000000, 0x0000000000000001, 0x00
	@@ signaling：qNaN（左）⇒ sNaN 结果 + NV（任一 NaN 即无序）
	TEST_FPCMP_S	10, ft, ftscmp, rd5, rf6, 0x000000007FC00000, rf7, 0x000000003F800000, 0x01
	@@ signaling：qNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	11, ft, ftscmp, rd5, rf6, 0x000000003F800000, rf7, 0x000000007FC00000, 0x01
	@@ signaling：sNaN（左）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	12, ft, ftscmp, rd5, rf6, 0x000000007F800001, rf7, 0x000000003F800000, 0x01
	@@ signaling：sNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	13, ft, ftscmp, rd5, rf6, 0x000000003F800000, rf7, 0x000000007F800001, 0x01
	@@ signaling：双 NaN ⇒ sNaN 结果 + NV
	TEST_FPCMP_S	14, ft, ftscmp, rd5, rf6, 0x000000007FC00000, rf7, 0x000000007FC00000, 0x01
	@@ signaling：负 qNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	15, ft, ftscmp, rd5, rf6, 0x000000003F800000, rf7, 0x00000000FFC00000, 0x01
	@@ signaling：负 sNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	16, ft, ftscmp, rd5, rf6, 0x000000003F800000, rf7, 0x00000000FF800001, 0x01
	@@ 两源同名（rf6 与 rf6）⇒ 相等 0；目的 rd6 与源 rf6 同号
	TEST_FPCMP	17, ftscmp, rd6, rf6, 0x000000003F800000, rf6, 0x000000003F800000, 0x0000000000000000, 0x00
	@@ legality：目的 rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_FP	18, ILLI, 0x44840187

	__TEST_END

	__TEST_SECTIONS
