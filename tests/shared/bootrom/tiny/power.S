@@ power.S — Machine-v5-Tiny power 启动 stub（m12-chipyard-007）
@@
@@ 规范：spec/Machine-v5 §6.1（image index table）/ §6.2（Tiny 的 hmon 装载契约）。
@@ 位置：BootROM 镜像偏移 0x0000–0x1FFF（上限 8 KiB），链接在复位向量
@@ 0xffff_ffff_0000；偏移 0 即复位指令。
@@
@@ 顺序（§6.2「power 的装载与移交顺序」1–8）：
@@   1. 校验表头与 hmon 表项（失败 ⇒ park：不进入 hmon、不静默继续）；
@@   2. 逐 8 字节把 hmon 段从 BootROM 复制到 hmon SRAM 起始；
@@   3. （Tiny 无 cache，该批写入对同一 hart 的后续取指自然可见）
@@   4. 写 cfx_hmon_hypv_excp_vector（幂等，初值已是 hmon SRAM 起始）；
@@   5. （Tiny 的 switch_run_mode 写入被忽略、保存值保持 3，§2）
@@   6. trap cfx_hmon, <boot_magic> 按 CFXTRAP 移交 hmon；
@@   7. hmon 校验后 escape 回本 stub；
@@   8. 跳固定应用入口 0xffff_ff01_0100，不返回。
@@
@@ 寄存器约定：rb0 = 当前 IP（只读）；rd0 = 0。本 stub 不建栈、不做宿主调用。
@@ 只使用 m12-005 已实现的整数子集（ld.o/st.o/set.zw/or.w/and.o/shr.uo/
@@ add.o/sub.o/cmp.uo/add.si/jump）+ 本任务新增的 br.* 与 cfx2rc/trap。

	.include "tests/shared/asm/machine-tiny.inc"
	.include "tests/shared/asm/machine.inc"
	.include "tests/shared/bootrom/tiny/tiny_common.inc"

	.text
	.globl	_start

_start:
	@@ 常量寄存器（rd 组）
	set.zw	rd20, wp0, 0x0001		@@ 1
	set.zw	rd21, wp0, 0xffff		@@ 0xffff
	LD64	rd22, 0xffff, 0xffff, 0x0000, 0x0000	@@ 0x0000_0000_ffff_ffff
	set.zw	rd23, wp0, 0x0007		@@ 7
	LD64	rd24, 0x2000, 0x0000, 0x0000, 0x0000	@@ 8 KiB（hmon 段上限）
	LD64	rd26, 0x4f54, 0x4442, 0x0000, 0x0000	@@ magic "DBOT"
	LD64	rd27, 0x0001, 0x0003, 0x0000, 0x0000	@@ boot_magic 0x0003_0001

	@@ ---- 表头（16 字节）：magic(4) version(2) count(2) boot_magic(4) resv(4)
	LOAD_ADDR rb3, BOOTROM_BASE + 0xe000	@@ image index table 固定偏移 0xE000

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
	shr.uo	rd7, rd10, 3			@@ flags[31:3] 必须为 0
	br.nz	{rd7}?, [rb0, power_park]
	shr.uo	rd11, rd6, 32			@@ type
	cmp.uo	rd9, rd11, rd20			@@ type == 1（hmon）
	br.nz	{rd9}?, [rb0, power_park]

	ld.o	rd6, [rb3, 24]			@@ offset
	and.o	rd7, rd6, rd23			@@ offset 8 字节对齐
	br.nz	{rd7}?, [rb0, power_park]
	ld.o	rd3, [rb3, 32]			@@ size
	br.z	{rd3}?, [rb0, power_park]	@@ size != 0
	and.o	rd7, rd3, rd23			@@ size 8 字节对齐
	br.nz	{rd7}?, [rb0, power_park]
	cmp.uo	rd9, rd3, rd24			@@ size <= 8 KiB
	br.p	{rd9}?, [rb0, power_park]
	ld.o	rd7, [rb3, 40]			@@ 表项 reserved 必须为 0
	br.nz	{rd7}?, [rb0, power_park]

	@@ ---- 段边界：offset + size 落在 64 KiB 镜像内
	LOAD_ADDR rb6, BOOTROM_BASE
	add.o	rb6, rb6, rd6			@@ src = BOOTROM_BASE + offset
	add.o	rb5, rb6, rd3			@@ src_end = src + size
	LOAD_ADDR rb7, 0x0001000000000000	@@ 2^48（BootROM 之上界）
	sub.o	rd5, rb5, rb7
	br.p	{rd5}?, [rb0, power_park]	@@ src_end > 2^48

	@@ ---- 逐 8 字节复制 hmon 段：dst = hmon SRAM 起始（§6.2 第 2 步）
	LOAD_ADDR rb7, HMON_BASE
	shr.uo	rd5, rd3, 3			@@ 8 字节字数
power_copy:
	ld.o	rd6, [rb6, 0]
	st.o	rd6, [rb7, 0]
	add.si	rb6, 8
	add.si	rb7, 8
	add.si	rd5, -1
	br.nz	{rd5}?, [rb0, power_copy]

	@@ ---- 向量幂等写入（初值已是 hmon SRAM 起始，DADAO-13 §1）
	LOAD_ADDR rd4, HMON_BASE
	cfx2rc	cfx_hmon, cg3, rc10, rd4

	@@ ---- power -> hmon 移交（CFXTRAP；boot_magic 与表头一致）
	@@ 构建器按镜像表的 boot_magic 字段改写下面这条指令的 immu18。
	.globl	boot_magic_trap
boot_magic_trap:
	trap	cfx_hmon, 0x30001

	@@ ---- hmon escape 回到这里：跳固定应用入口（§6.2 第 8 步）
	LOAD_ADDR rb2, ENTRY
	jump	[rb2, rd0, 0]

power_park:
	@@ §6.1 失败语义：停在 BootROM 的 park 循环
	jump	[rb0, rd0, 0]
