@@ shl.b_orri_rd.S — shl.b rdHB, rdHC, immu6（orri, opc 0x43／ha 0x18）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：shl.b_orri_rd　形式：orri　opc：0x43／ha 0x18　mask：0xFFFC0000　value：0x43600000　目的银行：RD
@@ 语义：rdHB[7:0] ← rdHC[7:0] << immu6，rdHB[63:8] ← 0（值语义、零扩展）；immu6 = 0..7
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；**immu6 > 7 ⇒ ILLI**（`encode_sbz`：
@@   移位量超过位宽限制，`immu6[5:3]` 为 SBZ）；immu6 = 0 合法；源可为 rd0（读出 0）
@@ 编码：orri = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 2（链例 12 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43605183 = value | rd5<<12 | rd6<<6 | immu6=3：1 << 3 = 8
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0000000000000001
	.dd.t32	0x43605183
	__CHECK_RD   1, rd5, 0x0000000000000008

	@@ 0x4363F047 = value | rd63<<12 | rd1<<6 | immu6=7（字段边界：最大目的号 + 最大立即数）：1 << 7 = 0x80
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x0000000000000001
	.dd.t32	0x4363F047
	__CHECK_RD   2, rd63, 0x0000000000000080

	@@ ---- semantic ----
	@@ immu6 = 0 合法：原值不变（不触发 ILLI；`immu6_zero` 不适用于 orri 移位）
	TEST_AR_ORRI         3, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000AB, 0, 0x00000000000000AB

	@@ immu6 = 7：1 << 7 = 0x80
	TEST_AR_ORRI         4, shl.b, rd5, 0x0000000000000000, rd6, 0x0000000000000001, 7, 0x0000000000000080

	@@ immu6 = 4：0xFF << 4 = 0xF0
	TEST_AR_ORRI         5, shl.b, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, 4, 0x00000000000000F0

	@@ 源的高 56 位不参与：0x...FE << 1 = 0xFC
	TEST_AR_ORRI         6, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDEFE, 1, 0x00000000000000FC

	@@ 目的初值全 1 被完整覆盖（rdHB[63:8] = 0）：0 << 3 = 0
	TEST_AR_ORRI         7, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 3, 0x0000000000000000

	@@ ---- boundary ----
	@@ 0x80 << 1 = 0（8 位内溢出丢弃）
	TEST_AR_ORRI         8, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, 1, 0x0000000000000000

	@@ immu6 = 2：0x3C << 2 = 0xF0
	TEST_AR_ORRI         9, shl.b, rd5, 0x0000000000000000, rd6, 0x000000000000003C, 2, 0x00000000000000F0

	@@ immu6 = 6：0x03 << 6 = 0xC0
	TEST_AR_ORRI        10, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000003, 6, 0x00000000000000C0

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x55 << 1 = 0xAA
	TEST_AR_ORRI        11, shl.b, rd9, 0x0000000000000055, rd9, 0x0000000000000055, 1, 0x00000000000000AA

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRI        12, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 5, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 13, shl.b, ILLI, rd0, rd6, 3

	@@ legality（encode_sbz）：immu6 = 8（shamt > 7）⇒ ILLI
	TEST_FAULT_ALU_ORRI 14, shl.b, ILLI, rd5, rd6, 8

	@@ legality（encode_sbz）：immu6 = 63（6 位域最大）⇒ ILLI
	TEST_FAULT_ALU_ORRI 15, shl.b, ILLI, rd5, rd6, 63

	__TEST_SECTIONS
