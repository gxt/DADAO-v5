@@ shr.st_orri_rd.S — shr.st rdHB, rdHC, immu6（orri, opc 0x41／ha 0x1B）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：shr.st_orri_rd　形式：orri　opc：0x41／ha 0x1B　mask：0xFFFC0000　value：0x416C0000　目的银行：RD
@@ 语义：rdHB ← 符号扩展(rdHC[31:0] >> immu6)（算术右移）；immu6 ∈ 0..31，> 31 ⇒ ILLI
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 31 ⇒ ILLI（`encode_sbz`）；源可为 rd0；immu6 = 0 合法
@@ 边界/覆盖：边界：imm 0/1/31 合法、32 与 63 ILLI、负数高位补 1
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 13 + 迁移 3（m13-testcases-045）（链例 18 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 >> 1（0x80000000 ⇒ 0xC0000000）的规范编码字
	@@ 规范编码字 0x416C5181（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 1）
	set.rd	rd6, 0x0000000080000000
	.dd.t32	0x416C5181
	__CHECK_RD   1, rd5, 0xFFFFFFFFC0000000

	@@ [encoding 2] 最高寄存器作目的（rd63）+ −1 >> 31 = −1（全 1）
	@@ 规范编码字 0x416FF05F（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 31）
	set.rd	rd1, 0x00000000FFFFFFFF
	.dd.t32	0x416FF05F
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [3] 0x80000000 >> 1 ⇒ 0xFFFFFFFF_C0000000
	TEST_AR_ORRI        3, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, 1, 0xFFFFFFFFC0000000

	@@ [4] 0xFFFFFFFF >> 4 = 0xFFFFFFFF
	TEST_AR_ORRI        4, shr.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, 4, 0xFFFFFFFFFFFFFFFF

	@@ [5] 0x7FFFFFFF >> 1 = 0x3FFFFFFF
	TEST_AR_ORRI        5, shr.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, 1, 0x000000003FFFFFFF

	@@ [6] imm 0 ⇒ 原值（只留低 32 位、符号扩展）
	TEST_AR_ORRI        6, shr.st, rd5, 0x0000000000000000, rd6, 0x8000000000000000, 0, 0x0000000000000000

	@@ [7] imm 31：0x80000000 >> 31 = 0xFFFFFFFF
	TEST_AR_ORRI        7, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, 31, 0xFFFFFFFFFFFFFFFF

	@@ [8] imm 31：0x7FFFFFFF >> 31 = 0
	TEST_AR_ORRI        8, shr.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, 31, 0x0000000000000000

	@@ [9] imm 8：0x12345678 >> 8 = 0x00123456
	TEST_AR_ORRI        9, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000012345678, 8, 0x0000000000123456

	@@ [10] 源的高 32 位不参与
	TEST_AR_ORRI       10, shr.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF80000000, 1, 0xFFFFFFFFC0000000

	@@ [11] rd0 作源：0 >> 5 = 0
	TEST_AR_ORRI       11, shr.st, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 5, 0x0000000000000000

	@@ [12] 源=目（原地）：rd9 >> 8
	TEST_AR_ORRI       12, shr.st, rd9, 0x0000000080000000, rd9, 0x0000000080000000, 8, 0xFFFFFFFFFF800000

	@@ [13] imm 16：0x8000FFFF >> 16 = 0xFFFFFFFF_FFFF8000
	TEST_AR_ORRI       13, shr.st, rd5, 0x0000000000000000, rd6, 0x000000008000FFFF, 16, 0xFFFFFFFFFFFF8000

	@@ [14] （YAML boundary 并入）0x0F0F0F0F0F0F0F0F >> 31 = 0
	TEST_AR_ORRI       14, shr.st, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, 31, 0x0000000000000000

	@@ [15] （YAML semantic 并入）0x0F0F0F0F… >> 2 = 0x03C3C3C3（正数 ⇒ 高位补 0）
	TEST_AR_ORRI       15, shr.st, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, 2, 0x0000000003C3C3C3

	@@ [16] 迁移（m13-testcases-045）：0x92345678 >> immu6=0 —— 符号来自低字 bit31
	@@   手算：低字原样 0x92345678；[63:32] = sign(bit31=1) = 0xFFFFFFFF ⇒ 0xFFFFFFFF92345678
	TEST_AR_ORRI       16, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000092345678, 0, 0xFFFFFFFF92345678

	@@ [17] 迁移：0xF0000000 >> immu6=4（bit31=1 ⇒ 32 位内补 1 到 0xFF000000，高半全 1）
	@@   手算：0xF0000000>>4 = 0xFF000000；[63:32] = sign(bit31) ⇒ 0xFFFFFFFFFF000000
	TEST_AR_ORRI       17, shr.st, rd5, 0x0000000000000000, rd6, 0x00000000F0000000, 4, 0xFFFFFFFFFF000000

	@@ [18] 迁移：源 bit61-63 置位但低 32 位为 0 >> immu6=28（窄宽度只看低字 ⇒ 结果为 0）
	@@   手算：低字 0x00000000 >> 28 = 0；[63:32] = sign(bit31=0) = 0 ⇒ 0x0000000000000000
	TEST_AR_ORRI       18, shr.st, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00E0000000000000, 28, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [19] immu6 = 32 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 19, shr.st, ILLI, rd5, rd6, 32

	@@ [20] immu6 = 63 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 20, shr.st, ILLI, rd5, rd6, 63

	@@ [21] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 21, shr.st, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
