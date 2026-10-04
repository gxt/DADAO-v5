# SPEC-091t: `contract-asm.md`——汇编语言叙述合约（清投影缺口①）

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 目标

新建 `.tao/knowledge/contract-asm.md`——把 `spec/Toolchain-01-汇编语言.md`（v5 自定规范，v1.1）**归一化**为叙述合约（投影类型①），消除 `spec/README.md` 投影表与 `Process-02` 合约清单中登记的**缺口①**（`contract-asm.md`）。

## 背景与现状（实测）

- `spec/README.md` §投影表 `Toolchain-01` 行：①叙述合约 = **`缺口`（`contract-asm.md`）**；同时 ④ 已有 `tests/lit/MC`、② 已有 `contracts/opcodes.yaml`（format/汇编形式列）、③ 已有 `check_asm_prose.py`/`check_asm_list_consistency.py`/`check_asm_list_drift.py`、生成投影 `.tao/knowledge/contract-asm-list.md`（227 条，已落位）。
- `spec/Process-02` 合约清单：`contract-asm.md` 状态 = **缺口**。
- `spec/Toolchain-01-汇编语言.md` 共 294 行，章节：
  - §1 范围与术语、§2 词法与记号（2.1 空白与大小写 / 2.2 注释 / 2.3 标识符与标签 / 2.4 数字与立即数单位 / 2.5 寄存器名）、§3 地址表达式 `[...]`（3.1 语法 / 3.2 语义 / 3.3 示例）、§4 寄存器组 `{...}` 与条件标记 `?`（4.1 语法 / 4.2 规则 / 4.3 示例 / `{...}` 用途速查表）、§5 指令语法（按格式类）、§6 伪指令、§7 指导符（directives）、§8 汇编器选项、§9 诊断、§10 汇编↔反汇编往返、§11 实现状态与缺口、§12 机器检查、§13 cfx 别名约定（13.1–13.8）、附：与上游 `spec/` 的关系。
- 合约编写规范见 `spec/Process-02-合约编写规范.md`（§ 编号、精确 bit 范围、异常 if-then、每条规范断言标注来源 `[spec §x]`）；投影规则见 `spec/README.md` §投影表（决策 8）。

## 交付物

1. **`.tao/knowledge/contract-asm.md`**（新建，叙述合约）：覆盖 `Toolchain-01` 全部章节，逐节归一化为**可精确消费**的断言型合约：
   - 词法/记号（注释、标识符、标签、数字与立即数单位、寄存器名）；
   - 地址表达式 `[...]` 三类语义与公式；
   - 寄存器组 `{...}` 与条件标记 `?` 的语法、规则（**含块赋值 count 语义、`{start:end}` 记法**）、用途速查；
   - 各格式类指令语法（`oiii`/`rrii`/`rrri`/`rwii`/`rrrr`/`orrr`/`orri` 等）；
   - 伪指令（`return`/`not.o`/`neg.*`/`set.ft`/`set.fo` 等）、指导符、汇编器选项；
   - 诊断（错误级别、退出码约定）、汇编↔反汇编往返要求、实现状态与缺口；
   - cfx 别名约定（13.1–13.8，指向 `.tao/knowledge/contract-cfx-aliases.md`）。
   - 每条规范性断言标注来源 `[Toolchain-01 §x]`（必要时并列上游 `[SimRISC-0x §y]`）。
2. **`.tao/knowledge/contract-asm.md` 来源头**：按 `check_spec_drift.py` 可分类的要求书写（见「约束」）。
3. **`spec/README.md`**：投影表 `Toolchain-01` 行 ① 列由 `缺口`（`contract-asm.md`）改为 `contract-asm.md`；从「登记缺口」表中移除 `contract-asm.md` 行。
4. **`spec/Process-02-合约编写规范.md`**：合约清单中 `contract-asm.md` 状态由 **缺口** 改为 **现行**。

## 约束

- **只归一化，不新造语义**：合约内容必须能在 `Toolchain-01`（及 `ADR-0013`）中找到依据；`Toolchain-01` 未明处如实标 `UNSPECIFIED`，**不臆造**。
- **不复制大段正文**：以精确断言/字段/公式为主，规范叙述留在 `spec/Toolchain-01`；避免与生成投影 `contract-asm-list.md`（227 条指令表）重复——指令表引用生成投影，不重抄。
- **`check_spec_drift` 分类必须通过**（`make check` 成员，fail-closed）：`contract-asm.md` 须被归类为 `spec-sourced` **或** `adr-sourced`。当前 `check_spec_drift.py` 的 `SPEC_PREFIX_TO_COMPONENT`/`SPEC_PREFIX_TO_FILENAME`/README 版本表均**不含 `Toolchain-01`**，故 `> **版本：X.Y.Z**` + `[Toolchain-01 §…]` 路径**无法分类**。两条可行路径——**已定（2026-10-04 用户裁定）= (b)**：
  - **(a) ADR-sourced（未采用）**：来源头引用 `adr-0013-assembly-syntax.md`（Status: Accepted），正文规范断言标注 `[Toolchain-01 §x]`；不改 checker。
  - **(b) 扩展 checker（采用）**：为 v5 自定规范 `Toolchain-01` 增设显式映射（含 README 版本表项），使 spec-sourced 分类成立；须同步 `check_spec_drift.py` 与 README 版本表，并补对应反例门控。
  理由：`contract-asm.md` 的来源本就是 `Toolchain-01`（v5 自定规范），使 **spec-sourced** 分类成立更贴合 `Process-02`，对后续 v5 自定规范的合约亦可复用。`make check` 须 EXIT=0。
- **引用审计**：`contract-asm.md` 若被 `check_spec_refs.py` 覆盖，须使其 Check1/Check2 的**新增违规为 0**（历史 76 条不计；如落入排除名单需说明并与生成投影的排除规则一致，见 `lessons.md §5.1`）。
- 改动范围仅限：`.tao/knowledge/contract-asm.md`（新建）、`spec/README.md`、`spec/Process-02-合约编写规范.md`（+ 若选 (b) 则 `tools/infra/check_spec_drift.py`、`README.md`）。不改 `spec/Toolchain-01` 正文、不改 `contracts/`、`tests/`、`components/`。
- ADR 提醒：本任务属「归一化现有 spec」，**预期不立 ADR**；若发现需新增规范正文/外部契约（超出 `Toolchain-01` 明文），**停下并提醒用户**（`Process-03`）。

## 验收标准

1. `.tao/knowledge/contract-asm.md` 存在，覆盖 `Toolchain-01` §1–§13 全部章节（逐节可定位，含 §13 cfx 约定）。
2. 合约内每条规范性断言均带来源标注（`[Toolchain-01 §x]`，必要时并列上游/ADR）；无来源依据的新语义 = 0。
3. `spec/README.md` 投影表 ① 列 `Toolchain-01` 行 = `contract-asm.md`；「登记缺口」表中不再有 `contract-asm.md`。
4. `spec/Process-02` 合约清单 `contract-asm.md` 状态 = **现行**。
5. `python3 tools/infra/check_spec_drift.py` EXIT=0（`contract-asm.md` 被正确分类）且 `make check` **EXIT=0**。
6. `python3 tools/infra/check_spec_refs.py` 中 `contract-asm.md` 引入的新 Check1/Check2 违规 = 0。
7. **反例门控**：一键证据脚本须内置「注入反例→预期 FAIL→还原→预期回绿」自检（如删某节来源标注 → `check_spec_refs`/自检 FAIL；或把 `spec/README.md` 缺口行改回 → 自检 FAIL），并在完成区给出真实输出与退出码。

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
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
