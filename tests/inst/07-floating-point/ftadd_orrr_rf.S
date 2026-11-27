@@ ftadd_orrr_rf — ftadd rfHB, rfHC, rfHD（orrr, opc 0x44 / ha 0x10，单精加法）
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
	@@ 规范编码字：dst=rf5 / c=rf6 / d=rf7（1.5 + 2.25 = 3.75）
	TEST_FPENC	1, ft, 0x44405187, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000040100000, 0x0000000040700000, 0x00
	@@ 字段边界：dst=rf63 / c=rf62 / d=rf61（1.0 + (-1.0) = +0）
	TEST_FPENC	2, ft, 0x4443FFBD, rf63, rf62, 0x000000003F800000, rf61, 0x00000000BF800000, 0x0000000000000000, 0x00

	@@ ---- semantic ----
	@@ 1.0 + 2.0 = 3.0（精确）
	TEST_FP3	3, ft, ftadd, rf5, rf6, 0x000000003F800000, rf7, 0x0000000040000000, 0, 0x0000000040400000, 0x00
	@@ -1.5 + 2.25 = 0.75（异号）
	TEST_FP3	4, ft, ftadd, rf5, rf6, 0x00000000BFC00000, rf7, 0x0000000040100000, 0, 0x000000003F400000, 0x00
	@@ 0.1 + 0.2 ⇒ ft 舍入值 + NX
	TEST_FP3	5, ft, ftadd, rf5, rf6, 0x000000003DCCCCCD, rf7, 0x000000003E4CCCCD, 0, 0x000000003E99999A, 0x10
	@@ 1.5 + 0 = 1.5（+0 恒等）
	TEST_FP3	6, ft, ftadd, rf5, rf6, 0x000000003FC00000, rf7, 0x0000000000000000, 0, 0x000000003FC00000, 0x00

	@@ ---- boundary ----
	@@ 1.5 + (-1.5) 精确抵消 ⇒ +0（RNE）
	TEST_FP3	7, ft, ftadd, rf5, rf6, 0x000000003FC00000, rf7, 0x00000000BFC00000, 0, 0x0000000000000000, 0x00
	@@ 同一抵消在 RDN 下 ⇒ -0（零符号随舍入方向）
	TEST_FP3	8, ft, ftadd, rf5, rf6, 0x000000003FC00000, rf7, 0x00000000BFC00000, 2, 0x0000000080000000, 0x00
	@@ qNaN + 1.0 ⇒ canonical qNaN，不置标志
	TEST_FP3	9, ft, ftadd, rf5, rf6, 0x000000007FC00000, rf7, 0x000000003F800000, 0, 0x000000007FC00000, 0x00
	@@ sNaN + 1.0 ⇒ canonical qNaN + NV
	TEST_FP3	10, ft, ftadd, rf5, rf6, 0x000000007F800001, rf7, 0x000000003F800000, 0, 0x000000007FC00000, 0x01
	@@ +Inf + (-Inf) ⇒ qNaN + NV
	TEST_FP3	11, ft, ftadd, rf5, rf6, 0x000000007F800000, rf7, 0x00000000FF800000, 0, 0x000000007FC00000, 0x01
	@@ +Inf + 1.0 ⇒ +Inf，不置标志
	TEST_FP3	12, ft, ftadd, rf5, rf6, 0x000000007F800000, rf7, 0x000000003F800000, 0, 0x000000007F800000, 0x00
	@@ ft_max + ft_max ⇒ +Inf + OF|NX（RNE）
	TEST_FP3	13, ft, ftadd, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x000000007F7FFFFF, 0, 0x000000007F800000, 0x14
	@@ ft_max + ft_max 在 RTZ 下 ⇒ ft_max + OF|NX（溢出 ≠ Inf）
	TEST_FP3	14, ft, ftadd, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x000000007F7FFFFF, 1, 0x000000007F7FFFFF, 0x14
	@@ 1.0 + 2^-25 恰在 RNE 中点 ⇒ 1.0 + NX
	TEST_FP3	15, ft, ftadd, rf5, rf6, 0x000000003F800000, rf7, 0x0000000033000000, 0, 0x000000003F800000, 0x10
	@@ 同一和在 RUP 下 ⇒ 1+2^-23 + NX
	TEST_FP3	16, ft, ftadd, rf5, rf6, 0x000000003F800000, rf7, 0x0000000033000000, 3, 0x000000003F800001, 0x10

	@@ ---- overlap ----
	@@ 目的 = 源C（rf9 = rf9 + 2.25）
	TEST_FP3	17, ft, ftadd, rf9, rf9, 0x000000003FC00000, rf7, 0x0000000040100000, 0, 0x0000000040700000, 0x00
	@@ 两源同名（rf9 = rf6 + rf6）
	TEST_FP3	18, ft, ftadd, rf9, rf6, 0x000000003FC00000, rf6, 0x000000003FC00000, 0, 0x0000000040400000, 0x00

	@@ ---- 边界补齐（m20-testcases-009；NaN 优先 / 次正规 / 溢出四象限，`SimRISC-07 §2.1/§1.3`）----
	@@ qNaN + sNaN ⇒ canonical qNaN + NV（sNaN 优先置 NV，qNaN 不掩盖）
	TEST_FP3	19, ft, ftadd, rf5, rf6, 0x000000007FC00000, rf7, 0x000000007F800001, 0, 0x000000007FC00000, 0x01
	@@ 负号 qNaN（含 payload）+ 1.0 ⇒ canonical 正 qNaN，不置标志（payload/符号归零）
	TEST_FP3	20, ft, ftadd, rf5, rf6, 0x00000000FFC12345, rf7, 0x000000003F800000, 0, 0x000000007FC00000, 0x00
	@@ 最小次正规 + 最小次正规 = 2^-148（精确次正规输出）⇒ 不置 UF/NX
	TEST_FP3	21, ft, ftadd, rf5, rf6, 0x0000000000000001, rf7, 0x0000000000000001, 0, 0x0000000000000002, 0x00
	@@ 最大次正规 + 最小次正规 = 最小正规（精确进位）⇒ 不置 UF/NX
	TEST_FP3	22, ft, ftadd, rf5, rf6, 0x00000000007FFFFF, rf7, 0x0000000000000001, 0, 0x0000000000800000, 0x00
	@@ 最大次正规 + 最大次正规 = 0x00FFFFFE（精确，和进入正规区）⇒ 不置 UF/NX
	TEST_FP3	23, ft, ftadd, rf5, rf6, 0x00000000007FFFFF, rf7, 0x00000000007FFFFF, 0, 0x0000000000FFFFFE, 0x00
	@@ 正溢出 RUP ⇒ +Inf + OF|NX
	TEST_FP3	24, ft, ftadd, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x000000007F7FFFFF, 3, 0x000000007F800000, 0x14
	@@ 正溢出 RDN ⇒ +ft_max + OF|NX（溢出 ≠ Inf）
	TEST_FP3	25, ft, ftadd, rf5, rf6, 0x000000007F7FFFFF, rf7, 0x000000007F7FFFFF, 2, 0x000000007F7FFFFF, 0x14
	@@ 负溢出 RDN ⇒ −Inf + OF|NX
	TEST_FP3	26, ft, ftadd, rf5, rf6, 0x00000000FF7FFFFF, rf7, 0x00000000FF7FFFFF, 2, 0x00000000FF800000, 0x14
	@@ 负溢出 RUP ⇒ −ft_max + OF|NX（溢出 ≠ Inf）
	TEST_FP3	27, ft, ftadd, rf5, rf6, 0x00000000FF7FFFFF, rf7, 0x00000000FF7FFFFF, 3, 0x00000000FF7FFFFF, 0x14

	@@ ---- legality ----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0；汇编器拒绝，给编码字）
	TEST_FAULT_FP	28, ILLI, 0x44400083

	__TEST_END

	__TEST_SECTIONS
