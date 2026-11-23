@@ st.o_rrii_rb.S — st.o rbHA, [rbHB, imms12]（rrii, opc 0x23）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：st.o_rrii_rb　形式：rrii　opc：0x23　mask：0xFF000000
@@ 语义：mem[EA] ← 源寄存器整 64 位；EA = rb[47:0] + imms12（大端）；整 8 字节全部写入
@@ 对齐：EA 需 8 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：源 0 号寄存器：rb0 读出**当前指令地址**（合法，见下方 rb0 段）；无 dst_0 限制
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节数据单元，字面量见该文件）
@@ 用例：encoding 2 / legality 2 / semantic 5 / boundary 8 / overlap 2 / rb0 6（链例 23 + 故障例 2；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ rb0 段（`spec/SimRISC-00 §2`：rb0 读出 = **当前正在执行的指令地址**，非 PC+4）：
@@   期望值不能写链接期常量（llvm-mc 只折装绝对常量，标签差静默折 0，`ISS-424`）⇒
@@   方式一 `aip.si rbX, 0` 取自身 IP + `add.si` 补字节差（探针不借被测 st）；
@@   方式二 `rb2rb rbX, rb0, 1` 直接拷出 IP；最后一例用 `.org` 钉住地址写绝对常量，
@@   防止「两条 IP 通路同错也自洽」。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

@@ ---- 文件专用宏（m15-testcases-002 下沉；只被本文件使用）----
@@ 内存实测 vs **运行期派生**的期望（RB 银行，如 `aip.si`/`rb2rb` 取出的 IP）：
@@   期望先 `rb2rd` 搬到 rd22 再比 —— 探针不借被测的 `st` 指令，也不要求链接期常量
@@   （`st.o rb0` 的期望值随链接布局变化，见 `tests/inst/MIGRATION.md §6`）。
.macro __CHECK_MEM_RB pt, baseval, off, rbsrc
	rb2rd	{rd22:rd22}, {\rbsrc:\rbsrc}
	set.rb rb21, (((\baseval) + (\off)) / 8) * 8
	ld.o	rd21, [rb21, 0]
	__REC	rd21
	br.eq	{rd22, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ rb 源
.macro TEST_ST_RB pt, mnem, src, base, baseval, off, srcval, unit
	set.rb	\src, \srcval
	set.rb \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \unit
.endm

	__TEST_BEGIN

	@@ ---- encoding ----
	TEST_ST_RB         1, st.o,   rb63,  rb62,  TEST_DATA,          0x0B8,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB         2, st.o,   rb1,   rb2,   TEST_DATA + 0x008,  0x0A8,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- semantic ----
	TEST_ST_RB         3, st.o,   rb2,   rb3,   TEST_DATA,          0x010,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB         4, st.o,   rb2,   rb3,   TEST_DATA,          0x018,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB         5, st.o,   rb2,   rb3,   TEST_DATA,          0x020,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB         6, st.o,   rb2,   rb3,   TEST_DATA,          0x028,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB         7, st.o,   rb2,   rb3,   TEST_DATA,          0x030,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- boundary ----
	TEST_ST_RB         8, st.o,   rb2,   rb3,   TEST_DATA,          0x050,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB         9, st.o,   rb2,   rb3,   TEST_DATA,          0x068,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB        10, st.o,   rb2,   rb3,   TEST_DATA,          0x078,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB        11, st.o,   rb2,   rb3,   TEST_DATA,          0x080,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D
	TEST_ST_RB        12, st.o,   rb2,   rb4,   TEST_DATA + 0x800,  -0x008,   0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- overlap ----
	@@ overlap：源 rb5 = 基址 rb5（真同名）⇒ 存入的值就是该地址本身
	TEST_ST_RB        13, st.o,   rb5,   rb5,   TEST_DATA + 0x088,  0x000,    TEST_DATA + 0x088,  TEST_DATA + 0x088
	TEST_ST_RB        14, st.o,   rb2,   rb6,   TEST_DATA,          0x060,    0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- rb0 作源：存入「当前指令地址」（`spec/SimRISC-00 §2`）----
	@@ 方式一：`aip.si rbX, 0`（imms30 = 0 合法）⇒ rbX = 该 aip.si **自身**地址；
	@@   delta = 被测 st.o 地址 − aip.si 地址。本段布局 aip.si(A) / add.si(A+4) / st.o(A+8)
	@@   ⇒ delta = 8（4 B × 2 条；注释与指令序列逐条对应，改序须同步改 delta）
	set.rb rb3, TEST_DATA
	aip.si	rb12, 0
	add.si	rb12, 8
	st.o	rb0, [rb3, 0x040]
	__CHECK_MEM_RB     15, TEST_DATA, 0x040, rb12      @@ 数据单元（8 字节） == IP 派生期望（方式一）

	@@ 方式二：`rb2rb rbX, rb0, 1` 直接拷出 rb0；布局 rb2rb(B) / add.si(B+4) / st.o(B+8)
	@@   ⇒ delta = 8 ⇒ rb13 = 被测 st.o 的地址
	rb2rb	{rb13:rb13}, {rb0:rb0}
	add.si	rb13, 8
	st.o	rb0, [rb3, 0x058]
	__CHECK_MEM_RB     16, TEST_DATA, 0x058, rb13      @@ 数据单元（8 字节） == IP 派生期望（方式二）

	@@ 链接期绝对期望：`.org 0x1800` 把被测 st.o 钉住 ⇒ 存入值必须恰为 ENTRY + 0x1800
	@@   （「IP 派生期望」两路同错也自洽，本点用绝对常量再钉一次真实地址）
	jump	[rb0, __rb0_abs]
	.org	0x1800
__rb0_abs:
	st.o	rb0, [rb3, 0x090]
	jump	[rb0, __rb0_abs_ck]
	.org	0x1840
__rb0_abs_ck:
	__CHECK_MEM        17, TEST_DATA, 0x090, (ENTRY + 0x1800)


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 8 字节数据单元）----
	TEST_ST_RB  18, st.o,    rb5,   rb6,   MSTORE + 0x1C0,   0x000,    0x7FFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF
	TEST_ST_RB  19, st.o,    rb5,   rb6,   MSTORE + 0x1C8,   0x000,    0x8000000000000000, 0x8000000000000000
	TEST_ST_RB  20, st.o,    rb5,   rb6,   MSTORE + 0x1D0,   0x000,    0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
	@@   ^ 三条各在 MSTORE + 0x1C0/0x1C8/0x1D0 写一个数据单元（值 = TEST_DATA + 0x028/0x020/0x088 的 64 位分量）

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	set.rb	rb5, 0x1111111111111111
	jump	[rb0, __rb0n]
	.org	0x2000
	@@ 负档槽：0x2000..0x2008 由 `.org` 填零（死的预设数据槽）
	.org	0x2040
__rb0n:
	st.o     rb5, [rb0, -0x040]		@@ 被测 @0x2040：EA = 0x2000 + 0
	__CHECK_MEM 21, (ENTRY + 0x2000), 0, 0x1111111111111111	@@ 负档槽（零）只被写低 64 位
__rb0n_ck:
	set.rb	rb5, 0x1111111111111111
	jump	[rb0, __rb0z]
	.org	0x20C0
__rb0z:
	@@ 被测 @0x20D0：EA = 自身指令地址（宏内预读 8 字节数据单元、只改高 32 位后写回）
	__CHECK_RD_ST_IP 22, st.o, rb5, rb
__rb0z_ck:
	set.rb	rb5, 0x1111111111111111
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	st.o     rb5, [rb0, 0x008]		@@ 被测 @0x2180：EA = 0x2188 + 0
	jump	[rb0, __rb0p_ck]
	.org	0x2188
	@@ 正档槽：0x2188..0x2190 由 `.org` 填零
	.org	0x2190
__rb0p_ck:
	__CHECK_MEM 23, (ENTRY + 0x2188), 0, 0x1111111111111111
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        24, st.o,   rb1,   MALIGN, rb3,                TEST_DATA, 0x004  @@ EA 未按 8 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        25, st.o,   rb1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
