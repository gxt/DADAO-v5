@@ tests/inst/12-misc/12-misc.inc — **12-misc 册专用**宏层（m15-testcases-003 收敛）
@@
@@ 口径：本文件只放**本册**用的宏与数据区布局；跨册宏在
@@ `tests/inst/macros/inst_test.inc`，单文件宏直接写在该 `.S` 内（门控
@@ `check-inst-macro-scope` 机械判三分层 + 死宏 0 + include 接线）。
@@ 本册每个 `.S` 在共享层之后 `.include` 本文件一次：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/12-misc/12-misc.inc"
@@
@@ lr / sc（原子，`spec/SimRISC-12 §1` + `contract-isa §14.2`）的用例都由同一组
@@ 「准备段 + 被测指令 + 断言行」构成：把 8 B 拍初值落地 → 用 `lr` 建本 hart 的保留
@@ 标记 → 把条件写的源值装进寄存器 → 执行被测指令。准备段与被测的 `lr/sc` 宽度/存储序
@@ 无关（只经宏参数传入），故按册收敛到这里；**点号行（`__CHECK_*`）与被测指令一律留在
@@ 用例处** —— 失败点号 = 用例序号（`spec/Kaiwu §7.1`）在文件里直接可见、可逐个核对。
@@
@@ ---------------------------------------------------------------------------
@@ 数据区（TEST_DATA 零区；每例独立 8 B 拍，例间不共享可写字节）
@@   `LMAL` 是**宽度专属**的故意不对齐地址（.w = +0x7F2 / .t = +0x7F4 / .o = +0x7F4）
@@   ⇒ 它留在各 `.S` 内，不进本文件。
@@ ---------------------------------------------------------------------------
	.equ A0, TEST_DATA + 0x500
	.equ A1, TEST_DATA + 0x508
	.equ A2, TEST_DATA + 0x510
	.equ A3, TEST_DATA + 0x518
	.equ A4, TEST_DATA + 0x520
	.equ A5, TEST_DATA + 0x528
	.equ A6, TEST_DATA + 0x530
	.equ A7, TEST_DATA + 0x538
	.equ A8, TEST_DATA + 0x540
	.equ A9, TEST_DATA + 0x548
	.equ A10, TEST_DATA + 0x550
	.equ A11, TEST_DATA + 0x558
	.equ A12, TEST_DATA + 0x560
	.equ A13, TEST_DATA + 0x568
	.equ A14, TEST_DATA + 0x570
	.equ A15, TEST_DATA + 0x578
	.equ A16, TEST_DATA + 0x580
	.equ A17, TEST_DATA + 0x588
	.equ B0, TEST_DATA + 0x600
	.equ B1, TEST_DATA + 0x608
	.equ B2, TEST_DATA + 0x610
	.equ B3, TEST_DATA + 0x618
	.equ B4, TEST_DATA + 0x620
	.equ B5, TEST_DATA + 0x628
	.equ B6, TEST_DATA + 0x630
	.equ B7, TEST_DATA + 0x638
	.equ B8, TEST_DATA + 0x640
	.equ B9, TEST_DATA + 0x648
	.equ B10, TEST_DATA + 0x650
	.equ B11, TEST_DATA + 0x658
	.equ B12, TEST_DATA + 0x660
	.equ B13, TEST_DATA + 0x668
	.equ B14, TEST_DATA + 0x670
	.equ B15, TEST_DATA + 0x678
	.equ B16, TEST_DATA + 0x680
	.equ B17, TEST_DATA + 0x688
	.equ L, TEST_DATA + 0x7E8        @@ 数据区末拍（末字 0x7F0）
	.equ SCR, TEST_DATA + 0x7F8      @@ 清标记落点（全 0 拍；消费标记用）

@@ ---------------------------------------------------------------------------
@@ 准备段（被测指令与点号行留在用例处）
@@   __PT_ST_INIT(ea, val)                        —— 8 B 拍初值落地
@@   __PT_LRSC_PREP(lr, ea, init, reload=1, k=0)  —— 落地 + 建标记；
@@        reload=1 时按 `ea + k` 重载基址再 `lr`（k = EA 相对拍起点的字节偏移），
@@        reload=0 时沿用 rb3（中间不再有地址计算，如「保留粒度」例）。
@@   __PT_LRSC_LD(lr, srcreg, ea, init, src, k=0) —— PREP + 源值进 `srcreg`
@@   __PT_LRSC_LD2(lr, srcreg, a, b, inita, initb, src)
@@        —— 两处拍初值（a / b）+ 在 a 建标记 + 源值（标记在 a、被测指令指向 b 的例）
@@   __PT_LRSC_LD2L(lr, srcreg, a, b, mbase, inita, initb, src)
@@        —— 两处拍初值 + `lr a` → `lr b`（另一条 lr 清 a 的标记）+ 重载 a + 源值；
@@           `mbase` = 第二条 lr 的基址寄存器（用例自带：原用例用 rb3/rb4 两种写法，
@@           保持指令字节不变）
@@   __PT_LRSC_CLEAR(lr, sc)                      —— 消费本 hart 的保留标记（lr SCR → sc SCR）
@@ ---------------------------------------------------------------------------
.macro __PT_ST_INIT ea, val
	set.rd	rd6, \val
	LOAD_ADDR rb3, \ea
	st.o	rd6, [rb3, 0]
.endm

.macro __PT_LRSC_PREP lrmnem, ea, init, reload=1, k=0
	__PT_ST_INIT	\ea, \init
	.if	\reload
	LOAD_ADDR rb3, (\ea) + (\k)
	.endif
	\lrmnem	rd2, [rb3]
.endm

.macro __PT_LRSC_LD lrmnem, srcreg, ea, init, src, k=0
	__PT_LRSC_PREP	\lrmnem, \ea, \init, 1, \k
	set.rd	\srcreg, \src
.endm

.macro __PT_LRSC_LD2 lrmnem, srcreg, a, b, inita, initb, src
	__PT_ST_INIT	\a, \inita
	__PT_ST_INIT	\b, \initb
	LOAD_ADDR rb3, \a
	\lrmnem	rd2, [rb3]
	set.rd	\srcreg, \src
.endm

.macro __PT_LRSC_LD2L lrmnem, srcreg, a, b, mbase, inita, initb, src
	__PT_ST_INIT	\a, \inita
	__PT_ST_INIT	\b, \initb
	LOAD_ADDR rb3, \a
	\lrmnem	rd2, [rb3]
	LOAD_ADDR \mbase, \b
	\lrmnem	rd2, [\mbase]
	LOAD_ADDR rb3, \a
	set.rd	\srcreg, \src
.endm

.macro __PT_LRSC_CLEAR lrmnem, scmnem
	LOAD_ADDR rb5, SCR
	\lrmnem	rd2, [rb5]
	\scmnem	rd5, rd2, [rb5]
.endm

@@ ===========================================================================
@@ 整例宏（m15-testcases-004；用户 2026-11-16 裁定「整例宏化」）——**一行 = 一整条用例**
@@
@@   点号是该行**第 1 个实参**；宏体里**占检查点**的 `__CHECK_RD` 用 `\pt` 作失败点号
@@   （失败点号 = 用例序号），其余 `__VERIFY_*` 不占检查点、共用同一点号。宏体只做
@@   「准备段 + 被测 `sc` + 断言」的顺序展开，指令序列与原用例逐条对齐（字节相等）。
@@   门控 `check-inst-macro-scope` 的 S6/S7/S8 机械判：宏体恰 1 处断言且点号引用 `\pt`、
@@   一行用例行恰展开 1 个检查点、`.S` 正文不得再有裸 `__CHECK_*`。
@@
@@   返回码只有「命中标记 ⇒ 成功 0」与「无标记 / 标记在别处 ⇒ 失败 1」两类（`spec/SimRISC-12
@@   §1`），故在宏体内固定为常量；**只有点号必须来自调用方**。
@@ ---------------------------------------------------------------------------

@@ 编码字例：`__PT_SC_ENC(pt, 助记符 lr, 源寄存器, 编码字, ea, 拍初值, 源值, 期望拍)`
@@   —— 直接执行规范编码字（被测 `sc` 不在宏里，`word` 自带 opc 0x47 + 位域）
.macro __PT_SC_ENC pt, lrmnem, srcreg, word, ea, init, src, exp
	__PT_LRSC_LD	\lrmnem, \srcreg, \ea, \init, \src
	.dd.t32	\word
	__CHECK_RD	\pt, rd5, 0x0
	__VERIFY_MEM	\pt, \ea, 0, \exp
.endm

@@ 命中标记 ⇒ 成功（`rdHB=0`），仅宽度窗口被写。
@@   `__PT_SC_LD(pt, sc, lr, 源寄存器, ea, 拍初值, 源值, 返回, 期望拍[, k])`
.macro __PT_SC_LD pt, scmnem, lrmnem, srcreg, ea, init, src, res, exp, k=0
	__PT_LRSC_LD	\lrmnem, \srcreg, \ea, \init, \src, \k
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, \res
	__VERIFY_MEM	\pt, \ea, 0, \exp
.endm

@@ 无保留标记（先消费标记）或 `rdHB == rdHC` 且无标记 ⇒ 失败（1）且不写内存。
.macro __PT_SC_NORESV pt, scmnem, lrmnem, srcreg, ea, init, src, exp
	__PT_ST_INIT	\ea, \init
	__PT_LRSC_CLEAR	\lrmnem, \scmnem
	LOAD_ADDR rb3, \ea
	set.rd	\srcreg, \src
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x1
	__VERIFY_MEM	\pt, \ea, 0, \exp
.endm

@@ sc 写回同值（源 = 刚 `lr` 读到的寄存器，不重新装载）⇒ 成功且字节不变。
.macro __PT_SC_LOADED pt, scmnem, lrmnem, srcreg, ea, init, exp
	__PT_ST_INIT	\ea, \init
	LOAD_ADDR rb3, \ea
	\lrmnem	\srcreg, [rb3]
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x0
	__VERIFY_MEM	\pt, \ea, 0, \exp
.endm

@@ 标记在 a、`sc` 指向 b（不同 8 B 字）⇒ 失败且两处都不写。
.macro __PT_SC_LD2 pt, scmnem, lrmnem, srcreg, a, b, inita, initb, src, expa, expb
	__PT_LRSC_LD2	\lrmnem, \srcreg, \a, \b, \inita, \initb, \src
	LOAD_ADDR rb4, \b
	\scmnem	rd5, \srcreg, [rb4]
	__CHECK_RD	\pt, rd5, 0x1
	__VERIFY_MEM	\pt, \a, 0, \expa
	__VERIFY_MEM	\pt, \b, 0, \expb
.endm

@@ 失败的 `sc` 清全部标记 ⇒ 随后 `sc` 原地址仍失败。
.macro __PT_SC_LD2_FAIL pt, scmnem, lrmnem, srcreg, a, b, inita, initb, src, exp
	__PT_LRSC_LD2	\lrmnem, \srcreg, \a, \b, \inita, \initb, \src
	LOAD_ADDR rb4, \b
	\scmnem	rd5, \srcreg, [rb4]
	LOAD_ADDR rb3, \a
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x1
	__VERIFY_MEM	\pt, \a, 0, \exp
.endm

@@ 本 hart 另一条 `lr` 清旧标记（`lr a` → `lr b` → `sc a`）⇒ 失败。
@@   `mbase` = 第二条 `lr` 的基址寄存器（用例自带：rb3/rb4 两种写法，保持指令字节不变）
.macro __PT_SC_LD2L pt, scmnem, lrmnem, srcreg, a, b, mbase, inita, initb, src, exp
	__PT_LRSC_LD2L	\lrmnem, \srcreg, \a, \b, \mbase, \inita, \initb, \src
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x1
	__VERIFY_MEM	\pt, \a, 0, \exp
.endm

@@ `sc` 成功后标记已消费 ⇒ 第二次 `sc` 失败、保留首次写。
@@   `prev` = 首次 `sc` 那条 `__VERIFY_RD` 共用的点号（不占新检查点）
.macro __PT_SC_2SC pt, prev, scmnem, lrmnem, srcreg, ea, init, src1, src2, exp
	__PT_LRSC_LD	\lrmnem, \srcreg, \ea, \init, \src1
	\scmnem	rd5, \srcreg, [rb3]
	__VERIFY_RD	\prev, rd5, 0x0
	set.rd	\srcreg, \src2
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x1
	__VERIFY_MEM	\pt, \ea, 0, \exp
.endm

@@ 同上但保留粒度例：`lr` 之后先有普通 store（`reload=0`：rb3 仍指向该拍）。
.macro __PT_SC_2SC_SELF pt, scmnem, lrmnem, srcreg, ea, init, src1, src2, exp
	__PT_LRSC_PREP	\lrmnem, \ea, \init, 0
	set.rd	\srcreg, \src1
	\scmnem	rd5, \srcreg, [rb3]
	__VERIFY_RD	\pt, rd5, 0x0
	set.rd	\srcreg, \src2
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x1
	__VERIFY_MEM	\pt, \ea, 0, \exp
.endm

@@ 保留粒度：`lr` 之后夹一条**普通 store**（宽度/地址刻意与 `sc` 不同）⇒ 标记仍在、
@@   `sc` 成功。`reload=0`：`__PT_ST_INIT` 已把 rb3 指向该拍，中间不再重算地址。
.macro __PT_SC_STORE_PREP pt, scmnem, lrmnem, srcreg, ea, init, stmnem, stval, stoff, src, exp
	__PT_LRSC_PREP	\lrmnem, \ea, \init, 0
	set.rd	rd6, \stval
	\stmnem	rd6, [rb3, \stoff]
	set.rd	\srcreg, \src
	\scmnem	rd5, \srcreg, [rb3]
	__CHECK_RD	\pt, rd5, 0x0
	__VERIFY_MEM	\pt, \ea, 0, \exp
.endm

@@ ---------------------------------------------------------------------------
@@ 2 行级结构重复宏（m15-testcases-005；判据 = 净收益 k×n−(n+2+k) > 0，
@@ 宏体只含准备段、0 个检查点 ⇒ 用非用例前缀 `__PREP_*`，`__PT_*` 只留给
@@ 「一行一条用例」的宏）。
@@ ---------------------------------------------------------------------------

.macro __PREP_LI_ADDR rd, imm, base, addr
	set.rd	\rd, \imm
	LOAD_ADDR	\base, \addr
.endm

.macro __PREP_ST_ADDR addr
	st.o	rd6, [rb3, 0]
	LOAD_ADDR	rb3, \addr
.endm
