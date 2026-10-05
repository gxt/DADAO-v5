# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

> **M1 归档指针（2026-10-03）**：2026-09-22 及之前的 89 条 M1 条目已归档至 `.tao/archive/M1/README.md`（历史指针，不再在此追加）。

> **M2 归档指针（2026-10-04）**：2026-09-23 ~ 2026-10-04 的 60 条 M2 条目已归档至 `.tao/archive/M2/README.md`（历史指针，不再在此追加）。

> **M3 归档指针（2026-10-05）**：2026-10-04 ~ 2026-10-05 的 34 条 M3 条目已归档至 `.tao/archive/M3/README.md`（历史指针，不再在此追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-10-05 | **`INTEG-014t`：M3 归档与回顾**。39 个 M3 任务书 → `.tao/archive/M3/`（`git mv`，38`R`+1`RM`）；`archive/M3/README.md`（§5 模板）+ `m3-retrospective.md` + `issues-closed.md`（56 条，`resolved_by` 提交日 ≤ 2026-10-05）；`changelog.md` 移 34 条 + 表头 M3 指针；`MEMORY.md` 移 1 行 + 表内指针；`issues.yaml` 移 56 closed + 头部指针；`milestones.md` 归档注。**用户裁定**：归档 `SPEC-096k`（`待开始`→`已验证`）。**验证**：证据 84 PASS + 注入 3；`make check` EXIT=0；`check_issues.py` EXIT=0（35 open/0 closed）；§3–§6 + 表格纪律合规。 | engineer + reviewer |
