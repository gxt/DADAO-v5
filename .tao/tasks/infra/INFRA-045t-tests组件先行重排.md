# INFRA-045t: `tests/` 组件先行重排

**模块**：infra
**项目里程碑**：M4
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含；现状实测须以 `find`/`grep` 为准）：
  - 现有 `tests/` 树（实测）：`tests/lit/MC/Dadao/`（`.s` + `lit.cfg.py`，由 `make check-lit` 运行）、`tests/lit/E2E/`（`.test` + `lit.cfg.py`，引用 `%e2e_dir` = `tests/e2e/`）、`tests/e2e/`（`smoke_*.s` 源）、`tests/codegen/`（M3 `.ll` + `expected.yaml`，由 `make test-codegen` 消费）、`tests/vectors/isa/`、`tests/scripts/`（共享 harness：`run_qemu_test.py`/`build_test_binary.py`/`codegen_crt0.s`/`trampoline.bin`/`gen_trampoline.py`/`verify_harness_dump.py`）。
  - 消费者（实测，须同步更新路径）：
    - `Makefile`：`check-lit`（`$(LIT_BIN) tests/lit/MC/Dadao tests/lit/E2E -v`）、`test-codegen`（`--crt0 tests/scripts/codegen_crt0.s`/`--trampoline tests/scripts/trampoline.bin`，向量/清单经 `run_codegen_e2e.py` 默认路径）。
    - `tools/integ/run_codegen_e2e.py`：`DEFAULT_VECTORS_DIR="tests/codegen"`、`DEFAULT_EXPECTED="tests/codegen/expected.yaml"`。
    - `tools/integ/check_interface_alignment.py`：`lit_dir = tests/lit/MC/Dadao`（LLVM lit format 族覆盖断言）。
    - `tools/llvm/check_lit_bytes.py`：`DEFAULT_LIT_DIR = tests/lit/MC/Dadao`。
    - `tools/testcases/validate_codegen_vectors.py`：`tests/codegen/` 路径。
    - 注释/文档引用（非执行必需，但须一致）：`tools/llvm/gen_asm_list.py`、`tools/llvm/validate_instrinfo.py`、`tests/*/lit.cfg.py` 内的路径推断注释。
  - **对照**：上游 LLVM 测试组织 `llvm/test/{MC,CodeGen,tools}/`（**组件先行**）；本任务对齐其**结构**，不迁移上游用例。
- **输出**（目标结构，组件先行）：
  ```
  tests/
  ├── llvm/
  │   ├── lit/
  │   │   ├── MC/DADAO/        ← tests/lit/MC/Dadao/（含 lit.cfg.py）
  │   │   ├── CodeGen/DADAO/   （新增；L2 结构测试落点）
  │   │   └── tools/DADAO/     （新增；LLVM 工具测试落点）
  │   └── codegen/             ← tests/codegen/（M3 L3 向量 + expected.yaml）
  ├── qemu/                    （新增；QEMU 组件测试/夹具落点）
  ├── vectors/isa/             （不迁移）
  ├── e2e/                     （不迁移；smoke_*.s 源）
  │   └── lit/                 ← tests/lit/E2E/（.test 驱动 + lit.cfg.py）
  └── scripts/                 （不迁移；共享 harness）
  ```
  1. **迁移**（用 `git mv` 保历史）：`tests/lit/MC/Dadao/` → `tests/llvm/lit/MC/DADAO/`；`tests/codegen/` → `tests/llvm/codegen/`；`tests/lit/E2E/` → `tests/e2e/lit/`（`%e2e_dir` 改指 `..`，即 `tests/e2e/`）。
  2. **新增**：`tests/llvm/lit/CodeGen/DADAO/` 与 `tests/llvm/lit/tools/DADAO/`（各含 `lit.cfg.py` + `README.md`，作为后续 L2/工具测试落点；内容可暂空）；`tests/qemu/`（含 `README.md`，QEMU 组件测试/夹具落点）。
  3. **更新消费者**：`Makefile`（`check-lit` → `tests/llvm/lit/MC/DADAO tests/e2e/lit`；`test-codegen` 的向量/清单路径或经 `run_codegen_e2e.py` 默认值统一）、`tools/integ/run_codegen_e2e.py`、`tools/integ/check_interface_alignment.py`、`tools/llvm/check_lit_bytes.py`、`tools/testcases/validate_codegen_vectors.py` 及上述注释引用。
  4. **lit 路径**：迁移后的 `lit.cfg.py` 内部「推测 `<repo>` 相对层级」的注释/回退路径同步修正（`tests/llvm/lit/MC/DADAO` 与 `tests/e2e/lit` 的深度不同）。
- **约束**：
  - **只搬不改语义**：迁移**不得**改动测试内容/期望值（`.s`/`.test`/`.ll`/`expected.yaml` 内容逐字节一致）；lit 通过数应与迁移前**逐项相等**（MC 22 / E2E 3；`test-codegen` 15/15）。
  - **`tests/scripts/` 与 `tests/vectors/isa/` 不迁移**（共享 harness/契约向量，非组件测试）。
  - **全库 grep 穷尽**：`grep -rn "tests/lit/MC/Dadao\|tests/lit/E2E\|tests/codegen"`（含 `Makefile`/`tools/`/`tests/`），逐个更新；**排除** `.tao/archive/**` 与历史记录。
  - **不改 `spec/`（模块边界，`ADR-0012 D4`）**：`spec/Process-05 §6` 记有旧落点（`tests/lit/MC/Dadao/`/`tests/codegen/`），本任务**不得**改（仅 spec 模块任务可改 `spec/`）；该处过期属**跨模块影响**，须由主会话裁定另立 spec 同步任务（登记为遗留，见 `SPEC-104k`「修订记录」待裁定点 5）。
  - **`Makefile` 为共享文件**：与其它改 `Makefile` 的任务**串行**。
  - 与 `SPEC-109t`/`TESTCASES-029t`/`030t`/`LLVM-050t`~`054t`/`INTEG-016t` **串行**（本任务先行——它们按新路径落向量；见 `SPEC-104k` 串行链）。
  - 临时目录 `/tmp/opencode/INFRA-045t/`；**不提交 git**；复杂命令输出留存 `.work/log/infra/`。

## 验收标准

1. **新结构存在**：`tests/llvm/lit/MC/DADAO/`、`tests/llvm/lit/CodeGen/DADAO/`、`tests/llvm/lit/tools/DADAO/`、`tests/llvm/codegen/`、`tests/qemu/`、`tests/e2e/lit/` 均存在；旧路径 `tests/lit/MC/Dadao`、`tests/lit/E2E`、`tests/codegen` **已不存在**（给 `find` 输出）。
2. **不回归**：`make check` EXIT=0；`make check-lit` EXIT=0 且通过数**与迁移前逐项相等**（≥ MC 22 + E2E 3；给 lit 真实输出）；`make test-codegen`（M3 15/15）EXIT=0。
3. **内容零改动**：迁移文件的 blob 与迁移前一致（`git diff --stat`/`git status` 显示为 rename；对 `tests/llvm/codegen`、`tests/llvm/lit/MC/DADAO` 逐个 `md5sum` 前后核对）。
4. **路径清零**：`grep -rn "tests/lit/MC/Dadao\|tests/lit/E2E\|tests/codegen" Makefile tools/ tests/`（排除 `.tao`/`.work`）**无残留**；`check-interface`（依赖 `check_lit_bytes.py` 新路径）EXIT=0。
5. **新落点可用**：`tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`、`tests/llvm/lit/tools/DADAO/lit.cfg.py`、`tests/e2e/lit/lit.cfg.py` 均存在且 `llvm-lit` 可识别（对空套件给 EXIT=0 或不纳入 `check-lit` 的明确说明）。
6. **无残留**：`make check-no-residue` EXIT=0；`git status --untracked-files=all` 仅本任务应有改动（迁移 + 新目录 + `Makefile` + 工具路径 + 任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。
7. **反例门控**：一键证据脚本 `.work/evidence/INFRA-045t/run.sh`（非交互、失败非零、逐项打印、结尾无 `tee`）——`--inject`：把 `Makefile check-lit` 路径改回旧路径（或重命名迁移后的某目录）→ `make check-lit` **FAIL** → 还原 → 回绿；给真实输出与退出码。

## 完成区

**测试结果**：
- 迁移前基线（`.work/log/infra/INFRA-045t/baseline-*.log`）：`make check-lit` EXIT=0，**MC=30 / E2E=4**（Total 34）；`make test-codegen` EXIT=0，**15/15**；`make check` EXIT=0。
- 迁移后（`.work/log/infra/INFRA-045t/post-*.log`）：`make check-lit` EXIT=0，**MC=30 / E2E=4**（逐项与迁移前相等）；`make test-codegen` EXIT=0，15/15；`make check` EXIT=0；`make check-interface` EXIT=0；`make check-no-residue` EXIT=0；`python3 tools/testcases/validate_codegen_vectors.py` EXIT=0（58 checks）；`python3 tools/llvm/check_lit_bytes.py` EXIT=0（118 patterns）。
- 一键证据脚本 `.work/evidence/INFRA-045t/run.sh`：默认模式 **20/20 PASS，EXIT=0**；`--inject` 自检 **PASS**（注入旧路径后 `make check-lit` **EXIT=2**；还原 md5 一致后 `make check-lit` **EXIT=0**）。

**修改文件**：
- 迁移（`git mv` 保历史，共 53 文件 = 50 个 0-diff 纯 rename + 3 个「rename + 路径修正」）：
  - `tests/lit/MC/Dadao/`（31 文件）→ `tests/llvm/lit/MC/DADAO/`
  - `tests/codegen/`（17 文件）→ `tests/llvm/codegen/`
  - `tests/lit/E2E/`（5 文件）→ `tests/e2e/lit/`
- 新增：`tests/llvm/lit/CodeGen/DADAO/{lit.cfg.py,README.md}`、`tests/llvm/lit/tools/DADAO/{lit.cfg.py,README.md}`、`tests/qemu/README.md`
- 路径更新：`Makefile`（`check-lit` 路径 + `test-codegen` 注释）、`tools/integ/run_codegen_e2e.py`（docstring + `DEFAULT_VECTORS_DIR`/`DEFAULT_EXPECTED`）、`tools/integ/check_interface_alignment.py`（`lit_dir` + 注释 + 报错串）、`tools/llvm/check_lit_bytes.py`（`DEFAULT_LIT_DIR` + docstring + help）、`tools/testcases/validate_codegen_vectors.py`（`VEC_DIR` + docstring）、`tools/llvm/gen_asm_list.py`（注释）、`tools/llvm/validate_instrinfo.py`（注释）、`tests/scripts/codegen_crt0.s`（注释）、`tests/llvm/lit/MC/DADAO/lit.cfg.py`（回退路径深度 4→5）、`tests/e2e/lit/lit.cfg.py`（回退路径注释 + `%e2e_dir` 改指 `..`）、`tests/llvm/codegen/expected.yaml`（首行注释，见下用户裁定）。
- **未动**（模块边界/非本任务）：`spec/**`、`contracts/**`、`components/**`、`.gitignore`（见遗留）。

**验收结果**（逐条，真实输出）：
1. **新结构存在 / 旧路径不存在**：`find tests -type d` 输出为：
   `tests/llvm/lit/MC/DADAO`、`tests/llvm/lit/CodeGen/DADAO`、`tests/llvm/lit/tools/DADAO`、`tests/llvm/codegen`、`tests/qemu`、`tests/e2e/lit` 均存在；`old path absent: tests/lit/MC/Dadao`、`tests/lit/E2E`、`tests/codegen`、`tests/lit` 均 absent（空目录已 `rmdir`）。见证据脚本第 1/1b 项（20/20 PASS）。
2. **不回归**：迁移前后 `make check-lit` 均 EXIT=0 且 **MC=30 / E2E=4 逐项相等**（≥ 任务书下限 MC22+E2E3）；`make test-codegen` 均 EXIT=0 且 15/15；`make check` 均 EXIT=0。
3. **内容零改动**：`git status` 显示 50 个纯 `R ` rename + 3 个 `RM `（rename+改）；对全部 53 个迁移文件做 `git hash-object`(新) ↔ `HEAD:<旧路径>` blob 对比，**仅 3 个已批准文件不同**（`tests/e2e/lit/lit.cfg.py`、`tests/llvm/lit/MC/DADAO/lit.cfg.py`、`tests/llvm/codegen/expected.yaml`），其余 **50/53 逐字节一致**（md5 前后表：`.work/log/infra/INFRA-045t/{pre,post}-migrate-md5.txt`）。
4. **路径清零**：`grep -rn "tests/lit/MC/Dadao\|tests/lit/E2E\|tests/codegen" Makefile tools/ tests/` **无匹配（EXIT=1）**；`make check-interface` EXIT=0（含 `LLVM lit ↔ opcodes.yaml PASS` + `LLVM lit format 族覆盖 9/9 PASS`，均走新路径 `tests/llvm/lit/MC/DADAO`）。
5. **新落点可用**：三个 `lit.cfg.py` 均存在；`tests/e2e/lit` 由 `make check-lit` 识别并通过 4/4；两个占位套件由 `llvm-lit` 解析成功——单独跑空目录时 lit 报 `contained no tests` 并以 EXIT=2 退出（lit 对「零测试路径」的固有行为），故按验收⑤的「**不纳入 `check-lit` 的明确说明**」分支处理（README 明确声明），并附「与 MC 合并运行 → 两 config 均被加载、0 自有测试、总 EXIT=0」证据（`.work/log/infra/INFRA-045t/evidence-placeholder-lit.log`）。
6. **无残留**：`make check-no-residue` EXIT=0；`git status --untracked-files=all` 仅本任务应有改动（迁移 + 5 个新文件 + 8 个消费者 + 任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。
7. **反例门控**：`.work/evidence/INFRA-045t/run.sh --inject` → `Makefile check-lit` 路径改回旧值（md5 `7b0546c…`→`9126ebf…`，注入有效）→ `make check-lit` **EXIT=2（FAIL）** → 还原（md5 回 `7b0546c…`）→ `make check-lit` **EXIT=0（回绿）**；脚本结尾无 `tee`、逐项打印、任一失败非零退出。

**新发现/坑**：
- **lit 空目录非 0 退出**：`llvm-lit <空套件目录>` 打印 `warning: input '...' contained no tests` 后以 **EXIT=2** 退出（`error: did not discover any tests for provided path(s)`）。新增落点若想「空套件 EXIT=0」必须放入至少 1 个测试（如 `UNSUPPORTED:` 标记），否则只能走「不纳入 check-lit + 明确说明」分支。本任务采用后者。
- **`config.llvm_tools_dir` 在直接 `llvm-lit` 调用下为空**：`make check-lit` 直接调 `$(LIT_BIN) <dirs>`（无 site config）、且环境 `LLVM_TOOLS_DIR` 未设，故 **MC/E2E 的「推测 `<repo>` 相对层级」回退分支确被实际执行**；MC 5 层、E2E 3 层的深度修正是**被真实运行验证**的（MC 30/30、E2E 4/4）。
- **`tests/scripts/__pycache__/`** 存在于工作树（`.gitignore` 已忽略），非本次产生、无残留告警。
- **`.gitignore` 的 `tests/codegen/*.{s,o,bin}` 模式迁移后已陈旧**（不再覆盖 `tests/llvm/codegen/`）；`INFRA-046t` 任务书已明确认领此修正，且本任务 `test-codegen` 运行产物落 `.work/log/integ/codegen-e2e`，未产生仓库残留。
- **`make check` 的 check-lit 注释**（`Makefile:308-309`）写「MC (22/22) + E2E (3/3)」与实际 **30/4** 不符——属既有陈旧注释，非本任务引入，未改动。
- 建议沉淀：`tests/` 组件先行结构（`llvm/lit/{MC,CodeGen,tools}/DADAO`、`llvm/codegen`、`qemu`、`e2e/lit`、不迁移的 `vectors/isa`+`scripts`）及迁移用 `git mv`+消费者清单。

**遗留问题**：
- ⏸ **`spec/Process-05 §6` 旧落点**（`tests/lit/MC/Dadao/`/`tests/codegen/`）未改——`ADR-0012 D4` 限定仅 spec 模块任务可改 `spec/`；任务书已明示登记为跨模块影响、由 `SPEC-110t` 同步。**本任务未动 `spec/`**。
- ⏸ **`.gitignore` 陈旧模式**（`tests/codegen/*.{s,o,bin}`）交 `INFRA-046t`（其任务书已认领）。
- ⏸ **两个占位 lit 套件**（`CodeGen/DADAO`、`tools/DADAO`）当前零测试、未入门控；由后续 L2/工具测试任务填充并接入门控（README 已写明接入方法）。
- ❌ 无其它未完成项。

> **用户裁定（2026-10-06，采纳）**：E2E 落点 = **`tests/e2e/`**（跨组件，**不塞** `llvm/`）；本任务 `tests/lit/E2E → tests/e2e/lit` 符合该裁定（`tests/e2e/` 桶内），**无需改动**。原「待裁定点 2」定案，见 `SPEC-104k`「修订记录（2026-10-06·2）」C.2。
>
> **用户裁定（2026-10-06，本任务执行期，原话）**：迁移 `tests/codegen/expected.yaml` 首行自带注释 `# tests/codegen/expected.yaml` 与新落点不符，验收③（逐字节一致）与验收④（路径清零）冲突，提问后用户答复 **“更新注释为新路径 (Recommended)”**。故将该行改为 `# tests/llvm/codegen/expected.yaml`；该文件是**唯一**允许内容变更的迁移文件（其余 50 个迁移文件逐字节一致）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：全局 `subagent_depth=1`，engineer 自主逐行审查全部改动（`git diff` 全量 + 新文件通读 + 迁移 blob 对比），并对照任务书验收 1–7 与硬约束逐条核验。

**判决**：实现完成，验收 1–7 均有真实输出支撑；所有 finding 已处置（3 项 ❌/⏸ 均有理由），无未修阻断项 → 状态置 `待验收`。

**审查意见（自主逐行）**：
- **逻辑正确性**：11 处改动均为「路径/注释」替换，无控制流或语义改动；`Makefile` 仅 2 行（`check-lit` 路径 + 注释）；Python 改动均为常量/注释，`make check` 的 `compileall` 通过。
- **回退路径深度**（关键项）：MC 由 4 层→5 层、E2E 保持 3 层，二者均**在 `LLVM_TOOLS_DIR` 未设、`config.llvm_tools_dir` 为空时被真实执行**（MC 30/30、E2E 4/4），非纸面推断。`%trampoline`/`%qemu`/`%e2e_dir` 重算后均指向正确位置（E2E 4/4 实跑验证）。
- **防造假**：所有命令 `cmd > log 2>&1; rc=$?`，无 `tee`；populate 了迁移前后 md5 表与 `git hash-object ↔ HEAD` blob 对比；`--inject` 自检证明门控可失败且可还原（md5 前后一致）。
- **未测输入/边界**：空套件（lit EXIT=2）已实测并转述为验收⑤「说明」分支；无其它未测边界。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 迁移文件 `expected.yaml` 首行注释与验收③（逐字节）冲突验收④（清零） | ✅已修（经用户裁定） | 首行 `# tests/codegen/expected.yaml` → `# tests/llvm/codegen/expected.yaml` | md5 `8c32540…`→`01f998d…`；`git status` 显示 `RM`；`validate_codegen_vectors` EXIT=0 |
| F2 `tests/scripts/codegen_crt0.s:9` 同类注释（非迁移文件） | ✅已修 | 注释路径 → `tests/llvm/codegen/expected.yaml` | 纯注释；`make test-codegen` EXIT=0 15/15 |
| F3 `Makefile:308-309` 注释「MC(22/22)+E2E(3/3)」与实际 30/4 不符 | ❌不修 | — | 既有陈旧注释，非本任务引入；本任务未改通过数，避免无关 diff |
| F4 空套件 `llvm-lit <dir>` EXIT=2（非 0） | ✅已处置（走验收⑤说明分支） | 两个占位 README 明确「not wired into `make check-lit`」 | `.work/log/infra/INFRA-045t/evidence-placeholder-lit.log`（与 MC 合并 → config 加载、0 自有测试、总 EXIT=0） |
| F5 改动行超 79 列（`run_codegen_e2e.py:4`=80、`check_lit_bytes.py:64`=89、`check_interface_alignment.py:730`=89、`validate_instrinfo.py:71`=83） | ❌不修 | — | 仓库无 flake8/ruff/pylint 配置（`AGENTS.md` 未规定启用），且多处既有行 >79；重排仅增 diff 噪声 |
| F6 `.gitignore` 陈旧模式 `tests/codegen/*.{s,o,bin}` | ⏸延后 | — | 不在本任务文件清单（验收④范围 = Makefile/tools/tests）；`INFRA-046t` 任务书已认领 |
| F7 生成/证据落点 | ✅已满足 | 证据脚本 `.work/evidence/INFRA-045t/run.sh`、日志 `.work/log/infra/INFRA-045t/` | 均在 gitignored `.work/` 下；`git status` 无 `.work` 残留 |

**约束自查**：未改 `spec/**`/`contracts/**`/`components/**`；未改函数签名；未引入外部依赖；临时文件仅 `/tmp/opencode/INFRA-045t/`（仅 `--inject` 的 Makefile 备份）；未提交 git。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑证据脚本 + 自行注入反例 + 逐项手动验证。

##### 1. 证据脚本审查

脚本 `.work/evidence/INFRA-045t/run.sh` 结构合格：
- ✅ 每条检查有 `pass`/`fail` 对，FAIL 路径非空
- ✅ `--inject`：备份 → sed 改 Makefile check-lit 路径回旧值 → md5 验注入有效 → `make check-lit` EXIT=2 (FAIL) → 还原 → md5 验还原 → 回绿 EXIT=0
- ✅ 无 `tee` 吞退出码，均 `cmd > log 2>&1; RC=$?`
- ✅ 结尾 `exit "$FAILED"`，任一检查失败则非零退出

##### 2. 重跑证据脚本（默认模式）

```
$ bash .work/evidence/INFRA-045t/run.sh > run-default.log 2>&1; echo "EXIT=$?"
EXIT=0

== INFRA-045t evidence: tests/ component-first reorganisation ==
[PASS] dir exists: tests/llvm/lit/MC/DADAO
[PASS] dir exists: tests/llvm/lit/CodeGen/DADAO
[PASS] dir exists: tests/llvm/lit/tools/DADAO
[PASS] dir exists: tests/llvm/codegen
[PASS] dir exists: tests/qemu
[PASS] dir exists: tests/e2e/lit
[PASS] old path absent: tests/lit/MC/Dadao
[PASS] old path absent: tests/lit/E2E
[PASS] old path absent: tests/codegen
[PASS] lit config exists: tests/llvm/lit/CodeGen/DADAO/lit.cfg.py
[PASS] lit config exists: tests/llvm/lit/tools/DADAO/lit.cfg.py
[PASS] lit config exists: tests/e2e/lit/lit.cfg.py
[PASS] placeholder lit suites not wired into check-lit (documented in their READMEs)
[PASS] content zero-change: only the 3 approved files differ (50/53 byte-identical)
[PASS] no stale path references in Makefile/tools/tests
[PASS] make check-lit EXIT=0, MC=30 E2E=4 (== pre-migration)
[PASS] placeholder lit suites recognized by llvm-lit (config loaded, 0 own tests)
[PASS] make test-codegen EXIT=0, 15/15
[PASS] make check EXIT=0
[PASS] make check-no-residue EXIT=0
INFRA-045t EVIDENCE: PASS
```

**20/20 PASS，EXIT=0**。

##### 3. 重跑证据脚本（--inject 自检）

```
$ bash .work/evidence/INFRA-045t/run.sh --inject > run-inject.log 2>&1; echo "EXIT=$?"
EXIT=0

== INFRA-045t counter-example injection (Makefile check-lit old path) ==
[PASS] injection effective (Makefile md5 changed 7b0546c... -> 9126ebf...)
[PASS] injected make check-lit FAILED as expected (EXIT=2)
[PASS] Makefile restored (md5 back to 7b0546c...)
[PASS] restored make check-lit green again (EXIT=0)
INJECT SELF-TEST: PASS
```

**4/4 PASS，EXIT=0**。

##### 4. 独立注入反例（与工程师不同）

**注入方式**：将 `tools/integ/run_codegen_e2e.py` 的 `DEFAULT_VECTORS_DIR` 从 `"tests/llvm/codegen"` 改回 `"tests/codegen"`（旧路径）。

```
$ ORIG_MD5=aa7ca165df590d0a4b6d84fe6aaa1548
$ sed -i 's|DEFAULT_VECTORS_DIR = "tests/llvm/codegen"|DEFAULT_VECTORS_DIR = "tests/codegen"|' tools/integ/run_codegen_e2e.py
$ INJ_MD5=8994a83a5ff06882764848469b9001f7  ← 注入有效（md5 变化）
$ git diff --stat tools/integ/run_codegen_e2e.py
 tools/integ/run_codegen_e2e.py | 4 ++-- 1 file changed, 2 insertions(+), 2 deletions(-)
$ make test-codegen > inject-test-codegen.log 2>&1; echo "EXIT=$?"
EXIT=2   ← FAIL（旧路径不存在）

$ cp /tmp/.../run_codegen_e2e.bak tools/integ/run_codegen_e2e.py
$ REST_MD5=aa7ca165df590d0a4b6d84fe6aaa1548  ← 还原 md5 一致
$ git diff tools/integ/run_codegen_e2e.py  ← 仅含工程师的合法改动（docstring + 2 常量）
$ make test-codegen > restore-test-codegen.log 2>&1; echo "EXIT=$?"
EXIT=0   ← 回绿
```

**注入 → FAIL → 还原 → 回绿，全过程确认。**

##### 5. 独立预检项核验

| 预检项 | 结果 | 证据 |
|--------|------|------|
| `make check` EXIT=0 | ✅ | 证据脚本 #6（重跑 EXIT=0） |
| `make check-lit` EXIT=0, MC=30 / E2E=4 | ✅ | 证据脚本 #4 + 独立重跑 `verify-check-lit.log` MC=30 E2E=4 |
| 迁移前后通过数一致 | ✅ | `baseline-check-lit.log` MC=30 E2E=4 == `post-check-lit.log` MC=30 E2E=4 |
| `make test-codegen` EXIT=0, 15/15 | ✅ | 证据脚本 #5（重跑 EXIT=0） |
| `make check-interface` EXIT=0 | ✅ | 独立重跑 EXIT=0 |
| `make check-no-residue` EXIT=0 | ✅ | 证据脚本 #7（重跑 EXIT=0） |
| 内容零改动：50/53 字节一致 | ✅ | git status: 50 `R` + 3 `RM`；证据脚本 #2 blob 对比 |
| 仅 3 个批准文件不同 | ✅ | `RM`: `lit.cfg.py`(E2E) + `lit.cfg.py`(MC) + `expected.yaml` |
| `expected.yaml` 首行注释变更符合裁定 | ✅ | `# tests/codegen/expected.yaml` → `# tests/llvm/codegen/expected.yaml`（仅注释） |
| 路径清零 grep EXIT=1 | ✅ | 独立 grep 无匹配，EXIT=1 |
| 新结构全部存在 | ✅ | 6 个新目录 + 3 个 lit.cfg.py + 3 个 README 全部 EXISTS |
| 旧路径全部清除 | ✅ | `tests/lit`/`tests/codegen` 均 GONE |
| 无 `*_tmp*`/`*.orig`/`*.rej` | ✅ | git status 无此类文件 |

##### 6. 遗留判定

| 遗留项 | 处置 | 证据 |
|--------|------|------|
| `spec/Process-05 §6` 旧路径 | ✅ 如实登记，交 SPEC-110t（ADR-0012 D4 约束仅 spec 模块任务可改 spec/） | grep 确认行 39/41 仍有旧路径 |
| `.gitignore` 陈旧模式 | ✅ 如实登记，交 INFRA-046t（任务书已认领） | INFRA-046t 任务文件 line 20/28 |
| 两个占位 lit 套件零测试 | ✅ 如实登记，README 已写明接入方法 | 证据脚本 #4b 验证 lit 可解析 |

##### 判决

**Accepted**。

验收 1–7 全部通过（证据脚本 20/20 + --inject 自检 4/4 + 独立注入反例验证）；约束逐条守住；遗留问题如实登记且有对应任务认领；无未修阻断项。
