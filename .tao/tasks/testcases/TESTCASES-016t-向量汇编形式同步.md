# TESTCASES-016t: 同步测试向量汇编形式

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：`SPEC-036t`（语法定义已更新——汇编文本同步只需语法定义，不依赖 MC 实现）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
