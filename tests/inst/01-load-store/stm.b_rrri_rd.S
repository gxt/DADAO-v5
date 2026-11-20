@@ stm.b_rrri_rd.S — stm.b {rdHA:rdHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x30）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.b_rrri_rd　形式：rrri　opc：0x30　mask：0xFF000000
@@ 语义：mem8[EA + i] ← 源 i 低 8 位；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rd0 作源合法（读出 0/当前指令地址）；允许索引 rdHC 落在源范围内（`stm` 只读，行为确定，不触发 ILLI）；immu6=0 ⇒ ILLI；rdHA+immu6>64 ⇒ ILLI（不环绕、不截断）；无对齐要求（字节访问）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：boundary 3 / rb0 3（链例 18 + 故障例 6；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

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
	set.rb rb28, MDATA_B + 0x090
	ldm.ub	{rd5:rd12}, [rb28, rd0]
	set.rd    rd19, 0x000
	set.rb rb4, 0xFFFFFF7FFFF8
	stm.b	{rd5:rd12}, [rb4, rd19]
	set.rb rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         9, rd21, 0x9091929394959697

	@@ overlap：索引 rd19 落在源组内（`stm` 允许重叠）⇒ 正常执行，行为确定
	set.rb rb28, MDATA_B + 0x0A0
	ldm.ub	{rd17:rd21}, [rb28, rd0]
	set.rd    rd19, 0x0A0
	set.rb rb4, MSTORE
	stm.b	{rd17:rd21}, [rb4, rd19]

	@@ overlap：`stm` 只读，源组 rd17..rd21 事后仍是原值
	set.rb rb28, MDUMP + 0x100
	stm.b	{rd17:rd21}, [rb28, rd0]
	__CHECK_MEM        10, MDUMP, 0x100, 0xA0A1A0A3A4000000
	__CHECK_MEM        11, MSTORE, 0x0A0, 0xA0A1A0A3A40000B4

	@@ legality：stm 允许 rd0 作源（读出 0），不触发 ILLI
	set.rb rb28, MDATA_B + 0x078
	ldm.ub	{rd1:rd2}, [rb28, rd0]
	set.rd    rd19, 0x000
	set.rb rb4, MSTORE + 0x0B8
	stm.b	{rd0:rd2}, [rb4, rd19]
	__CHECK_MEM        12, MSTORE, 0x0B8, 0x00B8B900000000B7


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 beat）----
	TEST_STM  13, stm.b,   rd, {rd5:rd5}, rb4, MSTORE, rd19, 0x1C7, TEST_DATA + 0x028, 0xC0DE00000000007F
	TEST_STM  14, stm.b,   rd, {rd5:rd5}, rb4, MSTORE, rd19, 0x1CF, TEST_DATA + 0x020, 0xC0DE000000000080
	TEST_STM  15, stm.b,   rd, {rd5:rd5}, rb4, MSTORE, rd19, 0x1D7, TEST_DATA + 0x088, 0xC0DE0000000000FF
	@@   ^ 三条各写 MSTORE + 0x1C0/0x1C8/0x1D0 一拍（值 = TEST_DATA + 0x028/0x020/0x088 的 8 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.rb rb28, TEST_DATA + 0x088
	ldm.ub   {rd5:rd5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0n_pre]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零
	.org	0x201C
__rb0n_pre:
	set.rd	rd19, -0x019		@@ 偏移：EA = 0x2000 + 7
	.org	0x2020
__rb0n:
	stm.b    {rd5:rd5}, [rb0, rd19]	@@ 被测 @0x2020：EA = 0x2000 + 7
	__CHECK_MEM 16, (ENTRY + 0x2000), 0, 0x00000000000000FF	@@ 负档槽（零）只被写低 8 位
__rb0n_ck:
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	stm.b    {rd5:rd5}, [rb0, rd0]	@@ 被测 @0x20C0：EA = 自身指令地址（只覆写本指令首 1 B）
	aip.si	rb12, 0
	ld.ub	rd21, [rb12, -0x004]		@@ 独立通路：0x20C4 − 4 = 0x20C0
	__CHECK_RD 17, rd21, 0x0000000000000011
__rb0z_ck:
	set.rb rb28, TEST_DATA + 0x088
	ldm.ub   {rd5:rd5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	set.rb rb26, (MSTORE + 0x1C0 + 7 - 8)
	aip.si	rb25, 0			@@ rb25 = ENTRY+0x2180
	sub.o	rd19, rb26, rb25
	stm.b    {rd5:rd5}, [rb0, rd19]	@@ 被测 @0x2188：EA = MSTORE + 0x1C0 + 7
	__CHECK_MEM 18, (MSTORE + 0x1C0), 0, 0xC0DE0000000000FF
__rb0p_ck:
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        19, ILLI, 0x30143040, rb3, MDATA_B, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        20, ILLI, 0x30DC304A, rb3, MDATA_B, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        21, ILLI, 0x30FC3042, rb3, MDATA_B, rd19, 0x000
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        22, stm.b, {rd5:rd6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        23, stm.b, {rd5:rd6}, CFXMEM, rb3, 0xFFFFFF7FFFFF, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        24, stm.b, {rd5:rd6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
