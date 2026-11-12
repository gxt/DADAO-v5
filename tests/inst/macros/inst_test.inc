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
@@   ENTRY+0x1F00             .faultpad      故障落点（≤256 B）
@@   ENTRY+0x1F80             TEST_FAULTV    故障期望槽：+0 one-hot、+8 退出码、
@@                                           +16 失败码（=检查点号）、+32 实测 one-hot
@@   ENTRY+0x2000 .. +0x3000  .testdata     数据块（TEST_DATA = +0x2800，0x800 负偏移
@@                                           区在前、0x780 尾部零填充在后）
@@   ENTRY+0x3000 .. +0x3800  结果字节缓冲（每检查点 8 字节，≤127 点 ⇒ ≤1016 B）
@@   ENTRY+0x4000             SYS_EXIT 参数块

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	@@ 机器几何一律取 `machine-tiny.inc`（生成物）里的符号，本节只补本宏层的布局。
	.equ TEST_HSEC,   ENTRY + 0x1E00
	.equ TEST_PAD,    ENTRY + 0x1F00
	.equ TEST_FAULTV, ENTRY + 0x1F80
	.equ TEST_DATA,   ENTRY + 0x2800
	.equ TEST_BUF,    ENTRY + 0x3000
	.equ TEST_EXITB,  ENTRY + 0x4000

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
@@ 故障例：TEST_FAULT(pt, 助记符, 目的/源, 故障名, 基址, 基址值, 偏移)
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

.macro TEST_FAULT pt, mnem, reg, fault, base, baseval, off
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
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
	LOAD_ADDR \base, \baseval
	\mnem	\reg, [\base, \off]
	@@ 走到这里 = 预期故障没有发生 ⇒ 仍按该例检查点号判 guest FAIL
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
	.space	0x740, 0
.endm
