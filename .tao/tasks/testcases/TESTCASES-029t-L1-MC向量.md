# TESTCASES-029t: L1 MC 向量（伪指令/指导符/选项/诊断/往返；独立 oracle）

**模块**：testcases
**项目里程碑**：M4
**依赖**：`SPEC-106t`、`INFRA-045t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-106t` 落地后的 `spec/Toolchain-01-汇编语言.md §6`（**权威伪指令集**，8 条合成型 + 展开规则）与 `.tao/adr/adr-0013-assembly-syntax.md`（D3/D9/D10/D11）；`spec/DADAO-11 §汇编兼容性`（`.dd.*` 指导符、`-multiple-to-single`）。
  - `.tao/knowledge/contract-asm.md §6/§7/§8/§9/§10`（伪指令/指导符/选项/诊断/往返）与 `contract-asm-list.md`（立即数范围速查）。
  - `contracts/opcodes.yaml`（**L1 独立 oracle 的期望值来源**：`format`/字段/编码身份）。
  - `spec/Process-05-里程碑TDD规范.md` §2（L1：MC，期望值来自 ISA 编码表）、§5（反例门控）、§6（落点）。
  - `INFRA-045t` 落地后的落点目录 `tests/llvm/lit/MC/DADAO/`。
- **输出**（**用户裁定 2026-10-06**：向量 + 独立 oracle，**暂不接入门控**）：
  - **L1 向量落 `tests/llvm/lit/MC/DADAO/`（单一落点，并入，不并排新目录）**；「暂不接入门控」用 lit **`UNSUPPORTED:` 标记**实现（每条新向量首部 `UNSUPPORTED: true`，使 `llvm-lit` 将其记为 unsupported 而**不阻断** `make check-lit`）；内容覆盖：
    - **伪指令**：`set.rd`/`set.rb`/`set.ft`/`set.fo`（imm/reg）展开（权威源 `Toolchain-01 §6`）；被删项（`nop`/`return`/`not.*`/`neg.*`）→ 应报 `unrecognized instruction mnemonic` 的反例。
    - **指导符**：`.dd.b08/w16/t32/o64` 宽度/大端字节序（含表达式/符号）；GAS `.word`/`.octa` 仍拒绝。
    - **选项**：`-multiple-to-single` 开/关对照（助记符不变、展开为单寄存器序列）。
    - **诊断**：越界立即数（`add.si rd8, 131072`、`cmp.ui …, 4096`）报错（非静默环绕）；地址类 `%4!=0` 报错；`ret rd0, 非0` 报错；`#` 非法（`AllowAdditionalComments=false`）。
    - **往返**：汇编↔反汇编（`contract-asm §10`）。
  - **独立 oracle** `tools/testcases/validate_mc_vectors.py`：**不调用 `llvm-mc`/`llc`/QEMU**，从 `contracts/opcodes.yaml`（+ spec）**独立派生**每条向量的期望编码/字段/展开形态，与向量内联期望值比对，可失败。
  - `tests/llvm/lit/MC/DADAO/README-m4.md`（M4 向量 ↔ 能力 ↔ 期望值来源对照表）。
  - **边界**：`not`/`neg` 的**替代功能**（底层真实指令 `xnor.o`/`sub.sX`，L1+L3）专门向量归 **`TESTCASES-032t`**，本任务不重复；本任务只保留被删伪指令 `not.*`/`neg.*` 的「unrecognized」反例。
- **约束**：
  - **门控时序（用户裁定 2026-10-06）**：本任务**只产出向量 + 独立 oracle**，**暂不接入** `make check`/`make check-lit`/`make test-elf`；由对应实现任务（`LLVM-051t`~`054t`）与 `INTEG-016t` **移除 `UNSUPPORTED:` 标记**、接入并转绿。用户原话：「向量+独立 oracle，暂不接入门控（推荐）」。
  - **单一落点**：向量直接落在 `tests/llvm/lit/MC/DADAO/`（`INFRA-045t` 后的唯一 L1 路径），**不**并排 `Dadao-m4/` 或其它平行目录；门控排除**只靠 `UNSUPPORTED:` 标记**，不靠路径隔离。
  - **期望值独立派生**（project 硬约束）：**不得**从 `llvm-mc`/`llc` 输出反推；须来自 `contracts/opcodes.yaml`/`spec/`（`Process-05 §4`）。
  - 规模 ∝ 能力（`Process-05 §3`「一能力一向量」）；手写少量、可审计，不批量迁移。
  - 「移植只借结构」（可借鉴上游 target 的用例**形态**，期望值独立派生）。
  - 不改 `contracts/**`、`components/**`、`Makefile`；临时目录 `/tmp/opencode/TESTCASES-029t/`；**不提交 git**。

## 验收标准

1. **向量齐全**：`tests/llvm/lit/MC/DADAO/` 覆盖上列五类（伪指令/指导符/选项/诊断/往返）各 ≥1；M4 向量均带 `UNSUPPORTED:` 标记；给出「向量 ↔ 能力 ↔ 期望值来源」表（`README-m4.md`）。
2. **独立 oracle**：`python3 tools/testcases/validate_mc_vectors.py` EXIT=0；脚本内**无** `subprocess`/`os.system`/`Popen` 调用（grep 核实）；期望值可由脚本从 `contracts/opcodes.yaml` 独立重算。
3. **反例门控**：对注入反例（改一条期望字节 / 改一条 `.s` / 少一类覆盖）→ validator **非零退出**（真实输出留存 `.work/log/testcases/`）；还原后回绿。
4. **门控不破**：`make check` EXIT=0；`make check-lit` EXIT=0 且新向量记为 **unsupported**（不阻断、不误报 PASS）；`make check-dirs`/`make check-no-residue` EXIT=0。
5. 一键证据脚本 `.work/evidence/TESTCASES-029t/run.sh`（非交互、失败非零、逐项打印、≥2 类注入自检、结尾无 `tee`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
> **用户裁定（2026-10-06）**：向量 + 独立 oracle，**暂不接入门控**（用 `UNSUPPORTED:` 标记）；落点改为**单一** `tests/llvm/lit/MC/DADAO/`。用户原话：「向量+独立 oracle，暂不接入门控（推荐）」。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
