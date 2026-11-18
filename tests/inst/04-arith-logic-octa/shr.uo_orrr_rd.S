@@ shr.uo_orrr_rd.S — shr.uo rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x12）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：shr.uo_orrr_rd　形式：orrr　opc：0x40／ha 0x12　mask：0xFFFC0000　value：0x40480000　目的银行：RD
@@ 语义：rdHB ← rdHC >> shamt（逻辑右移，高位补零）；shamt = rdHD[5:0]（0..63）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；shamt ≤ N=63（6 位域，天然满足）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3 + 迁移 3（m13-testcases-045）（链例 17 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联
@@ 移位量边界：0 / 63 / 64 与更大值只取低 6 位（⇒ 0 / 63），不触发 ILLI

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 >> 2 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40485187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0F0F0F0F0F0F0F0F
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x40485187
	__CHECK_RD   1, rd5, 0x03C3C3C3C3C3C3C3

	@@ 最高寄存器作目的（rd63）+ 移位量 63 的编码字（字段边界）
	@@ 规范编码字 0x404BF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x8000000000000000
	set.rd	rd2, 0x000000000000003F
	.dd.t32	0x404BF042
	__CHECK_RD   2, rd63, 0x0000000000000001

	@@ 移位量 2（YAML semantic 例）
	TEST_AR_ORRR         3, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0x03C3C3C3C3C3C3C3

	@@ 移位量 0 ⇒ 原值不变
	TEST_AR_ORRR         4, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000000, 0x0F0F0F0F0F0F0F0F

	@@ 符号位按逻辑移位补零：0x8000000000000000 >> 63 = 1（YAML boundary 例）
	TEST_AR_ORRR         5, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, rd7, 0x000000000000003F, 0x0000000000000001

	@@ 全 1 >> 1 = 0x7FFF..F（高位补零，不是算术右移）
	TEST_AR_ORRR         6, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000001, 0x7FFFFFFFFFFFFFFF

	@@ rd0 作源 C（读出 0）：0 >> 5 = 0
	TEST_AR_ORRR         7, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ 移位量 32：高半搬到低半
	TEST_AR_ORRR         8, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, rd7, 0x0000000000000020, 0x0000000080000000

	@@ 移位量 63（最大值）：全 1 >> 63 = 1
	TEST_AR_ORRR         9, shr.uo, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x000000000000003F, 0x0000000000000001

	@@ 移位量 64 ⇒ 只取低 6 位 = 0 ⇒ 原值不变（不触发 ILLI）
	TEST_AR_ORRR        10, shr.uo, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000040, 0xFFFFFFFFFFFFFFFF

	@@ 移位量全 1 ⇒ 低 6 位 = 63：0x8000000000000000 >> 63 = 1
	TEST_AR_ORRR        11, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, 0x0000000000000001

	@@ 目的=源C（原地）
	TEST_AR_ORRR        12, shr.uo, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, rd10, 0x0000000000000008, 0x000123456789ABCD

	@@ 目的=源D（原地）：目的旧值 4 就是移位量
	TEST_AR_ORRR        13, shr.uo, rd9, 0x0000000000000004, rd10, 0xFFFFFFFFFFFFFFFF, rd9, 0x0000000000000004, 0x0FFFFFFFFFFFFFFF

	@@ 两源同名：0x108 >> 8 = 1
	TEST_AR_ORRR        14, shr.uo, rd9, 0xFFFFFFFFFFFFFFFF, rd11, 0x0000000000000108, rd11, 0x0000000000000108, 0x0000000000000001

	@@ [15] 迁移（m13-testcases-045）：分散位型 0x21212121 >> 1（逻辑右移、高位补 0）
	@@   手算：全局位 0/5·8/13·16/21·24/29 右移 1 ⇒ 4/7·12/15·20/23·28 ⇒ 0x10909090（与 shr.so 同位型对照）
	TEST_AR_ORRR        15, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000021212121, rd7, 0x0000000000000001, 0x0000000010909090

	@@ [16] 迁移：同位型 >> 7（低位被移出，bit0/5 丢失）
	@@   手算：0x21212121 >> 7 = 0x00424242（位 1/6·9/14·17/22，低位 0/5 被移出）
	TEST_AR_ORRR        16, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000021212121, rd7, 0x0000000000000007, 0x0000000000424242

	@@ [17] 迁移：符号位 + 低位 1 的混合值 >> 31（逻辑右移 ⇒ 高半由 bit63 补零、不是全 1）
	@@   手算：0xFFFFFFFF80000001 >> 31 = 0x00000001FFFFFFFF（对比 shr.so 同位型 >> 31 = 全 1）
	TEST_AR_ORRR        17, shr.uo, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF80000001, rd7, 0x000000000000001F, 0x00000001FFFFFFFF

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     18, shr.uo, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
