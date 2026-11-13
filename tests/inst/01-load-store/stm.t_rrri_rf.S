@@ stm.t_rrri_rf.S — stm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x2F）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.t_rrri_rf　形式：rrri　opc：0x2F　mask：0xFF000000
@@ 语义：mem32[EA + 4i] ← 源 i 低 32 位；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rf0 作源合法（读出 0/当前指令地址）；overlap 不适用（范围在 RF、基址在 RB、索引在 RD ⇒ 天然不相交）；immu6=0 ⇒ ILLI；rfHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 4 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：链例 8 + 故障例 8（故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.t, rf, {rf1:rf2}, rb4, MSTORE, rd19, 0x000, MDATA_T + 0x000, 0x8000000080000001

	@@ semantic：count=3
	TEST_STM         2, stm.t, rf, {rf5:rf7}, rb4, MSTORE, rd19, 0x018, MDATA_T + 0x010, 0x8000000480000005, 0x80000006000000A4

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_STM         3, stm.t, rf, {rf8:rf15}, rb4, MSTORE, rd19, 0x038, MDATA_T + 0x020, 0x8000000880000009, 0x8000000A8000000B, 0x8000000C8000000D, 0x8000000E8000000F

	@@ 保持区：存储区左侧拍保持不变
	__CHECK_MEM         4, MSTORE, 0x030, 0xC0DE0000000000A6

	@@ boundary：EA 在拍内（+4）—— 首拍前半保持
	TEST_STM         5, stm.t, rf, {rf5:rf6}, rb4, MSTORE, rd19, 0x06C, MDATA_T + 0x058, 0xC0DE000080000016, 0x80000017000000AE

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         6, stm.t, rf, {rf5:rf6}, rb4, MSTORE + 0x888, rd19, -0x800, MDATA_T + 0x050, 0x8000001480000015

	@@ boundary：SRAM 尾拍（0xffffff7ffff8）可写，读写逐字节相等
	LOAD_ADDR rb28, MDATA_T + 0x090
	ldm.t	{rf5:rf6}, [rb28, rd0]
	__LI    rd19, 0x000
	LOAD_ADDR rb4, 0xFFFFFF7FFFF8
	stm.t	{rf5:rf6}, [rb4, rd19]
	LOAD_ADDR rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         7, rd21, 0x8000002480000025

	@@ encoding：组首高位单元素
	TEST_STM         8, stm.t, rf, {rf40:rf40}, rb4, MSTORE, rd19, 0x0A0, MDATA_T + 0x058, 0x80000016000000B4

	@@ overlap：**不适用** —— 范围在 RF bank，基址恒在 RB、索引恒在 RD ⇒ 结构上不可能相交（正常例见上）

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC         9, ILLI, 0x2F143040, rb3, MDATA_T, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        10, ILLI, 0x2FDC304A, rb3, MDATA_T, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        11, ILLI, 0x2FFC3042, rb3, MDATA_T, rd19, 0x000
	@@ 首址未按 4 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        12, stm.t, {rf5:rf6}, MALIGN, rb3, MDATA_T, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        13, stm.t, {rf5:rf6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        14, stm.t, {rf5:rf6}, CFXMEM, rb3, 0xFFFFFF7FFFFC, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        15, stm.t, {rf5:rf6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000
	@@ rf0 作源合法（读出 FCSR 的 qNaN），此处改测整段越出地址窗口 ⇒ CFXMEM
	TEST_FAULT_M        16, stm.t, {rf0:rf1}, CFXMEM, rb3, 0xFFFFFF7FFFFC, rd19, 0x000

	__TEST_SECTIONS
