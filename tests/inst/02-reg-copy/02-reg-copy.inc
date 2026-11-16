@@ tests/inst/02-reg-copy/02-reg-copy.inc — **02-reg-copy 册专用**宏层（m15-testcases-002 下沉）
@@
@@ 口径：本文件只放**本册**用的宏；跨册宏在 `tests/inst/macros/inst_test.inc`，
@@ 单文件宏直接写在该 `.S` 内（门控 `check-inst-macro-scope` 机械判）。
@@ 本册每个 `.S` 在共享层之后 `.include`：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/02-reg-copy/02-reg-copy.inc"
@@
.macro TEST_MOV1 pt, mnem, dst, src, exp
	\mnem	{\dst:\dst}, {\src:\src}
	.ifc	\mnem, rd2rd
	__CHECK_RD \pt, \dst, \exp
	.endif
	.ifc	\mnem, rb2rd
	__CHECK_RD \pt, \dst, \exp
	.endif
	.ifc	\mnem, ra2rd
	__CHECK_RD \pt, \dst, \exp
	.endif
	.ifc	\mnem, rf2rd
	__CHECK_RD \pt, \dst, \exp
	.endif
	.ifc	\mnem, rb2rb
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
	.endif
	.ifc	\mnem, rd2rb
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
	.endif
	.ifc	\mnem, rd2ra
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
	.endif
	.ifc	\mnem, rd2rf
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
	.endif
	.ifc	\mnem, rf2rf
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
	.endif
.endm
@@ ---------------------------------------------------------------------------
@@ 条件赋值（rrrr；`spec/SimRISC-02 §2`）
@@   TEST_CS1(pt, 助记符, 条件寄存器, 条件值, 目的, 目的初值,
@@            「成立」侧寄存器, 值, 「不成立」侧寄存器, 值, 期望)
@@     cs.n/cs.z/cs.p（目的 rdHB）：条件成立 ⇒ 目的 = 「成立」侧（rdHC），否则 = rdHD
@@   TEST_CS2(pt, 助记符, a, a 值, b, b 值, 目的, 目的初值, 赋值源, 源值, 期望)
@@     cs.eq/cs.ne（目的 rdHC）：条件成立 ⇒ 目的 = 赋值源（rdHD），否则目的不变
@@   TEST_CS1_RF(pt, 助记符, 条件寄存器, 条件值, 目的 rf, 目的初值偏移,
@@               候选 rf, 偏移, 候选 rf, 偏移, 期望)
@@     cs.n/z/p 的 rf 变体：目的与候选都在 rf 组，初值经 RDATA 装载、期望经落点比
@@   「未被选中侧不被改写」由用例内的 `__VERIFY_*` 断言（本组宏只判目的）；
@@   条件寄存器与目的/候选同名的别名语义按 C-27 deferred，用例一律不同名。
@@ ---------------------------------------------------------------------------

.macro TEST_CS1 pt, mnem, cond, condval, dst, dstinit, tc, tcval, td, tdval, exp
	@@ 条件寄存器可为 rd0（硬连零）：写 rd0 会触发 ILLI（dst_rd0），故跳过装载
	.ifnc	\cond, rd0
	__LI	\cond, \condval
	.endif
	__LI	\dst, \dstinit
	__LI	\tc, \tcval
	__LI	\td, \tdval
	\mnem	{\cond}?, \dst, \tc, \td
	__CHECK_RD \pt, \dst, \exp
.endm

.macro TEST_CS2 pt, mnem, a, aval, b, bval, dst, dstinit, d, dval, exp
	@@ 比较操作数可为 rd0（硬连零）：写 rd0 会触发 ILLI（dst_rd0），故跳过装载
	.ifnc	\a, rd0
	__LI	\a, \aval
	.endif
	.ifnc	\b, rd0
	__LI	\b, \bval
	.endif
	__LI	\dst, \dstinit
	__LI	\d, \dval
	\mnem	{\a, \b}?, \dst, \d
	__CHECK_RD \pt, \dst, \exp
.endm

.macro TEST_CS1_RF pt, mnem, cond, condval, dst, dstoff, tc, tcoff, td, tdoff, exp
	.ifnc	\cond, rd0
	__LI	\cond, \condval
	.endif
	__SET_MEM \dst, \dstoff
	__SET_MEM \tc, \tcoff
	__SET_MEM \td, \tdoff
	\mnem	{\cond}?, \dst, \tc, \td
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
.endm

@@ 块复制故障例（寄存器操作数形式；组文本原样给出，如 `{rd0}` / `{rb0}`）
@@   TEST_FAULT_MOV(pt, 助记符, 目的组, 故障名, 源组)
.macro TEST_FAULT_MOV pt, mnem, dstg, fault, srcg
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	\mnem	\dstg, \srcg
	__EXIT	\pt
	.endif
.endm
@@ 条件赋值故障例（第一类 `cs.n/z/p`）
@@   TEST_FAULT_CS(pt, 助记符, 目的, 故障名, 条件寄存器, 「成立」侧, 「不成立」侧)
.macro TEST_FAULT_CS pt, mnem, dst, fault, cond, tc, td
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	\mnem	{\cond}?, \dst, \tc, \td
	__EXIT	\pt
	.endif
.endm
@@ 条件赋值故障例（第二类 `cs.eq/ne`：两个比较操作数分开给，组文本里的逗号会断参数）
@@   TEST_FAULT_CS2(pt, 助记符, 目的, 故障名, a, b, 赋值源)
.macro TEST_FAULT_CS2 pt, mnem, dst, fault, a, b, d
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	\mnem	{\a, \b}?, \dst, \d
	__EXIT	\pt
	.endif
.endm
