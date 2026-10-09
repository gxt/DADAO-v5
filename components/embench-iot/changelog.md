# Embench-iot 组件变更记录

> 粒度：**按任务一条**，追加式。补丁集的生成/应用/校验规范见 `spec/Process-01-组件补丁组织与构建编排.md`。

| 日期 | 任务 | 变更 |
|---|---|---|
| 2026-10-09 | `INFRA-051t` | **组件接入骨架**：`manifests/components.lock.toml` 翻 `enabled=true` + 精确 commit `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`（`ADR-0022 D2`）；建 `components/embench-iot/{patches,series,changelog}`；首个补丁 = 新增 `examples/dadao/README.md`（占位，声明无行为；board shim/最小运行时归 `TESTCASES-039t`）。 |
