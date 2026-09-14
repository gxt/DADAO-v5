# LLVM-012t: lit 字节 oracle

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-009t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

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

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-022a-qfc-lit-oracle.md`（lit 部分）
- DADAO-0628：`scripts/check_lit_bytes.py`（形态参考，禁止复制正文）

## 交付物

- `tools/llvm/check_lit_bytes.py`：lit `# OBJ:` 字节 ↔ `contracts/opcodes.yaml` 独立 oracle
- 完成区附真实 stdout

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **编码表路径**：`contracts/opcodes.yaml` → `contracts/opcodes.yaml`。
2. **脚本目录**：`verif/` → `tools/llvm/`。
3. **lit 文件形态**：`tests/lit/MC/Dadao/*.s` 由 `LLVM-009t` 按 0.5.3 助记符重写并内建 `{{.*}}`；本任务**只做 oracle 校验，不改 lit 文件**。

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

1. `python3 tools/llvm/check_lit_bytes.py` 输出 `N patterns OK`、exit 0；若存在无匹配字节则 exit 1
2. 脚本不修改任何 yaml/lit 文件（只读）
3. 不含对 LLVM 工具的调用（grep 确认）
4. 完成区粘贴真实 stdout，不转述

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
