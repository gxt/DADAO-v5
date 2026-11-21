# m14-linux-045: 通用 entry/exit 工作循环（`TIF_*` 消费 + syscall enter/exit + irqentry 接线）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-044`（`select GENERIC_IRQ_ENTRY` 必须先编进来）；`m14-linux-027` 拆出本任务
**可并行分片**：否（linux 单写者）
**预估**：4–6 h
**档位**：大改
**状态**：已验证

## 背景（盘点结论，用户 2026-11-20 批准）

五份只读盘点（037/039/040/041/042）**独立指向同一根因**：

- `arch_do_signal_or_restart` 在 `arch/dadao` **全树无调用点**（generic 在 `kernel/entry/common.c:13` 是 `__weak` 空桩、唯一调用点 `:66` 不可达）⇒ **不报链接错，静默不投递**；
- `TIF_SIGPENDING` / `TIF_NEED_RESCHED` / `_TIF_WORK_MASK` **只有定义与注释、无消费者**（`039` 实测）；
- `syscall_enter_from_user_mode` / `syscall_exit_to_user_mode` 在 `arch/dadao` 引用 **0**（`037` #13，10 个工作项全为 0）；
- `syscall_work` 字段是死代码（只有播种清零，`040` ①-22）。

后果：信号、`SIGCHLD`、`exit_group`、抢占、audit/ptrace/seccomp **静默失效**。

## 要做

1. **返回用户态前的工作循环**：在用户态返回路径上按上游形态消费 `_TIF_WORK_MASK`（至少 `TIF_NEED_RESCHED`、`TIF_SIGPENDING`、`TIF_NOTIFY_RESUME`），逐位判、逐位清；
2. **syscall enter/exit**：接上 `syscall_enter_from_user_mode()` / `syscall_exit_to_user_mode()`（或按本端口分发结构给出等价实现，**必须在任务书说明为什么不能直接用通用函数**）；
3. **`arch_do_signal_or_restart`** 接线：本任务只负责**调用到它**；信号的实际投递与帧由 `m14-linux-046` 实现（未实现前 `get_signal()` 返回无信号即返回）；
4. **`irqentry_*`**：`044` 选上 `GENERIC_IRQ_ENTRY` 后，在异步入口接 `irqentry_enter_*`/`irqentry_exit_*` 或 `irq_enter_rcu`/`irq_exit_rcu` + `set_irq_regs`；
5. **`user_mode()`（**已裁定**，用户 2026-11-20，`discussing.md` N30）**：用 **`status` 低 4 位的模式编码**，判据 **`user_mode(regs) = ((regs->status & 0x3) != 0)`**；`trap`/`async_trap` 入口须把**异常前的运行模式**写进该字段（硬件 `excp_prev_run_mode` 可读），`escape` 前不需要恢复它（它描述「进入异常前」，不是当前态）。帧布局见 `m14-linux-046`（2048 B，`rd[0]=status`）。
   - **注意与 spec 的差异**：`spec/DADAO-12 §1` 把 jail(`0b01`) 归「用户态」，该判据把它判为**非**用户态；Linux 下不进 jail ⇒ 当前等价，将来支持 jail 须重裁。
6. **`irqs_disabled()` / `regs_irqs_disabled()`（**已裁定**，用户裁定 B）**：
   - `irqs_disabled()` **保持**「读硬件 `cfx_smon cg8 rc1` + `DADAO_IRQ_SOURCE_BITS` 子集判定」——与 RISC-V `sstatus.SIE` / arm64 `DAIF` 同构，「异常进入后为 true」是特性（让 `might_sleep()` 抓「在中断里睡」）；
   - `regs_irqs_disabled(regs)` **保持恒 false**——硬件把「异常前 mask」存在内部寄存器 `saved_global_cfx_intr_mask`、**不暴露给软件**（`DADAO-12 §3.6`），帧里拿不到；在任务书注明此接口限制，**不要**为此往帧里加位。

## 验收（逐条贴真实 rc）

1. **抢占生效**：`TIF_NEED_RESCHED` 置位后能触发 `schedule()`（给实测：长循环任务被切走）；
2. **`TIF_SIGPENDING` 可达 `get_signal()`**：置位后能走到信号分发点（此时无信号帧，允许「无 handler ⇒ `do_exit`」）；
3. **`in_hardirq()`/`get_irq_regs()` 在中断内正确**（配合 044 已选的 `GENERIC_IRQ_ENTRY`）；
4. **不回归**：k0 130 / k1 112 / k2 170 / k3 263 / k4 五探针 / k5（syscall 104 / clone 97 / futex 174）；
5. **可达 FAIL ≥2 路**：① 去掉 `TIF_NEED_RESCHED` 消费 ⇒ 第 1 条红；② 去掉 `arch_do_signal_or_restart` 调用 ⇒ 第 2 条红（`cp`+md5 还原 + 重建）；
6. `check-patch-tree` linux 段 0 问题；合并态（`Process-07 §5a`）。

## 完成区

**测试结果**：探针 `m45_entry_probe` **51/51**（正例 44 + 反例①4 + 反例②3，rc=0）；回归 **K0 146/146、K1 112/112、K2 170/170、K3 263/263**、**K4 五探针**（cow 86/86、fork 104/104、kthread 112/112、stack 44/44、**switch 76/76**）、**K5**（syscall 104/104、clone 97/97、**futex 174/174**），全 `rc=0`。L1：`check-config-pins` PASS(88)、`check-tasks` rc=0、`check-knowledge-refs` PASS。

**修改文件**：补丁集 **98 份** = master 96 + **2 份新增 arch 补丁**（`arch/dadao/kernel/entry_common.c`、`m45_entry_selftest.c`）；**`components/linux/patches/{kernel,mm}` 相对 master 零改动**（`git diff master -- …` 为空，通用 `kernel/entry/common.c` hunk 已撤）。另改 19 份既有补丁（`Kconfig.debug`/`asm/Kbuild`/`entry.h`/`irqflags.h`/`ptrace.h`/`setup.h`/`trap.h`、`kernel/Makefile`、`async_trap.S`/`irq.c`/`process.c`/`setup.c`/`syscalls.c`/`time.c`/`trap.S`、`k4_switch`/`k5_clone`/`k5_futex`/`k5_syscall` 自测）、`components/linux/series`、新 `tools/linux/m45_entry_probe.py`、18 份 `tools/linux/{check_k0..k3,k*_probe}.py`（CONFIG 符号 pin；另 `k5_futex_probe.py` 的注入判定接受「挂死 180 s 超时」为红，见坑⑤）。

**验收结果**（运行期证据目录内 `run.sh`：`RESULT: PASS`，逐项 rc 见其输出）：
1. **抢占**：E1 `iters=30 b_ran_at=4` —— 另一任务在长循环**中途**拿到 CPU（`TIF_NEED_RESCHED` 由 `exit_to_user_mode_loop` 消费）。
2. **`TIF_SIGPENDING`**：`sig_calls=1`（`arch_do_signal_or_restart()` 带位进入，紧跟 `get_signal()`）；子任务 `status=0xf` = 被 SIGTERM 终止。
3. **`in_hardirq()`/`get_irq_regs()`**：`bad_hardirq=0 bad_regs=0`，投递 `irq_user=15 / irq_kernel=4`。
4. **`user_mode()`**：umon 帧 `exit_user=30 / exit_kernel=0`；异步投递取自用户态 15 次（真）、内核态 4 次（假）。
5. **不回归**：见「测试结果」；`k4_switch` 76/76、`k5_futex` 174/174。
6. **可达 FAIL**：① 去掉出口对 `_TIF_WORK_MASK` 的消费 ⇒ **E1+E2 红**（`rc=115`，内核自报 `e1-other-task-ran-mid-loop`/`e2-died-by-signal`，非挂死）；② 去掉出口 IE 存/恢复 ⇒ **本端口未复现红项**（`rc=0`，如实登记，不声称可红）。两者均 `cp`+md5 还原、重建回绿。
7. **补丁集**：`check-patch-tree` linux 段 **0 问题**（98 份）；`apply_series` **幂等跳过**（已收敛时 rc=0，不重放）。

**新发现/坑**：① 通用 hunk 已撤销：`m14-llvm-007` 修好 `evaluateFixup` 后，同节 weak 调用发重定位，`arch_do_signal_or_restart` 的架构强定义自然生效（探针 E2 在无通用 hunk 的树上 `sig_calls=1`）。② 出口 IE 存/恢复**无法用反例证伪**（去掉后探针仍全绿）⇒ 只按「返回路径保持入口状态」的架构职责描述，不再声称会「永久掩 TIMER」。③ `status` 取「user⇒1/其余⇒0」（裁定公式 + jail 备注的唯一自洽解）。④ 用户态抢占的三件前置（`cfx_hart` user 行向量、`cfx_umon` user 行+全局 mask、异步入口按 `excp_prev_run_mode` 切内核栈）。⑤ **K5 futex 探针对 045 的抢占顺序敏感**：父任务在 clone/wake 返回处可被抢占，故 `k5_futex_selftest.c` 三处适配（子任务首 trap 等注册、唤醒后按「已报告或已退出」判 awake、F1A/F2b 改为等报告/记住被留睡的 slot），语义未放宽（丢唤醒仍红）；`no-recheck` 注入在该行为下变成「waiter 永不返回」，故探针的注入判定把 180 s 超时（`rc=124`）也算红。⑥ 纯用户态空转只能在下一次 trap 被抢占（异步帧跨 `schedule()` 不安全，见 `entry_common.c` 头注释）。

**遗留问题**：① 反例②（IE 存/恢复）不可达，如实登记；② `dadao_trap_exit()` 直接调 `irqentry_exit()` 会在首个用户 trap 自旋（有复现与对照，现按同体展开并注释，交 reviewer 复核）；③ `status` 编码请与 `046` 的 uapi 表述对齐；④ 合并态（`Process-07 §5a`）与 `make check` 全量由主会话合入后跑（本工作树 `make check` 的红仅来自其它组件在飞源树：chipyard/qemu）。**口径注**：验收第 4 条写「k0 130」，实测 **146/146**（与派单口径一致）。

## 审阅链注记（architect 2026-11-21）

- **第 1 轮 reviewer 验收：BLOCKED（需用户裁定）** —— 争议点是 `kernel/entry/common.c` 删空桩这一 hunk 的必要性；**用户裁定 C：修 LLVM**（`m14-llvm-007`），本任务据此返工撤掉该 hunk、恢复上游空桩。该 BLOCKED 记录原文在返工时被一并删除，此处补记以保持审阅链完整。
- **反例②口径**：完成区「去 IE 存/恢复 ⇒ `rc=0`」是**内建注入路径**口径；走全量探针（源码注入后 `--no-inject`）实测 `rc=1`，唯一红项是**静态源码形状断言**，运行期 E1–E4 全绿 ⇒ 行为层面确实不可达。

## 审阅记录

### 第 2 轮 engineer 自审（返工：撤通用 hunk + 四条订正）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 分支基于旧 master，且带通用 `kernel/entry/common.c` hunk | ✅已修 | `git rebase master`（88 提交）；冲突两处按「接受 047 的探针改动 + 保留本任务实现」取 master 侧后重做 `status` 适配；删 `patches/kernel/entry/common.c.patch` 与 series 行，`series` 98 | `git diff master -- patches/{kernel,mm}` 空；`linux: 98 patch(es)` 0 问题 |
| R2 「Clang 把调用绑到本地空桩」措辞已过时（llvm-007 已修） | ✅已修 | 通用 hunk 连同该措辞一并撤销；`entry_common.c` 头注释只保留上游 `__weak` 语义描述 | 弱桩在原位（`kernel/entry/common.c:13`），探针 E2 `sig_calls=1` |
| R3 「去掉 IE 存/恢复 ⇒ TIMER 永久被掩」未复现 | ✅已修 | 注释改为「返回路径保持入口 IE 状态」的职责描述并注明「未观察到破坏」；完成区如实登记 | 反例② `rc=0`、无红项（`cp`+md5 还原） |
| R4 完成区把反例写成「E1 红 / E2 红」而未说明表现 | ✅已修 | 反例①改为真实结果：`rc=115`、内核自报 `e1-*`/`e2-*`（非挂死）；反例②改为「未复现」 | 注入日志 `inject no-work-loop: rc=115 red=['e1-other-task-ran-mid-loop','e2-died-by-signal']` |
| R5 `apply_series` 说成「从 base 重放」 | ✅已修 | 改为「幂等跳过（已收敛即 rc=0）」；证据脚本第 4 项同步 | `apply-series: linux already applied (base+1, matches patches); skipped` |
| R6 证据脚本的改动集判据（提交后会变空） | ✅已修 | 改「未提交 ∪ `${BASE}..HEAD`」求并、空集按 0 计；新增 `patches/{kernel,mm}` 零改动检查（master 侧 + 未提交两侧求并） | 脚本第 5/6 项逐项打印 rc；`RESULT: PASS` |
| R7 045 的抢占使 `k5_futex` 探针的时序假设失效（子任务先于注册 trapping、唤醒后 waiter 已退出、F1A/F2b 顺序） | ✅已修 | 三处适配见「新发现/坑」⑤；判据改为「已报告或已退出即视为已唤醒」，丢唤醒仍红 | `k5_futex_probe: 174/174 passed` |
| R8 `dadao_trap_exit()` 直接调 `irqentry_exit()` 自旋（上一轮 F5 遗留） | ⏸延后（留审查点） | 保持与其用户态分支逐步相同的展开体 + 注释 | 展开体：探针 51/51；`irqentry_exit()`：镜像在首个用户 trap 停住 |

**判决**：R1–R7 已修并复验；R8 为已知未解现象（有对照、已绕行），不阻断验收，交 reviewer 复核。

### 第 2 轮 reviewer 验收

**判决：Accepted**（附 2 条 finding，见末）

**重跑（全部自跑、输出实测）**
- 证据脚本（运行期证据目录内 `run.sh`）：`RESULT: PASS` —— `judge-selfcheck rc=0`、`probe-all-cases+injections rc=0`、`m45_entry_probe: 51/51`、`patch-tree-linux-problems 0`、`check-patch-tree: linux: 98 patch(es)`、`series-entry-count 98/98`、`apply-series rc=0`（`already applied (base+1, matches patches); skipped`）、`changed-files 42`、`changed-outside-expected-areas 0`、`patches-kernel-mm-changed 0`。
- 回归（全 `rc=0`）：`check-linux-k0 146/146`、`k1 112/112`、`k2 170/170`、`k3 263/263`；K4 `cow 86/86`、`fork 104/104`、`kthread 112/112`、`stack 44/44`、`switch 76/76`（默认含反例；`--no-inject` 另测 `52/52`）；K5 `syscall 104/104`、`clone 97/97`、`futex 174/174`（默认含反例）。

**通用 hunk 撤销核验（逐条）**
- `git diff master -- components/linux/patches/{kernel,mm}` **为空**（rc=0 无输出）；`patches/kernel/` 只剩既有 `workqueue.c.patch`、`patches/kernel/entry/` 已不存在；`series` **98 行**且不含 `kernel/entry/common.c`；`fs/init/usr` 对 master 亦为空。
- 空桩**逐字节等于上游**：`git show <linux base>:kernel/entry/common.c` 与工作树文件 `diff` **rc=0**、md5 同为 `6bede7468eb6c63f9553187a43c6a0f2`；`grep -c "__weak arch_do_signal_or_restart"` = **1**；arch 强定义仍在（`entry_common.c.patch` 在 series，E2 `sig_calls=1`）。
- rebase 未吃 047：`k4_switch_selftest.c.patch` 对 master **只含 045 的两处 `status` 期望增量**，`mmgrab_lazy_tlb` 仍在（4 处）；`k5_futex_selftest.c.patch` 对 master 的 67 行插入均标注 `m14-linux-045`。

**两路反例（自写 needle，非复用探针内建；均 `cp`+md5 还原并回绿）**
- ① 去 `_TIF_WORK_MASK` 消费（改通用文件循环条件）⇒ `rc=1 39/44`，红项 `e1-other-task-ran-mid-loop`、`e2-died-by-signal`、`D want=0 got=115`，与完成区 `rc=115` 一致 → 还原 `44/44 rc=0`。
- ② 去两处出口 IE 存/恢复 ⇒ `rc=1 43/44`，**唯一红项是静态源码形状断言**（`出口前后保存/恢复本端口的 IE 字`），运行期 E1–E4 全绿 ⇒ **行为层面确实不可达**，与「登记不可达、不声称可红」一致 → 还原 `44/44 rc=0`。

**k5_futex 三处时序适配：未放宽丢唤醒（代码级 + 实测）**
- 代码：① 子任务首 trap `schedule()` **有界 2000 次**，仍无 slot 即 `k5f_fail(UNREGISTERED)`（红）；② `f1_waiter_awake` 放宽为 `!k5f_sleeping(pid) || reported`，但紧跟 `f1_waiter_script == WAIT_F1`、`f1_waiter_word == 1`、`f1_wake_count == 1` 三条严判，`k5f_sleeping` 把已死任务算「未睡」只让判据更严（`f2_left_asleep` 仍要求睡）；③ F1A 改 `wait_for_completion(&waiter->report)`（等不到即超时）、F2b 记住被留睡 slot 并断言 `left != NULL`。
- 实测（我这轮 `k5_futex` 默认含反例）：`lost-wake ⇒ rc=121 red=['f1_waiter_awake']`（**正是被放宽的那条仍判红**）、`no-recheck ⇒ rc=124`（按新规则计红）、`clear-tid-off/no-bitset/no-op-add/no-requeue/sc-crossing` 各自红在本用例 → `174/174 rc=0`。

**门控**：`check-patch-tree` linux 段 0 问题（98 份）、`apply_series` 幂等跳过 `rc=0`、`check-knowledge-refs` 写后 `rc=0`。

**finding（不阻断，交 architect）**：F-a 返工提交把 `### 第 1 轮 engineer 自审` 与上一轮 reviewer 的 **BLOCKED 判决**一并删掉，审阅轮次链断裂（该记录未入过 git、已不可从历史恢复）⇒ 请补一行「第 1 轮 reviewer 验收：BLOCKED（需用户裁定）→ 用户裁定 C（修 LLVM）」；F-b 完成区「反例② ⇒ `rc=0`」是**内建注入路径**口径（注入期间不重跑静态判据），全量探针（源码注入后 `--no-inject`）实为 `rc=1`（仅静态形状断言红）⇒ 建议写明口径。

**约束核验**：未改代码（源树两文件 md5 与注入前一致、`git status -uall` 仅本任务书、无注入备份残留）；未跑 `make install-host`（用现成安装根）；本记录无运行期具体路径；未提交 git。
