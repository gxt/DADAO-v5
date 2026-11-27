# m18-linux-028: 用户态异步返回丢任务（忙等可确定性复现）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-025`（`ISS-m18-001` 已闭）、`m18-linux-026`（0.8.1-rc 内核）
**可并行分片**：否（改 `components/linux`）
**预估**：3–5 h（标定：同档 025 实做约 5 h；本任务已有确定性复现器，定位为主）
**档位**：大改（异步入口/返回 + 调度）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-007` 交付 pthread 闭环时把探针改成**纯用户态忙等**（最大化 tick 命中），**8/8 触发**：控制台最后一行是 `K2 async user frame_ip=…`，之后无任何进展（无 `PTHREAD end`、无 die、无 panic）；普通负载下同现象表现为 `ISS-m18-005`（随机 case 的 `HOST_TIMEOUT`，已见 `mm-pfnmap` / `mm-map-populate` / `futex-wait-timeout` / `fstat02`）。

即：**用户态异步捕获/返回路径会丢任务**，此前被当作“宿主 flake”计数，现在有了确定性复现，不能再算 flake。

## 目标

1. **复现并固化**：把忙等探针做成可复跑、确定性 ≥8/8 的最小用例，保留“修前红”对照证据。
2. **定位根因**：抓现场（`cg15 rc0–rc5`、`cg16 rc17/18`、`cg5 rc8–rc11`、`cfx_smon`/`cfx_hart` 快照、`dadao_ticks`/timer cmp、被丢任务的内核栈/`task_struct` 状态、是否已 ack 但未返回、是否返回后未重入用户）。判据：必须能解释“为什么该任务不再被调度/不再返回用户”，**不接受“重跑就好”**。
3. **修复**：最小改动，落在 `components/linux/patches/**`；不得靠关中断/关 tick/加延时/重试掩盖。
4. **判据不得放宽**：`check-linux-k2`/`k5`/`k6`、`run_suite.py --suite ltp` 两轮、`amb_window_probe`、soak 全部保持原判据。

## 验收（逐条贴真实 rc）

1. 修前：忙等探针 ≥8/8 触发（同一镜像、固定轮数），日志与现场快照落盘；修后：同一探针 0/≥20。
2. 现场证据：上述寄存器/调度观测量各一组修前/修后对照。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现；② 破坏对应守护/断言 ⇒ 探针红。
4. 不回归：K2 **170/170**、K5 **285/285**、K6 **82/82**、`run_suite.py --suite ltp` **两轮逐例一致**、`amb_window_probe` 14/14、soak 窗口签名 0/≥1000。
5. 更新 `ISS-m18-009`（闭合）并说明与 `ISS-m18-005`/`ISS-m18-006` 的关系（同族则一并标注）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内的 `run.sh`；每次跑次单独目录留日志。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues-m18.yaml`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. **QEMU 配对**：用本 worktree 自建 0.8.1 QEMU（记 md5）；不覆盖共享安装根。
4. 组件补丁经 `make_patch.py linux` 重导；还原一律 `cp`+md5；还原后重建；同一时刻一个长跑批。
5. 禁「重试直到绿」；命中 `ISS-m18-005/006` 时单独计数记签名。

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
