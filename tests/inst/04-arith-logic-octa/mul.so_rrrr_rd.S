@@ mul.so_rrrr_rd.S — mul.so {rdHA, rdHB}, rdHC, rdHD（rrrr, opc 0x55）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：mul.so_rrrr_rd　形式：rrrr　opc：0x55　mask：0xFF000000　value：0x55000000　目的银行：RD
@@ 语义：{{rdHA, rdHB}} ← (rdHC × rdHD) 的有符号 128 位积；rdHA = 高 64 位，rdHB = 低 64 位
@@ 合法性：两个目的（rdHA/rdHB）不得同时为 rd0，也不得为同一非 rd0 寄存器 ⇒ ILLI（`dst_dual_same`）；
@@   其中一个为 rd0 合法（丢弃对应半结果）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrrr = opc | ha[23:18] | hb[17:12] | hc[11:6] | hd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/inst-tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 4 / overlap 3 + 迁移 3（m13-testcases-045）（链例 17 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ dst={rd5,rd6}/c=rd7/d=rd8 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x551461C8（opc<<24 | rd5<<18 | rd6<<12 | rd7<<6 | rd8）
	set.rd	rd5, 0x0000000000000000
	set.rd	rd6, 0x0000000000000000
	set.rd	rd7, 0x0000000000000064
	set.rd	rd8, 0x000000000000001E
	.dd.t32	0x551461C8
	__VERIFY_RD  1, rd5, 0x0000000000000000
	__CHECK_RD   1, rd6, 0x0000000000000BB8

	@@ 最高寄存器作高半 + rd0 源（读出 0）的编码字（字段边界）
	@@ 规范编码字 0x55FC1000（opc<<24 | rd63<<18 | rd1<<12 | rd0<<6 | rd0）
	set.rd	rd63, 0x0000000000000000
	set.rd	rd1, 0x0000000000000000
	.dd.t32	0x55FC1000
	__VERIFY_RD  2, rd63, 0x0000000000000000
	__CHECK_RD   2, rd1, 0x0000000000000000

	@@ (-1) * 1 = -1（高半全 1）
	TEST_AR_DUAL         3, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF

	@@ (-1) * (-1) = 1
	TEST_AR_DUAL         4, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000001

	@@ 乘 0 = 0
	TEST_AR_DUAL         5, mul.so, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000000

	@@ 高半丢弃：{rd0, rdN} 只留低半
	TEST_AR_DUAL         6, mul.so, rd0, rd9, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000001

	@@ 低半丢弃：{rdN, rd0} 只留高半
	TEST_AR_DUAL         7, mul.so, rd9, rd0, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x8000000000000000

	@@ INT64_MIN * (-1) = 2^63（高半 0）
	TEST_AR_DUAL         8, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x8000000000000000

	@@ min * min = 2^126（高半 0x4000..0、低半 0）
	TEST_AR_DUAL         9, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x8000000000000000, 0x4000000000000000, 0x0000000000000000

	@@ max * max = 2^126-2^64+1
	TEST_AR_DUAL        10, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x7FFFFFFFFFFFFFFF, rd8, 0x7FFFFFFFFFFFFFFF, 0x3FFFFFFFFFFFFFFF, 0x0000000000000001

	@@ max * (-1) = -max
	TEST_AR_DUAL        11, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x7FFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0x8000000000000001

	@@ 高半=源C（原地）
	TEST_AR_DUAL        12, mul.so, rd10, rd11, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, rd10, 0xFFFFFFFFFFFFFFFF, rd12, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000001

	@@ 低半=源D（原地）
	TEST_AR_DUAL        13, mul.so, rd10, rd11, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF, rd12, 0x0000000000000003, rd11, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFD

	@@ 两源同名：x * x
	TEST_AR_DUAL        14, mul.so, rd10, rd11, 0x0000000000000000, 0x0000000000000000, rd13, 0xFFFFFFFFFFFFFFFF, rd13, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000001

	@@ [15] 迁移（m13-testcases-045）：乘数位型压力 —— 0xAAAA..AB（负、奇）× 0x2FE7D（小乘数）
	@@   手算：a = −((2^64−1)/3) = −0x5555555555555555；b = 0x2FE7D = 3 × 0xFF7F
	@@   ⇒ |积| = 0xFF7F × (2^64−1) = 0xFF7E_FFFFFFFFFFFF0081（80 位，正）
	@@   取 128 位补码 ⇒ 积 = 0xFFFFFFFFFFFF0081_000000000000FF7F（高半全 1 段 + 0x0081）
	@@   低半 = 模 2^64 的积（与 ISA 无关，恰与上游 mul 的 expected 同值）；高半符号规则 = SimRISC-04 §1.4
	TEST_AR_DUAL        15, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xAAAAAAAAAAAAAAAB, rd8, 0x000000000002FE7D, 0xFFFFFFFFFFFF0081, 0x000000000000FF7F

	@@ [16] 迁移：小乘数 0x7E00（低位聚簇）× 0x6DB6DB6DB6DB6DB7（bit 周期 3 的密集位型）
	@@   手算：32256 × 7905747460161236407 = 255007790074960841544192
	@@   = 0x3600 × 2^64 + 0x1200 ⇒ 高半 0x3600、低半 0x1200（正积，无符号/有符号同解）
	TEST_AR_DUAL        16, mul.so, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000007E00, rd8, 0x6DB6DB6DB6DB6DB7, 0x0000000000003600, 0x0000000000001200

	@@ [17] 迁移：小乘数 0x7FC0（比 0x7E00 多 bit6）× 同一位型
	@@   手算：32704 × 7905747460161236407 = 258549564937113075454528
	@@   = 0x36C0 × 2^64 + 0x1240 ⇒ 高半 0x36C0、低半 0x1240（与 [16] 只差 bit6/位型对齐）
	TEST_AR_DUAL        17, mul.so, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x0000000000007FC0, rd8, 0x6DB6DB6DB6DB6DB7, 0x00000000000036C0, 0x0000000000001240

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_dual_same：两个目的同为 rd0
	TEST_FAULT_DUAL     18, mul.so, ILLI, rd0, rd0, rd7, rd8

	@@ dst_dual_same：两个目的为同一非 rd0 寄存器
	TEST_FAULT_DUAL     19, mul.so, ILLI, rd5, rd5, rd7, rd8

	__TEST_SECTIONS
