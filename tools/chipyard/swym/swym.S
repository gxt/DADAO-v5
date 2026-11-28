@@ swym.S — `swym N` 多拍时延 + 高位 SBZ/ILLI 的 RTL 探针（`m19-chipyard-003`）
@@
@@ 判据（`spec/SimRISC-12 §2`，`m19-spec-001` 定稿）：
@@   * `N = immu18[11:0]`（12 位）；`immu18[17:12]` 为 SBZ，非 0 ⇒ `ILLI`；
@@   * `swym 0` 总时延 1 拍，`swym N` 总时延 1 + N 拍；
@@   * 执行期间不取中断（原子）。本载体的宿主判据在 `check_swym.py`：
@@     周期 = `swym-done.cycle - swym.cycle + 1`（`+verbose` trace），
@@     ILLI 的 `cause_id` / `cause_ip` / `cause_info` 与 ELF 符号/指令字独立对照。
@@
@@ 载体约定（与 `tools/chipyard/excp/causeid.S` 同源）：Kaiwu-Tiny 固定 BootROM
@@ 固件（power stub → cfx_hmon → 本 ELF）。hmon 从 SRAM `+0xF8` 取返回地址 ⇒
@@ 每个 ILLI 例先用 `aip.si → add.si(+16) → st.o` 把返回槽指向 `aip + 16`
@@ （= 原始编码字之后的下一条指令），该布局由 `swym.lds` 的 ASSERT 回钉。
@@ 回落点核对 hmon 保存的 `cause_id`（`+0xE0`）与 `cause_info`（`+0xF0`）。
@@
@@ 期望值（独立 oracle，来自 spec/SimRISC-12 §2）：
@@   ILLI 位 = `1 << 8`（`contract-see §6.1` = `spec/DADAO-12 §3.6`）；
@@   ILLI 的 `cause_info` = 触发指令的 32 位编码字（`spec/Kaiwu §4.4`）。
@@
@@ 用法（同一 ELF 只跑 chipyard WumingTinyConfig）：
@@   llvm-mc --triple=dadao-unknown-elf -filetype=obj swym.S -o swym.o
@@   ld.lld -T swym.lds swym.o -o swym.elf
@@   simulator-chipyard.harness-WumingTinyConfig +permissive +verbose \
@@       +loadmem=swym.elf +semiout=swym.out +max-cycles=... +permissive-off none

	.include "tests/shared/asm/machine-tiny.inc"

	.equ	PARAM, ENTRY + 0x6000		@@ SYS_EXIT 参数块

	.text
	.globl	_start
_start:
	set.rb	rb20, HMON_BASE
	set.rb	rb21, fail
	st.o	rb21, [rb20, 0xF8]		@@ 意外异常 ⇒ fail（不静默重启）

	@@ ---- 时延：N = 0 / 1 / 4095（trace 判据：done - start + 1）----
	.globl	sw_n0
sw_n0:
	swym	0
	.globl	sw_n1
sw_n1:
	swym	1
	.globl	sw_n4095
sw_n4095:
	swym	4095

	@@ ---- ILLI ①：低 12 位 = 0、bit12 置位（immu18 = 0x1000）----
	.globl	sw_aip0
sw_aip0:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	sw_illi0
sw_illi0:
	.dd.t32	0x47881000
	.globl	sw_resume0
sw_resume0:
	set.zw	rd31, wp0, 0x0001
	ld.o	rd15, [rb20, 0xE0]
	set.rd	rd16, 0x100
	cmp.uo	rd30, rd15, rd16
	br.nz	{rd30}?, [rb0, fail]
	set.zw	rd31, wp0, 0x0002
	ld.o	rd15, [rb20, 0xF0]
	set.rd	rd16, 0x47881000
	cmp.uo	rd30, rd15, rd16
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- ILLI ②：immu18[17:12] 全 1（0x3FFFF）----
	.globl	sw_aip1
sw_aip1:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	sw_illi1
sw_illi1:
	.dd.t32	0x478BFFFF
	.globl	sw_resume1
sw_resume1:
	set.zw	rd31, wp0, 0x0003
	ld.o	rd15, [rb20, 0xE0]
	set.rd	rd16, 0x100
	cmp.uo	rd30, rd15, rd16
	br.nz	{rd30}?, [rb0, fail]
	set.zw	rd31, wp0, 0x0004
	ld.o	rd15, [rb20, 0xF0]
	set.rd	rd16, 0x478BFFFF
	cmp.uo	rd30, rd15, rd16
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- ILLI ③：低 12 位合法（N = 7）但 bit17 置位（immu18 = 0x20007）----
	.globl	sw_aip2
sw_aip2:
	aip.si	rb21, 0
	add.si	rb21, 16
	st.o	rb21, [rb20, 0xF8]
	.globl	sw_illi2
sw_illi2:
	.dd.t32	0x478A0007
	.globl	sw_resume2
sw_resume2:
	set.zw	rd31, wp0, 0x0005
	ld.o	rd15, [rb20, 0xE0]
	set.rd	rd16, 0x100
	cmp.uo	rd30, rd15, rd16
	br.nz	{rd30}?, [rb0, fail]
	set.zw	rd31, wp0, 0x0006
	ld.o	rd15, [rb20, 0xF0]
	set.rd	rd16, 0x478A0007
	cmp.uo	rd30, rd15, rd16
	br.nz	{rd30}?, [rb0, fail]

	@@ ---- pass ----
	set.rb	rb16, PARAM
	set.rd	rd20, 0x20026			@@ ADP_Stopped_ApplicationExit
	set.zw	rd21, wp0, 0x0000		@@ status 0 = pass
	st.o	rd20, [rb16, 0]
	st.o	rd21, [rb16, 8]
	set.zw	rd16, wp0, 0x0018		@@ SYS_EXIT
	trap	cfx_hmon, 0x3FF18
pass_spin:
	br.z	{rd0}?, [rb0, pass_spin]

	@@ ---- failure: SYS_EXIT(0x40 + check id) ----
fail:
	set.rb	rb16, PARAM
	set.rd	rd20, 0x20026
	add.si	rd31, 0x40
	st.o	rd20, [rb16, 0]
	st.o	rd31, [rb16, 8]
	set.zw	rd16, wp0, 0x0018
	trap	cfx_hmon, 0x3FF18
fail_spin:
	br.z	{rd0}?, [rb0, fail_spin]

	@@ ---- SYS_EXIT 参数块（运行时写，不进镜像）----
	.org	PARAM - ENTRY
	.space	16

	.section .note.GNU-stack, "", @progbits
