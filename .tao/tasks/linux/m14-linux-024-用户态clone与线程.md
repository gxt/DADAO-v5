# m14-linux-024: 用户态 clone/线程（CLONE_VM / CLONE_SETTLS / CLONE_THREAD + TLS 用户面）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-023`（syscall 闭环）、`m14-linux-020`（kernel_thread/copy_process 共享路径）、`m14-linux-016`（copy_process/dup_mm）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/process.c`/`syscalls.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：3–5 h（`clone` 是 `fork` 的 flag 扩展 + TLS 设置）
**档位**：大改（用户可见 clone 语义 + TLS；复核 ≥4 路注入）
**状态**：待开始

## 背景

`020` 只做内核线程（`kernel_thread`，`CLONE_FS|CLONE_FILES`、`mm == NULL`），把用户态 `clone` 交接给 K5（判据见 `020`「K5 交接判据」段）。本任务补用户态 `clone` 的完整语义。

DADAO 特有事实（`contract-syscall §10/§11`，**不得偏离**）：
- `rb3 = rbtp`（TP）；`clone` 含 `CLONE_SETTLS` 时子线程 `rb3/rbtp = tls` 参数、父不变。
- **「双返回」归用户态 wrapper（musl `clone`/`pthread_create`）**：内核只保证「子线程从 syscall 返回处开始执行时 `rd8 = 0`、其余寄存器现场 = 父现场副本（除返回寄存器与架构约定差异）」，父线程返回子 tid；内核**不实现两次返回**（`§10`）。
- `clone` 原子可见：子现场 = 父现场副本、`rd8 = 0`、子 `rbtp` 按 §10 设；不得让子看到半初始化 TCB（`§11`）。
- `lr`/`sc` 保留标记**异常/中断进入即清** ⇒ `lr…sc` 不能跨任何 syscall（`§11`）。

## 目标

1. **`clone` syscall 完整**（`kernel/syscalls.c` 或通用表 `clone` 号）：解析 `flags`/`stack`/`tls`/`ptid`/`ctid`（`rd16–31`/`rb16–31`，`§3`），交 `copy_process`；返回父侧 = 子 tid、子侧 = `rd8 = 0`。
2. **`CLONE_VM`**：共享父 `mm`（不 `dup_mm`），`mm->mm_users++`、`context.asid` **相同**（不新分配）。
3. **`CLONE_SETTLS`**：子线程 `rb3/rbtp = tls` 参数、父不变（`copy_thread` 的 TLS 分支）。
4. **`CLONE_THREAD`**：同线程组（`tgid` 共享）；`CLONE_FS/FILES/SIGHAND` 用户可见共享语义。
5. **TLS 用户面**：入口保存/返回恢复 `rb3`（`023` 已做）；`execve` 清 0（实现点见 `023` 待裁定 1）；`initial-exec`/`local-exec` 分工（TP 方向/偏置归 musl arch 宏，本任务不决定，`§10`）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_clone_probe.py` rc=0，逐 case 打印；期望值现场派生（`CLONE_*` 位 ← `include/uapi/linux/sched.h` 锁定源、TLS ← `contract-syscall §10`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `C1 CLONE_VM 共享地址空间`：clone 后子线程 `mm == 父 mm`（`mm_users` 增）、`context.asid` 相同（与 `fork` 对照：`fork` 的 `mm`/asid 不同）。
   - `C2 CLONE_SETTLS`：子线程 `rb3/rbtp == tls` 参数、父 `rb3` 不变（现场哨兵值）。
   - `C3 子入口 rd8=0 + 父返 tid`：父侧 `clone` 返回子 tid（非 0）、子侧 `rd8 == 0`（**双返回归 musl wrapper**，内核只保证这两点）。
   - `C4 CLONE_THREAD`：子线程与父同 `tgid`（线程组）；`CLONE_FS/FILES/SIGHAND` 共享（现场断言指针相同）。
   - `C5 TLS 保持`：子线程 `rbtp` 跨 syscall 不变（`023` 口径）。
3. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：① `CLONE_VM` 仍 `dup_mm` ⇒ `C1` 红（mm/asid 不同）；② `CLONE_SETTLS` 不设子 `rb3` ⇒ `C2` 红；③ 子入口不置 `rd8=0` ⇒ `C3` 红；④ `CLONE_THREAD` 不共享 `tgid` ⇒ `C4` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_syscall_probe.py`（023）、`k4_kthread_probe.py`（020）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-024/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{process.c,syscalls.c}.patch`、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k5_clone_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k5_clone_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §10/§11` + `DADAO-21 §4` + `contract-abi §4.5` 为准；`copy_process` 通用逻辑不重写，只补 arch 钩子；**「双返回」不得在内核实现**。
5. `clone` 原子可见：子现场 = 父副本、`rd8=0`、子 `rbtp` 按 §10 设（`§11`）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. **`execve` 清 0 实现点**：同 `023` 待裁定 1（若用户选 musl 校准，本任务的 TLS 用户面只做「入口保存/返回恢复 + `clone` SETTLS」，清 0 交 musl 任务）。
2. **pthread 类测试的载体**：本任务验收用**内核侧 clone 自检**（`kernel_thread` 风格 + 用户态 flag）；「真实 musl `pthread_create`」端到端依赖 musl 移植 + `futex`（`025`），是否在本任务断言由用户定（建议：留 `029` 收口门控做端到端，本任务只做 clone 语义）。

## 审阅记录

（待填）
