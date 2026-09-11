# INFRA-008m: infra 里程碑

**模块**：infra
**状态**：待开始
**目标**：DADAO-v5 具备可复现的构建基础设施（M0 完成）——干净 checkout 上可 `make manifest-check` / `make doctor` / `make status`，按精确 commit `fetch` 上游组件、`apply-series` 应用有序补丁，`build-mc` / `build-qemu` / `build-gem5` 目标就绪（组件未启用时为显式 stub），并可在干净主机或开发容器上运行仓库级检查；`make check` 在干净 checkout 上通过（M0 退出标准）。
**关联任务**：`INFRA-001k`、`INFRA-002t`、`INFRA-003t`、`INFRA-004t`、`INFRA-005t`、`INFRA-006t`、`INFRA-007t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：`Makefile`、`scripts/{manifest_check,fetch,apply_series,make_patch,fetch_refs,doctor,status,clean_work}.py`、`manifests/{components,references}.lock.toml`、`containers/dev/Dockerfile`
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
