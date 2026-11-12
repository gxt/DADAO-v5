@@ st.w_rrii_rd.S — st.w rdHA, [rbHB, imms12]（rrii, opc 0x19）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.w_rrii_rd　形式：rrii　opc：0x19　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器低 16 位；EA = rb[47:0] + imms12（大端）；只改这几条字节通道，beat 其余字节保持
@@ 对齐：EA 需 2 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：源 0 号寄存器：rd0 读出 0（合法）；无 dst_0 限制
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 3 / semantic 5 / boundary 5 / overlap 2（链例 15 + 故障例 2；故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_ST            1, st.w,   rd63,  rb63,  TEST_DATA,          0x0B8,    0xDEADBEEFCAFEF00D, 0xF00D111111111111
	TEST_ST            2, st.w,   rd1,   rb1,   TEST_DATA + 0x008,  0x0A8,    0xDEADBEEFCAFEF00D, 0xF00DF0F0F0F0F0F0

	@@ ---- semantic ----
	TEST_ST            3, st.w,   rd2,   rb3,   TEST_DATA,          0x010,    0xDEADBEEFCAFEF00D, 0xF00DAABBCCDDEEFF
	TEST_ST            4, st.w,   rd2,   rb3,   TEST_DATA,          0x01A,    0xDEADBEEFCAFEF00D, 0xFFEEF00DBBAA9988
	TEST_ST            5, st.w,   rd2,   rb3,   TEST_DATA,          0x024,    0xDEADBEEFCAFEF00D, 0x80000000F00D0000
	TEST_ST            6, st.w,   rd2,   rb3,   TEST_DATA,          0x02E,    0xDEADBEEFCAFEF00D, 0x7FFFFFFFFFFFF00D
	TEST_ST            7, st.w,   rd2,   rb3,   TEST_DATA,          0x030,    0xDEADBEEFCAFEF00D, 0xF00D000000000080

	@@ ---- boundary ----
	TEST_ST            8, st.w,   rd2,   rb3,   TEST_DATA,          0x03A,    0xDEADBEEFCAFEF00D, 0xFFFFF00DFF000000
	TEST_ST            9, st.w,   rd2,   rb3,   TEST_DATA,          0x044,    0xDEADBEEFCAFEF00D, 0x00000000F00DFFFF
	TEST_ST           10, st.w,   rd2,   rb3,   TEST_DATA,          0x04E,    0xDEADBEEFCAFEF00D, 0x000000000000F00D
	TEST_ST           11, st.w,   rd2,   rb3,   TEST_DATA,          0x050,    0xDEADBEEFCAFEF00D, 0xF00D000000008000
	TEST_ST           12, st.w,   rd2,   rb4,   TEST_DATA + 0x800,  -0x008,   0xDEADBEEFCAFEF00D, 0xF00D000000000000

	@@ ---- overlap ----
	TEST_ST           13, st.w,   rd2,   rb5,   TEST_DATA,          0x058,    0xDEADBEEFCAFEF00D, 0xF00D000000007FFF
	TEST_ST           14, st.w,   rd2,   rb6,   TEST_DATA,          0x060,    0xDEADBEEFCAFEF00D, 0xF00DBA9876543210

	@@ ---- legality ----
	@@ legality：st 允许 rd0 作源（读出 0），不是 ILLI
	LOAD_ADDR rb3, TEST_DATA
	st.w  	rd0, [rb3, 0x070]
	__CHECK_MEM 15, TEST_DATA, 0x070, 0x0000A5A55A5A5A5A

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	TEST_FAULT        16, st.w,   rd1,   MALIGN, rb3,                TEST_DATA, 0x001  @@ EA 未按 2 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        17, st.w,   rd1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
