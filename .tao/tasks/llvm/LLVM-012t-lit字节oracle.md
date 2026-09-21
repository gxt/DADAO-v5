# LLVM-012t: lit 字节 oracle

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-011t`、`LLVM-008t`、`SPEC-003t`
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
