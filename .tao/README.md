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

- `tasks/<module>/` — 任务文件 `<PREFIX>-nnn<suffix>-描述.md`（按模块分子目录），状态机按后缀：`k` 待开始→已验证；`t` 待开始→待验收→已验证（`待返工` 回退）；`m` 待开始→里程碑
- `knowledge/` — 知识库：`MEMORY.md`（状态摘要）、`registry.md`（机器路由）、`changelog.md`（变更记录）、`milestones.md`（项目里程碑路线图）、`contract-*.md`（归一化合约）、`adr-*.md`（架构决策）、`project_*.md`、`feedback_*.md`
- `logs/` — 命令输出日志（已被 `.tao/.gitignore` 忽略）

## 模块与任务编号

任务按模块组织：`tasks/<module>/<PREFIX>-nnn<suffix>-描述.md`，`nnn` 为模块内三位递增序号（跨后缀共享，前缀保证全局唯一）。

- `<suffix>`（谋事有因 / 做事有据 / 了事有果）：
  - `k`=启动（澄清目标+分解任务），状态 `待开始` → `已验证`（/plan 审查通过后，不单独验收）
  - `t`=普通任务，四态 `待开始` → `待验收` → `已验证`（`待返工` 回退）
  - `m`=里程碑标记（轻量），两态 `待开始` → `里程碑`
- 任务文件头部含 `**模块**` / `**项目里程碑**` / `**依赖**`；`k` 状态置顶，`m` 以 `**目标**` / `**关联任务**` 标注；项目里程碑（M1/M2…）见 `knowledge/milestones.md`

| 模块 | 前缀 | 交付物 |
| --- | --- | --- |
| `infra` | `INFRA` | 构建基础设施（组件锁、fetch/apply、Makefile、容器） |
| `spec` | `SPEC` | 规范锁定、ISA 合约、编码表、ABI/ELF/SBI 合约 |
| `testcases` | `TESTCASES` | 测试用例：向量（schema/validator）+ benchmark |
| `golden` | `GOLDEN` | Python 黄金模型 |
| `llvm` | `LLVM` | LLVM MC + CodeGen |
| `qemu` | `QEMU` | QEMU |
| `integ` | `INTEG` | 集成验证（E2E 套件与回归 + 跨模块接口对齐） |
| `gem5` | `GEM5` | gem5 |
| `sail` | `SAIL` | Sail |

> **数据/工具分离**：机器可读合约数据（`opcodes.yaml`/`legality_rules.yaml`/`abi.yaml`）放 `contracts/`；各模块工具脚本放 `tools/<module>/`。

## 项目结构（DADAO-v5 特有）

| 路径 | 用途 |
| --- | --- |
| `spec/` | 11 份原始规范文档（只读参考） |
| `manifests/` | 锁文件（规范/参考组件，精确 commit） |
| `contracts/` | 机器可读合约数据（编码表/ABI/合法性规则） |
| `tools/<module>/` | 各模块工具脚本（infra/spec/llvm/qemu/testcases） |
| `.tao/knowledge/contract-isa.md` | ISA 归一化合约（SimRISC 0.5.3） |
| `.tao/knowledge/contract-authoring.md` | 合约编写规范 |
| `components/` `tests/` `sail/` | 后续交付物（按需创建） |

## model

各角色的 agent 定义与 model 位于全局 opencode 配置（`~/.config/opencode/agent/`），工作仓库不包含 agent 文件。
