@@ fo2ft_orri_rf — fo2ft（orri, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 格式间转换（§1.4/§2）：fo2ft 六档 + 溢出按方向取 ±Inf/±ft_max、下溢按 tiny∧inexact 置 UF|NX、轻微溢出只置 NX；
@@ ft2fo 恒精确（SBZ、不置标志）；两者 NaN 结果一律 canonical qNaN、sNaN 入参置 NV。
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rf5 / src=rf6 / immu6=0x01（RNE），1.5 → 1.5f
	TEST_FPCVT_ENC_F2F	1, ft, 0x44245181, rf5, rf6, 0x3FF8000000000000, 0x000000003FC00000, 0x00
	@@ 字段边界：dst=rf63 / src=rf62 / immu6=0x04（RTZ）
	TEST_FPCVT_ENC_F2F	2, ft, 0x4427FF84, rf63, rf62, 0xBFF8000000000000, 0x00000000BFC00000, 0x00
	@@ 1.0 → 0x3F800000（精确）
	TEST_FPCVT_F2F	3, ft, fo2ft, rf5, rf6, 0x3FF0000000000000, 0x01, 0, 0x000000003F800000, 0x00
	@@ -0 → -0（零的符号保留）
	TEST_FPCVT_F2F	4, ft, fo2ft, rf5, rf6, 0x8000000000000000, 0x01, 0, 0x0000000080000000, 0x00
	@@ 1/3 RNE → 0x3EAAAAAB + NX
	TEST_FPCVT_F2F	5, ft, fo2ft, rf5, rf6, 0x3FD5555555555555, 0x01, 0, 0x000000003EAAAAAB, 0x10
	@@ 1/3 RTZ → 0x3EAAAAAA + NX
	TEST_FPCVT_F2F	6, ft, fo2ft, rf5, rf6, 0x3FD5555555555555, 0x04, 0, 0x000000003EAAAAAA, 0x10
	@@ 1/3 RUP → 0x3EAAAAAB + NX
	TEST_FPCVT_F2F	7, ft, fo2ft, rf5, rf6, 0x3FD5555555555555, 0x08, 0, 0x000000003EAAAAAB, 0x10
	@@ -1/3 RDN → 0xBEAAAAAB + NX
	TEST_FPCVT_F2F	8, ft, fo2ft, rf5, rf6, 0xBFD5555555555555, 0x10, 0, 0x00000000BEAAAAAB, 0x10
	@@ 动态档 0x20 读 rf0=RDN → 0x3EAAAAAA + NX
	TEST_FPCVT_F2F	9, ft, fo2ft, rf5, rf6, 0x3FD5555555555555, 0x20, 2, 0x000000003EAAAAAA, 0x10
	@@ 正溢出 RNE → +Inf + OF|NX
	TEST_FPCVT_F2F	10, ft, fo2ft, rf5, rf6, 0x7E37E43C8800759C, 0x01, 0, 0x000000007F800000, 0x14
	@@ 正溢出 RTZ → +ft_max + OF|NX
	TEST_FPCVT_F2F	11, ft, fo2ft, rf5, rf6, 0x7E37E43C8800759C, 0x04, 0, 0x000000007F7FFFFF, 0x14
	@@ 正溢出 RDN → +ft_max + OF|NX
	TEST_FPCVT_F2F	12, ft, fo2ft, rf5, rf6, 0x7E37E43C8800759C, 0x10, 0, 0x000000007F7FFFFF, 0x14
	@@ 负溢出 RNE → -Inf + OF|NX
	TEST_FPCVT_F2F	13, ft, fo2ft, rf5, rf6, 0xFE37E43C8800759C, 0x01, 0, 0x00000000FF800000, 0x14
	@@ 负溢出 RUP → -ft_max + OF|NX
	TEST_FPCVT_F2F	14, ft, fo2ft, rf5, rf6, 0xFE37E43C8800759C, 0x08, 0, 0x00000000FF7FFFFF, 0x14
	@@ 负溢出 RDN → -Inf + OF|NX
	TEST_FPCVT_F2F	15, ft, fo2ft, rf5, rf6, 0xFE37E43C8800759C, 0x10, 0, 0x00000000FF800000, 0x14
	@@ 轻微溢出（ft_max < 精确值 < 2^128）RTZ → ft_max，只置 NX、不置 OF
	TEST_FPCVT_F2F	16, ft, fo2ft, rf5, rf6, 0x47EFFFFFEC000000, 0x04, 0, 0x000000007F7FFFFF, 0x10
	@@ 同一轻微溢出在 RUP 下舍到 2^128 ⇒ +Inf + OF|NX
	TEST_FPCVT_F2F	17, ft, fo2ft, rf5, rf6, 0x47EFFFFFEC000000, 0x08, 0, 0x000000007F800000, 0x14
	@@ 2^-150 tiny+inexact RNE → +0 + UF|NX
	TEST_FPCVT_F2F	18, ft, fo2ft, rf5, rf6, 0x3690000000000000, 0x01, 0, 0x0000000000000000, 0x18
	@@ -2^-150 RTZ → -0 + UF|NX（零的符号随精确值）
	TEST_FPCVT_F2F	19, ft, fo2ft, rf5, rf6, 0xB690000000000000, 0x04, 0, 0x0000000080000000, 0x18
	@@ 1.5×2^-149（= 3×2^-150）RNE → 2^-149：**非零次正规结果** + UF|NX
	TEST_FPCVT_F2F	20, ft, fo2ft, rf5, rf6, 0x36A8000000000000, 0x01, 0, 0x0000000000000002, 0x18
	@@ 2^-149 恰为最小次正规（tiny 且**精确**）⇒ 不置 UF/NX
	TEST_FPCVT_F2F	21, ft, fo2ft, rf5, rf6, 0x36A0000000000000, 0x01, 0, 0x0000000000000001, 0x00
	@@ 1.5×2^-126（最小正规之上，精确）⇒ 不置标志
	TEST_FPCVT_F2F	22, ft, fo2ft, rf5, rf6, 0x3818000000000000, 0x01, 0, 0x0000000000C00000, 0x00
	@@ 2^-126 最小正规（精确）⇒ 不置标志
	TEST_FPCVT_F2F	23, ft, fo2ft, rf5, rf6, 0x3810000000000000, 0x01, 0, 0x0000000000800000, 0x00
	@@ f64 最大有限 RTZ → +ft_max + OF|NX（YAML `fo2ft` 例）
	TEST_FPCVT_F2F	24, ft, fo2ft, rf5, rf6, 0x7FEFFFFFFFFFFFFF, 0x04, 0, 0x000000007F7FFFFF, 0x14
	@@ qNaN → canonical qNaN（0x7FC00000），不置 NV
	TEST_FPCVT_F2F	25, ft, fo2ft, rf5, rf6, 0x7FF8000000000000, 0x01, 0, 0x000000007FC00000, 0x00
	@@ sNaN → canonical qNaN + NV
	TEST_FPCVT_F2F	26, ft, fo2ft, rf5, rf6, 0x7FF0000000000001, 0x01, 0, 0x000000007FC00000, 0x01
	@@ 负号 qNaN → canonical qNaN（符号位 0），不置 NV
	TEST_FPCVT_F2F	27, ft, fo2ft, rf5, rf6, 0xFFF8000000000000, 0x01, 0, 0x000000007FC00000, 0x00
	@@ +Inf → +Inf（不置标志）
	TEST_FPCVT_F2F	28, ft, fo2ft, rf5, rf6, 0x7FF0000000000000, 0x01, 0, 0x000000007F800000, 0x00
	@@ -Inf → -Inf（不置标志）
	TEST_FPCVT_F2F	29, ft, fo2ft, rf5, rf6, 0xFFF0000000000000, 0x01, 0, 0x00000000FF800000, 0x00
	@@ 源=目的（rf5 ← rf5）：先读后写，结果确定
	TEST_FPCVT_F2F	30, ft, fo2ft, rf5, rf5, 0x4004000000000000, 0x01, 0, 0x0000000040200000, 0x00
	@@ legality：目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	31, ILLI, 0x44240181
	@@ legality：immu6=0 非六档 ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	32, ILLI, 0x44245180
	@@ legality：immu6=0x03 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	33, ILLI, 0x44245183

	__TEST_END

	__TEST_SECTIONS
