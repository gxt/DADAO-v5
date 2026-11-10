@@ hmon.S — Machine-v5-Tiny cfx3 hmon handler（m12-chipyard-007；m12-chipyard-019 补分派）
@@
@@ 规范：spec/Machine-v5 §6.2 第 7 步 + §2（移交/运行模式）+ §4.4（五类同步异常）；
@@       spec/DADAO-12 §5.1–§5.3（trap 进入 / escape 退出）；
@@       spec/DADAO-13 §1–§2（cfx_hmon cg3/cg5 寄存器）。
@@
@@ 位置：BootROM 镜像偏移 0x2000–0x3FFF（上限 8 KiB），链接在 hmon SRAM 起始
@@ 0x0fff_0000_0000；段首即 hmon 入口 = 异常向量初值（DADAO-13 §1）。
@@
@@ 入口即向量，分派（m12-chipyard-019）：
@@   1. 现场三读：cfx_hmon cg5 rc2/rc3/rc4（excp_cause_id / ip / info）；
@@      每条分派都先读这三个寄存器（诊断日志据此逐次给出现场）；
@@   2. CFXTRAP（1 << 0）：校验 magic —— cause_info 的 immu18 = 表头
@@      boot_magic（§6.1）—— 通过后 escape +4 回 power stub（007 的移交路径）；
@@   3. IALIGN（1 << 13）：cause_ip 即非法 IP（IP 停留在非法地址，§4.4）；
@@      把 excp_cause_ip 改为「(cause_ip & ~3) + 4」（跳过非法地址所在的
@@      4 字节字）后 escape 0 返回；是否重试/跳过由 hmon 软件决定（§4.4）；
@@   4. 其余同步异常（CFXMEM/ILLI/UNDI/MALIGN）：escape +4（跳过触发指令，
@@      精确异常 ⇒ 该指令不写回、不访存）；
@@   5. 同步异常返回前把 excp_prev_run_mode 复位为 3：Tiny 恒 hypv
@@      （spec/Machine-v5 §2）。
@@ 任一 magic 校验失败 ⇒ 停在 park 循环（不静默继续）。
@@ 被改写（clobber）的寄存器：rd6–rd14；应用不得跨异常依赖这些寄存器。

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"
	.include "tests/shared/bootrom/tiny/tiny_common.inc"

	.text
	.globl	_start

_start:
	@@ 1. 现场：每条分派先读 cause id / ip / info（顺序固定，便于逐次对齐）
	cfx2rd	cfx_hmon, cg5, rc2, rd6		@@ excp_cause_id
	cfx2rd	cfx_hmon, cg5, rc3, rd7		@@ excp_cause_ip
	cfx2rd	cfx_hmon, cg5, rc4, rd8		@@ excp_cause_info

	@@ 2. CFXTRAP（1 << 0）?
	set.zw	rd9, wp0, 0x0001
	cmp.uo	rd10, rd6, rd9
	br.z	{rd10}?, [rb0, hmon_cfxtrap]

	@@ 3. 同步异常：Tiny 恒 hypv —— 返回前把 excp_prev_run_mode 复位为 3
	set.zw	rd11, wp0, 0x0003
	cfx2rc	cfx_hmon, cg5, rc0, rd11

	@@ 4. IALIGN（1 << 13）?
	LD64	rd12, 0x2000, 0x0000, 0x0000, 0x0000	@@ 1 << 13
	and.o	rd13, rd6, rd12
	cmp.uo	rd14, rd13, rd0
	br.nz	{rd14}?, [rb0, hmon_ialign]

	@@ 5. CFXMEM/ILLI/UNDI/MALIGN：跳过触发指令（+4）
	escape	cfx_hmon, [excp_cause_ip, 4]

hmon_ialign:
	@@ IP 停留在非法地址（cause_ip = 非法地址）：对齐到下一个 4 字节边界后
	@@ 以 escape 0 返回（返回地址 = 改写后的 excp_cause_ip）。
	LD64	rd12, 0xfffc, 0xffff, 0xffff, 0xffff	@@ ~3（低 2 位清零）
	and.o	rd13, rd7, rd12
	add.si	rd13, 4
	cfx2rc	cfx_hmon, cg5, rc3, rd13	@@ excp_cause_ip = 对齐地址 + 4
	escape	cfx_hmon, [excp_cause_ip, 0]

hmon_cfxtrap:
	@@ 校验 magic：cause_info 的低 18 位 = trap 的 immu18 = boot_magic
	LD64	rd12, 0xffff, 0x0003, 0x0000, 0x0000	@@ 0x0003_ffff（immu18 掩码）
	and.o	rd8, rd8, rd12
	LD64	rd13, 0x0001, 0x0003, 0x0000, 0x0000	@@ 0x0003_0001（boot_magic）
	cmp.uo	rd10, rd8, rd13
	br.nz	{rd10}?, [rb0, hmon_park]

	@@ 返回 power stub：跳过 trap 指令（偏移 +4，DADAO-12 §5.3）
	escape	cfx_hmon, [excp_cause_ip, 4]

hmon_park:
	jump	[rb0, rd0, 0]
