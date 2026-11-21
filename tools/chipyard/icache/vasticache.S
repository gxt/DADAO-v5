@@ vasticache.S — DADAO I-Cache 探针（`m16-chipyard-010`）
@@
@@ 目的：在 `WumingVastConfig` 上覆盖「8 路 × 128 组 × 64 B、只读、无 dirty、
@@ 缺失按 8 beat 填充」的取指侧语义面。页表几何、PTE 值、块 magic、组索引
@@ 全部由 `tools/chipyard/icache/gen_vasticache_tables.py` 独立算出（本文件
@@ 不含手算的索引/位域）。
@@
@@   A 命中 / 缺失（取指侧）
@@     r0：跳到 A1（PA 0x2_1000，一行 64 B = 16 条指令 = 8 beat）
@@         ⇒ 第 1 拍缺失（8 beat 填充），随后 7 拍命中（判据核日志计数）
@@
@@   B 8 路同组 + LRU
@@     r1..r7：A2..A8（同组 PA[12:6] = 64，8 个不同 tag）各一条 ⇒ 8 路 coexist
@@     r8：A9（同组第 9 行）⇒ 按 LRU 淘汰 A1
@@     r9：再访 A1 ⇒ 已被淘汰、重填（再淘汰 A2）
@@
@@   C 组索引位宽（PA[12:6] 7 位）
@@     r10：C1（PA[12:6] = 0；PA[12] 与 A 行相反，但 PA[11:6] 与 A 行相同）
@@          ⇒ 另一个组，**不得**淘汰任何 A 行（6 位索引注入时它会落进 A 组）
@@     r11：再访 A3 ⇒ 仍命中（若 A3 被 C1 挤掉就变成重填 ⇒ 判据红）
@@
@@ 观测量：块 magic 用 `__CHECK_RD`（不等即 `SYS_EXIT(点号)`）并记录结果缓冲；
@@ 事件（fill-done/hit/miss/victim/idx）与取指往返拍数（核的 `fetchresp
@@ latency=`）由宿主 `check_vasticache.py` 逐条比对 —— 命中不访存由「每条
@@ 命中行只有 1 次 fill-done」与「命中拍的 latency ≤ 4、缺失拍 ≥ 10」两路
@@ 独立证据给出（后者不读缓存自己的日志）。
@@
@@ 页表与代码块由 `+loadmem=` 按 `p_paddr` 装入 PA RAM；探针自身在核内 SRAM
@@（`addr[47:42] ≠ 0`，不经翻译、也不进 I-Cache —— 判据另核「SRAM 行 0 事件」）。

	.include "tests/inst/macros/inst_test.inc"
	.include "vasticache_tables.inc"

@@ 调一个被缓存（翻译后）的代码块：rb6 = 目标 VA、rb7 = 返回地址。
@@ 块尾 `jump [rb7, rd0, 0]` 回到探针（核内 SRAM，直连总线、不进缓存）。
.macro IC_CALL va, ret
	set.rb	rb6, \va
	set.rb	rb7, \ret
	jump	[rb6, rd0, 0]
\ret:
.endm

@@ 一个被缓存的代码块：**恰好 16 条指令 = 64 B = 一行**
@@   set.zw + or.w = 2 条（magic 的 wyde3 = 0xC0DE、wyde0 = 低 16 位）
@@   13 × swym = 13 条（无副作用空转，只占指令位）
@@   jump = 1 条（第 16 条，落在该行最后一拍 beat 7）
.macro IC_BLOCK name, magic
	.p2align 6
\name:
	set.zw	rd5, wp3, 0xC0DE
	or.w	rd5, wp0, ((\magic) & 0xFFFF)
	.rept	13
	swym	0
	.endr
	jump	[rb7, rd0, 0]
.endm

	__TEST_BEGIN

	@@ PTBR = 0（PA 0 的 L1 表），开 PTW
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6

	@@ ================= A 命中 / 缺失 =================
	IC_CALL	VA_A1, ret_a1
	__CHECK_RD 1, rd5, M_A1

	@@ ================= B 8 路同组 =================
	IC_CALL	VA_A2, ret_a2
	__CHECK_RD 2, rd5, M_A2
	IC_CALL	VA_A3, ret_a3
	__CHECK_RD 3, rd5, M_A3
	IC_CALL	VA_A4, ret_a4
	__CHECK_RD 4, rd5, M_A4
	IC_CALL	VA_A5, ret_a5
	__CHECK_RD 5, rd5, M_A5
	IC_CALL	VA_A6, ret_a6
	__CHECK_RD 6, rd5, M_A6
	IC_CALL	VA_A7, ret_a7
	__CHECK_RD 7, rd5, M_A7
	IC_CALL	VA_A8, ret_a8
	__CHECK_RD 8, rd5, M_A8
	@@ 同组第 9 行：按 LRU 淘汰 A1
	IC_CALL	VA_A9, ret_a9
	__CHECK_RD 9, rd5, M_A9
	@@ A1 已被淘汰：再访即重填（再淘汰 A2）
	IC_CALL	VA_A1, ret_a1b
	__CHECK_RD 10, rd5, M_A1

	@@ ================= C 组索引位宽 =================
	@@ 另一个组：不得淘汰任何 A 行
	IC_CALL	VA_C, ret_c
	__CHECK_RD 11, rd5, M_C
	@@ A3 仍应在（6 位索引时它会被 C1 挤掉 ⇒ 这里重填、判据红）
	IC_CALL	VA_A3, ret_a3b
	__CHECK_RD 12, rd5, M_A3

	__TEST_END
	__TEST_SECTIONS

	@@ ---- 被缓存的代码块（每个 64 B 一行；地址由 .lds 钉在生成器常量上）----
	.section .code_a1, "ax"
	IC_BLOCK A1, M_A1

	.section .code_a2, "ax"
	IC_BLOCK A2, M_A2

	.section .code_a3, "ax"
	IC_BLOCK A3, M_A3

	.section .code_a4, "ax"
	IC_BLOCK A4, M_A4

	.section .code_a5, "ax"
	IC_BLOCK A5, M_A5

	.section .code_a6, "ax"
	IC_BLOCK A6, M_A6

	.section .code_a7, "ax"
	IC_BLOCK A7, M_A7

	.section .code_a8, "ax"
	IC_BLOCK A8, M_A8

	.section .code_a9, "ax"
	IC_BLOCK A9, M_A9

	.section .code_c, "ax"
	IC_BLOCK C1, M_C

	@@ ---- 页表（PA 布局见生成器）----
	.section .pt_l1, "aw"
	.p2align 3
	.dd.o64	PTE_L1

	.section .pt_l2, "aw"
	.p2align 3
L2_TABLE:
	.dd.o64	PTE_L2_0
	.dd.o64	PTE_L2_1
	.dd.o64	PTE_L2_2
	.dd.o64	PTE_L2_3
	.dd.o64	PTE_L2_4
	.dd.o64	PTE_L2_5
	.dd.o64	PTE_L2_6
	.dd.o64	PTE_L2_7
	.dd.o64	PTE_L2_8
	.dd.o64	PTE_L2_9
	.dd.o64	PTE_L2_10
	.dd.o64	PTE_L2_11
	.dd.o64	PTE_L2_12
	.dd.o64	PTE_L2_13
	.dd.o64	PTE_L2_14
	.dd.o64	PTE_L2_15
L2_TABLE_END:
	.if	(L2_TABLE_END - L2_TABLE) != (L2_SIZE * 8)
	.error	"vasticache: L2 table entry count does not match L2_SIZE"
	.endif
