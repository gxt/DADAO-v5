@@ cmp.ui_rrii_rd.S — cmp.ui rdHA, rdHB, immu12（rrii, opc 0x5C）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：cmp.ui_rrii_rd　形式：rrii　opc：0x5C　mask：0xFF000000　value：0x5C000000　目的银行：RD
@@ 语义：rdHA ← 比较(零扩展 rdHB, 零扩展 immu12)：< ⇒ -1、== ⇒ 0、> ⇒ 1（写满 64 位）
@@ 合法性：目的 rdHA/rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrii = opc | rdha[23:18] | rdhb[17:12] | imm12[11:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ rd5 = cmp(rd6, 0xFFF) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x5C146FFF（opc<<24 | rd5<<18 | rd6<<12 | imm12）
	__LI	rd5, 0xFFFFFFFFFFFFFFFF
	__LI	rd6, 0x0000000000000000
	.dd.t32	0x5C146FFF
	__CHECK_RD   1, rd5, 0xFFFFFFFFFFFFFFFF

	@@ 目的=源（rd63）的编码字：先读源再写目的
	@@ 规范编码字 0x5CFFFFFF（opc<<24 | rd63<<18 | rd63<<12 | imm12）
	__LI	rd63, 0x0000000000000FFF
	.dd.t32	0x5CFFFFFF
	__CHECK_RD   2, rd63, 0x0000000000000000

	@@ 5 < 10 ⇒ -1
	TEST_AR_CMPI         3, cmp.ui, rd5, 0x0000000000000000, rd6, 0x0000000000000005, 10, 0xFFFFFFFFFFFFFFFF

	@@ 10 == 10 ⇒ 0
	TEST_AR_CMPI         4, cmp.ui, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000000A, 10, 0x0000000000000000

	@@ 11 > 10 ⇒ 1
	TEST_AR_CMPI         5, cmp.ui, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000000B, 10, 0x0000000000000001

	@@ rd0 作源（读出 0）：0 < 1 ⇒ -1
	TEST_AR_CMPI         6, cmp.ui, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 1, 0xFFFFFFFFFFFFFFFF

	@@ rd0 作源：0 == 0 ⇒ 0
	TEST_AR_CMPI         7, cmp.ui, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 0, 0x0000000000000000

	@@ immu12 零扩展（不是符号扩展）：0x8000..0 > 0xFFF ⇒ 1
	TEST_AR_CMPI         8, cmp.ui, rd6, 0x0000000000000000, rd7, 0x8000000000000000, 4095, 0x0000000000000001

	@@ immu12 全 1 边界：0xFFF == 0xFFF ⇒ 0
	TEST_AR_CMPI         9, cmp.ui, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000FFF, 4095, 0x0000000000000000

	@@ 0xFFE < 0xFFF ⇒ -1
	TEST_AR_CMPI        10, cmp.ui, rd6, 0x0000000000000000, rd7, 0x0000000000000FFE, 4095, 0xFFFFFFFFFFFFFFFF

	@@ 0x1000 > 0xFFF ⇒ 1
	TEST_AR_CMPI        11, cmp.ui, rd6, 0x0000000000000000, rd7, 0x0000000000001000, 4095, 0x0000000000000001

	@@ max > imm ⇒ 1（无符号）
	TEST_AR_CMPI        12, cmp.ui, rd8, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, 0, 0x0000000000000001

	@@ 1 > 0 ⇒ 1（最小正差）
	TEST_AR_CMPI        13, cmp.ui, rd8, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000001, 0, 0x0000000000000001

	@@ 目的=源B：比较后再覆盖
	TEST_AR_CMPI        14, cmp.ui, rd8, 0x0000000000000005, rd8, 0x0000000000000005, 9, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_CMPI 15, cmp.ui, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
