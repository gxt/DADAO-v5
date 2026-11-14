@@ rem.sb_orrr_rd.S — rem.sb rdHB, rdHC, rdHD（orrr, opc 0x43／ha 0x3B）
@@ 大类：10-arith-logic-byte（8 位数据运算，`spec/SimRISC-10 §1.3`）；册目录 `tests/inst/10-arith-logic-byte/`
@@ id：rem.sb_orrr_rd　形式：orrr　opc：0x43／ha 0x3B　mask：0xFFFC0000　value：0x43EC0000　目的银行：RD
@@ 语义：rdHB ← sign_extend8(s8(rdHC[7:0]) − s8(rdHD[7:0]) × trunc(...))，**余数符号 = 被除数符号**；
@@   **除零与 INT8_MIN ÷ −1 走定值表**（不触发异常，`spec/SimRISC-04 §1.4`）：
@@   除零 ⇒ 被除数（符号扩展写满 64 位）；−128 % −1 ⇒ 0
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0，作除数 ⇒ 除零定值）
@@ 编码：orrr = opc[31:24] | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / overlap 2（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding（规范编码字直接执行，钉 mask/value）----
	@@ 0x43EC5187 = value | rd5<<12 | rd6<<6 | rd7：60 % 7 = 4
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x000000000000003C
	__LI	rd7, 0x0000000000000007
	.dd.t32	0x43EC5187
	__CHECK_RD   1, rd5, 0x0000000000000004

	@@ 0x43EFF042 = value | rd63<<12 | rd1<<6 | rd2（字段边界：最大目的号）：−128 % 3 = −2
	__LI	rd63, 0x0000000000000000
	__LI	rd1, 0x0000000000000080
	__LI	rd2, 0x0000000000000003
	.dd.t32	0x43EFF042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFE

	@@ ---- semantic ----
	@@ −7 % 2 = −1（余数随被除数符号）
	TEST_AR_ORRR         3, rem.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000F9, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ 7 % −2 = 1（被除数仍为正 7，余数随被除数）
	TEST_AR_ORRR         4, rem.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000007, rd7, 0x00000000000000FE, 0x0000000000000001

	@@ −7 % −2 = −1（同号：余数仍是负）
	TEST_AR_ORRR         5, rem.sb, rd5, 0x0000000000000000, rd6, 0x00000000000000F9, rd7, 0x00000000000000FE, 0xFFFFFFFFFFFFFFFF

	@@ 源的高 56 位不参与：0x...C3(−61) % 8 = −5
	TEST_AR_ORRR         6, rem.sb, rd5, 0x0000000000000000, rd6, 0x123456789ABCDEC3, rd7, 0x0000000000000008, 0xFFFFFFFFFFFFFFFB

	@@ 目的初值全 1 被完整覆盖：0 % 5 = 0
	TEST_AR_ORRR         7, rem.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ ---- boundary ----
	@@ 除数为零 ⇒ 定值 = 被除数（符号扩展写满）：0x...FB(−5) ⇒ 0xFFFF_FFFF_FFFF_FFFB
	TEST_AR_ORRR         8, rem.sb, rd5, 0x0000000000000000, rd6, 0x123456789ABCDEFB, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFFB

	@@ −128 % −1 ⇒ 定值 0（溢出档，不触发异常）
	TEST_AR_ORRR         9, rem.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x00000000000000FF, 0x0000000000000000

	@@ 0x7F % 1 = 0
	TEST_AR_ORRR        10, rem.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000007F, rd7, 0x0000000000000001, 0x0000000000000000

	@@ −128 % 0x7F = −1（截断商 −1）
	TEST_AR_ORRR        11, rem.sb, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x000000000000007F, 0xFFFFFFFFFFFFFFFF

	@@ −128 % −128 = 0
	TEST_AR_ORRR        12, rem.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000000000

	@@ ---- overlap ----
	@@ 目的 = 源 C（原地）：0x40 % 8 = 0
	TEST_AR_ORRR        13, rem.sb, rd9, 0x0000000000000040, rd9, 0x0000000000000040, rd10, 0x0000000000000008, 0x0000000000000000

	@@ rd0 作源 C（读出 0）：0 % 1 = 0
	TEST_AR_ORRR        14, rem.sb, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000001, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ legality（dst_rd0）：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, rem.sb, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
