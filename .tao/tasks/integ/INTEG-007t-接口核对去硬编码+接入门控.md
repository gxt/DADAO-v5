# INTEG-007t: `check_interface_alignment` 去硬编码 + 接入 `make check`

**模块**：integ（含仓库根 `Makefile`，因需接入门控）
**项目里程碑**：M1→M2
**依赖**：用户裁定（2026-09-30，方案 A）；`SPEC-057t`（暴露该缺陷）
**状态**：待开始

## 问题（两个）

### A. 4 个**硬编码计数**（`tools/integ/check_interface_alignment.py`）

| 行 | 常量 | 语义 |
|---|---|---|
| L626 | `EXPECTED_TOTAL = 253` | `opcodes.yaml` 条目总数 |
| L627 | `EXPECTED_M1 = 176` | M1 身份数 |
| L688 | `EXPECTED_LIT = 53` | lit `# OBJ:` pattern 数 |
| L707 | `EXPECTED_TRANS = 253` | QEMU `trans_*` 定义数（**注释自述「应等于 opcodes 条目数」**） |

**问题**：① 指令集增删需手改 2–3 个数字（`rela.si` 即实例）；② 违反脚本自述原则「期望值内联自 ADR/合约、不从实现反推」——`EXPECTED_TOTAL/M1` 实为**契约当前值的快照**，**不可证伪**；③ 与既有机制重复（`inventory.md` ↔ `validate_vectors.py`；`check_lit_bytes.py` 已报告 pattern 数）。

### B. **未接入任何门控**（更严重）

`make check` = `manifest-check + validate-vectors + check-spec-drift + check-patch-tree + check-asm-list + check_issues + compileall` —— **不含**它；`grep -rn check_interface_alignment Makefile tools/` **无调用方**。
⇒ 本次删 `rela.si` 时它 `80/80 → 78/80`，`make check` **两态皆 EXIT=0**，靠 reviewer 手工跑才发现。

## 修改内容（方案 A）

### 1. 去硬编码（改为**跨载体推导**，保持可证伪）

| 常量 | 改为 |
|---|---|
| `EXPECTED_TRANS` | `len(records)`（从契约推导） |
| `EXPECTED_LIT` | 与 `tools/llvm/check_lit_bytes.py` **报告**的 pattern 数交叉（或断言「与报告一致且 > 0」） |
| `EXPECTED_TOTAL` / `EXPECTED_M1` | 与 `tests/vectors/inventory.md`（**另一独立载体**）交叉：inv 的 M1 身份行数 == `opcodes.yaml` 的 M1 条数、inv 身份总数 == 契约条数 |

> 要求：断言仍**跨模块/跨载体**，不得退化为「契约 ↔ 自身」。

### 2. 接入 `make check`

- 新增 target `check-interface`（跑该脚本）
- `check:` 的依赖加入 `check-interface`
- 该脚本内部已调 `check_lit_bytes.py` + `check_qemu_trans.py --strict` ⇒ 接入后二者**一并成为门控**（**本任务顺带闭合**其「未接门控」缺口）
- 确认**不依赖 `.work`**（只读 `components/*/patches` + `tests/` + `contracts/`）⇒ 无「必须先 `make prepare`」前置；若实测有依赖，停下报告并登记

## 约束

- **不改**其余 76 项的判定语义；`1.ELF`/`2.ADR`/`3.Schema` 三类不动
- `expected_em = 0x0DA0`、`EXPECTED_E_FLAGS = 0x1` 系**设计常量**（源自 `ADR-0003`），**保持硬编码**
- 不改 `docs/integ-interface-alignment.md` 的**历史验收记录**（如需补「如何运行」可加）
- 反例注入须可复原
- 命令缺失 → 停下报告

## 验收标准

1. **无硬编码计数**：`grep -nE "253|176|254|177|= 53"` 在该脚本中**不再**作为期望常量出现（`grep` 证据）
2. **可证伪（关键）**：在 /tmp 副本中
   - (a) 从 `opcodes.yaml` 删 1 条 → 检查 **FAIL**（且**不是**「改常数就绿」）
   - (b) 从 `inventory.md` 删 1 个 M1 身份 → 检查 **FAIL**
   - (c) 删 1 个 lit `# OBJ:` pattern → 检查 **FAIL**
   - (d) 删 1 个 QEMU `trans_*` 定义 → 检查 **FAIL**
   四例均须给出真实 FAIL 输出；复原后 EXIT=0、无残留
3. **接入门控有效**：在 /tmp 副本中制造契约漂移（删 `opcodes.yaml` 1 条）→ **`make check` 变红**（EXIT≠0）；复原后 `make check` EXIT=0
4. 正常态：脚本 `80/80 EXIT=0`；`make check` EXIT=0；`repository checks: PASS`
5. 反例注入须可复原（`git status`/`git diff` 证据）

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
