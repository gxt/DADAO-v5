@@ ld.t_rrii_rf.S — ld.t rfHA, [rbHB, imms12]（rrii, opc 0x16）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ld.t_rrii_rf　形式：rrii　opc：0x16　mask：0xFF000000
@@ 语义：目的 ← zero_extend(mem[EA])；EA = rb[47:0] + imms12（大端；32 位零扩展）
@@ 对齐：EA 需 4 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：该银行 0 号寄存器可作目的（无 dst_0 限制）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 2 / semantic 5 / boundary 6 / overlap 2（链例 15 + 故障例 2；故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_LD_RF_LO32    1, ld.t,   rf63,  rb63,  TEST_DATA,          0x000,    0x0000000001234567
	TEST_LD_RF_LO32    2, ld.t,   rf1,   rb1,   TEST_DATA + 0x008,  0x000,    0x0000000000112233

	@@ ---- semantic ----
	TEST_LD_RF_LO32    3, ld.t,   rf2,   rb4,   TEST_DATA,          0x000,    0x0000000001234567
	TEST_LD_RF_LO32    4, ld.t,   rf2,   rb4,   TEST_DATA,          0x004,    0x0000000089ABCDEF
	TEST_LD_RF_LO32    5, ld.t,   rf2,   rb4,   TEST_DATA,          0x008,    0x0000000000112233
	TEST_LD_RF_LO32    6, ld.t,   rf2,   rb4,   TEST_DATA,          0x020,    0x0000000080000000
	TEST_LD_RF_LO32    7, ld.t,   rf2,   rb4,   TEST_DATA,          0x018,    0x00000000FFEEDDCC

	@@ ---- boundary ----
	TEST_LD_RF_LO32    8, ld.t,   rf5,   rb6,   TEST_DATA,          0x034,    0x0000000000000080
	TEST_LD_RF_LO32    9, ld.t,   rf5,   rb6,   TEST_DATA,          0x01C,    0x00000000BBAA9988
	TEST_LD_RF_LO32   10, ld.t,   rf5,   rb6,   TEST_DATA,          0x0E0,    0x0000000000000000
	TEST_LD_RF_LO32   11, ld.t,   rf5,   rb6,   TEST_DATA,          0x09C,    0x0000000055555555
	TEST_LD_RF_LO32   12, ld.t,   rf7,   rb7,   TEST_DATA + 0x800,  -0x800,   0x0000000001234567
	TEST_LD_RF_LO32   13, ld.t,   rf8,   rb8,   TEST_DATA + 0x800,  -0x7FC,   0x0000000089ABCDEF

	@@ ---- overlap ----
	TEST_LD_RF_LO32   14, ld.t,   rf1,   rb1,   TEST_DATA,          0x000,    0x0000000001234567
	@@ overlap：同一目的连装两次，后到者生效
	LOAD_ADDR rb9, TEST_DATA
	ld.t    rf2, [rb9, 0x000]
	ld.t    rf2, [rb9, 0x008]
	rf2rd	{rd21:rd21}, {rf2:rf2}
	__CHECK_RD 15, rd21, 0x0000000000112233

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	TEST_FAULT        16, ld.t,   rf1,   MALIGN, rb3,                TEST_DATA, 0x002  @@ EA 未按 4 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        17, ld.t,   rf1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
