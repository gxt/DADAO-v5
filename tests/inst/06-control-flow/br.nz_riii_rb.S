@@ br.nz_riii_rb.S — br.nz {rbHA}?, [rb0, imms20]（riii/rb, opc 0x73）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §1`）；册目录 `tests/inst/06-control-flow/`
@@ id：br.nz_riii_rb　形式：riii（rb）　opc：0x73　mask：0xFF000000　value：0x73000000
@@ 语义：条件成立 ⇒ 跳转；目标 = rb0 + (SX(imms18) << 2)（64 位计算，结果写回 rb0，
@@   取低 48 位为下一条地址）；不成立 ⇒ 顺序执行 rb0 + 4
@@   判据（`spec/SimRISC-06 §1`）：rbHA != 0（**整 64 位**判零；-rb/-rd 两变体只差寄存器组、判据同口径）⇒ 成立
@@   条件按**整 64 位有符号**判（不是 32 位符号扩展后的值）；rb0 读出当前 IP（**非**硬连零）⇒ 非零 ⇒ 成立
@@ 合法性：`contracts/legality_rules.yaml` 对 br.nz 无 active 静态规则；源可为 rb0（读出当前 IP）；
@@   目标恒 4 字节对齐（`imms18 << 2`）⇒ 不会触发 IALIGN；imms18 = ±512 KiB ⇒ 可越过
@@   Tiny（8 MiB）SRAM 边界（边界例：目标在 SRAM 之下 ⇒ CFXMEM）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：riii = opc | rbha[23:18] | imms18[17:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rd`/`set.rb` 拼条件寄存器；**不使用数据区**）
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / overlap 2 / boundary 3（链例 12 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：条件寄存器用 `set.rd`/`set.rb` 拼常量（被测分支不参与造初值）、期望内联；跳转/不跳
@@   由 rd24 的 1/0 标记判（`TEST_BR1_RB`）；跳转**距离与落点地址**用 `.org` 钉住的槽位 +
@@   `__LAND_IP`（`aip.si` 取 IP）核，期望写 `ENTRY + <字面偏移>`

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1：规范编码字 0x73040002（rbha = 1 + 「成立」侧的值）⇒ 成立 ⇒ 跳过紧随的 4 B
	set.rb	rb1, 0x0000000000000001
	set.rd	rd24, 0
	.dd.t32	0x73040002
	add.si	rd24, 1
	__CHECK_RD          1, rd24, 0

	@@ 点 2：字段边界（rbha = 63，最大寄存器号）+ 同等成立（0x73FC0002）
	set.rb	rb63, 0x0000000000000001
	set.rd	rd24, 0
	.dd.t32	0x73FC0002
	add.si	rd24, 1
	__CHECK_RD          2, rd24, 0

	@@ ---- semantic ----
	@@ 1 ⇒ 成立
	TEST_BR1_RB	3, br.nz, rb5, 0x0000000000000001, 1
	@@ -1 ⇒ 成立
	TEST_BR1_RB	4, br.nz, rb5, 0xFFFFFFFFFFFFFFFF, 1
	@@ 零 ⇒ 不成立
	TEST_BR1_RB	5, br.nz, rb5, 0x0000000000000000, 0
	@@ 只置高位的非零值 ⇒ 成立（不是只看低 32 位）
	TEST_BR1_RB	6, br.nz, rb5, 0x8000000000000000, 1
	@@ 低 32 位全 1 ⇒ 成立
	TEST_BR1_RB	7, br.nz, rb5, 0x00000000FFFFFFFF, 1

	@@ ---- overlap ----
	@@ 同一寄存器连续两条分支：第一条跳过后寄存器未被改写 ⇒ 第二条仍按同值判（非零值）
	set.rb	rb5, 0x0000000000000001
	set.rd	rd24, 0
	br.nz	{rb5}?, [rb0, __o1]
	jump	[rb0, __o2]
__o1:
	set.rd	rd24, 1
__o2:
	br.nz	{rb5}?, [rb0, __o3]
	add.si	rd24, 1
__o3:
	__CHECK_RD         8, rd24, 1

	@@ rb0 作条件（rb0 读出当前 IP、非硬连零）：IP 非零 ⇒ 成立
	TEST_BR1_RB       9, br.nz, rb0, 0xFFFFFFFFFFFFFFFF, 1

	@@ ---- boundary：跳转距离（`.org` 钉住槽位；零填充只被 jump/分支跨过）----
	set.rb	rb5, 0x0000000000000001
	set.rd	rd24, 0
	jump	[rb0, __d_f1]
	.org	0xA00
__d_b1:                                  @@ 0xA00：后向字面量分支的落点
	__PREP_LAND_JUMP	__d_ck_b
	.org	0xE00
__d_f1:                                  @@ 0xE00：+0x800 ⇒ 落点 0x1600
	br.nz	{rb5}?, [rb0, 0x800]
	add.si	rd24, 1
	.org	0xE20
__d_b2:                                  @@ 0xE20：-0x420 ⇒ 落点 0xA00
	br.nz	{rb5}?, [rb0, -0x420]
	add.si	rd24, 1
	.org	0xE40
__d_f3:                                  @@ 0xE40：+0xBC0 ⇒ 落点 0x1A00（.text 近尾）
	br.nz	{rb5}?, [rb0, 0xBC0]
	add.si	rd24, 1
	.org	0x1600
__d_l1:                                  @@ 0x1600：第一例落点
	__PREP_LAND_JUMP	__d_ck_f
__d_ck_f:
	__CHECK_RD         10, rd24, (ENTRY + 0x1600)
	jump	[rb0, __d_b2]
__d_ck_b:
	__CHECK_RD         11, rd24, (ENTRY + 0xA00)
	jump	[rb0, __d_f3]
	.org	0x1A00
__d_l3:                                  @@ 0x1A00：大距离落点
	__PREP_LAND_JUMP	__d_ck_l
	.org	0x1A20
__d_ck_l:
	__CHECK_RD         12, rd24, (ENTRY + 0x1A00)

	__TEST_END

	@@ ---- fault（同镜像故障链：异常不返回到被测指令之后）----

	@@ 目标落在 SRAM 之下（imms18 = -0x20000 ⇒ rb0 - 0x80000）⇒ 取指 CFXMEM
	TEST_FAULT_CF1      13, rb1, 0x0000000000000001, CFXMEM, 0x73060000

	__TEST_SECTIONS
