@@ shl.w_orri_rd.S — shl.w rdHB, rdHC, immu6（orri, opc 0x42／ha 0x18）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：shl.w_orri_rd　形式：orri　opc：0x42／ha 0x18　mask：0xFFFC0000　value：0x42600000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rdHC[15:0] << immu6)；移出 16 位窗口的位静默丢弃，结果零扩展
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 15 ⇒ ILLI（`encode_sbz`，`contracts/legality_rules.yaml`）；源可为 rd0；immu6 = 0 合法
@@ 边界/覆盖：覆盖 imm 0/1/15 边界、移出窗口、源高位不参与、rd0 作源、原地左移
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / legality 5 / semantic 4 / boundary 4 / overlap 2（链例 13 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42601001
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）shl.w orri: rd2(src)=0xf0f0f0f0f0f0f0f, immu6=2, N=15
	__LI	rd2, 0x0F0F0F0F0F0F0F0F
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42601082
	__CHECK_RD   2, rd1, 0x0000000000003C3C

	@@ [3] （原 YAML 并入）boundary shl.w orri: rd2(src)=0xf0f0f0f0f0f0f0f, immu6=15=N, N=15
	__LI	rd2, 0x0F0F0F0F0F0F0F0F
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x4260108F
	__CHECK_RD   3, rd1, 0x0000000000008000

	@@ [4] 最大寄存器字段：rd63 = rd1 << 15，1 ⇒ 0x8000
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x4263F04F
	__CHECK_RD   4, rd63, 0x0000000000008000

	@@ [5] 0x1234 << 4 = 0x2340
	TEST_AR_ORRI     5, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000001234, 4, 0x0000000000002340

	@@ [6] 0x00FF << 8 = 0xFF00
	TEST_AR_ORRI     6, shl.w, rd5, 0x0000000000000000, rd6, 0x00000000000000FF, 8, 0x000000000000FF00

	@@ [7] imm=0 ⇒ 原值（低 16 位，零扩展）
	TEST_AR_ORRI     7, shl.w, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 0, 0x000000000000FFFF

	@@ [8] imm=1：0x8000 << 1 ⇒ 0（移出 16 位窗口）
	TEST_AR_ORRI     8, shl.w, rd5, 0x0000000000000000, rd6, 0x0000000000008000, 1, 0x0000000000000000

	@@ [9] imm=15：0xFFFF << 15 ⇒ 0x8000
	TEST_AR_ORRI     9, shl.w, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, 15, 0x0000000000008000

	@@ [10] 源高位不参与：低 16 位 1 << 4 = 0x10
	TEST_AR_ORRI     10, shl.w, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFF0001, 4, 0x0000000000000010

	@@ [11] rd0 作源 C ⇒ 0
	TEST_AR_ORRI     11, shl.w, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 5, 0x0000000000000000

	@@ [12] 目的=源C（原地）：rd9 = rd9(0x0003) << 2 = 0x000C
	TEST_AR_ORRI     12, shl.w, rd9, 0x0000000000000003, rd9, 0x0000000000000003, 2, 0x000000000000000C

	@@ [13] 目的=源C（原地）：rd9 = rd9(0x00FF) << 8 = 0xFF00
	TEST_AR_ORRI     13, shl.w, rd9, 0x00000000000000FF, rd9, 0x00000000000000FF, 8, 0x000000000000FF00

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [14] （原 YAML 并入）legality shl.w: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU_ORRI 14, shl.w, ILLI, rd0, rd0, 0

	@@ [15] immu6 = 16 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 15, shl.w, ILLI, rd1, rd2, 16

	@@ [16] immu6 = 63 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 16, shl.w, ILLI, rd1, rd2, 63

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU_ORRI 17, shl.w, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
