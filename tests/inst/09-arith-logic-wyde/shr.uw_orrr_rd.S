@@ shr.uw_orrr_rd.S — shr.uw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x12）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：shr.uw_orrr_rd　形式：orrr　opc：0x42／ha 0x12　mask：0xFFFC0000　value：0x42480000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rdHC[15:0] >> rdHD[3:0])（逻辑右移，高位补零）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；rdHD 高位（[5:4]）不参与（见 `新发现/坑`）
@@ 边界/覆盖：覆盖 shamt 0/1/15/16 的掩码、0x8000>>15、源高位不参与、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 4 / semantic 6 / boundary 5 / overlap 3（链例 18 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42481000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）shr.uw: rd2(src)=0xf0f0f0f0f0f0f0f, rd3(shamt)=2, N=15
	set.rd	rd2, 0x0F0F0F0F0F0F0F0F
	set.rd	rd3, 0x0000000000000002
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42481083
	__CHECK_RD   2, rd1, 0x00000000000003C3

	@@ [3] （原 YAML 并入）boundary shr.uw: rd2(src)=0xf0f0f0f0f0f0f0f, rd3(shamt)=15=N, N=15
	set.rd	rd2, 0x0F0F0F0F0F0F0F0F
	set.rd	rd3, 0x000000000000000F
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42481083
	__CHECK_RD   3, rd1, 0x0000000000000000

	@@ [4] 最大寄存器字段：rd63 = rd1 >> rd2[3:0]，0x8000 >> 15 = 1
	set.rd	rd1, 0x0000000000008000
	set.rd	rd2, 0x000000000000000F
	.dd.t32	0x424BF042
	__CHECK_RD   4, rd63, 0x0000000000000001

	@@ [5] 0x1234 >> 4 = 0x0123
	TEST_AR_ORRR     5, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd7, 0x0000000000000004, 0x0000000000000123

	@@ [6] 0x00FF >> 8 = 0（低半字节移出）
	TEST_AR_ORRR     6, shr.uw, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, rd7, 0x0000000000000008, 0x0000000000000000

	@@ [7] 0x0100 >> 4 = 0x10
	TEST_AR_ORRR     7, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000100, rd7, 0x0000000000000004, 0x0000000000000010

	@@ [8] 0x8000 >> 8 = 0x0080（逻辑：不补符号位）
	TEST_AR_ORRR     8, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000008, 0x0000000000000080

	@@ [9] shamt=0 ⇒ 原值（低 16 位，零扩展）
	TEST_AR_ORRR     9, shr.uw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0x000000000000FFFF

	@@ [10] shamt=16 只取 rdHD[3:0] = 0 ⇒ 原值（不触发 ILLI）
	TEST_AR_ORRR     10, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000F0F, rd7, 0x0000000000000010, 0x0000000000000F0F

	@@ [11] shamt=1：0xFFFF >> 1 = 0x7FFF
	TEST_AR_ORRR     11, shr.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x0000000000000001, 0x0000000000007FFF

	@@ [12] shamt=15：0x8000 >> 15 = 1（逻辑：高位补零）
	TEST_AR_ORRR     12, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x000000000000000F, 0x0000000000000001

	@@ [13] 源高位不参与：低 16 位 0xFF00 >> 8 = 0x00FF
	TEST_AR_ORRR     13, shr.uw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFF00, rd7, 0x0000000000000008, 0x00000000000000FF

	@@ [14] rd0 作源 C ⇒ 0
	TEST_AR_ORRR     14, shr.uw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [15] rd0 作源 D（shamt = 0）⇒ 原值
	TEST_AR_ORRR     15, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd0, 0x0000000000000000, 0x0000000000001234

	@@ [16] 目的=源C（原地）：rd9 = rd9(0x0100) >> 4 = 0x10
	TEST_AR_ORRR     16, shr.uw, rd9, 0x0000000000000100, rd9, 0x0000000000000100, rd8, 0x0000000000000004, 0x0000000000000010

	@@ [17] 目的=源D（原地）：rd9 = 0x0100 >> rd9[3:0]=4 ⇒ 0x10
	TEST_AR_ORRR     17, shr.uw, rd9, 0x0000000000000004, rd8, 0x0000000000000100, rd9, 0x0000000000000004, 0x0000000000000010

	@@ [18] 两源同名（shamt = 0x0400 的低 4 位 = 0）⇒ 原值 0x0400
	TEST_AR_ORRR     18, shr.uw, rd5, 0x0000000000000000, rd10, 0x0000000000000400, rd10, 0x0000000000000400, 0x0000000000000400

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [19] （原 YAML 并入）legality shr.uw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     19, shr.uw, ILLI, rd0, rd0, rd0

	@@ [20] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     20, shr.uw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
