# INFRA-002t: 仓库与构建骨架 + `.work/` 约定

**模块**：infra
**依赖**：无

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：现有仓库结构（`AGENTS.md`、`README.md`、`.tao/`、`spec/`、`manifests/`、`docs/`、`verif/`）
- 输出：补齐的目录骨架、`.gitignore`、`.work/` 目录约定
- 约束：不写实现代码；只建立骨架与忽略规则；`.work/` 全部内容不入库

## 背景（完整）

### 目标

建立 DADAO-v5 可复现构建所需的仓库骨架与 `.work/` 一次性工作区约定，使后续 manifest / 脚本 / Makefile / 容器有确定的落点。

### 设计理由

- 0628 `docs/repository-layout.md` 明确：仓库永不跟踪上游源码树或构建产物；源码 checkout 由 `components.lock.toml` + 有序补丁序列完全复现。
- ADR-0002 要求所有一次性数据放在 `.work/` 下。
- 工程规则（`docs/greenfield-charter.md`）：保持生成的产物在仓库历史之外。

### 关键概念 / 数据

- `.work/` 子目录职责（0628 `docs/repository-layout.md`）：
  - `.work/source/`：上游组件 checkout（`git clone` + 补丁）。
  - `.work/build/`：树外构建目录。
  - `.work/install/`：宿主工具与产物。
  - `.work/sysroot/`：目标 sysroot。
  - `.work/logs/`：构建与测试日志。
- 0628 顶层骨架：`manifests/`（不可变输入）、`components/`（补丁序列 + 组件文档）、`contracts/`、`tests/`、`scripts/`、`containers/`、`.work/`。
- DADAO-v5 现状：已有 `.gitignore`（含 `.work/`）、`manifests/`、`spec/`、`docs/`、`verif/`、`.tao/`；`components/`、`scripts/`、`containers/` 尚未建立。

### 上游引用

- DADAO-0628 `docs/repository-layout.md`（完整转述见上）。
- DADAO-0628 `.gitignore`：忽略 `.work/`、`__pycache__/`、`*.py[cod]`、`*.swp`、`*.tmp`、`*.log`、`.DS_Store`、`.idea/`、`.vscode/`，以及 lit / gem5 运行产物（`tests/lit/**/Output/`、`m5out/`）。
- DADAO-0628 `docs/adr/0002-build-orchestration.md`：一次性数据集中在 `.work/`。
- DADAO-0628 `docs/greenfield-charter.md` 工程规则 4：生成的产物在仓库历史之外。

## 交付物

- `.gitignore`：在现有基础上补齐 0628 的忽略项（`.work/` 已有，补 `*.tmp`、`*.log`、lit / gem5 运行产物等，按 v5 目录实际调整）。
- `.work/` 目录约定：在仓库文档（如 `docs/repository-layout.md`，若新建）或 `README.md` 中记录 `source/` / `build/` / `install/` / `sysroot/` / `logs/` 职责；`.work/` 本身不建目录、不入库。
- `components/`：目录骨架（含 `.gitkeep`），用于放置补丁序列与组件文档。
- `scripts/`：目录骨架（含 `.gitkeep`），用于放置 Python 工具。
- `containers/`：目录骨架（含 `.gitkeep`），用于放置开发容器。
- `manifests/`：已存在，确认与骨架一致（无需新建）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- 目录差异：v5 用 `.tao/` 承载 agent 中间文件（0628 用 `code-agent/`）；v5 用 `verif/` 承载验证工具（0628 用 `tools/`）；v5 用 `spec/`（0628 用 wiki/contracts）。骨架任务不复制 0628 的 `contracts/`、`code-agent/` 目录。
- `.gitignore` 已存在，本任务为补齐/对齐，而非从零创建。

## 已知坑 / 结论

- 仓库永不跟踪上游源码树与构建产物；`.work/` 必须整体忽略。
- 空目录需 `.gitkeep` 才能在 git 中保留（`components/`、`scripts/`、`containers/`）。
- 0628 的 `m5out/`、`tests/lit/**/Output/` 等运行产物忽略项，v5 在对应目录建立后按需保留。

## 参考

- DADAO-0628：`.work/DADAO-0628/docs/repository-layout.md`
- DADAO-0628：`.work/DADAO-0628/.gitignore`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- DADAO-0628：`.work/DADAO-0628/docs/greenfield-charter.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `.gitignore` 覆盖 `.work/`、Python 缓存、编辑器临时文件与运行产物
2. `components/`、`scripts/`、`containers/` 骨架存在且可被 git 保留
3. `.work/` 子目录约定有明确文档记录
4. `git status` 在干净状态下不显示 `.work/` 内任何文件

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
