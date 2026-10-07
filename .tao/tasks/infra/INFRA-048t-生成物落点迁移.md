# INFRA-048t: 生成物落点迁移（`test-codegen`/`test-elf`/lit → `.dadao/tests/`）

**模块**：infra
**项目里程碑**：M5
**依赖**：`INFRA-047t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **背景与规则（原样引用用户 2026-10-06 裁定，见 `.tao/knowledge/milestones.md`）**：
  > **生成物落点口径**：运行产物**默认为 `.dadao/tests/`**；**只有"难以放进 `.dadao/`"时**才退到**当前模块对应目录**；判据 = **"能否用配置选项解决"——能配置解决的一律不算"难"，必须放 `.dadao/`**。
  >
  > **落点规则生效时点**：**M4 已完成/在做的测试落点一律不动**；**自 M5 起按新规则**。M5 起步须迁移：① `test-codegen` 运行产物 `tests/llvm/codegen-e2e` → **`.dadao/tests/codegen-e2e`**；② `test-elf` 运行产物（`run_elf_e2e.py` 的 `DEFAULT_WORK_DIR` / `Makefile`）→ **`.dadao/tests/elf-e2e`**；③ lit 的 `test_exec_root`（现 `<build>/test-output/<name>`，在 `.work/build/llvm/` 内）→ **`.dadao/tests/lit-output/<name>`**。**`.work/log`（日志）与 `.work/evidence`（证据）不算"生成物"、不动**。
  - `.dadao/tests/` 已是安装根（`ADR-0016 D6`）下的测试产物根；路径经 `tools/infra/paths.py`（`test_artifacts_dir`）解析（**禁硬编码**）。
- **输入（自包含；现状须以 `grep`/`sed` 实测为准）**：
  - `Makefile`：`CODEGEN_E2E_WORK = tests/llvm/codegen-e2e`、`CODEGEN_ELF_WORK = .work/codegen-e2e-elf`、`test-codegen`/`test-elf` 目标（`--work-dir $(…)`）。
  - `tools/integ/run_codegen_e2e.py`：`DEFAULT_WORK_DIR = "tests/llvm/codegen-e2e"`。
  - `tools/integ/run_elf_e2e.py`：`DEFAULT_WORK_DIR`（当前 `.work/codegen-e2e-elf` 或等价，**以实测为准**）。
  - lit 的 `test_exec_root`：`tests/llvm/lit/MC/DADAO/lit.cfg.py`、`tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`、`tests/e2e/lit/**`（现指向 `<build>/test-output/<name>`，在 `.work/build/llvm/` 内）。
  - `.gitignore`：现有 `tests/llvm/codegen-e2e/` 等生成物忽略规则。
- **输出**：
  1. `Makefile`：`CODEGEN_E2E_WORK` → **`$(TEST_ARTIFACTS_DIR)/codegen-e2e`**；`CODEGEN_ELF_WORK` → **`$(TEST_ARTIFACTS_DIR)/elf-e2e`**；`test-codegen`/`test-elf` 目标同步（跑前清空、跑后按需保留）。
  2. `tools/integ/run_codegen_e2e.py`、`tools/integ/run_elf_e2e.py`：`DEFAULT_WORK_DIR` 指向 `.dadao/tests/{codegen-e2e,elf-e2e}`（可经 `paths.py` 解析；`--work-dir` 默认值同步）。
  3. lit `test_exec_root` → **`.dadao/tests/lit-output/<name>`**（三处 `lit.cfg.py` 或等价配置；经 `paths.py`/相对仓库根解析）。
  4. `.gitignore`：清理 `tests/llvm/codegen-e2e/` 旧模式（新落点 `.dadao/` 整体已被忽略），保留 M4/E2E 其它必要忽略规则。
- **约束（硬）**：
  - **只改落点，不改语义**：`test-codegen` 用例/流水线/期望值/通过数（15/15）、`test-elf`（5/5）、lit 用例与通过数**零改动**。
  - **`.work/log`/`.work/evidence` 不动**（日志/证据留存纪律，`.tao/README.md`）。
  - **与 `INFRA-047t` 串行**（同改 `Makefile`）。
  - `Makefile` 为共享文件，与其它改 `Makefile` 的任务**串行**。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/INFRA-048t/`；**不提交 git**；复杂命令输出留存 `.work/log/infra/`（**禁 `tee`**）。
  - **重建成本申报**：本任务不触发重建（仅改落点/路径）；若为验收需跑 `test-codegen`/`test-elf`，其前置 `build-*` 视现状增量，开工前说明。

## 验收标准

1. **新落点产出**：`make test-codegen` EXIT=0（15/15）后，`.dadao/tests/codegen-e2e/` 内有产物；`make test-elf` EXIT=0（5/5）后，`.dadao/tests/elf-e2e/` 内有产物；给 `ls -l` 真实输出。
2. **lit 落点**：`make check-lit` EXIT=0（60/60）后，`.dadao/tests/lit-output/<name>` 有输出（给 `ls`）；`grep -rn "test-output" tests/**/lit.cfg.py` 不再指向 `.work/build`。
3. **路径清零**：`grep -rn "tests/llvm/codegen-e2e\|\.work/codegen-e2e-elf" Makefile tools/ .gitignore | grep -v __pycache__` 无旧落点残留（历史归档/任务书正文除外）；默认 `work_dir` 指向新落点。
4. **语义零改动**：`test-codegen` 15/15、`test-elf` 5/5、`check-lit` 60/60 与改前**逐项相等**（给真实输出）。
5. **门控**：`make check` EXIT=0；`make check-no-residue` EXIT=0；`git status --untracked-files=all` 不显示 `.dadao/` 下生成物。
6. **一键证据脚本**：`.work/evidence/INFRA-048t/run.sh`——非交互、失败非零、逐项打印、**内置注入自检**（把某个 `*_WORK` 改回旧路径/重命名新落点目录 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出与退出码。
7. **无残留**：`git status --untracked-files=all` 仅本任务应有改动（`Makefile` + `tools/integ/run_*_e2e.py` + `lit.cfg.py` + `.gitignore` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**〔改 `DEFAULT_WORK_DIR`/移走新落点目录〕+ 约束核验 + 判决）
