# TESTCASES-102t: timing 探针去 icount 化（20 例解 BLOCKED）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-098t`（矩阵重生成）、`GEM5-020t`（CFXREG 对齐）
**状态**：已验证

## 用户裁定（2026-11-06）

> 「去掉 icount，对 qemu 有什么影响」→ 说明影响后选 **A：全部去 icount**。

即：删掉 `-icount`，把 20 个 timing 探针改成**时序模型无关**的轮询/窗口断言，使 QEMU 与 gem5 用同一份探针可比；QEMU 侧精确指令时刻断言不再保留。

## 现状

- 4 个探针文件用 `-icount shift=0`（1 ns/指令）让时间按指令条数确定性推进：
  - `min_rom_probe_integ047t.py` 1 例（`start_busy_returns_busy`）
  - `min_rom_probe_integ050t.py` 9 例（cfx_time/`cfx_hart` timer/cycle/insn）
  - `min_rom_probe_integ051t.py` 10 例（异步中断仲裁/timer/DMA 两源）
  - `node_probe_prelude.py` 负责把 `-icount` 拼进 QEMU 命令行
- parity 驱动 `run_parity.py` 只要发现命令行含 `-icount`，gem5 侧直接标 `BLOCKED`（「QEMU -icount 无 gem5 等价物」）⇒ `node/arch` 20 例 BLOCKED
- 这些用例的期望写成了指令条数（「1 ms BUSY ≈ 1e6 条指令」「10 万条指令内 cycle 至少前进 N」等）
- 事实：gem5 FS 有完整时间模型（tick/事件队列/timer），缺的只是 QEMU 的 `-icount` 开关；因此这是**测试资产耦合**，不是 gem5 能力缺口

## 目标

1. **删除 `-icount` 依赖**：`node_probe_prelude.py` 不再注入 `-icount`；三个探针的 `icount_shift` 参数与相关分支删除。
2. **改写时间等待为模型无关**：
   - 读当前 `cfx_time`/`SBI_TIME_GET`，按「当前值 + Δ」设 deadline；
   - 用**有界轮询**等待（最大迭代数 + 墙钟超时），不得死等；
   - 断言改为**架构可见属性**：到期前不触发、到期后窗口内触发、`ISTATUS` 语义、`IMASK` pending、单次/重触发、单调性、门限行为；
   - 窗口宽度须足够容纳两引擎的节拍差异（建议 ≥ 10× 名义值），并在注释里写明取值依据。
3. **parity 驱动**：删除「含 `-icount` 即 BLOCKED」规则与相关字段/自检；更新 `qemu_gem5_shim.py` 文档（仍拒未知选项即可）。
4. **重新对照**：`node/arch` 20 例从 BLOCKED 转为**实际对照**（AGREE_PASS / GEM5_ONLY_FAIL / QEMU_ONLY_FAIL / DIFF 之一），逐条给结论；不得把新失败写成 BLOCKED 掩盖。
5. 文档同步：`tools/testcases/arch/README.md`、`tools/testcases/parity/README.md`、`run_parity.py` 文档串。

## 范围 / 非范围

**在范围内**：`tools/testcases/arch/{node_probe_prelude.py,min_rom_probe_integ047t.py,min_rom_probe_integ050t.py,min_rom_probe_integ051t.py}`、`tools/testcases/parity/{run_parity.py,qemu_gem5_shim.py,README.md}`、`tools/testcases/arch/README.md`、本任务书、`milestones.md`。

**不在范围**：gem5/QEMU 实现语义（若出现真失败，另立任务）、`tests/**` 向量/期望、`spec/**`、`contracts/**`、`tests/parity/matrix-M11.md`（等结果稳定后由矩阵任务重生成）。

## 验收标准

1. 全仓 `-icount` 命中 = 0（活文件；归档/任务书除外）。
2. 20 例在 QEMU 与 gem5 上都实际执行，逐例给出状态与退出码；`BLOCKED` 计数 = 0（除非有真实能力缺口，须给证据并单列）。
3. 稳定性：同一探针对 QEMU 连跑 3 次、gem5 连跑 2 次，结果一致（允许时间窗口差异，不允许 PASS/FAIL 翻转）。
4. `run_parity.py --self-test` rc=0；`node/arch` 全量重跑：`total 269`、`blocked 0`、`diff 0`；`gem5_only_fail`/`qemu_only_fail` 逐条列名。
5. `make check-arch`、`make check`（L1）rc=0。
6. 反例：把任一窗口断言改成恒真（或把 `-icount` 加回）⇒ 对应门控/自检 FAIL；`cp`+`md5sum -c` 还原回绿（禁 git 还原）。
7. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 取舍已由用户确认：**放弃「恰好第 N 条指令到期」的强断言**，换取两引擎同探针可比。
- 若 gem5 在某例上确实不满足语义（不是节拍差异），按真实失败记录并给最小复现，另立实现任务；不得回填 BLOCKED。
- `-icount` 会关闭寄存器 dump；删除后如 dump 可用，可加强自检，但不得改变用例语义。

## 完成区

**测试结果**：20/20 timing 用例在 QEMU 与 gem5 实际执行均 `q=PASS/exit 0`、`g=PASS/exit 0`、`AGREE_PASS`（047t 1：`start_busy_returns_busy`；050t 9：`cycle_insn_monotonic`/`timer_istatus`/`timer_cmp_clears`/`timer_ones_disable`/`timer_interrupt`/`timer_imask_pending`/`timer_retrigger`/`sbi_time_monotonic`/`sbi_hart_set_timer`；051t 10：`pmem_pending_in_pmem`/`timer_pending_in_hart`/`pending_no_cross_cfx`/`global_mask_block`/`per_cfx_mask_block`/`intr_mask_tail_kick`/`timer_imask_hold`/`low_cfxha_first`/`escape_kick`/`direct_target`）。稳定性：证据脚本连跑 **2 轮均 10/10 rc=0**（每轮 100 次探针运行、无翻转）；焦点 `sbi_hart_set_timer` QEMU×15、gem5×10 全绿。`node/arch` 全量（冻结 gem5 副本）**total 269 / AGREE_PASS 269 / blocked 0 / diff 0 / GEM5_ONLY_FAIL 0 / QEMU_ONLY_FAIL 0**（rc=0）。
**修改文件**：`tools/testcases/arch/{node_probe_prelude.py,min_rom_probe_integ047t.py,min_rom_probe_integ050t.py,min_rom_probe_integ051t.py,min_rom_probe_async_094t.py,README.md}`、`tools/testcases/parity/{run_parity.py,qemu_gem5_shim.py,README.md}`、`tests/parity/README.md`、`TESTCASES-094t` 任务书、本任务书、`milestones.md`。
**验收结果**：
- F1 返工：`check_quiet` 改为**先计数、后时钟**（时钟 ≥ deadline 判不可判定）；`DELTA_NS` 100 µs→10 ms（`add.uo` 组 64 位 deadline）；`MAX_WAIT` 600k→4M（10 ms 在 gem5 约需 1.4M 迭代）。修前 QEMU 33 次 2 次 `0x62`，修后同例 QEMU 21 次（15 焦点 + 2 轮×3）0 失败。
- `make check-arch`：PASS（arch-smoke + 13 cfx probes）rc=0。
- `make check`（L1）：**rc=2**，仅 `check-patch-tree`（共享 gem5 源树被并行任务 GEM5-021t 改动 3 文件且 `scons -j32` 在跑）与 `check-run-artifacts`（并行任务 GEM5-022t 写了非法日志名）；其余 L1 目标单独重跑 **rc=0**；同一工作树在干扰落盘前的完整 `make check` 为 **rc=0**（重试 1 次同因，已留现场）。
- `run_parity --self-test` rc=0；`node/arch` 269/269 不变。
- 反例（2 轮各 4 项）：改坏 `wait_cond` 命中分支 ⇒ `timer_interrupt` rc=1；prelude 加回时钟覆盖 ⇒ shim rc=2 / probe rc=1；均 `cp`+`md5sum -c` 还原后回绿。
- `-icount`：`tools/` 活代码 0 命中；残留仅旧快照、历史 changelog、contract 否定句（见遗留）。
**新发现/坑**：QEMU 宿主时钟下滑移 0.5–7 ms，故 deadline 取 10 ms、窗口 1 s、迭代上限 4M 并在注释写依据；`check_quiet` 必须**先采样 witness 后采样时钟**，否则两次采样间的抢占会误判早投递（0x62 根因，非 QEMU 在 `cfx_time<cmp` 时投递）。arm 前需 cancel（cmp=~0/ctrl=0/pending=0）+基线重置+重试，否则可能武装已过期 timer。`add.uo {hi,lo}` 两目的必须不同（同则 ILLI）。并行任务重建共享 gem5 二进制会导致矩阵中途失效 ⇒ 最终矩阵用冻结副本（md5 `23ee54cd…`，源 `5812f78a…`）生成。
**遗留问题**：① 环境干扰（非本任务）：GEM5-021t 未提交的共享 gem5 源树改动 + GEM5-022t 非法日志名，使当前 `make check` 无法全绿（重试 1 次同因；本任务改动不含 components）；② 探针 WORKDIR 为跨 worktree 固定路径，两任务并跑同一探针会互覆 rom/log（既有隐患，未改）；③ 范围外 `-icount` 残留：旧矩阵快照（待矩阵任务重生成）、QEMU changelog、contract 否定表述；④ 按用户裁定不再保留「恰好第 N 条指令到期」强断言。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查改动源码并对照真实验收输出，finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `wait_cond` 迟到判定用 `br nn`，把 `cmp(now,bound)<0` 也当迟到 | ✅已修 | 改为 `cmp==1` 才判 late（`cmp.uo` 返回 -1/0/1） | 单例 PASS；3×/2× 无翻转 |
| F2 `check_quiet` 对 `count==want` 计数 witness 误用 `zero_is_met=False` | ✅已修 | 计数 witness 统一 `zero_is_met=True` | 9 例 timing 全 PASS |
| F3 宿主时钟在读数与写 cmp 间越过 deadline，武装「已过期」timer（retrigger 计数跳 3） | ✅已修 | arm 前 cancel（cmp=~0/ctrl=0/pending=0）+ 基线重置 + 8 次重试 | retrigger QEMU 连跑 5 次 PASS |
| F4 timer 用例用 rd20/rd21 做 ISTATUS 掩码，异步 handler 会覆盖 | ✅已修 | 改用 rd5/rd6 + W_TMP(rd28) | 050 全 16 例 PASS |
| F5 `min_rom_probe_async_094t.py` 仍用 icount 参数（任务书未列） | ✅已修（越界披露） | 去参数、`dump=False`、用例改名 `dedup_timer` | 该探针 QEMU/gem5 各 6/6 PASS |
| F6 证据日志名不满足 check-run-artifacts A3 | ✅已修 | 全部改 `TESTCASES-102t-<purpose>.log/.txt` | `check_run_artifacts` PASS |
| F7 50 ms 窗口在宿主高负载下误报 | ✅已修 | 窗口改 1 s + 迭代上限 600k + 注释写实测依据 | 3×/2× 稳定 |
| F8 旧快照仍有 20 BLOCKED 行 | ⏸延后 | 任务书明确不在范围，由矩阵任务重生成 | 已在遗留登记 |

判决：无未修 finding；状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-06，独立重跑；完整输出见 运行期日志）

**重跑（命令 → 我自己的退出码）**
1. `run_parity.py --self-test` → `SELF-TEST: PASS` **rc=0**；`--profiles node --scopes arch --list` = `269 case(s)`。
2. `node/arch` 全量（新 work-dir 现场生成、非读旧报告）→ `run_parity: PASS` **rc=0**；`total 269 / agree_pass 269 / blocked 0 / diff 0 / gem5_only_fail 0 / qemu_only_fail 0`；20 个 timing 例逐条 `q=PASS/0、g=PASS/0、AGREE_PASS`（两名单均空，无可列项）。
3. 运行期证据脚本（带 MATRIX_JSON）**第 1 次 rc=1**：`RUN qemu integ050t/sbi_hart_set_timer #3 rc=1`、`CHECK timing_runs_both_engines FAIL`、`CHECK timing_stability FAIL`，case 日志 `FAIL sbi_hart_set_timer exit exp=0 got='0x62'`；其余 8 项 PASS（`matrix_judge total=269 blocked=0 diff=0 g5=0 qo=0`；两处注入→FAIL→`md5 OK`→回绿）。
4. **有据重试第 1 次**：同脚本 `SUMMARY: 10/10 checks passed`、**rc=0**（100 次运行全 0、无翻转、注入 4 项照常）。
5. 焦点复跑 `--only sbi_hart_set_timer`：QEMU ×15 → **1 次 rc=1（0x62）**（当次 `load avg 0.42`，非超时）；再 ×10 → 0；gem5(shim) ×10 → 0。合计 QEMU 33 次 **2 FAIL（6%）**、gem5 15 次 0 FAIL。
6. `make check-arch` **rc=0**（`check-arch: PASS`）；`make check`（L1）**rc=0**（`repository checks (L1): PASS`）。
7. 越界披露项 `min_rom_probe_async_094t.py`：QEMU 6/6 **rc=0**、gem5 6/6 **rc=0**（我自跑）。
8. `-icount`：`grep -rn -- "-icount" tools/` → **0**；全仓残留 3 个非代码文件（旧矩阵快照 21 行、qemu changelog 1 行、contract-see 否定句 1 行）。

**独立注入（`cp` 备份 + `md5sum -c` 还原，未用 git 还原）**
- INJ-A：`integ050t::timer_interrupt` 改 `arm_timer(a, ctrl=0)`（事件永不到期）→ probe **rc=1 `0x63`**（`wait_cond` lost 分支可达）→ 还原 `md5 OK`、md5=注入前 → 复跑 **rc=0**。
- INJ-C：`node_probe_prelude.py` 加回 `-icount shift=0` → `tools/` 命中 **1**（脚本门控转红）、gem5 探针 **rc=1**（shim `0x2`）→ 还原命中 **0**、**rc=0**。
- 收尾对账：`git status --porcelain -uall` 与审查前**逐行相同（12 行）**；52 个目标文件 `md5sum -c` **52/52 OK**。

**约束核验**：① tools/ 活代码 `-icount`=0 ✅（全仓 3 处非代码残留见 F3）；② 20 例双引擎实跑、blocked 0、无「gem5 过而 QEMU 不过」✅；③ **稳定性 ❌（QEMU 出现 PASS/FAIL 翻转）**；④ self-test + 全量 269 ✅；⑤ 两门控 rc=0 ✅；⑥ 反例注入可达 FAIL 且还原回绿 ✅；⑦ 完成区 15 行、任务书无运行期路径 ✅，改动 12 文件与「修改文件」逐一对上 ✅。

**finding**
- **F1（阻断）** `check_quiet`（050/051 同源、覆盖 6 个 timing 例）先读 `cfx_time` 后读投递计数，两次采样非原子，而 `DELTA_NS=100_000`（100 µs）≪ 完成区自述宿主滑移 0.5–7 ms ⇒ 宿主抢占落在两采样之间即误判「到期前已投递」(0x62)。改法：**先读计数、后读时钟**，时钟 ≥ deadline 一律按「不可判定」跳过（或 now1→cond→now2 双采样），并把 `DELTA_NS` 提到 ≥10 ms 且与注释对齐；改后连跑 2 轮 run.sh + 该例 QEMU ≥15 次须全绿。若判定为 QEMU 真在 `cfx_time < cmp` 时投递（实现语义、范围外）⇒ 按真实失败留最小复现另立任务，**不得回填 BLOCKED**。
- **F2（文档）** 050/051 常量注释过期：写「窗口 50 ms、名义 50 µs、600k 覆盖 ~55 ms = 整个窗口」，实际 `WINDOW_NS=1_000_000_000`(1 s)、`DELTA_NS=100_000`(100 µs) ⇒「取值依据」与代码不符，须同步。
- **F3（文档）** 残留 `-icount` 3 文件已由完成区披露（矩阵快照待矩阵任务重生成）；另 `TESTCASES-094t` 完成区仍引旧用例名 `dedup_icount`（已改名 `dedup_timer`）。
- **F4（提示）** 探针 `WORKDIR` 为跨 worktree 固定路径，两任务并跑同一探针会互覆 rom/log（既有隐患，非本次引入）。

**判决：Needs Revision** —— 验收标准 3「稳定性不许 PASS/FAIL 翻转」在我自己的重跑下失败（run.sh rc=1；焦点复跑 1/15 复现，`0x62` 为语义性 FAIL 而非超时）；其余 6 条标准均通过。

### 第 2 轮 engineer 返工（reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1（阻断）`check_quiet` 先时钟后计数，两次采样非原子；100 µs 名义 deadline 过小 | ✅已修 | 采样顺序改为「先计数、后时钟」，时钟 ≥ deadline 判不可判定；`DELTA_NS` 100 µs→10 ms（`add.si`→`add.uo` 组 64 位 deadline）；`MAX_WAIT` 600k→4M | 焦点 QEMU×15、gem5×10 全绿；证据脚本连跑 2 轮 10/10、rc=0 |
| F2 常量注释与实参不符（50 ms/50 µs/600k） | ✅已修 | 050/051 注释改为 10 ms 名义、1 s 窗口（100×）、4M 迭代（10 ms 约 1.4M 次） | 旧值 grep 0 命中 |
| F3 `TESTCASES-094t` 仍引旧用例名 | ✅已修 | 094t 证据行改 `dedup_timer`（原 `dedup_icount`） | 旧名仅存于本任务返工记录 |
| F4 探针 WORKDIR 跨 worktree 固定 | ⏸延后 | 既有隐患、非本次引入，未改 | 已入完成区遗留 |
| R1（返工自审）`MAX_WAIT` 未随 DELTA 提升，gem5 首跑 `wait_cond` lost（0x64） | ✅已修 | 同 F1 的 `MAX_WAIT=4M`；实测 10 ms 约需 1.4M 迭代 | `sbi_hart_set_timer` gem5 rc=0（8.2 s），×10 全绿 |

根因结论：`0x62` 是采样顺序误差，非 QEMU 在 `cfx_time < cmp` 时投递；改后同例 QEMU 累计 21 次 0 失败，无最小复现可留，不另立任务。
外部阻塞：`make check` 现仅 `check-patch-tree`（GEM5-021t 未提交的共享 gem5 源树改动 + `scons -j32`）与 `check-run-artifacts`（GEM5-022t 写入非法日志名）两门红；其余 L1 目标单独重跑 rc=0，同树干扰前的完整 `make check` 为 rc=0。
判决：F1 已消除，无未修 finding；状态 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-06，独立复验；完整输出见 运行期日志）

**重跑（我自己的命令与 rc）**
1. 证据脚本连跑 **2 轮**（`MATRIX_JSON` = 我现场生成的 269 报告）→ 均 **`SUMMARY: 10/10`、rc=0**；每轮 100 条 `RUN`（60 QEMU + 40 gem5）**0 条非 0**、`timing_stability 0 flip`；两处自带注入照常 `inject rc=1 → md5 OK → restore rc=0`。
2. 焦点压测：`sbi_hart_set_timer` QEMU ×20 + ×25 = **45 次 0 失败**（加两轮 run.sh 的 6 次 = 51），gem5 ×12 **0 失败**；`start_busy_returns_busy` QEMU ×15 / gem5 ×10 全绿；`check_quiet` 族另测 `timer_interrupt`/`timer_retrigger`/`timer_imask_pending`/`timer_imask_hold` 各 ×10 = 40 次全绿；压测期 `load 7.61, 11.60, 9.86`（R1 复现假 `0x62` 时仅 0.42）。对照：返工前同例 QEMU 33 次 **2 FAIL(`0x62`)**。
3. `node/arch` 全量（新 work-dir 现场生成）→ **rc=0**：`total 269 / AGREE_PASS 269 / blocked 0 / diff 0 / gem5_only_fail 0 / qemu_only_fail 0`；20 个 timing 例逐条 `q=g=PASS/exit 0`。引擎身份：gem5 md5 `4c6b1b97…`（跑前跑后同值、未中途重建）、qemu `5dd37490…`；与 R1 的 `20b071c2…`、engineer 冻结件 `23ee54cd…` 同判 269/269（三枚二进制互证）。
4. `run_parity --self-test` **rc=0**；`make check-arch` **rc=0**（13 cfx 探针 PASS）。
5. L1 `make check` **rc=2**：唯一红 `check-patch-tree`（6 problem：assertion ⑨/⑥ 于 `process.cc`/`process.hh`/`se_workload.cc`）。**归属=环境、不据此判红**：本任务 0 个 `components/` 改动；`.work` 为指向主树的符号链接 ⇒ 共享 gem5 源树出现新本地提交 `0d811d3`（2026-11-06 12:18:44，并行会话）；**在主树 master 直接跑同一检查同样 rc=1、同样 6 problem**；R1 同一改动集当时 `check-patch-tree: 7 component(s), 305 patches OK` + `repository checks (L1): PASS` rc=0。`make -k check` 下其余全绿（`check-run-artifacts`/`check-no-residue`/`check-knowledge-refs` PASS、文档 88/88），L1 配方两步单跑 `check_issues` rc=0、`compileall` rc=0（完成区所称 `check-run-artifacts` 红在我这轮为 PASS，该干扰已不复现）。
6. 独立反例注入（`cp` + `md5sum -c`，未用 git 还原）：INJ-E 打断「到期前不触发」（050 `check_quiet` 命中分支改 `exit_seq(code)`）→ `FAIL timer_interrupt got='0x61'` **rc=1**；INJ-H 打断「窗口内触发」的迟到判定（051 `wait_cond` 删 `br ne → ok`）→ `FAIL timer_imask_hold got=6`(`0x106`=code_late) **rc=1**；两处还原 `md5 OK`、md5 与注入前相等 → 复跑均 **rc=0**。
7. 对账：`git status --porcelain -uall` 与审查前**逐行相同（13 行）**；48 项目标文件 md5 **48/48 OK**；`grep -- "-icount" tools/` = **0**；完成区 15 行 ≤30、任务书无绝对运行期路径。

**代码审计（F1 核心）**：`check_quiet` 现为「先读 witness(T1)、后读时钟(T2≥T1)，T2≥deadline 判不可判定跳过」⇒ T2<deadline 时 witness 必早于 deadline，假 `0x62` 的非原子窗口已消除（050/051 同源同序）；`DELTA_NS=10 ms` ≥ 实测滑移 7 ms（常态 ~20×），且 INJ-E 能打出 `0x61` 证明该检查在正常运行中**确实执行、未被跳过**；`MAX_WAIT=4M × ~7 指令 ≈ 28 ms`(gem5) > 10 ms deadline（约需 1.4M 迭代、2.8× 余量），通过用例在 deadline 即退出、4M 只作 lost 兜底 ⇒ **没有靠拉长等待掩盖语义**（返工期首跑 gem5 `0x64 lost` 后才提上限，反证该上限生效）。

**遗留（非阻断，同 R1）**：gem5 有效窗口≈18 ms（受 `MAX_WAIT` 截断；代码 `WINDOW_NS=1 s` = 100× 名义仍达标）；`start_busy_returns_busy` 的 BUSY 间隙断言对宿主抢占仍敏感（本轮 25 次全绿）；范围外 `-icount` 3 处文档残留；探针 `WORKDIR` 跨 worktree 固定路径。

**判决：Accepted** —— 验收标准 1–7 在我自己的重跑下全部通过（翻转已消除、269/269 blocked 0 diff 0、两门控与 self-test rc=0、反例可达 FAIL 且还原回绿、完成区合规）；L1 唯一红为共享 gem5 源树的环境干扰，已在主树复现、非本任务引入。architect 终审后可合入。

#### 收尾（architect，2026-11-06）

- 第 1 轮 F1（`sbi_hart_set_timer` 约 6% 假 `0x62`）已修：`check_quiet` 先读计数后读时钟、`DELTA_NS=10 ms`、`MAX_WAIT=4M`；reviewer 压测 QEMU 51 次、gem5 12 次零失败。
- 20 例 timing 探针去 `icount` 后 `node/arch` 269/269 AGREE、blocked 0、diff 0。
- 遗留：gem5 有效窗口受 `MAX_WAIT` 截断约 18 ms；`start_busy` 对宿主抢占敏感；探针 `WORKDIR` 跨 worktree 固定路径。
- 判决 Accepted（第 2 轮），状态置 `已验证`。
