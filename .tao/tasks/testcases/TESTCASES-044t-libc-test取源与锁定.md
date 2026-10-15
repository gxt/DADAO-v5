# TESTCASES-044t: libc-test 取源与锁定（取最新 commit）

**模块**：testcases
**项目里程碑**：M8
**依赖**：无（用户 2026-10-14 裁定源 + 版本口径）；前置登记 = `INFRA-076t §libc-test 定源`（只登记不下载，旧快照 `b7ec4679…` **已作废** ✗）；消费方 = 未来 M8 `P1 musl 静态` / `P2 动态链接` 的 **libc 一致性测试**（`ADR-0025 D6`，触发条件同 `LLVM-093t §基线跑触发条件`）
**状态**：待验收

## 执行环境
**执行环境**：本地

## 问题根源 / 立项来源

- **用户裁定（2026-10-14，原话；渠道 = 经主会话问答）**：
  - 「**libc-test: https://github.com/kraj/libc-test**」（定源，2026-10-14）；
  - 「**三个新组件，我记得都已经定好了的，可以入锁，libc-test取最新版本即可**」 ⇒ **放行入锁** + **取最新版本**（⇒ 取**当前最新 commit** 并**锁死**）。
- **动机**：M8 主线 = **无内核的 Linux 用户态栈**（`ADR-0025 D2`），musl 为唯一底座（`P1`/`P2`）；需要一个**独立于实现**的 libc 一致性测试语料来判 musl 移植是否成立（口径 = 独立 oracle，见 `AGENTS.md`「核心原则」）。按 v5 约定「**组件源一律 git 基线**」（`AGENTS.md`「工作区落点」/`lessons §3.19`），须先在本仓库内**取源 + 锁定**，使其**可 `git diff`**（tarball 不作组件源）。
- **订立理由（为何另立任务）**：`INFRA-076t` 对 libc-test **只登记、不下载**（硬约束 4）⇒ 取源与锁定须**独立成任务**。
- **现场实测（2026-10-14，architect 预核，**执行时须复核**）**：

  | 项 | 现场值 |
  |---|---|
  | `git ls-remote`（`gh-proxy.com` 代理） | `b7ec467969a53756258778fa7d9b045f912d1c93` = `HEAD` = `refs/heads/master`，**rc=0**；**无任何 tag** ✗ |
  | GitHub API `default_branch` / `pushed_at` | `master` / `2022-03-19T20:38:52Z` |

  ⇒ **事实（重要，须如实记录）**：该仓 `master` **自 2022-03 起未推进** ⇒ 「取最新」得到的 commit **与旧登记值 `b7ec4679…` 相同**；本轮变化的是**登记口径**（旧 = 「快照、非最新」⇒ **作废** ✗；新 = 「**最新 commit 锁死**」✓），**不是**值。

## 接口规范

- **输入**：用户裁定（源 URL + 取最新）；取源通道（代理，见「§取源通道」）；`manifests/components.lock.toml` 体例（`picolibc` / `qemu` / `llvm-test-suite`）。
- **输出**：
  1. `.cache/<name>.git`（**bare 裸仓库**；形态见「§锁条目与镜像形态」），供离线重建工作树；
  2. `.work/source/<name>/`（**git 检出**，detached at 锁 `commit`，**可 `git diff`**；**不入 git** —— `.work/` 已 gitignore）；
  3. `manifests/components.lock.toml` 新增 **`libc-test`** 条目（见「§锁条目与镜像形态」）；
  4. 本任务书「实测记录」+ 证据（`.work/evidence/<任务ID>/`）。
- **约束**：**不**改组件补丁 / `spec/` / `contracts/` / `tools/` / `components/`；**不**写契约正文；sha / 体积 / 耗时 / 分支形态**现场取证**；正文引用 `.work/**` 一律用 `<>` 占位。

## 取源通道

| 通道 | URL 形态 | 状态（2026-10-14 预核） |
|---|---|---|
| **`gh-proxy.com`（主）** | `https://gh-proxy.com/https://github.com/kraj/libc-test.git` | **✓ `ls-remote` rc=0**（同 `LLVM-093t` 实测可用通道） |
| `ghfast.top`（备） | `https://ghfast.top/https://github.com/kraj/libc-test.git` | 待现场实测 |
| 直连 `github.com` | — | `INFRA-076t` 记直连 `ls-remote` 超时 ✗（本仓体量小 ≈2.3 MB，可现场再试，**结果如实记录**） |

> 小包（≈2.3 MB）预计各代理均可用；**实际所用通道以现场实测为准**，`source[0]` 填**实际成功者**（口径同 `LLVM-093t`：镜像列首位者为 `make fetch` 的默认源）。

## 锁条目与镜像形态

**字段体例**对齐 `picolibc` / `qemu` / `llvm-test-suite`（`manifest_check.py` 硬要求：`repository` 必备；`enabled` 组件 **`commit` 必须 40-hex**；`patchless = true` 者**不得**声明 `patch_dir`/`patch_series`）：

```toml
[[component]]
name = "libc-test"
enabled = true
repository = "https://github.com/kraj/libc-test.git"
commit = "<现场取到的 40-hex 最新 commit>"
shallow = false                # 理由见下「形态选择」
patchless = true               # 无 v5 补丁集（参考/测试语料型，同 chipyard/linux/llvm-test-suite）
role = "libc conformance test suite (M8 musl static/dynamic validation input; no v5 patch set)"

[[component.source]]
name = "gh-proxy"
url = "https://gh-proxy.com/https://github.com/kraj/libc-test.git"
```

- **形态选择（`shallow` 取值须给现场理由）**：本仓**无 tag**、pin = **分支 tip 的 commit** ⇒ 按 `fetch.py` 注释，**浅镜像只跟随被跟踪 ref**（「fetching arbitrary commits is not supported」），上游一旦推进，`--depth 1 --branch <分支>` 的镜像**将不含**锁 commit ⇒ **pin 不可复现**。故**首选 `shallow = false`（全量 `git clone --mirror`，≈2.3 MB，成本可忽略）**；若工程师现场判定 `shallow = true` + `shallow_ref = "<默认分支名>"` 仍满足「**清空 `.cache` 后仍得到锁 commit**」且更省，可改用之，**须在条目注释与本任务书中写明理由**。
- **禁用**：`tag`/`branch` 字面**不得**充当 `commit`（`commit` 只能是 40-hex commit sha）；`shallow_ref` 若填**只能是分支名**，**不得**填 commit。
- 条目上方按 `llvm-test-suite` 体例加**注释**：用户裁定原话 + 取源日期 + 「取最新 commit 锁死」口径 + 旧登记作废说明 + 通道实测。

## 验收标准

1. **源与「最新」取证**：`git ls-remote <代理URL>` 现场输出（`HEAD` + `refs/heads/*` + 有无 `tag`）+ 默认分支名 + commit 日期（`git log -1 --format=%cI`）**如实记录**；**证明所取即当前最新**（对照 GitHub API `pushed_at` 或 `ls-remote` HEAD，**二选一即可、须贴输出**）；若实测值与上表预核值不同 ⇒ **以现场为准并说明**。
2. `.cache/<name>.git` 为 **bare**（`git rev-parse --is-bare-repository` = `true`）；`git cat-file -e <锁commit>^{commit}` **rc=0**；形态（`shallow` 取值 + 是否 `--mirror`）与锁条目**一致**。
3. `.work/source/<name>/` 为 **git 检出**，`rev-parse HEAD` = 锁 `commit`、`status --porcelain` 空；`rev-parse --is-shallow-repository` 现场记录。
4. **`git diff` 可用性证明**：向工作树任一源文件注入探针行 ⇒ `status --porcelain` 报 ` M`、`git diff --quiet` **rc≠0**；还原用 `cp` 备份回写 + **md5 逐位对账**（**禁** `git checkout`/`restore`/`stash`）⇒ `status` 回空、md5 回记录值（注入态「干净」断言须**可达 FAIL**）。
5. **pin 可复现性（独立目录核验）**：在 `/tmp/opencode/TESTCASES-044t/` 下**按锁条目字段**（同 URL、同形态）复跑一次 `clone` + `checkout --detach <锁commit>` ⇒ `rev-parse HEAD` **逐位等于**锁 `commit`。**不要求**整仓 `make fetch`（避免触发其它组件的网络开销/风险）。
6. `manifests/components.lock.toml` 新增 **`libc-test`** 条目（字段/注释见「§锁条目与镜像形态」）；`make manifest-check` **rc=0** + `make check`(L1) **rc=0**。
7. **旧登记作废落纸**：`INFRA-076t §libc-test 定源` 旧的「锁 `commit b7ec4679…`（2022-03 快照）」标注为**作废** ✗，并指向本任务（**本任务书与 `milestones.md` 已预置，本任务复核**）；若现场最新 commit **确实**等于 `b7ec4679…` ⇒ **如实写明「值与旧登记相同、口径已由『快照』改为『最新 commit 锁死』」**（**不得**伪造成不同值）。
8. **记录**：体积（bare / 工作树 `du -sh`）、耗时、顶层构成（`Makefile`/`config.mak.def`/`src/**` 等，现场 `ls`）如实落纸。
9. **参考对照**：`DADAO-0628` / `DADAO` 对 libc-test 的用法（**现场 `grep` 取证**；**无则写明「无命中」**，只借教训、不复制实现）。
10. 门控：`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 **rc=0**。
11. 一键证据脚本（`.work/evidence/<任务ID>/run.sh`）：非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检（**计数不写死**）。
12. `milestones.md`：`TESTCASES-044t` 流水行 + M8 规划区登记（**已由 architect 预置**，本任务复核）。
13. 完成区（**≤30 行**）与真实输出逐条对齐。

## 参考对照（`DADAO-0628` / `DADAO`；**只读、只借教训、不复制实现**）

> 来源：`.cache/refs/DADAO-0628/`、`.cache/refs/DADAO/`（只读参考树；`内容溯源，非执行必需`）。
> **现场取证（2026-10-14，architect 预核）**：`grep -rIl 'libc.test'` 在两棵参考树中**均无命中** ⇒ 参考仓**未使用** libc-test，**无用法可借**；本任务口径**全部取自 v5 自身**（`AGENTS.md` / `Process-01` / `manifests` 体例），**不依赖任何外部仓库内容**（`AGENTS.md`「参考来源与任务自包含」）。

## 用途（**推断，待用户确认**）

- **推断**：libc-test 用于 M8 **musl 侧 libc 一致性测试**（`P1 musl 静态` → `P2 动态链接` 之后的验证语料），与 `LLVM-093t` 的 llvm-test-suite（编译/性能基线）**分工不同**。
- **未经用户确认的部分**：具体**跑法 / 子集 / 判据**（是否用其自带 `Makefile`、是否只取 `src/regression` 等）**本任务不做**；触发条件同 `LLVM-093t §基线跑触发条件`（musl 静态/动态链跑通后另立任务）。**若用户对此推断有异议 ⇒ 停下报告**。

## 硬约束

1. 临时目录 `/tmp/opencode/TESTCASES-044t/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不**用 `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原注入（一律 `cp` + md5）。
3. 文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
4. **只动**：`.cache/<name>.git`、`.work/source/<name>/**`、`.work/log/<模块>/`、`.work/evidence/<任务ID>/`、`manifests/components.lock.toml`、本任务书、`.tao/knowledge/milestones.md`（若需订正）。**不动** `spec/` / `contracts/` / `tools/` / `components/`。
5. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`、**禁** `cmd | tee` 吞码。
6. 大文件（裸仓库 / 工作树）**不得**入 git（`.cache/`、`.work/` gitignored）。
7. **不提交**（提交权归 architect）；取得用户裁定须把**原话**写入本任务书。
8. **失败保留现场并继续推进**（自行处置：查证 / 换通道 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。

## 完成区

**测试结果**：证据脚本 `./.work/evidence/<任务ID>/run.sh` 全量 **A..H rc=0（103/103 检查通过，现场统计〔脚本内计数不写死〕，0 failed；连续两次同值）**；`--inject 1` rc=0 闭环（注入 ⇒ **3 条可达 FAIL**〔C4/C25/C26〕⇒ `cp`+md5 还原 ⇒ 回绿）。门控：`make check`(L1) rc=0（末行 `repository checks (L1): PASS`）、`make check-patch-tree` rc=0（`4 component(s), 129 patches OK`；输出**不含** `libc-test` = patchless 豁免）、`check-dirs`/`check-no-residue`/`check-knowledge-refs`/`check-tasks`/`tools/infra/check_issues.py`/`python3 -m compileall -q tools` 各 rc=0。**`check-modules`(L2) 未跑**（含 `check-picolibc-tests: build-picolibc` ⇒ 写 `.work/build/**`，与下发约束「只跑不触发构建的目标」冲突）⇒ 见"遗留问题"。
**修改文件**：`manifests/components.lock.toml`（新增 `libc-test` 条目 + 注释；相对 `master` **+45 −0** 行）；本任务书（完成区 + 自审 + `**状态**`）。证据（gitignored）：`.work/evidence/<任务ID>/`（`run.sh`、`lockedit.py`）、`.work/log/<模块>/`。**未越界**（未动 `spec/`/`contracts/`/`tools/`/`components/`）。
**验收结果**：（真实输出）① **锁值 = `b7ec467969a53756258778fa7d9b045f912d1c93`**（40-hex）；三通道 `git ls-remote` 均 `rc=0` 且 `HEAD` = `refs/heads/master` = 该值、**0 个 tag**；GitHub API `default_branch=master`、`pushed_at=2022-03-19T20:38:52Z`；`git log -1 --format=%cI` = `2021-10-23T16:14:41+00:00`、主题 `fix regression/pthread_once-deadlock` ⇒ **「取最新」值与旧登记 `b7ec4679…` 相同**（master 自 2021-10 未推进），变化在**口径**（快照 ⇒ 最新 commit 锁死），**如实记录、未伪造差异**。② `.cache/<name>.git`：`--is-bare-repository=true`、`is-shallow=false`、`origin=<source[0] gh-proxy>`、`cat-file -e <pin>^{commit}` rc=0、`refs/heads/master`=pin、tag=0。③ `.work/source/<name>`：`rev-parse HEAD`=pin、`status --porcelain` **0 行**、`--is-shallow-repository=false`、`origin`=本地 mirror。④ **`git diff` 可用**：注入探针 ⇒ `status` 报 ` M`（1 行）、`git diff --quiet` rc≠0、diff 含探针行 ⇒ `cp` 还原 + md5 对账（`abc7c2ea…` 逐位一致）⇒ status 回 0 行。⑤ **`make fetch` 幂等**：二次运行 `fetch: mirror libc-test.git already has b7ec467969a5; skipping fetch` + `fetch: libc-test already at <pin>`，镜像对象文件数 `3→3`、字节 `2573051→2573051`、in-pack `4623→4623`（前后逐项不变）。⑥ **pin 可复现**：`/tmp` 独立目录按锁字段（同 `source[0]` URL、`shallow=false`）复跑 `clone --mirror` + `--no-checkout` + `checkout --detach` ⇒ `rev-parse HEAD` 逐位 == pin。⑦ 体积/耗时（现场统计）：mirror **2.6M**、worktree **14M**、首取 **3 s**、二次 **1 s**；顶层 = `.gitignore AUTHORS COPYRIGHT Makefile README config.mak.def src/`，`src/` = `api common functional math musl regression`，`src/**/*.c` = **462**。⑧ `tools/infra/status.py` 列出 `libc-test enabled b7ec4679…`。⑨ 参考对照：`grep -rIl 'libc.test' .cache/refs/{DADAO-0628,DADAO}` = **0 命中**（无用法可借）。⑩ **旧登记作废**：`INFRA-076t §libc-test 定源` 已标「旧快照 `b7ec4679…` 已作废 ✗」（H7 现场核）。
**新发现/坑**：① **`pushed_at` ≠ 默认分支推进**：该仓 `pushed_at`（2022-03-19）晚于 `master` tip 提交日期（2021-10-23）⇒ 判「是否最新」应以 `ls-remote HEAD`/`refs/heads/*` 为准，`pushed_at` 只作旁证（预核表把 `pushed_at` 注成"最后活动"易被读成 commit 日期）。② **无 tag + pin=分支 tip ⇒ 必须 `shallow=false`**：浅裸镜像只跟被跟踪 ref，上游一推进即丢失锁 commit（`fetch.py` 注释已述；本仓仅 2.6 MB，全量成本可忽略）。③ **直连不稳定**：本次直连 github 可用（`ls-remote` rc=0、`--mirror` 7 s），但 `INFRA-076t`（2026-10-14）记同仓直连超时 ⇒ 主源仍取 `gh-proxy`（2 s）、直连登记为具名备源（`COMPONENT_SOURCE_LIBC-TEST=github`）。④ **`patchless` 双向封口**：`check_patch_tree` 对 `patchless` **只跳过**、`manifest_check` 对 `patchless` **拒绝** `patch_dir`/`patch_series` ⇒ 防「参考型组件偷塞补丁」（C18–C23 注入证可达 FAIL）。
**遗留问题**：① **`check-modules`(L2) 未跑**（唯一未执行项）：该目标含 `check-picolibc-tests: build-picolibc`⇒写 `.work/build/**`，与本任务下发约束「**只跑不触发构建的目标**」冲突；本任务只改锁册 + 取源、不动构建输入 ⇒ L2 判定不受影响；**留 `/complete` 由 architect 按需补跑**（已在下发提示中显式豁免，非静默跳过）。② 任务书 §用途的**跑法/子集/判据**仍为推断（未定），触发条件 = musl 静态/动态链跑通后另立任务 ⇒ 本任务不做。


## 审阅记录

#### 第 1 轮 engineer 自审
**审查范围**（自主逐行）：`manifests/components.lock.toml`（新增 `libc-test` 块，逐行）、`.work/evidence/<任务ID>/run.sh`（逐行）、`.work/evidence/<任务ID>/lockedit.py`（逐行）。

**意见/问题**
1. `E4` 原写 `check ... "$([ "$?" -ne 0 ] ...)"`：`$?` 落在**命令替换子 shell** 内，语义依赖 bash 继承规则、易脆 ⇒ 改为显式 `local drc=$?` 后再判。
2. `F2` 循环内 `check ... "$?"` 依赖「上一命令恰为被检命令」这一隐式前提 ⇒ 改为显式 `local trc=$?`。
3. `--inject 1` 首版只触发 **1 条** FAIL（C4）⇒ 「可达 FAIL」覆盖偏薄；补 **C25/C26**（以**锁册现场值**〔非常量〕反查镜像/工作树，即锁↔产物互指）⇒ 注入态 3 条 FAIL。
4. `A4` 用常量 `EXPECT_PIN` 而非锁册值 ⇒ **有意为之**：A 节视角 = 「镜像是否含*已记录*的锁值」，锁册错值由 C4/C25/C26 抓（分工不重叠，记此以免误判为漏检）。
5. `--inject` 注入**真锁册**：以 `cp` 备份 + md5 + `trap ... EXIT INT TERM` 还原；INJ5/INJ6 现场证「md5 逐位一致 + `git diff --numstat master` 删除 = 0」⇒ 无残留（**未**用 `git checkout`/`restore`/`stash`）。
6. 注入态递归复跑 `bash "$0" --sections AC`：因未传 `--inject` ⇒ 走正常路径，递归深度 1，无自激（INJ3/INJ7 证）。
7. 计数/体积**现场统计**（`4623`、`2573051`、`462`、`129` 等均运行时取，不写死）；`FAILED/CHECKS` 收尾现场统计。
8. 网络侧断言（B3–B11、G3–G9）首版**降级为 `[SKIP]`** ⇒ **检查总数随网络可达性漂移**（95/100 两种），且「不可达 ⇒ 判不了」有退化风险 ⇒ 改为**硬断言**（本任务 = 取源任务，通道不可达即 FAIL）：两次连跑稳定 **103**。
9. 边界复核：`check_field` 对 `False`/`None` 打印为 `False`/`None`（与 git 的 `false` 区分），A2/A10 用 git 小写值、C6/C7 用 python repr ⇒ 期望串各自对齐，无「两支写同一结果」。
10. 未测项：`check-modules`(L2) 未跑（约束见完成区遗留①）；无其它未测面（取源/锁定/幂等/可复现/门控均已现场取证）。

**判决**：finding 1/2/3/8 已修并复验；4/5/6/7/9 为「已核实-无需改动」；无未修 finding ⇒ 状态置 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 1 E4 `$?` 在命令替换内 | ✅已修 | `run.sh` E4 改显式 `drc=$?` | 全量 A..H 中 E4 PASS；注入态亦 PASS |
| 2 F2 循环隐式 `$?` | ✅已修 | `run.sh` F2 改显式 `trc=$?` | 全量跑中 F2 六项均 rc=0 |
| 3 注入仅 1 条可达 FAIL | ✅已修 | 新增 C25（锁册值 → 镜像 `cat-file -e`）、C26（锁册值 == 工作树 HEAD） | `--inject 1` 现场打印 3 条 `[FAIL]`（C4/C25/C26）⇒ 还原回绿 |
| 8 网络断言 `[SKIP]` ⇒ 计数漂移（95/100） | ✅已修 | B3–B11、G3–G9 全改**硬断言**（不降级 SKIP） | 连续两次全量跑均 `checks=103 failed=0`（同值） |
| 4 A4 用常量而非锁册值 | ❌不修 | 无（分工：常量=镜像含已记录锁值；锁册错值由 C4/C25/C26 抓） | C4 在注入态 FAIL 即证分工有效 |
| 5 真锁册注入的还原 | ❌不修 | 无（已按纪律 `cp`+md5+trap） | INJ5 md5 一致（`216e8797…`）、INJ6 删除 0 行 |
| 6 注入态递归深度 | ❌不修 | 无（深度 1，无自激） | INJ3 rc≠0 / INJ7 rc=0 |
| 7 计数是否写死 | ❌不修 | 无（均现场统计） | `checks=103`/对象数/字节数运行期取值 |
| 9 `False`/`None` vs `false` | ❌不修 | 无（期望串已对齐） | A2/A10（git 小写）与 C6/C7（repr）各自 PASS |


#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
