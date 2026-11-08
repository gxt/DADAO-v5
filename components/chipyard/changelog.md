# chipyard 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文>`；节 = `## M<k>`（节序 M1→M2→…）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M12

- **2026-11-08 `m12-chipyard-001`**
  - 摘要：**chipyard 首次进入 v5 补丁集**（`ADR-0024 D1` 就地修订，用户裁定 B）：新增 `generators/dadao-wuming/**`（`WumingTile extends BaseTile`、自声明 `TLClientNode`/`TLIdentityNode`、`WumingCoreParams` 不继承 `CoreParams`、桩核）、`generators/chipyard/src/main/scala/config/DadaoConfigs.scala`（`WumingTinyConfig`）、根 `build.sbt` 的 `wuming` 项目与 chipyard 依赖、`PeripheralFragments.WithBootROM` 的 BootROM 资源名参数。
  - 执行者：engineer
