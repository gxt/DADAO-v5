# SPEC-088t: FP 合法性规则归并（删 fp_mreg_*）、`mreg_range_overlap` 扩 FP、`dst_rf0` 分类修正

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-086t`（`scope` 口径，已验证）、`SPEC-087t`（FP 语义合约层，已验证）。相关基线：`contracts/{opcodes,legality_rules,fp_semantics}.yaml`、`.tao/knowledge/{contract-fp,contract-isa}.md`、`spec/SimRISC-07`、`tools/spec/{check_rule_refs,check_fp_contract,gen_legality_list}.py`、`Makefile`。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。
>
> **本任务只做 spec / contract 层修复**：不改任何组件代码（`components/**`）、不改 `tests/**`、不改 `tools/{llvm,qemu,testcases}/**`；实现层归 `QEMU-033t` / `LLVM-028t` / `TESTCASES-023t`。

---

## 0. 用户裁定（唯一真源，不得增删/更改）

1. **不新增** `fp_mreg_zero` / `fp_mreg_range_overflow`；**扩充现有** `mreg_zero` / `mreg_range_overflow` 覆盖 RF 寄存器组形态（28 条）。
2. `rf2rd` / `st.*` / `stm.*` / `cs.*-rf` 的 rf 是**源**；`dst_rf0` 中把它们从「例外（合法）」改标为「**不适用（rf 仅作源，无 rf 目的字段）**」。
3. `ldm.*` 允许 rf0 作目的——**已正确，无需改**（但请核实无遗漏）。
4. 现有 `mreg_range_overflow` 的**源、目的都查**（QEMU `trans_block.c.inc` 六条均为 `hb+hd>64 || hc+hd>64`）；`SPEC-087t` 的 `fp_mreg_range_overflow` **漏写源组**是缺陷。
5. **改 spec 禁止重叠**（**含完全重合**）：`SimRISC-07 §格式转换指令`（及必要时 `§浮点分类指令`）改为与 `SimRISC-02 §寄存器组之间块赋值` 一致——源/目的范围有交集 ⇒ ILLI；用 **`mreg_range_overlap`** 承载，扩到 FP。FP 中同组可重叠者仅 `ft2fo`/`fo2ft`/`ft2ft`/`fo2fo`（`rd2rf`/`rf2rd`/`ft2it`/`it2ft`/`ftcls` 跨组，结构性不可能）⇒ 该规则由 2 条扩到 **6 条**。
6. 分两任务：A（本任务）= spec/contract 层修复；B = `mreg_range_overlap` 的 M1 实现。
7. **不立 ADR**。

> **架构师提示（须用户拍板，见 §8 R1）**：裁定 2 把 `cs.*-rf` 与 `rf2rd`/`st.*`/`stm.*` 并列称「rf 仅作源，无 rf 目的字段」；但 `spec/SimRISC-02 §浮点条件赋值` 与 `.tao/knowledge/contract-fp.md §10` 均明确 `cs.*-rf` 的**目的**（`cs.n/z/p` 的 `rfHB`、`cs.eq/ne` 的 `rfHC`）为 rf0 ⇒ ILLI。若把 `cs.*-rf` 整条标为「不适用」，将丢掉 5 条 ILLI 约束、并把 `dst_rf0` 适用面从 35 降到 30。本任务按「**仅把 `cs.*-rf` 的 rf0-作-源 角色标为不适用；其 rf0-作-目的 仍适用**」拟稿，等待用户确认（R1）。

---

## 1. 事实核实（本轮 architect 实测；执行时以重跑为准）

### 1.1 规则现状（`contracts/legality_rules.yaml`，实测）

| id | 行 | status | 被 `rule_refs` 引用数（M1 记录） |
|---|---|---|---|
| `dst_rf0` | L74–89 | `deferred` | **0** |
| `mreg_zero` | L92–104 | `active` | 21 |
| `mreg_range_overflow` | L105–118 | `active` | 21 |
| `mreg_range_overlap` | L119–127 | `active` | 2 |
| `encode_fp_root_n` | L189–196 | `deferred` | 0 |
| `fp_mreg_zero` | L198–212 | `deferred` | 0 |
| `fp_mreg_range_overflow` | L214–225 | `deferred` | 0 |

实测汇总：规则 **18 条**（active 13 / deferred 5）；`指令引用 198 处`。
（`rule_refs` 由 `tools/spec/generate_opcodes.py::_compute_rule_refs` L729/L738 生成，`scope != "m1" ⇒ []`。）

### 1.2 `scope: fp` 记录的合法性投影（`contracts/fp_semantics.yaml`）

- 60 条 FP 指令的 `legality_refs` 现状：28 条引用 `fp_mreg_zero`+`fp_mreg_range_overflow`；4 条 `convert_ff` 亦引用（同样两项）；35 条引用 `dst_rf0`；2 条 `root` 引用 `encode_fp_root_n`；其余为空。
- 28 条 = `convert_ff`4 + `convert_f2i`8 + `convert_i2f`8 + `classify`2 + `rf_mem` 多寄存器 4（`ldm.t/stm.t/ldm.o/stm.o`）+ `rf_move`2（`rd2rf/rf2rd`）。
- `root` 2 条 `immu6` 语义是 `n`，不属多寄存器，归 `encode_fp_root_n`。

### 1.3 门控现状（实测）

- `tools/spec/check_rule_refs.py`：Gate1 = `rule_refs` id 必须存在；Gate2 = `active` 规则须被引用，否则 FAIL（`deferred` 允许 0 引用；豁免 4 条固定清单）。⇒ `mreg_*` 已 `active` 且被 M1 引用，扩充描述**不触发** Gate2；删掉 2 条 `deferred` 的 `fp_mreg_*` 不影响 active 计数。
- `tools/spec/check_fp_contract.py`：L54 `FP_RULES = ("dst_rf0","encode_fp_root_n","fp_mreg_zero","fp_mreg_range_overflow")`；L172–175 断言每条 FP 规则被 ≥1 条 FP id 引用；L177–181 断言「FP 规则未被非 fp 记录引用」。**注意**：`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 被 M1 记录引用，故 L177–181 必须收缩到「FP 专属规则」（`dst_rf0`/`encode_fp_root_n`），否则改后必 FAIL。
- `tools/spec/gen_legality_list.py`：docstring L6 写「18 rules」；`SEMANTIC_MAP`/`RULE_SUMMARY` **不含** `fp_mreg_*`；生成区只从 `entry.rule_refs` 构造 ⇒ 删 `fp_mreg_*`、改 `mreg_*` 描述**不改变任何 LEGALITY 生成区**。

### 1.4 spec 正文现状（file:line，实测）

- `spec/SimRISC-07-浮点运算.md` L148（§格式转换指令）：末句「**源和目的寄存器范围可以重叠**，转换按序号递增逐对进行，先读后写。重叠时行为依赖顺序，使用者应避免…」——**允许重叠**，须改为禁则。
- `spec/SimRISC-07` L257（§浮点分类指令）：末句「**源和目的寄存器范围可以重叠**，分类按序号递增逐对进行，先读后写。」——同为允许重叠表述；但 `ftcls/focls` 为 rf→rd **跨组**，结构性不可能重叠，须改为如实表述。
- `spec/SimRISC-02-寄存器复制.md` L86（§寄存器组之间块赋值）：已为「源范围与目的范围有交集时触发 ILLI 异常（即不允许源和目的寄存器范围有任何重叠）」——**本任务对齐目标**。
- `.tao/knowledge/contract-isa.md` L375 / L395 / L413：分别属 §3.3.3（`ra2rd/rd2ra`）、§4.1（`rd2rd`）、§4.2（`rb2rd/rd2rb/rb2rb`），均写「**源和目的范围可以重叠**；硬件按序号递增逐对处理，每对先读后写。」——与 `mreg_range_overlap`（`active`，2026-10-02 起）**矛盾**（`rd2rd`/`rb2rb` 同组；`ra2rd/rd2ra/rd2rb/rb2rd` 跨组、结构性不可能）。**本任务一并修正**（见 §2.4，须用户确认 R2）。

### 1.5 基线计数（`make check` EXIT=0，实测/台账）

M1 **152**、总记录 **227**、`rule_refs` 引用 **198**、规则 **18**（active 13 / deferred 5）、`check-spec-drift` 检查 **4** 合约、lit **26**、patches **67**、interface **80/80**、`check-scope` PASS（152/60/15）、`check-fp-contract` PASS。

---

## 2. 设计

### 2.1 删除 `fp_mreg_zero` / `fp_mreg_range_overflow`（裁定 1）

- 从 `contracts/legality_rules.yaml` **删除** L198–225 两条规则（规则 18→16）。
- 同步删除 `fp_semantics.yaml` 中 28 条对这些 id 的引用（改为 §2.2 的目标 id）。

### 2.2 扩充 `mreg_zero` / `mreg_range_overflow` / `mreg_range_overlap`（裁定 1/4/5）

三者的 `description` 与 `spec_cite` 扩充如下（**建议文本**，engineer 可按既有体例润色，但语义不得增减）：

**`mreg_zero`**（`spec_cite` 扩为多引用）
```yaml
  - id: mreg_zero
    fault: ILLI
    kind: static
    spec_cite: "SimRISC-01 §存取RD寄存器; SimRISC-01 §存取RF寄存器; SimRISC-02 §寄存器组之间块赋值; SimRISC-07 §格式转换指令; SimRISC-07 §浮点分类指令"
    status: active
    description: >
      多寄存器与块赋值指令 immu6=0 时触发 ILLI 异常。覆盖寄存器组：
      RD/RB：ldm.*/stm.*（RD、RB）、rd2rd/rb2rd/rd2rb/rb2rb；
      RA：ldm.o-ra/stm.o-ra、ra2rd/rd2ra；
      RF（scope: fp，共 28 条）：convert_ff（ft2ft/ft2fo/fo2ft/fo2fo）、
      convert_f2i（ft2it/ft2io/ft2ut/ft2uo/fo2it/fo2io/fo2ut/fo2uo）、
      convert_i2f（it2ft/io2ft/ut2ft/uo2ft/it2fo/io2fo/ut2fo/uo2fo）、
      classify（ftcls/focls）、RF 多寄存器存取（ldm.t/stm.t/ldm.o/stm.o）、
      RF↔RD 块赋值（rd2rf/rf2rd）。
      不适用于移位/扩展指令的立即数（orri）形式——其 immu6=0 是合法移位量/起始位；
      不适用于 root 的 immu6（其含义为 n，见 encode_fp_root_n）；
      不适用于单寄存器存取（ld.t/st.t/ld.o/st.o）与 set.w。
```

**`mreg_range_overflow`**（**源、目的都查**——裁定 4 是本条明确纠正点）
```yaml
  - id: mreg_range_overflow
    fault: ILLI
    kind: static
    spec_cite: "SimRISC-01 §存取RD寄存器; SimRISC-01 §存取RF寄存器; SimRISC-02 §寄存器组之间块赋值; SimRISC-07 §格式转换指令; SimRISC-07 §浮点分类指令"
    status: active
    description: >
      多寄存器/块赋值指令中任一起始寄存器 + immu6 > 64 时触发 ILLI 异常，不环绕、不截断；
      **源与目的起始寄存器均检查**。覆盖寄存器组：
      RD/RB：ldm.*/stm.*；块赋值目的 rdhb/rbhb 与源 rdhc/rbhc；
      RA：ldm.o-ra/stm.o-ra 目的/源、ra2rd、rd2ra；
      RF（scope: fp，共 28 条，清单同 mreg_zero）：目的起始（convert_ff/convert_i2f 的 rfhb、
      convert_f2i/classify 的 rdhb）与源起始（convert_ff/convert_f2i/classify 的 rfhc、
      convert_i2f 的 rdhc）**都检查**；ldm.*/stm.* 的 rfha、rd2rf 的 rfhb 与 rdhc、
      rf2rd 的 rdhb 与 rfhc 同样检查。
      不适用于 root 的 immu6（其含义为 n，且仅 n=2）、单寄存器存取与 set.w。
```

**`mreg_range_overlap`**（2 条 → 6 条，裁定 5）
```yaml
  - id: mreg_range_overlap
    fault: ILLI
    kind: static
    spec_cite: "SimRISC-02 §寄存器组之间块赋值; SimRISC-07 §格式转换指令"
    status: active
    description: >
      同寄存器组块赋值指令中，源范围与目的范围有任何交集（**含完全重合**）时触发 ILLI 异常。
      覆盖：rd2rd（rdhb↔rdhc）、rb2rb（rbhb↔rbhc）；
      以及 scope: fp 的 convert_ff 四条（ft2fo/fo2ft/ft2ft/fo2fo，rfhb↔rfhc）。共 6 条。
      跨组指令（ra2rd/rd2ra/rd2rb/rb2rd、rd2rf/rf2rd、convert_f2i、convert_i2f、classify）
      不适用——源与目的分属不同寄存器组，结构性不可能重叠。
```

> **关键不变量（裁定 4 的落地）**：`mreg_range_overflow` 的 FP 覆盖须**同时**含目的起始（`rfhb`/`rdhb`）与源起始（`rfhc`/`rdhc`）；不得复现 `fp_mreg_range_overflow` 只写目的侧或缺源侧的缺陷。验收以 §5 的反例（删除源侧覆盖→门控 FAIL）证伪。

### 2.3 `dst_rf0` 分类修正（裁定 2/3）

`dst_rf0`（`spec_cite` 补全）重构为四个清单，措辞按角色而非按指令：

- **适用（目的 rf0 → ILLI）**：`convert_ff`4 + `convert_i2f`8 + `arith`12 + `root`2 + `sign`4 + `cs_rf`5 = **35 条**（`cs_rf` 见 §0 R1；若用户裁定 cs_rf 整条不适用则 = 30，须全链同步）。
- **不适用（该指令无 rf 目的字段，rf 仅作源）**：`rf2rd`、`st.t/st.o`、`stm.t/stm.o`（`-rf`）。
- **例外（rf0 作目的合法）**：`rd2rf`（含 `{rf0:rf0+immu6-1}`）、`ld.t/ld.o/ldm.t/ldm.o`（按 FCSR 写掩码）、`set.w`。
- **源 rf0 合法（不触发本规则）**：上述各指令及 `cs.*-rf` 的 rf0-源角色（读出完整 64 位）。

`spec_cite` 补全为：
```
"SimRISC-00 §浮点寄存器; SimRISC-01 §存取RF寄存器; SimRISC-02 §寄存器组之间块赋值; SimRISC-02 §浮点条件赋值; SimRISC-03 §立即数常数赋值：Immediate constant"
```
（逐条来源：rf0 通用约束 SimRISC-00；RF 存取 SimRISC-01；块赋值/条件赋值 SimRISC-02；set.w SimRISC-03。）

### 2.4 规范正文修正（裁定 5）

1. **`spec/SimRISC-07 §格式转换指令`（L148）**：末句改为「**源范围与目的范围不可有任何交集（含完全重合），否则触发 ILLI 异常**（与 `SimRISC-02 §寄存器组之间块赋值` 一致）；无交集时按序号递增逐对进行、先读后写。」并在同节「限制」列表补一条同义条目。
2. **`spec/SimRISC-07 §浮点分类指令`（L257）**：因 `ftcls/focls` 为 rf→rd **跨组**，改为「来源为 `rf`、目的为 `rd`，分属不同寄存器组、结构性不可能重叠；分类按序号递增逐对进行。」
3. **`.tao/knowledge/contract-isa.md`（L375/L395/L413）**（须确认 R2）：
   - §4.1 L395（`rd2rd`）：改为「源范围与目的范围不可有任何交集（含完全重合），否则 → **ILLI**」并引 `[SimRISC-02 §寄存器组之间块赋值]`。
   - §4.2 L413（`rb2rb`/`rb2rd`/`rd2rb`）：`rb2rb` 同组⇒禁则；`rb2rd`/`rd2rb` 跨组⇒结构性不可能重叠。
   - §3.3.3 L375（`ra2rd`/`rd2ra`）：跨组⇒结构性不可能重叠。

> **不改**：`spec/SimRISC-02` 正文（L86 已正确，仅作对齐目标）；`spec/SimRISC-01 §存取RD寄存器` 的重叠表述（`ldm/stm` 非本规则覆盖，超出裁定范围）；`spec/SimRISC-0.5.3/**`、历史任务书、`adr-*`。

### 2.5 机器可读投影同步

- **`contracts/fp_semantics.yaml`**：
  - 28 条 `legality_refs`：`fp_mreg_zero → mreg_zero`、`fp_mreg_range_overflow → mreg_range_overflow`。
  - 4 条 `convert_ff`：追加 `mreg_range_overlap`（→ `[dst_rf0, mreg_zero, mreg_range_overflow, mreg_range_overlap]`）。
  - 保持 `scope: fp` 的 `opcodes.yaml` 记录 `rule_refs: []`（**不改 `opcodes.yaml`**）——遵守 `SPEC-086t` 口径（`scope != m1 ⇒ rule_refs=[]`）。
- **`.tao/knowledge/contract-fp.md`**：§2 L34、§9 L94、§12 L114 重叠表述改为禁则/结构性无重叠；§15 L131–136 重写为「FP 合法性引 `mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` + FP 专属 `dst_rf0`/`encode_fp_root_n`」，并注明共享规则同时服务 M1。
- **`tools/spec/check_fp_contract.py`**：
  - `FP_RULES = ("dst_rf0","encode_fp_root_n","mreg_zero","mreg_range_overflow","mreg_range_overlap")`（5 条，各须被 ≥1 条 FP id 引用）。
  - 新增 `FP_SPECIFIC_RULES = ("dst_rf0","encode_fp_root_n")`；L177–181 的「未被非 fp 记录引用」断言改为只对 `FP_SPECIFIC_RULES` 生效（`mreg_*` 被 M1 记录引用是**预期**）。
  - 建议把「≥1」收紧为**精确计数**：`mreg_zero` = 28、`mreg_range_overflow` = 28、`mreg_range_overlap` = 4、`dst_rf0` = 35（或 30，随 R1）、`encode_fp_root_n` = 2（用精确计数才能让「漏写源组/漏一条」可失败）。
  - docstring L12 同步。
- **`tools/spec/gen_legality_list.py`**：docstring L6「18 rules」→「16 rules」（非门控文案；`SPEC-087t` 同样处理过）。

### 2.6 计数变化（验收对照）

| 项 | 改前 | 改后 | 说明 |
|---|---|---|---|
| 规则总数 | 18 | **16** | 删 2 条 `fp_mreg_*`（deferred） |
| active（被引用/豁免） | 9 / 4 | **9 / 4** | 不变 |
| deferred | 5 | **3** | −2 |
| `指令引用` | 198 | **198** | `opcodes.yaml` 不动 |
| `check-fp-contract` FP 规则数 | 4 | **5** | +`mreg_range_overlap`，−2 FP 专属 |
| M1 / 总 / lit / patches / interface | 152 / 227 / 26 / 67 / 80 | **不变** | 不触编码与组件 |
| `check-spec-drift` 合约数 | 4 | **4** | 不新增 contract |
| `check-legality-drift` | 12 chapters | **12 chapters** | 生成区不变 |

---

## 3. 交付物与改动清单（逐文件）

| # | 文件 | 动作 |
|---|---|---|
| 1 | `contracts/legality_rules.yaml` | 删 `fp_mreg_zero`/`fp_mreg_range_overflow`；扩 `mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 描述与 spec_cite；`dst_rf0` 分类 + spec_cite 补全 |
| 2 | `contracts/fp_semantics.yaml` | 28 条 `legality_refs` 改 `mreg_zero`/`mreg_range_overflow`；`convert_ff` 4 条加 `mreg_range_overlap` |
| 3 | `.tao/knowledge/contract-fp.md` | §2/§9/§12 重叠表述 + §15 规则映射重写 |
| 4 | `.tao/knowledge/contract-isa.md` | L375/L395/L413 重叠表述（R2 确认后） |
| 5 | `spec/SimRISC-07-浮点运算.md` | §格式转换指令 L148、§浮点分类指令 L257 正文（仅正文，不动生成区标记） |
| 6 | `tools/spec/check_fp_contract.py` | `FP_RULES`/`FP_SPECIFIC_RULES`/精确计数/docstring |
| 7 | `tools/spec/gen_legality_list.py` | docstring 18→16 |
| 8 | `.tao/knowledge/{MEMORY,changelog,deferred}.md` | 由 `/complete` 追加（本任务不预填） |

**明确不改**：`contracts/opcodes.yaml`（**关键**，`rule_refs`/编码/`scope` 零改动）、`components/**`、`tests/**`、`tools/{llvm,qemu,testcases}/**`、`spec/SimRISC-02`、`spec/SimRISC-0.5.3/**`、历史任务书、`adr-*`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `contracts/{opcodes,legality_rules,fp_semantics}.yaml`
- `.tao/knowledge/{contract-fp,contract-isa}.md`、`spec/SimRISC-02`、`spec/SimRISC-07`
- `tools/spec/{check_rule_refs,check_fp_contract,gen_legality_list}.py`、`Makefile`
- 本任务书 §0 用户裁定

### 输出
见 §3 清单 1–7。

### 约束
- 中文；**不提交 git**；**不创建 ADR**（裁定 7）；只动任务书范围，越界须披露。
- **Spec-first**：所有规则/正文改动取自 `spec/`，不从实现反推。
- 遗留 `/tmp/opencode/SPEC-088t/`；日志 `.work/log/spec/SPEC-088t-*.log`；证据脚本 `.work/evidence/SPEC-088t/run.sh`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

> 通用：完成区贴**真实命令输出与退出码**；被检命令自身退出码须显式捕获（`cmd > log 2>&1; rc=$?`，禁 `cmd | tee log` 后取 `$?`）；复杂命令留 `.work/log/spec/SPEC-088t-*.log`；engineer 交付一键证据脚本 `.work/evidence/SPEC-088t/run.sh`（非交互、失败非零退出、逐项打印「检查名 + 期望/实际 + 退出码」、内置「注入反例→预期 FAIL→还原→回绿」自检或 `--inject`）。

1. **规则归并**：`legality_rules.yaml` 恰 **16 条**；`fp_mreg_zero`/`fp_mreg_range_overflow` **0 命中**；`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 描述含 §2.2 全部要点（含 `mreg_range_overflow` **源+目的**双侧）；`check-rule-refs` EXIT 0 且 `规则 16 条`、`指令引用 198 处`、active 9/豁免 4/deferred 3。
2. **FP 投影**：`fp_semantics.yaml` 60 条不变；`legality_refs` 中 `fp_mreg_*` 0 命中；`mreg_zero`/`mreg_range_overflow` 各被 **28** 条 FP id 引用，`mreg_range_overlap` 被 **4** 条引用，`dst_rf0`/`encode_fp_root_n` 计数与 §2.6 一致。
3. **门控可失败**：`make check-fp-contract` PASS；且 `check_fp_contract.py` 对 §6.1 反例 (a)–(f) 逐条真实 FAIL→还原→回绿（`git hash-object` 证明注入非空）。
4. **正文禁则**：`grep -n "不可有任何交集" spec/SimRISC-07-浮点运算.md` 命中 §格式转换指令；`grep "可以重叠" spec/SimRISC-07-浮点运算.md` **0 命中**；`contract-isa.md` L375/L395/L413 同类断言命中、旧句 0 命中。
5. **生成投影不回归**：`make check-legality-drift`（12 chapters OK）、`make check-asm-list-consistency`/`check-asm-list-drift`/`check-asm-prose` EXIT 0；`git diff -- spec/SimRISC-07` 仅正文行、markers 区零改；`gen_legality_list.py --verify` 12/12。
6. **关键计数不变**：`make check` EXIT 0；M1 152 / 总 227 / `rule_refs` 198 / lit 26 / patches 67 / interface 80 全不变；`validate-vectors 152/152`；`check-scope` PASS；`check-spec-drift` 4 合约。
7. **残留与越界**：`git status --untracked-files=all` 干净（除应改文件 + 本任务书）；`check-no-residue` PASS；`git diff --name-only` 与 §3 对齐（`opcodes.yaml`、`components/**`、`tests/**`、`tools/{llvm,qemu,testcases}/**` **不在 diff**）。
8. **`make check` 全绿**：`repository checks: PASS`。

### 6.1 反例注入（逐条须真实 FAIL→还原→回绿）

- (a) 从 `fp_semantics.yaml` 删除一条 `legality_refs` 中的 `mreg_zero` ⇒ `check-fp-contract` FAIL（精确计数 28→27）。
- (b) 把某条 `convert_ff` 的 `mreg_range_overlap` 删除 ⇒ FAIL（4→3）。
- (c) 在 `fp_semantics.yaml` 恢复一处 `fp_mreg_zero` 引用 ⇒ FAIL（`legality_refs 指向不存在的规则`）。
- (d) 在 `legality_rules.yaml` 重新加回 `fp_mreg_zero` ⇒ FAIL（规则数 16→17 或引用悬空；至少一条断言命中）。
- (e) 把 `mreg_range_overflow` 描述中的「源起始」句删掉（模拟 `SPEC-087t` 缺陷）⇒ **须**有一条门控/断言 FAIL（若现有门控测不到描述文本，则须在证据脚本中以 `grep` 断言补上，并说明其为文本级断言）。
- (f) 把 `SimRISC-07 §格式转换指令` 的禁则句改回「可以重叠」⇒ 证据脚本的正文 `grep` 断言 FAIL。
- **空注入防护**：每次注入后 `git diff --name-only` 非空 / `git hash-object` 变化；还原须复原原文并复核 blob 一致。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/SPEC-088t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律（本任务不改补丁，不适用）。
7. 复杂命令输出留存 `.work/log/spec/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/SPEC-088t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

| # | 风险/开放问题 | 影响 | 建议 |
|---|---|---|---|
| R1 | 裁定 2 把 `cs.*-rf` 整条列为「rf 仅作源，无 rf 目的字段」，但 spec SimRISC-02 §浮点条件赋值 / contract-fp §10 明确其 rf **目的**（rfHB/rfHC）为 rf0 ⇒ ILLI | `dst_rf0` 适用面 35→30、cs_rf 5 条失约束 | **用户拍板**：建议只把 `cs.*-rf` 的**源角色**标不适用，目的角色仍适用（本任务书已按此拟稿） |
| R2 | `contract-isa.md` L375/L395/L413 的重叠表述与 `mreg_range_overlap` 矛盾（历史遗留，`SPEC-061t/070t` 起） | 不改则 Task B 实现与合约自相矛盾 | **用户拍板**：建议纳入本任务（A）一并修正 |
| R3 | `dst_rf0`/`encode_fp_root_n` 是否翻 `active` | 维持 `deferred` 不影响 `check-rule-refs`（FP 记录 `rule_refs=[]`）；翻 active 会被 Gate2 判红 | 维持 `deferred`（同 `SPEC-087t` 口径），FP 实现期再翻 |
| R4 | 精确计数（28/28/4/35）是否收紧 | 收紧才能让「漏一条/漏源侧」可失败 | 建议收紧（§2.5） |
| R5 | 全量 `rule_refs` 是否扩展到 FP（改 `_compute_rule_refs`） | 会改变 `SPEC-086t` 口径与 198 计数、重生成 LEGALITY 区 | **不扩展**（遵守用户「勿破坏 SPEC-086t 口径」） |

### ADR 判断（须主动提醒）
- 判据核对：本任务为「把已生效的 `mreg_range_overlap` 覆盖扩到 FP」+「把 FP 与 SimRISC-02 对齐」，属既有决策的**范围外延/缺陷修复**，非新方向、非新跨组件合约（无新机器可读接口），**用户已裁定不立 ADR**（裁定 7）。
- **建议：不立 ADR**，理由与被否方案记入 `changelog`/任务书即可。若用户在确认时改判，则须补 ADR 并逐条确认 decision。

---

## 9. 与 `SPEC-086t`/`SPEC-087t` 的衔接（不改写历史）

- `SPEC-086t` 口径（`scope != m1 ⇒ rule_refs=[]`）**保持**；本任务只改 `fp_semantics.yaml` 的 `legality_refs`（第三类投影），不触 `opcodes.yaml`。
- `SPEC-087t` 的 `fp_mreg_zero`/`fp_mreg_range_overflow` 属**新增即缺陷**（漏源组、与 M1 规则重复），本任务删除并归并进 `mreg_*`；`SPEC-087t` 任务书「完成区/审阅记录」**不改写**，其历史结论（当时 `deferred` 合理）保持原样。
- 未来 FP 实现期翻 `active` + 回填 FP `rule_refs` 的衔接点（`SPEC-087t §9`、`deferred.md`）**仍有效**，本任务不关闭该衔接点。

## 完成区

**测试结果**：通过 8/8 验收项 + 7/7 反例注入（注入→预期 FAIL→还原→回绿）。一键证据脚本 `.work/evidence/SPEC-088t/run.sh`（默认 + `--inject` + `--full`）均 `EXIT=0`。

**修改文件**（7 个，与 §3 清单 1–7 逐条对齐；另加证据脚本，位于 git-ignored `.work/`）：
1. `contracts/legality_rules.yaml` — 删 `fp_mreg_zero`/`fp_mreg_range_overflow`（18→16）；扩 `mreg_zero`/`mreg_range_overflow`（源+目的双侧）/`mreg_range_overlap`（2→6）；`dst_rf0` 分类重构 + `spec_cite` 补全。
2. `contracts/fp_semantics.yaml` — 28 条 `legality_refs` 改 `mreg_zero`/`mreg_range_overflow`；4 条 `convert_ff` 加 `mreg_range_overlap`（`+28/-28` 行）。
3. `.tao/knowledge/contract-fp.md` — §2/§9/§12 重叠表述改禁则/结构性无重叠；§15 规则映射重写（5 规则，注明 `mreg_*` 与 M1 共享）。
4. `.tao/knowledge/contract-isa.md` — L375/L395/L413 改禁则/结构性无重叠。
5. `spec/SimRISC-07-浮点运算.md` — §格式转换指令末句 + 限制补禁则条；§浮点分类指令改结构性无重叠（仅正文，markers 区零改）。
6. `tools/spec/check_fp_contract.py` — `FP_RULES`（5 条）`FP_RULE_EXACT`（28/28/4/35/2 精确计数）`FP_SPECIFIC_RULES`；nonfp 断言收缩到专属规则；docstring 同步。
7. `tools/spec/gen_legality_list.py` — docstring `18 rules`→`16 rules`。
- 证据/日志：`.work/evidence/SPEC-088t/{run.sh,static_checks.py,mutate.py}`、`.work/log/spec/SPEC-088t-*.log`。

**验收结果**（真实命令 + 退出码；被检命令退出码经 `cmd > log 2>&1; rc=$?` 捕获）：

1. 规则归并：
```
$ python3 tools/spec/check_rule_refs.py
check-rule-refs: PASS (规则 16 条: active 被引用 9, active 豁免 4, deferred 3; 指令引用 198 处)
EXIT=0
```
`grep -c fp_mreg` 于 `legality_rules.yaml`/`fp_semantics.yaml` 均 0 命中。

2. FP 投影（`check-fp-contract`）：
```
[PASS] FP 规则被引用 dst_rf0: 期望=35 实际=35
[PASS] FP 规则被引用 encode_fp_root_n: 期望=2 实际=2
[PASS] FP 规则被引用 mreg_zero: 期望=28 实际=28
[PASS] FP 规则被引用 mreg_range_overflow: 期望=28 实际=28
[PASS] FP 规则被引用 mreg_range_overlap: 期望=4 实际=4
[PASS] legality_refs 均存在: 期望=0 实际=0
check-fp-contract: PASS
exit 0
```

3. 门控可失败（`run.sh --inject`，真实输出）：
```
── 反例 (a): 删一条 mreg_zero 引用（28→27）
  [PASS] 注入→FAIL (EXIT=1; 命中『FP 规则被引用 mreg_zero』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (b): 删一条 convert_ff 的 mreg_range_overlap（4→3）
  [PASS] 注入→FAIL (EXIT=1; 命中『FP 规则被引用 mreg_range_overlap』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (c): 复活一处 fp_mreg_zero 引用（悬空规则）
  [PASS] 注入→FAIL (EXIT=1; 命中『legality_refs 均存在』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (d): 重新加回 fp_mreg_zero 规则（16→17）
  [PASS] 注入→FAIL (EXIT=1; 命中『fp_mreg_* 规则 0 命中』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (e): 删 mreg_range_overflow 的源侧覆盖（模拟 SPEC-087t 漏源组）
  [PASS] 注入→FAIL (EXIT=1; 命中『含『源起始』』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (f): 把 SimRISC-07 禁则句改回「可以重叠」
  [PASS] 注入→FAIL (EXIT=1; 命中『『可以重叠』0 命中』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (g): 删 cs_rf 5 条的 dst_rf0 目的覆盖（35→30）
  [PASS] 注入→FAIL (EXIT=1; 命中『FP 规则被引用 dst_rf0』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
evidence: PASS
RUN_EXIT=0
```
（(d)(e)(f) 为**文本级 grep 断言**：既有门控不校描述文本/正文，故按任务书 §6.1(e) 在证据脚本以 `grep` 承担；各注入后 `md5sum` 变化、还原后 blob 一致。）

4. 正文禁则：
```
$ grep -n "不可有任何交集" spec/SimRISC-07-浮点运算.md
148:...源范围与目的范围不可有任何交集（含完全重合），否则触发 ILLI 异常...
$ grep -c "可以重叠" spec/SimRISC-07-浮点运算.md   # → 0
```
`contract-isa.md` 旧句「源和目的范围可以重叠」0 命中，L375/L395/L413 新句命中。

5. 生成投影不回归：
```
$ python3 tools/spec/gen_legality_list.py --verify     # 12/12 OK, EXIT=0
$ python3 tools/spec/check_legality_drift.py
check-legality-drift: 12 chapters OK
```

6. 关键计数不变（`make check` 日志）：
```
validate_vectors: 152/152 M1 identities covered OK
check-patch-tree: 2 component(s), 67 patches OK
总计: 80 项 | PASS: 80 | FAIL: 0
check-scope: PASS
── 结果: 检查 4 个合约，排除 2 个，错误 0 个 ──
Total Discovered Tests: 26 / Passed: 26 (100.00%)
check_rule_refs: 规则 16 条 ... 指令引用 198 处
```

7. 残留与越界：
```
$ git diff --name-only
.tao/knowledge/contract-fp.md
.tao/knowledge/contract-isa.md
contracts/fp_semantics.yaml
contracts/legality_rules.yaml
spec/SimRISC-07-浮点运算.md
tools/spec/check_fp_contract.py
tools/spec/gen_legality_list.py
```
`contracts/opcodes.yaml`、`components/**`、`tests/**`、`tools/{llvm,qemu,testcases}/**` 均不在 diff；`$ python3 tools/infra/check_dirs.py --residue` → `check-no-residue: PASS`。
`git diff -- spec/SimRISC-07-浮点运算.md` 仅 3 处正文行，生成区 markers 零改。

8. `make check` 全绿（`run.sh --full`）：
```
$ make check
repository checks: PASS
EXIT=0
```

**新发现/坑**（建议沉淀）：
- `SPEC-087t` 的 `fp_mreg_range_overflow` **只写目的侧、漏源侧**（QEMU 六条均为 `hb+hd>64 || hc+hd>64`）；本任务已归并进 `mreg_range_overflow` 并显式「源与目的起始寄存器均检查」，且以反例 (e) 证明「漏源侧」可被判出。
- `check-fp-contract` 的「FP 规则未被非 fp 记录引用」必须**收缩到 FP 专属规则**（`dst_rf0`/`encode_fp_root_n`）：`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap` 被 M1 的 `rule_refs` 引用是**预期**，否则改后必 FAIL（守 `SPEC-086t` 口径 `scope≠m1 ⇒ rule_refs=[]`，`opcodes.yaml` 零改动）。
- 「≥1」计数不足以捕获「漏一条/漏源侧」；改用**精确计数** 28/28/4/35/2 后，反例 (a)(b)(g) 才可失败。
- 描述文本/规范正文无法被既有机械门控覆盖，须由证据脚本的 `grep` 断言承担（反例 (d)(e)(f)），属**文本级**断言。
- `contracts/legality_rules.yaml` 头部注释「来源 SimRISC-00~04」在改动前已与既有 `SimRISC-06/07/11` 引用不符（历史遗留），本任务按外科手术式修改**未动**。

**遗留问题**：无未完成项。以下项**按任务书约定由 `/complete` 处理**，不计本任务遗留：`.tao/knowledge/{MEMORY,changelog,deferred}.md` 的追加（其中 `deferred.md` L55 仍以 `fp_mreg_*` 表述 FP 实现期待办，须在收尾时改为 `mreg_*` 口径）。`SPEC-087t` 任务书与「完成区/审阅记录」按 §9 **不改写**。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查全部 7 个改动文件 + 证据脚本。findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1（实现错误）：`fp_semantics.yaml` 首次 `replaceAll` 误将 12 条 `[dst_rf0, mreg_zero, mreg_range_overflow]`（convert_ff 4 + convert_i2f 8）全部加了 `mreg_range_overlap`；仅 `convert_ff` 4 条允许重叠 | ✅已修 | 先整体回退 12 条，再按 4 个 `convert_ff` id 逐一加 `mreg_range_overlap` | `git diff --stat` 显示 `+28/-28`；计数 `mreg_range_overlap=4`、`mreg_range_overflow=28`；`check-fp-contract` PASS |
| F2（覆盖缺口）：`mreg_range_overflow` 源侧、`dst_rf0` cs_rf 目的、正文禁则、`fp_mreg` 复活/规则数 均为**文本/结构**，`check_rule_refs`/`check_fp_contract` 单独测不到 | ✅已修（补断言） | `.work/evidence/SPEC-088t/static_checks.py` 增 16 条文本/计数断言；`run.sh --inject` 反例 (d)(e)(f)(g) 逐条证明可失败 | `run.sh --inject` 7/7 注入→FAIL→还原→回绿，`EXIT=0` |
| F3（口径风险）：若把「FP 规则未被非 fp 引用」保留给 `mreg_*`，改后必 FAIL | ✅已修 | 新增 `FP_SPECIFIC_RULES`，nonfp 断言仅对其生效 | `check-fp-contract` 的「FP 专属规则未被非 fp 记录引用: 期望=0 实际=0」PASS；`make check` EXIT=0 |
| F4（须核实）：`ldm.*` 允许 rf0 作目的、`mreg_range_overlap` 是否应含 `convert_f2i`/`classify` | ❌不修（已正确） | 不变 | `dst_rf0` 例外含 `ld.t/ld.o/ldm.t/ldm.o`；`convert_f2i`/`classify` 目的为 rd、跨组结构性不可重叠，`mreg_range_overlap` 仅 6 条（rd2rd/rb2rb + convert_ff 4） |

判决：全部 finding 已处置，无未修项 → 状态标「待验收」。

#### 第 1 轮 reviewer 验收

**审查方式**：审核证据脚本（`run.sh`/`static_checks.py`/`mutate.py`）→ 重跑默认模式 + `--inject` → 独立注入反例 → 逐项核对完成区。

##### 脚本审计结论

- **`run.sh`**：结构合理——默认跑 static_checks + 4 个门控；`--inject` 追加 7 个注入。`do_inject` 有备份/空注入检测（md5sum）/blob 一致性验证/还原确认。退出码捕获用 `cmd > log 2>&1; rc=$?`，未用 `tee` 吞码。✅
- **`static_checks.py`**：26 条断言，每条打印「检查名 + 期望/实际」，`_fail` 计数非零则 exit 1。断言覆盖：规则数 16、fp_mreg 0 命中、精确计数 28/28/4/35/2、mreg_range_overflow 源+目的双侧、mreg_range_overlap 含完全重合、dst_rf0 含 cs_rf 5 目的覆盖、SimRISC-07 禁则句/旧句 0 命中、contract-isa 新旧句、contract-fp 引 mreg_range_overlap、gen_legality_list docstring 16 rules。无恒真断言。✅
- **`mutate.py`**：7 个 case (a)-(g)，每个用 `_sub_once`（单次替换，assert 确认目标存在）。(e) 删「与源起始（」→「与（」使 static_checks 的「含『源起始』」FAIL；(g) 删5 条 cs_rf 的 `dst_rf0` 使计数 35→30 FAIL。均为非空注入、可达 FAIL 路径。✅

##### 重跑记录

**默认模式**（`run.sh`）：
```
══ 基础检查（静态断言 + 相关门控）══
  [PASS] static_checks (EXIT=0)
  [PASS] check-rule-refs (EXIT=0)
  [PASS] check-fp-contract (EXIT=0)
  [PASS] gen-legality-verify (EXIT=0)
  [PASS] check-legality-drift (EXIT=0)
evidence: PASS
EXIT=0
```

**注入模式**（`run.sh --inject`）：
```
══ 反例注入自检 ══
── 反例 (a): 删一条 mreg_zero 引用（28→27）
  [PASS] 注入→FAIL (EXIT=1; 命中『FP 规则被引用 mreg_zero』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (b): 删一条 convert_ff 的 mreg_range_overlap（4→3）
  [PASS] 注入→FAIL (EXIT=1; 命中『FP 规则被引用 mreg_range_overlap』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (c): 复活一处 fp_mreg_zero 引用（悬空规则）
  [PASS] 注入→FAIL (EXIT=1; 命中『legality_refs 均存在』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (d): 重新加回 fp_mreg_zero 规则（16→17）
  [PASS] 注入→FAIL (EXIT=1; 命中『fp_mreg_* 规则 0 命中』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (e): 删 mreg_range_overflow 的源侧覆盖（模拟 SPEC-087t 漏源组）
  [PASS] 注入→FAIL (EXIT=1; 命中『含『源起始』』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (f): 把 SimRISC-07 禁则句改回「可以重叠」
  [PASS] 注入→FAIL (EXIT=1; 命中『『可以重叠』0 命中』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
── 反例 (g): 删 cs_rf 5 条的 dst_rf0 目的覆盖（35→30）
  [PASS] 注入→FAIL (EXIT=1; 命中『FP 规则被引用 dst_rf0』)
  [PASS] 还原→回绿 (EXIT=0; blob 一致)
evidence: PASS
EXIT=0
```

**`make check` 全绿**：
```
validate_vectors: 152/152 M1 identities covered OK
check-patch-tree: 2 component(s), 67 patches OK
总计: 80 项 | PASS: 80 | FAIL: 0
check-scope: PASS
── 结果: 检查 4 个合约，排除 2 个，错误 0 个 ──
Total Discovered Tests: 26 / Passed: 26 (100.00%)
check_rule_refs: 规则 16 条 ... 指令引用 198 处
repository checks: PASS
EXIT=0
```

##### 约束核验

| 约束 | 结果 |
|---|---|
| 规则 16 条，fp_mreg_* 0 命中 | ✅ `grep -c fp_mreg` → 0；`grep -c '^- id:'` → 16 |
| mreg_range_overflow 源+目的双侧 | ✅ 描述含「源与目的起始寄存器均检查」「源起始」「目的起始」 |
| mreg_range_overlap 6 条（rd2rd/rb2rb + 4 FP convert_ff） | ✅ fp_semantics mreg_range_overlap=4 + legality_rules 描述列6 条 |
| dst_rf0: cs_rf 5 适用、rf2rd/st/stm 不适用 | ✅ cs_rf 5 在「适用」段；rf2rd/st/stm 在「不适用」段 |
| SimRISC-07 禁则句 + 旧句 0 命中 | ✅ L148「不可有任何交集」；`可以重叠`=0 |
| contract-isa.md L375/L395/L413 修正 | ✅ 旧「可以重叠」=0；新禁则/结构性不重叠命中 |
| 精确计数 28/28/4/35/2 | ✅ check_fp_contract.py FP_RULE_EXACT 逐条核对 |
| 152/227/198/26/67/80 不变 | ✅ make check 全绿 |
| check-scope PASS / check-legality-drift 12 OK | ✅ |
| git diff 仅 7 文件，无越界 | ✅ opcodes.yaml/components/tests/tools/{llvm,qemu,testcases} 不在 diff |
| git status 干净（除任务书+规划产物） | ✅ 仅 modified 7 文件 + untracked 任务书 |

##### 独立注入（reviewer 自选，不用脚本自带 (a)-(g)）

**注入点**：改 `tools/spec/check_fp_contract.py` 的 `mreg_range_overlap` 精确计数 4→5（被测产物之一）。

```
# 注入
$ sed -i 's/"mreg_range_overlap": 4/"mreg_range_overlap": 5/' tools/spec/check_fp_contract.py
$ git diff --name-only tools/spec/check_fp_contract.py
tools/spec/check_fp_contract.py
$ git hash-object tools/spec/check_fp_contract.py
79e529aa1c0b85d52c9b727ed6e34c7baa3e9d9a

# 重跑 → FAIL
$ python3 tools/spec/check_fp_contract.py
[FAIL] FP 规则被引用 mreg_range_overlap: 期望=5 实际=4
check-fp-contract: FAILED (1 项)
exit 1
EXIT=1

# 还原
$ sed -i 's/"mreg_range_overlap": 5/"mreg_range_overlap": 4/' tools/spec/check_fp_contract.py
$ diff /tmp/.../check_fp_contract_backup.py tools/spec/check_fp_contract.py
DIFF_EXIT=0  (与备份一致)

# 还原后回绿
$ python3 tools/spec/check_fp_contract.py
check-fp-contract: PASS
exit 0
EXIT=0

# git diff 不变（仍为 7 文件，无额外改动）
$ git diff --name-only
(7 文件，与注入前一致)
```

##### 完成区一致性核对

| 完成区声明 | reviewer 独立验证 | 一致？ |
|---|---|---|
| 规则 16 条，check-rule-refs PASS | ✅ 重跑 EXIT=0，输出一致 | ✅ |
| fp_mreg 0 命中 | ✅ grep 确认 | ✅ |
| 精确计数 28/28/4/35/2 | ✅ check_fp_contract 输出逐条一致 | ✅ |
| 7/7 注入 PASS | ✅ 重跑 EXIT=0，逐条一致 | ✅ |
| make check 全绿 | ✅ 重跑 EXIT=0，计数一致 | ✅ |
| git diff 7 文件 | ✅ 独立核对一致 | ✅ |
| F1 的 12 条 overlap 已收敛为 4 条 | ✅ fp_semantics mreg_range_overlap=4 | ✅ |
| F2 的文本级断言补齐 | ✅ static_checks.py 含 16 条文本/计数断言 | ✅ |
| F3 的 FP_SPECIFIC_RULES | ✅ check_fp_contract.py L73 仅含 dst_rf0/encode_fp_root_n | ✅ |
| F4 的 ldm 允许 rf0 / convert_f2i 不含 overlap | ✅ dst_rf0 例外含 ldm；mreg_range_overlap 仅 6 条 | ✅ |

**未发现不实/夸大**。完成区结论与 reviewer 独立验证逐条对齐。

##### 判决

**Accepted** —— 验收命令块在 reviewer 独立重跑下全部通过（默认 + `--inject` + `make check` + 独立注入）；7 项约束无违反；脚本审计合格（无恒真、FAIL 路径可达、注入非空可还原）；完成区与真实输出逐条对齐。
