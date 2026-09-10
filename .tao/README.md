# .tao — DADAO-v5 交互目录

本目录承载任务、知识与协作记录，由架构师/工程师/审查者角色流程使用。
全局规则见 `~/.config/opencode/AGENTS.md`（自动加载）；角色 agent 定义与 model 见全局 `~/.config/opencode/agent/`。

## 核心原则

- **Spec-first**：所有编码/语义期望值来自 `.tao/knowledge/` 中的合约（`contract-*.md`），不从实现反推
- **Independent oracle**：测试向量不能从 LLVM 或 QEMU 生成，必须独立派生自 `spec/`
- **Component lock**：LLVM/QEMU/gem5 以精确 commit hash 锁定，不用 tag/branch
- **工作流**：冻结规范基线 → 提取合约 → 生成机器可读数据 → 锁定组件版本 → 逐任务推进实现 → 差分验证 → 沉淀知识库

## 角色分工

主会话（build agent）作为**协调者**，通过命令驱动流程：

| 角色 | 实现 | 工具/入口 |
| --- | --- | --- |
| **架构师** | `architect` subagent（只做规划） | `/plan` 规划；验收由主会话协调 |
| **工程师** | `engineer` subagent | 由 `/dispatch` 用 task 调起 |
| **审查者** | `reviewer` subagent | 由 `/complete` 用 task 调起 |

流程：`/plan` 规划（architect + reviewer 交叉审查）→ 审查任务文件 → `/dispatch` 下发执行 → `/complete` 审查+收尾（reviewer + architect 交叉复核）

### 命令总览

| 命令 | 类型 | 用途 |
| --- | --- | --- |
| `/plan` | 流程 | 调起架构师规划，拆解任务文件 |
| `/dispatch` | 流程 | 调起工程师执行任务 |
| `/complete` | 流程 | 调起审查者验收 + 知识沉淀 |
| `/translate` | 工具 | 英文 markdown 文档中英对照翻译 |

## 交互目录 $TAO_ROOT 定位

用 `git rev-parse --show-toplevel` 找到当前仓库根，交互目录即 `$REPO_ROOT/.tao/`。后续所有 `$TAO_ROOT` 均指该目录。

## 目录

- `tasks/<module>/` — 任务文件 `<PREFIX>-nnn<suffix>-描述.md`（按模块分子目录），状态机：`待开始` → `待验收` → `已验证`，审查失败 `待返工`
- `knowledge/` — 知识库：`MEMORY.md`（状态摘要）、`registry.md`（机器路由）、`changelog.md`（变更记录）、`contract-*.md`（归一化合约）、`adr-*.md`（架构决策）、`project_*.md`、`feedback_*.md`
- `logs/` — 命令输出日志（已被 `.tao/.gitignore` 忽略）

## 模块与任务编号

任务按模块组织：`tasks/<module>/<PREFIX>-nnn<suffix>-描述.md`，`nnn` 为模块内三位递增序号（跨后缀共享，前缀保证全局唯一）。

- `<suffix>`：`k`=启动（澄清目标+分解任务）、`t`=普通任务、`m`=里程碑标记（轻量文件，不走四态状态机，`**状态**` 固定写 `里程碑`）
- 任务文件以 `**模块**` / `**阶段**` 字段标注归属；`m` 文件以 `**目标**` / `**关联任务**` 标注

| 模块 | 前缀 | 覆盖 Phase | 交付物 |
| --- | --- | --- | --- |
| `spec` | `SPEC` | 0,1,4 | 规范锁定、ISA 合约、编码表、ABI/ELF/SBI 合约 |
| `llvm` | `LLVM` | 6,11 | LLVM MC + CodeGen |
| `qemu` | `QEMU` | 7 | QEMU |
| `gem5` | `GEM5` | 9 | gem5 |
| `sail` | `SAIL` | 10 | Sail |

> 基础设施模块（测试向量 Phase 2、黄金模型 Phase 3、组件基线 Phase 5、集成验证 Phase 8）名称待定。

## 项目结构（DADAO-v5 特有）

| 路径 | 用途 |
| --- | --- |
| `spec/` | 11 份原始规范文档（只读参考） |
| `manifests/` | 锁文件（规范/参考组件，精确 commit） |
| `docs/phases/` | 阶段执行计划（12 份） |
| `verif/` | 验证工具（金模型、编码表） |
| `.tao/knowledge/contract-isa.md` | ISA 归一化合约（SimRISC 0.5.3） |
| `.tao/knowledge/contract-authoring.md` | 合约编写规范 |
| `components/` `tests/` `scripts/` `sail/` | 后续阶段交付物（按需创建） |

## model

各角色的 agent 定义与 model 位于全局 opencode 配置（`~/.config/opencode/agent/`），工作仓库不包含 agent 文件。
