@@ pseudo_set.rf_reg.S — 伪指令 `set.rf rfHA, rs`（寄存器源 ⇒ `rd2rf`/`rf2rf`；无 opcode 身份）
@@ 大类：00-isa-design（伪指令的**前端展开**面）；册目录 `tests/inst/00-isa-design/`
@@ 名字不是 opcode id（`spec/SimRISC-00 §5`：伪指令不是硬件指令）⇒ 在 `tests/inst.yaml` 以
@@   `inst-00-isa-design-008` 登记，并在 `tools/testcases/{check_tests_index,validate_vectors}.py`
@@   的 `NON_ID_CARRIERS` 显式登记（逐文件，不做目录级豁免）。
@@ 语义（真源）：`spec/Toolchain-01 §6.1` + §6.2.3（`set.rf rf, rs` → `rd2rf`/`rf2rf`；
@@   **rf 源为整 64 位复制**）+ `spec/SimRISC-02 §1`（`rf2rf` 按
@@   **整 64 位逐位复制**、源读 64 位/目的写 64 位）+ `spec/SimRISC-00 §2.3`「例外」段
@@   （`rf2rf` 不是 ft 结果写入 ⇒ **不做窄写、不保留目的高半**）。
@@ ★ 写宽对照第二行（本任务核心）：`set.rf rf, rs` 展开为 `rf2rf`（rf 源）/`rd2rf`（rd 源）
@@   ⇒ 结果 = 源的完整 64 位，**高 32 位被覆盖**（不保留目的旧高半）；`set.ft rf, imm32` 则
@@   相反（窄写，见 `pseudo_set.ft_imm32.S`）。这正是 `m13-spec-010` 把 FT/FO 同组复制合并为
@@   `rf2rf` 后的可观察变化 ⇒ 本文件是它的第一道回归。
@@ 负向判据：若实现把 `set.rf rf, rf` 展开成两条 `set.w`（窄写）或保留目的高半，本文件
@@   每个检查点都要求「高半 = 源高半」而初值高半一律与源高半不同 ⇒ 必红。
@@ 用例：encoding 0 / semantic 6 / boundary 4 / overlap 3（链例 13，故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；链例逐检查点把实测 8 字节
@@   写入结果缓冲并逐字节打印 ⇒ 三平台比较的是字节流。
@@ 探针：目的在 rf ⇒ `rf2rd` 跨组读回完整 64 位再 `__CHECK_RD`（`rf2rd` 不是被测伪指令）；
@@   源/目的初值经 `set.rd` + `rd2rf` 装配（**不用** `set.rf`/`set.ft`/`set.fo` 造 rf 初值，
@@   否则「整 64 位 vs 窄写」的对照会自证）。
@@ 覆盖边界：`rf0` 作**源**的 rf2rf 例（期望运行期取自 rf0 自身）在 `02-reg-copy` 的
@@   `rf2rf_orri_rf.S`（宏 `TEST_MOV_RF0`）里；`rf2rf` 目的含 `rf0` ⇒ ILLI 属该文件的
@@   故障例，本文件不重复。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- semantic：整 64 位（高 32 被覆盖）----
	@@ 源高 32 = 0，目的高 32 = 0xAAAAAAAA ⇒ 结果高 32 必须是 0（窄写/保留高半都会红）
	set.rd	rd20, 0xAAAAAAAAAAAAAAAA
	rd2rf	{rf1:rf1}, {rd20:rd20}
	set.rd	rd20, 0x0000000012345678
	rd2rf	{rf2:rf2}, {rd20:rd20}
	set.rf	rf1, rf2
	rf2rd	{rd21:rd21}, {rf1:rf1}
	__CHECK_RD           1, rd21, 0x0000000012345678
	@@ 目的高 32 全 1、源高 32 全 0 ⇒ 结果高 32 = 0
	set.rd	rd20, 0xFFFFFFFF00000000
	rd2rf	{rf3:rf3}, {rd20:rd20}
	set.rd	rd20, 0x0000000000000001
	rd2rf	{rf4:rf4}, {rd20:rd20}
	set.rf	rf3, rf4
	rf2rd	{rd21:rd21}, {rf3:rf3}
	__CHECK_RD           2, rd21, 0x0000000000000001
	@@ 源全 1 ⇒ 目的（初值全 0x11）整 64 位变全 1（高半被覆盖为 1）
	set.rd	rd20, 0x1111111111111111
	rd2rf	{rf5:rf5}, {rd20:rd20}
	set.rd	rd20, 0xFFFFFFFFFFFFFFFF
	rd2rf	{rf6:rf6}, {rd20:rd20}
	set.rf	rf5, rf6
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD           3, rd21, 0xFFFFFFFFFFFFFFFF
	@@ 目的初值 0、源四 wyde 互异
	set.rd	rd20, 0x0000000000000000
	rd2rf	{rf7:rf7}, {rd20:rd20}
	set.rd	rd20, 0x0123456789ABCDEF
	rd2rf	{rf8:rf8}, {rd20:rd20}
	set.rf	rf7, rf8
	rf2rd	{rd21:rd21}, {rf7:rf7}
	__CHECK_RD           4, rd21, 0x0123456789ABCDEF
	@@ 源只有 bit63 ⇒ 结果 = 0x8000...（目的旧低半被覆盖）
	set.rd	rd20, 0x000000000000FFFF
	rd2rf	{rf9:rf9}, {rd20:rd20}
	set.rd	rd20, 0x8000000000000000
	rd2rf	{rf10:rf10}, {rd20:rd20}
	set.rf	rf9, rf10
	rf2rd	{rd21:rd21}, {rf9:rf9}
	__CHECK_RD           5, rd21, 0x8000000000000000
	@@ 目的交替掩码、源 wyde 交替全 0/全 1
	set.rd	rd20, 0xA5A55A5A0F0FF0F0
	rd2rf	{rf11:rf11}, {rd20:rd20}
	set.rd	rd20, 0x0000FFFF0000FFFF
	rd2rf	{rf12:rf12}, {rd20:rd20}
	set.rf	rf11, rf12
	rf2rd	{rd21:rd21}, {rf11:rf11}
	__CHECK_RD           6, rd21, 0x0000FFFF0000FFFF

	@@ ---- boundary：寄存器窗口上界 / rd0 源 ----
	@@ 窗口上界 rf62 ← rf63
	set.rd	rd20, 0x1111111111111111
	rd2rf	{rf62:rf62}, {rd20:rd20}
	set.rd	rd20, 0xA5A55A5A0F0FF0F0
	rd2rf	{rf63:rf63}, {rd20:rd20}
	set.rf	rf62, rf63
	rf2rd	{rd21:rd21}, {rf62:rf62}
	__CHECK_RD           7, rd21, 0xA5A55A5A0F0FF0F0
	@@ 窗口上界反向 rf63 ← rf62
	set.rd	rd20, 0xDEADBEEFCAFEBABE
	rd2rf	{rf62:rf62}, {rd20:rd20}
	set.rd	rd20, 0x0000000000000000
	rd2rf	{rf63:rf63}, {rd20:rd20}
	set.rf	rf63, rf62
	rf2rd	{rd21:rd21}, {rf63:rf63}
	__CHECK_RD           8, rd21, 0xDEADBEEFCAFEBABE
	@@ rd 源（rd0 恒 0）⇒ `rd2rf`：整 64 位写 0（目的旧高半被覆盖）
	set.rd	rd20, 0xFFFFFFFFFFFFFFFF
	rd2rf	{rf1:rf1}, {rd20:rd20}
	set.rf	rf1, rd0
	rf2rd	{rd21:rd21}, {rf1:rf1}
	__CHECK_RD           9, rd21, 0x0000000000000000
	@@ rd 源（非 0）⇒ 整 64 位复制
	set.rd	rd5, 0xDEADBEEFCAFEBABE
	set.rd	rd20, 0x0000000000000000
	rd2rf	{rf2:rf2}, {rd20:rd20}
	set.rf	rf2, rd5
	rf2rd	{rd21:rd21}, {rf2:rf2}
	__CHECK_RD          10, rd21, 0xDEADBEEFCAFEBABE

	@@ ---- overlap：目的旧高半必须被覆盖（最锐利的一组）----
	@@ 源 = 全 0 的 rf、目的旧值全 1 ⇒ 结果必须整 64 位 0
	set.rd	rd20, 0xFFFFFFFFFFFFFFFF
	rd2rf	{rf3:rf3}, {rd20:rd20}
	set.rd	rd20, 0x0000000000000000
	rd2rf	{rf4:rf4}, {rd20:rd20}
	set.rf	rf3, rf4
	rf2rd	{rd21:rd21}, {rf3:rf3}
	__CHECK_RD          11, rd21, 0x0000000000000000
	@@ 同上，rf 源形态（`rf2rf`）
	set.rd	rd20, 0xFFFFFFFFFFFFFFFF
	rd2rf	{rf5:rf5}, {rd20:rd20}
	set.rd	rd20, 0x0000000000000000
	rd2rf	{rf6:rf6}, {rd20:rd20}
	set.rf	rf5, rf6
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD          12, rd21, 0x0000000000000000
	@@ 源低半全 1、高半全 0；目的旧值高半全 1 ⇒ 结果 = 0x00000000FFFFFFFF
	set.rd	rd20, 0xFFFFFFFFFFFFFFFF
	rd2rf	{rf7:rf7}, {rd20:rd20}
	set.rd	rd20, 0x00000000FFFFFFFF
	rd2rf	{rf8:rf8}, {rd20:rd20}
	set.rf	rf7, rf8
	rf2rd	{rd21:rd21}, {rf7:rf7}
	__CHECK_RD          13, rd21, 0x00000000FFFFFFFF

	__TEST_END

	__TEST_SECTIONS
