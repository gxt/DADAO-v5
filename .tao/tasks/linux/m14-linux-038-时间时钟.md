# m14-linux-038: 时间/时钟 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：2 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：已验证

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/kernel/time*`、`delay`、`clocksource`/`clockevent` 的 arch 侧、`include/asm/{delay,timex,clocksource}.h`，以及 `arch/riscv/kernel/time*`、`arch/arm64/kernel/time*` 的对应实现（为 `m14-linux-026` 提供对照）。

## 要做

逐个 hook / 机制判定属于哪一类，并给证据：

1. **缺失 hook**：上游有、我们没有（后果：功能不可用，或被迫走旁路）；
2. **语义不符**：有但行为不同（返回码 / 副作用 / 加锁 / 顺序）；
3. **旁路 vs 通用**：我们自造实现，上游走通用 `mm/`、`kernel/` 路径；
4. **Kconfig 缺口**：缺 `select` / `depends on`，导致本可复用的通用代码没编进来（`m14-linux-025` 的 `CLONE_BACKWARDS` 就是此类）。

**每条格式**：`arch/dadao/<file>:<line>` ↔ `arch/riscv/<file>:<line>`（必要时补 `arch/arm64`）/ 影响面 / 优先级（**P0** 阻塞当前在跑任务；**P1** 影响正确性；**P2** 仅形态差异）。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行），**每条带两侧 `文件:行号`**；
2. **覆盖现场派生**：列清「检查了哪些 hook / 机制」及条数（不写死），并说明如何枚举得到（命令或脚本口径）；
3. **抽查 5 条**：用 `sed -n '<行>p'` 贴出两侧原文，证明行号真实——**不许凭记忆**；
4. **不改任何代码**：`git status -uall` 只列本任务书；不占写者锁、不重建、不跑仿真。

## 盘点结论

**读源**：`components/linux` 源树 HEAD `c5f411a3a1`（`dadao: linux patch series`，父 `7b20d05fd` = 基线 `7.2.10`），工作树干净（`git status --porcelain -uall` 0 行，只读、未 apply/reset/make）。现行 `.config`（构建树只读）：`GENERIC_CLOCKEVENTS=y` / `HZ=100` / `HZ_PERIODIC=y`；`NO_HZ_IDLE`、`HIGH_RES_TIMERS`、`GENERIC_SCHED_CLOCK`、`HAVE_GENERIC_VDSO` 均未设。

### ① 缺失 hook

①-1 **P0 · clocksource 未注册**（`cfx_time` 可读却没有 `struct clocksource`）：`arch/dadao/kernel/time.c:148`（`dadao_time_freq`）、`:159`（`dadao_read_time`）↔ `drivers/clocksource/timer-riscv.c:95`（`riscv_clocksource`）、`:177`（`clocksource_register_hz`）；arm64 `drivers/clocksource/arm_arch_timer.c:150`、`:945`。影响：`timekeeper` 只剩 `jiffies` 后备源（`kernel/time/jiffies.c:32`，rating 1、`CLOCKSOURCE_MASK(32)`；`timekeeping_init` 经 `clocksource_default_clock()` 取它，`kernel/time/timekeeping.c:2064`）⇒ 分辨率 1/HZ = 10 ms。

①-2 **P0 · clockevent 未注册**（无 `struct clock_event_device`、无 `clockevents_config_and_register`）：`arch/dadao/include/asm/time.h:67`（注释明写 "deliberately absent"）、`arch/dadao/kernel/time.c:93`（start/stop 两个自造函数）↔ `timer-riscv.c:72`（`DEFINE_PER_CPU(...)`）、`:121`；arm64 `arm_arch_timer.c:674`、`:712`。影响见 ③-1（整条 tick 链不跑）。

①-3 **P1 · `sched_clock` 缺**：`arch/dadao` 无 `sched_clock_register`（0 命中）↔ `timer-riscv.c:183`、`arm_arch_timer.c:951`。退化为 `kernel/sched/clock.c:65` 的 jiffies 弱默认（`NSEC_PER_SEC/HZ` = 10 ms 粒度）；实测旁证 `arch/dadao/kernel/k5_syscall_selftest.c:202`（注释块 196–204，实测 10000 次 `schedule()` 不换手）。

①-4 **P1 · 周期计数面缺**（`cycles_t`/`get_cycles`/`get_cycles64`/`random_get_entropy`/`read_current_timer`）：`arch/dadao/include/asm/timex.h:1`（全文件仅 `CLOCK_TICK_RATE`，且未 include `asm-generic/timex.h`）↔ `arch/riscv/include/asm/timex.h:51`、`:84`；arm64 `arch/arm64/include/asm/timex.h:14`。影响：`random_get_entropy()` 落 jiffies 回退（`include/linux/timex.h:82`）⇒ CRNG 早期熵弱；`__delay` 无法按周期计数（见 ②-2）。

①-5 **P2 · `tick_setup_hrtimer_broadcast()` / `timer_probe()` / `pv_time_init()` 缺**：`arch/dadao/kernel/time.c:324`（`time_init` 只有 freq 校验、`period`、`lpj_fine`、打印）↔ `arch/riscv/kernel/time.c:46`、`:48`、`:50`；arm64 `arch/arm64/kernel/time.c:60`、`:62`、`:71`。无 OF/ACPI、单核、无半虚拟化 ⇒ **建议不整改**（纯形态差异）。

### ② 语义不符

②-1 **P0 · tick 记账只有 jiffies 自增 + `sched_tick()`**：`arch/dadao/kernel/time.c:238`（裸 `jiffies_64 += 1`）、`:260`（只调 `sched_tick`）↔ `kernel/time/tick-common.c:95`（`do_timer(1)`）、`:98`（`update_wall_time()`）、`:101`（`update_process_times()`）。`update_process_times()` 的职责见 `kernel/time/timer.c:2468`（`account_process_tick`/`run_local_timers`/`rcu_sched_clock_irq`/`irq_work_tick`/`sched_tick`/`run_posix_cpu_timers`）。影响：墙钟不推进（`update_wall_time()` 全树只在 tick 框架内调用：`tick-common.c:98`、`tick-sched.c:149`；`tick-legacy.c:33` 因 `LEGACY_TIMER_TICK=n` 不编译）、定时器轮不跑（`mod_timer` 到期回调永不触发）、用户/系统时间不记账、RCU 不看 tick。**注**：`update_process_times()` 无对外头文件声明（仅 `kernel/time/timekeeping.h:27` 内部），arch 侧不可达 ⇒ 只能注册 clockevent 让 `tick_handle_periodic` 代劳（`tick-common.c:326` → `tick_setup_periodic`）。

②-2 **P2 · `__delay` 按循环计数而非周期计数，且 `lpj_fine` 维度错配**：`arch/dadao/lib/delay.c:17`（`while (loops--) cpu_relax()`，17–18 行）、`:26`（`xloops * loops_per_jiffy * HZ` 放大）、`arch/dadao/kernel/time.c:342`（`lpj_fine = freq / HZ`，把周期率当循环率）↔ `arch/riscv/lib/delay.c:78`（`get_cycles()` 计时）、`:87`（`lpj_fine * UDELAY_MULT`）；arm64 `arch/arm64/lib/delay.c:41`。影响：`udelay/ndelay` 实际时长 ≈ 名义 × 每循环指令数（约 3–4×）；`init/calibrate.c:294` 把 `freq/HZ` 当循环数 ⇒ BogoMIPS 虚报 2000。

②-3 **P1 · 异步入口不经 IRQ 子系统**（无 `irq_enter_rcu()`/`set_irq_regs()`）：`arch/dadao/kernel/async_trap.S:55`（直接 `call dadao_async_handler`）、`arch/dadao/kernel/time.c:299` ↔ `arch/riscv/kernel/traps.c:424`–`:432`（`handle_riscv_irq`：`:428` `irq_enter_rcu`、`:429` `set_irq_regs`、`:432` `irq_exit_rcu`）；arm64 `arch/arm64/kernel/entry-common.c:43`（`irqentry_enter_from_kernel_mode`）。影响：`in_hardirq()/in_interrupt()` 为假、`irq_work_tick` 不跑、`user_mode(get_irq_regs())` 取不到（`tick-common.c:101` 靠它记 user/sys 时间）。

②-4 **P2 · jiffies 写入无 `jiffies_lock`/`jiffies_seq`**：`arch/dadao/kernel/time.c:238` ↔ `kernel/time/tick-common.c:89`（`raw_spin_lock` + `write_seqcount_begin`）。单核 64 位读不撕裂，NO_HZ 上线后必须补。

②-5 **P2 · tick 状态是全局量而非 per-CPU**：`arch/dadao/kernel/time.c:72`（`dadao_period`）、`:75`（`dadao_ticks`）、`:83`（`dadao_tick_on`）↔ `timer-riscv.c:72`（`DEFINE_PER_CPU`）、`:110`（`per_cpu_ptr`）。`cfx_hart` 本身是 per-hart，SMP 一开即错；今天 `NR_CPUS` 锁 1–1（`arch/dadao/Kconfig:54`）属潜伏。

②-6 **P2 · 帧内冗余关中断**：`arch/dadao/kernel/time.c:226`（`local_irq_save`，注释自陈"cheap enough"）↔ `timer-riscv.c:148`（handler 不做屏蔽，靠 `riscv_clock_event_stop()`）。语义无害。

### ③ 旁路 vs 通用

③-1 **P0 · tick 由探针启动，不由框架启动**：`arch/dadao/kernel/k4_switch_selftest.c:955`（唯一 `dadao_clockevent_start()` 调用点）↔ `timer-riscv.c:108`（cpuhp → `clockevents_config_and_register` → `tick_setup_periodic`）。现行 `.config`（futex 探针镜像）`CONFIG_DADAO_K4_SWITCH_SELFTEST=n` ⇒ **该镜像从不启动 tick**；任何未开该探针的镜像同样无 tick（`dadao_tick_on` 初值 0，`arch/dadao/kernel/time.c:83`）⇒ `schedule_timeout/msleep/nanosleep` 不唤醒，`clock_gettime` 停在开机值。

③-2 **P1 · 中断投递旁路 `irqchip`/`irqdomain`**：`arch/dadao/kernel/irq.c:87`（`init_IRQ` 只写向量 + 开两轴，无 `irqchip_init`）、`arch/dadao/kernel/time.c:308`（cause 硬编码判定）↔ `arch/riscv/kernel/irq.c:152`（`irqchip_init()`）、`timer-riscv.c:171`（`irq_create_mapping`）、`:185`（`request_percpu_irq`）。影响：无 `irq_desc`/`/proc/interrupts` 行/`request_irq` 能力，timer 只能由异步入口特判。

③-3 **P2 · `cfx_time` 直读派生 delay 与 `lpj_fine`（不经 clocksource）**：`arch/dadao/kernel/time.c:159`、`:342` ↔ 两参考实现的读时间一律经 clocksource `.read`（`timer-riscv.c:100`、`arm_arch_timer.c:154`）。026 接线后此项自然消失。

### ④ Kconfig 缺口

④-1 **P0 · `GENERIC_SCHED_CLOCK` 未选 ⇒ `sched_clock_register()` 是空桩**：`arch/dadao/Kconfig:11`–`:22`（该 12 行区间内 7 条 `select` 均无此条）↔ `arch/riscv/Kconfig:125`、`arch/arm64/Kconfig:141`；桩见 `include/linux/sched_clock.h:46`（`static inline ... { }`）。**026 若照 riscv 写法调用会静默无效**（无编译告警）——这是本盘点对 026 最直接的一条。

④-2 **P1 · `HIGH_RES_TIMERS` 未开**：`arch/dadao/configs/defconfig:15`（只 `HZ_100`）；`kernel/time/Kconfig:199` 无 default。影响：`hrtimer_resolution = LOW_RES_NSEC = TICK_NSEC`（`include/linux/hrtimer.h:140`、`include/vdso/ktime.h:13`）= 10 ms ⇒ `clock_getres` 报 10 ms（`kernel/time/posix-timers.c:275`），nanosleep/timerfd/poll 精度 10 ms。**待 026 注册 oneshot clockevent 后再开**。

④-3 **P2 · `HAVE_GENERIC_VDSO`/`GENERIC_GETTIMEOFDAY`/`ARCH_HAS_VDSO_ARCH_DATA` 未选**：`arch/dadao/Kconfig:11`–`:22` ↔ `arch/riscv/Kconfig:57`、`:113`、`:174`；`arch/arm64/Kconfig:143`、`:232`。影响：`clock_gettime` 恒走 syscall；**syscall 面本身不缺**（`kernel/time/posix-stubs.c:60` 或 `posix-timers.c:1142`；ABI 路由已登记 `arch/dadao/kernel/syscall_argmask.c:122`–`:125`、`:154`、`:207`）。

④-4 **P2 · `ARCH_HAS_TICK_BROADCAST`/`GENERIC_CLOCKEVENTS_BROADCAST`/`ARCH_HAS_READ_CURRENT_TIMER` 未选**：`arch/dadao/Kconfig:11`–`:22` ↔ `arch/riscv/Kconfig:55`、`:108`、`arch/riscv/include/asm/timex.h:84`；`arch/arm64/Kconfig:59`、`:125`。单核 + `lpj_fine` 已跳过 `calibrate_delay_direct` ⇒ 今天无害；SMP 前须补 broadcast。

④-5 **P2 · `CLOCK_TICK_RATE` 是 legacy 残留**：`arch/dadao/include/asm/timex.h:9`；无 `LEGACY_TIMER_TICK`（`kernel/time/Kconfig:68`）且全树无使用者 ⇒ 可删（建议并入 `m14-linux-040` 处置）。

### 对 `m14-linux-026` 的直接输入

- **必须做**：①-1 + ①-2 + ②-1 + ③-1（注册 clocksource/clockevent，tick 交 `tick_handle_periodic`）；④-1（`select GENERIC_SCHED_CLOCK` 后 `sched_clock_register`）——否则 `sched_clock` 静默为 jiffies。
- **可延后**：①-4（`get_cycles` 与 delay 改造同批）、②-3（IRQ 子系统化，需独立中断任务）、②-5（SMP 任务）、④-2（hrtimer，026 落地后再开）、④-3（vDSO）。
- **不要动**：①-5（无 OF/ACPI、单核，`timer_probe`/broadcast 均不适用）。

## 覆盖现场派生

**枚举口径**：hook 名单取自通用时间子系统对 arch 的接口面（`include/linux/{clocksource,clockchips,sched_clock,timex,delay,hrtimer}.h` 的 `extern` 与桩分支）外加两侧参考实现的注册面（`arch/*/kernel/time.c`、`arch/*/lib/delay.c`、`drivers/clocksource/{timer-riscv,arm_arch_timer}.c`）。脚本口径：把该名单写死为 shell 变量，对三侧（`arch/dadao` / `arch/riscv`+`timer-riscv.c` / `arch/arm64`+`arm_arch_timer.c`）逐符号 `grep -rl --include='*.c' --include='*.h' --include='*.S' --include='Kconfig*'`，统计**命中文件数**并现场打印合计；再人工过滤注释命中（见下）。

**现场结果**：`hooks=34`，`dadao_present=8`、`riscv_present=24`、`arm64_present=20`。dadao 的 8 处命中里 3 处仅在注释（`do_timer`/`update_wall_time`/`update_process_times` 均出现在 `arch/dadao/kernel/time.c` 说明性文字），**有效实现面 5 项**：`time_init`、`__delay`、`__udelay`、`__const_udelay`、`lpj_fine`。

**机制清单（34）**：`time_init` / `get_cycles` / `cycles_t` / `get_cycles64` / `read_current_timer` / `random_get_entropy` / `sched_clock_register` / `clocksource_register` / `clockevents_config_and_register` / `timer_probe` / `tick_setup_hrtimer_broadcast` / `pv_time_init` / `__delay` / `__udelay` / `__const_udelay` / `lpj_fine` / `ARCH_HAS_READ_CURRENT_TIMER` / `GENERIC_SCHED_CLOCK` / `HAVE_GENERIC_VDSO` / `GENERIC_GETTIMEOFDAY` / `ARCH_HAS_VDSO_ARCH_DATA` / `HIGH_RES_TIMERS` / `NO_HZ_IDLE` / `TICK_ONESHOT` / `irq_enter_rcu` / `set_irq_regs` / `request_percpu_irq` / `irq_create_mapping` / `do_timer` / `update_wall_time` / `tick_periodic` / `update_process_times` / `CPUHP_AP_` / `jiffies_lock`。

**再按覆盖面复核的 5 个横切面**（不计入上述 34）：① clocksource `read`/`rating`/`mask`/`flags` 结构字段（①-1 已引三侧行号）；② clockevent `set_next_event`/`set_state_*`/`cpumask`/`irq` 字段（①-2）；③ tick 记账职责分解（②-1，按 `update_process_times` 函数体逐项对照）；④ `timespec64` 转换与 syscall 路由（④-3，正向确认不缺）；⑤ 现行 `.config` 的 6 个时间相关符号取值（见"读源"行，取自构建树只读副本，未触发任何构建）。

## 抽查 5 条（`sed -n '<行>p'` 原文）

1. ②-1：`sed -n '238p' arch/dadao/kernel/time.c` → `	jiffies_64 += 1;`；`sed -n '95p' kernel/time/tick-common.c` → `		do_timer(1);`
2. ②-2：`sed -n '17p' arch/dadao/lib/delay.c` → `	while (loops--)`；`sed -n '78p' arch/riscv/lib/delay.c` → `	u64 t0 = get_cycles();`
3. ①-4：`sed -n '9p' arch/dadao/include/asm/timex.h` → `#define CLOCK_TICK_RATE		1000000`；`sed -n '53p' arch/riscv/include/asm/timex.h` → `	return csr_read(CSR_TIME);`
4. ③-1：`sed -n '955p' arch/dadao/kernel/k4_switch_selftest.c` → `	dadao_clockevent_start();`；`sed -n '121p' drivers/clocksource/timer-riscv.c` → `	clockevents_config_and_register(ce, riscv_timebase, 100, ULONG_MAX);`
5. ②-3：`sed -n '55p' arch/dadao/kernel/async_trap.S` → `	call	[rb5, rd0, 0]			/* returns only on a handled tick */`；`sed -n '428p' arch/riscv/kernel/traps.c` → `	irq_enter_rcu();`

## 完成区

**测试结果**：只读盘点，无构建/仿真；第 1 轮复核判 Needs Revision（6 处行号/数字）已全部修正并逐处回贴自证；`run.sh` rc=0、`run.sh --inject` rc=0。
**修改文件**：`.tao/tasks/linux/m14-linux-038-时间时钟.md`（仅此 1 文件；未改源码、未动只读源树与构建树）。

**验收结果**：①「盘点结论」56 行（≤80）、19 条各带两侧 `文件:行号`；②覆盖现场派生 `hooks=34`（有效 5／`riscv=24`／`arm64=20`）；③抽查 5 条两侧 `sed` 原文；④读源 HEAD `c5f411a3a1`（工作树干净，未 apply/reset/make）、本 worktree `git status -uall` 仅本任务书。

**新发现/坑**：① `sched_clock_register()` 在 `CONFIG_GENERIC_SCHED_CLOCK=n` 时是空桩（`include/linux/sched_clock.h:46`），照 riscv 移植不报错、不生效；② `lpj_fine` 必须与 `__delay` 的计数单位一致，混用不报错但延迟偏长 3–4×、BogoMIPS 虚报；③ 现行 `.config` 里 `K4_SWITCH_SELFTEST=n` ⇒ 该镜像从不启动 tick（唯一启动点是探针 `k4_switch_selftest.c:955`）；④ `update_process_times()` 仅 `kernel/time/timekeeping.h` 内部声明，arch 侧不可达。

**返工 1（reviewer Needs Revision；只改数字与指向，结论条目数/分级/覆盖段不动）**

1. ②-2 错：`lib/delay.c:15`、riscv `:76`／`:85` 三处都是**函数签名行** ⇒ 改 `:17`／`:78`／`:87`。自证：`sed -n '17p' arch/dadao/lib/delay.c` → `	while (loops--)`；`sed -n '78p' arch/riscv/lib/delay.c` → `	u64 t0 = get_cycles();`；`sed -n '87p' arch/riscv/lib/delay.c` → `	u64 ucycles = (u64)usecs * lpj_fine * UDELAY_MULT;`
2. ②-1 错：`:259` 实为 `if (dadao_tick_on) {` ⇒ 改 `:260`。自证：`sed -n '260p' arch/dadao/kernel/time.c` → `		sched_tick();`
3. ①-3 错：`:197` 是注释块首行 ⇒ 改 `:202` 并补注「注释块 196–204」。自证：`sed -n '202p' arch/dadao/kernel/k5_syscall_selftest.c` → * across 10000 `schedule()` calls.  Blocking is different: a task waiting on a
4. ④-1 错：「`select` 块 12 条」⇒ 改「该 12 行区间内 7 条 `select` 均无此条」。自证：`sed -n '11,22p' arch/dadao/Kconfig | wc -l` → `12`；`… | grep -c 'select '` → `7`；`sed -n '22p'` → `	select CLONE_BACKWARDS`
5. 额外自查（同类）：③-1 原写 `kernel/time.c:83`（该路径不存在）⇒ 改 `arch/dadao/kernel/time.c:83`。自证：`sed -n '83p'` → `static int dadao_tick_on;`
6. 额外自查（同类）：②-3 原引 `:424`–`:433`，端点 `:433` 仅 `}`（弱锚点）⇒ 改 `:424`–`:432` 并点名 `:428`／`:429`／`:432`。自证：`sed -n '428p;429p;432p' arch/riscv/kernel/traps.c` → `	irq_enter_rcu();` / `	old_regs = set_irq_regs(regs);` / `	irq_exit_rcu();`
7. 全文行号自查：把结论/覆盖/抽查段全部引用抽成 **97 条冻结锚点表**逐条回读源行（97/97 命中），并核「任务书每条引用 ⊆ 冻结表」（99 条引用 0 未核对）；本次 3 处错误即由该组判红。
8. 重跑：`sh run.sh` **rc=0**（**仅未提交态成立**；提交后 E3/E4 假红 rc=1，见「返工 2」）（14 项全 PASS：A 97/97、B 0 未核对、C1 56 行、C2 19、C3 5/5/9、D 34/8/24/20、E 源树 HEAD `c5f411a3a1`+干净、本仓仅 1 文件）；`sh run.sh --inject` **rc=0**（`:17`→`:15` 注入 ⇒ B 组红 rc=1；`hooks=34`→`35` ⇒ D3 红 rc=1；`cp` 备份 + `md5sum -c` 还原后回绿 rc=0）。

**返工 2（第 2 轮 reviewer：证据脚本在提交后假 FAIL）**

- **原因**：E3/E4 原断言「工作树恰 1 个**未提交**改动」；architect 提交后工作树干净 ⇒ E3/E4 假红（`期望=1 实际=0`）、`--inject` 因「正例不绿即退出」根本没跑反例 —— 违反「提交后仍须回绿（禁裸断言『变更存在』）」。
- **修法**（照 036 做法，改 E 组为 3 条）：E3 `git -c core.quotepath=false diff --name-only master...HEAD` ⊆ 本任务书（可空，防合并后同类假红）；E4 `git show --name-only --format= HEAD` 非空且仅本任务书（**提交态主判据**）；E5 `git status --porcelain -uall` ⊆ 本任务书（**0/1 都过**，多余文件才红）。`--inject` 增第 3 路「工作树探针」。
- **两态 rc**：未提交态（当前，工作树 1 改）rc=**0**；提交态（临时 clone 的干净树，HEAD 不变）rc=**0**。
- **注入证据**：引用注入（`lib/delay.c:17`→`:15`）⇒ `[FAIL] B` rc=**1**；计数注入（`hooks=34`→`35`）⇒ `[FAIL] D3` rc=**1**；工作树探针（`.tao/tasks/linux/__probe_038.keep`）⇒ `[FAIL] E5` 实际 2 行 rc=**1** → 删探针 rc=**0**。
- **重跑**：`sh run.sh` rc=**0**；`sh run.sh --inject` rc=**0**（`RESULT: PASS（未提交态绿 / 提交态绿 / 三路反例红 / 还原回绿）`）；`md5sum -c` 还原 OK。**未动**：6 处行号、97 条锚点表、A/B/C/D 四组判据、结论与覆盖段。

**遗留问题**：无（只读盘点；整改与否待用户裁定）。处置归口：①-1/①-2/②-1/③-1/④-1 → `m14-linux-026`；①-4/②-2 → delay 改造（未立项）；②-3/③-2 → 中断子系统任务（未立项）；④-3/④-5 → `m14-linux-040`；④-2 → 026 落地后再开。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

**审查范围**：结论段 19 条 + 覆盖段 + 抽查段，逐条把 `文件:行号` 用 `sed -n` 回读核对（共回读 dadao 26 处、riscv 12 处、arm64 12 处、通用 20 处），不看记忆。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `arch/dadao/Kconfig:9` 只是 `config DADAO`，非 select 行 | ✅已修 | 三处改为 `arch/dadao/Kconfig:11`–`:22`（12 条 select 区间） | `sed -n '11p;22p'` = `select 64BIT` / `select CLONE_BACKWARDS` |
| `arch/dadao/Kconfig:51` 是 `config NR_CPUS`，range 在 54 | ✅已修 | 改 `:54` | `sed -n '54p'` = `range 1 1` |
| `tick-common.c:88` 是 `if (tick_do_timer_cpu == cpu)`，`do_timer(1)` 在 95 | ✅已修 | 改 `:95` | `sed -n '95p'` = `do_timer(1);` |
| `syscall_argmask.c:112/115/266` 行号错（实为 99/102/空行） | ✅已修 | 改 `:122`–`:125`、`:154`、`:207`（112/113/114/115/169/266） | `sed -n '122,125p;207p'` 四行 clock_* + clock_adjtime |
| ①-1 只说「只剩 jiffies」，未给「谁把它选成当前源」 | ✅已修 | 补 `kernel/time/timekeeping.c:2064`（`clocksource_default_clock()`） | `sed -n '2064p'` = `clock = clocksource_default_clock();` |
| ④-2 说 `clock_getres` 报 10 ms，但未给调用链 | ✅已修 | 补 `kernel/time/posix-timers.c:275`（`posix_get_hrtimer_res`） | `sed -n '275p'` = `tp->tv_nsec = hrtimer_resolution;` |
| ③-1 原写「生产镜像无 tick」，但证据来自 futex 探针镜像配置 | ✅已修 | 改为「现行 `.config`（futex 镜像）该探针=n ⇒ 该镜像不启动 tick；未开该探针的镜像同样无 tick（`dadao_tick_on` 初值 0）」，并补 `kernel/time.c:83` | `sed -n '83p'` = `static int dadao_tick_on;` |
| ②-1 称 `update_wall_time()` 只在 tick 框架调用 | ✅已修 | 补注 `tick-legacy.c:33` 因 `LEGACY_TIMER_TICK=n` 不编译 | `kernel/time/Kconfig:68` = `config LEGACY_TIMER_TICK`；`.config` 无 `LEGACY_TIMER_TICK` |
| ④-5 称 `CLOCK_TICK_RATE` 全树无使用者 | ⏸延后（保留结论） | 未改 | 依据：`grep -rn CLOCK_TICK_RATE arch/ kernel/ drivers/ include/ lib/` 仅命中 arch 头文件；建议 040 落地时再用 `make` 侧验证一次 |
| 抽查用表格承载 `sed` 原文，窄终端会折行 | ✅已修 | 改为 5 条列表（每条两侧），内容不变 | 见「抽查 5 条」段 |

**判决**：所有实质 finding 已修或已标注保留依据；无未修项 ⇒ 状态可置 `待验收`。

### 第 2 轮 engineer 自审（返工后，自主逐行）

**做法**：把结论/覆盖/抽查段全部 `path:line` 引用抽成 97 条冻结锚点表（`cites.tsv`），逐条回读源行 + 反向核「引用 ⊆ 表」，再对 6 处修正逐处 `sed` 回贴。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ②-2 三处括号内容不在所引行（与抽查段自相矛盾） | ✅已修 | `:15`→`:17`、`:76`→`:78`、`:85`→`:87` | `sed -n '17p' lib/delay.c`=`	while (loops--)`；`:78p`=`u64 t0 = get_cycles();`；`:87p`=`… * lpj_fine * UDELAY_MULT;` |
| ②-1 `sched_tick()` 在 260 而非 259 | ✅已修 | `:259`→`:260` | `sed -n '260p'`=`		sched_tick();` |
| ①-3 「10000」在 202 而非 197 | ✅已修 | `:197`→`:202` | `sed -n '202p'`=`* across 10000 …` |
| ④-1 「12 条 select」实为 12 行/7 条 | ✅已修 | 改「该 12 行区间内 7 条 `select`」 | `sed -n '11,22p' … | wc -l`=12、`grep -c 'select '`=7 |
| ③-1 引 `kernel/time.c:83`（路径不存在） | ✅已修 | 补 `arch/dadao/` 前缀 | `sed -n '83p'`=`static int dadao_tick_on;` |
| ②-3 端点 `:433` 仅 `}`（弱锚点） | ✅已修 | 改 `:424`–`:432`，点名 `:428`/`:429`/`:432` | 三行分别为 `irq_enter_rcu();`/`set_irq_regs(regs);`/`irq_exit_rcu();` |

**判决**：无未修项；`sh run.sh` rc=0、`sh run.sh --inject` rc=0 ⇒ 状态保持 `待验收`。**（更正：该 rc 只在未提交态成立；architect 提交后 E3/E4 变假红 rc=1 —— 见完成区「返工 2」，E 组已改为两态都绿的判据。）**

### 第 1 轮 reviewer 验收（小改档；判决只依据本人重跑，不采信完成区）

**重跑记录**：源树命令在运行期 linux 检出内执行、只写相对路径（运行期路径不入册）；贴出时略去行首 tab；每条均带本人真实输出。

**① 抽查 10 条（P0×4 / P1×3 / P2×3），两侧 `sed -n '<行>p'` 原文**
- ①-1 P0：`arch/dadao/kernel/time.c:148`→`unsigned long dadao_time_freq(void)`、`:159`→`unsigned long dadao_read_time(void)` ↔ `drivers/clocksource/timer-riscv.c:95`→`static struct clocksource riscv_clocksource = {`、`:177`→`error = clocksource_register_hz(&riscv_clocksource, riscv_timebase);`、arm64 `arm_arch_timer.c:150`→`static struct clocksource clocksource_counter = {`、`:945`→`clocksource_register_hz(&clocksource_counter, arch_timer_rate);` ⇒ ✅ 相符
- ①-2 P0：`arch/dadao/include/asm/time.h:67` → "* What is deliberately absent: no `struct clock_event_device`, no" ↔ `timer-riscv.c:72`→`static DEFINE_PER_CPU(struct clock_event_device, riscv_clock_event) = {`、`:121`→`clockevents_config_and_register(ce, riscv_timebase, 100, ULONG_MAX);` ⇒ ✅
- ②-1 P0：`arch/dadao/kernel/time.c:238`→`jiffies_64 += 1;`、`:259`→`if (dadao_tick_on) {`（结论称「只调 sched_tick」，`sched_tick();` 实在 **260**）↔ `kernel/time/tick-common.c:95`→`do_timer(1);`、`:98`→`update_wall_time();`、`:101`→`update_process_times(user_mode(get_irq_regs()));`、`kernel/time/timer.c:2468`→`void update_process_times(int user_tick)`、`timekeeping.h:27`→`extern void update_process_times(int user);` ⇒ ⚠️ dadao 侧行号偏 1，其余相符
- ③-1 P0：`arch/dadao/kernel/k4_switch_selftest.c:955`→`dadao_clockevent_start();`、`arch/dadao/kernel/time.c:83`→`static int dadao_tick_on;` ↔ `timer-riscv.c:108`→`static int riscv_timer_starting_cpu(unsigned int cpu)` ⇒ ✅（cpuhp 起点锚）
- ④-1 P0：`arch/dadao/Kconfig:11`→`select 64BIT`、`:22`→`select CLONE_BACKWARDS`（11–22 实为 12 行 / **7 条 select**，`grep GENERIC_SCHED_CLOCK arch/dadao/Kconfig` rc=1）↔ `arch/riscv/Kconfig:125`→`select GENERIC_SCHED_CLOCK`、`include/linux/sched_clock.h:46`→`static inline void sched_clock_register(u64 (*read)(void), int bits,` ⇒ ✅ 行号相符，计数「12 条 select」有误
- ①-4 P1：`arch/dadao/include/asm/timex.h:1`→`/* SPDX-License-Identifier: GPL-2.0 */`（全文 11 行确无 get_cycles，:1 为文件锚）↔ `arch/riscv/include/asm/timex.h:51`→`static inline cycles_t get_cycles(void)`、`:84`→`#define ARCH_HAS_READ_CURRENT_TIMER`、arm64 `arch/arm64/include/asm/timex.h:14`→`#define get_cycles() arch_timer_read_counter()` ⇒ ✅
- ②-3 P1：`arch/dadao/kernel/async_trap.S:55`→`call [rb5, rd0, 0] /* returns only on a handled tick */` ↔ `arch/riscv/kernel/traps.c:424`→`static void noinstr handle_riscv_irq(struct pt_regs *regs)`（428/429/432 = irq_enter_rcu/set_irq_regs/irq_exit_rcu，`:433`→`}`）、arm64 `entry-common.c:43`→`state = irqentry_enter_from_kernel_mode(regs);` ⇒ ✅（`grep -rn irq_enter_rcu arch/dadao/` rc=1 零命中）
- ④-2 P1：`arch/dadao/configs/defconfig:15`→`CONFIG_HZ_100=y`（全文无 HIGH_RES/NO_HZ）↔ `kernel/time/Kconfig:199`→`config HIGH_RES_TIMERS`（无 default）、`include/linux/hrtimer.h:140`→`#define hrtimer_resolution (unsigned int)LOW_RES_NSEC`、`include/vdso/ktime.h:13`→`#define LOW_RES_NSEC TICK_NSEC`、`kernel/time/posix-timers.c:275`→`tp->tv_nsec = hrtimer_resolution;` ⇒ ✅
- ②-2 P2：`arch/dadao/lib/delay.c:15`→`void __delay(unsigned long loops)`，结论括注 `while (loops--) cpu_relax()` 实在 **17–18**（本任务书抽查段自引 `:17`）；`arch/riscv/lib/delay.c:76`→`void __delay(unsigned long cycles)`，括注 `get_cycles()` 实在 **78**（抽查段自引 `:78`）；`:85`→`void udelay(unsigned long usecs)`，括注 `lpj_fine * UDELAY_MULT` 实在 **87** ⇒ ❌ 三处括注内容不在所引行，且与抽查段自相矛盾
- ③-3 P2：`arch/dadao/kernel/time.c:159`→`unsigned long dadao_read_time(void)`、`:342`→`lpj_fine = freq / HZ;` ↔ `timer-riscv.c:100`→`.read = riscv_clocksource_rdtime,`、`arm_arch_timer.c:154`→`.read = arch_counter_read,` ⇒ ✅
- ④-5 P2：`arch/dadao/include/asm/timex.h:9`→`#define CLOCK_TICK_RATE 1000000` ↔ `kernel/time/Kconfig:68`→`config LEGACY_TIMER_TICK` ⇒ ✅
- 附 ①-3 P1：`arch/dadao/kernel/k5_syscall_selftest.c:197` → "* This port has no `sched_clock()` of its own yet (the guest clock source is"，结论括注「10000 次 schedule() 不换手」的 `10000` 实在 **202**（同注释块 196–204）⇒ ⚠️ 偏 5 行

**② 覆盖数现场重算**（34 符号清单 × 三侧 `grep -rl --include`，本人脚本、非采信）：`hooks=34 dadao_present=8 riscv_present=24 arm64_present=20`，与任务书逐字一致；dadao 8 = time_init / __delay / __udelay / __const_udelay / lpj_fine + do_timer / update_wall_time / update_process_times（后 3 条仅 time.c 注释行）⇒ 有效 5 项一致 ✅

**③ 不改代码**：`git show --stat HEAD` 与 `git diff master...HEAD --stat` 均只列任务书 1 文件（+113/-2）；源树 `git log --oneline -1` = `c5f411a3a dadao: linux patch series`、`git status --porcelain -uall` 0 行、今日 08:00 后改动文件 0 个、`*.o`/`*.cmd` 0 个、`git reflog` 顶条为 `commit:`（其后无 reset/apply）⇒ 未被 apply_series/reset/make 触碰 ✅

**④ 门控**：`make check-knowledge-refs` rc=0（PASS：扫描 193 文件、0 具体运行期路径引用、0 悬空互指）；`make check-tasks` rc=0（扫描 149 份任务书，①漏收尾 1 = 本任务，报告型不阻断）

**⑤ 结论段自检**：56 行（≤80）；19 条（①5/②6/③3/④5）；P0 5 / P1 5 / P2 9 现场计数一致 ✅；术语口径（bank = 寄存器组）无误译、全文无具体运行期路径 ✅

**约束核验**：不改代码 ✅；覆盖现场派生 ✅；不提交 git ✅；P0 五条与 `m14-linux-026` 目标逐条对应（注册 clocksource/clockevent、event_handler 记账、tick 启动点、`select GENERIC_SCHED_CLOCK` 防空桩）⇒ 分级合理 ✅（备注：026 状态为「待开始」，与「阻塞当前在跑任务」字面略异，属措辞）。

**判决：Needs Revision**——行号是本任务唯一硬判据（验收 #1/#3），以下对不上：
1) ②-2 三处括注不在所引行：`arch/dadao/lib/delay.c:15`→**17**、`arch/riscv/lib/delay.c:76`→**78**、`arch/riscv/lib/delay.c:85`→**87**（且 `:15` 与本任务书抽查段的 `:17` 自相矛盾）；
2) ②-1 `arch/dadao/kernel/time.c:259`→**260**（或改措辞为「259 分支内只调 sched_tick」）；
3) ①-3 `arch/dadao/kernel/k5_syscall_selftest.c:197`→**202**（或 196 注释块起）；
4) ④-1「select 块 12 条」→「12 行 / 7 条 select」（`:11`–`:22` 行号本身正确，`GENERIC_SCHED_CLOCK` 确无）。
修法：只改本任务书这 6 处数字，改后逐处 `sed -n` 回贴自证；结论其余内容、覆盖段、抽查段无需动。

### 第 2 轮 reviewer 验收（小改档；判决只依据本人重跑）

**① 6 处修正 + 2 处额外，逐处 `sed -n` 真实输出**（源树内相对路径；略行首 tab）
- ②-2 `arch/dadao/lib/delay.c:17`→`while (loops--)`、`:18`→`cpu_relax();`；`arch/riscv/lib/delay.c:78`→`u64 t0 = get_cycles();`、`:87`→`u64 ucycles = (u64)usecs * lpj_fine * UDELAY_MULT;` ⇒ ✅
- ②-1 `arch/dadao/kernel/time.c:260`→`sched_tick();` ⇒ ✅
- ①-3 `arch/dadao/kernel/k5_syscall_selftest.c:202`→`* across 10000 \`schedule()\` calls. …`，`sed -n '196p;204p'` = ` *` / ` * child completes it at its last trap…`（注释块 196–204）⇒ ✅
- ④-1 `sed -n '11,22p' arch/dadao/Kconfig | wc -l`=**12**、`grep -c 'select '`=**7**、`:11`=`select 64BIT`、`:22`=`select CLONE_BACKWARDS`、`grep -c GENERIC_SCHED_CLOCK`=**0** ⇒ ✅
- 额外 ③-1 `arch/dadao/kernel/time.c:83`→`static int dadao_tick_on;`（原 `kernel/time.c:83` 路径不存在）⇒ ✅
- 额外 ②-3 `arch/riscv/kernel/traps.c:424`→`static void noinstr handle_riscv_irq(struct pt_regs *regs)`、`:428`→`irq_enter_rcu();`、`:429`→`old_regs = set_irq_regs(regs);`、`:432`→`irq_exit_rcu();` ⇒ ✅

**② 我另随机抽 6 条（不在上列 8 处内）**：`arch/dadao/kernel/time.c:93`→`void dadao_clockevent_start(void)`（stop 在 `:99`）、`:75`→`static volatile unsigned int dadao_ticks;`、`:226`→`local_irq_save(flags);`（上一行注释自陈 `cheap enough`）、`arch/dadao/kernel/irq.c:87`→`void __init init_IRQ(void)`（`grep irqchip_init arch/dadao/` rc=1）、`arch/riscv/kernel/time.c:50`→`pv_time_init();`（arm64 `:71` 同）、`arch/riscv/Kconfig:108`→`select GENERIC_CLOCKEVENTS_BROADCAST if SMP` ⇒ 全部相符，无同类偏移 ✅

**③ 冻结锚点表判据实测**（本人注入，`cp`+md5 还原，真实任务书 md5 前后均 `c8bb92ac…`）：
- 表外行号：`arch/dadao/lib/delay.c:17`→`:15` ⇒ `[FAIL] B 引用全部经核对 | 实际=1 条: ['arch/dadao/lib/delay.c:15'] rc=1` ⇒ **真能抓「写了不在表内的行号」** ✅
- 表内但语义错：`delay.c:17`→`:26` ⇒ `[PASS] B …0 条未核对 rc=0` ⇒ 该判据只管表内/表外，**表内错位仍靠人审**（边界，不阻断；建议脚本注释写明）
- 表 97 行；`:15/:76/:85/:259/:197` 已不在表内（grep rc=1）；A 组 97/97 命中

**④ 结论基本面未动**：与返工前逐段 diff —— 盘点结论段 73→73 行，差异**恰为 6 处**（①-3/②-1/②-2/②-3/③-1/④-1）；覆盖段、抽查段 diff **空**；19 条、P0/P1/P2=5/5/9、`hooks=34 / dadao=8 / riscv=24 / arm64=20` 经我自己的 34 符号 × 三侧脚本现场重算一致 ✅

**⑤ 不改代码**：`git show --name-only HEAD` 与 `git diff master...HEAD --stat` 均仅本任务书 1 文件；源树 `git log --oneline -1`=`c5f411a3a dadao: linux patch series`、`git status --porcelain -uall` 0 行 ✅

**⑥ 门控**：`make check-knowledge-refs` rc=0（PASS）、`make check-tasks` rc=0（扫描 149 份，①漏收尾 1 = 本任务，报告型）✅

**判决：Needs Revision** —— 仅证据脚本 E 组与完成区 rc 声明（行号本身全对）：
1) 本人重跑运行期证据目录内的 `run.sh` **rc=1**（两次一致）：`[FAIL] E3 本 worktree 改动文件数 | 期望=1 | 实际=0 | rc=1`、`[FAIL] E4 改动文件是本任务书 | 实际=<无> | rc=1` ⇒ `RESULT: FAIL`；`run.sh --inject` 同样 **rc=1**，且因「正例不绿即 exit 1」**反例自检根本没跑**。根因：E3/E4 断言「工作树恰 1 个未提交改动」，返工已由 architect 提交为 HEAD（工作树干净）⇒ 提交后必假 FAIL，违反「提交后仍须回绿（禁裸断言『变更存在』）」。
2) 完成区与自审段写 `sh run.sh` rc=0、`--inject` rc=0，与我重跑的 rc=1 不符 ⇒ 按「结论与真实退出码逐条对齐」须更正。
修法：E3/E4 改为「`git diff master...HEAD --name-only` 仅本任务书 且 `git status --porcelain -uall` 为空或仅含本任务书」（0/1 都过）；改后 `run.sh` 与 `run.sh --inject` 均须 rc=0 并回填真实 rc。**6 处行号 + 2 处额外修正、97 条锚点表与 B 判据本身均正确，无需再动。**

### 第 3 轮 reviewer 验收（小改档；判决只依据本人重跑）

**① E 组三条读脚本核对**（证据检查器 L111/L118/L124）：
- E3 `git -c core.quotepath=false diff --name-only master...HEAD`，断言 `set(files3) <= {本任务书}` ⇒ **可空**（合并进 master 后为空也不红）✅
- E4 `git -c core.quotepath=false show --name-only --format= HEAD`，断言 `len>0 且 set == {本任务书}` ⇒ **非空且仅本任务书**（提交态主判据，不裸断言「变更存在」）✅
- E5 `git -c core.quotepath=false status --porcelain -uall`，断言 `paths5 <= {本任务书}` ⇒ **0/1 都过、出现其它文件才红** ✅
- 三处均带 `-c core.quotepath=false` ✅，**必要性实测**：提交态临时 clone 内 `core.quotepath` 未设（默认 true），`git show --name-only --format= HEAD` → `".tao/tasks/linux/m14-linux-038-\346\227\266\351\227\264\346\227\266\351\222\237.md"`（转义 ⇒ 必假红），带 `-c` 后为原名

**② 提交态正例（第 2 轮唯一阻断，已复现为绿）**：`sh run.sh` **rc=0** → `[PASS] E3 … 1 个: ['…时间时钟.md']`、`[PASS] E4 … 1 个`、`[PASS] E5 … 实际=0 行: []`、`ALL PASS (源树 HEAD c5f411a3a1)`；`sh run.sh --inject` **rc=0** → `RESULT: PASS（未提交态绿 / 提交态绿 / 三路反例红 / 还原回绿）`

**③ 我自己复现 2 路反例**（`cp`+md5 还原，未用 reset/checkout）：引用注入 `arch/dadao/lib/delay.c:17`→`:15` ⇒ `[FAIL] B 引用全部经核对 | 实际=1 条: ['arch/dadao/lib/delay.c:15'] | rc=1`；工作树探针 `.tao/tasks/linux/__probe_r3.keep` ⇒ `[FAIL] E5 … 实际=1 行: ['…__probe_r3.keep'] | rc=1` → 删探针 ⇒ `[PASS] E5 … 实际=0 行 | rc=0`、`ALL PASS`；探针残留 0 个，真实任务书 md5 前后均 `0ca31e86…`

**④ 结论与锚点未动**：盘点结论段与返工前逐段 diff **恰 6 处**（12 行 = 6 对）、56 行、19 条、P0/P1/P2=5/5/9；覆盖段与抽查段 diff **空**，`hooks=34 / dadao_present=8 / riscv=24 / arm64=20`；`cites.tsv` md5 = `c95f085c…` ✅

**⑤ 更正标注已加且属实（不删历史）**：第 1 轮自审判决后补「（更正：该 rc 只在未提交态成立；architect 提交后 E3/E4 变假红 rc=1 —— 见完成区『返工 2』…）」；返工 1 第 8 条补「**仅未提交态成立**；提交后 E3/E4 假红 rc=1，见『返工 2』」——与我第 2 轮实测 rc=1 一致 ✅

**⑥ 不改代码**：审前 `git status --porcelain -uall` 0 行、`git show --name-only HEAD` 与 `git diff master...HEAD --name-only` 均仅本任务书；源树 `c5f411a3a dadao: linux patch series`、status 0 行、今日改动 0 文件、`*.o` 0、探针 0 ✅

**⑦ 门控**：`make check-knowledge-refs` rc=0（PASS，0 具体运行期路径引用、0 悬空）；`make check-tasks` rc=0（扫描 149 份，①漏收尾 1 = 本任务，报告型）✅

**判决：Accepted** —— 第 2 轮唯一阻断（提交态 E3/E4 假红）已修，且由我在 HEAD 已提交、工作树干净状态下复现为 `run.sh` rc=0；三路反例红、两态正例绿、还原回绿均经我本人注入验证；6 处行号、97 条锚点表、覆盖数与结论段未动；无新问题。

**⑧ 写后复验**：本记录写入后（工作树 1 改 = 本任务书）`sh run.sh` rc=**0**，`[PASS] E5 … 实际=1 行: ['…时间时钟.md']`（0/1 两分支均已实测 PASS）；`make check-knowledge-refs` rc=**0**；`git status --porcelain -uall` 仅本任务书 1 行、探针 0 个、未提交 git。
