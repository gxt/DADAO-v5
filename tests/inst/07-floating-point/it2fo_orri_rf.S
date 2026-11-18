@@ it2fo_orri_rf — it2fo（orri, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 转换族（§1）：immu6 三套语义（六档 one-hot / SBZ / 复制个数）互斥。
@@ 浮点→整数：有限且取整在范围内 ⇒ inexact 置 NX；NaN/Inf/越界 ⇒ 饱和（按精确值符号取 max/min；NaN 取 max）并置 NV，不置 NX。
@@ 整数→浮点：精度损失 ⇒ NX；本任务的值域不产生 OF/UF（2^64 < ft_max、整数 ≥ 1）。
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段址见宏层文件头）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rf5 / src=rd6 / immu6=0x00，3 → 3.0（精确）
	TEST_FPCVT_ENC_RF	1, fo, 0x44F05180, rf5, rd6, 0x0000000000000003, 0x4008000000000000, 0x00
	@@ 字段边界：dst=rf63 / src=rd62
	TEST_FPCVT_ENC_RF	2, fo, 0x44F3FF80, rf63, rd62, 0x0000000000000001, 0x3FF0000000000000, 0x00
	@@ 0 → +0（精确）
	TEST_FPCVT_I2F	3, fo, it2fo, rf5, rd6, 0x0000000000000000, 0x00, 0, 0x0000000000000000, 0x00
	@@ 1 → 1.0（精确）
	TEST_FPCVT_I2F	4, fo, it2fo, rf5, rd6, 0x0000000000000001, 0x00, 0, 0x3FF0000000000000, 0x00
	@@ 2^20 一类的精确值 → 不置标志
	TEST_FPCVT_I2F	5, fo, it2fo, rf5, rd6, 0x0000000000100000, 0x00, 0, 0x4130000000000000, 0x00
	@@ 源类型最大值 → 精确装入（SBZ 精确转换）
	TEST_FPCVT_I2F	6, fo, it2fo, rf5, rd6, 0x000000007FFFFFFF, 0x00, 0, 0x41DFFFFFFFC00000, 0x00
	@@ 源类型最小值 → 精确装入
	TEST_FPCVT_I2F	7, fo, it2fo, rf5, rd6, 0xFFFFFFFF80000000, 0x00, 0, 0xC1E0000000000000, 0x00
	@@ SBZ 与 rf0 无关：rf0=RDN 下仍精确（不读环境）
	TEST_FPCVT_I2F	8, fo, it2fo, rf5, rd6, 0x000000007FFFFFFF, 0x00, 2, 0x41DFFFFFFFC00000, 0x00
	@@ 源/目的同号（rf6 ← rd6，不同寄存器组）
	TEST_FPCVT_I2F	9, fo, it2fo, rf6, rd6, 0x0000000000000005, 0x00, 0, 0x4014000000000000, 0x00
	@@ 窗口顶端同号（rf63 ← rd63）
	TEST_FPCVT_I2F	10, fo, it2fo, rf63, rd63, 0x000000000000003F, 0x00, 0, 0x404F800000000000, 0x00
	@@ legality：目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	11, ILLI, 0x44F00180
	@@ legality：SBZ 非 0（immu6=0x01）⇒ ILLI（encode_sbz）
	TEST_FAULT_FP	12, ILLI, 0x44F05181
	@@ legality：SBZ 非 0（immu6=0x20）⇒ ILLI（encode_sbz）
	TEST_FAULT_FP	13, ILLI, 0x44F051A0

	__TEST_END

	__TEST_SECTIONS
