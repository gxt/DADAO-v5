@@ cmp.uw_orrr_rd.S — cmp.uw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x2A）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：cmp.uw_orrr_rd　形式：orrr　opc：0x42／ha 0x2A　mask：0xFFFC0000　value：0x42A80000　目的银行：RD
@@ 语义：rdHB ← 无符号比较(rdHC[15:0], rdHD[15:0])：< ⇒ −1（64 位全 1）、== ⇒ 0、> ⇒ 1
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；rdHD==rdHC ⇒ 0
@@ 边界/覆盖：覆盖 0x8000 无符号判大、0xFFFF 上界、源高位不参与、rd0 作源、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 4 / semantic 5 / boundary 3 / overlap 3（链例 15 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42A81000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）cmp.uw: rd2=0xa, rd3=0x14, bits=16, signed=False
	set.rd	rd2, 0x000000000000000A
	set.rd	rd3, 0x0000000000000014
	.dd.t32	0x42A81083
	__CHECK_RD   2, rd1, 0xFFFFFFFFFFFFFFFF

	@@ [3] 最大寄存器字段：rd63 = cmp(rd1, rd2)，0x8000 > 1 ⇒ 1（无符号）
	set.rd	rd1, 0x0000000000008000
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x42ABF042
	__CHECK_RD   3, rd63, 0x0000000000000001

	@@ [4] 1 < 2 ⇒ −1（写满 64 位）
	TEST_AR_ORRR     4, cmp.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x0000000000000002, 0xFFFFFFFFFFFFFFFF

	@@ [5] 5 == 5 ⇒ 0
	TEST_AR_ORRR     5, cmp.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000005, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [6] 9 > 2 ⇒ 1
	TEST_AR_ORRR     6, cmp.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000009, rd7, 0x0000000000000002, 0x0000000000000001

	@@ [7] 0xFFFF vs 0 ⇒ 1（无符号上界）
	TEST_AR_ORRR     7, cmp.uw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x0000000000000000, 0x0000000000000001

	@@ [8] 0 vs 0xFFFF ⇒ −1
	TEST_AR_ORRR     8, cmp.uw, rd5, 0x0000000000000000, rd6, 0x0000000000000000, rd7, 0x000000000000FFFF, 0xFFFFFFFFFFFFFFFF

	@@ [9] 0x7FFF < 0x8000 ⇒ −1（无符号：0x8000 更大）
	TEST_AR_ORRR     9, cmp.uw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x0000000000008000, 0xFFFFFFFFFFFFFFFF

	@@ [10] 源高位不参与：低 16 位 5 vs 3 ⇒ 1
	TEST_AR_ORRR     10, cmp.uw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFF0005, rd7, 0x0000000100000003, 0x0000000000000001

	@@ [11] rd0 作源 C：0 < 0xFFFF ⇒ −1
	TEST_AR_ORRR     11, cmp.uw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x000000000000FFFF, 0xFFFFFFFFFFFFFFFF

	@@ [12] 两源都是 rd0 ⇒ 0
	TEST_AR_ORRR     12, cmp.uw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd0, 0x0000000000000000, 0x0000000000000000

	@@ [13] 目的=源C（原地）：rd9 = cmp(rd9=5, 9) ⇒ −1
	TEST_AR_ORRR     13, cmp.uw, rd9, 0x0000000000000005, rd9, 0x0000000000000005, rd8, 0x0000000000000009, 0xFFFFFFFFFFFFFFFF

	@@ [14] 目的=源D（原地）：rd9 = cmp(5, rd9=9) ⇒ 1
	TEST_AR_ORRR     14, cmp.uw, rd9, 0x0000000000000009, rd8, 0x0000000000000005, rd9, 0x0000000000000009, 0xFFFFFFFFFFFFFFFF

	@@ [15] 两源同名 ⇒ 0
	TEST_AR_ORRR     15, cmp.uw, rd5, 0x0000000000000000, rd10, 0x0000000000008000, rd10, 0x0000000000008000, 0x0000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [16] （原 YAML 并入）legality cmp.uw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     16, cmp.uw, ILLI, rd0, rd0, rd0

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     17, cmp.uw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
