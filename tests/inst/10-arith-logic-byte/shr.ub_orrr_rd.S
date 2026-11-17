@@ shr.ub_orrr_rd.S — shr.ub rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x12）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §2`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：shr.ub_orrr_rd　形式：orrr　opc：0x43／ha 0x12　mask：0xFFFC0000　value：0x43480000　目的银行：RD
@@ 语义：rdHB[7:0] ← rdHC[7:0] >> rdHD[2:0]（逻辑右移，零扩展），rdHB[63:8] ← 0；
@@   移位量 = **rdHD[2:0]**（天然对 8 取模），rdHD 的其他位被忽略、不触发 ILLI
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；源与目的同号合法
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43485187 = value | rd5<<12 | rd6<<6 | rd7：0x80 >> 3 = 0x10
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0000000000000080
	set.rd	rd7, 0x0000000000000003
	.dd.t32	0x43485187
	__CHECK_RD   1, rd5, 0x0000000000000010

	@@ 0x434BF042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：0xFF >> 7 = 1
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x00000000000000FF
	set.rd	rd2, 0x0000000000000007
	.dd.t32	0x434BF042
	__CHECK_RD   2, rd63, 0x0000000000000001

	@@ ---- semantic ----
	@@ 0x80 >> 1 = 0x40（最高位补 0 ⇒ 逻辑右移）
	TEST_AR_ORRR         3, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000001, 0x0000000000000040

	@@ 移位量 0：原值不变
	TEST_AR_ORRR         4, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x0000000000000000, 0x0000000000000001

	@@ 0xFF >> 4 = 0x0F
	TEST_AR_ORRR         5, shr.ub, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, rd7, 0x0000000000000004, 0x000000000000000F

	@@ 源的高 56 位不参与：0x...80 >> 4 = 0x08
	TEST_AR_ORRR         6, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE80, rd7, 0x0000000000000004, 0x0000000000000008

	@@ 目的初值全 1 被完整覆盖（rdHB[63:8] = 0）：0 >> 3 = 0
	TEST_AR_ORRR         7, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000003, 0x0000000000000000

	@@ ---- boundary ----
	@@ 移位量取 rdHD[2:0]：0x0B(1011) ⇒ 3 ⇒ 0x80 >> 3 = 0x10（高位被忽略，不抛 ILLI）
	TEST_AR_ORRR         8, shr.ub, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x000000000000000B, 0x0000000000000010

	@@ 移位量 8(1000) ⇒ 低 3 位为 0 ⇒ 原值
	TEST_AR_ORRR         9, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000008, 0x0000000000000080

	@@ 移位量 0xFF ⇒ 7 ⇒ 0x80 >> 7 = 1
	TEST_AR_ORRR        10, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x00000000000000FF, 0x0000000000000001

	@@ 0x01 >> 1 = 0（最低位移出）
	TEST_AR_ORRR        11, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x0000000000000001, 0x0000000000000000

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x80 >> 2 = 0x20
	TEST_AR_ORRR        12, shr.ub, rd9, 0x0000000000000080, rd9, 0x0000000000000080, rd10, 0x0000000000000002, 0x0000000000000020

	@@ 两源同名（移位量 = 该寄存器低 3 位）：0x0A(0000_1010) ⇒ shamt 2，0x0A >> 2 = 2
	TEST_AR_ORRR        13, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd11, 0x000000000000000A, rd11, 0x000000000000000A, 0x0000000000000002

	@@ rd0 作源 C（读出 0）⇒ 0
	TEST_AR_ORRR        14, shr.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000004, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, shr.ub, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
