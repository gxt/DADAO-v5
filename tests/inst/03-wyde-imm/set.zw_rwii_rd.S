@@ set.zw_rwii_rd.S — set.zw rdHA, wpN, immu16（rwii, opc 0x4C）
@@ 大类：03-wyde-imm（16 位立即数操作，`spec/SimRISC-03 §1`）；册目录 `tests/inst/03-wyde-imm/`
@@ id：set.zw_rwii_rd　形式：rwii　opc：0x4C　mask：0xFF000000　value：0x4C000000　目的银行：RD
@@ 语义：rdHA 的 wyde(wpN) ← immu16，其余 48 位**清 0**（旧值整体丢弃）
@@ 合法性：目的 rdHA = rd0 ⇒ ILLI（`dst_rd0`，`spec/SimRISC-03 附录 B`）；无其它规则
@@ 立即数分片：wp0/wp1/wp2/wp3 = bits[15:0]/[31:16]/[47:32]/[63:48]（LSW..MSW，`spec/SimRISC-03 §1`）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 WDATA（`_MEM` 期望的来源）/ SCRATCH（rb/rf 实测落点）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：目的在 rd 直接比；在 rb/rf 用同组 `st.o` 落到 SCRATCH 再逐字节比 —— 不借被测指令；
@@   期望内联；`_MEM` 变体的期望从 WDATA 装载（不经任何 rwii 指令）⇒ 期望不由被测指令自证。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/03-wyde-imm/03-wyde-imm.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ dst=rd5/wp2/0xABCD 的规范编码字直接执行（钉 mask/value）
	@@ 规范编码字 0x4C16ABCD（opc<<24 | rd5<<18 | wp2<<16 | 0xABCD）
	set.rd	rd5, 0x0123456789ABCDEF
	.dd.t32	0x4C16ABCD
	__CHECK_RD           1, rd5, 0x0000ABCD00000000
	@@ 最高寄存器 rd63 + wp3（字段边界）
	@@ 规范编码字 0x4CFF0001（opc<<24 | rd63<<18 | wp3<<16 | 0x0001）
	set.rd	rd63, 0x0000000000000000
	.dd.t32	0x4CFF0001
	__CHECK_RD           2, rd63, 0x0001000000000000

	@@ ---- semantic ----
	@@ wp0（LSW）：旧值整体丢弃
	TEST_WI_RD           3, set.zw, rd10, wp0, 0x1234, 0xFFFFFFFFFFFFFFFF, 0x0000000000001234
	@@ wp1
	TEST_WI_RD           4, set.zw, rd11, wp1, 0x8000, 0x0123456789ABCDEF, 0x0000000080000000
	@@ wp2
	TEST_WI_RD           5, set.zw, rd12, wp2, 0xFFFF, 0xA5A55A5A0F0FF0F0, 0x0000FFFF00000000
	@@ wp3（MSW）
	TEST_WI_RD           6, set.zw, rd13, wp3, 0x7FFF, 0xDEADBEEFCAFEF00D, 0x7FFF000000000000
	@@ wp2；期望取自 WDATA（独立 oracle）
	TEST_WI_RD_MEM       7, set.zw, rd14, wp2, 0xABCD, 0x0123456789ABCDEF, 0x40

	@@ ---- boundary ----
	@@ immu16=0 ⇒ 全清
	TEST_WI_RD           8, set.zw, rd6, wp0, 0x0000, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000
	@@ wp3 全 1
	TEST_WI_RD           9, set.zw, rd7, wp3, 0xFFFF, 0x0123456789ABCDEF, 0xFFFF000000000000
	@@ 位 31 单置（旧值不影响）
	TEST_WI_RD          10, set.zw, rd8, wp1, 0x8000, 0xFFFFFFFFFFFFFFFF, 0x0000000080000000
	@@ wp0 全 1
	TEST_WI_RD          11, set.zw, rd9, wp0, 0xFFFF, 0xDEADBEEFCAFEF00D, 0x000000000000FFFF
	@@ 最小非零立即数
	TEST_WI_RD          12, set.zw, rd15, wp0, 0x0001, 0x0000000000000000, 0x0000000000000001
	@@ 最高位单置
	TEST_WI_RD          13, set.zw, rd17, wp3, 0x8000, 0x0000000000000000, 0x8000000000000000

	@@ ---- overlap ----
	@@ 目的=隐式源：旧值被整体丢弃
	TEST_WI_RD          14, set.zw, rd18, wp2, 0x5A5A, 0xA5A55A5A0F0FF0F0, 0x00005A5A00000000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器放行该编码）
	TEST_FAULT_WI       15, set.zw, rd0, ILLI, wp0, 0x0001

	__TEST_SECTIONS
