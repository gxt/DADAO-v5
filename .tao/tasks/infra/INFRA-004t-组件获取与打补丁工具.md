# INFRA-004t: 组件获取与打补丁工具

**模块**：infra
**项目里程碑**：M1
**依赖**：`INFRA-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`manifests/components.lock.toml` 与 `manifests/references.lock.toml`（`INFRA-003t` 产出）、`components/<name>/patches/series` 与补丁本体
- 输出：`scripts/fetch.py`、`scripts/apply_series.py`、`scripts/make_patch.py`、`scripts/fetch_refs.py`
- 约束：所有上游 checkout 落在 `.work/source/<name>/`；补丁只从 `components/<name>/patches/` 读取；不复制 0.4.1 的补丁正文

## 背景（完整）

### 目标

按 manifest 精确 commit 获取上游组件源码，并将 DADAO 的有序补丁序列应用到 checkout 上；同时提供把本地开发工作树导出为补丁序列的工具。

### 设计理由

- ADR-0002：每个组件按完整 commit 获取并应用**单一有序补丁序列**；`git am` 是唯一打补丁路径。
- 可复现性：`.work/source/<name>` 完全可由 `components.lock.toml` + 补丁序列重建，不把上游源码树或产物纳入仓库。

### 关键概念 / 数据

- `fetch.py`（0628 逻辑，完整转述）：
  - 读取 `components.lock.toml`，取 `enabled` 组件；无 enabled 组件时打印提示并退出 0。
  - `source_root = .work/source`；目标 `source_root/<name>`。
  - **全新 clone**：`git clone --filter=blob:none --no-checkout <repo> <target>`，随后 `git fetch --no-tags origin <commit>` + `git checkout --detach <commit>`。
  - **已存在**：先 `git status --porcelain`，脏则报错拒覆盖；`git fetch --no-tags origin <commit>`；若 `HEAD == commit` 跳过；若 commit 是 HEAD 的祖先（说明已打过补丁）则**保持不动**；否则 `git checkout --detach <commit>`。
- `apply_series.py`（0628 逻辑，完整转述）：
  - 对每个 enabled 组件，要求 `source/.git` 存在（否则提示先 `make fetch`）；要求 `HEAD == component["commit"]`（否则报错）。
  - 读取 `components/<name>/patches/series`，逐行（跳过空行与 `#` 注释）用 `git -C <source> am <patch>` 应用；空序列打印提示。
- `make_patch.py`（v5 新增，0628 无此脚本）：从 `.work/source/<name>` 的工作树相对 base commit 生成有序补丁，输出到 `components/<name>/patches/` 并维护 `series`。0628 的补丁靠手动 `git format-patch` 产出，v5 将其工具化（参考 0628 的补丁序列**格式**，不复制其脚本或补丁正文）。

### 上游引用

- DADAO-0628 `scripts/fetch.py`（完整转述见上；含其对 `--no-checkout` clone 与"已打补丁祖先"两处关键修复的注释）。
- DADAO-0628 `scripts/apply_series.py`（完整转述见上）。
- DADAO-0628 `components/llvm/README.md` 与 `components/llvm/patches/series`：补丁序列的组织方式（`series` 有序清单 + 编号 `.patch` 文件；补丁名带任务号）。
- DADAO-0628 `docs/development-roadmap.md`（`scripts/fetch.py silently discarded applied patches` 段）：fetch 曾静默丢弃已应用补丁的事故记录。
- DADAO-0628 `docs/adr/0002-build-orchestration.md`：获取与补丁编排。

## 交付物

- `scripts/fetch.py`：按 commit 获取 enabled 组件到 `.work/source/<name>`。
- `scripts/apply_series.py`：将有序补丁序列 `git am` 到 checkout。
- `scripts/make_patch.py`：从工作树生成/维护补丁序列（v5 新增）。
- `scripts/fetch_refs.py`：按 `references.lock.toml` 获取只读参考仓库到其 `path`，供任务 `## 参考` 定位；DADAO-0628 直接用已有 `.work/DADAO-0628`（只做 commit 检查，不重新拉取），DADAO 从 `https://github.com/gxt/DADAO.git` 取到 `.work/DADAO`；已存在且 commit 匹配则跳过。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- 无 ISA 相关差异（基础设施，与 ISA 版本无关）。
- `make_patch.py` 为 v5 新增：0628 `scripts/` 下无此脚本，补丁靠手工 `git format-patch`。本任务只参考 0628 的补丁序列格式，不复制其补丁正文。
- 组件 commit 待定：`fetch.py` 在组件 `enabled = false` 时应与 0628 一样打印"no components enabled"并正常退出。

## 已知坑 / 结论

- **`--no-checkout` clone 的 HEAD 指向远端默认分支 tip，而非 pin commit**：新 clone 必须直接 `fetch <commit>` + `checkout --detach <commit>`，否则工作树为空、HEAD 停在错误 commit（0628 在启用 musl 时发现）。
- **重跑 `make fetch` 会静默丢弃已应用补丁**：当 HEAD 已含 pin commit 作为祖先（即补丁已 `git am` 在顶部）且工作树干净时，`checkout --detach <pin>` 会破坏性地丢弃全部补丁 commit。0628 在 2026-07-15/16 真实发生（重跑 fetch 抹掉 `.work/source/qemu` 的补丁，靠 reflog 恢复）。必须检测"已打补丁"并跳过。
- 脏工作树必须拒绝覆盖，避免丢失未提交改动。
- `apply_series.py` 严格要求 `HEAD == base commit`，防止在错误基线上叠补丁。
- 补丁应用统一用 `git am`（保留作者/提交信息），不用 `patch`/`git apply`。

## 参考

- DADAO-0628：`.work/DADAO-0628/scripts/fetch.py`
- DADAO-0628：`.work/DADAO-0628/scripts/apply_series.py`
- DADAO-0628：`.work/DADAO-0628/components/llvm/README.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- DADAO-0628：`.work/DADAO-0628/docs/development-roadmap.md`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0002-build-orchestration.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `fetch.py` 能按 manifest commit 获取组件；对已打补丁的 checkout 重跑不丢补丁；脏树拒绝覆盖
2. `apply_series.py` 能按 `series` 顺序 `git am` 应用补丁，并在 HEAD 非 base commit 时明确报错
3. `make_patch.py` 能从工作树生成补丁并维护 `series`（新工具，含基本自测）
4. 三脚本通过 `python3 -m compileall scripts`（`make fetch`/`make apply-series` 的集成由 `INFRA-006t` 验收）
5. `fetch_refs.py` 能按 `references.lock.toml` 将参考仓库取到 `path`；已存在且 commit 匹配时跳过

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
