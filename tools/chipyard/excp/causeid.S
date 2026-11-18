@@ causeid.S — `excp_cause_id` 全宽（低 16 位大类 + 子原因 wyde）探针
@@
@@ 目的（`m16-chipyard-003`）：把 **整 64 位** `cfx_<monitor>_excp_cause_id` 与
@@ `excp_cause_info` 从**异常帧**里读出来逐字节打印，供宿主逐条与
@@ `contract-see §6.1/§6.1.1`（逐位等价于 `spec/DADAO-12 §3.6`）对齐，
@@ 并作三方（chipyard / QEMU / gem5）**字节流全宽**比较（不再掩码低 16 位）。
@@
@@ 载体约定（与 `tests/inst/**` 同源）：一个 ELF 在三个平台上跑同一条硬件路径 ——
@@ 异常向量 → 固件 hmon（`tests/ee-tiny/hmon_tiny.S`：最小保存-跳转）→
@@ `escape` 回框架写在 hmon SRAM `+0xF8` 的回落点。固件把 `cg5 rc2/rc3/rc4`
@@ 存进 hmon SRAM `+0xE0/+0xE8/+0xF0`，探针在回落点读 `+0xE0`（cause_id）与
@@ `+0xF0`（cause_info）各记 8 字节 ⇒ 每个用例 16 字节，按 `__PRINT` 逐字节打印。
@@
@@ 回落点地址用 `aip.si rb21, 0` + `add.si` 现场取（`rb0` 口径；标签差进不了立即数，
@@ 见 `tests/inst/MIGRATION.md §6`）：`aip → add.si(+16) → st.o(返回槽) → 故障指令 → 回落点`
@@ 恒为 16 B ⇒ 每个用例同一个常量；`causeid.lds` 对每个用例的
@@ `resume == aip + 16` 下 ASSERT（手写常量由链接器回读校验）。
@@
@@ 用例（每类一个）：① 数据 `CFXMEM`（窗口外读）② 取指 `CFXMEM`（跳到窗口外）
@@ ③ `ILLI`（保留 cfx 的 trap）④ `UNDI`（QFC 空白格）⑤ `MALIGN`（8 字节未对齐）
@@ ⑥ `CFXREG`（已实现 cfx 的未实现 cg）⑦ `CFXTRAP`（hmon 移交）⑧ `IALIGN`
@@ （跳到 `IP[1:0] != 0`）。
@@
@@ **子原因期望值不写在本文件里**：宿主 `check_causeid.py` 现场从合约解析位号
@@ （`AGENTS.md`「Independent oracle」），本载体只负责把实测值原样搬出来。
@@ 本 profile（`WumingTinyConfig`）无页表走查，`CFXMEM` 一律是
@@ `[57] NONPTW`（`DADAO-12 §3.6 (四)`）；页表缺失类与 `ADWBFAIL` 在本 profile
@@ 不可构造（无 TLB/PTW），非 `CFXMEM`/`CFXPERM` 的 cause 两个 wyde 必须全 0。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN

	@@ 固件 hmon 的返回槽（hmon SRAM +0xF8）：每个用例先写自己的回落点。
	LOAD_ADDR rb20, HMON_BASE

	@@ ① 数据 CFXMEM：窗口外读（`cause_info` = 访存地址）
	LOAD_ADDR rb4, 0x1000000000
	.globl	c1_aip
c1_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
c1_fault:
	ld.o	rd18, [rb4, 0]
	.globl	c1_resume
c1_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ ② 取指 CFXMEM：跳到窗口外取指（`cause_info` = 被取指地址）
	@@ `jump [rb0, rd, 0]` 的目标 = `rb0`（该 jump 自身地址）+ rd ⇒ 差值在**执行点**
	@@ 用 `rb4 - rb0` 求，不依赖布局常量（`aip` 只用于取返回槽地址）。
	LOAD_ADDR rb4, 0x1000000000
	.globl	c2_aip
c2_aip:
	aip.si	rb21, 0
	add.si	rb21, 24
	st.o	rb21, [rb20, 0xF8]
	.globl	c2_fault
c2_fault:
	sub.o	rd18, rb4, rb0		@@ = 目标 - 本条地址
	add.si	rd18, -8		@@ jump 的 rb0 比本条晚 8 B（`causeid.lds` ASSERT 钉住）
	.globl	c2_jump
c2_jump:
	jump	[rb0, rd18, 0]
	.globl	c2_resume
c2_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ ③ ILLI：保留 cfx 的 `trap`
	.globl	c3_aip
c3_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
c3_fault:
	trap	cfx7, 0
	.globl	c3_resume
c3_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ ④ UNDI：QFC 空白格
	.globl	c4_aip
c4_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
c4_fault:
	.dd.t32	0x08040001
	.globl	c4_resume
c4_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ ⑤ MALIGN：8 字节访问未对齐（`cause_info` = 访存地址）
	LOAD_ADDR rb4, RAM_BASE+1
	.globl	c5_aip
c5_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
c5_fault:
	ld.o	rd18, [rb4, 0]
	.globl	c5_resume
c5_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ ⑥ CFXREG：保留寄存器 `cg5 rc63`（`spec/DADAO-12 §3.6`：保留 ⇒ CFXREG，
	@@ 三个实现一致；`cause_info` = 触发指令编码）。`cg5 rc1` 自 m14-spec-009 起是
	@@ `excp_prev_cfx_code`（RW），不再是保留寄存器，故换用表内明写 reserved 的 rc63。
	.globl	c6_aip
c6_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
c6_fault:
	cfx2rd	cfx_hmon, cg5, rc63, rd18
	.globl	c6_resume
c6_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ ⑦ CFXTRAP：`trap cfx_hmon` 移交（`cause_info` = 指令编码）
	.globl	c7_aip
c7_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
c7_fault:
	trap	cfx_hmon, 0x1234
	.globl	c7_resume
c7_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ ⑧ IALIGN：跳到 `IP[1:0] != 0`（`cause_info` = 该 IP）
	LOAD_ADDR rb4, RAM_BASE+2
	.globl	c8_aip
c8_aip:
	aip.si	rb21, 0
	add.si	rb21, 24
	st.o	rb21, [rb20, 0xF8]
	.globl	c8_fault
c8_fault:
	sub.o	rd18, rb4, rb0		@@ = 目标 - 本条地址
	add.si	rd18, -8		@@ jump 的 rb0 比本条晚 8 B（`causeid.lds` ASSERT 钉住）
	.globl	c8_jump
c8_jump:
	jump	[rb0, rd18, 0]
	.globl	c8_resume
c8_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	__TEST_END
