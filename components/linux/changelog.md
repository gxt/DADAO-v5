# Linux 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M14

- **2026-11-13 `m14-linux-001`**
  - 摘要：**组件转正：去 `patchless`、建空补丁集首态**。锁条目新增 `patch_dir = "components/linux/patches"` / `patch_series = "components/linux/series"`，`role` 改为「Linux 内核移植目标（`arch/dadao`）+ syscall 号表参考」；基线（`7.2.10` / `7b20d05f…` / `shallow_ref = v7.2.10`）与 `source[]` 不变。新增本目录 `README.md`/`changelog.md`/`series`（零条目）/`patches/.gitkeep`；**首个补丁由 `m14-linux-002` 落地**。空补丁集成为合法首态由 `docs/Process-01 §2/§8` 登记（`series` 零条目 + `patches/` 无 `.patch` + `.gitkeep` 至多一个 且仅空 `series` 时合法），E1 期望条数随之为 `base+0`；非空补丁集的 `base+1` 口径不放宽。
