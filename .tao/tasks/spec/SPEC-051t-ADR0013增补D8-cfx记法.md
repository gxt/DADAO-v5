# SPEC-051t: ADR-0013 增补 D8（cfx 系列汇编记法）

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：用户逐条确认（2026-09-29）
**状态**：已验证

## 背景

`ADR-0013`（Accepted，D1–D7）冻结了 DADAO 汇编语法，其引用的 `docs/spec/assembly-language.md` v1.1 §151–156 记录了 cfx 系列的书写（`cfxN`、`cgN`）。用户裁定修订 cfx 记法，并**授权就地增补** D8（不改动 D1–D7）。

## 修改内容（仅 `.tao/knowledge/adr-0013-assembly-syntax.md`）

1. 在 `## Decision（决策）` 末尾（D7 之后、`## Rationale` 之前）**新增 D8**，内容为下（逐字采用）：
2. 更新文件头 `**关联**` 字段，追加本次修订说明与相关任务（`SPEC-051t`…`SPEC-054t`）。
3. 在 `## 状态说明` 追加 D8 的授权记录。

### D8 正文（逐字插入）

```markdown
### D8：cfx 系列汇编记法（2026-09-29 用户逐条确认，授权就地增补）

**引用**：`docs/spec/assembly-language.md` §151–156、`contracts/opcodes.yaml`（cfx 家族）、`SPEC-052t`–`SPEC-054t`

- **D8.1（cfx 编号占位）**：核芯功能扩展编号字段（`cfxha`，bits[23:18]）在汇编书写中的**字段占位**记法为 **`cfxHA`**（取代 v1.1 的 `cfxN`）；其**具体写法**为编号（如 `cfx63`）或名称别名 `cfx_<cfxname>`。
- **D8.2（`cfx2rd`/`cfx2rc` 操作数）**：`crrr` 格式 `cfx2rd`/`cfx2rc` 的三个寄存器操作数写作 **`cgHB, rcHC, rdHD`**（对应字段 `cghb`/`rchc`/`rdhd`），取代原 `hb`/`hc`/`hd`。
- **D8.3（别名）**：`cfx_<cfxname>`（如 `cfx_power`、`cfx_umon`）是 `cfxHA` 位置具体编号的**宏别名**，汇编器等价替换。
- **D8.4（字段重命名）**：`contracts/opcodes.yaml`（生成源 `tools/spec/generate_opcodes.py`）字段重命名：`cfxcode→cfxha`、`hb→cghb`、`hc→rchc`、`hd→rdhd`。
- **D8.5（同步）**：`docs/spec/assembly-language.md` §151–156、`docs/assembly-list.md` 及各 `spec/SimRISC-*.md` 内嵌速查表同步修订/重生成。

**备选（否决）**：
- R1：保留 `cfxN` → 与既有 `<bank>H<slot>` 占位约定（`rdHA`、`rbHB`）不一致；否决。
- R2：保留 `hb`/`hc`/`hd` 字段名 → 缺寄存器组前缀，占位无法表达 `cg`/`rc` 归属；否决。
- R3：新建 `ADR-0015` → 用户裁定就地增补（D1–D7 未覆盖 cfx，D8 属新增决策而非改写）；否决。
```

### 状态说明追加句

```markdown
- **2026-09-29 增补 D8**：cfx 系列汇编记法（D8.1–D8.5）经用户逐条确认后**授权就地增补**；D1–D7 未改动。
```

## 约束

- **只改 `.tao/knowledge/adr-0013-assembly-syntax.md`**；不改其它文件
- **不得改动 D1–D7 的既有正文**（只追加）
- 逐字插入上述 D8 正文

## 验收标准

1. D8 已插入 Decision 段末尾；D1–D7 正文**逐字未变**（给出 diff 证据）
2. `**关联**` 与 `## 状态说明` 已更新
3. `git status` 仅该文件（+任务文件）
4. 语义/格式与 `adr-authoring.md` 模板一致

## 完成区
**测试结果**：N/A（文档性任务，无代码测试）
**修改文件**：`.tao/knowledge/adr-0013-assembly-syntax.md`（唯一改动文件）
**验收结果**：
1. **D8 插入位置**：D7 之后（L117）、`## Rationale` 之前（L133），L118–L131 为 D8 正文
2. **D1–D7 逐字未变**：`git diff` 仅显示三处增量（关联字段追加、D8 插入、状态说明追加），D1–D7 原有正文零改动（见上方完整 diff）
3. **关联字段**：已追加 `**2026-09-29 增补 D8**（cfx 系列汇编记法，关联 `SPEC-051t`–`SPEC-054t`）`
4. **状态说明**：已追加 D8 授权记录行
5. **git status**：仅 `M .tao/knowledge/adr-0013-assembly-syntax.md`（+任务文件）
6. **格式**：D8 结构（标题/引用/决策条目/备选否决）与 D1–D7 风格一致，符合 `adr-authoring.md` 模板
**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`.tao/knowledge/adr-0013-assembly-syntax.md` 三处改动（关联字段、D8 插入、状态说明）

**逐行审查**：

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | D8 标题行逐字一致 | ✅ | L118 = `### D8：cfx 系列汇编记法（2026-09-29 用户逐条确认，授权就地增补）`，与任务书一致 |
| 2 | D8 引用行逐字一致 | ✅ | L120 完全匹配任务书 |
| 3 | D8.1–D8.5 逐字一致 | ✅ | L122–L126 逐行与任务书对齐，含 `cfxHA`、`cgHB, rcHC, rdHD`、`cfx_<cfxname>`、`cfxcode→cfxha` 等关键术语 |
| 4 | 否决方案 R1–R3 逐字一致 | ✅ | L129–L131 逐行匹配 |
| 5 | D8 插入位置正确 | ✅ | D7 R2 (L116) → 空行 → D8 (L118) → 空行 → Rationale (L133) |
| 6 | D1–D7 正文未改动 | ✅ | `git diff` 仅显示三处增量变更，D1–D7 区域（L20–L116）无 diff |
| 7 | 关联字段已更新 | ✅ | L5 追加了 D8 修订说明与 SPEC-051t–054t 关联 |
| 8 | 状态说明已追加 | ✅ | L162 追加了 D8 授权记录 |
| 9 | git status 仅目标文件 | ✅ | `M .tao/knowledge/adr-0013-assembly-syntax.md` |
| 10 | 格式与 adr-authoring.md 一致 | ✅ | D8 结构（标题/引用/决策条/备选否决）与 D1–D7 风格一致 |

**Finding 处置**：无 finding，全部通过。

**判决**：✅ 通过，可标 `待验收`。

#### 第 1 轮 reviewer 验收

**审查对象**：`.tao/knowledge/adr-0013-assembly-syntax.md`（工作树 vs `git show HEAD:`）

**重跑记录（reviewer 亲自执行，非转述）**

1. 改动范围：

```
$ git status --porcelain
 M .tao/knowledge/adr-0013-assembly-syntax.md
 M ".tao/tasks/spec/SPEC-051t-ADR0013\345\242\236\350\241\245D8-cfx\350\256\260\346\263\225.md"
$ git ls-files --others --exclude-standard   # 无未跟踪文件（空）
```

2. 逐字对比 D1–D7 正文（HEAD L7–117 vs 工作树 L7–117）：

```
$ diff <(sed -n '7,117p' HEAD_adr.md) <(sed -n '7,117p' adr-0013-assembly-syntax.md)
IDENTICAL: HEAD L7-117 == WT L7-117 (D1-D7 body)
```

3. 逐字对比 D8 之后的既有正文（HEAD L118–146 = Rationale/Consequences/状态说明 vs 工作树 L133–161）：

```
$ diff <(sed -n '118,146p' HEAD_adr.md) <(sed -n '133,161p' adr-0013-assembly-syntax.md)
IDENTICAL tail (Rationale+Consequences+状态说明)
$ sed -n '162p' adr-0013-assembly-syntax.md   # 工作树唯一新增行
- **2026-09-29 增补 D8**：cfx 系列汇编记法（D8.1–D8.5）经用户逐条确认后**授权就地增补**；D1–D7 未改动。
```

4. D8 段（工作树 L118–131）与任务书逐字对比：

```
$ diff <(sed -n '21,34p' 任务书) <(sed -n '118,131p' adr文件)
IDENTICAL: D8 block == task book spec (L21-34)
$ diff <(sed -n '40p' 任务书) <(sed -n '162p' adr文件)
IDENTICAL: 状态说明追加句
```

5. 完整 diff（3 个 hunk，无其它）：

```
@@ -2,7 +2,7 @@  → 仅 **关联** 行追加
@@ -115,6 +115,21 @@ → 仅插入 D8 段（15 行）
@@ -144,3 +144,4 @@ → 仅追加状态说明末行
```

**约束核验（逐条）**

| # | 任务约束/验收项 | 结果 | reviewer 证据 |
|---|---|---|---|
| 1 | 只改 ADR（+任务文件） | ✅ | `git status --porcelain` 仅这两项；无未跟踪文件 |
| 2 | D1–D7 正文逐字未变 | ✅ | 范围 diff 完全一致（重跑记录 2）；`git diff` 无 D1–D7 区域 hunk |
| 3 | D8 全部内容正确 | ✅ | 与任务书 L21–34 逐字相同；D8.1 `cfxHA` / D8.2 `cgHB, rcHC, rdHD` / D8.3 `cfx_<cfxname>` 宏别名 / D8.4 `cfxcode→cfxha`、`hb→cghb`、`hc→rchc`、`hd→rdhd` / D8.5 同步，均齐备 |
| 3b | 备选 R1–R3 | ✅ | 与任务书 L32–34 一致（保留 `cfxN`、保留旧字段名、新建 ADR-0015 三案均否决） |
| 3c | 引用可定位 | ✅ | `docs/spec/assembly-language.md` §151–156 实存；`contracts/opcodes.yaml` 实存且含 `cfxcode`/`hb`/`hc`/`hd`（L1996–2008，待后续任务重命名，方向与 D8.4 相符）；`tools/spec/generate_opcodes.py` 实存 |
| 4 | 插入位置（D7 之后、Rationale 之前） | ✅ | D7 结束于 L116，空行 L117，D8 = L118–132，`## Rationale` = L133 |
| 5 | `**关联**` 已更新 | ✅ | L5 追加 `**2026-09-29 增补 D8**（…关联 SPEC-051t–SPEC-054t）` |
| 5b | `## 状态说明` 已更新 | ✅ | L162 新增 D8 授权记录行 |
| 5c | 状态仍为 `Accepted` | ✅ | L3 = `**状态**：Accepted`（未改动） |
| 6 | 格式符合 `adr-authoring.md` 模板 | ✅ | 文件含 状态/日期/关联 + Context/Decision/Rationale/Consequences/状态说明；D8 标题、**引用**、决策条目、备选否决结构与 D1–D7 同构 |
| 7 | Rationale「上述 7 条决策」 | 见下 | 非否决项 |

**关于要点 7 的判断**

`## Rationale`（L135）仍写「上述 7 条决策的核心权衡原则」，D8 引入后决策总数实为 8 条，字面计数已过时。判断：**属可选润色，非必须修正**——理由：（a）该句枚举的 5 条原则（统一记法/显式标记/对称性/确定性/就近）是 D1–D7 的取舍原则，D8 未新增此类原则；（b）该行属既有已冻结文本，按本任务「只追加、不改 D1–D7 正文」约束，本轮不宜改动；（c）如后续获授权，建议将「上述 7 条决策」改为「D1–D7 的核心权衡原则」以消除计数歧义。**不以其是否修正而否决。**

**未验证/采信项**

- D8 与「用户逐条确认的决策」的一致性：reviewer 无法访问用户会话原文，以任务书（声明为「用户逐条确认（2026-09-29）」）为确认记录来源进行比对；已确认 ADR 内容与任务书逐字一致。
- opcodes.yaml 的字段重命名（D8.4）与 assembly-language.md 修订（D8.5）**不在本任务范围**（由 SPEC-052t–054t 落地），本轮不核。

**判决**：**Accepted**

验收命令块三要素（改动范围、D1–D7 逐字未变、D8 逐字正确且位置正确）在 reviewer 独立重跑下全部通过，硬约束无违反。要点 7 的 Rationale 计数漂移为可选润色，不构成否决。提请主会话将任务状态置为 `已验证`，并由架构师/用户终审。
