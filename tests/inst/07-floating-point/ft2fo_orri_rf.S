@@ ft2fo_orri_rf — ft2fo（orri, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 格式间转换（§1.4/§2）：fo2ft 六档 + 溢出按方向取 ±Inf/±ft_max、下溢按 tiny∧inexact 置 UF|NX、轻微溢出只置 NX；
@@ ft2fo 恒精确（SBZ、不置标志）；两者 NaN 结果一律 canonical qNaN、sNaN 入参置 NV。
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rf5 / src=rf6 / immu6=0（SBZ），1.5f → 1.5
	TEST_FPCVT_ENC_F2F	1, fo, 0x44045180, rf5, rf6, 0x000000003FC00000, 0x3FF8000000000000, 0x00
	@@ 字段边界：dst=rf63 / src=rf62
	TEST_FPCVT_ENC_F2F	2, fo, 0x4407FF80, rf63, rf62, 0x00000000C0000000, 0xC000000000000000, 0x00
	@@ 1.0f → 1.0（精确，不置标志）
	TEST_FPCVT_F2F	3, fo, ft2fo, rf5, rf6, 0x000000003F800000, 0x0, 0, 0x3FF0000000000000, 0x00
	@@ -1.0f → -1.0
	TEST_FPCVT_F2F	4, fo, ft2fo, rf5, rf6, 0x00000000BF800000, 0x0, 0, 0xBFF0000000000000, 0x00
	@@ 2^-149（f32 最小次正规）→ f64 精确表示
	TEST_FPCVT_F2F	5, fo, ft2fo, rf5, rf6, 0x0000000000000001, 0x0, 0, 0x36A0000000000000, 0x00
	@@ ft_max → f64 精确（0x47EFFFFFE0000000）
	TEST_FPCVT_F2F	6, fo, ft2fo, rf5, rf6, 0x000000007F7FFFFF, 0x0, 0, 0x47EFFFFFE0000000, 0x00
	@@ -0f → -0（零的符号保留）
	TEST_FPCVT_F2F	7, fo, ft2fo, rf5, rf6, 0x0000000080000000, 0x0, 0, 0x8000000000000000, 0x00
	@@ +Inf → +Inf
	TEST_FPCVT_F2F	8, fo, ft2fo, rf5, rf6, 0x000000007F800000, 0x0, 0, 0x7FF0000000000000, 0x00
	@@ -Inf → -Inf
	TEST_FPCVT_F2F	9, fo, ft2fo, rf5, rf6, 0x00000000FF800000, 0x0, 0, 0xFFF0000000000000, 0x00
	@@ qNaN（带 payload）→ canonical qNaN，不置 NV（§1.4）
	TEST_FPCVT_F2F	10, fo, ft2fo, rf5, rf6, 0x000000007FC12345, 0x0, 0, 0x7FF8000000000000, 0x00
	@@ sNaN → canonical qNaN + NV
	TEST_FPCVT_F2F	11, fo, ft2fo, rf5, rf6, 0x000000007F800001, 0x0, 0, 0x7FF8000000000000, 0x01
	@@ 负号 sNaN → canonical qNaN（符号 0）+ NV
	TEST_FPCVT_F2F	12, fo, ft2fo, rf5, rf6, 0x00000000FF800001, 0x0, 0, 0x7FF8000000000000, 0x01
	@@ ft 最大次正规 → f64 精确
	TEST_FPCVT_F2F	13, fo, ft2fo, rf5, rf6, 0x000000007F7FFFFE, 0x0, 0, 0x47EFFFFFC0000000, 0x00
	@@ 源=目的（rf5 ← rf5）
	TEST_FPCVT_F2F	14, fo, ft2fo, rf5, rf5, 0x0000000040200000, 0x0, 0, 0x4004000000000000, 0x00
	@@ 窗口顶端源=目的（rf63 ← rf63）
	TEST_FPCVT_F2F	15, fo, ft2fo, rf63, rf63, 0x00000000C0200000, 0x0, 0, 0xC004000000000000, 0x00
	@@ legality：目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	16, ILLI, 0x44040180
	@@ legality：SBZ 非 0（immu6=0x01）⇒ ILLI（encode_sbz）
	TEST_FAULT_FP	17, ILLI, 0x44045181
	@@ legality：SBZ 非 0（immu6=0x08）⇒ ILLI（encode_sbz）
	TEST_FAULT_FP	18, ILLI, 0x44045188

	__TEST_END

	__TEST_SECTIONS
