@@ st.t_rrii_rf.S — st.t rfHA, [rbHB, imms12]（rrii, opc 0x17）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.t_rrii_rf　形式：rrii　opc：0x17　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器低 32 位；EA = rb[47:0] + imms12（大端）；只改这几条字节通道，beat 其余字节保持
@@ 对齐：EA 需 4 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：源 0 号寄存器：rf0 读出完整 64 位（合法）；无 dst_0 限制
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 2 / semantic 5 / boundary 8 / overlap 2 / rb0 3（链例 20 + 故障例 2；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

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


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 beat）----
	TEST_ST_RF  15, st.t,    rf5,   rb6,   MSTORE + 0x1C4,   0x000,    0x000000007FFFFFFF, 0xC0DE00007FFFFFFF
	TEST_ST_RF  16, st.t,    rf5,   rb6,   MSTORE + 0x1CC,   0x000,    0x0000000080000000, 0xC0DE000080000000
	TEST_ST_RF  17, st.t,    rf5,   rb6,   MSTORE + 0x1D4,   0x000,    0x00000000FFFFFFFF, 0xC0DE0000FFFFFFFF
	@@   ^ 三条各写 MSTORE + 0x1C0/0x1C8/0x1D0 一拍（值 = TEST_DATA + 0x028/0x020/0x088 的 32 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0n]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零（死的预设数据槽）
	.org	0x2040
__rb0n:
	st.t     rf5, [rb0, -0x03C]		@@ 被测 @0x2040：EA = 0x2000 + 4
	__CHECK_MEM 18, (ENTRY + 0x2000), 0, 0x0000000011111111	@@ 负档槽（零）只被写低 32 位
__rb0n_ck:
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	st.t     rf5, [rb0, 0x000]		@@ 被测 @0x20C0：EA = 自身指令地址（只覆写本指令首 4 B）
	aip.si	rb12, 0
	ld.ut	rd21, [rb12, -0x004]		@@ 独立通路：0x20C4 − 4 = 0x20C0
	__CHECK_RD 19, rd21, 0x0000000011111111
__rb0z_ck:
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	st.t     rf5, [rb0, 0x00C]		@@ 被测 @0x2180：EA = 0x2188 + 4
	jump	[rb0, __rb0p_ck]
	.org	0x2188
	@@ 正档槽：0x2188..0x2190 由 `.org` 填零
	.org	0x2190
__rb0p_ck:
	__CHECK_MEM 20, (ENTRY + 0x2188), 0, 0x0000000011111111
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        21, st.t,   rf1,   MALIGN, rb3,                TEST_DATA, 0x002  @@ EA 未按 4 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        22, st.t,   rf1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
