# SPEC-051t: ADR-0013 增补 D8（cfx 系列汇编记法）

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：用户逐条确认（2026-09-29）
**状态**：待开始

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
