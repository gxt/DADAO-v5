# m18-linux-021: 内核 hart-first 异步入口/返回/调度（cfx_hart cg9）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-qemu-004`（QEMU hart-first/cg9）已验证；`m18-llvm-001`（汇编器支持 `escape ..., 8`）
**可并行分片**：否
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为内核异步入口/返回/调度 + K2/K5 探针，取 2–3× 中位）
**档位**：大改（内核异常入口/调度）
**状态**：已作废（2026-11-23，`ADR-0061` 改写异步模型；本任务不再验收，替代任务 `m18-linux-022`）
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-qemu-004` 已把 QEMU 异步投递改为 hart-first：所有异步源进 `cfx_hart`，现场/mask/pending 在 `cg9`，`escape imms18=2` 选 cg9。内核仍按 monitor-first/旧异步路径（`async_trap.S` 以 `cfx_hart` 向量 + `irq_enter_rcu`、无 cg9），K2/K5 内核镜像门控与新 QEMU 不匹配。

## 目标

1. **入口**：异步入口固定 `cfx_hart cg9 rc6`（supv）；捕获 GPR 到任务 `task_pt_regs`；按 cg9 `prev_run_mode`/`from_user` 判是否切任务内核栈；用户态用 `dadao_user_stack_top`。
2. **现场/返回**：保存/恢复 cg9 现场（`prev_run_mode`/`prev_cfx`/`cause_ip`/`cause_id`/saved global mask）；返回用 `escape imms18=2`（cg9）；无帧/释放路径按 `DADAO-12 §5.3`；不得清 `cause_id` 后误返回。
3. **调度**：用户态异步走 `irqentry_enter/exit` + return-to-user work loop（`_TIF_NEED_RESCHED`/信号）；内核态异步不调度（沿用 `irq_enter_rcu/irq_exit_rcu`）；`pending` 在 cg9 rc5（位 cause 17/18），mask 位源 cfxha 15/32。
4. **探针**：K2 irq/time、K5 异步探针适配 hart-first；`tests/unit/linux/{k2_irq_probe,k2_time_probe}.py` 的期望与 QEMU 同步；新增/保留可达 FAIL。
5. **用户态时间可见/抢占**：按 ADR-0060 D6，用父进程 `/proc/uptime` 采样 + 子进程忙循环，另加 `alarm/SIGALRM` 交叉；500 次启动稳定性。

## 验收（逐条贴真实 rc）

1. 用户态异步投递进 `cfx_hart cg9`；`cause_id` 17/18、pending cg9、mask 位 15/32 有探针证据；`escape imms18=2` 返回正确。
2. 用户态忙循环期间 `jiffies` 推进（父进程采样 `/proc/uptime` 差值 ≈ 墙钟）；`alarm/SIGALRM` 不靠 syscall 投递；两个 CPU 密集任务按 tick 轮转。
3. 连续 **500** 次启动全部进入用户态（无 `ISS-498` 回归）；无 `die-no-vma`/panic。
4. **可达 FAIL ≥3 路**（`cp`+md5 还原+重建）：① 仍投 monitor/旧向量 ⇒ 入口断言红；② 不恢复 cg9 saved mask ⇒ 返回红；③ 去掉 `irqentry_exit` 工作循环 ⇒ 抢占/信号红。
5. 不回归：`check-linux-k0`–`k6` 全 rc=0；`check-config-pins`/`check-patch-tree` linux 段 0 problem/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
6. K2/K5 内核镜像门控由红转绿（此前 QEMU hart-first 已使旧镜像必红）。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（异步入口/返回/调度）、`components/linux/changelog.md`、`tests/unit/linux/**`（K2/K5 探针）、`tools/linux/**`（仅必要）、本任务书。
3. 不改 `spec/`、`.tao/contracts/`、`Makefile`、`components/qemu|musl|busybox/**`；不改版本号。
4. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建；术语「bank = 寄存器组」；时间口径按 `ADR-0058`。
5. 不把「测试改期望」当内核修复；内核行为按 spec/ADR-0060，不反向改契约。

## 待裁定

### 0（2026-11-23，取代）
**被 ADR-0061 取代，等待 m18-spec-004/qemu-005 后重写；已实测 cg9 释放/escape 矛盾，见运行期证据。**
（本任务书与下列「待裁定 1」均基于 ADR-0060；ADR-0061 改：掩码归 monitor、源索引统一 cfxha（取消 17/18）、`cg9` 精简为七槽（两个位图 HW/RO）、一帧多源、帧由 `escape` 结束。按用户 2026-11-23 指令：停止按旧口径推进，未做任何实现改动，未跑 K2/K5；现场与探针证据保留。注：本 worktree 基于 `167e6ad0`，其中尚无 `adr-0061` 文件，以上口径按用户传达记录。）

### 1（阻塞）`cg9`「释放帧在 `escape` 之前」与 `escape` 的帧有效性互斥 —— 目标 2 与 3 在同一帧上不可同时成立

**冲突文本（均在 spec 真源内）**

- `spec/DADAO-12 §5.2（四）`「软件可管」：*"释放帧应在 `escape` **之前**完成……`escape` 本身**不清** `async_cause_id`"*（`contract-see §6.3`「帧有效性与无嵌套」同句）。
- `spec/DADAO-12 §5.1`（现文件第 873 行）与 `§5.3` 第 0 步（第 1059 行）：选 `cg9` 帧时*"`async_cause_id = 0` ⇒ 在切换任何状态前触发 `CFXESC`"*；`§5.3` 第 1 步（第 1060 行）又写明 `escape` **不改写** `async_cause_id`（`contract-see §6.2`「失败即 `CFXESC`」同）。

⇒ 「先释放（写 `cg9 rc3 = 0`）再 `escape`」按 §5.1/§5.3 必 `CFXESC`；「先 `escape` 再释放」按「escape 不清」必然留下活动帧，而活动帧（`cause_id != 0`）让硬件只置 `async_pending`、不再进入。

**实现与实测证据（非纸面推断）**

- QEMU（`m18-qemu-004`，`components/qemu/patches/target/dadao/helper.c.patch`）：`helper_cfx_escape()` 的 cg9 分支 `if (cfxha_map[ci] != HART || a->cause_id == 0) → CFXESC`；`cg9 rc3` 的 `case 3` 是唯一释放口；`escape` 只恢复 `rc8 ← rc4` 与 `prev_*`、不改 `cause_id`。
- 运行期临时探针（非交付物，位于本任务临时目录内 `probe_release_before_escape.py`；QEMU = `m18-qemu-004` 构建的 hart-first `qemu-system-dadao`，`DADAO_TEST_PROFILE=vast`，退出码为真实 rc）：
  - **A**：handler 内写 `cg9 rc3 = 0` 后 `escape cfx_hart, 8` ⇒ cfx_hart supv 同步向量记录到 `cause = 1<<3`（`CFXESC`），退出码 **0xE2**（若原因不是 `CFXESC` 会走 0xE9 分支）。
  - **A2（隔离变量）**：只清 `async_pending`、不动 `cause_id` 再 `escape` ⇒ 合法返回，退出码 **0x00** ⇒ 拒绝 A 的唯一变量是 `cause_id = 0`。
  - **B（对照）**：handler 正常 `escape`（帧仍活）、返回后由特权代码释放 ⇒ 第二次事件才进入，退出码 **0x00**。
  - **C（检验 ADR 的「重建现场后返回」）**：写 `cause_id = 0` 后再写回 `cause_id = TIMER`（重建）→ `escape` 合法返回，但帧仍活 ⇒ 第二次事件仍不进入，退出码 **0x00** ⇒ 「重建」不能恢复投递。
- 同机对照：stock `min_rom_probe_integ051t --only timer_frame_hart` PASS（rc=0），证明探针环境/固件本身可用，A 的红不是环境问题。

**对内核的后果（逐条对应验收）**

- 一次 `escape` 之后 `async_cause_id != 0`；恢复投递只能由**能访问 `cfx_hart cg9` 的特权上下文**写 0 完成。
- **用户态**：若按目标 2 的「`escape imms18=2` 返回」实现，帧保持活动 ⇒ 用户忙循环只能被**一次** tick 打断（验收 2 与 `ADR-0060 D6` 不可达）。改用「进 handler 即释帧 + work loop + `trap cfx_umon` 回用户」（现有 `dadao_enter_user` 机制）可让用户态这半重复投递且**不需改 spec**——但这不是「用 escape 返回」，与目标 2 冲突。
- **内核态（决定性）**：内核态返回必须恢复「返回模式/当前 cfx/IP」，可用的只有两种：①目标 2 要求的 `escape cfx_hart, 8`（cg9）——但它必然留下活动帧，故内核态连续 tick（K2 时间门控的 N tick、K5 T 组「连续投递 / `jiffies_64` 每次 +1」）不可达（验收 6 不可达），「重建现场再返回」实测也无效（C）；②R3 的 cg5 trampoline（先释 cg9 帧、再用 `trap cfx_hart` 造 cg5 帧 + `escape cg5` 恢复）——可行但不用 `escape imms18=2`，与目标 2 冲突。
- **且会污染用户态半**：内核态任一次投递（work loop 期间、syscall 期间、boot 期都算）留下活动帧后，**此后所有**异步投递（含用户态）都停摆，直到某个特权上下文释帧；现行 spec 下内核路径没有「返回前释帧」的手段。⇒ 目标 3 的用户态抢占即使单独做出来，也会在第一次内核态 tick 后停摆，不能算交付。

**可选裁定（请选一项；我未按任何一项动手）**

- **R1（推荐；改动最小、语义自洽）**：cg9 的 `escape` 帧有效性判据由「`async_cause_id != 0`」改为「当前 cfx = `cfx_hart`」——即允许在**已释放**（`cause_id = 0`）的帧上返回（`prev_*`/`cause_ip` 是快照，释放不动它们）。这样 §5.2（四）「先释放再 escape」成立。改动面：`spec §5.1/§5.3` 两处措辞、`contract-see §6.2`、QEMU `helper_cfx_escape` 一处、`min_rom_probe_integ051t` 增一条正例；RTL/gem5 同改。
- **R2**：`escape`（cg9）在返回时**清除** `async_cause_id`（返回即释放）。与「escape 不清」相反；需改 spec/contract/QEMU/probe 现有断言（`escape_keeps_cause`/`no_nest_frame`），内核同样简单。
- **R3（不改 spec）**：内核自建「释放 + 经 cg5 返回」：用户态「释帧 → work loop → `trap cfx_umon` 回用户」（现有 `dadao_enter_user` 机制）；内核态「释帧 → `trap cfx_hart, 0` 造 cg5 帧 → cg5 stub 写回 `prev_*`/`excp_cause_ip` → 恢复 GPR → `escape cfx_hart, [excp_cause_ip, 0]`」。代价：`cfx_hart cg2 rc10` 改作返回 trampoline、每 hart 状态块、`rc11` 屏蔽窗内防重入，约 250 行汇编；**完全不用 `escape imms18=2`**，与目标 2/`ADR-0060 D4` 表述不一致，须 architect 明确允许。

**任一方案都要一并定的两点**（本任务推演/实测出的必要约束，不属新决策）

1. **跨 `schedule()` 的窗口**：单一 `cg9` 帧若在 user 路径的 work loop 里被睡眠跨越，别的任务可能建立新帧；故 user 路径的「返回」必须以**软件帧**（`task_pt_regs` + `trap cfx_umon`）为准，并在进 handler 前释放 `cg9`。
2. **内核路径的免嵌套窗**：handler 期 `rc8` 保持硬件置的全 1（探针已断言 `inside_global == ALL1`），返回前只恢复 `rc11`（被中断值）并释帧，最后一条 `escape` 由硬件把 `rc8 ← rc4` —— 这样「释帧 → escape」之间不会被同源重入（`rc8` 与 `rc11` 同时放行才投递）。

**我的处置**：按任务书「若发现 cg9 语义/spec 冲突，停下写「待裁定」」——**未改任何实现文件**（`git status` 空，`HEAD = 167e6ad0`），避免按未定口径写出半套内核。裁定后入口/帧捕获（cg9 rc0–rc4）/mask（rc8/rc11，位 = 源 cfxha）/pending（rc5，位 = cause id）/IE 旋钮与用户路径的大部分代码与方案选择无关，可直接落地。

## 完成区

**测试结果**：未跑 L1/L2 门控（阻塞于上面冲突，先取得决定性证据）：临时探针 4/4 得预期结论（A 释帧后 escape ⇒ 0xE2 且记录 `cause = 1<<3`；A2 只清 pending ⇒ 0x00；B 活帧挡投递、特权释放后恢复 ⇒ 0x00；C 重建后 escape 仍留活帧 ⇒ 0x00）；同机 stock `min_rom_probe_integ051t --only timer_frame_hart` PASS（rc=0）作环境对照。
**修改文件**：无（仅本任务书；`git status --porcelain -uall` 为空）。
**验收结果**（真实 rc）：
- `DADAO_TEST_PROFILE=vast python3 probe_release_before_escape.py --qemu <m18-qemu-004 构建的 hart-first qemu-system-dadao>` → `caseA exit=0xE2`（`CFXESC` 拒绝）、`caseA2 exit=0x00`（只清 pending 则合法）、`caseB exit=0x00`、`caseC exit=0x00`（重建后再 escape 仍留活帧、无第二次进入），rc=0。
- `min_rom_probe_integ051t --only timer_frame_hart`（同 QEMU）→ `PASS ... rc=0x00`，rc=0。
**新发现/坑**：
1. **主树 `.work/build/qemu` 是 hart-first 之前的旧二进制**：用它跑 stock `timer_frame_hart` 会 TIMEOUT；K2/K5 前必须 `make build-qemu JOBS=32`，否则会把环境问题误判成内核问题。
2. `min_rom_probe_integ051t` 的几何默认 `tiny`、`node_probe_prelude` 的机器默认 `vast`：直接跑需显式 `DADAO_TEST_PROFILE=vast`，否则静默 TIMEOUT。
3. 「待裁定 1」的判定方法可复用：临时目录内 import `min_rom_probe_integ051t`，自定义 `hmon_extra` + handler + `cfx_hart cg2 rc10` 同步向量记录器，即可对 escape 合法性做单点判定（含「原因确为 CFXESC」的分支）。
**遗留问题**：**本任务书被 ADR-0061 取代**（见「待裁定 0」）：目标 1–5/验收 1–7 随任务书一并作废，待 `m18-spec-004`/`m18-qemu-005` 落地后由 architect 重写再派。旧口径下的阻塞结论（cg9 释放/escape 互斥，四组实测）保留为证据。未提交 git、未改 spec/contracts/Makefile/qemu/musl/busybox、未升版本号、未跑 K2/K5。

## 审阅记录

### 第 1 轮 engineer 自审

**审查对象**：本任务无源码改动（`git status` 空、`HEAD = 167e6ad0`），自审对象是「阻塞判定」本身——它决定本任务是否值得继续写内核。逐条核对：spec `§5.1`/`§5.2（四）`/`§5.3` 原文与行号（本 tree 实测）、`contract-see §6.2/§6.3`、`ADR-0060 D3/D4/D5`、QEMU `helper_cfx_escape`/`dadao_async_enter`/`dadao_hart_async_reg_write` 逐行、`tests/ee-vast/hmon_k0_vast.S` 的 cg9 放行（deleg `0x8` + 源位 `{2,15}` ⇒ 内核可访问 cg9，无需固件改动）、`process.c::dadao_enter_user` 的用户返回机制（`trap cfx_umon`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 首版只测「清 pending + 清 cause_id 后 escape 被拒」，无法排除「清 pending」也是原因 | ✅已修 | 探针加 A2（只清 pending）与 C（重建 cause_id）两例 | A2/A/C 三例：0x00/0xE2/0x00，唯一变量 `cause_id` |
| F2 ADR 的「重建现场后返回」可能是出路，首版未检验 | ✅已修 | 加 case C：`cause_id=0` 后写回 `TIMER` 再 escape | C=0x00：escape 合法但帧仍活、第二次事件不进入 |
| F3 「用户态无法释放帧」是设计前提（用户不得有 `cg9` 访问权），非硬件验证 | ⏸延后 | 报告措辞已限定为设计前提；若要用户代码写 cg9，属 ABI/安全新决策 | `hmon_k0_vast.S` 只对源 cfx `{2,15}` 开 cfx_hart 的 supv 行与 deleg |
| F4 环境风险：主树 QEMU 旧二进制会让 stock 探针 TIMEOUT，可能被误读成「内核/规范问题」 | ✅已修 | 完成区「新发现/坑」1/2 点名，并用 stock 用例 PASS 作对照 | `timer_frame_hart`：旧 QEMU rc=124、qemu-004 构建 rc=0 |
| F5 报告引用的 spec 行号可能漂移 | ✅已修 | 以本 tree 实测行号（873/1059/1060）标注并附原文 | 直接 `sed -n` 读回 |

**约束核验**：独立 worktree、未提交 git、`git status` 空；未改 `spec/`/`.tao/contracts/`/`Makefile`/`components/{qemu,musl,busybox}`/版本号；未动 `components/linux/**`；临时探针只在运行期临时目录内；`make check-knowledge-refs` rc=0、`make check-component-changelog` rc=0。
**判决**：**不置「待验收」**（目标 1–5 全未实现，阻塞于「待裁定 1」），状态保持 `待开始`，返回主会话请裁定 R1/R2/R3。

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
