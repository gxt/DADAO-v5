# INTEG-061t: M11 里程碑核验与归档（无 m 后缀）

**模块**：integ
**项目里程碑**：M11
**依赖**：`TESTCASES-103t`、`TESTCASES-104t`、`INTEG-059t` 全部 `已验证`
**状态**：待开始

## 背景

用户 2026-11-08 裁定：M11 的模块 `m` 册门控**取消**（选 B）；M11 收口改为**立一个 integ 核验任务**（无 `m` 后缀）——「该检查任务状态检查任务状态，该归档归档即可」。本任务即该核验任务，**不新建 `m` 册**。

## 目标

### 1. 任务状态核验（机械）

- `make check-tasks`（含 `--strict`）：所有 M11 任务书 `**状态**` 与 `milestones.md` 表位置一致；漏收尾 = 0
- `make check-milestones-fresh`：分类一致 / 覆盖 / 已验证倒序 / 格式
- 逐个抽查「已验证」行对应的任务书：状态字段、完成区存在、审阅记录有判决
- 对 `待开始`/`进行中` 残留逐一给结论：并入 M11 归档、转入 M12，或明确登记为后续（写明理由与去向）

### 2. 里程碑判据复核（真实重跑）

- `make check-full`（L3）rc=0；`check-l3-report` rc=0
- `make check-night` 4/4 绿、`check-night-report` rc=0（若 059t 已包含同一证据，注明并复核其落盘结果即可，不重复跑）
- QEMU ↔ gem5 双向一致性矩阵存在且与 059t 结论一致；`tests/parity/matrix-M11.md` 已重生成
- 已知 BLOCKED 项（picolibc `math_test` B7 浮点）在报告中保留且不计入通过数

### 3. M11 归档（按 `docs/Process-04`）

- 建 `.tao/archive/M11/`：`README.md` 五节齐全（结构与册字段以 `check_archive.py` 判定为准）
- M11 任务书 `git mv` 入 `.tao/archive/M11/<模块>/`；归档任务自身最后入档
- `issues.yaml`：提取 M11 阶段（≤ 达成日）`closed` 项 → `issues-closed.md`，活台账移除
- `milestones.md`：删除 ≤ 达成日的「已验证」行；`待开始`/`进行中` 行不删，随里程碑迁移或另立
- 里程碑断言：`milestones.md` 的 `项目里程碑 = M11` 保留至 M12 正式接管（切换动作不在本任务，如需切按 `m12-infra-001` 双台账口径）

## 验收标准

1. `make check-tasks` rc=0 且 `--strict` 漏收尾 = 0；`make check-milestones-fresh` rc=0
2. `make check-full`（L3）rc=0、`check-l3-report` rc=0；`check-night` 4/4 与 `check-night-report` rc=0
3. `make check-archive` rc=0（含新 M11 归档，`--self-test` 亦 rc=0）
4. `git mv` 后无任务书遗留于 `.tao/tasks/`（M11 已完成项）；`.tao/archive/M11/README.md` 五节齐备
5. 核验报告写明：M11 任务总数、已验证数、残留项去向、已知 BLOCKED 项
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 非范围

- 不新建 `m` 册；不改 `check_milestone_tasks.py`（m 册门控取消归 `m12-infra-002`）
- 不修 M11 期间遗留的语义缺口（如需修复另立任务，本任务只登记去向）
- 不动 M12 台账与 M12 任务书
