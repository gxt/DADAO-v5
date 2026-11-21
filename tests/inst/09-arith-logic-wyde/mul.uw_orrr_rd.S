@@ mul.uw_orrr_rd.S — mul.uw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x30）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：mul.uw_orrr_rd　形式：orrr　opc：0x42／ha 0x30　mask：0xFFFC0000　value：0x42C00000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rdHC[15:0] × rdHD[15:0])；32 位积只留低 16 位（高位静默丢弃），结果零扩展
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 边界/覆盖：覆盖 0xFFFF×0xFFFF ⇒ 1、0x8000×2 ⇒ 0、0x7FFF×2、0xFFFF×0x8000、源高位垃圾、rd0 作源、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 4 / semantic 4 / boundary 5 / overlap 3（链例 16 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42C01000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）mul.uw: rd2=0x32, rd3=0x1e, bits=16
	set.rd	rd2, 0x0000000000000032
	set.rd	rd3, 0x000000000000001E
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42C01083
	__CHECK_RD   2, rd1, 0x00000000000005DC

	@@ [3] （原 YAML 并入）boundary mul.uw: rd2=0x80, rd3=0x80
	set.rd	rd2, 0x0000000000000080
	set.rd	rd3, 0x0000000000000080
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42C01083
	__CHECK_RD   3, rd1, 0x0000000000004000

	@@ [4] 最大寄存器字段：rd63 = rd1 × rd2，0x0100 × 0x0100 = 0x10000 ⇒ 低 16 位 0
	set.rd	rd1, 0x0000000000000100
	set.rd	rd2, 0x0000000000000100
	.dd.t32	0x42C3F042
	__CHECK_RD   4, rd63, 0x0000000000000000

	@@ [5] 300 × 200 = 60000 = 0xEA60（零扩展）
	TEST_AR_ORRR     5, mul.uw, rd5, 0x0000000000000000, rd6, 0x000000000000012C, rd7, 0x00000000000000C8, 0x000000000000EA60

	@@ [6] 5 × 7 = 35
	TEST_AR_ORRR     6, mul.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000005, rd7, 0x0000000000000007, 0x0000000000000023

	@@ [7] 0xFFFF × 0xFFFF = 0xFFFE0001 ⇒ 低 16 位 1
	TEST_AR_ORRR     7, mul.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x000000000000FFFF, 0x0000000000000001

	@@ [8] 0x8000 × 2 = 0x10000 ⇒ 0
	TEST_AR_ORRR     8, mul.uw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000002, 0x0000000000000000

	@@ [9] 0x7FFF × 2 = 0xFFFE
	TEST_AR_ORRR     9, mul.uw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x0000000000000002, 0x000000000000FFFE

	@@ [10] 0xFFFF × 0x8000 ⇒ 低 16 位 0x8000
	TEST_AR_ORRR     10, mul.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x0000000000008000, 0x0000000000008000

	@@ [11] 源高位不参与：低 16 位 2 × 3 = 6
	TEST_AR_ORRR     11, mul.uw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFF0002, rd7, 0x0000000000000003, 0x0000000000000006

	@@ [12] rd0 作源 C ⇒ 0
	TEST_AR_ORRR     12, mul.uw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [13] rd0 作源 D ⇒ 0
	TEST_AR_ORRR     13, mul.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd0, 0x0000000000000000, 0x0000000000000000

	@@ [14] 目的=源C（原地）：rd9 = 3 × 5 = 15
	TEST_AR_ORRR     14, mul.uw, rd9, 0x0000000000000003, rd9, 0x0000000000000003, rd8, 0x0000000000000005, 0x000000000000000F

	@@ [15] 目的=源D（原地）：rd9 = 3 × rd9(5) = 15
	TEST_AR_ORRR     15, mul.uw, rd9, 0x0000000000000005, rd8, 0x0000000000000003, rd9, 0x0000000000000005, 0x000000000000000F

	@@ [16] 两源同名：0x0101 × 0x0101 = 0x10201 ⇒ 0x0201
	TEST_AR_ORRR     16, mul.uw, rd5, 0x0000000000000000, rd10, 0x0000000000000101, rd10, 0x0000000000000101, 0x0000000000000201

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [17] （原 YAML 并入）legality mul.uw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     17, mul.uw, ILLI, rd0, rd0, rd0

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     18, mul.uw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
