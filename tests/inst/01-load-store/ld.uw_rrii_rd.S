@@ ld.uw_rrii_rd.S — ld.uw rdHA, [rbHB, imms12]（rrii, opc 0x11）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ld.uw_rrii_rd　形式：rrii　opc：0x11　mask：0xFF000000
@@ 语义：目的 ← zero_extend(mem[EA])；EA = rb[47:0] + imms12（大端；16 位零扩展）
@@ 对齐：EA 需 2 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：目的为 0 号寄存器 ⇒ ILLI
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 3 / semantic 5 / boundary 9 / overlap 2 / rb0 3（链例 21 + 故障例 3；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_LD            1, ld.uw,  rd63,  rb63,  TEST_DATA,          0x000,    0x0000000000000123
	TEST_LD            2, ld.uw,  rd1,   rb1,   TEST_DATA + 0x008,  0x000,    0x0000000000000011

	@@ ---- semantic ----
	TEST_LD            3, ld.uw,  rd2,   rb4,   TEST_DATA,          0x000,    0x0000000000000123
	TEST_LD            4, ld.uw,  rd2,   rb4,   TEST_DATA,          0x006,    0x000000000000CDEF
	TEST_LD            5, ld.uw,  rd2,   rb4,   TEST_DATA,          0x008,    0x0000000000000011
	TEST_LD            6, ld.uw,  rd2,   rb4,   TEST_DATA,          0x020,    0x0000000000008000
	TEST_LD            7, ld.uw,  rd2,   rb4,   TEST_DATA,          0x018,    0x000000000000FFEE

	@@ ---- boundary ----
	TEST_LD            8, ld.uw,  rd5,   rb6,   TEST_DATA,          0x036,    0x0000000000000080
	TEST_LD            9, ld.uw,  rd5,   rb6,   TEST_DATA,          0x00E,    0x0000000000006677
	TEST_LD           10, ld.uw,  rd5,   rb6,   TEST_DATA,          0x0E0,    0x0000000000000000
	TEST_LD           11, ld.uw,  rd5,   rb6,   TEST_DATA,          0x09E,    0x0000000000005555
	TEST_LD           12, ld.uw,  rd7,   rb7,   TEST_DATA + 0x800,  -0x800,   0x0000000000000123
	TEST_LD           13, ld.uw,  rd8,   rb8,   TEST_DATA + 0x800,  -0x7FE,   0x0000000000004567

	@@ ---- overlap ----
	TEST_LD           14, ld.uw,  rd1,   rb1,   TEST_DATA,          0x000,    0x0000000000000123
	@@ overlap：同一目的连装两次，后到者生效
	LOAD_ADDR rb9, TEST_DATA
	ld.uw   rd2, [rb9, 0x000]
	ld.uw   rd2, [rb9, 0x008]
	__CHECK_RD 15, rd2, 0x0000000000000011


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 beat）----
	TEST_LD    16, ld.uw,   rd5,   rb6,   TEST_DATA,          0x028,    0x0000000000007FFF
	TEST_LD    17, ld.uw,   rd5,   rb6,   TEST_DATA,          0x020,    0x0000000000008000
	TEST_LD    18, ld.uw,   rd5,   rb6,   TEST_DATA,          0x088,    0x000000000000FFFF

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	jump	[rb0, __rb0n]
	.org	0x2000
	.dd.o64	0x8000000000000000	@@ 负档槽（死数据；各宽度取首字节/半字/字 = 负向极小）
	.org	0x2040
__rb0n:
	ld.uw    rd5, [rb0, -0x040]		@@ 被测 @0x2040：EA = 0x2000
	rd2rd	{rd21:rd21}, {rd5:rd5}
	__CHECK_RD 19, rd21, 0x0000000000008000	@@ 负向极小
__rb0n_ck:
	jump	[rb0, __rb0z]
	.org	0x20C4
__rb0z:
	@@ 被测 @0x20C8：EA = 自身指令地址（宏内 aip.si @0x20C4 + 显式基址 +4 读回）
	__CHECK_RD_IP 20, ld.uw, rd5, rd13, rd
__rb0z_ck:
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	ld.uw    rd5, [rb0, 0x008]		@@ 被测 @0x2180：EA = 0x2188（正档槽）
	jump	[rb0, __rb0p_ck]
	.org	0x2188
	.dd.o64	0x7FFFFFFFFFFFFFFF	@@ 正档槽（死数据；各宽度取首字节/半字/字 = 正向极大）
__rb0p_ck:
	rd2rd	{rd21:rd21}, {rd5:rd5}
	__CHECK_RD 21, rd21, 0x0000000000007FFF	@@ 正向极大
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        22, ld.uw,  rd0,   ILLI,  rb3,                TEST_DATA, 0x000  @@ rd0 作目的 ⇒ ILLI（dst_rd0）
	TEST_FAULT        23, ld.uw,  rd1,   MALIGN, rb3,                TEST_DATA, 0x001  @@ EA 未按 2 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        24, ld.uw,  rd1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
