# INFRA-045t: `tests/` 组件先行重排

**模块**：infra
**项目里程碑**：M4
**依赖**：无
**状态**：待开始

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
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
> **用户裁定（2026-10-06，采纳）**：E2E 落点 = **`tests/e2e/`**（跨组件，**不塞** `llvm/`）；本任务 `tests/lit/E2E → tests/e2e/lit` 符合该裁定（`tests/e2e/` 桶内），**无需改动**。原「待裁定点 2」定案，见 `SPEC-104k`「修订记录（2026-10-06·2）」C.2。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
