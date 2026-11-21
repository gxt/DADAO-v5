@@ rf2rd_orri_rf.S — rf2rd {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}（orri, opc 0x40, ha 0x3E）
@@ 大类：02-reg-copy（寄存器复制，`spec/SimRISC-02 §1`）
@@ id：rf2rd_orri_rf　形式：orri　opc：0x40　mask：0xFFFC0000　value：0x40F80000
@@ 语义：rd[HB..HB+n-1] ← rf[HC..HC+n-1]，逐元素 64 位二进制不变（rf0 = FCSR，读完整 64 位）
@@ 合法性：目的起始为 rd0 ⇒ ILLI；immu6=0 ⇒ ILLI；起始+immu6>64 ⇒ ILLI（两侧）；
@@   源 rf0 合法；跨组复制（RF → RD）结构上不可能相交 ⇒ `mreg_range_overlap` 不适用
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（rf 初值经 `ld.o` 装载）/ SCRATCH
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 1（链例 11 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 注：rf0 读出的是 FCSR（含只读 qNaN 位型，值不确定）⇒ 含 rf0 的用例只断言同组其它元素

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/02-reg-copy/02-reg-copy.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高两个寄存器作目的/源（字段边界）
	__SET_MEM	rf63, 0x40
	TEST_MOV1           1, rf2rd, rd63, rf63, 0x0123456789ABCDEF
	@@ 规范编码字（dst=rd5, src=rf6, immu6=1）直接执行：钉住 mask/value
	__SET_MEM	rf6, 0x08
	.dd.t32	0x40F85181
	__CHECK_RD          2, rd5, 0x2222222222222222

	@@ ---- semantic ----
	__SET_MEM	rf5, 0x08
	TEST_MOV1           3, rf2rd, rd10, rf5, 0x2222222222222222
	__PREP_MEM2	rf5, 0x10, rf6, 0x18
	rf2rd	{rd10:rd11}, {rf5:rf6}
	__VERIFY_RD         4, rd10, 0x3333333333333333
	__CHECK_RD          4, rd11, 0xABCDEF0123456789
	__PREP_MEM2	rf5, 0x20, rf6, 0x28
	__SET_MEM	rf7, 0x30
	rf2rd	{rd10:rd12}, {rf5:rf7}
	__VERIFY_RD         5, rd10, 0x0000000000000000
	__VERIFY_RD         5, rd11, 0x00000000FFFFFFFF
	__CHECK_RD          5, rd12, 0x8000000000000000
	@@ 多元素（7 个连续寄存器）
	__PREP_MEM2	rf5, 0x38, rf6, 0x40
	__PREP_MEM2	rf7, 0x48, rf8, 0x50
	__PREP_MEM2	rf9, 0x58, rf10, 0x60
	__SET_MEM	rf11, 0x68
	rf2rd	{rd24:rd30}, {rf5:rf11}
	__VERIFY_RD         6, rd24, 0x0000000000000001
	__VERIFY_RD         6, rd27, 0xAAAAAAAAAAAAAAAA
	__CHECK_RD          6, rd30, 0x7FFFFFFFFFFFFFFF
	@@ rf0 作源合法（读出 FCSR 完整 64 位）：同组第 2 个元素仍照常搬（只断言该元素）
	__SET_MEM	rf1, 0x40
	rf2rd	{rd5:rd6}, {rf0:rf1}
	__CHECK_RD          7, rd6, 0x0123456789ABCDEF

	@@ ---- boundary ----
	@@ 源恰在 RF 组顶端
	__PREP_MEM2	rf62, 0x60, rf63, 0x50
	rf2rd	{rd60:rd61}, {rf62:rf63}
	__VERIFY_RD         8, rd60, 0x0F1E2D3C4B5A6978
	__CHECK_RD          8, rd61, 0xAAAAAAAAAAAAAAAA
	@@ 目的恰在 RD 组顶端（源仍为 RF 组顶端的两个值）
	rf2rd	{rd62:rd63}, {rf62:rf63}
	__VERIFY_RD         9, rd62, 0x0F1E2D3C4B5A6978
	__CHECK_RD          9, rd63, 0xAAAAAAAAAAAAAAAA
	@@ overlap（跨组结构性不可能相交）：源/目的同号（rd5 / rf5）照常复制
	__SET_MEM	rf5, 0x70
	TEST_MOV1          10, rf2rd, rd5, rf5, 0x000A000000001234
	@@ 最大元素个数 63（跨组）：目的 rd1..rd63 ← 源 rf0..rf62（rd6 ← rf5、rd63 ← rf62）
	__PREP_MEM2	rf5, 0x50, rf62, 0x40
	rf2rd	{rd1:rd63}, {rf0:rf62}
	__VERIFY_RD        11, rd6, 0xAAAAAAAAAAAAAAAA
	__CHECK_RD         11, rd63, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器拒绝该编码，故用原始字）
	TEST_FAULT_ENC        12, ILLI, 0x40F80041, rb3, TEST_DATA, rd19, 0x000
	@@ immu6=0 ⇒ ILLI（mreg_zero）
	TEST_FAULT_ENC        13, ILLI, 0x40F810C0, rb3, TEST_DATA, rd19, 0x000
	@@ 目的起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        14, ILLI, 0x40FBF042, rb3, TEST_DATA, rd19, 0x000
	@@ 源起始 + immu6 = 65 > 64 ⇒ ILLI（mreg_range_overflow）
	TEST_FAULT_ENC        15, ILLI, 0x40F81FC2, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
