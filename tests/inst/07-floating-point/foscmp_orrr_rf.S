@@ foscmp_orrr_rf — foscmp（orrr, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 比较（§4）：结果写满 64 位的 -1/0/1；无序时 quiet compare 取 canonical qNaN、signaling compare 取 sNaN（符号位 0、payload 不限 ⇒ 用结构断言）。
@@ NV：signaling 只要无序即置；quiet 仅在含 sNaN 时置；有序不置。
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rd5 / rf6=0x3FF0000000000000 / rf7=0x4000000000000000，1.0 < 2.0 ⇒ -1
	TEST_FPCMP_ENC	1, 0x0000000044A45187, rd5, rf6, 0x3FF0000000000000, rf7, 0x4000000000000000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ 字段边界：dst=rd63 / src=rf62 / rf61
	TEST_FPCMP_ENC	2, 0x0000000044A7FFBD, rd63, rf62, 0x3FF0000000000000, rf61, 0x4000000000000000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ 1.0 < 2.0 ⇒ -1（有序不置标志）
	TEST_FPCMP	3, foscmp, rd5, rf6, 0x3FF0000000000000, rf7, 0x4000000000000000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ 2.0 > 1.0 ⇒ +1
	TEST_FPCMP	4, foscmp, rd5, rf6, 0x4000000000000000, rf7, 0x3FF0000000000000, 0x0000000000000001, 0x00
	@@ 1.0 == 1.0 ⇒ 0
	TEST_FPCMP	5, foscmp, rd5, rf6, 0x3FF0000000000000, rf7, 0x3FF0000000000000, 0x0000000000000000, 0x00
	@@ +0 == -0 ⇒ 0（比较不区分零的符号）
	TEST_FPCMP	6, foscmp, rd5, rf6, 0x0000000000000000, rf7, 0x8000000000000000, 0x0000000000000000, 0x00
	@@ -Inf < +Inf ⇒ -1
	TEST_FPCMP	7, foscmp, rd5, rf6, 0xFFF0000000000000, rf7, 0x7FF0000000000000, 0xFFFFFFFFFFFFFFFF, 0x00
	@@ +Inf == +Inf ⇒ 0
	TEST_FPCMP	8, foscmp, rd5, rf6, 0x7FF0000000000000, rf7, 0x7FF0000000000000, 0x0000000000000000, 0x00
	@@ 最小正次正规 > +0 ⇒ +1（次正规按数值参与比较）
	TEST_FPCMP	9, foscmp, rd5, rf6, 0x0000000000000001, rf7, 0x0000000000000000, 0x0000000000000001, 0x00
	@@ signaling：qNaN（左）⇒ sNaN 结果 + NV（任一 NaN 即无序）
	TEST_FPCMP_S	10, fo, foscmp, rd5, rf6, 0x7FF8000000000000, rf7, 0x3FF0000000000000, 0x01
	@@ signaling：qNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	11, fo, foscmp, rd5, rf6, 0x3FF0000000000000, rf7, 0x7FF8000000000000, 0x01
	@@ signaling：sNaN（左）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	12, fo, foscmp, rd5, rf6, 0x7FF0000000000001, rf7, 0x3FF0000000000000, 0x01
	@@ signaling：sNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	13, fo, foscmp, rd5, rf6, 0x3FF0000000000000, rf7, 0x7FF0000000000001, 0x01
	@@ signaling：双 NaN ⇒ sNaN 结果 + NV
	TEST_FPCMP_S	14, fo, foscmp, rd5, rf6, 0x7FF8000000000000, rf7, 0x7FF8000000000000, 0x01
	@@ signaling：负 qNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	15, fo, foscmp, rd5, rf6, 0x3FF0000000000000, rf7, 0xFFF8000000000000, 0x01
	@@ signaling：负 sNaN（右）⇒ sNaN 结果 + NV
	TEST_FPCMP_S	16, fo, foscmp, rd5, rf6, 0x3FF0000000000000, rf7, 0xFFF0000000000001, 0x01
	@@ 两源同名（rf6 与 rf6）⇒ 相等 0；目的 rd6 与源 rf6 同号
	TEST_FPCMP	17, foscmp, rd6, rf6, 0x3FF0000000000000, rf6, 0x3FF0000000000000, 0x0000000000000000, 0x00
	@@ legality：目的 rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_FP	18, ILLI, 0x44A40187

	__TEST_END

	__TEST_SECTIONS
