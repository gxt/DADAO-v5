@@ st.o_rrii_rd.S — st.o rdHA, [rbHB, imms12]（rrii, opc 0x21）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.o_rrii_rd　形式：rrii　opc：0x21　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器低 64 位；EA = rb[47:0] + imms12（大端）；只改这几条字节通道，beat 其余字节保持
@@ 对齐：EA 需 8 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：源 0 号寄存器：rd0 读出 0（合法）；无 dst_0 限制。基址可用 rb0（= 当前指令地址）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 5 / semantic 5 / boundary 5 / overlap 2 / rb0 1（链例 16 + 故障例 4；故障例一例一镜像，`-defsym CASE_N=<点号>`）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ rb0 段（`spec/SimRISC-00 §2`：rb0 = 当前指令地址）：本 id 的**数据源在 rd 银行**，
@@   rb0 只能作**基址**（`rbhb`，role = src）⇒ EA = 本条 st.o 地址 + imms12；`.org` 钉住
@@   被测指令与零填充槽位，两侧都是链接期常量，落点只写不执行。

	.include "tests/inst/macros/inst_test.inc"

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
	LOAD_ADDR rb3, TEST_DATA
	st.o  	rd0, [rb3, 0x070]
	__CHECK_MEM 15, TEST_DATA, 0x070, 0x0000000000000000

	@@ ---- rb0 作基址（rbhb：role = src ⇒ EA = 本条 st.o 的地址 + imms12）----
	@@ 目标槽是「被 jump 跳过的 .text 零填充」：只被写、不被执行（每例独立 8 B）；
	@@ delta = 槽地址 − 被测 st.o 地址（本段两例均 −0x40），`.org` 把两侧都钉住。
	__LI	rd2, 0xDEADBEEFCAFEF00D
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

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	TEST_FAULT        17, st.o,   rd1,   MALIGN, rb3,                TEST_DATA, 0x004  @@ EA 未按 8 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        18, st.o,   rd1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM
	TEST_FAULT        19, st.o,   rd1,   CFXMEM, rb3,                0x7C0000000000, 0x000  @@ reserved cfx 地址空间（addr[47:42]=31）上的普通访存 ⇒ CFXMEM
	TEST_FAULT        20, st.o,   rd1,   CFXMEM, rb3,                0xF40000000000, 0x000  @@ reserved cfx 地址空间（addr[47:42]=61）上的普通访存 ⇒ CFXMEM

	__TEST_SECTIONS
