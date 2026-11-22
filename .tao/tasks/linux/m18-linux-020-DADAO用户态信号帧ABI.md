# m18-linux-020: DADAO 用户态信号帧 ABI（LTP 阻塞项）

**模块**：linux
**项目里程碑**：M18
**依赖**：无（与 `m18-linux-006` 串行，同写 linux/musl；006 的 `TEST_ADAPT` 待本任务）
**可并行分片**：否
**预估**：4–6 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 kernel+musl 的信号帧 ABI，取 3–4× 中位）
**档位**：大改（信号投递/恢复 + libc ABI）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-006` 首轮 LTP 分诊发现：**handler 安装/查询正常，但一投递信号就 SIGSEGV**。

- 探针（同一套件镜像）：`p_sigonly`（`sigaction` 安装+查询）PASS；`p_raise`（安装 handler 后 `raise(SIGUSR1)`）**SIGSEGV rc=139**；`p_usr1`（子进程 `kill(getppid(), SIGUSR1)`，父进程在 `waitpid`）**SIGSEGV rc=139**；`p_sig`（`alarm`+`fork`+`setpgid`+`wait`，不投递）PASS。
- LTP 的 `tst_test` 新接口在进入时由 harness `heartbeat()` 调 `kill(getppid(), SIGUSR1)` ⇒ `ltp-open01`、`ltp-sigaction01` 在第一条子测试前即 `rc=139 status=signal`；**所有新接口 LTP 用例都会先撞这个缺口**。
- musl 侧 `arch/dadao/bits/signal.h` 的 `mcontext_t`/`struct sigcontext` 目前是 **PROVISIONAL compile-only**（`[OPEN]`）；`m14-linux-046` 曾报「K5 handler 往返跑通」，需核清它与本次 LTP 投递的差异（是内核自测探针、还是用户态完整 `rt_sigframe`）。

证据行：`tests/unit/linux/suite/ltp/triage.yaml` 的 `ltp-open01`/`ltp-sigaction01`（`m18-linux-006` 交付），以及 `tests/unit/linux/suite/ltp/README.md`。

## 目标

1. **先核清现状**：M14 K5 的 handler 往返到底走的是哪条路径；`rt_sigframe`/`sigcontext` 的期望布局与 `contract-syscall`/`contract-abi` 差在哪；给出与 LTP `sigaction01` 的逐字段对照。
2. **定义/补齐 DADAO signal frame ABI**（按契约，不从实现反推）：`rt_sigframe` 布局、`sigcontext`（四组寄存器 + IP/SP/status）、`siginfo_t`、`ucontext_t`、`SA_SIGINFO`、`SA_RESTORER`/restorer、信号 mask、返回路径、栈对齐（8 字节）与 64 KiB 页/大端口径。
3. **实现**：内核投递/恢复路径 + musl `arch/dadao/bits/signal.h`（从 provisional 转正式，必要时 `sigsetjmp`/`restore.s` 同步）；不得用「测试侧改期望」绕过。
4. **验证**：`p_raise`/`p_usr1` 不再 SIGSEGV；LTP `sigaction01`/`open01` 能跑出真实 PASS/FAIL（不是 `UNSUPPORTED`）；补 handler 参数、siginfo、mask、restorer 的断言。

## 验收（逐条贴真实 rc）

1. 现状对照报告：K5 探针路径 vs LTP 路径、缺失字段清单、契约缺口（若是 spec/契约语义变更，停下写「待裁定」，不得自改 `spec/`/`.tao/contracts/`）。
2. `p_raise`、`p_usr1` 连续 5 次无 SIGSEGV；handler 收到正确 signo、`siginfo`、`ucontext` 寄存器可读、返回后原上下文恢复。
3. `run_suite.py --suite ltp --only ltp-sigaction01` 与 `--only ltp-open01` 连续 5 次：不再 `rc=139`，给出 PASS 或它们自己的断言 FAIL；`triage.yaml` 对应行更新/删除。
4. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 破坏 `sigcontext` 的 SP/IP 恢复 ⇒ 返回崩溃；② 去掉 `SA_RESTORER`/restorer 路径 ⇒ 返回路径红。
5. 不回归：`check-linux-k5`（S 组含信号帧）、`check-linux-k6` rc=0；`check-patch-tree` linux 与 musl 段与基线逐行相同；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
6. `m18-linux-006` 的 `TEST_ADAPT` 复评入口：修复后重跑 006 的 64 KiB 敏感用例并记录。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`components/musl/**`（`bits/signal.h`、`restore.s`、`sigsetjmp.s` 等必要文件）、`components/musl/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、本任务书。
3. **不改** `spec/`、`.tao/contracts/`、`Makefile`、`components/qemu/**`、`components/busybox/**`；语义/契约变更须先经用户确认。
4. 组件补丁经 `make_patch.py linux`/`musl` 重导；不改版本号；术语「bank = 寄存器组」；大端/64 KiB 页口径按 `MEMORY.md`。
5. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
6. 修复后必须同时回归静态与动态（`m18-infra-002` 已通）两种链接形态的信号投递。

## 待裁定

- 若 signal frame ABI 需要改 `contract-abi`/`contract-syscall` 的语义或版本号：列出变更请求，停下等用户确认。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
