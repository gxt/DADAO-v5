@@ shr.sb_orrr_rd.S — shr.sb rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x13）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：shr.sb_orrr_rd　形式：orrr　opc：0x43／ha 0x13　mask：0xFFFC0000　value：0x434C0000　目的银行：RD
@@ 语义：算术右移 —— rdHB[7:0] ← rdHC[7:0] >> rdHD[2:0]（移入位 = rdHC[7]），
@@   rdHB[63:8] ← sign(rdHC[7])（值语义：负数写满 1、正数写满 0）；
@@   移位量 = **rdHD[2:0]**（天然对 8 取模），rdHD 的其他位被忽略、不触发 ILLI
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；源与目的同号合法
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x434C5187 = value | rd5<<12 | rd6<<6 | rd7：0xF0(−16) >> 1 = 0xF8（−8）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x00000000000000F0
	__LI	rd7, 0x0000000000000001
	.dd.t32	0x434C5187
	__CHECK_RD   1, rd5, 0xFFFFFFFFFFFFFFF8

	@@ 0x434FF042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：0x80 >> 7 = 0xFF ⇒ −1
	__LI	rd63, 0x0000000000000000
	__LI	rd1, 0x0000000000000080
	__LI	rd2, 0x0000000000000007
	.dd.t32	0x434FF042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ ---- semantic ----
	@@ 0x80(−128) >> 1 = 0xC0（−64），高位写满 1
	TEST_AR_ORRR         3, shr.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFC0

	@@ 0x7F(127) >> 1 = 0x3F（正数 ⇒ 高位写满 0，零扩展）
	TEST_AR_ORRR         4, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, rd7, 0x0000000000000001, 0x000000000000003F

	@@ 0xFF(−1) >> 4 = 0xFF（−1 算术右移恒 −1）
	TEST_AR_ORRR         5, shr.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, rd7, 0x0000000000000004, 0xFFFFFFFFFFFFFFFF

	@@ 源的高 56 位不参与：0x...40(64) >> 2 = 0x10
	TEST_AR_ORRR         6, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE40, rd7, 0x0000000000000002, 0x0000000000000010

	@@ 目的初值全 1 被完整覆盖：0 >> 3 = 0
	TEST_AR_ORRR         7, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000003, 0x0000000000000000

	@@ ---- boundary ----
	@@ 移位量取 rdHD[2:0]：0x0B(1011) ⇒ 3 ⇒ 0xF0(−16) >> 3 = 0xFE（−2）
	TEST_AR_ORRR         8, shr.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000F0, rd7, 0x000000000000000B, 0xFFFFFFFFFFFFFFFE

	@@ 移位量 0xFF ⇒ 7：0x80 >> 7 = 0xFF ⇒ −1
	TEST_AR_ORRR         9, shr.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x00000000000000FF, 0xFFFFFFFFFFFFFFFF

	@@ 0x7F >> 7 = 0（正数不移入 1）
	TEST_AR_ORRR        10, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, rd7, 0x0000000000000007, 0x0000000000000000

	@@ 移位量 8(1000) ⇒ 低 3 位 0 ⇒ 原值（高位按符号扩展，非保留旧值）
	TEST_AR_ORRR        11, shr.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000008, 0xFFFFFFFFFFFFFF80

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x80 >> 1 = 0xC0
	TEST_AR_ORRR        12, shr.sb, rd9, 0x0000000000000080, rd9, 0x0000000000000080, rd10, 0x0000000000000001, 0xFFFFFFFFFFFFFFC0

	@@ 两源同名（移位量 = 该寄存器低 3 位）：0x46(0100_0110) ⇒ shamt 6，0x46 >> 6 = 1
	TEST_AR_ORRR        13, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd11, 0x0000000000000046, rd11, 0x0000000000000046, 0x0000000000000001

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRR        14, shr.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000003, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, shr.sb, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
