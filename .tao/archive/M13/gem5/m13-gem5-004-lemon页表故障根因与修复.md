# m13-gem5-004: gem5 SE 页表故障未投递给 guest（`lemon` 的 `GenericPageTableFault` 根因与修复）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-003`（非对齐 `.bss` 修复后 `lemon` 才能装载）；与 `m13-gem5-003` **同一组件，须串行**
**可并行分片**：否（组件单写者）
**状态**：已验证

## 背景

`m13-gem5-003` 修掉 `ISS-359` 后，dynamic `llvm-ts` 的 7 例从 `blocked` 转为可装载。其中：

- `Burg`、`spiff` ⇒ pass；
- `obsequi`/`sqlite3`/`bc`/`mafft` ⇒ 可装载，600 s 预算内未完成（属长尾，见 `m13-testcases-003`）；
- **`lemon` ⇒ 可装载并运行 56.5 s，随后 abort（`rc=-6`），日志为 gem5 内部的 `GenericPageTableFault`**；engineer 称「static 基线上同签名」。

用户 2026-11-10 裁定：**立任务查根因并修复**（放 M13）。

## 现象与待查

- 触发点：dynamic `lemon`（`MultiSource/Applications/lemon`）运行期出现 guest **未映射访问**。
- gem5 的反应是**仿真器内部 fatal/abort**，而不是把故障按 SE 语义投递给 guest（SIGSEGV）。
- QEMU 侧同一 ELF/同一套件**通过**（`m13-testcases-002` 结果），说明这不是程序自身必错，而是 gem5 的行为差异。
- 需要先确认：`static` 基线是否真同签名（用户已知悉 engineer 的声称，但**须用未改动的基线二进制独立复现**），若 static 不同签名，说明与 dynamic 装载路径相关，根因范围不同。

## 目标

1. **根因**：定位 `GenericPageTableFault` 的产生点（哪个地址、哪条翻译路径、是 SE 的 `seWorkload` 缺页处理还是 `process.cc` 的段映射缺失），给出最小复现命令与关键日志/调用栈。
2. **修复**：guest 访问未映射地址时，按 SE 语义**向 guest 投递故障**（SIGSEGV / guest 可见异常），**不得**让仿真器自身 abort；`lemon` 的最终结果与 QEMU 一致（pass 或按 oracle 的确定 fail，不得死于仿真器）。
3. **不掩盖**：若是 gem5 自身映射表错误（如段未登记）而非「guest 真越界」，则修映射而不是把 fatal 降级为 warning——两者必须在完成区明确区分。

## 验收标准

1. 根因说明：触发地址 / 翻译路径 / 为何 abort，附最小复现命令与真实输出（`rc`、日志行、调用栈）
2. 修复后 `lemon`（dynamic）结果与 QEMU 一致；给出 run 时耗与退出码
3. **基线对照**：用未改动的基线二进制复现 static 同例，判定是否同签名（结论写清）
4. 回归：`check-inst`（Vast 980/985 + 5 deferred、Tiny 44/44）、`check-inst-smoke`、`check-arch`、`check-unit`、L2 零回归；`check-patch-tree`/`check-source-state` rc=0
5. 补丁由 `make_patch.py gem5` 导出（非手改），`series`/`changelog.md` 同笔
6. 一键证据脚本（含可达 FAIL 注入：回退修复应使 `lemon` 重新 abort）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- 不处理 4 例 timeout（`obsequi`/`sqlite3`/`bc`/`mafft`，属 `m13-testcases-003` 长尾预算）
- 不改 QEMU / chipyard / spec
- 不做性能优化

## 说明

- 组件单写者：`m13-gem5-003` 收口（合并到 master）后方可开始。
- 构建在主控机（`JOBS=8`）；节点 207/208 正跑 `m13-testcases-003`，**不要占用**。
- 若根因涉及 `spec/` 语义（例如 SE 是否应向 guest 投递 SIGSEGV），先登记冲突、按现有 spec + QEMU 行为推进，不擅自改 spec。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. **不得写入未经主会话转达的用户裁定**；自定事项写「自决」（`ISS-365`）。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`src/arch/dadao/se_workload.cc`（`doClone`/`doExecve` 的 `zeroPages` 继承、`doExit` 的地址空间回收）、`src/sim/process.cc`（`deallocateMem` 按物理页清零）、`src/arch/dadao/tlb.{hh,cc}`（`PageFault` 投递 + VMA 内缺页就地 `fixupFault`）、`components/gem5/{series,changelog.md}`、证据 `run.sh` / `tlb_fault.c`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 诊断用 `cprintf`（TLB/SYS/ZERO/DEALLOC）留在组件源 | ✅已修 | 全部删除；`make_patch.py` 导出的 4 份补丁即最终态 | `grep -rn M13GEM5004` 组件源为空；补丁与源一致 |
| 证据脚本 C2「无子进程死亡」判据错误：`lemon` 的 `ecmascript.y` 子进程在 QEMU 下同样非零退出（父进程打印 `Error while running on`） | ✅已修 | 改为「gem5 stderr 的每条 `Error while running on` 必须也出现在 QEMU 输出里」 | 修复态 subset PASS；旧判据在修复态即假红 |
| C3 前缀比较拿 gem5 `guest.stdout` 对 QEMU `2>&1` 合并输出 ⇒ 0x1a98c1 假红（fd1/fd2 交错方式不同） | ✅已修 | 先剔除 QEMU 合并输出里的父进程 stderr 行得到 fd1 视图，再比前缀 | 1,743,060 B 逐字节相同 |
| `inject_edits()` 传相对路径 ⇒ 注入未落盘（I1 误报 same、I3 仍 139） | ✅已修 | 传 `.work/source/gem5/<path>`；I1 用 md5 列表逐文件比较 | 注入态 I1 changed、I3 探针 134 + VA 0 panic、I4 lemon 重新 panic |
| 探针命令把 `--num-threads` 放在 `se.py` 之前（gem5 rc=2 unknown option） | ✅已修 | 移到脚本之后 | B1–B3 全绿 |
| 有界 lemon 跑到 84 子进程时 `fatal: Out of memory`（256 MiB 池）：进程退出不回收物理页 | ✅已修（新缺陷） | `doExit` 对不共享页表的进程按映射逐页 `deallocateMem`（CLONE_VM 兄弟跳过） | 见完成区「全量运行」 |
| `count_of()` 在日志缺失时输出空串 | ✅已修 | `printf '%s' "${n:-0}"` | 缺文件时记 0 |
| `process.cc` 注释前误删一空行（无关 diff） | ✅已修 | 恢复空行，补丁只含本质改动 | `make_patch.py` 重导出 1 written/100 unchanged |
| `check-patch-tree` 首跑在**主工作树**（master 的补丁集）红 | ✅已修 | 改在任务 worktree 跑 | 任务 worktree 内 rc=0（331 补丁） |
| 另一并发任务把共享 `.work/source/chipyard` 提前 amend（14:09）⇒ 本 worktree 的 chipyard 补丁集与之不匹配 | ⏸延后（外部红） | 不动他人组件 | `check-patch-tree` 的 6 条问题全在 chipyard 断言⑥/⑨；gem5 的 101 补丁断言全过（同一命令、同一 worktree） |

判决：本任务范围内全部 finding 已修；chipyard 红为并发任务的外部红；状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-10，独立重跑；日志 `.work/log/gem5/m13-gem5-004-reviewer-*`）

**重跑记录（全部本人执行，退出码/输出原样）**
1. `RUN_DIR=<reviewer> bash .work/evidence/<任务ID>/run.sh --full` ⇒ **`RESULT=FAIL`，`22 checks, 1 failed`**：B0–B3/C1–C3/D2/D3 PASS（`C3 bytes compared: 1743060`），D1 `check-patch-tree` rc=2。（第 2 轮补注：此处原写具体 `.work/` 路径，`check-knowledge-refs` 判 rc=2；系本人第 1 轮笔误，已改 `<>` 形，复跑 rc=0。）
2. `make check-patch-tree`（本 worktree）rc=2、`20 problem(s)` **全 chipyard**（断言⑥⑨），**gem5 0 problem**；主工作树 master 同命令 rc=2（13 条 = 7 条 gem5「master 补丁集尚不含本任务 4 份」+ 同 6 条 chipyard）；`.work/source/chipyard` HEAD 提交时间 `2026-11-10 15:23:50`（审查期间仍被并发任务 amend）⇒ 外部红，非本任务。
3. 门控本人重跑：`check-inst` rc=0（Vast 985/980/5 deferred、Tiny 44/44）、`check-inst-smoke`/`check-arch`/`check-unit`/`check-modules`(L2)/`check-source-state`/`check-knowledge-refs` **均 rc=0**；`check-gem5-decode` rc=0（`--full` D3）。
4. `run.sh --inject`（**全新 RUN_DIR 首跑**）⇒ **`RESULT=FAIL`，`31 checks, 3 failed`（I3×3）**，根因 `fatal: Failed to open file <RUN>/tlb_fault.elf`——`inject_loop` 先 `run_probe`、后 `probe_checks`（才编译探针）；同轮 I1/I2/**I4**/I5×4/I6/B*/I7 均 PASS。补入探针 ELF 后**重跑 ⇒ `31 checks, 0 failed`、`RESULT=PASS`**。
5. **独立注入（只回退 R1：删 `pp->zeroPages = process->zeroPages;`×2；`cp`+md5 `863bd4f5…`→`c0c5fce6…`，build rc=0/128 s）**：自写最小探针 `dirty_page.c`（fork 子进程 mmap→写0xAA→munmap→再 mmap→读首字节）——**注入态 `child dirty=64 nonzero_byte=0xaa clean=0`，修复态 `dirty=0 clean=64`**；对照 VA-0 探针注入态仍 rc=139、无 panic（R3 未动）；lemon 300 s 注入态 rc=124、无仿真器 panic，但 stderr 出现 QEMU 之外的死亡子进程 `parse.y`、`wireshark_mate_grammar.lemon`（修复态与 QEMU 同为仅 `ecmascript.y`）⇒ 脏页→mallocng→`a_crash()` 空写→guest SIGSEGV。还原：md5 相等、源树 clean、build rc=0、回绿（`dirty=0`、default rc=139、handler `HANDLED signo=11 code=1 addr=0`）。
6. 根因指令独立核：`llvm-objdump -d musl/lib/libc.so` ⇒ `0x83c94 ∈ enframe`（`0x83bc0+0x224`）、指令 `st.b rd11,[rb4,0]`（前序 `set.zw …,0`+`rd2rb {rb4},{rd10}`）= 空指针写 `a_crash()`，与完成区逐字吻合。
7. 层②代码位：`src/sim/process.cc:359` 原 `SETranslatingPortProxy(system->threads[0], Always)`；`src/mem/se_translating_port_proxy.cc:55 fixupRange()` 用 `_tc->getProcessPtr()`、`Always` 分支 `allocateMem(range.vaddr,…)`；`src/sim/system.cc:95` `ContextID id=size()` ⇒ context0 = 首建线程（父进程）⇒ 子帧未清、父页反被写/被分配。
8. 基线（验收3，本人复现）：`gem5.opt.baseline` md5 `dee4abaf…`、`strings` 无 `DADAO unmapped-page fault` ⇒ 确为未改动基线；VA-0 探针 **rc=134 + 同一 panic 行 + `GenericPageTableFault::invoke` 栈帧**；static `lemon` **rc=134、60 s、同一 panic 行** ⇒ 同签名成立。
9. **全量 lemon（engineer 遗留 run，我方核到收尾 17:27）**：`seconds=10856.52`、guest `exit=0`、`sim.log` **0 panic**、`GEM5_EXIT_CAUSE=exiting with last active thread context`；guest stdout **34,860,820 B 与 QEMU fd1 视图逐字节相同**；stderr 20 行与 QEMU 同集（仅 `ecmascript.y`）。**但驱动 `klass=fail`（`md5(output+exit)=7aec71bc…` ≠ 参考 `8c485439…`）、驱动 `EXIT=1`**：oracle 哈希的是「stdout+stderr 交错文档」，gem5 SE 的 fd1/fd2 是分离宿主文件（驱动自记 `gem5_output_order`），20 条 stderr 全在文末、QEMU 则散布流中 ⇒ 该 md5 对 gem5-se **结构性不可达**，而 QEMU 为 `pass`。
10. 有界轮（我方 `--full`）：QEMU `pass / 33.12 s`；gem5 `blocked / timeout after 600s / 601.09 s`、stdout 1,743,060 B = QEMU 全量 34,860,820 B 的**前缀 5.0 %**。

**约束核验**：独立 worktree `m13-gem5-004` ✓；未 commit（HEAD 仍 `WIP:`、`git status` 空、无 upstream、未 push）✓；完成区 20 行 ≤30 ✓、无运行期路径（`.work/source/**` 属门控显式豁免，`check-knowledge-refs` rc=0）✓；改动 7 文件 = 完成区 6 项 + 本任务书（完成区未写「另本任务书」，003 惯例有写）；`doExit` 越界已披露 ✓；`M13GEM5004` 诊断残留 0 ✓；`series` 101 = 补丁 101 且字典序 ✓；补丁由 `check-patch-tree` 断言⑥⑨机械证明与源/HEAD 一致 ✓。

**判决：Needs Revision**
- **阻断①（验收2 未达成，且完成区与真实输出不符）**：全量结果是驱动 `fail`（oracle mismatch，10856.52 s、guest exit 0、驱动 rc=1），QEMU 是 `pass`；完成区「600 s 有界 1,743,060 B 与 QEMU fd1 输出逐字节相同」实为 **5 % 前缀**（脚本自身判据就叫 `byte-exact prefix`）；遗留问题①的完成判据「`klass=pass` + md5 与参考一致」**已证不可达**。要求：完成区/遗留问题改写为上述真实结果 + 判据不可达结论；「oracle 是否接受 gem5 SE 的 fd1/fd2 顺序差异」属**路由层问题**，交架构师裁定，reviewer/engineer 不擅自改驱动或 oracle。
- **阻断②（证据脚本不可独立跑通）**：全新 RUN_DIR 下 `--inject` rc=1（I3×3，探针 ELF 在 `inject_loop` 后半才编译）⇒ 把探针编译提到 `inject_loop` 之前，并在**全新 RUN_DIR** 重跑得 `RESULT=PASS`。
- 非阻断：`check-patch-tree` rc=2 属并发 chipyard 任务（gem5 断言全过）；完成区「另本任务书」漏写、OOM「第 84 个子进程」现场实为 86 个进程装载（1 主 + 85 子）、「QEMU 30.5 s」现场 `seconds=33.12`——文档级，收尾一并改。

**三个单独回答**：① 根因三层链**成立**（层①由本人独立注入 + 最小探针直接观测 64/64 脏页证实；层②代码位与 `threads[0]`=首建线程证据吻合；层③ 256 MiB 池 OOM 由 `doExit` 不回收帧导致，我方全量 run 在该修复下 180 min 无 OOM）。② `process.cc` 通用文件改动**无跨架构风险**：对初始进程（`threads[0]` 即自身）新旧写同一物理帧、行为等价；对其它 ISA 的 fork 子进程由「写错地址空间」改为「写本帧」，属纯修复；`physProxy` 为 `System` 常驻成员、页对齐，无额外前提。③ `doExit` 越界**可接受**：验收2（结果与 QEMU 一致）在 260 个 fork 子进程下必须回收帧才可能达成，属验收必需而非顺手改，且已按硬约束4 披露；建议架构师在收尾时决定是否单列任务承接 `doExecve` 同类泄漏（完成区遗留问题②）。

### 第 2 轮 engineer 返工（第 1 轮 reviewer：全量 oracle 真值 + `--inject` 顺序）

只改证据脚本与任务书，**未动被测代码**（组件源 `dadao: gem5 patch series` base+1、clean；4 份补丁与源一致）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 阻断① 完成区只写「600 s 有界 1,743,060 B 与 QEMU fd1 逐字节相同」（实为全量 34,860,820 B 的 5 % 前缀），未写全量真实结果 | ✅已修 | 完成区改写为全量真值 + 「判据当前不可达，属 oracle 路由问题，待 architect/用户裁定」；遗留问题同步；未改驱动/oracle | 全量 `run.json`：`klass=fail`、`exit=0`、`seconds=10856.52`、`md5(output+exit)=7aec71bc…` vs 参考 `8c485439…`；`sim.log` 0 panic、`GEM5_EXIT_CAUSE=exiting with last active thread context`；guest stdout 34,860,820 B == QEMU fd1 视图（全字节比对相等）、stderr 740 B/20 行与 QEMU 同序同内容 |
| 阻断② 全新 RUN_DIR 下 `--inject` 的 I3×3 报 `Failed to open file <RUN>/tlb_fault.elf`：探针在 `inject_loop` 后半才编译 | ✅已修 | 拆出 `build_probe()`（编译 + 链接 + B0 两条断言），在模式分派**之前**调用一次；`probe_checks()` 只跑 B1–B3 | 全新 RUN_DIR `--inject`：`31 checks, 0 failed`、`RESULT=PASS` rc=0（I3 `default`/`handler` 均 134、I4 lemon 重新 panic） |
| 非阻断：`check-patch-tree` rc=2 未在完成区写清 | ✅已修 | 完成区写明「rc=2 为并发 chipyard 任务，gem5 断言全过」 | 本轮 `--full` 的 `gate-patch-tree.log`：`check-patch-tree: gem5:` **0 条**、`chipyard:` **20 条**（10 文件 × 断言⑥⑨） |
| 非阻断：完成区漏写「另本任务书」 | ✅已修 | 「修改文件」补「另本任务书」 | — |
| 非阻断：OOM 现场写成「第 84 个子进程」 | ✅已修 | 改为「第 86 个进程装载」（现场 `Unknown operating system` 警告 86 条 = 1 主 + 85 子） | 运行期证据目录 OOM 日志 `grep -c` = 86 |
| 非阻断：「QEMU 30.5 s」 | ✅已修 | 改为 `seconds=33.12`（驱动 json 的 `seconds` 字段；`run_seconds=31.79`） | `lemon-qemu/run.json`：`seconds=33.12` |

判决：两条阻断 + 四条非阻断全部处理；状态保持 `待验收`。

**本轮重跑（各自全新 RUN_DIR，均在任务 worktree 内执行，rc 原样）**：
- `run.sh --full` ⇒ `22 checks, 1 failed`、`RESULT=FAIL`、**rc=1**；唯一红 = D1 `check-patch-tree`，其日志 `check-patch-tree: gem5:` **0 条**、`chipyard:` **20 条**（外部）。
- `run.sh --inject` ⇒ `31 checks, 0 failed`、`RESULT=PASS`、**rc=0**；I3×3（探针 134 + VA 0 panic）、I4（lemon 重新 panic）、I5×4（`cp`+md5 逐字节还原）、I6、B*、I7 全过。
- 收尾核对：组件源 4 文件 md5 `863bd4f5…`/`87b3a369…`/`a1ccfb8b…`/`259285f6…`、`git status` 空；本轮改动仅证据脚本与本任务书。

### 第 2 轮 reviewer 验收（2026-11-10，独立重跑；日志 `.work/log/gem5/m13-gem5-004-reviewer-r2-*`）

**重跑记录（全部本人执行，退出码/输出原样）**
1. **阻断②**：`RUN_DIR=<全新目录> run.sh --inject` ⇒ **`31 checks, 0 failed`、`RESULT=PASS`、rc=0**；`build_probe()` 在模式分派**之前**调用（`run.sh:381`，分派 `:388`），全新目录内 `tlb_fault.elf` 于 inject/lemon 阶段**之前**即存在；I3×3（探针 134 + VA 0 panic）、I4（lemon 重新 panic）、I5×4（`cp`+md5 逐字节还原）、I6、B1–B3、I7 全过；跑完组件源 clean。
2. **阻断①**：全量真值本人重算 —— `gem5 guest.stdout == QEMU fd1 视图` **全字节相等**（34,860,820 B，`g==qstd` True，**非前缀**）；stderr 两侧各 **740 B / 20 行、同序同内容**；`md5(QEMU 交错文档+"exit 0\n")=8c485439…`（= `lemon.reference_output`）、`md5(gem5 stdout+stderr+"exit 0\n")=7aec71bc…`；交错位 QEMU 首条 stderr 在 `1,743,041`（散布流中）、gem5 在 `34,860,820`（= stdout 末尾）⇒「交错 vs fd1/fd2 分离」解释成立；`run.json` `klass=fail`、`seconds=10856.52`、`exit=0`。完成区已无「600 s 1,743,060 B 逐字节相同」式表述（全文 grep 仅剩背景行、engineer 第 1 轮自审历史行与本人第 1 轮记录）。
3. **被测代码零改动**：4 文件 md5 `863bd4f5…`/`87b3a369…`/`a1ccfb8b…`/`259285f6…` 与第 1 轮**逐个相等**；`git diff c69ebca6..HEAD -- components/` = **0 行**（两笔新提交只动任务书）；`git status` 空；组件源 base+1、clean。
4. **门控**：`RUN_DIR=<另一全新目录> run.sh --full` ⇒ **`22 checks, 1 failed`、rc=1**，唯一红 D1；其日志 `check-patch-tree: gem5:` **0 条**、`chipyard:` **20 条**（10 文件 × 断言⑥⑨）、`20 problem(s)`；D2 `check-source-state` rc=0、D3 `check-gem5-decode` rc=0；C3 `bytes compared: 1743060`（脚本判据本就是 `byte-exact prefix`）。归属交叉验证：**主工作树**同命令 rc=2 但 `chipyard:` **0 条**、`gem5:` **7 条** —— 本分支 chipyard 补丁集是旧版（master 已随 `m12-chipyard-018` 合入新集、共享源 `17:06:20` 与之相符），master 则缺本任务 4 份 gem5 补丁 ⇒ **两处红互为镜像，均非本交付物缺陷**。
5. 其余门控（本人重跑）：`check-inst`（Vast 985/980/5 deferred、Tiny 44/44）/`check-inst-smoke`/`check-arch`/`check-unit`/`check-modules`(L2)/`check-source-state` **全 rc=0**。

**约束核验**：完成区 20 行 ≤30 ✓；任务书无运行期路径（仅硬约束条文的 `/tmp/opencode/<任务ID>/` 占位形）✓；未 commit（HEAD `a0bd2054`、`git status` 空、未 push）✓；本轮改动仅任务书 + 证据脚本 ✓；4 份补丁/`series`/`changelog` 自 WIP 起未变 ✓。

**判决：Accepted**（第 1 轮两条阻断均经我方重跑证实真修）
- 非阻断：`run.sh --full` 因 D1 仍 rc=1，红项已独立归因并发 chipyard 任务（本分支 gem5 断言 0 条；主工作树 chipyard 0 条），`check-patch-tree` rc=0 待分支合入 master 后复跑留证。
- 非阻断（文档级，收尾顺手改）：engineer 第 1 轮自审表 C3 行仍写「1,743,060 B 逐字节相同」（历史行、上下文已写「比前缀」），建议改「前缀」。
- **需用户裁定，不因此返工 engineer**：`oracle 交错 vs fd1/fd2 分离` 属**判据口径问题**（`ISS-357` 类），非代码缺陷——stdout 全字节一致、stderr 同序同内容、guest `exit=0`、0 panic，仅因 oracle 对「stdout+stderr 交错文档」哈希而 gem5 SE 是两个宿主文件，`klass` 判 `fail`。口径（接受 fd1/fd2 顺序差异 / 改 oracle 口径 / 保持 fail 并登记 known-gap）**由用户裁定**，reviewer 与 engineer 均不代裁；本任务未改驱动与 oracle。

**三个单独回答**：① 两条阻断**均真修**（②全新 RUN_DIR `--inject` 31/31 rc=0；①完成区已按全量真值改写并经我方逐字节重算核对）。② 全量真值**如实**（34,860,820 B 全字节相等、740 B/20 行同序同内容、两个 md5 与 `seconds`/`exit` 逐项对上），判据不可达**已写清**并标注待裁定、未改驱动/oracle。③ oracle 路由属判据口径，**应由用户裁定**（= 验收标准变更，属停止点）；建议 architect 上呈三选项并先按现状收口，待口径确定后再决定是否立任务改 oracle 或改 fd 合并策略。

## 完成区

**测试结果**：
- VA-0 故障探针：`ok` rc=0；`default` rc=139（guest 死于 SIGSEGV、仿真器正常退出、0 panic）；`handler` rc=0 且收到 `signo=11 code=1(SEGV_MAPERR) addr=0`。
- `lemon`（dynamic）**全量**（260 个 fork 子进程，`seconds=10856.52`）：guest `exit=0`、0 panic、`GEM5_EXIT_CAUSE=exiting with last active thread context`；guest stdout **34,860,820 B 与 QEMU fd1 视图逐字节相同**（stderr 740 B / 20 行与 QEMU 同序同内容，仅 `ecmascript.y`）。**驱动判 `klass=fail`**（`EXIT=1`）：`md5(stdout+stderr+"exit 0\n")=7aec71bc…` ≠ 参考 `8c485439…` —— 参考按 **stdout/stderr 交错文档**哈希，gem5 SE 的 fd1/fd2 是两个宿主文件（20 条 stderr 全在文末），与 `ISS-357` 同类。**完成判据（`klass=pass` + md5 与参考一致）当前不可达，属 oracle 路由问题，待 architect/用户裁定；本任务未改驱动、未改 oracle。**
- 基线对照（static）：未改动基线二进制 + static `lemon` ⇒ **同签名**（VA 0、同一 panic 行、59.1 s），与 dynamic 装载路径无关。
- 注入：回退 3 处修复 ⇒ 探针 rc=134 + VA 0 panic、`lemon` 重新 panic；`cp`+md5 逐文件还原后全绿（全新 RUN_DIR `RESULT=PASS` rc=0）。
- 门控：`check-inst` Vast 980/985（5 deferred）+ Tiny 44/44；`check-inst-smoke`/`check-arch`/`check-unit`/`check-gem5-decode`/`check-source-state`/L2 `check-modules` rc=0；`check-patch-tree` **rc=2 属并发 chipyard 任务**（共享源 17:06 再被 amend，本 worktree 的 chipyard 补丁集是旧版）：20 条问题全在 chipyard 断言⑥⑨，**gem5 0 条**。

**修改文件**：`components/gem5/patches/src/arch/dadao/se_workload.cc.patch`、`.../src/arch/dadao/tlb.cc.patch`、`.../src/arch/dadao/tlb.hh.patch`、`.../src/sim/process.cc.patch`（新增）、`components/gem5/series`、`components/gem5/changelog.md`、**另本任务书**；组件源 `dadao: gem5 patch series`（base+1、clean）。证据脚本/探针/关键日志在运行期证据目录。**越界披露（自决）**：`doExit` 的地址空间回收不在任务书列的 3 项目标内，但全量 `lemon` 在 256 MiB 池下第 86 个进程装载时必然 OOM，不补则「与 QEMU 一致」不可达，故一并修复。

**验收结果**：
- 红①（修复前）：`src/sim/faults.cc:103: panic: … Page table fault when accessing virtual address 0`，abort / 驱动 rc=-6。
- 根因指令：TLB 诊断 `vaddr=0 mode=1 pc=0x200083c94`；该 PC 是 mallocng `enframe` 的 `st.b rd11,[rb4,0]`（rb4=0），即 musl `a_crash()`，由 `assert(!p[-4])` 触发——元数据页被「回收未清零的脏页」污染。
- 绿：探针 139 / `HANDLED signo=11 code=1 addr=0`；全量 lemon stdout 34,860,820 B 与 QEMU fd1 逐字节相同、0 panic；QEMU 同例 `klass=pass`、`seconds=33.12`。

**新发现/坑**：① 三处独立缺陷串成一条链（`zeroPages` 未继承 → `deallocateMem` 用 `system->threads[0]` 的地址空间清零 → fork 型负载把池耗光）；② SE 下 `GenericPageTableFault::invoke` 对「无 VMA 访问」直接 panic，`fixupFault` 只是它的降级路径——必须在 TLB 里把「VMA 内缺页」与「真未映射」分开；③ gem5 SE 的 fd1/fd2 分离使「stdout+stderr 交错」的 oracle 对 fork 型程序结构性不可达（`ISS-357` 类）——有界比较必须先剔除父进程 stderr 行得到 fd1 视图；④ `lemon` 的 `ecmascript.y` 子进程在 QEMU 下也非零退出；⑤ gem5 `deallocateMem` 用 `system->threads[0]` 是通用缺陷（其它 ISA 的 fork 同样受影响）。

**遗留问题**：① **全量 lemon 的 oracle 路由**：`klass=fail` 仅因 stdout/stderr 交错方式不同（stdout 逐字节一致、0 panic、guest exit 0）——判据是否接受 gem5 SE 的 fd1/fd2 顺序差异，待 architect/用户裁定；本任务不动驱动/oracle。② `doExecve` 未回收旧镜像的物理页（同类泄漏，未展开）。

#### 收尾（architect，2026-11-10 20:01）

- 第 2 轮 **Accepted**：`--inject` 全新 RUN_DIR 31/31 rc=0（探针前置）；全量真值独立复算——stdout **34,860,820 B 全字节相等**（非前缀）、stderr 740 B/20 行同序同内容、`md5=7aec71bc…`≠参考 `8c485439…`、`seconds=10856.52`、`exit=0`、0 panic。
- 根因三层链经**独立注入 + 最小探针**验证（只删 `zeroPages` 继承 ⇒ 子进程 64/64 回收页带 0xAA，修复态 0/64）。
- 被测代码零改动（4 文件 md5 与第 1 轮逐个相等）；门控 gem5 全绿，D1 红项与 master 互为镜像（均为并发组件集差）。
- **判据口径转 `m13-testcases-006`**：分通道比对（stdout/stderr 分离），`lemon` 因参考为 md5 且两路非空 ⇒ 显式 `blocked`（非 fail、非放水）。
- `ISS-357` 由 `m13-testcases-006` 关闭（顺序不再进入判据）。
