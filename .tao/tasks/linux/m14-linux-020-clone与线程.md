# m14-linux-020: 内核线程（kernel_thread / kthreadd / kthread_create）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（`copy_process`/`copy_thread` 共享路径）、`m14-linux-017`（上下文切换/调度）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/process.c`/`copy_process` 钩子）
**并行组**：与 K4 其余任务**串行**（同组件同写者）
**预估**：2–3 h（收窄为内核线程；复用 016 的 `copy_process`，代码量小）
**档位**：中改（`copy_process` 的 `kernel_thread` 钩子 + `kthreadd` 接线 + 探针；复核 ≥3 路注入）
**状态**：待开始

## 背景

K4 分界已定（**用户 2026-11-17 选 A**）：**K4 = 内核侧进程/线程原语**，**K5 = 用户态**。本任务由原「clone/线程」**收窄为内核线程**：`kernel_thread` / `kthreadd` / `kthread_create` / `kthread_run` 最小面，为 K4 其余任务（COW/栈的验证载体、后续驱动/工作队列）提供内核线程基础设施。**用户态 `clone` 的 `CLONE_VM`/`CLONE_SETTLS`/`CLONE_THREAD` 语义、TLS（`rb3=rbtp`）用户面、`futex`、pthread 类测试全部归 K5**（判据交接见下「K5 交接判据」段）。

DADAO 特有事实（`contract-syscall §10/§11`，本任务**内核线程不消费**，仅作 K5 交接边界）：
- `rb3` = `rbtp`（thread pointer），保留不分配；内核线程**无用户态、无 TLS**，不设 `rb3`。
- `kernel_thread` 子任务**无用户 `mm`（`mm == NULL`）**：不 `dup_mm`，与 `016` 的 `fork`（有 `mm`）对照。
- `copy_process` 通用逻辑已支持 `CLONE_FS|CLONE_FILES` 等标志；本任务只补 `arch/dadao` 侧 `kernel_thread` 钩子，**不新增用户 clone 语义**。

## 目标

1. **`kernel_thread`（arch 钩子）**：`kernel_thread(fn, arg, flags)` 建内核线程——`copy_thread` 设子任务入口为 `fn`（`arg` 为参数）、子任务 `mm == NULL`（不 `dup_mm`）、默认 `CLONE_FS | CLONE_FILES`（共享父资源表）、子入口 `rd8 = 0`。
2. **`kthreadd`（`rest_init` 路径）**：内核在 `rest_init()` 创建 **pid 2 的 `kthreadd`**（内核线程守护者），供 `kthread_create` 排队。
3. **`kthread_create` / `kthread_run` 最小面**：能创建内核线程、执行 `fn`、`kthread_should_stop()`/`kthread_stop()` 退出（任务从运行队列消失）。
4. **复用 016 的 `copy_process`/`copy_thread` 共享路径**：`fork` 与 `kernel_thread` 走同一 `copy_process`，仅 `copy_thread` 的入口/`mm` 处理分支不同。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_kthread_probe.py` rc=0，逐 case 打印；期望值现场派生（`mm`/`mm_users` 布局 ← 内核源现场符号、`CLONE_*` 位 ← `include/uapi/linux/sched.h` 锁定源）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `K1 kthreadd 创建`：`rest_init()` 后 `kthreadd` 存在（pid == 2）、是内核线程（`mm == NULL`）。
   - `K2 kthread_create/kthread_run 起停`：创建内核线程 → `fn` 执行（计数器推进）→ `kthread_stop()` 后退出（`kthread_should_stop()` 返回真、任务从队列消失、`fn` 不再推进）。
   - `K3 kernel_thread 的 CLONE_FS|CLONE_FILES`：`kernel_thread` 子任务与父共享 `fs`/`files`（现场断言指针相同）；`mm == NULL`（**不** `dup_mm`，与 016 的 `fork` 对照——`fork` 子 `mm` 非空、asid 不同）。
   - `K4 无用户 clone 语义`：探针**负例断言**——本任务 `copy_thread` **不实现** `CLONE_SETTLS`（无 TLS 参数分支），`kernel_thread` 不设 `rb3`；断言「用户 clone 的 `CLONE_VM`/`CLONE_THREAD`/双返回不在 K4 实现」（结构性：`copy_thread` 签名无 `tls` 参数、无 `ret_from_kernel_thread` 的用户态分支）。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `rest_init` 不建 `kthreadd` ⇒ `K1` 红；② `kernel_thread` 错误地 `dup_mm`（`mm` 非空）⇒ `K3` 红；③ `kthread_stop` 不置停止位（`kthread_should_stop` 恒假）⇒ `K2` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）、`k4_switch_probe.py`（017）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## K5 交接判据（本任务不实现；K5 立册时逐条落验收）

- `clone` 的 `CLONE_VM` 共享地址空间（子 `mm` == 父 `mm`、`mm_users++`、asid 相同）。
- `clone` 的 `CLONE_SETTLS`（子线程 `rb3/rbtp` = `tls` 参数、父不变）。
- `clone` 子入口 `rd8 = 0`、父返回子 tid；**「双返回」归 musl wrapper**，内核只保证这两点（`contract-syscall §10`）。
- `CLONE_THREAD`（同线程组）、`CLONE_FS`/`CLONE_FILES`/`CLONE_SIGHAND` 的**用户可见共享语义**（内核侧 `kernel_thread` 的 `CLONE_FS|CLONE_FILES` 已在本任务 `K3` 覆盖，用户态可见性归 K5）。
- TLS 用户面：`rb3=rbtp` 入口保存/返回恢复、`execve` 清 0 实现点（musl 校准）、`initial-exec`/`local-exec` 分工（`contract-syscall §10`）。
- `futex`（`FUTEX_WAIT` 检查→睡眠原子、`FUTEX_WAKE` 不丢唤醒）、用户 `lr`/`sc` 保留标记跨 syscall 即清（`contract-syscall §11`）。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-020/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{process.c,Makefile}.patch`（`kernel_thread` 钩子）、`components/linux/patches/init/{main.c?}.patch`（`rest_init` 的 `kthreadd`，若需 arch 钩子）、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k4_kthread_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k4_kthread_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §10/§11`（TLS/原子性，作 K5 交接边界）+ `copy_process` 通用逻辑为准；`kernel_thread` 只补 arch 钩子，不重写 `copy_process`/`kthread` 通用代码；**不得**在本任务实现用户 clone 语义。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~（待裁定 2）clone/线程是否 K4~~ **已裁定（用户 2026-11-17 选 A）**：K4 = 内核侧进程/线程原语（本任务收窄为内核线程）；用户态 `clone`/TLS/`futex`/pthread 归 K5。原 `C1–C4` 判据整体移入「K5 交接判据」段。
2. ~~（待裁定 4）~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环并入 `016`/`017`，本任务内核线程不依赖用户态。

## 审阅记录

（待填）
