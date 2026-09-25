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

1. 在 `.work/source/<name>` 工作树上直接编辑（**不必**为每个补丁建立 commit；本规范**不保留**作者与提交信息）。
2. 导出：对**每个相对 base commit 有改动的路径**，执行
   `git -C .work/source/<name> diff <base_commit> -- <path>`，输出写入 `patches/<path>.patch`。
   - **必须**使用**裸 `git diff`** 输出（非 mbox、无邮件头）。
   - **不得**使用 `git format-patch`（其不支持 pathspec，且会引入 mbox 头与编号）。
3. 生成 `series`（`components/<name>/series`）：列出全部补丁相对 `patches/` 的路径，按**路径字典序**排序。
4. 由 `tools/infra/make_patch.py` 实现。

## 7. 应用流程（补丁集 → 源树）

1. **前置校验**：工作树 HEAD **必须**等于 `manifests/components.lock.toml` 中的 base commit；不等则**必须**拒绝应用。
2. **已应用检测**：若 `git apply --check --reverse` 对全部补丁成功，视为**已应用**并跳过（幂等）。
3. **预检**：`git apply --check` 对全部补丁（按 `series` 顺序）**必须**全部通过。
4. **应用**：`git apply` 逐份应用（按 `series` 顺序）。
5. **不得**使用 `git am`（本规范不保留作者与提交信息）。
6. 由 `tools/infra/apply_series.py` 实现。

## 8. 机器检查（5 条断言）

`tools/infra/check_patch_tree.py` **必须**对每个 enabled 组件断言：

| # | 断言 | 说明 |
|---|---|---|
| ① | **每份补丁恰含一个 `diff --git` 条目** | 覆盖 §4 第一条 |
| ② | **目标路径全局唯一** | 覆盖 §4 第二条与 §5（新增文件终态） |
| ③ | **`series` ↔ `patches/` 树双向一致** | 无遗漏、无多余、顺序为路径字典序 |
| ④ | **应用后最终 tree 与期望一致** | 见 §9 |
| ⑤ | **`patches/` 为纯镜像** | 其下每个文件均为 `<上游相对路径>.patch`；覆盖 §2 的纯镜像要求 |

任一断言失败 **必须**以非零退出码终止。

## 9. 应用后一致性

- 补丁集全量应用后，工作树的**最终内容**必须与 DADAO 定制状态一致；校验方式为**逐组件比对 tree hash**（`git write-tree` 或等价）与参考值一致。
- 参考值由 M1 补丁集重整时记录（见 `components/<name>/changelog.md`）。

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
- 相关决策变更记录见 `.tao/knowledge/adr-0002-build-orchestration.md` 的 `## 修订`（rev. 2026-09-23）。
