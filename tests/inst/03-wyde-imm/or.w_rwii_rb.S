@@ or.w_rwii_rb.S — or.w rbHA, wpN, immu16（rwii, opc 0x4A）
@@ 大类：03-wyde-imm（16 位立即数操作，`spec/SimRISC-03 §1`）；册目录 `tests/inst/03-wyde-imm/`
@@ id：or.w_rwii_rb　形式：rwii　opc：0x4A　mask：0xFF000000　value：0x4A000000　目的银行：RB
@@ 语义：rbHA 的 wyde(wpN) ← (旧值 | immu16)，其余 3 个 wyde 保持不变
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
	.include "tests/inst/03-wyde-imm/03-wyde-imm.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ dst=rb5/wp3/0x8000 的规范编码字
	@@ 规范编码字 0x4A178000（opc<<24 | rb5<<18 | wp3<<16 | 0x8000）
	__LI_RB	rb5, 0x0000000000000000
	.dd.t32	0x4A178000
	st.o	rb5, [rb29, 0]
	__CHECK_MEM          1, SCRATCH, 0, 0x8000000000000000
	@@ 最高寄存器 rb63 + wp0
	@@ 规范编码字 0x4AFC0001（opc<<24 | rb63<<18 | wp0<<16 | 0x0001）
	__LI_RB	rb63, 0x0000000000000000
	.dd.t32	0x4AFC0001
	st.o	rb63, [rb29, 0]
	__CHECK_MEM          2, SCRATCH, 0, 0x0000000000000001

	@@ ---- semantic ----
	@@ wp0（LSW）
	TEST_WI_RB           3, or.w, rb10, wp0, 0x1111, 0x0123456789ABCDEF, 0x0123456789ABDDFF
	@@ wp1 全 1
	TEST_WI_RB           4, or.w, rb11, wp1, 0xFFFF, 0x0123456789ABCDEF, 0x01234567FFFFCDEF
	@@ wp2
	TEST_WI_RB           5, or.w, rb12, wp2, 0x8000, 0x0123456789ABCDEF, 0x0123C56789ABCDEF
	@@ wp3（MSW）
	TEST_WI_RB           6, or.w, rb13, wp3, 0x0F0F, 0x0123456789ABCDEF, 0x0F2F456789ABCDEF
	@@ wp0；期望取自 WDATA（独立 oracle）
	TEST_WI_RB_MEM       7, or.w, rb14, wp0, 0x1111, 0x0123456789ABCDEF, 0x50

	@@ ---- boundary ----
	@@ immu16=0 ⇒ 恒等
	TEST_WI_RB           8, or.w, rb6, wp0, 0x0000, 0x0123456789ABCDEF, 0x0123456789ABCDEF
	@@ wp2 全 1
	TEST_WI_RB           9, or.w, rb7, wp2, 0xFFFF, 0x0123456789ABCDEF, 0x0123FFFF89ABCDEF
	@@ 旧值 0 ⇒ 结果即立即数
	TEST_WI_RB          10, or.w, rb8, wp2, 0x8000, 0x0000000000000000, 0x0000800000000000
	@@ 旧值全 1 ⇒ 恒等
	TEST_WI_RB          11, or.w, rb9, wp0, 0x0001, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF
	@@ 置 wp3 最高位
	TEST_WI_RB          12, or.w, rb15, wp3, 0x8000, 0x0F0F0F0F0F0F0F0F, 0x8F0F0F0F0F0F0F0F
	@@ immu16=0 恒等（高 16 位不被动）
	TEST_WI_RB          13, or.w, rb17, wp1, 0x0000, 0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFEF00D

	@@ ---- overlap ----
	@@ 目的=隐式源：旧 wyde 参与 OR
	TEST_WI_RB          14, or.w, rb18, wp0, 0x0F0F, 0xA5A55A5A0F0FF0F0, 0xA5A55A5A0F0FFFFF

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----
	@@ 目的 rb0 ⇒ ILLI（dst_rb0；汇编器放行该编码）
	TEST_FAULT_WI       15, or.w, rb0, ILLI, wp0, 0x0001

	__TEST_SECTIONS
