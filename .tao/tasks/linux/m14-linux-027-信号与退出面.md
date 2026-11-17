# m14-linux-027: 信号与退出面（SIGSEGV 投递 + 信号帧 4 组 + exit + setrlimit/RLIMIT_STACK）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-023`（syscall 闭环）、`m14-linux-019`（用户栈增长，SIGSEGV 来源）、`m14-linux-022`（异常帧四组）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/trap.S`/`mm/fault.c`/`kernel/signal.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：4–6 h（信号帧布局 + SIGSEGV 升级 + setrlimit；风险在 uapi 面）
**档位**：大改（信号帧 uapi + 页故障语义升级 + 探针；复核 ≥4 路注入）
**状态**：待开始

## 背景

K3/K4 遗留：页故障的「无 VMA / 越权」目前走 `DADAO_PF_FATAL`（`mm/fault.c`）具名终止（monitor 段退码），**不是** Linux 信号。本任务把用户态页故障升级为 **`SIGSEGV` 投递**（用户进程收到信号、按默认动作终止），并补齐信号帧（4 组寄存器）、`exit`/`exit_group`、`setrlimit`（`RLIMIT_STACK` 继承，`019` 交接）。

DADAO 特有事实（**不得偏离**）：
- 内核 `struct pt_regs`（`m14-linux-022`）= `rd[64]/rb[64]/ip/status/ra[64]/rf[64]`（2064 B，四组全量）；但 **uapi `user_regs_struct`（`uapi/asm/ptrace.h`）仍是 K0 旧定义 `rd[32]/rb[32]/ra[8]`**，未随 022 更新 ⇒ 信号帧布局需重新定义（见**待裁定 1**）。
- `ra0–ra63` 含 `{RACNT, MRPTR}` 元数据字，异常进入/退出**不改变**（`SimRISC-00 §2.4`）；信号帧保存/恢复须**逐位**保留 ra 栈。
- `rf0` = FCSR，写口 mask 非可写字段 ⇒ 帧内是架构值（`SimRISC-00 §2.3`）。
- `setrlimit`：`RLIMIT_STACK` 默认 8 MiB（128 页），`019` 已在内核侧 set/restore；本任务补 **syscall 面 + 继承**（子进程继承父 rlimit）。
- 信号帧返回 = `rt_sigreturn`（`016` 的 `syscalls.c` 桩返回 `-EINVAL`，本任务真实现）。

## 目标

1. **信号帧（sigframe/sigcontext）**：定义 `rt_sigframe` 布局（含 `struct sigcontext`，4 组寄存器 rd/rb/ra/rf + ip/status）；`setup_rt_frame`/`restore_sigcontext`（`kernel/signal.c`）按 `contract-abi` 的 caller/callee-saved 与 RA 栈保存/恢复；`rt_sigreturn` 真实现。
2. **SIGSEGV 投递**：`mm/fault.c` 的用户态「无 VMA / 越权 / `die-perm`」不再具名终止，改 `force_sig(SIGSEGV)`（内核态故障仍走具名终止）；用户进程按默认动作终止。
3. **exit / exit_group**：用户进程退出（`do_exit`）、`exit_group` 终止线程组；退出码正确（宿主可见）。
4. **setrlimit（RLIMIT_STACK）**：`setrlimit`/`getrlimit` syscall 面；子进程 `fork`/`execve` 继承 `RLIMIT_STACK`（`019` 的扩栈上限读继承值）。
5. **探针** `tools/linux/k5_signal_probe.py` + `CONFIG_DADAO_K5_SIGNAL_SELFTEST`。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_signal_probe.py` rc=0，逐 case 打印；期望值现场派生（信号帧布局 ← `contract-abi §4.5` + `SimRISC-00 §2.3/§2.4`、退码段 ← `spec/Kaiwu §7.1`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `S1 SIGSEGV 投递`：用户态访问无映射地址 ⇒ 收到 `SIGSEGV`（默认动作终止、退码正确）；**不再**走 `DADAO_PF_FATAL` 的 monitor 段具名终止。
   - `S2 信号帧往返`：安装 handler → 触发信号 → `rt_sigreturn` 恢复 4 组寄存器（`ra` 栈逐位、`rf0` 架构值、`ip`/`rb1`/callee-saved 哨兵值一致）。
   - `S3 exit/exit_group`：`exit(0)` ⇒ 进程退出、宿主 rc=0；`exit_group` 终止线程组。
   - `S4 setrlimit/RLIMIT_STACK 继承`：`setrlimit(RLIMIT_STACK, 新值)` 后 `getrlimit` 读回；`fork` 子进程继承父值；`019` 的扩栈上限用继承值。
3. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：① 页故障仍 `DADAO_PF_FATAL` 不投 SIGSEGV ⇒ `S1` 红；② `rt_sigreturn` 不恢复 `ra` 栈 ⇒ `S2` 红；③ `exit` 不退出 ⇒ `S3` 红；④ `fork` 不继承 `RLIMIT_STACK` ⇒ `S4` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_syscall_probe.py`（023）、`k4_fork_probe.py`（016）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-027/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{signal.c,signal.S?}.patch`（signal.c 新建）、`components/linux/patches/arch/dadao/include/uapi/asm/{sigcontext,ptrace}.h.patch`（4 组）、`components/linux/patches/arch/dadao/mm/fault.c.patch`（SIGSEGV 升级）、`components/linux/patches/arch/dadao/kernel/{syscalls.c,Makefile,Kconfig.debug}.patch`、`components/linux/changelog.md`、`tools/linux/k5_signal_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-abi §4.5`（callee-saved/CSR）+ `SimRISC-00 §2.3/§2.4`（rf0/ra 栈）+ `spec/Kaiwu §7.1`（退码段）为准；信号帧的寄存器保存集**不得**套 RISC-V/x86。
5. 内核态页故障仍具名终止（只升级**用户态**为 SIGSEGV）；`ra` 栈保存须逐位（含 `ra0` 元数据字）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. **信号帧的 uapi 布局**：`uapi/asm/ptrace.h` 的 `user_regs_struct` 现为 K0 旧定义（`rd[32]/rb[32]/ra[8]`），与内核 `pt_regs`（4 组 2064 B）不一致。**选项**：A = 扩 `user_regs_struct` 到 4 组（`rd/rb/ra/rf` 各 64 + `ip`/`status`），`sigcontext` 直接引用，与内核布局同构（建议，musl 侧 sigcontext 结构随之对齐）；B = `sigcontext` 用独立精简布局（只存 caller/callee-saved 需要的），uapi `user_regs_struct` 不动。**建议 A**（单一真源、与 ptrace/core dump 同布局）；需用户确认 musl 移植侧的 `mcontext_t`/`sigcontext` 对齐口径。

## 审阅记录

（待填）
