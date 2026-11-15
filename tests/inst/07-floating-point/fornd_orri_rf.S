@@ fornd_orri_rf — fornd（orri, opc 0x44 / ha 0x0B）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 取整（roundToIntegral，`spec/SimRISC-07 §2.3`）：fornd rfHB, rfHC, immu6
@@ 六档 one-hot：0x01 RNE / 0x02 RNA / 0x04 RTZ / 0x08 RUP / 0x10 RDN / 0x20 动态（读 rf0[33:32]）
@@ 只有 0x20 置 NX（且仅当结果 ≠ 输入）；±0 符号保留；Inf/NaN(|x|≥2^p) 原样或 canonical 化
@@ 写宽：`fo` 形式按整 64 位写入
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，证据脚本 `fp_ref.py`）按 spec 现算，不手写
@@ 目的预置 `0xDEADBEEFCAFEF00D`：ft 只写低 32 ⇒ 期望高 32 必须是 `0xDEADBEEF`（写宽回归）
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / src=rf6 / immu6=0x01（RNE），2.5 → 2.0
	TEST_FPRND_ENC	1, 0x442C5181, rf5, rf6, 0x4320000000000001, 0, 0x4320000000000000, 0x00
	@@ 字段边界：dst=rf63 / src=rf62 / immu6=0x20（动态）＋rf0=RTZ，-2.7 → -2.0 + NX
	TEST_FPRND_ENC	2, 0x442FFFA0, rf63, rf62, 0xC00599999999999A, 1, 0xC000000000000000, 0x10

	@@ ---- semantic ----
	@@ 2.5 RNE（平局取偶）→ 2.0，静态档不置 NX
	TEST_FPRND	3, fornd, rf5, rf6, 0x4320000000000001, 0x01, 0, 0x4320000000000000, 0x00
	@@ 2.5 RNA（平局远离 0）→ 3.0，静态档不置 NX
	TEST_FPRND	4, fornd, rf5, rf6, 0x4320000000000001, 0x02, 0, 0x4320000000000002, 0x00
	@@ -2.7 RTZ → -2.0
	TEST_FPRND	5, fornd, rf5, rf6, 0xC00599999999999A, 0x04, 0, 0xC000000000000000, 0x00
	@@ 2.1 RUP（向 +∞）→ 3.0
	TEST_FPRND	6, fornd, rf5, rf6, 0x4000CCCCCCCCCCCD, 0x08, 0, 0x4008000000000000, 0x00
	@@ -2.1 RDN（向 −∞）→ -3.0
	TEST_FPRND	7, fornd, rf5, rf6, 0xC000CCCCCCCCCCCD, 0x10, 0, 0xC008000000000000, 0x00
	@@ 2.5 动态档 0x20 读 rf0=RNE → 2.0 + NX（结果≠输入）
	TEST_FPRND	8, fornd, rf5, rf6, 0x4320000000000001, 0x20, 0, 0x4320000000000000, 0x10
	@@ 2.1 动态档 0x20 读 rf0=RUP → 3.0 + NX
	TEST_FPRND	9, fornd, rf5, rf6, 0x4000CCCCCCCCCCCD, 0x20, 3, 0x4008000000000000, 0x10
	@@ 3.0 动态档 0x20 结果精确 ⇒ 不置 NX
	TEST_FPRND	10, fornd, rf5, rf6, 0x4008000000000000, 0x20, 0, 0x4008000000000000, 0x00
	@@ 静态 RNE（0x01）不受 rf0=RUP 影响 → 2.5 仍 2.0、不置 NX
	TEST_FPRND	11, fornd, rf5, rf6, 0x4320000000000001, 0x01, 3, 0x4320000000000000, 0x00

	@@ ---- boundary ----
	@@ -0.5 RTZ → -0（取整结果为 0 时沿用输入符号）
	TEST_FPRND	12, fornd, rf7, rf8, 0xBFE0000000000000, 0x04, 0, 0x8000000000000000, 0x00
	@@ +0.5 RNE → +0（平局取偶）
	TEST_FPRND	13, fornd, rf7, rf8, 0x3FE0000000000000, 0x01, 0, 0x0000000000000000, 0x00
	@@ -0.0 RNE → -0（零的符号保留）
	TEST_FPRND	14, fornd, rf7, rf8, 0x8000000000000000, 0x01, 0, 0x8000000000000000, 0x00
	@@ 最小次正规 → +0（|x|<1）
	TEST_FPRND	15, fornd, rf7, rf8, 0x0000000000000001, 0x01, 0, 0x0000000000000000, 0x00
	@@ 最大次正规 → +0（绝对值 < 1）
	TEST_FPRND	16, fornd, rf7, rf8, 0x000FFFFFFFFFFFFF, 0x01, 0, 0x0000000000000000, 0x00
	@@ 2^p（已是整数，且 |x| ≥ 2^p ⇒ 原样返回）
	TEST_FPRND	17, fornd, rf7, rf8, 0x4340000000000000, 0x08, 0, 0x4340000000000000, 0x00
	@@ 最大有限值 → 原样返回
	TEST_FPRND	18, fornd, rf7, rf8, 0x7FEFFFFFFFFFFFFF, 0x01, 0, 0x7FEFFFFFFFFFFFFF, 0x00
	@@ +Inf → +Inf（原样、不置标志）
	TEST_FPRND	19, fornd, rf7, rf8, 0x7FF0000000000000, 0x01, 0, 0x7FF0000000000000, 0x00
	@@ -Inf（RDN 档）→ -Inf
	TEST_FPRND	20, fornd, rf7, rf8, 0xFFF0000000000000, 0x10, 0, 0xFFF0000000000000, 0x00
	@@ qNaN → canonical qNaN（符号 0、payload 归零）、不置 NV
	TEST_FPRND	21, fornd, rf7, rf8, 0x7FF8000000000123, 0x01, 0, 0x7FF8000000000000, 0x00
	@@ sNaN（RUP 档）→ canonical qNaN + NV
	TEST_FPRND	22, fornd, rf7, rf8, 0x7FF0000000000001, 0x08, 0, 0x7FF8000000000000, 0x01

	@@ ---- overlap ----
	@@ 目的 = 源（先读后写）：-3.5 RNE → -4.0
	TEST_FPRND	23, fornd, rf9, rf9, 0xC00C000000000000, 0x01, 0, 0xC010000000000000, 0x00
	@@ 源 = rf0（FCSR 低 32 位是 ft canonical qNaN）→ qNaN、不置 NV
	TEST_FPRND	24, fornd, rf9, rf0, 0x7FF8000000000000, 0x01, 0, 0x7FF8000000000000, 0x00

	@@ ---- 收窄补点（m13-testcases-044；原 C 探针覆盖、本载体缺的负平局/动态方向）----
	@@ −2.5 RNA（平局远离 0）⇒ −3.0；静态档不置 NX（`spec/SimRISC-07 §2.3`）
	TEST_FPRND	25, fornd, rf5, rf6, 0xC004000000000000, 0x02, 0, 0xC008000000000000, 0x00
	@@ −2.5 RNE（平局取偶）⇒ −2.0；静态档不置 NX
	TEST_FPRND	26, fornd, rf5, rf6, 0xC004000000000000, 0x01, 0, 0xC000000000000000, 0x00
	@@ +2.5 动态 0x20 读 rf0=RDN（10）⇒ +2.0 + NX（结果 ≠ 输入）
	TEST_FPRND	27, fornd, rf5, rf6, 0x4004000000000000, 0x20, 2, 0x4000000000000000, 0x10
	@@ −2.5 动态 0x20 读 rf0=RUP（11）⇒ −2.0 + NX
	TEST_FPRND	28, fornd, rf5, rf6, 0xC004000000000000, 0x20, 3, 0xC000000000000000, 0x10

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	29, ILLI, 0x442C0181
	@@ immu6=0x00 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	30, ILLI, 0x442C5180
	@@ immu6=0x03 非 one-hot ⇒ ILLI
	TEST_FAULT_FP	31, ILLI, 0x442C5183
	@@ immu6=0x30 多位同置 ⇒ ILLI
	TEST_FAULT_FP	32, ILLI, 0x442C51B0

	__TEST_END

	__TEST_SECTIONS
