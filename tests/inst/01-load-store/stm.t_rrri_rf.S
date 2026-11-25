@@ stm.t_rrri_rf.S — stm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x2F）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.t_rrri_rf　形式：rrri　opc：0x2F　mask：0xFF000000
@@ 语义：mem32[EA + 4i] ← 源 i 低 32 位；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 字节数据单元）
@@ 合法性：rf0 作源合法（读出完整 64 位 FCSR 值：`[33:32]` 舍入模式、`[4:0]` 标志、只读 qNaN 位；复位 `0x7FF800007FC00000`；本指令只存低 32 位）；overlap 不适用（范围在 RF、基址在 RB、索引在 RD ⇒ 天然不相交）；immu6=0 ⇒ ILLI；rfHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 4 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：boundary 3 / rb0 3（链例 18 + 故障例 8；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.t, rf, {rf1:rf2}, rb4, MSTORE, rd19, 0x000, MDATA_T + 0x000, 0x8000000080000001

	@@ semantic：count=3
	TEST_STM         2, stm.t, rf, {rf5:rf7}, rb4, MSTORE, rd19, 0x018, MDATA_T + 0x010, 0x8000000480000005, 0x80000006000000A4

	@@ semantic：count=8（多个数据单元，元素不跨 8 字节数据单元）
	TEST_STM         3, stm.t, rf, {rf8:rf15}, rb4, MSTORE, rd19, 0x038, MDATA_T + 0x020, 0x8000000880000009, 0x8000000A8000000B, 0x8000000C8000000D, 0x8000000E8000000F

	@@ 保持区：存储区左侧数据单元保持不变
	__CHECK_MEM         4, MSTORE, 0x030, 0xC0DE0000000000A6

	@@ boundary：EA 在数据单元内（+4）—— 首个数据单元前半保持
	TEST_STM         5, stm.t, rf, {rf5:rf6}, rb4, MSTORE, rd19, 0x06C, MDATA_T + 0x058, 0xC0DE000080000016, 0x80000017000000AE

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         6, stm.t, rf, {rf5:rf6}, rb4, MSTORE + 0x888, rd19, -0x800, MDATA_T + 0x050, 0x8000001480000015

	@@ boundary：SRAM 尾部数据单元（0xffffff7ffff8）可写，读写逐字节相等
	set.rb rb28, MDATA_T + 0x090
	ldm.t	{rf5:rf6}, [rb28, rd0]
	set.rd    rd19, 0x000
	set.rb rb4, 0xFFFFFF7FFFF8
	stm.t	{rf5:rf6}, [rb4, rd19]
	set.rb rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         7, rd21, 0x8000002480000025

	@@ encoding：组首高位单元素
	TEST_STM         8, stm.t, rf, {rf40:rf40}, rb4, MSTORE, rd19, 0x0A0, MDATA_T + 0x058, 0x80000016000000B4

	@@ overlap：**不适用** —— 范围在 RF bank，基址恒在 RB、索引恒在 RD ⇒ 结构上不可能相交（正常例见上）


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	TEST_STM   9, stm.t,   rf, {rf5:rf5}, rb4, MSTORE, rd19, 0x1C4, TEST_DATA + 0x028, 0xC0DE00007FFFFFFF
	TEST_STM  10, stm.t,   rf, {rf5:rf5}, rb4, MSTORE, rd19, 0x1CC, TEST_DATA + 0x020, 0xC0DE000080000000
	TEST_STM  11, stm.t,   rf, {rf5:rf5}, rb4, MSTORE, rd19, 0x1D4, TEST_DATA + 0x088, 0xC0DE0000FFFFFFFF
	@@   ^ 三条各在 MSTORE + 0x1C0/0x1C8/0x1D0 写一个数据单元（值 = TEST_DATA + 0x028/0x020/0x088 的 32 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.rb rb28, TEST_DATA + 0x088
	ldm.t    {rf5:rf5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0n_pre]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零
	.org	0x201C
__rb0n_pre:
	set.rd	rd19, -0x01C		@@ 偏移：EA = 0x2000 + 4
	.org	0x2020
__rb0n:
	stm.t    {rf5:rf5}, [rb0, rd19]	@@ 被测 @0x2020：EA = 0x2000 + 4
	__CHECK_MEM 12, (ENTRY + 0x2000), 0, 0x00000000FFFFFFFF	@@ 负档槽（零）只被写低 32 位
__rb0n_ck:
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	stm.t    {rf5:rf5}, [rb0, rd0]	@@ 被测 @0x20C0：EA = 自身指令地址（只覆写本指令首 4 B）
	aip.si	rb12, 0
	ld.ut	rd21, [rb12, -0x004]		@@ 独立通路：0x20C4 − 4 = 0x20C0
	__CHECK_RD 13, rd21, 0x0000000011111111
__rb0z_ck:
	set.rb rb28, TEST_DATA + 0x088
	ldm.t    {rf5:rf5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	set.rb rb26, (MSTORE + 0x1C0 + 4 - 8)
	aip.si	rb25, 0			@@ rb25 = ENTRY+0x2180
	sub.o	rd19, rb26, rb25
	stm.t    {rf5:rf5}, [rb0, rd19]	@@ 被测 @0x2188：EA = MSTORE + 0x1C0 + 4
	__CHECK_MEM 14, (MSTORE + 0x1C0), 0, 0xC0DE0000FFFFFFFF
__rb0p_ck:

	@@ ---- boundary：immu6=63（最大合法个数）整组存储（MUNI 同值数据单元，63 个 32 位元素）----
	@@   源组 = RF 的 63 个元素（ldm.t 预装：只写低 32 位；数据单元内两元素 0x0F1E2D3C/0x4B5A6978 交替）
	@@   首 0x000 / 中 0x080 / 尾 0x0F8（高 4 B = 第 63 个元素、低 4 B 保持 MSTORE 模式）
	@@   0x100 = 第 65 个元素（i=64），未写 ⇒ 保持 MSTORE 模式 0xC0DE0000000000C0
	set.rb rb3, MUNI
	ldm.t	{rf1:rf63}, [rb3, rd0]
	set.rb rb4, MSTORE
	stm.t	{rf1:rf63}, [rb4, rd0]
	__CHECK_MEM        15, MSTORE, 0x000, 0x0F1E2D3C4B5A6978
	__CHECK_MEM        16, MSTORE, 0x080, 0x0F1E2D3C4B5A6978
	__CHECK_MEM        17, MSTORE, 0x0F8, 0x0F1E2D3C000000BF
	__CHECK_MEM        18, MSTORE, 0x100, 0xC0DE0000000000C0

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC         19, ILLI, 0x2F143040, rb3, MDATA_T, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        20, ILLI, 0x2FDC304A, rb3, MDATA_T, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        21, ILLI, 0x2FFC3042, rb3, MDATA_T, rd19, 0x000
	@@ 首址未按 4 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        22, stm.t, {rf5:rf6}, MALIGN, rb3, MDATA_T, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        23, stm.t, {rf5:rf6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        24, stm.t, {rf5:rf6}, CFXMEM, rb3, 0xFFFFFF7FFFFC, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        25, stm.t, {rf5:rf6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000
	@@ rf0 作源合法（读出 FCSR 的 qNaN），此处改测整段越出地址窗口 ⇒ CFXMEM
	TEST_FAULT_M        26, stm.t, {rf0:rf1}, CFXMEM, rb3, 0xFFFFFF7FFFFC, rd19, 0x000

	__TEST_SECTIONS
