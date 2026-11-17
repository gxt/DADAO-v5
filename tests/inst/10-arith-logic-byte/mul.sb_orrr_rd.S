@@ mul.sb_orrr_rd.S — mul.sb rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x31）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §1.3`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：mul.sb_orrr_rd　形式：orrr　opc：0x43／ha 0x31　mask：0xFFFC0000　value：0x43C40000　目的银行：RD
@@ 语义：rdHB ← sign_extend8((s8(rdHC[7:0]) × s8(rdHD[7:0])) mod 2^8)；8×8 只保留低 8 位，
@@   高位乘积丢弃，结果按有符号（符号扩展）写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；源与目的同号合法
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 4（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43C45187 = value | rd5<<12 | rd6<<6 | rd7：6 × 7 = 42 = 0x2A
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0000000000000006
	set.rd	rd7, 0x0000000000000007
	.dd.t32	0x43C45187
	__CHECK_RD   1, rd5, 0x000000000000002A

	@@ 0x43C7F042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：(−1) × 3 = −3
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x00000000000000FF
	set.rd	rd2, 0x0000000000000003
	.dd.t32	0x43C7F042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFD

	@@ ---- semantic ----
	@@ 1 × 0x7F = 0x7F（最大正数）
	TEST_AR_ORRR         3, mul.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x000000000000007F, 0x000000000000007F

	@@ 2 × 0x40 = 0x80 ⇒ −128（乘积落入符号位）
	TEST_AR_ORRR         4, mul.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000002, rd7, 0x0000000000000040, 0xFFFFFFFFFFFFFF80

	@@ (−1) × (−1) = 1
	TEST_AR_ORRR         5, mul.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, rd7, 0x00000000000000FF, 0x0000000000000001

	@@ 源的高 56 位不参与：3 × 4 = 12 = 0x0C
	TEST_AR_ORRR         6, mul.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE03, rd7, 0x0000000000000004, 0x000000000000000C

	@@ 目的初值全 1 被完整覆盖：3 × 5 = 15 = 0x0F
	TEST_AR_ORRR         7, mul.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000003, rd7, 0x0000000000000005, 0x000000000000000F

	@@ ---- boundary ----
	@@ 0x7F × 0x7F = 0x3F01 ⇒ 只留低 8 位 0x01
	TEST_AR_ORRR         8, mul.sb, rd5, 0x0000000000000000, rd6, 0x000000000000007F, rd7, 0x000000000000007F, 0x0000000000000001

	@@ 0x80 × 0x80 = 0x4000 ⇒ 低 8 位 0
	TEST_AR_ORRR         9, mul.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000000000

	@@ (−1) × 0x7F = −127 = 0x81 ⇒ 符号扩展
	TEST_AR_ORRR        10, mul.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, rd7, 0x000000000000007F, 0xFFFFFFFFFFFFFF81

	@@ 0 × 0x7F = 0
	TEST_AR_ORRR        11, mul.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x000000000000007F, 0x0000000000000000

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：3 × 5 = 15
	TEST_AR_ORRR        12, mul.sb, rd9, 0x0000000000000003, rd9, 0x0000000000000003, rd10, 0x0000000000000005, 0x000000000000000F

	@@ 两源同名：0x0F × 0x0F = 0xE1 = 225 ⇒ 符号扩展成 −31
	TEST_AR_ORRR        13, mul.sb, rd5, 0x0000000000000000, rd11, 0x000000000000000F, rd11, 0x000000000000000F, 0xFFFFFFFFFFFFFFE1

	@@ rd0 作源 C（读出 0）：0 × 9 = 0
	TEST_AR_ORRR        14, mul.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000009, 0x0000000000000000

	@@ 原地 ×2：0x40 × 2 = 0x80 ⇒ −128
	TEST_AR_ORRR        15, mul.sb, rd9, 0x0000000000000040, rd9, 0x0000000000000040, rd10, 0x0000000000000002, 0xFFFFFFFFFFFFFF80

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     16, mul.sb, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
