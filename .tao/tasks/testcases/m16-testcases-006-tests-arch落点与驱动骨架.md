# m16-testcases-006: `tests/arch` 落点与驱动骨架

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（PLAN/矩阵）、`m16-testcases-005`（`tests/shared/signature.py`）已合入
**可并行分片**：否（共享 `tests/arch.yaml`、`check-tests-index`）
**预估**：中（结构与骨架，不含用例）
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

`m16-testcases-004` 已产出 `tests/arch/PLAN.md`（目录/接口/字段/Process-09 草案）与 `tests/arch/data/vast-arch-inventory.md`（9 cfx × 3 平台）。本任务把 PLAN 的**落点与骨架**落地，让后续 cfx 用例有统一挂载点。

裁定见 `.tao/knowledge/discussing.md`「M16 三方差分（Vast arch）批次裁定」：只 Vast、三方签名一致、仿真不进常规门控、脚本/数据集中 `tests/arch/`。

## 要做

1. **目录落点**（按 PLAN）：
   - `tests/arch/run_arch.py`：唯一驱动；`--cfx <0|2|3|4|5|15|32|34|63>`、`--platforms qemu[,gem5,chipyard]`、`--cache-model on|off`（arch 默认 on）、`--self-test`；
   - `tests/arch/common/signature.py`：薄壳，只重导出 `tests/shared/signature.py` 的 `parse`/`compare`/`unwritten`/`Emitter`，不复制实现；
   - `tests/arch/common/` 的载体适配接口（qemu / gem5 / chipyard 三个后端骨架；未实现的后端必须显式失败，不静默回退）；
   - 不建空壳 cfx 子目录，按已有用例建。
2. **`tests/arch.yaml` 字段**：增加 `machine: vast`（固定）与载体类型（`asm` / `driver`）；保留 `platforms: [system]`。
3. **`check-tests-index`**：校验 `machine` 字段合法且 arch 条目只能是 `vast`；驱动型 case 的 `file` 允许指向驱动（不是 `.s`），但仍须存在。
4. **Tiny hmon 迁出**：`arch-hmon-001` 与 `tests/arch/hmon/` 迁到 `tests/unit/gem5/`（保留原测试可跑），从 `tests/arch.yaml` 删除；同步 `tests/arch/README.md`、相关门控/引用。
5. **README**：`tests/arch/README.md` 改为「Vast only；驱动型 case；脚本/数据集中本目录」。
6. **最小验证 case**：用一条现有 ptw 或 umon 用例，经 `run_arch.py --platforms qemu --cfx <n>` 跑通并产出签名流（只证明骨架可用，不新增语义用例）。

## 不做

- 不写新的 cfx 语义用例（后续任务）；
- 不实现 QEMU/gem5/RTL 的 cache 模型或 cfx5 命令；
- 不改 `docs/Process-09`（004 已改）；
- 不改组件源码。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `tests/arch/**`、`tests/unit/gem5/**`、`tests/arch.yaml`、`tests/arch/README.md`、`tools/testcases/inst` 或 `tools/testcases/arch` 的索引校验器、本任务书；
- 不写运行期路径；术语「寄存器组」；
- 未实现的后端必须 fail-closed（非零、说明缺件），不得假 PASS。

## 验证

运行期证据目录内的 `run.sh`：

1. `run_arch.py --self-test` 通过；坏输入（未知 cfx、未实现后端）各自非零；
2. 最小 case 在 QEMU 上跑通，签名流按 `tests/shared/signature.py` 解析；
3. `make check-tests-index` 通过，现场统计条数与 `arch.yaml` 一致；注入「tiny 条目」⇒ FAIL；
4. Tiny hmon 迁出后，原 gem5 测试仍可跑（或明确记录 gem5 环境缺失，不能假 PASS）；
5. `make check-knowledge-refs`、`make check-tasks` 记录 rc；
6. `--inject` 至少 2 路（tiny 条目 / 未实现后端假绿）⇒ FAIL，`cp`+md5 还原后回绿。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
