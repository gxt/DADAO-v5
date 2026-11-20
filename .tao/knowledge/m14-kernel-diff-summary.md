# M14 内核与主流 ISA 差异盘点 — 汇总索引

> **性质**：八份只读盘点任务（`m14-linux-036`–`043`）的**汇总索引**，不是第二套判据。每条差异的原文（两侧 `文件:行号` + 影响面 + P0/P1/P2）在各自任务书的「盘点结论」段。
> **对比对象**：同一份 Linux 源树的 `arch/riscv`（主）/ `arch/arm64`（参照）。**盘点是只读的**：不改代码、不占写者锁。
> **整改权归用户**（2026-11-20）：本页只做索引与分流建议，是否整改、何时整改由用户逐项决定。

## 一、八份盘点（195 条）

| 任务 | 条数 | P0 | 关注点 |
| --- | --- | --- | --- |
| `m14-linux-036 mm/缺页/页表` | 25 | 3 | `select LOCK_MM_AND_FIND_VMA` 缺、缺页类不含读写、fill 不持 `ptl`、VMA 锁释放后 UAF 风险 |
| `m14-linux-037 syscall/ABI` | 25 | 0 | entry/exit 10 工作项引用 0；`syscall_set_return_value` 二次取负；参数只读 `rd16+`；号表 5 个号落 `sys_ni_syscall`（258/259 是契约要求） |
| `m14-linux-038 时间/时钟` | 19 | 5 | 未注册 `clocksource`/`clockevent`；tick 只 `jiffies_64 += 1`；tick 启动点只在探针；`GENERIC_SCHED_CLOCK` 未选 |
| `m14-linux-039 信号/退出` | 29 | 18 | 信号机制整体缺失（无 `kernel/signal.c`、无帧、`rt_sigreturn` 是桩、`TIF_SIGPENDING` 无消费者） |
| `m14-linux-040 Kconfig/选型` | 30 | 0 | 缺 `select` 16 条（`TRACEHOOK`/`SECCOMP_FILTER`/`LOCKDEP`/`GENERIC_SCHED_CLOCK` 等）；`NO_IOPORT_MAP` 删除会引发配置翻转 |
| `m14-linux-041 进程/线程` | 19 | 0 | `ret_from_fork` 把 `current` 当 `prev` 交 `schedule_tail()`；缺 `THREAD_INFO_IN_TASK`；`dadao_user_stack_top` per-hart |
| `m14-linux-042 trap/异常/中断` | 27 | 1 | `GENERIC_IRQ_ENTRY` 未编（`in_hardirq()` 恒 0）；`user_mode()` 恒 0；用户态故障走 `die`/monitor 码 |
| `m14-linux-043 启动/初始化` | 19 | 0 | 进 C 前 `current` 为 NULL；启动保留区未 `memblock_reserve`；**生产镜像走不到 `rest_init()`** |

> **P0 口径不一**：036/042 按「阻塞在跑任务」，038 按「阻塞尚未开始的 `026`」，039 按「功能整体缺失」。**不要简单相加当紧急项数**。

## 二、七个跨子系统根因（多份独立指向同一处）

1. **缺通用 entry/exit 工作循环** ← 037 #13、039 P0-1/2、040 ③、041 B2、042
   `arch_do_signal_or_restart` 无调用点（`kernel/entry/common.c:13` 是 `__weak` 空桩、唯一调用点 `:66` 不可达）、`TIF_SIGPENDING`/`TIF_NEED_RESCHED`/`_TIF_WORK_MASK` 全树 0 消费者、`syscall_enter/exit_to_user_mode` 引用 0、`syscall_work` 是死代码。
   **后果**：信号、`SIGCHLD`、`exit_group`、抢占、audit/ptrace/seccomp **静默失效**（不是编译错）。
2. **`CONFIG_GENERIC_SCHED_CLOCK` 未选** ← 038 ④-1、040 ① ⇒ `sched_clock_register()` 是 `static inline {}` 空桩（`include/linux/sched_clock.h:46-49`）。
3. **`CONFIG_GENERIC_IRQ_ENTRY` 未编** ← 042 ①-b1、038 ②-3、040 ③ ⇒ `kernel/entry/common.o` 不在链接集，`in_hardirq()` 恒 0、`get_irq_regs()` 恒 NULL、`irq_exit_rcu()` 不跑 softirq。
4. **`CONFIG_LOCK_MM_AND_FIND_VMA` 未选** ← 036 P0、042 P0 ⇒ **`m14-linux-035` 阶段 2 已补**。
5. **`user_mode()` 恒 0** ← 039 C5、042 P0 ⇒ 根因是帧里没有模式位；**已裁定用 `status` 低 4 位**（`discussing.md` N30）。
6. **信号机制整体缺失** ← 039（29 条 / P0 18）⇒ 直接推翻 `m14-linux-027` 的 2–3 h 估计，已拆成 `045`/`046` + 收窄后的 `027`。
7. **用户态故障/坏指针无出口** ← 036 ①、040 ① ⇒ 缺 `fixup_exception`，坏用户指针**直接停机**；缺 `select UACCESS_MEMCPY`。

## 三、分流（建议，用户定）

- **已修**（`m14-linux-035` 阶段 2 顺带）：`LOCK_MM_AND_FIND_VMA`、`pte_modify` 保 D/A、`flush_tlb` A/D 回写、`protection_map` 漏 `VM_SHARED`、`copy_user_highpage` 宏错、filemap、权限闸。
- **一行 Kconfig 类**（→ `m14-linux-044`）：`GENERIC_SCHED_CLOCK`、`GENERIC_IRQ_ENTRY`、`UACCESS_MEMCPY`（配 `fixup_exception`）。
- **需立任务**：`045`（entry/exit 工作循环）、`046`（信号帧与投递）、`026`（时钟链，038 的 5 条 P0 即它的设计输入）、trap 异常分流（`die` vs `force_sig_fault`）。
- **暂不修**（纯形态差异，单核/无 OF/无半虚拟化改了没收益）：vDSO、broadcast、perf/trace/kfence/kprobe、`tick_*broadcast` 等。

## 四、纪律备注（盘点期间学到的，已进门控/规范）

- 只读任务的证据脚本**判「只改了本任务书」不能用工作树未提交改动数**（`036`/`038`/`042` 各被打回一轮）⇒ `docs/Process-07 §5b`。
- **断言期望值与实际值必须同源派生**（`042` 的 `clean(committed)` vs `clean`）⇒ 同上。
- **基线参数不得缺省取 `HEAD`**（`m15-spec-005` 的 `BASE_REF`）⇒ 同上（第七例）。
- **写死常量类断言**（栈尺寸/页大小）必须现场派生：`041` 曾把 `THREAD_SIZE_ORDER 0` 当 4 KiB，实测 64 KiB（`PAGE_SHIFT=16`）。
