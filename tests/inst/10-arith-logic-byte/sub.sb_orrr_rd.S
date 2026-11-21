@@ sub.sb_orrr_rd.S — sub.sb rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x29）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §1.1`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：sub.sb_orrr_rd　形式：orrr　opc：0x43／ha 0x29　mask：0xFFFC0000　value：0x43A40000　目的银行：RD
@@ 语义：rdHB ← sign_extend8((rdHC[7:0] − rdHD[7:0]) mod 2^8)；只有低 8 位参与，借位静默丢弃，
@@   结果按有符号（符号扩展）写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / overlap 3（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43A45187 = value | rd5<<12 | rd6<<6 | rd7：3 − 4 = −1
	set.rd	rd5, 0x0000000000000000
	set.rd	rd6, 0x0000000000000003
	set.rd	rd7, 0x0000000000000004
	.dd.t32	0x43A45187
	__CHECK_RD   1, rd5, 0xFFFFFFFFFFFFFFFF

	@@ 0x43A7F042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：1 − 2 = −1
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x0000000000000002
	.dd.t32	0x43A7F042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ ---- semantic ----
	@@ 0x00 − 0x01 = 0xFF ⇒ −1（借位回绕）
	TEST_AR_ORRR         3, sub.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	@@ 0x80 − 0x01 = 0x7F：由负跨到正（符号扩展后为正数）
	TEST_AR_ORRR         4, sub.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000001, 0x000000000000007F

	@@ 0x7F − 0xFF = 0x7F − (−1) = 0x80 ⇒ −128（符号位翻转）
	TEST_AR_ORRR         5, sub.sb, rd5, 0x0000000000000000, rd6, 0x000000000000007F, rd7, 0x00000000000000FF, 0xFFFFFFFFFFFFFF80

	@@ 源的高 56 位不参与：0x...FF − 1 = 0xFE ⇒ −2
	TEST_AR_ORRR         6, sub.sb, rd5, 0x0000000000000000, rd6, 0x123456789ABCDEFF, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFE

	@@ 目的初值全 1 被完整覆盖：5 − 3 = 2
	TEST_AR_ORRR         7, sub.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000005, rd7, 0x0000000000000003, 0x0000000000000002

	@@ ---- boundary ----
	@@ 0x80 − 0x80 = 0（同值相减）
	TEST_AR_ORRR         8, sub.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000000000

	@@ 0x80 − 0x7F = 1（最负减最大正）
	TEST_AR_ORRR         9, sub.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x000000000000007F, 0x0000000000000001

	@@ 0x7F − 0x80 = 0xFF ⇒ −1
	TEST_AR_ORRR        10, sub.sb, rd5, 0x0000000000000000, rd6, 0x000000000000007F, rd7, 0x0000000000000080, 0xFFFFFFFFFFFFFFFF

	@@ 0x00 − 0xFF = 0x01（借位向高位索取后丢弃）
	TEST_AR_ORRR        11, sub.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x00000000000000FF, 0x0000000000000001

	@@ 低 8 位隔离：0xABCDEF0123456705 − 3 = 2
	TEST_AR_ORRR        12, sub.sb, rd5, 0x0000000000000000, rd6, 0xABCDEF0123456705, rd7, 0x0000000000000003, 0x0000000000000002

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x10 − 0x20 = 0xF0 ⇒ −16
	TEST_AR_ORRR        13, sub.sb, rd9, 0x0000000000000010, rd9, 0x0000000000000010, rd10, 0x0000000000000020, 0xFFFFFFFFFFFFFFF0

	@@ 两源同名：x − x = 0
	TEST_AR_ORRR        14, sub.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd11, 0x0000000000000055, rd11, 0x0000000000000055, 0x0000000000000000

	@@ rd0 作源 C（读出 0）：0 − 1 = −1
	TEST_AR_ORRR        15, sub.sb, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     16, sub.sb, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
