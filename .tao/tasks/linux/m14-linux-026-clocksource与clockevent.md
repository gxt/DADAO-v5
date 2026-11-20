# m14-linux-026: clocksource / clockevent 通用框架（cfx_time + cfx_hart 定时器）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-017`（最小 clockevent）、`m14-linux-023`（syscall 闭环，供 `clock_gettime` 等）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/time.c`/`setup.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）；与 023–025/027–028 共享文件少，理论上可并行、受单组件单写者约束
**预估**：3–4 h（接线为主，风险在 clocksource 稳定性判据与 clockevent 的 next-event 编程）
**档位**：中改（时间子系统接线 + 探针；复核 ≥3 路注入）
**状态**：待开始

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

（待填）
