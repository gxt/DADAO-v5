# Changelog

任务对仓库代码的实质改动记录（由 `/complete` 追加）。

> **M1 归档指针（2026-10-03）**：2026-09-22 及之前的 89 条 M1 条目已归档至 `.tao/archive/M1/README.md`（历史指针，不再在此追加）。

> **M2 归档指针（2026-10-04）**：2026-09-23 ~ 2026-10-04 的 61 条 M2 条目已归档至 `.tao/archive/M2/README.md`（历史指针，不再在此追加）。

> **M3 归档指针（2026-10-05）**：2026-10-05 的 35 条 M3 条目已归档至 `.tao/archive/M3/README.md`（历史指针，不再在此追加）。

> **M4 归档指针（2026-10-07）**：2026-10-06 ~ 2026-10-07 的 28 条 M4 条目已归档至 `.tao/archive/M4/README.md`（历史指针，不再在此追加）。

> **M5 归档指针（2026-10-08）**：2026-10-07 ~ 2026-10-08 的 20 条 M5 条目已归档至 `.tao/archive/M5/README.md`（历史指针，不再在此追加）。

> **M6 归档指针（2026-10-11）**：2026-10-09 ~ 2026-10-11 的 M6 条目（**1** 条）已归档至 `.tao/archive/M6/README.md §2`（历史指针，不再在此追加）；M6 逐任务的实质改动记录见归档任务书 `.tao/archive/M6/<模块>/`。

| 日期 | 描述 | 执行方 |
| --- | --- | --- |
| 2026-10-08 | **`INTEG-022t`：M5 任务书归档与回顾（自归档）**。27 个 M5 任务书（26 终态 + 自归档）`git mv` 入 `.tao/archive/M5/<模块>/`（`infra 3 / spec 9 / llvm 2 / qemu 6 / testcases 3 / integ 4`；`Process-04 §4.1` 自归档，`.tao/tasks/` 仅余 M6 `INTEG-023k`）；产物 `README.md`（清单 27 + 20 条 changelog 摘要 + MEMORY 摘录 + 指针）/`m5-retrospective.md`（达成/决策/机制/遗留/对 M6 交接 + §7.1 `§3` 逐条判定表）/`issues-closed.md`（5 条 = 3 原有 + 边界交付项 `ISS-170`/`ISS-171`）；台账指针（`changelog.md` 表头之上/`MEMORY.md` 表内/`milestones.md` 归档注/`issues.yaml` 文件头）；`Process-04 §3` 台账梳理（6 步、逐条判定；`scope` 含 `M5` 13 条处置完毕，8 条归属存疑项**未擅自定为 M6/closed**、保持原 `scope` + 标「待裁定」提请用户裁定；边界项 `ISS-003`/`ISS-110` 按拆分处置）。门控：`check_issues.py`（39 open/0 closed）EXIT=0、`make check` EXIT=0、`check-no-residue` EXIT=0、`check-spec-readonly`（21 册）EXIT=0；**`spec/` 交集为空**（未触 `spec/`/`contracts/`/`components/`/`tools/`/`tests/`/`Makefile`）；**自归档 rename 相似度随记录追加由 43%→31%**（`-M40%`→`-M30%` 方得 27 R，非移动错误；教训 `lessons §7.25`/规范 `§8.19`）。reviewer **`Accepted`**（独立注入假 `closed` 项 ⇒ `check_issues` 计数变化 ⇒ `cp`+md5 还原回绿，有鉴别力）；architect 交叉复核通过（独立重算 27 归档 / 27 移动 / 门控四绿 / 三产物计数 / 8 存疑项 / `spec/` 交集空）。 | engineer + reviewer（architect 交叉复核 + 正常提交） |
