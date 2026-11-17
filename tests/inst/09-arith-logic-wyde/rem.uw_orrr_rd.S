@@ rem.uw_orrr_rd.S — rem.uw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x3A）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：rem.uw_orrr_rd　形式：orrr　opc：0x42／ha 0x3A　mask：0xFFFC0000　value：0x42E80000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rdHC[15:0] mod rdHD[15:0])；除零 ⇒ 被除数（零扩展，不抛异常）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；rdHD 为 rd0 合法（除零定值）；rdHD==rdHC ⇒ 0
@@ 边界/覆盖：覆盖除零定值、0xFFFF 上下界、源高位垃圾、rd0 作源、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 3 / legality 4 / semantic 5 / boundary 3 / overlap 3（链例 16 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	set.rd	rd1, 0x0000000000000001
	.dd.t32	0x42E81001
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）rem.uw: rd2=0x64, rd3=0x7, bits=16
	set.rd	rd2, 0x0000000000000064
	set.rd	rd3, 0x0000000000000007
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42E81083
	__CHECK_RD   2, rd1, 0x0000000000000002

	@@ [3] （原 YAML 并入）boundary rem.uw: rd2=0x64, rd3=0x7
	set.rd	rd2, 0x0000000000000064
	set.rd	rd3, 0x0000000000000007
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42E81083
	__CHECK_RD   3, rd1, 0x0000000000000002

	@@ [4] （原 YAML 并入）encoding rem.uw: rdhd=rd0 (divisor=0) is legal, no ILLI
	set.rd	rd2, 0x0000000000000064
	set.rd	rd1, 0x0000000000000001
	.dd.t32	0x42E81080
	__CHECK_RD   4, rd1, 0x0000000000000064

	@@ [5] （原 YAML 并入）rem.uw rem-by-zero: rd2=0x64, rd0(divisor)=0 -> rd1=0x0000000000000064 (unsigned rem by zero defined value)
	set.rd	rd2, 0x0000000000000064
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42E81080
	__CHECK_RD   5, rd1, 0x0000000000000064

	@@ [6] 最大寄存器字段：rd63 = rd1 rem rd2，0xFFFF rem 0x10 = 0x0F
	set.rd	rd1, 0x000000000000FFFF
	set.rd	rd2, 0x0000000000000010
	.dd.t32	0x42EBF042
	__CHECK_RD   6, rd63, 0x000000000000000F

	@@ [7] 0x1234 rem 0x0100 = 0x34
	TEST_AR_ORRR     7, rem.uw, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd7, 0x0000000000000100, 0x0000000000000034

	@@ [8] 0xFFFF rem 0xFFFF = 0
	TEST_AR_ORRR     8, rem.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [9] 0xFFFF rem 1 = 0
	TEST_AR_ORRR     9, rem.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [10] 1 rem 0xFFFF = 1（被除数小于除数）
	TEST_AR_ORRR     10, rem.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000FFFF, 0x0000000000000001

	@@ [11] 源高位不参与：低 16 位 100 rem 7 = 2
	TEST_AR_ORRR     11, rem.uw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFF0064, rd7, 0x0000000000000007, 0x0000000000000002

	@@ [12] rd0 作源 C：0 rem 7 = 0
	TEST_AR_ORRR     12, rem.uw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [13] 被除数 0：0 rem 0xFFFF = 0
	TEST_AR_ORRR     13, rem.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x000000000000FFFF, 0x0000000000000000

	@@ [14] 目的=源C（原地）：rd9 = rd9(100) rem 7 = 2
	TEST_AR_ORRR     14, rem.uw, rd9, 0x0000000000000064, rd9, 0x0000000000000064, rd8, 0x0000000000000007, 0x0000000000000002

	@@ [15] 目的=源D（原地）：rd9 = 100 rem rd9(7) = 2
	TEST_AR_ORRR     15, rem.uw, rd9, 0x0000000000000007, rd8, 0x0000000000000064, rd9, 0x0000000000000007, 0x0000000000000002

	@@ [16] 两源同名：100 rem 100 = 0
	TEST_AR_ORRR     16, rem.uw, rd5, 0x0000000000000000, rd10, 0x0000000000000064, rd10, 0x0000000000000064, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [17] （原 YAML 并入）legality rem.uw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     17, rem.uw, ILLI, rd0, rd0, rd1

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     18, rem.uw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
