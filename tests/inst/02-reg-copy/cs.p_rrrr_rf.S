@@ cs.p_rrrr_rf.S — cs.p {rdHA}?, rfHB, rfHC, rfHD（rrrr, opc 0x65）
@@ 大类：02-reg-copy（浮点条件赋值，`spec/SimRISC-02 §3`）
@@ id：cs.p_rrrr_rf　形式：rrrr　opc：0x65　mask：0xFF000000　value：0x65000000
@@ 语义：rdHA 为正 ⇒ rfHB = rfHC；否则 rfHB = rfHD（条件在 RD 组，目的/候选在 RF 组）
@@ 合法性：目的 rfHB 为 rf0 ⇒ ILLI（`dst_rf0`）；源 rfHC/rfHD 可为 rf0（读出 FCSR 完整 64 位）；
@@   条件寄存器 rdHA 为 rd0 合法（读出 0 ⇒ 条件不成立）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 RDATA（rf 初值经 `ld.o` 装载）/ SCRATCH（落点，rb29 指）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 4 / legality 1 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 注：① rf0 作目的时只写 FCSR 的 [33:32]/[4:0] ⇒ 其写内容不断言，只断言「不触发 ILLI」；
@@   ② 条件寄存器与目的/候选同名的别名语义按 C-27 仍 deferred ⇒ 用例不同名

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 最高几个寄存器作条件/目的/候选（字段边界）
	TEST_CS1_RF        1, cs.p, rd63, 1, rf62, 0x00, rf61, 0x08, rf60, 0x10, 0x2222222222222222
	@@ 规范编码字（rdHA=rd5, rfHB=rf6, rfHC=rf7, rfHD=rf8）直接执行：钉住 mask/value
	__LI	rd5, 1
	__SET_MEM	rf6, 0x00
	__SET_MEM	rf7, 0x08
	__SET_MEM	rf8, 0x10
	.dd.t32	0x651461C8
	st.o	rf6, [rb29, 0]
	__CHECK_MEM         2, SCRATCH, 0, 0x2222222222222222

	@@ ---- semantic ----
	@@ 条件为正 ⇒ 取 rfHC；未选中侧 rfHD 不得被写
	__LI	rd1, 1
	__SET_MEM	rf10, 0x00
	__SET_MEM	rf11, 0x30
	__SET_MEM	rf12, 0x40
	cs.p	{rd1}?, rf10, rf11, rf12
	st.o	rf12, [rb29, 0]
	__VERIFY_MEM        3, SCRATCH, 0, 0x0123456789ABCDEF
	st.o	rf10, [rb29, 0]
	__CHECK_MEM         3, SCRATCH, 0, 0x8000000000000000
	@@ 条件为 2（正）⇒ 取 rfHC
	TEST_CS1_RF        4, cs.p, rd1, 2, rf10, 0x00, rf11, 0x30, rf12, 0x40, 0x8000000000000000
	@@ 条件为零 ⇒ 取 rfHD
	TEST_CS1_RF        5, cs.p, rd1, 0, rf10, 0x00, rf11, 0x30, rf12, 0x40, 0x0123456789ABCDEF
	@@ 条件为负 ⇒ 取 rfHD
	TEST_CS1_RF        6, cs.p, rd1, -1, rf10, 0x00, rf11, 0x30, rf12, 0x40, 0x0123456789ABCDEF

	@@ ---- legality / boundary ----
	@@ 条件为最大正数 ⇒ 取 rfHC
	TEST_CS1_RF        7, cs.p, rd1, 0x7FFFFFFFFFFFFFFF, rf10, 0x48, rf11, 0x30, rf12, 0x40, 0x8000000000000000
	@@ 条件为最小负数 ⇒ 取 rfHD
	TEST_CS1_RF        8, cs.p, rd1, 0x8000000000000000, rf10, 0x48, rf11, 0x30, rf12, 0x40, 0x0123456789ABCDEF
	@@ 成立侧为零 ⇒ 目的被清零（不是「不写」）
	TEST_CS1_RF        9, cs.p, rd1, 1, rf10, 0x48, rf11, 0x20, rf12, 0x40, 0x0000000000000000
	@@ 不成立侧为「位型全异」（0xFEDC…）
	TEST_CS1_RF       10, cs.p, rd1, 0, rf10, 0x48, rf11, 0x30, rf12, 0x48, 0xFEDCBA9876543210
	@@ 两侧候选同值 ⇒ 两支结果一致
	TEST_CS1_RF       11, cs.p, rd1, 1, rf10, 0x48, rf11, 0x50, rf12, 0x50, 0xAAAAAAAAAAAAAAAA
	@@ 目的初值恰等于「未选中侧」⇒ 仍按条件选中侧改写
	TEST_CS1_RF       12, cs.p, rd1, 1, rf10, 0x40, rf11, 0x30, rf12, 0x40, 0x8000000000000000
	@@ 条件寄存器 rd0（硬连零，读出 0）⇒ 非正 ⇒ 取 rfHD
	TEST_CS1_RF       13, cs.p, rd0, 0, rf10, 0x00, rf11, 0x30, rf12, 0x40, 0x0123456789ABCDEF
	@@ 条件/候选/目的互不同名（C-27 之外的路径），条件不成立 ⇒ 未选中侧 rfHC 不得被改写
	__LI	rd1, 0
	__SET_MEM	rf10, 0x00
	__SET_MEM	rf11, 0x58
	__SET_MEM	rf12, 0x40
	cs.p	{rd1}?, rf10, rf11, rf12
	st.o	rf11, [rb29, 0]
	__VERIFY_MEM       14, SCRATCH, 0, 0x5555555555555555
	st.o	rf10, [rb29, 0]
	__CHECK_MEM        14, SCRATCH, 0, 0x0123456789ABCDEF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rf0 ⇒ ILLI（dst_rf0；汇编器拒绝该编码，故用原始字：rdHA=1, rfHB=0, rfHC=3, rfHD=4）
	TEST_FAULT_ENC        15, ILLI, 0x650400C4, rb3, TEST_DATA, rd19, 0x000

	__TEST_SECTIONS
