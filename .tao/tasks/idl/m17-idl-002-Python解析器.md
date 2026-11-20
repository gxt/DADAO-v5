# m17-idl-002: IDL 解析器（Python，子集 → AST）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-001`（语法子集与宽度规则）
**可并行分片**：否
**预估**：3–5 天
**档位**：中改
**状态**：待开始

## 背景

`m17-idl-001` 会给出 `.idl` 实际使用的语法子集与出处。本任务只实现该子集，**不追求覆盖 652 行 treetop 的全语法**；语法真源仍是 UDB 的 IDL 语言规范（`spec/IDL-ISA语义描述语言与语义库.md`），本实现是它的**第二份实现**，靠 fixture 冻结行为防漂移。

## 目标

1. `tools/idl/`（或 `idl/pyparser/`）实现 parser：输入 `.idl`，输出 AST（节点类型与 `001` 的构造表一一对应）；
2. **全量解析 13 个 `.idl`**（12 册 + `lib/fp.idl`），operation 条数与 `render.py` 的 `# id:` 一致；
3. 新增 `make check-idl-parse`（L1 静态）：全量解析 + fixture 接受/拒绝集；
4. 不依赖 Ruby / gem / 网络。

## 验收（逐条贴真实 rc）

1. 263 条 operation 全量解析成功，条数由现场统计；
2. **拒绝集**：≥3 个语法错误样例必须报错（不是静默跳过）；
3. **漂移防护**：每个 operation 的构造签名冻结成 fixture，改动须显式更新；
4. **可达 FAIL ≥2 路**：① 删一个右括号 ⇒ 报错；② 改一条 operation 的 AST 节点 ⇒ fixture 红；
5. `render.py --check`、`check-idl-sync`、`check-knowledge-refs` 仍 rc=0（本任务不得影响渲染链路）。

## 约束

独立 `git worktree`；**不提交 git**；**不得改 `.idl` 与 `spec/`**；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
