# m18-linux-029: 异步精确点残余（忙等 7/20，疑 QEMU `cg15 rc2` 在 `ret` 上口径）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-028`（主因 `CFXESC` 已修）、`m18-linux-007`（忙等复现器）
**可并行分片**：否（先诊断，可能牵涉 QEMU 模型）
**预估**：3–5 h（标定：同档 025/028 实做各约 5 h；本任务已有 7/20 复现器，定位为主）
**档位**：大改（异步精确点 + 可能 QEMU 模型）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`，本 worktree 自建）

## 背景

`m18-linux-028` 修掉主因（user 异步把捕获交接 `cfx_smon` 后不 escape ⇒ 任务被切出期间 `cfxha != inner_cfx_code` ⇒ `CFXESC`，且 escape 落在恢复用户 SP 之后 ⇒ semihosting 参数失效、静默自旋）。修后 `CFXESC` 0/3，但忙等探针仍有 **7/20** 红，签名不同：

- 任务用户帧 `ip` 落在**相邻函数体**（`worker+0x10`，即该函数 prologue 之后）；
- `SP` 仍是该任务自己的用户栈；
- `start`（该任务等待的共享变量）**未置位**；
- 无 die、无 `CFXESC`；QEMU monitor 显示 CPU 在 **user 模式**执行该 ip。

`ISS-m18-011` 记录该残余，并给出假设：QEMU 对**异步精确点**（`cg15 rc2` = 已提交指令之后的 `rb0`，“跳转即目标”）在 `ret`/间接跳转边界上的取值，与内核假设不一致。

## 目标

1. **先诊断、后改**：确认是「QEMU 模型取值与 spec 一致但内核假设错」还是「QEMU 与 spec 不一致」。判据 = 用 `spec/` 正文（`DADAO-12 §5.4`、`ADR-0064`）逐条比对 `cg15 rc2` 在 `ret`/间接跳转上的定义，并用最小 RTL/QEMU 对照实验（可用 `tests/arch` 或最小汇编）取实测值。
2. **可复现**：复用 `m18-linux-007` 落在运行期证据目录的忙等复现器（`probe/pthread_busywait.c` + `run_busywait.py`），修前 ≥7/20 红、同一签名。
3. **修复**：
   - 若判「QEMU 与 spec 不一致」⇒ 改 `components/qemu/**`（最小），并按 `m18-qemu-007/009/010` 的口径重导补丁；同时评估对 RTL/gem5 的影响（不改它们，登记差异）。
   - 若判「内核假设错」⇒ 改 `components/linux/patches/**`（最小）。
   - **若 spec 本身没定义清楚** ⇒ 停下写「待裁定」（现象、签名、两种口径、影响面），不要自行改 `spec/`/`.tao/contracts/`。
4. **不得放宽判据**：K2/K5/K6、LTP 两轮、`amb_window_probe`、soak 全部保持原判据。

## 验收（逐条贴真实 rc）

1. 诊断结论：spec 条文引用 + 实测值 + 判「QEMU 错 / 内核错」的依据；若落到 spec 缺口，任务书「待裁定」给出两种口径。
2. 修前 ≥7/20 红（同一签名）、修后 **0/≥20**；日志与现场快照落盘，每跑次独立目录。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现；② 破坏守护/断言 ⇒ 探针红。
4. 不回归：K2 170/170、K5 285/285、K6 82/82、`run_suite.py --suite ltp` 两轮逐例一致、`amb_window_probe` 14/14、soak 窗口 0/≥1000 且静默自旋 0。
5. `ISS-m18-011` 闭合（`resolved_by` 指向本任务）；与 `ISS-m18-005/006/009` 的关系写清。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`、`components/qemu/patches/**`（仅在诊断判 QEMU 错时）、对应 `changelog.md`、`tests/unit/linux/**`、`tools/**` 中相关工具、`.tao/knowledge/issues-m18.yaml`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. QEMU 用本 worktree 自建（记 md5）；不覆盖共享安装根。
4. 组件补丁按 `docs/Process-01` 重导；还原一律 `cp`+md5；还原后重建；同一时刻一个长跑批。
5. 禁「重试直到绿」；命中 `ISS-m18-005/006` 时单独计数记签名。

## 待裁定

无（诊断若指向 spec 缺口，按目标 3 在完成区前写入本节）。

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
