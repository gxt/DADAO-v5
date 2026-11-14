@@ sub.sw_orrr_rd.S — sub.sw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x29）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：sub.sw_orrr_rd　形式：orrr　opc：0x42／ha 0x29　mask：0xFFFC0000　value：0x42A40000　目的银行：RD
@@ 语义：rdHB ← 符号扩展16(rdHC[15:0] − rdHD[15:0])；借位静默丢弃，结果符号扩展写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；rdHD==rdHC 合法
@@ 边界/覆盖：覆盖 0−1 ⇒ −1、0x7FFF−(−1)、0x8000 上界、rd0 作源、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / legality 4 / semantic 4 / boundary 4 / overlap 3（链例 15 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （YAML `tests/inst/base/reg-arith.yaml` 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42A41000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （YAML `tests/inst/base/reg-arith.yaml` 并入）sub.sw: rd2=0x32, rd3=0x1e, bits=16
	__LI	rd2, 0x0000000000000032
	__LI	rd3, 0x000000000000001E
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42A41083
	__CHECK_RD   2, rd1, 0x0000000000000014

	@@ [3] （YAML `tests/inst/base/reg-arith.yaml` 并入）boundary sub.sw: rd2=0x40, rd3=0x40
	__LI	rd2, 0x0000000000000040
	__LI	rd3, 0x0000000000000040
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42A41083
	__CHECK_RD   3, rd1, 0x0000000000000000

	@@ [4] 最大寄存器字段：rd63 = rd1 − rd2，0 − 1 ⇒ −1（符号扩展）
	__LI	rd1, 0x0000000000000000
	__LI	rd2, 0x0000000000000001
	.dd.t32	0x42A7F042
	__CHECK_RD   4, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [5] 0x1234 − 0x00F0 = 0x1144
	TEST_AR_ORRR     5, sub.sw, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd7, 0x00000000000000F0, 0x0000000000001144

	@@ [6] 0 − 1 ⇒ −1 ⇒ 64 位全 1
	TEST_AR_ORRR     6, sub.sw, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	@@ [7] 0x7FFF − 0xFFFF ⇒ 0x7FFF − (−1) = 0x8000 ⇒ 符号扩展
	TEST_AR_ORRR     7, sub.sw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x000000000000FFFF, 0xFFFFFFFFFFFF8000

	@@ [8] 0x8000 − 1 = 0x7FFF（INT16_MIN − 1 落到正半轴）
	TEST_AR_ORRR     8, sub.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000001, 0x0000000000007FFF

	@@ [9] 0x8000 − 0x0001 ⇒ 0x7FFF（同上，立即寄存器路径）
	TEST_AR_ORRR     9, sub.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000001, 0x0000000000007FFF

	@@ [10] 0xFFFF − 0xFFFF = 0
	TEST_AR_ORRR     10, sub.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [11] rd0 作源 C：0 − 0x8000 ⇒ 0x8000 符号扩展
	TEST_AR_ORRR     11, sub.sw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000008000, 0xFFFFFFFFFFFF8000

	@@ [12] rd0 作源 D：0xFFFF − 0 ⇒ −1 符号扩展
	TEST_AR_ORRR     12, sub.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd0, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ [13] 目的=源C（原地）：rd9 = 1 − 2 ⇒ −1
	TEST_AR_ORRR     13, sub.sw, rd9, 0x0000000000000001, rd9, 0x0000000000000001, rd8, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [14] 目的=源D（原地）：rd9 = 2 − rd9(7) ⇒ −5
	TEST_AR_ORRR     14, sub.sw, rd9, 0x0000000000000007, rd8, 0x0000000000000002, rd9, 0x0000000000000007, 0xFFFFFFFFFFFFFFFB

	@@ [15] 两源同名：0x8000 − 0x8000 = 0
	TEST_AR_ORRR     15, sub.sw, rd5, 0x0000000000000000, rd10, 0x0000000000008000, rd10, 0x0000000000008000, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [16] （YAML `tests/inst/base/reg-arith.yaml` 并入）legality sub.sw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     16, sub.sw, ILLI, rd0, rd0, rd0

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     17, sub.sw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
