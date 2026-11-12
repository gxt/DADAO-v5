# m13-testcases-003: 3600s 仍超时的例 × 7200s 复核

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-001` + `m13-testcases-002`（取「3600s 仍超时」的名单）
**可并行分片**：否（单机 48 并发跑批；测时间要求进程独占核）
**状态**：待验收

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
- **EXIT 计数订正（reviewer）**：per-suite `.EXIT` 0 个；`split-A.EXIT`/`split-B.EXIT` 各 1 个（内容 `1`）。
- 人读结论已落 `docs/TestReports/M13-长尾7200s.md`（逐例表 + 三类计数 + 环境指纹）。

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

