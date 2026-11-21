@@ rol.o_orri_rd.S — rol.o rdHB, rdHC, immu6（orri, opc 0x40／ha 0x19）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：rol.o_orri_rd　形式：orri　opc：0x40／ha 0x19　mask：0xFFFC0000　value：0x40640000　目的银行：RD
@@ 语义：rdHB ← rol(rdHC, immu6)，64 位逻辑循环左移；immu6 = 0..63 全部合法（无越界值）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；原地旋转允许；
@@   `immu6=0` 合法（`legality_rules.yaml::immu6_zero` 明确不适用于 orri 移位形式）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 1（链例 12 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rol.o(rd6, 5) 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40645185（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | immu6）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0xA5C396F1DEADBEEF
	.dd.t32	0x40645185
	__CHECK_RD   1, rd5, 0xB872DE3BD5B7DDF4

	@@ 最高寄存器作目的（rd63）+ 最大旋转量 63 的编码字（字段边界）
	@@ 规范编码字 0x4067F07F（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | immu6）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0xA5C396F1DEADBEEF
	.dd.t32	0x4067F07F
	__CHECK_RD   2, rd63, 0xD2E1CB78EF56DF77

	@@ immu6=0 合法 ⇒ 原值不变
	TEST_AR_ORRI         3, rol.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xA5C396F1DEADBEEF, 0, 0xA5C396F1DEADBEEF

	@@ 旋转量 1：最高位绕回最低位
	TEST_AR_ORRI         4, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, 1, 0x4B872DE3BD5B7DDF

	@@ 旋转量 32：高低 32 位互换
	TEST_AR_ORRI         5, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, 32, 0xDEADBEEFA5C396F1

	@@ 旋转量 62（= 64−2）
	TEST_AR_ORRI         6, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, 62, 0xE970E5BC77AB6FBB

	@@ 旋转量 63 = W−1（上界）
	TEST_AR_ORRI         7, rol.o, rd5, 0x0000000000000000, rd6, 0xA5C396F1DEADBEEF, 63, 0xD2E1CB78EF56DF77

	@@ 单 bit 0x8000000000000000 左旋 1 ⇒ 0x1（位串首尾相接）
	TEST_AR_ORRI         8, rol.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, 1, 0x0000000000000001

	@@ 源全 1 ⇒ 结果全 1（任意旋转量）
	TEST_AR_ORRI         9, rol.o, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 1, 0xFFFFFFFFFFFFFFFF

	@@ rd0 作源（读出 0）⇒ 结果 0
	TEST_AR_ORRI        10, rol.o, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 5, 0x0000000000000000

	@@ 源全 1 且旋转量 63：全 1 图案旋转不变
	TEST_AR_ORRI        11, rol.o, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 63, 0xFFFFFFFFFFFFFFFF

	@@ 目的=源（原地旋转，允许）
	TEST_AR_ORRI        12, rol.o, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, 8, 0x23456789ABCDEF01

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 13, rol.o, ILLI, rd0, rd6, 5

	__TEST_SECTIONS
