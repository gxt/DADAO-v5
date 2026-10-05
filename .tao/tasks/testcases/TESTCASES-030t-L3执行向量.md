# TESTCASES-030t: L3 执行向量（多 TU/多段/ELF 链路；独立 oracle）

**模块**：testcases
**项目里程碑**：M4
**依赖**：`SPEC-105t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-105t` 落地后的 `.tao/knowledge/contract-elf.md §2–§4`（RELA、4 类 reloc、`ABS48` 3 片、无 −4、溢出 link-time error）与 `.tao/adr/adr-0019`（Accepted）；`.tao/adr/adr-0004`（`SPEC-107t` 调整后的加载约定）。
  - `spec/Process-05` §2（**L3：IR → 代码 → 运行 → 结果比对；独立 oracle**）、§3/§4/§5/§6（L3 落点 `tests/codegen/` + `tools/integ/`/`tools/testcases/`）。
  - M3 既有 `tests/codegen/`（`.ll` + `expected.yaml`，由 `make test-codegen` 消费，**本任务不得破坏**）。
- **输出**（**用户裁定 2026-10-06**：向量 + 独立 oracle，**暂不接入门控**）：
  - **M4 L3 向量暂存目录 `tests/codegen-elf/`**（**独立于** M3 `tests/codegen/`，故 M3 `make test-codegen` 不受影响）：
    - **多 TU**：每个程序含 **≥2 个 `.ll`**（跨 TU 直接调用、跨 TU 全局符号），由清单声明如何链接。
    - **多段**：`.text`/`.rodata`/`.data`/`.bss` 均被覆盖；含全局数据初值与运行时读写。
    - **reloc 场景**：跨段/外部符号 `ABS48` 地址构造、跨 TU `REL26` call、条件分支 `REL20`/`REL14`（溢出负例另见 `INTEG-016t`）。
    - **文件**：`tests/codegen-elf/*.ll` + **清单 `tests/codegen-elf/expected.yaml`**（`programs: [{name, category, sources:[…], expected_exit_code, derivation}]`）+ `tests/codegen-elf/README.md`（程序 ↔ 覆盖点 ↔ 推导依据）。
  - **独立 oracle** `tools/testcases/validate_elf_vectors.py`：**不调用 `llc`/`QEMU`**，按 IR/spec 语义（宿主侧 Python，大端 + 64 位补码）**独立派生**每个程序的期望退出码，与 `expected.yaml` 比对；校验 schema/覆盖/多 TU 形态，可失败。
- **约束**：
  - **门控时序（用户裁定 2026-10-06）**：本任务**只产出向量 + 独立 oracle**，**暂不接入** `make test-elf`/`make check`；由 `INTEG-016t` 接入并转绿。向量目录不得被 M3 `make test-codegen` 消费（不写入 `tests/codegen/expected.yaml`、不放 `tests/codegen/*.ll`）。
  - **Independent oracle**（project 硬约束）：期望值**不得**由 `llc`/QEMU 生成；须宿主侧按 IR/spec 语义独立派生（或手算并写明推导）。size/sign 敏感项（指针差、补码、`ABS48` 分片）须逐条重算。
  - 规模 ∝ 能力（`Process-05 §3`）；手写少量、可审计（`§4`），不批量迁移。
  - 退出通道：返回值应落在 `ADR-0004 D3` 的 `0x00–0x7F`（避免与机器 fault 段 `0x80–0xFF` 歧义，吸取 `INTEG-012t` 遗留 1 的教训）。
  - 不改 `tests/codegen/**`、`contracts/**`、`components/**`、`Makefile`；临时目录 `/tmp/opencode/TESTCASES-030t/`；**不提交 git**。

## 验收标准

1. **向量齐全**：`tests/codegen-elf/` 含 ≥1 多 TU（≥2 `.ll`）、≥1 多段（`.data`+`.rodata`）、≥1 跨 TU `call`、≥1 `ABS48` 地址构造；`README` 给出「程序 ↔ 覆盖点 ↔ 推导依据」表。
2. **独立 oracle**：`python3 tools/testcases/validate_elf_vectors.py` EXIT=0（覆盖/schema/期望值全部 PASS）；脚本无外部工具调用（grep 核实）；给出宿主独立重算输出。
3. **size/sign 敏感逐条重算**：多 TU 求和/指针差/`ABS48` 分片等逐条独立复算与 `expected.yaml` 一致（含负值时高 8 位补码）。
4. **反例门控**：对注入反例（改期望值 / 改 IR 形态 / 少一个多 TU 用例）→ validator **非零退出**（真实输出留存 `.work/log/testcases/`）；还原回绿。
5. **不破 M3**：`make test-codegen`（M3 15/15）EXIT=0；`make check` EXIT=0；`make check-dirs`/`check-no-residue` EXIT=0。
6. 一键证据脚本 `.work/evidence/TESTCASES-030t/run.sh`（非交互、失败非零、逐项打印、≥2 类注入自检、结尾无 `tee`）。

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
