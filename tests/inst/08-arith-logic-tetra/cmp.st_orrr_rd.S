@@ cmp.st_orrr_rd.S — cmp.st rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x2B）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：cmp.st_orrr_rd　形式：orrr　opc：0x41／ha 0x2B　mask：0xFFFC0000　value：0x41AC0000　目的银行：RD
@@ 语义：rdHB ← −1/0/1（**写满 64 位**：−1 ⇒ 0xFFFFFFFFFFFFFFFF）；源按 bits[31:0] 有符号比较
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：−1 的 64 位写满、INT32 上/下界、32 位以上的高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 15（链例 17 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = cmp.st(rd6, rd7)（−1 vs 0 ⇒ −1）的规范编码字
	@@ 规范编码字 0x41AC5187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x00000000FFFFFFFF
	set.rd	rd7, 0x0000000000000000
	.dd.t32	0x41AC5187
	__CHECK_RD   1, rd5, 0xFFFFFFFFFFFFFFFF

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 1 vs 2 ⇒ −1
	@@ 规范编码字 0x41AFF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x0000000000000002
	.dd.t32	0x41AFF042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [3] 1 vs 2 ⇒ −1（写满 64 位）
	TEST_AR_ORRR        3, cmp.st, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [4] 2 vs 1 ⇒ +1
	TEST_AR_ORRR        4, cmp.st, rd5, 0x0000000000000000, rd6, 0x0000000000000002, rd7, 0x0000000000000001, 0x0000000000000001

	@@ [5] 相等 ⇒ 0
	TEST_AR_ORRR        5, cmp.st, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [6] −1 vs 0 ⇒ −1（有符号）
	TEST_AR_ORRR        6, cmp.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ [7] 0 vs −1 ⇒ +1
	TEST_AR_ORRR        7, cmp.st, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x00000000FFFFFFFF, 0x0000000000000001

	@@ [8] 源的高 32 位不参与：0xFFFFFFFF_00000001 vs 0x00000001_00000002 ⇒ −1（按低 32 位）
	TEST_AR_ORRR        8, cmp.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000001, rd7, 0x0000000100000002, 0xFFFFFFFFFFFFFFFF

	@@ [9] INT32_MIN vs INT32_MAX ⇒ −1
	TEST_AR_ORRR        9, cmp.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x000000007FFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ [10] INT32_MAX vs INT32_MIN ⇒ +1
	TEST_AR_ORRR       10, cmp.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x0000000080000000, 0x0000000000000001

	@@ [11] −1 vs 0x7FFFFFFF ⇒ −1
	TEST_AR_ORRR       11, cmp.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x000000007FFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ [12] 相等但高位不同：0x80000000 vs 0x0000000080000000 ⇒ 0
	TEST_AR_ORRR       12, cmp.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000080000000, 0x0000000000000000

	@@ [13] rd0 作源：0 vs 0xFFFFFFFF ⇒ +1
	TEST_AR_ORRR       13, cmp.st, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x00000000FFFFFFFF, 0x0000000000000001

	@@ [14] 源=目（原地）
	TEST_AR_ORRR       14, cmp.st, rd9, 0x0000000000000001, rd9, 0x0000000000000001, rd10, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [15] 目=源D（原地）
	TEST_AR_ORRR       15, cmp.st, rd9, 0x0000000000000002, rd10, 0x0000000000000001, rd9, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [16] 两源同名：x vs x ⇒ 0
	TEST_AR_ORRR       16, cmp.st, rd12, 0x0000000000000000, rd11, 0x0000000080000000, rd11, 0x0000000080000000, 0x0000000000000000

	@@ [17] （YAML semantic 并入）0xA vs 0x14 ⇒ −1
	TEST_AR_ORRR       17, cmp.st, rd5, 0x0000000000000000, rd6, 0x000000000000000A, rd7, 0x0000000000000014, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       18, cmp.st, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
