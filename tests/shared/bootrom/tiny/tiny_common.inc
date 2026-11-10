@@ tiny_common.inc — Machine-v5-Tiny BootROM 固件（power stub + hmon handler）的
@@ 共用汇编宏（m12-chipyard-007）。
@@
@@ LD64：把 64 位常量物化为一个寄存器。立即数字段只有 16 位（wyde），
@@ 因此按 wyde 逐个 set.zw/or.w 拼装（spec/SimRISC-03；machine.inc 的
@@ LOAD_ADDR 用的是同一手法，只是它只针对完整 64 位地址、不含省略）。
@@ `w0` 为最低 wyde；`wp0`–`wp3` 依次是高一级 wyde 位置。
@@ 值为 0 的 wyde 直接省略（少一条指令，语义不变）。

	.macro	LD64 rd, w0, w1, w2, w3
	set.zw	\rd, wp0, \w0
	.if \w1 != 0
	or.w	\rd, wp1, \w1
	.endif
	.if \w2 != 0
	or.w	\rd, wp2, \w2
	.endif
	.if \w3 != 0
	or.w	\rd, wp3, \w3
	.endif
	.endm
