@@ st.o_rrii_rd.S — st.o rdHA, [rbHB, imms12]（rrii, opc 0x21）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.o_rrii_rd　形式：rrii　opc：0x21　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器整 64 位；EA = rb[47:0] + imms12（大端）；整 8 字节全部写入
@@ 对齐：EA 需 8 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：源 0 号寄存器：rd0 读出 0（合法）；无 dst_0 限制。基址可用 rb0（= 当前指令地址）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节数据单元，字面量见该文件）
@@ 用例：encoding 2 / legality 5 / semantic 5 / boundary 8 / overlap 2 / rb0 4（链例 22 + 故障例 4；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ rb0 段（`spec/SimRISC-00 §2`：rb0 = 当前指令地址）：本 id 的**数据源在 rd 银行**，
@@   rb0 只能作**基址**（`rbhb`，role = src）⇒ EA = 本条 st.o 地址 + imms12；`.org` 钉住
@@   被测指令与零填充槽位，两侧都是链接期常量，落点只写不执行。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_ST            1, st.o,   rd63,  rb63,  TEST_DATA,          0x0B8,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST            2, st.o,   rd1,   rb1,   TEST_DATA + 0x008,  0x0A8,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- semantic ----
	TEST_ST            3, st.o,   rd2,   rb3,   TEST_DATA,          0x010,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST            4, st.o,   rd2,   rb3,   TEST_DATA,          0x018,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST            5, st.o,   rd2,   rb3,   TEST_DATA,          0x020,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST            6, st.o,   rd2,   rb3,   TEST_DATA,          0x028,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST            7, st.o,   rd2,   rb3,   TEST_DATA,          0x030,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- boundary ----
	TEST_ST            8, st.o,   rd2,   rb3,   TEST_DATA,          0x050,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST            9, st.o,   rd2,   rb3,   TEST_DATA,          0x068,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST           10, st.o,   rd2,   rb3,   TEST_DATA,          0x078,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST           11, st.o,   rd2,   rb3,   TEST_DATA,          0x080,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST           12, st.o,   rd2,   rb4,   TEST_DATA + 0x800,  -0x008,   0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- overlap ----
	TEST_ST           13, st.o,   rd2,   rb5,   TEST_DATA,          0x058,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST           14, st.o,   rd2,   rb6,   TEST_DATA,          0x060,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- legality ----
	@@ legality：st 允许 rd0 作源（读出 0），不是 ILLI
	set.rb rb3, TEST_DATA
	st.o  	rd0, [rb3, 0x070]
	__CHECK_MEM 15, TEST_DATA, 0x070, 0x0000000000000000

	@@ ---- rb0 作基址（rbhb：role = src ⇒ EA = 本条 st.o 的地址 + imms12）----
	@@ 目标槽是「被 jump 跳过的 .text 零填充」：只被写、不被执行（每例独立 8 B）；
	@@ delta = 槽地址 − 被测 st.o 地址（本段两例均 −0x40），`.org` 把两侧都钉住。
	set.rd	rd2, 0xDEADBEEFCAFEF00D
	jump	[rb0, __rb0b_a]
	.org	0x1300
	@@ 槽 A：ENTRY+0x1300（零填充；写入落点）
	.org	0x1340
__rb0b_a:                                @@ ENTRY+0x1340：被测 st.o
	st.o	rd2, [rb0, -0x40]           @@ EA = 0x1340 − 0x40 = 0x1300
	jump	[rb0, __rb0b_b]
	.org	0x1380
	@@ 槽 B：ENTRY+0x1380（零填充）
	.org	0x13C0
__rb0b_b:                                @@ ENTRY+0x13C0：被测 st.o
	st.o	rd2, [rb0, -0x40]           @@ EA = 0x13C0 − 0x40 = 0x1380
	jump	[rb0, __rb0b_ck]
	.org	0x1400
__rb0b_ck:
	__VERIFY_MEM      16, ENTRY + 0x1300, 0, 0xDEADBEEFCAFEF00D
	__CHECK_MEM       16, ENTRY + 0x1380, 0, 0xDEADBEEFCAFEF00D


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	TEST_ST    17, st.o,    rd5,   rb6,   MSTORE + 0x1C0,   0x000,    0x7FFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF
	TEST_ST    18, st.o,    rd5,   rb6,   MSTORE + 0x1C8,   0x000,    0x8000000000000000, 0x8000000000000000
	TEST_ST    19, st.o,    rd5,   rb6,   MSTORE + 0x1D0,   0x000,    0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
	@@   ^ 三条各写 MSTORE + 0x1C0/0x1C8/0x1D0 一拍（值 = TEST_DATA + 0x028/0x020/0x088 的 64 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0n]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零（死的预设数据槽）
	.org	0x2040
__rb0n:
	st.o     rd5, [rb0, -0x040]		@@ 被测 @0x2040：EA = 0x2000 + 0
	__CHECK_MEM 20, (ENTRY + 0x2000), 0, 0x1111111111111111	@@ 负档槽（零）只被写低 64 位
__rb0n_ck:
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	@@ 被测 @0x20D0：EA = 自身指令地址（宏内预读 8 B 拍、只改高 32 位后写回）
	__CHECK_RD_ST_IP 21, st.o, rd5, rd
__rb0z_ck:
	set.rd	rd5, 0x1111111111111111
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	st.o     rd5, [rb0, 0x008]		@@ 被测 @0x2180：EA = 0x2188 + 0
	jump	[rb0, __rb0p_ck]
	.org	0x2188
	@@ 正档槽：0x2188..0x2190 由 `.org` 填零
	.org	0x2190
__rb0p_ck:
	__CHECK_MEM 22, (ENTRY + 0x2188), 0, 0x1111111111111111
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        23, st.o,   rd1,   MALIGN, rb3,                TEST_DATA, 0x004  @@ EA 未按 8 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        24, st.o,   rd1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT        25, st.o,   rd1,   CFXMEM, rb3,                0x7C0000000000, 0x000  @@ reserved cfx 地址空间（addr[47:42]=31）上的普通访存 ⇒ CFXMEM
	TEST_FAULT        26, st.o,   rd1,   CFXMEM, rb3,                0xF40000000000, 0x000  @@ reserved cfx 地址空间（addr[47:42]=61）上的普通访存 ⇒ CFXMEM

	__TEST_SECTIONS
