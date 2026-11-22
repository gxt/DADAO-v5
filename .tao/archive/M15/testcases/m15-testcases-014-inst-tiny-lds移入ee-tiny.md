# m15-testcases-014: `inst-tiny.lds` 移入 `tests/ee-tiny/`

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-011`（ee-tiny 资产集中，已验证）
**可并行分片**：否（单文件 + 引用）
**预估**：30–60 min
**档位**：小改
**状态**：已验证

## 背景（用户 2026-11-18）

`m15-testcases-011` 把 tiny 的 bootrom/lds 集中到 `tests/ee-tiny/`，但把 `tests/inst/linker/inst-tiny.lds` 作为「inst 测试集布局」排除。用户指出它本质是 **tiny 专属 lds**，应一并集中。

## 目标

1. `git mv tests/inst/linker/inst-tiny.lds tests/ee-tiny/inst-tiny.lds`；`tests/inst/linker/` 若空则删除。
2. 更新引用：`tools/testcases/inst/run_asm_suite.py`（默认 `--lds`/`lds_map`）、`tests/inst/README.md`、`tests/inst/**` 中 `-T`/路径引用、其它 grep 到的调用方。
3. 测试集内容不动（`.S` 不变）。

## 验收（逐条贴真实 rc）

1. 旧路径不存在、新路径存在；md5 一致。
2. `check-inst-asm` **272/272**；`check-tests-index`、`check-dirs`、`check-no-residue` 全 rc=0。
3. `run_asm_suite.py --help` 可运行；1 路注入（引用改回旧路径 ⇒ 红，`cp`+md5 还原回绿）。
4. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：该 lds、调用方/文档、本任务书；**不动**测试集 `.S` 内容、`spec/`、`.tao/contracts/`。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

**改动范围**：`git mv` 1 个 lds；引用更新 207 个文件（202 个 `.S` 仅 `@@ 链接布局：` 注释行；`inst_test.inc` 2 行；`README.md` 2 处；`run_asm_suite.py` 3 处；`causeid.lds` 1 行；`core-wuming-cycle-model.md` 1 行）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 证据脚本 `check()` 比较位写错（拿 desc 当期望值 ⇒ 首跑 20 项全 FAIL 假红） | ✅已修 | 比较改为 `$4` vs `$3`，rc 列取比较结果 | 复跑 20 项全 OK、脚本 rc=0 |
| C6 把 `README.md`/`inst_test.inc` 的新路径也计入「`.S` 命中」（202 vs 204 假红） | ✅已修 | pathspec 收窄到 `tests/inst/*/*.S` | 202 == 202 |
| C11a 用 `git diff` 判「注入生效」（该文件本就有改动 ⇒ 恒真绿） | ✅已修 | 改为「注入前后 md5 不同」 | 实际=changed |
| `.S` 头注释行是否越界（任务书写「`.S` 内容不动」） | ❌不修（判定非越界，已在完成区披露） | 保留 202 处注释行更新 | 逐文件 diff：每文件仅 `@@ 链接布局：` 的 −/+ 各 1 行（202/202 文件 bad=0）；先例 `m15-testcases-006` 同样批量改该行 |

**逻辑/边界复核**：`DEFAULT_LDS` 仍是唯一默认来源（`--lds` 只覆盖），无按册映射表残留；70 个无 `@@ 链接布局：` 头的 `.S` 未被触碰；`.S` 的指令/期望/检查点零改动；历史记录（任务书、MIGRATION、discussing）不改写。

### 第 1 轮 reviewer 验收

**自证与快照**：`pwd`/`git rev-parse --show-toplevel` = 任务 worktree；分支 `m15-testcases-014`、HEAD=b312e129(WIP)；注入前/后 `git status --porcelain -uall` 均 0 行、逐行对账一致。

**重跑记录（我方命令 → 真实输出/退出码）**
- 迁移：`ls tests/inst/linker/` → `No such file or directory`（rc=2）；`tests/ee-tiny/inst-tiny.lds` 存在；其 md5 `91bfe81f06a922f2c7b0cb9095b39c93` == 基线 `b2d79c9f` 旧路径 blob 的 md5。
- `.S` 口径：改动 `.S`=202 == 基线带头部 `.S`=202（文件名集合逐一对账一致）；逐文件 `-U0` 断言「仅 1 处 −/+、均为 `@@ 链接布局：`、除 lds 路径外逐字相同」→ bad=0；现树带头部 `.S`=202 / `.S` 总数=272；指令/期望/检查点零改动。
- 引用：`DEFAULT_LDS`（run_asm_suite.py:142）、`--lds` help（:373）、`README.md` 2 处、`inst_test.inc` 2 行、`causeid.lds` 1 行、`docs/core-wuming-cycle-model.md` 1 行均已指向新路径；活动面旧路径 grep = 0（rc=1、无输出），余 10 处全在 `.tao/` 历史与 `tests/inst/MIGRATION.md`。
- 门控独立重跑：`check-tests-index` rc=0（PASS 472 条）、`check-dirs` rc=0、`check-no-residue` rc=0、`check-inst-macro-scope` rc=0（S9 WARN 系既有）、`timeout 2400 make check-inst-asm` rc=0 → `272/272 镜像通过（链例+故障链 633 例）`、`check-inst-asm: PASS`；`run_asm_suite.py --help` rc=0。
- 越界：`$BASE..HEAD` = 208 M + 1 R；非 `.S` 仅 6 文件（本任务书/README/inst_test.inc/run_asm_suite.py/causeid.lds/core-wuming-cycle-model.md）；`spec/`、`.tao/contracts/`、组件补丁、`Makefile` 命中 0；版本号改动 0。

**证据脚本审计 + 重跑**：20 条断言均有可达 FAIL 路径、无恒真；门控均 `>log; rc=$?` 未吞码。**重跑 `run.sh` → rc=1（17 OK / 3 FAIL）**：`[FAIL] C7a 期望=404 实际=0`、`[FAIL] C7b 期望=202 实际=0`、`[FAIL] C7c 期望=204 实际=0`。根因：C7 用裸 `git diff`（工作树↔索引），WIP 已提交后为空 ⇒ 恒假红，违反 AGENTS「断言『某变更存在』须带 `$BASE..HEAD`，禁裸 `git diff`」。

**独立注入（任务书未列的头注释路）**：把某 `.S` 的 `@@ 链接布局：` 改回旧路径（md5 `21faa649…`→`8662defb…`）⇒ 重跑同一脚本 rc=1：`C4 期望=0 实际=1`、`C6 期望=202 实际=201`、`C7a 404→2` ⇒ 红；`cp` 还原 md5 相等（`21faa649…`）⇒ 重跑回到 17 OK/3 FAIL（仅 C7）、`git status` 0 行。脚本自带 C11（DEFAULT_LDS 注入）在我重跑中亦 rc=2 红、还原后 rc=0。

**约束核验**：① 独立 worktree、未碰主工作树 ✅；② 只动 lds+调用方/文档+本任务书，越界 0 ✅；③ 未改版本号 ✅；④ 未提交 git ✅（本记录为唯一新增脏项）；⑤ 还原只用 `cp`+md5、未用 checkout/restore/stash/show ✅；⑥ 无 `cmd|tee` 吞码、`timeout` 未触发 124 ✅。

**判决：Needs Revision**
- 失败项：证据脚本（运行期证据目录）C7a/C7b/C7c，重跑 rc=1，不满足「20/20」。
- 修改建议（engineer 改，reviewer 不代写）：C7 三处 `git diff` 改为 `git diff b2d79c9f -- tests/inst…`（基线↔工作树，提交前/提交后/注入期均成立）；另 C4 的 `git grep | wc -l` 会把 git grep 自身报错吞成 0（假绿），改为捕获其 rc、>1 判 FAIL。修后重跑应 20/20 rc=0 再复验。
- 非阻断 finding：C1–C7 打印的 `rc=` 是比较常量而非真实退出码（engineer 已披露），建议改标 `cmp=`；C7c 写死 `hdr + 2`，`tests/inst` 后续再增文件会假红，建议现场派生。

### 第 2 轮 engineer 自审（返工：Needs Revision）

| finding（reviewer） | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| C7a/C7b/C7c 用裸 `git diff`，WIP 提交后为空 ⇒ 恒假红 | ✅已修 | 三处改 `git diff b2d79c9f …`（基线↔工作树） | 提交态 C7a 404==404、C7b 差异 0、C7c 205==205；同时刻旧写法 = 0（反证已留） |
| C4 `git grep … \| wc -l` 吞掉 grep 自身报错（假绿） | ✅已修 | 新增 `ggc()`：捕 rc，`rc>1` ⇒ 返回 -1 交断言判 FAIL | 非法正则自检 rc=128 ⇒ -1；注入旧引用 ⇒ C4 期望 0/实际 1 红 |
| C7c 写死 `hdr + 2`，`tests/inst` 增文件会假红 | ✅已修 | 期望 = 头部 `.S` + 含新路径的非 `.S` + 旧路径删除（三侧现场派生） | 205 = 202 + 2 + 1 |
| （非阻断）C1–C7 的 `rc=` 实为比较结果 | ✅已修 | 标签改 `cmp=`，仅 C11b 保留真实 `rc=` | 输出示 `cmp=0` / `rc=2` |

**复验（含第 1/3 次重试的落盘复核）**：证据脚本 md5 `c6f32521…`（6930 B，运行期证据目录）→ 20/20、rc=0（提交态可复现）；`make check-inst-asm` rc=0 → 272/272 PASS；注入 C4/C7 所需的两处改动后脚本 rc=1（`C4 0/1`、`C7a 402/403`、`C7b 0/2`、`C7c 204/205`），`cp` 还原后 `md5sum -c` OK 且回绿 20/20。

### 第 2 轮 reviewer 验收

- 返工落盘核验：证据脚本在运行期证据目录、被 `.gitignore` 第 2 行忽略（`git check-ignore -v` rc=0）⇒ `git status` 看不见它不是未落盘，盘上 md5 `c6f32521…`/120 行（上轮 `4a4e8ff3…`/105 行）⇒ 改了盘上、非未落盘；C7 三处已改 `git diff "$BASE"`（基线↔工作树），C4 新增 `ggc()` 捕 `git grep` rc、`>1` ⇒ -1 判 FAIL，C7c 期望=头部 `.S`+非 `.S` 新路径+旧路径删除 三侧现场派生，标签改 `cmp=`。
- **重跑证据脚本（HEAD=2ee46635 提交态、干净树）→ rc=0、20 OK / 0 FAIL**：`C7a 404==404`、`C7b 0==0`、`C7c 205==205`、`C9a rc=0`、`C9b 272/272`、C10 四门控 rc=0。
- **独立注入（任务书未列，两路）**：① 某 `.S` 头注释路径改回旧路径（`21faa649…`→`8662defb…`）；② 另一 `.S` 删一行 `@@ 链接布局：`（`618cff01…`→`ef829971…`）⇒ 同一脚本 **rc=1、16 OK / 4 FAIL**：`C4 0/1`、`C6 201/200`、`C7a 402/401`、`C7b 0/4`（C4/C7 均红，可达 FAIL 成立）。
- **`cp`+md5 还原**：两文件 md5 均回 `21faa649…`/`618cff01…` ⇒ 重跑 **rc=0、20/20**、`check-inst-asm 272/272 镜像通过`；`git status --porcelain -uall` 0 行、`run_asm_suite.py` md5 回 `34e42b77…`。
- 约束：未提交 git、未碰主工作树、还原只用 `cp`+md5（未用 checkout/restore/stash/show）✅。
- **判决：Accepted** —— 上轮唯一阻断（C7 裸 `git diff`）已闭合，C4/C7c/`cmp=` 同轮已修，提交态可复现。

## 完成区

**测试结果**：证据脚本 20/20 通过、rc=0（WIP 提交态可复现）；`check-inst-asm` 272/272 镜像 PASS；`check-tests-index`/`check-dirs`/`check-no-residue`/`check-inst-macro-scope` 全 rc=0；失败原因：无。

**修改文件**：
- `tests/inst/linker/inst-tiny.lds` → `tests/ee-tiny/inst-tiny.lds`（`git mv`；旧目录 `tests/inst/linker/` 已删）
- `tests/inst/**/*.S` 202 个（仅 `@@ 链接布局：` 注释行的 lds 路径，每文件 −1/+1）
- `tests/inst/macros/inst_test.inc`（2 行注释路径）、`tests/inst/README.md`（布局表行 + 「链接布局」节）
- `tests/ee-tiny/run_asm_suite.py`（docstring / `DEFAULT_LDS` / `--lds` help）
- `tools/chipyard/excp/causeid.lds`（头注释）、`docs/core-wuming-cycle-model.md`（载体口径）
- 本任务书（含返工记录）；证据脚本 `run.sh`（运行期证据目录，未入仓）

**验收结果**（真实输出）：
- C1/C2 旧路径 absent、新路径 present；C3 md5 `91bfe81f06a922f2c7b0cb9095b39c93` == 基线提交旧路径 blob
- C4 活动文件旧路径残留 0（豁免 `.tao/` 历史任务书与 `tests/inst/MIGRATION.md` 历史台账；注入旧引用 ⇒ 实际 1 红）
- C6/C7 头部 202 == 202；基线↔工作树 `@@ 链接布局` 改动 404 行 = 2×202；改动 `.S` 集合 == 带头部集合；`tests/inst` 改动 205 == 202 + 2 + 1（三侧现场派生）
- C11 注入：`DEFAULT_LDS` 改回旧路径 ⇒ rc=2 `ERROR: lds 不存在`；`cp` 还原 md5 一致 ⇒ 单 id rc=0 回绿
- 反向注入两路（删 1 行头部 ⇒ C7a/C7b/C7c 红；README 加旧路径 ⇒ C4 红）脚本 rc=1，`cp` 还原后 `md5sum -c` OK、回绿 20/20
- `check-inst-asm: PASS` 272/272 镜像（链例 + 故障链 633 例）；`check-tests-index` PASS（472 条）；其余三门控 PASS；`run_asm_suite.py --help` rc=0
- `git status -uall` = 1 项（本任务书 M；证据脚本在运行期证据目录、gitignored，不进 `git status`）；`git diff --stat` = 1 file changed, 46 insertions(+), 10 deletions(-)；基线↔工作树 = 209 files changed, 287 insertions(+), 213 deletions(-)

**新发现/坑**：
- 断言「某变更存在」须带基线（`git diff <BASE> -- …`）：WIP 提交后裸 `git diff` 为空 ⇒ 恒假红。
- 跨基线比对加 pathspec 会丢配对侧（重命名退化为旧路径 D + 新路径新增）⇒ 期望集合须计入 `--diff-filter=D`。
- `git grep … | wc -l` 吞 grep 报错成 0（假绿）⇒ 必须捕 rc。
- 272 个 `.S` 仅 202 个带 `@@ 链接布局：`（70 个后加文件无该头），计数禁写死。
- 「`.S` 内容不动」按「指令/期望/检查点不动」执行，路径只落在头注释（与 `m15-testcases-006` 同口径）。

**遗留问题**：历史记录旧路径按「历史不改写」保留——`tests/inst/MIGRATION.md` 10 处、`.tao/tasks/m15-testcases-006/007/011`、`.tao/knowledge/discussing.md`；非活动引用、不影响门控。
