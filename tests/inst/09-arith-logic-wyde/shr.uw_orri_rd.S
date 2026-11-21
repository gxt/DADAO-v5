@@ shr.uw_orri_rd.S — shr.uw rdHB, rdHC, immu6（orri, opc 0x42／ha 0x1A）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：shr.uw_orri_rd　形式：orri　opc：0x42／ha 0x1A　mask：0xFFFC0000　value：0x42680000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rdHC[15:0] >> immu6)（逻辑右移，高位补零）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 15 ⇒ ILLI（`encode_sbz`）；源可为 rd0；immu6 = 0 合法
@@ 边界/覆盖：覆盖 imm 0/1/15、0xFFFF 高位补零、rd0 作源、原地右移
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 5 / semantic 5 / boundary 4 / overlap 2（链例 14 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42681001
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）shr.uw orri: rd2(src)=0xf0f0f0f0f0f0f0f, immu6=2, N=15
	set.rd	rd2, 0x0F0F0F0F0F0F0F0F
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42681082
	__CHECK_RD   2, rd1, 0x00000000000003C3

	@@ [3] （原 YAML 并入）boundary shr.uw orri: rd2(src)=0xf0f0f0f0f0f0f0f, immu6=15=N, N=15
	set.rd	rd2, 0x0F0F0F0F0F0F0F0F
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x4268108F
	__CHECK_RD   3, rd1, 0x0000000000000000

	@@ [4] 最大寄存器字段：rd63 = rd1 >> 15，0x8000 ⇒ 1
	set.rd	rd1, 0x0000000000008000
	.dd.t32	0x426BF04F
	__CHECK_RD   4, rd63, 0x0000000000000001

	@@ [5] 0x1234 >> 4 = 0x0123
	TEST_AR_ORRI     5, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000001234, 4, 0x0000000000000123

	@@ [6] 0x00FF >> 8 = 0（低半字节移出）
	TEST_AR_ORRI     6, shr.uw, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, 8, 0x0000000000000000

	@@ [7] 0x8000 >> 8 = 0x0080（逻辑：不补符号位）
	TEST_AR_ORRI     7, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, 8, 0x0000000000000080

	@@ [8] imm=0 ⇒ 原值（低 16 位，零扩展）
	TEST_AR_ORRI     8, shr.uw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0x000000000000FFFF

	@@ [9] imm=1：0xFFFF >> 1 = 0x7FFF（高位补零）
	TEST_AR_ORRI     9, shr.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, 1, 0x0000000000007FFF

	@@ [10] imm=15：0x8000 >> 15 = 1
	TEST_AR_ORRI     10, shr.uw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, 15, 0x0000000000000001

	@@ [11] 源高位不参与：低 16 位 0xFF00 >> 8 = 0x00FF
	TEST_AR_ORRI     11, shr.uw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFF00, 8, 0x00000000000000FF

	@@ [12] rd0 作源 C ⇒ 0
	TEST_AR_ORRI     12, shr.uw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 5, 0x0000000000000000

	@@ [13] 目的=源C（原地）：rd9 = rd9(0x0100) >> 4 = 0x10
	TEST_AR_ORRI     13, shr.uw, rd9, 0x0000000000000100, rd9, 0x0000000000000100, 4, 0x0000000000000010

	@@ [14] 目的=源C（原地）：rd9 = rd9(0x8000) >> 8 = 0x0080
	TEST_AR_ORRI     14, shr.uw, rd9, 0x0000000000008000, rd9, 0x0000000000008000, 8, 0x0000000000000080

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [15] （原 YAML 并入）legality shr.uw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU_ORRI 15, shr.uw, ILLI, rd0, rd0, 0

	@@ [16] immu6 = 16 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 16, shr.uw, ILLI, rd1, rd2, 16

	@@ [17] immu6 = 63 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 17, shr.uw, ILLI, rd1, rd2, 63

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU_ORRI 18, shr.uw, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
