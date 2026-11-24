@@ tests/arch/time/time.body.S — `arch-time-001` 的测试 body（cfx_time，m16-chipyard-023）
@@
@@ **只放「测什么」**：运行模式环境（进入 hmon/smon/umon、栈、异常向量、签名
@@ 输出、退出）在 `tests/arch/common/env-{hmon,smon,umon}/env.S`（m16-testcases-015/
@@ 017），同一份 body 在三种模式下各跑一次，签名流三模式逐槽相同。
@@
@@ 观测面（`DADAO-12 §4.10`：`cfx_time` 是 per-system 全局时间计数器，只读、
@@ **没有中断**）：
@@
@@   槽 0 `time_freq`（cg10 rc0）—— 测试机 1 GHz（`contract-see §3`）
@@   槽 1 `time_freq` 再读 —— RO 稳定
@@   槽 2 `time_value`（cg10 rc1）单调：隔约 900 条指令后 `t1 >= t0` ⇒ 1
@@   槽 3 严格递增：`t1 > t0` ⇒ 1（计数器不动即判 0）
@@   槽 4 增量有界：两次读数的高 32 位差 ∈ {0,1} ⇒ delta < 2^33 ⇒ 1
@@        （真实间隔是数百~数万 count；该界只拦「跳到完全不同的量级」）
@@   槽 5 epoch 合理：`t0` 高位置 0 ⇒ 1（`contract-see §3`：复位后从 0 起算）
@@   槽 6 同基准：`cfx_hart cg8 rc2 cycle` 不早于紧邻的 `time_value` 读数 `t2`
@@        且同一 2^32 窗口 ⇒ 1（`contract-see §3`：两者同基准、1 count = 1 ns；
@@        单 hart 下读数相等，因此本用例只能判「同基准」，不能判两者不等）
@@
@@ **cfx34 没有中断，本 body 不测中断**：不写 `timer_cmp`/`timer_ctrl`（那是
@@ `cfx_hart §4.7` 的 per-hart 定时器）、不等待任何投递；`§4.10` 在 `cg10` 上
@@ 只定义 rc0/rc1，其余 rc 的读在 `arch-time-002` 判 `CFXREG`。
@@
@@ 寄存器约定：body 用 rd5–rd14、rb2（环境保留 rb1 = 栈、rb6 = 退出例程、
@@ rb30 = 签名写指针；SIG_BEGIN 另用 rd20 预填）。
@@
@@ 与全局时间的关系：本 body 不自己维护计数器 —— 读数全部来自硬件
@@ （`cfx2rd`），期望值在 `tests/arch/time/time_oracle.py` 现场派生。

	.include "signature.inc"

	.section .bodycode,"ax",@progbits
	.globl	test_body
test_body:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS

	@@ 槽 0：time_freq（cg10 rc0，RO）
	cfx2rd	cfx_time, cg10, rc0, rd5
	SIGUPD	rd5

	@@ 槽 1：time_freq 再读（RO 稳定）
	cfx2rd	cfx_time, cg10, rc0, rd6
	SIGUPD	rd6

	@@ 第一次读数 t0（rd9）
	cfx2rd	cfx_time, cg10, rc1, rd9

	@@ 隔约 900 条指令（300 次迭代 × 3 条）：让计数器明显前进
	set.rd	rd7, 300
t_gap:
	add.si	rb2, 1
	add.si	rd7, -1
	br.nz	{rd7}?, [rb0, t_gap]

	@@ 第二次读数 t1（rd10），紧邻的 t2（rd11）与 cfx_hart cycle（rd12）
	cfx2rd	cfx_time, cg10, rc1, rd10
	cfx2rd	cfx_time, cg10, rc1, rd11
	cfx2rd	cfx_hart, cg8, rc2, rd12

	@@ 槽 2：单调（t1 >= t0；cmp.uo 给 -1/0/1）
	cmp.uo	rd13, rd10, rd9
	set.rd	rd6, -1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ t1 < t0
	set.rd	rd5, 1
	br.nz	{rd14}?, [rb0, t_mono_rec]
	set.rd	rd5, 0
t_mono_rec:
	SIGUPD	rd5

	@@ 槽 3：严格递增（t1 > t0；rd13 仍是上面那次比较）
	set.rd	rd6, 1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ t1 > t0
	set.rd	rd5, 1
	br.z	{rd14}?, [rb0, t_strict_rec]
	set.rd	rd5, 0
t_strict_rec:
	SIGUPD	rd5

	@@ 槽 4：增量有界（高 32 位差 ∈ {0,1}）
	shr.uo	rd7, rd10, 32		@@ hi(t1)
	shr.uo	rd8, rd9, 32		@@ hi(t0)
	cmp.uo	rd13, rd7, rd8
	set.rd	rd6, -1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ hi(t1) < hi(t0)
	set.rd	rd5, 1
	br.nz	{rd14}?, [rb0, t_bound_rec]
	set.rd	rd5, 0
t_bound_rec:
	SIGUPD	rd5

	@@ 槽 5：epoch 合理（t0 高位置 0）
	shr.uo	rd7, rd9, 63
	set.rd	rd6, 0
	cmp.uo	rd14, rd7, rd6		@@ 0 ⇔ 高位为 0
	set.rd	rd5, 1
	br.z	{rd14}?, [rb0, t_epoch_rec]
	set.rd	rd5, 0
t_epoch_rec:
	SIGUPD	rd5

	@@ 槽 6：同基准（cycle >= t2 且同一 2^32 窗口）
	cmp.uo	rd13, rd12, rd11	@@ cycle 对 t2
	set.rd	rd6, -1
	cmp.uo	rd14, rd13, rd6		@@ 0 ⇔ cycle < t2
	shr.uo	rd7, rd12, 32		@@ hi(cycle)
	shr.uo	rd8, rd11, 32		@@ hi(t2)
	cmp.uo	rd15, rd7, rd8		@@ 0 ⇔ 同一窗口
	set.rd	rd5, 1
	br.z	{rd14}?, [rb0, t_base_fail]
	br.z	{rd15}?, [rb0, t_base_rec]
t_base_fail:
	set.rd	rd5, 0
t_base_rec:
	SIGUPD	rd5

	@@ 收尾交给环境（rb6 = env_finish；签名输出与 SYS_EXIT 在 .envtail）
	jump	[rb6, rd0, 0]
