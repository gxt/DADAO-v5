@@ set.w_rwii_rf.S — set.w rfHA, wpN, immu16（rwii, opc 0x4F）
@@ 大类：03-wyde-imm（16 位立即数操作，`spec/SimRISC-03 §1`）；册目录 `tests/inst/03-wyde-imm/`
@@ id：set.w_rwii_rf　形式：rwii　opc：0x4F　mask：0xFF000000　value：0x4F000000　目的银行：RF
@@ 语义：rfHA 的 wyde(wpN) ← immu16，其余 48 位**保持不变**（所以单精 2 条、双精 4 条拼装）
@@ 合法性：无附加合法性规则（`spec/SimRISC-03 附录 B`）。`set.w rf0` **合法**：写按 SimRISC-00 写语义 ——
@@   wp2 命中舍入模式 [33:32]、wp0 命中异常状态 [4:0]、wp1/wp3 完全写无效
@@ 立即数分片：wp0/wp1/wp2/wp3 = bits[15:0]/[31:16]/[47:32]/[63:48]（LSW..MSW，`spec/SimRISC-03 §1`）
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 WDATA（`_MEM` 期望的来源）/ SCRATCH（rb/rf 实测落点）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（段地址由宏层 `inst_test.inc` 固定；本册复用）
@@ 用例：encoding 2 / semantic 5 / boundary 9 / overlap 1（链例 17 + 故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：目的在 rd 直接比；在 rb/rf 用同组 `st.o` 落到 SCRATCH 再逐字节比 —— 不借被测指令；
@@   期望内联；`_MEM` 变体的期望从 WDATA 装载（不经任何 rwii 指令）⇒ 期望不由被测指令自证。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ dst=rf5/wp2/0x1234 的规范编码字
	@@ 规范编码字 0x4F161234（opc<<24 | rf5<<18 | wp2<<16 | 0x1234）
	__LI	rd20, 0x0123456789ABCDEF
	rd2rf	{rf5:rf5}, {rd20:rd20}
	.dd.t32	0x4F161234
	st.o	rf5, [rb29, 0]
	__CHECK_MEM          1, SCRATCH, 0, 0x0123123489ABCDEF
	@@ 最高寄存器 rf63 + wp3
	@@ 规范编码字 0x4FFF0001（opc<<24 | rf63<<18 | wp3<<16 | 0x0001）
	__LI	rd20, 0x0000000000000000
	rd2rf	{rf63:rf63}, {rd20:rd20}
	.dd.t32	0x4FFF0001
	st.o	rf63, [rb29, 0]
	__CHECK_MEM          2, SCRATCH, 0, 0x0001000000000000

	@@ ---- semantic ----
	@@ wp0（LSW）
	TEST_WI_RF           3, set.w, rf10, wp0, 0x9ABC, 0x0123456789ABCDEF, 0x0123456789AB9ABC
	@@ wp1 全 1
	TEST_WI_RF           4, set.w, rf11, wp1, 0xFFFF, 0x0123456789ABCDEF, 0x01234567FFFFCDEF
	@@ wp2 清 0
	TEST_WI_RF           5, set.w, rf12, wp2, 0x0000, 0x0123456789ABCDEF, 0x0123000089ABCDEF
	@@ wp3（MSW）
	TEST_WI_RF           6, set.w, rf13, wp3, 0xDEAD, 0x0123456789ABCDEF, 0xDEAD456789ABCDEF
	@@ wp2；期望取自 WDATA（独立 oracle）
	TEST_WI_RF_MEM       7, set.w, rf14, wp2, 0xFFFF, 0x0123456789ABCDEF, 0x60

	@@ ---- boundary ----
	@@ wp0 清零
	TEST_WI_RF           8, set.w, rf6, wp0, 0x0000, 0x0123456789ABCDEF, 0x0123456789AB0000
	@@ wp1 最高位
	TEST_WI_RF           9, set.w, rf7, wp1, 0x8000, 0x0123456789ABCDEF, 0x012345678000CDEF
	@@ wp3 最高位（旧值 0）
	TEST_WI_RF          10, set.w, rf8, wp3, 0x8000, 0x0000000000000000, 0x8000000000000000
	@@ wp3 最小非零
	TEST_WI_RF          11, set.w, rf9, wp3, 0x0001, 0x0000000000000000, 0x0001000000000000
	@@ 两条 set.w 拼 32 位单精 1.0（wp1=0x3F80 + wp0=0）
	__LI	rd20, 0x0000000000000000
	rd2rf	{rf20:rf20}, {rd20:rd20}
	set.w	rf20, wp1, 0x3F80
	set.w	rf20, wp0, 0x0000
	st.o	rf20, [rb29, 0]
	__CHECK_MEM         12, SCRATCH, 0, 0x000000003F800000
	@@ rf0/wp1 完全写无效 ⇒ 写前后 rf0 逐位相等
	TEST_WI_RF0_NOOP    13, wp1, 0xFFFF
	@@ rf0/wp3 完全写无效
	TEST_WI_RF0_NOOP    14, wp3, 0x0000
	@@ rf0/wp2 只写 [33:32]（RM←11；其余 14 位写无效），其余 62 位保持（逐字节）
	TEST_WI_RF0_WRITE   15, wp2, 0x03FF
	@@ rf0/wp0 只写 [4:0]（异常状态←全 1；[15:5] 写无效），其余位保持（逐字节）
	TEST_WI_RF0_WRITE   16, wp0, 0xFFFF

	@@ ---- overlap ----
	@@ 目的=隐式源：其余 48 位保持
	TEST_WI_RF          17, set.w, rf15, wp2, 0x1234, 0xA5A55A5A0F0FF0F0, 0xA5A512340F0FF0F0

	__TEST_END

	__TEST_SECTIONS
