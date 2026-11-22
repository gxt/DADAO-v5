# m17-idl-015: manifest 增加 `ignore` 字段并忽略 `__pycache__`（ISS-480）

**模块**：idl
**项目里程碑**：M17
**依赖**：无（与 `012`/`013` 不同文件；门控面与它们串行）
**可并行分片**：否
**预估**：30–60 min
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定）

`__pycache__` 是 Python 生成物、已在 `.gitignore`，但 `check-manifests-guard` **不读 git**：A2/A3 直接枚举**文件系统**（直接子文件 == `files`、直接子目录 == `subdirs`），用来抓「磁盘上的游离残留」——正是 `.gitignore` 会掩盖的那类东西。因此 `import idl_*` 生成 `idl/tools/__pycache__/` ⇒ 未登记子目录 ⇒ 红（`ISS-480`）。

用户裁定：**忽略项写在 `.manifests.toml`**（数据面），不在门控代码里硬编码目录名：

```toml
ignore = ["__pycache__"]   # 可选；只忽略**直接子项**，且必须是被 git 忽略的生成物
```

## 要做

1. `tools/infra/check_manifests_guard.py`：
   - 清单顶层新增可选字段 `ignore`（字符串列表，默认 `[]`），并入 `ALLOWED_TOP`；
   - 枚举 A2/A3 时跳过 `ignore` 中的**直接子项**（文件或目录，按名字精确匹配）；`recursive=true` 时每层同样生效；
   - **防滥用**（三条硬校验，任一违例 ⇒ FAIL）：① 条目只能是直接子项名（无 `/`、非 `.`/`..`、非空、无重复）；② 不得与 `files` 或 `subdirs` 同名（不能借 ignore 藏内容项）；③ 条目必须被 `git check-ignore -q <dir>/<name>` 判为忽略（生成物才可忽略；仓库外/未跟踪的游离目录仍红；`git` 不可用 ⇒ FAIL，不静默跳过）。
   - 模块 docstring 的 A2/A3 说明同步。
2. `idl/tools/.manifests.toml`（以及 `.py` 模块所在的其他受检目录，如有）加 `ignore = ["__pycache__"]`；`idl/.manifests.toml` 若存在同类风险一并加。
3. `--self-test` 增三路：① 声明 `ignore` + 建该目录 ⇒ PASS；② 不声明 + 建同名目录 ⇒ FAIL；③ `ignore` 与 `subdirs`/`files` 同名 ⇒ FAIL（配置错）。
4. `docs/Process-07` 的 `check-manifests-guard` 行补：可选 `ignore`（仅被 git 忽略的直接子项，且不得遮蔽已登记项）。

## 不做

- 不读 `.gitignore` 做**通配**忽略（只对清单显式列名的直接子项生效）；
- 不忽略任何已登记内容；不改现有 `files`/`subdirs` 内容；不改 `idl/` 布局（归 `012`）。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `tools/infra/check_manifests_guard.py`、`idl/tools/.manifests.toml`（及必要的同类清单）、`docs/Process-07`、本任务书；完成区 ≤30 行。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-manifests-guard` rc=0（现状）；
2. 在 `idl/tools/` 下建 `__pycache__/x.pyc` ⇒ 仍 rc=0；删掉后回基线；
3. 在 `idl/tools/` 下建 `foo/` ⇒ rc=1「未登记子目录」；删除后 rc=0；
4. 把 `ignore` 改成 `["tools"]`（与已登记子目录同名）⇒ rc=1（配置错）；
5. `--self-test`：原 14 类 + 新增 3 类全过，且三路互为对照；
6. 断言真实 rc（禁 `cmd | tee` 吞码）。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
