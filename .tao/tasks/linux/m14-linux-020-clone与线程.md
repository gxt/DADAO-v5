# m14-linux-020: 内核线程（kernel_thread / kthreadd / kthread_create）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（`copy_process`/`copy_thread` 共享路径）、`m14-linux-017`（上下文切换/调度）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/process.c`/`copy_process` 钩子）
**并行组**：与 K4 其余任务**串行**（同组件同写者）
**预估**：2–3 h（收窄为内核线程；复用 016 的 `copy_process`，代码量小）
**档位**：中改（`copy_process` 的 `kernel_thread` 钩子 + `kthreadd` 接线 + 探针；复核 ≥3 路注入）
**状态**：待验收

## 背景

K4 分界已定（**用户 2026-11-17 选 A**）：**K4 = 内核侧进程/线程原语**，**K5 = 用户态**。本任务由原「clone/线程」**收窄为内核线程**：`kernel_thread` / `kthreadd` / `kthread_create` / `kthread_run` 最小面，为 K4 其余任务（COW/栈的验证载体、后续驱动/工作队列）提供内核线程基础设施。**用户态 `clone` 的 `CLONE_VM`/`CLONE_SETTLS`/`CLONE_THREAD` 语义、TLS（`rb3=rbtp`）用户面、`futex`、pthread 类测试全部归 K5**（判据交接见下「K5 交接判据」段）。

DADAO 特有事实（`contract-syscall §10/§11`，本任务**内核线程不消费**，仅作 K5 交接边界）：
- `rb3` = `rbtp`（thread pointer），保留不分配；内核线程**无用户态、无 TLS**，不设 `rb3`。
- `kernel_thread` 子任务**无用户 `mm`（`mm == NULL`）**：不 `dup_mm`，与 `016` 的 `fork`（有 `mm`）对照。
- `copy_process` 通用逻辑已支持 `CLONE_FS|CLONE_FILES` 等标志；本任务只补 `arch/dadao` 侧 `kernel_thread` 钩子，**不新增用户 clone 语义**。

## 目标

1. **`kernel_thread`（arch 钩子）**：`kernel_thread(fn, arg, flags)` 建内核线程——`copy_thread` 设子任务入口为 `fn`（`arg` 为参数）、子任务 `mm == NULL`（不 `dup_mm`）、默认 `CLONE_FS | CLONE_FILES`（共享父资源表）、子入口 `rd8 = 0`。
2. **`kthreadd`（`rest_init` 路径）**：内核在 `rest_init()` 创建 **pid 2 的 `kthreadd`**（内核线程守护者），供 `kthread_create` 排队。
3. **`kthread_create` / `kthread_run` 最小面**：能创建内核线程、执行 `fn`、`kthread_should_stop()`/`kthread_stop()` 退出（任务从运行队列消失）。
4. **复用 016 的 `copy_process`/`copy_thread` 共享路径**：`fork` 与 `kernel_thread` 走同一 `copy_process`，仅 `copy_thread` 的入口/`mm` 处理分支不同。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_kthread_probe.py` rc=0，逐 case 打印；期望值现场派生（`mm`/`mm_users` 布局 ← 内核源现场符号、`CLONE_*` 位 ← `include/uapi/linux/sched.h` 锁定源）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `K1 kthreadd 创建`：`rest_init()` 后 `kthreadd` 存在（pid == 2）、是内核线程（`mm == NULL`）。
   - `K2 kthread_create/kthread_run 起停`：创建内核线程 → `fn` 执行（计数器推进）→ `kthread_stop()` 后退出（`kthread_should_stop()` 返回真、任务从队列消失、`fn` 不再推进）。
   - `K3 kernel_thread 的 CLONE_FS|CLONE_FILES`：`kernel_thread` 子任务与父共享 `fs`/`files`（现场断言指针相同）；`mm == NULL`（**不** `dup_mm`，与 016 的 `fork` 对照——`fork` 子 `mm` 非空、asid 不同）。
   - `K4 无用户 clone 语义`：探针**负例断言**——本任务 `copy_thread` **不实现** `CLONE_SETTLS`（无 TLS 参数分支），`kernel_thread` 不设 `rb3`；断言「用户 clone 的 `CLONE_VM`/`CLONE_THREAD`/双返回不在 K4 实现」（结构性：`copy_thread` 签名无 `tls` 参数、无 `ret_from_kernel_thread` 的用户态分支）。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `rest_init` 不建 `kthreadd` ⇒ `K1` 红；② `kernel_thread` 错误地 `dup_mm`（`mm` 非空）⇒ `K3` 红；③ `kthread_stop` 不置停止位（`kthread_should_stop` 恒假）⇒ `K2` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）、`k4_switch_probe.py`（017）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## K5 交接判据（本任务不实现；K5 立册时逐条落验收）

- `clone` 的 `CLONE_VM` 共享地址空间（子 `mm` == 父 `mm`、`mm_users++`、asid 相同）。
- `clone` 的 `CLONE_SETTLS`（子线程 `rb3/rbtp` = `tls` 参数、父不变）。
- `clone` 子入口 `rd8 = 0`、父返回子 tid；**「双返回」归 musl wrapper**，内核只保证这两点（`contract-syscall §10`）。
- `CLONE_THREAD`（同线程组）、`CLONE_FS`/`CLONE_FILES`/`CLONE_SIGHAND` 的**用户可见共享语义**（内核侧 `kernel_thread` 的 `CLONE_FS|CLONE_FILES` 已在本任务 `K3` 覆盖，用户态可见性归 K5）。
- TLS 用户面：`rb3=rbtp` 入口保存/返回恢复、`execve` 清 0 实现点（musl 校准）、`initial-exec`/`local-exec` 分工（`contract-syscall §10`）。
- `futex`（`FUTEX_WAIT` 检查→睡眠原子、`FUTEX_WAKE` 不丢唤醒）、用户 `lr`/`sc` 保留标记跨 syscall 即清（`contract-syscall §11`）。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-020/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{process.c,Makefile}.patch`（`kernel_thread` 钩子）、`components/linux/patches/init/{main.c?}.patch`（`rest_init` 的 `kthreadd`，若需 arch 钩子）、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k4_kthread_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k4_kthread_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §10/§11`（TLS/原子性，作 K5 交接边界）+ `copy_process` 通用逻辑为准；`kernel_thread` 只补 arch 钩子，不重写 `copy_process`/`kthread` 通用代码；**不得**在本任务实现用户 clone 语义。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~（待裁定 2）clone/线程是否 K4~~ **已裁定（用户 2026-11-17 选 A）**：K4 = 内核侧进程/线程原语（本任务收窄为内核线程）；用户态 `clone`/TLS/`futex`/pthread 归 K5。原 `C1–C4` 判据整体移入「K5 交接判据」段。
2. ~~（待裁定 4）~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环并入 `016`/`017`，本任务内核线程不依赖用户态。

## 审阅记录

### 第 1 轮 engineer 自审

- 目标 1–3 由探针 K1–K3 逐条覆盖；目标 4（复用 016 的 `copy_process`/`copy_thread`）由 K3 的 fork 对照（同一父任务、私有 mm、不同 asid）现场证明：`kernel_thread` 只多了一段「丢弃 `copy_mm()` 为 CLONE_VM 取的那份引用」。
- K4（负例）判为**结构性**：`copy_thread()` 无 `tls` 参数、arch 不出现 `CLONE_SETTLS`/`CLONE_THREAD`/`ret_from_kernel_thread`/`futex`、kernel_thread 分支不写 `rd8`、`syscalls.c` 无 clone 实现——用户 clone/TLS/futex 全归 K5。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 挂在 `kthreadd_done` 之后跑：带 mm 的 `kernel_thread()` 返回 `-EINVAL` | ✅已修 | 钩子移到 `kernel_init_freeable()` 之后 | 移动后 K3 全绿（探针 110/110）；原因见完成区「新发现」② |
| F2 K1 读 `comm` 得 `swapper/0`（daemon 尚未被调度） | ✅已修 | 名字断言移到 K2（`k2-kthreadd-ran`），K1 只打印 `comm_before_run` | `K4 kthread k2: kthreadd_comm=kthreadd` |
| F3 K2 用 `schedule()` 轮转不成立（无 `sched_clock`） | ✅已修 | 三次交接改 `wait_for_completion`；工作阶段改有界循环 | K2 断言全绿；注入③有界变红（4 条） |
| F4 fork 对照子帧 = `kernel_init` 自己（中途被调度会重入 init） | ✅已修 | clone 前把父帧 `rd16` 钉成 `k4kt_park` | 110/110；子任务即便被调度也只 park |
| F5 探针「`ticks_now` 自比」恒真；K3 mutation 断言名不存在 | ✅已修 | 与 stop 行的 `ticks` 对比；mutation 改 rb3/rd8 | `--selfcheck` 三组各 1–2 条被捕获 |
| F6 新 Kconfig 符号未进其它 14 个切片脚本 | ✅已修 | 各 `CONFIG_PINS` 补 `..._KTHREAD_SELFTEST=n` | `check-config-pins` PASS（17 符号 × 45 镜像） |
| F7 开发期在 `kernel/fork.c` 留诊断打点 | ✅已修 | 全部删除 | 任务树 24 项改动均为交付文件 |
| F8 越界：`setup.c`/`setup.h` 与 14 个钉子脚本不在「预计改动文件」内 | ✅已披露 | 完成区「修改文件」逐项列出（前者是「镜像不得在边界收尾」的必要一行，后者是 ISS-470 门控要求） | 见完成区 |

### 第 1 轮 reviewer 验收

- **重跑（运行期证据目录内的 `run.sh`，全量）**：**39/41**——40 项绿；2 项红全在 `check-patch-tree`/`--source-state`，根因是 **共享 chipyard 源树脏**（4 个 scala 文件，mtime 16:33/16:43，晚于 engineer 16:30 的绿跑；`linux: OK HEAD=654a0a05d clean=True`、`linux: 87 patch(es)`）⇒ 判为并发/环境干扰、非本任务缺陷；该门控**重跑 3 次**结论一致（已记次）。
- **探针真跑**：`python3 tools/linux/k4_kthread_probe.py` → **110/110**（rc=0）；`--selfcheck` K1/K2/K3 各 2/2/1 条被翻转捕获（有可达 FAIL）。
- **三条关键断言（我自己的控制台日志，不采信完成区）**：K1 `present=1 pid=2 mm=0x0 kthread=1 fs=0x200005a2b28 files=0x200005a2650`（真表非空）；K2 两路 `stop_ret=0x4b54 saw_stop=1 state=128(TASK_DEAD) on_rq=0 frozen=1`；K3 `fs_same=1 files_same=1`（与父指针相同且非 0）、`kt_mm=0x0`、父有 mm 时 `mm_users 1→1`、fork `fork_mm_diff=1 asid 1≠2`。
- **独立注入 4 路（全不在 engineer 的 3 路内；每路 cp+md5 还原 md5 相等 → 重建回绿 110/110 → 源树 clean）**：① 不 `mmput()` ⇒ `k3-mm-reference-balanced` want=1 **got=2** 红；② `kthreadd` 不 `set_task_comm` ⇒ `kthreadd_comm` want=kthreadd **got=swapper/0** 红（同证硬事实证硬事实③）；③ `dadao_k4_boundary` 不 `return` ⇒ K1/K2/K3 行全缺红；④ 把探针挪回 `kernel_init_freeable()` **之前** ⇒ 内核自报 `K4 kthread FAIL: kernel_thread-mm=0x16`（=−EINVAL）红（证硬事实②）。
- **硬事实①（独立核，代码链完整）**：本镜像从不调 `dadao_clockevent_start()`（只有 017 自检调）⇒ 定时器不 arm、`dadao_tick_on=0` ⇒ `sched_tick()` 不跑；`update_rq_clock()` 读 `sched_clock_cpu()`，arch 无 `sched_clock` 实现（K5/021），generic 源是 jiffy 而 `jiffies_64` 只在 `dadao_timer_interrupt()` 里加 ⇒ `rq->clock`/`vruntime` 不前进 ⇒ `pick_next_task_fair`→`pick_next_entity(protect=true)`→`pick_eevdf` 的 `protect_slice(curr)` 恒真 ⇒ **运行态 `schedule()` 永远重选自己** ⇒ 内核线程交接只能阻塞等待。**成立**。
- **硬事实②（独立实测）**：注入④复现 `kernel_thread` 带 mm 时返回 **22**；链路逐行核过：`need_futex_hash_allocate_default = (clone_flags & CLONE_VM)` → `futex_hashmask==0` → `clamp(...,16,1)` → `futex_hash_allocate(1,…)` 的 `hash_slots==1` 分支返回 `-EINVAL`，而 `futex_init()` 是 `core_initcall`、在 `kernel_init_freeable()` 内才跑。**成立**。
- **硬事实③（独立核）**：`kernel/kthread.c` 的 `set_task_comm()` 在 `kthreadd()` 自己的 prologue，而 `complete(&kthreadd_done)` 在 `rest_init()` 的 `schedule_preempt_disabled()` **之前**（等到完成 ≠ daemon 跑过）；注入②实测 comm 停在继承来的 `swapper/0` ⇒「真跑过」只能由一次成功的 `kthread_create()` 证明。**成立**。
- **不回归（我的重跑）**：k0 **130/130**、k1 112/112、k2 170/170、k3 263/263、`k4_fork` 104/104、`k4_cow` 86/86、`k4_stack` 44/44、`k4_switch --no-inject` 52/52、`check-config-pins` PASS（15 切片脚本 × 17 符号 × 45 镜像）。
- **合并态（`Process-07 §5a`）**：`git merge --no-commit master`（master 仅前进 .tao 文档）下探针 **110/110**、pins PASS、patch-tree `linux: 87 patch(es)`；`git merge --abort` 后 HEAD 与工作树同合并前逐字一致（前后 `git status -uall` 均空，无提交）。
- **边界**：注释剥离后 arch/dadao 内 `CLONE_SETTLS/CLONE_THREAD/ret_from_kernel_thread/futex/CLONE_VM/CLONE_SIGHAND` 计数**全 0**；`copy_thread` 签名无 `tls` 参数；本 commit 只加 kthread 的 mm 分支，**未实现任何用户面 clone/TLS/futex 语义**（归 K5）。
- **越界披露核**：`setup.c` 仅 +9 行（KTHREAD 镜像在 K4 边界 `return`、不收尾——必要且最小）、`setup.h` 仅 +3 行声明；15 个切片脚本各 +3 行钉子（ISS-470）；无 `spec/`、`.tao/contracts/`、`tests/`、`components/qemu/`、根 `Makefile` 改动。
- **判决：Accepted**（2 条文档级 finding，不阻断，收尾时改）。
  - F-a：`Kconfig.debug` 的 help 与自检文件头仍写「right after `wait_for_completion(&kthreadd_done)`」，实际调用点在 `kernel_init_freeable()` 之后（与本任务 F1 相矛盾）——改文案即可。
  - F-b：完成区「合并态 master 仅前进两份 `.tao/knowledge`」已过时（现 4 个 commit，含 `.tao/tasks`）；且 `check-patch-tree` 需在共享 chipyard 源树干净后复跑一次确认绿。

### 第 1 轮 engineer 返工（文档级；只改注释，不动代码/判据/注入）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-a `Kconfig.debug` help 与自检文件头仍写「right after `wait_for_completion(&kthreadd_done)`」 | ✅已修 | 两处改为「after `kernel_init_freeable()`」，并各留一句「为什么不能更早」：`kernel_thread()` 强制 CLONE_VM ⇒ 带 mm 的 clone 走 `futex_hash_allocate_default()`，`futex_hashmask` 只在 `futex_init()`（core_initcall，位于 `kernel_init_freeable()` 内）之后才非 0，之前桶数被夹成 1 ⇒ `-EINVAL` | 重建后探针 **110/110**（rc=0）；`make_patch` 只重写这两份补丁（其余 85 份逐字节未变） |
| F-b 完成区「合并态 master 仅前进两份 `.tao/knowledge`」过时；`check-patch-tree` 需在共享 chipyard 源树干净时复跑 | ✅已修 | 「验收结果」一句改为实际情形（其后主控又合入 `.tao/tasks` 等提交）并写明 chipyard 前提与「本部件独立成立」的证据 | `--source-state`：`linux: OK HEAD=651819b4 count=1 clean=True`；全量 5 项红全在 chipyard ⑥/⑦（4 个 scala 文件，并发会话所改） |

## 完成区

**测试结果**：`tools/linux/k4_kthread_probe.py` **110/110** 通过（S/K1/K2/K3 四组，K4 为结构性负例）；`--selfcheck` 三组均有可达 FAIL（各 1–2 条被翻转捕获）；**3 路注入**均「红 → `cp`+md5 还原 → 重建 → 回绿」：`no-kthreadd`（K1 red=3，镜像在探针前就以 guest 段 `0xe1` 终止）、`kt-keeps-mm`（K3 red=4）、`no-stop-bit`（K2 red=4）。失败原因：无。
**修改文件**：`components/linux/patches/arch/dadao/kernel/process.c.patch`（`kernel_thread` 钩子：丢弃 CLONE_VM 取到的父 mm 引用）、`.../kernel/k4_kthread_selftest.c.patch`（新）、`.../Kconfig.debug.patch`、`.../kernel/Makefile.patch`、`.../kernel/setup.c.patch`（越界披露：边界在本镜像不止步）、`.../include/asm/setup.h.patch`（越界披露：声明）、`components/linux/patches/init/main.c.patch`、`components/linux/series`、`components/linux/changelog.md`、`tools/linux/k4_kthread_probe.py`（新）、`tools/linux/{check_k0,check_k1,check_k2,check_k3,k1_pt_probe,k2_irq_probe,k2_time_probe,k2_trap_probe,k3_page_probe,k3_pt_probe,k4_cow_probe,k4_fork_probe,k4_stack_probe,k4_switch_probe}.py`（越界披露：各补一条配置钉子，ISS-470）。
**验收结果**：运行期证据目录内的 `run.sh` 逐项打印「检查名 + want/got/rc」：41/41 通过；k0 **130/130**、k1、k2、k3、k4_fork、k4_cow、k4_stack、k4_switch（52/52）、`check-config-pins`、`--source-state`（`linux: OK clean=True`）全绿；门控在合并态（`git merge master` 后）跑完——当时 master 只前进两份 `.tao/knowledge`，其后主控又合入 `.tao/tasks` 等提交（对门控无影响）。`check-patch-tree` 全量须在**共享 chipyard 源树干净**时复跑：本轮该源树被并发会话改脏（4 个 scala 文件，mtime 16:34/16:43，HEAD 未变），全量 5 项红全在 chipyard 的 ⑥/⑦，本部件独立成立（`linux: 87 patch(es)`，无任何 linux 断言失败）。
**新发现/坑**：① **无 `sched_clock` 时运行态任务永不换人**——`pick_task_fair()` 以 `protect = true` 调 `pick_eevdf()`，EEVDF 的 `protect_slice()` 依赖时钟推进，时钟不前进则 `schedule()` 永远重选自己（017 的 S2「交替」实为各自跑完再 park）。故内核线程的每次交接必须是**阻塞等待**，工作阶段用**有界循环**（«停止位没来» 变成判据而非挂死）。② **探针必须在 `kernel_init_freeable()` 之后跑**：`need_futex_hash_allocate_default()` 只判 `CLONE_VM`，带 mm 的 `kernel_thread()` 会走 `futex_hash_allocate_default()`，而 `futex_hashmask` 由 core_initcall 的 `futex_init()` 决定；之前 `buckets` 被夹成 1 ⇒ 返回 `-EINVAL`（实测 `kernel_thread` 返回 `-22`）。③ `kthreadd` 的 comm 只在它被调度后写（prologue 的 `set_task_comm()`），「daemon 真跑过」的证据是**一次成功的 `kthread_create()`**。
**遗留问题**：无。用户态 `clone`/TLS/`futex` 按任务书归 K5；`--skip-build` 与 016 同形（要求构建树里已有镜像），不影响判据。
