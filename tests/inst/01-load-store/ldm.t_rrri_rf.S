@@ ldm.t_rrri_rf.S — ldm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x2E）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ldm.t_rrri_rf　形式：rrri　opc：0x2E　mask：0xFF000000
@@ 语义：目的 i ← mem32[EA + 4i]（写 RF 低 32 位，高 32 位不变）；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rf0 作目的合法（按 FCSR 写掩码）；overlap 不适用（范围在 RF、基址在 RB、索引在 RD ⇒ 天然不相交）；immu6=0 ⇒ ILLI；rfHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 4 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：链例 11 + 故障例 7（故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ encoding：bank 最高寄存器作组首（count=1，rf 边界）
	TEST_LDM         1, ldm.t, {rf63:rf63}, rb3, MDATA_T + 0x000, rd19, 0x000, MDUMP + 0x000, 1, 0x8000000000000000

	@@ encoding：bank 低端起始，count=2
	TEST_LDM         2, ldm.t, {rf1:rf2}, rb3, MDATA_T + 0x008, rd19, 0x000, MDUMP + 0x008, 1, 0x8000000280000003

	@@ semantic：count=3 三个连续元素
	TEST_LDM         3, ldm.t, {rf5:rf7}, rb3, MDATA_T + 0x010, rd19, 0x000, MDUMP + 0x010, 2, 0x8000000480000005, 0x8000000600000000

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_LDM         4, ldm.t, {rf8:rf15}, rb3, MDATA_T + 0x020, rd19, 0x000, MDUMP + 0x020, 4, 0x8000000880000009, 0x8000000A8000000B, 0x8000000C8000000D, 0x8000000E8000000F

	@@ semantic：宽度/符号扩展逐元素核对（零扩展）
	LOAD_ADDR rb3, MDATA_T + 0x030
	__LI    rd19, 0x000
	ldm.t	{rf5:rf7}, [rb3, rd19]
	rf2rd	{rd21:rd21}, {rf5:rf5}
	ext.uo	rd21, rd21, 31
	__CHECK_RD         5, rd21, 0x000000008000000C
	rf2rd	{rd21:rd21}, {rf7:rf7}
	ext.uo	rd21, rd21, 31
	__CHECK_RD         6, rd21, 0x000000008000000E

	@@ semantic：同一组首、不同偏移（偏移来自 rd19）
	TEST_LDM         7, ldm.t, {rf5:rf6}, rb3, MDATA_T + 0x038, rd19, 0x000, MDUMP + 0x040, 1, 0x8000000E8000000F

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_LDM         8, ldm.t, {rf5:rf6}, rb3, MDATA_T + 0x840, rd19, -0x800, MDUMP + 0x048, 1, 0x8000001080000011

	@@ boundary：组首+count == 64 恰好合法（不环绕、不截断）
	TEST_LDM         9, ldm.t, {rf62:rf63}, rb3, MDATA_T + 0x048, rd19, 0x000, MDUMP + 0x050, 1, 0x8000001280000013

	@@ semantic：大偏移（0x80）仍按元素宽度递增
	TEST_LDM        10, ldm.t, {rf5:rf7}, rb3, MDATA_T + 0x080, rd19, 0x000, MDUMP + 0x058, 2, 0x8000002080000021, 0x8000002200000000

	@@ boundary：大组（16 个元素）跨多拍
	TEST_LDM        11, ldm.t, {rf32:rf47}, rb3, MDATA_T + 0x058, rd19, 0x000, MDUMP + 0x068, 8, 0x8000001680000017, 0x8000001880000019, 0x8000001A8000001B, 0x8000001C8000001D, 0x8000001E8000001F, 0x8000002080000021, 0x8000002280000023, 0x8000002480000025

	@@ overlap：**不适用** —— 范围在 RF bank，基址恒在 RB、索引恒在 RD ⇒ 结构上不可能相交

	@@ overlap：同一 RF 连装两次，后到者生效（只比低 32 位）
	LOAD_ADDR rb3, MDATA_T + 0x090
	__LI    rd19, 0x000
	ldm.t	{rf9:rf9}, [rb3, rd19]
	LOAD_ADDR rb3, MDATA_T + 0x018
	ldm.t	{rf9:rf9}, [rb3, rd19]
	rf2rd	{rd21:rd21}, {rf9:rf9}
	ext.uo	rd21, rd21, 31
	__CHECK_RD        12, rd21, 0x0000000080000006

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        13, ILLI, 0x2E143040, rb3, MDATA_T, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x2EDC304A, rb3, MDATA_T, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        15, ILLI, 0x2EFC3042, rb3, MDATA_T, rd19, 0x000
	@@ 首址未按 4 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        16, ldm.t, {rf5:rf6}, MALIGN, rb3, MDATA_T, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        17, ldm.t, {rf5:rf6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        18, ldm.t, {rf5:rf6}, CFXMEM, rb3, 0xFFFFFF7FFFFC, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        19, ldm.t, {rf5:rf6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
