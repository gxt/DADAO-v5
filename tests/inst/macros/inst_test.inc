@@ tests/inst/macros/inst_test.inc — **跨册**共享宏层（m15-testcases-002 分层）
@@
@@ **宏作用域三层规则**（门控 `check-inst-macro-scope`（L1）机械判，任一违反即红）：
@@   1. **跨册**（≥2 个册用到）⇒ 本文件；
@@   2. **册专用**（只在一个册用）⇒ `tests/inst/<册>/<册>.inc`，由该册各 `.S`
@@      在本文件之后 `.include`；
@@   3. **单文件专用** ⇒ 直接写在该 `.S` 内（`.include` 之后、首个用例之前）。
@@   死宏（无使用者）必须为 0。
@@
@@ 本层只提供**跨册**宏与公共常量（`.equ`）/镜像骨架；册/文件专用宏见上。
@@
@@ 目的（`tests/inst/MIGRATION.md` §3）：一个 opcode id 一个 `.S`，一行一个用例，
@@ **期望值内联**。用例失败 ⇒ `SYS_EXIT(检查点号)`：guest FAIL 段 `0x01`–`0x7F`，
@@ 值 = 失败点序号（`spec/Kaiwu §7.1`）；机器异常例 ⇒ `SYS_EXIT(0xF0|异常位索引)`，
@@ 即 Tiny（运行模式恒 `hypv`）的 monitor 段编码：CFXMEM `0xF1`、CFXREG `0xF2`、
@@ ILLI `0xF8`、MALIGN `0xFC`、IALIGN `0xFD`（`m15-testcases-007` 起故障例链式合并：
@@ 异常码本身由落点按**期望 one-hot** 核对，成败由「匹配则跳下一例 / 不匹配则
@@ `SYS_EXIT(点号)`」表达，另有一例一 `__EXIT(点号)` 兜住「异常没发生」）。
@@
@@ **镜像 = 每 `.S` 一个**（`m15-testcases-007`；故障例链式合并在同一镜像内跑）：
@@ 由汇编符号 `CASE_N` 选择两种入口（`llvm-mc -defsym CASE_N=<n>`）：
@@
@@   CASE_N = 0（缺省）= **完整镜像**（门控口径）：encoding / legality（非故障）/
@@     semantic / boundary / overlap 逐例顺序执行。每个检查点把**实测的 8 字节**写进
@@     结果缓冲；链例跑完后 `__TEST_END` **进入故障链**——每个故障例依次执行自己的
@@     触发指令，同步异常经 hmon 落到 `.faultpad` 的 `__pad`，落点核对 `cause_id`
@@     低 16 位 one-hot 后**跳下一例**；最后一例落到收尾（`SYS_WRITEC` 逐字节打印
@@     结果缓冲 + `SYS_EXIT(0)`）。三方（chipyard / QEMU / gem5）比较的就是这串字节
@@     ⇒ **逐字节一致**，而不只是退出码一致。无故障例的 `.S` 仍「打印 + 退出」
@@     （`__fault_chain` 就定在收尾代码处 ⇒ `__TEST_END` 的跳转落到收尾）。
@@
@@   CASE_N = <检查点> = **调试用单例模式**：`_start` 直接跳到该故障例体；之后仍按链
@@     续跑到收尾（调试用单例模式不打印缓冲）⇒ 退出码与完整镜像一致。只用于单例定位，
@@     不进门控（`check-inst-asm` 只跑 `CASE_N=0`）。
@@
@@ 故障例链的机制（本文件 `__FAULT_BODY_BEGIN`/`__FAULT_BODY_END`/`__pad`）：
@@   一例体 = `__FAULT_BODY_BEGIN <点号>`（唯一标号 `__fc_<点号>`；**第一例兼链起点**
@@   `__fault_chain`）+ 触发序列 + `__FAULT_BODY_END <点号>`。后者 = 未触发即判红的
@@   `__EXIT <点号>`（**必须保留**：它就是「异常没有发生」的检出器）+ 一行
@@   `.faulttab` 表项（= 本例入口 `__fc_<点号>`，**按点号索引**）。
@@   **下一例地址的取得**：落点按 `点号 + 1` 读表（`.faulttab` 按点号索引、点号连续 ⇒
@@   槽位相邻），非 0 ⇒ 跳过去；读到 **0**（最后一例之后 = `__TEST_SECTIONS` 追加的
@@   表尾哨兵）⇒ 跳收尾。⇒ **没有任何「我是最后一例」的声明**，也不依赖 `.S` 里
@@   `__TEST_END` 与故障例的先后顺序（两种排版都存在）。落点跳转用
@@   `jump [rb, rd0, 0]`（`rrii` 绝对形式，`Addr = rb + rd0 + 0`）。
@@   用例寄存器不受影响：落点只用 rb11/rb16/rb20/rb21 与 rd20–rd23（保留寄存器）。
@@
@@ hmon 的返回地址：固件 hmon 从 hmon SRAM +0xF8 读返回地址（`spec/Kaiwu
@@ §6.2`：power 写默认值 `trap+4`，**框架可覆盖**）。故障例在触发前把落点
@@ `TEST_PAD` 写进 0xF8，于是三方走同一个硬件入口（向量 → 异常帧 → 固件 hmon →
@@ `escape`），测试不再自带处理器。`m12-chipyard-028` 起三方 BootROM 固件同版
@@ （`ISS-410` 已修）。
@@
@@ 保留寄存器（用例不得占用）：rb3=数据基址、rb30=结果缓冲写指针、
@@ rd20/rd21/rb21=期望/实测/临时、rd22/rd23=临时与退出码、
@@ rd16/rb16=semihosting、r?4/rd4=退出参数块、
@@ rb29=寄存器复制实测落点（SCRATCH）、rb27=rf0 写语义例的前/后落点（WSCRATCH）、
@@ rd25/rd26=rf0 写语义例的「写前值 / 期望字节」、
@@ rd24/rb24=控制流（06）用例的「跳转标记 / 落点 IP」与 RAS 实测临时。
@@
@@ 固定地址（Tiny；`.lds` 的 ASSERT 与本节 `.equ` 共同钉住）——全部册（00 + 01–12）**同一份**布局
@@ `tests/ee-tiny/tests_inst_tiny.lds`（`m15-testcases-006` 统一，见该文件头）：
@@   ENTRY = MAIN_SRAM_BASE + 0x2000（`0xffff_ff00_2000`；spec/Kaiwu §6.2，
@@           `kernel_reserved = 0`；image_window = 0x2_0000 覆盖 ENTRY..+0x21FFF）
@@   ENTRY+0x0000 .. +0x4000  .text          链例 + 故障例体 + 收尾代码（16 KiB 窗口）
@@   ENTRY+0x4000 .. +0x4200  .faultpad      故障落点 `__pad`（≤512 B）
@@   ENTRY+0x4200             TEST_FAULTV    故障期望槽：+0 one-hot、+8 失败码（=点号）
@@   ENTRY+0x4300 .. +0x4780  .faulttab      后继表（点号 × 8 B + 表尾哨兵；≤0x480）
@@   ENTRY+0x5000 .. +0x7000  .testdata     数据块（TEST_DATA = +0x5800，0x800 负偏移
@@                                           区在前；单元素 24 个 8 字节数据单元模式；多元素区见下）
@@   SIGNATURE = MAIN_SRAM_BASE+0x1000 .. +0x1800  结果字节缓冲（TEST_BUF；运行期写，不进镜像；
@@                                           ≤127 槽 × 8 B = 1016 B；`SIG_DUMP` 参数块在尾部 +0x7F8）
@@   EXIT_BLOCK = MAIN_SRAM_BASE+0x0030（16 B）      SYS_EXIT 参数块（TEST_EXITB；运行期写，不进镜像）
@@
@@ `m19-testcases-002`：结果缓冲从 `ENTRY+0x7000` 迁到固定签名区 `SIGNATURE`，
@@ SYS_EXIT 参数块从 `ENTRY+0x7800` 迁到全局 `EXIT_BLOCK`（`+0x0030`），
@@ `ENTRY` 由 `0xffff_ff01_0100` 改为 `0xffff_ff00_2000`。
@@
@@ 副作用口径（用户 2026-11-13 裁定，`ldm`/`stm`/`r2r` 等多寄存器/多元素指令）：
@@   **不要求无副作用** —— 这类指令**允许部分元素已经生效**（「源/目范围不得重叠」正是为此）；
@@   chipyard **无需整段预检**。故多元素故障例（`TEST_FAULT_M`/`TEST_FAULT_ENC`）
@@   **只比异常大类**（落点核 one-hot；不对目的寄存器/目标内存做哨兵断言）；
@@   `.S` 注释一律写「允许部分生效」，不得写「不写任何元素 / 第一个数据单元之前」之类断言。
@@   **单元素 `ld`/`st` 仍须精确**（`012` 的 `TEST_FAULT` 路径不变，不动）。
@@   另：中途访存 `denied` 不可构造（`ISS-381` F-c；`m12-chipyard-008` 已定其语义为 `CFXMEM`）。
@@
@@ 寄存器复制 / 条件赋值（02-reg-copy，`spec/SimRISC-02`）的实测通路：
@@   目的在 rd ⇒ `__CHECK_RD` 直接比；目的在 rb/ra/rf ⇒ 同组 `st.o` 落到 SCRATCH
@@   （8 B 独立落点，逐次覆写）再 `__CHECK_MEM` —— 探针**不借被测的复制指令**，
@@   否则期望会依赖另一条复制指令。`__VERIFY_*` 判据相同但**不占检查点**：一个用例的
@@   多条断言共用点号，只有最后一条（`__CHECK_*`）追加结果缓冲，故「失败点号 = 用例序号」。
@@   ra/rf 的源/目的初值只能经内存给（`set.zw`/`or.w` 无 ra/rf 形式）⇒ `__SET_MEM`
@@   从 RDATA（TEST_DATA + 0x1300 的 16 个数据单元）装载；rd 用 `set.rd`、rb 用 `set.rb`。
@@   `rb29` = 复制类实测落点基址（保留；`__TEST_BEGIN` 装好），用例不得占用。
@@   条件赋值（`cs.*`）的同名别名语义按 C-27 仍 deferred（`tests/inst/inventory.md`）
@@   ⇒ 用例只覆盖「条件 / 候选 / 目的互不同名」的路径，不断言别名快照。
@@
@@ 多元素（ldm.*/stm.*）数据区（TEST_DATA 内偏移，均 8 字节对齐；字面量由本节
@@ `.testdata` 现场生成，与 012 单元素用例使用的 0x000-0x0E8 区互不重叠）：
@@   +0x800  MDATA_B   256 个字节 0x80..0xBF 循环（高位置 1 ⇒ ub/sb 各一档）
@@   +0x900  MDATA_W   128 个 16 位元素 0x8000..0x807F
@@   +0xA00  MDATA_T   64 个 32 位元素 0x80000000..0x8000003F
@@   +0xB00  MDATA_O   64 个 64 位元素 0x0102030405060708 + i（数据单元内字节互不相同）
@@   +0xD00  MUNI      64 个同值 8 字节数据单元 0x0F1E2D3C4B5A6978（最大个数例用；字节互不相同）
@@   +0xF00  MDUMP     512 B 零区（多元素装入后的回写落点）
@@   +0x1100 MSTORE    64 个 8 字节数据单元保持区模式 0xC0DE0000000000A0 + i（多元素存储落点）
@@   （`TEST_DATA+0x0C0`..`+0x800` 保持全零：单元素用例的零区读数依赖它）
@@ 寄存器复制（02-reg-copy）的数据区（同上，偏移相对 TEST_DATA）：
@@   +0x1300 RDATA      16 个 8 字节数据单元装载源（ra/rf 初值 + 条件赋值的 rf 候选取值）
@@   +0x1400 SCRATCH    8 B 落点（rb/ra/rf 实测逐次覆写）
@@ 16 位立即数操作（03-wyde-imm）的数据区（同上，偏移相对 TEST_DATA）：
@@   +0x1500 WDATA      16 个 8 字节数据单元：初值/边界 + 4 个 id 的「独立 oracle」期望（`_MEM` 变体装载）
@@   +0x1580 WSCRATCH   16 B：rf0 写语义例的「写前 8 B / 写后 8 B」（rb27 指）
@@ 控制流（06-control-flow）的数据区（同上，偏移相对 TEST_DATA）：
@@   +0x1700 MEMRAS     8 B：MemRAS 条目（`ret` 的 D4b 下溢例：计数 0）；MRPTR 指此
@@   （+0x1600..+0x1700 与 +0x1708..+0x1800 保持零：控制流用例不使用）

	.include "tests/shared/asm/machine-tiny.inc"

	@@ 机器几何一律取 `machine-tiny.inc`（生成物）里的符号，本节只补本宏层的布局。
	@@ 布局单一（`m15-testcases-006`）：全部册共用 `tests/ee-tiny/tests_inst_tiny.lds`，
	@@ `.text` 窗口 16 KiB（原 01 册 0x1E00 / 07 册 0x4000 两份布局合并为一份）。
	.equ TEST_PAD,    ENTRY + 0x4000
	.equ TEST_DATA,   ENTRY + 0x5800
	@@ 结果缓冲 = 固定签名区（spec/Kaiwu §6.2.1：MAIN_SRAM_BASE + 0x1000，0x800）；
	@@ 不在镜像窗口内 ⇒ 运行期写入，不占 PT_LOAD 字节。
	.equ TEST_BUF,    RAM_BASE + 0x1000
	@@ SYS_EXIT 参数块 = 全局 EXIT_BLOCK（spec/Kaiwu §6.2.1：MAIN_SRAM_BASE + 0x0030）。
	.equ TEST_EXITB,  EXIT_BLOCK
	.equ TEST_FAULTV, ENTRY + 0x4200        @@ 故障期望槽（2 × 8 B；见文件头）
	.equ FAULTTAB,    ENTRY + 0x4300        @@ 后继表（点号 × 8 B + 哨兵；见文件头）

@@ 多元素数据区（见文件头；偏移相对 TEST_DATA）
	.equ MDATA_B, TEST_DATA + 0x800
	.equ MDATA_W, TEST_DATA + 0x900
	.equ MDATA_T, TEST_DATA + 0xA00
	.equ MDATA_O, TEST_DATA + 0xB00
	.equ MUNI,    TEST_DATA + 0xD00
	.equ MDUMP,   TEST_DATA + 0xF00
	.equ MSTORE,  TEST_DATA + 0x1100

@@ 寄存器复制数据区（见文件头；偏移相对 TEST_DATA）
	.equ RDATA,   TEST_DATA + 0x1300   @@ 16 个 8 字节数据单元装载源（ra/rf 初值与候选取值）
	.equ SCRATCH, TEST_DATA + 0x1400   @@ rb/ra/rf 实测落点（逐次覆写）

@@ 16 位立即数操作数据区（见文件头；偏移相对 TEST_DATA）
	.equ WDATA,    TEST_DATA + 0x1500  @@ 16 个 8 字节数据单元：初值/边界 + 独立 oracle 期望
	.equ WSCRATCH, TEST_DATA + 0x1580  @@ rf0 写语义例的前/后 8 B（rb27 指）

@@ 控制流数据区（见文件头；偏移相对 TEST_DATA）
	.equ MEMRAS,   TEST_DATA + 0x1700  @@ MemRAS 条目（ret 的 D4b 下溢例）

@@ semihosting：服务号在 rd16、参数块指针在 rb16、trap 标签 0x3FF00+服务号
@@ （`contract-semihosting` §1/§2）。
	.equ SEMIHOST_TAG, 0x3FF00
	.equ SYS_WRITEC,   0x03
	.equ SYS_EXIT,     0x18
	.equ ADP_STOPPED_APP_EXIT, 0x20026

@@ 签名流机制（写槽 / 整段 dump）由共享层提供（`m16-testcases-002`）：
@@ `SIGUPD` = 本文件旧 `__REC` 的写入口，`SIG_DUMP_CHARS` = 旧 `__PRINT` 的逐字节打印；
@@ 两条展开逐字节相同 ⇒ 现有镜像的指令流与输出都不变。`tests/arch` 与 host 侧
@@ （`tools/testcases/lib/signature.py`）复用同一槽宽/哨兵口径。
	.include "tests/shared/asm/signature.inc"

@@ 没有 -defsym CASE_N 时按完整镜像（0：链例 + 故障链）处理。
	.ifndef CASE_N
	.equ CASE_N, 0
	.endif

@@ 链例检查点数（收尾据此决定结果缓冲的字节数）。
	.set	__NCHECK, 0

@@ ---------------------------------------------------------------------------
@@ 基本构件
@@ ---------------------------------------------------------------------------

@@ 立即数 → 寄存器**一律用规范伪指令**（`spec/Toolchain-01 §6`）：
@@   `set.rd rd, imm64`（1–4 条）/ `set.rb rb, imm64`（`set.zw`-rb + `or.w`-rb）/
@@   `set.fo rf, imm64`（`rd2rf rf, rd0` + 非零 wyde 的 `set.w`，整 64 位）。
@@   **不另造装载宏**：测试层与规范单一真源（`m15-testcases-006`）。`set.ft rf, imm32`
@@   是**窄写**（只写低 32、高 32 保持）⇒ **只用于被测指令本身的窄写场景**，不得当装载器。

@@ SYS_EXIT(code)（参数块 {ADP_Stopped_ApplicationExit, code}，`contract-semihosting` §3/§5）
@@   **诊断构建开关**（`m17-testcases-001`）：`llvm-mc --defsym SIG_CONTINUE=1` 时本宏
@@   的**非 0 退出**不产码 ⇒ 判红点继续跑到收尾，host 侧仍能拿到完整签名流做
@@   「槽 N 期望/实际」诊断（`make check-inst-sig` 只在正常镜像失败时另编一份诊断
@@   镜像）；`SYS_EXIT(0)` 仍照常退出。未定义 `SIG_CONTINUE` 时展开与旧版逐字节相同
@@   （M16 周期基线不变；`m17-testcases-001` 全量 272 镜像 `.text` md5 对账）。
.macro __EXIT code
	.ifndef	SIG_CONTINUE
	.set	__exit_now, 1
	.else
	.if	\code == 0
	.set	__exit_now, 1
	.else
	.set	__exit_now, 0
	.endif
	.endif
.if	__exit_now
	set.rb rb16, TEST_EXITB
	set.rd	rd4, ADP_STOPPED_APP_EXIT
	st.o	rd4, [rb16, 0]
	set.rd	rd4, \code
	st.o	rd4, [rb16, 8]
	set.zw	rd16, wp0, SYS_EXIT
	trap	cfx0, (SEMIHOST_TAG + SYS_EXIT)
	.dd.t32	0
.endif
.endm

@@ 结果缓冲追加 8 字节实测值（rb30 是移动写指针），并记一个检查点。
@@   写槽/前进两份动作在共享层 `SIGUPD`（`tests/shared/asm/signature.inc`），本层只留
@@   「记一个检查点」——**不留第二份写入口**。
.macro __REC reg
	SIGUPD	\reg
	.set	__NCHECK, __NCHECK + 1
.endm

@@ ---------------------------------------------------------------------------
@@ 检查点：期望 vs 实测；不等 ⇒ SYS_EXIT(检查点号)；相等 ⇒ 记录实测值
@@ ---------------------------------------------------------------------------

@@ rd 银行实测（被测指令的目的就是 rd）
.macro __CHECK_RD pt, dst, exp
	set.rd	rd20, \exp
	__REC	\dst
	br.eq	{rd20, \dst}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ 内存实测：以 EA 所在 8 字节数据单元（EA/8*8）为单位比较（大端）
.macro __CHECK_MEM pt, baseval, off, exp
	set.rb rb21, (((\baseval) + (\off)) / 8) * 8
	ld.o	rd21, [rb21, 0]
	set.rd	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __ck_\@]
	__EXIT	\pt
__ck_\@:
.endm

@@ 同上判据但**不占检查点**（同一用例的多条断言共用点号；失败同样 `SYS_EXIT(pt)`）
.macro __VERIFY_RD pt, reg, exp
	set.rd	rd20, \exp
	br.eq	{rd20, \reg}?, [rb0, __vr_\@]
	__EXIT	\pt
__vr_\@:
.endm

.macro __VERIFY_MEM pt, baseval, off, exp
	set.rb rb21, (((\baseval) + (\off)) / 8) * 8
	ld.o	rd21, [rb21, 0]
	set.rd	rd20, \exp
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
@@ 寄存器块复制（orri；`spec/SimRISC-02 §1`）
@@   TEST_MOV1(pt, 助记符, 目的, 源, 期望) —— 单寄存器（immu6 = 1）一行一个检查点。
@@   多寄存器用例直接写 `助记符 {dst:dst+k-1}, {src:src+k-1}` + 若干 `__VERIFY_*`
@@   （不占点号）+ 末尾一条 `__CHECK_*`（点号在这里）；失败点号仍 = 用例序号。
@@   目的银行由助记符决定：目的在 rd ⇒ `__CHECK_RD`；在 rb/ra/rf ⇒ 同组 `st.o` 落到
@@   SCRATCH 再 `__CHECK_MEM`（探针不经过任何复制指令）。
@@   同组复制 `rf2rf` 的 31 元边界例另用 `__VERIFY_MEM_RF`/`__CHECK_MEM_RF`（rf 目的 vs 内存数据单元；
@@   探针 = `rf2rd` 跨组读回 + `ld.o`），见该宏处说明。
@@ ---------------------------------------------------------------------------

@@ 从 RDATA 装载 8 字节到任意银行（ra/rf 初值的独立通路：内存 → 组）
.macro __SET_MEM reg, off
	set.rb rb3, RDATA + \off
	ld.o	\reg, [rb3, 0]
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
@@ 探针不借被测指令：初值用 `set.rd`（set.zw/set.ow/or.w/andn.w，见 03 册），期望内联；比较只用 br.eq。
@@ ---------------------------------------------------------------------------

.macro TEST_AR_ORRR pt, mnem, dst, dstinit, c, cval, d, dval, exp
	.ifnc	\dst, rd0
	set.rd	\dst, \dstinit
	.endif
	.ifnc	\c, rd0
	.ifnc	\c, \dst
	set.rd	\c, \cval
	.endif
	.endif
	.ifnc	\d, rd0
	.ifnc	\d, \dst
	.ifnc	\d, \c
	set.rd	\d, \dval
	.endif
	.endif
	.endif
	\mnem	\dst, \c, \d
	__CHECK_RD \pt, \dst, \exp
.endm

.macro TEST_AR_ORRI pt, mnem, dst, dstinit, c, cval, imm, exp
	.ifnc	\dst, rd0
	set.rd	\dst, \dstinit
	.endif
	.ifnc	\c, rd0
	.ifnc	\c, \dst
	set.rd	\c, \cval
	.endif
	.endif
	\mnem	\dst, \c, \imm
	__CHECK_RD \pt, \dst, \exp
.endm

@@ ---------------------------------------------------------------------------
@@ 故障例：TEST_FAULT(pt, 助记符, 目的/源, 故障名, 基址, 基址值, 偏移)
@@        TEST_FAULT_M(pt, 助记符, 组, 故障名, 基址, 基址值, 偏移寄存器, 偏移值)
@@        TEST_FAULT_ENC(pt, 故障名, 编码字, 基址, 基址值, 偏移寄存器, 偏移值)
@@        TEST_FAULT_WI(pt, 助记符, 目的, 故障名, wpN, immu16)
@@   故障例体在**每个镜像**里都产码（`CASE_N=0` 的完整镜像也产码——它就是故障链）；
@@   `-defsym CASE_N=<pt>` 只改变入口（`_start` 直接跳该例），不改变体。
@@   落点核对 `cause_id` 低 16 位 one-hot：不等 ⇒ `SYS_EXIT(点号)`；相等 ⇒ 跳下一例。
@@ ---------------------------------------------------------------------------

@@ 把落点写进固件 hmon 的返回地址槽（hmon SRAM + 0xF8；`spec/Kaiwu §6.2`）
.macro __SET_HMON_RETURN
	set.rb rb20, HMON_BASE
	set.rb rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]
.endm

@@ 故障例公共体：写 hmon 返回槽 + 把 one-hot / 失败点号写进 TEST_FAULTV
@@   +8 的失败点号同时是 `.faulttab` 的索引（落点据此查后继例），故落点两条路径都要它。
.macro __FAULT_GUARD pt, fault
	__SET_HMON_RETURN
	.set	__onehot, 0
	.ifc	\fault, CFXMEM
	.set	__onehot, 0x0002
	.endif
	.ifc	\fault, CFXREG
	.set	__onehot, 0x0004
	.endif
	.ifc	\fault, ILLI
	.set	__onehot, 0x0100
	.endif
	.ifc	\fault, MALIGN
	.set	__onehot, 0x1000
	.endif
	.ifc	\fault, IALIGN
	.set	__onehot, 0x2000
	.endif
	.ifc	\fault, UNDI
	.set	__onehot, 0x0200
	.endif
	.ifc	\fault, RASOF
	.set	__onehot, 0x0400
	.endif
	.ifc	\fault, RASUF
	.set	__onehot, 0x0800
	.endif
	.if	__onehot == 0
	.error	"unknown fault name"
	.endif
	set.rb rb11, TEST_FAULTV
	set.rd	rd20, __onehot
	st.o	rd20, [rb11, 0]
	set.rd	rd22, \pt
	st.o	rd22, [rb11, 8]
.endm

@@ 故障例体入口（一例一个标号；首例兼链起点，`CASE_N=<pt>` 时兼单例入口）
.macro __FAULT_BODY_BEGIN pt
	.ifndef	__FAULT_CHAIN_SEEN
	.set	__FAULT_CHAIN_SEEN, 1
__fault_chain:
	.endif
	.if	CASE_N == \pt
	.globl	__fault_case
__fault_case:
	.endif
__fc_\pt:
.endm

@@ 故障例体末尾：未触发即判红（`__EXIT \pt`，漏报检出器）+ `.faulttab` 表项
@@   表项 = **本例入口** `__fc_<pt>`（按点号索引；表项之间由 `.org` 留出的零槽 = 空槽）。
@@   落点不看「谁是我的后继」：它按 `点号 + 1` 读下一槽 —— 有下一例就跳过去，
@@   读到 **0**（最后一例之后 = `__TEST_SECTIONS` 追加的哨兵槽）就跳收尾。
.macro __FAULT_BODY_END pt
	__EXIT	\pt
	.pushsection	.faulttab, "a"
	.org	(\pt) * 8
	.dd.o64	__fc_\pt
	.popsection
.endm

@@ 原始编码故障例（汇编器会拒绝的编码，如 immu6 = 0）
.macro TEST_FAULT_ENC pt, fault, enc, base, baseval, offreg, offval
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	set.rb \base, \baseval
	set.rd	\offreg, \offval
	.dd.t32	\enc
	__FAULT_BODY_END \pt
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
	set.rd	\reg, \val
	.endif
.endm

.macro TEST_FAULT_ALU3 pt, mnem, fault, dst, c, d
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	__FAULT_LOAD_SRC \c, 0x0123456789ABCDEF
	__FAULT_LOAD_SRC \d, 0x0000000000000007
	\mnem	\dst, \c, \d
	__FAULT_BODY_END \pt
.endm

.macro TEST_FAULT_ALU_ORRI pt, mnem, fault, dst, c, imm
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	__FAULT_LOAD_SRC \c, 0x0123456789ABCDEF
	\mnem	\dst, \c, \imm
	__FAULT_BODY_END \pt
.endm

@@ ---------------------------------------------------------------------------
@@ 控制流（06-control-flow，`spec/SimRISC-06`）：条件分支 / 无条件跳转 / 调用 / 返回
@@   TEST_BR2(pt, 助记符, A, A值, B, B值, 期望)：`rrii` 条件分支（br.eq/br.ne）
@@   TEST_BR1(pt, 助记符, 寄存器, 值, 期望)：`riii` rd 条件分支（br.n/nn/z/nz/p/np）
@@   TEST_BR1_RB(pt, 助记符, 寄存器, 值, 期望)：`riii` rb 条件分支（br.z/br.nz 的 -rb 形式）
@@     期望：1 = 条件成立（跳转），0 = 不成立（不跳）。跳转路径把 rd24 置 1、不跳路径
@@     保持 0，由 `__CHECK_RD` 比 ⇒ 一个用例一个检查点。**落点地址**不在这三条宏里核
@@     （地址用 `.org` 钉住后另设检查点，见各 `.S` 的边界段：`__LAND_IP`）。
@@     源为 rd0/rb0 时跳过装载（硬连零）；两源同名（overlap）只装一次。
@@   __LAND_IP：落点 IP 捕获 —— `aip.si rb24, 0` 取**该指令自身地址**（`rb0` 口径），
@@     再 `rb2rd` 搬到 rd24 ⇒ 实测值 = 落点绝对地址。必须紧放在落点第一条指令。
@@     用途：把「跳转距离/落点」的期望写成 `ENTRY + <字面偏移>`——llvm-mc 只折装
@@     **绝对常量**，标签差在立即数里会被折成 0（`tests/inst/MIGRATION.md §6/019`）。
@@   链例里分支/跳转的「跳过」一律用 `jump`；`.org` 填充的零字只允许被 `jump`/分支跨过。
@@   故障例：`TEST_FAULT_CF`/`TEST_FAULT_CF1`（原始编码：越界跳转目标、`ret rd0` 非零
@@   立即数、保留编码；`CF1` 另给条件寄存器初值）、`TEST_FAULT_BR2`
@@   （条件成立后跳到不可取指的目标 ⇒ UNDI）、`TEST_FAULT_ADDR0`（rrii 目标地址 0 ⇒
@@   CFXMEM）、`TEST_FAULT_RAS`（建立 RA 状态后执行 call/ret ⇒ RASOF/RASUF）、
@@   `TEST_FAULT_RASUF_MEM`（MemRAS 条目计数 0 ⇒ D4b RASUF）。
@@ ---------------------------------------------------------------------------

@@ 同上，另给条件寄存器初值（riii 条件分支的越界目标例 / `sc` 的原始编码例）
@@   TEST_FAULT_CF1(pt, 寄存器, 值, 故障名, 编码字)
@@   寄存器参数**跨银行**（12-misc 传 `rb3`/`rb6`、06 传 `rd1`）：规范伪指令 `set.rd`/`set.rb`
@@   各自绑定一个寄存器组、没有「任意寄存器组」形态 ⇒ 本宏用硬件指令展开装值（与旧装载
@@   宏同型；展开与旧装载宏逐字节相同，不引入新语义）。
.macro TEST_FAULT_CF1 pt, r, rval, fault, enc
	__FAULT_BODY_BEGIN \pt
	__FAULT_GUARD \pt, \fault
	.ifnc	\r, rd0
	.ifnc	\r, rb0
	set.zw	\r, wp0, ((\rval) & 0xFFFF)
	or.w	\r, wp1, (((\rval) >> 16) & 0xFFFF)
	or.w	\r, wp2, (((\rval) >> 32) & 0xFFFF)
	or.w	\r, wp3, (((\rval) >> 48) & 0xFFFF)
	.endif
	.endif
	.dd.t32	\enc
	__FAULT_BODY_END \pt
.endm

@@ ---------------------------------------------------------------------------
@@ 浮点运算（07-floating-point，`spec/SimRISC-07 §2`）
@@
@@ 链例（一行一个检查点；点号 = 用例序号）：
@@   TEST_FP3(pt, 宽度, 助记符, 目的, 源C, C值, 源D, D值, 舍入模式, 期望值, 期望标志)
@@   TEST_FP4(pt, 宽度, 助记符, 目的, 源B, B值, 源C, C值, 源D, D值,
@@             舍入模式, 期望值, 期望标志)
@@   TEST_FPROOT(pt, 宽度, 助记符, 目的, 源, 源值, n, 舍入模式, 期望值, 期望标志)
@@   宽度 = `ft`（单精：只比/只记低 32 位，高 32 位不作规定）| `fo`（双精：64 位全比）。
@@   舍入模式 = rf0[33:32] 的 0..3（RNE/RTZ/RDN/RUP）。
@@   每个用例先清 rf0[4:0] 再设 rf0[33:32]，执行后**先断言标志**再比结果：
@@   期望标志按 rf0[4:0] 位序 NV=0x01 / DZ=0x02 / OF=0x04 / UF=0x08 / NX=0x10
@@   （`spec/SimRISC-00 §2.3.1`）；标志与结果共用一个点号，结果缓冲只记结果。
@@   初值经 `set.fo` 装配（整 64 位） ⇒ 不借任何浮点指令造期望值。
@@   故障例（汇编器会拒绝的非法编码，如目的 rf0 / root 的 n≠2）：
@@   TEST_FAULT_FP(pt, 故障名, 编码字) —— 只比异常码（浮点指令不产生陷阱）。
@@ ---------------------------------------------------------------------------

@@ 07-floating-point 的三个三操作数族（rnd / sclb / sgn）的共享宏。
@@ 原先在 8 个册文件（fornd/ftrnd、fosclb/ftsclb、fosgnj/fosgnn/ftsgnj/ftsgnn）里
@@ 各自逐字重复定义（32 处纯重复、宏体完全相同）⇒ 统一在共享层定义一次；
@@ 册文件只留用例行。定义顺序无关（宏在使用点才展开）。

@@ ---------------------------------------------------------------------------
@@ 镜像骨架
@@ ---------------------------------------------------------------------------

@@ 入口：CASE_N != 0 时跳到被选中的故障例体（调试用单例模式）；否则进入链例
@@   `rb30/rb29/rb27` 只在完整镜像（`CASE_N=0`）里装载（调试用单例模式不记检查点、不打印缓冲）。
.macro __TEST_BEGIN
	.text
	.globl	_start
_start:
.if CASE_N != 0
	jump	[rb0, __fault_case]
.endif
	set.rb rb30, TEST_BUF
	set.rb rb29, SCRATCH
	set.rb rb27, WSCRATCH
.endm

@@ 链例收尾 = **进入故障链**（`m15-testcases-007`）：跳到第一例体；落点按
@@   `.faulttab` 逐例跳下去，最后一例由「下一槽 = 0」跳到 `__TEST_SECTIONS` 的
@@   收尾代码（打印链例缓冲 + PASS）。无故障例的 `.S` 里 `__fault_chain` 就定在
@@   收尾代码处 ⇒ 本跳转直接落到「打印 + 退出」。
.macro __TEST_END
	jump	[rb0, __fault_chain]
.endm

@@ 收尾代码 / 落点段 / 数据块（不含用例；每个文件调用一次）
.macro __TEST_SECTIONS
	@@ 故障落点：核 `cause_id` 低 16 位 one-hot → 不等 `SYS_EXIT(失败码=点号)`；
	@@ 相等则按点号查 `.faulttab` 的**下一槽**：非 0 ⇒ 跳下一例，0 ⇒ 跳收尾。
	.section .faultpad, "ax"
	.globl	__pad
__pad:
	set.rb rb11, TEST_FAULTV
	ld.o	rd23, [rb11, 8]			@@ 失败码 = 点号（兼 `.faulttab` 索引）
	set.rb rb21, HMON_BASE + 0xE0	@@ 固件 hmon 的 cause_id 槽
	ld.o	rd20, [rb21, 0]
	ld.o	rd21, [rb11, 0]
	set.rd	rd22, 0xFFFF			@@ 只比大类 cause_id[15:0]
	and.o	rd20, rd20, rd22		@@ 依据 ADR-0056 D2 / contract-see §6.1.1：
						@@ 子原因是 wyde2/wyde3 里的独立
						@@ one-hot 字段，不参与本比较
	br.ne	{rd20, rd21}?, [rb0, __pad_fail]
	set.rb rb21, FAULTTAB + 8
	shl.o	rd23, rd23, 3			@@ 点号 × 8 = 表项字节偏移
	add.o	rb21, rb21, rd23		@@ &tab[点号 + 1]（bbd 形态：rb + rd）
	ld.o	rb21, [rb21, 0]			@@ 下一例入口；0 = 本例是最后一例
	br.z	{rb21}?, [rb0, __pad_done]
	jump	[rb21, rd0, 0]			@@ rrii 绝对形式：Addr = rb21 + 0
__pad_done:
	jump	[rb0, __fault_finish]		@@ 链走完 → 收尾（打印链例缓冲 + PASS）
__pad_fail:
	set.rb rb16, TEST_EXITB
	set.rd	rd4, ADP_STOPPED_APP_EXIT
	st.o	rd4, [rb16, 0]
	st.o	rd23, [rb16, 8]
	set.zw	rd16, wp0, SYS_EXIT
	trap	cfx0, (SEMIHOST_TAG + SYS_EXIT)
	.dd.t32	0

	@@ 收尾：链例结果缓冲（8 × 检查点数）+ PASS。位置 = `.text` 末尾（本宏是文件里
	@@ 最后一条），故障链的最后一例由落点的 0 槽跳到这里；无故障例的 `.S` 里
	@@ `__fault_chain` 就定义在这里 ⇒ `__TEST_END` 顺落过去（打印 + 退出不变）。
	@@ 调试用单例模式（`CASE_N=<点号>`）只比退出码，不打印缓冲（缓冲此时未被写入）。
	.text
	.ifndef	__FAULT_CHAIN_SEEN
__fault_chain:
	.endif
__fault_finish:
.if CASE_N == 0
	.if __NCHECK > 0
	@@ 逐字节路径：与旧 `__PRINT` 展开逐字节相同 ⇒ 镜像指令流/周期基线不变。
	@@ 块写路径（`SIG_DUMP`）由 `tests/arch` 探针使用并三方验证（`m16-testcases-002`）。
	SIG_DUMP_CHARS	TEST_BUF, __NCHECK
	.endif
.endif
	__EXIT	0

	@@ `.faulttab` 表尾哨兵：最后一例读到的「下一槽」= 0 ⇒ 落点走收尾
	.ifdef	__FAULT_CHAIN_SEEN
	.pushsection	.faulttab, "a"
	.space	8, 0
	.popsection
	.endif

	@@ 数据块（0x1000 B）：前 0x800 B 负偏移区（零），随后 192 B 模式（TEST_DATA
	@@ 起 24 个 8 字节数据单元），再 0x740 B 零。每个存储例各用一个独立数据单元，
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
	@@ MUNI（+0xD00）：64 个同值 8 字节数据单元（最大个数例）
	.rept	64
	.dd.o64	0x0F1E2D3C4B5A6978
	.endr
	@@ MDUMP（+0xF00）：512 B 零区，多元素装入的回写落点
	.space	0x200, 0
	@@ MSTORE（+0x1100）：64 个 8 字节数据单元保持区模式 0xC0DE0000000000A0 + i
	.set	__i, 0
	.rept	64
	.dd.o64	0xC0DE0000000000A0 + __i
	.set	__i, __i + 1
	.endr
	@@ RDATA（+0x1300）：16 个 8 字节数据单元装载源（ra/rf 初值 + 条件赋值的 rf 候选取值）
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
	@@ WDATA（+0x1500）：16 个 8 字节数据单元 —— 16 位立即数操作（03-wyde-imm）的初值/边界表；
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
