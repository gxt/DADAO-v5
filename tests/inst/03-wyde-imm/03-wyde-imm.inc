@@ tests/inst/03-wyde-imm/03-wyde-imm.inc — **03-wyde-imm 册专用**宏层（m15-testcases-002 下沉）
@@
@@ 口径：本文件只放**本册**用的宏；跨册宏在 `tests/inst/macros/inst_test.inc`，
@@ 单文件宏直接写在该 `.S` 内（门控 `check-inst-macro-scope` 机械判）。
@@ 本册每个 `.S` 在共享层之后 `.include`：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/03-wyde-imm/03-wyde-imm.inc"
@@
@@ ---------------------------------------------------------------------------
@@ 16 位立即数操作（rwii；`spec/SimRISC-03 §1`）：一行 = 一个检查点
@@   TEST_WI_RD(pt, 助记符, 目的 rd, wpN, immu16, 初值, 期望)
@@   TEST_WI_RB(pt, 助记符, 目的 rb, wpN, immu16, 初值, 期望)
@@   TEST_WI_RF(pt, 助记符, 目的 rf, wpN, immu16, 初值, 期望)
@@   TEST_WI_{RD,RB,RF}_MEM(pt, 助记符, 目的, wpN, immu16, 初值, WDATA 偏移)
@@ 判据：目的在 rd ⇒ 直接比；在 rb/rf ⇒ 同组 `st.o` 落到 SCRATCH 再逐字节比
@@   （探针不借被测的立即数指令）。`_MEM` 变体的**期望从 WDATA 装载**（不经任何 rwii
@@   指令）—— `set.rd` 自身用 set.zw/set.ow/or.w/andn.w 拼常量，故该变体防「期望由被测指令自证」。
@@ 初值装载：rd 用 `set.rd`、rb 用 `set.rb`、rf 用 `set.fo`（复制指令，独立于本册）。
@@ ---------------------------------------------------------------------------

.macro TEST_WI_RD pt, mnem, dst, wp, imm, init, exp
	set.rd	\dst, \init
	\mnem	\dst, \wp, \imm
	__CHECK_RD \pt, \dst, \exp
.endm

.macro TEST_WI_RB pt, mnem, dst, wp, imm, init, exp
	set.rb	\dst, \init
	\mnem	\dst, \wp, \imm
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
.endm

.macro TEST_WI_RD_MEM pt, mnem, dst, wp, imm, init, off
	set.rd	\dst, \init
	\mnem	\dst, \wp, \imm
	set.rb rb21, WDATA + \off
	ld.o	rd20, [rb21, 0]
	__REC	\dst
	br.eq	{rd20, \dst}?, [rb0, __wrm_\@]
	__EXIT	\pt
__wrm_\@:
.endm

.macro TEST_WI_RB_MEM pt, mnem, dst, wp, imm, init, off
	set.rb	\dst, \init
	\mnem	\dst, \wp, \imm
	st.o	\dst, [rb29, 0]
	set.rb rb21, WDATA + \off
	ld.o	rd20, [rb21, 0]
	ld.o	rd21, [rb29, 0]
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __wrm_\@]
	__EXIT	\pt
__wrm_\@:
.endm

@@ rf0（FCSR）的 `set.w` 写语义（`spec/SimRISC-03 §1` 注 + `spec/SimRISC-00` 写语义：
@@   只更新 [33:32]（舍入模式）与 [4:0]（异常状态），其余位写无效）
@@   TEST_WI_RF0_NOOP(pt, wpN, immu16)：wp1/wp3 完全写无效 ⇒ 写前后 rf0 逐位相等。
@@   TEST_WI_RF0_WRITE(pt, wpN, immu16)：wp2/wp0 只写各自可写域 —— 前置先把该域清 0，
@@     期望 = 写前值对应字节 + 写入增量（其余 7 字节不变），逐字节比。大端下
@@     [39:32] = 第 3 字节（[33:32] 是其低 2 位）、[7:0] = 第 7 字节（[4:0] 是其低 5 位）。
@@   前置写若被实现忽略，期望字节也会跟着错 ⇒ 断言必红（fail-closed，不会假绿）。
@@ ---------------------------------------------------------------------------

@@ 16 位立即数操作故障例（rwii：目的 rd0/rb0 ⇒ ILLI）
@@   TEST_FAULT_WI(pt, 助记符, 目的, 故障名, wpN, immu16)
.macro TEST_FAULT_WI pt, mnem, dst, fault, wp, imm
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	\mnem	\dst, \wp, \imm
	__FAULT_BODY_END \pt
.endm
