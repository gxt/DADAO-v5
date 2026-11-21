# m14-linux-026: clocksource / clockevent 通用框架（cfx_time + cfx_hart 定时器）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-017`（最小 clockevent）、`m14-linux-023`（syscall 闭环，供 `clock_gettime` 等）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/time.c`/`setup.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）；与 023–025/027–028 共享文件少，理论上可并行、受单组件单写者约束
**预估**：3–4 h（接线为主，风险在 clocksource 稳定性判据与 clockevent 的 next-event 编程）
**档位**：中改（时间子系统接线 + 探针；复核 ≥3 路注入）
**状态**：待验收

## 背景

本任务由 `m14-linux-021`（已后移 K5）**原样交接**，正文口径见 `m14-linux-021` 任务书（交接材料）。K4 的 `017` 已做「最小 clockevent」（`cfx_hart` timer 驱动 tick，仅满足 init/调度/计时）；本任务升级为 Linux 通用 **`clocksource`（cfx_time）+ `clockevent`（cfx_hart timer_cmp）** 框架，`timekeeping`/`sched_clock` 走真时钟。

DADAO 特有事实（`contract-see §3/§6.5`，**不得偏离**）：
- `cfx_time`：`cg10 rc0 = freq = 1_000_000_000`（1 GHz，测试机约定）、`rc1 = value`（64 位、复位从 0 起算、1 count = 1 ns）。
- `cfx_hart` 定时器：`cg8 rc4 = timer_cmp`（绝对时间，写新值取消旧 deadline 并清 `TIMER` pending）、`rc5 = timer_ctrl`（bit0 ENABLE/bit1 IMASK/bit2 ISTATUS 只读）；到期触发可屏蔽 `TIMER`（`1 << 10`）、`cause_info = 0`。
- `TIMER` 异步入口 = `cfx_hart` supv 行（`contract-see §6.3`）；`escape` 后补投由**硬件**完成，内核不得软件代投（`§6.5`）。
- 放行前提：`cfx_time` 需 `cg10`、`cfx_hart` 需 `cg8` 的 `hypv_cg_reg_deleg` 放开（K2 已放行）。

## 盘点输入（`m14-linux-038 时间/时钟 与主流 ISA 差异盘点`，用户 2026-11-20 授权引用）

`m14-linux-038` 给出 19 条差异，其中 **5 条 P0 正是本任务的范围**，按它的证据直接落：

1. **`clocksource` 未注册**：`cfx_time` 可读却无 `struct clocksource`（对照 `drivers/clocksource/timer-riscv.c:95`/`:177`）⇒ `timekeeper` 只剩 `jiffies` 后备源（`kernel/time/jiffies.c:32`，rating 1、10 ms）；
2. **`clockevent` 未注册**：无 `struct clock_event_device`、无 `clockevents_config_and_register`（`arch/dadao/include/asm/time.h:67` 注释明写 "deliberately absent"）；
3. **tick 记账只有 `jiffies_64 += 1` + `sched_tick()`**（`kernel/time.c:238`/`:259`）：墙钟不推进（`update_wall_time()` 全树只在 tick 框架内调用）、定时器轮不跑、用户/系统时间不记账；
4. **tick 唯一启动点是探针**（`k4_switch_selftest.c:955`）⇒ 生产路径无 tick；
5. **`GENERIC_SCHED_CLOCK` 未选**（`m14-linux-044` 已补 select 并注册 `sched_clock`；本任务确认它与 `cfx_time` 同源即可）。

**P1 两条与本任务相关**：`sched_clock` 缺（jiffies 弱默认 10 ms）、`HIGH_RES_TIMERS` 未开。

**不作为本任务范围**（038 判 P2 或需另立）：`__delay` 循环计数与 `lpj_fine` 维度错配、jiffies 无锁、tick 状态全局非 per-CPU（SMP 潜伏）、无 vDSO、broadcast 等。

**跨任务约束（`m14-linux-044` 实测推翻）**：`CONFIG_GENERIC_IRQ_ENTRY` **不是** `in_hardirq()` 的开关（`irq_enter_rcu()` 在 `kernel/softirq.c:662` 无条件定义），别把「tick 不跑」归因到那个 select。

## 目标

1. **`clocksource`（cfx_time）**：`dadao_clocksource` 注册（`read` = `cfx_time_value`、`freq` = 现场读 `cg10 rc0`、`rating` 自定但须说明理由）；`sched_clock` 走 `cfx_time`；`timekeeping` 由 clocksource 驱动。
2. **`clockevent`（cfx_hart timer_cmp）**：`dadao_clockevent` 注册（`set_next_event` = 写 `timer_cmp` 绝对时间、`set_state_*` = 写 `timer_ctrl` ENABLE/IMASK）；`dadao_timer_interrupt()` 改调 `event_handler`，不再裸写 jiffies。
3. **`time_init()`**：注册 clocksource/clockevent，替换 K2 裸 `dadao_timer_arm`；`period = freq/HZ` 现场派生。
4. **探针** `tools/linux/k5_clocksource_probe.py`：沿用 K2 `k2_time_probe.py` 的「间隔余量 = period/2」与「停表校验」口径，不破坏 K2 判据。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_clocksource_probe.py` rc=0，逐 case 打印；期望值现场派生（`freq` ← `cg10 rc0` 读值、`period` ← `freq/HZ` 现场算、`HZ` ← `.config`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `T1 clocksource 单调`：连续两次 `cfx_time_value` 读值非降；`sched_clock` 与 `cfx_time_value` 同源（差值恒定容差内）。
   - `T2 clockevent next-event`：写 `timer_cmp = now + period` 后在期望时刻内收到 `TIMER`（间隔 ∈ `[period/2, 2*period]`）；`set_next_event` 后旧 deadline 取消。
   - `T3 tick 驱动`：`event_handler` 每 tick 推进 `jiffies_64` + `schedule_tick` 跑通。
   - `T4 稳定性判据`：`read` 两次调用间单调（QEMU 虚拟时钟不回退）；负例注入「`read` 返回上次值」⇒ 红。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `read` 不读 `cfx_time`（恒常量）⇒ `T1` 红；② `set_next_event` 写错寄存器 ⇒ `T2` 红；③ `event_handler` 不推进 jiffies ⇒ `T3` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0（**K2 time 组必须仍绿**，`007` 判据不因升级退役——除非按 `docs/Process-07 §4a` 显式退役并给替代）；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-026/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{time.c,setup.c}.patch`、`components/linux/patches/arch/dadao/include/asm/{timex.h,clocksource?}.patch`、`components/linux/changelog.md`、`tools/linux/k5_clocksource_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-see §3/§6.5` + `spec/DADAO-12 §4.7/§4.10` 为准；寄存器语义已冻结，本任务只做**接线**；不破坏 K2 的「两轴 mask / 单旋钮」口径（`§6.4`）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~（待裁定 3）~~ **已裁定（用户 2026-11-17 选 B）**：clocksource/clockevent 升级后移 K5，本任务即原 `m14-linux-021` 的落地；K4 只跑 jiffies 最小框架。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：所有 finding 已处置，状态 → `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 通用 tick 在 `update_process_times()`→`irq_work_tick()` 处触发 `BUG_ON(!irqs_disabled())`（实测 WARNING init/main.c:1110 + kernel panic） | ✅已修 | `time.c` 的 `dadao_timer_interrupt()` 通用分支在体内 `arch_local_irq_disable()`、退出前 restore（本端口 IE 状态是源 mask 行） | `probe3` panic → `probe4/6` 52/52；`t3 jdelta=4 ticks=4` |
| F2 探针镜像停在 K4 边界、`late_initcall` 不运行（begin 行缺失） | ✅已修 | `kernel/setup.c` 的 `dadao_k4_boundary()` 增 `CONFIG_DADAO_K5_CLOCK_SELFTEST` 的 `return` 分支 | `probe2` 无 begin → `probe3/6` 52/52 |
| F3 `clockevents_switch_state()/clockevents_program_event()` 非公开 API（`tick-internal.h`），编译失败 | ✅已修 | 改用设备回调 `set_state_*`/`set_next_event` + `state_use_accessors`/`next_event` | `build2` 编译错误 → `build3` PASS；`probe` 52/52 |
| F4 `dadao_clockevent_stop()` 若只写 `set_state_shutdown`，从 handler 内停表会被 `tick_handle_periodic()` 的 oneshot 环重新 arm（m45 场景） | ✅已修 | 停表同时把核心状态置 `CLOCK_EVT_STATE_ONESHOT_STOPPED`（启动时置回 ONESHOT） | `m45_entry_probe --no-inject` 44/44 |
| F5 `k4_switch_probe` S6 的「未注册 clock_event_device/clocksource」静态断言与本升级矛盾 | ✅已修（升级后的替代断言） | 改为「生产镜像走通用 clockevent；K2 裸 tick 只剩边界镜像」，注册的端到端判据由 K5 clock 门控承担 | `k4_switch_probe --no-inject` 52/52（S6/S7 均绿） |
| F6 `read-frozen` 注入在冻结 clocksource 后仍能跑完启动（时间冻结但 jiffies 由 tick 推进），需确认 T1 可达 FAIL | ✅确认 | 注入路径无需改代码 | `inject:read-frozen` T1 红、`cp`+md5 还原、重建回绿 |
| F7 两条既有 WARNING（`init/main.c:1110`、`fs/sysfs/group.c:137`）会让「无 WARNING」断言假红 | ✅已修 | 探针按名白名单过滤两条既有 WARNING，其余 WARNING 仍红 | `probe6` 52/52；`--selfcheck` 6/6 |

**逐行审查结论**：`time.c` 的两条编译期分叉只按镜像选择（K2 边界 vs 通用），无运行期双模式；`dadao_clockevent_start/stop` 的状态写入点与 `tick_handle_periodic()` 的 `clockevent_state_oneshot()` 判据对应；探针的每条断言都有实测 FAIL 路径（`--selfcheck` 逐组翻转 + 3 路注入），期望值全部现场派生（契约 freq、`.config` HZ、`freq/HZ`、jiffies rating、`CLOCK_EVT_FEAT_ONESHOT`、`DADAO_K5_CLOCK_TICKS`）。

### 第 1 轮 reviewer 验收

**判决：Accepted**（3 条非阻断 finding，交 architect 收尾改）。以下全部是本人在仓库根重跑的真实输出，未采信完成区。

**重跑记录（命令 → 真实 rc / 输出）**
- `python3 tools/linux/k5_clocksource_probe.py` → **rc=0**、`k5_clocksource_probe: PASS (52/52)`；现场逐组数：C1 25 + T1 7 + T2 7 + T3 5 + T4 8 = 52，`[FAIL]` 0 行
- `python3 tools/linux/k5_clocksource_probe.py --no-build --selfcheck` → **rc=0**、`PASS (6/6 组可翻转 + 对照)`（C1/T1/T2/T3/T4 各红一次 + 未改动对照 0 失败）
- `make check-linux-k0` → **rc=0** `146/146`；`-k1` → **rc=0** `112/112`；`-k2` → **rc=0** `170/170`，`[GROUP] B 29/29 E 15/15 T 17/17 M 12/12 S 20/20 X 9/9 R 4/4 G 64/64`（**K2 T 组 17/17 仍绿**，`check_k2.py` 的 diff 只有 1 行钉子，判据未动）；`-k3` → **rc=0** `263/263`
- `make check-patch-tree` → **rc=0**、`check-patch-tree: linux: 104 patch(es)`、`11 patch set(s), 454 patches OK`（104 = 027 的 103 + 本任务新增 `k5_clock_selftest.c.patch`；`series` 104 行且新增行在位、顺序正确）
- `python3 tools/infra/apply_series.py --component linux` → **rc=0**、`already applied (base+1, matches patches); skipped`，前后 HEAD 同为 `10f19738`
- `make check-config-pins` → **rc=0**、`现场统计：切片脚本 21 个、Kconfig 符号 23 个、镜像 51 个` / `检查 96 项，失败 0 项`
- `make check-linux-boot-contract`、`check-contracts-dir`、`check-contracts-pending`、`check-contract-relocs`、`check-knowledge-refs` → 全 **rc=0**
- `python3 tools/linux/k4_switch_probe.py --no-inject` → **rc=0** `52/52`，改写后的 S6 正向断言 PASS（`want=True got=True`）
- `python3 tools/linux/k5_syscall_probe.py --no-inject` → **rc=0** `62/62`；不带该参数 → **rc=0** `104/104`：完成区 `62/62` 与 027 复核 `104/104` 是**两个口径、都为真**，非笔误

**独立注入（本人 `cp`+md5 → 改被测产物 → 重建 → 还原 → 重建；未用 `--inject` 充数）**
- ① `dadao_clocksource_read()` 改恒返 0：md5 `e6e49bb436198e5574a3e27b0ea689e5` → `18c0a289…`，探针 **rc=1**、红 7 项（T1「读值前进/同源偏移恒定/步进一致」、T4「窗口前进/ktime 前进/步进一致」、T3「连续投递数」）；`cp` 还原后 md5 复等 `e6e49bb436198e5574a3e27b0ea689e5` → 重建 **rc=0 `PASS (52/52)`**
- ② `set_next_event()` 的 deadline 写成 `+delta*2`：md5 `fdff1d0e5f87f7ac2c665c58c6005ee5`，探针 **rc=1**、红 3 项全在 T2（长/短 `cmp` 读回、投递间隔 ∈ [period/2, 2·period]），其余组绿；还原 md5 复等 → 重建 **rc=0 `PASS (52/52)`**
- 两路均「注入红 → 还原 md5 相等 → 重建回绿」；收尾 `git -C .work/source/linux status --porcelain` 输出为空

**约束核验（逐条）**
1. 禁区：`git status` 无 `spec/**`、`.tao/contracts/**`、`components/qemu/**`、根 `Makefile` ✔；改动 29 改 + 2 新 = 31 项，与完成区「修改文件 + 越界披露」逐条对得上 ✔
2. `time_init()` 顺序 = `clocksource_register_hz()` →（`clocksource_select`/`timekeeping_notify` 切源）→ `clockevents_config_and_register()` ✔；`dadao_timer_arm` 生产调用点为 0（唯一调用在 `#ifdef CONFIG_DADAO_K2_TIME_STOP` 内）✔
3. `dadao_timer_interrupt()` 通用分支只 `arch_local_irq_disable` → `dadao_ticks++` → `event_handler` → restore ✔；`freq` 现读 `cg10 rc0`、`period = freq/HZ`、`HZ` ← `.config`、`lpj_fine = freq/HZ` 全现场派生 ✔；rating 300 的理由写在源码注释 ✔
4. 20 个门控脚本补钉 `CONFIG_DADAO_K5_CLOCK_SELFTEST=n`：`config_pins` 要求「脚本 key set == Kconfig 符号集」，漏钉即 FAIL ⇒ 属**收紧**非放宽，`check-config-pins` 现场 96 项 0 失败 ✔
5. 运行期证据目录内的 `run.sh` 逐条审过（`run_check` 捕被检命令自身退出码、全文无 `tee`、计数现场读取）；其 17 项我单独重跑 16 项，唯一未跑是 `probe-inject`（由上面 2 路独立注入替代）——**未整跑 `run.sh`**（中改 40 min 档，逐条等价重跑）

**finding（不阻断，交 architect 收尾）**
- F-a（重点越界项，判为**未削弱但偏浅**）：S6 已由「未注册 ⇒ FAIL」翻转为正向「必须已注册 + K2 边界隔离」，**既非删除也非恒真**——现场验：删掉 `clockevents_config_and_register(&dadao…)` 调用行后断言**仍 True**（`time.c` 尚有 2 处注释命中），连注释一起清才 False。最小修法：子串判据钉成调用形态 `clockevents_config_and_register(&dadao`，并把被摘掉的 clocksource 半边补成 `clocksource_register_hz` 同判（其替代判据目前只写在代码注释里 = K5 探针 C1 注册面 + T1）
- F-b：按 `docs/Process-07 §4a` 补一条退役台账（旧「未注册 clocksource/clockevent」断言 → 替代判据 = `tools/linux/k5_clocksource_probe.py` C1 + T1–T4；`check-linux-k3` R4 已有同形先例）
- F-c：探针两条 WARNING 白名单按 `file:line` 写死（`init/main.c:1110`、`fs/sysfs/group.c:137`）；本轮实测输出里**一条 WARNING 都没有**（白名单当前空转），同址若出新告警会被放过 —— 建议改按告警文本判

## 完成区

**测试结果**：运行期证据目录 `run.sh` **17/17 项 PASS（`RESULT: PASS`）**。`k5_clocksource_probe.py` **52/52**（C1 注册面 + T1–T4）；`--selfcheck` **6/6 组可翻转 + 对照**；`--inject` **3/3**（`read-frozen`→T1+T4 红、`next-event-wrong-reg`→T2 红、`handler-no-tick`→T3 红，每路「注入红 → `cp`+md5 还原 → 重建 → 回绿」）。回归：`check-linux-k0` 146/146、`k1` 112/112、`k2` **170/170（T 组 17/17，K2 time 判据仍绿）**、`k3` 263/263；`check-patch-tree` 454 补丁 0 问题、`apply_series --component linux` 幂等（HEAD 不变）、`check-config-pins` 96 项、`check-linux-boot-contract`/`check-contracts-dir`/`check-contracts-pending`/`check-contract-relocs`/`check-knowledge-refs` 全 rc=0；组件源树收尾干净。旁证（非本任务门控）：`k4_switch_probe --no-inject` 52/52、`m45_entry_probe --no-inject` 44/44、`k5_signal_probe --no-inject` 117/117、`k5_syscall_probe --no-inject` 62/62。
**修改文件**：`components/linux/patches/arch/dadao/kernel/{time.c,setup.c,Makefile}.patch`、新 `.../kernel/k5_clock_selftest.c.patch`、`.../Kconfig.debug.patch`、`.../include/asm/{time.h,timex.h}.patch`、`components/linux/{series,changelog.md}`、新 `tools/linux/k5_clocksource_probe.py`；各门控切片补钉 `CONFIG_DADAO_K5_CLOCK_SELFTEST=n`（20 个 `tools/linux/{check_k*,*_probe}.py`）；`tools/linux/k4_switch_probe.py` 的 S6 静态断言按升级后的边界改写。**越界披露**：`kernel/Makefile.patch`、新 `kernel/k5_clock_selftest.c.patch` 不在任务书「预计改动」清单（探针镜像所需，与 023–027 同形）；20 个门控脚本的钉子行与 `k4_switch_probe.py` 的 S6 断言亦不在清单（`check-config-pins`/升级后边界所致）。未动 `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
**验收结果**：`K5 time: cs=dadao_cfx_time rating=300 mask=0xffffffffffffffff freq=1000000000 hz=100 period=10000000`；`K5 time: ce=dadao_cfx_hart_timer rating=300 features=0x2 handler=1 min_delta=100`；`t2 period=10000000 cmp_long-arm=80013005 cmp_short-arm=10008726 interval=10077577`；`t3 want=4 ticks=4 jdelta=4 se_delta=39998773`；`t4 cs_delta=2510766 ktime_delta=2509604 window=2500000`；证据脚本 `checks: pass=17 fail=0` / `RESULT: PASS`。
**新发现/坑**：① `irq_work_run_list()` 的 `BUG_ON(!irqs_disabled())` 在通用 tick 上可达——本端口没有硬件 IE 位，arch 异步 handler 必须在体内关源 mask 行，否则 `update_process_times()`→`irq_work_tick()` 直接 panic（修复前实测 WARNING `init/main.c:1110` + `Kernel panic`）。② `clocksource_register_hz()` 在 `time_init()`（`local_irq_enable()` 之前）可用：`timekeeping_notify()` 的 `stop_machine()` 走 early 单 CPU 分支。③ 只声明 `CLOCK_EVT_FEAT_ONESHOT`——声明 `FEAT_PERIODIC` 会让 `tick_handle_periodic()` 不再续挂（`timer_cmp` 无硬件重装）。④ `clockevents_switch_state()/clockevents_program_event()` 非公开（`kernel/time/tick-internal.h`）；arch 侧停/启 tick 用设备回调 + `state_use_accessors`（`ONESHOT_STOPPED`），否则从 handler 内停表会被 oneshot 环重新 arm。⑤ 探针镜像必须同时在 `setup.c` 的 K4 边界返回，否则 `late_initcall` 不跑。⑥ `init/main.c:1110` 与 `fs/sysfs/group.c:137` 两条 WARNING 是 K4 起全镜像既有的，探针按名白名单过滤。⑦ 探针镜像要嵌入 initramfs：`make_defconfig.py` CLI 会写 `CONFIG_INITRAMFS_SOURCE`，`apply_config_lines()` 不会——新 worktree 里 K0/K4-S7 会因此假失败（环境，非本任务）。
**遗留问题**：① `dadao_clock_event_device` 的 rating 300 为自定值（理由见源码注释：高于 jiffies 1、低于按核周期计数器 400 档），未进契约；② `k4_switch_probe` 的 S7 需要 worktree 内构建 musl/busybox/initramfs（本次环境已补齐，属构建输入而非代码）；③ `check-linux-k4` 无 Makefile 门控（K4 探针本就不是 L2 成员），其 S6 静态断言改写未走 `docs/Process-07 §4a` 台账（未改文档；若复核要求，补一条 §4a 处置记录即可）。

