@@ tests/shared/asm/perm_hypv.inc — hypv 两轴放行（`m17-chipyard-001`，`DIV-07` 关闭）
@@
@@ 背景：RTL 的固定 BootROM（`spec/Kaiwu §6.2`）把 `+loadmem` 的测试体以
@@ **cfx_power(63) / hypv** 交付；`DIV-07` 关闭后 hypv 行也判权，目标 cfx 的
@@ hypv 源掩码复位只允许源 `cfx_hmon`(3)（`spec/DADAO-13 §1` 的 `…F7`）⇒ 测试体
@@ 对任何其它 cfx 的 `cfx2rd`/`cfx2rc`/`trap` 都会被拒（`CFXPERM`）。
@@
@@ 测试侧准备 = **在 monitor 里放行**（`m16-testcases-017` 的 env 权限准备同一思路，
@@ 只是 body 从 cfx_power 起步）：测试体把 `cfx_hmon` 的 hypv 向量暂指向本文件的
@@ 放行块、`switch_run_mode` 写 hypv，再 `trap cfx_hmon`；放行块以 **cfx_hmon**
@@ 运行（源 cfx = 3 ⇒ 所有 cfx 的复位掩码都允许），把目标 cfx 的 hypv 四类掩码
@@ 写成 0（允许所有源）、`cg3 rc12` 写成 8（bit3 恒 1，其余放行），最后 `escape`
@@ 回 `trap + 4`（恢复 cfx_power / hypv），测试体继续。
@@
@@ 用法：
@@
@@     PERM_MON_OPEN perm_mon          ; 入口处；cfx_ptw 等尚未被访问
@@     ...测试体...
@@   .balign 4
@@   perm_mon:
@@     PERM_OPEN       cfx_ptw         ; 目标 cfx 的 hypv 四类掩码
@@     PERM_OPEN_DELEG cfx_hart        ; 有 commonRows 的 cfx 再放行 cg_reg_deleg
@@     PERM_MON_CLOSE                  ; 必须最后一块
@@
@@ 约束：
@@   * 调用点不得持有 `rd28`/`rd29`/`rb28`（放行块只用它们；这三只在
@@     `tests/arch` 与 `tools/chipyard` 的全量探针里均未被占用）；
@@   * `perm_mon` 必须与测试体同镜像、4 字节对齐（`cg3 rc15` 写丢低 2 位）；
@@   * `PERM_OPEN_DELEG` 只用于实现 `cg3 rc12` 的 cfx（`umon/smon/hmon/hart/
@@     pmem/time`）；`ptw/cache/power` 的 `cg3 rc12` 是 `CFXREG`；
@@   * 放行块把固件入口（= `HMON_BASE`，`spec/DADAO-13 §1` 复位值）写回
@@     `cfx_hmon cg3 rc15`，测试体随后的同步异常仍走平台固件。
@@
@@ 依据：`spec/DADAO-12 §3.1`–`§3.4`（四类同步来源 mask，位索引 = 源 cfx，
@@ 0 = 允许、1 = 屏蔽）、`§5.2`（`trap` 的 `<mode>_cfxtrap` 判定）、
@@ `.tao/contracts/contract-see.md §3`。

@@ 平台固件的 hmon 入口 = hmon SRAM 起始（`spec/DADAO-13 §1` 的 `cg3 rc15` 复位值；
@@   Kaiwu-Tiny 与 Kaiwu-Vast 同址）。用到的探针若已从 `machine-*.inc` 得到该符号，
@@   这里的 `.ifndef` 不改变它。
.ifndef	HMON_BASE
.equ	HMON_BASE, 0x0fff00000000
.endif

@@ 进入 monitor 并在出口处把固件入口写回。
.macro	PERM_MON_OPEN lab
	set.rb	rb28, \lab
	rb2rd	rd28, rb28, 1
	cfx2rc	cfx_hmon, cg3, rc15, rd28		@@ hypv 向量 = 放行块（原 rc10）
	set.rd	rd28, 3
	cfx2rc	cfx_hmon, cg3, rc14, rd28		@@ switch_run_mode = hypv（原 rc8）
	trap	cfx_hmon, 0				@@ 进 monitor（源 cfx = 3）
	@@ 回到 cfx_power / hypv：恢复平台固件的 hmon 入口
	set.rb	rb28, HMON_BASE
	rb2rd	rd28, rb28, 1
	cfx2rc	cfx_hmon, cg3, rc15, rd28
.endm

@@ 目标 cfx 的四类 hypv 源掩码 = 0（允许所有源）。
.macro	PERM_OPEN ha
	set.rd	rd29, 0
	cfx2rc	\ha, cg3, rc0, rd29			@@ cfxtrap
	cfx2rc	\ha, cg3, rc1, rd29			@@ cfxmem
	cfx2rc	\ha, cg3, rc2, rd29			@@ cfxreg
	cfx2rc	\ha, cg3, rc3, rd29			@@ cfxexe
.endm

@@ 同上，再放行 `cg3 rc12`（supv 访问该 cfx 的任一 cg 的前提）。
.macro	PERM_OPEN_DELEG ha
	PERM_OPEN \ha
	set.rd	rd29, 8
	cfx2rc	\ha, cg3, rc12, rd29
.endm

@@ 放行结束：回到 `trap + 4`。新 escape 没有 +4 偏移：返回点取 `cg5 rc10`
@@ （入口时 = trap 地址），软件先加 4 再 `escape cfx_hmon`。
.macro	PERM_MON_CLOSE
	cfx2rd	cfx_hmon, cg5, rc10, rd29
	add.si	rd29, 4
	cfx2rc	cfx_hmon, cg5, rc10, rd29
	escape	cfx_hmon
	swym	0
.endm
