# TESTCASES-018t: 向量 notes 文本笔误订正

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

## 问题描述（来自 `deferred.md`）

- **notes 文本笔误**（`006t` 遗留 N-1）：`ctrl-call.yaml` case[7] 与 `generate_ctrl_jump_call_ret.py` 的 notes 写「low 48=**0xAAAA000000000000**」（**多 4 个 0**），实际 `low48 = 0xAAAA00000000`（12 位十六进制 = 48 位）。**数值全部正确**、重算 0 mismatch；纯文本笔误。

## 修改内容

1. `tools/testcases/generate_ctrl_jump_call_ret.py`：notes 的 `0xAAAA000000000000` → `0xAAAA00000000`
2. 重新生成 `tests/vectors/isa/ctrl-call.yaml`（确认仅该文本变化）

## 约束

- 只改该文本；**不动任何编码/期望值/其他 notes**
- 生成器重跑须幂等（重跑无 diff）
- 完成后 `make check` EXIT=0；`validate_vectors` 178/178

## 验收标准

1. notes 中的 `low 48` 数值为 `0xAAAA00000000`（48 位）
2. 向量语义未变（`ctrl-call.yaml` 逐 case 比对仅该文本差异）
3. 生成器幂等；`validate_vectors` EXIT=0；`make check` EXIT=0

## 完成区
**测试结果**：validate_vectors 177/177 PASS；make check EXIT=0（全绿）
**修改文件**：
- `tools/testcases/generate_ctrl_jump_call_ret.py`（第274行）：notes `0xAAAA000000000000` → `0xAAAA00000000`
- `tests/vectors/isa/ctrl-call.yaml`（重生成）：对应 notes 同步订正

**验收结果**：
```
$ git diff --stat
 tests/vectors/isa/ctrl-call.yaml               | 3 +--
 tools/testcases/generate_ctrl_jump_call_ret.py | 2 +-
 2 files changed, 2 insertions(+), 3 deletions(-)
```
diff 仅该文本变化（generator 第274行 + yaml 第205行），无编码/期望值/其他 notes 改动。

幂等验证：重跑 generator 后 diff 不变 ✓

语义验证：
```
ra63 = 0x0001AAAA00000000
low 48 = 0xAAAA00000000 (48 bits)
notes says: 0xAAAA00000000 → match: True
```

```
$ python3 tools/testcases/validate_vectors.py
validate_vectors: 177/177 M1 identities covered OK (inventory sync OK; 15 data files, 744 cases; data coverage gaps: 0)
```

```
$ make check
validate_vectors: 177/177 M1 identities covered OK
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
repository checks: PASS
```

**新发现/坑**：无
**遗留问题**：无

#### 第 1 轮 engineer 自审
逐行审查完毕：
- 逻辑正确性：`0xAAAA_0000_0000` 的 low 48 = `0xAAAA00000000`（12 hex =48 bit），原 notes 写 `0xAAAA000000000000`（16 hex =64 bit）确为笔误 ✓
- 修改范围：仅改 notes 字符串，不动编码/期望值/其他 notes ✓
- 幂等性：重跑 generator diff 不变 ✓
- 验收：validate_vectors 177/177、make check EXIT=0 ✓

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| （无） | — | — | — |

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收

**判决：Accepted**（验收命令全部独立重跑通过；约束逐条守住；无规避动作）

**一、分析的文件**
- `tools/testcases/generate_ctrl_jump_call_ret.py`（生成器，第 274 行 notes）
- `tests/vectors/isa/ctrl-call.yaml`（重生成产物，第 205 行 notes）
- `contracts/opcodes.yaml`（M1 身份集计数，用于核对 177/178）
- `Makefile`（`check` / `validate-vectors` 目标）
- 台账：`.tao/knowledge/deferred.md`、`docs/issues.yaml`

**二、重跑记录（均为本审查者独立执行）**

1) 生成器 diff（文本订正确认）：
```
$ git diff -- tools/testcases/generate_ctrl_jump_call_ret.py
@@ -271,7 +271,7 @@ def _gen_call_rrii():
-              "high 16=0x0001 (valid), low 48=0xAAAA000000000000; "
+              "high 16=0x0001 (valid), low 48=0xAAAA00000000; "
```
仅 1 行、仅该 4 个多余 `0` 被删除；无编码/期望值改动。

2) 旧 vs 新 `ctrl-call.yaml` **逐 case 逐字段**比对（本审查者脚本，解析 YAML 后比对全部 9 条 case 的所有字段）：
```
$ git show HEAD:tests/vectors/isa/ctrl-call.yaml > old.yaml && cp tests/vectors/isa/ctrl-call.yaml new.yaml
$ python3 /tmp/opencode/TESTCASES-018t/cmp_cases.py
old entries: 9 new entries: 9
differing (index, field) pairs: [(7, 'notes')]
[7] field 'notes':
  OLD: "... low 48=0xAAAA000000000000; ..."
  NEW: "... low 48=0xAAAA00000000; ..."
TOTAL differing fields: 1
  index 7 id=call_rrii_ra class=semantic field=notes
```
→ 9 条 case 中**仅 case[7]（`call_rrii_ra` semantic）的 `notes`** 一处差异，且差异恰为笔误订正；其余 8 条 case 的所有字段（`encoding`/`expected_state`/`expected_pc`/`input_state`/`spec_cite`/`status` 等）**零差异**。文件级 `git diff` 的换行重排（1 insertion/2 deletions）全部落在**同一 `notes` 字段内部**，系 YAML `width=120` 自动折行，不含语义变化。

3) 生成器**幂等**（重跑无 diff）：
```
$ md5sum tests/vectors/isa/ctrl-{jump,call,ret}.yaml > before.txt
$ python3 tools/testcases/generate_ctrl_jump_call_ret.py; echo GEN_EXIT=$?
Wrote .../ctrl-jump.yaml: 6 cases ... / ctrl-call.yaml: 9 cases ... / ctrl-ret.yaml: 2 cases ...
Total: 17 cases across 3 files
GEN_EXIT=0
$ md5sum -c before.txt; echo IDEMPOTENT_EXIT=$?
tests/vectors/isa/ctrl-jump.yaml: OK
tests/vectors/isa/ctrl-call.yaml: OK
tests/vectors/isa/ctrl-ret.yaml: OK
IDEMPOTENT_EXIT=0
$ git diff --stat -- tests/vectors/isa/
 tests/vectors/isa/ctrl-call.yaml | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```
→ 重跑逐字节一致；生成器只写 3 个文件，实际仅 `ctrl-call.yaml` 变更。

4) `validate_vectors`：
```
$ python3 tools/testcases/validate_vectors.py; echo EXIT=$?
validate_vectors: 177/177 M1 identities covered OK (inventory sync OK; 15 data files, 744 cases; data coverage gaps: 0)
EXIT=0
```

5) `make check`：
```
$ make check; echo EXIT=$?
... manifest validation: PASS
validate_vectors: 177/177 M1 identities covered OK ...
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
check_issues: 65 open, 9 closed (0 blocking M1-gate: 0)
repository checks: PASS
EXIT=0
```

6) **反例门控（证明比对方法有判别力，非恒真）**——向副本注入 `encoding.word` 改动：
```
differing (index, field) pairs: [(4, 'encoding'), (7, 'notes')]
[4] field 'encoding': OLD {"word": "0x75000002"} NEW {"word": "0x75000003"}
```
→ 比对脚本能检出编码字段被篡改；本任务的「仅该文本变化」结论非真空。

**三、数值语义独立核算**
```
ra63 = 0x0001AAAA00000000
low48 = ra63 & 0xFFFFFFFFFFFF = 0xaaaa00000000  (12 hex = 48 bit)
旧笔误值 0xAAAA000000000000 = 16 hex = 64 bit（确为多 4 个 0）
```
→ 订正后 `0xAAAA00000000` 语义正确。

**四、约束逐条核验**

| 约束 | 结论 | 证据 |
|------|------|------|
| 只改该文本，不动编码/期望值/其他 notes | ✅ | 第 2 项逐字段比对：9 case 仅 index 7 `notes` 一处差异 |
| 生成器重跑幂等（重跑无 diff） | ✅ | 第 3 项 md5 全部 OK、`IDEMPOTENT_EXIT=0` |
| 完成后 `make check` EXIT=0 | ✅ | 第 5 项 `EXIT=0`，`repository checks: PASS` |
| 验收标准 1：notes 值为 `0xAAAA00000000`（48 位） | ✅ | 第 1 项 diff + 第三项核算 |
| 验收标准 2：向量语义未变 | ✅ | 第 2 项逐 case 比对 |
| 验收标准 3：生成器幂等 + validate_vectors/make check EXIT=0 | ✅ | 第 3/4/5 项 |

**五、非阻断观察（供架构师终审，不影响本任务验收）**

1. **任务书约束「`validate_vectors` 178/178」为陈旧值**：实测 **177/177**。根因是上游 `SPEC-039t`（commit `166c1a3`）将 `fence` 移出 M1（`opcodes.yaml` M1 身份 178→177），本任务的纯文本订正不改变覆盖计数。验收标准 #3 只要求 `EXIT=0`，已满足；完成区写 177/177 与实测一致（无夸大）。
2. **台账未同步（超出本任务声明的 2 文件范围）**：`docs/issues.yaml` 的 `ISS-030`（本笔误）仍 `status: open` / `resolved_by: null`；`deferred.md` 的「N-1 notes 文本笔误」条目原样保留。任务「修改内容」仅声明 2 个文件、验收标准未含台账项，故不判返工；但项目惯例（如 `SPEC-039t` 关闭 `ISS-056` + 更新 deferred）建议由主会话/架构师在 `/complete` 时关闭 `ISS-030` 并标注 deferred 条目已消解，以保持可审计性。
3. **工作区含其他任务未提交改动**（INFRA-017t / INTEG-006t / LLVM-022t / QEMU-027t 等，mtime 与本任务相近，系并行任务）：完成区的 `git diff --stat`「仅 2 文件」是任务写入时的真实快照（目标两文件的 diff 与所述一致），非虚构。本审查只针对本任务的 2 个产物。

**六、我验证了 / 我采信的**
- 亲自重跑并核验：生成器 diff、逐 case 语义比对、幂等 md5、`validate_vectors`、`make check`、数值核算、比对脚本反例。
- 采信（未独立重跑）：无（本轮全部结论均有本审查者的真实终端输出）。