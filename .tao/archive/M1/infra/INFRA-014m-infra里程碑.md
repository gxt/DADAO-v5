# INFRA-014m: infra 里程碑

**模块**：infra
**项目里程碑**：M1
**状态**：里程碑
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

## 核验记录（2026-09-21，主会话执行；用户确认置里程碑）

**关联任务**：`INFRA-001k`~`013t` 全部 `已验证`（含本会话完成的 `010t`（issue registry）/`011t`（spec 引用审计器）/`012t`（spec drift 检查））。

**产出文件（18/18 存在）**：`Makefile`；`tools/infra/{manifest_check,fetch,apply_series,make_patch,fetch_refs,doctor,status,clean_work,check_issues,check_spec_refs,check_spec_drift}.py`；`manifests/{components,references}.lock.toml`；`containers/dev/Dockerfile`；`docs/issues.yaml`；`.tao/knowledge/adr-0001-greenfield-rebuild.md`、`adr-0002-build-orchestration.md`。

**gate 状态（区分既有红因）**：
```
$ python3 tools/infra/manifest_check.py     → exit 0  ✓
$ python3 tools/infra/check_spec_drift.py   → exit 0  ✓
$ python3 tools/testcases/validate_vectors.py → exit 0  ✓
$ python3 tools/infra/check_issues.py       → exit 1  ← 设计如此（M1-gate 阻断项 ISS-056）
$ python3 tools/infra/check_spec_refs.py    → exit 1  ← 设计如此（57 violations；独立目标，不入 make check）
```
⇒ **`make check` 的红因唯一 = `ISS-056`（`fence` 实现缺失，qemu 侧）**，infra 自身 gate 无问题 ✓；该 issue 已按用户裁定登记 `deferred`（处置完毕）⇒ 不构成本模块的未处置跨模块影响 ✓。

**结论**：核验通过，置 `里程碑`。
