# ADR-0002: Manifest 驱动的构建编排

**状态**：Accepted
**日期**：2026-09-12
**关联**：ADR-0001（greenfield 重建）；`manifests/components.lock.toml`、`manifests/references.lock.toml`；`docs/repository-layout.md`；任务 `INFRA-002t`~`006t`、`INFRA-008t`

## Context（背景）

DADAO-v5 需要从锁定的上游组件（LLVM/QEMU/gem5）与参考仓库复现源码并完成构建，而仓库**永不跟踪**上游源码树或构建产物。因此需要：一个稳定的用户接口、一套可复现的版本来源机制，以及明确区分「一次性数据」与「需持久保留的数据」的边界。历史 meta-repository 采用 Make + Python 处理 manifest 的编排思路，v5 采纳其决策并针对大仓库体量做扩展。

## Decision（决策）

- **D1 稳定用户接口**：以 **Make** 作为统一入口（`fetch` / `fetch-refs` / `apply-series` / `prepare` / `build-*` / `clean-work` 等），实际逻辑委托给 `tools/infra/` 下的 **Python 标准库**脚本；不引入第三方 Python 依赖。
- **D2 一次性数据集中在 `.work/`**：上游工作树、树外构建目录、install、sysroot、构建/组件日志等所有可丢弃数据放在 `.work/` 下，整体由 `.gitignore` 忽略；仓库不预建、不跟踪其内容。agent 任务中间文件（含验证日志）按 `.tao/` 约定放 `.work/log/<模块>/`（`.work/` 整体 gitignore）。
- **D3 按完整 commit 锁定**：每个组件从 `manifests/components.lock.toml` 读取**完整 40 位 commit** 获取；tag/branch 不作为可复现基线。
- **D4 树形补丁集 + 一文件一补丁**（rev. 2026-09-23 改写，原为「单一有序补丁序列 + `git am`」）：每个组件的 DADAO 改动以 `components/<name>/patches/` 的**树形补丁集**表达——目录镜像上游源码树，一份补丁对应一个上游文件（文件名 = `<上游相对路径>.patch`，**无编号前缀**），`series` 为清单（一行一个，顺序按路径字典序）。统一用 **`git apply`** 应用（先 `git apply --check` 全量预检），**不保留作者与提交信息**；**不设** `newfiles/`、`fixups/` 等多层目录。新增文件同样以补丁表达（`new file mode` + 全文 `+` 行），且其补丁**必须是终态**（不得再有第二份补丁触及同一路径）。上述约束由 `tools/infra/check_patch_tree.py` 的断言在 `make check` 中机械校验；条文见 `docs/spec/component-patching.md`。
- **D5 v5 新增：持久 bare mirror + 可再生工作树**（避免重下大仓库）：
  - 上游组件 bare mirror 落在 `.cache/<name>.git`；参考仓库 bare mirror 落在 `.cache/refs/<id>.git`；两者均在 `.cache/` 下且整体 gitignore。
  - 首次 `git clone --mirror` 下载一次；已存在时只做增量 `git fetch --prune`（且当 mirror 已含 pin commit 时跳过 fetch）。
  - `.work/` 下的工作树从本地 mirror 建立/重建（本地硬链接，不额外占盘），删除 `.work/` 后可**离线重建**，无需重新下载大仓库。
  - `clean_work` 只清 `.work/`，**不删除 `.cache/`**。
- **D6 否决以下历史做法**：
  - 环境相关的 Git URL 重写；
  - 仅按可变分支选版本；
  - 未审查的独立 `fixups` 层；
  - 把上游仓库拷贝进 meta-repository；
  - 把脏的生成源码树当作权威实现。

## Rationale（理由）

- Make 在干净主机与开发容器上普遍可用，是稳定的薄接口；Python 标准库无需额外依赖，足以处理 manifest / 结构化数据，满足可复现与可移植要求。
- 完整 commit + 单一有序补丁序列，使源码 checkout 可由锁文件完全复现，避免 tag/branch 漂移与多层 fixups 导致来源不可审计。
- `.work/` 一次性化保证仓库历史不含生成物（对齐「生成的产物在仓库历史之外」的工程规则）。
- v5 扩展 `.cache/` 持久 mirror 是针对 LLVM/QEMU/gem5 体量大的现实：`.work/` 被清理后仍能从本地对象库重建工作树，避免重复下载；mirror 只增量更新，`clean_work` 不误删。
- 否决项均源自历史事故与教训：URL 重写破坏可复现性；可变分支无法锁定；未审查 fixups 绕过评审；拷贝上游仓库造成仓库膨胀与来源/许可混乱；脏生成树无法追溯，不能作为权威实现。

## Consequences（影响）

- **正面**：干净 checkout 上可一键准备与构建；版本来源精确、可审计；清空 `.work/` 不损失本地对象库，工作树重建无需网络。
- **约束**：enabled 组件必须有完整 commit 且补丁序列存在（由 `tools/infra/manifest_check.py` 校验）；补丁只能经 **`git apply`** 路径应用（rev. 2026-09-23）；`.cache/` 与 `.work/` 均须在 `.gitignore` 中整体忽略。
- **代价/负面**：`.cache/` 在本地磁盘上保留 bare mirror，占用空间，首次下载成本仍存在；`.work/` 与 `.cache/` 的清理职责必须严格区分（`clean_work` 不碰 `.cache/`）。

## 状态说明

**Accepted**（2026-09-13；rev. 2026-09-13 D2 措辞澄清、rev. 2026-09-17 日志目录迁至 `.work/log/`、**rev. 2026-09-23 D4 改写为树形补丁集 + `git apply`**，均见 `## 修订`）。决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策（**本 ADR 的 rev. 2026-09-23 属决策反转，经用户裁定就地修订，偏离已在修订条目中记录**）。评审确认项：D1–D6（Make+Python 标准库、`.work/` 一次性数据、完整 commit 锁定、补丁表达与序列、`.cache/` 持久 mirror+可再生工作树、否决 5 条历史做法）经用户逐条确认。

## 修订

**rev. 2026-09-13（用户决定）**：D2 措辞澄清——「日志」改为「构建/组件日志」；agent 任务中间文件（含验证日志）按 `.tao/` 约定放 `.work/log/<模块>/`（`.work/` 整体 gitignore）。D1、D3–D6 不变。

**rev. 2026-09-17（用户决定）**：D2 的日志留存位置由 `.tao/logs/` 迁至 **`.work/log/<模块>/<任务ID>-<命令名>.log`**（reviewer 重跑加 `-review-`；命令正常结束时用 `tee` 同时输出到终端和日志）。动机：全局 agent 规则的 `.tao/logs/` 约定已移除，改由本仓库自行规定；`.work/` 已由根 `.gitignore` 整体忽略，新位置天然不进 git，且与 D2「一次性数据集中在 `.work/`」一致。旧 `.tao/logs/` 已迁移（311 文件）并删除 `.tao/.gitignore`；历史记录中的旧路径不改写。D1、D3–D6 不变。

**rev. 2026-09-23（用户决定）**：**D4 决策变更**——补丁表达由「单一有序序列 + `git am`」改为「**树形补丁集（一文件一补丁）+ `git apply`**」：目录镜像上游源码树、文件名 = `<上游相对路径>.patch`（无编号前缀）、`series` 为清单（路径字典序）；应用改为 `git apply --check` 预检 + `git apply`，**不保留作者与提交信息**；**取消** `newfiles/`、`fixups/` 等多层目录；新增文件同样以补丁表达且**必须终态**；四条断言（每补丁单条目 / 目标路径全局唯一 / `series`↔树一致 / 应用后 tree 一致）由 `tools/infra/check_patch_tree.py` 接入 `make check`。动机：①`git am` 要求 mbox 且需保作者/信息，而该信息对本项目无价值；②一文件一补丁消除「多补丁改同一文件」，使顺序无关且可机械校验；③树形命名使目录即源码树、便于查阅。**规则偏离说明**：本条属**决策反转**，按 `adr-authoring.md`「决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策」，本应新增 ADR；经用户 2026-09-23 裁定**就地修订**，特此记录该偏离。D1–D3、D5、D6 不变。
