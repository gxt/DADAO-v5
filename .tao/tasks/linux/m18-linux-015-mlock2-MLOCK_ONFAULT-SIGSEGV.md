# m18-linux-015: mlock2 / MLOCK_ONFAULT 路径 SIGSEGV

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务单路径根因定位，取 1.5–2× 中位）
**档位**：中改（mm/syscall）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-005` 分诊的 `mm-mlock2-tests`（`KERNEL_BUG`）：程序只打出 TAP header/plan（`1..15`）就 `SIGSEGV`（rc=139），第一条子测试 `mlock2_(3 * page_size, MLOCK_ONFAULT)` **没有**以 `ENOSYS` 失败，测试因此进入 `test_mlock_lock()` 并在其中崩溃。没有任何用户态断言被触发 ⇒ 属内核（或 libc/内核 ABI）故障，不是测试假设。证据行见 `tests/unit/linux/suite/triage.yaml`。

## 目标

1. 定位崩溃点：`mlock2`/`MLOCK_ONFAULT` 的系统调用实现、页表/权限路径或返回 ABI（寄存器/errno）。
2. 修复到符合 Linux mm/syscall 语义：要么真正实现 `mlock2`+`MLOCK_ONFAULT`，要么按契约返回 `ENOSYS`/`EINVAL`，不得「成功但坏页表」。
3. 修后用例能继续跑完全部子测试并给出明确结果。

## 验收（逐条贴真实 rc）

1. 修前签名（rc=139、仅 TAP header）落盘；修后 `run_suite.py --only mm-mlock2-tests` 连续 5 次无 `SIGSEGV`，输出逐子测试结果（15 条或明确 SKIP）。
2. 返回值/errno 与 `contract-syscall` 及 Linux `mlock2(2)` 语义一致；至少覆盖：`MLOCK_ONFAULT` 合法、未知 flags ⇒ `EINVAL`、未映射区间 ⇒ `ENOMEM`。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ SIGSEGV 复现；② 把 `mlock2` 实现为总是 `ENOSYS` ⇒ 正向用例判红（若选择实现语义）。
4. 不回归：`check-linux-k5`、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. 更新 `triage.yaml` 对应行；`check_suite.py --latest` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小，mm/syscall）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`（triage/用例配置）、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 期望值来自 `contract-syscall` 与 Linux 语义；不改测试来迁就内核现状。
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
