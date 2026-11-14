@@ ftrnd_orri_rf — ftrnd（orri, opc 0x44 / ha 0x03）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 取整（roundToIntegral，`spec/SimRISC-07 §2.3`）：ftrnd rfHB, rfHC, immu6
@@ 六档 one-hot：0x01 RNE / 0x02 RNA / 0x04 RTZ / 0x08 RUP / 0x10 RDN / 0x20 动态（读 rf0[33:32]）
@@ 只有 0x20 置 NX（且仅当结果 ≠ 输入）；±0 符号保留；Inf/NaN(|x|≥2^p) 原样或 canonical 化
@@ 写宽：`ft` 形式只写目的低 32 位、高 32 位保持原值（`spec/SimRISC-07 §1.3`）
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，证据脚本 `fp_ref.py`）按 spec 现算，不手写
@@ 目的预置 `0xDEADBEEFCAFEF00D`：ft 只写低 32 ⇒ 期望高 32 必须是 `0xDEADBEEF`（写宽回归）
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

@@ ---- 本文件局部宏（不改共享宏层）----
@@ 目的 rf、源 rf、第三域 = immu6 取整档；期望按整 64 位比较（ft 高 32 必须保持）
@@ （判据同 `__CHECK_RD`：先断言标志、再比 64 位结果；点号与结果缓冲一致）
.macro __FP_CHK64 pt, dst, exp, flags
	rf2rd	{rd21:rd21}, {rf0:rf0}
	ext.uo	rd21, rd21, 4
	__VERIFY_RD \pt, rd21, \flags
	rf2rd	{rd21:rd21}, {\dst:\dst}
	__LI	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __fpchk_\@]
	__EXIT	\pt
__fpchk_\@:
.endm

@@ 源初值经 `__LI_RF`（不经浮点指令）；目的预置 0xDEADBEEFCAFEF00D（ft 只写低 32）
.macro __FP_RD1 dst, src, sval
	.ifnc	\src, rf0
	__LI_RF	\src, \sval
	.endif
	.ifnc	\dst, \src
	__LI_RF	\dst, 0xDEADBEEFCAFEF00D
	.endif
.endm

@@ TEST_FPRND(pt, 助记符, 目的, 源, 源值, immu6, rf0[33:32], 期望, 期望标志)
.macro TEST_FPRND pt, mnem, dst, src, sval, cvt, rfm, exp, flags
	__FP_ENV \rfm
	__FP_RD1 \dst, \src, \sval
	\mnem	\dst, \src, \cvt
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm

@@ TEST_FPRND_ENC(pt, 编码字, 目的, 源, 源值, rf0[33:32], 期望, 期望标志)
.macro TEST_FPRND_ENC pt, enc, dst, src, sval, rfm, exp, flags
	__FP_ENV \rfm
	__FP_RD1 \dst, \src, \sval
	.dd.t32	\enc
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / src=rf6 / immu6=0x01（RNE），2.5 → 2.0
	TEST_FPRND_ENC	1, 0x440C5181, rf5, rf6, 0x0000000040200000, 0, 0xDEADBEEF40000000, 0x00
	@@ 字段边界：dst=rf63 / src=rf62 / immu6=0x20（动态）＋rf0=RTZ，-2.7 → -2.0 + NX
	TEST_FPRND_ENC	2, 0x440FFFA0, rf63, rf62, 0x00000000C02CCCCD, 1, 0xDEADBEEFC0000000, 0x10

	@@ ---- semantic ----
	@@ 2.5 RNE（平局取偶）→ 2.0，静态档不置 NX
	TEST_FPRND	3, ftrnd, rf5, rf6, 0x0000000040200000, 0x01, 0, 0xDEADBEEF40000000, 0x00
	@@ 2.5 RNA（平局远离 0）→ 3.0，静态档不置 NX
	TEST_FPRND	4, ftrnd, rf5, rf6, 0x0000000040200000, 0x02, 0, 0xDEADBEEF40400000, 0x00
	@@ -2.7 RTZ → -2.0
	TEST_FPRND	5, ftrnd, rf5, rf6, 0x00000000C02CCCCD, 0x04, 0, 0xDEADBEEFC0000000, 0x00
	@@ 2.1 RUP（向 +∞）→ 3.0
	TEST_FPRND	6, ftrnd, rf5, rf6, 0x0000000040066666, 0x08, 0, 0xDEADBEEF40400000, 0x00
	@@ -2.1 RDN（向 −∞）→ -3.0
	TEST_FPRND	7, ftrnd, rf5, rf6, 0x00000000C0066666, 0x10, 0, 0xDEADBEEFC0400000, 0x00
	@@ 2.5 动态档 0x20 读 rf0=RNE → 2.0 + NX（结果≠输入）
	TEST_FPRND	8, ftrnd, rf5, rf6, 0x0000000040200000, 0x20, 0, 0xDEADBEEF40000000, 0x10
	@@ 2.1 动态档 0x20 读 rf0=RUP → 3.0 + NX
	TEST_FPRND	9, ftrnd, rf5, rf6, 0x0000000040066666, 0x20, 3, 0xDEADBEEF40400000, 0x10
	@@ 3.0 动态档 0x20 结果精确 ⇒ 不置 NX
	TEST_FPRND	10, ftrnd, rf5, rf6, 0x0000000040400000, 0x20, 0, 0xDEADBEEF40400000, 0x00
	@@ 静态 RNE（0x01）不受 rf0=RUP 影响 → 2.5 仍 2.0、不置 NX
	TEST_FPRND	11, ftrnd, rf5, rf6, 0x0000000040200000, 0x01, 3, 0xDEADBEEF40000000, 0x00

	@@ ---- boundary ----
	@@ -0.5 RTZ → -0（取整结果为 0 时沿用输入符号）
	TEST_FPRND	12, ftrnd, rf7, rf8, 0x00000000BF000000, 0x04, 0, 0xDEADBEEF80000000, 0x00
	@@ +0.5 RNE → +0（平局取偶）
	TEST_FPRND	13, ftrnd, rf7, rf8, 0x000000003F000000, 0x01, 0, 0xDEADBEEF00000000, 0x00
	@@ -0.0 RNE → -0（零的符号保留）
	TEST_FPRND	14, ftrnd, rf7, rf8, 0x0000000080000000, 0x01, 0, 0xDEADBEEF80000000, 0x00
	@@ 最小次正规 → +0（|x|<1）
	TEST_FPRND	15, ftrnd, rf7, rf8, 0x0000000000000001, 0x01, 0, 0xDEADBEEF00000000, 0x00
	@@ 最大次正规 → +0（绝对值 < 1）
	TEST_FPRND	16, ftrnd, rf7, rf8, 0x00000000007FFFFF, 0x01, 0, 0xDEADBEEF00000000, 0x00
	@@ 2^p（已是整数，且 |x| ≥ 2^p ⇒ 原样返回）
	TEST_FPRND	17, ftrnd, rf7, rf8, 0x000000004B800000, 0x08, 0, 0xDEADBEEF4B800000, 0x00
	@@ 最大有限值 → 原样返回
	TEST_FPRND	18, ftrnd, rf7, rf8, 0x000000007F7FFFFF, 0x01, 0, 0xDEADBEEF7F7FFFFF, 0x00
	@@ +Inf → +Inf（原样、不置标志）
	TEST_FPRND	19, ftrnd, rf7, rf8, 0x000000007F800000, 0x01, 0, 0xDEADBEEF7F800000, 0x00
	@@ -Inf（RDN 档）→ -Inf
	TEST_FPRND	20, ftrnd, rf7, rf8, 0x00000000FF800000, 0x10, 0, 0xDEADBEEFFF800000, 0x00
	@@ qNaN → canonical qNaN（符号 0、payload 归零）、不置 NV
	TEST_FPRND	21, ftrnd, rf7, rf8, 0x000000007FC00123, 0x01, 0, 0xDEADBEEF7FC00000, 0x00
	@@ sNaN（RUP 档）→ canonical qNaN + NV
	TEST_FPRND	22, ftrnd, rf7, rf8, 0x000000007F800001, 0x08, 0, 0xDEADBEEF7FC00000, 0x01

	@@ ---- overlap ----
	@@ 目的 = 源（先读后写）：-3.5 RNE → -4.0
	TEST_FPRND	23, ftrnd, rf9, rf9, 0xDEADBEEFC0600000, 0x01, 0, 0xDEADBEEFC0800000, 0x00
	@@ 源 = rf0（FCSR 低 32 位是 ft canonical qNaN）→ qNaN、不置 NV
	TEST_FPRND	24, ftrnd, rf9, rf0, 0x000000007FC00000, 0x01, 0, 0xDEADBEEF7FC00000, 0x00

	@@ ---- 收窄补点（m13-testcases-044；原 C 探针覆盖、本载体缺的负平局/动态方向）----
	@@ −2.5 RNA（平局远离 0）⇒ −3.0；静态档不置 NX（`spec/SimRISC-07 §2.3`）
	TEST_FPRND	25, ftrnd, rf5, rf6, 0x00000000C0200000, 0x02, 0, 0xDEADBEEFC0400000, 0x00
	@@ −2.5 RNE（平局取偶）⇒ −2.0；静态档不置 NX
	TEST_FPRND	26, ftrnd, rf5, rf6, 0x00000000C0200000, 0x01, 0, 0xDEADBEEFC0000000, 0x00
	@@ +2.5 动态 0x20 读 rf0=RDN（10）⇒ +2.0 + NX
	TEST_FPRND	27, ftrnd, rf5, rf6, 0x0000000040200000, 0x20, 2, 0xDEADBEEF40000000, 0x10
	@@ −2.5 动态 0x20 读 rf0=RUP（11）⇒ −2.0 + NX
	TEST_FPRND	28, ftrnd, rf5, rf6, 0x00000000C0200000, 0x20, 3, 0xDEADBEEFC0000000, 0x10

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	29, ILLI, 0x440C0181
	@@ immu6=0x00 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	30, ILLI, 0x440C5180
	@@ immu6=0x03 非 one-hot ⇒ ILLI
	TEST_FAULT_FP	31, ILLI, 0x440C5183
	@@ immu6=0x30 多位同置 ⇒ ILLI
	TEST_FAULT_FP	32, ILLI, 0x440C51B0

	__TEST_END

	__TEST_SECTIONS
