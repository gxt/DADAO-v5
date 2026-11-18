@@ shl.w_orrr_rd.S — shl.w rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x10）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：shl.w_orrr_rd　形式：orrr　opc：0x42／ha 0x10　mask：0xFFFC0000　value：0x42400000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rdHC[15:0] << rdHD[3:0])；移位量取 rdHD 低 4 位，结果零扩展
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；rdHD 高位（[5:4]）不参与（见 `新发现/坑`）
@@ 边界/覆盖：覆盖 shamt 0/1/15/16 的掩码、移出窗口、源高位不参与、rd0 作源、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 4 / semantic 4 / boundary 6 / overlap 3（链例 17 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42401000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）shl.w: rd2(src)=0xf0f0f0f0f0f0f0f, rd3(shamt)=2, N=15
	set.rd	rd2, 0x0F0F0F0F0F0F0F0F
	set.rd	rd3, 0x0000000000000002
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42401083
	__CHECK_RD   2, rd1, 0x0000000000003C3C

	@@ [3] （原 YAML 并入）boundary shl.w: rd2(src)=0xf0f0f0f0f0f0f0f, rd3(shamt)=15=N, N=15
	set.rd	rd2, 0x0F0F0F0F0F0F0F0F
	set.rd	rd3, 0x000000000000000F
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42401083
	__CHECK_RD   3, rd1, 0x0000000000008000

	@@ [4] 最大寄存器字段：rd63 = rd1 << rd2[3:0]，1 << 4 = 0x10
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x0000000000000004
	.dd.t32	0x4243F042
	__CHECK_RD   4, rd63, 0x0000000000000010

	@@ [5] 0x1234 << 4 = 0x2340
	TEST_AR_ORRR     5, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd7, 0x0000000000000004, 0x0000000000002340

	@@ [6] 0x00FF << 8 = 0xFF00（移入高半字节）
	TEST_AR_ORRR     6, shl.w, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, rd7, 0x0000000000000008, 0x000000000000FF00

	@@ [7] 0x0100 << 4 = 0x1000
	TEST_AR_ORRR     7, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000000100, rd7, 0x0000000000000004, 0x0000000000001000

	@@ [8] shamt=0 ⇒ 原值（低 16 位，零扩展）
	TEST_AR_ORRR     8, shl.w, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0x000000000000FFFF

	@@ [9] shamt=16 只取 rdHD[3:0] = 0 ⇒ 原值（不触发 ILLI）
	TEST_AR_ORRR     9, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000000F0F, rd7, 0x0000000000000010, 0x0000000000000F0F

	@@ [10] shamt=15：1 << 15 = 0x8000
	TEST_AR_ORRR     10, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000000F, 0x0000000000008000

	@@ [11] 0x8000 << 1 ⇒ 0（移出 16 位窗口）
	TEST_AR_ORRR     11, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [12] 0x7FFF << 1 = 0xFFFE
	TEST_AR_ORRR     12, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x0000000000000001, 0x000000000000FFFE

	@@ [13] rd0 作源 C ⇒ 0
	TEST_AR_ORRR     13, shl.w, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [14] rd0 作源 D（shamt = 0）⇒ 原值
	TEST_AR_ORRR     14, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd0, 0x0000000000000000, 0x0000000000001234

	@@ [15] 目的=源C（原地）：rd9 = rd9(3) << 2 = 0x0C
	TEST_AR_ORRR     15, shl.w, rd9, 0x0000000000000003, rd9, 0x0000000000000003, rd8, 0x0000000000000002, 0x000000000000000C

	@@ [16] 目的=源D（原地）：rd9 = 3 << rd9[3:0]=4 ⇒ 0x30
	TEST_AR_ORRR     16, shl.w, rd9, 0x0000000000000004, rd8, 0x0000000000000003, rd9, 0x0000000000000004, 0x0000000000000030

	@@ [17] 两源同名：3 << 3 = 0x18
	TEST_AR_ORRR     17, shl.w, rd5, 0x0000000000000000, rd10, 0x0000000000000003, rd10, 0x0000000000000003, 0x0000000000000018

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [18] （原 YAML 并入）legality shl.w: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     18, shl.w, ILLI, rd0, rd0, rd0

	@@ [19] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     19, shl.w, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
