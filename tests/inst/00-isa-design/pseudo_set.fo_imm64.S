@@ pseudo_set.fo_imm64.S — 伪指令 `set.fo rfHA, imm64`（立即数源；无 opcode 身份，`00-isa-design` 册）
@@ 大类：00-isa-design（伪指令的**前端展开**面）；册目录 `tests/inst/00-isa-design/`
@@ 名字不是 opcode id（`spec/SimRISC-00 §5`：伪指令不是硬件指令）⇒ 在 `tests/inst.yaml` 以
@@   `inst-00-isa-design-007` 登记，并在 `tools/testcases/{check_tests_index,validate_vectors}.py`
@@   的 `NON_ID_CARRIERS` 显式登记（逐文件，不做目录级豁免）。
@@ 语义（真源）：`spec/Toolchain-01 §6.1`（`set.fo rf, imm64` → `rd2rf rf, rd0`（恒 0，清零目的）
@@   + 对每个非零 wyde 的 `set.w rf, wpN, <wyde>`；**`set.fo rf, 0` ⇒ 仅 1 条 `rd2rf`**）
@@   + `spec/SimRISC-03 §4`（双精 1.0 的四条 `set.w` 示例与「加载零 → `rd2rf {rf1}, {rd0}`」示例）。
@@ 判据：**整 64 位**结果 = 立即数的 64 位位型（双击格式满载 64 位 ⇒ 与 `set.ft` 的窄写不同）；
@@   `imm = 0` 必须**清零整 64 位**（走 `rd2rf rd0` 特例，旧值（含高 32）全部丢弃）。
@@ 展开形状（`imm=0` 只有一条 `rd2rf`、无 `set.w`）由证据脚本对反汇编静态断言。
@@ 用例：encoding 0 / semantic 8 / boundary 6 / overlap 1（链例 15，故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Machine-v5 §7.1`）；链例逐检查点把实测 8 字节
@@   写入结果缓冲并逐字节打印 ⇒ 三平台比较的是字节流。
@@ 探针：目的在 rf ⇒ `rf2rd` 跨组读回完整 64 位再 `__CHECK_RD`（不是被测伪指令）；初值经
@@   `__LI_RF`（`__LI` + `rd2rf`）装配，不经任何 `set.*` 伪指令。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- semantic：整 64 位 + imm=0 特例 ----
	@@ imm=0 ⇒ `rd2rf rd0` 单项：旧值（全 1）整 64 位清零
	__LI_RF	rf1, 0xFFFFFFFFFFFFFFFF
	set.fo	rf1, 0
	rf2rd	{rd21:rd21}, {rf1:rf1}
	__CHECK_RD           1, rd21, 0x0000000000000000
	@@ 双精 1.0 = 0x3FF0000000000000（spec §4 示例：wp3 一条 + 其余零 wyde）
	__LI_RF	rf2, 0x0000000000000000
	set.fo	rf2, 0x3FF0000000000000
	rf2rd	{rd21:rd21}, {rf2:rf2}
	__CHECK_RD           2, rd21, 0x3FF0000000000000
	@@ 全 1（四个 wyde 全 0xFFFF）
	__LI_RF	rf3, 0x0000000000000000
	set.fo	rf3, 0xFFFFFFFFFFFFFFFF
	rf2rd	{rd21:rd21}, {rf3:rf3}
	__CHECK_RD           3, rd21, 0xFFFFFFFFFFFFFFFF
	@@ 高 32 位被立即数覆盖为 0（与 `set.ft` 的窄写对照：`set.fo` 写满 64 位）
	__LI_RF	rf4, 0xFFFFFFFFFFFFFFFF
	set.fo	rf4, 0x00000000FFFFFFFF
	rf2rd	{rd21:rd21}, {rf4:rf4}
	__CHECK_RD           4, rd21, 0x00000000FFFFFFFF
	@@ 四 wyde 互异
	__LI_RF	rf5, 0x0000000000000000
	set.fo	rf5, 0x0123456789ABCDEF
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD           5, rd21, 0x0123456789ABCDEF
	@@ 只有 bit63
	__LI_RF	rf6, 0x0000000000000000
	set.fo	rf6, 0x8000000000000000
	rf2rd	{rd21:rd21}, {rf6:rf6}
	__CHECK_RD           6, rd21, 0x8000000000000000
	@@ 只有 bit0
	__LI_RF	rf7, 0xA5A55A5A0F0FF0F0
	set.fo	rf7, 0x0000000000000001
	rf2rd	{rd21:rd21}, {rf7:rf7}
	__CHECK_RD           7, rd21, 0x0000000000000001
	@@ 交替掩码
	__LI_RF	rf8, 0x0000000000000000
	set.fo	rf8, 0xA5A55A5A0F0FF0F0
	rf2rd	{rd21:rd21}, {rf8:rf8}
	__CHECK_RD           8, rd21, 0xA5A55A5A0F0FF0F0

	@@ ---- boundary：单/双 wyde 边界、qNaN 位型、寄存器字段上界 ----
	@@ 只有 wp3 非零
	__LI_RF	rf9, 0x0000000000000000
	set.fo	rf9, 0xFFFF000000000000
	rf2rd	{rd21:rd21}, {rf9:rf9}
	__CHECK_RD           9, rd21, 0xFFFF000000000000
	@@ 中间两个 wyde 全 1、两侧全 0
	__LI_RF	rf10, 0xFFFFFFFFFFFFFFFF
	set.fo	rf10, 0x0000FFFFFFFF0000
	rf2rd	{rd21:rd21}, {rf10:rf10}
	__CHECK_RD          10, rd21, 0x0000FFFFFFFF0000
	@@ quiet NaN 位型（指数全 1、尾数最高位 1、符号 0；位型逐位保留）
	__LI_RF	rf11, 0x0000000000000000
	set.fo	rf11, 0x7FF8000000000000
	rf2rd	{rd21:rd21}, {rf11:rf11}
	__CHECK_RD          11, rd21, 0x7FF8000000000000
	@@ 负零位型
	__LI_RF	rf12, 0xFFFFFFFFFFFFFFFF
	set.fo	rf12, 0x8000000000000000
	rf2rd	{rd21:rd21}, {rf12:rf12}
	__CHECK_RD          12, rd21, 0x8000000000000000
	@@ 四 wyde 互异（另一组）
	__LI_RF	rf13, 0x0000000000000000
	set.fo	rf13, 0xDEADBEEFCAFEBABE
	rf2rd	{rd21:rd21}, {rf13:rf13}
	__CHECK_RD          13, rd21, 0xDEADBEEFCAFEBABE
	@@ 目的寄存器字段上界 rf63
	__LI_RF	rf63, 0x0123456789ABCDEF
	set.fo	rf63, 0x00000000FFFFFFFF
	rf2rd	{rd21:rd21}, {rf63:rf63}
	__CHECK_RD          14, rd21, 0x00000000FFFFFFFF

	@@ ---- overlap：imm=0 的破坏性（旧值非零、含高半 ⇒ 必须整 64 位清零）----
	__LI_RF	rf2, 0x0123456789ABCDEF
	set.fo	rf2, 0
	rf2rd	{rd21:rd21}, {rf2:rf2}
	__CHECK_RD          15, rd21, 0x0000000000000000

	__TEST_END

	__TEST_SECTIONS
