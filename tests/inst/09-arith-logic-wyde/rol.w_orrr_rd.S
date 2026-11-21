@@ rol.w_orrr_rd.S — rol.w rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x11）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：rol.w_orrr_rd　形式：orrr　opc：0x42／ha 0x11　mask：0xFFFC0000　value：0x42440000　目的银行：RD
@@ 语义：rdHB ← 零扩展16(rol(rdHC[15:0], rdHD[3:0]))；orrr 旋转量只有低 4 位参与（天然 mod 16），结果零扩展
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；rdHD 高位（[5:4]）不参与、不触发 ILLI（mod 16）
@@ 边界/覆盖：覆盖 amount 0..15 与 >15 的取模、位模式保持、rd0 作源、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / legality 4 / semantic 7 / boundary 3 / overlap 3（链例 17 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	set.rd	rd2, 0x0000000000000000
	.dd.t32	0x42441080
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）rol.w orrr: rd2(src)=0xFFFFFFFFFFFFBEEF rd3(amount)=0 -> amount mod 16 = 0, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd3, 0x0000000000000000
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42441083
	__CHECK_RD   2, rd1, 0x000000000000BEEF

	@@ [3] （原 YAML 并入）rol.w orrr: rd2(src)=0xFFFFFFFFFFFFBEEF rd3(amount)=1 -> amount mod 16 = 1, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd3, 0x0000000000000001
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42441083
	__CHECK_RD   3, rd1, 0x0000000000007DDF

	@@ [4] （原 YAML 并入）rol.w orrr: rd2(src)=0xFFFFFFFFFFFFBEEF rd3(amount)=7 -> amount mod 16 = 7, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd3, 0x0000000000000007
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42441083
	__CHECK_RD   4, rd1, 0x00000000000077DF

	@@ [5] （原 YAML 并入）rol.w orrr: rd2(src)=0xFFFFFFFFFFFFBEEF rd3(amount)=15 -> amount mod 16 = 15, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd3, 0x000000000000000F
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42441083
	__CHECK_RD   5, rd1, 0x000000000000DF77

	@@ [6] （原 YAML 并入）rol.w orrr: rd2(src)=0xFFFFFFFFFFFFBEEF rd3(amount)=19 -> amount mod 16 = 3, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd3, 0x0000000000000013
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42441083
	__CHECK_RD   6, rd1, 0x000000000000F77D

	@@ [7] （原 YAML 并入）boundary rol.w orrr: rd3=15=W-1, W=16
	set.rd	rd2, 0xFFFFFFFFFFFFBEEF
	set.rd	rd3, 0x000000000000000F
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x42441083
	__CHECK_RD   7, rd1, 0x000000000000DF77

	@@ [8] 最大寄存器字段：rd63 = rol.w(rd1, rd2[3:0]=1)，0x0001 ⇒ 0x0002
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x4247F042
	__CHECK_RD   8, rd63, 0x0000000000000002

	@@ [9] amount=4：0x1234 ⇒ 0x2341
	TEST_AR_ORRR     9, rol.w, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd7, 0x0000000000000004, 0x0000000000002341

	@@ [10] amount=8：0xABCD ⇒ 0xCDAB
	TEST_AR_ORRR     10, rol.w, rd5, 0x0000000000000000, rd6, 0x000000000000ABCD, rd7, 0x0000000000000008, 0x000000000000CDAB

	@@ [11] amount=0 ⇒ 原值（低 16 位，零扩展）
	TEST_AR_ORRR     11, rol.w, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0x000000000000FFFF

	@@ [12] amount=15：0x0001 ⇒ 0x8000
	TEST_AR_ORRR     12, rol.w, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000000F, 0x0000000000008000

	@@ [13] rd0 作源 C ⇒ 0
	TEST_AR_ORRR     13, rol.w, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000007, 0x0000000000000000

	@@ [14] rd0 作源 D（amount = 0）⇒ 原值
	TEST_AR_ORRR     14, rol.w, rd5, 0x0000000000000000, rd6, 0x0000000000001234, rd0, 0x0000000000000000, 0x0000000000001234

	@@ [15] 目的=源C（原地）：rd9 = rol.w(rd9=0xABCD, 8) ⇒ 0xCDAB
	TEST_AR_ORRR     15, rol.w, rd9, 0x000000000000ABCD, rd9, 0x000000000000ABCD, rd8, 0x0000000000000008, 0x000000000000CDAB

	@@ [16] 目的=源D（原地）：rd9 = rol.w(1, rd9[3:0]=15) ⇒ 0x8000
	TEST_AR_ORRR     16, rol.w, rd9, 0x000000000000000F, rd8, 0x0000000000000001, rd9, 0x000000000000000F, 0x0000000000008000

	@@ [17] 两源同名（amount = 0xFF 的低 4 位 = 15）：rol.w(0x00FF, 15) ⇒ 0x807F
	TEST_AR_ORRR     17, rol.w, rd5, 0x0000000000000000, rd10, 0x00000000000000FF, rd10, 0x00000000000000FF, 0x000000000000807F

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ [18] （原 YAML 并入）legality rol.w: dest rdHB=rd0 -> ILLI (dst_rd0)
	TEST_FAULT_ALU3     18, rol.w, ILLI, rd0, rd2, rd0

	@@ [19] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     19, rol.w, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
