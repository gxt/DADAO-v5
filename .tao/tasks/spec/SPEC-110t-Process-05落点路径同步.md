# SPEC-110t: `Process-05 §6` 落点路径同步

**模块**：spec
**项目里程碑**：M4
**依赖**：`INFRA-045t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含）：
  - `spec/Process-05-里程碑TDD规范.md §6`（落点，SHOULD）——**现行文（实测）**：
    - **L1**：`tests/lit/MC/Dadao/`（必要时进 patch 的 `llvm/test/MC/DADAO/`）；
    - **L2**：`tests/lit/` 或 patch 的 `llvm/test/CodeGen/DADAO/`；MIR 用例；
    - **L3**：`tests/codegen/` + `tools/integ/` + `tools/testcases/`；独立 oracle 脚本**随产物入库**。
  - `INFRA-045t` 落地后的 `tests/` **组件先行**新结构：
    ```
    tests/{llvm/lit/{MC,CodeGen,tools}/DADAO, llvm/codegen, qemu, vectors/isa, e2e/lit, scripts}
    ```
    - `tests/lit/MC/Dadao/` → `tests/llvm/lit/MC/DADAO/`；`tests/codegen/` → `tests/llvm/codegen/`（M4 L3 独立清单落 `tests/llvm/codegen/m4/`）；`tests/lit/E2E/` → `tests/e2e/lit/`；
    - 新增 `tests/llvm/lit/CodeGen/DADAO/`（L2 结构测试落点）、`tests/llvm/lit/tools/DADAO/`（LLVM 工具测试落点）、`tests/qemu/`（QEMU 组件测试/夹具落点）；
    - `tests/scripts/`（共享 harness）、`tests/vectors/isa/`（契约向量）**不迁移**。
  - `.tao/adr/adr-0012-simrisc-0.5.4-update.md` 的 **D4**（`spec/` 只读策略调整）：「**只有 spec 模块的任务才能修改 `spec/` 下的文件**」——本任务为 spec 模块，符合；`INFRA-045t`（infra 模块）**不得**改 `spec/`（其任务书以此为由登记本处为跨模块遗留）。
  - 依据（用户裁定，转发）：`SPEC-104k`「修订记录（2026-10-06）」**待裁定点 5**——`Process-05 §6` 的示例路径随 `INFRA-045t` 重排而过期，须由 **spec 模块**同步任务落地。
- **输出**：
  - `spec/Process-05-里程碑TDD规范.md §6` 正文更新——把落点示例改为组件先行路径：
    - **L1**：`tests/llvm/lit/MC/DADAO/`（必要时进 patch 的 `llvm/test/MC/DADAO/`）；
    - **L2**：`tests/llvm/lit/CodeGen/DADAO/` 或 patch 的 `llvm/test/CodeGen/DADAO/`；MIR 用例；
    - **L3**：`tests/llvm/codegen/`（M3）+ `tests/llvm/codegen/m4/`（M4 独立清单）+ `tools/integ/` + `tools/testcases/`；独立 oracle 脚本**随产物入库**；
    - **其它落点**（一并写明，与 `INFRA-045t` 新结构一致）：QEMU 组件测试 `tests/qemu/`；E2E 驱动 `tests/e2e/lit/`；共享 harness `tests/scripts/`；契约向量 `tests/vectors/isa/`。
  - **仅改 §6 的示例路径**；§1–§5、§7 与规范实质（MUST/SHOULD 等级、三层定义）不动。
- **约束**：
  - **只同步路径、不改规范语义**：§6 为 SHOULD（落点示例）；**不得**改 §2 三层定义/期望值来源、§3 规模、§4 移植、§5 反例门控、§7 关系。
  - **上游 patch 路径复核**：`llvm/test/MC/DADAO/`、`llvm/test/CodeGen/DADAO/` 属上游 LLVM 测试树（补丁内），与 `tests/` 重排无关——确认仍有效后保持；若与 `INFRA-045t` 新结构产生冲突，**停下报告**（不臆改）。
  - **文件范围**：仅 `spec/Process-05-里程碑TDD规范.md`；越界须披露。
  - **门控**：`make check` EXIT=0（含 `check-spec-refs`/`check-spec-codeblocks`）。
  - **串行**：`spec/` 为共享文件，与其它改 `spec/` 的任务**串行**；依赖 `INFRA-045t`（新路径已落地）。
  - 临时目录 `/tmp/opencode/SPEC-110t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`。

## 验收标准

1. **路径同步**：`spec/Process-05-里程碑TDD规范.md §6` 仅含新路径（`tests/llvm/lit/MC/DADAO/`、`tests/llvm/lit/CodeGen/DADAO/`、`tests/llvm/codegen/`（+`m4/`）、`tests/qemu/`、`tests/e2e/lit/`、`tests/scripts/`、`tests/vectors/isa/`）；`grep -nE "tests/lit/MC/Dadao|tests/codegen|tests/lit/E2E|tests/lit/" spec/Process-05*.md` **无旧路径**（`llvm/test/...` 上游 patch 路径除外）。
2. **语义不动**：§1–§5、§7 与改动前**逐字一致**（`git diff` 证明仅 §6 路径变更）；`MUST`/`SHOULD` 等级与三层定义不变。
3. **门控**：`make check` EXIT=0（含 `check-spec-refs`/`check-spec-codeblocks`）；给真实命令输出与退出码。
4. **反例门控**：`.work/evidence/SPEC-110t/run.sh`（非交互、失败非零、逐项打印、结尾无 `tee`）对注入反例（把 §6 的 L1 示例路径改回 `tests/lit/MC/Dadao/`）**必须 FAIL**（断言捕获），还原后回绿；给真实输出与退出码。
5. `git status --untracked-files=all` 仅本任务应有改动（`spec/Process-05…` + 任务书）；未改其它文件。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
> **用户裁定（2026-10-06）**：`Process-05 §6` 落点同步**单独一个 `SPEC`**（本任务）；因 `INFRA-045t` 重排 `tests/`（组件先行），`§6` 示例路径过期，须由 spec 模块同步（依据 `ADR-0012 D4`：仅 spec 模块可改 `spec/`）；同步后 `make check` EXIT=0。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
