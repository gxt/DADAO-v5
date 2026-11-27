@@ ctpop_orri_rd.S — ctpop rdHB, rdHC, immu6（orri, opc 0x47／ha 0x25）
@@ 大类：12-misc（其它指令 · 位扫描与位计数 `spec/SimRISC-12 §3`）；册目录 `tests/inst/12-misc/`
@@ id：ctpop_orri_rd　形式：orri　opc：0x47／ha 0x25　mask：0xFFFC0000　value：0x47940000　目的银行：RD
@@ 语义：统计有效位 `rdHC[hd:0]`（hd = immu6 = 有效位上界，0..63）内 1 的个数；
@@   `rdHC[63:hd+1]` 不参与运算；结果 ∈ 0..64 **写满 64 位**（高位置 0，值语义）
@@ 定值：`rdHC[hd:0]` 全 0 ⇒ 结果 0（自然值，无特例）
@@ 合法性：`hd` 全部合法（0..63 无非法值，不新增规则）；`dst_rd0`——目的 rdhb 为 rd0 ⇒ ILLI；
@@   源 rdhc 可为 rd0（读出 0 ⇒ 0）；rdhb == rdhc（原地运算）允许
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 9 / legality 1（链例）/ overlap 1（链例 18）+ 故障例 1（dst_rd0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联；
@@   目的初值一律置全 1 ⇒ 若实现只写低位 / 不清高位，断言必红（fail-closed）
@@ 期望来自 spec/SimRISC-12 §3 + contracts/opcodes.yaml + legality_rules.yaml::dst_rd0（不从实现反推）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/12-misc/12-misc.inc"

	__TEST_BEGIN

	@@ ---- encoding：规范编码字直接执行（rd5 ← ctpop rd6, hd=7；编码 0x47945187） ----
	@@! inputs: kind=enc word=0x47945187 dst=rd5 src=rd6 v=0xAA hd=7
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x00000000000000AA
	.dd.t32	0x47945187
	__CHECK_RD	1, rd5, 0x0000000000000004

	@@ ---- encoding：字段边界（rd63 作目的 + rd1 作源 + hd=63；编码 0x4797F07F）----
	@@! inputs: kind=enc word=0x4797F07F dst=rd63 src=rd1 v=0x1 hd=63
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x0000000000000001
	.dd.t32	0x4797F07F
	__CHECK_RD	2, rd63, 0x0000000000000001

	@@ ---- semantic：全宽 64 位，全 1 ⇒ 64 ----
	TEST_AR_ORRI	3, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFFFFFFFFFF, 63, 0x0000000000000040

	@@ ---- semantic：宽 32（hd=31），高半全 1 在有效位之外 ⇒ 0 ----
	TEST_AR_ORRI	4, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFF00000000, 31, 0x0000000000000000

	@@ ---- semantic：全宽 64，逐字节互不相同的值 ⇒ 32 ----
	TEST_AR_ORRI	5, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0123456789ABCDEF, 63, 0x0000000000000020

	@@ ---- semantic：宽 32，0x0F0F0F0F ⇒ 16 ----
	TEST_AR_ORRI	6, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000F0F0F0F, 31, 0x0000000000000010

	@@ ---- semantic：宽 16（hd=15），0x0F0F ⇒ 8 ----
	TEST_AR_ORRI	7, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000F0F, 15, 0x0000000000000008

	@@ ---- semantic：宽 8（hd=7），0xF0 ⇒ 4 ----
	TEST_AR_ORRI	8, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000F0, 7, 0x0000000000000004

	@@ ---- boundary：hd=7，0xFF00 的 [15:8] 在有效位之外 ⇒ 0 ----
	TEST_AR_ORRI	9, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000000FF00, 7, 0x0000000000000000

	@@ ---- boundary：全 0 + hd=63 ⇒ 0 ----
	TEST_AR_ORRI	10, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 63, 0x0000000000000000

	@@ ---- boundary：hd=0（宽 1 位），bit0=0 ⇒ 0 ----
	TEST_AR_ORRI	11, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 0, 0x0000000000000000

	@@ ---- boundary：hd=0（宽 1 位），bit0=1 ⇒ 1 ----
	TEST_AR_ORRI	12, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, 0, 0x0000000000000001

	@@ ---- boundary：hd=62，仅 bit63=1 在有效位之外 ⇒ 0 ----
	TEST_AR_ORRI	13, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, 62, 0x0000000000000000

	@@ ---- boundary：hd=63，仅 bit63=1 ⇒ 1 ----
	TEST_AR_ORRI	14, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, 63, 0x0000000000000001

	@@ ---- boundary：交替位 0x5555.. ⇒ 32 ----
	TEST_AR_ORRI	15, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x5555555555555555, 63, 0x0000000000000020

	@@ ---- boundary：高位清零（目的初值全 1，结果 8 写满 64 位）----
	TEST_AR_ORRI	16, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, 7, 0x0000000000000008

	@@ ---- legality：源 rdhc=rd0（读出 0）合法 ⇒ 0；不得触发 ILLI ----
	TEST_AR_ORRI	17, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 63, 0x0000000000000000

	@@ ---- overlap：目的 = 源（原地运算，允许）----
	TEST_AR_ORRI	18, ctpop, rd9, 0xFFFFFFFFFFFFFFFF, rd9, 0xFFFFFFFFFFFFFFFF, 63, 0x0000000000000040

	@@ ---- boundary：one-hot 2^32 + hd=63 ⇒ 1 ----
	TEST_AR_ORRI	19, ctpop, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000100000000, 63, 0x0000000000000001

	__TEST_END

	@@ ---- fault（同镜像故障链）----
	@@ fault 20：目的 rdhb = rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_ALU_ORRI	20, ctpop, ILLI, rd0, rd6, 7

	__TEST_SECTIONS
