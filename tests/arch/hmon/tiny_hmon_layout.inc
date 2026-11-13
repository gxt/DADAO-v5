@@ tiny_hmon_layout.inc — Machine-v5-Tiny hmon 用例的 SRAM 布局（m13-gem5-001）
@@
@@ `tiny_hmon.S`（应用）使用本布局：应用在 SRAM 里放结果表与固定数据区，
@@ 并以符号调用自己的记录例程（`.rcheck`）。hmon 段是**共享最小 handler**
@@ （`tests/shared/bootrom/tiny/hmon.S`，m13-integ-007），它只读写 hmon SRAM
@@ 的数据槽（0xD8–0xFF），不引用应用侧的任何符号。
@@
@@ 数据区（DATA_BASE = ENTRY + 0x3100）内的字节偏移：
@@   +0x00 slot_ptr  结果槽指针（应用自建，记录例程追加）
@@   +0x10 failcnt   失配计数（SYS_EXIT 状态码据此选 0x21/0x71）
@@   +0x40 param     SYS_OPEN / SYS_WRITE / SYS_EXIT 参数块
@@   +0x80 fname     导出文件名
@@   +0xC0 msg       控制台消息

	.equ	RECORD_CHECK, ENTRY + 0x2000
	.equ	DATA_BASE, ENTRY + 0x3100
	.equ	RESULTS, ENTRY + 0x4000

	.equ	SLOT_PTR, DATA_BASE + 0x00
	.equ	FAILCNT, DATA_BASE + 0x10
	.equ	PARAM, DATA_BASE + 0x40
	.equ	FNAME, DATA_BASE + 0x80
	.equ	MSG, DATA_BASE + 0xC0
