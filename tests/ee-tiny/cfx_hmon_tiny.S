@@ cfx_hmon_tiny.S — Kaiwu-Tiny cfx3 hmon handler：最小「保存-跳转」算法
@@ （由 cfx_power_tiny 装入 hmon SRAM；两者共同构成最初可用的执行环境）
@@ （m13-integ-007；M19 数据槽迁到 spec §6.2 的 0x0C00 页：m19-testcases-005）
@@
@@ 规范：spec/Kaiwu §1.1/§2/§4.4/§6.2；spec/DADAO-12 §5.1–§5.3；
@@       spec/DADAO-13 §1–§2（cfx_hmon cg3/cg5）。
@@
@@ 位置：BootROM 镜像偏移 0x0800–0x13FF（上限 3 KiB；m19-testcases-005）；
@@ 链接在 hmon SRAM 起始 0x0fff_0000_0000。段首即 hmon 入口 = 异常向量初值
@@ （DADAO-13 §1），入口是一条跳往处理体的 `jump`（见下「代码布局」）。
@@
@@ 数据页（hmon SRAM 内偏移，spec §6.2「数据 0x0C00–0x0CFF，初值 0」；页内偏移
@@ 是固件/框架契约，构建器 `build_tiny_bootrom.py` 机械校验）：
@@   0xC00  +0x00  excp_cause_id   （hmon 写，测试框架读）
@@   0xC08  +0x08  excp_cause_ip   （hmon 写，测试框架读）
@@   0xC10  +0x10  excp_cause_info （hmon 写，测试框架读）
@@   0xC18  +0x18  异常返回地址    （power 写默认值，框架可覆盖；hmon 读）
@@   0xC20  +0x20  保存的 rd63 原值（hmon 写/读）
@@   0xC28  +0x28  保存的 rb63 原值（hmon 写/读）
@@ 数据页在代码区之外：BootROM 表项 size = 代码长度，power 只复制代码区
@@ （≤ 0x0C00），数据页保持 hmon SRAM 初值 0。
@@
@@ 为什么需要第二个基址寄存器（`rb63`）：
@@   `ld.o`/`st.o` 的基址只能取 RB 组、立即数是有符号 12 位（`imms12`，
@@   spec/SimRISC-01），而 `rb0` 读出即当前 IP ⇒ 单条 `rb0` 相对访存最多到
@@   `IP + 0x7FF`。数据页在 `0x0C00`，入口 `IP = 0x0000` ⇒ **rb0 一条指令到不了
@@   `0x0C00`**。故处理体用 `rb63` 作数据页基址（`HMON_BASE + 0x0C00`），页内
@@   偏移是小立即数；`rb63` 的原值也必须保存（应用经 hmon 处理异常后 `rb63`
@@   必须完好）。
@@
@@ 代码布局（为什么处理体从 0x500 开始）：
@@   `rb63` 的原值只能存进数据页，而写数据页又先要有基址寄存器 —— 引导必须
@@   用一条 `rb0` 相对存（`st.o rb63, [rb0, imm]`）。这条指令的地址 =
@@   `IP + imm`，故 `IP ≥ 0x0C00 − 0x7FF = 0x401` 才够得到数据页。处理体放在
@@   0x500（`imm = 0xC28 − 0x500 = 0x728`），入口用一条相对 `jump` 跳到它。
@@   0x004–0x4FF 是段内填充零（代码区 ≤ 3 KiB，本段 ≈ 1.3 KiB）；不放可执行
@@   指令，也不与数据页重叠。
@@
@@ 主处理代码（无任何策略判断）：
@@   存 rb63 原值 → `rb63 = 数据页基址` → 存 rd63 原值；
@@   读 cg5 rc4/rc2/rc5（cause_id / prev_ip / cause_info）存 +0x00/+0x08/+0x10；
@@   从 +0x18 取返回地址写入 **`cg5 rc10`**（出口意图 escape ip）；
@@   从 +0x20/+0x28 恢复 rd63/rb63（`rb63` 最后恢复，之后不再用基址）；
@@   `escape cfx_hmon`（m18-spec-007 / ADR-0061 R3：只提供 cfxHA，返回点取 `rc10`）。
@@ 退出码与旧的分派策略都不在这里——它们是测试框架（应用）的职责。

	.include "tests/shared/asm/machine-tiny.inc"

	.equ	HMON_DATA,            0xC00	@@ 数据页起始（hmon SRAM 内偏移，§6.2）
	.equ	HMON_SLOT_CAUSE_ID,   0x00
	.equ	HMON_SLOT_CAUSE_IP,   0x08
	.equ	HMON_SLOT_CAUSE_INFO, 0x10
	.equ	HMON_SLOT_RETURN,     0x18
	.equ	HMON_SLOT_RD63,       0x20
	.equ	HMON_SLOT_RB63,       0x28
	.equ	HMON_BODY,            0x500	@@ 处理体起始（见「代码布局」）

	.text
	.globl	_start

_start:
	jump	[rb0, hmon_body]		@@ 0x000 入口 → 处理体（相对跳转）

	.org	HMON_BODY
hmon_body:
	@@ 引导：用 rb0（= 本指令 IP = 0x500）相对存 rb63 原值到数据页 +0x28
	st.o	rb63, [rb0, (HMON_DATA + HMON_SLOT_RB63 - HMON_BODY)]	@@ 0x500 -> 0xC28
	set.rb	rb63, HMON_BASE + HMON_DATA	@@ 0x504/0x508 数据页基址
	st.o	rd63, [rb63, HMON_SLOT_RD63]	@@ 0xC20 存 rd63 原值
	cfx2rd	cfx_hmon, cg5, rc4, rd63	@@ cause_id（rc4）
	st.o	rd63, [rb63, HMON_SLOT_CAUSE_ID]	@@ 0xC00
	cfx2rd	cfx_hmon, cg5, rc2, rd63	@@ prev ip（rc2）
	st.o	rd63, [rb63, HMON_SLOT_CAUSE_IP]	@@ 0xC08
	cfx2rd	cfx_hmon, cg5, rc5, rd63	@@ cause_info（rc5）
	st.o	rd63, [rb63, HMON_SLOT_CAUSE_INFO]	@@ 0xC10
	ld.o	rd63, [rb63, HMON_SLOT_RETURN]	@@ 0xC18 返回地址
	cfx2rc	cfx_hmon, cg5, rc10, rd63	@@ escape ip <- 返回地址
	ld.o	rd63, [rb63, HMON_SLOT_RD63]	@@ 0xC20 恢复 rd63
	ld.o	rb63, [rb63, HMON_SLOT_RB63]	@@ 0xC28 恢复 rb63（此后不再用基址）
	escape	cfx_hmon
