@@ tests/inst/06-control-flow/06-control-flow.inc — **06-control-flow 册专用**宏层（m15-testcases-002 下沉）
@@
@@ 口径：本文件只放**本册**用的宏；跨册宏在 `tests/inst/macros/inst_test.inc`，
@@ 单文件宏直接写在该 `.S` 内（门控 `check-inst-macro-scope` 机械判）。
@@ 本册每个 `.S` 在共享层之后 `.include`：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/06-control-flow/06-control-flow.inc"
@@
.macro TEST_BR2 pt, mnem, a, aval, b, bval, want
	.ifnc	\a, rd0
	__LI	\a, \aval
	.endif
	.ifnc	\b, rd0
	.ifnc	\b, \a
	__LI	\b, \bval
	.endif
	.endif
	__LI	rd24, 0
	\mnem	{\a, \b}?, [rb0, __bt_\@]
	jump	[rb0, __bl_\@]
__bt_\@:
	__LI	rd24, 1
__bl_\@:
	__CHECK_RD \pt, rd24, \want
.endm
.macro TEST_BR1 pt, mnem, r, rval, want
	.ifnc	\r, rd0
	__LI	\r, \rval
	.endif
	__LI	rd24, 0
	\mnem	{\r}?, [rb0, __bt_\@]
	jump	[rb0, __bl_\@]
__bt_\@:
	__LI	rd24, 1
__bl_\@:
	__CHECK_RD \pt, rd24, \want
.endm
.macro TEST_BR1_RB pt, mnem, r, rval, want
	.ifnc	\r, rb0
	__LI_RB	\r, \rval
	.endif
	__LI	rd24, 0
	\mnem	{\r}?, [rb0, __bt_\@]
	jump	[rb0, __bl_\@]
__bt_\@:
	__LI	rd24, 1
__bl_\@:
	__CHECK_RD \pt, rd24, \want
.endm
@@ 落点 IP 捕获（必须紧放在落点第一条指令）：rd24 = IP = 该 `aip.si` 的地址
.macro __LAND_IP
	aip.si	rb24, 0
	rb2rd	{rd24:rd24}, {rb24:rb24}
.endm
@@ 控制流故障例（原始编码；汇编器会拒绝的编码或越界目标）
@@   TEST_FAULT_CF(pt, 故障名, 编码字)
.macro TEST_FAULT_CF pt, fault, enc
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	.dd.t32	\enc
	__EXIT	\pt
	.endif
.endm
@@ 控制流「目标不可取指」故障例：条件成立 ⇒ 跳到 `target`（零字区/非代码区）
@@   TEST_FAULT_BR2(pt, 助记符, A, A值, B, B值, 故障名, 目标)
@@   目标用标签（分支目标走正常重定位，不是立即数常量）⇒ 可用 `TEST_DATA + 偏移`
.macro TEST_FAULT_BR2 pt, mnem, a, aval, b, bval, fault, target
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	__LI	\a, \aval
	.ifnc	\b, \a
	__LI	\b, \bval
	.endif
	\mnem	{\a, \b}?, [rb0, \target]
	__EXIT	\pt
	.endif
.endm
@@ jump/call 的 rrii 形式：目标地址 0（`rbHA = 0`、`rdHB = 0`、`imms12 = 0`）⇒ 取指 CFXMEM
@@   TEST_FAULT_ADDR0(pt, 助记符, 故障名)
.macro TEST_FAULT_ADDR0 pt, mnem, fault
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	__LI_RB	rb5, 0
	__LI	rd6, 0
	\mnem	[rb5, rd6, 0]
	__EXIT	\pt
	.endif
.endm
@@ RAS 故障例：按故障名建立最小 RA 前置，再执行 `inst`（call/ret 的完整文本）
@@   RASOF ⇒ C3b：RACNT = 63、MRPTR = 0、ra63 = [计数 1, 返回地址 0xCCCC00000000]
@@           （返回地址与待压入的不同 ⇒ 不走 C2 折叠，直接落 C3b 溢出）
@@   RASUF ⇒ D4a：RACNT = 0、MRPTR = 0
@@   `inst` 用 `:vararg` 收整段文本（含 `[..]` 内的逗号），如 `call [rb0, 4]`
.macro TEST_FAULT_RAS pt, fault, inst:vararg
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	.ifc	\fault, RASOF
	__LI	rd5, 0x0001CCCC00000000
	rd2ra	{ra63}, {rd5}
	__LI	rd5, 0x003F000000000000
	rd2ra	{ra0}, {rd5}
	.endif
	.ifc	\fault, RASUF
	rd2ra	{ra0}, {rd0}
	.endif
	.ifc	\fault, CFXMEM
	@@ D4b：MemRAS 条目 = {计数 1, 返回地址 0xBBBB00000000（cfxha 46，其它 cfxha 段）}
	@@   ⇒ 消费条目、PC = 该地址；Tiny 只在 cfxha 63/3 映射 ⇒ 取指 CFXMEM（Kaiwu §1.2）
	__LI	rd5, 0x0001BBBB00000000
	LOAD_ADDR rb5, MEMRAS
	st.o	rd5, [rb5, 0]
	__LI	rd5, MEMRAS
	rd2ra	{ra0}, {rd5}
	.endif
	\inst
	__EXIT	\pt
	.endif
.endm

@@ ---------------------------------------------------------------------------
@@ 2 行级结构重复宏（m15-testcases-005；判据 = 净收益 k×n−(n+2+k) > 0，
@@ 宏体只含准备段、0 个检查点 ⇒ 用非用例前缀 `__PREP_*`，`__PT_*` 只留给
@@ 「一行一条用例」的宏）。
@@ ---------------------------------------------------------------------------

.macro __PREP_LAND_JUMP target
	__LAND_IP
	jump	[rb0, \target]
.endm
