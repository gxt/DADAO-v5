# SPEC-086t: 浮点范围口径切换 —— `scope` 字段（m1|fp|excluded）与 FP 门控（试点）

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无硬依赖。相关基线（均**已验证**）：`SPEC-085t`（生成投影落位到 `.tao/knowledge/contract-asm-list.md`）、`INFRA-027t`（新增 `check-asm-list-drift` 门控）、`SPEC-069t`（当前 227=152+75 的编码表现状）。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 用户裁定（唯一真源，不得增删/更改）

以下为 2026-10-03 用户就「新增原生浮点指令支持」的**逐条裁定**，本任务书据此规划：

- **路线**：原生浮点指令（全工具链）；**否决** soft-float libcall（0628 路线）。
- **范围**：全量 **60 条**（`contracts/opcodes.yaml` 中 `excluded_m1` 且 `id` 以 `_rf` 结尾者；含运算 / RF 存取 / 转换搬移 / 符号位 / 条件赋值 / 比较 / 分类 / 开方）。
- **起点**：**contracts/spec 试点**（只做这一层，不铺开全程序）。
- **范围口径**：**新设独立范围**——FP **不再**作为 M1 身份、**不再**标 `excluded_m1`；**M1 门控口径保持不变并保持 `make check` 绿**；FP 另立范围/门控，可增量推进。
- **里程碑**：`M1→M2` 过渡任务（沿用 2026-09-25 约定，**不新建里程碑**，标 `**项目里程碑**：M1→M2`）。
- **ADR**：**不立**（理由写入任务书 + 后续 `changelog`；**不得**创建 ADR 文件）。

---

## 一、事实核实（本轮 architect 实测，作为任务前提；勿再转述，执行时以重跑为准）

### 1.1 计数与 FP 集合（`contracts/opcodes.yaml` 实测）

```
total 227  # M1 152 / excluded_m1 75 / 有 rule_refs 135
excluded_m1 且 id 以 _rf 结尾 = 60 条（= 用户裁定范围）
```

60 条的构成（`id` / `format` / `op`，含 `ha`）：

- **MISC-RF 子表 44 条**（`op=0x44`，SimRISC-00 §MISC-RF指令编码）：
  - orri 24 条：`ftcls/ft2fo/ft2ft/ftroot/focls/fo2ft/fo2fo/foroot`（ha 0x00/01/02/06/08/09/0A/0E）、`ft2it/ft2io/ft2ut/ft2uo`（0x30–0x33）、`it2ft/io2ft/ut2ft/uo2ft`（0x34–0x37）、`fo2it/fo2io/fo2ut/fo2uo`（0x38–0x3B）、`it2fo/io2fo/ut2fo/uo2fo`（0x3C–0x3F）
  - orrr 16 条：`ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb/ftsgnn/ftsgnj`（0x10–0x17）、`foadd/fosub/fomul/fodiv/forem/fosclb/fosgnn/fosgnj`（0x18–0x1F）
  - orrr 比较 4 条：`ftqcmp/ftscmp`（0x20/0x21）、`foqcmp/foscmp`（0x28/0x29）
- **RF 存取/搬移/条件赋值/比较 16 条**（分属其它章节）：
  - SimRISC-01（RF 存取，8 条）：`ld.t/st.t`（0x16/0x17）、`ld.o/st.o`（0x26/0x27）、`ldm.t/stm.t`（0x2E/0x2F）、`ldm.o/stm.o`（0x3E/0x3F）
  - SimRISC-03（立即数，1 条）：`set.w`（0x4F）
  - SimRISC-02（条件赋值/块赋值，7 条）：`cs.n/cs.z/cs.p`（0x61/0x63/0x65）、`cs.eq/cs.ne`（0x5E/0x5F）、`rd2rf`（ha 0x3D）/`rf2rd`（ha 0x3E）

**44 vs 60 的根源（必须讲清，范围口径才自洽）**：`spec/SimRISC-07-浮点运算.md` 只承载 **44 个助记符**（MISC-RF 子表的浮点运算/转换/比较/分类），故其头部标「44 条」；用户裁定范围 60 条 = 44（SimRISC-07）+ 16 条**分散在 SimRISC-01/02/03 的 RF 形态**（`ld/st/ldm/stm` 的 `-rf`、`cs.*-rf`、`rd2rf/rf2rd`、`set.w-rf`）。二者不是矛盾，而是**「浮点运算章」与「FP 范围」的口径差**。

### 1.2 `excluded_m1` 的产生与全部消费方（实测 file:line）

**产生**（`tools/spec/generate_opcodes.py`）：
- `L176–199 rec(..., excluded=False)`：`excluded=True` ⇒ `r["excluded_m1"]=True` + `r["decode"]="ILLI"`（L196–198）。
- 浮点族表 `_SPECIAL_IDS` L126–139（仅用于 id 解析，非 `excluded` 判据）。
- `build_misc_rf()` L627–674 全 44 条 `excluded=True`；另有 16 条散布在 L273–369/L386/L411–444/L483–517/L574–577。
- 计数/头注释 L763–778。

**消费 `excluded_m1 != true` 作为 M1 身份判据**（实测）：

| # | 文件 | 行 | 用法 |
|---|---|---|---|
| A1 | `tools/spec/generate_opcodes.py` | 733 | `_compute_rule_refs`：`if r.get("excluded_m1")` ⇒ `rule_refs=[]` |
| A2 | `tools/spec/generate_opcodes.py` | 763 / 771–777 | 计数（M1/excluded）+ 头注释 |
| B1 | `tools/testcases/validate_vectors.py` | 78–94 | `load_opcodes`：`m1 = [r for r in records if not r.get("excluded_m1")]`（M1 身份集/`by_id`） |
| B2 | `tools/testcases/validate_vectors.py` | 225–230 | 向量 `id` 必须 ∈ M1 身份集 |
| B3 | `tools/testcases/validate_vectors.py` | 284–313 | **R8 reserved 交叉校验**：遍历 `all_records`（**含** excluded），word 命中即 FAIL —— **须保持覆盖 FP 编码** |
| B4 | `tools/testcases/validate_vectors.py` | 645 | 重复 M1 id 检查 |
| B5 | `tools/testcases/validate_vectors.py` | 679–694 | inventory 行集 ↔ M1 身份集同步 |
| B6 | `tools/testcases/validate_vectors.py` | 763 | 汇总「M1 identities covered」 |
| C1 | `tools/testcases/generate_isa_vectors.py` | 26 / 39 | `M1 = [r for r in ALL if not r.get("excluded_m1")]` |
| C2 | `tools/testcases/generate_mem_vectors.py` | 43–44 / 58 | 同上 |
| C3 | `tools/testcases/generate_ctrl_br.py` | 31 | 同上 |
| C4 | `tools/testcases/generate_ctrl_jump_call_ret.py` | 43 | 同上 |
| C5 | `tools/testcases/generate_misc.py` | 19 / 148 | 注释「fence excluded_m1」 |
| C6 | `tools/testcases/test_anti_forgery_008t.py` | 95–96 | 反造假注入用例标签/word（含 `ld.t-rf`=excluded） |
| D1 | `tools/qemu/check_qemu_trans.py` | 90 / 99 / 108 / 113 | `is_m1`/`m1_total` 统计与标签 |
| D2 | `tools/qemu/check_005t_coverage.py` | 27–33 | `ILLI_INSTRUCTIONS` 集合注释（RF 条件赋值/立即数） |
| E1 | `tools/integ/check_interface_alignment.py` | 663–664 | `m1_count` ↔ inventory 交叉计数 |
| E2 | `tools/integ/check_interface_alignment.py` | 740–741 | `m1_formats`（lit format 族覆盖） |
| F1 | `tools/llvm/gen_asm_list.py` | 10 / 556 / 591–592 / 598 / 657 | 计数、`// excluded_m1` 注释 |
| F2 | `tools/llvm/gen_asm_list.py` | 193–197 / 452 | `DEFERRED_SECTIONS`（「浮点运算」章 deferred 标） |
| G1 | `tools/llvm/generate_instrinfo.py` | 7 / 34 | 只 emit M1 def |
| G2 | `tools/llvm/validate_instrinfo.py` | 12 / 54 / 60 | 断言 excluded 不定义 |
| G3 | `tools/llvm/gen_m1_asm.py` | 179 | 取 M1 |
| H1 | `tools/spec/gen_legality_list.py` | 156 / 210–215 | LEGALITY 区「excluded_m1（decode ILLI）」附注 |
| H2 | `tools/spec/check_qfc_coverage.py` | 357–358 / 375–380 | `yaml_excl` 集合（standalone，非 `make check`） |
| I1 | `tests/vectors/inventory.md` | 13–16 | M1 覆盖矩阵标题/谓词表述（计数已为 152） |
| I2 | `tests/vectors/README.md` / `schema.md` | 9–10 / 202–203 | M1 scope 判据表述（**已陈旧：写 177，实为 152**） |

**spec 侧现状**：
- `spec/SimRISC-07-浮点运算.md` L4 头部 `分类：浮点运算 [deferred]（44 条）`；L9 为生成区（`gen_asm_list` 的 `DEFERRED_SECTIONS` 决定 `**deferred**` 标）；L64 为生成区（`gen_legality_list` 的 `**excluded_m1（decode ILLI）：**`）。
- 生成区 `excluded_m1（decode ILLI）：` 分布：`SimRISC-01` L63（8 条 fp）、`SimRISC-02` L43（7 条 fp）、`SimRISC-03` L30（1 条 fp）、`SimRISC-07` L64（44 条 fp）、`SimRISC-11` L26（4 条 excluded）、`SimRISC-12` L31（11 条 excluded）——**恰好 60 fp + 15 excluded = 75**。
- `SimRISC-00`：§浮点寄存器（L82–124，rf0/FCSR 位布局）、§MISC-RF指令编码（L375–388，44 条编码权威表）、L255 `MISC-RF … Excluded from M1`。
- `spec/Toolchain-01-汇编语言.md`：L5（`227 条…浮点与待定两章整章 deferred`）、L42（`RF 属 Excluded from M1`）、L151、L221（`152 条 M1`）。
- `contracts/opcodes.yaml` 头部 L1–7：`共 227 条：M1 内 152 条，excluded_m1 75 条；有 rule_refs 135 条`。

### 1.3 基线可复现性（实测）

- `generate_opcodes.py` 重生成**逐字节可复现**：`diff contracts/opcodes.yaml <重生成> → DIFF_EXIT=0`（回应 `SPEC-067t` 时期登记的「16 条 legality 漂移」既有债务，**现已消解**）。
- `make check` 基线 **EXIT=0**（`repository checks: PASS`；lit 26/26；`validate_vectors 152/152`；`check_qemu_trans 227/227 (M1 152/152)`；`check_interface_alignment 80/80`；`validate_encoding 227 OK`；`check_rule_refs PASS（16 规则，198 引用）`）。日志：`.work/log/spec/SPEC-086-plan-make-check.log`。

### 1.4 任务粒度建议

**建议：本试点 1 个任务（`SPEC-086t`），原子交付。**

理由：
1. **口径切换必须原子**——一旦 `opcodes.yaml` 去掉 `excluded_m1`，所有 `not excluded_m1` 谓词立即把 FP 计入 M1（152→212），若不同一提交迁移消费方，`make check` 立刻变红。用户要求「保持绿」，故谓词迁移 + 重生成 + 新门控只能同一提交。
2. 工作量是**机械映射**（约 20 处谓词 + 2 个生成器 + 2 份生成物重跑），非语义新写，单 engineer 可在一次任务内完成并自审。
3. 可拆点仅有一处：**新门控 `check-scope` 可作独立小任务**，但那样 FP 范围在两次任务之间**无门控保护**（且用户要求本试点给出「守 FP 范围的门控」）。故并入本任务。

> 若用户希望缩小单次改动，备选粒度：`SPEC-086t` = 口径切换 + 迁移（建门控开关但暂不接入 `make check`）；`SPEC-087t` = `check-scope` 接入 `make check` + 反例。**不推荐**（中间态无保护，且两任务共享 `Makefile` 须串行）。

---

## 2. 新范围口径设计方案（≥2 备选 + 取舍）

### 2.1 目标（口径须同时满足）

1. `scope` 与既有 M1 门控**解耦**：FP 不属于 M1、也不属「excluded」。
2. M1 身份谓词切换后，**M1 计数恒为 152**（门控口径不变）。
3. 「FP 已定义但未实现 ⇒ 解码仍 ILLI」语义**不丢**。
4. 「reserved-word 交叉校验仍覆盖 FP 编码」语义**不丢**（R8 遍历全部记录）。
5. FP 可**增量推进**（将来实现时把 `scope: fp` 的记录翻成已实现，而不触碰 M1 口径）。

### 2.2 备选方案

**方案 A（推荐）— 用 `scope` 枚举取代 `excluded_m1`**

- `opcodes.yaml` **每条记录**新增 `scope` 字段，取值 `m1 | fp | excluded`（互斥、穷尽）：
  - `m1` = 152；`fp` = 60；`excluded` = 15（cfx 6：`cfx2rd/cfx2rc/cfxld/cfxst/escape/trap`；LR-SC 8；`fence` 1）。
- 删除 `excluded_m1` 字段。`decode: ILLI` 保留，且约定 **`scope != m1` ⇒ `decode: ILLI`**（UNDI 仍仅用于空白单元格=无记录）。
- 谓词映射：`not r.get("excluded_m1")` → `r.get("scope") == "m1"`；`r.get("excluded_m1")`（=非 M1）→ `r.get("scope") != "m1"`。
- 优点：单一正交轴；精确落实用户裁定；计数可派生（227=152+60+15）；迁移机械、可 grep 穷尽；未来可扩展 `scope: m2` 等。
- 代价：`opcodes.yaml` 每条 +1 行（227 行，生成物，可接受）；约 20 处消费方谓词需迁移（本任务核心工作量）；既有文档/ADR 中 `excluded_m1` 字样成为历史（不改写历史）。

**方案 A′ — `scope` 仅标注非 M1 记录（缺省 = m1）**

- 只有 75 条非 M1 记录带 `scope: fp|excluded`；M1 记录不带。谓词 = `r.get("scope") is None`（或缺省 `"m1"`）。
- 优点：`opcodes.yaml` diff 更小（75 处 vs 227 处）。
- **否决理由**：`缺省 = m1` 是**静默默认**——字段拼写错误/漏写会把记录**静默升级为 M1**，违反项目「无静默缺席」原则，且新门控无法区分「有意缺省」与「笔误」。

**方案 B — 保留 `excluded_m1` 语义不动 + 另加正交字段 `family: fp`**

- FP 记录仍 `excluded_m1: true`，再加 `family: fp`；M1 谓词 `not excluded_m1` **完全不变**（迁移量为 0，`make check` 天然绿）。
- **否决理由**：直接**违反用户裁定**「FP **不再**标 `excluded_m1`」；且保留两个重叠概念（`excluded_m1` 表 M1 排除、`family` 表范围），口径不自洽，FP 仍被永久标记为「被排除」而非「独立可推进范围」。

**方案 C — `implemented: false` + `family: fp`（两字段替代一布尔）**

- 与 B 等价、字段更多。**否决**：无额外收益，字段耦合更差。

### 2.3 取舍与推荐

**推荐方案 A**。关键取舍：

| 维度 | A | A′ | B |
|---|---|---|---|
| 满足「不再标 excluded_m1」 | ✅ | ✅ | ❌ |
| 满足「M1 计数不变 152」 | ✅（谓词迁移后） | ✅ | ✅ |
| FP 独立可推进 | ✅ | ✅ | 部分 |
| 静默默认风险 | 低（强制字段） | **高** | 低 |
| 迁移量 | 中（~20 处） | 中 | 0 |
| 新门控可机械守 FP | ✅ | 弱 | 弱 |

**命名**（待在任务书确认时由用户拍板）：字段名 `scope`；取值 `m1 | fp | excluded`。备选命名：`range` / `m1_scope`；取值 `core | fp | excluded`。本任务书统一用 `scope`。

---

## 3. 改动清单（逐文件、逐消费方，含 file:line）

> 分类：**① 本试点核心交付（spec 层）**、**② 必须同一提交（否则 `make check` 变红）**、**③ 一致性迁移（非 `make check` 门控，但留悬空谓词会误导，建议同提交）**、**④ 规范正文/投影/文档口径**、**⑤ 不得改写 / 需用户裁定**。

### ① 本试点核心交付

| 文件 | 位置 | 现状 | 目标 |
|---|---|---|---|
| `tools/spec/generate_opcodes.py` | 176–199 | `rec(..., excluded=True)` → `excluded_m1`+`decode` | 改 `rec(..., scope="m1")`；非 m1 传 `scope`；`scope != m1` 时 `decode: ILLI` |
| 同上 | 273–277、309–313、325–330、364–369 | 8 条 RF 存取 `excluded=True` | `scope="fp"` |
| 同上 | 386–387 | `set.w-rf` | `scope="fp"` |
| 同上 | 411–418 | `cs.eq/cs.ne-rf` | `scope="fp"` |
| 同上 | 425–444 | `cs.n/cs.z/cs.p-rf` | `scope="fp"` |
| 同上 | 483–494 | `cfx2rd/cfx2rc/cfxld/cfxst/escape/trap` | `scope="excluded"` |
| 同上 | 503–505 | `fence` | `scope="excluded"` |
| 同上 | 510–517 | `lr_*/sc_*`（8） | `scope="excluded"` |
| 同上 | 574–577 | `rd2rf/rf2rd` | `scope="fp"` |
| 同上 | 627–674 | `build_misc_rf` 44 条 | `scope="fp"` |
| 同上 | 733 | `if r.get("excluded_m1")` | `if r.get("scope") != "m1"` |
| 同上 | 763–778 | 计数/头注释（M1/excluded） | `M1 {n_m1} + scope fp {n_fp} + scope excluded {n_ex}` |
| 同上 | 1–12 | docstring 说明 | 改述 `scope` 语义 |
| `contracts/opcodes.yaml` | 全部 227 | 75×`excluded_m1: true` | 227×`scope`（152 m1 / 60 fp / 15 excluded）；头部 L1–7 重写 |
| `tools/spec/check_scope.py` | 新建 | — | scope 分区门控（见 §5.3） |
| `Makefile` | 38–45（`.PHONY`）、221（`check` 列表）、新增 target | — | 增 `check-scope` 并接入 `make check` |

### ② 必须同一提交（否则 `make check` 变红）

| 文件 | 行 | 现状 | 目标 | 关联门控 |
|---|---|---|---|---|
| `tools/testcases/validate_vectors.py` | 78–94、225–230、645、679–694、763 | M1=`not excluded_m1` | `scope=="m1"`；汇总文案 | `validate-vectors` |
| `tools/testcases/validate_vectors.py` | 284–313 | **R8 遍历 `all_records`（含 excluded）** | **保持遍历全部记录**（只更新 L308 报错文案为 `scope=…`） | 同上（语义不丢） |
| `tools/qemu/check_qemu_trans.py` | 90、99、108、113 | `is_m1`/`m1_total` | `scope=="m1"`、标签 | `check-interface`（调用 `--strict`） |
| `tools/integ/check_interface_alignment.py` | 663–664、740–741 | `m1_count` / `m1_formats` | `scope=="m1"` | `check-interface` |
| `tools/llvm/gen_asm_list.py` | 10、193–197、452、556、591–592、598、657、660–661 | 计数、`// excluded_m1`、`DEFERRED_SECTIONS` 标 | 计数改三分类；注释改 `scope`；`浮点运算` 章标改新口径（见 §4.1） | `check-asm-list` / `check-asm-list-drift` |
| `.tao/knowledge/contract-asm-list.md` | 全文生成 | 头 `227 条 = M1 152 + excluded_m1 75` | 重生成（逐字节一致） | `check-asm-list-drift` |
| `tools/spec/gen_legality_list.py` | 156、210–215 | `excluded_m1（decode ILLI）：` 附注 | 按 scope 分节：`scope: fp`（decode ILLI） / `scope: excluded`（decode ILLI） | `check-legality-drift` |
| `spec/SimRISC-01/02/03/07/11/12` | LEGALITY 生成区（63 / 43 / 30 / 64 / 26 / 31） | `excluded_m1` 附注 | 重生成（`gen_legality_list.py --apply`） | `check-legality-drift` |
| `spec/SimRISC-01..12` | ASSEMBLY_LIST 生成区 | deferred 标 | 重生成（`gen_asm_list.py --embed-spec`） | `check-asm-list-consistency` |
| `tests/vectors/inventory.md` | 13–16 | 「M1 身份集 = `excluded_m1 != true`」表述、标题 | 表述改 `scope == m1`；标题保持「M1 覆盖矩阵（152 条）」 | `validate-vectors` + `check-interface` |

> **R8 是不可丢语义之一**：`validate_vectors.py` 的 reserved-word 交叉校验**必须继续遍历全部记录**（含 `scope: fp`），否则 FP 编码会被误判为「空白单元格」而允许标 `reserved`。迁移时**只改谓词处，不动 `all_records` 的返回与遍历**。

### ③ 一致性迁移（非 `make check` 门控；建议同提交，避免悬空谓词）

| 文件 | 行 | 目标 |
|---|---|---|
| `tools/testcases/generate_isa_vectors.py` | 26、39 | `scope=="m1"` |
| `tools/testcases/generate_mem_vectors.py` | 43–44、58 | `scope=="m1"` |
| `tools/testcases/generate_ctrl_br.py` | 31 | `scope=="m1"` |
| `tools/testcases/generate_ctrl_jump_call_ret.py` | 43 | `scope=="m1"` |
| `tools/testcases/generate_misc.py` | 19、148 | 注释改 `scope: excluded`（fence） |
| `tools/testcases/test_anti_forgery_008t.py` | 95–96 | 注入标签 `R8/excluded` → `R8/scope-excluded`（`ld.t-rf` 现属 `scope: fp`，标签须同步） |
| `tools/qemu/check_005t_coverage.py` | 27–33 | 注释「RF … excluded_m1」→「`scope: fp`」（集合内容不变，仍应 ILLI） |
| `tools/spec/check_qfc_coverage.py` | 357–358、375–380 | `yaml_excl` = `scope != m1`（standalone） |
| `tools/llvm/generate_instrinfo.py` | 7、34 | `scope=="m1"` |
| `tools/llvm/validate_instrinfo.py` | 12、54、60 | `scope=="m1"`；断言改「非 m1 不定义」 |
| `tools/llvm/gen_m1_asm.py` | 179 | `scope=="m1"` |

> 跨模块提示：③ 中 `tools/llvm/*` 属 llvm 模块、`tools/qemu/*` 属 qemu 模块、`tools/testcases/*` 属 testcases 模块；本任务作为 spec 任务**越界修改**须在完成区显式披露。若不改，这些工具会静默把 FP 当 M1（埋雷）。

### ④ 规范正文/投影/文档口径（口径同步）

| 文件 | 位置 | 目标 |
|---|---|---|
| `spec/SimRISC-07-浮点运算.md` | L4 | 头部 `[deferred]（44 条）` → 新口径（见 §4.1） |
| `spec/SimRISC-07-浮点运算.md` | 新增注 | 「FP 范围总账」：`scope: fp` 共 60 = 本册 44 + SimRISC-01（8）/02（7）/03（1）的 16 条 RF 形态 |
| `spec/SimRISC-00-指令系统设计.md` | 255、281、375–388 | MISC-RF 子表/指针处标注 `scope: fp`；rf0/FCSR 定义（L82–124）保持（语义依据） |
| `spec/Toolchain-01-汇编语言.md` | 5、42、151、221 | `227`/`deferred`/`Excluded from M1`/`152` 措辞对齐新口径 |
| `spec/README.md` | 72–73、80 | 投影表 `③机械门控` 列补 `tools/spec/check_scope.py`（`SimRISC-00` 行 / `SimRISC-01…12` 行） |
| `.tao/knowledge/contract-isa.md` | 7、25、48–86、821–828、1115–1147、1399–1420 | §9 标题/范围由「Excluded from M1」→「`scope: fp`（未实现，decode ILLI）」；§14 保持 excluded；A.7 清单按 scope 分类 |
| `tests/vectors/README.md` | 9–10 | 判据 → `scope == m1`；**陈旧 177 → 152** |
| `tests/vectors/schema.md` | 202–203 | 同上 |
| `docs/README.md` | 17 | 核对（deferred 44/11、172 条**不变**；如含 `excluded_m1`/`75` 字样则同步） |
| `docs/impact-matrix.md` | 120、155、156、170 | `excluded_m1` → `scope` |
| `docs/m1-retrospective.md` | 356 | `excluded_m1` 描述 |
| `docs/m2-spec-planning.md` | 103 | 「excluded_m1」措辞（讨论稿） |
| `docs/spec/assembly-language.md` | 5 | 计数 251→227（若仍陈旧） |
| `.tao/knowledge/{MEMORY.md,deferred.md,changelog.md}` | — | 由 `/complete` 追加（本任务不预填） |

### ⑤ 不得改写 / 需用户裁定

| 对象 | 原因 |
|---|---|
| `.tao/adr/adr-0014-fence-excluded-m1.md`（全文含 `excluded_m1` 字样） | Accepted ADR 决策快照；按 `AGENTS.md`「已 Accepted ADR 改动 decision 须逐条经用户确认」，**不得静默改写**。登记为用户裁定项 |
| `docs/issues.yaml` 416–421、`.tao/knowledge/deferred.md` 40/43/144/148 | 历史台账行（`ISS-056` 语境）；按体例不改写正文，可加注 |
| `spec/SimRISC-0.5.3/**`、旧任务书、`.tao/knowledge/changelog.md` 历史行 | 历史，锁定/体例不改 |
| `components/llvm-project/patches/**`、`components/qemu/patches/**`、`tests/lit/**`、`tests/vectors/isa/*.yaml` | **本试点不含 LLVM/QEMU/向量实现**——不新增 FP def / trans / 向量 |

---

## 4. spec 侧改动细则

### 4.1 `SimRISC-07` 的 `[deferred]` 标注如何改为新口径

当前 `[deferred]` 把**状态（未实现）**与**范围归属**混在一起。新口径下二者**正交**：`scope: fp` = 范围归属；`deferred/未实现` = 状态。**推荐（最小改动 + 显式口径）**：

- 头部 L4：`> **分类：浮点运算 [deferred]**（44 条）` → `> **分类：浮点运算 [scope: fp]（44 条；未实现，decode ILLI）** — …`（保留「未实现」语义，去掉 `deferred` 与 `excluded_m1` 混用）。
- 生成章标题（`gen_asm_list.py` L452 / `DEFERRED_SECTIONS`）：`### 浮点运算（44 条）｜ **deferred** — 待浮点专门任务` → `### 浮点运算（44 条）｜ **scope: fp（未实现，decode ILLI）** — 待浮点专门任务`。
- `待定` 章（SimRISC-12，11 条 `scope: excluded`）保持 `**deferred**`（确属未归类）。
- LEGALITY 生成区 `**excluded_m1（decode ILLI）：**` → 拆两节：
  - `**scope: fp（decode ILLI，未实现）：**`（SimRISC-01/02/03/07 的 60 条）
  - `**scope: excluded（decode ILLI）：**`（SimRISC-11/12 的 15 条）

> 备选最小方案（备用）：保留 `deferred` 字样作为状态，仅在 FP 章标题后追加 `（scope: fp）`。**推荐上述替换**，因用户明确要求「`[deferred]` 标注改为新口径」。

### 4.2 `SimRISC-00` / `Toolchain-01` 计数与投影同步

- `SimRISC-00`：MISC-RF 子表（L375–388）与主表指针（L281）标注该子表 `scope: fp`；rf0/FCSR 位布局（L82–124）**不动**（FP 语义依据，且 `SPEC-060t` 已定稿）。L255 「`MISC-RF … Excluded from M1`」→「`scope: fp`（未实现，decode ILLI）」。
- `Toolchain-01`：L5 「浮点与待定两章整章 deferred」→ 保留（状态描述仍成立）+ 注明 FP 为 `scope: fp`；L42 「RF 属 Excluded from M1」→「RF 属 `scope: fp`」；L221 `152 条 M1` 不变（口径切换后 M1 仍 152）。
- `spec/README.md` 投影表：两行的 ③机械门控列补 `check_scope.py`；`SimRISC-07` 行的 ②机器数据已含 `contracts/opcodes.yaml`。

### 4.3 生成器与生成物重生成

| 生成器 | 重生成产物 | 门控 |
|---|---|---|
| `tools/spec/generate_opcodes.py` | `contracts/opcodes.yaml` | `validate-encoding`、`check-rule-refs`、`validate-vectors`、`check-interface` |
| `tools/llvm/gen_asm_list.py`（默认） | `.tao/knowledge/contract-asm-list.md` | `check-asm-list-drift` |
| `tools/llvm/gen_asm_list.py --embed-spec` | `spec/SimRISC-01..12` 的 ASSEMBLY_LIST 区 | `check-asm-list-consistency` |
| `tools/spec/gen_legality_list.py --apply` | `spec/SimRISC-01..12` 的 LEGALITY 区 | `check-legality-drift` |

> 顺序：先改两个生成器源码 → 重生成 opcodes.yaml → 再重生成三处投影。全部生成物**勿手工编辑**。

---

## 5. 门控影响与「保持绿」的验证方式

### 5.1 `make check` 各子项：改动后应**恰好不变**的计数

| 门控 | 期望值（改动后必须与改动前一致） |
|---|---|
| `manifest-check` | PASS |
| `validate-vectors` | `152/152 M1 identities covered OK`，`gaps 0`，EXIT 0 |
| `check-spec-drift` | 不变 |
| `check-patch-tree` | 67 patches OK（未动 `components/`） |
| `check-asm-list` / `check-asm-list-drift` | EXIT 0（**内容**变化、**结果**绿） |
| `check-asm-prose` | EXIT 0 |
| `check-legality-drift` | EXIT 0（内容变化、结果绿） |
| `check-interface` | `80/80`；`opcodes.yaml 条目数：总计 227, M1 内 152`；`QEMU trans 227/227 (M1 152/152)` |
| `validate-encoding` | `227 条记录 OK` |
| `check-rule-refs` | `16 条规则; 指令引用 198 处`（FP 无 legality ⇒ 引用数不变） |
| `check-qemu-semantics` | 不变（仅 M1 向量） |
| `check-cfx-aliases` | 不变 |
| `check-dirs` / `check-no-residue` | EXIT 0 |
| `check-lit` | 26/26 |
| `check-issues` | 0 blocking M1-gate |
| **新增 `check-scope`** | EXIT 0（见 §5.3） |

**应保持不变的关键常量**：M1 身份 **152**、总记录 **227**、`rule_refs` 指令数 **135** / 引用 **198**、lit **26**、patches **67**、interface **80/80**。**预期变化**：`opcodes.yaml` 增 `scope`（删 `excluded_m1`）、`contract-asm-list.md` 头注、LEGALITY 区附注、`SimRISC-07` 章标题。

### 5.2 「保持绿」的验证方式（真实命令 + 真实退出码）

```bash
# 基线（改动前）
make check > .work/log/spec/SPEC-086t-make-check-before.log 2>&1; echo "EXIT=$?"

# 改动 + 重生成后
make check > .work/log/spec/SPEC-086t-make-check-after.log 2>&1; echo "EXIT=$?"
```

- 逐项对比 before/after 的关键行（M1 152、227、198、26/26、80/80、67）。
- `make check` 内已含 `check-lit`/`check-qemu-semantics`，**不得**以「只跑子集」代替（除非环境缺 build，须按 `AGENTS.md` 申报替代证据）。

### 5.3 新增门控 `tools/spec/check-scope.py`（守 FP 范围）

**职责**（可执行、可失败）：

1. `opcodes.yaml` 每条记录**恰有** 1 个合法 `scope` ∈ {`m1`,`fp`,`excluded`}（缺失/非法 ⇒ FAIL）。
2. **分区计数**：`m1 == 152`、`fp == 60`、`excluded == 15`、`total == 227`（任一不符 ⇒ FAIL）。
3. `scope != "m1"` ⇒ `decode == "ILLI"`；`scope == "m1"` ⇒ 不得有 `excluded_m1`/`decode: ILLI`（防回退）。
4. **FP 结构判据**：`scope == "fp"` ⇔ `id.endswith("_rf")`（结构性定义，可机械核对；60 条清单由 spec/契约派生，**不从实现反推**）。
5. 断言旧字段 `excluded_m1` **已消失**（`grep -c` 为 0，历史文件除外）。
6. 输出「检查名 + 期望/实际 + 退出码」；任一失败非零退出。

**接入**：`Makefile` 增 `check-scope` 目标并加入 `check` 列表（放在 `validate-encoding` 附近）。`spec/README.md` 投影表同步。

**为什么不是并入 `validate_encoding.py`**：`validate_encoding` 管「编码合法性」，`check_scope` 管「范围分区」，职责不同（Do One Thing）；但可在 `validate_encoding` 增一条「`scope` 字段存在性」廉价断言作为补充。

---

## 6. 验收标准（可执行、可失败、含反例注入）

> 通用要求：完成区贴**真实命令输出与退出码**；复杂命令输出留 `.work/log/spec/SPEC-086t-*.log`；留证须捕获**被检命令自身**退出码（`cmd > log 2>&1; rc=$?` 或 `${PIPESTATUS[0]}`，禁 `| tee` 后 `$?`）；engineer 交付一键证据脚本 `.work/evidence/SPEC-086t/run.sh`（非交互、任一失败非零退出、逐项打印期望/实际、内置反例注入自检）。

1. **口径落地**：`contracts/opcodes.yaml` 每条记录含 `scope`；计数 `227 = 152 m1 + 60 fp + 15 excluded`；全库 `grep -c "excluded_m1"`（排除历史文件）为 **0**。
   - 命令：`python3 -c "import yaml;r=yaml.safe_load(open('contracts/opcodes.yaml'));from collections import Counter;print(Counter(x['scope'] for x in r))"` ⇒ `Counter({'m1':152,'fp':60,'excluded':15})`。
2. **M1 口径不变**：`validate_vectors` 输出 `152/152`；`check_qemu_trans --strict` 输出 `227/227 (M1 152/152)`；`check_interface_alignment` 输出 `80/80` 且 `M1 内 152`。
3. **解码语义不丢**：所有 `scope != m1` 记录 `decode == "ILLI"`（`check-scope` 断言；反例见 #6）。
4. **R8 语义不丢**：`validate_vectors` 的 reserved 交叉校验仍遍历全部 227 条（构造一条 word 命中某 FP 编码的 `reserved` 向量 ⇒ 应 FAIL，证明覆盖 FP）。
   - 反例：临时把 `ld.t_rrii_rf` 的 word（`0x16000000`）做 `encoding.reserved: true` 的向量 ⇒ `validate_vectors` 报 R8 FAIL；移除后回绿。
5. **生成物可复现**：两个生成器重跑均 `diff` 为空：
   - `generate_opcodes.py` → `diff contracts/opcodes.yaml <regen>` EXIT 0；
   - `gen_asm_list.py` → `.tao/knowledge/contract-asm-list.md` 逐字节一致；
   - `gen_asm_list.py --embed-spec` + `gen_legality_list.py --apply` 后 `check-asm-list-consistency` / `check-legality-drift` EXIT 0。
6. **反例注入（必须真实 FAIL → 还原 → 回绿）**，至少覆盖：
   - (a) 把 1 条 `scope: fp` 改为 `scope: m1` ⇒ `check-scope` FAIL（计数 153/59）+ `validate-vectors` 或 `check-interface` FAIL（M1 变 153）；还原 ⇒ 全绿。
   - (b) 把 1 条 fp 的 `decode: ILLI` 改为 `UNDI` ⇒ `check-scope` FAIL；还原 ⇒ 绿。
   - (c) 改 `SimRISC-07` ASSEMBLY_LIST 生成区一个字（或改生成器输出）⇒ `check-asm-list-consistency` FAIL；重生成后 ⇒ 绿。
   - (d) 改 LEGALITY 生成区一个字 ⇒ `check-legality-drift` FAIL；重生成后 ⇒ 绿。
   - (e) **空注入防护**：每次注入后 `git diff --name-only` 非空；**还原须包含重建**（源码还原 ≠ 生成物还原，重跑生成器）。
7. **spec 口径**：
   - `SimRISC-07` 头部与生成章标题不再有 `[deferred]` 混用（按 §4.1）；含「FP 范围总账」注（60=44+16，列 16 条出处）。
   - `SimRISC-01/02/03/07` LEGALITY 区标 `scope: fp`；`SimRISC-11/12` 标 `scope: excluded`；合计 60/15。
   - `tests/vectors/README.md` / `schema.md` 判据改 `scope == m1`，陈旧 177 → 152。
8. **`make check` EXIT=0**（含新增 `check-scope`）；关键计数与 §5.1 逐条一致。
9. **越界与残留**：`git diff --name-only` 与改动清单对齐；`git status --untracked-files=all` 干净；临时产物仅在 `/tmp/opencode/SPEC-086t/`，日志在 `.work/log/spec/`。

**范围边界（本试点明确不含）**：
- 不新增 LLVM 汇编/反汇编实现（`components/llvm-project/patches/**` 不动）；
- 不新增 QEMU 解码/trans（`components/qemu/patches/**` 不动，FP 仍 ILLI）；
- 不新增 FP 测试向量（`tests/vectors/isa/*.yaml`、`tests/lit/**` 不动）；
- 不建 ADR；不改历史 ADR/任务书/`SimRISC-0.5.3`。

**后续衔接点（本任务不创建，仅登记）**：
- `SPEC-08xt`：FP 语义合约与独立 oracle（从 `spec/SimRISC-07` 派生期望值）。
- `TESTCASES-0xxt`：FP 覆盖矩阵（`inventory.md` 增第二表 + `validate_vectors.parse_inventory` 按 section 区分多表）。
- `LLVM-0xxt`：FP 汇编/反汇编（含 MISC-RF + 16 条 RF 变体）。
- `QEMU-0xxt`：FP decode/trans 实现（替换 ILLI 桩）。
- `INTEG-0xxt`：FP E2E 闭环。

---

## 7. 独立 oracle 提醒（项目铁律）

- FP 的**语义期望值将来不得由 LLVM 或 QEMU 生成**，必须独立派生自 `spec/`（`tests/vectors/README.md` 已载此原则）。
- 本试点**只做范围口径**，**不产生任何 FP 语义期望值**；涉及的合法性/字段定义依据来自：
  - 编码：`spec/SimRISC-00` §MISC-RF指令编码（`op=0x44` 子表）与 QFC 主表 / MISC 子表；
  - 寄存器：`spec/SimRISC-00` §浮点寄存器 / §浮点状态寄存器（rf0/FCSR 位布局）；
  - 语义与限制：`spec/SimRISC-07`（格式转换/运算/符号位/比较/分类、`immu6` 限制、`ftroot` 仅 n=2）；
  - RF 存取/搬移/条件赋值：`spec/SimRISC-01`、`SimRISC-02`、`SimRISC-03`；
  - 规则：`contracts/legality_rules.yaml`（如 `dst_rf0`）。
- 新门控 `check-scope` 的 FP 判据（`id.endswith("_rf")`、60 条集合）来自**契约/spec**，不得从 LLVM/QEMU 反推。

---

## 8. 为何不立 ADR（用户裁定 + 理由）

- 用户 2026-10-03 明确裁定**不立 ADR**；本任务不创建 `adr-*.md`。
- 记录理由（写入本任务书 + 后续 `/complete` 的 `changelog`）：本次为**范围口径的机械重构**（把一个布尔判据 `excluded_m1` 替换为枚举 `scope`），**不改变任何指令语义/编码/契约期望值**；M1 身份集与全部门控计数**保持不变**；被否方案（A′ 缺省 m1、B 保留 excluded_m1 + family、C 双布尔）已记录于 §2.2，满足 ADR 判据中「多方案/已否方案」的记录需求，故无需独立 ADR 承载。
- **提醒**：该变更触及**跨模块外部契约**（`opcodes.yaml` 的消费者），本命中 ADR 判据之一；因用户已裁定，故不立。若后续 FP 语义/编码落地或口径再变，届时按 `spec/Process-03-ADR编写规范.md` 重新评估。

---

## 9. 风险与开放问题

| # | 风险 / 开放问题 | 影响 | 建议处置 |
|---|---|---|---|
| R1 | **`scope` 命名与取值未定稿**（`scope`/`range`；`m1/fp/excluded`） | 全任务命名 | 下发前由用户拍板 |
| R2 | **`excluded_m1` 字样残留在历史载体**：`adr-0014`（fence）、`docs/issues.yaml` 416–421、`deferred.md` 40/43/144/148、旧任务书、`changelog` | 措辞陈旧，非门控 | 历史不改写；`adr-0014` 属 Accepted ADR 快照，**须用户裁定**是否加注/修订（不得静默改） |
| R3 | **`inventory.md` 是否本任务新增 FP 表** | 若加第二张 `id|format` 表，`validate_vectors.parse_inventory` 会把 FP 行当 M1 行 ⇒ `INVENTORY EXTRA` | 本试点**不加** FP 表（保持 validator 不动）；FP 覆盖矩阵留后续 `TESTCASES-0xxt`（届时按 section 区分多表）。若用户要求本试点加，则须把 `parse_inventory` 多表支持纳入本任务范围 |
| R4 | **`deferred` 与 `scope` 是否保留并用** | spec 标注口径 | 推荐 `scope` 表范围、`deferred` 表状态（正交）；按 §4.1 落实 |
| R5 | **既有陈旧计数**：`tests/vectors/README.md:10`、`schema.md:202` 写 177（实为 152） | 文档失真 | 本试点顺带订正（属同口径载体） |
| R6 | **生成物与源码的还原一致性** | 反例注入后若只还原源码不重跑生成器，门控会跑在注入过的生成物上 | 验收 #6(e) 强制「还原含重建」 |
| R7 | **跨模块越界**：本任务改 `tools/llvm`、`tools/qemu`、`tools/testcases` 工具（非实现） | 模块归属 | 完成区显式披露；不触碰 `components/**`、`tests/**` |
| R8 | **`scope: excluded` 的 15 条**（cfx/LR-SC/fence）无独立门控覆盖 | 口径分界 | `check-scope` 断言其计数 15 与 `decode: ILLI`；后续若 M2 启用 cfx 再立项 |

---

## 执行环境
**执行环境**：本地

## 接口规范

### 输入
- `contracts/opcodes.yaml`（现状 227=152+75）、`contracts/legality_rules.yaml`
- `tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/llvm/gen_asm_list.py`
- 消费方工具（§3 表 ①②③ 所列）
- `spec/SimRISC-00/07/01/02/03/11/12`、`spec/Toolchain-01-汇编语言.md`、`spec/README.md`
- `.tao/knowledge/contract-isa.md`、`tests/vectors/{inventory.md,README.md,schema.md}`
- `Makefile`、`docs/{README.md,impact-matrix.md,m1-retrospective.md,m2-spec-planning.md,spec/assembly-language.md}`

### 输出
1. `contracts/opcodes.yaml`：227 条带 `scope`（152/60/15），删除 `excluded_m1`，头注释重写。
2. `tools/spec/generate_opcodes.py`：产出 `scope`；`scope != m1 ⇒ decode: ILLI`。
3. 消费方谓词迁移（§3 表 ①②③）。
4. 生成物重生成：`.tao/knowledge/contract-asm-list.md`、`spec/SimRISC-01..12` 的 ASSEMBLY_LIST/LEGALITY 区。
5. `tools/spec/check_scope.py`（新）+ `Makefile` 的 `check-scope`。
6. spec 正文/投影/文档口径同步（§3 表 ④）。
7. 知识沉淀（由 `/complete` 追加 `MEMORY.md`/`changelog.md`，并按需 `deferred.md` 加注）。

### 约束
- 全程中文；**不提交 git**；**不创建 ADR**；只动任务书范围，越界须披露。
- **Spec-first**：所有期望值来自 `spec/` 与 `contracts/`，不从实现反推。
- **原子**：②③ 与 ① 必须同一提交，否则 `make check` 变红；生成物勿手工编辑。
- **不改** `components/llvm-project/patches/**`、`components/qemu/patches/**`、`tests/lit/**`、`tests/vectors/isa/*.yaml`；**不改** `adr-*` 决策正文、`spec/SimRISC-0.5.3/**`、已验收历史任务书。
- 临时产物 `/tmp/opencode/SPEC-086t/`；日志 `.work/log/spec/SPEC-086t-*.log`；证据脚本 `.work/evidence/SPEC-086t/run.sh`。
- 遵循 `AGENTS.md`「子代理硬约束」与「验证脚本反例门控」。

## 验收标准
见上文 §6（1–9）；反例注入见 §6.6。

## 完成区

**测试结果**：通过 **21/21**（一键证据脚本 `.work/evidence/SPEC-086t/run.sh`，默认模式）、反例注入自检 **21/21**（`run.sh --inject`）；两轮均 `PASS=21 FAIL=0`。
- 基线 `make check` 改动前 `EXIT=0`（日志 `.work/log/spec/SPEC-086t-make-check-before.log`）；改动后 `make check` `EXIT=0`（日志 `.work/log/spec/SPEC-086t-make-check-after.log`）。
- `validate_vectors`：`152/152 M1 identities covered OK`；`check_qemu_trans --strict`：`227/227 insns have trans impl (M1 152/152)`；`check_interface_alignment`：`总计: 80 项 | PASS: 80 | FAIL: 0`，`M1 内 152`；`validate_encoding`：`227 条记录 OK`；`check_rule_refs`：`16 条规则; 指令引用 198 处`；`check-legality-drift`：`12 chapters OK`；`check-asm-list-consistency`：`12 spec files OK`；`check-asm-list-drift`：`PASS (byte-identical)`；lit `26/26`；patches `67 OK`；新增 `check-scope: PASS`。
- 独立工具回归：`test_anti_forgery_008t.py`（5 注入 + 1 valid）、`check_005t_coverage.py`、`check_qfc_coverage.py` 均 `EXIT=0`；`check_spec_refs.py`（standalone、基线本就 FAIL）保持基线 `76 violations (18+58)`，无回归（见「新发现/坑」）。

**修改文件**（39 改 + 2 新增，未提交）：
- 核心：`tools/spec/generate_opcodes.py`、`contracts/opcodes.yaml`（重生成）、`tools/spec/check_scope.py`（新）、`Makefile`。
- 消费方 ②：`tools/testcases/validate_vectors.py`、`tools/qemu/check_qemu_trans.py`、`tools/integ/check_interface_alignment.py`、`tools/llvm/gen_asm_list.py`、`tools/spec/gen_legality_list.py`、`.tao/knowledge/contract-asm-list.md`（重生成）、`spec/SimRISC-01/02/03/07/11/12`（生成区重跑）、`tests/vectors/inventory.md`。
- 一致性 ③：`tools/testcases/generate_isa_vectors.py`、`generate_mem_vectors.py`、`generate_ctrl_br.py`、`generate_ctrl_jump_call_ret.py`、`generate_misc.py`（+重生成 `tests/vectors/isa/misc.yaml` 注释行）、`test_anti_forgery_008t.py`、`tools/qemu/check_005t_coverage.py`、`tools/spec/check_qfc_coverage.py`、`tools/llvm/generate_instrinfo.py`、`validate_instrinfo.py`、`gen_m1_asm.py`。
- 口径 ④：`spec/SimRISC-00`、`spec/Toolchain-01`、`spec/README.md`、`.tao/knowledge/contract-isa.md`、`tests/vectors/README.md`、`tests/vectors/schema.md`、`docs/README.md`、`docs/impact-matrix.md`、`docs/m1-retrospective.md`、`docs/m2-spec-planning.md`。
- 越界披露：`contracts/legality_rules.yaml`（仅改 L19 注释计数，未在 ④ 列出）、`tests/vectors/isa/misc.yaml`（仅由生成器重跑得到注释行 1 行变更，非向量数据）。

**验收结果**（逐条真实输出与退出码）：
1. 口径落地：
   - `python3 -c "..."` ⇒ `Counter({'m1': 152, 'fp': 60, 'excluded': 15})`；total 227。
   - `python3 tools/spec/check_scope.py` ⇒ `check-scope: PASS`，`EXIT=0`。
   - 全库 `grep -rl "excluded_m1"`（排除 `.git/.work/.cache/__pycache__` 与历史载体 `.tao/adr/`、`.tao/tasks/`、`.tao/knowledge/{MEMORY,changelog,deferred}.md`、`docs/issues.yaml`、`docs/spec-065t-legality-proposal.md`、`spec/SimRISC-0.5.3/`）⇒ **0 文件**（无输出）。
2. M1 口径不变：`validate_vectors` `152/152`；`check_qemu_trans --strict` `227/227 (M1 152/152)`；`check_interface_alignment` `80/80` 且 `M1 内 152`（均 `EXIT=0`）。
3. 解码语义不丢：`check_scope` 断言 `scope!=m1 ⇒ decode=ILLI`（0 违规，PASS）。
4. R8 语义不丢：临时把 `0x16000000`（`ld.t_rrii_rf`, `scope: fp`）作 `reserved: true` 向量 ⇒ `validate_vectors` `EXIT=1` 且报 `matches defined encoding ... scope=fp`；移除后回 `EXIT=0`（`run.sh` C7 与 `--inject` R8）。
5. 生成物可复现：`generate_opcodes.py` 重跑后 `contracts/opcodes.yaml` `diff` 为空；`gen_asm_list.py` → `.tao/knowledge/contract-asm-list.md` 逐字节一致；`check-asm-list-consistency` / `check-legality-drift` `EXIT=0`。
6. 反例注入（a–e + R8，`run.sh --inject`：PASS=21 FAIL=0）：(a) fp→m1 ⇒ `check-scope`/`validate-vectors` FAIL；(b) ILLI→UNDI ⇒ `check-scope` FAIL；(c) SimRISC-07 ASSEMBLY_LIST 改字 ⇒ `check-asm-list-consistency` FAIL；(d) LEGALITY 改字 ⇒ `check-legality-drift` FAIL；(e) 每次注入 `git hash-object` 变化（非空注入）、还原经重跑生成器且 blob 与注入前一致。
7. spec 口径：`SimRISC-07` 头部 `[scope: fp]（44 条；未实现，decode ILLI）` + 「FP 范围总账（60=44+8+7+1）」注；生成章标题去 `[deferred]` 混用；`SimRISC-01/02/03/07` LEGALITY 标 `scope: fp`、`SimRISC-11/12` 标 `scope: excluded`（合计 60/15）；`tests/vectors/README.md`/`schema.md` 判据改 `scope == "m1"`、`177→152`。
8. `make check` `EXIT=0`，关键计数与 §5.1 逐条一致（227 / 152 / 198 / 26 / 80 / 67）。
9. 越界与残留：`git status --untracked-files=all` 仅任务应改文件 + `tools/spec/check_scope.py` + 本任务书；`check-no-residue` PASS；临时产物仅在 `/tmp/opencode/SPEC-086t/`，日志在 `.work/log/spec/SPEC-086t-*.log`。

**新发现/坑**：
- **任务书内部矛盾 3 处**（已按可执行性取最贴合意图的解读，均披露）：
  1. §3③ 要求改 `generate_misc.py` L19/L148 注释为 `scope`，但 §6 范围边界写 `tests/vectors/isa/*.yaml` **不动**；L148 是**产出 misc.yaml 注释行**的生成源 ⇒ 改生成器后重跑必致 `misc.yaml` 1 行注释变更。取舍：重跑生成器保持「生成器-产物」一致（否则残留旧字段且 §6.1 grep 非 0）；仅注释行、非向量数据。
  2. §3③ 写「注入标签 `R8/excluded` → `R8/scope-excluded`」，括注却称「`ld.t-rf` 现属 `scope: fp`」；两者矛盾。取更准确者 `R8/scope-fp`（描述串同步去 `excluded_m1`）。
  3. §1.2/§4.2 称 `SimRISC-00` L255 有 `MISC-RF … Excluded from M1`；实测该文件无此字样（仅 L281 主表指针、L375 子表标题）。已在 L281 表后与 L375 子表处新增 `scope` 注。
- **§6.1「全库 grep=0」未列出的 live 载体**：`contracts/legality_rules.yaml` L19 注释、`docs/spec-065t-legality-proposal.md`。前者按 live contract 更新注释（越界披露）；后者属历史提案（与旧任务书同类）纳入排除集，未改。
- **`check_scope.py` 自命中防护**：断言旧字段消失时以 `"excluded"+"_m1"` 拼接构造，避免门控脚本自身命中被扫（否则 tools/ 扫描恒 FAIL）。建议沉淀此写法。
- **非门控 `check_spec_refs.py` 的隐性回归**：contract-isa 新增含 `decode ILLI` 的行会被其 Check2（含规范标记但无 `[SimRISC-XX §…]` 引用）计入；初版 +2（76→78）。处置：`§9` 标题与 `§14` 引子补 spec 引用（`[SimRISC-07 §版本]` / `[SimRISC-12 §fence指令]`），恢复基线 **76**（18 Check1 + 58 Check2），无回归。建议沉淀：改 `contract-isa.md` 后除 `make check` 外应跑一次 standalone `check_spec_refs.py` 对比基线。
- 生成物可复现性良好：`generate_opcodes.py` 幂等（回应 `SPEC-067t` 遗留债务，本任务实测 `diff` 空）；`gen_asm_list.py` / `gen_legality_list.py` 幂等。

**遗留问题**：
- **越界（已披露，非语义）**：`tests/vectors/isa/misc.yaml`（生成器注释 1 行）、`contracts/legality_rules.yaml`（L19 注释）、`spec/SimRISC-00`（`scope` 注，2 处）、`spec/Toolchain-01` L15/L246（`Excluded from M1`→`scope: excluded`，超出 ④ 列明的 L5/42/151/221）。
- **历史载体保留旧字段字样（按 R2/§3⑤ 不改写）**：`.tao/adr/adr-0014-fence-excluded-m1.md`、`.tao/knowledge/{MEMORY,changelog,deferred}.md`、`docs/issues.yaml`、`docs/spec-065t-legality-proposal.md`、旧任务书、本任务书自身。
- R3：`inventory.md` **未加** FP 表（符合任务），FP 覆盖矩阵留 `TESTCASES-0xxt`。
- 后续衔接点（本任务仅登记，未创建）：FP 语义合约/独立 oracle、FP 覆盖矩阵、LLVM/QEMU FP 实现（替换 ILLI 桩）、FP E2E。
- 无未修 finding（自审 finding 全部 ✅已修）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`git diff` 全部 39 改 + `tools/spec/check_scope.py`；重跑全部门控与 3 个 standalone 工具；构造反例 (a)–(e) + R8。

**判决**：所有 finding 已修；`make check` EXIT=0；一键证据脚本 21/21 + 注入 21/21。**可标 待验收**。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `check_scope.py` 计数断言字符串不等（`"0 条缺失/非法"` vs `"0 条"`）致 4 项假 FAIL | ✅已修 | 4 处 `record(...)` 期望串统一为 `"0 条"`/`"0 个文件"` | 修复前 `EXIT=1`（4 FAIL）；修复后 `check-scope: PASS`，`EXIT=0` |
| F2 `check_scope.py` 文档串含旧字段字面量 → 被自身扫描命中（tools/ 恒 FAIL） | ✅已修 | 文档改述 + `OLD_FIELD="excluded"+"_m1"` 拼接 | `check_scope: PASS`；`grep -n excluded_m1 tools/spec/check_scope.py` 无输出 |
| F3 改 `contract-isa.md` 后 standalone `check_spec_refs.py` 违规 76→78（新增 `decode ILLI` 行无 spec 引用） | ✅已修 | §9 标题补 `[SimRISC-07 §版本]`、§14 引子补 `[SimRISC-12 §fence指令]` | baseline（HEAD worktree）`76 (18+58)`；修复后 `76 (18+58)`，无回归 |
| F4 `tests/vectors/isa/misc.yaml` 旧字段残留（生成器产出），`§6.1` grep 非 0 | ✅已修 | 改 `generate_misc.py` L19/L148 注释并重跑；`misc.yaml` 仅 1 行注释变 | `diff` 仅第 7 行注释；`validate_vectors 152/152 EXIT=0` |
| F5 (a)–(e) 反例注入的 FAIL 路径与还原（含重跑重建）是否可达/可复原 | ✅已修/已证 | `run.sh --inject` 逐项断言 `hash-object` 变化 + FAIL + 重跑生成器还原一致 | `--inject` `PASS=21 FAIL=0`；`git worktree` 基线对比无残留 |
| F6 R8 语义：`0x16000000` 是否仍被判为「已定义编码」 | ✅已证 | 保留 `all_records` 全量遍历，仅更新报错文案为 `scope=` | 注入 ⇒ `validate_vectors EXIT=1` 且报 `scope=fp`；移除 ⇒ `EXIT=0` |
| F7 生成物幂等/漂移 | ✅已证 | — | `generate_opcodes.py` 重跑 `diff` 空；`check-asm-list-drift PASS (byte-identical)`；`check-legality-drift 12 chapters OK` |
| F8 越界文件与任务清单对齐 | ✅已披露 | 见「遗留问题」；`git diff --name-only` 与 ①–④ + 披露项一致 | `git status` 干净无残留；`check-no-residue PASS` |

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-03
**审查范围**：全部验收项（1–9）+ 脚本审计 + 独立注入 + 3 处矛盾判定

---

##### 一、重跑记录（逐项真实命令、输出、退出码）

**1.1 分区与清零**

```bash
python3 -c "
import yaml; from collections import Counter
r = yaml.safe_load(open('contracts/opcodes.yaml'))
c = Counter(x['scope'] for x in r)
print('Counter:', c); print('total:', len(r))
"
# 输出：
# Counter: Counter({'m1': 152, 'fp': 60, 'excluded': 15})
# total: 227
# EXIT=0
```

全库 grep（排除历史载体）：
```bash
grep -rl 'excluded_m1' tools/ contracts/ spec/ tests/ docs/ Makefile README.md AGENTS.md \
  | grep -v __pycache__ | grep -v '.git/' | grep -v '.work/' | grep -v '.cache/'
# 输出：docs/issues.yaml, docs/spec-065t-legality-proposal.md（均为历史排除集内文件）
# EXIT=0（grep 无匹配时 exit 1，但仅命中历史文件 → 符合预期）
```

check_scope.py 独立运行：
```
[PASS] 每条记录恰有合法 scope: 期望=0 条 实际=0 条
[PASS] m1 计数: 期望=152 实际=152
[PASS] fp 计数: 期望=60 实际=60
[PASS] excluded 计数: 期望=15 实际=15
[PASS] total 计数: 期望=227 实际=227
[PASS] scope!=m1 ⇒ decode=ILLI: 期望=0 条 实际=0 条
[PASS] scope==m1 ⇒ 无 decode/旧字段: 期望=0 条 实际=0 条
[PASS] scope:fp ⇔ id 以 _rf 结尾: 期望=0 条 实际=0 条
[PASS] 旧字段在非历史文件中消失: 期望=0 个文件 实际=0 个文件
check-scope: PASS
EXIT=0
```

**1.2 M1 口径不变**

```bash
python3 tools/testcases/validate_vectors.py 2>&1 | tail -1
# validate_vectors: 152/152 M1 identities covered OK (inventory sync OK; 15 data files, 692 cases; data coverage gaps: 0)
# EXIT=0

python3 tools/qemu/check_qemu_trans.py --strict 2>&1 | tail -1
# check_qemu_trans: 227/227 insns have trans impl (M1 152/152)
# EXIT=0

python3 tools/integ/check_interface_alignment.py 2>&1 | grep -E '(总计|M1 内)'
# 4.Opcodes    opcodes.yaml 条目数  PASS  总计 227, M1 内 152（inventory.md 独立计数 152 一致）
# 总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
# EXIT=0
```

```bash
make check > /tmp/opencode/SPEC-086t-review/make-check.log 2>&1; echo "EXIT=$?"
# EXIT=0
# 关键计数：
# - validate_vectors: 152/152
# - check_qemu_trans: 227/227 (M1 152/152)
# - check_interface_alignment: 80/80, M1 内 152
# - validate_encoding: 227 条记录 OK
# - check-rule-refs: 16 条规则; 指令引用 198 处
# - check-patch-tree: 67 patches OK
# - check-scope: PASS
# - lit: 26/26
# - check-asm-list-consistency: 12 spec files OK
# - check-asm-list-drift: PASS (byte-identical)
# - check-legality-drift: 12 chapters OK
# - repository checks: PASS
```

**1.3 解码/交叉校验语义不丢**

check_scope.py 断言 `scope!=m1 ⇒ decode==ILLI`：上方已验，0 条违规，PASS。

R8 遍历验证：`validate_vectors.py` L298 `for rec in all_records:` 遍历全部227条（含 scope fp/excluded），仅更新 L308 报错文案为 `scope=`。

R8 反例（engineer 脚本 C7）：
```
# 注入 reserved.yaml（word=0x16000000, reserved=true）
# blob 变化 9faa6c737fde → ab7d4aab47e7
# validate_vectors EXIT=1，报 "matches defined encoding ... scope=fp"
# 移除后 EXIT=0，reserved.yaml 还原一致
```

**1.4 生成物可复现**

```bash
cp contracts/opcodes.yaml /tmp/opencode/SPEC-086t-review/opcodes.before.yaml
python3 tools/spec/generate_opcodes.py > /dev/null 2>&1
diff -q /tmp/opencode/SPEC-086t-review/opcodes.before.yaml contracts/opcodes.yaml
# 无输出（逐字节一致）
# gen_rc=0 diff_rc=0

python3 tools/llvm/gen_asm_list.py -o /tmp/opencode/SPEC-086t-review/contract-asm-list.regen.md > /dev/null 2>&1
diff -q /tmp/opencode/SPEC-086t-review/contract-asm-list.regen.md .tao/knowledge/contract-asm-list.md
# 无输出（逐字节一致）
# gen_rc=0 diff_rc=0

python3 tools/spec/check_asm_list_consistency.py 2>&1
# check-asm-list-consistency: 12 spec files OK
# EXIT=0

python3 tools/spec/check_legality_drift.py 2>&1
# check-legality-drift: 12 chapters OK
# EXIT=0
```

**1.5 证据脚本重跑（默认模式）**

```bash
bash .work/evidence/SPEC-086t/run.sh > /tmp/opencode/SPEC-086t-review/run-default.log 2>&1; echo "EXIT=$?"
# EXIT=0
# PASS=21 FAIL=0
# SPEC-086t: ALL PASS
```

逐项输出（摘要）：
- C1 分区计数: PASS (m1 152 fp 60 excluded 15 total 227)
- C2 check-scope: PASS (rc=0)
- C3 validate-vectors: PASS (rc=0, 152/152)
- C4 check_qemu_trans: PASS (rc=0, 227/227 M1 152/152)
- C5 check_interface_alignment: PASS (rc=0, 80/80, M1 内 152)
- C6a generate_opcodes: PASS (rc=0, diff 空)
- C6b gen_asm_list: PASS (rc=0, diff 空)
- C6c check-asm-list-consistency: PASS (rc=0)
- C6d check-legality-drift: PASS (rc=0)
- C7 R8 注入: PASS (blob 变化, validate_vectors FAIL rc=1, 还原后 rc=0)
- C8 make check: PASS (rc=0)

**1.6 证据脚本重跑（--inject 模式）**

```bash
bash .work/evidence/SPEC-086t/run.sh --inject > /tmp/opencode/SPEC-086t-review/run-inject.log 2>&1; echo "EXIT=$?"
# EXIT=0
# PASS=21 FAIL=0
# SPEC-086t: ALL PASS
```

逐项输出（摘要）：
- (a) fp→m1: 注入非空 → check-scope FAIL(rc=1) → validate-vectors FAIL(rc=1) → 重跑生成器回绿 → 还原一致
- (b) ILLI→UNDI: 注入非空 → check-scope FAIL(rc=1) → 重跑生成器回绿 → 还原一致
- (c) ASSEMBLY_LIST 改字: 注入非空 → check-asm-list-consistency FAIL(rc=1) → 重跑生成器回绿 → 还原一致
- (d) LEGALITY 改字: 注入非空 → check-legality-drift FAIL(rc=1) → 重跑生成器回绿 → 还原一致
- (R8) reserved 命中 FP: 注入非空 → validate-vectors FAIL(rc=1) → 还原后回绿 → 还原一致

注入后 `git diff --name-only` 仅含任务应改文件（39 modified + 2 untracked），无残留。

---

##### 二、脚本审计结论

**审计对象**：`.work/evidence/SPEC-086t/run.sh`（270行）

| 审计项 | 结论 |
|--------|------|
| 每条断言的 FAIL 路径 | ✅ 每个 check_rc / assert 都测试真实 rc（`$?` 直接捕获），无 `check(name, True)` 恒真模式 |
| 退出码语义 | ✅ 最终 `$FAIL -eq 0` → exit 0/1，清晰 |
| `tee` 吞码 | ✅ 无 `| tee`，所有退出码直接捕获 |
| `--inject` 的 (a)–(e) 非空 | ✅ 每个注入都有 `assert_changed`（`git hash-object` 变化检查），实测 blob 均变化 |
| 还原含重跑生成器 | ✅ (a)(b) 重跑 `generate_opcodes.py`；(c) 重跑 `gen_asm_list.py --embed-spec`；(d) 重跑 `gen_legality_list.py --apply`；(R8) 用 cp 还原备份（向量文件，无生成器） |
| 还原一致性 | ✅ 每个注入函数末尾检查 `hash_of == before`，实测均一致 |
| 空注入防护 | ✅ `assert_changed` 函数检查 blob 前后变化 |

**脚本合格，可作为验收证据。**

---

##### 三、独立注入与还原证据

**注入 A：改 check_scope.py 的 EXPECTED_M1（152→151）**

```bash
BEFORE_HASH=$(git hash-object tools/spec/check_scope.py)
# before=66b6ed6431b5a54f28e7987655a9edfd83086bf1

python3 -c "
p='tools/spec/check_scope.py'; s=open(p).read()
open(p,'w').write(s.replace('EXPECTED_M1 = 152','EXPECTED_M1 = 151',1))
"

python3 tools/spec/check_scope.py 2>&1
# [FAIL] m1 计数: 期望=151 实际=152
# check-scope: FAILED (1 项)
# EXIT=1

# 还原
python3 -c "
p='tools/spec/check_scope.py'; s=open(p).read()
open(p,'w').write(s.replace('EXPECTED_M1 = 151','EXPECTED_M1 = 152',1))
"
RESTORE_HASH=$(git hash-object tools/spec/check_scope.py)
# restore=66b6ed6431b5a54f28e7987655a9edfd83086bf1（与 before 一致）

python3 tools/spec/check_scope.py 2>&1
# check-scope: PASS
# EXIT=0
```

**注入 B：改 opcodes.yaml 的 scope（fp→excluded）**

```bash
BEFORE_HASH=$(git hash-object contracts/opcodes.yaml)
# before=7801a3c02828c74afc2ee5480888902cd96e3399

python3 -c "
p='contracts/opcodes.yaml'; s=open(p).read()
assert s.count('  scope: fp\n')>=1
open(p,'w').write(s.replace('  scope: fp\n','  scope: excluded\n',1))
"

python3 tools/spec/check_scope.py 2>&1 | grep FAIL
# [FAIL] fp 计数: 期望=60 实际=59
# [FAIL] excluded 计数: 期望=15 实际=16
# [FAIL] scope:fp ⇔ id 以 _rf 结尾: 期望=0 条 实际=1 条（ld.t_rrii_rf）
# check-scope: FAILED (3 项)

# 还原（重跑生成器）
python3 tools/spec/generate_opcodes.py > /dev/null 2>&1
RESTORE_HASH=$(git hash-object contracts/opcodes.yaml)
# restore=7801a3c02828c74afc2ee5480888902cd96e3399（与 before 一致）

python3 tools/spec/check_scope.py 2>&1 | tail -3
# [PASS] scope:fp ⇔ id 以 _rf 结尾: 期望=0 条 实际=0 条
# [PASS] 旧字段在非历史文件中消失: 期望=0 个文件 实际=0 个文件
# check-scope: PASS
```

**注入后 git diff --name-only 非空确认**：两次注入均检测到目标文件 blob 变化（注入 A: 66b6ed→9f1b98；注入 B: 7801a3→46f3b1）。

**还原后 git status 干净**：无残留修改。

---

##### 四、3 处矛盾判定

**矛盾 ①**：§3③ 改 `generate_misc.py`（产出 `misc.yaml` 注释）vs §6「`tests/vectors/isa/*.yaml` 不动」

- 核实：`generate_misc.py` L19/L148 注释行确实产出 `misc.yaml` 的 header comment（第7行）。改生成器后重跑必致 `misc.yaml`1 行注释变更。
- 实测 diff：`misc.yaml` 仅第7行注释变（`excluded_m1: true` → `scope: excluded`），非向量数据。
- 判定：**可接受**。engineer 取「重跑生成器保持生成器-产物一致」是正确选择。否则残留旧字段会导致 §6.1 grep 非 0。变更仅为注释行，不影响向量语义。

**矛盾 ②**：§3③ 标签 `R8/scope-excluded` vs 括注「`ld.t-rf` 属 fp」

- 核实：`ld.t_rrii_rf` 的 `scope` 为 `fp`（opcodes.yaml 确认）。
- engineer 取 `R8/scope-fp`（更准确），描述串同步去 `excluded_m1`。
- 判定：**可接受**。`R8/scope-fp` 准确反映 `ld.t-rf` 的真实 scope。原任务书的 `R8/scope-excluded` 是笔误。

**矛盾 ③**：§1.2 称 `SimRISC-00` L255 有 `MISC-RF … Excluded from M1`，engineer 实测无。

- 核实：`sed -n '250,260p' spec/SimRISC-00-指令系统设计.md` 显示 L255 为「标识位说明」节，无 `MISC-RF` 或 `Excluded from M1` 字样。
- 判定：**可接受**。任务书 §1.2 的描述有误（可能是基于旧版本或笔误）。engineer 在 L290（主表指针后）和 L379（MISC-RF 子表标题处）新增 `scope` 注，位置合理。

---

##### 五、越界与最小性

**engineer 披露的越界**：

| 越界文件 | 改动内容 | 必要性 | 最小性 |
|----------|---------|--------|--------|
| `tests/vectors/isa/misc.yaml` | L7 注释行（生成器产出） | 必要（否则 grep 非 0） | ✅ 最小（仅1行注释） |
| `contracts/legality_rules.yaml` L19 | 注释计数 `75→60+15` | 非必要但合理（一致性） | ✅ 最小（1行注释） |
| `spec/SimRISC-00` L290/L379 | 新增 `scope` 分区注 | 非必要但合理（可读性） | ✅ 最小（2处新增注） |
| `spec/Toolchain-01` L15/L246 | `Excluded from M1` → `scope: excluded` | 非必要但合理（一致性） | ✅ 最小（2处措辞） |

**未披露越界检查**：
```bash
git diff --name-only | grep -E '^(components/|tests/lit/|tests/vectors/isa/)' | grep -v misc.yaml
# 无输出
```
- `components/**`：✅ 未动
- `tests/lit/**`：✅ 未动
- `tests/vectors/isa/*.yaml`：✅ 仅 misc.yaml（已披露）

**git status 干净**：39 modified + 2 untracked（check_scope.py + 任务书），无残留临时文件。

---

##### 六、完成区一致性

| 完成区声明 | reviewer 核实 | 一致？ |
|-----------|--------------|--------|
| Counter({'m1':152,'fp':60,'excluded':15}), total 227 | ✅ 重跑一致 | ✅ |
| check_scope PASS, EXIT=0 | ✅ 重跑一致 | ✅ |
| 全库 grep 0 文件（排除历史） | ✅ 仅命中 docs/issues.yaml 和 docs/spec-065t（历史文件） | ✅ |
| validate_vectors 152/152 EXIT=0 | ✅ 重跑一致 | ✅ |
| check_qemu_trans 227/227 (M1 152/152) EXIT=0 | ✅ 重跑一致 | ✅ |
| check_interface_alignment 80/80 M1 内 152 EXIT=0 | ✅ 重跑一致 | ✅ |
| make check EXIT=0 | ✅ 重跑一致 | ✅ |
| validate_encoding 227 OK | ✅ 重跑一致 | ✅ |
| check_rule_refs 16 规则 198 引用 | ✅ 重跑一致 | ✅ |
| check-patch-tree 67 OK | ✅ 重跑一致 | ✅ |
| lit 26/26 | ✅ 重跑一致 | ✅ |
| generate_opcodes diff 空 | ✅ 重跑一致 | ✅ |
| gen_asm_list diff 空 | ✅ 重跑一致 | ✅ |
| check-asm-list-consistency 12 OK | ✅ 重跑一致 | ✅ |
| check-legality-drift 12 OK | ✅ 重跑一致 | ✅ |
| R8 注入 FAIL → 还原回绿 | ✅ 重跑一致 | ✅ |
| run.sh 默认21/21 | ✅ 重跑一致 | ✅ |
| run.sh --inject 21/21 | ✅ 重跑一致 | ✅ |
| 39改 + 2新增 | ✅ git diff --name-only 确认 | ✅ |
| 越界披露完整 | ✅ 核实一致 | ✅ |

**未发现不实/夸大。**

---

##### 七、判决

**Accepted**。

全部验收项（1–9）在 reviewer 独立重跑下通过：
1. ✅ 分区与清零：Counter({'m1':152,'fp':60,'excluded':15})，total 227，全库 grep 仅命中历史文件
2. ✅ M1 口径不变：validate_vectors 152/152、check_qemu_trans 227/227 (M1 152/152)、check_interface_alignment 80/80、make check EXIT=0
3. ✅ 解码语义不丢：check_scope 断言 scope!=m1 ⇒ decode=ILLI，0 违规
4. ✅ R8 语义不丢：validate_vectors 的 R8 遍历全部227条（all_records），反例注入确认覆盖 FP 编码
5. ✅ 生成物可复现：generate_opcodes diff 空、gen_asm_list diff 空、check-asm-list-consistency/check-legality-drift EXIT=0
6. ✅ 反例注入（脚本 a–e + R8 + reviewer 独立注入2处）：全部 FAIL→还原→回绿
7. ✅ spec 口径：SimRISC-07 头部/生成章标题/Legality 区正确更新；SimRISC-01/02/03/07 标 scope: fp；SimRISC-11/12 标 scope: excluded
8. ✅ make check EXIT=0，关键计数与 §5.1 逐条一致
9. ✅ 越界与残留：git status 干净，无未披露越界，临时产物仅在 /tmp/opencode/SPEC-086t/

脚本审计：`.work/evidence/SPEC-086t/run.sh` 合格（FAIL 路径可达、非恒真、还原含重跑生成器、无 tee 吞码）。

3 处矛盾判定：①②③ 均可接受，无需返工。
