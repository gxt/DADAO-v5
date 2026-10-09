# INFRA-051t: Embench 组件接入（组件化 + `enabled`）

**模块**：infra
**项目里程碑**：M6
**依赖**：`SPEC-122t`（Embench 上游选择 ADR，拟 `adr-0022`，须 `Accepted`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 已 `Accepted` 的 Embench 上游选择 ADR（`SPEC-122t` 产出，拟 `.tao/adr/adr-0022-*.md`：记录上游仓库 + 精确 commit）。
  - `manifests/components.lock.toml`（现有组件锁体例；`ADR-0005` 多源锁）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（树形补丁集 + 一文件一补丁）。
  - 现 `make fetch` 机制（落 `.work/source/<name>/`）。
- **输出**：
  1. `manifests/components.lock.toml`：Embench 条目 **翻 `enabled = true`**（`name`/`repository`/精确 commit 与 ADR 一致；标识符 = 原始仓库名，`MEMORY.md` 决策）。
  2. `components/embench-iot/{patches/**,series,changelog.md}`：**骨架**（`patches/` 树形补丁集 + `series` 清单 + `changelog.md`；本任务只建骨架，board shim/运行时的**实现**归 `TESTCASES-039t`）。
  3. **工作树**：`make fetch` 生成 `.work/source/embench-iot`（gitignored）。
- **约束**：
  - **ADR 未 `Accepted` 前不进实现**（`Process-03`）。
  - 与 `INFRA-050t` **同改 `Makefile`/`manifests` ⇒ 串行**。
  - 补丁集组织/生成/应用/校验以 `Process-01` 为准（`make check` 的 `check-patch-tree` 机械校验）。
  - 只建**骨架**；不提前引入 board shim/运行时实现（那属 `TESTCASES-039t`）。

## 硬约束

- **临时目录** `/tmp/opencode/INFRA-051t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**（涉 `components/**` 者）：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿（新组件须入校验）。
- **一键证据脚本** `.work/evidence/INFRA-051t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：`make fetch` 若需克隆/下载 Embench（网络）须先申报；**禁**自行选定镜像/开始下载，按 `AGENTS.md`「大文件下载与镜像」由用户定。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/infra/INFRA-051t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **锁条目启用**：`manifests/components.lock.toml` 的 Embench 条目 `enabled = true`，且 `name`/`repository`/commit 与 ADR **逐字一致**（给 `grep` 真实输出）。
2. **骨架存在**：`components/embench-iot/{patches/**,series,changelog.md}` 存在（给 `ls`/`find` 输出）。
3. **工作树生成**：`make fetch` EXIT=0，`.work/source/embench-iot` 存在且 HEAD == 锁定 commit（给真实输出）。
4. **门控**：`make check` EXIT=0（含 `check-patch-tree` 断言⑥，新组件纳入校验）。
5. **一键证据脚本**：`.work/evidence/INFRA-051t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把 `enabled` 改回 `false` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`manifests/components.lock.toml` + `components/embench-iot/**` + 本任务书）；`.work/` 生成物不暴露；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：全部通过。`make check` EXIT=0（`check-patch-tree` 3 components / 106 patches；`check-index-blobs` 80 new-file OK；`check-source-state` 三组件 OK）；证据脚本 13/13 PASS、`RUN_EXIT=0`（`.work/log/infra/INFRA-051t-evidence.log`）。

**修改文件**（`git status --porcelain -uall` 仅此 + 本任务书）：
- `manifests/components.lock.toml`（embench-iot 条目：`enabled false→true`、`commit ""→"09c2ed8c…70"`、删过时注释；其它组件零改）
- `components/embench-iot/README.md`、`changelog.md`、`series`（均新）
- `components/embench-iot/patches/examples/dadao/README.md.patch`（新；最小占位，声明无行为）

**验收结果**（真实输出见 `.work/log/infra/INFRA-051t-*`）：
- ① 锁条目 `enabled=True` + commit `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` + repo `https://github.com/embench/embench-iot.git`，与 `ADR-0022 D1/D2` **逐字相等**；`git diff --name-only` 仅 `manifests/components.lock.toml`（其它组件零改）。
- ② `make fetch` EXIT=0；**不联网**——本地镜像 `.cache/embench-iot.git` 本就含该 commit（日志 `mirror embench-iot.git already has 09c2ed8c3b70; skipping fetch`）。fresh fetch 后 `.work/source/embench-iot` `git rev-parse HEAD` = `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`（== 锁定基线）。
- ③ 幂等：连跑两次 `make fetch` 均 EXIT=0，第二次无 `Cloning`（仅 `… already at …`）。
- ④ 门控：`make check` / `check-patch-tree` EXIT=0（见「遗留问题」矛盾与处置）。
- ⑤ 证据脚本 `.work/evidence/INFRA-051t/run.sh`：13/13 PASS、`RUN_EXIT=0`；含注入自检 A（manifest commit 改错 ⇒ lock 检查与 `check-patch-tree` FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）、B（patch index hash 改错 ⇒ `check-index-blobs` FAIL ⇒ 还原 ⇒ 回绿），md5 逐项相等。
- ⑥ 无残留：`git status --porcelain -uall` 仅本任务改动；`check-no-residue` PASS；无 `*_tmp*`/`*.orig`/`*.rej`。

**新发现/坑**：
- `check_patch_tree.py` 对 **enabled 组件硬性拒绝空 `series`**（`series is empty`，EXIT=1）；且 `.work/source` 存在时断言⑦⑧要求 `base+1` ⇒ enabled 组件必须「有 ≥1 有效补丁且已 apply」。故「enabled + 空骨架」无法过门控。
- `make fetch` 对「已 apply（HEAD 以 base 为祖先）」的组件经 `merge-base --is-ancestor` 判定后**保持不动**（不覆盖已应用补丁）⇒ 幂等安全。
- 首次 `make fetch` 从**本地镜像**克隆（硬链接），**零网络**。

**遗留问题**：任务书验收③（`HEAD==锁定 commit`）与④（门控绿）**同刻不可并存**——`.work/source` 停在基线时断言⑧失败。经用户 2026-10-09 裁定「放 1 个最小占位补丁」：骨架含 1 个**非 shim/运行时**占位补丁（`examples/dadao/README.md`），`make apply-series` 后 `.work/source/embench-iot`=base+1（干净）⇒ 门控绿。board shim/最小运行时仍归 `TESTCASES-039t`（本任务未引入）。此外无遗留。

> **主会话 2026-10-09 复核确认（`lessons §7.3`）**：用户确认「放 1 个最小占位补丁」裁定属实、保持。
>
> **（对齐 reviewer 非阻塞建议）** 验收③措辞（`HEAD==锁定 commit`）与实际 `base+1` 的关系：**enabled 组件要求 `≥1` 补丁且已 apply**（`check_patch_tree` 硬约束）。

## 审阅记录

#### 第 1 轮 engineer 自审

**改动逐行审查**：
- `manifests/components.lock.toml`：仅 embench-iot 条目被改；`name`/`repository`/`patch_dir`/`patch_series`/`role` 未变；`enabled`/`commit` 与 `ADR-0022 D1/D2` 逐字一致；删的两行注释是已填 commit 后失效的占位说明。其余组件零改（`git diff --name-only` 仅本文件）。
- `components/embench-iot/patches/examples/dadao/README.md.patch`：裸 `git diff --cached`（无邮件头）；恰一个 `diff --git`；`new file mode` + 有效 hunk（`@@ -0,0 +1,9 @@`，9 行）；index 新 hash `b906f14` 经 `check-index-blobs` 独立重算一致；断言⑥（应用产物 vs 工作树）green。
- `series`：单条、相对 `patches/`、字典序（平凡）；`patches/` 纯镜像（仅 `*.patch`）。
- `README.md` / `changelog.md`：依 `Process-01 §2/§10` 体例（对齐 qemu 组件）。
- 占位内容**声明无行为**、明示 board shim/运行时归 `TESTCASES-039t`（未提前引入实现）。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书③与④同刻不可并存（enabled + 空骨架不可过门控） | ✅已修（按用户裁定） | 加 1 个最小占位补丁 + `make apply-series`（`.work/source`=base+1） | 证据脚本 13/13 PASS、`make check` EXIT=0；矛盾在完成区②④注明 |
| F2 空 `series` 被门控硬拒 | ✅已报告 | —（门控不改，超本任务范围） | 实测 `series is empty` EXIT=1（`check-patch-tree-base.log` + 注入日志） |
| F3 证据脚本 stray 过滤用子串匹配 | ❌不修（可接受） | — | 另有 `check-no-residue` PASS 兜底；脚本 `no-stray-changes` PASS |
| F4 占位路径 `examples/dadao/README.md` 可能与 `039t` 重叠 | ⏸延后（已报） | — | 与 039t 的 `boardsupport.c` 无同名冲突；记入完成区「新发现/坑」 |

**判决**：F1/F2 已按用户裁定处置；无未修阻塞项 ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（独立执行，真实输出/退出码；完整日志 `/tmp/opencode/INFRA-051t-review/`）：
1. **锁**：`git diff manifests/components.lock.toml` 仅 1 hunk（embench-iot 条目：`enabled false→true`、`commit ""→"09c2ed8c3b7008c95d08b038de4a3f6dc103ed70"`、删 2 行过时注释）；`name`/`repository`/`patch_dir`/`patch_series`/`role` 逐字未变；其它组件条目零改（rc=0）。独立比对 `.tao/adr/adr-0022-embench-upstream.md`（状态 Accepted）：D1 `https://github.com/embench/embench-iot.git`、D2 `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` 与锁条目**逐字相等**。
2. **骨架只骨架**：`find components/embench-iot -type f` = README.md / changelog.md / series / patches/examples/dadao/README.md.patch（4 文件）；`grep -rniE 'boardsupport|initialise_board|mem(set|cpy)|sqrt'` 仅命中 README/补丁中的**声明性提及**（无实现文件）。占位补丁全文仅 `new file examples/dadao/README.md`（9 行声明文，明示「This file declares no behaviour」「board shim/运行时由 TESTCASES-039t 添加」）；临时树 `git clone .cache/embench-iot.git`（HEAD=09c2ed8c…）上 `git apply --check` **EXIT=0** 干净应用。
3. **`make fetch`×2**：均 **EXIT=0**，两次输出一致——`fetch: mirror embench-iot.git already has 09c2ed8c3b70; skipping fetch` + `embench-iot HEAD (6702d6c64560) already has 09c2ed8c3b70 as an ancestor … leaving it alone`，第二次无 `Cloning` ⇒ **幂等**；**零联网**（`.cache/embench-iot.git` `git cat-file -e 09c2ed8c…^{commit}` EXIT=0 本就含该 commit）。`.work/source/embench-iot`：HEAD=`6702d6c`（`dadao: embench-iot patch series`，父=09c2ed8）= **base+1**，`rev-list --count 09c2ed8..HEAD`=1，`git status --porcelain` 空 ⇒ 与「apply-series 后 = base+1」自洽（与任务书③「HEAD==锁定 commit」的矛盾已按用户 2026-10-09 裁定处置，见遗留问题）。
4. **门控**：`make check` **EXIT=0**，含 `check-patch-tree: 3 component(s), 106 patches OK`、`check-index-blobs: 80 new-file patch(es) OK`、`check-no-residue: PASS`。现场计数：`find components/*/patches -name '*.patch' | wc -l`=**106**、embench 侧=**1** ⇒ 改前 105 → +1，与 engineer 报数一致。
5. **独立注入（与 A/B 不同）**：`cp series series.preinject`（md5 `d1f1572…7309`）→ 清空 `series`（md5 `d41d8cd…`）→ `check_patch_tree.py` **EXIT=1**，输出 `check-patch-tree: embench-iot: series is empty`（符合预期 FAIL）→ `cp` 还原（md5 `d1f1572…7309` 逐字相等）→ `check_patch_tree.py` **EXIT=0** `3 component(s), 106 patches OK` 回绿。
6. **证据脚本**：审 `.work/evidence/INFRA-051t/run.sh`（176 行）——逐项 `report` 打印「名|期望|实际|rc」、任一失败 `overall=1` 非零退出、注入 A/B 均「mutate 非零 rc → `cp`+md5 相等 → recheck rc=0」、无 `tee`（`cmd >log 2>&1; rc=$?` 捕获自身退出码）、`trap restore_all EXIT` 兜底、注入有效（A/B 的 mutate rc≠0 证明改动生效）。重跑：**13/13 PASS、RUN_EXIT=0**（含 `make check` rc=0、fetch 幂等 rc1=0/rc2=0/clone2=no、inject-A/B `md5_equal=yes`）。
7. **无残留**：`git status --porcelain -uall` 仅 `manifests/components.lock.toml`(M) + `components/embench-iot/{README.md,changelog.md,series,patches/examples/dadao/README.md.patch}`(??) + 本任务书(M)，与完成区「修改文件」声明**逐行对账一致**；`git diff --name-only origin/master...HEAD` 空（未提交，符合「不提交 git」）、`grep -E '^(spec|contracts)/'` **无命中**；其它 `components/**` `git diff --name-only | grep -v embench-iot` **无命中**；`_tmp/_orig/_rej` 无命中。注入已还原（md5 对账相等，见 5）。

**约束核验**：临时目录 `/tmp/opencode/INFRA-051t-review/`（仅读审）✓；未提交 git ✓；只审未改 ✓；`series` 注入已 `cp`+md5 还原（未用 checkout/restore/stash）✓；门控绿 ✓；占位补丁声明无行为、未越界引入 board shim/运行时（归 `TESTCASES-039t`）✓；用户裁定「1 个最小占位补丁」实施真实（补丁全文 + 幂等 fetch + base+1 自洽均已独立复核）✓。计数均由现场脚本统计，未写死。

**问题**：无阻塞项。非阻塞备注：① 任务书验收③「HEAD==锁定 commit」表述与实际 base+1 的矛盾已按用户裁定处置并记录（遗留问题段），建议后续任务书措辞对齐「apply-series 后 = base+1」；② 证据脚本 `no-stray-changes` 用子串过滤（engineer F3 自评可接受），有 `check-no-residue` 兜底，不阻塞。

**判决：Accepted**（1–7 全部以本人独立重跑的真实输出/退出码核验通过，注入 FAIL→还原→回绿成立，约束无违反）。
