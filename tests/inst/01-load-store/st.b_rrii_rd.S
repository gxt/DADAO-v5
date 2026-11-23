@@ st.b_rrii_rd.S — st.b rdHA, [rbHB, imms12]（rrii, opc 0x18）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.b_rrii_rd　形式：rrii　opc：0x18　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器低 8 位；EA = rb[47:0] + imms12（大端）；只改 1 个字节，其余 7 个字节保持
@@ 对齐：无要求（字节访问）
@@ 合法性：源 0 号寄存器：rd0 读出 0（合法）；无 dst_0 限制
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节数据单元，字面量见该文件）
@@ 用例：encoding 2 / legality 4 / semantic 5 / boundary 8 / overlap 2 / rb0 3（链例 21 + 故障例 3；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_ST            1, st.b,   rd63,  rb63,  TEST_DATA,          0x0B8,    0xDEADBEEFCAFEF00D, 0x0D11111111111111
	TEST_ST            2, st.b,   rd1,   rb1,   TEST_DATA + 0x008,  0x0A8,    0xDEADBEEFCAFEF00D, 0x0DF0F0F0F0F0F0F0

	@@ ---- semantic ----
	TEST_ST            3, st.b,   rd2,   rb3,   TEST_DATA,          0x010,    0xDEADBEEFCAFEF00D, 0x0D99AABBCCDDEEFF
	TEST_ST            4, st.b,   rd2,   rb3,   TEST_DATA,          0x019,    0xDEADBEEFCAFEF00D, 0xFF0DDDCCBBAA9988
	TEST_ST            5, st.b,   rd2,   rb3,   TEST_DATA,          0x022,    0xDEADBEEFCAFEF00D, 0x80000D0000000000
	TEST_ST            6, st.b,   rd2,   rb3,   TEST_DATA,          0x02B,    0xDEADBEEFCAFEF00D, 0x7FFFFF0DFFFFFFFF
	TEST_ST            7, st.b,   rd2,   rb3,   TEST_DATA,          0x034,    0xDEADBEEFCAFEF00D, 0x000000000D000080

	@@ ---- boundary ----
	TEST_ST            8, st.b,   rd2,   rb3,   TEST_DATA,          0x03D,    0xDEADBEEFCAFEF00D, 0xFFFFFFFFFF0D0000
	TEST_ST            9, st.b,   rd2,   rb3,   TEST_DATA,          0x046,    0xDEADBEEFCAFEF00D, 0x00000000FFFF0DFF
	TEST_ST           10, st.b,   rd2,   rb3,   TEST_DATA,          0x04F,    0xDEADBEEFCAFEF00D, 0x000000000000FF0D
	TEST_ST           11, st.b,   rd2,   rb3,   TEST_DATA,          0x050,    0xDEADBEEFCAFEF00D, 0x0D00000000008000
	TEST_ST           12, st.b,   rd2,   rb4,   TEST_DATA + 0x800,  -0x008,   0xDEADBEEFCAFEF00D, 0x0D00000000000000

	@@ ---- overlap ----
	TEST_ST           13, st.b,   rd2,   rb5,   TEST_DATA,          0x058,    0xDEADBEEFCAFEF00D, 0x0D00000000007FFF
	TEST_ST           14, st.b,   rd2,   rb6,   TEST_DATA,          0x060,    0xDEADBEEFCAFEF00D, 0x0DDCBA9876543210

	@@ ---- legality ----
	@@ legality：st 允许 rd0 作源（读出 0），不是 ILLI
	set.rb rb3, TEST_DATA
	st.b  	rd0, [rb3, 0x070]
	__CHECK_MEM 15, TEST_DATA, 0x070, 0x00A5A5A55A5A5A5A


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	TEST_ST    16, st.b,    rd5,   rb6,   MSTORE + 0x1C7,   0x000,    0x000000000000007F, 0xC0DE00000000007F
	TEST_ST    17, st.b,    rd5,   rb6,   MSTORE + 0x1CF,   0x000,    0x0000000000000080, 0xC0DE000000000080
	TEST_ST    18, st.b,    rd5,   rb6,   MSTORE + 0x1D7,   0x000,    0x00000000000000FF, 0xC0DE0000000000FF
	@@   ^ 三条各写 MSTORE + 0x1C0/0x1C8/0x1D0 一拍（值 = TEST_DATA + 0x028/0x020/0x088 的 8 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0n]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零（死的预设数据槽）
	.org	0x2040
__rb0n:
	st.b     rd5, [rb0, -0x039]		@@ 被测 @0x2040：EA = 0x2000 + 7
	__CHECK_MEM 19, (ENTRY + 0x2000), 0, 0x0000000000000011	@@ 负档槽（零）只被写低 8 位
__rb0n_ck:
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	st.b     rd5, [rb0, 0x000]		@@ 被测 @0x20C0：EA = 自身指令地址（只覆写本指令首 1 B）
	aip.si	rb12, 0
	ld.ub	rd21, [rb12, -0x004]		@@ 独立通路：0x20C4 − 4 = 0x20C0
	__CHECK_RD 20, rd21, 0x0000000000000011
__rb0z_ck:
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	st.b     rd5, [rb0, 0x00F]		@@ 被测 @0x2180：EA = 0x2188 + 7
	jump	[rb0, __rb0p_ck]
	.org	0x2188
	@@ 正档槽：0x2188..0x2190 由 `.org` 填零
	.org	0x2190
__rb0p_ck:
	__CHECK_MEM 21, (ENTRY + 0x2188), 0, 0x0000000000000011
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        22, st.b,   rd1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT        23, st.b,   rd1,   CFXMEM, rb3,                0x400000000000, 0x000  @@ reserved cfx 地址空间（addr[47:42]=16）上的普通访存 ⇒ CFXMEM
	TEST_FAULT        24, st.b,   rd1,   CFXMEM, rb3,                0x8C0000000000, 0x000  @@ reserved cfx 地址空间（addr[47:42]=35）上的普通访存 ⇒ CFXMEM

	__TEST_SECTIONS
