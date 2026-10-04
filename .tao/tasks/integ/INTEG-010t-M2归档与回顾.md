# INTEG-010t: M2 归档与回顾（收尾）

**模块**：integ
**项目里程碑**：M2
**依赖**：`SPEC-090k`、`SPEC-091t`、`SPEC-092t`、`SPEC-093t`、`SPEC-030t`、`SPEC-033t`、`TESTCASES-014t`、`INTEG-009t`（**全部 M2 任务**；且 M2 各模块 `m` 均已核验为 `里程碑`、M2 门槛 5 条均满足）
**状态**：待开始

## 目标

M2 达成后，按 `spec/Process-04-里程碑归档规范.md` 把 M2 的**任务书**与**台账历史**归档到 `.tao/archive/M2/`，编写 M2 回顾与台账快照，并在各活台账留下指针。本任务**只在 M2 达成后执行**。

## 背景与现状（实测）

- M1 归档先例：`.tao/archive/M1/`（`README.md` + `m1-retrospective.md` + `issues-closed.md` + 各模块子目录）；约定与教训见 `spec/Process-04`（含 §7「M1 归档实录」6 条教训）。
- 现行活台账：`.tao/knowledge/{MEMORY.md,changelog.md,issues.yaml,milestones.md}`；任务书按 `.tao/tasks/<module>/` 组织。
- 归档判据（`Process-04 §2`）：任务书 `**项目里程碑**：M2` 且状态终态（`已验证`/`里程碑`）；`changelog.md` 日期 ≤ M2 达成日的条目；`MEMORY.md` 纯 M2 行；`issues.yaml` 中 `resolved_by` 对应任务提交日 ≤ 达成日的 `closed` 项。

## 交付物

1. **`.tao/archive/M2/`**（新建）：
   - `README.md`（按 `Process-04 §4` 模板：归档判据计数、任务清单按模块、changelog 摘录、MEMORY 摘录、指针）；
   - `m2-retrospective.md`（M2 回顾：事实快照 / 资产地图 / 过程度量 / 时间线 / 被否方案 / 风险台账 / M3 交接 / 复现手册 / 审计链）；
   - `issues-closed.md`（M2 阶段 closed 项快照，可选但建议）；
   - `<module>/` 子目录：M2 任务书用 **`git mv`** 移入（保留 rename；`git status` 显示 `R`）。
2. **活台账处理**（`Process-04 §5`）：
   - `changelog.md`：移除 ≤ 达成日的 M2 条目；表头**之上**加归档指针；
   - `MEMORY.md`：移除归档行；「当前进度」表**内**加归档指针（合法表行）；
   - `issues.yaml`：提取 M2 阶段 closed 项 → `archive/M2/issues-closed.md`，从活台账移除，文件头注释加指针；
   - `milestones.md`：M2 行置「达成」，表下加归档注；
   - `.tao/README.md`：`archive/<里程碑>/` 约定已于 M1 建立，无需重复改。
3. **门槛终检记录**：归档前逐条核验 M2 门槛 5 条，结果写入 `INTEG-010t` 完成区（与 `m2-retrospective.md` 对应）。

## 约束

- 严格遵守 `spec/Process-04`；**不删除、不改历史**（任务书 `git mv`、台账内容搬入 archive）。
- **只 `git add` 归档相关文件**；并行任务在跑时**暂缓**归档（`Process-04 §6` 混提教训）。提交**须经用户确认**（`AGENTS.md`；由主会话执行）。
- 产出 markdown：表内无空行、无连续空行；blockquote 不插在 `| --- |` 与数据行之间；文件尾无空行（`Process-04 §6/§7`）。
- 归档判据边界（达成日当天/灰区）**须实测**（`git log --grep <taskID>`），**不得凭印象**。
- ADR 提醒：归档属过程操作，**不立 ADR**。

## 验收标准

1. `.tao/archive/M2/` 存在，含 `README.md`、`m2-retrospective.md`、`issues-closed.md`（如生成）与各模块任务书子目录。
2. `README.md` 的判据计数（任务书数 / changelog 条数 / MEMORY 行数 / closed 项数）**可机械复算**且与 archive 内容一致。
3. M2 任务书以 `git mv` 移入，`git status` 显示 `R`（rename），非 `A`+`D`。
4. 活台账已按 `Process-04 §5` 处理：`changelog.md` 指针在表头之上；`MEMORY.md` 指针为表内合法行；`issues.yaml` 头部指针 + 快照提取；`milestones.md` M2 = `达成` + 归档注。
5. `make check` **EXIT=0**；`git status` 无临时残留（`check-no-residue`）。
6. M2 门槛 5 条逐条核验记录（附命令与退出码）写入完成区；正式 `m2-retrospective.md` 与之一致。
7. 归档提交单独成一个 commit，只含归档相关文件（混提检查：`git show --stat`）。

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
