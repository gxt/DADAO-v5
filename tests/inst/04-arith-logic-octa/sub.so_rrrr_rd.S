@@ sub.so_rrrr_rd.S — sub.so {rdHA, rdHB}, rdHC, rdHD（rrrr, opc 0x53）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：sub.so_rrrr_rd　形式：rrrr　opc：0x53　mask：0xFF000000　value：0x53000000　目的银行：RD
@@ 语义：{{rdHA, rdHB}} ← SX(rdHC) − SX(rdHD)（128 位）；rdHA = 高 64 位，rdHB = 低 64 位
@@ 合法性：两个目的（rdHA/rdHB）不得同时为 rd0，也不得为同一非 rd0 寄存器 ⇒ ILLI（`dst_dual_same`）；
@@   其中一个为 rd0 合法（丢弃对应半结果）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrrr = opc | ha[23:18] | hb[17:12] | hc[11:6] | hd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ dst={rd5,rd6}/c=rd7/d=rd8 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x531461C8（opc<<24 | rd5<<18 | rd6<<12 | rd7<<6 | rd8）
	set.rd	rd5, 0x0000000000000000
	set.rd	rd6, 0x0000000000000000
	set.rd	rd7, 0x0000000000000064
	set.rd	rd8, 0x000000000000001E
	.dd.t32	0x531461C8
	__VERIFY_RD  1, rd5, 0x0000000000000000
	__CHECK_RD   1, rd6, 0x0000000000000046

	@@ 最高寄存器作高半 + rd0 源（读出 0）的编码字（字段边界）
	@@ 规范编码字 0x53FC1000（opc<<24 | rd63<<18 | rd1<<12 | rd0<<6 | rd0）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x53FC1000
	__VERIFY_RD  2, rd63, 0x0000000000000000
	__CHECK_RD   2, rd1, 0x0000000000000000

	@@ 100 - 30 = 70
	TEST_AR_DUAL         3, sub.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x0000000000000064, rd8, 0x000000000000001E, 0x0000000000000000, 0x0000000000000046

	@@ 0 - 1 = -1（高半符号扩展）
	TEST_AR_DUAL         4, sub.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x0000000000000000, rd8, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ (-1) - (-1) = 0
	TEST_AR_DUAL         5, sub.so, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000000

	@@ 高半丢弃：{rd0, rdN} 只留低半
	TEST_AR_DUAL         6, sub.so, rd0, rd9, 0x0000000000000000, 0x0000000000000000, rd7, 0x0000000000000000, rd8, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ 低半丢弃：{rdN, rd0} 只留高半
	TEST_AR_DUAL         7, sub.so, rd9, rd0, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF

	@@ INT64_MIN - 1：高半 -1、低半 0x7FFF..F
	TEST_AR_DUAL         8, sub.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF

	@@ max - (-1) = 0x8000..0（高半 0）
	TEST_AR_DUAL         9, sub.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x7FFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x8000000000000000

	@@ min - max = -2^64+1（高半全 1、低半 1）
	TEST_AR_DUAL        10, sub.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x7FFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0x0000000000000001

	@@ max - max = 0
	TEST_AR_DUAL        11, sub.so, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x7FFFFFFFFFFFFFFF, rd8, 0x7FFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000000

	@@ 高半=源C（原地）
	TEST_AR_DUAL        12, sub.so, rd10, rd11, 0x0000000000000000, 0x0000000000000000, rd10, 0x0000000000000000, rd12, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ 低半=源D（原地）
	TEST_AR_DUAL        13, sub.so, rd10, rd11, 0x0000000000000000, 0x0000000000000005, rd12, 0x0000000000000009, rd11, 0x0000000000000005, 0x0000000000000000, 0x0000000000000004

	@@ 两源同名：x - x = 0
	TEST_AR_DUAL        14, sub.so, rd10, rd11, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd13, 0x8000000000000000, rd13, 0x8000000000000000, 0x0000000000000000, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_dual_same：两个目的同为 rd0
	TEST_FAULT_DUAL     15, sub.so, ILLI, rd0, rd0, rd7, rd8

	@@ dst_dual_same：两个目的为同一非 rd0 寄存器
	TEST_FAULT_DUAL     16, sub.so, ILLI, rd5, rd5, rd7, rd8

	__TEST_SECTIONS
