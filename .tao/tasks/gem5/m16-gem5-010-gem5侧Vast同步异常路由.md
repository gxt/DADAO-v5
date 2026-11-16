# m16-gem5-010: gem5 侧 `Kaiwu-Vast` 同步异常路由对齐 `DADAO-12 §5.2`

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m14-qemu-006`（**已验证**：QEMU 侧同一改动的实现与 28 个 oracle 复推，可作行为对照）
**可并行分片**：否（改 `components/gem5` 单一组件树）
**预估**：3–5 h
**档位**：中改（删一条路由 + oracle 对齐；复核 ≥2 路注入 + 探针全量）
**状态**：待验收

## 背景

`DADAO-12 §5.2` 要求**执行过程中的同步异常一律先进对应运行模式的 monitor 向量**（MUST）。QEMU 侧的 `Kaiwu-Vast` 曾把 5 类同步异常做成 **staged 机器 fault**（不进向量），已由 `m14-qemu-006` 删除 staged 模型、两 profile 统一进 monitor。

`.tao/knowledge/discussing.md` 记有同一条未闭环（`spec-004` 候选）：「Vast 的同步异常仍是 staged 机器 fault（`DADAO-12 §5.2(一)` 要求进向量），5 个 arch 探针 oracle 依赖旧口径；**统一需同步改 qemu/gem5 + 探针**」—— QEMU 侧已完成，**gem5 侧无任务**。

## 执行前必须先复现（不得凭推断改）

用现成探针在 gem5 上跑 `Kaiwu-Vast`（`-M kaiwu-vast`）的同步异常例，确认当前行为落在哪一类：

- `tests/arch/**` 的 `049t`（`old_ram_unmapped` / `oob_fetch_cfxmem`）、`integ042t`、`integ048t`（`power_bootrom_store` / `closed_power_bootrom`）；
- 期望（改后）：两 profile 的 `sync_exc_monitor_entry = true`，异常进 monitor 向量、由向量决定去向；不存在第二条"机器 fault 直接退出"的路由（`Kaiwu §7.1` 的 `fault` 兜底**仅**用于「向量不可达」）。

现场结论写进完成区（**未复现成功不得开改**）。

## 目标

1. **单路由**：`Kaiwu-Vast` 的同步异常只走 monitor 向量；删除/禁用 staged 机器 fault 路径（与 `m14-qemu-006` 的裁决一致：**真删，不是 `if (0)`**）；
2. **保留唯一兜底**：仅当「向量不可达」时按 `Kaiwu §7.1` 走机器 fault（该路径有用例覆盖，不得一并删）；
3. **帧四项**对齐：`prev_run_mode`、`cause_id`（含子原因，若 `m16-gem5-009` 已落地）、`cause_ip`（触发指令地址；取指异常时 = 非法 IP）、`cause_info`（数据 `CFXMEM` = 访存地址；`ILLI` = 指令编码）；
4. **oracle 按 spec 复推**：受影响探针的期望值由 `DADAO-12 §5.2` 步骤逐字段推出，**不得**照实现输出改期望。

## 验收（真实 rc + 输出）

1. **与 QEMU 一致**：`m14-qemu-006` 覆盖的同一批探针在 gem5 上全部 PASS，且帧四项与 QEMU **逐字段相同**；
2. **反例可达**：注入「让某同步异常走 staged 路径」⇒ 该探针红（证明 staged 确实被移除而不是被绕过）；
3. **兜底仍在**：`integ040t/ptwerr_monitor_cfxmem_exit`（向量不可达 ⇒ `§7.1` 机器 fault）仍绿；
4. **≥2 路注入**（`cp`+md5 还原）：① 上面那路 staged；② `prev_run_mode` 改成读切换后的值 ⇒ `prevm` 断言红；
5. 门控：`check-gem5-decode`、`check-arch`（14 探针）、`check-patch-tree`（gem5 段 0 problem）、`make_patch` 幂等；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `components/gem5/**` + 必要的 `tools/gem5/**` + 本任务书；**不动** `spec/`、`contracts/`、`tests/**`、`components/{qemu,linux,chipyard}`；
- 不得为"让探针变绿"改期望值；**spec 是唯一真源**；
- 不提交 git；注入还原 `cp`+md5（禁 `git checkout/restore`）；基线钉死 commit（`ISS-458`）。

## 完成区

**测试结果**：一键证据脚本三组（默认 A/C/D/E + `--inject` 三路）—— A 代码证据 11/11、C 帧 2/2、D QEMU 1/1、E 门控 4/5（E5 见下，外部）；`--inject` 三组各 4/2/2 检查全 PASS（红→还原→回绿）。gem5 FS Vast 探针实测：`049t` 9/9、`integ040t` **34/34**（含 `§7.1` 兜底例）、`integ042t` **25/25**、`integ048t` 全绿；改前同一批为 6 / 1 / 3 / 1 例红。
**修改文件**：`components/gem5/patches/src/arch/dadao/{node_cfx.cc,node_cfx.hh,node_tlb.cc,fs_machine.cc,fs_machine.hh,inst.cc}.patch`、`components/gem5/changelog.md`、本任务书；证据脚本与日志在运行期证据目录（未归档）。
**验收结果**：
- **改前复现**（同一批探针、改前二进制）：`049t` 6 例 `exit exp=0x0 got=0xf1` 且 rd10–rd13 全 0（**无帧**）；`integ040t/tlb_bypass_ptw_off` 同形；`integ042t` 3 例同形；`integ048t/power_bootrom_store` `exit exp=0x2e got=0xe8`（supv+ILLI 的 staged 机器 fault 码）。⇒ 证据是 staged 直退，不是「进了 monitor 但帧错」。
- **单路由（真删）**：`MachineFault::invoke` 的 Node 分支改走 `nodeSyncEnter`（与既有 Tiny→hmon 分支对称）；`node_tlb` **6 处** `machineFault(...)` 直投改为携带帧的 `machineFaultAt(cause, faultPc, info)`；`NodePtwFault`/`NodePermFault` 同口；全树 `exitSimLoopNow` 仅剩 **1 处**（`machineFaultExit`，只在「向量不可达」时用）。无 `if(0)`/注释桩。
- **帧四项**（`§5.2` 步 5，逐字段、全部由 spec 复推）：数据 `CFXMEM` = `prev=3(hypv) / cid=0x2 / cip=触发 ld.o·st.o 地址（如 0xffffffff1020）/ cinfo=访存地址（0xffff00001000、0x1000000、0xffc000000000）`；取指 `CFXMEM` = `cip=cinfo=非法 IP（0x1000000 / 0xffc000000000，§5「IP 停留」）`；SRAM/保留 cfx = `cid=0x2 / cinfo=0x83ff00010000、0x800000000000、0x180000000000`；ILLI（BootROM 存储）= `prevm=2(supv) / cid=0x100 / cinfo=0x21504000（st.o 指令编码，由 `contracts/opcodes.yaml` 独立派生）/ cip=st.o 地址 / syncn=1`；`prev_run_mode` 取**切换前**快照（用户态 case 实测 `PREVM:0=0`）。
- **与 QEMU 一致**：同一批 11 例 + 兜底例 + 用户态 prevm 在 QEMU 与 gem5 上**逐字段相同**（同一张 spec 派生表判两侧，D1 全绿，无差异项）。
- **注入（`cp`+md5 还原 + 重建）**：①复活 staged 直退 ⇒ `049t/old_ram_unmapped got=0xf1`、`integ048t/power_bootrom_store got=0xe8` 双红，而 `§7.1` 兜底例**仍绿**；②`prev_run_mode` 改读切换后的值 ⇒ 用户态帧 `PREVM:0` 0→2；③`prev_run_mode` 写常量 ⇒ `prevm:2 exp=0x2 got=0x0` 红。三路均 `cp` 还原到基线 md5 并重建回绿。
- **门控真数**：`check-gem5-decode` rc=0；`check-patch-tree` **gem5 段 0 problem**（qemu 段 7 条为 `m14-qemu-003` 在途，逐条为 assertion ⑥/⑦/⑨ 的 helper.c 等）；`make_patch gem5` **幂等**（第二次 `0 written`、补丁目录 md5 不变）；`--source-state` gem5 `OK count=1 clean=True`；`check-arch` **E5 红**：2 次重跑 + 单例 3 次直跑均只有 `integ042t/pmem_dma_irq_delivered`（PMEM_DMA 异步中断）TIMEOUT，QEMU 侧（本改动不触 qemu），该例在 gem5 上绿。
- **回归**：15 个 arch 探针（含 `046t`）在 gem5 Vast 上全量复跑，仅 `integ007t` 1/64（semihosting console）与 `integ046t` 15/16（`cfx_smon VEC == smon e_entry`）红，改前逐例相同。
**新发现/坑**：① 探针超时只杀 python，`gem5.opt` 子进程会存活并继续写 `-D cpu` 全量 trace（本次一度把工作盘写满、连带 gate 锁写失败自锁）⇒ 证据脚本加 EXIT trap 按 `PARITY_WORK_ROOT` 清理孤儿；② 「向量不可达」必须在**投递前**判：先 `nodeCfxEnter` 再判会把 `runMode` 切走、`§7.1` 的 `bit5:4` 用错模式（QEMU `dadao_excp_to_exit_code` 读切换后 `inner_run_mode`，hypv/supv 例恰好相同，属其潜在隐患）；③ monitor 各行 `⟨mode⟩_switch_run_mode` 在 hypv/supv 下等于进入模式，故「prev 读切换后值」在既有断言里不可见，只能用户态帧验证；④ 本机 gem5 增量重建不是逐位可复现（每次链接后 md5 变），版本以交付时 md5 为准。
**遗留问题**：① `RASOF` 的 `cause_info`（`§4.1` = 准备压栈的返回地址）仍为 0，需 `exec/b5` 增加回传通道，无探针覆盖，未在本任务扩权；② Node 侧无 `IALIGN` 落点（取指未检 `IP[1:0]≠0`），改前既有、与本次路由无关；③ `integ007t`/`integ046t` 的既有红未处置；④ `check-arch` 的 QEMU 单例红须待 `m14-qemu-003` 收口后复跑。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`node_cfx.{cc,hh}`（`nodeVectorReachable`/`nodeSyncEnter`/`NodeState.curInstWord`）、`fs_machine.{cc,hh}`（`MachineFault::invoke` 的 Node 分支 + `machineFaultExit`）、`node_tlb.cc`（6 处 raise 点 + 两个 fault 类）、`inst.cc`（`curInstWord` 记录、semihosting-off/无 cfx 的 `cause_ip`/`cause_info`）；对照 `spec/DADAO-12 §2.2/§4.1/§5.2(一)(二)(三)/§5`、`spec/Kaiwu §1.1/§2/§4.4/§7.1`、`ADR-0045 D6`。

逐行结论：同步异常不可屏蔽（`nodeCfxEnter` 的 sync 分支不查掩码，未改动）；`nodeSyncEnter` 在**进入前**用 `mode[entryMode].excpVector` 判可达（无副作用），可达才调 `nodeCfxRaise`，故 `§5.2` 步 4–7 的计数/帧/切换语义与既有 `nodeCfxRaise` 完全一致；不可达分支按 `ctz(cause)` + **entryMode** 出码，`target<=3` 走 monitor 段、否则走其它 cfx 段（`§7.1` 两段编码未重排）；`nodeVectorReachable` 的地址规则与 `NodeTLB::translate` 同源（`NodeAddrMask`/cfxha=addr[47:42]/内部 SRAM 偏移 `0x3ff_0000_0000` + 64 KiB，与 `node_tlb` 的 hmon/smon/pmem 判定同常量）；Tiny 路径逐位不变（其分支在 Node 分支之前且已 `return`）；`inst.cc` 的 `curInstWord` 只在 Node bookkeeping 段赋值，SE/Tiny 不触。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `machineFault` 之名与现语义（进 monitor、兜底才退出）不符 | ❌不修 | 无改动；已在 `fs_machine.hh`/`inst.cc` 注释写明「FS 上就是执行期同步异常」 | 改名会波及 Tiny/SE 20+ 调用点、且 `check-interface` 断言引用该名，超本任务范围 |
| F2 `RASOF` 的 `cause_info` 应为「准备压栈的返回地址」，仍写 0 | ⏸延后 | 无改动 | 需 `exec/b5` 回传通道；无探针覆盖；登记遗留① |
| F3 Node 无 `IALIGN` 落点 | ⏸延后 | 无改动 | 改前既有缺口（`fs_tlb` 才有），与本次路由无关；登记遗留② |
| F4 cfx0（VA）向量的可达性只查 `ptw_enable`，不查页表映射 | ✅有 spec 依据 | 无改动（注释写明依据） | `§5.2` 步 7「软件须保证异常向量所在页不会发生页缺失，硬件不提供向量缺失的恢复机制」 |
| F5 ILLI 的 `cause_info` 在 BootROM 存储 raise 点看不到指令字 | ✅已修 | 新增 `NodeState.curInstWord`，由 `DadaoInst::execute()` 逐指令记录；`node_tlb` 的 ROM 存储分支取它 | 帧实测 `cinfo:2=0x21504000`（与 `contracts/opcodes.yaml` 独立派生一致）；注入③的对照组证明该字段可判 |
| F6 `prev_run_mode` 若在切换后取值会用错模式 | ✅已修 | `nodeSyncEnter` 在 `nodeCfxEnter` 之前判可达，兜底出码用 `entryMode` | 注入②在用户态帧上把 `PREVM:0` 由 0 变 2，正常构建为 0 |
| F7 探针超时会把 gem5 子进程留成孤儿并写爆磁盘 | ✅已修 | 证据脚本加 `EXIT` trap，按 `PARITY_WORK_ROOT` 只杀本脚本派生的 `gem5.opt` | 本轮磁盘写满后清理成功恢复（333 GiB 可用）；脚本默认组不再残留 |

判决：F5–F7 已修并复验；F4 有 spec 依据；F1/F2/F3 登记为遗留/不修理由；状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-17，全部独立重跑）

1. **重跑（cwd=任务 worktree 根）**：`make check-gem5-decode` rc=0；`make check-patch-tree` rc=2（qemu 段 11 条=m14-qemu-005 在途）但 **gem5 段 0 problem**；`make_patch gem5` `0 written`、补丁目录 md5 前后同 `1f1e7d44…`；`check-source-state` gem5 `OK count=1 clean=True`；任务树/源树快照前后均 `git status` 0 行、与完成区「修改文件」8 项对账一致。
2. **首轮 `run.sh` FAIL 的根因是我方失误**：以证据目录为 cwd 调用，`.work` 软链使 `cd "$(git rev-parse --show-toplevel)"` 落到主工作树（make_patch 日志里的目标路径是主工作树的 `components/gem5/patches`，非本任务 worktree）⇒ 首轮 E2/E3 无效；改 cwd 重跑如上（全绿）。该 cwd 依赖缺陷记 finding F1。
3. **`check-arch`：尝试1 rc=2、尝试2 rc=2（记次数 2），8/14 红，全部 QEMU 侧外部**：日志全程只跑 `[qemu]`（Makefile `_locked-check-arch` 带 `DADAO_TEST_PROFILE=vast`、14 探针）；`.work/source/qemu` 脏（`cpu.h`/`helper.c` 含 `DADAO_SUB_NONPTW (1ULL<<57)`）；红值 `0x200000000000002 / 0x10000000000002 / 0x8000000080` 正是其子原因位；qemu 二进制 `67cb9acf`（交付时，我开跑前实测）→`229bf0f1`（m14-qemu-005 自 00:56:54Z 起 install-host 在途）；本任务 diff 不含 qemu ⇒ **未决：待 m14-qemu-005 收口复跑**。
4. **帧+兜底（我重跑 `frame_check.py`）**：`RESULT: PASS`、45 PASS/0 FAIL（含 `ptwerr_monitor_cfxmem_exit exit=0xf1`、用户态 `prevm:0=0x0`）；D 组 `FRAME_ENGINE=qemu` rc=0 逐字段同，qemu md5 `67cb9acf…`（=交付时二进制）。
5. **改前复现（我自跑）**：`gem5-before.opt`（11-15 产物）跑 `049t/old_ram_unmapped` → `exit exp=0x0 got=0xf1; rd10–13 全 0` ⇒ staged 直退属实。
6. **staged 反例（任务验收项2，我从正确 cwd 重跑其 `run.sh --inject staged`）**：`RESULT: PASS (4 checks, 0 failed)`、exit=0 —— 注入后 `049t/old_ram_unmapped got=0xf1`、`integ048t/power_bootrom_store got=0xe8` 双红、`§7.1` 兜底例仍绿；`cp` 还原 md5 `a3a77621…`==baseline → 重建 rc=0 → 回绿。
7. **注入 R1（自设计，非其三路）**：`nodeSyncEnter` 去掉可达性判 ⇒ `integ040t/ptwerr_monitor_cfxmem_exit` `TIMEOUT rc=1`（0xf1 消失）→ 还原 md5 `e4d9effb…`==baseline → 重建 rc=0 → `PASS 1/1` ⇒ **兜底出口仍可达且是该例唯一出口**。
8. **注入 R2（自设计）**：`node.curInstWord=0` 切断 ILLI info ⇒ `cinfo:2 exp=0x21504000 got=0x0 rc=1` → 还原 md5 `3f4d0fe0…`==baseline → 重建 rc=0 → `PASS`。四路注入均 `cp`+md5、无 checkout/restore、结束无孤儿 `gem5.opt`、盘 333G 可用、未开大 trace。
9. **staged 真删（逐 hunk + 自跑 grep）**：`src/arch/dadao` `exitSimLoopNow` 仅 `fs_machine.cc:131`（`machineFaultExit` 内），`machineFaultExit` 调用点 2（invoke 兜底 + nodeSyncEnter 兜底）；`if (0)/#if 0` 0 命中；`node_tlb` `machineFault(` 0、`machineFaultAt` 6、`nodeSyncEnter` 2；无注释桩；`trapTo` 先判 `nodeActive` ⇒ Node 不落 `isFsMachine` 直退口。
10. **帧四项 spec 复推（我自推）**：prev=§5.2 步5 在步6 切换前（实现 `prevRunMode=entryMode` 先于 `runMode=switchRunMode`）；cid §5.2(二) `CFXMEM=1<<1=0x2`、`ILLI=1<<8=0x100`（`m16-gem5-009` 状态=待开始 ⇒ 子原因不属本任务）；cip=触发指令地址、取指例 `cip==cinfo==非法IP`（§5 IP 停留）；cinfo §4.1 = 访存地址 `0xffff00001000 / 0x1000000 / 0xffc000000000 / 0x83ff00010000(=PMEM_BASE+64KiB) / 0x800000000000(=32<<42) / 0x180000000000(=6<<42)`，ILLI `0x21504000`（`contracts/opcodes.yaml` `st.o_rrii_rd`：`0x21<<24 | 20<<18 | 4<<12 | 0` 独立算得）——与实测逐项相同。
11. **越界核验**：`git diff --name-only 558025a0..7614debb` = 6 个 `components/gem5/patches/**` + `components/gem5/changelog.md` + 本任务书；无 `spec/`、`contracts/`、`tests/**`、`components/{qemu,linux,chipyard}`；`tools/**` 零改动（未动任何期望值）；未提交 git；基线钉死 558025a0。
12. **披露①（我造成的现场变化）**：首轮 cwd 误落主树致 `make_patch` 写脏主树 6 个 gem5 patch ⇒ 已用 `git cat-file blob HEAD:` 取基线字节 + `cp` 还原、md5 对账，主树 `git status` 0 行、`git diff` 空。
13. **披露②**：我的重跑覆盖了 `.work/evidence/m16-gem5-010/logs/*.log`（engineer 原始日志被本轮日志替换；完成区文字未动）；**披露③**：注入重建后 `gem5.opt` md5 `a6ca74c9…`，交付值 `030f51a4…` 我在任何重建前实测一致（增量重建非逐位可复现=完成区坑④）。
14. **findings（非阻断，交 architect）**：F1 `run.sh` 的 `cd "$(git rev-parse --show-toplevel)"` 经 `.work` 软链会落主工作树（可脏主树/跑错仓），应改为显式 worktree 根；F2 完成区「qemu 段 7 条」现 11 条、「全树 exitSimLoopNow 1 处」精确口径是 `src/arch/dadao/` 内 1 处（另有上游无关命中）；F3 `check-arch` 现 8 红须待 `m14-qemu-005` 收口复跑。
15. **判决：Accepted** —— 验收 1–4、6 与门控 1–4 在我独立重跑下全绿、4 路注入（2 自设计 + 其 staged + 其脚本路径）均「红→cp+md5 还原→重建→回绿」成立；验收 5 的 `check-arch` 我两轮重跑 8/14 红、根因为并发写者 `m14-qemu-005`（证据见 3，非本任务缺陷），复跑排队交 architect 终审。

## 收尾订正（复核 F1–F3，2026-11-17）

- **F1**：`run.sh` **依赖 cwd**（以证据目录为 cwd 时 `.work` 软链会让 `git rev-parse --show-toplevel` 落主工作树，`make_patch` 写脏主树 6 个 patch）⇒ 属 `ISS-456` 的**复发**，已在 issue 里记复发；本任务侧由复核 `cp`+md5 还原、主树 `git status` 0 行。
- **F2**：完成区两处口径订正 —— ①「qemu 段 7 条」现为 11 条（`m14-qemu-005` 在途，非本任务）；②「全树 `exitSimLoopNow` 1 处」的精确口径是 **`src/arch/dadao/` 内 1 处**（`fs_machine.cc:131`，`machineFaultExit` 内）。
- **F3**：`check-arch`（14 探针）在 `m14-qemu-005` 在途期间红且**全为 QEMU 侧**（qemu 源树含 `DADAO_SUB_NONPTW (1ULL<<57)` 注入态、二进制 `67cb9acf→229bf0f1`）⇒ **由 `m14-qemu-005` 的验收覆盖**（它的验收本就含 `check-arch` 14 探针）；本任务不再单独复跑。
