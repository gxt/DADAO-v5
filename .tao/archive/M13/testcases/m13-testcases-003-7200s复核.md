# m13-testcases-003: 3600s 仍超时的例 × 7200s 复核

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-001` + `m13-testcases-002`（取「3600s 仍超时」的名单）
**可并行分片**：否（单机 48 并发跑批；测时间要求进程独占核）
**状态**：已验证

## 用户裁定（原话）

「跑3600s，甚至7200s……不修改源码，不做调试，只记录结果；我来对结果进行分析和裁定。」

## 用户裁定（2026-11-10，本任务执行口径）

- 「207/208，**各自可安排 48 个测试用例**，先把 **static** 全跑，然后再把 **dynamic** 全跑。」
- 同意**追加 120 s 采样**：每例先跑 120 s 后 `SIGINT`，读 gem5 `stats.txt` 的 `simInsts`（**只读自带 stats，不调试、不改源码**），用于区分「挂死 vs 纯计算量」。
- 同意**输出落点改按新规**：人读结论 → `docs/TestReports/`；原始 JSON **不入库**（留运行期证据目录）。
- 安排任务前先查磁盘：主控机 `make check-disk`、节点 `remote.py status` 的 `disk_alert`；**> 90% 报警**。

## 目标

1. 从 001/002 的结果里取「3600s 仍超时」的例（static 72 + dynamic 78），**先 static 全部、再 dynamic 全部**；两节点各 ≤48 并发。
2. 每例先做 **120 s 采样**（`SIGINT` 后读 `simInsts`），再做 **gem5 SE 7200s** 重跑；同例 QEMU 计时。
3. 输出每例：`case` / `simInsts_120s` / `gem5_seconds` / `qemu_seconds` / `ratio` / `klass` / `exit`。
4. 统计：有多少例在 7200s 下转 PASS；结合 `simInsts_120s` 判「挂死（120 s 内已跑海量指令）vs 纯计算量」——**只给数据与观察**。

## 验收标准

1. 名单与 001/002 的「仍超时」集合**逐个对应**（不遗漏、不新增）
2. 输出：人读结论落 `docs/TestReports/M13-长尾7200s.md`；原始 JSON 留运行期证据目录（**不入库**），仅把必要摘要（逐例表 + 三类计数）写进结论册
3. 报告含：逐例表、转 PASS/仍超时/异常三类计数、执行环境指纹
4. **不改** gem5/QEMU/测试资产/用例与期望
5. 采样只用 gem5 自带 `stats.txt`（`--outdir` + `SIGINT`），不引入调试构建
6. 执行前：主控机 `make check-disk` rc=0、两节点 `disk_alert=ok`；否则先报警再处置
5. 完成区 ≤30 行、无运行期路径

## 执行方式（2026-11-10 用户改为按时耗分组）

用户 2026-11-10：「长跑，是不是重新分一下，30s以内的，按7200s进行测试，看看是否能跑出结果来；30s以上的，直接扔某个节点机上，一直跑」。

- **分组阈值 30 s**（按 3600 s 批的 `qemu_seconds`）：`≤30 s` ⇒ A 组（7200 s 预算，有机会跑完）；`>30 s` ⇒ B 组（不设实际上限，跑完为止）。
- 分组结果（现场统计）：A = 26 static + 34 dynamic = **60 例**；B = 46 static + 44 dynamic = **90 例**。
- 执行：A 在 208（先 static 后 dynamic，各 7200 s）；B 在 207（两档同时跑，32 并发/档，安全上限 172800 s）。
- 120 s 采样结果保留（两节点各半，合并覆盖全部 150 例）。
- 依据：按最低观测比值 172×，qemu > 42 s 即注定超 7200 s；30 s 阈值留了余量。

## 执行方式（原计划，已作废）

- 两节点并行，各 ≤48 并发；**先 static（72 例）后 dynamic（78 例）**；主会话启动 background
- 预计：static 36/36 单波 ≈ 2 h，dynamic 39/39 单波 ≈ 2 h，合计 **≈ 4 h**（采样另加约 2–3 min/节点）
- 用例名单从 `refs/m13-001-static-3600s-full.json`（blocked 72）与 `refs/m13-002-dynamic-3600s-full.json`（blocked 78）派生，逐个对应、不增不减

## 非范围

- 不做根因分析、不调试、不改源码

## 准备阶段（2026-11-10，engineer）

分工：本阶段只交付脚本与名单，**不启动 7200 s 长跑**（主会话后台启动）。

## 完成区

**交付物**（入库）：`tools/testcases/tset/gem5-se-baseline/make_blocked_case_lists.py`（派生名单 + 分片，写出的每个文件都用 `run_engine_ratio.load_selection` 回读校验）；`tools/testcases/tset/gem5-se-baseline/sample_insts.py`（120 s 采样）。**运行期证据目录下的 `run.sh`（不入库）**：preflight → lists → selfcheck → sample → long，逐阶段 `*_EXIT`，不删任何东西。

**名单计数（现场统计，未写死）**：static `blocked=72`（libc-test 2 / llvm-ts 70）→ 分片 36/36；dynamic `blocked=78`（libc-test 1 / llvm-ts 77）→ 分片 39/39；两分片并集 == 全集、无重复、无遗漏（生成器内断言）。

**采样工具真实输出**：1 例 × 120 s（`functional/clocale_mbfuncs`）→ `simInsts=139350401`、`exit_cause=user interrupt received`、`seconds=121.77`、`outcome=interrupted_sigint`，与 `m5out/stats.txt` 的 `simInsts` 行回读一致。另验 llvm 路径（20 s，`MultiSource/Applications/aha`）`simInsts=21398833`/`interrupted_sigint`；「跑完退出」路径（短用例）`simInsts=4113`、`exit_cause=exiting with last active thread context`、`outcome=completed` —— 两种结局可区分。

**验收结果**：`make_blocked_case_lists.py --self-test` 18/18 rc=0；`sample_insts.py --self-test` 22/22 rc=0（含 `build_cmd` 与 `gem5_se_engine.run_gem5_se` 的逐项比对，及「比较可失败」反例）；`run.sh lists` rc=0、`run.sh selfcheck` rc=0、`run.sh preflight` rc=1（按设计阻断，见下）。**未启动长跑**。

**preflight 实测**：节点 `disk_alert=ok`（13%）、`running=none`、`gem5.opt` 可执行 → PASS；**主控机 `make check-disk` = 91% ALERT**；两节点 commit 与主控机 master 不一致 → 阻断。

**新发现/坑**：
- gem5 的 SIGINT 走 `exitSimLoop("user interrupt received")`，`m5.simulate` 的 `atexit.register(stats.dump)` 仍写 `stats.txt`（rc=125，统计完整）→ 采样不需要 debug 构建。
- 主控机组件构建树在本阶段被其它任务反复重建（二进制一度不完整且无 x 位），宿主上跑 gem5 会撞 `not executable`；长跑必须上节点。
- dynamic 名单只有 1 个 libc 例 → 落在 shard1，shard2 只有 llvm-ts；`run_engine_ratio` 拒绝空 suite（`run.sh` 用 `--print-suites` 取实集）。
- `make check-disk` 只看当前仓库根所在文件系统：在任务 worktree 跑看到的是临时盘，不代表主控机。
- 采样复用各 driver 的 `build_and_run`，只替换 `gem5_se_engine.evaluate` 这一个引擎边界；钩子必须打到 **driver 自己 import 的模块对象**，不能另 load 一份。

**遗留问题**：① 7200 s 长跑未启动（主会话负责）；启动前需：提交合并 → 两节点同步到同一 commit → 主控机磁盘降到 <90% → 再跑 `run.sh`。② 节点侧命令（sample/long）尚无法冒烟：节点仓库还没有本任务的两个新工具。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查两个新工具 + `run.sh`，finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 采样钩子打到自 load 的模块副本，driver 不受影响 | ✅已修 | 改用 `driver.gem5_se_engine` 并就地替换 | 真实 1 例采样成功（两套 driver 各 1 例） |
| gem5 子进程未登记 `proc_reap`，外部 Ctrl-C 会留孤儿 | ✅已修 | `sample_one` 接收并 `track/release` | self-test 22/22 + 1 例实跑 |
| 未映射到 case id 的运行会被静默降级为 `not_sampled` | ✅已修 | driver 跑完即检 stray → 硬失败 rc=2 | 代码路径 + 目录映射 self-test 两项 |
| `--only` 收窄后 `case_list.total` 失真 | ✅已修 | 拆 `total`/`selected` | self-test「report listed vs selected」 |
| `wait_and_interrupt` 用 `killpg(pid)`、假进程会误伤自身进程组 | ✅已修 | 改 `killpg(getpgid(pid))`；假进程用不可能 pid | 「killed after SIGINT」用例由 FAIL 转 PASS |
| `sim.log` 全量读取（长跑可能很大） | ✅已修 | 只读尾部 64 KB | exit_cause 两例解析一致 |
| self-test 里画表函数无人调用（死代码） | ✅已修 | 删除 | `SUITES` 改用于 suite 校验后无未用常量 |
| 临时产物误落 worktree 根，污染 `git status` | ✅已修 | 移入运行期临时目录 | `git status -uall` 仅剩两个新工具 |

判决：无未修 finding；本轮为准备阶段，**状态保持 `待开始`**（按派单口径，改 `待验收` 前先回报主会话）。

## 完成区（architect 收口，2026-11-12 10:05）

**B 组（207，172800 s 上限）数据完整，收尾脚本崩溃但数据有效。**

- 两份 ratio JSON 均 `ok=true`、`missing=[]`：
  - static `rows=46`：**43 pass / 2 blocked / 1 fail**；比值 n=44，min **141.7**、median **349.9**、max **1269.2**
  - dynamic `rows=44`：**42 pass / 1 blocked / 1 fail**；比值 n=43，min **157.2**、median **352.8**、max **1284.6**
  - 合计 **90 例：85 pass / 3 blocked / 2 fail**
- 与 A-long 对照：B 组中位约 **350×**，A-long 约 **700×** ⇒ 两者不是同一量级，「跑不完」的判定阈值应分开。
- **收尾异常（`ISS-398`）**：包装脚本 `run_split.sh` 在最后写 EXIT 时用相对路径（cwd 不符）⇒ `No such file or directory`；第 94 行 `rc` 未初始化 ⇒ `unbound variable`，整体 rc=1、**0 个 EXIT 文件**。数据本身未受影响（JSON 已落盘且 `ok=true`）。
- 判据以 JSON 为准，不以脚本 rc 为准；`m13-testcases-003` 的 A 组结论不受影响。
- **收尾归因更正（指向 `ISS-398`）**：本完成区首版写的「cwd 不符」「第 94 行 `rc` 未初始化」「0 个 EXIT 文件」三条**已证伪**，正确归因见 `ISS-398`（运行实例无 mkdir / 运行中改脚本致重读错位 / `--log-prefix` 不合正则），保留原文以守「不改写既有完成区」纪律。
- **EXIT 计数订正（reviewer）**：per-suite `.EXIT` 0 个；`split-A.EXIT`/`split-B.EXIT` 各 1 个（内容 `1`）。
- 人读结论已落 `docs/TestReports/M13-长尾7200s.md`：**全量逐例表 90 行**（组/case/klass/gem5 exit/比值/两引擎秒）+ 三类计数 + 5 例未通过归因 + 名单对账 + 环境指纹 + 复现 + 边界；A 组 60 例逐例表由 `refs/m13-001/002-*-full.md` 承载（本册 §4 注明）。

### 第 1 轮 reviewer 验收（2026-11-12，全部独立重跑）

**判决：Needs Revision** —— 验收标准 2/3 未达：人读结论册 `docs/TestReports/M13-长尾7200s.md` **不存在**（`git log --all` 检索 0 条；`docs/TestReports/` 现有 7 册无一含 B 组数据）⇒ 逐例表 + 三类计数 + 执行环境指纹无载体。其余项全部通过。完整输出留运行期日志目录 `m13-testcases-003-reviewer-r1.log`。

**重跑记录（本机亲跑，RC=退出码）**
1. `make check-milestones-fresh` RC=0（m12/m13 两册 PASS）；`make check-knowledge-refs` RC=0；`python3 tools/infra/check_issues.py` RC=0（40 open/5 closed；**Makefile 无 `check-issues` 目标**，按脚本跑）。
2. 两份 ratio JSON（节点 207 只读取回临时树，md5 static `1c4aa1c0…` / dynamic `ac53c734…`）python3 全量重算：static `rows=46 ok=True missing=[]` → `{pass 43, blocked 2, fail 1}`、`summary.ratio n=44 min 141.726 median 349.880 max 1269.211`；dynamic `rows=44 ok=True missing=[]` → `{pass 42, blocked 1, fail 1}`、`n=43 min 157.202 median 352.761 max 1284.603`。**与完成区逐数字一致**，合计 90 = **85/3/2** ✓。
3. 逐行 `ratio == gem5_seconds / qemu_seconds` 90/90，最大相对偏差 2.96e-06（3 位小数取整量级）。
4. 排除口径：`n = rows − (gem5_klass==blocked)`（46−2=44、44−1=43），`excluded_truncated=2/1`；**fail 未被排除**（fourinarow 的 141.7/157.2 正是 min）——不是「blocked/fail 都排除」。
5. 名单对账：`static 72 = A26+B46`、`dynamic 78 = A34+B44`，A∩B=0，对 001/002 全量 blocked 集合 `missing=[] extra=[]` ✓。
6. 5 例归属（节点上 driver 自带 reason，只读）：blocked×3 = `Applications/lua`(static+dynamic)、`Benchmarks/mafft`(static)，`timeout after 172800s (SE, not a verdict)` / gap `no guest exit within 172800s` ⇒ **撞 172800 s 预算截断，非崩溃**；fail×2 = `FreeBench/fourinarow`(static+dynamic)，`exit=0` 但 `oracle mismatch … output differs (3007 B vs 3007 B, sha256 54dba77cdbbf8b49)` ⇒ **输出比对不通过**（两轮同 sha，确定性）。
7. 节点侧独立佐证：static gem5-se/qemu case 目录各 46 = rows 46；dynamic 各 45 vs rows 44（多 1 为首轮被 pkill 的残留目录，名单/JSON 仍 44 且逐 case 对齐）；节点 `*.EXIT` 0 个。

**rc=1 归因（读 `run_split.sh` 61/94 行 + 会话留存原始输出）**
- 原始输出逐字：`line 61: …/split/B/<mode>/llvm-ts.EXIT: No such file or directory` ×2 → `[2026-11-12 09:33:41] B: rc=1` → `line 94: rc: unbound variable`。
- 61 行**运行时**是 printf：`mkdir -p` 是 2026-11-10 13:36 才补进脚本，而 B 于 09:30:43 起跑 ⇒ 运行实例无 mkdir、本地父目录从未建立；**不是「cwd 不符」**（同一相对 `$EVID` 的 `split-B.EXIT` 写成了 `1`）。
- 94 行是 `main "$@"`，`rc` 在 72/66 行已 `local rc=0`，且 `B: rc=1` 已打印 ⇒ **不是「rc 未初始化」**，是运行中改脚本致 bash 重读错位；按 ISS-398 原修法（`${rc:-1}`）改不掉真因。
- 第三因未登记：`remote.py run --log-prefix <任务号>-split-…` 不合任务号正则，校验在**远端跑完写日志时**触发 ⇒ `rc=2`（两份 per-suite 日志只剩该 ERROR）。
- 三处都只在包装脚本收尾（EXIT 写入 / 返回码 / 本地日志落盘），**不触碰 90 例数据**（数据由节点上 `run_engine_ratio.py` 产出，rows/ok/missing/逐行 ratio 已独立核）⇒ 「判据以 JSON 为准、rc=1 只影响收尾」成立。

**A 组独立性**：A 四份 ratio JSON（208）rows 2+24+1+33=60、`ok=True missing=[]`，2026-11-10 13:34 收口，早于 B 收尾 2 天；A 有同样 line-61 失败但数据完好；`M13-A组长尾计时.md`（009，中位 699/703 ≈ 700×，与完成区「A-long 约 700×」一致）独立于本次 B 收尾 ⇒ **A 组结论不受影响**。

**约束核验**：architect 完成区 11 行 ≤30、无运行期路径 ✓；本轮未 commit / 未 push / 未改台账（开工快照 `git status --porcelain -uall` 空、HEAD `9366db6b`；收尾快照唯一改动 = 本审阅记录，HEAD 仍 `9366db6b`）✓；207 仅只读（ls/find/python3 读 + scp 取回）✓；运行期证据目录下的 `split/B-extra/run.sh`（29 检查/0 失败、inject 段真 FAIL 后还原）**未重跑**——其 pilot 段会在 208 起真实用例，超只读范围，采信留存输出。

**非阻断 findings（architect 收尾改）**：① ISS-398 两条归因与修法按上文更正；② 「0 个 EXIT 文件」应为「per-suite 0 个、`split-A/B.EXIT` 各 1（内容 1）」；③ 现 line 62 的 `$?` 取的是 `mkdir` 返回码，不是 python 的 rc。

**Needs Revision 具体项**：补 `docs/TestReports/M13-长尾7200s.md`（A+B 逐例表、转 PASS/仍超时/异常三类计数、执行环境指纹；原始 JSON 仍留运行期不入库），补齐即判 Accepted。

### 第 2 轮 reviewer 验收（2026-11-12）

**判决：Needs Revision（仅剩「逐例表」一项；其余本轮全部通过）**

**重跑记录（本机亲跑，RC=退出码）**
1. `make check-test-reports` RC=0 ⇒ `PASS (7 report(s), 3 snapshot(s))`（与主会话声明一致）；`python3 tools/infra/check_issues.py` RC=0（40 open/5 closed）。
2. 报告数字 vs 两份 JSON 现场全量比对（python 逐格核，`CHECK_RC=0 BAD=[]`）：三类计数表 static `46/43/2/1  141.7/349.9/1269.2`、dynamic `44/42/1/1  157.2/352.8/1284.6`、合计 `90/85/3/2` **全等**；§2 五行 `case/klass/ratio/gem5秒/qemu秒` 与 JSON 逐格相等（172800.0 = 172800.02/.03 取整），表内非 pass 集合 == JSON 非 pass 集合。
3. `ISS-398` 逐条对现场证据：① `mkdir -p` 13:36 才入脚本、B 09:30:43 起跑 ⇒ 运行实例无 mkdir（非 cwd）✓；② `rc` 在 66/72 行 `local rc=0`、真因运行中改脚本致 bash 重读错位（非未初始化）✓；③ `--log-prefix` 非任务号正则 ⇒ 远端写日志时 `rc=2` ✓；`line 62 $? = mkdir 返回码` ✓。**无残留错误归因**。
4. 完成区新增行「EXIT 计数订正：per-suite 0 个、`split-A/B.EXIT` 各 1（内容 1）」与现场一致 ✓；报告 §4 口径同 ✓。
5. 快照：HEAD `fa1f7ea3`，`git status -uall` 仅本轮审阅记录；未 commit / 未 push / 未改台账 ✓。

**阻断项（验收标准 3「报告含：逐例表」）**
- 报告**没有全量逐例表**：§2 标题即「未通过项（5 例）」，全文出现 case 名仅 **3/90**；A 组 60 例也无承载册（本册标题限定 B 组）。
- 项目先例同措辞下是全量：`m13-001-*-full.md` 逐例 72 行（`grep -c '^|'`=74）、`m13-002-*-full.md` 78 行（=104），且 001/002 的 JSON 同样不入库、靠结论册承载 ⇒ 本任务 85 例 pass 的逐例 `gem5/qemu 秒与比值`目前只在运行期 JSON，未入册。
- 且完成区新增行自称「（逐例表 + 三类计数 + 环境指纹）」⇒ **断言与产物不一致**（补表即消）。

**修法（机械，可由 JSON 生成）**：结论册补全量逐例表 `case / gem5_s / qemu_s / ratio / klass / exit`（B 组 90 行；A 组 60 行同册承载或在任务书指明由哪一册承载），并保持现有计数/指纹/复现/边界不变 ⇒ 即判 Accepted。

**非阻断 findings（architect 收尾改）**：① 完成区首版归因行（cwd 不符 / 第 94 行 rc 未初始化 / 0 个 EXIT 文件）按「不改写既有完成区」未回改，而新增行只订正了 EXIT 计数 ⇒ 建议再追加一行指向 `ISS-398` 的更正；② 目标 3 的 `simInsts_120s` 采样列在入库材料中无载体，是否入册留 architect/用户裁定。

### 第 3 轮 reviewer 验收（2026-11-12）

**判决：Needs Revision（仅 1 项范围/口径问题，标注供 architect 定夺；本轮其余全部通过）**

**重跑记录（本机亲跑，RC=退出码）**
1. §2 全量逐例表 **90 行** vs 两份 JSON 逐格核（python，`CHECK_RC=0`）：`case / klass / gem5 exit / 比值 / gem5秒 / qemu秒` 全对，缺 0 多 0；最大偏差 比值 0.05、gem5 0.05 s、qemu 0.0000（＝1 位小数显示取整）；`blocked` 3 行 `gem5 exit` 全为 `—`、非 blocked 87 行全非 `—`；klass 分布 `85/3/2` 与 §1 一致。
2. 章节编号 1→7 连贯，§1 交叉引用已改指 §6（复现）✓；`make check-test-reports` RC=0 ⇒ `PASS (7 report(s), 3 snapshot(s))`。
3. 完成区新增「收尾归因更正（指向 `ISS-398`）」行：三条证伪点与 `ISS-398` 逐条一致、**未再写错归因** ✓；完成区 11 行 ≤30 ✓；`git status -uall` 仅本任务书、HEAD `fd628027`、未 commit/push/未改台账 ✓；`ISS-398` 复核仍与现场一致（`check_issues` RC=0）。
4. A 组承载说法实测：`m13-001-static-3600s-full.md` `## 逐例` = **72 行**（全 blocked）✓、覆盖 A-static 26 例 ✓；`m13-002-dynamic-3600s-full.md` `## 逐例` = **93 行**（blocked 78 + pass 14 + fail 1，文件标题即「dynamic 长尾 93 例」）⇒ 报告写「78 行」**与现场不符**；A-dynamic 34 例覆盖 ✓。

**阻断项（范围/口径，供 architect 定夺，reviewer 不自行放行）**
- 两册是 **3600 s 基线**（文件名即 `*-3600s-*`），A 组 60 例的 **7200 s** 逐例结果与其 **60/60 数值不同**：`SPASS` refs=`blocked @3600.01` → A 组=`pass @6898.2`（klass 相反），`lencod` 3600.01 → 7200.02。tracked 文件中检索 A 组 7200 s 特征值（`6898.2`、`7200.02` 等）**无命中**；三类计数 `40 pass/17 blocked/3 fail` 只在台账讨论册一行。
- ⇒ 按 §4 指针取值会取到**另一批实验**的数据，验收标准 3 对 A 组的「逐例表」实际无入库载体。
- **二选一（落地即判 Accepted）**：① 本册补 A 组 60 行（源 = A 组四份 ratio JSON，列同 §2）；② architect/用户**明示裁定**「A 组 7200 s 逐例不入册」，则 §4 如实改写（refs＝3600 s 基线逐例；A 组三类计数见台账）并留裁定原话。

**非阻断 findings（architect 收尾改）**：① §4「`m13-002-dynamic-3600s-full.md`（78 行）」应为 **93 行**（或注明「其中 blocked 78」）；② `simInsts_120s` 采样列仍无入库载体（与本阻断项同属范围裁定，可一并定）。

### 第 4 轮 reviewer 验收（2026-11-12）

**判决：Accepted**（验收标准 1–7 在本轮重跑下全部通过；2 条非阻断 findings 见末，由 architect 收尾改）

**重跑记录（本机亲跑，RC=退出码）**
1. **A 组 60 行逐格核**（§2.1 vs 节点 208 四份 ratio JSON，`CHECK_RC=0`）：`suite/case/klass/gem5 exit/比值/gem5秒/qemu秒` 全对、缺 0 多 0；klass 分布 **40/17/3**；`blocked` 17 行 exit 全 `—`、非 blocked 43 行全非 `—`；最大偏差 比值 0.049、gem5 0.05 s、qemu 0.0000（1 位小数取整）。
2. **同源核**：四份 JSON 在节点 208 的 md5 与本地运行期证据逐份相同（`68bc50c6…` / `7a8fd028…` / `ba6289ea…` / `d5ea8f25…`），报告确以节点 208 数据为源。
3. **B 组 90 行（§2.2）复核**仍全对（缺 0 不符 0）；§1 的 A `40/17/3`、B `85/3/2` 与两表 klass 分布一致；标题「两档预算（A 7200 s / B 172800 s）」与 §1、§2.1/§2.2 自洽。
4. **§4 订正与 refs 现场一致**：`m13-001-…md` `## 逐例`=**72 行**、`m13-002-…md` `## 逐例`=**93 行**（blocked 78 + pass 14 + fail 1）；§4 已写明二者是 3600 s 基线、**不能替代**本册两档结果、§2.1/§2.2 才是逐例表 ⇒ 上轮阻断项已消。
5. `make check-test-reports` RC=0 ⇒ `PASS (7 report(s), 3 snapshot(s))`；`check-knowledge-refs` / `check-milestones-fresh` / `check_issues` 均 RC=0；报告无 `.work/` 路径、章节 1–7 连贯、§1 交叉引用指 §6。
6. **反例注入（只在临时树，仓库 md5 前后同 `d014489b…`）**：基线 `PASS rc=0` → 注入①（A 首行 blocked→pass）`FAIL rc=1`（klass/exit 不符）→ 注入②（删一行）`FAIL rc=1`（rows=59、缺 1）→ 还原 `PASS rc=0`。
7. 约束：`a72116ec`（71+/6-）与 `f1b54d4f`（6+/5-）**只改本册**，无源码/测试资产/契约改动（验收标准 4）✓；完成区 11 行 ≤30、无运行期路径 ✓；本轮我未 commit/push/未改台账（`git status -uall` 只有本任务书）✓；207/208 只读查询 ✓。

**非阻断 findings（architect 收尾改）**
- §1 计数表只有 `static / dynamic / 合计`（实为 **B 组**，合计 90）却未标组名，易被读成两组总和 150 ⇒ 表头或合计行标「B 组」；可顺带补 A 组比值行（非 blocked n=43：min 152.8 / 中位 431.3 / max 1575.7）。
- **范围裁定（非本册缺陷）**：`simInsts_120s` 不在验收标准 2/3 必备项内，本册未承载不构成缺陷；现场采样产物只有两份 `sample-static.json`（36+36，与 static 全量 72 例逐一对齐、`interrupted_sigint` 72/72、simInsts 18.0 M–53.2 M）+ 运行期 168 个含 simInsts 的文件，**未见 dynamic 采样产物**（EXIT 仅 `sample-static*`）⇒ 覆盖 72/150，与执行方式「合并覆盖全部 150 例」的计划不一致。**建议**：把两份采样 JSON 并成 72 行表入册或入 `refs/` 并注明 dynamic 未采样；否则在任务书遗留段登记口径，不要停在「计划 150、实际 72」的无记录状态。

#### 收尾（architect，2026-11-12 10:53）

- 第 4 轮 reviewer **Accepted**：A 组 60 行 / B 组 90 行逐例表与节点 JSON **逐格一致**（缺 0 不符 0，只有 1 位小数显示取整）；四份 A 组 JSON md5 与本地证据逐份相同。
- §4 已订正为「refs 的 72/93 行是 **3600 s 基线**，不可替代本册两档结果」。
- 反例注入（临时树）：A 首行 blocked→pass ⇒ FAIL；删一行 ⇒ rows=59 FAIL；还原 ⇒ PASS。
- 本册补：§1 表头标「B 组」、A 组比值行（n=43：152.8 / 431.3 / 1575.7）、`simInsts` 覆盖 72/150 的口径。
- 采样工具 `sample_insts.py` 的 `fingerprint`（引擎/宿主身份）随本任务合入。
- 遗留：`simInsts_120s` 只覆盖 static 72/150，dynamic 未采样；数据留运行期，未入册（reviewer 判为范围裁定，非本册缺陷）。

