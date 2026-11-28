@@ cfx_power_tiny.S — Kaiwu-Tiny cfx_power 启动 stub：校验镜像表、把 cfx_hmon_tiny
@@ 装入 hmon SRAM 并移交，从而构建最初可用的执行环境（m12-chipyard-007；
@@ M19 8 KiB 几何见 m19-testcases-005）
@@
@@ 规范：spec/Kaiwu §1.1（核内地址空间）/ §6.1（image index table）/
@@       §6.2（Tiny 的 8 KiB BootROM 布局与 hmon 装载契约）/ §6.2.1（主 SRAM 布局）。
@@ 位置：BootROM 镜像偏移 0x0000–0x07FF（上限 2 KiB），链接在复位向量
@@ 0xffff_ffff_0000；偏移 0 即复位指令。表在镜像偏移 0x1F00。
@@
@@ 顺序（§6.2「power 的装载与移交顺序」）：
@@   1. 校验表头与 hmon 表项（失败 ⇒ park：不进入 hmon、不静默继续）；
@@      按 8 KiB 几何校验：offset == 0x800、size ≤ 0x0C00、offset + size ≤ 0x1400；
@@   2. 放核握手（VERSION/MAILBOX，§6.2.1）：**未实现** —— MAILBOX magic 仍是
@@      `[OPEN]`（§6.2.1），没有可比较的值；不猜值、不在此设假桩；
@@   3. 逐 8 字节把 hmon 段（表项 size = 代码长度）复制到 hmon SRAM 起始；
@@      数据区（0x0C00–0x0CFF）与栈不在镜像段内，保持 SRAM 初值 0；
@@   4. 写 hmon 数据页 +0x18 的默认返回地址（= 本 trap 的下一条指令）；
@@   5. （Tiny 无 cache ⇒ 该批写入对同一 hart 的后续取指自然可见）
@@   6. （Tiny 的 switch_run_mode 写入被忽略、保存值保持 3，§2；异常向量初值
@@      已等于 hmon SRAM 起始，§4.4 ⇒ 两者都不写）
@@   7. trap cfx_hmon, <boot_magic> 按 CFXTRAP 移交 hmon；
@@   8. hmon 按本 stub 写入的默认返回地址 escape 回本 stub；
@@   9. 跳固定应用入口 0xffff_ff00_2000（= ENTRY，§6.2 第 9 步），不返回。
@@
@@ 寄存器约定：rb0 = 当前 IP（只读）；rd0 = 0。本 stub 不建栈、不做宿主调用。
@@ 只使用 m12-005 已实现的整数子集（ld.o/st.o/set.zw/set.rd/or.w/and.o/shr.uo/
@@ add.o/sub.o/cmp.uo/add.si/jump）+ br.*/cfx2rc/trap，以及 rb2rd（读当前 IP）。

	.include "tests/shared/asm/machine-tiny.inc"

	.text
	.globl	_start

_start:
	@@ 常量寄存器（rd 组）
	set.zw	rd20, wp0, 0x0001		@@ 1
	set.zw	rd21, wp0, 0xffff		@@ 0xffff
	set.rd rd22, 0x00000000ffffffff	@@ 0x0000_0000_ffff_ffff
	set.zw	rd23, wp0, 0x0007		@@ 7
	set.zw	rd30, wp0, 0x0003		@@ 表项 flags = 0x3（必需 + 装入，扁平段不校验）
	set.rd rd24, 0x0000000000000c00	@@ 表项 size 上限（hmon 源段 ≤ 3 KiB）
	set.rd rd28, 0x0000000000000800	@@ 表项 offset 固定值
	set.rd rd26, 0x0000000044424f54	@@ magic "DBOT"
	set.rd rd27, 0x0000000000030001	@@ boot_magic 0x0003_0001

	@@ ---- 表头（16 字节）：magic(4) version(2) count(2) boot_magic(4) resv(4)
	set.rb rb3, BOOTROM_BASE + 0x1f00	@@ image index table 固定偏移 0x1F00

	ld.o	rd6, [rb3, 0]			@@ magic | version | count | boot_magic[31:16]
	shr.uo	rd7, rd6, 32			@@ magic
	cmp.uo	rd9, rd7, rd26
	br.nz	{rd9}?, [rb0, power_park]
	shr.uo	rd7, rd6, 16			@@ version
	and.o	rd7, rd7, rd21
	cmp.uo	rd9, rd7, rd20
	br.nz	{rd9}?, [rb0, power_park]
	and.o	rd7, rd6, rd21			@@ count（Tiny = 1）
	cmp.uo	rd9, rd7, rd20
	br.nz	{rd9}?, [rb0, power_park]

	ld.o	rd6, [rb3, 8]			@@ boot_magic | reserved
	shr.uo	rd7, rd6, 32			@@ boot_magic
	cmp.uo	rd9, rd7, rd27
	br.nz	{rd9}?, [rb0, power_park]
	and.o	rd7, rd6, rd22			@@ reserved 必须为 0
	br.nz	{rd7}?, [rb0, power_park]

	@@ ---- hmon 表项（32 字节，自偏移 16）：type(4) flags(4) offset(8) size(8) resv(8)
	ld.o	rd6, [rb3, 16]			@@ type | flags
	and.o	rd10, rd6, rd22			@@ flags
	cmp.uo	rd9, rd10, rd30			@@ flags == 0x3（bit31:3 为 0 由此蕴含）
	br.nz	{rd9}?, [rb0, power_park]
	shr.uo	rd11, rd6, 32			@@ type
	cmp.uo	rd9, rd11, rd20			@@ type == 1（hmon）
	br.nz	{rd9}?, [rb0, power_park]

	ld.o	rd6, [rb3, 24]			@@ offset
	and.o	rd7, rd6, rd23			@@ offset 8 字节对齐
	br.nz	{rd7}?, [rb0, power_park]
	cmp.uo	rd9, rd6, rd28			@@ offset == 0x800（§6.2 固定 hmon 源段）
	br.nz	{rd9}?, [rb0, power_park]
	ld.o	rd3, [rb3, 32]			@@ size
	br.z	{rd3}?, [rb0, power_park]	@@ size != 0
	and.o	rd7, rd3, rd23			@@ size 8 字节对齐
	br.nz	{rd7}?, [rb0, power_park]
	cmp.uo	rd9, rd3, rd24			@@ size <= 3 KiB
	br.p	{rd9}?, [rb0, power_park]
	ld.o	rd7, [rb3, 40]			@@ 表项 reserved 必须为 0
	br.nz	{rd7}?, [rb0, power_park]

	@@ ---- 段边界：offset + size 落在 hmon 源窗口（0x0800..0x1400）内，
	@@ 即整体落在 8 KiB 镜像内；src = BOOTROM_BASE + offset 同时备好供复制用
	set.rb rb6, BOOTROM_BASE
	add.o	rb6, rb6, rd6			@@ src = BOOTROM_BASE + offset
	add.o	rb5, rb6, rd3			@@ src_end = src + size
	set.rb rb7, BOOTROM_BASE + 0x1400	@@ hmon 源窗口末（0x0800 + 0x0C00）
	cmp.uo	rd9, rb5, rb7
	br.p	{rd9}?, [rb0, power_park]	@@ src_end > 窗口末

	@@ ---- 逐 8 字节复制 hmon 段：dst = hmon SRAM 起始（§6.2 第 3 步）
	set.rb rb7, HMON_BASE			@@ dst = hmon SRAM 起始
	shr.uo	rd5, rd3, 3			@@ 8 字节字数
power_copy:
	ld.o	rd6, [rb6, 0]
	st.o	rd6, [rb7, 0]
	add.si	rb6, 8
	add.si	rb7, 8
	add.si	rd5, -1
	br.nz	{rd5}?, [rb0, power_copy]

	@@ ---- hmon 默认返回地址（m13-integ-007）：hmon 数据页 +0x18 = 本 trap 的
	@@ 下一条指令。数据页在 hmon SRAM 偏移 0x0C00（§6.2），超出 rb0 相对的单条
	@@ ld/st 立即数范围（`imms12`，SimRISC-01）⇒ 用 set.rb 取数据页基址。
	@@ 先把两个 scratch 寄存器设成已知值：hmon 必须把它们保存在数据页、退出前
	@@ 恢复（cfx_hmon_tiny.S）；这些值同时是移交后自检的基准。
	set.rd	rd63, 0x0a0b000000000011	@@ hmon 必须保存/恢复的 rd63
	set.rb	rb63, 0x0000000000000b0b	@@ hmon 的第二个基址寄存器（原值）
	set.rb rb7, HMON_BASE + 0x0c00		@@ hmon 数据页基址
	@@ rb2rd 读当前 IP（= 本指令地址 X）；布局 rb2rd(X)/add.si(X+4)/
	@@ st.o(X+8)/trap(X+12) ⇒ trap + 4 = X + 16。
	rb2rd	rd4, rb0, 1
	add.si	rd4, 16
	st.o	rd4, [rb7, 0x18]

	@@ ---- power -> hmon 移交（CFXTRAP；boot_magic 与表头一致）
	@@ 构建器按镜像表的 boot_magic 字段改写下面这条指令的 immu18。
	.globl	boot_magic_trap
boot_magic_trap:
	trap	cfx_hmon, 0x30001

	@@ ---- hmon escape 回到这里：先自检两个 scratch 寄存器已复原（否则 park），
	@@ 再跳固定应用入口（§6.2 第 9 步）
	set.rd	rd13, 0x0a0b000000000011
	cmp.uo	rd9, rd63, rd13
	br.nz	{rd9}?, [rb0, power_park]
	set.rb	rb13, 0x0000000000000b0b
	cmp.uo	rd9, rb63, rb13
	br.nz	{rd9}?, [rb0, power_park]
	set.rb rb2, ENTRY
	jump	[rb2, rd0, 0]

power_park:
	@@ §6.1 失败语义：停在 BootROM 的 park 循环
	jump	[rb0, rd0, 0]
