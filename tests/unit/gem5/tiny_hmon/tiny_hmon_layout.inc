@@ tiny_hmon_layout.inc — Kaiwu-Tiny hmon 用例的 SRAM 布局（m13-gem5-001）
@@
@@ `tiny_hmon.S`（应用）使用本布局：应用在 SRAM 里放结果表与固定数据区，
@@ 并以符号调用自己的记录例程（`.rcheck`）。hmon 段是**共享最小 handler**
@@ （`tests/ee-tiny/cfx_hmon_tiny.S`，m13-integ-007；m15-testcases-011 迁至 `tests/ee-tiny/`），
@@ 它只读写 hmon SRAM 数据页（0xC00–0xCFF，m19-testcases-005）的槽，
@@ 不引用应用侧的任何符号。
@@
@@ hmon SRAM 数据页（HMON_BASE + 0xC00）的页内字节偏移：
@@   +0x00 cause_id      excp_cause_id（hmon 写，应用读）
@@   +0x08 cause_ip      excp_cause_ip（hmon 写，应用读）
@@   +0x10 cause_info    excp_cause_info（hmon 写，应用读）
@@   +0x18 return        异常返回地址（power 写默认值，框架可覆盖；hmon 读）
@@   +0x20 saved rd63    hmon 保存/恢复
@@   +0x28 saved rb63    hmon 保存/恢复
@@
@@ 应用数据区（DATA_BASE = ENTRY + 0x3100）内的字节偏移：
@@   +0x00 slot_ptr  结果槽指针（应用自建，记录例程追加）
@@   +0x10 failcnt   失配计数（SYS_EXIT 状态码据此选 0x21/0x71）
@@   +0x40 param     SYS_OPEN / SYS_WRITE / SYS_EXIT 参数块
@@   +0x80 fname     导出文件名
@@   +0xC0 msg       控制台消息
@@
@@ hmon 数据页（spec/Kaiwu §6.2：代码 0x0000–0x0BFF、数据 0x0C00–0x0CFF、
@@ 栈 0x0D00–0x1FFF；数据页在表项 size 之外，保持 SRAM 初值 0）。
	.equ	HMON_DATA,            0xC00
	.equ	HMON_SLOT_CAUSE_ID,   0x00
	.equ	HMON_SLOT_CAUSE_IP,   0x08
	.equ	HMON_SLOT_CAUSE_INFO, 0x10
	.equ	HMON_SLOT_RETURN,     0x18
	.equ	HMON_SLOT_RD63,       0x20
	.equ	HMON_SLOT_RB63,       0x28

	.equ	RECORD_CHECK, ENTRY + 0x2000
	.equ	DATA_BASE, ENTRY + 0x3100
	.equ	RESULTS, ENTRY + 0x4000

	.equ	SLOT_PTR, DATA_BASE + 0x00
	.equ	FAILCNT, DATA_BASE + 0x10
	.equ	PARAM, DATA_BASE + 0x40
	.equ	FNAME, DATA_BASE + 0x80
	.equ	MSG, DATA_BASE + 0xC0
