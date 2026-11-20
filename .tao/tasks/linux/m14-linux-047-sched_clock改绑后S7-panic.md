# m14-linux-047: 工具链修复后 `k4_switch` S7 panic（`__mmdrop(&init_mm)`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-llvm-007`（已把同节 weak 调用改为发重定位，**共享安装根已重建为新工具链**）
**可并行分片**：否（linux 单写者）
**预估**：4–6 h
**档位**：大改（内核缺陷定位 + 修复）
**状态**：待验收

## 背景（事实，来自 `m14-llvm-007` 的实测）

- `m14-llvm-007` 修好后，内核里有 **8 个调用点**从「弱定义」改绑到强定义：`sched_clock` × 7（`kernel/sched/build_utility.o`）+ `release_thread` × 1（`kernel/exit.o`），全内核 `.text` 差 **23 B**；
- 隔离副本（同一内核源码/配置）对照：旧工具链 `k4_switch` **52/52**；新工具链 **50/51**；
- 失败点 `S7`：`Run /init.musl` 处 panic
  `kernel/fork.c:725 BUG_ON(mm == &init_mm)`（`__mmdrop` 收到 `&init_mm`）；
- 其余 K0–K3、K4 其它探针（fork 104/104、kthread 112/112、cow 86/86、stack 44/44）、K5（104/97/174）全绿；
- 判定：这是**被静默折叠长期掩盖的内核缺陷**，不是工具链回归。

## 目标

1. **定位根因**：为什么 `__mmdrop(&init_mm)` 会发生。两条线索先查：
   - `sched_clock` 强实现（`CONFIG_GENERIC_SCHED_CLOCK=y`）在 DADAO 上的行为——是否依赖尚未初始化的时钟，导致某条路径提前/延后；
   - `release_thread` 强定义（`arch/dadao` 或通用）是否对 `mm` 做了 `mmput`/引用计数操作。
2. **修复**：优先 arch 侧（`arch/dadao`）；确需动通用代码的，先报主会话转用户裁定（禁止自决）。
3. **回归**：新工具链下 K0–K5 全绿、`k4_switch` 恢复 **52/52**。

## 验收（逐条贴真实 rc）

1. **根因证据**：给出「改绑 → 哪条路径 → `__mmdrop(&init_mm)`」的链条（反汇编/调用点/引用计数变化），不是猜；
2. **修复验证**：`k4_switch` 52/52；K0 146 / K1 112 / K2 170 / K3 263 / K4 五探针 / K5 104/97/174 全 rc=0；
3. **可达 FAIL ≥2 路**（`cp`+md5）：① 撤回修复 ⇒ S7 复现 panic；② 用旧工具链对照 ⇒ 52/52（证明差异来自改绑）；
4. `check-patch-tree` linux 段 0 问题；`apply_series` 幂等；
5. 完成区写明：改了 arch 还是通用、为什么不能只在 arch 侧解决（若动通用）。

## 约束

独立 `git worktree`；不提交 git；**不得回退/重建共享工具链**（已是修复版，记录 `clang/llvm-mc/ld.lld` md5 并核对）；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` **全绿（38 项检查，rc=0）**；`k4_switch` **52/52**（含 6 路内建反例 **76/76**）；K0 146/146、K1 112/112、K2 170/170、K3 263/263、K4 fork 104/104・kthread 112/112・cow 86/86・stack 44/44、K5 clone 97/97・syscall 104/104・futex 174/174，全部 rc=0。
**修改文件**：`components/linux/patches/arch/dadao/kernel/k4_switch_selftest.c.patch`（根因修复 + 新断言 `s5-init-mm-lazy-ref`）、`components/linux/patches/arch/dadao/kernel/k5_futex_selftest.c.patch`（同一根因家族：F7 的调度顺序假设）。**只改 `arch/dadao`**，未动 `kernel/`、`mm/`，未动任何 `CONFIG_*`。
**验收结果**：
1. **根因链条（实测，证据目录 `logs/deficit-chain.log`）**：`sched_clock` 改绑后，S5 那个"借用 mm"的 kernel thread 真正被调度出去了 ⇒ `context_switch()` 的 kernel→user 分支把 `rq->prev_mm` 交给 `finish_task_switch` 的 `mmdrop_lazy_tlb_sched()`，日志 `MMDBG drop init_mm count=2`（2→1）；而该任务（`k4_switch_selftest.c` 的 `k4s_s5_task`/syscall 收尾）直接写 `current->mm`/`current->active_mm`，从未做 `mmgrab_lazy_tlb`/`mmdrop_lazy_tlb` 配对 ⇒ `kernel_init` 的 exec 走到 `exec_mmap()` 的 `mmdrop_lazy_tlb(&init_mm)` 时 `count=1`，drop 成 0 ⇒ `__mmdrop()` 的 `BUG_ON(mm == &init_mm)`（干净构建报 `kernel/fork.c:725`；加了临时打点时为 732）。旧工具链下该任务在此点从未被换出，泄漏与亏空互相抵消，所以一直"绿"——这是被折叠掩盖的**端口侧缺陷**，不是工具链回归。
2. **修复**：任务入口 `mmgrab_lazy_tlb(自己的 mm)` + `mmdrop_lazy_tlb(继承的 active_mm)`（后者有 NULL 保护），收尾反向 `mmgrab_lazy_tlb(&init_mm)` / `mmdrop_lazy_tlb(自己的 mm)`；新增断言把不变量做成可判：`s5-init-mm-lazy-ref`，want 由 `IS_ENABLED(CONFIG_MMU_LAZY_TLB_REFCOUNT)` 派生（2，无 lazy 引用计数时为 1）。
3. **可达 FAIL（cp+md5，三项都实测）**：① 撤回修复 ⇒ `[FAIL] S7` + `BUG: failure at kernel/fork.c:725/__mmdrop()`，还原后 md5 一致并回绿 52/52；② 旧工具链 + 同一源码 fresh 构建 ⇒ 52/52；③ `diff_sites.py` 的 allow-list 去掉 `release_thread` ⇒ FAIL。
4. **工具链改动面（反汇编，fresh-vs-fresh）**：总共 **26 B** 代码差 = `.text` 8 个调用点（`sched_clock`×7 + `release_thread`×1，23 B）+ `.init.text` 1 个（`start_kernel` 的 `trap_init`，3 B）。后者是任务书"8 个调用点"之外的**第 9 处同节 weak 改绑**（`trap_init` 弱体在 `init/main.c`、强体在 `arch/dadao/kernel/setup.c` 且为空，无行为差）；其余 `.rodata`/`.data` 差异只是 banner 时间戳、`.notes` 只是新链接带 build-id（+36 B），都在证据脚本里单独打印、不参与判据。
5. **补丁树**：`check-patch-tree` linux 段 **96 patches、0 断言**；整仓 rc=1 只因并行任务留在共享运行期目录的 llvm-project/chipyard 树，脚本按组件分流并逐条打印（判据只对 linux 段断言）。`apply_series --component linux` 二次运行 "already applied (base+1, matches patches)"，幂等。
6. **改了 arch 还是通用**：**arch**（`arch/dadao/kernel/*_selftest.c`，随内核补丁集发布）。通用 `kernel/`/`mm/` 无需改动：`exec_mmap()` 的 `mmdrop_lazy_tlb(active_mm)` 与 `context_switch()` 的懒 TLB 记账都是上游语义，缺的是调用方对 `mmgrab_lazy_tlb`/`mmdrop_lazy_tlb` 的配对（`Documentation/mm/active_mm.rst` 明写）。因此不需要用户裁定。
**新发现/坑**：
- 共享安装根已是修复版：`clang 5ec67d1c0e393931e897b14222aa65b4`、`llvm-mc ad34d612d21a37a32e902fe314c0d64d`、`ld.lld 29058efd30fb6aedcd398d21ffb132b5`；本轮**未重建、未回退**。
- 同一根因模式还散落在 `k4_cow_selftest.c`、`k4_stack_selftest.c`、`k4_kthread_selftest.c`、`k5_{syscall,futex,clone}_selftest.c`（直接写 `current->mm`/`active_mm`）。这些镜像本轮全绿（借 mm 期间没有可用抢占点，或借完立即归还），但建议后续统一改用 `mmgrab_lazy_tlb`/`mmdrop_lazy_tlb`（或 `kthread_{use,unuse}_mm`）。
- `k5_futex` 的 F7 是被同一根因家族打出来的**间歇**红（新工具链 1/3 失败、旧工具链 0/3）：它假设"`k5f_child_exit` 完成时子任务已跑完 `mm_release()`"，而 `CONFIG_PREEMPT_VOLUNTARY=y` 下父任务可以在中间被唤醒。已改为有界、让出 CPU 的等待（断言不变），5/5 复跑绿且观察到 `spins>0`（等待确实在起作用）。
- `check-patch-tree` 是**整仓**门控：在任务 worktree 里跑必须按组件分流判据，否则会被别人的在途组件树判红（不是本模块问题）。
- 工具链 A/B 对照必须 **fresh-vs-fresh**：增量树 `UTS_VERSION` 的构建号位数不同会改变 banner 串长，把 `.rodata` 之后所有地址整体平移（曾误报"8076 B 代码差"）。
- `.work` 在任务 worktree 里是**符号链接**：证据脚本取仓库根必须用调用者 cwd 的 `git rev-parse`（`pwd -P` / `__file__` 会解析到主检出，读到别人的内核源码）。
**遗留问题**：无未修 finding。`k5_futex` 的 F7 hunk 与 K4 修复同属本任务根因家族，故一并修；若认为它应独立成任务，可单独回退该补丁的两处改动（K4 的 52/52 不依赖它）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-21）

**范围**：两处补丁（`k4_switch_selftest.c` 根因修复 + `k5_futex_selftest.c` 的 F7 等待）。逐行审查 + 行为复验，证据与上面「验收结果」同源。

- **入口配对**：先 `mmgrab_lazy_tlb(mm)`，再（`active_mm` 非 NULL 时）`mmdrop_lazy_tlb(old)`。若 `old == mm` 则净 0；NULL 已保护，探针不因不变量暂未成立而崩。
- **出口配对**：`mmgrab_lazy_tlb(&init_mm)` 在发布指针之前，随后 `mmdrop_lazy_tlb(own)`；与入口严格对称（各自 grep 到 1 处 grab、1 处 drop），无双重释放/泄漏。
- **断言派生**：want 用 `IS_ENABLED(CONFIG_MMU_LAZY_TLB_REFCOUNT) ? 2 : 1`，不写死 2；打印与断言读同一次现场值。
- **k5f 等待**：有界（1000 次 `schedule()`）、每次让出 CPU，不会死循环；`schedule()` 在 umon 钩子内已有先例（同探针 `wait_for_completion`、K4 S5 钩子）。判据未放宽——`--inject clear-tid-off` 仍令 F7 红（实测）。
- **反例强度**：撤回修复后 panic 由两条独立断言捕获（S7 红 + 具体 BUG 行）；还原用 `cp`+md5 对账，`git status` 干净，且回绿 52/52。
- **判据派生**：`diff_sites.py` 现场统计差异字节与改绑目标，allow-list 缺项即红（实测一次）；`run.sh` 的 52/76 等计数全部从工具输出解析，不写死。
**判决**：无未修 finding → 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-21，大改档）

**重跑（全部自己执行，不采信转述）**：运行期证据目录内的 `run.sh` → `RESULT: PASS (38 checks)`；`k4_switch` 基线 **52/52**、内建反例 **76/76**（6 轮注入全 PASS）；K0 **146/146**、K1 **112/112**、K2 **170/170**、K3 **263/263**、K4 fork 104・kthread 112・cow 86・stack 44、K5 clone 97・syscall 104・futex 174，全 rc=0。
**可达 FAIL 两路（我自注入，`cp`+md5 对账、还原后回绿）**：① 撤回修复 ⇒ `PROBE_EXIT=1`、`50/51 passed, 1 FAILED`、`[FAIL] S7`、`BUG: failure at kernel/fork.c:725/__mmdrop()!`，还原 md5 回到修复态（标记 1/1/1）；② 删出口 `mmgrab_lazy_tlb(&init_mm)` ⇒ `EXIT=1`、`45/47`、`[FAIL] S7` + 同一 `fork.c:725`，失败落在 S5 归还期（少一次 grab 使 init_mm 被 drop 到 0），还原后 `apply_series` 判 `already applied` rc=0。
**链条核验**：`context_switch()` 的 `if (!prev->mm) rq->prev_mm = prev->active_mm` → `finish_task_switch()` 的 `mmdrop_lazy_tlb_sched(mm)`，与日志 `cs p=<prev> pamm=<init_mm> n=<next> nmm=<own_mm>` 后紧跟 `drop init_mm count=2`（2→1）对得上；`exec_mmap()` 的 `mmdrop_lazy_tlb(active_mm)` 把 1→0 触发 `__mmdrop`；修复后新断言 `s5-init-mm-lazy-ref` 现场取值通过 ⇒ 2→1→0 亏空闭合。
**修复正确性**：入口 grab(new)+drop(old)、出口 grab(init_mm)+drop(new) 严格对称，grab 先于发布指针，`active_mm` 判空；want 由 `IS_ENABLED(CONFIG_MMU_LAZY_TLB_REFCOUNT)` 派生、不写死 2。`git diff HEAD~1 -- components/linux/patches/kernel components/linux/patches/mm` 为空，`git show --name-only HEAD` 恰 3 文件 ⇒ 只动 arch。
**改动面**：`diff_sites` 实测 `.text 23 B + .init.text 3 B = 26 B`，改绑 `sched_clock×7 + release_thread×1 + trap_init×1` = 9 点；allow-list 去 `release_thread` 注入即 rc=1；旧工具链同源 fresh 对照 `52/52`。
**门控**：`check-patch-tree` linux 段 **0 断言**（另 7 条属并行组件，按组件分流）、`apply_series --component linux` 两次 rc=0 且幂等、`check-knowledge-refs` 记录写入前后均 rc=0。工具链三件 md5 与完成区一致，`clang` mtime 早于派单提交 ⇒ 本轮未重建、未回退。
**k5_futex 判定＝测试侧时序假设错误，非真 bug 被掩盖**：`complete()` 在 child 的 exit trap 内、先于 `do_exit()` 的 `mm_release()`；原注释「父任务再跑时 word 已清」依赖「阻塞任务是本端口唯一切换点」，`sched_clock` 改绑改变唤醒/vruntime 决策后不再成立。断言 want 仍 0、读同一 word、等待有界 1000 次且让出 CPU ⇒ 永不清除仍红。
**Finding（非阻断）**：① `--inject clear-tid-off` 实测红在同 case 前置断言 `f7_clear_tid_ptr`（`red=['f7_clear_tid_ptr']`），`f7_tid_cleared` 的独立 FAIL 路径本轮未单独注入（断言未放宽，机制分析支持不掩盖）；② F7 原 bullet 注释「the word is 0 when the parent runs again」与新等待实现不一致，建议随收尾改；③ 同类直接写 `current->active_mm` 的点仍散在 k4_kthread/k5_clone/k5_futex/k5_syscall，engineer 已披露，建议另立任务。
**判决**：**Accepted**。
