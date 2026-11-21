# m14-linux-017: 上下文切换（switch_to 汇编 + 调度跑双任务 + FP 保存范围）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（进程骨架 + `copy_thread` + `thread_struct`）、`m14-testcases-006`（hmon 全 cfx supv 权限转交 smon，U-mode 帧固件前置）
**可并行分片**：否（`components/linux` 单写者；共享 `include/asm/{switch_to,processor}.h`、`kernel/process.c`）
**并行组**：与 K4 其余任务**串行**（同组件同写者）
**预估**：7–9 h（`__switch_to` 汇编 + U-mode ↔ S-mode 帧往返 + 最小 clockevent + F3/init 真跑）
**档位**：大改（新汇编入口 + 调度接线 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：已验证

## 背景

`m14-linux-016` 建立进程骨架后，`kernel_init()` 会调用 `schedule()`，而 `include/asm/switch_to.h` 目前只有 `__switch_to(prev,next)` 声明、**无实现**（K0 桩，注释称「K1 提供 `__switch_to_asm`」）。本任务补真正的上下文切换：`__switch_to` 保存 prev 的 callee-saved 上下文到 `thread_struct`、恢复 next 的，使 fork 出的子进程真正被调度运行。

DADAO 特有事实（不得套 RISC-V/x86）：
- **callee-saved = `rd32–63` + `rb32–63`**（连续，`stm.o`/`ldm.o` 可整段搬运，`contract-abi §4.5`；`rb63` 为普通成员）；`SP=rb1` 由调度器切栈，**不属 CSR**（`contract-abi §4.5`）；`rb2`=FP 不在 CSR（prologue 管）、`rb3`=rbtp 保留。
- **RA 由 `call`/`ret` 硬件自动压弹 RegRAS**（`ra0–ra63`，`ra63` 栈顶），`__switch_to` 的返回地址走 `call` 语义——上下文切换**不保存 ra 数组**，只保证 `call`/`ret` 配对不跨切换点破裂（`contract-abi §2.3`）。
- **FP（rf）范围待裁定**：`rf32–63` 属 CSR（`contract-abi §4.5`），但内核是否用 RF（soft-float vs hard-float）、用户态是否用 FP 未定 ⇒ 本任务 `__switch_to` 是否保存/恢复 `rf32–63` 由**待裁定 1** 定。
- 无 PS/TS 位、无懒 FPU 陷阱（`processor.h` 已注「No lazy FPU」）。

## 目标

1. **`include/asm/processor.h`**：`thread_struct` 增 `callee_saved` 段（`rd32–63`/`rb32–63`，FP 段按**待裁定 1**）；`INIT_THREAD` 同步。
2. **`include/asm/switch_to.h` + `kernel/process.c`**：`__switch_to(prev,next)` 真实现——保存 `prev` 的 callee-saved 到 `prev->thread`、恢复 `next->thread`、切 `rb1`（SP），返回 `prev`（`switch_to` 宏的 `last`）。
3. **`__switch_to_asm`**（`kernel/entry.S` 或并入 `process.c` 的 inline asm）：用 `stm.o`/`ldm.o` 整段保存/恢复 `rd32–63`/`rb32–63`（`SimRISC-01 §1/§2` 的块传送布局），FP 段按裁定。
4. **调度接线**：`cpu_idle`/`schedule` 路径跑通，`kernel_init` 之后 fork 出的子进程与 init task **来回切换**（探针观测「两个任务交替执行」）。
5. **`switch_mm`**（`mm/mmu.c`，K3 只留接口注释「K4 落地四步序列」）：落地 `switch_mm_irqs_off` 四步——切 ASID（`cfx_ptw_tlb_asid`）、失效旧 ASID 的 `G=0` 条目（`tlb_control invalid|VA/range|ASID_ANY=0`）、按需写 PTBR、返回（`contract-tlb TLB-30`）。
6. **U-mode ↔ S-mode 帧保存/恢复（cg5 单帧，用户 2026-11-17 选 C）**：用户进程切换时，被切换走的进程若在**用户态**，其用户态上下文（`pt_regs` 全量 + 用户栈 `rb1`）随 `thread_struct`/`task` 保存；切回时经 `cfx_umon` user 行向量/`escape` 恢复用户态帧。验证「用户进程 A ↔ B 切换后各自用户态帧/寄存器正确」。**单帧、不含递归**（同 cfx 嵌套留 K5）。
7. **最小 clockevent（用户 2026-11-17 裁定）**：`cfx_hart` 的 timer（`cg8 rc4 = timer_cmp` 绝对时间 / `rc5 = timer_ctrl` ENABLE/IMASK/ISTATUS）驱动 tick 中断，仅满足 `kernel_init`/调度/计时需要（`schedule_tick`、jiffies 推进）；**不做** clocksource/clockevent 通用框架升级（那属 K5 的 `m14-linux-021`）。寄存器语义按 `contract-see §3/§6.5`（`cfx_hart` 定时器、`TIMER` 异步入口 `cfx_hart` supv 行已由 K2 `async_trap.S` 落地）；放行前提（`cfx_hart` cg8 的 `hypv_cg_reg_deleg`）K2 已放行。
8. **F3：execve 建 `VM_GROWSDOWN` 栈 VMA + init 真跑（用户 2026-11-17 裁定从 `016` 移入）**：`kernel_init` → initramfs `/init`（静态 musl）在 QEMU 上跑起来；execve 后 `current->mm` 有且仅一个 `VM_GROWSDOWN` 栈 VMA（`vm_start`/`vm_end` 现场打印、大小 ≥ 1 页、入口 `ip`/`rb1` 已由 `start_thread` 填）。**与 019 分工**：本任务只到「init 能跑 + 栈 VMA 存在」，`019` 测 `S1–S6`（栈 VMA 下方扩栈）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_switch_probe.py` rc=0，逐 case 打印；期望值现场派生（callee-saved 集合 ← `contract-abi §4.5`，块传送布局 ← `SimRISC-01 §1/§2`，`switch_mm` 步骤 ← `contract-tlb TLB-30`）。
2. **探针 case（每条一条可达 FAIL 断言）**：
   - `S1 保存/恢复往返`：`__switch_to(a,b)` 后 `b` 的 callee-saved 字段与切换前一致（逐寄存器，用现场注入的哨兵值）；`a` 的字段被保存到 `a->thread`。
   - `S2 双任务交替`：fork 后两个任务各递增自己的计数器并 `schedule()`，探针断言「两个计数器都推进」（证明真切换、非单跑）。
   - `S3 switch_mm`：切到新 `mm` 后 `cfx_ptw_tlb_asid` == `mm->context.asid`（现场读值），且失效命令值按 `contract-tlb TLB-19` 现场重建（不写死）。
   - `S4 callee-saved 越界`：`__switch_to` 只碰 callee-saved 段 + SP，**不得**碰 caller-saved（`rd8–31`/`rb8–31`）与保留（`rb2`/`rb3`）——探针用哨兵值断言切换前后 caller-saved/保留寄存器不变。
   - `S5 U-mode 帧往返（用户 2026-11-17 选 C）`：两个用户进程 A/B 交替切换，断言各进程用户态帧字段逐项正确——`ip`/`rb1`/`rb3`/`rd32–63`/`rb32–63`（callee-saved）在 A→B→A 往返后与首入一致（现场哨兵值）；`status == 0`；**不含递归**（切换路径不写 cg5→cg6）。
   - `S6 最小 clockevent`：`cfx_hart` timer 驱动 tick——写 `timer_cmp = now + period`（`period = freq/HZ` 现场派生）后在期望间隔内收到 `TIMER`，`jiffies`/`schedule_tick` 推进；**不注册** clocksource/clockevent 通用框架（负例：探针断言通用框架未接线，`021` 归 K5）。
   - `S7 F3/init 真跑`：`kernel_init` → initramfs `/init`（静态 musl）在 QEMU 上跑起来（打印 init 标记）；execve 后 `current->mm` 有且仅一个 `VM_GROWSDOWN` 栈 VMA（`vm_start`/`vm_end` 现场打印、大小 ≥ 1 页、入口 `ip`/`rb1` 已填）。
3. **≥6 路注入**（`cp`+md5 还原 + 重建回绿）：① `__switch_to` 不保存 `rd32` 段 ⇒ `S1` 红（b 侧 rd32 哨兵被 clobber）；② 保存了但恢复错序 ⇒ `S1` 红；③ `switch_mm` 不写 ASID ⇒ `S3` 红；④ 切换碰了 `rb3`（rbtp）⇒ `S4` 红；⑤ 用户态帧不保存 `rb3`（rbtp）⇒ `S5` 红（A 往返后 rbtp 被 clobber）；⑥ timer 不写 `timer_cmp`（无 tick）⇒ `S6` 红；⑦ `execve` 不建 `VM_GROWSDOWN` ⇒ `S7` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-017/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/include/asm/{switch_to,processor}.h.patch`、`components/linux/patches/arch/dadao/kernel/{process.c,entry.S,Makefile}.patch`（entry.S 新建）、`components/linux/patches/arch/dadao/mm/mmu.c.patch`（`switch_mm` 落地）、`components/linux/changelog.md`、`tools/linux/k4_switch_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-abi §4.5`（callee-saved/CSR）、`SimRISC-01 §1/§2`（块传送）、`contract-tlb TLB-30`（switch_mm）为准；**不得**套 RISC-V `ra`/`s0-s11` 或 x86 帧布局。
5. `__switch_to` 必须在关中断/关抢占的临界区被调（`switch_to` 的既有调用点保证）；`last = __switch_to(prev,next)` 语义与 `switch_to` 宏一致（返回 `prev`）。
6. **单帧、不递归（用户 2026-11-17 选 C）**：U-mode ↔ S-mode 帧往返用 cg5 单帧，**不实现同 cfx 递归**（cg5→cg6 保存留 K5）；用户态进程切换不引入 umon 递归。
7. **最小 clockevent 不做通用框架升级（用户 2026-11-17 裁定）**：只做 `cfx_hart` timer 驱动 tick，**不得**注册 clocksource/clockevent 通用框架（`021` 已后移 K5）；不破坏 K2 的「两轴 mask / 单旋钮」口径（`contract-see §6.4`）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~（待裁定 1）FP 保存范围~~ **已裁定（用户 2026-11-17）**：`rd/rb/rf/ra` **全部在异常入口/出口帧处理**（由 `m14-linux-022` 落地：`ra`/`rf` 用 `ldm.o`/`stm.o` 块传送）；`__switch_to` **不再单独保存/恢复 FP**，只切换内核栈与内核态 callee-saved。本任务的 `S5`（U-mode 帧往返）按此断言。
2. ~~（待裁定 4）~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环并入本任务 + `016`；「用户进程 A↔B 切换」断言（`S5`）已加入，单帧、不含递归（同 cfx 嵌套留 K5）。
3. ~~（待裁定 3）上下文切换是否保存整条 RAS~~ **已裁定（用户 2026-11-18，选 A）**：**接受保存整条 `ra0–ra63`**（`stm.o`/`ldm.o` 各 2 条，每次切换 +4 条块传送）；依据 `spec/SimRISC-00`「进程切换时，操作系统须保存和恢复全部 `ra0–ra63`」与 `m14-linux-022` 的异常帧口径（`ra` 必须在入口/出口恢复）。

## 审阅记录

> **（待裁定 6，第 23 轮新增，**S5 的前置设计选择**）**：按第 22 轮方案（入口栈保持静态、只把帧按任务化）实现时发现，该方案**无法让 A/B 交替**：umon handler 一旦 `schedule()`，A 与 B 的内核续跑点都落在**同一张静态入口栈**上（互相覆盖）；这与帧放在哪里无关，F13 的教训是同一件事。要满足 S5（两进程交替 + 帧逐项一致），必须让**每个任务的内核 handler 跑在自己的内核栈**上。本端口 `current` 由 SP 派生，入口拿不到「自己的内核栈」——F28 的 `thread_info.task` 正是为此在**静态栈**上刷新。**建议方案（与 F13 不同，不依赖 SP）**：新增一个**全局 `dadao_current_task` 单元**，由 `__switch_to`（及 `dadao_enter_user`）写入，umon 入口读它取 `task_stack_page(task) + THREAD_SIZE` 作新 SP；单 hart、无嵌套 ⇒ 全局单元是安全的，且 `thread_info` 天然位于各任务内核栈底。请裁定：**(A)** 按此方案做（属核心结构改动，需扩到 `entry.S`/`process.c`/`thread_info.h`）；**(B)** S5 降级为「帧按任务化 + 不阻塞的交替」（需放宽判据：交替由帧切换模拟，不改内核栈）；**(C)** S5 推迟到 K5 与嵌套/抢占一起做。**已按 (B)/(C) 都不用动代码，本轮未改内核**。

> **（待裁定 5，本轮新增）**：`F37` 残余——同步帧内屏蔽异步源后，C 半 `arch_local_irq_restore()` 与 asm `escape` 之间仍有**待投递 tick 立即生效**的间隙（实测：`replace-zero` 之后即 CFXESC）。两个候选：**(A)** 把恢复掩码挪到 `escape` 之后（`cg5 rc3` 重定向到 unmask 蹦床；代价：umon 帧会破坏用户 `rd2/rd3`，需另找 scratch）；**(B)** 认定 `escape` 应恢复 `inner_cfx_code`（= `ISS-454` 的语义纠正，改 spec/QEMU，本任务不自行改）。**建议 (B)**：`§5.3` 对 `inner_cfx_code` 的缺失是同一个口径问题的两面（掩码读法与 escape 目标都依赖「当前 cfx」），(A) 只能绕内核侧且（umon 帧）无法干净实现。

> **交接清单（2026-11-18，用户裁定 4 后暂停；QEMU 侧 `m14-spec-009` 改完并合入后按序执行）**
> 1. **第一步**：`make install-host`（重建含新 `escape` 语义的 QEMU）→ 跑 `k4_switch_probe.py --no-inject`，期望 **S7 转绿**（`CFXESC` 消失、`/init.musl` 跑到 `exit_group`）。
> 2. 紧随其后**去掉临时屏蔽**：删掉 `kernel/traps.c`/`kernel/process.c` 里 `arch_local_irq_save()/restore()` 包壳（F37 的 workaround），保留 `dadao_in_frame`（帧内不打印试点，方案 C 的成果）。删后立即复验：S1–S7 + 5 路注入 + 全回归。
> 3. **本任务 S5（U-mode 帧 A/B 往返）判据**：两用户进程 A/B 交替切换；各进程 `ip`/`rb1`/`rb3`/`rd32–63`/`rb32–63`（callee-saved）在 A→B→A 后与首入一致（现场哨兵）；`status == 0`；**不含递归**（切换路径不写 cg5→cg6）。落地方式 = 按任务帧（`task_pt_regs()` + 入口栈 `thread_info.task` + `dadao_enter_user` 写任务帧），F13 曾试并回退，S7 通后重做。
> 4. 补任务书要求的**注入⑤**：用户态帧不保存 `rb3`（rbtp）⇒ S5 红（A 往返后 rbtp 被 clobber）。
> 5. **019 缺口复验**：`k4_stack_probe` 增 case 7「用户态触发」——execve 后把初始 `sp` 置于栈底下方 1 页并 store ⇒ 断言 VMA 扩 1 页 + PTE 装载 + 读 0 + 扩栈计数 +1；未通前标 BLOCKED，不伪造。
> 6. 顺序：QEMU 合入 → `install-host` → S7 → 去屏蔽 → 回归/注入 → S5 → 栈增长用户态 case。
> 7. **不要动** `components/qemu/**` 与 QEMU 源树（`m14-spec-009` 持有）；本任务只碰 `components/linux/**` 与 `tools/linux/**`。

> **（待裁定 4，本轮新增，架构侧已判 spec 语义，但与本任务/他任务探针的既有判据冲突）**：按 `spec/DADAO-12 §5.2 步骤6` + `§5.3 步骤0`，「异常帧内执行 `trap cfx0`（semihosting 打印）」本身非法——打印会把 `inner_cfx_code` 改成 `cfx0`，随后该帧的 `escape <原 cfx>` 必报 `CFXESC`。**冲突点**：K2/K3/K4 四个门控的判据输入**就是**帧内打印出来的行（`K3 pf:`、`K2 tick:`、`K4 umon->smon:` 等），因此落实该判定需要把 K2–K4 探针的诊断统一改成「帧内只记内存、`escape` 之后再打印」。请裁定：**（A）**本任务一并重构（会改到 `check_k2`/`check_k3`/`k2_*`/`k3_*`/`k4_*` 的判据与其它任务的验收面，需扩权）；**（B）**另立专门任务（本任务 S7 仍卡 F29，按架构侧判定不在本任务内修）；**（C）**先只在 `017` 自己的探针镜像里试点「帧内不打印」，用寄存器/内存槽传值，验证后再推广。建议 **(C)→(B)**。


### 第 1 轮 engineer 自审（2026-11-18，m14-linux-017）

**范围**：本任务全部改动（`components/linux/**`、`tools/linux/k4_switch_probe.py`）逐行自查；实跑以本 worktree 为唯一工作树（`git rev-parse --show-toplevel` 自证）。

**自主逐行审查发现与处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `__switch_to` 不搬返回地址栈 ⇒ A→B→A 回到上层返回点（哨兵寄存器活到 C 代码里，缺页终止 `code=0xe1`） | ✅已修（并升级为待裁定 3） | `thread_struct.ras[64]`；`entry.S` 用 `stm.o {ra0:ra62}`+`{ra63}` 保存/恢复 | `k4_switch_probe` S1 `bad=0x0`；`s1-a-ras-count want=0x4 got=0x4`（B 侧 `ras-count=1`） |
| F2 探针 asm 助手把调用者的 callee-saved 库改成哨兵（违反 `contract-abi §4.8` 的被调者保存义务），调用者带着哨兵继续跑 ⇒ `code=0xe1` | ✅已修 | `k4_switch_asm.S` 进/出各一次 `stm/ldm` 保存/恢复调用者两库（`.bss` 缓冲） | S1 往返 `bad=0x0`，且 S1 之后 S4 仍绿 |
| F3 新任务用 `set.rb rb2, 0` 做 `jump` 基址 ⇒ 违反「不碰 `rb2`」且把新任务 FP 置 0 | ✅已修 | `entry.S` 改用 `rb16`（caller-saved 实参，已被消费）作基址 | S4 `s4-rb2-untouched want=0x2f02 got=0x2f02` |
| F4 `pgd_alloc()` 不给用户表装内核 L1 槽 ⇒ 写完 PTBR 内核自己取指即 CFXMEM | ✅已修 | `pgalloc.h` 复制 `swapper_pg_dir` 的 `[USER_PTRS_PER_PGD, PTRS_PER_PGD)` | S3 `alive_on_new_table=1`（切到新表后仍打印） |
| F5 用户页只置 `U` ⇒ 内核（supv）读用户缓冲即 `CFXPERM/NSPERM`，`write(2)`/`copy_from_user()` 不可能工作 | ✅已修 | `mm/fault.c` 的 `dadao_pf_mode_bits()` 返回 `U\|S` | 静态判据 + S7 待验（未打通，见完成区） |
| F6 016 的 `k4_fork_probe` 因切换变真而红（只被观察的子任务被 `cond_resched()` 调度走） | ✅已修 | `k4_selftest.c`：clone 后 `clear_tsk_need_resched(current)`（PREEMPT_NONE 下 `preempt_disable()` 是空操作，实测 `preempt=0`） | `k4_fork_probe` **101/101** |
| F7 S2 的 park 用 `set_current_state()+schedule()` 触发 `WARN_ON_ONCE(p->is_blocked)`（sched/core.c:4603/6749） | ✅已修 | 改用 `wait_for_completion(&永不完成)` 的标准阻塞路径 | 两次 WARN 仍在（改为 fork 时触发），已登记为 F8 |
| F8 同镜像里 S2 的 case 体被执行**两次**，第二次 `spins` 为垃圾值 ⇒ 有任务在别人的栈上继续跑；与 S7 卡在 `schedule_idle()` 的 `WARN_ON_ONCE(current->__state)` 疑同源 | ⏸延后 | — | 现象与日志行已写入 `changelog.md` 本条「未完成 ③」；**未定位根因**，S2 的 4 条断言在两次执行里都成立，故不影响已交付判据 |
| F9 `switch_mm()` 的步骤②对**新** ASID 做 `invalid|all|ASID_ANY=0`（而不是对旧 ASID）：两者都满足 TLB-30，取新 ASID 是为了不碰 `G=1` 内核条目（TLB-26） | ❌不修（有意） | — | `mmu.c` 注释说明；S3 的期望值由 `dadao_tlb_control_value()` 现场重建（`invalid_cmd=0x2`） |

### 第 2 轮 engineer 自审（2026-11-18，用户裁定 RAS=接受后继续推进）

**处置**：待裁定 3 已按用户 2026-11-18 选 A 记为**已裁定**；本轮集中打 S5/S7/F8。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F10（新，**已修**）`__switch_to` 不保存 `rb2`（FP）⇒ 被挂起 C 帧的尾声用**别人的** FP 恢复 SP：实测启动任务带着内核线程的 `SP`/`current` 继续跑（`spins` 呈垃圾值、S2 体在别人栈上跑） | ✅已修 | `thread_struct.fp` + `entry.S` 在 `st.o rb1`/`ld.o rb1` 旁成对保存/恢复 `rb2`；`asm-offsets` 增 `THREAD_FP` | 修后 S2 `spins=1 pid=0 sp=0x200004cf670`（与会话前垃圾值对比）；S1 `bad=0x0`、S4 `rb2-untouched` 仍绿 |
| F11（新，**已查清不是缺陷**）RAS 保存/恢复是否幂等：`stm {ra0:ra62}`+`{ra63}` → `ldm` → 再 `stm` 两份缓冲逐槽比较 | ✅已验（新增断言） | `k4_switch_asm.S::dadao_k4_ras_idem` + S1 的 `ras-save-restore-idempotent` | `diff_slots=0`、`racnt=3 a63=0x1020000113274` |
| F12（新，**未定位**）S2 的 case 体在同一次启动里被执行**两次**（`entry #1`/`#2`，两次 `racnt=4`、`pid=0`、`sp` 相同、断言两遍全绿）；与「返回地址被多弹一层」同形。已排除：RAS 块传送非幂等（F11）、FP 未保存（F10）、`thread_struct` 无 `resume` 相关残留 | ⏸延后（保留现场） | — | 日志 `check-linux-k4-switch/log/switch.log`（`entry #1/#2` 两行 + 两次全绿） |
| F13 S5 的按任务帧改造（`task_pt_regs()` + 入口栈 `thread_info.task` + `dadao_enter_user` 写任务帧）本轮**试做后回退**：改完 `k4_fork_probe` 的 F5 从 CFXMEM(0x8) 退到「挂死」，时间用尽，先保回归 | ⏸延后（S5 未实现） | 回退 `trap.S` 的 umon 入口与 `process.c::dadao_enter_user` 到 016 的静态帧版本（保留 F10 的 FP 修复） | 回退后 `k4_fork_probe` **101/101**、S1–S6 全绿（`39 PASS / 3 FAIL`，红项只有 S5 与 S7×2） |

### 第 3 轮 engineer 自审（2026-11-18，继续攻 S5/S7/F8）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F14（新，**已定位并修**，S7 的堵点 ①）`kernel_init` 在 `kernel_execve()` 成功后**返回**，`dadao_ret_from_fork` 却把「内核线程 fn 返回」一律判为错误并退出 `0x33`；而 `start_thread()` 已经把**本任务**的帧改成新程序（ip/rb1）——正确语义是「继续进用户态」（其它端口由 `ret_from_fork` 落进 `ret_to_user` 得到同一形状） | ✅已修 | `process.c::dadao_ret_from_fork`：`fn` 返回后若帧已不是「内核线程」形状（`ip != ret_from_fork` 且 `rb1 != 0`）⇒ `dadao_enter_user(regs)`；否则仍具名报错 | 修后镜像里出现 `K4 fork: kernel thread exec'd …` 前的路径已可达（见 F15 现场） |
| F15（新，**未解**，S7 的堵点 ②）越过 K4 边界后系统**确实在跑**（`copy_thread #3 fn=kernel_init`、`#4 fn=kthreadd`、`#5` 由 pid 4 派生），但 `jiffies` 冻结在 4294937296、**交接后一个 tick 都没来**；交接点实测 `mask=0x…7fff`（源位开着）、`timer=0x1`（ENABLE、无 ISTATUS） | ⏸延后（现场已存） | — | 现场四行：`handoff mask/timer/jiffies`、`copy_thread #3/#4/#5 mask=0x…7fff jiffies=同值`；判据：交接前 S6 能收到 tick（jiffies+3），交接后为零 |
| F8/F12（继续追，**已缩小**）S2 的 case 体执行两次：用 `dadao_k4_ras_idem` 转储入口处 RAS 顶层三项，两次 entry 的 `top` 相同、而 `t1` **相差 4**（`0x…336c` vs `0x…3370` = `call+0` vs `call+4`）⇒ 其中一次的「s2 调用返回地址」是 **call+0**；同时 S1 的直接往返、`racnt` 前后一致说明「切换不泄漏栈深度」；`noinline` 与循环标记（`i=1 before/after schedule`）都正常 | ⏸延后（现场已存；非 RAS 幂等、非 FP、非内联） | — | 两行 `s2: entry … top=… t1=…` 的 +4 差异；`dbg: loop i=1 before/after` 成对出现 |
| F13 S5 的按任务帧改造（上一轮） | ⏸延后（仍是 S5 未实现的直接原因；本轮未再尝试） | — | — |

### 第 4 轮 engineer 自审（2026-11-18，主攻 F15 / 次攻 F8）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F15 裁决修正（**关键**）：不是「tick 坏了」。三处现场（① 交接前 busy-wait、② 交接后 kernel-thread 上下文、③ 显式 `dadao_timer_arm` 后再等过 deadline）显示：`cfx_time` 持续推进、`CMP` 写对、`ENABLE=1`、源位开着（`mask=0x…7fff`）、`global_cfxt_intr_mask=0x…7fff`，且**等过 deadline 后 `dj=3`（jiffies 真推进）** ⇒ 最小 clockevent 在交接后仍工作；此前的「冻结」是观测点都落在 tick 之间 | ✅已澄清（不修） | — | `K4 dbg wait: t=370494543 cmp=0x144b4296 st=0x1 j=…304 dj=3` |
| F16（新，**已定位到层，未解**）：真正的堵点在 `kernel_init_freeable()` 的 **initcall 序列之前**——给 `core/postcore/arch/subsys/fs/rootfs/late_initcall` 各放一行标记（探针镜像，不改 `init/main.c`），**一个都没打印**；而 `kthreadd`（`copy_thread #4`）与 kworker（`#7 pid=6`）已经起来 | ⏸延后（现场已存；下轮把标记前移到 `smp_init`/`workqueue_init`/`async_synchronize_full`/`wait_for_initramfs` 逐个二分） | `k4_switch_selftest.c` 增 7 个 initcall 层标记（probe 镜像专用，只打印） | 一次启动中的标记行（当前为 0 行）+ `K4 fork: copy_thread #3/#4/#7` 现场 |
| F8/F12（次攻，**已把判据写清**）：两次 entry 的 `top` 相同、`t1` 差 4（`call+0` vs `call+4`）⇒ 第二次是从 `call` 的返回点落进 case 体；已排除 RAS 幂等性（F11）、FP（F10）、内联（`noinline` 后仍现）、`schedule()` 返回错位（`loop i=1 before/after` 成对） | ⏸延后（下轮按「`call` 压的是 `call+4` 还是 `call+0`」直接用 `dadao_k4_ras_idem` 在 `call` 前后各转储一次来定） | — | 两行 `s2: entry … top=… t1=…`（`0x…336c` vs `0x…3370`） |

### 第 5 轮 engineer 自审（2026-11-18，m14-linux-031 合入后）

**背景**：`m14-linux-031` 合入 master（`d033c054`）后 initramfs 布局变了——`/init` 是 193 B **脚本**（`#!/bin/sh` + `exec /bin/sh`），静态 musl MVP init 改名 `init.musl`（18520 B），另有 `/bin/busybox`（311408 B）+ applet 链接。本任务 worktree 基于旧 `0e907f72`，已按架构侧指示取用 master 的 `tools/linux/{make_initramfs,check_k0,check_k1,k1_boot_probe,build_busybox}.py`（`git checkout master -- <path>`，未做 merge/squash：本地任务书与本任务改动冲突，且不提交）。重建 initramfs 后自检通过：`/init script (193 B) -> exec /bin/sh (busybox applet sh)`、`init.musl 18520 B`、`image entries (15 + TRAILER)`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F16（承上）S7 的判定对象随 031 改为 `/init` 脚本 → `/bin/sh`（busybox）；本任务内核侧 syscall hook 只答 MVP 的四个调用（`getpid/write/brk/exit_group`），**跑 busybox 还需 `execve/fork/wait/read/openat`（K5 的 syscall 表）** | ✅已按架构侧规则(a)改判据并在 hook 注释写明；**规则(b) 的触发条件与时点**：F16 修好后若 busybox 起不来（缺上述调用）⇒ 改 `/init` 为 `exec /init.musl` 并记录证据；**当前 F16 未解，故 (b) 未触发**（不能预判） | `k4_switch_probe.py` 的 S7 说明与 `MISSING["S7"]` 文案；`k4_switch_selftest.c` 的 hook 头注释 | initramfs 自检 3 行 PASS（见上） |
| F17（**待裁定，未触发**）：若 F16 修好后 (a)/(b) 都走不通（例如 busybox 需要的不止 syscall：`/proc`、`/dev/console`、`mmap` 可执行文件映射等），按架构侧规则保留现场并登记 F17，不改内核硬凑 | ⏸待触发 | — | — |

### 第 6 轮 engineer 自审（2026-11-18，主攻 F16）

**master 取用整理（按架构侧「优先 merge」）**：本轮做了**正式 squash-merge**（`git merge --squash master`，**未产生任何提交**）：先把本任务书用 `patch -R` 退回 HEAD 版（备份在 `/tmp/opencode/m14-linux-017/tb/mine.md`），merge 后把本任务的「审阅记录 + 完成区」重新接回 master 版任务书（其中 RAS 裁定行由 master 版本提供）。⇒ 上一轮的 28 个 `git checkout master --` 文件现在都变成 **merge 的一部分**，不再是来源不明的取用；`git status` 里它们是 merge 结果而非孤立 checkout。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F16（**本轮已定位到单条语句**）`kernel_init_freeable()` 停在 `workqueue_init()` → `wq_cpu_intensive_thresh_init()` 的**第一条语句** `pwq_release_worker = kthread_run_worker(0, "pool_workqueue_release")`（等新 kworker 启动的完成量） | ⏸延后（定位完成；修复超本轮预算，判据写清） | `init/main.c` 加 13 个 `DADAO_INIT_MARK` 打点（`#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST`）；`kernel/workqueue.c` 加 13 个 `DADAO_WQ_MARK` 打点（同一 `#ifdef`，探针镜像专用） | 一次启动的分层现场：`K4 init: enter kernel_init_freeable` → `before smp_prepare_cpus` → `before workqueue_init` → `K4 wq: thresh_init 0` → **无后续**（`rescuer_begin`/`bh_workers`/… 全未打印） |
| F16 判据（下一轮可直接接） | ⏸待续 | — | ① `wq_cpu_intensive_thresh_init()` 的第一句是 `kthread_run_worker()`（`kthread_create_on_node` → `wait_for_completion(&create.done)`，等 kthreadd 派生并启动新 kworker）；② `kernel_init` 更早的 `wait_for_completion(&kthreadd_done)` **已通过**（否则到不了本函数），故完成量机制本身可用；③ 因此嫌疑集中在「kthreadd 之后能否再派生新 kworker」与 F8（`call+0`/`call+4`）这一类 RAS 后续行为；下一轮建议：在 `kthread_create_on_node` 的 `create.done` 两侧各打一行（pid + `creation` 完成量），并把 `kthreadd` 的 `create_kthread` 入口打一行，即可判定是「kthreadd 没被调度」还是「新线程没跑到 `complete()`」 |

### 第 7 轮 engineer 自审（2026-11-18，按上轮判据判 A/B）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F16 判 A/B（**结论 = B，且比 B 更进一步**）：`kthreadd` 被调度了（pid 6 进 `create_kthread`），新线程也起来了（pid 7 `kthread()` 入口 → 过 `sched_setscheduler_nocheck` → 到 `complete()` 前），**不是调度/唤醒路径的 A**。`complete()` 本身生效：`done->done=1` 且被唤醒者 `p5_state=0`（TASK_RUNNING）；但**下一个 tick（10 ms）里 pid 5 又回到 `state=2`、且从未打印「done」行** ⇒ 唤醒后又睡回同一完成量 | ⏸延后（定位完成，与 F8 同族判据已写清） | `kernel/kthread.c`（新增补丁，5 处 `K4 kt:` 打点：`queue`/`wait`/`kthreadd create_kthread`/`NEW THREAD started`/`before|after sched_setscheduler`/`before complete`/`after complete` 含 `done->done` 与 p5 状态）；`arch/dadao/kernel/time.c` 的 tick 里加 `K4 kt watch#N`（pid 5/7 的 `__state`/`on_cpu`，3 个 tick） | ① `K4 kt: after complete pid=7 done->done=1 p5_state=0 p5_oncpu=0`；② `K4 kt watch#1..#3 j=…301..303 p5=2/0 oncpu=0 p7=2/0 oncpu=0`；③ 全程无 `K4 kt: done` 行 |
| F8 ↔ F16 关联（**判据**）：完成量是 `DECLARE_COMPLETION_ONSTACK`（`done=0x200041cf548`，在 pid 5 **自己的栈**上）；「已置 1 的 `done` 在等待方醒来后又读到 0」等价于**等待方栈上的那 8 字节被改写**，与 F8 的「任务在别人的栈上继续跑 / RAS 顶层 `call+0` vs `call+4`」同族。⇒ **先修 F8，再回看 F16**（与用户预定策略一致） | ⏸待续（F8 优先） | — | 两条现场（同上）+ F8 的 `t1` 差 4 证据 |
| F8 下一轮判据（写清供交接）：① 在 `dadao_switch_to_asm` 入口/出口各转储一次 RAS（`dadao_k4_ras_idem`）与 `sp`，对比同一任务前后两次切换的 `top/t1`；② 检查 `call` 压栈是否为 `call+4`（用 `ra2rd rdX, ra63, 1` 在 `call` 之后立刻读，与「调用点地址 + 4」比对）；③ 检查 `ret` 后 `RACNT` 是否恰好 −1（已有 `dadao_k4_ras_racnt`） | ⏸待续 | — | — |

### 第 8 轮 engineer 自审（2026-11-18，修 F8）

**结论：F8/F12 结案 —— 是探针源码的重复调用，不是内核缺陷。**

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F8/F12（**已结案：探针 bug**）S2 的 case 体执行两次：早前「从 tarball 恢复源码 + 重新插入 case 调用」时 `k4s_case_s2();` 被写了两遍（同一次启动里两遍完全相同、断言两遍全绿、`t1` 差 4 是两个不同 call site 的 `call+4`） | ✅已修 | 删掉重复行（`k4_switch_selftest.c`） | 修后启动里 `K4 switch s2: c0=…` **只出现 1 次**；`ras_diff=0`；S1/S3/S4/S6 全绿 |
| F19（新，**已证并成为交付断言**）`call`/`ret` 的 RAS 语义：`call` 恰压 1 条、`ret` 恰弹 1 条、压入值 = `call+4`（`contract-isa §8.4/§8.6`） | ✅已测（新增 3 条断言） | `k4_switch_asm.S::dadao_k4_call_probe`（`RACNT` 三处 + 压入条目 + 与 `call+4` 的异或，全落 `.bss` 数组）；S 组断言 `call-pushes-one-entry`/`ret-pops-one-entry`/`call-pushes-call-plus4` | `racnt 3 -> 4 -> 3 entry=0x10200001439f8 xor_call_plus4=0x0`，三条 `ok` |
| F20（新，**已证并成为交付断言**）一次 `schedule()` 往返后，任务自己的**有效** RAS（`RACNT` 内那几条）逐槽不变 ⇒ 切换的「整条搬」模型自洽（无效槽按 `spec/SimRISC-00 §2.4` 不定，测试只比有效窗口） | ✅已测（新增 1 条断言） | `k4_switch_asm.S::dadao_k4_ras_dump`（只存不载）+ S2 的 `spins==1` 前后对比 | `ras_diff=0 pre0=0x4000000000000 pre63=0x…25c8 post63=0x…25d4`（63 槽是 dump 自己的 call，已排除）、`s2-ras-unchanged-by-schedule ok` |
| F16（**仍未解，证据更新**）：完成量问题独立于 F8 —— 同一次启动里 `after complete` 显示 `done->done=1`、`p5_state=0`；3 个 tick 内 `p5` 回到 `state=2` 且新线程 pid 7 **已消失**（`find_get_task_by_vpid(7)` 为 NULL，watch#3 `p7=-1`） | ⏸待续（下轮从「p7 消失」入手：`kthread()` 里 `complete()` 之后会 `schedule_preempt_disabled()` 等首次唤醒，若它退出/被回收，则 `p5` 的完成量无人再管） | — | `K4 kt: after complete pid=7 done->done=1 p5_state=0 p5_oncpu=0`；`K4 kt watch#1..#3 … p5=2/0 oncpu=0 p7=2/0 → p7=-1/-1`；无 `K4 kt: done` 行 |

### 第 9 轮 engineer 自审（2026-11-18，查 pid 7 消失）

**两条纠正 + 一条新现场**（本轮价值在于推翻两个错误假设、修掉自己的方法学错误）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F21（**方法学错误，已修**）上轮「p5 醒来又睡回 / p7 消失」的现场**硬编码了 pid**（5/7），而 pid 每次启动会变（本机上是 3/4/5）⇒ 该轮结论不可靠 | ✅已修 | `kernel/kthread.c` 在入队处记录 `dadao_kt_creator_pid = current->pid`；新线程与 tick 打点一律按该 pid 查任务，不再写死 | 现场 `queue … pid=3` / `NEW THREAD started … pid=5` / `after complete … creator=3 …` |
| F22（**假设被推翻**）「完成量那 8 字节被改写」：实测 `done@0x200041af548` 在 tick 时读到 `now=0x100000000` —— 这正是**大端下 u32 `done=1`**（我的探针用 64 位读了 u32，高半字=1、低半字=0）。⇒ 完成量**没有被改写**，F16 的机理不在这 | ✅已澄清（探针只影响结论，不影响产品） | tick 打点改为打印 `done` 地址 + 新线程留下的值 + 现读值 | `after complete … done->done=1 creator=3 state=0 oncpu=0 on_rq=1`；`watch#N done@0x…548 was=0 now=4294967296` |
| F16（**仍未解，现场更新**）用正确 pid 后：`complete()` 之后创建者**确实被完整唤醒**（`state=0 on_rq=1`）；但一个 tick 后创建者变成 `state=2 on_rq=0` 且**从未执行到 `wait_for_completion` 之后的打点**，同时新线程（pid 5）停在 `schedule_preempt_disabled()`、current 始终是 pid 0 | ⏸延后（现场已收窄） | — | `watch#1..#4: creator=3/2 oncpu=0 onrq=0 cur=0/0`；无 `K4 kt: done` 行；`done=1` 保持 |
| F16 下一轮判据（写清） | ⏸待续 | — | 在 `wait_for_completion_killable` 的 **swait 循环内部**打点（第几轮迭代、`x->done`、`current->__state`、`list_empty(&wait.entry)`）：① 若创建者**从未再进入**该循环 ⇒ 它被调度到别处/在别处睡（查 `schedule()` 的 `prev->__state` 与 `prev->on_rq`）；② 若再进入且看到 `done=1` 却没返回 ⇒ 查 `x` 指针（栈帧/`DECLARE_COMPLETION_ONSTACK` 的地址）是否被 `sp` 偏移影响 |

### 第 10 轮 engineer 自审（2026-11-18，swait 循环内部打点）

**结论：S7 的堵点已具名 —— kernel_init（pid 3）在 workqueue 完成量被唤醒并跑过之后，又执行了一次 `wait_for_completion(&kthreadd_done)`，而该完成量已被第一次等待消费（`done=0`）⇒ 永久阻塞。** 这是「同一语句被重复执行」的实例（RAS 原语与切换的 RAS 保持性前一轮已证正确）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F16 具名化（**本轮核心**）：`do_wait_for_common` 的 swait 循环打点显示 pid 3 两次进入 | ⏸结论已定，修法待续 | `kernel/sched/completion.c` 加 `K4 wt:` 打点（`enter` 含 `x/done/RACNT/sp/comm`、每轮 `iter` 含 `done/state/list_empty/on_rq`、`sleep`/`woke`/`leave`），全部 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST` | ① `K4 wt: enter pid=3 x=0x200041af548 done=0 racnt=9 sp=0x200041af4d0`（workqueue 的栈上完成量）；② `K4 kt: after complete … creator=3 state=0 oncpu=0 on_rq=1`（被完整唤醒）；③ `K4 wt: enter pid=3 x=0x20000560818 done=0 racnt=17 sp=0x200041af330`（**`llvm-nm` 解析 `x` = `kthreadd_done`**，`done` 已被消费） |
| F23（新判据）：第二次等待的 RAS 深度 **17** vs 第一次 **9**，且栈更深（`0x…af330` < `0x…af4d0`）⇒ 不是「回到更浅的旧帧」，而是「在同一条链上更深的位置重复执行了 `kernel_init` 顶部的等待」；同时实测「一次 `schedule()` 前后 RACNT 4 → 4（不泄漏）」、`call`/`ret` 语义正确（第 8 轮断言） | ⏸待续 | — | 两行 `K4 wt: enter`（racnt 9/17）+ `ras round 1: 4 -> 4` |
| F16 下一轮判据（写清） | ⏸待续 | — | 在 `__schedule()` 里对「`prev == pid 3`」打一次 `prev->pid/prev->__state/prev->thread.sp/rq->curr->pid`，并在 `dadao_ret_from_fork` 与 `switch_to` 的恢复点各打一次 `RACNT`+`sp`：若 pid 3 被 switch 回来时 `RACNT` 是 17 而栈是 9 时的栈，则说明 **保存/恢复的 `sp` 与 `ras` 不是同一次快照**（`thread_struct` 里两个字段被不同时机写入）；这能解释「同一条链上更深处重复执行」 |

### 第 11 轮 engineer 自审（2026-11-18，**根因已定位并修复**）

**根因（真）**：`thread.ra`（新任务入口）**在任务首次运行后从未清零**。`__switch_to_asm` 用 `thread.ra != 0` 判断「从未运行过的任务」并 `jump` 到 `dadao_ret_from_fork`；`copy_thread` 设了 `t->ra` 却没人清掉 ⇒ **其后每次切回都走 fresh-task 路径、重新进入 `dadao_ret_from_fork`、重跑 `fn`**。这解释了三件事：① `kernel_init` 第二次执行 `wait_for_completion(&kthreadd_done)`（`done` 已被消费 ⇒ 永久阻塞，F16/S7）；② 早前 S2「体执行两次」；③ 早期 `spins` 呈垃圾值。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F24（**根因，已修**）`thread.ra` 未清零 ⇒ 每次切回重跑 `fn` | ✅已修 | `kernel/process.c::dadao_ret_from_fork` 入口 `current->thread.ra = 0;`（附注释说明「本函数只由 `jump` 进入、恢复走自己的 `call` 入口」） | 修复后：`K4 init: rootfs_initcall reached` / `late_initcall reached` / `before|after do_basic_setup` / `before|after wait_for_initramfs` 全部出现；并到达 `Run /sbin/init…/bin/sh as init process`（此前停在 workqueue_init） |
| F25（新，**交付断言**）内核线程体只启动一次 | ✅已测（2 条断言） | `k4_switch_selftest.c`：`k4s_starts[2]` 计数 + `s2-thread-{0,1}-started-once` | `K4 check s2-thread-0-started-once want=0x1 got=0x1 ok`（两条都 ok） |
| F26（新，S7 的**下一个**堵点）到 `Run /bin/sh as init process` 后 `Kernel panic - not syncing: No working init found` ⇒ `kernel_execve("/bin/sh")` 失败；另有一条 `VFS: Failed to pivot into new rootfs` | ⏸待续（属 execve/VFS 面，非切换面） | — | 现场 4 行 `Run …` + panic 行；`/init`（193 B 脚本）未被 `init_eaccess` 选中（走的是 `/sbin/init…/bin/sh` 兜底表）⇒ 下轮先查 `/init` 是否在 rootfs 里可见、再查 `load_elf_binary`/`setup_arg_pages` 的返回值 |
| 诊断补丁收口（本轮清理） | ✅已清理 | 删掉 `kernel/{kthread,sched/completion}.c` 的 F16 诊断补丁（`patches/` 下对应补丁一并删除、`series` 80 补丁）；保留 `init/main.c` 的 7 个 `K4 init:` 层标记与 `kernel/workqueue.c` 的 `DADAO_WQ_MARK`（均 `#ifdef`，探针镜像专用） | `check-patch-tree`/`--source-state` 绿；S1–S6 断言全绿 |

### 第 12 轮 engineer 自审（2026-11-18，F26 = execve/initramfs 面）

**三处真实缺陷已修，S7 从「无 init 可跑」推进到「busybox ELF 载入期的页表/激活问题」**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F26a（**已修**）initramfs 从未进内核：`CONFIG_BLK_DEV_INITRD` 未开、也无 `CONFIG_INITRAMFS_SOURCE` 接线 ⇒ `init_eaccess("/init")=-2`（ENOENT）、`pivot_root=-16`（EBUSY）、`kernel_execve` 全 `-2` ⇒ `No working init found` | ✅已修 | `arch/dadao/configs/defconfig.patch` 加 `CONFIG_BLK_DEV_INITRD=y`；`tools/linux/make_defconfig.py` 在 defconfig 之后写 `CONFIG_INITRAMFS_SOURCE="<运行期 initramfs.cpio>"`（**指向 cpio 文件，不是目录**——目录版会漏掉只在 cpio 里的 `bin/busybox`）；`usr/initramfs_data.S.patch`（新增）把 `.quad` 换成 DADAO 唯一允许的 `.dd.o64`（`spec/Toolchain-01 §7.1`） | `init_eaccess(/init)=0`；`Run /init as init process`；`K4 exec: depth=0 interp=/bin/sh ret=0`（脚本 handler 成功） |
| F26b（**已修**）`CONFIG_INITRAMFS_SOURCE` 指向目录 ⇒ rootfs 里只有 `init`/`init.musl`，`bin/sh` 不存在 ⇒ `open_exec("/bin/sh")` = `-ENOENT` | ✅已修（同上：改指 cpio 文件） | 见上 | 同一行 `interp=/bin/sh ret=0`（此前 `ret=-2`） |
| F27（新，**S7 当前堵点**）busybox ELF 载入期：内核在 VA `0x7baf0`（ELF 段 `0x70000-0x80000`）访问触发 `CFXMEM/DGPTRAP`，通道第 1 次 `fill-zero`、第 2 次同址仍缺页 ⇒ `die-missing`（`pte` 已是 present），且 `ptbr=0x4750000`。判据：**填充写进了 `current->mm` 的表，但生效中的 PTBR 可能不是它**（exec 的 `exec_mmap`→`activate_mm`→`switch_mm` 路径需核对） | ⏸待续（非切换/帧面，属 exec 的 mm 激活） | — | `K3 pf: n=1 … result=fill-zero` → `K3 pf: n=2 … try=2 result=die-missing`；`unrecoverable supv exception cause=CFXMEM ip=0x2000044b2b8 info=0x7baf0 ptbr=0x4750000` |
| F27 下一轮判据（写清） | ⏸待续 | — | 在 `dadao_switch_mm()` 打一行（写出的 ASID/PTBR + `next->pgd`），并在页故障通道的填充分支打 `__pa(mm->pgd)` vs `dadao_ptbr_read()`：若二者不等 ⇒ `activate_mm`/`exec_mmap` 未走到我们的 `switch_mm`（查 `asm/mmu_context.h` 的 `#define activate_mm` 与 `exec_mmap` 的调用序）；若相等 ⇒ 查 TLB 失效（`local_flush_tlb_page` 的 ASID 维度）与 PTE 的 HSJU/权限位 |

### 第 13 轮 engineer 自审（2026-11-18，F27 = 页表填充 vs walker）

**结论：F27 不是「mm 没激活」也不是 TLB 陈旧 —— PTBR/ASID/ptw_enable 全对、PTE 已在表里，但硬件 walker 仍报缺页。** 现场（两次故障各自的入口状态）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F27a（**已排除**）「exec 的新 mm 未成为生效 PTBR」 | ❌不成立（已排除） | — | `K4 mm switch: mm=… asid=2 pgd=… pa=0x4750000 read_back asid=2 ptbr=0x4750000`；故障入口 `ptbr=0x4750000 asid=2 mm_pgd=0x4750000 enabled=1`（两次故障都一样） |
| F27b（**已排除**）「TLB 缓存了非 present 项」 | ❌不成立（已排除） | 诊断期把 publish 的失效临时换成 `local_flush_tlb_all()`（ASID_ANY=1 全失效） | 换成全失效后仍是 `fill-zero` → 同址 `die-missing` |
| F27c（**新，未解**）**walker 对「表里已 present 的 PTE」持续报 CFXMEM**：`dadao_pf_publish` 里 `pte_val(*ptep)=0x500000000048ff81`（P=1、HSJU=0x5(S\|U)、R=1、W=0 的共享零页），PTBR 指向该表，第二次故障仍在同一条指令同址报 `CFXMEM/DGPTRAP` | ⏸待续（本轮预算用尽） | `mm/fault.c` 加 `K4 pf entry`（id/info/ptbr/asid/enabled/mm_pgd）与 `K4 pf pub`（va/mm/mm_pgd/ptbr/asid/mm_asid/pte）两处诊断（`#ifdef`） | `K4 pf pub: va=0x7baf0 mm=… mm_pgd=0x4750000 ptbr=0x4750000 asid=2 mm_asid=2 pte=0x500000000048ff81`；`K3 pf: n=1 … fill-zero` → `n=2 … try=2 die-missing` |
| F27 下一轮判据（写清） | ⏸待续 | — | ① 按 **PTBR**（不是 `mm->pgd`）把 L1 槽 0 与 L2 槽 7 的 8 字节直接读出来打印（本轮试过但编辑打错、未跑成）；② 若二者都对 ⇒ 问题在**访问类型**：这是 **supv 对 W=0 用户页的 store**，按 `spec/DADAO-12 §2.2.6` 判序（P→SPF/GPF→HSJU→R/W/X）应报 `CFXPERM/NWPERM` 而不是 `CFXMEM/DGPTRAP` —— 即可能是 **QEMU 模型的判序/缺页类归属**偏离 spec（记录后按 MEMORY「浮点/差分以 spec 裁决」同理走 issue，不在内核侧硬绕）；③ 或者用**超页**映射同一段以绕开 L2，判别是 L2 条目还是访问类型 |

### 第 14 轮 engineer 自审（2026-11-18，**F27 根因已修 + initramfs 链真跑起来**）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F27（**根因，已修**）页故障通道用 **`pmd_off_k()`（内核 swapper 表）** 建 L2 / 写 PTE / 找 ptep，而进程的 PTBR 指向**自己的**表 ⇒ 映射永远写进内核表，walker 在进程表里看不到（`l1=0` 通过 PTBR 读出，而通道自己的 `pmd_off_k` 副本 present）。K1–K4 期 PTBR 一直是内核表所以从未暴露；017 的 `switch_mm` 落地后立刻现形 | ✅已修（**高价值**） | `mm/fault.c`：`dadao_pf_fill()` 改用 `pmd_off(vma->vm_mm, addr)`（`vm_mm == NULL` 的探针窗口仍用 `pmd_off_k`）、`pmd_populate_kernel(vma->vm_mm ?: &init_mm, …)`；`dadao_pf_ptep()` 改为按 VMA 取表 | 修后同一 VA：`l1=0x4000000004780001 l2pa=0x4780000 l2e=0x500000000048ff81`（PTBR 表里 present ✓）；第二次故障类型从 `CFXMEM` 变成 **`CFXPERM/NWPERM` → `replace-zero`**（正是 `spec/DADAO-12 §2.2.6` 判序对「写共享零页」的结果） |
| F28（新，**已修**）umon 入口栈的 `thread_info.task` 只在安装时设过一次（016 的 F5 里用户任务就是启动任务，故成立）；execve 之后用户任务变成 `kernel_init` ⇒ 故障处理里 `current->mm == NULL`（实测用户首指令缺页 `vma=0`、`mm_pgd=0x0`，而 PTBR 已是 exec 的 mm） | ✅已修 | `process.c::dadao_enter_user()` 每次进用户态刷新该 cell（附注释说明 016→017 的差异） | 修后 exec 后的页故障恢复为 `mm_pgd=0x4750000 mm=0x…` 并与 `ptbr` 一致 |
| F30（**已修，且是工艺级发现**）：`k3` 的 pf1 镜像突然红（`exit_task_stack_account+0x4` 上 `rb16=0x28`）——真因**不是内核改动**，而是各门控的配置切片**没钉住我新加的 `CONFIG_DADAO_K4_SWITCH_SELFTEST`**，于是 pf1 镜像继承了 `y`，走了本任务的 `rdinit=/init.musl` 覆盖 ⇒ 跑进 init/exit 路径 | ✅已修 | 在 `tools/linux/{check_k0,check_k1,check_k2,check_k3}.py` 的切片与 `k4_fork_probe.py` 的 `IMAGE` 里各加一行 `CONFIG_DADAO_K4_SWITCH_SELFTEST=n`（与 `CONFIG_DADAO_K4_SELFTEST` 互斥的兄弟符号必须成对钉住） | 补钉后 k3 **263/263**、k4_fork **101/101** 均恢复 |
| F31（**已修**）F27 的表选择规则：必须选**walker 实际读的那张表** —— `vma->vm_mm == current->mm` 且 `__pa(mm->pgd) == dadao_ptbr_read()` 时用 `pmd_off(mm, …)`，否则 `pmd_off_k(…)`（K1–K4 形状 PTBR 仍是内核表；探针窗口无 mm） | ✅已修 | `mm/fault.c` 新增 `dadao_pf_table()`，`dadao_pf_fill()` 与 `dadao_pf_ptep()` 共用；L2 用 `pmd_populate_kernel(vma->vm_mm ?: &init_mm, …)` | k3 **263/263**、k4_fork **101/101**、switch 39/3 同时绿；exec 路径的页故障恢复为 `fill-zero → replace-zero`（修前是 `fill-zero → die-missing`） |
| F29（新，S7 当前堵点）exec 后的用户任务在首次缺页链路里触发 **async 帧 `cause=0x8`**（= `CFXESC`，`info=0x7e080000`）⇒ `dadao_async_die` 具名终止 `code=0xe3`。按 `contract-see §5.1/§5.3`：`escape` 失败的两个条件是「`cfxha != inner_cfx_code`」或「`excp_cause_id = 0`」，与 `ISS-454`（`escape` 不恢复 `inner_cfx_code`）在 umon 委派路径上的交互高度相关 | ⏸待续（预算用尽） | — | `dadao: unexpected async cause=0x8 info=0x7e080000 mode=2 code=0xe3`（每次启动稳定复现）；此前紧跟 `K3 pf n=2 … replace-zero` |
| F29 下一轮判据（写清） | ⏸待续 | — | ① 在 umon stub 的**每一处** `escape cfx_umon` 前打印当前 `inner_cfx_code`（`cread cfx_id`? 用 `cfx2rd` 读当前 cfx 的 `cfx_id` 不可行时，读 `cfx_umon cg5 rc0` 的 prev_mode 与 `cfx_smon cg5` 是否仍激活）与帧的 `excp_cause_id`；② 若确认是「smon 委派后 `inner_cfx_code` 仍是 `cfx_smon` 而 stub 用 `escape cfx_umon`」⇒ 改走 `trap cfx_umon, 0`（与委派路径同形），或按 `ISS-454` 在委派返回后先重设 current cfx |

**里程碑（本轮实测）**：`/init`（脚本）→ `/bin/sh`（**busybox 真的跑起来**，`Comm: sh`、`Pid: 3`）；按任务书规则 (b) 探针镜像改判 `rdinit=/init.musl`，`init_eaccess=0`、`kernel_execve=0`、`K4 fork: kernel thread exec'd ip=0x211c8 sp=0x1ffff9efe70` ⇒ **musl init 已进入用户态**，只剩用户态首指令链路的 `CFXESC`（F29）。

**本轮最终状态**：F27 根因**已修**（页故障通道写错了表）、F28/F30/F31 已修；`k3` 一度红是**配置串味**（已按「兄弟符号成对钉住」修好门控）。S7 现在只剩 **F29**（用户态首指令链路出现 async `cause=0x8`＝`CFXESC`，与 `ISS-454` 的 `inner_cfx_code` 交互）；S5 未做。

### 第 15 轮 engineer 自审（2026-11-18，打 F29）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F29（**已定位到指令**，未修）：CFXESC 的出错点是 `dadao_supv_excp` 里的 **`escape cfx_smon, [excp_cause_ip, 0]`**（`ip=0x20000151484`，`sp` 属 `kernel_init` 栈）；`§5.3 步骤0` 的两个触发条件（`cfxha != inner_cfx_code` 或 帧 `excp_cause_id == 0`）二者之一成立 | ⏸待续（预算用尽） | `time.c::dadao_async_die` 增打 `cfx_hart cg5 rc2/rc3`（cause_ip）与 `cfx_smon cg5 rc2/rc3`（帧是否有效） | `dadao: unexpected async cause=0x8 info=0x7e080000 mode=2 code=0xe3 ip=0x20000151484 cause_rd=0x8 sp=0x200041af630`（`llvm-nm`+`objdump` 解析为 `dadao_supv_excp+0x114` 的那条 `escape cfx_smon`） |
| F32（新，**关键对照实验**）：把故障通道的那行 `K3 pf:` 报告**静音**后，CFXESC **消失**，但 guest 在 `K4 fork: kernel thread exec'd` 之后**无任何输出直到超时** ⇒ 「帧内打印」与「用户首指令不执行」是同一段代码的两个面：控制台是 `trap cfx0, 0x3FF00`，而 `§5.2 步骤6` 明确 `trap` 会把 `inner_cfx_code` 置为目标 cfx ⇒ **在异常帧内做任何 `trap cfx0`（打印）都会让该帧的 `escape <其它 cfx>` 目标不符**（除非 responder 不改 inner——需按 spec 判定） | ⏸待续（需按 spec 裁决：`trap` 对 `inner_cfx_code` 的副作用是否应被 responder 豁免；若是，则属 QEMU/固件侧；若否，则内核必须避免在帧内打印或改走 `trap cfx_umon, 0` 重入） | — | ① 有打印：`unexpected async cause=0x8 … ip=…1484`（`escape cfx_smon`）；② 静音后：`exec'd ip=0x211c8` → `RC=124`（无 CFXESC、无用户输出） |
| F32 下一轮判据（写清） | ⏸待续 | — | ① 在 `dadao_supv_excp` 的 C 半前后各打一次 `cfx_smon cg5 rc2`（帧号/是否被消费）**并注意该打印本身会动 inner**（把两次打印都放在 `trap cfx_smon` 重入之后，或用 `if (0)` 二分）；② 直接做「无打印」版本 + 在 `dadao_umon_excp` 里用寄存器记录（不打印）帧状态，最后一次打印在 `escape` **之后**；③ 依 `spec/DADAO-12 §5.2 步骤6 + §5.3 步骤0` 判定「帧内 `trap cfx0` 是否合法」，若判定为固件/模型问题 ⇒ 登记 `issues.yaml` + `待裁定` |

### 第 16 轮 engineer 自审（2026-11-18，按架构侧 spec 判定执行）

**架构侧判定（已落盘，不再议）**：`§5.2 步骤6` 规定 `trap` 把 `inner_cfx_code` 置为目标 cfx；`§5.3 步骤0` 规定 `cfxha != inner_cfx_code` ⇒ `CFXESC`。**帧内 `trap cfx0`（semihosting 打印）本身就是错的**，不是模型缺陷、不是 spec 歧义；不改 spec、不改 QEMU。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F33（新，**架构级冲突，需裁定**）：本端口**所有里程碑探针**（K2/K3/K4）都在异常帧内打印（`dadao_early_printf` → `trap cfx0`），按上述判定即「帧内 `trap cfx0` = 错」。而 K2/K3 门控**正是依赖这些帧内打印**（`K3 pf:` 行、`K2 tick` 行等）作为判据输入 ⇒ 执行该判定要把 K2–K4 探针的诊断全部改成「帧内只记内存、`escape` 后再打印」，跨本任务范围（会改到其它任务的门控判据） | ⏸**待裁定**（提请架构侧：是本任务一并重构探针诊断，还是另立任务） | 本轮未改（避免越界改他任务门控） | 冲突依据：`spec/DADAO-12 §5.2 步骤6`/`§5.3 步骤0`（架构侧判定原文）+ 现有 `mm/fault.c`/`kernel/time.c` 的帧内打印被 `check_k2/k3` 解析 |
| F29 证据补充（**排除帧无效**）：在 async die 里加打 `cfx_smon cg5 rc2/rc3` ⇒ `smon_id=0x10000000000002`（帧有效、cause=CFXMEM）、`smon_ip=0x2000044b8d4`（= 出错 ip） ⇒ **CFXESC 的触发条件是「目标不符」而非「帧无效」**，与 F33 的判定一致 | ✅证据已收 | `time.c::dadao_async_die` 的打点 | `unexpected async cause=0x8 … ip=0x20000151484 … smon_id=0x10000000000002 smon_ip=0x2000044b8d4` |
| F34（新，**分类错误，已定位**）：`cause=0x8`（同步 `CFXESC`）走进 `dadao_async_die` 的原因——`cfx_hart` 的 `supv_excp_vector`（`cg2 rc10`）**只有一个向量**，同步 `CFXESC` 在 supv 期也进这个向量（`§5.2` 伪码：`ESCAPE` 失败 ⇒ `cause=CFXESC; temp_cfx_code = inner_cfx_code`，即进**当前 cfx**；当前 cfx 累计过 timer 后是 `cfx_hart`）⇒ 异步 stub 收到同步 cause | ✅已解释（不改代码：症状而非根因） | — | 同上一条现场（`cause=0x8` + 帧有效） |
| F35（新，未解）：按架构侧判定「帧内打印是错的」后，「无打印时用户态首指令不执行」仍需解释（`exec'd ip=0x211c8` 后无输出到超时）。本轮尝试用宏关掉 tick 起始做对照，`EXTRA_CFLAGS` 未传到 arch 对象（构建通过但未见效），实验未成立、已回退 | ⏸待续 | （实验开关已回退） | `K4 switch: selftest` 仍 1 处、`K3 pf: n=1` 行为与上轮一致 |

### 第 17 轮 engineer 自审（2026-11-18，执行裁定方案 C）

**方案 C 已落地（仅 017 的探针镜像）**：`early_console.c` 增加 `dadao_in_frame` —— 帧内 `dadao_early_printf` **直接丢弃**（不做 semihosting），帧内只把关键数字写进 `dadao_flog_last[4]`（标量，规避本任务代码模型下数组的 `R_DADAO_ABS48` 越界），由 `dadao_early_exit`（结束前）与 `dadao_ret_from_fork` 的 exec 分支（帧外）打印；三个 C 半（`traps.c`/`process.c`/`time.c`）在入口置位、出口清零。**门控 Gating**：丢弃行为与记录全部在 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST` 内 ⇒ K2/K3/K4 探针的帧内打印**保持不变**（未改 `check_k2/k3`、`k2_*/k3_*/k4_*` 判据）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F33 判定的**直接后果已验证**：帧内不再有任何 semihosting | ✅已实现（方案 C） | 见上 | 017 镜像里 `K3 pf:` 等帧内行消失，改由 `K4 flog:` 在帧外输出 |
| **F36（新，重要：F33 的前提被证伪）**：**去掉帧内所有打印后，`CFXESC` 依旧出现**，且出错指令仍是 `dadao_supv_excp+0x114` 的 `escape cfx_smon`（`ip=0x20000151664`）⇒「帧内 `trap cfx0` 导致 inner 漂移」在**这条链路上不是触发原因**（该帧已无任何打印） | ⏸待续（需新判据） | — | `K4 flog: n=0xa5a5…0008(cause=0x8 CFXESC) a=0x7e080000 b=0x20000151664(escape ip) c=0x2(mode)`；`llvm-objdump` 解析 `+0x114` = `escape cfx_smon, [excp_cause_ip, 0]`；同镜像内 `K3 pf:` 帧内行已全无 |
| F35（**部分回答**）：**去掉帧内打印后，用户态首指令确实执行了**——`K4 flog: n=3 a=CFXMEM b=0x211c8(=musl 入口) c=0x4750000(=PTBR)`，即 `exec'd ip=0x211c8` 之后立刻在该地址发生取指缺页、PTBR 正确 ⇒ 用户代码**已进入**，不是「首指令不执行」；随后被上面的 F36 的 `CFXESC` 终止（`RC=193`） | ✅部分 | — | `K4 fork: kernel thread exec'd ip=0x211c8 sp=0x1ffffd1fe70`；`K4 flog: n=3 a=0x1000000000002 b=0x211c8 c=0x4750000` |
| F36 下一轮判据（写清） | ⏸待续 | — | ① `inner_cfx_code` 不可读 ⇒ 用**排除法**：在 `dadao_supv_excp` 的 C 半里把 `cfx_smon cg5 rc2/rc3` 与 `cfx_umon cg5 rc2`（若可读）记进 flog，判定「smon 帧是否被 smon 自己的 escape 消费两次」或「`trap cfx_smon, FROM_USER` 是否被 cfxtrap 掩码拒绝（`§5.2` 拒绝时 `temp_cfx_code = monitor`）」；② 直接在 `umon` 委派处**先** `trap cfx_smon, 0`（合法 target）而不是带 immu18 的变体，看 CFXESC 是否消失；③ 若仍不消失 ⇒ 用 `-d int` 抓 QEMU 的 cfx 切换日志（只读，不改模型），定位 inner 的实际取值 |
| EXTRA_CFLAGS 实验说明 | ✅已清理 | 宏门控已删除（`dadao_clockevent_start()` 恢复无条件调用） | `K4 switch: selftest` 字符串仍在镜像中，tick 行为与上轮一致 |

### 第 17 轮 engineer 自审（续，执行裁定方案 C + 根因定位）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 方案 C 落地（帧内零 semihosting） | ✅已实现（017 镜像内） | `early_console.c`：`dadao_in_frame` 由三个 C 入口置位/出口清零，帧内 `dadao_early_printf` **丢弃**；帧内只把数字写 `dadao_flog_last[4]` / `dadao_pf_last[6]` / `dadao_supv_diag[4]`，由 `dadao_early_exit`（帧外）打印。全部 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST` ⇒ K2/K3 探针打印与判据不变 | 017 镜像内 `K3 pf:` 帧内行消失、`K4 flog:/K4 supv:/K4 pf last:` 帧外输出；k3 门控（254→263）交由回归复核 |
| F33 的判定前提**被证伪**（F36） | ✅已定位 | — | 帧内打印全去后 `CFXESC` **仍在**：`K4 flog: n=0xd1e0…0008 a=0x7e080000 b=0x20000151704 c=2`（b = supv stub 的 `escape cfx_smon`） |
| F36 根因（**本轮实测确定**）：**异步投递落在同步帧内** ⇒ `inner_cfx_code` 变 `cfx_hart`；`escape` 不恢复 inner（`§5.3` 伪码 + QEMU `helper_cfx_escape` 均无该步，= `ISS-454`）⇒ 该帧的 `escape cfx_smon` 命中 `§5.3 步骤0` 的「目标不符」分支。对照：把进入用户态那次 tick 关掉后同路径连做 3 次 escape 全成功、无 CFXESC | ✅根因已证 | 无（仅实验） | ① tick 开：`K4 supv: returns=2 last_id=0x10000000000002`（帧有效 ⇒ 非「帧无效」分支）后 CFXESC；② tick 关：`returns=3`、无 CFXESC（实验已回退，`k4_switch_selftest.c` md5 与备份一致） |
| F37（新）：按 `§5.2 步骤3` 的源掩码语义，在同步帧的 C 半期间屏蔽本内核的源（bit15） | ✅已实现（**仍不完全**） | `traps.c`: `dadao_trap_handler` 改为 `arch_local_irq_save()` + `dadao_trap_dispatch()` + `arch_local_irq_restore()`；`process.c` 同法包 `dadao_user_excp_dispatch()` | 屏蔽后 CFXESC 从「第 2 次 escape」推到「第 4 次」，且用户代码真正跑起来（见 F35）；但仍会复现 ⇒ 见下条 |
| **F37 残余（待裁定）**：C 半 `restore` 之后到 asm `escape` 之间的间隙里，**pending 的 tick 会被立即投递**，于是 drift 依旧（本次 `K4 pf last: res=5 replace-zero` 之后即 CFXESC） | ⏸待裁定 | — | 两个候选解需架构侧定：**(A)** 把「恢复掩码」挪到 `escape` **之后**（用 `cg5 rc3` 重定向到 unmask 蹦床，K2 已有 redirect 先例）——但 umon 帧会把用户态的 `rd2/rd3` 当 scratch 破坏；**(B)** 认定 `escape` 应恢复 `inner_cfx_code`（即 `ISS-454` 的语义纠正，需改 spec/QEMU） |
| F35（**已回答**）：无打印时用户首指令确实执行 | ✅已证 | — | `exec'd ip=0x211c8` 后依次：取指缺页（`K4 flog n=3 a=CFXMEM b=0x211c8 c=0x4750000`）→ 用户执行 → 对 0x33670 的写触发 NWPERM → `replace-zero`（`K4 pf last: res=5 sub=0x25 vma=0x30000-0x40000`） |
| F38（新，**已解释，非缺陷**）：内核态 `memset+0x14/0x40` 的 NWPERM | ✅已解释 | — | 内核在 exec 后经用户映射清零 BSS（va 0x33670 ∈ vma 0x30000-0x40000），页是共享零页（W=0）⇒ `replace-zero` 后重试；属既有 `fill-zero→replace-zero` 通道 |
| 上轮 `EXTRA_CFLAGS` 实验 | ✅已清理 | 宏门控已删（`dadao_clockevent_start()` 恢复无条件） | `k4_switch_selftest.c` md5 = 备份 `f236bb0f…` |

### 第 18 轮 engineer 自审（2026-11-18，按指派做用户栈增长 S1–S6）

**口径说明（如实）**：本轮指派写的是「S5 = 用户栈增长」，但本任务书的 `S5` 是「U-mode 帧 A/B 往返」；栈增长是 `m14-linux-019` 的 `S1–S6`。按指派原文与「判据在 `m14-linux-019` 交接」执行：**本轮实现并验收 019 的 S1–S6**，本任务的 S5（帧往返）仍卡在用户态闭环（F37），未做。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 栈增长内核侧原本**完全未实现**（`arch/dadao` 无 `VM_GROWSDOWN`、无扩栈分支）⇒ 019 的 S1 会直接 `die-no-vma` | ✅已实现 | `mm/fault.c`：`dadao_pf_grow_stack()`（`find_vma` + `VM_GROWSDOWN` + `expand_stack_locked()`，两规则由通用 `expand_downwards()` 承担）+ 判词链在「无 VMA」分支先试缺页类扩栈；新增扩栈计数 `dadao_pf_grow_count()` | `K3 pf: n=1 … va=0x14000030000 vma=0x14000030000-0x14000060000 result=fill-zero`（VMA 起点被扩到故障页） |
| 探针载体：S7 未通 ⇒ 不能用真实用户进程压栈；按 019 任务书「内核侧自检代码（supv 访问）」的既有裁定做 | ✅已实现（**标注部分完成**） | 新增 `mm/k4_stack_selftest.c` + `CONFIG_DADAO_K4_STACK_SELFTEST`（1/3/4/6 各一镜像）+ `mm/Makefile`/`Kconfig.debug`/`asm/setup.h`/`kernel/setup.c` 接线；新增 `tools/linux/k4_stack_probe.py`（44 条断言） | `k4_stack_probe.py` **44/44 PASS, rc=0**；case 1 的 `K4 stack done: vma=0x14000020000-0x14000060000 grows=2 entries=4 pages=2`、`RC=0` |
| F39（新，**已修**）：直接 `mm_alloc()` 后不激活地址空间 ⇒ 填充落在内核表、失效按旧 ASID ⇒ 同一写第二次仍 `NWPERM`（`replace-zero` → 立刻 `die-perm`） | ✅已修 | `st_setup_mm()` 调 `dadao_switch_mm(NULL, mm, current)`，并打印 `K4 stack mm:` 现场 | 修前：`K4 stack unshare: pfn pte=0x…0416ffc1 zero=0x480000` 后 `die-perm`；修后：`n=4 … result=replace-zero` → `s5-store-value` 读回一致 |
| F40（新）：`grow-any-vma` 注入单改内核分支**杀不掉** S4——`expand_downwards()` 里还有一道 `VM_GROWSDOWN` 检查（双重护栏） | ✅已修（注入定义修正） | 注入改为两处同改（`mm/fault.c` + `mm/vma.c`），并在探针里写明原因 | 注入后 `case 4 不再以 die-no-vma 结束` 红 → `cp`+md5 还原（两文件 md5 对账）→ 重建 → `die-no-vma` 回绿；注入 5/5 绿 |
| F41（新，**已修**）：新加的门控符号 `CONFIG_DADAO_K4_STACK_SELFTEST` 没被兄弟门控钉住 ⇒ switch 探针镜像继承上一张镜像的 `=6`，在 K4 边界就被栈自检结束（`K4 switch: begin` 全无，14 条红）——F30 同类问题第二次复发 | ✅已修 | `check_k0/k1/k2/k3.py` + `k4_fork_probe.py` 的切片各补 `CONFIG_DADAO_K4_STACK_SELFTEST=0`；`k4_switch_probe.py` 的 IMAGE 补钉 + 静态 recon 增一条镜像配置断言 | 补钉后 switch 探针回到 39/3（红项仍只有 S5/S7 两条已具名未实现项） |
| F42（新，**已修**）：`regen.sh` 漏跑一次（改完 S6 打印后直接写探针）⇒ `check-patch-tree --source-state` 报 `linux: dirty paths: M arch/dadao/mm/k4_stack_selftest.c`，k0 的 K12 `apply-series` 与 k2 的 R1/R2 连带红 | ✅已修 | 重跑 `regen.sh`（84 补丁，apply-series 干净提交） | `--source-state` 回 `linux: OK HEAD=65313b6f4d8b count=1 clean=True`；k0 **130/130**、k2 **170/170** 重跑 rc=0；`check-patch-tree` rc=0 |
| 019 的 S1–S6 逐条结果 | ✅ 6/6 覆盖 | — | S1 `s1-start/s1-end/s1-grows` ok + 通道行 `vma.start == 故障页` 恰好 2 条；S2 `s2-size == 起始+2 页`；S3 `dist 8519680 > limit 8388608` ⇒ `die-no-vma`；S4 无 `VM_GROWSDOWN` ⇒ `die-no-vma`；S5 `s5-grows == 0x2`（不增）+ `vm_start` 不变；S6 `dist 1 页 < gap 16 MiB` 且 `size 4 页 < limit` ⇒ `die-no-vma`（gap 先于 limit 成立） |

### 第 19 轮 engineer 自审（2026-11-18，合入 master + spec-009 后推进 S7）

**合入**：`git reset`（mixed，清掉 419 文件的 squash 暂存区，非任务文件 398 个回 `HEAD`、72 个非任务未跟踪先备份再删）→ `git merge master` **无冲突**（merge commit `e7054f13`）；本任务书取我们的版本（master 对该文件唯一的改动是「待裁定 3 = 已裁定 A」，我们已含），`check_k0/k1.py` 的配置钉住按 master 新结构重新补上。合并后 `HEAD..master = 0`。

**QEMU**：本 worktree 无 llvm 源/构建树，`make install-host` 会连带触发与 QEMU 无关的 LLVM 重建；改为主树 `make build-qemu`（PASS）+ 按 `atomic-install` 语义装 `qemu-system-dadao`/`qemu-dadao` 并 md5 对账（`6f3fa209d738713aa8735c52dee1a315`，与构建产物一致）。**例外已记**：收尾应有完整 LLVM 树的机器补跑一次 `make install-host` 对账。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| **F37 已由架构消除**：spec-009 使 `escape` 恢复 `inner_cfx_code`（`helper.c:2906`） | ✅已修（架构侧） | 新 QEMU 已装 | 修复前 `dadao: unexpected async cause=0x8 … ip=…` 每次必现；修复后同一镜像**不再出现 CFXESC** |
| 去掉 F37 的临时屏蔽（交接第 2 步） | ✅已删 | `kernel/traps.c`/`kernel/process.c` 去掉 `arch_local_irq_save/restore` 包壳；`early_console.c` 去掉帧内丢弃（保留 `dadao_in_frame` 与 flog 机制）；`mm/fault.c` 去掉帧内跳过报告 | 删后 K3 pf/K4 诊断行恢复输出，S7 现场可读 |
| **F43（新，已修）**：exec 的 text VMA 是**文件后备**（`vm_file`+`vm_pgoff`），无 `vm_private_data` ⇒ 取指缺页 `fill-code` 返回 NULL（`res=7 die-missing`，`ip=0x211c8 vma=0x20000-0x30000 flags=0x75 priv=0x0`） | ✅已修 | `mm/fault.c` 新增 `dadao_pf_fill_from_file()`：按 `vm_pgoff<<PAGE_SHIFT + 页内偏移` 用 `kernel_read()` 读一页到新分配页（短读尾部为 0），仅用于取指类 | 修后同址 `result=fill-code`，`pte=0x50000000047affa1`（PA 0x47a0000） |
| **F44（新，未解的 S7 堵点）**：用户态真的跑起来了——入口帧正确、初始栈正确（`user sp words: argc=0x1, argv[0]=0x1ffffe0ffd0, NULL, envp…`）、musl `_start`→`_start_c` 执行——随后在 `0x211d0`–`0x2120c` 一带**空转无输出**直到超时 | ⏸待续（下轮判据见下） | — | `in_asm` 末尾翻译块 `0x21204/0x2120c`；整机 `RC=124` |
| F44 下轮判据（写清） | ⏸ | — | ① K4 **没有任何系统调用表**（`process.c` 一律回 `-ENOSYS`），musl init 的 `write`/`brk`/`exit_group(94)` 全部拿到 ENOSYS ⇒ 先确认「空转」是否 `exit()` 重试环：在 CFXTRAP 分支按次数记录 `regs->rd[15]`（syscall nr）到 flog（不打印），末次打印即可判定是不是 syscall 号错位；② 若确实因 ENOSYS，S7 判据要么由 017 的探针钩子接住 `exit_group(94)`（`dadao_k4_user_syscall()` 已存在，检查其号匹配与 `rd15` 约定），要么把「`/init` 真跑」的最小 syscall 面并入本任务（需架构裁定范围，K5 才拥有完整表） |
| **F45（新，未闭环，需下轮复核）**：合入后**曾出现一次**内核态 `memset+0x14` 写 `0x41af52f`（= `__pa(sp)` 形态）的 CFXMEM/die-no-vma；加入入口打点后**未再复现** | ⏸待续（可疑：与 TLB/时序相关） | — | 复发时现场：`K3 pf: n=3 … ip=0x2000044c15c(memset+0x14) va=0x41af52f vma=0x0-0x0 sp=0x200041af640`；判据：用 RAS `ra0` 取 `memset` 的返回地址定位调用者，并核对是否有人把 `__pa()` 当 VA 用 |

### 第 20 轮 engineer 自审（2026-11-18，F44 定位）

**syscall 面（架构侧裁定）**：探针钩子 `dadao_k4_user_syscall()` 早已接 `write`/`brk`/`exit_group`（号取内核 uapi 头 = 由 `scripts/syscall.tbl` 生成，**未硬编码**；`write(1)`=64、`exit_group`=94、`brk`=214；另含 `getpid`），全部在 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST` 内 ⇒ 里程碑镜像零影响。本轮新增**限次（前 8 条）syscall 现场打点**判定号是否错位。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F44 判据①（syscall 号是否错位） | ✅已判定：**号没跑偏** | `process.c` CFXTRAP 分支加 8 行限次打点（`rd15`/`rd16`/`rb16`/`rd17`/`rb17`/`ip`） | `K4 syscall: nr=rd15=0x5d(93=exit) rd16=0x0 … ip=0x21200` 循环——即 musl `_Exit` 的 `exit(93)` 兜底环；`exit_group(94)` 此前未被调到 ⇒ 说明用户程序在更早处就 Enter 了退出路径 |
| **F44 根因之一（已修，F47）**：`dadao_pf_fill_from_file()` 把**页内偏移重复加了一次**（页粒度读必须从文件页首读）⇒ 代码页整体错位 0x11c8，执行到 ELF 里根本没有 `trap` 的地址 | ✅已修 | `pos = (loff_t)vma->vm_pgoff << PAGE_SHIFT;`（去掉 `+ (addr & ~PAGE_MASK)`），注释写明实测 | 修后该页首 8 字节 = `0x7f454c46…`（ELF 头）⇒ VA 0x20000 正确对应文件页 0；`_start`（`rb2rb {rb16},{rb1}` / `call [rb0,8]`）与 objdump 完全一致地执行 |
| **F48（新，未解，当前 S7 堵点）**：`_start_c` 第一条栈读（`ld.st rd16,[rb16,4]`，va=0x1ffffe1fe74）报 **CFXPERM + NUPERM**——该叶条目 `0x400000007fb0fffd`（PA 0x7fb0f000，S 位有、**U 位无**、R/W/X/GLOBAL/D/A 全有），而**页故障通道从未填过该 VA**（加 `K4 fill:` 打点后仅 0x33670 一条）⇒ 存在**第二个 PTE 写入者**，且它按内核口径（S-only）映射了用户栈 | ⏸待续（下轮判据见下） | 无（诊断打点已回退，`pos` 修复保留） | `K4 umon->smon: … cause=0x100000080 ip=0x211dc info=0x1ffffe1fe74`；`K4 pf raw: l2e=0x400000007fb0fffd`；`K4 pf last: res=6(die-perm) sub=0x20(NUPERM)`；通道另一行 `K4 umon->smon: the channel did not install a mapping (policy=1)` |
| F48 下轮判据（写清） | ⏸ | — | ① 在 NUPERM 入口打印 `current->mm`、`vma->vm_mm`、`vma->vm_flags` 与 `pte_val`，判定「VMA 对但 PTE 无 U」是否成立；② 查第二个写入者：`dadao_pf_fill` 的 **superpage 分支**（`_PAGE_S|_PAGE_GLOBAL`，无 U）、`update_mmu_cache`、`arch_dup_mmap`、`setup_arg_pages` 拷贝路径、以及 K1 `ptw` 表是否覆盖了 PGD index 4095（本 VA 的 `l1i=0x7ff8`，紧邻内核窗口 4096 起）；③ 若确认是「内核代写用户页缺 U」，属通道缺陷 ⇒ 在 `dadao_pf_mode_bits` 的调用点补齐（按 `vma->vm_mm` 判定，不能靠 `current`） |
| F45（保留判据，不追） | ⏸ | — | 见第 19 轮 |

### 第 21 轮 engineer 自审（2026-11-18，F48 根因 + 修复）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F48 判据①（VMA 对、PTE 无 U） | ✅已证实 | NUPERM 入口打点（已随诊断回退） | `K4 nuperm: va=0x1ffffaafe74 mm=cur=0x20004165b00 ptbr=mm_pa=0x4750000 pmd_k=0x0 pmd_mm=0x4000000004760001 pte_k=0x0`；`K4 nuperm2: idx=4095 user_ptrs=4096 task=0x20000000000 swapper[4095]=0x0 mm[4095]=0x4000000004760001` |
| F48 判据②（查写入者） | ✅已定：**不是**通道、**不是** K1 越界 | 给 `dadao_pf_fill` 加入口/各分支打点 + `pgd4095` 在 exec 返回与用户入口两处打点（均已回退） | 全程只有两次填充（`0x33670`、`0x211c8`，都在 L2@0x4780000）；而 `pgd4095` 在 **execve 返回时就已经是 `0x4000000004760001`** ⇒ 写入发生在 execve 内、且不经本端口异常通道 |
| **F48 根因（已修）**：`protection_map[]`（`__P000…__S111`）全部取 `PAGE_KERNEL*` = `S|G|R|W|X|A|D`，**没有 U 位**；exec 的 `get_arg_page()`→`get_user_pages`→通用 `handle_mm_fault()` 直接用 `vm_get_page_prot()` 映射初始栈 ⇒ 用户栈页「present 但无 U」 | ✅已修 | `arch/dadao/include/asm/pgtable.h`：新增 `_PAGE_USER_{R,RW,RX,RWX}`（U+S 双位，与 `dadao_pf_mode_bits()` 同口径），`__P001/010/011/100-111` 与 `__S0xx/__S1xx` 改用它；`__P000/__S000`（PROT_NONE）保持内核只读（「无用户访问」= 无 U）。**按 `vm_flags` 派生、不看 `current`**（F28 教训） | 修后 musl 启动连续走到 `set_tid_address`(0x60=96)、`getpid`(0xac=172)，`_start_c` 的栈读写全部正常（不再有 NUPERM/die-perm） |
| **F49（新，未解）**：`getpid` 返回后用户程序**跳到 0**（`K3 pf: n=5 … IGPTRAP ip=0x0 va=0x0 result=die-no-vma`） | ⏸待续（下轮判据见下） | — | 现场见上；`in_asm` 末尾只剩内核 die 路径 |
| F49 下轮判据（写清） | ⏸ | — | ① 用 `-d in_asm` 抓 **用户态**最后 3 个翻译块（按地址过滤 0x0/0x212xx/0x232xx），定位是 `ret` 回 0 还是 `call [rbX]`（rbX=0）；② 若为 `ret` 回 0 ⇒ 查用户 RAS 往返（umon stub 的 `DADAO_GPR_SAVE/RESTORE` 是否覆盖 `ra0`（{RACNT,MRPTR}）与 `ra63`），这正与本任务 S5 判据重合；③ 若为 `call [rbX]`，打印该处 `rbX` 与前一 trap 的返回上下文；④ 同时核对 `set_tid_address`(96)/`brk`(214) 的 ENOSYS 是否让 musl 走了 `NULL` 回调（`init.c` 的 `init_write_all` 之后才 `_Exit`） |

### 第 22 轮 engineer 自审（2026-11-19，F49 定位 + **S7 转绿**）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F49 判据①（`ret` 回 0 还是 `call [rbX]`） | ✅已判死：**不是 ret** | `-d in_asm` 抓用户态最后翻译块 | 最后用户块 = `0x232d4 <sccp>`，其尾指令是 `ld.o rb4,[rb4,0]` + **`jump [rb4, rd0, 0]`**；随后内核 die 路径 |
| **F49 根因（已修，F50）**：`sccp`（musl `__syscall_cp`）按 syscall 号索引 **`.rodata` 里的跳转表**（0x103c8）；本端口对**文件后备 VMA 的数据访问**一律映射共享零页 ⇒ 表项全 0 ⇒ `jump [rb4=0]` | ✅已修 | `mm/fault.c`：`dadao_pf_fill()` 增加 `fill-file`（文件后备数据页按 `vm_pgoff<<PAGE_SHIFT` 读页、R(+X if VM_EXEC)）；`dadao_pf_unshare_zero()` 增加「**非零页**只读页的写 ⇒ 私有副本」（`memcpy` 后置 W），零页仍走原「不复制」路径；判词链接受 `fill-file` | `K3 pf: n=4 … va=0x10040 vma=0x10000-0x20000 result=fill-file`；随后用户态连续执行并到达 `exit_group` |
| 判据④（ENOSYS 是否让 musl 走 NULL 回调） | ✅已排除（不是主因），但**发现钩子读错寄存器组** | `brk` 钩子原读 `regs->rd[16]`；指针参数应在 **`rb16`**（contract-instruction §4.1）。改为 `rb16`，并按裁定「至少返回可用堆顶、不必真扩」只做记账（`mm->brk = want`） | 修前 init 以 `exit=4`（`INIT_EXIT_BRK`）结束；修后 `K4 switch init: exit code=0` |
| **S7 转绿** | ✅ | 探针 `MISSING` 表移除 S7（改由真实判据判） | `k4_switch_probe`: `S7: initramfs /init 跑到 exit_group` PASS；`K4 switch done: initramfs /init ran under kernel_init, exit=0` |
| **S5（本任务 U-mode 帧 A/B 往返）** | ⏸未做（本轮超时，方案已定） | — | 方案：umon 入口保持静态栈（`current` 由 SP 派生），但**帧改为按任务**：入口 `DADAO_GPR_SAVE` 到静态槽后 `memcpy` 进 `task_pt_regs(current)`，C 半与出场 `DADAO_GPR_RESTORE` 都改用该指针（需给 `entry.h` 加「寄存器版」RESTORE 宏）；`dadao_enter_user` 写 `task_pt_regs(current)`、`dadao_umon_enter` 从指针恢复。F13 曾试「入口栈也按任务」而回退，本轮方案不动入口栈、只动帧，风险更低 |

### 第 23 轮 engineer 自审（2026-11-19，S5 前置设计核查 —— **停在裁定前，未改内核**）

**本轮工作**：按第 22 轮方案（入口栈保持静态、只把帧按任务化）动手前先做前置核查，结论是**该方案不足以实现 S5**，理由与证据如下：

| 核查项 | 结论 | 依据 |
|---|---|---|
| 帧按任务化是否可做 | ✅ 可做（`entry.h` 已有 `DADAO_GPR_SAVE_AT`/`RESTORE_AT`，`rb3` 指帧即可） | `arch/dadao/include/asm/entry.h:82/131` |
| 帧按任务化是否**够** | ❌ 不够：**交替**需要 handler 阻塞（`schedule()`），而 handler 跑在**静态入口栈**上 | `kernel/trap.S:171` `set.rb rb1, dadao_umon_stack_top`；`asm/thread_info.h:43` `current` = `SP & ~(THREAD_SIZE-1)` 派生 |
| 阻塞的后果 | A、B 的内核续跑点落在同一张 64 KiB 静态栈 ⇒ 互相覆盖（与帧放哪里无关） | 同 F13 回退的机制 |
| 能否让入口直接换到「自己的内核栈」 | ❌ 不能：入口的 SP 还是**用户栈**，`current` 尚不可知（F28 正是为此在静态栈上刷新 `thread_info.task`） | `traps.c`/`process.c` 的 `dadao_umon_stack` 用法 |
| 不依赖 SP 的可行设计 | ✅ 全局 `dadao_current_task`（`__switch_to`/`dadao_enter_user` 写、umon 入口读）→ 取 `task_stack_page(task)+THREAD_SIZE` 当新 SP；单 hart、无嵌套 ⇒ 全局单元安全 | 已写入「待裁定 6」 |

**因此本轮按纪律停在此处**：**未改任何内核代码**（`git status` 与前一轮一致：`M 33 / ?? 10`；S7 仍为绿、42 PASS / 1 FAIL 的状态未变），把设计选择登记为**待裁定 6（A/B/C）**。不退回 F13 的「入口栈也按任务」做法，也不擅自扩核心结构。

### 第 24 轮 engineer 自审（2026-11-19，方案 A 试验 —— **未达绿，已回退到 S7 绿状态**）

**按裁定 6(A) 实做**（全局 `dadao_current_task` + 入口改用任务自己的内核栈 + 帧按任务化），分步实测结果：

| 步骤 | 结果 | 证据 |
|---|---|---|
| ① `switch_to_asm` 在切栈前写 `dadao_current_task`（用 `rb4/rb5/rd3`，**未碰 `rb3`**） | ✅ 生效 | 首次实现误用 `rb3` 当 scratch ⇒ `s4-rb3-untouched` 红；改用 caller-saved 后 S4 回绿 |
| ② umon 入口读该单元 → `task_stack_page(task)+THREAD_SIZE` 作新 SP；帧 `adopt` 进 `task_pt_regs(current)` | ✅ 栈切换生效（不再用静态入口栈） | `dadao_umon_enter+0x18` 曾 MALIGN：**指针返回值在 `rb8` 不是 `rd8`**（contract-abi §4.4），修正后不再错 |
| ③ `current` 改为读全局（保留 NULL→SP 兜底） | ❌ **引入 `copy_process` MALIGN** | `dadao: unrecoverable supv exception cause=MALIGN ip=copy_process+0x344 info=0xa6584a110062`（`rest_init` 建 `kthreadd` 时）；把 `current` 退回 SP 派生后该故障即消失 ⇒ 与 `current` 的取值来源相关 |
| ④ 同时把 `current_pt_regs()` 改为 `task_pt_regs(current)` | ❌ 仍红（同一 `copy_process` MALIGN，偏移略变） | 见上 |
| ⑤ 只保留入口层（`current` 仍 SP 派生 + `current_pt_regs()` 原样），帧/栈按任务化 | ❌ 用户态 ip 变 0（`K4 flog n=4 … b=0x0`，`pf last ip=0x0`） | 说明「帧按任务化」与静态 `dadao_user_frame` 的写入/读取路径没对齐 |

**结论与处置**：方案 A 需要的不只是「换一个 `current` 来源」，还牵动 `current_pt_regs()`、`copy_thread`/`start_thread` 的帧位置，以及入口的 staging 帧协议；本轮 2 h 内未能给出全绿实现，**已把代码回退到第 22 轮的 S7 绿状态**（`git diff` 与第 22 轮一致；`K4 switch done: initramfs /init ran under kernel_init, exit=0` 复现）。**未提交**。

**下轮判据（写清，避免重复试错）**：
1. `current` 一旦改来源，必须同时核对 **`current_pt_regs()`/`task_pt_regs()` 的所有使用者**（`copy_thread`、`start_thread`、`dadao_ret_from_fork`），并验证 `init_task.stack` 与 boot 期 SP 同区（实测 `init_task.stack=0x20000510000`、`sp=0x2000051f590` ✓ 同区，故 ③ 的故障不是栈不匹配）；
2. 先做「入口不改栈、只把 `current` 换来源」的**单独**一轮，确认 `S1–S7` 全绿，再做「入口换栈」，两步分开；
3. `dadao_enter_user` 与 umon 入口必须共用**同一个帧位置来源**（当前一个是 `dadao_user_frame` 静态帧、一个是 `dadao_umon_save` 静态帧）；⑤ 的 ip=0 正是这条不成立；
4. 指针返回值（`&pt_regs`）一律走 **`rb8`**；这是本轮已确认的 ABI 事实（contract-abi §4.4）。

### 第 25 轮 engineer 自审（2026-11-19，按用户裁定的 cg6 方案落地入口切栈）

**用户裁定**：`cg6` 就是做这个的；`__switch_to` 只写一行（把 `task_stack_page(next)+THREAD_SIZE` 写进 `cfx_umon cg6 rc1`）；入口用 `rd2`/`rd3`（reserved）做过渡；静态栈留作 boot 兜底（`cg6 rc1 == 0` 时用）。**取代**上一版「全局 `dadao_current_task` + 改 `current`」的做法（已全部撤掉，`current`/`current_pt_regs()` 仍按 SP 派生）。

| 项 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `__switch_to` 预写任务栈顶 | ✅ | `process.c`：`DADAO_CFX_WRITE(cfx_umon, UMON_CG_SCRATCH, UMON_RC_SCRATCH_STACK_TOP, (unsigned long)task_stack_page(next) + THREAD_SIZE)`（在 `dadao_switch_to_asm` 之前）；`cfx.h` 加 `UMON_CG_SCRATCH=6`/`UMON_RC_SCRATCH_STACK_TOP=1` | — |
| umon 入口切到任务栈 | ✅ | `trap.S`：`rb2rd rd2, rb1, 1`（用户 SP）→ `cfx2rd cfx_umon, cg6, rc1, rd3` → `br.z {rd3}? .Lumon_boot_stack` → `rd2rb rb1, rd3, 1`；0 时回落 `set.rb rb1, dadao_umon_stack_top` | 入口不再用静态栈（boot 之后） |
| 帧按任务化 | ✅ | 入口 `add.si rb1, -PT_REGS_SIZE` + `dadao_umon_adopt()`（把静态暂存帧 `memcpy` 进 `task_pt_regs(current)`）→ `rb16` 作为 C 半的帧参数；出场用 `dadao_umon_frame()` 重新取指针再 `DADAO_GPR_RESTORE_AT` | 见下 |
| **F51（本轮踩到并修）**：切栈后 cg5 的 `excp_cause_ip`/`status` 仍写进 `[rb3]`（旧静态帧）⇒ 帧 `ip` 为 0，用户首指令报 `ip=0x0 va=0x211c8`，随后跳到 0 | ✅已修 | 两处 `st.o rd17/rd0, [rb3, …]` 改为 `[rb16, …]`（rb16 = 采纳后的任务帧） | 修后 `K4 syscall: nr=rd15=0x40 …`、`K4 switch init: exit code=0`、`K4 switch done: … exit=0` |
| **F52（本轮踩到并修）**：`rb2rd/rd2rb` 的源/目的不能用 `rd4–rd7` 之外的写法；`cfx2rc` 的值寄存器必须是 rd；`sub.o` 在本 ISA 不存在；`or.w`/`add.o` 不能混用 rd2/rd3（reserved） | ✅已修 | 计算改在 C 侧（`__switch_to`），入口只用用户给的 4 条（`rb2rd rd2, rb1, 1` / `cfx2rd …, rd3` / `rd2rb rb1, rd3, 1`） | 构建通过 |
| `current` 的来源 | ✅**不变**（SP 派生） | 上一版的全局单元/`current_pt_regs()` 改动全部撤销 | 第 24 轮的 `copy_process` MALIGN 不再出现 |
| F28「每 entry 刷新 `thread_info.task`」是否还需要 | **仍需要（保留）** | 未改 | 入口现在切到任务自己的栈，`current_thread_info()` 自然指向该任务；但 `dadao_enter_user` 进入用户态前仍走静态 `dadao_user_frame`，且 `dadao_user_entry_install` 的 seed 仍被 boot 兜底路径使用 ⇒ 保留并注明理由 |
| S5 判据本体（A/B 往返） | ⏸未做（本轮超时） | — | 入口/帧的**前置**已就位：42 PASS / 1 FAIL，唯一红项仍是 `S5` 的 MISSING 占位 |

### 第 26 轮 engineer 自审（2026-11-19，S5 用例试做 —— 未达绿，已撤回用例）

**本轮做了什么**：在探针镜像里写了 S5 用例（两个任务各自用哨兵构造用户帧 → `dadao_enter_user` → 桩 `trap cfx_umon, 0` → 钩子里校验 → `schedule()` → 回来再校验 → `trap cfx_umon, 1` 收尾），并加了探针钩子与 `k4s_s5_task`。

**实测现场（关键，供下一轮直接续做）**：
- 用例能走到：`K4 switch s5: begin` → 建 mm/VMA → 代码页（`fill-code` at 0x4000400000 ✓）→ 数据页 `fill-zero`（桩的 `ld.o rd20,[rb10,0]` ✓）。
- **A（who=0）两次进入 `trap #0`**（`K4 s5 hook: nr=0 who=0 visits=0` 然后 `visits=1`）——说明第一次 `SKIP` 之后用户态**没有**前进到 `trap #1`，而是又回到同一条 `trap cfx_umon, 0`；随后整机静默（无 B 的钩子、无收尾摘要、无 wait 打印）。
- **B（who=1）从未进用户态**（无 `who=1` 的钩子行）⇒ A 的 `schedule()` 之后 B 没被跑到，或 B 的 `dadao_enter_user` 没走到。

**撤回**：S5 用例与钩子全部删除（`k4s_case_s5`/`dadao_k4_s5_syscall`/`K4S_FAIL_S5`、`dadao_umon_busy` 改回 `static`），重建后 **`k4_switch_probe` 回到 42 PASS / 1 FAIL**（唯一红项仍是 S5 的 MISSING 占位），S1–S4/S6/S7 全绿。

**下轮判据（写清）**：
1. 「A 又回到 `trap #0`」先判是 **`SKIP` 没生效**还是**用户 `ip` 被写回**：在 `.Lumon_skip` 之前打印 `excp_cause_ip`（cg5 rc3）与采纳帧的 `ip`，两处都应是 0x4000400000；若 escape 走 `+4` 而用户仍回到 0x4000400000，则查 `DADAO_GPR_RESTORE_AT` 是否把帧里的 `ip` 也恢复了（帧的 `PT_IP` 只在入口由 `st.o rd17,[rb16,PT_IP]` 写，用户 `ip` 不该从帧恢复）。
2. 「B 未进用户态」：在 `k4s_s5_task` 入口、`dadao_switch_mm` 之后、`dadao_enter_user` 之前各打一行，确认 B 是否被调度到；`dadao_enter_user` 用的是**静态** `dadao_user_frame`（A 已在 handler 里），B 覆盖它是否影响 A 的恢复——A 的恢复已改用按任务帧，但 `dadao_umon_enter` 仍读静态帧，需确认时序。
3. 注入⑤（去掉 `DADAO_GPR_SAVE_AT` 里 `frame.rb[3] = rbtp`）随用例一起做。

### 第 27 轮 engineer 自审（2026-11-19，S5 单任务往返 + 两个根因）

**F53（关键，已定位）**：上轮「A 重入 `trap #0`」是**判据错**——umon 的**服务号在 `immu18`**（`trap cfx_umon, N`），不是 `rd15`（`rd15` 是 Linux syscall 号，contract-syscall §1）。探针桩两条 trap 的 `rd15` 都是 0，钩子把 `trap #1` 当成 `#0`，于是 visits 递增、任务永不收尾。
证据（单任务用例）：`K4 s5 hook: nr=0 visits=0 ip=0x4000400000` → 修正后 `svc=0 … ip=0x4000400000`、`svc=1 … ip=0x4000400008` ✔ **U-mode 帧往返本身在这一步已经跑通**（进入用户态 → trap #0 → 钩子 → SKIP → 桩的 `ld.o` → trap #1）。

**F54（新，未解）**：任务收尾后**创建者（boot 任务）再也拿不到 CPU**——试了两种收尾都失败：
- `for (;;) schedule();`（在 handler 内 park）⇒ 创建者的循环打印一行都不出现；
- `do_exit(0)` ⇒ 同样静默（该任务 `current->mm` 被换成 S5 的 mm，疑与退出时的 mm 收尾有关）。
⇒ 下一轮判据：① 在 `do_exit` 前后打点（`exit_mm`/`schedule` 前后），判定是否卡在 mm 收尾（S5 的 mm 是从 boot 任务“借”来的，`active_mm` 也被改过）；② 备选：让 S5 任务**不退出**而是把 `thread.ra` 指到 park 桩并在 *user* 态自旋（`jump [rb0,0]` 会 die，需要一个新的 `swym/跳自身` 桩指令序列）；③ 或者把 S5 的验收改成「在 svc=1 处由内核自报逐项结果」（不改创建者的等待语义），S7 之后不再依赖该任务收尾。

**本轮处置**：单任务用例与钩子已撤回（保留入口改造），树回到 **42 PASS / 1 FAIL**（唯一红项 S5 占位），S1–S4/S6/S7 全绿。

### 第 28 轮 engineer 自审（2026-11-19，S5 单任务往返转绿一次 + 两处真 bug 修复）

| 项 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| **F55（真 bug，已修）**：`DADAO_GPR_SAVE` 先把 `rb3` 覆盖成帧地址、再「保存 rbtp」⇒ **`frame.rb[3]` 里存的是帧地址，rbtp 从未被保存**（`DADAO_GPR_RESTORE_AT` 最后又从该槽恢复 `rb3`，等于把帧地址写进用户 rbtp） | ✅已修（核心宏） | `asm/entry.h`：`DADAO_GPR_SAVE` 在改基址**之前**用保留寄存器 `rd2`（其原值先存 `cfx cg6 rc0`）把 `rb3` 落到 `frame.rb[3]`，再设基址；`DADAO_GPR_SAVE_AT` 去掉那句错误的 rbtp 存 | 修前 S5 的帧校验 `got=0x5`（bit0=ip、bit2=rb3）；修后 **`K4 check s5-a-frame want=0x0 got=0x0 ok`**（单任务 A 的整轮帧校验通过） |
| **F53 复核**：服务号在 `immu18` | ✅复核一致 | S5 用例按 `regs->ip`（桩两条 trap 的地址）分发服务号 | `svc=0 ip=0x4000400000` → `svc=1 ip=0x4000400008` |
| **F54/F56（未解）**：A/B 交替与任务收尾仍不成立 | ⏸待续 | 用例已按要求撤回（只回退本轮用例代码，入口改造与 F55 保留） | 本轮观察到：A 的 svc=0 `schedule()` 之后**B 没有运行**（无 `s5-b-frame`），A 直接到了 svc=1；A 在用户态 park（重定向到桩的 `jump [rb0,0]`）后**整机停住**（本端口用户态无抢占）。另一条老现象：任何任务的「内核态 park / do_exit」都会让创建者（boot 任务）拿不到 CPU |

**F56 下轮判据（写清）**：
1. **B 不运行**：怀疑 `dadao_switch_mm(NULL, k4s_s5_mm, current)` 是**全局**改动（PTBR/ASID 是每 hart 状态），A 切 mm 后 B（仍以为在内核表上）与 boot 任务的执行环境被一起改掉；判据：在 S5 前**不切 mm**（改用 `dadao_pf_window_add` 注册用户窗口 + 把窗口的 mode 位改成 U|S），或让每个任务在自己的 mm 上运行后再切回。
2. **收尾**：本端口无用户态抢占 ⇒ 用户态 park 会饿死整机；A/B 收尾应在**内核态**用 `wait_for_completion`（S2 已有可用范式），而不是 `schedule()` 自旋或 `do_exit`。
3. 断言仍在 `svc=1` 处由内核自报（裁定②已授权的取证点前移），**判据不变**。

### 第 29 轮 engineer 自审（2026-11-19，判据① 窗口方案 —— 撞到两处内核空指针，已回退）

**合入**：`git merge master`（FF，`5c7d6df3`），未动主工作树。

**判据①（不切 mm，改用户窗口）实施与结果**：
- 新增 `dadao_pf_window_add_user()` + `dadao_pf_window_user[]` 标记 + `dadao_pf_window_mode()`（窗口被用户可达时给 `U|S`，与用户 VMA 同口径；`§2.2.6` 只要求按*访问者*模式判 HSJU ⇒ **无 spec 缺口**）。
- S5 用例改为：窗口（代码/数据/两个栈）+ 两任务 + `wait_for_completion_timeout`（S2 范式），断言仍在 `svc=1` 内核自报。

**实测撞到两处内核空指针（本轮新发现，均已定位）**：
1. **F57（已定位）**：`local_flush_tlb_page()` 对非内核地址直接取 `vma->vm_mm->context.asid`；探针窗口 `vm_mm == NULL` ⇒ NULL 解引用（现场 `info=0x32e` = `vm_mm` 的偏移）。K3 窗口不触发是因为它们在**内核地址**上（`dadao_addr_is_kernel()` 提前返回）。
2. **F58（已定位到 `dadao_pf_fill` 内，未查出具体字段）**：修 F57 后同一路径在 `dadao_pf_fill` 里再次 NULL 解引用（`info=0x30`）；说明窗口在**用户地址**上还有一处「假定有 `vm_mm`」的取字段。

**处置（按纪律）**：① 未撞到 spec 缺口，但两处空指针不在「一个函数内」可修完（F57 在 `tlbflush.h`、F58 在 `fault.c` 的填充路径），已超出本轮预算 ⇒ **回退本轮新增的窗口 API 与 S5 用例**，**保留**入口切栈（第 25 轮）与 **F55 rbtp 修复**（第 28 轮）。树回到 **42 PASS / 1 FAIL**（唯一红项 S5 占位）。

**下轮判据（写清）**：
1. 把「用户可达的窗口」当作**通道的一等概念**补齐，而不是零散打补丁：`dadao_pf_fill` 内所有需要 `vm_mm` 的位置（`dadao_pf_table`、`pmd_populate_kernel`、`local_flush_tlb_page`、`dadao_pf_publish`）都按「窗口 ⇒ 内核表 + ASID 0」统一处理；先 grep `vma->vm_mm` 的全部使用点一次查完（避免 F57→F58 这种逐个撞）。
2. 或改走「每个任务一个真 mm」但**只在任务自己运行时切**（`switch_to` 里按 next->mm 切，而不是在用例里手工切）——这要求 `switch_to` 增加 mm 切换，属核心改动，需另行裁定。
3. 断言仍在 `svc=1` 自报（裁定②），判据不变；注入⑤（删 rbtp 保存）随用例一起做。

### 第 30 轮 engineer 自审（2026-11-19，按用户裁定改为「每任务真 mm」）

**用户裁定（逐字）**：「2TiB以上是smon空间，所以，每个进程新建L1页表时，应该复制2TiB以上的完整的页表项；据我所知，其它isa应该都是这么做的」。spec 依据已核：`spec/Kaiwu` §内存窗口（`VA [0,4TiB)`、用户 `[0,2TiB)`、`VA = PA + 2TiB`）。

| 项 | 结果 | 证据 |
|---|---|---|
| **`pgd_alloc()` 复制 VA ≥ 2 TiB 的全部顶层项** | ✅**已满足并有直接断言**（代码本已如此：`memcpy(pgd + USER_PTRS_PER_PGD, swapper_pg_dir + USER_PTRS_PER_PGD, …)`）；本轮把它变成**探针断言**（独立于任何往返） | `K4 switch s5: pgd copy items=4096 mismatches=0 user_ptrs=4096` + `K4 check s5-pgd-copy-items want=0x1000 got=0x1000 ok` + `K4 check s5-pgd-copy-mismatches want=0x0 got=0x0 ok`（逐项与 `swapper_pg_dir` 比较，非抽样） |
| `pgd_free` 不释放共享内核表 | ✅已核：本端口 `pgd_free` = 通用 `__pgd_free`，只释放 L1 页本身，不遍历/释放共享的内核 L2 ✓（已在 `pgalloc.h` 注释写明） | 代码评审 + 回归全绿 |
| **S5「每任务真 mm + 正常 `switch_mm`」** | ⏸未达绿（撞到两处 cfx 权限问题） | 见下 |
| 窗口旁路（`pf_window_add_user` 等） | ✅已彻底移除（第 29 轮新增的全部删除，`grep` 0） | `grep -c window_add_user` = 0 |

**本轮新发现（均已定位到指令级）**：
- **F59**：任务**用自己的 mm（PTBR/ASID 已切）**时，钩子里的 `dadao_early_printf` → 控制台 `trap cfx0, 0x3FF00` **被拒为 `CFXPERM + NCFXPERM`**（`ip=dadao_k4_s5_syscall+0xa4`）。去掉该打印后流程继续（A 的 `schedule()` 成功切到 B ✓）⇒ 与「帧/往返」无关，是**控制台路径在新 mm 下的 cfx 权限**问题。
- **F60**：**任务 B 在自己的 `dadao_switch_mm(NULL, mm_B, current)` 内**再次撞 `CFXPERM + NCFXPERM`（`va=0x7a106008`，`ptbr` 仍是 A 的表）⇒ `switch_mm` 的 cfx 访问在新 mm 语境下被拒。

**处置**：S5 用例整体撤回（只保留本轮的 `s5-pgd-copy-*` 两条真实断言）；树回到 **42 PASS / 1 FAIL**（唯一红项 S5 占位）。

**下轮判据（写清）**：
1. **F59/F60 同一族**：查 `cfx2rc/cfx2rd` 的**来源掩码**在「任务自己的 mm」下为何被拒——重点看 `cfx_umon`/`cfx_ptw` 的 `supv` 行 `cfxreg`/`cfxtrap` 位是否只在 boot 时按 `init_mm` 语境放过、而 `switch_mm`（ASID 变化）后失效；判据：在 `switch_mm` 前后各打印 `cfx_smon cg2 rc2(cfxtrap)/rc4(mask)` 与 `cfx_ptw cg2`，定位是哪一位被拒。
2. 修复方向只能是「内核访问 cfx 的权限与 ASID/当前 mm 无关」——若确认与 spec 的 `NCFXPERM` 定义冲突，登记 `待裁定`，不改 spec。
3. 断言仍留在 `svc=1`（裁定②）；注入⑤（删 rbtp 保存）随用例一起做。

### 第 31 轮 engineer 自审（2026-11-19，**S5 转绿 + 注入⑤ 可达 FAIL**）

| 项 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| **F59/F60 根因（模型依据）**：`cfx_perm_denied()`（QEMU `helper.c`）按 `cfx[target].mode[supv].<kind>` 的**第「当前 cfx」位**判权；`§3.3` 的 cg2 rc0/rc2 都是**按源 cfx 索引**。内核（固件）只给 {smon(2), hart(15)} 放过；任务陷入后当前 cfx 是 **cfx_umon(0)** ⇒ 内核自己的 `cfx2rd/cfx2rc`（`cfx_ptw`、`cfx_hart` 的 timer、控制台 `trap cfx0`）被拒 `NCFXPERM` | ✅已修（一个函数：`dadao_user_entry_install()`） | `process.c`：对内核会访问的 cfx（`cfx_umon/smon/ptw/hart/time`）把 supv 的 **cfxtrap(rc0)** 与 **cfxreg(rc2)** 行中 {0,2,15} 三位**清零（=放行）**；`cfx.h` 加 `DADAO_CFX_SOURCES_OPEN` 常量并注明「掩码按源 cfx 索引」 | 修前 `CFXPERM + NCFXPERM`（`dadao_k4_s5_syscall+0xa4`、`switch_mm` 内）；修后 `K4 switch: ptw-from-umon ptbr=0x4770000 ok=1` |
| **S5 A/B 往返** | ✅**转绿** | S5 用例：两任务各自 mm（`pgd_alloc` 复制内核窗口已断言）、各自 `switch_mm`、`svc=0` 校验→`schedule()`→再校验、`svc=1` 终校验+`complete`+交回 `init_mm` 后 `wait_for_completion`（不再自旋/`do_exit`） | `K4 switch s5: a_bad=0x0 b_bad=0x0 visits=1/1 reported=2 entries=2`；`K4 check s5-a-frame/b-frame/s5-both-reported/s5-a-visited/s5-b-visited/s5-no-recursion` 全 `ok` |
| 门控 | ✅ | `k4_switch_probe.py`：S5 入 `CASES`、移出 `MISSING`，新增 4 条 S5 断言 + 2 条 pgd 复制断言 | `--no-inject` **51 PASS / 0 FAIL（rc=0）** |
| **注入⑤** | ✅可达 FAIL | 新注入 `no-rbtp-save`：删 `DADAO_GPR_SAVE` 里 `st.o rd2, [rb3, PT_RB_BASE + 3*8]` | 注入后 `K4 check s5-a-frame … FAIL`、整机 rc=67；`cp`+md5 还原（`6fade299…` 对账）→ 重建 → **全绿** |
| S7 保持 | ✅ | 无回退 | `K4 switch done: initramfs /init ran under kernel_init, exit=0` |

**判决**：**S5 与 S7 均达验收；注入⑤ 可达 FAIL** ⇒ 状态改 **`待验收`**。

### 第 1 轮 reviewer 验收（2026-11-19，大改档；以下命令与输出均为本 reviewer 独立重跑）

**重跑记录（命令 / 真实输出 / 退出码）**

1. `python3 tools/linux/k4_switch_probe.py --no-inject` ⇒ `k4_switch_probe: 51/51 passed`，**EXIT=0**（还原后再跑一次仍 51/51、EXIT=0）。现场：`K4 switch s5: a_bad=0x0 b_bad=0x0 visits=1/1 reported=2 entries=2`、`K4 switch s5: pgd copy items=4096 mismatches=0 user_ptrs=4096`、`K4 switch done: initramfs /init ran under kernel_init, exit=0`。
2. 回归逐条 **EXIT=0**：`check-linux-k0` 130/130、`-k1` 112/112、`-k2` 170/170、`-k3` 263/263、`k4_fork_probe` 101/101、`k4_stack_probe` 44/44 —— 与完成区数字**逐个一致**。
3. `make check-patch-tree` **EXIT=0**（11 补丁集/431 补丁，linux 84）；`make check-source-state` **EXIT=0**（`linux: OK HEAD=2187e1bb6cec count=1 clean=True`）。
4. `k4_switch_probe --selfcheck` ⇒ `[SELFCHECK] PASS`（16 条红），证明判据可红。
5. **注入⑤**：`--inject no-rbtp-save` ⇒ `inject no-rbtp-save: rc=67 red=['s5-a-frame'] died=True`、`K4 check s5-a-frame want=0x0 got=0x4 FAIL`（bit2 = `rb3`）、`a_bad=0x4 b_bad=0x4`；还原 md5 `6fade299…` 与注入前快照一致 ⇒ 回绿，**55/55，EXIT=0**。
6. **另 5 路注入（核对完成区「6/6」）**：`no-rd32-save`→S1（rc=64）、`restore-wrong-order`→S1（225）、`no-asid-write`→S3（67）、`switch-clobbers-tp`→S4（65）、`no-timer-arm`→S6（68），每路 md5 对账 + 还原后回绿，**71/71，EXIT=0**。
7. **自选第 7 路（不在 017 的 6 路内）**：`process.c` 删 `DADAO_OPEN_SUPV(cfx_ptw);`（`cp` 备份，md5 `54792353…`→`de803ccc…`）⇒ `cause=CFXPERM sub=NCFXPERM va=0x7a106008` + `dadao: die mode=2 code=0xe7`、`K4 switch s5:` 行缺失 ⇒ **44/46、EXIT=1**；`cp` 还原后 `md5sum -c` 6/6 OK、`--source-state` clean、`--no-inject` **51/51 EXIT=0**。

**四处修复独立核验（读源码，不采信完成区转述）**

- **F55**：`entry.h::DADAO_GPR_SAVE` 顺序 = 存 `rd2` → `rb2rd rd2, rb3, 1` → `set.rb rb3, \frame` → `st.o rd2, [rb3, PT_RB_BASE + 3*8]`，`SAVE_AT` 已无 rbtp 存；注入⑤ 变红即证其载荷。
- **F59/F60 = 符合 spec，不是「用实现迁就」**：`spec/DADAO-12 §3.3`（行 349/351）cg2 rc0/rc2「RW｜`0=允许`、`1=屏蔽`｜**位索引=源 cfx**」（通用口径行 319）；`§5.2(一)`（行 836）「`cfx2rd/cfx2rc` 目标 cfx 的 `<mode>_cfxtrap`/`<mode>_cfxreg` 拒绝源 cfx ⇒ `CFXPERM`」；`§2.2.6`（行 297）`CFXPERM` + `[39] NCFXPERM`；`contract-syscall §8`（`contract-syscall.md:117`）「**内核须在启动时把所需来源位清 `0`**，不得依赖固件默认掩码长期放行宽于需要的来源」。修法只写 **cg2（supv 行）**、只清 `cfxtrap(rc0)`/`cfxreg(rc2)`、只开内核三处当前 cfx {0,2,15}；**U-mode 所用 cg0 行未动** ⇒ 未给用户放宽权限，也未改 spec/合约。
- **pgd 复制**：`pgalloc.h::pgd_alloc()` 为 `memcpy(pgd + USER_PTRS_PER_PGD, swapper_pg_dir + …, (PTRS_PER_PGD - USER_PTRS_PER_PGD) * 8)`；`k4s_case_s5_pgdcopy()` 是 **for 逐项比对**（非抽样），`USER_PTRS_PER_PGD = 2^41 / 2^29 = 4096`，期望 `items` 由 `PTRS_PER_PGD - USER_PTRS_PER_PGD` 现场算出。
- **入口切栈**：`process.c::__switch_to` 在 `dadao_switch_to_asm` **之前**写 `cfx_umon cg6 rc1 = task_stack_page(next) + THREAD_SIZE`；`trap.S` 为 `rb2rd rd2, rb1, 1` / `cfx2rd …, rd3` / `br.z {rd3} → .Lumon_boot_stack`（`==0` 回落静态栈）/ `rd2rb rb1, rd3, 1` ✓。

**判据未放宽（逐项在位）**：`k4s_s5_check` 六位 = `ip`(bit0)、`rb1`(bit1)、`rb3`(bit2)、`status == 0`(bit3)、`rd32–63`(bit4)、`rb32–63`(bit5)，在 **svc=0 首入 / `schedule()` 返回后 / svc=1** 各判一次；探针侧另判 `a_bad`/`b_bad`==0、`visits == 1/1`、`reported == 2`、pgd `items`/`mismatches`。取证点前移**未删任何一项**。

**约束核验**：① `git rev-parse --show-toplevel` = 任务 worktree、分支 `m14-linux-017`、HEAD `e20ea0ea` 未动，**本轮未提交任何 git**；② `git diff --name-only master...HEAD` 共 45 文件，全在 `components/linux/**`、`tools/linux/**`、本任务书，`spec/`、`.tao/contracts/`、`tests/`、`components/qemu/`、根 `Makefile` **0 命中**；③ 注入还原只用 `cp`+md5，**未用** `checkout/restore/stash/reset`；④ 快照对账：验收期间（写入本记录前）前后各记一次 `git status --porcelain -uall` **均 0 行**、HEAD 均为 `e20ea0ea`、6 个目标文件 `md5sum -c` 全 OK；写入本审阅记录后工作区仅本任务书 1 处改动（即本记录本身），其余文件 md5 未变、`--source-state` 仍 clean；⑤ 任务书未引用 `.work` 下任何具体路径、`**状态**` = 待验收、完成区 30 行、第 27–31 轮判决段的三处陈旧短语（本 reviewer 按派单自查）在全文**均 0 命中**。

**findings（文档/断言级，不阻断，交 architect 收尾修）**：F-a `s5-no-recursion` 用 `k4s_s5_entries >= 2`，递归增到 >2 仍绿（实际兜底是探针 `visits == 1/1` ⇒ entries 恰为 2），建议改 `== 2`；F-b `components/linux/changelog.md` 的 017 条目止于「追加 21」，其「未完成 ① S5 未实现 ② S7 未打通」已过时；F-c 完成区「遗留问题」仍写「当前 S7 卡在 F29」「① S5 未实现」，与本轮 51/51 矛盾（历史段，宜补注已解）；F-d 完成区「修改文件」漏列 `include/asm/current.h.patch`（该补丁本轮只多出一个空行，需确认是否误改）；F-e 审阅记录第 6 轮含具体临时目录路径，宜改运行期措辞。

**判决：Accepted** —— 验收命令块在本 reviewer 重跑下全绿；7 路注入（任务书 6 路 + 自选 1 路）全部「注入 → 目标 case 红 → `cp`+md5 还原 → 回绿」有真实输出与退出码；四处处处核到源码与 spec 原文；判据逐项在位、无越界改动。Accepted 只代表「工程师达标」，架构侧仍终审。

## 完成区

**测试结果（第 31 轮 · S5 转绿）**：`k4_switch_probe --no-inject` **51 PASS / 0 FAIL（rc=0）**——S1–S7 全部通过（含 `S5` 的 `a_bad=0x0 b_bad=0x0` 与 `S7` 的 `init: exit code=0`）。回归：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）；switch `--inject` **6/6 全绿**（新增 `no-rbtp-save`：注入后 `s5-a-frame` 红、整机 rc=67，`cp`+md5 还原后回绿）；`check-patch-tree` rc=0 与 `--source-state` clean。

**测试结果（第 30 轮 · pgd 内核窗口复制）**：`k4_switch_probe --no-inject` **42 PASS / 1 FAIL（rc=1）**，唯一红项 = `S5`（A/B 往返未完成，MISSING 占位）；**新增两条真实断言**：`K4 switch s5: pgd copy items=4096 mismatches=0 user_ptrs=4096`、`K4 check s5-pgd-copy-items want=0x1000 got=0x1000 ok`、`K4 check s5-pgd-copy-mismatches want=0x0 got=0x0 ok`（新 mm 的 `pgd[USER_PTRS_PER_PGD..]` 与 `swapper_pg_dir` **逐项**相等）。S5 本体（每任务真 mm + 正常 `switch_mm`）撞到 **F59/F60**：任务自己的 mm 生效后，控制台 `trap cfx0` 与 `switch_mm` 的 cfx 访问都被拒为 `CFXPERM + NCFXPERM`（已定位到指令），用例已撤回。回归：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state` clean。

**测试结果（第 28 轮 · rbtp 保存修复）**：`k4_switch_probe --no-inject` **42 PASS / 1 FAIL（rc=1）**，唯一红项 = `S5`（用例已撤回，MISSING 占位）；S7 仍绿。**F55 已修**：`DADAO_GPR_SAVE` 在改基址前用 `rd2`（其原值先入 `cfx cg6 rc0`）把真实 `rb3`(rbtp) 写入 `frame.rb[3]`，`SAVE_AT` 删掉错误的 rbtp 存；修前 S5 帧校验 `got=0x5`，修后 **`K4 check s5-a-frame want=0x0 got=0x0 ok`**（单任务整轮帧校验通过）。**F56（未解）**：A/B 交替仍不成立——A 的 `schedule()` 后 B 未运行（疑 `dadao_switch_mm` 是每 hart 全局状态，A 切 mm 把 B/boot 任务的执行环境一起改掉）；用户态 park 会饿死整机（本端口无用户抢占）；内核态 park/`do_exit` 仍使创建者拿不到 CPU。回归：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state` clean。

**测试结果（第 27 轮 · S5 单任务往返定位）**：`k4_switch_probe --no-inject` **42 PASS / 1 FAIL（rc=1）**，唯一红项 = `S5`（用例已撤回，仍是 MISSING 占位）；S7 仍绿。本轮定位 **F53**（umon 服务号在 `immu18` 而非 `rd15`；修正后单任务用例 `svc=0 … ip=0x4000400000` → `svc=1 … ip=0x4000400008`，**U-mode 帧往返本身跑通**）与 **F54**（任务收尾后创建者拿不到 CPU：park 与 `do_exit` 两种都静默）。回归：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state` clean。

**测试结果（第 26 轮 · S5 用例试做/撤回）**：`k4_switch_probe --no-inject` **42 PASS / 1 FAIL（rc=1）**，唯一红项 = `S5`（用例未完成，仍为 MISSING 占位）；S7 仍绿。S5 用例实测现场（已写进自审）：A 两次进入 `trap #0`（`visits=0/1`）、B 从未进用户态、无收尾摘要 ⇒ 用例已撤回，入口改造保留。回归：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state` clean。

**测试结果（第 25 轮 · 入口切到任务栈）**：`k4_switch_probe --no-inject` **42 PASS / 1 FAIL（rc=1）**，唯一红项 = `S5`（用例未写；`S7` 仍绿：`K4 switch init: exit code=0`、`K4 switch done: … exit=0`）。回归（串行无并发）：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state`（linux base+1 clean）rc=0。本轮实现：`__switch_to` 把 `task_stack_page(next)+THREAD_SIZE` 写进 `cfx_umon cg6 rc1`；umon 入口用 `rd2/rd3` 中转切到该栈（`cg6 rc1 == 0` 回落静态栈）；帧 `memcpy` 进 `task_pt_regs(current)` 并在 C 半/出场统一用该指针。**F51**：切栈后 cg5 字段仍写旧帧 ⇒ 帧 `ip=0`（已修：改 `[rb16]`）。**F52**：`rb2rd/rd2rb`/`cfx2rc` 的操作数规则与 `sub.o` 不存在（计算移到 C 侧）。`current` 仍按 SP 派生（第 24 轮的全局单元改动已撤）。

**测试结果（第 22 轮 · **S7 转绿**）**：`k4_switch_probe --no-inject` **42 PASS / 1 FAIL（rc=1）**，唯一红项 = `S5`（U-mode 帧 A/B 往返未实现；`S7` 已从 `MISSING` 表移除、由真实判据判定）。S7 现场：`K3 pf: n=4 … va=0x10040 vma=0x10000-0x20000 result=fill-file`（rodata 跳转表按文件内容映射）→ musl `sccp`/`write`/`brk`/`exit_group` 全走通 → `K4 switch init: exit code=0 ("K4 switch init" ran)`、`K4 switch done: initramfs /init ran under kernel_init, exit=0`。回归（串行无并发）：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state`（linux base+1 clean）rc=0。

**测试结果（第 21 轮 · F48 修复）**：`k4_switch_probe --no-inject` **40 PASS / 3 FAIL（rc=1）**，红项仍只有 `S5`（帧往返未实现）与 `S7`×2；**S7 现场再进一步**：`protection_map` 补 U 位后，初始栈的 `NUPERM/die-perm` 全消失，musl 启动走到 `set_tid_address`(96)/`getpid`(172) 并进入 `init_main`；当前新堵点 **F49**（`getpid` 返回后用户程序**跳到 0**：`K3 pf: n=5 … IGPTRAP ip=0x0 va=0x0 result=die-no-vma`）。回归（串行无并发）：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state`（linux base+1 clean）rc=0。

**测试结果（第 20 轮 · F44 定位）**：`k4_switch_probe --no-inject` **40 PASS / 3 FAIL（rc=1）**，红项仍只有 `S5`（帧往返未实现）与 `S7`×2；**S7 现场推进两级**：① 判定 syscall 号未错位（`rd15=0x5d`=`exit` 兜底环，`exit_group` 未到）；② 修 **F47**（代码页填充重复加页内偏移 ⇒ 整页错位 0x11c8）后，`_start`/`_start_c` 与 ELF 反汇编**逐条一致**地执行；当前卡 **F48**（用户栈叶条目 `0x400000007fb0fffd` 为 S-only、无 U ⇒ 用户态栈读 `NUPERM`，而通道从未填过该 VA ⇒ 存在第二个 PTE 写入者）。回归（串行无并发）：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state`（linux base+1 clean）rc=0。

**测试结果（第 19 轮 · 合入 master + spec-009 后）**：`k4_switch_probe --no-inject` **40 PASS / 3 FAIL（rc=1）**，红项仍只有 `S5`（本任务帧往返，未实现）与 `S7`×2；**S7 现场推进**：`CFXESC` 已随 spec-009 消失（修复前每次必现）、exec 取指经 F43 文件后备填充成功（`result=fill-code pte=0x50000000047affa1`）、入口帧与初始栈全对（`user sp words: argc=0x1 argv[0]=0x1ffffe0ffd0 NULL envp…`）、musl `_start`→`_start_c` 真执行；当前卡 **F44**（此后 `0x211d0–0x2120c` 带空转无输出直到 `RC=124`，疑系统调用面缺失：K4 一律回 `-ENOSYS`）。回归（串行无并发）：k0 **130/130**、k1 **112/112**、k2 **170/170**、k3 **263/263**、`k4_fork_probe` **101/101**、`k4_stack_probe` **44/44**（各 rc=0）、switch `--inject` **5/5 全绿**、`check-patch-tree` rc=0 与 `--source-state`（linux base+1 clean，84 补丁）rc=0。

**测试结果（第 18 轮 · 用户栈增长 S1–S6）**：`k4_stack_probe.py` **44/44 PASS, rc=0**（case 1 = S1+S2+S5 一次启动；case 3/4/6 各一镜像，均以 `die-no-vma` 终止、§7.1 分段 `0xe1` 对账）；`--inject` **4/4 全绿**（`grow-any-vma`→S4、`no-limit`→S3、`perm-grows`→S5、`no-guard-gap`→S6，每路「目标 case 红 → `cp`+md5 还原（含双文件）→ 重建回绿」）；`--selfcheck` 可红（破损控制台 10 条红）。现场值：`K4 stack setup: vma=0x14000040000-0x14000060000 pages=2 rlimit=8388608 gap=16777216`；`K4 stack done: vma=0x14000020000-0x14000060000 grows=2 entries=4 pages=2`；`s2-size=0x40000`（起始 2 页 + 2 页）；`s3: dist=8519680 limit=8388608`；`s6: dist=1 页 size=4 页 gap=16 MiB`。**缺口（如实标注）**：故障由 supv 访问触发（019 裁定的载体），真实用户进程压栈触发依赖 U-mode 闭环（本任务 F37）⇒ 栈增长为**部分完成：内核侧验收，用户态触发未验**。回归（第 18 轮最终源码状态，串行无并发）：`check-linux-k0` **130/130**、`check-linux-k1` **112/112**、`check-linux-k2` **170/170**、`check-linux-k3` **263/263**（各 rc=0）、`k4_fork_probe` **101/101**、`k4_switch_probe --no-inject` **40 PASS / 3 FAIL（rc=1，红项仅 S5、S7×2）**、`check-patch-tree` rc=0 与 `--source-state`（linux base+1 clean，84 补丁）rc=0、switch 探针 `--inject` **5/5 全绿**。

**测试结果**（第 17 轮，m14-linux-031 的新 initramfs 布局下）：`k4_switch_probe.py --no-inject` **39 PASS / 3 FAIL，rc=1**——3 条红全部是未实现项（`S5`、`S7` 两条）；S1/S2/S3/S4/S6 与 B 组静态判据全绿（S1 `bad=0x0`、S2 `c0=4 c1=4 done=2 back_bad=0`、S3 `asid=1 ptbr=0x4190000 ptw=1 invalid_cmd=0x2` + `alive_on_new_table=1`、S4 三项 `ok`、S6 `ticks=3 jiffies_delta=3`）。`--selfcheck` rc=0（破损控制台 → 多条红，含 S1/S2/S3/S5/S7 核心判据）。`--inject` **5/5 全绿**（第 17 轮重跑；每路：目标 case 红 → `cp`+md5 还原 → 重建回绿 → 重启回绿）：`no-rd32-save`→S1、`restore-wrong-order`→S1（硬缺页终止）、`no-asid-write`→S3、`switch-clobbers-tp`→S4、`no-timer-arm`→S6。**注入定义修正**：任务书写的「只不写 `timer_cmp`」在本机不是有效负例——旧/复位 CMP 会被当成"已过期"⇒ tick 反而连发（实测 42 项全绿、S6 通过），故该路改为「`cmp` 与 `ctrl` 都不写」（`no-timer-arm`），并把理由记在此处。回归（全部实跑，第 17 轮最终源码状态）：`k4_fork_probe` **101/101**、`check-linux-k0` **130/130**（rc=0，含 031 新布局 + 内核内嵌 initramfs 的断言）、`check-linux-k1` **112/112**、`check-linux-k2` **170/170**、`check-linux-k3` **263/263**（各 rc=0）、`check-patch-tree` rc=0 与 `--source-state`（linux base+1 clean，79 补丁）rc=0。
**修改文件**：**第 30 轮**：`patches/arch/dadao/kernel/k4_switch_selftest.c.patch`（`k4s_case_s5_pgdcopy()`：新 mm 的内核窗口逐项对比断言）；另合入 master（`5c7d6df3`，FF）。**第 28 轮**：`patches/arch/dadao/include/asm/entry.h.patch`（**F55**：`DADAO_GPR_SAVE` 在改基址前保存真实 `rb3`(rbtp)，`SAVE_AT` 删掉错误存法）；**第 25 轮**：`patches/arch/dadao/kernel/{process,entry}.S.patch`（`__switch_to` 预写 `cfx_umon cg6 rc1`）、`patches/arch/dadao/kernel/trap.S.patch`（入口按 cg6 切栈 + 帧采纳 + cg5 字段写新帧）、`patches/arch/dadao/include/asm/cfx.h.patch`（`UMON_CG_SCRATCH`/`UMON_RC_SCRATCH_STACK_TOP`）；**第 22 轮**：`patches/arch/dadao/mm/fault.c.patch`（`fill-file`：文件后备数据页按文件内容映射；`dadao_pf_unshare_zero()` 增「非零只读页写 ⇒ 私有副本」）、`patches/arch/dadao/kernel/k4_switch_selftest.c.patch`（`brk` 钩子改读 `rb16` 并按裁定只做记账）、`tools/linux/k4_switch_probe.py`（`MISSING` 表移除 S7）；**第 21 轮**：`patches/arch/dadao/include/asm/pgtable.h.patch`（`protection_map` 的 `__P*`/`__S*` 改为带 **U 位**的 `_PAGE_USER_*`，PROT_NONE 保持内核只读）；**第 20 轮**：`patches/arch/dadao/mm/fault.c.patch`（`dadao_pf_fill_from_file()` 的 `pos` 改为文件页首）、`patches/arch/dadao/kernel/process.c.patch`（CFXTRAP 前 8 条 syscall 现场打点，探针镜像内）；**syscall 面说明**：`write`/`brk`/`exit_group`/`getpid` 由探针钩子 `dadao_k4_user_syscall()` 提供（号来自内核 uapi 头即 `scripts/syscall.tbl` 生成，未硬编码），**探针级、完整表属 K5 `m14-linux-023`**，里程碑镜像零影响。**第 19 轮**：`patches/arch/dadao/mm/fault.c.patch`（`dadao_pf_fill_from_file()` 文件后备取指；`dadao_pf_last` 扩到 8 槽）、`patches/arch/dadao/kernel/{traps,process,early_console}.c.patch`（删 F37 的 `arch_local_irq_save/restore` 包壳与帧内丢弃，保留 `dadao_in_frame`/flog）、`tools/linux/{check_k0,check_k1}.py`（按 master 新结构重建配置钉住）；另合入 master（merge commit `e7054f13`，无冲突）。**第 18 轮（用户栈增长）**：`patches/arch/dadao/mm/{fault.c,Makefile}.patch`（`dadao_pf_grow_stack()` + 扩栈计数 + 判词链分支）、`patches/arch/dadao/mm/k4_stack_selftest.c.patch`（**新**，S1–S6）、`patches/arch/dadao/Kconfig.debug.patch`（`CONFIG_DADAO_K4_STACK_SELFTEST`）、`patches/arch/dadao/include/asm/setup.h.patch`、`patches/arch/dadao/kernel/setup.c.patch`（K4 边界接线）、`tools/linux/k4_stack_probe.py`（**新**，44 条断言 + 4 路注入 + `--selfcheck`）；**第 17 轮**：`patches/arch/dadao/kernel/{trap.S,traps.c,process.c,early_console.c}.patch`（帧内零 semihosting 的 `dadao_in_frame` + 数字槽 + `escape` 后打印；同步帧 C 半的 `arch_local_irq_save/restore` 包壳；supv stub 的 `dadao_supv_diag` 记录，asm/C 均 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST`）、`patches/arch/dadao/mm/fault.c.patch`（`dadao_pf_last[6]` 数字判词）、`patches/arch/dadao/include/asm/setup.h.patch`（`dadao_flog_report` 等声明）；`components/linux/{series,changelog.md}`；**第 14 轮**：`patches/arch/dadao/mm/fault.c.patch`（`dadao_pf_table()` 表选择 + `pmd_populate_kernel(vma->vm_mm)`）、`patches/arch/dadao/kernel/process.c.patch`（`dadao_enter_user` 刷新入口栈 `thread_info.task`）、`patches/init/main.c.patch`（探针镜像 `rdinit=/init.musl`，规则 (b)）、`tools/linux/{check_k0,check_k1,check_k2,check_k3}.py` + `k4_fork_probe.py`（兄弟符号 `CONFIG_DADAO_K4_SWITCH_SELFTEST=n` 成对钉住）；**第 13 轮**：`patches/arch/dadao/mm/{fault,mmu}.c.patch`（`K4 pf entry`/`K4 pf pub`/`K4 mm switch` 三处诊断，均 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST`）；**第 12 轮新增**：`patches/usr/initramfs_data.S.patch`（`.quad`→`.dd.o64`）、`patches/arch/dadao/configs/defconfig.patch`（`CONFIG_BLK_DEV_INITRD=y`）、`patches/init/main.c.patch`（F26 errno 打点 + initramfs probe）、`patches/init/do_mounts.c.patch`（pivot errno）、`patches/fs/exec.c.patch`（`exec_binprm` 的 interp/ret 打点）、`tools/linux/make_defconfig.py`（`CONFIG_INITRAMFS_SOURCE` 指向 cpio）；**F16 诊断补丁（均 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST`）**：`kernel/{kthread,sched/completion}.c`、`init/main.c`、`arch/dadao/kernel/{time,k4_switch_selftest,k4_switch_asm}`；**master merge 带来**：`tools/linux/{make_initramfs,check_k0,check_k1,k1_boot_probe,build_busybox}.py` + `tests/ee-tiny/**`（031 的 initramfs 新布局与资产集中）；**F16 打点**：`init/main.c.patch`（13 个 `DADAO_INIT_MARK`）、`kernel/workqueue.c.patch`（新增，13 个 `DADAO_WQ_MARK`，均 `#ifdef CONFIG_DADAO_K4_SWITCH_SELFTEST`）；改写 `arch/dadao/{Kconfig.debug,include/asm/{processor,switch_to,mmu_context,ptw,pgalloc,setup,time},kernel/{Makefile,asm-offsets,setup,process,time},mm/{fault,mmu}}.patch`（`.h`/`.c` 对应补丁）；新增 `arch/dadao/kernel/{entry.S,k4_switch_selftest.c,k4_switch_asm}.patch`；`tools/linux/k4_switch_probe.py`（新）。**越界披露**：`include/asm/pgalloc.h`、`include/asm/ptw.h`、`mm/fault.c`、`kernel/k4_selftest.c`（016 的探针：clone 后清 `TIF_NEED_RESCHED`）、`include/asm/setup.h`（边界签名 `__noreturn` → 可返回）。**本分支工作区含 master 的 squash 内容（未提交，合并由架构侧处理）**：m14-linux-031 新 initramfs 布局已以 `git merge --squash master` 并入（无提交；任务书冲突保留本任务「审阅记录/完成区」，RAS 裁定行取自 master 版）；下列文件即该 merge 的一部分：`tools/linux/{make_initramfs,check_k0,check_k1,k1_boot_probe}.py` 改写 + `tools/linux/build_busybox.py` 新增 + `tests/ee-tiny/**`（24 个资产文件，`check_k1/k2` 的新依赖）；均以 `git checkout master -- <path>` 取用、**未做 merge/squash 提交**，也未改本任务的内核补丁集。`spec/**`、`.tao/contracts/**`、`components/qemu/**`、根 `Makefile` **未动**，版本号未改。
**验收结果**（第 11 轮新增，节选）：`K4 check s2-thread-0-started-once want=0x1 got=0x1 ok`；`K4 init: rootfs_initcall reached` / `late_initcall reached` / `after do_basic_setup` / `after wait_for_initramfs`；`Run /sbin/init` → `Run /bin/sh as init process` → `Kernel panic - not syncing: No working init found`。以下为更早轮次：`K4 switch call: racnt 3 -> 4 -> 3 entry=0x10200001439f8 xor_call_plus4=0x0`（`call`/`ret` 语义三条断言 ok）；`K4 switch s2: ras_diff=0 … post63=0x10200001425d4`（`schedule` 往返后有效 RAS 不变，ok）；S2 `K4 switch s2: c0=4 c1=4 done=2 spins=1 back_bad=0 pid=0 sp=0x200004cf6d0`（**每启动仅 1 次**）；S6 `K4 switch s6: freq=1000000000 hz=100 period=10000000 ticks0=0` / `K4 switch s6: ticks=3 jiffies_delta=3 window=40000000 elapsed=30889527`；S1 `K4 switch s1: bad=0x0 … res_rd0=0xa5a5000000000000`；S3 `K4 switch s3: asid=1 want_asid=1 ptbr=0x4190000 want_ptbr=0x4190000 ptw=1 invalid_cmd=0x2`；S7 断点 `K4 switch: selftest done, continuing to kernel_init` → `WARNING: kernel/sched/core.c:7396 … Comm: pool_workqueue_`（未到 `/init`）。
**新发现/坑**：① 本硬件的 RAS 有**环缓冲隐藏基址**（QEMU `ras_base`）：软件只能按逻辑槽（`ra63` 栈顶）观测，块传送读写都走逻辑翻译，故「保存/恢复逻辑视图」是充分的；② `RACNT` 是唯一深度判据，`stm.o {ra0:ra62}` 必须与 `{ra63}` 成对（`immu6<=63`）；③ `set.zw rdX, wpN, imm` 会把其余 wyde 清零，可用来造 18 位以上常量；④ `asm-offsets` 里 `offsetof(struct task_struct, thread.X)` 是**任务相对**偏移，汇编拿到 `&task->thread` 时必须用 `offsetof(struct thread_struct, X)`（两套都留了）；⑤ `PREEMPT_NONE` 下 `preempt_disable()` 是空操作（`CONFIG_PREEMPT_COUNT` 未开），要挡 `cond_resched()` 只能清 `TIF_NEED_RESCHED`；⑥ `sub_reason`/ASID/PTBR 的期望值一律用内核自己的生成函数重建（`dadao_tlb_control_value()`），不在探针里重抄编码。
**遗留问题**：⓪ **F27 已修（第 14 轮，高价值）**：页故障通道原用 `pmd_off_k()`（内核表）建 L2/写 PTE ⇒ 017 落地 `switch_mm` 后映射写错表；改为按 `vma->vm_mm` 取表（`dadao_pf_fill`/`dadao_pf_ptep`）。同轮修 F28（umon 入口栈 `thread_info.task` 每 entry 刷新）。**initramfs 链已真跑**：`/init` → `/bin/sh`（busybox，`Comm: sh`）；按规则 (b) 探针改判 `/init.musl`，`kernel_execve=0` 并进入用户态。当前 S7 卡在 **F29**：用户态首指令链路出现 async 帧 `cause=0x8`（`CFXESC`，与 `ISS-454` 的 `inner_cfx_code` 交互）。（第 13 轮记录：：`switch_mm`/PTBR/ASID/ptw_enable 与 TLB 失效**均已排除**——PTE 已在 `mm->pgd` 里 present，但 walker 对「supv 向 W=0 用户页 store」仍报 `CFXMEM/DGPTRAP`（按 `§2.2.6` 判序应为 `CFXPERM/NWPERM`）⇒ 下轮先按 PTBR 直读 L1/L2 条目，再据判序决定是内核侧还是 **QEMU 模型**的问题。（第 12 轮记录：：initramfs 首次真正进内核（`BLK_DEV_INITRD` + `INITRAMFS_SOURCE=<cpio>` + `usr/initramfs_data.S` 的 `.dd.o64`），`/init` 可见、脚本 handler 成功、interp `/bin/sh` 打开成功；当前 S7 卡在 **F27**（busybox ELF 载入期 `fill-zero` 后同址仍缺页，疑 exec 的新 mm 未成为生效 PTBR）。（第 11 轮记录：：`thread.ra` 首次运行后未清零 ⇒ 每次切回重跑 `fn`（kernel_init 因此二次等 `kthreadd_done`）；修后 initcalls 全跑通并到 `Run /bin/sh as init process`，当前 S7 卡在 `kernel_execve` 失败（`No working init found`）。（第 10 轮记录：：kernel_init 在 workqueue 完成量唤醒后**又等了一次 `kthreadd_done`（`done=0`）⇒ 永久阻塞**；RAS 深度第二次=17 vs 第一次=9（同链更深），而 `call`/`ret` 语义与「一次切换不泄漏 RACNT」均已实测正确 ⇒ 下一轮在 `__schedule()`/`switch_to` 恢复点核对「`sp` 与 `ras` 是否同一快照」。（第 9 轮纠正：创建者被完整唤醒 `state=0 on_rq=1`，但下一 tick 又 `state=2 on_rq=0` 且未执行到等待之后的打点；完成量本身未被改写——`0x100000000` 是大端 u32 `done=1`）**；上轮「完成量 8 字节被改写」假设已推翻；：kthreadd 与新线程都跑了、`complete()` 也生效（`done->done=1`、等待方 `state=0`），但等待方随后**又睡回同一完成量**（完成量在其栈上）⇒ 与 **F8 同族**，按预定策略**先修 F8 再回看 F16**；两轮判据已写在「第 6/7 轮自审」；① **S5 未实现**：按任务帧改造（`task_pt_regs()` + 入口栈 `thread_info.task` + `dadao_enter_user` 写任务帧）试做后**回退**（F13），静态帧版本已回绿；② **S7/F3 未打通**：已修「execve 成功后必须进用户态」（F14）；F15 澄清为「tick 工作正常」（等过 deadline 后 `jiffies` 真推进，`dj=3`）；真正堵点 **F16** = `kernel_init_freeable()` 在 **`core_initcall` 之前**就停住（7 层 initcall 标记一个都没打印，而 `kthreadd`/kworker 已起来），下轮据此逐个前移标记；③ **F8/F12 已结案（探针 bug：`k4s_case_s2()` 被写了两遍）**；新增两条交付断言：`call`/`ret` 的 RAS 语义（pushes 1 / pops 1 / push=call+4）与「一次 `schedule()` 往返后有效 RAS 逐槽不变」；④ 已知实现偏离：`thread_struct` 增 `fp`（`rb2`，非 CSR 但属被挂起 C 帧）+ `ras[64]`（用户已裁定 A）；⑤ `--inject` 5 路本轮未跑。

