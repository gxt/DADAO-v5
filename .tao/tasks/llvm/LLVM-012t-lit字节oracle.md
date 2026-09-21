# LLVM-012t: lit 字节 oracle

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-011t`、`LLVM-008t`、`SPEC-003t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节为**下发前预检**结论，优先级高于下文旧文本；冲突时以本节为准。

**P1 — mnemonic 提取正则（实测踩坑）**：lit 的 `OBJ:` 行格式为
`# OBJ: {{[0-9a-f]+:}} AA BB CC DD{{.*}}<mnemonic>{{.*}}<操作数>`
（`{{.*}}` 是 **FileCheck 模式**，不是字面量）。提取 mnemonic 须**遇 `{{` 即停**，用 `([A-Za-z][A-Za-z0-9._]*)`；**不得**用 `\S+`（会吞掉 `{{.*}}` 与操作数，实测得到 `add.si{{.*}}rd8`）。

**P2 — N 下限须用独立计数（防空绿）**：原「下限 = lit 文件中 `# OBJ:` 行总数」是**自指**——若解析正则失配，计数与 N **同时下降**，门控失效。⇒ 计数须用**独立、更宽松**的方式（如按 `# OBJ:` 字面出现次数统计，或由 yaml 推导硬下限）；且须满足 `N == 独立计数` 才 exit 0。

**P3 — 反例门控（强制，AGENTS.md）**：实测真实数据 **41/41 全通过、0 错误** ⇒ 脚本永远只报 `41 patterns OK`，**无法证明它能失败**。故必须给出三组注入的真实输出：
- 注入**错字节**（改 1 位使 `(word & mask) != value`）→ 必须 `exit 1`
- 注入**错 mnemonic**（字节对但 mnemonic 改成别的）→ 必须 `exit 1`
- **空 `OBJ:` 集**（临时目录无 `OBJ:` 行）→ 必须 `exit 1`（防空绿）
还原后 → `41 patterns OK` / `exit 0`；**还原须含重建**并给 `git status`/`git diff` 证据。

**P4 — 与 `test_encoding_oracle.py` 的边界（避免重复造轮子）**：`tools/llvm/test_encoding_oracle.py`（`006t` 交付、`011t` 扩至 **68** 用例）独立校验 **`llvm-mc` 的实际输出**，**不解析 lit 文件**；本任务的 `check_lit_bytes.py` 校验 **lit 文件里手写的 `# OBJ:` 期望字节 ↔ `opcodes.yaml`**。二者**互补**、不重复；本任务**不得**去重造 oracle 逻辑，也**不运行**任何 LLVM 工具。

**P5 — 实测基线（可直接跑，预期通过）**：

| 项 | 实测 |
|---|---|
| `# OBJ:` 行总数 | **41**（含 `011t` 的 `ra.s` 11 条） |
| 匹配到**唯一**记录 | **41/41** ✓（无匹配 0、多匹配 0） |
| mnemonic 与命中记录一致 | **41/41** ✓ |

⇒ 预期输出 `41 patterns OK`、`exit 0`。另实测：多数 `mask=0xFF000000`（仅盖 op 字段），`orri`/`orrr` 为 `0xFFFC0000`；因 `op` 值每 insn 唯一，每条 word 仍**唯一命中** ⇒ 「无匹配」检查有效。

**P6 — 删除无信息量条目**：原差异 #1「编码表路径：`contracts/opcodes.yaml` → `contracts/opcodes.yaml`」为**同值笔误**，已删。


## 接口规范

- 输入：
  - `tests/lit/MC/Dadao/*.s` 的 `# OBJ:` 行（字节级期望）
  - `contracts/opcodes.yaml`（mask/value）
- 输出：`tools/llvm/check_lit_bytes.py`：lit `# OBJ:` 字节 ↔ `contracts/opcodes.yaml` 独立校验（真错误时 exit 1）
- 约束：
  - 只读 yaml/lit，不改任何文件
  - **不运行 LLVM 工具**（纯 Python + yaml），oracle 独立于实现
  - 脚本放 `tools/llvm/`

## 背景（完整）

### 目标

lit 文件中 `# OBJ:` 行手写了期望字节，但这些字节是否与 `contracts/opcodes.yaml` 的 mask/value 公式一致，从未有独立、常态化的验证。本任务补齐该 oracle。

### 设计理由

翻译链 `contracts/opcodes.yaml → LLVM → 测试` 中最弱环是「手写期望字节 ↔ 编码表」，须用独立 oracle 机械校验，避免人工手算遗漏。

### 关键概念 / 数据

**lit 字节校验**：从每个 `.s` 提取 `# OBJ: AA BB CC DD{{.*}}mnemonic`，`word=int("AABBCCDD",16)`；遍历 `contracts/opcodes.yaml` 找 `(word & mask) == value` 的记录；无匹配 → `WARN`（真错误，exit 1）；全匹配 → `check_lit_bytes: N patterns OK`（exit 0）。

**增强校验**：
- **mnemonic ↔ 命中记录**：提取 `OBJ:` 行尾的 mnemonic，与命中记录的 `mnemonic` 字段比对。不匹配 → exit 1（字节编码的是另一条指令）。
- **N ≥ 下限**：脚本须报告匹配的 pattern 总数 N，若 N = 0（即无任何 `OBJ:` 行被提取）→ exit 1（防空绿）。建议下限 = lit 文件中 `# OBJ:` 行总数（可从 `.s` 文件计数）。
- **mask 覆盖力提示**：多数 `mask = 0xFF000000`（只盖 op 字段），对 hb/hc/hd 字段错无检测力。脚本输出中标注「mask 仅盖 op」作为 informational 提示，不阻断（mask 宽度由 opcodes.yaml 决定，脚本不改 mask）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-022a-qfc-lit-oracle.md`（lit 部分）
- DADAO-0628：`scripts/check_lit_bytes.py`（形态参考，禁止复制正文）

## 交付物

- `tools/llvm/check_lit_bytes.py`：lit `# OBJ:` 字节 ↔ `contracts/opcodes.yaml` 独立 oracle
- 完成区附真实 stdout

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

2. **脚本目录**：`verif/` → `tools/llvm/`。
3. **lit 文件形态**：`tests/lit/MC/Dadao/*.s` 由 `LLVM-008t` 按 0.5.3 助记符生成并内建 `OBJ:`/`ASM:` 前缀 + `{{.*}}`；本任务**只做 oracle 校验，不改 lit 文件**。

## 已知坑 / 结论

1. **lit 字节 oracle 不运行 LLVM**：纯 Python + yaml，才能独立于实现发现工具/手推错误。
2. **正则兼容 spacer**：`# OBJ:` 提取 4 个 hex 字节，不关心其后 `{{.*}}`。
3. **无匹配即真错误**：exit 1，不可静默。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-022a-qfc-lit-oracle.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_lit_bytes.py`
- DADAO-0628：`.work/DADAO-0628/tests/lit/MC/Dadao/`
- 本项目：`contracts/opcodes.yaml`、`tests/lit/MC/Dadao/`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 tools/llvm/check_lit_bytes.py` 输出 `41 patterns OK`（**现在可跑**；实测 41/41 唯一匹配、mnemonic 全一致）、`exit 0`；存在无匹配字节 / mnemonic 不匹配 / `N == 0` / `N != 独立计数` 时 `exit 1`
2. 脚本不修改任何 yaml/lit 文件（只读）
3. 不含对 LLVM 工具的调用（`grep` 确认；**不运行** `llvm-mc`/`llvm-objdump`）
4. **反例门控（强制）**：三组注入（错字节 / 错 mnemonic / 空 `OBJ:` 集）均 `exit 1`；还原（含重建）→ `41 patterns OK`、`exit 0`。给真实输出 + 还原证据
5. **独立计数**：`N` 与「宽松方式独立统计的 `# OBJ:` 行数」**一致**（防空绿，见 P1/P2）
6. **边界**：不重复 `test_encoding_oracle.py` 的逻辑（见 P4）；脚本为纯 Python + yaml
7. 完成区粘贴**真实 stdout**（不转述）；结论与输出逐条对齐

## 完成区

**测试结果**：通过 5/5；失败 0

**修改文件**：`tools/llvm/check_lit_bytes.py`（新建）

**验收结果**：

1. **默认运行**：
```
check_lit_bytes: 41 patterns OK
  (info: 32/41 masks cover op-field only)
EXIT_CODE=0
```

2. **反例门控 (a) — 错字节**（`rrii_load.s` 第一条 `10 20 00 01` → **小写** `ff 20 00 01`；**须小写**——解析正则只收小写 hex，大写会被跳过而仅由「N ≠ 独立计数」兜住）：
```
  rrii_load.s:12: word=0xFF200001 — no match in opcodes.yaml
  N (40) != independent count (41)
EXIT_CODE=1
```

3. **反例门控 (b) — 错 mnemonic**（字节正确，`ld.ub` → `ld.uw`）：
```
  rrii_load.s:12: mnemonic 'ld.uw' != 'ld.ub' (insn=ld.ub-rd)
  N (40) != independent count (41)
EXIT_CODE=1
```

4. **反例门控 (c) — 空 OBJ 集**（临时目录仅含无 `OBJ:` 行的 dummy.s）：
```
check_lit_bytes: ERROR — N == 0 (no patterns extracted)
EXIT_CODE=1
```

5. **独立计数一致性**：`Independent count (literal # OBJ:): 41`，`N from script: 41`，`Match: True`

6. **不调用 LLVM 工具**：`grep -n 'llvm\|subprocess\|os\.system\|os\.popen'` → `CLEAN: No LLVM/subprocess calls found`

8. **大写注入的纵深防御**（reviewer 复核补充）：`10 20 00 01` → `FF 20 00 01`（大写）→ 解析器**跳过**该行、**不打印** `no match` 细节，仅 `N (40) != independent count (41)` → `exit 1`（设计内的兜底路径）；还原后 `41 patterns OK`。

7. **只读性**：运行前后 `git status --short` 仅显示 `?? tools/llvm/check_lit_bytes.py`（新增脚本本身），无其他变更

**新发现/坑**：
- FileCheck 模式 `{{[0-9a-f]+:}}` 在 Python regex 中需逐字符转义：`\{\{\[0-9a-f\]\+:\}\}`。首次用 `\{\{[0-9a-f]+:\}\}` 导致 `[0-9a-f]` 被解释为字符类、`+` 被解释为量词，正则完全不匹配 → N=0。修复后通过。
- `{{.*}}` 用 `\{\{.*?\}\}` 即可（lazy 匹配 `.*` 两个字面字符），无需 `\{\{\.\*\}\}`。
- 32/41 的 mask 为 `0xFF000000`（仅盖 op 字段），9/41 为 `0xFFFC0000`（orri/orrr 盖 op+ha）。因每条指令的 op 值唯一，每条 word 仍唯一命中，「无匹配」检查有效。

**遗留问题**：无

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-21，独立复跑）

审查对象：新建 `tools/llvm/check_lit_bytes.py`（未提交，sha256 `fa722692fdc8308d9d40ad25623433d5678f95d3eaaef9da215751a1adbf0a09`）。纯 Python + yaml，**未运行任何 LLVM 工具**。日志：`.work/log/llvm/LLVM-012t-review-*.log`。

#### 1. 默认运行（重跑）

```
$ python3 tools/llvm/check_lit_bytes.py
check_lit_bytes: 41 patterns OK
  (info: 32/41 masks cover op-field only)
EXIT=0
```
（直接 `echo $?` 取真实退出码，非管道码。）与预期 `41 patterns OK` / `exit 0` 一致。

#### 2. 反例门控（三组 + 大写纵深，均就地注入 + `git checkout` 还原）

注入前基线 `tests/lit/MC/Dadao/rrii_load.s` sha256 `d974fd8a045b701fc1d9a79d7b82d79435536fcfa5bb1b1af8e10aec810a4723`。

**(a) 错字节（小写）**：`10 20 00 01` → `ff 20 00 01`（`git diff` 确认目标文件确被改动，非空注入）
```
$ python3 tools/llvm/check_lit_bytes.py
  rrii_load.s:12: word=0xFF200001 — no match in opcodes.yaml
  N (40) != independent count (41)
EXIT_A=1
```
还原：`sha256sum -c` → `rrii_load.s: OK`；`git diff --name-only -- tests/lit/` 空；复跑 → `41 patterns OK`、`EXIT_RESTORE=0`。

**(b) 错 mnemonic**：字节正确，`ld.ub` → `ld.uw`
```
$ python3 tools/llvm/check_lit_bytes.py
  rrii_load.s:12: mnemonic 'ld.uw' != 'ld.ub' (insn=ld.ub-rd)
  N (40) != independent count (41)
EXIT_B=1
```
还原：sha256 OK；`git diff --name-only tests/lit/` 空；复跑 → `41 patterns OK`、`EXIT_RESTORE_B=0`。

**(c) 空 `OBJ:` 集**：`/tmp/opencode/LLVM-012t/empty-lit/dummy.s`（无 `OBJ:` 行）。因脚本 `LIT_DIR` 硬编码、无 CLI，用 `importlib` 载入**同一脚本**后仅覆写模块级 `LIT_DIR` 调 `main()`（未改仓库文件）：
```
$ python3 <import check_lit_bytes; m.LIT_DIR=<tmp>; m.main()>
check_lit_bytes: ERROR — N == 0 (no patterns extracted)
MAIN_RC=1   EXIT_C=1
```
附：空目录（无 `.s`）→ `check_lit_bytes: ERROR — no .s files found`，`EXIT_C2=1`。

**(额外) 大写 hex 注入（纵深防御）**：`10 20 00 01` → `FF 20 00 01`（解析正则只收小写 ⇒ 该行被**跳过**）：
```
$ python3 tools/llvm/check_lit_bytes.py
  N (40) != independent count (41)
EXIT_UPPER=1
```
**无** `no match` 细节行（如 P1/主会话所述，大写行由 N≠独立计数兜住）→ 纵深防御成立。还原：sha256 OK；复跑 `41 patterns OK`、`EXIT_RESTORE_UPPER=0`。

#### 3. 独立计数（宽松统计）

```
$ grep -h -o '#[[:space:]]*OBJ:' tests/lit/MC/Dadao/*.s | wc -l   → 41
$ grep -c 'OBJ:' tests/lit/MC/Dadao/*.s | awk -F: '{s+=$2} END{print s}' → 41
```
脚本的 `N`（匹配数）与独立宽松计数**均为 41**，相等。另用**独立第三方脚本** `/tmp/opencode/LLVM-012t/independent.py`（先将 `{{...}}` 替换为空格再按 token 解析，方法与脚本不同）复算：
```
independent literal count : 41
unique match              : 41
mnemonic consistent       : 41
mask==0xFF000000          : 32
problems                  : []
```
⇒ 41/41 唯一匹配、mnemonic 全一致、`32/41` op-only mask 独立复现。

#### 4. 约束核验（逐条）

| 验收标准 | 结果 |
|---|---|
| 1. 默认 `41 patterns OK`/`exit 0`；四类错误 `exit 1` | ✓ 逐条重跑（无匹配/错 mnemonic/N==0/N≠独立计数均 exit 1） |
| 2. 只读（不改 yaml/lit） | ✓ 运行前后 `git status --short` 恒为 `M 任务书` + `?? tools/llvm/check_lit_bytes.py`；`git diff --stat -- tests/lit/` 空；脚本无写模式 `open` |
| 3. 不调用 LLVM 工具 | ✓ `grep -n 'llvm\|subprocess\|os\.system\|os\.popen'` 无匹配（rc=1）；`grep -ni` 亦无；imports 仅 glob/os/re/sys/yaml |
| 4. 反例门控三组均 exit 1 + 还原 41 OK | ✓ 见 §2（含大写纵深） |
| 5. N == 独立计数 | ✓ 41 == 41（§3） |
| 6. 不重复 `test_encoding_oracle.py` 逻辑 | ✓ 后者用 `subprocess` 跑 `llvm-mc`、按格式公式算期望；本脚本只解析 lit 文本 + 查 `opcodes.yaml`，二者无共享代码/数据流 |
| 7. 完成区真实 stdout、逐条对齐 | ✓ 见 §5，数字全部对齐（仅 1 处证据标签瑕疵，非阻断） |

#### 5. 完成区核对

- 「41 patterns OK / exit 0」「32/41 masks cover op-field only」✓ 与我重跑逐字一致。
- (b) 错 mnemonic 输出 `mnemonic 'ld.uw' != 'ld.ub' (insn=ld.ub-rd)` + `N(40)!=41` ✓ 逐字一致。
- (c) 空 OBJ 集 `ERROR — N == 0` ✓ 一致。
- 独立计数 41 / N 41 / Match True ✓ 一致（我另用两种宽松方式 + 独立脚本复算）。
- 「grep CLEAN」✓ 一致（我实测无匹配，rc=1）。
- 只读性 ✓ 一致。
- **证据瑕疵（非阻断，供记录）**：完成区 §2(a) 写作注入 `→ FF 20 00 01`（大写），但所贴输出含 `no match` 细节行——**大写注入不会产生该细节行**（解析正则 `[0-9a-f]` 不收大写，该行被静默跳过，仅由 N≠计数兜住）。该输出实为**小写** `ff 20 00 01` 注入的真实结果（我已分别复现两者）。属完成区**注入字面量的笔误/标签错**（疑因消息内 `0xFF200001` 用大写 X 而误植），**非输出造假**、不影响功能结论；建议后续把 §2(a) 的 `FF` 更正为 `ff`，并补记大写注入的 N 计数兜底路径以与实现语义一致。

#### 判决

**Accepted**。验收命令块在本轮**独立重跑**下全部通过：默认 `41 patterns OK`/`exit 0`；三组反例（错字节/错 mnemonic/空 OBJ）均实打实 `exit 1`；大写 hex 注入由 N≠独立计数兜住 `exit 1`；每次注入均 `git checkout` 还原并 `sha256sum -c` 核对；独立宽松计数与独立第三方脚本均复现 41/41、mnemonic 全一致、32/41 op-only mask；脚本只读、无 LLVM/subprocess、逻辑与 `test_encoding_oracle.py` 不重复。完成区数字与真实输出逐条对齐，仅存上述**1 处非阻断的注入字面量笔误**。

#### 非阻断观察

1. 脚本**无 CLI 选项**（`LIT_DIR` 硬编码），故「空 `OBJ:` 集」反例须以 importlib 覆写模块变量验证（我据此完成）。若未来希望在别的 lit 目录/CI 复用，可考虑加可选 `--lit-dir`（非本任务要求，不阻断）。
2. 独立计数门控能捕获「解析器失配」（防空绿），但**无法捕获整行 `OBJ:` 被删除**（此时 N 与独立计数同时下降仍相等，脚本会报 `40 patterns OK`/exit 0）。此为设计内已知边界（任务 P2 只要求防空绿），如需硬下限可由 `opcodes.yaml` 推导，建议登记为可选增强。

