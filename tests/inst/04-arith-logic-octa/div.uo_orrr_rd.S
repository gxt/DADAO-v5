@@ div.uo_orrr_rd.S — div.uo rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x38）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：div.uo_orrr_rd　形式：orrr　opc：0x40／ha 0x38　mask：0xFFFC0000　value：0x40E00000　目的银行：RD
@@ 语义：rdHB ← rdHC ÷ rdHD（无符号，向零截断）；**÷0 ⇒ 全 1**；无无符号溢出
@@ 合法性：目的 rdHA/rdHB 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[19:18] | hb[17:12] | hc[11:6] | hd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 5 / overlap 3（链例 15 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 / rd7 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40E05187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0000000000000064
	__LI	rd7, 0x0000000000000007
	.dd.t32	0x40E05187
	__CHECK_RD   1, rd5, 0x000000000000000E

	@@ 最高寄存器三字段（rd63）的编码字（字段边界）
	@@ 规范编码字 0x40E3F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	__LI	rd63, 0x0000000000000000
	__LI	rd1, 0xFFFFFFFFFFFFFFFF
	__LI	rd2, 0x0000000000000001
	.dd.t32	0x40E3F042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ 100 / 7 = 14（截断）
	TEST_AR_ORRR         3, div.uo, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000007, 0x000000000000000E

	@@ 1 / 1 = 1
	TEST_AR_ORRR         4, div.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x0000000000000001, 0x0000000000000001

	@@ 0 / 7 = 0
	TEST_AR_ORRR         5, div.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ 7 / 8 = 0（向零截断）
	TEST_AR_ORRR         6, div.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000007, rd7, 0x0000000000000008, 0x0000000000000000

	@@ rd0 作被除数：0 / 7 = 0
	TEST_AR_ORRR         7, div.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ 除数为 0 ⇒ 全 1（定值，不触发异常）
	TEST_AR_ORRR         8, div.uo, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ max / 1 = max
	TEST_AR_ORRR         9, div.uo, rd6, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	@@ max / 2 = 0x7FFF..F
	TEST_AR_ORRR        10, div.uo, rd6, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0000000000000002, 0x7FFFFFFFFFFFFFFF

	@@ 1 / max = 0
	TEST_AR_ORRR        11, div.uo, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000001, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000

	@@ max / max = 1
	TEST_AR_ORRR        12, div.uo, rd6, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000001

	@@ 目的=源C（原地）
	TEST_AR_ORRR        13, div.uo, rd9, 0x0000000000000064, rd9, 0x0000000000000064, rd10, 0x0000000000000007, 0x000000000000000E

	@@ 目的=源D（原地）
	TEST_AR_ORRR        14, div.uo, rd9, 0x0000000000000007, rd10, 0x0000000000000064, rd9, 0x0000000000000007, 0x000000000000000E

	@@ 两源同名 ⇒ 1
	TEST_AR_ORRR        15, div.uo, rd9, 0x0000000000000000, rd11, 0x0000000000003039, rd11, 0x0000000000003039, 0x0000000000000001

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     16, div.uo, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
