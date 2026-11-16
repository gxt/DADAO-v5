@@ atomic_rmw.S — 原子 RMW 的**合成序**（lr → 计算 → sc → 失败重试）载体；无 opcode 身份（`00-isa-design` 册）
@@ 大类：00-isa-design（指令系统设计）；`01`–`12` 各册保持「一个 opcode id 一个文件」，
@@   本文件不属任何单个 id，故落 00 册；在 `tests/inst.yaml` 以 `inst-00-isa-design-009`
@@   登记（载体↔索引双向断言），并在 `tools/testcases/{check_tests_index,validate_vectors}.py`
@@   的 `NON_ID_CARRIERS` 逐文件显式登记。
@@ 语义（期望一律独立推导自 `spec/SimRISC-12 §1`「LR-SC 指令」+ `contract-isa §14.2`，
@@   不从 qemu/llvm/gem5 反推）：
@@   * `lr` 从 [rbHD] 读到 rdHC 并置保留标记；`sc` 命中标记 ⇒ 写入 rdHC 且 rdHB=0（成功），
@@     未命中 ⇒ **不写**且 rdHB=1（失败）；成败都清本 hart 全部标记。
@@   * 清标记的事件只有三种：本 hart 另一条 `lr`、另一 hart 对**同一精确地址+相同宽度**的
@@     store、异常/中断进入。**同 hart 同址同宽的普通 `st` 不清标记**（故本文件用它改内存）。
@@   * 保留粒度 = 精确地址 + 访问宽度；`.o` 宽度 8 B、地址须 8 B 自然对齐。
@@ 合成序（C11 `__atomic_fetch_*` / LLVM 原子 lowering 的目标形态）：`lr` 拿到 old 后
@@   **在寄存器里算新值**再 `sc`；`sc` 返回非 0 ⇒ 必须**重读**（重新 `lr`）后重算重试。
@@   本文件把这条环的每一个可观测点写成显式断言（失败不写 / 成功才写 / 返回值 = old /
@@   重试必须重读）。
@@ 用例：encoding 0 / legality 0 / semantic 12 / boundary 1（链例 13 + 故障例 0）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；点号 1..13 连续
@@   （`run_asm_suite.scan_source` 断言）。逐个检查点把实测 8 字节写入结果缓冲并逐字节打印
@@   ⇒ 三方比较的是字节流（同一 ELF，chipyard/qemu/gem5）。
@@ 探针：初值一律经普通 `st.o` 给（不用 lr/sc 造初值）；"抢走保留标记"用本 hart 第二条
@@   `lr`（`spec/SimRISC-12 §1` 的第一条清标记事件）⇒ 单 hart 可构造、可重复。
@@ 数据块：`tests/inst/macros/inst_test.inc` 的 TEST_DATA 零区；每例独立 8 B 拍（0x500 起），
@@   例间不共享可写字节 ⇒ 用例可单独阅读、顺序无关。
@@ 链接布局：00 册无自有 `.lds` ⇒ 复用 `tests/inst/01-load-store/inst-tiny.lds`
@@   （`run_asm_suite` 的册内 `.lds` 优先、无则默认布局）。
@@ GAP（不可构造，不伪造、不写用例）：
@@   ① **多 hart 争用**：Tiny 单 hart，无法构造"另一 hart 对同址同宽 store 清标记"；
@@   ② **内存序强度**（`an`/`ar`/`nr` 的重排约束）：单 hart 顺序执行不可观测；
@@   ③ **`sc` 偶发失败**：spec 允许 spurious failure，但无"让它偶发失败"的可控手段；
@@   ④ **异常/中断进入清标记**：与 `m13-testcases-037` 同因（三平台实测分歧，不进正式向量）。
@@   以上与 `ISS-440`/`ISS-443` 同线（`tests/inst/MIGRATION.md §6`）。

	.include "tests/inst/macros/inst_test.inc"

@@ 数据区（TEST_DATA 零区；每例独立 8 B 拍）
	.equ A0, TEST_DATA + 0x500       @@ 1–3  fetch_add（含强制失败重试）
	.equ A1, TEST_DATA + 0x508       @@ 4    fetch_sub
	.equ A2, TEST_DATA + 0x510       @@ 5    fetch_and
	.equ A3, TEST_DATA + 0x518       @@ 6    fetch_or
	.equ A4, TEST_DATA + 0x520       @@ 7    fetch_xor
	.equ A5, TEST_DATA + 0x528       @@ 8    exchange
	.equ A6, TEST_DATA + 0x530       @@ 9    compare_exchange（相等 ⇒ sc）
	.equ A7, TEST_DATA + 0x538       @@ 10   compare_exchange（不等 ⇒ 不执行 sc）
	.equ A8, TEST_DATA + 0x540       @@ 11–12 重试必须重读
	.equ A9, TEST_DATA + 0x548       @@ 13   fetch_add 回绕边界
	.equ STL, TEST_DATA + 0x5F8      @@ "抢走保留标记"的落点（本 hart 第二条 lr 的目标）

	__TEST_BEGIN

	@@ ---- 1：fetch_add 的 lr 返回值 = old（内存初值 0x100） ----
	__LI	rd6, 0x0000000000000100
	LOAD_ADDR rb3, A0
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A0
	lr.o.nn	rd2, [rb3]                     @@ old = 0x100
	__CHECK_RD	1, rd2, 0x0000000000000100

	@@ ---- 2：保留被抢（本 hart 第二条 lr）⇒ sc 失败返回 1 且**不写**内存 ----
	__LI	rd6, 0x0000000000000008
	add.uo	{rd0, rd5}, rd2, rd6           @@ 候选新值 = old + 8 = 0x108
	LOAD_ADDR rb4, STL
	lr.o.nn	rd3, [rb4]                     @@ 清掉 A0 的保留标记（等价"被抢"）
	LOAD_ADDR rb3, A0
	sc.o.nn	rd7, rd5, [rb3]                @@ 未命中 ⇒ rd7 = 1，A0 不变
	__VERIFY_MEM	2, A0, 0, 0x0000000000000100
	__CHECK_RD	2, rd7, 0x0000000000000001

	@@ ---- 3：重试（重新 lr）⇒ sc 成功返回 0，A0 = old + 8 ----
	LOAD_ADDR rb3, A0
	lr.o.nn	rd2, [rb3]                     @@ 重读 old = 0x100
	__LI	rd6, 0x0000000000000008
	add.uo	{rd0, rd5}, rd2, rd6           @@ 0x108
	sc.o.nn	rd7, rd5, [rb3]                @@ 命中 ⇒ rd7 = 0
	__VERIFY_MEM	3, A0, 0, 0x0000000000000108
	__VERIFY_RD	3, rd2, 0x0000000000000100
	__CHECK_RD	3, rd7, 0x0000000000000000

	@@ ---- 4：fetch_sub ⇒ 返回 old(0x200)、内存 = old - 0x30 = 0x1D0 ----
	__LI	rd6, 0x0000000000000200
	LOAD_ADDR rb3, A1
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A1
	lr.o.nn	rd2, [rb3]
	__LI	rd6, 0x0000000000000030
	sub.uo	{rd0, rd5}, rd2, rd6           @@ 0x1D0（借位丢弃；fetch_sub 为模 2^64 减）
	sc.o.nn	rd7, rd5, [rb3]
	__VERIFY_MEM	4, A1, 0, 0x00000000000001D0
	__VERIFY_RD	4, rd2, 0x0000000000000200
	__CHECK_RD	4, rd7, 0x0000000000000000

	@@ ---- 5：fetch_and ⇒ 内存 = old & val，返回 old ----
	__LI	rd6, 0xF0F0F0F0F0F0F0F0
	LOAD_ADDR rb3, A2
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A2
	lr.o.nn	rd2, [rb3]
	__LI	rd6, 0x0FF00FF00FF00FF0
	and.o	rd5, rd2, rd6                  @@ 0x00F000F000F000F0
	sc.o.nn	rd7, rd5, [rb3]
	__VERIFY_MEM	5, A2, 0, 0x00F000F000F000F0
	__VERIFY_RD	5, rd2, 0xF0F0F0F0F0F0F0F0
	__CHECK_RD	5, rd7, 0x0000000000000000

	@@ ---- 6：fetch_or ⇒ 内存 = old | val，返回 old ----
	__LI	rd6, 0x0123456789ABCDEF
	LOAD_ADDR rb3, A3
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A3
	lr.o.nn	rd2, [rb3]
	__LI	rd6, 0xF00000000000000F
	or.o	rd5, rd2, rd6                  @@ 0xF123456789ABCDEF
	sc.o.nn	rd7, rd5, [rb3]
	__VERIFY_MEM	6, A3, 0, 0xF123456789ABCDEF
	__VERIFY_RD	6, rd2, 0x0123456789ABCDEF
	__CHECK_RD	6, rd7, 0x0000000000000000

	@@ ---- 7：fetch_xor ⇒ 内存 = old ^ val，返回 old ----
	__LI	rd6, 0xFFFFFFFFFFFFFFFF
	LOAD_ADDR rb3, A4
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A4
	lr.o.nn	rd2, [rb3]
	__LI	rd6, 0x0F0F0F0F0F0F0F0F
	xor.o	rd5, rd2, rd6                  @@ 0xF0F0F0F0F0F0F0F0
	sc.o.nn	rd7, rd5, [rb3]
	__VERIFY_MEM	7, A4, 0, 0xF0F0F0F0F0F0F0F0
	__VERIFY_RD	7, rd2, 0xFFFFFFFFFFFFFFFF
	__CHECK_RD	7, rd7, 0x0000000000000000

	@@ ---- 8：exchange ⇒ 内存 = 新值，返回 old（新值 ≠ old，两值可区分） ----
	__LI	rd6, 0x1111111111111111
	LOAD_ADDR rb3, A5
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A5
	lr.o.nn	rd2, [rb3]                     @@ old = 0x1111…
	__LI	rd5, 0xDEADBEEFCAFEF00D
	sc.o.nn	rd7, rd5, [rb3]
	__VERIFY_MEM	8, A5, 0, 0xDEADBEEFCAFEF00D
	__VERIFY_RD	8, rd2, 0x1111111111111111
	__CHECK_RD	8, rd7, 0x0000000000000000

	@@ ---- 9：compare_exchange ①比较相等 ⇒ 执行 sc，内存 = 期望新值 ----
	__LI	rd6, 0x0000000000000100
	LOAD_ADDR rb3, A6
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A6
	lr.o.nn	rd2, [rb3]                     @@ old = 0x100
	__LI	rd6, 0x0000000000000100        @@ 比较期望 = 0x100（= old）
	__LI	rd9, 0x0000000000000000
	cmp.uo	rd8, rd2, rd6                  @@ 相等 ⇒ rd8 = 0
	br.ne	{rd8, rd9}?, [rb0, __ce_skip9]   @@ 不等才跳过 sc
	__LI	rd5, 0x0000000000000888
	sc.o.nn	rd7, rd5, [rb3]
__ce_skip9:
	__VERIFY_MEM	9, A6, 0, 0x0000000000000888
	__VERIFY_RD	9, rd2, 0x0000000000000100
	__CHECK_RD	9, rd7, 0x0000000000000000

	@@ ---- 10：compare_exchange ②比较不等 ⇒ **不执行 sc**（内存不变、结果寄存器不动） ----
	__LI	rd6, 0x0000000000000200
	LOAD_ADDR rb3, A7
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A7
	lr.o.nn	rd2, [rb3]                     @@ old = 0x200
	__LI	rd7, 0x00000000000000FF        @@ 哨兵：sc 命中会把它覆写成 0
	__LI	rd6, 0x0000000000000100        @@ 比较期望 = 0x100（≠ old）
	__LI	rd9, 0x0000000000000000
	cmp.uo	rd8, rd2, rd6                  @@ 不等 ⇒ rd8 = -1
	br.ne	{rd8, rd9}?, [rb0, __ce_skip10]
	__LI	rd5, 0x0000000000000888
	sc.o.nn	rd7, rd5, [rb3]                @@ 本行不得执行
__ce_skip10:
	__VERIFY_MEM	10, A7, 0, 0x0000000000000200
	__VERIFY_RD	10, rd7, 0x00000000000000FF   @@ sc 未执行（结果寄存器未被写）
	__CHECK_RD	10, rd2, 0x0000000000000200

	@@ ---- 11：重试环的失败点 —— sc 失败返回 1、不写；陈旧候选本身是 0x108 ----
	__LI	rd6, 0x0000000000000100
	LOAD_ADDR rb3, A8
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A8
	lr.o.nn	rd2, [rb3]                     @@ old1 = 0x100
	rd2rd	{rd10:rd10}, {rd2:rd2}         @@ 留一份 old1（后面算"陈旧候选"）
	__LI	rd6, 0x0000000000000008
	add.uo	{rd0, rd5}, rd10, rd6          @@ 陈旧候选 = 0x108
	LOAD_ADDR rb4, STL
	lr.o.nn	rd3, [rb4]                     @@ 抢 ⇒ 清标记
	LOAD_ADDR rb3, A8
	sc.o.nn	rd7, rd5, [rb3]                @@ 失败 ⇒ rd7 = 1
	__VERIFY_MEM	11, A8, 0, 0x0000000000000100
	__VERIFY_RD	11, rd5, 0x0000000000000108
	__CHECK_RD	11, rd7, 0x0000000000000001

	@@ ---- 12：失败后改内存（普通 st，已在清除之后）⇒ 重试**必须重读**，否则算错 ----
	__LI	rd6, 0x0000000000000040
	LOAD_ADDR rb3, A8
	st.o	rd6, [rb3, 0]                  @@ 同 hart 同址同宽 st **不清**标记（此时本就无标记）
	LOAD_ADDR rb3, A8
	lr.o.nn	rd2, [rb3]                     @@ 重读 ⇒ 0x40（不是陈旧的 0x100）
	__LI	rd6, 0x0000000000000008
	add.uo	{rd0, rd5}, rd2, rd6           @@ 0x48（用重读值算）
	sc.o.nn	rd7, rd5, [rb3]
	__VERIFY_MEM	12, A8, 0, 0x0000000000000048
	__VERIFY_RD	12, rd2, 0x0000000000000040   @@ 读到的是新值
	__CHECK_RD	12, rd7, 0x0000000000000000

	@@ ---- 13：boundary —— fetch_add 回绕（全 1 + 1 ⇒ 低 64 位 0，进位丢弃）----
	__LI	rd6, 0xFFFFFFFFFFFFFFFF
	LOAD_ADDR rb3, A9
	st.o	rd6, [rb3, 0]
	LOAD_ADDR rb3, A9
	lr.o.nn	rd2, [rb3]
	__LI	rd6, 0x0000000000000001
	add.uo	{rd0, rd5}, rd2, rd6           @@ 0x0
	sc.o.nn	rd7, rd5, [rb3]
	__VERIFY_MEM	13, A9, 0, 0x0000000000000000
	__VERIFY_RD	13, rd2, 0xFFFFFFFFFFFFFFFF
	__CHECK_RD	13, rd7, 0x0000000000000000

	__TEST_END

	__TEST_SECTIONS
