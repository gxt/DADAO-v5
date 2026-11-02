# M9 归档（Archive）

> **归档日期**：2026-10-25 ｜ **范围**：M9 里程碑（**FP 完备性 + ISA 收口 + 规范重组**；2026-10-19 起 ~ **2026-10-24 达成**）。
> **状态（如实）**：**项目里程碑 M9 = 达成（2026-10-24，用户裁定「不用等我确认」）**——核验册 `INTEG-037m`（留活于 `.tao/tasks/integ/`，供 `check-milestone` 与 M10 交接）。
> **归档判据**：任务书字段 `**项目里程碑**：M9` 且状态 `已验证`（**68** 个 = infra 11 / llvm 15 / qemu 10 / spec 21 / testcases 11）；`issues.yaml` M9 期关闭项（**83** 条，见 `issues-closed.md`）。
> **留活（不归档）**：`INTEG-037m`（里程碑核验册，`.tao/tasks/integ/`）；`issues.yaml` 11 条 open（全部 M10 登记项）。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m9-retrospective.md`，后续路线见 `.tao/knowledge/milestones.md`。

## 1. M9 任务清单（68 个，按模块）

| 模块 | 数量 |
|---|---|
| infra | 11 |
| llvm | 15 |
| qemu | 10 |
| spec | 21 |
| testcases | 11 |

> 任务书位于同目录下 `infra/` `spec/` `llvm/` `qemu/` `testcases/` 子目录（`git mv` 保留 `R` rename 历史）。

## 2. 终局证据（2026-10-24 复跑）

| 套件 | 结果 |
|---|---|
| L3 `check-full` | PASS（Embencb 38/38、`lit-full`、全量语义 967） |
| libc-test 静态 / 动态 | 331 pass / 0 fail；338 pass / 0 fail（`blocked` 5 / 2） |
| llvm-test-suite 静态 / 动态 | 204 pass / 0 fail；203 pass / 0 fail（`blocked` 13 / 14） |
| 发布版本 | **SimRISC 0.5.5**（13 册；changelog 30→14 条；归档 `SimRISC-0.5.5/`） |

> `rc=1` 仅由 `blocked>0` 触发（`ISS-248` 既定口径），非失败。

## 3. 相关索引

- 关闭 issue：同目录 `issues-closed.md`（83 条）
- 里程碑核验：`.tao/tasks/integ/INTEG-037m-M9里程碑核验.md`
- 回顾：同目录 `m9-retrospective.md`
