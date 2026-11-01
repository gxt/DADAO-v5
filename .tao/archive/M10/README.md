# M10 归档（Archive）

> **归档日期**：2026-11-01 ｜ **范围**：M10 里程碑（**cfx 空间/权限/启动链 + 工具链与测试收口**；2026-10-25 起 ~ **2026-11-01 达成**）的**全部任务书与相关记录**
> **状态（如实）**：**项目里程碑 M10 = 达成（2026-11-01）**——核验册 `INTEG-052m`（结论「M10 达成」）随本归档移入本目录顶层；归档前 `make check-milestone` **rc=0**（现跑）。
> **归档判据**：任务书字段 `**项目里程碑**：M10` 且状态 `已验证`/`里程碑`（**71** 个 = infra 7 / integ 14 `t` + 1 `m` / llvm 12 / qemu 3 / spec 8 / testcases 26）；`issues.yaml` M10 期关闭项（**17** 条，见 `issues-closed.md`）。
> **留活（不归档）**：`INFRA-113t`（字段 `**项目里程碑**：M10 后`，状态 `待开始`，M10 后清理项）；`INTEG-051t` 字段带「M11 未定义，暂挂 M10，待用户确认」括注，`INTEG-052m` 已将其列入「本期任务」⇒ **按 M10 期任务归档**（字段原文随任务书保留）。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m10-retrospective.md`，后续路线见 `.tao/knowledge/milestones.md`。
> **门控提示**：归档后 `.tao/tasks/**` 已无 `INTEG-*m` 档 ⇒ `make check-milestone` 的 ① 「当前里程碑无 `m` 册」为**预期红**（M11 规划立 `k`/`m` 后回绿），非本归档引入的缺陷；L1 `make check` 不含该目标（`Process-04 §8`）。

## 1. M10 任务清单（71 个，按模块）

| 模块 | 数量 | 任务号 |
|---|---|---|
| infra | 7 | INFRA-106t/107t/108t/109t/110t/112t/114t |
| integ | 14 | INTEG-038t–050t（连续 13 个）+ INTEG-051t |
| integ（核验册，顶层） | 1 | INTEG-052m（`M10里程碑核验.md`，置于本目录顶层） |
| llvm | 12 | LLVM-130t–141t |
| qemu | 3 | QEMU-074t/075t/076t |
| spec | 8 | SPEC-173t–180t |
| testcases | 26 | TESTCASES-063t/064t/065t/067t–089t（缺 066） |

> 任务书位于同目录下 `infra/` `integ/` `llvm/` `qemu/` `spec/` `testcases/` 子目录（`git mv` 保留 `R` rename 历史）。

## 2. 终局证据（M10 达成时）

| 套件 | 结果 |
|---|---|
| 夜跑 `make check-night` | **4/4 PASS**：`tset libc-test` / `tset llvm-ts` / `tset embench` / `arch cfx` 四行 `rc=0`；报告 `.dadao/tests/night/2026-11-01-08/`（`manifest.tsv` + `run.log` + `meta.json`） |
| L3 全量戳 `20261031T170934Z` | 8 行 `rc=0`，`check-l3-report` PASS（报告 `.dadao/tests/l3/20261031T170934Z/`） |
| L1 `make check` / L2 `make check-modules` | 均 `rc=0`（2026-11-01 现跑） |
| 收尾门控 `make check-milestone` | `rc=0`（归档前现跑；`INFRA-114t` 修复 `check-sync-nonmaskable` 的 `PMEM_DMA` 白名单缺口后回绿） |
| open issue | **0**（归档前 `check_issues.py` 报 `0 open, 17 closed`；17 条见 `issues-closed.md`） |

## 3. 相关索引 / 指针

- 里程碑定义/达成：`.tao/knowledge/milestones.md`（M10 任务流水行**保留**在活台账，作历史可读索引）
- 里程碑核验：同目录 `INTEG-052m-M10里程碑核验.md`
- 里程碑回顾：同目录 `m10-retrospective.md`
- 关闭 issue 快照：同目录 `issues-closed.md`（17 条）
- 遗留台账：`.tao/knowledge/issues.yaml`（当前 `0 open`）、`.tao/knowledge/lessons.md`（教训/方法论）
- **跨文件引用说明**：本归档**未更新**历史引用；凡引用 `.tao/tasks/**` 中 M10 任务书路径者，其内容现位于本目录（历史指针）。
