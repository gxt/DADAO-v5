# M6 归档（Archive）

> **归档日期**：2026-10-11 ｜ **范围**：M6 里程碑（2026-10-11 达成）的全部任务书与相关记录
> **归档判据**：任务书字段 `**项目里程碑**：M6` 且状态终态（**46** 个 = `infra 5 / spec 9 / llvm 17 / qemu 4 / testcases 6 / integ 5`）；`changelog.md` 中 M6 时期（2026-10-09 ~ 2026-10-11）条目（**1** 条）；`MEMORY.md` 中纯 M6 行（**0** 行）；`issues.yaml` 中 `resolved_by` 指向 M6 任务的 closed 项（**18** 条）。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见本目录 `m6-retrospective.md`，路线见 `.tao/knowledge/milestones.md`。

## 1. M6 任务清单（46 个，按模块）

| 模块 | 数量 |
|---|---|
| infra | 5 |
| spec | 9 |
| llvm | 17 |
| qemu | 4 |
| testcases | 6 |
| integ | 5 |

> 任务书位于同目录下 `infra/` `spec/` `llvm/` `qemu/` `testcases/` `integ/` 子目录。
>
> **特别项**：`integ/INTEG-026m`（**本归档任务自身**）：按 `Process-04 §4.1` 末条**自归档**——最后一步 `git mv` 自身入本目录。
> **注**：`integ/INTEG-023k`（M6 开启 `k`）按 `Process-04 §1`「**M5 起由 INTEG 模块开闭**」归 M6；`integ/INTEG-027t`（agent 配置与规则重构，进程/工具类）`**项目里程碑**` 字段含「不计入 M6 交付任务流水」括注，按字段值（`M6` 起首）归 M6。

## 2. 台账快照

| 快照 | 数量 | 位置 |
|---|---|---|
| M6 阶段已关闭 issue | **18** | 本目录 `issues-closed.md` |
| M6 任务书 | **46** | 本目录 `<模块>/` 子目录 |
| M6 回顾 | 1 | 本目录 `m6-retrospective.md` |

### 2.1 changelog（M6 时期，2026-10-09 ~ 2026-10-11，1 条）

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-10-10 | **`INTEG-027t`：项目 agent 配置与规则重构（`.opencode/**` 入库）**。审计 30 条（A01–F02）逐条收口；`.opencode/{agent,command}/` → 复数 `{agents,commands}/`（E01）；`instructions/` 通用必需项并入 `AGENTS.md`「命令与任务执行纪律」后删除（F01/E02，补回 10 / 显式不适用 4，零静默丢弃）；新增 `opencode.jsonc`（`watcher.ignore=[.work/**,.cache/**,.dadao/**]`）；`AGENTS.md` 新增「长任务」节并精简 **216→172 行**（规则不丢，`slim-map` 逐文件逐条对账）；`.opencode/**` 8 文件**入库**（F02，未跟踪亦未被忽略 ⇒ 无需改 `.gitignore`）。证据 `.work/evidence/INTEG-027t/run.sh` **10/10 PASS + 注入自检**、`make check-no-residue` EXIT=0；`spec/`/`contracts/`/`components/` 交集空。reviewer 第 1 轮 **Needs Revision**（F01 丢规则）→ 返工补回 → 第 2 轮 **Accepted**；architect 交叉复核 + 提交。详见 `.work/log/integ/INTEG-027t-report.md`。 | engineer + reviewer（architect 提交） |

### 2.2 MEMORY 摘录（M6 时期）

> `MEMORY.md` **无纯 M6 行**（`Process-04 §4.3` 判据）；本次仅新增「M6 归档」指针行（`MEMORY.md`「当前进度」表内）。

> **说明**：M6 逐任务的实质改动记录见各归档任务书「完成区」；`changelog.md` 仅 1 条 M6 条目（`/complete` 追加），§2.1 为其归档快照。

## 3. 指针

- 里程碑定义/达成：`.tao/knowledge/milestones.md`
- 里程碑回顾：本目录 `m6-retrospective.md`
- 台账快照：本目录 `issues-closed.md`（M6 阶段 closed **18** 条）
- 遗留台账：`.tao/knowledge/issues.yaml`（issue/待决）、`.tao/knowledge/lessons.md`（教训/方法论/过程记录）
- 变更流水（之后）：`.tao/knowledge/changelog.md`
- **跨文件引用说明**：本归档**未更新**历史引用；凡引用 `changelog.md`/`MEMORY.md` 中 M6 条目者，以活台账为准。
