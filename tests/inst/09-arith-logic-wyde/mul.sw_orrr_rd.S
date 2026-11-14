@@ mul.sw_orrr_rd.S — mul.sw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x31）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：mul.sw_orrr_rd　形式：orrr　opc：0x42／ha 0x31　mask：0xFFFC0000　value：0x42C40000　目的银行：RD
@@ 语义：rdHB ← 符号扩展16(rdHC[15:0] × rdHD[15:0])；32 位积只留低 16 位，结果符号扩展
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）
@@ 边界/覆盖：覆盖负积符号扩展、0x7FFF×2 ⇒ 0xFFFE、0xFFFF×0xFFFF ⇒ 1、源高位垃圾、rd0 作源、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / legality 4 / semantic 4 / boundary 5 / overlap 3（链例 16 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （YAML `tests/inst/base/reg-arith.yaml` 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42C41000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （YAML `tests/inst/base/reg-arith.yaml` 并入）mul.sw: rd2=0x32, rd3=0x1e, bits=16
	__LI	rd2, 0x0000000000000032
	__LI	rd3, 0x000000000000001E
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42C41083
	__CHECK_RD   2, rd1, 0x00000000000005DC

	@@ [3] （YAML `tests/inst/base/reg-arith.yaml` 并入）boundary mul.sw: rd2=0x40, rd3=0x40
	__LI	rd2, 0x0000000000000040
	__LI	rd3, 0x0000000000000040
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42C41083
	__CHECK_RD   3, rd1, 0x0000000000001000

	@@ [4] 最大寄存器字段：rd63 = rd1 × rd2，0x8000 × 0x8000 = 0x40000000 ⇒ 低 16 位 0
	__LI	rd1, 0x0000000000008000
	__LI	rd2, 0x0000000000008000
	.dd.t32	0x42C7F042
	__CHECK_RD   4, rd63, 0x0000000000000000

	@@ [5] 0x0032 × 0x001E = 0x05DC（正积符号扩展为同值）
	TEST_AR_ORRR     5, mul.sw, rd5, 0x0000000000000000, rd6, 0x0000000000000032, rd7, 0x000000000000001E, 0x00000000000005DC

	@@ [6] −1 × 5 = −5 ⇒ 64 位全 1 减 4
	TEST_AR_ORRR     6, mul.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x0000000000000005, 0xFFFFFFFFFFFFFFFB

	@@ [7] 0x7FFF × 2 = 0xFFFE ⇒ 符号扩展 −2
	TEST_AR_ORRR     7, mul.sw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFE

	@@ [8] 0xFFFF × 0xFFFF = 1 ⇒ 1（负×负为正）
	TEST_AR_ORRR     8, mul.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x000000000000FFFF, 0x0000000000000001

	@@ [9] 0x8000 × 2 = 0x10000 ⇒ 0
	TEST_AR_ORRR     9, mul.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000002, 0x0000000000000000

	@@ [10] −32768 × −1 = 32768 ⇒ 低 16 位 0x8000 ⇒ 符号扩展回 −32768
	TEST_AR_ORRR     10, mul.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x000000000000FFFF, 0xFFFFFFFFFFFF8000

	@@ [11] 源高位不参与：低 16 位 −2 × 3 = −6
	TEST_AR_ORRR     11, mul.sw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFE, rd7, 0x0000000000000003, 0xFFFFFFFFFFFFFFFA

	@@ [12] rd0 作源 C ⇒ 0
	TEST_AR_ORRR     12, mul.sw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [13] rd0 作源 D ⇒ 0
	TEST_AR_ORRR     13, mul.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd0, 0x0000000000000000, 0x0000000000000000

	@@ [14] 目的=源C（原地）：rd9 = −1 × 3 = −3
	TEST_AR_ORRR     14, mul.sw, rd9, 0x000000000000FFFF, rd9, 0x000000000000FFFF, rd8, 0x0000000000000003, 0xFFFFFFFFFFFFFFFD

	@@ [15] 目的=源D（原地）：rd9 = −1 × rd9(3) = −3
	TEST_AR_ORRR     15, mul.sw, rd9, 0x0000000000000003, rd8, 0x000000000000FFFF, rd9, 0x0000000000000003, 0xFFFFFFFFFFFFFFFD

	@@ [16] 两源同名：0x0101 × 0x0101 ⇒ 0x0201（正数不扩展符号）
	TEST_AR_ORRR     16, mul.sw, rd5, 0x0000000000000000, rd10, 0x0000000000000101, rd10, 0x0000000000000101, 0x0000000000000201

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [17] （YAML `tests/inst/base/reg-arith.yaml` 并入）legality mul.sw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     17, mul.sw, ILLI, rd0, rd0, rd0

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     18, mul.sw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
