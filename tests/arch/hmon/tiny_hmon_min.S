@@ tiny_hmon_min.S — QEMU 端的 Tiny hmon「最小保存-跳转」行为用例
@@ （m13-integ-007；算法见 .tao/knowledge/refs/m12-006-cycle-design.md §11）
@@
@@ 加载契约：宿主只装本应用 ELF（crt + 本文件，SRAM-only，固定入口 ENTRY）；
@@ 固定 64 KiB BootROM（共享 power stub + hmon.S）由 `bootrom-image` 提供。
@@
@@ 用例职责（测试框架 = 本程序）：
@@   1. 移交闭环：应用能运行、hmon 槽 0xE0/0xE8/0xF0 保存的是 power 的
@@      CFXTRAP 现场，槽 0xF8 是 power 写入的默认返回地址（trap+4）；
@@   2. 五类同步异常各 1 例（CFXMEM/ILLI/UNDI/MALIGN/IALIGN）：每例前把
@@      槽 0xF8 写成不同的 landing 地址，事后读回 hmon 槽，逐值交给驱动
@@      与独立期望值比较；
@@   3. 每例把 rd63 置为哨兵值，事后记录 rd63 与 hmon 槽 0xD8（保存值）；
@@   4. landing 前两条指令写 poison=0xdead：若 hmon 采用旧的 `+4` 策略，
@@      poison 会被执行，驱动据此判 FAIL（本用例不依赖 hmon 的任何判断）。
@@   5. 控制流只用 call/branch/escape，不引入 jump（用户 2026-11-11 修正）。
@@
@@ 结果：连续 6 条 64 字节记录（id, cause_id, cause_ip, cause_info,
@@ rd63_after, saved_rd63, return_slot, poison）写到 RESULTS，经 semihosting
@@ SYS_OPEN/SYS_WRITE 导出；判据由 tools/testcases/arch/min_rom_probe_integ007t.py
@@ 用独立期望值逐值比较。

	.include "machine-tiny.inc"
	.include "machine.inc"

	.equ	RESULTS, ENTRY + 0x4000
	.equ	PARAM,   ENTRY + 0x5000
	.equ	FNAME,   ENTRY + 0x5100
	.equ	MSG,     ENTRY + 0x5200
	.equ	IALIGN_TARGET, ENTRY + 0x1D01

	@@ 绝对地址（链接期 R_DADAO_ABS48）：把符号地址装入 64 位寄存器。
	.macro	LOAD_ABS rd, sym
	set.zw	\rd, wp0, \sym
	or.w	\rd, wp1, \sym
	or.w	\rd, wp2, \sym
	or.w	\rd, wp3, \sym
	.endm

	.section .text.start, "ax"
	.globl	_start
_start:
	LOAD_ADDR rb1, SP			@@ crt：入口设 SP（Machine-v5 §6）
	@@ 顺序落入紧随其后的 .text（同段、4 字节对齐、无填充）

	.text
	.globl	hmon_min_main
hmon_min_main:
	LOAD_ADDR rb3, RESULTS
	LOAD_ADDR rb5, HMON_BASE

	@@ ---- record 0: power -> hmon 移交现场 + 默认返回地址 ------------------
	ld.o	rd10, [rb5, 0xE0]		@@ cause_id (CFXTRAP)
	ld.o	rd11, [rb5, 0xE8]		@@ cause_ip (power 的 trap)
	ld.o	rd12, [rb5, 0xF0]		@@ cause_info (trap 编码)
	set.zw	rd13, wp0, 0
	st.o	rd13, [rb3, 0]
	st.o	rd10, [rb3, 8]
	st.o	rd11, [rb3, 16]
	st.o	rd12, [rb3, 24]
	add.si	rb3, 32
	ld.o	rd10, [rb5, 0xF8]		@@ power 写的默认返回地址
	st.o	rd10, [rb3, 0]
	ld.o	rd10, [rb5, 0xD8]		@@ 移交时保存的 rd63
	st.o	rd10, [rb3, 8]
	cfx2rd	cfx_hmon, cg3, rc10, rd10	@@ 异常向量（power 不改）
	st.o	rd10, [rb3, 16]
	st.o	rd0, [rb3, 24]
	add.si	rb3, 32

	@@ ---- 1: CFXMEM -> land_mem -------------------------------------------
	LOAD_ABS rd5, land_mem
	st.o	rd5, [rb5, 0xF8]
	LOAD_ADDR rd63, 0x1111222233334444
	set.zw	rd20, wp0, 0
	LOAD_ADDR rb2, 0x1000000000
	.globl	f_mem
f_mem:
	ld.o	rd10, [rb2, 0]
	set.zw	rd20, wp0, 0xdead
	set.zw	rd21, wp0, 0xbeef
	.globl	land_mem
land_mem:
	set.zw	rd13, wp0, 1
	call	[rb0, record]

	@@ ---- 2: ILLI -> land_illi -------------------------------------------
	LOAD_ABS rd5, land_illi
	st.o	rd5, [rb5, 0xF8]
	LOAD_ADDR rd63, 0x2222333344445555
	set.zw	rd20, wp0, 0
	.globl	f_illi
f_illi:
	trap	cfx7, 0
	set.zw	rd20, wp0, 0xdead
	set.zw	rd21, wp0, 0xbeef
	.globl	land_illi
land_illi:
	set.zw	rd13, wp0, 2
	call	[rb0, record]

	@@ ---- 3: UNDI -> land_undi --------------------------------------------
	LOAD_ABS rd5, land_undi
	st.o	rd5, [rb5, 0xF8]
	LOAD_ADDR rd63, 0x3333444455556666
	set.zw	rd20, wp0, 0
	.globl	f_undi
f_undi:
	.dd.t32	0x08040001
	set.zw	rd20, wp0, 0xdead
	set.zw	rd21, wp0, 0xbeef
	.globl	land_undi
land_undi:
	set.zw	rd13, wp0, 3
	call	[rb0, record]

	@@ ---- 4: MALIGN -> land_malign ----------------------------------------
	LOAD_ABS rd5, land_malign
	st.o	rd5, [rb5, 0xF8]
	LOAD_ADDR rd63, 0x4444555566667777
	set.zw	rd20, wp0, 0
	LOAD_ADDR rb2, RAM_BASE + 1
	.globl	f_malign
f_malign:
	ld.o	rd10, [rb2, 0]
	set.zw	rd20, wp0, 0xdead
	set.zw	rd21, wp0, 0xbeef
	.globl	land_malign
land_malign:
	set.zw	rd13, wp0, 4
	call	[rb0, record]

	@@ ---- 5: IALIGN -> land_ialign ----------------------------------------
	LOAD_ABS rd5, land_ialign
	st.o	rd5, [rb5, 0xF8]
	LOAD_ADDR rd63, 0x5555666677778888
	set.zw	rd20, wp0, 0
	LOAD_ADDR rb2, IALIGN_TARGET
	.globl	f_ialign
f_ialign:
	call	[rb2, rd0, 0]
	set.zw	rd20, wp0, 0xdead
	set.zw	rd21, wp0, 0xbeef
	.globl	land_ialign
land_ialign:
	set.zw	rd13, wp0, 5
	call	[rb0, record]

	@@ ---- export the observation table ------------------------------------
	LOAD_ADDR rb4, MSG
	LOAD_ADDR rd6, 0x686d6f6e2d6d696e
	st.o	rd6, [rb4, 0]
	LOAD_ADDR rd6, 0x2d6f6b0a00000000
	st.o	rd6, [rb4, 8]

	LOAD_ADDR rb4, FNAME
	LOAD_ADDR rd6, 0x686d6f6e5f6d696e
	st.o	rd6, [rb4, 0]
	LOAD_ADDR rd6, 0x5f726573756c7473
	st.o	rd6, [rb4, 8]
	LOAD_ADDR rd6, 0x2e62696e00000000
	st.o	rd6, [rb4, 16]

	LOAD_ADDR rb16, MSG
	set.zw	rd16, wp0, 0x0004		@@ SYS_WRITE0
	trap	cfx_hmon, 0x3FF00

	LOAD_ADDR rb4, PARAM
	LOAD_ADDR rb5, FNAME
	st.o	rb5, [rb4, 0]
	set.zw	rd6, wp0, 5			@@ binary + create
	st.o	rd6, [rb4, 8]
	set.zw	rd6, wp0, 21			@@ filename length + NUL
	st.o	rd6, [rb4, 16]
	set.zw	rd16, wp0, 0x0001		@@ SYS_OPEN
	LOAD_ADDR rb16, PARAM
	trap	cfx_hmon, 0x3FF00

	LOAD_ADDR rb4, PARAM
	st.o	rd8, [rb4, 0]			@@ handle
	LOAD_ADDR rb5, RESULTS
	st.o	rb5, [rb4, 8]			@@ buffer
	set.zw	rd6, wp0, 0x1000
	st.o	rd6, [rb4, 16]
	set.zw	rd16, wp0, 0x0005		@@ SYS_WRITE
	LOAD_ADDR rb16, PARAM
	trap	cfx_hmon, 0x3FF00

	LOAD_ADDR rb4, PARAM
	set.zw	rd6, wp1, 0x0002
	or.w	rd6, wp0, 0x0026		@@ ADP_Stopped_ApplicationExit
	st.o	rd6, [rb4, 0]
	set.zw	rd6, wp0, 0x0021		@@ PASS
	st.o	rd6, [rb4, 8]
	set.zw	rd16, wp0, 0x0018		@@ SYS_EXIT
	LOAD_ADDR rb16, PARAM
	trap	cfx_hmon, 0x3FF00
	swym	0

@@ ---------------------------------------------------------------------------
@@ record: rd13 = record id（其余现场值从 hmon 槽重读）。追加 8 个 octa。
@@ ---------------------------------------------------------------------------
record:
	ld.o	rd10, [rb5, 0xE0]
	ld.o	rd11, [rb5, 0xE8]
	ld.o	rd12, [rb5, 0xF0]
	st.o	rd13, [rb3, 0]
	st.o	rd10, [rb3, 8]
	st.o	rd11, [rb3, 16]
	st.o	rd12, [rb3, 24]
	add.si	rb3, 32
	st.o	rd63, [rb3, 0]			@@ rd63 异常后值
	ld.o	rd10, [rb5, 0xD8]		@@ hmon 保存的 rd63
	st.o	rd10, [rb3, 8]
	ld.o	rd10, [rb5, 0xF8]		@@ hmon 读到的返回地址槽
	st.o	rd10, [rb3, 16]
	st.o	rd20, [rb3, 24]			@@ poison（+4 策略会写成 0xdead）
	add.si	rb3, 32
	ret	rd0, 0
