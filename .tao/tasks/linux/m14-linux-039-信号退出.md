# m14-linux-039: 信号/退出 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：2–3 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：待验收

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/kernel/signal.c`/`signal.h`/`process.c` 的退出与等待部分、`include/asm/signal.h`、`ucontext` 布局，以及 `arch/riscv/kernel/{signal,process}.c`、`arch/arm64/kernel/{signal,process}.c`（为 `m14-linux-027` 提供对照）。

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

**口径**：DADAO 侧读自组件源检出，**HEAD `c5f411a`**（盘点期间该树 `git status` 干净、只读未改）；对照 `arch/riscv`（主）/`arch/arm64`（参照）。共查 **42 项 hook/机制、76 条断言**，差异 **29 条**（P0 18 / P1 6 / P2 5；另 13 项判「与上游一致」）。条数与行号全部由运行期证据目录内 `run.sh` 现场核对（只读快照 + md5），不写死。

**P0 —— 阻塞 m14-linux-027**（18 项）

1. ① **缺失 hook：信号投递总闸**（A1/A5）。`arch/dadao/` 全树无 `arch_do_signal_or_restart`；generic 侧是弱符号（`kernel/entry/common.c:13`）⇒ 缺了照样链接、静默不投递 ↔ `arch/riscv/kernel/signal.c:499`；`get_signal()` 调用点同样没有 ↔ `:534`。
2. ① **返回用户态不跑工作循环**（A2/A3）。`arch/dadao/kernel/syscalls.c:127-143` 只把 `ERESTART*` 折成 `-EINTR`，`arch/dadao/kernel/process.c:669` 直接返回 stub 策略；无 `irqentry_enter/exit_*`（`arch/dadao/` 全树无）↔ `syscall_exit_to_user_mode`（`arch/riscv/kernel/process.c:232`）+ `irqentry_enter_from_user_mode`（`arch/riscv/kernel/traps.c:150`）。影响：`TIF_SIGPENDING`（`arch/dadao/include/asm/thread_info.h:47`）永不消费 ⇒ 信号、`SIGCHLD`、`exit_group` 的 `zap_other_threads` 全部静默失效；连带 `TIF_NEED_RESCHED` 也不生效（用户态只在阻塞式 syscall 里让出）。
3. ① **信号帧整体不存在**（B1–B6/B12）。无 `arch/dadao/kernel/signal.c`；`rt_sigframe`/`get_sigframe`/`setup_rt_frame`/`setup_sigcontext`/`restore_sigcontext`/帧组装链（`handle_signal`+`signal_setup_done`+altstack 保存）无对应物 ↔ `arch/riscv/kernel/signal.c:35,390,413,353,219,483,496,430`。
4. ① **`sys_rt_sigreturn` 是桩**（B7）：`return -EINVAL`（`arch/dadao/kernel/syscalls.c:44-46`）↔ `SYSCALL_DEFINE0(rt_sigreturn)` 真实现 `arch/riscv/kernel/signal.c:310-351`（含 `badframe` 失败路径 `:341-350`）。影响：handler 返回即丢上下文。
5. ② **uapi 帧布局陈旧**（B8/B9）：`user_regs_struct` 仍 `rd[32]/rb[32]/ra[8]/ip/status`（`arch/dadao/include/uapi/asm/ptrace.h:6`），`sigcontext` 直接引用（`arch/dadao/include/uapi/asm/sigcontext.h:7`）；与 027 已裁定的 2048B（`rd[64]/rb[64]/ra[64]/rf[64]`，`rb[0]`=IP）冲突。上游是「`sc_regs` 与 `pt_regs` 同构、整块 `__copy_from_user`」（`arch/riscv/kernel/signal.c:226`）；我们内核侧已是 4×64+2（`arch/dadao/include/asm/ptrace.h` 的 `_Static_assert`）而 uapi 侧落后 ⇒ 帧装不下 4 组。
6. ② **`user_mode(regs)` 恒 0**（C1，`arch/dadao/include/asm/ptrace.h:87`）↔ `arch/riscv/include/asm/ptrace.h:67`（`status & SR_PP`）。generic 入口靠它分流（`kernel/entry/common.c:111`）⇒ 用户异常被当内核异常；「回用户态」的一切判定（信号投递、`do_trap` 分流）同此。
7. ③ **用户态页故障仍以 monitor 码终止整机**（C3/C4/C6）：`arch/dadao/mm/fault.c:702`（`DADAO_PF_FATAL`）→`:735`（`die-no-vma`）/`:764`（`die-perm`）→`arch/dadao/kernel/traps.c:377-382`（`dadao_early_exit`）↔ `arch/riscv/mm/fault.c:152`（`do_trap(regs, SIGSEGV…)`；内核态分支走 `no_context`，定义在同文件 `:93`、调用 `:156`）→`arch/riscv/kernel/traps.c:129`（`force_sig_fault`）。影响：S1 无从断言；父进程永远看不到 `WIFSIGNALED`。

**P1 —— 影响正确性**（6 项）

8. ① **缺 `access_error()` 判定表**（C2）：上游在 `handle_mm_fault` 前用 cause+VMA flags 判越权（`arch/riscv/mm/fault.c:249-273`），越权直接 `SEGV_ACCERR`（`:354-358`）；我们只在私有通道里由 `CFXPERM+NWPERM` 反推（`arch/dadao/mm/fault.c:740-769`）⇒ 恢复 SIGSEGV 时 `si_code`（MAPERR/ACCERR）无来源。
9. ①④ **无 sigtramp 载体**（F1/F2/F3）：未 `select HAVE_GENERIC_VDSO`（`arch/dadao/Kconfig` 全文无）↔ `arch/riscv/Kconfig:174`；无 `VDSO_SYMBOL`/vdso 对象 ↔ `arch/riscv/kernel/signal.c:438`。027 必须先裁定载体：最小 vdso / 用户栈压两条指令（`arch/riscv/kernel/signal.c:450`，nommu 形）/ `SA_RESTORER`（`arch/arm64/kernel/signal.c:1487`）。
10. ①④ **`DYNAMIC_SIGFRAME` 未选**（F4/A7）：`arch/Kconfig:1770` 定义、riscv `select`（`arch/riscv/Kconfig:623`）；缺失 ⇒ `sigaltstack_size_valid()`（`arch/riscv/kernel/signal.c:585`）不生效，小于帧的 altstack 也能装。

**P2 —— 形态差异**（5 项）

11. ② **`ucontext` 用 generic 版**（B11）：`generic-y += ucontext.h`（`arch/dadao/include/uapi/asm/Kbuild:5`）⇒ 结构 `:5-11` 里掩码在末尾 ↔ riscv 自定义（`arch/riscv/include/uapi/asm/ucontext.h:13-36`，掩码前置、预留 128B）。单 libc 自洽即可，但 musl 的 `mcontext_t`/`uc_sigmask` 偏移须按实际头文件取。
12. ② **缺 `AT_MINSIGSTKSZ`**（A6）：`arch/dadao/include/asm/elf.h` 无 `ARCH_DLINFO` ↔ `arch/riscv/include/asm/elf.h:117`；影响 glibc 的 `SIGSTKSZ`，musl 不依赖。
13. ② **栈增长只在 missing 类**（E3/E2）：`arch/dadao/mm/fault.c:731` 才尝试 `dadao_pf_grow_stack`，permission 类永不长（019 S5 的既有设计）↔ 上游 `lock_mm_and_find_vma`（`arch/riscv/mm/fault.c:382`）对任意 fault 长栈。
14. ③ **探针侧的收尸手法**（D3）：`kernel_wait4()` 写状态要用户指针（`arch/dadao/kernel/k5_syscall_selftest.c:694`），探针改为轮询 `EXIT_ZOMBIE` + `exit_code`（`:721`）。内核无缺陷，但 027 的 S3 必须走**用户态** `wait4`/`waitid` 才算测过。

**判「与上游一致」的 13 项要点**（不列为差异，写清以免重复调研）

- **退出/收尸**：`do_exit`/`do_group_exit`/`exit_code`/`wait4` 全走通用（D1/D2），arch 侧两侧都没有覆盖；正常退出链路**已工作**（K5 探针以 `exit_code>>8`、`&0x7f` 断言）——缺口只在「异常致死」。`flush_thread`/`release_thread`/`start_thread`/`copy_thread`/`arch_dup|release_task_struct` 的有无与上游等价（D4–D8）；`expand_stack_locked`（`arch/dadao/mm/fault.c:276`，E1）承载 `RLIMIT_STACK`/`stack_guard_gap`，**`setrlimit` 无需 arch 代码**（syscall 已在表内、`arch/dadao/kernel/syscall_argmask.c:151` 已配好参数掩码），027 只需补继承/TDD 断言。
- **头文件/钩子**：`asm/signal.h` 缺失不算缺口（B10：uapi 强制头自动生成 generic wrapper，riscv 同样没有）；`TIF_*` 位定义齐（A4）；`arch_vma_access_permitted` 恒 true（C5，`arch/dadao/include/asm/mmu_context.h:98`）与上游默认一致（riscv 走 `include/asm-generic/mm_hooks.h:20-25` 同样 `return true`）——**不是 SIGSEGV 的成因**，且本端口该 hook 无调用者（私有通道不走 `mm/memory.c:6665`）；无 `COMPAT`（F5）、`CLONE_BACKWARDS` 已选（F6，025 的成果）。

### 覆盖口径（现场派生）

枚举办法：从 `arch/riscv` 的 `kernel/{signal,process,traps}.c` + `mm/fault.c` + `include/asm/{ptrace,elf}.h` + `Kconfig`，以及 `arch/arm64` 同类文件逐**函数/hook**取出「主流 ISA 必须具备的面」，再逐项在 `arch/dadao` 判「有/缺/语义不同」；每条断言写成 `文件:行:模式`（`checks.tsv`），由 `run.sh` 现场统计三组计数（items / rows / verdict）——**总数不写死**。42 项清单：

- **A 信号投递（7）**：A1 `arch_do_signal_or_restart`｜A2 exit-to-user 工作循环｜A3 irqentry 入口｜A4 TIF 工作位｜A5 `get_signal` 调用点｜A6 `signal_minsigstksz`/`AT_MINSIGSTKSZ`｜A7 `sigaltstack_size_valid`
- **B 信号帧（12）**：B1 `rt_sigframe`｜B2 `get_sigframe`｜B3 `setup_rt_frame`｜B4 `setup_sigcontext`｜B5 `restore_sigcontext`｜B6 `SYSCALL_DEFINE0(rt_sigreturn)`｜B7 `sys_rt_sigreturn` 桩｜B8 uapi `user_regs_struct`｜B9 uapi `sigcontext`｜B10 `asm/signal.h`｜B11 `ucontext` 布局｜B12 `handle_signal`/`signal_setup_done`/altstack 保存
- **C 同步异常→信号（6）**：C1 `user_mode()`｜C2 `access_error()`｜C3 `bad_area`/`no_context`｜C4 `do_trap`/`force_sig_fault`｜C5 `arch_vma_access_permitted`｜C6 私有页故障通道的判决出口
- **D 退出/等待（8）**：D1 `do_exit`/`do_group_exit`｜D2 `exit_code` 断言｜D3 `kernel_wait4` 手法｜D4 `flush_thread`｜D5 `arch_dup|release_task_struct`｜D6 `start_thread`｜D7 `copy_thread`｜D8 `release_thread`
- **E 栈增长（3）**：E1 `expand_stack_locked`（RLIMIT_STACK/guard gap 的落点）｜E2 上游 `lock_mm_and_find_vma`｜E3 增长触发类
- **F tramp + Kconfig（6）**：F1 `HAVE_GENERIC_VDSO`｜F2 `VDSO_SYMBOL`/vdso｜F3 `SA_RESTORER`｜F4 `DYNAMIC_SIGFRAME`｜F5 `COMPAT`｜F6 `CLONE_BACKWARDS`

### 抽查（`sed -n '<行>p'`，两侧原文，非记忆）

```
arch/dadao/kernel/syscalls.c:46      | 	return -EINVAL;
arch/riscv/kernel/signal.c:310       | SYSCALL_DEFINE0(rt_sigreturn)
arch/dadao/include/asm/ptrace.h:87   | 	return 0;
arch/riscv/include/asm/ptrace.h:67   | #define user_mode(regs) (((regs)->status & SR_PP) == 0)
arch/dadao/mm/fault.c:764            | 				result = "die-perm";
arch/riscv/kernel/traps.c:129        | 	force_sig_fault(signo, code, (void __user *)addr);
arch/dadao/kernel/traps.c:381        | 		dadao_early_exit(0xc0UL | ((DADAO_MODE_USER & 0x3) << 4) | 0x1);
arch/riscv/mm/fault.c:152            | 		do_trap(regs, SIGSEGV, code, addr);
arch/dadao/include/asm/mmu_context.h:98 | 	return true;
arch/dadao/include/uapi/asm/ptrace.h:6  | 	unsigned long rd[32];
arch/riscv/kernel/signal.c:226       | 	err = __copy_from_user(regs, &sc->sc_regs, sizeof(sc->sc_regs));
```

## 完成区

**测试结果**：通过 76/76 条断言、42/42 项；失败 0。`run.sh` rc=0；`run.sh --inject` 两路反例均 rc=1（改行号 / 改快照正文）、`cp`+md5 还原后回绿 rc=0。
**修改文件**：仅本任务书（`git status -uall` 只有它）；组件源检出只读未改（HEAD `c5f411a`，`git status` 干净）；未占写者锁、未 apply_series、未重建、未跑仿真。
**验收结果**：
- `./run.sh` → `items=42 rows=76 failures=0`；`verdict 18 P0 / 6 P1 / 5 P2 / 13 same`；`RESULT: PASS (76 claims over 42 items)` rc=0。
- `./run.sh --inject` → 注入1 `FAIL INJ …:45 expected 'arch_do_signal_or_restart' actual '{'` rc=1；注入2 快照 md5 校验 rc=1；还原后 `ok SNAP all snapshot.md5: 287 files match` + `RESULT: PASS` rc=0。
- 抽查 11 行两侧原文全部命中（本节上方），且 live 树与快照 md5 逐文件一致。
**新发现/坑**：
- `arch_do_signal_or_restart` 在 generic 是 `__weak`（`kernel/entry/common.c:13`）⇒「缺 hook」是**静默型**缺陷，不报链接错。建议 027 的探针加一条「handler 被调用」的可达 FAIL 断言，勿以「能链接」判已实现。
- `user_mode()` 恒 0（`arch/dadao/include/asm/ptrace.h:87`）是**跨子系统**的地雷：不仅信号，`irqentry` 分流、`do_trap`、任何 `user_mode(regs)` 判定都会被带偏；027 落地前必须先让它从帧的 run mode 判。
- 盘查口径：`asm/signal.h`/`asm/ucontext.h` 缺失**不算**缺口（uapi 强制头自动生成 generic wrapper，riscv 同样没有）——盘点时容易被误报为「缺 hook」。
- `arch_vma_access_permitted` 恒 true 与上游等价（035 的结论成立），SIGSEGV 缺口在判决层（`die-*`）而非该 hook；建议把这条写进 027 任务书，避免重复排查。
**遗留问题**：无（只读盘点；整改由用户裁定后另立任务）。

## 审阅记录

### 第 1 轮 engineer 自审

- 逻辑：逐条把「上游有/hook 名」与「DADAO 是否有」对齐；对每个 `file:line` 用 `sed -n` 回读（快照 + live 双向 md5 一致），无凭记忆行号。
- 设计：把「断言集合」与「结论文字」解耦——结论引用 item 编号（A1…F6），断言表是唯一事实源，脚本现场统计条数；避免手写总数漂移。
- 防造假：`run.sh` 的 `has`/`absent_file`/`absent_grep` 三类断言都有可达 FAIL 路径，已用两路注入证明（错行号、改快照正文）；快照 287 文件 md5 校验防止「结论与快照脱钩」。
- 边界：未改任何代码；未触碰组件源检出（只读，HEAD 记录在案）；未提交 git。
- 判决：全部 finding 已闭环，任务置「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 初版 `checks.tsv` 的 A3 行号写成 147（实为 150） | ✅已修 | 断言行号 147→150 | `A3 riscv …traps.c:150 has 'irqentry_enter_from_user_mode'` ok |
| 快照目录层级错位（`cp -r arch/dadao snapshot/arch/` ⇒ 落到 `snapshot/arch/*`） | ✅已修 | 先建 `snapshot/arch` 再拷 `arch/dadao` | 39 条 dadao 断言由 FAIL 全转 ok |
| item 计数按「项号+判决」去重，会把「一项两判决」重复计（42≠41） | ✅已修 | 改 `awk '!seen[$1]++'`（每项首行定判决） | `items=42` 与 `verdict` 之和 18+6+5+13=42 相符 |
| B11 首行判决写成 `same`（实际是 ucontext 布局 P2） | ✅已修 | 把 P2 行调到该项首行 | `verdict 5 P2`（A6/B11/D3/E2/E3） |
| `run.sh` 里 `nitem` 只增不用（`set -u` 下的定时炸弹） | ✅已修 | 删掉该变量与自增 | `grep nitem` 只剩统计 printf；`run.sh` rc=0 |
| `run.sh` 硬编码宿主源树路径打 HEAD（不可移植、且属运行期路径） | ✅已修 | 改为可选 `LIVE_TREE` 环境变量，缺省只打快照 HEAD | 不设变量 rc=0；`LIVE_TREE=…` 时同样 rc=0 |

### 第 1 轮 reviewer 验收（小改档）

**重跑（本人执行，输出/退出码为实测）**
1. 运行期证据目录内 `./run.sh` → `items=42 rows=76 failures=0`、`verdict 18 P0 / 6 P1 / 5 P2 / 13 same`、`RESULT: PASS (76 claims over 42 items)` **rc=0**；`./run.sh --inject` → 注入1 断言行号 FAIL、注入2 快照 md5 FAIL（各 rc=1）→ 还原后 `ok SNAP all 287 files match` + PASS，整体 **rc=0**。与完成区数字逐项一致。
2. 快照 ↔ 组件源检出按 `snapshot.md5` 逐文件 md5 比对（287 文件）**零差异**；检出 HEAD `c5f411a`、`git status` 干净 ⇒ 行号在 live 树同样成立。
3. **独立注入 2 路**（cp+md5 备份还原，未用 git checkout/restore）：① 改快照 `include/asm/ptrace.h:87` → `FAIL SNAP … 1 of 287 files differ` **rc=1** → 还原 md5 一致 → 回绿 **rc=0**；② 改快照 `kernel/syscalls.c:46`（`-EINVAL`→`-EPERM`）并同步 md5 清单 → `FAIL B7 … expected 'return -EINVAL' actual 'return -EPERM;'`、`RESULT: FAIL (1 of 76)` **rc=1** → 两处还原 md5 一致 → 回绿 **rc=0**。断言层与完整性层 FAIL 路径均可达。
4. 门控：`make check-knowledge-refs` **rc=0**（PASS，0 具体运行期引用、0 悬空）、`make check-tasks` **rc=0**（报告型「漏收尾 1」= 本任务待验收，不阻断）；**本记录写入后重跑 `check-knowledge-refs` rc=0**。

**行号抽查（`sed -n '<行>p'` 对 live 检出独立回读；P0/P1/P2 各 ≥2，共 30+ 处）**
- P0：`syscalls.c:44/46`、`syscalls.c:127-143`、`process.c:669`、`include/asm/ptrace.h:87`（`user_mode()` 81–87 全函数恒 `return 0;`）、`riscv/kernel/signal.c:499/534/310/341-350`、`kernel/entry/common.c:13/66/111`、`thread_info.h:47`、`mm/fault.c:702/735/764`、`kernel/traps.c:377/381`、`riscv/mm/fault.c:93/152`、`riscv/kernel/traps.c:129`、`riscv/process.c:232`、`riscv/traps.c:150`、uapi `ptrace.h:6`、`sigcontext.h:7` —— 全部命中。
- P1：`riscv/mm/fault.c:249`（`access_error` 定义）与 `:354-358`（`SEGV_ACCERR`）、`riscv/kernel/signal.c:585`、`riscv/Kconfig:174/623`、`arch/Kconfig:1770`、dadao Kconfig 无 `HAVE_GENERIC_VDSO`/`DYNAMIC_SIGFRAME` —— 命中。
- P2：`riscv/include/asm/elf.h:117`、`riscv/mm/fault.c:382`、`k5_syscall_selftest.c:694/721`、dadao uapi `Kbuild:5`、`riscv/ucontext.h:13`、`mm/fault.c:731` —— 命中；任务书「抽查」段 11 行两侧原文全部复现。**0 条失配。**
- 缺失类独立 grep（`arch/dadao` 全树 ×13 模式：`arch_do_signal_or_restart`/`get_signal`/`irqentry_`/`exit_to_user_mode`/`access_error`/信号帧 7 符号/`HAVE_GENERIC_VDSO`/`VDSO_SYMBOL`/`DYNAMIC_SIGFRAME`/`CONFIG_COMPAT`/`do_group_exit`/`arch_dup_task_struct`/`signal_minsigstksz`/`sigaltstack_size_valid`）**全空**；`arch/dadao/kernel/signal.c`、`include/asm/signal.h` 确不存在。

**5 条 P0 关键论断复核**（决定 027 工作量）
1. `arch_do_signal_or_restart` dadao 全树 0 命中；generic 确为 `__weak` 空体（`common.c:13`）⇒ 静默型成立；唯一调用点 `common.c:66` 所在 exit-to-user 工作循环因 dadao 全树无 `exit_to_user_mode` 而不可达 ⇒ **确无可达调用点**。
2. `syscalls.c:127-143`、`process.c:669` 逐行读过：只折 `ERESTART*`→`-EINTR` 并返回 stub 策略，**无 `ti_work`/TIF 消费**；dadao 全树 `TIF_SIGPENDING/TIF_NEED_RESCHED/_TIF_WORK_MASK` 仅 `thread_info.h` 定义 + `time.c:265` 注释，**无消费者** ⇒ 成立。
3. 信号帧整体不存在：无 `kernel/signal.c`；`rt_sigframe/get_sigframe/setup_rt_frame/setup_sigcontext/restore_sigcontext/handle_signal/signal_setup_done/save_altstack` 全树 0 命中 ⇒ 成立。
4. `sys_rt_sigreturn` 桩：`syscalls.c:44-46` 原文即声明 + 定义 + `return -EINVAL;` ⇒ 成立。
5. `user_mode(regs)` 恒 0：`include/asm/ptrace.h:81-87` 恒 `return 0;`；generic 分流点 `common.c:111` `if (user_mode(regs))` ⇒ 成立。

**与 m14-linux-035 交叉：不矛盾，同一事实两面**——035 讲「**将来走通用路径**时 `mm/memory.c:6665` 调用点被启用 ⇒ 恒 true 的闸必须在入口自补」（阶段 1 结论 A，需补权限闸）；039 讲「**现状**该 hook 与 generic 默认同值、私有通道不走 `:6665` ⇒ 不是今天 SIGSEGV 的成因」。默认值 vs 可用性/调用点；039 完成区亦明写「035 的结论成立」。riscv 无自实现（走 generic 默认），arm64/x86/powerpc 有自实现（arm64 `mmu_context.h:303`）——任务书原文准确。

**约束核验**：不改代码 ✓（`git show --stat HEAD` 仅任务书 1 文件；检出 HEAD `c5f411a` 且 `git status` 干净；注入只用 cp+md5）；快照与结论一致 ✓；术语「寄存器组」✓；本记录无具体运行期路径 ✓；完成区数字与实测逐项一致 ✓。

**发现（非阻断，交 architect 收尾改）**：结论行文「`include/asm-generic/mm_hooks.h:20-25` 同样 `return true`」——`:20` 是函数签名行、`return true` 实在 `:24`（同函数，指向正确），建议写 `:20-25`。另：派单提示转述「riscv 等 arch 有自实现」与事实不符（riscv 走 generic 默认），任务书原文无此错。

**判决：Accepted** —— 抽查 0 失配、5 条 P0 全部独立复核成立、2 路独立注入 FAIL 可达且还原回绿、门控 rc=0、约束无违反。
