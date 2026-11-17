@@ shl.o_orrr_rd.S — shl.o rdHB, rdHC, rdHD（orrr, opc 0x40／ha 0x10）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §2.2`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：shl.o_orrr_rd　形式：orrr　opc：0x40／ha 0x10　mask：0xFFFC0000　value：0x40400000　目的银行：RD
@@ 语义：rdHB ← rdHC << shamt（左移，低位补零）；shamt = rdHD[5:0]（0..63）
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0（读出 0）；shamt ≤ N=63（6 位域，天然满足）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3 + 迁移 4（m13-testcases-045）（链例 18 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联
@@ 移位量边界：0（不动）/ 63（最大值）/ 64 与更大值只取低 6 位（⇒ 0 / 63），不触发 ILLI

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ rd5 = rd6 << 2 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x40405187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | rd7）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0F0F0F0F0F0F0F0F
	set.rd	rd7, 0x0000000000000002
	.dd.t32	0x40405187
	__CHECK_RD   1, rd5, 0x3C3C3C3C3C3C3C3C

	@@ 最高寄存器作目的（rd63）+ 移位量 1 的编码字（字段边界）
	@@ 规范编码字 0x4043F042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x0000000000000001
	set.rd	rd2, 0x0000000000000001
	.dd.t32	0x4043F042
	__CHECK_RD   2, rd63, 0x0000000000000002

	@@ 移位量 2（YAML semantic 例）
	TEST_AR_ORRR         3, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0x3C3C3C3C3C3C3C3C

	@@ 移位量 0 ⇒ 原值不变
	TEST_AR_ORRR         4, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000000, 0x0F0F0F0F0F0F0F0F

	@@ 左移溢出：0x8000000000000000 << 1 ⇒ 0（bit63 移出）
	TEST_AR_ORRR         5, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, rd7, 0x0000000000000001, 0x0000000000000000

	@@ 逐 nibble 值 << 4 ⇒ 每半字节左邻（低位补零）
	TEST_AR_ORRR         6, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, rd7, 0x0000000000000004, 0x123456789ABCDEF0

	@@ rd0 作源 C（读出 0）：0 << 5 = 0
	TEST_AR_ORRR         7, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ 移位量 63（最大值）：1 << 63 = 0x8000000000000000
	TEST_AR_ORRR         8, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0x000000000000003F, 0x8000000000000000

	@@ 移位量 32：低半搬到高半
	TEST_AR_ORRR         9, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000020, 0xFFFFFFFF00000000

	@@ 移位量 64 ⇒ 只取低 6 位 = 0 ⇒ 原值不变（不触发 ILLI）
	TEST_AR_ORRR        10, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000040, 0x0F0F0F0F0F0F0F0F

	@@ 移位量全 1 ⇒ 低 6 位 = 63：1 << 63 = 0x8000000000000000
	TEST_AR_ORRR        11, shl.o, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, rd7, 0xFFFFFFFFFFFFFFFF, 0x8000000000000000

	@@ 目的=源C（原地）
	TEST_AR_ORRR        12, shl.o, rd9, 0x0123456789ABCDEF, rd9, 0x0123456789ABCDEF, rd10, 0x0000000000000008, 0x23456789ABCDEF00

	@@ 目的=源D（原地）：目的旧值 3 就是移位量
	TEST_AR_ORRR        13, shl.o, rd9, 0x0000000000000003, rd10, 0x0000000000000001, rd9, 0x0000000000000003, 0x0000000000000008

	@@ 两源同名：7 << 7 = 0x380
	TEST_AR_ORRR        14, shl.o, rd9, 0xFFFFFFFFFFFFFFFF, rd11, 0x0000000000000007, rd11, 0x0000000000000007, 0x0000000000000380

	@@ [15] 迁移（m13-testcases-045）：分散位型 0x21212121（每字节 0x21 ⇒ 全局位 0/5·8/13·16/21·24/29）<< 1
	@@   手算：位 i → i+1 ⇒ 1/6·9/14·17/22·25/30 ⇒ 每字节 0x42 ⇒ 0x42424242（与 nibble 位型不同的分档）
	TEST_AR_ORRR        15, shl.o, rd5, 0x0000000000000000, rd6, 0x0000000021212121, rd7, 0x0000000000000001, 0x0000000042424242

	@@ [16] 迁移：同位型 << 7（跨 nibble 边界）
	@@   手算：0x21212121 << 7 = 0x1090909080（位 7/12·15/20·23/28·31/36；bit36 进高半）
	TEST_AR_ORRR        16, shl.o, rd5, 0x0000000000000000, rd6, 0x0000000021212121, rd7, 0x0000000000000007, 0x0000001090909080

	@@ [17] 迁移：同位型 << 31（位 0+31=31 … 29+31=60，跨 32 位边界）
	@@   手算：0x21212121 << 31 = 0x1090909080000000
	TEST_AR_ORRR        17, shl.o, rd5, 0x0000000000000000, rd6, 0x0000000021212121, rd7, 0x000000000000001F, 0x1090909080000000

	@@ [18] 迁移：移位量取 rdHD[5:0]（DADAO 掩码语义，非 ILLI）——0xFFFF..FFC7 的低 6 位 = 7
	@@   手算：0xFFFFFFFFFFFFFFC7 & 0x3F = 0x07 ⇒ 结果同 [16]（SimRISC-04 §2.2「shamt 位域 hd[5:0]」）
	TEST_AR_ORRR        18, shl.o, rd5, 0x0000000000000000, rd6, 0x0000000021212121, rd7, 0xFFFFFFFFFFFFFFC7, 0x0000001090909080

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3     19, shl.o, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
