# INFRA-099t: 门控/安装根写者互斥制度化（`ISS-229`）

**模块**：infra
**项目里程碑**：M9
**依赖**：`INFRA-096t`（安装根新鲜度门控，`待验收`）、`INFRA-093t`（运行产物/日志规矩，已验证）、`QEMU-066t`（`ISS-300` 手工 `cp` 例外手法登记源，`待验收`）、`INFRA-097t`/`INFRA-098t`（**同改 `Makefile`，须串行**）
**状态**：已验证

> **编号（现场取号，2026-10-20）**：`infra` 现存最大 = `INFRA-096t`（本批另占 `097`/`098`）⇒ 取 **`099`**（编写前 `grep -rn 'INFRA-099' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实

- **`ISS-229` 现场（假 FAIL）**：`L2`（`make check-modules`）与 `L3`（`make check-full`）在同一工作树**并发** ⇒ `L3_EXIT=2`、Embench `37/38`，失败例报 `stddef.h not found`（读瞬态不完整的安装根）；错开单跑 ⇒ `L3_EXIT=0`、`38/38`。同类：手动 `make build-mc` 与 L2 内的 `install-host→build-mc` 并发 ⇒ 构建树被写坏（`clang-23` 异常膨胀 / segfault，`LLVM-094t` 阶段 A 现场）。
- **现状（只靠注释）**：`Makefile:316-320` 的 `NOTE (concurrency)` 明写「只把 `install-host` 的**写侧**做成 race-safe（`INFRA-053t`/`ISS-172`）；同一工作树并发跑 **gate** targets 仍 **UNSUPPORTED**（共享 build trees 与 SDK artifact dirs）」；`AGENTS.md`「并行任务上限」「长任务」有纪律文字 ⇒ **不可机械判**。
- **目标关系（易踩）**：`Makefile:588 check`（L1）、`:595 check-modules:`（L2）、`:599 check-full: check-qemu-semantics test-m6`（L3）、`:899 test-semihost: install-host build-bootrom test-elf test-codegen check`、`:424 install-host: build-mc build-lld build-qemu build-builtins` ⇒ **嵌套链极深**（`check-modules → test-semihost → install-host/check/build-bootrom`，`check-full → test-m6 → check-lit-full`）。**任何互斥机制都必须允许「同一 make 树内的嵌套」**，否则必死锁。
- **契约/规范落点**：`docs/Process-07 §2`（触发点）、`§3`（新检查定层）、`Makefile:316-320` 注释、`AGENTS.md`「并行任务上限」「长任务」（≤2 行指针）；`ISS-300`（安装根例外手法应收编，本册只做互斥、**不替代**新鲜度检查）；`ISS-210`（旧安装根假绿）。

## 接口规范

- **输入**：`Makefile`（写者目标：`install-host`/`build-*`/`check`/`check-modules`/`check-full`/`test-*` 等）、`tools/infra/**`（若落脚本）、`docs/Process-07`、`AGENTS.md`。
- **输出**：
  1. **机械互斥**：对「会写 `.work/build/**`、安装根 `.dadao/**`、SDK 产物目录」的**顶层**目标加互斥（`flock` 或等价；实现自选，须先诊断嵌套关系）；第二个**独立**进程要么等待（有界）要么 fail-fast 并打印「谁持有锁 / 锁路径 / PID」；
  2. 嵌套**不误伤**：同一 make 树内 `check-modules → test-semihost → install-host/check`、`check-full → check-qemu-semantics + test-m6` 全部实测通过；
  3. 文档：`docs/Process-07 §2` 增「互斥（MUST）」条；`Makefile:316-320` NOTE 由「UNSUPPORTED」订正为「由锁保证」；`AGENTS.md` 对应条 1 行指针；
  4. 证据 `.work/evidence/<任务ID>/run.sh`（含并发探针与自测）+ 日志 `.work/log/infra/INFRA-099t-*.log`。
- **约束**：**不改** `spec/` / `contracts/` / `.tao/contracts/**` / `components/**` / `tests/vectors/**`；不改任何门控的**判定语义**（只加互斥）；不 commit/push；**不跑** L3 全量作为本册验收（用 L2 + 并发探针即可）。

## 验收标准

1. **互斥可判（核心）**：两个**独立** shell 同时启动写者（至少覆盖 `check-modules` + `install-host`；再覆盖 `build-builtins` + `check` 组合）⇒ 不出现交错写；被拒/等待方有明确提示；串行复跑两者 **rc=0**；给出两进程的起止时间戳 + 日志。
2. **fail-fast/等待语义**：等待须有上界（可配置）且超时给出明确诊断；fail-fast 须 rc≠0 + 提示持有者信息；**不得**静默无限阻塞。
3. **嵌套不死锁**：`make check-modules` 单独跑 rc=0（内含 `test-semihost → install-host/check`）；`make check-full` 的**前置互斥**场景下不因嵌套自锁（若 L3 太慢，可只跑 `check-qemu-semantics` + `test-m6` 的嵌套子集或 `make -n` + 单目标实测，但须有真实执行证据说明无自锁）。
4. **异常面**：锁文件路径不可写 / 锁工具缺失 ⇒ 显式 FAIL（不得静默跳过互斥）；给出实测输出。
5. **可达 FAIL ≥ 2**（真实输出 + 还原回绿）：
   - (a) **并发探针**：两进程同时进 ⇒ 互斥触发器确实生效（而非巧合串行）；用「持有锁 N 秒」的探针让窗口稳定可观测；
   - (b) **注入去掉互斥**（临时树）⇒ 探针观察到两进程重叠（时间戳/锁未持有时写者并行）⇒ 判据可失败；**不得**在真实工作树制造构建树损坏，可用文件级写探针（同一路径写 marker）替代；
   - (c) **自测**：若落脚本，须有 `--self-test`，覆盖「同树嵌套允许 / 独立进程拒绝 / 锁不可用报错」三类注入。
6. **文档一致**：`Process-07`/`Makefile` NOTE/`AGENTS.md` 三处措辞与实现一致（机械可 grep 对齐）；不改判定语义（门控 rc 含义、用例分类不变）。
7. **回归**：`make check`(L1) rc=0；`make check-modules`(L2) rc=0；`check-run-artifacts` / `check-no-residue` rc=0；`check-milestones-fresh` rc=0。
8. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-229` 回填（`closed` + `resolved_by: INFRA-099t`；若与 `ISS-300` 有交叉，注记边界）。
9. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-099t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（是否引入外部 `flock` 依赖 / 是否把互斥做成独立门控层）时留问。
6. 复杂命令输出留 `.work/log/infra/`；并发探针用短任务（`check` L1 或文件级写探针），**不得**并发跑完整 L3 制造损坏。

## 完成区

**测试结果**（日志 `.work/log/infra/INFRA-099t-*.log`；证据 `.work/evidence/INFRA-099t/{run.sh,probe.mk,serialization_check.py}`）：
- `gate_lock.py --self-test` = **8/8 PASS**（嵌套放行 / 陈旧标记仍取锁 / 独立进程 rc=75 / failfast 0.08 s / 有界等待 / 锁不可用 rc=69 且拒跑 / 释放后重取）；主会话独立复跑同结果。
- **真并发 ㈠**（主会话亲跑，非探针）：`make check-modules` 与 `make install-host` 同起 ⇒ A rc=0 / 413 s、B rc=0 / 471 s；B 打印 `WAIT … held by … target=check-modules` 后排队（取得锁后实际工作 63 s）。
- **真并发 ㈡**（强制争用）：`gate_lock.py … -- sleep 45` 持锁，同起 `build-builtins` / `check` ⇒ 两者各打印 `WAIT … target=probe`、rc=0（46 s / 81 s），串行无交错。
- `make check`(L1) rc=0；`make check-modules`(L2) rc=0（8 m 13 s，实计 41 次嵌套放行，无自锁）。
- 可达 FAIL：注入（临时 `Makefile` 副本 + md5 对账）去掉互斥 ⇒ `overlap=yes`、串行判据 rc=1；真 `Makefile` 复跑 ⇒ `overlap=no` 回绿。锁不可用 ⇒ rc=69 且目标体零执行；failfast ⇒ rc=75 + 持有者信息。
**修改文件**：`Makefile`（29 个 `GATE_LOCKED_TARGETS` + `gate-locked` 重入 + `_locked-*` 体 + NOTE 订正）、`tools/infra/gate_lock.py`（新增 480 行）、`docs/Process-07-门控分层规范.md`（§2 互斥 MUST）、`AGENTS.md`（1 行指针）、**本册**（完成区/状态）、`.tao/knowledge/milestones.md`（任务流水行状态）、`.tao/knowledge/issues.yaml`（`ISS-229` closed 回填 + 关闭依据/边界注记）。
**验收结果**：9 条验收逐条命中；`check-run-artifacts` / `check-no-residue` / `check-milestones-fresh` 均 rc=0。
**新发现/坑**：① **只锁 recipe 无效** —— `install-host` 的**前置**才是写者 ⇒ 必须重入 `_locked-<t>`；② `close_fds=False` 保 jobserver，否则 `make -jN` 在子 make 退化 `-j1`；③ 无 `/proc` 时祖先校验降级为信任标记（自测报 SKIP，已在 docstring 披露）；④ 内核已放锁但 JSON 持有者记录残留 ⇒ 须标 `[stale: process gone]`。
**遗留问题**：互斥范围 = **同一工作树**（锁文件 `<repo>/.dadao/gate.lock`）；不同 `git worktree` 之间不互斥（符合本册语义，跨树串行需另议）。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收

**判决：Needs Revision** —— 9 条中 8 条在我自己的重跑下命中；**#8 后半未落**（`issues.yaml` 的 `ISS-229` 仍 `open`/`resolved_by: null`）+ 完成区「修改文件」与 `git show --stat` 对账漏 2 项。日志/证据全在 `/tmp/opencode/INFRA-099t-review/`（临时区，不入仓）。

**独立重跑（rc 一律取被检命令自身）**
1. `python3 tools/infra/gate_lock.py --self-test` ⇒ `self-test: 8/8 PASS`、**rc=0**（`selftest.log`）。
2. `.work/evidence/INFRA-099t/run.sh`（`847b76ac` 后基线）⇒ `== RESULT: 11 checks, 0 failed ==`、**rc=0**（`evidence-3-baseline.log`）：C2 `now=29 gated=29 ungated=0`、C3 `checker rc=0 / B wall=5.08s`、C4 `checker rc=1`、C6 `tool rc=69 / make rc=2 / body-ran=no`、C7 `failfast rc=2 / wait rc=2`、C8 `make check rc=0 waited-for=target=probe-a`、C9 `rc=0 nested=41`、C11 `jobserver-warning=no`。修复前（`6fa530ae` 态）我先跑 = `11 checks, 2 failed, rc=1`（C8/C9 rc=2，根因 `check-milestones-fresh A1: L68 表=待开始 ≠ 任务书=待验收`）⇒ 由 `847b76ac` 修掉，我复跑该门控 **rc=0**。
3. **我自己的反例注入**（`cp Makefile …/Makefile.bak2` + md5，非 engineer 的 C4 副本法）：`gate-locked = ` 改回裸重入 `$(MAKE) -f … _locked-$(1)` ⇒ md5 `388b7ea6… → 3ca35291…`，同一脚本 ⇒ `11 checks, 8 failed`、**rc=1**（C2 `ungated=29`、C3/C5 `checker rc=1 overlap`、C6 `body-ran=yes`、C7 `failfast rc=0`、C8 `wait-msg=0`、C9 `nested=0`）；`cp` 还原 ⇒ `equal=YES` 回 `388b7ea6…`，复跑 ⇒ `0 failed`、**rc=0** 回绿（`evidence-45-driver.log` / `evidence-4-injected.log` / `evidence-5-restored.log`；全程未用 git checkout/restore/stash）。
4. 独立注入 ×3：伪造 `DADAO_GATE_LOCK_HELD` 而持有者非祖先 ⇒ `warning … no ancestor holds … acquiring normally` + **rc=75**、body 零执行；锁父为文件 / 目录 0555 / `fcntl=None` ⇒ 均 **rc=69** 且 body 零执行；临时副本改 `close_fds=True` + `make -j4` ⇒ `warning: jobserver unavailable: using -j1`（真 `gate_lock.py` md5 `970cc431…` 未变）。
5. **真并发（带时间戳）**：`21:10:06 gate_lock.py … target=probe -- sleep 20` 持锁 + `21:10:07 make check` ⇒ `gate-lock: WAIT … held by pid=1592898 … target=probe … waits up to 3600s` → `ACQUIRED after 18.6s` → `repository checks (L1): PASS`、**rc=0**、`21:11:04` 收（`contention.log`）。完成区真并发㈠/㈡ 盘上证据 = `/tmp/opencode/INFRA-099t/{A,B,E,F}.{log,meta}`：`A_EXIT=0/413s`、`B_EXIT=0/471s`、`E_EXIT=0/46s`、`F_EXIT=0/81s` + 各自 `WAIT … target=check-modules|probe` 行，与完成区数字逐条一致。
6. **回归**：`make check` **rc=0**（`l1-plain.log`）；`make check-modules` **rc=0**（`21:11:58→21:18:16`，**nested=41**，`l2-direct.log`）；`check-run-artifacts` rc=0（`A3 916 new file(s), 0 illegal, 5965 exempt`）、`check-no-residue` rc=0、`check-milestones-fresh` rc=0（`PASS 26 行`）——末轮三者复跑仍 rc=0。
7. **#3 嵌套（check-full 链，按册不跑 L3 全量）**：`GATE_LOCK=/tmp/…/full-dry.lock DADAO_GATE_LOCK_VERBOSE=1 make -n check-full` ⇒ **rc=0 + 9 次 `gate-lock: nested:` 放行**，命中 `_locked-check-full/test-m6/check-qemu-semantics/install-host`；单目标实测 `make check-qemu-semantics` ⇒ **rc=0**、`PASS（886/897，载体 19 册）`（13 s）。
8. **语义核验（防假绿）**：现场比对脚本 `prereq_diff.py` ⇒ **29/29** `GATE_LOCKED_TARGETS` 的 `_locked-<t>` 前置与原规则**逐字相同**（`mismatches=0 of 29`，无前置漏在锁外，含 `_locked-test-codegen: install-host` 走嵌套放行）；`gate-locked` 与 `+` 单点定义、`.PHONY` 含 29+29；C2/C9 计数均现场统计非写死；无遗漏写者（`build-gem5` 必失败骨架、`docker-image` 仓外、`fetch/apply-series/prepare` 写 `.work/source|.cache` 不属本册三目录口径 ⇒ 遗留）。

**约束核验**：写审阅记录前 `git status --porcelain -uall` = **0 行**；`6fa530ae~1..HEAD` 共 6 文件，禁改目录 `spec/ contracts/ components/ tests/vectors/ manifests/ .tao/contracts` **零改动**；未 `commit`/未 `push`；我的临时产物只落 `/tmp/opencode/INFRA-099t-review/`；开工/收尾 5 个目标文件 md5 **全等**（`diff md5-before md5-after` rc=0 ⇒ 注入确已还原）。

**Needs Revision（最小返工项，均可复现）**
- ① `grep -A4 '^- id: ISS-229' .tao/knowledge/issues.yaml` ⇒ `status: open`、`resolved_by: null`，而验收 #8 明文要求 `closed` + `resolved_by: INFRA-099t`（同批 `INFRA-096t/097t/098t` 均在 engineer 提交内回填）；完成区却称「9 条验收逐条命中」⇒ 与盘上事实不符。**改**：置 `closed` + `resolved_by: INFRA-099t`，notes 补关闭依据与 `ISS-300` 边界注记。
- ② `git show --name-only 6fa530ae 847b76ac` = 6 文件，完成区「修改文件」仅列 4 项 ⇒ 漏 **本册** 与 `.tao/knowledge/milestones.md`。**改**：完成区补列这两项。
- 遗留（不阻断）：`GATE_LOCK` 可被环境变量覆盖 ⇒ 定制 env 会静默分叉互斥面；互斥仅限同一工作树（完成区已披露）；L3 全量未跑（本册不要求）。

#### 第 2 轮 reviewer 验收

**判决：Needs Revision（唯一项、一行改）** —— 第 1 轮两项返工**均已落实**（`ISS-229` 已 `closed`+`resolved_by` 回填、完成区已补列本册与 `milestones.md`），L1/门控/工作树全绿；但完成区「修改文件」与 3 个提交的并集**仍差 1 项**：漏 `.tao/knowledge/issues.yaml`（`e1210cff` 把它带进并集、却没列进对账字段）。日志：`/tmp/opencode/INFRA-099t-review/r2-{l1,milestones-fresh,check-issues}.log`、`r2-union.txt`（临时区，不入仓）。

**重跑记录（rc 取被检命令自身；无 `| tee`；未用 `git checkout/restore/stash`）**
1. `git show --numstat e1210cff` ⇒ **2 files**（`issues.yaml` **4/3**、本册 **20/2**，合计 24+/5-）；`git show --name-only --format='' e1210cff | grep -E '^(Makefile|AGENTS\.md|tools/|docs/)'` ⇒ **0 命中** ⇒ 返工零触门控载体/文档/工具。
2. **证据复用理由**：`.work/evidence/INFRA-099t/run.sh` 的断言对象 = `Makefile`/`tools/infra/gate_lock.py`/`docs/Process-07`/`AGENTS.md`（`grep -E 'issues\.yaml|ISS-229|milestones|check_issues' run.sh` 仅命中 L2 顶注 1 行、**非断言**）；这些文件在 `e1210cff` **零改动** ⇒ 上轮 `evidence-3-baseline.log`（`11 checks, 0 failed`）、`evidence-4-injected.log`（`8 failed`）、`evidence-5-restored.log`（`0 failed`）继续有效；另我本轮亲跑 L1 兜底。
3. `python3 -c "yaml.safe_load(...)"` 解析 `.tao/knowledge/issues.yaml`（非文本目测）⇒ `status = closed`、`resolved_by = INFRA-099t`、`notes len=4350`；notes 末段「【关闭（2026-10-21，`INFRA-099t`）】」含**关闭依据**（flock + 29 个 `GATE_LOCKED_TARGETS` + 嵌套放行 + 有界等待/`rc=75`/`rc=69`）、**证据**（self-test 8/8、真并发 A rc=0/413 s、B rc=0/471 s + `WAIT … target=check-modules`、注入 11→`8 failed`→还原 `11/11`、L1/L2 rc=0）、**边界**①同树限定（`<repo>/.dadao/gate.lock`）②`GATE_LOCK` 可被 env 覆盖登记为遗留③不替代 `ISS-300`/`ISS-210` ⇒ 验收 #8 前半 **PASS**（上述 6 个关键词用 `in notes` 程序核，全 `True`）。
4. `python3 tools/infra/check_issues.py` ⇒ **rc=0**：`check_issues: 52 open, 36 closed (0 blocking M1-gate: 0)` + `resolved_by 约束 OK (36 closed → 非空 / 52 open → null)`。
5. **并集对账**：`git -c core.quotepath=false show --name-only --format='' 6fa530ae 847b76ac e1210cff | sort -u` = **7 文件**（`issues.yaml`、`milestones.md`、本册、`AGENTS.md`、`Makefile`、`docs/Process-07-门控分层规范.md`、`tools/infra/gate_lock.py`）vs 完成区 L62 列 **6 项** ⇒ **差集 = `.tao/knowledge/issues.yaml`**（本册 / `milestones.md` 按第 1 轮要求已补列 ✓）。
6. `make check` ⇒ **rc=0**、`repository checks (L1): PASS`（含 `check_issues` 52/36 行）；`make check-milestones-fresh` ⇒ **rc=0**、`结果: PASS (26 行…)`；`git status --porcelain -uall` ⇒ 写本记录前 **0 行**、写后 **1 行**（仅本册，即我本轮唯一改动）。

**约束核验**：本轮我未 `commit`/未 `push`、未用 `git checkout/restore/stash`、无 `cmd | tee`；我产生的临时产物只落 `/tmp/opencode/INFRA-099t-review/`；禁改目录 `spec/ contracts/ components/ tests/vectors/ manifests/ .tao/contracts` 零改动；本册仍是 3 提交内唯一任务书改动、未越界。

**Needs Revision（唯一最小改）**：完成区 L62「**修改文件**」补列 `.tao/knowledge/issues.yaml`（`ISS-229` `closed` 回填）⇒ 并集 7 = 列 7；否则完成区「验收结果：9 条验收逐条命中」与对账字段再次与盘上事实不符（同第 1 轮 ② 的缺陷面）。改后**无需**重跑证据（仍只动本册一行、零触 `Makefile`/`tools`/`docs`/`AGENTS.md`）。

#### 第 3 轮 reviewer 验收

**判决：Accepted** —— 上轮唯一返工项（完成区「修改文件」并集 7 vs 6）已落实：并集 **7 = 7**（`comm` 双向差集均 0 行）；`make check`(L1) rc=0；写本记录前工作树 0 行。

**重跑记录（rc 取被检命令自身；无 `| tee`；未用 `git checkout/restore/stash`）**
1. `git show --numstat a7d14fb9` ⇒ **仅 1 个文件**（本册 `17/1`，无第二文件）；`git show --name-only --format='' a7d14fb9 | grep -E '^(Makefile|AGENTS\.md|tools/|docs/)'` ⇒ **rc=1、0 命中** ⇒ 返工零触门控载体/文档 ⇒ 第 2 轮「证据复用」理由仍成立（`evidence-3-baseline.log` 11 checks/0 failed、`evidence-4-injected.log` 8 failed、`evidence-5-restored.log` 回绿继续有效）。
2. **并集对账**：`git -c core.quotepath=false show --name-only --format='' 6fa530ae 847b76ac e1210cff a7d14fb9 | sort -u` = **7**：`.tao/knowledge/issues.yaml`、`.tao/knowledge/milestones.md`、本册 `.tao/tasks/infra/INFRA-099t-门控与安装根互斥.md`、`AGENTS.md`、`Makefile`、`docs/Process-07-门控分层规范.md`、`tools/infra/gate_lock.py`；与完成区 L62 七项 `comm -23`/`comm -13` 双向比对 ⇒ 差集 **0 行**、多余 **0 行** ⇒ **7 = 7**（`r3-union.txt`）。
3. `make check` ⇒ **rc=0**、末行 `repository checks (L1): PASS`；全志 `grep -ci fail` = **0**、`[PASS]` 231 行（含 `check-milestones-fresh 结果: PASS (26 行…)`、`check-no-residue: PASS`、`check-run-artifacts PASS`、`check_issues: 52 open, 36 closed`）⇒ `/tmp/opencode/INFRA-099t-review/r3-l1.log`。
4. `git status --porcelain -uall` ⇒ 写本记录前 **0 行**；`Makefile`/`gate_lock.py`/`Process-07`/`AGENTS.md`/`issues.yaml`/`milestones.md` 六文件 md5 前后 `diff` **rc=0**（未被本轮改动）。

**约束核验**：未 `commit`/未 `push`；未用 `git checkout/restore/stash`；无 `cmd | tee`；临时产物只落 `/tmp/opencode/INFRA-099t-review/`；禁改目录 `spec/ contracts/ components/ tests/vectors/ manifests/ .tao/contracts` 零改动；`a7d14fb9` 仅动本册一行，与完成区「修改文件」口径一致、无越界。

**Accepted** —— 本轮 3 项核验在**我自己的重跑**下全部命中、无新增缺陷；遗留（`GATE_LOCK` 可被 env 覆盖、互斥仅限同一工作树、L3 全量未跑）已于第 1 轮登记、不阻断。终审权归架构师。
