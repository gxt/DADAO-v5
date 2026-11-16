@@ fo2uo_orri_rf — fo2uo（orri, opc 0x44）
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
	TEST_FPCVT_ENC_RD	1, 0x44EC5181, rd5, rf6, 0x4008000000000000, 0x0000000000000003, 0x00
	@@ 字段边界：dst=rd63 / src=rf62 / immu6=0x04（RTZ），-3.75 → -3 + NX
	TEST_FPCVT_ENC_RD	2, 0x44EFFF84, rd63, rf62, 0xC00E000000000000, 0x0000000000000000, 0x01
	@@ 2.0 → 2（RNE，精确）
	TEST_FPCVT_F2I	3, fo2uo, rd5, rf6, 0x4000000000000000, 0x01, 0, 0x0000000000000002, 0x00
	@@ -2.0 → -2（RNE；结果写满 64 位）
	TEST_FPCVT_F2I	4, fo2uo, rd5, rf6, 0xC000000000000000, 0x01, 0, 0x0000000000000000, 0x01
	@@ 1.75 RTZ → 1 + NX
	TEST_FPCVT_F2I	5, fo2uo, rd5, rf6, 0x3FFC000000000000, 0x04, 0, 0x0000000000000001, 0x10
	@@ -1.75 RTZ → -1 + NX
	TEST_FPCVT_F2I	6, fo2uo, rd5, rf6, 0xBFFC000000000000, 0x04, 0, 0x0000000000000000, 0x01
	@@ 2.5 RNE（平局取偶）→ 2 + NX
	TEST_FPCVT_F2I	7, fo2uo, rd5, rf6, 0x4004000000000000, 0x01, 0, 0x0000000000000002, 0x10
	@@ 2.5 RNA（平局远离 0）→ 3 + NX
	TEST_FPCVT_F2I	8, fo2uo, rd5, rf6, 0x4004000000000000, 0x02, 0, 0x0000000000000003, 0x10
	@@ -2.5 RDN → -3 + NX
	TEST_FPCVT_F2I	9, fo2uo, rd5, rf6, 0xC004000000000000, 0x10, 0, 0x0000000000000000, 0x01
	@@ 2.5 动态档（0x20）读 rf0=RUP → 3 + NX
	TEST_FPCVT_F2I	10, fo2uo, rd5, rf6, 0x4004000000000000, 0x20, 3, 0x0000000000000003, 0x10
	@@ 静态档 0x01（RNE）不受 rf0=RUP 影响 → 仍 2 + NX（§1.1）
	TEST_FPCVT_F2I	11, fo2uo, rd5, rf6, 0x4004000000000000, 0x01, 3, 0x0000000000000002, 0x10
	@@ 界内最大可表示值 → 18446744073709549568（精确，不置标志）
	TEST_FPCVT_F2I	12, fo2uo, rd5, rf6, 0x43EFFFFFFFFFFFFF, 0x01, 0, 0xFFFFFFFFFFFFF800, 0x00
	@@ 越界（> 目标最大值）→ 饱和 max + NV，不置 NX
	TEST_FPCVT_F2I	13, fo2uo, rd5, rf6, 0x43F0000000000000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ +0.0 → 0（精确）
	TEST_FPCVT_F2I	14, fo2uo, rd5, rf6, 0x0000000000000000, 0x01, 0, 0x0000000000000000, 0x00
	@@ -1.0 对无符号目标越界 → 饱和 0 + NV（不置 NX）
	TEST_FPCVT_F2I	15, fo2uo, rd5, rf6, 0xBFF0000000000000, 0x01, 0, 0x0000000000000000, 0x01
	@@ -0.5 RNE → 0 + NX（取整后在范围内 ⇒ 只置 NX）
	TEST_FPCVT_F2I	16, fo2uo, rd5, rf6, 0xBFE0000000000000, 0x01, 0, 0x0000000000000000, 0x10
	@@ +Inf → 饱和 max + NV
	TEST_FPCVT_F2I	17, fo2uo, rd5, rf6, 0x7FF0000000000000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ -Inf → 饱和 min + NV
	TEST_FPCVT_F2I	18, fo2uo, rd5, rf6, 0xFFF0000000000000, 0x01, 0, 0x0000000000000000, 0x01
	@@ qNaN → 饱和 max + NV（spec：NaN 取饱和值；最大/最小方向见 §1.4 措辞，三方一致取 max，登记待裁定）
	TEST_FPCVT_F2I	19, fo2uo, rd5, rf6, 0x7FF8000000000000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ sNaN → 饱和 max + NV（同 NaN，无 NX）
	TEST_FPCVT_F2I	20, fo2uo, rd5, rf6, 0x7FF0000000000001, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ 2.7 向 +∞（非平局：2.7 非整数）→ 3 + NX（六档之 RUP）
	TEST_FPCVT_F2I	21, fo2uo, rd5, rf6, 0x400599999999999A, 0x08, 0, 0x0000000000000003, 0x10
	@@ 负号 qNaN → 饱和 max + NV（NaN 的符号不改变饱和方向）
	TEST_FPCVT_F2I	22, fo2uo, rd5, rf6, 0xFFF8000000000000, 0x01, 0, 0xFFFFFFFFFFFFFFFF, 0x01
	@@ 源/目的同号（rd6 ← rf6，不同寄存器组，无别名）
	TEST_FPCVT_F2I	23, fo2uo, rd6, rf6, 0x4004000000000000, 0x01, 0, 0x0000000000000002, 0x10
	@@ 窗口顶端同号（rd63 ← rf63）
	TEST_FPCVT_F2I	24, fo2uo, rd63, rf63, 0xBFFC000000000000, 0x04, 0, 0x0000000000000000, 0x01
	@@ 负向溢出：负有限值量级超目标最大值（|−1e300| > 2^64）⇒ 0 + NV（`SimRISC-07 §1.4` 无符号目的）
	TEST_FPCVT_F2I	25, fo2uo, rd5, rf6, 0xFE37E43C8800759C, 0x01, 0, 0x0000000000000000, 0x01
	@@ −0.0 ⇒ 0（零是无符号整数的精确表示 ⇒ 无 NV 也无 NX；按符号位判「负 ⇒ NV」的实现必红）
	TEST_FPCVT_F2I	26, fo2uo, rd5, rf6, 0x8000000000000000, 0x01, 0, 0x0000000000000000, 0x00
	@@ legality：目的 rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_FP	27, ILLI, 0x44EC0181
	@@ legality：immu6=0 非六档 ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	28, ILLI, 0x44EC5180
	@@ legality：immu6=0x03 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	29, ILLI, 0x44EC5183
	@@ legality：immu6=0x30 多位同置（非 one-hot）⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	30, ILLI, 0x44EC51B0

	__TEST_END

	__TEST_SECTIONS
