# SPEC-080t: 生成器真空合法性约束修正（`.o` orri 的 `immu6 <= 63`）+ 重生成

**模块**：spec（`tools/spec/` + `contracts/` + `spec/`）
**项目里程碑**：M2
**依赖**：`SPEC-070t`/`071t`/`074t`（合法性清单生成式已落地）
**状态**：已验证

## 现象与根因

`contracts/opcodes.yaml` 中 **5 条** 指令带**恒真**的合法性表达式 `immu6 <= 63`，并被映射到 `encode_sbz`（SBZ 非零 → ILLI）：

| 指令 | 现 `legality` / `rule_refs` |
|---|---|
| `ext.uo_orri_rd`、`ext.so_orri_rd`、`shl.uo_orri_rd`、`shr.so_orri_rd`、`shr.uo_orri_rd` | `['rdhb != rd0', 'immu6 <= 63']` / `['dst_rd0', 'encode_sbz']` |

**`immu6` 是 6 位字段（0–63）** ⇒ `immu6 <= 63` **恒真、永不触发** ⇒ 归入 `encode_sbz` **错误** ✗。
`spec/SimRISC-04` 正文自证：L218 `shl.uo/shr.so/shr.uo` 移位量 **0–63、`hd[5:0]` 全有效**；L231/L235 `ext.uo/ext.so` 的 `hd ≤ 63`。⇒ **`SimRISC-04` 不应有任何 `encode_sbz`**。

**根因**：`tools/spec/generate_opcodes.py` **L529–530** 对 MISC-octa（`.o`）orri 位运算**硬编码** `["rdhb != rd0", "immu6 <= 63"]`。
（`.ut/.st/…` 的 `immu6 <= 31/15/7` **非真空** ⇒ 正确保留，`SimRISC-08/09/10` 不受影响 ✓。）

## 改动

1. **`tools/spec/generate_opcodes.py` L529–530**：`.o` orri 位运算的 legality 改为 **`["rdhb != rd0"]`**（**删除真空的 `"immu6 <= 63"`**）。
2. **重生成 `contracts/opcodes.yaml`**（`make` 生成目标或直接跑生成器）：上述 5 条的 `legality` 去 `immu6 <= 63`、`rule_refs` 去 `encode_sbz`。
3. **重生成各章 `LEGALITY` 生成区**（`tools/spec/gen_legality_list.py --apply`）：`spec/SimRISC-04` 的 `encode_sbz` 行**消失**；`SimRISC-08/09/10` 的 `encode_sbz`（`31/15/7`）**保持不变** ✓。
4. **`contracts/legality_rules.yaml` 的 `encode_sbz` description**：删除**不可能条件**「`shl.uo/shr.so/shr.uo: shamt > 63`」（`immu6` 6 位 ⇒ 不可能）；其余（`fence`/`.ut/.uw/.ub`/`ext`/`lr`）保留。
5. **幂等**：两个生成器（`generate_opcodes.py`、`gen_legality_list.py`）连跑两次输出一致。

## 范围外 ✗
- **不动** QEMU/LLVM（真空约束从未触发，实现无行为改变）；
- **不动** `tests/vectors/**`（与已登记的 #1 生成器↔向量漂移无关）；
- 不改历史文件；不改 `ADR`。

## 验收标准（须真实可失败）

1. `contracts/opcodes.yaml` 中 **`immu6 <= 63` = 0**（`grep`/脚本核实）；上述 5 条 `rule_refs` 不含 `encode_sbz` ✓。
2. `spec/SimRISC-04` 生成区**无 `encode_sbz`**；`SimRISC-08/09/10` 的 `encode_sbz`（`31/15/7`）**仍在**且条数不变 ✓。
3. **门控**：`make check` **EXIT=0**（`check-legality-drift` 12 章、`check-rule-refs`、`validate-encoding`、`check-asm-prose` 0 等）。
4. **反例承重** ⚠️（二选一或都做）：
   - A：在**生成器**里把 `"immu6 <= 63"` 加回 `.o` orri、**只重生成 `opcodes.yaml` 而不重生成 LEGALITY 区** ⇒ `check-legality-drift` **FAIL**；
   - B：手改 `SimRISC-04` 生成区（加/删一行）⇒ `check-legality-drift` **FAIL**；复原 byte-identical。
5. **幂等**（两生成器两次 sha 一致）。
6. **未越界**：`git diff --name-only` ⊆ `tools/spec/generate_opcodes.py`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`spec/SimRISC-04-*.md`、任务书；历史文件干净 ✓。
7. 退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）；命令失败 ⇒ 停下报告 ✗。

## 完成区
**测试结果**：`make check` EXIT=0（25/25 PASS，repository checks PASS）
**修改文件**：
- `tools/spec/generate_opcodes.py` — L530 `["rdhb != rd0", "immu6 <= 63"]` → `["rdhb != rd0"]`
- `contracts/opcodes.yaml` — 重生成，5条 `immu6 <= 63` + 5条 `encode_sbz` 删除
- `contracts/legality_rules.yaml` — `encode_sbz` description 删除 `shl.uo/shr.so/shr.uo: shamt > 63`
- `spec/SimRISC-04-64位数据运算.md` — LEGALITY 生成区 `encode_sbz` 行删除

**`immu6 <= 63` 归零证据**：
```
$ grep -c "immu6 <= 63" contracts/opcodes.yaml
0
```

**SimRISC-04/08/09/10 生成区前后对照**：
- **SimRISC-04**：改前2条（`dst_rd0` + `dst_dual_same` + `encode_sbz`），改后2条（`dst_rd0` + `dst_dual_same`），`encode_sbz` 行消失 ✓
- **SimRISC-08**：`encode_sbz`（`shl.ut/shr.st/shr.ut`，3条）保持不变 ✓
- **SimRISC-09**：`encode_sbz`（`shl.uw/shr.sw/shr.uw`，3条）保持不变 ✓
- **SimRISC-10**：`encode_sbz`（`shl.ub/shr.sb/shr.ub`，3条）保持不变 ✓
- `opcodes.yaml` 中 `encode_sbz` 总数：改前14条 → 改后9条（减5，即 SimRISC-04 的5条）

**反例承重 + 复原**：
- **A 方案**：在生成器里把 `"immu6 <= 63"` 加回 `.o` orri、只重生成 `opcodes.yaml` 不重生成 LEGALITY ⇒ `check-legality-drift` **FAIL**（`SimRISC-04 drift, EXIT=1`）
- **复原**：删回 `immu6 <= 63`、重生成 `opcodes.yaml` ⇒ SHA256 `696dbec78a801510e48d952b6a54577c62cd23cb03087a1b6442191743e159aa` 与正确状态一致（byte-identical）✓
- **复原后验证**：`check-legality-drift` 12 chapters OK, EXIT=0 ✓

**幂等证据**：
```
$ sha256sum contracts/opcodes.yaml  # 跑3次 generate_opcodes.py
696dbec78a801510e48d952b6a54577c62cd23cb03087a1b6442191743e159aa  (×3，一致)

$ python3 tools/spec/gen_legality_list.py --apply  # 跑2次
全部 "unchanged (idempotent)"（×2，一致）
```

**验收结果**：
1. ✅ `immu6 <= 63` = 0 in opcodes.yaml；5条 rule_refs 不含 `encode_sbz`
2. ✅ SimRISC-04 无 `encode_sbz`；SimRISC-08/09/10 各3条保持不变
3. ✅ `make check` EXIT=0（25/25 PASS）
4. ✅ 反例承重：A 方案 FAIL + 复原 byte-identical
5. ✅ 幂等：两生成器连跑两次输出一致
6. ✅ 未越界：`git diff --name-only` ⊆ 4个指定文件（QEMU-031t 文件未碰）
7. ✅ 退出码用 `cmd >log 2>&1; rc=$?`

**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：4个改动文件逐行审查

**1. `tools/spec/generate_opcodes.py` L530**
- 改动：`["rdhb != rd0", "immu6 <= 63"]` → `["rdhb != rd0"]`
- 正确性：immu6 是6位字段（0-63），`immu6 <= 63` 恒真，删除正确
- 影响范围：仅 `.o` orri 的5条指令（ext.uo/ext.so/shr.uo/shr.so/shl.uo），不影响 `.ut/.st/.uw/.ub` 的非真空约束
- **PASS**

**2. `contracts/opcodes.yaml`**
- 5条指令的 `legality` 从 `["rdhb != rd0", "immu6 <= 63"]` 变为 `["rdhb != rd0"]`
- 5条指令的 `rule_refs` 从 `["dst_rd0", "encode_sbz"]` 变为 `["dst_rd0"]`
- 其余 `encode_sbz`（SimRISC-08/09/10 各3条 + fence 相关）保持不变
- 由生成器自动产出，非手改，SHA256 幂等验证通过
- **PASS**

**3. `contracts/legality_rules.yaml`**
- 删除 `encode_sbz` description 中的 `shl.uo/shr.so/shr.uo: shamt > 63`
- 保留 `.ub/.uw/.ut` 的非真空条件
- 删除后句子语法通顺（`shamt > 31）；` 后接 `扩展起始位...`）
- **PASS**

**4. `spec/SimRISC-04-64位数据运算.md`**
- LEGALITY 生成区的 `encode_sbz` 行被 `gen_legality_list.py --apply` 自动删除
- 由生成器自动产出，非手改
- **PASS**

**边界情况**：
- `immu6 <= 63` 从 `EXPR_TO_RULE` 映射表中未删除（L717），因为 `.ut/.st/.ub` 变体仍可能用到 → 正确，不改
- `ext.uo/ext.so` 的 `orrr` 形式（`ext.uo_orrr_rd`）不受影响（用 `rdhd` 不用 `immu6`）→ 正确

**判决**：所有 finding 已修（0 finding），可标「待验收」

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（独立重跑，不采信完成区）
**证据留档**：`/tmp/opencode/SPEC-080t-r1/`
**HEAD**：`a38a976872f6549476ba9eaafcf3ab0035179b74`
**说明**：工作树另有在飞任务 QEMU-031t 的未提交改动（`components/qemu/**`、`tests/vectors/isa/{ctrl-br,reg-compare}.yaml`、`tools/qemu/min_rom_probe_031t.py`、QEMU-031t 任务书），**不属本任务**，不计入范围判定。

##### 1. 真空约束归零（验收点 1）— PASS
```
$ grep -c "immu6 <= 63" contracts/opcodes.yaml; echo "rc=$?"
0
rc=1                  # grep 无匹配 ⇒ 0（归零）
```
5 条（`ext.uo/ext.so/shl.uo/shr.so/shr.uo` 的 `orri_rd`）现 `legality=['rdhb != rd0']`、`rule_refs=['dst_rd0']`（用 YAML 解析器逐条读出，非文本近似）。
`encode_sbz` 总数 `HEAD:14 → now:9`（`git show HEAD:contracts/opcodes.yaml | grep -c` = 14；当前 = 9）；当前 9 条恰为 `.ut/.uw/.ub` 三组（`immu6 <= 31/15/7`）共 9 条，**其它 `encode_sbz` 未被误删** ✓。
`git diff contracts/opcodes.yaml` = **10 处纯删除**（5 条 `immu6 <= 63` + 5 条 `encode_sbz`），无其它改动。

##### 2. 生成区（验收点 2）— PASS
```
$ grep -rn "encode_sbz" spec/SimRISC-*.md
spec/SimRISC-08-32位数据运算.md:38:* `encode_sbz`…（3 条）
spec/SimRISC-09-16位数据运算.md:38:* `encode_sbz`…（3 条）
spec/SimRISC-10-8位数据运算.md:38:* `encode_sbz`…（3 条）
$ grep -c "encode_sbz" "spec/SimRISC-04-64位数据运算.md"; echo rc=$?
0
rc=1
```
`SimRISC-04` 生成区改前 3 类（`dst_rd0`/`dst_dual_same`/`encode_sbz`）→ 改后 2 类（`dst_rd0`/`dst_dual_same`），仅删 `encode_sbz` 行（`git diff` 单行删除）。
`SimRISC-08/09/10` 的三条 `encode_sbz` 与 HEAD **逐字相同**（`git show HEAD:…` 对比），文件未被 `git status` 标记为 modified。

##### 3. 生成器（验收点 3）— PASS
- `git diff tools/spec/generate_opcodes.py`：`L529` 的 `["rdhb != rd0", "immu6 <= 63"]` → `["rdhb != rd0"]`（在 `build_misc_octa` 的 `.o` orri 循环内），**是生成器改动，非手改 `opcodes.yaml`**。
- 幂等/生成式：连跑生成器 2 次，`sha256sum contracts/opcodes.yaml` 稳定为 `696dbec78a801510e48d952b6a54577c62cd23cb03087a1b6442191743e159aa`；与 HEAD 重生成无关，说明 `opcodes.yaml` 完全由该生成器驱动。
- `gen_legality_list.py --verify` → EXIT=0，12 章 OK；`--apply` 全部报 `unchanged (idempotent)`。

##### 4. 反例承重（验收点 4，reviewer 亲自执行 A 方案）— PASS
```
# 注入：把 "immu6 <= 63" 加回生成器 .o orri（单处，assert count==1）
$ python3 tools/spec/generate_opcodes.py   # 只重生成 opcodes.yaml，不重生成 LEGALITY
生成完成：227 条…
$ grep -c "immu6 <= 63" contracts/opcodes.yaml
5                                        # 注入生效（diff vs 正确备份新增 5×immu6 + 5×encode_sbz）
$ python3 tools/spec/check_legality_drift.py > … ; rc=$?
FAIL: 64位数据运算 (SimRISC-04-64位数据运算.md): LEGALITY content drift (first diff at line 6, expected 7 lines, got 6 lines)
1 violation(s) found, 11 OK
EXIT=1                                   # ★ FAIL，门控可失败
# 复原：还原生成器 + 重生成
$ cp …/generate_opcodes.py.correct tools/spec/generate_opcodes.py && python3 tools/spec/generate_opcodes.py
$ sha256sum contracts/opcodes.yaml
696dbec78a801510e48d952b6a54577c62cd23cb03087a1b6442191743e159aa
$ cmp contracts/opcodes.yaml …/opcodes.yaml.correct && echo BYTE-IDENTICAL
BYTE-IDENTICAL
$ python3 tools/spec/check_legality_drift.py; echo "EXIT=$?"
check-legality-drift: 12 chapters OK
EXIT=0
```
复原后 `tools/spec/generate_opcodes.py` SHA = `fc5fc5a4…b16211`（与审查前一致）；工作树无注入残留。
> 注：A 方案注入等价于把生成器该行回到 HEAD，故注入时 `git diff generate_opcodes.py` 为空；注入有效性由**重生成产物变化**（`+5 immu6 / +5 encode_sbz`）证明。

##### 5. `make check`（验收点 3/门控）— PASS
```
$ make check > make_check.log 2>&1; rc=$?; echo EXIT=$rc
EXIT=0
```
log 内关键行：
```
validate_vectors: 152/152 M1 identities covered OK
check-spec-drift: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check-asm-prose: PASS (0 violations)
check-legality-drift: 12 chapters OK
validate_encoding: 227 条记录 OK
check-rule-refs: PASS (规则 15 条…指令引用 197 处)
check-qemu-semantics: PASS (149/149)
check-lit: 25/25 PASS
check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

##### 6. 未越界（验收点 6）— PASS
`git status` 过滤掉 QEMU-031t 文件后，仅：
```
 M contracts/legality_rules.yaml
 M contracts/opcodes.yaml
 M spec/SimRISC-04-64位数据运算.md
 M tools/spec/generate_opcodes.py
?? .tao/tasks/spec/SPEC-080t-…（任务书）
```
⊆ 任务允许的 4 文件 + 任务书；**未碰** LLVM/QEMU/向量/历史文件（`ADR`、`manifests`、`docs/spec` 干净）。门控脚本本身（`check_legality_drift.py`/`gen_legality_list.py`/`check_rule_refs.py`/`validate_encoding.py`）均未改动 —— 非凑绿。

##### 7. 完成区逐条复读 — PASS（1 处叙述笔误，不影响交付）
- 4 个文件的改动、SHA256、反例 A FAIL+复原 byte-identical、`make check` EXIT=0、25/25 —— **与本审查真实输出逐条一致**。
- 笔误：完成区「SimRISC-04：改前**2**条（`dst_rd0`+`dst_dual_same`+`encode_sbz`）…」计数与所列为 3 类矛盾；实际**改前 3 条 → 改后 2 条**。属叙述计数笔误，非产出缺陷，不构成返工。

##### 遗留观察（非阻断）
- `EXPR_TO_RULE` L717 仍保留 `("immu6 <= 63", "encode_sbz")` 映射；现无任何记录使用 `<=63`（`.ut/.uw/.ub` 为 31/15/7），该映射成为**死项**。任务未要求删除，工程师已在自审中显式说明保留理由；不影响正确性，可留待后续清理。

##### 判决
**Accepted** —— 验收点 1–7 在 reviewer 独立重跑下全部通过；第 1、3、4 点明确成立：真空约束已归零且生成器为唯一来源（1、3 PASS），反例 A 亲自注入后 `check-legality-drift` 真实 FAIL=1 且复原 byte-identical（4 PASS）。硬约束无违反，无凑绿。
（架构师终审仍可对上述「遗留观察」决定是否追加清理任务。）


#### 主会话收尾（2026-10-02）

1. **提交推送**：`generate_opcodes.py`（`.o` orri 去 `immu6<=63`）+ 重生成 `opcodes.yaml`/`SimRISC-04` LEGALITY 区 + `legality_rules.yaml` `encode_sbz` 描述（删不可能条件）（见 git log）。
2. **reviewer 第 1 轮 Accepted**：`immu6<=63`=0；5 条 `rule_refs=['dst_rd0']`；`SimRISC-04` 无 `encode_sbz`、`08/09/10` 逐字不变；**亲注入**（加回生成器 + 只重生成 opcodes）⇒ `check-legality-drift` **FAIL** + byte-identical 复原；`make check` EXIT=0。
3. **非阻断遗留**（登记）：
   - 完成区「改前 2 条」为**叙述笔误**（实为 3→2），不影响交付。
   - `generate_opcodes.py` 的 **`EXPR_TO_RULE` L717 `("immu6 <= 63","encode_sbz")` 已成死项**（无记录用 `<=63`）⇒ 未删（任务未要求），留后续清理。
