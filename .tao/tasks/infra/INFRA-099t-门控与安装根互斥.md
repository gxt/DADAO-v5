# INFRA-099t: 门控/安装根写者互斥制度化（`ISS-229`）

**模块**：infra
**项目里程碑**：M9
**依赖**：`INFRA-096t`（安装根新鲜度门控，`待验收`）、`INFRA-093t`（运行产物/日志规矩，已验证）、`QEMU-066t`（`ISS-300` 手工 `cp` 例外手法登记源，`待验收`）、`INFRA-097t`/`INFRA-098t`（**同改 `Makefile`，须串行**）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`infra` 现存最大 = `INFRA-096t`（本批另占 `097`/`098`）⇒ 取 **`099`**（编写前 `grep -rn 'INFRA-099' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实

- **`ISS-229` 现场（假 FAIL）**：`L2`（`make check-modules`）与 `L3`（`make check-full`）在同一工作树**并发** ⇒ `L3_EXIT=2`、Embench `37/38`，失败例报 `stddef.h not found`（读瞬态不完整的安装根）；错开单跑 ⇒ `L3_EXIT=0`、`38/38`。同类：手动 `make build-mc` 与 L2 内的 `install-host→build-mc` 并发 ⇒ 构建树被写坏（`clang-23` 异常膨胀 / segfault，`LLVM-094t` 阶段 A 现场）。
- **现状（只靠注释）**：`Makefile:316-320` 的 `NOTE (concurrency)` 明写「只把 `install-host` 的**写侧**做成 race-safe（`INFRA-053t`/`ISS-172`）；同一工作树并发跑 **gate** targets 仍 **UNSUPPORTED**（共享 build trees 与 SDK artifact dirs）」；`AGENTS.md`「并行任务上限」「长任务」有纪律文字 ⇒ **不可机械判**。
- **目标关系（易踩）**：`Makefile:588 check`（L1）、`:595 check-modules:`（L2）、`:599 check-full: check-qemu-semantics test-m6`（L3）、`:899 test-semihost: install-host build-bootrom test-elf test-codegen check`、`:424 install-host: build-mc build-lld build-qemu build-builtins` ⇒ **嵌套链极深**（`check-modules → test-semihost → install-host/check/build-bootrom`，`check-full → test-m6 → check-lit-full`）。**任何互斥机制都必须允许「同一 make 树内的嵌套」**，否则必死锁。
- **契约/规范落点**：`docs/Process-07 §2`（触发点）、`§3`（新检查定层）、`Makefile:316-320` 注释、`AGENTS.md`「并行任务上限」「长任务」（≤2 行指针）；`ISS-300`（安装根例外手法应收编，本册只做互斥、**不替代**新鲜度检查）；`ISS-210`（旧安装根假绿）。

## 接口规范

- **输入**：`Makefile`（写者目标：`install-host`/`build-*`/`check`/`check-modules`/`check-full`/`test-*` 等）、`tools/infra/**`（若落脚本）、`docs/Process-07`、`AGENTS.md`。
- **输出**：
  1. **机械互斥**：对「会写 `.work/build/**`、安装根 `.dadao/**`、SDK 产物目录」的**顶层**目标加互斥（`flock` 或等价；实现自选，须先诊断嵌套关系）；第二个**独立**进程要么等待（有界）要么 fail-fast 并打印「谁持有锁 / 锁路径 / PID」；
  2. 嵌套**不误伤**：同一 make 树内 `check-modules → test-semihost → install-host/check`、`check-full → check-qemu-semantics + test-m6` 全部实测通过；
  3. 文档：`docs/Process-07 §2` 增「互斥（MUST）」条；`Makefile:316-320` NOTE 由「UNSUPPORTED」订正为「由锁保证」；`AGENTS.md` 对应条 1 行指针；
  4. 证据 `.work/evidence/<任务ID>/run.sh`（含并发探针与自测）+ 日志 `.work/log/infra/INFRA-099t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `components/**` / `tests/vectors/**`；不改任何门控的**判定语义**（只加互斥）；不 commit/push；**不跑** L3 全量作为本册验收（用 L2 + 并发探针即可）。

## 验收标准

1. **互斥可判（核心）**：两个**独立** shell 同时启动写者（至少覆盖 `check-modules` + `install-host`；再覆盖 `build-builtins` + `check` 组合）⇒ 不出现交错写；被拒/等待方有明确提示；串行复跑两者 **rc=0**；给出两进程的起止时间戳 + 日志。
2. **fail-fast/等待语义**：等待须有上界（可配置）且超时给出明确诊断；fail-fast 须 rc≠0 + 提示持有者信息；**不得**静默无限阻塞。
3. **嵌套不死锁**：`make check-modules` 单独跑 rc=0（内含 `test-semihost → install-host/check`）；`make check-full` 的**前置互斥**场景下不因嵌套自锁（若 L3 太慢，可只跑 `check-qemu-semantics` + `test-m6` 的嵌套子集或 `make -n` + 单目标实测，但须有真实执行证据说明无自锁）。
4. **异常面**：锁文件路径不可写 / 锁工具缺失 ⇒ 显式 FAIL（不得静默跳过互斥）；给出实测输出。
5. **可达 FAIL ≥ 2**（真实输出 + 还原回绿）：
   - (a) **并发探针**：两进程同时进 ⇒ 互斥触发器确实生效（而非巧合串行）；用「持有锁 N 秒」的探针让窗口稳定可观测；
   - (b) **注入去掉互斥**（临时树）⇒ 探针观察到两进程重叠（时间戳/锁未持有时写者并行）⇒ 判据可失败；**不得**在真实工作树制造构建树损坏，可用文件级写探针（同一路径写 marker）替代；
   - (c) **自测**：若落脚本，须有 `--self-test`，覆盖「同树嵌套允许 / 独立进程拒绝 / 锁不可用报错」三类注入。
6. **文档一致**：`Process-07`/`Makefile` NOTE/`AGENTS.md` 三处措辞与实现一致（机械可 grep 对齐）；不改判定语义（门控 rc 含义、用例分类不变）。
7. **回归**：`make check`(L1) rc=0；`make check-modules`(L2) rc=0；`check-run-artifacts` / `check-no-residue` rc=0；`check-milestones-fresh` rc=0。
8. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-229` 回填（`closed` + `resolved_by: INFRA-099t`；若与 `ISS-300` 有交叉，注记边界）。
9. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-099t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（是否引入外部 `flock` 依赖 / 是否把互斥做成独立门控层）时留问。
6. 复杂命令输出留 `.work/log/infra/`；并发探针用短任务（`check` L1 或文件级写探针），**不得**并发跑完整 L3 制造损坏。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
