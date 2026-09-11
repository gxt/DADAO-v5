# ADR 编写规范与模板

ADR（Architecture Decision Record）记录影响架构、难以逆转的决策。任务书涉及 ADR 时，**以本文件为格式依据**，不依赖外部参考仓库（如 DADAO-0628）。

## 何时写 ADR

- 选定外部组件基线（LLVM / QEMU / gem5 的上游版本与精确 commit）
- 冻结跨模块契约（Test Machine、Object ABI、ELF 等）
- 其它难以逆转、影响多个模块的架构决策

## 落点与命名

- 落在 `.tao/knowledge/adr-<nnnn>-<slug>.md`（如 `.tao/knowledge/adr-0004-test-machine.md`）
- `<nnnn>` 四位递增，与任务编号解耦
- 关联任务在「关联」字段标注

## 模板

```markdown
# ADR-<nnnn>: <标题>

**状态**：Candidate
**日期**：<YYYY-MM-DD>
**关联**：<相关 ADR / 任务编号 / spec 章节>

## Context（背景）

<问题、约束、依赖；引用 spec 章节而非实现代码>

## Decision（决策）

<做出的决定，逐条列出（D1、D2…），可含明确的无 spec 依据项>

## Rationale（理由）

<为何这样决定；与备选方案的对比>

## Consequences（影响）

<正面/负面后果、后续约束>

## 状态说明

<从 Candidate 到 Accepted 的评审记录/条件>
```

## 流程

- 先置 `Candidate` 提交；评审通过后由主会话置 `Accepted`
- 决策变更时**新增 ADR 或标注 `Superseded`**，不直接改写已 `Accepted` 的决策
- ADR 内容以 v5 自身 spec/合约为准；对 0628 等外部仓库仅作**内容溯源**，不照抄其决策
