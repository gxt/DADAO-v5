# m18-linux-012: ISS-503 K6 门控五条 finding 订正

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控）
**可并行分片**：否
**预估**：1–2 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为门控断言/文档订正，取 1–1.5× 中位）
**档位**：中改（门控断言）
**状态**：待开始
**执行环境**：本地

## 背景

`ISS-503`【P3】（`m18-linux-003` 复核五条非阻断 finding）：

- F1：`check_k6.py` C 组 11 条「rc 标记是脚本期望的…」在 `region()` 成功分支内恒真（应并入 region 断言）。
- F2：完成区「musl 18 项」不准（实为 10 problem；18 是证据脚本按非 linux 前缀行的统计，标签 `non-linux problems` 亦失准）。
- F3：完成区/`Process-07` 的「5 次翻转（S/C/E/R×2）」与「四组各一次」不符。
- F4：`run.sh` 有未使用的 `check_absent_lines`。
- F5：§4a.3 表符号名 `dadao_umon_frame` 应为 `dadao_umon_save`。

## 目标

逐条订正；**不放松 K6 判据**，恒真断言改为可达 FAIL；文档数字与实况一致。

## 验收（逐条贴真实 rc）

1. F1：11 条恒真断言并入 `region()` 的有效断言（或删除并由 region 缺失断言覆盖），注入「C 组期望行缺失」可判红。
2. F2：证据脚本非 linux 问题计数口径与标签准确；`check-patch-tree` 实况（musl 10 problem）与打印一致。
3. F3：任务书完成区与 `Process-07` 的翻转计数改为实况（S/C/E 各 1 + R 2 = 5，四组表述订正）。
4. F4：删除孤儿 `check_absent_lines`。
5. F5：§4a.3 表符号名改为 `dadao_umon_save`（`trap.S` 单帧实体）。
6. `check-linux-k6` rc=0（71/71 或现场打印项数）；`--selfcheck`/`--inject` 仍可翻转；`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. `ISS-503` 关闭；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/unit/linux/check_k6.py`、`docs/Process-07*.md`、`.tao/tasks/linux/m18-linux-003-K6收口门控.md`（仅订正 F2/F3 事实，不改审阅记录）、`.tao/knowledge/issues.yaml`、本任务书。
3. 不改内核/组件；不改版本号；术语「bank = 寄存器组」。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

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
