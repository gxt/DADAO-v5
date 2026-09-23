# Repository Layout

DADAO-v5 仓库布局与一次性工作区（`.work/`）约定。

仓库**永不跟踪**上游源码树或构建产物；源码 checkout 由组件锁文件（`manifests/`）
加有序补丁序列完全复现（参考 v5 ADR-0002 `.tao/knowledge/adr-0002-build-orchestration.md`：一次性数据集中在 `.work/`）。

## 纳入版本控制的目录

- `AGENTS.md` / `README.md`：项目规则与总览。
- `.tao/`：agent 交互目录（任务 / 知识 / 日志），详见 `.tao/README.md`。
- `manifests/`：不可变输入——规范与参考组件的锁文件（精确 commit）。
- `spec/`：原始规范文档（只读）。
- `components/`：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁）+ 组件专属文档（`README.md`/`changelog.md`）。规范见 `docs/spec/component-patching.md`。
- `tools/<module>/`：各模块工具脚本（`tools/infra/` 含 fetch / 准备 / 校验 / 状态等，Python 标准库）。
- `containers/`：开发容器定义。
- `contracts/`：规范派生的机器可读数据（编码表、合法性规则、ABI）。
- `docs/`：仓库级文档（如本布局说明）。
- `tests/`：独立于组件单元测试的接口与执行测试（按需创建）。
- `sail/`：Sail 形式化规范（按需创建）。

## 一次性工作区 `.work/`（整体忽略，不入库）

所有一次性数据集中在 `.work/` 下，其子目录职责如下：

- `.work/source/`：上游组件工作树（从 `.cache/` 的 mirror 建，+ 有序补丁）；可随 `.work/` 重建。
- `.work/build/`：树外构建目录。
- `.work/install/`：宿主工具与产物。
- `.work/sysroot/`：目标 sysroot。
- `.work/log/`：构建与测试日志（agent 任务验证日志，`<任务ID>-<命令名>.log`）。

`.work/` 整体由 `.gitignore` 忽略，**仓库不预先建立这些子目录、也不跟踪其内容**；
子目录在需要时由构建脚本创建。

## 持久对象库 `.cache/`（整体忽略，不入库）

`.cache/<name>.git` 存放上游组件的 **bare mirror（本地对象库）**，`.cache/refs/<id>.git` 存放参考仓库的 bare mirror，分别由 `tools/infra/fetch.py` / `tools/infra/fetch_refs.py`
首次 `git clone --mirror` 下载一次、以后只增量 `git fetch`。`.cache/` **持久保留**（`clean_work`
不删除），使 `.work/` 下的工作树即使被清空也能从本地 mirror 重建、无需重新下载大仓库。

## 参考仓库检出 `.dadao/`（整体忽略，不入库）

`.dadao/<id>/` 存放**参考仓库的只读工作树**（`DADAO-0628`、`DADAO`），由
`tools/infra/fetch_refs.py` 按 `manifests/references.lock.toml` 的 `path` 从
`.cache/refs/<id>.git` 本地克隆并 detach 到锁定 `head`；`make fetch-refs` 幂等重建。

- 定位：**长期只读**的工程经验参考（上游已停止更新），**不随 `clean-work` 删除**，与一次性工作区 `.work/` 明确区分。
- 用途：查阅历史实现、架构与工程教训；**不复制其实现**，任务书引用时标注「内容溯源，非执行必需」。
- **路径变更记录（2026-09-23）**：参考仓库工作树由 `.work/DADAO-0628` / `.work/DADAO` 迁至
  `.dadao/DADAO-0628` / `.dadao/DADAO`（`manifests/references.lock.toml` 的 `path` 同步）；
  历史任务书中的旧路径已按新位置更新。
