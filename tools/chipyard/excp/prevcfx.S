@@ prevcfx.S — `escape` 恢复 `inner_cfx_code <- excp_prev_cfx_code`（`cg5 rc1`）探针
@@
@@ 目的（`m16-chipyard-005`）：用**可失败**的访客侧断言覆盖 `DADAO-12 §3.6/§5.2/§5.3`
@@ 的新语义，且不依赖 `hmon` SRAM 的上电内容（`tests/inst/11-cfx/escape_ciii_cfx.S`
@@ 链例 12 用 `hmon` SRAM `+0xC8` 当到达计数，本 profile 的 TLRAM 上电不为 0 ⇒ 该链例
@@ 在 chipyard 上结构性不可跑；本载体把计数槽**显式清零**，见任务书「遗留问题」）。
@@
@@ 断言（全部是访客侧可观测的架构值，逐 8 字节写入结果缓冲后 `SYS_WRITEC` 打印）：
@@  1 `cg5 rc1` 的 boot 保存值 = `cfx_power`(0x3F)：power 以 `trap cfx_hmon` 移交，
@@    `§5.2` 第 5 步把当时的 `inner_cfx_code`(=63) 写进 hmon 帧；
@@  2 `cg5 rc1` 可写：写 0x25 读回 0x25（`§3.6` RW）；
@@  3 写回 0x3F（后续 trap 会重新写入，此处只为把帧复原，读回 0x3F）；
@@  4 hmon 帧内 `escape cfx_hmon` 回到应用（落点计数第 1→第 2 次的路径在 5/6 之后）；
@@  5 应用（`inner_cfx_code`=63）再 `escape cfx_hmon` ⇒ **CFXESC**（`§5.3` 步骤 0：
@@    `cfxha(3) != inner_cfx_code(63)`），且该异常**交给当前 cfx = cfx_power**
@@    （自建 power 入口记录 `cause_id = 1<<3`）；
@@  6 该 CFXESC 的 `cause_ip` = 被拦下的 `escape` 指令地址（运行期 `aip.si` 派生）；
@@  7 落点到达次数 = 2（handler 的 escape 一次 + catcher 的 escape 一次）；
@@    ——旧语义（escape 不恢复 cfx）下第 5 步的 escape 会**成功**，落点被第 3 次到达，
@@    在打印缓冲之前判红（`__EXIT 4`），因此该探针有可达 FAIL 路径。
@@
@@ 用法（三平台同一 ELF；判据见 `check_prevcfx.py` 与证据脚本）：
@@   llvm-mc --triple=dadao-unknown-elf -filetype=obj prevcfx.S -o prevcfx.o
@@   ld.lld -T prevcfx.lds prevcfx.o -o prevcfx.elf

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	LOAD_ADDR rb20, HMON_BASE		@@ 固件 hmon 的槽（+0xE0/0xE8/0xF0/0xF8）
	LOAD_ADDR rb22, HMON_BASE		@@ 本探针自己的槽（+0xB0/0xB8/0xC0/0xC8）
	set.rd	rd11, HMON_BASE			@@ hmon 向量初值（`spec/DADAO-13 §1`）
	st.o	rd0, [rb22, 0xC8]		@@ 到达计数**显式清零**（不依赖 SRAM 上电值；rd0 恒 0）
	st.o	rd0, [rb22, 0xC0]		@@ handler 记录的 cause_id 槽
	st.o	rd0, [rb22, 0xB8]		@@ catcher 记录的 cause_id 槽
	st.o	rd0, [rb22, 0xB0]		@@ catcher 记录的 cause_ip 槽
	LOAD_ADDR rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]		@@ 固件 hmon 的返回槽（意外异常 ⇒ 红）

	@@ ---- 1–3：`cg5 rc1` 的 boot 保存值与 RW ----
	cfx2rd	cfx_hmon, cg5, rc1, rd5
	__CHECK_RD	1, rd5, 0x3F

	set.rd	rd6, 0x25
	cfx2rc	cfx_hmon, cg5, rc1, rd6
	cfx2rd	cfx_hmon, cg5, rc1, rd5
	__CHECK_RD	2, rd5, 0x25

	set.rd	rd6, 0x3F
	cfx2rc	cfx_hmon, cg5, rc1, rd6
	cfx2rd	cfx_hmon, cg5, rc1, rd5
	__CHECK_RD	3, rd5, 0x3F

	@@ ---- 4–7：装自建 hmon 入口 → trap → handler escape 回应用 ----
	set.rd	rd12, (ENTRY + 0x1B00)
	cfx2rc	cfx_hmon, cg3, rc10, rd12
	set.rd	rd13, (ENTRY + 0x1E00)
	trap	cfx_hmon, 0x30001
	__EXIT	5				@@ 不返回 ⇒ 红

__end:
	cfx2rc	cfx_hmon, cg3, rc10, rd11	@@ 还原 hmon 向量 = hmon SRAM 起始
	set.rd	rd12, BOOTROM_BASE		@@ 还原 power 向量 = BootROM 起始
	cfx2rc	cfx_power, cg3, rc10, rd12
	__TEST_END

	@@ ---- 自建 hmon 入口（trap 的目标；进入时 `inner_cfx_code = 3`）----
	.org	0x1B00
__hmon:
	cfx2rd	cfx_hmon, cg5, rc2, rd63	@@ 进入时的 cause_id（应为 CFXTRAP = 1）
	st.o	rd63, [rb22, 0xC0]
	cfx2rc	cfx_hmon, cg5, rc3, rd13	@@ 返回地址 = 应用给的落点
	escape	cfx_hmon, [excp_cause_ip, 0]

	@@ ---- 自建 cfx_power 入口（CFXESC 交给「当前 cfx」；`§5.3` 步骤 0）----
	.org	0x1C40
__power:
	cfx2rd	cfx_power, cg5, rc2, rd63
	st.o	rd63, [rb22, 0xB8]
	cfx2rd	cfx_power, cg5, rc3, rd63
	st.o	rd63, [rb22, 0xB0]
	cfx2rc	cfx_power, cg5, rc3, rd13
	escape	cfx_power, [excp_cause_ip, 0]

	@@ ---- 落点：第 1 次 = hmon 帧的 escape；第 2 次 = CFXESC 交给 power 后的回程 ----
	.org	0x1E00
__lp_pad:
	ld.o	rd8, [rb22, 0xC8]
	add.si	rd8, 1
	st.o	rd8, [rb22, 0xC8]
	ld.o	rd7, [rb22, 0xB8]		@@ catcher 记录的 cause_id（未调用 = 0）
	set.rd	rd9, 2
	cmp.uo	rd9, rd8, rd9
	br.p	{rd9}?, [rb0, __fail]		@@ 到达 > 2 次 ⇒ 旧语义 ⇒ 红
	br.z	{rd7}?, [rb0, __first]
	@@ 第 2 次到达：CFXESC 已由 power 入口记录
	__CHECK_RD	4, rd8, 2
	__CHECK_RD	5, rd7, 0x8
	ld.o	rd5, [rb22, 0xB0]		@@ catcher 记下的 cause_ip
	rb2rd	{rd6:rd6}, {rb25:rb25}		@@ 被拦下的 escape 地址（aip 派生）
	__VERIFY_EQ_RD	6, rd5, rd6
	jump	[rb0, __end]
__first:
	ld.o	rd5, [rb22, 0xC0]		@@ hmon 入口记下的 cause_id
	__CHECK_RD	7, rd5, 0x1		@@ 确为 CFXTRAP 帧的 escape
	set.rd	rd12, (ENTRY + 0x1C40)	@@ 装 power 入口
	cfx2rc	cfx_power, cg3, rc10, rd12
	set.rd	rd13, (ENTRY + 0x1E00)
	.globl	pad_aip
pad_aip:
	aip.si	rb25, 0				@@ rb25 = 本指令地址（pad_aip）
	add.si	rb25, 8				@@ +8 = 下面 escape 的地址（`prevcfx.lds` ASSERT）
	.globl	prevcfx_escape
prevcfx_escape:
	escape	cfx_hmon, [excp_cause_ip, 0]	@@ 当前 cfx = 63 ⇒ 必判 CFXESC
	__EXIT	4
__fail:
	__EXIT	7

	__TEST_SECTIONS
