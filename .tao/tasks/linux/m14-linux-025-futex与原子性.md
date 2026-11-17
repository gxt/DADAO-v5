# m14-linux-025: futex 与原子性（FUTEX_WAIT 原子 / FUTEX_WAKE 不丢唤醒 / 用户 lr+sc）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-024`（clone/线程，futex 需多线程）、`m14-linux-023`（syscall 闭环）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/syscalls.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：3–4 h（futex 是通用机制，arch 侧只补原子读/清保留标记口径）
**档位**：中改（`futex` 接线 + 原子性断言；复核 ≥3 路注入）
**状态**：待开始

## 背景

`024` 有了线程后，`futex` 成为 pthread 互斥/条件变量的地基。本任务补 `futex` 与用户原子性（`contract-syscall §11`）。

DADAO 特有事实（`contract-syscall §11`，**不得偏离**）：
- `lr`/`sc` 的保留标记、成功/失败、宽度、对齐与清标记条件**一律**按 `SimRISC-12 §1`；`sc` 可能**偶发失败**（spurious），软件须循环重试；**异常或中断进入清除保留标记** ⇒ `lr…sc` **不能跨任何 syscall/异常**（`§11`）。
- `futex`：`FUTEX_WAIT` 的「检查用户字 → 睡眠」必须原子——内核在持锁下用 `lr` 语义复核用户字（或等价单核原子读）后再入队；`FUTEX_WAKE` 不得丢唤醒；`futex` 不改变用户 `lr`/`sc` 语义（`§11`）。
- 单核下**不得**把「单核」当免内存序假设，生成的序须与多核一致（`§11`）。
- 用户 `atomic_*`/`cmpxchg` 由 `lr`/`sc` 循环实现（宽度选 `.b`/`.w`/`.t`/`.o`）。

## 目标

1. **`futex` syscall 接线**：`FUTEX_WAIT`/`FUTEX_WAKE`（+ `FUTEX_WAIT_BITSET`/`WAKE_BITSET` 最小面）走通用 `kernel/futex.c`；`arch/dadao` 侧只补「原子读用户字」（`futex_atomic_cmpxchg_inatomic`/等价，用 `lr` 语义）。
2. **用户 `lr`/`sc` 清标记**：确认异常/中断/syscall 进入即清保留标记（`SimRISC-12 §1`），用户 `cmpxchg` 循环正确重试（不跨 syscall）。
3. **探针** `tools/linux/k5_futex_probe.py` + `CONFIG_DADAO_K5_FUTEX_SELFTEST`：两线程 `FUTEX_WAIT`/`WAKE` 往返 + 用户 `cmpxchg` 竞争。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_futex_probe.py` rc=0，逐 case 打印；期望值现场派生（`lr/sc` 语义 ← `SimRISC-12 §1`、futex 口径 ← `contract-syscall §11`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `F1 FUTEX_WAIT 原子`：线程 A 检查用户字 == 期望后 `FUTEX_WAIT` 入队；线程 B 改字 + `FUTEX_WAKE` ⇒ A 醒来（**不丢唤醒**、检查→睡眠原子）。
   - `F2 FUTEX_WAKE 计数`：多个 waiter 时 `WAKE(n)` 唤醒恰 n 个（现场计数）。
   - `F3 用户 lr/sc 竞争`：两线程 `cmpxchg` 同一地址，恰一者成功（`lr`/`sc` 语义正确、spurious 重试）。
   - `F4 lr/sc 不跨 syscall`：`lr` 后 syscall 再 `sc` ⇒ `sc` 失败（保留标记被清）。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `FUTEX_WAIT` 不复核用户字（非原子）⇒ `F1` 红；② `FUTEX_WAKE` 漏唤醒 ⇒ `F1`/`F2` 红；③ `lr/sc` 保留标记不跨 syscall 清（跨 syscall 仍成功）⇒ `F4` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_clone_probe.py`（024）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-025/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{syscalls.c,futex?}.patch`、`components/linux/patches/arch/dadao/include/asm/{futex.h,cmpxchg.h}.patch`、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k5_futex_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k5_futex_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §11` + `SimRISC-12 §1`（原子指令）为准；`futex` 通用逻辑（`kernel/futex.c`）不重写，只补 arch 原子读；**不得**因单核放宽内存序。
5. 不定义 TLB/cache/多 hart 保留标记仲裁（`§11`；多 hart 另立契约）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. 无新裁定项；`futex` 与 `lr/sc` 口径已由 `contract-syscall §11` 冻结，本任务只做接线与断言。

## 审阅记录

（待填）
