# SPEC-083t: ret rd0 ⇒ imms18 必须 0 — 规范与契约落地

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`SPEC-082t`、`LLVM-026t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/SimRISC-06-控制流.md`（§函数返回，当前 L133–135 无硬约束）
  - `.tao/knowledge/contract-isa.md`（§1.3.1 / §8.5，当前已有 `ret rd0, 0` 允许的说明，但缺 `rd0 ⇒ imms18==0` 的硬约束）
  - `tools/spec/generate_opcodes.py`（`ret_riii_ra` 当前 `legality: []`）
  - `contracts/legality_rules.yaml`（需新增规则条目）
  - `contracts/opcodes.yaml`（自动生成，不手改）

- **输出**：
  1. `spec/SimRISC-06-控制流.md`：§函数返回段新增约束表述
  2. `.tao/knowledge/contract-isa.md`：§1.3.1 或 §8.5 同步新增硬约束
  3. `tools/spec/generate_opcodes.py`：`ret_riii_ra` 的 `legality` 增加条件约束
  4. `contracts/legality_rules.yaml`：新增规则 ID/描述
  5. `contracts/opcodes.yaml`：由生成器重生成（含 `rule_refs`）
  6. 合法性清单：由 `tools/spec/gen_legality_list.py` 重生成
  7. 门控 `make check-legality-drift` + `make check-rule-refs` 通过

- **约束**：
  - 不改 `.tao/adr/adr-0013-assembly-syntax.md`
  - 不改 `spec/SimRISC-0.5.3/`
  - 不提交 git
  - 与 `ADR-0013 D3/D10`（汇编立即数字节化）正交，`ret` 的 `imms18` 编码名不变
  - `generate_opcodes.py` 的 `EXPR_TO_RULE` 映射需同步更新

## 验收标准

1. **规范文本**：`spec/SimRISC-06-控制流.md` §函数返回段明确写出：`ret rdHA, imms18` 中，当 `rdHA == rd0` 时，`imms18` MUST 为 0；否则**非法**：**汇编期硬报错**（LLVM，`Error` 级）+ **运行期 ILLI 0x88**（QEMU）。
2. **合约同步**：`.tao/knowledge/contract-isa.md` §1.3.1 或 §8.5 中新增相应硬约束表述，引用 `[SimRISC-06 §函数返回]`。
3. **生成器变更**：`tools/spec/generate_opcodes.py` 中 `ret_riii_ra` 的 `legality` 列表非空，包含条件约束表达式（如 `"rdha != rd0 or imms18 == 0"` 或等价形式）。
4. **规则目录**：`contracts/legality_rules.yaml` 新增一条规则，**ID = `dst_rd0_nonzero`**（与既有 `dst_rd0`/`dst_dual_same`/`dst_rb0` 的 `dst_*` 约定一致；用户确认），`kind: static`，`fault: ILLI`，`status: active`，`spec_cite: "SimRISC-06 §函数返回"`；`description` 须写清"**仅 `ret` 适用**：`rdha == rd0` 且 `imms18 != 0` ⇒ ILLI"。
5. **重生成**：运行 `python3 tools/spec/generate_opcodes.py` 后，`contracts/opcodes.yaml` 中 `ret_riii_ra` 的 `legality` 和 `rule_refs` 非空。
6. **合法性清单**：运行 `python3 tools/spec/gen_legality_list.py` 重生成清单文件，无报错。
7. **门控通过**：`make check-legality-drift` 和 `make check-rule-refs` 均 exit 0。
8. **自包含**：任务书不引用外部仓库文件作为执行依赖。

## 完成区

**测试结果**：8/8 验收项通过。反例门控 2 组均真实 FAIL 后还原回绿；两生成器幂等。

**修改文件**：
- `tools/spec/generate_opcodes.py`：新增常量 `LEG_RET_RD0_IMMS18 = "!(rdha == rd0 && imms18 != 0)"`；`ret_riii_ra` 的 `legality` 由 `[]` 改为 `[LEG_RET_RD0_IMMS18]`；`EXPR_TO_RULE` 新增 `("!(rdha == rd0 && imms18 != 0)", "dst_rd0_nonzero")`；注释计数 15→16。
- `tools/spec/gen_legality_list.py`（**任务书未列出，属支撑性必要改动，见「新发现/坑」#3**）：`SEMANTIC_MAP`/`RULE_SUMMARY` 新增 `dst_rd0_nonzero`；docstring 计数 15→16、134→135。
- `contracts/legality_rules.yaml`：新增规则 `dst_rd0_nonzero`（`kind: static`、`fault: ILLI`、`status: active`、`spec_cite: "SimRISC-06 §函数返回"`，description 写明「仅 ret 适用」）。
- `contracts/opcodes.yaml`：由生成器重生成（`ret_riii_ra` 的 `legality`/`rule_refs` 非空；header 有 rule_refs 条数 134→135）。
- `spec/SimRISC-06-控制流.md`：§函数返回 prose 新增硬约束段；LEGALITY 生成区由 `gen_legality_list.py --apply` 重生成（新增 `dst_rd0_nonzero` 行）。
- `.tao/knowledge/contract-isa.md`：§1.3.1、§8.5 新增硬约束；§15.1 ILLI 汇总补 `ret rd0` 且 `imms18 != 0` 条目（consistency 补充，见「遗留问题」）。

**验收结果**（真实命令 + 退出码；复杂命令日志见 `.work/log/spec/SPEC-083t-*.log`）：

验收 1（规范文本）：
```
$ grep -n '硬约束.*MUST.*0x88' spec/SimRISC-06-控制流.md
138:**（硬约束）**`ret rdHA, imms18` 中，当 `rdHA == rd0` 时，`imms18` **MUST** 为 0；否则该指令**非法**：汇编期须**硬报错**（LLVM，`Error` 级，汇编失败并返回非零退出码，**不得**降为 warning），运行期执行该非法编码触发 **ILLI** 异常（测试机退出码 `0x88`，QEMU）。
```
写明了 rdHA==rd0 ⇒ imms18 MUST 0、非法、汇编期硬报错（LLVM Error 级）、运行期 ILLI 0x88（QEMU）✅

验收 2（合约同步）：
```
$ grep -n 'rdHA == rd0` 时 `imms18` MUST 为 0' .tao/knowledge/contract-isa.md
39:  - `ret rd0, 0` 允许（无需设置返回值）；但 `rdHA == rd0` 时 `imms18` MUST 为 0，否则非法（ILLI）。[SimRISC-00 §数据寄存器][SimRISC-06 §函数返回]
（§8.5 同款硬约束条，均引 [SimRISC-06 §函数返回]）
```
✅

验收 3/5（生成器 + 重生成）：
```
$ python3 tools/spec/generate_opcodes.py        # EXIT=0
生成完成：227 条（M1 内 152，excluded_m1 75，有 rule_refs 135）-> /mnt/tao/DADAO-v5/contracts/opcodes.yaml
$ python3 -c "import yaml;r=[o for o in yaml.safe_load(open('contracts/opcodes.yaml')) if o['id']=='ret_riii_ra'][0];print(r['legality'], r['rule_refs'])"
['!(rdha == rd0 && imms18 != 0)'] ['dst_rd0_nonzero']
```
✅ `ret_riii_ra` 的 `legality`/`rule_refs` 均非空。

验收 4（规则目录）：
```
$ python3 -c "import yaml;r=[x for x in yaml.safe_load(open('contracts/legality_rules.yaml'))['rules'] if x['id']=='dst_rd0_nonzero'][0];print(r)"
{'id': 'dst_rd0_nonzero', 'fault': 'ILLI', 'kind': 'static', 'spec_cite': 'SimRISC-06 §函数返回', 'status': 'active', 'description': '仅 ret 适用：ret rdHA, imms18 中 rdha == rd0 且 imms18 != 0 时触发 ILLI 异常。…'}
规则总数 16；dst_* 集合 = dst_rd0/dst_rd0_nonzero/dst_dual_same/dst_rb0/dst_rf0
```
✅ 字段与验收 4 逐项一致。

验收 6（合法性清单重生成）：
```
$ python3 tools/spec/gen_legality_list.py --apply   # EXIT=0
gen-legality: Injected into /mnt/tao/DADAO-v5/spec/SimRISC-06-控制流.md
gen-legality: 其余 11 章 unchanged (idempotent)
$ sed -n '31,38p' spec/SimRISC-06-控制流.md
* `dst_rd0_nonzero`：ret 目的 rd0 时 imms18≠0 → ILLI — `ret_riii_ra`（1 条）
```
✅

验收 7（门控；EXIT=0）：
```
$ make check-legality-drift ; echo EXIT=$?
check-legality-drift: 12 chapters OK
EXIT=0
$ make check-rule-refs ; echo EXIT=$?
check-rule-refs: PASS (规则 16 条: active 被引用 9, active 豁免 4, deferred 3; 指令引用 198 处)
EXIT=0
```
✅ 附带回归门控全部 EXIT=0：`validate-encoding`（227 条 OK）、`check-asm-list`（12 spec files OK）、`check-asm-list-drift`（PASS byte-identical）、`check-asm-prose`（PASS 0 violations）、`check-spec-drift`（PASS）、`check-interface`（80/80）、`validate-vectors`（152/152）、`check-cfx-aliases`（PASS）、`check-dirs`（PASS）、`check-no-residue`（PASS）。

验收 8（自包含）：
```
$ grep -nE 'DADAO-0628|/DADAO/|\.cache/refs|manifests/' .tao/tasks/spec/SPEC-083t-*.md ; echo EXIT=$?
EXIT=1        # 无外部仓库引用
```
✅

**反例门控（须能失败）**：
- 反例 A（drift）：临时把生成器 `ret_riii_ra` 的 `legality` 还原为 `[]` 并**只**重生成 `opcodes.yaml`（不重生成 LEGALITY 区）：
```
$ python3 tools/spec/generate_opcodes.py
生成完成：227 条（…有 rule_refs 134）          # 较正确态 -1，注入生效
$ python3 tools/spec/check_legality_drift.py ; echo EXIT=$?
FAIL: 控制流 (SimRISC-06-控制流.md): LEGALITY content drift (first diff at line 4, expected 7 lines, got 8 lines)
1 violation(s) found, 11 OK
EXIT=1
```
复原（还原生成器 + 重生成）后 `cmp` ⇒ BYTE-IDENTICAL，`check-legality-drift` ⇒ `12 chapters OK` EXIT=0 ✅
- 反例 B（rule-refs）：临时把规则 id 改名 `dst_rd0_nonzero`→`dst_rd0_nonzero_DISABLED`：
```
$ python3 tools/spec/check_rule_refs.py ; echo EXIT=$?
FAIL: 孤儿豁免清单自检失败
  实际有但预期无（新孤儿规则）: ['dst_rd0_nonzero_DISABLED']
EXIT=1
```
复原后 `cmp` ⇒ BYTE-IDENTICAL，`check-rule-refs` ⇒ PASS EXIT=0 ✅

**幂等**：`generate_opcodes.py` 连跑 2 次，`sha256(contracts/opcodes.yaml)` 恒为 `be82d5ed0d836a4ffb32610a442fd7670b11611a4252ebac05561c0d625daf18`；`gen_legality_list.py --apply` 再跑输出全 `unchanged (idempotent)` EXIT=0。

**新发现/坑**：
1. **`or` 关键字会撞 `validate-encoding` 的标识符白名单**：`tools/spec/validate_encoding.py::check_legality_refs` 用 `[A-Za-z_][A-Za-z0-9_]*` 抽标识符，`ALLOWED_NON_FIELD` 只含 `rd0/rb0/ra0/rf0/aligned/no_overlap`，**不含 `or`/`and`**；实测 `"rdha != rd0 or imms18 == 0"` 会被判为「引用了不存在的字段 `or`」⇒ `validate-encoding` FAIL（即 `make check` 红）。故按验收 3 允许的「等价形式」，采用 `"!(rdha == rd0 && imms18 != 0)"`（De Morgan 等价，且与既有 `dst_dual_same` 的 `!(…)` 风格一致、不引入新操作符）。四值真值表核对 0 差异。**仅靠 `check-legality-drift`/`check-rule-refs` 两门控发现不了该问题，必须连带跑 `validate-encoding`。**
2. **`gen_legality_list.py` 的语义分组与摘要表是硬编码白名单**：`SEMANTIC_MAP` 未收录的 rule id 会落入 `"其它"`，而 `SEMANTIC_ORDER` 不含 `"其它"` ⇒ 该规则被**静默丢弃**、不出现在任何章 LEGALITY 区（dry-run 实测：去掉映射后控制流块 `dst_rd0_nonzero` 命中数 = 0）。新增合法性规则必须同步 `SEMANTIC_MAP`（+ `RULE_SUMMARY`），否则「规则存在但不可见」。
3. **`gen_legality_list.py` 属支撑性必要改动**：任务书「输出」未列该文件，但为让新规则出现在 LEGALITY 清单（验收 1/6 之意图）必须改；本任务仅新增两条映射 + 文档计数，未改渲染逻辑。

**遗留问题**：
- ✅已修（无未修 finding）。
- 提示（非本任务范围，供架构师判断是否立任务）：新规则 `dst_rd0_nonzero` 目前**无 ISA 合法性向量**——`tools/testcases/generate_isa_vectors.py::_ILLI_RULES` 仅覆盖 `dst_rd0/dst_dual_same/dst_rb0/mreg_zero`，不枚举全部规则（故 `validate-vectors` 仍绿）。运行期 ILLI 语义的端到端验证由 QEMU 侧任务承担（LLVM-027t 覆盖汇编期硬报错）。若需要「规则↔向量」全覆盖门控，建议另立 testcases 任务。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：6 个改动文件逐行 + 生成产物 + 门控 + 反例还原。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 任务书 要点给的 `"rdha != rd0 or imms18 == 0"` 会撞 `validate-encoding` 标识符白名单（`or` 非法） | ✅已修 | 采用 De Morgan 等价形式 `"!(rdha == rd0 && imms18 != 0)"`（验收 3 明列允许「等价形式」） | 真值表 4/4 一致；`make validate-encoding` EXIT=0 |
| 2 | 新增规则未加入 `gen_legality_list.py` 的 `SEMANTIC_MAP` 时会静默消失 | ✅已修 | `SEMANTIC_MAP`/`RULE_SUMMARY` 加 `dst_rd0_nonzero` | 去映射 dry-run 命中 0 → 加映射后 SimRISC-06 生成区含该行；`check-legality-drift` EXIT=0 |
| 3 | 仅改 §1.3.1/§8.5，§15.1「ILLI 触发场景（M1 汇总）」漏项，合约自相不完整 | ✅已修 | §15.1 补 `ret rd0` 且 `imms18 != 0` 条 | `check-spec-drift` PASS；§15.1 grep 命中 |
| 4 | 反例须证明约束「承重」且可复原 | ✅已验 | 反例 A/B | A：drift EXIT=1 + 还原 byte-identical + 回绿；B：rule-refs EXIT=1 + 还原 byte-identical + 回绿 |
| 5 | 生成器/规则目录是否幂等、是否有其它 15 条计数残留 | ✅已验 | docstring/注释计数 15→16、134→135 | opcodes sha 两次一致；`--apply` 全 unchanged；live 代码/文档无 `15 条` 残留（仅历史任务书记录不改） |

**逻辑正确性核对**：
- 语义方向：legality 存「允许条件」，`!(A && B)`（A=`rdha==rd0`，B=`imms18!=0`）⇔ `rdha != rd0 or imms18 == 0`，即「rd0 目的时 imms18 必须 0」；与规则 description、spec prose、contract-isa 一致。
- 范围隔离：该表达式只挂 `ret_riii_ra`；检索确认无其它指令使用同一表达式，`dst_rd0` 描述未受影响（`ret rd0,0` 例外仍准确）。
- 未改决策语义：ADR-0013 未触碰；`ret` 编码名 `imms18` 不变（本任务属 §函数返回 运行期/汇编期约束，与 D3/D10 正交）。

**判决**：5 项 finding 全部 ✅已修/已验，无未修项。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-03
**审查范围**：8 条验收 + 等价性核验 + `or` 关键字证真 + 反例门控 + 范围/越界 + `make check` 全量 + 完成区一致性

---

**一、验收逐条重跑（真实命令 + 退出码）**

**验收 1（规范文本）**：
```
$ grep -n '硬约束.*MUST.*0x88' spec/SimRISC-06-控制流.md
138:**（硬约束）**`ret rdHA, imms18` 中，当 `rdHA == rd0` 时，`imms18` **MUST** 为 0；否则该指令**非法**：汇编期须**硬报错**（LLVM，`Error` 级，汇编失败并返回非零退出码，**不得**降为 warning），运行期执行该非法编码触发 **ILLI** 异常（测试机退出码 `0x88`，QEMU）。
EXIT=0
```
✅ rdHA==rd0 ⇒ imms18 MUST 0、非法、汇编期硬报错（LLVM Error 级）、运行期 ILLI 0x88（QEMU）均写明。

**验收 2（合约同步）**：
```
$ grep -n 'rdHA == rd0` 时 `imms18` MUST 为 0' .tao/knowledge/contract-isa.md
39:  - `ret rd0, 0` 允许（无需设置返回值）；但 `rdHA == rd0` 时 `imms18` MUST 为 0，否则非法（ILLI）。[SimRISC-00 §数据寄存器][SimRISC-06 §函数返回]
EXIT=0
```
§1.3.1（line 39）及 §8.5（line 789）均含硬约束，引用 `[SimRISC-06 §函数返回]`。✅

**验收 3+5（生成器 + 重生成）**：
```
$ python3 tools/spec/generate_opcodes.py 2>&1
生成完成：227 条（M1 内 152，excluded_m1 75，有 rule_refs 135）-> /mnt/tao/DADAO-v5/contracts/opcodes.yaml
EXIT=0
$ python3 -c "import yaml;r=[o for o in yaml.safe_load(open('contracts/opcodes.yaml')) if o['id']=='ret_riii_ra'][0];print('legality:', r['legality']);print('rule_refs:', r['rule_refs'])"
legality: ['!(rdha == rd0 && imms18 != 0)']
rule_refs: ['dst_rd0_nonzero']
EXIT=0
```
✅ `ret_riii_ra` 的 legality/rule_refs 均非空，含条件约束表达式。

**验收 4（规则目录）**：
```
$ python3 -c "import yaml;...[field checks]..."
{'id': 'dst_rd0_nonzero', 'fault': 'ILLI', 'kind': 'static', 'spec_cite': 'SimRISC-06 §函数返回', 'status': 'active', 'description': '仅 ret 适用：...'}
All field assertions PASS
Total rules: 16
dst_* rules: ['dst_rd0', 'dst_rd0_nonzero', 'dst_dual_same', 'dst_rb0', 'dst_rf0']
EXIT=0
```
✅ 字段 id/kind/fault/status/spec_cite/description 逐项与验收 4 一致。

**验收 6（合法性清单重生成）**：
```
$ python3 tools/spec/gen_legality_list.py --apply 2>&1
gen-legality: Injected into /mnt/tao/DADAO-v5/spec/SimRISC-06-控制流.md
gen-legality: 其余 11 章 unchanged (idempotent)
EXIT=0
$ sed -n '/LEGALITY_START/,/LEGALITY_END/p' spec/SimRISC-06-控制流.md
* `dst_rd0_nonzero`：ret 目的 rd0 时 imms18≠0 → ILLI — `ret_riii_ra`（1 条）
```
✅ SimRISC-06 LEGALITY 生成区含 `dst_rd0_nonzero` 行。

**验收 7（门控）**：
```
$ make check-legality-drift 2>&1
check-legality-drift: 12 chapters OK
EXIT=0
$ make check-rule-refs 2>&1
check-rule-refs: PASS (规则 16 条: active 被引用 9, active 豁免 4, deferred 3; 指令引用 198 处)
EXIT=0
```
✅

**验收 8（自包含）**：
```
$ grep -nE 'DADAO-0628|/DADAO/|\.cache/refs|manifests/' .tao/tasks/spec/SPEC-083t-*.md ; echo EXIT=$?
EXIT=1
```
✅ 无外部仓库引用。

---

**二、等价性独立核验**

```
rdha==rd0  imms18!=0  |  A=(rdha!=rd0 or imms18==0)  B=!(rdha==rd0 && imms18!=0)  match
  True     True     |  False                        False                         ✓
  True     False    |  True                         True                          ✓
  False    True     |  True                         True                          ✓
  False    False    |  True                         True                          ✓
All 4 combinations match: True
EXIT=0
```
✅ 四值真值表完全等价。符合验收 3 允许的「或等价形式」。

---

**三、`or` 关键字问题证真**

临时把生成器改成字面 `or` 形式 `"rdha != rd0 or imms18 == 0"`（同步 EXPR_TO_RULE 映射）：
```
$ python3 tools/spec/generate_opcodes.py 2>&1
生成完成：227 条（…有 rule_refs 135）
EXIT=0
$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml 2>&1
ERROR: ret_riii_ra: legality 'rdha != rd0 or imms18 == 0' 引用了不存在的字段/标识符 'or'（该记录字段: ['imms18', 'rdha']）
验证失败: 1 个错误
EXIT=1
```
✅ `validate-encoding` 确实 FAIL。`ALLOWED_NON_FIELD` 白名单不含 `or`，`or` 被判为未知标识符。engineer 的决策依据**成立**。

还原后：
```
$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml 2>&1
validate_encoding: 227 条记录 OK
EXIT=0
```
✅ 还原回绿。

---

**四、反例门控（自注入 + 还原）**

**反例 A（drift）**：临时把 `ret_riii_ra` 的 legality 还原为 `[]`：
```
$ python3 tools/spec/generate_opcodes.py 2>&1
生成完成：227 条（…有 rule_refs 134）    # 较正确态 -1
EXIT=0
$ python3 tools/spec/check_legality_drift.py 2>&1
FAIL: 控制流 (SimRISC-06-控制流.md): LEGALITY content drift (first diff at line 4, expected 7 lines, got 8 lines)
1 violation(s) found, 11 OK
EXIT=1
```
✅ 确实 FAIL。还原 + 重生成后：
```
$ make check-legality-drift 2>&1
check-legality-drift: 12 chapters OK
EXIT=0
```
✅ 回绿。

**反例 B（rule-refs）**：临时把规则 id 改名 `dst_rd0_nonzero`→`dst_rd0_nonzero_DISABLED`：
```
$ python3 tools/spec/check_rule_refs.py 2>&1
FAIL: 孤儿豁免清单自检失败
  预期: ['excp_ialign', 'excp_rasof', 'excp_rasuf', 'excp_undi']
  实际: ['dst_rd0_nonzero_DISABLED', 'excp_ialign', 'excp_rasof', 'excp_rasuf', 'excp_undi']
  实际有但预期无（新孤儿规则）: ['dst_rd0_nonzero_DISABLED']
EXIT=1
```
✅ 确实 FAIL。还原后：
```
$ python3 tools/spec/check_rule_refs.py 2>&1
check-rule-refs: PASS (规则 16 条: active 被引用 9, active 豁免 4, deferred 3; 指令引用 198 处)
EXIT=0
```
✅ 回绿。

---

**五、范围/越界 + 支撑改动核验**

`gen_legality_list.py` 的 `SEMANTIC_MAP`/`RULE_SUMMARY` 改动必要性验证：

临时去掉 `dst_rd0_nonzero` 的 `SEMANTIC_MAP` 映射后重跑：
```
$ python3 tools/spec/gen_legality_list.py --apply 2>&1
gen-legality: Injected into /mnt/tao/DADAO-v5/spec/SimRISC-06-控制流.md
EXIT=0
$ sed -n '/LEGALITY_START/,/LEGALITY_END/p' spec/SimRISC-06-控制流.md
（LEGALITY 区不含 dst_rd0_nonzero，只有 excp_*）
```
✅ 确认：去掉映射后 `dst_rd0_nonzero` 被**静默丢弃**。支撑改动**必要且最小**（仅新增 2 条映射 + docstring 计数更新）。

改动范围：仅 `SEMANTIC_MAP` +1 行、`RULE_SUMMARY` +1 行、docstring 计数 15→16/134→135。未改渲染逻辑。无未披露越界。

git diff 确认 7 个改动文件均在任务书范围内（`gen_legality_list.py` 属完成区披露的支撑改动）。

---

**六、门控全量**

```
$ make check 2>&1
（省略中间输出）
validate_encoding: 227 条记录 OK
check-rule-refs: PASS (规则 16 条: active 被引用 9, active 豁免 4, deferred 3; 指令引用 198 处)
check-qemu-semantics: PASS
check-cfx-aliases: PASS (byte-identical)
check-dirs: PASS
check-no-residue: PASS
25/25 lit tests PASS
EXIT=0
```
✅ `make check` 全量通过，含 `check-no-residue`。

git 状态：仅 7 个任务相关文件为 M 状态，无 `tmp`/`_tmp`/`_gate`/`.orig`/`.rej` 残留。✅

---

**七、完成区一致性逐条核对**

| 完成区声明 | reviewer 验证 | 判定 |
|---|---|---|
| 8/8 验收项通过 | 8/8 逐条重跑确认 | ✅一致 |
| 反例门控 2 组均真实 FAIL 后还原回绿 | A/B 均重跑确认 FAIL+还原回绿 | ✅一致 |
| 两生成器幂等 | `generate_opcodes.py` 重跑 sha256 一致，`gen_legality_list.py --apply` 全 unchanged | ✅一致 |
| 修改文件 7 个 | git diff 确认 7 个文件 | ✅一致 |
| `gen_legality_list.py` 属支撑性必要改动 | 去映射后静默丢弃已验证 | ✅一致 |
| rule_refs 134→135 | 重生成确认 135 | ✅一致 |
| 规则总数 16 | 重跑确认 16 | ✅一致 |
| opcodes sha256 `be82d5ed...` | 重生成 sha256 一致 | ✅一致 |
| 规则 description 含「仅 ret 适用」 | 重跑确认 | ✅一致 |

未发现不实或夸大。

---

**判决：Accepted**

- 8 条验收标准全部通过（reviewer 独立重跑）
- 等价性四值真值表完全匹配
- `or` 关键字问题证真（`validate-encoding` 确实 FAIL），engineer 的 De Morgan 等价决策有据
- 反例门控 2 组均能真实 FAIL，还原后回绿
- `gen_legality_list.py` 支撑改动必要且最小，无越界
- `make check` 全量 EXIT=0，`check-no-residue` PASS
- 完成区与真实输出逐条一致，未发现不实