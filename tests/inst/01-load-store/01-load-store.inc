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
	set.rb \base, \baseval
	\mnem	\dst, [\base, \off]
	__CHECK_RD \pt, \dst, \exp
.endm

@@ ---------------------------------------------------------------------------
@@ 存储（st.*）：TEST_ST(pt, 助记符, 源, 基址, 基址值, 偏移, 源值, 数据单元期望)
@@   数据单元期望 = 存储后该 8 字节数据单元的完整内容：b/w/t 只改其中几个字节，
@@   其余字节必须保持 ⇒ 同时钉住窄写的字节范围与「不越界写」。
@@ ---------------------------------------------------------------------------

@@ rd 源
.macro TEST_ST pt, mnem, src, base, baseval, off, srcval, unit
	set.rd	\src, \srcval
	set.rb \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \unit
.endm

@@ rf 源（rd → rf 用 orri 复制）
.macro TEST_ST_RF pt, mnem, src, base, baseval, off, srcval, unit
	set.rd	rd20, \srcval
	rd2rf	{\src:\src}, {rd20:rd20}
	set.rb \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \unit
.endm

@@ ---------------------------------------------------------------------------
@@ 多元素（ldm.*/stm.*，rrri）：一个组 ↔ 内存多点（`spec/SimRISC-01 §1-4`）
@@   TEST_LDM(pt, 助记符, 组, 基址, 基址值, 偏移寄存器, 偏移值, 回写区, 数据单元数, 期望数据单元...)
@@   TEST_STM(pt, 助记符, 组别, 组, 基址, 基址值, 偏移寄存器, 偏移值, 源区, 期望数据单元...)
@@
@@ 判据（一行 = 一个检查点，失败 ⇒ `SYS_EXIT(pt)`）：
@@   * `TEST_LDM`：装入后用**同宽度、同组**的 `stm.*` 把该组回写到 `回写区`（通常
@@     `MDUMP` 零区），再逐 8 字节数据单元与内联期望比较 —— 元素不跨数据单元（宽度整除 8 且起址
@@     宽度对齐），所以「数据单元 = 若干元素」的字节布局是确定的；末尾记录最后一个数据单元实测。
@@   * `TEST_STM`：先用**同宽度、同组**的 `ldm.*` 从 `源区` 预装该组，再执行存储，逐个数据单元
@@     与内联期望比较（期望里同时含相邻「保持字节」⇒ 顺带钉住不越界写）。
@@   组 = 寄存器范围文本（`{rd5:rd8}`）；寄存器组别由组名自身给出（rd/rb/ra/rf）。
@@   数据单元数由调用者给出并与期望数据单元个数强制相等（漏写数据单元 ⇒ `.error`）；`TEST_LDM` 的
@@   回写区必须是「本文件尚未写过」的零区（尾巴不足一个数据单元的字节按 0 比），故各例按
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
.macro TEST_LDM pt, mnem, grp, base, baseval, offreg, offval, dump, nb, units:vararg
	set.rd	\offreg, \offval
	set.rb \base, \baseval
	\mnem	\grp, [\base, \offreg]
	set.rb rb28, \dump
	__DMP_STM \mnem, \grp, rb28, rd0
	.set	__ne, 0
	.irp	v, \units
	.set	__ne, __ne + 1
	.endr
	.if	__ne != \nb
	.error	"TEST_LDM: 期望数据单元个数与数据单元数不符"
	.endif
	.set	__b, 0
	.irp	v, \units
	set.rb rb21, \dump + (8 * __b)
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
.macro TEST_STM pt, mnem, bank, grp, base, baseval, offreg, offval, src, units:vararg
	set.rb rb28, \src
	__PRE_LDM \mnem, \bank, \grp, rb28, rd0
	set.rd	\offreg, \offval
	set.rb \base, \baseval
	\mnem	\grp, [\base, \offreg]
	.set	__b, 0
	.irp	v, \units
	set.rb rb21, (((\baseval) + (\offval) + 8 * __b) / 8) * 8
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
	set.rb \base, \baseval
	\mnem	\reg, [\base, \off]
	@@ 走到这里 = 预期故障没有发生 ⇒ 仍按该例检查点号判 guest FAIL
	__FAULT_BODY_END \pt
.endm

@@ ---------------------------------------------------------------------------
@@ 未对齐访问的「无副作用」故障例（`spec/SimRISC-01 §1` 的 IDL：MALIGN 在写目的 /
@@   写存储器**之前** raise ⇒ 单元素 ld 的目的、单元素 st 的目标数据单元均保持原值；
@@   用户 2026-11-13 裁定「单元素 ld/st 仍须精确」）。
@@ 机制：公共故障落点 `__pad` 只核 cause 后跳后继例，本类例需要「异常返回后」再核，
@@   故把固件 hmon 的返回槽（hmon 数据页 +0x18，`spec/Kaiwu §6.2`「框架可覆盖」）改写成
@@   用例自己的核对点；核对点用 `__VERIFY_*`（不占检查点）后再跳回 `__pad` ——
@@   cause 槽/`TEST_FAULTV` 都没被改动，公共落点仍按点号查 `.faulttab` 走下一例。
@@   装返回地址用 `set.rd`（标签只能进 64 位立即数）+ `rd2rb`（不经被测指令）。
@@ ---------------------------------------------------------------------------
.macro __SET_HMON_RETURN_TO lbl
	set.rd	rd19, \lbl
	rd2rb	{rb21:rb21}, {rd19:rd19}
	set.rb	rb20, HMON_DATA_BASE
	st.o	rb21, [rb20, HMON_FRAME_RETURN]
.endm

@@ ld.*：未对齐 ⇒ MALIGN，且目的寄存器不被写（保持调用前预置值）
.macro TEST_FAULT_LD_MALIGN_KEEPDST pt, mnem, dst, dstval, base, baseval, off
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, MALIGN
	set.rd	\dst, \dstval
	set.rb	\base, \baseval
	__SET_HMON_RETURN_TO __mal_keepdst_\pt
	\mnem	\dst, [\base, \off]
	__FAULT_BODY_END \pt
__mal_keepdst_\pt:
	__VERIFY_RD \pt, \dst, \dstval
	jump	[rb0, __pad]
.endm

@@ st.*：未对齐 ⇒ MALIGN，且目标 8 字节数据单元不被写（`cell` = 数据单元偏移，对齐；
@@   `off` = 未对齐的 EA 偏移；预置用对齐 st.o，核对用 ld.o —— 两条独立通路）
.macro TEST_FAULT_ST_MALIGN_KEEPMEM pt, mnem, src, srcval, base, baseval, off, cell, cellval
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, MALIGN
	set.rb	\base, \baseval
	set.rd	rd19, \cellval
	st.o	rd19, [\base, \cell]
	set.rd	\src, \srcval
	__SET_HMON_RETURN_TO __mal_keepmem_\pt
	\mnem	\src, [\base, \off]
	__FAULT_BODY_END \pt
__mal_keepmem_\pt:
	__VERIFY_MEM \pt, \baseval, \cell, \cellval
	jump	[rb0, __pad]
.endm
@@ 多元素（rrri）故障例：只比异常码（多元素指令允许部分元素已生效，用户 2026-11-13 裁定）
@@   TEST_FAULT_M(pt, 助记符, 组, 故障名, 基址, 基址值, 偏移寄存器, 偏移值)
.macro TEST_FAULT_M pt, mnem, grp, fault, base, baseval, offreg, offval
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	set.rb \base, \baseval
	set.rd	\offreg, \offval
	\mnem	\grp, [\base, \offreg]
	__FAULT_BODY_END \pt
.endm

@@ ---------------------------------------------------------------------------
@@ `rb0` 作**基址**（`spec/SimRISC-00 §2`：rb0 读出 = **当前指令地址** IP，非「下一条」；
@@   `spec/SimRISC-01` 只禁 `rb0` 作**目的**）—— 零档（`imm`/偏移寄存器 = 0）用例：
@@   EA = **被测指令自身地址** ⇒ 目标是**指令字**，期望值只能现场派生：用**同一条指令、
@@   同宽度**经显式基址（`aip.si` 取 IP 再 +4/+8）读同一地址，逐位相等即断言
@@   「EA = 当前指令地址」（若实现取「下一条」，两侧 EA 相差 4 ⇒ 不等 ⇒ 判红）。
@@   调用点由 `.org` 钉住被测指令地址（见各 `.S` 的 `__rb0z` 段；64 位形式须 8 B 对齐）。
@@   宏名带 `__CHECK_` ⇒ 一行宏调用 = 一个检查点（失败点号 = 用例序号）。
@@ ---------------------------------------------------------------------------

@@ ld.*（rrii）零档：`mnem dst, [rb0, 0]` vs `mnem tmp, [rb12, 4]`
.macro __CHECK_RD_IP pt, mnem, dst, tmp, bank
	aip.si	rb12, 0
	\mnem	\dst, [rb0, 0x000]
	add.si	rd2, 0			@@ 填充：让「下一条」处的字节与本指令不同（判别 IP 口径）
	\mnem	\tmp, [rb12, 0x004]
	.ifc	\bank, rd
	rd2rd	{rd21:rd21}, {\dst:\dst}
	rd2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	.ifc	\bank, rb
	rb2rd	{rd21:rd21}, {\dst:\dst}
	rb2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	.ifc	\bank, ra
	ra2rd	{rd21:rd21}, {\dst:\dst}
	ra2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	.ifc	\bank, rf
	rf2rd	{rd21:rd21}, {\dst:\dst}
	rf2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	__REC	rd21
	br.eq	{rd21, rd22}?, [rb0, __ipok_\@]
	__EXIT	\pt
__ipok_\@:
.endm

@@ ldm.*（rrri）零档：偏移寄存器取 rd0（= 0）⇒ EA = 自身；读回用显式基址 + 偏移 8
.macro __CHECK_RD_LDM_IP pt, mnem, reg, tmp, bank
	aip.si	rb12, 0
	set.rd	rd19, 0x008
	\mnem	{\reg:\reg}, [rb0, rd0]
	add.si	rd2, 0			@@ 填充：让「下一条」处的字节与本指令不同（判别 IP 口径）
	\mnem	{\tmp:\tmp}, [rb12, rd19]
	.ifc	\bank, rd
	rd2rd	{rd21:rd21}, {\reg:\reg}
	rd2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	.ifc	\bank, rb
	rb2rd	{rd21:rd21}, {\reg:\reg}
	rb2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	.ifc	\bank, ra
	ra2rd	{rd21:rd21}, {\reg:\reg}
	ra2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	.ifc	\bank, rf
	rf2rd	{rd21:rd21}, {\reg:\reg}
	rf2rd	{rd22:rd22}, {\tmp:\tmp}
	.endif
	__REC	rd21
	br.eq	{rd21, rd22}?, [rb0, __ipok_\@]
	__EXIT	\pt
__ipok_\@:
.endm

@@ st.*（rrii，8 B 宽）零档：EA = 自身地址 ⇒ 8 字节数据单元的低 32 位是**其后的指令字**，
@@   必须原样保留：先读回原数据单元、只改写高 32 位的两个 wyde 再写回；读回与写入值相等
@@   即断言「store 落在自身地址」。调用点 `.org` 钉住预读指令（被测 st 在 +0x10）。
.macro __CHECK_RD_ST_IP pt, mnem, src, bank
	ld.o	rd2, [rb0, 0x010]		@@ 预读被测 st.o 处的 8 字节数据单元
	andn.w	rd2, wp2, 0xFFFF		@@ 高 32 位改写 ⇒ 写入值与原地不同
	or.w	rd2, wp3, 0x0001
	.ifc	\bank, rb
	set.rb	\src, rd2
	.endif
	.ifc	\bank, ra
	rd2ra	{\src:\src}, {rd2:rd2}
	.endif
	.ifc	\bank, rf
	set.rf	\src, rd2
	.endif
	.ifc	\bank, rd
	rd2rd	{\src:\src}, {rd2:rd2}
	.endif
	\mnem	\src, [rb0, 0x000]		@@ 被测：EA = 自身指令地址（8 字节数据单元）
	ld.o	rd21, [rb0, -0x004]		@@ 独立通路读回（自身 IP − 4）
	__REC	rd21
	br.eq	{rd2, rd21}?, [rb0, __ipok_\@]
	__EXIT	\pt
__ipok_\@:
.endm

@@ stm.*（rrri，8 B 宽）零档：同上（偏移寄存器 rd0 = 0 ⇒ EA = 自身地址）
.macro __CHECK_RD_STM_IP pt, mnem, src, bank
	ld.o	rd2, [rb0, 0x010]
	andn.w	rd2, wp2, 0xFFFF
	or.w	rd2, wp3, 0x0001
	.ifc	\bank, rb
	set.rb	\src, rd2
	.endif
	.ifc	\bank, ra
	rd2ra	{\src:\src}, {rd2:rd2}
	.endif
	.ifc	\bank, rf
	set.rf	\src, rd2
	.endif
	.ifc	\bank, rd
	rd2rd	{\src:\src}, {rd2:rd2}
	.endif
	\mnem	{\src:\src}, [rb0, rd0]		@@ 被测：EA = 自身指令地址（8 字节数据单元）
	ld.o	rd21, [rb0, -0x004]
	__REC	rd21
	br.eq	{rd2, rd21}?, [rb0, __ipok_\@]
	__EXIT	\pt
__ipok_\@:
.endm
