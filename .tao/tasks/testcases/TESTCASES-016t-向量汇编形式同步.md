# TESTCASES-016t: 同步测试向量汇编形式

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：`SPEC-036t`（语法定义已更新——汇编文本同步只需语法定义，不依赖 MC 实现）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- 输入：`tests/vectors/isa/*.yaml`、`tests/vectors/schema.md`、`tests/vectors/README.md`、`tools/testcases/generate_*.py`
- 输出：更新上述文件中引用旧语法的文本
- 约束：
  - 只改汇编形式相关的文本，不改 encoding/expected_fault/expected_pc 等数据
  - 向量文件的 `notes` 字段可能包含旧语法汇编示例，需更新
  - 若审计后**确认无旧语法残留**，按空任务关闭（`已验证`，完成区注明「经 grep 审计无旧语法残留，无修改」）

## 修改内容

### 1. 审计范围

以下文件/目录中的旧语法文本需更新：

| 文件/目录 | 检查内容 |
|-----------|---------|
| `tests/vectors/isa/*.yaml` | `notes` 字段中的汇编示例 |
| `tests/vectors/schema.md` | 汇编示例 |
| `tests/vectors/README.md` | 汇编示例 |
| `tools/testcases/generate_*.py` | 硬编码的汇编示例文本 |

旧→新映射（按需）：
- `ld.ub rd8, rb2, 1` → `ld.ub rd8, [rb2, 1]`
- `br.eq rd8, rd0, [rb0, 4i]` → `br.eq {rd8, rd0}?, [rb0, 4i]`
- `ldm.ub rd8, rb0, rd1, 3` → `ldm.ub {rd8:rd10}, [rb0, rd1]`
- `jump 2` → `jump [rb0, 2i]`
- 等等

### 2. 注意

- `encoding` 字段（`{word, mask, value}`）不受语法变更影响
- `expected_fault`/`expected_pc` 不受影响
- `id` 字段（如 `ld.ub_rrii_rd`）是内部标识，不改

## 验收标准

1. **无旧语法残留**：以下 grep 命令均返回空（涵盖所有已知旧语法模式）：
   ```bash
   grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/vectors/ tools/testcases/
   grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/vectors/ tools/testcases/
   grep -rEn 'jump [0-9]' tests/vectors/ tools/testcases/
   grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/vectors/ tools/testcases/
   grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/vectors/ tools/testcases/
   ```
2. `python3 tools/testcases/validate_vectors.py` 全绿（向量验证通过）
3. 向量的 encoding/expected_fault/expected_pc 等数据未被改动（`git diff --stat` 仅涉及 notes/汇编文本文件）
4. `make check` 通过（无回归）
5. **反例注入**：选择一个已知含旧语法模式的文件（若存在），临时写入一条旧语法（如在某 `.yaml` 的 notes 中加 `br.eq rd8, rd0, 4`——旧语法，无 `[]`/`{}`），确认 grep 命中（验证 1 的 grep 能检出），然后还原。若审计后确认无旧语法残留可注入，则跳过此步并在完成区注明。
6. 若审计后确认无旧语法残留：完成区注明「经 grep 审计无旧语法残留，无修改」，状态直接置 `已验证`

## 完成区

**测试结果**：grep 审计 5 个官方模式 + 1 个扩展模式均 EXIT=1（无旧语法残留）；`make check` EXIT=0；`validate_vectors.py` 178/178 通过

**修改文件**：
- `tests/vectors/schema.md`：第 110 行编码注释 `ld.ub rd1, rb1, 0` → `ld.ub rd1, [rb1, 0]`（仅注释）
- `tools/testcases/generate_ctrl_br.py`：第 115-120 行注释 `br.X rd0:` → `br.X {rd0}?`（6 行，仅注释）

**验收结果**：
- 旧语法 grep 审计（全部 EXIT=1）：
  ```
  grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/vectors/ tools/testcases/ → EXIT=1
  grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/vectors/ tools/testcases/ → EXIT=1
  grep -rEn 'jump [0-9]' tests/vectors/ tools/testcases/ → EXIT=1
  grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/vectors/ tools/testcases/ → EXIT=1
  grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/vectors/ tools/testcases/ → EXIT=1
  ```
- 扩展模式 `br\.\w+ rd[0-9]+[^{]`：EXIT=1
- 反例注入验证：
  - 注入 `br.eq rd8, rd0, 4` 到 schema.md 末尾 → grep `br\.[a-z]+ rd[0-9]+,` 命中（EXIT=0）
  - 还原后 grep 恢复空（EXIT=1）
- `git diff --stat`：仅 2 个文件，7 行注释改动，无 encoding/expected_fault/expected_pc 数据改动
- `make check`：EXIT=0
- `validate_vectors.py`：178/178 M1 identities covered OK

**新发现/坑**：
- `generate_ctrl_br.py` 第 312-314 行的 `br.X:` 是条件名缩写标签（后跟寄存器赋值说明），不是汇编语法示例，不需要改——需区分「语法示例」与「条件名标签」

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：`tests/vectors/schema.md`（1 行注释）、`tools/testcases/generate_ctrl_br.py`（6 行注释）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 schema.md ld 旧语法 | ✅已修 | `ld.ub rd1, rb1, 0` → `ld.ub rd1, [rb1, 0]` | grep EXIT=1 |
| F2 generate_ctrl_br.py br 旧语法 | ✅已修 | `br.X rd0:` → `br.X {rd0}?`（6 行） | grep EXIT=1 |
| F3 generate_ctrl_br.py 312-314 行 | ⏸不改 | 条件名缩写标签，非汇编语法示例 | 上下文分析 |
| F4 grep 审计覆盖度 | ✅验证 | 反例注入命中+还原 | 注入 EXIT=0→还原 EXIT=1 |
| F5 make check/validator | ✅通过 | — | make check EXIT=0; validate 178/178 |

判决：所有 finding 已处置，标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：`tests/vectors/`（README.md、inventory.md、schema.md、isa/*.yaml）与 `tools/testcases/`（8 个 .py）全目录；对照 `docs/spec/assembly-language.md`（ADR-0013 冻结语法）。

**重跑记录**（reviewer 亲自执行，非转述）：

```
$ grep -rEn 'ld\.(ub|sb|uw|sw|ut|st|o) (rd|rb|ra|rf)[0-9]+, (rb|rd)[0-9]+,' tests/vectors/ tools/testcases/   → EXIT=1
$ grep -rEn 'br\.[a-z]+ rd[0-9]+,' tests/vectors/ tools/testcases/                                                → EXIT=1
$ grep -rEn 'jump [0-9]' tests/vectors/ tools/testcases/                                                          → EXIT=1
$ grep -rEn 'ldm\.\w+ (rd|rb|ra|rf)[0-9]+, rb' tests/vectors/ tools/testcases/                                    → EXIT=1
$ grep -rEn 'add\.(uo|so) rd[0-9]+, rd[0-9]+, rd' tests/vectors/ tools/testcases/                                 → EXIT=1
$ grep -rEn 'br\.\w+ rd[0-9]+[^{]' tests/vectors/ tools/testcases/                                               → EXIT=1
$ python3 tools/testcases/validate_vectors.py   → EXIT=0
    "validate_vectors: 178/178 M1 identities covered OK (inventory sync OK; 15 data files, 747 cases; data coverage gaps: 0)"
$ make check   → EXIT=0
    "validate_vectors: 178/178 … / spec drift check: PASS / check-asm-list-consistency: 12 spec files OK / repository checks: PASS"
```

**独立 grep 兜底**（6 条官方/扩展模式之外的补充模式，均 EXIT=1，无命中）：
- `mnemonic + 寄存器操作数`（实例级）：仅命中已被修复的两处，且显示为**新**语法（`schema.md:110 # ld.ub rd1, [rb1, 0]`；`generate_ctrl_br.py:115-120 # br.n {rd0}? …`）
- `ld/st` 无方括号旧式、`ldm/stm` 无花括号旧式、`cs.*` 无花括号旧式、3 操作数无花括号旧式、寄存器复制裸操作数、`jump 数字`、`cfxld/cfxst/swym/lr_nn/sc_nn` → 全 EXIT=1
- 残留命中均为**散文化描述**（如 `ctrl-call.yaml:135 "ra1 valid and ra0 low48=0 → RASOF"`）与**合法新语法** (`swym 0`)，非旧汇编示例

**反例注入（证伪 grep 非恒真）**：在 scope 内的临时文件 `tests/vectors/__reviewer_probe_016t.tmp` 写入 6 条旧语法，6 个 grep 全部命中并发 FAIL：
```
G1 ld.ub rd8, rb2, 1        → 命中 EXIT=0
G2 br.eq rd8, rd0, [rb0, 4i] → 命中 EXIT=0
G3 jump 2                   → 命中 EXIT=0
G4 ldm.ub rd8, rb0, rd1, 3  → 命中 EXIT=0
G5 add.so rd1, rd2, rd3     → 命中 EXIT=0
G6 br.eq rd8, rd0, 4        → 命中 EXIT=0
```
删除探针后 `git status --porcelain` 仅剩 3 个已知修改文件，6 个 grep 恢复 EXIT=1（注入已完全还原，无污染）。

**约束核验**（逐条）：

| # | 约束 | 结论 | 证据 |
|---|------|------|------|
| 1 | tests/vectors/ 与 tools/testcases/ 无旧语法示例 | PASS | 6 模式 + 6 补充模式全 EXIT=1；探针证明 grep 可失败 |
| 2 | 改动仅注释/文本，不动 encoding/input_state/expected 等语义字段 | PASS | `git diff -U0`：schema.md 1 行（仅 `#` 后注释，`word: "0x10041000"` 值不变）；generate_ctrl_br.py 6 行全为 `#` 注释（`git diff --numstat`：1/1、6/6）；**无任何 .yaml 被改** |
| 3 | 反例注入可复原 | PASS | 探针删除后 git status 干净、grep 恢复空 |
| 4 | `make check` EXIT=0 | PASS | 见重跑记录 |
| 5 | validate_vectors 178/178 | PASS | 见重跑记录 |
| 6 | 完成区与真实输出一致 | PASS | 工程师所述 EXIT=1/EXIT=0/178-178 与本人重跑逐条吻合 |

**改动正确性**：对照 `docs/spec/assembly-language.md`（冻结语法）——`ld.ub rd1, [rb1, 0]` 与 §5（L72 `ld.ub rd8, [rb2, 1]`）一致；`br.n {rd0}?` 与 §5（L110/L142 `br.n {rd0}?, [rb0, 4i]`）一致。工程师 F3（`generate_ctrl_br.py:312-314` 的 `br.n:`/`br.z:` 为条件标签而非汇编示例）经核对成立，非规避。

**判决：Accepted**

- 验收命令块在 reviewer 本人重跑下全部通过（EXIT 码一致），约束逐条无违反，改动为纯注释/文本且语法正确。
- 无阻断性问题。
