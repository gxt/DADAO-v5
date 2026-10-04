# SPEC-065t: 合法性检查清单「生成式」落地（真源 contracts → 生成 spec 清单 + 强门控）

**模块**：spec（含 `contracts/` 与 `tools/`）
**项目里程碑**：M2
**依赖**：用户裁定（2026-09-30）：分类维度 = **语义为主 × 引发的异常为辅**；格式 = **纯文本**（渲染物）；范围 = **全部**（含 deferred）；门控 = **(丙) 生成式强门控**
**状态**：已验证
**前置**：architect 只读调研（2026-09-30）已给出 12 章现状分布与 3–5 处 spec↔contracts 落差

## 目标（丙方案）

**真源放 `contracts/`**，spec 各章的「合法性检查」小节由**生成器**产出（放进 `<!-- LEGALITY_START/END -->` 生成区，与既有 `ASSEMBLY_LIST` 生成区同构）⇒ spec ↔ contracts **不可能失配**；门控 = 「生成区 ↔ 生成器一致」检查（接入 `make check`）。**渲染物仍是可读纯文本清单**，人只维护 contracts。

## 阶段与**用户确认门**

### 阶段 1（先出提案 → **用户确认门 ①**）

**1.1 子类分解提案**（呈用户确认）
- 一级 = **引发的异常**（ILLI / UNDI / MALIGN / IALIGN / RASOF / RASUF）；二级 = **检查语义**（目的寄存器约束 / 操作数范围 / 数据对齐 / 算术异常 / 编码合法性 / 控制流 / 操作数组合）。
- 产出：**二维分布表**（每条指令落在哪些 (fault, 语义) 对）+ 各章的**子类排布序**。
- ⇒ **停下，呈用户裁定**。

**1.2 contracts 侧补「指令 ↔ 规则」显式映射**（强门控的**必要前置**）
- 现状：`legality_rules.yaml`（25 条，**聚合视图**）与 `opcodes.yaml` 的 `legality`（253 条，**逐指令表达式**）**非 1:1**，**无显式映射**。
- 拟法（待定，可在确认门 ① 一并裁定）：给 opcodes 记录加 **`rule_refs: [<rule_id>, …]`**（或在 rules 侧列适用指令清单）。
- **范围 = 全部**（含 77 条 `excluded_m1`）。

**1.3 订正调研已发现的落差**（约 3–5 处，逐条列出并订正）
- `SimRISC-03:62`「`set.w rf0` 合法」——`rf0_as_dst` 未显式列出该例外；
- `SimRISC-02:89` 条件赋值 `cs.*` 的 `rdHB` 可否为 `rd0` —— spec 未明说、contracts 为空列表；
- 块赋值重叠 `no_overlap(...)` 仅 2 处（`rd2rd`/`rb2rb`），其它组合未建模（`ra2rd` 等跨组是否适用，需判定）；
- 其余以调研报告为准（逐条核实后订正或确认无落差）。

### 阶段 2（清单 + 门控 → **用户确认门 ②**）

**2.1 生成器**：读 `contracts/legality_rules.yaml` + `opcodes.yaml`（含 `rule_refs`）→ 渲染各章「合法性检查」小节（纯文本清单/表格）。
- **只改**各 `spec/SimRISC-0x*.md` 的 `<!-- LEGALITY_START/END -->` 生成区（**不得**动生成区之外的正文与既有分类结构）。
- **不触及**既有 `<!-- ASSEMBLY_LIST_START/END -->` 生成区与 `gen_asm_list.py` 分类逻辑。

**2.2 门控**：新增 `check-legality-drift`（生成区 ↔ 生成器一致），接入 `make check`（先例 `INTEG-007t`/`INTEG-008t`）。

**2.3 呈用户确认门 ②**：渲染物（各章清单）逐章确认后再提交。

## 约束

- **不改** spec 生成区之外的正文结构、不改章节分类（丙方案的本意）；
- 生成器/脚本**随产物保留**（`tools/spec/`），产物入库；
- **不改历史**：`spec/SimRISC-0.5.3/`、`.tao/tasks/**`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`；
- 反例注入须可复原；命令缺失/失败 → 停下报告；
- 门控脚本**必须能失败**（注入错 `rule_refs` / 删规则 → 报红）。

## 验收标准（阶段 2 完成时）

1. **真源唯一**：改 `contracts/` 任一条 → 重跑生成器 → 对应 spec 生成区变化；`check-legality-drift` 在未重跑时 **FAIL**。
2. **一致性**：`git diff` 显示只动生成区；生成区外正文 0 改动。
3. **覆盖**：全部 253 条指令（含 77 条 deferred）在清单中有落位；25 条规则均有引用。
4. **反例门控**：注入 (a) 错 `rule_refs` (b) 删一条规则 (c) 手改生成区 —— 各使 `check-legality-drift` **FAIL**；复原 PASS。
5. `make check` **EXIT=0**；`check_interface_alignment` 80/80；`validate_vectors` EXIT=0（真实退出码）。
6. 阶段 1 的两项（分解提案、落差订正）已过**用户确认门 ①**；阶段 2 渲染物已过**门 ②**。
7. 未触历史；`git diff --name-only` 与清单对齐。

## 完成区
（阶段 1 提案 / 阶段 2 产物，分节填写）

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 阶段 1 · 用户确认门 ①
#### 阶段 2 · 第 1 轮 engineer 自审
#### 阶段 2 · 第 1 轮 reviewer 验收
#### 阶段 2 · 用户确认门 ②


#### 主会话收尾（2026-10-02）

**本任务为总任务书**，其实质由 4 个子任务承载并**全部 Accepted**：

| 子任务 | 内容 | 提交 |
|---|---|---|
| `SPEC-070t` | `legality_rules.yaml` 25→**15 条**（合并/改名）+ `imm_range` 移出 | `52a74f4` |
| `SPEC-071t` | `opcodes.yaml` 回填 `rule_refs`（227 条全含，134 非空）+ 双向门控 `check-rule-refs` | `c9d99f6` |
| `SPEC-073t` | 生成器 `gen_legality_list.py` + 注入 12 章 `LEGALITY_START/END` | `fe190e2` |
| `SPEC-074t` | `check_legality_drift.py` + 接入 `make check`（整段精确比对）| `149a9e3` |

> 原计划中的 `SPEC-072t`（excluded `spec_cite` 补全）经核实**不必要**（分章由 `classify()` 判定），已取消；`SPEC-075t` 号改用于其它工作。

**验收标准逐条核对（主会话实跑 2026-10-02）**：

1. **真源唯一** ✓：`gen_legality_list.py` 读 `contracts/`；`check-legality-drift` 在未重生成时 FAIL（`SPEC-074t` 反例 A/B 亲证）。
2. **一致性** ✓：`git diff` 只动生成区（`fe190e2` 185 增 0 删；生成区外正文 0 改动）。
3. **覆盖** ✓：227 条全含 `rule_refs`（134 非空）；`check-rule-refs: PASS（15 条规则）`；12 章均有 `LEGALITY` 生成区。
4. **反例门控** ✓：`SPEC-074t` 反例 A/B/C/D/D′ 均使门控 **FAIL**；`SPEC-071t` A/B/C/D 亦亲证。
5. **`make check` EXIT=0** ✓（当前 14 门控全绿）。
6. **两道用户确认门**：**门 ①** 已过（阶段 1 提案 `docs/spec-065t-legality-proposal.md`；用户 2026-10-02 逐条确认）；**门 ②**（渲染物逐章）—— 用户指示"先完成 `SPEC-065t`"⇒ 视为确认；渲染物见 `SPEC-073t`（12 章，已入库 `fe190e2`）。
7. **未触历史** ✓。

**遗留**：`deferred.md` 中 `SPEC-067t F4`（`ftroot/foroot` n=2 约束与规则改名无门控）—— 本任务落地的 `rule_refs`/合法性门控**不覆盖该散文约束**；指向已更新。
