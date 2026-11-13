@@ stm.o_rrri_rb.S — stm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x3B）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.o_rrri_rb　形式：rrri　opc：0x3B　mask：0xFF000000
@@ 语义：mem64[EA + 8i] ← 源 i；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rb0 作源合法（读出 0/当前指令地址）；允许基址 rbHB 落在源范围内（`stm` 只读，行为确定，不触发 ILLI）；immu6=0 ⇒ ILLI；rbHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 8 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：链例 8 + 故障例 7（故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.o, rb, {rb1:rb2}, rb4, MSTORE, rd19, 0x000, MDATA_O + 0x000, 0x0102030405060708, 0x0102030405060709

	@@ semantic：count=3
	TEST_STM         2, stm.o, rb, {rb5:rb7}, rb4, MSTORE, rd19, 0x020, MDATA_O + 0x010, 0x010203040506070A, 0x010203040506070B, 0x010203040506070C

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_STM         3, stm.o, rb, {rb8:rb15}, rb4, MSTORE, rd19, 0x048, MDATA_O + 0x020, 0x010203040506070C, 0x010203040506070D, 0x010203040506070E, 0x010203040506070F, 0x0102030405060710, 0x0102030405060711, 0x0102030405060712, 0x0102030405060713

	@@ 保持区：存储区左侧拍保持不变
	__CHECK_MEM         4, MSTORE, 0x040, 0xC0DE0000000000A8

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         5, stm.o, rb, {rb5:rb6}, rb4, MSTORE + 0x898, rd19, -0x800, MDATA_O + 0x050, 0x0102030405060712, 0x0102030405060713

	@@ boundary：SRAM 尾拍（0xffffff7ffff8）可写，读写逐字节相等
	LOAD_ADDR rb28, MDATA_O + 0x090
	ldm.o	{rb5:rb5}, [rb28, rd0]
	__LI    rd19, 0x000
	LOAD_ADDR rb4, 0xFFFFFF7FFFF8
	stm.o	{rb5:rb5}, [rb4, rd19]
	LOAD_ADDR rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         6, rd21, 0x010203040506071A

	@@ overlap：基址 rb3 落在源组内（`stm` 允许重叠）⇒ 正常执行，行为确定
	LOAD_ADDR rb28, MDATA_O + 0x0A8
	ldm.o	{rb1:rb5}, [rb28, rd0]
	__LI    rd19, 0x0B8
	LOAD_ADDR rb3, MSTORE
	stm.o	{rb1:rb5}, [rb3, rd19]

	@@ overlap：`stm` 只读，源组 rb1..rb5 事后仍是原值（含 rb3=MSTORE）
	LOAD_ADDR rb28, MDUMP + 0x100
	stm.o	{rb1:rb5}, [rb28, rd0]
	__CHECK_MEM         7, MDUMP, 0x100, 0x010203040506071D
	__CHECK_MEM         8, MDUMP, 0x108, 0x010203040506071E
	__CHECK_MEM         9, MDUMP, 0x110, 0x0000FFFFFF013A00
	__CHECK_MEM        10, MDUMP, 0x118, 0x0102030405060720
	__CHECK_MEM        11, MDUMP, 0x120, 0x0102030405060721
	__CHECK_MEM        12, MSTORE, 0x0B8, 0x010203040506071D
	__CHECK_MEM        13, MSTORE, 0x0C0, 0x010203040506071E
	__CHECK_MEM        14, MSTORE, 0x0C8, 0x0000FFFFFF013A00
	__CHECK_MEM        15, MSTORE, 0x0D0, 0x0102030405060720
	__CHECK_MEM        16, MSTORE, 0x0D8, 0x0102030405060721

	@@ encoding：组首高位单元素
	TEST_STM        17, stm.o, rb, {rb40:rb40}, rb4, MSTORE, rd19, 0x0F0, MDATA_O + 0x058, 0x0102030405060713

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        18, ILLI, 0x3B143040, rb3, MDATA_O, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        19, ILLI, 0x3BDC304A, rb3, MDATA_O, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        20, ILLI, 0x3BFC3042, rb3, MDATA_O, rd19, 0x000
	@@ 首址未按 8 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        21, stm.o, {rb5:rb6}, MALIGN, rb3, MDATA_O, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        22, stm.o, {rb5:rb6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        23, stm.o, {rb5:rb6}, CFXMEM, rb3, 0xFFFFFF7FFFF8, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        24, stm.o, {rb5:rb6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
