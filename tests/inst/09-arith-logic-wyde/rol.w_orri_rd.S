@@ rol.w_orri_rd.S — rol.w rdHB, rdHC, immu6（orri, opc 0x42／ha 0x19）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：rol.w_orri_rd　形式：orri　opc：0x42／ha 0x19　mask：0xFFFC0000　value：0x42640000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rol(rdHC[15:0], immu6))；旋转量取 immu6（0..15），结果零扩展写满 64 位（`spec/SimRISC-09 §2.2`）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 15 ⇒ ILLI（`encode_sbz`）；源可为 rd0；immu6 = 0 合法（原值）
@@ 边界/覆盖：覆盖 imm 0/1/8/14/15 五档、旋转保持位模式、rd0 作源、原地旋转
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 5 / semantic 7 / boundary 3 / overlap 3（链例 16 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	set.rd	rd2, 0x0000000000000000
	.dd.t32	0x42641080
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）rol.w orri: rd2(src)=0xFFFFFFFFFFFFBEEF immu6=0, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42641080
	__CHECK_RD   2, rd1, 0x000000000000BEEF

	@@ [3] （原 YAML 并入）rol.w orri: rd2(src)=0xFFFFFFFFFFFFBEEF immu6=1, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42641081
	__CHECK_RD   3, rd1, 0x0000000000007DDF

	@@ [4] （原 YAML 并入）rol.w orri: rd2(src)=0xFFFFFFFFFFFFBEEF immu6=14, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x4264108E
	__CHECK_RD   4, rd1, 0x000000000000EFBB

	@@ [5] （原 YAML 并入）rol.w orri: rd2(src)=0xFFFFFFFFFFFFBEEF immu6=15, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x4264108F
	__CHECK_RD   5, rd1, 0x000000000000DF77

	@@ [6] （原 YAML 并入）boundary rol.w orri: immu6=15=W-1, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x4264108F
	__CHECK_RD   6, rd1, 0x000000000000DF77

	@@ [7] 最大寄存器字段：rd63 = rol.w(rd1, imm=1)，0x8000 ⇒ 0x0001
	set.rd	rd1, 0x0000000000008000
	.dd.t32	0x4267F041
	__CHECK_RD   7, rd63, 0x0000000000000001

	@@ [8] imm=8：0xABCD ⇒ 0xCDAB（半字交换）
	TEST_AR_ORRI     8, rol.w, rd5, 0x0000000000000000, rd6, 0x000000000000ABCD, 8, 0x000000000000CDAB

	@@ [9] imm=4：0x1234 ⇒ 0x2341
	TEST_AR_ORRI     9, rol.w, rd5, 0x0000000000000000, rd6, 0x0000000000001234, 4, 0x0000000000002341

	@@ [10] 0x00FF << 8 = 0xFF00
	TEST_AR_ORRI     10, rol.w, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, 8, 0x000000000000FF00

	@@ [11] imm=0 ⇒ 原值（低 16 位，零扩展）
	TEST_AR_ORRI     11, rol.w, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0x000000000000FFFF

	@@ [12] imm=15：0x0001 ⇒ 0x8000
	TEST_AR_ORRI     12, rol.w, rd5, 0x0000000000000000, rd6, 0x0000000000000001, 15, 0x0000000000008000

	@@ [13] rd0 作源 C ⇒ 0
	TEST_AR_ORRI     13, rol.w, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 7, 0x0000000000000000

	@@ [14] 目的=源C（原地）：rd9 = rol.w(rd9=0x1234, imm=4) ⇒ 0x2341
	TEST_AR_ORRI     14, rol.w, rd9, 0x0000000000001234, rd9, 0x0000000000001234, 4, 0x0000000000002341

	@@ [15] 目的=源C（原地）：rd9 = rol.w(rd9=0x1234, imm=8) ⇒ 0x3412
	TEST_AR_ORRI     15, rol.w, rd9, 0x0000000000001234, rd9, 0x0000000000001234, 8, 0x0000000000003412

	@@ [16] 目的=源C（原地）：rd9 = rol.w(rd9=0x0001, imm=1) ⇒ 0x0002
	TEST_AR_ORRI     16, rol.w, rd9, 0x0000000000000001, rd9, 0x0000000000000001, 1, 0x0000000000000002

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [17] （原 YAML 并入）legality rol.w orri: immu6=16 > W-1=15 -> ILLI (encode_sbz)
	TEST_FAULT_ALU_ORRI 17, rol.w, ILLI, rd1, rd2, 16

	@@ [18] （原 YAML 并入）legality rol.w: dest rdHB=rd0 -> ILLI (dst_rd0)
	TEST_FAULT_ALU_ORRI 18, rol.w, ILLI, rd0, rd2, 0

	@@ [19] immu6 = 16 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 19, rol.w, ILLI, rd1, rd2, 16

	@@ [20] immu6 = 63 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 20, rol.w, ILLI, rd1, rd2, 63

	__TEST_SECTIONS
