# Phase 0：基础设施与规范锁定

## 目标

建立 DADAO-v5 仓库的可复现基础设施：目录结构、锁文件、工作规则。这是所有后续阶段的基石。

## 已完成

| 文件 | 说明 |
|------|------|
| `AGENTS.md` | 通用规则（作用域、命名约定、指令格式、核心原则） |
| `README.md` | 项目概览、版本号、11 阶段总览、依赖关系图 |
| `.gitignore` | 忽略 `.work/`、`__pycache__/` 等 |
| `manifests/spec.lock.toml` | 规范锁定（锁定 wiki commit 和版本号） |
| `project/MEMORY.md` | 跨会话快速定位、关键差异提示 |
| `project/rule-architect.md` | 架构师角色规范 |
| `project/rule-subagent.md` | 子代理角色规范 |
| `project/rule-reviewer.md` | 审查者角色规范 |
| `project/contracts/README.md` | 合约编写规范 |
| `project/phases/*.md` | 12 个阶段执行计划 |
| `wiki/*.md` | 11 份原始规范文档（只读） |

## 延后项

以下文件按需创建，在实际需要时再补充：

| 文件 | 何时创建 |
|------|----------|
| `Makefile` | Phase 5 组件基线时 |
| `manifests/components.lock.toml` | Phase 5 组件基线时 |
| `project/adr/*.md` | 有跨组件合约变更时 |
| `project/designs/*.md` | 有设计决策需要记录时 |
| `project/tasks/PhaseN/` | 各阶段开始时 |
| `project/knowledge/` | 有验证结论需要沉淀时 |
| `scripts/*.py` | 需要自动化工具时 |

## 验证标准

- [x] `manifests/spec.lock.toml` 存在且版本号正确
- [x] `AGENTS.md` 包含作用域、命名约定、核心原则
- [x] `project/rule-*.md` 三个角色规则文件齐全
- [x] `project/MEMORY.md` 包含项目概要和目录索引
- [x] `.gitignore` 存在

## 依赖关系

- 本阶段不依赖其他阶段
- 是后续所有阶段的前提条件
