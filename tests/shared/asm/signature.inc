@@ tests/shared/asm/signature.inc — 签名流（signature）机制（m16-testcases-002）
@@
@@ 用途：把测试的**观测点实际值**写成一段固定宽度（8 字节/槽）的大端字节流，收尾时
@@ 整段输出给 host；host 侧用 `tools/testcases/lib/signature.py` 解析、按槽比对。
@@ 被 `tests/inst/macros/inst_test.inc`（`__REC` / 收尾打印）复用；判据 = 「被 ≥2 个
@@ scope 复用」⇒ 放 `tests/shared/asm/`（`docs/Process-09 §3/§6`）。
@@
@@ 布局与常量（host 侧同一口径，见 `signature.py` 的 `SLOT`/`UNWRITTEN`/`ARG_TAIL`）：
@@   * 槽宽 `SIG_SLOT` = 8 字节，大端；
@@   * 未写哨兵 `SIG_UNWRITTEN` = `0xdeadbeef`（`SIG_BEGIN` 预填；漏跑的槽在 host 侧
@@     报「槽 N 未写」，不静默当 0）；
@@   * 写指针 = **rb30**（`inst_test.inc` §保留寄存器约定；用例不得占用）；
@@   * `SIG_DUMP` 的参数块放在签名区**尾部** `buf + SIG_ARG_TAIL`（`0x7F8`；签名区容量
@@     `0x800`、槽数 ≤127 ⇒ 与槽数据不重叠）。
@@
@@ 依赖：`set.rb`（汇编器伪指令，无需 include）；semihosting 常量
@@ `SEMIHOST_TAG`/`SYS_WRITEC`/`SYS_WRITE` 可由调用方先 `.equ`（本文件只在未定义时补
@@ 默认值，值取 `contract-semihosting §1/§3`）。
@@
@@ 收尾输出两条路（`SIG_DUMP` 优先块写、失败回退）：
@@   1. `SYS_WRITE`（handle 1）一次块写整段——参数块 `{1, buf, 8*n}`；
@@   2. 返回 `rd8`（未写字节数）非 0 ⇒ `SYS_WRITEC` 逐字节回退（既有镜像行为不变）。
@@      **句柄语义**：handle 1 只在宿主先 `SYS_OPEN(":tt", w)` 后有效；QEMU/gem5 未打开
@@      时返回「未写」⇒ 自动回退，host 收到的字节流与块写一致。
@@      `SIG_DUMP_CHARS` 直接走逐字节路径（`tests/inst` 用它保持指令流/周期基线不变）。

	.equ	SIG_SLOT,      8
	.equ	SIG_UNWRITTEN, 0xdeadbeef
	.equ	SIG_ARG_TAIL,  0x7F8

	.ifndef	SEMIHOST_TAG
	.equ	SEMIHOST_TAG, 0x3FF00
	.endif
	.ifndef	SYS_WRITEC
	.equ	SYS_WRITEC,   0x03
	.endif
	.ifndef	SYS_WRITE
	.equ	SYS_WRITE,    0x05
	.endif

@@ 签名区初始化：`count` 个槽预填 `SIG_UNWRITTEN`，并把 rb30 指到区首。
@@   `buf` = 签名区首地址（8 字节对齐；`inst_test.inc` 用 TEST_BUF）。
.macro SIG_BEGIN buf, count
	set.rb rb30, \buf
	set.rd	rd20, SIG_UNWRITTEN
	.set	__sig_off, 0
	.rept	\count
	st.o	rd20, [rb30, __sig_off]
	.set	__sig_off, __sig_off + SIG_SLOT
	.endr
.endm

@@ 追加一个观测点：把 `reg` 的 8 字节写进当前槽，写指针前进一格。
@@   与 `inst_test.inc` 旧 `__REC` 同形、同寄存器约定（rb30 = 写指针）⇒ 指令流逐字节不变。
.macro SIGUPD reg
	st.o	\reg, [rb30, 0]
	add.si	rb30, SIG_SLOT
.endm

@@ 逐字节输出 `count` 个槽（SYS_WRITEC；`contract-semihosting §3`）。
@@   `count == 0` 直接不产码：循环是 do-while（先发一字节再减一），零长进循环会
@@   把 `rd17` 减成负数并永久循环 ⇒ 在宏内判掉（任意调用点都安全）。
.macro SIG_DUMP_CHARS buf, count
.if \count > 0
	set.rb rb16, \buf
	set.zw	rd16, wp0, SYS_WRITEC
	set.zw	rd17, wp0, (SIG_SLOT * (\count))
__sig_pc_\@:
	trap	cfx0, (SEMIHOST_TAG + SYS_WRITEC)
	add.si	rb16, 1
	add.si	rd17, -1
	br.nz	{rd17}?, [rb0, __sig_pc_\@]
.endif
.endm

@@ 整段输出 `count` 个槽：先 `SYS_WRITE`（handle 1）块写，未写则回退逐字节。
@@   参数块 `{1, buf, SIG_SLOT*count}` 写在 `buf + SIG_ARG_TAIL`。
@@   `rd8` 返回**未写字节数**：`< 0`（句柄无效）或 `== 长度`（句柄未打开）⇒ 回退；
@@   `0` ⇒ 完成；`0 < rd8 < 长度`（部分写）⇒ 不重复写，交给 host 侧长度断言判红。
.macro SIG_DUMP buf, count
.if \count > 0
	set.rb rb16, ((\buf) + SIG_ARG_TAIL)
	set.rd	rd20, 1
	st.o	rd20, [rb16, 0]			@@ 句柄 1 = 标准输出
	set.rd	rd20, \buf
	st.o	rd20, [rb16, 8]			@@ 缓冲区指针（PA，不经页表）
	set.rd	rd20, (SIG_SLOT * (\count))
	st.o	rd20, [rb16, 16]		@@ 字节数
	set.zw	rd16, wp0, SYS_WRITE
	trap	cfx0, (SEMIHOST_TAG + SYS_WRITE)
	br.z	{rd8}?, [rb0, __sig_dn_\@]	@@ 全部写完
	set.rd	rd20, (SIG_SLOT * (\count))
	br.eq	{rd8, rd20}?, [rb0, __sig_fb_\@]	@@ 整段未写 ⇒ 回退
	br.nn	{rd8}?, [rb0, __sig_fb_\@]		@@ 句柄无效 ⇒ 回退
	jump	[rb0, __sig_dn_\@]		@@ 部分写：不重复写
__sig_fb_\@:
	SIG_DUMP_CHARS \buf, \count
__sig_dn_\@:
.endif
.endm
