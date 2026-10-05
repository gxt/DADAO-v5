# TESTCASES-032t: `not`/`neg` 功能向量（L1 编码 + L3 执行；独立 oracle）

**模块**：testcases
**项目里程碑**：M4
**依赖**：`SPEC-106t`、`INFRA-045t`、`TESTCASES-029t`、`TESTCASES-030t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含）：
  - `.tao/adr/adr-0013-assembly-syntax.md` 的 **D11**（2026-10-06 用户逐条确认，`Accepted`）——**决策来源**。**用户裁定原话（原文引用）**：「**删除（不实现，10 条）**：`nop`（用 `swym 0`）、`return`（用 `ret rd0, 0`）、`not.{b,w,t,o}`（用 `xnor.o`/`xnor.X`）、`neg.{b,w,t,o}`（用 `sub.sX`）。」
  - `SPEC-106t` 落地后的 `spec/Toolchain-01-汇编语言.md §6`（权威伪指令集）与 `spec/SimRISC-00 §伪指令`（**功能说明 + 如何实现**：`not`→`xnor.o`、`neg`→`sub.sX`）。
  - **底层真实指令的语义来源**（**期望值独立派生基点**）：
    - `.tao/knowledge/contract-isa.md` §6.3（`xnor.o` 64 位逻辑：相同为一、相异为零；「无专门 not 指令；当 `rdhc` 或 `rdhd` 为 `rd0` 时，`xnor` 实现另一操作数取反」）、§6.6（`not.o rdhb, rdhc` → `xnor.o rdhb, rdhc, rd0`；`neg.o rdhb, rdhc` → `sub.so rd0, rdhb, rd0, rdhc`）、§10.6/§11.6/§12.6（`neg.b/w/t` → `sub.sb/sw/st rdhb, rd0, rdhc`）。
    - **已删窄位宽逻辑**：`xnor.b/w/t` 已于 `SPEC-069t` 删除（`contract-isa` §10.3/§11.3/§12.3 的 `SPEC-069t` 注），故 `not.b/w/t` **无对应底层指令**——本任务 `not` **仅测 64 位 `xnor.o`**。
    - `spec/SimRISC-04 §Logic operators：逻辑运算 / §not / §neg`、`spec/SimRISC-05/08/09/10 §加减操作`（只读溯源，内容非执行必需）。
  - `contracts/opcodes.yaml`（**L1 独立 oracle 的期望编码来源**）：`xnor.o_orrr_rd`（`format: orrr`，`op=0x40`/`ha=0x0B`/`value=0x402C0000`，`legal:` `rdhb != rd0`）、`sub.sb_orrr_rd`（`op=0x43`/`ha=0x29`）、`sub.sw_orrr_rd`（`op=0x42`/`ha=0x29`）、`sub.st_orrr_rd`（`op=0x41`/`ha=0x29`）、`sub.so_rrrr_rd`（`format: rrrr`，`op=0x53`，双目的 `rdha:rdhb = rdhc − rdhd`）。
  - `spec/Process-05-里程碑TDD规范.md` §2（L1 期望值来自 ISA 编码表；L3 独立 oracle）、§4（期望值独立派生）、§5（反例门控）、§6（落点）。
  - `INFRA-045t` 落地后的落点：`tests/llvm/lit/MC/DADAO/`（L1）、`tests/llvm/codegen/m4/`（L3）。
- **输出**（**用户裁定 2026-10-06**：向量 + 独立 oracle，**暂不接入门控**）：
  - **L1 编码/往返向量** 落 `tests/llvm/lit/MC/DADAO/`（并入，单一落点；每条首部带 `UNSUPPORTED: true`，使 `llvm-lit` 记为 unsupported 而**不阻断** `make check-lit`）：
    - **`not` 功能 → 仅 64 位 `xnor.o`**：`xnor.o rd, rc, rd0` 的编码（`; OBJ:` 字节独立派生自 `contracts/opcodes.yaml`）与反汇编往返；`.b/.w/.t` **不适用**（见上「已删窄位宽逻辑」）。
    - **`neg` 功能 → `sub.sb/sw/st/so`**：`sub.sb/sw/st rd, rd0, rc`（8/16/32 位符号扩展减法）与 `sub.so {rd0, rd}, rd0, rc`（64 位双目的）的编码/往返（`; OBJ:` 独立派生自 `contracts/opcodes.yaml`）。
  - **L3 执行向量** 落 `tests/llvm/codegen/m4/`（并入 `m4/` 落点，与 `TESTCASES-030t` 共用**独立 m4 清单** `expected.yaml`，M3 驱动不读）：
    - `*.ll`（IR 级程序）+ `tests/llvm/codegen/m4/expected.yaml` 条目：按位取反（`xor x, -1` 语义）与取负（`0 - x` 语义）的 IR 程序，覆盖 8/16/32/64 位有符号；宿主侧独立派生期望退出码（大端 + 64 位补码），**不调用** `llc`/QEMU。
    - 边界用例：`not 0` / `not -1`、`neg 0`、各宽度 `INT_MIN` 取负、符号扩展边界（如 8 位 `0x80`）。
  - **独立 oracle**（**扩展** `TESTCASES-029t`/`030t` 建立的共享 validator，不另造）：
    - L1：`tools/testcases/validate_mc_vectors.py`——**不调用** `llvm-mc`/`llc`/QEMU，从 `contracts/opcodes.yaml` 独立派生 `xnor.o`/`sub.sX` 的期望编码/字段，与向量内联期望值比对，可失败。
    - L3：`tools/testcases/validate_elf_vectors.py`——**不调用** `llc`/QEMU，按 IR/spec 语义独立派生每个程序的期望退出码，与 `m4/expected.yaml` 比对，可失败。
  - `tests/llvm/lit/MC/DADAO/README-m4.md`、`tests/llvm/codegen/m4/README.md` 补「`not`/`neg` 功能 ↔ 底层真实指令 ↔ 期望值来源」对照行。
  - **边界**：`set.*` 展开/指导符/选项/诊断归 `TESTCASES-029t`；多 TU/多段/ELF 链路归 `TESTCASES-030t`；被删伪指令 `not.*`/`neg.*` 的「unrecognized」反例归 `TESTCASES-029t`。本任务只做 `not`/`neg` 的**替代功能**（`xnor.o`/`sub.sX`，**底层真实指令**）正例向量，不重复。
- **约束**：
  - **门控时序（用户裁定 2026-10-06）**：本任务**只产出向量 + 独立 oracle**，**暂不接入** `make check`/`make check-lit`/`make test-elf`；L1 用 lit **`UNSUPPORTED:` 标记**、L3 用**独立 m4 清单**；由对应实现任务与 `INTEG-016t` 移除标记/接入并转绿。
  - **期望值独立派生**（project 硬约束）：**不得**从 `llvm-mc`/`llc`/QEMU 反推；L1 来自 `contracts/opcodes.yaml`，L3 来自 IR/spec 语义（`Process-05 §4`）。
  - **指令精确**：`not` → **仅** `xnor.o`；`neg` → `sub.sb/sw/st/so`；**不得**测试已删的 `xnor.b/w/t`。
  - **规模 ∝ 能力**（`Process-05 §3`）；手写少量、可审计。
  - **串行**：共享 `tests/llvm/lit/MC/DADAO/`、`tests/llvm/codegen/m4/` 与两个 validator，**串行于** `TESTCASES-029t`/`030t`（本任务在其后扩展脚本）。
  - 不改 `contracts/**`、`components/**`、`Makefile`；临时目录 `/tmp/opencode/TESTCASES-032t/`；**不提交 git**；复杂命令输出留存 `.work/log/testcases/`。

## 验收标准

1. **L1 向量齐全**：`tests/llvm/lit/MC/DADAO/` 含 `xnor.o`（`rd, rc, rd0`）与 `sub.sb/sw/st/so` 的编码/往返向量各 ≥1；`; OBJ:` 字节独立派生自 `contracts/opcodes.yaml`；均带 `UNSUPPORTED:` 标记；`README-m4.md` 给出「功能 ↔ 底层指令 ↔ 期望值来源」表。
2. **L3 向量齐全**：`tests/llvm/codegen/m4/` 含 `not`/`neg` 的 IR 程序 + `expected.yaml` 条目；覆盖 8/16/32/64 位有符号取负与 64 位取反；含 `0`/`-1`/各宽度 `INT_MIN` 边界；`README.md` 给出「程序 ↔ 覆盖点 ↔ 推导依据」。
3. **独立 oracle**：`python3 tools/testcases/validate_mc_vectors.py`、`python3 tools/testcases/validate_elf_vectors.py` 对新增向量 EXIT=0；脚本内**无** `subprocess`/`os.system`/`Popen`（grep 核实）；L1 期望可由脚本从 `contracts/opcodes.yaml` 独立重算。
4. **size/sign 逐条重算**：`sub.sb/sw/st` 的符号扩展与 64 位补码、各宽度 `INT_MIN` 取负逐条独立复算，与 `expected.yaml`/`; OBJ:` 一致（含负值高 8 位补码）。
5. **反例门控**：对注入反例（改一条 `; OBJ:` 期望字节 / 改一条 L3 期望退出码 / 少一类覆盖）→ validator **非零退出**（真实输出留存 `.work/log/testcases/`）；还原后回绿。
6. **门控不破**：`make check` EXIT=0；`make check-lit` EXIT=0 且新向量记为 **unsupported**（不阻断、不误报 PASS）；`make check-dirs`/`check-no-residue` EXIT=0。
7. 一键证据脚本 `.work/evidence/TESTCASES-032t/run.sh`（非交互、失败非零、逐项打印、≥2 类注入自检、结尾无 `tee`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
> **用户裁定（2026-10-06）**：`not`/`neg` 功能向量**单独一个 `TESTCASES`**（本任务），自 `SPEC-106t` 移出；测**底层真实指令**（`not`→`xnor.o`；`neg`→`sub.sb/sw/st/so`），L1 编码 + L3 执行，期望值**独立派生自 `spec/`/`contracts/`**；暂不接入门控（`UNSUPPORTED:` + 独立 m4 清单）。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
