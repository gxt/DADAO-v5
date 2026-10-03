# 组件补丁组织与构建编排规范

> **状态**：生效（2026-09-23）｜**上位依据**：`ADR-0002 D4`（rev. 2026-09-23）
> **机器检查**：`tools/infra/check_patch_tree.py`（接入 `make check`）
> **关键词**：本规范用「**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）」表达规范性等级；凡标 **必须** 者，均由上述 checker 机械校验。
> **参考业界同类物**：quilt / Debian `debian/patches`（补丁序列）、`git-apply(1)`、Linux `submitting-patches`（补丁形态）。

---

## 1. 范围与术语

- **组件（component）**：由 `manifests/components.lock.toml` 锁定、并在 `.work/source/<name>` 建立工作树的上游仓库（当前为 `llvm-project`、`qemu`）。
- **补丁集（patch set）**：`components/<name>/patches/` 下的全部补丁，用于把上游工作树从其锁定 base commit 改造为 DADAO 定制状态。
- **树形补丁（tree-shaped patch）**：目录结构镜像上游源码树、文件名等于「上游相对路径 + `.patch`」的补丁文件。
- **目标路径（target path）**：一份补丁所作用的上游相对路径。
- **终态（final state）**：某路径在补丁集**全部应用后**的内容。

## 2. 目录形态

```
components/<name>/
├── README.md      # 简明扼要，供人查阅（该组件是什么、补丁集概况）
├── changelog.md   # 每次改动，简洁（按任务一条，追加式）
├── series         # 补丁清单：一行一个，路径**相对 patches/**（如 target/dadao/translate.c.patch）
└── patches/       # 路径镜像树（**纯镜像**：只含 <上游相对路径>.patch）
    └── <上游相对路径>.patch
```

- `patches/` 下的目录结构**必须**镜像上游源码树；补丁文件路径**必须**为 `<上游相对路径>.patch`。
- `patches/` **必须**为**纯镜像**：其下**只**允许 `<上游相对路径>.patch` 文件；清单等元数据一律置于 `patches/` **之外**。
- **必须**保留 `components/<name>/series`，其内容为补丁相对 `patches/` 的路径，一行一个，**顺序按路径字典序**。
- 上述两个路径**必须**在 `manifests/components.lock.toml` 中显式声明：`patch_dir`（镜像树根）与 `patch_series`（清单文件）；脚本**不得**从其一推导其二。
- **不得**设 `newfiles/`、`fixups/` 等多层目录；新增文件亦以补丁表达（见 §5）。

## 3. 命名

- 补丁文件名**必须**为 `<上游相对路径>.patch`，**不得**带 `NNNN` 等编号前缀。
- 例：上游 `target/dadao/translate.c` → `patches/target/dadao/translate.c.patch`。

## 4. 一文件一补丁（双向唯一）

- **必须**满足：**一份补丁只含一个 `diff --git` 条目**（不得多文件一补丁）。
- **必须**满足：**一个目标路径在补丁集中只被一份补丁触及**（不得多补丁改同一文件）。
- 由 §8 断言 ①、② 机械校验。

## 5. 新增文件

- 新增文件**必须**同样以补丁表达（`new file mode` + 全文 `+` 行），**不得**以裸源码文件形式存放于补丁集。
- 新增文件的补丁**必须**是其**终态**：即该路径**不得**再被补丁集中的任何其它补丁触及（与 §4 的第二条一致，但对新增文件尤须保证）。

## 6. 生成流程（源树 → 补丁集）

### 6.1 提交式流程与不变量（E1 / E8）

- **硬规则**：补丁文件**不得**手工编辑或直接修改（§6.1.1）；改组件源码**必须**在 working tree（`.work/source/<name>`）中进行。
- **不变量 E1**：`.work/source/<name>` 在**任何时刻**都**必须**满足：
  1. **worktree 干净**：`git status --porcelain` 输出为空；
  2. **HEAD = 上游 base commit + 恰好 1 个 commit**：`git rev-list --count <base>..HEAD == 1`。
- **E8 澄清**：导出的补丁**仍是裸 `git diff <base>`**（**不含**作者/提交信息）；本地 commit **只用于维持干净工作树**，**永不推送上游**。
- E1 由 §8 断言 ⑦⑧⑨ 机械校验；模块改动前/后可用 §8.1 的 `--source-state` 自检。

#### 6.1.1 硬规则：不得手工编辑补丁

- 补丁文件**不得**手工编辑或直接修改。
- 违反此规则会导致 `@@` 头行数错误、尾部截断等不可预见问题。

### 6.2 生成幂等

- 导出时**必须先与现有补丁比较**；**逐字节一致 ⇒ 不替换**（保持原文件与时间戳不变），避免 `index`/头部信息被无谓刷新。
- 由 `tools/infra/make_patch.py` 实现。

### 6.3 任务起点（E2）与导出步骤（E3）

- **E2 任务起点**：动组件**前**先自检 E1（§8.1）。若 `.work/source/<name>` 不干净，**必须**先把既有改动提交/收敛成「base+1 且干净」（§6.4）；**不干净不得开始新改动**。
- **导出步骤**：
  1. **导出前必须校验 E1**，不满足**拒绝导出**（`tools/infra/make_patch.py` 以非零退出码拒绝并打印原因）。
  2. 对**每个相对 base commit 有改动的路径**，执行
     `git -C .work/source/<name> diff <base_commit> -- <path>`，输出写入 `patches/<path>.patch`。
     - **必须**使用**裸 `git diff`** 输出（非 mbox、无邮件头）。
     - **不得**使用 `git format-patch`（其不支持 pathspec，且会引入 mbox 头与编号）。
     - 因 E1 要求改动已 commit，新增文件已在 HEAD 中，`git diff <base>` 天然可见；**原 `git add -N`（intent-to-add）技巧作废，不再使用**。
  3. 生成 `series`（`components/<name>/series`）：列出全部补丁相对 `patches/` 的路径，按**路径字典序**排序。
  4. 由 `tools/infra/make_patch.py` 实现。

### 6.4 收敛为 1 个 commit（E4）

- 若在当前 base 之上已累积了本地 commit（不论 1 个还是多个），**必须**把它们收敛为**恰好 1 个**以恢复 E1：
  `git reset --soft HEAD~` → `git add -A` → `git commit`。
  - 上面按**最外层恰好 1 个本地 commit** 计；若累积了多个，改为 `git reset --soft <base>` 后重新提交。

> **补注（2026-10-02 事故；2026-10-03 按 E8 改写）**
>
> **「补丁可重建源树」的机械核对**：应用产物与 `.work/source/<name>` 内容一致 + `make check-patch-tree` 断言⑥（§8）。这是捕获 `@@` 头行数错误、尾部截断等手工编辑事故的唯一机械手段。
>
> **陷阱：含 `new file mode` 且无 hunk 的补丁可绕过 `git apply --check`**（2026-10-02 事故根因之一）。实测（git 2.43.0）：**0 字节文件**、**仅含 `diff --git` 头**（无论是否带 `---`/`+++` 行）但**不含 `new file mode`** ⇒ `git apply --check` **报错 rc=128**。**但**：只要含 `new file mode`（无论 blob 是否为空、无论是否缺 `index`/`---`/`+++` 行），**只要无 hunk** ⇒ `git apply --check` **静默通过**（rc=0）；而断言①（每份补丁恰含一个 `diff --git` 条目）和断言③（`series` ↔ `patches/` 双向一致）均无法捕获此类无 hunk 补丁。此时须靠**断言⑥**（应用产物 blob 一致性）兜底；人工审查时亦应核对补丁**含有效 hunk**。

## 7. 应用流程（补丁集 → 源树）

1. **前置校验（E5 放宽）**：工作树 HEAD **必须**属于 `{base, base+1 且该 commit 内容 == 补丁集}`；其余一律**拒绝应用**。
2. **已应用幂等（E5）**：若 HEAD == base+1、该 commit 内容 == 补丁集、且 worktree 干净 ⇒ 视为**已应用**，**跳过**（**不产生**第 2 个 commit）。
3. **逐补丁应用幂等**：按 `series` 顺序**逐补丁**处理：
   - 先对单份补丁执行 `git apply --check --reverse`：**成功 ⇒ 该补丁已应用，跳过**（不执行 `git apply`，不改 mtime）。
   - 失败 ⇒ 先 `git apply --check`（预检），再 `git apply`（应用）。
   - （动机：避免"重放⇒时间戳全变⇒几乎全量重编"，与 `INFRA-018t` 同源。）
4. **应用后自动提交（E5）**：应用完补丁集后，**自动**执行 `git add -A` + `git commit -m "dadao: <component> patch series"`。
   - **不设** local `user.name`/`user.email`（使用环境/仓库既有身份）。
   - **不设** `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`。
   - `<component>` 为组件名，如 `dadao: qemu patch series`。
   - 提交完成后工作树干净且 HEAD = base+1，恢复 E1。
5. **不得**使用 `git am`（本规范不保留作者与提交信息）；上述本地 commit **永不推送上游**。
6. 由 `tools/infra/apply_series.py` 实现。

## 8. 机器检查（9 条断言）

`tools/infra/check_patch_tree.py` **必须**对每个 enabled 组件断言：

| # | 断言 | 说明 |
|---|---|---|
| ① | **每份补丁恰含一个 `diff --git` 条目** | 覆盖 §4 第一条 |
| ② | **目标路径全局唯一** | 覆盖 §4 第二条与 §5（新增文件终态） |
| ③ | **`series` ↔ `patches/` 树双向一致** | 无遗漏、无多余、顺序为路径字典序 |
| ④ | **应用后最终 tree 与期望一致** | 见 §9 |
| ⑤ | **`patches/` 为纯镜像** | 其下每个文件均为 `<上游相对路径>.patch`；覆盖 §2 的纯镜像要求 |
| ⑥ | **应用产物内容一致性** | 补丁集全量应用到 base 后，各受影响路径 blob **必须** == `.work/source` 对应文件；不一致 ⇒ FAIL |
| ⑦ | **worktree 干净（E6）** | `.work/source/<name>` 的 `git status --porcelain` 为空 |
| ⑧ | **HEAD = base + 恰好 1 个 commit（E6）** | `git rev-list --count <base>..HEAD == 1` |
| ⑨ | **HEAD 的净 diff == 补丁集（E6）** | `git diff <base> HEAD` 的净 diff（按路径、`index` 行归一化后）与补丁集**逐路径一致** |

- 断言 ⑥ 与 ⑨ 分工不同：**⑥**＝补丁应用产物 vs **工作树**；**⑨**＝**HEAD commit** vs **补丁集**。
- 若 `.work/source/<name>` 缺失：沿用既有「跳过 apply 检查」的通知语义，**断言 ⑦⑧⑨ 亦随之明确打印跳过**（不得静默）。
- 任一断言失败 **必须**以非零退出码终止。

### 8.1 模块自检（E7）

- 修改某组件的模块，**改动前/改动后各查一次** E1：
  `python3 tools/infra/check_patch_tree.py --source-state`（或 `make check-source-state`）。
- 输出 HEAD、commit count 与干净状态；E1 成立 ⇒ exit 0，否则 ⇒ exit 非零。
- 不干净 ⇒ **先排查自身**（本模块改动是否遗留未提交/未收敛），**不得**带脏树继续。
- `--source-state` **复用断言 ⑦⑧ 的判定逻辑**，不另写一套。

## 9. 应用后一致性

- 补丁集全量应用后，工作树的**最终内容**必须与 DADAO 定制状态一致；校验方式为**逐组件比对 tree hash**（`git write-tree` 或等价）与参考值一致。
- 参考值由 M1 补丁集重整时记录（见 `components/<name>/changelog.md`）。
- 断言 ⑥（§8）进一步验证：补丁集应用到 base 后各受影响文件的 blob 必须等于 `.work/source/<name>` 中对应文件的 blob（内容一致性，捕获 `@@` 头错误等手工编辑事故）。

## 10. 文档约定

- `components/<name>/README.md`：**简明扼要**，供人查阅；说明该组件是什么、补丁集概况（不写逐补丁开发史）。
- `components/<name>/changelog.md`：记录**每次改动**，简洁；**按任务一条**，追加式。
- 补丁的开发脉络**不**在补丁集内叙述；必要时写入代码注释、组件 README/changelog 或仓库级文档。

## 11. 边界情况（**待定**）

以下情形在 M1 补丁集中**无实例**（实测：16 份补丁中 rename / delete / mode 变更均为 0），故本规范**暂不规定**，待出现实例时再议并补入本节：

- **重命名（rename）**：一个 git diff 条目涉及两个路径时，如何计「一文件一补丁」、补丁名用哪个路径。
- **删除（delete）**：`deleted file mode` 条目的补丁命名与计数。
- **净效果为零**：文件在补丁集内「先建后删」或「改了又改回」时，是否产出补丁。
- **mode 变更**（可执行位）、**二进制文件**。

## 12. 迁移与变更记录

- 本规范于 2026-09-23 生效，同时 M1 补丁集由「16 份编号补丁 + `git am`」重整为「树形补丁集（67 份）+ `git apply`」。
- **rev. 2026-09-25**：补丁清单由 `patches/series` 迁至 `components/<name>/series`，`patches/` 成为**纯镜像**；manifest 新增 `patch_dir` 字段（与 `patch_series` 并列，脚本不再互相推导）；断言由 4 条增至 5 条（新增⑤纯镜像）。动机：①使 §2「镜像上游源码树」成为字面成立且可机械校验的不变量；②`make_patch.py` 导出前整体清空 `patches/`，清单置于其外可避免「先删后建」。属 D4 的派生实现细节，未触及 D4 决策，经用户 2026-09-25 裁定**不需新 ADR**。
- **rev. 2026-10-03**（E1–E8，T3 文档分层改造）：确立「提交式流程」——E1 不变量（worktree 干净 + HEAD = base + 恰好 1 个 commit）；E2 任务起点；E3 导出前校验 E1、不满足拒绝导出、废止 `git add -N`；E4 收敛为 1 个 commit；E5 应用后自动提交（不固定 author/日期，message 固定 `dadao: <component> patch series`）、重复应用幂等、HEAD 校验放宽为 `{base, base+1 且内容 == 补丁集}`；E6 断言追加 ⑦⑧⑨（不重排 ①–⑥）；E7 模块改动前/后自检 `--source-state`（并入 `check_patch_tree.py`）；E8 澄清补丁仍为裸 `git diff`、本地 commit 永不推送上游。相应改造 `tools/infra/{make_patch,apply_series,check_patch_tree}.py`。**不改 decision 语义**，为 D4 的派生实现细节。
- 相关决策变更记录见 `.tao/adr/adr-0002-build-orchestration.md` 的 `## 修订`（rev. 2026-09-23）。
