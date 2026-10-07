# SPEC-117t: `Process-05 §6` 落点规则补正（`.dadao/tests/` 口径）

**模块**：spec
**项目里程碑**：M5
**依赖**：`INFRA-048t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **背景**：`spec/Process-05-里程碑TDD规范.md §6` 现行「测试产物落点与留存」只写了「按测试本身定；模块固定路径 ⇒ 落模块目录下；否则 `.dadao/tests/`（`ADR-0016 D6`）；不强制留存」。**M5 起落点口径收紧**（用户 2026-10-06 裁定）：**默认 `.dadao/tests/`；只有"难以放进 `.dadao/`"才退到模块目录；判据 = "能否用配置选项解决"——能配置解决的一律必须放 `.dadao/`**。`INFRA-048t` 已把 `test-codegen`/`test-elf`/lit 落点迁到 `.dadao/tests/`，本任务把该口径写入规范正文，使规范与实现一致。
- **输入（自包含）**：
  - `spec/Process-05-里程碑TDD规范.md §6`（现行文本）。
  - 用户 2026-10-06 裁定原话（见 `.tao/knowledge/milestones.md`「生成物落点口径」与「落点规则生效时点」）：**默认 `.dadao/tests/`**；**判据 = 能配置解决 ⇒ 必进 `.dadao/`**；**`.work/log`/`.work/evidence` 不算"生成物"、不动**；**M4 已完成落点不动、自 M5 起按新规则**。
  - `ADR-0016 D6`（测试向量运行产物根 = `.dadao/tests/`）、`ADR-0016 D8`（真实路径）。
  - `INFRA-048t` 迁移后的实际落点（`.dadao/tests/{codegen-e2e,elf-e2e,lit-output/<name>}`）。
- **输出**：
  - `spec/Process-05-里程碑TDD规范.md §6` 修订：把「测试产物落点与留存」改写为**明确默认 + 判据**——① **默认落 `.dadao/tests/`**（`ADR-0016 D6`）；② 仅当**用配置选项**仍"难以放进 `.dadao/`"时才退到该模块目录；③ **落点路径须经 `manifests/install-dirs.lock.toml`/`tools/infra/paths.py` 解析（禁硬编码，`ADR-0016 D7/D8`）**；④ **`.work/log`/`.work/evidence` 不算"生成物"、不受本规则约束**；⑤ **M4 及以前的落点不动，自 M5 起生效**；⑥ 保留「不强制留存」。
- **约束（硬）**：
  - **只改 `Process-05 §6` 落点规则正文**，不改规范其它节语义、不改 `ADR`（ADR 只记决策）。
  - **不产向量、不改 `Makefile`/`tools/`**（落点实现归 `INFRA-048t`）。
  - `spec/` 为共享文件，与其它改 `spec/` 的任务（`SPEC-113t`~`116t`）**串行**。
  - `make check`（`check-spec-refs` 等）EXIT=0；`spec/README.md` 投影表如含 `Process-05` 相关行需同步（无则跳过）。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-117t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **规则落地**：`Process-05 §6` 含「默认 `.dadao/tests/` + 判据（能配置解决 ⇒ 必进 `.dadao/`）+ 经定位机制解析（`ADR-0016 D7/D8`）+ `.work/log`/`.work/evidence` 不动 + 自 M5 起」五要点（`grep`/`sed` 真实输出）。
2. **与实现一致**：§6 示例/口径与 `INFRA-048t` 迁移后的实际落点（`.dadao/tests/{codegen-e2e,elf-e2e,lit-output}`）不矛盾。
3. **门控**：`make check` EXIT=0（`repository checks: PASS`）；给真实输出。
4. **一键证据脚本**：`.work/evidence/SPEC-117t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（删去「默认 `.dadao/tests/`」句/把判据改回旧措辞 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
5. **无残留**：`git status --untracked-files=all` 仅 `spec/Process-05-里程碑TDD规范.md`（及必要的 `spec/README.md` 投影行）+ 本任务书。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 逐条核五要点 + 判决）
