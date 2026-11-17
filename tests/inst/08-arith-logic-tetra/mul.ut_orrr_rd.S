@@ mul.ut_orrr_rd.S — mul.ut rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x30）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：mul.ut_orrr_rd　形式：orrr　opc：0x41／ha 0x30　mask：0xFFFC0000　value：0x41C00000　目的银行：RD
@@ 语义：rdHB ← 零扩展((rdHC[31:0] × rdHD[31:0])[31:0])；高位静默丢弃
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：只留积的低 32 位、零扩展（0x80000000 ≠ 负）、32 位以上的高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 15（链例 17 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 × rd7（3×5=15）的规范编码字
	@@ 规范编码字 0x41C05187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000000000003
	set.rd	rd7, 0x0000000000000005
	.dd.t32	0x41C05187
	__CHECK_RD   1, rd5, 0x000000000000000F

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 0x80000000×1 ⇒ 零扩展
	@@ 规范编码字 0x41C3F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x0000000080000000
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x41C3F042
	__CHECK_RD   2, rd63, 0x0000000080000000

	@@ [3] 3 × 5 = 15
	TEST_AR_ORRR        3, mul.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000003, rd7, 0x0000000000000005, 0x000000000000000F

	@@ [4] 0xFFFFFFFF × 3 = 0x2FFFFFFFD ⇒ 低 32 位 0xFFFFFFFD
	TEST_AR_ORRR        4, mul.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000003, 0x00000000FFFFFFFD

	@@ [5] 0xFFFFFFFF × 0xFFFFFFFF = 1
	TEST_AR_ORRR        5, mul.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x00000000FFFFFFFF, 0x0000000000000001

	@@ [6] 源的高 32 位不参与：0xFFFFFFFF_00000003 × 0x12345678_00000005 = 15
	TEST_AR_ORRR        6, mul.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000003, rd7, 0x1234567800000005, 0x000000000000000F

	@@ [7] 0x00010000 × 0x00010000 = 0x100000000 ⇒ 0
	TEST_AR_ORRR        7, mul.ut, rd5, 0x0000000000000000, rd6, 0x0000000000010000, rd7, 0x0000000000010000, 0x0000000000000000

	@@ [8] 0x80000000 × 1 ⇒ 零扩展（高 32 位为 0，与 .st 相反）
	TEST_AR_ORRR        8, mul.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0x0000000080000000

	@@ [9] 0x7FFFFFFF × 0x7FFFFFFF ⇒ 低 32 位 1
	TEST_AR_ORRR        9, mul.ut, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x000000007FFFFFFF, 0x0000000000000001

	@@ [10] 0x80000000 × 2 = 0x100000000 ⇒ 0
	TEST_AR_ORRR       10, mul.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000002, 0x0000000000000000

	@@ [11] 0x0000FFFF × 0x0000FFFF = 0xFFFE0001 ⇒ 零扩展
	TEST_AR_ORRR       11, mul.ut, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x000000000000FFFF, 0x00000000FFFE0001

	@@ [12] rd0 作源：0 × 7 = 0
	TEST_AR_ORRR       12, mul.ut, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [13] 源=目（原地）：rd9 = rd9 × 3
	TEST_AR_ORRR       13, mul.ut, rd9, 0x0000000000000005, rd9, 0x0000000000000005, rd10, 0x0000000000000003, 0x000000000000000F

	@@ [14] 目=源D（原地）：rd9 旧值 3 是乘数
	TEST_AR_ORRR       14, mul.ut, rd9, 0x0000000000000003, rd10, 0x0000000000000005, rd9, 0x0000000000000003, 0x000000000000000F

	@@ [15] 两源同名：0x00010001² 的低 32 位
	TEST_AR_ORRR       15, mul.ut, rd12, 0x0000000000000000, rd11, 0x0000000000010001, rd11, 0x0000000000010001, 0x0000000000020001

	@@ [16] （YAML semantic 并入）0x32 × 0x1E = 0x5DC
	TEST_AR_ORRR       16, mul.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000032, rd7, 0x000000000000001E, 0x00000000000005DC

	@@ [17] （YAML boundary 并入）0x80 × 0x80 = 0x4000
	TEST_AR_ORRR       17, mul.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000080, rd7, 0x0000000000000080, 0x0000000000004000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       18, mul.ut, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
