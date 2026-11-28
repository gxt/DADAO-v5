# m18-linux-015: mlock2 / MLOCK_ONFAULT 路径 SIGSEGV

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-005`
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务单路径根因定位，取 1.5–2× 中位）
**档位**：中改（mm/syscall）
**状态**：已验证
**阻塞**：无（`m18-linux-023`/`024` 已合入；基线在本任务内补齐，见「待裁定」已解除说明）。
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-005` 分诊的 `mm-mlock2-tests`（`KERNEL_BUG`）：程序只打出 TAP header/plan（`1..15`）就 `SIGSEGV`（rc=139），第一条子测试 `mlock2_(3 * page_size, MLOCK_ONFAULT)` **没有**以 `ENOSYS` 失败，测试因此进入 `test_mlock_lock()` 并在其中崩溃。没有任何用户态断言被触发 ⇒ 属内核（或 libc/内核 ABI）故障，不是测试假设。证据行见 `tests/unit/linux/suite/triage.yaml`。

## 目标

1. 定位崩溃点：`mlock2`/`MLOCK_ONFAULT` 的系统调用实现、页表/权限路径或返回 ABI（寄存器/errno）。
2. 修复到符合 Linux mm/syscall 语义：要么真正实现 `mlock2`+`MLOCK_ONFAULT`，要么按契约返回 `ENOSYS`/`EINVAL`，不得「成功但坏页表」。
3. 修后用例能继续跑完全部子测试并给出明确结果。

## 验收（逐条贴真实 rc）

1. 修前签名（rc=139、仅 TAP header）落盘；修后 `run_suite.py --only mm-mlock2-tests` 连续 5 次无 `SIGSEGV`，输出逐子测试结果（15 条或明确 SKIP）。
2. 返回值/errno 与 `contract-syscall` 及 Linux `mlock2(2)` 语义一致；至少覆盖：`MLOCK_ONFAULT` 合法、未知 flags ⇒ `EINVAL`、未映射区间 ⇒ `ENOMEM`（`apply_vma_lock_flags()` 的三处 `-ENOMEM`：`mm/mlock.c:536` 无 VMA、`:549` 内部空洞、`:565` 尾部；`mlock(2)` man page 亦明确 ENOMEM = 范围不全是已映射页）。
3. **可达 FAIL ≥1 路**（`cp`+md5 还原 + 重建）：注入 `syscall_argmask[284] 0x01→0x00`（`mlock2` 的 `start` 不再走 `rb16`）⇒ 用例非 PASS 且出现命名子断言红；还原后回绿。
4. 不回归：`check-linux-k5`、`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem（musl 共享树的既有 problem 见坑④）；`check-config-pins`/`check-component-changelog`/`check-tests-index`/`check-tasks`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
5. 更新 `triage.yaml` 对应行；`check_suite.py --latest` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（最小，mm/syscall）、`components/linux/changelog.md`、`tests/unit/linux/suite/**`（triage/用例配置）、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 期望值来自 `contract-syscall` 与 Linux 语义；不改测试来迁就内核现状。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」。
5. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

**已解除（2026-11-25）**：`m18-linux-023`（扁平位图解码）与 `024`（异步窗口）已合入 master，安装根 QEMU 与内核配对；015 按 B 方案在本任务内补基线。以下原文保留作历史记录。

1. **本任务没有内核缺陷可修；两条「环境/基线」验收项被 `m18-linux-023` 阻塞。** 当前内核 + **预扁平位图** QEMU（md5 `5181f23f`，`strings` 无扁平不变式报错串；安装根 `7148dbca` 有）——即 2026-11-22 记录本行时所用的编码——上，**未改动树**连续 5 次 PASS（每次 15/15、`SUITE CASE END mm-mlock2-tests rc=0 status=exit`、无 SIGSEGV；见运行期证据目录 `run.sh` B 段）。同一内核 + **安装根**（扁平位图）则任何启动都在 `dadao_k1_pt_init` 的注册探针处 `die`（`unknown cause=0x10000000000000`），用例 `status=missing`。⇒ mlock2/mm 语义侧无缺陷，缺的是 023 的**扁平位图解码**。
2. 请裁定 A / B：
   - **A（推荐）**：015 以「无内核改 + 证据」收口；`suite.yaml`（`mm-mlock2-tests` 期望改 `PASS`）与 `triage.yaml`（删该行；S3c 要求两者同步）**留给 023 一次性改**（023 任务书已写明 K5/K6 期望按扁平模型更新、015..018 受影响）。理由：交付态测不出 PASS，此刻改基线即造一条不可复现的记录。
   - **B**：若坚持在 015 内改基线，请先派 023 落地解码，015 返工一次只改这两行。

## 完成区

**测试结果**：安装根 QEMU（扁平位图；**md5 已于当日 15:44 被并发重装，实测二进制 md5 以运行期记录为准**（本轮 `8b49d6d9…`，`strings` 扁平位图特征仍在）；5/5 绿不受影响）+ 当前补丁集内核：`run_suite.py --only mm-mlock2-tests` **连续 5 次 PASS**（每轮第 1/3 次即绿，重试 0；`m18-linux-024` flake **0** 次），每次 `Totals: pass:15 fail:0`、`SUITE CASE END mm-mlock2-tests rc=0 status=exit`、`status=signal` 0 次。全量 8 例 1 次：PASS=4 FAIL=2 SKIP=2；`timers-nanosleep` 另单跑 3 次均 PASS（合计 4/4）⇒ 其基线由 HOST_TIMEOUT 漂到 PASS，随同两文件订正。注入 `syscall_argmask[284] 0x01→0x00`：`FAIL rc=1`，`not ok 1 test_mlock_lock: Locked` 等 7 条命名子断言红；`cp`+md5 还原并强制重建后回绿（15/15）。运行期探针 `p_mlock_hole.c`（静态 musl，经套件 `/init` + 单例 initramfs 跑起，runner rc=0）：`mlock2(未映射空洞,page,0)` ⇒ `-1 errno=12 (ENOMEM)`；`mlock2(已映射,page,0)` ⇒ `0`；`mlock2(已映射,page,MLOCK_ONFAULT)` ⇒ `0`；guest `SUITE CASE END p-mlock-hole rc=0 status=exit`、`PROBE SUMMARY: 3/3 passed`。证据：运行期证据目录内 `run.sh`（`RESULT: PASS`）+ 同目录 `run-round2.log`、`logs2/`、`probe/`（`run.log` 与 guest `console.log`）。
**修改文件**：`tests/unit/linux/suite/suite.yaml`（`mm-mlock2-tests`、`timers-nanosleep` 的 `expect` → PASS）、`tests/unit/linux/suite/triage.yaml`（删两条对应行）、本任务书。无内核/QEMU/spec/契约/Makefile 改动。
**验收结果**（逐条）：
1. 修前签名：历史 run `20261122T192445` `rc=139 status=signal`（仅 TAP header）；修后 5/5 PASS，15 条子断言全过（VmLck、VmFlags、VMA split/merge、`mlockall(MCL_FUTURE)`、`MAP_DROPPABLE`）。
2. errno/语义：`MLOCK_ONFAULT` 合法 ✓；未知 flags ⇒ `EINVAL` ✓；未映射空洞 ⇒ **`-1/ENOMEM`** ✓（探针实测 `errno=12`；`mm/mlock.c:536/549/565` 三处 `-ENOMEM`，man page 同，见坑②）；已映射区间与 `MLOCK_ONFAULT` 均返回 0。
3. 可达 FAIL：argmask 注入 ⇒ `not ok 1/3/11/12/13/14/15` ⇒ 还原回绿；`run.sh` C 段 5/5 断言。
4. 不回归：`check-linux-k5` 285/285 rc=0；`check-linux-k6` 82/82 rc=0；`check-patch-tree` linux 105 patch / **0 problem**；全树 8 problem = **qemu 6（`cpu.c`/`cpu.h`/`helper.c`）+ musl 2（`bits/signal.h`）**，红集随共享源树漂移（坑④）；`check-config-pins`/`check-component-changelog`/`check-tests-index`/`check-tasks`/`check-knowledge-refs` rc=0；`check_suite.py --latest` 23/23 rc=0。
5. `make check`：与基线（HEAD 两文件换入后同树重跑）**逐行相同**（diff 0 行）；red 停在 `check-patch-tree`（分布见第 4 条，红集随共享源树漂移）。`check-patch-tree --source-state` linux `count=1 clean=True`。
**新发现/坑**：② 「未映射区间 ⇒ ENOMEM」口径正确（第 2 轮 reviewer 复核 + 本轮探针实测）：`apply_vma_lock_flags()` 在 `mm/mlock.c:536`（无 VMA）、`:549`（内部空洞）、`:565`（尾部）三处返回 `-ENOMEM`，`do_mlock` 原样上抛；`mlock(2)` man page ERRORS 同义。上一版「返回 0」的表述与推论已删除。③ 安装根 QEMU 与 023 内核配对后无需旧模型垫片，旧轮「交付态判不了」作废。④ 本轮 `check-patch-tree` 8 problem = qemu 6（`cpu.c`/`cpu.h`/`helper.c` 的断言 ⑥+⑨）+ musl 2（`bits/signal.h` 的 ⑥+⑨）；均因共享 qemu/musl 源树与锁定补丁集不匹配。同期 `m16-qemu-007` worktree 在跑，共享 qemu 源树的 `target/dadao/helper.c` 处于未提交修改态 ⇒ 红集随共享源树漂移，不作为本任务判据；本任务 3 文件不含任何 qemu/musl 内容，linux 段 105/0。⑤ `timers-nanosleep` 在 022/024 异步交付修复后稳定 PASS（4/4），原 HOST_TIMEOUT 基线与 KERNEL_BUG 行已成过期项（S3c 会判红），故同两文件一并改。
**遗留问题**：无（待裁定 1/2 已解除）。原「≥2 路可达 FAIL」因无内核修复可回退，按返工口径降为 ≥1 路（argmask 注入）。

## 审阅记录

### 第 1 轮 engineer 自审
自审对象：分析结论、`run.sh`、任务书。**无代码改动 ⇒ 没有可回退的「修复」**，故自审聚焦「结论有没有可达反例」与「证据能否失败」。
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 结论「mlock2 无缺陷」只靠一次 PASS 可能掩盖偶发 | ✅已修 | `run.sh` 要求 5 连续 PASS，逐次断言 15/15 与 `status=signal`=0 | `logs/run-sh-v6.log` B 段（attempts=5） |
| F2 「交付态判不了」若不现场复现等于推测 | ✅已修 | `run.sh` A 段在安装根模型上跑一次，断言 `unknown cause` 与「非 PASS」 | `logs/run-sh-v6.log` A 段 2/2 PASS |
| F3 注入必须真能红，且红在 mlock2 本身上 | ✅已修 | argmask `[284]` 0x01→0x00 → 命名子断言 `not ok 1`；`cp`+md5 还原 | `run.sh` C 段；`logs/inject.log`（verdict）+ 该次 run 的 console（`SUITE CASE BEGIN/END` 之间） |
| F4 024 flake 不能记成用例红 | ✅已修 | 按 `die mode=2 code=0xe1` 单独计数，另判「无其它失败签名」 | v6 flakes=0、others=0 |
| F5 门控红是否被我污染 | ✅已修 | 撤掉临时解码垫片（用后删除、不入交付）后单独重跑 `check-patch-tree`；两棵源树 `git status` 干净 + md5 对账 | `logs/check-patch-tree-pristine.log` linux 0 problem |
| F6 证据脚本可复跑、失败非零 | ✅已修 | 非交互、逐项打印、末尾 `RESULT/RESULT: FAIL` + exit 1 | v6 末行 `RESULT: PASS` |

判决：无未修 finding；但**任务的基线两项被 023 阻塞**，状态保持「待开始」，不标「待验收」。

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）

### 第 2 轮 engineer 自审
自审对象：`run.sh`（A–D 段）、`suite.yaml`、`triage.yaml`、本任务书。无内核代码改动，自审聚焦「证据能否失败」与「基线改动是否自洽」。
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 首版 flake 正则 `va=0x10` 无边界，误匹配普通缺页行 `va=0x10040`，5 次全被判 flake | ✅已修 | FLAKE_RE 加 `([^0-9a-f]|$)`；verdict 去前导空格 | 二跑 5/5 首 attempt 绿、flakes=0 |
| F2 `build_kernel` 只看 image+vmlinux 哈希，改源码后复用旧内核 ⇒ 注入假绿 | ✅已修 | 注入/还原前 `rm -f kernel-image.json` 强制重建 | inject `rc=1`、7 条 `not ok`；regreen 15/15 |
| F3 024 flake 若 3 次仍命中，原逻辑不记红 | ✅已修 | `round_ok` 标志，一轮未绿落 FAIL | 代码复核；本轮 0 flake 未触发 |
| F4 `--only` 无法满足 S1/S2/S3c/S3f（设计如此），只用它判 5 连会出假红 | ✅已修 | 5 连用 `--skip-checks` 判用例级；另跑全量 8 例 + `check_suite --results/--latest` 判台账 | full rc=0；check_suite 23/23 rc=0 |
| F5 `timers-nanosleep` 基线漂移使 S2/S3c 恒红，只改 mlock2 则 `check_suite rc=0` 不可达 | ✅已修 | 同两文件内 timers expect→PASS、删其行；先 3 次单跑确认 | timers 4/4 PASS；full S2/S3c PASS |
| F6 `make check` 基线须独立可比 | ✅已修 | `cp` 备份两文件 → `git show HEAD:` 取基线内容换入 → 同树重跑 → `cp` 回并 md5 对账 | md5 67b6e022/9aa93e25；diff 0 行 |
判决：无未修 finding；状态 → `待验收`。

### 第 2 轮 reviewer 验收

**重跑记录（判决依据全部为本人于仓库根的输出/退出码）**
1. `run.sh`（运行期证据目录内）重跑：`RESULT: PASS` rc=0。B 段 5 轮均第 1/3 次绿：逐轮 verdict `PASS mm-mlock2-tests rc=0 status=exit`、`Totals: pass:15 fail:0`、`status=signal`=0；`flakes=0`、`others=0`（024 族 0 次命中、无重跑轮次）。D 段全量 8 例 rc=0、`check_suite --results` rc=0。
2. 独立注入（cp+md5 备份）：`syscall_argmask[284] 0x01→0x00` + 删内核镜像记录强制重建 ⇒ `FAIL rc=1`、命名子断言 `not ok 1 test_mlock_lock: Locked` 等 7 条红、无 15/15 行；cp 还原（md5 `d98077c9…` 相等）→ 重建 → PASS 15/15、signal=0、源树 clean。
3. 坑复现：注入态源码、**不删**镜像记录 ⇒ `kernel: unchanged … skipped rebuild` ⇒ 用例假绿 PASS——「镜像哈希复用旧内核」坑真实（先前一次不删却重建，因前一跑用例集合不同致 cpio 哈希不匹配，非坑失真）。
4. 脚本反例：注入后重跑同一 `run.sh` ⇒ `RESULT: FAIL (17 check(s) failed)` rc=1（B 段 5 轮 verdict、C 段注入/还原、D 段 rc、源树 clean 全红）；随后全量 cp 还原（源码与证据原件 md5 复原、日志 cp -a 回滚后 diff 无差异）→ 重建回绿 PASS 15/15。
5. `timers-nanosleep`：本人单跑 1 次 + 全量 1 次均 PASS rc=0；加 engineer 3 单跑 + 1 全量 ⇒ 合计 6/6。
6. 门控：`check-linux-k5` 285/285 rc=0；`check-linux-k6` 82/82 rc=0；`check_suite --latest` 23/23 rc=0、`--patches-only` rc=0；`check-config-pins`/`check-tests-index`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog` 均 rc=0。
7. `check-patch-tree`：linux 105 patch / **0 problem**；全树 8 = qemu 6（cpu.c/cpu.h/helper.c ⑥+⑨）+ musl 2（bits/signal.h ⑥+⑨），与坑④记录一致；本任务 3 文件 diff 无 qemu/musl 内容。
8. `make check`：当前树 rc=2 停在 check-patch-tree；基线（merge-base 两文件换入同树重跑，cp 还原 + md5 对账相等）同 rc=2；diff 仅基线跑多 2 行 gate-lock 等待（并发 build-gem5 占锁），其余逐行相同。
9. 范围：分支自身改动（merge-base..HEAD）**恰 3 文件**；`master..HEAD` 另含 5 个 master 先行合入的 m20 文件（非本任务产出）；无内核补丁/QEMU/spec/契约/Makefile；版本未变；未 push；完成区 10 行；任务书无运行期路径；状态 `待验收`；三文件 md5 与开工快照对账相等。

**约束核验**：硬约束 1–5 守住（独立 worktree、不提交、只动声明 3 文件、期望未迁就实现、还原一律 cp+md5 且对账相等）。

**F1（阻断·语义类）**：验收②订正「未映射区间 ⇒ 返回 0（不是 ENOMEM），与上游一致」**与 Linux 上游相反**：① mlock(2) man page ERRORS 明文 ENOMEM「Some of the specified address range does not correspond to mapped pages」；② `apply_vma_lock_flags()` 三处 `-ENOMEM`（`vma_iter_load` 落空、内部空洞 `vma->vm_start != tmp`、尾部 `tmp < end`），`do_mlock` 原样上抛；③ `mm/mlock.c` 与上游 v7.2.10 逐字相同（kernel.org 同版文件 md5 与树内一致）——**身份成立但推论反了**；④ 证据目录无 hole 实测，完成区第 2 条 ✓ 无支撑。原口径 ENOMEM 才对。
**处置**：验收②、完成区第 2 条、坑②改回 ENOMEM（与上游一致）；无门控读取该行，改后重跑 `check-knowledge-refs`/`check-tasks` 即可。

**F2（不阻断·记录）**：完成区所记安装根 QEMU md5 已因当日 15:44 并发重装过期（当前二进制 md5 不同；扁平位图特征串仍在，我方 5/5 绿，判据不受影响）。

**判决：Needs Revision**（仅 F1；5/5、两处基线改动、注入与坑、不回归、范围在我方重跑下全部通过）。

### 第 3 轮 engineer 自审
自审对象：F1 语义订正、hole 探针、QEMU md5 记录、静态门控复跑。
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（reviewer）「未映射 ⇒ 0」与上游相反 | ✅已修 | 验收②、完成区第 2 条、坑②统一改回 `-1/ENOMEM`，引 `mm/mlock.c:536/549/565` + man page；删空洞「返回 0」表述与推论 | 探针 3/3；三处口径均为 `-1/ENOMEM`（旧表述仅存于 reviewer 引文与本行引用） |
| F1 缺 hole 实测 | ✅已修 | 运行期新增 `p_mlock_hole.c` + runner：静态 musl，经套件 `/init` 与单例 initramfs 启动，跑完恢复 K6 镜像 | runner rc=0；guest `rc=0 status=exit`；hole `-1 errno=12`、mapped `0`、onfault `0` |
| F2（reviewer）QEMU md5 过期 | ✅已修 | 完成区改为「当日 15:44 并发重装，实测 md5 以运行期记录为准；扁平位图特征仍在，5/5 绿不受影响」 | 当前 `8b49d6d9…`、mtime 15:44:57、`strings` 扁平特征 223 |
| 探针是否真能失败 | ✅已修 | 三例逐条判 `PASS <case>` 与 `PROBE SUMMARY: 3/3`；runner 计数失败即非零 | 探针源码内三支各自独立判定；本轮 0 fail |
| 写入后静态门控 | ✅已修 | 仅改任务书后重跑 | `check-knowledge-refs`/`check-tasks`/`check-tests-index`/`check-config-pins`/`check-component-changelog` 均 rc=0；`check_suite --latest` 23/23 rc=0 |
| `--latest` 被 reviewer 注入期的全量 run 顶成最新（mm-mlock2 FAIL） | ✅已修 | 干净树重跑全量；attempt 1 `mm-map-populate` HOST_TIMEOUT（024 族），attempt 2/3 rc=0 | `check_suite --latest` 23/23 rc=0 |
判决：F1/F2 已修，无未修 finding；状态保持 `待验收`。

### 第 3 轮 reviewer 验收

**重跑记录（判决依据全部为本人输出/退出码）**
1. **F1 闭环**：验收②（`ENOMEM`，引 `mm/mlock.c:536` 无 VMA/`:549` 内部空洞/`:565` 尾部 + man page）、完成区第 2 条（`-1/ENOMEM` + 探针 `errno=12` + 同三行号）、坑②（三处 `-ENOMEM` + man page，声明旧「返回 0」已删）**三处均为 ENOMEM**；本人逐行复核 `sed -n '536p;549p;565p'` = 三处 `return -ENOMEM;`，行号引用准确。旧「返回 0」仅存于审阅记录历史引文（第 2 轮 F1 原文与第 3 轮自审表引用）——可接受；正文唯一「返回 0」为「已映射区间与 `MLOCK_ONFAULT` 均返回 0」，语义正确且探针实测。
2. **hole 探针本人复跑**（运行期证据目录内 `probe/run_probe.py`，非交互）：`PROBE_RC=0`，`PROBE RESULT: PASS (0 check(s) failed)`；guest 实测 `mlock2(unmapped, page, 0) = -1 errno=12 (ENOMEM)`、`mlock2(mapped, page, 0) = 0`、`mlock2(mapped, page, MLOCK_ONFAULT) = 0`、`PROBE SUMMARY: 3/3 passed`、`qemu rc=0 stop=guest-done`；runner 断言三支独立、finally 恢复 K6 镜像并删镜像记录。
3. **F2 闭环**：完成区已记「15:44 并发重装、以运行期记录为准（本轮 `8b49d6d9…`）」；本人实测当前安装根 QEMU md5 = `8b49d6d9ea9c39dc2dffc1ca7d02739b`，**与记录前 8 位一致**。
4. **范围**：`git diff master..HEAD --name-only` **恰 3 文件**（任务书 + 两 yaml；上轮多出的 5 个 m20 文件系 master 侧新提交，已经 `1faade1b` merge 进入分支，不再出现）；`merge-base..HEAD` 同 3 文件；提交 `8b331466` 仅改任务书（+38/−4）与声明一致；未 push；完成区 10 行、无具体 `.work/**`；状态 `待验收`；两 yaml md5 与开工快照对账相等、工作树仅任务书待提交。
5. **门控重跑**：`check-knowledge-refs`/`check-tasks`/`check-tests-index`/`check-config-pins`/`check-component-changelog` 均 **rc=0**；`check_suite.py --latest` **rc=0**（23/23，最新 run 为干净树全量）。5 连跑与 K5/K6 按派单不重跑（上轮已验）。

**约束核验**：F1 三处口径、探针实测、md5 记法、范围与状态逐项吻合；无新 finding。

**判决：Accepted**
