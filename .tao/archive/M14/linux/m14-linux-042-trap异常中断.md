# m14-linux-042: trap/异常/中断 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：2–3 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：已验证

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

第一批中 `m14-linux-036`/`037`/`039`（mm/syscall/信号）已验证并形成格式基线；`038`（时间）、`040`（Kconfig）仍在进行中、未收尾，本任务不把它们的结论当已交付引用。格式基线：**每条带两侧 `文件:行号` + 影响面 + P0/P1/P2**，覆盖数**现场派生**，抽查用 `sed -n` 贴原文。

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/kernel/trap.S`、`async_trap.S`、`traps.c`、`irq.c`（若有）、`include/asm/{ptrace,processor,irqflags}.h` 的异常相关部分；对比 `arch/riscv/kernel/{traps,entry.S,irq.c}`（主）与 `arch/arm64/kernel/{entry-common,traps}.c`（参照）。重点：`irqentry_*`/`irq_enter_rcu`、异常分类与 `die`/`force_sig_fault` 分流、`fixup_exception` 出口、嵌套与抢占、`in_interrupt`/`in_hardirq` 语义。

## 要做

逐个 hook / 机制判定属于哪一类，并给证据：

1. **缺失 hook**：上游有、我们没有；
2. **语义不符**：有但行为不同（返回码 / 副作用 / 加锁 / 顺序 / 何时切栈）；
3. **旁路 vs 通用**：我们自造实现，上游走通用 `kernel/`、`mm/` 路径；
4. **Kconfig 缺口**：缺 `select` / `depends on` 导致通用代码没编进来。

**每条格式**：`arch/dadao/<file>:<line>` ↔ `arch/riscv/<file>:<line>`（必要时补 `arch/arm64`）/ 影响面 / 优先级（**P0** 阻塞在跑任务；**P1** 影响正确性；**P2** 仅形态差异）。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行），**每条带两侧 `文件:行号`**；
2. **覆盖现场派生**：列清检查了哪些 hook / 机制及条数（不写死），并写清枚举口径（命令）；
3. **抽查 ≥5 条**：用 `sed -n '<行>p'` 贴两侧原文，**不许凭记忆**；
4. **不改任何代码**：用 `git show --name-only HEAD` 与 `git status -uall` 判「只改了本任务书」（**不要用裸 `git diff`/`git status` 计数**——提交后会变空，`m14-linux-036` 已踩过）；
5. 不占写者锁、不重建、不跑仿真。

## 盘点结论

**基线**：Linux 源树 `c5f411a3a`（7.2.10＋dadao 补丁态，只读检出；未 `apply_series`/`reset`/`make`）；下文 dadao 行号取自该态，riscv/arm64 为同树对照。036 已报的 mm 侧条目只标「同族」，不重复计数。共 **27 条**。

### ① 缺失 hook（8 条）

- **[P1] 异步入口完全不经 IRQ 子系统**：`arch/dadao/kernel/async_trap.S:38-61`（只保存现场/调 C，无 `irq_enter_rcu`/`set_irq_regs`/`irq_exit_rcu`）＋`arch/dadao/kernel/time.c:299-317`（handler 只置 `dadao_in_frame`）↔ `arch/riscv/kernel/traps.c:424-432`（`irq_enter_rcu`→`set_irq_regs`→`handle_arch_irq`→`irq_exit_rcu`）、`:435-444`（`irqentry_enter/exit`）。影响：`include/linux/hardirq.h:46-50` 的 `preempt_count_add(HARDIRQ_OFFSET)` 从未执行 ⇒ `in_hardirq()`/`in_interrupt()` 恒 0、`get_irq_regs()` 恒 NULL、`irq_exit_rcu()` 不跑 softirq；`might_sleep()`/`in_atomic()` 在中断里误判为可睡眠。
- **[P1] 无 `irqentry_*` 框架**：`arch/dadao/Kconfig:9-22`（无 `select`）＋`arch/dadao/` 全树 grep `irqentry_*` 0 命中 ↔ `arch/riscv/Kconfig:112`（`select GENERIC_ENTRY`）、`arch/riscv/kernel/traps.c:150-154`（用户异常）／`:414-420`（页故障）；`kernel/entry/Makefile:15` 只在 `CONFIG_GENERIC_IRQ_ENTRY` 下编 `common.o`。影响：`irqentry_enter_from_user_mode`/`irqentry_exit_to_user_mode`/`irqentry_nmi_enter` 全部不可链接；当前构建配置实测 `CONFIG_GENERIC_IRQ_ENTRY` 未设置。
- **[P1] 返回用户态无 `exit_to_user_mode_loop`/`syscall_exit_to_user_mode`**：`arch/dadao/kernel/syscalls.c:127-142`（`dadao_user_syscall_post` 只做 restart 码，固定返回 SKIP）＋`arch/dadao/kernel/process.c:345`（`dadao_ret_from_fork` 直接 `dadao_enter_user`）↔ `arch/riscv/kernel/traps.c:325-345`（`syscall_enter_from_user_mode`＋`syscall_exit_to_user_mode`）、`kernel/entry/common.c:42-89`（`TIF_NEED_RESCHED`→`schedule()`、`TIF_SIGPENDING`→`arch_do_signal_or_restart`）。影响：用户态信号/抢占/`TIF_NOTIFY_RESUME` 永不处理；039 的「信号无出口」在 trap 侧的入口证据。
- **[P1] 无 `fixup_exception`／`__ex_table` 修复出口**：`arch/dadao/kernel/traps.c:512-521`（页故障类失败直接 `dadao_die`）＋`arch/dadao/include/asm/Kbuild:7`（只 generic `extable.h`，无 `mm/extable.c`）↔ `arch/riscv/mm/fault.c:93-99`（`no_context`→`fixup_exception`）、`arch/riscv/mm/extable.c:82`；`arch/arm64/mm/fault.c:418`。影响：内核态坏用户指针/`copy_from_user` 走裸 `memcpy`（`arch/dadao/Kconfig:15`）⇒ 整机 semihost 退出而非 `-EFAULT`（036 同族，trap 侧根因）。
- **[P1] 内核态异常无 NMI 入口**：`arch/dadao/kernel/traps.c:427-430`（重入即 selfcheck 0x0e）／`:521`（直接 die）↔ `arch/riscv/kernel/traps.c:156-158`、`:187-192`（`irqentry_nmi_enter/exit`）；`arch/arm64/kernel/entry-common.c:561-563`。影响：内核态嵌套异常不置 `in_nmi()`、无 NMI lockdep/RCU；handler 内二次异常即整机退出。
- **[P1] 无 irqchip/irqdomain/`handle_arch_irq`**：`arch/dadao/kernel/irq.c:87-145`（`init_IRQ` 直接写 cfx 行；无 `irqchip_init`/`handle_arch_irq`）＋`arch/dadao/include/asm/irq.h:5-7` ↔ `arch/riscv/kernel/irq.c:148-155`、`arch/riscv/Kconfig:206`（`IRQ_DOMAIN`）／`:119`（`GENERIC_IRQ_MULTI_HANDLER`）。影响：无 `irq_desc`/`irq_domain`/`request_irq` 生态，第二个异步源无法接入；`/proc/interrupts` 为空（`arch/dadao/kernel/traps.c:612-615`）。
- **[P1] 异步源只认 TIMER，其余直接退出**：`arch/dadao/kernel/time.c:308-314`（非 TIMER 或 `info≠0` → `dadao_async_die`）↔ `arch/riscv/kernel/traps.c:424-432`（`handle_arch_irq` 分发到 irqchip）。影响：IPI/PMEM_DMA 等源无分发点，SMP/多源前置缺失。
- **[P2] 无 `notify_die`/oops 通知链**：`arch/dadao/kernel/traps.c:299-309`（`dadao_die` 只写 `dadao_flog_last`）↔ `arch/riscv/kernel/traps.c:97`（`notify_die(DIE_OOPS)`）；`arch/arm64/kernel/traps.c:186`。影响：kprobe/kgdb/kdb/kexec/`panic_on_oops` 收不到 oops；与 B3 同族。

### ② 语义不符（11 条）

- **[P0] `user_mode()` 恒返回 0**：`arch/dadao/include/asm/ptrace.h:81-87` ↔ `arch/riscv/include/asm/ptrace.h:67`、`arch/arm64/include/asm/ptrace.h:198`。影响：`mm/mmap_lock.c:444/469` 的 `lock_mm_and_find_vma()` 把用户缺页当内核态，取锁失败时走 `search_exception_tables()`（本机空表）⇒ 返回 NULL；035 阶段 2 的入口改造在锁竞争下直接失败；它也是 B2/B7 不能分流的总根因。
- **[P1] 用户态同步异常不分流 `force_sig_fault`**：`arch/dadao/kernel/traps.c:369-374`（非页表类用户 cause 直接 monitor 退出）／`:377-381`（页故障失败直接退出）＋`arch/dadao/kernel/process.c:527-536`（非 CFXTRAP 直接退出）↔ `arch/riscv/kernel/traps.c:115-129`（`do_trap`→`force_sig_fault`）、`:132-141`（user/kernel 分流）；`arch/arm64/kernel/traps.c:291-302`。影响：用户 SIGSEGV/SIGILL/SIGBUS 不可达，任一用户故障停机（036 第 2 条／039 同族）。
- **[P1] fatal 路径直接 `dadao_die`，无 `die()/make_task_dead`**：`arch/dadao/kernel/traps.c:299-309`、`:521` ↔ `arch/riscv/kernel/traps.c:76-112`（`oops_enter`/`notify_die`/`panic_on_oops`/`make_task_dead(SIGSEGV)`）；`arch/arm64/kernel/traps.c:206-234`。影响：内核 oops 杀整机而非当前任务；`panic_on_oops`/kexec 无效。
- **[P1] `irqs_disabled()` 在异常帧内可能为假**：`arch/dadao/include/asm/irqflags.h:132-142`（只看软件 `DADAO_IRQ_SOURCE_BITS` 位）＋`:145-151`（承认硬件 `global_cfx_intr_mask` 全 1 保护帧）↔ `arch/riscv/include/asm/irqflags.h:37-45`（SIE 位）。影响：帧内硬件实际不可投递，软件却报 IRQ enabled；`might_sleep()`/`in_atomic()`/lockdep 误判，中断 handler 可“合法”睡眠。
- **[P1] `local_irq_disable()` 只屏蔽 TIMER 一位，不是全局 IE**：`arch/dadao/include/asm/irqflags.h:48`（`DADAO_IRQ_SOURCE_BITS = 1<<15`）、`:100-116` ↔ `arch/riscv/include/asm/irqflags.h:31-33`（清 `SR_IE`，屏蔽所有源）。影响：临界区只挡 TIMER；第二异步源接入后 `local_irq_save()` 不再等于“关中断”。
- **[P1] 用户态运行时 TIMER 被 umon 的 user 行屏蔽**：`arch/dadao/kernel/irq.c:130-133`（只清 `cfx_smon` supv 行 bit15）＋`arch/dadao/kernel/process.c:364-366`（`cfx_umon` cg0 只写 switch/vector，未清 rc4）↔ `arch/riscv/kernel/traps.c:435-444`（IRQ 与运行模式无关，统一 `do_irq`）。按 `.tao/contracts/contract-see.md:153`（过滤查“当前运行模式 monitor”）用户模式查 `cfx_umon_user_cfx_intr_mask`（复位全 1）；影响：纯用户态计算不被 tick 抢占；若在 supv 窗口补投，则叠加 A3 的用户 SP 问题。
- **[P2] 用户故障经 `trap cfx_smon` 转手后模式字段变 supv**：`arch/dadao/kernel/trap.S:273-290`（user 帧转 supv 通道）＋`arch/dadao/kernel/traps.c:120-121`／`:293-295`（exit code 读 smon 帧 `prev_mode`）↔ `arch/riscv/kernel/traps.c:150-154`（用户异常直接用 user `regs`）。影响：smon 帧本身不含用户模式；当前用户路径用 B2 的硬编码 `0xc0|(USER<<4)` 绕过，任何未来走 `dadao_exit_code()` 的报告都会记成 supv；B1 之外的第二处“用户态身份丢失”。
- **[P2] 静态单帧 + 全局 re-entrancy 标志，非 per-task/per-cpu**：`arch/dadao/kernel/trap.S:125-135`（`.bss` 单 `dadao_excp_save`）＋`arch/dadao/kernel/traps.c:235`（全局 `dadao_trap_busy`）＋`arch/dadao/kernel/async_trap.S:72-76` ↔ `arch/riscv/kernel/entry.S:252-322`（`ret_from_exception` 用当前任务栈上的 `pt_regs`）。影响：handler 内二次异常会覆盖现场；SMP 后多 hart 共用一帧。
- **[P2] `dadao_in_frame` 是布尔而非嵌套深度**：`arch/dadao/kernel/traps.c:45`／`:537-540`＋`arch/dadao/kernel/time.c:305-317` ↔ `arch/riscv/kernel/traps.c:156-158`（NMI enter/exit 成对嵌套）。影响：async 帧内再进 sync 帧，内层退出即清 0；semihosting 抑制判定失真。
- **[P2] `arch_ptrace` 全 `-EIO`、`ptrace_disable` 空**：`arch/dadao/kernel/traps.c:618-627` ↔ `arch/riscv/kernel/ptrace.c:544-555`（默认回落 `ptrace_request`）、`:540`。影响：PTRACE_* 标准请求不可用；与 D4 的 `HAVE_ARCH_TRACEHOOK` 缺口同源。
- **[P2] `cfx_umon` cg5 单帧跨任务复用，只回写 `cause_ip`**：`arch/dadao/kernel/trap.S:199-202`（adopt task 帧）／`:240-255`（睡眠后只重写 cg5 rc3，未重写 `prev_mode`/`prev_cfx`/global mask）↔ `arch/riscv/kernel/entry.S:252-322`（每任务栈帧）。影响：一个任务在 syscall 中睡眠、另一用户任务再进 umon 时，`escape` 依赖的 cg5 其余字段属于后一个任务；当前所有用户 trap 的 mode/cfx 相同故未显性，属结构缺口（只读分析，未实测）。

### ③ 旁路 vs 通用（3 条）

- **[P1] 自建 `dadao_fault_probe` 取代异常表/`notify_die`**：`arch/dadao/kernel/traps.c:197-227`、`:468-497`＋`arch/dadao/include/asm/trap.h:83-98` ↔ `arch/riscv/mm/extable.c:82`、`arch/riscv/kernel/traps.c:97`。影响：探针只能编译进内核、同时一个（`-EBUSY`），无 kprobe/uprobe/kgdb 动态插桩。
- **[P2] 自建 tick 取代 `tick_periodic`/`update_process_times`**：`arch/dadao/kernel/time.c:238`（`jiffies_64 += 1`）、`:259-260`（只 `sched_tick()`）↔ `arch/riscv/kernel/time.c:46-48`（`timer_probe()`→clockevent）、`kernel/time/tick-common.c:101`（`update_process_times(user_mode(get_irq_regs()))`）。影响：timer wheel、RCU/任务时间统计、`profile_tick` 都不跑；归 038（时间/时钟，未收尾）范围，待其结论，不在此重复判定。
- **[P1] 自建 syscall 入口绕过 `syscall_enter_from_user_mode`**：`arch/dadao/kernel/process.c:516-669`、`arch/dadao/kernel/syscalls.c:127-142` ↔ `arch/riscv/kernel/traps.c:325-345`。影响：seccomp/audit/ptrace syscall stop/trace 全部缺失；与 A3/D4 同源。

### ④ Kconfig 缺口（5 条）

- **[P1] 缺 `select GENERIC_ENTRY`（及 `GENERIC_IRQ_ENTRY`）**：`arch/dadao/Kconfig:9-22` ↔ `arch/riscv/Kconfig:112`、`arch/arm64/Kconfig:133`；`kernel/entry/Makefile:15`。影响：`kernel/entry/common.o` 不编，A1/A2 的 `irqentry_*`/`exit_to_user_mode_*` 无定义；当前构建配置实测未设置。
- **[P1] 缺 `IRQ_DOMAIN`/`GENERIC_IRQ_MULTI_HANDLER`/`GENERIC_IRQ_SHOW`**：`arch/dadao/Kconfig:9-22` ↔ `arch/riscv/Kconfig:206`／`:119`／`:120`、`arch/arm64/Kconfig:235`／`:137`。影响：A6 的 irqchip/irqdomain/`/proc/interrupts` 缺口根因。
- **[P1] 缺 `TRACE_IRQFLAGS_SUPPORT`/`IRQ_STACKS`/`HAVE_IRQ_EXIT_ON_IRQ_STACK`**：`arch/dadao/Kconfig:9-22` ↔ `arch/riscv/Kconfig:228`、`:901-904`、`arch/arm64/Kconfig:256`。影响：无 lockdep IRQ 状态跟踪；无独立 IRQ 栈（A3 根因）。
- **[P2] 缺 `HAVE_ARCH_TRACEHOOK`/`HAVE_ARCH_SECCOMP_FILTER`/`HAVE_ARCH_AUDITSYSCALL`/`HAVE_KPROBES`/`HAVE_ARCH_KGDB`**：`arch/dadao/Kconfig:9-22` ↔ `arch/riscv/Kconfig:148`／`:145`／`:130`／`:184`／`:140`、`arch/arm64/Kconfig:173`／`:171`／`:151`／`:230`／`:165`。影响：ptrace regset、seccomp、audit、kprobe、kgdb 通用代码不编；B10/C1/C3 的 Kconfig 侧。
- **[P1] `select UACCESS_MEMCPY` 与异常表 uaccess 相反**：`arch/dadao/Kconfig:15` ↔ `arch/riscv/Kconfig` 无此项（走 `mm/extable.c`）；`lib/Kconfig:542`。影响：`include/asm-generic/uaccess.h:13-95` 用裸 `memcpy`，坏用户指针不进异常表；A4 的 Kconfig 根因（036 同族）。

### 覆盖与口径（现场派生）

- **基线/只读**：Linux 源树 HEAD `c5f411a3a`；只读检出，未 `apply_series`/`reset`/`make`，未占写者锁。
- **文件覆盖**：dadao 侧 **17 个文件**（`kernel/{trap.S,async_trap.S,traps.c,irq.c,entry.S,time.c,process.c,syscalls.c}` 8 ＋ `include/asm/{ptrace,processor,irqflags,irq,trap,entry,thread_info}.h` 7 ＋ `Kconfig`/`configs/defconfig` 2），共 **4419 行**；riscv 6 个对照文件 ＋ arm64 3 个，共 **5332 行**；逐文件通读。
- **hook 枚举口径**：从 riscv/arm64 同名入口取 **40 个 token**（`irqentry_*` 6、`irq_enter_rcu`/`irq_exit_rcu`/`set_irq_regs`/`get_irq_regs`、`in_hardirq`/`in_interrupt`/`in_nmi`/`preempt_count`、`exit_to_user_mode_*`、`syscall_*_from_user_mode`、`fixup_exception`/`__ex_table`、`notify_die`/`force_sig_fault`/`do_trap`/`user_mode`、`local_irq_*`、`call_on_irq_stack`/`irq_stack`、`handle_arch_irq`/`irqchip_init`/`request_irq`、`show_interrupts`/`arch_ptrace`/`show_stack`、`panic_on_oops`/`make_task_dead`/`oops_enter` 等），用 `grep -rl --include='*.c' --include='*.h' --include='*.S'` 逐 token 在 `arch/dadao` 与 `arch/riscv` 计数；dadao 命中 **7**（其中 `user_mode`/`local_irq_disable`/`show_interrupts`/`arch_ptrace` 4 个语义不符）、riscv-only **28**、两侧均 0 的通用层 token **5**。
- **机制组**：**10 组**（同步入口/用户入口/异步入口/异常分类/修复出口/嵌套抢占/IRQ 子系统/返回用户/栈与帧/调试钩子），逐组对照；结论 **27 条**（①8 ②11 ③3 ④5；**P0 1 / P1 18 / P2 8**）。
- **优先级口径**：P0 仅取「阻塞在跑任务」；唯一 P0 为 B1（035 阶段 2 的 `lock_mm_and_find_vma`），其余按正确性/形态分 P1/P2。
- **Kconfig 实测**：当前构建配置 `CONFIG_GENERIC_ENTRY`/`CONFIG_GENERIC_IRQ_ENTRY`/`CONFIG_IRQ_DOMAIN`/`CONFIG_TRACE_IRQFLAGS_SUPPORT` 均未设置（`grep -c` = 0）；`CONFIG_PREEMPT_VOLUNTARY=y`、`CONFIG_PREEMPT_COUNT` 未设置。
- **行号真实性**：本段全部 `file:line` 由 `run.sh` 逐条解析（文件存在＋行号在范围＋该行非空），结果见完成区；抽查 12 条（≥5）见完成区 `sed -n` 原文。

## 完成区

**测试结果**：未提交态 39/39、提交态 38/38；运行期证据目录内 `run.sh` 两态均退出码 0（`OK=39/38 FAIL=0`、`RESULT: PASS`）；失败项：无。

**修改文件**：`.tao/tasks/linux/m14-linux-042-trap异常中断.md`（仅此一件；`arch/` 与 Linux 源树零改动；证据脚本在工作区未入库证据目录内）。未提交 git。

**验收结果**：
- 基线：Linux 源树 HEAD `c5f411a3a`（只读检出，`status --porcelain -uall` 空，未 `apply_series`/`reset`/`make`）。
- 覆盖：dadao 17 文件 4419 行、riscv/arm64 对照 9 文件 5332 行；40 token 现场 grep：dadao 命中 7／riscv-only 28／两侧均 0 5；机制 10 组；结论 27 条（①8 ②11 ③3 ④5；P0 1/P1 18/P2 8），与任务书逐项相符。
- 行号：盘点结论段 72 个 `path:line` 全部可解析（文件存在＋行号在范围＋该行非空，bad=0）；脚本对「结论＋完成区」的 81 个 refs 逐条复验（审阅记录按 reviewer 原文保留，不纳入自动 refs 检查）。
- 抽查 12 处（≥5，两侧 `sed -n '<line>p'` 原文）：`user_mode` `arch/dadao/include/asm/ptrace.h:81` `static inline int user_mode(...)` ↔ `arch/riscv/include/asm/ptrace.h:67` `#define user_mode(regs) ...`；异步入口 `arch/dadao/kernel/async_trap.S:38` `dadao_async_excp:` ↔ `arch/riscv/kernel/traps.c:428` `irq_enter_rcu();`／`:432` `irq_exit_rcu();`；`dadao_die` `arch/dadao/kernel/traps.c:521` ↔ `force_sig_fault` `arch/riscv/kernel/traps.c:129`；umon user 行 `arch/dadao/kernel/process.c:364` ↔ `arch/dadao/include/asm/irqflags.h:137`／`arch/riscv/include/asm/irqflags.h:39`；`UACCESS_MEMCPY` `arch/dadao/Kconfig:15` ↔ `GENERIC_ENTRY` `arch/riscv/Kconfig:112`。
- 注入自检（`cp` 备份＋md5 对账，非 git 还原）：把 `arch/riscv/include/asm/ptrace.h:67` 改成 `:99999` ⇒ refs 检查红（bad=1）；`cp` 还原后 md5 与注入前一致（脚本现场打印）且 bad=0；另把「共 **27 条**」改成 26 ⇒ 计数检查红。
- 不改代码：`git show --name-only HEAD` 只含本任务书（无 `arch/`/`kernel/`/`mm/`/`include/` 源码）；`git status --porcelain -uall` 仅本任务书；`git diff --name-only HEAD --` 仅本任务书。
- 门控：`make check-knowledge-refs` PASS（悬空 0；0 具体运行期路径引用）；`make check-tasks` rc=0（报告型：待验收 1=本任务，不阻断）。

**新发现/坑**：
- **`user_mode()` 恒 0 是 035 阶段 2 的 P0 隐藏前置**：`mm/mmap_lock.c:444` 与 `:469` 的 `lock_mm_and_find_vma()` 在锁竞争时把用户缺页当内核态，走 `search_exception_tables()`；本机 `__ex_table` 为空 ⇒ 返回 NULL。补 `select LOCK_MM_AND_FIND_VMA` 之外还必须先修 `user_mode()`。
- **`irqentry_*` 不是「少了几个调用」，而是 `CONFIG_GENERIC_IRQ_ENTRY` 未编**：`kernel/entry/common.o` 不在链接集，`in_hardirq()`/`in_interrupt()` 恒 0、`get_irq_regs()` 恒 NULL；`irq_exit_rcu()` 不跑 softirq。
- **用户态 tick 被 umon 的 user 行挡住**：`init_IRQ()` 只清 `cfx_smon` supv 行；按 contract-see §6.4，用户模式查 `cfx_umon_user_cfx_intr_mask`（复位全 1）⇒ 纯用户态不被 tick 抢占；若在 supv 窗口补投，则叠加 A3 的用户 SP 问题。
- **异步入口不切栈**：若将来放开用户态异步源，`dadao_async_handler()` 会跑在用户 SP 上，`current_thread_info()` 从用户 SP 推导（当前 TIMER 被遮住，属潜伏 P1）。
- `arch/dadao/Kconfig` 的 `select UACCESS_MEMCPY` 与异常表 uaccess 相反；`fixup_exception()` 无实现、`__ex_table` 空，内核坏指针整机退出。

**返工 1（2026-11-20，reviewer Needs Revision）**：
- 原因/修法：`run.sh` 干净分支 `git.tree_state` 期望/实际串写死（`clean(committed)` vs `clean`）⇒ 入 HEAD 恒红；原 `time.c` 305–315 起点是赋值、终点空行，实际 **308-314**。改为同源派生（`expected=0`/`actual=$head_other`，`git show`/`status` 加 `core.quotepath=false`）；refs 检查新增「区间终点非空」校验；全文自查合计收紧 25 处端点（含上述 305–315→308–314）（`Kconfig` 9-22；`traps.c` 197-227/299-309/369-374/377-381/468-497/612-615；`time.c` 299-317/305-317/308-314；`irq.c` 87-145；`syscalls.c` 127-142；`ptrace.h` 81-87；`irqflags.h` 132-142；riscv `traps.c` 76-112/115-129/132-141/325-345/424-432/435-444；riscv `irq.c` 148-155；riscv `ptrace.c` 544-555；riscv `irqflags.h` 31-33；arm64 `traps.c` 291-302；`entry/common.c` 42-89）。
- 提交态 rc：仓外合成「HEAD 仅本任务书」干净树实跑 `run.sh` ⇒ `OK=38 FAIL=0`、`EXIT=0`（`git.tree_state | OK expected=0 actual=0`）。
- 注入：真实工作树放未跟踪探针文件 ⇒ `git.tree_state | FAIL expected=only-taskfile actual=other`、`EXIT=1`；删除后回 `OK=39 FAIL=0`、`EXIT=0`。另把 `arch/dadao/kernel/time.c:308-314` 终点改 315 ⇒ `ref END-EMPTY`、`EXIT=1`；`cp` 还原后 md5 一致、回绿。
- 行号自证：`sed -n '308,314p' arch/dadao/kernel/time.c` ⇒ `if (cause != DADAO_CAUSE_TIMER)`／`dadao_async_die(cause, info);`／`if (info != 0) {`／两行注释／`dadao_async_die(cause, info);`／`}`。

**遗留问题**：无未完成项。27 条的整改去向（立即修／立任务／暂不修）由用户裁定；本任务只读，不改代码。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `process.c` 原 526–535 起点为空行 | ✅已修 | 改为 `arch/dadao/kernel/process.c:527-536`（`if (cls != CFXTRAP)` 块） | refs 由 bad=2 转 bad=0 |
| `entry-common.c` 原 559–562 起点为空行 | ✅已修 | 改为 `arch/arm64/kernel/entry-common.c:561-563`（`irqentry_nmi_enter/exit`） | refs 由 bad=2 转 bad=0 |
| 证据脚本 `git.tree_state` 期望串与实现不一致 | ✅已修 | 期望改为 `only-taskfile` | 重跑 39/39、`EXIT=0` |
| 多处 range 起点落在注释/空行（traps.c 193/298/44/234、irq.c 129、irq.h 4） | ✅已修 | 起点改到代码行（197/299/45/235/130/5） | refs 72/72、bad=0 |

判决：全部 finding 已修，无未修项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-20）

**判决：Needs Revision**（① 证据脚本提交态恒红；② 1 处行号错位）。以下命令与输出均为 reviewer 亲跑，未采信完成区转述。

**重跑记录**
- 仓库根执行「运行期证据目录内的 `run.sh`」：`rc=1`、`OK=37 FAIL=1`，唯一红：`git.tree_state | FAIL expected=clean(committed) actual=clean`。根因＝脚本干净分支期望/实际两串写死且永不可能相等 ⇒ 本任务书 09:41 入 HEAD 后必红；engineer 自审只改了脏树分支的期望串。完成区「39/39 rc=0」＝未提交态跑法（脏分支 3 项 vs 干净分支 2 项 ⇒ 39 vs 38，数目自洽、非编造）。
  **修改建议**：`run.sh` 干净分支的 `git.tree_state` 改成同源派生（期望 `0`、实际 `$status_lines`，仍可达 FAIL）；修后同一命令须 `rc=0`。
- 独立注入（`cp` 备份＋md5，非 git 还原）：把结论中 `arch/riscv/include/asm/ptrace.h:67` 改 `:99999` ⇒ 重跑 `rc=1`、`OK=36 FAIL=3`（`refs.all_resolved actual=1`、`refs.conclusion.bad actual=1`）；`cp` 还原后 md5＝注入前 `9d7727162fdbb1538df5e7c09c80e987`、`git status -uall` 空；还原后重跑回落基线 `FAIL=1`（同上缺陷，回绿被挡 ⇒ 返工项）。
- 行号抽查 11 条、两侧 `sed -n` 原文全对上：`ptrace.h:81-88`（dadao 全函数仅 `return 0;`）↔ riscv `:67` `#define user_mode … SR_PP` ↔ arm64 `:198`；`mmap_lock.c:444/469` 均 `if (regs && !user_mode(regs)) {`；`async_trap.S:38` `dadao_async_excp:` ↔ riscv `traps.c:428/432` `irq_enter_rcu();/irq_exit_rcu();`、`:435-445` `irqentry_enter/exit`；`traps.c:512/521`（`dadao_die` 调用点）、`traps.c:299-310`（`dadao_die` 定义）、`traps.c:618-627` ↔ riscv `ptrace.c:544-556`；`trap.S:125-135` ＋ `traps.c:235`；`irq.c:130-133` ＋ `process.c:364-366`；`irqflags.h:132-143/145-151` ↔ riscv `:37-45`（`SR_IE` 在 39）；`Kconfig:15` `select UACCESS_MEMCPY`、`kernel/entry/Makefile:15`、`contract-see.md:153`（单旋钮＝当前运行模式 monitor 行）。
- **错位（须修）**：`arch/dadao/kernel/time.c:305-315` 起点 305＝`dadao_in_frame = 1;`、终点 315 为空行，所述「非 TIMER 或 `info≠0` → `dadao_async_die`」实为 **308-314** ⇒ 改 `:308-314`（refs 检查只验起点非空，故脚本未拦住）。

**P0 四环（事实/推断分列）**：事实① `user_mode()` 81-88 单一 `return 0;`；事实② `get_mmap_lock_carefully`（:444/446）与 `upgrade_mmap_lock_carefully`（:469/471）在取锁失败且 `!user_mode` 时走 `search_exception_tables()`，未命中即 `return false` ⇒ `lock_mm_and_find_vma()` 返回 NULL；事实③ 该段在 `CONFIG_LOCK_MM_AND_FIND_VMA`（:436）之下、**当前构建配置未设**（riscv `Kconfig:209` 有 `select`，035 需补）；事实④ 构建产物 vmlinux `__ex_table` 段长 **0**（`objdump -h`），arch/dadao 零 extable 条目、`UACCESS_MEMCPY` 生效。推断：「035 阶段 2 在锁竞争下直接失败」——035 任务书未点名 `lock_mm_and_find_vma`/`user_mode`，属**有据推断**（其验收要求 `do_page_fault → handle_mm_fault`，riscv 同型入口必经此函数并需补 `select`）；P0 定级依据＝035 已在「进行中」表；结论段与完成区均已写明「补 `select` 之外还必须先修 `user_mode()`」的条件性 ⇒ P0 成立但属条件式，措辞可接受。

**CONFIG_GENERIC_IRQ_ENTRY 查实**：事实＝`kernel/entry/Makefile:15` 仅 `obj-$(CONFIG_GENERIC_IRQ_ENTRY) += common.o`；构建产物中 `common.o` 不存在、`kernel/entry/built-in.a` 空成员；构建配置内 `GENERIC_ENTRY`/`GENERIC_IRQ_ENTRY`/`LOCK_MM_AND_FIND_VMA`/`PREEMPT_COUNT` 均 0 命中（`PREEMPT_VOLUNTARY=y`）。`in_hardirq()` 恒 0＝事实（`HARDIRQ_OFFSET` 唯一写点 `__irq_enter_raw` → `irq_enter_rcu`，本构建无可达调用点；dadao 侧 `irqentry_*` grep 0）；`get_irq_regs()` 恒 NULL＝事实（`set_irq_regs` 仅 `kernel/irq/handle.c:290`，dadao 无 `generic_handle_irq` 调用链）；**须收窄**：`in_interrupt()` 含 softirq 分量，关 BH 窗口可非 0，建议改写为「硬中断/NMI 分量恒 0」。
**同根因说明**：`m14-linux-038`（时间/时钟）、`m14-linux-040`（Kconfig/选型）盘上仍在「进行中（待开始）」表、完成区待填 ⇒ **无已报结论可比对，本轮不能写「三份盘点同根因」**；就本任务自身，①-b1、①-b2、④-b1 三条是同一根因（dadao 入口不调通用入口机制 ＋ 通用入口因缺 `select` 未编）的三个侧面，属同族重复。（另：背景「第一批 036–040 已交付」与台账不符——036/037/039 已验证、038/040 未交付 ⇒ 文档级 finding，收尾时改。）

**其余 P1 抽 3 条**：用户态故障仍走 `dadao_early_exit`/monitor 码（`traps.c:369-375`、`:377-382`、`process.c:527-536`，全程无 `force_sig_fault`）↔ riscv `:115-130`/`:132-142` ✓；用户模式 TIMER 被 umon user 行挡（`irq.c:130-133` 只清 smon supv 行、`process.c:364-366` 只写 switch/vector）＋ `contract-see.md:153` ✓；`irqs_disabled()` 只看软件位而硬件 `global_cfx_intr_mask` 全 1 保护帧（`irqflags.h:132-143`/`:145-151`）↔ riscv `:37-45` ✓。

**约束核验**：不改代码 ✓（`git show --name-only HEAD` 仅本任务书；源树 `c5f411a3a` 与任务 worktree 在写入本记录前 `status -uall` 均空；注入按 `cp`+md5 还原且 md5 相等；全程未 commit/push）；`make check-knowledge-refs` rc=0（PASS、悬空 0、0 具体运行期路径引用）；`make check-tasks` rc=0（报告型，待验收 1＝本任务）。本记录写入后已重跑 `make check-knowledge-refs`：rc=0。

### 第 2 轮 reviewer 验收（2026-11-20）

**判决：Accepted**（第 1 轮 2 项阻断均在我自己的重跑下复现修复；另记 2 条非阻断 finding 供收尾改）。以下均为 reviewer 亲跑输出。

**阻断 1 已修（提交态恒红）**：HEAD＝`09074933`（`git show --stat` 仅本任务书）、工作树干净态下跑「运行期证据目录内的 `run.sh`」⇒ `rc=0`、`OK=38 FAIL=0`、`RESULT: PASS`、`git.tree_state | OK expected=0 actual=0`。核对：干净分支已改**同源派生** `chk "git.tree_state" "0" "$head_other"`（`head_other`＝`git show --name-only` 现场 `grep -vx` 计数），不再两字面量互比；脏分支可达 FAIL（其自测放未跟踪探针 ⇒ `expected=only-taskfile actual=other`）。`git show/status/diff` 四处均加 `-c core.quotepath=false`（本机 `core.quotepath` 恰为 false，加旗后中文路径不被引号化、`grep -vx` 可匹配）✓。

**阻断 2 已修（行号）**：`sed -n '308,314p' arch/dadao/kernel/time.c` ⇒ `if (cause != DADAO_CAUSE_TIMER)`／`dadao_async_die(cause, info);`／`if (info != 0) {`／两行注释／`dadao_async_die(cause, info);`／`}` —— 与「非 TIMER 或 `info≠0` → `dadao_async_die`」逐行相符，起点已离开 305 的赋值行 ✓。

**终点校验可达 FAIL（我独立注入复现）**：把 `arch/dadao/kernel/time.c:308-314` 终点改成 315 ⇒ 重跑 `rc=1`、`OK=36 FAIL=3`、stderr 四处 `ref END-EMPTY arch/dadao/kernel/time.c:308-315`、`RESULT: FAIL`；`cp` 还原后 md5 与注入前一致（`a39a0cf72a043b1b8df6f942228ffd76`）、`git status -uall` 空，再跑 `rc=0 / OK=38 FAIL=0` —— 注入→FAIL→还原→回绿闭环成立 ✓。

**收紧端点抽 6 处（要求 5），两侧 `sed`**：`arch/dadao/kernel/traps.c:369-374` 终点＝`dadao_early_exit(...)`；`arch/dadao/kernel/time.c:308-314` 终点＝`}`；`arch/riscv/kernel/traps.c:424-432` 终点＝`irq_exit_rcu();`；`kernel/entry/common.c:42-89` 终点＝`return ti_work;`；`arch/dadao/kernel/irq.c:87-145` 终点＝`bit);`；`arch/dadao/include/asm/irqflags.h:132-142` 终点＝`return` 语句。清单 25 项与现场对账得上（差集 22 项旧 token 消失＋3 项旧 token 因仍留在第 1 轮审阅记录中而不进差集，合计 25）。

**文档表述**：背景已改为「`036`/`037`/`039` 已验证；`038`、`040` 仍在进行中、未收尾，不把它们的结论当已交付引用」✓；全文无「三份盘点同根因」的肯定表述（唯一出现处是第 1 轮审阅记录的否定句「本轮不能写…」）✓。

**结论未动**：脚本现场值＝27 条／P0-P1-P2 `1/18/8`／分类 `8/11/3/5`／覆盖 `4419`＋`5332` 行／token `7/28/5`／结论 refs `72`、bad=0 —— 与第 1 轮一致 ✓。

**约束核验**：不改代码 ✓（HEAD 仅本任务书、源树 `c5f411a3a` 且 `status --porcelain -uall` 0 行、写入本记录前任务 worktree 空、注入按 `cp`＋md5 还原；全程未 commit/push）；`make check-knowledge-refs` rc=0（写入本记录前后各跑一次，均 PASS、悬空 0、0 具体运行期路径引用）；`make check-tasks` rc=0（报告型）。

**finding（非阻断，供收尾改）**：① 返工段自述收紧清单第 14 项写 `irqflags.h 132-142`，结论段实际为 `irqflags.h:132-141`，且 141＝`{`（开括号端点）⇒ 两处改齐（建议按自述收成 `132-142`，终点为 return 语句、非括号）；② `time.c:308-314` 终点 314＝`}`（闭括号）——该值系第 1 轮 reviewer 处方、内容与描述完全一致，记备注不阻断（如需可收 `308-313`）。
