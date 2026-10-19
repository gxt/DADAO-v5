# QEMU-065t: qemu-user 线程语义（线程链 T2）

**模块**：qemu
**项目里程碑**：M9
**依赖**：`INFRA-095t`（T1：musl `__clone` + TP，**必须已验证**）、`QEMU-062t`（DADAO linux-user 后端，已验证）、`QEMU-063t`（宿主信号诊断，已验证）
**状态**：待验收

> **编号（现场取号，2026-10-19）**：`qemu` 现存最大 = `QEMU-064t` ⇒ 取 **`065`**（`grep -rn 'QEMU-065' .tao/` 0 命中）。
> **线程链位置（T2）**：串行链 **T1 `INFRA-095t` → T2 `QEMU-065t` → T3 `TESTCASES-052t` → T4 `LLVM-100t` → T5 `LLVM-117t`**。本册只做 **qemu-user（linux-user）**；**不做** system 模式（`-M dadao-m1`）线程。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（先读，勿重复查证）

- **guest `clone` 已走通用 linux-user 线程路径**：`linux-user/syscall.c` 的 `do_fork` 在 `CLONE_VM` 下 `cpu_copy` 新 env、`begin_parallel_context`、`pthread_create(clone_func)`；`cpu_clone_regs_child` 设 `newsp→rb1` + `rd8=0`；父侧 `cpu_clone_regs_parent` 为空、`rd8` 保留 tid。
- **`CLONE_SETTLS` 已接 `rb3`**：`linux-user/syscall.c:7056`（线程路径）与 `:7146`（fork 路径）调 `cpu_set_tls(new_env,newtls)`；`linux-user/dadao/target_cpu.h:26` = `env->rb[3] = newtls`；`get_sp_from_cpustate` = `rb1`。
- **clone 参数掩码已对**：`linux-user/dadao/cpu_loop.c:343` `case TARGET_NR_clone` = `0x14`（地址槽 2/4 = `parent_tidptr`/`child_tidptr`）；`dadao_syscall()` 按掩码从 `rd16+`/`rb16+` 重建参数；`contract-syscall §3`。
- **futex / exit 走通用实现**：`linux-user/syscall.c:13628` `TARGET_NR_futex` → `do_sys_futex`（宿主 `SYS_futex`）；`:9783` `TARGET_NR_exit` 在多线程下做**线程终止**（`child_tidptr` futex wake + `cpu_loop_exit`），`:11745` `TARGET_NR_exit_group` → 宿主 `exit_group`。
- **信号面已有 DADAO 帧**：`linux-user/dadao/signal.c` 的 `target_rt_sigframe` / `setup_rt_frame` / `do_rt_sigreturn`；`mcontext` 形状 = `{pc, rd[64], rb[64]}`（与 musl `bits/signal.h` 的 `__gregs[129]` 对齐）。**已知限制（现场注释）**：帧**不保存 RAS**（`ra/ras_base`）⇒ 在调用中途收到信号、`sigreturn` 后返回链可能不完整；本册必须在探针中如实暴露，不得假设一定可用。
- **musl 侧消费**（T1 产出，本册不改）：`pthread_create` 用 `CLONE_VM|CLONE_THREAD|...|CLONE_SETTLS`；`__pthread_exit` 走 `SYS_exit`；`exit()` 走 `SYS_exit_group`。
- **范围边界**：system 模式 `dadao-m1` 已于 `QEMU-060t` 回退为 semihosting-only，**无线程/无 syscall 服务**；本册判据全部在 `qemu-dadao`（user-mode）。

## 接口规范

- **输入**：
  - T1 的两档运行产物（静态 `libc.a` + `crt1.o`、动态 `libc.so` + `ld-musl-dadao.so.1`）与 C1/C2 探针源；
  - `components/qemu/patches/linux-user/**`（现状；若需修，按 `docs/Process-01` 一文件一补丁 + `series` + `changelog.md`）；
  - `manifests/components.lock.toml` 的 `qemu` 条目（commit 身份）；安装根 `qemu-dadao`。
- **输出**：
  1. 线程语义探针与结果（两档）：并发互斥计数、`CLONE_SETTLS`→`rb3`、futex、`exit` vs `exit_group`、per-thread 信号 + `sigaltstack`；
  2. 若发现 qemu 缺口 ⇒ **最小**补丁（优先 `linux-user/dadao/**`；通用 `linux-user/syscall.c` 仅在 DADAO 特有分支/掩码有误时改，且披露）+ `changelog.md`；
  3. `.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项 rc、含 `--inject`）+ 日志 `.work/log/qemu/QEMU-065t-*.log`；
  4. 本册完成区（≤30 行）。
- **约束（硬）**：
  - **前置安装根**：`make install-host` 已完成且新鲜（`qemu-dadao --version` + 时间戳）；若本册改 `components/qemu/**` ⇒ 重建后**必须**重跑 `install-host` 再跑判据（`ISS-210`）；
  - **不改** `components/musl/**`、`components/llvm-project/**`、`spec/`、`contracts/`、`.tao/contracts/**`；
  - **不改** system 模式语义；`check-qemu-semantics` / `check-qemu-smoke` 必须保持绿；
  - 改 `components/qemu/**` ⇒ **必须单跑 `make install-host`**（先申报耗时；`JOBS=8`、禁全核；不得与其它 L2/L3 并发 —— `ISS-229`/`ISS-210`）；
  - 探针超时必须显式（`timeout <N>`），**124 判 FAIL**，不得无限等待；
  - 期望值独立：并发总数 = 线程数 × 每线程次数（算术手算）；`rb3` = T1 传入的常量；不得从 qemu 内部状态反推。

## 做

### 阶段 0：前置与基线

- 断言 T1 已完成（`libc.a`/`libc.so` 的 `__clone` 来自 arch `clone.s`，C1/C2 探针默认通过）；安装根 `qemu-dadao` 新鲜（贴 `--version` + 时间戳）。
- 复跑 T1 C1/C2（静态 + 动态）作为基线；记录 rc。

### 阶段 A：并发 / futex

- 探针 `concurrent.c`：`N=4` 线程 × `M=250000` 次 `pthread_mutex_lock/unlock` 保护的自增；期望 **`N*M`**（独立算术 oracle）；主线程 join 全部后打印总值。跑 **5 轮**，每轮 `timeout 120`；5/5 必须等于 `N*M`、exit 0、无超时。
- 探针 `condvar.c`：1 个 waiter + 1 个 signaler（`pthread_cond_wait/signal`，内部走 futex）+ 1 个 `pthread_cond_broadcast` 两 waiter 场景；期望两个 waiter 都被唤醒、计数 = 2。
- 若出现挂死/宿主信号：保留现场（日志 + `timeout` rc），按 `ISS-255/257` 同族归因；**不得**用「重跑一次就过」掩盖。

### 阶段 B：`CLONE_SETTLS` → `rb3`

- **静态档（硬判据）**：复用 T1 C2：直接 `__clone(func, stack, flags|CLONE_SETTLS, arg, ..., tls=0x5a5a0000, ...)`，子线程 `__get_tp()` 写回；父断言 **逐位相等**。跑 3 次（排除偶然）。**依据**：`__clone` 在 `pthread_impl.h:160` 为 `hidden` ⇒ 动态档不可直接调用，故直接探针只在静态档。
- **动态档（一致性）**：`pthread_create` 子线程 `__get_tp()` 与 `pthread_self()` 的差 = `sizeof(struct pthread)+TP_OFFSET`（`TP_OFFSET=0`）；同一子线程内恒定、不同线程不同。该检查**不冒充独立 oracle**（独立 oracle = 静态档常量）。

### 阶段 C：`exit` vs `exit_group`

- 探针 `thread_exit.c`：worker 调 `pthread_exit((void*)0x1234)`；主线程 `pthread_join` 拿到 `0x1234`，进程继续并 exit 0 ⇒ 证明 `SYS_exit` 只终止线程。
- 探针 `group_exit.c`：worker 调 `exit(7)`（musl `exit` = `exit_group`）；整个进程 exit **7**（主线程不得继续打印「after」）。两档各跑；用 shell `$?` 判 7。
- 对照：`_exit(7)` 同样 exit_group；`pthread_exit` 后主线程再 `exit(0)`。

### 阶段 D：per-thread 信号 + `sigaltstack`

- 探针 `signals.c`：2 个 worker，各自：
  1. `sigaltstack()` 安装**自己的** 8 KiB 栈（`SS_ONSTACK` 可读）；
  2. `sigaction(SIGUSR1, SA_ONSTACK|SA_SIGINFO)` 处理器记录 `si_pid`、`pthread_self()`、`ss_sp` 范围；
  3. `pthread_kill(pthread_self(), SIGUSR1)` ⇒ 处理器在**自己的** altstack 上运行；
  4. 一个线程 `pthread_sigmask(SIG_BLOCK, SIGUSR1)`，另一个 `pthread_kill` 它 ⇒ 被阻塞的线程不运行处理器，解除阻塞后才运行（per-thread mask）。
- 期望：两线程各自处理器命中 1 次、`ss_sp` 落在各自 altstack 范围、进程未因信号终止、exit 0。
- **已知限制处置**：若失败根因 = `signal.c` 不保存 RAS（帧注释已声明）⇒ 先判断能否用「处理器内不返回调用链 / 仅顶层 handler」规避；**不能**把「信号在调用中途收不到/返回错」写成 pass。若必须补 RAS 保存，属 qemu 信号帧最小修复（须改 `signal.c` + `target_sigframe` 布局并与 musl `bits/signal.h` 对齐；`bits/signal.h` 在 musl 面，**本册不改** ⇒ 若需同步改 musl，**停下报告**，交 user 裁定/另立册）。
- 可选补充：`tgkill` 定向到指定线程（`SYS_tgkill`）与 `pthread_kill` 同判据。

### 阶段 E：修复（仅当 A–D 暴露 qemu 缺口）

- 只做**最小**修复：参数掩码/寄存器映射（`cpu_loop.c`、`target_cpu.h`）、clone 后 `rb3`/`rd8`、线程退出唤醒、信号帧字段。每处附「现状失败签名 → 修后签名」。
- 改 `components/qemu/**` 后：`make build-qemu JOBS=8` → `make install-host` → 复跑 A–D + `check-qemu-semantics`/`check-qemu-smoke`；更新 `components/qemu/changelog.md` 的 M9 节。

### 阶段 F：证据与门控

- `.work/evidence/<任务ID>/run.sh`，**≥2 条可达 FAIL**：
  1. `--inject` 把 `CLONE_SETTLS` 分支临时短路（临时树）⇒ C2/B 的 `rb3` 断言 FAIL；`cp`+md5 还原 ⇒ 回绿；
  2. 把并发期望改为 `N*M+1`（测试侧注入）⇒ 计数断言 FAIL；还原 ⇒ 回绿；
  3. 可选：`thread_exit` 改成 `exit` ⇒ `pthread_join` 场景 FAIL（证明两者判据可区分）。
- 门控各留自身 rc：`make check`（L1）、`check-qemu-semantics`、`check-qemu-smoke`、`check-patch-tree`、`check-component-changelog`、`check-source-state`、`check-no-residue`、`check-tasks`、`python3 tools/infra/check_issues.py`；任务收尾跑 `make check-modules`（L2，串行）。

## 验收标准

1. **T1 程序两档**：静态 + 动态的 C1/C2 在 `qemu-dadao` 均通过（贴 rc/输出）；无 `timeout`。
2. **并发/futex**：4×250000 互斥计数 5/5 轮 = **1,000,000**；condvar 两 waiter 均被唤醒；每轮 `timeout` rc≠124；日志完整。
3. **`CLONE_SETTLS`**：**静态档**直接 `__clone` 的 `tls` 常量与子线程 `__get_tp()` **逐位相等**（3/3，独立 oracle）；**动态档** `pthread_create` 子线程满足 `__get_tp() - pthread_self() == sizeof(struct pthread)`（一致性，非独立 oracle）。
4. **`exit` vs `exit_group`**：`pthread_exit` 只终止线程且 join 得到传入值、主进程 exit 0；worker `exit(7)` ⇒ 整个进程 rc=7；两者输出可区分。
5. **per-thread 信号 + `sigaltstack`**：2 线程各自处理器命中、altstack 范围正确、阻塞掩码 per-thread 生效、进程 exit 0；若有 RAS 限制，按「已知限制」显式记录并以可判失败呈现（不得静默）。
6. **无回归**：`check-qemu-semantics`、`check-qemu-smoke` 与 `make check`（L1）rc=0；若改 qemu，`install-host` 后复跑并留安装根新鲜证据。
7. **可达 FAIL ≥2**：证据脚本 `--inject` 至少两条断言「注入→FAIL→`cp`+md5 还原→回绿」；禁恒真、禁 `git checkout/restore/stash`。
8. **边界**：只动 qemu 面（+本册/证据）；`components/musl/**`、`components/llvm-project/**`、`spec/`、`contracts/`、`.tao/contracts/**` 0 改动；不提交 git、不 push；完成区 ≤30 行并与真实输出逐条对齐。

## 不做项（显式）

1. **musl `__clone` 实现** ✗ —— T1 `INFRA-095t`（本册只消费）。
2. **`__thread` / 动态 TLS / `dlopen`** ✗ —— T4 `LLVM-100t` / T5 `LLVM-117t`。
3. **047t 用例计数收口与 `ISS-252` 关闭** ✗ —— T3 `TESTCASES-052t`。
4. **system 模式（`dadao-m1`）线程** ✗ —— 该运行时已回退；无内核目标（`ADR-0025 D2`）。
5. **`pthread_cancel` 完整取消语义** ✗ —— 依赖信号帧 + `__cp_begin/__cp_end`；本册只验信号送达/altstack，不承诺取消一定触发（`bits/signal.h` 仍 `[OPEN]`）。
6. **`spec/` / 契约 / 重定位编号 / musl ABI 帧** ✗（改须用户裁定 + ADR）。

## 完成区
**测试结果**：证据 `.work/evidence/QEMU-065t/run.sh`：**33 PASS / 12 FAIL**（12 FAIL 全为下述两项真实缺口；`--inject` 3/3 PASS）。C1 static/dynamic exit=0（`join=0 shared=41 ret=42 child_errno=1234 parent_errno=77`）；**ISS-293 未转 pass**：`functional/snprintf`（静态）/`functional/strtod`（动态）仍 `qemu killed by host signal 4`（SIGILL）；并发 **5/5 轮 rc=124**（timeout 120，4×250000 互斥计数，无输出）；A 辅助：4×250000 各自槽求和 `sum=1000000`、condvar `signal 1/1 + broadcast 2/2`；B：静态 3/3 `child_tp=0x5a5a0000 == tls`（父 TP 不变）、动态两线程 `delta=200 == sizeof(pthread)+0`；C：`join=0 ret=0x1234 after_exit_ran=0`、worker `exit(7)` ⇒ 进程 **rc=7** 且无 `AFTER`；D：两线程各自 altstack（sp `0x52ab0∈[0x51000,0x53000)`、`0x54ab0∈[0x53000,0x55000)`）、`si_pid=getpid`、`si_code=-6`、`si_signo=10`、阻塞窗口 `cnt=1`→解阻塞 `2`、`tgkill` 仅命中目标线程；RAS 诊断（3 层调用链 + handler 内调用）**未复现损坏**（帧仍不保存 RAS）。
**修改文件**：本册（完成区 + 自审）；`.work/evidence/QEMU-065t/run.sh`（新增）；`.work/log/{qemu,testcases}/QEMU-065t-*.log`。**`components/qemu/**`、`tools/qemu/**`、`tests/vectors/**` 0 改动**（无补丁、无 changelog）。
**验收结果**：`check-qemu-semantics` **224/224** rc=0、`check-qemu-smoke` **90/90** rc=0；047t 抽样 static **10/10**、dynamic **10/10**；安装根 qemu md5 `4938a733…` == 构建树（`v11.1.1-1-gfb8e4f8`）；`check-patch-tree` rc=0（5 组件 **183** patches，**未变化**）、`check-component-changelog`/`check-source-state`/`check-index-blobs`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-run-artifacts`/`check_issues` 均 rc=0；`make check`（L1）rc=0。
**新发现/坑**：① **ISS-293 根因不是旧测试 ELF**：`compiler-rt` builtins 归档陈旧（安装根==构建树 `d0a81c89…`，mtime 2026-10-18 20:36，早于 LLVM-116t 的编码迁移）；`extenddftf2.c.o` 内仍有**已废止 `shl` 编码 `0x40505146`**（ha=0x14，`llvm-objdump` 显示 `<unknown>`）×3，而现 clang 发 `shl.o` = `40 40 84 11`（ha=0x10）⇒ 新 qemu 按 UNDI→SIGILL。修法 = 重建 compiler-rt builtins + `install-host`（本册禁跑）⇒ **ISS-293 保持 open**，不得按「旧 ELF 重建即消失」关闭。② **并发缺口在 musl 而非 qemu**：`arch/dadao/atomic_arch.h` 的 `a_cas` 是**普通 load/compare/store**（文件头自称 `SINGLE-THREADED, NOT REAL ATOMICS`，并写明「多线程可达后必须替换」）⇒ 4×250000 丢更新/挂死；小规模实测（`.work/log/qemu/QEMU-065t-atomicity-probe.log`）`1×200000` 精确 3/3、`2×2000` 3/3 侥幸精确、`3×2000 → 5999/5992/5999`（3/3 丢更新）、`4×2000 → 3/3 rc=124`。ISA 侧无可用原子（LR-SC/`fence` 均 `scope: excluded`，`contract-isa §14`），故**无法在 T2 范围内最小修复**。③ 空转等待循环会被 DCE（`for(i=0;i<2e9;i++);` 被删）⇒ 探针须用 volatile（首版 `group_exit` 因此误报 `AFTER`，已修）。④ 手写 asm 读 `rb1`/`rb3` 必须 `register ... __asm__("rd8")` 绑定，否则 `"=r"` 可能落别的 RD（首版信号探针 sp 读出 0/常量）。
**遗留问题**：① **阻断派单验收项 2（并发 == N×M）**：需用户/架构师裁定线程原子性路径（实现 LR-SC/fence 并改 `scope` + 契约/ADR，或指定串行化模型），随后补 musl `atomic_arch.h`（本册禁改 musl）——建议另立 T1b 册。② `ISS-293` 保持 open：需重建 compiler-rt builtins + `install-host` 后复核（本册禁跑 install-host）。③ `ISS-255` 仍复现（`regression/flockfile-list` 宿主 SIGBUS=7、`regression/setenv-oom` 宿主 SIGTRAP=5），另 `regression/raise-race` 现已 **PASS**；未写台账（越界）。④ 未跑 `install-host`/L2/L3、未 commit/push、未改 `**状态**`（按派单）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（`subagent_depth=1`，无嵌套子代理）：核对 A–D 各探针的断言可达 FAIL、oracle 独立性（B 静态 = 常量、动态 = ABI 一致性）、信号 handler 无 libc 调用、注入以 `cp`+md5 还原（未用 git）；逐条排查「空循环被 DCE」「asm 输出寄存器未绑定」「期望值与被传值同源」三类假绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `group_exit` 主线程 2e9 空循环被优化掉 ⇒ 误报 `AFTER` | ✅已修 | `group_exit.c` 改 volatile `spin` + `worker_exiting` 同步 | 3/3 单跑 rc=7 无 `AFTER`；证据 default C 段 PASS |
| 注入 2 原设计改 `TLS_CONST` 不产生失配（期望与被传同源） | ✅已修 | 改为传 `TLS_CONST + 0x1000` | inj2 rc=3 + `FAIL: child rb3 != tls argument`，还原 md5 一致 |
| 读 `rb1`/`rb3` 用 `"=r"` 未绑定 `rd8` ⇒ 读到错值 | ✅已修 | `register ... __asm__("rd8")` | 信号 sp 落在各自 altstack 范围 |
| `--inject` 仍跑全量（含 5×120 s 挂死轮） | ✅已修 | MODE 提前分流为 quick 模式 | `--inject` 3/3 PASS，耗时 <1 min |
| 并发断言是否可达 FAIL（防恒真） | ✅已证 | 无（真实缺口） | 5/5 rc=124；`4×2000` 丢更新、`2×2000` 丢更新各 1 次 |
| 本册无 qemu 补丁（183 不变） | ⏸延后（证据指向 musl/ISA，非 qemu） | 无 | `check-patch-tree` 183 OK；musl `atomic_arch.h` 头注 + `contract-isa §14` |

判决：可修 finding 均已处置；**并发原子性缺口不在本册可改范围**（musl/ISA 裁定），故完成区如实登记为阻断项，状态按派单保持 `待开始`。

#### 第 1 轮 reviewer 验收

#### 提交审核（architect）

- **档位**：正常提交（按派单给定信息）。**未 push**。
- **提交**：本笔（`QEMU-065t/T2：qemu-user 线程语义验证 …`；`git log -1 --format=%h`）；显式 staging **3 路径**，未用 `git add -A`。
- **对账（对完成区「修改文件」）**：本册（完成区 + 第 1 轮自审 + 本记录）、`issues.yaml`（新 `ISS-294` = ISA 缺原子原语）、`milestones.md`（本任务状态 `待开始`→`待验收` + 未完成册行）✓；`.work/evidence/QEMU-065t/run.sh`、`.work/log/{qemu,testcases}/QEMU-065t-*.log` 属忽略区不入 git（完成区已列）✓；完成区声明 `components/qemu/**`、`tools/qemu/**`、`tests/vectors/**` 0 改动 ⇒ 未提 ✓。**无漏提 / 多提 / 越界**。
- **台账联动**：完成区遗留①（并发原子性）原「未写台账（越界）」⇒ 本次由 architect 登记 `ISS-294`（`open`/`P1`/`scope:[spec]`），指向 T3/T4 阻塞关系与 (A) ISA 原子原语 / (B) ADR 单核假设 二选一待裁。完成区原文未改（只改 `**状态**`）。
