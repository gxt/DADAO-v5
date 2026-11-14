@@ div.sw_orrr_rd.S — div.sw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x39）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：div.sw_orrr_rd　形式：orrr　opc：0x42／ha 0x39　mask：0xFFFC0000　value：0x42E40000　目的银行：RD
@@ 语义：rdHB ← 符号扩展16(rdHC[15:0] ÷ rdHD[15:0])（向零截断）；除零 ⇒ −1；INT16_MIN ÷ −1 ⇒ 0xFFFF_FFFF_FFFF_8000（定值表）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；rdHD 为 rd0 合法（除零定值）；rdHD==rdHC ⇒ 1
@@ 边界/覆盖：覆盖四象限符号、除零定值、溢出定值、−32768÷2、源高位垃圾、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 3 / legality 3 / semantic 7 / boundary 5 / overlap 3（链例 19 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x42E41001
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）div.sw: rd2=0x64, rd3=0x7, bits=16
	__LI	rd2, 0x0000000000000064
	__LI	rd3, 0x0000000000000007
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42E41083
	__CHECK_RD   2, rd1, 0x000000000000000E

	@@ [3] （原 YAML 并入）boundary div.sw: rd2=0x80, rd3=0x7
	__LI	rd2, 0x0000000000000080
	__LI	rd3, 0x0000000000000007
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42E41083
	__CHECK_RD   3, rd1, 0x0000000000000012

	@@ [4] （原 YAML 并入）encoding div.sw: rdhd=rd0 (divisor=0) is legal, no ILLI
	__LI	rd2, 0x0000000000000064
	__LI	rd1, 0x0000000000000001
	.dd.t32	0x42E41080
	__CHECK_RD   4, rd1, 0xFFFFFFFFFFFFFFFF

	@@ [5] （原 YAML 并入）div.sw div-by-zero: rd2=0x64, rd0(divisor)=0 -> rd1=0xFFFFFFFFFFFFFFFF (signed div by zero defined value)
	__LI	rd2, 0x0000000000000064
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42E41080
	__CHECK_RD   5, rd1, 0xFFFFFFFFFFFFFFFF

	@@ [6] （原 YAML 并入）div.sw signed overflow: INT_MIN/-1 -> 0xFFFFFFFFFFFF8000 (defined value)
	__LI	rd2, 0xFFFFFFFFFFFF8000
	__LI	rd3, 0xFFFFFFFFFFFFFFFF
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x42E41083
	__CHECK_RD   6, rd1, 0xFFFFFFFFFFFF8000

	@@ [7] 最大寄存器字段：rd63 = rd1 ÷ rd2，−100 ÷ 7 = −14（向零截断）
	__LI	rd1, 0x000000000000FF9C
	__LI	rd2, 0x0000000000000007
	.dd.t32	0x42E7F042
	__CHECK_RD   7, rd63, 0xFFFFFFFFFFFFFFF2

	@@ [8] −100 ÷ 7 = −14（向零截断，`spec/SimRISC-09 §1.3`）
	TEST_AR_ORRR     8, div.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FF9C, rd7, 0x0000000000000007, 0xFFFFFFFFFFFFFFF2

	@@ [9] 100 ÷ −7 = −14
	TEST_AR_ORRR     9, div.sw, rd5, 0x0000000000000000, rd6, 0x0000000000000064, rd7, 0x000000000000FFF9, 0xFFFFFFFFFFFFFFF2

	@@ [10] −100 ÷ −7 = 14
	TEST_AR_ORRR     10, div.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FF9C, rd7, 0x000000000000FFF9, 0x000000000000000E

	@@ [11] 1 ÷ −1 = −1
	TEST_AR_ORRR     11, div.sw, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000FFFF, 0xFFFFFFFFFFFFFFFF

	@@ [12] 0x7FFF ÷ 1 = 0x7FFF
	TEST_AR_ORRR     12, div.sw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x0000000000000001, 0x0000000000007FFF

	@@ [13] −32768 ÷ 1 = −32768（符号扩展）
	TEST_AR_ORRR     13, div.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFF8000

	@@ [14] −32768 ÷ 2 = −16384
	TEST_AR_ORRR     14, div.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFC000

	@@ [15] 源高位不参与：低 16 位 −100 ÷ 7 = −14
	TEST_AR_ORRR     15, div.sw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFF9C, rd7, 0x0000000000000007, 0xFFFFFFFFFFFFFFF2

	@@ [16] rd0 作源 C：0 ÷ 7 = 0
	TEST_AR_ORRR     16, div.sw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [17] 目的=源C（原地）：rd9 = rd9(100) ÷ 7 = 14
	TEST_AR_ORRR     17, div.sw, rd9, 0x0000000000000064, rd9, 0x0000000000000064, rd8, 0x0000000000000007, 0x000000000000000E

	@@ [18] 目的=源D（原地）：rd9 = 100 ÷ rd9(7) = 14
	TEST_AR_ORRR     18, div.sw, rd9, 0x0000000000000007, rd8, 0x0000000000000064, rd9, 0x0000000000000007, 0x000000000000000E

	@@ [19] 两源同名：−100 ÷ −100 = 1
	TEST_AR_ORRR     19, div.sw, rd5, 0x0000000000000000, rd10, 0x000000000000FF9C, rd10, 0x000000000000FF9C, 0x0000000000000001

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [20] （原 YAML 并入）legality div.sw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     20, div.sw, ILLI, rd0, rd0, rd1

	@@ [21] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     21, div.sw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
