@@ set.zw_rwii_rb.S — set.zw rbHA, wpN, immu16（rwii, opc 0x4E）
@@ 大类：03-wyde-imm（16 位立即数操作，`spec/SimRISC-03 §1`）；册目录 `tests/inst/03-wyde-imm/`
@@ id：set.zw_rwii_rb　形式：rwii　opc：0x4E　mask：0xFF000000　value：0x4E000000　目的银行：RB
@@ 语义：rbHA 的 wyde(wpN) ← immu16，其余 48 位**清 0**（含 [63:48]，`spec/SimRISC-03 §3` 注：地址高位）
@@ 合法性：目的 rbHA = rb0 ⇒ ILLI（`dst_rb0`，`spec/SimRISC-03 附录 B`）；无其它规则
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
	@@ dst=rb5/wp1/0x1234 的规范编码字
	@@ 规范编码字 0x4E151234（opc<<24 | rb5<<18 | wp1<<16 | 0x1234）
	__LI_RB	rb5, 0x0123456789ABCDEF
	.dd.t32	0x4E151234
	st.o	rb5, [rb29, 0]
	__CHECK_MEM          1, SCRATCH, 0, 0x0000000012340000
	@@ 最高寄存器 rb63 + wp3
	@@ 规范编码字 0x4EFFFFFF（opc<<24 | rb63<<18 | wp3<<16 | 0xFFFF）
	__LI_RB	rb63, 0x0000000000000000
	.dd.t32	0x4EFFFFFF
	st.o	rb63, [rb29, 0]
	__CHECK_MEM          2, SCRATCH, 0, 0xFFFF000000000000

	@@ ---- semantic ----
	@@ wp0（LSW）
	TEST_WI_RB           3, set.zw, rb10, wp0, 0x1234, 0xFFFFFFFFFFFFFFFF, 0x0000000000001234
	@@ wp1
	TEST_WI_RB           4, set.zw, rb11, wp1, 0x8000, 0x0123456789ABCDEF, 0x0000000080000000
	@@ wp2
	TEST_WI_RB           5, set.zw, rb12, wp2, 0xFFFF, 0xA5A55A5A0F0FF0F0, 0x0000FFFF00000000
	@@ wp3（MSW）
	TEST_WI_RB           6, set.zw, rb13, wp3, 0x7FFF, 0xDEADBEEFCAFEF00D, 0x7FFF000000000000
	@@ wp2；期望取自 WDATA（独立 oracle）
	TEST_WI_RB_MEM       7, set.zw, rb14, wp2, 0xABCD, 0x0123456789ABCDEF, 0x40

	@@ ---- boundary ----
	@@ immu16=0 ⇒ 全清
	TEST_WI_RB           8, set.zw, rb6, wp0, 0x0000, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000
	@@ wp3 全 1
	TEST_WI_RB           9, set.zw, rb7, wp3, 0xFFFF, 0x0123456789ABCDEF, 0xFFFF000000000000
	@@ 位 31 单置
	TEST_WI_RB          10, set.zw, rb8, wp1, 0x8000, 0xFFFFFFFFFFFFFFFF, 0x0000000080000000
	@@ wp0 全 1
	TEST_WI_RB          11, set.zw, rb9, wp0, 0xFFFF, 0xDEADBEEFCAFEF00D, 0x000000000000FFFF
	@@ 高 16 位归零（地址溢出检测用法）
	TEST_WI_RB          12, set.zw, rb15, wp1, 0x9ABC, 0xFFFF0000FFFF0000, 0x000000009ABC0000
	@@ 最小非零立即数
	TEST_WI_RB          13, set.zw, rb17, wp0, 0x0001, 0x0000000000000000, 0x0000000000000001

	@@ ---- overlap ----
	@@ 目的=隐式源：旧值被整体丢弃
	TEST_WI_RB          14, set.zw, rb18, wp2, 0x5A5A, 0xA5A55A5A0F0FF0F0, 0x00005A5A00000000

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rb0 ⇒ ILLI（dst_rb0；汇编器放行该编码）
	TEST_FAULT_WI       15, set.zw, rb0, ILLI, wp0, 0x0001

	__TEST_SECTIONS
