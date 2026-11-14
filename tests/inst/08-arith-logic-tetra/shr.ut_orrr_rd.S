@@ shr.ut_orrr_rd.S — shr.ut rdHB, rdHC, rdHD（orrr, opc 0x41／ha 0x12）
@@ 大类：08-arith-logic-tetra（32 位数据运算，`spec/SimRISC-08`）；册目录 `tests/inst/08-arith-logic-tetra/`
@@ id：shr.ut_orrr_rd　形式：orrr　opc：0x41／ha 0x12　mask：0xFFFC0000　value：0x41480000　目的银行：RD
@@ 语义：rdHB ← 零扩展(rdHC[31:0] >> shamt)（逻辑右移）；shamt = rdHD[4:0]（对 32 取模、不 ILLI），结果零扩展写满 64 位
@@ 合法性：目的 rdhb 为 rd0 ⇒ ILLI（`dst_rd0`）；源可为 rd0；orrr 的移位量天然取低 5 位
@@ 边界/覆盖：边界：shamt 0/1/31/32/全 1、结果零扩展（高位补 0 而非源高位）、源高位不参与
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orrr = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | rdhd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic+boundary+overlap 14 + 迁移 3（m13-testcases-045）（链例 19 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ [encoding 1] rd5 = rd6 >> 1（0x80000000 ⇒ 0x40000000）的规范编码字
	@@ 规范编码字 0x41485187（opc<<24 | ha<<18 | rd5<<12 | rd6<<6 | 7）
	__LI	rd6, 0x0000000080000000
	__LI	rd7, 0x0000000000000001
	.dd.t32	0x41485187
	__CHECK_RD   1, rd5, 0x0000000040000000

	@@ [encoding 2] 最高寄存器作目的（rd63）+ 1 >> 1 = 0
	@@ 规范编码字 0x414BF042（opc<<24 | ha<<18 | rd63<<12 | rd1<<6 | 2）
	__LI	rd1, 0x0000000000000001
	__LI	rd2, 0x0000000000000001
	.dd.t32	0x414BF042
	__CHECK_RD   2, rd63, 0x0000000000000000

	@@ [3] 0x80000000 >> 1 = 0x40000000（高位补 0）
	TEST_AR_ORRR        3, shr.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x0000000000000001, 0x0000000040000000

	@@ [4] 0xFFFFFFFF >> 1 = 0x7FFFFFFF，高 32 位为 0
	TEST_AR_ORRR        4, shr.ut, rd5, 0x0000000000000000, rd6, 0x00000000FFFFFFFF, rd7, 0x0000000000000001, 0x000000007FFFFFFF

	@@ [5] shamt 0 ⇒ 原值（只留低 32 位）
	TEST_AR_ORRR        5, shr.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, 0x00000000FFFFFFFF

	@@ [6] shamt 31：0x80000000 >> 31 = 1
	TEST_AR_ORRR        6, shr.ut, rd5, 0x0000000000000000, rd6, 0x0000000080000000, rd7, 0x000000000000001F, 0x0000000000000001

	@@ [7] 0x12345678 >> 8 = 0x00123456
	TEST_AR_ORRR        7, shr.ut, rd5, 0x0000000000000000, rd6, 0x0000000012345678, rd7, 0x0000000000000008, 0x0000000000123456

	@@ [8] shamt 32 ⇒ 取低 5 位 = 0 ⇒ 原值（不触发 ILLI）
	TEST_AR_ORRR        8, shr.ut, rd5, 0x0000000000000000, rd6, 0x000000000F0F0F0F, rd7, 0x0000000000000020, 0x000000000F0F0F0F

	@@ [9] shamt 全 1 ⇒ 31：0x7FFFFFFF >> 31 = 0
	TEST_AR_ORRR        9, shr.ut, rd5, 0x0000000000000000, rd6, 0x000000007FFFFFFF, rd7, 0x00000000FFFFFFFF, 0x0000000000000000

	@@ [10] 源的高 32 位不参与：0xFFFFFFFF_80000000 >> 1 = 0x40000000（不是 0xFFFFFFFFC0000000）
	TEST_AR_ORRR       10, shr.ut, rd5, 0x0000000000000000, rd6, 0xFFFFFFFF80000000, rd7, 0x0000000000000001, 0x0000000040000000

	@@ [11] rd0 作源：0 >> 5 = 0
	TEST_AR_ORRR       11, shr.ut, rd5, 0x0000000000000000, rd0, 0x0000000000000000, rd7, 0x0000000000000005, 0x0000000000000000

	@@ [12] 源=目（原地）：rd9 >> 8
	TEST_AR_ORRR       12, shr.ut, rd9, 0x0000000012345678, rd9, 0x0000000012345678, rd10, 0x0000000000000008, 0x0000000000123456

	@@ [13] 目=源D（原地）：rd9 旧值 3 是移位量
	TEST_AR_ORRR       13, shr.ut, rd9, 0x0000000000000003, rd10, 0x0000000080000000, rd9, 0x0000000000000003, 0x0000000010000000

	@@ [14] 两源同名：0x80000000 >> 31 = 1
	TEST_AR_ORRR       14, shr.ut, rd12, 0x0000000000000000, rd11, 0x0000000080000000, rd11, 0x0000000080000000, 0x0000000080000000

	@@ [15] （YAML boundary 并入）0x0F0F0F0F0F0F0F0F >> 31 = 0
	TEST_AR_ORRR       15, shr.ut, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x000000000000001F, 0x0000000000000000

	@@ [16] （YAML semantic 并入）0x0F0F0F0F… >> 2 = 0x03C3C3C3
	TEST_AR_ORRR       16, shr.ut, rd5, 0x0000000000000000, rd6, 0x0F0F0F0F0F0F0F0F, rd7, 0x0000000000000002, 0x0000000003C3C3C3

	@@ [17] 迁移（m13-testcases-045）：分散位型 0x21212121 >> 7（32 位逻辑右移、高半置 0）
	@@   手算：0x21212121>>7 = 0x00424242 ⇒ 0x0000000000424242（与 shr.st 同位型 19 的符号扩展结果对照）
	TEST_AR_ORRR       17, shr.ut, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000021212121, rd7, 0x0000000000000007, 0x0000000000424242

	@@ [18] 迁移：bit31 置位 + 低位 1 >> 31（逻辑 ⇒ 高半由零填充，不是全 1）
	@@   手算：0x80000001>>31 = 1（bit0 移出）⇒ 0x0000000000000001
	TEST_AR_ORRR       18, shr.ut, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF80000001, rd7, 0x000000000000001F, 0x0000000000000001

	@@ [19] 迁移：源高 32 位全 1、低字 bit31=0 >> 4（高半只看低字 ⇒ 全 0）
	@@   手算：0x12345678>>4 = 0x01234567 ⇒ 0x0000000001234567
	TEST_AR_ORRR       19, shr.ut, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF12345678, rd7, 0x0000000000000004, 0x0000000001234567

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ [17] dst_rd0：目的 rd0 ⇒ ILLI
	TEST_FAULT_ALU3       20, shr.ut, ILLI, rd0, rd6, rd7

	__TEST_SECTIONS
