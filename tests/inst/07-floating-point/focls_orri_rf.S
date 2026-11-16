@@ focls_orri_rf — focls（orri, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 分类（§5）：结果只占 [9:0]（其余位清零），按 rf 窗口逐个分类写到 rd 窗口；个数 1–63、起始+个数 ≤ 64、目的不得为 rd0。
@@ ftcls 只看源寄存器**低 32 位**（高 32 位不作规定）；rf0 作源合法。
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rd8 / src=rf40 / immu6=1，1.0 → 0x100
	TEST_FPCLS_ENC1	1, focls, 0x44208A01, rd8, 0x3FF0000000000000, 0x0000000000000100
	@@ 字段边界：dst=rd60 / src=rf63 / immu6=1
	TEST_FPCLS_ENC1	2, focls, 0x4423CFC1, rd60, 0x0000000000000000, 0x0000000000000040
	@@ positiveNormal → 第 8 位（0x100）
	TEST_FPCLS1	3, focls, 0x3FF0000000000000, 0x0000000000000100
	@@ negativeNormal → 第 3 位（0x008）
	TEST_FPCLS1	4, focls, 0xBFF0000000000000, 0x0000000000000008
	@@ positiveZero → 第 6 位（0x040）
	TEST_FPCLS1	5, focls, 0x0000000000000000, 0x0000000000000040
	@@ negativeZero → 第 5 位（0x020）
	TEST_FPCLS1	6, focls, 0x8000000000000000, 0x0000000000000020
	@@ positiveSubnormal（最小次正规）→ 第 7 位（0x080）
	TEST_FPCLS1	7, focls, 0x0000000000000001, 0x0000000000000080
	@@ negativeSubnormal → 第 4 位（0x010）
	TEST_FPCLS1	8, focls, 0x8000000000000001, 0x0000000000000010
	@@ positiveInfinity → 第 9 位（0x200）
	TEST_FPCLS1	9, focls, 0x7FF0000000000000, 0x0000000000000200
	@@ negativeInfinity → 第 2 位（0x004）
	TEST_FPCLS1	10, focls, 0xFFF0000000000000, 0x0000000000000004
	@@ quietNaN → 第 1 位（0x002）
	TEST_FPCLS1	11, focls, 0x7FF8000000000000, 0x0000000000000002
	@@ signalingNaN → 第 0 位（0x001）
	TEST_FPCLS1	12, focls, 0x7FF0000000000001, 0x0000000000000001
	@@ 两个元素：正规 + 正次正规（序号递增逐对）
	TEST_FPCLS2	13, focls, 0x3FF0000000000000, 0x0000000000000100, 0x0000000000000001, 0x0000000000000080
	@@ 三个元素：+0 / -0 / +Inf
	TEST_FPCLS3	14, focls, 0x0000000000000000, 0x0000000000000040, 0x8000000000000000, 0x0000000000000020, 0x7FF0000000000000, 0x0000000000000200
	@@ 四个元素：-Inf / -正规 / -次正规 / qNaN（[63:10] 必须清零）
	TEST_FPCLS4	15, focls, 0xFFF0000000000000, 0x0000000000000004, 0xBFF0000000000000, 0x0000000000000008, 0x8000000000000001, 0x0000000000000010, 0x7FF8000000000000, 0x0000000000000002
	@@ rf0 作源：读出的位型按本宽度是 qNaN（fo 全 64 位；ft 低 32 位）
	TEST_FPCLS_RF0	16, focls, 0x0000000000000002
	@@ 范围上界：{rd60:rd63} ← {rf60:rf63}（起始 60 + 个数 4 = 64，合法）
	TEST_FPCLS_TOP4	17, focls, 0x3FF0000000000000, 0x0000000000000100, 0xBFF0000000000000, 0x0000000000000008, 0x7FF0000000000000, 0x0000000000000200, 0xFFF0000000000000, 0x0000000000000004
	@@ overlap：目的 rd40 / 源 rf40（同号、不同寄存器组，无别名）
	TEST_FPCLS1_IDX	18, focls, 0x3FF0000000000000, 0x0000000000000100
	@@ legality：目的 rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_FP	19, ILLI, 0x44200A01
	@@ legality：immu6=0 ⇒ ILLI（mreg_zero）
	TEST_FAULT_FP	20, ILLI, 0x44214A00
	@@ legality：目的起始 61 + 4 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_FP	21, ILLI, 0x4423DA04
	@@ legality：源起始 61 + 4 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_FP	22, ILLI, 0x44214F44

	__TEST_END

	__TEST_SECTIONS
