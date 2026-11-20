# m14-linux-044: Kconfig 选型补齐（`GENERIC_SCHED_CLOCK` / `GENERIC_IRQ_ENTRY` / `UACCESS_MEMCPY` + `fixup_exception`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-035` 合入（**同一份 `arch/dadao/Kconfig.patch`**，必须串行）
**可并行分片**：否
**预估**：3–4 h
**档位**：中改
**状态**：待开始

## 背景（盘点结论，用户 2026-11-20 批准先修）

`m14-linux-038`/`040`/`042` 三份只读盘点交叉指向三处**只差一个 `select`** 的缺口，且都不是 DADAO 特有语义，纯属「通用代码没编进来」：

1. **`CONFIG_GENERIC_SCHED_CLOCK` 未选**（038 ④-1、040 ①）：`sched_clock_register()` 退化为 `include/linux/sched_clock.h:46-49` 的 `#else` 空 `static inline` ⇒ 照 riscv 写法移植会**静默无效**；
2. **`CONFIG_GENERIC_IRQ_ENTRY` 未编**（042 ①-b1、038 ②-3、040 ③）：`kernel/entry/Makefile:15` 只在该配置下编 `common.o`，产物不存在 ⇒ `in_hardirq()` 恒 0、`in_interrupt()` 的硬中断/NMI 分量恒 0、`get_irq_regs()` 恒 NULL、`irq_exit_rcu()` 不跑 softirq；
3. **`CONFIG_UACCESS_MEMCPY` 未选**（036 ①、040 ①）：`copy_from_user`/`copy_to_user` 走通用实现需要它；但**选它必须同时补 `fixup_exception()` 出口**（`arch/dadao/mm/fault.c:726-737` 现在没有），否则**坏用户指针直接停机**（不是返回 `-EFAULT`）。

## 要做

1. `components/linux/patches/arch/dadao/Kconfig.patch` 补三条 `select`（写法对照 `arch/riscv/Kconfig`；`UACCESS_MEMCPY` 注意上游是 `select UACCESS_MEMCPY if !MMU` 还是无条件，**按 DADAO 实际（有 MMU）判断，不要照抄**）；
2. 补 `fixup_exception()`：坏用户指针经 `__ex_table` 返回 `-EFAULT`，**不再进 `dadao_die`/monitor 码**；对照 `arch/riscv/mm/fault.c:93-99`；
3. **同步检查**：选了 `GENERIC_IRQ_ENTRY` 后 `irqentry_*` 的调用点是否仍缺（若缺，登记为 finding 交后续任务，**本任务不扩范围去接**——那属 entry/exit 工作循环任务）；
4. 若 `GENERIC_SCHED_CLOCK` 要求注册点（`sched_clock_register`），**只做「能注册 + 可读」**，不重写 tick 链（那是 `m14-linux-026 clocksource/clockevent`）。

## 验收（逐条贴真实 rc）

1. **`in_hardirq()` 不再恒 0**：在中断 handler 内实测返回 1（探针或既有 k2 断言扩展）；
2. **`sched_clock()` 有真值**：与 `cfx_time` 同源、单调递增（给实测序列）；
3. **坏用户指针返回 `-EFAULT`**：给一个非法用户地址的 `copy_from_user` 实测（改前停机、改后 `-EFAULT`）；
4. 不回归：k0 130 / k1 112 / k2 170 / k3 263 / k4 五探针 / k5（syscall 104 / clone 97 / futex 174）；
5. **可达 FAIL ≥2 路**：① 去掉 `select GENERIC_IRQ_ENTRY` ⇒ `in_hardirq()` 红；② 去掉 `fixup_exception` ⇒ 坏指针用例停机（`cp`+md5 还原 + 重建）；
6. `check-patch-tree` linux 段 0 问题；从 base 全新 `apply_series` 可重放；合并态（`Process-07 §5a`）。

## 完成区

（待填）
