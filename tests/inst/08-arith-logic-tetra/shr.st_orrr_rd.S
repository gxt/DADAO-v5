@@ shr.st_orrr_rd.S — shr.st rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x13）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：shr.st_orrr_rd　形式：orrr　opc：0x41／ha 0x13　mask：0xFFFC0000　value：0x414C0000　目的银行：RD
@@ 语义：rdHB ← 符号扩展(rdHC[31:0] >> shamt)（算术右移，高位补 rdHC[31]）；shamt = rdHD[4:0]（对 32 取模、不 ILLI）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；orrr 的移位量天然取低 5 位
@@ 边界/覆盖：边界：负数高位补 1、shamt 31 ⇒ 全 0/全 1、shamt 取模、源高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic+boundary+overlap 15 + 迁移 4（m13-testcases-045）（链例 21 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 >> 1（0x80000000 ⇒ 0xC0000000）的规范编码字
	@@ 规范编码字 0x414C5187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	set.rd	rd6, 0x0000000080000000
	set.rd	rd7, 0x0000000000000001
	.dd.t32	0x414C5187
	__CHECK_RD   1, rd5, 0xFFFFFFFFC0000000

	@@ [encoding 2] 最高寄存器作目的（rd63）+ −1 >> 4 = −1（全 1）
	@@ 规范编码字 0x414FF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	set.rd	rd1, 0x00000000FFFFFFFF
	set.rd	rd2, 0x0000000000000004
	.dd.t32	0x414FF042
	__CHECK_RD   2, rd63, 0xFFFFFFFFFFFFFFFF

	@@ [3] 0x80000000 >> 1 = 0xC0000000 ⇒ 符号扩展 0xFFFFFFFF_C0000000
	TEST_AR_ORRR        3, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0xFFFFFFFFC0000000

	@@ [4] 0xFFFFFFFF >> 4 = 0xFFFFFFFF（全 1）
	TEST_AR_ORRR        4, shr.st, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000004, 0xFFFFFFFFFFFFFFFF

	@@ [5] 0x7FFFFFFF >> 1 = 0x3FFFFFFF（正数高位补 0）
	TEST_AR_ORRR        5, shr.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x0000000000000001, 0x000000003FFFFFFF

	@@ [6] shamt 0 ⇒ 原值（只留低 32 位，符号扩展）
	TEST_AR_ORRR        6, shr.st, rd5, 0x0000000000000000, rd6, 0x8000000000000000, rd7, 0x0000000000000000, 0x0000000000000000

	@@ [7] shamt 31：0x80000000 >> 31 = 0xFFFFFFFF（符号位铺满）
	TEST_AR_ORRR        7, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x000000000000001F, 0xFFFFFFFFFFFFFFFF

	@@ [8] shamt 31：0x7FFFFFFF >> 31 = 0
	TEST_AR_ORRR        8, shr.st, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x000000000000001F, 0x0000000000000000

	@@ [9] shamt 32 ⇒ 取低 5 位 = 0 ⇒ 原值（不触发 ILLI）
	TEST_AR_ORRR        9, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000020, 0xFFFFFFFF80000000

	@@ [10] 0x12345678 >> 8 = 0x00123456（正数）
	TEST_AR_ORRR       10, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000012345678, rd7, 0x0000000000000008, 0x0000000000123456

	@@ [11] 源的高 32 位不参与：0x00000000_80000000 >> 1 仍按 bit31 符号扩展
	TEST_AR_ORRR       11, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0xFFFFFFFFC0000000

	@@ [12] rd0 作源：0 >> 5 = 0
	TEST_AR_ORRR       12, shr.st, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [13] 源=目（原地）：rd9 >> 8
	TEST_AR_ORRR       13, shr.st, rd9, 0x0000000080000000, rd9, 0x0000000080000000, rd10, 0x0000000000000008, 0xFFFFFFFFFF800000

	@@ [14] 目=源D（原地）：rd9 旧值 3 是移位量
	TEST_AR_ORRR       14, shr.st, rd9, 0x0000000000000003, rd10, 0x0000000080000000, rd9, 0x0000000000000003, 0xFFFFFFFFF0000000

	@@ [15] 两源同名：−1 >> 1 = −1
	TEST_AR_ORRR       15, shr.st, rd12, 0x0000000000000000, rd11, 0x00000000FFFFFFFF, rd11, 0x00000000FFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ [16] （YAML boundary 并入）0x0F0F0F0F0F0F0F0F >> 31 = 0
	TEST_AR_ORRR       16, shr.st, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x000000000000001F, 0x0000000000000000

	@@ [17] （YAML semantic 并入）0x0F0F0F0F… >> 2 = 0x03C3C3C3（正数 ⇒ 高位补 0）
	TEST_AR_ORRR       17, shr.st, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0x0000000003C3C3C3

	@@ [18] 迁移（m13-testcases-045）：每字节 0x81（全局位 0/7·8/15·16/23·24/31）+ bit31=1 的算术右移 1
	@@   手算：0x81818181 >>1 ⇒ 位 6/7·14/15·22/23/30/31 ⇒ 0xC0C0C0C0；[63:32] = sign(bit31) = 全 1
	@@   ⇒ 0xFFFFFFFFC0C0C0C0（与 shr.ut 同位型 15 的零扩展结果对照）
	TEST_AR_ORRR       18, shr.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF81818181, rd7, 0x0000000000000001, 0xFFFFFFFFC0C0C0C0

	@@ [19] 迁移：同位型 >> 7（补 1 段跨 nibble 边界）
	@@   手算：0x81818181>>7 = 0x01030303，高 7 位补 1 ⇒ 0xFF030303；[63:32] 全 1 ⇒ 0xFFFFFFFFFF030303
	TEST_AR_ORRR       19, shr.st, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF81818181, rd7, 0x0000000000000007, 0xFFFFFFFFFF030303

	@@ [20] 迁移：0x92345678 >> 0 —— 符号来自**低字 bit31**（源高 32 位为 0 也要全 1 扩展）
	@@   手算：shamt=0 ⇒ 低字原样 0x92345678；[63:32] = sign(bit31=1) = 0xFFFFFFFF ⇒ 0xFFFFFFFF92345678
	TEST_AR_ORRR       20, shr.st, rd5, 0x0000000000000000, rd6, 0x0000000092345678, rd7, 0x0000000000000000, 0xFFFFFFFF92345678

	@@ [21] 迁移：源高 32 位全 1、低字 bit31=0 >> 4 —— 高半**只看低字 bit31**（不得跟着源高位全 1）
	@@   手算：0x12345678>>4 = 0x01234567，bit31=0 ⇒ [63:32] = 0 ⇒ 0x0000000001234567
	TEST_AR_ORRR       21, shr.st, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF12345678, rd7, 0x0000000000000004, 0x0000000001234567

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [18] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       22, shr.st, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
