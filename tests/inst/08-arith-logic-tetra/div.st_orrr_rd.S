@@ div.st_orrr_rd.S — div.st rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x39）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：div.st_orrr_rd　形式：orrr　opc：0x41／ha 0x39　mask：0xFFFC0000　value：0x41E40000　目的银行：RD
@@ 语义：rdHB ← 符号扩展(rdHC[31:0] ÷ rdHD[31:0])；truncate-toward-zero；除零 ⇒ 0xFFFFFFFFFFFFFFFF、INT32_MIN÷−1 ⇒ 0xFFFFFFFF80000000（定值，不抛异常）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：符号四组合、除零、INT32_MIN÷−1 与 ÷1、|被除数|<|除数| ⇒ 0
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 19（链例 21 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 ÷ rd7（7÷2=3）的规范编码字
	@@ 规范编码字 0x41E45187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000000000007
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x41E45187
	__CHECK_RD   1, rd5, 0x0000000000000003

	@@ [encoding 2] 最高寄存器作目的（rd63）+ −7÷2 = −3 ⇒ 符号扩展
	@@ 规范编码字 0x41E7F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x00000000FFFFFFF9
	set.rd	rd2, 0x0000000000000002
	.dd.t32	0x41E7F042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFD

	@@ [3] 7 ÷ 2 = 3
	TEST_AR_ORRR        3, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x0000000000000002, 0x0000000000000003

	@@ [4] −7 ÷ 2 = −3（truncate toward zero）
	TEST_AR_ORRR        4, div.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFF9, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFD

	@@ [5] 7 ÷ −2 = −3
	TEST_AR_ORRR        5, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x00000000FFFFFFFE, 0xFFFFFFFFFFFFFFFD

	@@ [6] −7 ÷ −2 = 3
	TEST_AR_ORRR        6, div.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFF9, rd7, 0x00000000FFFFFFFE, 0x0000000000000003

	@@ [7] 源的高 32 位不参与：0xFFFFFFFF_FFFFFFF9 ÷ 2 = −3
	TEST_AR_ORRR        7, div.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFF9, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFD

	@@ [8] 除零 ⇒ 0xFFFFFFFFFFFFFFFF（定值，不触发异常）
	TEST_AR_ORRR        8, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ [9] INT32_MIN ÷ −1 ⇒ 0xFFFFFFFF80000000（溢出定值）
	TEST_AR_ORRR        9, div.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x00000000FFFFFFFF, 0xFFFFFFFF80000000

	@@ [10] INT32_MIN ÷ 1 ⇒ 0xFFFFFFFF80000000
	TEST_AR_ORRR       10, div.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0xFFFFFFFF80000000

	@@ [11] |被除数| < |除数| ⇒ 0（3 ÷ 4）
	TEST_AR_ORRR       11, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000003, rd7, 0x0000000000000004, 0x0000000000000000

	@@ [12] 1 ÷ −1 = −1
	TEST_AR_ORRR       12, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x00000000FFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ [13] rd0 作源：0 ÷ 5 = 0
	TEST_AR_ORRR       13, div.st, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [14] 源=目（原地）：rd9 = rd9 ÷ 2
	TEST_AR_ORRR       14, div.st, rd9, 0x00000000FFFFFFF9, rd9, 0x00000000FFFFFFF9, rd10, 0x0000000000000002, 0xFFFFFFFFFFFFFFFD

	@@ [15] 目=源D（原地）：rd9 旧值 2 是除数
	TEST_AR_ORRR       15, div.st, rd9, 0x0000000000000002, rd10, 0x00000000FFFFFFF9, rd9, 0x0000000000000002, 0xFFFFFFFFFFFFFFFD

	@@ [16] 两源同名：x ÷ x = 1
	TEST_AR_ORRR       16, div.st, rd12, 0x0000000000000000, rd11, 0x0000000000000007, rd11, 0x0000000000000007, 0x0000000000000001

	@@ [17] （YAML semantic 并入）0x64 ÷ 7 = 0xE
	TEST_AR_ORRR       17, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000007, 0x000000000000000E

	@@ [18] （YAML boundary 并入）0x80 ÷ 7 = 0x12
	TEST_AR_ORRR       18, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000007, 0x0000000000000012

	@@ [19] （YAML semantic 并入）0x64 ÷ 0 ⇒ 0xFFFFFFFFFFFFFFFF（除零定值）
	TEST_AR_ORRR       19, div.st, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ [20] （YAML encoding 并入）rdhd=rd0 合法：0x64 ÷ 0（rd0 作除数）⇒ 0xFFFFFFFFFFFFFFFF
	TEST_AR_ORRR       20, div.st, rd5, 0x0000000000000001, rd6, 0x0000000000000064, rd0, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ [21] （YAML semantic 并入）INT32_MIN ÷ −1（源带高位垃圾）⇒ 0xFFFFFFFF80000000（溢出定值）
	TEST_AR_ORRR       21, div.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF80000000, rd7, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFF80000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [22] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       22, div.st, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
