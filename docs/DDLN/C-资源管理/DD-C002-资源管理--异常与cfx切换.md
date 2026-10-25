# 资源管理 -- 异常与cfx切换

**本册要点**

- 异常进入保存 prev mode/mask，切到 `switch_run_mode`/`switch_cfx_mask`，跳 cfx 向量。
- `trap` 进入；`escape` 用 `excp_cause_ip + (imms18 << 2)` 返回。
- 同步异常给 cause id；异步中断置 `excp_pending`（OR、写 0 清）。
- 多 pending 的优先级由实现决定；`excp_prev_*` 只有一级。
- `excp_cause_nonmaskable` 不受 mask 控制。
- cfx 访问权限（`ILLI`）与 PTBR 权限（`PERM`）是两层。
- 多 hart：per-hart cfx 隔离；共享 cfx 需软件仲裁。

## 1. 为什么异常进入要切换 mode 和 cfx mask？

**答：** 因为异常进入后要按“目标 cfx 的权限上下文”运行，而不是沿用异常前的 mode/mask；`switch_run_mode`/`switch_cfx_mask` 给出进入后的模式与掩码。

- **进入时保存**：prev mode、prev cfx mask、cause id/ip/info、pending。
- **进入时切换**：mode ← `cfx_<name>_<mode>_switch_run_mode`；mask ← `cfx_<name>_<mode>_switch_cfx_mask`。
- **为什么**：handler 可能跑在更高权限；mask 决定 handler 内还能触发哪些 cfx 指令，防止同类异常反复打断。
- **各模式字段**：`user`/`jail`/`supv` 在 `cg0`，`hypv` 在 `cg3`。
- **对比**：x86 ring 切换 + IST；ARM EL 切换；RISC-V M/S/U 切换；MIPS kernel/user；SPARC trap level；PowerPC MSR。

## 2. `trap`/`escape` 的进入/退出路径怎么走？

**答：** `trap` 走异常进入流程，保存现场并跳到 `cfx_<name>_<mode>_excp_vector`；`escape` 恢复 prev mode/mask，按 `excp_cause_ip + (imms18 << 2)` 返回。

- **`trap cfx, immu18`**：`cfxha` 指定目标 cfx；`immu18` 是功能号/原因；进入该 cfx 的向量。
- **`escape cfx, [excp_cause_ip, imms20]`**：`imms20` 是字节偏移，须 `%4==0`；编码层是 `imms18 << 2`。
- **返回地址**：以 `excp_cause_ip`（被陷入指令的地址）为基准，而不是当前 PC；`escape ..., 4` 返回 trap 的下一条。
- **为什么**：handler 可能在别的 cfx/地址空间运行；用 `excp_cause_ip` 做基准，返回位置由软件控制。
- **对比**：x86 `IRET`；ARM `ERET`；RISC-V `MRET`/`SRET`；MIPS `ERET`；SPARC `RETT`；PowerPC `RFI`。

## 3. 同步异常和异步中断怎么统一到 cfx？

**答：** 都落到同一个 cfx 的 `excp_pending` + cause 机制：同步异常直接给 cause id/ip/info；异步中断先置 pending 位，再按 mask 进入。

- **`excp_pending`**：待处理异常/中断位图，one-hot，OR 语义，写 0 清位。
- **同步异常**：`excp_cause_id`（one-hot）、`excp_cause_ip`、`excp_cause_info`。
- **异步中断**：设备/定时器置 pending；进入后按 cause 表分派。
- **mask**：global mask + 指令类型 mask + switch mask；0=可触发、1=屏蔽。
- **对比**：x86 IDT + APIC；ARM EL 向量 + GIC；RISC-V trap 向量 + PLIC；MIPS 异常入口；SPARC trap table；PowerPC 异常向量。

## 4. 多个 pending 同时置位先处理谁？handler 内再异常怎么办？

**答：** 规范给的是 pending 位图，不规定固定优先级；同一时刻多个 pending 的处理顺序由实现决定，软件应先读 pending 再分派。`excp_prev_*` 只有一份，handler 内再异常要靠软件保存/恢复。

- **优先级**：规范未给固定优先级；不同实现可按 cause 编号、硬件优先级或软件策略选择（具体需查实现手册）。
- **嵌套**：`excp_prev_run_mode`/`excp_prev_cfx_mask` 只有一份；嵌套 handler 必须先保存上一层的 prev 状态。
- **重入**：同一 cfx 的 handler 内再触发同一 cfx，会覆盖 prev 状态；软件要么屏蔽，要么换栈/换 cfx。
- **不可屏蔽**：`excp_cause_nonmaskable` 不受 mask 控制，保证致命错误能进入。
- **对比**：x86 APIC 优先级/NMI；ARM GIC 优先级/FIQ；RISC-V PLIC 优先级；MIPS 中断优先级；SPARC trap level；PowerPC 异常优先级。

## 5. `excp_cause_nonmaskable` 为什么不可屏蔽？

**答：** 它是硬件按 cause 表静态设置的不可屏蔽位图；这些异常不受 cfx mask 控制，保证致命错误一定能进入 handler。

- **只读**：`excp_cause_nonmaskable` 由硬件设置，软件只读。
- **作用**：与普通 mask 相与时，nonmaskable 位不被屏蔽。
- **典型**：硬件错误、不可恢复的异常；具体 cause 表由各 cfx 定义。
- **对比**：x86 NMI；ARM FIQ/SError；RISC-V 的 NMI（若实现）；MIPS 的 NMI；SPARC 的 error mode；PowerPC 的 machine check。

## 6. cfx 访问权限（ILLI）和 PTBR 权限（PERM）为什么是两个层次？

**答：** 因为两者检查的对象不同：cfx 访问权限决定“能不能执行这条 cfx 指令”（不通过 → `ILLI`）；PTBR 权限决定“当前模式能不能访问这个 VA 对应的地址空间”（不通过 → `PERM`）。

- **cfx 访问权限**：global mask + 指令类型 mask；不允许 ⇒ `ILLI`。
- **PTBR 权限**：`cfx_ptw_user/jail/supv/hypv_perm`；不允许 ⇒ `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`。
- **顺序**：先检查指令是否允许执行，再做地址转换/PTBR 权限检查。
- **为什么分开**：一个是“指令级”权限，一个是“地址空间级”权限；混在一起会让异常原因不清。
- **对比**：x86 CPL/IOPL vs 页表 U/S；ARM EL vs PTE AP；RISC-V 模式 vs PTE U；MIPS kernel/user vs TLB；SPARC trap level vs MMU；PowerPC MSR vs 页表。

## 7. 多 hart 时，异常进入/退出怎么隔离？共享 cfx 的 pending 怎么处理？

**答：** per-hart cfx（0–15）的异常状态是 per-hart 的，天然隔离；共享 cfx（如 `llc`）的 pending/状态由共享资源维护，需要软件仲裁或 IPI。

- **per-hart**：`cfx0`–`cfx15` 每个 hart 独立；prev 状态、pending、mask 都是本 hart 的。
- **共享 cfx**：`llc` 跨 hart 共享；对共享寄存器的读写要考虑并发。
- **IPI**：`hart` cfx 提供核间中断原因码；用 `trap`/pending 通知另一个 hart。
- **软件**：共享 cfx 的 pending 由谁清、谁处理，需要软件约定；不要假设“一个 cfx 只有一份状态”。
- **对比**：x86 per-CPU IDT/APIC；ARM per-core GIC；RISC-V per-hart CLINT/PLIC；MIPS per-core 中断；SPARC/ PowerPC 的 per-CPU 异常状态。

## 背景知识

### 术语与概念

- **同步异常**：由当前指令直接触发（非法指令、地址未对齐、缺页等），`excp_cause_ip` 指向该指令。
- **异步中断**：与当前指令无直接关系，通过 pending 位等待处理。
- **`excp_pending`**：待处理异常/中断位图，one-hot，OR 语义，写 0 清位。
- **nonmaskable**：不可屏蔽异常，不受普通 cfx mask 控制。
- **嵌套/重入**：handler 内再次异常；`excp_prev_*` 只有一级，嵌套要靠软件保存。
- **精确异常**：异常时 `excp_cause_ip` 指向出错指令，处理后可从该指令重新执行。

### 对照

**x86-64**：异常/中断经 IDT 进入，ring 切换；`IRET` 返回；NMI 不可屏蔽；APIC 管中断优先级。

**ARM64**：异常按 EL 进入对应向量；`ELR`/`SPSR` 保存返回地址与状态；`ERET` 返回；FIQ/SError 可作高优先级。

**RISC-V**：trap 向量 + `mepc`/`mcause`/`mtval`；`MRET`/`SRET` 返回；M/S/U 模式；PLIC 管外部中断。

**MIPS**：统一异常入口；CP0 `Cause`/`EPC`；`ERET` 返回；kernel/user 两种模式。

**SPARC**：trap table + `TBR`；trap level 表示屏蔽层级；`RETT` 返回；窗口溢出/下溢是特殊 trap。

**PowerPC**：异常向量 + `SRR0`/`SRR1`；`RFI` 返回；MSR 管模式与中断；machine check 不可屏蔽。
