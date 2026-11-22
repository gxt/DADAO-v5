# m17-idl-015: manifest 门控精确忽略 `__pycache__`（ISS-480）

**模块**：idl
**项目里程碑**：M17
**依赖**：无（与 `012`/`013` 不同文件；门控面与它们串行）
**可并行分片**：否
**预估**：30–60 min
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定）

`__pycache__` 是 Python 生成物、已在 `.gitignore`，但 `check-manifests-guard` **不读 git**：它的 A2/A3 直接枚举目录的**文件系统**内容（直接子文件 == `files` 键、直接子目录 == `subdirs`），目的是抓「磁盘上的游离残留」——这正是 `.gitignore` 会掩盖的那类东西。所以 `import idl_*` 一旦生成 `idl/__pycache__/`，就多出一个未登记子目录 ⇒ 门控红（`m15-idl-021`、`m17-idl-002` 各踩一次；`ISS-480`）。

修法**不**改成读 `.gitignore`（那会让构建产物一起藏起来，削弱 fail-closed），而是**精确名例外**：只忽略名为 `__pycache__` 的目录。

## 要做

1. `tools/infra/check_manifests_guard.py`：A2/A3（含 `recursive` 递归面）枚举时**精确忽略**名为 `__pycache__` 的子目录；不新增其它忽略项、不读 `.gitignore`。
2. `--self-test` 增两路（现有十四类之外）：
   - 受检目录内建 `__pycache__/`（内含一个 `x.pyc`）⇒ 仍 PASS；
   - 受检目录内建 `foo/` ⇒ 仍 FAIL（证明未放宽）。
3. `docs/Process-07` 的 `check-manifests-guard` 行补一句：忽略生成目录 `__pycache__`（精确名），其它游离目录/文件仍 FAIL。
4. （防御性，可选）`Makefile` 的 `check-idl-*` 目标统一加 `PYTHONDONTWRITEBYTECODE=1`。

## 不做

- 不读 `.gitignore`、不忽略其它生成物（`.work/` 不在受检根内；目录根下散落的 `*.pyc` 文件仍判红）；
- 不改任何 `.manifests.toml` 的内容；不改 `idl/` 布局（归 `012`）。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `tools/infra/check_manifests_guard.py`、`docs/Process-07`、（可选）`Makefile`、本任务书；完成区 ≤30 行。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-manifests-guard` rc=0（现状）；
2. 在 `idl/` 下建 `__pycache__/x.pyc` ⇒ 仍 rc=0；删掉后回基线；
3. 在 `idl/` 下建 `foo/` ⇒ rc=1 且报「未登记子目录」；删除后 rc=0；
4. `python3 tools/infra/check_manifests_guard.py --self-test`：原 14 类 + 新增 2 类全过，且**新增的两类互为反例**；
5. 断言真实 rc（禁 `cmd | tee` 吞码）。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
