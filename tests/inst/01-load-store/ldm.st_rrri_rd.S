@@ ldm.st_rrri_rd.S — ldm.st {rdHA:rdHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x2D）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ldm.st_rrri_rd　形式：rrri　opc：0x2D　mask：0xFF000000
@@ 语义：目的 i ← sign_extend(mem32[EA + 4i])；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：目的 rdHA 为 rd0 ⇒ ILLI；索引 rdHC 落在传送范围 rd[HA..HA+immu6-1] 内 ⇒ ILLI（`ldm` 禁重叠）；immu6=0 ⇒ ILLI；rdHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 4 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：boundary 3 / rb0 3（链例 17 + 故障例 9；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ encoding：bank 最高寄存器作组首（count=1，rd 边界）
	TEST_LDM         1, ldm.st, {rd63:rd63}, rb3, MDATA_T + 0x000, rd19, 0x000, MDUMP + 0x000, 1, 0x8000000000000000

	@@ encoding：bank 低端起始，count=2
	TEST_LDM         2, ldm.st, {rd1:rd2}, rb3, MDATA_T + 0x008, rd19, 0x000, MDUMP + 0x008, 1, 0x8000000280000003

	@@ semantic：count=3 三个连续元素
	TEST_LDM         3, ldm.st, {rd5:rd7}, rb3, MDATA_T + 0x010, rd19, 0x000, MDUMP + 0x010, 2, 0x8000000480000005, 0x8000000600000000

	@@ semantic：count=8（多拍，元素不跨 8 B 拍）
	TEST_LDM         4, ldm.st, {rd8:rd15}, rb3, MDATA_T + 0x020, rd19, 0x000, MDUMP + 0x020, 4, 0x8000000880000009, 0x8000000A8000000B, 0x8000000C8000000D, 0x8000000E8000000F

	@@ semantic：宽度/符号扩展逐元素核对（符号扩展）
	set.rb rb3, MDATA_T + 0x030
	set.rd    rd19, 0x000
	ldm.st	{rd5:rd7}, [rb3, rd19]
	__CHECK_RD         5, rd5, 0xFFFFFFFF8000000C
	__CHECK_RD         6, rd7, 0xFFFFFFFF8000000E

	@@ semantic：同一组首、不同偏移（偏移来自 rd19）
	TEST_LDM         7, ldm.st, {rd5:rd6}, rb3, MDATA_T + 0x038, rd19, 0x000, MDUMP + 0x040, 1, 0x8000000E8000000F

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_LDM         8, ldm.st, {rd5:rd6}, rb3, MDATA_T + 0x840, rd19, -0x800, MDUMP + 0x048, 1, 0x8000001080000011

	@@ boundary：组首+count == 64 恰好合法（不环绕、不截断）
	TEST_LDM         9, ldm.st, {rd62:rd63}, rb3, MDATA_T + 0x048, rd19, 0x000, MDUMP + 0x050, 1, 0x8000001280000013

	@@ semantic：大偏移（0x80）仍按元素宽度递增
	TEST_LDM        10, ldm.st, {rd5:rd7}, rb3, MDATA_T + 0x080, rd19, 0x000, MDUMP + 0x058, 2, 0x8000002080000021, 0x8000002200000000

	@@ boundary：索引恰在传送范围**外一位**（组首 rd20、索引 rd19）⇒ 正常执行（范围内 ⇒ ILLI，见故障例）
	TEST_LDM        11, ldm.st, {rd20:rd22}, rb3, MDATA_T + 0x058, rd19, 0x000, MDUMP + 0x068, 2, 0x8000001680000017, 0x8000001800000000


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	TEST_LDM  12, ldm.st,  {rd5:rd5}, rb3, TEST_DATA + 0x028, rd19, 0x000, MDUMP + 0x1C0, 1, 0x7FFFFFFF00000000
	TEST_LDM  13, ldm.st,  {rd5:rd5}, rb3, TEST_DATA + 0x020, rd19, 0x000, MDUMP + 0x1C8, 1, 0x8000000000000000
	TEST_LDM  14, ldm.st,  {rd5:rd5}, rb3, TEST_DATA + 0x088, rd19, 0x000, MDUMP + 0x1D0, 1, 0xFFFFFFFF00000000

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
	ldm.st   {rd5:rd5}, [rb0, rd19]	@@ 被测 @0x2020：EA = 0x2000
	rd2rd	{rd21:rd21}, {rd5:rd5}
	__CHECK_RD 15, rd21, 0xFFFFFFFF80000000	@@ 负向极小
__rb0n_ck:
	jump	[rb0, __rb0z]
	.org	0x2080
__rb0z:
	@@ 被测 @0x2088：EA = 自身指令地址（宏内 aip.si @0x2080 + 显式基址 +8 读回；8 B 对齐）
	__CHECK_RD_LDM_IP 16, ldm.st, rd5, rd13, rd
__rb0z_ck:
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	set.rb rb26, (TEST_DATA + 0x088 - 8)
	aip.si	rb25, 0			@@ rb25 = ENTRY+0x2180
	sub.o	rd19, rb26, rb25		@@ rd19 = (TEST_DATA+0x080) − 0x2180
	ldm.st   {rd5:rd5}, [rb0, rd19]	@@ 被测 @0x2188：EA = ENTRY+0x5888
	rd2rd	{rd21:rd21}, {rd5:rd5}
	__CHECK_RD 17, rd21, 0xFFFFFFFFFFFFFFFF	@@ 全 1（正偏移 ⇒ 数据区）
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        18, ILLI, 0x2D143040, rb3, MDATA_T, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        19, ILLI, 0x2DDC304A, rb3, MDATA_T, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        20, ILLI, 0x2DFC3042, rb3, MDATA_T, rd19, 0x000
	@@ 首址未按 4 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        21, ldm.st, {rd5:rd6}, MALIGN, rb3, MDATA_T, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        22, ldm.st, {rd5:rd6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        23, ldm.st, {rd5:rd6}, CFXMEM, rb3, 0xFFFFFF7FFFFC, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        24, ldm.st, {rd5:rd6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000
	@@ overlap：索引 rd7 落在传送范围 rd5..rd8 内 ⇒ ILLI（`ldm` 禁重叠）
	TEST_FAULT_M        25, ldm.st, {rd5:rd8}, ILLI, rb3, MDATA_T, rd7, 0x000
	@@ 目的 rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_M        26, ldm.st, {rd0:rd1}, ILLI, rb3, MDATA_T, rd19, 0x000

	__TEST_SECTIONS
