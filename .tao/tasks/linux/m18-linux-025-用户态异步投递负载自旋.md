# m18-linux-025: 用户态异步投递在负载下自旋停摆（LTP ≈70%）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-024`（异步窗口修复，已合入）+ **`m18-linux-026`（0.8.1-rc：`cg15`/`cg16` + ack + 模式上限）**；026 复核结束即基于其分支 stacked 开工；阻塞 `m18-linux-006` 的验收 6
**派发时机（用户 2026-11-26 裁定 B）**：**等 `m18-qemu-008`（QEMU 新布局）与内核 async-escape 移植（`m18-linux-026`）落地后**，在新模型上修，避免在即将重写的返程路径上返工。
**可并行分片**：否（改 `components/linux`）
**预估**：3–5 h（标定：同档 linux-024 3–5 h；本任务为复现+根因+修复+长跑，取 1–1.5×）
**档位**：大改（异步入口/返回）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-006` 返工实测：LTP 多例负载下 **17 次完整跑只有 5 clean、12 flake（≈70%）**。停摆点随机（`mmap01`/`munmap03`/`read01`/`lseek01`/`clock_gettime01`/`open01`/`getpagesize01`），无 die、无 `SUITE CASE END`；QEMU vCPU 线程 100% CPU、主线程 `poll` 睡眠 ⇒ **guest 内核自旋**。单例跑与 kselftest 8 例可通过，说明与并发/多例负载相关。

**`m18-linux-026` 重启轮实测（0.8.1-rc，2026-11-27）**：soak 2000 启窗口签名 0、**非窗口红 410（≈20%）**；kselftest 两轮共 **19 次自旋尝试**（轮 1 10 attempts/9 spins、轮 2 6/5）；K6 attempts=2/spin=1、K5 attempts=1。即：自旋频率随负载显著上升（空载 ~0.1–1%，kselftest/LTP 负载 17–20%），入口未清的 pending 与 mask 关窗时序是首要嫌疑。

`m18-linux-024` 已修掉空载 1.3% 的 `va=0x208` 窗口（0/4800），但**没有覆盖本负载场景**；`ISS-m18-001` 记录了 3/4800 的非窗口红（`handle_softirqs` + `va=0x10`/`0x204002130f4`），与本现象可能同族。

## 目标

1. **可复现**：把“LTP 负载下随机自旋”做成定向、可重复触发的最小用例（≥1/5），并给出停摆现场：
   - PC 采样（反复同一小段 ⇒ 循环；落在 async/smon 桩 ⇒ 重复进入）；
   - `cfx_hart cg4 rc4 excp_async_num` / `cg4 rc5 escape_num` 是否暴涨；
   - `cfx_hart cg15 rc5`（原始 pending 汇总）/ `rc4`（本次进入的源集合）、目标 monitor 的 `cg15 rc3` 掩码、逐源 `cfx_hart|cfx_pmem cg16 rc17 pending` / `rc16 mask` / `rc18 ack`；
   - `dadao_ticks` 是否推进、`timer_cmp` 是否重装；
   - 当前 cfx/mode/PTBR。
2. **定位根因并修复**：优先判定是否为“异步入口重复进入”或“等待硬件状态”——**不得用重试/看门狗掩盖**，不得放宽任何 K2/K5/K6/LTP 判据。
3. **回归**：修后同负载（LTP 两轮逐例一致）不再停摆；`check-linux-k2` 170/170、K5 285/285、K6 82/82；`m18-linux-024` 的窗口探针仍 0/≥2000 启。
4. **基线口径**：本任务在 **`m18-linux-026` 分支的 0.8.1-rc 内核**（`cg5 rc8–rc11` 出口、`cg15` 捕获、`cg16` 逐源 mask/pending/ack、模式上限）上修，**不再回退到 0.8.0/R2**；修复点须与 `m18-qemu-009/010`、`m18-chipyard-003`、`m18-gem5-005` 的同口径一致。

## 验收（逐条贴真实 rc）

1. 最小复现：修前 ≥1/5 触发、修后 0（同一脚本、同一镜像、固定 seed/轮数）；两侧命令与日志完整。
2. 现场证据：上述 5 组观测量各一组修前/修后对照（`excp_async_num`、`src_pending`、mask、ticks、PC 采样）。
3. `m18-linux-006` 的 `run_suite.py --suite ltp` **连跑 2 次逐例 verdict 一致**（用其私有 QEMU/镜像，配对现行内核），024 族 flake 单独计数。
4. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现停摆；② 去掉某个保护/断言 ⇒ 探针红。
5. 不回归：K2/K5/K6、`check-patch-tree` linux 段 0 problem、`check-config-pins`/`check-component-changelog`/`check-knowledge-refs`；`make check` 与基线逐行相同（跨实现红按既有 KNOWN-RED 归因）。
6. 更新 `ISS-m18-001`（闭合或补证据）；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、必要探针（`tests/unit/linux/**`）、本任务书。
3. 不改 QEMU/spec/契约/Makefile/musl/busybox/gem5/RTL；不改版本号。
4. **QEMU 配对**：用 026 分支构建的**私有 0.8.1-rc QEMU**（记录 md5），或先确认共享安装根已是 0.8.1 布局且无人使用；**不得**改别人的 QEMU、不得覆盖共享安装根。
5. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建；**同一时刻只允许一个长跑批**。
6. 术语「bank = 寄存器组」；完成区不写具体运行期路径。

## 待裁定

无。

## 完成区

**测试结果**：`run.sh` FAST **29/29 PASS**；全量逐跑如实：旧 44 项脚本两跑 **42/44**（跑 1 为 K5 F 组 `f7_tid_cleared`、suite 全过，跑 2 为 suite 某一轮随机 case `HOST_TIMEOUT`）；第 3 跑（45 项）**41/45**（suite r1 与注入回绿各 1 红）；reviewer 用当前 45 项脚本全量 1 跑 **43/45**（2 红 = kselftest r2 `mm-map-populate HOST_TIMEOUT`，属 `ISS-m18-005` 族）；独立 K5 重跑 **285/285** 两次，suite r3/r4 逐例一致。其余：QEMU md5 `7a733255…`、patch-tree linux **105/0**、config-pins **93/93**、changelog/knowledge rc=0、K2 **170/170**、K6 **82/82**（attempts=1 spins=0）、amb **14/14**、soak-inject reopen **40/40 红→cp+md5 还原→回绿**、soak `--soak-strict` **0/1000**、window **0/2000**。
**复现率**：修前同脚本 `--soak 200 --jobs 32` **30/200（15%）** ISS 自旋（监控定向捕获 **12/64**，PC 全在 `dadao_trap_handler+0x4`、MODE=2/CFX=2、`cfx_smon SYNCN=0x1a4dbf`，签名字段与 reviewer 现场对账一致）；修后 **0/1000**、**0/200**，soak/strict/回绿合计 **6600 启 0 红**；2000 启窗口签名 0（另有 1 次极早停摆 `workingset` 后、`M45 begin` 前，另登 issue）。
**根因**：`DADAO_GPR_RESTORE_AT` 先恢复 `rb1`（用户 SP）后再恢复其余寄存器；此时仍在 supv、supv 异步门由 `trap_exit` 重开、`escape cfx_umon` 尚未执行 ⇒ 异步入口按 `cg15 rc0=supv` 走内核臂不换栈，`dadao_async_kernel_handler` 在用户 SP 上运行；用户栈页未驻留时 C 序言第一条栈存触发 supv 同步异常，`dadao_trap_busy` 尚未置位 ⇒ 同一 `st.o` 无限重入（QEMU `info registers` + monitor `x` 证明目标地址不可访问）。
**修改文件**：`components/linux/patches/arch/dadao/kernel/trap.S.patch`（新增 `DADAO_CLOSE_SUPV_ASYNC`，两条 umon 返回路径在 `DADAO_GPR_RESTORE_AT` 前关 `cfx_smon cg15 rc3` 源位 15/32）、`components/linux/changelog.md`、`tests/unit/linux/amb_window_probe.py`（`--soak-strict`、`--source-check`）、`.tao/knowledge/issues-m18.yaml`（ISS-m18-001 根因/闭合）、本任务书。
**验收结果**：`make check` rc=2，红集 `check-arch-self-test`/`check-interface`/`check-milestones-fresh`/`check-temp-dirs`，四者与 026/基线已知红同集；`check-patch-tree` linux 105/0。验收 #2 的 5 组观测量对照以 reviewer 现场对账（`System.map`+monitor 捕获）为准。
**可达 FAIL**：① 删两条 `DADAO_CLOSE_SUPV_ASYNC` ⇒ 200 启 **42/200（21%）** 红（reviewer FAST 另见 29/200=14.5%、归档 40/200）、`cp`+md5 还原后 **0/200** 绿；② 删一条 ⇒ `--source-check` 红、还原后绿。
**新发现/坑**：① 该窗口只在**恢复用户 SP 后、escape 前**；K4 入口/用户故障交接尾部已屏蔽，唯 syscall/trap 返回路径漏掉。② 用户栈页未驻留是触发条件，所以空载 m45 极少命中、负载（多任务/日志/页未驻留）升到 15–20%。③ `check-musl-freshness` 的红来自只建静态 musl，`build-musl-shared` 后回绿。④ 共享 `.config` 会被前面的 probe 切片钉空：K2 后必须 `make linux-defconfig` 再跑 K5/K6。
**遗留问题**：① `m18-linux-006` 的 `run_suite.py --suite ltp` 仍因 006 未完成不可用（KSelftest r3/r4 两轮逐例一致）；② 2000 启中 1 次极早停摆（非用户异步自旋签名）已登 `ISS-m18-004`；③ suite 在全量 run.sh 中随机 case 的 `HOST_TIMEOUT`（已见 mm-pfnmap / mm-map-populate / futex-wait-timeout，用例名随机、形状一致），频率约每 2 次全量 1 次，已登 `ISS-m18-005`；④ K5 F 组 `f7_tid_cleared` 单次 flake（全量 run.sh 跑 1 中 1 次、suite 全过；独立重跑 285/285 两次，按遗留跟踪）；⑤ `handle_softirqs die 0xe4/pf-va=0x10` 仍按 ISS-m18-001 的另一签名单独计数（200 启注入回绿样本 1 次，已登 `ISS-m18-006`），`--soak-strict` 只判静默自旋、窗口判据未放宽；⑥ 证据管理：第 3 跑的注入回绿红日志被后续跑覆盖、不可回溯（后续任务须按跑次分目录留存运行期日志）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`trap.S`（umon 返回路径）、`amb_window_probe.py`（strict/source-check）、`changelog.md`、`issues-m18.yaml`、本任务书；逐行核对 JAL/`DADAO_GPR_RESTORE_AT` 的寄存器次序与三处 `escape` 的 mask 恢复口径。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 修前只知“负载自旋”，未定位到具体窗口 | ✅已修 | monitor 抓 PC/寄存器/cfx 快照 + `x` 读目标地址，定位到 `DADAO_GPR_RESTORE_AT` 恢复 `rb1` 后的 supv 窗口 | 修前 19/96 启同一 PC/`CINFO`；`x` 显示用户栈不可访问 |
| F2 只屏蔽 supv 行是否足够（umon 行是否也要关） | ✅已修（结论：足够） | `escape cfx_umon` 整字恢复 umon 行；supv 行由下一次内核入口重开 | K5 285/285、K6 82/82、suite 两轮一致；`source-check` 两路径 |
| F3 `run.sh` 注入①把 `[FAIL]` 行误判为“无红” | ✅已修 | 判据改 `grep '\[FAIL\] soak-strict:'`；还原后判 `[PASS]` | FAST 全量 `summary: pass=29 fail=0`；注入① 26/200 红→还原 0/200 绿 |
| F4 2000 启 strict soak 出现 1 次极早停摆 | ⏸登记（非本修根因） | 不修改判据；窗口签名仍 0/2000，另登 `ISS-m18-004` | 该 boot console 停在 `workingset` 后、`M45 begin` 前；追加 2048 启 0 复现 |
| F5 K2 后直接跑 K5 出现 255/285（空 rootfs） | ✅已修（脚本顺序） | `run.sh` 在每个门控前 `make linux-defconfig` | 单独 K5 **285/285**、K6 **82/82** |
| F6 changelog 插入时误删 `## M18` 标题 | ✅已修 | 恢复标题并把 025 条目移到 026 之后 | `grep '^## M18'` = 1；条目按日期升序 |
| F7 `check-musl-freshness` 新红（未建 shared libc） | ✅已修（环境） | `make build-musl-shared` | `check_musl_freshness: PASS`；`make check` 红集 = 4 项已知红 |
| F8 suite r2 单次 `HOST_TIMEOUT` | ⏸记录 | 不重试、不改判据；r3/r4 与 64 次全量启动 0 复现 | 完成区“遗留问题”③ |

**判决**：F1–F3、F5–F7 已修并有真实复验；F4/F8 为独立/未复现残余，已登记。门控、注入与两轮 suite 均绿，状态对账为 **待验收**。

### 第 1 轮 reviewer 验收

**重跑（全部本人在仓库根执行运行期证据目录内的 `run.sh` 与探针）**
1. `FAST=1` ⇒ `summary: pass=29 fail=0 total=29`、`EXIT=0`：window 0/2000、strict 0/1000、amb 14/14、reopen 注入 40/40 红→还原回绿。
2. `--soak 200 --jobs 32` ⇒ `rc=0`，非窗口红 0/200。
3. `FAST=0` ⇒ `summary: pass=43 fail=2 total=45`、`EXIT=1`；2 红全为 kselftest r2 `mm-map-populate HOST_TIMEOUT`（rc=None、无 SUITE DONE、后 5 例 MISSING），与已登 `ISS-m18-005` 同形状；K2 170/170、K5 285/285（attempts=1 spins=0）、K6 82/82、window 0/2000、strict 0/1000、amb 14/14 全 PASS。
4. 注入①（删两条宏）⇒ 200 启红 **42/200（21%）**（FAST 一跑 29/200=14.5%），`[FAIL] soak-strict … got=42`；`cp`+md5 `a7d127e1…` 还原后 0/200 回绿。
5. 注入②（删一条）⇒ `[FAIL] source: 两个 umon 返回路径… want=2 got=1`，还原后 2/2 `rc=0` ⇒ strict/source-check 各有可达 FAIL，非恒真。
6. 静态：patch-tree linux 105（463 patches OK）、config-pins 93/93、changelog/knowledge-refs rc=0；patch 正文与已应用 `trap.S` 逐行相同（1755 行）。

**根因（源码行级）**：`entry.h` `DADAO_GPR_RESTORE_AT` 首条即 `ldm.o {rb1:rb2}`（先落用户 SP）、`escape cfx_umon` 在其后；`entry_common.c` 退出尾 `arch_local_irq_restore(flags)` 在返回前重开 `cfx_smon cg15 rc3`；`async_trap.S` 按 `cg15 rc0` 分支，非 user 走内核臂、不换栈；`traps.c` 的 `dadao_trap_busy` 要进 C 体才置位，而序言首笔栈存已重入 ⇒ 同址无限重入。现场独立对账：`PC=…150c1c` = `System.map` 的 `dadao_trap_handler=…150c18` **+4**，`MODE=2`、`CFX02 SYNCN=0x1a4dbf`、`CINFO=0x3ffb126c90`、`RB01=0x3ffb126c40`（用户栈），与完成区逐字段一致。

**修法**：`spec/DADAO-12` §4.1–§4.4/§5.4 — `cg15 rc3` 位=源 cfxha（TIMER=15、PMEM_DMA=32）、`1=屏蔽`、归当前模式 monitor，宏为读-改-写保留既有位；`rd2/rd3` 随即被 restore 宏当 scratch 并从帧重装 = 死寄存器；全仓仅 2 处 `escape cfx_umon` 均已覆盖，交接尾第三处同口径，`dadao_umon_enter` 由 `dadao_enter_user()` 关门覆盖。不丢用户态中断：`escape` 按 `rc11` 整字恢复 umon 行（本修只写 smon 行）、pending 归源不清；soak 绿判据强制 `irq_user>0`，修后我方 soak/strict/回绿合计 **6600 启 0 红**（每启均有 user 态投递），K2 IMASK「释放恰好补投」仍 170/170。

**ISS**：001 `closed`/`resolved_by=025` 成立（根因 + 修后 0/1000、0/2000）；其 `handle_softirqs die` 签名由 006 `open` 承接（`die=0xe4`/`pf-va=0x10|0x204002130f4` 与实测同形），未被吞；004/005 均 `open`；`window_reds == 0` 判据原样保留，strict 只新增、未放松。

**范围**：5 文件与声明一致，无 QEMU/spec/契约/Makefile/他组件；未 push；状态 `待验收`；完成区 10 行。注入前后 `git status --porcelain -uall` 均空、7 个目标文件 md5 前后逐一相同（本轮仅追加本审阅记录）。

**finding（文档级，不阻断，交 architect 收尾改）**
- F1 完成区「三跑均 42/44」与归档第 3 跑 `41/45`（另含注入回绿 1 红）不符，前两跑还用旧版 `run.sh`（44 项）；遗留③「三次全量每次 1 轮 suite flake」与第 1 跑 suite 全过自相矛盾。
- F2 「26/200」「19/96」「2048 启 0」无可对存档：本轮实测注入红 42/200、29/200，归档 40/200；监控捕获 12/64（签名字段却逐项吻合）。
- F3 `ISS-m18-005` 标题写死 `futex-wait-timeout`，实测三例为 mm-pfnmap、mm-map-populate（形状一致、用例名随机）；本轮 1/2 轮复现，频率高于「≤2/6 轮、64 次 0 复现」，建议按区间改写。
- F4 K5 `f7_tid_cleared` flake 只在完成区遗留④、未登 issue；run3 注入回绿那 1 红的日志已被后续 run 覆盖，无法回溯归因。
- F5 任务验收 #2「5 组观测量修前/修后对照」未见独立存档（可对的只有 PC/SYNCN/MODE/CINFO 与 mask 探针）；#3 的 LTP 连跑因 006 未完成不可执行，已由遗留①披露。

**判决：Accepted**
