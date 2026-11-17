@@ rb2rd_orri_rb.S — rb2rd {rdHB:rdHB+immu6-1}, {rbHC:rbHC+immu6-1}（orri, opc 0x40, ha 0x36）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rb2rd_orri_rb　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40D80000
@@ 语义：rd[HB..HB+n-1] ← rb[HC..HC+n-1]，逐元素 64 位二进制不变（n = immu6，1..63）
@@ 合法性：目的起始为 rd0 ⇒ ILLI；immu6=0 ⇒ ILLI；起始+immu6>64 ⇒ ILLI（两侧）；
@@   跨组复制（RB → RD）结构上不可能相交 ⇒ `mreg_range_overlap` 不适用
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（装载源）/ SCRATCH（组实测落点，rb29 指）
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 1（链例 11 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高两个寄存器作目的/源（字段边界）
	set.rb	rb62, 0x0123456789ABCDEF
	TEST_MOV1           1, rb2rd, rd63, rb62, 0x0123456789ABCDEF
	@@ 规范编码字（dst=rd5, src=rb6, immu6=1）直接执行：钉住 mask/value
	set.rb	rb6, 0x5555555555555555
	.dd.t32	0x40D85181
	__CHECK_RD          2, rd5, 0x5555555555555555

	@@ ---- semantic ----
	set.rb	rb5, 0x1111111111111111
	TEST_MOV1           3, rb2rd, rd10, rb5, 0x1111111111111111
	set.rb	rb5, 0xFFFFFFFFFFFFFFFF
	set.rb	rb6, 0x8000000000000000
	rb2rd	{rd10:rd11}, {rb5:rb6}
	__VERIFY_RD         4, rd10, 0xFFFFFFFFFFFFFFFF
	__CHECK_RD          4, rd11, 0x8000000000000000
	set.rb	rb5, 0x0000000000000001
	set.rb	rb6, 0xFEDCBA9876543210
	set.rb	rb7, 0x7FFFFFFFFFFFFFFF
	rb2rd	{rd10:rd12}, {rb5:rb7}
	__VERIFY_RD         5, rd10, 0x0000000000000001
	__VERIFY_RD         5, rd11, 0xFEDCBA9876543210
	__CHECK_RD          5, rd12, 0x7FFFFFFFFFFFFFFF
	@@ 多元素（7 个连续寄存器，值逐元素可辨）
	set.rb	rb5, 0x0000000000000000
	set.rb	rb6, 0x0000000000000001
	set.rb	rb7, 0x0000000000000002
	set.rb	rb8, 0x0000000000000003
	set.rb	rb9, 0x0000000000000004
	set.rb	rb10, 0x0000000000000005
	set.rb	rb11, 0x0000000000000006
	rb2rd	{rd24:rd30}, {rb5:rb11}
	__VERIFY_RD         6, rd24, 0x0000000000000000
	__VERIFY_RD         6, rd27, 0x0000000000000003
	__CHECK_RD          6, rd30, 0x0000000000000006
	@@ 源值为零 ⇒ 目的旧值被覆盖（不是「未写」）
	set.rd	rd17, 0xAAAAAAAAAAAAAAAA
	set.rb	rb7, 0x0000000000000000
	rb2rd	{rd17:rd18}, {rb7:rb8}
	__VERIFY_RD         7, rd17, 0x0000000000000000
	__CHECK_RD          7, rd18, 0x0000000000000003

	@@ ---- boundary ----
	@@ 源恰在 RB 组顶端
	set.rb	rb62, 0x0F1E2D3C4B5A6978
	set.rb	rb63, 0xAAAAAAAAAAAAAAAA
	rb2rd	{rd60:rd61}, {rb62:rb63}
	__VERIFY_RD         8, rd60, 0x0F1E2D3C4B5A6978
	__CHECK_RD          8, rd61, 0xAAAAAAAAAAAAAAAA
	@@ 目的恰在 RD 组顶端（源仍为 RB 组顶端的两个值）
	rb2rd	{rd62:rd63}, {rb62:rb63}
	__VERIFY_RD         9, rd62, 0x0F1E2D3C4B5A6978
	__CHECK_RD          9, rd63, 0xAAAAAAAAAAAAAAAA
	@@ overlap（跨组结构性不可能相交）：源/目的同号（rd5 / rb5）照常复制
	set.rb	rb5, 0x0123456789ABCDEF
	TEST_MOV1          10, rb2rd, rd5, rb5, 0x0123456789ABCDEF
	@@ 最大元素个数 63（跨组）：目的 rd1..rd63 ← 源 rb0..rb62（rd6 ← rb5、rd63 ← rb62）
	set.rb	rb5, 0xAAAAAAAAAAAAAAAA
	set.rb	rb62, 0x0123456789ABCDEF
	rb2rd	{rd1:rd63}, {rb0:rb62}
	__VERIFY_RD        11, rd6, 0xAAAAAAAAAAAAAAAA
	__CHECK_RD         11, rd63, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器对 rb2rd 放行该编码）
	TEST_FAULT_MOV        12, rb2rd, {rd0}, ILLI, {rb1}
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        13, ILLI, 0x40D810C0, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x40DBF042, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        15, ILLI, 0x40D81FC2, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
