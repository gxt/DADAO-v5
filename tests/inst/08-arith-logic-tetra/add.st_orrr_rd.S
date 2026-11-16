@@ add.st_orrr_rd.S — add.st rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x21）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：add.st_orrr_rd　形式：orrr　opc：0x41／ha 0x21　mask：0xFFFC0000　value：0x41840000　目的银行：RD
@@ 语义：rdHB ← 符号扩展(rdHC[31:0] + rdHD[31:0])；32 位进位静默丢弃
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；两源/源=目允许
@@ 边界/覆盖：边界：进位丢弃、INT32 上/下界、32 位以上的高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 15（链例 17 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 + rd7（1+2=3）的规范编码字
	@@ 规范编码字 0x41845187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000000000001
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x41845187
	__CHECK_RD   1, rd5, 0x0000000000000003

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 0x7FFFFFFF+1 ⇒ 符号扩展为负
	@@ 规范编码字 0x4187F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x000000007FFFFFFF
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x4187F042
	__CHECK_RD   2, rd63, 0xFFFFFFFF80000000

	@@ [3] 1 + 2 = 3（正数）
	TEST_AR_ORRR        3, add.st, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x0000000000000002, 0x0000000000000003

	@@ [4] −1 + 1 = 0（跨零）
	TEST_AR_ORRR        4, add.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [5] −1 + −1 = −2 ⇒ 符号扩展全 1 高位
	TEST_AR_ORRR        5, add.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x00000000FFFFFFFF, 0xFFFFFFFFFFFFFFFE

	@@ [6] 源的高 32 位不参与：0xDEADBEEF_00000005 + 0x11111111_00000003 = 8
	TEST_AR_ORRR        6, add.st, rd5, 0x0000000000000000, rd6, 0xDEADBEEF00000005, rd7, 0x1111111100000003, 0x0000000000000008

	@@ [7] 0x7FFFFFFF + 0x7FFFFFFF = 0xFFFFFFFE（溢出静默丢弃）
	TEST_AR_ORRR        7, add.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x000000007FFFFFFF, 0xFFFFFFFFFFFFFFFE

	@@ [8] 0xFFFFFFFF + 0xFFFFFFFF = 0xFFFFFFFE（进位出 32 位丢弃）
	TEST_AR_ORRR        8, add.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x00000000FFFFFFFF, 0xFFFFFFFFFFFFFFFE

	@@ [9] 上界：0x7FFFFFFF + 0 = 0x7FFFFFFF
	TEST_AR_ORRR        9, add.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x0000000000000000, 0x000000007FFFFFFF

	@@ [10] 下界：0x80000000 + 0 ⇒ 0xFFFFFFFF_80000000
	TEST_AR_ORRR       10, add.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000000, 0xFFFFFFFF80000000

	@@ [11] 0x80000000 + 0x7FFFFFFF = 0xFFFFFFFF ⇒ −1
	TEST_AR_ORRR       11, add.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x000000007FFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ [12] rd0 作源（读出 0）：0 + 5 = 5
	TEST_AR_ORRR       12, add.st, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000005

	@@ [13] 源=目（原地）：rd9 = rd9 + 2
	TEST_AR_ORRR       13, add.st, rd9, 0x00000000FFFFFFFF, rd9, 0x00000000FFFFFFFF, rd10, 0x0000000000000002, 0x0000000000000001

	@@ [14] 目=源D（原地）：rd9 旧值 2 是加数
	TEST_AR_ORRR       14, add.st, rd9, 0x0000000000000002, rd10, 0x00000000FFFFFFFF, rd9, 0x0000000000000002, 0x0000000000000001

	@@ [15] 两源同名：x + x = 0xFFFFFFFE
	TEST_AR_ORRR       15, add.st, rd12, 0x0000000000000000, rd11, 0x000000007FFFFFFF, rd11, 0x000000007FFFFFFF, 0xFFFFFFFFFFFFFFFE

	@@ [16] （YAML semantic 并入）0x32 + 0x1E = 0x50
	TEST_AR_ORRR       16, add.st, rd5, 0x0000000000000000, rd6, 0x0000000000000032, rd7, 0x000000000000001E, 0x0000000000000050

	@@ [17] （YAML boundary 并入）0x40 + 0x40 = 0x80
	TEST_AR_ORRR       17, add.st, rd5, 0x0000000000000000, rd6, 0x0000000000000040, rd7, 0x0000000000000040, 0x0000000000000080

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       18, add.st, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
