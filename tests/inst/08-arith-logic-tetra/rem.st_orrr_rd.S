@@ rem.st_orrr_rd.S — rem.st rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x3B）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：rem.st_orrr_rd　形式：orrr　opc：0x41／ha 0x3B　mask：0xFFFC0000　value：0x41EC0000　目的银行：RD
@@ 语义：rdHB ← 符号扩展(rdHC[31:0] mod rdHD[31:0])；余数符号 = 被除数符号；除零 ⇒ 被除数（符号扩展）、INT32_MIN mod −1 ⇒ 0（定值，不抛异常）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：余数符号随被除数（C99）、除零定值、溢出定值
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 19（链例 21 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 mod rd7（7 mod 2 = 1）的规范编码字
	@@ 规范编码字 0x41EC5187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000000000007
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x41EC5187
	__CHECK_RD   1, rd5, 0x0000000000000001

	@@ [encoding 2] 最高寄存器作目的（rd63）+ −7 mod 2 = −1 ⇒ 全 1
	@@ 规范编码字 0x41EFF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x00000000FFFFFFF9
	set.rd	rd2, 0x0000000000000002
	.dd.t32	0x41EFF042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [3] 7 mod 2 = 1
	TEST_AR_ORRR        3, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x0000000000000002, 0x0000000000000001

	@@ [4] −7 mod 2 = −1 ⇒ 0xFFFFFFFFFFFFFFFF（符号随被除数）
	TEST_AR_ORRR        4, rem.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFF9, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [5] 7 mod −2 = 1
	TEST_AR_ORRR        5, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x00000000FFFFFFFE, 0x0000000000000001

	@@ [6] −7 mod −2 = −1
	TEST_AR_ORRR        6, rem.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFF9, rd7, 0x00000000FFFFFFFE, 0xFFFFFFFFFFFFFFFF

	@@ [7] 源的高 32 位不参与：0xFFFFFFFF_FFFFFFF9 mod 2 = −1
	TEST_AR_ORRR        7, rem.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFF9, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [8] 除零 ⇒ 被除数（符号扩展，定值）
	TEST_AR_ORRR        8, rem.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFF9, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFF9

	@@ [9] INT32_MIN mod −1 ⇒ 0（溢出定值）
	TEST_AR_ORRR        9, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [10] INT32_MIN mod 1 ⇒ 0
	TEST_AR_ORRR       10, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [11] 5 mod 3 = 2
	TEST_AR_ORRR       11, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000000000005, rd7, 0x0000000000000003, 0x0000000000000002

	@@ [12] 1 mod −1 = 0
	TEST_AR_ORRR       12, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [13] rd0 作源：0 mod 5 = 0
	TEST_AR_ORRR       13, rem.st, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [14] 源=目（原地）：rd9 = rd9 mod 4
	TEST_AR_ORRR       14, rem.st, rd9, 0x00000000FFFFFFF9, rd9, 0x00000000FFFFFFF9, rd10, 0x0000000000000004, 0xFFFFFFFFFFFFFFFD

	@@ [15] 目=源D（原地）：rd9 旧值 4 是除数
	TEST_AR_ORRR       15, rem.st, rd9, 0x0000000000000004, rd10, 0x00000000FFFFFFF9, rd9, 0x0000000000000004, 0xFFFFFFFFFFFFFFFD

	@@ [16] 两源同名：x mod x = 0
	TEST_AR_ORRR       16, rem.st, rd12, 0x0000000000000000, rd11, 0x0000000000000007, rd11, 0x0000000000000007, 0x0000000000000000

	@@ [17] （YAML semantic 并入）0x64 mod 7 = 2
	TEST_AR_ORRR       17, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000007, 0x0000000000000002

	@@ [18] （YAML boundary 并入）0x80 mod 7 = 2
	TEST_AR_ORRR       18, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000007, 0x0000000000000002

	@@ [19] （YAML semantic 并入）0x64 mod 0 ⇒ 0x64（除零定值 = 被除数）
	TEST_AR_ORRR       19, rem.st, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000000, 0x0000000000000064

	@@ [20] （YAML encoding 并入）rdhd=rd0 合法：0x64 mod 0（rd0 作除数）⇒ 0x64
	TEST_AR_ORRR       20, rem.st, rd5, 0x0000000000000001, rd6, 0x0000000000000064, rd0, 0x0000000000000000, 0x0000000000000064

	@@ [21] （YAML semantic 并入）INT32_MIN mod −1（源带高位垃圾）⇒ 0（溢出定值）
	TEST_AR_ORRR       21, rem.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF80000000, rd7, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [22] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       22, rem.st, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
