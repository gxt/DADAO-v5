@@ ld.t_rrii_rf.S — ld.t rfHA, [rbHB, imms12]（rrii, opc 0x16）
@@ 大类：01-load-store（取数存数，`spec/SimRISC-01 §1`）
@@ id：ld.t_rrii_rf　形式：rrii　opc：0x16　mask：0xFF000000
@@ 语义：目的 ← zero_extend(mem[EA])；EA = rb[47:0] + imms12（大端；32 位零扩展）
@@ 对齐：EA 需 4 B 自然对齐，未对齐 ⇒ MALIGN
@@ 合法性：该银行 0 号寄存器可作目的（无 dst_0 限制）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA（24 个 8 字节 beat，字面量见该文件）
@@ 用例：encoding 2 / legality 2 / semantic 5 / boundary 9 / overlap 2 / rb0 3（链例 21 + 故障例 2；镜像 = 每 `.S` 一个：链例 + 全部故障例顺序跑，`-defsym CASE_N=<点号>` = 调试用单例模式）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/01-load-store/01-load-store.inc"

@@ ---- 文件专用宏（m15-testcases-002 下沉；只被本文件使用）----
@@ rf 目的，只比低 32 位（ld.t 存单精：高 32 位不做特殊规定 ⇒ 不据以判失败）
.macro TEST_LD_RF_LO32 pt, mnem, dst, base, baseval, off, exp
	LOAD_ADDR \base, \baseval
	\mnem	\dst, [\base, \off]
	rf2rd	{rd21:rd21}, {\dst:\dst}
	ext.uo	rd21, rd21, 31
	set.rd	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

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


	@@ ==== m15-testcases-010 追补：boundary 极值 + rb0 作基址三档 ====
	@@ ---- boundary：宽度极值（正向极大 / 负向极小 / 全 1；取自 TEST_DATA 现有 beat）----
	@@   `ld.t`/`ldm.t` 只写低 32 位 ⇒ 目的先清 0（高 32 位保持 0）
	set.fo	rf5, 0x0000000000000000
	TEST_LD_RF_LO32  16, ld.t,    rf5,   rb6,   TEST_DATA,          0x028,    0x000000007FFFFFFF
	TEST_LD_RF_LO32  17, ld.t,    rf5,   rb6,   TEST_DATA,          0x020,    0x0000000080000000
	TEST_LD_RF_LO32  18, ld.t,    rf5,   rb6,   TEST_DATA,          0x088,    0x00000000FFFFFFFF

	@@ ---- rb0 作基址：imm 负 / 零 / 正三档（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址**，非「下一条」）----
	@@   槽与被测指令都由 `.org` 钉住：llvm-mc 把标签差折成 0（ISS-424）⇒ imm 只能写字面常量；
	@@   负档 EA = ENTRY+0x2000（死的预设数据槽）、零档 EA = 被测指令自身地址、正档 EA = ENTRY+0x2188。
	@@ `ld.t` 只写低 32 位 ⇒ 目的/读回寄存器先清 0
	set.fo	rf5, 0x0000000000000000
	set.fo	rf13, 0x0000000000000000
	jump	[rb0, __rb0n]
	.org	0x2000
	.dd.o64	0x8000000000000000	@@ 负档槽（死数据；各宽度取首字节/半字/字 = 负向极小）
	.org	0x2040
__rb0n:
	ld.t     rf5, [rb0, -0x040]		@@ 被测 @0x2040：EA = 0x2000
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD 19, rd21, 0x0000000080000000	@@ 负向极小
__rb0n_ck:
	jump	[rb0, __rb0z]
	.org	0x20C4
__rb0z:
	@@ 被测 @0x20C8：EA = 自身指令地址（宏内 aip.si @0x20C4 + 显式基址 +4 读回）
	__CHECK_RD_IP 20, ld.t, rf5, rf13, rf
__rb0z_ck:
	jump	[rb0, __rb0p]
	.org	0x2180
__rb0p:
	ld.t     rf5, [rb0, 0x008]		@@ 被测 @0x2180：EA = 0x2188（正档槽）
	jump	[rb0, __rb0p_ck]
	.org	0x2188
	.dd.o64	0x7FFFFFFFFFFFFFFF	@@ 正档槽（死数据；各宽度取首字节/半字/字 = 正向极大）
__rb0p_ck:
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD 21, rd21, 0x000000007FFFFFFF	@@ 正向极大
	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	TEST_FAULT        22, ld.t,   rf1,   MALIGN, rb3,                TEST_DATA, 0x002  @@ EA 未按 4 B 自然对齐 ⇒ MALIGN
	TEST_FAULT        23, ld.t,   rf1,   CFXMEM, rb3,                0x0,      0x000  @@ EA=0（cfxha 0 段无 RAM）⇒ CFXMEM

	__TEST_SECTIONS
