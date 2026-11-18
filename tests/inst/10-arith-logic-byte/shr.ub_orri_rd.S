@@ shr.ub_orri_rd.S — shr.ub rdHB, rdHC, immu6（orri, opc 0x43／ha 0x1A）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：shr.ub_orri_rd　形式：orri　opc：0x43／ha 0x1A　mask：0xFFFC0000　value：0x43680000　目的银行：RD
@@ 语义：rdHB[7:0] ← rdHC[7:0] >> immu6（逻辑右移、零扩展），rdHB[63:8] ← 0；immu6 = 0..7
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；**immu6 > 7 ⇒ ILLI**（`encode_sbz`）；
@@   immu6 = 0 合法；源可为 rd0（读出 0）
@@ 编码：orri = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 3 / overlap 2（链例 12 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43685183 = value | rd5<<12 | rd6<<6 | immu6=3：0x80 >> 3 = 0x10
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0000000000000080
	.dd.t32	0x43685183
	__CHECK_RD   1, rd5, 0x0000000000000010

	@@ 0x436BF047 = value | rd63<<12 | rd1<<6 | immu6=7（字段边界）：0xFF >> 7 = 1
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x00000000000000FF
	.dd.t32	0x436BF047
	__CHECK_RD   2, rd63, 0x0000000000000001

	@@ ---- semantic ----
	@@ immu6 = 0 合法：原值不变（不触发 ILLI）
	TEST_AR_ORRI         3, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, 0, 0x00000000000000FF

	@@ immu6 = 7：0x80 >> 7 = 1
	TEST_AR_ORRI         4, shr.ub, rd5, 0x0000000000000000, rd6, 0x0000000000000080, 7, 0x0000000000000001

	@@ immu6 = 4：0xFF >> 4 = 0x0F
	TEST_AR_ORRI         5, shr.ub, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, 4, 0x000000000000000F

	@@ 源的高 56 位不参与：0x...80 >> 4 = 0x08
	TEST_AR_ORRI         6, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE80, 4, 0x0000000000000008

	@@ 目的初值全 1 被完整覆盖（rdHB[63:8] = 0）：0 >> 1 = 0
	TEST_AR_ORRI         7, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 1, 0x0000000000000000

	@@ ---- boundary ----
	@@ 0x01 >> 1 = 0（最低位移出）
	TEST_AR_ORRI         8, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, 1, 0x0000000000000000

	@@ immu6 = 6：0xC0 >> 6 = 3
	TEST_AR_ORRI         9, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000C0, 6, 0x0000000000000003

	@@ immu6 = 5：0xFF >> 5 = 7
	TEST_AR_ORRI        10, shr.ub, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, 5, 0x0000000000000007

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x80 >> 2 = 0x20
	TEST_AR_ORRI        11, shr.ub, rd9, 0x0000000000000080, rd9, 0x0000000000000080, 2, 0x0000000000000020

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRI        12, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 4, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 13, shr.ub, ILLI, rd0, rd6, 3

	@@ legality（encode_sbz）：immu6 = 8（shamt > 7）⇒ ILLI
	TEST_FAULT_ALU_ORRI 14, shr.ub, ILLI, rd5, rd6, 8

	@@ legality（encode_sbz）：immu6 = 63 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 15, shr.ub, ILLI, rd5, rd6, 63

	__TEST_SECTIONS
