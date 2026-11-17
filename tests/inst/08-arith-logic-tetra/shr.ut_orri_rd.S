@@ shr.ut_orri_rd.S — shr.ut rdHB, rdHC, immu6（orri, opc 0x41／ha 0x1A）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：shr.ut_orri_rd　形式：orri　opc：0x41／ha 0x1A　mask：0xFFFC0000　value：0x41680000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rdHC[31:0] >> immu6)（逻辑右移）；immu6 ∈ 0..31，> 31 ⇒ ILLI
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 31 ⇒ ILLI（`encode_sbz`）；源可为 rd0；immu6 = 0 合法
@@ 边界/覆盖：边界：imm 0/1/31 合法、32 与 63 ILLI、结果零扩展
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 12 + 迁移 2（m13-testcases-045）（链例 16 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 >> 1（0x80000000 ⇒ 0x40000000）的规范编码字
	@@ 规范编码字 0x41685181（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 1）
	set.rd	rd6, 0x0000000080000000
	.dd.t32	0x41685181
	__CHECK_RD   1, rd5, 0x0000000040000000

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 0x80000000 >> 31 = 1（imm 字段上界）
	@@ 规范编码字 0x416BF05F（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 31）
	set.rd	rd1, 0x0000000080000000
	.dd.t32	0x416BF05F
	__CHECK_RD   2, rd63, 0x0000000000000001

	@@ [3] 0x80000000 >> 1 = 0x40000000
	TEST_AR_ORRI        3, shr.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, 1, 0x0000000040000000

	@@ [4] 0xFFFFFFFF >> 1 = 0x7FFFFFFF
	TEST_AR_ORRI        4, shr.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, 1, 0x000000007FFFFFFF

	@@ [5] imm 0 ⇒ 原值（只留低 32 位）
	TEST_AR_ORRI        5, shr.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0x00000000FFFFFFFF

	@@ [6] imm 31：0x80000000 >> 31 = 1
	TEST_AR_ORRI        6, shr.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, 31, 0x0000000000000001

	@@ [7] 0x12345678 >> 8 = 0x00123456
	TEST_AR_ORRI        7, shr.ut, rd5, 0x0000000000000000, rd6, 0x0000000012345678, 8, 0x0000000000123456

	@@ [8] imm 16：0xFFFF0000 >> 16 = 0x0000FFFF
	TEST_AR_ORRI        8, shr.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFF0000, 16, 0x000000000000FFFF

	@@ [9] 源的高 32 位不参与：0xFFFFFFFF_80000000 >> 1 = 0x40000000
	TEST_AR_ORRI        9, shr.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF80000000, 1, 0x0000000040000000

	@@ [10] rd0 作源：0 >> 5 = 0
	TEST_AR_ORRI       10, shr.ut, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 5, 0x0000000000000000

	@@ [11] 源=目（原地）：rd9 >> 8
	TEST_AR_ORRI       11, shr.ut, rd9, 0x0000000012345678, rd9, 0x0000000012345678, 8, 0x0000000000123456

	@@ [12] imm 1：0x7FFFFFFF >> 1 = 0x3FFFFFFF
	TEST_AR_ORRI       12, shr.ut, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, 1, 0x000000003FFFFFFF

	@@ [13] （YAML boundary 并入）0x0F0F0F0F0F0F0F0F >> 31 = 0
	TEST_AR_ORRI       13, shr.ut, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, 31, 0x0000000000000000

	@@ [14] （YAML semantic 并入）0x0F0F0F0F… >> 2 = 0x03C3C3C3
	TEST_AR_ORRI       14, shr.ut, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, 2, 0x0000000003C3C3C3

	@@ [15] 迁移（m13-testcases-045）：分散位型 0x21212121 >> immu6=7（32 位逻辑右移）
	@@   手算：0x21212121>>7 = 0x00424242 ⇒ 0x0000000000424242（与 shr.st 同位型 19 的符号扩展结果对照）
	TEST_AR_ORRI       15, shr.ut, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000021212121, 7, 0x0000000000424242

	@@ [16] 迁移：源高 32 位全 1、低字 bit31=0 >> immu6=4（高半只看低字 ⇒ 全 0）
	@@   手算：0x12345678>>4 = 0x01234567 ⇒ 0x0000000001234567
	TEST_AR_ORRI       16, shr.ut, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF12345678, 4, 0x0000000001234567

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [17] immu6 = 32 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 17, shr.ut, ILLI, rd5, rd6, 32

	@@ [18] immu6 = 63 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 18, shr.ut, ILLI, rd5, rd6, 63

	@@ [19] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 19, shr.ut, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
