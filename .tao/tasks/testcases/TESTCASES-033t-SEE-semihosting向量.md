# TESTCASES-033t: SEE/HEE + semihosting 向量（L1 MC + L3 执行；独立 oracle）

**模块**：testcases
**项目里程碑**：M5
**依赖**：`SPEC-114t`、`SPEC-115t`、`LLVM-060t`、`INFRA-048t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-114t`（SEE/semihosting 正文）+ `SPEC-115t`（`trap`/`escape`/`cfx2rc`/`cfx2rd` re-scope + `contracts/opcodes.yaml`）+ `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`）。
  - `LLVM-060t`（MC 编码支持；**L1 MC 向量依赖它**）+ `INFRA-048t`（落点 `.dadao/tests/`）。
  - `spec/Process-05-里程碑TDD规范.md`（§2 L1/L2/L3；§3「一能力一向量」；§4 期望值**独立派生**；§5 反例门控；§6 落点）；`contracts/opcodes.yaml`（L1 期望编码来源）。
  - `spec/SimRISC-11-其它.md`（4 条形式）、`spec/DADAO-12 §5`（异常进入/退出）、`spec/DADAO-22 §1/§3`（调用约定/初始化）、`.tao/knowledge/contract-abi.md §4.1/§4.4`（传参/返回）。
  - 既有 `tests/llvm/lit/MC/DADAO/`（`validate_mc_vectors.py` oracle）与 `tests/llvm/codegen/`（L3 驱动模式）。
- **输出**：
  - **L1 MC 向量**：落 `tests/llvm/lit/MC/DADAO/`（如 `m5-trap-escape-cfx2.s`）——`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码与往返；**分阶段**：`LLVM-060t` 就绪前以 lit **`UNSUPPORTED:`** 标记暂缓（`Process-05`；`LLVM-060t` 完成后**去除**标记）。期望编码**独立派生自 `contracts/opcodes.yaml`**（**禁**从 `llvm-mc` 反推）。
  - **L3 执行向量**：落 `tests/llvm/codegen/m5/`（独立 m5 清单 + `expected.yaml`）——经 `llc`/`llvm-mc`/`ld.lld`/`qemu` 跑通：① **semihosting 服务**（≥ console `WRITEC/WRITE0/WRITE` + `EXIT`/`EXIT_EXTENDED`；`READC` 可 host 输入桩）；② **权限反例**（未授权模式/未实现 cfx ⇒ `NUPERM/NJPERM/NSPERM/NHPERM` 或 `CFXREG`）；③ **一条一般 trap 进入向量 + escape 返回**。**期望值独立派生自 spec/契约**（**禁**从 QEMU 反填）。
  - **独立 oracle**：扩展 `tools/testcases/validate_mc_vectors.py` / 新增 `validate_elf_vectors.py` 派生（复用 `029t`/`030t` 共享 validator，`Process-05 §6`）；**不调用** `llvm-mc`/`llc`/QEMU 作为期望来源。
  - `tests/llvm/lit/MC/DADAO/README-m5.md`（向量 ↔ 能力 ↔ 期望值来源对照）。
- **门控时序（`Process-05` TDD）**：向量**先立**；L1 暂缓用 `UNSUPPORTED:`（**不接门控**），由 `LLVM-060t` 完成后（或 `INTEG-020t` 收口时）去除标记接入 `check-lit`；L3 落 m5 独立清单（`make test-codegen`/`test-elf` 的 M3/M4 驱动**不读**，避免误接）。
- **约束（硬）**：
  - **期望值独立派生**（`AGENTS.md`「Independent oracle」；`Process-05 §4`）；**不得**从 LLVM/QEMU 反填。
  - **规模 ∝ 能力**（「一能力一向量」），手写少量、可审计；**禁**批量迁移。
  - **向量须能对反例失败**（`Process-05 §5`）：每条向量有可达 FAIL 路径（**逐条**核对，避免恒真/两支同值）。
  - 不改 `contracts/**`/`components/**`/`Makefile`；临时目录 `/tmp/opencode/TESTCASES-033t/`；**不提交 git**；复杂命令输出留存 `.work/log/testcases/`（**禁 `tee`**）。
  - **重建成本申报**：L3 需 `build-mc`/`build-lld`/`build-qemu`（增量，`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **L1 向量**：`tests/llvm/lit/MC/DADAO/` 含 4 条指令编码/往返向量（`LLVM-060t` 就绪前带 `UNSUPPORTED:`）；`make check-lit` EXIT=0 且新向量被正确处理（unsupported 或 PASS）。
2. **L3 向量**：`tests/llvm/codegen/m5/` 含 semihosting 服务（≥3 类）/权限反例（≥3 类）/一般 trap+escape 各 ≥1；给出「向量 ↔ 能力 ↔ 期望值来源」表。
3. **独立 oracle**：`python3 tools/testcases/validate_*.py` EXIT=0；oracle **无** `subprocess`/`os.system`/`Popen`（`grep` 核实）；期望值可独立重算。
4. **L3 执行**：经 m5 驱动跑通，逐例「名字/期望/实际/退出码」；给真实输出（`.work/log/testcases/`）。
5. **反例门控**：对注入反例（改一条期望字节 / 改一条服务号 / 改一条权限期望）⇒ oracle/驱动器**非零退出**；还原后回绿（真实输出）。
6. **门控**：`make check`/`make check-lit` EXIT=0；`make check-no-residue` EXIT=0。
7. **一键证据脚本**：`.work/evidence/TESTCASES-033t/run.sh`——非交互、失败非零、逐项打印、≥2 类注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅新增向量 + oracle + README + 本任务书。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 独立全量重算（逐条） + 门控 + 判决）

#### architect 重排落纸（2026-10-07，用户裁定 1）
**用户原话**：「**A 重排：先 LLVM-060t 再 SPEC-115t（推荐）**」（经主会话转达；见 `lessons §7.3`）。

**对本任务的影响（lit 归属裁定）**：本任务的 L1 MC 向量落点 `tests/llvm/lit/MC/DADAO/` 现由**前置的 `LLVM-060t` 先行自带**（含 `crrr`/`ciii` 的 `; OBJ:`），本任务**复用/扩展**（不再需要「`LLVM-060t` 就绪前以 `UNSUPPORTED:` 暂缓」，因其已就绪）。`tests/vectors/inventory.md` 的 4 行由 `SPEC-115t` 承接（`validate_vectors` 要求行集 == `scope==m1` 集，原子强制）。完整归属理由见 `SPEC-115t` 审阅记录「第 2 轮 architect 重排落纸」。
