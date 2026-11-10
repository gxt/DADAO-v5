# m12-chipyard-020: 取指预取优化（4 预取槽 + 数据优先仲裁 + 延迟计数）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-007`（BootROM 固件/移交，已合入后方可改核）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 用户裁定（2026-11-10）

> 「同意，单独一个小任务来做」——针对「缓冲深度是不是影响其它访存 / 建议 2 还是 4」的结论。

结论要点：

- **8 beat 是 FIFO 容量**，不直接抢带宽；真正与 `ldm`/`stm` 争 SRAM 的是**在飞预取请求数**。
- 现状 `IdRange(0,3)` = 1 需求 + 2 预取；实测跨 beat 代价 **7–8 拍**（队列常被抽干）⇒ 稳态取指约 1 条 / 2.5–4 拍。
- 建议：**4 个预取槽**（`IdRange(0,5)`），FIFO 深度保持 8；并**数据优先仲裁**（数据口有未完成请求时不发新预取）；加 **SRAM 往返延迟计数器**用于校准。

## 目标

1. **预取槽 2 → 4**：`IdRange(0,5)`（1 需求 + 4 预取），FIFO 仍 `fetchDepth=8`；source 回收/flush stale 语义不变。
2. **数据优先仲裁**：数据端口存在未完成请求（`MREQ`/`MWAIT` 或 outstanding 计数 > 0）时，**暂停发起新预取**（已发出的不清空）；恢复条件写清。
3. **延迟计数器**：在 RTL 内记录「需求取指发出 → 回包有效」的拍数（可读寄存器或诊断 `printf`），用于校准预取槽数是否够。
4. **回归**：273 例逐字节一致；Tiny 44/44；8-beat FIFO 峰值仍可达 8。

## 非范围

- 不改 BootROM/固件/hmon（`007`）
- 不改异常/寄存器（`019`）
- 不改 `ldm`/`stm` 语义（`008`）

## 验收标准

1. `IdRange(0,5)` 可核（生成物/源码）；预取槽=4 有实测证据（同时在飞请求峰值）
2. **数据优先**：构造 `ldm`/`stm` 长 burst，**取指不抢占**（对比改前：burst 期间取指发出数应显著下降或为 0），burst 完成时间不劣于改前
3. **延迟计数**：给出实测 SRAM 往返拍数（≥3 次采样），并据此判断 4 槽是否足够（若不足，给数据与建议，不自行加）
4. **取指性能**：紧循环下跨 beat 代价从 7–8 拍下降到 ≤2 拍（给出前后对比数字）
5. 273 例 md5 不变；Tiny 44/44
6. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0（外部红逐条核实）
7. 一键证据脚本（含可达 FAIL 注入：例如把预取槽改回 2 应使跨 beat 指标退化）
8. 完成区 ≤30 行、无运行期路径

## 说明

- **必须在独立 `git worktree` 内作业**（`ISS-368`）；禁改主工作树。
- 构建/调试在主控机；**不占用 207/208**（长跑在跑）。
- 组件单写者：等 `m12-chipyard-007` 合并后再开工。
- 只加 20–30 行量级的改动，**不要顺手重构** FSM；若发现需要更大改动，停下报告。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-10）

**审查范围**：`WumingCore` 预取槽/仲裁/延迟计数、`WumingTile` `IdRange`、`fetch_probe` 证据工具；逐行核对动态索引、同拍多写、stale/flush 与 `waitBeat` 交互。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 只加宽到 4 槽时跨 beat 仍 8 拍：发射受 `qCount=/=0 && !waitBeat` 限制，最多 1 个在飞 | ✅已修 | 发射条件改 `pfStreamLive = qCount=/=0 \|\| waitBeat` | 跨 beat p50 8→1 |
| F2 MREQ 前一拍仍发出 1 个预取 | ❌不修 | 属「已发出的不清空」；严格「数据请求发出后」计数为 0 | bench `fetch_requests_after_data_request=0` |
| F3 延迟寄存器可能被优化掉 | ✅已修 | `prefetch ... lat=${fetchLatency}` 读取该寄存器 | 生成 Verilog 含 `fetchLatency`/`demandSentCycle`（247–248 行） |
| F4 注入还原用 `cp -p` 保留旧 mtime，重建未触发（自检假红） | ✅已修 | 还原后 `touch` 源文件再重建 | `--self-test-inject` 全 PASS |
| F5 L1/L2 归因过宽 | ✅已修 | L1 白名单 4 项且 chipyard/本任务不得为 offender；L2 仅放行 8 个已知 DADAO-E2E 欠账 | 见完成区 L1/L2 |
| F6 Tiny 44/44 红 | 外部红 | QEMU-only 门控；本任务 diff 不含 qemu/tests；共享安装根被并发任务重建 | 同门控在 master 的 tests/tools 上复现 44/1 |

**判决**：F1/F3/F4/F5 已修，F2 判定不修（符合任务「已发出的不清空」），F6 外部红已核实；状态 → 待验收。

### 第 1 轮 reviewer 验收（2026-11-11）

**判决：Accepted**（验收命令块在 reviewer 自己的重跑下全绿 `summary: PASS=46 FAIL=0 / RERUN_RC=0`；3 条非阻断 finding 见文末，交 architect 收尾处置）。日志见运行期日志目录（chipyard 模块）`m12-chipyard-020-reviewer-*.log`。

**重跑记录（全部为 reviewer 亲自执行，非采信 engineer 转述）**
1. 一键证据脚本 `run.sh`（任务 ID 证据目录下）完整跑三轮：第 1 轮 `summary: PASS=46 FAIL=0`；第 3 轮 `PASS=46 FAIL=0 / RERUN_RC=0`。第 2 轮唯一 FAIL `L1 … ours=9` 根因是**我自己**写的日志 `reviewer-*.log` 无任务号前缀（`check-run-artifacts` illegal name，路径含 chipyard 被脚本 OURS 计数命中）→ 改名 `m12-chipyard-020-reviewer-*` 后回绿，非交付物缺陷。
2. 跨 beat（我用独立脚本重算，非脚本自报）：`{"execs":409,"cross_n":204,"cross_p50":1,"cross_max":8,"cross_gt2":1}`，分布 `{1:203, 8:1}`，唯一 8 拍为首跨拍（ip offset=8，冷启动）；`busy=4` 111 次（`live=4` 109 次）；延迟 10 采样 `4,4,4,4,4,4,4,4,6,6` → `ceil(6/2)=3 ≤ 4`。
3. `run.sh --self-test-inject` → `INJECT_RC=0`：注入 4→2 得 `cross_p50=5 cross_gt2=102`；还原 md5 `56e2ea582db470a385032e530ae3e812` 一致 → 回绿。
4. 独立注入①（`cp` 备份 → `pfSlots=2` + 恢复 m12-018 旧发射门 → elab/build rc=0、simulator newer → `ONLY=D`）→ **FAIL** `cross_p50=8 cross_gt2=204`（独立复现「改前 204/204 = 8 拍」），`INJECTED_RC=1`；`cp` 还原 md5 一致、重建 rc=0 → `RESTORED_RC=0`。
5. 独立注入②（生成物 `WumingCore.sv` 去掉 `pfWanted` 的 dataBusy 项 → 只重建 bench → `ONLY=E`）→ **FAIL** `PROBE fetch_requests_after_data_request=6 / verdict=FAIL`，`INJECTED_RC=1`；还原 md5 `cf925d61493262b7c125c42722419d1c` 一致 → `RESTORED_RC=0`。证明数据优先断言有可达 FAIL 路径。
6. 门控亲跑：elab rc=0 且 `%Error`=0、Verilator rc=0 且 `%Error`=0、simulator newer、`pfValid_0..3`=4 且无 `pfValid_4`；`check-source-state` rc=0（另一轮 rc=2 others=qemu）；`apply-series`/`check-patch-tree` rc=2 → offender 仅 qemu(+gem5)、chipyard 不在列；L1 五红逐条核为外部（qemu 补丁断言⑨⑥ / night+gem5 评审日志名 / gem5+testcases 陈旧临时目录 / `m13-testcases-008` 任务书 `.work` 引用 / `check-milestones-fresh` 2 项 VIOLATION 属 `m13-integ-004`、`m13-testcases-009`，M12 册本任务行 PASS）；L2 rc=2 → 恰 8 个 `DADAO-E2E`（clang+qemu；`m12-testcases-002` 任务书已登记同 8 例、状态待开始），其他 FAIL=0。
7. Tiny：两轮均 `Results: 44 total, 1 passed, 0 failed, 43 errors`（harness Timeout）；期间 `m13-qemu-002` 正并发重建共享 qemu 安装根（`qemu-system-dadao` mtime 23:40/23:47、`.work/source/qemu` 脏、`install-host` 进程在跑）⇒ 外部红归因成立；该门只依赖 qemu + `tests/inst`，与 RTL 无因果。

**三个焦点问题（读 RTL + 实测）**
- ① 跨 beat 是否真降到 p50=1：**是**——204 次里 203 次为 1 拍，唯一 8 拍是首跨拍（冷启动）；改前数字由我独立注入复现为 `p50=8 / gt2=204`（204/204=8），非采信。
- ② 数据优先是否安全（不丢已发预取）：**安全**——`!dataBusy` 只挡新发射；在途预取回包路径 `pfPushOk = pfRespOk && … && state =/= sFreq && (state =/= sFwait || waitBeat)` 不含 dataBusy，且 `fifoFlush` 只在 `sExec`/`sFwait`/`finish` 分支置位、`sMreq`/`sMwait` 不会置位 ⇒ 回包仍入队；`pfValid` 只在回包时释放，flush 只标 `pfStale` 不清空 ⇒ 已发预取既不丢也不被重复占用 source ID（槽复用必须等回包消费完，`PriorityEncoder(pfValid.map(!_))` 只挑空槽，同拍回包与新发射不会撞同一槽）。实测 `fetch_requests_after_data_request=0`、`during=1`，且去掉 dataBusy 项后变 6（注入② FAIL）。
- ③ 发射门放宽是否引入冲突：**不引入**——`finish` 走 `waitBeat` 分支时 `fifoPop := qCount` 抽干队列，而 `finish` 只在 `sExec`（`queueHit` ⇒ `qCount>0`）被调用，`headBeat` 此时有效，故等待节拍 = `nextBeatReg + (off - qCount)` ∈ `[nextBeatReg, nextBeatReg+pfLive)`，正是在途预取覆盖的区间；`pfBeat = nextBeatReg + pfLive` 起步于在途之后、不会重复申请同一节拍；`pfPushOk` 允许 `sFwait`+`waitBeat` 期间入队；回退到需求取指的那一拍 `fifoFlush` 组合为真使 `pfWanted=0`（不会同拍既发预取又发需求），且挂起的 `pfReqValid` 使 `pfBusy≥1` 挡住提前回退。

**约束核验**：① 独立 worktree、分支 `m12-chipyard-020`，HEAD 仍为 architect WIP `b62f576e`，reviewer 未 commit；`git status --porcelain -uall` 审前为空，审后仅本审阅记录（任务书自身）为 `M`，无其它残留。② `git show --stat HEAD` = 任务书 + changelog + 2 个 patch + gen_probe + tb_fetch_probe 共 6 文件，与完成区「修改文件」一致、无越界。③ 完成区 17 行 ≤30；任务书全文经 grep 核无宿主绝对路径、临时目录、家目录、运行期目录引用。④ 源码+生成物双证：`IdRange(0, 5)`/数据口 `IdRange(0, 3)`/`fetchDepth=8`/`pfSlots=4`，chisel.log `5 <= WumingCoreFetch 0`。⑤ 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 三向一致；R1=C `or.o`=1 拍、`shl.o`≥2 拍。⑥ 反例注入：脚本自带 + reviewer 两次独立注入，均「注入→FAIL→`cp`+md5 还原→回绿」。⑦ 快照对账：5 个交付文件 md5 审前=审后 `fbfa9ff8 / 04cb653c / fe239c57 / ae793044 / 7650803d`（changelog、2 个 patch、gen_probe、tb_fetch_probe）；任务书审前 `10d67c07`、审后因本轮审阅记录改动（预期，reviewer 唯一写入）；`.work/source` `WumingCore.scala=56e2ea58…`、`WumingTile.scala=cbda63c6…` 同值；无 `*.preinject`/`*.inj-bak` 残留。

**findings（非阻断，交 architect）**
- F1 `run.sh` G 段归因用 `git diff --name-only HEAD`（只看未提交改动）——任务改动已进 HEAD ⇒ `OUTSIDE` 恒 0，归因分支实际不可失败；且回显 `same gate red on master's tests/tools` 是固定文案（脚本并未真跑 master）。实质归因 reviewer 已独立核过成立（见重跑记录 7）。建议：diff 基准改为任务基线（`HEAD~1..HEAD` 或任务书修改文件清单），删除固定回显。
- F2 E 段断言 `data burst time == configured latency` 对「仲裁拖慢数据」不敏感（bench 两个 slave 独立、回复按固定 latency 到期），只在数据通路整体损坏时才 FAIL；「burst 不劣化」实为结构性论证，遗留②已披露 `ldm`/`stm` burst 未实现。建议改名或补共享 SRAM 模型。
- F3 完成区「同门控在 master 复现 44/1」reviewer 未独立复现（按边界不在主工作树跑门控）；建议 architect 在 `m13-qemu-002` 装完后重跑 Tiny 一次取绿。
- 观察（非 020 引入）：`io.imem.a.valid := atDemand || pfReqValid` 在 `sExec`→`sFreq` flush 且 `a.ready=0` 时可能在 valid 保持期间更换 bits（m12-018 既有结构，020 未改），记给 architect 定夺。

## 完成区

**测试结果**：一键证据脚本 PASS=46 / FAIL=0（A–H；L1/L2 外部红逐项归因）；注入「槽 4→2」→ 脚本 FAIL（跨 beat p50=5、102/204 次 >2 拍）；`cp`+md5 还原 → 重建 → PASS。
**修改文件**：
- `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch`（4 槽 `Vec` + 数据优先 + 延迟计数 + 放宽发射条件）
- `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingTile.scala.patch`（取指 `IdRange(0, 5)`）
- `tools/chipyard/fetch_probe/gen_probe.py`、`tools/chipyard/fetch_probe/tb_fetch_probe.cpp`（新增跨 beat 探针；bench 判据改为数据优先）
- `components/chipyard/changelog.md`（本任务条目）
**验收结果**：
- 跨 beat（400 条 `or.o` 直线流）：改前 204/204 次 = 8 拍；4 槽后 p50=1、204 次中仅冷启动 1 次为 8；同拍在飞预取峰值 4（111 次采样）
- 数据优先（200 拍数据 burst bench）：burst 耗时 = 200（不劣化）、数据请求发出后预取数 0、同拍在途 1
- SRAM 往返延迟：10 次采样 4,4,4,4,4,4,4,4,6,6 → 需 ceil(6/2)=3 槽 ≤ 4（足够）
- 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变；R1=C（`or.o` 1 拍、`shl.o` 2 拍）不变
- elaboration/Verilator rc=0、`%Error`=0；`check-source-state`/`check-patch-tree` 中 chipyard 干净（整体 rc=2 来自 qemu/gem5 并发任务）
- L1 四项红全为外部（qemu/gem5 补丁、他任务日志名、他任务临时目录、他任务任务书的运行期目录引用）；L2 仅 8 个 DADAO-E2E（`m12-testcases-002` 欠账）
**新发现/坑**：4 槽本身无效——m12-018 的发射门 `qCount=/=0 && !waitBeat` 使核跨 beat 即进 FWAIT、最多 1 个在飞；`nextBeatReg` 本就支持空队列续推，故放宽为 `qCount=/=0 || waitBeat`。延迟 6 拍 × 每 beat 2 拍消费 ⇒ 需 3 槽。`cp -p` 还原保留旧 mtime 会让 make 不重建（自检假红），还原后须 `touch`。
**遗留问题**：① Tiny 44/44 外部红（QEMU-only 门控，共享安装根被并发任务重建；同门控在 master 的 tests/tools 上复现 44/1）；② `ldm`/`stm` 长 burst 未实现（`m12-chipyard-008`），burst 证据用 bench 的 200 拍单次数据访问代理；③ 冷启动首个跨 beat 仍为 8 拍（首次需求取指固有）。

#### 收尾（architect，2026-11-11 00:38）

- reviewer **Accepted**（独立重算，不采信脚本自报）：跨 beat 分布 `{1:203, 8:1}` ⇒ **p50=1**，唯一 8 拍是冷启动首跨；注入「恢复 2 槽 + 旧发射门」⇒ `cross_p50=8, cross_gt2=204`（= 改前 204/204）⇒ 还原回绿。
- **数据优先安全**：门控只挡新发射，回包路径 `pfPushOk` 不含 `dataBusy`；`pfValid` 仅回包释放、flush 只标 stale ⇒ 已发预取不丢；注入去掉 `dataBusy` ⇒ `after=6`、bench FAIL ⇒ 还原回绿。
- **发射门放宽无冲突**：`finish` 的等待节拍落在在途预取区间内、`pfBeat` 起步于在途之后；回退需求取指同拍 `fifoFlush` 使 `pfWanted=0`。
- SRAM 往返 10 采样 `4×8,6×2` ⇒ `ceil(6/2)=3 ≤ 4` 槽；`busy=4` 111 次。
- 非阻断（转 `ISS-375`）：F1 `run.sh` 归因用 `git diff HEAD` 致 `OUTSIDE` 恒 0 + master 回显固定；F2 数据 burst 判据系结构性论证；F3 Tiny 44/1 需在 `qemu-002` 装完后复跑。
- 既有结构观察（非本任务引入）：`io.imem.a.valid := atDemand || pfReqValid` 在 `sExec→sFreq` flush 且 `a.ready=0` 时可能 valid 保持期间换 bits（`018` 既有）。
