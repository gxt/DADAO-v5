# AGENTS.md — DADAO-v5 项目规则

> 全局规则（沟通约定、开发约定、八荣八耻、交互目录定位）由 `~/.config/opencode/AGENTS.md` 自动加载，本文件只写 DADAO-v5 特有内容。

## 基本规则（必须遵守）

- **工作范围**：仅在 DADAO-v5/ 目录内修改或创建文件，可读取其他目录。
- **git 操作**：仅涉及 DADAO-v5 子模块，不操作父仓库或其他子模块。如需父仓库配合，提示用户处理。
- **参考目录**：`DADAO-0628` 和 `DADAO` 作为工程经验参考，不复制其代码。两者 commit 已锁定在 `manifests/`。
- **提交确认**：所有提交必须先经用户确认。
- **操作前提问**：进行实际操作前先向用户提问，一次只问一个问题，根据回答追问直到完全理解需求。

## 进入项目

首次进入先读 `.tao/README.md`（角色/命令/流程/项目结构）与 `.tao/knowledge/MEMORY.md`（当前状态），再读 `.tao/tasks/` 下当前阶段任务。

## 核心原则

- **Spec-first**：所有编码/语义期望值来自 `.tao/knowledge/contract-*.md`，不从实现反推
- **Independent oracle**：测试向量不能从 LLVM 或 QEMU 生成，必须独立派生自 `spec/`
- **Component lock**：LLVM/QEMU/gem5 以 `manifests/` 中的精确 commit hash 锁定，不用 tag/branch

## 目录结构

```
DADAO-v5/
├── AGENTS.md              # 本文件
├── README.md              # 项目总览与阶段计划
├── .tao/                  # 交互目录（任务/知识/日志）
│   ├── tasks/PhaseN/      # 任务文件 Tnnn-描述.md
│   └── knowledge/         # MEMORY.md、contract-*.md、adr-*.md
├── docs/phases/           # 阶段执行计划
├── manifests/             # 锁文件（规范/参考组件）
├── spec/                  # 原始规范文档（只读）
└── verif/                 # 验证工具（金模型、编码表）
```

## 中间验证规范

每个子任务完成后，应立即运行验证：
1. **检查输出文件是否存在**：确认所有预期的输出文件已创建
2. **运行验证脚本**：如有验证脚本（如 `verif/validate_encoding.py`），立即运行
3. **检查引用一致性**：确认所有引用指向正确的文档（如 SimRISC-00/01/02/03/04，而非 DADAO-11）
4. **填写完成区**：记录验证结果后再提交

## 角色与流程

角色规则、任务编号（`Tnnn` 全局递增）、四态状态机与命令（`/plan` `/dispatch` `/complete` `/status`）见全局 `~/.config/opencode/` 与 `.tao/README.md`。工作仓库不含 agent 文件。
