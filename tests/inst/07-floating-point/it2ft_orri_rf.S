@@ it2ft_orri_rf — it2ft（orri, opc 0x44）
@@ 大类：07-floating-point（`spec/SimRISC-07`）；册目录 `tests/inst/07-floating-point/`
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐检查点把实测 8 字节写进结果缓冲并逐字节打印 ⇒ 三方比较的是字节流；标志与结果共用一个点号
@@ 期望值由独立参考模型（精确有理数 + 手写 round-and-pack，见证据脚本）按 `SimRISC-07` 现算，不手写
@@ 转换族（§1）：immu6 三套语义（六档 one-hot / SBZ / 复制个数）互斥。
@@ 浮点→整数：有限且取整在范围内 ⇒ inexact 置 NX；NaN/Inf/越界 ⇒ 饱和（按精确值符号取 max/min；NaN 取 max）并置 NV，不置 NX。
@@ 整数→浮点：精度损失 ⇒ NX；本任务的值域不产生 OF/UF（2^64 < ft_max、整数 ≥ 1）。
@@ 链接布局：`tests/inst/07-floating-point/inst-tiny-fp.lds`（段址见宏层 `__FP_LAYOUT` 分支）

	.equ	__FP_LAYOUT, 1
	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/07-floating-point/07-floating-point.inc"

	__TEST_BEGIN
	@@ 规范编码字：dst=rf5 / src=rd6 / immu6=0x01，3 → 3.0（精确）
	TEST_FPCVT_ENC_RF	1, ft, 0x44D05181, rf5, rd6, 0x0000000000000003, 0x0000000040400000, 0x00
	@@ 字段边界：dst=rf63 / src=rd62
	TEST_FPCVT_ENC_RF	2, ft, 0x44D3FF81, rf63, rd62, 0x0000000000000001, 0x000000003F800000, 0x00
	@@ 0 → +0（精确）
	TEST_FPCVT_I2F	3, ft, it2ft, rf5, rd6, 0x0000000000000000, 0x01, 0, 0x0000000000000000, 0x00
	@@ 1 → 1.0（精确）
	TEST_FPCVT_I2F	4, ft, it2ft, rf5, rd6, 0x0000000000000001, 0x01, 0, 0x000000003F800000, 0x00
	@@ 2^20 一类的精确值 → 不置标志
	TEST_FPCVT_I2F	5, ft, it2ft, rf5, rd6, 0x0000000000100000, 0x01, 0, 0x0000000049800000, 0x00
	@@ 16777217 在 RNE 下舍入 + NX（平局/截断点）
	TEST_FPCVT_I2F	6, ft, it2ft, rf5, rd6, 0x0000000001000001, 0x01, 0, 0x000000004B800000, 0x10
	@@ 16777217 在 RTZ 下舍入 + NX（平局/截断点）
	TEST_FPCVT_I2F	7, ft, it2ft, rf5, rd6, 0x0000000001000001, 0x04, 0, 0x000000004B800000, 0x10
	@@ 16777217 在 RUP 下舍入 + NX（平局/截断点）
	TEST_FPCVT_I2F	8, ft, it2ft, rf5, rd6, 0x0000000001000001, 0x08, 0, 0x000000004B800001, 0x10
	@@ 16777217 在 RDN 下舍入 + NX（平局/截断点）
	TEST_FPCVT_I2F	9, ft, it2ft, rf5, rd6, 0x0000000001000001, 0x10, 0, 0x000000004B800000, 0x10
	@@ 16777217 在 RNA 下平局远离 0 + NX
	TEST_FPCVT_I2F	10, ft, it2ft, rf5, rd6, 0x0000000001000001, 0x02, 0, 0x000000004B800001, 0x10
	@@ 动态档 0x20 读 rf0=RTZ → 截断 + NX
	TEST_FPCVT_I2F	11, ft, it2ft, rf5, rd6, 0x0000000001000001, 0x20, 1, 0x000000004B800000, 0x10
	@@ 静态档 RNE 不受 rf0=RDN 影响（仍就近取偶）
	TEST_FPCVT_I2F	12, ft, it2ft, rf5, rd6, 0x0000000001000001, 0x01, 2, 0x000000004B800000, 0x10
	@@ 源类型最大值 → 舍入 + NX
	TEST_FPCVT_I2F	13, ft, it2ft, rf5, rd6, 0x000000007FFFFFFF, 0x01, 0, 0x000000004F000000, 0x10
	@@ 源类型最小值 → 精确（2 的幂）
	TEST_FPCVT_I2F	14, ft, it2ft, rf5, rd6, 0xFFFFFFFF80000000, 0x01, 0, 0x00000000CF000000, 0x00
	@@ 动态档 + rf0=RUP：0 → +0（精确）
	TEST_FPCVT_I2F	15, ft, it2ft, rf5, rd6, 0x0000000000000000, 0x20, 3, 0x0000000000000000, 0x00
	@@ 源/目的同号（rf6 ← rd6，不同寄存器组）
	TEST_FPCVT_I2F	16, ft, it2ft, rf6, rd6, 0x0000000000000005, 0x01, 0, 0x0000000040A00000, 0x00
	@@ 窗口顶端同号（rf63 ← rd63）
	TEST_FPCVT_I2F	17, ft, it2ft, rf63, rd63, 0x000000000000003F, 0x01, 0, 0x00000000427C0000, 0x00
	@@ legality：目的 rf0 ⇒ ILLI（dst_rf0）
	TEST_FAULT_FP	18, ILLI, 0x44D00181
	@@ legality：immu6=0 非六档 ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	19, ILLI, 0x44D05180
	@@ legality：immu6=0x03 非 one-hot ⇒ ILLI（encode_onehot）
	TEST_FAULT_FP	20, ILLI, 0x44D05183

	__TEST_END

	__TEST_SECTIONS
