@@ pseudo_set.rd_imm.S — 伪指令 `set.rd rdHA, imm64`（立即数源；无 opcode 身份，`00-isa-design` 册）
@@ 大类：00-isa-design（伪指令的**前端展开**面）；册目录 `tests/inst/00-isa-design/`
@@ 名字不是 opcode id：`set.*` 是伪指令、不是硬件指令（`spec/SimRISC-00 §5`：伪指令由汇编器
@@   前端展开为一条或多条真实指令，反汇编器只输出真实指令）⇒ 无 id，在
@@   `tests/inst.yaml` 以 `inst-00-isa-design-002` 登记（载体↔索引双向断言），并在
@@   `tools/testcases/{check_tests_index,validate_vectors}.py` 的 `NON_ID_CARRIERS` 显式登记。
@@ 语义（真源）：`spec/Toolchain-01 §6.1`（`set.rd rd, imm64` → **最少指令数**，`set.zw`/`set.ow`
@@   + `or.w`/`andn.w`，≤4 条）+ `spec/SimRISC-03 §2`（wyde 级展开示例与「只能一条
@@   `set.zw`/`set.ow`」约束）+ §1（`set.zw` 清零其余 48 位、`set.ow` 置 1）。
@@ 判据（本文件的检查点）：展开是**前端行为**，可观察结果只有一条 —— 目的寄存器最终等于
@@   立即数的**完整 64 位位型**（不依赖旧值、不依赖展开细节）。期望一律内联自 spec 的立即数
@@   位型，**不从 qemu/llvm 输出反推**。
@@ 展开形状（「只能一条 `set.zw`/`set.ow`」「全 0/全 1 ≤1 条」）不能由 guest 观察 ⇒ 由证据脚本
@@   对 `llvm-objdump` 的反汇编逐例静态断言（本文件头部声明，不在检查点里）。
@@ 用例：encoding 0 / semantic 12 / boundary 6 / overlap 2（链例 20，故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；链例逐检查点把实测 8 字节
@@   写入结果缓冲并逐字节打印 ⇒ 三平台比较的是字节流。
@@ 探针：目的在 rd ⇒ `__CHECK_RD` 直接比（不借任何 rwii 指令造期望）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- semantic：零 / 小值 / 负数 / 稀疏位 / 全 1 ----
	@@ imm=0 ⇒ 全 64 位清零（spec 示例：`set.rd rd1, 0` = 一条 set.zw）
	set.rd	rd5, 0
	__CHECK_RD           1, rd5, 0x0000000000000000
	@@ 16 位以内的正数
	set.rd	rd5, 0x1234
	__CHECK_RD           2, rd5, 0x0000000000001234
	@@ 全 1（-1）⇒ 一条 set.ow 全 64 位置 1
	set.rd	rd5, -1
	__CHECK_RD           3, rd5, 0xFFFFFFFFFFFFFFFF
	@@ 负小值 -42 ⇒ 高 48 位由 set.ow 的填充自动置 1（符号扩展不是伪指令的额外语义，
	@@   而是「位型 = 立即数的 64 位补码」的展开结果）
	set.rd	rd6, -42
	__CHECK_RD           4, rd6, 0xFFFFFFFFFFFFFFD6
	@@ 负小值 -32768（0x8000 的单 wyde 边界）
	set.rd	rd6, -32768
	__CHECK_RD           5, rd6, 0xFFFFFFFFFFFF8000
	@@ 32 位常量（两个非零 wyde）
	set.rd	rd7, 0x1234ABCD
	__CHECK_RD           6, rd7, 0x000000001234ABCD
	@@ 四个 wyde 互不相同（≤4 条展开的下界）
	set.rd	rd7, 0xDEADBEEFCAFEBABE
	__CHECK_RD           7, rd7, 0xDEADBEEFCAFEBABE
	@@ 稀疏位：bit63 + bit0
	set.rd	rd8, 0x8000000000000001
	__CHECK_RD           8, rd8, 0x8000000000000001
	@@ wyde 交替掩码（高 wyde 全 1、低 wyde 全 0 交替）
	set.rd	rd8, 0xFFFF0000FFFF0000
	__CHECK_RD           9, rd8, 0xFFFF0000FFFF0000
	@@ 高位全 1 + 低 16 位掩码 0xFFF0（spec §2 示例）
	set.rd	rd9, 0xFFFFFFFFFFFFFFF0
	__CHECK_RD          10, rd9, 0xFFFFFFFFFFFFFFF0
	@@ ~(1<<5)（spec §2 示例：展开为 set.ow wp0, 0xFFDF）
	set.rd	rd9, 0xFFFFFFFFFFFFFFDF
	__CHECK_RD          11, rd9, 0xFFFFFFFFFFFFFFDF
	@@ 只在 wp2 有值（其余 wyde 全 0）
	set.rd	rd10, 0x0000ABCD00000000
	__CHECK_RD          12, rd10, 0x0000ABCD00000000

	@@ ---- boundary：最值 / 单 wyde 边界 / 目的寄存器边界 ----
	@@ 只有最高 wyde 非零
	set.rd	rd10, 0xFFFF000000000000
	__CHECK_RD          13, rd10, 0xFFFF000000000000
	@@ 四 wyde 两两不同（0x0123/0x4567/0x89AB/0xCDEF）
	set.rd	rd11, 0x0123456789ABCDEF
	__CHECK_RD          14, rd11, 0x0123456789ABCDEF
	@@ 最大正数（bit63 = 0，其余全 1）
	set.rd	rd11, 0x7FFFFFFFFFFFFFFF
	__CHECK_RD          15, rd11, 0x7FFFFFFFFFFFFFFF
	@@ 交替掩码 A5A5..5A5A..（两个 wyde 极性相反）
	set.rd	rd12, 0xA5A55A5A0F0FF0F0
	__CHECK_RD          16, rd12, 0xA5A55A5A0F0FF0F0
	@@ 最小非零（bit0）
	set.rd	rd12, 1
	__CHECK_RD          17, rd12, 0x0000000000000001
	@@ 目的寄存器字段上界 rd63 + 全 1（set.ow 路径的字段边界）
	set.rd	rd63, -1
	__CHECK_RD          18, rd63, 0xFFFFFFFFFFFFFFFF

	@@ ---- overlap：目的旧值不影响结果（伪指令写满 64 位）----
	@@ 旧值全为交替掩码 ⇒ 结果 = 立即数（低 32 全 1、高 32 全 0）
	@@   旧值**不经被测伪指令**铺（`set.rb` + `rb2rd`；否则「只写低 32」的坏实现会
	@@   把旧值也写成同一窄值，断言退化恒真）
	set.rb	rb13, 0xA5A55A5A0F0FF0F0
	rb2rd	{rd13}, {rb13}
	set.rd	rd13, 0x00000000FFFFFFFF
	__CHECK_RD          19, rd13, 0x00000000FFFFFFFF
	@@ 旧值非零 ⇒ 结果 = 仅 bit63
	set.rd	rd13, 0x8000000000000000
	__CHECK_RD          20, rd13, 0x8000000000000000

	__TEST_END

	__TEST_SECTIONS
