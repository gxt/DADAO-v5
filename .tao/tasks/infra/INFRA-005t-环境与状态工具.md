# INFRA-005t: 环境与状态工具

**模块**：infra
**阶段**：0

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml`、`manifests/references.lock.toml`（`INFRA-003t` 产出）、宿主环境
- 输出：`scripts/doctor.py`、`scripts/status.py`、`scripts/clean_work.py`
- 约束：脚本只用 Python 标准库（`shutil` / `subprocess` / `tomllib` / `pathlib`）；`clean_work.py` 只删 `.work/`

## 背景（完整）

### 目标

提供宿主环境自检、组件/参考状态展示、以及安全清理 `.work/` 的三个辅助工具，支撑 `make doctor` / `make status` / `make clean-work`。

### 设计理由

- 可复现性要求在任何干净主机或开发容器上先做环境自检（`doctor`），并区分原生构建路径与容器构建路径。
- `status` 把 manifest 中锁定的 component/reference 与实际 checkout 对照，暴露 commit 漂移（DRIFT）。
- `clean_work.py` 以最小且防误删的方式移除一次性数据。

### 关键概念 / 数据

- `doctor.py`（0628 逻辑）：
  - required 工具：`git` / `make` / `cmake` / `python3`；native 工具：`ninja` / `clang`；另检测 `docker`。
  - 逐项打印 `OK`/`MISSING` 与版本首行。
  - required 缺失 → FAIL；native 缺失且无 docker → FAIL；否则按是否缺 native 报告 `native` 或 `container` 构建路径可用。
- `status.py`（0628 逻辑）：
  - 打印 Components：`name` / `enabled|disabled` / `commit`（未设显示 `UNSET`）。
  - 打印 References：对每个 reference 的 `path` 执行 `git rev-parse HEAD` 与 `git status --porcelain`，输出 `MATCH|DRIFT` 与 dirty 计数；路径不存在显示 `missing`。
- `clean_work.py`（0628 逻辑）：解析 `ROOT/.work`，断言其父目录为仓库根且名称为 `.work`，存在则 `shutil.rmtree`，否则提示不存在；防误删。

### 上游引用

- DADAO-0628 `scripts/doctor.py`（完整转述见上）。
- DADAO-0628 `scripts/status.py`（完整转述见上）。
- DADAO-0628 `scripts/clean_work.py`（完整转述见上）。
- DADAO-0628 `docs/repository-layout.md`：`.work/` 为一次性工作区，可整体清理。
- DADAO-0628 `code-agent/designs/0002-detailed-roadmap.md`：Phase 0 交付要求 `make doctor` / `make status` 可用。

## 交付物

- `scripts/doctor.py`：宿主/容器构建前提自检。
- `scripts/status.py`：component 与 reference 的锁定/漂移状态。
- `scripts/clean_work.py`：安全删除 `.work/`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- `status.py` 读取 `references.lock.toml`（v5 文件名），而 0628 读取 `references.toml`。
- reference 集合不同：v5 为 DADAO-0628 / DADAO，`path` 指向 `.work/DADAO-0628` 等实际位置。
- `doctor.py` 的工具清单可扩展（如 gem5 需要 `scons`，见 `INFRA-007t`），但保持"required / native / container"三段式判定。

## 已知坑 / 结论

- `doctor.py` 在原生缺 `ninja`/`clang` 时仍可通过，前提是有 docker（走容器构建路径）。
- `status.py` 对 reference 的 `path` 做 git 查询；路径错误会显示 `missing`（0628 指向其原作者的本地绝对路径，v5 必须改指向本项目内的真实位置）。
- `clean_work.py` 的路径断言（父目录 + 名称）是防误删的关键，不可省略。
- 三个脚本均须在 `python3 -m compileall scripts` 下无语法错误。

## 参考

- DADAO-0628：`.work/DADAO-0628/scripts/doctor.py`
- DADAO-0628：`.work/DADAO-0628/scripts/status.py`
- DADAO-0628：`.work/DADAO-0628/scripts/clean_work.py`
- DADAO-0628：`.work/DADAO-0628/docs/repository-layout.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `doctor.py` 正确判定 required/native 工具并报告可用的构建路径，退出码语义正确
2. `status.py` 输出 component 锁定状态与 reference 的 `MATCH`/`DRIFT`，无异常退出
3. `clean_work.py` 只删除 `.work/`，对异常路径拒绝执行
4. 三脚本通过 `python3 -m compileall scripts`

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
