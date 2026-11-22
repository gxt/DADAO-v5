# m18-linux-017: clock_nanosleep(TIMER_ABSTIME) 整机停摆

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`
**可并行分片**：否
**预估**：3–4 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务涉及时钟/定时器阻塞路径，取 2–3× 中位）
**档位**：中改（time/hrtimer）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-005` 分诊的 `timers-nanosleep`（`KERNEL_BUG`）：程序打出 TAP header/plan（`1..12`）后**完全无输出**——没有内核日志、没有 guest alarm、没有 case end；第一条子测试调用 `clock_nanosleep(CLOCK_REALTIME, TIMER_ABSTIME, now+10ns)` 后机器停止推进。因此该用例被标 `stall: true` 单独 boot，宿主无进展看门狗是唯一兜底（`HOST_TIMEOUT`）。证据行见 `tests/unit/linux/suite/triage.yaml`。

## 目标

1. 定位 `TIMER_ABSTIME` 绝对时间路径的停摆根因（时间基准、deadline 换算、hrtimer/时钟事件编程、到期中断投递、返回用户路径）。
2. 修复；不得用「把测试改成相对时间」或加宿主超时掩盖。
3. 修后该用例能跑完全部 12 条子测试并给出明确 verdict。

## 验收（逐条贴真实 rc）

1. 修前停摆签名与 `HOST_TIMEOUT` 落盘；修后 `run_suite.py --only timers-nanosleep` 连续 5 次无停摆、verdict 一致。
2. 覆盖：绝对/相对 `clock_nanosleep`、过去时间立即返回、被信号打断返回 `EINTR`、`clock_gettime(CLOCK_MONOTONIC/REALTIME)` 与 `cfx_time` 基准一致（`ADR-0058`：guest 时间只用 `cfx_time`/内核 tick）。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 停摆复现；② 破坏 deadline 换算 ⇒ 超时子测试红或停摆。
4. 不回归：`check-linux-k2`（时间边界）、`check-linux-k5`（T 组 34/34）、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. 更新 `triage.yaml` 行；`check_suite.py --latest` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小，time/clock/hrtimer）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`、`tools/linux/suite/**`（仅必要）、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 时间口径按 `ADR-0058`；期望值以 `contract-syscall` 与 Linux clock 语义为准；DADAO 64 KiB 页/大端口径按 `MEMORY.md`。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
6. 停摆类证据必须含「宿主无进展」判定方法与时间窗，不得只写「超时」。

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
