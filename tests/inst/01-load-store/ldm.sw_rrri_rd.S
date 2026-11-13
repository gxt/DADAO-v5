@@ ldm.sw_rrri_rd.S — ldm.sw {rdHA:rdHA+immu6-1}, [rbHB, rdHC]（rrri, opc 0x2C）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ldm.sw_rrri_rd　形式：rrri　opc：0x2C　mask：0xFF000000
@@ 语义：目的 i ← sign_extend(mem16[EA + 2i])；EA = rb[47:0] + rd[63:0]（immu6 = 元素个数 1..63；元素宽度整除 8 且起址按宽度对齐 ⇒ 元素不跨 8 B 拍）
@@ 合法性：目的 rdHA 为 rd0 ⇒ ILLI；索引 rdHC 落在传送范围 rd[HA..HA+immu6-1] 内 ⇒ ILLI（`ldm` 禁重叠）；immu6=0 ⇒ ILLI；rdHA+immu6>64 ⇒ ILLI（不环绕、不截断）；首址未按 2 B 对齐 ⇒ MALIGN
@@ 数据块：`tests/inst/macros/inst_test.inc` 的多元素区（MDATA_B/W/T/O、MUNI、MDUMP、MSTORE；字面量见该文件）
@@ 用例：链例 10 + 故障例 9（故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ encoding：bank 最高寄存器作组首（count=1，rd 边界）
	TEST_LDM         1, ldm.sw, {rd63:rd63}, rb3, MDATA_W + 0x000, rd19, 0x000, MDUMP + 0x000, 1, 0x8000000000000000

	@@ encoding：bank 低端起始，count=2
	TEST_LDM         2, ldm.sw, {rd1:rd2}, rb3, MDATA_W + 0x008, rd19, 0x000, MDUMP + 0x008, 1, 0x8004800500000000

	@@ semantic：count=3 三个连续元素
	TEST_LDM         3, ldm.sw, {rd5:rd7}, rb3, MDATA_W + 0x010, rd19, 0x000, MDUMP + 0x010, 1, 0x80088009800A0000

	@@ semantic：count=16（多拍，元素不跨 8 B 拍）
	TEST_LDM         4, ldm.sw, {rd24:rd39}, rb3, MDATA_W + 0x020, rd19, 0x000, MDUMP + 0x018, 4, 0x8010801180128013, 0x8014801580168017, 0x80188019801A801B, 0x801C801D801E801F

	@@ semantic：宽度/符号扩展逐元素核对（符号扩展）
	LOAD_ADDR rb3, MDATA_W + 0x030
	__LI    rd19, 0x000
	ldm.sw	{rd5:rd7}, [rb3, rd19]
	__CHECK_RD         5, rd5, 0xFFFFFFFFFFFF8018
	__CHECK_RD         6, rd7, 0xFFFFFFFFFFFF801A

	@@ semantic：同一组首、不同偏移（偏移来自 rd19）
	TEST_LDM         7, ldm.sw, {rd5:rd6}, rb3, MDATA_W + 0x038, rd19, 0x000, MDUMP + 0x038, 1, 0x801C801D00000000

	@@ boundary：偏移寄存器为负（EA = 基址 + 负偏移，取 48 位模加）
	TEST_LDM         8, ldm.sw, {rd5:rd6}, rb3, MDATA_W + 0x840, rd19, -0x800, MDUMP + 0x040, 1, 0x8020802100000000

	@@ boundary：组首+count == 64 恰好合法（不环绕、不截断）
	TEST_LDM         9, ldm.sw, {rd62:rd63}, rb3, MDATA_W + 0x048, rd19, 0x000, MDUMP + 0x048, 1, 0x8024802500000000

	@@ semantic：大偏移（0x80）仍按元素宽度递增
	TEST_LDM        10, ldm.sw, {rd5:rd7}, rb3, MDATA_W + 0x080, rd19, 0x000, MDUMP + 0x050, 1, 0x8040804180420000

	@@ boundary：索引恰在传送范围**外一位**（组首 rd20、索引 rd19）⇒ 正常执行（范围内 ⇒ ILLI，见故障例）
	TEST_LDM        11, ldm.sw, {rd20:rd22}, rb3, MDATA_W + 0x058, rd19, 0x000, MDUMP + 0x058, 1, 0x802C802D802E0000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 口径：多元素指令**允许部分元素已生效**（用户 2026-11-13 裁定）⇒ 故障例只比异常码，
	@@   不判目的寄存器/目标内存的副作用（单元素 `ld`/`st` 的精确性见 `012`，不在本文件）
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        12, ILLI, 0x2C143040, rb3, MDATA_W, rd19, 0x000
	@@ 组首+immu6=65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        13, ILLI, 0x2CDC304A, rb3, MDATA_W, rd19, 0x000
	@@ bank 顶端 63 + immu6=2 = 65 > 64 ⇒ ILLI（边界不环绕）
	TEST_FAULT_ENC        14, ILLI, 0x2CFC3042, rb3, MDATA_W, rd19, 0x000
	@@ 首址未按 2 B 对齐 ⇒ MALIGN
	TEST_FAULT_M        15, ldm.sw, {rd5:rd6}, MALIGN, rb3, MDATA_W, rd19, 0x001
	@@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT_M        16, ldm.sw, {rd5:rd6}, CFXMEM, rb3, 0x0, rd19, 0x000
	@@ 整段越出地址窗口（首元素在 SRAM 尾、后续元素越界）⇒ CFXMEM
	TEST_FAULT_M        17, ldm.sw, {rd5:rd6}, CFXMEM, rb3, 0xFFFFFF7FFFFE, rd19, 0x000
	@@ 保留 cfx 地址空间（addr[47:42]=6）的普通访存 ⇒ CFXMEM
	TEST_FAULT_M        18, ldm.sw, {rd5:rd6}, CFXMEM, rb3, 0x180000000000, rd19, 0x000
	@@ overlap：索引 rd7 落在传送范围 rd5..rd8 内 ⇒ ILLI（`ldm` 禁重叠）
	TEST_FAULT_M        19, ldm.sw, {rd5:rd8}, ILLI, rb3, MDATA_W, rd7, 0x000
	@@ 目的 rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_M        20, ldm.sw, {rd0:rd1}, ILLI, rb3, MDATA_W, rd19, 0x000

	__TEST_SECTIONS
