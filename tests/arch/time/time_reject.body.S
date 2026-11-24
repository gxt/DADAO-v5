@@ tests/arch/time/time_reject.body.S — `arch-time-002` 的测试 body（m16-chipyard-023）
@@
@@ **只跑 hmon（hypv）**：本 case 逐条触发同步异常（`CFXREG`），而 step5 链在
@@ supv/user 下没有同步异常处理程序（`tests/arch/common/env-README.md`
@@ 「已知语义边界」）⇒ 只能在 hypv 跑，排除原因见 `tests/arch/modes.yaml`。
@@
@@ 观测面（`DADAO-12 §4.10`：`cfx_time` 只有 `cg10 rc0/rc1` 两个 RO 寄存器）：
@@
@@   槽 0 `time_freq`（cg10 rc0）—— 测试机 1 GHz（`contract-see §3`）
@@   槽 1 读 `cg10 rc2`（保留 rc）⇒ `CFXREG`（cause_id = 1<<2）
@@   槽 2 读 `cg10 rc63`（保留 rc 上界）⇒ `CFXREG`
@@   槽 3 写 `cg10 rc0`（RO）⇒ `CFXREG`（写被拒，不生效）
@@   槽 4 写 `cg10 rc1`（RO）⇒ `CFXREG`
@@   槽 5 再读 `time_freq` ⇒ 仍为 1 GHz（被拒的写没有改到寄存器）
@@
@@ `cg10` 上**没有** `timer_cmp`/`timer_ctrl`/中断源（`§4.7` 才是 per-hart
@@ 比较与 `TIMER`）—— 本 case 的 rc2..rc63 拒绝面就是这条的机械证据。
@@
@@ 故障观察：固件 hmon 的同步异常处理把 `excp_cause_id` 写进 profile 的
@@ fault-record 槽（`machine-vast.inc` 的 `FAULT_RECORD`）并从 `cause_ip + 4`
@@ 复位，因此每条故障例先清槽、触发、再读槽（与 `tests/inst` 的链例同源）。
@@
@@ 寄存器约定：body 用 rd5/rd6、rb20（fault-record 基址）；环境保留 rb1 = 栈、
@@ rb6 = 退出例程、rb30 = 签名写指针（SIG_BEGIN 另用 rd20 预填）。

	.include "machine-vast.inc"
	.include "signature.inc"

	.section .bodycode,"ax",@progbits
	.globl	test_body
test_body:
	SIG_BEGIN ENV_SIG_BUF, ENV_SIG_SLOTS
	set.rb	rb20, FAULT_RECORD

	@@ 槽 0：time_freq（cg10 rc0，RO）
	cfx2rd	cfx_time, cg10, rc0, rd5
	SIGUPD	rd5

	@@ 槽 1：cg10 rc2（保留）读 ⇒ CFXREG
	st.o	rd0, [rb20, 0]		@@ 清故障槽（不靠残留）
	cfx2rd	cfx_time, cg10, rc2, rd6
	ld.o	rd5, [rb20, 0]
	SIGUPD	rd5

	@@ 槽 2：cg10 rc63（保留，rc 上界）读 ⇒ CFXREG
	st.o	rd0, [rb20, 0]
	cfx2rd	cfx_time, cg10, rc63, rd6
	ld.o	rd5, [rb20, 0]
	SIGUPD	rd5

	@@ 槽 3：写 cg10 rc0（RO）⇒ CFXREG
	st.o	rd0, [rb20, 0]
	set.rd	rd6, 0
	cfx2rc	cfx_time, cg10, rc0, rd6
	ld.o	rd5, [rb20, 0]
	SIGUPD	rd5

	@@ 槽 4：写 cg10 rc1（RO）⇒ CFXREG
	st.o	rd0, [rb20, 0]
	set.rd	rd6, 0
	cfx2rc	cfx_time, cg10, rc1, rd6
	ld.o	rd5, [rb20, 0]
	SIGUPD	rd5

	@@ 槽 5：被拒的写没有改到 freq（仍 1 GHz）
	cfx2rd	cfx_time, cg10, rc0, rd5
	SIGUPD	rd5

	@@ 收尾交给环境（rb6 = env_finish）
	jump	[rb6, rd0, 0]
