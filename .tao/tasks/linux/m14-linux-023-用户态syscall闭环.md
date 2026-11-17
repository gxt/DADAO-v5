# m14-linux-023: 用户态 syscall 闭环（umon 入口 + 分发表 + errno + TLS 用户面）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（最小 U-mode 入口骨架）、`m14-linux-017`（init 真跑 + 最小 clockevent）、`m14-linux-020`（kernel_thread/kthreadd）——均为 **K4 收口**前置
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/trap.S`/`syscalls.c`/`process.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：4–6 h（syscall 分发/返回路径 + errno + TLS 入口保存恢复）
**档位**：大改（syscall 闭环核心路径 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

`016` 做了最小 U-mode 入口骨架（`cfx_umon` user 行路由 + 单帧），`017` 做到「init 真跑」（`kernel_init` → initramfs `/init`）。本任务让静态 musl `init` 能**发起 syscall 并正确返回**，形成「用户态 → trap → 内核 → escape → 用户态」闭环。`syscall_table.c` 的分发表已由 K0 建好（asm-generic 号表）；本任务补齐**入口参数解析 / 分派 / 返回 / errno / TLS**。

DADAO 特有事实（`contract-syscall §2/§3/§8/§9/§10`，**不得偏离**）：
- 用户 syscall = `trap cfx_umon, 0`（`SBI_UMON_SYSCALL`）；`rd15 = nr`、参数 `rd16–31`/`rb16–31`/`rf16–31`（三组独立计数、自 16 起）、返回 `rd8`（`§3`）。
- 入口帧：硬件只存 cg5 五字段（`excp_prev_run_mode`/`excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_pending`），**不存通用寄存器**；`excp_cause_id == 1<<0`（`CFXTRAP`）、`immu18 = excp_cause_info & 0x3FFFF`（`§8` 合约内推导）。
- **errno = `rd8` 负值（`-errno`），`[-4095, -1]`**；不支持返回 `-ENOSYS`、参数错返回对应负值；**不用 `rd1`**（`§9`）；内部重启码（`ERESTARTSYS` 等）不得外泄。
- **TLS**：`rb3 = rbtp`（thread pointer），保留不分配、跨 syscall 保持 ⇒ 入口保存、返回恢复（`§10`）。
- 返回 = `escape cfx_umon, [excp_cause_ip, 4]`（落回 `trap` 下一条）；`escape` 的 `cfxha` 必须 = 当前 cfx（`cfx_umon`），帧/目标错 ⇒ `CFXESC`。

## 目标

1. **umon 入口完整**：`kernel/trap.S` 的 umon 向量接 syscall 路径——保存用户态 `pt_regs`（4 组 rd/rb/ra/rf，`m14-linux-022` 帧布局）、按 `rd15` 查 `sys_call_table` 分派、返回前恢复。
2. **参数/返回**：`arch/dadao` 侧 `syscall_get_nr`/`syscall_get_arguments`/`syscall_set_return_value`（`asm/syscall.h`）落地——`nr=rd15`、参数从 `rd16/rb16` 起、返回值写 `rd8`（`§3`）。
3. **errno**：错误路径写 `rd8 = -errno`（`[-4095,-1]`）；`-ENOSYS`/`-EINVAL` 等；`ERESTARTSYS` 类内部码在返回用户态前转 `-errno` 或重试（`§9`）。
4. **TLS 用户面**：入口保存 `rb3`、返回恢复；`execve` 清 0（实现点见**待裁定 1**）；`rb3` 不作传参/临时（`§10`）。
5. **返回用户态**：`ret_from_syscall` 恢复用户态寄存器、`escape cfx_umon, [excp_cause_ip, 4]` 落回；`TIF_*` 工作（reschedule/signal）预留钩子（信号归 `027`）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_syscall_probe.py` rc=0，逐 case 打印；期望值现场派生（号表 ← `contract-syscall §1.2` 锁定快照、寄存器 ← `contract-abi §4`、errno ← `contract-syscall §9`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `U1 write 往返`：用户态 `write(fd, buf, n)` ⇒ 经 umon 分发、返回 `n`（非负）、输出正确。
   - `U2 exit 往返`：`exit(0)` ⇒ 正常退出（宿主 rc=0 / `SYS_EXIT(0)`）。
   - `U3 errno 形态`：不支持号返回 `-ENOSYS`、参数错返回 `-EINVAL`（`rd8` 负值、∈ `[-4095,-1]`，**非** `rd1`）。
   - `U4 TLS 保持`：`rb3` 跨多次 syscall 不变（现场哨兵值）；`write` 返回后 `rb3` 仍 = 入口值。
   - `U5 帧字段`：`excp_cause_id == 1<<0`、`excp_prev_run_mode == user(0)`、`excp_cause_ip == trap` 地址、`immu18 == info & 0x3FFFF`（`§8`）。
3. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：① 不恢复 `rb3` ⇒ `U4` 红；② 返回写 `rd1` 而非 `rd8` ⇒ `U3` 红；③ `immu18` 解析错（取错位段）⇒ `U5` 红；④ 错误返回 `-1` 而非 `-errno` ⇒ `U3` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）、`k4_switch_probe.py`（017）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-023/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{trap.S,syscalls.c,process.c}.patch`、`components/linux/patches/arch/dadao/include/asm/{syscall.h,ptrace.h}.patch`、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k5_syscall_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k5_syscall_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §2/§3/§8/§9/§10` + `contract-abi §4` 为准；**不得**套 RISC-V `a0–a7`/x86 寄存器约定；`rd15` 是号、`rd16/rb16` 起参数、`rd8` 返回。
5. 单帧、不递归（同 cfx 嵌套留 K5，`016` 口径）；`escape` 后补投由硬件完成（`contract-see §6.5`）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. **`execve` 清 0 的实现点**（`contract-syscall §10`）：「`rbtp` 清 0」在内核 `execve` 路径 vs musl 启动代码，二者择一。建议：内核 `execve` 清 0（与「`clone` 子入口 `rd8=0`」同层，内核保证初始态），musl 侧不重复；若用户选 musl 校准，则本任务 TLS 用户面只做「入口保存/返回恢复」，清 0 交 `024`/musl 任务。

## 审阅记录

（待填）
