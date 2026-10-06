# INFRA-046t: 测试产物落点与留存统一

**模块**：infra
**项目里程碑**：M4
**依赖**：`INFRA-045t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **背景（现状偏差，实测）**：`make test-codegen`（`INTEG-012t`，M3 CodeGen E2E 门控）的**运行产物**现落 **`.work/log/integ/codegen-e2e`**（`Makefile` 的 `CODEGEN_E2E_WORK` + `tools/integ/run_codegen_e2e.py` 的 `DEFAULT_WORK_DIR`）——**既非某模块下、也非 `.dadao/tests/`**，与下述规则不一致。
- **规则依据（原样引用用户 2026-10-06 裁定）**：
  > 测试产物落点**按测试本身定，不强制**；**若某模块的测试路径固定 → 放该模块目录下**（如 `tests/llvm/...`、`tests/qemu/...`）；**否则统一放 `.dadao/tests/`**（`ADR-0016 D6`）。**不强制留存**。
  - 规则已写入 `spec/Process-05-里程碑TDD规范.md §6`（「测试产物落点与留存」）；`ADR-0016 D6`：**测试向量运行产物根 = `.dadao/tests/`**（兜底）。
- **输入**（自包含；现状实测须以 `grep` 为准）：
  - `Makefile`：`CODEGEN_E2E_WORK = .work/log/integ/codegen-e2e`、`CODEGEN_E2E_LOG = .work/log/integ/test-codegen.log`、`test-codegen` 目标（`--work-dir $(CODEGEN_E2E_WORK)`）。
  - `tools/integ/run_codegen_e2e.py`：`DEFAULT_WORK_DIR = ".work/log/integ/codegen-e2e"`（`--work-dir` 默认值）；产物为每个用例的 `<stem>.prog.s` / `<stem>.s` / `<stem>.o` / `<stem>.bin`。
  - `.gitignore`：现有 `tests/codegen/*.s` / `*.o` / `*.bin`（旧落点的生成物忽略规则；`INFRA-045t` 把 `tests/codegen → tests/llvm/codegen` 后该模式**陈旧**）。
  - `INFRA-045t` 迁移后落点：`tests/llvm/codegen/`（M3 L3 向量 + `expected.yaml`）。
- **输出**：
  1. **落点选择（明确）**：`test-codegen` 运行产物 → **`tests/llvm/codegen-e2e/`**（**模块固定路径**）。
     - **理由**：(i) `test-codegen` 的测试用例/向量属 **llvm 模块**（`INFRA-045t` 后固定于 `tests/llvm/codegen/`），按规则「**模块测试路径固定 ⇒ 落该模块目录下**」；(ii) 与向量同处 `tests/llvm/`，便于对照检视。
     - **被否方案**：`.dadao/tests/codegen-e2e/`（`ADR-0016 D6` 兜底根）——仅适用于**无固定模块路径**的测试；本任务有固定模块路径，故**不**采用该兜底。
  2. `Makefile`：`CODEGEN_E2E_WORK` → **`tests/llvm/codegen-e2e`**；`test-codegen` **跑前清空**该目录（避免陈旧残留），跑后**保留**产物供检视（「不强制留存」——如需清理可删，不清亦合规）。
  3. `tools/integ/run_codegen_e2e.py`：`DEFAULT_WORK_DIR` → **`tests/llvm/codegen-e2e`**（`--work-dir` 默认值同步）。
  4. `.gitignore`：新增 **`tests/llvm/codegen-e2e/`**（生成物不入库，保持 `git status` 干净）；若 `INFRA-045t` 未清理旧模式 `tests/codegen/*.{s,o,bin}`，本任务一并校正为 `tests/llvm/codegen/` 对应模式。
  5. **日志落点不动**：`CODEGEN_E2E_LOG` 保持 `.work/log/integ/`——**日志**属 `.work` 日志留存纪律（ADR-0002/`.tao/README.md`），**非**「测试产物」，不在本规则调整范围。
- **约束**：
  - **只改落点，不改语义**：`test-codegen` 的用例、流水线（llc→llvm-mc→objcopy→qemu）、期望值、通过数**零改动**。
  - **保留探针/harness 的自清行为**（不强制留存）：其它 infra 探针/harness 在 `.work/` 的临时目录自清行为**保持**，本任务不引入「强制留存」。
  - 不引入新的外部依赖。
  - **与 `INFRA-045t` 串行**（同改 `run_codegen_e2e.py`/`Makefile`；`tests/llvm/` 结构须先由 `INFRA-045t` 建立）。
  - 临时目录 `/tmp/opencode/INFRA-046t/`；**不提交 git**；复杂命令输出留存 `.work/log/infra/`。

## 验收标准

1. **新落点产出**：`make test-codegen` EXIT=0（M3 15/15 不回归）；运行后 `tests/llvm/codegen-e2e/` 内存在产物（给 `ls -l tests/llvm/codegen-e2e/` 真实输出）。
2. **不回归 / 门控**：`make check` EXIT=0；`make check-no-residue` EXIT=0；`git status --untracked-files=all` 不显示 `tests/llvm/codegen-e2e/` 下文件（已被忽略）。
3. **路径清零**：`grep -rn "codegen-e2e" Makefile tools/` 均指向新落点（无 `.work/log/integ/codegen-e2e` 残留）；`run_codegen_e2e.py` 默认 `work_dir` = `tests/llvm/codegen-e2e`。
4. **语义零改动**：`test-codegen` 用例/期望值/通过数（15/15）与改前**逐项相等**（给 lit/驱动真实输出）。
5. **一键证据脚本**：`.work/evidence/INFRA-046t/run.sh`——非交互；任一检查失败即非零退出；**逐项打印**「检查名 + 期望/实际 + rc」；**内置反例自检**（`--inject`：把 `CODEGEN_E2E_WORK` 改回旧路径 `.work/log/integ/codegen-e2e`（或重命名新落点目录）→ 断言 **FAIL** → 还原 → 回绿），给真实输出与退出码；结尾**不得**用 `tee` 吞退出码（用 `rc=$?` / `PIPESTATUS` / `set -o pipefail`）。
6. **无残留**：`git status --untracked-files=all` 仅本任务应有改动（`Makefile` + `tools/integ/run_codegen_e2e.py` + `.gitignore` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
