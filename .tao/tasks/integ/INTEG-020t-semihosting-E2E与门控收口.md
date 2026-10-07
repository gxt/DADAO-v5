# INTEG-020t: SEE/semihosting E2E + harness stdio 捕获 + 门控收口（`make test-semihost`）

**模块**：integ
**项目里程碑**：M5
**依赖**：`QEMU-046t`、`QEMU-047t`、`TESTCASES-033t`、`TESTCASES-034t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `QEMU-046t`（semihosting 共享层 + `SYS_EXIT`）、`QEMU-047t`（新 bootrom + `-bios`）、`TESTCASES-033t`（SEE/semihosting 向量）、`TESTCASES-034t`（exit-port→`SYS_EXIT` 迁移后）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D7** host 侧安全：`-semihosting-config` 的 `target=`/`chardev=`/`arg=`；建议默认 `gdb`/沙箱）+ `adr-0004` 修订。
  - `spec/Process-05-里程碑TDD规范.md §6`（落点 + `INFRA-048t` 的 `.dadao/tests/`）；`tools/infra/paths.py`（`test_artifacts_dir`）。
  - 既有 `tools/integ/run_elf_e2e.py`/`Makefile::test-elf`/`check-lit`（E2E 驱动范式）。
  - **门槛（`INTEG-019k` §第 2 轮用户裁定 9）**：门控名 = **`make test-semihost`**（**不是** `test-see`）；组成 = ① **正向**（bootrom + 单/多 TU ELF 经 `-semihosting`、console 捕获、`SYS_EXIT` 码）；② **权限反例**（未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`）；③ **服务表各条至少 1 例**；④ **不回归**（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`）；⑤ **`INTEG` 开闭**。
- **输出**：
  1. **`tools/integ/` 驱动**（如 `run_semihost_e2e.py`）：fail-closed——bootrom（`-bios`，`QEMU-047t`）+ 单/多 TU ELF 经 `-semihosting`，跑通 semihosting 服务，**捕获 console 输出**，比对 `SYS_EXIT` 码；逐例打印「名字/期望/实际/退出码」。
  2. **harness stdio 捕获（细节展开，本任务明确落定）**：
     - **`-semihosting-config` 的 `target=`/`chardev=`/`arg=` 由谁传**：**明确**是 **Makefile 传参** 还是 **harness 脚本包装**（二选一，落定并记录理由）；建议 **驱动脚本经 `-semihosting-config target=gdb|native,chardev=...` 传参**（与 `ADR-0020 D7` 一致，默认沙箱）。
     - **console 输出捕获落点**：捕获到 **stdout** 还是 **stderr**（或 chardev 文件），**落点** = `.dadao/tests/semihost-e2e/`（`INFRA-048t` 口径）；**比对方式**（逐字节/去尾空白/期望串包含）。
  3. **`Makefile` 新目标 `test-semihost`**：见门槛五组成；**任何一类不符即非零退出**；与既有 `test-elf`/`test-codegen` **并存**。
  4. **`tests/e2e/lit/`**（如适用）：semihosting E2E lit 用例（`Process-05 §6`；`check-lit` 路径 `tests/e2e/lit`）。
  5. **`make check` 收口**：新目标接入/不破坏既有门控；`INTEG` 开闭登记（`INTEG-021m` 前置）。
- **约束（硬）**：
  - **门控名 = `make test-semihost`**（**不得**用 `test-see`——用户指出"没有 SEE"）。
  - **`SYS_EXIT` 为退出机制**（`TESTCASES-034t` 后）；**不回归** M1–M4 链。
  - **期望值独立派生**（`Process-05 §4`）；console 比对**不得**只凭 QEMU 输出反填。
  - **不回归**：`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit` 全绿。
  - `Makefile`/`tests/`/`tools/` 为共享文件，与其它改这些文件的任务**串行**。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/INTEG-020t/`；**不提交 git**；复杂命令输出留存 `.work/log/integ/`（**禁 `tee`**）。
  - **重建成本申报**：依赖 `build-mc`/`build-lld`/`build-qemu`（增量；`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **正向**：`make test-semihost` EXIT=0；bootrom + 单/多 TU ELF 经 `-semihosting`，console 捕获内容与 `SYS_EXIT` 码逐例比对正确；给真实输出（多 TU + console 各 ≥1）。
2. **权限反例**：未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`（≥1 类）——机器可判（真实输出）。
3. **服务表覆盖**：**25 服务各 ≥1 例**（脚本计数=25；给真实输出）。
4. **不回归**：`make test-elf` 5/5、`make test-codegen` 15/15、`make check`、`make check-lit` 全 EXIT=0（给真实输出）。
5. **harness stdio 落定**：完成区明确「`-semihosting-config` 传参方」与「console 捕获落点/比对方式」，且与实现一致（`grep`/真实输出）。
6. **反例门控**：注入反例（改一条期望退出码 / 改一条 console 期望串 ⇒ `test-semihost` **非零退出** ⇒ 还原 ⇒ 回绿）；给真实输出。
7. **一键证据脚本**：`.work/evidence/INTEG-020t/run.sh`——非交互、失败非零、逐项打印、含注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅 `tools/integ/**` + `Makefile` + `tests/e2e/lit/**` + 本任务书；`.dadao/` 生成物不入库。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 核 25 服务/反向例/不回归 + 判决）
