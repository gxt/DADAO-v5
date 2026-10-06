# SPEC-065t 阶段 1 提案（确认门 ① 待裁定）

**来源**：architect 只读调研（2026-10-01），数据取自 `contracts/opcodes.yaml`（253 条）、`contracts/legality_rules.yaml`（25 条）、`spec/SimRISC-00~12`、`ADR-0012 D6/D7`、`tools/spec/check_asm_list_consistency.py`、`Makefile`。

---

## 1. 子类分解提案

### 1.1 一级（fault）× 二级（检查语义）二维表

| fault | 语义 | 规则 ID | kind | 涉及章 |
|---|---|---|---|---|
| **ILLI** | 目的寄存器约束 | `rd_dest_rd0` | static | 01–10 |
| | | `rb_dest_rb0` | static | 01, 05 |
| | | `rf0_as_dst` | static (deferred) | 07 |
| | | `dual_dest_both_rd0` / `dual_dest_same_reg` | static | 04, 08–10 |
| | | `ra2rd_dest_rd0` | static | 02 |
| | 操作数范围 | `imm_range`（通用） | static | 00 |
| | | `multi_immu6_zero` / `multi_range_overflow` | static | 01, 02 |
| | | `ra_multi_immu6_zero` / `ra_multi_range_overflow` | static | 01, 02 |
| | | `shamt_overflow` / `ext_bit_overflow` | static | 04, 08–10 |
| | 操作数组合 | `copy_range_overlap`（**新增**） | static | 02 |
| | 编码合法性 | `sbz_nonzero` | static | 00, 11（fence） |
| | | `reserved_undi`† | static | 00 |
| | | `cfx_reserved` / `lr_hb_not_zero` / `fp_root_invalid_n` / `fp_log_invalid_base` | static (deferred) | 07/11/12 |
| | 算术异常 | `div_by_zero` / `div_overflow` | **dynamic** | 04, 08–10 |
| **UNDI** | 编码合法性 | `reserved_undi`† | static | 00 |
| **MALIGN** | 数据对齐 | `data_malign` | **dynamic** | 01 |
| **IALIGN** | 指令对齐 | `instruction_align` | **dynamic** | 06 |
| **RASOF / RASUF** | 控制流 | `ras_of` / `ras_uf` | **dynamic** | 06 |

† `reserved_undi` 的 fault = UNDI（覆盖 QFC 空白单元格）；32 位全零 → ILLI（原专门非法指令；`ADR-0012 D3.5` 起该指令已删除、全零字为保留编码 → UNDI）。

### 1.2 各章「合法性检查」生成区排布序

| 章 | 顺序 |
|---|---|
| 01 | ILLI·目的寄存器 → ILLI·操作数范围 → MALIGN·数据对齐 |
| 02 | ILLI·目的寄存器 → ILLI·操作数范围 → ILLI·操作数组合 |
| 03 | ILLI·目的寄存器 |
| 04 / 08 / 09 / 10 | ILLI·目的寄存器 → ILLI·操作数范围 → ILLI·算术异常 |
| 05 | ILLI·目的寄存器 → ILLI·操作数范围 |
| 06 | IALIGN·指令对齐 → RASOF·控制流 → RASUF·控制流 |
| 07 | ILLI·目的寄存器（deferred）→ ILLI·操作数范围（deferred） |
| 11 | ILLI·编码合法性（SBZ） |
| 12 | ILLI·编码合法性（deferred） |

### 1.3 聚合分布（要点）

- **M1 中 `legality: []` 共 18 条**：`st.b`、10 条条件跳转、`jump`、`call`/`ret`、原专门非法指令（已删除）、`swym`（excluded_m1）。其合法性由**动态通用规则**覆盖（`instruction_align` IALIGN、`ras_of`/`ras_uf`），或 `rd0` 作**源**合法（ADR-0015 D2）。
- 各章命中规则密度（聚合）：01 章 `rd_dest_rd0`×16 + `multi_*`×8 + `ra_multi_*`×4 + `data_malign`×14；04/08/09/10 章 `rd_dest_rd0` + `dual_dest_*` + `shamt_overflow` + `ext_bit_overflow` + `div_*`；等等。

---

## 2. 映射设计（建议 (a)）

### 2.1 (a) vs (b)

| 维度 | **(a) opcodes 加 `rule_refs`** | (b) rules 加适用指令清单 |
|---|---|---|
| 一致性风险 | 新增指令时**必须**填 `rule_refs`（可强制非空校验） | 需回头更新多条规则，**易遗漏** |
| 初稿生成 | ✅ 可脚本化：现仅 **30 种唯一 legality 表达式** ⇒ 一次映射表即可批量回填 | 需对 25 条规则逐一扫 253 条指令 |
| 门控 | 正向（ID 存在）+ 反向（active 规则至少被 1 条引用） | 同理，方向相反 |
| 代价 | **159 条**有 legality 的指令需补字段（脚本初稿 + 人工复核 ~5 条歧义） | 25 条规则各列平均 ~10 条指令 |

**建议 (a)**：`rule_refs` 与 `legality` 同层、语义自包含；opcodes 是指令级数据的自然归属地；脚本化能力抵消表面条数差异。

### 2.2 字段形态

```yaml
- id: ld.ub_rrii_rd
  legality: [rdha != rd0]
  rule_refs: [rd_dest_rd0]      # 新增：可选 list[string]，缺失 = 未映射（门控报错）
  spec_cite: SimRISC-01 §存取RD寄存器
```

- 取值 = `legality_rules.yaml` 的 `id`。
- 语义 = **直接适用**规则；上级通用规则（如 `imm_range`）**不**逐条列出（在 SimRISC-00 通用规则处声明一次）。

### 2.3 初稿可行性

253 条共 **30 种唯一 legality 表达式** ⇒ 建一次映射表（如 `rdha != rd0`/`rdhb != rd0`/`rdhc != rd0` → `rd_dest_rd0`；`aligned(2|4|8)` → `data_malign`；`immu6 <= N` → 按 `shl./shr.` vs `ext.` 前缀区分 `shamt_overflow`/`ext_bit_overflow`；`immu6 != 0` → 按 `bank` 区分 `multi_*`/`ra_multi_*`；`no_overlap(...)` → `copy_range_overlap`；…），批量回填后人工复核 ~5 条歧义。

### 2.4 `legality: []` 的处理

- M1 的 18 条 → `rule_refs: []`（**合法**：无显式静态约束；IALIGN/RAS 为动态通用规则，不逐条引用）。
- 77 条 `excluded_m1` → `rule_refs` 空；生成区标注「excluded_m1: decode ILLI」，**不为** `decode: ILLI` 新建规则 ID。

### 2.5 两道门控判据（可失败）

1. **ID 存在性**：所有 `rule_refs` 的 id ∈ `legality_rules.yaml` 的 `id`。反例：加 `rule_refs: [nonexistent_rule]` → FAIL。
2. **孤儿规则**：每条 `status: active` 规则至少被 1 条指令引用。反例：新增 `active` 规则但无人引用 → FAIL。（`deferred` 允许 0 引用。）

---

## 3. 落差订正清单（4 项）

### 3.1 `copy_range_overlap`（**新增**，须用户确认拟文）

```yaml
- id: copy_range_overlap
  fault: ILLI
  kind: static
  spec_cite: "SimRISC-02 §寄存器组之间块赋值"
  status: active
  description: >
    同寄存器组块赋值指令中，源范围与目的范围有任何交集时触发 ILLI 异常。
    仅适用于 rd2rd（rdhb↔rdhc）与 rb2rb（rbhb↔rbhc）。
    跨组指令（ra2rd/rd2ra/rd2rb/rb2rd/rd2rf/rf2rd）不适用——
    源与目的在不同寄存器组，地址空间不重叠，覆盖为结构性不可能。
```

`kind: static`（与 `multi_range_overflow` 同口径）。影响：`legality_rules.yaml` 25 → **26** 条；`rd2rd`/`rb2rb` 的 `rule_refs` 新增该 id。

### 3.2 `set.w rf0` 例外 → **无实质落差，不改**

`rf0_as_dst`（description）已列 `set.w` 在「不在禁止清单」中；`set.w_rwii_rf` 为 `excluded_m1`、`legality: []` 正确。阶段 2 生成器渲染该规则时自动呈现例外列表。

### 3.3 `cs.*` 的 `rdHB` 可否为 `rd0` → **无落差，不改**

`cs.*_rd`（5 条）已带 `rdhb != rd0` / `rdhc != rd0`（命中 `rd_dest_rd0`）；`cs.*_rf`（5 条）为 `excluded_m1` ⇒ M2 激活时需补 `rf0_as_dst` 引用（记入生成器注释）。

### 3.4 块赋值跨组（`ra2rd` 等）→ **contracts 正确，不改**

`no_overlap(...)` 只在同组 `rd2rd`/`rb2rb` ✓；6 条跨组指令源目的异组，**结构性不可能**重叠 ⇒ 不加。spec SimRISC-02 行 66 的泛化措辞可优化，但**不纳入本阶段**。

---

## 4. 生成区落点与形态

- **落点**：`SimRISC-01 ~ 12`，位于 `<!-- ASSEMBLY_LIST_END -->` **之后**、正文（如「用户态指令」）**之前**，新增 `<!-- LEGALITY_START --> … <!-- LEGALITY_END -->`。**SimRISC-00 不加**（通用规则在各章交叉引用）。
- **渲染样例（SimRISC-02）**：

```markdown
<!-- LEGALITY_START -->
## 合法性检查

### ILLI — 目的寄存器约束
- `rd_dest_rd0`：cs.n/cs.z/cs.p（rd）目的 rdHB 不可为 rd0；cs.eq/cs.ne（rd）目的 rdHC 不可为 rd0
- `rb_dest_rb0`：rb2rb / rd2rb 目的 rbHB 不可为 rb0
- `ra2rd_dest_rd0`：ra2rd 目的 rdHB 不可为 rd0

### ILLI — 操作数范围
- `multi_immu6_zero` / `multi_range_overflow`：rd2rd/rb2rb/rb2rd/rd2rb
- `ra_multi_immu6_zero` / `ra_multi_range_overflow`：ra2rd/rd2ra

### ILLI — 操作数组合
- `copy_range_overlap`：rd2rd、rb2rb 源范围与目的范围有交集 → ILLI

> excluded_m1（cs.*-rf、rd2rf、rf2rd）：M1 范围外，decode ILLI
<!-- LEGALITY_END -->
```

- **隔离**：`gen_asm_list.py`（行 434–435）与 `check_asm_list_consistency.py`（行 31–32）**只管** `ASSEMBLY_LIST` 标记，与新标记**零耦合** ✓。

---

## 5. 门控 `check_legality_drift.py`

**判据**：① 加载 contracts（含 `rule_refs`）→ 内存生成各章预期内容；② 与 spec 实际 `LEGALITY` 区逐字比对；③ 附加两道门控（ID 存在性 / 孤儿规则）。**Exit 0** = 一致。

**三个可失败反例**：

| 反例 | 注入 | 预期 |
|---|---|---|
| A | 某指令 `rule_refs: [bogus_rule]` | FAIL（门控 1） |
| B | 删除 `rd_dest_rd0` 规则但保留引用 | FAIL（门控 1 + 2） |
| C | 手改任一 `LEGALITY` 区插入 `FAKE_RULE: …` | FAIL（内容不匹配） |

复原：`git checkout` 还原 → PASS（注入前须确认 `git diff` 非空）。

---

## 6. 分阶段实施计划（6 任务）

| 阶段 | 任务 | 内容 | 依赖 | 验收 |
|---|---|---|---|---|
| 1 | **SPEC-066t** | `legality_rules.yaml` 新增 `copy_range_overlap` | — | grep + 字段完整性 |
| 1 | **SPEC-067t** | `opcodes.yaml` 为 159 条补 `rule_refs`（脚本初稿 + 人工复核） | 066t | 门控 1/2 PASS；`validate_encoding.py` EXIT=0 |
| 1 | **SPEC-068t** | contracts 一致性终审（26 条规则全覆盖、159 条无遗漏、77 条 excluded 处理确认） | 067t | 双向门控 PASS + 抽检 10 条 |
| 2 | **SPEC-069t** | 编写 `tools/spec/gen_legality_list.py` | 068t | dry-run 人工确认 + 与现有手写内容比对 |
| 2 | **SPEC-070t** | 生成并注入 12 个 spec 文件的 `LEGALITY` 区 | 069t | `git diff` 只动生成区；`check-asm-list` 不受影响 |
| 2 | **SPEC-071t** | 编写 `check_legality_drift.py` + 接入 `make check` | 070t | 3 反例 FAIL + 复原 PASS；`make check` EXIT=0 |

依赖：`066t → 067t → 068t → 069t → 070t → 071t`；阶段 2 完成后进入**用户确认门 ②**（渲染物逐章确认）。

---

## 7. 待用户裁定（确认门 ①）

| # | 事项 | architect 建议 | 主会话意见 |
|---|---|---|---|
| 1 | 映射方案 | **(a) opcodes 加 `rule_refs`**（159 条补字段） | 同意 (a) |
| 2 | `copy_range_overlap` 拟文 + `kind: static` | 接受（25→26 条） | 同意 |
| 3 | `set.w rf0` | 无实质落差，不改 | 同意 |
| 4 | `cs.*` 的 rd0 口径 | 无落差，`cs.*_rf` 的 `rf0_as_dst` 引用留 M2 | 同意 |
| 5 | 块赋值跨组 | contracts 正确，spec 措辞优化不纳入本阶段 | 同意 |
| 6 | 生成区落点 | 紧邻 `ASSEMBLY_LIST_END` 之后、正文之前；SimRISC-00 不加 | 同意 |
| 7 | 任务拆分 | 阶段 1（066t–068t）+ 阶段 2（069t–071t） | 同意 |
