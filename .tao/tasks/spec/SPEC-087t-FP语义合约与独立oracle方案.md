# SPEC-087t: FP 语义合约与独立 oracle 方案（原生浮点）

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`SPEC-086t`（`scope` 口径切换，**已验证**，`scope: fp` = 60）；相关基线：`contract-isa.md`（M1 合约，§9 为 FP 指针）、`spec/SimRISC-00/01/02/03/07`、`spec/Process-02`、`spec/Process-03`、`tools/spec/{check_scope,check_rule_refs,gen_legality_list,generate_opcodes}.py`、`tools/infra/check_spec_drift.py`、`Makefile`。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。
>
> **本任务只做「FP 语义合约」；独立 oracle 只出「方案」，不写实现、不产任何期望值。**

---

## 0. 用户裁定（唯一真源，不得增删/更改）

- **路线**：原生浮点（全工具链）；**否决** soft-float libcall（0628 路线）。
- **范围**：`scope: fp` 全量 **60 条**（`contracts/opcodes.yaml`，与 `SPEC-086t` 口径一致）。
- **本棒范围**：**只做 FP 语义合约**；**oracle 只出方案/骨架，不产任何期望值**。
- **里程碑**：`M1→M2` 过渡期任务（`t`，不入 `milestones.md`、不新建里程碑）。
- **本任务不含**：LLVM/QEMU/向量实现、oracle 代码实现、期望值生成。
- **ADR**：**待用户裁定**（见 §10；架构师只给建议，不擅自创建/不擅自否定）。

---

## 1. 事实核实（本轮 architect 实测，作为任务前提；执行时以重跑为准）

### 1.1 无 golden model

`tools/` 下仅 `infra/ integ/ llvm/ qemu/ spec/ testcases/`（实测 `ls -d tools/*/`），**无 `tools/golden/`**；`.tao/tasks/` 下无 `golden/` 目录。项目**当前无任何 FP 参考实现/黄金模型**。唯一可用「独立 oracle」是 `tests/vectors/` 的 M1 向量（由 Python 生成器独立派生），FP 无对应物。

### 1.2 FP 合法性规则现状（实测）

`contracts/legality_rules.yaml`（共 16 条规则）：

| id | 行 | status | 覆盖 | rule_refs 引用 |
|---|---|---|---|---|
| `dst_rf0` | L74 | **`deferred`**（L78） | FP 目的 rf0 → ILLI；列了 35 条（30 rf 目的 + `cs.*` 5）+ 例外清单（`rd2rf`/`ld.o`/`ldm.o`/`ld.t`/`ldm.t`/`set.w`） | **0**（FP 记录 `rule_refs: []`） |
| `encode_fp_root_n` | L187 | **`deferred`**（L191） | `ftroot`/`foroot` 仅 n=2 | **0** |

`check_rule_refs.py`（`make check-rule-refs`）：
- Gate 1（L62–69）：指令 `rule_refs` 的 id 必须存在。
- Gate 2（L79–90）：`status: active` 的规则须被引用，否则 FAIL；**`deferred` 允许 0 引用（L82–83 `continue`）**；豁免清单固定为 4 条（`EXPECTED_ORPHAN_EXEMPTIONS`，L23–28），清单本身有自检。
- 含义：**新增 FP 规则若置 `active` 且无引用 ⇒ `make check` 变红**；置 `deferred` 安全。

`tools/spec/generate_opcodes.py::_compute_rule_refs`（L729，判据 L738）：`scope != "m1"` ⇒ `rule_refs: []`（**不解析 FP 的 legality**）。`EXPR_TO_RULE`（L689–727）无 FP 表达式。

`tools/spec/gen_legality_list.py`：`rule_to_chapters`（L106–116）只从 `entry.rule_refs` 建映射；FP 记录无 `rule_refs` ⇒ **新增 FP 规则不会进入任何 LEGALITY 生成区**（对 `check-legality-drift` 无影响）；`SEMANTIC_MAP`（L38–55）/`RULE_SUMMARY`（L67–84）无 FP 规则条目（未引用即不渲染）。

### 1.3 `scope: fp` 60 条按语义族的分布（实测，本任务书基准）

`python3` 统计 `opcodes.yaml` `scope=="fp"` = 60 条，按助记符/族：

| 族（建议名） | 条数 | id |
|---|---|---|
| `convert_ff`（同/异浮点格式） | 4 | `ft2fo/ft2ft/fo2ft/fo2fo_orri_rf` |
| `convert_f2i`（浮点→整型） | 8 | `ft2it/ft2io/ft2ut/ft2uo/fo2it/fo2io/fo2ut/fo2uo_orri_rf` |
| `convert_i2f`（整型→浮点） | 8 | `it2ft/io2ft/ut2ft/uo2ft/it2fo/io2fo/ut2fo/uo2fo_orri_rf` |
| `arith`（S2D1 运算） | 12 | `ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb/foadd/fosub/fomul/fodiv/forem/fosclb_orrr_rf` |
| `root`（S1D1 开方） | 2 | `ftroot_orri_rf/foroot_orri_rf` |
| `sign`（符号位注入） | 4 | `ftsgnj/ftsgnn/fosgnj/fosgnn_orrr_rf` |
| `compare` | 4 | `ftqcmp/ftscmp/foqcmp/foscmp_orrr_rf` |
| `classify` | 2 | `ftcls_orri_rf/focls_orri_rf` |
| `cs_rf`（浮点条件赋值） | 5 | `cs.n/cs.z/cs.p/cs.eq/cs.ne_rrrr_rf` |
| `rf_mem`（RF 存取） | 8 | `ld.t/st.t/ld.o/st.o_rrii_rf`、`ldm.t/stm.t/ldm.o/stm.o_rrri_rf` |
| `rf_move`（RF↔RD 块赋值） | 2 | `rd2rf_orri_rf/rf2rd_orri_rf` |
| `set_w_rf`（RF 立即数） | 1 | `set.w_rwii_rf` |
| **合计** | **60** | |

- **`dst_rf0` 命中 35 条**：`convert_i2f`(8) + `convert_ff`(4) + `arith`(12) + `root`(2) + `sign`(4) + `cs_rf`(5) = 35（目的为 rf 的都不含例外项）。
- **多寄存器（`immu6` = 连续个数）命中 28 条**：`convert_ff`(4) + `convert_f2i`(8) + `convert_i2f`(8) + `classify`(2) + `rf_mem` 多寄存器(4：`ldm.t/stm.t/ldm.o/stm.o`) + `rf_move`(2) = 28。
- **`root` 的 `immu6` 是 `n`（非个数）**：2 条，归 `encode_fp_root_n`。

### 1.4 spec 依据现状（file:line，实测）

- `spec/SimRISC-00-指令系统设计.md`：§浮点寄存器 L82–90（rf0 源合法/目的非法、ft/fo、64 位）；§浮点状态寄存器 L92–124（位布局、舍入 4 模式、标志 NV/DZ/OF/UF/NX、写掩码、不触发异常）；§MISC-RF指令编码 L375–388（44 条权威编码表，标 `scope: fp`）。
- `spec/SimRISC-07-浮点运算.md`：头部 L4–6（`[scope: fp]` + **FP 范围总账 60=44+16**）；生成区 L8–60（ASSEMBLY_LIST）、L62–111（LEGALITY，全为 `decode ILLI` 占位）；正文 §格式转换指令 L116–155（含 `immu6` 1–63、转换饱和/NaN/OF/UF/NX）；§浮点运算指令/S2D1 L157–185（`ftrem`/`forem`、`ftsclb`/`fosclb`）；§S1D1 L187–201（`rootn(x,n)` **仅 n=2**、`rootn(-0,2)` 不要求）；§浮点符号位操作指令 L203–225（`copySign`、`rfHD=rf0`→`abs()`、`rfHC==rfHD`→`copy/negate`）；§浮点比较指令 L227–246（结果 1/0/−1、unordered→qNaN/sNaN、符号位 0）；§浮点分类指令 L248–278（10 类位 [9:0]、其余清零、`immu6` 1–63）；L279 注（rf0 目的→ILLI、源合法）。
- `spec/SimRISC-01-取数存数.md`：§存取RF寄存器 L178–202（`ld.t/st.t` 4B、`ld.o/st.o` 8B；`ldm/stm` `immu6` 1–63；`rfHA+immu6>64`→ILLI；`rf0` 目的合法且 `ld.t/ldm.t` 的 `[63:32]` 不变、源读全 64 位）。
- `spec/SimRISC-02-寄存器复制.md`：`rf2rd`/`rd2rf` L73–88（块赋值、`immu6` 1–63、`rd2rf` 的 `rf0` 目的合法含 `{rf0:...}`、`rf2rd` `rf0` 源合法）；§浮点条件赋值 L111–132（两类条件、`rf0` 目的→ILLI/源合法）。
- `spec/SimRISC-03-16位立即数操作.md`：`set.w` L64–73（只设 16 位、`set.w rf0` 合法、`wp2`→舍入/`wp0`→异常状态、`wp1/wp3` 写无效）；`set.ft`/`set.fo` 伪指令 L158–186（展开为 `set.w`/`rd2rf`/`ft2ft`/`fo2fo`）。
- `README.md` L9–13：版本表 `SimRISC = 0.5.4`（`check_spec_drift` 的版本真源）。
- `tools/infra/check_spec_drift.py`：**枚举 `.tao/knowledge/` 下所有 `contract-*.md`**（L282），逐个要求 spec-sourced（**L147–159：版本头行须含 `[SimRISC-XX §…]` 引用**）或 ADR-sourced，否则 FAIL。⇒ **新 `contract-fp.md` 必须带合规版本头**。
- `spec/README.md` 投影表 L70–83：`SimRISC-01…12` 行的 ①叙述合约为 `contract-isa.md`；缺口登记表 L85–94。
- `contracts/README.md` L5–18：`contracts/` 文件清单（`opcodes.yaml`/`abi.yaml`/`legality_rules.yaml`），并明示「**黄金模型（Python 独立 oracle）属 `golden` 模块（M2）**」。
- `spec/Process-02-合约编写规范.md` L7–19：合约文件清单（含 4 项已登记缺口），**无 `contract-fp.md`**。

### 1.5 基线可复现（实测口径）

`make check` 当前 EXIT=0，关键计数（`SPEC-086t` 后）：M1 **152**、总记录 **227**、`rule_refs` 指令 **135**/引用 **198**、规则 **16**、lit **26**、patches **67**、interface **80/80**、`check-scope` PASS（152/60/15）。本任务据此定义「应变/不应变」计数（§5）。

---

## 2. 契约落点设计（≥2 备选 + 取舍 + 推荐）

### 2.1 叙述合约（`contract-*.md`）

**方案 A（推荐）－ 新建 `.tao/knowledge/contract-fp.md`**
- 与 `contract-isa.md`（明确自述「M1 范围」「`scope: fp`…本合约不提取」）分离；FP 60 条 + IEEE754 语义 + oracle 派生规则自成一体。
- 与项目既有体例一致（`contract-abi.md`/`contract-elf.md` 均按域分册）。
- 版本头合规：首行 `> **版本：0.5.4** [SimRISC-00 §浮点寄存器][SimRISC-07 §版本]`（满足 `check_spec_drift` L147–159）。

**方案 B － 扩 `contract-isa.md`**
- 优点：单文件、无新文件登记。
- 否决理由：① 违反其自述范围（§9 现为 FP 指针桩 L821–828）；② 文件已 ~1500 行，FP 会再膨胀数百行，混入 IEEE754/舍入/标志等非 ISA 编码内容；③ `check_spec_refs.py` 对 contract-isa 的规范断言计数（standalone 基线 76）更易受扰动。

### 2.2 机器可读表示

**方案 A（推荐）－ 新建 `contracts/fp_semantics.yaml`（语义）+ 扩 `legality_rules.yaml`（合法性）**
- `fp_semantics.yaml` 承载：FCSR/舍入/标志环境、12 个语义族、**60 条 id→family→spec_cite→semantics_ref→legality_refs** 映射；**不承载编码**（编码唯一真源仍是 `opcodes.yaml`）。
- 合法性**规则**（ILLI 触发条件）入 `legality_rules.yaml`（与既有目录体例一致）；语义（运算/舍入/NaN/饱和）不入该文件。
- **`opcodes.yaml` 不改**（关键取舍）：编码表继续只由 `spec/SimRISC-00 + contract-isa` 生成，避免 `validate-encoding`/`validate-vectors`/`check-interface`/三处生成投影的连锁回归；FP 的合法性由 `fp_semantics.yaml` 的 `legality_refs` 表达。

**方案 B － 扩 `opcodes.yaml`（每条加 `semantics`/`fp_family` 字段）**
- 优点：单表。
- 否决理由：① 编码表混入语义，破坏「编码表 = 编码」的单一职责；② 改 `_compute_rule_refs`（`scope != m1 ⇒ []`）+ `EXPR_TO_RULE` + 重生成，**改动 60 条记录并触发 `validate-encoding`/`check-rule-refs`/`gen_legality_list` 连锁**，`SimRISC-07` LEGALITY 生成区会从「decode ILLI」变成渲染 FP 规则条目，需重跑多处生成物；③ 与用户「FP 独立范围」的取向相悖。

**方案 C － 只写叙述合约、无机器可读**
- 否决：无法机械门控 60 条覆盖/族完备，无法给后续 oracle 提供稳定输入；不满足用户「机器可读部分放哪」的要求。

### 2.3 与 `spec/SimRISC-07` 正文/生成区的关系（避免打架）

- **正文**（`spec/SimRISC-07` L116–279）= 语义真源，**本任务不改**（已含 IEEE754/舍入/标志/饱和/NaN/`immu6`/`n=2` 等）。
- **生成区**（ASSEMBLY_LIST L8–60、LEGALITY L62–111）= 由 `gen_asm_list.py` / `gen_legality_list.py` 从 `opcodes.yaml`(+`legality_rules.yaml`) 机械生成；因 `opcodes.yaml` 不动、新 FP 规则不被 `rule_refs` 引用，**生成区逐字节不变**（`check-asm-list-*`/`check-legality-drift` 保持绿）。
- **新 `fp_semantics.yaml` 是第三类投影**（语义投影），**不接入任何现有生成器**，只被新门控 `check-fp-contract` 与后续 oracle 消费。这样不会与既有生成投影冲突。

### 2.4 取舍汇总

| 维度 | A（推荐） | B（扩 isa / opcodes） | C（仅叙述） |
|---|---|---|---|
| 与既有范围自洽 | ✅ | ❌（混范围/混职责） | ✅ |
| 不触发既有生成投影/计数回归 | ✅ | ❌ | ✅ |
| 机器可门控（60 条覆盖/族完备） | ✅ | ✅ | ❌ |
| oracle 可稳定消费 | ✅ | ✅ | ❌ |
| 与 `check_spec_drift`/`check_spec_refs` 兼容 | ✅（版本头合规） | 部分（大改 contract-isa） | ✅ |

**推荐：叙述 = `contract-fp.md`；机器可读 = `contracts/fp_semantics.yaml` + `legality_rules.yaml` 扩规则；`opcodes.yaml` 不动。**

> 命名（`contract-fp.md` / `fp_semantics.yaml` / 规则 id 前缀）待用户在任务确认时拍板（见 §11 R1）。

---

## 3. 合约内容清单（按族，每条标注 spec 依据）

> 要求：`contract-fp.md` 每个语义族独立 § 编号 + **锚点 `<a id="…">`**（供 `fp_semantics.yaml` 的 `semantics_ref` 机械解析）；每条断言句末标 `[SimRISC-XX §章节]`（Spec-first，不从实现反推）。

### 3.0 全局环境（`contract-fp.md` §1）
- rf 寄存器模型：64 位；ft 用低 32 位、高 32 位不做规定。[SimRISC-00 §浮点寄存器]
- rf0 = FCSR：位布局 `[63:51]/[50:34]/[33:32]/[31:22]/[21:5]/[4:0]`；**写只更新 `[33:32]`+`[4:0]`**；`rf0` 可作运算源、**不可作运算目的**。[SimRISC-00 §浮点寄存器][SimRISC-00 §浮点状态寄存器]
- 舍入模式 `rf0[33:32]`：`00 RNE / 01 RTZ / 10 RDN / 11 RUP`。[SimRISC-00 §浮点状态寄存器]
- 标志 `rf0[4:0]`：`bit0 NV / bit1 DZ / bit2 OF / bit3 UF / bit4 NX`，按 IEEE754 累积（accrued）。[SimRISC-00 §浮点状态寄存器]
- 合规性：浮点格式符合 IEEE754；**浮点指令不触发异常**，始终返回 IEEE754 结果（NaN/Inf）。[SimRISC-07 §浮点运算][SimRISC-00 §浮点状态寄存器]
- `immu6` 双重语义：作为**连续个数**（1–63）用于转换/分类/RF 多寄存器；作为 `n` 用于 `root`（仅 2）。`immu6` 本身的 ILLI 条件见 §4。[SimRISC-07 §格式转换指令][SimRISC-07 §S1D1]

### 3.1 `convert_ff`（同/异浮点格式转换）[SimRISC-07 §格式转换指令]
- 语义：逐对转换，`immu6` 连续个数 1–63；源/目的可重叠，按序号递增、**先读后写**。
- 舍入：`rf0[33:32]`。
- 溢出 → ±Inf 并置 OF；下溢按舍入模式处理并置 UF；NaN **传播 payload**；sNaN 输入置 NV 并返回 qNaN。

### 3.2 `convert_f2i`（浮点→整型）[SimRISC-07 §格式转换指令]
- 目的为 **rd**（8 条）；`immu6` 连续个数 1–63。
- NaN/Inf/超范围 → **整型饱和值（最大/最小）** 并置 **NV**。
- 精度损失（inexact）不置 NX？→ **待 spec 明确**（spec 仅说 i→f 可能 inexact、f→i 饱和+NV）；合约如实记录 spec 现状，不臆造（见 §11 R6）。

### 3.3 `convert_i2f`（整型→浮点）[SimRISC-07 §格式转换指令]
- 目的为 **rf**；`immu6` 连续个数 1–63。
- 可能 inexact（精度损失），舍入 `rf0[33:32]`；标志按 IEEE754。

### 3.4 `arith`（S2D1 运算）[SimRISC-07 §浮点运算指令][SimRISC-07 §S2D1]
- orrr：`rfHB` 目的、`rfHC`/`rfHD` 源；**先读全部源再写结果**。
- 集合：`ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb` 与 `fo*` 对应 12 条。
- `ftrem`/`forem` = IEEE754 remainder（`rfHC − n×rfHD`，n 最接近、**平局取偶**）；除零/Inf/NaN 按 IEEE754。
- `ftsclb`/`fosclb` = `rfHC × 2^rfHD`（rfHD 取整数值），舍入按 rf0；NaN/Inf/溢出/下溢按 IEEE754。
- 标志 NV/DZ/OF/UF/NX 按 IEEE754。

### 3.5 `root`（S1D1）[SimRISC-07 §S1D1]
- orri：`rfHB` 目的、`rfHC` 源；`immu6` = `n`，**仅 n=2**（否则 ILLI，见 §4）。
- `rootn(-0,2)` 结果**不做具体要求**。
- 先读源再写结果。

### 3.6 `sign`（符号位注入）[SimRISC-07 §浮点符号位操作指令]
- orrr：`rfHB` 目的、`rfHC`/`rfHD` 源；先读全部源再写结果。
- `sgnj` = `copySign(rfHC, rfHD)`；`sgnn` = `copySign(rfHC, ~sign(rfHD))`。
- 特例：`rfHD=rf0` ⇒ `sgnj` = `abs(rfHC)`、`sgnn` = `−abs(rfHC)`；`rfHC==rfHD` ⇒ `sgnj` = `copy`、`sgnn` = `negate`。

### 3.7 `compare` [SimRISC-07 §浮点比较指令]
- orrr：目的为 **rdHB**；`ftqcmp/ftscmp/foqcmp/foscmp`。
- 结果：`rfHC>rfHD → 1`、`= → 0`、`< → −1`；**unordered**（含 NaN）→ qcmp 返回 **qNaN**、scmp 返回 **sNaN**，**符号位为 0**。
- NaN 按整型解读为**正数**；配合 `cs.*` 的使用约定（与 SimRISC-02 §浮点条件赋值 呼应）。

### 3.8 `classify` [SimRISC-07 §浮点分类指令]
- orri：目的为 **rd**；`immu6` 连续个数 1–63；源/目的可重叠、按序先读后写。
- 输出：目的 `[63:10]` 全清零，仅用 `[9:0]`；10 类位（0 negInf…9 qNaN）。

### 3.9 `cs_rf`（浮点条件赋值）[SimRISC-02 §浮点条件赋值][SimRISC-02 §寄存器组之间块赋值]
- 第一类 `cs.n/cs.z/cs.p`：`rdHA` 为负/零/正 ⇒ `rfHB = rfHC` else `rfHD`。
- 第二类 `cs.eq/cs.ne`：`rdHA==/!=rdHB` ⇒ `rfHC = rfHD`。
- 目的（`rfHB`/`rfHC`）为 `rf0` → **ILLI**；源（`rfHC`/`rfHD`）为 `rf0` 合法（读全 64 位）。

### 3.10 `rf_mem`（RF 存取）[SimRISC-01 §存取RF寄存器]
- `ld.t/st.t` 4 字节、`ld.o/st.o` 8 字节；`ldm.t/stm.t/ldm.o/stm.o` `immu6` 连续个数 1–63。
- 对齐：继承 SimRISC-01 的宽度对齐（`-t` 4B、`-o` 8B；单条由 `excp_malign` 覆盖）。
- `rf0` 作目的**合法**（`ld.t/ldm.t` 的 `[63:32]` **不变**；`ld.o/ldm.o` 按 FCSR 写掩码）；作源读出**完整 64 位**。

### 3.11 `rf_move`（`rd2rf`/`rf2rd`）[SimRISC-02 §寄存器组之间块赋值]
- orri 块赋值，`immu6` 连续个数 1–63；源/目的可重叠、按序先读后写。
- `rd2rf` 目的 `rf0` **合法**（含 `{rf0:rf0+immu6-1}`）；`rf2rd` 源 `rf0` 合法。

### 3.12 `set_w_rf`（`set.w`）[SimRISC-03 §立即数常数赋值：Immediate constant]
- rwii：只设置指定 16 位，其余 48 位不变。
- `set.w rf0` 合法：`wp2` 命中舍入模式、`wp0` 命中异常状态、`wp1/wp3` 完全写无效（遵 FCSR 写掩码）。

### 3.13 伪指令（非 60 条 id，仅说明）[SimRISC-03 §set.ft 伪指令]
- `set.ft`/`set.fo` 展开为 `set.w` 组合（全零 → `rd2rf {rf},{rd0}`；寄存器传值 → `rd2rf`/`ft2ft`/`fo2fo`）。**属汇编器展开，不进 `opcodes.yaml` 60 条**；合约如实记录即可。

---

## 4. 合法性规则设计

### 4.1 现有两条是否足够？→ **不足**

- `dst_rf0`（deferred）覆盖 35 条 FP 目的 rf0 → ILLI，**保留**（并补全例外：`rd2rf` 含 `{rf0:…}`、`rf2rd` 源、`ld.*-rf`/`ldm.*-rf` 目的、`set.w-rf`）。
- `encode_fp_root_n`（deferred）覆盖 `root` n=2，**保留**。
- **缺**：FP 多寄存器（`immu6`）的 `=0` 与范围越界规则（现有 `mreg_zero`/`mreg_range_overflow` 只覆盖 RD/RB/RA，不覆盖 RF；且 FP 记录无 `rule_refs`）。

### 4.2 建议新增（`contracts/legality_rules.yaml`）

| id（建议） | fault/kind | status | 覆盖（28 条） | spec_cite |
|---|---|---|---|---|
| `fp_mreg_zero` | ILLI/static | **deferred** | FP `immu6` 连续个数形式 `immu6=0` → ILLI：`convert_ff/f2i/i2f`、`classify`、`rf_mem` 多寄存器（`ldm.t/stm.t/ldm.o/stm.o`）、`rf_move` | SimRISC-07 §格式转换指令/§浮点分类指令、SimRISC-01 §存取RF寄存器、SimRISC-02 §寄存器组之间块赋值 |
| `fp_mreg_range_overflow` | ILLI/static | **deferred** | FP `immu6` 形式 `起始+immu6>64` → ILLI（不环绕、不截断），同上 28 条 | 同上 |

- **`root` 的 `immu6` 是 n**，归 `encode_fp_root_n`（不放 `fp_mreg_*`）。
- **`rd2rf`/`rf2rd` 的 `rf0` 目的例外**：作为 `dst_rf0` 的**例外（合法）**记录，不新增规则（规则目录只列非法触发条件）。
- **`set.w-rf`/`ld.*-rf` 的 `rf0` 目的**：同上，作为例外。

### 4.3 status 决策：全部 `deferred`（FP 未实现期）

- 理由：`check_rule_refs` Gate 2（L79–90）对 `active` 规则要求「被引用」，而 `opcodes.yaml` 的 FP 记录 `rule_refs` 恒为 `[]`（生成器 `_compute_rule_refs` L738）；若置 `active` ⇒ **`make check` 变红**。
- `deferred` 允许 0 引用（L82–83），且现有 `dst_rf0`/`encode_fp_root_n` 已是 `deferred`，本任务新增规则同态，**一致性最好**。
- 覆盖改由 **新门控 `check-fp-contract`** 的 `legality_refs` 双向核对承担（§5），不依赖 `check-rule-refs`。
- **未来**（FP 实现任务）翻 `active` 时：需回填 FP 记录的 `legality` + 扩 `EXPR_TO_RULE` + 改 `_compute_rule_refs` 使 `scope: fp` 也解析 `rule_refs`，并重跑 `gen_legality_list`（届时 `SimRISC-07` LEGALITY 生成区会变化）——**本任务不做**，登记为后续衔接点。

### 4.4 `check-rule-refs` 影响

- 规则数 **16 → 18**（+2 deferred）；`指令引用 198 处` **不变**（`opcodes.yaml` 不动）；`active 被引用/active 豁免` 不变；`deferred` 数 +2。**EXIT 0 不变**。
- `gen_legality_list.py` 的 docstring「16 rules」（L6，注释）为文案，可选同步（非门控）。

---

## 5. 门控设计

### 5.1 新增 `tools/spec/check_fp_contract.py`（`make check-fp-contract`）

职责（**可执行、可失败**；输出「检查名 + 期望/实际 + 退出码」）：

1. **覆盖双向一致**：`fp_semantics.yaml` 的 id 集合 == `opcodes.yaml` 中 `scope=="fp"` 的 id 集合；计数 == **60**（缺/多 ⇒ FAIL）。
2. **族合法**：每条 `family` ∈ 12 族枚举；每族计数 == 约定值（`convert_ff`4/`convert_f2i`8/`convert_i2f`8/`arith`12/`root`2/`sign`4/`compare`4/`classify`2/`cs_rf`5/`rf_mem`8/`rf_move`2/`set_w_rf`1）。
3. **spec_cite 非空且合规**：匹配 `^SimRISC-0[0-7]\b`；缺失 ⇒ FAIL。
4. **族完备**：每族声明的 `required_keys` 在族定义中存在（`families` 段）；缺失 ⇒ FAIL。
5. **legality 双向**：每条 `legality_refs` ∈ `legality_rules.yaml` 的 id；且 4 条 FP 规则（`dst_rf0`、`encode_fp_root_n`、`fp_mreg_zero`、`fp_mreg_range_overflow`）各被 ≥1 条 FP id 引用（缺 ⇒ FAIL）；FP 规则的引用者必须都是 `scope: fp`。
6. **叙述锚点可达**：每条 `semantics_ref` = `contract-fp.md#<anchor>`，且 `contract-fp.md` 存在对应 `<a id="<anchor>">`（缺失 ⇒ FAIL）。
7. **合规头**：`contract-fp.md` 首行版本头含 `[SimRISC-` 引用（与 `check_spec_drift` 同判据，提前拦截）。

- **接入**：`Makefile` 的 `.PHONY`（L38–45）+ `check:` 列表（L223）各加 `check-fp-contract`；`spec/README.md` 投影表 ③ 列登记 `tools/spec/check_fp_contract.py`。
- **为何独立而非并入 `check_scope`/`validate_encoding`**：职责单一（Do One Thing）——`check-scope` 管范围分区、`validate-encoding` 管编码、本门控管「FP 语义投影完备性」。

### 5.2 `make check` 影响：应**保持不变**的计数

| 门控 | 期望（改动后） |
|---|---|
| `validate-vectors` | `152/152`、gaps 0、EXIT 0（**228→不动**） |
| `check-scope` | PASS（m1 152 / fp 60 / excluded 15 / total 227） |
| `check-rule-refs` | EXIT 0；`指令引用 198` **不变**；规则数 16→18、deferred +2（仅摘要文案变化） |
| `validate-encoding` | `227 条记录 OK` |
| `check-interface` | `80/80`、`M1 内 152`；`QEMU trans 227/227 (M1 152/152)` |
| `check-legality-drift` | `12 chapters OK`（FP 规则未被 `rule_refs` 引用 ⇒ 生成区不变） |
| `check-asm-list` / `check-asm-list-drift` / `check-asm-prose` | EXIT 0（不动 `opcodes.yaml`） |
| `check-spec-drift` | 绿；**检查合约数 3→4**（新增 `contract-fp.md`），排除 2、错误 0 |
| `check-patch-tree` | `67 patches OK` |
| `check-lit` | `26/26` |
| `check-dirs` / `check-no-residue` | EXIT 0 |
| **新增 `check-fp-contract`** | PASS |

**关键不变量**：`152`（M1）、`227`（总记录）、`198`（rule 引用处）、`26`（lit）、`67`（patches）、`80`（interface）**全部不变**。**预期变化**：规则数 16→18、`check-spec-drift` 合约数 3→4、新增一个 check 目标。

### 5.3 反例注入思路（供验收脚本，必须真实 FAIL→还原→回绿）

- (a) 从 `fp_semantics.yaml` 删除 1 条 id ⇒ `check-fp-contract` FAIL（59/60）。
- (b) 把 1 条 `family` 改为 `bogus` ⇒ FAIL（非法族）。
- (c) 把某条 `legality_refs` 指向不存在的规则 id ⇒ FAIL。
- (d) 删除某族 `required_keys` 中一个键 ⇒ FAIL（族不完备）。
- (e) 删除 `contract-fp.md` 某族 `<a id>` 锚点 ⇒ FAIL（锚点不可达）。
- (f) 空注入防护：每次注入后 `git hash-object` 变化；还原须**重跑相关生成器/恢复原文并复核 blob 一致**。

---

## 6. 独立 oracle 方案（**只出方案：不写实现、不产任何期望值**）

> 本节即「oracle 方案」交付内容；落地到 `docs/fp-oracle-design.md`（设计文档，非实现）。**不含代码、不含任何输入→输出期望值。**

### 6.1 目标与铁律

- FP 测试期望值**不得**由 LLVM/QEMU 生成或校准；必须**独立派生自 `spec/`**（`tests/vectors/README.md` 已载此原则）。
- 本任务**不产期望值**；只定义「将来如何独立派生出可信期望值」。

### 6.2 接口形态（设计层骨架）

```
tools/golden/fp_ref.py
    eval(insn: str, ops: list[int], state: FCSRState) -> (result: list[int], flags: int)
        # insn: opcodes.yaml 的 id（如 "ftadd_orrr_rf"）
        # ops : 输入寄存器原始 64 位（按 fields 顺序）
        # state: rf0 舍入模式 + 标志初值
        # 返回: 目的寄存器原始 64 位（列表，支持块形式）+ 新标志 rf0[4:0]
```
- 输入/输出均为**原始 64 位整数**（不依赖宿主 `float`）；`FCSRState` 只含 `round_mode`/`flags`。
- 由 `fp_semantics.yaml` 的 `id→family→semantics_ref` 驱动分派（同一接口覆盖 60 条）。

### 6.3 从 spec 的派生规则

- 族→spec 章节映射严格取自 `fp_semantics.yaml`（即 §3 清单），oracle 只实现 spec 明文语义；**spec 未明处（如 `convert_f2i` 是否置 NX、`rootn(-0,2)`）标 `UNSPECIFIED`，不臆造**（见 §11 R6）。

### 6.4 舍入模式（`rf0[33:32]`，重点风险）

- 宿主 Python `float` 为 IEEE754 双精、**只有 RNE**；`struct` 打包亦是 RNE。**非 RNE（RTZ/RDN/RUP）无法由宿主 `float` 直接得到**。
- **推荐路径**：纯 Python、以**精确有理数**（`fractions.Fraction` / 自写整数尾数）实现「精确结果 → 按目标格式（f32/f64）+ 指定舍入模式显式舍入 → 编码」；RNE/RTZ/RDN/RUP 四种模式统一由一套显式舍入逻辑处理，**不使用宿主 `float` 的四则运算作为语义来源**。
- 备选（记录取舍）：① `decimal`（支持 5 种舍入，但指数/子正规/标志要额外处理）；② 引入 softfloat 库（依赖外部库、版本锁定成本）；③ 宿主 `struct`+手写 guard/sticky（仅 RNE 可靠，其余仍需手写）。
- **可行性结论**：f32 可行且优先；f64 全模式 + 子正规 + tininess 检测 + NX/UF 判定是难点，需分阶段（见 §6.8）。**这是本方案最大风险**。

### 6.5 标志位（NV/DZ/OF/UF/NX）与 NaN/Inf 传播

- 标志须**累积**到 `rf0[4:0]`（accrued），非仅当条；sNaN→NV+qNaN；f→i 饱和→NV；溢出→±Inf+OF；下溢按舍入+UF；inexact→NX。
- NaN/Inf：按 `contract-fp.md`（§3）逐族实现；`convert_ff` 传播 payload、`compare` 的 unordered 编码、`sign` 的符号注入与 `rf0` 特例。

### 6.6 独立验证方式（自证，不靠 LLVM/QEMU）

- **代数恒等式/性质**：`x+0=x`、`x*1=x`、四舍五入模式下的单调性、`convert_ff` 往返（在可表示范围内）、`sgnj` 与符号位组合恒等式、`classify` 恰一位置位。
- **双路对照（独立实现互证）**：同一语义用两条独立路径计算（精确有理数路径 vs 手写位级路径），随机输入下断言一致——**不引入 LLVM/QEMU**。
- **RNE 交叉锚点**：RNE 结果可与宿主 `struct`（f32）/`float`（f64）对拍，**仅作 RNE 的第三方参照**，其它模式与标志仍靠自证。
- **spec 明文用例**：spec 给出的特例（`rootn(-0,2)` 除外、`rfHD=rf0` 的 `abs()`）作为断言。
- 所有自证不得使用 LLVM/QEMU 输出作为期望值。

### 6.7 可行性风险

- f64 + 4 舍入模式 + 子正规 + UF/NX 的精确判定；`ftrem`（IEEE remainder）与 `ftsclb`（scaleB）的边界；NaN payload 逐位传播；`immu6` 块形式的逐对/先读后写顺序。**建议先 f32、先 RNE、先 arith，再扩模式与 f64。**

### 6.8 建议的落地任务（本任务只登记，不创建）

- `GOLDEN-001t`：oracle 骨架（`tools/golden/fp_ref.py` 接口 + `FCSRState` + 分派 + 自证 harness；**无期望值**）。
- `GOLDEN-002t`：f32 arith + RNE + 标志（自证）。
- `GOLDEN-003t`：4 舍入模式 + f64。
- `GOLDEN-004t`：转换/比较/分类/符号/root + 块形式。
- `TESTCASES-0xxt`：FP 覆盖矩阵 + 向量（由 `GOLDEN-*` 独立产期望值 → 反哺 LLVM/QEMU 差分）。

---

## 7. 交付物与改动清单（逐文件）

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `.tao/knowledge/contract-fp.md` | 新建 | FP 叙述合约（§3 清单；版本头合规；族锚点） |
| 2 | `contracts/fp_semantics.yaml` | 新建 | 机器可读语义投影（§2.2 schema；60 条 + 12 族 + 环境） |
| 3 | `contracts/legality_rules.yaml` | 修改 | +`fp_mreg_zero`、+`fp_mreg_range_overflow`（deferred）；补 `dst_rf0` 例外说明 |
| 4 | `tools/spec/check_fp_contract.py` | 新建 | FP 合约门控（§5.1） |
| 5 | `Makefile` | 修改 | `.PHONY` + `check:` + `check-fp-contract` target |
| 6 | `.tao/knowledge/contract-isa.md` | 修改 | §9（L821–828）改为指向 `contract-fp.md` 的**最小指针**（保留 spec 引用，避免 `check_spec_refs` 回归） |
| 7 | `spec/README.md` | 修改 | 投影表增/拆 `SimRISC-07` 行（①`contract-fp.md` ②`fp_semantics.yaml` ③`check_fp_contract.py` ④`缺口`） |
| 8 | `spec/Process-02-合约编写规范.md` | 修改 | 合约清单加 `contract-fp.md`（现行） |
| 9 | `contracts/README.md` | 修改 | 文件说明表加 `fp_semantics.yaml` |
| 10 | `docs/fp-oracle-design.md` | 新建 | oracle 方案（§6 内容；**无实现、无期望值**） |
| 11 | `.tao/knowledge/{MEMORY,changelog,deferred}.md` | 由 `/complete` 追加 | 本任务不预填 |
| 12 | （可选，待用户裁定）`.tao/adr/adr-00xx-*.md` | 新建 Candidate | 见 §10 |

**明确不改**：`contracts/opcodes.yaml`（**关键**）、`spec/SimRISC-07` 正文与生成区、`spec/SimRISC-00/01/02/03` 正文、`components/**`、`tests/vectors/**`、`tests/lit/**`、`tools/llvm/*`、`tools/qemu/*`、`tools/testcases/*`、`spec/SimRISC-0.5.3/**`、历史任务书、`adr-*` 正文。

---

## 8. 验收标准（可执行、可失败、含反例注入）

> 通用：完成区贴**真实命令输出与退出码**；留证捕获被检命令自身退出码（禁 `| tee` 后 `$?`）；复杂命令留 `.work/log/spec/SPEC-087t-*.log`；engineer 交付一键证据脚本 `.work/evidence/SPEC-087t/run.sh`（非交互、失败非零退出、逐项打印期望/实际、内置反例注入自检）。

1. **契约落点**：`contract-fp.md` 存在且含合规版本头（`[SimRISC-00 §…]`/`[SimRISC-07 §…]`）；`check-spec-drift` 绿且「检查 4 个合约」。
2. **机器可读覆盖**：`fp_semantics.yaml` 恰 60 条，id 集合与 `opcodes.yaml` `scope=="fp"` **双向一致**；12 族计数与 §1.3 一致。
3. **门控可失败**：`make check-fp-contract` PASS；§5.3 反例 (a)–(f) 逐条真实 FAIL→还原→回绿（`git hash-object` 证明非空注入）。
4. **合法性规则**：`legality_rules.yaml` 含 4 条 FP 相关规则（2 旧 + 2 新），均 `deferred`；`check-rule-refs` EXIT 0、`指令引用 198` 不变；FP 规则被 `check-fp-contract` 的 `legality_refs` 全覆盖。
5. **生成投影不回归**：`check-asm-list-consistency`/`check-asm-list-drift`/`check-legality-drift`/`check-asm-prose` EXIT 0（`SimRISC-07` 生成区逐字节不变 ⇒ 可由 `git diff spec/SimRISC-07-浮点运算.md` 为**空**佐证）。
6. **关键计数不变**：`make check` EXIT 0；`152/227/198/26/67/80` 与 §5.2 逐条一致；`validate-vectors 152/152`；`check-scope` PASS；`check_interface 80/80`。
7. **oracle 方案**：`docs/fp-oracle-design.md` 含 §6 六要素（接口/派生/舍入/标志与 NaN/自证/可行性+落地任务）；**不含任何期望值**（grep 不到 `expected`/向量式输入输出对）；明确「不得由 LLVM/QEMU 校准」。
8. **残留与越界**：`git status --untracked-files=all` 干净（除任务应改文件 + 本任务书）；`check-no-residue` PASS；临时产物仅 `/tmp/opencode/SPEC-087t/`，日志 `.work/log/spec/`；`git diff --name-only` 与 §7 一致（`opcodes.yaml`、`spec/SimRISC-07`、`components/**`、`tests/**`、`tools/{llvm,qemu,testcases}/**` **不在 diff**）。
9. **`make check` 全绿**：含新 target；`repository checks: PASS`。

---

## 9. 范围边界与后续衔接

**范围边界（明确不含）**：
- 不含 oracle 代码实现（`tools/golden/**` 不创建代码）；
- 不含任何期望值 / 测试向量；
- 不含 LLVM/QEMU 实现；不含 FP 向量/lit；
- 不改 `opcodes.yaml`、`spec/SimRISC-07` 正文/生成区、`components/**`、`tests/**`、`tools/{llvm,qemu,testcases}/**`；
- 不建 ADR（待用户裁定，见 §10）；不改历史 ADR/任务书/`SimRISC-0.5.3`。

**后续衔接点（本任务仅登记，不创建）**：
- `GOLDEN-001t`：oracle 骨架（接口 + 自证 harness，无期望值）。
- `GOLDEN-00xt`：FP 语义实现（f32→f64、RNE→四模式）。
- `TESTCASES-0xxt`：FP 覆盖矩阵（`inventory.md` 多表 + `validate_vectors.parse_inventory` 按 section 区分；当前加 FP 行会触发 `INVENTORY EXTRA`）。
- `LLVM-0xxt` / `QEMU-0xxt` / `INTEG-0xxt`：FP 汇编/QEMU trans（替换 ILLI 桩）/E2E。
- FP 实现期：把 `dst_rf0`/`encode_fp_root_n`/`fp_mreg_*` 翻 `active` + 回填 FP `rule_refs` + 重跑 `gen_legality_list`（`SimRISC-07` LEGALITY 生成区届时会变）。

---

## 10. ADR 判断（须主动提醒，由用户裁定；本任务不创建 ADR）

**判据核对（`spec/Process-03-ADR编写规范.md` L7–14）**：

| 判据 | 是否命中 | 说明 |
|---|---|---|
| 1 高代价 | ✅ | FP 语义合约是后续 golden/LLVM/QEMU/testcases 的共同依据，改起来贵 |
| 2 跨模块/需一致 | ✅ | 影响 golden/llvm/qemu/testcases 多模块接口 |
| 3 多方案需记录取舍 | ✅ | 叙述落点（A/B/C）、机器可读表示（A/B）、合法性 status（deferred/active）均有取舍 |
| 4 外部依赖/契约 | ✅ | IEEE754 外部标准 + 跨模块语义契约 |
| 5 结论固化约束 | ✅ | 固化「FP 语义如何投影/如何独立派生」 |
| 6 定位/方向 | ⚠️ | 原生浮点路线已由用户裁定，本任务是其投影，非新方向 |

**架构师建议：建议立 1 个 ADR（Candidate）**，主题「FP 语义合约的落点与机器可读表示」，关联 `SPEC-087t`；**只记决策/理由/被否方案/指向 spec 章节，不承载语义正文**（正文归 `spec/SimRISC-07` 与 `contract-fp.md`，见 Process-03 L20–24）。拟决策（**须逐条经用户确认后方可写为 Accepted**，AGENTS.md）：
- D1 叙述落点 = 新 `contract-fp.md`（否决：扩 `contract-isa.md`）。
- D2 机器可读 = 新 `contracts/fp_semantics.yaml` + 扩 `legality_rules.yaml`（否决：扩 `opcodes.yaml`）。
- D3 FP 合法性规则未实现期 status = `deferred`（否决：`active` + 回填 `rule_refs`）。

**备选（不立）**：沿用 `SPEC-086t` 先例，把理由与被否方案记入任务书 + `changelog`。**此点必须由用户拍板**（见 §11 R9）。

---

## 11. 风险与开放问题

| # | 风险/开放问题 | 影响 | 建议处置 |
|---|---|---|---|
| R1 | 命名未定稿：`contract-fp.md` / `fp_semantics.yaml` / 规则 id `fp_mreg_zero`/`fp_mreg_range_overflow` / 族名 | 全任务命名 | 下发前用户拍板 |
| R2 | 新增 FP 规则 `deferred` vs `active` | `check-rule-refs` Gate 2 | 推荐 `deferred`（§4.3）；若用户要 `active` 须同任务回填 `rule_refs`，工作量与影响面大增 |
| R3 | oracle「方案/骨架」是否含**代码骨架文件** | 交付物范围 | 本任务书按「仅设计文档、无代码」规划；若用户要骨架代码，另立 `GOLDEN-001t`（见 §6.8） |
| R4 | `docs/fp-oracle-design.md` 落点 | 交付物 | 推荐 `docs/`（设计方案与 `docs/m2-spec-planning.md` 同类） |
| R5 | `contract-fp.md` 版本头须过 `check_spec_drift`（L147–159 只读版本头行） | `make check` 变红 | 首行写 `> **版本：0.5.4** [SimRISC-00 §浮点寄存器][SimRISC-07 §版本]`；执行时先跑 `make check-spec-drift` |
| R6 | spec 未明处：`convert_f2i` 是否置 NX、`ftrem`/`sclb` 边界、`rootn(-0,2)` | 合约可能被指「臆造」 | 合约**如实记录 spec 现状**并标「spec 未明 / 不要求」；oracle 标 `UNSPECIFIED`，不臆造 |
| R7 | `contract-isa.md` §9 改指针可能扰 `check_spec_refs`（standalone 基线 76） | 隐性回归 | 改动保持最小并带 spec 引用；改后跑 `check_spec_refs.py` 对比基线 76 |
| R8 | 改 `contracts/legality_rules.yaml` 后 `gen_legality_list.py` docstring「16 rules」陈旧 | 文档失真（非门控） | 可选同步注释；确认生成区不变 |
| R9 | ADR 立/不立 | 决策层 | **用户裁定**（§10 建议：立 1 个 Candidate，D1–D3 逐条确认） |
| R10 | `fp_semantics.yaml` 60 条逐条 `spec_cite` 的核对工作量 | 工期 | 用 §1.3 族表 + §3 清单机械派生；门控兜底 |
| R11 | `immu6` 双重语义（个数 vs `n`）易混 | 语义错误 | 合约 §3.0/§3.5 明确；`legality_refs` 区分（`fp_mreg_*` vs `encode_fp_root_n`） |

---

## 执行环境
**执行环境**：本地

## 接口规范

### 输入
- `contracts/opcodes.yaml`（`scope: fp` 60 条）、`contracts/legality_rules.yaml`（16 条）
- `spec/SimRISC-00/01/02/03/07`、`spec/README.md`、`spec/Process-02`、`spec/Process-03`
- `.tao/knowledge/contract-isa.md`（§9 指针）、`README.md`（版本表）
- `tools/spec/{check_scope,check_rule_refs,gen_legality_list,generate_opcodes}.py`、`tools/infra/check_spec_drift.py`、`Makefile`
- `.tao/knowledge/deferred.md`（FP 衔接点登记）

### 输出
1. `.tao/knowledge/contract-fp.md`（叙述合约，§3 清单 + 族锚点 + 合规版本头）
2. `contracts/fp_semantics.yaml`（机器可读语义投影；60 条 + 12 族 + FCSR 环境）
3. `contracts/legality_rules.yaml` 扩 2 条 FP 规则（`deferred`）
4. `tools/spec/check_fp_contract.py`（新门控）+ `Makefile`（`check-fp-contract` 接入 `check`）
5. `docs/fp-oracle-design.md`（oracle 方案，无实现/无期望值）
6. 文档接线：`contract-isa.md §9`、`spec/README.md`、`spec/Process-02`、`contracts/README.md`
7. 知识沉淀由 `/complete` 追加

### 约束
- 中文；**不提交 git**；**不创建 ADR**；只动任务书范围，越界须披露。
- **Spec-first**：所有语义/合法性断言来自 `spec/`；不从 LLVM/QEMU 反推。
- **不改** `opcodes.yaml`、`spec/SimRISC-07` 正文/生成区、`components/**`、`tests/**`、`tools/{llvm,qemu,testcases}/**`、`adr-*`、`SimRISC-0.5.3`、历史任务书。
- 临时产物 `/tmp/opencode/SPEC-087t/`；日志 `.work/log/spec/SPEC-087t-*.log`；证据脚本 `.work/evidence/SPEC-087t/run.sh`。
- 遵循 `AGENTS.md`「子代理硬约束」「验证脚本反例门控」。

## 验收标准
见上文 §8（1–9）；反例注入见 §5.3。

## 完成区

**测试结果**：通过 8/8 命令级断言 + 11/11 关键计数断言（一键证据脚本默认模式 `.work/evidence/SPEC-087t/run.sh`，EXIT=0）；注入模式 (a)–(g) 7/7「非空注入→FAIL→还原→回绿」全部成立（EXIT=0）。`make check` EXIT=0。

**修改文件**：
- 新建 `.tao/knowledge/contract-fp.md`（FP 叙述合约 + 12 族锚点 + 合规版本头）
- 新建 `contracts/fp_semantics.yaml`（FCSR 环境 + 12 族 + 60 条投影）
- 修改 `contracts/legality_rules.yaml`（+`fp_mreg_zero`/`fp_mreg_range_overflow`，均 `deferred`；`dst_rf0` 补例外）
- 新建 `tools/spec/check_fp_contract.py`（门控）
- 修改 `Makefile`（`.PHONY` + `check:` 列表 + `check-fp-contract` target + help）
- 修改 `.tao/knowledge/contract-isa.md`（§9 改最小指针，保留 spec 引用）
- 修改 `spec/README.md`（投影表拆出 `SimRISC-07` 行）
- 修改 `spec/Process-02-合约编写规范.md`（+`contract-fp.md` 现行）
- 修改 `contracts/README.md`（+`fp_semantics.yaml`）
- 新建 `docs/fp-oracle-design.md`（oracle 方案，无实现/无期望值）
- 修改 `tools/spec/gen_legality_list.py`（docstring `16 rules`→`18 rules`，R8 可选；**越界披露**）
- 新建 `.work/evidence/SPEC-087t/run.sh`（一键证据脚本，`.work/` gitignored）
- `.work/log/spec/SPEC-087t-*.log`（验收留证，gitignored）

**验收结果**（真实命令 + 退出码）：
- `make check` → **EXIT=0**，`repository checks: PASS`（留证 `.work/log/spec/SPEC-087t-after-check.log`）。
- 应**不变**：`validate_vectors: 152/152`（gaps 0）、`validate_encoding: 227 条记录 OK`、`check-interface 总计 80 项 | PASS: 80 | FAIL: 0`、`QEMU trans 227/227 (M1 152/152)`、`check-legality-drift: 12 chapters OK`、`check-patch-tree: 67 patches OK`、`check-lit` 26/26、`check-asm-list-consistency: 12 spec files OK`、`check-scope: PASS`（m1 152/fp 60/excluded 15/total 227）、`check-rule-refs: 指令引用 198 处`。
- 预期**变化**：`check-spec-drift` 由「检查 3 个合约」→ **「检查 4 个合约，排除 2，错误 0」**；`check-rule-refs` 规则 **16→18**（deferred 3→5）；新增 `check-fp-contract: PASS`。
- 反例注入 (§5.3 a–g，留证 `.work/log/spec/SPEC-087t-evid-inject-run.log`)：`git hash-object` 证明注入非空；每条注入后 `make check-fp-contract` 非零退出（rc=2），还原后回绿（rc=0）：
  - (a) 删 `set.w_rwii_rf` → FAIL（59/60）
  - (b) `family: bogus` → FAIL
  - (c) 悬空 `legality_ref` → FAIL
  - (d) 删族 `required_keys` 一个键 → FAIL（另验证：删指令记录 `legality_refs` 键 → `记录缺 required_keys: ft2fo_orri_rf:legality_refs` → FAIL）
  - (e) 删 `contract-fp.md` 的 `<a id="arith">` → FAIL
  - (g) 删 `legality_rules.yaml` 的 `fp_mreg_zero` → FAIL
  - (f) 空注入防护：每个 inject_case 均断言 hash 变化 + 还原一致（无一空注入）
- 生成投影不回归：`git diff -- spec/SimRISC-07-浮点运算.md` 为空；`git diff -- contracts/opcodes.yaml` 为空。
- `check-spec-refs.py`（standalone，不在 `make check`）：实测 **76 violations（18 Check1 + 58 Check2）**，与 HEAD 基线逐项比对**完全相同**（HEAD 临时合约目录重跑亦为 76），且 `contract-fp.md` **零新增违规**。
- oracle 方案：`grep -n "expected" docs/fp-oracle-design.md` 无命中（rc=1）；含接口/派生/舍入/标志与 NaN/自证/可行性+落地任务六要素；明载「不得由 LLVM/QEMU 校准」。
- 残留：`git status --porcelain` 仅本任务应改文件 + 本任务书；`check-no-residue: PASS`；临时产物仅 `/tmp/opencode/SPEC-087t/`。

**新发现/坑**：
1. `check-asm-prose.py` 扫描 `docs/**/*.md`，且**空语言围栏（```）按 asm 处理**——设计文档伪代码块中的 `#` 行会触发 `R4(#注释)` 致 `make check` 红。修法：围栏标语言（如 ```text）或用 `;` 注释。（本轮实际踩到并修复）
2. 门控 `required_keys` 的 FAIL 路径需**双向**可达：删「families 段声明」与删「指令记录键」是两条独立路径，均已注入验证可达。
3. `check-spec-refs.py` 为 standalone 且有**历史既存 76 违规基线**，不在 `make check`；新增 `contract-*.md` 须保证零新增违规（本轮 contract-fp.md 贡献 0）。
4. `check-fp-contract` 的「FP 规则未被非 fp 记录引用」断言在当前 `opcodes.yaml`（FP 记录 `rule_refs` 恒 `[]`）下恒真——作为未来 FP 实现期的防护保留。
5. `contracts/README.md` 原列表仅 3 文件且明示「黄金模型属 golden 模块（M2）」——本任务只在 `contracts/` 加**语义投影数据**（非实现），与该原则不冲突。

**遗留问题**：
- `check-spec-refs.py` 的 76 条历史违规非本任务引入，未修（不越界）。
- `tools/spec/gen_legality_list.py` docstring 「16 rules→18 rules」为 `SPEC-087t §4.4`/R8 标注的**可选**同步，已做，属 §7 清单外的越界改动（已披露）。
- oracle 实现与任何期望值/向量**按任务不在本棒**；后续 `GOLDEN-001t…004t`/`TESTCASES-0xxt` 已在 `docs/fp-oracle-design.md §7` 登记（未创建任务）。
- ADR **按任务不创建**（§10 待用户裁定）。
- FP 实现期需把 `dst_rf0`/`encode_fp_root_n`/`fp_mreg_*` 翻 `active` + 回填 FP `rule_refs` + 重跑 `gen_legality_list`——本任务不做，登记于 §9。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`tools/spec/check_fp_contract.py`、`contracts/fp_semantics.yaml`、`.tao/knowledge/contract-fp.md`、`contracts/legality_rules.yaml`（新规则）、`Makefile`、`docs/fp-oracle-design.md`、接线文档（`contract-isa.md §9`、`spec/README.md`、`Process-02`、`contracts/README.md`）、`tools/spec/gen_legality_list.py`。

**逐行审查要点与判决**：
- 逻辑正确性：门控 7 项职责均有独立断言与可达 FAIL 路径（含指令级/族级 required_keys 双路径）；60 条 id 双向覆盖、12 族计数与 §1.3 一致；`spec_cite` 正则 `^SimRISC-0[0-7]\b` 覆盖全部；`semantics_ref` 锚点 12 族全可达。**通过**。
- 设计/惯用法：独立门控（`record()` 汇总 + 非零退出 + 「检查名/期望/实际/退出码」），与 `check_scope.py` 体例一致；未改 `opcodes.yaml`（编码真源），未触发 `gen_legality_list`/`validate_encoding`/`check-interface` 连锁。**通过**。
- 防造假：所有结论取自真实命令输出；证据脚本内置 (a)–(g) 注入自检并用 `git hash-object` 证明非空；还原核对 hash 并回绿。**通过**。
- 发现并处置：
  | finding | 处置 | 改了什么 | 复验证据 |
  |---|---|---|---|
  | F1 `docs/fp-oracle-design.md` 伪代码块以 `#` 注释 + 空语言围栏 → `check-asm-prose` R4 报 5 处、`make check` EXIT=2 | ✅已修 | 围栏改 ```` ```text ````（非 asm 块，R4 不适用） | `python3 tools/spec/check_asm_prose.py --strict` → EXIT=0 `PASS (0 violations)`；随后 `make check` EXIT=0 |
  | F2 `gen_legality_list.py` docstring 仍写 `16 rules`（R8 可选陈旧） | ✅已修 | docstring `16 rules`→`18 rules` | `make check-legality-drift` EXIT=0（12 chapters OK）；`make check` EXIT=0 |
  | F3 门控 required_keys 需复核「指令记录缺键」路径可达（不止族声明） | ✅已修/已验证 | 无需改码（本就检查两处）；补注入验证 | 删 `instructions[0].legality_refs` → `check-fp-contract` 非零，报 `记录缺 required_keys: ft2fo_orri_rf:legality_refs`；还原回绿 |
- 未修 finding：无。
- **自审判决**：所有 finding 已修/已验证，完成区与真实输出逐条对齐；状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-03
**审查范围**：全部 10 项验收标准（§8 1–9 + §5.3 反例注入）

---

##### 1. 零改动断言

```
$ git diff --name-only -- contracts/opcodes.yaml spec/SimRISC-07-浮点运算.md components/ tests/ tools/llvm/ tools/qemu/ tools/testcases/
（无输出）
```
**结论**：✅ `opcodes.yaml`、`spec/SimRISC-07`、`components/**`、`tests/**`、`tools/{llvm,qemu,testcases}/**` 零改动。

---

##### 2. 应不变计数（重跑 `make check` EXIT=0，逐项提取）

```
$ make check → EXIT=0，repository checks: PASS
```

| 门控 | 期望 | 实际 | 结果 |
|---|---|---|---|
| validate-vectors | 152/152 | `validate_vectors: 152/152` | ✅ |
| validate-encoding | 227 条 | `validate_encoding: 227 条记录 OK` | ✅ |
| check-interface | 80/80 | `总计: 80 项 \| PASS: 80 \| FAIL: 0` | ✅ |
| QEMU trans | 227/227 (M1 152/152) | `227/227 insns have trans impl (M1 152/152)` | ✅ |
| check-legality-drift | 12 chapters | `check-legality-drift: 12 chapters OK` | ✅ |
| check-patch-tree | 67 patches | `67 patches OK` | ✅ |
| check-lit | 26/26 | `Passed: 26 (100.00%)` | ✅ |
| check-scope | PASS (152/60/15) | `check-scope: PASS` | ✅ |
| check-rule-refs | 指令引用 198 处 | `指令引用 198 处` | ✅ |
| check-asm-list-consistency | 12 spec files | `check-asm-list-consistency: 12 spec files OK` | ✅ |

---

##### 3. 应变化

| 项 | 期望 | 实际 | 结果 |
|---|---|---|---|
| 合法性规则 | 16→18 | `规则 18 条`（active 9+豁免 4+deferred 5） | ✅ |
| check-spec-drift 合约数 | 3→4 | `检查 4 个合约，排除 2 个，错误 0 个` | ✅ |
| make check 含 check-fp-contract | PASS | `[check-fp-contract] 期望退出码=0 实际退出码=0` | ✅ |

---

##### 4. 合约质量（Spec-first）

- **contract-fp.md**：12 族锚点 `<a id="…">` 全部存在（convert_ff/convert_f2i/convert_i2f/arith/root/sign/compare/classify/cs_rf/rf_mem/rf_move/set_w_rf + fp-env/pseudo/open-points）；版本头 `> **版本：0.5.4** [SimRISC-00 §浮点寄存器][SimRISC-07 §版本]` 合规。
- **spec_cite 可定位性**（10 个唯一值全部验证）：
  ```
  SimRISC-01 §存取RF寄存器 → spec/SimRISC-01-取数存数.md ✅
  SimRISC-02 §寄存器组之间块赋值 → spec/SimRISC-02-寄存器复制.md ✅
  SimRISC-02 §浮点条件赋值 → spec/SimRISC-02-寄存器复制.md ✅
  SimRISC-03 §立即数常数赋值：Immediate constant → spec/SimRISC-03-16位立即数操作.md ✅
  SimRISC-07 §S1D1 → spec/SimRISC-07-浮点运算.md ✅
  SimRISC-07 §S2D1 → spec/SimRISC-07-浮点运算.md ✅
  SimRISC-07 §格式转换指令 → spec/SimRISC-07-浮点运算.md ✅
  SimRISC-07 §浮点分类指令 → spec/SimRISC-07-浮点运算.md ✅
  SimRISC-07 §浮点比较指令 → spec/SimRISC-07-浮点运算.md ✅
  SimRISC-07 §浮点符号位操作指令 → spec/SimRISC-07-浮点运算.md ✅
  ```
- **抽查语义断言**：
  1. §5 arith「`ftrem`/`forem` 为 IEEE754 remainder，平局取偶」→ spec SimRISC-07 §S2D1 匹配 ✅
  2. §7 sign「`sgnj` = copySign，`sgnn` = copySign(rfHC, ~sign(rfHD))」→ spec §浮点符号位操作指令 匹配 ✅
  3. §1 全局「FCSR [33:32] 舍入模式 00 RNE / 01 RTZ / 10 RDN / 11 RUP」→ spec §浮点状态寄存器 匹配 ✅
  4. §6 root「仅 n=2，`rootn(-0,2)` 不做具体要求」→ spec §S1D1 匹配 ✅
  5. §15 合法性「`dst_rf0` 覆盖 35 条」→ 实际 `dst_rf0` 被 35 条引用 ✅
- **fp_semantics.yaml 双向一致**：opcodes `scope:fp` 60 条 == semantics 60 条（`missing=[]`, `extra=[]`） ✅
- **12 族计数**：convert_ff:4/convert_f2i:8/convert_i2f:8/arith:12/root:2/sign:4/compare:4/classify:2/cs_rf:5/rf_mem:8/rf_move:2/set_w_rf:1 ✅
- **legality_refs 双向**：4 条 FP 规则各被 ≥1 条引用（dst_rf0:35, encode_fp_root_n:2, fp_mreg_zero:28, fp_mreg_range_overflow:28） ✅
- **compare 族 legality_refs=[]**：正确——目的为 `rd`（整型寄存器），不受 `dst_rf0`（rf 目的）约束 ✅

---

##### 5. 新门控可失败（审计 `check_fp_contract.py`）

- **16 个 `record()` 断言**，覆盖 7 项职责（id 计数/重复/覆盖双侧/族合法/族集合/12 族计数/spec_cite/required_keys 声明/required_keys 记录/legality_refs 存在/4 条 FP 规则被引用/FP 规则未被非 fp 引用/锚点可达/版本头）。
- **每条断言有可达 FAIL 路径**：无恒真、无「两支写同一结果」、无 `check(name, True)` 模式。
- **结构观察**：「FP 规则未被非 fp 记录引用」在当前状态（FP 记录 `rule_refs=[]`）下为恒真，但作为未来 FP 实现期的前向防护保留——**符合设计意图，非缺陷**。
- **退出码语义**：`failures` 非空 → `return 1`；否则 `return 0`。无 `tee` 吞码。

---

##### 6. 脚本审计 + 重跑

**`run.sh` 结构审计**：
- ✅ `set -u`（未定义变量报错）
- ✅ `backup_all()`/`restore_all()` + `trap 'restore_all' EXIT`（异常退出也还原）
- ✅ `inject_case()` 用 `git hash-object` 断言注入非空 + 还原后 hash 一致
- ✅ `run_expect_rc()` 直接捕获 `$?`（不用 `tee` 吞码）
- ✅ 7 个注入函数 (a)–(g) 各修改不同目标/不同字段，均非空
- ✅ `FAIL` 变量累积 + 最终非零退出

**默认模式重跑**（独立终端）：
```
$ bash .work/evidence/SPEC-087t/run.sh → EXIT=0
所有 16 个断言 [PASS]，含 check-spec-refs 基线 76 + contract-fp.md 零新增
```

**注入模式重跑**（独立终端）：
```
$ bash .work/evidence/SPEC-087t/run.sh --inject → EXIT=0
(a) 删 set.w_rwii_rf → FAIL (rc=2) → 还原 → PASS (rc=0) ✅
(b) family=bogus → FAIL (rc=2) → 还原 → PASS (rc=0) ✅
(c) 悬空 legality_ref → FAIL (rc=2) → 还原 → PASS (rc=0) ✅
(d) 删 required_keys → FAIL (rc=2) → 还原 → PASS (rc=0) ✅
(e) 删 contract-fp.md 锚点 → FAIL (rc=2) → 还原 → PASS (rc=0) ✅
(g) 删 fp_mreg_zero 规则 → FAIL (rc=2) → 还原 → PASS (rc=0) ✅
(f) 空注入防护：所有 inject_case hash 均变化 + 还原一致 ✅
```

---

##### 7. 独立注入（不使用脚本自带 (a)–(g)）

**注入方案**：改 `fp_semantics.yaml` 中 `ftadd_orrr_rf` 的 `spec_cite` 从 `"SimRISC-07 §S2D1"` → `"BOGUS"`。

```
$ python3 -c "..."  # 改 spec_cite
$ python3 tools/spec/check_fp_contract.py
  [FAIL] spec_cite 合规: 期望=0 实际=1
  check-fp-contract: FAILED (1 项)
  exit 1
EXIT=1

$ cp /tmp/.../fp_semantics.yaml.RESTORE contracts/fp_semantics.yaml  # 还原
$ python3 tools/spec/check_fp_contract.py
  check-fp-contract: PASS
  exit 0
EXIT=0

$ git diff --name-only -- contracts/fp_semantics.yaml
（无输出 — 已还原）
```

**结论**：✅ 注入非空 → FAIL → 还原 → 回绿。注入不在脚本 (a)–(g) 范围内。

---

##### 8. oracle 方案合规

- `docs/fp-oracle-design.md` 存在，91 行
- **不含期望值**：`grep -c "expected"` → 0 ✅
- **明载「不得由 LLVM/QEMU 校准」**：4 处「不得」（L5 铁律、L16 接口约束、L47 UNSPECIFIED 原则、L74 自证约束） ✅
- **六要素齐全**：接口形态(L19)、派生规则(L39)、舍入模式(L52)、标志与 NaN(L62)、自证方式(L68)、可行性风险+落地任务(L76) ✅
- **舍入方案自洽**：推荐精确有理数路径、备选 decimal/softfloat/host struct 各有利弊、可行性结论「f32 可行且优先，f64 全模式是难点」——风险如实 ✅
- **无代码**：全文纯设计文档 ✅

---

##### 9. 越界与残留

**已披露越界**：
1. `gen_legality_list.py` docstring `16 rules`→`18 rules`：可选同步（R8），已做——**合理且最小** ✅
2. `contract-isa.md` §9 改指针：保留 spec 引用、只加指针到 `contract-fp.md`——**必要且最小** ✅
3. `spec/README.md` 投影表拆出 `SimRISC-07` 行 ✅
4. `spec/Process-02` 合约清单加 `contract-fp.md` ✅
5. `contracts/README.md` 文件表加 `fp_semantics.yaml` ✅

**未披露越界**：无。

**残留检查**：
```
$ git status --untracked-files=all
  修改: contract-isa.md, Makefile, contracts/README.md, legality_rules.yaml, Process-02, spec/README.md, gen_legality_list.py
  新增: contract-fp.md, fp_semantics.yaml, fp-oracle-design.md, check_fp_contract.py, 任务书
```
全部为任务 §7 应改文件 + 任务书本身。无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留。✅

---

##### 10. 完成区一致性

逐条核对完成区与重跑输出：
- 「8/8 命令级断言 + 11/11 关键计数断言」→ 重跑确认全部 [PASS] ✅
- 「注入模式 (a)–(g) 7/7 全部成立」→ 重跑确认 ✅
- 「make check EXIT=0」→ 重跑确认 ✅
- 「check-spec-refs 基线 76、contract-fp.md 零新增违规」→ 重跑确认 ✅
- 「git diff -- spec/SimRISC-07-浮点运算.md 为空」→ 确认 ✅
- 「git diff -- contracts/opcodes.yaml 为空」→ 确认 ✅

**无夸大或不实**。

---

#### 判决

**Accepted** ✅

全部 10 项验收标准通过（含独立注入验证）。产出物质量合格：零改动约束守住、关键计数不变、新门控可失败、合约 Spec-first 且 spec_cite 全部可定位、oracle 方案合规无代码无期望值、越界均已披露且最小。
