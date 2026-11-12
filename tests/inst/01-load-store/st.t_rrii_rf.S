@@ st.t_rrii_rf.S — st.t rfHA, [rbHB, imms12]（rrii, opc 0x17）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.t_rrii_rf　形式：rrii　opc：0x17　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器低 32 位；EA = rb[47:0] + imms12（大端）；只改这几条字节通道，beat 其余字节保持
@@ 对齐：EA 需 4 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：源 0 号寄存器：rf0 读出完整 64 位（合法）；无 dst_0 限制
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 2 / semantic 5 / boundary 5 / overlap 2（链例 14 + 故障例 2；故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_ST_RF         1, st.t,   rf63,  rb63,  TEST_DATA,          0x0B8,    0xDEADBEEFCAFEF00D, 0xCAFEF00D11111111
	TEST_ST_RF         2, st.t,   rf1,   rb1,   TEST_DATA + 0x008,  0x0A8,    0xDEADBEEFCAFEF00D, 0xCAFEF00DF0F0F0F0

	@@ ---- semantic ----
	TEST_ST_RF         3, st.t,   rf2,   rb3,   TEST_DATA,          0x010,    0xDEADBEEFCAFEF00D, 0xCAFEF00DCCDDEEFF
	TEST_ST_RF         4, st.t,   rf2,   rb3,   TEST_DATA,          0x01C,    0xDEADBEEFCAFEF00D, 0xFFEEDDCCCAFEF00D
	TEST_ST_RF         5, st.t,   rf2,   rb3,   TEST_DATA,          0x020,    0xDEADBEEFCAFEF00D, 0xCAFEF00D00000000
	TEST_ST_RF         6, st.t,   rf2,   rb3,   TEST_DATA,          0x02C,    0xDEADBEEFCAFEF00D, 0x7FFFFFFFCAFEF00D
	TEST_ST_RF         7, st.t,   rf2,   rb3,   TEST_DATA,          0x030,    0xDEADBEEFCAFEF00D, 0xCAFEF00D00000080

	@@ ---- boundary ----
	TEST_ST_RF         8, st.t,   rf2,   rb3,   TEST_DATA,          0x03C,    0xDEADBEEFCAFEF00D, 0xFFFFFFFFCAFEF00D
	TEST_ST_RF         9, st.t,   rf2,   rb3,   TEST_DATA,          0x040,    0xDEADBEEFCAFEF00D, 0xCAFEF00DFFFFFFFF
	TEST_ST_RF        10, st.t,   rf2,   rb3,   TEST_DATA,          0x04C,    0xDEADBEEFCAFEF00D, 0x00000000CAFEF00D
	TEST_ST_RF        11, st.t,   rf2,   rb3,   TEST_DATA,          0x050,    0xDEADBEEFCAFEF00D, 0xCAFEF00D00008000
	TEST_ST_RF        12, st.t,   rf2,   rb4,   TEST_DATA + 0x800,  -0x008,   0xDEADBEEFCAFEF00D, 0xCAFEF00D00000000

	@@ ---- overlap ----
	TEST_ST_RF        13, st.t,   rf2,   rb5,   TEST_DATA,          0x058,    0xDEADBEEFCAFEF00D, 0xCAFEF00D00007FFF
	TEST_ST_RF        14, st.t,   rf2,   rb6,   TEST_DATA,          0x060,    0xDEADBEEFCAFEF00D, 0xCAFEF00D76543210

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	TEST_FAULT        15, st.t,   rf1,   MALIGN, rb3,                TEST_DATA, 0x002  @@ EA 未按 4 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        16, st.t,   rf1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
