# m14-linux-027: 信号与退出面（SIGSEGV 投递 + exit + setrlimit/RLIMIT_STACK）

> **本任务已按用户 2026-11-20 裁定拆分**（依据 `m14-linux-039 信号/退出 与主流 ISA 差异盘点`）：信号机制整体缺失（29 条差异 / P0 18），2–3 h 不成立。拆分后：
>
> - **`m14-linux-045 通用 entry/exit 工作循环`** —— `TIF_*` 消费 + syscall enter/exit + `irqentry_*` 接线（基础设施）；
> - **`m14-linux-046 信号帧与投递`** —— `rt_sigframe`/`setup_rt_frame`/`rt_sigreturn`/`force_sig`（信号本体）；
> - **本任务（027）只保留行为面** —— SIGSEGV 投递、`exit`/`exit_group`、`setrlimit(RLIMIT_STACK)` 继承。
>
> 原「信号帧 4 组」那条验收（S2）**已移入 046**；本任务不再实现帧。

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-045`（工作循环：`TIF_SIGPENDING` 能被消费）、`m14-linux-046`（信号帧与投递）、`m14-linux-019`（用户栈增长，SIGSEGV 来源）、`m14-linux-022`（异常帧四组）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/trap.S`/`mm/fault.c`/`kernel/signal.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：4–6 h（信号帧布局 + SIGSEGV 升级 + setrlimit；风险在 uapi 面）
**档位**：大改（信号帧 uapi + 页故障语义升级 + 探针；复核 ≥4 路注入）
**状态**：待验收

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
   - ~~`S2 信号帧往返`~~ **已移入 `m14-linux-046 信号帧与投递`**（本任务不再做帧）。
   - `S3 exit/exit_group`：`exit(0)` ⇒ 进程退出、宿主 rc=0；`exit_group` 终止线程组。
   - `S4 setrlimit/RLIMIT_STACK 继承`：`setrlimit(RLIMIT_STACK, 新值)` 后 `getrlimit` 读回；`fork` 子进程继承父值；`019` 的扩栈上限用继承值。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① 页故障仍 `DADAO_PF_FATAL` 不投 SIGSEGV ⇒ `S1` 红；② `exit` 不退出 ⇒ `S3` 红；③ `fork` 不继承 `RLIMIT_STACK` ⇒ `S4` 红。（原 ②「`rt_sigreturn` 不恢复 `ra` 栈」随 S2 移入 046。）
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_syscall_probe.py`（023）、`k4_fork_probe.py`（016）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-027/`。
2. **预计改动文件**（收窄后）：`components/linux/patches/arch/dadao/mm/fault.c.patch`（用户态页故障升级 SIGSEGV）、`components/linux/patches/arch/dadao/kernel/{syscalls.c,Kconfig.debug}.patch`（setrlimit/exit 面）、`components/linux/changelog.md`、`tools/linux/k5_signal_probe.py`（新）。**信号帧与 `signal.c` 已归 `046`**，本任务不建。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-abi §4.5`（callee-saved/CSR）+ `SimRISC-00 §2.3/§2.4`（rf0/ra 栈）+ `spec/Kaiwu §7.1`（退码段）为准；信号帧的寄存器保存集**不得**套 RISC-V/x86。
5. 内核态页故障仍具名终止（只升级**用户态**为 SIGSEGV）；`ra` 栈保存须逐位（含 `ra0` 元数据字）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~**信号帧的 uapi 布局**~~ **已移交 `m14-linux-046 信号帧与投递`**（本任务不再定义帧）。**帧定义以 046 为准，且被用户 2026-11-20 的后续裁定更新**：2048 B、`rd[0]` = `status`（软件容器，低 4 位模式；**不是**硬件 status 寄存器）、`rb[0]` = `ip`、`ra[64]`/`rf[64]` 全量、匿名 union 表达；**11-17 那句「删除 `status`」已被 11-20 的「`status` 替代 `rd[0]`」取代**（见 `discussing.md` N30）。以下为 11-17 原文，仅作沿革留存：`user_regs_struct` = **`rd[64]` / `rb[64]` / `ra[64]` / `rf[64]`**，共 **2048 B**；**删除 `status`**（DADAO 无 status 寄存器）；**`rb[0]` 充当 IP**（只读寄存器的数据副本），不另设 `ip` 字段；`sigcontext` 直接引用。落地三条硬断言：① 帧内 `rb[0] == 异常时的 ip`（内核组装时不能沿用 `pt_regs.rb[0]=0` 的占位）；② `rt_sigreturn` 用 `rb[0]` 决定返回 IP、`rb1..63` 写回寄存器，**不得写 `rb0` 寄存器**（只读，写 ⇒ `ILLI`）；③ 编译期断言 `sizeof==2048` 与各段偏移（`rb=512`、`ra=1024`、`rf=1536`）。musl 侧 `mcontext_t`/`MC_PC` 按 `rb[0]` 槽对齐。术语一律用 IP，不用 PC。

## 审阅记录

### 第 1 轮 engineer 自审

**结论**：全部 finding 已处置，任务置 `待验收`。

- **自审范围**：`fault.c`/`traps.c`/`entry_common.c`/`trap.S`/`k5_signal_selftest.c`/`ptrace.h`/`setup.h`/`uapi/asm/unistd.h`/`Makefile.syscalls`/`Kconfig.debug` + 探针 `k5_signal_probe.py` + `changelog.md`；逐行核对了「SEGV 策略→交接收尾→向量发布→用户恢复」的四段闭环与 S1/S5/S6 的每条断言是否可达 FAIL（每 case 都有一个「不应到达」的退出码或一个必须为真的读数）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 交接路径只 `force_sig()` 不消费 `TIF_SIGPENDING`：用户态同一缺页被重试 4 次后撞预算、仍具名终止 | ✅已修 | 新增 `entry_common.c::dadao_user_fault_return()`（`enter_from_user_mode` + 工作循环 + 发布 `frame->ip`），`trap.S` 交接返回处调用 | S1 两相从「具名终止」变 `exit_code&0x7f=11` 且启动 rc=0；`pf-stays-fatal` 注入反向证明（退码 0xC1） |
| 兄弟线程的心跳循环永不让出 CPU（无 tick、纯用户态）⇒ 组长饿死、S5 挂到 QEMU 超时 | ✅已修 | 心跳钩子里 `schedule()`（附「为何只有这一处能让出」的注释） | S5 七条断言全绿；日志 `s5 leader: clone=0x17 hb=11` 证明交接次序 |
| `getrlimit/setrlimit`（163/164）答 `-ENOSYS`：`rlimit` ABI 组未启用，而 argmask 早已登记两号 | ✅已修 | 新增 `arch/dadao/kernel/Makefile.syscalls`（`syscall_abis_64 += rlimit`）+ uapi `__ARCH_WANT_SET_GET_RLIMIT`；不引入新号 | S6 12 条全绿（`set/get=0`、`cur=max=0x50000`、子进程读回同值） |
| `wait4` 状态是 `int`，大端下 64 位读把 `0x5500` 读成 `0x5500_0000_0000` | ✅已修 | 新增 `m46_read_report32()` 并改用它 | `s6-wait-status-sigsegv want=0xb got=0xb` |
| 越界目标地址一度按 `+4P-limit-2P` 混算（差 4 页，会落进界内） | ✅已修 | 改为 `M46_STACK2_VA - M46_ST_LIMIT - 2*PAGE_SIZE`（与 `acct_stack_growth()` 的 `size=vm_end-address` 同口径） | `grows` 0→1、越界那次不动；`over-limit-refused` 绿 |
| `ADWBFAIL`/`NONPTW` 这类机器级读数的 `cause_info` 不是用户 VA，却被当作 `si_addr` | ❌不修（披露） | — | 两路是机器故障（Linux 给 SIGBUS），本任务范围是「无 VMA/越权/die-perm」；探针不覆盖，已记入「遗留问题」 |
| `exit-noop` 注入会让**所有**以 `exit` 收尾的阶段一起红（不只 S5） | ❌不修（披露） | — | `exit` 是每个脚本的收尾，注入必然波及；探针按「红 / 挂死 ⇒ 该 case 红」判定，实测 `rc=124 hung=True` |

**旁证**：证据脚本 36 项全绿（`RESULT: PASS`）；源树注入后 `git status --porcelain` 为空、`apply_series` 第二次为 no-op。

### 第 1 轮 reviewer 验收

**判决：Accepted**（大改档 60 min；下列命令与输出均为 reviewer 本人执行，长输出留复核临时目录，此处只贴判据行）

- **探针全量**：`python3 tools/linux/k5_signal_probe.py` ⇒ `k5_signal_probe: 157/157 passed`、**rc=0**、`grep -c "^\[FAIL\]"` = **0**；`--selfcheck` **rc=0**（坏控制台翻出 73 条红）。8 路注入逐路「注入红 → 还原 md5 对账 → 重建 → 回绿」全 PASS（`exit-noop rc=124 hung=True`、`pf-stays-fatal rc=193`、`fork-keeps-rlimit` 红 4 项），与完成区披露一致。
- **s1/s5/s6 抽读**：s1 两读数 `die-no-vma`/`die-perm`、阶段 3/4 = `(32, 0xb, 0)` 且启动继续；s5 `exit(0)` 退码 0、组长 `exit_group(0)` 后兄弟 tid 消失且 `hb` 冻结（`group-sibling-gone`/`group-sibling-stopped` 绿）；s6 `cur=max=0x50000`、`child-inherited-*` 同值、`in-limit-growth=1`、`wait-status-sigsegv=0xb`、`over-limit-refused` `grows 0→1`。
- **独立注入 A（自写改法，非 `--inject`）**：源树 `mm/fault.c` 删掉用户态投递块 ⇒ `--no-inject` **rc=1、33 条 FAIL**，控制台 `K4 umon->smon: the channel did not install a mapping (policy=1)`、**启动 rc=193（0xC1 具名终止）**、阶段止于 0/1/2 ⇒ **s1 红**；`cp`+md5 还原 = `6b6808f406905d2ac4f4fcd81a0df2d3`（与注入前相等），源树 `git status` 干净。
- **独立注入 B（自写改法）**：源树 `kernel/fork.c` 加 `sig->rlim[RLIMIT_STACK].rlim_cur = 8UL << 20` ⇒ **rc=1**，红项 `s6-child-inherited-cur`/`s6-wait-status-sigsegv`/`s6-wait-status-no-exit`/`s6-over-limit-refused`，内核退码 `0x78` ⇒ **s6 红**；`cp`+md5 还原 = `dd68c275d40f2961f26ca900c66009f0`（相等），源树干净。两路还原后合并回绿：`--no-inject` ⇒ **117/117、rc=0**。
- **门控**：`check-patch-tree` 首跑 **rc=2**（`linux: assertion ⑦: worktree is not clean: M kernel/fork.c` —— reviewer 在探针注入窗口内并发跑所致，属环境干扰），**重试 1/1 ⇒ rc=0**（`11 patch set(s), 452 patches OK`，linux 段 **103** 篇）；`check-config-pins`、`check-contracts-dir`、`check-contract-relocs`、`check-knowledge-refs`、`check-index-blobs` 各 **rc=0**；`apply_series --component linux` **rc=0** 且 `linux already applied (base+1, matches patches); skipped`。
- **回归（独立重跑 2 个）**：`k4_fork_probe.py` **rc=0（104/104）**、`k5_syscall_probe.py` **rc=0（104/104）**；`check-linux-k0/-k1/-k2/-k3` 与 `m45_entry_probe` **未独立重跑**，核 engineer 日志分别为 `146/146`、`112/112`、`170/170`、`263/263`、`51/51` PASS。
- **语义抽读（代码级）**：`mm/fault.c` 仅 `policy == DADAO_PF_FATAL && from_user` 改投 `force_sig_fault(SIGSEGV, die-perm ? SEGV_ACCERR : SEGV_MAPERR, info)`，内核态保持 `DADAO_PF_FATAL`；`traps.c` 的 `DADAO_PF_SEGV` 分支只 `return DADAO_TRAP_RESUME_SKIP`（不在 smon 静态帧 `do_exit`）；`entry_common.c::dadao_user_fault_return()` = `enter_from_user_mode` + `irqentry_exit_to_user_mode_prepare`（→ `exit_to_user_mode_loop` 消费 `TIF_SIGPENDING`）+ 收尾后才写 `UMON_RC_EXCP_VECTOR, regs->ip`，`trap.S` 交接返回处调用它；`syscall.tbl` 93/94 与 163/164 + uapi `__ARCH_WANT_SET_GET_RLIMIT` + 新 `arch/dadao/kernel/Makefile.syscalls`（由 `scripts/Makefile.asm-headers` 引入，机制可达）。
- **越界核验**：`traps.c`/`entry_common.c`/`trap.S` 不在预计清单，但为 S1 必需（交接路径没有回用户态收尾 ⇒ 撞重试预算后仍具名终止，engineer 自审有反证），且未触碰禁改面（`spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile` 均未动）；`kernel/syscalls.c` 未改属替代实现（setrlimit 面 = uapi + `Makefile.syscalls`），163/164 实测可用，与目标 4 等价。任务书 diff 只动「状态 + 审阅记录 + 完成区」，验收标准与硬约束未被改写。
- **finding（不阻断，交 architect 收尾改）**：完成区写 `k5_syscall_probe.py 62/62`，reviewer 实测与 engineer 日志均为 **104/104** —— 文档数字笔误，不影响 rc=0 判据。

## 完成区

**测试结果**：运行期证据目录的 `run.sh` **36/36 项 PASS（`RESULT: PASS`）**；`k5_signal_probe.py` **157/157**（046 的 76 条基线不回退 + s1/s5/s6 新增 41 条），`--selfcheck` PASS，**8 路注入**（5 旧 + 3 新：`pf-stays-fatal`/`exit-noop`/`fork-keeps-rlimit`）逐路「注入红 → `cp`+md5 还原 → 重建 → 回绿」。

**修改文件**：`components/linux/patches/arch/dadao/mm/fault.c.patch`、`.../kernel/{traps.c,entry_common.c,trap.S,k5_signal_selftest.c}.patch`、`.../include/{asm/ptrace.h,asm/setup.h}.patch`、`.../include/uapi/asm/unistd.h.patch`、新 `.../kernel/Makefile.syscalls.patch`、`.../Kconfig.debug.patch`、`components/linux/{series,changelog.md}`、`tools/linux/k5_signal_probe.py`。**越界披露**：任务书预计清单里的 `kernel/syscalls.c` **未改**（`setrlimit` 面落在 uapi + `Makefile.syscalls`，属更小的改动）；`kernel/{traps.c,entry_common.c,trap.S}` 不在预计清单，但 SIGSEGV 的投递必须在交接路径的回用户态收尾里做（在 smon 静态帧里 `do_exit()` 会跨睡眠，非法）。

**验收结果**：`check-linux-k0/-k1/-k2/-k3` rc=0；`k5_syscall_probe.py` 62/62、`k4_fork_probe.py`、`m45_entry_probe.py` rc=0；`check-patch-tree`/`check-config-pins`/`check-contracts-dir`/`check-contract-relocs`/`check-knowledge-refs` rc=0；`apply_series --component linux` 第二次 no-op。S1：`die-no-vma`/`die-perm` 两读数均 `exit_code&0x7f=11`、无 exit status、启动继续（旧行为 0xC1 具名终止已由注入证明被替换）。S5：`exit(0)` 退码 0；组长 `exit_group(0)` 后克隆兄弟的 tid 消失且心跳冻结（`hb=11→11`）。S6：`setrlimit(5 页)`→`getrlimit` 读回、fork 子读回同值、界内长一页 / 界外 SIGSEGV（`wait4` 状态 `WTERMSIG=11`）。

**新发现/坑**：① 交接路径原本没有回用户态的收尾（没有 `enter/exit_from_user_mode`、没有 `_TIF_WORK_MASK`），只 `force_sig()` 会无限重缺页；② smon 帧是静态帧 + `dadao_trap_busy`，睡眠期间别的任务的 supv 异常会判「recursive supv exception」⇒ 致命信号的 `do_exit` 只能放在 umon 帧的收尾里；③ 本端口原本没有 `getrlimit/setrlimit`（`rlimit` ABI 组缺失），`syscall_argmask.c` 却早已按地址参数登记 ⇒ 补 ABI 组而非改号；④ `wait4` 状态是 `int` + 本机大端 ⇒ 必须按 32 位读；⑤ 只在用户态跑 `trap` 的任务不会被抢占（时钟已停、异步帧不能跨切换）⇒ 探针的对交必须显式让出或阻塞；⑥ 扩栈上限按 `size = vm_end - address` 与 `RLIMIT_STACK` 同单位比较，无邻居时 `stack_guard_gap`（256 页）不是约束；⑦ 同一 worktree 里并发跑两个探针（或一个被杀后残留 QEMU）会污染共享构建树，表现为「ABI 像是错位」的假失败 —— 清空构建树重建即恢复（应在派单规则里强调「同组件同写者」也含同 worktree 的并发跑批）。

**遗留问题**：① `ADWBFAIL`/`NONPTW` 两路机器级读数的 `si_addr` 仍是 `cause_info` 原值（Linux 语义应给 SIGBUS）；属机器故障路径，本任务范围外，登记待续。② 本 worktree 的组件源树只有 `qemu` 的 `linux-user/riscv/syscall.tbl` 快照（023 探针的独立 oracle，sha256 与 `contract-syscall §1.2` 一致），四载体比对门控 `check-syscall-abi` 需要完整 qemu 源树，未纳入本次证据。

