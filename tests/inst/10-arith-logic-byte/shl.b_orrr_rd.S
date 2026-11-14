@@ shl.b_orrr_rd.S — shl.b rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x10）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：shl.b_orrr_rd　形式：orrr　opc：0x43／ha 0x10　mask：0xFFFC0000　value：0x43400000　目的银行：RD
@@ 语义：rdHB[7:0] ← rdHC[7:0] << rdHD[2:0]，rdHB[63:8] ← 0（值语义、零扩展）；
@@   移位量 = **rdHD[2:0]**（天然对 8 取模），rdHD 的高位被忽略、不触发 ILLI
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；源与目的同号合法
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 4（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43405187 = value | rd5<<12 | rd6<<6 | rd7：1 << 3 = 8
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x0000000000000001
	__LI	rd7, 0x0000000000000003
	.dd.t32	0x43405187
	__CHECK_RD   1, rd5, 0x0000000000000008

	@@ 0x4343F042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：1 << 7 = 0x80
	__LI	rd63, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x0000000000000001
	__LI	rd2, 0x0000000000000007
	.dd.t32	0x4343F042
	__CHECK_RD   2, rd63, 0x0000000000000080

	@@ ---- semantic ----
	@@ 移位量 0：原值不变（值语义，高位清零）
	TEST_AR_ORRR         3, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x0000000000000000, 0x0000000000000001

	@@ 0x80 << 1 = 0（8 位内溢出丢弃）
	TEST_AR_ORRR         4, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000001, 0x0000000000000000

	@@ 0xFF << 4 = 0xF0
	TEST_AR_ORRR         5, shl.b, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, rd7, 0x0000000000000004, 0x00000000000000F0

	@@ 源的高 56 位不参与：0x...AB << 1 = 0x56
	TEST_AR_ORRR         6, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDEAB, rd7, 0x0000000000000001, 0x0000000000000056

	@@ 目的初值全 1 被完整覆盖（rdHB[63:8] = 0）：0 << 3 = 0
	TEST_AR_ORRR         7, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000003, 0x0000000000000000

	@@ ---- boundary ----
	@@ 移位量取 rdHD[2:0]：0x0B(1011) ⇒ 3 ⇒ 1 << 3 = 8（高位被忽略，不抛 ILLI）
	TEST_AR_ORRR         8, shl.b, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000000B, 0x0000000000000008

	@@ 移位量 8(1000) ⇒ 低 3 位为 0 ⇒ 原值
	TEST_AR_ORRR         9, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x0000000000000008, 0x0000000000000001

	@@ 移位量 0xFF ⇒ 7 ⇒ 1 << 7 = 0x80
	TEST_AR_ORRR        10, shl.b, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x00000000000000FF, 0x0000000000000080

	@@ 0x80 << 7 = 0（最高位再左移全丢）
	TEST_AR_ORRR        11, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000007, 0x0000000000000000

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：3 << 2 = 0x0C
	TEST_AR_ORRR        12, shl.b, rd9, 0x0000000000000003, rd9, 0x0000000000000003, rd10, 0x0000000000000002, 0x000000000000000C

	@@ 两源同名：1 << 1 = 2
	TEST_AR_ORRR        13, shl.b, rd5, 0x0000000000000000, rd11, 0x0000000000000001, rd11, 0x0000000000000001, 0x0000000000000002

	@@ 原地 << 7：0x01 ⇒ 0x80
	TEST_AR_ORRR        14, shl.b, rd9, 0x0000000000000001, rd9, 0x0000000000000001, rd10, 0x0000000000000007, 0x0000000000000080

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRR        15, shl.b, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     16, shl.b, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
