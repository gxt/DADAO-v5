# m14-linux-025: futex 与原子性（FUTEX_WAIT 原子 / FUTEX_WAKE 不丢唤醒 / 用户 lr+sc）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-024`（clone/线程，futex 需多线程）、`m14-linux-023`（syscall 闭环）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/syscalls.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：3–4 h（futex 是通用机制，arch 侧只补原子读/清保留标记口径）
**档位**：中改（`futex` 接线 + 原子性断言；复核 ≥3 路注入）
**状态**：待验收

## 背景

`024` 有了线程后，`futex` 成为 pthread 互斥/条件变量的地基。本任务补 `futex` 与用户原子性（`contract-syscall §11`）。

DADAO 特有事实（`contract-syscall §11`，**不得偏离**）：
- `lr`/`sc` 的保留标记、成功/失败、宽度、对齐与清标记条件**一律**按 `SimRISC-12 §1`；`sc` 可能**偶发失败**（spurious），软件须循环重试；**异常或中断进入清除保留标记** ⇒ `lr…sc` **不能跨任何 syscall/异常**（`§11`）。
- `futex`：`FUTEX_WAIT` 的「检查用户字 → 睡眠」必须原子——内核在持锁下用 `lr` 语义复核用户字（或等价单核原子读）后再入队；`FUTEX_WAKE` 不得丢唤醒；`futex` 不改变用户 `lr`/`sc` 语义（`§11`）。
- 单核下**不得**把「单核」当免内存序假设，生成的序须与多核一致（`§11`）。
- 用户 `atomic_*`/`cmpxchg` 由 `lr`/`sc` 循环实现（宽度选 `.b`/`.w`/`.t`/`.o`）。

## 目标

1. **`futex` syscall 接线**：`FUTEX_WAIT`/`FUTEX_WAKE`（+ `FUTEX_WAIT_BITSET`/`WAKE_BITSET` 最小面）走通用 `kernel/futex.c`；`arch/dadao` 侧只补「原子读用户字」（`futex_atomic_cmpxchg_inatomic`/等价，用 `lr` 语义）。
2. **用户 `lr`/`sc` 清标记**：确认异常/中断/syscall 进入即清保留标记（`SimRISC-12 §1`），用户 `cmpxchg` 循环正确重试（不跨 syscall）。
3. **探针** `tools/linux/k5_futex_probe.py` + `CONFIG_DADAO_K5_FUTEX_SELFTEST`：两线程 `FUTEX_WAIT`/`WAKE` 往返 + 用户 `cmpxchg` 竞争。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_futex_probe.py` rc=0，逐 case 打印；期望值现场派生（`lr/sc` 语义 ← `SimRISC-12 §1`、futex 口径 ← `contract-syscall §11`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `F1 FUTEX_WAIT 原子`：线程 A 检查用户字 == 期望后 `FUTEX_WAIT` 入队；线程 B 改字 + `FUTEX_WAKE` ⇒ A 醒来（**不丢唤醒**、检查→睡眠原子）。
   - `F2 FUTEX_WAKE 计数`：多个 waiter 时 `WAKE(n)` 唤醒恰 n 个（现场计数）。
   - `F3 用户 lr/sc 竞争`：两线程 `cmpxchg` 同一地址，恰一者成功（`lr`/`sc` 语义正确、spurious 重试）。
   - `F4 lr/sc 不跨 syscall`：`lr` 后 syscall 再 `sc` ⇒ `sc` 失败（保留标记被清）。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `FUTEX_WAIT` 不复核用户字（非原子）⇒ `F1` 红；② `FUTEX_WAKE` 漏唤醒 ⇒ `F1`/`F2` 红；③ `lr/sc` 保留标记不跨 syscall 清（跨 syscall 仍成功）⇒ `F4` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_clone_probe.py`（024）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-025/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{syscalls.c,futex?}.patch`、`components/linux/patches/arch/dadao/include/asm/{futex.h,cmpxchg.h}.patch`、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k5_futex_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k5_futex_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §11` + `SimRISC-12 §1`（原子指令）为准；`futex` 通用逻辑（`kernel/futex.c`）不重写，只补 arch 原子读；**不得**因单核放宽内存序。
5. 不定义 TLB/cache/多 hart 保留标记仲裁（`§11`；多 hart 另立契约）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. 无新裁定项；`futex` 与 `lr/sc` 口径已由 `contract-syscall §11` 冻结，本任务只做接线与断言。
2. **`CLONE_CHILD_CLEARTID` 的「唤醒」与「shared futex 在哪些页上成立」（第 2 轮复核后重测，2026-11-20）**：
   - **已测（清半边可用）**：正确常量 `0x00200000` 下子线程退出**确实清** tid 字（`clear_child_tid` = 程序给的字、`mm_users = 2`、父方读回 `0x0`）⇒ F7 常驻用例。
   - **CLEARTID 的唤醒**是 `mm_release()` → `do_futex(FUTEX_WAKE, 1, NULL, NULL, 0, 0)`（flags = 0 ⇒ **shared** 键）；该键在本端口能否成立取决于页，见下。
   - **实测（临时镜像，控制台原文见「完成区 → 返工 2」）**：
     ① 读填充（`fill-zero`）的匿名页：`get_futex_key()` 返回 0（`folio->mapping` 非 0），shared `FUTEX_WAIT` = **-11**（EAGAIN，键成立）；
     ② 写替换（NWPERM `replace-zero`）的匿名页：`folio->mapping == NULL` ⇒ `get_futex_key()` **-14**（EFAULT）；
     ③ **真实文件后备页**（ramfs `filp_open(O_CREAT)` + `kernel_write` + `mmap(MAP_SHARED)`，故障路径 `fill-file`）：shared `WAKE` 即**停在 `get_user_pages_fast` 不返回**（WAIT 未及执行；先发 WAKE 正是为了把失败点与 wait 逻辑分开）⇒ 本端口**不可测**，既不是 -14 也不是 -11。
   - **根因**：故障通道的页一律由 `alloc_page` 装（`dadao_pf_alloc_page()` **不做 rmap**，共享零页同样），`folio->mapping` 不是通道维护的不变量 ⇒ ①/② 的差异来自页的来源/历史（实测非 0 vs NULL），**不能按「匿名/文件」划界**；文件映射在本端口由通道**从文件拷入私有页**（`fill-file`），不是页缓存页，GUP 在该 VMA 上不返回。
   - **影响面**：musl 的 `pthread_join` 主等待是 private（`detach_state`），**不受影响**；`__tl_lock()/__tl_sync()` 对 `__thread_list_lock` 的 shared 等待**只在争用**时才发 futex，且 `__wait/__wake` 忽略返回值、`__timedwait_cp` 把非 EINTR/ETIMEDOUT 归 0 ⇒ 只会退化为**自旋**，不阻断 025、不影响 029 的 create/join 代表例；`PTHREAD_PROCESS_SHARED` 同步对象与真实文件页的 shared futex 仍**未验证**。
   - **选项**：A 给通道页补 rmap（`anon_vma` + `page_add_new_anon_rmap`）并让文件映射走页缓存（`filemap_fault`）；B 只补 rmap（文件页的 shared 键仍不可用）；C 登记为已知限制。
   - **建议**：A，**单独立任务**（改 `mm/`，不属本任务）；对齐用户 2026-11-20 规则「内核实现优先走通用标准流程」——本端口的**自定义缺页通道**正是要回归通用路径的那类旁路，任务书须登记「为什么不能走通用」。
   - **本任务处置**：F7 只断言「清」半边；shared 面不入绿用例，登记为遗留 + 立任务候选。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查了三个新增/修改面：内核探针（交接协议、断言、失败路径）、用户桩（寄存器/地址/分支）、门控（派生值、注入点、自检）。逐条发现与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| A1 `f2b_awake` 把已退出的前两个 waiter 也算「应醒」⇒ 恒红 | ✅已修 | 改判「未报告的那个 waiter 现在是否醒 + 三个都报告」 | 探针 161/161，`f2b_left_waiter/f2b_left_awake/f2b_reported` ok |
| A2 门控用「第一个 trap 是 futex」筛子线程，漏掉 F1A（其第一个 trap 是 `PRE_WAIT`） | ✅已修 | 拆成 `immu18==0` 与 `immu18==PRE_WAIT` 两类，各自断言 | `子线程的 futex 调用次数`/`恰有一个线程先在 PRE_WAIT` ok |
| A3 门控把 console 的 `script=5`（十进制）整串与 `K5F_SCRIPT_CMPXCHG` 名字比 | ✅已修 | 用 stub 的 `K5F_SCRIPT_*` 求值后按整数比 | `登记的 script 顺序` ok |
| A4 `f6_waiter_bitset` 在 waiter 报告**之前**读 `res[3]`（此时为 0） | ✅已修 | 首个 trap 就记录 `first_bitset`，改读它 | `f6_waiter_bitset want=0x2` ok |
| A5 `FUTEX_REQUEUE` 的 `nr_requeue` 放错槽（放 `val3`），一个也没搬 | ✅已修 | 放第 4 个参数（`rb17`，无 timespec 命令的 `val2` 槽） | `f5_requeue_moved`/`f5_wake_on_destination` ok，未注入时 129/129 |
| A6 `f2_waiters` 断言引用内核侧常量（会与 stub 各自漂移而不报） | ✅已修 | 改为从 stub 的 clone 块现场数 `WAIT_F1@W_F2` 的个数 | `F2 waiters 常量 == 程序里的等待线程数 want=3` ok |
| A7 子线程的 `PRE_WAIT` trap 未 claim（落到「undefined umon function」，`rd8` 被污染） | ✅已修 | `k5f_child_trap` 把 `PRE_WAIT` 当作本探针功能 claim（SKIP） | 控制台不再出现 `undefined umon function immu18=0x2c20` |
| A8 `--selfcheck` 只证明「能红」、不证明「能绿」（可能恒真） | ✅已修 | 两个控制台、四个 watched check 双向：破损必红、修好后必绿 | `SELFCHECK PASS: every watched check has a reachable FAIL path` |
| A9 `lost-wake` 注入最初只去掉 `__futex_unqueue`，唤醒仍会发出（注入无效） | ✅已修 | 改为让 `__futex_wake_mark()` 直接 `return false`（既不 unqueue 也不 wake） | 该路 F1 红、退码 `0x79`，还原后回绿 |
| A10 F7（CLEARTID + shared wait）原型跑不通（wait=-14），若留下就是把缺陷写成绿用例 | ✅已修（移除 + 登记） | 删掉 F7 代码，结论落「待裁定 2」/「新发现」 | 组件源树 `git diff` 空、补丁集 93 条不变 |
| A11 新增的 `arch_futex_atomic_op_inuser` 在 WAIT/WAKE 路径上不可达（只有 PI/`WAKE_OP` 用它）⇒ 头文件是死代码，运行期从未验证 | ✅已修 | 加 F8 `FUTEX_WAKE_OP`：字 0x10→0x11 + 比较为真才唤醒，专门跑 arch 的 `lr/sc` 读改写；门控另按 uapi 的 `FUTEX_OP_*` 复核编码字 | 探针 129/129（无注入）；注入 `no-op-add` ⇒ `f8_op_word` 红、退码 0x69 |
| A12 `no-op-store` 注入（arch 读改写不落存储）使 `futex_wake_op` 的错误路径死锁 ⇒ 4 分钟超时而不是具名红（证据弱、耗时长） | ✅已修 | 改成 `no-op-add`（ADD 丢旧值 ⇒ 字错、唤醒照常），红得快且具名 | `inject no-op-add: rc=105 red=['f8_op_word']` |

判决：无未修 finding；实现与「验收」逐条对齐，状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（我自己的执行，全部在本任务工作树）**
- 一键证据（运行期证据目录内的 `run.sh`）：`RESULT passed=19 failed=0`、退出码 0；`k5_futex_probe: 161/161 passed`、`INFO probe PASS lines=161 FAIL lines=0`；`judge-selfcheck` rc=0（`SELFCHECK PASS: every watched check has a reachable FAIL path`）。
- 其 6 路注入由我重跑，逐路红在具名 case 且还原回绿：`no-recheck`→F1A、`lost-wake`→F1、`no-bitset`→F6、`no-requeue`→F5、`no-op-add`→F8、`sc-crossing`→F4（六条 `红: want=True got=True` + 六条 `还原后回绿: want=[] got=[]` 全 PASS）。
- 门控真实 rc：`check-config-pins` 0、`check-syscall-abi` 0（86/86）、`check-index-blobs` 0、`apply_series --component linux` 0（幂等）、`check_patch_tree --source-state` linux `OK … count=1 clean=True`；`check-patch-tree` linux 段 `93 patch(es)`、problems=0、count==series 93。
- 不回归（我这轮，`REGRESSION total=11 failed=0`，逐项 rc=0）：k0 130/130、k1 112/112、k2 170/170、k3 263/263、k4_fork 104、k4_cow 86、k4_stack 44、k4_switch 76、k4_kthread 112、k5_syscall 104、k5_clone 97。
- 全新重放：以 `Linux 7.2.10` 基线检出临时树、按 `series` 逐条 `git apply` ⇒ `REPLAY ok=93 bad=0`，与共享源树 `diff -qr` 差异 **0 行**。
- 期望值现场派生抽查 3 条：`f4_sc_after_syscall` want=1 ← `spec/SimRISC-12 §1`「设置成 1，表示写入失败」；`f1a_ret_is_eagain` want=2⁶⁴−11 ← 内核 `errno-base.h` 的 `EAGAIN 11`；`f2_wake_count`/`f6_waiter_bitset` want ← 用户桩 `K5F_F2_WAKE`/`K5F_F6_BITS` 现场求值。
- `sc` 重试有界（读码）：arch futex 头文件两处循环均为 `attempt < DADAO_FUTEX_SC_RETRIES(8)`，耗尽返回 `-EAGAIN`，非自旋。

**我的 ≥4 路注入（其 6 路由我重跑 + 另加 2 路新注入；均 cp+md5 还原 → 重建 → 回绿）**
1. 上述 6 路：全红在具名 case、还原后回绿。
2. 新增 ①（用户桩 F4 在 syscall 之后重做 `lr`，跨 syscall 仍成功）：`--no-inject` rc=1，`内核自评的每条 K5 check 都 ok: want=[] got=['f4_sc_after_syscall']`、宿主 `启动以 SYS_EXIT(0) 收尾: want=0 got=125`(0x7d)；cp 还原后 md5 回到基线。
3. 新增 ②（F3 的失败重试不重新 `lr`）：rc=1，`got=['f3_parent_retry_value']`、宿主 `got=124`(0x7c)；还原后重建 `k5_futex_probe: 129/129 passed`、rc=0。
4. 还原对账：共享 linux 源树 `git status` 空、目标文件 md5 与注入前一致；本任务工作树 `git status -uall` 空（我未改任何仓库文件，未 commit）。

**两件判定**
1. **F7 缺陷记录不如实（阻断，返工只改记录或补测，不改代码）**：① 原型 clone 常量写成 `0x02000000`（= `CLONE_NEWCGROUP`），uapi `CLONE_CHILD_CLEARTID = 0x00200000` ⇒ **CLEARTID 根本没打开**；② 原型用 `K5F_OP_WAIT_PRIVATE`(0x80) **private** wait，不是记录所称 shared wait，该轮唯一留存控制台为 `f7_wait_ret want=0x0 got=0xfffffffffffffff2`；private WAIT 在同页 F1–F6 全绿 ⇒ -14 根因未定位，「实测 shared wait = -14」与真实运行不符。另「⇒ musl `pthread_join` 不可用」与 musl 源码矛盾：join 等 `t->detach_state`、`__timedwait_cp(…,1)` 走 **private**，退出线程 `a_store(DT_EXITED)` + `__wake(…,1,1)` 也是 private，不经过 CLEARTID。**027**（exit/exit_group + 信号，无 pthread 依赖）不受影响；**029** 第 5 条端到端 create/join **未被证实阻断**，但 shared futex（barrier/进程共享路径）仍是未验证风险，须在 029 前用正确 flag 补测（private/shared 两路各贴控制台）。
2. **共享源树外部写入**：当前共享 linux 源树 `git status` 空、`check-syscall-abi` rc=0（86/86）；该改动文本与 `k5_syscall_probe.py` 的 `argmask-mmap` 注入**逐字节相同**，且该探针的运行期暂存目录恰在事发分钟被创建 ⇒ 判为「一次被中断的 `k5_syscall_probe` 注入轮留下的残留」（该探针正在本任务回归链内），**非第三方任务**；盘上无法证明发起会话，如实登记，不据此打回；附带登记：该探针把暂存目录写死成另一任务号的目录（跨任务复用）。

**约束核验**：独立 worktree、分支=任务号 ✓；未改 `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、根 `Makefile` ✓；完成区 ≤30 行且无运行期路径 ✓；注入还原只用 cp+md5（未用 checkout/restore/stash）✓；我未提交 git ✓。

**写入本记录后重跑 `make check-knowledge-refs`**：**rc=2**，红点是另一任务书（`m16-gem5-017`，已随其收尾提交、非本任务改动）里 2 处具体运行期证据路径引用；`悬空: 0`、本任务书与本段 0 处。如实登记，交 architect 处置。

**判决：Needs Revision** —— 仅第 1 件（记录真实性）不过；验收命令块在我自己的重跑下**全部通过**，代码与门控无返工项（改记录即可，无需重跑门控）。附注：首轮一键证据在回归段被环境中断一次（进程消失、现场留存），改后台方式重跑得 19/19。

### 返工轮（第 1 轮 reviewer Needs Revision）engineer 处置

先核实、后改记录；未改内核实现，只补测并新增一个可失败的 F7 用例。

| reviewer 意见 | 我的核实 | 处置 |
|---|---|---|
| ① CLEARTID 常量写成 `0x02000000`（= `CLONE_NEWCGROUP`），CLEARTID 根本没打开 | **成立**：`include/uapi/linux/sched.h` 的 `CLONE_CHILD_CLEARTID 0x00200000` / `CLONE_NEWCGROUP 0x02000000`；上一轮原型（`add_f7`）写的是后者 | 用正确常量重测（见「完成区 → 返工 1」）；常量进交付探针与门控（门控按 `sched.h` 比对，这类错以后必红） |
| ② 原型用 private wait，「shared wait = -14」不成立、根因未定位 | **部分成立**：原型 v1 确是 private + 错常量，那一轮的表现是**睡死到超时**（不是 -14）；-14 来自随后一次「只把 wait 改成 shared、常量仍未改」的临时运行 ⇒ 上一轮记录把两次混成一句，且没做 private/shared 对照 | 重做 4 路对照（shared/private × 匿名页/文件后备页），控制台原文见「完成区 → 返工 1」；根因定位到 `get_futex_key()` 的 `!folio->mapping` 分支 |
| ③ 「⇒ `pthread_join` 不可用」与 musl 源码矛盾 | **成立**：`pthread_join.c` 的 `__timedwait_cp(…, 1)`（private，等 `detach_state`），退出线程的 `a_store(DT_EXITED)`+`__wake(…,1,1)` 也是 private。**核实中另发现**：musl 把 CLEARTID 挂在 `__thread_list_lock`（`pthread_create.c:245/355`），`__tl_lock()`/`__tl_sync()` 对它做 **shared** 等待（`:31`/`:50`，`__tl_sync` 仅在锁被占用时才等） | 删除错误结论；「待裁定 2」改为「join 主路径不受影响；匿名页 shared futex（线程表锁争用、`PTHREAD_PROCESS_SHARED`）仍未验证」；后者记**单独立任务**候选，不扩 `mm/` |
| ④ 要求「`run.sh` 仍 19/19、探针数现场统计」 | 新增 F7（+5 条）与注入 `clear-tid-off`（+5 条），计数由日志现场统计 | 见「完成区」 |

**改动范围自证**：相对上一轮 WIP，补丁集只动了 `k5_futex_selftest.c`（探针）与 `trap.S` 的探针用户桩（`#ifdef CONFIG_DADAO_K5_FUTEX_SELFTEST` 内）——`git diff <WIP> -- components/linux/patches` 仅这两份；futex 头文件、`process.c`/`setup.c`/`Kconfig.debug`/`Makefile`/`setup.h` 零改动 ⇒ 符合「不改内核实现」。

### 第 2 轮 reviewer 验收

**重跑（我自己的执行）**
- 一键证据（运行期证据目录内的 `run.sh`）：`RESULT passed=20 failed=0`、退出码 0；`INFO probe PASS lines=171 FAIL lines=0`、`k5_futex_probe: 171/171 passed`（现场统计）；基础轮我单独跑两次均 `134/134` rc=0；`judge-selfcheck` rc=0。
- 7 路注入逐路「红 → `cp`+md5 还原 → 重建 → 回绿」：`no-recheck`→F1A、`lost-wake`→F1、`no-bitset`→F6、`no-requeue`→F5、`no-op-add`→F8、`clear-tid-off`→F7（`rc=106`=0x6a，红在 `f7_clear_tid_ptr`）、`sc-crossing`→F4。
- **我的独立注入**（`mm_release()` 不再 `put_user(0,…)`，与 `clear-tid-off` 不同路）：`K5 check f7_tid_cleared want=0x0 got=0x1a FAIL`、宿主 `got=106`(0x6a)、探针 rc=1；`cp`+md5 还原后 `134/134` rc=0 ⇒ **F7 清半边断言有可达 FAIL 路径**。
- 门控真实 rc：`check-patch-tree` linux 段 `93 patch(es)`、problems=0、count==93；`check-config-pins` 0、`check-syscall-abi` 0（86/86）、`check-index-blobs` 0、`apply_series` 幂等 0、`--source-state` linux `OK count=1 clean=True`；`REGRESSION total=11 failed=0`（k0 130、k1 112、k2 170、k3 263、k4 104/86/44/76/112、k5_syscall 104、k5_clone 97）。
- 改动范围：相对 `0611118c` 只动 `k5_futex_selftest.c.patch`、`trap.S.patch`（另加 changelog、任务书、探针脚本），`series` 仍 93；futex 头文件、`process.c`/`setup.c`/`Kconfig.debug`/`Makefile`/`setup.h` **0 改动**；trap.S 改动全在 `#ifdef CONFIG_DADAO_K5_FUTEX_SELFTEST`…`#endif` 内 ✓。
- 语义现场确认：`errno-base.h` `EAGAIN 11`、`EFAULT 14` ⇒ `-11`=EAGAIN、`-14`=EFAULT ✓；`CLONE_CHILD_CLEARTID` 门控按 `sched.h` 比对（`0x02000000` 这类错现在必红）✓。

**我自己跑的 F7 private/shared 两组（临时加测 → `cp`+md5 还原 → 重建回绿）**
- `f7b` shared WAIT（数据页字）= **-14**、`f7c` private WAIT = **-11**、`f7d` shared WAKE = **-14** —— 与记录一致 ✓。
- `f7e` = **-11**，但**测到的不是文件后备页**：我的运行打印 `K5 rev file map FAILED`（`filp_open` 失败）；其原脚本失败分支不打印、其控制台同样没有 `file map` 行，且该地址的 fault `vma=` 是**未被切开的整段匿名区间** ⇒ 两次都没建成文件映射，这个 -11 取自该窗口里的**匿名栈页**。
- ⇒ 两条记录不成立：①「文件后备页 shared 正常」**未被验证**；②「本端口匿名页 shared = `-EFAULT`」**过宽**——同一 VMA 内，经 NWPERM `replace-zero` 写替换的数据页 shared 失败，经 `fill-zero` 读填充的匿名栈页 shared **成功**。真实条件应窄化为「**写替换出来的那一页**」，文件页那一路须补测或删除。

**`__thread_list_lock` 影响（只判不改）**
- 属实：`pthread_create` 把 `&__thread_list_lock` 当 CLEARTID 指针（`pthread_create.c:355`），`__tl_lock/__tl_sync/__tl_unlock` 分别用 `__wait(…,0)`/`__wake(…,0)`，即 **shared** 操作；但只在**争用**时才发 futex（无争用 `a_cas` 直接成功，`__tl_sync` 见 0 即返回）。
- `-14` 不会传导到应用：`__wait`/`__wake` 忽略返回值，`__timedwait_cp` 把非 EINTR/ETIMEDOUT 一律归 0；WAIT 失败即不睡 ⇒ **不存在丢唤醒死锁**，争用时只是**自旋**（CPU 开销）。
- **判**：不阻断 025；**不影响 029** 的端到端 create/join 代表例（无争用路径不发 futex、join 主等待 private）；027 无依赖。**同意立独立任务**，但判据须按上面的窄化条件写（写替换页 + 真实文件页两路实测），并在 029 前补一次「并发 create/join + 文件后备页 shared」实测。

**判决：Needs Revision** —— 仅**记录层**需改（`完成区 → 新发现`、`待裁定 2`、changelog 现场事实① 的 f7e 归因与匿名页泛化）；验收命令块在我自己的重跑下**全部通过**，代码与门控无返工项（改记录即可，无需重跑门控）。

**写入本记录后重跑 `make check-knowledge-refs`**：**rc=2**，红点仍是 `m16-gem5-017` 任务书那 2 处（已知、另案处理，不背给本任务）；`悬空: 0`、本任务书 0 处。共享 linux 源树 `git status` 空、本工作树仅本任务书被改、我未提交 git。

### 返工轮 2（第 2 轮 reviewer Needs Revision）engineer 处置

| reviewer 意见 | 我的核实 | 处置 |
|---|---|---|
| ① 「文件后备页 shared 正常」未被验证（`filp_open` 失败、失败分支不打印、`vma=` 是未切开的匿名区间） | **成立**：上一轮的测量脚本把 `filp_open` 的失败分支写成静默（`IS_ERR` 时什么都不打）；控制台因此没有 `file map` 行；该 VA 是栈页 | 失败分支改为**必打并显式 `FAILED`**（本轮原文：`K5 futex file create(bogus) FAILED err=-2`；该镜像是临时测量、以 `FAILED` 上屏，若常驻化须改 `k5f_expect` 判 FAIL）；真实文件页改用 ramfs（`O_CREAT` + `kernel_write` + `mmap(MAP_SHARED)`），建成后打印 `file map: … got=… ok`；在其上实测发现 `get_user_pages_fast` 停住 ⇒ 记「**不可测**」而不是「正常」 |
| ② 「匿名页 shared = `-EFAULT`」过宽 | **成立**：同一 VMA 内 `fill-zero`（读填充）页 `get_futex_key()` = 0（`mapping` 非 0）⇒ WAIT = -11；`replace-zero`（写替换）页 `mapping == NULL` ⇒ -14 | 收窄为「**写替换产生的页**失败、读填充的页正常」；根因记「通道页缺 rmap，`mapping` 不是不变量」，不按页类下结论 |
| ③ 不得声称 `pthread_join` 不可用；`__thread_list_lock` 只在争用发 futex | **成立**（另查 musl `__wait/__wake` 忽略返回值、`__timedwait_cp` 把非 EINTR/ETIMEDOUT 归 0） | 记录改为「join 走 private、不受影响；争用时退化为自旋，**不阻断 025/029**」 |
| ④ `run.sh` 20/20、探针数现场统计 | 本轮只改记录（任务书 + changelog），探针/补丁集/门控**零改动** | 见「完成区」 |

**与用户 2026-11-20 规则对齐**：该规则要求内核实现优先走 `mm/`/`kernel/` 的通用路径；本轮把「通道页缺 rmap、文件映射不经页缓存」记成**单独立任务**（回归 `handle_mm_fault`/rmap/page cache），不在本任务里给 futex 另造旁路。

**改动范围自证**：本轮 `git status` 只有任务书与 `components/linux/changelog.md`；`components/linux/patches`、`series`、`tools/linux/k5_futex_probe.py` 与上一轮**逐字节相同** ⇒ 上一轮 `run.sh` 20/20、探针 171/171、7 路注入的结论继续有效（reviewer 已独立重跑）。

### 第 3 轮 reviewer 验收

**重跑（我自己的执行）**
- 一键证据（运行期证据目录内的 `run.sh`）：`RESULT passed=20 failed=0`、`R3_RUN_EXIT=0`；`INFO probe PASS lines=171 FAIL lines=0`、`k5_futex_probe: 171/171 passed`（现场统计）；基础轮我单独跑 3 次均 `134/134` rc=0；`judge-selfcheck` rc=0。
- 7 路注入逐路红 → `cp`+md5 还原 → 重建 → 回绿（`clear-tid-off` `rc=106`=0x6a、`sc-crossing` 0x7d 等）；门控真实 rc：`check-patch-tree` linux 段 `93 patch(es)`/problems=0/count==93、`check-config-pins` 0、`check-syscall-abi` 0（86/86）、`check-index-blobs` 0、`apply_series` 幂等 0、`--source-state` linux OK；`REGRESSION total=11 failed=0`（k0 130、k1 112、k2 170、k3 263、k4 104/86/44/76/112、k5_syscall 104、k5_clone 97）。
- 改动范围：相对上轮 WIP **只有任务书 + changelog**（`git diff --stat` 两文件）；补丁集/探针/门控与上轮逐字节相同 ✓（本轮 20/20、171/171 即由此产生）。

**我自己跑的三态实测（临时镜像 + 我自己写的 `get_futex_key` 打点；跑完 `cp`+md5 还原 → 源树 `git status` 空、回绿 `134/134` rc=0）**
- P1 `fill-zero` 页：`REV gup ret …` → `REV mapping=00000200047e1449 anon=1` → `p1_fillzero_shared_wait_ret = -11` ✓（`folio_test_anon` ⇒ 键=(mm,address) ⇒ 值不符答 `-EAGAIN`）。
- P2 `replace-zero` 数据页：`REV mapping=0000000000000000 anon=0` → `p2_replacezero_shared_wait_ret = -14` ✓（`!folio->mapping` ⇒ `-EFAULT`）——同一份控制台里 `mapping` 与返回值**逐行可对**，因果成立。
- P3 文件页：`K5 futex file map: va=0x10000c80000 … ok` + `K3 pf … result=fill-file` → `REV gup enter addr=0x10000c80000 rw=0` **之后无任何输出** → 启动超时、探针 rc=1（`D: 启动以 SYS_EXIT(0) 收尾 want=0 got=124`）⇒ **GUP 停住我自己复现**；P4 未到达（与记录一致）。
- 读码补一句：`dadao_pf_fill` 对无文件的 data VMA 映射的是**共享零页**，而 P1 拿到的是 `anon=1` 的页 ⇒ P1 的 -11 应来自 **GUP 的 `FOLL_WRITE` 走通用 COW 路径（带 rmap）**，不是「通道页有 rmap」——与记录「`mapping` 不是通道维护的不变量、不能按页类划界」相容；**机制留给 035 定位**（finding，不阻断）。

**P3 影响面（只判）**
- **应写进 `m14-linux-035 缺页路径回归 Linux 通用流程` 的背景**：作为「GUP 必须返回」的实测症状 + 可机械判的回归项（shared 键、`splice/vmsplice/sendfile`、`O_DIRECT`、`process_vm_readv`/`ptrace`/`/proc/pid/mem`、`io_uring` 固定缓冲都钉页）；并注明**停点未定位**（fast walk / faultin / 锁），035 须先定位再谈修复。
- **不影响 027**（信号只走 `copy_to_user`/`put_user`，不钉页）、**不影响 029**（私有 futex 不进 GUP、普通 `read/write` 用 `copy_*_user`；其 create/join 代表例用 private 键）。

**记录核验**：`待裁定 2` / `完成区` / changelog ① 现在只剩实测事实（三态 + 根因 + 影响面 + A/B/C 选项），**无**「`pthread_join` 不可用」、**无**「匿名页 = `-EFAULT`」这类过宽结论；changelog **②–⑦ 与上轮逐字节相同**（程序比对 702/702 字节 identical）✓。小 finding（不阻断）：临时件 `r2_measure.py` 的 P3 发的是 shared **WAIT**、留存控制台里发的是 shared **WAKE**（`rd16=0x1`），归档时应注明实际用的是哪一版。

**判决：Accepted** —— 验收命令块在我自己的重跑下**全部通过**，三态与 P3 停点我**独立复现**，记录只剩实测事实；上述两条 finding 属记录/临时件层面，交 architect 与 035 处置，不构成返工项。

**写入本记录后重跑 `make check-knowledge-refs`**：**rc=2**，红点仍是 `m16-gem5-017` 任务书那 2 处（已知、另案处理，不背给本任务）；`悬空: 0`、本任务书 0 处。共享 linux 源树 `git status` 空（三个被我临时改过的文件 md5 与注入前逐字节相同）、本工作树仅本任务书被改、我未提交 git。

## 完成区

**测试结果**：`k5_futex_probe.py` **171/171**（基础 134 + 7 路注入，计数现场统计）；7 路注入全「红 → `cp`+md5 还原 → 重建 → 回绿」，退码即目标 case 码：`no-recheck` 0x7a、`lost-wake` 0x79、`no-bitset` 0x7f、`no-requeue` 0x7e、`no-op-add` 0x69、`clear-tid-off` 0x6a、`sc-crossing`（QEMU 侧）0x7d。不回归 11 项全绿（k0 130、k1 112、k2 170、k3 263、k4_fork 104、k4_cow 86、k4_stack 44、k4_switch 76、k4_kthread 112、k5_syscall 104、k5_clone 97）。一键证据 `run.sh`：见「验收结果」。
**修改文件**：`components/linux/patches/arch/dadao/include/asm/futex.h.patch`（新）、`.../kernel/k5_futex_selftest.c.patch`（新）、`.../kernel/{trap.S,process.c,setup.c,Makefile}.patch`、`.../include/asm/setup.h.patch`、`.../Kconfig.debug.patch`、`components/linux/series`、`components/linux/changelog.md`、`tools/linux/k5_futex_probe.py`（新）、17 个门控脚本的 `CONFIG_PINS` 各补 1 行。**未新增** `cmpxchg.h`。
**验收结果**：运行期证据目录内的 `run.sh`（一键、非交互、逐条打印 name/expect/got/rc、任一失败即非零）：**20/20 项 PASS**（上一轮 19 项无回归 + 新增的 `injection-clear-tid-off-red` 一条，计数现场统计）；`check-patch-tree` **linux 段 93 补丁 0 问题**、`apply_series --component linux` 幂等、`--source-state` **linux count=1 clean=True**、`check-config-pins` PASS（18 脚本 × 20 符号 × 48 镜像）、`check-syscall-abi` 86/86、`check-index-blobs` PASS（339 新文件补丁）。
**新发现/坑**：
- `CLONE_CHILD_CLEARTID`：**清 tid 可用**（实测 0x0）；**唤醒**是 shared 键，其成立与否取决于页——`fill-zero` 匿名页键成立（shared WAIT = -11）、`replace-zero` 匿名页 `-14`（`folio->mapping==NULL`）、**真实文件后备页在 GUP 停住（不可测）**；根因是通道页无 rmap（见「待裁定 2」）。上轮「匿名页 shared = `-EFAULT`」「⇒ `pthread_join` 不可用」两句均已按实测收窄/删除。
- `FUTEX_WAKE_OP` 是 arch 原子钩子（`arch_futex_atomic_op_inuser`）**唯一**的用户路径；不写 F8 则该头文件是死代码。
- `FUTEX_REQUEUE` 的 `nr_requeue` 在**第 4 个参数**（无 timespec 的命令该槽是整数 `val2`）；`futex_requeue()` 返回「唤醒数 + 搬运数」。
- 7.2.10 的 `FUTEX_WAIT` 复核是 `get_user` **读后比较**，不是 `cmpxchg`；arch 的 `cmpxchg` 钩子由 PI/requeue 与 `WAKE_OP` 用。
- 探针镜像须显式跳过 `dadao_k4_boundary()` 的收尾；`lr/sc` 的「入口清保留标记」在**机器**侧（QEMU `helper.c`），内核侧无法注入。
**遗留问题**：
- **shared futex 的可用页类（已定位、未修）**：`fill-zero` 匿名页键成立；`replace-zero`（写替换）匿名页 `-EFAULT`；**真实文件后备页在 `get_user_pages_fast` 停住（不可测）**。根因 = 通道页由 `alloc_page` 装、无 rmap，文件映射不经页缓存。影响 `PTHREAD_PROCESS_SHARED` 同步对象与按 shared 口径等待的用户程序；**建议单独立任务**（补 rmap + 页缓存映射），本任务不改 `mm/`；musl `pthread_join`（private）与 029 的 create/join 不受阻。
- 注入被强杀会**留下注入态**（本轮遇到一次）；已用注入器的 `.orig` + md5 还原，建议后续落「注入中」标记。
- `check-patch-tree`/`--source-state` 的**整体**非零来自在途外部组件（chipyard/gem5）；linux 段已单独断言。内核 `arch_cmpxchg` 仍是 asm-generic 的 UP 形。

### 返工 1（第 1 轮 reviewer：F7 记录不如实）

**原记录 → 实测事实 → 结论**（内核实现未改；F7 由临时测量提升为交付用例）
1. 原记录「CLEARTID + shared wait = -14 ⇒ shared wait = `-EFAULT` ⇒ `pthread_join` 不可用」。实测（控制台原文）：`f7a_tid_word_after_exit=0x0`（正确常量 `0x00200000` 下**清**可用）、`clear_child_tid` = 数据页 `W_F7`、`mm_users = 2`；同一字 `shared WAIT = -14`、`private WAIT = -11`、`shared WAKE = -14`、**文件后备页** `shared WAIT = -11`（expected 均为 `0x0bad0bad`）⇒ `-14` 只在「不带 `FUTEX_PRIVATE_FLAG` 的 op + 本端口故障通道装的匿名页」出现（`get_futex_key()` 的 `!folio->mapping` 分支，该页无 rmap）。⇒ CLEARTID 的**唤醒**在该页上发不出去（`mm_release()` 不检查 `do_futex` 的返回值）；join 主等待是 private 的 `detach_state` ⇒ 原结论**错误已删**。
2. 处置：F7（清半边，5 条断言，可失败）进交付探针 + 注入 `clear-tid-off`（`0x6a`）；`CLONE_CHILD_CLEARTID` 由门控按 `include/uapi/linux/sched.h` 复核（错成 `0x02000000` 必红）；shared 面记「待裁定 2」+ 单独立任务候选。

### 返工 2（第 2 轮 reviewer：文件页未建成 + 匿名页结论过宽）

**原记录 → 实测事实 → 结论**（内核实现与探针/补丁集均未改，只改记录）
1. 原记录「文件后备页 shared = -11 ⇒ 正常」。**不成立**：上一轮 `filp_open` 失败且失败分支静默，测到的是**栈页**。本轮修复失败分支后原文：`K5 futex file create(bogus) FAILED err=-2`（故意的坏路径）+ `K5 futex file write: n=8`、`K5 futex file map: va=0x10000c80000 got=0x10000c80000 ok`（ramfs `mmap(MAP_SHARED)` 真的建成）。
2. 原记录「本端口匿名页 shared = `-EFAULT`」**过宽**。同一 VMA 内实测：`fill-zero`（读填充）页 `get_futex_key()` 返回 0、`mapping=0x200047e1449` ⇒ shared WAIT = **-11**；`replace-zero`（NWPERM 写替换）页 `mapping=0x0` ⇒ **-14**。⇒ 收窄为「**写替换产生的页**失败、读填充的页正常」。
3. 真实文件后备页（故障路径 `fill-file`）：shared **WAKE 即停在 `get_user_pages_fast`**（控制台在该 `gup start` 后无下文、240 s 超时；WAIT 未及执行）⇒ **不可测**（既非 -14 也非 -11），原因是本端口文件映射由通道从文件拷入私有页、不是页缓存页。
4. 结论：共同根因是**通道页无 rmap**（`dadao_pf_alloc_page()` = `alloc_page`，文件映射也不经页缓存），「按页类划界」只是症状；`PTHREAD_PROCESS_SHARED`/真实文件页的 shared 面**单独立任务**，musl `pthread_join`（private）与 029 不受影响。
