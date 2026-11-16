@@ rem.ub_orrr_rd.S — rem.ub rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x3A）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §1.3`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：rem.ub_orrr_rd　形式：orrr　opc：0x43／ha 0x3A　mask：0xFFFC0000　value：0x43E80000　目的银行：RD
@@ 语义：rdHB ← zero_extend8(rdHC[7:0] % rdHD[7:0])（无符号余数），结果写满 64 位；
@@   **除数为零走定值表**（不触发异常，`spec/SimRISC-04 §1.4`）：除零 ⇒ 被除数（零扩展写满）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0，作除数 ⇒ 除零定值）
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / overlap 2（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43E85187 = value | rd5<<12 | rd6<<6 | rd7：60 % 7 = 4
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x000000000000003C
	set.rd	rd7, 0x0000000000000007
	.dd.t32	0x43E85187
	__CHECK_RD   1, rd5, 0x0000000000000004

	@@ 0x43EBF042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：0xFF % 3 = 0
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x00000000000000FF
	set.rd	rd2, 0x0000000000000003
	.dd.t32	0x43EBF042
	__CHECK_RD   2, rd63, 0x0000000000000000

	@@ ---- semantic ----
	@@ 7 % 2 = 1
	TEST_AR_ORRR         3, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000007, rd7, 0x0000000000000002, 0x0000000000000001

	@@ 0xFF % 0x10 = 15（无符号视角）
	TEST_AR_ORRR         4, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, rd7, 0x0000000000000010, 0x000000000000000F

	@@ 源的高 56 位不参与：0x...FF % 2 = 1
	TEST_AR_ORRR         5, rem.ub, rd5, 0x0000000000000000, rd6, 0x123456789ABCDEFF, rd7, 0x0000000000000002, 0x0000000000000001

	@@ 目的初值全 1 被完整覆盖：10 % 4 = 2
	TEST_AR_ORRR         6, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000000A, rd7, 0x0000000000000004, 0x0000000000000002

	@@ 0 % 5 = 0
	TEST_AR_ORRR         7, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ ---- boundary ----
	@@ 除数为零 ⇒ 定值 = 被除数（零扩展写满）：0x...FB ⇒ 0x0000_0000_0000_00FB
	TEST_AR_ORRR         8, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDEFB, rd7, 0x0000000000000000, 0x00000000000000FB

	@@ 0xFF % 1 = 0
	TEST_AR_ORRR         9, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ 0x80 % 0x7F = 1（128 = 127 + 1）
	TEST_AR_ORRR        10, rem.ub, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x000000000000007F, 0x0000000000000001

	@@ 0x7F % 0x80 = 0x7F（被除数小于除数 ⇒ 余数为被除数）
	TEST_AR_ORRR        11, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, rd7, 0x0000000000000080, 0x000000000000007F

	@@ 0x80 % 0x80 = 0
	TEST_AR_ORRR        12, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000000000

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x40 % 8 = 0
	TEST_AR_ORRR        13, rem.ub, rd9, 0x0000000000000040, rd9, 0x0000000000000040, rd10, 0x0000000000000008, 0x0000000000000000

	@@ rd0 作源 C（读出 0）：0 % 1 = 0
	TEST_AR_ORRR        14, rem.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000001, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, rem.ub, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
