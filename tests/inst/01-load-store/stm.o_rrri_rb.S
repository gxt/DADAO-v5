@@ stm.o_rrri_rb.S — stm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x3B）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：stm.o_rrri_rb　形式：rrri　opc：0x3B　mask：0xFF000000
@@ 语义：mem64[EA + 8i] ← 源 i；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 字节数据单元）
@@ 合法性：rb0 作源合法（读出当前指令地址）；允许基址 rbHB 落在源范围内（`stm` 只读，行为确定，不触发 ILLI）；immu6=0 ⇒ ILLI；rbHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 8 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：boundary 3 / rb0 3（链例 27 + 故障例 7；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ encoding：count=2
	TEST_STM         1, stm.o, rb, {rb1:rb2}, rb4, MSTORE, rd19, 0x000, MDATA_O + 0x000, 0x0102030405060708, 0x0102030405060709

	@@ semantic：count=3
	TEST_STM         2, stm.o, rb, {rb5:rb7}, rb4, MSTORE, rd19, 0x020, MDATA_O + 0x010, 0x010203040506070A, 0x010203040506070B, 0x010203040506070C

	@@ semantic：count=8（多个数据单元，元素不跨 8 字节数据单元）
	TEST_STM         3, stm.o, rb, {rb8:rb15}, rb4, MSTORE, rd19, 0x048, MDATA_O + 0x020, 0x010203040506070C, 0x010203040506070D, 0x010203040506070E, 0x010203040506070F, 0x0102030405060710, 0x0102030405060711, 0x0102030405060712, 0x0102030405060713

	@@ 保持区：存储区左侧数据单元保持不变
	__CHECK_MEM         4, MSTORE, 0x040, 0xC0DE0000000000A8

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_STM         5, stm.o, rb, {rb5:rb6}, rb4, MSTORE + 0x898, rd19, -0x800, MDATA_O + 0x050, 0x0102030405060712, 0x0102030405060713

	@@ boundary：SRAM 尾部数据单元（0xffffff7ffff8）可写，读写逐字节相等
	set.rb rb28, MDATA_O + 0x090
	ldm.o	{rb5:rb5}, [rb28, rd0]
	set.rd    rd19, 0x000
	set.rb rb4, 0xFFFFFF7FFFF8
	stm.o	{rb5:rb5}, [rb4, rd19]
	set.rb rb21, 0xFFFFFF7FFFF8
	ld.o	rd21, [rb21, 0]
	__CHECK_RD         6, rd21, 0x010203040506071A

	@@ overlap：基址 rb3 落在源组内（`stm` 允许重叠）⇒ 正常执行，行为确定
	set.rb rb28, MDATA_O + 0x0A8
	ldm.o	{rb1:rb5}, [rb28, rd0]
	set.rd    rd19, 0x0B8
	set.rb rb3, MSTORE
	stm.o	{rb1:rb5}, [rb3, rd19]

	@@ overlap：`stm` 只读，源组 rb1..rb5 事后仍是原值（含 rb3=MSTORE）
	set.rb rb28, MDUMP + 0x100
	stm.o	{rb1:rb5}, [rb28, rd0]
	__CHECK_MEM         7, MDUMP, 0x100, 0x010203040506071D
	__CHECK_MEM         8, MDUMP, 0x108, 0x010203040506071E
	__CHECK_MEM         9, MDUMP, 0x110, MSTORE        @@ 期望 = 源组里 rb3 的值（= MSTORE 地址；用符号 ⇒ 与布局无关）
	__CHECK_MEM        10, MDUMP, 0x118, 0x0102030405060720
	__CHECK_MEM        11, MDUMP, 0x120, 0x0102030405060721
	__CHECK_MEM        12, MSTORE, 0x0B8, 0x010203040506071D
	__CHECK_MEM        13, MSTORE, 0x0C0, 0x010203040506071E
	__CHECK_MEM        14, MSTORE, 0x0C8, MSTORE        @@ 同上（源组 rb3 原值）
	__CHECK_MEM        15, MSTORE, 0x0D0, 0x0102030405060720
	__CHECK_MEM        16, MSTORE, 0x0D8, 0x0102030405060721

	@@ encoding：组首高位单元素
	TEST_STM        17, stm.o, rb, {rb40:rb40}, rb4, MSTORE, rd19, 0x0F0, MDATA_O + 0x058, 0x0102030405060713


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	TEST_STM  18, stm.o,   rb, {rb5:rb5}, rb4, MSTORE, rd19, 0x1C0, TEST_DATA + 0x028, 0x7FFFFFFFFFFFFFFF
	TEST_STM  19, stm.o,   rb, {rb5:rb5}, rb4, MSTORE, rd19, 0x1C8, TEST_DATA + 0x020, 0x8000000000000000
	TEST_STM  20, stm.o,   rb, {rb5:rb5}, rb4, MSTORE, rd19, 0x1D0, TEST_DATA + 0x088, 0xFFFFFFFFFFFFFFFF
	@@   ^ 三条各在 MSTORE + 0x1C0/0x1C8/0x1D0 写一个数据单元（值 = TEST_DATA + 0x028/0x020/0x088 的 64 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.rb rb28, TEST_DATA + 0x088
	ldm.o    {rb5:rb5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0n_pre]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零
	.org	0x201C
__rb0n_pre:
	set.rd	rd19, -0x020		@@ 偏移：EA = 0x2000 + 0
	.org	0x2020
__rb0n:
	stm.o    {rb5:rb5}, [rb0, rd19]	@@ 被测 @0x2020：EA = 0x2000 + 0
	__CHECK_MEM 21, (ENTRY + 0x2000), 0, 0xFFFFFFFFFFFFFFFF	@@ 负档槽（零）只被写低 64 位
__rb0n_ck:
	set.rb	rb5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	@@ 被测 @0x20D0：EA = 自身指令地址（宏内预读 8 字节数据单元、只改高 32 位后写回）
	__CHECK_RD_STM_IP 22, stm.o, rb5, rb
__rb0z_ck:
	set.rb rb28, TEST_DATA + 0x088
	ldm.o    {rb5:rb5}, [rb28, rd0]		@@ 源组 = TEST_DATA + 0x088
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	set.rb rb26, (MSTORE + 0x1C0 + 0 - 8)
	aip.si	rb25, 0			@@ rb25 = ENTRY+0x2180
	sub.o	rd19, rb26, rb25
	stm.o    {rb5:rb5}, [rb0, rd19]	@@ 被测 @0x2188：EA = MSTORE + 0x1C0 + 0
	__CHECK_MEM 23, (MSTORE + 0x1C0), 0, 0xFFFFFFFFFFFFFFFF
__rb0p_ck:

	@@ ---- boundary：immu6=63（最大合法个数）整组存储（MUNI 同值元素）----
	@@   源组 = RB 的 MUNI 63 个同值数据单元（rb1..rb63 占满 ⇒ 装入/存储的基址都只能用 rb0=IP）
	@@   `ldm` 禁重叠 ⇒ 装入也不能拿 rb1..rb63 作基址；两处地址都由 `.org` 钉住、偏移写字面常量：
	@@   ldm @ENTRY+0x2388（偏移 0x4178 = MUNI−…）、stm @ENTRY+0x2390（偏移 0x4570 = MSTORE−…）
	@@   装入覆盖 rb1..rb63 含签名写指针 rb30（元素 29）⇒ 存前经 rd18 暂存、存后恢复
	jump	[rb0, __uni63_pre]
	.org	0x2380
__uni63_pre:
	set.rd	rd19, 0x4178		@@ MUNI − (ENTRY+0x2388)
	rb2rd	{rd18:rd18}, {rb30:rb30}	@@ 暂存签名写指针（ldm 装入会覆盖 rb30）
	.org	0x2388
	ldm.o	{rb1:rb63}, [rb0, rd19]	@@ 装入 @0x2388：EA = MUNI
	set.rd	rd19, 0x4570		@@ MSTORE − (ENTRY+0x2390)
	.org	0x2390
	stm.o	{rb1:rb63}, [rb0, rd19]	@@ 被测 @0x2390：EA = MSTORE
	rd2rb	{rb30:rb30}, {rd18:rd18}	@@ 恢复签名写指针后再记检查点
	__CHECK_MEM        24, MSTORE, 0x000, 0x0F1E2D3C4B5A6978
	__CHECK_MEM        25, MSTORE, 0x0F8, 0x0F1E2D3C4B5A6978
	__CHECK_MEM        26, MSTORE, 0x1F0, 0x0F1E2D3C4B5A6978
	__CHECK_MEM        27, MSTORE, 0x1F8, 0xC0DE0000000000DF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        28, ILLI, 0x3B143040, rb3, MDATA_O, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        29, ILLI, 0x3BDC304A, rb3, MDATA_O, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        30, ILLI, 0x3BFC3042, rb3, MDATA_O, rd19, 0x000
	@@ 首址未按 8 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        31, stm.o, {rb5:rb6}, MALIGN, rb3, MDATA_O, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        32, stm.o, {rb5:rb6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        33, stm.o, {rb5:rb6}, CFXMEM, rb3, 0xFFFFFF7FFFF8, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        34, stm.o, {rb5:rb6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
