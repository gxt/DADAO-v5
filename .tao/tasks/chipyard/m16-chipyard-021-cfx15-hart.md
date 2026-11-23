# m16-chipyard-021: RTL cfx15 hart（cg8 管理 + cg9 异步现场 + timer 中断）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-020` 合入（同步路由已就位）；`ADR-0060`（hart-first，Accepted）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待验收

## 背景

`ADR-0060` 取代 `ADR-0059`：异步投递统一 **hart-first**——TIMER（`1<<17`）与 PMEM_DMA（`1<<18`）都投 **`cfx_hart`（cfxha 15）** 的 supv 单向量，现场/mask/pending 全在新增 **`cfx_hart cg9`**。本任务补 RTL 的 `cfx_hart`：cg8 原有管理寄存器 + 新增 cg9。

## 要做

1. **cg8（原 hart 管理）**：`hart_id`/`cycle`/`insn`/`timer_cmp`/`timer_ctrl`（`DADAO-12 §4.7`）；`cycle`/`insn` 按时钟计数；`hart_id` 单 hart 为 0。
2. **新增 cg9（16 rc，ADR-0060 D2）**：`async_prev_run_mode`(2b)、`async_prev_cfx_code`(6b)、`async_cause_ip`(48b)、`async_cause_id`(64b，非 0=有效帧)、`async_saved_global_intr_mask`、`async_pending`(位=**cause id** `1<<17`/`1<<18`)、`async_excp_vector`(48b)、`async_switch_run_mode`(2b，固定 supv=2)、`async_global_intr_mask`/`async_user_intr_mask`/`async_jail_intr_mask`/`async_supv_intr_mask`/`async_hypv_intr_mask`(位索引=**源 cfxha** 15/32)；rc13–15 reserved。
3. **TIMER 投递（hart-first）**：`timer_cmp` 到期 ⇒ `async_cause_id=1<<17`；投 `cfx_hart` 的 **supv 单向量**（`cg9 rc6`/`rc7=2`），写 `cg9 rc0–rc4`；mask 查 `cg9 rc8–rc12`（位=15）；pending 置 `cg9 rc5`（位=`1<<17`）。
4. **无嵌套/释放/重建**：`async_cause_id != 0` 时新事件只置 pending；软件写 0 释放帧、清 pending；可快照/重建。
5. **escape frame selector（bit1）**：`imms18=2` 选 `cg9` 偏移 0；`imms18=3` ⇒ `ILLI`；`imms18[17:2]` SBZ；`cfxha` = 当前 cfx。
6. **探针**：cg8/cg9 寄存器读写；timer 到期投 cfx_hart/supv、cg9 现场/pending/mask；`escape imms18=2` 返回；`3` ⇒ `ILLI`。
7. **H/S/U 三模式**：timer 在 hmon/smon/umon 下都投 `cfx_hart` supv（目标固定，不随当前模式变）；权限不允许的模式显式标注。
8. **三方用例（B）**：case 定义/期望只写一份；RTL 探针与 QEMU/gem5 复用同一 case；由 `check-arch-vast` 按需跑。
9. **不回归**：Tiny 无 cfx15；cfx3/4/5 既有语义不变。

## 不做

- 不做 cfx32/34（另两件）；
- 不改 cfx0/2 的同步路由（020）；
- 不做 monitor-first（ADR-0059 作废）；
- 不加多核/IPI。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. cg8/cg9 寄存器读写/保留；`cg9 rc13–15` ⇒ `CFXREG`；
2. timer 到期：`async_cause_id=1<<17`、投 cfx_hart supv、`cg9` 现场逐项、pending 位 `1<<17`、mask 位 15；
3. `escape imms18=2` 返回；`3` ⇒ `ILLI`；`imms18[17:2]≠0` ⇒ `ILLI`；
4. H/S/U 三模式下投递目标均为 cfx_hart/supv；
5. **可达 FAIL**：注入「timer 投 monitor」/「pending 记 cfxha 位」⇒ 红；`cp`+md5 还原并强制重建后回绿；
6. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` 的 A 段 9/9、C/D/E 段 26/26（合计 **35/35，rc=0**）；`run.sh --inject` **19/19，rc=0**。三模式（同一份 `cfx15.S`，链接期 `TMODE=3/2/0`）：H **58 槽**、U/S 各 **14 槽**逐槽等于现场从 `spec/DADAO-12` §1/§3.6/§4.7、`ADR-0060` D2/D4、`contract-see` §3/§6.1 与 `contracts/opcodes.yaml` 派生的期望；三模式 timer 投递均落 **cfx_hart+supv**（escape trace `mode=2 cfx=15`）。额外回归：`cfx5_regs` 22/22、`cfx02_regs` 47/47 在新 Vast 上通过。
**修改文件**：组件源 4（`generators/dadao-gewu/.../GewuFile.scala`、`generators/dadao-wuming/.../common/{WumingCore,WumingDecoder,WumingParams}.scala`；提交 base+1 `f01da22`，重导 4 份补丁，`series` 仍 26 条）；`components/chipyard/{README.md,changelog.md}`；新增 `tests/arch/hart/{cfx15.S,cfx15.lds,check_cfx15.py,README.md}`；`tests/arch/{README.md,expected-divergences.yaml}`；本任务书；运行期证据脚本（运行期证据目录内的 `run.sh`）。未改 spec/contracts/QEMU/gem5。
**验收结果**：① cg8：hart_id=0、cycle/insn 递增、timer_cmp RW、timer_ctrl 只写 `[1:0]`（bit2 ISTATUS 只读）；cg8 rc1/6/7、cg9 rc13/14/15、写 RO、读保留均 `CFXREG`，写 RO 的 `cause_info` = 指令编码。② timer：屏蔽期 pending=**`1<<17`**（非 cfxha 位 15）且 cause_id=0；放开后投 cfx_hart+supv，cg9 rc0–rc4 逐项、pending=`1<<17`、mask 位 15、无嵌套（帧活动期第二次事件只置 pending、cause_id 不变）。③ `escape imms18=2` 返回并释放帧、恢复 global mask；`imms18=3` 与 `imms18[17:2]≠0` ⇒ `ILLI`。④ H/S/U 三模式投递目标一致。⑤ 注入①「timer 投当前 monitor」②「pending/cause 记 cfxha 位 15」⇒ 探针均红；`cp`+md5 还原（基线 `3d2de4b7…` 前后一致）并强制重建后三模式回绿（重建 323/322/320/312 s）。⑥ 构建：Vast elab+sim rc=0、`%Error`=0，全量重建 312–323 s；Tiny elab+sim rc=0、`%Error`=0，约 100 s；环境 JDK `20.0.2-internal`、conda gcc `13.2.0`、Verilator `5.020`、`RISCV` 指向组件 `.conda-env/riscv-tools`；Vast sim md5 `4b880f25…`、Tiny `f8f6e4b6…`（只作记录，ISS-453）。⑦ 门控：`apply_series`/`check-source-state` chipyard clean+base+1（`HEAD=f01da22`）、`check-patch-tree` chipyard 段 **0 problem**（26 patches；全局 16 条全在 gem5/linux/musl 既有 KNOWN-RED）、`make_patch` 幂等（0 written）、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue` 均 rc=0。⑧ Tiny：`11-cfx` 5/5、`01-load-store` 38/38 与 020 的 pre-021 基线逐镜像字节相同。
**新发现/坑**：① 寄存器面测试会覆盖 cg9 rc6 向量与五个 mask；timer 测试前不恢复会跳到 `0xFFFF_FFFF_FFFC`（实测 UNDI→CFXMEM 循环，无输出）。② 异步 handler 复用等待循环的 `rd7/rb5` 会清零计数器，escape 后循环永不退出（实测）；handler 改用 `rd21/rb3`。③ Tiny 无 cfx_hart，若按 ADR-0060 全局放开 `escape` frame selector，`11-cfx/escape_ciii_cfx` 的 `imms18=2` 会从 `ILLI` 变 `CFXESC`（结构性红）；本任务按「Tiny 无 cfx15 不回归」把 selector 限定在有 cfx_hart 的机器（`WumingDecoder(withHart)`），登记 `DIV-11`。④ 当前工具链汇编器仍只接受 `imms18[17:1]=0`，`escape ..., 2` 用 `.dd.t32` 原始编码（待 `m16-llvm-001`）。⑤ 020 的 changelog 有两个 `## M16` 节导致 `check-component-changelog` 红；本任务合并为一个 M16 节。⑥ 任务 worktree 不带 `.dadao`/`.work/source`，证据脚本运行时链接到主 worktree。
**遗留问题**：① `DIV-10`：`tests/arch/umon/mode_entry.S` 的异步段仍是 monitor-first（020），已被 `tests/arch/hart/cfx15.S` 承接，待用例迁移任务更新（不影响本任务的同步段）。② `DIV-11`：Tiny 的 `escape` frame selector 编码集未随 ADR 变更，待 spec/工具链同步 + `11-cfx` 期望更新。③ 语义口径（交 `m18-spec-002` 承接）：(a) `async_switch_run_mode`（cg9 rc7）为**写接受并忽略、读回恒 2**，与 ADR-0060 D1「固定 supv=2」一致，须在 spec 明写「写忽略」；(b) `escape` 合法返回**即释放** `async_cause_id`——D4 以 `cause_id != 0` 判帧有效，不自动释放会让帧永久活动、后续 TIMER 永久堵死；与 D3「软件写 0 释放」（丢弃语义）不冲突，须在 D3/D4 补「返回即释放」一句。④ PMEM_DMA 源归 `m16-chipyard-022`；hypv 不强制两轴判权（`DIV-07`）不变。⑤ 三方（B）：`cfx15.S`/期望只写一份、checker 从合约派生，已可由 `check-arch-vast` 复用；QEMU/gem5 的 hart-first 后端不在本任务（`ADR-0060` D8 的 QEMU 先行任务），`DIV-06` 维持到 022/023 与后端接入。

**返工处置（第 2 轮）**：① 阻断项 ✅已修——完成区「修改文件」行改为「运行期证据脚本（运行期证据目录内的 `run.sh`）」，`make check-knowledge-refs` **rc=0（0 具体 `.work/**` 引用）**；② F1 ✅已修——`components/chipyard/README.md` 与 `changelog.md` 的槽数均改为 **H 58 槽 / U/S 14 槽**（全仓检索无其它槽数笔误）；③ F2 ✅已修——`run.sh` D 段标签改为 `sim rc`，重跑 D 段 **12/12、0 failure**（H 58 槽、U/S 各 14 槽）；④ 两条语义口径已按 reviewer 结论落「遗留」③，交 `m18-spec-002` 承接。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile` 的 `GewuHartParams`/`HartRegs`/`hartRows`/读数据 mux/写块/pending/投递/escape 分支、`commonRows` 对 cfx_hart 的 `cg8 rc1` 关闭、`WumingParams` 的 Vast-only 接入、`WumingDecoder(withHart)` 的 selector 门控、`WumingCore` 的 `retirePulse`/`escape.frame`/`hart` 输入；探针的 58/14 槽、等待循环与 handler 寄存器隔离、checker 的现场派生与 self-test。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 寄存器面测试覆盖 cg9 rc6/五 mask，timer 投递跳 `-4`（实测 UNDI 循环） | ✅已修 | 测试后恢复 `async_entry` 与五个 mask | H 58 槽全绿 |
| F2 handler 复用等待循环 `rd7/rb1` ⇒ escape 后死循环 | ✅已修 | handler 改用 `rd21/rb3` | 三模式均退出并全绿 |
| F3 Tiny 的 escape 编码集随 ADR 改变 ⇒ `11-cfx/escape_ciii_cfx` 红 | ✅已修 | `WumingDecoder(withHart)`：无 cfx15 用旧 SBZ 规则；登记 DIV-11 | Tiny 5/5 + 38/38 与 020 基线逐字节相同 |
| F4 `escape ..., 2` 汇编器拒绝 | ✅已修（绕行） | 探针用 `.dd.t32` 原始编码；checker 从 opcodes.yaml 派生 | 三模式汇编/校验绿 |
| F5 cg9 rc14/15 未覆盖（任务要求 rc13–15） | ✅已修 | H 增加两组 `CFXREG` 记录（58 槽） | 期望/实测 58 槽全绿 |
| F6 020 的 changelog 两个 M16 节使门控红 | ✅已修 | 合并为一个 M16 节 | `check-component-changelog` rc=0 |
| F7 `async_switch_run_mode` 写忽略 vs ADR 表 RW；escape 释放帧 | ⏸延后（语义待裁） | 写忽略/读 2；escape 清 cause_id | 记入「遗留问题」③，交 spec 同步确认 |

判决：F1–F6 已修并复验；F7 为口径性问题，已显式登记。状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（仓库根执行运行期证据目录内的 `run.sh`；我以 `ONLY=A,C,D,E` 作位置参数传入，脚本按其参数解析跑全段 A–F，故含 B 段重建与 F 段注入）：
- **A 9/9**（apply_series base+1 matches、source-state clean、patch-tree chipyard 0 problem、make_patch 0 written、index-blobs/tests-index/tasks rc=0）；**B 6/6**（Vast 305 s、Tiny 102 s，elab+verilator rc=0、`%Error`=0，sim md5 `4b880f25…`/`f8f6e4b6…`）；**C 6/6**（三模式汇编+checker --self-test，逐槽 mutation 可达 FAIL）；**D 12/12**（H **58 槽**、S/U 各 **14 槽**，0 failure；三模式 escape trace `mode=2 cfx=15` 各 1 次）；**E 8/8**（11-cfx 5 镜像、01-load-store 38 镜像，差异 0 字节，批次前后 Tiny sim md5 相同）⇒ **summary PASS=60 FAIL=0，exit=0**。
- **F 注入 19/19，rc=0**：inject1（投当前 monitor）源 md5 变更 ⇒ 红（m0/m2 签名流缺失；m3 槽 55–57 expected `0xC0DE0021/0/mask` actual `0x8/0x7E3C0002/0xDEADBEEF`）；inject2（pending/cause 记 cfxha 位）⇒ 红（m0/m2 槽 00/06/08/09/10 expected `0x20000` actual `0x8000`）；两路 `cp`+md5 还原均回 `3d2de4b7…`、还原重建后三模式 0 failure、final md5 一致。
- **独立补跑**：`cfx5_regs` 22/22、`cfx02_regs` 47/47（新 Vast，checker rc=0）；`check-component-changelog` rc=0、`check-no-residue` rc=0、`check-tasks` rc=0。
- **`make check-knowledge-refs` rc=2 FAIL**（ISS-352）：唯一违规项指向**完成区「修改文件」行**写了运行期证据脚本的具体 `.work/**` 路径；基线（HEAD 完成区为「待填」）无此引用 ⇒ 本任务引入。

**核验**：cg8（`hart_id=0`、`cycle`/`insn` 递增、`timer_cmp` RW、`timer_ctrl` 只写 `[1:0]`、rc1/6/7 与写 RO ⇒ `CFXREG`）与 cg9 16 rc（rc0–4 现场、rc5 pending=`1<<17`、rc6 vector 4B 对齐、rc7 恒读 2、rc8–12 mask 位=源 cfxha 15、rc13–15 ⇒ `CFXREG`）逐行对照 `GewuFile`、`spec/DADAO-12 §4.7`、`ADR-0060 D2`，D 段槽值现场一致（pending/cause=131072=`1<<17`、saved mask=`…7FFF`）。TIMER：屏蔽期只置 pending、`intr.valid` 被活动帧关断（无嵌套）、ack 写 rc0–rc4 + `runMode:=2`/`curCfx:=15` + global 置全 1；escape `imms18=2` 返回/释放/恢复 mask，`3` 与 `[17:2]≠0` 由 decoder ⇒ `ILLI`（静态+动态双证）。
**待裁判定**：① `async_switch_run_mode` ADR D2 标 RW、D1 定「固定 supv=2」——写接受忽略+读回 2 同时满足两条款（若写入生效反而违反 D1）⇒ **可接受**，须由 `m18-spec-002` 明写「写忽略」；② escape 合法返回自动释放 `async_cause_id`：D4 以 `cause_id!=0` 为帧有效判据，软件「写 0」在返回前做会让 escape 变 `CFXESC`、返回后做需两轴权限且时机不可控 ⇒ 自动释放是唯一自洽读法、与「写 0 释放」（丢弃语义）不冲突 ⇒ **可接受**，须由 `m18-spec-002` 在 D3/D4 补「返回即释放」。DIV-10（`mode_entry.S` 异步段仍 monitor-first，已由 `cfx15.S` 承接）与 DIV-11（Tiny 保留旧 SBZ 编码集，`11-cfx` case13/14 仍断言 ILLI）核对属实；`escape ..., 2` 汇编缺口已有 `m18-llvm-001` 承接，`.dd.t32` 绕行可接受。
**约束核验**：独立 worktree ✓；**未提交 git**（HEAD 仍 `8360ada4` 派单）✓；验收前后 `git status` 快照逐行一致、共享源树被注入文件还原 md5 相等 ✓；注入只用 `cp`+md5、未用 checkout/restore/stash ✓；术语「寄存器组」✓；证据脚本含环境块（JDK/gcc/Verilator 缺失即 ENV BLOCKED rc=4）✓。
**finding（非阻断）**：F1 `components/chipyard/README.md` 新节写「H 52 槽」，实测/期望 58 槽（数字笔误，请 architect 收尾改）；F2 `run.sh` D 段标签「guest rc」实测为仿真器退出码（guest 行为由签名流长度与槽值强制，标签措辞问题）。
**判决：Needs Revision** —— 指名失败项：`make check-knowledge-refs` **rc=2**（ISS-352：完成区「修改文件」行的具体运行期证据脚本路径），违反任务硬约束「不写运行期路径」与 AGENTS「具体 `.work/**` 引用一律 FAIL」，且该门控为收尾必绿项。修改建议：该行改为「运行期证据脚本（运行期证据目录内的 `run.sh`）」，预期重跑 `make check-knowledge-refs` rc=0。其余验收项（A–F 60/60、cfx5/cfx02 回归、changelog/no-residue）在我自己的重跑下全绿，返工面仅此一行。

### 第 2 轮 reviewer 验收

**阻断项闭环（我自己复跑）**：`make check-knowledge-refs` **rc=0**，输出 `具体路径 (不可复现): 0`、`悬空: 0`、`结果: PASS`；`check-tasks` rc=0、`check-tests-index` rc=0、`check-component-changelog` rc=0。第 1 轮指名的完成区「修改文件」行已改为「运行期证据脚本（运行期证据目录内的 `run.sh`）」，任务书内已无具体运行期路径（仅存 `.work/**` 通配引述与 `.work/source` 豁免形）。
**D 段我自己重跑**（`ONLY=D` 运行期证据目录内的 `run.sh`）：**summary PASS=12 FAIL=0，exit=0**；标签已为 `sim rc`；H **58 槽**、S/U 各 **14 槽**；三份 checker 日志 `58/14/14 slot(s), 0 failure(s)`；escape trace `mode=2 cfx=15` 各 1 次。
**F1 核验**：`components/chipyard/README.md` 与 `changelog.md` 均已写「H 58 槽 / U/S 14 槽」；全仓检索「52 槽」仅剩本任务书第 1 轮 finding 的引述与无关的 IDL 条目，实现文档无残留。
**遗留③核验**：(a) rc7「写接受并忽略、读回恒 2，与 D1『固定 supv=2』一致，**须在 spec 明写**」、(b)「escape 返回**即释放** cause_id，与 D3 软件写 0（丢弃语义）不冲突，**须在 D3/D4 补一句**」——与我第 1 轮结论一致，均为待 `m18-spec-002` 同步的口径，**未暗示 spec 已改** ✓。
**未动实现**：4 份补丁 md5 与第 1 轮逐一相同（`50d6c5fc…`/`419b313e…`/`7e599e1e…`/`7e7d0686…`）；共享源树被测文件 md5 仍为基线 `3d2de4b7…`；`git status` 快照 13 条与返工前一致；HEAD 仍 `8360ada4`，**未提交 git** ✓。本轮改动仅文档与标签（证据脚本 md5 `d8aa6548…`→`43719fcb…`，断言表达式未变），故不重跑 A/B/C/E/F——第 1 轮 60/60 与两路注入证据继续有效。
**剩余 finding（非阻断）**：证据脚本里 `all_modes()` 为未被调用的死函数，其 `.out.rc` 读取在探针产物下恒得 0（文件不存在），且本轮标签改成 `sim rc` 后与所读量语义相反——建议随脚本清理删除该死函数；其余同第 1 轮 F1/F2 均已闭环。
**判决：Accepted** —— 第 1 轮阻断项（`check-knowledge-refs` rc=2）复跑 rc=0 闭环，F1/F2 已修并由我独立复跑验证（D 12/12、槽数 58/14/14、0 failure），遗留③表述准确，实现与补丁零改动。
