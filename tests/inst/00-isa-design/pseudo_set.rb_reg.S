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

@@ ---- 文件专用宏（m15-testcases-004 整例宏化；只被本文件使用）----
@@ **一行 = 一整条用例**：点号是该行第 1 个实参，宏体末尾的 `__CHECK_MEM` 用 `\pt`
@@   作失败点号并记录实测值 ⇒ 「失败点号 = 用例序号」在文件里逐行可见
@@   （门控 `check-inst-macro-scope` S6/S7/S8 机械判：宏体恰 1 处断言且点号引用 `\pt`、
@@   一行用例行恰展开 1 个检查点、正文不得再有裸 `__CHECK_*`）。
@@ 参数 = 点号, 源寄存器, 目的寄存器, 源值[, 目的旧值]（源与目的不同名 ⇒ 「不同名」口径）。
@@   `old` 只在「旧值被整体覆盖」例传（先按 `__LI_RB` 铺旧值再覆盖）。
.macro __PT_SET_RB_RD pt, src, dst, val, old
	.ifnb	\old
	__LI_RB	\dst, \old
	.endif
	__LI	\src, \val
	set.rb	\dst, \src
	st.o	\dst, [rb29, 0]
	__CHECK_MEM	\pt, SCRATCH, 0, \val
.endm

.macro __PT_SET_RB_RB pt, src, dst, val
	__LI_RB	\src, \val
	set.rb	\dst, \src
	st.o	\dst, [rb29, 0]
	__CHECK_MEM	\pt, SCRATCH, 0, \val
.endm

@@ 源为 rd0（硬连零）：只读、读出 0 ⇒ 整 64 位写 0；不装载（写 rd0 会 ILLI）。
.macro __PT_SET_RB_RD0 pt, dst
	set.rb	\dst, rd0
	st.o	\dst, [rb29, 0]
	__CHECK_MEM	\pt, SCRATCH, 0, 0x0
.endm

	__TEST_BEGIN

	@@ ---- semantic：rd2rb（源值高半非零）----
	__PT_SET_RB_RD	1, rd5, rb5, 0xDEADBEEFCAFEBABE
	__PT_SET_RB_RD	2, rd6, rb6, 0x0123456789ABCDEF
	@@ 高 32 全 1、低 32 全 0
	__PT_SET_RB_RD	3, rd7, rb7, 0xFFFFFFFF00000000
	@@ 只有 wp1
	__PT_SET_RB_RD	4, rd8, rb8, 0x00000000CAFE0000
	@@ 只有 wp0
	__PT_SET_RB_RD	5, rd9, rb9, 0x000000000000BABE
	@@ 只有 wp3
	__PT_SET_RB_RD	6, rd10, rb10, 0xDEAD000000000000
	@@ 只有 wp2
	__PT_SET_RB_RD	7, rd11, rb11, 0x0000BEEF00000000
	@@ rd0 恒 0 ⇒ 整 64 位写 0（源 rd0 合法：只读、读出 0）
	__PT_SET_RB_RD0	8, rb12

	@@ ---- semantic：rb2rb（源值高半非零）----
	__PT_SET_RB_RB	9, rb25, rb13, 0xDEADBEEFCAFEBABE
	__PT_SET_RB_RB	10, rb25, rb14, 0xFEDCBA9876543210
	@@ 只有 wp3
	__PT_SET_RB_RB	11, rb25, rb15, 0xDEAD000000000000
	@@ 只有 wp2
	__PT_SET_RB_RB	12, rb25, rb16, 0x0000BEEF00000000
	@@ 只有 wp1
	__PT_SET_RB_RB	13, rb25, rb17, 0x00000000CAFE0000
	@@ 只有 wp0
	__PT_SET_RB_RB	14, rb25, rb18, 0x000000000000BABE
	@@ 全 1
	__PT_SET_RB_RB	15, rb25, rb19, 0xFFFFFFFFFFFFFFFF
	@@ 稀疏位：bit63 + bit0
	__PT_SET_RB_RB	16, rb25, rb19, 0x8000000000000001

	@@ ---- boundary：目的寄存器字段上界 rb63（两种源各一例）----
	__PT_SET_RB_RD	17, rd12, rb63, 0x0000FFFF00000000
	__PT_SET_RB_RB	18, rb25, rb63, 0xA5A55A5A0F0FF0F0
	@@ 低 32 位全 1、高 32 位全 0（wp1+wp0）
	__PT_SET_RB_RD	19, rd13, rb26, 0x00000000FFFFFFFF

	@@ ---- overlap：源/目的同名不合法（mreg_range_overlap）⇒ 用例一律不同名；
	@@   此处断言「目的旧值（高半非零）被整体覆盖」----
	__PT_SET_RB_RD	20, rd14, rb31, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF

	__TEST_END

	__TEST_SECTIONS
