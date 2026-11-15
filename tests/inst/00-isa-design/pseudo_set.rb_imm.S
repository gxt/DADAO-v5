@@ pseudo_set.rb_imm.S — 伪指令 `set.rb rbHA, imm64`（立即数源；无 opcode 身份，`00-isa-design` 册）
@@ 大类：00-isa-design（伪指令的**前端展开**面）；册目录 `tests/inst/00-isa-design/`
@@ 名字不是 opcode id（`spec/SimRISC-00 §5`：伪指令不是硬件指令）⇒ 在 `tests/inst.yaml` 以
@@   `inst-00-isa-design-004` 登记，并在 `tools/testcases/{check_tests_index,validate_vectors}.py`
@@   的 `NON_ID_CARRIERS` 显式登记（逐文件，不做目录级豁免）。
@@ 语义（真源）：`spec/Toolchain-01 §6.1`（`set.rb rb, imm64` → `set.zw`-rb + `or.w`-rb；
@@   **不补 `set.ow`-rb**（rb 无该变体））+ `spec/SimRISC-03 §3`（wyde 级展开与「只能一条
@@   `set.zw`」约束）+ §1（rb 只有 `set.zw`/`or.w`/`andn.w`）。
@@ 与 `set.rd` 的**形态差异**（与 `pseudo_set.rd_imm.S` 对照）：负值/全 1 在 rd 里可用一条
@@   `set.ow` 完成（其余 48 位置 1），在 rb 里必须 `set.zw` + 逐 wyde `or.w`（全 1 = 4 条）；
@@   但**可观察结果相同**：目的寄存器 = 立即数的完整 64 位位型（RB 是整 64 位寄存器，
@@   作访存基址时才截到 `rb[47:0]`，`spec/SimRISC-00 §2.2`）。
@@ 覆盖要求（用户 2026-11-15：「rb 寄存器应该要测到完整 64 位」）：
@@   * 四个 wyde 各有**单 wyde 非零**的专例（wp3 = bits[63:48]、wp2 = [47:32]、wp1 = [31:16]、
@@     wp0 = [15:0]），另有多 wyde 组合与「高 32 全 1」形态（验证种子 + `or.w` 修正不会
@@     误清高半）、稀疏位型（`0x8000000000000001`）、`set.rb rb, 0`（种子 wp0 清其余 48 位）；
@@   * 校验一律 **64 位**：`st.o` 把 rb 落 8 字节到 SCRATCH，`__CHECK_MEM` 按整 beat 比
@@     （比较宽度 = 64 位，非只比低半）；探针不经任何 `set.*` 指令。
@@ 用例：encoding 0 / semantic 15 / boundary 3 / overlap 2（链例 20，故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；链例逐检查点把实测 8 字节
@@   写入结果缓冲并逐字节打印 ⇒ 三平台比较的是字节流。
@@ wyde 覆盖表（点号 → 非零 wyde）：
@@   2: wp0 | 3: wp1 | 4: wp2 | 5: wp3 | 6: wp2+wp1+wp0 | 7: wp3+wp2+wp1+wp0
@@   8: wp3+wp2+wp1+wp0（高 32 全 1）| 9: wp3+wp2 | 10: 全 1 | 11: 全 1 | 12: 全 1 | 13: wp3+wp0
@@   1: 全 0 | 14: 全部 | 15: 全部 | 16: wp3+wp1 | 17: wp2+wp0 | 18: wp0 | 19: 全 0（旧值覆盖）
@@   20: 全部（旧值覆盖）

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- semantic ----
	@@ 0 ⇒ 一条 set.zw wp0, 0：其余 48 位清零
	set.rb	rb5, 0
	st.o	rb5, [rb29, 0]
	__CHECK_MEM          1, SCRATCH, 0, 0x0000000000000000
	@@ 只有 wp0（bits[15:0]）
	set.rb	rb5, 0x1234
	st.o	rb5, [rb29, 0]
	__CHECK_MEM          2, SCRATCH, 0, 0x0000000000001234
	@@ 只有 wp1（bits[31:16]）
	set.rb	rb6, 0x00000000CAFE0000
	st.o	rb6, [rb29, 0]
	__CHECK_MEM          3, SCRATCH, 0, 0x00000000CAFE0000
	@@ 只有 wp2（bits[47:32]）
	set.rb	rb6, 0x0000BEEF00000000
	st.o	rb6, [rb29, 0]
	__CHECK_MEM          4, SCRATCH, 0, 0x0000BEEF00000000
	@@ 只有 wp3（bits[63:48]）
	set.rb	rb6, 0xDEAD000000000000
	st.o	rb6, [rb29, 0]
	__CHECK_MEM          5, SCRATCH, 0, 0xDEAD000000000000
	@@ 48 位地址（spec §3 示例：set.zw wp2 + or.w wp1 + or.w wp0，共 3 条）
	set.rb	rb7, 0x123456789ABC
	st.o	rb7, [rb29, 0]
	__CHECK_MEM          6, SCRATCH, 0, 0x0000123456789ABC
	@@ 四 wyde 互异
	set.rb	rb7, 0xDEADBEEFCAFEBABE
	st.o	rb7, [rb29, 0]
	__CHECK_MEM          7, SCRATCH, 0, 0xDEADBEEFCAFEBABE
	@@ 高 32 全 1 + 低 32 互异（四个 wyde 全非零）：1 条种子 + 3 条 or.w 一条不漏
	@@   ⇒ 任一 wyde 漏写或被误清，此例必红
	set.rb	rb8, 0xFFFFFFFFCAFEBABE
	st.o	rb8, [rb29, 0]
	__CHECK_MEM          8, SCRATCH, 0, 0xFFFFFFFFCAFEBABE
	@@ 高 32 全 1、低 32 全 0（种子取 wp3，wp2 用 or.w 补全 1）
	set.rb	rb8, 0xFFFFFFFF00000000
	st.o	rb8, [rb29, 0]
	__CHECK_MEM          9, SCRATCH, 0, 0xFFFFFFFF00000000
	@@ 全 1（-1）：rb 无 set.ow ⇒ set.zw + 3×or.w（4 条）
	set.rb	rb9, -1
	st.o	rb9, [rb29, 0]
	__CHECK_MEM         10, SCRATCH, 0, 0xFFFFFFFFFFFFFFFF
	@@ 负小值 -42：位型 = 立即数的 64 位补码（高 48 位由 or.w 逐 wyde 置 1）
	set.rb	rb9, -42
	st.o	rb9, [rb29, 0]
	__CHECK_MEM         11, SCRATCH, 0, 0xFFFFFFFFFFFFFFD6
	@@ 负小值 -32768
	set.rb	rb10, -32768
	st.o	rb10, [rb29, 0]
	__CHECK_MEM         12, SCRATCH, 0, 0xFFFFFFFFFFFF8000
	@@ 稀疏位：bit63 + bit0
	set.rb	rb10, 0x8000000000000001
	st.o	rb10, [rb29, 0]
	__CHECK_MEM         13, SCRATCH, 0, 0x8000000000000001
	@@ 四 wyde 全非零的交替掩码
	set.rb	rb11, 0x0F0F0F0F0F0F0F0F
	st.o	rb11, [rb29, 0]
	__CHECK_MEM         14, SCRATCH, 0, 0x0F0F0F0F0F0F0F0F
	@@ 两半极性相反
	set.rb	rb11, 0xA5A55A5A0F0FF0F0
	st.o	rb11, [rb29, 0]
	__CHECK_MEM         15, SCRATCH, 0, 0xA5A55A5A0F0FF0F0

	@@ ---- boundary ----
	@@ wyde 交替全 1/全 0（wp3、wp1 为全 1；wp2、wp0 为全 0）
	set.rb	rb12, 0xFFFF0000FFFF0000
	st.o	rb12, [rb29, 0]
	__CHECK_MEM         16, SCRATCH, 0, 0xFFFF0000FFFF0000
	@@ 高位 wyde 全 0、低位 wyde 全 1（48 位地址上界形态）
	set.rb	rb12, 0x0000FFFF0000FFFF
	st.o	rb12, [rb29, 0]
	__CHECK_MEM         17, SCRATCH, 0, 0x0000FFFF0000FFFF
	@@ 目的寄存器字段上界 rb63 + 最小非零（bit0）
	set.rb	rb63, 1
	st.o	rb63, [rb29, 0]
	__CHECK_MEM         18, SCRATCH, 0, 0x0000000000000001

	@@ ---- overlap：目的旧值不影响结果（伪指令写满 64 位）----
	__LI_RB	rb13, 0xA5A55A5A0F0FF0F0
	set.rb	rb13, 0
	st.o	rb13, [rb29, 0]
	__CHECK_MEM         19, SCRATCH, 0, 0x0000000000000000
	__LI_RB	rb13, 0x0000000000000001
	set.rb	rb13, 0xA5A55A5A0F0FF0F0
	st.o	rb13, [rb29, 0]
	__CHECK_MEM         20, SCRATCH, 0, 0xA5A55A5A0F0FF0F0

	__TEST_END

	__TEST_SECTIONS
