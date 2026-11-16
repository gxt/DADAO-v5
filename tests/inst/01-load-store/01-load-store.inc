@@ tests/inst/01-load-store/01-load-store.inc — **01-load-store 册专用**宏层（m15-testcases-002 下沉）
@@
@@ 口径：本文件只放**本册**用的宏；跨册宏在 `tests/inst/macros/inst_test.inc`，
@@ 单文件宏直接写在该 `.S` 内（门控 `check-inst-macro-scope` 机械判）。
@@ 本册每个 `.S` 在共享层之后 `.include`：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/01-load-store/01-load-store.inc"
@@
@@ ---------------------------------------------------------------------------
@@ 装入（ld.*）：TEST_LD(pt, 助记符, 目的, 基址, 基址值, 偏移, 期望)
@@   每次重新装载基址寄存器 ⇒ 每个用例自包含，可单独阅读。
@@ ---------------------------------------------------------------------------

@@ rd 目的
.macro TEST_LD pt, mnem, dst, base, baseval, off, exp
	LOAD_ADDR \base, \baseval
	\mnem	\dst, [\base, \off]
	__CHECK_RD \pt, \dst, \exp
.endm

@@ ---------------------------------------------------------------------------
@@ 存储（st.*）：TEST_ST(pt, 助记符, 源, 基址, 基址值, 偏移, 源值, beat 期望)
@@   beat 期望 = 存储后该 8 字节 beat 的完整内容：b/w/t 只改其中几个字节，
@@   其余字节必须保持 ⇒ 同时钉住字节通道与「不越界写」。
@@ ---------------------------------------------------------------------------

@@ rd 源
.macro TEST_ST pt, mnem, src, base, baseval, off, srcval, beat
	set.rd	\src, \srcval
	LOAD_ADDR \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \beat
.endm

@@ rf 源（rd → rf 用 orri 复制）
.macro TEST_ST_RF pt, mnem, src, base, baseval, off, srcval, beat
	set.rd	rd20, \srcval
	rd2rf	{\src:\src}, {rd20:rd20}
	LOAD_ADDR \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \beat
.endm

@@ ---------------------------------------------------------------------------
@@ 多元素（ldm.*/stm.*，rrri）：一个组 ↔ 内存多点（`spec/SimRISC-01 §1-4`）
@@   TEST_LDM(pt, 助记符, 组, 基址, 基址值, 偏移寄存器, 偏移值, 回写区, 拍数, 期望拍...)
@@   TEST_STM(pt, 助记符, 组别, 组, 基址, 基址值, 偏移寄存器, 偏移值, 源区, 期望拍...)
@@
@@ 判据（一行 = 一个检查点，失败 ⇒ `SYS_EXIT(pt)`）：
@@   * `TEST_LDM`：装入后用**同宽度、同组**的 `stm.*` 把该组回写到 `回写区`（通常
@@     `MDUMP` 零区），再逐 8 字节拍与内联期望比较 —— 元素不跨拍（宽度整除 8 且起址
@@     宽度对齐），所以「拍 = 若干元素」的字节布局是确定的；末尾记录最后一拍实测。
@@   * `TEST_STM`：先用**同宽度、同组**的 `ldm.*` 从 `源区` 预装该组，再执行存储，逐拍
@@     与内联期望比较（期望里同时含相邻「保持字节」⇒ 顺带钉住不越界写）。
@@   组 = 寄存器范围文本（`{rd5:rd8}`）；寄存器组别由组名自身给出（rd/rb/ra/rf）。
@@   拍数由调用者给出并与期望拍个数强制相等（漏写拍 ⇒ `.error`）；`TEST_LDM` 的
@@   回写区必须是「本文件尚未写过」的零区（尾巴不足一拍的字节按 0 比），故各例按
@@   各自的偏移分段使用（见各 `.S` 的 `MDUMP + 0x…`）。
@@ 依赖：`TEST_LDM` 的回写借 `stm.*`、`TEST_STM` 的预装借 `ldm.*`（互为逆操作）；
@@   抽样元素另有 `__CHECK_RD` 独立核对（见各 `.S`），不依赖这一对。
@@ ---------------------------------------------------------------------------

@@ 助记符 → 同宽度 `stm.*`（回写用）；组文本原样沿用
.macro __DMP_STM mnem, grp, base, off
	.ifc	\mnem, ldm.ub
	stm.b	\grp, [\base, \off]
	.endif
	.ifc	\mnem, ldm.sb
	stm.b	\grp, [\base, \off]
	.endif
	.ifc	\mnem, ldm.uw
	stm.w	\grp, [\base, \off]
	.endif
	.ifc	\mnem, ldm.sw
	stm.w	\grp, [\base, \off]
	.endif
	.ifc	\mnem, ldm.ut
	stm.t	\grp, [\base, \off]
	.endif
	.ifc	\mnem, ldm.st
	stm.t	\grp, [\base, \off]
	.endif
	.ifc	\mnem, ldm.o
	stm.o	\grp, [\base, \off]
	.endif
	.ifc	\mnem, ldm.t
	stm.t	\grp, [\base, \off]
	.endif
	.ifc	\mnem, stm.t
	stm.t	\grp, [\base, \off]
	.endif
	.ifc	\mnem, stm.o
	stm.o	\grp, [\base, \off]
	.endif
.endm

@@ 助记符 → 同宽度 `ldm.*`（预装用）；组文本原样沿用（宽度 + 组别共同决定助记符：
@@ b/w/t 的 RD 形式是 `ldm.ub/uw/ut`，而 RF 只有 `ldm.t`）
.macro __PRE_LDM mnem, bank, grp, base, off
	.ifc	\mnem, stm.b
	ldm.ub	\grp, [\base, \off]
	.endif
	.ifc	\mnem, stm.w
	ldm.uw	\grp, [\base, \off]
	.endif
	.ifc	\mnem, stm.t
	.ifc	\bank, rf
	ldm.t	\grp, [\base, \off]
	.endif
	.ifc	\bank, rd
	ldm.ut	\grp, [\base, \off]
	.endif
	.endif
	.ifc	\mnem, stm.o
	ldm.o	\grp, [\base, \off]
	.endif
.endm

@@ 多元素装入
.macro TEST_LDM pt, mnem, grp, base, baseval, offreg, offval, dump, nb, beats:vararg
	set.rd	\offreg, \offval
	LOAD_ADDR \base, \baseval
	\mnem	\grp, [\base, \offreg]
	LOAD_ADDR rb28, \dump
	__DMP_STM \mnem, \grp, rb28, rd0
	.set	__ne, 0
	.irp	v, \beats
	.set	__ne, __ne + 1
	.endr
	.if	__ne != \nb
	.error	"TEST_LDM: 期望拍个数与拍数不符"
	.endif
	.set	__b, 0
	.irp	v, \beats
	LOAD_ADDR rb21, \dump + (8 * __b)
	ld.o	rd21, [rb21, 0]
	set.rd	rd20, \v
	br.ne	{rd20, rd21}?, [rb0, __lmbad_\@]
	.set	__b, __b + 1
	.endr
	__REC	rd21
	jump	[rb0, __lmdone_\@]
__lmbad_\@:
	__EXIT	\pt
__lmdone_\@:
.endm

@@ 多元素存储
.macro TEST_STM pt, mnem, bank, grp, base, baseval, offreg, offval, src, beats:vararg
	LOAD_ADDR rb28, \src
	__PRE_LDM \mnem, \bank, \grp, rb28, rd0
	set.rd	\offreg, \offval
	LOAD_ADDR \base, \baseval
	\mnem	\grp, [\base, \offreg]
	.set	__b, 0
	.irp	v, \beats
	LOAD_ADDR rb21, (((\baseval) + (\offval) + 8 * __b) / 8) * 8
	ld.o	rd21, [rb21, 0]
	set.rd	rd20, \v
	br.ne	{rd20, rd21}?, [rb0, __smbad_\@]
	.set	__b, __b + 1
	.endr
	__REC	rd21
	jump	[rb0, __smdone_\@]
__smbad_\@:
	__EXIT	\pt
__smdone_\@:
.endm

.macro TEST_FAULT pt, mnem, reg, fault, base, baseval, off
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	LOAD_ADDR \base, \baseval
	\mnem	\reg, [\base, \off]
	@@ 走到这里 = 预期故障没有发生 ⇒ 仍按该例检查点号判 guest FAIL
	__FAULT_BODY_END \pt
.endm
@@ 多元素（rrri）故障例：只比异常码（多元素指令允许部分元素已生效，用户 2026-11-13 裁定）
@@   TEST_FAULT_M(pt, 助记符, 组, 故障名, 基址, 基址值, 偏移寄存器, 偏移值)
.macro TEST_FAULT_M pt, mnem, grp, fault, base, baseval, offreg, offval
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	LOAD_ADDR \base, \baseval
	set.rd	\offreg, \offval
	\mnem	\grp, [\base, \offreg]
	__FAULT_BODY_END \pt
.endm
