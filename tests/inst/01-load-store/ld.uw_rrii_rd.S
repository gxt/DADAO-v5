@@ ld.uw_rrii_rd.S — ld.uw rdHA, [rbHB, imms12]（rrii, opc 0x11）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ld.uw_rrii_rd　形式：rrii　opc：0x11　mask：0xFF000000
@@ 语义：目的 ← zero_extend(mem[EA])；EA = rb[47:0] + imms12（大端；16 位零扩展）
@@ 对齐：EA 需 2 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：目的为 0 号寄存器 ⇒ ILLI
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 3 / semantic 5 / boundary 6 / overlap 2（链例 15 + 故障例 3；故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

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

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	TEST_FAULT        16, ld.uw,  rd0,   ILLI,  rb3,                TEST_DATA, 0x000  @@ rd0 作目的 ⇒ ILLI（dst_rd0）
	TEST_FAULT        17, ld.uw,  rd1,   MALIGN, rb3,                TEST_DATA, 0x001  @@ EA 未按 2 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        18, ld.uw,  rd1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
