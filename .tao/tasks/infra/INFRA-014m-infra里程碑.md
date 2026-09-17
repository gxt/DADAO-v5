# INFRA-014m: infra 里程碑

**模块**：infra
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 具备可复现的构建基础设施 + 通用 CI 检查——干净 checkout 上可 `make manifest-check` / `make doctor` / `make status`，按精确 commit `fetch` 上游组件、`apply-series` 应用有序补丁，`build-mc` / `build-qemu` / `build-gem5` 目标就绪（组件未启用时为显式 stub）；`make check` 通过，且 issue registry / spec 引用审计 / spec drift 检查工具可运行。
**关联任务**：`INFRA-002t`~`INFRA-013t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：`Makefile`、`tools/infra/{manifest_check,fetch,apply_series,make_patch,fetch_refs,doctor,status,clean_work,check_issues,check_spec_refs,check_spec_drift}.py`、`manifests/{components,references}.lock.toml`、`containers/dev/Dockerfile`、`docs/issues.yaml`、`.tao/knowledge/adr-0001-greenfield-rebuild.md`、`.tao/knowledge/adr-0002-build-orchestration.md`
- ~~**跨模块前置（gem5）**~~ ✅ **已移除**：M1 容器不含 gem5 依赖（gem5 属后续阶段），故不再把 M1 里程碑 gate 在 gem5 上（见 `INFRA-007t` 变更记录）。
- **引用一致性前置**：✅ **已处置**——`INFRA-001k`（ADR-0001/0002）与 `Makefile`（第 3 行注释）的 ADR 引用已补明 v5 路径。
- **注（2026-09-14 模块重划）**：新增 `INFRA-010t`/`011t`/`012t`（通用 CI 检查，从 `verif` 迁入）；本里程碑因此由 `里程碑` 回退为 `待开始`，待新任务 `已验证` 后再核验。
- **注（2026-09-17 里程碑顺延）**：新增 `INFRA-013t`（按原始仓库名命名），原 `INFRA-013m` 顺延为 `INFRA-014m`。
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
