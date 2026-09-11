# INFRA-001k: infra 模块启动（目标澄清与任务分解）

**模块**：infra
**阶段**：0

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`spec/` 规范锁定（SimRISC 0.5.3）、`docs/phases/Phase0-基础设施与规范锁定.md`、DADAO-0628 Phase 0（Foundation）资产
- 输出：infra 模块任务分解（`INFRA-002t` ~ `INFRA-007t`）与里程碑标记（`INFRA-008m`）
- 约束：只规划不实现；LLVM/QEMU/gem5 的精确 commit 在后续 llvm/qemu/gem5 模块的 ADR 中确定，本阶段仅占位/待定

## 背景（完整）

### 目标

为 DADAO-v5 建立可复现的构建基础设施：干净 checkout 能按精确 commit 获取上游组件、应用有序补丁、构建 LLVM MC / QEMU / gem5，并在干净主机或开发容器上运行仓库级检查。对应 DADAO-0628 的 **Phase 0（Foundation）**。

### 设计理由

- **Greenfield 重建（ADR-0001）**：从干净的上游组件 commit 实现 DADAO，仅复用 legacy 仓库的编排概念与已记录的工程教训，不 cherry-pick 任何 legacy 实现代码。
- **Manifest 驱动编排（ADR-0002）**：以 Make 作为稳定用户接口，用 Python 标准库脚本处理 manifest；所有一次性数据放在 `.work/` 下；每个组件按完整 commit 获取并应用**单一有序补丁序列**。拒绝的 legacy 行为：环境相关 Git URL 重写、仅用可变分支选版本、独立未审查的 `fixups` 层、把上游仓库拷进元仓库、把脏的生成源码树当作权威实现。
- 上游来源分两类：**component**（可构建的上游仓库，按 commit 锁定 + 补丁序列）与 **reference**（只读参考仓库，按 commit 锁定，只取架构/教训，不复制实现）。

### 关键概念 / 数据

- **component lock**：`manifests/components.lock.toml`，字段 `name` / `enabled` / `repository` / `commit` / `patch_series` / `role`。
- **reference lock**：`manifests/references.lock.toml`（0628 中为 `references.toml`），字段 `id` / `path` / `repository` / `head` / `dirty` / `purpose` / `reuse` / `selected_paths`。
- **patch series**：`components/<name>/patches/series`（有序清单，`#` 为注释），补丁本体 `components/<name>/patches/*.patch`。
- **`.work/` 布局**：`source/`（上游 checkout）、`build/`（树外构建）、`install/`（宿主工具/产物）、`sysroot/`（目标 sysroot）、`logs/`（构建/测试日志）。仓库永不跟踪上游源码树或构建产物。
- **Phase 0 退出标准**：干净 checkout 上 `make check` 通过。

### 上游引用

- DADAO-0628 `code-agent/designs/0001-foundation-scope.md`：M1（MC+QEMU）+ M2（Basic CodeGen）的 Foundation 范围；排除项必须产生显式、可断言的错误，不能是静默 no-op / 宿主 abort / timeout。
- DADAO-0628 `code-agent/designs/0002-detailed-roadmap.md`：Phase 0（Foundation，Complete）交付——仓库结构、manifest 系统、Makefile 编排；`make check` / `make doctor` / `make status` 可用；初始 spec lock；开发容器骨架；ADR-0001/0002 接受。退出：干净 checkout 上 `make check` 通过。
- DADAO-0628 `docs/development-roadmap.md`（M0 段）：M0 = Reproducible Foundation——仓库检查可在干净主机或开发容器运行；SPEC 与 component commit 锁定；独立指令向量有文档化 schema。
- DADAO-0628 `docs/adr/0001-greenfield-rebuild.md`、`docs/adr/0002-build-orchestration.md`：见「设计理由」。
- DADAO-0628 `docs/repository-layout.md`：仓库目录职责与 `.work/` 子目录划分。
- DADAO-0628 `docs/greenfield-charter.md`：工程规则——垂直切片、显式失败、commit 绑定、产物在仓库历史之外、跨组件合约需接口测试、不凭编译成功宣称完成。

## 任务分解

| 编号 | 任务 | 交付物 | 依赖 |
|------|------|--------|------|
| `INFRA-002t` | 仓库与构建骨架 + `.work/` 约定 | `.gitignore`、`.work/` 目录约定、`components/`/`scripts/`/`containers/`/`manifests/` 骨架 | — |
| `INFRA-003t` | manifest 系统 + 组件锁 + 参考锁 | `manifests/components.lock.toml`、`manifests/references.lock.toml`、`scripts/manifest_check.py` | `INFRA-002t` |
| `INFRA-004t` | 组件获取与打补丁工具 | `scripts/fetch.py`、`scripts/apply_series.py`、`scripts/make_patch.py` | `INFRA-003t` |
| `INFRA-005t` | 环境与状态工具 | `scripts/doctor.py`、`scripts/status.py`、`scripts/clean_work.py` | `INFRA-003t` |
| `INFRA-006t` | Makefile 编排 | `Makefile` | `INFRA-004t`、`INFRA-005t` |
| `INFRA-007t` | 开发容器 | `containers/dev/Dockerfile` + docker targets | `INFRA-006t` |
| `INFRA-008m` | infra 里程碑 | 里程碑标记 | `INFRA-002t` ~ `INFRA-007t` |

依赖链：`002t → 003t → {004t, 005t} → 006t → 007t`；`008m` 汇总全部。

## 交付物

- `.tao/tasks/infra/INFRA-001k-模块启动与任务分解.md`（本文件）
- `.tao/tasks/infra/INFRA-002t` ~ `INFRA-007t`、`INFRA-008m` 任务文件

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施与 ISA 版本无关）。基础设施机制（manifest / patch series / `.work/` / Make+Python）整体沿用 0628 的 Phase 0 设计。
- 目录归属差异：DADAO-v5 的 agent 中间文件集中在 `.tao/`（0628 用 `code-agent/`）；任务文件在 `.tao/tasks/<module>/`。
- 组件 commit 待定：LLVM/QEMU/gem5 的精确 commit 在后续 llvm/qemu/gem5 模块的 ADR 中确定，本阶段仅占位/禁用。
- `spec.lock.toml` schema 差异：v5 用 `[versions]` 与 `[foundation_included]` 表，0628 用扁平字段，`manifest_check.py` 需适配。

## 已知坑 / 结论

- Phase 0 是后续所有阶段的前提；`make check` 在干净 checkout 上通过是其退出标准。
- component 在 ADR 记录上游选择与精确 commit 之前保持 disabled；tag/branch 不作为可复现基线。
- `.work/` 必须被 git 忽略，仓库永不跟踪上游源码树与构建产物。
- 排除项必须产生显式、可断言的错误，不能是静默 no-op、宿主 abort 或 timeout。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0001-foundation-scope.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- DADAO-0628：`.work/DADAO-0628/docs/development-roadmap.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0001-greenfield-rebuild.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- DADAO-0628：`.work/DADAO-0628/docs/repository-layout.md`
- DADAO-0628：`.work/DADAO-0628/docs/greenfield-charter.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 明确 infra 模块目标与交付物（Phase 0 可复现基础设施）
2. 分解出 `INFRA-002t` ~ `INFRA-007t` 与 `INFRA-008m`，并标注依赖关系
3. 任务编号符合 `<PREFIX>-nnn<suffix>` 约定（模块内递增、跨后缀共享）
4. 规划内容不包含任何实现文件（Makefile / 脚本 / Dockerfile 等）

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
