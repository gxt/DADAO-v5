@@ ld.sb_rrii_rd.S — ld.sb rdHA, [rbHB, imms12]（rrii, opc 0x13）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ld.sb_rrii_rd　形式：rrii　opc：0x13　mask：0xFF000000
@@ 语义：目的 ← sign_extend(mem[EA])；EA = rb[47:0] + imms12（大端；8 位符号扩展）
@@ 对齐：无要求（字节访问）
@@ 合法性：目的为 0 号寄存器 ⇒ ILLI
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 2 / semantic 5 / boundary 6 / overlap 2（链例 15 + 故障例 2；故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_LD            1, ld.sb,  rd63,  rb63,  TEST_DATA,          0x000,    0x0000000000000001
	TEST_LD            2, ld.sb,  rd1,   rb1,   TEST_DATA + 0x008,  0x000,    0x0000000000000000

	@@ ---- semantic ----
	TEST_LD            3, ld.sb,  rd2,   rb4,   TEST_DATA,          0x000,    0x0000000000000001
	TEST_LD            4, ld.sb,  rd2,   rb4,   TEST_DATA,          0x007,    0xFFFFFFFFFFFFFFEF
	TEST_LD            5, ld.sb,  rd2,   rb4,   TEST_DATA,          0x008,    0x0000000000000000
	TEST_LD            6, ld.sb,  rd2,   rb4,   TEST_DATA,          0x020,    0xFFFFFFFFFFFFFF80
	TEST_LD            7, ld.sb,  rd2,   rb4,   TEST_DATA,          0x018,    0xFFFFFFFFFFFFFFFF

	@@ ---- boundary ----
	TEST_LD            8, ld.sb,  rd5,   rb6,   TEST_DATA,          0x037,    0xFFFFFFFFFFFFFF80
	TEST_LD            9, ld.sb,  rd5,   rb6,   TEST_DATA,          0x00F,    0x0000000000000077
	TEST_LD           10, ld.sb,  rd5,   rb6,   TEST_DATA,          0x0E0,    0x0000000000000000
	TEST_LD           11, ld.sb,  rd5,   rb6,   TEST_DATA,          0x09F,    0x0000000000000055
	TEST_LD           12, ld.sb,  rd7,   rb7,   TEST_DATA + 0x800,  -0x800,   0x0000000000000001
	TEST_LD           13, ld.sb,  rd8,   rb8,   TEST_DATA + 0x800,  -0x7FF,   0x0000000000000023

	@@ ---- overlap ----
	TEST_LD           14, ld.sb,  rd1,   rb1,   TEST_DATA,          0x007,    0xFFFFFFFFFFFFFFEF
	@@ overlap：同一目的连装两次，后到者生效
	LOAD_ADDR rb9, TEST_DATA
	ld.sb   rd2, [rb9, 0x000]
	ld.sb   rd2, [rb9, 0x007]
	__CHECK_RD 15, rd2, 0xFFFFFFFFFFFFFFEF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	TEST_FAULT        16, ld.sb,  rd0,   ILLI,  rb3,                TEST_DATA, 0x000  @@ rd0 作目的 ⇒ ILLI（dst_rd0）
	TEST_FAULT        17, ld.sb,  rd1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
