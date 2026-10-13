# SPEC-089t: FP 合法性 `rule_refs` 回填 + `dst_rf0`/`encode_fp_root_n` 翻 `active` + FP rd-目的 `dst_rd0` 回填（(A) 15 条）+ 生成区重跑 + `decode: ILLI` 口径收口

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-086t`（`scope` 口径，已验证）、`SPEC-087t`（FP 语义合约，已验证）、`SPEC-088t`（FP 合法性规则归并，已验证）；**实现层前置**：`LLVM-029t`/`LLVM-030t`（FP 汇编/反汇编 + 汇编期合法性，已验证）、`QEMU-034t`–`QEMU-037t`（FP 执行层 60/60，已验证）。相关基线：`contracts/{opcodes,fp_semantics,legality_rules}.yaml`、`.tao/knowledge/contract-fp.md`、`spec/SimRISC-01/02/03/07`、`tools/spec/{generate_opcodes,gen_legality_list,check_scope,check_rule_refs,check_fp_contract}.py`、`tools/llvm/gen_asm_list.py`、`Makefile`。
**状态**：已验证

> 本任务书是**架构师规划产物**。§0 与 §8 的业务裁定已由用户于 **2026-10-04 最终确定**：R1 = 方案 B、R2 = 补 `rf2rd` 的 `dst_rd0`、R2b = **(A) 全补 15 条**、R5 = 采纳交叉断言、R6 = 随 R1 清理文案、**不立 ADR**。下发执行前仍须按 `AGENTS.md`「任务分解与执行确认」由用户确认任务书整体。
>
> **本任务只做 spec / contract / 生成器 / 门控层收口**：不改 `components/**`、不改 `tests/**`、不改 `tools/{llvm,qemu,testcases}` 中除 `gen_asm_list.py`（文案）外的脚本。R2b 采用 (A)（15 条 FP rd-目的指令全部补 `dst_rd0`）后，**LLVM/QEMU 目前不检 `dst_rd0@FP`** ⇒ 须**另立实现任务**（建议号 `LLVM-031t`、`QEMU-038t`，见 §10），本任务**不创建、不实现**。

---

## 0. 预置裁定（用户 2026-10-04 已逐条裁定；下发前仍须确认任务书整体）

1. **回填 FP `rule_refs`**：把 `contracts/opcodes.yaml` 中 `scope: fp` 60 条的 `legality` 空表回填为与其合法性一致的表达式，使 `rule_refs` 非空（见 §2.2/§2.3）。
2. **`dst_rf0` / `encode_fp_root_n` 由 `deferred` 翻 `active`**（现各 `deferred`，`legality_rules.yaml` L78 / L207）。共享 `mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 已 `active`，**不翻 status**。
3. **`scope != m1 ⇒ rule_refs=[]` 口径改为 `scope == excluded ⇒ rule_refs=[]`**（FP 与 M1 同口径解析 `rule_refs`；`excluded` 仍恒空，含 `fence`）。
4. **重跑生成区**：`gen_legality_list.py --apply`（`spec/SimRISC-01/02/03/07` 的 LEGALITY 区）与必要的 asm-list 投影（见 §2.6）；`check-legality-drift` 回绿。
5. **`decode: ILLI` 口径（R1，用户裁定 = 方案 B）**：`scope: fp` **不再携带 `decode`**（视同已实现）；**仅 `scope: excluded` 保留 `decode: ILLI`**。同步 `check_scope.py` 断言（`excluded ⇔ decode==ILLI`；`m1`/`fp` ⇒ 无 `decode`）与全部相关文案（`gen_asm_list`/LEGALITY 生成区/`contract-asm-list.md`/`spec/SimRISC-07` 头部等）。
6. **FP rd-目的指令的 `dst_rd0`（R2 + R2b，用户裁定 = 补 + (A) 全补 15 条）**：为 `rf2rd` 补 `dst_rd0`（R2）；并**全部补** FP 的 rd-目的指令（`convert_f2i` 8 + `classify` 2 + `compare` 4 + `rf2rd` 1 = **15 条**，R2b = (A)）。**非**最小只补 `rf2rd`。
7. **交叉断言（R5，用户裁定 = 采纳）**：`opcodes.yaml` 的 `rule_refs` ↔ `fp_semantics.yaml` 的 `legality_refs` **逐 id 交叉断言**（防双源漂移，见 §2.9）。
8. **文案清理（R6，用户裁定 = 随 R1 一并清理）**：`contract-asm-list.md`/`spec/SimRISC-07` 等 `decode ILLI`/「未实现」文案随 R1 清理（见 §2.6）。
9. **不立 ADR**（见 §7）；**不提交 git**；**不得触碰用户并发的归档改动**（`.tao/archive/**`、`docs/**`、`spec/**` 中与归档相关者、`.tao/knowledge/milestones.md`）。

---

## 1. 事实核实（本轮 architect 实测，file:line；执行时以重跑为准）

### 1.1 `contracts/opcodes.yaml`（227 条，实测）

- 分区：`scope: m1` **152**、`scope: fp` **60**、`scope: excluded` **15**，总计 **227**。
- FP 60 条现状：`legality: []` **60/60**、`rule_refs: []` **60/60**、`decode: ILLI` **60/60**。
- 全表 `rule_refs`：有引用指令 **135** 条、引用处数 **198**；`legality` 非空但 `rule_refs` 空仅 `fence_oiii_imm`（`scope: excluded`）。
- `rule_refs` 逐规则引用数：`dst_rd0` 104、`dst_rb0` 10、`dst_dual_same` 6、`dst_rd0_nonzero` 1、`encode_sbz` 9、`excp_malign` 24、`mreg_zero` 21、`mreg_range_overflow` 21、`mreg_range_overlap` 2（合计 198）。
- 头部注释（生成物）：`contracts/opcodes.yaml` L7「共 227 条…」、L8「有 rule_refs 的指令：135 条」。
- `decode: ILLI` 记录 **75** 条（fp 60 + excluded 15）；生成逻辑 `tools/spec/generate_opcodes.py` L202-203（`if scope != "m1": r["decode"] = "ILLI"`）。

### 1.2 `contracts/legality_rules.yaml`（16 条，实测）

- `dst_rf0`：L74–94，`status: deferred`（L78）；描述末句 L94「浮点类指令（RF）整体属 M1 范围外…」。
- `encode_fp_root_n`：L203–210，`status: deferred`（L207）；描述末句 L210「浮点类指令（RF）整体属 M1 范围外。」。
- `mreg_zero` L97、`mreg_range_overflow` L115、`mreg_range_overlap` L131：均 `active`。
- 头部注释 L20-21 仍写「M1 范围外（deferred）：RF 浮点（SimRISC-03 全部）…」。

### 1.3 生成器与门控（实测）

- `tools/spec/generate_opcodes.py`：
  - `rec()` L179–204：`scope != "m1"` 时写 `decode: ILLI`（L202-203）。
  - `EXPR_TO_RULE` L689–727：**无任何 FP 表达式映射**（缺 `rfhb/rfhc != rf0`、`immu6 == 2`、`rfha/rfhb/rfhc + immu6 <= 64`、`no_overlap(rfhb, rfhc, immu6)`）。
  - `_compute_rule_refs()` L729–751：L738 `if r.get("scope") != "m1" or not r.get("legality")` ⇒ `rule_refs=[]`。
  - 模块 docstring L4-10 写「`scope != "m1" ⇒ decode: ILLI`」「fp 尚未实现」。
  - 头部写出 L774–781（含 L781 `有 rule_refs …`）。
- `tools/spec/check_scope.py`：断言 3a L143-149（`scope != m1 ⇒ decode == ILLI`）、3b L151-157（`scope == m1 ⇒ 无 decode/旧字段`）；计数 L30-33（152/60/15/227）；docstring L7。
- `tools/spec/check_rule_refs.py`：Gate2 L79-90（`active` 须被引用或豁免）；豁免清单 L23-28（`excp_ialign/rasof/rasuf/undi` **不变**）。当前摘要（实测）：`规则 16 条: active 被引用 9, active 豁免 4, deferred 3; 指令引用 198 处`。
- `tools/spec/check_fp_contract.py`：`FP_RULES` L58（5 条）、`FP_RULE_EXACT` L63-69（dst_rf0 35 / encode_fp_root_n 2 / mreg_zero 28 / mreg_range_overflow 28 / mreg_range_overlap 4）、`FP_SPECIFIC_RULES` L73。均基于 `fp_semantics.yaml` 的 `legality_refs`，**不读 `opcodes.yaml` 的 `rule_refs`**。
- `tools/spec/gen_legality_list.py`：docstring L7 写「135 with rule_refs」；`RULE_SUMMARY` L72/L80 含「（deferred）」字样；`render_chapter_legality()` L136–224 会把**全部** `scope: fp` 条目列在 L212-216 的「**scope: fp（decode ILLI，未实现）**」注中（与规则 bullet 重复）；`SEMANTIC_MAP` L38-55 已含 5 条 FP 规则。
- `tools/spec/check_legality_drift.py`：调用同一 `render_chapter_legality` 做**整块逐字比较**（L143-166）。
- `tools/llvm/gen_asm_list.py`：`SECTION_BADGES` L196「**scope: fp（未实现，decode ILLI）** — 待浮点专门任务」；头部 L658「为 `scope: fp`（未实现，decode ILLI）」；L659 范围总账注。生成物 `.tao/knowledge/contract-asm-list.md`（L7/L171 含同款文案）与 `spec/SimRISC-07` 的 `<!-- ASSEMBLY_LIST_START/END -->` 内嵌标题（L11）均由此生成。
- `Makefile`：`check-legality-drift` L299、`check-scope` L315、`check-rule-refs` L320、`check-fp-contract` L325；四者均在 `check:` 链（L224）。

### 1.4 真源与现状（`fp_semantics.yaml` / `contract-fp.md`）

- `contracts/fp_semantics.yaml` 60 条 `legality_refs`（**已 `已验证`**，`SPEC-088t` 后）：`dst_rf0` 35、`encode_fp_root_n` 2、`mreg_zero` 28、`mreg_range_overflow` 28、`mreg_range_overlap` 4；无规则 9 条（`compare` 4 + `rf_mem` 单寄存器 4 + `set_w_rf` 1）。**注**：R2b (A) 后 `compare` 4 条补 `dst_rd0`，无规则降为 **5** 条（见 §2.7/§6）。
- `.tao/knowledge/contract-fp.md §15` L129–137：给出 FP 规则映射；**L137 明确**「FP 记录 `rule_refs` 为空（`opcodes.yaml`，遵守 `SPEC-086t` 口径）」——**本任务须重写此句**。
- `contract-fp.md §12` L111–116（rf_move）：`rd2rf`/`rf2rd` 只写 `mreg_zero`/`mreg_range_overflow`，**未写 `dst_rd0`**。
- `spec/SimRISC-02-寄存器复制.md` L80–88（§寄存器组之间块赋值「限制如下」）L84 明文「目的寄存器**不可为 `rd0`/`rb0`**…」；L73/L74 明列 `rf2rd`/`rd2rf`。生成表 L34–51 的 `dst_rd0` 仅 8 条（`cs.*-rd` 5 + `ra2rd` + `rb2rd` + `rd2rd`），**无 `rf2rd`**（因 `rf2rd` 现 `rule_refs=[]`）。
- `spec/SimRISC-07-浮点运算.md`：L4 正文「（44 条；未实现，decode ILLI）」；L8–60 ASSEMBLY_LIST 生成区（L11 标题文案）；L62+ LEGALITY 生成区（现仅「scope: fp…decode ILLI」清单，无规则 bullet）。

### 1.5 基线（本轮实测）

```
check-scope: PASS（152/60/15/227）
check-rule-refs: PASS (规则 16 条: active 被引用 9, active 豁免 4, deferred 3; 指令引用 198 处)
check-fp-contract: PASS（FP 规则 35/2/28/28/4）
check-legality-drift: 12 chapters OK
```

### 1.6 与实现的差异（**重要，见 §8 R2/R2b**）

- `components/qemu/patches/.../trans_fp.c.inc.patch` L38 注释与 `trans_rf2rd_orri_rf`（L440-457）**不检查** `rf2rd` 目的 `rd0`（仅 `fp_check_mreg`）；`trans_rd2rf_orri_rf`（L422-439）明注 rf0 目的合法。FP 的 `convert_f2i`/`classify`/`compare` 目的均为 rd，实现亦**不检** `dst_rd0@FP`（即 R2b (A) 涉及的 **15 条全部无检查**）。
- `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch` L985–1070 仅对块赋值做 `mreg_range_overlap` + 组计数一致性硬报错（L1022），**不检查** FP rd-目的指令的 `dest == rd0`。
- ⇒ R2b 采用 (A)（补全 15 条）后，**合约 / 生成物 / 门控**在本任务落地；**LLVM/QEMU 实现缺口须另立任务**（§10：建议 `LLVM-031t`、`QEMU-038t`），本任务**不触组件、不实现**。

---

## 2. 设计（逐项改动清单，file:line）

> 所有改动以 §0 裁定为准；若用户改判，须全链同步（下方括注受影响文件）。

### 2.1 `tools/spec/generate_opcodes.py` — `_compute_rule_refs` 口径调整（§0.3）

- L738 条件由 `if r.get("scope") != "m1" or not r.get("legality")` 改为
  `if r.get("scope") == "excluded" or not r.get("legality")`（`scope: fp` 与 `m1` 同解析）。
- L730–735 docstring 同步：「`scope == "excluded"` ⇒ `rule_refs: []`；`m1`/`fp` 按 `EXPR_TO_RULE` 映射」。
- 模块 docstring L9 同步（`scope != "m1" ⇒ decode: ILLI` 的措辞随 §2.5 调整）。
- **影响**：`fence_oiii_imm`（`excluded`）仍 `rule_refs=[]`（其 SBZ 表达式不被引用，符合预期）。

### 2.2 `tools/spec/generate_opcodes.py` — `EXPR_TO_RULE` 扩 FP 表达式（§0.1/§0.5）

在 L689–727 增加（**字符串须与 `legality` 逐字一致**；来源 `.tao/knowledge/contract-fp.md §15` + `fp_semantics.yaml`）：

| 新增表达式（`legality`） | → rule id |
|---|---|
| `rfhb != rf0` | `dst_rf0` |
| `rfhc != rf0` | `dst_rf0` |
| `immu6 == 2` | `encode_fp_root_n` |
| `rfha + immu6 <= 64` | `mreg_range_overflow` |
| `rfhb + immu6 <= 64` | `mreg_range_overflow` |
| `rfhc + immu6 <= 64` | `mreg_range_overflow` |
| `no_overlap(rfhb, rfhc, immu6)` | `mreg_range_overlap` |

（`immu6 != 0`、`rdhb + immu6 <= 64`、`rdhc + immu6 <= 64`、`rdhb != rd0` 已在映射表中。）

### 2.3 `tools/spec/generate_opcodes.py` — FP 各 `rec()` 回填 `legality`（§0.1/§0.6）

按 `fp_semantics.yaml` 的 `legality_refs` **逐条派生**（目的：`_compute_rule_refs` 结果 == `fp_semantics.legality_refs`）。逐族表达式（字段名取自各 `rec()` 的 `fields`，已核对）：

| 族 / 位置 | 数量 | `legality` 表达式 |
|---|---|---|
| `convert_ff`（MISC-RF orri 0x01/0x02/0x09/0x0A，`generate_opcodes.py` L636-663） | 4 | `rfhb != rf0`、`immu6 != 0`、`rfhb + immu6 <= 64`、`rfhc + immu6 <= 64`、`no_overlap(rfhb, rfhc, immu6)` |
| `convert_i2f`（orri 0x34-0x37/0x3C-0x3F） | 8 | `rfhb != rf0`、`immu6 != 0`、`rfhb + immu6 <= 64`、`rdhc + immu6 <= 64` |
| `convert_f2i`（orri 0x30-0x33/0x38-0x3B） | 8 | `rdhb != rd0`、`immu6 != 0`、`rdhb + immu6 <= 64`、`rfhc + immu6 <= 64` |
| `arith`（orrr 0x10-0x1D） | 12 | `rfhb != rf0` |
| `sign`（orrr 0x16/0x17/0x1E/0x1F） | 4 | `rfhb != rf0` |
| `root`（orri 0x06/0x0E） | 2 | `rfhb != rf0`、`immu6 == 2` |
| `classify`（orri 0x00/0x08） | 2 | `rdhb != rd0`、`immu6 != 0`、`rdhb + immu6 <= 64`、`rfhc + immu6 <= 64` |
| `compare`（orrr 0x20/0x21/0x28/0x29） | 4 | `rdhb != rd0` |
| `cs_rf`（L416-423 `cs.eq/ne`，L430-449 `cs.n/z/p`） | 5 | `cs.eq/ne`：`rfhc != rf0`；`cs.n/z/p`：`rfhb != rf0` |
| `rf_mem` 多寄存器（L330-335 `ldm.t/stm.t`；L369-374 `ldm.o/stm.o`） | 4 | `immu6 != 0`、`rfha + immu6 <= 64` |
| `rf_mem` 单寄存器（L279-283/L314-318） | 4 | （空，无规则） |
| `rf_move`：`rd2rf`（L579-580） | 1 | `immu6 != 0`、`rfhb + immu6 <= 64`、`rdhc + immu6 <= 64` |
| `rf_move`：`rf2rd`（L581-582） | 1 | `rdhb != rd0`、`immu6 != 0`、`rdhb + immu6 <= 64`、`rfhc + immu6 <= 64` |
| `set_w_rf`（L391-392） | 1 | （空，无规则） |

> **注**：`arith`/`sign` 的 orrr 无 `immu6`（单寄存器），故仅 `dst_rf0`；`compare`/`classify`/`convert_f2i` 目的为 rd，`mreg_range_overflow` 只查其**源/目的起始寄存器**（`rdhb`/`rfhc`）。`immu6` 语义在 `root` 为 `n`（不入 `mreg_*`）。

> **(A) 新增 `dst_rd0` 的 15 条 FP rd-目的指令（逐条，见 §8 R2b）**：本表 4 个族（`convert_f2i` 8 + `compare` 4 + `classify` 2 + `rf2rd` 1）的 `legality` 各追加表达式 `rdhb != rd0`（已在 `EXPR_TO_RULE` L692 映射为 `dst_rd0`，**字符串逐字一致**）。逐条 id：
> - `convert_f2i`（orri，目的 `rdhb`）：`ft2it_orri_rf`、`ft2io_orri_rf`、`ft2ut_orri_rf`、`ft2uo_orri_rf`、`fo2it_orri_rf`、`fo2io_orri_rf`、`fo2ut_orri_rf`、`fo2uo_orri_rf`；
> - `classify`（orri，目的 `rdhb`）：`ftcls_orri_rf`、`focls_orri_rf`；
> - `compare`（orrr，目的 `rdhb`）：`ftqcmp_orrr_rf`、`ftscmp_orrr_rf`、`foqcmp_orrr_rf`、`foscmp_orrr_rf`；
> - `rf_move`（orri，目的 `rdhb`）：`rf2rd_orri_rf`。
>
> **归属核对**：`dst_rd0` 规则描述（`legality_rules.yaml` L38）称适用于 `orrr`（单目的 `rdhb`）与 `orri` 目的字段，并特例点名 `ra2rd` 的目的 `rdhb`；上述 15 条中 `compare` 属 `orrr` 单目的 `rdhb`，`convert_f2i`/`classify`/`rf2rd` 属 `orri` 目的字段 `rdhb`，与 `fp_semantics.yaml`/`contract-fp.md` 的族划分一致（`convert_f2i`/`compare`/`classify` 目的为 rd 组、`rf2rd` 目的为 rd 组；`rd2rf` 目的为 rf 组不适用）。故须同步扩写该规则描述以显式覆盖这 15 条（§2.4）。

### 2.4 `contracts/legality_rules.yaml`（§0.2/§0.6）

- `dst_rf0` L78 `status: deferred` → `active`；描述 L94 末句「浮点类指令（RF）整体属 M1 范围外…」改为「FP 已实现（`LLVM-029t/030t`、`QEMU-034t`–`037t`）；本规则 `active`，由 `scope: fp` 记录的 `rule_refs` 覆盖（35 条）」。
- `encode_fp_root_n` L207 `status: deferred` → `active`；描述 L210 同类改「…（2 条）」。
- L20-21 头部注释「M1 范围外（deferred）：RF 浮点…」同步为「LR-SC 原子（SimRISC-12）、特权 cfx（SimRISC-04）；RF 浮点已实现（`scope: fp`，60 条）」。
- `dst_rd0`（L26–40，`active`）**适用范围描述同步扩写**：现描述「适用于 `orrr`（单目的 `rdhb`）、`orri/rrii/riii/rwii`（目的字段 `rdha/rbha`）…`ra2rd` 的目的字段 `rdhb`…」须**显式覆盖** (A) 的 15 条 FP rd-目的指令——`orri` 目的字段 `rdhb`（`convert_f2i` 8、`classify` 2、`rf2rd` 1）与 `orrr` 单目的 `rdhb`（`compare` 4）。否则 (A) 引入的 `dst_rd0@FP` 引用在本规则描述中无对应适用语句（规则描述与 `rule_refs` 自相矛盾）。
- **不新增/不删除规则**（仍 16 条）；`dst_rd0` 已 `active`，**不改 status**。

### 2.5 `contracts/opcodes.yaml`（生成物，重跑 `generate_opcodes.py`）

- FP 60 条回填 `legality` + `rule_refs`（§2.1/§2.3）。
- 头部注释 L5-8：随 §2.1/§2.5(decode) 文案与计数自动更新（L8「有 rule_refs …」）。
- （R1 = 方案 B）FP 60 条去掉 `decode: ILLI`；仅 `excluded` 15 条保留。
- **编码/`mask`/`value`/`scope` 零改动**（`validate-encoding` 应保持 PASS）。

### 2.6 生成物重跑

- `tools/spec/gen_legality_list.py`：
  - L7 docstring「135 with rule_refs」→「**190** with rule_refs」（(A) 口径，§6 实测）。
  - L72/L80：`dst_rf0`/`encode_fp_root_n` 摘要去「（deferred）」。
  - L212-216：`fp_entries` 改为**仅列无 `rule_refs` 的 fp 条目**（已被规则 bullet 覆盖者不再重复列）。(A) 口径下无规则 fp 条目仅 **5 条**（`ld.t`/`st.t`/`ld.o`/`st.o` 4 条 + `set.w` 1 条；ch07 的 44 条与 ch02 的 7 条 fp 条目全部有规则 ⇒ 该两章无 fp 条目注）；文案由「**scope: fp（decode ILLI，未实现）**」改为「**scope: fp（无附加合法性规则）**」（R1 = 方案 B）；`excluded` 注（L217-221）保留「（decode ILLI）」。
  - `--apply` 重写 `spec/SimRISC-01/02/03/07` 的 LEGALITY 区（4 章内容变化；04/05/06/08/09/10/11/12 不涉及 fp、内容不变）。
- `tools/llvm/gen_asm_list.py`（**R1 = 方案 B**）：L196 `SECTION_BADGES["浮点运算"]` 去「（未实现，decode ILLI）」；L658/L659 文案同步。重跑生成 `.tao/knowledge/contract-asm-list.md` 与 `spec/SimRISC-07` 的 `<!-- ASSEMBLY_LIST_START/END -->` 内嵌标题（`--embed-spec`）。**不改** 44/60 等计数（R1 不改 `scope`）。
- `spec/SimRISC-07-浮点运算.md` L4 正文「（44 条；未实现，decode ILLI）」→「（44 条，已实现）」（**正文行**，R1 裁定；不改 markers 内生成区以外的其它正文）。
- **不改**：`spec/SimRISC-0.5.3/**`、历史任务书、`adr-*`、`components/**`、`tests/**`。

### 2.7 `contracts/fp_semantics.yaml` 与 `contract-fp.md`

- `fp_semantics.yaml`（**R2b = (A)**）：为 FP 的 rd-目的 **15 条** `legality_refs` 追加 `dst_rd0`：
  - `convert_f2i` 8（`ft2it_orri_rf`/`ft2io_orri_rf`/`ft2ut_orri_rf`/`ft2uo_orri_rf`/`fo2it_orri_rf`/`fo2io_orri_rf`/`fo2ut_orri_rf`/`fo2uo_orri_rf`，L136-175）；
  - `classify` 2（`ftcls_orri_rf`/`focls_orri_rf`，L338-347）；
  - `compare` 4（`ftqcmp_orrr_rf`/`ftscmp_orrr_rf`/`foqcmp_orrr_rf`/`foscmp_orrr_rf`，L316-335）；
  - `rf_move` / `rf2rd` 1（`rf2rd_orri_rf`，L424-428）。
  其余 45 条 `legality_refs` **不变**（60 条 id 集合、12 族划分均不变）。
- `contract-fp.md §15` L137：删「FP 记录 `rule_refs` 为空（遵守 `SPEC-086t` 口径）」，改为「FP 记录 `rule_refs` 由 `opcodes.yaml` 回填，须与 `fp_semantics.yaml` 的 `legality_refs` 逐 id 一致；`dst_rf0`/`encode_fp_root_n` 已 `active`；FP rd-目的 15 条另受 `dst_rd0` 约束」。
- `contract-fp.md §3/§8/§12`（(A) 相关的族文案）：
  - §3 `convert_f2i`（L45）「目的为 rd 组（非 rf），不受 rf0 目的约束」→ 补「但受 `dst_rd0` 约束（目的 `rdHB` 为 `rd0` → ILLI）」；
  - §8 `compare`（L87）同类补 `dst_rd0` 语句；§9 `classify` 目的 `rdHB`（L91 起）补同类语句；
  - §12 `rf_move`（L111-116）补「`rf2rd` 目的 `rdHB` 为 `rd0` → ILLI；`rd2rf` 目的为 rf（`rf0` 合法）」，并明确 §12 中「源 `rf0` 合法」与「目的 `rd0` 非法」是两条不同约束。
- `contract-fp.md §15` 的规则映射处为 `dst_rd0` 增列 FP 15 条（与 `dst_rf0` 的「rf 仅作源」区分：`dst_rd0` 作用于 rd-目的字段 `rdhb`，`dst_rf0` 作用于 rf-目的字段 `rfhb`）。
- **不改**：`contract-fp.md` 其它 `[SimRISC-]` 引用结构（`check-spec-drift` 审计 `contract-fp.md`，须保持版本头与引用合规）。

### 2.8 门控同步

- `tools/spec/check_scope.py`（**R1 = 方案 B**）：断言 3a/3b 改为「`scope == excluded` ⇔ `decode == ILLI`；`scope ∈ {m1, fp} ⇒ 无 decode`」；docstring L7 同步。计数 L30-33 **不变**（152/60/15/227）。
- `tools/spec/check_rule_refs.py`：**代码不变**（豁免清单 `excp_ialign/rasof/rasuf/undi` 不变）；摘要随数据变化（active 被引用 9→**11**；指令引用 198→**310**）。
- `tools/spec/check_fp_contract.py`：`FP_SPECIFIC_RULES` 不变（`dst_rd0` 为共享规则，**不得**列入）；`FP_RULES` **追加** `dst_rd0`、`FP_RULE_EXACT` **追加** `dst_rd0: 15`（FP 侧新增计数断言，防漏填 (A) 的任一条）；**新增 Check 8 交叉断言**（§2.9）。
- `Makefile`：target 不变（`check-legality-drift`/`check-scope`/`check-rule-refs`/`check-fp-contract` 已在线）。

### 2.9 `opcodes.yaml` ↔ `fp_semantics.yaml` 的 FP 规则交叉断言（**R5 采纳**，新增 Check 8）

在 `tools/spec/check_fp_contract.py` **新增 Check 8**：对每个 `scope: fp` 的 opcodes 记录，其 `rule_refs` 集合须 **==** `fp_semantics.yaml` 同 `id` 的 `legality_refs` 集合（排序后比较；逐 id 打印缺失/多出项，任一差异 ⇒ 非零退出）。理由：`legality` 表达式（opcodes）与 `legality_refs`（fp_semantics）是同一事实的两次登记，须机械防漂移。**该断言是本任务「判出漏填任一条（含 (A) 的 15 条）」的关键门控**；详见 §5 反例 (b)/(f)/(g)。

---

## 3. 接口规范（自包含）

### 输入
- `contracts/{opcodes,fp_semantics,legality_rules}.yaml`
- `.tao/knowledge/contract-fp.md`、`spec/SimRISC-01/02/03/07`、`spec/SimRISC-02 §寄存器组之间块赋值`
- `tools/spec/{generate_opcodes,gen_legality_list,check_scope,check_rule_refs,check_fp_contract}.py`、`tools/llvm/gen_asm_list.py`、`Makefile`
- 本任务书 §0 用户裁定

### 输出
- 见 §2 改动清单；`opcodes.yaml`/`contract-asm-list.md`/LEGALITY 区为**重生成**产物；另有**手工改动**：`fp_semantics.yaml`、`legality_rules.yaml`、`contract-fp.md`、`spec/SimRISC-07` L4 正文。

### 约束
- 中文；**不提交 git**；**不创建 ADR**；**不改** `components/**`、`tests/**`、`spec/SimRISC-0.5.3/**`、历史任务书、`adr-*`。
- **范围边界（R2b (A) 尤其注意）**：本任务**只落合约 / 生成物 / 门控**——**不含 LLVM/QEMU 实现**（15 条 `dst_rd0@FP` 的汇编期/运行期检查另立任务，见 §10）、**不含向量/oracle**、**不含 `spec/` 正文的语义改写**（仅随 R1/R6 清理 `decode ILLI`/「未实现」文案与 §2.7 列出的合约投影句）。
- **不得触碰用户并发的归档改动**：`.tao/archive/**`、`docs/**`、`spec/**` 中与归档相关者、`.tao/knowledge/milestones.md` **一律不动**。
- **Spec-first**：FP `legality` 真源 = `contract-fp.md §15` + `fp_semantics.yaml`；`dst_rd0` 归属判据 = `legality_rules.yaml` L26–40 + `SimRISC-02 §寄存器组之间块赋值` 通则；不得从 LLVM/QEMU 反推。
- **生成器随产物保留**：若新增脚本，落 `tools/spec/`（入库）或 `.work/`（不入库者不得只放 `/tmp`）。
- 临时目录 `/tmp/opencode/SPEC-089t/`；日志 `.work/log/spec/SPEC-089t-*.log`；证据脚本 `.work/evidence/SPEC-089t/run.sh`。

---

## 4. 执行环境
**执行环境**：本地

---

## 5. 验收标准（可执行、可失败，含反例注入）

> 通用：完成区贴**真实命令输出与退出码**；被检命令自身退出码须显式捕获（`cmd > log 2>&1; rc=$?`，**禁** `cmd | tee log` 后取 `$?`）；复杂命令留 `.work/log/spec/SPEC-089t-*.log`；engineer 交付一键证据脚本 `.work/evidence/SPEC-089t/run.sh`（非交互、任一失败即非零退出、逐项打印「检查名 + 期望/实际 + 退出码」、内置「注入反例→预期 FAIL→还原→回绿」自检或 `--inject`）。

1. **FP `rule_refs` 回填（R2b = (A)）**：`opcodes.yaml` 中 `scope: fp` 有 `rule_refs` 的条目 = **55**（60 − 5 条无规则：`ld.t`/`st.t`/`ld.o`/`st.o` 4 + `set.w` 1）；全表有引用指令 = **190**；引用处数 = **310**。逐规则 FP 引用数：`dst_rf0` 35、`encode_fp_root_n` 2、`mreg_zero` 28、`mreg_range_overflow` 28、`mreg_range_overlap` 4、`dst_rd0` **15**。
2. **规则翻 `active`**：`legality_rules.yaml` 仍 **16** 条；`active` **15** / `deferred` **1**（仅 `encode_cfx`）；`check-rule-refs` EXIT 0 且摘要 `active 被引用 11, active 豁免 4, deferred 1`（指令引用 **310**，防「翻 active 后孤儿」）。
3. **交叉一致性**（§2.9，R5 采纳）：`check-fp-contract` 新增 **Check 8 PASS**；`opcodes.yaml` 中 FP 记录的 `rule_refs` 与 `fp_semantics.yaml` `legality_refs` **逐 id 相等**（含 `dst_rd0` 15 条）；`check_fp_contract` 的 `dst_rd0` 计数断言 = **15**（`FP_RULES`/`FP_RULE_EXACT` 追加项，`FP_SPECIFIC_RULES` 不含 `dst_rd0`）。
4. **生成区回绿**：`make check-legality-drift` → `12 chapters OK`（**此为权威门控**；`gen_legality_list.py --verify` 仅打印 OK/MISMATCH 且**恒退出 0**，不得单独作为证据）；`spec/SimRISC-01/02/03/07` 的 LEGALITY **生成区**变更仅这 4 章（`git diff` 的 LEGALITY 区限于这 4 章；全库 diff 另见验收 8）。
5. **`decode` 口径（R1 = 方案 B）**：`opcodes.yaml` 中 `scope: fp` 含 `decode` 的条目 = **0**；`scope: excluded` 含 `decode: ILLI` = **15**；`make check-scope` PASS 且断言「`excluded` ⇔ `decode == ILLI`；`m1`/`fp` ⇒ 无 decode」；`grep -c "decode: ILLI"` = 15（+注释）；`gen_asm_list`/LEGALITY/`contract-asm-list.md`/`SimRISC-07` 中「未实现，decode ILLI」对 fp 的表述 **0 命中**。
6. **FP rd-目的 `dst_rd0` 落地（R2 + R2b = (A)，15 条）**：
   - `opcodes.yaml` 中 **15 条** FP rd-目的记录（`convert_f2i` 8 + `classify` 2 + `compare` 4 + `rf2rd` 1，逐条 id 见 §2.3）的 `rule_refs` 均含 `dst_rd0`；
   - `fp_semantics.yaml` 同 **15** id 的 `legality_refs` 均含 `dst_rd0`；
   - `spec/SimRISC-02` 生成表 `dst_rd0` 由 8 条变 **9 条**（含 `rf2rd_orri_rf`；其余 14 条在 ch07 的 LEGALITY 区）；
   - `contract-fp.md §3/§8/§12/§15` 同步（§2.7）；`legality_rules.yaml` 的 `dst_rd0` 描述扩写覆盖 15 条（§2.4）；
   - 登记 LLVM/QEMU 后续实现任务（§10：建议 `LLVM-031t`、`QEMU-038t`；**本任务不创建、不实现**）。
7. **计数不变项**：M1 **152** / 总 **227** / scope 分区 **152·60·15** / lit **26** / patches **67** / interface **80**；`validate-encoding` PASS；`validate-vectors 152/152`；`check-spec-drift` 4 合约。（与变化项对照见 §6。）
8. **残留与越界**：`git status --untracked-files=all` 干净（除应改文件 + 本任务书 + `.work/`）；`check-no-residue` PASS；`git diff --name-only` 与 §2 清单对齐（`components/**`、`tests/**` **不在 diff**；**不含 LLVM/QEMU 实现、不含向量/oracle**）；**未触碰** `.tao/archive/**`、`docs/**`、`spec/**` 中与归档相关者、`.tao/knowledge/milestones.md`。
9. **`make check` 全绿**：`repository checks: PASS`，EXIT=0。

### 5.1 反例注入（逐条须真实 FAIL→还原→回绿，`git diff --name-only` 非空 + blob 校验）

- (a) `_compute_rule_refs` 条件改回 `scope != "m1" ⇒ []`（或删 `EXPR_TO_RULE` 的 `rfhb != rf0`）⇒ 重生成后 `check-rule-refs` **Gate2 FAIL**（`dst_rf0`/`encode_fp_root_n` 孤儿）。
- (b) 删某条有规则 FP 记录的一条 `legality` 表达式（如 `convert_ff` 的 `no_overlap(rfhb, rfhc, immu6)`，或 (A) 之一的 `rdhb != rd0`）⇒ **§2.9 Check 8 交叉断言 FAIL**（`opcodes.rule_refs` ≠ `fp_semantics.legality_refs`）；未重跑生成区时另见 `check-legality-drift` FAIL。
- (c) 把 `dst_rf0` 改回 `deferred` 但保留 FP 引用 ⇒ 至少一条断言 FAIL（`check-rule-refs` Gate2 / 规则计数）。
- (d) （R1 = 方案 B）给任一 `scope: fp` 记录注入 `decode: ILLI` ⇒ `check-scope` FAIL。
- (e) 手动改 `spec/SimRISC-07` LEGALITY 区一行（不重跑生成器）⇒ `check-legality-drift` FAIL。
- (f) **（R2b (A)）** 从一条 FP rd-目的记录（逐一覆盖 4 族至少各一：`ft2it_orri_rf`、`ftcls_orri_rf`、`ftqcmp_orrr_rf`、`rf2rd_orri_rf`）删 `dst_rd0` 引用 ⇒ **Check 8 交叉断言 FAIL** 且 `check_fp_contract` 的 `dst_rd0` 计数由 **15 变 14** FAIL；对 `rf2rd` 另致 `spec/SimRISC-02` 生成表 `dst_rd0` 9→8（未重跑则 drift FAIL）。
- (g) **（(A) 鉴别力）** 只回填 14 条（漏 `compare` 4 中的一条，或漏 `rf2rd`）⇒ Check 8 / `dst_rd0` 计数 FAIL——证明「全补 15」被机械判定，而非靠人工目视。
- **空注入防护**：每次注入后 `git diff --name-only` 非空 / `git hash-object` 变化；还原须复原原文（源码还原后**重建生成物**）并复核 blob 一致。

---

## 6. 计数影响（改前 → 改后）

> 口径 = **R1 方案 B + R2b (A)**（用户 2026-10-04 裁定）。以下为**实测推算**值（§6.1 给出验证方法）。

| 项 | 改前 | 改后 | 说明 |
|---|---|---|---|
| 规则总数 | 16 | **16** | 不增删 |
| active / deferred | 13 / 3 | **15 / 1** | 翻 `dst_rf0`/`encode_fp_root_n`；`encode_cfx` 仍 deferred |
| active 被引用 / 豁免 | 9 / 4 | **11 / 4** | 两条 FP 专属规则被 FP 引用 |
| `指令引用` 处数 | 198 | **310** | +112 = FP 97（`dst_rf0` 35 + `encode_fp_root_n` 2 + `mreg_zero` 28 + `mreg_range_overflow` 28 + `mreg_range_overlap` 4）+ `dst_rd0@FP` 15 |
| `dst_rd0` 引用数 | 104 | **119** | +15（(A) FP rd-目的） |
| 有 `rule_refs` 指令数 | 135 | **190** | +55（FP：60 − 5 条无规则） |
| `scope: fp` 有 `rule_refs` | 0 | **55** | 回填 + (A) |
| FP 无规则条目 | 9（`compare` 4 + `rf_mem` 单寄存器 4 + `set.w` 1） | **5**（`rf_mem` 单寄存器 4 + `set.w` 1） | (A) 使 `compare` 4 条有 `dst_rd0` |
| M1 / 总 / scope 分区 | 152 / 227 / 152·60·15 | **不变** | 不触编码 |
| `decode: ILLI` 记录数 | 75（fp 60 + excluded 15） | **15**（仅 excluded） | R1 = 方案 B |
| `check-legality-drift` | 12 OK | **12 OK**（01/02/03/07 内容变） | 重跑生成区 |
| lit / patches / interface / validate-vectors | 26 / 67 / 80 / 152 | **不变** | 不触组件/向量 |
| `contract-asm-list.md` | 含「fp 未实现」 | **随 R1（方案 B）重生成** | 生成物 |

**改后逐规则 `rule_refs` 引用数（实测，§6.1）**：`dst_rd0` **119**、`excp_malign` 24、`dst_rb0` 10、`mreg_zero` **49**、`mreg_range_overflow` **49**、`dst_dual_same` 6、`dst_rf0` **35**、`dst_rd0_nonzero` 1、`mreg_range_overlap` **6**、`encode_sbz` 9、`encode_fp_root_n` **2**（合计 **310**）。

### 6.1 计数验证方法（可复现）

1. **实测脚本**（engineer 须在证据脚本内复算并打印，不信任本文数字）：读 `contracts/opcodes.yaml` + `contracts/fp_semantics.yaml`，对每条 `scope: fp` 记录以 `fp_semantics` 同 id 的 `legality_refs`（(A) 15 条另并 `dst_rd0`）为期望 `rule_refs`，去重保序后统计：`有引用指令数`、`总引用处数`、`逐规则引用数`。
2. **交叉核对**：与重跑后的 `opcodes.yaml` 头部注释（`generate_opcodes.py` L781「有 rule_refs 的指令：190 条」）一致；与 `check-rule-refs` 摘要「指令引用 310 处」「active 被引用 11」一致；与 `check_fp_contract` 的 `dst_rd0` 计数 15 一致。
3. **权威来源**：`opcodes.yaml` 为生成物（重跑 `generate_opcodes.py`），故实现后以**重跑产物**为准；本表为 architect 规划期实测推算（读当前 `opcodes.yaml` 135/198 + `fp_semantics` 97 + (A) 15 = 310）。

---

## 7. ADR 判断（须主动提醒）

- **判据核对**（`spec/Process-03-ADR编写规范.md`：高代价 / 跨模块 / 多方案 / 外部契约 / 结论固化 / 定位）：
  - **回填 `rule_refs` + 翻 `active`**：机械落地 `SPEC-087t`/`SPEC-088t` 已定事实，**非新决策**。
  - **`decode: ILLI` 口径修订（§8 R1）**：**唯一候选**——它重定义 `opcodes.yaml` 字段语义并跨 `contracts/`+`spec/`+多个门控（`check-scope`/`gen_asm_list`/`gen_legality_list`），符合「跨模块 + 结论固化」。但它是「FP 由未实现转已实现」的**自然推论**，而非新方向；`SPEC-086t` 的 `scope` 口径已覆盖 FP 定位。
  - **`rf2rd` 的 `dst_rd0`（§8 R2）**：spec 内部条款间的一致性调和，属既有规则框架内的裁定，非新架构决策。
- **用户裁定：不立 ADR（2026-10-04）**——与用户此前对 FP 各项「不立 ADR」一致；把裁定结论与理由写入本任务书 + `contract-fp.md`（结论固化于合约层）。
- 判据复核结论：`decode` 字段语义修订（R1）虽具「跨模块 + 结论固化」色彩，但其为「FP 由未实现转已实现」的**自然推论**（`SPEC-086t` 的 `scope` 口径已覆盖 FP 定位）；`dst_rd0@FP`（R2b）为既有规则框架内的**条款一致性调和**。二者均**不构成新架构决策**，故**不立 ADR**。

---

## 8. 风险与裁定（用户 2026-10-04 已裁决；下表为裁决记录）

| # | 风险/开放问题 | 影响 | 建议 |
|---|---|---|---|
| **R1** | **`decode: ILLI` 口径**：FP 已实现（`LLVM-029t/030t`、`QEMU-034t`–`037t` 均 `已验证`），但 `opcodes.yaml` 60 条 fp 仍标 `decode: ILLI`，`check-scope` 断言 `scope != m1 ⇒ decode ILLI`，且 `gen_asm_list`/LEGALITY/`contract-asm-list.md`/`SimRISC-07` L4 处含「未实现，decode ILLI」 | 语义失真、跨模块文案过时 | **用户裁定 = 方案 B（2026-10-04）**：fp 视同 m1，**不携带 `decode`**；仅 `excluded` 保留 `decode: ILLI`；同步 `check_scope`（改为 `excluded ⇔ decode ILLI`、`m1/fp ⇒ 无 decode`）+ 四处文案（§2.5/§2.6）。**方案 A 已否决** |
| **R2** | **`rf2rd` 目的 `rd0` 不一致**：`SimRISC-02 §寄存器组之间块赋值` L84 通则「目的不可为 rd0/rb0」，`rf2rd`（L73）在该节内；但 `contract-fp.md §12`/`fp_semantics.yaml`/生成表均未列 `dst_rd0`；实现（QEMU `trans_rf2rd` / LLVM 块赋值检查）亦不检 | 合约↔spec↔实现三方不一致；补则生实现缺口 | **用户裁定 = 补 `dst_rd0`（2026-10-04）**（Spec-first：通则明文覆盖 `rf2rd`）。落地：改 §2.3/§2.7 `legality` + `fp_semantics` + `contract-fp §12/§15`；**另立** LLVM/QEMU 实现任务（§10，本任务不触组件）。「豁免 rf_move」已否决 |
| **R2b** | **`dst_rd0` 对 FP 全部 rd-目的指令的适用范围（本轮新发现）**：`dst_rd0` 规则描述（`legality_rules.yaml` L26–40）称覆盖 `orrr`（单目的 `rdhb`）与 `orri` 目的字段，据此 **`convert_f2i` 8 + `classify` 2 + `compare` 4 + `rf2rd` 1 = 15 条** FP rd-目的指令都应受 `dst_rd0` 约束；但 `fp_semantics`/`contract-fp §15` 对**全部 15 条**均未列 `dst_rd0`（不止 `rf2rd`）。`deferred.md` L60 只点了 `rf2rd` | 若只补 `rf2rd`，`convert_f2i`/`classify`/`compare` 仍不自洽；补全 15 条（选 A）后计数为 **有引用指令 190、引用处数 310**，实现缺口扩大到 LLVM+QEMU 共 3 类指令 | **用户裁定 = (A) 全补 15 条（2026-10-04）**：严格 Spec-first 补全 15 条（逐条 id 见 §2.3），实现任务面更大（§10：`LLVM-031t` + `QEMU-038t`）。**(B) 豁免 / (C) 最小均否决**。§2/§6 已按 (A) 改写 |
| **R2b-1** | **`dst_rd0` 规则描述须扩写**：(A) 引入的 15 条 FP 引用要求规则描述显式覆盖 `orri` 目的 `rdhb`（`convert_f2i`/`classify`/`rf2rd`）与 `orrr` 单目的 `rdhb`（`compare`） | 规则描述与 `rule_refs` 自相矛盾 | 采纳 §2.4：扩写 `legality_rules.yaml` L26–40 适用范围（**不增删规则、不改 status**） |
| **R3** | **`gen_legality_list` 的 fp 注去重** | 回填后 fp 条目会在「规则 bullet」与「scope: fp 注」**双双出现** | 采纳 §2.6：fp 注仅列无规则条目；文案随 R1 |
| **R4** | **`fp` 无规则条目**：改前 **9 条**（compare 4 / rf_mem 单寄存器 4 / set.w 1）；R2b (A) 后 **5 条**（rf_mem 单寄存器 4 / set.w 1） | 回填后仅余 5 条无 `rule_refs`（与 `fp_semantics` 一致） | 保持（与 `check_fp_contract` 一致）；`compare` 4 条已由 R2b (A) 补 `dst_rd0` |
| **R5** | **§2.9 交叉断言是否新增** | 不加则 `opcodes.rule_refs` 与 `fp_semantics.legality_refs` 双源可漂移 | **用户裁定 = 采纳（2026-10-04）**：新增 Check 8（低成本、可失败），§2.9 |
| **R6** | **`contract-asm-list.md` / `SimRISC-07` L4 正文文案** | 若 R1 方案 B 不清理，则「未实现」表述残留 | **用户裁定 = 随 R1 一并清理（2026-10-04）**（§2.6）；`SimRISC-07` L4 属正文行，仅改该行、不动其它正文 |
| **R7** | **`check-spec-drift` 审计 `contract-fp.md`** | 改 §3/§8/§12/§15 须保持版本头/引用合规 | 保持 `[SimRISC-]` 引用与结构；改后跑 `check-spec-drift` |
| **R8** | **LLVM/QEMU 实现缺口（15 条 `dst_rd0@FP`）** | 合约/门控落地后实现仍不检 ⇒ 合约↔实现不一致 | 本任务**只登记**建议任务号（§10：`LLVM-031t`、`QEMU-038t`），**不创建、不实现**；不得因「实现未跟上」而回退合约 |

---

## 9. 与 `SPEC-086t`/`087t`/`088t` 的衔接（不改写历史）

- `SPEC-086t` 的 `scope` 分区口径（152/60/15/227）**不变**；本任务只改 `scope != m1 ⇒ rule_refs=[]` 这一**子口径**（收窄为 `excluded`），并随 R1（方案 B）修订 `decode` 口径。二者均已由用户 2026-10-04 裁定，**不再改判**。
- `SPEC-087t` 的 `fp_semantics.legality_refs` 为 FP 合法性**真源**；`SPEC-088t` 的 `mreg_*` 归并**保持**。本任务把该真源**投影回** `opcodes.rule_refs`（此前因 `SPEC-086t` 口径为空），并随 R2b (A) 为 15 条 rd-目的指令在**双边**（`opcodes`/`fp_semantics`）补 `dst_rd0`。
- 历史任务书「完成区/审阅记录」**不改写**；`deferred.md` L55/L60 由 `/complete` 收尾时更新（本任务不预填）。

---

## 10. 后续衔接：需另立的实现任务（**本任务只登记，不创建**）

R2b (A) 使**合约 / 生成物 / 门控**覆盖 `dst_rd0@FP`（15 条），但 LLVM/QEMU **当前不检** `dst_rd0@FP`（§1.6）⇒ 合约↔实现存在缺口。按「合约 vs 实现分离」，须另立实现任务（**建议号仅供用户参考，最终编号以创建时为准；本任务不创建**）：

| 建议任务 | 模块 | 内容 | 依赖 |
|---|---|---|---|
| **`LLVM-031t`** | llvm | 汇编期静态检查：FP 的 rd-目的 15 条（`convert_f2i` 8 + `classify` 2 + `compare` 4 + `rf2rd` 1）目的字段为 `rd0` 时硬报错（Error 级、非零退出），对齐 M1 的 `dst_rd0` 静态检查语义 | `SPEC-089t` 已验证；`LLVM-029t/030t` |
| **`QEMU-038t`** | qemu | 运行期 ILLI：上述 15 条 FP rd-目的指令目的为 `rd0` 时 `gen_exception_illegal`（0x88），对齐 M1 `dst_rd0` 运行期语义 | `SPEC-089t` 已验证；`QEMU-034t`–`037t` |

> **交接事实源**：两任务须以本任务落地后的 `contract-fp.md §3/§8/§12/§15` + `fp_semantics.yaml`（含 `dst_rd0`）为准，**Spec-first**，不从现有实现反推。`deferred.md` L60 由本任务 `/complete` 收尾时追加「R2b 已裁定 (A) + 实现任务待立」。**本任务不得因实现缺口而回退合约。**

---

## 完成区

**测试结果**：全部通过。
- 一键证据脚本 `.work/evidence/SPEC-089t/run.sh`（默认模式）EXIT=0：独立复算 17 项 + 三处交叉核对 6 项 + 验收门控 10 项，全 PASS。
- `--inject` 模式 EXIT=0：反例注入 (a)–(g) 全部「注入→FAIL→还原→回绿」，且还原后 5 文件指纹一致（`38784f77…b886`）。
- `make check` EXIT=0（`repository checks: PASS`；lit 29/29）。
- 关键命令真实输出见 `.work/log/spec/SPEC-089t-*.log` / `.work/log/spec/SPEC-089t-evidence.log` / `.work/log/spec/SPEC-089t-inject.log`。

**修改文件**（本任务产出，未提交，未 `git add -A`）：
- 生成器/门控：`tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/spec/check_scope.py`、`tools/spec/check_fp_contract.py`、`tools/llvm/gen_asm_list.py`、`Makefile`（仅 check-scope 注释文案）。
- 合约（手改）：`contracts/legality_rules.yaml`、`contracts/fp_semantics.yaml`、`.tao/knowledge/contract-fp.md`。
- 生成物（重跑，**非手编**）：`contracts/opcodes.yaml`、`.tao/knowledge/contract-asm-list.md`、`spec/SimRISC-01/02/03/07`（LEGALITY 生成区；07 另含 ASSEMBLY 区标题 + L4 正文）。
- 证据脚本（落 `.work/`，不入库）：`.work/evidence/SPEC-089t/run.sh`；日志 `.work/log/spec/SPEC-089t-*.log`。
- **未触碰用户并发的归档改动**：`spec/Process-04-…`、`spec/Toolchain-01-…`、`docs/README.md`、`tools/infra/check_issues.py`、`.tao/knowledge/MEMORY.md`、`docs/issues.yaml → .tao/knowledge/issues.yaml`（staged rename）均保持原样；`tools/spec/check_scope.py` 内用户已改的 `docs/issues.yaml → .tao/knowledge/issues.yaml`（HISTORY_PREFIXES）原样保留。
- **未改**：`components/**`、`tests/**`、`spec/SimRISC-0.5.3/**`、历史任务书、`adr-*`、`.tao/knowledge/milestones.md`。

**验收结果**（逐条真实命令 + 退出码；§5/§6）：
- §5.1 FP `rule_refs` 回填：独立复算 `有 rule_refs 指令=190`、`引用处数=310`、`scope:fp 有 rule_refs=55`、`dst_rd0=119`；FP 无规则仅 5 条（`ld.t/st.t/ld.o/st.o` + `set.w`）。逐规则：`dst_rf0 35 / encode_fp_root_n 2 / mreg_zero 49 / mreg_range_overflow 49 / mreg_range_overlap 6 / dst_rd0 119`。
- §5.2 规则翻 active：`legality_rules.yaml` 仍 16 条，active 15 / deferred 1；`check_rule-refs` EXIT=0，摘要 `active 被引用 11, active 豁免 4, deferred 1; 指令引用 310 处`。
- §5.3 交叉一致性：`check-fp-contract` EXIT=0；新增 Check 8 `opcodes.rule_refs == fp_semantics.legality_refs: 期望=0 实际=0`；`FP 规则被引用 dst_rd0: 期望=15 实际=15`；`FP_SPECIFIC_RULES` 不含 `dst_rd0`（nonfp 断言仍 0）。
- §5.4 生成区回绿：`check-legality-drift: 12 chapters OK`（EXIT=0）；`git diff --name-only -- spec/SimRISC-*.md` 仅 01/02/03/07（LEGALITY 生成区 + 07 ASSEMBLY 标题）。
- §5.5 `decode` 口径（R1-B）：`opcodes.yaml` 中 scope fp 含 decode = 0、scope excluded 含 `decode: ILLI` = 15；`grep -c "decode: ILLI" contracts/opcodes.yaml` = 16（15 记录 + 1 头注）；`check-scope` EXIT=0，断言 `scope==excluded ⇒ decode=ILLI` 与 `scope∈{m1,fp} ⇒ 无 decode/旧字段`；fp 的「未实现，decode ILLI」在 `gen_asm_list`/LEGALITY/`contract-asm-list.md`/`SimRISC-07` 0 命中。
- §5.6 FP rd-目的 `dst_rd0`（15 条）：`spec/SimRISC-02` 生成表 `dst_rd0` 8→**9 条**（含 `rf2rd_orri_rf`）；ch07 LEGALITY `dst_rd0` 14 条（合计 15）；`fp_semantics` 同 15 id 含 `dst_rd0`；`contract-fp.md §3/§8/§9/§12/§15` 与 `legality_rules.yaml` 的 `dst_rd0` 描述均已同步。
- §5.7 计数不变项：M1 152 / 总 227 / scope 分区 152·60·15；`validate-encoding` 227 条 OK；`validate-vectors 152/152`；`check-spec-drift` 4 合约 PASS；`check-interface` 80/80。**（lit 实测 29、patches 实测 69，与任务书「26/67」不符——为任务书规划期数字陈旧，二者本任务前后不变，见「新发现/坑」。）**
- §5.8 残留/越界：`check-no-residue: PASS`；`git status --untracked-files=all` 除应改文件 + 本任务书 + 用户并发项外无残留；`components/**`、`tests/**` 不在 diff。
- §5.9 `make check` EXIT=0。
- §5.1 反例注入 (a)–(g)（`.work/log/spec/SPEC-089t-inject.log`）：
  - (a) 条件改回 `scope != m1` → 重生成后 `check-rule-refs` Gate2 FAIL（`dst_rf0`/`encode_fp_root_n` 孤儿）→ 还原回绿。
  - (b) 删 `convert_ff` 的 `no_overlap`（源 + 重生成）→ Check 8 FAIL（`ft2fo/ft2ft/fo2ft/fo2fo` 缺 `mreg_range_overlap`）→ 回绿。
  - (c) `dst_rf0` 改回 `deferred`（保留引用）→ **`check-rule-refs` 本身仍 EXIT=0**（deferred 允许 0 引用），由验收摘要断言 `active 被引用 11, active 豁免 4, deferred 1` 判 FAIL（实测摘要变为 `active 被引用 10 … deferred 2`）→ 回绿。（任务书 §5.1(c) 称 Gate2 FAIL，实测为摘要口径，详见「新发现/坑」。）
  - (d) 给任一 scope fp 注入 `decode: ILLI` → `check-scope` FAIL（`m1/fp 记录含 decode`）→ 回绿。
  - (e) 手改 `SimRISC-07` LEGALITY 一行 → `check-legality-drift` FAIL（1 violation, 11 OK）→ 回绿。
  - (f) fp_semantics 去 4 族代表（`ft2it`/`ftcls`/`ftqcmp`/`rf2rd`）的 `dst_rd0` → `dst_rd0` 计数 15→11 FAIL 且 Check 8 逐 id 报出 4 条 → 回绿。
  - (g) **只补 14**（单条 `ft2ut_orri_rf` 去 `dst_rd0`）→ 计数 15→14 FAIL 且 Check 8 报出 `ft2ut_orri_rf` → 回绿（证明「全补 15」被机械判定）。

**新发现/坑**：
1. **任务书 §5.1(c) 与实现不符（供模板改进）**：`dst_rf0` 改回 `deferred` 但保留 FP 引用时，`check_rule_refs.py` **EXIT=0**——Gate2 对 `status==deferred` 直接 `continue`（「deferred 允许 0 引用」），豁免自检也只统计 active 未引用集（仍为 4）。故「翻 active」的正确回归判据是**摘要口径**（`active 被引用 11 / deferred 1`，验收 §5.2），而非 Gate2。证据脚本 (c) 据此以摘要断言实现。
2. **任务书计数「lit 26 / patches 67」陈旧**：实测 `check-lit` **29/29**、`check-patch-tree` **69 patches**（`LLVM-028t` 的 overlap-legality lit、`LLVM-029t/030t`、`QEMU-033t` 等依赖任务已在其后加入）。二者非本任务改动（`tests/**`、`components/**` 不在 diff），本任务前后不变。
3. **R1 文案清理未覆盖的非任务文件残留**：`spec/SimRISC-00-指令系统设计.md` L290/L379、`.tao/knowledge/contract-isa.md` L25/L821/L823 仍写 `scope: fp（未实现，decode ILLI）`。二者**不在任务书 §2 改动清单**（§5.5 亦仅点名 `gen_asm_list`/LEGALITY/`contract-asm-list.md`/`SimRISC-07`），按「不得修改任务文档未列出的文件」**未动**，登记为遗留。
4. 复现命令与留证：`bash .work/evidence/SPEC-089t/run.sh`、`--inject`；复杂输出留 `.work/log/spec/SPEC-089t-*.log`（逐命令捕获被检命令自身退出码，无 `tee` 吞码）。

**遗留问题**：
- **L1（新发现 3）**：`spec/SimRISC-00` 与 `contract-isa.md` 的 fp「未实现，decode ILLI」文案未清（非本任务文件）。建议后续 spec 小任务按 R1 口径收口（改「已实现」并去掉 fp 的 decode 表述），并评估是否需门控防回归。
- **L2（R2b/A 实现缺口，任务书已明确「本任务不创建」）**：15 条 `dst_rd0@FP`（`convert_f2i` 8 + `classify` 2 + `compare` 4 + `rf2rd` 1）的 LLVM 汇编期静态检查与 QEMU 运行期 ILLI **尚未实现**；建议另立 `LLVM-031t`/`QEMU-038t`（本任务仅登记，未创建）。`deferred.md` L60 由 `/complete` 收尾时更新。
- **L3**：`check_rule-refs` 对「deferred 规则被引用」无断言（见新发现 1）；是否加「deferred 不得被引用」门控由后续裁定，本任务未改 `check_rule_refs.py`（任务书 §2.8 要求代码不变）。


## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查（本轮无嵌套子代理）：逐条核对 `generate_opcodes.py`（7 个 FP 表达式映射、各族 `legality` 与 `fp_semantics.legality_refs` 逐族一致、`_compute_rule_refs` 条件）、`check_scope.py`（3a/3b 覆盖全部 scope）、`check_fp_contract.py`（6 条 FP_RULES/精确计数/Check 8 排序集合比较）、`gen_legality_list.py`（fp 注仅列无规则条目）、`gen_asm_list.py`（badge/头部文案）、`legality_rules.yaml`/`fp_semantics.yaml`/`contract-fp.md` 文案；并逐条实跑反例注入确认 FAIL 路径可达。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_fp_contract.py` 顶部注释仍写「5 条 FP 规则」 | ✅已修 | 注释改「6 条（…+ dst_rd0）」并列入共享规则 | `py_compile` OK；`run.sh` 复算 6 条计数全绿 |
| F2 证据脚本 `inj_f`/`inj_g` 对单元素 `[dst_rd0]`（compare）定位失败，误改相邻记录 | ✅已修 | 改为「按 id 定位 `legality_refs` 行 + 三种形态剥离」，加 assert | `--inject` EXIT=0，(f) 4 族代表均被 Check 8 报出 |
| F3 任务书 §5.1(c) 称 `check-rule-refs` Gate2 FAIL，实测 EXIT=0（deferred 允许 0 引用） | ⏸延后（已披露） | (c) 以验收摘要断言实现；未改 `check_rule_refs.py`（§2.8 要求代码不变） | 实测输出 `active 被引用 10 … deferred 2`；记录于完成区「新发现 1」 |
| F4 任务书「lit 26 / patches 67」与实测 29/69 不符 | ❌不修（非本任务引入） | 未动 `tests/**`、`components/**` | `git diff --name-only` 不含二者；`make check` 前后同值 |
| F5 `spec/SimRISC-00` L290/L379、`contract-isa.md` L25/821/823 仍有 fp「未实现，decode ILLI」 | ⏸延后（已披露） | 未动（不在任务书 §2 清单） | 登记完成区「新发现 3」「遗留 L1」 |

判决：所有「应修」项已修并复验；F3/F4/F5 为任务书口径/范围外的既存事实，均已留证披露，不阻断本任务（`make check` EXIT=0、证据脚本双模式 EXIT=0）。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-04
**审查范围**：§5 全部验收标准 + §5.1 反例注入 (a)-(g) + 脚本审计 + 独立注入 + 披露判定

---

##### A. 证据脚本审计（`.work/evidence/SPEC-089t/run.sh`）

| 审计项 | 结论 |
|---|---|
| 非交互 | ✅ 无 stdin 读取 |
| 任一失败即非零退出 | ✅ `fail` 变量累加，`exit 1` |
| 逐项打印 | ✅ `ck`/`run_gate` 打印期望/实际/退出码 |
| 无 `tee` 吞退出码 | ✅ 用 `> log 2>&1; rc=$?` |
| (a)-(g) 注入非空 | ✅ 每个 `inj_*` 含 `assert` 定位失败即报错 |
| (a)-(g) 可还原 | ✅ `backup_all`/`restore_all` + 文件指纹比对 |
| (a)-(g) 独立归因 | ✅ 每个注入改不同文件/不同断言路径 |
| (c) Gate2 vs 摘要口径 | ✅ 已正确定位：`gate_c()` 用摘要断言（`active 被引用 11`），非 Gate2 退出码 |
| (f) 4 族代表覆盖 | ✅ `ft2it`/`ftcls`/`ftqcmp`/`rf2rd` 各一族 |
| (g) 只补 14 鉴别 | ✅ 去单条 `ft2ut_orri_rf` 的 `dst_rd0` ⇒ 计数 15→14 + Check 8 报出 |
| 恒真断言 | 未发现。`ck` 比较期望/实际，`run_inj` 比较 rc_bad≠0 且 rc_ok==0 |

**脚本审计结论**：合格，可作为验收依据。

---

##### B. 重跑记录（真实命令 + 输出 + 退出码）

**B1. 证据脚本正常模式**
```
$ bash .work/evidence/SPEC-089t/run.sh
──── SPEC-089t 验收（独立复算 + 交叉核对 + 门控）────
[1] 独立复算计数
  [PASS] 复算 有 rule_refs 指令: 期望=190 实际=190
  [PASS] 复算 引用处数: 期望=310 实际=310
  [PASS] 复算 dst_rd0 引用数: 期望=119 实际=119
  [PASS] 复算 scope:fp 有 rule_refs: 期望=55 实际=55
  [PASS] 复算 decode: ILLI 记录数: 期望=15 实际=15
  [PASS] 复算 scope:fp 含 decode: 期望=0 实际=0
  [PASS] 复算 FP 无规则条目数: 期望=5 实际=5
  [PASS] 复算 规则 active: 期望=15 实际=15
  [PASS] 复算 规则 deferred: 期望=1 实际=1
  [PASS] 复算 dst_rf0: 期望=35 实际=35
  [PASS] 复算 encode_fp_root_n: 期望=2 实际=2
  [PASS] 复算 mreg_zero: 期望=49 实际=49
  [PASS] 复算 mreg_range_overflow: 期望=49 实际=49
  [PASS] 复算 mreg_range_overlap: 期望=6 实际=6
  [PASS] 复算 dst_rd0@FP（15 条 id）: 期望=15 实际=15
  [PASS] 复算 opcodes↔fp_semantics 漂移 id: 期望=0 实际=0
  [PASS] FP 无规则 id 集: 期望=ld.o_rrii_rf,... 实际=一致
[2] 三处交叉核对（6 项全 PASS）
[3] 验收门控（10 项全 PASS）
SPEC-089t evidence: PASS
EXIT=0
```

**B2. 证据脚本 `--inject` 模式**
```
$ bash .work/evidence/SPEC-089t/run.sh --inject
== 注入 (a)-(g) == 全部「注入后 exit≠0 → 还原后 exit=0 → PASS」
注入全部还原后文件指纹一致: 期望=3aea971c... 实际=3aea971c...
SPEC-089t evidence: PASS
EXIT=0
```

**B3. `make check`**
```
$ make check
repository checks: PASS
Total Discovered Tests: 29, Passed: 29 (100.00%)
EXIT=0
```

**B4. 独立计数复算（reviewer 自跑 Python，不信任脚本）**
```
scope分区: m1=152 fp=60 excluded=15 total=227
有rule_refs指令: 190
引用处数: 310
dst_rd0: 119 (M1=104 FP=15)
scope:fp 有rule_refs: 55
decode ILLI 总: 15, fp含decode: 0, excluded含decode ILLI: 15
FP无规则: 5 -> ['ld.o_rrii_rf','ld.t_rrii_rf','set.w_rwii_rf','st.o_rrii_rf','st.t_rrii_rf']
规则: total=16 active=15 deferred=1
EXIT=0
```

---

##### C. 约束逐条核验

| 验收标准 | 判定 | 证据 |
|---|---|---|
| §5.1 FP rule_refs 回填：有引用指令=190、引用处数=310、scope:fp 有 rule_refs=55、FP 无规则=5 | ✅ PASS | 独立复算 190/310/55/5；逐规则 dst_rf0=35 encode_fp_root_n=2 mreg_zero=49 mreg_range_overflow=49 mreg_range_overlap=6 dst_rd0=119（M1:104+FP:15） |
| §5.2 规则翻 active：16 条/active 15/deferred 1；check-rule-refs 摘要 active 被引用 11/豁免 4/deferred 1/引用 310 | ✅ PASS | 独立复算 15/1；`check_rule_refs.py` EXIT=0 摘要匹配 |
| §5.3 交叉一致性：Check 8 PASS；dst_rd0=15；FP_SPECIFIC_RULES 不含 dst_rd0 | ✅ PASS | `check_fp_contract.py` EXIT=0；Check 8 期望=0 实际=0；dst_rd0 期望=15 实际=15 |
| §5.4 生成区回绿：check-legality-drift 12 OK | ✅ PASS | `check_legality_drift.py` EXIT=0，12 chapters OK |
| §5.5 decode 口径 R1-B：fp 含 decode=0、excluded 含 ILLI=15、check-scope PASS、fp「未实现」0 命中 | ✅ PASS | 独立复算 fp_decode=0 ex_decode=15；`check_scope.py` EXIT=0；`grep` SimRISC-07/contract-asm-list 0 命中 |
| §5.6 FP dst_rd0 15 条：逐条在 opcodes + fp_semantics 均含 dst_rd0；rd2rf 不含 | ✅ PASS | 逐条核对 15 条全部 YES；rd2rf rule_refs=['mreg_zero','mreg_range_overflow']（无 dst_rd0） |
| §5.7 计数不变项：M1=152/总=227/scope=152·60·15；validate-encoding PASS；validate-vectors 152/152；check-spec-drift 4 合约 | ✅ PASS | 独立复算 152/227/152·60·15；`make check` EXIT=0 含 validate-encoding/vectors/spec-drift |
| §5.8 残留越界：components/ tests/ 不在 diff | ✅ PASS | `git diff --name-only` 不含 components/ tests/ |
| §5.9 make check EXIT=0 | ✅ PASS | 29/29 passed, repository checks: PASS |
| 生成物可复现：generate_opcodes.py 重生成语义一致 | ✅ PASS | 语义比较 `a==b` True（diff 仅为 YAML key 排序差异） |
| check-asm-list-drift PASS | ✅ PASS | byte-identical |
| check-asm-list-consistency PASS | ✅ PASS | 证据脚本 gates 全 PASS |
| check-asm-prose --strict PASS | ✅ PASS | 证据脚本 gates 全 PASS |

---

##### D. 独立注入（reviewer 自选，不用脚本 (a)-(g)）

**注入方案**：删 `opcodes.yaml` 中 `ftqcmp_orrr_rf` 的 `dst_rd0` 引用（`fp_semantics.yaml` 保留不动），重跑 `check_fp_contract.py`。

```
注入: ftqcmp_orrr_rf rule_refs ['dst_rd0'] -> []
check_fp_contract exit=1
  [FAIL] opcodes.rule_refs == fp_semantics.legality_refs: 期望=0 实际=1
STDERR: check-fp-contract: FAIL — FP 双源 rule_refs 漂移: ftqcmp_orrr_rf(缺:['dst_rd0'] 多:[])
```

**还原后回绿**：
```
还原后 check_fp_contract exit=0
  [PASS] FP 规则被引用 dst_rd0: 期望=15 实际=15
  [PASS] opcodes.rule_refs == fp_semantics.legality_refs: 期望=0 实际=0
```

**结论**：Check 8 交叉断言可独立检测 opcodes 侧漏填 `dst_rd0`，具有真实鉴别力。

---

##### E. 披露判定

| 项 | 判定 |
|---|---|
| **L1**：`SimRISC-00` L290/L379、`contract-isa.md` L25/821/823 仍有 fp「未实现，decode ILLI」 | **属实，不在任务书 §2 清单**，engineer 正确未改。建议另立 spec 小任务按 R1 口径收口。不阻断本任务。 |
| **F3**：任务书 §5.1(c) 称 `check-rule-refs` Gate2 FAIL，实测 EXIT=0（deferred 允许 0 引用） | **属实，任务书描述偏差**。`check_rule_refs.py` Gate2 对 `status==deferred` 直接 `continue`，不报 FAIL。正确回归判据是摘要口径（`active 被引用 11/deferred 1`）。engineer 已在脚本 (c) 中以摘要断言实现，处置合理。建议任务书模板修正。不阻断。 |
| **F4**：lit 实测 29/29、patches 实测 69，任务书写 26/67 | **属实，非本任务引入**。`LLVM-028t`/`LLVM-029t`/`LLVM-030t`/`QEMU-033t` 等任务已在其后加入 lit/patches。`git diff` 不含 `tests/`/`components/`。不阻断。 |

---

##### F. 越界核验

`git diff --name-only` 共 18 个文件：
- **本任务改动（12）**：`generate_opcodes.py`、`gen_legality_list.py`、`check_scope.py`、`check_fp_contract.py`、`gen_asm_list.py`、`Makefile`（注释）、`legality_rules.yaml`、`fp_semantics.yaml`、`opcodes.yaml`（生成）、`contract-asm-list.md`（生成）、`contract-fp.md`、`SimRISC-01/02/03/07`（生成区）
- **用户并发归档改动（6，未触碰）**：`MEMORY.md`、`docs/README.md`、`Process-04`、`Toolchain-01`、`check_issues.py`、`contract-asm-list.md` 中归档联动

**未发现越界**。`components/**`、`tests/**`、`spec/SimRISC-0.5.3/**`、历史任务书、`adr-*`、`milestones.md` 均未触碰。

---

##### G. 判决

**Accepted**

全部 10 项验收门控在 reviewer 独立重跑下通过；计数独立复算 16 项全对且三处交叉核对一致；R1 方案 B（fp 无 decode=0、excluded decode ILLI=15）落地正确；R2b (A) 15 条 FP rd-目的指令逐条含 `dst_rd0` 在 opcodes + fp_semantics 双侧一致；Check 8 交叉断言可失败（独立注入证实）；生成物可复现；证据脚本审计合格（(a)-(g) 非空/可还原/独立归因/无恒真）；越界无；披露项 L1/F3/F4 均属实但不阻断。

