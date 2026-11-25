@@ ptw_regs.S — `cfx_ptw` 寄存器面 + 地址路由探针（`m16-chipyard-006`）
@@
@@ 目的：用**可失败**的访客侧断言覆盖「Kaiwu-Vast 的地基」两条语义，且判据的
@@ 位号不写死在本文件里：
@@
@@   A 寄存器面（`DADAO-12 §4.5` / `contract-tlb` TLB-03/TLB-04）
@@     1 `cg8 rc8`（`cfx_ptw_enable`）复位 = 0；写 1 读 1；写 0 读 0
@@     2 `cg9 rc0`（`cfx_ptw_ptbr`）写全 1 ⇒ 读回 `[63:56]=0`、`[55:16]=1`、`[15:0]=0`
@@     3 `cg12 rc1`（`tlb_asid`）写全 1 ⇒ 读回 `0xFFFF`（`[63:16]` 读 0）
@@     4 `cg12 rc2`（`tlb_addr_start`）写全 1 ⇒ 读回 `VA[41:0]`（42 位）
@@     5 `cg12 rc3`（`tlb_addr_size`）整 64 位往返
@@     6 `cg12 rc0`（`tlb_control`，WO）写 `none` 与 `clean` 各一次**不报错**
@@     7 `cfx_ptw` 无内部空间：`cg7 rc0/rc1`（desc/start）读 0（`DADAO-12 §3.8`）
@@
@@   B 地址路由（`contract-tlb §10` TLB-40/TLB-41/TLB-42）
@@     8 `ptw_enable = 0` 时核内地址（hmon SRAM）照常读写 ⇒ 只有 `addr[47:42] = 0`
@@       才可能被翻译（TLB-40）
@@     9 `ptw_enable = 1` 时同一核内访问仍成功 ⇒ 核内地址**不进** PTW/TLB（TLB-40）
@@    10`ptw_enable = 1` + `VA[47:42] = 0` 的读 ⇒ `CFXMEM` + 数据缺失类（本任务的
@@       步查是占位、不映射任何页；`contract-tlb §11 ⑨b` 的 `DGPTRAP`）
@@    11 同上但取指 ⇒ `CFXMEM` + 取指缺失类（`IGPTRAP`）
@@    12`ptw_enable = 0` + `VA[47:42] = 0` 的读 ⇒ 只置 `CFXMEM`（无高位位图；TLB-41）
@@    13 同上但取指 ⇒ 只置 `CFXMEM`（无高位位图）
@@
@@ 断言方式：A 段用 `__CHECK_RD`（不等即 `SYS_EXIT(点号)`）；B 段把异常帧里的
@@ `excp_cause_id`/`excp_cause_info` 原样 `__REC` 进结果缓冲，由宿主
@@ `check_ptw_regs.py` **现场从合约解析位号**后逐条比对（本文件不含任何子原因常量，
@@ 也不假设大类位号——`AGENTS.md`「Independent oracle」）。
@@
@@ 载体约定（与 `tools/chipyard/excp/causeid.S` 同源）：故障用例把回落点写进固件
@@ hmon 的返回槽（hmon SRAM `+0xF8`，`aip.si` 现场取），落点读固件槽 `+0xE0`
@@ （cause_id）与 `+0xF0`（cause_info）。每个故障用例的
@@ `aip → add.si(+16) → st.o(返回槽) → 故障访问 → 回落点` 恒为 16 B（取指用例为
@@ 24 B，多一条 `sub.o`/`add.si` 求跳跃目标），`ptw_regs.lds` 对每个用例回读校验。
@@
@@ **本探针只能在 `WumingVastConfig` 上跑**：`Kaiwu-Tiny` 不实现 `cfx_ptw`
@@（`contract-see §3`），第一条 `cfx2rd cfx_ptw, cg8, rc8` 就是 CFXREG。
@@
@@ 用法：
@@   llvm-mc --triple=dadao-unknown-elf -filetype=obj -I . ptw_regs.S -o ptw_regs.o
@@   ld.lld -T ptw_regs.lds ptw_regs.o -o ptw_regs.elf

	.include "tests/inst/macros/inst_test.inc"
	.include "tests/shared/asm/perm_hypv.inc"

	__TEST_BEGIN
	@@ 测试侧两轴放行（`DIV-07` 关闭后 hypv 也判权；body 以 cfx_power 交付）
	PERM_MON_OPEN perm_mon
	set.rb rb20, HMON_BASE		@@ 固件 hmon 的帧槽（+0xE0/0xE8/0xF0/0xF8）
	set.rb rb22, HMON_BASE		@@ 本探针自己的槽（+0xB0 标记、+0xB8/+0xC0 计数）
	@@ SRAM 上电值不保证为 0 ⇒ 探针自己的槽显式清零（`tests/inst/11-cfx` 的教训）
	st.o	rd0, [rb22, 0xB0]
	st.o	rd0, [rb22, 0xB8]
	st.o	rd0, [rb22, 0xC0]

	@@ ================= A 寄存器面 =================
	cfx2rd	cfx_ptw, cg8, rc8, rd5
	__CHECK_RD	1, rd5, 0			@@ TLB-03：复位使能 = 0

	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	cfx2rd	cfx_ptw, cg8, rc8, rd5
	__CHECK_RD	2, rd5, 1

	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	cfx2rd	cfx_ptw, cg8, rc8, rd5
	__CHECK_RD	3, rd5, 0

	@@ PTBR：只存 PPN[55:16]，[15:0] 强制 0、[63:56] 保留 0（§4.5）
	set.rd	rd6, 0xFFFFFFFFFFFFFFFF
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	cfx2rd	cfx_ptw, cg9, rc0, rd5
	__CHECK_RD	4, rd5, 0xFFFFFFFFFF0000

	@@ ASID：[15:0]，[63:16] 读 0（§4.5）
	cfx2rc	cfx_ptw, cg12, rc1, rd6
	cfx2rd	cfx_ptw, cg12, rc1, rd5
	__CHECK_RD	5, rd5, 0xFFFF

	@@ addr_start：VA[41:0]（§4.5）
	cfx2rc	cfx_ptw, cg12, rc2, rd6
	cfx2rd	cfx_ptw, cg12, rc2, rd5
	__CHECK_RD	6, rd5, 0x3FFFFFFFFFF

	@@ addr_size：整 64 位往返（§4.5）
	set.rd	rd6, 0x123456789ABCDEF0
	cfx2rc	cfx_ptw, cg12, rc3, rd6
	cfx2rd	cfx_ptw, cg12, rc3, rd5
	__CHECK_RD	7, rd5, 0x123456789ABCDEF0

	@@ tlb_control（WO，写即执行、无完成状态）：`none` 与 `clean/all` 各写一次。
	@@ 写被拒 ⇒ CFXREG 进 hmon 且不会回到下一条 ⇒ 能走到这里就证明「写不报错」。
	set.rd	rd6, 0				@@ [1:0]=00 none（其余位忽略）
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	set.rd	rd6, 1				@@ [1:0]=01 clean、[3:2]=00 all
	cfx2rc	cfx_ptw, cg12, rc0, rd6

	@@ cfx_ptw 无内部空间：cg7 块 0 的 desc 与 start 都读 0（`DADAO-12 §3.8`）
	cfx2rd	cfx_ptw, cg7, rc0, rd5
	__CHECK_RD	8, rd5, 0
	cfx2rd	cfx_ptw, cg7, rc1, rd5
	__CHECK_RD	9, rd5, 0

	@@ ================= B 地址路由 =================
	@@ 8：ptw_enable = 0 时核内地址（hmon SRAM）可读写 —— 写标记
	set.rd	rd6, 0x55
	st.o	rd6, [rb22, 0xB0]
	ld.o	rd5, [rb22, 0xB0]
	__CHECK_RD	10, rd5, 0x55

	@@ 9：ptw_enable = 1 时同一核内访问仍可读写 ⇒ 核内地址不进 PTW/TLB（TLB-40）
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	ld.o	rd5, [rb22, 0xB0]
	__CHECK_RD	11, rd5, 0x55

	@@ 10：ptw_enable = 1、VA[47:42] = 0 的数据读 ⇒ CFXMEM + 数据缺失类
	set.rb rb4, 0x1000
	.globl	d1_aip
d1_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
d1_fault:
	ld.o	rd18, [rb4, 0]
	.globl	d1_resume
d1_resume:
	ld.o	rd5, [rb20, 0xE0]		@@ excp_cause_id
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]		@@ excp_cause_info
	__REC	rd5

	@@ 11：ptw_enable = 1、VA[47:42] = 0 的取指 ⇒ CFXMEM + 取指缺失类
	set.rb rb4, 0x2000
	.globl	d2_aip
d2_aip:
	aip.si	rb21, 0
	add.si	rb21, 24
	st.o	rb21, [rb20, 0xF8]
	.globl	d2_fault
d2_fault:
	sub.o	rd18, rb4, rb0			@@ = 目标 − 本条地址
	add.si	rd18, -8			@@ jump 的 rb0 比本条晚 8 B（lds ASSERT）
	.globl	d2_jump
d2_jump:
	jump	[rb0, rd18, 0]
	.globl	d2_resume
d2_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 12：ptw_enable = 0、VA[47:42] = 0 的数据读 ⇒ 只置 CFXMEM（无高位位图；TLB-41）
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	set.rb rb4, 0x1000
	.globl	d3_aip
d3_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
d3_fault:
	ld.o	rd18, [rb4, 0]
	.globl	d3_resume
d3_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 13：ptw_enable = 0、VA[47:42] = 0 的取指 ⇒ 只置 CFXMEM（无高位位图）
	set.rb rb4, 0x2000
	.globl	d4_aip
d4_aip:
	aip.si	rb21, 0
	add.si	rb21, 24
	st.o	rb21, [rb20, 0xF8]
	.globl	d4_fault
d4_fault:
	sub.o	rd18, rb4, rb0
	add.si	rd18, -8
	.globl	d4_jump
d4_jump:
	jump	[rb0, rd18, 0]
	.globl	d4_resume
d4_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 收尾：恢复 ptw_enable = 0（不影响后续，仅为把机器留在复位口径）
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	__TEST_END

	__TEST_SECTIONS

	@@ 放行块（cfx_hmon/hypv 下打开目标 cfx 的 hypv 源掩码）
	.text
	.balign 4
perm_mon:
	PERM_OPEN	cfx_ptw
	PERM_MON_CLOSE
