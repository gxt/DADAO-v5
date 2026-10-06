# SPEC-106t: 伪指令集收缩 spec 修订（按 ADR-0013 D11）

**模块**：spec
**项目里程碑**：M4
**依赖**：`SPEC-109t`、`INFRA-045t`、`SPEC-110t`
**状态**：已验证

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

**测试结果**：全部通过。
- 一键证据脚本 `.work/evidence/SPEC-106t/run.sh`：默认模式 **7/7 检查 PASS，EXIT=0**（C1 权威源迁移 / C2 SimRISC-00 无定义行 / C3 全 spec 一致 / C4 contract-asm 收缩 / C5 MEMORY 恰 7 项 / C6 README 指针 / C7 五个 spec 门控）；`--inject` 自检 **4/4 场景 PASS，EXIT=0**（注入有效→断言 FAIL→md5 还原→回绿）。日志：`.work/log/spec/SPEC-106t-evidence-baseline.log`、`…-evidence-inject.log`。
- `make check` **EXIT=0**（`.work/log/spec/SPEC-106t-make-check-final.log`，末行 `repository checks: PASS`，lit 34/34）。
- 单门控：`check-spec-refs` EXIT=0、`check-asm-list` EXIT=0、`check-asm-list-drift` EXIT=0、`check-asm-prose` EXIT=0、`check-spec-codeblocks` EXIT=0、`check-spec-drift` EXIT=0（日志 `.work/log/spec/SPEC-106t-{门控}.log`）。
- 失败原因：无。

**修改文件**：
- `spec/Toolchain-01-汇编语言.md`（§6 重写为**唯一权威**：8 保留 + 10 删除替代 + `ret` 显式；§11 伪指令 18→8）。
- `spec/SimRISC-00-指令系统设计.md`（§伪指令：删 18 条定义表，改「权威指针 + 已删 10 条功能说明/替代」）。
- `spec/SimRISC-04-64位数据运算.md`、`spec/SimRISC-06-控制流.md`、`spec/SimRISC-08-32位数据运算.md`、`spec/SimRISC-09-16位数据运算.md`、`spec/SimRISC-10-8位数据运算.md`、`spec/SimRISC-11-其它.md`（§not/§neg/§return/§nop 标注「伪指令（已删除）」+ 真实指令替代）。
- `spec/DADAO-22-SBI-主管系统二进制接口.md`（**越界披露**：1 处被删伪指令**使用** `not.o rd16, rd31` → `xnor.o rd16, rd31, rd0`，使示例与收缩后口径一致）。
- `.tao/knowledge/contract-asm.md`（§6 收缩口径：权威源=`Toolchain-01 §6`、8 条、反汇编只显真实指令、被删 10 条替代；§11 `伪指令 18 条|未实现`→`8 条（合成型）|待实现`；投影行 ④ `tests/lit/MC`→`tests/llvm/lit/MC/DADAO`）。
- `.tao/knowledge/MEMORY.md`（偏离台账 6→**7** 项，新增第 7 项指向 `ADR-0013 §D11`；仅归一化登记+指针）。
- `spec/README.md`（投影表 `Toolchain-01` 行 ④ → `tests/llvm/lit/MC/DADAO`；`SimRISC-01…06,08…12` 行 ④ 旧悬空 `tests/lit/MC/Dadao` → 新路径）。
- `.tao/tasks/spec/SPEC-106t-….md`（本任务书：完成区/自审/状态）。
- 证据与日志（`.work/`，整体 gitignored、未入库）：`.work/evidence/SPEC-106t/run.sh`、`.work/log/spec/SPEC-106t-*.log`。
- **未动**：`contracts/**`、`components/**`（未实现 LLVM）、`tools/**`、其它 spec/knowledge 文件。

**验收结果**（逐条，真实输出）：
1. **权威源迁移**：`spec/Toolchain-01-汇编语言.md §6` 现为唯一权威——8 条合成型（`set.rd`×2/`set.rb`×2/`set.ft`×2/`set.fo`×2）+ 展开规则（常量→最少指令数；符号/可重定位→固定 3 片 + `R_DADAO_ABS48`；`set.rb` `wp0–wp3`/地址 ≤48 位/不补 `set.ow-rb`；`ret rdHA, imms18` 显式、不加无参）+ 被删 10 条替代；`grep -nE '\| `(nop|return|not\.|neg\.)' spec/SimRISC-00-指令系统设计.md` → **无匹配（rc=1）**（SimRISC-00 仅功能说明/替代，无定义行）。证据脚本 C1/C2 PASS。
2. **全 spec 一致**：`grep -rnE '^\|[[:space:]]*`(nop|return|not\.[bwto]|neg\.[bwto])`' spec/`（排除 `SimRISC-0.5.3/`）→ **无匹配**；被删小节头均标 `伪指令（已删除）`（`grep` 实测 SimRISC-04/06/08/09/10/11）；`set.*` 展开与 `ADR-0013 D11` 逐条一致。证据脚本 C3 PASS。
3. **合约/台账/投影**：`contract-asm §6` 为收缩口径（`8 条合成型`、`反汇编只输出真实硬件指令`、无 `18 条`）、`§11` = `伪指令 8 条（合成型）| 待实现`；`MEMORY.md` 偏离台账 **恰 7 项**（`grep -cE '^\| [0-9]+ \|'`=7，第 7 项含 `ADR-0013 §D11`）；`spec/README.md` 投影行含 `tests/llvm/lit/MC/DADAO`、无 `tests/lit/MC`。证据脚本 C4/C5/C6 PASS。
4. **门控**：`make check` **EXIT=0**（含 `check-asm-list`/`check-asm-list-drift`/`check-asm-prose`/`check-spec-codeblocks`/`check-spec-drift`；**注意 `check-spec-refs` 为 standalone、不在 `make check` 目标内**，已单独执行 **EXIT=0**）；见上日志。证据脚本 C7 PASS。
5. **反例门控**：`run.sh --inject` EXIT=0，4 场景均「注入有效→断言 FAIL→md5 还原→回绿」：I1 加回 `nop` 定义行→C2 FAIL；I2 `ret` 改无参→C1 FAIL；I3 台账删 1 行→C5 FAIL；I4 删 `nop`→`swym 0` 替代写法→C1 FAIL。真实输出见 `.work/log/spec/SPEC-106t-evidence-inject.log`。
6. `git status --untracked-files=all` 仅上述 12 个文件（`spec/**` + `contract-asm.md` + `MEMORY.md` + 本任务书）；**未改** `contracts/**`、**未改** `components/**`（未实现 LLVM）、无残留。

**新发现/坑**：
- **`contract-isa.md` 投影未随收缩更新（越界未改，已登记遗留）**：`.tao/knowledge/contract-isa.md` 的 §5.4/§6.6/§8.7/§10.5/§11.5/§12.5/§13.3 仍将 `nop`/`return`/`not.o`/`neg.{b,w,t,o}` 列为伪指令（投影层滞后）。它不在本任务列出的文件范围（`spec/**`+`contract-asm.md`+`MEMORY.md`+`spec/README.md`），**未修改**；为使其 `[SimRISC-xx §…伪指令]` 引用不悬空，被删小节**头采用 `X 伪指令（已删除）`**（`（` 是 `check_spec_refs.resolve_section` 认可的 lead-in），故 `check-spec-refs` 全绿。
- **`docs/impact-matrix.md` 悬空引用（未改，登记）**：其第 94/114/146 行仍描述 `contract-isa §6.6/§8.7/§13.3`（`SimRISC-04/06/11 §not/§neg/§return/§nop 伪指令`）；`docs/` 不在本任务范围，未改。
- **`tools/spec/check_spec_codeblocks.py` 的 `PSEUDO_INSTRUCTIONS` 仍列 10 条被删项**（第 65–70 行）：该门控对 `simrisc` 代码块中的伪指令助记符做豁免；收缩后该集合应仅留 4 个 `set.*` 助记符，否则被删项若重新出现在代码块会被静默豁免。**`tools/**` 不在本任务范围，未改**；已由本任务证据脚本 C2/C3 以「定义行/小节头」形态兜住反例。
- **`not.b/w/t` 替代口径**：任务/ADR 原文作 `xnor.o`/`xnor.X`；因窄位宽 `xnor.b/w/t` 已随 `SPEC-069t` 删除（SimRISC-08/09/10 明载），且 `SPEC-104k` 的 `TESTCASES-032t` 明确「`not`→`xnor.o`（仅 64 位；`.b/.w/.t` 不适用）」，故 `Toolchain-01 §6` 落为「`not.{b,w,t,o}` → `xnor.o`；窄位宽无等宽替代」，与既有规范一致，且不会让 `check-spec-codeblocks` 因 `xnor.b/w/t`（不存在）报未知助记符。
- **`check-spec-refs` 为 standalone（不在 `make check` 目标内）**：已单独执行并入证据脚本 C7；任务验收要求「含 check-spec-refs」，据此显式运行。
- 建议沉淀：伪指令权威定义已由上游「`SimRISC-00 §伪指令` 18 条」迁至 `Toolchain-01 §6`（8 合成型 + 10 替代），`SimRISC-00` 降为功能说明；偏离台账新增第 7 项（`ADR-0013 D11`）。

**遗留问题**：
- ⏭ **投影层滞后（越界，建议后续 SPEC/相应任务处理）**：`contract-isa.md` 的伪指令小节（§5.4 保留 `set.*` 正确；§6.6/§8.7/§10.5/§11.5/§12.5/§13.3 为已删项）与 `docs/impact-matrix.md` 的对应行未随本收缩更新。本任务文件范围不含二者，且门控（含 `check-spec-refs`）全绿，故未改；建议立后续任务把 `contract-isa.md` 的已删伪指令小节改为「已删除 + 真实指令替代」并同步 `docs/impact-matrix.md`。
- ⏭ **`tools/spec/check_spec_codeblocks.py` 的 `PSEUDO_INSTRUCTIONS` 建议收缩**至 `{set.rd,set.rb,set.ft,set.fo}`（超出本任务范围）；现已由证据脚本反例门控覆盖，非阻塞。
- 其余：无；无未修 finding。

> **用户裁定（2026-10-06，原文记录）**：
> ① 本任务文件范围 = **全 `spec/`**（含 `SimRISC-04/06/08/09/10/11`），非仅 `SimRISC-00/03/06`。用户原话：「全 spec 范围删除被删伪指令定义（推荐）」。
> ② 权威伪指令集迁至 **`spec/Toolchain-01-汇编语言.md §6`**；`SimRISC-00 §伪指令` 删除定义、改留「功能说明 + 如何实现」（如 `not`→`xnor.o`、`neg`→`sub.sX`），不再作为指令；同步 `contract-asm §6` + `spec/README` 投影表指针。
> ③ **本任务不产向量**（2026-10-06 二次裁定）：`not`/`neg` 替代功能（`xnor.o`/`sub.sX`）的专门向量**移出**本任务，归 **`TESTCASES-032t`**（单独一个 `TESTCASES`）。用户原话：「`not`/`neg` 功能向量单独一个 `TESTCASES`；`Process-05 §6` 落点同步单独一个 `SPEC`」。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：全局 `subagent_depth=1`，engineer **自主逐行审查**（`git diff` 全量 12 文件逐行 + 改动后 `spec/Toolchain-01 §6`/`SimRISC-00 §伪指令`/`SimRISC-04/06/08/09/10/11` 通读 + 事前/事后门控输出对照），并按任务书验收 1–6 与硬约束逐条核验。

**判决**：实现完成；验收 1–6 均有真实输出支撑；无未修阻断项 → 状态置 `待验收`。

**审查意见（自主逐行）**：
- **逻辑/文本正确性**：§6 权威表 8 行与 `ADR-0013 D11` 的 8 条逐条对应（`set.rd`/`set.rb`/`set.ft`/`set.fo` 各 2 源形式）；展开规则覆盖「常量→最少指令数、符号→固定 3 片 + `R_DADAO_ABS48`」「`set.rb` `wp0–wp3`/≤48 位/不补 `set.ow-rb`」「`ret rdHA, imms18` 显式、不加无参」；被删 10 条逐条给替代（`swym 0`/`ret rd0, 0`/`xnor.o`/`sub.sX`）。`SimRISC-00` 删除定义表且不含 `| \`nop\`` 等行（grep rc=1）。
- **一致性/悬空引用**：被删小节头改 `X 伪指令（已删除）`，使 `contract-isa.md` 既有 `[SimRISC-xx §X 伪指令]` 引用仍可解析（`check-spec-refs` 0 violations）；`contract-asm §6` 去掉 `[SimRISC-00 §伪指令]` 后改引 `[Toolchain-01 §6][ADR-0013 D11]`，无悬空。`README` 两处旧路径（`tests/lit/MC`、`tests/lit/MC/Dadao`）同步为新结构。
- **边界/未覆盖**：`SimRISC-02 §48` 提及 `set.*` 伪指令（保留项）未动；`SimRISC-03` 既有 `set.*` 展开正文按任务要求**保留**；`DADAO-22` 的 `not.o` **使用**改为 `xnor.o`（越界披露）；`docs/`、`contract-isa.md`、`tools/` 未动（登记）。
- **防造假**：全部门控命令 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，**无 `tee`**；反例自检给出 md5 前后与「注入→FAIL→还原→回绿」真实输出；`git status` 用 `-c core.quotepath=false`。未以 validator 绿灯替代语义判断。
- **范围/纪律**：仅任务书列出的文件 + 1 处披露的 `DADAO-22`；未改 `contracts/**`/`components/**`/`tools/**`；临时目录 `/tmp/opencode/SPEC-106t/`；未提交 git；未改函数签名、未引入依赖。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `check-spec-refs` 因被删小节头改名而报 7 处引用失败（`contract-isa.md` 引 `§not/§neg/§return/§nop 伪指令`） | ✅已修 | 小节头由 `— 不再作为伪指令` 改为 `X 伪指令（已删除）`（`（` 为 `resolve_section` 认可 lead-in） | `make check-spec-refs` → `结果: PASS (0 violations)` EXIT=0；证据 C7 PASS |
| F2 `contract-isa.md` 仍将已删伪指令列为投影（权威源唯一） | ⏭延后（越界） | —（不在任务书文件范围；改之将违反「只动任务书范围」） | 已登记「新发现/遗留」；`check-spec-refs` 绿、`git status` 仅范围文件 |
| F3 `docs/impact-matrix.md` 悬空引用被删小节 | ⏭延后（越界） | —（`docs/` 不在范围） | 已登记；非门控 |
| F4 `tools/spec/check_spec_codeblocks.py` 的 `PSEUDO_INSTRUCTIONS` 仍含 10 条已删项 | ⏭延后（越界） | —（`tools/**` 不在范围） | 已登记；证据脚本 C2/C3 以定义行/小节头形态兜住反例 |
| F5 ADR 原文 `xnor.o`/`xnor.X`：`not.b/w/t` 无等宽替代的落法 | ❌不修（依既有 Accepted 规范，非重决策） | §6 落为 `not.{b,w,t,o} → xnor.o`，并注明窄位宽无等宽替代 | SimRISC-08/09/10 明载 `xnor.b/w/t` 已删；`SPEC-104k` `TESTCASES-032t`：`not`→`xnor.o`（仅 64 位，`.b/.w/.t` 不适用） |
| F6 `contract-isa.md` 引用导致必须保 `§X 伪指令` 可解析，与「删除定义」措辞张力 | ✅已修 | 用 `X 伪指令（已删除）` 头——既标删除又保引用可解析 | `grep -rnE '^#+ *(nop\|return\|not\|neg) '` 全部含 `（已删除）`；`check-spec-refs` 绿 |

**约束自查**：只改任务书范围文件（+1 处披露的 `DADAO-22`）；未改 `contracts/**`、`components/**`、`tools/**`；未改函数签名；未引入依赖；临时目录 `/tmp/opencode/SPEC-106t/`；未提交 git；完成区结论与真实输出逐条对齐。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑证据脚本（baseline + inject）+ 独立注入反例（与 I1–I4 不同）+ 独立 grep/门控复核 + 越界/残留判定。

**判决**：**Accepted**

##### 1. 证据脚本审查

脚本 `.work/evidence/SPEC-106t/run.sh` 结构合格：
- `set -uo pipefail`、FAIL 计数器、结尾 `exit $FAIL`（无 `tee` 吞退出码）
- 7 项断言（C1–C7）+ 4 项注入自检（I1–I4），每项注入含 md5 前后比对 + 还原验证
- 每条断言均有可达 FAIL 路径（C1 查形式存在性 + 关键短语；C2 查定义行缺失；C3 查表行 + 小节头标注；C4/C5/C6 查文本精确匹配；C7 跑5 个门控）

##### 2. 独立重跑记录

**Baseline**：
```
$ bash .work/evidence/SPEC-106t/run.sh > /tmp/.../baseline.log 2>&1; echo "EXIT=$?"
===== SPEC-106t baseline acceptance =====
[check] C1 Toolchain-01 §6 权威：8 保留形式 + 10 替代写法 + ret 显式两操作数
[PASS] C1 Toolchain-01 §6 authoritative set
[check] C2 SimRISC-00 §伪指令：无被删项定义行，仅有功能说明/替代
[PASS] C2 SimRISC-00 no deleted def rows + guidance
[check] C3 全 spec：无被删伪指令定义行/表，被删小节均标注（已删除）
[PASS] C3 全 spec consistent (no deleted defs; sections annotated)
[check] C4 contract-asm §6 收缩口径 + §11 伪指令 8 条
[PASS] C4 contract-asm shrunk
[check] C5 MEMORY 偏离台账恰 7 项且第 7 项指向 ADR-0013 D11
[PASS] C5 MEMORY ledger (7 rows, row7 -> ADR-0013 D11)
[check] C6 spec/README 投影指针（tests/llvm/lit/MC/DADAO，无 tests/lit/MC）
[PASS] C6 README pointers
[check] C7 spec 门控（spec-refs/asm-list/asm-list-drift/asm-prose/spec-codeblocks）
  check-spec-refs EXIT=0
  check-asm-list EXIT=0
  check-asm-list-drift EXIT=0
  check-asm-prose EXIT=0
  check-spec-codeblocks EXIT=0
[PASS] C7 spec gates
-----------------------------------------
SPEC-106t EVIDENCE: PASS
EXIT=0
```

**Inject self-test**：
```
$ bash .work/evidence/SPEC-106t/run.sh --inject > /tmp/.../inject.log 2>&1; echo "EXIT=$?"
===== SPEC-106t counter-example injection self-test =====
----- I1: 把 `nop` 定义行加回 SimRISC-00 -----
[PASS] I1 injection effective (7b27... -> 5378...)
[PASS] I1 injected -> C2 FAILED as expected
[PASS] I1 restored (7b27...)
[PASS] I1 restored -> C2 green again
----- I2: 把 `ret` 改为无参（Toolchain-01 §6）-----
[PASS] I2 injection effective (4c39... -> 18db...)
[PASS] I2 injected -> C1 FAILED as expected
[PASS] I2 restored (4c39...)
[PASS] I2 restored -> C1 green again
----- I3: 偏离台账删 1 行（MEMORY row 7）-----
[PASS] I3 injection effective (20a7... -> 8693...)
[PASS] I3 injected -> C5 FAILED as expected
[PASS] I3 restored (20a7...)
[PASS] I3 restored -> C5 green again
----- I4: 删去 §6 被删项替代写法（nop -> swym 0）-----
[PASS] I4 injection effective (4c39... -> 82f3...)
[PASS] I4 injected -> C1 FAILED as expected
[PASS] I4 restored (4c39...)
[PASS] I4 restored -> C1 green again
-----------------------------------------
SPEC-106t EVIDENCE: PASS
EXIT=0
```

##### 3. 独立注入（与 I1–I4 不同）

**注入目标**：`SimRISC-04` 第 174 行 `#### not 伪指令（已删除）` → 移除 `（已删除）` → 应触发 C3（未标注删除的小节头）。

```
$ sed -i '174s/伪指令（已删除）/伪指令/' spec/SimRISC-04-64位数据运算.md
$ md5sum: BEFORE=8ae3... AFTER=c4f7... (INJECT OK)
$ git diff --name-only: spec/SimRISC-04-64位数据运算.md (注入有效，非空)

$ # 验证 C3 检测到：
$ grep -rnE '^#+[[:space:]]*(nop|return|not|neg)[[:space:]]' spec/ --include='*.md' | grep '伪指令' | grep -v '（已删除）'
./spec/SimRISC-04-64位数据运算.md:174:#### not 伪指令
C3 -> FAIL (expected)

$ # 还原：
$ cp /tmp/.../S04.bak spec/SimRISC-04-64位数据运算.md
$ md5sum: RESTORED=8ae3... (MATCH)
$ C3 -> PASS (restored)
$ git diff --name-only: 不含 SimRISC-04（仅任务书自身改动）
```

##### 4. 独立复核

| 检查项 | 结果 |
|--------|------|
| **权威源唯一**：`grep -nE '\| `(nop\|return\|not\.\|neg\.)' spec/SimRISC-00*.md` | EXIT=1（无匹配）✅ |
| **全 spec 无被删定义行**：`grep -rnE '^\|[[:space:]]*`(nop\|return\|not\.[bwto]\|neg\.[bwto])`' spec/` | EXIT=1（无匹配）✅ |
| **全 spec 小节头均标（已删除）**：`grep ... \| grep '伪指令' \| grep -v '（已删除）'` | EXIT=1（无匹配）✅ |
| **contract-asm §6**：8 条合成型、反汇编只输出真实硬件指令、无 stale 18 条 | ✅ |
| **contract-asm §11**：`伪指令 8 条（合成型） \| 待实现` | ✅ |
| **MEMORY 偏离台账**：`grep -cE '^\| [0-9]+ \|'` = 7；第 7 项含 `ADR-0013 §D11` | ✅ |
| **README 投影**：含 `tests/llvm/lit/MC/DADAO`；无 stale `tests/lit/MC` | ✅ |
| **`make check`** | EXIT=0，lit 34/34，`repository checks: PASS` ✅ |
| **`make -s check-spec-refs`** | EXIT=0，`PASS (0 violations)` ✅ |
| **`git status`** | 仅 13 个预期文件（`spec/**` 10 + `contract-asm.md` + `MEMORY.md` + 任务书）；未改 `contracts/**`/`components/**`/`tools/**` ✅ |
| **Toolchain-01 §6 与 ADR-0013 D11 一致性**：8 保留形式逐条对应；展开规则覆盖常量/符号/`set.rb` wp0–wp3/≤48/不补 `set.ow-rb`；`ret rdHA, imms18` 显式不加无参；被删 10 条替代含窄位宽说明 | ✅ |

##### 5. 越界/残留判定

| 项 | 判定 | 理由 |
|----|------|------|
| **`contract-isa.md` 投影层**（§6.6/§8.7/§10.5/§11.5/§12.5/§13.3 仍列已删伪指令） | **另立任务**，不阻塞本任务 | 不在任务书文件范围；`check-spec-refs` 全绿（被删小节头 `X 伪指令（已删除）` 格式可被 `resolve_section` 解析）；改 `contract-isa.md` 属投影层同步，应独立任务处理 |
| **`docs/impact-matrix.md` 悬空引用** | **另立任务**，不阻塞 | `docs/` 不在范围；非门控覆盖 |
| **`tools/spec/check_spec_codeblocks.py` 的 `PSEUDO_INSTRUCTIONS` 仍含 10 条** | **登记遗留**，不阻塞 | `tools/**` 不在范围；证据脚本 C2/C3 以定义行/小节头形态兜住反例；建议后续收缩至 `{set.rd,set.rb,set.ft,set.fo}` |
| **`spec/DADAO-22` 1 处 `not.o`→`xnor.o`** | **合理越界** | 使示例与收缩后口径一致，属必要修正；已披露 |

**判决：Accepted** —— 验收命令块在独立重跑下全部通过（baseline 7/7 PASS + inject 4/4 PASS + 独立注入 1/1 FAIL→还原→回绿）；约束无违反；越界/残留均合理处置（登记/另立任务）。
