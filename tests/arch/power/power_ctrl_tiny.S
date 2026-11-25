@@ tests/arch/power/power_ctrl_tiny.S — `cfx_power ctrl`（`cg8 rc1`，WO）在
@@ Kaiwu-Tiny 上的 profile 门控探针（`m16-chipyard-031`）。
@@
@@ `spec/Kaiwu §3` 明写 Kaiwu-Tiny **未实现** `cfx_power_ctrl` ⇒ 访问 `CFXREG`
@@ （显式失败，不设静默成功的桩）。RTL 的写侧只在 `useVM`（Kaiwu-Vast）打开；
@@ 本探针在 Tiny 上写 0，期望 `CFXREG` 的 one-hot 落点；写若被接受 ⇒ 该例体末尾
@@ 的 `__EXIT 1` 判红。运行：
@@   python3 tests/ee-tiny/run_inst_tiny.py --vectors tests/arch/power \
@@       --id power_ctrl_tiny --platforms chipyard --chipyard <Tiny sim>
	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ 故障例：写 `cfx_power cg8 rc1`（WO）⇒ Tiny 未实现 ⇒ CFXREG。
	__FAULT_BODY_BEGIN 1
	__FAULT_GUARD 1, CFXREG
	set.rd	rd6, 0
	cfx2rc	cfx_power, cg8, rc1, rd6
	__FAULT_BODY_END 1

	__TEST_END
	__TEST_SECTIONS
