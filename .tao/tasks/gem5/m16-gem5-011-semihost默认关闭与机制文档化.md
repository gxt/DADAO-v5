# m16-gem5-011: semihosting 默认关闭（与 ARM/RISC-V 一致）+ 调用机制与安全边界文档化

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-007`（semihosting 开关，已验证）、`m16-chipyard-001`（已收尾）
**可并行分片**：否（`components/gem5` 单写者）
**预估**：1–1.5 h
**档位**：小改（一处默认值 + 两份文档；复核 diff + 1 路注入 + 受影响门控）
**状态**：待验收

## 背景（用户 2026-11-17 裁定）

> 用户：「默认关闭没问题，关键是怎么调用宿主机功能」——即采「接受 `--semihost` 开关 + **默认 `off`**、显式开启」，与 gem5 上游 ARM（`--semi-enable`）/ RISC-V（`--semihosting`）一致。

现状：

- `configs/dadao/se_timing.py`：`--semihost` 默认 **`off`**（与上游一致）。
- `configs/dadao/fs.py`：默认 **`on`**（不一致，需统一为 `off`）。
- 调用方（`tools/gem5/compare_chipyard.py`、`tools/testcases/parity/qemu_gem5_shim.py`）均**显式**传 `--semihost on` ⇒ 改默认值无回归。
- `components/gem5/README.md` / `changelog.md` 未写「触发机制 + 服务表 + 宿主边界」。

## 目标

1. **默认值统一**：把 `fs.py` 的 `--semihost` 默认 `on` → **`off`**。按 `docs/Process-01` 的组件流程：改**源树** `configs/dadao/fs.py`（`.work/source/gem5`）→ `python3 tools/infra/make_patch.py gem5` 重导补丁 → 确认 `make_patch` 幂等。
2. **文档化调用机制**（写进 `components/gem5/README.md` 与 `changelog.md` 的对应条目，不新建文件）：
   - **触发**：guest 执行 `trap <任意 cfxha>, 0x3FFxx`（`immu18[17:8] == 0x3FF`）；gem5 在 cfx/向量处理**之前**短路，QEMU 同口径；`--semihost off` 或无 responder 时该 trap 行为不变。
   - **传参**：服务号 `rd16`、参数块指针 `rb16`、标量返回 `rd8`、64 位**大端**（`contract-semihosting §2`）。
   - **服务表**：`BaseSemihosting` 的 24 个 generic 服务 + `SYS_SYNCCACHE`（0x19）；适配器只提供 `State/Result`（寄存器/大端/`TranslatingPortProxy`）。
   - **宿主边界**：console → 宿主 stdout（`--console-out`）；文件 → `files_root_dir`；时间 → 宿主时钟；`SYS_SYSTEM` 默认 `deny`（`--semihost-system native` 才允许）。
   - **默认关**：`se_timing.py`/`fs.py` 均 `off`，需显式 `--semihost on`。
3. 不改 C++、不重建 `gem5.opt`（仅 Python 配置与文档）。

## 验收（逐条贴真实 rc）

1. `grep -n '"--semihost"' .work/source/gem5/configs/dadao/fs.py` 默认值 = `off`；`se_timing.py` 仍 `off`。
2. `make_patch gem5` 幂等（二次 `0 written`）；`check-patch-tree` gem5 段 **0 problem**；`--source-state` gem5 OK；`check-component-changelog` rc=0。
3. `check-gem5-decode` rc=0。
4. **1 路注入**（`cp`+md5 还原）：把 `fs.py` 默认改回 `on` ⇒ 验收 1 的断言必须红。
5. README/changelog 的机制段五项齐全（触发/传参/服务表/宿主边界/默认关），逐项可 `grep` 命中。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **不改任何版本号**（版本号升级须用户认可，见 `AGENTS.md` 核心原则）。
3. 只动：`components/gem5/patches/configs/dadao/fs.py.patch`（重导产物）、`components/gem5/README.md`、`components/gem5/changelog.md`、源树 `configs/dadao/fs.py`、本任务书。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`fs.py` 默认值改动、重导出补丁 diff、README 新节、changelog 条目、一键证据脚本。

**逐项核对**：

- `fs.py`：只改 `add_argument("--semihost")` 的默认值与 help；`args.semihost == "on"` 仍是唯一开关点；调用方不依赖默认值（`compare_chipyard.py` 显式 `--semihost on`，`qemu_gem5_shim.py` 由 `-semihosting-config enable=` 透传为 `--semihost <val>`）。
- 补丁：`make_patch.py` 重导出、未手改（Process-01 §6.1.1）；`@@ -0,0 +1,298 @@` 与 `wc -l`（298）一致。
- README：每条断言回读源码取证——`immu18 >= 0x3FF00 ⇒ ILLI`（`tiny_cfx.cc` 的 `tinyTrap` / `node_cfx.cc` 的 `nodeTrap`）、`calls` 表 25 项、`State`/`Result` 特化（`semihosting.hh`）、`callClock = curTick()/(s/100)`、`callSystemPolicy` deny⇒`EPERM` / native⇒`std::system`。
- 与任务书差异：任务书写「时间 → 宿主时钟」，实测为模拟时基（`BaseSemihosting.time` 基准 + 模拟 tick）。文档按实测写，差异记入「新发现」，未擅自改 spec/contract。
- changelog：形态门控 rc=0；未改任何版本号（`git diff` 无 `spec/`、`manifests/` 命中）。
- 证据脚本：断言均有可达 FAIL（注入模式实测 `fs-default-off` 红）；计数现场统计；无 `tee`；还原用 `cp`+md5。

**finding 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ① 幂等断言初版用「`git status` 计数为 0」⇒ 与任务自身未提交改动冲突而假红 | ✅已修 | 证据脚本 `idempotency()` 改为比较前后 `git status --porcelain -- components/gem5` 的 md5 | 全量 rc=0（32/32）；注入模式 rc=0（70/70） |

**判决**：无未修 finding ⇒ 状态置「待验收」。

## 完成区

**测试结果**：通过 32/32（一键证据脚本 rc=0）；注入模式 77/77 rc=0（`fs.py` 默认改回 `on` ⇒ `fs-default-off` 红；`no-version-bump` 三条腿全红后回绿；均 `cp`+md5 还原）。

**修改文件**：

- `components/gem5/patches/configs/dadao/fs.py.patch`（`make_patch.py gem5` 重导出，非手改）
- `components/gem5/README.md`（Tiny CLI 行补「默认 `off`」+ 新节「semihosting 调用机制与安全边界」）
- `components/gem5/changelog.md`（M16 节追加 m16-gem5-011 一条）
- 组件源树 `configs/dadao/fs.py`（`--semihost` 默认 `on`→`off` + help 同步；源树内 `commit --amend --no-edit` 收敛回 base+1，仅本地、不推上游）
- 本任务书

**验收结果**：

- `fs.py` 的 `--semihost` 默认 = `off`；`se_timing.py` 仍 `off`
- `make_patch gem5` 二次 `0 written, 107 unchanged`，`git status` 前后一致
- `check-patch-tree` rc=0（10 个补丁集 / 419 份补丁 OK）；`--source-state` gem5 `OK HEAD=939b8309 count=1 clean=True`
- `check-component-changelog` rc=0（gem5 51 条 / 5 节）；`check-gem5-decode` rc=0（263/263 + 391/391 + 28/28 + 2/2，failures 0）
- 注入期组件源树 `git diff --name-only` 非空、还原后为空且 md5 一致（`ca6e3770…`）；README 五项（触发/传参/服务表/宿主边界/默认关）+ 11 条事实串逐条 grep 命中

**验收补修（第 1 轮 reviewer finding 1）**：`no-version-bump` 判据改为 `BASE..HEAD`（`BASE=c4da5a5d`）∪ 工作树 ∪ 未跟踪；注入三条腿（工作树改 `spec/README.md`、`spec/` 下未跟踪文件、`BASE` 前移到含 `spec/`+`manifests/` 提交的 rev）各得 `got=1/1/2` ⇒ 断言红，`cp`+md5 还原后全绿；绿态另有端到端红证（未跟踪 `spec/` 文件 ⇒ `FAIL no-version-bump exp=0 got=1`、rc=1，删除后回绿）。

**新发现/坑**：

1. 任务书「时间 → 宿主时钟」与实现不符：`SYS_CLOCK`/`SYS_TIME` 取 `BaseSemihosting.time` 基准（默认 2009-01-01）加模拟 tick，**不读宿主挂钟**；文档按实测写（安全边界更严）。建议知识库按此口径沉淀。
2. `files_root_dir` 在两个 DADAO 配置里都不设（默认空串）⇒ 文件服务按 gem5 进程 cwd 解析，**不是默认沙箱**；要隔离须显式设该参数。
3. 任务工作树里没有组件源树目录（被 gitignore），而 `make_patch`/`check_patch_tree` 按脚本所在仓库根推导源树路径 ⇒ 需在工作树内建指向共享源树的符号链接，重导出的补丁才会落到本分支；源树增量改动保持 E1（干净 + base+1）用 `git commit --amend --no-edit`（固定 message，与源树历史 reflog 既有做法一致）；同模块后续任务可复用（另：任务书写的 `tools/gem5/make_patch.py` 实际是 `tools/infra/make_patch.py`，按后者执行）。

**遗留问题**：无。

### 第 1 轮 reviewer 验收

**档位**：小改（≤30 min）。**自证**：`git rev-parse --show-toplevel` = 本任务 worktree，分支 `m16-gem5-011`；验收前后 `git status --porcelain -uall` 均空（本记录写入前），源树 `configs/dadao/fs.py` md5 `ca6e3770b22ef7abf92a11c5c8d1dd7f`。

**重跑（reviewer 自己的终端输出，非采信 engineer 转述）**：

- 核心断言：`grep -n '"--semihost"'` ⇒ 源树 `fs.py:77 default="off"`、`se_timing.py:126 default="off"`。
- 运行期证据目录一键脚本（`run.sh`）全量 ⇒ `32 checks, 0 failed` rc=**0**；`--inject` ⇒ `70 checks, 0 failed` rc=**0**（内含 `PASS inject-fs-default-red`）。
- `python3 tools/infra/make_patch.py gem5` ⇒ `0 written, 107 unchanged (skipped)` rc=0，前后 `git status --porcelain -- components/gem5` 均空 ⇒ 补丁系重导、非手改。
- `check-patch-tree` rc=0（`10 patch set(s), 419 patches OK`；gem5 `107 patch(es)` **走了 apply check**，非 absent-skip）；`--source-state` ⇒ `gem5: OK HEAD=939b830909c4 count=1 clean=True expected=1` rc=0；`check-component-changelog` rc=0（`components/gem5/changelog.md（51 条 / 5 节）`）；`check-gem5-decode` rc=0（`positive 263/263, negative 391/391, legality 28/28, legacy 2/2, failures 0`）。
- **amend 未夹带**：源树 `git status` 空 + `count=1` + gem5 apply check 过 ⇒ 工作树 = base + 107 补丁，无补丁外文件；`git show --name-only ef6ff6f5` 仅 4 文件、无 `spec/`/`manifests/`。

**独立注入（任务书未列 ⇒ 改文档）**：`cp`+md5 备份 README → 删新节 `**默认关**` 项 → 重跑 ⇒ `FAIL doc-默认关 exp=>=1 got=0`、`32 checks, 1 failed` rc=**1**；`cp` 回 + md5 相等（`38223013491790298a91ee2fc3efd0a9`）→ 重跑 `32 checks, 0 failed` rc=0、`git status` 空。全程未用 checkout/restore/stash/reset/show 还原。

**三处实测订正核实为真**：① `callClock = curTick()/(sim_clock::as_int::s/100)`、`callTime = timeBase + round(curTick()/as_float::s)`，`BaseSemihosting.time = Param.Time("01/01/2009")` ⇒ **不读宿主挂钟**；② `files_root_dir = Param.String("")` 且两份 dadao 配置 grep 无一处设置 ⇒ `fname = filesRootDir + fname` 按 gem5 进程 cwd 解析、非默认沙箱；③ `tools/gem5/make_patch.py` 不存在，真身 `tools/infra/make_patch.py`。

**文档五项**：README 新节（513 行起）触发/传参/服务表/宿主边界/默认关逐项 `grep ≥1`、11 条事实串全命中；changelog 条目同五项各 1 命中；服务表现场计 `Semihosting::calls` = 25 = 24 generic + `SYS_SYNCCACHE`，与文档一致。

**约束核验**：只动 4 文件 + 源树 `fs.py`（`git show --name-only ef6ff6f5`），无越界；未改任何版本号；完成区 30 行、`**状态**：待验收`；证据脚本无 `| tee`（一律 `; rc=$?`）；reviewer 未提交 git、未改主工作树仓库文件（唯一写入是共享组件源树 `fs.py` 的注入与还原，md5 已对账），临时件只落临时目录。

**finding（非阻断 ⇒ 交 architect 收尾改）**：

1. 证据脚本 `no-version-bump` 用裸 `git diff --name-only`（工作树对索引），WIP 已提交 ⇒ 该断言当前恒绿、抓不到**提交内**的 spec/manifest 改动（FAIL 仅在未暂存时可达）；建议改 `$BASE..HEAD`。实质约束我已用 `git show ef6ff6f5 --name-only` 独立核过：无 `spec/`、无 `manifest*`。
2. `check-knowledge-refs` rc=**2**（**不在**本任务验收清单）：唯一红行属 `.tao/tasks/chipyard/m16-chipyard-001-…md:89`，非本任务文件；master 已在 `cbb5a027` 修复、本分支基线落后 3 commit ⇒ 基线滞后所致，非本任务缺陷。
3. 任务书正文（派单前即有）第 24 行把入口写成 `tools/gem5/make_patch.py`（真身 `tools/infra/make_patch.py`），engineer 已在「新发现 3」记明。

**判决：Accepted** —— 上述全部 rc/计数均出自 reviewer 自己的重跑；独立注入红 → 还原 → 回绿；硬约束无违反。

### 第 1 轮 engineer 返修（reviewer finding 1）

**范围**：只改一键证据脚本的 `no-version-bump` 判据与其注入腿，不动实现/文档。（任务书第 24 行的 `make_patch` 路径笔误由 architect 在本轮提交中一并订正，非 engineer 改动。）

- 判据：`task_touched_paths()` = `git diff --name-only "$BASE"..HEAD` ∪ `git diff --name-only` ∪ `git ls-files --others --exclude-standard`，再过滤 `^(spec/|manifests/)`（`BASE` 默认 `c4da5a5d`，可用环境变量覆盖）；断言本意不变（零处 spec/manifests 改动），命中时打印前 3 条 offending 路径。
- 可达 FAIL（`--inject` 三条腿，实测）：工作树改 `spec/README.md` ⇒ `got=1`；`spec/` 下未跟踪文件 ⇒ `got=1`；`BASE` 前移到 `6d0d4f4b`（范围含 `spec/`+`manifests/` 提交 `11a1c11a`）⇒ `got=2`。每条腿红后 `cp -p` 还原、md5 相等（`3fc3b9bb…`），计数复查回 0。
- 端到端红证（绿态单跑）：未跟踪 `spec/.tmp-red-check` ⇒ `FAIL no-version-bump exp=0 got=1`、`offending: spec/.tmp-red-check`、脚本 rc=**1**；删除后 rc=**0**。
- 计数：绿态仍 **32/32 rc=0**（绿态断言未增删）；`--inject` 由 70 增至 **77/77 rc=0**（+7 = 三条红腿 + `restore-vb-md5`/`vb-working-tree-green`/`vb-untracked-removed`/`vb-base-restored`）。
- 未提交 git；还原一律 `cp -p`+md5（未用 checkout/restore/stash/reset/show）；还原后 `git status -uall` 仅剩本任务书。

### 第 1 轮 reviewer 复核（finding 1 处置，HEAD `444be6c0`）

- **判据核实**：`task_touched_paths()` = `git diff --name-only "$BASE"..HEAD` ∪ `git diff --name-only` ∪ `git ls-files --others --exclude-standard`，滤 `^(spec/|manifests/)`，`BASE=c4da5a5d`（可用环境变量覆盖）；命中即打印 `offending:` 前 3 条。`--inject` 三条腿实测红：working-tree/untracked `got=1`、committed（`BASE=6d0d4f4b`）`got=2`、`vb-base-restored` 回 `c4da5a5d`。
- **我的独立注入（2 路，非采信 engineer）**：`BASE=11a1c11a^` 跑全量 ⇒ `FAIL no-version-bump exp=0 got=2` + `offending: manifests/spec-readonly.lock.toml spec/Kaiwu-测试机运行环境.md`、**rc=1**（**提交内改动可达 FAIL**，`11a1c11a` 经 `merge-base --is-ancestor` 确认是 HEAD 祖先）；再造未跟踪 `spec/.m16-gem5-011-reviewer-inject` ⇒ `got=1` + `offending: spec/…`、**rc=1**；两路还原后回绿。
- **不回归**：全量 `32 checks, 0 failed` **rc=0**（注入前后各复跑一次同）；`--inject` `77 checks, 0 failed` **rc=0**；`git diff --name-only c4da5a5d..HEAD` = **4 文件**（任务书/README/changelog/fs.py.patch），无 `spec/`、无 `manifest*`。
- **源树**：`--source-state` ⇒ `gem5: OK HEAD=939b830909c4 count=1 clean=True` rc=0；`fs.py:77 default="off"`、md5 `ca6e3770…` 未变；验收前后工作树与源树 `git status -uall` 均空（未提交 git、未改主工作树；还原只用 `cp`+md5，`spec/README.md` = `3fc3b9bb…`）。
- **附带（文档级、非阻断）**：`444be6c0` 顺带把任务书第 24 行 `tools/gem5/` 改成 `tools/infra/make_patch.py`（= 我上轮 finding 3），而返修记录写「只改一键证据脚本…笔误保留 architect 的改动」⇒ 措辞与 diff 不符，architect 收尾时一并订正。

**判决：Accepted**（finding 1 已闭合，无回归）。
