# GEM5-024t: gem5 SE 信号、资源限制与进程信息

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-023t`（文件 I/O 与时钟；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与事实

- `GEM5-022t` 后 SE 基线：gem5 pass 371 / blocked 217；文件 I/O 与时钟由 `GEM5-023t` 处理
- 本任务覆盖基线里三类阻塞（`GEM5-021t` gap inventory）：
  - **signals 21 例**：`rt_sigprocmask`(135)、`sigaltstack`(132)、`rt_sigaction`、`rt_sigreturn`；代表 `functional/pthread_cancel`、`pthread_cond`、`setjmp`、`regression/sigreturn`、`sigaltstack`、`sigprocmask-internal`、`llvm-ts sqlite3`/`lemon`/`SIBsim4`
  - **resource limits 2 例**：`prlimit64`(261)；代表 `regression/rlimit-open-files`、`pthread_atfork-errno-clobber`
  - **process info 1 例**：`uname`(160)；代表 `llvm-ts unix-smail`
- static 语料里的「pthread_*」多数只是**单线程**用到 `rt_sigprocmask`（信号屏蔽/取消点），不要求真线程；真线程/futex 另立任务

## 目标

1. **信号**：实现 `rt_sigprocmask`、`rt_sigaction`、`rt_sigreturn`、`sigaltstack`、`kill`/`tgkill`（自杀路径）；单进程自投递信号（`raise`）与屏蔽/挂起语义；信号帧在 guest 栈上构造与恢复；默认动作（terminate/ignore）与 `SIGCHLD` 等按 Linux 语义。
2. **资源限制**：`prlimit64`/`getrlimit`/`setrlimit`；至少 `RLIMIT_NOFILE`、`RLIMIT_STACK`、`RLIMIT_DATA`、`RLIMIT_AS`（与 QEMU/内核口径一致，`cur=0` 的 Valgrind workaround 需对齐）。
3. **进程信息**：`uname`、`getpid`/`getppid`/`gettid`、`getuid`/`geteuid`/`getgid`/`getegid`、`sysinfo`（按语料需要）。
4. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh,process.*,...}`、`components/gem5/changelog.md`、`components/gem5/README.md`（能力边界）、本任务书、`milestones.md`。

**不在范围**：真线程/`clone`/`futex`/TLS（另立任务）、多进程 `execve`/`fork`/`wait4`（另立）、文件 I/O 与时钟（`GEM5-023t`）、动态链接、QEMU、测试用例与期望。

## 验收标准

1. 基线复跑：signals / resource limits / process info 三桶 blocked 归零（或转真实失败并给最小复现）；`qemu_only_fail` 仍 0；`gem5_only_fail` 不新增。
2. 代表案例（`setjmp`、`sigaltstack`、`sigreturn`、`rlimit-open-files`、`unix-smail`）各跑 ≥3 次结果一致。
3. 信号语义抽测：`raise(SIGUSR1)` 被 handler 捕获后继续执行；屏蔽期间挂起、解除后投递；`SIG_IGN`/默认终止；`sigaltstack` 生效。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
5. 反例：把 `rt_sigprocmask` 改回未实现 ⇒ 代表案例回 blocked；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 先做 `rt_sigprocmask`（21 例里绝大多数首触它），再做 `sigaltstack`/`sigreturn`/`rt_sigaction`。
- 信号帧布局须与 `contract-syscall` 一致（大端、64 KiB 页、寄存器保存顺序）。
- 若某语言/用例依赖真线程（`clone`），按 BLOCKED 单列，不硬凑。
