@@ vastwalk.S — DADAO 两级页表走查探针（`m16-chipyard-007`）
@@
@@ 目的：在 `WumingVastConfig` 上覆盖「PTW 两级步查」的功能面，断言值全部由
@@ `tools/chipyard/ptw/gen_vastwalk_tables.py` 独立算出（页表几何/PTE 编码/期望
@@ A/D 值），本文件不含任何手算的索引或位号。
@@
@@   A 走查正确性（`DADAO-12 §2.2.1`/`§2.2.2`）
@@     1 普通页：`VA = PA + 2 TiB` 读到的数据 = 宿主装入该 PA 的值（L1→L2→PA）
@@     8/9 512 MiB 超页：两个 64 MiB 片段（offset 0 / 64 MiB）都命中
@@     10 取指：跳到「VA→PA」映射的可执行页，落点把 `rd7` 置标记后跳回
@@
@@   B A/D（`DADAO-12 §2.2.5`、`contract-tlb` TLB-13…TLB-16）
@@     PTE 在数据页自身（自映射读 = 同页、不触发换出），逐拍读回「内存里的 PTE」：
@@     2 首次读之后 A 仍为 0（本地置位、未回写）
@@     3 `clean` 之后 A = 1（回写内存）
@@     4 首次 store 之后 D 仍为 0（本地）
@@     5 `clean` 之后 D = 1
@@     6 再 `clean`（无挂起）PTE 不变（「再次访问不再置」⇒ 无多余回写，宿主按
@@       `ad-wb` 事件计数核对）
@@     7 store 的数据真的落到内存（读回）
@@
@@   C 故障路径（spec 顺序：缺页 → 小页缺失 → HSJU → R/W/X）
@@     11 L1 `P=0, SP=0` ⇒ CFXMEM + DGPTRAP
@@     12 L1 `P=0, SP=1` ⇒ CFXMEM + DSPTRAP
@@     13 L1 `P=1, SP=1` 且 SPF 位 = 0 ⇒ CFXMEM + DSPFTRAP
@@     14 L2 `P=0` ⇒ CFXMEM + DGPTRAP
@@     15 L2 `P=1` 且 GPF 位 = 0 ⇒ CFXMEM + DGPFTRAP
@@     16 HSJU 不符（U-only 而运行在 hypv）⇒ CFXPERM + NHPERM
@@     17 `W=0` 的页做 `st` ⇒ CFXPERM + NWPERM
@@     18 `X=0` 的页取指 ⇒ CFXPERM + NXPERM
@@     19 `tlb_control` 的 scope = `11`（保留编码）⇒ CFXREG（TLB-24）
@@
@@ 断言方式：A/B 段用 `__CHECK_RD`（不等即 `SYS_EXIT(点号)`）；C 段把异常帧里的
@@ `excp_cause_id`/`excp_cause_info` 原样 `__REC` 进结果缓冲，由宿主
@@ `check_vastwalk.py` 现场从 `spec/DADAO-12 §3.6` / `contract-tlb` 解析位号后逐条
@@ 比对（本文件不含子原因常量）。
@@
@@ 载体约定（与 `tools/chipyard/ptw/vastptw.S` 同源）：故障用例把回落点写进固件
@@ hmon 的返回槽（hmon SRAM `+0xF8`，`aip.si` 现场取），落点读固件槽 `+0xE0`
@@ （cause_id）与 `+0xF0`（cause_info）。数据类故障例的
@@ `aip → add.si(+16) → st.o(返回槽) → 故障访问 → 回落点` 恒为 16 B；取指类为
@@ 24 B（多 `sub.o`/`add.si` 求跳跃目标）。`vastwalk.lds` 对每个用例回读校验。
@@
@@ 页表与数据由 `+loadmem=` 装入 PA RAM（`vastwalk.lds` 的段就放在 PA：
@@ L1 表 0、L2 表 0x1_0000、故障表 0x3_0000、可执行页 0x5_0000、超页 0x4000_0000
@@ / 0x4400_0000）；本探针自身在核内 SRAM（`addr[47:42] ≠ 0`，不经翻译）。
@@
@@ 用法：
@@   python3 tools/chipyard/ptw/gen_vastwalk_tables.py --emit inc > vastwalk_tables.inc
@@   llvm-mc --triple=dadao-unknown-elf -filetype=obj -I . -I <dir of the inc> vastwalk.S -o vastwalk.o
@@   ld.lld -T vastwalk.lds vastwalk.o -o vastwalk.elf

	.include "tests/inst/macros/inst_test.inc"
	.include "vastwalk_tables.inc"

	__TEST_BEGIN
	LOAD_ADDR rb20, HMON_BASE		@@ 固件 hmon 的帧槽（+0xE0/0xF0/0xF8）

	@@ PTBR = 0（PA 0 的 L1 表），开 PTW
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6

@@ `CASE_ADWB=1` = ADWBFAIL 专用镜像（只跑第 20 段，供实现层注入用）
.ifndef CASE_ADWB
.set CASE_ADWB, 0
.endif

.if CASE_ADWB == 0
	@@ ================= A 走查正确性 =================
	@@ 1 普通页：L1 → L2 → PA，且 VA = PA + 2 TiB
	LOAD_ADDR rb4, VA_DATA
	ld.o	rd5, [rb4, 0x700]
	__CHECK_RD	1, rd5, PAYLOAD

	@@ ================= B A/D =================
	@@ 2 首次访问之后，内存里的 PTE 仍 A=0（本地挂起，未回写）
	ld.o	rd5, [rb4, 8]
	__CHECK_RD	2, rd5, PTE_DATA_A0D0

	@@ 3 clean/all 回写本地 A
	set.rd	rd6, 1			@@ [1:0]=01 clean、[3:2]=00 all
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb4, 8]
	__CHECK_RD	3, rd5, PTE_DATA_A1D0

	@@ 4 首次 store（A 已是 1）只把 D 本地置位
	LOAD_ADDR rb5, STORE_VAL
	st.o	rb5, [rb4, 0x708]
	ld.o	rd5, [rb4, 8]
	__CHECK_RD	4, rd5, PTE_DATA_A1D0

	@@ 5 clean 回写 D
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb4, 8]
	__CHECK_RD	5, rd5, PTE_DATA_A1D1

	@@ 6 无挂起位的 clean 不产生回写 ⇒ PTE 逐位不变
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	ld.o	rd5, [rb4, 8]
	__CHECK_RD	6, rd5, PTE_DATA_A1D1

	@@ 7 store 的数据写到了 PA
	ld.o	rd5, [rb4, 0x708]
	__CHECK_RD	7, rd5, STORE_VAL

	@@ 8/9 512 MiB 超页：两个 64 MiB 片段
	LOAD_ADDR rb4, VA_SUPER
	ld.o	rd5, [rb4, 0]
	__CHECK_RD	8, rd5, MAGIC0
	LOAD_ADDR rb4, VA_SUPER1
	ld.o	rd5, [rb4, 0]
	__CHECK_RD	9, rd5, MAGIC1

	@@ 10 取指走页表：跳到映射页，桩把 rd7 置 STUB_MARK 后跳回
	@@    （返回地址由 `aip.si` 现场取 + 链接期常量偏移 ⇒ 不写死绝对地址）
	LOAD_ADDR rb4, VA_CODE
	.globl	vw_jump_site
vw_jump_site:
	aip.si	rb6, 0
	add.si	rb6, 12			@@ = 两条指令（8 B）+ 本条（4 B），由 .lds ASSERT 回读校验
	jump	[rb4, rd0, 0]
	.globl	vw_back
vw_back:
	__CHECK_RD	10, rd7, STUB_MARK

	@@ ================= C 故障路径 =================
	@@ 11 L1 P=0, SP=0 ⇒ CFXMEM + DGPTRAP
	LOAD_ADDR rb4, VA_L1_NP
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f1_aip
f1_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f1_fault:
	ld.o	rd18, [rb4, 0]
	.globl	f1_resume
f1_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 12 L1 P=0, SP=1 ⇒ CFXMEM + DSPTRAP
	LOAD_ADDR rb4, VA_L1_SP
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f2_aip
f2_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f2_fault:
	ld.o	rd18, [rb4, 0]
	.globl	f2_resume
f2_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 13 L1 SPF 对应位 = 0 ⇒ CFXMEM + DSPFTRAP
	LOAD_ADDR rb4, VA_L1_SPF
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f3_aip
f3_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f3_fault:
	ld.o	rd18, [rb4, 0]
	.globl	f3_resume
f3_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 14 L2 P=0 ⇒ CFXMEM + DGPTRAP
	LOAD_ADDR rb4, VA_L2B0
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f4_aip
f4_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f4_fault:
	ld.o	rd18, [rb4, 0]
	.globl	f4_resume
f4_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 15 L2 GPF 对应位 = 0 ⇒ CFXMEM + DGPFTRAP
	LOAD_ADDR rb4, VA_L2B1
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f5_aip
f5_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f5_fault:
	ld.o	rd18, [rb4, 0]
	.globl	f5_resume
f5_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 16 HSJU 不符（U-only 页、运行在 hypv）⇒ CFXPERM + NHPERM
	LOAD_ADDR rb4, VA_L2B2
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f6_aip
f6_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f6_fault:
	ld.o	rd18, [rb4, 0]
	.globl	f6_resume
f6_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 17 W=0 的页做 st ⇒ CFXPERM + NWPERM
	LOAD_ADDR rb4, VA_W0
	LOAD_ADDR rb5, STORE_VAL
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f7_aip
f7_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f7_fault:
	st.o	rb5, [rb4, 0]
	.globl	f7_resume
f7_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 18 X=0 的页取指 ⇒ CFXPERM + NXPERM
	LOAD_ADDR rb4, VA_NOX
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f8_aip
f8_aip:
	aip.si	rb21, 0
	add.si	rb21, 24
	st.o	rb21, [rb20, 0xF8]
	.globl	f8_fault
f8_fault:
	sub.o	rd18, rb4, rb0			@@ = 目标 − 本条地址
	add.si	rd18, -8			@@ jump 的 rb0 比本条晚 8 B
	.globl	f8_jump
f8_jump:
	jump	[rb0, rd18, 0]
	.globl	f8_resume
f8_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 19 tlb_control 的 scope = 11（保留编码）⇒ CFXREG（TLB-24）
	set.rd	rd6, 0x0D			@@ op=01 clean、scope=11
	st.o	rd0, [rb20, 0xE0]		@@ 清帧槽：故障没发生 ⇒ 判据看到 0 而不是残留
	st.o	rd0, [rb20, 0xF0]
	.globl	f9_aip
f9_aip:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
f9_fault:
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.globl	f9_resume
f9_resume:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

.endif	@@ CASE_ADWB == 0（ADWBFAIL 专用镜像只跑下面的 20 段）

	@@ 20 A/D 回写失败：本机 PA RAM 全可写 ⇒ 机器级不可达（`contract-tlb §11` ⑦），
	@@    由证据脚本的实现层注入（强制 PTE 写失败）触发；未注入时这里记录到全 0。
	LOAD_ADDR rb4, VA_FRESH
	ld.o	rd5, [rb4, 0]			@@ 填充：A 本地置位（PTE.A = 0）
	__CHECK_RD	20, rd5, FRESH_MAGIC
	st.o	rd0, [rb20, 0xE0]
	st.o	rd0, [rb20, 0xF0]
	.globl	f20_aip
f20_aip:
	aip.si	rb21, 0
	add.si	rb21, 20			@@ set.rd + cfx2rc ⇒ 回落点 = aip + 20
	st.o	rb21, [rb20, 0xF8]
f20_fault:
	set.rd	rd6, 1			@@ clean/all：回写挂起的 A
	cfx2rc	cfx_ptw, cg12, rc0, rd6
	.globl	f20_after
f20_after:
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5

	@@ 收尾：关 PTW（把机器留在复位口径），打印结果缓冲并 SYS_EXIT(0)
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg8, rc8, rd6
	__TEST_END

	@@ 数据段：数据页 payload / 超页两个片段（PA 由 .lds 钉住）
	.section .pagedata, "aw"
	.p2align 3
	.dd.o64	PAYLOAD
	.dd.o64	0

	.section .fresh, "aw"
	.p2align 3
	.dd.o64	FRESH_MAGIC

	.section .super0, "aw"
	.p2align 3
	.dd.o64	MAGIC0

	.section .super1, "aw"
	.p2align 3
	.dd.o64	MAGIC1

	@@ 取指用例的桩：经 VA 映射到 PA 0x5_0000 执行，把 rd7 置标记后跳回
	.section .stub, "ax"
	.globl	vw_stub
vw_stub:
	set.rd	rd7, STUB_MARK
	jump	[rb6, rd0, 0]			@@ rb6 = 探针算好的返回地址

	__TEST_SECTIONS
