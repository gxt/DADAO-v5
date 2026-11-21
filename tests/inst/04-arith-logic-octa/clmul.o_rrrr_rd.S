@@ clmul.o_rrrr_rd.S — clmul.o {rdHA, rdHB}, rdHC, rdHD（rrrr, opc 0x56）
@@ 大类：04-arith-logic-octa（64 位数据运算，`spec/SimRISC-04 §1.5`）；册目录 `tests/inst/04-arith-logic-octa/`
@@ id：clmul.o_rrrr_rd　形式：rrrr　opc：0x56　mask：0xFF000000　value：0x56000000　目的银行：RD
@@ 语义：{rdHA, rdHB} ← rdHC ⊗ rdHD（GF(2) 多项式无进位乘，128 位：rdHA 高 / rdHB 低）；
@@   位间只有「与」和「异或」、无进位（与整数 mul.uo 不同，如 0b11 ⊗ 0b11 = 0b101）
@@ 合法性：两个目的（rdHA/rdHB）不得同时为 rd0，也不得为同一非 rd0 寄存器 ⇒ ILLI（`dst_dual_same`）；
@@   其中一个为 rd0 合法（丢弃对应半结果）；源被覆盖前已捕获（先读源后写目的）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrrr = opc | ha[23:18] | hb[17:12] | hc[11:6] | hd[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 9 / overlap 2（链例 19 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联；
@@   双目的用例高半 `__VERIFY_RD` + 低半 `__CHECK_RD`（两条断言共用点号）。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"

	__TEST_BEGIN

	@@ {rd1,rd2} = clmul.o(rd3, rd4) 的规范编码字直接执行（钉 mask/value；输入取 x ⊗ x）
	@@ 规范编码字 0x560420C4（opc<<24 | rd1<<18 | rd2<<12 | rd3<<6 | rd4）
	set.rd	rd1, 0xAAAAAAAAAAAAAAAA
	set.rd	rd2, 0xAAAAAAAAAAAAAAAA
	set.rd	rd3, 0x0123456789ABCDEF
	set.rd	rd4, 0x0123456789ABCDEF
	.dd.t32	0x560420C4
	__VERIFY_RD  1, rd1, 0x0001040510111415
	__CHECK_RD   1, rd2, 0x4041444550515455

	@@ 最高寄存器作高半 + rd0 作低半（丢弃低半）的编码字（字段边界）
	@@ 规范编码字 0x56FC0042（opc<<24 | rd63<<18 | rd0<<12 | rd1<<6 | rd2）
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0xFFFFFFFFFFFFFFFF
	set.rd	rd2, 0x0123456789ABCDEF
	.dd.t32	0x56FC0042
	__CHECK_RD   2, rd63, 0x00E13CDD789944A5

	@@ 0 ⊗ 0 = 0（目的初值全 1 也被覆盖）
	TEST_AR_DUAL         3, clmul.o, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, rd8, 0x0000000000000000, 0x0000000000000000, 0x0000000000000000

	@@ 1 ⊗ x = x（高半 0、低半原值）
	TEST_AR_DUAL         4, clmul.o, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000001, rd8, 0xA5C396F1DEADBEEF, 0x0000000000000000, 0xA5C396F1DEADBEEF

	@@ 2^63 ⊗ 2^63 = x^126 ⇒ 高半 2^62、低半 0（无进位；整数乘的进位形态不同）
	TEST_AR_DUAL         5, clmul.o, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x8000000000000000, 0x4000000000000000, 0x0000000000000000

	@@ 满宽随机 1（YAML semantic）
	TEST_AR_DUAL         6, clmul.o, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xE0C2EB3BF5679582, rd8, 0x6A11AF6271A240DF, 0x22E1F032C3C94BEC, 0x5C9E0CB300783D3E

	@@ 满宽随机 2（YAML semantic）
	TEST_AR_DUAL         7, clmul.o, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x54076FAF1FE0B2F5, rd8, 0xCC8977404FEDF8CA, 0x3CDAA60C0ADA7122, 0xD8AE9BE9F179AD82

	@@ 两源同名：x ⊗ x（GF(2) 平方，无交叉项进位）
	TEST_AR_DUAL         8, clmul.o, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x0123456789ABCDEF, rd8, 0x0123456789ABCDEF, 0x0001040510111415, 0x4041444550515455

	@@ 0 ⊗ 全 1 = 0（零元）
	TEST_AR_DUAL         9, clmul.o, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000000, rd8, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0x0000000000000000

	@@ 1 ⊗ 2^63 = 2^63（单位元 × 最高位）
	TEST_AR_DUAL        10, clmul.o, rd5, rd6, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, rd7, 0x0000000000000001, rd8, 0x8000000000000000, 0x0000000000000000, 0x8000000000000000

	@@ 全 1 ⊗ 全 1：高半 = 低半 = 0x5555…（交错位）
	TEST_AR_DUAL        11, clmul.o, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0xFFFFFFFFFFFFFFFF, 0x5555555555555555, 0x5555555555555555

	@@ 2^63 ⊗ 全 1：高半 0x7FFF…、低半 0x8000…
	TEST_AR_DUAL        12, clmul.o, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000

	@@ 全 1 ⊗ 0x0123456789ABCDEF（高低半同值）
	TEST_AR_DUAL        13, clmul.o, rd5, rd6, 0x0000000000000000, 0x0000000000000000, rd7, 0xFFFFFFFFFFFFFFFF, rd8, 0x0123456789ABCDEF, 0x00E13CDD789944A5, 0x00E13CDD789944A5

	@@ 高半丢弃：{rd0, rdN} 只留低半
	TEST_AR_DUAL        14, clmul.o, rd0, rd9, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF, rd7, 0x0123456789ABCDEF, rd8, 0xFEDCBA9876543210, 0x00E038D8688850B0, 0x40A0789828C810F0

	@@ 高半丢弃：{rd0, rdN} 只留低半（2^63 ⊗ 3 低半仍为 2^63）
	TEST_AR_DUAL        15, clmul.o, rd0, rd9, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x0000000000000003, 0x0000000000000001, 0x8000000000000000

	@@ 低半丢弃：{rdN, rd0} 只留高半
	TEST_AR_DUAL        16, clmul.o, rd9, rd0, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000, rd7, 0x0123456789ABCDEF, rd8, 0xFEDCBA9876543210, 0x00E038D8688850B0, 0x40A0789828C810F0

	@@ 低半丢弃：{rdN, rd0} 只留高半（2^63 ⊗ 3 高半为 1）
	TEST_AR_DUAL        17, clmul.o, rd9, rd0, 0x0000000000000000, 0x0000000000000000, rd7, 0x8000000000000000, rd8, 0x0000000000000003, 0x0000000000000001, 0x8000000000000000

	@@ 高半=源 C（原地）：源先读后写 ⇒ 结果按原 rd1 值参与
	TEST_AR_DUAL        18, clmul.o, rd1, rd2, 0x0123456789ABCDEF, 0xAAAAAAAAAAAAAAAA, rd1, 0x0123456789ABCDEF, rd4, 0xFEDCBA9876543210, 0x00E038D8688850B0, 0x40A0789828C810F0

	@@ 低半=源 D（原地）：源先读后写 ⇒ 结果按原 rd2 值参与
	TEST_AR_DUAL        19, clmul.o, rd1, rd2, 0xAAAAAAAAAAAAAAAA, 0xFEDCBA9876543210, rd3, 0x0123456789ABCDEF, rd2, 0xFEDCBA9876543210, 0x00E038D8688850B0, 0x40A0789828C810F0

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ dst_dual_same：两个目的同为 rd0（汇编器拒绝该助记符形式 ⇒ 用原始编码字）
	TEST_FAULT_ENC      20, ILLI, 0x560000C4, rb3, TEST_DATA, rd7, 0x000

	@@ dst_dual_same：两个目的为同一非 rd0 寄存器（同上，原始编码字）
	TEST_FAULT_ENC      21, ILLI, 0x561450C4, rb3, TEST_DATA, rd7, 0x000

	__TEST_SECTIONS
