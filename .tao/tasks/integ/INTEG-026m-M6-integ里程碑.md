# INTEG-026m: M6 integ 里程碑（整体收敛点）

**模块**：integ
**项目里程碑**：M6
**状态**：待开始
**目标**：M6 端到端闭环——驱动 `lli` 值级对拍 / Embench / lit 全量档；新 target **`test-m6`**（**opt-in，不进 `make check`**）；`make check` 收口。**M6 整体收敛点**——依赖的各模块 `m` 均 `里程碑` ⇒ 主会话置项目里程碑 `达成`（`spec/Process-04 §1`）。
**关联任务**：`INTEG-025t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tools/integ/**`（M6 E2E 驱动）、`Makefile` 的 `test-m6`（opt-in）目标
- `make test-m6` EXIT=0；不回归：`make check` EXIT=0
- 各模块 `m` 均 `里程碑`：`INFRA-052m`/`SPEC-125m`/`LLVM-067m`/`QEMU-054m`/`TESTCASES-040m`
- 跨模块影响已处置（无未处置项）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`；依赖模块 `m` 均达成后置项目里程碑 `M6` 为 `达成`）

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、产出存在性、`test-m6` 与 `check` 重跑、跨模块处置、判决）
