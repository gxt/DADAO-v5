@@ escape_ciii_cfx.S — escape cfxHA（ciii, opc 0x7E）
@@ 大类：11-cfx（核芯功能扩展，`spec/SimRISC-11 §3`）；册目录 `tests/inst/11-cfx/`
@@ id：escape_ciii_cfx　形式：ciii　opc：0x7E　mask：0xFF000000　value：0x7E000000
@@ 语义（`spec/DADAO-12 §5.1/§5.3`，`m18-spec-007` / ADR-0061 R3）：
@@   唯一操作数是 `cfxHA`，`imms18` 必须为 0（SBZ；非 0 ⇒ ILLI）；`cfxha` reserved
@@   ⇒ ILLI；`cfxha != inner_cfx_code` ⇒ 当前 cfx 的 CFXESC；返回的四元组取自
@@   当前 cfx 的 `cg5` **出口意图** `rc8`–`rc11`（run mode / cfx code / ip / intr mask）；
@@   目标模式（`rc8`）不得高于当前模式、目标 cfx（`rc9`）必须已实现、目标模式必须有
@@   monitor，否则在切换任何状态前报当前 cfx 的 CFXESC；`escape_num` 每次 +1；
@@   `rc11` **整字**写入目标模式 monitor 的 `cg15 rc3`（与切模式/切 cfx/跳转原子）。
@@   不设“帧有效位”：`cg5 rc4`（cause id）为 0 也可返回。
@@ 编码：ciii = opc[31:24] | cfxha[23:18] | imms18[17:0]；`escape cfxHA` ⇒ imms18 = 0。
@@ 链接布局：`tests/ee-tiny/tests_inst_tiny.lds`（全部册共用（00 + 01–12）；段地址由宏层 `inst_test.inc` 固定）
@@ 用例：encoding/semantic/boundary 链例 28 + 故障例 9（共 37 个检查点）
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；故障例退出码 = `0xF0|异常位索引`
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 三方比较的是字节流
@@ 探针：应用运行在 cfx_power(63)/hypv（`spec/Kaiwu §1` 启动链），自建 hmon 入口
@@   （`cfx_hmon cg3 rc15`）与 cfx_power 入口（`cfx_power cg3 rc15`）分别接管同步
@@   trap 与 CFXESC；handler 把 `cg5 rc0`–`rc5`/`rc8`–`rc11` 记到 RAM 槽（SSCR/PSCR），
@@   落点逐项核。期望值全部由 `spec/DADAO-12 §3.6/§5.1/§5.3` 与编码定义内联派生。
@@ GAP（不计入链例）：① `escape_num` 在 chipyard RTL 无 cg4 ⇒ 三平台不一致
@@   （QEMU 已实现，链例 12/18 在 QEMU 上生效）；② 升权与“目标模式无 monitor”
@@   （如 jail→jmon 不存在）在 Tiny 不可构造（Tiny 恒 hypv、无 jail），由
@@   `tests/arch/hart/cfx15.S`（Vast/supv）承接；③ 异步进入的写入集合需 cfx_hart，
@@   Tiny 不实现该 cfx ⇒ 同由 `cfx15.S` 承接。

	.include "tests/inst/macros/inst_test.inc"

@@ ---- 本文件局部宏（不改共享宏层；宏体不含检查行）----
	.equ	SSCR, TEST_DATA + 0x1C00	@@ hmon handler 记录槽（RAM，power 可读）
	.equ	PSCR, TEST_DATA + 0x1D00	@@ cfx_power handler 记录槽
	.equ	P0, 0x0123456789ABCDEF		@@ trap 前 hmon 的 async mask
	.equ	P1, 0x0000000000000001		@@ 第一次 escape 写的 rc11（整字反例）
	.equ	P2, 0x8000000000000001		@@ 第二次 escape 写的 rc11（整字反例）

@@ `cg5` 帧记录（rc0–rc5、rc8–rc11）落到 `\base + \off`
.macro	__REC_FRAME cfx, base, off
	cfx2rd	\cfx, cg5, rc0, rd5
	st.o	rd5, [\base, \off + 0x00]
	cfx2rd	\cfx, cg5, rc1, rd5
	st.o	rd5, [\base, \off + 0x08]
	cfx2rd	\cfx, cg5, rc2, rd5
	st.o	rd5, [\base, \off + 0x10]
	cfx2rd	\cfx, cg5, rc3, rd5
	st.o	rd5, [\base, \off + 0x18]
	cfx2rd	\cfx, cg5, rc4, rd5
	st.o	rd5, [\base, \off + 0x20]
	cfx2rd	\cfx, cg5, rc5, rd5
	st.o	rd5, [\base, \off + 0x28]
	cfx2rd	\cfx, cg5, rc8, rd5
	st.o	rd5, [\base, \off + 0x30]
	cfx2rd	\cfx, cg5, rc9, rd5
	st.o	rd5, [\base, \off + 0x38]
	cfx2rd	\cfx, cg5, rc10, rd5
	st.o	rd5, [\base, \off + 0x40]
	cfx2rd	\cfx, cg5, rc11, rd5
	st.o	rd5, [\base, \off + 0x48]
.endm

@@ 写当前 cfx 的出口意图：run mode = hypv、cfx = power、ip = \ip、mask = \mask
.macro	__PREP_ESC cfx, ip, mask
	set.rd	rd5, 0x0000000000000003
	cfx2rc	\cfx, cg5, rc8, rd5
	set.rd	rd5, 0x000000000000003F
	cfx2rc	\cfx, cg5, rc9, rd5
	set.rd	rd5, \ip
	cfx2rc	\cfx, cg5, rc10, rd5
	set.rd	rd5, \mask
	cfx2rc	\cfx, cg5, rc11, rd5
.endm

	__TEST_BEGIN
	set.rb	rb20, HMON_BASE
	set.rb	rb4, SSCR
	set.rb	rb5, PSCR
	@@ 任何意外异常先落到固件 hmon 的返回槽（fail-fast；随后会被还原）
	set.rb	rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]

	@@ ---- hmon 的 async mask = P0，trap 入口记录 rc3 取该快照 ----
	set.rd	rd5, P0
	cfx2rc	cfx_hmon, cg15, rc3, rd5
	@@ hmon 的 escape_num 基线（启动链已 escape 过一次）
	cfx2rd	cfx_hmon, cg4, rc5, rd5
	st.o	rd5, [rb4, 0x58]
	@@ 自建 hmon 入口（hypv 向量）与 cfx_power 入口（CFXESC 承接）
	set.rd	rd5, hmon_entry
	cfx2rc	cfx_hmon, cg3, rc15, rd5
	set.rd	rd5, power_entry
	cfx2rc	cfx_power, cg3, rc15, rd5
	@@ 写 power 的出口意图（case 2 用）：hypv / power / case2_land / P2
	__PREP_ESC cfx_power, case2_land, P2

	@@ ==== case 1：同步 trap 的入口记录 + 正常返回四元组 + rc11 整字 + escape_num ====
__case1:
case1_trap:
	trap	cfx_hmon, 0
case1_land:
	@@ 1-6 入口记录（硬件在 trap 时写）
	__CHECK_MEM   1, SSCR, 0x00, 3
	__CHECK_MEM   2, SSCR, 0x08, 0x000000000000003F
	set.rb	rb21, SSCR
	ld.o	rd5, [rb21, 0x10]
	ld.o	rd6, [rb21, 0x40]
	__VERIFY_EQ_RD   3, rd5, rd6			@@ rc2 (prev ip) == rc10 (escape ip 副本)
	set.rd	rd6, 1
	__CHECK_RD   3, rd6, 1
	__CHECK_MEM   4, SSCR, 0x18, P0
	__CHECK_MEM   5, SSCR, 0x20, 0x0000000000000001
	__CHECK_MEM   6, SSCR, 0x28, 0x7F0C0000
	@@ 7-10 出口意图（进入时由入口记录复制）
	__CHECK_MEM   7, SSCR, 0x30, 3
	__CHECK_MEM   8, SSCR, 0x38, 0x000000000000003F
	set.rb	rb21, SSCR
	ld.o	rd5, [rb21, 0x48]
	ld.o	rd6, [rb21, 0x18]
	__VERIFY_EQ_RD   9, rd5, rd6			@@ rc11 (意图) == rc3 (入口 mask 副本)
	set.rd	rd6, 1
	__CHECK_RD   9, rd6, 1
	__CHECK_MEM  10, SSCR, 0x48, P0
	@@ 11 rc11 整字写入目标模式 monitor（hypv → hmon）：读回恰为 P1（增量写会残留 1）
	cfx2rd	cfx_hmon, cg15, rc3, rd5
	__CHECK_RD  11, rd5, P1
	@@ 12 escape_num = 基线 + 1
	cfx2rd	cfx_hmon, cg4, rc5, rd5
	ld.o	rd6, [rb4, 0x58]
	add.si	rd6, 1
	__VERIFY_EQ_RD  12, rd5, rd6			@@ escape_num = 基线 + 1
	set.rd	rd6, 1
	__CHECK_RD  12, rd6, 1
	@@ 13-16 同步进入只写目标 cfx（hmon）的帧：power 的入口记录保持复位 0
	cfx2rd	cfx_power, cg5, rc0, rd5
	__CHECK_RD  13, rd5, 0
	cfx2rd	cfx_power, cg5, rc1, rd5
	__CHECK_RD  14, rd5, 0
	cfx2rd	cfx_power, cg5, rc2, rd5
	__CHECK_RD  15, rd5, 0
	cfx2rd	cfx_power, cg5, rc3, rd5
	__CHECK_RD  16, rd5, 0

	@@ ==== case 2：cfx_power 自己的正常返回（四元组成功即证明 cfx=power、mode=hypv、ip 精确） ====
__case2:
	escape	cfx_power
case2_land:
	@@ 17 目标模式 monitor（hypv → hmon）的 cg15 rc3 = P2 整字
	cfx2rd	cfx_hmon, cg15, rc3, rd5
	__CHECK_RD  17, rd5, P2
	@@ 18 cfx_power 的 escape_num = 0 + 1
	cfx2rd	cfx_power, cg4, rc5, rd5
	__CHECK_RD  18, rd5, 1
	@@ 19 escape 不消费/不清 hmon 的入口记录（仍是 case 1 的 prev mode = hypv）
	cfx2rd	cfx_hmon, cg5, rc0, rd5
	__CHECK_RD  19, rd5, 3

	@@ ==== case 3：cfxha != 当前 cfx ⇒ 当前 cfx(power) 的 CFXESC ====
__case3:
	set.rd	rd5, 3
	st.o	rd5, [rb5, 0x50]
	__PREP_ESC cfx_power, case2_land, P2
case3_bad:
	escape	cfx_hmon
	__EXIT	20				@@ 未报错 ⇒ 判红
case3_land:
	__CHECK_MEM  20, PSCR, 0x20, 0x0000000000000008	@@ CFXESC
	__CHECK_MEM  21, PSCR, 0x28, 0x7E0C0000		@@ 指令编码
	set.rb	rb21, PSCR
	ld.o	rd5, [rb21, 0x10]
	ld.o	rd6, [rb21, 0x40]
	__VERIFY_EQ_RD  22, rd5, rd6			@@ prev ip == rc10（进入时复制）
	set.rd	rd6, 1
	__CHECK_RD  22, rd6, 1
	cfx2rd	cfx_hmon, cg15, rc3, rd5
	__CHECK_RD  23, rd5, P2				@@ 切换任何状态前报错 ⇒ mask 不变
	__CHECK_MEM  24, PSCR, 0x38, 0x000000000000003F	@@ CFXESC 进入 power 帧：prev cfx = power

	@@ ==== case 4：目标 cfx 未实现（rc9 = 6）⇒ 当前 cfx 的 CFXESC，且不改任何状态 ====
__case4:
	set.rd	rd5, 4
	st.o	rd5, [rb5, 0x50]
	__PREP_ESC cfx_power, case2_land, P2
	set.rd	rd5, 0x0000000000000006		@@ 目标 cfx = 6（reserved/未实现）
	cfx2rc	cfx_power, cg5, rc9, rd5
case4_bad:
	escape	cfx_power
	__EXIT	25				@@ 未报错 ⇒ 判红
case4_land:
	__CHECK_MEM  25, PSCR, 0x20, 0x0000000000000008	@@ CFXESC
	__CHECK_MEM  26, PSCR, 0x28, 0x7EFC0000		@@ 指令编码（cfx63、imms18=0）
	set.rb	rb21, PSCR
	ld.o	rd5, [rb21, 0x10]
	ld.o	rd6, [rb21, 0x40]
	__VERIFY_EQ_RD  27, rd5, rd6			@@ prev ip == rc10（进入时复制）
	set.rd	rd6, 1
	__CHECK_RD  27, rd6, 1
	cfx2rd	cfx_hmon, cg15, rc3, rd5
	__CHECK_RD  28, rd5, P2				@@ 目标非法 ⇒ rc11 不落地

	@@ ---- 收尾：还原平台固件向量（故障链经固件路由）与 hmon mask ----
	set.rd	rd5, HMON_BASE
	cfx2rc	cfx_hmon, cg3, rc15, rd5
	set.rd	rd5, BOOTROM_BASE
	cfx2rc	cfx_power, cg3, rc15, rd5
	set.rd	rd5, 0x7FFFFFFFFFFFFFF7
	cfx2rc	cfx_hmon, cg15, rc3, rd5
	__TEST_END

	@@ ---- 自建 hmon 入口：记录同步 trap 的入口/出口字段，改 rc10/rc11 后正常返回 ----
	.balign	4
hmon_entry:
	set.rb	rb2, SSCR
	__REC_FRAME cfx_hmon, rb2, 0x00
	set.rd	rd5, case1_land
	cfx2rc	cfx_hmon, cg5, rc10, rd5
	set.rd	rd5, P1
	cfx2rc	cfx_hmon, cg5, rc11, rd5
	escape	cfx_hmon
	swym	0

	@@ ---- cfx_power 入口：CFXESC 承接（case 3/4），记录后按 phase 返回对应落点 ----
	.balign	4
power_entry:
	set.rb	rb2, PSCR
	__REC_FRAME cfx_power, rb2, 0x00
	ld.o	rd6, [rb2, 0x50]
	set.rd	rd5, 3
	br.eq	{rd6, rd5}?, [rb0, __p_land3]
	set.rd	rd5, 4
	br.eq	{rd6, rd5}?, [rb0, __p_land4]
	__EXIT	29				@@ 非预期进入 ⇒ 判红
__p_land3:
	set.rd	rd5, case3_land
	jump	[rb0, __p_escape]
__p_land4:
	set.rd	rd5, case4_land
__p_escape:
	cfx2rc	cfx_power, cg5, rc10, rd5
	escape	cfx_power
	swym	0

	@@ ---- 故障例：入口记录 rc0–rc3 只读（写 ⇒ CFXREG）----
	TEST_FAULT_ENC  29, CFXREG, 0x7B0C5005, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  30, CFXREG, 0x7B0C5045, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  31, CFXREG, 0x7B0C5085, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  32, CFXREG, 0x7B0C50C5, rb12, TEST_DATA, rd11, 0

	@@ ---- 故障例：imms18（SBZ）非 0 / reserved cfxha ⇒ ILLI ----
	TEST_FAULT_ENC  33, ILLI, 0x7EFC0004, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  34, ILLI, 0x7EFC0002, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  35, ILLI, 0x7EFFFFFF, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  36, ILLI, 0x7E180000, rb12, TEST_DATA, rd11, 0
	TEST_FAULT_ENC  37, ILLI, 0x7EF40000, rb12, TEST_DATA, rd11, 0

	__TEST_SECTIONS
