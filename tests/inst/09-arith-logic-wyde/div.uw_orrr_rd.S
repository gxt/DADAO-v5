@@ div.uw_orrr_rd.S — div.uw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x38）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：div.uw_orrr_rd　形式：orrr　opc：0x42／ha 0x38　mask：0xFFFC0000　value：0x42E00000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rdHC[15:0] ÷ rdHD[15:0])（无符号、向零截断）；除零 ⇒ 定值 0xFFFF（不抛异常，`spec/SimRISC-04 §1.4`）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；rdHD 为 rd0 合法（除数 0 ⇒ 定值）；rdHD==rdHC ⇒ 1
@@ 边界/覆盖：覆盖除零定值、0xFFFF 上下界、商截断、源高位垃圾、rd0 作源与被除数 0、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 3 / legality 4 / semantic 5 / boundary 4 / overlap 3（链例 17 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （YAML `tests/inst/base/reg-arith.yaml` 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x42E01001
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （YAML `tests/inst/base/reg-arith.yaml` 并入）div.uw: rd2=0x64, rd3=0x7, bits=16
	__LI	rd2, 0x0000000000000064
	__LI	rd3, 0x0000000000000007
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42E01083
	__CHECK_RD   2, rd1, 0x000000000000000E

	@@ [3] （YAML `tests/inst/base/reg-arith.yaml` 并入）boundary div.uw: rd2=0x64, rd3=0x7
	__LI	rd2, 0x0000000000000064
	__LI	rd3, 0x0000000000000007
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42E01083
	__CHECK_RD   3, rd1, 0x000000000000000E

	@@ [4] （YAML `tests/inst/base/reg-arith.yaml` 并入）encoding div.uw: rdhd=rd0 (divisor=0) is legal, no ILLI
	__LI	rd2, 0x0000000000000064
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x42E01080
	__CHECK_RD   4, rd1, 0x000000000000FFFF

	@@ [5] （YAML `tests/inst/base/reg-arith.yaml` 并入）div.uw div-by-zero: rd2=0x64, rd0(divisor)=0 -> rd1=0x000000000000FFFF (unsigned div by zero defined value)
	__LI	rd2, 0x0000000000000064
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42E01080
	__CHECK_RD   5, rd1, 0x000000000000FFFF

	@@ [6] 最大寄存器字段：rd63 = rd1 ÷ rd2，0xFFFF ÷ 1 = 0xFFFF
	__LI	rd1, 0x000000000000FFFF
	__LI	rd2, 0x0000000000000001
	.dd.t32	0x42E3F042
	__CHECK_RD   6, rd63, 0x000000000000FFFF

	@@ [7] 0x1234 ÷ 0x0100 = 0x12（向零截断）
	TEST_AR_ORRR     7, div.uw, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd7, 0x0000000000000100, 0x0000000000000012

	@@ [8] 0xFFFF ÷ 0xFFFF = 1
	TEST_AR_ORRR     8, div.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x000000000000FFFF, 0x0000000000000001

	@@ [9] 0xFFFF ÷ 1 = 0xFFFF（无符号上界）
	TEST_AR_ORRR     9, div.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x0000000000000001, 0x000000000000FFFF

	@@ [10] 1 ÷ 0xFFFF = 0（商截断）
	TEST_AR_ORRR     10, div.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [11] 0x8000 ÷ 2 = 0x4000（无符号：高位不进符号）
	TEST_AR_ORRR     11, div.uw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000002, 0x0000000000004000

	@@ [12] 源高位不参与：低 16 位 100 ÷ 7 = 14
	TEST_AR_ORRR     12, div.uw, rd5, 0x0000000000000000, rd6, 0x0000FFFFFFFF0064, rd7, 0x0000FFFFFFFF0007, 0x000000000000000E

	@@ [13] rd0 作源 C：0 ÷ 7 = 0
	TEST_AR_ORRR     13, div.uw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [14] 被除数 0：0 ÷ 0xFFFF = 0
	TEST_AR_ORRR     14, div.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [15] 目的=源C（原地）：rd9 = rd9(100) ÷ 7 = 14
	TEST_AR_ORRR     15, div.uw, rd9, 0x0000000000000064, rd9, 0x0000000000000064, rd8, 0x0000000000000007, 0x000000000000000E

	@@ [16] 目的=源D（原地）：rd9 = 100 ÷ rd9(7) = 14
	TEST_AR_ORRR     16, div.uw, rd9, 0x0000000000000007, rd8, 0x0000000000000064, rd9, 0x0000000000000007, 0x000000000000000E

	@@ [17] 两源同名：100 ÷ 100 = 1
	TEST_AR_ORRR     17, div.uw, rd5, 0x0000000000000000, rd10, 0x0000000000000064, rd10, 0x0000000000000064, 0x0000000000000001

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [18] （YAML `tests/inst/base/reg-arith.yaml` 并入）legality div.uw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     18, div.uw, ILLI, rd0, rd0, rd1

	@@ [19] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     19, div.uw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
