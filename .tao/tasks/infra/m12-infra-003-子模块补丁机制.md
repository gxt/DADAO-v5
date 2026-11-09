# m12-infra-003: 子模块补丁机制（恢复 `INFRA-137t` 方向）

**模块**：infra
**项目里程碑**：M12
**可并行分片**：否（工具改动单写者；试点需 chipyard 源树独占）
**状态**：待开始

## 用户裁定（原话）

「我们当然需要给子模块打 patch，现在不做，以后也要做」（2026-11-09）

此前 2026-11-08 以「不调试 chipyard 本身」为由撤销了 `INFRA-137t`；该理由现被推翻，方向恢复。

## 背景与事实

- `tools/infra/apply_series.py` 只处理顶层组件：读 `component["patch_dir"]`/`patch_series`，在组件源树根应用。
- `manifests/components.lock.toml` 的组件体例没有子模块路径字段；`check_patch_tree.py` 的断言按顶层路径匹配。
- `m12-chipyard-003` 需要给 `generators/testchipip/src/main/resources/testchipip/vsrc/SimDRAM.v` 打补丁（`MEM_BASE` 未声明位宽，默认 32 位，Tiny 的 48 位基址会被截断），当前机制做不到。

## 目标

1. **manifest schema**：组件条目新增可选字段（如 `submodule_patches`），声明「子模块路径 → 补丁目录/系列」；不破坏现有顶层补丁组件。
2. **`apply_series.py`**：按声明进入子模块工作树（`<源树>/<子模块路径>`）应用对应系列，生成独立本地 commit；顶层与子模块两类互不影响。
3. **`make_patch.py`**：支持从子模块工作树导出补丁（一文件一补丁、`new file mode` 齐备）。
4. **`check_patch_tree.py`**：断言覆盖子模块补丁（HEAD diff、patch↔worktree 一致性、source-state clean）。
5. **`docs/Process-01`**：登记子模块补丁的组织方式与适用范围（不复制 chipyard 全量子模块，只登记实际要改的）。
6. **试点**：用 testchipip 的 `SimDRAM.v` 补丁（`MEM_BASE`/`ADDR_BITS` 位宽）验证端到端——补丁导出、`apply-series`、门控、`check-source-state`。

## 验收标准

1. 试点补丁可 `git apply --check` 重放；`apply-series` 后子模块工作树 state 正确（独立 commit、clean）
2. `check-patch-tree` 覆盖子模块且能对「补丁与源树不一致」报红（可达 FAIL 注入）
3. 顶层组件补丁行为不变（回归：现有 314 份仍 OK）
4. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0（两节点验证；改完执行 `make sync-node-repo`）
5. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

- 不批量纳入所有子模块（只登记实际要改的）
- 不改 chipyard 上游代码语义（只做补丁机制）
- 不动 `m12-chipyard-003` 的核实现（该任务返工另行处置）

## 说明

- 子模块工作树由 `fetch.py` 从本地镜像检出；补丁必须能在这份检出上重放，不能依赖联网。
- 构建/运行在 `server207`；仓库修改在主控机。
