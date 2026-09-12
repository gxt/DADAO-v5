# INFRA-001k: infra 模块启动

**模块**：infra
**项目里程碑**：M1
**依赖**：无
**状态**：已验证

## 问题根源

DADAO-v5 要从上游组件（LLVM/QEMU/gem5）的可复现基线构建全栈，但当前仓库缺少：组件锁、获取/打补丁工具、构建编排、开发容器。缺少这层基础设施，后续 llvm/qemu/gem5 模块的补丁无法可复现地应用到固定上游 commit，构建产物不可复现。DADAO-0628 的 Foundation（M0）正是为此。

## 目的

建立可复现构建基础设施：干净 checkout 能按精确 commit 获取上游组件、应用有序补丁、构建 LLVM MC / QEMU / gem5，并在干净主机或开发容器上运行仓库级检查（`make check` 通过）。

## 对照关系

- **借鉴**：DADAO-0628 Foundation（M0）与 ADR-0001（greenfield 重建）、ADR-0002（manifest 驱动编排）；v5 已采纳为自身 ADR（`.tao/knowledge/adr-0001-greenfield-rebuild.md`、`.tao/knowledge/adr-0002-build-orchestration.md`）。
- **差异**：v5 的 agent 中间文件集中 `.tao/`（0628 用 `code-agent/`），任务在 `.tao/tasks/<module>/`；组件 commit 待后续模块 ADR 确定（本阶段占位/禁用）；v5 **不使用 spec lock 文件**，规范版本表在 `README.md`。
- **拒绝的 legacy 行为**：环境相关 Git URL 重写、仅用可变分支选版本、未审查的 fixups 层、把上游仓库拷进元仓库、把脏的生成源码树当权威实现。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `INFRA-002t` | 仓库与构建骨架 + `.work/` 约定 | `.gitignore`、`.work/` 约定、目录骨架 | 无 |
| `INFRA-003t` | manifest 系统 + 组件锁 + 参考锁 | `components.lock.toml`、`references.lock.toml`、`manifest_check.py` | `INFRA-002t` |
| `INFRA-004t` | 组件获取与打补丁工具 | `fetch.py`、`apply_series.py`、`make_patch.py`、`fetch_refs.py` | `INFRA-003t` |
| `INFRA-005t` | 环境与状态工具 | `doctor.py`、`status.py`、`clean_work.py` | `INFRA-003t` |
| `INFRA-006t` | Makefile 编排 | `Makefile` | `INFRA-004t`、`INFRA-005t` |
| `INFRA-007t` | 开发容器 | `containers/dev/Dockerfile` + docker targets | `INFRA-006t` |
| `INFRA-008t` | 补 v5 自身 ADR（0001 greenfield / 0002 构建编排） | `.tao/knowledge/adr-0001-greenfield-rebuild.md`、`adr-0002-build-orchestration.md` | 无 |
| `INFRA-009m` | infra 里程碑 | 里程碑标记 | `INFRA-002t`~`INFRA-008t` |

- **依赖关系**：`002t → 003t → {004t, 005t} → 006t → 007t`；`008t`（补 v5 自身 ADR，独立）→ `009m` 汇总全部。
- **分解理由**：按「骨架 → 锁 → 工具 → 编排 → 容器」分层，每层可独立验收；共享工具（锁/获取/状态）无法拆到单个上游组件，故独立成 infra 模块。

## 说明

- 只规划不实现；组件 commit 待后续模块 ADR 确定。
- `.work/` 永不入 git；排除项必须显式失败，不能静默 no-op。
- 详细背景与 DADAO-0628 对照见各 `t` 任务文件；参考 `.work/DADAO-0628/code-agent/designs/0001-foundation-scope.md`、`0002-detailed-roadmap.md`、`docs/adr/0001-greenfield-rebuild.md`、`0002-build-orchestration.md`。
