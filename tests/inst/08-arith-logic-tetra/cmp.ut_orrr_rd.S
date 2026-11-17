@@ cmp.ut_orrr_rd.S — cmp.ut rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x2A）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：cmp.ut_orrr_rd　形式：orrr　opc：0x41／ha 0x2A　mask：0xFFFC0000　value：0x41A80000　目的银行：RD
@@ 语义：rdHB ← −1/0/1（写满 64 位）；源按 bits[31:0] **无符号**比较
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：0xFFFFFFFF 按无符号大于 1（与 .st 相反）、−1 写满、32 位以上的高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 14（链例 16 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = cmp.ut(rd6, rd7)（0xFFFFFFFF vs 1 ⇒ +1）的规范编码字
	@@ 规范编码字 0x41A85187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x00000000FFFFFFFF
	set.rd	rd7, 0x0000000000000001
	.dd.t32	0x41A85187
	__CHECK_RD   1, rd5, 0x0000000000000001

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 0 vs 0xFFFFFFFF ⇒ −1
	@@ 规范编码字 0x41ABF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x0000000000000000
	set.rd	rd2, 0x00000000FFFFFFFF
	.dd.t32	0x41ABF042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [3] 1 vs 2 ⇒ −1（写满 64 位）
	TEST_AR_ORRR        3, cmp.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [4] 0xFFFFFFFF vs 0x00000001 ⇒ +1（无符号，与 .st 的 −1 相反）
	TEST_AR_ORRR        4, cmp.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000001, 0x0000000000000001

	@@ [5] 相等 ⇒ 0
	TEST_AR_ORRR        5, cmp.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [6] 0x80000000 vs 0x7FFFFFFF ⇒ +1
	TEST_AR_ORRR        6, cmp.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x000000007FFFFFFF, 0x0000000000000001

	@@ [7] 0x7FFFFFFF vs 0x80000000 ⇒ −1
	TEST_AR_ORRR        7, cmp.ut, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x0000000080000000, 0xFFFFFFFFFFFFFFFF

	@@ [8] 源的高 32 位不参与：0xFFFFFFFF_00000001 vs 0x00000001_00000000 ⇒ 0
	TEST_AR_ORRR        8, cmp.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000001, rd7, 0x0000000100000000, 0x0000000000000001

	@@ [9] 0 vs 0xFFFFFFFF ⇒ −1
	TEST_AR_ORRR        9, cmp.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x00000000FFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ [10] 上界相等：0xFFFFFFFF vs 0xFFFFFFFF ⇒ 0
	TEST_AR_ORRR       10, cmp.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [11] 0x80000000 vs 0 ⇒ +1
	TEST_AR_ORRR       11, cmp.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000000, 0x0000000000000001

	@@ [12] rd0 作源：0 vs 1 ⇒ −1
	TEST_AR_ORRR       12, cmp.ut, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	@@ [13] 源=目（原地）
	TEST_AR_ORRR       13, cmp.ut, rd9, 0x0000000000000001, rd9, 0x0000000000000001, rd10, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [14] 目=源D（原地）
	TEST_AR_ORRR       14, cmp.ut, rd9, 0x0000000000000002, rd10, 0x0000000000000001, rd9, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [15] 两源同名：x vs x ⇒ 0
	TEST_AR_ORRR       15, cmp.ut, rd12, 0x0000000000000000, rd11, 0x00000000FFFFFFFF, rd11, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [16] （YAML semantic 并入）0xA vs 0x14 ⇒ −1（写满 64 位，ADR-0037 D1 的位型前提）
	TEST_AR_ORRR       16, cmp.ut, rd5, 0x0000000000000000, rd6, 0x000000000000000A, rd7, 0x0000000000000014, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       17, cmp.ut, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
