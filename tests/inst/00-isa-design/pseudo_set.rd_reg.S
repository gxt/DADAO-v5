@@ pseudo_set.rd_reg.S — 伪指令 `set.rd rdHA, rs`（寄存器源；无 opcode 身份，`00-isa-design` 册）
@@ 大类：00-isa-design（伪指令的**前端展开**面）；册目录 `tests/inst/00-isa-design/`
@@ 名字不是 opcode id（`spec/SimRISC-00 §5`：伪指令不是硬件指令）⇒ 在 `tests/inst.yaml` 以
@@   `inst-00-isa-design-003` 登记，并在 `tools/testcases/{check_tests_index,validate_vectors}.py`
@@   的 `NON_ID_CARRIERS` 显式登记（逐文件，不做目录级豁免）。
@@ 语义（真源）：`spec/Toolchain-01 §6.1`（`set.rd rd, rs` → `rb2rd`/`rf2rd`/`ra2rd`/`rd2rd`）
@@   + `spec/SimRISC-02 §1`（块复制**保持 64 位二进制不变**、源/目的范围不得重叠、`immu6`=1）。
@@ 判据：四种源银行各覆盖，且**整 64 位**（高 32 位也搬）—— 期望内联自 spec 的寄存器位型。
@@ 源初值通路（不借被测伪指令）：rd/rb 用 `__LI`/`__LI_RB`；ra 只能经内存给（`set.zw`/`or.w`
@@   无 ra 形式）⇒ `__SET_MEM` 从 RDATA 装载，其值由宏层 `.testdata` 的字面量给出。
@@ 用例：encoding 0 / semantic 8 / boundary 1 / overlap 1（链例 10，故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；链例逐检查点把实测 8 字节
@@   写入结果缓冲并逐字节打印 ⇒ 三平台比较的是字节流。
@@ 探针：目的在 rd ⇒ `__CHECK_RD` 直接比（复制指令本体在伪指令之外的银行读回里不使用）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ ---- semantic：四种源银行 ----
	@@ rb2rd：四 wyde 互异
	__LI_RB	rb5, 0x0123456789ABCDEF
	set.rd	rd5, rb5
	__CHECK_RD           1, rd5, 0x0123456789ABCDEF
	@@ rb2rd：全 1
	__LI_RB	rb6, 0xFFFFFFFFFFFFFFFF
	set.rd	rd6, rb6
	__CHECK_RD           2, rd6, 0xFFFFFFFFFFFFFFFF
	@@ rf2rd：整 64 位（rf 作源读出完整 64 位，非窄写）
	__LI_RF	rf3, 0x123456789ABCDEF0
	set.rd	rd7, rf3
	__CHECK_RD           3, rd7, 0x123456789ABCDEF0
	@@ rf2rd：稀疏位（bit63 + bit0）
	__LI_RF	rf4, 0x8000000000000001
	set.rd	rd8, rf4
	__CHECK_RD           4, rd8, 0x8000000000000001
	@@ ra2rd：ra 初值经内存装入（RDATA+0x18 = 0xABCDEF0123456789）
	__SET_MEM	ra5, 0x18
	set.rd	rd9, ra5
	__CHECK_RD           5, rd9, 0xABCDEF0123456789
	@@ ra2rd：RDATA+0x30 = 0x8000000000000000（只有 bit63）
	__SET_MEM	ra10, 0x30
	set.rd	rd10, ra10
	__CHECK_RD           6, rd10, 0x8000000000000000
	@@ rd2rd：四 wyde 互异
	__LI	rd11, 0xDEADBEEFCAFEBABE
	set.rd	rd12, rd11
	__CHECK_RD           7, rd12, 0xDEADBEEFCAFEBABE
	@@ rd2rd：交替掩码
	__LI	rd11, 0xA5A55A5A0F0FF0F0
	set.rd	rd13, rd11
	__CHECK_RD           8, rd13, 0xA5A55A5A0F0FF0F0

	@@ ---- boundary：rd0 作源（硬连零）+ 目的寄存器字段上界 ----
	@@ rd0 恒 0 ⇒ 整 64 位写 0（源 rd0 合法：只读、读出 0）
	set.rd	rd14, rd0
	__CHECK_RD           9, rd14, 0x0000000000000000

	@@ ---- overlap：源/目的同名不合法（mreg_range_overlap）⇒ 用例一律不同名；
	@@   此处断言「目的旧值被整体覆盖」----
	@@ rb63（最高基址寄存器作源）+ 目的旧值非零 ⇒ 结果 = 源值
	__LI_RB	rb63, 0x0000FFFF00000000
	__LI	rd15, 0xA5A55A5A0F0FF0F0
	set.rd	rd15, rb63
	__CHECK_RD          10, rd15, 0x0000FFFF00000000

	__TEST_END

	__TEST_SECTIONS
