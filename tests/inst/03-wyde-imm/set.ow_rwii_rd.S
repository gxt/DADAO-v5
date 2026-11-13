@@ set.ow_rwii_rd.S — set.ow rdHA, wpN, immu16（rwii, opc 0x4D）
@@ 大类：03-wyde-imm（16 位立即数操作，`spec/SimRISC-03 §1`）；册目录 `tests/inst/03-wyde-imm/`
@@ id：set.ow_rwii_rd　形式：rwii　opc：0x4D　mask：0xFF000000　value：0x4D000000　目的银行：RD
@@ 语义：rdHA 的 wyde(wpN) ← immu16，其余 48 位**置 1**（旧值整体丢弃；rb 无此变体）
@@ 合法性：目的 rdHA = rd0 ⇒ ILLI（`dst_rd0`，`spec/SimRISC-03 附录 B`）；无其它规则
@@ 立即数分片：wp0/wp1/wp2/wp3 = bits[15:0]/[31:16]/[47:32]/[63:48]（LSW..MSW，`spec/SimRISC-03 §1`）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 WDATA（`_MEM` 期望的来源）/ SCRATCH（rb/rf 实测落点）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：目的在 rd 直接比；在 rb/rf 用同组 `st.o` 落到 SCRATCH 再逐字节比 —— 不借被测指令；
@@   期望内联；`_MEM` 变体的期望从 WDATA 装载（不经任何 rwii 指令）⇒ 期望不由被测指令自证。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ dst=rd5/wp2/0x1234 的规范编码字
	@@ 规范编码字 0x4D161234（opc<<24 | rd5<<18 | wp2<<16 | 0x1234）
	__LI	rd5, 0x0000000000000000
	.dd.t32	0x4D161234
	__CHECK_RD           1, rd5, 0xFFFF1234FFFFFFFF
	@@ 最高寄存器 rd63 + wp3
	@@ 规范编码字 0x4DFF0001（opc<<24 | rd63<<18 | wp3<<16 | 0x0001）
	__LI	rd63, 0x0123456789ABCDEF
	.dd.t32	0x4DFF0001
	__CHECK_RD           2, rd63, 0x0001FFFFFFFFFFFF

	@@ ---- semantic ----
	@@ wp0（LSW）
	TEST_WI_RD           3, set.ow, rd10, wp0, 0x1234, 0x0000000000000000, 0xFFFFFFFFFFFF1234
	@@ wp1
	TEST_WI_RD           4, set.ow, rd11, wp1, 0x8000, 0x0000000000000000, 0xFFFFFFFF8000FFFF
	@@ wp2 全 1 ⇒ 64 位全 1
	TEST_WI_RD           5, set.ow, rd12, wp2, 0xFFFF, 0x0123456789ABCDEF, 0xFFFFFFFFFFFFFFFF
	@@ wp3（MSW）
	TEST_WI_RD           6, set.ow, rd13, wp3, 0xABCD, 0x0000000000000000, 0xABCDFFFFFFFFFFFF
	@@ wp2；期望取自 WDATA（独立 oracle）
	TEST_WI_RD_MEM       7, set.ow, rd14, wp2, 0x1234, 0x0000000000000000, 0x48

	@@ ---- boundary ----
	@@ immu16 全 1 ⇒ 64 位全 1
	TEST_WI_RD           8, set.ow, rd6, wp0, 0xFFFF, 0x0000000000000000, 0xFFFFFFFFFFFFFFFF
	@@ immu16=0 ⇒ 只清该 wyde
	TEST_WI_RD           9, set.ow, rd7, wp0, 0x0000, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFF0000
	@@ wp1 清 0 ⇒ 中间空 16 位
	TEST_WI_RD          10, set.ow, rd8, wp1, 0x0000, 0x0000000000000000, 0xFFFFFFFF0000FFFF
	@@ wp2 最高位
	TEST_WI_RD          11, set.ow, rd9, wp2, 0x8000, 0x0123456789ABCDEF, 0xFFFF8000FFFFFFFF
	@@ 符号位所在 wyde
	TEST_WI_RD          12, set.ow, rd15, wp3, 0x8000, 0x0123456789ABCDEF, 0x8000FFFFFFFFFFFF
	@@ 最大正 15 位立即数
	TEST_WI_RD          13, set.ow, rd17, wp0, 0x7FFF, 0x0000000000000000, 0xFFFFFFFFFFFF7FFF

	@@ ---- overlap ----
	@@ 目的=隐式源：旧值被整体丢弃
	TEST_WI_RD          14, set.ow, rd18, wp2, 0x1234, 0xA5A55A5A0F0FF0F0, 0xFFFF1234FFFFFFFF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器放行该编码）
	TEST_FAULT_WI       15, set.ow, rd0, ILLI, wp2, 0x0004

	__TEST_SECTIONS
