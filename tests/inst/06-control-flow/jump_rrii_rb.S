@@ jump_rrii_rb.S — jump [rbHA, rdHB, imms14]（rrii/rb, opc 0x71）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §2`）；册目录 `tests/inst/06-control-flow/`
@@ id：jump_rrii_rb　形式：rrii（rb）　opc：0x71　mask：0xFF000000　value：0x71000000
@@ 语义：无条件跳转；目标 = rbHA + rdHB + (SX(imms12) << 2)（64 位计算，结果写回 rb0，
@@   取低 48 位为下一条地址）；rbHA **仅读**（不修改）
@@   特例（`spec/SimRISC-06 §2`）：ha = rb0 时 `rdHB + (imms12 << 2)` 仍是**相对**跳转
@@   立即数在汇编层按**字节**书写（`imms14`），编码层 `imms12 = 字节 >> 2`
@@ 合法性：`contracts/legality_rules.yaml` 对 jump 无 active 静态规则；目标恒 4 字节对齐
@@   （`imms12 << 2`）⇒ 不会触发 IALIGN；基址可以是任意 RB（含 0）⇒ 目标地址 0 落在
@@   未映射段 ⇒ 取指 CFXMEM（合法性/故障例）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrii = opc | rbha[23:18] | rdhb[17:12] | imms12[11:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rb`/`set.rd` 拼基址与偏移寄存器）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 1 / semantic 1 / overlap 1 / boundary 3（链例 6 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：跳转**距离与落点地址**用 `.org` 钉住的槽位 + `__LAND_IP`（`aip.si` 取 IP）核，
@@   期望写 `ENTRY + <字面偏移>`（llvm-mc 只折装绝对常量，标签差不进立即数）

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1：规范编码字 0x71000002（rbha = rb0、rdhb = rd0、imms12 = 2 ⇒ +8）⇒ 跳过 4 B
	set.rd	rd24, 0
	.dd.t32	0x71000002
	add.si	rd24, 1
	__CHECK_RD          1, rd24, 0

	@@ ---- semantic ----
	@@ rb0 作基址 + rdHB 寄存器偏移：目标 = IP + 4 + 8 = IP + 12 ⇒ 跳过 2 条（rd24 保持 0）
	set.rd	rd6, 4
	set.rd	rd24, 0
	jump	[rb0, rd6, 8]
	add.si	rd24, 1
	add.si	rd24, 2
	__CHECK_RD          2, rd24, 0

	@@ ---- overlap ----
	@@ 基址与偏移都取 0 号寄存器（rb0 在 rrii 里是相对基址、rd0 读出 0）⇒ 退化为相对跳转
	set.rd	rd24, 0
	jump	[rb0, rd0, 8]
	add.si	rd24, 1
	__CHECK_RD          3, rd24, 0

	@@ ---- boundary：目标地址（`.org` 钉住槽位；零填充只被 jump 跨过）----
	set.rb	rb5, (ENTRY + 0x1300)
	set.rd	rd6, 0x100
	set.rd	rd24, 0
	jump	[rb0, __slot4]
	.org	0x800
__l5:                                    @@ 0x800：例 5 的落点
	__PREP_LAND_JUMP	__ck5
	.org	0xC00
__slot4:                                 @@ 0xC00：基址 ENTRY+0x1300 + 0x100 + 0 ⇒ 落点 0x1400
	jump	[rb5, rd6, 0]
	.org	0xC20
__slot5:                                 @@ 0xC20：基址 ENTRY+0x900 + 0 - 0x100 ⇒ 落点 0x800
	jump	[rb5, rd6, -0x100]
	.org	0xC40
__slot6:                                 @@ 0xC40：基址 ENTRY+0x1800 + 0x60 + 0x40 ⇒ 落点 0x18A0
	jump	[rb5, rd6, 0x40]
	.org	0x1400
__l4:                                    @@ 0x1400：例 4 的落点
	__PREP_LAND_JUMP	__ck4
	.org	0x18A0
__l6:                                    @@ 0x18A0：例 6 的落点
	__PREP_LAND_JUMP	__ck6
	.org	0x1A00
__ck4:
	__CHECK_RD          4, rd24, (ENTRY + 0x1400)
	set.rb	rb5, (ENTRY + 0x900)     @@ 例 5：基址 + 0 偏移 - 0x100
	set.rd	rd6, 0
	jump	[rb0, __slot5]
__ck5:
	__CHECK_RD          5, rd24, (ENTRY + 0x800)
	set.rb	rb5, (ENTRY + 0x1800)    @@ 例 6：基址 + 0x60 + 0x40
	set.rd	rd6, 0x60
	jump	[rb0, __slot6]
__ck6:
	__CHECK_RD          6, rd24, (ENTRY + 0x18A0)

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ 目标地址 0（rb5 = 0、rd6 = 0、imms12 = 0）⇒ 取指 CFXMEM
	TEST_FAULT_ADDR0    7, jump, CFXMEM

	__TEST_SECTIONS
