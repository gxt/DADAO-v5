@@ stm.o_rrri_rf.S — stm.o {rfHA:rfHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x3F）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.o_rrri_rf　形式：rrri　opc：0x3F　mask：0xFF000000
@@ 语义：mem64[EA + 8i] ← 源 i；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rf0 作源合法（读出 0/当前指令地址）；overlap 不适用（范围在 RF、基址在 RB、索引在 RD ⇒ 天然不相交）；immu6=0 ⇒ ILLI；rfHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 8 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：boundary 3 / rb0 3（链例 14 + 故障例 8；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.o, rf, {rf1:rf2}, rb4, MSTORE, rd19, 0x000, MDATA_O + 0x000, 0x0102030405060708, 0x0102030405060709

	@@ semantic：count=3
	TEST_STM         2, stm.o, rf, {rf5:rf7}, rb4, MSTORE, rd19, 0x020, MDATA_O + 0x010, 0x010203040506070A, 0x010203040506070B, 0x010203040506070C

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_STM         3, stm.o, rf, {rf8:rf15}, rb4, MSTORE, rd19, 0x048, MDATA_O + 0x020, 0x010203040506070C, 0x010203040506070D, 0x010203040506070E, 0x010203040506070F, 0x0102030405060710, 0x0102030405060711, 0x0102030405060712, 0x0102030405060713

	@@ 保持区：存储区左侧拍保持不变
	__CHECK_MEM         4, MSTORE, 0x040, 0xC0DE0000000000A8

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         5, stm.o, rf, {rf5:rf6}, rb4, MSTORE + 0x898, rd19, -0x800, MDATA_O + 0x050, 0x0102030405060712, 0x0102030405060713

	@@ semantic：8 个元素的大组存储
	TEST_STM         6, stm.o, rf, {rf24:rf31}, rb4, MSTORE, rd19, 0x0B8, MDATA_O + 0x068, 0x0102030405060715, 0x0102030405060716, 0x0102030405060717, 0x0102030405060718, 0x0102030405060719, 0x010203040506071A, 0x010203040506071B, 0x010203040506071C

	@@ boundary：SRAM 尾拍（0xffffff7ffff8）可写，读写逐字节相等
	LOAD_ADDR rb28, MDATA_O + 0x090
	ldm.o	{rf5:rf5}, [rb28, rd0]
	set.rd    rd19, 0x000
	LOAD_ADDR rb4, 0xFFFFFF7FFFF8
	stm.o	{rf5:rf5}, [rb4, rd19]
	LOAD_ADDR rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         7, rd21, 0x010203040506071A

	@@ encoding：组首高位单元素
	TEST_STM         8, stm.o, rf, {rf40:rf40}, rb4, MSTORE, rd19, 0x108, MDATA_O + 0x058, 0x0102030405060713

	@@ overlap：**不适用** —— 范围在 RF bank，基址恒在 RB、索引恒在 RD ⇒ 结构上不可能相交（正常例见上）


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 beat）----
	TEST_STM   9, stm.o,   rf, {rf5:rf5}, rb4, MSTORE, rd19, 0x1C0, TEST_DATA + 0x028, 0x7FFFFFFFFFFFFFFF
	TEST_STM  10, stm.o,   rf, {rf5:rf5}, rb4, MSTORE, rd19, 0x1C8, TEST_DATA + 0x020, 0x8000000000000000
	TEST_STM  11, stm.o,   rf, {rf5:rf5}, rb4, MSTORE, rd19, 0x1D0, TEST_DATA + 0x088, 0xFFFFFFFFFFFFFFFF
	@@   ^ 三条各写 MSTORE + 0x1C0/0x1C8/0x1D0 一拍（值 = TEST_DATA + 0x028/0x020/0x088 的 64 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	LOAD_ADDR rb28, TEST_DATA + 0x088
	ldm.o    {rf5:rf5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0n_pre]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零
	.org	0x201C
__rb0n_pre:
	set.rd	rd19, -0x020		@@ 偏移：EA = 0x2000 + 0
	.org	0x2020
__rb0n:
	stm.o    {rf5:rf5}, [rb0, rd19]	@@ 被测 @0x2020：EA = 0x2000 + 0
	__CHECK_MEM 12, (ENTRY + 0x2000), 0, 0xFFFFFFFFFFFFFFFF	@@ 负档槽（零）只被写低 64 位
__rb0n_ck:
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	@@ 被测 @0x20D0：EA = 自身指令地址（宏内预读 8 B 拍、只改高 32 位后写回）
	__CHECK_RD_STM_IP 13, stm.o, rf5, rf
__rb0z_ck:
	LOAD_ADDR rb28, TEST_DATA + 0x088
	ldm.o    {rf5:rf5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	LOAD_ADDR rb26, (MSTORE + 0x1C0 + 0 - 8)
	aip.si	rb25, 0			@@ rb25 = ENTRY+0x2180
	sub.o	rd19, rb26, rb25
	stm.o    {rf5:rf5}, [rb0, rd19]	@@ 被测 @0x2188：EA = MSTORE + 0x1C0 + 0
	__CHECK_MEM 14, (MSTORE + 0x1C0), 0, 0xFFFFFFFFFFFFFFFF
__rb0p_ck:
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC         15, ILLI, 0x3F143040, rb3, MDATA_O, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        16, ILLI, 0x3FDC304A, rb3, MDATA_O, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        17, ILLI, 0x3FFC3042, rb3, MDATA_O, rd19, 0x000
	@@ 首址未按 8 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        18, stm.o, {rf5:rf6}, MALIGN, rb3, MDATA_O, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        19, stm.o, {rf5:rf6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        20, stm.o, {rf5:rf6}, CFXMEM, rb3, 0xFFFFFF7FFFF8, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        21, stm.o, {rf5:rf6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000
	@@ rf0 作源合法（读出 FCSR 的 qNaN），此处改测整段越出地址窗口 ⇒ CFXMEM
	TEST_FAULT_M        22, stm.o, {rf0:rf1}, CFXMEM, rb3, 0xFFFFFF7FFFF8, rd19, 0x000

	__TEST_SECTIONS
