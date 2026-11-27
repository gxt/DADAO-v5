# m18-linux-007: pthread create/join 闭环（K6 缺口）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控）、`m18-infra-001`（musl 基线）、`m18-linux-026`（0.8.1-rc 内核）、`m18-infra-002`（动态链接，已交付）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务以既有 clone/futex 为前提，取 1.5–2× 中位）
**档位**：中改（用户态线程 + 内核 futex/clone 验证）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

> **重派基线（2026-11-27）**：在 **0.8.1-rc 内核**（`cg15`/`cg16` + ack + 模式上限 + 出口帧，`m18-linux-026`）与**本 worktree 自建 QEMU**（记 md5，不覆盖共享安装根）上做；`m18-linux-025` 已闭合 `ISS-m18-001`，但 `ISS-m18-005`（随机 `HOST_TIMEOUT`）/`ISS-m18-006`（`handle_softirqs die`）/`ISS-m18-007`（无 syscall 重启）仍是已知低频/语义缺口：命中即单独计数记签名，每轮 ≤3 次重跑，**不得**当作本任务失败、也不得用重试掩盖；每次跑次单独目录留日志。

## 背景

- `m14-linux-029` 判 pthread create/join 属 K6 范围；用户 2026-11-20 定「建册时再定」，至今无任务书 ⇒ 本任务补立。
- musl 侧 `src/thread/dadao/clone.s` 已是真实现（`INFRA-095t`），内核 K4/K5 已有 `clone`/`futex`/信号；但**没有 create/join 的端到端证据**，K6 只到 busybox 前台执行。
- 本任务不引入新 ABI；期望值按 `contract-syscall.md`（`clone`/`futex`/`set_tid_address`/`exit`）与 `contract-abi.md` 的线程/TLS 口径。

## 目标

1. **验证**：静态 musl 程序完成 `pthread_create` × N + `pthread_join`（含返回值与 `void *` 回传）、`pthread_self`、每线程 TLS（`__thread` 计数）、`pthread_detach`、`pthread_exit`。
2. **定位**：任一项失败，定位到层（内核 syscall/futex、musl clone/TLS、调度/信号），给出证据；修复只做最小必要改动。
3. **门控素材**：交付一个可复跑脚本与探针（运行期证据目录 `run.sh`），结论可被后续 `check-linux-suite`/K6 扩展复用。
4. **动态边界**：动态链接版 pthread 依赖 `m18-infra-002`，本任务先静态；动态版作为遗留项记录并注明复跑入口，不得用静态结果替代动态结论。

## 验收（逐条贴真实 rc）

1. pthread 用例在 QEMU vast 上 **5/5 次连续通过**（同一镜像；每次输出逐字判定），日志含线程数、TLS 计数、join 返回值。
2. 失败路径/边界有断言：`pthread_create` 资源不足或 join 自身、detach 后 join 的错误码符合 `contract-syscall.md`（至少 1 条负向用例）。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 破坏 `clone` 的 TLS/栈参数 ⇒ 用例红；② 破坏 join 唤醒（futex 源）⇒ 用例红；还原后回绿。
4. 不回归：`check-linux-k6` rc=0；`check-linux-k5` rc=0；`check-config-pins`、`check-patch-tree`（linux 与 musl 段与基线逐行相同）、`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/musl/**`（最小）、`components/linux/patches/**`（最小，仅线程/调度/futex 相关）、`tests/unit/linux/**`、`tools/linux/**`、对应 changelog、本任务书。**不改** `Makefile`、`components/qemu/**`、`components/busybox/**`、`check-linux-k6` 判据。
3. 组件补丁按 `docs/Process-01` 重导；不改版本号；术语「bank = 寄存器组」。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 不得以重试掩盖偶发；偶发红必须给频率与根因证据。

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
