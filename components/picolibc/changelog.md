# Picolibc 组件变更记录

> 粒度：**按任务一条**，追加式。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md`。

| 日期 | 任务 | 变更 |
|---|---|---|
| 2026-10-11 | `INFRA-055t` | **组件接入骨架**：`manifests/components.lock.toml` 追加 picolibc 条目（`enabled=true`、精确 commit `2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`、`shallow=true`、`shallow_ref="release-1.8.12"`）；建 `components/picolibc/{README.md,patches,series,changelog}`；首个补丁 = 新增 `dadao/README.md`（占位，**声明无行为**；真移植归 M7）。浅裸镜像 `.cache/picolibc.git` + 工作树 `.work/source/picolibc`（`make fetch`）。 |
