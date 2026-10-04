# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

> **M1 归档指针（2026-10-03）**：2026-09-22 及之前的 89 条 M1 条目已归档至 `.tao/archive/M1/README.md`（历史指针，不再在此追加）。

> **M2 归档指针（2026-10-04）**：2026-09-23 ~ 2026-10-04 的 60 条 M2 条目已归档至 `.tao/archive/M2/README.md`（历史指针，不再在此追加）。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-10-04 | **`INTEG-010t`：M2 归档与回顾（M2 收尾）**。按 `spec/Process-04` 把 M2 的 **149 个任务书**（已验证 141 + 里程碑 8）`git mv` 归档至 `.tao/archive/M2/{infra,spec,testcases,llvm,qemu,integ}/`（`R100`；模块 19/80/12/16/16/6）；新建 `archive/M2/README.md`（§5 模板：判据计数 **149/60/47/41** + 任务清单 + changelog〔60〕/MEMORY〔45+2〕摘录 + 指针）+ `m2-retrospective.md` + `issues-closed.md`（41 条）。**活台账**（§6）：`changelog.md` 移除 60 条（指针在表头之上）、`MEMORY.md` 移除 45 行 + 拆 2 混合行（表内指针）、`issues.yaml` 提取 41 closed（头指针，现 **72 open / 0 closed**）、`milestones.md` 归档注。**门槛终检 5/5**；`make check` EXIT=0（lit 31/31）。**证据**：一键证据 31/31 + `--inject`；reviewer + architect 独立注入（decoy / changelog 追加行）→ FAIL → 还原 sha 复原。**披露**：`SPEC-020m`/`SPEC-025m` 按 (A) 归档；`QEMU-030t`/`TESTCASES-020t` 字段含 `M2（…）`。 | engineer + reviewer + architect |
