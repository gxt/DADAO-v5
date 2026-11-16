@@ call_rrii_ra.S — call [rbHA, rdHB, imms14]（rrii/ra, opc 0x75）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §3`）；册目录 `tests/inst/06-control-flow/`
@@ id：call_rrii_ra　形式：rrii（ra）　opc：0x75　mask：0xFF000000　value：0x75000000
@@ 语义：目标 = rbHA + rdHB + (SX(imms12) << 2)（64 位计算，结果写回 rb0，取低 48 位）；
@@   同时把**返回地址 = 该 call 指令地址 + 4** 压入 RAS（两种形式一致）；rbHA **仅读**
@@   特例（`spec/SimRISC-06 §3`）：ha = rb0 时 `rdHB + (imms12 << 2)` 仍是相对跳转
@@ 合法性：无静态规则；压栈可能触发 **RASOF**（RACNT == 63 且 MRPTR == 0）；目标恒
@@   4 字节对齐 ⇒ 不会触发 IALIGN；基址可为 0 ⇒ 目标地址 0 ⇒ 取指 CFXMEM
@@ 编码：字段位域见 `contracts/opcodes.yaml`：rrii = opc | rbha[23:18] | rdhb[17:12] | imms12[11:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（`set.rb`/`set.rd` 拼基址与偏移寄存器）
@@ 链接布局：`tests/inst/linker/inst-tiny.lds`（全部册共用（00 + 01–12）；ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 1 / semantic 11 / overlap 2（链例 14 + 故障例 2）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：call 与 RAS 只读可观测（`ra2rd` 读 ra63/ra0、`aip.si` 取落点 IP）；RA 状态用
@@   `rd2ra` 建立（`ra0[53:48]` = RACNT、`[47:0]` = MRPTR）；期望值内联
@@ 布局：槽位（call 本体）与落点/检查块按 **执行顺序** 交替排布，`.org` 钉住地址

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1：规范编码字 0x75000002（rbha = rb0、rdhb = rd0、imms12 = 2 ⇒ +8）⇒ 跳过 4 B
	set.rd	rd24, 0
	.dd.t32	0x75000002
	add.si	rd24, 1
	__CHECK_RD          1, rd24, 0

	@@ ---- semantic（自然 call/ret 配对）：压栈→弹栈后 RACNT 归 0 ----
	rd2ra	{ra0}, {rd0}
	set.rd	rd24, 0
	call	[rb0, __fx]
__fx_ret:
	jump	[rb0, __fx_ck]
__fx:
	set.rd	rd24, 1
	ret	rd0, 0
__fx_ck:
	__CHECK_RD          2, rd24, 1
	ra2rd	{rd25}, {ra0}
	__CHECK_RD          3, rd25, 0

	@@ ---- overlap ----
	@@ 基址与偏移都取 0 号寄存器（rb0 在 rrii 里是相对基址、rd0 读出 0）⇒ 退化为相对调用
	rd2ra	{ra0}, {rd0}
	set.rd	rd24, 0
	call	[rb0, rd0, 8]
	add.si	rd24, 1
	__CHECK_RD          4, rd24, 0        @@ +8 ⇒ 跳过后面的 add.si（rd24 保持 0）
	ra2rd	{rd26}, {ra0}
	__CHECK_RD          5, rd26, 0x0001000000000000   @@ 未返回 ⇒ RACNT = 1

	@@ ---- semantic：基址 + 寄存器偏移 + 立即数（`.org` 钉住槽位）----
	set.rb	rb5, (ENTRY + 0x900)
	set.rd	rd6, 0x40
	rd2ra	{ra0}, {rd0}            @@ 冷栈
	jump	[rb0, __slotA]
	.org	0x800
__slotA:                                 @@ 0x800：基址 ENTRY+0x900 + 0x40 + 0 ⇒ 落点 0x940
	call	[rb5, rd6, 0]
	.org	0x940
__lA:                                     @@ 0x940：落点
	__PREP_LAND_JUMP	__ckA
	.org	0x980
__ckA:
	__CHECK_RD          6, rd24, (ENTRY + 0x940)          @@ 落点地址
	ra2rd	{rd25}, {ra63}
	__CHECK_RD          7, rd25, (0x0001000000000000 + ENTRY + 0x804)  @@ 返回地址 + 计数 1
	ra2rd	{rd26}, {ra0}
	__CHECK_RD          8, rd26, 0x0001000000000000       @@ RACNT = 1

	@@ semantic：rb0 作基址的特例（`rdHB + (imms12 << 2)` 是相对跳转）
	rd2ra	{ra0}, {rd0}            @@ 清栈（上一例压入的条目不复用）
	set.rd	rd6, 0x40
	jump	[rb0, __slotB]
	.org	0xB00
__slotB:                                 @@ 0xB00：rb0 + 0x40 + 0x40 ⇒ 落点 0xB80
	call	[rb0, rd6, 0x40]
	.org	0xB80
__lB:                                     @@ 0xB80：落点
	__PREP_LAND_JUMP	__ckB
	.org	0xBC0
__ckB:
	__CHECK_RD          9, rd24, (ENTRY + 0xB80)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD         10, rd25, (0x0001000000000000 + ENTRY + 0xB04)
	ra2rd	{rd26}, {ra0}
	__CHECK_RD         11, rd26, 0x0001000000000000

	@@ semantic（C2 递归折叠：栈顶返回地址 == 本 call 的返回地址 ⇒ 只加计数）
	set.rd	rd6, 0x40
	set.rd	rd5, (0x0001000000000000 + ENTRY + 0xE04)
	rd2ra	{ra63}, {rd5}
	set.rd	rd5, 0x0001000000000000
	rd2ra	{ra0}, {rd5}
	jump	[rb0, __slotC]
	.org	0xE00
__slotC:                                 @@ 0xE00：rb0 + 0x40 + 0 ⇒ 落点 0xE40（返回地址 0xE04 = 栈顶）
	call	[rb0, rd6, 0]
	.org	0xE40
__lC:                                     @@ 0xE40：落点
	__PREP_LAND_JUMP	__ckC
	.org	0xE80
__ckC:
	__CHECK_RD         12, rd24, (ENTRY + 0xE40)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD         13, rd25, (0x0002000000000000 + ENTRY + 0xE04)  @@ 计数 1→2
	ra2rd	{rd26}, {ra0}
	__CHECK_RD         14, rd26, 0x0001000000000000       @@ RACNT 不变（仍 1）

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ 目标地址 0（rb5 = 0、rd6 = 0、imms12 = 0）⇒ 取指 CFXMEM
	TEST_FAULT_ADDR0   15, call, CFXMEM

	@@ C3b：RACNT = 63 且 MRPTR = 0、栈顶返回地址 ≠ 本条 call 的返回地址 ⇒ RASOF
	@@   （C3b 的「溢出到 MemRAS」分支见 `call_iiii_ra.S` 点 15–18：压栈流程与形式无关）
	TEST_FAULT_RAS     16, RASOF, call [rb5, rd6, 4]

	__TEST_SECTIONS
