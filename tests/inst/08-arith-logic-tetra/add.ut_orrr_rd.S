@@ add.ut_orrr_rd.S — add.ut rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x20）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：add.ut_orrr_rd　形式：orrr　opc：0x41／ha 0x20　mask：0xFFFC0000　value：0x41800000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rdHC[31:0] + rdHD[31:0])；32 位进位静默丢弃
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：进位丢弃、0x80000000 不作符号扩展、32 位以上的高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic+boundary+overlap 15（链例 17 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 + rd7（1+2=3）的规范编码字
	@@ 规范编码字 0x41805187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	__LI	rd6, 0x0000000000000001
	__LI	rd7, 0x0000000000000002
	.dd.t32	0x41805187
	__CHECK_RD   1, rd5, 0x0000000000000003

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 0x7FFFFFFF+1 ⇒ **零**扩展（与 .st 相反）
	@@ 规范编码字 0x4183F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	__LI	rd1, 0x000000007FFFFFFF
	__LI	rd2, 0x0000000000000001
	.dd.t32	0x4183F042
	__CHECK_RD   2, rd63, 0x0000000080000000

	@@ [3] 1 + 2 = 3
	TEST_AR_ORRR        3, add.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x0000000000000002, 0x0000000000000003

	@@ [4] 0xFFFFFFFF + 1 = 0（进位丢弃）
	TEST_AR_ORRR        4, add.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [5] 0xFFFFFFFF + 0xFFFFFFFF = 0xFFFFFFFE
	TEST_AR_ORRR        5, add.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x00000000FFFFFFFF, 0x00000000FFFFFFFE

	@@ [6] 源的高 32 位不参与：0xFFFFFFFF_00000005 + 0x12345678_00000003 = 8
	TEST_AR_ORRR        6, add.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000005, rd7, 0x1234567800000003, 0x0000000000000008

	@@ [7] 0x7FFFFFFF + 0x7FFFFFFF = 0xFFFFFFFE
	TEST_AR_ORRR        7, add.ut, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x000000007FFFFFFF, 0x00000000FFFFFFFE

	@@ [8] 0x80000000 + 0x80000000 = 0（进位出 32 位丢弃）
	TEST_AR_ORRR        8, add.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000080000000, 0x0000000000000000

	@@ [9] 上界：0x7FFFFFFF + 0
	TEST_AR_ORRR        9, add.ut, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x0000000000000000, 0x000000007FFFFFFF

	@@ [10] 0x80000000 + 0 ⇒ 零扩展（高 32 位必须为 0）
	TEST_AR_ORRR       10, add.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000000, 0x0000000080000000

	@@ [11] 0 + 0xFFFFFFFF = 0xFFFFFFFF
	TEST_AR_ORRR       11, add.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x00000000FFFFFFFF, 0x00000000FFFFFFFF

	@@ [12] rd0 作源（读出 0）：0 + 5 = 5
	TEST_AR_ORRR       12, add.ut, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000005

	@@ [13] 源=目（原地）：rd9 = rd9 + 2
	TEST_AR_ORRR       13, add.ut, rd9, 0x00000000FFFFFFFF, rd9, 0x00000000FFFFFFFF, rd10, 0x0000000000000002, 0x0000000000000001

	@@ [14] 目=源D（原地）：rd9 旧值 2 是加数
	TEST_AR_ORRR       14, add.ut, rd9, 0x0000000000000002, rd10, 0x00000000FFFFFFFF, rd9, 0x0000000000000002, 0x0000000000000001

	@@ [15] 两源同名：x + x
	TEST_AR_ORRR       15, add.ut, rd12, 0x0000000000000000, rd11, 0x000000007FFFFFFF, rd11, 0x000000007FFFFFFF, 0x00000000FFFFFFFE

	@@ [16] （YAML semantic 并入）0x32 + 0x1E = 0x50
	TEST_AR_ORRR       16, add.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000032, rd7, 0x000000000000001E, 0x0000000000000050

	@@ [17] （YAML boundary 并入）0x80 + 0x80 = 0x100
	TEST_AR_ORRR       17, add.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000000100

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       18, add.ut, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
