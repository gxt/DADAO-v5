@@ cmp.si_rrii_rd.S — cmp.si rdHA, rdHB, imms12（rrii, opc 0x5D）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：cmp.si_rrii_rd　形式：rrii　opc：0x5D　mask：0xFF000000　value：0x5D000000　目的银行：RD
@@ 语义：rdHA ← 比较(有符号 rdHB, 符号扩展 imms12)：< ⇒ -1、== ⇒ 0、> ⇒ 1（写满 64 位）
@@ 合法性：目的 rdHA/rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrii = opc | rdha[23:18] | rdhb[17:12] | imm12[11:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = cmp(rd6, -2048) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x5D146800（opc<<24 | rd5<<18 | rd6<<12 | imm12）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x5D146800
	__CHECK_RD   1, rd5, 0x0000000000000001

	@@ 目的=源（rd63）+ 最大正立即数 2047 的编码字
	@@ 规范编码字 0x5DFFF7FF（opc<<24 | rd63<<18 | rd63<<12 | imm12）
	set.rd	rd63, 0x00000000000007FF
	.dd.t32	0x5DFFF7FF
	__CHECK_RD   2, rd63, 0x0000000000000000

	@@ -1 < 0 ⇒ -1
	TEST_AR_CMPI         3, cmp.si, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0xFFFFFFFFFFFFFFFF

	@@ 0 == 0 ⇒ 0
	TEST_AR_CMPI         4, cmp.si, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 0, 0x0000000000000000

	@@ 1 > 0 ⇒ 1
	TEST_AR_CMPI         5, cmp.si, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, 0, 0x0000000000000001

	@@ rd0 作源（读出 0）：0 > -1 ⇒ 1（立即数符号扩展）
	TEST_AR_CMPI         6, cmp.si, rd5, 0x0000000000000000, rd0, 0x0000000000000000, -1, 0x0000000000000001

	@@ rd0 作源：0 == 0 ⇒ 0
	TEST_AR_CMPI         7, cmp.si, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 0, 0x0000000000000000

	@@ INT64_MIN vs imms12 最小 −2048：INT64_MIN 更小 ⇒ -1
	TEST_AR_CMPI         8, cmp.si, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x8000000000000000, -2048, 0xFFFFFFFFFFFFFFFF

	@@ b = −2049（imms12 装不下）< 最小 −2048 ⇒ -1
	TEST_AR_CMPI         9, cmp.si, rd6, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFF7FF, -2048, 0xFFFFFFFFFFFFFFFF

	@@ imms12 最大 2047：0 < 2047 ⇒ -1
	TEST_AR_CMPI        10, cmp.si, rd6, 0x0000000000000000, rd7, 0x0000000000000000, 2047, 0xFFFFFFFFFFFFFFFF

	@@ 0x8000..0（负数）< -1 ⇒ -1（符号比较）
	TEST_AR_CMPI        11, cmp.si, rd8, 0x0000000000000000, rd7, 0x8000000000000000, -1, 0xFFFFFFFFFFFFFFFF

	@@ max（正数）> 2047 ⇒ 1
	TEST_AR_CMPI        12, cmp.si, rd8, 0x0000000000000000, rd7, 0x7FFFFFFFFFFFFFFF, 2047, 0x0000000000000001

	@@ imms12 最小 −2048 == −2048 ⇒ 0
	TEST_AR_CMPI        13, cmp.si, rd8, 0xFFFFFFFFFFFFFFFF, rd7, 0xFFFFFFFFFFFFF800, -2048, 0x0000000000000000

	@@ 目的=源B：比较后再覆盖
	TEST_AR_CMPI        14, cmp.si, rd8, 0x0000000000000005, rd8, 0x0000000000000005, 9, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_CMPI 15, cmp.si, ILLI, rd0, rd6, -1

	__TEST_SECTIONS
