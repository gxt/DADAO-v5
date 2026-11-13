@@ stm.b_rrri_rd.S — stm.b {rdHA:rdHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x30）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.b_rrri_rd　形式：rrri　opc：0x30　mask：0xFF000000
@@ 语义：mem8[EA + i] ← 源 i 低 8 位；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rd0 作源合法（读出 0/当前指令地址）；允许索引 rdHC 落在源范围内（`stm` 只读，行为确定，不触发 ILLI）；immu6=0 ⇒ ILLI；rdHA+immu6>64 ⇒ ILLI（不环绕、不截断）；无对齐要求（字节访问）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：链例 11 + 故障例 6（故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.b, rd, {rd1:rd2}, rb4, MSTORE, rd19, 0x000, MDATA_B + 0x000, 0x80810000000000A0

	@@ semantic：count=3
	TEST_STM         2, stm.b, rd, {rd5:rd7}, rb4, MSTORE, rd19, 0x018, MDATA_B + 0x010, 0x90919200000000A3

	@@ semantic：count=16（多拍，元素不跨 8 B 拍）
	TEST_STM         3, stm.b, rd, {rd24:rd39}, rb4, MSTORE, rd19, 0x030, MDATA_B + 0x020, 0xA0A1A2A3A4A5A6A7, 0xA8A9AAABACADAEAF

	@@ 保持区：存储区左侧拍保持不变
	__CHECK_MEM         4, MSTORE, 0x028, 0xC0DE0000000000A5

	@@ boundary：9 元素跨 2 拍，第二拍只开 1 lane（其余字节保持）
	TEST_STM         5, stm.b, rd, {rd5:rd13}, rb4, MSTORE, rd19, 0x050, MDATA_B + 0x040, 0x8081828384858687, 0x88DE0000000000AB

	@@ 保持区：第二拍之后的拍保持不变
	__CHECK_MEM         6, MSTORE, 0x060, 0xC0DE0000000000AC

	@@ boundary：EA 在拍内（+3）—— 首拍前 3 字节保持
	TEST_STM         7, stm.b, rd, {rd5:rd9}, rb4, MSTORE, rd19, 0x073, MDATA_B + 0x058, 0xC0DE0098999A9B9C

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         8, stm.b, rd, {rd5:rd6}, rb4, MSTORE + 0x888, rd19, -0x800, MDATA_B + 0x050, 0x90910000000000B1

	@@ boundary：SRAM 尾拍（0xffffff7ffff8）可写，读写逐字节相等
	LOAD_ADDR rb28, MDATA_B + 0x090
	ldm.ub	{rd5:rd12}, [rb28, rd0]
	__LI    rd19, 0x000
	LOAD_ADDR rb4, 0xFFFFFF7FFFF8
	stm.b	{rd5:rd12}, [rb4, rd19]
	LOAD_ADDR rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         9, rd21, 0x9091929394959697

	@@ overlap：索引 rd19 落在源组内（`stm` 允许重叠）⇒ 正常执行，行为确定
	LOAD_ADDR rb28, MDATA_B + 0x0A0
	ldm.ub	{rd17:rd21}, [rb28, rd0]
	__LI    rd19, 0x0A0
	LOAD_ADDR rb4, MSTORE
	stm.b	{rd17:rd21}, [rb4, rd19]

	@@ overlap：`stm` 只读，源组 rd17..rd21 事后仍是原值
	LOAD_ADDR rb28, MDUMP + 0x100
	stm.b	{rd17:rd21}, [rb28, rd0]
	__CHECK_MEM        10, MDUMP, 0x100, 0xA0A1A0A3A4000000
	__CHECK_MEM        11, MSTORE, 0x0A0, 0xA0A1A0A3A40000B4

	@@ legality：stm 允许 rd0 作源（读出 0），不触发 ILLI
	LOAD_ADDR rb28, MDATA_B + 0x078
	ldm.ub	{rd1:rd2}, [rb28, rd0]
	__LI    rd19, 0x000
	LOAD_ADDR rb4, MSTORE + 0x0B8
	stm.b	{rd0:rd2}, [rb4, rd19]
	__CHECK_MEM        12, MSTORE, 0x0B8, 0x00B8B900000000B7

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        13, ILLI, 0x30143040, rb3, MDATA_B, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x30DC304A, rb3, MDATA_B, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        15, ILLI, 0x30FC3042, rb3, MDATA_B, rd19, 0x000
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        16, stm.b, {rd5:rd6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        17, stm.b, {rd5:rd6}, CFXMEM, rb3, 0xFFFFFF7FFFFF, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        18, stm.b, {rd5:rd6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
