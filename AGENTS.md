# AGENTS.md — DADAO-v5 通用规则

## 作用域（必须遵守）

- **本文件只约束 DADAO-v5/ 目录内的工作。** 禁止读取、修改、创建该目录之外的任何文件。
- git 操作只涉及 DADAO-v5 子模块，不得对父仓库（gxtao）或其他子模块做任何操作。
- 如需父仓库配合（如更新子模块指针），应明确提示用户，由用户在父仓库 session 中处理。
- 不要读取 `~/.claude/CLAUDE.md`、`~/.config/opencode/AGENTS.md` 等家目录配置文件，只遵守本文件及 `project/rule-*.md` 的规则。
- **参考目录**：`DADAO-0628` 作为工程经验参考，不复制其代码。

## 进入项目

首次进入先读 `project/MEMORY.md` 了解当前状态，再读 `project/rule-*.md` 了解角色规则。

## 方法论概述

本仓库的本质是一套让 AI Agent 正确工作的约束系统，而非传统意义上的"项目"。核心认知——"**不是你写代码、Agent 帮你，而是 Agent 写代码、你写约束**。"

**角色分工**：

| 角色 | 做什么 |
|------|--------|
| **架构师** | 冻结规范、写合约、拆分任务、验收交付 |
| **子代理** | 读任务 → 实现 → 自审 → 提交 |
| **审查者** | 独立验证文件正确性 + 重跑验收命令 → 判决 |

**工作流**：冻结规范基线 → 提取合约 → 生成机器可读数据 → 锁定组件版本 → 逐任务推进实现 → 差分验证 → 沉淀知识库。

**核心原则**：
- **Spec-first**：所有编码/语义期望值来自 `project/contracts/`，不从实现反推
- **Independent oracle**：测试向量不能从 LLVM 或 QEMU 生成，必须独立派生自 wiki
- **Component lock**：LLVM/QEMU/gem5 以精确 commit hash 锁定，不用 tag/branch

## 角色规则引用

| 角色 | 规则文件 |
|------|---------|
| 架构师 | `project/rule-architect.md` |
| 子代理（执行 agent） | `project/rule-subagent.md` |
| 审查者 | `project/rule-reviewer.md` |

## Model 分配

为确保审查独立性，审查者必须使用与任务执行子代理不同的 model。

| 角色 | Model | 说明 |
|------|-------|------|
| 架构师 | mimo-v2.5-pro | 规划和验收，保持连续性 |
| 子代理 | DeepSeek V4 Pro | 任务实现 |
| 审查者 | mimo-v2.5-pro | 独立验证（与子代理不同 model） |
