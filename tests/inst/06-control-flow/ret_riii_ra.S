@@ ret_riii_ra.S — ret rdHA, imms18（riii/ra, opc 0x76）
@@ 大类：06-control-flow（控制流，`spec/SimRISC-06 §4`）；册目录 `tests/inst/06-control-flow/`
@@ id：ret_riii_ra　形式：riii（ra）　opc：0x76　mask：0xFF000000　value：0x76000000
@@ 语义：从返回地址栈弹出返回地址并跳转（来源**可能不是 ra63**，取决于 RAS 状态，
@@   `spec/SimRISC-00 §2.4.2`）；同时把 `imms18` 符号扩展到 64 位写进 rdHA（返回值）
@@   弹栈判定：D1 计数 0 ⇒ RASUF；D2 计数 > 1 ⇒ 计数减 1、RACNT 不变；D3 计数 = 1 ⇒
@@   弹出栈顶、RACNT 减 1；D4 `RACNT == 0` ⇒ D4a MRPTR = 0 ⇒ RASUF / D4b 读 MemRAS 条目
@@ 合法性：`dst_rd0_nonzero`（`contracts/legality_rules.yaml`）：rdHA == rd0 时 imms18
@@   **必须**为 0（汇编期硬报错；运行期执行该非法编码 ⇒ ILLI）；rdHA ≠ rd0 时 imms18 任意
@@   另：弹栈可能触发 **RASUF**（动态）
@@ 编码：字段位域见 `contracts/opcodes.yaml`：riii = opc | rdha[23:18] | imms18[17:0]
@@ 数据块：`tests/inst/macros/inst_test.inc`（MEMRAS = TEST_DATA + 0x1700：D4b 的 MemRAS 条目）
@@ 链接布局：`tests/inst/01-load-store/inst-tiny.lds`（ENTRY 由 `machine-tiny.inc` 固定）
@@ 用例：encoding 2 / semantic 8 / overlap 1 / boundary 7（链例 18 + 故障例 5）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：RA 状态用 `rd2ra` 全 64 位写建立（`ra0[53:48]` = RACNT、`[47:0]` = MRPTR，
@@   `ra1`–`ra63` = 计数/返回地址）；弹出后落点 IP 用 `aip.si` 取、ra63/ra0 用 `ra2rd` 读
@@   ⇒ 全部**只读**观测，期望值内联（链接期地址写 `ENTRY + <偏移>`）；
@@   每个 ret 之后紧跟 `__EXIT <点号>`：ret 若未跳转（弹栈失效）→ 直接按该点号判红

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/inst/06-control-flow/06-control-flow.inc"

@@ ---- 文件专用宏（m15-testcases-002 下沉；只被本文件使用）----
@@ MemRAS 下溢（D4b）：ra0 = {RACNT = 0, MRPTR = MEMRAS}、MemRAS[MRPTR] 的递归计数 = 0
.macro TEST_FAULT_RASUF_MEM pt, inst:vararg
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, RASUF
	__LI	rd5, 0
	LOAD_ADDR rb5, MEMRAS
	st.o	rd5, [rb5, 0]           @@ MemRAS[MRPTR] 的递归计数 = 0
	__LI	rd5, MEMRAS              @@ MRPTR = MEMRAS、RACNT = 0（高 16 位 = 0）
	rd2ra	{ra0}, {rd5}
	\inst
	__EXIT	\pt
	.endif
.endm

	__TEST_BEGIN

	@@ ---- encoding ----
	@@ 点 1/2：规范编码字 0x76000000（ret rd0, 0）作为被调函数的返回 ⇒ 弹回 call+4、
	@@   RACNT 归 0；若未弹栈/未跳转，ra0 仍为 1 ⇒ 点 2 判红
	rd2ra	{ra0}, {rd0}
	__LI	rd24, 0
	call	[rb0, __enc]
__enc_ret:
	jump	[rb0, __enc_ck]
__enc:
	__LI	rd24, 1
	.dd.t32	0x76000000
	__EXIT	1
__enc_ck:
	__CHECK_RD          1, rd24, 1
	ra2rd	{rd25}, {ra0}
	__CHECK_RD          2, rd25, 0

	@@ ---- semantic：D3（计数 = 1 ⇒ 弹出栈顶、RACNT 2→1）----
	__LI	rd5, 0x0002000000000000
	rd2ra	{ra0}, {rd5}
	__LI	rd5, (0x0001000000000000 + ENTRY + 0x800)
	rd2ra	{ra63}, {rd5}
	__LI	rd5, 0x0001AAAA00000000
	rd2ra	{ra62}, {rd5}
	ret	rd0, 0
	__EXIT	3
	.org	0x800
__lD3:                                   @@ 0x800：D3 的落点
	__LAND_IP
	jump	[rb0, __ckD3]
	.org	0x820
__ckD3:
	__CHECK_RD          3, rd24, (ENTRY + 0x800)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD          4, rd25, 0x0001AAAA00000000
	ra2rd	{rd26}, {ra0}
	__CHECK_RD          5, rd26, 0x0001000000000000

	@@ semantic：D2（计数 > 1 ⇒ 计数减 1、RACNT 不变）
	__LI	rd5, 0x0001000000000000
	rd2ra	{ra0}, {rd5}
	__LI	rd5, (0x0002000000000000 + ENTRY + 0xA00)
	rd2ra	{ra63}, {rd5}
	ret	rd0, 0
	__EXIT	6
	.org	0xA00
__lD2:                                   @@ 0xA00：D2 的落点
	__LAND_IP
	jump	[rb0, __ckD2]
	.org	0xA20
__ckD2:
	__CHECK_RD          6, rd24, (ENTRY + 0xA00)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD          7, rd25, (0x0001000000000000 + ENTRY + 0xA00)
	ra2rd	{rd26}, {ra0}
	__CHECK_RD          8, rd26, 0x0001000000000000

	@@ semantic：返回值写入 rdHA（imms18 = 42，rdHA ≠ rd0 ⇒ 无约束）
	__LI	rd5, 0x0001000000000000
	rd2ra	{ra0}, {rd5}
	__LI	rd5, (0x0001000000000000 + ENTRY + 0xC00)
	rd2ra	{ra63}, {rd5}
	ret	rd5, 42
	__EXIT	9
	.org	0xC00
__lR42:                                  @@ 0xC00：返回值例的落点
	__LAND_IP
	jump	[rb0, __ckR42]
	.org	0xC20
__ckR42:
	__CHECK_RD          9, rd5, 0x000000000000002A
	__CHECK_RD         10, rd24, (ENTRY + 0xC00)

	@@ ---- boundary：返回值按 imms18 符号扩展到 64 位（-1 ⇒ 全 1）----
	__LI	rd5, 0x0001000000000000
	rd2ra	{ra0}, {rd5}
	__LI	rd5, (0x0001000000000000 + ENTRY + 0xE00)
	rd2ra	{ra63}, {rd5}
	ret	rd5, -1
	__EXIT	11
	.org	0xE00
__lRm1:                                  @@ 0xE00：符号扩展例的落点
	__LAND_IP
	jump	[rb0, __ckRm1]
	.org	0xE20
__ckRm1:
	__CHECK_RD         11, rd5, 0xFFFFFFFFFFFFFFFF
	__CHECK_RD         12, rd24, (ENTRY + 0xE00)

	@@ ---- overlap：目的 = rd0（imms18 必须为 0，`dst_rd0_nonzero`）—— 跳转照常 ----
	__LI	rd5, 0x0001000000000000
	rd2ra	{ra0}, {rd5}
	__LI	rd5, (0x0001000000000000 + ENTRY + 0x1000)
	rd2ra	{ra63}, {rd5}
	ret	rd0, 0
	__EXIT	13
	.org	0x1000
__lR0:                                   @@ 0x1000：rd0 目的例的落点
	__LAND_IP
	jump	[rb0, __ckR0]
	.org	0x1020
__ckR0:
	__CHECK_RD         13, rd24, (ENTRY + 0x1000)

	@@ ---- boundary：D4b 取 MemRAS 条目（RACNT = 0、MRPTR ≠ 0）----
	@@ 条目计数 > 1 ⇒ 该条目压入成为栈顶（计数 −1）、MRPTR += 8、RACNT = 1
	__LI	rd5, (0x0003000000000000 + ENTRY + 0x1200)
	LOAD_ADDR rb5, MEMRAS
	st.o	rd5, [rb5, 0]           @@ MemRAS[MRPTR] = {计数 3, 返回地址 0x1200}
	__LI	rd5, MEMRAS              @@ ra0 = {RACNT = 0, MRPTR = MEMRAS}
	rd2ra	{ra0}, {rd5}
	ret	rd0, 0
	__EXIT	14
	.org	0x1200
__lD4b:                                  @@ 0x1200：D4b（计数 > 1）的落点
	__LAND_IP
	jump	[rb0, __ckD4b]
	.org	0x1240
__ckD4b:
	__CHECK_RD         14, rd24, (ENTRY + 0x1200)
	ra2rd	{rd25}, {ra63}
	__CHECK_RD         15, rd25, (0x0002000000000000 + ENTRY + 0x1200)  @@ 计数 3→2、成为栈顶
	ra2rd	{rd26}, {ra0}
	__CHECK_RD         16, rd26, (0x0001000000000000 + MEMRAS + 8)       @@ RACNT=1、MRPTR += 8

	@@ 条目计数 = 1 ⇒ 消费该条目（MRPTR += 8、RACNT 仍 0、RegRAS 不变）
	__LI	rd5, (0x0001000000000000 + ENTRY + 0x1400)
	LOAD_ADDR rb5, MEMRAS
	st.o	rd5, [rb5, 0]
	__LI	rd5, MEMRAS
	rd2ra	{ra0}, {rd5}
	ret	rd0, 0
	__EXIT	17
	.org	0x1400
__lD4b1:                                 @@ 0x1400：D4b（计数 = 1）的落点
	__LAND_IP
	jump	[rb0, __ckD4b1]
	.org	0x1440
__ckD4b1:
	__CHECK_RD         17, rd24, (ENTRY + 0x1400)
	ra2rd	{rd26}, {ra0}
	__CHECK_RD         18, rd26, (MEMRAS + 8)                            @@ MRPTR += 8、RACNT 仍 0

	__TEST_END

	@@ ---- fault（一例一镜像：异常不返回到被测指令之后）----

	@@ dst_rd0_nonzero：ret rd0, 1（imms18 ≠ 0）⇒ ILLI（汇编器拒绝该编码，直接给编码字）
	TEST_FAULT_CF      19, ILLI, 0x76000001

	@@ dst_rd0_nonzero：ret rd0, -1（imms18 = 0x3FFFF）⇒ ILLI
	TEST_FAULT_CF      20, ILLI, 0x7603FFFF

	@@ D4a：RACNT = 0 且 MRPTR = 0 ⇒ RASUF（精确异常：RA 保持原状）
	TEST_FAULT_RAS     21, RASUF, ret rd0, 0

	@@ D4b：RACNT = 0、MRPTR = MEMRAS，条目递归计数 = 0 ⇒ RASUF
	TEST_FAULT_RASUF_MEM 22, ret rd0, 0

	@@ D4b + 其它 cfxha 段：MemRAS 条目 = {计数 1, 返回地址 0xBBBB00000000}（cfxha 46）
	@@   ⇒ 消费该条目、PC = 0xBBBB00000000；Tiny 只在 cfxha 63 / 3 有映射，其它 cfxha 段
	@@   取指 ⇒ CFXMEM（`spec/Kaiwu §1.2`；退出码编码 `§7.1` = 0xF1）
	TEST_FAULT_RAS     23, CFXMEM, ret rd0, 0

	__TEST_SECTIONS
