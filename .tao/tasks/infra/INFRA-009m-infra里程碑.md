# INFRA-009m: infra 里程碑

**模块**：infra
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 具备可复现的构建基础设施（M0 完成）——干净 checkout 上可 `make manifest-check` / `make doctor` / `make status`，按精确 commit `fetch` 上游组件、`apply-series` 应用有序补丁，`build-mc` / `build-qemu` / `build-gem5` 目标就绪（组件未启用时为显式 stub），并可在干净主机或开发容器上运行仓库级检查；`make check` 在干净 checkout 上通过（M0 退出标准）。
**关联任务**：`INFRA-002t`、`INFRA-003t`、`INFRA-004t`、`INFRA-005t`、`INFRA-006t`、`INFRA-007t`、`INFRA-008t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：`Makefile`、`scripts/{manifest_check,fetch,apply_series,make_patch,fetch_refs,doctor,status,clean_work}.py`、`manifests/{components,references}.lock.toml`、`containers/dev/Dockerfile`、`.tao/knowledge/adr-0001-greenfield-rebuild.md`、`.tao/knowledge/adr-0002-build-orchestration.md`
- **跨模块前置**：`INFRA-007t` 的 gem5 构建依赖清单标注 `[OPEN]`（待 gem5 模块确认）；在 gem5 模块确认前不得置 `里程碑`（见 `INFRA-007t` 审阅记录 → 交叉复核）。
- **引用一致性前置（核验前必须处置）**：修正 `INFRA-001k`（ADR-0001/0002 裸引用）与 `Makefile`（第 3 行注释）的 ADR 引用，补明 v5 路径（`.tao/knowledge/adr-0002-build-orchestration.md` / `adr-0001-greenfield-rebuild.md`）。由主会话在核验本里程碑前处置（不另开任务）。
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
