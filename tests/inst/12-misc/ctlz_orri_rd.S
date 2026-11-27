@@ ctlz_orri_rd.S — ctlz rdHB, rdHC, immu6（orri, opc 0x47／ha 0x26）
@@ 大类：12-misc（其它指令 · 位扫描与位计数 `spec/SimRISC-12 §3`）；册目录 `tests/inst/12-misc/`
@@ id：ctlz_orri_rd　形式：orri　opc：0x47／ha 0x26　mask：0xFFFC0000　value：0x47980000　目的银行：RD
@@ 语义：在有效位 `rdHC[hd:0]`（hd = immu6 = 有效位上界，0..63）内，从 bit hd **向下**数前导零；
@@   `rdHC[63:hd+1]` 不参与运算；结果 ∈ 0..64 **写满 64 位**（高位置 0，值语义）
@@ 定值：`rdHC[hd:0]` 全 0 ⇒ 结果 = hd+1（规范消除 UB，不是未定义值）
@@ 合法性：`hd` 全部合法（0..63 无非法值，不新增规则）；`dst_rd0`——目的 rdhb 为 rd0 ⇒ ILLI；
@@   源 rdhc 可为 rd0（读出 0 ⇒ hd+1）；rdhb == rdhc（原地运算）允许
@@ 编码：字段位域见 `contracts/opcodes.yaml`：orri = opc | ha[23:18] | rdhb[17:12] | rdhc[11:6] | immu6[5:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd` 拼初值；本册无需内存期望表）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 6 / boundary 10 / legality 1（链例）/ overlap 1（链例 18）+ 故障例 1（dst_rd0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w 拼常量，被测指令不参与造初值）、期望内联；
@@   目的初值一律置全 1 ⇒ 若实现只写低位 / 不清高位，断言必红（fail-closed）
@@ 期望来自 spec/SimRISC-12 §3 + contracts/opcodes.yaml + legality_rules.yaml::dst_rd0（不从实现反推）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/12-misc/12-misc.inc"

	__TEST_BEGIN

	@@ ---- encoding：规范编码字直接执行（rd5 ← ctlz rd6, hd=7；编码 0x47985187） ----
	@@! inputs: kind=enc word=0x47985187 dst=rd5 src=rd6 v=0x40 hd=7
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, 0x0000000000000040
	.dd.t32	0x47985187
	__CHECK_RD	1, rd5, 0x0000000000000001

	@@ ---- encoding：字段边界（rd63 作目的 + rd1 作源 + hd=63；编码 0x479BF07F）----
	@@! inputs: kind=enc word=0x479BF07F dst=rd63 src=rd1 v=0x1 hd=63
	set.rd	rd63, 0xFFFFFFFFFFFFFFFF
	set.rd	rd1, 0x0000000000000001
	.dd.t32	0x479BF07F
	__CHECK_RD	2, rd63, 0x000000000000003F

	@@ ---- semantic：全宽 64 位，最高位为 1 ⇒ 0 个前导零 ----
	TEST_AR_ORRI	3, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x8000000000000000, 63, 0x0000000000000000

	@@ ---- semantic：宽 32（hd=31），bit31 为 1 ⇒ 0 ----
	TEST_AR_ORRI	4, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000080000000, 31, 0x0000000000000000

	@@ ---- semantic：宽 64，首个 1 在 bit60 ⇒ 3 ----
	TEST_AR_ORRI	5, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x1F00000000000000, 63, 0x0000000000000003

	@@ ---- semantic：宽 32，逐 nibble 值 0x0F0F0F0F ⇒ 4 ----
	TEST_AR_ORRI	6, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x000000000F0F0F0F, 31, 0x0000000000000004

	@@ ---- semantic：宽 16（hd=15），0x00FF ⇒ bit15..8 全 0、bit7=1 ⇒ 8 ----
	TEST_AR_ORRI	7, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x00000000000000FF, 15, 0x0000000000000008

	@@ ---- semantic：宽 8（hd=7），0x80 ⇒ bit7=1 ⇒ 0 ----
	TEST_AR_ORRI	8, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000080, 7, 0x0000000000000000

	@@ ---- boundary：hd=31，0x100000000 的 bit32 在有效位之外 ⇒ 定值 hd+1 = 32 ----
	TEST_AR_ORRI	9, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000100000000, 31, 0x0000000000000020

	@@ ---- boundary：hd=7，0x8000 的 bit15 在有效位之外 ⇒ 定值 8（按全 64 位会得 16）----
	TEST_AR_ORRI	10, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000008000, 7, 0x0000000000000008

	@@ ---- boundary：全 0 + hd=63 ⇒ 定值上界 64（规范明示，非 UB）----
	TEST_AR_ORRI	11, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 63, 0x0000000000000040

	@@ ---- boundary：全 1 + hd=63 ⇒ 0 ----
	TEST_AR_ORRI	12, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0xFFFFFFFFFFFFFFFF, 63, 0x0000000000000000

	@@ ---- boundary：hd=0（宽 1 位），bit0=0 ⇒ 定值 1 ----
	TEST_AR_ORRI	13, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000000, 0, 0x0000000000000001

	@@ ---- boundary：hd=0（宽 1 位），bit0=1 ⇒ 0 ----
	TEST_AR_ORRI	14, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, 0, 0x0000000000000000

	@@ ---- boundary：hd=62，bit61=1 ⇒ 1（bit62 为 0，bit63 不看）----
	TEST_AR_ORRI	15, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x2000000000000000, 62, 0x0000000000000001

	@@ ---- boundary：高位清零（目的初值全 1，结果 28 写满 64 位）----
	TEST_AR_ORRI	16, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000F00000000, 63, 0x000000000000001C

	@@ ---- legality：源 rdhc=rd0（读出 0）合法 ⇒ 定值 hd+1 = 32；不得触发 ILLI ----
	TEST_AR_ORRI	17, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd0, 0x0000000000000000, 31, 0x0000000000000020

	@@ ---- legality/overlap：rdhb=rd0 作目的 ⇒ 故障例 19（见文件尾）----

	@@ ---- overlap：目的 = 源（原地运算，允许）----
	TEST_AR_ORRI	18, ctlz, rd9, 0x00000000000007FF, rd9, 0x00000000000007FF, 11, 0x0000000000000001

	@@ ---- boundary：one-hot 2^0（最低位）+ hd=63 ⇒ 63（定值公式 63−k）----
	TEST_AR_ORRI	19, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x0000000000000001, 63, 0x000000000000003F

	@@ ---- boundary：one-hot 2^62 + hd=63 ⇒ 1 ----
	TEST_AR_ORRI	20, ctlz, rd5, 0xFFFFFFFFFFFFFFFF, rd6, 0x4000000000000000, 63, 0x0000000000000001

	__TEST_END

	@@ ---- fault（同镜像故障链）----
	@@ fault 21：目的 rdhb = rd0 ⇒ ILLI（dst_rd0）
	TEST_FAULT_ALU_ORRI	21, ctlz, ILLI, rd0, rd6, 7

	__TEST_SECTIONS
