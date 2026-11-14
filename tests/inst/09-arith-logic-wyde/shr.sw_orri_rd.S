@@ shr.sw_orri_rd.S — shr.sw rdHB, rdHC, immu6（orri, opc 0x42／ha 0x1B）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：shr.sw_orri_rd　形式：orri　opc：0x42／ha 0x1B　mask：0xFFFC0000　value：0x426C0000　目的银行：RD
@@ 语义：rdHB ← 符号扩展16(rdHC[15:0] >> immu6)（算术右移，高位补 rdHC[15]）；rdHB[63:16] = 符号扩展
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；immu6 > 15 ⇒ ILLI（`encode_sbz`）；源可为 rd0；immu6 = 0 合法
@@ 边界/覆盖：覆盖负数补 1、immu6 0/1/15、0x8000 与 0x7FFF 的符号差、rd0 作源、原地右移
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / legality 5 / semantic 4 / boundary 4 / overlap 2（链例 13 + 故障例 4）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （YAML `tests/inst/base/reg-shift-extend.yaml` 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x426C1001
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （YAML `tests/inst/base/reg-shift-extend.yaml` 并入）shr.sw orri: rd2(src)=0xf0f0f0f0f0f0f0f, immu6=2, N=15
	__LI	rd2, 0x0F0F0F0F0F0F0F0F
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x426C1082
	__CHECK_RD   2, rd1, 0x00000000000003C3

	@@ [3] （YAML `tests/inst/base/reg-shift-extend.yaml` 并入）boundary shr.sw orri: rd2(src)=0xf0f0f0f0f0f0f0f, immu6=15=N, N=15
	__LI	rd2, 0x0F0F0F0F0F0F0F0F
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x426C108F
	__CHECK_RD   3, rd1, 0x0000000000000000

	@@ [4] 最大寄存器字段：rd63 = rd1 >> 15（算术），0x8000 ⇒ −1（符号填充）
	__LI	rd1, 0x0000000000008000
	.dd.t32	0x426FF04F
	__CHECK_RD   4, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [5] 0x8000 >> 1 = 0xC000（高位补符号位 1）
	TEST_AR_ORRI     5, shr.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, 1, 0xFFFFFFFFFFFFC000

	@@ [6] 0xF000 >> 4 = 0xFF00 ⇒ 符号扩展 −256
	TEST_AR_ORRI     6, shr.sw, rd5, 0x0000000000000000, rd6, 0x000000000000F000, 4, 0xFFFFFFFFFFFFFF00

	@@ [7] imm=0 ⇒ 符号扩展原值（0x8001 ⇒ 负）
	TEST_AR_ORRI     7, shr.sw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFF8001, 0, 0xFFFFFFFFFFFF8001

	@@ [8] imm=15：0x8000 >> 15 ⇒ −1（15 位全为符号 1）
	TEST_AR_ORRI     8, shr.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, 15, 0xFFFFFFFFFFFFFFFF

	@@ [9] imm=15：0x7FFF >> 15 = 0（正数）
	TEST_AR_ORRI     9, shr.sw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, 15, 0x0000000000000000

	@@ [10] 源高位不参与：低 16 位 0x8000 >> 8 = 0xFF80
	TEST_AR_ORRI     10, shr.sw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFF8000, 8, 0xFFFFFFFFFFFFFF80

	@@ [11] rd0 作源 C ⇒ 0
	TEST_AR_ORRI     11, shr.sw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, 5, 0x0000000000000000

	@@ [12] 目的=源C（原地）：rd9 = rd9(0x7FFF) >> 8 = 0x007F
	TEST_AR_ORRI     12, shr.sw, rd9, 0x0000000000007FFF, rd9, 0x0000000000007FFF, 8, 0x000000000000007F

	@@ [13] 目的=源C（原地）：rd9 = rd9(0x8000) >> 8 = 0xFF80（符号扩展）
	TEST_AR_ORRI     13, shr.sw, rd9, 0x0000000000008000, rd9, 0x0000000000008000, 8, 0xFFFFFFFFFFFFFF80

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [14] （YAML `tests/inst/base/reg-shift-extend.yaml` 并入）legality shr.sw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU_ORRI 14, shr.sw, ILLI, rd0, rd0, 0

	@@ [15] immu6 = 16 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 15, shr.sw, ILLI, rd1, rd2, 16

	@@ [16] immu6 = 63 > 15 ⇒ ILLI（`encode_sbz`）
	TEST_FAULT_ALU_ORRI 16, shr.sw, ILLI, rd1, rd2, 63

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU_ORRI 17, shr.sw, ILLI, rd0, rd6, 1

	__TEST_SECTIONS
