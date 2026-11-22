# m17-idl-015: manifest 增加 `ignore` 字段并忽略 `__pycache__`（ISS-480）

**模块**：idl
**项目里程碑**：M17
**依赖**：无（与 `012`/`013` 不同文件；门控面与它们串行）
**可并行分片**：否
**预估**：30–60 min
**档位**：中改（复核 ≤40 min）
**状态**：已验证

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

**测试结果**：`run.sh` 18/18 绿（rc=0）；`--self-test` 21/21（原 15 + `ignore` 4 + `recursive`×`ignore` 2）；`make check-manifests-guard` rc=0（10 清单 / 86 文件 / 36 sha256）；`check-no-residue`、`check-dirs` rc=0。

**修改文件**：
- `tools/infra/check_manifests_guard.py`：`ALLOWED_TOP` 加 `ignore`；`load_manifest` 加 A9 结构校验（直接子项名 / 去重 / 不得与 `files`·`subdirs` 同名）；`check_tree` 的 A2/A3 按名跳过；新增 `check_ignores`（`git check-ignore`，git 缺失或非 git 树 ⇒ FAIL）；summary 打印现场统计「ignore 跳过 N」；docstring Schema + A2/A3/A9；`--self-test` 增 4 例（跳过 PASS / 未声明 FAIL / 同名 FAIL / 未被 git 忽略 FAIL）+ 2 例 `recursive`×`ignore`（reviewer F1）
- `idl/tools/.manifests.toml`、`tests/ee-tiny/.manifests.toml`：`ignore = ["__pycache__"]`（后者是另一处含 `.py` 模块的受检目录；`idl/` 根无 `.py` 未加）
- `docs/Process-07-门控分层规范.md`：登记行 + 盘点表 + 末节 `--self-test` 措辞补 `ignore` 口径
- 本任务书

**验收结果**（`/tmp/opencode/m17-idl-015/run.sh` 真实 rc）：
- 基线 rc=0；`__pycache__` 建/删 ⇒ rc=0，现场 `ignore 跳过 1`→`0`；真实 `import idl_paths` 生成 pyc ⇒ rc=0（`ISS-480` 原症状消失）
- 注入 `idl/tools/foo/` ⇒ make rc=2 / 脚本自身 rc=1「多出子目录 foo」→ 删后 rc=0
- 注入 `ignore=["idl_exec.py"]`（files 同名）、`idl/` 根 `ignore=["tools"]`（subdirs 同名）⇒ rc≠0 点名「不得与 files/subdirs 同名」；`ignore=["notignored_dir"]` ⇒「未被 git 忽略」；均 `cp`+md5 还原（`c42857e6…`/`1f20e6fc…`）后回绿
- 反例自检：删 `idl/tools` 的 `ignore` 行 ⇒ 同一 `run.sh` rc=1、4 红 → md5 还原 → 18/18 回绿
- `PATH` 去 git ⇒ rc=1「无法判定」×2，= 现场声明 `ignore` 的清单数（现场派生）
- **reviewer F1 已处理**：`--self-test` 加 2 例 —— `recursive=true` 且根与 `subdirs` 子目录各建 `__pycache__/` ⇒ rc=0（两层都跳过）；`s/__pycache__2/` 干扰项 ⇒ rc≠0 点名「多出子目录 __pycache__2」（只按名精确匹配）。探针「ignore 只在顶层生效」⇒ 该 PASS 例 **转 FAIL**（20/21），md5 还原后回 21/21；`run.sh` 仍 18/18 rc=0

**新发现/坑**：
- `git check-ignore -q <p>` 对**尚不存在**的路径，目录型规则（`__pycache__/`）判 rc=1，带尾斜杠才 rc=0（实测 git 2.43）⇒ 实现分「存在按真实类型 / 不存在按文件→目录」两判
- `git check-ignore` 会吃 `core.excludesFile` 与 `.git/info/exclude`（非仓库 `.gitignore` 也能放行）；按任务书口径如此，日后收紧须解析命中来源
- `make` 把非零归一为 **2**：任务书验证写的「rc=1」是脚本自身退出码，证据两侧都断言

**遗留问题**：无（F2 的 `Makefile` 注释已在收尾改为「逐类注入，条数现场统计」）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `git check-ignore` 对**未创建**的目录型条目判 rc=1 ⇒「先声明、后建目录」会误红 | ✅已修 | `_ignored_by_git`：存在按真实类型；不存在先按文件、再按目录（尾斜杠）各判一次 | `--self-test` 19/19；`run.sh` §1 基线 rc=0 |
| 自检树非 git 仓库 ⇒ A9 恒 FAIL，「声明+建 ⇒ PASS」用例不可能为真（假红） | ✅已修 | `_build_tree` 对临时树 `git init` + 写 `.gitignore`（真判据，不造假） | `--self-test` 19/19 |
| A9 第③条（条目必须被 git 忽略）无自检覆盖 | ✅已修 | 增第 4 例：`ignore=["keepme"]` + 建 `a/keepme/` | 该例 PASS（原因命中「未被 git 忽略」） |
| 证据脚本标题用反引号 ⇒ shell 执行 `ignore`（`command not found`） | ✅已修 | 标题去反引号 | 重跑无该报错，18/18 |
| 任务书验证 4 设想 `idl/tools` 的 `ignore=["tools"]` 与「已登记子目录」同名，但该清单**无 `subdirs`** ⇒ 不构成同名 | ✅已修（改道并披露） | 同名注入改在 `idl/` 根清单（`subdirs` 含 `tools`），另加 `idl/tools` 的 `files` 同名注入 | 两路均 rc=1 且点名「不得与 files/subdirs 同名」 |
| `make` 归一出代码 2，与任务书「rc=1」不符（易被当成未达预期） | ✅已修 | 同一注入两侧断言（make rc≠0 + 脚本自身 rc=1） | §3 实际 `rc=2` / `rc=1` |
| A9「git 不可用 ⇒ FAIL」分支无证据 | ✅已修 | 证据加 `PATH` 去 git 一路，命中数与「现场声明 ignore 的清单数」对账 | 实际 `rc=1 命中=2 声明清单=2` |
| `docs/Process-07` 末节「`--self-test` 六类注入」已过时 | ✅已修 | 改「逐类注入，含 `ignore` 三路」（不写死计数） | 该行 grep 现场核对 |

### 第 2 轮 engineer 自审（reviewer F1：`recursive` 每层生效无自检）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（非阻断）：4 路 `ignore` 用例全是 `recursive=false`，「每层生效」只有临时树手工证明 | ✅已修 | 加 `BASE_B_IGNORE` + 2 例：① 根与 `b/s/` 各建 `__pycache__/` ⇒ rc=0（两层都跳过）；② 再建 `b/s/__pycache__2/` ⇒ rc=1「多出子目录 __pycache__2」（只按名精确匹配） | `--self-test` 21/21；探针把 `ignored` 改为「仅顶层生效」⇒ 例① 转 FAIL（20/21），md5 `9512ba1a…` 还原后 21/21；`run.sh` 18/18 rc=0 |


### 第 1 轮 reviewer 复核

**重跑（reviewer 自己执行，仓库根，禁 `tee` 吞码）**：

| 命令 | 真实输出 / 退出码 |
|---|---|
| 运行期证据目录内 `run.sh` | rc=0；`汇总: PASS=18 FAIL=0`、`结果: PASS`，含 `ignore 跳过 0/1` 现场计数、`PATH 无 git rc=1 命中=2 声明清单=2` |
| `python3 tools/infra/check_manifests_guard.py --self-test` | rc=0；用例行 19、`[FAIL]` 计数 0；末行 `--self-test: 19/19 符合预期` |
| `make check-manifests-guard` | rc=0；`清单 10；受检目录 10；文件 86；sha256 36；ignore 跳过 0`、`结果: PASS` |
| `make check-dirs` / `make check-no-residue` | rc=0 / rc=0（`check-dirs: PASS`、`check-no-residue: PASS`） |

**重点核查（逐条证据）**：
1. **语义**：临时树探针（`recursive=true`，根与 `b/` 两层各建 `__pycache__`、另建子串名 `__pycache__2`）⇒ rc=1 只点名 `__pycache__2`，两层均跳过 ⇒ 按名精确 + 每层生效；`_ignored_by_git` 探针：非 git 树 `None`、PATH 无 git `None`、仓库内 `True` ⇒ 调用方判红不静默；A9 三条硬校验（无 `/`、去重、不得与 `files`/`subdirs` 同名）均在 `load_manifest` 内。
2. **真症状消失**：不设 `PYTHONDONTWRITEBYTECODE`，`import idl_paths` ⇒ pyc=1、门控 rc=0、`ignore 跳过 1`，删后 rc=0；`tests/ee-tiny` 实测 `import run_inst_tiny`（8 处工具以模块方式导入该目录）⇒ pyc=1、rc=0，删后回绿。
3. **未放宽**：`idl/tools/foo/` ⇒ make rc=2 / 脚本 rc=1「多出子目录 foo」；`tests/ee-tiny/foo/` ⇒ rc=1；删后均 rc=0。
4. **清单零内容改动**：两份清单 `git diff` 各仅 +1 行 `ignore`，`files`/`subdirs` 逐字未动；受检 10 清单中含 `.py` 的仅 `idl/tools`、`tests/ee-tiny` 两处（均已登记），`idl/` 根无 `.py` 不加合理。
5. **可达 FAIL（独立注入，非工程 4 路，`cp`+md5 还原）**：`ignore=["sub/deep"]` ⇒ rc=1「只允许直接子项名」；`ignore` 重复项 ⇒ rc=1「有重复项」；`ignore=["."]` ⇒ rc=1；删 `tests/ee-tiny` 的 `ignore` 行 + 同一 import ⇒ rc=1「多出子目录 __pycache__」；还原后 md5 `c42857e6…`/`0e801df7…` 与注入前快照相等、回绿 rc=0。
6. **文档**：`docs/Process-07` 三处补 `ignore` 口径，明写「按名精确匹配，不按路径/通配」，无通配忽略表述。
7. **越界**：`git status --porcelain -uall` 恰 5 文件，与完成区一致；`find` 无 `__pycache__`/`foo` 残留；终态 5 个文件 md5 与注入前快照逐个相等。

**finding（均非阻断）**：

| # | finding | 处置 |
|---|---|---|
| F1 | `--self-test` 的 4 路 ignore 用例全为 `recursive=false`，「每层生效」无自检覆盖 | reviewer 已用临时树探针独立证行为；建议下轮补一例 |
| F2 | `Makefile` 注释仍写「六类注入」（engineer 已披露，`Makefile` 不在允许文件内） | 后续任务顺手改 |
| F3 | `docs/Process-07` 判定列行号 `check_manifests_guard.py:89-236` 与现文件（`audit`=373 行）不符 | 该行号在 HEAD 即陈旧、非本任务引入；文档级，收尾改 |

**判决：Accepted** —— 验收命令在 reviewer 自己的重跑下全绿（18/18、19/19、三项 make rc=0），7 项重点核查逐条有真实输出与退出码，硬约束（不读 git 做通配、不改 `files`/`subdirs`、独立 worktree、不提交、术语「寄存器组」）无违反。本记录不改 `**状态**`。

