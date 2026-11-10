@@ hmon.S — Machine-v5-Tiny cfx3 hmon handler：最小「保存-跳转」算法
@@ （m13-integ-007；用户 2026-11-11 第二次修正，见
@@   .tao/knowledge/refs/m12-006-cycle-design.md §11）
@@
@@ 规范：spec/Machine-v5 §1.1/§2/§4.4/§6.2；spec/DADAO-12 §5.1–§5.3；
@@       spec/DADAO-13 §1–§2（cfx_hmon cg3/cg5）。
@@
@@ 位置：BootROM 镜像偏移 0x2000–0x3FFF；链接在 hmon SRAM 起始
@@ 0x0fff_0000_0000。段首即 hmon 入口 = 异常向量初值（DADAO-13 §1），
@@ 因此代码从 0x00 开始、不需要 jump。
@@
@@ 固定布局（hmon SRAM 内偏移，三方共用；构建器强制）：
@@   0x00  代码起点（10 条指令，44 B；代码区上限 0xD8 = 216 B）
@@   0xD8  保存的 rd63 原值                （hmon 写/读）
@@   0xE0  excp_cause_id                  （hmon 写，测试框架读）
@@   0xE8  excp_cause_ip                  （hmon 写，测试框架读）
@@   0xF0  excp_cause_info                （hmon 写，测试框架读）
@@   0xF8  异常返回地址                    （power 写默认值，框架可覆盖；hmon 读）
@@
@@ 数据区在代码区之外：BootROM 表项 size = 代码长度，power 只复制代码区，
@@ 数据区保持 hmon SRAM 初值。
@@
@@ 主处理代码（无任何策略判断）：
@@   读 cg5 rc2/rc3/rc4（cause_id / cause_ip / cause_info）存 0xE0/0xE8/0xF0；
@@   从 0xF8 取返回地址写入 excp_cause_ip；从 0xD8 恢复 rd63；
@@   `escape cfx_hmon, [excp_cause_ip, 0]`。
@@ 退出码与旧的分派策略都不在这里——它们是测试框架（应用）的职责。

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"

	.equ	HMON_SLOT_RD63,       0xD8
	.equ	HMON_SLOT_CAUSE_ID,   0xE0
	.equ	HMON_SLOT_CAUSE_IP,   0xE8
	.equ	HMON_SLOT_CAUSE_INFO, 0xF0
	.equ	HMON_SLOT_RETURN,     0xF8

	.text
	.globl	_start

_start:
	st.o	rd63, [rb0, HMON_SLOT_RD63]			@@ 0x00
	cfx2rd	cfx_hmon, cg5, rc2, rd63			@@ 0x04 cause_id
	st.o	rd63, [rb0, HMON_SLOT_CAUSE_ID - 0x08]		@@ 0x08 -> 0xE0
	cfx2rd	cfx_hmon, cg5, rc3, rd63			@@ 0x0c cause_ip
	st.o	rd63, [rb0, HMON_SLOT_CAUSE_IP - 0x10]		@@ 0x10 -> 0xE8
	cfx2rd	cfx_hmon, cg5, rc4, rd63			@@ 0x14 cause_info
	st.o	rd63, [rb0, HMON_SLOT_CAUSE_INFO - 0x18]	@@ 0x18 -> 0xF0
	ld.o	rd63, [rb0, HMON_SLOT_RETURN - 0x1c]		@@ 0x1c <- 0xF8
	cfx2rc	cfx_hmon, cg5, rc3, rd63			@@ 0x20 cause_ip <- 返回地址
	ld.o	rd63, [rb0, HMON_SLOT_RD63 - 0x24]		@@ 0x24 <- 0xD8（恢复）
	escape	cfx_hmon, [excp_cause_ip, 0]			@@ 0x28
