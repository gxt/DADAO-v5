@@ sub.st_orrr_rd.S — sub.st rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x29）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：sub.st_orrr_rd　形式：orrr　opc：0x41／ha 0x29　mask：0xFFFC0000　value：0x41A40000　目的银行：RD
@@ 语义：rdHB ← 符号扩展(rdHC[31:0] − rdHD[31:0])；借位静默丢弃
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：借位丢弃、INT32 上/下界、32 位以上的高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 14（链例 16 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 − rd7（5−3=2）的规范编码字
	@@ 规范编码字 0x41A45187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000000000005
	set.rd	rd7, 0x0000000000000003
	.dd.t32	0x41A45187
	__CHECK_RD   1, rd5, 0x0000000000000002

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 0 − 0x80000000 ⇒ 符号扩展为负
	@@ 规范编码字 0x41A7F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x0000000000000000
	set.rd	rd2, 0x0000000080000000
	.dd.t32	0x41A7F042
	__CHECK_RD   2, rd63, 0xFFFFFFFF80000000

	@@ [3] 1 − 3 = −2 ⇒ 高位全 1
	TEST_AR_ORRR        3, sub.st, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x0000000000000003, 0xFFFFFFFFFFFFFFFE

	@@ [4] −1 − 1 = −2
	TEST_AR_ORRR        4, sub.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFE

	@@ [5] −1 − −1 = 0
	TEST_AR_ORRR        5, sub.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [6] 源的高 32 位不参与：0xDEADBEEF_00000005 − 0x11111111_00000001 = 4
	TEST_AR_ORRR        6, sub.st, rd5, 0x0000000000000000, rd6, 0xDEADBEEF00000005, rd7, 0x1111111100000001, 0x0000000000000004

	@@ [7] 0 − 0x80000000 = 0x80000000 ⇒ 符号扩展（借位丢弃）
	TEST_AR_ORRR        7, sub.st, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x0000000080000000, 0xFFFFFFFF80000000

	@@ [8] 0x80000000 − 1 = 0x7FFFFFFF（下界绕回上界）
	TEST_AR_ORRR        8, sub.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0x000000007FFFFFFF

	@@ [9] 0x7FFFFFFF − 0xFFFFFFFF = 0x80000000 ⇒ 符号扩展
	TEST_AR_ORRR        9, sub.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x00000000FFFFFFFF, 0xFFFFFFFF80000000

	@@ [10] 上界：0x7FFFFFFF − 0 = 0x7FFFFFFF
	TEST_AR_ORRR       10, sub.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x0000000000000000, 0x000000007FFFFFFF

	@@ [11] rd0 作源：0 − 5 = −5
	TEST_AR_ORRR       11, sub.st, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0xFFFFFFFFFFFFFFFB

	@@ [12] 源=目（原地）：rd9 = rd9 − 2
	TEST_AR_ORRR       12, sub.st, rd9, 0x00000000FFFFFFFF, rd9, 0x00000000FFFFFFFF, rd10, 0x0000000000000002, 0xFFFFFFFFFFFFFFFD

	@@ [13] 目=源D（原地）：rd9 旧值 2 是减数
	TEST_AR_ORRR       13, sub.st, rd9, 0x0000000000000002, rd10, 0x00000000FFFFFFFF, rd9, 0x0000000000000002, 0xFFFFFFFFFFFFFFFD

	@@ [14] 两源同名：x − x = 0
	TEST_AR_ORRR       14, sub.st, rd12, 0x0000000000000000, rd11, 0x000000007FFFFFFF, rd11, 0x000000007FFFFFFF, 0x0000000000000000

	@@ [15] （YAML semantic 并入）0x32 − 0x1E = 0x14
	TEST_AR_ORRR       15, sub.st, rd5, 0x0000000000000000, rd6, 0x0000000000000032, rd7, 0x000000000000001E, 0x0000000000000014

	@@ [16] （YAML boundary 并入）0x40 − 0x40 = 0
	TEST_AR_ORRR       16, sub.st, rd5, 0x0000000000000000, rd6, 0x0000000000000040, rd7, 0x0000000000000040, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       17, sub.st, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
