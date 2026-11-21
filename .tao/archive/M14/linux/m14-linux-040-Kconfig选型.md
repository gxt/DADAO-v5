# m14-linux-040: Kconfig/选型 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：1–2 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：已验证

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/Kconfig*`（含 `.debug`）与 `arch/riscv/Kconfig*`、`arch/arm64/Kconfig*` 的 `select`/`depends on` 集合差异；重点找「通用代码已具备、但因缺 `select` 没编进来」的项（`m14-linux-025` 的 `CLONE_BACKWARDS` 是样例）。

## 要做

逐个 hook / 机制判定属于哪一类，并给证据：

1. **缺失 hook**：上游有、我们没有（后果：功能不可用，或被迫走旁路）；
2. **语义不符**：有但行为不同（返回码 / 副作用 / 加锁 / 顺序）；
3. **旁路 vs 通用**：我们自造实现，上游走通用 `mm/`、`kernel/` 路径；
4. **Kconfig 缺口**：缺 `select` / `depends on`，导致本可复用的通用代码没编进来（`m14-linux-025` 的 `CLONE_BACKWARDS` 就是此类）。

**每条格式**：`arch/dadao/<file>:<line>` ↔ `arch/riscv/<file>:<line>`（必要时补 `arch/arm64`）/ 影响面 / 优先级（**P0** 阻塞当前在跑任务；**P1** 影响正确性；**P2** 仅形态差异）。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行），**每条带两侧 `文件:行号`**；
2. **覆盖现场派生**：列清「检查了哪些 hook / 机制」及条数（不写死），并说明如何枚举得到（命令或脚本口径）；
3. **抽查 5 条**：用 `sed -n '<行>p'` 贴出两侧原文，证明行号真实——**不许凭记忆**；
4. **不改任何代码**：`git status -uall` 只列本任务书；不占写者锁、不重建、不跑仿真。

## 盘点结论

**读取基线**：源码检出 HEAD `c5f411a3a`（`dadao: linux patch series`，基线 `7b20d05fd` Linux 7.2.10），工作树干净；未 `apply_series`/`reset`/`make`（该检出同时被 `m14-linux-035` 使用，本任务只读）。

**覆盖与口径（现场派生）**：枚举口径 = `grep -cE '^[[:space:]]*select[[:space:]]'` 与 `'^[[:space:]]*depends on[[:space:]]'`，对三个 arch 的 `Kconfig*` 全量统计；符号去重后按关键字分桶（脚本在运行期证据目录，`run.sh` 每次现场重算）。现场值：**dadao 7 select / 12 depends-on；riscv 311 / 130（5 个文件）；arm64 440 / 76（3 个文件）**，合计对比 **758 select / 218 depends-on**；riscv 独有 select 符号 **288** 个 → 平台/总线/固件 87、特性未实现 97、通用机制需评估 40、其它需评估 64（后两桶 104 个逐条过，本轮逐条判定并落到结论的共 30 条：①16 / ②5 / ③6 / ④3）。`depends on` 侧：dadao 12 条全部指向自造 `DADAO_*` 自检符号（`Kconfig.debug:55/76/92/105/115/124/133/276/292/327/350/375`），与 riscv 依赖图无交集 ⇒ 同名项差异不在 `depends on` 文本，而在同名 config 的定义/默认值（②组）。已对齐的两条既有样本：`CLONE_BACKWARDS`（dadao:22 ↔ riscv:96）、`ARCH_HAS_SYSCALL_WRAPPER`（dadao:17 ↔ riscv:54）。

### ① 缺失 hook（上游有、我们没有；后果 = 通用代码没编进来）

1. `HAVE_ARCH_TRACEHOOK` 缺 ↔ `arch/riscv/Kconfig:148`（arm64:173）：`PTRACE_GETREGSET/SETREGSET` 整段在 `#ifdef CONFIG_HAVE_ARCH_TRACEHOOK` 内（`kernel/ptrace.c:1356`），未定义时 `ret = -EIO`（`kernel/ptrace.c:1166`）；arch 也无 regset（`grep -rnE 'user_regset|regset_view' arch/dadao` = 0 命中，只有 `elf.h:39` 的类型别名）⇒ GDB 读寄存器不可用。**P1**。
2. `HAVE_ARCH_SECCOMP_FILTER` 缺 ↔ `arch/riscv/Kconfig:145`（arm64:171）：它 `select HAVE_ARCH_SECCOMP`（`arch/Kconfig:630`），`SECCOMP_FILTER` 依赖二者 + NET（`arch/Kconfig:666`）⇒ 两种 seccomp 模式均不可用；但 arch 侧 `syscall_get_arch()` **已实现**（`arch/dadao/include/asm/syscall.h:121`），只缺 `syscall_rollback()`（`grep -rn syscall_rollback arch/dadao` = 0 命中；`kernel/seccomp.c:1289/1364` 会调用它）⇒ 典型「hooks 半就绪、Kconfig 未接」。**P1**。
3. `HAVE_RSEQ` 缺 ↔ `arch/riscv/Kconfig:199`（arm64:225）：`CONFIG_RSEQ` `depends on HAVE_RSEQ`（`init/Kconfig:1988-1991`）⇒ `sys_rseq` 走 `sys_ni`（`kernel/sys_ni.c:392`）返回 ENOSYS。**P2**。
4. `ARCH_WANT_DEFAULT_TOPDOWN_MMAP_LAYOUT` + `HAVE_ARCH_MMAP_RND_BITS` 缺 ↔ `arch/riscv/Kconfig:83/142`（arm64:92/167）：前者还 `select ARCH_HAS_ELF_RANDOMIZE`（`arch/Kconfig:1394`）；缺它时 `arch_pick_mmap_layout()` 走兜底 `mmap_base = TASK_UNMAPPED_BASE`、清 `MMF_TOPDOWN`（`mm/util.c:480-484`）⇒ mmap 只向上长、不留 stack gap、无 ASLR。**P2**。
5. `HAVE_SYSCALL_TRACEPOINTS` / `SYSCTL_EXCEPTION_TRACE` 缺 ↔ `arch/riscv/Kconfig:204/226`（arm64 同）⇒ 无 `sys_enter/sys_exit` tracepoint、无 `exception-trace` sysctl。**P2**。
6. `ARCH_STACKWALK` + `STACKTRACE_SUPPORT` + `LOCKDEP_SUPPORT` + `TRACE_IRQFLAGS_SUPPORT` 缺 ↔ `arch/riscv/Kconfig:63/320/353/228`（arm64:52）：`LOCK_DEBUGGING_SUPPORT` 依赖后三者（`lib/Kconfig.debug:1444-1446`）⇒ PROVE_LOCKING / DEBUG_SPINLOCK 整族不可选，BUG/WARN 无栈回溯。**P1**（017/018/023/025 正在改调度/COW/futex 锁，缺 lockdep 无从证伪）。
7. `ARCH_HAS_DEBUG_VM_PGTABLE` / `ARCH_HAS_DEBUG_WX` / `ARCH_HAS_PTDUMP` 缺 ↔ `arch/riscv/Kconfig:30/31/47`（arm64:26/14）：`DEBUG_VM_PGTABLE` 依赖前者（`lib/Kconfig.debug:916-919`），`DEBUG_WX` 依赖后两者（`mm/Kconfig.debug:186-190`）。**P2**（与第 28 条同源）。
8. `HAVE_STACKPROTECTOR` / `ARCH_HAS_FORTIFY_SOURCE` 缺 ↔ `arch/riscv/Kconfig:203/34`（arm64:227）：`CONFIG_STACKPROTECTOR` 依赖前者（`arch/Kconfig:701-705`）⇒ 无 canary、无 FORTIFY。**P2**（加固）。
9. `ARCH_HAS_STRICT_KERNEL_RWX` / `ARCH_HAS_SET_MEMORY` 缺 ↔ `arch/riscv/Kconfig:51/50`：`STRICT_KERNEL_RWX` 依赖前者（`arch/Kconfig:1581-1584`），且 arch 无 `mark_rodata_ro`/`set_memory_*`（`grep -rnE 'mark_rodata_ro|set_memory_(ro|rw|nx)' arch/dadao` = 0 命中）⇒ text/rodata 不可 RO。**P2**。
10. `HAVE_ARCH_JUMP_LABEL(_RELATIVE)` 缺 ↔ `arch/riscv/Kconfig:134-135`（arm64:156-157）：`CONFIG_JUMP_LABEL` 依赖它（`arch/Kconfig:130-132`）⇒ static_branch 恒走 fallback（语义等价、性能损失）。**P2**。
11. `GENERIC_SCHED_CLOCK` 缺 ↔ `arch/riscv/Kconfig:125`（arm64:141）：`arch/dadao/include/asm/time.h:71` 已写明「属 K5、2026-11-17 裁定延期」⇒ sched_clock 只有 jiffies 精度。**P1**（已在 m14-linux-021 跟踪，此处确认影响面）。
12. `THREAD_INFO_IN_TASK` 缺 ↔ `arch/riscv/Kconfig:227`（arm64:253）：我们用栈内 `thread_info`（`arch/dadao/include/asm/thread_info.h:17-23`、`arch/dadao/include/asm/current.h:11-16`），TIF 位在栈底并自维护编号（`thread_info.h:47-63`），未 `select HAVE_GENERIC_TIF_BITS`（riscv:169）⇒ 栈溢出即破坏 TIF、通用 TIF 语义靠手工复刻。**P2**。
13. `HAVE_ARCH_AUDITSYSCALL` 缺 ↔ `arch/riscv/Kconfig:130`：`AUDITSYSCALL` 依赖它（`init/Kconfig:556-558`）⇒ audit 不可用。**P2**。
14. `ARCH_HAS_HW_PTE_YOUNG` 缺 ↔ `arch/riscv/Kconfig:37`（arm64:47）：我们 `pte_young/pte_mkyoung` 全软件位（`arch/dadao/include/asm/pgtable.h:141,170-176`），但测试机硬件做 A/D 回写 ⇒ 声明与硬件不符，`arch_has_hw_pte_young()` 恒 false（`include/linux/pgtable.h:609` 直接 `IS_ENABLED(CONFIG_ARCH_HAS_HW_PTE_YOUNG)`）、MGLRU 不可选（`mm/Kconfig:1435`）。**P2**。
15. `ARCH_HAS_PTE_SPECIAL` 缺 ↔ `arch/riscv/Kconfig:48`（arm64:46）⇒ 无 `pte_special`/VM_PFNMAP 语义（当前无设备、无 PFNMAP 用户）。**P2**。
16. 性能类合并：`ARCH_USE_CMPXCHG_LOCKREF`(riscv:77) / `ARCH_HAS_FAST_MULTIPLIER`(33) / `DCACHE_WORD_ACCESS`(riscv:1001) / `BUILDTIME_TABLE_SORT`(94) 缺 ⇒ 通用代码走慢路径（lockref 用自旋、hweight/字符串散列用标量、kallsyms 线性查找）。**P2**。

### ② 语义不符（同名 config 的定义/默认值不同）

17. `NR_CPUS`：`arch/dadao/Kconfig:51-54`（无 `depends`、`range 1 1`、default 1）↔ `arch/riscv/Kconfig:450-456`（`depends on SMP`、range 2..512、default 32/64/256）⇒ SMP=n 时 riscv 隐藏该项，我们仍暴露且夹到 1。**P2**。
18. `CMDLINE`：dadao:94-100 只有 string ↔ `arch/riscv/Kconfig:1207-1240`（+FALLBACK/EXTEND/FORCE）、`arch/arm64/Kconfig:2465-2495`（+FROM_BOOTLOADER/FORCE）⇒ 无 bootloader 命令行策略（boot info `cmdline_size = 0`）。**P2**。
19. `ARCH_FORCE_MAX_ORDER`：dadao:59-64 default 10 ↔ `arch/arm64/Kconfig:1726-1730`（64K 页 default 13）⇒ 64 KiB 页最大连续块 64 MiB vs 512 MiB。**P2**。
20. `UACCESS_MEMCPY`：dadao:15 无条件 ↔ `arch/riscv/Kconfig:229` 仅 `if !MMU`（arm64 不选）⇒ 我们 uaccess 走通用 memcpy 路径，两参照 arch 用各自 asm copy（形态/性能差异，语义由 generic 保证）。**P2**。
21. 固定形态三项：`MMU`(dadao:34-35) / `64BIT`(28-29) / `CPU_BIG_ENDIAN`(31-32) 全 `def_bool y` ↔ `arch/riscv/Kconfig:292-297`、`7-8`（由 `ARCH_RV64I` 选，riscv:411-415）、`arch/arm64/Kconfig:1583-1585`（BE `depends on BROKEN`）⇒ 我们不提供裁剪形态（符合 spec：BE / 64 KiB / MMU 固定）。**P2**。另 `PAGE_OFFSET/PHYS_OFFSET/ARCH_DMA_MINALIGN` 用 Kconfig hex/int（dadao:66-78）↔ riscv 运行期 `kernel_map.page_offset`（`arch/riscv/include/asm/page.h:32-37`）、arm64 头文件 128（`arch/arm64/include/asm/cache.h:35`）：固定 2 TiB 窗口/PA 0，副作用是 KASLR 不可能。**P2**。

### ③ 旁路 vs 通用（我们自造、上游走 `kernel/`/`mm/` 通用路径）

22. **syscall 入口**：`dadao_user_excp_dispatch()`（`arch/dadao/kernel/process.c:516`）直接调 `dadao_user_syscall()`+`dadao_call_syscall()`（同文件 662-666）↔ `syscall_enter_from_user_mode()`（`arch/riscv/kernel/traps.c:336`）+ `GENERIC_ENTRY`（riscv:112 → `kernel/entry/{common,syscall-common}.c`）⇒ `SYSCALL_WORK_*`（seccomp / ptrace / audit / tracepoint / rseq slice）永不执行；`thread_info.syscall_work`（`asm/thread_info.h:19`）在 `arch/dadao` 内**除播种清零**（`kernel/process.c:447` `ti->syscall_work = 0;`）**外无任何 test/set**；通用读点（`include/linux/entry-common.h:101/147/264`）因入口旁路而不可达。**P1**。
23. **异常/中断入口**：`dadao_async_excp`（`arch/dadao/kernel/async_trap.S:38`）+ C half ↔ `irqentry_enter/exit_*`（`arch/riscv/kernel/traps.c:150-158/176-192/219-236`）；`grep -rnE 'irqentry_(enter|exit)|irq_enter|irq_exit|rcu_irq' arch/dadao` = 0 命中 ⇒ 中断态无 RCU / trace / preempt 记账（SMP=n 掩盖），接 lockdep/RCU 前必须补。**P1**。
24. **tick**：`jiffies_64 += 1`（`arch/dadao/kernel/time.c:238`）+ `sched_tick()`（time.c:260）↔ 通用 `tick_periodic()/update_process_times()`；arch 内无 `raise_softirq`/`TIMER_SOFTIRQ` ⇒ 定时器/hrtimer 不推进、无 user/system 记账，`schedule_timeout` 类睡眠靠调用方不阻塞（futex/clone 探针注释已注明）。**P1**（任务书登记为 m14-linux-021 延期，此处确认影响面）。
25. **内存模型**：FLATMEM（默认，`mm/Kconfig:429-431`）↔ riscv `ARCH_SPARSEMEM_ENABLE`(308-312)+`ARCH_SELECT_MEMORY_MODEL`(314-315) ⇒ 无 sparsemem/hotplug；PA RAM 连续在 [0,2 GiB)（spec/Kaiwu §1.1），当前成立。**P2**。
26. **TLB gather**：`MMU_GATHER_NO_RANGE`(dadao:14) ↔ riscv `MMU_GATHER_RCU_TABLE_FREE if SMP && MMU`(210) ⇒ 逐页 flush、无 table-free 延迟（SMP=n 下等价）。**P2**。
27. **IRQ 分发**：arch 自管两条 mask 轴（`arch/dadao/kernel/irq.c`），无 `GENERIC_IRQ_MULTI_HANDLER`(riscv:119)/`IRQ_DOMAIN`(206)/`SPARSE_IRQ`(225)；`grep -rnE 'request_irq|irq_domain|irq_desc|irq_set_chip' arch/dadao` = 0 命中 ⇒ 无 irq_desc/irqchip 框架，接外设中断需补。**P2**。

### ④ Kconfig 缺口 / 卫生

28. `Kconfig.debug`（393 行）与上游 debug 选项无对应：`DADAO_K3_PT_SELFTEST`(`Kconfig.debug:141`) 想覆盖的正是 `DEBUG_VM_PGTABLE`（`lib/Kconfig.debug:916`，因缺 `ARCH_HAS_DEBUG_VM_PGTABLE` 不可用）；`DADAO_K3_PF_SELFTEST`(187) ↔ 通用 `DEBUG_VM`（可用但未接）；`DADAO_K4/K5_*` ↔ `DEBUG_ATOMIC_SLEEP`/`PROVE_LOCKING`（后者不可用，见 ①-6）。建议：先把上游 debug 选项打通，`Kconfig.debug` 只留无上游等价物的 boot 边界探针。**P2**。
29. `NO_IOPORT_MAP`（dadao:37）：C/汇编侧**无消费者**（`grep -rn CONFIG_NO_IOPORT_MAP .` = 0 命中），但**裸符号在 Kconfig 侧被读取**，不能当死配置：`lib/Kconfig:385`（`HAS_IOPORT_MAP depends on HAS_IOMEM && !NO_IOPORT_MAP`）、`drivers/net/ethernet/realtek/Kconfig:47`、`arch/mips/Kconfig:54`；`HAS_IOMEM` 是 `default y`（`lib/Kconfig:375-378`）⇒ 删掉 dadao 的定义会让 `!NO_IOPORT_MAP` 由 false 变 true，`HAS_IOPORT_MAP`（`lib/Kconfig:383-386`，`default y`）由 n 翻 y，`grep -rnE 'depends on.*HAS_IOPORT_MAP' --include=Kconfig* . | wc -l` = 13 个此类项（`FW_CFG_SYSFS`、`104_QUAD_8`、`VORTEX`、`TCG_ATMEL`、`GPIO_TQMX86`、`SND_SC6000` 等，完整 13 项见证据脚本）从此可选。当前 defconfig（PCI/ISA/驱动全关，且这些项多数还要求 X86/ARM/COMPILE_TEST）**预计不引出新编译单元**，但确切结论**需实测**（可写副本删定义后比对新符号；本任务只读不跑）。**结论：删前须先评估，不是「可删」**；新架构的正门是 `HAS_IOPORT`（riscv:128）。**P2**。
30. 卫生两项：`select 64BIT`（dadao:11）与 `config 64BIT def_bool y`（dadao:28）自相重复；自检用 `int` 单选 case（`Kconfig.debug:187-190` 0..9、`158-161` 0..6）导致一镜像只验一个 case，与上游 bool + 运行时参数/KUnit 的做法不同。**P2**。

**优先级口径**：P0 = 阻塞当前在跑任务（本盘点**无**）；P1 = 影响正确性/标准 ABI 行为（22/23/24/1/2/6/11）；P2 = 形态、性能、加固、调试工具。

## 完成区

**测试结果**：只读盘点，无构建/仿真/门控。证据脚本（运行期证据目录的 `run.sh`）：正跑 **67/67 PASS**（`RESULT PASS`，exit 0）；反例注入 1 路（临时树内把 `arch/dadao/Kconfig:22` 改为 `select NOT_CLONE_BACKWARDS`）→ 同一脚本 **66 PASS + 1 FAIL**（`FAIL dadao:Kconfig:22 …`，rc=1）→ `SELFTEST PASS`（还原 = 源码树零写入，只 `cp` 到临时目录注入）。
**修改文件**：`.tao/tasks/linux/m14-linux-040-Kconfig选型.md`（结论 + 完成区 + 审阅记录）。运行期证据（`run.sh` / `enumerate.py` / 两份日志）放运行期证据目录（已被 `.gitignore` 忽略），不入库。
**验收结果**：`git status --porcelain -uall` 只列本任务书；现场计数 **758 select / 218 depends-on**（dadao 7/12、riscv 311/130、arm64 440/76）；`comm -23` 求独有集得 riscv-only **288**，分桶 87/97/40/64 = 288（与 `enumerate.py` 一致）。
**新发现/坑**：
- **判「缺 select」必须先看依赖链**：`HAVE_ARCH_SECCOMP_FILTER` 一条同时决定 `HAVE_ARCH_SECCOMP`（`arch/Kconfig:630`）与 `SECCOMP_FILTER`（666）；`ARCH_WANT_DEFAULT_TOPDOWN_MMAP_LAYOUT` 顺带 `ARCH_HAS_ELF_RANDOMIZE`（1394）——只做「缺哪个符号」的差集会漏掉这些连带门。
- **`arch/*/Kconfig.debug` 不是孤儿**：`grep -n Kconfig.debug Kconfig` 只有 `lib/Kconfig.debug`（无 arch 行），真正入口是 `lib/Kconfig.debug:2000`（menu「… Debugging」）；先查这一条才不会误判「自检开关不可达」。
- **「无消费者」必须两种搜法都做**：`NO_IOPORT_MAP` 的 C/汇编侧 `CONFIG_NO_IOPORT_MAP` 0 命中，但裸符号在 Kconfig 侧被 3 处读取（`lib/Kconfig:385` / `realtek:47` / `mips:54`），删除会让 `HAS_IOPORT_MAP` 翻 y ⇒ 判「死配置/可删」前先查 `CONFIG_` 前缀与裸符号两遍。
- **hooks 与 Kconfig 不同步**：`syscall_get_arch()` 已实现（`asm/syscall.h:121`）、`syscall_rollback()` 在 `arch/dadao` 0 命中（`grep -rn` 实证）、`HAVE_ARCH_SECCOMP_FILTER` 也没 select——Kconfig 缺口常落在「代码做了一半」的位置。
- 建议沉淀：本次枚举口径（`grep -cE` + `comm -23` 求独有集 + 关键字分桶）与三条依赖链（seccomp / mmap 布局 / lockdep）可复用为后续 ISA 差异盘点模板。
**遗留问题**：无未完成项；整改项按结论优先级由用户裁定（P0 无）。

**返工 1（reviewer 第 1 轮 Needs Revision；只改 2 处断言，条目数/分级/覆盖统计不动）**：
- **①-22 错在「全仓无第二处引用」**：实况 `arch/dadao/kernel/process.c:447` 有播种清零，通用读点在 `include/linux/entry-common.h:101/147/264`。已改成「`arch/dadao` 内除播种清零外无 test/set；通用读点因入口旁路不可达」，**P1 结论不变**。
  自证：`sed -n 447p arch/dadao/kernel/process.c` → `		ti->syscall_work = 0;`；`sed -n 101p` → `		work = READ_ONCE(current_thread_info()->syscall_work);`；`sed -n 147p` 与 `sed -n 264p` → `	unsigned long work = READ_ONCE(current_thread_info()->syscall_work);`。搜索口径：`grep -rn syscall_work arch/dadao` 仅 2 行（`arch/dadao/include/asm/thread_info.h:19` 定义 + `arch/dadao/kernel/process.c:447` 清零）。
- **④-29 错在「全树无消费者 / 符号可删」**：裸符号被 Kconfig 读取，删定义会翻转 `HAS_IOPORT_MAP`。已改成「无 C 消费者、Kconfig 侧被读取、删前须先评估；是否引出新编译单元需实测」，**仍 P2、仍是同一条**。
  自证：`sed -n 385p lib/Kconfig` → `	depends on HAS_IOMEM && !NO_IOPORT_MAP`；`sed -n 375,378p lib/Kconfig` → `config HAS_IOMEM` / `	bool` / `	depends on !NO_IOMEM` / `	default y`；`sed -n 383,386p lib/Kconfig` → `config HAS_IOPORT_MAP` / `	bool` / `	depends on HAS_IOMEM && !NO_IOPORT_MAP` / `	default y`；`sed -n 47p drivers/net/ethernet/realtek/Kconfig` → `	depends on 8139TOO && !NO_IOPORT_MAP`；`sed -n 54p arch/mips/Kconfig` → `	select HAS_IOPORT if !NO_IOPORT_MAP || ISA`。
- **同类绝对化断言全文复查**（凡「0 命中/无引用/可删」都必须带可复现命令，且 `CONFIG_` 前缀与裸符号两种搜法都做）：①-1 `user_regset|regset_view`、①-2 `syscall_rollback`、①-9 `mark_rodata_ro|set_memory_*`、③-23 `irqentry_*|irq_enter|irq_exit|rcu_irq`、③-27 `request_irq|irq_domain|irq_desc|irq_set_chip` 均已补搜索命令，并写进证据脚本的「0 命中断言」实测。
- **重跑**：`run.sh` → `RESULT PASS`、rc=0（断言数见完成区）；`run.sh --inject` → `SELFTEST PASS`。

**抽查 5 条（`sed -n '<行>p'` 原文，逐字）**：
1. `arch/dadao/Kconfig:22` → `	select CLONE_BACKWARDS` ｜ `arch/riscv/Kconfig:96` → `	select CLONE_BACKWARDS`
2. `arch/dadao/Kconfig:15` → `	select UACCESS_MEMCPY` ｜ `arch/riscv/Kconfig:229` → `	select UACCESS_MEMCPY if !MMU`
3. `arch/dadao/Kconfig:51-54` → `config NR_CPUS` / `	int "Maximum number of CPUs"` / `	default 1` / `	range 1 1` ｜ `arch/riscv/Kconfig:450-456` → `config NR_CPUS` / `	int "Maximum number of CPUs (2-512)"` / `	depends on SMP` / `	range 2 512 if !RISCV_SBI_V01` / `	range 2 32 if RISCV_SBI_V01 && 32BIT` / `	range 2 64 if RISCV_SBI_V01 && 64BIT` / `	default "32" if 32BIT`
4. `arch/dadao/Kconfig.debug:141` → `config DADAO_K3_PT_SELFTEST` ｜ `arch/riscv/Kconfig:30` → `	select ARCH_HAS_DEBUG_VM_PGTABLE`
5. `arch/dadao/Kconfig:34` → `config MMU` ｜ `arch/riscv/Kconfig:292` → `config MMU`
（附第 6 条说明参照系：`arch/arm64/Kconfig:1467` → `	select HAVE_PAGE_SIZE_64KB`——64 KiB 页的比对基准是 arm64，不是 riscv。）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-20）

审查对象 = 本任务书的每一条断言（行号、依赖链、结论）。方式：把结论引用的行号做成 67 条脚本断言（`sed -n` 打回原文，含上面 5 条抽查对），依赖链逐条落到 `arch/Kconfig`、`lib/Kconfig.debug`、`mm/Kconfig`、`mm/Kconfig.debug`、`init/Kconfig` 的具体 `depends on` 行；覆盖计数用两套独立口径（`grep -c` 与 python 去重）互校。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 初版把 `select HAVE_ARCH_SECCOMP` 记作 `arch/Kconfig:634`（实为注释行） | ✅已修 | 改为 `arch/Kconfig:630` | `sed -n 630p` = `	select HAVE_ARCH_SECCOMP` |
| 初版 `kernel/ptrace.c` 的 `ret = -EIO` 记作 1163（实为函数首行偏移） | ✅已修 | 改为 `kernel/ptrace.c:1166` | `sed -n 1166p` = `	int ret = -EIO;` |
| 初版 riscv-only 计数用 `293-7=286`（把 dadao 独有的 2 个符号也减了） | ✅已修 | 改用 `comm -23` 求集合差，得 288 | `run.sh` 现场输出 `riscv-only=288`，与分桶和一致 |
| 曾假设「`arch/dadao/Kconfig.debug` 未被 source ⇒ 自检开关不可达」 | ✅已修（错误假设撤销） | 查得 `lib/Kconfig.debug:2000` 统一 source；不作为 finding | `sed -n 1998,2000p lib/Kconfig.debug` |
| 初版把 `HAVE_PAGE_SIZE_64KB` 当 riscv 参照项（riscv 无此符号） | ✅已修 | 参照改为 `arch/arm64/Kconfig:1467`，并在结论中注明 | `sed -n 1467p` = `	select HAVE_PAGE_SIZE_64KB` |

判决：5 条 finding 全部 ✅已修，无未修项 ⇒ 状态置 `待验收`。

### 第 2 轮 engineer 自审（2026-11-20，返工 reviewer 第 1 轮 Needs Revision）

逐行核对 reviewer 指名的两处，并把「无/0 命中/可删」类断言全部改为「命令 + 实测输出」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ①-22 `syscall_work` 说「全仓无第二处引用」，实际 `process.c:447` 有清零、`entry-common.h:101/147/264` 有读点 | ✅已修 | 改为「`arch/dadao` 内除播种清零外无 test/set；通用读点因入口旁路不可达」 | `sed -n 447p` = `		ti->syscall_work = 0;`；`sed -n 101p/147p/264p` 三行均含 `syscall_work`；`run.sh` 新增该 4 行断言，正跑 PASS |
| ④-29 `NO_IOPORT_MAP` 说「全树无消费者 / 可删」，实际裸符号被 `lib/Kconfig:385` 等读取，删定义会翻转 `HAS_IOPORT_MAP` | ✅已修 | 改为「无 C 消费者 + Kconfig 侧被读取 + 删前须评估 + 新编译单元需实测」 | `sed -n 385p` = `	depends on HAS_IOMEM && !NO_IOPORT_MAP`；`sed -n 375,378p` 显示 `HAS_IOMEM default y`；`sed -n 47p realtek` / `sed -n 54p mips` 命中；`run.sh` 新增断言 + 「`CONFIG_NO_IOPORT_MAP` 全树 0 命中」断言，正跑 PASS |
| 同类绝对化断言（`user_regset`/`syscall_rollback`/`mark_rodata_ro`/`irqentry`/`request_irq`）原先未给命令 | ✅已修 | 每条补搜索命令；`run.sh` 增加 6 条「0 命中」断言（命中即 FAIL） | `run.sh` 正跑 `RESULT PASS`、rc=0；注入模式 `SELFTEST PASS` |

判决：3 条 finding 全部 ✅已修，无未修项；条目数仍 30、分级未动 ⇒ 状态保持 `待验收`，交回主会话复核。

### 第 1 轮 reviewer 验收（2026-11-20）

**判决：Needs Revision** —— 2 处断言与现场不符；行号抽查、核心统计、证据脚本、门控、三重点核验**全部通过**。

**重跑（我自己的命令与真实输出）**：
- 运行期证据目录内的 `run.sh` → `RESULT PASS`、`PASS=49 FAIL=0`、rc=0；与完成区日志全量 `diff` 无差异。
- 独立反例注入（临时树内改 `arch/dadao/Kconfig:15` 为 `select NOT_UACCESS_MEMCPY`，与自审注入点 :22 不同）→ 同一脚本 `FAIL dadao:Kconfig:15 want='select UACCESS_MEMCPY'`、`PASS=48 FAIL=1`、`RESULT FAIL`、rc=1 → 删临时树 → 源树 `md5sum arch/dadao/Kconfig` 注入前后均 `f35946103ba8a798cf43a7e188464882` → 复跑回绿 `RESULT PASS`、rc=0。
- 门控：`make check-knowledge-refs` rc=0（悬空 0、具体 `.work` 引用 0）；`make check-tasks` rc=0（报告型，① 列本任务属预期）。

**行号抽查（`sed -n '<行>p'` 两侧原文，11 条 ≥ 要求 8，P1×5 / P2×6，全部逐字命中）**：①-1 `riscv:148`/`arm64:173`/`ptrace.c:1356`/`1166`；①-2 `riscv:145`/`arm64:171`/`arch/Kconfig:630`/`666`/`syscall.h:121`；①-6 `riscv:63/320/353/228`/`arm64:52`/`lib/Kconfig.debug:1444-1446`；①-11 `riscv:125`/`arm64:141`/`time.h:71`；①-22 `process.c:516/662`/`traps.c:336`/`riscv:112`/`thread_info.h:19`；②-3 `riscv:199`/`arm64:225`/`init/Kconfig:1991`/`sys_ni.c:392`；②-4 `riscv:83/142`/`arm64:92/167`/`arch/Kconfig:1394`/`mm/util.c:480-484`；②-12 `riscv:227`/`arm64:253`/`riscv:169`；②-17 `dadao:51/54`↔`riscv:450/452`；②-20 `dadao:15`↔`riscv:229`；②-29 `dadao:37`/`arm64:323`/`riscv:128`。另补验约 90 处引用（依赖链 `arch/Kconfig:130-132/701-705/1581-1584/1394`、`lib/Kconfig.debug:916-919`、`mm/Kconfig.debug:186-190`、`init/Kconfig:556-558/1988-1991`、`sched_clock.h:46` 等）全中。

**统计重算（我的 `grep -cE`/`comm -23`，口径与完成区同）**：select = dadao 7+0、riscv 276+0+10+21+4=**311**、arm64 317+0+123=**440**，合计 **758**；depends = **12/130/76**，合计 **218**；riscv 去重 293、dadao 7、`comm -23` 独有 **288**；dadao 12 条 depends 全指 `DADAO_*`，落点 `Kconfig.debug:55/76/92/105/115/124/133/276/292/327/350/375` 逐行命中 —— 758/218/288、7/12、311/130、440/76 全对上。

**三重点核验**：① TRACEHOOK 缺 ⇒ `GETREGSET/SETREGSET` 段（`ptrace.c:1356-1382`）被编译掉，落 `default: break`（1406-1407）后 `return ret`（1410）返回初值 `-EIO`（1166），dadao `user_regset` grep 0 ⇒ GDB 寄存器读返 `-EIO` **成立**；② `arch/Kconfig:630` 确在 `config HAVE_ARCH_SECCOMP_FILTER` 内、666 为 `SECCOMP_FILTER` 依赖，dadao 两符号均未 select，`syscall_get_arch()` 在 `syscall.h:121`、`syscall_rollback` 于 arch/dadao **0 命中** ⇒ **成立**；③ 与 038 同根因：桩即 `include/linux/sched_clock.h:46-49` 的 `#else` 空 `static inline`（逐行核 43-50），`kernel/time/Makefile:23` `obj-$(CONFIG_GENERIC_SCHED_CLOCK)`；038 分支任务书 ④-1 报同一条（038 记 P0、本任务记 P1，仅优先级口径不同、非矛盾；038 内容为读其分支任务书，未重跑其脚本，不在本任务范围）。

**约束核验**：`git show --stat HEAD` 仅本任务书；`git status --porcelain -uall` 0 行；源树只读（md5 前后一致）；未提交 git；本记录无运行期路径。分析面 = 任务书 + 运行期证据脚本 + 源树 Kconfig/ptrace/sched_clock 等引用文件 + 038 分支任务书，**无采信项**（全部亲自重跑）。

**Needs Revision（指名两处，其余全过）**：
1. ①-22「`thread_info.syscall_work` 全仓无第二处引用」不实：`arch/dadao/kernel/process.c:447` = `ti->syscall_work = 0;`（umon 栈 thread_info 播种清零），通用读点 `include/linux/entry-common.h:101/147/264` 亦引用该字段。改法：写成「arch/dadao 内除播种清零外无任何 test/set 调用；通用读点因入口旁路不可达」（P1 结论本身不变）。
2. ④-29「全树无消费者 / 仅各 arch Kconfig 定义 / 符号可删」不实：C 侧 `CONFIG_NO_IOPORT_MAP` 0 命中属实，但裸符号被 `lib/Kconfig:385`（`HAS_IOPORT_MAP depends on HAS_IOMEM && !NO_IOPORT_MAP`）、`drivers/net/ethernet/realtek/Kconfig:47`、`arch/mips/Kconfig:54` 读取，且 `HAS_IOMEM` 于 `lib/Kconfig:375-378` `default y` ⇒ 删符号会让 dadao 的 `HAS_IOPORT_MAP` 由 n 翻 y。改法：写成「无 C 消费者；Kconfig 侧被 lib/Kconfig:385 等读取，直接删会翻转 HAS_IOPORT_MAP，须先评估」。

### 第 2 轮 reviewer 验收（2026-11-20）

**判决：Accepted** —— 2 处修正核实改对、6 条 0 命中断言抽 2 条注入验证可达 FAIL、数字未动、门控全绿；1 条文档级 finding 记档不阻断。

**两处修正（任务书原文 + 源行 `sed -n` 逐字核对）**：
- ①-22 现文：「在 `arch/dadao` 内**除播种清零**（`kernel/process.c:447` `ti->syscall_work = 0;`）**外无任何 test/set**；通用读点（`include/linux/entry-common.h:101/147/264`）因入口旁路而不可达」——源行实测：447 = `ti->syscall_work = 0;`，101/147/264 均含 `READ_ONCE(current_thread_info()->syscall_work)` ⇒ **改对**（P1 结论未动）。
- ④-29 现文：C/汇编侧 `grep -rn CONFIG_NO_IOPORT_MAP .` = 0 + 裸符号 3 处读取（`lib/Kconfig:385`/`realtek:47`/`mips:54`）+ `HAS_IOMEM` `default y`（`lib/Kconfig:375-378`）⇒ `HAS_IOPORT_MAP`（`lib/Kconfig:383-386`）由 n 翻 y + **13 个依赖项** + 预计不引出新编译单元、**需实测**、结论「删前须先评估，不是可删」——源行 375-378/383-386/385/47/54 全中；我另实测全树 `grep -rn CONFIG_NO_IOPORT_MAP` = **0 命中**、`grep -rnE 'depends on.*HAS_IOPORT_MAP' --include='Kconfig*' | wc -l` = **13** ⇒ **改对**（仍 P2、同一条）。

**6 条 0 命中断言（实现为「输出非空即 FAIL」）+ 我抽 2 条独立注入（临时树，真树零写入）**：临时树基线 67 PASS rc=0 → ① 新建 `arch/dadao/kernel/irq.c` 假命中 `irq_enter` → `FAIL dadao irqentry/irq_enter/rcu_irq expected 0 hits`、66+1、**rc=1** → rm 还原 → ② `include/asm/syscall.h` 追加 `syscall_rollback` → `FAIL dadao syscall_rollback expected 0 hits`、66+1、**rc=1** → `cp` 备份还原（两侧 md5 `50363d6d…` 一致）→ **回绿 67 PASS rc=0** → 删临时树；真树 `syscall.h`/`Kconfig` md5 与第 1 轮一致（`50363d6d…`/`f3594610…`）。

**数字与脚本（全部现场重跑）**：条目 **30**（①16/②5/③6/④3，grep 计数 30）、P1 7 条（22/23/24/1/2/6/11）、**758/218/288**（正跑 `COUNT` 行）、**13** 依赖项 —— 均与第 1 轮一致；运行期证据目录内 `run.sh` 正跑 **67/67 PASS** rc=0、`run.sh --inject` `SELFTEST PASS` rc=0。

**门控与约束**：`make check-knowledge-refs` rc=0、`make check-tasks` rc=0；`git status --porcelain -uall` 0 行、`git show --stat HEAD` 仅本任务书（返工提交）；源树 HEAD `c5f411a3a` 干净；未提交 git；本记录无运行期路径。

**Finding（文档级，不阻断）**：第 29 条 13 项的举例中 `8139TOO`、`TCG_TIS` 不在实测集合内（13 项明细 = FW_CFG_SYSFS / 104_QUAD_8 / VORTEX / CAN_PEAK_PCMCIA / HW_RANDOM_AMD / TCG_ATMEL / GPIO_TQMX86 / GPIO_AMD8111 / SCSI_GENERIC_NCR5380 / GPIB_NI_PCI_ISA / I2C_ELEKTOR / SND_SC6000 / SND_LX6464ES；`fw_cfg`/`GPIB` 为近似指代）——计数 13、机制与「删前须评估」结论不受影响，按文档级小错记档，由 architect 收尾时改。


