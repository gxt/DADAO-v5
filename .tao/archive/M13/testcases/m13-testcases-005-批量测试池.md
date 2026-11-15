# m13-testcases-005: case 级批量测试池（多节点、即产即落、可续跑）

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（协议见 `docs/Process-09 §16`、`docs/Process-08 §1.9`，已生效）
**可并行分片**：否（工具实现）
**状态**：已验证

## 背景

`m13-testcases-003` 在 207/208 跑 150 例长尾时暴露三类等待放大：

1. **套件级波次**：`run_engine_ratio.py` 先跑完某套件的全部 qemu 才跑 gem5；一个 1103 s 的 qemu 挡住 35 例 gem5 约 18 min。
2. **结果攒批**：驱动在套件结束才写 JSON ⇒ 中途零可读结果，节点无法按「剩余量」调度。
3. **节点写死**：分片在脚本里固定，新增节点要改代码。

`docs/Process-09 §16` 已定五条原则与队列协议，本任务把它落成工具。

## 目标

实现 `tools/testcases/tset/gem5-se-baseline/run_pool.py`（命令 + 模块）：

1. **输入** `cases.jsonl`：一行一例 `{case, suite, link_mode, budget_s, class}`（`class ∈ short|normal|long|xlong`）。
2. **调度**：主控机侧按 `remote.py status` 的 `loadavg`/`disk_alert`/`running` 决定每个节点并发数（`--jobs-per-node`，默认取 `min(空闲核, 48)`）；**节点列表来自 `--hosts`，不写死**。
3. **执行**：每例一个独立命令，调用**既有驱动**（`run_llvm_ts_user.py` / `run_libc_test_user_suite.py` 的 `--only <case>`），**不重写构建/比对逻辑**；每例独立 `--work-dir`、独立超时（`budget_s`）。
4. **即产即落**：每例结束立刻向 `progress.jsonl` 追加一行（`Process-08 §1.9` 字段），并写 `state.jsonl` 状态变更（含 `attempt`、`node`、UTC）。
5. **幂等续跑**：`--resume` 读 `progress.jsonl` 的 `done` 集合跳过；`failed/timeout` 按 `--retry N` 重排，**重试次数记录**。
6. **xlong 隔离**：`class=xlong` 只派给 `--xlong-hosts` 指定的节点（默认 = 全部），且可设独立预算；**不得**占用主队列节点配额。
7. **指标**：结束时输出吞吐（例/h）、等待放大系数（Σ单例耗时 / (墙钟 × 节点数)）、每节点空转率、屏障次数（应 0）。

## 非范围

- 不改驱动/引擎/用例/期望（只调用）
- 不改 `run_engine_ratio.py`（它是套件级门控工具，保持现状）
- 不做结果归因/矩阵（`m13-integ-001` 的生成器负责）

## 验收标准

1. **功能**：在 207/208 上跑一个 **20 例** 混合样本（含 pass / fail / timeout 各若干），全部落 `progress.jsonl`，逐行字段完整、时间递增、无覆盖。
2. **续跑**：跑到一半强杀（SIGTERM），`--resume` 重跑 ⇒ 已 `done` 的例**不重跑**（用 `attempt` 计数与日志证明），未完成的补跑。
3. **等待放大系数 ≤1.5**（20 例样本，2 节点；给出实测值与算法）。
4. **新节点加入**：`--hosts` 增加一个节点后无需改代码即可接活（可用同一节点重复写两次模拟，或用 `--dry-run` 证明派单逻辑）。
5. **xlong 隔离**：构造一个 `xlong` 例，验证它只派给 `--xlong-hosts`、且不减少主队列在其他节点的并发。
6. **失败处置**：某例返回非零/超时 ⇒ 记 `failed`/`timeout` 并继续下一例，不中断整池；`--retry` 生效且次数可查。
7. 门控：`check-tasks` / `check-no-residue` / `check-run-artifacts` / L1 / L2 rc=0（外部红逐条核实）
8. 一键证据脚本（含可达 FAIL 注入：例如让 progress 写入失败 ⇒ 应显式报错）
9. 完成区 ≤30 行、无运行期路径

## 说明

- 协议真源：`docs/Process-09 §16`（不在任务书里另立一套）。
- 节点交互：主控机侧中转文件放 `.work/`，**禁 `/tmp`**；节点操作后 `make sync-node-repo`。
- 构建/调试在主控机；**不要占用 207/208 的长跑时段**（先查 `remote.py status` 的 `running`，有长跑时用 `--dry-run` 或等空闲）。
- 若发现需要改驱动才能按 case 调度，**停下登记并返回主会话**（可能需要先给驱动加 `--only` 支持）。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 完成区

**测试结果**：`run_pool.py --self-test` **82/82**；证据脚本**可重跑**：干净态 **rc=0**、紧接着二次执行 **rc=0**（各 39 项阶段 CHECK + 58 条内嵌数据 CHECK；其中 2 条 FAIL 属 `stale` 阶段的**预期**红）；`stale`（把 full 产物做旧）⇒ 校验器 **rc=1**、报 `artifact is stale`；L2 rc=0；L1 仅外部红（见 6）。
**修改文件**：`tools/testcases/tset/gem5-se-baseline/run_pool.py`（新增，任务 worktree 分支内）；本任务书（状态 + 完成区 + 审阅记录）。
**验收结果**：
1. 功能：20 例混合样本（16 pass / 2 timeout / 2 fail）逐例调用**既有驱动**（llvm-ts `--only '^id$'`，libc-test/embench `--filter '^id$'`；每例独立 `--work-dir`/`--json-out`/`budget_s`），未改驱动/用例/期望；`progress.jsonl` 20 行、§1.9 七字段齐备、`utc` 非降、`(case,attempt)` 唯一；`state.jsonl` 走 `pending→running→终态`。timeout 由 `budget_s=2` 对 `aha`（基线 guest ≈105 s）/`viterbi`（≈10 s）触发，fail 用不存在的 case id。
2. 即产即落 + 续跑：SIGTERM 在 **8/20** 例后停（rc=**130**、`[signal] SIGTERM`），盘上已有 8 行可读结果（非攒批）；`--resume --retry 1` 报 `skipped_done=8`，补跑 12 例 + 重试 4 例（2 timeout + 2 fail，`attempt` 1→2），done 例 `running` 次数恒为 1；**重试额度是硬上限**——额度耗尽后再次 `--resume` 不再重跑（`retrycap` 阶段：三趟轨迹 `[1,2]`、第三趟 `executed=0`），`blocked` 亦按终态跳过。
3. 等待放大（§16.2 **双报**）：Σ单例 **122.9 s**、墙钟 **61.991 s**；按节点 Σ/(墙钟×2) = **0.991**，按槽位 Σ/(墙钟×**2 槽**) = **0.991**（`nodes_active=2`、`slots_total=2`）；吞吐 **1161.5 例/h**；空转率 0.015/0.003；屏障 **0**、该轮 `retry_waves=0`（`retry_waves=1`/`barriers=1` 属 resume 轮）。**口径披露**：`hosts=[localA, localB]` 是**同一台主控机**的两个标签（`--local`；207 在跑 B 组、208 按指令不占），故"2 节点"= **2 个逻辑槽位**，该指标只作调度诊断，**不作**跨机吞吐/加速声明；早期节点验证同样是把同一台机器写两次（`[gxt@server208, gxt@server208]`）。两式在 1 槽/标签时同值，槽数≠节点数时分离（self-test：2 槽/节点 ⇒ 节点式 1.0、槽位式 0.5）。
4. 新节点：`--dry-run` + 记录态证明 1 标签→1 槽、2 标签→2 槽、忙节点 **0 槽**（reason `busy: …`），**代码不变**（真实忙节点案例由 reviewer 在 207 上实测：0 槽 + `busy: …gem5.opt…`）。
5. xlong 隔离：`class=xlong` 全部落 `--xlong-hosts`（localB），两标签主槽位仍各 1；xlong 槽 localB=1 / localA=0（主队列配额不减）。
6. 门控：`check-tasks`/`check-no-residue` rc=0；`check-run-artifacts` 本身 rc=2 但**无一条违规点名本任务**（违规 = 另一任务 reviewer 留下的一件非法命名文件）；L2 rc=0；L1 rc=2，红项 `check-patch-tree`/`check-temp-dirs`/`check-run-artifacts`/`check-milestones-fresh` 均**不点名本任务文件或目录**（逐条重跑核实，证据留存）。`compileall tools` rc=0。
7. 一键证据（10 阶段，含 `retrycap`/`stale` 两个不变量阶段）：注入（删 `plan_resume` 的 done-skip）→ 断言转红（重跑 2 例）→ `cp`+md5 还原 → 回绿（只跑 1 例）；`stale` 阶段专测"旧产物不许假绿"；`retrycap` 阶段专测"重试额度耗尽不重跑"。
**新发现/坑**：
- 第 2 轮阻断（已修）：`plan_resume` 在重试额度耗尽时只写 `notes`、**不进 `skip`** ⇒ 反复 `--resume` 会把 `attempt` 顶到 3、与 docstring「有额度才重排」矛盾；self-test 当时只断言 note 存在、没断言"被跳过"，所以单测抓不到。现改为**终态一律跳过**（`done`/`blocked`/额度耗尽的 `failed`·`timeout`），并补 4 条断言（耗尽在 `skip`、不重新入队、再 resume 不增 `attempt`）。
- **不要在 `run.sh` 运行期间编辑它**：bash 按偏移增量读脚本，改一次就可能让当前那趟以 `unexpected EOF` 死掉（本轮实测 1 次）；改脚本后必须整趟重跑再取证据。
- 证据脚本原先不清理固定 `--run-dir`：二次执行 rc=2，且数据断言会读上一轮旧产物**假绿**（reviewer 第 1 轮阻断项）。现每个阶段先 `rm -rf` **自己的** run 目录，所有数据断言前置"产物 mtime ≥ 阶段起点"，`stale` 阶段把该路径当反例常驻。
- `remote.py status` 的 `running=` 正则含 `run_[a-z_]+suite\.py`：`--local` 下会把本机 ssh 载荷/其它会话的 driver 认成"有活在跑" ⇒ 派单阶段用 `--allow-busy`（plan 阶段改用记录态以免断言随宿主负载漂移）。
- 逐例独立 `--work-dir` 的固有成本：libc-test 每例重建 `libtest.a`（节点上约 40 s/例，占该例墙钟 ~95%；本机 ccache 热后约 5 s）。
- `check-run-artifacts` A2/A3 扫**活动**目录：并发跑门控会瞬时看到别人未写完的 run 目录/日志 ⇒ 该门控 1 次重试 + "无违规点名本任务"判据（本次重试后仍红，属外部）。
**遗留问题**：无功能遗留。L1 四处外部红待并发任务收口后由主会话复跑确认回绿；证据运行目录内的逐例产物已按 Process-08 §1.8 清理，只留脚本/校验器/汇总/日志。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `run_pool.py` + 证据脚本，边实跑边发现即改：

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `STATUS_*` 用字符串 ⇒ `sys.exit("0")` 实退出码 1 | ✅已修 | 改整型常量 | self-test rc=0；证据 `full rc=0` |
| F2 节点 status 键名正则 `[A-Za-z_]+` 静默丢掉 `qemu_md5` | ✅已修 | 允许数字 + 新增 self-test 用例 | self-test 70/70（`status key with digit`） |
| F3 信号必须打到 python 本体（后台化 shell 函数只杀包装子 shell） | ✅已修 | 证据脚本直接 `python3 … &`；pool 收到 SIGTERM 只停派单、在飞例跑完 | run1 rc=130 + `[signal] SIGTERM` + 8 行已落盘 |
| F4 停止后节点仍被上次 ssh 载荷占用 ⇒ `--resume` 判 0 槽 rc=2 | ✅已修 | 证据脚本加 `wait_node_idle`（轮询 `running=none`） | resume rc=0、skipped_done=8 |
| F5 上轮残留的节点 `result.json` 可能被当本次判决 | ✅已修 | 节点逐例目录带 run 名 + 跑前 `rm -f result.json` | 20 例判决与驱动一致；重试 attempt 正确 |
| F6 xlong 队列原本在主队列排空后才开跑（退化成屏障） | ✅已修 | 两队列各自 slot 组并发起跑 | xlong 阶段两槽同时有活；amp 0.99 |
| F7 队列跑完未断言"每个 case 有终态记录"（线程静默死会漏判） | ✅已修 | 收尾 `unrecorded` 校验（非中断 ⇒ rc=1） | 全量 run：queued=20 / terminal=20 |
| F8 `--jobs-per-node` 负数只在排空时以"无槽位"报错 | ✅已修 | 参数入口显式校验 | 手测负数 ⇒ rc=2 + 明确报错 |
| F9 死代码：`_HOST_INDEX`、first/last 统计、未用 `TERMINAL` | ✅已修 | 删除 / 改用于终态校验 | `py_compile` + self-test |
| F10 `--local` 把本机 ssh 载荷误判为"忙"（同坑 1） | ✅已修 | 证据脚本本地阶段 `--allow-busy` + 注释 | xlong/inject 阶段 rc=0 |

判决：全部 finding 已修，状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-10，全部本人实跑）

**重跑记录（真实输出 / 退出码）**
- `./run.sh selftest plan` → **RC=0**：`self-test: 70/70 checks passed`；plan `one=1 two=2 busy=1`，207 判 0 槽 reason `busy: …gem5.opt…`，208 照常 1 槽。
- `./run.sh xlong inject` → **RC=1**：`CHECK xlong rc expected=0 actual=2 rc=FAIL`，日志 `ERROR: progress.jsonl already has 4 row(s); pass --resume …`；紧随的 `xlong data assertions rc=0` 读的是上一轮 16:55 的旧 `progress/summary`（**stale PASS**）。同因复现：对 `runtime/full`（20 行残留）用 `--hosts localA --local` 跑 → `ERROR: …20 row(s) …` **RC=2**（未接触节点）。根因 = `stage_full/run1/xlong` 不清理固定 `--run-dir`。
- `./run.sh gates` → **RC=0**（10 checks 0 failed）：`check-tasks`/`check-no-residue`/`check-run-artifacts`/`compileall`/L2 全 0；L1 rc=2 仅 `check-patch-tree`（gem5 断言⑨）与 `check-temp-dirs`（`m13-gem5-004-work`、`m13-gem5-003-runtime`），均不点名本任务 ⇒ 外部红核实成立。
- 自建 **SIGTERM+resume**（`--local`，不占 207/208）：10 s SIGTERM → **RC=130**、`[signal] SIGTERM`、盘上 **4/8 行**（即产即落）；`--resume --retry 1` → `skipped_done=4` **==** 中断时 done 集合，done 例 `running` 计数**恒为 1**，3 例 `attempt [1,2]`，8/8 终态，**RC=0**。工程侧产物同核：`skipped_done=8` == 中断时 8 个 done，20/20 终态。
- **xlong 隔离**（fresh run-dir，RC=0）：xlong 只落 `localB#2`；main 槽 `{localA#1:1, localB#2:1}`、xlong 槽 `{localA#1:0, localB#2:1}` ⇒ 主队列并发不减。
- **busy 误判复现**：case 在跑时 `remote.py status --local` 的 `running=` 含 `run_libc_test_user_suite.py` ⇒ `decide_slots(...,False)=(0,'busy: …')`、`allow_busy=True=(1,'idle=62, cap=1')`；`--allow-busy` 只豁免 busy，**不**豁免 `disk_alert`/`loadavg`（语义正确）。
- **独立注入（本人）**：`Journal.progress_row` 丢行 → `./run.sh selftest inject` **RC=1**（self-test 68/70；`restored build runs only the pending case expected=1 actual=2 rc=FAIL`）→ `cp`+md5 还原（`00f40477…` 前后相等）→ 同脚本 **RC=0**（70/70、7 checks 0 failed）。另 `--inject-progress-failure` → **RC=3**、`progress.jsonl` 不存在、`stopped fail-closed`（run.sh 未覆盖该路径）。
- **产物核验**：progress 20 行 §1.9 七字段齐、`utc` 非降、`(case,attempt)` 唯一；state 走 `pending→running→done|failed|timeout`（`blocked` 由 self-test 覆盖）；每行 open+flush+fsync，**无攒批**。

**阻断项（Needs Revision 根因）**：`run.sh` 不可重跑——`full`/`run1`/`xlong` 二次执行 rc=2，且数据断言会读旧产物照常 PASS（`lessons §2.14`「提交后仍应回绿」不满足）。修法：三阶段开跑前 `rm -rf` 自己的 `--run-dir`（`resume` 依赖 `run1`，须断言产物新鲜/由上一阶段刚产出），数据断言先校验产物 mtime 晚于阶段起点。**预期**：干净态与二次执行均 RC=0，stale 时显式 FAIL。
**完成区须更正（随返工一并改）**：① `Σ单例 777.6 s` 与实测 **780.053 s** 不符（0.986 对应 Σ=780.05；777.6/791.2=0.983）；②「2 节点」实为 `hosts=[gxt@server208, gxt@server208]`（同机两标签），完成区未披露；③ 该轮 `retry_waves=0`（`retry_waves=1` 属 resume 轮）。
**约束核验**：只改本任务书（审阅记录）；`run_pool.py` md5 前后 `00f40477…` 一致；未 commit（HEAD 仍 `4109b139`）；主工作树 `git status` 干净（ISS-368）；完成区 20 行 ≤30、无运行期绝对路径；全程未在 207/208 执行用例（仅只读 `status`）；临时件在 `/tmp/opencode/m13-testcases-005-review/`；原 run.sh 各阶段日志已备份至该目录。

**判决：Needs Revision**（仅 `run.sh` 清理/新鲜度 + 完成区三处数字/口径；`run_pool.py` 协议、续跑、xlong、busy、失败处置、注入、门控各项实跑均通过）。

### 第 1 轮 engineer 返工（2026-11-10，回应 Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| R1 证据脚本不可重跑：`full`/`run1`/`xlong` 二次执行 rc=2，且数据断言读上一轮旧产物**假绿** | ✅已修 | `run.sh` 每阶段先 `fresh_run_dir`（只删本任务自己的 run 目录，含 `selftest`/`plan`/`inject`）；新增 `verify.py`，所有数据断言前置「产物 mtime ≥ 阶段起点」；`resume` 增 `run1/.stage-start ≥ SUITE_START` 断言 | 干净态 **rc=0**；紧接着二次执行 **rc=0**（两轮各 84 条 CHECK、33 项阶段 CHECK 0 failed） |
| R2 「旧产物假绿」先前无守门 | ✅已修 | 新增 `stale` 阶段：把 `full` 产物 `touch` 成 2020-01-01 后跑校验器，**必须红** | 校验器 rc=1、`progress.jsonl artifact is stale: mtime=1577836800`；阶段断言「必须红」PASS |
| C1 Σ单例与实测不符 | ✅已修 | 完成区改成本轮实测 **122.698 s**（墙钟 62.851 s），并给出两式结果 | Σ/(墙钟×2 节点)=**0.976**；Σ/(墙钟×2 槽)=**0.976** |
| C2 「2 节点」未披露为同机两标签 | ✅已修 | 完成区写明 `hosts=[localA,localB]`（`--local`，同一台主控机）+ 早期节点验证是 `[gxt@server208, gxt@server208]`；补 `nodes_active`/`slots_total` 双口径与「不作跨机吞吐/加速声明」 | 完成区第 3 条；`summary` 同时给 `nodes_active=2`、`slots_total=2` |
| C3 `retry_waves` 轮次写错 | ✅已修 | 分开写：`full` 轮 `retry_waves=0`/`barriers=0`；`resume` 轮 `retry_waves=1`/`barriers=1` | 两轮 `run.out` 的 `[done]` 行（另加校验器断言 `retry waves 0 in this stage`） |

判决：全部处置完成，状态 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-10，全部本人实跑）

**重跑记录（真实输出 / 退出码）**
- **可重跑**：`run.sh`（9 阶段）**连跑两次 → RUN1_RC=0 / RUN2_RC=0**，各 `33 checks, 0 failed`；全脚本 `84 CHECK = 33 阶段 + 51 内嵌`（plan 6 + verify-full 22 + verify-resume 11 + verify-xlong 9 + stale 3，现场逐条数得），仅有的 2 条 `rc=FAIL` 在 `stale` 阶段（预期红）⇒ 与声称三情形一致。
- **新鲜度断言**：把 `progress.jsonl` mtime 改到 2020 → 校验器 **rc=1** + `artifact is stale: mtime=1577836800`；`cp -p` 还原 → **rc=0**、md5 一致。`stale` 阶段常驻反例 rc=1 判 PASS。
- **可重跑反例（本人注入）**：`fresh_run_dir` 改为不删 → `run.sh xlong` **rc=1**（`xlong rc 0/2`、`progress.jsonl is fresh … False`、`data assertions 0/1` 三处红）→ `cp`+md5 还原 → **rc=0**（11 项全 PASS）。
- **旧产物 + 新阶段**：单独跑 `run.sh resume` → **rc=1**，`run1 stage ran in this invocation expected=True actual=False` ⇒ 该断言真生效。
- **指标双报**：本轮实测 Σ=119.472 / 墙钟 60.313 / `nodes_active=2` / `slots_total=2` ⇒ 节点式 0.990 = 槽位式 0.990（我按两式复算一致）；工程侧 run.out 的 Σ=122.698、62.851、0.976、1145.6 与完成区**逐字一致**，复算 122.698/(62.851×2)=0.976。`retry_waves`：full=0/barriers=0、resume=1/barriers=1，各自正确。
- **门控亲跑**：`check-tasks`/`check-no-residue`/`compileall`/L2 **rc=0**；`check-run-artifacts` rc=2，唯一违规是另一任务的非法名日志文件；L1 rc=2 四项（`check-milestones-fresh` 违规 = `m13-testcases-006`、`check-patch-tree` = gem5 断言⑨、`check-run-artifacts` = 同上那件、`check-temp-dirs` = gem5/infra/004-review 的临时目录）——**均不点名本任务**。白名单可达 FAIL 已验：给本任务日志目录造一个非法名文件 → 违规计数 **1**（会判红），删掉 → 0。
- **注入**：`run.sh inject` 两轮均 5 项全 PASS（改文件 / 重跑 2 例 / md5 相等 / 还原只跑 1 例 / rc=0）。

**阻断项（新发现：代码行为与自述合约矛盾）**：`plan_resume` 在重试额度耗尽时只写 `notes`（`not retried`）**却不进 `skip`** ⇒ 下一次 `--resume` 照样重跑。干净复现（独立运行目录、4 例、连续三次执行）：首跑 attempt=1 → resume#1 attempt=2（正确）→ resume#2 打印 `not retried: … attempts=2 >= 1+--retry 1: not retried` 却 `executed=1`、attempt 轨迹 **[1,2,3]**；同一现象使证据脚本自身断言 `retry attempts are capped by --retry 1 expected=2 actual=3` **FAIL**（单独跑 resume 那轮实测）。与 docstring「re-queued only when an attempt is left under --retry」、`--retry` help（default 0）、日志措辞直接矛盾；self-test 只断言 note 存在、不断言该例被跳过 ⇒ 单测抓不到。修法：额度耗尽即 `skip[case] = reason`（`notes` 仅作报告），并补 self-test「耗尽后再次 resume 不重跑」；预期连跑三次 resume attempt 恒 ≤1+`--retry`、`run.sh` 两次 rc=0。
**约束核验**：完成区 20 行 ≤30、本轮记录无运行期路径；未 commit（HEAD `dbfc1009` 为 architect WIP）；主工作树干净（ISS-368）；全程未在 207/208 执行用例（脚本默认 `LOCAL=1`）；两处注入均 `cp`+md5 还原并复核相等。
**判决：Needs Revision**（仅上述 `--retry` 跨次 resume 的跳过逻辑 + 对应断言；可重跑、新鲜度、双报口径、同机两标签披露、门控归属本轮全部实跑通过）。

### 第 2 轮 engineer 返工（2026-11-10，回应 Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| R3 `--retry` 额度耗尽后仍会重跑（`attempt` 1→2→3），与 docstring 矛盾 | ✅已修 | `plan_resume`：额度耗尽 ⇒ **写进 `skip`**（`notes` 仅作报告）；`blocked` 一并按终态跳过 | self-test 82/82；`retrycap` 阶段轨迹 `[1,2]`、第三趟 `executed=0`；`resume` 轮校验器 `retry attempts are capped by --retry 1 expected=2 actual=2` |
| R3b self-test 只断言 note 存在，抓不到"仍在重跑" | ✅已修 | 新增 4 条断言：耗尽例在 `skip`、`pending` 不含它、再 resume 不增 `attempt`、`blocked` 属终态 | `--self-test` 82/82（原 74 项 + 8 项新判据） |
| R3c 证据脚本缺这一路径的常驻用例 | ✅已修 | 新增 `retrycap` 阶段（run → `--resume --retry 1` → `--resume --retry 1`），并入默认阶段表 | `run.sh` 两趟各 rc=0；`retrycap.EXIT=0` |

判决：全部处置完成，状态 `待验收`。

### 第 3 轮 reviewer 验收（2026-11-10，全部本人实跑）

**重跑记录（真实输出 / 退出码）**
- **阻断真修（干净目录连跑三趟）**：首跑 `executed=4`（failed, attempt=1）→ resume#1 `executed=1`（attempt=2）→ resume#2 `skipped_done=4 pending_main=0`、`[resume] not retried: … not retried (quota exhausted)`、`[done] executed=0`；attempt 轨迹 `functional/not-a-case-typo [1,2]`，全场 max=2 = 1+`--retry`；日志含 `quota exhausted` ✓。
- **`retrycap` 阶段（三趟常驻反例）**：`executed nothing` / `reports the exhausted quota` / `attempt trajectory is [1,2]` / `attempt cap holds` / `one verdict row per attempt` / `stays failed` 六项全 PASS，`MEASURE retrycap attempts=[1,2]`。
- **连跑两次**：`run.sh`（10 阶段）**RUN1_RC=0 / RUN2_RC=0**，各 `39 checks, 0 failed`；**97 条 CHECK = 39 阶段 + 58 内嵌**（plan 6 + verify-full 22 + verify-resume 11 + verify-xlong 9 + retrycap 7 + stale 3，逐日志现场数得），2 条 `rc=FAIL` 全在 `stale`（预期红）。
- **self-test 82/82**（RC=0）。新增 8 条（净 +8：新增 12 个判据名、删改 4 个旧名）——本人注入「把 `skip[case]=note` 删掉」→ **78/82**，红的恰是 4 条新判据：`retry 0 skips done/exhausted/blocked`（`['a','b','c','d']` vs `['a','d']`）、`exhausted retry is skipped`、`exhausted case is not queued again`（`['c']` vs `['b','c']`）、`a further resume keeps the same cap`；同轮 `retrycap` 轨迹变 `[1,2,3]`、`executed nothing` 转红 ⇒ **无恒真、可达 FAIL**；`cp`+md5 还原 → 82/82、RC=0。
- **主 resume 轮**：`skipped_done=8`、补 12、重试 4 例 `attempts=[1,2]`（`aha`/`viterbi`/两个 typo），`retry attempts are capped expected=2 actual=2` PASS；`run1` 轮 `[signal] SIGTERM` + `executed=8`。
- **指标**：完成区 `Σ=122.9 / 墙钟 61.991 / 0.991 / 1161.5` 与证据输出逐字一致，我复算 122.9/(61.991×2)=0.991、20/61.991×3600=1161.5 ✓。
- **门控**：`check-tasks`/`check-no-residue`/`compileall`/L2 **rc=0**（本人单跑复核）；`run.sh gates` **RC=0**，`check-run-artifacts` rc=2 与 L1 四项（`check-milestones-fresh`→`m13-testcases-006`、`check-patch-tree`→gem5 断言⑨、`check-run-artifacts`→另一任务的非法名日志、`check-temp-dirs`→gem5/infra 临时目录）**均不点名本任务**。
- **注入**：`run.sh inject` 两轮 5 项全 PASS（注入点已改为「skip-done 换 pass」，保持文件有效）。

**`blocked` 终态跳过的判断：合理，但需补一句说明。** `blocked` 是已判定的平台缺口（终态），与 round-1 docstring「never retried」及状态机一致；**改前它在 resume 时反而会被重跑**（与本轮阻断同类的隐患），改后才自洽。残留提示：平台缺口修好后 `--resume` 不会自动重试，须换运行目录（或删该行）重跑；该语义目前只在 docstring，`resumed_skipped` 也只列 case 不列原因，建议在 `[resume]` 日志或完成区写明。样本里没有天然 `blocked` 例，该分支仅由 self-test 覆盖（已在 82 项中）。
**约束核验**：完成区 22 行 ≤30、本轮记录无运行期路径；未 commit（HEAD `4498f58d` 为 architect WIP）；主工作树干净（ISS-368）；全程未在 207/208 执行用例（脚本默认 `LOCAL=1`）；两处注入均 `cp`+md5 还原并复核相等（`run.sh e044e9c2…`、`verify.py 8240d9f8…`、`run_pool.py e44d240b…` 与快照一致）；快照对账无差异。
**判决：Accepted**（第 2 轮唯一阻断已实证修复；可重跑、新鲜度、双报口径、同机两标签披露、门控归属本轮全部复跑通过）。

#### 收尾（architect，2026-11-10 21:04）

- 第 3 轮 **Accepted**：retry 硬上限生效（三趟 attempt 轨迹 `[1,2]`、第三趟 `executed=0`、日志 `quota exhausted`）；`run.sh` 连跑两次均 rc=0（97 条 CHECK，2 条预期红在 `stale`）；self-test 82/82，reviewer 注入「删 skip[case]」⇒ 4 条新判据红 + retrycap 轨迹变 `[1,2,3]` ⇒ 还原回绿。
- 指标：Σ122.9 / 墙钟 61.991 / 2 标签 ⇒ **0.991**；吞吐 **1161.5 例/h**。
- 终态语义：`done`/`blocked`/额度耗尽的 `failed`/`timeout` 一律跳过；仅「仍有额度」的 `failed`/`timeout` 重排。
- 遗留：① 跨机两节点实测未做（本轮 `hosts` 是同机两标签，已披露），待 207 空闲后补测；② `blocked` 跳过原因未落日志/完成区，建议后续补一行。
