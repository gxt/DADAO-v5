@@ pseudo_set.ft_imm32.S — 伪指令 `set.ft rfHA, imm32`（立即数源；无 opcode 身份，`00-isa-design` 册）
@@ 大类：00-isa-design（伪指令的**前端展开**面）；册目录 `tests/inst/00-isa-design/`
@@ 名字不是 opcode id（`spec/SimRISC-00 §5`：伪指令不是硬件指令）⇒ 在 `tests/inst.yaml` 以
@@   `inst-00-isa-design-006` 登记，并在 `tools/testcases/{check_tests_index,validate_vectors}.py`
@@   的 `NON_ID_CARRIERS` 显式登记（逐文件，不做目录级豁免）。
@@ 语义（真源）：`spec/Toolchain-01 §6.1`（`set.ft rf, imm32` → 2 条 `set.w`（wp1/wp0））
@@   + `spec/SimRISC-03 §1`（`set.w` 只设置对应 16 位、**其余 48 位不变**）
@@   + `spec/SimRISC-00 §2.3`（ft 结果「只写低 32 位、高 32 位保持原值」的写法总则）。
@@ ★ 写宽对照第一行（本册与本任务的核心）：`set.ft rf, imm32` 是**窄写** —— 结果 =
@@   `(rf 初值 & 0xFFFFFFFF00000000) | imm32`；高 32 位**必须保持写前值**（不扩展、不填 0、
@@   不填 1）。对照面 = `pseudo_set.rf_reg.S`（`set.rf rf, rs` ⇒ `rd2rf`/`rf2rf` 整 64 位，
@@   高 32 位**被覆盖**）。
@@ 负向判据：若实现把 `set.ft` 展开成整 64 位搬移（如 `rd2rf`）或把高半清 0，本文件每个
@@   检查点的期望都要求高半 = 初值高半（初值高半一律取非 0 且与 imm32 的高半无关）⇒ 必红。
@@ 用例：encoding 0 / semantic 7 / boundary 6 / overlap 2（链例 15，故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；链例逐检查点把实测 8 字节
@@   写入结果缓冲并逐字节打印 ⇒ 三平台比较的是字节流。
@@ 探针：目的在 rf ⇒ `rf2rd` 跨组读回完整 64 位再 `__CHECK_RD`（`rf2rd` 不是被测伪指令）；
@@   初值经 `set.rd` + `rd2rf` 装配（**不用** `set.fo`/`set.ft`；否则「只写低 32」的坏实现
@@   会把初值高半也写窄，每条「高半保持」断言都退化恒真）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- semantic：写宽（高 32 保持）+ imm32 各 wyde ----
	@@ imm32 = 0 ⇒ 低 32 清 0，高 32 保持 0xA5A55A5A
	set.rd	rd20, 0xA5A55A5A0F0FF0F0
	rd2rf	{rf1:rf1}, {rd20:rd20}
	set.ft	rf1, 0x00000000
	rf2rd	{rd21:rd21}, {rf1:rf1}
	__CHECK_RD           1, rd21, 0xA5A55A5A00000000
	@@ imm32 = 0xFFFFFFFF ⇒ 低 32 全 1，高 32 保持 0x01234567
	set.rd	rd20, 0x0123456789ABCDEF
	rd2rf	{rf2:rf2}, {rd20:rd20}
	set.ft	rf2, 0xFFFFFFFF
	rf2rd	{rd21:rd21}, {rf2:rf2}
	__CHECK_RD           2, rd21, 0x01234567FFFFFFFF
	@@ imm32 = 0x3F800000（单精 1.0f）⇒ 高 32 保持全 1
	set.rd	rd20, 0xFFFFFFFFFFFFFFFF
	rd2rf	{rf3:rf3}, {rd20:rd20}
	set.ft	rf3, 0x3F800000
	rf2rd	{rd21:rd21}, {rf3:rf3}
	__CHECK_RD           3, rd21, 0xFFFFFFFF3F800000
	@@ 初值高 32 = 0 ⇒ 结果高 32 仍为 0（窄写不等于「高半来自 imm 的符号」）
	set.rd	rd20, 0x0000000000000000
	rd2rf	{rf4:rf4}, {rd20:rd20}
	set.ft	rf4, 0xFFFFFFFF
	rf2rd	{rd21:rd21}, {rf4:rf4}
	__CHECK_RD           4, rd21, 0x00000000FFFFFFFF
	@@ 初值只有 bit63 ⇒ 高半保持 bit63，低半 = 1
	set.rd	rd20, 0x8000000000000000
	rd2rf	{rf5:rf5}, {rd20:rd20}
	set.ft	rf5, 0x00000001
	rf2rd	{rd21:rd21}, {rf5:rf5}
	__CHECK_RD           5, rd21, 0x8000000000000001
	@@ 初值高 32 = 0x7FFFFFFF（若「高半被清 0」则必红）
	set.rd	rd20, 0x7FFFFFFFFFFFFFFF
	rd2rf	{rf6:rf6}, {rd20:rd20}
	set.ft	rf6, 0x7F7FFFFF
	rf2rd	{rd21:rd21}, {rf6:rf6}
	__CHECK_RD           6, rd21, 0x7FFFFFFF7F7FFFFF
	@@ 四 wyde 互异的初值 + 四 wyde 互异的 imm32
	set.rd	rd20, 0xDEADBEEFCAFEBABE
	rd2rf	{rf7:rf7}, {rd20:rd20}
	set.ft	rf7, 0x12345678
	rf2rd	{rd21:rd21}, {rf7:rf7}
	__CHECK_RD           7, rd21, 0xDEADBEEF12345678

	@@ ---- boundary：imm32 的 wyde 边界 / 高半各极性 ----
	@@ imm32 = 0x0000FFFF（只有 wp0 全 1）
	set.rd	rd20, 0xFFFF0000FFFF0000
	rd2rf	{rf8:rf8}, {rd20:rd20}
	set.ft	rf8, 0x0000FFFF
	rf2rd	{rd21:rd21}, {rf8:rf8}
	__CHECK_RD           8, rd21, 0xFFFF00000000FFFF
	@@ imm32 高半全 1、低半 0（wp1 全 1）
	set.rd	rd20, 0xAAAAAAAAAAAAAAAA
	rd2rf	{rf9:rf9}, {rd20:rd20}
	set.ft	rf9, 0xFFFF0000
	rf2rd	{rd21:rd21}, {rf9:rf9}
	__CHECK_RD           9, rd21, 0xAAAAAAAAFFFF0000
	@@ imm32 bit31 单置（ft 符号位）
	set.rd	rd20, 0x1111222233334444
	rd2rf	{rf10:rf10}, {rd20:rd20}
	set.ft	rf10, 0x80000000
	rf2rd	{rd21:rd21}, {rf10:rf10}
	__CHECK_RD          10, rd21, 0x1111222280000000
	@@ imm32 = 0x00010000（只有 wp1 的 bit0）
	set.rd	rd20, 0x3333444455556666
	rd2rf	{rf11:rf11}, {rd20:rd20}
	set.ft	rf11, 0x00010000
	rf2rd	{rd21:rd21}, {rf11:rf11}
	__CHECK_RD          11, rd21, 0x3333444400010000
	@@ 初值低 32 已全 1、imm32 = 0 ⇒ 只清低 32
	set.rd	rd20, 0x00000000FFFFFFFF
	rd2rf	{rf12:rf12}, {rd20:rd20}
	set.ft	rf12, 0x00000000
	rf2rd	{rd21:rd21}, {rf12:rf12}
	__CHECK_RD          12, rd21, 0x0000000000000000
	@@ 目的寄存器字段上界 rf63
	set.rd	rd20, 0x1111222233334444
	rd2rf	{rf63:rf63}, {rd20:rd20}
	set.ft	rf63, 0xAAAABBBB
	rf2rd	{rd21:rd21}, {rf63:rf63}
	__CHECK_RD          13, rd21, 0x11112222AAAABBBB

	@@ ---- overlap：目的旧值参与（高半来自旧值）+ 不触碰 FCSR ----
	@@ 初值高 32 全 1、低 32 全 1，imm32 = 0 ⇒ 结果 = 0xFFFFFFFF00000000（高低半来源不同）
	set.rd	rd20, 0xFFFFFFFFFFFFFFFF
	rd2rf	{rf13:rf13}, {rd20:rd20}
	set.ft	rf13, 0x00000000
	rf2rd	{rd21:rd21}, {rf13:rf13}
	__CHECK_RD          14, rd21, 0xFFFFFFFF00000000
	@@ `set.w` 不是浮点运算 ⇒ FCSR 位型写前写后逐位相等（期望不在本检查点内联：
	@@   射频状态位由硬件定义，故用 rf0 自身作运行期期望）
	set.rd	rd20, 0x0123456789ABCDEF
	rd2rf	{rf2:rf2}, {rd20:rd20}
	rf2rd	{rd25:rd25}, {rf0:rf0}
	set.ft	rf2, 0x12345678
	rf2rd	{rd26:rd26}, {rf0:rf0}
	__VERIFY_EQ_RD      15, rd25, rd26
	rf2rd	{rd21:rd21}, {rf2:rf2}
	__CHECK_RD          15, rd21, 0x0123456712345678

	__TEST_END

	__TEST_SECTIONS
