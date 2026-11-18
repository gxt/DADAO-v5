@@ rol.t_orri_rd.S — rol.t rdHB, rdHC, immu6（orri, opc 0x41／ha 0x19）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：rol.t_orri_rd　形式：orri　opc：0x41／ha 0x19　mask：0xFFFC0000　value：0x41640000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rol32(rdHC[31:0], immu6))；immu6 ∈ 0..31，> 31 ⇒ ILLI
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 31 ⇒ ILLI（`encode_sbz`，`SimRISC-08 §2.2` 明文）；源可为 rd0；immu6 = 0 合法
@@ 边界/覆盖：边界：imm 0/1/31 合法、32 与 63 ILLI、循环语义（非移出）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 15（链例 17 + 故障例 3）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rol(rd6, 1)（0x80000001 ⇒ 0x00000003）的规范编码字
	@@ 规范编码字 0x41645181（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 1）
	set.rd	rd6, 0x0000000080000001
	.dd.t32	0x41645181
	__CHECK_RD   1, rd5, 0x0000000000000003

	@@ [encoding 2] 最高寄存器作目的（rd63）+ rol(1, 31) = 0x80000000（imm 字段上界）
	@@ 规范编码字 0x4167F05F（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 31）
	set.rd	rd1, 0x0000000000000001
	.dd.t32	0x4167F05F
	__CHECK_RD   2, rd63, 0x0000000080000000

	@@ [3] rol(0x80000001, 1) = 0x00000003
	TEST_AR_ORRI        3, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000080000001, 1, 0x0000000000000003

	@@ [4] imm 0 ⇒ 原值（只留低 32 位，合法）
	TEST_AR_ORRI        4, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0x00000000FFFFFFFF

	@@ [5] rol(0x12345678, 8) = 0x34567812
	TEST_AR_ORRI        5, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000012345678, 8, 0x0000000034567812

	@@ [6] imm 31：rol(1, 31) = 0x80000000（零扩展）
	TEST_AR_ORRI        6, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, 31, 0x0000000080000000

	@@ [7] rol(0xFFFFFFFF, 5) = 0xFFFFFFFF
	TEST_AR_ORRI        7, rol.t, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, 5, 0x00000000FFFFFFFF

	@@ [8] imm 16：rol(1, 16) = 0x00010000
	TEST_AR_ORRI        8, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, 16, 0x0000000000010000

	@@ [9] rol(0x0000FFFF, 16) = 0xFFFF0000
	TEST_AR_ORRI        9, rol.t, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, 16, 0x00000000FFFF0000

	@@ [10] 源的高 32 位不参与：0xFFFFFFFF_00000001 rol 4 = 0x10
	TEST_AR_ORRI       10, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000001, 4, 0x0000000000000010

	@@ [11] rd0 作源：rol(0, 7) = 0
	TEST_AR_ORRI       11, rol.t, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 7, 0x0000000000000000

	@@ [12] 源=目（原地）：rd9 = rol(rd9, 8)
	TEST_AR_ORRI       12, rol.t, rd9, 0x0000000012345678, rd9, 0x0000000012345678, 8, 0x0000000034567812

	@@ [13] imm 31 上界：rol(0x80000000, 31) = 0x00000001
	TEST_AR_ORRI       13, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000080000000, 31, 0x0000000040000000

	@@ [14] （YAML semantic 并入）rol(0xFFFFFFFFDEADBEEF, imm 0) = 0xDEADBEEF
	TEST_AR_ORRI       14, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, 0, 0x00000000DEADBEEF

	@@ [15] （YAML semantic 并入）rol(…, imm 1) = 0xBD5B7DDF
	TEST_AR_ORRI       15, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, 1, 0x00000000BD5B7DDF

	@@ [16] （YAML semantic 并入）rol(…, imm 30) = 0xF7AB6FBB
	TEST_AR_ORRI       16, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, 30, 0x00000000F7AB6FBB

	@@ [17] （YAML semantic/boundary 并入）rol(…, imm 31) = 0xEF56DF77
	TEST_AR_ORRI       17, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, 31, 0x00000000EF56DF77

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [18] immu6 = 32 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 18, rol.t, ILLI, rd5, rd6, 32

	@@ [19] immu6 = 63 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 19, rol.t, ILLI, rd5, rd6, 63

	@@ [20] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 20, rol.t, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
