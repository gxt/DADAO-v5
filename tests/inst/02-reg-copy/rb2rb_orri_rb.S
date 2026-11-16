@@ rb2rb_orri_rb.S — rb2rb {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}（orri, opc 0x40, ha 0x34）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rb2rb_orri_rb　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40D00000
@@ 语义：rb[HB..HB+n-1] ← rb[HC..HC+n-1]，逐元素 64 位二进制不变（n = immu6，1..63）
@@ 合法性：目的起始为 rb0 ⇒ ILLI（rb0 = 当前 IP）；immu6=0 ⇒ ILLI；起始+immu6>64 ⇒ ILLI（两侧）；
@@   源/目的范围有任何交集 ⇒ ILLI（`mreg_range_overlap`，含完全重合）—— 同组复制最多 31 个元素
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（装载源）/ SCRATCH（组实测落点，rb29 指）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 4 / boundary 3 / overlap 1（链例 10 + 故障例 6）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高两个寄存器作源/目的（字段边界）
	__LI_RB	rb62, 0x0123456789ABCDEF
	TEST_MOV1           1, rb2rb, rb63, rb62, 0x0123456789ABCDEF
	@@ 规范编码字（dst=rb5, src=rb6, immu6=1）直接执行：钉住 mask/value
	__LI_RB	rb6, 0x5555555555555555
	.dd.t32	0x40D05181
	st.o	rb5, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x5555555555555555

	@@ ---- semantic ----
	__LI_RB	rb5, 0x1111111111111111
	TEST_MOV1           3, rb2rb, rb10, rb5, 0x1111111111111111
	__LI_RB	rb5, 0xFFFFFFFFFFFFFFFF
	__LI_RB	rb6, 0x8000000000000000
	rb2rb	{rb10:rb11}, {rb5:rb6}
	st.o	rb10, [rb29, 0]
	__VERIFY_MEM        4, SCRATCH, 0, 0xFFFFFFFFFFFFFFFF
	st.o	rb11, [rb29, 0]
	__CHECK_MEM         4, SCRATCH, 0, 0x8000000000000000
	__LI_RB	rb5, 0x0000000000000001
	__LI_RB	rb6, 0xFEDCBA9876543210
	__LI_RB	rb7, 0x7FFFFFFFFFFFFFFF
	rb2rb	{rb10:rb12}, {rb5:rb7}
	st.o	rb10, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0x0000000000000001
	st.o	rb11, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0xFEDCBA9876543210
	st.o	rb12, [rb29, 0]
	__CHECK_MEM         5, SCRATCH, 0, 0x7FFFFFFFFFFFFFFF
	@@ 多元素（7 个连续寄存器，值逐元素可辨）
	__LI_RB	rb5, 0x0000000000000000
	__LI_RB	rb6, 0x0000000000000001
	__LI_RB	rb7, 0x0000000000000002
	__LI_RB	rb8, 0x0000000000000003
	__LI_RB	rb9, 0x0000000000000004
	__LI_RB	rb10, 0x0000000000000005
	__LI_RB	rb11, 0x0000000000000006
	rb2rb	{rb12:rb18}, {rb5:rb11}
	st.o	rb12, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000000
	st.o	rb15, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000003
	st.o	rb18, [rb29, 0]
	__CHECK_MEM         6, SCRATCH, 0, 0x0000000000000006

	@@ ---- boundary ----
	@@ 目的恰在寄存器组顶端
	__LI_RB	rb60, 0x0F1E2D3C4B5A6978
	__LI_RB	rb61, 0xAAAAAAAAAAAAAAAA
	rb2rb	{rb62:rb63}, {rb60:rb61}
	st.o	rb62, [rb29, 0]
	__VERIFY_MEM        7, SCRATCH, 0, 0x0F1E2D3C4B5A6978
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         7, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	@@ 源恰在寄存器组顶端
	rb2rb	{rb60:rb61}, {rb62:rb63}
	st.o	rb60, [rb29, 0]
	__VERIFY_MEM        8, SCRATCH, 0, 0x0F1E2D3C4B5A6978
	st.o	rb61, [rb29, 0]
	__CHECK_MEM         8, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	@@ 目的在源之前、两段相邻不相交（合法的另一侧）
	__LI_RB	rb8, 0x00000000FFFFFFFF
	__LI_RB	rb9, 0x000000000000FFFF
	rb2rb	{rb5:rb6}, {rb8:rb9}
	st.o	rb5, [rb29, 0]
	__VERIFY_MEM        9, SCRATCH, 0, 0x00000000FFFFFFFF
	st.o	rb6, [rb29, 0]
	__CHECK_MEM         9, SCRATCH, 0, 0x000000000000FFFF
	@@ 最大合法元素个数（同组不许重叠 ⇒ 2n ≤ 63 ⇒ n ≤ 31）；目的段含结果/落点寄存器，
	@@ 复制后先按原值重装 rb29（落点）与 rb30（结果缓冲写指针）再核对
	__LI_RB	rb37, 0xAAAAAAAAAAAAAAAA
	__LI_RB	rb62, 0x0123456789ABCDEF
	rb2rb	{rb1:rb31}, {rb32:rb62}
	LOAD_ADDR rb29, SCRATCH
	LOAD_ADDR rb30, TEST_BUF + (8 * __NCHECK)
	st.o	rb6, [rb29, 0]
	__VERIFY_MEM       10, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	st.o	rb31, [rb29, 0]
	__CHECK_MEM        10, SCRATCH, 0, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rb0 ⇒ ILLI（dst_rb0；汇编器对 rb2rb 放行该编码）
	TEST_FAULT_MOV        11, rb2rb, {rb0}, ILLI, {rb1}
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        12, ILLI, 0x40D010C0, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        13, ILLI, 0x40D3F042, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x40D01FC2, rb3, TEST_DATA, rd19, 0x000
	@@ 源/目的范围部分交错（dst 3..4 / src 2..3）⇒ ILLI（mreg_range_overlap）
	TEST_FAULT_ENC        15, ILLI, 0x40D03082, rb3, TEST_DATA, rd19, 0x000
	@@ 源/目的范围完全重合（dst 3 / src 3）⇒ ILLI（含完全重合）
	TEST_FAULT_ENC        16, ILLI, 0x40D030C1, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
