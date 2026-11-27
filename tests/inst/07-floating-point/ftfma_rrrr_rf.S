@@ ftfma_rrrr_rf — ftfma rfHA, rfHB, rfHC, rfHD（rrrr, opc 0x5E，fused multiply-add，单次舍入）
@@ 大类：07-floating-point（浮点运算，`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 每个用例：清 rf0[4:0] → 设 rf0[33:32] → 执行 → 断言 rf0[4:0]（NV=1/DZ=2/OF=4/UF=8/NX=16）
@@   → 比对结果（二者共用点号）；ft 只比低 32 位（高 32 位不作规定）
@@ 初值经 `set.fo` 装配（整 64 位：`rd2rf rf, rd0` + 非零 wyde 的 `set.w`；不经浮点指令）；期望值由独立 IEEE 754 参考模型复算
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 规范编码字：dst=rf5 / b=rf6(2) / c=rf7(3) / d=rf8(4) ⇒ 10
	TEST_FPENC4	1, ft, 0x5E1461C8, rf5, rf6, 0x0000000040000000, rf7, 0x0000000040400000, rf8, 0x0000000040800000, 0x0000000041200000, 0x00
	@@ 字段边界：dst=rf63 / b=rf62(1) / c=rf61(1) / d=rf60(-1) ⇒ +0
	TEST_FPENC4	2, ft, 0x5EFFEF7C, rf63, rf62, 0x000000003F800000, rf61, 0x000000003F800000, rf60, 0x00000000BF800000, 0x0000000000000000, 0x00

	@@ ---- semantic ----
	@@ 2 × 3 + 4 = 10
	TEST_FP4	3, ft, ftfma, rf5, rf6, 0x0000000040000000, rf7, 0x0000000040400000, rf8, 0x0000000040800000, 0, 0x0000000041200000, 0x00
	@@ 规格反例：(1+2^-23)(1-2^-23) - 1 = -2^-46（单次舍入，0xA8800000）
	TEST_FP4	4, ft, ftfma, rf5, rf6, 0x000000003F800001, rf7, 0x000000003F7FFFFE, rf8, 0x00000000BF800000, 0, 0x00000000A8800000, 0x00
	@@ -2 × 3 + 1 = -5
	TEST_FP4	5, ft, ftfma, rf5, rf6, 0x00000000C0000000, rf7, 0x0000000040400000, rf8, 0x000000003F800000, 0, 0x00000000C0A00000, 0x00
	@@ 0.5 × 0.5 + 0.25 = 0.5（精确）
	TEST_FP4	6, ft, ftfma, rf5, rf6, 0x000000003F000000, rf7, 0x000000003F000000, rf8, 0x000000003E800000, 0, 0x000000003F000000, 0x00

	@@ ---- boundary ----
	@@ 0 × Inf + qNaN ⇒ qNaN + NV（0×Inf 优先于 NaN 传播）
	TEST_FP4	7, ft, ftfma, rf5, rf6, 0x0000000000000000, rf7, 0x000000007F800000, rf8, 0x000000007FC00000, 0, 0x000000007FC00000, 0x01
	@@ Inf × 2 + (-Inf) ⇒ qNaN + NV
	TEST_FP4	8, ft, ftfma, rf5, rf6, 0x000000007F800000, rf7, 0x0000000040000000, rf8, 0x00000000FF800000, 0, 0x000000007FC00000, 0x01
	@@ Inf × 2 + 1 ⇒ +Inf
	TEST_FP4	9, ft, ftfma, rf5, rf6, 0x000000007F800000, rf7, 0x0000000040000000, rf8, 0x000000003F800000, 0, 0x000000007F800000, 0x00
	@@ qNaN × 1 + 1 ⇒ qNaN，不置标志
	TEST_FP4	10, ft, ftfma, rf5, rf6, 0x000000007FC00000, rf7, 0x000000003F800000, rf8, 0x000000003F800000, 0, 0x000000007FC00000, 0x00
	@@ sNaN × 1 + 1 ⇒ qNaN + NV
	TEST_FP4	11, ft, ftfma, rf5, rf6, 0x000000007F800001, rf7, 0x000000003F800000, rf8, 0x000000003F800000, 0, 0x000000007FC00000, 0x01
	@@ 1 × 1 + (-1) ⇒ +0（RNE）
	TEST_FP4	12, ft, ftfma, rf5, rf6, 0x000000003F800000, rf7, 0x000000003F800000, rf8, 0x00000000BF800000, 0, 0x0000000000000000, 0x00
	@@ 1 × 1 + (-1) ⇒ -0（RDN）
	TEST_FP4	13, ft, ftfma, rf5, rf6, 0x000000003F800000, rf7, 0x000000003F800000, rf8, 0x00000000BF800000, 2, 0x0000000080000000, 0x00
	@@ ft_max × 2 + 0 ⇒ +Inf + OF|NX（RNE）
	TEST_FP4	14, ft, ftfma, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x0000000040000000, rf8, 0x0000000000000000, 0, 0x000000007F800000, 0x14
	@@ ft_max × 2 + 0 在 RTZ 下 ⇒ ft_max + OF|NX
	TEST_FP4	15, ft, ftfma, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x0000000040000000, rf8, 0x0000000000000000, 1, 0x000000007F7FFFFF, 0x14
	@@ 最小次正规 × 0.5 + 0 ⇒ +0 + UF|NX
	TEST_FP4	16, ft, ftfma, rf5, rf6, 0x0000000000000001, rf7, 0x000000003F000000, rf8, 0x0000000000000000, 0, 0x0000000000000000, 0x18

	@@ ---- overlap ----
	@@ 目的 = 第一乘数（rf9 = rf9 × 2 + 4）
	TEST_FP4	17, ft, ftfma, rf9, rf9, 0x0000000040000000, rf7, 0x0000000040000000, rf8, 0x0000000040800000, 0, 0x0000000041000000, 0x00
	@@ 目的 = 第二乘数（rf9 = 2 × rf9 + 4）
	TEST_FP4	18, ft, ftfma, rf9, rf6, 0x0000000040000000, rf9, 0x0000000040000000, rf8, 0x0000000040800000, 0, 0x0000000041000000, 0x00
	@@ 目的 = 加数（rf9 = 2 × 3 + rf9）
	TEST_FP4	19, ft, ftfma, rf9, rf6, 0x0000000040000000, rf7, 0x0000000040400000, rf9, 0x0000000040800000, 0, 0x0000000041200000, 0x00

	@@ ---- 收窄补点（m13-testcases-044；原 C 探针覆盖、本载体缺的边界，依据 `spec/SimRISC-07 §2.5`）----
	@@ 轻微溢出：精确和 = ft_max + 2^102（1/4 ulp，ulp = 2^104）> max，
	@@   RNE 的无限指数舍入结果仍为 ft_max ⇒ 不构成溢出 ⇒ 结果 ft_max、只置 NX
	TEST_FP4	20, ft, ftfma, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x000000003F800000, rf8, 0x0000000072800000, 0, 0x000000007F7FFFFF, 0x10
	@@ 同一输入在 RUP 下舍到 2^128 > max ⇒ 溢出 ⇒ +Inf + OF|NX
	TEST_FP4	21, ft, ftfma, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x000000003F800000, rf8, 0x0000000072800000, 3, 0x000000007F800000, 0x14
	@@ 次正规结果且 inexact：2^-149 × 1.25 = 1.25 单位 ⇒ RNE 舍到 1 单位（2^-149），UF|NX
	TEST_FP4	22, ft, ftfma, rf5, rf6, 0x0000000000000001, rf7, 0x000000003FA00000, rf8, 0x0000000000000000, 0, 0x0000000000000001, 0x18
	@@ 同一输入在 RUP 下舍到 2 单位（2^-148），UF|NX
	TEST_FP4	23, ft, ftfma, rf5, rf6, 0x0000000000000001, rf7, 0x000000003FA00000, rf8, 0x0000000000000000, 3, 0x0000000000000002, 0x18
	@@ Inf 作加数：1 × 2 + (−Inf) ⇒ −Inf，不置标志（`§2.5`「特例」第 3 条）
	TEST_FP4	24, ft, ftfma, rf5, rf6, 0x000000003F800000, rf7, 0x0000000040000000, rf8, 0x00000000FF800000, 0, 0x00000000FF800000, 0x00

	@@ ---- 边界补齐（m20-testcases-009；0×Inf 优先 / NaN 加法数 / tininess-after-rounding）----
	@@ 0 × −Inf + qNaN ⇒ qNaN + NV（负 Inf 变体；零乘无穷优先于 NaN 传播）
	TEST_FP4	25, ft, ftfma, rf5, rf6, 0x0000000000000000, rf7, 0x00000000FF800000, rf8, 0x000000007FC00000, 0, 0x000000007FC00000, 0x01
	@@ Inf × Inf + (−Inf) ⇒ qNaN + NV（Inf + (−Inf)）
	TEST_FP4	26, ft, ftfma, rf5, rf6, 0x000000007F800000, rf7, 0x000000007F800000, rf8, 0x00000000FF800000, 0, 0x000000007FC00000, 0x01
	@@ 加数为负号 qNaN（含 payload）⇒ canonical 正 qNaN，不置标志
	TEST_FP4	27, ft, ftfma, rf5, rf6, 0x000000003F800000, rf7, 0x000000003F800000, rf8, 0x00000000FFC00123, 0, 0x000000007FC00000, 0x00
	@@ 加数为 sNaN ⇒ qNaN + NV（有限积不掩盖 sNaN）
	TEST_FP4	28, ft, ftfma, rf5, rf6, 0x000000003F800000, rf7, 0x000000003F800000, rf8, 0x000000007F800001, 0, 0x000000007FC00000, 0x01
	@@ tininess-after-rounding（RNE）：最大次正规 × (1+2^-23) 的精确积 = min_normal − 2^-172，
	@@   舍入后等于最小正规 ⇒ 非 tiny ⇒ 只置 NX、不置 UF（`SimRISC-07 §1.3/§2.5`）
	TEST_FP4	29, ft, ftfma, rf5, rf6, 0x00000000007FFFFF, rf7, 0x000000003F800001, rf8, 0x0000000000000000, 0, 0x0000000000800000, 0x10
	@@ 同一输入 RTZ 舍到最大次正规（舍入后仍 tiny 且 inexact）⇒ UF|NX
	TEST_FP4	30, ft, ftfma, rf5, rf6, 0x00000000007FFFFF, rf7, 0x000000003F800001, rf8, 0x0000000000000000, 1, 0x00000000007FFFFF, 0x18
	@@ 最小次正规 × 2 = 2^-148（精确次正规输出）⇒ 不置 UF/NX
	TEST_FP4	31, ft, ftfma, rf5, rf6, 0x0000000000000001, rf7, 0x0000000040000000, rf8, 0x0000000000000000, 0, 0x0000000000000002, 0x00

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0；汇编器拒绝，给编码字）
	TEST_FAULT_FP	32, ILLI, 0x5E0020C4

	__TEST_END

	__TEST_SECTIONS
