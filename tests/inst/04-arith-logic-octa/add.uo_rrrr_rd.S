@@ add.uo_rrrr_rd.S — add.uo {rdHA, rdHB}, rdHC, rdHD（rrrr, opc 0x50）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：add.uo_rrrr_rd　形式：rrrr　opc：0x50　mask：0xFF000000　value：0x50000000　目的银行：RD
@@ 语义：{{rdHA, rdHB}} ← ZX(rdHC) + ZX(rdHD)（128 位）；**rdHA = 进位（0/1）**，rdHB = 低 64 位
@@ 合法性：两个目的（rdHA/rdHB）不得同时为 rd0，也不得为同一非 rd0 寄存器 ⇒ ILLI（`dst_dual_same`）；
@@   其中一个为 rd0 合法（丢弃对应半结果）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrrr = opc | ha[23:18] | hb[17:12] | hc[11:6] | hd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 4 / boundary 4 / overlap 3（链例 13 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ dst={rd5,rd6}/c=rd7/d=rd8 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x501461C8（opc<<24 | rd5<<18 | rd6<<12 | rd7<<6 | rd8）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0000000000000000
	__LI	rd7, 0x0000000000000064
	__LI	rd8, 0x000000000000001E
	.dd.t32	0x501461C8
	__VERIFY_RD  1, rd5, 0x0000000000000000
	__CHECK_RD   1, rd6, 0x0000000000000082

	@@ 最高寄存器作高半 + rd0 源（读出 0）的编码字（字段边界）
	@@ 规范编码字 0x50FC1000（opc<<24 | rd63<<18 | rd1<<12 | rd0<<6 | rd0）
	__LI	rd63, 0x0000000000000000
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x50FC1000
	__VERIFY_RD  2, rd63, 0x0000000000000000
	__CHECK_RD   2, rd1, 0x0000000000000000

	@@ 小值：100 + 30 ⇒ 无进位
	TEST_AR_DUAL         3, add.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x0000000000000064, rd8, 0x000000000000001E, 0x0000000000000000, 0x0000000000000082

	@@ 加数含 0：结果 = 另一操作数
	TEST_AR_DUAL         4, add.uo, rd5, rd6, 0x5A5A5A5A5A5A5A5A, 0x5A5A5A5A5A5A5A5A, rd7, 0x0123456789ABCDEF, rd8, 0x0000000000000000, 0x0000000000000000, 0x0123456789ABCDEF

	@@ 高半丢弃：{rd0, rdN} 合法，只留低半
	TEST_AR_DUAL         5, add.uo, rd0, rd9, 0x0000000000000000, 0x0000000000000000, rd7, 0x0000000000000005, rd8, 0x0000000000000007, 0x0000000000000000, 0x000000000000000C

	@@ 低半丢弃：{rdN, rd0} 合法，只留进位
	TEST_AR_DUAL         6, add.uo, rd9, rd0, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0000000000000001, 0x0000000000000001, 0x0000000000000000

	@@ 进位出 1：两个 0x8000..0 相加
	TEST_AR_DUAL         7, add.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x8000000000000000, 0x0000000000000001, 0x0000000000000000

	@@ 全 1 + 全 1：进位 1、低半 …FE
	TEST_AR_DUAL         8, add.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000001, 0xFFFFFFFFFFFFFFFE

	@@ 最大无符号 + 1：进位 1、低半 0
	TEST_AR_DUAL         9, add.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0000000000000001, 0x0000000000000001, 0x0000000000000000

	@@ 0 + 0：不进位
	TEST_AR_DUAL        10, add.uo, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, rd8, 0x0000000000000000, 0x0000000000000000, 0x0000000000000000

	@@ 高半=源C（原地）：源值先被捕获再写
	TEST_AR_DUAL        11, add.uo, rd10, rd11, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, rd10, 0xFFFFFFFFFFFFFFFF, rd12, 0x0000000000000001, 0x0000000000000001, 0x0000000000000000

	@@ 低半=源D（原地）
	TEST_AR_DUAL        12, add.uo, rd10, rd11, 0x0000000000000000, 0x8000000000000000, rd12, 0x8000000000000000, rd11, 0x8000000000000000, 0x0000000000000001, 0x0000000000000000

	@@ 两源同名：x + x = 2x（进位 1）
	TEST_AR_DUAL        13, add.uo, rd10, rd11, 0x0000000000000000, 0x0000000000000000, rd13, 0x8000000000000000, rd13, 0x8000000000000000, 0x0000000000000001, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_dual_same：两个目的同为 rd0
	TEST_FAULT_DUAL     14, add.uo, ILLI, rd0, rd0, rd7, rd8

	@@ dst_dual_same：两个目的为同一非 rd0 寄存器
	TEST_FAULT_DUAL     15, add.uo, ILLI, rd5, rd5, rd7, rd8

	__TEST_SECTIONS
