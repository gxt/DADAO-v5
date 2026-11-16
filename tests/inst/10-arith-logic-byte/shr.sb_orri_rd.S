@@ shr.sb_orri_rd.S — shr.sb rdHB, rdHC, immu6（orri, opc 0x43／ha 0x1B）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：shr.sb_orri_rd　形式：orri　opc：0x43／ha 0x1B　mask：0xFFFC0000　value：0x436C0000　目的银行：RD
@@ 语义：算术右移立即数 —— rdHB[7:0] ← rdHC[7:0] >> immu6（移入位 = rdHC[7]），
@@   rdHB[63:8] ← sign(rdHC[7])；immu6 = 0..7
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；**immu6 > 7 ⇒ ILLI**（`encode_sbz`）；
@@   immu6 = 0 合法；源可为 rd0（读出 0）
@@ 编码：orri = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 2（链例 12 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x436C5181 = value | rd5<<12 | rd6<<6 | immu6=1：0xF0(−16) >> 1 = 0xF8（−8）
	set.rd	rd5, 0x0000000000000000
	set.rd	rd6, 0x00000000000000F0
	.dd.t32	0x436C5181
	__CHECK_RD   1, rd5, 0xFFFFFFFFFFFFFFF8

	@@ 0x436FF047 = value | rd63<<12 | rd1<<6 | immu6=7（字段边界）：0x80 >> 7 = 0xFF ⇒ −1
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x0000000000000080
	.dd.t32	0x436FF047
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ ---- semantic ----
	@@ immu6 = 0 合法：原值不变（符号扩展写满，非「高位保持」）
	TEST_AR_ORRI         3, shr.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000F0, 0, 0xFFFFFFFFFFFFFFF0

	@@ immu6 = 7 且被除数正：0x7F >> 7 = 0
	TEST_AR_ORRI         4, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, 7, 0x0000000000000000

	@@ immu6 = 4 且被除数负：0xFF(−1) >> 4 = 0xFF ⇒ −1
	TEST_AR_ORRI         5, shr.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, 4, 0xFFFFFFFFFFFFFFFF

	@@ 源的高 56 位不参与：0x...40 >> 2 = 0x10
	TEST_AR_ORRI         6, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE40, 2, 0x0000000000000010

	@@ 目的初值全 1 被完整覆盖：0 >> 3 = 0
	TEST_AR_ORRI         7, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 3, 0x0000000000000000

	@@ ---- boundary ----
	@@ immu6 = 6：0x80(−128) >> 6 = 0xFE（−2），高位写满 1
	TEST_AR_ORRI         8, shr.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000080, 6, 0xFFFFFFFFFFFFFFFE

	@@ immu6 = 1 且被除数正：0x7F >> 1 = 0x3F（高位写满 0）
	TEST_AR_ORRI         9, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, 1, 0x000000000000003F

	@@ immu6 = 5：0x8F(−113) >> 5 = 0xFC（−4）
	TEST_AR_ORRI        10, shr.sb, rd5, 0x0000000000000000, rd6, 0x000000000000008F, 5, 0xFFFFFFFFFFFFFFFC

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x80 >> 2 = 0xE0（−32）
	TEST_AR_ORRI        11, shr.sb, rd9, 0x0000000000000080, rd9, 0x0000000000000080, 2, 0xFFFFFFFFFFFFFFE0

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRI        12, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 4, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 13, shr.sb, ILLI, rd0, rd6, 3

	@@ legality（encode_sbz）：immu6 = 8（shamt > 7）⇒ ILLI
	TEST_FAULT_ALU_ORRI 14, shr.sb, ILLI, rd5, rd6, 8

	@@ legality（encode_sbz）：immu6 = 63 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 15, shr.sb, ILLI, rd5, rd6, 63

	__TEST_SECTIONS
