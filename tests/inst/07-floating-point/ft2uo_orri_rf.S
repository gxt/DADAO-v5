@@ ft2uo_orri_rf — ft2uo（orri, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 转换族（§1）：immu6 三套语义（六档 one-hot / SBZ / 复制个数）互斥。
@@ 浮点→整数：有限且取整在范围内 ⇒ inexact 置 NX；NaN/Inf/越界 ⇒ 饱和（按精确值符号取 max/min；NaN 取 max）并置 NV，不置 NX。
@@ 整数→浮点：精度损失 ⇒ NX；本任务的值域不产生 OF/UF（2^64 < ft_max、整数 ≥ 1）。
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rd5 / src=rf6 / immu6=0x01（RNE），3.0 → 3（精确）
	TEST_FPCVT_ENC_RD	1, 0x44CC5181, rd5, rf6, 0x0000000040400000, 0x0000000000000003, 0x00
	@@ 字段边界：dst=rd63 / src=rf62 / immu6=0x04（RTZ），-3.75 → -3 + NX
	TEST_FPCVT_ENC_RD	2, 0x44CFFF84, rd63, rf62, 0x00000000C0700000, 0x0000000000000000, 0x01
	@@ 2.0 → 2（RNE，精确）
	TEST_FPCVT_F2I	3, ft2uo, rd5, rf6, 0x0000000040000000, 0x01, 0, 0x0000000000000002, 0x00
	@@ -2.0 → -2（RNE；结果写满 64 位）
	TEST_FPCVT_F2I	4, ft2uo, rd5, rf6, 0x00000000C0000000, 0x01, 0, 0x0000000000000000, 0x01
	@@ 1.75 RTZ → 1 + NX
	TEST_FPCVT_F2I	5, ft2uo, rd5, rf6, 0x000000003FE00000, 0x04, 0, 0x0000000000000001, 0x10
	@@ -1.75 RTZ → -1 + NX
	TEST_FPCVT_F2I	6, ft2uo, rd5, rf6, 0x00000000BFE00000, 0x04, 0, 0x0000000000000000, 0x01
	@@ 2.5 RNE（平局取偶）→ 2 + NX
	TEST_FPCVT_F2I	7, ft2uo, rd5, rf6, 0x0000000040200000, 0x01, 0, 0x0000000000000002, 0x10
	@@ 2.5 RNA（平局远离 0）→ 3 + NX
	TEST_FPCVT_F2I	8, ft2uo, rd5, rf6, 0x0000000040200000, 0x02, 0, 0x0000000000000003, 0x10
	@@ -2.5 RDN → -3 + NX
	TEST_FPCVT_F2I	9, ft2uo, rd5, rf6, 0x00000000C0200000, 0x10, 0, 0x0000000000000000, 0x01
	@@ 2.5 动态档（0x20）读 rf0=RUP → 3 + NX
	TEST_FPCVT_F2I	10, ft2uo, rd5, rf6, 0x0000000040200000, 0x20, 3, 0x0000000000000003, 0x10
	@@ 静态档 0x01（RNE）不受 rf0=RUP 影响 → 仍 2 + NX（§1.1）
	TEST_FPCVT_F2I	11, ft2uo, rd5, rf6, 0x0000000040200000, 0x01, 3, 0x0000000000000002, 0x10
	@@ 界内最大可表示值 → 18446742974197923840（精确，不置标志）
	TEST_FPCVT_F2I	12, ft2uo, rd5, rf6, 0x000000005F7FFFFF, 0x01, 0, 0xFFFFFF0000000000, 0x00
	@@ 越界（> 目标最大值）→ 饱和 max + NV，不置 NX
	TEST_FPCVT_F2I	13, ft2uo, rd5, rf6, 0x000000005F800000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ +0.0 → 0（精确）
	TEST_FPCVT_F2I	14, ft2uo, rd5, rf6, 0x0000000000000000, 0x01, 0, 0x0000000000000000, 0x00
	@@ -1.0 对无符号目标越界 → 饱和 0 + NV（不置 NX）
	TEST_FPCVT_F2I	15, ft2uo, rd5, rf6, 0x00000000BF800000, 0x01, 0, 0x0000000000000000, 0x01
	@@ -0.5 RNE → 0 + NX（取整后在范围内 ⇒ 只置 NX）
	TEST_FPCVT_F2I	16, ft2uo, rd5, rf6, 0x00000000BF000000, 0x01, 0, 0x0000000000000000, 0x10
	@@ +Inf → 饱和 max + NV
	TEST_FPCVT_F2I	17, ft2uo, rd5, rf6, 0x000000007F800000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ -Inf → 饱和 min + NV
	TEST_FPCVT_F2I	18, ft2uo, rd5, rf6, 0x00000000FF800000, 0x01, 0, 0x0000000000000000, 0x01
	@@ qNaN → 饱和 max + NV（spec：NaN 取饱和值；最大/最小方向见 §1.4 措辞，三方一致取 max，登记待裁定）
	TEST_FPCVT_F2I	19, ft2uo, rd5, rf6, 0x000000007FC00000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ sNaN → 饱和 max + NV（同 NaN，无 NX）
	TEST_FPCVT_F2I	20, ft2uo, rd5, rf6, 0x000000007F800001, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ 2.7 向 +∞（非平局：2.7 非整数）→ 3 + NX（六档之 RUP）
	TEST_FPCVT_F2I	21, ft2uo, rd5, rf6, 0x00000000402CCCCD, 0x08, 0, 0x0000000000000003, 0x10
	@@ 负号 qNaN → 饱和 max + NV（NaN 的符号不改变饱和方向）
	TEST_FPCVT_F2I	22, ft2uo, rd5, rf6, 0x00000000FFC00000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ 源/目的同号（rd6 ← rf6，不同寄存器组，无别名）
	TEST_FPCVT_F2I	23, ft2uo, rd6, rf6, 0x0000000040200000, 0x01, 0, 0x0000000000000002, 0x10
	@@ 窗口顶端同号（rd63 ← rf63）
	TEST_FPCVT_F2I	24, ft2uo, rd63, rf63, 0x00000000BFE00000, 0x04, 0, 0x0000000000000000, 0x01
	@@ 负向溢出：负有限值量级超目标最大值（|−1e30| > 2^64）⇒ 0 + NV（`SimRISC-07 §1.4` 无符号目的）
	TEST_FPCVT_F2I	25, ft2uo, rd5, rf6, 0x00000000F149F2CA, 0x01, 0, 0x0000000000000000, 0x01
	@@ −0.0 ⇒ 0（零是无符号整数的精确表示 ⇒ 无 NV 也无 NX；按符号位判「负 ⇒ NV」的实现必红）
	TEST_FPCVT_F2I	26, ft2uo, rd5, rf6, 0x0000000080000000, 0x01, 0, 0x0000000000000000, 0x00
	@@ legality：目的 rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_FP	27, ILLI, 0x44CC0181
	@@ legality：immu6=0 非六档 ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	28, ILLI, 0x44CC5180
	@@ legality：immu6=0x03 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	29, ILLI, 0x44CC5183
	@@ legality：immu6=0x30 多位同置（非 one-hot）⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	30, ILLI, 0x44CC51B0

	__TEST_END

	__TEST_SECTIONS
