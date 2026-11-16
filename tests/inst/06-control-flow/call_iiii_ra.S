@@ call_iiii_ra.S — call [rb0, imms26]（iiii/ra, opc 0x74）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §3`）；册目录 `tests/inst/06-control-flow/`
@@ id：call_iiii_ra　形式：iiii（ra）　opc：0x74　mask：0xFF000000　value：0x74000000
@@ 语义：目标 = rb0 + (SX(imms24) << 2)（64 位计算，结果写回 rb0，取低 48 位为下一条地址）；
@@   同时把**返回地址 = 该 call 指令地址 + 4** 压入返回地址栈（RAS，`spec/SimRISC-00 §2.4`），
@@   条目 = {[63:48] 递归计数（首次压栈 = 1）、[47:0] 返回地址}；RACNT 记在 `ra0[53:48]`
@@ 合法性：`contracts/legality_rules.yaml`：无静态规则；压栈可能触发 **RASOF**（动态：
@@   RACNT == 63 且 MRPTR == 0）；目标恒 4 字节对齐 ⇒ 不会触发 IALIGN
@@ 编码：字段位域见 `contracts/opcodes.yaml`：iiii = opc | imms24[23:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（本文件只用寄存器）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 1 / semantic 12 / boundary 5（链例 18 + 故障例 1）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：call 与返回地址栈都是**只读**可观测（`ra2rd` 读 ra63/ra62/ra0、`aip.si` 取落点 IP）；
@@   RA 状态用 `rd2ra` 全 64 位写 **建立**（RA 组无 rd0 约束、`ra0` 的 [53:48] = RACNT、
@@   [47:0] = MRPTR，`spec/SimRISC-00 §2.4.4`），期望值内联（链接期地址写 `ENTRY + <偏移>`）
@@ 布局：槽位（call 本体）与落点/检查块按 **执行顺序** 交替排布，`.org` 钉住地址

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1：规范编码字 0x74000002（imms24 = 2 ⇒ +8）⇒ 压入 A+4、跳到 A+8 ⇒ 跳过 4 B
	__LI	rd24, 0
	.dd.t32	0x74000002
	add.si	rd24, 1
	__CHECK_RD          1, rd24, 0

	@@ ---- semantic（自然 call/ret 配对）：压栈→弹栈后 RACNT 归 0 ----
	rd2ra	{ra0}, {rd0}            @@ RACNT = 0、MRPTR = 0（干净栈）
	__LI	rd24, 0
	call	[rb0, __fx]
__fx_ret:
	jump	[rb0, __fx_ck]
__fx:
	__LI	rd24, 1
	ret	rd0, 0
__fx_ck:
	__CHECK_RD          2, rd24, 1
	ra2rd	{rd25}, {ra0}
	__CHECK_RD          3, rd25, 0

	@@ ---- semantic：C1 冷栈压栈 + 返回地址写 ra63 + RACNT（`.org` 钉住槽位）----
	rd2ra	{ra0}, {rd0}            @@ 冷栈
	jump	[rb0, __slot1]
	.org	0x800
__slot1:                                 @@ 0x800：call ⇒ 压入 0x804、落到 0x840
	call	[rb0, 0x40]
	.org	0x840
__l1:                                    @@ 0x840：C1 的落点
	__PREP_LAND_JUMP	__ck1
	.org	0x880
__ck1:
	__CHECK_RD          4, rd24, (ENTRY + 0x840)          @@ 落点地址
	ra2rd	{rd25}, {ra63}
	__CHECK_RD          5, rd25, (0x0001000000000000 + ENTRY + 0x804)  @@ 返回地址 + 计数 1
	ra2rd	{rd26}, {ra0}
	__CHECK_RD          6, rd26, 0x0001000000000000       @@ RACNT = 1

	@@ semantic（C2 递归折叠：栈顶返回地址 == 本 call 的返回地址 ⇒ 只加计数）
	__LI	rd5, (0x0001000000000000 + ENTRY + 0xA04)
	rd2ra	{ra63}, {rd5}
	__LI	rd5, 0x0001000000000000
	rd2ra	{ra0}, {rd5}            @@ RACNT = 1
	jump	[rb0, __slot2]
	.org	0xA00
__slot2:                                 @@ 0xA00：call ⇒ 压入 0xA04（= 栈顶）、落到 0xA40
	call	[rb0, 0x40]
	.org	0xA40
__l2:                                    @@ 0xA40：C2 的落点
	__PREP_LAND_JUMP	__ck2
	.org	0xA80
__ck2:
	__CHECK_RD          7, rd24, (ENTRY + 0xA40)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD          8, rd25, (0x0002000000000000 + ENTRY + 0xA04)  @@ 计数 1→2
	ra2rd	{rd26}, {ra0}
	__CHECK_RD          9, rd26, 0x0001000000000000       @@ RACNT 不变（仍 1）

	@@ semantic（C3a 压栈：栈顶返回地址 ≠ 本 call 的返回地址 ⇒ 旧顶下移 ra62）
	__LI	rd5, 0x0001AAAA00000000
	rd2ra	{ra63}, {rd5}
	__LI	rd5, 0x0001000000000000
	rd2ra	{ra0}, {rd5}            @@ RACNT = 1
	jump	[rb0, __slot3]
	.org	0xC00
__slot3:                                 @@ 0xC00：call ⇒ 压入 0xC04、落到 0xC40
	call	[rb0, 0x40]
	.org	0xC40
__l3:                                    @@ 0xC40：C3a 的落点
	__PREP_LAND_JUMP	__ck3
	.org	0xC80
__ck3:
	__CHECK_RD         10, rd24, (ENTRY + 0xC40)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD         11, rd25, (0x0001000000000000 + ENTRY + 0xC04)  @@ 新栈顶
	ra2rd	{rd25}, {ra62}
	__CHECK_RD         12, rd25, 0x0001AAAA00000000       @@ 旧栈顶下移
	ra2rd	{rd26}, {ra0}
	__CHECK_RD         13, rd26, 0x0002000000000000       @@ RACNT 1→2

	@@ ---- boundary：最小距离 +4（目标与返回地址重合）----
	jump	[rb0, __slot4]
	.org	0x1000
__slot4:                                 @@ 0x1000：目标 = 返回地址 = 0x1004
	call	[rb0, 4]
	.org	0x1004
__l4:                                    @@ 0x1004：落点（= 返回地址）
	__PREP_LAND_JUMP	__ck4
	.org	0x1020
__ck4:
	__CHECK_RD         14, rd24, (ENTRY + 0x1004)

	@@ ---- boundary：C3b 溢出到 MemRAS（满栈 + MRPTR ≠ 0 ⇒ 最旧条目落 MemRAS）----
	__LI	rd5, 0x0005DDDD00000000
	rd2ra	{ra1}, {rd5}            @@ RACNT = 63 时最旧条目下标 = 64 − RACNT = 1
	__LI	rd5, 0x0001CCCC00000000
	rd2ra	{ra63}, {rd5}           @@ 栈顶返回地址 ≠ 本条 call 的返回地址（不走 C2）
	__LI	rd5, (0x003F000000000000 + MEMRAS + 0x80)   @@ RACNT = 63、MRPTR = MEMRAS+0x80
	rd2ra	{ra0}, {rd5}
	jump	[rb0, __slot5]
	.org	0x1200
__slot5:                                 @@ 0x1200：满栈 call ⇒ 最旧条目落 MRPTR−8、压新条目
	call	[rb0, 0x40]
	.org	0x1240
__l5:                                    @@ 0x1240：C3b 的落点
	__PREP_LAND_JUMP	__ck5
	.org	0x1280
__ck5:
	__CHECK_RD         15, rd24, (ENTRY + 0x1240)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD         16, rd25, (0x0001000000000000 + ENTRY + 0x1204)
	ra2rd	{rd26}, {ra0}
	__CHECK_RD         17, rd26, (0x003F000000000000 + MEMRAS + 0x78)   @@ MRPTR −= 8
	LOAD_ADDR rb5, (MEMRAS + 0x78)
	ld.o	rd5, [rb5, 0]
	__CHECK_RD         18, rd5, 0x0005DDDD00000000       @@ 最旧条目已落 MemRAS

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ C3b：RACNT = 63 且 MRPTR = 0、栈顶返回地址 ≠ 本条 call 的返回地址 ⇒ RASOF（精确异常，
	@@   RA 与内存均保持异常前状态）
	TEST_FAULT_RAS     19, RASOF, call [rb0, 4]

	__TEST_SECTIONS
