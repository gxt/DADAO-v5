@@ cfx5_maint.S — `cfx_cache`（cfx5）**维护命令** RTL 探针（`m16-chipyard-017`）
@@
@@ 目的：在 `WumingVastConfig` 上覆盖 `contract-cache` §3–§5 的命令语义：
@@ 操作（clean/invalidate/flush）、范围（all/PA 单行/PA 区间）、选择（I/D）、
@@ 使能位为 0 时的 no-op、不可缓存/无行 PA 的无效果、以及非法编码 ⇒ CFXREG。
@@
@@ 几何/页表/控制字/magic/间接期望全部由 `gen_cfx5_maint_tables.py` 现场给出
@@ （`.equ` 形式的 include），本文件不写位号、不手算 PT。
@@
@@ 观测通道（两条，互相独立）：
@@   * **取指端口**（D 侧写回/丢弃的真值）：把代码行经 D 路径改掉，再用
@@     `I|invalidate` 丢掉 I 行后跳过去 —— 取指只能从内存重填，执行到的立即数
@@     就是内存内容（D 侧 invalidate 未写回 ⇒ 旧值；clean/flush 已写回 ⇒ 新值）。
@@     这与 `m16-chipyard-009` 的「写回时机以取指端口为独立观测量」同法；
@@   * **缓存日志**（`WumingCache[dcache]` / `[icache]`）：miss/fill-done/cmd
@@     事件由判据脚本逐条比对（flush 后必须重新缺失、invalidate 不得出现 wb）。
@@
@@ 记录顺序 = `gen_cfx5_maint_tables.expected_records()`；`__CHECK_RD` 的失败点号
@@ 只用于镜像级兜底（`SYS_EXIT(点号)`），语义判据在宿主 checker。
@@
@@ 只在 `WumingVastConfig` 上跑：Tiny 不实现 cfx5（CACHE-28）。
@@
@@ 用法：
@@   python3 gen_cfx5_maint_tables.py > <out>/cfx5_maint_tables.inc
@@   llvm-mc --triple=dadao-unknown-elf -filetype=obj -I <repo> -I <out> \
@@       cfx5_maint.S -o cfx5_maint.o
@@   ld.lld -T cfx5_maint.lds cfx5_maint.o -o cfx5_maint.elf

	.include "tests/inst/macros/inst_test.inc"
	.include "cfx5_maint_tables.inc"

	__TEST_BEGIN
	set.rb	rb20, HMON_BASE
	set.rb	rb21, abort
	st.o	rb21, [rb20, 0xF8]		@@ 未预期异常 ⇒ 显式失败（不是死循环）

	@@ PTBR = 0（L1 在 PA 0），开 PTW
	set.rd	rd6, 0
	cfx2rc	cfx_ptw, cg9, rc0, rd6
	set.rd	rd6, 1
	cfx2rc	cfx_ptw, cg8, rc8, rd6

	set.rb	rb8, VA_CODE
	set.rb	rb9, VA_R0
	set.rb	rb10, VA_R1
	set.rb	rb11, VA_D

	@@ ================= A. I 侧：单行 / 区间 =================
	@@ 热身：内存里的代码行（`+loadmem` 装入）执行旧立即数
	set.rb	rb5, a0
	jump	[rb8, rd0, 0]
a0:
	or.o	rd5, rd20, rd0
	__CHECK_RD 1, rd5, IMM0

	@@ 经 D 改成立即数 IMM1，并 D|clean|单行 写回；I|clean|单行 必须 no-op
	set.zw	rd13, wp0, IMM1
	st.w	rd13, [rb8, 2]
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_CLEAN_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_CLEAN_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, a1
	jump	[rb8, rd0, 0]
a1:
	or.o	rd5, rd20, rd0
	__CHECK_RD 2, rd5, IMM0		@@ I 行未失效 ⇒ 仍是旧指令

	@@ I|invalidate|单行 ⇒ 取指重填，执行 IMM1
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, a2
	jump	[rb8, rd0, 0]
a2:
	or.o	rd5, rd20, rd0
	__CHECK_RD 3, rd5, IMM1

	@@ 改 IMM2，D|clean|PA 区间 + I|invalidate|PA 区间（区间 = 这一行）
	set.zw	rd13, wp0, IMM2
	st.w	rd13, [rb8, 2]
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_CLEAN_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, a3
	jump	[rb8, rd0, 0]
a3:
	or.o	rd5, rd20, rd0
	__CHECK_RD 4, rd5, IMM2

	@@ I|flush 等价 invalidate：改 IMM3，D|clean，I|flush|单行
	set.zw	rd13, wp0, IMM3
	st.w	rd13, [rb8, 2]
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_CLEAN_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_FLUSH_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, a4
	jump	[rb8, rd0, 0]
a4:
	or.o	rd5, rd20, rd0
	__CHECK_RD 5, rd5, IMM3

	@@ ================= B. D 侧：单行（取指端口为真值） =================
	@@ 现在内存/I 行都是 IMM3。经 D 改 IMM4（脏行），
	@@ D|invalidate|单行 丢弃脏行 ⇒ 内存仍 IMM3；I|invalidate 后取指 ⇒ IMM3
	set.zw	rd13, wp0, IMM4
	st.w	rd13, [rb8, 2]
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, b0
	jump	[rb8, rd0, 0]
b0:
	or.o	rd5, rd20, rd0
	__CHECK_RD 6, rd5, IMM3

	@@ D|clean|单行：改 IMM5（脏行），clean 写回 ⇒ 取指执行 IMM5
	set.zw	rd13, wp0, IMM5
	st.w	rd13, [rb8, 2]
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_CLEAN_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, b1
	jump	[rb8, rd0, 0]
b1:
	or.o	rd5, rd20, rd0
	__CHECK_RD 7, rd5, IMM5

	@@ D|flush|单行：改 IMM6（脏行），flush 写回并删除 ⇒ 取指执行 IMM6；
	@@ 随后经 D 读该行必须缺失重填（行已删）
	set.zw	rd13, wp0, IMM6
	st.w	rd13, [rb8, 2]
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_FLUSH_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, b2
	jump	[rb8, rd0, 0]
b2:
	or.o	rd5, rd20, rd0
	__CHECK_RD 8, rd5, IMM6
	ld.o	rd5, [rb8, 0]
	__CHECK_RD 9, rd5, CAT_IMM6_WORD

	@@ ================= C. D 侧：PA 区间（相邻两行） =================
	@@ 初值 M_R0/M_R1 由 `+loadmem` 装入；写新值成脏行后 D|invalidate|区间
	set.rb	rb4, N_R0
	st.o	rb4, [rb9, 0]
	set.rb	rb4, N_R1
	st.o	rb4, [rb10, 0]
	set.rd	rd7, PA_R0
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 128
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	ld.o	rd5, [rb9, 0]
	__CHECK_RD 10, rd5, M_R0
	ld.o	rd5, [rb10, 0]
	__CHECK_RD 11, rd5, M_R1

	@@ D|clean|区间：写新值成脏行，clean 写回 ⇒ 再 invalidate 单行后读回新值
	set.rb	rb4, N_R0
	st.o	rb4, [rb9, 0]
	set.rb	rb4, N_R1
	st.o	rb4, [rb10, 0]
	set.rd	rd7, PA_R0
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 128
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_CLEAN_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rd	rd7, PA_R0
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rd	rd7, PA_R1
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	ld.o	rd5, [rb9, 0]
	__CHECK_RD 12, rd5, N_R0
	ld.o	rd5, [rb10, 0]
	__CHECK_RD 13, rd5, N_R1

	@@ D|flush|区间：写新值成脏行，flush 写回并删除 ⇒ 读回新值（缺失重填）
	set.rb	rb4, P_R0
	st.o	rb4, [rb9, 0]
	set.rb	rb4, P_R1
	st.o	rb4, [rb10, 0]
	set.rd	rd7, PA_R0
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 128
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_FLUSH_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	ld.o	rd5, [rb9, 0]
	__CHECK_RD 14, rd5, P_R0
	ld.o	rd5, [rb10, 0]
	__CHECK_RD 15, rd5, P_R1

	@@ ================= D. D 侧：all =================
	@@ invalidate|all：写新值成脏行，整侧失效 ⇒ 读回旧值（缺失重填）
	set.rb	rb4, N_D
	st.o	rb4, [rb11, 0]
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_ALL
	cfx2rc	cfx_cache, cg8, rc9, rd7
	ld.o	rd5, [rb11, 0]
	__CHECK_RD 16, rd5, M_D

	@@ clean|all：写新值成脏行，整侧写回 ⇒ 再单行 invalidate 后读回新值
	set.rb	rb4, N_D
	st.o	rb4, [rb11, 0]
	set.zw	rd7, wp0, CTRL_D_CLEAN_ALL
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rd	rd7, PA_D
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	ld.o	rd5, [rb11, 0]
	__CHECK_RD 17, rd5, N_D

	@@ flush|all：写新值成脏行，整侧写回并失效 ⇒ 读回新值（缺失重填）
	set.rb	rb4, P_D
	st.o	rb4, [rb11, 0]
	set.zw	rd7, wp0, CTRL_D_FLUSH_ALL
	cfx2rc	cfx_cache, cg8, rc9, rd7
	ld.o	rd5, [rb11, 0]
	__CHECK_RD 18, rd5, P_D

	@@ ================= E. 使能位 = 0 ⇒ 该侧不维护 =================
	@@ 代码行当前内存/I 都是 IMM6。经 D 改 IMM7（脏行），关 D，
	@@ D|invalidate|单行 必须是 no-op；重开 D 后 clean 仍能看到这条脏行
	@@ ⇒ 取指执行 IMM7（若 invalidate 误生效，clean 无行可写、内存仍 IMM6）。
	set.zw	rd13, wp0, IMM7
	st.w	rd13, [rb8, 2]
	set.rd	rd7, 0
	cfx2rc	cfx_cache, cg8, rc8, rd7		@@ cache_enable = 0
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rd	rd7, 3
	cfx2rc	cfx_cache, cg8, rc8, rd7		@@ 重新使能
	set.zw	rd7, wp0, CTRL_D_CLEAN_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, e0
	jump	[rb8, rd0, 0]
e0:
	or.o	rd5, rd20, rd0
	__CHECK_RD 19, rd5, IMM7

	@@ ================= F. 无行 / 不可缓存 PA：无效果、不报异常 =================
	set.rd	rd7, 0x00FFFFFF010100		@@ 核内 SRAM 地址（PA RAM 无此行）
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_D_CLEAN_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_FLUSH_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rd	rd5, W_MMIO
	__REC	rd5

	@@ ---- F2. cache_addr_start 的 56 位（CACHE-18 / ISS-534） ----
	@@ PA_HIGH 的 [47:0] == PA_D：若维护端口按 48 位截断，下面的单行 invalidate
	@@ 会错误命中 A_D 并丢掉脏行；正确实现按 56 位比较 ⇒ 无行、A_D 保留。
	set.rb	rb4, N_D
	st.o	rb4, [rb11, 0]			@@ A_D 成脏行（内存里是 P_D）
	set.rd	rd7, PA_HIGH
	cfx2rc	cfx_cache, cg8, rc10, rd7
	cfx2rd	cfx_cache, cg8, rc10, rd5
	__REC	rd5				@@ 读回 = PA_HIGH（寄存器不截断）
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	ld.o	rd5, [rb11, 0]
	__REC	rd5				@@ 仍是脏行 N_D（未被别名删掉）

	@@ ================= G. 无条件 no-op（不检查范围/操作数） =================
	@@ 选侧 = 00、操作 = flush、范围 = reserved：no-op
	set.rd	rd7, 0
	cfx2rc	cfx_cache, cg8, rc11, rd7		@@ addr_size = 0
	set.zw	rd7, wp0, CTRL_NOSEL_FLUSH_RESV
	cfx2rc	cfx_cache, cg8, rc9, rd7
	@@ 选侧 = ID、操作 = none、范围 = PA 区间、size = 0：no-op
	set.zw	rd7, wp0, CTRL_ID_NONE_RANGE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rd	rd5, W_NONE_SEL
	__REC	rd5

	@@ ================= H. 非法编码 ⇒ CFXREG，且不得执行任何维护 =================
	@@ f1: 脏行（IMM8）+ 非法 clean（选侧 ID、范围 reserved）⇒ CFXREG；
	@@     I|invalidate 后取指必须执行内存里的 IMM7（非法命令没有 clean）
	set.zw	rd13, wp0, IMM8
	st.w	rd13, [rb8, 2]
	set.rb	rb5, f1_resume
	st.o	rb5, [rb20, 0xF8]
	set.zw	rd7, wp0, CTRL_ID_CLEAN_RESV
	.globl	f1_fault
f1_fault:
	cfx2rc	cfx_cache, cg8, rc9, rd7
	.dd.t32	0
	.globl	f1_resume
f1_resume:
	set.rb	rb20, HMON_BASE
	set.rb	rb8, VA_CODE
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5				@@ cause_id
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5				@@ cause_info = 指令编码
f1_resume2:
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, f1_end
	jump	[rb8, rd0, 0]
f1_end:
	or.o	rd5, rd20, rd0
	__CHECK_RD 20, rd5, IMM7

	@@ f2: PA 区间 + addr_size = 0 ⇒ CFXREG；该非法 invalidate 不得丢掉
	@@     上面留下的脏行（IMM8）——D|clean 后取指必须执行 IMM8
	set.rd	rd7, 0
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.rb	rb5, f2_resume
	st.o	rb5, [rb20, 0xF8]
	set.zw	rd7, wp0, CTRL_D_INVALIDATE_RANGE
	.globl	f2_fault
f2_fault:
	cfx2rc	cfx_cache, cg8, rc9, rd7
	.dd.t32	0
	.globl	f2_resume
f2_resume:
	set.rb	rb20, HMON_BASE
	set.rb	rb8, VA_CODE
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5
f2_resume2:
	set.rd	rd7, PA_CODE
	cfx2rc	cfx_cache, cg8, rc10, rd7
	set.rd	rd7, 64
	cfx2rc	cfx_cache, cg8, rc11, rd7
	set.zw	rd7, wp0, CTRL_D_CLEAN_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.zw	rd7, wp0, CTRL_I_INVALIDATE_LINE
	cfx2rc	cfx_cache, cg8, rc9, rd7
	set.rb	rb5, f2_end
	jump	[rb8, rd0, 0]
f2_end:
	or.o	rd5, rd20, rd0
	__CHECK_RD 21, rd5, IMM8

	@@ f3: D 使能位 = 0 时非法编码仍校验（CACHE-08）
	set.rd	rd7, 0
	cfx2rc	cfx_cache, cg8, rc8, rd7		@@ 关 I/D
	set.rb	rb5, f3_resume
	st.o	rb5, [rb20, 0xF8]
	set.zw	rd7, wp0, CTRL_D_CLEAN_RESV
	.globl	f3_fault
f3_fault:
	cfx2rc	cfx_cache, cg8, rc9, rd7
	.dd.t32	0
	.globl	f3_resume
f3_resume:
	set.rb	rb20, HMON_BASE
	set.rb	rb8, VA_CODE
	ld.o	rd5, [rb20, 0xE0]
	__REC	rd5
	ld.o	rd5, [rb20, 0xF0]
	__REC	rd5
f3_resume2:
	set.rd	rd7, 3
	cfx2rc	cfx_cache, cg8, rc8, rd7
	__TEST_END

	@@ 未预期异常（含 cfx5 整体缺失）落点：显式失败，不是死循环
abort:
	__EXIT 126

	@@ PA 段内容：页表 / 数据初值 / 代码行（`+loadmem` 按 p_paddr 装入）
	.section .pt_l1, "aw"
	.dd.o64	PTE_L1
	.section .pt_l2, "aw"
	.dd.o64	0			@@ L2[0]
	.dd.o64	0			@@ L2[1]
	.dd.o64	0			@@ L2[2]
	.dd.o64	0			@@ L2[3]
	.dd.o64	PTE_DATA		@@ L2[4]：page 4（R0/R1/D）
	.dd.o64	0			@@ L2[5]
	.dd.o64	0			@@ L2[6]
	.dd.o64	0			@@ L2[7]
	.dd.o64	PTE_CODE		@@ L2[8]：page 8（代码行）
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.dd.o64	0
	.section .l_r0, "aw"
	.dd.o64	M_R0
	.section .l_r1, "aw"
	.dd.o64	M_R1
	.section .l_d, "aw"
	.dd.o64	M_D
	.section .l_code, "aw"
	.dd.t32	STUB_OLD			@@ 4 B instruction word
	.dd.t32	STUB_JUMP			@@ 4 B jump right after it

	__TEST_SECTIONS
