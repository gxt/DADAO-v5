@@ ftsclb_orrr_rf — ftsclb（orrr, opc 0x44 / ha 0x15）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 缩放（scaleB，`spec/SimRISC-07 §2.1`）：ftsclb rfHB, rfHC, rdHD
@@ 计算 rfHC × 2^rdHD；第三操作数是 rd 组**有符号 64 位整数指数**（rd0 表示 0）
@@ 舍入模式恒取 rf0[33:32]；NaN/Inf/溢出/下溢按 IEEE 754（UF 仅 tiny 且 inexact）
@@ 写宽：`ft` 形式只写目的低 32 位、高 32 位保持原值（`spec/SimRISC-07 §1.3`）
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，证据脚本 `fp_ref.py`）按 spec 现算，不手写
@@ 目的预置 `0xDEADBEEFCAFEF00D`：ft 只写低 32 ⇒ 期望高 32 必须是 `0xDEADBEEF`（写宽回归）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / src=rf6 / 第三域 = rd7（指数 2）：1.5×2^2 = 6.0
	TEST_FPSCLB_ENC	1, 0x44545187, rf5, rf6, 0x000000003FC00000, rd7, 0x0000000000000002, 0, 0xDEADBEEF40C00000, 0x00
	@@ 字段边界：dst=rf63 / src=rf62 / rd63（指数 -3）：1.25×2^-3 = 0.15625
	TEST_FPSCLB_ENC	2, 0x4457FFBF, rf63, rf62, 0x000000003FA00000, rd63, 0xFFFFFFFFFFFFFFFD, 0, 0xDEADBEEF3E200000, 0x00

	@@ ---- semantic ----
	@@ 1.0×2^3 = 8.0（精确、不置标志）
	TEST_FPSCLB	3, ftsclb, rf5, rf6, 0x000000003F800000, rd7, 0x0000000000000003, 0, 0xDEADBEEF41000000, 0x00
	@@ -1.5×2^2 = -6.0
	TEST_FPSCLB	4, ftsclb, rf5, rf6, 0x00000000BFC00000, rd7, 0x0000000000000002, 0, 0xDEADBEEFC0C00000, 0x00
	@@ 1.0×2^-1 = 0.5（负指数按有符号 64 位解释）
	TEST_FPSCLB	5, ftsclb, rf5, rf6, 0x000000003F800000, rd7, 0xFFFFFFFFFFFFFFFF, 0, 0xDEADBEEF3F000000, 0x00
	@@ 指数源 = rd0 ⇒ 指数 0：1.5×2^0 = 1.5
	TEST_FPSCLB	6, ftsclb, rf5, rf6, 0x000000003FC00000, rd0, 0x0000000000000000, 0, 0xDEADBEEF3FC00000, 0x00
	@@ 最小次正规 ×2^1 = 2^-148（精确次正规、不置 UF）
	TEST_FPSCLB	7, ftsclb, rf5, rf6, 0x0000000000000001, rd7, 0x0000000000000001, 0, 0xDEADBEEF00000002, 0x00
	@@ 1.25×2^-3 = 0.15625（精确）
	TEST_FPSCLB	8, ftsclb, rf5, rf6, 0x000000003FA00000, rd7, 0xFFFFFFFFFFFFFFFD, 0, 0xDEADBEEF3E200000, 0x00
	@@ 零保持符号：-0.0×2^5 = -0.0
	TEST_FPSCLB	9, ftsclb, rf5, rf6, 0x0000000080000000, rd7, 0x0000000000000005, 0, 0xDEADBEEF80000000, 0x00

	@@ ---- boundary ----
	@@ 最大有限值×2^1 ⇒ +Inf + OF|NX（RNE 溢出取 Inf）
	TEST_FPSCLB	10, ftsclb, rf7, rf8, 0x000000007F7FFFFF, rd7, 0x0000000000000001, 0, 0xDEADBEEF7F800000, 0x14
	@@ 最大有限值×2^-1 = 精确减半（无标志）
	TEST_FPSCLB	11, ftsclb, rf7, rf8, 0x000000007F7FFFFF, rd7, 0xFFFFFFFFFFFFFFFF, 0, 0xDEADBEEF7EFFFFFF, 0x00
	@@ 最小正规数×2^-1 = 2^(emin-1)（精确次正规、不置 UF）
	TEST_FPSCLB	12, ftsclb, rf7, rf8, 0x0000000000800000, rd7, 0xFFFFFFFFFFFFFFFF, 0, 0xDEADBEEF00400000, 0x00
	@@ 1.0×2^-150 = ½·最小次正规 ⇒ RNE 得 +0 + UF|NX
	TEST_FPSCLB	13, ftsclb, rf7, rf8, 0x000000003F800000, rd7, 0xFFFFFFFFFFFFFF6A, 0, 0xDEADBEEF00000000, 0x18
	@@ 同一值在 rf0=RUP 下 ⇒ 最小次正规 + UF|NX（动态模式生效）
	TEST_FPSCLB	14, ftsclb, rf7, rf8, 0x000000003F800000, rd7, 0xFFFFFFFFFFFFFF6A, 3, 0xDEADBEEF00000001, 0x18
	@@ 1.0×2^200 ⇒ +Inf + OF|NX
	TEST_FPSCLB	15, ftsclb, rf7, rf8, 0x000000003F800000, rd7, 0x00000000000000C8, 0, 0xDEADBEEF7F800000, 0x14
	@@ 1.0×2^-200 ⇒ +0 + UF|NX
	TEST_FPSCLB	16, ftsclb, rf7, rf8, 0x000000003F800000, rd7, 0xFFFFFFFFFFFFFF38, 0, 0xDEADBEEF00000000, 0x18
	@@ +Inf×2^5 = +Inf（不置标志）
	TEST_FPSCLB	17, ftsclb, rf7, rf8, 0x000000007F800000, rd7, 0x0000000000000005, 0, 0xDEADBEEF7F800000, 0x00
	@@ -Inf×2^-5 = -Inf
	TEST_FPSCLB	18, ftsclb, rf7, rf8, 0x00000000FF800000, rd7, 0xFFFFFFFFFFFFFFFB, 0, 0xDEADBEEFFF800000, 0x00
	@@ qNaN×2^3 = canonical qNaN（不置 NV）
	TEST_FPSCLB	19, ftsclb, rf7, rf8, 0x000000007FC00123, rd7, 0x0000000000000003, 0, 0xDEADBEEF7FC00000, 0x00
	@@ sNaN×2^3 = canonical qNaN + NV
	TEST_FPSCLB	20, ftsclb, rf7, rf8, 0x000000007F800001, rd7, 0x0000000000000003, 0, 0xDEADBEEF7FC00000, 0x01
	@@ +0×2^5 = +0（零保持符号）
	TEST_FPSCLB	21, ftsclb, rf7, rf8, 0x0000000000000000, rd7, 0x0000000000000005, 0, 0xDEADBEEF00000000, 0x00

	@@ ---- overlap ----
	@@ 目的 = 源（先读后写）：1.5×2^2 = 6.0
	TEST_FPSCLB	22, ftsclb, rf9, rf9, 0xDEADBEEF3FC00000, rd7, 0x0000000000000002, 0, 0xDEADBEEF40C00000, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	23, ILLI, 0x44540187

	__TEST_END

	__TEST_SECTIONS
