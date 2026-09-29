# SPEC-052t: cfx 字段重命名（cfxha/cghb/rchc/rdhd）与重生成

**模块**：spec（含跨模块 `tools/llvm/gen_asm_list.py`，因须同步才能保持 `make check` 绿灯）
**项目里程碑**：M1→M2
**依赖**：`ADR-0013 D8`（Accepted，本任务落地 D8.1–D8.5 的**机制**部分）
**状态**：已验证

## 背景

`ADR-0013 D8` 裁定：cfx 汇编记法改为 `cfxHA` / `cgHB, rcHC, rdHD`，并重命名字段。现状不一致：

- `contracts/opcodes.yaml`：`cfx2rd`/`cfx2rc` 字段为 `cfxcode`、`hb`、`hc`、`hd`；`cfxld`/`cfxst`/`trap`/`escape` 字段为 `cfxcode`
- `tools/llvm/gen_asm_list.py::operands()` **已按 `cghb`/`rchc` 判断**（当前 yaml 的 `hb`/`hc` 落到 `else` 分支 → 渲染为 `hb, hc, hd`）
- 故当前生成表为 `cfx2rd cfxcode, hb, hc, hd`（与 D8 不符）

## 修改内容

### 1. `tools/spec/generate_opcodes.py`

- `f_crrr()`：字段名 `cfxcode→cfxha`、`hb→cghb`、`hc→rchc`、`hd→rdhd`（**role/bank/bits 不变**：`cfxcode`/`cfx_cg`/`cfx_rc`；bits `[23:18]`/`[17:12]`/`[11:6]`/`[5:0]`）
- `f_crii()`/`f_ciii()`：`cfxcode→cfxha`
- 注释/文档字符串同步

### 2. 重生成 `contracts/opcodes.yaml`（用 `generate_opcodes.py`）

### 3. `tools/llvm/gen_asm_list.py`

- `operands()`：`name == "cfxcode"` → `name == "cfxha"`（kind 仍为 `"cfxcode"`；`cghb`/`rchc` 分支已存在，无需改）
- `field_name()`：`FIELD_RE` 扩展为 `^(rd|rb|ra|rf|cg|rc|cfx)([a-z]{2})$` → `cfxha→cfxHA`、`cghb→cgHB`、`rchc→rcHC`、`rdhd→rdHD`
- `new_form()` 中硬编码的 `cfxcode` → `cfxHA`（`trap`、`escape` 两处）
- 顶部注释/`field_name` 文档字符串中的 `cfxcode` 同步
- **注意**：`new_template()`（L378 起）为**死代码**（docstring 已标 deprecated），本任务**不改**

### 4. `contracts/legality_rules.yaml`（L295）

描述性文本中的 `cfxcode` → `cfxha`（若判定为字段引用；若是纯语义描述可保留并说明）

### 5. 重生成产物

- `docs/assembly-list.md`（`python3 tools/llvm/gen_asm_list.py -o docs/assembly-list.md`）
- 12 个 `spec/SimRISC-*.md` 内嵌速查表（`--embed-spec`）
- 若 `docs/self-consistency.md` 为生成物则一并重生成（请核实其生成方式；若非生成物则按字段引用同步）

### 6. 期望的 cfx 汇编形式（**逐条核对**）

```
cfxld   cfxHA, [rbHB, immu12]
cfxst   cfxHA, [rbHB, immu12]
cfx2rd  cfxHA, cgHB, rcHC, rdHD
cfx2rc  cfxHA, cgHB, rcHC, rdHD
escape  cfxHA, [excp_cause_ip, imms18i]
trap    cfxHA, immu18
```

## 约束

- **role 名不变**（`cfxcode`/`cfx_cg`/`cfx_rc`）；只改**字段名**
- 不影响 `validate_instrinfo.py` 的槽位名（`ha/hb/hc/hd` 为格式槽位，与本重命名无关）
- 不改 `docs/m1-retrospective.md`（历史记录）
- 不自行安装/下载；命令缺失 → 停下报告
- **本任务不得留半成品**：字段改名与生成器同步必须一起完成，结束时 `make check` 必须 EXIT=0

## 验收标准

1. `opcodes.yaml` 中 cfx 家族字段名为 `cfxha`/`cghb`/`rchc`/`rdhd`；bits/role/bank 未变
2. 生成表（`docs/assembly-list.md` + 12 内嵌表）cfx 行如 §6 所列
3. 生成器**幂等**（重跑无 diff）；其它 248 条渲染**不变**（给出 diff 证据）
4. `make check` EXIT=0（含 `check-asm-list-consistency`）
5. 全库（`tools/`/`contracts/`/`docs/`/`tests/`）无遗留 `cfxcode` 字段引用（历史文档除外，须列明）
6. 反例验证：注入（如 `cfxha`→`cfxcode`）→ 生成表回退旧形式可检出；复原后无残留

## 完成区

**测试结果**：`make check` EXIT=0（`check-asm-list-consistency: 12 spec files OK`；`repository checks: PASS`）

**修改文件**（7 个）：
1. `tools/spec/generate_opcodes.py` — `f_crrr()` 字段名 `cfxcode→cfxha`、`hb→cghb`、`hc→rchc`、`hd→rdhd`；`f_crii()`/`f_ciii()` 字段名 `cfxcode→cfxha`（role/bank/bits 不变）
2. `contracts/opcodes.yaml` — 由 `generate_opcodes.py` 重生成，cfx 家族 6 条字段名更新
3. `tools/llvm/gen_asm_list.py` — `operands()` 名称匹配 `cfxcode→cfxha`；`FIELD_RE` 增 `cfx` 前缀；`field_name()` 文档字符串同步；`new_form()` escape/trap 两处 `cfxcode→cfxHA`
4. `contracts/legality_rules.yaml` L295 — `cfxcode→cfxha`（字段引用）
5. `docs/assembly-list.md` — 重生成，cfx 6 行更新
6. `spec/SimRISC-11-其它.md` — 内嵌表 cfx2rd/cfx2rc/escape/trap 4 行更新
7. `spec/SimRISC-12-待定.md` — 内嵌表 cfxld/cfxst 2 行更新

**验收结果**：

*期望形式逐条核对*：
| 指令 | 期望 | 实际 | 结果 |
|------|------|------|------|
| `cfxld` | `cfxld   cfxHA, [rbHB, immu12]` | `cfxld cfxHA, [rbHB, immu12]` | ✅ |
| `cfxst` | `cfxst   cfxHA, [rbHB, immu12]` | `cfxst cfxHA, [rbHB, immu12]` | ✅ |
| `cfx2rd` | `cfx2rd  cfxHA, cgHB, rcHC, rdHD` | `cfx2rd cfxHA, cgHB, rcHC, rdHD` | ✅ |
| `cfx2rc` | `cfx2rc  cfxHA, cgHB, rcHC, rdHD` | `cfx2rc cfxHA, cgHB, rcHC, rdHD` | ✅ |
| `escape` | `escape  cfxHA, [excp_cause_ip, imms18i]` | `escape cfxHA, [excp_cause_ip, imms18i]` | ✅ |
| `trap` | `trap    cfxHA, immu18` | `trap cfxHA, immu18` | ✅ |

*生成器幂等*：重跑 `generate_opcodes.py` + `gen_asm_list.py` + `--embed-spec` 后 `git diff` 无新增变更。✅

*其它 248 条渲染不变*：`git diff --stat` 显示仅 `SimRISC-11`（4 行）和 `SimRISC-12`（2 行）内嵌表变更，其余10个 spec 文件无 diff。✅

*opcodes.yaml diff 证据*：仅 cfx 家族 6 条的字段名变更（`cfxcode→cfxha` 6处、`hb→cghb` 2处、`hc→rchc` 2处、`hd→rdhd` 2处），共 24 行变更（12 `-` + 12 `+`）。role/bank/bits 全部不变。✅

*全库 `cfxcode` 残留清单*（`tools/`/`contracts/`/`docs/`/`tests/`，排除 `docs/m1-retrospective.md`）：
| 文件 | 行 | 内容 | 保留理由 |
|------|-----|------|---------|
| `tools/spec/generate_opcodes.py` | 95,102,108 | `_field("cfxha", ..., "cfxcode", ...)` | role 值，不变 |
| `tools/llvm/generate_instrinfo.py` | 101 | `role in ("cfxcode", ...)` | role 匹配，不变 |
| `tools/llvm/gen_asm_list.py` | 15,36,84,199,218 | role 名 / kind 值 / OPERAND_ROLES | role 名不变 |
| `contracts/opcodes.yaml` | 6处 | `role: cfxcode` | role 值，不变 |
| `docs/spec/assembly-language.md` | 151,155,156 | `cfxcode 写作 cfxN` | 语法规范文档，描述 cfxcode 概念在汇编中的表示；非本任务范围（任务书未列出该文件） |
| `docs/self-consistency.md` | 41,53,86 | SEE 规范概念引用 | 非生成物，架构概念描述，非字段引用 |
| `docs/m1-retrospective.md` | — | 历史记录 | 任务约束明确不改 |

*反例注入+复原*：
- 注入：`f_crrr()` 中 `cfxha` → `cfxcode`，重生成后 `cfx2rd`/`cfx2rc` 回退为旧形式 `cfxcode, cgHB, rcHC, rdHD`（检出成功）
- `git diff --name-only` 注入后非空（确认注入生效）
- 复原：还原备份文件，`git diff` 恢复原状（7 文件变更），`make check` EXIT=0
- 无残留 ✅

*`make check` 真实退出码*：
```
$ make check > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 64 open, 10 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

**新发现/坑**：
- `FIELD_RE` 原正则 `^(rd|rb|ra|rf|cg|rc)([a-z]{2})$` 不匹配3字母前缀 `cfx`，需扩展 alternation；`cghb`/`rchc` 的 `cg`/`rc` 前缀原本就匹配，无需改
- `docs/spec/assembly-language.md` L151/155/156 有 `cfxcode` 字段引用（"cfxcode 写作 cfxN"），不在本任务范围但建议后续同步
- `docs/self-consistency.md` 的 `cfxcode` 是架构概念引用（SEE cfxcode 分配表），非字段名

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

审查范围：`tools/spec/generate_opcodes.py`、`tools/llvm/gen_asm_list.py`、`contracts/legality_rules.yaml` 三文件 diff。

审查结论：**无 finding，所有改动正确**。

逐条审查：

| # | 检查点 | 结论 |
|---|--------|------|
| 1 | `f_crrr()` 的 `R("cghb", ..., bank="rb")` — `bank` 显式传入，不受 `_bank_of("cghb")` 返回 `"imm"` 影响 | ✅ 正确 |
| 2 | `FIELD_RE` 增 `cfx` — `cfxha` 匹配 `("cfx","ha")` → `cfxHA`；`cghb`/`rchc`/`rdhd` 原本就匹配 | ✅ 正确 |
| 3 | `operands()` 的 `kind="cfxcode"` 不变 → `template()`/`example_line()` 的 kind 匹配仍有效 | ✅ 正确 |
| 4 | `new_form()` escape/trap 硬编码 `cfxHA` — 与期望形式一致 | ✅ 正确 |
| 5 | `legality_rules.yaml` L295 — 字段引用 `cfxcode→cfxha`，语义不变 | ✅ 正确 |
| 6 | role 值（`"cfxcode"`/`"cfx_cg"`/`"cfx_rc"`）全部未改 | ✅ 符合约束 |
| 7 | `new_template()` 死代码未改 | ✅ 符合任务要求 |
| 8 | `OPERAND_ROLES` 未改（role 名集合） | ✅ 符合约束 |

**判决：通过，无遗留 finding。**

#### 第 1 轮 reviewer 验收

**审查范围**：`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`tools/spec/generate_opcodes.py`、`tools/llvm/gen_asm_list.py`、`docs/assembly-list.md`、`spec/SimRISC-11/12`。反例注入在 `/tmp/opencode/SPEC-052t/` 副本内完成（已清理），真实仓库工作区未被污染（全程 `git diff` 哈希不变）。

**重跑记录（均为审查者亲自执行，非转述）**：

*① 字段重命名与 bits/role/bank 不变* —— 用 python 结构化对比 `HEAD:contracts/opcodes.yaml` 与工作区：
```
cfx family ids: ['cfx2rd_crrr_cfx','cfx2rc_crrr_cfx','cfxld_crii_cfx','cfxst_crii_cfx','escape_ciii_cfx','trap_ciii_cfx']
total changed entries: 6
   （逐个 field 比较除 name 外全部属性 → 全部相等；顶层除 fields 外全部相等）
cfx2rd/cfx2rc 字段：cfxha[23:18]/cfxcode/imm、cghb[17:12]/cfx_cg/rb、rchc[11:6]/cfx_rc/rc、rdhd[5:0]/dst/rd
cfxld/cfxst：cfxha + rbhb/src/rb + immu12
escape/trap：cfxha + imms18/immu18
```
→ 仅 6 条 cfx entry 变更，且**只改了 `name`**；bits/role/bank 逐条一致。

*② 生成表 cfx 行（工作区实读）*：
```
docs/assembly-list.md:316  | `cfx2rc` | `crrr` | `cfx` | `cfx2rc cfxHA, cgHB, rcHC, rdHD` |
docs/assembly-list.md:317  | `cfx2rd` | `crrr` | `cfx` | `cfx2rd cfxHA, cgHB, rcHC, rdHD` |
docs/assembly-list.md:318  | `escape` | `ciii` | `cfx` | `escape cfxHA, [excp_cause_ip, imms18i]` |
docs/assembly-list.md:321  | `trap`   | `ciii` | `cfx` | `trap cfxHA, immu18` |
docs/assembly-list.md:327  | `cfxld`  | `crii` | `cfx` | `cfxld cfxHA, [rbHB, immu12]` |
docs/assembly-list.md:328  | `cfxst`  | `crii` | `cfx` | `cfxst cfxHA, [rbHB, immu12]` |
```
`spec/SimRISC-11` 4 行（cfx2rd/cfx2rc/escape/trap）+ `spec/SimRISC-12` 2 行（cfxld/cfxst）与 §6 期望**逐字一致**。

*③ 仅 cfx 行变化* —— python 逐行对比 `HEAD:docs/assembly-list.md` 与工作区（338 行 vs 338 行）：
```
differing line count: 6
```
6 行**全部是 cfx 家族行**（cfx2rc/cfx2rd/escape/trap/cfxld/cfxst），其余 **248 条指令行逐字未变**。10 个未涉及 spec 文件 sha256 全部 `OK`（幂等段落打印）。

*④ role 名不变*：`grep -nE "name: (hb|hc|hd)$" contracts/opcodes.yaml` → `NONE`；`contracts/opcodes.yaml` 仍有 `role: cfxcode` ×6；`tools/llvm/generate_instrinfo.py:101: if role in ("cfxcode","cfx_cg","cfx_rc"):` 未改（该文件不在 diff 内）。

*⑤ 生成器幂等* —— 依次运行 `python3 tools/spec/generate_opcodes.py`、`python3 tools/llvm/gen_asm_list.py -o docs/assembly-list.md`、`python3 tools/llvm/gen_asm_list.py --embed-spec`（三命令 `EXIT=0`），再 `sha256sum -c` 生成前快照：`contracts/opcodes.yaml`、`docs/assembly-list.md`、`spec/SimRISC-00..12` 共 14 文件**全部 `OK`**；`git diff | sha256sum` 前后均为 `941208257f465c9c…`（未新增变更）。

*⑥ `make check`（必须捕获命令自身退出码）*：
```
$ make check > /tmp/opencode/SPEC-052t.make_check.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
...
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 64 open, 10 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

*⑦ 残留核查*（`tools/`/`contracts/`/`docs/`/`tests/`，即任务验收范围）—— 逐处判定：
| 位置 | 类别 | 判定 |
|------|------|------|
| `tools/spec/generate_opcodes.py` 95/102/108 | role 值 `"cfxcode"` | (a) 允许 |
| `tools/llvm/generate_instrinfo.py` 101 | role 匹配 | (a) 允许 |
| `tools/llvm/gen_asm_list.py` 15/36/84/199/218 | role/kind 名 | (a) 允许 |
| `contracts/opcodes.yaml` ×6 | `role: cfxcode` | (a) 允许 |
| `docs/spec/assembly-language.md` 151/155/156 | cfx 记法说明 | (b) 下一任务 |
| `docs/self-consistency.md` 41/53/86 | SEE 概念 | (c) 允许 |
| `docs/m1-retrospective.md` | 历史 | (d) 允许 |

`grep -rn "cfxcode" docs/assembly-list.md spec/SimRISC-*.md` 的命中的是 `spec/SimRISC-00` 与 `spec/SimRISC-11`（速度表区块外）的**架构概念散文**（"六位的cfxcode" / "`cfx<cfxcode>` 记法"），非字段名、非渲染；且 `spec/` **不在任务验收范围**（任务仅列 `tools/contracts/docs/tests`）。**范围内无任何字段名/渲染残留**。

*⑧ 反例注入（在 `/tmp/opencode/SPEC-052t/` 副本内，真实仓库不受影响）*：
- **A) `cfxha`→`cfxcode`**（改 `generate_opcodes.py` 三处 `_field("cfxha"…)`，`diff -q` 确认注入生效）→ 重生成后：
  ```
  | `cfx2rc` | … | `cfx2rc cfxcode, cgHB, rcHC, rdHD` |
  | `cfx2rd` | … | `cfx2rd cfxcode, cgHB, rcHC, rdHD` |
  | `cfxld`  | … | `cfxld cfxcode, [rbHB, immu12]` |
  | `cfxst`  | … | `cfxst cfxcode, [rbHB, immu12]` |
  ```
  回退为旧形式，**可检出**（对照任务书 §6）。复原备份后一致。
  > 观察（非阻塞）：注入 A 时 `check_asm_list_consistency.py` 仍返回 `12 spec files OK / EXIT=0` —— 该脚本只校验「spec 内嵌表 ↔ 生成器输出」一致性，不校验绝对期望串，故不能单独拦截此注入。检出依赖对照 §6 期望形式（本任务 §6 即有此功能），符合验收标准 6「可检出」的表述。
- **B) 删除 `FIELD_RE` 的 `cfx` 分支**（`^(rd|rb|ra|rf|cg|rc)([a-z]{2})$`）→ 重生成后 `cfx2rd cfxha, cgHB, rcHC, rdHD`、`cfxld cfxha, [rbHB, immu12]`（`cfxHA` 未大写），**可检出**。
- **复原**：备份文件还原后 `diff -q` 全部 `identical`；真实仓库 `git diff` 哈希仍为 `9412082…`，`git status --porcelain | wc -l` = 8（与审查前一致），无残留；`/tmp/opencode/SPEC-052t` 已删除。

**约束核验（逐条）**：
| 约束 | 结果 |
|------|------|
| role 名不变（`cfxcode`/`cfx_cg`/`cfx_rc`）| ✅ `role: cfxcode` 保留、`generate_instrinfo.py` 未改 |
| 不影响 validate_instrinfo 槽位名 ha/hb/hc/hd | ✅ 未触碰该文件 |
| 不改 `docs/m1-retrospective.md` | ✅ 不在 diff 内 |
| 不自行安装/下载 | ✅ 无网络/安装动作 |
| 不得留半成品，`make check` EXIT=0 | ✅ 独立重跑 EXIT=0 |
| 验收 1 字段名+bite/role/bank | ✅ 结构化对比仅 6 entry 的 name 变 |
| 验收 2 生成表 cfx 行如 §6 | ✅ 6 行逐字一致 |
| 验收 3 幂等 + 248 条不变 | ✅ sha256 全 OK + 6/338 行 diff |
| 验收 4 `make check` EXIT=0 | ✅ |
| 验收 5 范围内无字段引用残留 | ✅（范围内仅 role/kind 名 + 已列明文档）|
| 验收 6 反例可检出 + 复原无残留 | ✅ A/B 两种注入均可检出，复原干净 |

**审查者结论**：所有验收命令在本人独立重跑下通过，硬约束逐条守住。完成区中的数字（24 行 opcodes diff、12 spec files OK、仅 SimRISC-11/12 变更、EXIT=0）与本人真实输出**完全一致**，无美化/转述。

**判决：Accepted。**

> 供架构师终审参考的两点观察（不构成返工）：
> 1. `docs/spec/assembly-language.md` 151/155/156 与 `spec/SimRISC-00/11` 的散文仍用架构概念 `cfxcode`；前者按任务书属下一任务，后者为原始规范概念名、非字段引用。
> 2. `check-asm-list-consistency` 为一致性校验而非绝对期望校验，无法单独拦截"字段名整体回退"类注入；若要机制化防回归，需另行增加期望串断言（本任务未要求）。
