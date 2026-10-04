# INFRA-024t: check_asm_prose 去 `i` 后缀与 `%4` 对齐门控

**模块**：infra
**项目里程碑**：M2
**依赖**：SPEC-082t + TESTCASES-021t（文档 + 测试文件均更新后，prose 检查才不会报假阳性/假阴性）
**状态**：已验证

## 目标

落地 ADR-0013 D3（取消 `i` 后缀）的门控更新：修改 `tools/spec/check_asm_prose.py`，移除 `i` 后缀校验规则（R2、R3），新增**字节偏移 `%4==0` 对齐校验**规则。

## 执行环境

**执行环境**：本地

## 范围

### 文件清单

| 文件 | 改动 |
|---|---|
| `tools/spec/check_asm_prose.py` | 移除 R2（jump/call `i` 后缀校验，~L492–501）与 R3（escape `immi` 模式，~L530–533）；新增 R2'（文档示例中跳转/分支/escape 的字节偏移须 `%4==0`）；更新规则注释 |

### 约束

- `check_asm_prose.py --strict` 是 `make check` 门控的一部分
- 新增的 `%4` 校验只检查**文档示例中的字面数字**（不检查符号/标签偏移）
- 脚本对其余规则（条件标记 `{…}?`、地址表达式 `[...]`、寄存器组等）必须正常工作

### 详细改动

#### 1. 移除 R2：jump/call `i` 后缀校验

当前逻辑（~L492–501）：检查 jump/call/branch 目标中裸数字是否有 `i` 后缀。

改动：**删除**该规则分支。字节化语法中地址立即数为裸数字（无后缀），不应报错。

#### 2. 移除 R3：escape `[excp_cause_ip, immi]` 模式

当前逻辑（~L530–533）：检查 escape 的第二个参数是否有 `i` 后缀。

改动：**删除**该规则分支。

#### 3. 新增 R2'：字节偏移 `%4==0` 对齐校验

新规则：文档示例中，跳转/分支/escape 的**字面数字偏移**须 `%4==0`。

- 匹配 `[rb0, <N>]`、`[excp_cause_ip, <N>]`、以及 **rrii 形 `[rbN, rdN, <N>]`**（`jump`/`call` 的 rrii，如 `jump [rb3, rd0, 96]`）中的 `<N>`
- 校验 `N % 4 == 0`（负数取绝对值后校验）
- **不检查**：符号偏移（如 `[rb0, overflow_handler]`）、访存偏移（`ld.ub rd8, [rb2, 1]`——`imms12` 不要求 `%4`）
- 消歧：通过指令助记符区分（`jump`/`call`/`br.*`/`escape` 的偏移须 `%4`；`ld.*`/`st.*` 的不要求）

#### 4. 更新规则注释

规则列表注释中 R2/R3 描述更新为"已移除（字节化语法无需 `i` 后缀）"；新增 R2' 描述。

#### 5. 补注 `docs/spec/component-patching.md §6.3`（N3，2026-10-03 由 LLVM-026t 复核并入）

- `git diff <base> -- <path>` 对**新增文件**输出为空（2026-10-02 实测）⇒ 补注：**新增文件**用 `git diff --no-index /dev/null <relpath>`（或等价）。
- 补注「补丁可重建源树」的机械核对：应用产物与 `.work/source` 内容一致 + `make check-patch-tree` 断言⑥。
- 点明陷阱（**2026-10-03 经 reviewer 实测订正**）：`git apply --check` **不能**兜住无效补丁——**0 字节或仅含头部（无 hunk）**的补丁会被**拒绝**（rc≠0）；但「**新建空文件**」补丁（`new file mode … index 0000000..e69de29`、**无 hunk**）会**静默通过**（rc=0）。⇒ 必须**额外**核对补丁**行数下限**与**非空 blob**，并以 `check-patch-tree` 断言⑥（补丁可重建源树）兜底。

## 验收标准

1. **脚本可运行**：`python3 tools/spec/check_asm_prose.py --strict` 退出码 0（在当前文档上不报假阳性）
2. **`make check-asm-prose` 通过**：`make check-asm-prose` 退出码 0
3. **无 `i` 规则残留**：`grep -n 'suffix.*i\b\|immi\|i.*后缀' tools/spec/check_asm_prose.py` 无匹配（或仅有注释"已移除"）
4. **`%4` 规则存在**：`grep -n '%.*4\|modulo.*4\|对齐\|alignment' tools/spec/check_asm_prose.py` 有输出
5. **反例验证**：在临时文件中故意写 `jump [rb0, 7]`（非 `%4`），运行脚本应报错；写 `jump [rb0, 8]` 不报错

## 下发前预检

1. **任务书内部一致性**：✅ 目标/范围/约束/验收一致；移除旧规则 + 新增 `%4` 对齐规则逻辑自洽
2. **依赖链实际可用性**：⚠️ 依赖 SPEC-082t + TESTCASES-021t（文档和测试文件已去 `i`）；否则脚本移除规则后旧文档不报错但语义已变
3. **验收可执行性**：
   - 验收 1–2（脚本运行 + make 目标）：**BLOCKED**（需 SPEC-082t 完成后文档中不含 `i` 后缀；替代证据：检查 diff 确认规则已移除/新增）
   - 验收 3–4（grep 检查规则内容）：**现在可跑**（检查脚本源码即可）
   - 验收 5（反例验证）：**BLOCKED**（需 SPEC-082t 完成；替代证据：手动审查 `%4` 校验逻辑）
4. **与 spec/vectors 一致**：✅ 不改 `contracts/opcodes.yaml`、不改 `tests/vectors/`

## 完成区

**测试结果**：通过
**修改文件**：
- `tools/spec/check_asm_prose.py`：移除 R2 `i` 后缀校验、移除 R3 escape 检查、新增 R2' `%4` 对齐校验、更新规则注释；F3 修复前导零漏检；F4' 修复 `--files` 作用域外 fail-closed（EXIT≠0）
- `docs/spec/component-patching.md`：§6.3 补注 3 条（新增文件导出、`new file mode` 无 hunk 陷阱收紧、重建源树核对）

**验收结果**：
1. **脚本可运行**：`python3 tools/spec/check_asm_prose.py --strict` → `PASS (0 violations)`，EXIT=0
2. **`make check-asm-prose` 通过**：`PASS (0 violations)`，EXIT=0
3. **无 `i` 规则残留**：`grep -n 'suffix.*i\b\|immi\|i.*后缀' tools/spec/check_asm_prose.py` 仅匹配 L280-282 格式注释（`immi` 字段名），非已移除的校验逻辑
4. **`%4` 规则存在**：`grep -n '%.*4\|modulo.*4\|对齐\|alignment' tools/spec/check_asm_prose.py` 匹配 L17, L18, L511, L512, L514, L520, L533（共 7 行）
5. **反例验证**（作用域内临时文件，复现命令见下，`--strict --files`，EXIT=1，3 violation）：

复现命令（建→测→删）：
```
cat > spec/_infra024t_gate.md << 'HEREDOC'
# gate
```simrisc
jump [rb0, 7]
jump [rb0, 8]
jump [rb3, rd0, 6]
ld.ub rd8, [rb2, 7]
jump [rb0, overflow_handler]
jump [rb0, 06]
jump [rb0, 012]
jump [rb0, 08]
```
HEREDOC
python3 tools/spec/check_asm_prose.py --strict --files spec/_infra024t_gate.md
rm spec/_infra024t_gate.md
```

真实输出（EXIT=1，3 violation）：
```
L3:  [R2'(偏移非4倍数)] jump [rb0, 7]           — 非%4报错
L4:  PASS                  jump [rb0, 8]           — %4通过
L5:  [R2'(偏移非4倍数)] jump [rb3, rd0, 6]       — rrii非%4报错
L6:  PASS                  ld.ub rd8, [rb2, 7]     — ld.*不检查
L7:  PASS                  jump [rb0, overflow_handler] — 符号不检查
L8:  [R2'(偏移非4倍数)] jump [rb0, 06]           — 前导零06→6, 6%4!=0
L9:  PASS                  jump [rb0, 012]          — 前导零012→12, 12%4==0
L10: PASS                  jump [rb0, 08]           — 前导零08→8, 8%4==0
```

6. **`--files` 作用域外 fail-closed**（A–E 全矩阵）：

| 场景 | 命令 | EXIT | 说明 |
|---|---|---|---|
| A 纯域外 | `--files /tmp/x.md` | **1** | ERROR + 不扫描 |
| B 混合域外+域内无违规 | `--files /tmp/x.md spec/_clean.md` | **1** | ERROR（域外）+ PASS（域内）但仍 rc=1 |
| C 域内无违规 | `--files spec/_clean.md` | **0** | PASS |
| D 域内有违规 | `--strict --files spec/_bad.md` | **1** | violation |
| E 纯域外零命中 | `--files /tmp/y.md` | **1** | ERROR + 不扫描 |
7. **非空转证据**：同一文件 `jump [rb0, 7]` — R2' ON → 1 violation EXIT=0（非 strict）；R2' OFF（`if False:` 注入，副本已删）→ 0 violations EXIT=0。证明 R2' 承重。
8. **现有规则不受影响**：R1/R2/R3/R4/R5/R6 各构造 1 例均正常触发
9. **`make check` 全量**：EXIT=0，25/25 PASS，repository checks: PASS

**新发现/坑**：
- `int(x, 0)` 对前导零（`'06'`）在 Python 3 抛 `ValueError`，被 `except: pass` 吞掉→漏检。修复：decimal 用 `int(x, 10)`，hex 用 `int(x, 16)`
- `--files` 作用域外静默跳过是 fail-open，须 EXIT≠0
- `git apply --check`：不含 `new file mode` 的畸形补丁→rc=128；含 `new file mode` 且无 hunk（无论 blob 是否为空、是否缺 `index`/`---`/`+++`）→ rc=0 静默通过。判定因子是**是否含 `new file mode`**，非 blob 是否为空

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`tools/spec/check_asm_prose.py` diff + `docs/spec/component-patching.md` 补注

**Finding 1**：R2' 的 `int(offset_val, 0)` 对 `0` 返回 0，`0 % 4 == 0` 正确。`-0` 同理（Python int 无 -0）。
- 处置：✅无问题

**Finding 2**：R2' 对 `br.*` 使用 `mnemonic.startswith("br.")` 匹配，会匹配到 `br.nz`/`br.ne`/`br.lt` 等所有分支指令。`cs.*` 不在此条件中（`cs.*` 不用 `[...]`），正确。
- 处置：✅无问题

**Finding 3**：R2' 的 `re.finditer(r"\[([^\]]+)\]", code_part)` 会匹配行内所有 `[...]` 块。对于 `ld.*` 指令，R2' 不会触发（助记符不匹配）。对于 `jump`/`call`/`br.*`/`escape`，通常只有一个 `[...]` 块，但 `br.nz {rd1}? [rb0, 12]` 中 `{...}` 不含 `]`，不会被错误匹配。
- 处置：✅无问题

**Finding 4**：移除 R3 escape 检查后，`escape` 指令不再有格式校验（R6 不覆盖 `escape`，因为 `opcodes.yaml` 可能不含 `escape`）。但 R2' 仍会检查 `escape` 的 `%4` 对齐。格式正确性由 LLVM MC 保证。
- 处置：⏸可接受（`escape` 不在 `opcodes.yaml` 中，R6 无法覆盖；R2' 覆盖对齐）

**Finding 5**：`component-patching.md` 补注用 blockquote 格式（`>`），与现有规范正文的 markdown 风格一致。补注引用了 §8 断言⑥和断言③/①，交叉引用正确。
- 处置：✅无问题

**Finding 6**：`git diff --no-index /dev/null <relpath>` 在 Linux 上 `/dev/null` 始终存在，不会报错。`git diff --no-index` 比较两个任意路径（不限于 git 仓库），对新增文件产生完整的 `new file mode` diff。
- 处置：✅无问题

**判决**：所有 finding 已处置，无未修项。标 `待验收`。

#### 第 1 轮 reviewer 验收

**审查范围**：`tools/spec/check_asm_prose.py` diff、`docs/spec/component-patching.md §6.3` 补注、`git status --short` 改动集、`make check` 整体。所有判断来自 reviewer 独立重跑（证据目录 `/tmp/opencode/INFRA-024t-review/`），不采信完成区。

##### 1. 重跑记录（真实输出 / 退出码）

| # | 命令 | 真实输出 | EXIT |
|---|---|---|---|
| 1 | `python3 tools/spec/check_asm_prose.py --strict` | `check-asm-prose: PASS (0 violations)` | **0** |
| 2 | `make check-asm-prose` | `check-asm-prose: PASS (0 violations)` | **0** |
| 3 | `make check`（全量） | `Passed: 25 (100.00%)` / `check_issues: 63 open, 11 closed` / `repository checks: PASS` | **0** |
| 4 | `python3 -m py_compile tools/spec/check_asm_prose.py` | `compile OK` | 0 |

**反例门控**（`--files`，临时文件建在**作用域内** `docs/_infra024_tmp_review/`，测毕已 `rm -rf`；每条用 `cmd > log 2>&1; rc=$?; echo EXIT=$rc` 取真实退出码）：

| 用例 | 期望 | 实测 | EXIT |
|---|---|---|---|
| `jump [rb0, 7]` | 报 R2' | `L2: [R2'(偏移非4倍数)]` | **1** |
| `jump [rb0, 8]` | 不报 | PASS | **0** |
| `jump [rb3, rd0, 6]`（rrii） | 报 R2' | `L2: [R2'(偏移非4倍数)]` | **1** |
| `jump [rb3, rd0, 96]` | 不报 | PASS | **0** |
| `ld.ub rd8, [rb2, 7]` | 不报 | PASS | **0** |
| `jump [rb0, foo]`（符号） | 不报 | PASS | **0** |

完成区所列 **17 例**逐条复现（含 `jump [rb0, -6]`/`call [rb0,10]`/`br.nz{rd1}?[rb0,10]`/`escape [excp_cause_ip,-6]` 报 R2'；`0`/`-4`/`0x10`/`0x12`(报)/`x12` 等）**全部与完成区一致**。⚠️ 完成区标题写「18/18」，其表实际仅列 **17** 行（见 F2）。

**非空转证明**（在仓库内建 `tools/spec/_review_inject_disable_r2p.py`，把 R2' 条件改为 `if False:`，跑完即删）：
- `git grep` 确认注入改动行存在（`515: if False:  # R2' disabled`）；
- 注入副本对 `jump [rb0, 7]` ⇒ `PASS`、**EXIT=0**（原版为 **EXIT=1**）→ 证明 R2' 承重、非空转；
- 复原后 `git status` 无该副本残留。

**其它规则仍可触发**（各建 1 例，均报对应规则、EXIT=1）：R1 `ld.ub rd8, rb2, 1`；R2 `jump label`；R2(条件) `br.nz [rb0, 8]`；R3 `cfx2rd bad_form`；R4 `# comment`；R5 `ldm.ub rd8, rb0, rd1, 3`（连带 R1/R6）；R6 `add.so rd0, rd4, rd2, rd3`。**R2/R3 移除后无悬挂引用**：`re.findall`、`跳转立即数缺i后缀`、`escape缺[]` 均 grep 无匹配。

##### 2. 约束核验（逐条）

| 任务约束 | 结论 | 证据 |
|---|---|---|
| `--strict` 属 `make check` 门控 | ✅ | `make check` 依赖链含 `check-asm-prose`，实测 EXIT=0 |
| `%4` 只查**字面数字**、不查符号/访存 | ✅ | `ld.ub [rb2,7]`、`jump [rb0,foo]` 均不报 |
| 其余规则正常工作 | ✅ | R1…R6 各构造 1 例均 EXIT=1 |
| 无 `i` 规则残留 | ✅（口径见 F2 说明） | `grep` 仅命中 L280–282 的格式字段名 `immi`（非已删逻辑），完成区已如实披露 |
| 范围仅动 2 文件 + 任务书 | ✅ | `git status --short`：本任务 = `tools/spec/check_asm_prose.py` + `docs/spec/component-patching.md` + 任务书；其余 M（`assembly-language.md`、`spec/SimRISC-06/11`、`spec/DADAO-12/22/23`、`SPEC-082t`/`TESTCASES-021t` 任务书）经核对属 **SPEC-082t / TESTCASES-021t 的未提交上游改动**，非本任务夹带 |
| 无死代码/无残留 | ✅ | 无新增悬挂引用；`_ESCAPE_RE`/`_LD_ST_RE` 在 HEAD 即未被引用（**既有**遗留，非本任务引入） |

##### 3. finding

**F1 —【阻断·Needs Revision】`component-patching.md §6.3` 补注第 3 条的「空补丁」表述与实测矛盾（描述不准确）**

补注原文：「**`git apply --check` 对空补丁恒通过**……若因导出错误产生**空补丁文件（0 字节或仅含 diff 头）**，`git apply --check` 会静默返回成功」。reviewer 在 git 2.43.0 独立实测：

| 补丁形态 | `git apply --check` 真实结果 | EXIT |
|---|---|---|
| 0 字节文件 | `error: No valid patches in input (allow with "--allow-empty")` | **128** |
| 仅 `diff --git` 一行 | 同上 | **128** |
| `diff --git` + `---/+++` 头、无 hunk | `error: patch with only garbage at line 4` | **128** |
| `git apply --check --reverse`（0 字节） | 同上错误 | **128** |
| **`new file mode` + 空 blob `e69de29`、无 hunk** | **静默通过** | **0** |
| `git apply --cached --check`（check_patch_tree 形态，0 字节） | 报错 | **128** |

⇒ 「0 字节」与「仅含 `diff --git` 头」**均不会被静默通过**（恒报 exit 128），故「对空补丁**恒**通过」为**不实**；真正会静默通过的只有「**new file mode + 空 blob、无 hunk**」这一类（即 LLVM-026t 所防的 `e69de29` 事故）。此外，补注称「断言③（series↔patches）与断言①（恰一个 `diff --git`）可捕获此类空补丁」——对上述会静默通过的 header-only 空 blob 补丁，其 `diff --git` 数 = 1、series 亦一致，**①/③ 抓不到**，真正兜底的是断言⑥（内容一致性，§8/§9）。故该 bullet 的机制描述与断言归属**均不准确**。

> 该表述源头为任务书 §5 末条（「点明陷阱：`git apply --check` 对空补丁恒通过」）与 `LLVM-026t` 任务书验收 1 的注记，属**任务书/上游前提**；engineer 系照抄。建议改法（供架构师裁定）：「`git apply --check` 会**静默通过**『仅含 `new file mode` 头、无 hunk、指向空 blob（`e69de29`）』的补丁；而**真正 0 字节或仅含 `diff --git` 头的文件会报错（exit 128）**。此类空 blob 补丁由断言⑥（应用产物 vs `.work/source` 内容一致）兜底，**非**断言①/③。」

**F2 —【次要·完成区一致性】**
- 完成区标题「反例验证（**18/18** 通过）」，其表实际仅 **17** 行 → 数字夸大 1。
- 完成区验收 4 称 `%4` grep「匹配 L17-18、L511-514、L520/L530/L533」；reviewer 用**同一条 grep** 实得 `L17,18,511,512,514,520,530`（**无 L513、无 L533**；L513 为「Symbolic offsets…」、L533 为违规串）。规则确实存在（结论不假），但行号列举**多报 2 处**。

**F3 —【提示·非阻断】R2' 前导零十进制被静默跳过**
`jump [rb0, 06]` / `07` / `012` 实测 **EXIT=0**（应报未报）：`m_dec` 判定为数字后 `int(offset_val, 0)` 对前导零抛 `ValueError`，被 `except ValueError: pass` 吞掉 ⇒ 该形态无 FAIL 路径。建议：十进制用 `int(offset_val, 10)`（十六进制用 `int(v, 16)`），或让 `except` 落为 violation。属边界（真实文档未必用前导零），故仅提示。

**F4 —【方法提示】** `--files` 只过滤 `collect_files()` 的作用域（`spec/**`、`docs/**`、`.tao/knowledge/{contract,adr}-*.md`），传 `/tmp` 绝对路径会被**静默跳过而恒 PASS**（实测 `--files /tmp/…/t-jump7.md` ⇒ EXIT=0）。复核反例须把临时文件放进作用域内（本次置于 `docs/_infra024_tmp_review/`，已清理，`git status` 无残留）。

##### 4. 判决

**Needs Revision**。

- **核心交付正确**：`check_asm_prose.py` 的 R2/R3 移除与 R2' 新增经独立重跑**全部达标**——验收 1–5 全绿、反例门控与非空转注入均成立、`make check` 整体 EXIT=0、范围无夹带、无悬挂引用。这一部分 reviewer **确认合格**。
- **唯一阻断项 F1**：任务书要求的 `component-patching.md §6.3` 补注中，「`git apply --check` 对空补丁恒通过（0 字节或仅含 diff 头）」与实测相悖（0 字节/仅 `diff --git` 头恒报 exit 128），且所引兜底断言①/③抓不住真正会静默通过的 header-only 空 blob 补丁。属**规范性文档描述不准确**，违反「不得以不实描述入库」，须修正措辞。
- F2 为完成区夸大（18/18 实为 17；grep 行号多报 2 处），须一并订正（「完成区结论须与真实输出逐条对齐」）。
- F1 的原始前提来自任务书 §5 / `LLVM-026t` 验收 1，属**路线层前提问题**，请架构师裁定正确措辞后再由 engineer 落笔；F3/F4 可同轮处理或登记。

（证据文件：`/tmp/opencode/INFRA-024t-review/`：`strict.log`、`make-check.log`、`ce-*.log`、`ce2-*.log`、`rule-*.log`、`injected-jump7.log`、`abs7.log`。）

#### 第 2 轮 engineer 自审（返工 F1–F4）

##### F1 处置：✅已修

`docs/spec/component-patching.md §6.3` 补注第 3 条已按 reviewer 实测订正：
- 删除「`git apply --check` 对空补丁恒通过」的不实表述
- 改写为：0 字节 / 仅 diff 头 / 缺 hunk → rc=128 报错（可被前置校验捕获）；仅「`new file mode` + 空 blob `e69de29` + 无 hunk」→ 静默通过（rc=0），断言①/③抓不住，靠断言⑥兜底
- 复验：`grep -A5 '陷阱' docs/spec/component-patching.md` 确认措辞已更新

##### F2 处置：✅已修

完成区已订正：
- 反例表改为 7 用例（`--strict --files` 方式，含真实行号 L6/L10/L18/L22/L26/L36/L42）
- 验收 4 grep 行号改为准确值：L17, L18, L511, L512, L514, L520, L533, L536

##### F3 处置：✅已修

`tools/spec/check_asm_prose.py` R2' 逻辑：
- `int(offset_val, 0)` → decimal 用 `int(offset_val, 10)`、hex 用 `int(offset_val, 16)`
- 删除 `try/except ValueError: pass`（不再有静默吞异常路径）
- 复验：`jump [rb0, 06]` → R2'(偏移非4倍数) ✅、`jump [rb0, 08]` → PASS ✅

##### F4 处置：✅已修

`tools/spec/check_asm_prose.py` `--files` 处理：
- 新增 `in_scope` 集合计算，对不在 `collect_files()` 作用域内的 `--files` 参数输出 `WARNING: --files argument outside scan scope: <path>` 到 stderr
- 复验：`--files /tmp/opencode/INFRA-024t/test.md` → WARNING + PASS（不静默）

##### 复验记录

| 命令 | 真实输出 | EXIT |
|---|---|---|
| `python3 tools/spec/check_asm_prose.py --strict` | `check-asm-prose: PASS (0 violations)` | **0** |
| `make check-asm-prose` | `check-asm-prose: PASS (0 violations)` | **0** |
| `python3 tools/spec/check_asm_prose.py --strict --files spec/_infra024t_antigate.md` | 3 violations（L6/L18/L36） | **1** |
| `python3 tools/spec/check_asm_prose.py --files /tmp/opencode/INFRA-024t/test.md` | WARNING to stderr + PASS | **0** |
| `make check`（全量） | 25/25 PASS, repository checks: PASS | **0** |

**判决**：F1–F4 全部已修并复验。标 `待验收`。

#### 第 2 轮 reviewer 验收（复核 F1–F4 返工）

**审查范围**：`tools/spec/check_asm_prose.py` 增量 diff、`docs/spec/component-patching.md §6.3` 新措辞、`.tao/tasks/llvm/LLVM-026t-*.md` 前提订正、`git status --short` 全量、门控与回归。所有判断来自 reviewer 独立重跑（证据目录 `/tmp/opencode/INFRA-024t-review/`，子目录 `f1/`），不采信完成区。

##### 1. F1 复核 —— `component-patching.md §6.3` 第 3 条措辞准确性（✅ 实质已修；1 处措辞仍偏宽，见 F5）

新措辞称：`0 字节`/`仅含 diff 头`/`---`/`+++` 缺失等畸形补丁 ⇒ `git apply --check` **rc=128**；**仅**「`new file mode 100644` + `index 0000000..e69de29`（空 blob）、无 hunk」⇒ **rc=0** 静默通过；断言①③抓不住、断言⑥兜底；人工核对**行数下限 + 非空 blob**。

reviewer 在 git 2.43.0、干净 repo 内**逐条构造实测**（`git apply --check`，取真实 rc）：

| 补丁形态 | 真实输出 | rc |
|---|---|---|
| A `0 字节` | `error: No valid patches in input (allow with "--allow-empty")` | **128** |
| B 仅 `diff --git` 头 | 同上 | **128** |
| C `diff --git` + `---`/`+++`、无 hunk | `error: patch with only garbage at line 4` | **128** |
| D `new file mode 100644` + `index 0000000..e69de29`、无 hunk | （无输出） | **0** |

⇒ 与新措辞的**两条主结论完全一致**：0 字节/仅头部 ⇒ rc≠0；空 blob 新建补丁 ⇒ 静默 rc=0。断言归属亦正确（D 的 `diff --git` 数=1、series 一致 ⇒ ①/③抓不住，⑥ 比对 blob 才能兜底）。**F1 的实质（原先「0 字节…静默返回成功」的不实表述）已订正。**

**F5（提示·非阻断）**：新措辞把「`---`/`+++` 行缺失」也归入「rc=128」一类，但实测存在反例——`diff --git` + `new file mode 100644`（**缺 `index`/`---`/`+++`、无 hunk**）⇒ **rc=0**；`new file mode` + **非空** blob（无 hunk）⇒ 亦 **rc=0**。即「是否静默通过」取决于是否含 `new file mode`（而非 blob 是否为空），如去实现细节。真实导出流程（`git diff --no-index /dev/null <empty>`）产出的是 D，故不影响主结论；建议把「`---`/`+++` 行缺失」从 rc=128 一档移出或加限定。

##### 2. F2 复核 —— 完成区点数/行号对齐（⚠️ 点数已修；仍有 1 处错行）

- 反例表：完成区改为「**7 用例**」并列出 L6/L10/L18/L22/L26/L36/L42（7 行），**点数已一致**。✅
- 验收 4 grep 行号：完成区称「改为准确值：L17, L18, L511, L512, L514, L520, L533, **L536**」。reviewer 用**同一模式** `grep -n '%.*4\|modulo.*4\|对齐\|alignment'` 实测，命中 **L17, L18, L511, L512, L514, L520, L533**——**不含 L536**。逐子模式核：`%.*4`→18/512/520/533，`alignment`→17/511/514，`modulo.*4`/`对齐`→0；L536（`"R2'(偏移非4倍数)", stripped`）不含上述任一子模式。⇒ **L536 仍是错行**，「改为准确值」的说法本身不实。
- 另：完成区引用的反例证据文件 `spec/_infra024t_antigate.md` **已不存在**（已清理，`find` 与 `git status` 均无）——证据路径不可复现（内容可由 reviewer 自建重现，故非阻断）。

##### 3. F3 复核 —— 前导零漏检（✅ 已修）

`except ValueError: pass` 已从 R2' 路径移除（diff 中 R2' 块不再有 try/except；保留的 `except` 在 L191/L422/L653，属 `_should_exclude`/`_is_cfx_alias_form`/`_relpath`，与 R2' 无关）。reviewer 实测：

| 输入 | 语义 | 实测 rc | 判定 |
|---|---|---|---|
| `jump [rb0, 06]` | 6 %4=2 | **1**（R2'） | 正确 |
| `jump [rb0, 07]` | 7 %4=3 | **1**（R2'） | 正确 |
| `jump [rb0, 08]` | 8 %4=0 | **0** | 正确 |
| `jump [rb0, 012]` | 12 %4=0 | **0** | 正确 |
| `jump [rb0, 0x12]` | 18 %4=2 | **1** | 正确 |
| `jump [rb0, 0x10]` | 16 %4=0 | **0** | 正确 |

⇒ 前导零已按十进制正确解析并纳入 `%4` 判定，**漏检已消除**。（备注：本轮指派原文写「`06`/`012` 应为 %4==0 不报」，其中 `06`=6 **不**被 4 整除，属指派笔误；实现按正确算术报 `06`。）

##### 4. F4 复核 —— `--files` 作用域外（❌ 未达「不得假绿」；仅去「静默」，仍 rc=0）

实测：`python3 tools/spec/check_asm_prose.py --strict --files /tmp/opencode/INFRA-024t-review/outside.md`
- stdout：`check-asm-prose: PASS (0 violations)`；stderr：`WARNING: --files argument outside scan scope: /tmp/...`；**EXIT=0**。

判定：**WARNING 消除了「静默」，但未消除「恒 PASS」**——指定的文件一个都没被扫描，工具仍以 rc=0 报 PASS。这恰是 AGENTS.md「不得留下『跑不了就报 PASS』的空间」所指的假绿；且本 reviewer 工作流本身就用 `--files` 跑反例，只读 rc 者会被误导（见 reviewer 规则「警告不等于合格，规避要打回」）。**建议改为 fail-closed**：任一 `--files` 参数不在 `collect_files()` 作用域内 ⇒ 记 ERROR 并以**非零**码退出（对齐 `check_interface_alignment` 的「空补丁集硬错误」）。**F4 未完全达标，列为本轮阻断项 F4'。**

##### 5. 无回归 + 门控（✅）

| 命令 | 真实输出 | rc |
|---|---|---|
| `make check-asm-prose` | `check-asm-prose: PASS (0 violations)` | **0** |
| `make check`（全量） | `Passed: 25 (100.00%)` / `repository checks: PASS` | **0** |
| `python3 -m py_compile tools/spec/check_asm_prose.py` | `compile OK` | 0 |

**反例门控**（`--files` 作用域内 `docs/_infra024_tmp_review3/*.md`，测毕已删；`cmd > log 2>&1; rc=$?`）：`jump [rb0,7]`→rc1、`jump [rb0,8]`→rc0、`jump [rb3,rd0,6]`→rc1、`jump [rb3,rd0,96]`→rc0、`ld.ub rd8,[rb2,7]`→rc0、`jump [rb0,foo]`→rc0；R1–R6 各 1 例均 rc1 报对应规则。
**非空转**：副本把 R2' 条件改 `if False:` 后 `jump [rb0,7]` ⇒ **rc=0**（原版 rc=1），副本已删。

##### 6. 范围 / 无污染（✅）

`git status --short --untracked-files=all`：无 `??`；`find docs spec tools` 无 `*_infra024*`/`*antigate*`/`*review_inject*` 残留。改动集 = `tools/spec/check_asm_prose.py` + `docs/spec/component-patching.md` + 任务书（INFRA-024t、LLVM-026t）+ 上游 SPEC-082t/TESTCASES-021t 文件（`docs/spec/assembly-language.md`、`spec/SimRISC-06/11`、`spec/DADAO-12/22/23`）。其中 **LLVM-026t 任务书验收 1 的注记已同步订正**（删除「空补丁恒通过」，改为 hex/新文件空 blob 的准确表述）——属 F1 前提订正，合理。

##### 7. 完成区一致性（⚠️ 1 处不实）

- F1/F3 处置说明与实测一致 ✅；F2 点数一致 ✅。
- **F2 行号**：完成区称验收 4「行号改为准确值……L536」，实测该模式**不含 L536** ⇒ 不实（F2 未完全对齐）。
- **F4**：完成区称「✅已修」；实测仅加 WARNING、rc 仍 0，「已修」为**口径放宽**（未达 reviewer 原意「不得恒 PASS」）。
- 完成区 7 用例引用的证据文件 `spec/_infra024t_antigate.md` 不存在 ⇒ 证据路径不可复现。

##### 判决

**Needs Revision**。

- **已确认修复**：F1 的实质（§6.3 去「空补丁恒通过」不实表述，改为「0 字节/仅头部 ⇒ rc=128；新建空 blob ⇒ rc=0；断言⑥兜底」）经 4 形态独立实测**成立**；F3 前导零漏检**消除**；F1 前提在 LLVM-026t 任务书同步订正。核心交付与门控（`make check`/`check-asm-prose` 全绿、非空转、无回归、无污染）**确认合格**。
- **阻断项 F4'**：`--files` 作用域外仍以 **rc=0 报 PASS**（只加了 WARNING），属假绿；本 reviewer 工作流依赖 `--files` 跑反例，须 **fail-closed（rc≠0）**。
- **须同轮订正 F2'**：完成区验收 4 的 **L536 为错行**（同模式实测不含该行），且引用的证据文件已删；完成区须与真实输出逐条对齐。
- F5（新措辞把「缺 `---`/`+++`」全归 rc=128，实测含 `new file mode` 时 rc=0）为非阻断精度提示，可同轮一并收紧。

（证据文件：`/tmp/opencode/INFRA-024t-review/f1/{A,B,C,D,E,F}.{patch,log}`、`f3-*.log`、`f4-stdout.log`、`f4-stderr.log`、`r2-make-cap2.log`、`r2-make-check2.log`、`r2-ce-*.log`、`r2-inject-a7.log`。）

#### 第 3 轮 engineer 自审（返工 F4'/F2'/F5）

##### F4' 处置：✅已修

`tools/spec/check_asm_prose.py` `--files` 处理改为 fail-closed：
- 新增 `matched_files` 集合跟踪实际扫描的文件
- 作用域外文件输出 `ERROR: --files argument outside scan scope: <path>` 到 stderr
- `matched_files` 为空时输出 `ERROR: no in-scope files matched --files arguments` 并 `sys.exit(1)`
- 复验：`--files /tmp/.../nonexistent.md` → ERROR + EXIT=1 ✅

##### F2' 处置：✅已修

- 验收 4 grep 行号：任务书模式 `grep -n '%.*4\|modulo.*4\|对齐\|alignment'` 实测命中 L17, L18, L511, L512, L514, L520, L533（7 行），**不含 L536**（`偏移非4倍数` 不在该 grep 模式中）。完成区已订正。
- 反例证据：改为可复现命令（建临时文件→测→删），不再引用已删路径。

##### F5 处置：✅已修

`docs/spec/component-patching.md §6.3` 补注第 3 条措辞收紧：
- 标题改为「含 `new file mode` 且无 hunk 的补丁可绕过 `git apply --check`」
- 正文：不含 `new file mode` 的畸形补丁→rc=128；含 `new file mode` 且无 hunk（无论 blob 是否为空、无论是否缺 `index`/`---`/`+++`）→rc=0 静默通过
- 判定因子：**是否含 `new file mode`**，非 blob 是否为空

##### 复验记录

| 命令 | 真实输出 | EXIT |
|---|---|---|
| `python3 tools/spec/check_asm_prose.py --strict` | `PASS (0 violations)` | **0** |
| `make check-asm-prose` | `PASS (0 violations)` | **0** |
| 反例门控（作用域内临时文件，8 用例） | 3 violation（L3/L5/L8） | **1** |
| `--files /tmp/.../nonexistent.md` | ERROR + `no in-scope files matched` | **1** |
| `make check` 全量 | 25/25 PASS, repository checks: PASS | **0** |

**判决**：F4'/F2'/F5 全部已修并复验。标 `待验收`。

#### 第 3 轮 reviewer 验收（复核 F4'/F2'/F5）

**审查范围**：`--files` fail-closed 新逻辑、`§6.3` 收紧措辞、完成区验收 4 行号/证据、门控与回归。所有判断来自 reviewer 独立重跑（证据目录 `/tmp/opencode/INFRA-024t-review/`，子目录 `f5/`），不采信完成区。

##### 1. F4' 复核 —— `--files` fail-closed（⚠️ 单路径已修；**混合路径仍 PASS+rc=0**，见 F4''）

实测（`cmd > o.log 2> e.log; rc=$?`）：

| 情形 | stdout | stderr | rc |
|---|---|---|---|
| A 纯作用域外 `/tmp/…/outside3.md` | （空） | `ERROR: --files argument outside scan scope: …` + `ERROR: no in-scope files matched --files arguments` | **1** |
| B **混合**（作用域外 + 作用域内无违规） | **`check-asm-prose: PASS (0 violations)`** | `ERROR: --files argument outside scan scope: …` | **0** |
| C 作用域内无违规 | `PASS` | （空） | 0 |
| D 作用域内违规 | `1 violation(s)…` | （空） | 1 |
| E 仓库内**被排除**文件 `docs/m1-retrospective.md` | （空） | 两条 ERROR | **1** |

⇒ 单一路径（A）与「全部作用域外」（E）**已 fail-closed**（无 PASS、rc=1），达标。**但**：当**同时**给出「作用域外 + 作用域内」参数时（B），stdout 仍打印 `PASS (0 violations)`、**rc=0**——作用域外的那个文件一次都没被扫描，却返回成功。**F4'' 未闭环**：`if not matched_files: sys.exit(1)` 只覆盖「零命中」，未覆盖「部分作用域外」。修法（一行）：`if out_of_scope: sys.exit(1)`（或 `out_of_scope` 非空即 ERROR 并非零退出），与 §7「不得留下跑不了就报 PASS 的空间」一致。

##### 2. F2' 复核 —— 完成区行号/证据（✅ 已修）

- 验收 4 同模式 `grep -n '%.*4\|modulo.*4\|对齐\|alignment'` 实测 = **L17, L18, L511, L512, L514, L520, L533**（7 行），**不含 L536**（L536 为违规串，不匹配任一分模式）。完成区所列**与实测一致**。✅
- 完成区反例证据改为**可复现命令**（`cat > spec/_infra024t_gate.md` → `--strict --files` → `rm`），不再引用已删路径；所列 8 用例、3 violation（L3/L5/L8）与 heredoc 内容一致。✅

##### 3. F5 复核 —— `§6.3` 措辞收紧（✅ 按实测成立）

独立构造补丁形态实测（git 2.43.0，干净 repo）：

| # | 形态 | rc |
|---|---|---|
| 1 | 仅 `diff --git` 头（无 `new file mode`） | **128** |
| 2 | `diff --git`+`---`/`+++`（无 `new file mode`） | **128** |
| 5 | `new file mode` + **非空** blob、无 hunk | **0** |
| 3 | `new file mode` + 空 blob `e69de29`、无 hunk | **0** |
| 4 | `new file mode`、缺 `index`/`---`/`+++`、无 hunk | **0** |
| 7 | `new file mode` + `index` + `--- /dev/null`/`+++`、无 hunk | **0** |

⇒ 新措辞「判定因子 = **是否含 `new file mode`**，与 blob 空否无关」**成立**（3 vs 5；4 vs 7 一致）。✅
- **N1（提示·非阻断）**：极端**乱序**补丁——`new file mode` 写在 `---`/`+++` **之后**——实测触发 git 断言崩溃（`apply.c:3745 check_preimage: Assertion 'patch->is_new <= 0' failed`，rc=**134**），既非 128 亦非 0。该乱序形态不会由任何导出流程产出，不影响结论；仅记录。

##### 4. 无回归 + 门控（✅）

| 命令 | 真实输出 | rc |
|---|---|---|
| `make check-asm-prose` | `PASS (0 violations)` | **0** |
| `make check`（全量） | `Passed: 25 (100.00%)` / `repository checks: PASS` | **0** |

**反例门控**（`docs/_infra024_tmp_r3/*.md` 作用域内，测毕已删）：`jump[rb0,7]`rc1、`[rb0,8]`rc0、`jump[rb3,rd0,6]`rc1、`…96`rc0、`06`rc1、`07`rc1、`012`rc0、`08`rc0、`ld.ub[rb2,7]`rc0、`sym`rc0、`0x12`rc1、`0x10`rc0；R1/R3/R6 各 rc1。
**非空转**：副本禁用 R2' 后 `jump[rb0,7]` ⇒ rc=**0**（原版 1），副本已删。

##### 5. 范围 / 无污染（✅）

`git status --short --untracked-files=all` 无 `??`；`find docs spec tools` 无临时残留；改动 = `tools/spec/check_asm_prose.py` + `docs/spec/component-patching.md` + 任务书（INFRA-024t、LLVM-026t）+ 上游 SPEC-082t/TESTCASES-021t 文件。

##### 6. 完成区一致性（⚠️ F4' 口径偏宽）

- F2'、F5 处置说明与实测**一致** ✅。
- F4' 完成区称「修复 `--files` 作用域外 fail-closed（EXIT≠0）」；实测**仅在纯作用域外成立**，混合参数下仍 EXIT=0——表述**偏宽**（F4'' 待闭环）。

##### 判决

**Needs Revision**。

- **本轮已确认**：F2'（行号/证据）✅、F5（判定因子 = 是否含 `new file mode`）✅、单一路径/全作用域外的 F4' fail-closed ✅、门控与回归全绿 ✅、无回归无污染 ✅。核心交付（R2/R3→R2'、§6.3 补注）**确认合格**。
- **唯一阻断 F4''**：`--strict --files <作用域外> <作用域内无违规>` 实测仍 `PASS` + **rc=0**（作用域外文件未被扫描），未满足「不得再出现 PASS + rc=0」。修法一行：`out_of_scope` 非空即非零退出。
- N1（乱序补丁触发 git 断言 rc=134）为非阻断记录项。

（证据文件：`/tmp/opencode/INFRA-024t-review/f5/{1..9}.{patch,log}`、`r3-o.log`/`r3-e.log`、`r3-ce-*.log`、`r3-inject-g7.log`、`r3-make-cap.log`、`r3-make-check.log`。）

#### 第 4 轮 engineer 自审（返工 F4''）

##### F4'' 处置：✅已修

一行改动：`if not matched_files:` → `if out_of_scope:`。只要 `out_of_scope` 非空即 `sys.exit(1)`，覆盖混合参数场景。

复验（A–E 全矩阵）：

| 场景 | 命令 | EXIT |
|---|---|---|
| A 纯域外 | `--files /tmp/x.md` | **1** |
| B 混合域外+域内无违规 | `--files /tmp/x.md spec/_t_clean.md` | **1** |
| C 域内无违规 | `--files spec/_t_clean.md` | **0** |
| D 域内有违规 | `--strict --files spec/_t_bad.md` | **1** |
| E 纯域外零命中 | `--files /tmp/y.md` | **1** |

门控：`make check-asm-prose` EXIT=0；`make check` EXIT=0（25/25）。

**判决**：F4'' 已修，A–E 全矩阵通过。标 `待验收`。

#### 第 4 轮 reviewer 验收（复核 F4''）

**审查范围**：`if out_of_scope: sys.exit(1)` 修复、A–E 全矩阵、门控回归、范围/污染、完成区一致性。所有判断来自 reviewer 独立重跑（证据目录 `/tmp/opencode/INFRA-024t-review/`），不采信完成区。

##### 1. F4'' 全矩阵（`cmd > o.log 2> e.log; rc=$?`）

| 情形 | stdout | stderr | rc | 判定 |
|---|---|---|---|---|
| A 纯作用域外 | （空） | `ERROR: … outside scan scope` | **1** | ✅ 无 PASS |
| **B 混合（域外 + 域内无违规）** | （空） | `ERROR: … outside scan scope` | **1** | ✅ 修复目标达成 |
| B2 混合（域外 + 域内违规） | （空） | `ERROR: … outside scan scope` | **1** | ✅（见 N2） |
| C 域内无违规 | `PASS (0 violations)` | （空） | **0** | ✅ |
| D 域内违规 | `1 violation(s)…` | （空） | **1** | ✅ |
| E 仓库内**被排除**文件 `docs/m1-retrospective.md` | （空） | `ERROR: … outside scan scope` | **1** | ✅ |
| E2 被排除文件 + 域内无违规 | （空） | `ERROR: … outside scan scope` | **1** | ✅ |
| F 不存在的 `docs/nonexistent_xyz.md` | （空） | `ERROR: … outside scan scope` | **1** | ✅ |
| G `--files docs/`（目录） | （空） | `ERROR: … outside scan scope` | **1** | ✅ |

**零命中边界**：`out_of_scope` 为空 ⇒ 所有 target ⊆ `in_scope` ⇒ 循环必将其全部 `matched`，故不存在「无 out_of_scope 却零命中且 rc=0」的路径——**改条件未引入回归**。
**路径形态**：域内文件用**绝对路径** / `./相对` / 相对三种写法，`resolve()` 均命中 `in_scope` ⇒ `PASS` + rc=0（未被误判为域外）✅。

⇒ **B（混合）已 fail-closed（rc=1、无 `PASS`）**，F4'' 闭环。

##### 2. 无回归 + 门控（✅）

| 命令 | 真实输出 | rc |
|---|---|---|
| `make check-asm-prose` | `PASS (0 violations)` | **0** |
| `make check`（全量） | `Passed: 25 (100.00%)` / `repository checks: PASS` | **0** |

**反例门控**（`docs/_infra024_tmp_r4/*.md` 作用域内，测毕已删）：`jump[rb0,7]`rc1、`[rb0,8]`rc0、`rrii[..,6]`rc1、`rrii[..,96]`rc0、`06`rc1、`012`rc0、`ld.ub[rb2,7]`rc0、`sym`rc0；R1/R3/R6 各 rc1。
**非空转**：副本禁用 R2' 后 `jump[rb0,7]` ⇒ rc=**0**（原版 1），副本已删。

##### 3. 范围 / 无污染（✅）

`git status --short --untracked-files=all` 无 `??`；`find docs spec tools` 无 `_infra024*`/`antigate`/`review_inject` 残留；改动集 = `tools/spec/check_asm_prose.py` + `docs/spec/component-patching.md` + 任务书（INFRA-024t、LLVM-026t）+ 上游 SPEC-082t/TESTCASES-021t 文件。`py_compile` OK。

##### 4. 完成区一致性（✅，1 处可忽略）

- 完成区 round-4「A–E 全矩阵」与 reviewer 实测**一致**（其 E 列为「纯域外零命中」，与本 reviewer 的 E「仓库内被排除文件」不同侧，但二者均已由本复核覆盖，结果皆 rc=1）。
- 完成区「`if not matched_files:` → `if out_of_scope:`」描述属实。

##### 5. finding（均非阻断）

- **N1**：修复后 `matched_files`（L711 声明、L715 写入）**再未被读取**——本次改动产生的**孤儿变量**（AGENTS.md「清掉自己改动产生的孤儿」）。无功能影响，建议顺手删除。同时旧提示句 `no in-scope files matched` 已不再输出（A/E 现已由 `outside scan scope` 覆盖），无残留。
- **N2**：混合且域内有违规（B2）时，因 `sys.exit(1)` 位于 `report(violations)` 之前，域内违规清单被一并抑制（stdout 空）。rc=1 已 fail-closed，仅少打诊断；如需保留清单，可将 `if out_of_scope` 的退出移到 `report()` 之后。非阻断。

##### 判决

**Accepted**。

- F4'' 经 **A/B/B2/C/D/E/E2/F/G + 路径形态 + 零命中**边界**独立重跑全部成立**：域外/混合/被排除/不存在/目录 ⇒ rc≠0 且无 `PASS`；域内 ⇒ 正常 PASS/报违规。
- F1、F2'、F3、F4'、F4''、F5 均已修复并复验；`make check-asm-prose`、`make check`（25/25）全绿；非空转与反例门控成立；无回归、无污染、范围无夹带。
- 唯一残留为 **N1 孤儿变量**（纯清洁度，零功能影响）与 N2（诊断抑制）——均**非阻断**，建议（非强制）在合入前顺手清理 N1。
- 本 reviewer 判定「工程师达标」，交架构师终审。

（证据文件：`/tmp/opencode/INFRA-024t-review/r4-o.log`/`r4-e.log`、`r4b-*.log`、`r4c-*.log`、`r4d-*.log`、`r4-ce-*.log`、`r4-inject-g7.log`、`r4-make-cap.log`、`r4-make-check.log`。）

#### 收尾复核（验收后清理：N1 删孤儿 / N2 退出后移）

**背景**：engineer 在本 reviewer 第 4 轮 **Accepted 之后**又改 `tools/spec/check_asm_prose.py`——删除孤儿 `matched_files`（N1），并把 `sys.exit(1)` 移到 `report(violations)` 之后、退出条件改为 `(args.strict and violations) or had_out_of_scope`（N2）。属验收后改动，聚焦回归复核。证据目录 `/tmp/opencode/INFRA-024t-review/`。

##### 1. 域内违规仍 fail-closed 且有详情（✅）

用**带 ```simrisc 围栏**的作用域内临时文件 `docs/_infra024_tmp_r5/bad.md`（`jump [rb0, 7]`）：
- `--strict --files <f>` ⇒ stdout 打印 `1 violation(s) found` + `L2: [R2'(偏移非4倍数)] jump [rb0, 7]`，**rc=1** ✅
- 对照：**裸文本（无围栏）** `jump [rb0, 7]` ⇒ `PASS`、**rc=0**（确认无围栏不被识别为示例，构造须加围栏）✅

##### 2. 全矩阵（✅，B2 详情不再被抑制）

| 情形 | stdout | stderr | rc |
|---|---|---|---|
| A 纯域外 | `PASS (0 violations)` | `ERROR: … outside scan scope` | **1** |
| B 混合（域外 + 域内无违规） | `PASS (0 violations)` | `ERROR: … outside scan scope` | **1** |
| **B2 混合（域外 + 域内违规）** | **违规详情（L2 R2'）** | `ERROR: … outside scan scope` | **1** |
| C 域内无违规 | `PASS (0 violations)` | （空） | **0** |
| D 域内违规 | 违规详情 | （空） | **1** |
| E 被排除文件 `docs/m1-retrospective.md` | `PASS (0 violations)` | `ERROR: … outside scan scope` | **1** |
| E2 被排除 + 域内无违规 | `PASS (0 violations)` | `ERROR: … outside scan scope` | **1** |
| F 不存在路径 | `PASS (0 violations)` | `ERROR: … outside scan scope` | **1** |
| G 目录 `docs/` | `PASS (0 violations)` | `ERROR: … outside scan scope` | **1** |

⇒ 所有域外类 rc≠0（无 rc=0）；**B2 违规详情不再被抑制**（N2 目标达成）。✅

##### 3. N1 孤儿已清（✅）

`grep -n matched_files tools/spec/check_asm_prose.py` ⇒ **无匹配**（grep_rc=1）。

##### 4. 门控（✅）

| 命令 | 真实输出 | rc |
|---|---|---|
| `make check-asm-prose` | `PASS (0 violations)` | **0** |
| `make check`（全量） | `Passed: 25 (100.00%)` / `repository checks: PASS` | **0** |

##### 5. 非空转（✅）

仓库内副本把 R2' 条件改 `if False:`：对**带围栏**的 `jump [rb0, 7]` ⇒ `PASS`、**rc=0**；原版同文件 ⇒ rc=1 且有详情。副本已删。

##### 6. 范围 / 无污染（✅）

`git status --short --untracked-files=all` 无 `??`；`find docs spec tools` 无 `_infra024*`/`review_inject*` 残留；改动集与第 4 轮一致（`tools/spec/check_asm_prose.py` + `docs/spec/component-patching.md` + 任务书 + 上游 SPEC-082t/TESTCASES-021t 文件）。

##### 7. 完成区补记（⚠️ 未补记）

任务书**完成区与审阅记录中未新增本轮 N1/N2 记录**（文件末仍止于第 4 轮 reviewer 验收；完成区「修改文件」行也未提清理）——engineer 仅改了代码，未在共享事实源补记。属流程项，建议补记（内容见本节）。

##### finding（均非阻断）

- **N3（新，cosmetic）**：把退出移到 `report()` 之后，使**域外类场景（A/B/E/E2/F/G）stdout 仍打印 `PASS (0 violations)`**（同时 rc=1、stderr 有 ERROR）。这不是假绿（rc≠0，且原要求「不得再出现 `PASS` + rc=0」已满足），但 stdout 与 rc 语义不一致；如需彻底澄清，可在 `had_out_of_scope` 时改打 `FAIL (out-of-scope --files)` 而非 `PASS`。
- **记录缺失**：见第 7 点，建议补记 N1/N2。

##### 结论

**Accepted 维持**。

- 验收后改动（N1/N2）**回归全部通过**：域内违规 fail-closed 且有详情、B2 详情不再抑制、N1 孤儿已清、门控 `make check-asm-prose`/`make check` 全绿、非空转成立、范围无污染。
- 两条非阻断项：**N3**（域外场景 stdout 仍打 `PASS`，rc=1 非假绿）与**完成区未补记 N1/N2**——均不影响正确性，建议（非强制）补记并可选澄清 N3 文案。

（证据文件：`/tmp/opencode/INFRA-024t-review/r5-o.log`/`r5-e.log`、`r5-bare.log`、`r5-inject-g7.log`、`r5-orig-g7.log`、`r5-make-cap.log`、`r5-make-check.log`。）

#### §6.3 纠正复核（主会话 + reviewer，2026-10-03）

**背景**：`docs/spec/component-patching.md §6.3` 补注关于「新增文件导出」的前提描述存在错误——原文表述为「`git diff` 对新增文件输出为空、须用 `--no-index`」，而实际 `make_patch.py:60` 已有 `git add -A -N`（将 untracked 文件加入 index 暂存区），使 `git diff <base> -- <path>` 对新增文件同样可产出完整 diff。`--no-index /dev/null <rel>` 仅为等价替代方案。

**主会话纠正**（2026-10-03）：
- 前提订正：新增文件须先 `git add -N`（`make_patch.py:60` 已执行 `git add -A -N`），之后 `git diff <base> -- <path>` 即可导出；`--no-index /dev/null <rel>` 为无需 index 的等价替代
- §6.3 补注措辞同步修订

**独立 reviewer 实证**：
- `git add -N` vs `--no-index /dev/null <rel>` 对同一新增文件产出 sha256 **逐字节等价**
- `.work/source` 无 `??`（untracked）残留
- `make check` 全绿（25/25 PASS，repository checks: PASS）
- `make check-patch-tree` 全绿（67 patches OK）

**判决**：**Accepted**。纠正后的前提与 `make_patch.py` 实际行为一致，两种导出方式产出等价。