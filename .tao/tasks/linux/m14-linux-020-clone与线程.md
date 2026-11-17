# m14-linux-020: clone 与线程（CLONE_* 标志 + TLS + 共享地址空间）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（`copy_process`/`copy_mm`）、`m14-linux-017`（上下文切换）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/process.c`/`fork.c` 钩子）
**并行组**：与 K4 其余任务**串行**（同组件同写者）
**预估**：3–5 h（`clone` 是 `fork` 的 flag 扩展，代码量取决于是否含 `CLONE_SETTLS`/`CLONE_VM`）
**档位**：中改（`copy_process` 的 arch 钩子扩展 + TLS；复核 ≥3 路注入）
**状态**：待开始

## 背景

`m14-linux-016` 实现 `fork`（`CLONE_SIGHAND` 无 `CLONE_VM` 等线程标志）。本任务补 `clone` 的**线程**语义：`CLONE_VM`（共享地址空间）、`CLONE_FS`/`CLONE_FILES`/`CLONE_SIGHAND`（共享资源表）、`CLONE_SETTLS`（子线程 `rbtp` = `tls` 参数）、`CLONE_THREAD`（同线程组）。`copy_process` 的通用逻辑已支持这些 flag；本任务只补 `arch/dadao` 侧钩子。

DADAO 特有事实（`contract-syscall §10/§11`，**本任务不得偏离**）：
- `rb3` = `rbtp`（thread pointer，TP），**保留不分配**、跨 syscall 保持；`clone` 含 `CLONE_SETTLS` 时子线程 `rbtp` = `tls` 参数、父线程不变。
- **「双返回」属用户态 wrapper（musl `clone`/`pthread_create`）语义**，内核只保证「子线程从 syscall 返回处开始执行时 `rd8 = 0`、其余寄存器现场 = 父现场副本（除返回寄存器与架构约定差异）」，父线程返回子 tid；内核**不实现两次返回**。
- `clone` 原子可见：子现场 = 父现场副本、`rd8 = 0`；子 `rbtp` 按 §10 设置；不得让子看到半初始化的 TCB（`contract-syscall §11`）。
- `lr`/`sc` 保留标记**异常/中断进入即清** ⇒ `lr…sc` 不能跨 syscall（`SimRISC-12 §1`）；单核下不得把「单核」当免内存序假设（`contract-syscall §11`）。

## 目标

1. **`copy_thread` 扩展**：支持 `CLONE_SETTLS`（子 `thread.tp`/`rb3` = 传入 `tls`）、`CLONE_VM`（不 `dup_mm`，共享父 `mm` 且 `mm->mm_users++`）、子入口 `rd8 = 0`。
2. **`syscall` 面**：`clone` 号走通用表（号表 `contract-syscall §1.2` 锁定来源，沿用 RISC-V 编号）；参数解析（`flags`/`stack`/`tls`/`ptid`/`ctid`）与 `copy_process` 传参按 `DADAO-21 §3/§4`（`rd16–31`/`rb16–31`）。
3. **TLS 维护**（`contract-syscall §10`）：入口保存/返回恢复 `rb3`；`clone` 子线程按 `CLONE_SETTLS` 设 `rbtp`。
4. **探针** `tools/linux/k4_clone_probe.py` + `CONFIG_DADAO_K4_CLONE_SELFTEST`：内核侧 `clone`（`kernel_thread`/直接 `copy_process`）创建共享 `mm` 的线程，断言见「验收 2」。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_clone_probe.py` rc=0，逐 case 打印；期望值现场派生（号表 ← `contract-syscall §1.2` 锁定快照、寄存器 ← `contract-abi §4`、TLS ← `contract-syscall §10`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `C1 CLONE_VM 共享地址空间`：clone 后子线程 `mm` == 父 `mm`（`mm_users` 增）、`context.asid` **相同**（共享 ⇒ 不新分配）；与 `fork`（`mm` 不同、asid 不同）对照。
   - `C2 CLONE_SETTLS`：子线程 `rb3/rbtp` == 传入 `tls` 值、父线程 `rb3` 不变（现场哨兵值）。
   - `C3 子入口 rd8=0`：子线程从 `copy_thread` 入口恢复时 `rd8 == 0`（`contract-syscall §10`「子入口 rd8=0」）。
   - `C4 父返回子 tid`：clone 返回后父侧拿到子 tid（非 0）；子侧 `rd8=0`（双返回归 musl wrapper，内核只保证这两点）。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `CLONE_VM` 仍 `dup_mm` ⇒ `C1` 红（mm 不同/asid 不同）；② `CLONE_SETTLS` 不设子 `rb3` ⇒ `C2` 红；③ 子入口不置 `rd8=0` ⇒ `C3` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）、`k4_switch_probe.py`（017）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-020/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{process.c,fork.c?}.patch`（`copy_thread` 扩展；`fork.c` 仅若需 arch 钩子）、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,syscalls.c}.patch`、`components/linux/patches/arch/dadao/kernel/k4_clone_selftest.c.patch`（新）、`components/linux/changelog.md`、`tools/linux/k4_clone_probe.py`。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §10/§11` + `DADAO-21 §4` + `contract-abi §4.5` 为准；`copy_process` 通用逻辑不重写，只补 arch 钩子；「双返回」**不得**在内核实现。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. **（待裁定 2）clone/线程是否属 K4**：本任务已按「属 K4」立项。**选项**：A = 保留（K4 含 clone/线程，成本低——`clone` 是 `fork` 的 flag 扩展）；B = 后移 K5（K4 只做 `fork`/单进程，clone 的线程/共享语义延后，musl 静态 init 单进程即可）。**建议 A**（代码量与 `fork` 高度重叠，K4 一次到位）；若用户选 B，本任务撤销、`CLONE_*` 归 K5，`fork` 的 `CLONE_SIGHAND` 等标志回退到最小集。
2. **（待裁定 4）** 本任务 clone/线程的探针在内核侧构造（`kernel_thread`/直接 `copy_process`），不依赖 U-mode 入口；「真实 pthread 创建」端到端断言依赖 U-mode 入口 + musl，归 K5。

## 审阅记录

（待填）
