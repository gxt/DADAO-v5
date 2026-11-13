@@ ldm.o_rrri_ra.S — ldm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x3C）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ldm.o_rrri_ra　形式：rrri　opc：0x3C　mask：0xFF000000
@@ 语义：目的 i ← mem64[EA + 8i]；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：ra0 作目的合法（可读写）；overlap 不适用（范围在 RA、基址在 RB、索引在 RD ⇒ 天然不相交）；immu6=0 ⇒ ILLI；raHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 8 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：链例 11 + 故障例 7（故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ encoding：bank 最高寄存器作组首（count=1，ra 边界）
	TEST_LDM         1, ldm.o, {ra63:ra63}, rb3, MDATA_O + 0x000, rd19, 0x000, MDUMP + 0x000, 1, 0x0102030405060708

	@@ encoding：bank 低端起始，count=2
	TEST_LDM         2, ldm.o, {ra1:ra2}, rb3, MDATA_O + 0x008, rd19, 0x000, MDUMP + 0x008, 2, 0x0102030405060709, 0x010203040506070A

	@@ semantic：count=3 三个连续元素
	TEST_LDM         3, ldm.o, {ra5:ra7}, rb3, MDATA_O + 0x010, rd19, 0x000, MDUMP + 0x018, 3, 0x010203040506070A, 0x010203040506070B, 0x010203040506070C

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_LDM         4, ldm.o, {ra8:ra15}, rb3, MDATA_O + 0x020, rd19, 0x000, MDUMP + 0x030, 8, 0x010203040506070C, 0x010203040506070D, 0x010203040506070E, 0x010203040506070F, 0x0102030405060710, 0x0102030405060711, 0x0102030405060712, 0x0102030405060713

	@@ semantic：宽度/符号扩展逐元素核对（零扩展）
	LOAD_ADDR rb3, MDATA_O + 0x030
	__LI    rd19, 0x000
	ldm.o	{ra5:ra7}, [rb3, rd19]
	ra2rd	{rd21:rd21}, {ra5:ra5}
	__CHECK_RD         5, rd21, 0x010203040506070E
	ra2rd	{rd21:rd21}, {ra7:ra7}
	__CHECK_RD         6, rd21, 0x0102030405060710

	@@ semantic：同一组首、不同偏移（偏移来自 rd19）
	TEST_LDM         7, ldm.o, {ra5:ra6}, rb3, MDATA_O + 0x038, rd19, 0x000, MDUMP + 0x070, 2, 0x010203040506070F, 0x0102030405060710

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_LDM         8, ldm.o, {ra5:ra6}, rb3, MDATA_O + 0x840, rd19, -0x800, MDUMP + 0x080, 2, 0x0102030405060710, 0x0102030405060711

	@@ boundary：组首+count == 64 恰好合法（不环绕、不截断）
	TEST_LDM         9, ldm.o, {ra62:ra63}, rb3, MDATA_O + 0x048, rd19, 0x000, MDUMP + 0x090, 2, 0x0102030405060711, 0x0102030405060712

	@@ semantic：大偏移（0x80）仍按元素宽度递增
	TEST_LDM        10, ldm.o, {ra5:ra7}, rb3, MDATA_O + 0x080, rd19, 0x000, MDUMP + 0x0A0, 3, 0x0102030405060718, 0x0102030405060719, 0x010203040506071A

	@@ boundary：大组（16 个元素）跨多拍
	TEST_LDM        11, ldm.o, {ra32:ra47}, rb3, MDATA_O + 0x058, rd19, 0x000, MDUMP + 0x0B8, 16, 0x0102030405060713, 0x0102030405060714, 0x0102030405060715, 0x0102030405060716, 0x0102030405060717, 0x0102030405060718, 0x0102030405060719, 0x010203040506071A, 0x010203040506071B, 0x010203040506071C, 0x010203040506071D, 0x010203040506071E, 0x010203040506071F, 0x0102030405060720, 0x0102030405060721, 0x0102030405060722

	@@ overlap：**不适用** —— 范围在 RA bank，基址恒在 RB、索引恒在 RD ⇒ 结构上不可能相交

	@@ boundary：immu6=63（最大合法个数）整组装入 + 回写（MUNI 同值元素）
	LOAD_ADDR rb3, MUNI
	__LI    rd19, 0x000
	ldm.o	{ra1:ra63}, [rb3, rd19]
	LOAD_ADDR rb28, MSTORE
	stm.o	{ra1:ra63}, [rb28, rd0]
	__CHECK_MEM        12, MSTORE, 0x000, 0x0F1E2D3C4B5A6978
	__CHECK_MEM        13, MSTORE, 0x0F8, 0x0F1E2D3C4B5A6978
	__CHECK_MEM        14, MSTORE, 0x1F0, 0x0F1E2D3C4B5A6978
	ra2rd	{rd21:rd21}, {ra63:ra63}
	__CHECK_RD        15, rd21, 0x0F1E2D3C4B5A6978

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        16, ILLI, 0x3C143040, rb3, MDATA_O, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        17, ILLI, 0x3CDC304A, rb3, MDATA_O, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        18, ILLI, 0x3CFC3042, rb3, MDATA_O, rd19, 0x000
	@@ 首址未按 8 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        19, ldm.o, {ra5:ra6}, MALIGN, rb3, MDATA_O, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        20, ldm.o, {ra5:ra6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        21, ldm.o, {ra5:ra6}, CFXMEM, rb3, 0xFFFFFF7FFFF8, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        22, ldm.o, {ra5:ra6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
