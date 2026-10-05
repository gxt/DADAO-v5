# SPEC-106t: 伪指令集收缩 spec 修订（按 ADR-0013 D11）

**模块**：spec
**项目里程碑**：M4
**依赖**：`SPEC-109t`、`INFRA-045t`、`SPEC-110t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含；决策已定，本任务只落 **spec 正文**，**不重新决策、不产向量**）：
  - `.tao/adr/adr-0013-assembly-syntax.md` 的 **D11**（2026-10-06 用户逐条确认，`Accepted`）——**本任务唯一决策来源**。**用户裁定原话（原文引用）**：「**原则**：只保留『**ISA 无法直接表达、需多指令合成**』的伪指令；**1:1 助记符别名一律不保留**；**反汇编只显示真实硬件指令**。**保留（实现，8 条）**：`set.rd rd, imm64`（常量 → 最少指令数 `set.zw/ow`+`or.w/andn.w`；符号 → 3 片 + `R_DADAO_ABS48`）、`set.rd rd, rs`（`rb2rd`/`rf2rd`/`ra2rd`/`rd2rd`）；`set.rb rb, imm64`（`set.zw-rb`+`or.w-rb`）、`set.rb rb, rs`（`rd2rb`/`rb2rb`）；`set.ft rf, imm32`（2 条 `set.w`）/ `set.ft rf, rs`（`rd2rf`/`ft2ft`）；`set.fo rf, imm64`（4 条 `set.w`）/ `set.fo rf, rs`（`rd2rf`/`fo2fo`）。**删除（不实现，10 条）**：`nop`（用 `swym 0`）、`return`（用 `ret rd0, 0`）、`not.{b,w,t,o}`（用 `xnor.o`/`xnor.X`）、`neg.{b,w,t,o}`（用 `sub.sX`）。**`ret` 语法**：保持 `ret rdha, imms18` 显式；**不加无参形态**。**偏离**：本决策删除上游 `SimRISC-0.5.4` 定义的 5 类伪指令 ⇒ **上游偏离**，登记 `MEMORY.md` 偏离台账。」
  - **现状**：`spec/Toolchain-01-汇编语言.md §6`（第 165–173 行）现仅**转述**「上游 `SimRISC-00 §伪指令` 规定 18 条伪指令」；`spec/SimRISC-00 §伪指令`（约第 395–415 行）为定义来源；被删伪指令的详细定义散布在 `spec/SimRISC-04 §not/§neg`、`SimRISC-06 §return`、`SimRISC-08/09/10 §neg`、`SimRISC-11 §nop`（`SimRISC-08/09/10 §not` 已标「已删除」）。
  - `.tao/knowledge/contract-asm.md §6`（伪指令，现为 18 条口径）、§11（缺口 18 条未实现）；`spec/README.md` 投影表 `Toolchain-01` 行（④列现指 `tests/lit/MC`）。
  - `.tao/knowledge/MEMORY.md` §「上游 ↔ v5 偏离台账」（当前 **6 项**）。
  - `spec/DADAO-11-AEE-应用程序运行环境.md`（上游依据溯源；**只读对照**）。
- **输出**：
  1. **权威伪指令集迁至 `spec/Toolchain-01-汇编语言.md §6`**：`Toolchain-01 §6` 不再「转述上游 18 条」，改为**规范正文**——明确 `ADR-0013 D11` 的 **8 条合成型**（`set.rd`×2 / `set.rb`×2 / `set.ft`×2 / `set.fo`×2）及其**展开规则**（常量→最少指令数；符号/可重定位→固定 3 片 + `R_DADAO_ABS48`；`set.rb` `wp0–wp3`/地址 ≤48 位/不补 `set.ow-rb`；`ret` 显式不加无参），并**分列被删 10 条**及其替代写法。
  2. **`spec/SimRISC-00 §伪指令` 删除伪指令定义**：**不再作为指令**；改留「**功能说明 + 如何实现**」——如 `not.{b,w,t,o}` → `xnor.o`/`xnor.X`、`neg.{b,w,t,o}` → `sub.sX`、`nop` → `swym 0`、`return` → `ret rd0, 0`（**说明性**，不构成指令定义）。
  3. **全 spec 范围删除/标注被删伪指令定义**：以 `grep -rn` 实测为准（至少 `SimRISC-04`、`SimRISC-06`、`SimRISC-08/09/10`、`SimRISC-11`），逐条标注删除/移除其**规范性定义**，并留「用真实指令替代」指引；`set.rd/set.rb/set.ft/set.fo` 的既有展开正文核正保留。
  4. `.tao/knowledge/contract-asm.md` §6 改为收缩后口径（**权威源 = `Toolchain-01 §6`**；8 条合成型；反汇编只显真实指令；被删 10 条列替代），§11 缺口更新（伪指令由「18 条未实现」→「8 条待实现」）。
  5. `.tao/knowledge/MEMORY.md` 偏离台账：**新增 1 项**——「删除上游 `SimRISC-0.5.4` 定义的 5 类伪指令（`nop`/`return`/`not.*`/`neg.*`）」，指向 `ADR-0013 D11`（台账 **6 项 → 7 项**；只做归一化登记 + 指针，不新增决策）。
  6. **`spec/README.md` 投影表指针同步**：`Toolchain-01` 行（正文/叙述合约/机器数据/门控/可执行各列）之投影指针须指向新的权威伪指令位置（`Toolchain-01 §6` 为其正文），并保证无悬空引用。
- **约束**：
  - **只落正文、不重新决策**：`ADR-0013 D11` 已 `Accepted`；不得增删其未列的伪指令，不得改 `ret` 语法。
  - **不产向量（用户裁定 2026-10-06）**：本任务**只做 spec 文本**，**不产出任何测试向量**；`not`/`neg` 替代功能（底层真实指令 `xnor.o`/`sub.sX`）的 **L1 编码 + L3 执行**专门向量归 **`TESTCASES-032t`**（落 `tests/llvm/lit/MC/DADAO/`、`tests/llvm/codegen/m4/`）。
  - **文件范围 = 全 `spec/`（用户裁定 2026-10-06）**：`SPEC-104k §说明` 假设改 `SimRISC-00/03/06`，但实测被删伪指令定义散布在 `SimRISC-04/06/08/09/10/11`。**用户原话（原文记录）**：「全 spec 范围删除被删伪指令定义（推荐）」。故**须以 `grep -rn` 全 `spec/` 实测为准**，逐一删除/标注，保证 `check-asm-list-drift`/`check-spec-codeblocks`/`check-asm-prose`/`check-spec-refs` 无悬空引用而报红。
  - **权威源唯一**：伪指令**定义**只在 `Toolchain-01 §6`；`SimRISC-00` 仅留功能说明；`contract-asm §6` 为投影。不得两处并存定义。
  - **不改** `contracts/opcodes.yaml`、**不实现** LLVM（伪指令展开归 `LLVM-051t`）。
  - **串行**：依赖 `SPEC-109t`（共享 `SimRISC-00/11`、`contract-asm §6`）；依赖 `INFRA-045t`（新落点已重排，`spec/README.md` 投影指针用新路径）；依赖 `SPEC-110t`（`Process-05 §6` 落点体例先行确定，本任务路径引用与之对齐）。`spec/`、`.tao/knowledge/` 为共享文件，串行。
  - 临时目录 `/tmp/opencode/SPEC-106t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`。

## 验收标准

1. **权威源迁移**：`spec/Toolchain-01-汇编语言.md §6` 为伪指令**定义**的唯一权威（8 条合成型 + 展开规则 + 被删 10 条替代）；`grep -nE '\| `(nop|return|not\.|neg\.)'` 对 `SimRISC-00` 无**定义**保留行（仅「功能说明 + 如何实现」）。
2. **全 spec 一致**：`grep -rn` 全 `spec/` 后，凡定义被删伪指令的小节均已标注删除/移除，**无**「规范性保留 + 详细定义」的悬空引用；`set.rd/set.rb/set.ft/set.fo` 展开与 `ADR-0013 D11` 逐条一致。
3. **合约/台账/投影**：`contract-asm.md §6` 为收缩后口径、§11 更新（18→8）；`MEMORY.md` 偏离台账**恰 7 项**（新增项指针指向 `ADR-0013 D11`）；`spec/README.md` 投影表 `Toolchain-01` 行指针无悬空（含 `tests/llvm/lit/MC/DADAO/` 等新路径）。
4. **门控**：`make check` EXIT=0（含 `check-asm-list`/`check-asm-list-drift`/`check-asm-prose`/`check-spec-codeblocks`/`check-spec-refs`）；完成区给真实命令输出与退出码。
5. **反例门控**：`.work/evidence/SPEC-106t/run.sh` 对注入反例（把 `nop` 定义行加回、把 `ret` 改为无参、把偏离台账删 1 行、删去 `Toolchain-01 §6` 某被删项的替代写法）**必须 FAIL**，还原后回绿；给真实输出与退出码。
6. `git status --untracked-files=all` 仅本任务应有改动；未改 `contracts/**`、未改实现。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
> **用户裁定（2026-10-06，原文记录）**：
> ① 本任务文件范围 = **全 `spec/`**（含 `SimRISC-04/06/08/09/10/11`），非仅 `SimRISC-00/03/06`。用户原话：「全 spec 范围删除被删伪指令定义（推荐）」。
> ② 权威伪指令集迁至 **`spec/Toolchain-01-汇编语言.md §6`**；`SimRISC-00 §伪指令` 删除定义、改留「功能说明 + 如何实现」（如 `not`→`xnor.o`、`neg`→`sub.sX`），不再作为指令；同步 `contract-asm §6` + `spec/README` 投影表指针。
> ③ **本任务不产向量**（2026-10-06 二次裁定）：`not`/`neg` 替代功能（`xnor.o`/`sub.sX`）的专门向量**移出**本任务，归 **`TESTCASES-032t`**（单独一个 `TESTCASES`）。用户原话：「`not`/`neg` 功能向量单独一个 `TESTCASES`；`Process-05 §6` 落点同步单独一个 `SPEC`」。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
