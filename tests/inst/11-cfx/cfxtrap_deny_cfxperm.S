@@ cfxtrap_deny_cfxperm.S — cfxtrap 来源掩码拒绝 ⇒ CFXPERM（`spec/DADAO-12 §3.4/§4.1`）
@@ 大类：11-cfx（核芯功能扩展权限轴）；册目录 `tests/inst/11-cfx/`
@@ 语义：`cg3 rc0`（hypv `cfxtrap` 来源 mask）限制 `trap`/`escape` 的控制转移到该 cfx；
@@   位索引 = 源 cfx（= 当前 `inner_cfx_code`）、0=允许、1=屏蔽，访问自身 cfx 只绕过 cfx 轴。
@@   拒绝 ⇒ 当前运行模式 monitor（hypv ⇒ cfx_hmon）的 `CFXPERM`（cause one-hot `1<<7`）+
@@   扁平位图（ADR-0062 D2/D3）：只置 `CFXPERM`（`1<<7`），`[63:32]` 全 0（旧 `[39]` 已删）；
@@   `cause_info` = **触发指令地址**（与 `excp_cause_ip` 同值，
@@   §4.1 的刻意统一），不是指令编码——本文件与 `cfxreg_deny_cfxperm.S` 是同一口径的两个载体，
@@   `cfxtrap` 一侧的实现早于 `cfxreg`（本任务只为权限轴补齐 `cfxreg`/`cfxexe`），此例作对照。
@@ 载体身份：跨 `cfx2rc`（置位）与 `trap`（被拒）与异常进入，无单一 opcode 身份；
@@   索引 id = `inst-11-cfx-007`（非 id 载体，`check_tests_index.NON_ID_CARRIERS` 登记）。
@@ 前提：应用跑在 `cfx_power(63)`（`spec/Kaiwu §1`）；hmon 的 hypv `cfxtrap` mask 复位值
@@   `0x7FFF_FFFF_FFFF_FFF7`（`spec/DADAO-13 §1`）⇒ bit63 = 0（允许 power），bit3 = 0（自身，恒忽略）。
@@ 链例逐个检查点把实测 8 字节写入结果缓冲并逐字节打印 ⇒ 各方比较的是字节流；
@@   期望值按 `spec/DADAO-13 §1` 与 `spec/DADAO-12 §3.4/§4.1` 内联（不从实测反推）。
@@ 失败点号 = 用例序号 = `SYS_EXIT` 参数（`spec/Kaiwu §7.1`）；本例的拒绝路径落点用 4 号。
@@ 探针：拒绝后的 cause_id / cause_ip / cause_info 由**平台固件** hmon 的「保存-跳转」写进
@@   hmon SRAM 0xE0/0xE8/0xF0（`spec/Kaiwu §6.2`），本文件的落点块（`.org 0x880`）逐项核对；
@@   触发指令地址用 `aip.si` 运行期派生（期望不写死 `.text` 偏移）。
@@ 不可恢复说明：bit63 置 1 后，任何从 cfx_power 到 cfx_hmon 的 `cfx2rd`/`cfx2rc` 都被拒 ⇒
@@   本例不再回写 mask（无需恢复：其后只走 semihosting 短路 `trap cfx0`，不经 cfx 掩码）。
@@ 平台口径（`m17-qemu-001`/`m17-gem5-001`/`m17-chipyard-001` 后三方一致）：IDL/QEMU/
@@   gem5/RTL 都在全运行模式判权（含 hypv，`trap` 目标查 `<mode>_cfxtrap`），
@@   `CFXPERM` 的 `cause_info` 都是触发指令地址（`ISS-469` 已修；`DIV-07` 已关闭）。

	.include "tests/inst/macros/inst_test.inc"

	__TEST_BEGIN
	set.rb rb20, HMON_BASE
	set.rb rb21, TEST_PAD
	st.o	rb21, [rb20, 0xF8]              @@ 任何意外异常 ⇒ 标准故障落点（fail-fast）

	@@ ---- semantic：hmon 的 hypv cfxtrap mask 复位值（bit63=0 / bit3=0，`spec/DADAO-13 §1`）----
	cfx2rd	cfx_hmon, cg3, rc0, rd5
	__CHECK_RD   1, rd5, 0x7FFFFFFFFFFFFFF7

	@@ ---- semantic：RW —— 清 bit0（源 cfx0）后读回，再写回复位值并读回 ----
	set.rd	rd5, 0x7FFFFFFFFFFFFFF6
	cfx2rc	cfx_hmon, cg3, rc0, rd5
	cfx2rd	cfx_hmon, cg3, rc0, rd6
	__CHECK_RD   2, rd6, 0x7FFFFFFFFFFFFFF6
	set.rd	rd5, 0x7FFFFFFFFFFFFFF7
	cfx2rc	cfx_hmon, cg3, rc0, rd5
	cfx2rd	cfx_hmon, cg3, rc0, rd6
	__CHECK_RD   3, rd6, 0x7FFFFFFFFFFFFFF7

	@@ ---- 拒绝路径：hmon 的 hypv cfxtrap mask 的 bit63（源 cfx = 应用所在的 cfx_power 63）
	@@   置 1（此刻 bit63=0 ⇒ 本指令本身仍被允许），再 trap cfx_hmon ⇒ CFXPERM ----
	set.rd	rd5, 0xFFFFFFFFFFFFFFF7
	cfx2rc	cfx_hmon, cg3, rc0, rd5
	set.rb rb21, (ENTRY + 0x880)
	st.o	rb21, [rb20, 0xF8]              @@ 落点 = 本文件的权限检查块
	aip.si	rb25, 0                        @@ rb25 = 本指令地址；+8 = 下面 trap 的地址
	add.si	rb25, 8
	trap	cfx_hmon, 0x10                  @@ 被 cfxtrap 来源掩码拒绝 ⇒ CFXPERM
	__EXIT	4                              @@ 未拒绝 ⇒ 判红（检查点 4）

	@@ ---- 拒绝路径落点：cause_id = 1<<7（`CFXPERM`，无子原因）；cause_ip = cause_info = 指令地址 ----
	.org	0x880
	__VERIFY_MEM 4, HMON_BASE, 0xE0, 0x0000000000000080
	rb2rd	{rd22:rd22}, {rb25:rb25}            @@ 运行期派生的触发指令地址
	set.rb rb21, (HMON_BASE + 0xE8)
	ld.o	rd21, [rb21, 0]
	br.eq	{rd22, rd21}?, [rb0, __cfxtrap_ip]
	__EXIT	4                              @@ cause_ip ≠ 指令地址 ⇒ 判红
__cfxtrap_ip:
	set.rb rb21, (HMON_BASE + 0xF0)
	ld.o	rd21, [rb21, 0]
	br.eq	{rd22, rd21}?, [rb0, __cfxtrap_done]
	__EXIT	4                              @@ cause_info ≠ 指令地址（如写成指令编码）⇒ 判红
__cfxtrap_done:
	__TEST_END

	__TEST_SECTIONS
