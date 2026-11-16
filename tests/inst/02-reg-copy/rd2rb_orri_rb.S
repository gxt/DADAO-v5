@@ rd2rb_orri_rb.S — rd2rb {rbHB:rbHB+immu6-1}, {rdHC:rdHC+immu6-1}（orri, opc 0x40, ha 0x35）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rd2rb_orri_rb　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40D40000
@@ 语义：rb[HB..HB+n-1] ← rd[HC..HC+n-1]，逐元素 64 位二进制不变（n = immu6，1..63）
@@ 合法性：目的起始为 rb0 ⇒ ILLI（rb0 = 当前 IP）；immu6=0 ⇒ ILLI；起始+immu6>64 ⇒ ILLI（两侧）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（装载源）/ SCRATCH（组实测落点，rb29 指）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 1（链例 11 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高寄存器作目的、RD 组顶端作源（字段边界）
	set.rd	rd62, 0x0123456789ABCDEF
	TEST_MOV1           1, rd2rb, rb63, rd62, 0x0123456789ABCDEF
	@@ 规范编码字（dst=rb5, src=rd6, immu6=1）直接执行：钉住 mask/value
	set.rd	rd6, 0x5555555555555555
	.dd.t32	0x40D45181
	st.o	rb5, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x5555555555555555

	@@ ---- semantic ----
	set.rd	rd5, 0x1111111111111111
	TEST_MOV1           3, rd2rb, rb10, rd5, 0x1111111111111111
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x8000000000000000
	rd2rb	{rb10:rb11}, {rd5:rd6}
	st.o	rb10, [rb29, 0]
	__VERIFY_MEM        4, SCRATCH, 0, 0xFFFFFFFFFFFFFFFF
	st.o	rb11, [rb29, 0]
	__CHECK_MEM         4, SCRATCH, 0, 0x8000000000000000
	set.rd	rd5, 0x0000000000000001
	set.rd	rd6, 0xFEDCBA9876543210
	set.rd	rd7, 0x7FFFFFFFFFFFFFFF
	rd2rb	{rb10:rb12}, {rd5:rd7}
	st.o	rb10, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0x0000000000000001
	st.o	rb11, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0xFEDCBA9876543210
	st.o	rb12, [rb29, 0]
	__CHECK_MEM         5, SCRATCH, 0, 0x7FFFFFFFFFFFFFFF
	@@ 多元素（7 个连续寄存器，值逐元素可辨）
	set.rd	rd5, 0x0000000000000000
	set.rd	rd6, 0x0000000000000001
	set.rd	rd7, 0x0000000000000002
	set.rd	rd8, 0x0000000000000003
	set.rd	rd9, 0x0000000000000004
	set.rd	rd10, 0x0000000000000005
	set.rd	rd11, 0x0000000000000006
	rd2rb	{rb12:rb18}, {rd5:rd11}
	st.o	rb12, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000000
	st.o	rb15, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000003
	st.o	rb18, [rb29, 0]
	__CHECK_MEM         6, SCRATCH, 0, 0x0000000000000006
	@@ 源含 rd0（硬连零，读 0）：逐元素照搬
	set.rd	rd1, 0x0000000000001234
	rd2rb	{rb17:rb18}, {rd0:rd1}
	st.o	rb17, [rb29, 0]
	__VERIFY_MEM        7, SCRATCH, 0, 0x0000000000000000
	st.o	rb18, [rb29, 0]
	__CHECK_MEM         7, SCRATCH, 0, 0x0000000000001234

	@@ ---- boundary ----
	@@ 源恰在 RD 组顶端
	set.rd	rd62, 0x0F1E2D3C4B5A6978
	set.rd	rd63, 0xAAAAAAAAAAAAAAAA
	rd2rb	{rb60:rb61}, {rd62:rd63}
	st.o	rb60, [rb29, 0]
	__VERIFY_MEM        8, SCRATCH, 0, 0x0F1E2D3C4B5A6978
	st.o	rb61, [rb29, 0]
	__CHECK_MEM         8, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	@@ 目的恰在 RB 组顶端（源仍为 RD 组顶端的两个值）
	rd2rb	{rb62:rb63}, {rd62:rd63}
	st.o	rb62, [rb29, 0]
	__VERIFY_MEM        9, SCRATCH, 0, 0x0F1E2D3C4B5A6978
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         9, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	@@ overlap（跨组结构性不可能相交）：源/目的同号（rd5 / rb5）照常复制
	set.rd	rd5, 0x0123456789ABCDEF
	TEST_MOV1          10, rd2rb, rb5, rd5, 0x0123456789ABCDEF
	@@ 最大元素个数 63（跨组）：目的段覆盖结果/落点寄存器 ⇒ 复制后重装 rb29/rb30 再核对
	@@ 目的 rb1..rb63 ← 源 rd1..rd63（同号对应：rb6 ← rd6、rb63 ← rd63）
	set.rd	rd6, 0xAAAAAAAAAAAAAAAA
	set.rd	rd63, 0x0123456789ABCDEF
	rd2rb	{rb1:rb63}, {rd1:rd63}
	LOAD_ADDR rb29, SCRATCH
	LOAD_ADDR rb30, TEST_BUF + (8 * __NCHECK)
	st.o	rb6, [rb29, 0]
	__VERIFY_MEM       11, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	st.o	rb63, [rb29, 0]
	__CHECK_MEM        11, SCRATCH, 0, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rb0 ⇒ ILLI（dst_rb0；汇编器对 rd2rb 放行该编码）
	TEST_FAULT_MOV        12, rd2rb, {rb0}, ILLI, {rd1}
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        13, ILLI, 0x40D410C0, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x40D7F042, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        15, ILLI, 0x40D41FC2, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
