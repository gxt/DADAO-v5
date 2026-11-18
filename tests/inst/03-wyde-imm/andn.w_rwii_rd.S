@@ andn.w_rwii_rd.S — andn.w rdHA, wpN, immu16（rwii, opc 0x49）
@@ 大类：03-wyde-imm（16 位立即数操作，`spec/SimRISC-03 §1`）；册目录 `tests/inst/03-wyde-imm/`
@@ id：andn.w_rwii_rd　形式：rwii　opc：0x49　mask：0xFF000000　value：0x49000000　目的银行：RD
@@ 语义：rdHA 的 wyde(wpN) ← (旧值 & ~immu16)，其余 3 个 wyde 保持不变
@@ 合法性：目的 rdHA = rd0 ⇒ ILLI（`dst_rd0`，`spec/SimRISC-03 附录 B`）；无其它规则
@@ 立即数分片：wp0/wp1/wp2/wp3 = bits[15:0]/[31:16]/[47:32]/[63:48]（LSW..MSW，`spec/SimRISC-03 §1`）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 WDATA（`_MEM` 期望的来源）/ SCRATCH（rb/rf 实测落点）
@@ 链接布局：`tests/ee-tiny/inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / boundary 6 / overlap 1（链例 14 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：目的在 rd 直接比；在 rb/rf 用同组 `st.o` 落到 SCRATCH 再逐字节比 —— 不借被测指令；
@@   期望内联；`_MEM` 变体的期望从 WDATA 装载（不经任何 rwii 指令）⇒ 期望不由被测指令自证。

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/03-wyde-imm/03-wyde-imm.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ dst=rd5/wp0/0x00FF 的规范编码字
	@@ 规范编码字 0x491400FF（opc<<24 | rd5<<18 | wp0<<16 | 0x00FF）
	set.rd	rd5, 0xFFFFFFFFFFFFFFFF
	.dd.t32	0x491400FF
	__CHECK_RD           1, rd5, 0xFFFFFFFFFFFFFF00
	@@ 最高寄存器 rd63 + wp3
	@@ 规范编码字 0x49FFFFFF（opc<<24 | rd63<<18 | wp3<<16 | 0xFFFF）
	set.rd	rd63, 0x0123456789ABCDEF
	.dd.t32	0x49FFFFFF
	__CHECK_RD           2, rd63, 0x0000456789ABCDEF

	@@ ---- semantic ----
	@@ wp0（LSW）
	TEST_WI_RD           3, andn.w, rd10, wp0, 0x00FF, 0x0123456789ABCDEF, 0x0123456789ABCD00
	@@ wp1
	TEST_WI_RD           4, andn.w, rd11, wp1, 0x0F0F, 0x0123456789ABCDEF, 0x0123456780A0CDEF
	@@ wp2
	TEST_WI_RD           5, andn.w, rd12, wp2, 0xFF00, 0x0123456789ABCDEF, 0x0123006789ABCDEF
	@@ wp3（MSW）
	TEST_WI_RD           6, andn.w, rd13, wp3, 0x0F0F, 0x8899AABBCCDDEEFF, 0x8090AABBCCDDEEFF
	@@ wp1；期望取自 WDATA（独立 oracle）
	TEST_WI_RD_MEM       7, andn.w, rd14, wp1, 0xFFFF, 0x0123456789ABCDEF, 0x58

	@@ ---- boundary ----
	@@ immu16=0 ⇒ 恒等（AND-NOT 单位元）
	TEST_WI_RD           8, andn.w, rd6, wp0, 0x0000, 0x0123456789ABCDEF, 0x0123456789ABCDEF
	@@ 旧值 0 ⇒ 恒 0
	TEST_WI_RD           9, andn.w, rd7, wp0, 0xFFFF, 0x0000000000000000, 0x0000000000000000
	@@ wp2 全 1 ⇒ 该 wyde 清零
	TEST_WI_RD          10, andn.w, rd8, wp2, 0xFFFF, 0xFFFFFFFFFFFFFFFF, 0xFFFF0000FFFFFFFF
	@@ 清符号位
	TEST_WI_RD          11, andn.w, rd9, wp3, 0x8000, 0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF
	@@ wp0 全 1
	TEST_WI_RD          12, andn.w, rd15, wp0, 0xFFFF, 0xDEADBEEFCAFEF00D, 0xDEADBEEFCAFE0000
	@@ wp1 低位字节掩码
	TEST_WI_RD          13, andn.w, rd17, wp1, 0x00FF, 0x00000000FFFFFFFF, 0x00000000FF00FFFF

	@@ ---- overlap ----
	@@ 目的=隐式源：旧 wyde 参与 AND-NOT
	TEST_WI_RD          14, andn.w, rd18, wp0, 0xF0F0, 0xA5A55A5A0F0FF0F0, 0xA5A55A5A0F0F0000

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----
	@@ 目的 rd0 ⇒ ILLI（dst_rd0；汇编器放行该编码）
	TEST_FAULT_WI       15, andn.w, rd0, ILLI, wp0, 0x0001

	__TEST_SECTIONS
