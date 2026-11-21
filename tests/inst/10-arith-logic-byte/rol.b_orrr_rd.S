@@ rol.b_orrr_rd.S — rol.b rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x11）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2.2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：rol.b_orrr_rd　形式：orrr　opc：0x43／ha 0x11　mask：0xFFFC0000　value：0x43440000　目的银行：RD
@@ 语义：rdHB[7:0] ← rol8(rdHC[7:0], rdHD[2:0])（逻辑循环左移、对 8 取模），rdHB[63:8] ← 0；
@@   移位量 = **rdHD[2:0]**（rdHD 的其他位被忽略、不触发 ILLI）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；源与目的同号合法
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43445187 = value | rd5<<12 | rd6<<6 | rd7：rol8(0x81, 1) = 0x03
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0000000000000081
	set.rd	rd7, 0x0000000000000001
	.dd.t32	0x43445187
	__CHECK_RD   1, rd5, 0x0000000000000003

	@@ 0x4347F042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：rol8(0x01, 7) = 0x80
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x0000000000000007
	.dd.t32	0x4347F042
	__CHECK_RD   2, rd63, 0x0000000000000080

	@@ ---- semantic ----
	@@ 旋转量 0：原值不变（值语义：高位清零）
	TEST_AR_ORRR         3, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x0000000000000000, 0x0000000000000001

	@@ 0x80 rol 1 = 1（最高位回绕到最低位）
	TEST_AR_ORRR         4, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000001, 0x0000000000000001

	@@ 0x0F rol 4 = 0xF0
	TEST_AR_ORRR         5, rol.b, rd5, 0x0000000000000000, rd6, 0x000000000000000F, rd7, 0x0000000000000004, 0x00000000000000F0

	@@ 源的高 56 位不参与：0x...34 rol 4 = 0x43
	TEST_AR_ORRR         6, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE34, rd7, 0x0000000000000004, 0x0000000000000043

	@@ 目的初值全 1 被完整覆盖（rdHB[63:8] = 0）：0 rol 3 = 0
	TEST_AR_ORRR         7, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000003, 0x0000000000000000

	@@ ---- boundary ----
	@@ 旋转量取 rdHD[2:0]：0x0B(1011) ⇒ 3 ⇒ rol8(0x11, 3) = 0x88（高位被忽略，不抛 ILLI）
	TEST_AR_ORRR         8, rol.b, rd5, 0x0000000000000000, rd6, 0x0000000000000011, rd7, 0x000000000000000B, 0x0000000000000088

	@@ 旋转量 0xFF ⇒ 7：rol8(0x01, 7) = 0x80
	TEST_AR_ORRR         9, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x00000000000000FF, 0x0000000000000080

	@@ 跨位回绕：rol8(0x81, 2) = 0x06
	TEST_AR_ORRR        10, rol.b, rd5, 0x0000000000000000, rd6, 0x0000000000000081, rd7, 0x0000000000000002, 0x0000000000000006

	@@ 旋转量 8(1000) ⇒ 低 3 位 0 ⇒ 原值
	TEST_AR_ORRR        11, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000081, rd7, 0x0000000000000008, 0x0000000000000081

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：rol8(0x81, 1) = 0x03
	TEST_AR_ORRR        12, rol.b, rd9, 0x0000000000000081, rd9, 0x0000000000000081, rd10, 0x0000000000000001, 0x0000000000000003

	@@ 两源同名：rol8(0x03, 3) = 0x18
	TEST_AR_ORRR        13, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd11, 0x0000000000000003, rd11, 0x0000000000000003, 0x0000000000000018

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRR        14, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, rol.b, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
