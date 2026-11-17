@@ stm.w_rrri_rd.S — stm.w {rdHA:rdHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x31）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.w_rrri_rd　形式：rrri　opc：0x31　mask：0xFF000000
@@ 语义：mem16[EA + 2i] ← 源 i 低 16 位；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rd0 作源合法（读出 0/当前指令地址）；允许索引 rdHC 落在源范围内（`stm` 只读，行为确定，不触发 ILLI）；immu6=0 ⇒ ILLI；rdHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 2 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：boundary 3 / rb0 3（链例 18 + 故障例 7；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.w, rd, {rd1:rd2}, rb4, MSTORE, rd19, 0x000, MDATA_W + 0x000, 0x80008001000000A0

	@@ semantic：count=3
	TEST_STM         2, stm.w, rd, {rd5:rd7}, rb4, MSTORE, rd19, 0x018, MDATA_W + 0x010, 0x80088009800A00A3

	@@ semantic：count=16（多拍，元素不跨 8 B 拍）
	TEST_STM         3, stm.w, rd, {rd24:rd39}, rb4, MSTORE, rd19, 0x030, MDATA_W + 0x020, 0x8010801180128013, 0x8014801580168017, 0x80188019801A801B, 0x801C801D801E801F

	@@ 保持区：存储区左侧拍保持不变
	__CHECK_MEM         4, MSTORE, 0x028, 0xC0DE0000000000A5

	@@ boundary：EA 在拍内（+2）—— 首拍前 2 字节保持
	TEST_STM         5, stm.w, rd, {rd5:rd7}, rb4, MSTORE, rd19, 0x062, MDATA_W + 0x058, 0xC0DE802C802D802E

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         6, stm.w, rd, {rd5:rd6}, rb4, MSTORE + 0x878, rd19, -0x800, MDATA_W + 0x050, 0x80288029000000AF

	@@ boundary：SRAM 尾拍（0xffffff7ffff8）可写，读写逐字节相等
	LOAD_ADDR rb28, MDATA_W + 0x090
	ldm.uw	{rd5:rd8}, [rb28, rd0]
	set.rd    rd19, 0x000
	LOAD_ADDR rb4, 0xFFFFFF7FFFF8
	stm.w	{rd5:rd8}, [rb4, rd19]
	LOAD_ADDR rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         7, rd21, 0x80488049804A804B

	@@ overlap：索引 rd19 落在源组内（`stm` 允许重叠）⇒ 正常执行，行为确定
	LOAD_ADDR rb28, MDATA_W + 0x0A0
	ldm.uw	{rd17:rd21}, [rb28, rd0]
	set.rd    rd19, 0x090
	LOAD_ADDR rb4, MSTORE
	stm.w	{rd17:rd21}, [rb4, rd19]

	@@ overlap：`stm` 只读，源组 rd17..rd21 事后仍是原值
	LOAD_ADDR rb28, MDUMP + 0x100
	stm.w	{rd17:rd21}, [rb28, rd0]
	__CHECK_MEM         8, MDUMP, 0x100, 0x8050805100908053
	__CHECK_MEM         9, MDUMP, 0x108, 0x8054000000000000
	__CHECK_MEM        10, MSTORE, 0x090, 0x8050805100908053
	__CHECK_MEM        11, MSTORE, 0x098, 0x80540000000000B3

	@@ legality：stm 允许 rd0 作源（读出 0），不触发 ILLI
	LOAD_ADDR rb28, MDATA_W + 0x078
	ldm.uw	{rd1:rd2}, [rb28, rd0]
	set.rd    rd19, 0x000
	LOAD_ADDR rb4, MSTORE + 0x0B0
	stm.w	{rd0:rd2}, [rb4, rd19]
	__CHECK_MEM        12, MSTORE, 0x0B0, 0x0000803C803D00B6


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 beat）----
	TEST_STM  13, stm.w,   rd, {rd5:rd5}, rb4, MSTORE, rd19, 0x1C6, TEST_DATA + 0x028, 0xC0DE000000007FFF
	TEST_STM  14, stm.w,   rd, {rd5:rd5}, rb4, MSTORE, rd19, 0x1CE, TEST_DATA + 0x020, 0xC0DE000000008000
	TEST_STM  15, stm.w,   rd, {rd5:rd5}, rb4, MSTORE, rd19, 0x1D6, TEST_DATA + 0x088, 0xC0DE00000000FFFF
	@@   ^ 三条各写 MSTORE + 0x1C0/0x1C8/0x1D0 一拍（值 = TEST_DATA + 0x028/0x020/0x088 的 16 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	LOAD_ADDR rb28, TEST_DATA + 0x088
	ldm.uw   {rd5:rd5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0n_pre]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零
	.org	0x201C
__rb0n_pre:
	set.rd	rd19, -0x01A		@@ 偏移：EA = 0x2000 + 6
	.org	0x2020
__rb0n:
	stm.w    {rd5:rd5}, [rb0, rd19]	@@ 被测 @0x2020：EA = 0x2000 + 6
	__CHECK_MEM 16, (ENTRY + 0x2000), 0, 0x000000000000FFFF	@@ 负档槽（零）只被写低 16 位
__rb0n_ck:
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	stm.w    {rd5:rd5}, [rb0, rd0]	@@ 被测 @0x20C0：EA = 自身指令地址（只覆写本指令首 2 B）
	aip.si	rb12, 0
	ld.uw	rd21, [rb12, -0x004]		@@ 独立通路：0x20C4 − 4 = 0x20C0
	__CHECK_RD 17, rd21, 0x0000000000001111
__rb0z_ck:
	LOAD_ADDR rb28, TEST_DATA + 0x088
	ldm.uw   {rd5:rd5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	LOAD_ADDR rb26, (MSTORE + 0x1C0 + 6 - 8)
	aip.si	rb25, 0			@@ rb25 = ENTRY+0x2180
	sub.o	rd19, rb26, rb25
	stm.w    {rd5:rd5}, [rb0, rd19]	@@ 被测 @0x2188：EA = MSTORE + 0x1C0 + 6
	__CHECK_MEM 18, (MSTORE + 0x1C0), 0, 0xC0DE00000000FFFF
__rb0p_ck:
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        19, ILLI, 0x31143040, rb3, MDATA_W, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        20, ILLI, 0x31DC304A, rb3, MDATA_W, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        21, ILLI, 0x31FC3042, rb3, MDATA_W, rd19, 0x000
	@@ 首址未按 2 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        22, stm.w, {rd5:rd6}, MALIGN, rb3, MDATA_W, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        23, stm.w, {rd5:rd6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        24, stm.w, {rd5:rd6}, CFXMEM, rb3, 0xFFFFFF7FFFFE, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        25, stm.w, {rd5:rd6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
