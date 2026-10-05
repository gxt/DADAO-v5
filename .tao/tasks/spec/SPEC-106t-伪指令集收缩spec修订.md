# SPEC-106t: 伪指令集收缩 spec 修订（按 ADR-0013 D11）

**模块**：spec
**项目里程碑**：M4
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含；决策已定，本任务只落正文）：
  - `.tao/adr/adr-0013-assembly-syntax.md` 的 **D11**（2026-10-06 用户逐条确认，`Accepted`）——本任务**唯一决策来源**。
  - `spec/SimRISC-00-指令系统设计.md` §伪指令（第 395–415 行附近的 15 行伪指令表）、`spec/SimRISC-03-16位立即数操作.md`（§set.rd / §set.rb / §set.ft / set.fo 伪指令）、`spec/SimRISC-06-控制流.md`（§return 伪指令）等。
  - `.tao/knowledge/contract-asm.md` §6（伪指令）、§11（实现状态与缺口）。
  - `.tao/knowledge/MEMORY.md` §「上游 ↔ v5 偏离台账」（当前 **6 项**）。
  - `spec/DADAO-11-AEE-应用程序运行环境.md`（上游依据溯源；只读对照）。
- **输出**：
  - **`spec/SimRISC-00 §伪指令` 表**：只保留 `ADR-0013 D11` 的 **8 条合成型**（`set.rd`×2 / `set.rb`×2 / `set.ft`×2 / `set.fo`×2）；**删除** 10 条 1:1 别名（`nop`、`return`、`not.{b,w,t,o}`〔表中实为 `not.o` 单条，按实际存在的条目处理〕、`neg.{b,w,t,o}`）；对被删条目，给出「删除」标注或移除行，并注明「用真实指令替代」（`swym 0` / `ret rd0, 0` / `xnor.o`/`xnor.X` / `sub.sX`）。
  - **`spec/SimRISC-03`**：`set.rd`/`set.rb`/`set.ft`/`set.fo` 的展开规则保留并核正；补充 `ADR-0013 D11` 的「常量 vs 符号」判据（可汇编期求值→最少指令数；符号/可重定位→固定 3 片 + `R_DADAO_ABS48`）；`set.rb` 细节（允许 `wp0–wp3`；明确为地址时 ≤48 位；**不补 `set.ow-rb`**，注明与 `set.rd` 的不对称）；`ret` 保持显式 `ret rdHA, imms18`、**不加无参形态**。
  - **删除条目的详细定义章节**：凡 `spec/SimRISC-0x` 中定义被删伪指令的小节（实测至少 `SimRISC-04 §not/§neg`、`SimRISC-06 §return`、`SimRISC-08 §neg`、`SimRISC-09 §neg`、`SimRISC-10 §neg`、`SimRISC-11 §nop`；`SimRISC-08/09/10 §not` 已标「已删除」可保持）须按 D11 **标注删除/移除其规范性定义**，并留「用真实指令替代」指引。
  - `.tao/knowledge/contract-asm.md` §6 改为收缩后口径（8 条合成型；明确反汇编只显真实指令），§11 缺口表相应更新（伪指令由「18 条未实现」→「8 条待实现」）。
  - `.tao/knowledge/MEMORY.md` 偏离台账：**新增 1 项**——「删除上游 `SimRISC-0.5.4` 定义的 5 类伪指令（`nop`/`return`/`not.*`/`neg.*`）」，指向 `ADR-0013 D11`（台账由 6 项 → 7 项；只做归一化登记 + 指针，不新增决策）。
- **约束**：
  - **只落正文、不重新决策**：`ADR-0013 D11` 已 `Accepted`；不得增删其未列的伪指令，不得改 `ret` 语法。
  - **文件范围 = 全 `spec/`（用户裁定 2026-10-06）**：`SPEC-104k §说明` 假设本任务改 `SimRISC-00/03/06`，但实测被删伪指令的详细定义分散在 `SimRISC-04 §not/§neg`、`SimRISC-06 §return`、`SimRISC-08/09/10 §neg`、`SimRISC-11 §nop`。**用户原话（问答摘要，原文记录）**：「全 spec 范围删除被删伪指令定义（推荐）」。故**须以 `grep -rn` 全 `spec/` 实测为准**，逐一删除/标注，保证 `check-asm-list-drift`/`check-spec-codeblocks`/`check-asm-prose` 无悬空引用而报红。（此点已偏离 `SPEC-104k` 的 00/03/06 假设，记入 `SPEC-104k` 完成区。）
  - **不改** `contracts/opcodes.yaml`、**不实现** LLVM（伪指令展开归 `LLVM-051t`）；`spec/`、`.tao/knowledge/` 为共享文件，**串行**。
  - 临时目录 `/tmp/opencode/SPEC-106t/`；**不提交 git**。

## 验收标准

1. **表收缩**：`spec/SimRISC-00 §伪指令` 表恰含 **8 条合成型**（`set.rd`/`set.rb`/`set.ft`/`set.fo` × {imm,reg}）；`grep -nE '\| `(nop|return|not\.|neg\.)'` 对 `SimRISC-00` 无保留行。
2. **全 spec 一致**：`grep -rn` 全 `spec/` 后，凡定义被删伪指令的小节均已标注删除/移除，**无**「规范性保留 + 详细定义」的悬空引用；`set.rd/set.rb/set.ft/set.fo` 展开与 `ADR-0013 D11` 逐条一致。
3. **合约/台账**：`contract-asm.md` §6 为收缩后口径、§11 缺口更新；`MEMORY.md` 偏离台账**恰 7 项**（新增项指针指向 `ADR-0013 D11`）。
4. **门控**：`make check` EXIT=0（含 `check-asm-list`/`check-asm-list-drift`/`check-asm-prose`/`check-spec-codeblocks`/`check-spec-refs`）；完成区给真实命令输出与退出码。
5. **反例门控**：`.work/evidence/SPEC-106t/run.sh` 对注入反例（把 `nop` 行加回、把 `ret` 改为无参、把偏离台账删 1 行）**必须 FAIL**，还原后回绿。
6. `git status --untracked-files=all` 仅本任务应有改动；未改 `contracts/**`、未改实现。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
> **用户裁定（2026-10-06）**：本任务文件范围 = **全 `spec/`**（含 `SimRISC-04/06/08/09/10/11`），非仅 `SimRISC-00/03/06`。用户原话：「全 spec 范围删除被删伪指令定义（推荐）」。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
