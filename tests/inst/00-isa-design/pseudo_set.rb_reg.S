@@ pseudo_set.rb_reg.S — 伪指令 `set.rb rbHA, rs`（寄存器源；无 opcode 身份，`00-isa-design` 册）
@@ 大类：00-isa-design（伪指令的**前端展开**面）；册目录 `tests/inst/00-isa-design/`
@@ 名字不是 opcode id（`spec/SimRISC-00 §5`：伪指令不是硬件指令）⇒ 在 `tests/inst.yaml` 以
@@   `inst-00-isa-design-005` 登记，并在 `tools/testcases/{check_tests_index,validate_vectors}.py`
@@   的 `NON_ID_CARRIERS` 显式登记（逐文件，不做目录级豁免）。
@@ 语义（真源）：`spec/Toolchain-01 §6.1`（`set.rb rb, rs` → `rd2rb`/`rb2rb`）
@@   + `spec/SimRISC-02 §1`（块复制**保持 64 位二进制不变**；源/目的范围不得重叠）。
@@ 覆盖要求（用户 2026-11-15：「rb 寄存器应该要测到完整 64 位」）：
@@   * 两种源（`rd2rb`、`rb2rb`）各覆盖，且各至少一例源值**高半非零**
@@     （`0xDEADBEEFCAFEBABE` / `0xFEDCBA9876543210`）；
@@   * 四个 wyde（wp3=[63:48]、wp2=[47:32]、wp1=[31:16]、wp0=[15:0]）在**两种源**上都有
@@     「单 wyde 非零」专例；另有「高 32 全 1」与稀疏位型；
@@   * 校验一律 **64 位**：`st.o` 落 8 字节到 SCRATCH、`__CHECK_MEM` 整 beat 比（非只比低半）。
@@ 用例：encoding 0 / semantic 16 / boundary 3 / overlap 1（链例 20，故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；链例逐检查点把实测 8 字节
@@   写入结果缓冲并逐字节打印 ⇒ 三平台比较的是字节流。
@@ wyde 覆盖表（点号 → 源银行 / 非零 wyde）：
@@   1: rd / wp3+wp2+wp1+wp0 | 2: rd / wp3+wp2+wp1+wp0 | 3: rd / wp3+wp2 | 4: rd / wp1
@@   5: rd / wp0 | 6: rd / wp3 | 7: rd / wp2 | 8: rd0 源（全 0）
@@   9: rb / wp3+wp2+wp1+wp0 | 10: rb / wp3+wp2+wp1+wp0 | 11: rb / wp3 | 12: rb / wp2
@@   13: rb / wp1 | 14: rb / wp0 | 15: rb / 全 1 | 16: rb / wp3+wp0（稀疏）
@@   17: rb63 目的 / rd 源 / wp2 | 18: rb63 目的 / rb 源 / 全部 | 19: rd 源 / wp1+wp0
@@   20: 全 0（旧值覆盖）

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- semantic：rd2rb（源值高半非零）----
	__LI	rd5, 0xDEADBEEFCAFEBABE
	set.rb	rb5, rd5
	st.o	rb5, [rb29, 0]
	__CHECK_MEM          1, SCRATCH, 0, 0xDEADBEEFCAFEBABE
	__LI	rd6, 0x0123456789ABCDEF
	set.rb	rb6, rd6
	st.o	rb6, [rb29, 0]
	__CHECK_MEM          2, SCRATCH, 0, 0x0123456789ABCDEF
	@@ 高 32 全 1、低 32 全 0
	__LI	rd7, 0xFFFFFFFF00000000
	set.rb	rb7, rd7
	st.o	rb7, [rb29, 0]
	__CHECK_MEM          3, SCRATCH, 0, 0xFFFFFFFF00000000
	@@ 只有 wp1
	__LI	rd8, 0x00000000CAFE0000
	set.rb	rb8, rd8
	st.o	rb8, [rb29, 0]
	__CHECK_MEM          4, SCRATCH, 0, 0x00000000CAFE0000
	@@ 只有 wp0
	__LI	rd9, 0x000000000000BABE
	set.rb	rb9, rd9
	st.o	rb9, [rb29, 0]
	__CHECK_MEM          5, SCRATCH, 0, 0x000000000000BABE
	@@ 只有 wp3
	__LI	rd10, 0xDEAD000000000000
	set.rb	rb10, rd10
	st.o	rb10, [rb29, 0]
	__CHECK_MEM          6, SCRATCH, 0, 0xDEAD000000000000
	@@ 只有 wp2
	__LI	rd11, 0x0000BEEF00000000
	set.rb	rb11, rd11
	st.o	rb11, [rb29, 0]
	__CHECK_MEM          7, SCRATCH, 0, 0x0000BEEF00000000
	@@ rd0 恒 0 ⇒ 整 64 位写 0（源 rd0 合法：只读、读出 0）
	set.rb	rb12, rd0
	st.o	rb12, [rb29, 0]
	__CHECK_MEM          8, SCRATCH, 0, 0x0000000000000000

	@@ ---- semantic：rb2rb（源值高半非零）----
	__LI_RB	rb25, 0xDEADBEEFCAFEBABE
	set.rb	rb13, rb25
	st.o	rb13, [rb29, 0]
	__CHECK_MEM          9, SCRATCH, 0, 0xDEADBEEFCAFEBABE
	__LI_RB	rb25, 0xFEDCBA9876543210
	set.rb	rb14, rb25
	st.o	rb14, [rb29, 0]
	__CHECK_MEM         10, SCRATCH, 0, 0xFEDCBA9876543210
	@@ 只有 wp3
	__LI_RB	rb25, 0xDEAD000000000000
	set.rb	rb15, rb25
	st.o	rb15, [rb29, 0]
	__CHECK_MEM         11, SCRATCH, 0, 0xDEAD000000000000
	@@ 只有 wp2
	__LI_RB	rb25, 0x0000BEEF00000000
	set.rb	rb16, rb25
	st.o	rb16, [rb29, 0]
	__CHECK_MEM         12, SCRATCH, 0, 0x0000BEEF00000000
	@@ 只有 wp1
	__LI_RB	rb25, 0x00000000CAFE0000
	set.rb	rb17, rb25
	st.o	rb17, [rb29, 0]
	__CHECK_MEM         13, SCRATCH, 0, 0x00000000CAFE0000
	@@ 只有 wp0
	__LI_RB	rb25, 0x000000000000BABE
	set.rb	rb18, rb25
	st.o	rb18, [rb29, 0]
	__CHECK_MEM         14, SCRATCH, 0, 0x000000000000BABE
	@@ 全 1
	__LI_RB	rb25, 0xFFFFFFFFFFFFFFFF
	set.rb	rb19, rb25
	st.o	rb19, [rb29, 0]
	__CHECK_MEM         15, SCRATCH, 0, 0xFFFFFFFFFFFFFFFF
	@@ 稀疏位：bit63 + bit0
	__LI_RB	rb25, 0x8000000000000001
	set.rb	rb19, rb25
	st.o	rb19, [rb29, 0]
	__CHECK_MEM         16, SCRATCH, 0, 0x8000000000000001

	@@ ---- boundary：目的寄存器字段上界 rb63（两种源各一例）----
	__LI	rd12, 0x0000FFFF00000000
	set.rb	rb63, rd12
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         17, SCRATCH, 0, 0x0000FFFF00000000
	__LI_RB	rb25, 0xA5A55A5A0F0FF0F0
	set.rb	rb63, rb25
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         18, SCRATCH, 0, 0xA5A55A5A0F0FF0F0
	@@ 低 32 位全 1、高 32 位全 0（wp1+wp0）
	__LI	rd13, 0x00000000FFFFFFFF
	set.rb	rb26, rd13
	st.o	rb26, [rb29, 0]
	__CHECK_MEM         19, SCRATCH, 0, 0x00000000FFFFFFFF

	@@ ---- overlap：源/目的同名不合法（mreg_range_overlap）⇒ 用例一律不同名；
	@@   此处断言「目的旧值（高半非零）被整体覆盖」----
	__LI_RB	rb31, 0xFFFFFFFFFFFFFFFF
	__LI	rd14, 0x0000000000000001
	set.rb	rb31, rd14
	st.o	rb31, [rb29, 0]
	__CHECK_MEM         20, SCRATCH, 0, 0x0000000000000001

	__TEST_END

	__TEST_SECTIONS
