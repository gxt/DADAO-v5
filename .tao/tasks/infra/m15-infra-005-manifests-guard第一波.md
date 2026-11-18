# m15-infra-005: `.manifests.toml` 目录防护第一波（spec / .tao / .tao/knowledge）

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-infra-003`（盘点结论：6 目录无白名单、`spec` 新增册逃锁）
**可并行分片**：否（跨 spec/.tao/tools/docs）
**预估**：3–4 h
**档位**：中改
**状态**：待开始

## 背景与裁定（用户 2026-11-18）

`refs` 事件暴露：目录与文件没有「只能放什么」的机械约束，新增逃逸、删除无声。用户裁定分步改造，**第一批** = `spec/`、`.tao/`、`.tao/knowledge`。

用户原话要点（逐条落纸）：
1. 第一批三目录；`.tao/.manifests.toml` **只管顶层**，另**支持子目录递归选项**（后续模块如 `patches` 需要）。
2. 清单文件名统一 **`.manifests.toml`**（带点）。
3. `spec/` **只允许 spec 模块任务修改，且需裁定**；`owner` 只作声明、门控只打印不判红。
4. `manifests/spec-readonly.lock.toml` 内容迁入 `spec/.manifests.toml`，**注释全部删除**，只留文件名 + sha256（用户：项目由一人维护，历史看 git log，不必保留过程注记）。
5. `.tao/.manifests.toml` 列当前子目录 + `README.md`，**不准建子目录和新文件**。
6. `.tao/knowledge/.manifests.toml` 列现有文件 + `owner`；**删除 `cfx-register-usage.md`**（改为移到 `docs/` 并就地修订 `ADR-0046` 的引用）。
7. 门控名 **`check-manifests-guard`**；**`check-spec-readonly` 合并进去**（原目标删除）。

## 清单格式（统一 schema）

```toml
schema = 1
owner = "spec"              # 声明性；门控只打印
subdirs = []                # 允许的子目录；空 = 禁止建子目录
recursive = false           # true ⇒ 对 subdirs 递归应用本清单的 files 规则（第一批全 false）

[files."<name>"]
sha256 = "…"                # 可选；有则校验
owner  = "spec"             # 可选；条目级声明
```

- **清单自身不计入集合**（`files` 里不得列 `.manifests.toml`）。
- `files` 的 key 必须是**该目录的直接子文件**（不含子目录内文件）。
- 非递归模式下：目录下新增/删除**任何**文件或子目录 ⇒ 红。

## 三份清单（内容以现场为准，不得照抄本文数量）

### `spec/.manifests.toml`
- `subdirs = []`、`recursive = false`、`owner = "spec"`。
- `files` = 现场 `spec/*.md` 全部册（22 册，现场 `ls` 计数），每条带 `sha256`（从现有 `manifests/spec-readonly.lock.toml` 迁入，**注记全删**）。
- 迁完 `git rm manifests/spec-readonly.lock.toml`。

### `.tao/.manifests.toml`
- `subdirs = ["adr","archive","contracts","knowledge","tasks"]`、`recursive = false`。
- `files` = `README.md`（有则列；现场核对）。

### `.tao/knowledge/.manifests.toml`
- `subdirs = []`、`recursive = false`。
- `files` = 现有文件（**排除** `cfx-register-usage.md`，它被移走），条目带 `owner`：
  - `MEMORY.md`、`milestones-m14.md`、`milestones-m15.md`、`milestones-m16.md`、`discussing.md`、`issues.yaml` → `main-session`
  - `mirrors.md`、`nodes.md` → `infra`

## `cfx-register-usage.md` 与 ADR-0046

- `git mv .tao/knowledge/cfx-register-usage.md docs/cfx-register-usage.md`。
- **就地修订** `.tao/adr/adr-0046-cfx-register-profile.md` 第 26 行的路径引用（`knowledge/` → `docs/`），**不改任何 decision 内容**；ADR docstring/状态不改。
- 核 `docs/` 是否有对应索引需要补一行（`docs/README.md` 若列文件则补；不新建文件）。

## 门控改造

1. **新增** `tools/infra/check_manifests_guard.py` + `make check-manifests-guard`（**L1**，进 `_locked-check`）：
   - 发现全仓 `.manifests.toml`（`git ls-files -z | grep '\.manifests\.toml$'`），逐个校验；
   - **双向断言**：实际文件集合 == `files`；实际子目录集合 == `subdirs`；多一个少一个都红；
   - 有 `sha256` 的条目逐字节校验；`recursive = true` 时对子目录递归（第一批无使用者，但要有 `--self-test` 覆盖）；
   - `owner` 仅打印；错误信息给 `目录:文件` 与「多出/缺失」；
   - **必须能失败**：`--self-test` 覆盖「新增文件 / 删除文件 / 改 sha256 / 多建子目录 / 清单自身被列入 / recursive 分支」六类注入。
2. **删除** `check-knowledge-dir`（目标 + `tools/infra/check_knowledge_dir.py`）。
3. **删除** `check-spec-readonly`（目标 + `tools/infra/check_spec_readonly.py`），能力并入 guard（反向断言由 guard 的 `spec/.manifests.toml` 双向校验天然提供）。
4. 同步：`Makefile`（`_locked-check`、`GATE_LOCKED_TARGETS`、help、`check`/`check-full` 成员）、`docs/Process-07`（门控表：删 2 加 1）、`docs/Process-06`（spec 保护改为读 `spec/.manifests.toml`，删锁文件描述）、`AGENTS.md`（加两条：① `spec/` 只允许 spec 模块任务修改且需用户裁定；② 清单/锁类文件只写数据、不写过程注记，变更依据看 git log）。

## 验收（逐条贴真实 rc）

1. 三份清单在位，`check-manifests-guard` rc=0。
2. **六类注入**（`--self-test` 或手工）各产生可达 FAIL；`recursive = true` 分支有一条真实子目录用例（可在临时树构造）。
3. `spec/` 新增一册（临时）⇒ guard **rc≠0**（这是本轮要堵的核心缺口）；删除 ⇒ rc≠0；还原 ⇒ rc=0。
4. `sha256` 校验：改一册 spec ⇒ rc≠0；还原 ⇒ rc=0。
5. `manifests/spec-readonly.lock.toml` 已删；`grep -rn "spec-readonly" Makefile tools docs` = 0（历史任务书/ADR 除外，逐条列明）。
6. `cfx-register-usage.md` 在 `docs/`；`ADR-0046` 引用已改；`grep -rn "knowledge/cfx-register-usage" . --exclude-dir=.work --exclude-dir=.cache` = 0（历史任务书除外）。
7. `make check` 中相关门控全绿：`check-manifests-guard`、`check-knowledge-refs`、`check-contracts-dir`、`check-dirs`、`check-archive`、`check-spec-refs`、`check-milestones-fresh`。
8. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. **不改版本号**；不动 `spec/` 正文（只读校验）；不动 `contracts/`。
3. 清单**不写任何过程注记**（用户裁定）；迁移时注记丢弃，不加 `note` 字段。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 若发现某目录实际内容与「只列文件」冲突（如 `.tao/knowledge` 有子目录），**停在待裁定**。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
