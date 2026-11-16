@@ rol.b_orri_rd.S — rol.b rdHB, rdHC, immu6（orri, opc 0x43／ha 0x19）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2.2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：rol.b_orri_rd　形式：orri　opc：0x43／ha 0x19　mask：0xFFFC0000　value：0x43640000　目的银行：RD
@@ 语义：rdHB[7:0] ← rol8(rdHC[7:0], immu6)，rdHB[63:8] ← 0；immu6 = 0..7
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；**immu6 > 7 ⇒ ILLI**（`encode_sbz`：
@@   越界旋转量 `8..63`）；immu6 = 0 合法；源可为 rd0（读出 0）
@@ 编码：orri = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 2（链例 12 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43645181 = value | rd5<<12 | rd6<<6 | immu6=1：rol8(0x81, 1) = 0x03
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x0000000000000081
	.dd.t32	0x43645181
	__CHECK_RD   1, rd5, 0x0000000000000003

	@@ 0x4367F047 = value | rd63<<12 | rd1<<6 | immu6=7（字段边界）：rol8(0x01, 7) = 0x80
	__LI	rd63, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x4367F047
	__CHECK_RD   2, rd63, 0x0000000000000080

	@@ ---- semantic ----
	@@ immu6 = 0 合法：原值不变（不触发 ILLI）
	TEST_AR_ORRI         3, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000AB, 0, 0x00000000000000AB

	@@ immu6 = 4：0x0F rol 4 = 0xF0
	TEST_AR_ORRI         4, rol.b, rd5, 0x0000000000000000, rd6, 0x000000000000000F, 4, 0x00000000000000F0

	@@ immu6 = 7：0x81 rol 7 = 0xC0（最高位回绕）
	TEST_AR_ORRI         5, rol.b, rd5, 0x0000000000000000, rd6, 0x0000000000000081, 7, 0x00000000000000C0

	@@ 源的高 56 位不参与：0x...34 rol 4 = 0x43
	TEST_AR_ORRI         6, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE34, 4, 0x0000000000000043

	@@ 目的初值全 1 被完整覆盖（rdHB[63:8] = 0）：0 rol 2 = 0
	TEST_AR_ORRI         7, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 2, 0x0000000000000000

	@@ ---- boundary ----
	@@ immu6 = 3：rol8(0x11, 3) = 0x88
	TEST_AR_ORRI         8, rol.b, rd5, 0x0000000000000000, rd6, 0x0000000000000011, 3, 0x0000000000000088

	@@ immu6 = 5：rol8(0x07, 5) = 0xE0
	TEST_AR_ORRI         9, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000007, 5, 0x00000000000000E0

	@@ immu6 = 6：rol8(0x03, 6) = 0xC0
	TEST_AR_ORRI        10, rol.b, rd5, 0x0000000000000000, rd6, 0x0000000000000003, 6, 0x00000000000000C0

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：rol8(0x81, 1) = 0x03
	TEST_AR_ORRI        11, rol.b, rd9, 0x0000000000000081, rd9, 0x0000000000000081, 1, 0x0000000000000003

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRI        12, rol.b, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 5, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 13, rol.b, ILLI, rd0, rd6, 1

	@@ legality（encode_sbz）：immu6 = 8（越界旋转量）⇒ ILLI
	TEST_FAULT_ALU_ORRI 14, rol.b, ILLI, rd5, rd6, 8

	@@ legality（encode_sbz）：immu6 = 63 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 15, rol.b, ILLI, rd5, rd6, 63

	__TEST_SECTIONS
