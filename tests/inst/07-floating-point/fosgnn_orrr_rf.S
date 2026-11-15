@@ fosgnn_orrr_rf — fosgnn（orrr, opc 0x44 / ha 0x1E）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 符号注入（`spec/SimRISC-07 §3`）：fosgnn rfHB, rfHC, rfHD
@@ copySignNeg：rfHC 除符号位外的位 + rfHD 符号位取反；纯位操作：payload 逐位保留、不置任何标志
@@ 符号取位：ft = rfHD bit31（只写目的低 32、高 32 保持原值）；fo = rfHD bit63（整 64 位写）
@@ 特例：rfHD = rf0 ⇒ abs / -abs；rfHC = rfHD ⇒ copy / negate
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，证据脚本 `fp_ref.py`）按 spec 现算，不手写
@@ 目的预置 `0xDEADBEEFCAFEF00D`：ft 只写低 32 ⇒ 期望高 32 必须是 `0xDEADBEEF`（写宽回归）
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / src=rf6 / 符号源 rf7（-2.0）：+1.5 → -1.5
	TEST_FPSGN_ENC	1, 0x44785187, rf5, rf6, 0x3FF8000000000000, rf7, 0xC000000000000000, 0x3FF8000000000000, 0x00
	@@ 字段边界：dst=rf63 / src=rf62 / 符号源 rf61（+2.0）：-1.5 → +1.5
	TEST_FPSGN_ENC	2, 0x447BFFBD, rf63, rf62, 0xBFF8000000000000, rf61, 0x4000000000000000, 0xBFF8000000000000, 0x00

	@@ ---- semantic ----
	@@ copySignNeg：+1.5（符号源 -2.0）→ +1.5
	TEST_FPSGN	3, fosgnn, rf5, rf6, 0x3FF8000000000000, rf7, 0xC000000000000000, 0x3FF8000000000000, 0x00
	@@ copySignNeg：-1.5（符号源 +2.0）→ -1.5
	TEST_FPSGN	4, fosgnn, rf5, rf6, 0xBFF8000000000000, rf7, 0x4000000000000000, 0xBFF8000000000000, 0x00
	@@ copySignNeg：-1.5（符号源 -2.0）→ +1.5
	TEST_FPSGN	5, fosgnn, rf5, rf6, 0xBFF8000000000000, rf7, 0xC000000000000000, 0x3FF8000000000000, 0x00
	@@ 符号源 = rf0 ⇒ -abs(rfHC)（FCSR 符号位恒 0）
	TEST_FPSGN	6, fosgnn, rf5, rf6, 0xBFF8000000000000, rf0, 0x0000000000000000, 0xBFF8000000000000, 0x00

	@@ ---- boundary ----
	@@ rfHC = rfHD（同号寄存器）⇒ negate（符号取反）
	TEST_FPSGN	7, fosgnn, rf5, rf9, 0xBFF0000000000000, rf9, 0xBFF0000000000000, 0x3FF0000000000000, 0x00
	@@ qNaN 的 payload 逐位保留（纯位操作，不 canonical 化）
	TEST_FPSGN	8, fosgnn, rf5, rf6, 0x7FF8000000000001, rf7, 0xC000000000000000, 0x7FF8000000000001, 0x00
	@@ sNaN 输入不置 NV、位型按符号注入返回
	TEST_FPSGN	9, fosgnn, rf5, rf6, 0x7FF0000000000001, rf7, 0xC000000000000000, 0x7FF0000000000001, 0x00
	@@ +0 的符号取自符号源：+0（符号源 -2.0）→ -0
	TEST_FPSGN	10, fosgnn, rf5, rf6, 0x0000000000000000, rf7, 0xC000000000000000, 0x0000000000000000, 0x00
	@@ -0（符号源 +2.0）→ 符号位 1
	TEST_FPSGN	11, fosgnn, rf5, rf6, 0x8000000000000000, rf7, 0x4000000000000000, 0x8000000000000000, 0x00
	@@ -Inf（符号源 +2.0）→ 符号位 1（-Inf）
	TEST_FPSGN	12, fosgnn, rf5, rf6, 0xFFF0000000000000, rf7, 0x4000000000000000, 0xFFF0000000000000, 0x00
	@@ 最小次正规（符号源 -2.0）⇒ 只改符号位、payload 不动
	TEST_FPSGN	13, fosgnn, rf5, rf6, 0x0000000000000001, rf7, 0xC000000000000000, 0x0000000000000001, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源（先读后写）：+1.5（符号源 -2.0）
	TEST_FPSGN	14, fosgnn, rf9, rf9, 0x3FF8000000000000, rf7, 0xC000000000000000, 0x3FF8000000000000, 0x00
	@@ 目的 = 符号源（符号取自已被读出的 rf9）
	TEST_FPSGN	15, fosgnn, rf9, rf6, 0x3FF8000000000000, rf9, 0xC000000000000000, 0x3FF8000000000000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	16, ILLI, 0x44780187

	__TEST_END

	__TEST_SECTIONS
