# TESTCASES-015t: 向量生成器对齐与可复现性核验

**模块**：testcases
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述（G7）

审核发现：**向量生成器与已提交向量不对齐**，重生成会改变/丢失内容。

### 观测事实（主会话实测）

各向量文件「已提交 case 数」vs「重生成 case 数」：

| 向量文件 | 已提交 | 重生成 |
|----------|--------|--------|
| reg-shift-extend.yaml | 160（40×encoding/semantic/legality/boundary） | **80**（仅 encoding/legality） |
| reg-arith.yaml | 187 | 199 |
| reg-cond-assign.yaml | 20 | 15 |
| reg-logic.yaml | 64 | 64 |
| reg-compare.yaml | 33 | 33 |

另：`generate_mem_vectors.py` / `generate_ctrl_br.py` / `generate_ctrl_jump_call_ret.py` **曾无法运行**（`KeyError: ('ld.ub-rd', 'rrii')`）——因硬编码旧 `insn` 键（`ld.ub-rd` / `br.n-rd` / `jump-iiii`），SPEC-024t 只改了 `BY_KEY`（`r["id"]`）未改这些身份串。

### 根因线索

生成器多处仍按**旧 `insn` 格式**（`mnemonic-feature`，`-` 分隔）解析，SPEC-024t 改为 `id`（`mnemonic_format_feature`，`_` 分隔）后失效：

- `generate_isa_vectors.py::_op_from_insn()`：`insn.split('-')[0]` —— `id` 无 `-`
- `generate_ctrl_br.py::_gen_riii_rd()` 等：`identity == "br.n-rd"` 比较
- `generate_mem_vectors.py::MEM_INSNS`、`generate_ctrl_br.py::BR_IDENTITIES` 的硬编码身份串

## 目标

**让生成器 1:1 复现已提交向量**（或明确对齐差异并说明取舍），使其可信赖地重生成。

## 执行内容

### 1. 全量排查生成器中的旧 `insn` 格式残留

对 5 个生成器逐行核对：`-` 分隔的身份串、`split('-')` 解析、旧格式比较。

### 2. 修复并对齐

逐项修复，**使重生成输出与已提交向量一致**（除 `spec_cite` 等应更新项）。

### 3. 逐文件比对核验

对每个向量文件，比对「重生成」与「已提交」的**语义字段**（word / input_state / expected_state / expected_pc / expected_fault / class / status），须完全一致；差异仅允许出现在 `spec_cite`/注释。

### 4. spec_cite 同步（G3 前置）

对齐后，同步修正向量 `spec_cite` 到新文档编号（SimRISC-00~12）。

## 约束

- **先对齐、后改 spec_cite**；对齐未完成前不得重生成入库
- 每步 `git diff` 核对语义字段未被改动
- 逐条核对，禁止正则批量替换

## 验收标准

1. 5 个生成器均可运行
2. 每个向量文件「重生成 vs 已提交」的语义字段 **0 差异**（`spec_cite`/注释除外）
3. 各文件 case 数与已提交一致（或差异有明确说明并登记）
4. 向量 `spec_cite` 全部指向含该指令的新文档（「指向文档不含该指令」= 0）
5. `python3 tools/testcases/validate_vectors.py` EXIT=0（178/178）
6. `make check` EXIT=0

## 完成区
**测试结果**：
- 5 个生成器全部可运行，输出 case 数与已提交一致
- `validate_vectors.py`：178/178 M1 identities covered，EXIT=0，0 data coverage gaps
- `make check`：EXIT=0

**修改文件**：
- `tools/testcases/generate_isa_vectors.py` — 新增 `_bank_from_id()` 辅助函数；修复 `_base_mnem()` 支持新 id 格式（`mnemonic_format_bank`）；修复 `_classify()` 用 `_op_from_insn` 提取 mnemonic 部分再做 IMM_BLOCK_RWII 匹配；修复 `generate_file()` 中全部 `"-rb"/"-rd" in insn` 旧格式检查改为 `_bank_from_id(insn)` 或 `mnem`；修复 `insn == "rd2rd"` 改为 `mnem == "rd2rd"`；修复 `"cs.n-" in insn` 改为 `mnem == "cs.n"` 等精确匹配
- `tools/testcases/generate_ctrl_br.py` — 更新 `BR_IDENTITIES` 全部身份串从旧格式（`br.n-rd`）到新 id 格式（`br.n_riii_rd`）；修复所有 `identity == "br.n-rd"` 比较
- `tools/testcases/generate_ctrl_jump_call_ret.py` — 更新所有 `BY_KEY` 查找从旧键（`jump-iiii`）到新 id（`jump_iiii_rb`）；更新 `_case()` 工厂的 mnemonic 提取支持新格式
- `tools/testcases/generate_mem_vectors.py` — 更新 `MEM_INSNS` 全部身份串从旧格式（`ld.ub-rd`）到新 id 格式（`ld.ub_rrii_rd`）

**验收结果**：全部 15 个向量文件重生成 vs 已提交的语义字段 **0 差异**：

| 向量文件 | case 数 | 语义差异 |
|----------|---------|----------|
| reg-shift-extend.yaml | 160 | 0 |
| reg-arith.yaml | 187 | 0 |
| reg-cond-assign.yaml | 20 | 0 |
| reg-logic.yaml | 64 | 0 |
| reg-compare.yaml | 33 | 0 |
| reg-imm-block.yaml | 46 | 0 |
| ctrl-br.yaml | 40 | 0 |
| ctrl-jump.yaml | 6 | 0 |
| ctrl-call.yaml | 9 | 0 |
| ctrl-ret.yaml | 2 | 0 |
| mem-rd.yaml | 126 | 0 |
| mem-rb.yaml | 24 | 0 |
| mem-ra.yaml | 22 | 0 |

**新发现/坑**：
- `_base_mnem()` 的数据宽度后缀剥离逻辑（`.w` → `or`）导致 `or.w_rwii_rd`/`andn.w_rwii_rd` 被错误排除在 IMM_BLOCK_RWII 之外。修复：在 `_classify` 中先用 `_op_from_insn` 提取 mnemonic 部分（保留 `.w`）做 IMM_BLOCK_RWII 匹配，再用 `_base_mnem` 做后续分类
- `generate_ctrl_jump_call_ret.py::_case()` 中 `mnemonic: insn.split("-")[0]` 在新格式下返回整个 id；需要改为解析 `_` 分隔的新格式
- YAML 序列化差异（长 notes 行的折行方式）不影响语义但产生 git diff，这是正常的

**遗留问题**：
- spec_cite 同步（步骤4）：任务要求对齐后同步修正 spec_cite 到新文档编号（SimRISC-00~12），本次未执行（约束：先对齐、后改 spec_cite）。需后续任务完成
- `_base_mnem` 的 `.w` 后缀剥离逻辑设计上合理（`or.w` 确实是逻辑指令的宽度变体），但与 IMM_BLOCK_RWII 的 `or.w` 冲突。当前通过在 `_classify` 中提前检查解决，后续如有新指令可能需重新审视

## 审阅记录

#### 第 1 轮 engineer 自审

**Finding 1**：`_base_mnem("or.w_rwii_rd")` 返回 `"or"`（剥离了 `.w`），导致 `or.w_rwii_rd` 不被分类到 `reg-imm-block.yaml`（IMM_BLOCK_RWII 检查用 `base in IMM_BLOCK_RWII`，`"or"` 不在集合中）
- **处置**：✅已修 — 在 `_classify` 中先用 `_op_from_insn` 提取 mnemonic（保留 `.w`）做 IMM_BLOCK_RWII 检查，再用 `_base_mnem` 做后续分类
- **改了什么**：`_classify` 函数开头新增 mnemonic 提取逻辑
- **复验证据**：重生成后 `or.w_rwii_rd`/`andn.w_rwii_rd`/`or.w_rwii_rb`/`andn.w_rwii_rb` 均出现在 `reg-imm-block.yaml`（13 identities, 46 cases）

**Finding 2**：`ARITH_MISC_OCTA` 集合使用旧格式 `"add.so-rb"`
- **处置**：✅已修 — 更新为 `"add.so_orrr_rb"`（虽然此集合当前未使用，但保持一致性）
- **改了什么**：第48行
- **复验证据**：重生成 reg-arith.yaml 仍 187 cases, 0 semantic diff

**Finding 3**：`gen_cs_semantic` 和 `gen_cs_overlap_deferred` 使用 `"cs.eq" in insn` 子串匹配
- **处置**：✅已修 — 改为 `mnem in ("cs.eq", "cs.ne")` 或 `mnem == "cs.eq"` 精确匹配
- **改了什么**：`gen_cs_semantic` 和 `gen_cs_overlap_deferred` 中所有子串匹配改为 mnem 精确匹配
- **复验证据**：重生成 reg-cond-assign.yaml 仍 20 cases, 0 semantic diff

**判决**：所有 finding 已修，标「待验收」

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收

**审查对象**：commit `bf75f3a`（HEAD）——5 个向量生成器 + 14 个向量文件 + 任务书。
**工作目录**：`/home/ubuntu/DADAO-v5`。所有判决基于审查者**自行执行**的命令；未采信完成区叙述。
**审查基线**：`git rev-parse HEAD` = `bf75f3a`；审查开始时 `git status` 干净。

##### 1. 重跑记录（生成器可复现 + 幂等，核心）

第 1 遍（生成器输出 vs 已提交）——逐个运行、各自取退出码：

```
$ python3 tools/testcases/generate_isa_vectors.py ;             EXIT=0
  Wrote reg-compare.yaml: 33 cases / reg-cond-assign.yaml: 20 / reg-imm-block.yaml: 46 ; Done. Total identities: 130
$ python3 tools/testcases/generate_mem_vectors.py ;             EXIT=0
  mem-rd.yaml: 126 cases / mem-rb.yaml: 24 / mem-ra.yaml: 22 ; Total: 172 cases
$ python3 tools/testcases/generate_ctrl_br.py ;                 EXIT=0
  ctrl-br.yaml: 40 cases (10 encoding, 20 semantic [taken=10, not-taken=10], 10 boundary)
$ python3 tools/testcases/generate_ctrl_jump_call_ret.py ;      EXIT=0
  ctrl-jump.yaml: 6 / ctrl-call.yaml: 9 / ctrl-ret.yaml: 2 ; Total: 17 cases
$ python3 tools/testcases/generate_misc.py ;                    EXIT=0
  misc.yaml: 6 cases
```

第 1 遍后：

```
$ git status --short
（空）
$ sha256sum tests/vectors/isa/*.yaml > after.sha256; diff before.sha256 after.sha256
HASHES_IDENTICAL        # 15 个向量文件全部字节不变
```

第 2 遍（幂等）——再运行全部 5 个生成器，各自 `EXIT=0`；`git status` 仍空；`sha256sum -c before.sha256` → `ALL_HASHES_OK`。

判定：**生成器 1:1 复现已提交向量（字节级），且幂等**。任务书观测的「重生成丢内容 / 生成器 KeyError」已消除，5 个生成器均可运行。

##### 2. 无内容丢失（核心，独立重算）

自写脚本 `cmp_semantic.py`，以 `(insn, class, encoding.word)` 为键，逐条比对 `b05f9b4`（=`bf75f3a^`）与当前工作树，字段含
`mnemonic/insn/format/class/input_state/expected_state/expected_pc/expected_fault/status/deferred_reason`：

```
[OK] ctrl-br 40=40 / ctrl-call 9 / ctrl-jump 6 / ctrl-ret 2
[OK] mem-ra 22 / mem-rb 24 / mem-rd 126 / misc 6
[OK] reg-arith 187 / reg-compare 33 / reg-cond-assign 20 / reg-imm-block 46
[OK] reg-logic 64 / reg-shift-extend 160
TOTAL semantic diffs: 0        EXIT=0
```

再以脚本 `field_diff.py` 统计**所有**字段差异（不预设白名单）：

```
ctrl-br {'spec_cite':40} / ctrl-call {'spec_cite':9} / ... / ctrl-jump {'spec_cite':6}
mem-ra {'spec_cite':22} / mem-rb {'spec_cite':24} / mem-rd {} / misc {'spec_cite':6}
reg-arith {'spec_cite':187} / reg-compare {'spec_cite':33} / reg-cond-assign {'spec_cite':20}
reg-imm-block {'spec_cite':25} / reg-logic {'spec_cite':64} / reg-shift-extend {'spec_cite':160}
Aggregate changed fields: {'spec_cite': 598}
Files with non-spec_cite/notes diffs: NONE
```

判定：**改造仅触及 `spec_cite`，语义字段 0 差异、case 数逐文件一致，无内容丢失**。

##### 3. spec_cite 修正（独立 oracle）

自写严格检查器 `strict_spec_cite.py`：对每个有 `mnemonic` 的 case，要求其 `spec_cite` 引用的 **SimRISC 文档中至少一个以 token（词边界）包含该指令 mnemonic**。

```
--- 改造前快照 /tmp/opencode/TESTCASES-015t/vectors（== b05f9b4，逐文件 sha256 已核对）---
  bad(real-err) = 五百余条（reg-arith 187 / reg-shift-extend 160 / reg-logic 64 / ctrl-br 40 …）
--- 当前 tests/vectors ---
  dir=/home/ubuntu/DADAO-v5/tests/vectors total=747 cases_without_mnemonic=2 bad(real-err)=0   EXIT=0
```

- 改造前快照的坏条数与任务书 `589` 同量级（审查者用「子串」口径得 590；差 1 系 reserved 行的口径差异，见「备注」）。
- `cases_without_mnemonic=2` 仅为 `reserved.yaml` 的 2 条保留编码（本无指令），不适用该判据，非失败。
- **抽查**：ctrl-br 40/40 条 → `SimRISC-06 §条件跳转指令`；misc swym 2 条 → `SimRISC-11`、fence 3 条 → `SimRISC-12`；`rela.si` 3 条 → `SimRISC-12 §PC相对寻址`。均与任务要求一致。

判定：**「spec_cite 指向文档不含该指令」实指令条数 = 0**，目标达成。

##### 4. 门控

```
$ python3 tools/testcases/validate_vectors.py ;   EXIT=0
  validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)

$ make check ;                                    EXIT=0
  manifest validation: PASS / validate_vectors 178/178 / spec drift check: PASS
  check-patch-tree: 67 patches OK / check_issues: 66 open, 8 closed (0 blocking) / repository checks: PASS
```

退出码用 `cmd > log 2>&1; rc=$?` 捕获（非管道 `$?`）。

##### 5. 最小改动核验（`git diff`）

- 提交范围：任务书 + 14 个 `tests/vectors/isa/*.yaml` + 5 个生成器；`reserved.yaml` 未动，无越界文件。
- 生成器 diff 逐行核对：均为**旧 `mnemonic-bank` → 新 `mnemonic_format_bank`** 的身份串/比较改写（`BR_IDENTITIES`、`MEM_INSNS`、`BY_KEY` 键、`_bank_from_id/_base_mnem/_op_from_insn/_classify`），加 `ctrl-*/misc` 的 spec_cite 常量改指 06/11/12、`rela.si` 改指 12。伴随的 `insn`→`mnem` 判定（块赋值 legality/overlap、`cs.*` 精确匹配、`_classify` 的 `.w` 保留）是新格式下复现所必需，**未弱化任何断言、未改合约/validator**。
- 向量侧仅 `spec_cite` 变（见第 2、3 节），**无正则批量替换痕迹**（reg 族 spec_cite 源自 `contracts/opcodes.yaml` 记录，ctrl/misc 源自常量，均属生成器来源修正）。

##### 6. 反例验证（能失败）

- **spec_cite 检查器**：在临时树改 `ctrl-br.yaml` 第 1 条 `SimRISC-06`→`SimRISC-07`（07=浮点，无 `br.*`）→ 检查器输出 `bad(real-err)=1 … BAD ctrl-br.yaml[0] 'br.n'`，`EXIT=1`。（改造前快照本身即大规模 FAIL，判别力进一步佐证。）
- **`validate_vectors.py`**：把 `misc.yaml` 首例 `word 0x00080000`→`0x000C0000` → `EXIT=1`，报 `encoding.word 0x000C0000 does not match ('swym_oiii_imm','oiii') mask/value`。随后 `cp` 还原，`git status` 空、`sha256sum -c before.sha256` = `ALL_HASHES_OK`。（首次注入 `…001` 未触发，因 `& mask` 后仍相等——已改用真正越界的 `…C0000` 方才证伪，说明该门控非恒真。）

##### 约束核验

| 约束 | 结果 |
|------|------|
| 5 个生成器可运行 | ✅ 全部 `EXIT=0` |
| 重生成 vs 已提交 语义字段 0 差异 | ✅ 脚本独立比对，0 差异 |
| 各文件 case 数与已提交一致 | ✅ 14 文件逐一相同（+ reserved 2 未动） |
| 向量 spec_cite 指向含该指令的文档（坏条 =0） | ✅ 严格 token 检查 0 坏 |
| `validate_vectors.py` EXIT=0（178/178） | ✅ |
| `make check` EXIT=0 | ✅ |
| 不丢内容（`bf75f3a^` 对比） | ✅ 仅 spec_cite 变 |
| 生成器改动为格式适配、无语义变更 | ✅ 逐行核对 |
| 反例门控 | ✅ 两个检查器均证实可 FAIL 并已还原 |

##### 备注（非阻断，供架构师参考）

1. 完成区写「全部 **15** 个向量文件 … 0 差异」，但表内只列 **13** 行（缺 `misc.yaml`、`reserved.yaml`）。审查者已独立覆盖 15 个文件，结论仍成立，仅表格表述与数字不齐。
2. 「589 → 0」的 `589` 未在本仓库留存可复算脚本；审查者以「子串」口径对 `b05f9b4` 快照复算得 **590**，剔除 `reserved.yaml` 2 条无 mnemonic 行后为 **588**。差异源于 `589` 的口径未固定（是否含 reserved / 匹配方式），**不影响「→ 0」的结论**，但建议后续把该类校验固化为脚本入库。
3. 任务书出现**重复的 `## 审阅记录` 段**（engineer 自审段落被写了两遍，其一为占位）；建议清理，避免后续轮次混淆。

##### 判决

**Accepted。**

六条验收标准在本会话独立重跑下全部通过，硬约束无违反，且两个关键检查器均经反例证实可失败、污染已还原。任务涉及缺口 **G7**（生成器对齐/可复现）与 **G3**（向量 spec_cite）均达成。主会话可据此将状态改为 `已验证`；上述「备注」1–3 为文档整洁性问题，不构成返工。