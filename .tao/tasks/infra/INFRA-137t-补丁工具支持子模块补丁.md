# INFRA-137t: 补丁工具支持「组件内子模块」补丁

**模块**：infra
**项目里程碑**：M11
**依赖**：无（`INFRA-136t` 依赖本任务）
**状态**：待开始

## 背景与事实

`INFRA-136t` 要把 chipyard 的 `generators/testchipip` 子模块内的 `SimTSI.cc` 修好（`--help` 崩溃），但现有补丁工具无法表达子模块内的文件：

- `generators/testchipip` 在 chipyard 仓库里是 **gitlink**（`160000`），父仓没有该文件
- 子模块内改文件后，父仓 `git status` 只显示 ` M generators/testchipip`，`diff --stat` 为 0 行
- 生成的补丁 `git apply --check`（worktree）rc=0，但 `git apply --cached --check`（scratch index）rc=1 `does not exist in index` ⇒ `check_patch_tree` 断言 ④⑥ 与 `apply_series` 的 `expected_tree` 全部走不通
- `fetch.py` **不管理子模块**：新机器上没有子模块检出，`apply-series` 无处可打

用户裁定（2026-11-08）：「A」——扩展工具支持子模块补丁，而不是改构建胶水或只做运行期修改。

## 目标（设计，实现须遵守）

### 1. 清单（`manifests/components.lock.toml`）

受补丁组件可声明子模块补丁源：

```toml
[[component]]
name = "chipyard"
# … 既有字段；去掉 patchless，加：
patch_dir = "components/chipyard/patches"
patch_series = "components/chipyard/series"
submodule_patches = [{ name = "testchipip", path = "generators/testchipip" }]
```

- `name` 用于 `series` 前缀与 `patches/<name>/` 目录；`path` 是组件内的子模块路径。
- 未声明 `submodule_patches` 的组件行为完全不变（回归面控制）。

### 2. 系列文件（`series`）

- 以 `<name>/` 开头的行 = 该子模块的补丁，路径相对子模块根（如 `testchipip/src/main/resources/testchipip/csrc/SimTSI.cc.patch`）；
- 其余行 = 父仓补丁（语义不变）；
- 判定用「首段是否命中已声明 name」，不得按扩展名/目录猜测。

### 3. `apply_series.py`

对每个组件：

1. 从**父仓 base 树**取子模块 base 提交：`git ls-tree <base> <path>` ⇒ `160000 <sha>`。
2. 子模块工作树必须存在且 clean、HEAD == 该 base；否则**明确失败**并提示「先初始化子模块」（`git submodule update --init <path>`），不得静默跳过。
3. 先按顺序应用子模块补丁（逐条 `--check --reverse` 幂等），在**子模块内**提交（message 带组件名与子模块名）；再应用父仓补丁；最后父仓 `git add <path>`（gitlink）并提交。
4. 幂等：父仓 HEAD 已是 base+1 且（父仓树除 gitlink 外 == base+补丁）且（子模块 HEAD == base+子模块补丁）⇒ 打印 already applied 并跳过。
5. 失败路径保留现场（不 `reset --hard` 之外的自动回滚；若已提交子模块需说明手工恢复方式）。

### 4. `check_patch_tree.py`

- **父仓**：期望树 = base 树 + 父仓补丁，**并把 `<path>` 的 gitlink 覆盖为「本机子模块 HEAD」**；断言 ④⑥ 只针对父仓补丁条目（子模块补丁不得参与 scratch-index 应用）。
- **跨机比较口径（关键）**：子模块的补丁提交由各机 `apply-series` **本地生成**，其 SHA 含时间戳 ⇒ 父仓 gitlink 的值**逐机不同**。因此：
  - 父仓「期望树」只能在本机内部自洽（用本机子模块 HEAD 代入），**禁止**把父仓 tree hash 与 gitlink SHA 跨机比较；
  - 跨机一致性一律比 **子模块 tree hash**（与组件层现有「比 tree 不比 commit id」口径一致）；
  - 任何断言不得要求两台机器的 gitlink SHA 相等。
- **子模块**：断言「HEAD == 子模块 base + 1」「worktree clean」「HEAD 树 == base 树 + 子模块补丁」。
- 断言 ⑦⑧（`--source-state`）对父仓仍适用；子模块的 clean/base+1 作为**新增断言**（编号顺延，文档同步）。
- 输出须逐条可读：`chipyard:testchipip: assertion N: …`。

### 5. `fetch.py`

- 组件声明了 `submodule_patches` 时，`make fetch` 负责把对应子模块检出到 base：
  - 优先用本地镜像 `.cache/<component>-<name>.git`（离线）；
  - 镜像缺失 ⇒ **明确报错**并给出 `make fetch` 的补镜像方式，**不得**转去公网静默 clone。
- 说明：镜像由 `fetch.py` 首次从上游建（记录 URL 到 changelog/文档），之后走本地。

### 6. 文档

- `docs/Process-01`（组件补丁组织与构建编排）补充「子模块补丁」的目录/系列/断言约定；
- `components/chipyard/README.md` + `changelog.md` 写清新增能力与回退方式。

## 范围 / 非范围

**在范围内**：`tools/infra/{fetch,apply_series,check_patch_tree,make_patch}.py`、`manifests/components.lock.toml`（仅结构与 chipyard 条目）、`docs/Process-01`、`components/chipyard/**`（README/changelog 与空补丁集骨架）、本任务书、`milestones.md`。

**不在范围**：任何具体的 `SimTSI.cc` 修复（属 `INFRA-136t`）、其它组件的补丁语义、`Makefile` 目标名。

## 验收标准

1. **零回归**：现有 7 个受补丁组件的 `check-patch-tree` / `check-source-state` / `make apply-series` 全部 rc=0（先跑基线，改后逐项对照）。
2. **子模块补丁可应用**：用一个**最小占位补丁**（例如在子模块内加一个空行注释文件）验证 `apply-series` 能应用、提交、父仓 gitlink 更新；`check-patch-tree` rc=0。
3. **幂等**：再次 `make apply-series` ⇒ 打印 already applied、rc=0，源树不变（md5 对比）。
4. **失败路径可达**：子模块缺失/HEAD 不是 base ⇒ 明确报错并非零；子模块补丁不匹配 ⇒ 报错并指出补丁路径。
5. **负控**：故意让父仓期望树不匹配（注入）⇒ `check-patch-tree` FAIL；`cp`+md5 还原回绿。
6. **新机器可复现**：模拟「子模块未初始化」（临时树），`make fetch` 能给明确指引；按指引离线初始化后可 `apply-series`。
7. `make check`（L1）rc=0；`docs/Process-01` 与实现一致（人工核对清单给出）。
8. 完成区 ≤30 行、无运行期路径。

## 说明

- 子模块 `generators/testchipip` 当前 base = `26f821be94252b9c4c83511a3376a51ffc138551`（父仓 gitlink，chipyard 共 55 个子模块；`sims/verilator` 属 chipyard 自身，不在本次改动内）。
- 这是**主流程改动**，务必先记录改前的 `check-patch-tree`/`check-source-state`/`apply-series` 输出作为基线，再逐项对照。
- 允许分两次提交（工具+清单、文档），但同一次下发内完成。
- 若实现中发现设计与现有断言不可兼容（例如 ⑦⑧ 依赖单一 HEAD），**停下报告**并给出替代设计，不要私自放宽断言。
