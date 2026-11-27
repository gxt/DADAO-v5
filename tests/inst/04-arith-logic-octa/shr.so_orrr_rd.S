@@ shr.so_orrr_rd.S — shr.so rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x13）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：shr.so_orrr_rd　形式：orrr　opc：0x40／ha 0x13　mask：0xFFFC0000　value：0x404C0000　目的银行：RD
@@ 语义：rdHB ← rdHC >> shamt（算术右移，高位补 rdHC[63]）；shamt = rdHD[5:0]（0..63）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；shamt ≤ N=63（6 位域，天然满足）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 4 / overlap 3 + 迁移 3（m13-testcases-045）（链例 18 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联
@@ 移位量边界：0 / 63 / 64 与更大值只取低 6 位（⇒ 0 / 63），不触发 ILLI

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 >> 2 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x404C5187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0F0F0F0F0F0F0F0F
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x404C5187
	__CHECK_RD   1, rd5, 0x03C3C3C3C3C3C3C3

	@@ 最高寄存器作目的（rd63）+ 负数源 + 移位量 2 的编码字（字段边界）
	@@ 规范编码字 0x404FF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x8000000000000000
	set.rd	rd2, 0x0000000000000002
	.dd.t32	0x404FF042
	__CHECK_RD   2, rd63, 0xE000000000000000

	@@ 正数算术右移 = 逻辑右移（移位量 2，YAML semantic 例）
	TEST_AR_ORRR         3, shr.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0x03C3C3C3C3C3C3C3

	@@ 负数算术右移：高位补 1（0x8000000000000000 >> 2 = 0xE000..）
	TEST_AR_ORRR         4, shr.so, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0x0000000000000002, 0xE000000000000000

	@@ 全 1 >> 63 = 全 1（符号位一路补 1）
	TEST_AR_ORRR         5, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x000000000000003F, 0xFFFFFFFFFFFFFFFF

	@@ -2 >> 1 = -1（0xFFFF..FE >> 1）
	TEST_AR_ORRR         6, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFE, rd7, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	@@ 正数最大值 >> 63 = 0（符号位为 0）
	TEST_AR_ORRR         7, shr.so, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x7FFFFFFFFFFFFFFF, rd7, 0x000000000000003F, 0x0000000000000000

	@@ 移位量 32：负数高半补 1
	TEST_AR_ORRR         8, shr.so, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0x0000000000000020, 0xFFFFFFFF80000000

	@@ 移位量 0 ⇒ 原值不变（符号位不参与）
	TEST_AR_ORRR         9, shr.so, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0x0000000000000000, 0x8000000000000000

	@@ 移位量 64 ⇒ 只取低 6 位 = 0 ⇒ 原值不变（不触发 ILLI）
	TEST_AR_ORRR        10, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000040, 0xFFFFFFFFFFFFFFFF

	@@ rd0 作源 C（读出 0，符号位 0）：0 >> 5 = 0
	TEST_AR_ORRR        11, shr.so, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ 目的=源C（原地）
	TEST_AR_ORRR        12, shr.so, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, rd10, 0x0000000000000008, 0x000123456789ABCD

	@@ 目的=源D（原地）：目的旧值 4 就是移位量
	TEST_AR_ORRR        13, shr.so, rd9, 0x0000000000000004, rd10, 0xFFFFFFFFFFFFFFFF, rd9, 0x0000000000000004, 0xFFFFFFFFFFFFFFFF

	@@ 两源同名（负数）：0xFFFF..FF08 >> 8 = 全 1
	TEST_AR_ORRR        14, shr.so, rd9, 0x0000000000000000, rd11, 0xFFFFFFFFFFFFFF08, rd11, 0xFFFFFFFFFFFFFF08, 0xFFFFFFFFFFFFFFFF

	@@ [15] 迁移（m13-testcases-045）：每字节 0x81（全局位 0/7·8/15·16/23·24/31）+ 负号 0xFFFFFFFF81818181 >> 1
	@@   手算：低字 >>1 ⇒ 位 6/7·14/15·22/23·30/31（bit31 由补 1 得到）⇒ 0xC0C0C0C0；
	@@   高字 0xFFFFFFFF 算术右移 1 仍 0xFFFFFFFF ⇒ 0xFFFFFFFFC0C0C0C0
	TEST_AR_ORRR        15, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF81818181, rd7, 0x0000000000000001, 0xFFFFFFFFC0C0C0C0

	@@ [16] 迁移：同位型 >> 7（算术移位的补 1 段跨 nibble 边界）
	@@   手算：0x81818181>>7 = 0x01030303，高 7 位补 1 ⇒ 0xFF030303；高字 0xFFFFFFFF ⇒ 0xFFFFFFFFFF030303
	TEST_AR_ORRR        16, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF81818181, rd7, 0x0000000000000007, 0xFFFFFFFFFF030303

	@@ [17] 迁移：同位型 >> 31（补 1 段铺满 ⇒ 全 1）
	@@   手算：0x81818181>>31 = 1，补 31 个 1 ⇒ 0xFFFFFFFF；高字同 ⇒ 0xFFFFFFFFFFFFFFFF
	TEST_AR_ORRR        17, shr.so, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF81818181, rd7, 0x000000000000001F, 0xFFFFFFFFFFFFFFFF

	@@ 符号位单置 >> 1：算术右移高位补 1 ⇒ 0xC000..（与 shr.uo 同一输入对照）
	TEST_AR_ORRR        18, shr.so, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0x0000000000000001, 0xC000000000000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     19, shr.so, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
