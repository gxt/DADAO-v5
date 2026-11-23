@@ ldm.t_rrri_rf.S — ldm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x2E）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ldm.t_rrri_rf　形式：rrri　opc：0x2E　mask：0xFF000000
@@ 语义：目的 i ← mem32[EA + 4i]（写 RF 低 32 位，高 32 位不变）；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：rf0 作目的合法（只写低 32 位 ⇒ rf0 内仅 [4:0] 可写，[31:5] 与 [63:32] 保持）；overlap 不适用（范围在 RF、基址在 RB、索引在 RD ⇒ 天然不相交）；immu6=0 ⇒ ILLI；rfHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 4 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：boundary 3 / rb0 3 / 窄写 2 / rf0 作目的 1（链例 21 + 故障例 7；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	@@ ---- 文件专用宏（m15-testcases-017：窄写补测）----
	@@ `ldm.t` 只写各目的 rf 低 32 位、高 32 位保持原值（`spec/SimRISC-01 §4` 写入宽度注；
	@@   `spec/SimRISC-00 §2.3`）⇒ 先用 `ld.o` 把目的装成「高位已知非零」的 8 B 拍，装入后
	@@   `rf2rd` 读回**完整 64 位**。期望两半都取自数据区字面量（独立 oracle，不从实现反推）；
	@@   实现若零扩展（高半清 0）⇒ 用例必红。
	@@ 两个元素（count=2）：两个目的各自预置高位，一次装入两个元素后**两个寄存器都比完整
	@@   64 位**（前一个 `__VERIFY_RD` 不占点号，后一个 `__CHECK_RD` 记本用例 ⇒ 一例一点）。
	@@   参数：pre0/pre1 = 预置拍偏移，off = 装入的元素偏移（同一基址内）。
.macro TEST_LDM_RF_FULL2 pt, r0, r1, base, baseval, pre0, pre1, off, exp0, exp1
	set.rb \base, \baseval
	ld.o	\r0, [\base, \pre0]
	ld.o	\r1, [\base, \pre1]
	set.rd	rd19, \off
	ldm.t	{\r0:\r1}, [\base, rd19]
	rf2rd	{rd22:rd22}, {\r0:\r0}
	__VERIFY_RD \pt, rd22, \exp0
	rf2rd	{rd21:rd21}, {\r1:\r1}
	__CHECK_RD \pt, rd21, \exp1
.endm

	__TEST_BEGIN

	@@ encoding：bank 最高寄存器作组首（count=1，rf 边界）
	TEST_LDM         1, ldm.t, {rf63:rf63}, rb3, MDATA_T + 0x000, rd19, 0x000, MDUMP + 0x000, 1, 0x8000000000000000

	@@ encoding：bank 低端起始，count=2
	TEST_LDM         2, ldm.t, {rf1:rf2}, rb3, MDATA_T + 0x008, rd19, 0x000, MDUMP + 0x008, 1, 0x8000000280000003

	@@ semantic：count=3 三个连续元素
	TEST_LDM         3, ldm.t, {rf5:rf7}, rb3, MDATA_T + 0x010, rd19, 0x000, MDUMP + 0x010, 2, 0x8000000480000005, 0x8000000600000000

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_LDM         4, ldm.t, {rf8:rf15}, rb3, MDATA_T + 0x020, rd19, 0x000, MDUMP + 0x020, 4, 0x8000000880000009, 0x8000000A8000000B, 0x8000000C8000000D, 0x8000000E8000000F

	@@ semantic：逐元素核对
	set.rb rb3, MDATA_T + 0x030
	set.rd    rd19, 0x000
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

	@@ overlap：同一 RF 连装两次，后到者生效（本用例只比低 32 位；高 32 位保持见点 20）
	set.rb rb3, MDATA_T + 0x090
	set.rd    rd19, 0x000
	ldm.t	{rf9:rf9}, [rb3, rd19]
	set.rb rb3, MDATA_T + 0x018
	ldm.t	{rf9:rf9}, [rb3, rd19]
	rf2rd	{rd21:rd21}, {rf9:rf9}
	ext.uo	rd21, rd21, 31
	__CHECK_RD        12, rd21, 0x0000000080000006


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	@@   `ld.t`/`ldm.t` 只写低 32 位 ⇒ 目的先清 0（高 32 位保持 0）
	set.fo	rf5, 0x0000000000000000
	TEST_LDM  13, ldm.t,   {rf5:rf5}, rb3, TEST_DATA + 0x028, rd19, 0x000, MDUMP + 0x1C0, 1, 0x7FFFFFFF00000000
	TEST_LDM  14, ldm.t,   {rf5:rf5}, rb3, TEST_DATA + 0x020, rd19, 0x000, MDUMP + 0x1C8, 1, 0x8000000000000000
	TEST_LDM  15, ldm.t,   {rf5:rf5}, rb3, TEST_DATA + 0x088, rd19, 0x000, MDUMP + 0x1D0, 1, 0xFFFFFFFF00000000

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	jump	[rb0, __rb0n_pre]
	.org	0x2000
	.dd.o64	0x8000000000000000	@@ 负档槽（死数据）
	.org	0x201C
__rb0n_pre:
	set.rd	rd19, -0x020		@@ 偏移 = 0x2020 − 0x2000
	.org	0x2020
__rb0n:
	ldm.t    {rf5:rf5}, [rb0, rd19]	@@ 被测 @0x2020：EA = 0x2000
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD 16, rd21, 0x0000000080000000	@@ 负向极小
__rb0n_ck:
	jump	[rb0, __rb0z]
	.org	0x2080
__rb0z:
	@@ 被测 @0x2088：EA = 自身指令地址（宏内 aip.si @0x2080 + 显式基址 +8 读回；8 B 对齐）
	__CHECK_RD_LDM_IP 17, ldm.t, rf5, rf13, rf
__rb0z_ck:
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	set.rb rb26, (TEST_DATA + 0x088 - 8)
	aip.si	rb25, 0			@@ rb25 = ENTRY+0x2180
	sub.o	rd19, rb26, rb25		@@ rd19 = (TEST_DATA+0x080) − 0x2180
	ldm.t    {rf5:rf5}, [rb0, rd19]	@@ 被测 @0x2188：EA = ENTRY+0x5888
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD 18, rd21, 0x00000000FFFFFFFF	@@ 全 1（正偏移 ⇒ 数据区）

	@@ ==== m15-testcases-017：窄写补测（高 32 位保持，`spec/SimRISC-01 §4` 注）====
	@@ MDATA_T 的元素是 0x80000000+i（i = 偏移/4）⇒ 字面量可现推：`ld.o` 一拍 = 相邻两元素，
	@@   高半 = 前一个元素 ⇒ 期望两半都取自数据区字面量，实现若零扩展（高半清 0）必红。
	@@ 两元素组：高半分别预置 0x80000002（+0x008 拍 = 元素 2/3）/ 0x80000004（+0x010 拍 = 元素 4/5），
	@@   装入 +0x020 的两个元素 0x80000008/0x80000009
	TEST_LDM_RF_FULL2  19, rf5, rf6, rb3, MDATA_T, 0x008, 0x010, 0x020, 0x8000000280000008, 0x8000000480000009
	@@ 同一寄存器被多个元素依次写：预置高半 0x80000000（+0x000 拍），先装元素 0x80000025、
	@@   再装元素 0x80000007 ⇒ 两次窄写都不碰高半，最终仍是 0x8000000080000007
	set.rb rb3, MDATA_T
	ld.o	rf9, [rb3, 0x000]
	set.rd	rd19, 0x094
	ldm.t	{rf9:rf9}, [rb3, rd19]
	set.rd	rd19, 0x01C
	ldm.t	{rf9:rf9}, [rb3, rd19]
	rf2rd	{rd21:rd21}, {rf9:rf9}
	__CHECK_RD 20, rd21, 0x8000000080000007

	@@ ==== m17-testcases-002：rf0 作目的（`spec/SimRISC-01 §4` 注）====
	@@ `ldm.t` 只写各目的低 32 位；`rf0` 在这个写入窗口内只有 [4:0] 可写
	@@   ⇒ [63:32] 与 [31:5] 必须保持写前值。三条断言分离：
	@@   ① [63:32] 与写前快照掩码等值 ② [31:5] 与写前快照掩码等值 ③ [4:0] = 写入值低 5 位。
	set.w	rf0, wp0, 0x0000		@@ 建立已知写前态：清异常状态 [4:0]
	set.w	rf0, wp2, 0x0003		@@ [33:32]（舍入模式）= 11（写窗口外，须保持）
	st.o	rf0, [rb27, 0]			@@ 写前快照（rb27 = WSCRATCH）
	@@ 组内第二个目的读到下一个元素（rf0 ← 元素 0x80000021，rf1 ← 元素 0x80000022）
	set.rb rb3, MDATA_T + 0x084		@@ 元素 0x80000021 ⇒ rf0[4:0] = 0x01
	set.rd	rd19, 0x000
	set.fo	rf1, 0xDEADBEEF00000000		@@ 组内第二目的预置高半（窄写须保持）
	ldm.t	{rf0:rf1}, [rb3, rd19]
	rf2rd	{rd21:rd21}, {rf0:rf0}		@@ 写后 rf0（读出完整 64 位）
	ld.o	rd24, [rb27, 0]			@@ 写前快照
	set.rd	rd20, 0xFFFFFFFF00000000
	and.o	rd22, rd21, rd20
	and.o	rd23, rd24, rd20
	__VERIFY_EQ_RD 21, rd22, rd23		@@ ① [63:32] 保持
	set.rd	rd20, 0x00000000FFFFFFE0
	and.o	rd22, rd21, rd20
	and.o	rd23, rd24, rd20
	__VERIFY_EQ_RD 21, rd22, rd23		@@ ② [31:5] 保持
	set.rd	rd20, 0x000000000000001F
	and.o	rd22, rd21, rd20
	__CHECK_RD 21, rd22, 0x0000000000000001	@@ ③ [4:0] = 写入值低 5 位（0x80000021 ⇒ 0x01）
	rf2rd	{rd21:rd21}, {rf1:rf1}
	__VERIFY_RD 21, rd21, 0xDEADBEEF80000022	@@ 同组非 0 目的仍按窄写（rf1 高半保持）

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        22, ILLI, 0x2E143040, rb3, MDATA_T, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        23, ILLI, 0x2EDC304A, rb3, MDATA_T, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        24, ILLI, 0x2EFC3042, rb3, MDATA_T, rd19, 0x000
	@@ 首址未按 4 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        25, ldm.t, {rf5:rf6}, MALIGN, rb3, MDATA_T, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        26, ldm.t, {rf5:rf6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        27, ldm.t, {rf5:rf6}, CFXMEM, rb3, 0xFFFFFF7FFFFC, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        28, ldm.t, {rf5:rf6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000

	__TEST_SECTIONS
