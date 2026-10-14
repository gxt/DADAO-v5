# INFRA-081t: libc-test 取源与锁定（取最新 commit）

**模块**：infra
**项目里程碑**：M8
**依赖**：无（用户 2026-10-14 裁定源 + 版本口径）；前置登记 = `INFRA-076t §libc-test 定源`（只登记不下载，旧快照 `b7ec4679…` **已作废** ✗）；消费方 = 未来 M8 `P1 musl 静态` / `P2 动态链接` 的 **libc 一致性测试**（`ADR-0025 D6`，触发条件同 `INFRA-077t §基线跑触发条件`）
**状态**：待开始

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
| **`gh-proxy.com`（主）** | `https://gh-proxy.com/https://github.com/kraj/libc-test.git` | **✓ `ls-remote` rc=0**（同 `INFRA-077t` 实测可用通道） |
| `ghfast.top`（备） | `https://ghfast.top/https://github.com/kraj/libc-test.git` | 待现场实测 |
| 直连 `github.com` | — | `INFRA-076t` 记直连 `ls-remote` 超时 ✗（本仓体量小 ≈2.3 MB，可现场再试，**结果如实记录**） |

> 小包（≈2.3 MB）预计各代理均可用；**实际所用通道以现场实测为准**，`source[0]` 填**实际成功者**（口径同 `INFRA-077t`：镜像列首位者为 `make fetch` 的默认源）。

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
5. **pin 可复现性（独立目录核验）**：在 `/tmp/opencode/INFRA-081t/` 下**按锁条目字段**（同 URL、同形态）复跑一次 `clone` + `checkout --detach <锁commit>` ⇒ `rev-parse HEAD` **逐位等于**锁 `commit`。**不要求**整仓 `make fetch`（避免触发其它组件的网络开销/风险）。
6. `manifests/components.lock.toml` 新增 **`libc-test`** 条目（字段/注释见「§锁条目与镜像形态」）；`make manifest-check` **rc=0** + `make check`(L1) **rc=0**。
7. **旧登记作废落纸**：`INFRA-076t §libc-test 定源` 旧的「锁 `commit b7ec4679…`（2022-03 快照）」标注为**作废** ✗，并指向本任务（**本任务书与 `milestones.md` 已预置，本任务复核**）；若现场最新 commit **确实**等于 `b7ec4679…` ⇒ **如实写明「值与旧登记相同、口径已由『快照』改为『最新 commit 锁死』」**（**不得**伪造成不同值）。
8. **记录**：体积（bare / 工作树 `du -sh`）、耗时、顶层构成（`Makefile`/`config.mak.def`/`src/**` 等，现场 `ls`）如实落纸。
9. **参考对照**：`DADAO-0628` / `DADAO` 对 libc-test 的用法（**现场 `grep` 取证**；**无则写明「无命中」**，只借教训、不复制实现）。
10. 门控：`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 **rc=0**。
11. 一键证据脚本（`.work/evidence/<任务ID>/run.sh`）：非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检（**计数不写死**）。
12. `milestones.md`：`INFRA-081t` 流水行 + M8 规划区登记（**已由 architect 预置**，本任务复核）。
13. 完成区（**≤30 行**）与真实输出逐条对齐。

## 参考对照（`DADAO-0628` / `DADAO`；**只读、只借教训、不复制实现**）

> 来源：`.cache/refs/DADAO-0628/`、`.cache/refs/DADAO/`（只读参考树；`内容溯源，非执行必需`）。
> **现场取证（2026-10-14，architect 预核）**：`grep -rIl 'libc.test'` 在两棵参考树中**均无命中** ⇒ 参考仓**未使用** libc-test，**无用法可借**；本任务口径**全部取自 v5 自身**（`AGENTS.md` / `Process-01` / `manifests` 体例），**不依赖任何外部仓库内容**（`AGENTS.md`「参考来源与任务自包含」）。

## 用途（**推断，待用户确认**）

- **推断**：libc-test 用于 M8 **musl 侧 libc 一致性测试**（`P1 musl 静态` → `P2 动态链接` 之后的验证语料），与 `INFRA-077t` 的 llvm-test-suite（编译/性能基线）**分工不同**。
- **未经用户确认的部分**：具体**跑法 / 子集 / 判据**（是否用其自带 `Makefile`、是否只取 `src/regression` 等）**本任务不做**；触发条件同 `INFRA-077t §基线跑触发条件`（musl 静态/动态链跑通后另立任务）。**若用户对此推断有异议 ⇒ 停下报告**。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-081t/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不**用 `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原注入（一律 `cp` + md5）。
3. 文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
4. **只动**：`.cache/<name>.git`、`.work/source/<name>/**`、`.work/log/<模块>/`、`.work/evidence/<任务ID>/`、`manifests/components.lock.toml`、本任务书、`.tao/knowledge/milestones.md`（若需订正）。**不动** `spec/` / `contracts/` / `tools/` / `components/`。
5. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`、**禁** `cmd | tee` 吞码。
6. 大文件（裸仓库 / 工作树）**不得**入 git（`.cache/`、`.work/` gitignored）。
7. **不提交**（提交权归 architect）；取得用户裁定须把**原话**写入本任务书。
8. **失败保留现场并继续推进**（自行处置：查证 / 换通道 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
