# m18-linux-016: futex_waitv 返回 EINVAL（多等待接口缺失）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为单 syscall 实现/接线，取 1.5–2× 中位）
**档位**：中改（syscall/futex）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

> **重派基线（2026-11-27）**：在 **0.8.1-rc 内核**与**本 worktree 自建 QEMU**（记 md5，不覆盖共享安装根）上做。`tests/unit/linux/suite/triage.yaml` 里 `futex-wait-timeout` 的 `futex_waitv` 条目仍在（`KERNEL_BUG`），落地后按该条目的 `rerun` 指示复跑并更新分类；LTP 侧的 `ltp-*` 台账当前为空（`m18-linux-006`），本任务若影响 LTP 用例须补跑 `run_suite.py --suite ltp` 两次。低频红纪律：`ISS-m18-005/006/007` 命中单独计数（`ISS-m18-007` = 无 syscall 重启，可能影响 `futex_waitv` 的 EINTR 语义，须明确该接口是否返回 `-EINTR` 而非重启），每轮 ≤3 次重跑，按跑次留日志。

## 背景

`m18-linux-005` 分诊的 `futex-wait-timeout`（`KERNEL_BUG`）：四组里三组通过（相对 `futex_wait`、`FUTEX_WAIT_BITSET` 的 REALTIME/MONOTONIC、`FUTEX_WAIT_REQUEUE_PI`、`FUTEX_LOCK_PI`），但 `futex_waitv` 对普通相对等待返回 **EINVAL(22)** ⇒ 该多等待接口在本移植上未实现。证据行见 `tests/unit/linux/suite/triage.yaml`。

## 目标

1. 核对 `contract-syscall` 中 `futex_waitv` 的号表/参数/返回约定；确认是「未实现返回 EINVAL」还是实现有误。
2. 实现或修正 `futex_waitv`（多 futex 等待，含 `flags`、`clockid`、超时语义），符合 Linux ABI 与契约；不得用「恒 EINVAL」冒充支持。
3. 修后该用例的 `futex_waitv` 子测试通过。

## 验收（逐条贴真实 rc）

1. 修前 EINVAL 复现；修后 `run_suite.py --only futex-wait-timeout` 连续 5 次 verdict 一致，`futex_waitv` 子测试 PASS。
2. 覆盖边界：空数组/`nr_futexes` 越界 ⇒ `EINVAL`；重复 futex 键 ⇒ `EINVAL`；超时路径返回 `ETIMEDOUT`；被唤醒路径返回 0。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退 `futex_waitv` 实现 ⇒ 子测试红；② 破坏超时换算 ⇒ 超时子测试红。
4. 不回归：`check-linux-k5`（futex 组）、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. 更新 `triage.yaml` 行；`check_suite.py --latest` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小，futex/syscall 表）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 期望值以 `contract-syscall` 与 Linux ABI 为准；不做「测试适配」绕过。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

无。

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
