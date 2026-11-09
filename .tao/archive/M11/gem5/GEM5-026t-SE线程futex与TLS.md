# GEM5-026t: gem5 SE 线程/futex 与 TLS

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-025t`（IPC/多进程；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与事实

- 基线 `GEM5-021t` 中 threads/futex 4 例：`futex`(98)（`functional/pthread_mutex_pi`）、`get_robust_list`(100)（`pthread_robust`、`pthread-robust-detach`）、`clone`(220)（`functional/vfork`）
- 大量 `libc-test` 的 `tls_*` 与部分 `pthread_*` 用例在信号/内存面补齐后会转而依赖 **TLS**；static 语料当前由 `rt_sigprocmask`/`mmap` 先挡住，需在本任务验证
- `GEM5-014t` 的 SE 只做了单线程、最小启动 syscall 面；未实现 `clone`/`futex`/per-thread TLS
- **TP 已明确定义**：`spec/DADAO-21 ABI` 规定 `rb3 = rbtp`；TLS 变体/TP 偏置由 `contract-dynlink §2.4/§7` 下放给 musl arch 宏（`TLS_ABOVE_TP`、`TP_OFFSET 0`、`DTP_OFFSET 0`），线程模型已在 musl 实现、QEMU 已验证 ⇒ **无需裁定，按既有定义实现**

## 目标

1. **线程**：`clone`（`CLONE_VM|CLONE_THREAD|CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID` 等按语料）、每线程栈、线程退出与 join；`set_tid_address` 的 clear-tid 语义。
2. **futex**：`FUTEX_WAIT`/`WAKE`/`REQUEUE`/`WAIT_BITSET`（按语料）；与 gem5 事件队列/多 CPU 上下文配合，不得忙等。
3. **robust list**：`get_robust_list`/`set_robust_list`。
4. **TLS（验收切片，不做 TLS 模型）**：事实是 TLS block 分配与 TP 初值都在 musl 用户态完成（`__init_tls`/`__set_thread_area` 写 `rb3`），spec 只定义 `rb3=rbtp`、TLS 变体由 `contract-dynlink §2.4/§7` 下放给 musl arch 宏 ⇒ **gem5 只在 `clone` 的 `CLONE_SETTLS` 路径把 `tls` 参数写入子线程 `rb3`**，不另造 TLS 模型、不分配 TLS block。验收切片：静态单线程 `functional/tls_align`（现基线已 pass）回归；每线程 `functional/tls_init`、`functional/tls_local_exec` 通过；两线程 `__get_tp()` 不同且各自 `TP+TPOFF` 落盘。
5. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,isa.*,...}`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：动态链接（`GEM5-027t`）、IPC/多进程（`GEM5-025t`）、QEMU、测试用例与期望、spec 语义（未明确处先问）。

## 验收标准

1. 基线复跑：threads/futex 桶 blocked 归零；TLS 相关用例（`functional/tls_*`、`tls_local_exec` 等）实测通过或给出真实失败归因；`qemu_only_fail` 0。
2. 抽测：两线程 `pthread_create` + `join`、mutex 争用、`futex` 等待/唤醒、TLS 变量每线程独立、`pthread_exit` 清理。
3. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
4. 反例：把 `clone` 改回未实现 ⇒ 线程用例回 blocked；`cp`+`md5sum -c` 还原重建回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- **规范前提已核实**：`spec/DADAO-21 ABI` 只定义 `rb3=rbtp`；TLS 变体/TP 偏置归 `contract-dynlink §2.4/§7`，musl 端口已定值（`TLS_ABOVE_TP`、`TP_OFFSET 0`、`DTP_OFFSET 0`）并在 QEMU 验证 ⇒ **无需新 spec、无需新裁定**；若实现中发现 spec 未覆盖的新语义，再停下提交。
- gem5 缺 OS 常量层（`OS::TGT_CLONE_*`/`archClone`）：按最小实现手写 clone 分支，或在 DADAO 侧补最小 `linux.hh`，二选一在完成区说明理由。
- 与 `GEM5-024t` 的信号帧、`GEM5-025t` 的多进程共享 `Process` 状态，注意回归。

## 审阅记录

### 第 1 轮 engineer 自审

实现的 spike 结论、7 条自审 finding 与处置如下（全部逐行复核过改动源码）。

**Spike 结论（先做、≤1 h）**：gem5 SE 的多 `ThreadContext` 路径**可行**——
`se.py --num-threads` 创建的上下文可被 `System::Threads::findFree()` 复用，
把第二个上下文挂到**同一** `Process`（`setProcessPtr` + 一次
`assignThreadContext`）后，它与主线程共享页表/fd 表并按 tick 轮转互斥执行；
per-context 的 TLB/ISA/寄存器组互不干扰；`Process::initState()` 的
`initialStateBuilt` 幂等保护让"同一 Process 被多个上下文使用"成立（不需要
再初始化映像/栈）。最小复现：探针 `thr_tls`（两线程各自读 TP、写 TLS、抢
共享计数器）在 spike 阶段即跑通 `create r=0 / worker tls=7 / join r=0
ret=42`。反向证据：未实现 `CLONE_THREAD` 时同一探针 `fatal: syscall 220`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ① 清理调试代码时把 `tc->setReg(rd(8), result)` 一并删掉（syscall 返回值未写回） | ✅已修 | 恢复该行 | 探针 `pt1` 恢复 `create r=0/join r=0 ret=42`；`libc-final` 337 例与基线 0 差异 |
| ② futex 超时事件在 `deschedule` 后又被 `delete`，与 gem5 的 `AutoDelete` 重复释放（宿主 SIGSEGV） | ✅已修 | 去掉手工 `delete`，由队列释放 | 注入前 `pthread_robust`/`sem_init` 由挂死→pass；`futex_probe` 三轮一致 |
| ③ `std::list::remove` 在本 libstdc++ 返回 void，被当 bool 用 | ✅已修 | 先 `find` 再 `remove` | 编译 + `futex_probe` 三轮一致 |
| ④ PI futex 的 `FUTEX_WAIT` 等待者被普通 `FUTEX_WAKE`（musl robust 退出路径发的）漏唤醒 → `pthread_robust` PI 死锁 | ✅已修 | `wakeFutexWaiters` 也唤醒 PI 等待者，由 `acquirePi()` 重读字决定接管或继续等 | `functional/pthread_robust` pass（基线） |
| ⑤ LR/SC 保留标记没有跨 hart 失效，两线程 CAS 丢更新 → `sem_init` 失败、`pthread_*` 计数错 | ✅已修 | `ISA` 保留持有者表 + `inst.cc` 每次 store 清"另一 hart 同址同宽"标记（contract-isa §LR-SC） | `sem_init` pass；探针 `shared=4000`、`counter=9000` 精确 |
| ⑥ `get_robust_list` 把"未注册"报成长度 0 | ✅已修 | 长度恒报 `3*sizeof(long)`（同 Linux），头可为 NULL | `robust_probe`：`len=24`、`set_robust_list` EINVAL/0 |
| ⑦ 每指令一次 `ISA::pendingSignal` 检查的开销 | ⏸延后 | 保留（异步取消需要）；记录 ~1–2% | `--num-threads` 8→64 使近预算基准 ~4% 慢（见遗留） |

### 第 1 轮 reviewer 验收

**过程核验（前后快照）**：主树 `status -uall`=0、`master`/`db432ae2`；任务树恰 12 项改动（`GEM5-026t`，未提交，与 engineer 自述一致）；全仓仅 2 个 worktree、无第三处残留；组件源树 `clean / c99bc64 / base+1`（`rev-list --count base..HEAD`=1）。reviewer 前后 12 文件 md5 逐字相同（`snap-before.md5` vs `snap-after.md5` diff 为空）⇒ 未改 engineer 任何交付物。
**重跑记录（reviewer 亲跑，rc 自取）**：`check-patch-tree`=0（7 组件 305 补丁 OK）；`check-source-state`=0（gem5 `HEAD=c99bc64 count=1 clean=True`）；`check-gem5-decode`=0；`check-inst`=0（44/44）；`check-arch`=0（14/14）；L1 `make check`=0；L2 `make check-modules`=0；`run.sh`=**passes=69 fails=0**（8 门控 + 4 探针×3 轮逐字节一致 + 20 例×2 轮全 pass + 基线断言）。
**独立基线（reviewer 自跑 `run_gem5_se_baseline.py --jobs 24 --gem5-timeout 120`、独立工作目录）**：`qemu_pass=587 gem5_pass=435 blocked=147 qemu_only_fail=0 gem5_only_fail=6`；gap 只有 `time budget=140 / simulator/loader=4 / SysV IPC=3` ⇒ **threads/futex 桶 = 0**；QEMU 侧 589 例与 engineer 基线**逐例 0 差异**，`gem5_only_fail` 集合**完全相同**（popen/spawn/vfork/execle-env/bison/unix-smail）。21 个线程/TLS 用例 gem5 与 qemu **双双 pass**（含 `tls_align`/`tls_init`/`tls_local_exec`）；`raise-race`=blocked（time budget）。与 engineer 的 434/148 差 1 例 = `whetstone`（负载敏感，我方 pass、其侧 blocked），方向是更优、非少过。
**预算项复核（非回归）**：`Queens`=pass 135.4 s、`Quicksort`=pass 128.9 s（`--gem5-timeout 600`）⇒ 单纯超 120 s 预算，非功能回归；与 engineer 披露的「64 上下文 ~4% 慢」一致。
**独立注入（与 engineer 不同的反例）**：在 `wakeFutexWaiters` 首行插入 `return 0`（`git diff` 非空）→ 重建 rc=0 → `futex_probe` rc=125、`functional/pthread_cond`=blocked（non-guest end）⇒ **可达 FAIL**；`cp`+`md5sum -c` 还原（源 md5 `1efa90a5…`、`git diff --quiet`=0）→ 重建 rc=0 → 探针 rc=0 且 `SUMMARY fails=0`。全程未用 `git checkout/restore`。
**约束核验**：① 线程 = 同 `Process` 第二 `ThreadContext`，`initState` 有 `initialStateBuilt` 幂等、`findFree` + contextIds 成员判重、`CLONE_SETTLS`→子 `rb3`、clear-tid/set_tid_address 每线程、非末线程 `SYS_exit` 只退本线程（`group||sig||liveThreadCount<=1` 才退进程）—— 源码逐行 + `thr_tls`/`clone_tls` 探针 + 19 例实测 ✅；② futex 9 类操作俱在 `doFutex`，WAIT 路径不置 `retry`（全文件唯一 `retry=true` 是 023t writev）、`futexParked` 早退不写 rd8、超时走 `AutoDelete` 事件（无忙等/无 trap 重执行）、`WAKE_OP`/`FD`→`ENOSYS` 且 README 已披露 ✅；③ TLS 只做 `rb3` 写入、无 TLS block/模型新增 ✅；④ LR/SC 跨 hart 失效严格按 contract-isa §LR-SC（同址同宽、排除自身），每线程信号 + 指令边界投递带 `!fs` 门控（FS 不受影响），既有行为由 L1/L2/check-inst/check-arch 全 0 与全量基线 0 差异佐证 ✅；⑧ 完成区 7 行 ≤30、全文无运行期路径 ✅。
**Finding（均非阻断）**：F1 `parkOnFutex` 在 `futexDeadline` 报错/已过期分支提前 return，漏 `delete` 的 `FutexWaiter`（宿主小泄漏，语料基本不可达）；F2 `Queens`/`Quicksort` 由 pass→blocked（预算边界，已披露并复核，见上）；F3 `WAIT_BITSET`/`WAKE_BITSET`/`CMP_REQUEUE`/`TRYLOCK_PI` 在 locked musl 中**无调用点** ⇒ 语料不可达、实现未被测到（文档未声称已测）；F4 `FUTEX_REQUEUE` 返回「唤醒+改挂」之和，contract/语料均未钉该值（musl 忽略），与 Linux 是否逐字一致待考；F5 `FUTEX_UNLOCK_PI` 未校验调用者为 owner（Linux 返回 EPERM；musl 仅以 owner 身份调用）；F6 `doCloneThread` 在 tid 写失败时留下 `live` 却永不运行的线程（会让末线程退出走成「线程退出」，语料不可达：musl 恒传合法 tid 指针）；F7 `doExitThread` 对无 `ThreadState` 的上下文静默 return（防御分支，未找到可达路径）。
**判决：Accepted** —— 验收命令块全部由 reviewer 重跑且 rc=0，线程/futex/TLS 三条硬约束守住，反例注入可达 FAIL 并回绿；F1–F7 非阻断，留 architect 终审与后续收口。

## 完成区

**测试结果**：探针 4 组 × 3 轮全 PASS 且三轮逐字节一致（`thr_tls`/`clone_tls`/`futex_probe`/`robust_probe`，各 `SUMMARY fails=0`；TLS 两项 `tp` 不同、`TPOFF` 相同、值各自独立；raw clone `CLONE_SETTLS` 的 `child_tp == tls`）；libc-test static gem5-se 337 例：321 pass / 11 blocked（time budget）/ 4 fail+1 known-fail（即 025t 已登记的 `popen`/`spawn`/`vfork`/`execle-env` 环境缺口 + bison 捕获差异）。threads/futex 桶 20 例：**19 pass**，`regression/raise-race` blocked 归 time budget。全量双引擎基线：qemu_pass 587 / gem5_pass **434**（025t 418）/ blocked **148**（164）/ qemu_only_fail **0** / gem5_only_fail 6（同 025t 同集合）/ **threads/futex 桶 0**。失败原因：`raise-race` 100 次 fork + 1000 次信号超 120 s 预算（能力已有，非能力缺口）。
**修改文件**：`components/gem5/patches/{configs/dadao/se.py,src/arch/dadao/{se_workload.cc,se_workload.hh,process.cc,process.hh,isa.cc,isa.hh,inst.cc}}.patch`（8 份，源 `HEAD=c99bc64`，`make_patch.py` 导出 8 改/89 不变）、`components/gem5/README.md`、`components/gem5/changelog.md`、本任务书、`.tao/knowledge/milestones.md`。
**验收结果**：`run.sh` **passes=69 fails=0**（含 `build-gem5` rc=0、`check-inst` PASS、`check-arch` PASS、`check-gem5-decode` rc=0、`check-patch-tree` 7 组件 305 补丁 OK、`check-source-state` gem5 `HEAD=c99bc64 count=1 clean=True`、L1 rc=0、L2 rc=0）；`run.sh --inject` **passes=20 fails=0**：`clone(CLONE_THREAD)` 改回未实现 ⇒ 探针 `fatal: syscall 220 not implemented`、`functional/pthread_mutex` `blocked@220` ⇒ `cp`+`md5sum -c` 还原（`git diff` 为空）重建 ⇒ 探针回绿。终态 `gem5.opt` md5 `72f139fc8610f1476860c052f708cf06`（源码同一 commit `c99bc64`；gem5 内嵌构建时间，**重建即变**，md5 只作标识；基线跑在改动前一次重建上，`libc-final` 337 例判定与基线 **0 差异**，故基线数有效）。
**新发现/坑**：① 多 `ThreadContext` 复用同一 `Process` 是可行的（见 spike 结论）；② 保留标记必须**跨 hart** 失效，否则 musl `a_cas` 丢更新（contract-isa §LR-SC，sem/引用计数全线受影响）；③ gem5 `AutoDelete` 事件在 `deschedule` 时就被释放，不能再 `delete`；④ musl 取消处理器返回 trampoline 时 SP 可以不是帧基址 ⇒ 内核侧要记帧栈；⑤ `--num-threads` 必须 ≥ 语料最大活动线程数（`pthread_cond-smasher` 11 个，否则 `pthread_create` 静默失败、条件变量超时）；⑥ 64 上下文使近预算单线程基准约慢 4%（`whetstone` 单跑仍 pass，`Queens`/`Quicksort` ~121 s）。
**遗留问题**：① `regression/raise-race` 归 time budget（`TESTCASES-103t` 预算项）；② `Queens`/`Quicksort` 在 `--num-threads 64` 下 ~121 s 略超 120 s 预算（同上，单跑 `Quicksort` 121.3 s、`whetstone` pass）；③ 非线程的 `clone(CLONE_VM)`（pshared）仍按 025t 的 fork 语义复制地址空间；④ `FUTEX_WAKE_OP`/`FUTEX_FD` 未建模（显式 `ENOSYS`）；⑤ `git checkout` 未用于任何还原（全部 `cp`+`md5sum`）。

#### 收尾（architect，2026-11-07 12:40）

- F1（`parkOnFutex` 早退漏 `delete FutexWaiter`，宿主小泄漏）与 F5（`FUTEX_UNLOCK_PI` 未校验 owner）登记 `ISS-345`（P3），随后续 futex 任务修。
- F2：`Queens`/`Quicksort` 在 64 上下文下 121 s 超 120 s 预算，600 s 下 pass（135/129 s），非回归。
- F3/F4/F6/F7：无调用点/返回值语义待核/防御分支，已记录。
- 过程核验：实现曾在主树，已迁移；主树 `git status` 空、HEAD 未变；任务树 12 文件与补丁一致。
- 基线：gem5 pass 418→435（reviewer 复跑）/ blocked 164→147；threads/futex 桶清零；`qemu_only_fail=0`、`gem5_only_fail=6` 同集合。
- 判决 Accepted，状态置 `已验证`。
