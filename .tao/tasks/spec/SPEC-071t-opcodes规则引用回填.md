# SPEC-071t: `opcodes.yaml` 回填 `rule_refs` + 规则引用双向门控

**模块**：spec（`contracts/` + `tools/spec/`）
**项目里程碑**：M2
**依赖**：`SPEC-070t`（15 条规则已定稿，`52a74f4`）
**状态**：待验收

## 背景与关键约束

`contracts/opcodes.yaml` **是生成物**：由 `tools/spec/generate_opcodes.py` 中硬编码的 `records` 经 `yaml.dump` 产出（无外部输入源 ✓）。
⇒ **`rule_refs` 必须加在生成器里**（`rec(...)` 的条目或 `main()` 的统一后处理），再重新生成 ✗ —— **禁止**只手改 `contracts/opcodes.yaml` ✗（下次生成即丢，本会话已两次踩同类坑 ✗）。
⇒ 首次落地后须验证生成器**幂等**（连跑两次 sha256 不变 ✓）。

## 目标

1. `opcodes.yaml` 新增字段 `rule_refs`（list[string]，取值 = `contracts/legality_rules.yaml` 的 `id` ✓）：
   - **有非空 `legality` 的 M1 指令** ⇒ 按其 `legality` 表达式映射到**对应规则 id**（可多条）✓；
   - **M1 内 `legality: []`** ⇒ `rule_refs: []` ✓；
   - **全部 `excluded_m1: true`** ⇒ `rule_refs: []` ✓。
   - 数量**以脚本实算为准**（不得沿用"135/18"等旧数 ✗；`SPEC-069t` 后指令集已变 ✓）。
2. 新增 `tools/spec/check_rule_refs.py`（**双向门控**，可独立 CLI 退出码）：
   - **门控 1（ID 存在性）**：每条指令 `rule_refs` 的所有 id 必须 ∈ `legality_rules.yaml` 的 id 集合 ✓；
   - **门控 2（孤儿规则）**：`status: active` 的规则**至少被 1 条指令引用** ✓，**但下列 4 条显式豁免**（理由见下）：
     `{excp_ialign, excp_rasof, excp_rasuf, excp_undi}` ✓
     —— 前 3 条为**运行时/全局条件**（取指对齐、返回地址栈上/下溢），不由任何编码 `legality` 表达式触发；`excp_undi` 是**未分配编码的兜底 fault**（不归属任何 M1 指令）。
     检查器须**断言豁免清单恰为这 4 条**（多/少/改名 ⇒ 门控自身 FAIL ✗），防止清单静默膨胀。`status: deferred` 一律允许 0 引用 ✓。
     注：`excp_malign`（`kind: dynamic`）**被 `aligned()` 引用**（24 条）⇒ **不在豁免清单内** ✗，仍受门控约束（说明 `kind` 不是孤儿判别的依据）。
   - 退出 0 = 通过；退出 1 = 失败，打印定位信息 ✓。
3. 将 `check-rule-refs` 接入 `make check`（新增独立 target；**不改**既有 target 判定逻辑 ✗）。
4. 上层通用规则（如已移出的 `imm_range` 语义）**不**逐条列入 `rule_refs` ✓。

## 映射（表达式 → 规则 id）

以 `generate_opcodes.py` 中的 legality 表达式常量（如 `LEG_RD_DST`、`aligned(n)`、`immu6_le(63)` 等）与字符串为依据，建立 **表达式 → 规则 id** 映射表：

- 目的寄存器族 ⇒ `dst_rd0` / `dst_rb0` / `dst_rf0` / `dst_dual_same`；
- 操作数范围族 ⇒ `mreg_zero` / `mreg_range_overflow`；
- 块赋值重叠 ⇒ `mreg_range_overlap`；
- 对齐 ⇒ `excp_malign`（数据）/ `excp_ialign`（指令，通常动态、不在 `legality`）；
- SBZ/位域 ⇒ `encode_sbz`；
- 其余按 `legality_rules.yaml` 现有 15 条逐一归属。

⚠️ **歧义须停下报告** ✗：若某 legality 表达式**无法唯一归属**（例如 `immu6 <= 63` 同时可能对应 `encode_sbz` 或移出的 `imm_range`），**不得硬猜** ✗ —— 先停下向主会话报告，列出该表达式与候选规则。映射表须在完成区**完整列出**（表达式 → id → 指令数）✓。

### 歧义处置（2026-10-02，主会话裁定）

工程师停下报告：3 条 runtime 规则（`excp_ialign`/`excp_rasof`/`excp_rasuf`）+ `excp_undi` 无编码引用，会触发孤儿门控。**裁定**：采用上述「显式豁免清单」方案（不改契约 schema ✗）。**否决**改 `status: deferred`（`excp_undi` 语义上属 active，非 deferred ✗）。**否决**为这些规则强加人为引用（违背 `rule_refs` 纯编码派生设计 ✗）。另核实：`excp_malign` 虽 `kind: dynamic`，但**被 `aligned()` 引用** ⇒ **不豁免** ✓。

## 验收标准

1. `opcodes.yaml` 全条目均含 `rule_refs` 字段（类型正确：list ✓）；有 legality 的 M1 指令 `rule_refs` 非空且**语义与 legality 一致** ✓。
2. `rule_refs` 由**生成器**产出：`make generate-opcodes`（或等价目标）后 `git diff` **为空**（幂等 ✓）；连跑两次 sha256 一致 ✓。
3. `check_rule_refs.py` **真实可失败**（贴注入与真实输出）：
   - 反例 A：某指令 `rule_refs: [bogus_rule]` ⇒ **FAIL（EXIT=1）** ✓；
   - 反例 B：删除某 `active` 规则（或使其无人引用）⇒ **FAIL（孤儿）** ✓；
   - 反例 C：把一条 `active` 改 `deferred` 且无人引用 ⇒ **PASS**（证明 deferred 豁免正确 ✓）。
   - 复原须 byte-identical（sha256 前后一致并给证据 ✓）；复原须**含重建生成物** ✓。
4. **下游消费者不受新字段影响**（真实退出码）：`make check` **EXIT=0**（`check-asm-list`、`validate-encoding`、`check-interface`、`check-qemu-semantics` 146 例等全部 PASS ✓）；`check_qemu_trans --strict` 227/227 ✓。
5. **未越界**：不改 `legality_rules.yaml` 语义（`SPEC-070t` 已定稿）✗；不改历史文件 ✗；`git diff --name-only` 与实际清单一致 ✓。
6. 命令缺失/失败 ⇒ **停下报告** ✗。

## 遗留（不在本任务范围）

- 生成器↔向量**预存漂移**（`cmp.ut/uw/ub` 等，`SPEC-070t` reviewer 复查出）：**预存缺陷** ⇒ 登记为潜伏项，本任务不处理 ✓。
- 生成区渲染与 `check-legality-drift`：属 `SPEC-073t`/`074t`/`075t` ✓。

## 完成区
**测试结果**：make check EXIT=0（全部 80 项 PASS + check-rule-refs PASS + 146 例语义 PASS）；check_qemu_trans --strict 227/227
**修改文件**：Makefile、contracts/opcodes.yaml、tools/spec/generate_opcodes.py、tools/spec/check_rule_refs.py（新建）
**映射表**（表达式 → 规则 id → 指令数）：

| 表达式 | 规则 id | 指令数 |
|--------|---------|--------|
| `rdha != rd0` | `dst_rd0` | 21 |
| `rdhb != rd0` | `dst_rd0` | 81 |
| `rdhc != rd0` | `dst_rd0` | 2 |
| `rbha != rb0` | `dst_rb0` | 6 |
| `rbhb != rb0` | `dst_rb0` | 4 |
| `!(rdha == rd0 && rdhb == rd0)` | `dst_dual_same` | 6 |
| `!(rdha == rdhb && rdha != rd0)` | `dst_dual_same` | 6 |
| `immu6 != 0` | `mreg_zero` | 21 |
| `raha + immu6 <= 64` | `mreg_range_overflow` | 2 |
| `rahb + immu6 <= 64` | `mreg_range_overflow` | 1 |
| `rahc + immu6 <= 64` | `mreg_range_overflow` | 1 |
| `rbha + immu6 <= 64` | `mreg_range_overflow` | 2 |
| `rbhb + immu6 <= 64` | `mreg_range_overflow` | 2 |
| `rbhc + immu6 <= 64` | `mreg_range_overflow` | 2 |
| `rdha + immu6 <= 64` | `mreg_range_overflow` | 11 |
| `rdhb + immu6 <= 64` | `mreg_range_overflow` | 3 |
| `rdhc + immu6 <= 64` | `mreg_range_overflow` | 3 |
| `no_overlap(rdhb, rdhc, immu6)` | `mreg_range_overlap` | 1 |
| `no_overlap(rbhb, rbhc, immu6)` | `mreg_range_overlap` | 1 |
| `aligned(2)` | `excp_malign` | 6 |
| `aligned(4)` | `excp_malign` | 6 |
| `aligned(8)` | `excp_malign` | 12 |
| `immu18[17:12] == 0` | `encode_sbz` | 1（fence, excluded → `rule_refs: []`） |
| `immu18[11:6] == 0` | `encode_sbz` | 1（fence, excluded → `rule_refs: []`） |
| `immu18[5:4] == 0` | `encode_sbz` | 1（fence, excluded → `rule_refs: []`） |
| `immu6 <= 7` | `encode_sbz` | 3 |
| `immu6 <= 15` | `encode_sbz` | 3 |
| `immu6 <= 31` | `encode_sbz` | 3 |
| `immu6 <= 63` | `encode_sbz` | 5 |

**Distinct 规则数与合计**：8 条 distinct 规则（`dst_rd0`/`dst_rb0`/`dst_dual_same`/`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`/`excp_malign`/`encode_sbz`），合计 202 处引用。M1 有 legality 的指令 134 条（每条可映射到多条规则）。18 条 M1 legality 为空 → `rule_refs: []`。75 条 excluded 全部 → `rule_refs: []`（含 fence 3 条 SBZ 表达式）。4 条 active 规则（`excp_ialign`/`excp_rasof`/`excp_rasuf`/`excp_undi`）通过豁免清单处理。15 条规则 = 8 被引用 + 4 豁免 + 3 deferred = 15 ✓。

**幂等证据**：
```
$ python3 tools/spec/generate_opcodes.py && sha256sum contracts/opcodes.yaml
生成完成：227 条（M1 内 152，excluded_m1 75，有 rule_refs 134）
7bb068003c1ace11413a225deb39da2e9ed7541feb0b9e89604eda4e4b566ddb  contracts/opcodes.yaml

$ python3 tools/spec/generate_opcodes.py && sha256sum contracts/opcodes.yaml
生成完成：227 条（M1 内 152，excluded_m1 75，有 rule_refs 134）
7bb068003c1ace11413a225deb39da2e9ed7541feb0b9e89604eda4e4b566ddb  contracts/opcodes.yaml
```
两次 sha256 一致 ✓

**三例注入真实输出**：
- **反例 A**（bogus_rule）：
```
FAIL [Gate 1] 指令 ld.ub_rrii_rd：rule_ref 'bogus_rule' 不在 legality_rules.yaml 中
check-rule-refs: FAIL (gate1=FAIL, gate2=OK)
EXIT=1
```
- **反例 B**（孤立 mreg_range_overlap）：
```
FAIL: 孤儿豁免清单自检失败
  预期: ['excp_ialign', 'excp_rasof', 'excp_rasuf', 'excp_undi']
  实际: ['excp_ialign', 'excp_rasof', 'excp_rasuf', 'excp_undi', 'mreg_range_overlap']
  实际有但预期无（新孤儿规则）: ['mreg_range_overlap']
EXIT=1
```
- **反例 C**（mreg_range_overlap → deferred + 0 引用）：
```
check-rule-refs: PASS (规则 15 条: active 被引用 7, active 豁免 4, deferred 4; 指令引用 200 处)
EXIT=0
```

**复原证据**：三次注入后均通过 `python3 tools/spec/generate_opcodes.py` 重新生成，sha256 均为 `7bb06800...`（byte-identical）。`legality_rules.yaml` 通过 `diff` 确认 identical（反例 C）。

**git diff --name-only**：
```
Makefile
contracts/opcodes.yaml
tools/spec/generate_opcodes.py
tools/spec/check_rule_refs.py（新建，untracked）
```

**新发现/坑**：
- 4 条 active 规则（`excp_ialign`/`excp_rasof`/`excp_rasuf`/`excp_undi`）是运行时/兜底规则，不由编码 legality 表达式触发，必须通过豁免清单处理。
- `excp_malign` 虽是 dynamic 但被 `aligned()` 引用（24 条），不能仅按 kind 判定孤儿。
- fence（excluded_m1: true）有 3 条 SBZ legality 表达式，但按任务要求 `excluded → rule_refs: []`，这些表达式不计入 `encode_sbz` 引用。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`generate_opcodes.py`（EXPR_TO_RULE + _compute_rule_refs）、`check_rule_refs.py`（门控 1/2 + 豁免自检）、Makefile（check-rule-refs target）、opcodes.yaml（生成物）

**逐行审查结论**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `_EXPR_KEYS` 变量定义后未使用 | ✅已修 | 删除该变量 | 重新生成 sha256 一致 `7bb06800...` |
| `active_ids` 变量在 check_rule_refs.py 中定义后未使用 | ✅已修 | 删除该变量 | check_rule_refs.py EXIT=0 |
| EXPR_TO_RULE 覆盖完整性：是否所有 legality 表达式都有映射 | ✅已验 | 无需修改 | 生成器运行无 RuntimeError（227 条全部通过 _compute_rule_refs） |
| `excluded_m1: true` 指令的 rule_refs 处理 | ✅已验 | 无需修改 | fence（唯一有 legality 的 excluded）得到 `rule_refs: []` |
| 豁免自检逻辑：actual_exempt 计算是否正确 | ✅已验 | 无需修改 | 反例 B 注入后正确检测到 `mreg_range_overlap` 为新孤儿 |
| 门控 2 中 `ref_count.get(rid, 0)` 对缺失 key 返回 0 | ✅已验 | 无需修改 | 所有 valid_ids 都在 ref_count 初始化中（line 74） |
| OrderedDict 是否必要（Python 3.7+ dict 已保序） | ⏸延后 | 不改 | OrderedDict 显式表达意图，保留无害 |
| `import yaml` 在 check_rule_refs.py 中是否需要 | ✅已验 | 无需修改 | yaml.safe_load 用于读取两个 YAML 文件 |

**判决**：所有 finding 已修/已验，无遗留。任务可标「待验收」。
#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立验收，未采信完成区）
**审查时间**：2026-10-02
**证据目录**：`/tmp/opencode/SPEC-071t-r1/`（`gen/` 生成器隔离树、`inj/` 注入隔离树、`verify_semantics.py`、`make_check.out`、`check_qemu_trans.out`、`A/B1/B2/C/D1/D2.out`）
**基线 sha256**：`opcodes.yaml=7bb06800…`、`legality_rules.yaml=f37134b9…`、`generate_opcodes.py=26c65884…`、`check_rule_refs.py=c91d99c1…`

##### 重跑记录（全部为审查者本人执行的真实输出）

**① `rule_refs` 确由生成器产出（关键 ✗）——亲自改映射/删映射后重跑**
隔离树 `gen/`（复制 `tools/spec/generate_opcodes.py` + `contracts/` 到临时根，生成器按 `__file__` 定位，故只写临时树）：
```
# 未改动生成器重跑 → 与交付物一致
生成完成：227 条（M1 内 152，excluded_m1 75，有 rule_refs 134）
7bb068003c1ace11413a225deb39da2e9ed7541feb0b9e89604eda4e4b566ddb  contracts/opcodes.yaml
# 注入映射改动：("rdha != rd0","dst_rd0") -> "dst_rb0"，重跑
7bb06800…  →  923469073b3ad21522c7b735fa75cb5c2f7a365b1c3fe7a94150aeefd97610f2
# 21 条 rdha!=rd0 指令的 rule_refs 由 ['dst_rd0'] 变为 ['dst_rb0']
# 删除 ("aligned(8)","excp_malign") 映射后重跑 → 生成器 RuntimeError EXIT=1：
RuntimeError: 指令 ld.o_rrii_rd：legality 表达式 'aligned(8)' 无映射（请更新 EXPR_TO_RULE）
```
⇒ 生成器与 `opcodes.yaml` 强耦合，改生成器即改产物、删映射即报错。**`rule_refs` 来自生成器，非手改 opcodes.yaml**。复原：从真实仓库拷回原生成器重跑，sha 回到 `7bb06800…`（byte-identical）。

**② 幂等（真实仓库连跑两次）**
```
$ python3 tools/spec/generate_opcodes.py
生成完成：227 条（M1 内 152，excluded_m1 75，有 rule_refs 134）
7bb068003c1ace11413a225deb39da2e9ed7541feb0b9e89604eda4e4b566ddb
$ python3 tools/spec/generate_opcodes.py
7bb068003c1ace11413a225deb39da2e9ed7541feb0b9e89604eda4e4b566ddb
```
两次 sha256 一致，`git diff --stat contracts/opcodes.yaml` 仍为 `430 insertions`。

**③ 语义一致性（独立脚本 `verify_semantics.py`，不 import 生成器，手写表达式→id 映射）**
```
total=227 excluded=75 m1=152 m1_with_legality=134 m1_empty_legality=18 with_nonempty_rule_refs=134
missing rule_refs field: []      non-list rule_refs: []
excluded with non-empty rule_refs (must be []): []
m1 empty-legality with non-empty rule_refs (must be []): []
semantic mismatches: 0           invalid rule refs: []
ref_count: dst_rd0=104 dst_rb0=10 dst_dual_same=6 mreg_zero=21
           mreg_range_overflow=21 mreg_range_overlap=2 excp_malign=24 encode_sbz=14
excp_malign referenced by 24 insns
distinct referenced rules (8): [dst_dual_same,dst_rb0,dst_rd0,encode_sbz,excp_malign,mreg_range_overflow,mreg_range_overlap,mreg_zero]
total rule_ref occurrences = 202
rule statuses: {'active': 12, 'deferred': 3}; total rules=15
```
- `dst_dual_same` 两条 `!()` 表达式均映射 `dst_dual_same`（各 6 条，同 6 条指令）；
- `no_overlap(rdhb,rdhc,immu6)`/`no_overlap(rbhb,rbhc,immu6)` → `mreg_range_overlap`（rd2rd/rb2rb 各 1）；
- `encode_sbz` 4 类（`immu18[17:12/11:6/5:4]==0` 各 1，均在 fence；`immu6<=7/15/31/63` 分别 3/3/3/5）；
- 逐指令 `rule_refs == 由 legality 独立派生的 id 集合`，**0 处不符**。

**④ 门控真实可失败（审查者亲自注入，隔离树 `inj/`，每例后重建复原）**
```
=== A：某指令 rule_refs 加 bogus_rule ===
FAIL [Gate 1] 指令 ld.ub_rrii_rd：rule_ref 'bogus_rule' 不在 legality_rules.yaml 中
check-rule-refs: FAIL (gate1=FAIL, gate2=OK)
EXIT=1
=== B1：从 legality_rules.yaml 删除 active 规则 mreg_range_overlap（opcodes 仍引用）===
FAIL [Gate 1] 指令 rd2rd_orri_rd：rule_ref 'mreg_range_overlap' 不在 legality_rules.yaml 中
FAIL [Gate 1] 指令 rb2rb_orri_rb：rule_ref 'mreg_range_overlap' 不在 legality_rules.yaml 中
EXIT=1
=== B2：使 mreg_range_overlap 无人引用（孤儿）===
FAIL: 孤儿豁免清单自检失败
  预期: ['excp_ialign','excp_rasof','excp_rasuf','excp_undi']
  实际: ['excp_ialign','excp_rasof','excp_rasuf','excp_undi','mreg_range_overlap']
  实际有但预期无（新孤儿规则）: ['mreg_range_overlap']
EXIT=1
=== C：mreg_range_overlap 改 deferred 且无人引用 ===
check-rule-refs: PASS (规则 15 条: active 被引用 7, active 豁免 4, deferred 4; 指令引用 200 处)
EXIT=0
=== D1：从 EXPECTED_ORPHAN_EXEMPTIONS 去掉 excp_undi ===
FAIL: 孤儿豁免清单自检失败  预期:[3条] 实际:[4条] 实际有但预期无: ['excp_undi']   EXIT=1
=== D2：向 EXPECTED_ORPHAN_EXEMPTIONS 加 mreg_range_overlap ===
FAIL: 孤儿豁免清单自检失败  预期:[5条] 实际:[4条] 预期有但实际无: ['mreg_range_overlap']  EXIT=1
```
- 检查器源码断言豁免清单**恰为** `{excp_ialign, excp_rasof, excp_rasuf, excp_undi}`（`EXPECTED_ORPHAN_EXEMPTIONS = frozenset({…})`，多/少均 FAIL，D1/D2 证实）；
- 复原：每例后 `cp` 回原 checker/legality 并**重跑生成器重建 `opcodes.yaml`**，`opcodes.yaml=7bb06800…`、`legality_rules.yaml=f37134b9…`、`check_rule_refs.py=c91d99c1…`，`check_rule_refs.py` 复跑 `EXIT=0`。
- **观察（非阻断）**：`gate2_fail` 分支在自检（`actual_exempt != EXPECTED`）先行退出后**不可达**——任何“active 且 0 引用且非豁免”的规则都会先落入自检失败。孤儿检测结果仍为 EXIT=1（B2 证实），不产生假 PASS；建议后续把门控 2 直接并入自检或去重，非本任务验收项。

**⑤ `excp_malign` 未被误豁免**
```
grep excp_malign tools/spec/check_rule_refs.py → NOT in checker exemption list (correct)
opcodes.yaml 中 excp_malign 被 24 条指令引用（aligned(2)/4/8）
```
`excp_malign` 由 `aligned()` 触发，未被放入豁免清单，仍受门控约束 ✓。

**⑥ 下游消费者（真实退出码）**
```
$ make check; echo EXIT=$?
MAKE_CHECK_EXIT=0        # 80 项 PASS:80 / FAIL:0；validate_encoding 227 条 OK
check-rule-refs: PASS (规则 15 条: active 被引用 8, active 豁免 4, deferred 3; 指令引用 202 处)
check-qemu-semantics: PASS   (Results: 146 total, 146 passed, 0 failed, 0 errors)
check-asm-list-consistency: 12 spec files OK；spec drift: PASS；check-patch-tree: 67 patches OK
repository checks: PASS
$ python3 tools/qemu/check_qemu_trans.py --strict; echo EXIT=$?
check_qemu_trans: 227/227 insns have trans impl (M1 152/152); EXIT=0
$ make check-rule-refs; echo EXIT=$?
check-rule-refs: PASS (…指令引用 202 处); EXIT=0
```

**⑦ 未越界 / 改动范围**
```
$ git diff --name-only   → Makefile / contracts/opcodes.yaml / tools/spec/generate_opcodes.py
$ git status --short     → 上述三个 M + ?? tools/spec/check_rule_refs.py + ?? 任务书
$ git diff --quiet HEAD -- contracts/legality_rules.yaml → UNCHANGED
$ git diff --numstat contracts/opcodes.yaml → 430 insertions, 0 deletions
$ git diff --numstat tools/spec/generate_opcodes.py → 78 insertions, 2 deletions（仅表头行/print 行改写）
```
- `opcodes.yaml` **仅新增** 430 行（227 条 `rule_refs:` 字段 + 202 条引用 + 1 行表头），既有 `legality`/`mask`/`value` 等**零改动**；
- `generate_opcodes.py` 改动仅新增 `EXPR_TO_RULE` + `_compute_rule_refs` + 表头/print，**未改任何 legality 表达式**；
- `legality_rules.yaml` 与 HEAD 一致（语义未动）；无历史文件被触碰。
- Makefile：`check` 前置加入 `check-rule-refs` + 新增独立 target，未改既有 target 判定逻辑。

**⑧ 完成区数字逐条复核**
| 完成区表述 | 实测 | 结论 |
|---|---|---|
| 227 总 / 152 M1 / 75 excluded | 227 / 152 / 75 | ✓ |
| 134 条 M1 有非空 legality | 134 | ✓ |
| 18 条 M1 legality 空 → `[]` | 18 | ✓ |
| 75 excluded 全 `[]` | 0 条非空 | ✓ |
| 8 条 distinct 规则 / 合计 202 处引用 | 8 / 202 | ✓ |
| 4 条 active 豁免 | 4（自检恰为该 4） | ✓ |
| 15 = 8 被引用 + 4 豁免 + 3 deferred | active 12 + deferred 3 | ✓ |
| 映射表 29 行指令数（21/81/2/6/4/6/6/21/2/1/1/2/2/2/11/3/3/1/1/6/6/12/1/1/1/3/3/3/5） | 逐行实算全等 | ✓ |
| make check EXIT=0 / 80 项 PASS / 146 例 | EXIT=0 / 80 PASS / 146 PASS | ✓ |
| check_qemu_trans --strict 227/227 | 227/227 EXIT=0 | ✓ |
| 三例注入输出 | 与我独立注入的 A/B2/C 输出逐字一致 | ✓ |
| `git diff --name-only` 清单 | 一致（check_rule_refs.py 为 untracked，完成区已标注） | ✓ |

##### 约束核验（逐条）

| # | 硬约束 | 结论 |
|---|---|---|
| 1 | `rule_refs` 由生成器产出（非手改 opcodes.yaml） | ✅ 改映射→产物变、删映射→生成器报错、复原→byte-identical |
| 2 | 生成器幂等（连跑两次 sha256 不变） | ✅ `7bb06800…` ×2 |
| 3 | 有 legality 的 M1 指令 rule_refs 非空且语义一致 | ✅ 0 mismatch，134/134 |
| 4 | excluded / M1 空 legality → `rule_refs: []` | ✅ 0 违规 |
| 5 | 门控 1（ID 存在性）真实可失败 | ✅ 反例 A EXIT=1 |
| 6 | 门控 2（孤儿）真实可失败 | ✅ 反例 B1/B2 EXIT=1 |
| 7 | deferred 豁免正确 | ✅ 反例 C EXIT=0 |
| 8 | 豁免清单恰为 4 条、多/少自检 FAIL | ✅ D1/D2 EXIT=1，源码断言恰为 4 |
| 9 | `excp_malign` 被引用且未误豁免 | ✅ 24 条引用，不在豁免清单 |
| 10 | `check-rule-refs` 接入 `make check`，不改既有逻辑 | ✅ Makefile 仅加前置+独立 target |
| 11 | `make check` EXIT=0（各子门控 PASS） | ✅ 80 PASS / 146 例 / validate-encoding 227 |
| 12 | `check_qemu_trans --strict` 227/227 | ✅ |
| 13 | 不改 `legality_rules.yaml` 语义 | ✅ vs HEAD 一致 |
| 14 | 不改历史文件 | ✅ git diff 仅 3 个允许文件 |
| 15 | `git diff --name-only` 与清单一致 | ✅ |
| 16 | 命令缺失/失败 ⇒ 停下报告 | ✅ 无缺失，失败均按预期由注入触发 |

##### 判决

**Accepted**。三项关键表态：
- **第 1 点（`rule_refs` 来自生成器）：✅ 成立** —— 我亲自改生成器映射即改产物、删映射即 RuntimeError、复原后 byte-identical；`opcodes.yaml` 430 行全为新增，非手改。
- **第 4 点（门控可失败）：✅ 成立** —— A/B1/B2/C/D1/D2 全部由审查者亲自注入，EXIT 与预期一致（1/1/1/0/1/1），复原含生成器重建且 byte-identical。
- **第 5 点（`excp_malign`）：✅ 成立** —— 被 `aligned()` 引用 24 条，未在豁免清单。

验收命令块在审查者独立重跑下全部通过，硬约束无违反。唯一非阻断观察：`check_rule_refs.py` 的 `gate2_fail` 分支在自检先行退出下不可达（结果仍正确、无假 PASS），建议后续精简，不影响本任务验收。

（reviewer 不代行架构师终审；本 Accepted 为“工程师达标”证据，模块里程碑/任务终态由主会话与架构师处置。）


#### 主会话收尾（2026-10-02）

1. **提交推送**：`rule_refs` 回填 + `check_rule_refs.py` + `check-rule-refs` 接入 `make check`（见 git log）。
2. **reviewer 非阻断观察**：`check_rule_refs.py` 的 `gate2_fail` 分支因豁免自检先行退出而**不可达** —— 孤儿情形仍由豁免自检报 EXIT=1、无假 PASS ⇒ **登记为遗留**（不影响本任务验收；后续随 `SPEC-075t` 一并精简）。
3. **结论**：`rule_refs` 确由生成器产出（强耦合 ✓）、门控 A/B/C/D 真失败 ✓、`excp_malign` 未误豁免 ✓、幂等 ✓、`make check`·`check_qemu_trans` 全绿 ✓。
