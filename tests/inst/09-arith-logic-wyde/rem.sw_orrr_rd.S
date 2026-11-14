@@ rem.sw_orrr_rd.S — rem.sw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x3B）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：rem.sw_orrr_rd　形式：orrr　opc：0x42／ha 0x3B　mask：0xFFFC0000　value：0x42EC0000　目的银行：RD
@@ 语义：rdHB ← 符号扩展16(rdHC[15:0] rem rdHD[15:0])（余数符号 = 被除数）；除零 ⇒ 被除数（符号扩展）；INT16_MIN rem −1 ⇒ 0
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；rdHD 为 rd0 合法（除零定值）；rdHD==rdHC ⇒ 0
@@ 边界/覆盖：覆盖余数随被除数符号、除零定值、溢出定值 0、源高位垃圾、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 3 / legality 4 / semantic 7 / boundary 3 / overlap 3（链例 18 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x42EC1001
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）rem.sw: rd2=0x64, rd3=0x7, bits=16
	__LI	rd2, 0x0000000000000064
	__LI	rd3, 0x0000000000000007
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42EC1083
	__CHECK_RD   2, rd1, 0x0000000000000002

	@@ [3] （原 YAML 并入）boundary rem.sw: rd2=0x80, rd3=0x7
	__LI	rd2, 0x0000000000000080
	__LI	rd3, 0x0000000000000007
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42EC1083
	__CHECK_RD   3, rd1, 0x0000000000000002

	@@ [4] （原 YAML 并入）encoding rem.sw: rdhd=rd0 (divisor=0) is legal, no ILLI
	__LI	rd2, 0x0000000000000064
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x42EC1080
	__CHECK_RD   4, rd1, 0x0000000000000064

	@@ [5] （原 YAML 并入）rem.sw rem-by-zero: rd2=0x64, rd0(divisor)=0 -> rd1=0x0000000000000064 (signed rem by zero defined value)
	__LI	rd2, 0x0000000000000064
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42EC1080
	__CHECK_RD   5, rd1, 0x0000000000000064

	@@ [6] （原 YAML 并入）rem.sw signed overflow: INT_MIN/-1 -> 0x0000000000000000 (defined value)
	__LI	rd2, 0xFFFFFFFFFFFF8000
	__LI	rd3, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42EC1083
	__CHECK_RD   6, rd1, 0x0000000000000000

	@@ [7] 最大寄存器字段：rd63 = rd1 rem rd2，−100 rem 7 = −2（余数随被除数符号）
	__LI	rd1, 0x000000000000FF9C
	__LI	rd2, 0x0000000000000007
	.dd.t32	0x42EFF042
	__CHECK_RD   7, rd63, 0xFFFFFFFFFFFFFFFE

	@@ [8] −100 rem 7 = −2（余数符号 = 被除数符号）
	TEST_AR_ORRR     8, rem.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FF9C, rd7, 0x0000000000000007, 0xFFFFFFFFFFFFFFFE

	@@ [9] 100 rem −7 = 2
	TEST_AR_ORRR     9, rem.sw, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x000000000000FFF9, 0x0000000000000002

	@@ [10] −100 rem −7 = −2
	TEST_AR_ORRR     10, rem.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FF9C, rd7, 0x000000000000FFF9, 0xFFFFFFFFFFFFFFFE

	@@ [11] INT16_MIN rem −1 ⇒ 0（溢出定值表）
	TEST_AR_ORRR     11, rem.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [12] 0x7FFF rem 2 = 1
	TEST_AR_ORRR     12, rem.sw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x0000000000000002, 0x0000000000000001

	@@ [13] 源高位不参与：低 16 位 −100 rem 7 = −2
	TEST_AR_ORRR     13, rem.sw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFF9C, rd7, 0x0000000000000007, 0xFFFFFFFFFFFFFFFE

	@@ [14] rd0 作源 C：0 rem 7 = 0
	TEST_AR_ORRR     14, rem.sw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [15] 被除数 0：0 rem 0xFFFF = 0
	TEST_AR_ORRR     15, rem.sw, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [16] 目的=源C（原地）：rd9 = rd9(100) rem 7 = 2
	TEST_AR_ORRR     16, rem.sw, rd9, 0x0000000000000064, rd9, 0x0000000000000064, rd8, 0x0000000000000007, 0x0000000000000002

	@@ [17] 目的=源D（原地）：rd9 = 7 rem rd9(100) = 7
	TEST_AR_ORRR     17, rem.sw, rd9, 0x0000000000000064, rd8, 0x0000000000000007, rd9, 0x0000000000000064, 0x0000000000000007

	@@ [18] 两源同名：100 rem 100 = 0
	TEST_AR_ORRR     18, rem.sw, rd5, 0x0000000000000000, rd10, 0x0000000000000064, rd10, 0x0000000000000064, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [19] （原 YAML 并入）legality rem.sw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     19, rem.sw, ILLI, rd0, rd0, rd1

	@@ [20] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     20, rem.sw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
