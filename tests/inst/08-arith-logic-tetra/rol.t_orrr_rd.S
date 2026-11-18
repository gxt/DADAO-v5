@@ rol.t_orrr_rd.S — rol.t rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x11）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：rol.t_orrr_rd　形式：orrr　opc：0x41／ha 0x11　mask：0xFFFC0000　value：0x41440000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rol32(rdHC[31:0], amount))；amount = rdHD[4:0]（对 32 取模、不 ILLI），结果零扩展写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（结果恒 0）；`rdHB == rdHC` 允许；orrr 的旋转量天然取低 5 位（`SimRISC-08 §2.2`）
@@ 边界/覆盖：边界：amount 0/1/31/32/全 1（取模）、循环而非移出、源高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 18（链例 20 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rol(rd6, 1)（0x80000001 ⇒ 0x00000003）的规范编码字
	@@ 规范编码字 0x41445187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000080000001
	set.rd	rd7, 0x0000000000000001
	.dd.t32	0x41445187
	__CHECK_RD   1, rd5, 0x0000000000000003

	@@ [encoding 2] 最高寄存器作目的（rd63）+ rol(1, 31) = 0x80000000
	@@ 规范编码字 0x4147F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x000000000000001F
	.dd.t32	0x4147F042
	__CHECK_RD   2, rd63, 0x0000000080000000

	@@ [3] rol(0x80000001, 1) = 0x00000003（最高位循环到最低位）
	TEST_AR_ORRR        3, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000080000001, rd7, 0x0000000000000001, 0x0000000000000003

	@@ [4] amount 0 ⇒ 原值（只留低 32 位）
	TEST_AR_ORRR        4, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0x00000000FFFFFFFF

	@@ [5] rol(0x12345678, 8) = 0x34567812
	TEST_AR_ORRR        5, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000012345678, rd7, 0x0000000000000008, 0x0000000034567812

	@@ [6] rol(1, 31) = 0x80000000（零扩展 ⇒ 高 32 位为 0）
	TEST_AR_ORRR        6, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000001F, 0x0000000080000000

	@@ [7] rol(0xFFFFFFFF, 5) = 0xFFFFFFFF（全 1 不变）
	TEST_AR_ORRR        7, rol.t, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000005, 0x00000000FFFFFFFF

	@@ [8] amount 32 ⇒ 取低 5 位 = 0 ⇒ 原值（不触发 ILLI）
	TEST_AR_ORRR        8, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000012345678, rd7, 0x0000000000000020, 0x0000000012345678

	@@ [9] amount 全 1 ⇒ 低 5 位 = 31：rol(1, 31) = 0x80000000
	TEST_AR_ORRR        9, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x00000000FFFFFFFF, 0x0000000080000000

	@@ [10] rol(0x00000001, 16) = 0x00010000（半字交换）
	TEST_AR_ORRR       10, rol.t, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x0000000000000010, 0x0000000000010000

	@@ [11] 源的高 32 位不参与：0xFFFFFFFF_00000001 rol 4 = 0x10
	TEST_AR_ORRR       11, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000001, rd7, 0x0000000000000004, 0x0000000000000010

	@@ [12] rd0 作源：rol(0, 7) = 0
	TEST_AR_ORRR       12, rol.t, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [13] 源=目（原地）：rd9 = rol(rd9, 8)
	TEST_AR_ORRR       13, rol.t, rd9, 0x0000000012345678, rd9, 0x0000000012345678, rd10, 0x0000000000000008, 0x0000000034567812

	@@ [14] 目=源D（原地）：rd9 旧值 3 是旋转量
	TEST_AR_ORRR       14, rol.t, rd9, 0x0000000000000003, rd10, 0x0000000000000001, rd9, 0x0000000000000003, 0x0000000000000008

	@@ [15] 两源同名：rol(0x00000003, 3) = 0x00000018
	TEST_AR_ORRR       15, rol.t, rd12, 0x0000000000000000, rd11, 0x0000000000000003, rd11, 0x0000000000000003, 0x0000000000000018

	@@ [16] （YAML semantic 并入）rol(0xFFFFFFFFDEADBEEF, amount 0) = 0xDEADBEEF
	TEST_AR_ORRR       16, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, rd7, 0x0000000000000000, 0x00000000DEADBEEF

	@@ [17] （YAML semantic 并入）rol(…, 1) = 0xBD5B7DDF
	TEST_AR_ORRR       17, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, rd7, 0x0000000000000001, 0x00000000BD5B7DDF

	@@ [18] （YAML semantic 并入）rol(…, 15) = 0xDF77EF56
	TEST_AR_ORRR       18, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, rd7, 0x000000000000000F, 0x00000000DF77EF56

	@@ [19] （YAML semantic/boundary 并入）rol(…, 31) = 0xEF56DF77
	TEST_AR_ORRR       19, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, rd7, 0x000000000000001F, 0x00000000EF56DF77

	@@ [20] （YAML semantic 并入）rol(…, 35) ⇒ amount 取低 5 位 = 3 ⇒ 0xF56DF77E
	TEST_AR_ORRR       20, rol.t, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFDEADBEEF, rd7, 0x0000000000000023, 0x00000000F56DF77E

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [21] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       21, rol.t, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
