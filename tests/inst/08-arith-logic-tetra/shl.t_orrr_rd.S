@@ shl.t_orrr_rd.S — shl.t rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x10）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：shl.t_orrr_rd　形式：orrr　opc：0x41／ha 0x10　mask：0xFFFC0000　value：0x41400000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rdHC[31:0] << shamt)；shamt = rdHD[4:0]（对 32 取模、**不** ILLI），结果零扩展写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；orrr 的移位量天然取低 5 位
@@ 边界/覆盖：边界：shamt 0/31/32/全 1（取模）、移出 32 位的高位丢弃、源高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 15 + 迁移 3（m13-testcases-045）（链例 20 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 << 2（0x0F0F0F0F ⇒ 0x3C3C3C3C）的规范编码字
	@@ 规范编码字 0x41405187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x000000000F0F0F0F
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x41405187
	__CHECK_RD   1, rd5, 0x000000003C3C3C3C

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 1 << 1
	@@ 规范编码字 0x4143F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x4143F042
	__CHECK_RD   2, rd63, 0x0000000000000002

	@@ [3] 0x0F0F0F0F << 2 = 0x3C3C3C3C，高 32 位为 0
	TEST_AR_ORRR        3, shl.t, rd5, 0x0000000000000000, rd6, 0x000000000F0F0F0F, rd7, 0x0000000000000002, 0x000000003C3C3C3C

	@@ [4] shamt 0 ⇒ 原值（只留低 32 位）
	TEST_AR_ORRR        4, shl.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0x00000000FFFFFFFF

	@@ [5] 0xFFFFFFFF << 1 = 0xFFFFFFFE（移出位丢弃）
	TEST_AR_ORRR        5, shl.t, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000001, 0x00000000FFFFFFFE

	@@ [6] 0x80000000 << 1 = 0（移到第 32 位 ⇒ 丢出 32 位窗口）
	TEST_AR_ORRR        6, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [7] 0x12345678 << 8 = 0x34567800
	TEST_AR_ORRR        7, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000012345678, rd7, 0x0000000000000008, 0x0000000034567800

	@@ [8] shamt 31：1 << 31 = 0x80000000（零扩展 ⇒ 高 32 位为 0）
	TEST_AR_ORRR        8, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000001F, 0x0000000080000000

	@@ [9] shamt 32 ⇒ 取低 5 位 = 0 ⇒ 原值（不触发 ILLI）
	TEST_AR_ORRR        9, shl.t, rd5, 0x0000000000000000, rd6, 0x000000000F0F0F0F, rd7, 0x0000000000000020, 0x000000000F0F0F0F

	@@ [10] shamt 全 1 ⇒ 低 5 位 = 31：1 << 31
	TEST_AR_ORRR       10, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x00000000FFFFFFFF, 0x0000000080000000

	@@ [11] 源的高 32 位不参与：0xFFFFFFFF_00000001 << 4 = 0x10
	TEST_AR_ORRR       11, shl.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000001, rd7, 0x0000000000000004, 0x0000000000000010

	@@ [12] rd0 作源：0 << 5 = 0
	TEST_AR_ORRR       12, shl.t, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [13] 源=目（原地）：rd9 << 8
	TEST_AR_ORRR       13, shl.t, rd9, 0x0000000001234567, rd9, 0x0000000001234567, rd10, 0x0000000000000008, 0x0000000023456700

	@@ [14] 目=源D（原地）：rd9 旧值 3 是移位量
	TEST_AR_ORRR       14, shl.t, rd9, 0x0000000000000003, rd10, 0x0000000000000001, rd9, 0x0000000000000003, 0x0000000000000008

	@@ [15] 两源同名：7 << 7 = 0x380
	TEST_AR_ORRR       15, shl.t, rd12, 0x0000000000000000, rd11, 0x0000000000000007, rd11, 0x0000000000000007, 0x0000000000000380

	@@ [16] （YAML semantic 并入）0x0F0F0F0F0F0F0F0F << 2 = 0x3C3C3C3C
	TEST_AR_ORRR       16, shl.t, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0x000000003C3C3C3C

	@@ [17] （YAML boundary 并入）0x0F0F0F0F0F0F0F0F << 31 = 0x80000000
	TEST_AR_ORRR       17, shl.t, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x000000000000001F, 0x0000000080000000

	@@ [18] 迁移（m13-testcases-045）：分散位型 0x21212121（每字节 0x21）<< 7 —— **DADAO 与 RISC-V 的分歧点**
	@@   手算：低 32 位 0x21212121 << 7 = 0x90909080；spec/SimRISC-08 §「shl.t」明定 [63:32] = 0
	@@   ⇒ 0x0000000090909080（RISC-V sllw 为符号扩展 0xFFFFFFFF90909080；本行**不取**该值）
	TEST_AR_ORRR       18, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000021212121, rd7, 0x0000000000000007, 0x0000000090909080

	@@ [19] 迁移：源高 32 位为全 1、低字 bit31=0 ⇒ 高半不参与且结果零扩展
	@@   手算：0x12345678 << 4 = 0x23456780（bit28-31 移出 32 位窗口）⇒ 0x0000000023456780
	TEST_AR_ORRR       19, shl.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF12345678, rd7, 0x0000000000000004, 0x0000000023456780

	@@ [20] 迁移：0x99345678 << 4 —— 低字 bit31=1，零扩展后**不得**出现高半 1
	@@   手算：0x99345678 << 4 = 0x93456780 + 移出位丢弃 ⇒ 0x0000000093456780（RISC-V sllw 给 0xFFFFFFFF93456780）
	TEST_AR_ORRR       20, shl.t, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000099345678, rd7, 0x0000000000000004, 0x0000000093456780

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       21, shl.t, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
