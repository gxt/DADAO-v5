@@ br.np_riii_rd.S — br.np {rdHA}?, [rb0, imms20]（riii/rd, opc 0x6D）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §1`）；册目录 `tests/inst/06-control-flow/`
@@ id：br.np_riii_rd　形式：riii（rd）　opc：0x6D　mask：0xFF000000　value：0x6D000000
@@ 语义：条件成立 ⇒ 跳转；目标 = rb0 + (SX(imms18) << 2)（64 位计算，结果写回 rb0，
@@   取低 48 位为下一条地址）；不成立 ⇒ 顺序执行 rb0 + 4
@@   判据（`spec/SimRISC-06 §1`）：rdHA <= 0（有符号「非正」）⇒ 条件成立
@@   条件按**整 64 位有符号**判（不是 32 位符号扩展后的值）；rd0 读出 0 ⇒ 成立
@@ 合法性：`contracts/legality_rules.yaml` 对 br.np 无 active 静态规则；源可为 rd0（读出 0）；
@@   目标恒 4 字节对齐（`imms18 << 2`）⇒ 不会触发 IALIGN；imms18 = ±512 KiB ⇒ 可越过
@@   Tiny（8 MiB）SRAM 边界（边界例：目标在 SRAM 之下 ⇒ CFXMEM）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：riii = opc | rdha[23:18] | imms18[17:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`__LI`/`__LI_RB` 拼条件寄存器；**不使用数据区**）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 2 / semantic 5 / overlap 2 / boundary 3（链例 12 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：条件寄存器用 `__LI`/`__LI_RB` 拼常量（被测分支不参与造初值）、期望内联；跳转/不跳
@@   由 rd24 的 1/0 标记判（`TEST_BR1`）；跳转**距离与落点地址**用 `.org` 钉住的槽位 +
@@   `__LAND_IP`（`aip.si` 取 IP）核，期望写 `ENTRY + <字面偏移>`

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1：规范编码字 0x6D040002（rdha = 1 + 「成立」侧的值）⇒ 成立 ⇒ 跳过紧随的 4 B
	__LI	rd1, 0x0000000000000000
	__LI	rd24, 0
	.dd.t32	0x6D040002
	add.si	rd24, 1
	__CHECK_RD          1, rd24, 0

	@@ 点 2：字段边界（rdha = 63，最大寄存器号）+ 同等成立（0x6DFC0002）
	__LI	rd63, 0x0000000000000000
	__LI	rd24, 0
	.dd.t32	0x6DFC0002
	add.si	rd24, 1
	__CHECK_RD          2, rd24, 0

	@@ ---- semantic ----
	@@ 零 ⇒ 成立
	TEST_BR1	3, br.np, rd5, 0x0000000000000000, 1
	@@ 负（-1）⇒ 成立
	TEST_BR1	4, br.np, rd5, 0xFFFFFFFFFFFFFFFF, 1
	@@ INT64_MIN ⇒ 成立
	TEST_BR1	5, br.np, rd5, 0x8000000000000000, 1
	@@ 正 1 ⇒ 不成立
	TEST_BR1	6, br.np, rd5, 0x0000000000000001, 0
	@@ 低 32 位全 1、高 32 位 0（= +4294967295）⇒ 不成立
	TEST_BR1	7, br.np, rd5, 0x00000000FFFFFFFF, 0

	@@ ---- overlap ----
	@@ 同一寄存器连续两条分支：第一条跳过后寄存器未被改写 ⇒ 第二条仍按同值判（零值）
	__LI	rd5, 0x0000000000000000
	__LI	rd24, 0
	br.np	{rd5}?, [rb0, __o1]
	jump	[rb0, __o2]
__o1:
	__LI	rd24, 1
__o2:
	br.np	{rd5}?, [rb0, __o3]
	add.si	rd24, 1
__o3:
	__CHECK_RD         8, rd24, 1

	@@ rd0 作条件（硬连零读出 0）：0 成立
	TEST_BR1       9, br.np, rd0, 0xFFFFFFFFFFFFFFFF, 1

	@@ ---- boundary：跳转距离（`.org` 钉住槽位；零填充只被 jump/分支跨过）----
	__LI	rd5, 0x0000000000000000
	__LI	rd24, 0
	jump	[rb0, __d_f1]
	.org	0xA00
__d_b1:                                  @@ 0xA00：后向字面量分支的落点
	__LAND_IP
	jump	[rb0, __d_ck_b]
	.org	0xE00
__d_f1:                                  @@ 0xE00：+0x800 ⇒ 落点 0x1600
	br.np	{rd5}?, [rb0, 0x800]
	add.si	rd24, 1
	.org	0xE20
__d_b2:                                  @@ 0xE20：-0x420 ⇒ 落点 0xA00
	br.np	{rd5}?, [rb0, -0x420]
	add.si	rd24, 1
	.org	0xE40
__d_f3:                                  @@ 0xE40：+0xBC0 ⇒ 落点 0x1A00（.text 近尾）
	br.np	{rd5}?, [rb0, 0xBC0]
	add.si	rd24, 1
	.org	0x1600
__d_l1:                                  @@ 0x1600：第一例落点
	__LAND_IP
	jump	[rb0, __d_ck_f]
__d_ck_f:
	__CHECK_RD         10, rd24, (ENTRY + 0x1600)
	jump	[rb0, __d_b2]
__d_ck_b:
	__CHECK_RD         11, rd24, (ENTRY + 0xA00)
	jump	[rb0, __d_f3]
	.org	0x1A00
__d_l3:                                  @@ 0x1A00：大距离落点
	__LAND_IP
	jump	[rb0, __d_ck_l]
	.org	0x1A20
__d_ck_l:
	__CHECK_RD         12, rd24, (ENTRY + 0x1A00)

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ 目标落在 SRAM 之下（imms18 = -0x20000 ⇒ rb0 - 0x80000）⇒ 取指 CFXMEM
	TEST_FAULT_CF1      13, rd1, 0x0000000000000000, CFXMEM, 0x6D060000

	__TEST_SECTIONS
