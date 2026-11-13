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
@@ rd31/rb31=故障处理器暂存、rd16/rb16=semihosting、r?4/rd4=退出参数块、
@@ rb29=寄存器复制实测落点（SCRATCH）、rb27=rf0 写语义例的前/后落点（WSCRATCH）、
@@ rd25/rd26=rf0 写语义例的「写前值 / 期望字节」。
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
@@ 寄存器复制 / 条件赋值（02-reg-copy，`spec/SimRISC-02`）的实测通路：
@@   目的在 rd ⇒ `__CHECK_RD` 直接比；目的在 rb/ra/rf ⇒ 同组 `st.o` 落到 SCRATCH
@@   （8 B 独立落点，逐次覆写）再 `__CHECK_MEM` —— 探针**不借被测的复制指令**，
@@   否则期望会依赖另一条复制指令。`__VERIFY_*` 判据相同但**不占检查点**：一个用例的
@@   多条断言共用点号，只有最后一条（`__CHECK_*`）追加结果缓冲，故「失败点号 = 用例序号」。
@@   ra/rf 的源/目的初值只能经内存给（`set.zw`/`or.w` 无 ra/rf 形式）⇒ `__SET_MEM`
@@   从 RDATA（TEST_DATA + 0x1300 的 16 拍）装载；rd 用 `__LI`、rb 用 `__LI_RB`。
@@   `rb29` = 复制类实测落点基址（保留；`__TEST_BEGIN` 装好），用例不得占用。
@@   条件赋值（`cs.*`）的同名别名语义按 C-27 仍 deferred（`tests/inst/inventory.md`）
@@   ⇒ 用例只覆盖「条件 / 候选 / 目的互不同名」的路径，不断言别名快照。
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
@@ 寄存器复制（02-reg-copy）的数据区（同上，偏移相对 TEST_DATA）：
@@   +0x1300 RDATA      16 拍装载源（ra/rf 初值 + 条件赋值的 rf 候选取值）
@@   +0x1400 SCRATCH    8 B 落点（rb/ra/rf 实测逐次覆写）
@@ 16 位立即数操作（03-wyde-imm）的数据区（同上，偏移相对 TEST_DATA）：
@@   +0x1500 WDATA      16 拍：初值/边界 + 4 个 id 的「独立 oracle」期望（`_MEM` 变体装载）
@@   +0x1580 WSCRATCH   16 B：rf0 写语义例的「写前 8 B / 写后 8 B」（rb27 指）

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

@@ 寄存器复制数据区（见文件头；偏移相对 TEST_DATA）
	.equ RDATA,   TEST_DATA + 0x1300   @@ 16 拍装载源（ra/rf 初值与候选取值）
	.equ SCRATCH, TEST_DATA + 0x1400   @@ rb/ra/rf 实测落点（逐次覆写）

@@ 16 位立即数操作数据区（见文件头；偏移相对 TEST_DATA）
	.equ WDATA,    TEST_DATA + 0x1500  @@ 16 拍：初值/边界 + 独立 oracle 期望
	.equ WSCRATCH, TEST_DATA + 0x1580  @@ rf0 写语义例的前/后 8 B（rb27 指）

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

@@ 同上判据但**不占检查点**（同一用例的多条断言共用点号；失败同样 `SYS_EXIT(pt)`）
.macro __VERIFY_RD pt, reg, exp
	__LI	rd20, \exp
	br.eq	{rd20, \reg}?, [rb0, __vr_\@]
	__EXIT	\pt
__vr_\@:
.endm

.macro __VERIFY_MEM pt, baseval, off, exp
	LOAD_ADDR rb21, (((\baseval) + (\off)) / 8) * 8
	ld.o	rd21, [rb21, 0]
	__LI	rd20, \exp
	br.eq	{rd20, rd21}?, [rb0, __vm_\@]
	__EXIT	\pt
__vm_\@:
.endm

@@ 两个 rd 寄存器相等（值不可预测时的比较，如 rf0 读出的 FCSR）
.macro __VERIFY_EQ_RD pt, a, b
	br.eq	{\a, \b}?, [rb0, __ve_\@]
	__EXIT	\pt
__ve_\@:
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
@@ 寄存器块复制（orri；`spec/SimRISC-02 §1`）
@@   TEST_MOV1(pt, 助记符, 目的, 源, 期望) —— 单寄存器（immu6 = 1）一行一个检查点。
@@   多寄存器用例直接写 `助记符 {dst:dst+k-1}, {src:src+k-1}` + 若干 `__VERIFY_*`
@@   （不占点号）+ 末尾一条 `__CHECK_*`（点号在这里）；失败点号仍 = 用例序号。
@@   目的银行由助记符决定：目的在 rd ⇒ `__CHECK_RD`；在 rb/ra/rf ⇒ 同组 `st.o` 落到
@@   SCRATCH 再 `__CHECK_MEM`（探针不经过任何复制指令）。
@@ ---------------------------------------------------------------------------

@@ 从 RDATA 装载 8 字节到任意银行（ra/rf 初值的独立通路：内存 → 组）
.macro __SET_MEM reg, off
	LOAD_ADDR rb3, RDATA + \off
	ld.o	\reg, [rb3, 0]
.endm

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

@@ ---------------------------------------------------------------------------
@@ 16 位立即数操作（rwii；`spec/SimRISC-03 §1`）：一行 = 一个检查点
@@   TEST_WI_RD(pt, 助记符, 目的 rd, wpN, immu16, 初值, 期望)
@@   TEST_WI_RB(pt, 助记符, 目的 rb, wpN, immu16, 初值, 期望)
@@   TEST_WI_RF(pt, 助记符, 目的 rf, wpN, immu16, 初值, 期望)
@@   TEST_WI_{RD,RB,RF}_MEM(pt, 助记符, 目的, wpN, immu16, 初值, WDATA 偏移)
@@ 判据：目的在 rd ⇒ 直接比；在 rb/rf ⇒ 同组 `st.o` 落到 SCRATCH 再逐字节比
@@   （探针不借被测的立即数指令）。`_MEM` 变体的**期望从 WDATA 装载**（不经任何 rwii
@@   指令）—— `__LI` 自身用 set.zw/or.w 拼常量，故该变体防「期望由被测指令自证」。
@@ 初值装载：rd 用 `__LI`、rb 用 `__LI_RB`、rf 用 `__LI` + `rd2rf`（复制指令，独立于本册）。
@@ ---------------------------------------------------------------------------

.macro TEST_WI_RD pt, mnem, dst, wp, imm, init, exp
	__LI	\dst, \init
	\mnem	\dst, \wp, \imm
	__CHECK_RD \pt, \dst, \exp
.endm

.macro TEST_WI_RB pt, mnem, dst, wp, imm, init, exp
	__LI_RB	\dst, \init
	\mnem	\dst, \wp, \imm
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
.endm

.macro TEST_WI_RF pt, mnem, dst, wp, imm, init, exp
	__LI	rd20, \init
	rd2rf	{\dst:\dst}, {rd20:rd20}
	\mnem	\dst, \wp, \imm
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
.endm

.macro TEST_WI_RD_MEM pt, mnem, dst, wp, imm, init, off
	__LI	\dst, \init
	\mnem	\dst, \wp, \imm
	LOAD_ADDR rb21, WDATA + \off
	ld.o	rd20, [rb21, 0]
	__REC	\dst
	br.eq	{rd20, \dst}?, [rb0, __wrm_\@]
	__EXIT	\pt
__wrm_\@:
.endm

.macro TEST_WI_RB_MEM pt, mnem, dst, wp, imm, init, off
	__LI_RB	\dst, \init
	\mnem	\dst, \wp, \imm
	st.o	\dst, [rb29, 0]
	LOAD_ADDR rb21, WDATA + \off
	ld.o	rd20, [rb21, 0]
	ld.o	rd21, [rb29, 0]
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __wrm_\@]
	__EXIT	\pt
__wrm_\@:
.endm

.macro TEST_WI_RF_MEM pt, mnem, dst, wp, imm, init, off
	__LI	rd20, \init
	rd2rf	{\dst:\dst}, {rd20:rd20}
	\mnem	\dst, \wp, \imm
	st.o	\dst, [rb29, 0]
	LOAD_ADDR rb21, WDATA + \off
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

.macro TEST_WI_RF0_NOOP pt, wp, imm
	st.o	rf0, [rb27, 0]
	ld.o	rd25, [rb27, 0]
	set.w	rf0, \wp, \imm
	st.o	rf0, [rb27, 0]
	ld.o	rd20, [rb27, 0]
	__REC	rd20
	br.eq	{rd20, rd25}?, [rb0, __r0n_\@]
	__EXIT	\pt
__r0n_\@:
.endm

.macro TEST_WI_RF0_WRITE pt, wp, imm
	set.w	rf0, \wp, 0x0000
	st.o	rf0, [rb27, 0]
	ld.o	rd25, [rb27, 0]
	set.w	rf0, \wp, \imm
	st.o	rf0, [rb27, 8]
	.ifc	\wp, wp2
	ld.ub	rd26, [rb27, 3]
	add.si	rd26, ((\imm) & 3)
	st.b	rd26, [rb27, 3]
	.endif
	.ifc	\wp, wp0
	ld.ub	rd26, [rb27, 7]
	add.si	rd26, ((\imm) & 0x1F)
	st.b	rd26, [rb27, 7]
	.endif
	ld.o	rd20, [rb27, 0]
	ld.o	rd21, [rb27, 8]
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __r0w_\@]
	__EXIT	\pt
__r0w_\@:
.endm

@@ ---------------------------------------------------------------------------
@@ 64 位数据运算（04-arith-logic-octa 算术族，`spec/SimRISC-04 §1`）：一行 = 一个检查点
@@   TEST_AR_DUAL(pt, 助记符, 高半, 低半, 高初值, 低初值,
@@               源C, C值, 源D, D值, 高期望, 低期望)
@@     rrrr 双目的 add/sub/mul：`{rdHA, rdHB}` = 128 位结果（HA 高、HB 低）。
@@     高半用 `__VERIFY_RD`、低半用 `__CHECK_RD` ⇒ 两条断言共用点号，失败点号仍 = 用例序号。
@@   TEST_AR_ORRR(pt, 助记符, 目的, 目的初值, 源C, C值, 源D, D值, 期望)
@@     orrr 单目的 cmp/div/rem：目的写满 64 位。
@@   TEST_AR_ORRI(pt, 助记符, 目的, 目的初值, 源C, C值, immu6, 期望)
@@     orri 移位/扩展：immu6 = 移位量（shl/shr）或扩展起始位（ext），0..63；
@@     immu6=0 合法（`legality_rules.yaml::immu6_zero` 明确不适用于 orri 移位/扩展）。
@@   TEST_AR_SI(pt, 助记符, 目的, 初值, imms18, 期望)
@@     riii `add.si dst, imms18`：目的兼源，立即数符号扩展后加。
@@   TEST_AR_CMPI(pt, 助记符, 目的, 目的初值, 源B, B值, imm12, 期望)
@@     rrii `cmp.si/cmp.ui dst, src, imm`：结果 -1/0/1 写满 64 位。
@@ 初值装载顺序 = 高/低（或目的）/源C/源D；**与已装载寄存器同名者跳过**（`.ifnc`），
@@   故别名用例（目的=源）的「源值」必须等于该寄存器已装载的初值 —— 用例须自洽，
@@   证据脚本的独立重算按同一规则校验（不一致即红）。**rd0 一律不装载**
@@   （rd0 只读、写它会 ILLI；作源时读出 0），双目的为 rd0 的那一半不做比对、点号落在留下的一半。
@@ 探针不借被测指令：初值用 `__LI`（set.zw/or.w，见 03 册），期望内联；比较只用 br.eq。
@@ ---------------------------------------------------------------------------

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

.macro TEST_AR_ORRR pt, mnem, dst, dstinit, c, cval, d, dval, exp
	.ifnc	\dst, rd0
	__LI	\dst, \dstinit
	.endif
	.ifnc	\c, rd0
	.ifnc	\c, \dst
	__LI	\c, \cval
	.endif
	.endif
	.ifnc	\d, rd0
	.ifnc	\d, \dst
	.ifnc	\d, \c
	__LI	\d, \dval
	.endif
	.endif
	.endif
	\mnem	\dst, \c, \d
	__CHECK_RD \pt, \dst, \exp
.endm

.macro TEST_AR_ORRI pt, mnem, dst, dstinit, c, cval, imm, exp
	.ifnc	\dst, rd0
	__LI	\dst, \dstinit
	.endif
	.ifnc	\c, rd0
	.ifnc	\c, \dst
	__LI	\c, \cval
	.endif
	.endif
	\mnem	\dst, \c, \imm
	__CHECK_RD \pt, \dst, \exp
.endm

.macro TEST_AR_SI pt, mnem, dst, init, imm, exp
	__LI	\dst, \init
	\mnem	\dst, \imm
	__CHECK_RD \pt, \dst, \exp
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

.macro TEST_AR_RB_SI pt, mnem, dst, init, imm, exp
	__LI_RB	\dst, \init
	\mnem	\dst, \imm
	st.o	\dst, [rb29, 0]
	__CHECK_MEM \pt, SCRATCH, 0, \exp
.endm

@@ ---------------------------------------------------------------------------
@@ 故障例：TEST_FAULT(pt, 助记符, 目的/源, 故障名, 基址, 基址值, 偏移)
@@        TEST_FAULT_M(pt, 助记符, 组, 故障名, 基址, 基址值, 偏移寄存器, 偏移值)
@@        TEST_FAULT_ENC(pt, 故障名, 编码字, 基址, 基址值, 偏移寄存器, 偏移值)
@@        TEST_FAULT_WI(pt, 助记符, 目的, 故障名, wpN, immu16)
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

@@ 16 位立即数操作故障例（rwii：目的 rd0/rb0 ⇒ ILLI）
@@   TEST_FAULT_WI(pt, 助记符, 目的, 故障名, wpN, immu16)
.macro TEST_FAULT_WI pt, mnem, dst, fault, wp, imm
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	\mnem	\dst, \wp, \imm
	__EXIT	\pt
	.endif
.endm

@@ 64 位数据运算故障例（`spec/SimRISC-04 §1`；汇编器对非法编码同样放行）
@@   TEST_FAULT_DUAL(pt, 助记符, 故障名, 高半, 低半, 源C, 源D)  —— dst_dual_same
@@   TEST_FAULT_ALU3(pt, 助记符, 故障名, 目的, 源C, 源D)        —— dst_rd0（orrr）
@@   TEST_FAULT_ALU_ORRI(pt, 助记符, 故障名, 目的, 源C, immu6)  —— dst_rd0（orri）
@@   TEST_FAULT_ALU_SI(pt, 助记符, 故障名, 目的, imms18)        —— dst_rd0（riii）
@@   TEST_FAULT_ALU_CMPI(pt, 助记符, 故障名, 目的, 源B, imm12)  —— dst_rd0（rrii）
@@   05-arith-addr 的三条（`spec/SimRISC-05`；源/目的分属不同银行）：
@@   TEST_FAULT_BBD(pt, 助记符, 故障名, 目的RB, 源C-RB, 源D-RD)  —— dst_rb0（bbd）
@@   TEST_FAULT_DBB(pt, 助记符, 故障名, 目的RD, 源C-RB, 源D-RB)  —— dst_rd0（dbb）
@@   TEST_FAULT_RB_SI(pt, 助记符, 故障名, 目的RB, 立即数)        —— dst_rb0（riii rb）
@@   源寄存器给固定非零值（rd0/rb0 作源合法，不装载 ⇒ 跳过装载）。
.macro __FAULT_LOAD_SRC reg, val
	.ifnc	\reg, rd0
	__LI	\reg, \val
	.endif
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

.macro TEST_FAULT_ALU3 pt, mnem, fault, dst, c, d
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	__FAULT_LOAD_SRC \c, 0x0123456789ABCDEF
	__FAULT_LOAD_SRC \d, 0x0000000000000007
	\mnem	\dst, \c, \d
	__EXIT	\pt
	.endif
.endm

.macro TEST_FAULT_ALU_ORRI pt, mnem, fault, dst, c, imm
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	__FAULT_LOAD_SRC \c, 0x0123456789ABCDEF
	\mnem	\dst, \c, \imm
	__EXIT	\pt
	.endif
.endm

.macro TEST_FAULT_ALU_SI pt, mnem, fault, dst, imm
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	\mnem	\dst, \imm
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
	LOAD_ADDR rb29, SCRATCH
	LOAD_ADDR rb27, WSCRATCH
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
	@@ RDATA（+0x1300）：16 拍装载源（ra/rf 初值 + 条件赋值的 rf 候选取值）
	.dd.o64	0x1111111111111111      @@ +0x00
	.dd.o64	0x2222222222222222      @@ +0x08
	.dd.o64	0x3333333333333333      @@ +0x10
	.dd.o64	0xABCDEF0123456789      @@ +0x18
	.dd.o64	0x0000000000000000      @@ +0x20
	.dd.o64	0x00000000FFFFFFFF      @@ +0x28
	.dd.o64	0x8000000000000000      @@ +0x30
	.dd.o64	0x0000000000000001      @@ +0x38
	.dd.o64	0x0123456789ABCDEF      @@ +0x40
	.dd.o64	0xFEDCBA9876543210      @@ +0x48
	.dd.o64	0xAAAAAAAAAAAAAAAA      @@ +0x50
	.dd.o64	0x5555555555555555      @@ +0x58
	.dd.o64	0x0F1E2D3C4B5A6978      @@ +0x60
	.dd.o64	0x7FFFFFFFFFFFFFFF      @@ +0x68
	.dd.o64	0x000A000000001234      @@ +0x70（[63:54]=0 ⇒ ra0 可作目的）
	.dd.o64	0x000000000000FFFF      @@ +0x78
	@@ +0x1380..+0x1500 保持零（含 +0x1400 SCRATCH —— rb/ra/rf 实测落点，rb29 指）
	.space	0x180, 0
	@@ WDATA（+0x1500）：16 拍 —— 16 位立即数操作（03-wyde-imm）的初值/边界表；
	@@   `_MEM` 变体从这里装载期望（独立 oracle：不经 set.zw/set.ow/or.w/andn.w/set.w）
WDATA:
	.dd.o64	0x0000000000000000      @@ +0x00
	.dd.o64	0x0123456789ABCDEF      @@ +0x08（四个 wyde 互不相同）
	.dd.o64	0x8899AABBCCDDEEFF      @@ +0x10
	.dd.o64	0xFFFFFFFFFFFFFFFF      @@ +0x18
	.dd.o64	0x000000000000FFFF      @@ +0x20
	.dd.o64	0xFFFF0000FFFF0000      @@ +0x28
	.dd.o64	0x8000000000000000      @@ +0x30
	.dd.o64	0x7FFFFFFFFFFFFFFF      @@ +0x38
	.dd.o64	0x0000ABCD00000000      @@ +0x40（set.zw  wp2 0xABCD，init +0x08）
	.dd.o64	0xFFFF1234FFFFFFFF      @@ +0x48（set.ow  wp2 0x1234，init 0）
	.dd.o64	0x0123456789ABDDFF      @@ +0x50（or.w    wp0 0x1111，init +0x08）
	.dd.o64	0x012345670000CDEF      @@ +0x58（andn.w  wp1 0xFFFF，init +0x08）
	.dd.o64	0x0123FFFF89ABCDEF      @@ +0x60（set.w   wp2 0xFFFF，init +0x08）
	.dd.o64	0xDEADBEEFCAFEF00D      @@ +0x68
	.dd.o64	0xA5A55A5A0F0FF0F0      @@ +0x70
	.dd.o64	0x13579BDF2468ACE0      @@ +0x78
	@@ WSCRATCH（+0x1580）：rf0 写语义例的「写前 / 写后」8 B（rb27 指）与其余零
	.space	0x280, 0
.endm
