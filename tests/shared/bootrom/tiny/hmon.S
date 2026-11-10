@@ hmon.S — Machine-v5-Tiny 最小 cfx3 hmon handler（m12-chipyard-007）
@@
@@ 规范：spec/Machine-v5 §6.2 第 7 步 + §2（移交/运行模式）；
@@       spec/DADAO-12 §5.1–§5.3（trap 进入 / escape 退出）；
@@       spec/DADAO-13 §1–§2（cfx_hmon cg3/cg5 寄存器）。
@@
@@ 位置：BootROM 镜像偏移 0x2000–0x3FFF（上限 8 KiB），链接在 hmon SRAM 起始
@@ 0x0fff_0000_0000；段首即 hmon 入口 = 异常向量初值（DADAO-13 §1）。
@@
@@ 本任务只做「移交返回」，不做异常分派（五类同步异常/退出码归 m12-chipyard-019）：
@@   入口即向量；
@@   1. 校验 CFXTRAP：cfx_hmon cg5 rc2（excp_cause_id）= 1 << 0；
@@   2. 校验 magic  ：cfx_hmon cg5 rc4（excp_cause_info，trap 的指令编码）
@@                   的 immu18 = 表头 boot_magic（§6.1 boot_magic = 0x30001）；
@@   3. `escape cfx_hmon, [excp_cause_ip, 4]` 返回 power stub。
@@ 任一校验失败 ⇒ 停在 park 循环（不静默继续）。

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"
	.include "tests/shared/bootrom/tiny/tiny_common.inc"

	.text
	.globl	_start

_start:
	@@ 入口即向量（hmon SRAM 起始）。先校验 CFXTRAP = 1（one-hot 位索引 0）。
	set.zw	rd7, wp0, 0x0001
	cfx2rd	cfx_hmon, cg5, rc2, rd6		@@ excp_cause_id
	cmp.uo	rd9, rd6, rd7
	br.nz	{rd9}?, [rb0, hmon_park]

	@@ 校验 magic：cause_info 的低 18 位 = trap 的 immu18 = boot_magic。
	cfx2rd	cfx_hmon, cg5, rc4, rd6		@@ excp_cause_info（指令编码）
	LD64	rd8, 0xffff, 0x0003, 0x0000, 0x0000	@@ 0x0003_ffff（immu18 掩码）
	and.o	rd6, rd6, rd8
	LD64	rd8, 0x0001, 0x0003, 0x0000, 0x0000	@@ 0x0003_0001（boot_magic）
	cmp.uo	rd9, rd6, rd8
	br.nz	{rd9}?, [rb0, hmon_park]

	@@ 返回 power stub：跳过 trap 指令（偏移 +4，DADAO-12 §5.3）
	escape	cfx_hmon, [excp_cause_ip, 4]

hmon_park:
	jump	[rb0, rd0, 0]
