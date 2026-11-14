@@ mul.uo_rrrr_rd.S — mul.uo {rdHA, rdHB}, rdHC, rdHD（rrrr, opc 0x54）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：mul.uo_rrrr_rd　形式：rrrr　opc：0x54　mask：0xFF000000　value：0x54000000　目的银行：RD
@@ 语义：{{rdHA, rdHB}} ← (rdHC × rdHD) 的无符号 128 位积；rdHA = 高 64 位，rdHB = 低 64 位
@@ 合法性：两个目的（rdHA/rdHB）不得同时为 rd0，也不得为同一非 rd0 寄存器 ⇒ ILLI（`dst_dual_same`）；
@@   其中一个为 rd0 合法（丢弃对应半结果）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrrr = opc | ha[23:18] | hb[17:12] | hc[11:6] | hd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3 + 迁移 2（m13-testcases-045）（链例 16 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `__LI`（set.zw/or.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ dst={rd5,rd6}/c=rd7/d=rd8 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x541461C8（opc<<24 | rd5<<18 | rd6<<12 | rd7<<6 | rd8）
	__LI	rd5, 0x0000000000000000
	__LI	rd6, 0x0000000000000000
	__LI	rd7, 0x0000000000000064
	__LI	rd8, 0x000000000000001E
	.dd.t32	0x541461C8
	__VERIFY_RD  1, rd5, 0x0000000000000000
	__CHECK_RD   1, rd6, 0x0000000000000BB8

	@@ 最高寄存器作高半 + rd0 源（读出 0）的编码字（字段边界）
	@@ 规范编码字 0x54FC1000（opc<<24 | rd63<<18 | rd1<<12 | rd0<<6 | rd0）
	__LI	rd63, 0x0000000000000000
	__LI	rd1, 0x0000000000000000
	.dd.t32	0x54FC1000
	__VERIFY_RD  2, rd63, 0x0000000000000000
	__CHECK_RD   2, rd1, 0x0000000000000000

	@@ 100 * 30 = 3000（高半 0）
	TEST_AR_DUAL         3, mul.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x0000000000000064, rd8, 0x000000000000001E, 0x0000000000000000, 0x0000000000000BB8

	@@ 乘 0 = 0（目的初值被覆盖）
	TEST_AR_DUAL         4, mul.uo, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000000

	@@ 乘 1 = 原值
	TEST_AR_DUAL         5, mul.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x0123456789ABCDEF, rd8, 0x0000000000000001, 0x0000000000000000, 0x0123456789ABCDEF

	@@ 高半丢弃：{rd0, rdN} 只留低半
	TEST_AR_DUAL         6, mul.uo, rd0, rd9, 0x0000000000000000, 0x0000000000000000, rd7, 0xFEDCBA9876543210, rd8, 0x0123456789ABCDEF, 0x0121FA00AD77D742, 0x2236D88FE5618CF0

	@@ 低半丢弃：{rdN, rd0} 只留高半
	TEST_AR_DUAL         7, mul.uo, rd9, rd0, 0x0000000000000000, 0x0000000000000000, rd7, 0xFEDCBA9876543210, rd8, 0x0123456789ABCDEF, 0x0121FA00AD77D742, 0x2236D88FE5618CF0

	@@ max * max：高半 …FE、低半 1
	TEST_AR_DUAL         8, mul.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFE, 0x0000000000000001

	@@ 2^63 * 2 = 2^65：高半 1、低半 0
	TEST_AR_DUAL         9, mul.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x0000000000000002, 0x0000000000000001, 0x0000000000000000

	@@ max * 2 = 2^65-2：高半 1、低半 …FE
	TEST_AR_DUAL        10, mul.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0000000000000002, 0x0000000000000001, 0xFFFFFFFFFFFFFFFE

	@@ 两个 64 位满宽因数（高低半都非零）
	TEST_AR_DUAL        11, mul.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFEDCBA9876543210, rd8, 0x0123456789ABCDEF, 0x0121FA00AD77D742, 0x2236D88FE5618CF0

	@@ 高半=源C（原地）
	TEST_AR_DUAL        12, mul.uo, rd10, rd11, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, rd10, 0xFFFFFFFFFFFFFFFF, rd12, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFE, 0x0000000000000001

	@@ 低半=源D（原地）
	TEST_AR_DUAL        13, mul.uo, rd10, rd11, 0x0000000000000000, 0x0000000000000003, rd12, 0x0000000000000005, rd11, 0x0000000000000003, 0x0000000000000000, 0x000000000000000F

	@@ 两源同名：x * x
	TEST_AR_DUAL        14, mul.uo, rd10, rd11, 0x0000000000000000, 0x0000000000000000, rd13, 0x0123456789ABCDEF, rd13, 0x0123456789ABCDEF, 0x00014B66DC33F6AC, 0xDCA5E20890F2A521

	@@ [15] 迁移（m13-testcases-045）：与 mul.so [15] **同一对操作数**的无符号对照
	@@   手算：0xAAAAAAAAAAAAAAAB = 2^64 − (2^64−1)/3，0x2FE7D = 3 × 0xFF7F
	@@   ⇒ 积 = 0xFF7F × (3·2^64 − (2^64−1)) = 0xFF7F × (2·2^64 + 1) = 0x1FEFE·2^64 + 0xFF7F
	@@   高半 0x000000000001FEFE、低半 0x000000000000FF7F（对比 mul.so 同操作数高半 0xFFFF..0081 ⇒ 判别 .u/.s）
	TEST_AR_DUAL        15, mul.uo, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xAAAAAAAAAAAAAAAB, rd8, 0x000000000002FE7D, 0x000000000001FEFE, 0x000000000000FF7F

	@@ [16] 迁移：两个 bit63 均置位的满宽度无符号积（高半自身也是满位型）
	@@   手算：12297829382473034411 × 7905747460161236407 = 97223533405982418136784826902817001277
	@@   = 0x4924924924924924_CF3CF3CF3CF3CF3D（period-4 交替位型 ⇒ 部分积/进位链全链翻转）
	TEST_AR_DUAL        16, mul.uo, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0xAAAAAAAAAAAAAAAB, rd8, 0x6DB6DB6DB6DB6DB7, 0x4924924924924924, 0xCF3CF3CF3CF3CF3D

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_dual_same：两个目的同为 rd0
	TEST_FAULT_DUAL     17, mul.uo, ILLI, rd0, rd0, rd7, rd8

	@@ dst_dual_same：两个目的为同一非 rd0 寄存器
	TEST_FAULT_DUAL     18, mul.uo, ILLI, rd5, rd5, rd7, rd8

	__TEST_SECTIONS
