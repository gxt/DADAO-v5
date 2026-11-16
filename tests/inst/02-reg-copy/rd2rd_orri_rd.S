@@ rd2rd_orri_rd.S — rd2rd {rdHB:rdHB+immu6-1}, {rdHC:rdHC+immu6-1}（orri, opc 0x40, ha 0x2C）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rd2rd_orri_rd　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40B00000
@@ 语义：rd[HB..HB+n-1] ← rd[HC..HC+n-1]，逐元素 64 位二进制不变（n = immu6，1..63）
@@ 合法性：目的起始为 rd0 ⇒ ILLI；immu6=0 ⇒ ILLI；起始+immu6>64 ⇒ ILLI（两侧）；源/目的范围
@@   有任何交集 ⇒ ILLI（`mreg_range_overlap`，含完全重合）—— 同组复制因此最多 31 个元素
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（装载源）/ SCRATCH（组实测落点）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 1（链例 11 + 故障例 6）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高两个寄存器作源/目的（字段边界）
	set.rd	rd62, 0x0123456789ABCDEF
	TEST_MOV1           1, rd2rd, rd63, rd62, 0x0123456789ABCDEF
	@@ 规范编码字（dst=rd5, src=rd6, immu6=1）直接执行：钉住 mask/value
	set.rd	rd6, 0x5555555555555555
	.dd.t32	0x40B05181
	__CHECK_RD          2, rd5, 0x5555555555555555

	@@ ---- semantic ----
	set.rd	rd5, 0x1111111111111111
	TEST_MOV1           3, rd2rd, rd10, rd5, 0x1111111111111111
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x8000000000000000
	rd2rd	{rd10:rd11}, {rd5:rd6}
	__VERIFY_RD         4, rd10, 0xFFFFFFFFFFFFFFFF
	__CHECK_RD          4, rd11, 0x8000000000000000
	set.rd	rd5, 0x0000000000000001
	set.rd	rd6, 0xFEDCBA9876543210
	set.rd	rd7, 0x7FFFFFFFFFFFFFFF
	rd2rd	{rd10:rd12}, {rd5:rd7}
	__VERIFY_RD         5, rd10, 0x0000000000000001
	__VERIFY_RD         5, rd11, 0xFEDCBA9876543210
	__CHECK_RD          5, rd12, 0x7FFFFFFFFFFFFFFF
	@@ 多元素（7 个连续寄存器，值逐元素可辨）
	set.rd	rd9, 0x0000000000000000
	set.rd	rd10, 0x0000000000000001
	set.rd	rd11, 0x0000000000000002
	set.rd	rd12, 0x0000000000000003
	set.rd	rd13, 0x0000000000000004
	set.rd	rd14, 0x0000000000000005
	set.rd	rd15, 0x0000000000000006
	rd2rd	{rd24:rd30}, {rd9:rd15}
	__VERIFY_RD         6, rd24, 0x0000000000000000
	__VERIFY_RD         6, rd27, 0x0000000000000003
	__CHECK_RD          6, rd30, 0x0000000000000006
	@@ 源含 rd0（硬连零，读 0）：逐元素照搬
	set.rd	rd1, 0x0000000000001234
	rd2rd	{rd17:rd18}, {rd0:rd1}
	__VERIFY_RD         7, rd17, 0x0000000000000000
	__CHECK_RD          7, rd18, 0x0000000000001234

	@@ ---- boundary ----
	@@ 目的恰在寄存器组顶端
	set.rd	rd60, 0x0F1E2D3C4B5A6978
	set.rd	rd61, 0xAAAAAAAAAAAAAAAA
	rd2rd	{rd62:rd63}, {rd60:rd61}
	__VERIFY_RD         8, rd62, 0x0F1E2D3C4B5A6978
	__CHECK_RD          8, rd63, 0xAAAAAAAAAAAAAAAA
	@@ 源恰在寄存器组顶端
	rd2rd	{rd60:rd61}, {rd62:rd63}
	__VERIFY_RD         9, rd60, 0x0F1E2D3C4B5A6978
	__CHECK_RD          9, rd61, 0xAAAAAAAAAAAAAAAA
	@@ 目的在源之前、两段相邻不相交（合法的另一侧）
	set.rd	rd8, 0x00000000FFFFFFFF
	set.rd	rd9, 0x000000000000FFFF
	rd2rd	{rd5:rd6}, {rd8:rd9}
	__VERIFY_RD        10, rd5, 0x00000000FFFFFFFF
	__CHECK_RD         10, rd6, 0x000000000000FFFF
	@@ 最大合法元素个数（同组不许重叠 ⇒ 2n ≤ 63 ⇒ n ≤ 31）
	set.rd	rd37, 0xAAAAAAAAAAAAAAAA
	set.rd	rd62, 0x0123456789ABCDEF
	rd2rd	{rd1:rd31}, {rd32:rd62}
	__VERIFY_RD        11, rd6, 0xAAAAAAAAAAAAAAAA
	__CHECK_RD         11, rd31, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器对 rd2rd 放行该编码，故用助记符形式）
	TEST_FAULT_MOV        12, rd2rd, {rd0}, ILLI, {rd1}
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        13, ILLI, 0x40B010C0, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x40B3F042, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        15, ILLI, 0x40B01FC2, rb3, TEST_DATA, rd19, 0x000
	@@ 源/目的范围部分交错（dst 3..4 / src 2..3）⇒ ILLI（mreg_range_overlap）
	TEST_FAULT_ENC        16, ILLI, 0x40B03082, rb3, TEST_DATA, rd19, 0x000
	@@ 源/目的范围完全重合（dst 3 / src 3）⇒ ILLI（含完全重合）
	TEST_FAULT_ENC        17, ILLI, 0x40B030C1, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
