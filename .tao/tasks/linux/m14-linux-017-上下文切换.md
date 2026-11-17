# m14-linux-017: 上下文切换（switch_to 汇编 + 调度跑双任务 + FP 保存范围）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（进程骨架 + `copy_thread` + `thread_struct`）
**可并行分片**：否（`components/linux` 单写者；共享 `include/asm/{switch_to,processor}.h`、`kernel/process.c`）
**并行组**：与 K4 其余任务**串行**（同组件同写者）
**预估**：5–7 h（风险在 `__switch_to` 汇编、FP 保存范围（待裁定 1）、U-mode ↔ S-mode 帧往返）
**档位**：大改（新汇编入口 + 调度接线 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

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

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_switch_probe.py` rc=0，逐 case 打印；期望值现场派生（callee-saved 集合 ← `contract-abi §4.5`，块传送布局 ← `SimRISC-01 §1/§2`，`switch_mm` 步骤 ← `contract-tlb TLB-30`）。
2. **探针 case（每条一条可达 FAIL 断言）**：
   - `S1 保存/恢复往返`：`__switch_to(a,b)` 后 `b` 的 callee-saved 字段与切换前一致（逐寄存器，用现场注入的哨兵值）；`a` 的字段被保存到 `a->thread`。
   - `S2 双任务交替`：fork 后两个任务各递增自己的计数器并 `schedule()`，探针断言「两个计数器都推进」（证明真切换、非单跑）。
   - `S3 switch_mm`：切到新 `mm` 后 `cfx_ptw_tlb_asid` == `mm->context.asid`（现场读值），且失效命令值按 `contract-tlb TLB-19` 现场重建（不写死）。
   - `S4 callee-saved 越界`：`__switch_to` 只碰 callee-saved 段 + SP，**不得**碰 caller-saved（`rd8–31`/`rb8–31`）与保留（`rb2`/`rb3`）——探针用哨兵值断言切换前后 caller-saved/保留寄存器不变。
   - `S5 U-mode 帧往返（用户 2026-11-17 选 C）`：两个用户进程 A/B 交替切换，断言各进程用户态帧字段逐项正确——`ip`/`rb1`/`rb3`/`rd32–63`/`rb32–63`（callee-saved）在 A→B→A 往返后与首入一致（现场哨兵值）；`status == 0`；**不含递归**（切换路径不写 cg5→cg6）。
3. **≥5 路注入**（`cp`+md5 还原 + 重建回绿）：① `__switch_to` 不保存 `rd32` 段 ⇒ `S1` 红（b 侧 rd32 哨兵被 clobber）；② 保存了但恢复错序 ⇒ `S1` 红；③ `switch_mm` 不写 ASID ⇒ `S3` 红；④ 切换碰了 `rb3`（rbtp）⇒ `S4` 红；⑤ 用户态帧不保存 `rb3`（rbtp）⇒ `S5` 红（A 往返后 rbtp 被 clobber）。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-017/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/include/asm/{switch_to,processor}.h.patch`、`components/linux/patches/arch/dadao/kernel/{process.c,entry.S,Makefile}.patch`（entry.S 新建）、`components/linux/patches/arch/dadao/mm/mmu.c.patch`（`switch_mm` 落地）、`components/linux/changelog.md`、`tools/linux/k4_switch_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-abi §4.5`（callee-saved/CSR）、`SimRISC-01 §1/§2`（块传送）、`contract-tlb TLB-30`（switch_mm）为准；**不得**套 RISC-V `ra`/`s0-s11` 或 x86 帧布局。
5. `__switch_to` 必须在关中断/关抢占的临界区被调（`switch_to` 的既有调用点保证）；`last = __switch_to(prev,next)` 语义与 `switch_to` 宏一致（返回 `prev`）。
6. **单帧、不递归（用户 2026-11-17 选 C）**：U-mode ↔ S-mode 帧往返用 cg5 单帧，**不实现同 cfx 递归**（cg5→cg6 保存留 K5）；用户态进程切换不引入 umon 递归。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~（待裁定 1）FP 保存范围~~ **已裁定（用户 2026-11-17）**：`rd/rb/rf/ra` **全部在异常入口/出口帧处理**（由 `m14-linux-022` 落地：`ra`/`rf` 用 `ldm.o`/`stm.o` 块传送）；`__switch_to` **不再单独保存/恢复 FP**，只切换内核栈与内核态 callee-saved。本任务的 `S5`（U-mode 帧往返）按此断言。
2. ~~（待裁定 4）~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环并入本任务 + `016`；「用户进程 A↔B 切换」断言（`S5`）已加入，单帧、不含递归（同 cfx 嵌套留 K5）。

## 审阅记录

（待填）
