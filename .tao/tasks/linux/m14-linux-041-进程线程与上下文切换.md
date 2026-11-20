# m14-linux-041: 进程/线程与上下文切换 与主流 ISA 差异盘点（只读盘点）

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

第一批（`m14-linux-036`–`040`，mm/syscall/时间/信号/Kconfig）已交付并形成格式基线：**每条带两侧 `文件:行号` + 影响面 + P0/P1/P2**，覆盖数**现场派生**，抽查用 `sed -n` 贴原文。

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/kernel/process.c`（`copy_thread`/`__switch_to`/`ret_from_fork`/`start_thread`）、`include/asm/processor.h`、`switch_to` 宏、`thread_info`、`kernel/fork` 的 arch 钩子、`exec` 相关；对比 `arch/riscv/kernel/process.c`（主）与 `arch/arm64/kernel/process.c`（参照）。重点：切栈/帧保存范围、`TIF_*` 工作位、`flush_thread`/`release_thread`、`arch_dup_task_struct`、`start_thread` 的 PC/SP 约定。

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

**基线**：linux 源树 HEAD `c5f411a3a`（7.2.10 ＋ dadao 补丁态；**只读**：未 `apply_series`/`reset`/`make`，源树 `git status` 为空）。dadao 行号取自该态；主对比 `arch/riscv`，参照 `arch/arm64`。017/024 已修的三处（同 cfx 的 cg5 单份、入口栈顶被保存序列覆盖、子任务从 trap 下一条进入）不复报。共 **19 条**（①3 ②7 ③3 ④6）。

### ① 缺失 hook（3 条）

- **A1 [P2] `flush_thread`/`release_thread` 空实现**：`arch/dadao/kernel/setup.c:449-451`、`arch/dadao/kernel/setup.c:453-455` ↔ `arch/riscv/kernel/process.c:184-207`（清 FPU/向量）、`arch/arm64/kernel/process.c:334-342`（`fpsimd_flush_thread`+`tls_thread_flush` 等 6 项）。因 FP 走异常帧（`arch/dadao/include/asm/processor.h:51-57`）、`start_thread` 整帧清零（`arch/dadao/kernel/setup.c:442`）、无向量 ⇒ **现在正确**；但 FPU/cache 落地后没有 hook 可接（空位陷阱）。`release_thread` 与 weak 默认等价（`kernel/exit.c:245`）。
- **A2 [P2] `arch_dup_task_struct`/`arch_release_task_struct` 走 weak 兜底**：`kernel/fork.c:899-903`（`*dst=*src`）、`kernel/fork.c:180`（空）↔ `arch/riscv/kernel/process.c:216-226`（先 `fstate_save(src,…)` 再整结构拷贝）、`arch/riscv/kernel/process.c:209-214`（释放向量上下文）。同 A1 前提；若 FP 改为 lazy/thread-owned，子任务会拿到父任务的脏 FP。
- **A3 [P2] ASLR 两个钩子缺**：`fs/exec.c:641`、`fs/binfmt_elf.c:193`（`arch_align_stack` 恒等默认）、`mm/util.c:390`（`arch_randomize_brk` weak）↔ `arch/riscv/kernel/process.c:109-114`（减随机量并对齐 16）。`arch/dadao/include/asm/elf.h:20-21` 自证无随机化 ⇒ 设计如此，仅登记缺口。

### ② 语义不符（7 条）

- **B1 [P1] `ret_from_fork` 把 `current` 当 `prev` 交给 `schedule_tail()`**：`arch/dadao/kernel/process.c:299` ↔ 契约 `kernel/sched/core.c:5442`（`@prev: the thread we just switched away from`）；riscv 由 asm 保留 `a0=prev` 后 `call schedule_tail`（`arch/riscv/kernel/entry.S:364`、`arch/riscv/kernel/entry.S:373`；参数约定见 `arch/riscv/kernel/entry.S:420-425`），arm64 同（`arch/arm64/kernel/entry.S:855`）。确定后果：真实 prev 的整段 `finish_task_switch` 记账丢失（`kernel/sched/core.c:5378-5381`、`kernel/sched/core.c:5432`）；`finish_task()` 是任务被切出后 `on_cpu=0` 的唯一清零点（另有 `sched_fork` 的初值 0：`kernel/sched/core.c:4890`），见 `kernel/sched/core.c:5114` ⇒ 漏清后 `try_to_wake_up()` 会走 `kernel/sched/core.c:4415` 的 `smp_cond_load_acquire(&p->on_cpu,!VAL)` 自旋（前置：`kernel/sched/core.c:4347` 的 `on_rq && ttwu_runnable` 会先短路，故需 `on_rq==0`，即「阻塞后立刻切到 fresh 任务」的时序）。**待真机复核**：024 的 `wait_for_completion` 现场通过，说明其路径未命中 stale `on_cpu`；`fork();wait();`（K6 shell，032/033）是判据，命中即升 P0。修法：`__switch_to` 把 prev 存 per-hart（与 `dadao_user_stack_top` 同点），ret_from_fork 调 `schedule_tail(prev)`。
- **B2 [P1] 用户返回无 TIF 工作处理**：`arch/dadao/kernel/syscalls.c:127-142`（`dadao_user_syscall_post` 只把 `-ERESTART*` 降为 `-EINTR`；注释自承 TIF 工作「hook 在这里」）、`arch/dadao/kernel/process.c:345`（ret_from_fork 直接 `dadao_enter_user`）↔ `arch/riscv/kernel/process.c:232`、`arch/riscv/kernel/process.c:237`（`syscall_exit_to_user_mode(regs)`）。`arch/dadao/include/asm/thread_info.h:83-90` 的 `_TIF_WORK_SYSCALL_ENTRY`/`_TIF_WORK_MASK`/`_TIF_SYSCALL_WORK` 全仓 **0 消费者**（grep）⇒ SIGPENDING/NEED_RESCHED/NOTIFY_* 置位后无人处理。与 039/042 交叉，本条只记进程返回路径。
- **B3 [P1] `dadao_user_stack_top` 用 per-hart 全局代替每任务栈顶**：`arch/dadao/kernel/process.c:269`（`__switch_to` 写）、`arch/dadao/kernel/process.c:496-497`（`dadao_enter_user` 再写）↔ `arch/riscv/include/asm/thread_info.h:56-63`（`kernel_sp`/`user_sp` 每任务，`arch/riscv/kernel/entry.S:268-269` 每次异常写）。单 hart 下写-读都在切换临界区，可用；嵌套 umon／抢占复用该全局时会读到他任务栈顶。
- **B4 [P2] `thread_struct.rf` 声明却不切，且无「内核不用 RF」的编译约束**：`arch/dadao/include/asm/processor.h:73`、`arch/dadao/kernel/entry.S:34-36`（明示不搬）↔ `arch/riscv/include/asm/switch_to.h:51-59`（`__switch_to_fpu` 存/取 dirty FP）。前提是 contract-abi §4.5 `allocatable.rf` 为空（`.tao/contracts/contract-abi.md:156`）；M4 放开 RF 后内核一旦分配 rf32-63 即跨任务串值 ⇒ 需 `-mgeneral-regs-only` 等价约束或切 RF。
- **B5 [P2] `start_thread` 整帧清零 vs 上游只设 PC/SP/status**：`arch/dadao/kernel/setup.c:440-447` ↔ `arch/riscv/kernel/process.c:144-182`；arm64 同形「Ensure all GPRs are zeroed」（`arch/arm64/include/asm/processor.h:305-315`）⇒ 与 arm64 一致、比 riscv 更严格，**非缺陷**；`status=0` 因本机无 status 寄存器/IE 位（`arch/dadao/include/asm/ptrace.h:44-47`）。
- **B6 [P2] `show_regs` 只打 `IP`/`STATUS`+rd/rb**：`arch/dadao/kernel/traps.c:583-596`（`:587` 为 `IP: … STATUS: …`）↔ `arch/riscv/kernel/process.c:67-101`（`__show_regs` 打 pc/ra/sp/gp/tp/…/status/cause）。缺 ra/rf 两组 bank 与 SP，崩溃现场信息不全。
- **B7 [P2] TIF 位号割裂且混入废弃位**：`arch/dadao/include/asm/thread_info.h:47-63` ↔ `include/asm-generic/thread_info_tif.h:10-50`（`SIGPENDING=1`/`NEED_RESCHED=4`/`RSEQ=11`；16–31 保留给 arch）。dadao 把 `SIGPENDING=0`…`SECCOMP=15` 放进通用区间，`TIF_NOHZ`（上游仅 sparc/mips/loongarch 残留）与 `TIF_SYSCALL_*`（现代内核改用 `SYSCALL_WORK_*`，`arch/dadao/include/asm/thread_info.h:19` 的 `syscall_work` 全仓 0 消费者）是死位 ⇒ 上游新增通用位即冲突。

### ③ 旁路 vs 通用（3 条）

- **C1 [P2] kernel_thread 手工断 mm**：`arch/dadao/kernel/process.c:186-196`（`args->kthread && p->mm` ⇒ `p->mm=NULL; mmput`）↔ 通用 `kernel/fork.c:1567-1602`（`CLONE_VM` ⇒ `mmget(oldmm); tsk->mm=mm`）与 `arch/riscv/kernel/process.c:255-263`（不动 mm）。上游假设 kthread 只在 `mm==NULL` 上下文创建；本机强行断开服务 020 的 kthread 自检，将来若有 `kernel_thread()` 需共享用户 mm 会静默失效。
- **C2 [P2] 自造用户入口/返回通道**：`arch/dadao/kernel/process.c:352-511`（`dadao_user_entry_install`/`dadao_enter_user`/cfx_umon 行）↔ `arch/riscv/kernel/entry.S:363-377`（`ret_from_fork_* → ret_from_exception`）+ `arch/riscv/kernel/process.c:228-238`。DADAO 无 `ret` 回帧的形状使然，但 TIF/信号/调度工作因此没有通用挂点（同 B2）；与 042 交叉，不复述 trap 细节。
- **C3 [P2] 子任务 IP 前移放在 ret_from_fork**：`arch/dadao/kernel/process.c:342`（`regs->ip += DADAO_INSN_BYTES`）↔ `arch/riscv/kernel/traps.c:330`（`regs->epc += 4`，在 syscall 分发前）。语义等价；024 已按「子任务从 trap 下一条进入」修好，此处只记位置差异（父任务靠 cg5 escape，子任务靠本行）。

### ④ Kconfig 缺口（6 条）

- **D1 [P1] 缺 `select THREAD_INFO_IN_TASK`**：`arch/dadao/Kconfig:11-22`（7 个 select，无此项）↔ `arch/riscv/Kconfig:227`。后果：`current` 取自 SP 掩码 + 栈底 `thread_info`（`arch/dadao/include/asm/current.h:11-16`、`arch/dadao/include/asm/thread_info.h:41-45`），无 vmap 栈/溢出检测。
- **D2 [P2] 栈尺寸本身优于 riscv，缺的是加固选型（无 `VMAP_STACK`/guard）**：`arch/dadao/include/asm/thread_info.h:9-11`（`THREAD_SIZE_ORDER 0`）＋`arch/dadao/configs/defconfig:7`（`CONFIG_PAGE_SIZE_64KB=y`）＋`arch/Kconfig:1376-1382`（`PAGE_SHIFT default 16 if PAGE_SIZE_64KB`）＋`arch/dadao/include/asm/pgtable.h:15-17`（`#if PAGE_SHIFT != 16 #error`）⇒ `THREAD_SIZE = 64 KiB << 0 = 64 KiB`；对照 riscv `arch/riscv/Kconfig:190`（`HAVE_PAGE_SIZE_4KB`）＋`arch/riscv/Kconfig:910-914`（`default 2`）⇒ 16 KiB，dadao 反为其 **4 倍**。真实缺口 = 无 `select HAVE_ARCH_VMAP_STACK`（`arch/riscv/Kconfig:153`；`grep VMAP_STACK arch/dadao/` = 0）⇒ 无 guard 页/栈溢出陷获，亦无 `arch/riscv/include/asm/thread_info.h:24-33` 的 2×THREAD_SIZE 对齐廉价检测。
- **D3 [P2] 缺 `select HAVE_RSEQ`**：`arch/dadao/include/asm/thread_info.h:55`（`TIF_RSEQ` 死位）↔ `arch/riscv/Kconfig:199`；`CONFIG_RSEQ` 依赖 `HAVE_RSEQ`（`init/Kconfig:1988-1992`），`rseq` 落到 `COND_SYSCALL` 的 `-ENOSYS`（`kernel/sys_ni.c:392`）。
- **D4 [P2] 缺懒抢占选型**：`arch/dadao/Kconfig:11-22`（无 `ARCH_HAS_PREEMPT_LAZY`）、`arch/dadao/include/asm/thread_info.h:47-63`（无 `HAVE_TIF_NEED_RESCHED_LAZY`）↔ `arch/riscv/Kconfig:45` + `arch/riscv/include/asm/thread_info.h:117`。
- **D5 [P2] 缺 `ARCH_HAS_CURRENT_STACK_POINTER`/`GENERIC_SMP_IDLE_THREAD`/`HAVE_STACKPROTECTOR`**：`arch/dadao/Kconfig:11-22` ↔ `arch/riscv/Kconfig:28`、`arch/riscv/Kconfig:126`、`arch/riscv/Kconfig:203`；栈保护由 `arch/dadao/Makefile:17-20` 显式 `-fno-stack-protector` 关掉（m14-llvm-002 未落地）。
- **D6 [P2] 缺 membarrier/KVM/FPU 选型**：`arch/dadao/Kconfig:11-22` ↔ `arch/riscv/Kconfig:39`（`ARCH_HAS_KERNEL_FPU_SUPPORT`）、`arch/riscv/Kconfig:40-41`（`ARCH_HAS_MEMBARRIER_*`）、`arch/riscv/Kconfig:1391`（`source arch/riscv/kvm/Kconfig`）。无 per-task FPU/KVM 状态 ⇒ 切换宏无需对应钩子（与 A1/B4 同一前提）。

### 覆盖与口径（现场派生）

- **钩子全集 9**：在 `kernel/fork.c`、`kernel/exit.c`、`fs/exec.c`、`fs/binfmt_elf.c`、`mm/util.c` 上 grep `arch_dup_task_struct|arch_release_task_struct|arch_task_cache_init|arch_thread_struct_whitelist|arch_setup_new_exec|arch_align_stack|arch_randomize_brk|release_thread|flush_thread`，去重 **9 项**。现场统计：dadao 定义 **2**（`flush_thread`/`release_thread`）、riscv **6**、arm64 **6**。判入 A1–A3、B5；其余 3 项（`arch_task_cache_init`/`arch_thread_struct_whitelist`/`arch_setup_new_exec`）与 riscv 同为 weak/默认（无 per-task arch 状态），不单列。
- **riscv `kernel/process.c` 顶层函数 18**：本任务相关 **12**（`arch_cpu_idle`/`__show_regs`/`show_regs`/`arch_align_stack`/`start_thread`/`flush_thread`/`arch_release_task_struct`/`arch_dup_task_struct`/`ret_from_fork_kernel`/`ret_from_fork_user`/`copy_thread`/`arch_task_cache_init`），排除 6（`set/get_unalign_ctl`、`compat_*` 2、`try_to_set_pmm`、`tagged_addr_init`）。
- **`switch_to` 宏动作 6 vs 1**：riscv 依次 `__set_prev_cpu`/`__switch_to_fpu`/`__switch_to_vector`/`switch_to_should_flush_icache`/`__switch_to_envcfg`/`__switch_to`（`arch/riscv/include/asm/switch_to.h:113-126`）；dadao 仅 `__switch_to` 1 步（`arch/dadao/include/asm/switch_to.h:36-39`）。差 5 步均有「无机上状态」理由（无 FPU/向量/cache/envcfg/prev_cpu）。
- **`thread_struct` 字段 13 vs 8**：riscv `arch/riscv/include/asm/processor.h:106-126`，dadao `arch/dadao/include/asm/processor.h:66-75`；差集 = FP/向量/envcfg/sum/align_ctl/SMP。
- **栈尺寸 64 KiB vs 16 KiB（按页大小现场乘，不按 order 数字猜）**：`arch/dadao/configs/defconfig:7`（`CONFIG_PAGE_SIZE_64KB=y`）→ `arch/Kconfig:1376-1382`（`PAGE_SHIFT=16`）→ `arch/dadao/include/asm/thread_info.h:9-11`（order 0）⇒ 64 KiB；riscv `arch/riscv/Kconfig:190`（4 KiB 页）+ `arch/riscv/Kconfig:910-914`（order 2）⇒ 16 KiB。由 `run.sh` 的 `stack.*` 6 项现场乘算。
- **TIF 名 17 vs 通用头 10（另有 3 个条件位）**：按 `grep -c '^#define TIF_'` 现场统计；riscv 走通用头并声明 2 个 `HAVE_TIF_*`（`arch/riscv/include/asm/thread_info.h:117-120`）。
- **riscv 进程/线程相关 `select` 15**：`grep -oE 'select [A-Z0-9_]+' arch/riscv/Kconfig` 按 `THREAD|STACKPROTECTOR|PREEMPT_LAZY|CURRENT_STACK_POINTER|RSEQ|MEMBARRIER|KVM|FPU|VECTOR|SHADOW|USER_CFI|ARCH_HAS_SYSCALL` 过滤（riscv 全部 select **272**、dadao **7**）。入结论 6 条（D1–D6）。
- **结论条目**：**19**（①3 ②7 ③3 ④6），全部带两侧 `文件:行号`；行号真实性与 7 条抽查由运行期证据目录内的 `run.sh` 现场校验。

### 抽查（两侧 `sed -n '<行>p'` 原文）

- `arch/dadao/kernel/process.c:299` = `schedule_tail(current);` ↔ `kernel/sched/core.c:5444` = `asmlinkage __visible void schedule_tail(struct task_struct *prev)`；`arch/riscv/kernel/entry.S:364` = `call schedule_tail`。
- `arch/dadao/kernel/syscalls.c:142` = `return DADAO_TRAP_RESUME_SKIP;`（127-143 全文无 TIF 处理）↔ `arch/riscv/kernel/process.c:237` = `syscall_exit_to_user_mode(regs);`。
- `arch/dadao/include/asm/thread_info.h:9` = `#define THREAD_SIZE_ORDER	0` ↔ `arch/riscv/Kconfig:914` = `default 2`（`THREAD_SIZE_ORDER`）。
- `arch/dadao/kernel/process.c:269` = `dadao_user_stack_top = (unsigned long)task_stack_page(next) + THREAD_SIZE;` ↔ `arch/riscv/include/asm/thread_info.h:61` = `long			kernel_sp;	/* Kernel stack pointer */`。
- `arch/dadao/kernel/setup.c:449` = `void flush_thread(void)`（空体）↔ `arch/riscv/kernel/process.c:186` = `#ifdef CONFIG_FPU`（其下 `fstate_off`/`memset(fstate)` 为实作）。
- `arch/dadao/include/asm/thread_info.h:55` = `#define TIF_RSEQ		8` ↔ `arch/riscv/Kconfig:199` = `	select HAVE_RSEQ`。
- `arch/dadao/include/asm/processor.h:73` = `unsigned long rf[32];		/* rf32-rf63 (frame-owned, not switched) */` ↔ `arch/riscv/include/asm/switch_to.h:57` = `fstate_save(prev, regs);`。

## 完成区

**测试结果**：通过 60/60（运行期证据目录内 `run.sh`，退出码 0；含第 7 节「注入→FAIL→回绿」自检）；失败项：无。

**修改文件**：`.tao/tasks/linux/m14-linux-041-进程线程与上下文切换.md`（仅此一件；未改任何代码、未动 Linux 源树、不占写者锁、未重建、未跑仿真）。

**验收结果**：
- 结论 **19 条**（①3 ②7 ③3 ④6），每条带两侧 `文件:行号` + 影响面 + 优先级（P0 0 条、P1 4 条、P2 15 条；B1 命中真机 `fork();wait();` 即升 P0）。
- 覆盖现场派生（源树 HEAD `c5f411a3a`）：通用钩子 **9**／dadao 2／riscv 6／arm64 6；riscv `process.c` 顶层 18（相关 12）；`switch_to` 6 vs 1 步；`thread_struct` 13 vs 8 字段；TIF 17 vs 通用 10（+3 条件）；riscv select 272／dadao 7（进程类 15）；栈 **64 KiB** vs 16 KiB（`defconfig`+`arch/Kconfig` 现场乘）。
- 行号真实性：结论与抽查中 **93** 个唯一 `路径:行号` 全部可解析（文件存在＋行号在范围内＋该行非空），`refs.check` = `resolved=93 bad=0`。
- 7 条抽查（两侧 `sed -n '<行>p'` 原文）已在「抽查」段贴出，`run.sh` 的 `spot.*` **左右两侧各验原文 + 任务书回贴**（28 项全绿）。
- 改动集：`scope.head_no_code` = 0（HEAD 文件集无 `.tao/` 之外的文件）、`scope.head_has_taskfile` = 1、`scope.worktree` = `taskfile-only`（工作树仅本任务书）；**不用裸 `git diff`/`git status` 计数**。
- 注入自检：临时副本把 `arch/dadao/kernel/process.c:299` 改为 `:9299` ⇒ `refs` 检查 FAIL（`OUT-OF-RANGE`）且 `inject.refs_red=1`；真实任务书零写操作（临时树注入）。
- 门控：`make check-knowledge-refs` ⇒ `结果: PASS`、rc=0（0 悬空）；`make check-tasks` ⇒ rc=0（报告型：漏收尾 1＝本任务在跑）。

**新发现/坑**：
- **`schedule_tail(prev)` 的 `prev` 是 fresh 任务拿不到的**：DADAO 的 `__switch_to_asm` 清掉 `rb16` 后直接 `jump`，新任务天然没有 prev；要按上游契约修，必须先由 C 半（`__switch_to`）把 prev 存到 per-hart 位置（`dadao_user_stack_top` 已是同型先例）。
- **栈尺寸别按 order 数字猜**：本机 64 KiB 页使 `THREAD_SIZE_ORDER 0` = **64 KiB**（riscv 4 KiB 页 × order 2 = 16 KiB，本机反大 4 倍）；真风险是**无 `VMAP_STACK` guard** 与 `current` 靠 SP 掩码，不是栈小。凡 `THREAD_SIZE` 一律按 `PAGE_SIZE << ORDER` 从 `defconfig`+`arch/Kconfig` 现场乘。
- **用户返回路径是 TIF 工作的空挂点**：`_TIF_WORK_MASK` 等宏齐全但零消费者，任何「置位后再处理」的上游机制（信号、懒抢占、rseq、uprobe）在这里都静默丢失。
- **`thread_struct.rf` 是"声明即契约"的陷阱**：字段名与注释看起来像已保存的上下文，实际既不切也不由编译约束保证不用；核对上下文切换必须看 `entry.S` 的搬运清单，不能看字段表。

**返工 1（D2 栈尺寸写死，reviewer 第 1 轮唯一阻断）**：错在按 RISC-V/x86 经验默认 4 KiB 页，把 `THREAD_SIZE_ORDER 0` 读成「4 KiB 栈」。现场派生：`arch/dadao/configs/defconfig:7`（`CONFIG_PAGE_SIZE_64KB=y`）→ `arch/Kconfig:1376-1382`（`PAGE_SHIFT = 16`）→ `arch/dadao/include/asm/pgtable.h:15-17`（非 16 即 `#error`）→ `THREAD_SIZE = 64 KiB << 0 = 64 KiB`；riscv `arch/riscv/Kconfig:190`（4 KiB 页）+ `arch/riscv/Kconfig:914`（`default 2`）= 16 KiB ⇒ dadao 为其 **4 倍**。**重定级 D2 = P2**：真实缺口只剩「无 `HAVE_ARCH_VMAP_STACK` guard（`grep VMAP_STACK arch/dadao/` = 0，riscv `arch/riscv/Kconfig:153`）+ 无 2×THREAD_SIZE 廉价溢出检测」；「4 KiB 溢出」「K6 exec 首个压力点」表述已删除。同步：D2 正文、新发现、覆盖段、P1 5→4／P2 14→15。自证：`sed -n '7p' arch/dadao/configs/defconfig`、`sed -n '1376,1382p' arch/Kconfig`、`sed -n '9,11p' arch/dadao/include/asm/thread_info.h`；`run.sh` 新增 `stack.*` 6 项现场乘算（64/16/4/guard/defconfig/vmap_gap）。

**遗留问题**：返工 1 的阻断项（D2 栈尺寸）✅已修，复验见「返工 1」段与 `run.sh` 的 `stack.*`；reviewer 两项非阻断（`spot()` 右侧断言、B6 `IP`/`STATUS`）✅已修。19 条的整改去向（立即修／立任务／暂不修）由用户裁定；B1 建议在 K6 shell（032/033）派单前用真机 `fork();wait();` 复现一次以确认是否升 P0。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| B1 只写"传错"未给可判定后果 | ✅已修 | 补 `finish_task_switch` 记账行号与 `on_cpu` 唯一写入点，并标注 024 现场通过的反证与真机判据 | `sed -n '5114p;5378,5381p;4415p' kernel/sched/core.c` 原文核对 |
| A1 把 `flush_thread` 空实现写成缺陷 | ✅已修 | 改为「当前正确、FPU/cache 落地后的空位」，并给 FP 帧内与 `start_thread` 清零依据 | `arch/dadao/include/asm/processor.h:51-57`、`arch/dadao/kernel/setup.c:442` 原文 |
| B4 未给"内核不用 RF"的契约依据 | ✅已修 | 补 `.tao/contracts/contract-abi.md:156`（`allocatable.rf` 为空）并注明 M4 后升 P1 | 契约原文 `sed -n '156p'` |
| D3 "rseq 不在表"表述不准 | ✅已修 | 改为 `CONFIG_RSEQ` 依赖 `HAVE_RSEQ`、`COND_SYSCALL` 兜底 `-ENOSYS` | `init/Kconfig:1988-1992`、`kernel/sys_ni.c:392` |
| B5 未说明 `status=0` 是否缺陷 | ✅已修 | 补「本机无 status 寄存器/IE 位」依据，判非缺陷 | `arch/dadao/include/asm/ptrace.h:44-47` |
| 覆盖段"riscv 相关函数"口径未写排除项 | ✅已修 | 列 12 相关 + 6 排除，均可现场复算 | `grep -nE` 于 riscv `process.c` |
| 抽查原计划 5 条 | ✅已修 | 加到 7 条，含每条 P1 | `run.sh` 逐条比对 |
| 覆盖段称 9 个通用钩子却只映射 6 个 | ✅已修 | 补「其余 3 项（`arch_task_cache_init`/`arch_thread_struct_whitelist`/`arch_setup_new_exec`）与 riscv 同为 weak/默认」 | 9−6=3 逐名核对 |
| B1「`finish_task()` 是 `on_cpu=0` 唯一写入」不准确 | ✅已修 | 限定为「切出后的唯一清零点」，并补 `sched_fork` 初值 0（`kernel/sched/core.c:4890`） | `grep -n "on_cpu" kernel/sched/core.c` 全量核对 |
| B4 引用 `arch/dadao/kernel/entry.S:33-36` 多含一行上下文 | ✅已修 | 收窄为 `arch/dadao/kernel/entry.S:34-36` | `sed -n '33,38p'` 原文 |

判决：全部 finding 已修，无未修项 ⇒ 状态置 `待验收`。

### 第 2 轮 engineer 自审（返工 1）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| D2 把 `THREAD_SIZE_ORDER 0` 写死成 4 KiB 栈（16× 偏差） | ✅已修 | 改为 64 KiB 事实（defconfig→`PAGE_SHIFT=16`→pgtable 强制→`64 KiB<<0`），重定级 P1→P2，删除「4 KiB 溢出／首个压力点」 | `stack.dadao_kib=64`、`stack.riscv_kib=16`、`stack.dadao_vs_riscv=4` |
| `spot()` 只断言左侧、右侧仅打印 | ✅已修 | 加右侧原文断言 + 右侧任务书回贴；7 条 ×4 检查 | `spot.*` 28 项全绿（总计 60/60） |
| B6 漏写还打 `IP`/`STATUS` | ✅已修 | 标题与正文补 `IP`/`STATUS`（`arch/dadao/kernel/traps.c:587`） | `sed -n '587p' arch/dadao/kernel/traps.c` |
| 全文写死常量复扫 | ✅已修 | 栈尺寸全部改为现场派生；`NR_CPUS` 无断言；reviewer 记录原文保留不改 | `grep -n "4 KiB\|16 KiB\|PAGE_SIZE\|NR_CPUS"`：仅 reviewer 记录命中 |
| 完成区数字未随重定级更新 | ✅已修 | P1 5→4、P2 14→15；测试 40→60、refs 88→93 | 重跑 `run.sh` |

判决：全部 finding 已修 ⇒ 状态保持 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-20）

**重跑（命令均在任务 worktree 根执行，源树 `c5f411a3a` 只读）**
- 运行期证据目录内的 `run.sh`（`LINUX_SRC` 指向只读源树）⇒ `RESULT: PASS (0 failures) / OK=40 FAIL=0`，rc=0；连跑 2 次同结果，与完成区「40/40、退出码 0」一致。
- **独立注入（非自检替代）**：`cp` 备份任务书（md5 `7f32d1a5…`）→ 把 `arch/dadao/kernel/process.c:299` 改为 `:9299` → 重跑同一脚本 ⇒ **rc=1**、`refs.all_resolved FAIL`、`BAD arch/dadao/kernel/process.c:9299 (OUT-OF-RANGE 685)`、`RESULT: FAIL (3 failures)`；`cp` 回写后 md5 相等、`git status --porcelain -uall` 空，重跑 ⇒ rc=0 回绿。
- 门控：`make check-knowledge-refs` ⇒ `结果: PASS`、**rc=0**（悬空 0）；`make check-tasks` ⇒ **rc=0**（① 漏收尾 1＝本任务在跑、② 已立未开工 18，报告型）。

**行号抽查（两侧原文，P1 5 条全查 + P2 抽 10 条，`sed -n`/`awk NR==` 现贴）**
- **B1 属实**：`arch/dadao/kernel/process.c:299`=`schedule_tail(current);`；`kernel/sched/core.c:5442`=`@prev: the thread we just switched away from.`、`5444` 定义、`5456` `finish_task_switch(prev)`；riscv `entry.S:364`/`373`=`call schedule_tail`、`420-425`「a0: previous task_struct … passed to schedule_tail」；arm64 `entry.S:855`=`bl schedule_tail`。
- B2 `syscalls.c:142`/`process.c:345`/riscv `process.c:237`、`thread_info.h:83-90` 三宏 **grep 仅定义无消费者**；B3 `process.c:269`、`496-497`、riscv `thread_info.h:61-63`、`entry.S:268-269`；D1 `dadao/Kconfig:11-22` **恰 7 个 select** 且 `grep THREAD_INFO_IN_TASK arch/dadao`=0、riscv `Kconfig:227`、`current.h:11-16`、`thread_info.h:41-45`；D2 `thread_info.h:9-11`、riscv `Kconfig:914`、`thread_info.h:24-33`。
- P2 抽 10 条全对：A1（`setup.c:449-455` 空体、riscv `process.c:184-207`、arm64 `process.c:334-342`、`exit.c:245` weak）、A2（`fork.c:899-903`/`180`、riscv `process.c:216-226`/`209-214`）、A3（`exec.c:641`、`binfmt_elf.c:193`、`mm/util.c:390`、riscv `process.c:109-114`、`elf.h:20-21`）、B4（`processor.h:73`、`entry.S:34-36`、riscv `switch_to.h:51-59`、`contract-abi.md:156`）、B5/B6（`setup.c:440-447`、arm64 `processor.h:305-315`、`traps.c:583-596`）、B7（`thread_info_tif.h:7-48`）、C1（`process.c:186-196`、`fork.c:1567-1602`）、C3（`process.c:342`、riscv `traps.c:330`）、D3–D6（`init/Kconfig:1991`、`sys_ni.c:392`、riscv `Kconfig:28/39-41/45/126/199/203/1391`、`dadao/Makefile:17-20`）⇒ **无行号编造**。
- **B1 链条分层**：确定事实 = 传错 prev（上行）+ 记账落到 fresh 任务（`core.c:5378-5381`、`5432`）+ 切出后 `on_cpu` 唯一清零点为 `finish_task`（`5114`；grep 全 sched 仅 `4890/5098/5114/8357` 四处写）+ `ttwu` `4415` 自旋；**推断** = 自旋还需 `p->on_rq==0`（`core.c:4347` 先短路）与「阻塞后立刻切到 fresh 任务」的时序，现场未复现 —— 与任务自述「机制确定、待真机复核」一致，**不阻断**（建议补一句 4347 前置条件）。

**阻断项（唯一）**：D2 与新发现把 `THREAD_SIZE_ORDER 0` 写死为「**4 KiB 内核栈**」并据此判 P1（「exec/深 VFS 在 4 KiB 栈溢出风险」「4 KiB 栈是 K6 exec 首个压力点」）—— **实测 64 KiB**：构建配置 `CONFIG_PAGE_SHIFT 16`（dadao `defconfig` `CONFIG_PAGE_SIZE_64KB=y`），`arch/dadao/include/asm/pgtable.h:15-16` 强制 `PAGE_SHIFT==16` 否则 `#error`，`THREAD_SIZE=PAGE_SIZE<<0=64 KiB`；riscv `default 2` + 4 KiB 页 = 16 KiB，dadao 栈反为其 **4 倍** ⇒ 影响面与 P1 定级不成立（属「写死值 vs 现场值」）。**改法**：D2 改为 64 KiB 事实，影响面改为「无 `VMAP_STACK`/guard（`grep VMAP_STACK arch/dadao`=0，riscv `Kconfig:153`）、无 2×THREAD_SIZE 廉价溢出检测」，重定级（建议 P2，或改理由保 P1），同步改新发现与完成区；顺手两处非阻断：`run.sh` 的 `spot()` 目前**只断言左侧**原文（右侧仅打印），补右侧断言；B6「只打 rd/rb」补注还打 `IP/STATUS`（`traps.c:587`）。

**约束核验**：只读盘点、不改代码 —— `git show --name-only HEAD` 仅本任务书 1 文件、`git status --porcelain -uall` 空、源树 `c5f411a3a` `status` 0 行；017/024 已修三处（cg5 单份、入口栈顶被覆盖、子任务 IP 前移）在基线与 C3 标注「已修/语义等价/不复报」，**未**写成缺陷（B3 是对修复引入的 per-hart 全局的独立新问题，非复报）；032/033 仍在「待开始」表 ⇒ **派单前真机 `fork();wait();` 复核 B1 可行**（017 已有 `k4_fork_probe` 载体、<5 min 冒烟，不必等 K6，建议由主会话排）。

**判决：Needs Revision** —— 仅 D2 栈尺寸事实错误（16× 偏差）阻断；其余 18 条、覆盖计数、改动集、门控与证据脚本在我自己的重跑下全绿。

### 第 2 轮 reviewer 验收（2026-11-20，只核 D2 修复 + 四项顺手改）

**重跑**：运行期证据目录内的 `run.sh` ⇒ `RESULT: PASS (0 failures) / OK=60 FAIL=0`、**rc=0**（连跑 2 次），`refs.check resolved=93 bad=0`、`scope.*` 三项 OK。门控：`make check-knowledge-refs` ⇒ PASS、**rc=0**（悬空 0）；`make check-tasks` ⇒ **rc=0**（① 漏收尾 1＝本任务在跑、② 已立未开工 18，报告型）。

**D2 现场派生链（逐条 `sed -n`/`awk` 原文）**：`arch/dadao/configs/defconfig:7`=`CONFIG_PAGE_SIZE_64KB=y`；`arch/Kconfig:1376-1382`=`config PAGE_SHIFT`…`default 16 if PAGE_SIZE_64KB`（1378 为 `default 12 if PAGE_SIZE_4KB`）；`arch/dadao/include/asm/pgtable.h:15-17`=`#if PAGE_SHIFT != 16`／`#error …64 KiB pages…`／`#endif`；`thread_info.h:9-11`=`THREAD_SIZE_ORDER 0`／`(PAGE_SIZE << THREAD_SIZE_ORDER)`／`THREAD_SHIFT PAGE_SHIFT`；对照 riscv `Kconfig:190`=`select HAVE_PAGE_SIZE_4KB`、`:914`=`default 2`、`:153`=`select HAVE_ARCH_VMAP_STACK if MMU && 64BIT` ⇒ **64 KiB vs 16 KiB（4 倍）成立**；`run.sh` 的 `stack.defconfig_64kb/pgtable_guard/dadao_kib=64/riscv_kib=16/dadao_vs_riscv=4/vmap_gap=0` 六项全 OK（现场从 defconfig+Kconfig 乘算，非写死）。

**重定级与残留扫描**：结论段实测 `[P1]=4`、`[P2]=15`、条目 `19`（①3 ②7 ③3 ④6 未动）；D2 正文已改「栈尺寸本身优于 riscv，缺的是加固选型（无 `VMAP_STACK`/guard）」；`grep -n '首个压力点|4 KiB 内核栈|4 KiB 栈'` 仅命中「返工 1」记录、修复表与我第 1 轮审阅（历史留痕），**结论/新发现无残留错误表述**；`4 KiB`/`16 KiB` 其余命中均为 riscv 页大小（正确）；覆盖段除新增「栈 64 KiB vs 16 KiB」外数字未动（9／2／6／6、18、6 vs 1、13 vs 8、17 vs 10、272／7／15）。

**spot() 右侧断言 —— 独立注入 2 路（均 `cp` 备份 + md5 还原）**：
- 注入 A：改**任务书**抽查段右原文中间字符（`…task_struct *prevX`）⇒ **rc=1**、`spot.schedule_tail.right.paste FAIL`、`OK=59 FAIL=1`；还原 md5 `faeeb5dc…` 相等，重跑回绿 60/60 rc=0。
- 注入 B：改**证据脚本**某条 spot 的右侧期望（`select HAVE_RSEQ`→`HAVE_RSEQZ`）⇒ **rc=1**、`spot.tif_rseq.right FAIL expected=[…RSEQZ] actual=[…RSEQ]`、`spot.tif_rseq.right.paste FAIL`、`OK=58 FAIL=2`；还原 md5 `b323f0c2…` 相等。
- **观察（非阻断）**：回贴用 `grep -qF` 子串匹配 ⇒ ① 纯追加字符（`HAVE_RSEQX`）② 同文本在正文另有出处（D3 标题）都能让回贴蒙过；源侧 `spot.*.right` 断言本身可达 FAIL（注入 B 已证），建议回贴改整行相等。

**B1 前置 / B6 补注**：B1 已补 `kernel/sched/core.c:4347` 前置，`sed -n '4347p'` = `		if (READ_ONCE(p->on_rq) && ttwu_runnable(p, wake_flags))` 属实；B6 标题/正文已改「只打 `IP`/`STATUS`+rd/rb」并引 `:587`，`sed -n '587p'` = `pr_info("IP: %016lx STATUS: %016lx\n", regs->ip, regs->status);` 属实。

**改动集/只读**：本分支两笔提交（`a6ec31ef`、`c7638a61`）`git show --name-only` 均**仅本任务书** 1 文件；`git status --porcelain -uall` 空；源树 `c5f411a3a` `status` 0 行；我未提交 git（仅本轮追加本审阅记录）。

**判决：Accepted** —— D2 修复与四项顺手改在我自己的重跑、两路注入与逐条 `sed` 下全部成立；仅留 1 条非阻断观察（回贴子串弱性），交 architect 收尾时定夺。
