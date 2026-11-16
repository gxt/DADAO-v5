@@ tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc — **04-arith-logic-octa 册专用**宏层（m15-testcases-002 下沉）
@@
@@ 口径：本文件只放**本册**用的宏；跨册宏在 `tests/inst/macros/inst_test.inc`，
@@ 单文件宏直接写在该 `.S` 内（门控 `check-inst-macro-scope` 机械判）。
@@ 本册每个 `.S` 在共享层之后 `.include`：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/04-arith-logic-octa/04-arith-logic-octa.inc"
@@
.macro TEST_AR_DUAL pt, mnem, hi, lo, hiinit, loinit, c, cval, d, dval, exphi, explo
	.ifnc	\hi, rd0
	__LI	\hi, \hiinit
	.endif
	.ifnc	\lo, rd0
	__LI	\lo, \loinit
	.endif
	.ifnc	\c, rd0
	.ifnc	\c, \hi
	.ifnc	\c, \lo
	__LI	\c, \cval
	.endif
	.endif
	.endif
	.ifnc	\d, rd0
	.ifnc	\d, \hi
	.ifnc	\d, \lo
	.ifnc	\d, \c
	__LI	\d, \dval
	.endif
	.endif
	.endif
	.endif
	\mnem	{\hi, \lo}, \c, \d
	@@ 被丢弃的一半（目的 = rd0）无从核对 ⇒ 点号落在留下的那一半
	.ifnc	\hi, rd0
	.ifnc	\lo, rd0
	__VERIFY_RD \pt, \hi, \exphi
	.endif
	.endif
	.ifnc	\lo, rd0
	__CHECK_RD  \pt, \lo, \explo
	.else
	__CHECK_RD  \pt, \hi, \exphi
	.endif
.endm
.macro TEST_AR_CMPI pt, mnem, dst, dstinit, b, bval, imm, exp
	.ifnc	\dst, rd0
	__LI	\dst, \dstinit
	.endif
	.ifnc	\b, rd0
	.ifnc	\b, \dst
	__LI	\b, \bval
	.endif
	.endif
	\mnem	\dst, \b, \imm
	__CHECK_RD \pt, \dst, \exp
.endm
.macro TEST_FAULT_DUAL pt, mnem, fault, hi, lo, c, d
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	__FAULT_LOAD_SRC \c, 0x0123456789ABCDEF
	__FAULT_LOAD_SRC \d, 0x0000000000000007
	\mnem	{\hi, \lo}, \c, \d
	__EXIT	\pt
	.endif
.endm
.macro TEST_FAULT_ALU_CMPI pt, mnem, fault, dst, b, imm
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	__FAULT_LOAD_SRC \b, 0x0123456789ABCDEF
	\mnem	\dst, \b, \imm
	__EXIT	\pt
	.endif
.endm
