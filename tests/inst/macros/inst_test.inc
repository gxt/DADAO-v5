@@ tests/inst/macros/inst_test.inc — `tests/inst/<册>/<id>.S` 的汇编宏层
@@
@@ 目的（`tests/inst/MIGRATION.md` §3）：一个 opcode id 一个 `.S`，一行一个用例，
@@ **期望值内联**。用例失败 ⇒ `SYS_EXIT(检查点号)`：guest FAIL 段 `0x01`–`0x7F`，
@@ 值 = 失败点序号（`spec/Machine-v5 §7.1`）；机器异常例 ⇒ `SYS_EXIT(0xF0|异常位索引)`，
@@ 即 Tiny（运行模式恒 `hypv`）的 monitor 段编码：CFXMEM `0xF1`、CFXREG `0xF2`、
@@ ILLI `0xF8`、MALIGN `0xFC`、IALIGN `0xFD`。
@@
@@ 一个 `.S` = 两种镜像形态，由汇编符号 `CASE_N` 选择（`llvm-mc -defsym CASE_N=<n>`）：
@@
@@   CASE_N = 0（缺省）= **链例镜像**：encoding / legality（非故障）/ semantic /
@@     boundary / overlap 逐例顺序执行。每个检查点把**实测的 8 字节**写进结果缓冲，
@@     末尾用 `SYS_WRITEC` 逐字节打印该缓冲并 `SYS_EXIT(0)`。三方（chipyard / QEMU /
@@     gem5）比较的就是这串字节 ⇒ **逐字节一致**，而不只是退出码一致。
@@
@@   CASE_N = <检查点> = **故障例镜像**：`_start` 直接跳到该例。该例执行一条会触发
@@     同步异常的指令，由**测试自己的** hmon 处理器把 `cause_id` 交回落点，落点核对
@@     one-hot 后 `SYS_EXIT(0xF0|位索引)`。故障例必须一例一镜像——异常不返回到
@@     被测指令之后，因此同一个镜像无法继续下一例。
@@
@@ 为什么自装 hmon 处理器：hmon 的「保存-跳转」由 BootROM 固件提供，而固件的分派
@@ 策略随版本变化（芯片侧 BootROM hex 与 QEMU/gem5 装载的 `bootrom_tiny.bin` 可能
@@ 不同版）。测试程序在运行期把本文件的处理器拷到 hmon SRAM 基址（`excp_vector`
@@ 初值 = hmon SRAM 起始，`spec/Machine-v5 §4.4`），于是三方行为一致，同时仍然走
@@ 硬件异常入口（向量 → 异常帧 → `escape`），不是软件模拟。
@@
@@ 保留寄存器（用例不得占用）：rb3=数据基址、rb30=结果缓冲写指针、
@@ rd20/rd21/rb21=期望/实测/临时、rd22/rd23=临时与退出码、
@@ rd31/rb31=故障处理器暂存、rd16/rb16=semihosting、r?4/rd4=退出参数块。
@@
@@ 固定地址（Tiny；`.lds` 的 ASSERT 与本节 `.equ` 共同钉住）：
@@   ENTRY+0x0000 .. +0x1E00  .text          链例 + 故障例体
@@   ENTRY+0x1E00             .hmon_stub     测试自有 hmon 处理器（≤64 B）
@@   ENTRY+0x1F00             .faultpad      故障落点（≤128 B）
@@   ENTRY+0x1F80             TEST_FAULTV    故障期望槽：+0 one-hot、+8 退出码、
@@                                           +16 失败码（=检查点号）、+32 实测 one-hot
@@   ENTRY+0x2000 .. +0x4000  .testdata     数据块（TEST_DATA = +0x2800，0x800 负偏移
@@                                           区在前；单元素 24 拍模式；多元素区见下）
@@   ENTRY+0x4000 .. +0x4800  结果字节缓冲（每检查点 8 字节，≤127 点 ⇒ ≤1016 B）
@@   ENTRY+0x5000             SYS_EXIT 参数块
@@
@@ 副作用口径（用户 2026-11-13 裁定，`ldm`/`stm`/`r2r` 等多寄存器/多元素指令）：
@@   **不要求无副作用** —— 这类指令**允许部分元素已经生效**（「源/目范围不得重叠」正是为此）；
@@   chipyard **无需整段预检**。故多元素故障例（`TEST_FAULT_M`/`TEST_FAULT_ENC`）
@@   **只比异常码**（`SYS_EXIT(0xF0|位索引)`），不对目的寄存器/目标内存做哨兵断言；
@@   `.S` 注释一律写「允许部分生效」，不得写「不写任何元素 / 第一拍之前」之类断言。
@@   **单元素 `ld`/`st` 仍须精确**（`012` 的 `TEST_FAULT` 路径不变，不动）。
@@   另：中途总线 `denied` 不可构造（`ISS-381` F-c；`m12-chipyard-008` 已定其语义为 `CFXMEM`）。
@@
@@ 多元素（ldm.*/stm.*）数据区（TEST_DATA 内偏移，均 8 字节对齐；字面量由本节
@@ `.testdata` 现场生成，与 012 单元素用例使用的 0x000-0x0E8 区互不重叠）：
@@   +0x800  MDATA_B   256 个字节 0x80..0xBF 循环（高位置 1 ⇒ ub/sb 各一档）
@@   +0x900  MDATA_W   128 个 16 位元素 0x8000..0x807F
@@   +0xA00  MDATA_T   64 个 32 位元素 0x80000000..0x8000003F
@@   +0xB00  MDATA_O   64 个 64 位元素 0x0102030405060708 + i（拍内字节互不相同）
@@   +0xD00  MUNI      64 个同值拍 0x0F1E2D3C4B5A6978（最大个数例用；字节互不相同）
@@   +0xF00  MDUMP     512 B 零区（多元素装入后的回写落点）
@@   +0x1100 MSTORE    64 拍保持区模式 0xC0DE0000000000A0 + i（多元素存储落点）
@@   （`TEST_DATA+0x0C0`..`+0x800` 保持全零：单元素用例的零区读数依赖它）

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	@@ 机器几何一律取 `machine-tiny.inc`（生成物）里的符号，本节只补本宏层的布局。
	.equ TEST_HSEC,   ENTRY + 0x1E00
	.equ TEST_PAD,    ENTRY + 0x1F00
	.equ TEST_DATA,   ENTRY + 0x2800
	.equ TEST_BUF,    ENTRY + 0x4000
	.equ TEST_EXITB,  ENTRY + 0x5000
	.equ TEST_FAULTV, ENTRY + 0x1F80        @@ 故障期望槽（4 × 8 B；见文件头）

@@ 多元素数据区（见文件头；偏移相对 TEST_DATA）
	.equ MDATA_B, TEST_DATA + 0x800
	.equ MDATA_W, TEST_DATA + 0x900
	.equ MDATA_T, TEST_DATA + 0xA00
	.equ MDATA_O, TEST_DATA + 0xB00
	.equ MUNI,    TEST_DATA + 0xD00
	.equ MDUMP,   TEST_DATA + 0xF00
	.equ MSTORE,  TEST_DATA + 0x1100

@@ semihosting：服务号在 rd16、参数块指针在 rb16、trap 标签 0x3FF00+服务号
@@ （`contract-semihosting` §1/§2）。
	.equ SEMIHOST_TAG, 0x3FF00
	.equ SYS_WRITEC,   0x03
	.equ SYS_EXIT,     0x18
	.equ ADP_STOPPED_APP_EXIT, 0x20026

@@ 没有 -defsym CASE_N 时按链例镜像（0）处理。
	.ifndef CASE_N
	.equ CASE_N, 0
	.endif

@@ 链例检查点数（收尾据此决定结果缓冲的字节数）。
	.set	__NCHECK, 0

@@ ---------------------------------------------------------------------------
@@ 基本构件
@@ ---------------------------------------------------------------------------

@@ 64 位立即数 → rd（定长 4 条：wp0 用 set.zw 清零，wp1..3 用 or.w 拼装）
.macro __LI rd, val
	set.zw	\rd, wp0, ((\val) & 0xFFFF)
	or.w	\rd, wp1, (((\val) >> 16) & 0xFFFF)
	or.w	\rd, wp2, (((\val) >> 32) & 0xFFFF)
	or.w	\rd, wp3, (((\val) >> 48) & 0xFFFF)
.endm

@@ 64 位立即数 → rb
.macro __LI_RB rb, val
	set.zw	\rb, wp0, ((\val) & 0xFFFF)
	or.w	\rb, wp1, (((\val) >> 16) & 0xFFFF)
	or.w	\rb, wp2, (((\val) >> 32) & 0xFFFF)
	or.w	\rb, wp3, (((\val) >> 48) & 0xFFFF)
.endm

@@ SYS_EXIT(code)（参数块 {ADP_Stopped_ApplicationExit, code}，`contract-semihosting` §3/§5）
.macro __EXIT code
	LOAD_ADDR rb16, TEST_EXITB
	__LI	rd4, ADP_STOPPED_APP_EXIT
	st.o	rd4, [rb16, 0]
	__LI	rd4, \code
	st.o	rd4, [rb16, 8]
	set.zw	rd16, wp0, SYS_EXIT
	trap	cfx0, (SEMIHOST_TAG + SYS_EXIT)
	.dd.t32	0
.endm

@@ 结果缓冲追加 8 字节实测值（rb30 是移动写指针），并记一个检查点
.macro __REC reg
	st.o	\reg, [rb30, 0]
	add.si	rb30, 8
	.set	__NCHECK, __NCHECK + 1
.endm

@@ 逐字节打印 [ptr, ptr+len)（SYS_WRITEC：按长度，不吃 NUL 终止）
.macro __PRINT ptr, len
	LOAD_ADDR rb16, \ptr
	set.zw	rd16, wp0, SYS_WRITEC
	set.zw	rd17, wp0, \len
__pl_\@:
	trap	cfx0, (SEMIHOST_TAG + SYS_WRITEC)
	add.si	rb16, 1
	add.si	rd17, -1
	br.nz	{rd17}?, [rb0, __pl_\@]
.endm

@@ ---------------------------------------------------------------------------
@@ 检查点：期望 vs 实测；不等 ⇒ SYS_EXIT(检查点号)；相等 ⇒ 记录实测值
@@ ---------------------------------------------------------------------------

@@ rd 银行实测（被测指令的目的就是 rd）
.macro __CHECK_RD pt, dst, exp
	__LI	rd20, \exp
	__REC	\dst
	br.eq	{rd20, \dst}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ 内存实测：以 EA 所在 8 字节 beat（EA/8*8）为单位比较（大端）
.macro __CHECK_MEM pt, baseval, off, exp
	LOAD_ADDR rb21, (((\baseval) + (\off)) / 8) * 8
	ld.o	rd21, [rb21, 0]
	__LI	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

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

@@ rb 目的（实测经 rb2rd 搬到 rd21）
.macro TEST_LD_RB pt, mnem, dst, base, baseval, off, exp
	LOAD_ADDR \base, \baseval
	\mnem	\dst, [\base, \off]
	rb2rd	{rd21:rd21}, {\dst:\dst}
	__LI	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ ra 目的
.macro TEST_LD_RA pt, mnem, dst, base, baseval, off, exp
	LOAD_ADDR \base, \baseval
	\mnem	\dst, [\base, \off]
	ra2rd	{rd21:rd21}, {\dst:\dst}
	__LI	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ rf 目的，64 位全比（ld.o）
.macro TEST_LD_RF pt, mnem, dst, base, baseval, off, exp
	LOAD_ADDR \base, \baseval
	\mnem	\dst, [\base, \off]
	rf2rd	{rd21:rd21}, {\dst:\dst}
	__LI	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ rf 目的，只比低 32 位（ld.t 存单精：高 32 位不做特殊规定 ⇒ 不据以判失败）
.macro TEST_LD_RF_LO32 pt, mnem, dst, base, baseval, off, exp
	LOAD_ADDR \base, \baseval
	\mnem	\dst, [\base, \off]
	rf2rd	{rd21:rd21}, {\dst:\dst}
	ext.uo	rd21, rd21, 31
	__LI	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ ---------------------------------------------------------------------------
@@ 存储（st.*）：TEST_ST(pt, 助记符, 源, 基址, 基址值, 偏移, 源值, beat 期望)
@@   beat 期望 = 存储后该 8 字节 beat 的完整内容：b/w/t 只改其中几个字节，
@@   其余字节必须保持 ⇒ 同时钉住字节通道与「不越界写」。
@@ ---------------------------------------------------------------------------

@@ rd 源
.macro TEST_ST pt, mnem, src, base, baseval, off, srcval, beat
	__LI	\src, \srcval
	LOAD_ADDR \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \beat
.endm

@@ rb 源
.macro TEST_ST_RB pt, mnem, src, base, baseval, off, srcval, beat
	__LI_RB	\src, \srcval
	LOAD_ADDR \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \beat
.endm

@@ ra 源（rd → ra 用 orri 复制；基址寄存器不得与源同名）
.macro TEST_ST_RA pt, mnem, src, base, baseval, off, srcval, beat
	__LI	rd20, \srcval
	rd2ra	{\src:\src}, {rd20:rd20}
	LOAD_ADDR \base, \baseval
	\mnem	\src, [\base, \off]
	__CHECK_MEM \pt, \baseval, \off, \beat
.endm

@@ rf 源（rd → rf 用 orri 复制）
.macro TEST_ST_RF pt, mnem, src, base, baseval, off, srcval, beat
	__LI	rd20, \srcval
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
	__LI	\offreg, \offval
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
	__LI	rd20, \v
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
	__LI	\offreg, \offval
	LOAD_ADDR \base, \baseval
	\mnem	\grp, [\base, \offreg]
	.set	__b, 0
	.irp	v, \beats
	LOAD_ADDR rb21, (((\baseval) + (\offval) + 8 * __b) / 8) * 8
	ld.o	rd21, [rb21, 0]
	__LI	rd20, \v
	br.ne	{rd20, rd21}?, [rb0, __smbad_\@]
	.set	__b, __b + 1
	.endr
	__REC	rd21
	jump	[rb0, __smdone_\@]
__smbad_\@:
	__EXIT	\pt
__smdone_\@:
.endm

@@ ---------------------------------------------------------------------------
@@ 故障例：TEST_FAULT(pt, 助记符, 目的/源, 故障名, 基址, 基址值, 偏移)
@@        TEST_FAULT_M(pt, 助记符, 组, 故障名, 基址, 基址值, 偏移寄存器, 偏移值)
@@        TEST_FAULT_ENC(pt, 故障名, 编码字, 基址, 基址值, 偏移寄存器, 偏移值)
@@   只有 `-defsym CASE_N=<pt>` 才展开该例代码；链例镜像里它不产码。
@@   落点核对 cause_id one-hot，随后 `SYS_EXIT(0xF0|位索引)`。
@@ ---------------------------------------------------------------------------

@@ 把处理器代码（TEST_HSEC 起 64 B）拷到 hmon SRAM 基址
.macro __INSTALL_HMON
	LOAD_ADDR rb20, TEST_HSEC
	LOAD_ADDR rb21, HMON_BASE
	set.zw	rd22, wp0, 8
__cp_\@:
	ld.o	rd23, [rb20, 0]
	st.o	rd23, [rb21, 0]
	add.si	rb20, 8
	add.si	rb21, 8
	add.si	rd22, -1
	br.nz	{rd22}?, [rb0, __cp_\@]
.endm

@@ 故障例公共体：装 hmon 处理器 + 把 one-hot / 退出码 / 失败点号写进 TEST_FAULTV
.macro __FAULT_GUARD pt, fault
	__INSTALL_HMON
	.set	__onehot, 0
	.set	__code, 0
	.ifc	\fault, CFXMEM
	.set	__onehot, 0x0002
	.set	__code, 0xF1
	.endif
	.ifc	\fault, CFXREG
	.set	__onehot, 0x0004
	.set	__code, 0xF2
	.endif
	.ifc	\fault, ILLI
	.set	__onehot, 0x0100
	.set	__code, 0xF8
	.endif
	.ifc	\fault, MALIGN
	.set	__onehot, 0x1000
	.set	__code, 0xFC
	.endif
	.ifc	\fault, IALIGN
	.set	__onehot, 0x2000
	.set	__code, 0xFD
	.endif
	.if	__onehot == 0
	.error	"unknown fault name"
	.endif
	LOAD_ADDR rb11, TEST_FAULTV
	__LI	rd20, __onehot
	st.o	rd20, [rb11, 0]
	__LI	rd21, __code
	st.o	rd21, [rb11, 8]
	__LI	rd22, \pt
	st.o	rd22, [rb11, 16]
.endm

.macro TEST_FAULT pt, mnem, reg, fault, base, baseval, off
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	LOAD_ADDR \base, \baseval
	\mnem	\reg, [\base, \off]
	@@ 走到这里 = 预期故障没有发生 ⇒ 仍按该例检查点号判 guest FAIL
	__EXIT	\pt
	.endif
.endm

@@ 多元素（rrri）故障例：只比异常码（多元素指令允许部分元素已生效，用户 2026-11-13 裁定）
@@   TEST_FAULT_M(pt, 助记符, 组, 故障名, 基址, 基址值, 偏移寄存器, 偏移值)
.macro TEST_FAULT_M pt, mnem, grp, fault, base, baseval, offreg, offval
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	LOAD_ADDR \base, \baseval
	__LI	\offreg, \offval
	\mnem	\grp, [\base, \offreg]
	__EXIT	\pt
	.endif
.endm

@@ 原始编码故障例（汇编器会拒绝的编码，如 immu6 = 0）：同样只比异常码
.macro TEST_FAULT_ENC pt, fault, enc, base, baseval, offreg, offval
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	LOAD_ADDR \base, \baseval
	__LI	\offreg, \offval
	.dd.t32	\enc
	__EXIT	\pt
	.endif
.endm

@@ ---------------------------------------------------------------------------
@@ 镜像骨架
@@ ---------------------------------------------------------------------------

@@ 入口：CASE_N != 0 时跳到被选中的故障例体；否则进入链例
.macro __TEST_BEGIN
	.text
	.globl	_start
_start:
.if CASE_N != 0
	jump	[rb0, __fault_case]
.endif
	LOAD_ADDR rb30, TEST_BUF
.endm

@@ 链例收尾：打印结果缓冲（8 × 检查点数）并 PASS
.macro __TEST_END
	__PRINT	TEST_BUF, (8 * __NCHECK)
	__EXIT	0
.endm

@@ 处理器段 / 落点段 / 数据块（不含用例；每个文件调用一次）
.macro __TEST_SECTIONS
	.section .hmon_stub, "ax"
	.p2align 3
	.globl	__hmon_stub
__hmon_stub:
	LOAD_ADDR rb31, TEST_FAULTV + 32
	cfx2rd	cfx_hmon, cg5, rc2, rd31
	st.o	rd31, [rb31, 0]
	LOAD_ADDR rd63, TEST_PAD
	cfx2rc	cfx_hmon, cg5, rc3, rd63
	escape	cfx_hmon, [excp_cause_ip, 0]
	.dd.t32	0
	.dd.t32	0

	.section .faultpad, "ax"
	.globl	__pad
__pad:
	LOAD_ADDR rb11, TEST_FAULTV
	ld.o	rd20, [rb11, 32]
	ld.o	rd21, [rb11, 0]
	br.ne	{rd20, rd21}?, [rb0, __pad_fail]
	ld.o	rd23, [rb11, 8]
	jump	[rb0, __pad_exit]
__pad_fail:
	ld.o	rd23, [rb11, 16]
__pad_exit:
	LOAD_ADDR rb16, TEST_EXITB
	__LI	rd4, ADP_STOPPED_APP_EXIT
	st.o	rd4, [rb16, 0]
	st.o	rd23, [rb16, 8]
	set.zw	rd16, wp0, SYS_EXIT
	trap	cfx0, (SEMIHOST_TAG + SYS_EXIT)
	.dd.t32	0

	@@ 数据块（0x1000 B）：前 0x800 B 负偏移区（零），随后 192 B 模式（TEST_DATA
	@@ 起 24 个 8 字节 beat），再 0x740 B 零。每个存储例各用一个独立 beat，
	@@ 例与例之间不共享可写字节 ⇒ 用例可单独阅读、顺序无关。
	.section .testdata, "aw"
	.p2align 3
	.space	0x800, 0
TEST_DATA_PATTERN:
	.dd.o64	0x0123456789ABCDEF
	.dd.o64	0x0011223344556677
	.dd.o64	0x8899AABBCCDDEEFF
	.dd.o64	0xFFEEDDCCBBAA9988
	.dd.o64	0x8000000000000000
	.dd.o64	0x7FFFFFFFFFFFFFFF
	.dd.o64	0x0000000000000080
	.dd.o64	0xFFFFFFFFFF000000
	.dd.o64	0x00000000FFFFFFFF
	.dd.o64	0x000000000000FFFF
	.dd.o64	0x0000000000008000
	.dd.o64	0x0000000000007FFF
	.dd.o64	0xFEDCBA9876543210
	.dd.o64	0x0102030405060708
	.dd.o64	0xA5A5A5A55A5A5A5A
	.dd.o64	0xDEADBEEFCAFEF00D
	.dd.o64	0x13579BDF2468ACE0
	.dd.o64	0xFFFFFFFFFFFFFFFF
	.dd.o64	0x0000000000000000
	.dd.o64	0x5555555555555555
	.dd.o64	0xAAAAAAAAAAAAAAAA
	.dd.o64	0x0F0F0F0F0F0F0F0F
	.dd.o64	0xF0F0F0F0F0F0F0F0
	.dd.o64	0x1111111111111111
	@@ 0x0C0..0x800 保持零（单元素用例的零区读数，含 +0x7F8）
	.space	0x740, 0
	@@ MDATA_B（+0x800）：256 个字节 0x80..0xBF 循环
	.set	__i, 0
	.rept	256
	.dd.b08	0x80 + (__i & 0x3F)
	.set	__i, __i + 1
	.endr
	@@ MDATA_W（+0x900）：128 个 16 位元素 0x8000..0x807F
	.set	__i, 0
	.rept	128
	.dd.w16	0x8000 + __i
	.set	__i, __i + 1
	.endr
	@@ MDATA_T（+0xA00）：64 个 32 位元素 0x80000000..0x8000003F
	.set	__i, 0
	.rept	64
	.dd.t32	0x80000000 + __i
	.set	__i, __i + 1
	.endr
	@@ MDATA_O（+0xB00）：64 个 64 位元素 0x0102030405060708 + i
	.set	__i, 0
	.rept	64
	.dd.o64	0x0102030405060708 + __i
	.set	__i, __i + 1
	.endr
	@@ MUNI（+0xD00）：64 个同值拍（最大个数例）
	.rept	64
	.dd.o64	0x0F1E2D3C4B5A6978
	.endr
	@@ MDUMP（+0xF00）：512 B 零区，多元素装入的回写落点
	.space	0x200, 0
	@@ MSTORE（+0x1100）：64 拍保持区模式 0xC0DE0000000000A0 + i
	.set	__i, 0
	.rept	64
	.dd.o64	0xC0DE0000000000A0 + __i
	.set	__i, __i + 1
	.endr
	.space	0x500, 0
.endm
