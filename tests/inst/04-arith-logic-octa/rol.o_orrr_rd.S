@@ rol.o_orrr_rd.S — rol.o rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x11）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：rol.o_orrr_rd　形式：orrr　opc：0x40／ha 0x11　mask：0xFFFC0000　value：0x40440000　目的银行：RD
@@ 语义：rdHB ← rol(rdHC, rdHD[5:0])，64 位逻辑循环左移；旋转量只取源 D 低 6 位
@@   ⇒ 天然等价于 amount mod 64（64/65/… 不触发 ILLI，按低 6 位取模）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；
@@   原地旋转允许；源 C 与旋转量源 D 可为同一寄存器（先读源后写目的）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 4 / overlap 2（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rol.o(rd6, rd7) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40445187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0xA5C396F1DEADBEEF
	set.rd	rd7, 0x0000000000000005
	.dd.t32	0x40445187
	__CHECK_RD   1, rd5, 0xB872DE3BD5B7DDF4

	@@ 最高寄存器作目的（rd63）+ 旋转量 32 的编码字（字段边界）
	@@ 规范编码字 0x4047F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0xA5C396F1DEADBEEF
	set.rd	rd2, 0x0000000000000020
	.dd.t32	0x4047F042
	__CHECK_RD   2, rd63, 0xDEADBEEFA5C396F1

	@@ 旋转量 0 ⇒ 原值不变
	TEST_AR_ORRR         3, rol.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xA5C396F1DEADBEEF, rd7, 0x0000000000000000, 0xA5C396F1DEADBEEF

	@@ 旋转量 1：最高位绕回最低位
	TEST_AR_ORRR         4, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, rd7, 0x0000000000000001, 0x4B872DE3BD5B7DDF

	@@ 旋转量 31
	TEST_AR_ORRR         5, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, rd7, 0x000000000000001F, 0xEF56DF77D2E1CB78

	@@ 旋转量 32：高低 32 位互换
	TEST_AR_ORRR         6, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, rd7, 0x0000000000000020, 0xDEADBEEFA5C396F1

	@@ 旋转量 63 = W−1（上界）
	TEST_AR_ORRR         7, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, rd7, 0x000000000000003F, 0xD2E1CB78EF56DF77

	@@ 旋转量 65 只取低 6 位 ⇒ 等价于 1（mod 64，不触发 ILLI）
	TEST_AR_ORRR         8, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, rd7, 0x0000000000000041, 0x4B872DE3BD5B7DDF

	@@ 旋转量 64 ⇒ 低 6 位为 0 ⇒ 原值不变
	TEST_AR_ORRR         9, rol.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xA5C396F1DEADBEEF, rd7, 0x0000000000000040, 0xA5C396F1DEADBEEF

	@@ 单 bit 0x1 左旋 63 ⇒ 最高位（循环移动的另一端）
	TEST_AR_ORRR        10, rol.o, rd5, 0x0000000000000000, rd6, 0x0000000000000001, rd7, 0x000000000000003F, 0x8000000000000000

	@@ 单 bit 0x8000000000000000 左旋 1 ⇒ 0x1
	TEST_AR_ORRR        11, rol.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, rd7, 0x0000000000000001, 0x0000000000000001

	@@ rd0 作源 C（读出 0）⇒ 结果 0
	TEST_AR_ORRR        12, rol.o, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ 目的=源 C（原地旋转，允许）
	TEST_AR_ORRR        13, rol.o, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, rd10, 0x0000000000000008, 0x23456789ABCDEF01

	@@ 目的=旋转量源 D（先读源后写目的）：rd9=37 为旋转量，结果按 37 旋转
	TEST_AR_ORRR        14, rol.o, rd9, 0x0000000000000025, rd10, 0x0123456789ABCDEF, rd9, 0x0000000000000025, 0x3579BDE02468ACF1

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     15, rol.o, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
