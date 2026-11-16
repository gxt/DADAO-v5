@@ tests/inst/05-arith-addr/05-arith-addr.inc — **05-arith-addr 册专用**宏层（m15-testcases-002 下沉）
@@
@@ 口径：本文件只放**本册**用的宏；跨册宏在 `tests/inst/macros/inst_test.inc`，
@@ 单文件宏直接写在该 `.S` 内（门控 `check-inst-macro-scope` 机械判）。
@@ 本册每个 `.S` 在共享层之后 `.include`：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/05-arith-addr/05-arith-addr.inc"
@@
@@ ---------------------------------------------------------------------------
@@ 64 位地址运算（05-arith-addr，`spec/SimRISC-05`）：目的在 RB 银行的三条 id
@@   TEST_AR_BBD(pt, 助记符, 目的RB, 源C-RB, C值, 源D-RD, D值, 期望)
@@     orrr bbd：`add.o/sub.o rbHB, rbHC, rdHD`（目的 rbHB；源 = rbHC + rdHD）
@@   TEST_AR_DBB(pt, 助记符, 目的RD, 源C-RB, C值, 源D-RB, D值, 期望)
@@     orrr dbb：`cmp.uo/sub.o rdHB, rbHC, rbHD`（目的 rdHB；两源都在 RB）
@@   TEST_AR_RB_SI(pt, 助记符, 目的RB, 初值, imms18, 期望)
@@     riii rb：`add.si rbHA, imms18`（目的兼源）
@@   这三条的**目的都只写不读**（不装初值）；源按银行用 `__LI_RB`（rb）/`__LI`（rd）装载，
@@   rd0 作源跳过装载（读出 0）。目的在 RB ⇒ 实测经同组 `st.o` 落到 SCRATCH 再
@@   `__CHECK_MEM`（探针不借被测指令）；目的在 rd ⇒ `__CHECK_RD`。
@@ ---------------------------------------------------------------------------

.macro TEST_AR_BBD pt, mnem, dst, c, cval, d, dval, exp
	__LI_RB	\c, \cval
	.ifnc	\d, rd0
	__LI	\d, \dval
	.endif
	\mnem	\dst, \c, \d
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
.endm

.macro TEST_AR_DBB pt, mnem, dst, c, cval, d, dval, exp
	__LI_RB	\c, \cval
	.ifnc	\d, \c
	__LI_RB	\d, \dval
	.endif
	\mnem	\dst, \c, \d
	__CHECK_RD \pt, \dst, \exp
.endm

@@ 64 位地址运算（`spec/SimRISC-05`）的故障例：源按银行分别装载
.macro TEST_FAULT_BBD pt, mnem, fault, dst, c, d
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	.ifnc	\c, rb0
	__LI_RB	\c, 0x0123456789ABCDEF
	.endif
	.ifnc	\d, rd0
	__LI	\d, 0x0000000000000007
	.endif
	\mnem	\dst, \c, \d
	__EXIT	\pt
	.endif
.endm
.macro TEST_FAULT_DBB pt, mnem, fault, dst, c, d
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	.ifnc	\c, rb0
	__LI_RB	\c, 0x0123456789ABCDEF
	.endif
	.ifnc	\d, rb0
	__LI_RB	\d, 0x0000000000000007
	.endif
	\mnem	\dst, \c, \d
	__EXIT	\pt
	.endif
.endm
.macro TEST_FAULT_RB_SI pt, mnem, fault, dst, imm
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	\mnem	\dst, \imm
	__EXIT	\pt
	.endif
.endm
