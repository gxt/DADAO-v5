@@ ft2ft_orri_rf — ft2ft（orri, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 复制类（§1.3）：纯 64 位位型搬移、不改位、不置标志；个数 1–63、源/目的范围不得有交集（含完全重合）、起始+个数 ≤ 64。
@@ ft 的**高 32 位不作规定**（contract-fp §1）⇒ 用例只比低 32 位；fo 全 64 位比较。
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rf20 / src=rf40 / immu6=2（两个）
	TEST_FPCOPY_ENC2	1, ft, ft2ft, 0x44094A02, rf40, rf41, rf20, rf21, 0x000000003F800000, 0x000000003F800000, 0x00000000C0200000, 0x00000000C0200000
	@@ 字段边界：dst=rf63 / src=rf62 / immu6=1（只搬一个元素）
	TEST_FPCOPY_ENC2	2, ft, ft2ft, 0x440BFF81, rf62, rf62, rf63, rf63, 0x000000007FC00000, 0x000000007FC00000, 0x000000007FC00000, 0x000000007FC00000
	@@ 个数 1：位型原样搬移（含 NaN payload）
	TEST_FPCOPY1	3, ft, ft2ft, 0x000000003F800000, 0x000000003F800000
	@@ 个数 2：两个元素逐对搬移
	TEST_FPCOPY2	4, ft, ft2ft, 0x000000003F800000, 0x000000003F800000, 0x00000000C0200000, 0x00000000C0200000
	@@ 个数 3：三个元素逐对搬移
	TEST_FPCOPY3	5, ft, ft2ft, 0x000000003F800000, 0x000000003F800000, 0x00000000C0200000, 0x00000000C0200000, 0x000000007FC00000, 0x000000007FC00000
	@@ 个数 4：四个元素逐对搬移
	TEST_FPCOPY4	6, ft, ft2ft, 0x000000003F800000, 0x000000003F800000, 0x00000000C0200000, 0x00000000C0200000, 0x000000007FC00000, 0x000000007FC00000, 0x0000000000000001, 0x0000000000000001
	@@ 寄存器窗口顶端：{rf60:rf63} ← {rf40:rf43}（起始 60 + 4 = 64，§1.3 上界）
	TEST_FPCOPY_TOP4	7, ft, ft2ft, 0x000000003F800000, 0x000000003F800000, 0x00000000C0200000, 0x00000000C0200000, 0x000000007FC00000, 0x000000007FC00000, 0x0000000000000001, 0x0000000000000001
	@@ 最高号单寄存器：rf63 ← rf40
	TEST_FPCOPY_TOP1	8, ft, ft2ft, 0x00000000C0200000, 0x00000000C0200000
	@@ 最大可行个数 31（{rf1:rf31} ← {rf32:rf62}；两端窗口各 31 个、互不相交），逐元素核「目的 == 源内存」
	TEST_FPCOPY_31	9, ft, ft2ft
	@@ 相邻不相交窗口：{rf40:rf41} ← {rf42:rf43}（合法，无交集）
	TEST_FPCOPY_ADJ	10, ft, ft2ft, 0x000000007FC00000, 0x000000007FC00000, 0x0000000000000001, 0x0000000000000001
	@@ rf0 作源合法：复制出的值 == 同一时刻 rf0 的位型（FCSR qNaN 字段）
	TEST_FPCOPY_RF0	11, ft, ft2ft
	@@ legality：目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	12, ILLI, 0x44080A01
	@@ legality：immu6=0 ⇒ ILLI（mreg_zero）
	TEST_FAULT_FP	13, ILLI, 0x44094A00
	@@ legality：起始 60 + 个数 8 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_FP	14, ILLI, 0x440BCA08
	@@ legality：源/目的完全重合 ⇒ ILLI（mreg_range_overlap）
	TEST_FAULT_FP	15, ILLI, 0x44094502
	@@ legality：源/目的部分重合（rf21..rf24 ∩ rf20..rf23）⇒ ILLI（mreg_range_overlap）
	TEST_FAULT_FP	16, ILLI, 0x44094544

	__TEST_END

	__TEST_SECTIONS
