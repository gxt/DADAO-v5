# Repository Layout

DADAO-v5 仓库布局与一次性工作区（`.work/`）约定。

仓库**永不跟踪**上游源码树或构建产物；源码 checkout 由组件锁文件（`manifests/`）
加有序补丁序列完全复现（参考 ADR-0002：一次性数据集中在 `.work/`）。

## 纳入版本控制的目录

- `AGENTS.md` / `README.md`：项目规则与总览。
- `.tao/`：agent 交互目录（任务 / 知识 / 日志），详见 `.tao/README.md`。
- `manifests/`：不可变输入——规范与参考组件的锁文件（精确 commit）。
- `spec/`：原始规范文档（只读）。
- `components/`：有序补丁序列与组件专属文档。
- `scripts/`：确定性的 fetch / 准备 / 校验 / 状态工具（Python 标准库）。
- `containers/`：开发容器定义。
- `verif/`：验证工具与规范派生的机器可读数据（编码表、合法性规则）。
- `docs/`：仓库级文档（如本布局说明）。
- `tests/`：独立于组件单元测试的接口与执行测试（按需创建）。
- `sail/`：Sail 形式化规范（按需创建）。

## 一次性工作区 `.work/`（整体忽略，不入库）

所有一次性数据集中在 `.work/` 下，其子目录职责如下：

- `.work/source/`：上游组件工作树（从 `.cache/` 的 mirror 建，+ 有序补丁）；可随 `.work/` 重建。
- `.work/build/`：树外构建目录。
- `.work/install/`：宿主工具与产物。
- `.work/sysroot/`：目标 sysroot。
- `.work/logs/`：构建与测试日志。

`.work/` 整体由 `.gitignore` 忽略，**仓库不预先建立这些子目录、也不跟踪其内容**；
子目录在需要时由构建脚本创建。

## 持久对象库 `.cache/`（整体忽略，不入库）

`.cache/<name>.git` 存放上游组件的 **bare mirror（本地对象库）**，`.cache/refs/<id>.git` 存放参考仓库的 bare mirror，分别由 `scripts/fetch.py` / `scripts/fetch_refs.py`
首次 `git clone --mirror` 下载一次、以后只增量 `git fetch`。`.cache/` **持久保留**（`clean_work`
不删除），使 `.work/` 下的工作树即使被清空也能从本地 mirror 重建、无需重新下载大仓库。
