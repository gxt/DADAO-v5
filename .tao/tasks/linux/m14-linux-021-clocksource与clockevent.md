# m14-linux-021: clocksource / clockevent 升级（cfx_time 真时钟 + cfx_hart 定时器进通用框架）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-007`（K2 时间最小框架：`time.c` 的 `dadao_read_time`/`dadao_timer_arm` 等）、`m14-linux-017`（调度上电后 `schedule_tick` 有运行队列）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/time.c`/`kernel/setup.c`）
**并行组**：与 K4 其余任务**串行**（同组件同写者）
**预估**：3–4 h（接线为主，风险在 clocksource 稳定性判据与 clockevent 的 next-event 编程）
**档位**：中改（时间子系统接线 + 探针；复核 ≥3 路注入）
**状态**：待开始

## 背景

K2（`m14-linux-007`）已建**最小时间框架**：`time.c` 的 `dadao_read_time()`/`dadao_timer_arm()`/`dadao_timer_interrupt()` 直接操作 `cfx_time`/`cfx_hart`，`dadao_timer_interrupt()` 只做 `jiffies_64 += 1` + 重挂（`do_timer()` 的 jiffies 半边；负载均值半边要每 CPU 运行队列，K4 才具备）。本任务把它升级为 Linux 通用 **`clocksource`（cfx_time）+ `clockevent`（cfx_hart timer_cmp）**：注册到 `clocksource`/`clockevent` 框架，`timekeeping`/`sched_clock` 走真时钟，替代 `jiffies` 最小记账。

DADAO 特有事实（`contract-see §3/§6.5`，**不得偏离**）：
- `cfx_time`：`cg10 rc0 = freq = 1_000_000_000`（1 GHz，测试机约定）、`rc1 = value`（64 位、复位从 0 起算、1 count = 1 ns）；QEMU 以 `QEMU_CLOCK_VIRTUAL` ns 建模。
- `cfx_hart` 定时器：`cg8 rc4 = timer_cmp`（RW，64 位绝对时间，单位同 `cfx_time_value`；写新值取消旧 deadline 并清 `TIMER` pending）、`rc5 = timer_ctrl`（bit0 ENABLE/bit1 IMASK/bit2 ISTATUS 只读）；到期触发可屏蔽 `TIMER`（`1 << 10`）、`cause_info = 0`。
- `TIMER` 异步入口 = `cfx_hart` 的 supv 行（`contract-see §6.3`，K2 已落地 `async_trap.S`）；`escape` 后补投由**硬件**完成，内核不得软件代投（`contract-see §6.5`）。
- 放行前提：`cfx_time` 需 `cg10`、`cfx_hart` 需 `cg8` 的 `hypv_cg_reg_deleg` 放开（`contract-see §6.5`，K2 已放行）。

## 目标

1. **`clocksource`（cfx_time）**：`dadao_clocksource` 注册（`read` = `cfx_time_value`、`freq` = 1 GHz 现场读 `cg10 rc0`、`rating` 自定但须说明理由）；`sched_clock` 走 `cfx_time`；`timekeeping` 由 `clocksource` 驱动。
2. **`clockevent`（cfx_hart timer_cmp）**：`dadao_clockevent` 注册（`set_next_event` = 写 `timer_cmp` 绝对时间、`set_state_*` = 写 `timer_ctrl` ENABLE/IMASK）；`dadao_timer_interrupt()` 改为调 `clockevent` 的 `event_handler`（tick / 单次），不再裸写 jiffies。
3. **`time_init()`**：注册 clocksource/clockevent，替换 K2 的裸 `dadao_timer_arm` 路径；`HZ` 周期仍现场派生（`period = freq / HZ`，不写死）。
4. **探针** `tools/linux/k4_clocksource_probe.py`：断言见「验收 2」；沿用 K2 `k2_time_probe.py` 的「间隔余量 = period/2」与「停表校验」口径，不破坏 K2 判据。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_clocksource_probe.py` rc=0，逐 case 打印；期望值现场派生（`freq` ← `cg10 rc0` 读值、`period` ← `freq/HZ` 现场算、`HZ` ← `.config`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `T1 clocksource 单调`：连续两次 `cfx_time_value` 读值**非降**（`read` 现场打印）；`sched_clock` 与 `cfx_time_value` 同源（差值恒定在容差内）。
   - `T2 clockevent next-event`：写 `timer_cmp = now + period` 后在期望时刻内收到 `TIMER`（间隔 ∈ `[period/2, 2*period]` 现场实测分布）；`set_next_event` 后旧 deadline 取消（写更早值不双触发）。
   - `T3 jiffies/tick 驱动`：`event_handler` 每 tick 推进 `jiffies_64` + `schedule_tick` 跑通（有运行队列后负载均值半边可用）。
   - `T4 稳定性判据`：`clocksource` 的 `read` 两次调用间单调（QEMU 虚拟时钟不回退）；负例：注入「`read` 返回上一次值」⇒ 稳定性判据红。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `clocksource.read` 不读 `cfx_time`（恒返回常量）⇒ `T1` 红；② `set_next_event` 写错寄存器（写 `timer_ctrl` 而非 `timer_cmp`）⇒ `T2` 红（无中断或周期错）；③ `event_handler` 不推进 jiffies ⇒ `T3` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0（**K2 `check-linux-k2` 的 time 组必须仍绿**，`m14-linux-007` 判据不因升级而退役——除非按 `docs/Process-07 §4a` 显式退役并给替代）；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-021/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{time.c,setup.c}.patch`、`components/linux/patches/arch/dadao/include/asm/{timex.h,clocksource?}.patch`、`components/linux/changelog.md`、`tools/linux/k4_clocksource_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-see §3/§6.5` + `spec/DADAO-12 §4.7/§4.10` 为准；`cfx_time`/`cfx_hart` 的寄存器语义已冻结（§3），本任务只做**接线**，不改寄存器语义。
5. `escape` 后补投、IMASK pending 由硬件完成，内核**不得**软件代投（`contract-see §6.5`）；升级后不得破坏 K2 的「两轴 mask / 单旋钮」口径（`contract-see §6.4`）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. **（待裁定 3）clockevent/clocksource 是否在 K4 升级**：**选项**：A = 保留（K4 升级到通用框架，`sched_clock`/`timekeeping` 走真时钟，替代 jiffies 最小记账）；B = 后移 K5（K4 沿用 K2 最小 jiffies 框架，升级延后）。**建议 B**：调度/进程/COW/栈不依赖精确时钟（jiffies 已够），clocksource/clockevent 升级是「时间精度」优化、与进程语义正交；但若 K4 要跑真 init（musl 可能调 `clock_gettime`/`clock_getres`），则需 A。**本任务已按 A 立项**，若用户选 B 则撤销、归 K5。

## 审阅记录

（待填）
