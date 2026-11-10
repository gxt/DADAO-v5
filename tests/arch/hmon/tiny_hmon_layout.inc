@@ tiny_hmon_layout.inc — Machine-v5-Tiny hmon 用例的 SRAM 布局（m13-gem5-001）
@@
@@ `tiny_hmon.S`（应用）与 `tiny_hmon_handler.S`（hmon 段）共用同一份布局：
@@ 应用在 SRAM 里放结果表与固定数据区，hmon handler 通过同一批符号写结果记录、
@@ 读恢复地址、写 handler mailbox / 读 PROBE。两段由 `build_tiny_bootrom.py`
@@ 装进同一个 BootROM 镜像，因此符号值必须与应用 ELF 的链接布局一致
@@ （`tiny_hmon.lds`：.rcheck = ENTRY+0x2000、.data = ENTRY+0x3100、
@@ .results = ENTRY+0x4000）。
@@
@@ 数据区（DATA_BASE = ENTRY + 0x3100）内的字节偏移：
@@   +0x00 slot_ptr  结果槽指针（应用自建，hmon 追加）
@@   +0x08 recovery  IALIGN 恢复地址（handler escape 0 的目标）
@@   +0x10 failcnt   失配计数（SYS_EXIT 状态码据此选 0x21/0x71）
@@   +0x18 handle    SYS_OPEN 返回的文件句柄
@@   +0x20 probe     handler 是否要在本次异常里读一次 cg3（应用置 1）
@@   +0x28 mailbox   handler 入口 PC（供应用记录移交帧）
@@   +0x40 param     SYS_OPEN / SYS_WRITE / SYS_EXIT 参数块
@@   +0x80 fname     导出文件名
@@   +0xC0 msg       控制台消息

	.equ	RECORD_CHECK, ENTRY + 0x2000
	.equ	DATA_BASE, ENTRY + 0x3100
	.equ	RESULTS, ENTRY + 0x4000

	.equ	SLOT_PTR, DATA_BASE + 0x00
	.equ	RECOVERY, DATA_BASE + 0x08
	.equ	FAILCNT, DATA_BASE + 0x10
	.equ	HANDLE, DATA_BASE + 0x18
	.equ	PROBE, DATA_BASE + 0x20
	.equ	MAILBOX, DATA_BASE + 0x28
	.equ	PARAM, DATA_BASE + 0x40
	.equ	FNAME, DATA_BASE + 0x80
	.equ	MSG, DATA_BASE + 0xC0
