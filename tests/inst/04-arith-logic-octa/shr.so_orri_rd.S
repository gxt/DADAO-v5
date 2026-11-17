@@ shr.so_orri_rd.S — shr.so rdHB, rdHC, immu6（orri, opc 0x40／ha 0x1B）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：shr.so_orri_rd　形式：orri　opc：0x40／ha 0x1B　mask：0xFFFC0000　value：0x406C0000　目的银行：RD
@@ 语义：rdHB ← rdHC >> immu6（算术右移，高位补 rdHC[63]）；immu6 = 0..63
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；
@@   `immu6=0` 合法（`legality_rules.yaml::immu6_zero` 明确不适用于移位/扩展的 orri 形式）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 1（链例 12 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 >> 2 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x406C5182（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | immu6）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0F0F0F0F0F0F0F0F
	.dd.t32	0x406C5182
	__CHECK_RD   1, rd5, 0x03C3C3C3C3C3C3C3

	@@ 最高寄存器作目的（rd63）+ 负数源 + 最大立即数 63 的编码字（字段边界）
	@@ 规范编码字 0x406FF07F（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | immu6）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x8000000000000000
	.dd.t32	0x406FF07F
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ 正数算术右移 = 逻辑右移（移位量 2，YAML semantic 例）
	TEST_AR_ORRI         3, shr.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, 2, 0x03C3C3C3C3C3C3C3

	@@ 负数算术右移：高位补 1（0x8000000000000000 >> 2 = 0xE000..）
	TEST_AR_ORRI         4, shr.so, rd5, 0x0000000000000000, rd6, 0x8000000000000000, 2, 0xE000000000000000

	@@ 全 1 >> 63 = 全 1（符号位一路补 1）
	TEST_AR_ORRI         5, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, 63, 0xFFFFFFFFFFFFFFFF

	@@ -2 >> 1 = -1（0xFFFF..FE >> 1）
	TEST_AR_ORRI         6, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFE, 1, 0xFFFFFFFFFFFFFFFF

	@@ 正数最大值 >> 63 = 0（符号位为 0）
	TEST_AR_ORRI         7, shr.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x7FFFFFFFFFFFFFFF, 63, 0x0000000000000000

	@@ 移位量 32：负数高半补 1
	TEST_AR_ORRI         8, shr.so, rd5, 0x0000000000000000, rd6, 0x8000000000000000, 32, 0xFFFFFFFF80000000

	@@ 移位量 0 合法 ⇒ 原值不变（不触发 ILLI）
	TEST_AR_ORRI         9, shr.so, rd5, 0x0000000000000000, rd6, 0x8000000000000000, 0, 0x8000000000000000

	@@ 移位量 63（YAML boundary 例）：正数 0x0F0F.. >> 63 = 0
	TEST_AR_ORRI        10, shr.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, 63, 0x0000000000000000

	@@ 移位量 4：负数每半字节右移一格、高位补 1
	TEST_AR_ORRI        11, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF00000000, 4, 0xFFFFFFFFF0000000

	@@ 目的=源C（原地）
	TEST_AR_ORRI        12, shr.so, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, 8, 0x000123456789ABCD

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU_ORRI 13, shr.so, ILLI, rd0, rd6, 2

	__TEST_SECTIONS
