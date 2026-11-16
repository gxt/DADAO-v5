@@ rd2ra_orri_ra.S — rd2ra {raHB:raHB+immu6-1}, {rdHC:rdHC+immu6-1}（orri, opc 0x40, ha 0x2D）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rd2ra_orri_ra　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40B40000
@@ 语义：ra[HB..HB+n-1] ← rd[HC..HC+n-1]，逐元素 64 位二进制不变（含 RA 高 16 位）
@@ 合法性：目的 ra0 合法（RACNT/MRPTR，`SimRISC-00 §2.4`）；immu6=0 ⇒ ILLI；起始+immu6>64 ⇒ ILLI（两侧）；
@@   跨组复制（RD → RA）结构上不可能相交 ⇒ `mreg_range_overlap` 不适用
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（装载源）/ SCRATCH（组实测落点，rb29 指）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / legality 2 / boundary 2 / overlap 1（链例 12 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高两个寄存器作目的/源（字段边界）
	__LI	rd62, 0x0123456789ABCDEF
	TEST_MOV1           1, rd2ra, ra63, rd62, 0x0123456789ABCDEF
	@@ 规范编码字（dst=ra5, src=rd6, immu6=1）直接执行：钉住 mask/value
	__LI	rd6, 0x5555555555555555
	.dd.t32	0x40B45181
	st.o	ra5, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x5555555555555555

	@@ ---- semantic ----
	__LI	rd5, 0x1111111111111111
	TEST_MOV1           3, rd2ra, ra10, rd5, 0x1111111111111111
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x8000000000000000
	rd2ra	{ra10:ra11}, {rd5:rd6}
	st.o	ra10, [rb29, 0]
	__VERIFY_MEM        4, SCRATCH, 0, 0xFFFFFFFFFFFFFFFF
	st.o	ra11, [rb29, 0]
	__CHECK_MEM         4, SCRATCH, 0, 0x8000000000000000
	__LI	rd5, 0x0000000000000001
	__LI	rd6, 0xFEDCBA9876543210
	__LI	rd7, 0x7FFFFFFFFFFFFFFF
	rd2ra	{ra10:ra12}, {rd5:rd7}
	st.o	ra10, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0x0000000000000001
	st.o	ra11, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0xFEDCBA9876543210
	st.o	ra12, [rb29, 0]
	__CHECK_MEM         5, SCRATCH, 0, 0x7FFFFFFFFFFFFFFF
	@@ 多元素（7 个连续寄存器，值逐元素可辨）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0000000000000001
	__LI	rd7, 0x0000000000000002
	__LI	rd8, 0x0000000000000003
	__LI	rd9, 0x0000000000000004
	__LI	rd10, 0x0000000000000005
	__LI	rd11, 0x0000000000000006
	rd2ra	{ra24:ra30}, {rd5:rd11}
	st.o	ra24, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000000
	st.o	ra27, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000003
	st.o	ra30, [rb29, 0]
	__CHECK_MEM         6, SCRATCH, 0, 0x0000000000000006
	@@ 源值零 ⇒ 目的旧值被覆盖（不是「未写」）
	__LI	rd7, 0x0000000000000000
	__LI	rd8, 0x00000000000000FF
	rd2ra	{ra5:ra6}, {rd7:rd8}
	st.o	ra5, [rb29, 0]
	__VERIFY_MEM        7, SCRATCH, 0, 0x0000000000000000
	st.o	ra6, [rb29, 0]
	__CHECK_MEM         7, SCRATCH, 0, 0x00000000000000FF

	@@ ---- legality / boundary ----
	@@ ra0 作目的合法：写 [53:48] = RACNT（本镜像随后不用 call/ret）；写完立即恢复 ra0 = 0
	__LI	rd6, 0x000A000000001234
	rd2ra	{ra0}, {rd6}
	st.o	ra0, [rb29, 0]
	__CHECK_MEM         8, SCRATCH, 0, 0x000A000000001234
	rd2ra	{ra0}, {rd0}
	@@ ra0 作目的、immu6=2（rf0 之外的 0 号寄存器同样合法），后续元素照常赋值
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0123456789ABCDEF
	rd2ra	{ra0:ra1}, {rd5:rd6}
	st.o	ra1, [rb29, 0]
	__CHECK_MEM         9, SCRATCH, 0, 0x0123456789ABCDEF
	rd2ra	{ra0}, {rd0}
	@@ 目的恰在 RA 组顶端
	__LI	rd60, 0x0F1E2D3C4B5A6978
	__LI	rd61, 0xAAAAAAAAAAAAAAAA
	rd2ra	{ra62:ra63}, {rd60:rd61}
	st.o	ra62, [rb29, 0]
	__VERIFY_MEM       10, SCRATCH, 0, 0x0F1E2D3C4B5A6978
	st.o	ra63, [rb29, 0]
	__CHECK_MEM        10, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	@@ overlap（跨组结构性不可能相交）：源/目的同号（rd5 / ra5）照常复制
	__LI	rd5, 0x00000000FFFFFFFF
	TEST_MOV1          11, rd2ra, ra5, rd5, 0x00000000FFFFFFFF
	@@ 最大元素个数 63（跨组）：目的 ra1..ra63 ← 源 rd1..rd63（ra6 ← rd6、ra63 ← rd63）
	__LI	rd6, 0xAAAAAAAAAAAAAAAA
	__LI	rd63, 0x0123456789ABCDEF
	rd2ra	{ra1:ra63}, {rd1:rd63}
	st.o	ra6, [rb29, 0]
	__VERIFY_MEM       12, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	st.o	ra63, [rb29, 0]
	__CHECK_MEM        12, SCRATCH, 0, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        13, ILLI, 0x40B410C0, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x40B7F042, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        15, ILLI, 0x40B41FC2, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
