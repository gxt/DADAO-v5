@@ div.ub_orrr_rd.S — div.ub rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x38）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §1.3`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：div.ub_orrr_rd　形式：orrr　opc：0x43／ha 0x38　mask：0xFFFC0000　value：0x43E00000　目的银行：RD
@@ 语义：rdHB ← zero_extend8(rdHC[7:0] ÷ rdHD[7:0])（无符号除法），结果写满 64 位；
@@   **除数为零走定值表**（不触发异常，`spec/SimRISC-04 §1.4`）：除零 ⇒ 0x0000_0000_0000_00FF；
@@   `div.u` 不存在有符号溢出档
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0，作除数 ⇒ 除零定值）
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / overlap 2（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43E05187 = value | rd5<<12 | rd6<<6 | rd7：60 ÷ 7 = 8
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x000000000000003C
	__LI	rd7, 0x0000000000000007
	.dd.t32	0x43E05187
	__CHECK_RD   1, rd5, 0x0000000000000008

	@@ 0x43E3F042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：0xFF ÷ 2 = 127
	__LI	rd63, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x00000000000000FF
	__LI	rd2, 0x0000000000000002
	.dd.t32	0x43E3F042
	__CHECK_RD   2, rd63, 0x000000000000007F

	@@ ---- semantic ----
	@@ 7 ÷ 2 = 3（余数丢弃）
	TEST_AR_ORRR         3, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000007, rd7, 0x0000000000000002, 0x0000000000000003

	@@ 0xFF ÷ 0x10 = 15（无符号视角）
	TEST_AR_ORRR         4, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, rd7, 0x0000000000000010, 0x000000000000000F

	@@ 源的高 56 位不参与：0x...FF ÷ 2 = 0x7F
	TEST_AR_ORRR         5, div.ub, rd5, 0x0000000000000000, rd6, 0x123456789ABCDEFF, rd7, 0x0000000000000002, 0x000000000000007F

	@@ 目的初值全 1 被完整覆盖：10 ÷ 4 = 2
	TEST_AR_ORRR         6, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000000A, rd7, 0x0000000000000004, 0x0000000000000002

	@@ 0 ÷ 1 = 0
	TEST_AR_ORRR         7, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000001, 0x0000000000000000

	@@ ---- boundary ----
	@@ 除数为零 ⇒ 定值 0x0000_0000_0000_00FF（零扩展到 255，不触发异常）
	TEST_AR_ORRR         8, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x123456789ABCDE12, rd7, 0x0000000000000000, 0x00000000000000FF

	@@ 0xFF ÷ 1 = 0xFF（最大商）
	TEST_AR_ORRR         9, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, rd7, 0x0000000000000001, 0x00000000000000FF

	@@ 0x80 ÷ 0x7F = 1（128 ÷ 127 截断）
	TEST_AR_ORRR        10, div.ub, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x000000000000007F, 0x0000000000000001

	@@ 0x7F ÷ 0x80 = 0（小于除数的正数）
	TEST_AR_ORRR        11, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, rd7, 0x0000000000000080, 0x0000000000000000

	@@ 0x80 ÷ 0x80 = 1
	TEST_AR_ORRR        12, div.ub, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000000001

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x40 ÷ 8 = 8
	TEST_AR_ORRR        13, div.ub, rd9, 0x0000000000000040, rd9, 0x0000000000000040, rd10, 0x0000000000000008, 0x0000000000000008

	@@ rd0 作源 C（读出 0）：0 ÷ 1 = 0
	TEST_AR_ORRR        14, div.ub, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000001, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, div.ub, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
