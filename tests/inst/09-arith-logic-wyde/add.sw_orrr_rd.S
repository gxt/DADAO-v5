@@ add.sw_orrr_rd.S — add.sw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x21）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：add.sw_orrr_rd　形式：orrr　opc：0x42／ha 0x21　mask：0xFFFC0000　value：0x42840000　目的银行：RD
@@ 语义：rdHB ← 符号扩展16(rdHC[15:0] + rdHD[15:0])；16 位和的高位静默丢弃，结果符号扩展写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；rdHD==rdHC 合法
@@ 边界/覆盖：覆盖进位丢符号位（0x7FFF+1 ⇒ 负数）、回绕 0、符号扩展上界与 rd0 作源
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 4 / semantic 4 / boundary 4 / overlap 3（链例 15 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x42841000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）add.sw: rd2=0x32, rd3=0x1e, bits=16
	set.rd	rd2, 0x0000000000000032
	set.rd	rd3, 0x000000000000001E
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42841083
	__CHECK_RD   2, rd1, 0x0000000000000050

	@@ [3] （原 YAML 并入）boundary add.sw: rd2=0x40, rd3=0x40
	set.rd	rd2, 0x0000000000000040
	set.rd	rd3, 0x0000000000000040
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x42841083
	__CHECK_RD   3, rd1, 0x0000000000000080

	@@ [4] 最大寄存器字段：rd63 = rd1 + rd2，0x7FFF + 1 ⇒ 0x8000 ⇒ 符号扩展
	set.rd	rd1, 0x0000000000007FFF
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x4287F042
	__CHECK_RD   4, rd63, 0xFFFFFFFFFFFF8000

	@@ [5] 0x1234 + 0x00F0 = 0x1324（正数符号扩展为同值）
	TEST_AR_ORRR     5, add.sw, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd7, 0x00000000000000F0, 0x0000000000001324

	@@ [6] −1 + −1 = −2（0xFFFF + 0xFFFF）
	TEST_AR_ORRR     6, add.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x000000000000FFFF, 0xFFFFFFFFFFFFFFFE

	@@ [7] −1 + 1 = 0（16 位回绕后符号扩展为 0）
	TEST_AR_ORRR     7, add.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd7, 0x0000000000000001, 0x0000000000000000

	@@ [8] 0x7FFF + 1 ⇒ 0x8000 ⇒ 符号扩展 −32768
	TEST_AR_ORRR     8, add.sw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x0000000000000001, 0xFFFFFFFFFFFF8000

	@@ [9] 0x8000 + 0x8000 ⇒ 0x10000 ⇒ 0（16 位回绕）
	TEST_AR_ORRR     9, add.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000008000, 0x0000000000000000

	@@ [10] 0x4000 + 0x4000 ⇒ 0x8000 ⇒ 符号扩展
	TEST_AR_ORRR     10, add.sw, rd5, 0x0000000000000000, rd6, 0x0000000000004000, rd7, 0x0000000000004000, 0xFFFFFFFFFFFF8000

	@@ [11] rd0 作源 C：0 + −1 ⇒ 符号扩展 −1
	TEST_AR_ORRR     11, add.sw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x000000000000FFFF, 0xFFFFFFFFFFFFFFFF

	@@ [12] rd0 作源 D：0x8000 + 0 = 符号扩展 −32768
	TEST_AR_ORRR     12, add.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd0, 0x0000000000000000, 0xFFFFFFFFFFFF8000

	@@ [13] 目的=源C（原地）：rd9 = 1 + 0x7FFF ⇒ 0x8000
	TEST_AR_ORRR     13, add.sw, rd9, 0x0000000000000001, rd9, 0x0000000000000001, rd8, 0x0000000000007FFF, 0xFFFFFFFFFFFF8000

	@@ [14] 目的=源D（原地）：rd9 = 0xFFFF + rd9(−1) ⇒ −2
	TEST_AR_ORRR     14, add.sw, rd9, 0x000000000000FFFF, rd8, 0x000000000000FFFF, rd9, 0x000000000000FFFF, 0xFFFFFFFFFFFFFFFE

	@@ [15] 两源同名：0x8000 + 0x8000 ⇒ 0（16 位回绕）
	TEST_AR_ORRR     15, add.sw, rd5, 0x0000000000000000, rd10, 0x0000000000008000, rd10, 0x0000000000008000, 0x0000000000000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [16] （原 YAML 并入）legality add.sw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     16, add.sw, ILLI, rd0, rd0, rd0

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     17, add.sw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
