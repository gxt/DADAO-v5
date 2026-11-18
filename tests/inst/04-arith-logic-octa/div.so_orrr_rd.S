@@ div.so_orrr_rd.S — div.so rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x39）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：div.so_orrr_rd　形式：orrr　opc：0x40／ha 0x39　mask：0xFFFC0000　value：0x40E40000　目的银行：RD
@@ 语义：rdHB ← rdHC ÷ rdHD（有符号，truncate-toward-zero）；**÷0 ⇒ 全 1**；INT64_MIN ÷ −1 ⇒ INT64_MIN
@@ 合法性：目的 rdHA/rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[19:18] | hb[17:12] | hc[11:6] | hd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / overlap 3（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 / rd7 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40E45187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	set.rd	rd5, 0x0000000000000000
	set.rd	rd6, 0x0000000000000064
	set.rd	rd7, 0x0000000000000007
	.dd.t32	0x40E45187
	__CHECK_RD   1, rd5, 0x000000000000000E

	@@ 最高寄存器三字段（rd63）的编码字（字段边界）
	@@ 规范编码字 0x40E7F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x40E7F042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ 100 / 7 = 14
	TEST_AR_ORRR         3, div.so, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000007, 0x000000000000000E

	@@ -100 / 7 = -14（向零截断）
	TEST_AR_ORRR         4, div.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFF9C, rd7, 0x0000000000000007, 0xFFFFFFFFFFFFFFF2

	@@ 100 / -7 = -14
	TEST_AR_ORRR         5, div.so, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0xFFFFFFFFFFFFFFF9, 0xFFFFFFFFFFFFFFF2

	@@ -100 / -7 = 14
	TEST_AR_ORRR         6, div.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFFFFFFFF9C, rd7, 0xFFFFFFFFFFFFFFF9, 0x000000000000000E

	@@ rd0 作被除数：0 / -7 = 0
	TEST_AR_ORRR         7, div.so, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFF9, 0x0000000000000000

	@@ 除数为 0 ⇒ 全 1（定值）
	TEST_AR_ORRR         8, div.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFF9C, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ INT64_MIN / (-1) ⇒ INT64_MIN（溢出定值）
	TEST_AR_ORRR         9, div.so, rd6, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0xFFFFFFFFFFFFFFFF, 0x8000000000000000

	@@ INT64_MIN / 1 = INT64_MIN
	TEST_AR_ORRR        10, div.so, rd6, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x0000000000000001, 0x8000000000000000

	@@ -1 / 2 = 0（向零截断，不是 -1）
	TEST_AR_ORRR        11, div.so, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0000000000000002, 0x0000000000000000

	@@ 1 / -2 = 0
	TEST_AR_ORRR        12, div.so, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000001, rd8, 0xFFFFFFFFFFFFFFFE, 0x0000000000000000

	@@ 目的=源C（原地）
	TEST_AR_ORRR        13, div.so, rd9, 0x0000000000000064, rd9, 0x0000000000000064, rd10, 0x0000000000000007, 0x000000000000000E

	@@ 目的=源D（原地）
	TEST_AR_ORRR        14, div.so, rd9, 0x0000000000000007, rd10, 0x0000000000000064, rd9, 0x0000000000000007, 0x000000000000000E

	@@ 两源同名 ⇒ 1
	TEST_AR_ORRR        15, div.so, rd9, 0x0000000000000000, rd11, 0xFFFFFFFFFFFFCFC7, rd11, 0xFFFFFFFFFFFFCFC7, 0x0000000000000001

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     16, div.so, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
