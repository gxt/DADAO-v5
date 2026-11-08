# INFRA-140t: 把 `riscv-isa-sim` 纳入子模块镜像集（ISS-354）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-138t`（子模块镜像机制，已合入）
**状态**：待开始

## 用户授权（原话）

> 「做」

承接上一问「把 `toolchains/riscv-tools/riscv-isa-sim` 纳入镜像集，要不要做？」。

## 背景与事实

- `INFRA-138t` 建了 29 个 `lite = true` 子模块镜像（chipyard 上游最小集）。
- 但 conda 版 `riscv-tools` **不含 fesvr**；我们是从 `toolchains/riscv-tools/riscv-isa-sim` 源码编出 `libfesvr.a` 并装进 `<env>/riscv-tools` 的（`INFRA-133t` 记录）。
- 因此**全新机器**离线重建 RTL 环境时，还缺这一个源 ⇒ 已登记 `ISS-354`。
- 该子模块属于 chipyard 自身（`160000` gitlink，在 `.gitmodules` 中），**不是**新组件。
- 镜像已由 architect 预建：`.cache/submodules/toolchains__riscv-tools__riscv-isa-sim.git`（9.2 MiB，含锁定 commit `9c190a0…`）。

## 目标

1. **语义**：`lite` 保持「chipyard 上游最小集」原义，**不改**；为 `toolchains/riscv-tools/riscv-isa-sim` 条目新增标记 `dadao_extra = true`（并在 lock 注释里写明理由：conda 缺 fesvr，需源码编 fesvr）。
2. **`fetch.py`**：子模块选取条件由 `lite` 改为 **`lite or dadao_extra`**；`--populate-submodules` 建立镜像时同样按并集。
3. **`sync_cache.py`**：节点校验项由 `lite` 改为同一并集（当前 30 项）。
4. **文档**：
   - `docs/Process-01 §14`：补充 `lite` 与 `dadao_extra` 的区别（上游最小集 vs 本仓库额外需要）；
   - `.tao/knowledge/nodes.md §11.5`：同步说明并给出当前数量。
5. 关闭 `ISS-354`（`resolved_by: INFRA-140t`）。

## 范围 / 非范围

**在范围内**：`manifests/chipyard-submodules.lock.toml`（仅该条加标记 + 注释）、`tools/infra/fetch.py`、`tools/infra/sync_cache.py`、上述两处文档、本任务书、`milestones.md`、`issues.yaml`。

**不在范围**：其它子模块、`lite` 语义、组件镜像、chipyard 源码/构建。

## 验收标准

1. **离线复现（核心）**：临时树 + `GIT_ALLOW_PROTOCOL=file`（+ 关闭端口 proxy）跑 fetch 子模块初始化 ⇒ **30** 个（29 lite + `riscv-isa-sim`）全部在 lock commit，`submodule status` 无 `-`。
2. `sync_cache.py` 对两节点校验 **30** 项 PASS（镜像已同步后）；人为移走该镜像 ⇒ 该节点 FAIL。
3. **零回归**：原 29 个镜像与选取结果不变（数量现场统计并打印）；`make fetch` 组件部分逐行一致；`apply-series`/`check-patch-tree`/L1 与改前一致（并发任务导致的红需核实归属）。
4. 文档与实现一致（字段名 `dadao_extra`、选取并集、`sync_cache` 数量）。
5. 完成区 ≤30 行、无运行期路径。

## 说明

- 镜像已预建，`--populate-submodules` 对本条应为「已存在，跳过」；不要重新从公网克隆。
- 数量一律现场统计，不在代码/文档里写死；文档里的「30」以实测为准。
