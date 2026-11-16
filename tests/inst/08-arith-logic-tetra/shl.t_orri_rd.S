@@ shl.t_orri_rd.S — shl.t rdHB, rdHC, immu6（orri, opc 0x41／ha 0x18）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：shl.t_orri_rd　形式：orri　opc：0x41／ha 0x18　mask：0xFFFC0000　value：0x41600000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rdHC[31:0] << immu6)；immu6 ∈ 0..31，> 31 ⇒ ILLI，结果零扩展写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 31 ⇒ ILLI（`encode_sbz`）；源可为 rd0；immu6 = 0 合法（原值）
@@ 边界/覆盖：边界：imm 0/1/31 合法、32 与 63 ILLI、移出 32 位窗口的位丢弃
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 13 + 迁移 2（m13-testcases-045）（链例 17 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 << 2 的规范编码字
	@@ 规范编码字 0x41605182（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 2）
	set.rd	rd6, 0x000000000F0F0F0F
	.dd.t32	0x41605182
	__CHECK_RD   1, rd5, 0x000000003C3C3C3C

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 1 << 31（imm 字段上界）
	@@ 规范编码字 0x4163F05F（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 31）
	set.rd	rd1, 0x0000000000000001
	.dd.t32	0x4163F05F
	__CHECK_RD   2, rd63, 0x0000000080000000

	@@ [3] 0x0F0F0F0F << 2 = 0x3C3C3C3C
	TEST_AR_ORRI        3, shl.t, rd5, 0x0000000000000000, rd6, 0x000000000F0F0F0F, 2, 0x000000003C3C3C3C

	@@ [4] imm 0 ⇒ 原值（只留低 32 位，合法不抛异常）
	TEST_AR_ORRI        4, shl.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0x00000000FFFFFFFF

	@@ [5] 0xFFFFFFFF << 1 = 0xFFFFFFFE
	TEST_AR_ORRI        5, shl.t, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, 1, 0x00000000FFFFFFFE

	@@ [6] 0x80000000 << 1 = 0（移出 32 位窗口）
	TEST_AR_ORRI        6, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000080000000, 1, 0x0000000000000000

	@@ [7] 0x12345678 << 8 = 0x34567800
	TEST_AR_ORRI        7, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000012345678, 8, 0x0000000034567800

	@@ [8] imm 31：1 << 31 = 0x80000000（零扩展）
	TEST_AR_ORRI        8, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, 31, 0x0000000080000000

	@@ [9] imm 16：0x0000FFFF << 16 = 0xFFFF0000
	TEST_AR_ORRI        9, shl.t, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, 16, 0x00000000FFFF0000

	@@ [10] 源的高 32 位不参与：0xFFFFFFFF_00000001 << 4 = 0x10
	TEST_AR_ORRI       10, shl.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000001, 4, 0x0000000000000010

	@@ [11] rd0 作源：0 << 5 = 0
	TEST_AR_ORRI       11, shl.t, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 5, 0x0000000000000000

	@@ [12] 源=目（原地）：rd9 << 8
	TEST_AR_ORRI       12, shl.t, rd9, 0x0000000001234567, rd9, 0x0000000001234567, 8, 0x0000000023456700

	@@ [13] imm 31 上界：0xFFFFFFFF << 31 = 0x80000000（只留 bit31）
	TEST_AR_ORRI       13, shl.t, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, 31, 0x0000000080000000

	@@ [14] （YAML semantic 并入）0x0F0F0F0F0F0F0F0F << 2 = 0x3C3C3C3C
	TEST_AR_ORRI       14, shl.t, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, 2, 0x000000003C3C3C3C

	@@ [15] （YAML boundary 并入）0x0F0F0F0F0F0F0F0F << 31 = 0x80000000
	TEST_AR_ORRI       15, shl.t, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, 31, 0x0000000080000000

	@@ [16] 迁移（m13-testcases-045）：分散位型 0x21212121 << immu6=14（跨 nibble 的立即数移位档）
	@@   手算：0x21212121 << 14 = 0x84848484000 ⇒ 低 32 位 0x48484000，[63:32] = 0 ⇒ 0x0000000048484000
	TEST_AR_ORRI       16, shl.t, rd5, 0x0000000000000000, rd6, 0x0000000021212121, 14, 0x0000000048484000

	@@ [17] 迁移：0x99345678 << immu6=4（低字 bit31=1，零扩展 ⇒ 高半不得为 1）
	@@   手算：0x99345678 << 4 = 0x93456780 ⇒ 0x0000000093456780（RISC-V slliw 给 0xFFFFFFFF93456780）
	TEST_AR_ORRI       17, shl.t, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000099345678, 4, 0x0000000093456780

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [18] immu6 = 32 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 18, shl.t, ILLI, rd5, rd6, 32

	@@ [19] immu6 = 63 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 19, shl.t, ILLI, rd5, rd6, 63

	@@ [20] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 20, shl.t, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
