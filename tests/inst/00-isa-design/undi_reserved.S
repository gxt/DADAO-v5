@@ undi_reserved.S — 保留编码（QFC 空白格）的 UNDI 断言（无 opcode 身份，`00-isa-design` 册）
@@ 大类：00-isa-design（指令系统设计：保留编码的**否定**面，`spec/SimRISC-00 §2.9`）
@@ 名字不是 opcode id：本册承载「不属于任何合法身份」的编码用例，故无 id、不入 M1 覆盖矩阵；
@@   在 `tests/inst.yaml` 以 `inst-00-isa-design-001` 登记（载体↔索引双向断言），在
@@   `tools/testcases/{check_tests_index,validate_vectors}.py` 的 `NON_ID_CARRIERS` 显式登记。
@@ 语义：QFC 主表的空白单元格 = 保留编码 ⇒ 译码即 UNDI（`spec/SimRISC-00 §2.9`；
@@   `contracts/legality_rules.yaml` 的 `undefined_encoding`）；不是「未实现」也不是 NOP。
@@ 判据：故障例一例一镜像，退出码 = monitor 段编码 `0xF0|异常位索引` ⇒ UNDI = `0xF9`
@@   （`spec/Machine-v5 §7.1`）；三平台（chipyard/qemu/gem5）同码。
@@ 用例：encoding 0 / semantic 0 / boundary 0 / overlap 0 / legality 3（链例 0 + 故障例 3）
@@ 来源：原保留编码 YAML 的 3 条**无 id** 用例（该 YAML 已随 YAML 退役删除；
@@   其余 6 条 CFXMEM 例本就有 id 与 `.S` 载体，随各 id 保留）。
@@ 编码字与 QFC 格位（现场自 `spec/SimRISC-00` QFC 表逐格核）：
@@   0x08040001 — op[7:0]=0x08，QFC 0000-1xxx 整行 reserved；
@@   0x1B040001 — op=0x1B，QFC 0001-1xxx 行的 column 011（0x18~0x1F 中 0x1B 空白）；
@@   0x58040001 — op=0x58，QFC 0101-1xxx 行的 column 000（0x59/0x5A/0x5B/0x5C/0x5D 为合法指令）。
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数；点号 1..3 连续（`run_asm_suite.scan_source` 断言）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ op=0x08 整行 reserved（ha=0x01，非全零）
	TEST_FAULT_ENC        1, UNDI, 0x08040001, rb3, TEST_DATA, rd19, 0

	@@ op=0x1B 单格空白（同行的 0x18/0x19/0x1A 是合法 st.*）
	TEST_FAULT_ENC        2, UNDI, 0x1B040001, rb3, TEST_DATA, rd19, 0

	@@ op=0x58 单格空白（同行 0x59/0x5A/0x5B 等为合法指令）
	TEST_FAULT_ENC        3, UNDI, 0x58040001, rb3, TEST_DATA, rd19, 0

	__TEST_SECTIONS
