@@ st.o_rrii_rf.S — st.o rfHA, [rbHB, imms12]（rrii, opc 0x27）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.o_rrii_rf　形式：rrii　opc：0x27　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器整 64 位；EA = rb[47:0] + imms12（大端）；整 8 字节全部写入
@@ 对齐：EA 需 8 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：源 0 号寄存器：rf0 读出完整 64 位（合法）；无 dst_0 限制
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节数据单元，字面量见该文件）
@@ 用例：encoding 2 / legality 3 / semantic 5 / boundary 8 / overlap 2 / rb0 3（链例 21 + 故障例 2；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_ST_RF         1, st.o,   rf63,  rb63,  TEST_DATA,          0x0B8,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF         2, st.o,   rf1,   rb1,   TEST_DATA + 0x008,  0x0A8,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- semantic ----
	TEST_ST_RF         3, st.o,   rf2,   rb3,   TEST_DATA,          0x010,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF         4, st.o,   rf2,   rb3,   TEST_DATA,          0x018,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF         5, st.o,   rf2,   rb3,   TEST_DATA,          0x020,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF         6, st.o,   rf2,   rb3,   TEST_DATA,          0x028,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF         7, st.o,   rf2,   rb3,   TEST_DATA,          0x030,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- boundary ----
	TEST_ST_RF         8, st.o,   rf2,   rb3,   TEST_DATA,          0x050,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF         9, st.o,   rf2,   rb3,   TEST_DATA,          0x068,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF        10, st.o,   rf2,   rb3,   TEST_DATA,          0x078,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF        11, st.o,   rf2,   rb3,   TEST_DATA,          0x080,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF        12, st.o,   rf2,   rb4,   TEST_DATA + 0x800,  -0x008,   0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- overlap ----
	TEST_ST_RF        13, st.o,   rf2,   rb5,   TEST_DATA,          0x058,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RF        14, st.o,   rf2,   rb6,   TEST_DATA,          0x060,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	TEST_ST_RF  15, st.o,    rf5,   rb6,   MSTORE + 0x1C0,   0x000,    0x7FFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF
	TEST_ST_RF  16, st.o,    rf5,   rb6,   MSTORE + 0x1C8,   0x000,    0x8000000000000000, 0x8000000000000000
	TEST_ST_RF  17, st.o,    rf5,   rb6,   MSTORE + 0x1D0,   0x000,    0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
	@@   ^ 三条各在 MSTORE + 0x1C0/0x1C8/0x1D0 写一个数据单元（值 = TEST_DATA + 0x028/0x020/0x088 的 64 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0n]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零（死的预设数据槽）
	.org	0x2040
__rb0n:
	st.o     rf5, [rb0, -0x040]		@@ 被测 @0x2040：EA = 0x2000 + 0
	__CHECK_MEM 18, (ENTRY + 0x2000), 0, 0x1111111111111111	@@ 负档槽（零）只被写低 64 位
__rb0n_ck:
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	@@ 被测 @0x20D0：EA = 自身指令地址（宏内预读 8 字节数据单元、只改高 32 位后写回）
	__CHECK_RD_ST_IP 19, st.o, rf5, rf
__rb0z_ck:
	set.fo	rf5, 0x1111111111111111
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	st.o     rf5, [rb0, 0x008]		@@ 被测 @0x2180：EA = 0x2188 + 0
	jump	[rb0, __rb0p_ck]
	.org	0x2188
	@@ 正档槽：0x2188..0x2190 由 `.org` 填零
	.org	0x2190
__rb0p_ck:
	__CHECK_MEM 20, (ENTRY + 0x2188), 0, 0x1111111111111111

	@@ ==== m17-testcases-004：rf0 作源（`spec/SimRISC-00 §2.3.1` 位域独立派生期望）====
	@@ `set.w rf0, wp0/wp2` 只写 [4:0] 异常状态 / [33:32] 舍入模式；其余位（只读 qNaN 与 SBZ）保持。
	@@ 期望 = [63:51]0b0111111111111 | [50:34]0 | [33:32]00 | [31:22]0b0111111111 | [21:0]0
	@@      = 0x7FF8_0000_7FC0_0000（任务书原文 0x7FF8_00FF_C000_0000 在 [39:32] 置 1，
	@@        与 [50:34] SBZ 冲突；见本任务书「待裁定」）。
	set.w	rf0, wp0, 0x0000		@@ 清异常状态 [4:0]
	set.w	rf0, wp2, 0x0000		@@ 舍入模式 [33:32] = 00（RNE）
	set.rb	rb3, TEST_DATA
	st.o	rf0, [rb3, 0x038]		@@ rf0 作源合法，读出整 64 位
	__CHECK_MEM 21, TEST_DATA, 0x038, 0x7FF800007FC00000
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        22, st.o,   rf1,   MALIGN, rb3,                TEST_DATA, 0x004  @@ EA 未按 8 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        23, st.o,   rf1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
