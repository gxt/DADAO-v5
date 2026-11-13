@@ rd2rf_orri_rf.S — rd2rf {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}（orri, opc 0x40, ha 0x3D）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rd2rf_orri_rf　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40F40000
@@ 语义：rf[HB..HB+n-1] ← rd[HC..HC+n-1]，逐元素 64 位二进制不变
@@ 合法性：目的 rf0 **合法**（FCSR 写掩码只动 [33:32]/[4:0]，`SimRISC-00 §2.3`；含 immu6≥2 的
@@   `{rf0:…}` 组）；immu6=0 ⇒ ILLI；起始+immu6>64 ⇒ ILLI（两侧）；跨组无重叠规则
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（装载源）/ SCRATCH（组实测落点，rb29 指）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 1（链例 12 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 注：rf0 的写内容（FCSR 掩码）不断言——本文件只断言「rf0 作目的不触发 ILLI」与同组后续元素照常赋值

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高两个寄存器作目的/源（字段边界）
	__LI	rd62, 0x0123456789ABCDEF
	TEST_MOV1           1, rd2rf, rf63, rd62, 0x0123456789ABCDEF
	@@ 规范编码字（dst=rf5, src=rd6, immu6=1）直接执行：钉住 mask/value
	__LI	rd6, 0x5555555555555555
	.dd.t32	0x40F45181
	st.o	rf5, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x5555555555555555

	@@ ---- semantic ----
	__LI	rd5, 0x1111111111111111
	TEST_MOV1           3, rd2rf, rf10, rd5, 0x1111111111111111
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x8000000000000000
	rd2rf	{rf10:rf11}, {rd5:rd6}
	st.o	rf10, [rb29, 0]
	__VERIFY_MEM        4, SCRATCH, 0, 0xFFFFFFFFFFFFFFFF
	st.o	rf11, [rb29, 0]
	__CHECK_MEM         4, SCRATCH, 0, 0x8000000000000000
	__LI	rd5, 0x0000000000000001
	__LI	rd6, 0xFEDCBA9876543210
	__LI	rd7, 0x7FFFFFFFFFFFFFFF
	rd2rf	{rf10:rf12}, {rd5:rd7}
	st.o	rf10, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0x0000000000000001
	st.o	rf11, [rb29, 0]
	__VERIFY_MEM        5, SCRATCH, 0, 0xFEDCBA9876543210
	st.o	rf12, [rb29, 0]
	__CHECK_MEM         5, SCRATCH, 0, 0x7FFFFFFFFFFFFFFF
	@@ 多元素（7 个连续寄存器，值逐元素可辨）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0000000000000001
	__LI	rd7, 0x0000000000000002
	__LI	rd8, 0x0000000000000003
	__LI	rd9, 0x0000000000000004
	__LI	rd10, 0x0000000000000005
	__LI	rd11, 0x0000000000000006
	rd2rf	{rf24:rf30}, {rd5:rd11}
	st.o	rf24, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000000
	st.o	rf27, [rb29, 0]
	__VERIFY_MEM        6, SCRATCH, 0, 0x0000000000000003
	st.o	rf30, [rb29, 0]
	__CHECK_MEM         6, SCRATCH, 0, 0x0000000000000006
	@@ 源值零 ⇒ 目的旧值被覆盖（不是「未写」）
	__LI	rd7, 0x0000000000000000
	__LI	rd8, 0x00000000000000FF
	rd2rf	{rf5:rf6}, {rd7:rd8}
	st.o	rf5, [rb29, 0]
	__VERIFY_MEM        7, SCRATCH, 0, 0x0000000000000000
	st.o	rf6, [rb29, 0]
	__CHECK_MEM         7, SCRATCH, 0, 0x00000000000000FF

	@@ ---- boundary ----
	@@ rf0 作目的合法（FCSR 掩码，内容不断言）：组内后续元素照常赋值
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0123456789ABCDEF
	rd2rf	{rf0:rf1}, {rd5:rd6}
	st.o	rf1, [rb29, 0]
	__CHECK_MEM         8, SCRATCH, 0, 0x0123456789ABCDEF
	@@ 目的恰在 RF 组顶端
	__LI	rd60, 0x0F1E2D3C4B5A6978
	__LI	rd61, 0xAAAAAAAAAAAAAAAA
	rd2rf	{rf62:rf63}, {rd60:rd61}
	st.o	rf62, [rb29, 0]
	__VERIFY_MEM        9, SCRATCH, 0, 0x0F1E2D3C4B5A6978
	st.o	rf63, [rb29, 0]
	__CHECK_MEM         9, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	@@ 目的/源都在组顶端、个数 1（字段另一侧边界）
	__LI	rd63, 0x00000000FFFFFFFF
	rd2rf	{rf63}, {rd63}
	st.o	rf63, [rb29, 0]
	__CHECK_MEM        10, SCRATCH, 0, 0x00000000FFFFFFFF
	@@ overlap（跨组结构性不可能相交）：源/目的同号（rd5 / rf5）照常复制
	__LI	rd5, 0x000000000000FFFF
	TEST_MOV1          11, rd2rf, rf5, rd5, 0x000000000000FFFF
	@@ 最大元素个数 63（跨组）：目的 rf1..rf63 ← 源 rd1..rd63（rf6 ← rd6、rf63 ← rd63）
	__LI	rd6, 0xAAAAAAAAAAAAAAAA
	__LI	rd63, 0x0123456789ABCDEF
	rd2rf	{rf1:rf63}, {rd1:rd63}
	st.o	rf6, [rb29, 0]
	__VERIFY_MEM       12, SCRATCH, 0, 0xAAAAAAAAAAAAAAAA
	st.o	rf63, [rb29, 0]
	__CHECK_MEM        12, SCRATCH, 0, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ immu6=0 ⇒ ILLI（mreg_zero；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        13, ILLI, 0x40F410C0, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x40F7F042, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        15, ILLI, 0x40F41FC2, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
