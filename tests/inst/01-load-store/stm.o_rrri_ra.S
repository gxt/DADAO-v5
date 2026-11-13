@@ stm.o_rrri_ra.S — stm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x3D）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.o_rrri_ra　形式：rrri　opc：0x3D　mask：0xFF000000
@@ 语义：mem64[EA + 8i] ← 源 i；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：ra0 作源合法（读出 0/当前指令地址）；overlap 不适用（范围在 RA、基址在 RB、索引在 RD ⇒ 天然不相交）；immu6=0 ⇒ ILLI；raHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 8 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：链例 8 + 故障例 7（故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.o, ra, {ra1:ra2}, rb4, MSTORE, rd19, 0x000, MDATA_O + 0x000, 0x0102030405060708, 0x0102030405060709

	@@ semantic：count=3
	TEST_STM         2, stm.o, ra, {ra5:ra7}, rb4, MSTORE, rd19, 0x020, MDATA_O + 0x010, 0x010203040506070A, 0x010203040506070B, 0x010203040506070C

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_STM         3, stm.o, ra, {ra8:ra15}, rb4, MSTORE, rd19, 0x048, MDATA_O + 0x020, 0x010203040506070C, 0x010203040506070D, 0x010203040506070E, 0x010203040506070F, 0x0102030405060710, 0x0102030405060711, 0x0102030405060712, 0x0102030405060713

	@@ 保持区：存储区左侧拍保持不变
	__CHECK_MEM         4, MSTORE, 0x040, 0xC0DE0000000000A8

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         5, stm.o, ra, {ra5:ra6}, rb4, MSTORE + 0x898, rd19, -0x800, MDATA_O + 0x050, 0x0102030405060712, 0x0102030405060713

	@@ semantic：8 个元素的大组存储
	TEST_STM         6, stm.o, ra, {ra24:ra31}, rb4, MSTORE, rd19, 0x0B8, MDATA_O + 0x068, 0x0102030405060715, 0x0102030405060716, 0x0102030405060717, 0x0102030405060718, 0x0102030405060719, 0x010203040506071A, 0x010203040506071B, 0x010203040506071C

	@@ boundary：SRAM 尾拍（0xffffff7ffff8）可写，读写逐字节相等
	LOAD_ADDR rb28, MDATA_O + 0x090
	ldm.o	{ra5:ra5}, [rb28, rd0]
	__LI    rd19, 0x000
	LOAD_ADDR rb4, 0xFFFFFF7FFFF8
	stm.o	{ra5:ra5}, [rb4, rd19]
	LOAD_ADDR rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         7, rd21, 0x010203040506071A

	@@ encoding：组首高位单元素
	TEST_STM         8, stm.o, ra, {ra40:ra40}, rb4, MSTORE, rd19, 0x108, MDATA_O + 0x058, 0x0102030405060713

	@@ overlap：**不适用** —— 范围在 RA bank，基址恒在 RB、索引恒在 RD ⇒ 结构上不可能相交（正常例见上）

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC         9, ILLI, 0x3D143040, rb3, MDATA_O, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        10, ILLI, 0x3DDC304A, rb3, MDATA_O, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        11, ILLI, 0x3DFC3042, rb3, MDATA_O, rd19, 0x000
	@@ 首址未按 8 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        12, stm.o, {ra5:ra6}, MALIGN, rb3, MDATA_O, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        13, stm.o, {ra5:ra6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        14, stm.o, {ra5:ra6}, CFXMEM, rb3, 0xFFFFFF7FFFF8, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        15, stm.o, {ra5:ra6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
