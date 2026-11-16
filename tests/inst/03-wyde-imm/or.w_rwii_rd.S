@@ or.w_rwii_rd.S — or.w rdHA, wpN, immu16（rwii, opc 0x48）
@@ 大类：03-wyde-imm（16 位立即数操作，`spec/SimRISC-03 §1`）；册目录 `tests/inst/03-wyde-imm/`
@@ id：or.w_rwii_rd　形式：rwii　opc：0x48　mask：0xFF000000　value：0x48000000　目的银行：RD
@@ 语义：rdHA 的 wyde(wpN) ← (旧值 | immu16)，其余 3 个 wyde 保持不变
@@ 合法性：目的 rdHA = rd0 ⇒ ILLI（`dst_rd0`，`spec/SimRISC-03 附录 B`）；无其它规则
@@ 立即数分片：wp0/wp1/wp2/wp3 = bits[15:0]/[31:16]/[47:32]/[63:48]（LSW..MSW，`spec/SimRISC-03 §1`）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 WDATA（`_MEM` 期望的来源）/ SCRATCH（rb/rf 实测落点）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：目的在 rd 直接比；在 rb/rf 用同组 `st.o` 落到 SCRATCH 再逐字节比 —— 不借被测指令；
@@   期望内联；`_MEM` 变体的期望从 WDATA 装载（不经任何 rwii 指令）⇒ 期望不由被测指令自证。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ dst=rd5/wp2/0xFF00 的规范编码字
	@@ 规范编码字 0x4816FF00（opc<<24 | rd5<<18 | wp2<<16 | 0xFF00）
	__LI	rd5, 0x0000000000000000
	.dd.t32	0x4816FF00
	__CHECK_RD           1, rd5, 0x0000FF0000000000
	@@ 最高寄存器 rd63 + wp3
	@@ 规范编码字 0x48FF0001（opc<<24 | rd63<<18 | wp3<<16 | 0x0001）
	__LI	rd63, 0x0000000000000000
	.dd.t32	0x48FF0001
	__CHECK_RD           2, rd63, 0x0001000000000000

	@@ ---- semantic ----
	@@ wp0（LSW）
	TEST_WI_RD           3, or.w, rd10, wp0, 0x1111, 0x0123456789ABCDEF, 0x0123456789ABDDFF
	@@ wp1 全 1 ⇒ 该 wyde 全 1
	TEST_WI_RD           4, or.w, rd11, wp1, 0xFFFF, 0x0123456789ABCDEF, 0x01234567FFFFCDEF
	@@ wp2
	TEST_WI_RD           5, or.w, rd12, wp2, 0x8000, 0x0123456789ABCDEF, 0x0123C56789ABCDEF
	@@ wp3（MSW）
	TEST_WI_RD           6, or.w, rd13, wp3, 0x0F0F, 0x0123456789ABCDEF, 0x0F2F456789ABCDEF
	@@ wp0；期望取自 WDATA（独立 oracle）
	TEST_WI_RD_MEM       7, or.w, rd14, wp0, 0x1111, 0x0123456789ABCDEF, 0x50

	@@ ---- boundary ----
	@@ immu16=0 ⇒ 恒等（OR 单位元）
	TEST_WI_RD           8, or.w, rd6, wp0, 0x0000, 0x0123456789ABCDEF, 0x0123456789ABCDEF
	@@ wp2 全 1 ⇒ 该 wyde 全 1
	TEST_WI_RD           9, or.w, rd7, wp2, 0xFFFF, 0x0123456789ABCDEF, 0x0123FFFF89ABCDEF
	@@ 旧值 0 ⇒ 结果即立即数
	TEST_WI_RD          10, or.w, rd8, wp2, 0x8000, 0x0000000000000000, 0x0000800000000000
	@@ 旧值全 1 ⇒ 恒等（吸收元）
	TEST_WI_RD          11, or.w, rd9, wp0, 0x0001, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
	@@ 置 wp3 最高位
	TEST_WI_RD          12, or.w, rd15, wp3, 0x8000, 0x0F0F0F0F0F0F0F0F, 0x8F0F0F0F0F0F0F0F
	@@ immu16=0 且旧值非平凡 ⇒ 恒等
	TEST_WI_RD          13, or.w, rd17, wp1, 0x0000, 0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- overlap ----
	@@ 目的=隐式源：旧 wyde 参与 OR
	TEST_WI_RD          14, or.w, rd18, wp0, 0x0F0F, 0xA5A55A5A0F0FF0F0, 0xA5A55A5A0F0FFFFF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器放行该编码）
	TEST_FAULT_WI       15, or.w, rd0, ILLI, wp0, 0x0001

	__TEST_SECTIONS
