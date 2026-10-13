# SPEC-110t: `Process-05 §6` 落点路径同步

**模块**：spec
**项目里程碑**：M4
**依赖**：`INFRA-045t`
**状态**：已验证

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
- 一键证据脚本 `.work/evidence/SPEC-110t/run.sh`：默认模式 **8/8 PASS，EXIT=0**；`--inject` 自检 **4/4 PASS，EXIT=0**（注入有效 → 旧路径断言 FAIL → 还原 md5 一致 → 回绿）。
- `make check` EXIT=0（`.work/log/spec/SPEC-110t-make-check.log`）；`make check-spec-refs` EXIT=0（`…-check-spec-refs.log`）；`make check-spec-codeblocks` EXIT=0（`…-check-spec-codeblocks.log`）。
- 失败原因：无。

**修改文件**：
- `spec/Process-05-里程碑TDD规范.md`（**仅 §6**：`+4 −3` 行）。
- `.tao/tasks/spec/SPEC-110t-Process-05落点路径同步.md`（完成区/自审/状态）。
- 证据与日志（均 gitignore，未入库）：`.work/evidence/SPEC-110t/run.sh`、`.work/log/spec/SPEC-110t-*.log`。
- **未动**：§1–§5、§7 及 §6 的「测试产物落点与留存」段；`llvm/test/MC|CodeGen/DADAO/` 上游 patch 路径保持（未改 `components/**`）。

**验收结果**（逐条，真实输出）：
1. **路径同步**：`spec/Process-05 §6` 现为 L1 `tests/llvm/lit/MC/DADAO/`、L2 `tests/llvm/lit/CodeGen/DADAO/`、L3 `tests/llvm/codegen/`（M3）+ `tests/llvm/codegen/m4/`（M4 独立清单）、其它落点 `tests/qemu/`、`tests/e2e/lit/`、`tests/scripts/`、`tests/vectors/isa/`。`grep -nE "tests/lit/MC/Dadao|tests/codegen|tests/lit/E2E|tests/lit/" spec/Process-05*.md` → **无匹配（EXIT=1）**（`llvm/test/...` 上游 patch 路径不在该模式内，保持）。证据脚本第 1/2 项 PASS。
2. **语义不动**：`git diff --stat -- spec/Process-05-里程碑TDD规范.md` = `1 file changed, 4 insertions(+), 3 deletions(-)`，仅 §6；证据脚本第 3 项以 awk 剥离 §6 后与 `HEAD:spec/...` **逐字节 diff 为空**（§1–§5 + §7 与改动前一致）。`MUST`/`SHOULD` 等级、三层定义、`**随产物入库**` 等字样均未动。
3. **门控**：`make check` `EXIT=0`（末行 `repository checks: PASS`；lit 34/34）；`make check-spec-refs` `EXIT=0`（`结果: PASS (0 violations)`）；`make check-spec-codeblocks` `EXIT=0`（`PASS (618 instruction line(s))`）。
4. **反例门控**：`run.sh --inject` → 把 §6 L1 改回 `tests/lit/MC/Dadao/`（md5 `46c502d7…`→`4233ca93…`，注入有效）→ 旧路径断言 **检测到并 FAIL**（`grep` 命中第 39 行）→ 还原（md5 回 `46c502d7…`）→ **回绿**（`grep` 无匹配 rc=1）；脚本结尾无 `tee`、逐项打印、任一失败非零退出。
5. **范围**：`git status --untracked-files=all` 仅本任务应有改动（`spec/Process-05…` + 任务书），证据脚本第 4 项 PASS；无其它文件、无残留。

**新发现/坑**：
- `tests/llvm/codegen/m4/` **当前尚未存在**（`ls` 无此目录）——它是 `TESTCASES-030t`/`032t` 的规划落点（M4 独立清单 `expected.yaml`，`TESTCASES-031m` 里程碑产物）。§6 按任务书要求前置登记该路径；后续 `TESTCASES-030t` 落地时创建，若届时改路径需再同步本处。**非本任务缺陷，不臆造目录**。
- `tests/llvm/lit/tools/DADAO/`（INFRA-045t 新增的 LLVM 工具测试落点）**未**写入 §6——任务书「其它落点」为显式四项枚举（qemu/e2e-lit/scripts/vectors-isa），未含该项；按任务书范围不擅自扩写。建议后续如有工具测试任务需要，再一并补 §6。
- git 对非 ASCII 路径默认以八进制转义 + 引号输出（`"spec/Process-05-\351…"`），比对路径须加 `-c core.quotepath=false`（或 `-z`）；本任务证据脚本首版因此误报 1 例，已修正后 8/8。
- 建议沉淀：`Process-05 §6` 落点已随 `INFRA-045t` 组件先行结构（`tests/llvm/lit/{MC,CodeGen}/DADAO`、`tests/llvm/codegen[/m4]`、`tests/qemu`、`tests/e2e/lit`、`tests/scripts`、`tests/vectors/isa`）同步。

**遗留问题**：
- ✅ 无未完成项。`tests/llvm/codegen/m4/` 目录待 `TESTCASES-030t` 创建（见「新发现/坑」），不属本任务范围。
> **用户裁定（2026-10-06）**：`Process-05 §6` 落点同步**单独一个 `SPEC`**（本任务）；因 `INFRA-045t` 重排 `tests/`（组件先行），`§6` 示例路径过期，须由 spec 模块同步（依据 `ADR-0012 D4`：仅 spec 模块可改 `spec/`）；同步后 `make check` EXIT=0。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：全局 `subagent_depth=1`，engineer 自主逐行审查（`git diff` 全量 + 最终 §6 通读 + 基线/事后门控输出对照），并按任务书验收 1–5 与硬约束逐条核验。

**判决**：实现完成，验收 1–5 均有真实输出支撑；无未修阻断项 → 状态置 `待验收`。

**审查意见（自主逐行）**：
- **逻辑/文本正确性**：改动为 3 行旧路径 → 4 行新路径（含新增「其它落点」行），无控制流/语义改动；新路径逐条回填 `INFRA-045t` 已落地结构：`tests/llvm/lit/MC/DADAO/`、`tests/llvm/lit/CodeGen/DADAO/`、`tests/llvm/codegen/`、`tests/qemu/`、`tests/e2e/lit/`、`tests/scripts/`、`tests/vectors/isa/` 均在 `find tests -type d` 实测存在。
- **边界/未测输入**：`tests/llvm/codegen/m4/` 实测不存在（规划路径，见完成区）；L3 原有 `tools/integ/`+`tools/testcases/` 与「独立 oracle 脚本随产物入库」保留未动；「必要时进 patch 的 `llvm/test/MC/DADAO/`」「patch 的 `llvm/test/CodeGen/DADAO/`」上游路径确认与本重排无冲突（补丁树内的 `llvm/test/`，非仓库 `tests/`），保持原样（未触及 `components/**`）。
- **防造假**：全部命令 `cmd > log 2>&1; rc=$?`，无 `tee`；注入自检给出 md5 前后与 grep 命中行，还原以 md5 相等 + `git diff --stat`（仅 `+4 −3`）证明；§1–§5/§7 用「剥离 §6 后与 `HEAD` 逐字节 diff」独立证明，而非肉眼判断。
- **范围/纪律**：仅 `spec/Process-05…` 与任务书；`git status --untracked-files=all` 无其它改动；临时文件仅 `/tmp/opencode/SPEC-110t/`；未提交 git；未改函数签名/未引入依赖。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 §6「其它落点」比旧文多一行（旧 3 行 → 新 4 行） | ❌不修（任务书要求） | 新增 `- **其它落点**：…` 行 | 任务书 §输出「其它落点（一并写明）」；证据脚本第 1 项覆盖 qemu/e2e-lit/scripts/vectors-isa 四项 |
| F2 `tests/llvm/codegen/m4/` 目录暂不存在 | ❌不修（范围外，如实登记） | —（§6 按任务书前置登记） | `ls tests/llvm/codegen/m4` → No such file；`TESTCASES-030t`/`031m` 规划落点 |
| F3 §6 未列 `tests/llvm/lit/tools/DADAO/` | ❌不修（不越界） | — | 任务书「其它落点」为显式四项枚举，未含工具落点；已在完成区提示后续可选补 |
| F4 证据脚本首版 git 路径比对因非 ASCII 转义误报 | ✅已修 | `git status` 加 `-c core.quotepath=false` | 重跑默认模式 8/8 PASS、EXIT=0 |

**约束自查**：只改 `spec/Process-05-里程碑TDD规范.md §6` + 任务书；未改 `contracts/**`/`components/**`/`Makefile`；未改函数签名；未引入依赖；临时目录 `/tmp/opencode/SPEC-110t/`；未提交 git。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑 evidence 脚本（baseline + inject）+ 独立注入反例（L2 路径改旧值）+ git diff/status 核验 + 旧路径 grep 全量扫描。

---

##### 1. 证据脚本审查

**`.work/evidence/SPEC-110t/run.sh`**：
- 4 个检查函数（新路径存在、旧路径缺席、§1-§5+§7 逐字节一致、git status 范围）+ 3 个门控（make check / check-spec-refs / check-spec-codeblocks）= baseline 模式 7 项 + inject 模式 4 项。
- FAIL 路径：每个 `check_*` 函数返回非零即触发 `fail()`，`FAILURES` 计数最终非零退出。✓
- 注入：sed 替换 §6 L1 旧路径 → md5 变化 → `check_old_paths_absent` 检测到 → 还原 → md5 一致 → 回绿。✓
- 结尾无 `tee`，退出码由 `FAILURES` 计数决定。✓
- **判定：证据脚本合格，不代写。**

---

##### 2. 重跑记录（reviewer 独立执行）

**Baseline（默认模式）**：EXIT=0，7/7 PASS + 1 项总结果 PASS
```
===== SPEC-110t baseline acceptance =====
[check] §6 new component-first paths present
  new path present: tests/llvm/lit/MC/DADAO/
  new path present: tests/llvm/lit/CodeGen/DADAO/
  new path present: tests/llvm/codegen/
  new path present: tests/llvm/codegen/m4/
  new path present: tests/qemu/
  new path present: tests/e2e/lit/
  new path present: tests/scripts/
  new path present: tests/vectors/isa/
[PASS] new paths present in §6
[check] old paths absent from spec/Process-05*.md
  old-path grep: no match (rc=1) -> absent
[PASS] old paths absent
[check] §1-§5,§7 unchanged vs HEAD
  §1-§5 + §7 identical to HEAD (only §6 differs)
[PASS] §1-§5,§7 byte-identical
[check] git status scope
  git status: only SPEC-110t files (spec file / task file)
[PASS] git status scope
[check] make check
[PASS] make check EXIT=0
[check] make check-spec-refs
[PASS] make check-spec-refs EXIT=0
[check] make check-spec-codeblocks
[PASS] make check-spec-codeblocks EXIT=0
-----------------------------------------
SPEC-110t EVIDENCE: PASS
```

**Inject（`--inject` 模式）**：EXIT=0，4/4 PASS
```
===== SPEC-110t counter-example injection (§6 L1 -> old path) =====
[PASS] injection effective (md5 changed 46c502d7 -> 4233ca93)
  old-path grep found:
    39:- **L1**：`tests/lit/MC/Dadao/`（必要时进 patch 的 `llvm/test/MC/DADAO/`）；
[PASS] injected old path detected -> assertion FAILED as expected
[PASS] restored (md5 back to 46c502d7)
  old-path grep: no match (rc=1) -> absent
[PASS] restored -> assertion green again
-----------------------------------------
SPEC-110t EVIDENCE: PASS
```

---

##### 3. 独立注入（reviewer 自选注入点，与 engineer 不同）

**注入目标**：§6 L2 路径 `tests/llvm/lit/CodeGen/DADAO/` → `tests/lit/`（匹配旧路径 grep 模式 `tests/lit/`）。

```
BEFORE=46c502d7c05a3342c57118d59e4dce24 AFTER=b81020c22bdcd331508a06990a03177a
[PASS] injection effective
40:- **L2**：`tests/lit/` 或 patch 的 `llvm/test/CodeGen/DADAO/`；MIR 用例；
[PASS] injected old path detected -> assertion would FAIL
RESTORED=46c502d7c05a3342c57118d59e4dce24
[PASS] restored md5 matches
[PASS] restored -> old paths absent again
```

- 注入有效：md5 从 `46c502d7` → `b81020c2`（不同注入点，md5 也不同，证明非重复）
- `check_old_paths_absent` grep 命中第 40 行 → 断言 FAIL ✓
- 还原：md5 回 `46c502d7` → grep 无匹配 → 回绿 ✓
- `git diff --stat` 还原后：`1 file changed, 4 insertions(+), 3 deletions(-)` — 与注入前一致 ✓

---

##### 4. 约束核验

| # | 约守项 | 结果 |
|---|--------|------|
| 1 | §6 仅含新路径，旧路径 grep EXIT=1（无匹配） | ✅ |
| 2 | `git diff` 仅 §6 变更（+4/−3），§1–§5 + §7 逐字节一致 | ✅ |
| 3 | `make check` EXIT=0 | ✅ |
| 4 | `make check-spec-refs` EXIT=0 | ✅ |
| 5 | `make check-spec-codeblocks` EXIT=0 | ✅ |
| 6 | `git status` 仅 `spec/Process-05…` + 任务书，无其它文件 | ✅ |
| 7 | 未提交 git | ✅ |
| 8 | 证据脚本结尾无 `tee`，FAIL 路径非零退出 | ✅ |
| 9 | 注入可还原（md5 回原值），还原后回绿 | ✅ |

**`git diff` 全文**（确认仅 §6）：
```diff
 ## 6. 落点（SHOULD）
 
-- **L1**：`tests/lit/MC/Dadao/`（必要时进 patch 的 `llvm/test/MC/DADAO/`）；
-- **L2**：`tests/lit/` 或 patch 的 `llvm/test/CodeGen/DADAO/`；MIR 用例；
-- **L3**：`tests/codegen/` + `tools/integ/` + `tools/testcases/`；独立 oracle 脚本**随产物入库**。
+- **L1**：`tests/llvm/lit/MC/DADAO/`（必要时进 patch 的 `llvm/test/MC/DADAO/`）；
+- **L2**：`tests/llvm/lit/CodeGen/DADAO/` 或 patch 的 `llvm/test/CodeGen/DADAO/`；MIR 用例；
+- **L3**：`tests/llvm/codegen/`（M3）+ `tests/llvm/codegen/m4/`（M4 独立清单）+ `tools/integ/` + `tools/testcases/`；独立 oracle 脚本**随产物入库**；
+- **其它落点**：QEMU 组件测试 `tests/qemu/`；E2E 驱动 `tests/e2e/lit/`；共享 harness `tests/scripts/`；契约向量 `tests/vectors/isa/`。
```

---

##### 5. 遗留判定：§6 未列 `tests/llvm/lit/tools/DADAO/`

任务书「其它落点」为**显式四项枚举**（qemu / e2e-lit / scripts / vectors-isa），未含 `tests/llvm/lit/tools/DADAO/`。engineer 按任务书范围不越界，完成区已标注建议后续补。**判定：不属本任务缺陷，不阻断验收。** 后续若有 LLVM 工具测试任务，届时再同步 §6。

---

##### 判决：**Accepted**

验收标准 1–5 全部通过（reviewer 独立重跑 + 独立注入 L2 反例验证）。约束无违反。§6 路径同步正确，§1–§5 + §7 逐字节未变，门控全绿，证据脚本合格且注入可失败可还原。
