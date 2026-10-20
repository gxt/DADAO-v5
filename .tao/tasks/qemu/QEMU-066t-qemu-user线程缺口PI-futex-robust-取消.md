# QEMU-066t: qemu-user 线程缺口三条（PI futex / robust list / 取消被重启）

**模块**：qemu
**项目里程碑**：M9
**依赖**：`INFRA-095t`（T1：musl `__clone` + TP，返工后 `rb3` 仅 `CLONE_SETTLS` 时写）、`QEMU-065t`（T2：qemu-user 线程语义）、`TESTCASES-052t`（T3：pthread 度量与 `ISS-295`~`ISS-299` 现场）；三者须**已验证**（或主会话明确放行）
**状态**：待验收

> **编号（现场取号，2026-10-20）**：`qemu` 现存最大 = `QEMU-065t` ⇒ 取 **`066`**（`grep -rn 'QEMU-066' .tao/ components/` 0 命中）。
> **链上位置**：T3 的 19 例目标残留 **4 例**全部落在本册；本册完成后 T3 才能达到 **19/19**（`TESTCASES-052t` 仍按它自己的册收口，本册**不改**其状态/判据）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（先读，勿重复查证）

**现场（`TESTCASES-052t-rerun`，2026-10-20，前置 `c47c9b7`；两档各 3 跑一致 + 修 `ISS-299` 后各 1 跑复核）**：19 目标两档均 **15 pass / 3 fail / 1 blocked**；残余 4 例逐条根因如下（原因与 `TESTCASES-052t` 首轮一致，未变）：

1. **`ISS-296`｜`functional/pthread_mutex_pi`（两档 fail）**：`pthread_mutex_pi.c:148: PTHREAD_MUTEX_ERRORCHECK relock did not return EDEADLK, got deadlock`。`qemu-dadao -strace` 现场 = 子线程 `futex(uaddr, FUTEX_LOCK_PI, …)` 返回 **`-1 ESRCH`**（errno 3）；musl 的 PI 慢路径（`musl/src/thread/pthread_mutex_timedlock.c:21-55`）对 `ESRCH` 落到 `__timedwait` 兜底 ⇒ 100 ms 超时 ⇒ 用例判 deadlock（返回值 `-1`）。
   - **内核侧语义（`linux/kernel/futex/pi.c:375-418` `handle_exit_race`）**：`FUTEX_LOCK_PI` 的 `ESRCH` 只在「`uaddr` 里的 owner PID 在宿主找不到可 attach 的 task」时返回（重读 `uaddr` 值仍相等 ⇒ 判定用户态值是 bogus）。**因此必须先定位 `_m_lock` 里的值与当前宿主 tid 的关系**，再定修法。
   - **未确认假设**（`ISS-296` 登记原文，**不得**当结论直接用）：「PI futex 的 owner 是 guest TID，宿主找不到该 TID」。**反证材料**：本端口 `gettid`/`set_tid_address` 直接返回宿主 tid（`linux-user/syscall.c:13212-13213`、`:13535-13542`），`clone` 路径父侧返回 `info.tid`（`:7088`）⇒ guest tid **看起来**等于宿主 tid。**探针须先把这三处对齐后再结论**（见「做·阶段 A」）。
2. **`ISS-297`｜`functional/pthread_robust`（blocked：60 s 超时）+ `regression/pthread-robust-detach`（fail：`timedlock … got 110 ETIMEDOUT want 130 EOWNERDEAD`，两档）**：`pthread_mutexattr_setrobust()` 返回 `38 ENOSYS`。根因 = `linux-user/syscall.c:13552-13568`：`TARGET_NR_set_robust_list` / `TARGET_NR_get_robust_list` **按上游设计**直接 `-TARGET_ENOSYS`（注释：robust 链表在宿主不合法、且无法可靠拦截线程死亡）；musl 的 `pthread_mutexattr_setrobust`（`musl/src/thread/pthread_mutexattr_setrobust.c`）以 `SYS_get_robust_list` 探测内核支持，`ENOSYS` ⇒ robust 属性不置位 ⇒ 用例按非 robust 走 → 挂或 ETIMEDOUT。
   - **关键事实（决定工作量，务必按此设计）**：musl **自己在用户态**处理 robust 链表 —— `musl/src/thread/pthread_create.c:119-137`（`__pthread_exit` 内）逐项 `a_swap(&m->_m_lock, 0x40000000)` + `__wake`，并显式注释覆盖「non-pshared mutex 与 detached 线程」两种场景（正是本册两例）。⇒ 平台侧只需 `set_robust_list` / `get_robust_list` 的**注册与查询一致**，不必实现内核式「线程死亡时遍历 guest 链表」。
   - **musl 的调用点（本册须逐条覆盖）**：`pthread_mutex_trylock.c:27-35`（首次持锁时 `set_robust_list(&self->robust_list, 3*sizeof(long))`，即 `off` 已设置后的 head 指针）；`pthread_create.c:159-162`（detached 退出前 `set_robust_list(0, …)` 注销）；`pthread_mutexattr_setrobust.c`（`get_robust_list(0, &p, &l)` 探测）。
3. **`ISS-298`｜`regression/pthread_cond_wait-cancel_ignored`（两档 fail）**：`pthread_cond_wait did not act on cancellation`（`pthread_join` 得 `rv=0`，线程正常 return）。`-strace` 现场：取消信号**已投递**、handler 已跑（`rt_sigreturn`），随后**同一 futex 被重新 `FUTEX_WAIT`（无 EINTR）**，线程最终 `exit(0)`。对照：`pthread_cancel`（`sleep` 上取消）、`pthread_cancel-points`（`sem_*wait`）、`pthread_exit-cancel` 均 pass ⇒ 取消机制整体在位，缺的只是「阻塞在 futex 时的取消」。
   - **musl 协议（`musl/src/thread/pthread_cancel.c:48-79`）**：`cancel_handler` 以 `sa_flags = SA_SIGINFO|SA_RESTART|SA_ONSTACK` 注册；若被中断的 PC 落在 `[__cp_begin, __cp_end)` 内，**改写 `uc_mcontext.MC_PC = __cp_cancel`**（即「不重启、转去取消」），否则 `tkill` 重投。该协议**依赖「handler 改写了 PC ⇒ 系统调用不得重启」**的 Linux 语义。
   - **qemu 侧现状**：`linux-user/signal.c:1249-1251` 把 guest `TARGET_SA_RESTART` 原样加到宿主 action；`linux-user/dadao/cpu_loop.c:425-428` 对 `-QEMU_ERESTARTSYS` **无条件** `pc -= 4` 重放 trap（不检查 handler 是否改写了 PC）⇒ 取消被重启吞掉。

## 接口规范

- **输入**：
  - 安装根 `qemu-dadao`（`make install-host` 产物，须新鲜：`--version` + 二进制 md5 + 时间戳）；
  - 现行补丁集 `components/qemu/patches/**`（树形、一文件一补丁；现状 qemu **59** 份 / 全仓 **183**）；
  - 047t 驱动 `tools/testcases/run_libc_test_user_suite.py`（`--link-mode {static,dynamic}`、`--filter`、必填 `--json-out`）与 `tools/testcases/report_thread_cases.py`（`TARGET_CASES` 19 条 + `EXTRA_CASES` 1 条）；
  - 4 条用例源码（只读，作为期望值依据）：`libc-test/src/functional/{pthread_mutex_pi,pthread_robust}.c`、`libc-test/src/regression/{pthread-robust-detach,pthread_cond_wait-cancel_ignored}.c`。
- **输出**：
  1. 最小 qemu 补丁（优先 `linux-user/dadao/**`；确需改通用 `linux-user/syscall.c` / `linux-user/signal.c` 时按 `docs/Process-01` 落到对应 `<file>.patch`，**新增独立补丁文件即为合法**）+ `components/qemu/changelog.md` 的 `## M9` 节一条；
  2. 两档 4 例（外加 19 例全量）复跑 JSON + 逐例定性；
  3. `.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项 rc、含 `--inject` ≥2 条可达 FAIL）+ 日志 `.work/log/qemu/<任务ID>-*.log`；
  4. 本册完成区（≤30 行）。
- **约束（硬）**：
  - **改 `components/qemu/**` ⇒ 必须 `make install-host`**（先申报耗时；`JOBS=8`、禁全核；不与其它 L2/L3 并发 —— `ISS-210`/`ISS-229`）；判据必须在 **install-host 之后**的安装根上跑；**只重建不复装 = 假绿**；
  - **不改** `components/musl/**`、`components/llvm-project/**`、`spec/`、`contracts/`、`.tao/contracts/**`、`tests/vectors/**`；
  - **不改测试侧**：libc-test 语料 / 标签 / 期望值 / 驱动分类规则一律不动（`ISS-299` 的修复已在 `TESTCASES-052t-rerun` 落地，**本册不得回退或放宽**）；**禁止**把 `fail` 改成 `blocked`/`known-fail`/`excluded` 来「转绿」；
  - 期望值独立：`EDEADLK`/`EOWNERDEAD`/`ENOTRECOVERABLE`/`PTHREAD_CANCELED` 均取自用例源码与 `pthread_mutex_*` 契约，不从 qemu 内部状态反推；
  - 探针超时显式（`timeout <N>`），**124 判 FAIL**；不得无限等待、不得靠「重跑一次就过」；
  - 任何改动都要给「现状失败签名 → 修后签名」逐条对照。

## 做

### 阶段 0：前置与基线

- 断言 `make install-host` 已完成且新鲜（`qemu-dadao --version` + `md5sum` + 时间戳），并与 `.work/build/qemu` 一致。
- 基线复跑 4 例（两档）：`--filter '^(functional/pthread_mutex_pi|functional/pthread_robust|regression/pthread-robust-detach|regression/pthread_cond_wait-cancel_ignored)$'`，`--json-out /tmp/opencode/QEMU-066t/base-{static,dynamic}.json`；记录 klass + `first_error`，作为后续「修后签名」的对照。

### 阶段 A：`ISS-296` PI futex（先定位、后修）

1. **最小探针 `pi_probe.c`**（静态档优先，避免 hidden 符号问题）：① 主线程 `pthread_mutex_lock`（PI mutex）→ 另一线程 `pthread_mutex_lock` 同锁（观察 `FUTEX_LOCK_PI` 返回值）；② 同线程重锁（`ERRORCHECK`）应得 `EDEADLK`；③ `FUTEX_UNLOCK_PI` 后等待者是否被唤醒。探针内打印 `gettid()`、`m->_m_lock` 读出值（`#include "../src/internal/pthread_impl.h"` 或直接按公开头偏移读取并注明依据）、`errno`。
2. **定位**：把 `uaddr` 值、当前宿主 tid、`/proc/<tid>` 存在性三者对齐；用 `-strace` + `qemu-dadao -d ...`/`gdb` 判断 `ESRCH` 是从「值不是活 tid」来的，还是「`FUTEX_PRIVATE_FLAG`/`FUTEX_CMD_MASK`/地址翻译/超时转换」路径来的。**必须给出可复现的根因证据**，不得沿用 `ISS-296` 的未确认假设。
3. **修**（按根因取最小方案，逐条说明理由）：
   - 若 owner tid 语义确有问题 ⇒ 在 `do_futex` 的 PI 分支做 guest↔宿主 tid 的**双向**翻译（含 `FUTEX_LOCK_PI`/`FUTEX_TRYLOCK_PI`/`FUTEX_UNLOCK_PI`/`FUTEX_WAIT_REQUEUE_PI`/`FUTEX_CMP_REQUEUE_PI` 的兼容处理），并把「翻译只在 `CLONE_THREAD` 场景启用」写清；
   - 若根因是 qemu 对 PI 操作处理不当（私有标志、`val3`/超时、地址翻译）⇒ 就地修；
   - 兜底不取：**不得**用「PI 一律返回 `ENOSYS`」蒙混（那样 `musl` 的 `pthread_mutexattr_setprotocol` 探测失败、`pthread_mutex_pi` 必挂）。
4. 判据：探针 ② 得 `EDEADLK`、③ 等待者被唤醒且 `pthread_mutex_pi` 两档 pass。

### 阶段 B：`ISS-297` robust list（注册/查询一致性）

1. 在 `TaskState`（`linux-user/qemu.h`）加 per-thread 的 `robust_list_head`（guest 指针）+ `robust_list_len`（或等价形状），在 `linux-user/syscall.c` 的 `TARGET_NR_set_robust_list` / `TARGET_NR_get_robust_list` 分支实现：
   - `set_robust_list(head, len)`：`head == 0` ⇒ 注销（长度可忽略）；否则要求 `len == 3*sizeof(long)`（否则 `-TARGET_EINVAL`，与内核一致），保存；
   - `get_robust_list(pid, &head, &len)`：`pid == 0`（且语义上等于 `gettid()`）⇒ 返回本线程；其它 tid ⇒ 按内核口径（无该线程 ⇒ `-TARGET_ESRCH`；有但不支持跨线程读取 ⇒ **须在注释与本册中显式声明所选口径**）；
   - 线程退出/回收路径不得残留悬空指针（`TaskState` 已按线程销毁）。
2. **不要**尝试内核式「死亡时遍历 guest 链表」：musl 已在用户态自处理（见「现场证据 2」），实现它属过度设计。
3. 判据：`pthread_mutexattr_setrobust` 不再 `ENOSYS`；`pthread_robust`（含 `pshared`×`pi` 四个组合）与 `pthread-robust-detach`（`pshared` 0/1）两档 pass，覆盖 `EOWNERDEAD` → `pthread_mutex_consistent` → 正常重锁、以及 `ENOTRECOVERABLE` 路径。

### 阶段 C：`ISS-298` 取消被 `SA_RESTART` 重启

1. **最小探针 `cancel_probe.c`**：worker 阻塞在 `futex(FUTEX_WAIT)`（或 `pthread_cond_wait`）→ 主线程 `pthread_cancel` → 期望 join 得 `PTHREAD_CANCELED`；同时打印「是否观察到 `EINTR`」「handler 内 `MC_PC` 是否落在 `[__cp_begin,__cp_end)`」。
2. **定位**：区分两种失败形态——(a) 宿主 `SA_RESTART` 让宿主 futex **在 handler 之前**自动重启（QEMU 根本没机会处理待投递信号）；(b) 信号处理完、QEMU 按 `-QEMU_ERESTARTSYS` **无条件**重放 trap，忽略 handler 对 PC 的改写。用 `-strace` 顺序 + 临时加日志（**临时树注入**，不提交）判定。
3. **修**：使重启判定与 Linux 一致——**仅当** sigreturn 恢复的 PC 仍指向该 trap（即 handler 未改写 PC）时才重启；被改写的 PC 必须让其生效（musl 取消协议的唯一依赖点）。若需改通用 `linux-user/signal.c`（宿主 action 的 `SA_RESTART` 传播），在补丁注释中写明与 musl `cancel_handler` 的对应关系。
4. 判据：探针 join 得 `PTHREAD_CANCELED`；`pthread_cond_wait-cancel_ignored` 两档 pass；**不回归** `functional/pthread_cancel`、`pthread_cancel-points`、`regression/pthread_cancel-sem_wait`、`regression/pthread_exit-cancel`（两档）。

### 阶段 D：回归与 T3 收口证据

- 19 例（`TARGET_CASES`）两档全跑：`--json-out /tmp/opencode/QEMU-066t/after-{static,dynamic}.json`，再用 `report_thread_cases.py` 出对账表；**19/19 目标 = 两档均 19 pass**（`pthread_create-oom` 仍按 `ISS-257` flake 口径**不计入** 19，但其 klass 变化须如实记录）。
- `check-qemu-semantics`、`check-qemu-smoke` 必须不回归（基线：**224/224**、**90/90**）。

### 阶段 E：证据与可达 FAIL

- `.work/evidence/<任务ID>/run.sh`（默认全跑；`--inject` 快跑），**≥2 条**可达 FAIL：
  1. 把 PI 的 `EDEADLK` 分支临时短路（临时树）⇒ 探针 ② 与 `pthread_mutex_pi` FAIL；`cp`+md5 还原 ⇒ 回绿；
  2. 把 `set_robust_list` 改回 `-TARGET_ENOSYS`（临时树）⇒ `pthread_robust`/`pthread-robust-detach` FAIL；还原 ⇒ 回绿；
  3. （可选）把「PC 已改写不重启」判定反转 ⇒ `pthread_cond_wait-cancel_ignored` FAIL。
- **还原纪律**：`cp` 备份 + md5 对账，或临时树注入；**禁** `git checkout/restore/stash/show` 还原。

### 阶段 F：门控与台账

- 逐个留自身 rc：`make check`（L1）、`check-qemu-semantics`、`check-qemu-smoke`、`check-patch-tree`、`check-component-changelog`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`python3 tools/infra/check_issues.py`；收尾跑 `make check-modules`（L2，串行）。

## 验收标准

1. **前置新鲜**：`make install-host` 在本次补丁之后执行；贴 `qemu-dadao --version`、二进制 md5（== `.work/build/qemu`）、时间戳。
2. **`ISS-296`**：最小探针给出「值/tid/`/proc` 存在性」对齐后的根因证据；修后 `ERRORCHECK` 重锁得 `EDEADLK`、PI 等待者被唤醒、`functional/pthread_mutex_pi` **静态 + 动态均 pass**。
3. **`ISS-297`**：`set_robust_list`/`get_robust_list` 注册-查询一致（含 `head==0` 注销、`len != 3*sizeof(long)` ⇒ `EINVAL`、跨 tid 口径显式声明）；`functional/pthread_robust`（`pshared`×`pi` 四组合）与 `regression/pthread-robust-detach`（`pshared` 0/1）**两档均 pass**（含 `EOWNERDEAD`→`consistent` 与 `ENOTRECOVERABLE`）。
4. **`ISS-298`**：阻塞 futex 上的取消使 `pthread_join` 得 `PTHREAD_CANCELED`；`regression/pthread_cond_wait-cancel_ignored` 两档 pass；四个取消相关用例两档不回归。
5. **T3 收口面**：19 例目标两档 **19/19 pass**（贴 `report_thread_cases.py` 对账 + 两档 JSON 路径）；`pthread_create-oom` 的变化如实记录、不计入 19。
6. **无回归**：`check-qemu-semantics` **224/224**、`check-qemu-smoke` **90/90**、`make check`（L1）rc=0；改 qemu ⇒ `check-patch-tree` / `check-component-changelog` / `check-source-state` rc=0（补丁计数如实报，允许新增）。
7. **可达 FAIL ≥2**：`--inject` 至少两条「注入→FAIL→`cp`+md5 还原→回绿」；禁恒真、禁 `git checkout/restore/stash`。
8. **测试侧零改动**：libc-test 语料/标签/期望值/`tools/testcases/**` 0 改动（`git diff --stat` 为证）；无任何 `fail`→`blocked`/`known-fail`/`excluded` 的降级。
9. **边界**：`components/musl/**`、`components/llvm-project/**`、`spec/`、`contracts/`、`.tao/contracts/**`、`tests/vectors/**` 0 改动；不提交 git、不 push；完成区 ≤30 行且与真实输出逐条对齐。

## 不做项（显式）

1. **改 musl 端口**（`__clone`/`a_cas`/`syscall_cp.s`/取消协议） ✗ —— `a_cas` 假原子归 `ISS-294`（待用户裁定），本册只在 qemu 面修。
2. **测试侧放宽/改标签/改期望值** ✗ —— 明令禁止。
3. **`ISS-252` / `ISS-299` 的关闭** ✗ —— 归 `TESTCASES-052t`（本册只供证据）。
4. **`ISS-255`/`ISS-257` 宿主信号 / `RLIMIT_AS` 族** ✗ —— qemu 面独立项。
5. **system 模式（`dadao-m1`）线程** ✗ —— 已回退 semihosting-only。
6. **`pthread_prio_protect` / 调度优先级（PI 的真正优先级继承效果）** ✗ —— 本册只要求 `EDEADLK`/加解锁语义正确，不承诺宿主调度优先级传递。
7. **`spec/` / 契约 / ABI 帧改动** ✗（若判定必须改 ⇒ **停下报告**，交用户裁定 + ADR）。

## 完成区
**测试结果**：`.work/evidence/QEMU-066t/run.sh` **`--full` 24/24 PASS**、**`--inject` 23/23 PASS**（3 条注入各「注入→FAIL→`cp`+md5 还原→回绿」，含 3 次 rebuild）。两档 4 例 **4/4 PASS**（`functional/pthread_mutex_pi`、`functional/pthread_robust`、`regression/pthread-robust-detach`、`regression/pthread_cond_wait-cancel_ignored`，静态/动态各 `PASS exit=0`）。T3 19 目标 **两档均 19/19**（`/tmp/opencode/QEMU-066t/t3-{static,dynamic}.json` + `report_thread_cases.py --json-out .../t3-report.json`）；额外 `regression/pthread_create-oom` 静态 `BLOCKED`（`qemu killed by host signal 5`，`ISS-257`，不计入 19）、动态 `PASS`。旁证（信号帧改动的回归面）`functional/setjmp`、`regression/{sigaltstack,sigprocmask-internal,sigreturn}` 两档 4/4 PASS。修前/修后签名：PI `futex(FUTEX_PRIVATE_FLAG|FUTEX_LOCK_PI)= -1 errno=3(ESRCH)` → `= -1 errno=35(EDEADLK)`；取消 `tkill(33)` 后 `tkill(self,33)` 重投 + 同一 futex 重新 WAIT → `tkill(33)` 后直接 `rt_sigreturn`、线程被取消（`.work/log/qemu/QEMU-066t-strace-{pi,cancel}-{before,after}.log`）。
**修改文件**：`components/qemu/patches/linux-user/syscall.c.patch`、`.../linux-user/dadao/signal.c.patch`、**新增** `.../linux-user/qemu.h.patch`、`components/qemu/series`、`components/qemu/changelog.md`（`## M9` 一条）、`.tao/knowledge/issues.yaml`（`ISS-296/297/298` → `closed` + `resolved_by: QEMU-066t` + 处置附注）、本册（完成区 + 第 1 轮自审）；证据 `.work/evidence/QEMU-066t/{run.sh,build_probe.sh,t3_counts.py,pi_probe2.c,robust_probe.c,cancel_probe.c,cancel_probe2.c}`、日志 `.work/log/qemu/QEMU-066t-*`（`.work/` 不入 git）。**测试侧零改动**：`git diff --stat -- tools/testcases tests` 空、`git status -uall -- tools/testcases tests libc-test` 空。组件检出 `HEAD=c266401`（base+1，clean）。
**验收结果**：安装根 `qemu-dadao` md5 **`5e252eb736755ddc2ef8e502f29946ca`** == `.work/build/qemu/qemu-dadao`，mtime `2026-10-20 02:48`，`--version` = `v11.1.1-1-gc266401`。门控（逐条自身 rc）：`check-qemu-semantics` **224/224** rc=0、`check-qemu-smoke` **90/90** rc=0、`check-patch-tree` rc=0（5 组件 **184** patches = qemu **59 → 60**）、`check-index-blobs` rc=0、`check-source-state` rc=0、`check-no-residue` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0、`check-component-changelog` rc=0、`check-run-artifacts` rc=0、`python3 tools/infra/check_issues.py` rc=0（54 open / 17 closed）、`make check`（L1）rc=0。`make build-qemu JOBS=8` 增量（改 `syscall.c`）**7.9 s**。
**新发现/坑**：① **`ISS-296` 的真因不是「guest TID 未翻译」而是字节序**：本端口 `gettid`/`set_tid_address`/`clone` 父侧都直返宿主 tid（探针实测 mutex 字里的 owner == 子线程 `gettid()` == 宿主 tid），但 PI futex 字**存的就是 owner TID**，DADAO 大端写、宿主内核小端读 ⇒ 内核见到字节颠倒值（`0x00395754`→`0x54573900`）⇒ 查不到任务 ⇒ `ESRCH`。修法只能是「宿主调用前后做保值整字转换」。② **`ISS-298` 的真因不是 `SA_RESTART`**：DADAO `struct target_ucontext` 的 `QEMU_ALIGNED(16)` 把 `uc_mcontext` 顶到 176，而 musl `ucontext_t` 期望 168 ⇒ handler 读到的 `MC_PC` 是对齐填充（恒 0）⇒ `[__cp_begin,__cp_end)` 永假。`-QEMU_ERESTARTSYS` 的 trap 重放**无需改**（帧在重放后同一轮内取，PC=trap；handler 改写经 `sigreturn` 生效即覆盖重放）——原假设的两个候选修法都不必要。③ 构建物内嵌 `git describe`（`v11.1.1-1-g<sha>[-dirty]`）⇒ 同一份源码在**不同 commit/脏树**下 md5 不同；比对「安装根 == 构建树」必须在**最终 commit 且 clean** 之后做，否则误判。④ 证据脚本首版把「driver rc=0」当 T3 判据 ⇒ 静态档因 `pthread_create-oom`（`ISS-257`）假 FAIL；已改为从 report JSON 统计 19 目标。
**遗留问题**：① **PI 字在「真正阻塞的 `FUTEX_LOCK_PI`」期间处于宿主序**（补丁注释与 changelog 已显式登记）：非阻塞路径（未争用获取、`EDEADLK`、trylock、unlock）全部正确，真要彻底消除需在 qemu 内做完整 PI futex 模拟（另立册，本册不做）；`pthread_robust` 的 pi 争用场景实测仍 pass。② `get_robust_list` 对「存在的其它线程 tid」也返回 `ESRCH`（qemu-user 无 per-tid 查找；musl 只用 `pid==0`）——口径已在代码注释与本册声明。③ **未跑 `make install-host`**（派单禁）；改为与 `install-host` 的 qemu 两步等价的原子 `cp`（只替换 `qemu-dadao`/`qemu-system-dadao`，不重建/重装 LLVM），md5 已核对；**未 commit/push**（`components/qemu` 检出内的 E1 `commit --amend` 属既有做法）；**未改 `**状态**`**（按派单）。④ 未跑 L2/L3 汇总（`check-modules`/`check-full`，派单禁），仅单跑本册要求的两个门控。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查（`subagent_depth=1`，无嵌套子代理）：逐行读 `do_futex` 新分支、`pi_futex_word_to_host/to_target`、`set/get_robust_list` 两个 case、`target_ucontext` 改动；对照内核 `kernel/futex/{pi.c,syscalls.c}` 与 musl `pthread_mutex_*.c`/`pthread_create.c`/`pthread_cancel.c` 的消费方；核对每条探针断言的 oracle 独立性与可达 FAIL 路径；核对注入的「真改到文件、真重建、真回绿」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `pi_futex_word_to_target()` 的 `lock_user` 失败被静默吞掉 | ✅已修（加注释说明：同地址刚被 `to_host` 成功锁定，此处失败不改变 syscall 结果） | `syscall.c` 注释 | 重建后 `--full` 24/24、`--inject` 23/23 |
| 探针断言硬编码地址/前缀（`head=0x4b128`、`word=0x0039`）——脆弱且与被测同源 | ✅已修 | `robust_probe.c` 改打 `head_matches/len_ok/head_cleared`；`pi_probe2.c` 改打 `owner_matches_gettid` | `--quick` 11/11；断言变结构性布尔 |
| 注入 2 原打在 `set_robust_list`，而 musl 忽略它的返回值 ⇒ 用例仍 pass（注入不可达判据，属假注入） | ✅已修 | 改注入 `get_robust_list`（musl `pthread_mutexattr_setrobust` 的探测点），并要求 `pthread-robust-detach` driver rc≠0 | `--inject` 日志 inj2 两项均按预期 FAIL |
| T3 断言把 driver rc=0 当判据 ⇒ 静态档被 `pthread_create-oom`（`ISS-257`）拖成假 FAIL | ✅已修 | `check_t3` 改为从 `report_thread_cases.py` 的 JSON 统计 19 目标 + 「无 target fail」断言 | `--full` 24/24，`other_nonpass=['regression/pthread_create-oom']` |
| 证据脚本未校验安装根新鲜（`ISS-210` 假绿风险） | ✅已修 | 新增 `check_install_root`（build md5 == install root） | `--full` 首项 PASS，两处 md5 相同 |
| 注入是否真改动了文件（防「空注入」） | ✅已证 | `inject_file` 要求 pattern 命中数 == 1，并比 md5 | 三次注入 md5 均变；还原后 md5 回到原值 |
| `get_robust_list` 对存在的其它线程返回 `ESRCH`（非内核精确语义） | ⏸延后（无 guest 消费者；qemu-user 无 per-tid 查找设施；任务允许显式声明口径） | 代码注释 + 完成区遗留② | `robust_probe` 的 `pid=8` ⇒ `ESRCH` 符合所选口径 |
| 阻塞在 `LOCK_PI` 期间字面为宿主序 | ⏸延后（需完整 PI futex 模拟，另立册） | 补丁注释 + changelog + 完成区遗留① | 非阻塞路径与 `pthread_robust` pi 组合实测 pass |

判决：可修 finding 已全部处置；两项延后项均为**无消费者/需另立册**的能力边界，已在代码与本册显式登记，不影响本册判据。`components/qemu` 检出 E1 成立（`HEAD=c266401`、`base..HEAD` 1 个 commit、clean）。

#### 第 1 轮 architect 提交审核
- **档位**：`待验收`（engineer 返回后、reviewer 判决前）⇒ **正常提交**（按派单「提交 `QEMU-066t`」，非 `WIP:`）。**提交号 `809edff`**，落 `QEMU-066t` 分支；**未 push**。
- **文件集对账**（`git diff --cached --name-only`，显式 staging 8 项，禁 `git add -A`）：
  - 与完成区「修改文件」7 项**逐条相符**：`components/qemu/patches/linux-user/{syscall.c.patch, dadao/signal.c.patch, qemu.h.patch(新增)}`、`components/qemu/series`、`components/qemu/changelog.md`、`.tao/knowledge/issues.yaml`、本册。
  - **多提 1 项**：`.tao/knowledge/milestones.md`（architect 职责内：本册 `**状态**` 两处 `待开始 → 待验收` + 流水一句改动，89 → 76 字符 ≤120）。
  - `issues.yaml` 内含 **architect 侧新增** `ISS-300`（`P3` / `open`，安装根新鲜度：`install-host` 之外的二进制替换属例外手法，应尽量走 `install-host`；本次 `cp` 的 md5 已核对一致 ⇒ 结论有效）。
  - **漏提 / 越界**：无（`spec/`、`contracts/`、`tools/`、`tests/` 零改动；`components/qemu` 检出 clean、`HEAD=c266401`）。
- **核验（秒级 + L1，均现场复跑）**：`check-patch-tree` **5 组件 / 184 patches OK** rc=0（`59 → 60`，与 changelog 一致）；`check_issues.py` rc=0（**55 open / 17 closed**，`resolved_by` 约束 OK）；`check_tasks.py` rc=0（「漏收尾 8」为报告项、不阻断，本册即其一，reviewer 判决后由主会话 `/complete`）；**`make check`（L1）rc=0，34.8 s**（含 `check-index-blobs`：132 new-file OK、`check-knowledge-refs` 悬空 0、`check-no-residue` PASS、`check-spec-readonly` 21 卷 OK）。
- **披露保留（已核、不改写）**：完成区遗留③ 的「未跑 `make install-host`、以原子 `cp` 替换安装根 qemu 两步」为**例外手法**，理由（否则门控读旧二进制假绿）与 md5 核对均在册；已按派单登记 `ISS-300`。

#### 第 1 轮 reviewer 验收（2026-10-20）

**重跑记录**：
- `run.sh --full`：rc=0（**24/24 PASS**）。逐条：ISS-296 探针 first lock rc=0 + relock EDEADLK(35) + owner==gettid ✓；ISS-297 探针 head=0 len=24 + set/get agree + bad len EINVAL + foreign pid ESRCH + unregister head_cleared=1 + musl setrobust r=0 ✓；ISS-298 frame PC in_range=1 + cancel joins CANCELED ✓；4 例两档 4/4 ✓（静态+动态）；T3 19 目标两档 19/19 ✓（static: other_nonpass=`pthread_create-oom`；dynamic: other_nonpass=[]）；install root md5 == build tree ✓；check-qemu-semantics **224/224** ✓；check-qemu-smoke **90/90** ✓。
- `run.sh --quick`：rc=0（11/11 PASS）。
- **ISS-296 strace 证据自验**：before log `FUTEX_PRIVATE_FLAG|FUTEX_LOCK_PI` = -1 errno=3(ESRCH)；after log = -1 errno=35(EDEADLK) ✓。根因 = PI futex 字存 owner TID、DADAO 大端写、宿主内核小端读 ⇒ 字节颠倒值 ⇒ 查不到任务 ⇒ ESRCH。修法 `stl_he_p(p, ldl_p(p))` 保值整字转换 ✓。
- **ISS-297 robust 证据自验**：`set_robust_list` len≠3\*sizeof(long) ⇒ EINVAL ✓；head==0 注销 ✓；`get_robust_list` 对其它 tid ESRCH（口径已在代码注释声明）✓；musl `pthread_mutexattr_setrobust` 探测 r=0 ✓。
- **ISS-298 ucontext 证据自验**：`target_ucontext` 无 `QEMU_ALIGNED`、uc_mcontext 偏移 168（8+8+24+128）✓；musl 期望 168 ✓。原 `MC_PC` 恒 0（对齐填充）⇒ `[__cp_begin,__cp_end)` 永假 ⇒ 取消失效。修复后 cancel handler 改写 PC 经 `sigreturn` 生效 ✓。
- **测试侧零改动**：`git diff --stat -- tools/testcases tests` = 空 ✓；`git status -uall -- tools/testcases tests libc-test` = 空 ✓。
- **独立注入**：改 `syscall.c` 的 `stl_he_p(p, ldl_p(p))` 为注释 ⇒ `make build-qemu JOBS=8` + `run.sh --quick` ⇒ `FAIL ISS-296 pi relock EDEADLK`（rc=1）；还原 md5 对账 YES + rebuild + `run.sh --quick` ⇒ 11/11 PASS rc=0 ✓。
- `make check`(L1)：PASS ✓。
- `git status --porcelain`：空 ✓。

**约束核验**：① PI futex 大端转换 ✓；② robust 注册/注销一致（head=0 注销、len≠24 EINVAL）✓；③ `target_ucontext` 去 16B 对齐 ✓；④ gettid 无需翻译（探针 owner==gettid）✓；⑤ 4 例两档 4/4 pass ✓；⑥ T3 19/19 两档 ✓；⑦ semantics 224/224 ✓；⑧ smoke 90/90 ✓；⑨ 测试侧零改动 ✓；⑩ musl/llvm/spec/contracts 零改动 ✓。

**判定：Accepted**。三条缺口全部达标；三处 engineer 注入 + 独立注入均红→还原→绿；24/24 全绿；T3 收口 19/19 两档；无未通过的约束。
