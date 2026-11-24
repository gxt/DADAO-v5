@@ tests/arch/cache/cache.body.S — cfx5（`cfx_cache`）三方 arch 用例的测试 body
@@ （`m16-testcases-009`）。
@@
@@ **只放「测什么」**：运行模式环境（进入 hmon/smon/umon、栈、异常向量、签名
@@ 输出、退出）在 `tests/arch/common/env-{hmon,smon,umon}/env.S`（m16-testcases-
@@ 015/017）。QEMU/gem5 两个承载跑同一份 body；RTL 承载是 `cache_rtl.S`（同一组
@@ 槽序与期望，见 `cache_oracle.py`）。
@@
@@ 汇编期 `--defsym CACHE_CASE` 选 case（1/2/3/4），一份源出四个镜像：
@@
@@   1 `arch-cache-001`：寄存器面 + D 单行 invalidate/clean/flush + I 侧
@@     invalidate/flush 后取指重取 + `cache_enable=0` 不维护 + 编码 no-op /
@@     无行 PA 无效果（三模式）。
@@   2 `arch-cache-002`：D 侧范围 —— PA 单行边界、PA 区间（相邻两行 + 区间外
@@     一行）、all（三模式）。
@@   3 `arch-cache-003`：拒绝面（读 WO、写 RO、保留 rc、非法控制字 ⇒ CFXREG，
@@     且非法命令不产生维护动作）；只 hmon（supv/user 无同步异常处理程序）。
@@   4 `arch-cache-004`：`cache-model=off`（CACHE-27）：cfx5 存在、`exist=0`、
@@     合法命令被接受无效果、非法编码仍 ⇒ CFXREG；只 hmon。
@@
@@ 期望值见 `cache_oracle.py`（现场从 `contract-cache` / `contract-see` /
@@ `contracts/opcodes.yaml` 派生）；本文件只把实测写进签名流。
@@
@@ 寄存器约定：body 用rd5–rd15、rb5/rb7–rb10；环境保留 rb1 = 栈、rb6 = 退出
@@ 例程、rb30 = 签名写指针（SIG_BEGIN 另用 rd20 预填；自修改代码行的 16 位立即数
@@ 也落在 rd20）。

	.include "cache_tables.inc"
	.include "signature.inc"

	.ifndef CACHE_CASE
	.equ	CACHE_CASE, 1
	.endif

@@ ---------------------------------------------------------------------------
@@ 宏
@@ ---------------------------------------------------------------------------
.macro WCTRL word
	set.rd	rd6, \word
	cfx2rc	cfx_cache, cg8, rc9, rd6
.endm

.macro WADDR addr
	set.rd	rd7, \addr
	cfx2rc	cfx_cache, cg8, rc10, rd7
.endm

.macro WSIZE size
	set.rd	rd7, \size
	cfx2rc	cfx_cache, cg8, rc11, rd7
.endm

.macro WENABLE val
	set.rd	rd6, \val
	cfx2rc	cfx_cache, cg8, rc8, rd6
.endm

.macro ST8 addr, val
	set.rb	rb8, \addr
	set.rb	rb9, \val
	st.o	rb9, [rb8, 0]
.endm

.macro LD8 addr, dst
	set.rb	rb8, \addr
	ld.o	\dst, [rb8, 0]
.endm

@@ 只写代码行第 0 字（4 B）；第 1 字（`jump [rb5]`）保持不动。
.macro PATCH_CODE word
	set.rb	rb8, A_CODE
	set.rd	rd9, \word
	st.t	rd9, [rb8, 0]
.endm

.macro RUN_CODE off
	@@ body 在 umon 下被拷到 U 页（0x6000_0000），链接地址 0x101xxx 对 user 不可
	@@ 达 ⇒ 返回地址 = 运行期基址（rb10，入口用 aip.si 求得）+ 段内固定偏移
	@@ （下面 `.org` 把续点钉在 test_body 的固定偏移上）。
	rb2rb	rb5, rb10, 1
	add.si	rb5, \off
	set.rb	rb8, A_CODE
	jump	[rb8, rd0, 0]
.endm

@@ 区间 / 单行测试的初值：内存四行写回，cache 清空。
.macro SETMEM
	ST8	A_R0, M_R0
	ST8	A_R1, M_R1
	ST8	A_D,  M_D
	ST8	A_OUT, M_OUT
	WCTRL	D_FLUSH_ALL
.endm

@@ 读故障现场（hmon 自身 cg5）：cause_id 与 cause_info 各一槽。
.macro REC_CAUSE
	cfx2rd	cfx_hmon, cg5, rc2, rd5
	SIGUPD	rd5
	cfx2rd	cfx_hmon, cg5, rc4, rd5
	SIGUPD	rd5
.endm

@@ ---------------------------------------------------------------------------
	.section .bodycode,"ax",@progbits
	.globl	test_body
test_body:
	@@ rb10 = 本 body 的运行期基址（aip.si 给「下一条指令」的 IP）
	aip.si	rb10, 0
	@@ rb10 = aip.si 的当前 IP
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS

.if	CACHE_CASE == 1
	@@ ---------------- arch-cache-001 ----------------
	ST8	A_D, M_D
	set.rb	rb8, A_CODE
	set.rd	rd9, WORD_OLD
	st.t	rd9, [rb8, 0]
	set.rd	rd9, WORD_JUMP
	st.t	rd9, [rb8, 4]
	WCTRL	D_FLUSH_ALL

	@@ 寄存器面（CACHE-03/06/07/18/27）
	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	WENABLE	0
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	WENABLE	3
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	set.rd	rd6, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_cache, cg8, rc8, rd6
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	set.rd	rd7, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_cache, cg8, rc10, rd7
	cfx2rd	cfx_cache, cg8, rc10, rd5
	SIGUPD	rd5
	set.rd	rd7, C_PATTERN64
	cfx2rc	cfx_cache, cg8, rc10, rd7
	cfx2rd	cfx_cache, cg8, rc10, rd5
	SIGUPD	rd5
	cfx2rc	cfx_cache, cg8, rc11, rd7
	cfx2rd	cfx_cache, cg8, rc11, rd5
	SIGUPD	rd5

	@@ D 侧单行（CACHE-15/16/19/20）
	ST8	A_D, N_D
	WADDR	A_D
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	ST8	A_D, N_D
	WADDR	A_D
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	ST8	A_D, P_D
	WADDR	A_D
	WSIZE	64
	WCTRL	D_FLUSH_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	@@ I 侧：改写代码行 + D clean ⇒ I 命令后取指重取（CACHE-19）
	PATCH_CODE WORD_INVAL
	WADDR	A_CODE
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	I_CLEAN_LINE		@@ no-op（RTL 日志断言核不发命令）
	WCTRL	I_INVAL_LINE
	RUN_CODE 0x800

	.org	0x800
c_i1:
	or.o	rd5, rd20, rd0
	SIGUPD	rd5

	PATCH_CODE WORD_FLUSH
	WADDR	A_CODE
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	I_FLUSH_LINE
	RUN_CODE 0x900

	.org	0x900
c_i2:
	or.o	rd5, rd20, rd0
	SIGUPD	rd5

	PATCH_CODE WORD_RANGE
	WADDR	A_CODE
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	I_INVAL_RANGE
	RUN_CODE 0xa00

	.org	0xa00
c_i3:
	or.o	rd5, rd20, rd0
	SIGUPD	rd5

	@@ 使能位 = 0：该侧不维护（CACHE-08）
	ST8	A_OUT, N_EN
	WENABLE	0
	WADDR	A_OUT
	WSIZE	64
	WCTRL	D_INVAL_LINE		@@ no-op
	WENABLE	3
	WCTRL	D_CLEAN_LINE
	WCTRL	D_INVAL_LINE
	LD8	A_OUT, rd5
	SIGUPD	rd5

	@@ 无行 / 不可缓存 PA：无效果、不报异常（CACHE-22）
	WADDR	PA_NOLINE
	WSIZE	64
	WCTRL	D_INVAL_LINE
	WCTRL	D_CLEAN_RANGE
	WCTRL	I_FLUSH_RANGE
	set.rd	rd5, W_MMIO
	SIGUPD	rd5

	@@ 无条件 no-op：不检查范围编码 / size（CACHE-12/13）
	WSIZE	0
	WCTRL	NONE_SEL_FLUSH_RESV
	set.rd	rd5, W_SEL0
	SIGUPD	rd5
	WCTRL	ID_NONE_RANGE
	set.rd	rd5, W_NONE
	SIGUPD	rd5
.endif

.if	CACHE_CASE == 2
	@@ ---------------- arch-cache-002 ----------------
	@@ PA 单行只命中包含 addr_start 的行（CACHE-16）
	SETMEM
	ST8	A_R0, N_R0
	ST8	A_R1, N_R1
	WADDR	A_R0
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	@@ PA 区间 invalidate：相邻两行都丢（CACHE-17）
	SETMEM
	ST8	A_R0, N_R0
	ST8	A_R1, N_R1
	WADDR	A_R0
	WSIZE	128
	WCTRL	D_INVAL_RANGE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	@@ PA 区间 clean：写回两行（再单行失效后读新值）
	SETMEM
	ST8	A_R0, N_R0
	ST8	A_R1, N_R1
	WADDR	A_R0
	WSIZE	128
	WCTRL	D_CLEAN_RANGE
	WSIZE	64
	WCTRL	D_INVAL_LINE
	WADDR	A_R1
	WCTRL	D_INVAL_LINE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	@@ PA 区间 flush：写回并失效
	SETMEM
	ST8	A_R0, P_R0
	ST8	A_R1, P_R1
	WADDR	A_R0
	WSIZE	128
	WCTRL	D_FLUSH_RANGE
	LD8	A_R0, rd5
	SIGUPD	rd5
	LD8	A_R1, rd5
	SIGUPD	rd5

	@@ 区间外的行不被碰（CACHE-15/17 的边界）
	SETMEM
	ST8	A_OUT, N_OUT
	ST8	A_R0, N_R0
	WADDR	A_R0
	WSIZE	128
	WCTRL	D_INVAL_RANGE
	LD8	A_OUT, rd5
	SIGUPD	rd5

	@@ all：忽略 addr_start/size（CACHE-15）
	SETMEM
	ST8	A_D, N_D
	WCTRL	D_INVAL_ALL
	LD8	A_D, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_D, N_D
	WCTRL	D_CLEAN_ALL
	WADDR	A_D
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	SETMEM
	ST8	A_D, P_D
	WCTRL	D_FLUSH_ALL
	LD8	A_D, rd5
	SIGUPD	rd5
.endif

.if	CACHE_CASE == 3
	@@ ---------------- arch-cache-003（只 hmon） ----------------
	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5

	@@ 读 WO ⇒ CFXREG；cause_info = 指令编码
	cfx2rd	cfx_cache, cg8, rc9, rd5
	REC_CAUSE

	@@ 写 RO ⇒ CFXREG
	set.rd	rd6, 0
	cfx2rc	cfx_cache, cg8, rc0, rd6
	REC_CAUSE

	@@ 保留 rc ⇒ CFXREG
	cfx2rd	cfx_cache, cg8, rc1, rd5
	REC_CAUSE

	@@ 非法控制字：[3:2] = 11
	WADDR	A_D
	WSIZE	64
	set.rd	rd6, ID_CLEAN_RESV
	cfx2rc	cfx_cache, cg8, rc9, rd6
	REC_CAUSE

	@@ 非法操作数：PA 区间且 size = 0
	WSIZE	0
	set.rd	rd6, D_INVAL_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd6
	REC_CAUSE

	@@ enable = 0 不抑制编码校验（CACHE-08）
	WENABLE	0
	set.rd	rd6, D_CLEAN_RESV
	cfx2rc	cfx_cache, cg8, rc9, rd6
	REC_CAUSE
	WENABLE	3

	@@ 非法 clean 不得写回脏行（CACHE-14/25）
	SETMEM
	ST8	A_D, N_D
	WADDR	A_D
	WSIZE	64
	set.rd	rd6, ID_CLEAN_RESV
	cfx2rc	cfx_cache, cg8, rc9, rd6
	WADDR	A_D
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	@@ 非法 invalidate 不得丢弃脏行（CACHE-14/25）
	SETMEM
	ST8	A_D, N_D
	WADDR	A_D
	WSIZE	0
	set.rd	rd6, D_INVAL_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd6
	WADDR	A_D
	WSIZE	64
	WCTRL	D_CLEAN_LINE
	WCTRL	D_INVAL_LINE
	LD8	A_D, rd5
	SIGUPD	rd5

	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5
.endif

.if	CACHE_CASE == 4
	@@ ---------------- arch-cache-004（cache-model=off） ----------------
	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	WENABLE	3
	cfx2rd	cfx_cache, cg8, rc8, rd5
	SIGUPD	rd5
	set.rd	rd7, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_cache, cg8, rc10, rd7
	cfx2rd	cfx_cache, cg8, rc10, rd5
	SIGUPD	rd5
	set.rd	rd7, C_PATTERN64
	cfx2rc	cfx_cache, cg8, rc10, rd7
	cfx2rd	cfx_cache, cg8, rc10, rd5
	SIGUPD	rd5
	cfx2rc	cfx_cache, cg8, rc11, rd7
	cfx2rd	cfx_cache, cg8, rc11, rd5
	SIGUPD	rd5

	@@ 合法命令被接受（不报异常）、不产生维护
	WCTRL	D_CLEAN_ALL
	set.rd	rd5, W_CLEAN_ALL
	SIGUPD	rd5
	WADDR	A_D
	WSIZE	64
	WCTRL	D_INVAL_LINE
	set.rd	rd5, W_INVAL_LINE
	SIGUPD	rd5
	WADDR	A_OUT
	WSIZE	64
	WCTRL	D_FLUSH_RANGE
	set.rd	rd5, W_FLUSH_RANGE
	SIGUPD	rd5

	@@ 无 cache 模型：写到内存、读回新值（命令无效果）
	ST8	A_OUT, N_OUT
	WADDR	A_OUT
	WSIZE	64
	WCTRL	D_INVAL_LINE
	LD8	A_OUT, rd5
	SIGUPD	rd5

	@@ 非法编码仍 ⇒ CFXREG（CACHE-27）
	WADDR	A_D
	WSIZE	64
	set.rd	rd6, ID_CLEAN_RESV
	cfx2rc	cfx_cache, cg8, rc9, rd6
	REC_CAUSE

	WSIZE	0
	set.rd	rd6, D_INVAL_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd6
	REC_CAUSE

	cfx2rd	cfx_cache, cg8, rc0, rd5
	SIGUPD	rd5
.endif

	@@ 收尾交给环境（rb6 = env_finish；签名输出与 SYS_EXIT 在 .envtail）
	jump	[rb6, rd0, 0]
