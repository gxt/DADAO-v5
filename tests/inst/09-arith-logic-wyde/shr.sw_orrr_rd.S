@@ shr.sw_orrr_rd.S — shr.sw rdHB, rdHC, rdHD（orrr, opc 0x42／ha 0x13）
@@ 大类：09-arith-logic-wyde（16 位数据运算，`spec/SimRISC-09`）；册目录 `tests/inst/09-arith-logic-wyde/`
@@ id：shr.sw_orrr_rd　形式：orrr　opc：0x42／ha 0x13　mask：0xFFFC0000　value：0x424C0000　目的银行：RD
@@ 语义：rdHB ← 符号扩展16(rdHC[15:0] >> rdHD[3:0])（算术右移，高位补 rdHC[15]）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；rdHD 高位（[5:4]）不参与（见 `新发现/坑`）
@@ 边界/覆盖：覆盖负数补 1、shamt 0/1/15/16 的掩码、源=目原地、三种别名
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / legality 4 / semantic 4 / boundary 5 / overlap 3（链例 16 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [1] （原 YAML 并入）encoding: word matches opcodes.yaml mask/value, fields legal, no ILLI
	.dd.t32	0x424C1000
	__CHECK_RD   1, rd1, 0x0000000000000000

	@@ [2] （原 YAML 并入）shr.sw: rd2(src)=0xf0f0f0f0f0f0f0f, rd3(shamt)=2, N=15
	__LI	rd2, 0x0F0F0F0F0F0F0F0F
	__LI	rd3, 0x0000000000000002
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x424C1083
	__CHECK_RD   2, rd1, 0x00000000000003C3

	@@ [3] （原 YAML 并入）boundary shr.sw: rd2(src)=0xf0f0f0f0f0f0f0f, rd3(shamt)=15=N, N=15
	__LI	rd2, 0x0F0F0F0F0F0F0F0F
	__LI	rd3, 0x000000000000000F
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x424C1083
	__CHECK_RD   3, rd1, 0x0000000000000000

	@@ [4] 最大寄存器字段：rd63 = rd1 >> rd2[3:0]（算术），0x8000 >> 15 ⇒ −1
	__LI	rd1, 0x0000000000008000
	__LI	rd2, 0x000000000000000F
	.dd.t32	0x424FF042
	__CHECK_RD   4, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [5] 0x8000 >> 1 = 0xC000（符号扩展）
	TEST_AR_ORRR     5, shr.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFC000

	@@ [6] 0xF000 >> 4 = 0xFF00 ⇒ 符号扩展 −256
	TEST_AR_ORRR     6, shr.sw, rd5, 0x0000000000000000, rd6, 0x000000000000F000, rd7, 0x0000000000000004, 0xFFFFFFFFFFFFFF00

	@@ [7] 0xFF00 >> 4 ⇒ −16（符号位填满）
	TEST_AR_ORRR     7, shr.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FF00, rd7, 0x0000000000000004, 0xFFFFFFFFFFFFFFF0

	@@ [8] shamt=0 ⇒ 符号扩展原值（0x8001）
	TEST_AR_ORRR     8, shr.sw, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFF8001, rd7, 0x0000000000000000, 0xFFFFFFFFFFFF8001

	@@ [9] shamt=16 只取 rdHD[3:0] = 0 ⇒ 符号扩展原值（不触发 ILLI）
	TEST_AR_ORRR     9, shr.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008001, rd7, 0x0000000000000010, 0xFFFFFFFFFFFF8001

	@@ [10] shamt=15：0x8000 >> 15 ⇒ −1（符号填充）
	TEST_AR_ORRR     10, shr.sw, rd5, 0x0000000000000000, rd6, 0x0000000000008000, rd7, 0x000000000000000F, 0xFFFFFFFFFFFFFFFF

	@@ [11] shamt=15：0x7FFF >> 15 = 0
	TEST_AR_ORRR     11, shr.sw, rd5, 0x0000000000000000, rd6, 0x0000000000007FFF, rd7, 0x000000000000000F, 0x0000000000000000

	@@ [12] rd0 作源 C ⇒ 0
	TEST_AR_ORRR     12, shr.sw, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [13] rd0 作源 D（shamt = 0）⇒ 符号扩展原值
	TEST_AR_ORRR     13, shr.sw, rd5, 0x0000000000000000, rd6, 0x000000000000FFFF, rd0, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF

	@@ [14] 目的=源C（原地）：rd9 = rd9(0x8000) >> 8 = 0xFF80
	TEST_AR_ORRR     14, shr.sw, rd9, 0x0000000000008000, rd9, 0x0000000000008000, rd8, 0x0000000000000008, 0xFFFFFFFFFFFFFF80

	@@ [15] 目的=源D（原地）：rd9 = 0x0100 >> rd9[3:0]=4 ⇒ 0x10
	TEST_AR_ORRR     15, shr.sw, rd9, 0x0000000000000004, rd8, 0x0000000000000100, rd9, 0x0000000000000004, 0x0000000000000010

	@@ [16] 两源同名：0x8001 >> 1 ⇒ 0xFFFF_FFFF_FFFF_C000（符号扩展）
	TEST_AR_ORRR     16, shr.sw, rd5, 0x0000000000000000, rd10, 0x0000000000008001, rd10, 0x0000000000008001, 0xFFFFFFFFFFFFC000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [17] （原 YAML 并入）legality shr.sw: dest=rd0/rb0 → ILLI (dst_rd0)
	TEST_FAULT_ALU3     17, shr.sw, ILLI, rd0, rd0, rd0

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI（`dst_rd0`）
	TEST_FAULT_ALU3     18, shr.sw, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
