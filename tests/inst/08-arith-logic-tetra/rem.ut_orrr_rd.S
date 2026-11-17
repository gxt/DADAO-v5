@@ rem.ut_orrr_rd.S — rem.ut rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x3A）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：rem.ut_orrr_rd　形式：orrr　opc：0x41／ha 0x3A　mask：0xFFFC0000　value：0x41E80000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rdHC[31:0] mod rdHD[31:0])（无符号）；除零 ⇒ 被除数（零扩展，定值）；无溢出
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；两源/源=目允许
@@ 边界/覆盖：边界：除零定值、0x80000000 按无符号、32 位以上的高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 16（链例 18 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 mod rd7（7 mod 2 = 1）的规范编码字
	@@ 规范编码字 0x41E85187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000000000007
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x41E85187
	__CHECK_RD   1, rd5, 0x0000000000000001

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 0xFFFFFFFF mod 0x10 = 0xF
	@@ 规范编码字 0x41EBF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x00000000FFFFFFFF
	set.rd	rd2, 0x0000000000000010
	.dd.t32	0x41EBF042
	__CHECK_RD   2, rd63, 0x000000000000000F

	@@ [3] 7 mod 2 = 1
	TEST_AR_ORRR        3, rem.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000007, rd7, 0x0000000000000002, 0x0000000000000001

	@@ [4] 0xFFFFFFFF mod 0x10 = 0xF
	TEST_AR_ORRR        4, rem.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000010, 0x000000000000000F

	@@ [5] 0xFFFFFFFF mod 0xFFFFFFFF = 0
	TEST_AR_ORRR        5, rem.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [6] 源的高 32 位不参与：0xFFFFFFFF_FFFFFFFF mod 0x10 = 0xF
	TEST_AR_ORRR        6, rem.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000010, 0x000000000000000F

	@@ [7] 除零 ⇒ 被除数（零扩展定值）
	TEST_AR_ORRR        7, rem.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000000, 0x00000000FFFFFFFF

	@@ [8] 0x80000000 mod 0x10 = 0（按无符号）
	TEST_AR_ORRR        8, rem.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000010, 0x0000000000000000

	@@ [9] 0x80000000 mod 0xFFFFFFFF = 0x80000000
	TEST_AR_ORRR        9, rem.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x00000000FFFFFFFF, 0x0000000080000000

	@@ [10] 上界：0xFFFFFFFF mod 1 = 0
	TEST_AR_ORRR       10, rem.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [11] 3 mod 4 = 3
	TEST_AR_ORRR       11, rem.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000003, rd7, 0x0000000000000004, 0x0000000000000003

	@@ [12] rd0 作源：0 mod 5 = 0
	TEST_AR_ORRR       12, rem.ut, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [13] 源=目（原地）：rd9 = rd9 mod 4
	TEST_AR_ORRR       13, rem.ut, rd9, 0x00000000FFFFFFFF, rd9, 0x00000000FFFFFFFF, rd10, 0x0000000000000004, 0x0000000000000003

	@@ [14] 目=源D（原地）：rd9 旧值 4 是除数
	TEST_AR_ORRR       14, rem.ut, rd9, 0x0000000000000004, rd10, 0x00000000FFFFFFFF, rd9, 0x0000000000000004, 0x0000000000000003

	@@ [15] 两源同名：x mod x = 0
	TEST_AR_ORRR       15, rem.ut, rd12, 0x0000000000000000, rd11, 0x00000000FFFFFFFF, rd11, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [16] （YAML semantic 并入）0x64 mod 7 = 2
	TEST_AR_ORRR       16, rem.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000007, 0x0000000000000002

	@@ [17] （YAML semantic 并入）0x64 mod 0 ⇒ 0x64（除零定值 = 被除数）
	TEST_AR_ORRR       17, rem.ut, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x0000000000000000, 0x0000000000000064

	@@ [18] （YAML encoding 并入）rdhd=rd0 合法：0x64 mod 0（rd0 作除数）⇒ 0x64
	TEST_AR_ORRR       18, rem.ut, rd5, 0x0000000000000001, rd6, 0x0000000000000064, rd0, 0x0000000000000000, 0x0000000000000064

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [19] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       19, rem.ut, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
