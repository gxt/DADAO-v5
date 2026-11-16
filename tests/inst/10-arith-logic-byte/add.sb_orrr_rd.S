@@ add.sb_orrr_rd.S — add.sb rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x21）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §1.1`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：add.sb_orrr_rd　形式：orrr　opc：0x43／ha 0x21　mask：0xFFFC0000　value：0x43840000　目的银行：RD
@@ 语义：rdHB ← sign_extend8((rdHC[7:0] + rdHD[7:0]) mod 2^8)；只有低 8 位参与，进位静默丢弃，
@@   结果按有符号（符号扩展）写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`，`spec/SimRISC-10 附录 B`）；源可为 rd0（读出 0）；
@@   源与目的同号、两源同名均合法（先读后写）
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / overlap 3（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43845187 = value | rd5<<12 | rd6<<6 | rd7：3 + 4 = 7
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0000000000000003
	set.rd	rd7, 0x0000000000000004
	.dd.t32	0x43845187
	__CHECK_RD   1, rd5, 0x0000000000000007

	@@ 0x4387F042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：(−1) + 2 = 1
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x00000000000000FF
	set.rd	rd2, 0x0000000000000002
	.dd.t32	0x4387F042
	__CHECK_RD   2, rd63, 0x0000000000000001

	@@ ---- semantic ----
	@@ 0xFF + 0x01：低 8 位回绕到 0（有符号 −1 + 1 = 0）
	TEST_AR_ORRR         3, add.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ 0x7F + 0x00：最大正数不变
	TEST_AR_ORRR         4, add.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, rd7, 0x0000000000000000, 0x000000000000007F

	@@ 0x7F + 0x01 = 0x80：符号位翻转 ⇒ 符号扩展写满（非零扩展）
	TEST_AR_ORRR         5, add.sb, rd5, 0x0000000000000000, rd6, 0x000000000000007F, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFF80

	@@ 源的高 56 位不参与：0x...FF + 1 = 0x00 ⇒ 进位丢弃
	TEST_AR_ORRR         6, add.sb, rd5, 0x0000000000000000, rd6, 0x123456789ABCDEFF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ 0x80 作被加数：−128 + 0 仍是 −128（结果符号扩展）
	TEST_AR_ORRR         7, add.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFF80

	@@ ---- boundary ----
	@@ 0xFF + 0xFF = 0x1FE ⇒ 低 8 位 0xFE = −2
	TEST_AR_ORRR         8, add.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, rd7, 0x00000000000000FF, 0xFFFFFFFFFFFFFFFE

	@@ 0x7F + 0x7F = 0xFE ⇒ 符号扩展
	TEST_AR_ORRR         9, add.sb, rd5, 0x0000000000000000, rd6, 0x000000000000007F, rd7, 0x000000000000007F, 0xFFFFFFFFFFFFFFFE

	@@ 0x80 + 0x80 = 0x100 ⇒ 低 8 位 0（最负数相加回绕）
	TEST_AR_ORRR        10, add.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000000000

	@@ −1 + 1 = 0（跨零）
	TEST_AR_ORRR        11, add.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ 目的初值全 1 被完整覆盖（结果写满 64 位，不是只改低 8 位）
	TEST_AR_ORRR        12, add.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x0000000000000002, 0x0000000000000003

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：5 + 3 = 8
	TEST_AR_ORRR        13, add.sb, rd9, 0x0000000000000005, rd9, 0x0000000000000005, rd10, 0x0000000000000003, 0x0000000000000008

	@@ 两源同名：4 + 4 = 8
	TEST_AR_ORRR        14, add.sb, rd5, 0x0000000000000000, rd11, 0x0000000000000004, rd11, 0x0000000000000004, 0x0000000000000008

	@@ rd0 作源 C（读出 0）：0 + 5 = 5
	TEST_AR_ORRR        15, add.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000005

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     16, add.sb, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
