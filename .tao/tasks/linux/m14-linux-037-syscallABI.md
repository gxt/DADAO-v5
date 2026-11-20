# m14-linux-037: syscall/ABI 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：2 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：待验收

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/kernel/syscall*.c`、`include/asm/syscall.h`、`unistd.h`、`uapi` 相关、`signal` 帧的 ABI 部分，以及 `arch/riscv/kernel/syscall*`、`arch/arm64/kernel/syscall*` 的对应实现（含参数传递、返回 errno 约定、`ptrace`/`seccomp` 钩子）。

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

**基线（只读，未改动）**：内核源码检出 HEAD = `c5f411a3a`（`v7.2.10` 之上一个 `dadao: linux patch series` 提交），读时工作树干净；该提交只动 `arch/dadao/`（88 个文件）+ `init/main.c`、`init/do_mounts.c`、`fs/exec.c`、`kernel/workqueue.c`、`usr/initramfs_data.S`，**未触 `arch/riscv` / `arch/arm64` / `kernel/ptrace.c` / `kernel/seccomp.c` / `kernel/entry/` / `include/asm-generic/`**，故两侧行号同为上游 `7.2.10`（`7b20d05fd`）基线，可比。号表另按 `scripts/syscall.tbl` 现场派生比对（该文件同样未被本补丁集改动）。

**枚举口径（现场派生）**：A＝`include/asm-generic/syscall.h` 的 9 个 hook 原型（DADAO 7/9，riscv 9/9，arm64 9/9）；B＝可选 arch hook 2 个（`syscall_handler`、`arch_syscall_is_vdso_sigreturn`；DADAO 0/2，riscv 2/2）；C＝`include/linux/entry-common.h` 的 syscall 进入/退出工作项 10 个（进入 6：user-dispatch／rseq-slice／ptrace-entry／seccomp／tracepoint／audit；退出 4：audit／tracepoint／ptrace+step／`syscall_exit_work`；DADAO 引用数 **0**）；D＝syscall 相关 Kconfig 门 7 个（DADAO `select` 1/7）；E＝号表/UAPI 6 项（abi 集／号值真源／号段差／argmask／compat／信号帧）。共 34 项，命中差异 25 条：**P1 10 条、P2 15 条、P0 0 条**（无一阻塞在跑的 `m14-linux-035`）。

### ① 缺失 hook（4）

1. **`syscall_get_error()` 未实现**：`arch/dadao/include/asm/syscall.h:66-124`（全文只有 7 个 hook，无此函数）↔ `arch/riscv/include/asm/syscall.h:46-52`、`arch/arm64/include/asm/syscall.h:43-49`。后果：`PTRACE_GET_SYSCALL_INFO` 的 `exit.rval`（`kernel/ptrace.c:984`）无来源。**P1**。
2. **`syscall_rollback()` 未实现**：同上 ↔ riscv:40-44、arm64:26-30。后果：`kernel/seccomp.c:1289,1364` 与 `kernel/entry/syscall_user_dispatch.c:66` 一旦启用即无符号可用；且 DADAO 的 `rd8` 不是参数寄存器，其语义应是**空实现**，不能照抄 `regs->a0 = orig_a0`。**P2**。
3. **`arch_syscall_is_vdso_sigreturn()` 未实现** ↔ riscv:115-118。后果：无 vdso `sigreturn` 判定（当前无 vdso，故无实害）。**P2**。
4. **`syscall_handler()` 与带类型表项缺失**：`arch/dadao/include/asm/syscall.h` 无 ↔ riscv:100-113；DADAO 在 `arch/dadao/kernel/syscalls.c:99-108` 内联 nospec+范围检查（**等价**），但表项以 `long call(void)` 声明（`arch/dadao/kernel/syscall_table.c:24`）而定义是 `sys_x(const struct pt_regs *)`（`arch/dadao/include/asm/syscall_wrapper.h:47-63`）↔ riscv 表项用真实签名（`arch/riscv/kernel/syscall_table.c:15`）⇒ CFI/LTO 开启时会被拒。**P2**。

### ② 语义不符（8）

5. **`syscall_set_return_value()` 把 `error` 再取负（真 bug）**：`arch/dadao/include/asm/syscall.h:88`（`error ? -error : val`）↔ `arch/riscv/include/asm/syscall.h:64`（`error ?: val`）、`arch/arm64/include/asm/syscall.h:51-62`。按 `include/asm-generic/syscall.h:100-105`，`@error` **已是负值**（seccomp 传 `-ENOSYS`/`-data`：`kernel/seccomp.c:1283,1301`；ptrace：`kernel/ptrace.c:1115`）⇒ DADAO 会写出**正的** errno，用户读到"成功 + 正数"。**P1**。
6. **`syscall_get_arguments()` 只返回数据组前 6 槽**：`arch/dadao/include/asm/syscall.h:101-109` ↔ riscv:67-77（a0–a5 位置全量）。地址参数实际在 `rb16+`（`contract-syscall §3`），而 audit 取前 4 参（`include/linux/entry-common.h:67-68`）、tracepoint/seccomp 取 6 参 ⇒ 参数整体错位；`syscall_set_arguments()`（同文件 111-119）同病。**P1**。
7. **`user_mode()` 恒返回 0**：`arch/dadao/include/asm/ptrace.h:81-88` ↔ riscv 按 `status` 判。任何通用 user/kernel 判定（信号投递、页故障升级、ptrace）都会走错分支；根因是入口帧没保存 `excp_prev_run_mode`（`contract-syscall §8` 的 cg5 现场字段清单也未列它）。**P1**。
8. **`sys_rt_sigreturn` 恒 `-EINVAL`**：`arch/dadao/kernel/syscalls.c:43-47` ↔ riscv 真实现（`arch/riscv/kernel/signal.c`）。当前是"诚实桩"，但语义上应终止进程（SIGSEGV）而非返回可继续的 EINVAL。**P2**（027 替换）。
9. **信号帧 ABI 三处口径不一**：内核 uapi = `rd[32]/rb[32]/ra[8]/ip/status`（`arch/dadao/include/uapi/asm/ptrace.h:5-11`，592 B）↔ 027 已裁定 `rd[64]/rb[64]/ra[64]/rf[64]`＝2048 B、`rb[0]` 即 IP、无 `status`（`.tao/tasks/linux/m14-linux-027-信号与退出面.md:53`）↔ musl 组件源码 `arch/dadao/bits/signal.h:37`（临时 `__gregs[129]`）；`struct sigcontext` 随 uapi 为 `regs + __unused[4]`（`arch/dadao/include/uapi/asm/sigcontext.h:7-10`）↔ riscv `sc_regs + sc_fpregs`（`arch/riscv/include/uapi/asm/sigcontext.h:31-37`）。**P1**（027 落地前必须收敛，否则 ptrace/coredump/sigreturn 各说一套）。
10. **`pt_regs` 的 `rb[0]` 与 `ip` 双份且注释相反**：`arch/dadao/include/asm/ptrace.h:21-22` 称 "rb0 stays 0"，实际 `arch/dadao/kernel/traps.c:402` 写 `rb[0] = ip`。**P2**（与 #9 同笔收口）。
11. **`PTRACE_SYSEMU`/`_SINGLESTEP` 占号 101/102**：`arch/dadao/include/uapi/asm/ptrace.h:13-15`（注释自称 "stay reserved"）↔ riscv 不定义、arm64 用 31/32（`arch/arm64/include/uapi/asm/ptrace.h:77-78`）⇒ UAPI 承诺了不支持的请求号。**P2**。
12. **ELF core 的 gregset = 整个 `pt_regs`（258 词）**：`ELF_NGREG` = `sizeof(pt_regs)/8`（`arch/dadao/include/asm/elf.h:38`），无 `ELF_CORE_COPY_REGS`，走 `include/linux/elfcore.h:82-83` 原样拷贝 ↔ riscv 拷 `user_regs_struct`（`arch/riscv/include/asm/elf.h:129-133`）⇒ coredump 布局 = 内部帧（含 `ra`/`rf`/`status`），与 #9 的 027 裁定不一致。**P2**。

### ③ 旁路 vs 通用（4）

13. **用户 syscall 全链路绕过 generic entry/exit（本任务最大项）**：`arch/dadao/kernel/process.c:662-669`（`dadao_user_syscall` → `dadao_call_syscall` → `dadao_user_syscall_post`）↔ `arch/riscv/kernel/traps.c:336,342,345`（`syscall_enter_from_user_mode` → `syscall_handler` → `syscall_exit_to_user_mode`）。后果：`include/linux/entry-common.h` 的 `:68`（audit entry）、`:82`（user dispatch）、`:96`（ptrace entry）、`:106`（seccomp）、`:115`（tracepoint entry）、`:244/247/251`（audit/trace/ptrace exit）与 `syscall_exit_to_user_mode_work()` 的 TIF 工作**全部不执行**（C 组 10/10 缺失）。**P1**，027/032–034 的硬前置。
14. **`syscall_work` 位图有名无实**：`struct thread_info.syscall_work` 已在（`arch/dadao/include/asm/thread_info.h:19`），但仍定义旧接口 `TIF_SYSCALL_*`/`_TIF_SYSCALL_WORK`（同文件 60-63、83-90）；7.2.10 已改用 `SYSCALL_WORK_*` 位图（`include/linux/thread_info.h:42-59`），而 DADAO 无任何置位/检查点。**P2**。
15. **没有 syscall 重启的等价物**：上游入口先用 `regs->epc += 4`、返回时按需回退（`arch/riscv/kernel/traps.c:330`）；DADAO 用 resume policy（`arch/dadao/kernel/trap.S:100-118`），但 post 恒 `SKIP`（`arch/dadao/kernel/syscalls.c:142`）⇒ `ERESTART*` 一律降级 `-EINTR`（同文件 131-138），"重新执行该系统调用"路径缺失。**P1**（027 的 restart 依赖）。
16. **ptrace 架构面全是桩**：`arch_ptrace` 恒 `-EIO`（`arch/dadao/kernel/traps.c:618-623`）、`ptrace_disable` 空（同 625-627）、`elf_core_copy_task_fpregs` 恒 0（629-633）↔ `arch/riscv/kernel/ptrace.c:544+`。**P1**（与 #17 同源）。附：参数分 bank + 只传 frame 指针的 `dadao_call_syscall`（`arch/dadao/kernel/trap.S:328-334`、`arch/dadao/kernel/syscall_argmask.c:231-247`）是 C′ 裁定的**有意设计**，与 `contract-syscall §3` 一致，**不属旁路**。

### ④ Kconfig 缺口（4）

17. **缺 `select HAVE_ARCH_TRACEHOOK`**：`arch/dadao/Kconfig:10-23`（全文 7 个 select）↔ `arch/riscv/Kconfig:148`、`arch/arm64/Kconfig:173` ⇒ `kernel/ptrace.c:897-1160` 整段不编译，`PTRACE_GETREGSET/SETREGSET`（1357-1358）与 `PTRACE_GET_SYSCALL_INFO`（1375）落到 default `-EIO`；同时是 #1 无编译错误的**原因**。**P1**。
18. **缺 `HAVE_ARCH_SECCOMP_FILTER`（连带 `HAVE_ARCH_SECCOMP`）** ↔ riscv:145、arm64:171 ⇒ `CONFIG_SECCOMP` 不可选（`arch/Kconfig:647-651`）；启用还需 `asm/seccomp.h` 的 `SECCOMP_ARCH_NATIVE{,_NR,_NAME}`（`arch/riscv/include/asm/seccomp.h:11-17`），DADAO 无此文件。**P2**。
19. **缺 `HAVE_ARCH_AUDITSYSCALL`** ↔ riscv:130、arm64:151 ⇒ `CONFIG_AUDITSYSCALL` 不可选（`init/Kconfig:553-559`）；即使可选，#6 也让 audit 参数错。**P2**。
20. **缺 `HAVE_SYSCALL_TRACEPOINTS` / `GENERIC_ENTRY` / `HAVE_RSEQ`** ↔ riscv:204/112/199、arm64:229/225 ⇒ `FTRACE_SYSCALLS` 不可选（`kernel/trace/Kconfig:599`）、generic entry 不可得（#13 无法用通用件补齐）、rseq(293) 恒 `-ENOSYS`（`init/Kconfig:1988-1991`）。**P2**。

### ⑤ 号表与 UAPI 覆盖（5）

21. **号表 abi 集缺 3 个（5 个号落到 `sys_ni_syscall`）**：`arch/dadao/kernel/Makefile.syscalls` **不存在** ⇒ 用默认 `common,64`（`scripts/Makefile.asm-headers:18-23`）↔ `arch/riscv/kernel/Makefile.syscalls:3-4`（riscv/rlimit/memfd_secret）、`arch/arm64/kernel/Makefile.syscalls:3-4`。现场派生：DADAO 表 472 条项（`__SYSCALL(` 416 + `__SYSCALL_WITH_COMPAT` 56）、最大号 471、151 个 `sys_ni_syscall`，两侧 `diff` 只差 5 个号。**`258/259`（riscv_hwprobe/riscv_flush_icache）是 `contract-syscall §1.3` 明文要求沿用**，现落到 `sys_ni_syscall` ⇒ **P1**。
22. **另外 3 个号同样缺失（P2）**：`163/164`（getrlimit/setrlimit，riscv 走 `rlimit` abi）、`447`（memfd_secret）在 DADAO 表里都是 `sys_ni_syscall`（同一 abi 集缺口，见 #21）↔ `arch/riscv/kernel/Makefile.syscalls:3-4`。后果：这三个号恒 `-ENOSYS`；musl 走 `prlimit64` 故当前无实害。**P2**。
23. **号值双真源（今日一致，有漂移风险）**：`__NR_*` 取自 `include/uapi/asm-generic/unistd.h`（`arch/dadao/include/uapi/asm/unistd.h:8`），表取自 `scripts/syscall.tbl` 生成（`arch/dadao/include/asm/syscall_table.h:12`）↔ riscv 两者同源（`arch/riscv/include/uapi/asm/unistd.h:20` 取生成的 `unistd_64.h`）。现场核：`__NR_syscalls`=472 两侧一致、312 个同名号值 0 冲突。**P2**。
24. **argmask 只到 452，428–471 段仅 439/452 有掩码**：`arch/dadao/kernel/syscall_argmask.c:48-222`（173 行）。`clone3(435)`/`open_tree(428)`/`openat2(437)`/`mount_setattr(442)`/`landlock_*(444-446)`/`statmount(457)` 等首参为指针却 mask=0 ⇒ 按 `contract-syscall §3`（指针入 RB）本应走 `rb16`，实际从 `rd16` 读；与 musl/QEMU 同源默认一致（自洽但违契约），需 ABI 侧裁定后统一补表。**P2／待裁定**。
25. **无 compat 路径**：无 `compat_sys_call_table`、无 `CONFIG_COMPAT`、无 `__NR_*_32` ↔ `arch/riscv/include/asm/syscall.h:20,105-109`。**P2**（v5 未定义 32 位 ABI；若 M15 要 ILP32 需整体补）。

> **不改代码**：本次只读（未 apply/reset/make/仿真），`git status -uall` 只列本任务书。**P0 = 0**：无一条阻塞在跑的 `m14-linux-035`；#13/#15/#17 是 `m14-linux-027`（待开始）的硬前置，整改顺序建议 17→13→15→5→6→7→9。

## 审阅记录

### 第 1 轮 engineer 自审

本任务交付物是盘点结论（无代码），故自审＝**逐条回读**：把全文 59 处 `路径:行` 引用用脚本抽出来、逐行 `sed` 回读原文（1 处 MISSING 是 musl 组件路径，不在内核树，已单独核对），并复核每个计数/号值的派生口径。发现与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| A1 号表条目数按 `^__SYSCALL(` 数成 416，漏掉 56 条 `__SYSCALL_WITH_COMPAT` | ✅已修 | 口径改为 `^__SYSCALL` 全族：472 条项（416+56），最大号 471 | `grep -cE '^__SYSCALL'` 两侧均 472；两侧 `diff` 仍只 5 行 |
| A2 首版把 258/259 与 163/164/447 压进同一条，P1/P2 计数与条数对不上（24 条 vs 9+15） | ✅已修 | 拆为 #21（258/259，P1）与 #22（163/164/447，P2）⇒ 25 条 / P1 10 / P2 15 | `grep -c '\*\*P1\*\*'`=11（含汇总行）、`\*\*P2`=16（含汇总行） |
| A3 musl 文件写成 `musl/arch/...`，在「内核树相对路径」语境下易误读 | ✅已修 | 改为「musl 组件源码 `arch/dadao/bits/signal.h:37`」并 `sed` 回读确认 `__dadao_mc_gp_state[129]` | 该行原文＝`typedef unsigned long __dadao_mc_gp_state[129]; …` |
| A4 `pt_regs` 的 rb0 注释引 `:21-22` 跨两行，需确认 rb0 那句在第 22 行 | ✅已核 | 引用范围保留（21=rd0、22=rb0），措辞限定为「称 rb0 stays 0」 | 22 行原文＝`*   rb[0..63]  rb0 stays 0 (it is the read-only IP, mirrored into \`ip\`)` |
| A5 「P0=0」需证否：确认无条目命中在跑的 035（mm 缺页） | ✅已核 | 保留 P0=0；未把「用户态页故障→SIGSEGV 旁路」列为本任务条目（该面由 035 承接，避免重复立项） | 25 条均落在 syscall / 号表 / 信号帧 ABI 面，无一条指向 `mm/fault.c` |

### 第 1 轮 reviewer 验收

判决：**Accepted**。以下全部由 reviewer 自行重跑（内核源码检出 HEAD `c5f411a3a`、读时 0 改动），不采信完成区转述。

1. **行号抽查 16 条、0 条对不上**（P1 #1/#5/#6/#7/#13/#17，P2 #8/#10/#14/#21/#24/#25，另补 #2/#3/#9/#11/#12），逐条 `sed -n '<行>p'`：
   - `arch/dadao/include/asm/syscall.h:88` = `	regs->rd[8] = error ? -error : val;` ↔ `arch/riscv/include/asm/syscall.h:64` = `	regs->a0 = (long) error ?: val;`
   - `arch/dadao/include/asm/syscall.h:101-109`（`:108` = `		args[i] = regs->rd[16 + i];`）↔ riscv `:67-77`（`:71` = `	args[0] = regs->orig_a0;`）
   - `arch/dadao/kernel/process.c:662-669` ↔ `arch/riscv/kernel/traps.c:336/342/345`（`syscall_enter_from_user_mode`/`syscall_handler`/`syscall_exit_to_user_mode`）
   - `arch/dadao/Kconfig` 7 个 `select`（11/12/13/14/15/17/22 行）↔ riscv `:148`、arm64 `:173` = `select HAVE_ARCH_TRACEHOOK`
   - `kernel/ptrace.c:984`；`include/linux/entry-common.h:67-68` 及 `:82/:96/:106/:115/:244/:247/:251`；`uapi/asm/ptrace.h:6`、`:14-15`（101/102）；`asm/elf.h:38`；`kernel/traps.c:402` = `	regs->rb[0] = regs->ip;`；`kernel/seccomp.c:1289/1364`、`kernel/entry/syscall_user_dispatch.c:66`、`riscv/include/asm/syscall.h:46-52/115-118` —— 均与所述内容一致。
2. **#5 查实（真 bug）**：`include/asm-generic/syscall.h:103` 明写 `@error: negative error code`；`kernel/seccomp.c:1284` 传 `-data`、`:1303` 传 `-ENOSYS`、`kernel/ptrace.c:1115` 传负 rval ⇒ DADAO 的 `-error` 会写出**正 errno**，riscv `(long)error ?: val` 不会。**今日无调用者 ⇒ 潜伏**：`CONFIG_SECCOMP` depends `HAVE_ARCH_SECCOMP`（`arch/Kconfig:647-650`，DADAO 未 select）、`ptrace.c:1115` 在 `#ifdef CONFIG_HAVE_ARCH_TRACEHOOK`（`:897-1160`）、`lib/syscall.o` 由 `lib/Makefile:203` 挂同一开关、`syscall_user_dispatch.o` 由 `CONFIG_GENERIC_SYSCALL` 决定，三者在当前 `.config` 均无；`arch/dadao` 树内调用者 **0**。
3. **#6 查实（同为潜伏）**：`contract-syscall §3`（第 63 行）确为「数据 `rd16–rd31`、地址 `rb16–rb31`、浮点 `rf16–rf31`…不共享槽位」，而 `syscall_get_arguments` 只读 `rd16+`；四个消费点（`entry-common.h:67`、`include/trace/events/syscalls.h:31`、`kernel/seccomp.c:256`、`kernel/ptrace.c:951`）分别被 AUDITSYSCALL/FTRACE_SYSCALLS/SECCOMP/HAVE_ARCH_TRACEHOOK 挡住（#18/#19/#20 已自述），且 DADAO 0 次进入 generic entry ⇒ 今日无消费者。**两条均非 P0，原分级 P1（启用后即错）维持**。
4. **#13 的 10 个工作项符号 `grep -c` 现场全 0**：`syscall_user_dispatch`/`rseq_syscall_enter_work`/`arch_ptrace_report_syscall_entry`/`__secure_computing`/`trace_syscall_enter`/`syscall_enter_audit`/`audit_syscall_entry`/`audit_syscall_exit`/`trace_syscall_exit`/`arch_ptrace_report_syscall_exit`/`syscall_exit_to_user_mode_work` 均 0；`arch/dadao` 对 `enter_from_user_mode`/`exit_to_user_mode*`/`get_signal`/`resume_user_mode_work` 亦 0。**与「`arch_do_signal_or_restart` 全树无」同一根因**（缺通用 entry/exit 循环）：该符号上游唯一调用点 = `kernel/entry/common.c:66`，`:13` 另有 `__weak` 空桩 ⇒ 不报链接错、静默不投递。注：039 任务书现为「待开始」、完成区空、未见该表述，此结论系我独立 grep 所得。
5. **号表 5 号**：`arch/dadao/kernel/Makefile.syscalls` **不存在**（`ls` rc=2）⇒ 默认 `common,64`（`scripts/Makefile.asm-headers:19`）；`arch/riscv/kernel/Makefile.syscalls:4` = `syscall_abis_64 += riscv rlimit memfd_secret`；`contract-syscall §1.3`（48-49 行）明文「沿用 RISC-V 号表 ⇒ 该段随表一并沿用」「直接沿用 RISC-V 的 arch-specific 号（`riscv_hwprobe`/`riscv_flush_icache`）」⇒ **258/259 确为契约要求**。我方重跑 `scripts/syscalltbl.sh`：DADAO 表 472 行（`__SYSCALL(` 416 + `__SYSCALL_WITH_COMPAT(` 56）、`sys_ni_syscall` 151、最大号 471，与 riscv abi 集 `diff` **恰 5 行 = 163/164/258/259/447**；`__NR_syscalls`=472（`include/uapi/asm-generic/unistd.h:867`）。
6. **计数**：结论段 25 条，`**P1**` 10 + `**P2**` 14 + `**P2／待裁定**` 1 ⇒ **P1 10 / P2 15 / P0 0**，与完成区一致。
7. **门控（我方真实退出码）**：`make check-knowledge-refs` → `PASS`、**rc=0**；`make check-tasks` → 报告型、**rc=0**（①「完成区已填但待验收」1 条即本任务，属正常阶段）。**反例注入**：给本任务书追加一行含具体运行期路径的引用 → 门控 `FAIL`、**rc=2** 并点名该行 → `cp` 备份还原、md5 与注入前相等 → **回绿 rc=0**。
8. **约束核验**：① 未改代码——`git show --stat HEAD` 仅本任务书（+83/−2），`git status --porcelain -uall` 空；② 术语用「寄存器组」；③ 本记录无具体运行期路径（写入后已重跑门控见第 7 条）。

**Finding（不阻断，交 architect 收尾改）**：结论段行数按 40–86 行计 47、含末尾空行计 48，完成区写 48 属口径差异（≤80 判据不受影响）；#5/#6 措辞宜补「启用后」限定，避免读成今日已错。

## 完成区

**测试结果**：只读任务，无测试套件；验收 4 项全过——①结论 ≤80 行（实测 48 行）；②覆盖现场派生（34 项 / 25 条，口径见结论头部）；③抽查 5 条 `sed -n` 双侧原文（下）；④`git status -uall` 只列本任务书。

**修改文件**：`.tao/tasks/linux/m14-linux-037-syscallABI.md`（写入「盘点结论」+ 本节，无代码改动）。

**验收结果**（真实输出）：
- 基线：组件源码检出 `git rev-parse HEAD` = `c5f411a3a1b1b98d0cd2f6e5e26ec1476a391982`（`describe` = `v7.2.10-1-gc5f411a3a`），`git status --porcelain -uall` = 0 行；`git show --name-only` 核该提交未触 `arch/riscv`/`arch/arm64`/`kernel/ptrace.c`/`kernel/seccomp.c`/`kernel/entry/`/`include/asm-generic/`/`scripts/syscall.tbl`，故两侧行号同为上游 `7.2.10` 基线。
- 号表派生：`./scripts/syscalltbl.sh --abis common,64 scripts/syscall.tbl …` ↔ `--abis common,64,riscv,rlimit,memfd_secret`，`diff` 仅 5 号（163/164/258/259/447）；DADAO 472 条表项、151 个 `sys_ni_syscall`、`__NR_syscalls`=472，与既有构建树生成头逐字节相同。
- 计数派生：asm-generic hook 9 个→DADAO 7；可选 arch hook 2 个→0；entry/exit 工作项 10 个→`arch/dadao` 引用 0；Kconfig 门 7 个→`select` 1；argmask 173 行、428–471 段仅 439/452。
- 抽查 S1：`arch/dadao/include/asm/syscall.h:88` = `	regs->rd[8] = error ? -error : val;` ／ `arch/riscv/include/asm/syscall.h:64` = `	regs->a0 = (long) error ?: val;`
- 抽查 S2：`arch/dadao/include/asm/syscall.h:108` = `		args[i] = regs->rd[16 + i];` ／ `arch/riscv/include/asm/syscall.h:71` = `	args[0] = regs->orig_a0;`
- 抽查 S3：`arch/dadao/Kconfig:17` = `	select ARCH_HAS_SYSCALL_WRAPPER` ／ `arch/riscv/Kconfig:148` = `	select HAVE_ARCH_TRACEHOOK`
- 抽查 S4：`arch/dadao/kernel/process.c:669` = `	return dadao_user_syscall_post(regs);` ／ `arch/riscv/kernel/traps.c:345` = `		syscall_exit_to_user_mode(regs);`
- 抽查 S5：`arch/dadao/include/uapi/asm/ptrace.h:6` = `	unsigned long rd[32];` ／ `arch/riscv/include/uapi/asm/ptrace.h:26` = `	unsigned long pc;`

**新发现/坑**：
- 「缺失 hook」与「Kconfig 缺口」耦合：未 select `HAVE_ARCH_TRACEHOOK` ⇒ `syscall_get_error` 缺失**不报编译错**（`kernel/ptrace.c:897-1160` 整段被裁）；排期须成套处理，否则单补 hook 是死代码。
- 7.2.10 已把 syscall work flags 从 `_TIF_SYSCALL_*` 迁到 `thread_info.syscall_work` + `SYSCALL_WORK_*`；DADAO 仍写旧宏，照旧接口补入口会写到没人读的位。
- 号值有**两个真源**（uapi `asm-generic/unistd.h` 给号，`scripts/syscall.tbl` 给表）；今日 0 冲突，补 abi 时必须同改两处。
- 组件源码树读时正被在跑任务使用：仅只读（未 apply/reset/make），结论已锚定 HEAD，滚动后须按该 HEAD 复核。
**遗留问题**：是否立即整改由用户裁定（「是否立刻整改，我来定」）；#24（argmask 428–471）需先裁定「上游新增号的指针参是否一律入 RB」。
