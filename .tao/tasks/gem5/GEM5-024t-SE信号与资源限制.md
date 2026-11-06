# GEM5-024t: gem5 SE 信号、资源限制与进程信息

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-023t`（文件 I/O 与时钟；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与事实

- `GEM5-022t` 后 SE 基线：gem5 pass 371 / blocked 217；文件 I/O 与时钟由 `GEM5-023t` 处理
- 本任务覆盖基线里三类阻塞（`GEM5-021t` gap inventory）：
  - **signals 21 例**：`rt_sigprocmask`(135)、`sigaltstack`(132)、`rt_sigaction`、`rt_sigreturn`；代表 `functional/pthread_cancel`、`pthread_cond`、`setjmp`、`regression/sigreturn`、`sigaltstack`、`sigprocmask-internal`、`llvm-ts sqlite3`/`lemon`/`SIBsim4`
  - **resource limits 2 例**：`prlimit64`(261)；代表 `regression/rlimit-open-files`、`pthread_atfork-errno-clobber`
  - **process info 1 例**：`uname`(160)；代表 `llvm-ts unix-smail`
- static 语料里的「pthread_*」多数只是**单线程**用到 `rt_sigprocmask`（信号屏蔽/取消点），不要求真线程；真线程/futex 另立任务

## 目标

1. **信号**：实现 `rt_sigprocmask`、`rt_sigaction`、`rt_sigreturn`、`sigaltstack`、`kill`/`tgkill`（自杀路径）；单进程自投递信号（`raise`）与屏蔽/挂起语义；信号帧在 guest 栈上构造与恢复；默认动作（terminate/ignore）与 `SIGCHLD` 等按 Linux 语义。
2. **资源限制**：`prlimit64`/`getrlimit`/`setrlimit`；至少 `RLIMIT_NOFILE`、`RLIMIT_STACK`、`RLIMIT_DATA`、`RLIMIT_AS`（与 QEMU/内核口径一致，`cur=0` 的 Valgrind workaround 需对齐）。
3. **进程信息**：`uname`、`getpid`/`getppid`/`gettid`、`getuid`/`geteuid`/`getgid`/`getegid`、`sysinfo`（按语料需要）。
4. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh,process.*,...}`、`components/gem5/changelog.md`、`components/gem5/README.md`（能力边界）、本任务书、`milestones.md`。

**不在范围**：真线程/`clone`/`futex`/TLS（另立任务）、多进程 `execve`/`fork`/`wait4`（另立）、文件 I/O 与时钟（`GEM5-023t`）、动态链接、QEMU、测试用例与期望。

## 验收标准

1. 基线复跑：signals / resource limits / process info 三桶 blocked 归零（或转真实失败并给最小复现）；`qemu_only_fail` 仍 0；`gem5_only_fail` 不新增。
2. 代表案例（`setjmp`、`sigaltstack`、`sigreturn`、`rlimit-open-files`、`unix-smail`）各跑 ≥3 次结果一致。
3. 信号语义抽测：`raise(SIGUSR1)` 被 handler 捕获后继续执行；屏蔽期间挂起、解除后投递；`SIG_IGN`/默认终止；`sigaltstack` 生效。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
5. 反例：把 `rt_sigprocmask` 改回未实现 ⇒ 代表案例回 blocked；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 先做 `rt_sigprocmask`（21 例里绝大多数首触它），再做 `sigaltstack`/`sigreturn`/`rt_sigaction`。
- 信号帧布局须与 `contract-syscall` 一致（大端、64 KiB 页、寄存器保存顺序）。
- 若某语言/用例依赖真线程（`clone`），按 BLOCKED 单列，不硬凑。

## 完成区

**测试结果**：`run.sh` 默认 33/33 PASS（SUMMARY pass=33 fail=0；基线明细另打印 7 条）、`--inject` 16/16 PASS；独立 guest 探针 77 条断言全 PASS（宿主 oracle 75 条；PASS 集除 `frame-info-before-ucontext`、`sigaltstack-too-small` 两条 guest-ABI-only 断言外逐条一致）；信号行为各 ×3 一致：默认 `raise(SIGUSR1)`=138、`kill(SIGKILL)`=137、默认 `SIGCHLD` 忽略=0；代表 10 例 ×3 全 pass 且三次一致；`unix-smail` ×3 一致 blocked@59（进程信息缺口已闭，新缺口 pipe2 归 `GEM5-025t`）；基线 static 复跑 gem5_pass 409 / blocked 178（023t 399/188），signals、resource limits、process info 三桶 blocked=0，`qemu_only_fail=0`，`gem5_only_fail=1`（bison，023t 既有捕获模型差异）；增量去向：10 例转 pass、20 例转 threads/futex、6 例转 time budget、1 例转 IPC、1 例转 simulator/loader。
**修改文件**：`components/gem5/patches/src/arch/dadao/{process.hh,process.cc,se_workload.cc}.patch`、`components/gem5/README.md`、`components/gem5/changelog.md`、本任务书、`.tao/knowledge/milestones.md`。
**验收结果**：`build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1 `make check`、L2 `check-modules` 全 rc=0；源 `se_workload.cc` md5 `ae6fc63d928d4f2ed01e5a523354ce83`（补丁 `fb2d988436d7…`）、注入还原后 `md5sum -c` OK；gem5.opt md5 `87239b8771f29920206534f1a0f7425a`（重建即变，仅标识）；源树 `HEAD=1b16db4 count=1 clean=True`；反例注入 `rt_sigprocmask`→未实现 ⇒ `regression/sigprocmask-internal` blocked@135，`cp`+`md5sum -c` 还原重建后探针回绿（未用 git 还原）。
**新发现/坑**：① 帧布局真源是 musl `arch/dadao/bits/signal.h`（`ucontext_t` 1200 B、`uc_mcontext`@168、`__gregs[129] = {pc, rd, rb}`），`contract-syscall` 只钉寄存器/返回值不含帧，探针按该头文件的 C 类型逐字段校验；② `uc_sigmask` 存的是**进入 handler 前**的掩码（Linux `sigmask_to_save`），handler 生效掩码 = 旧|`sa_mask`|sig（`SA_NODEFER` 免 sig），`sigreturn` 必须回读 guest 帧（musl 取消处理会原地改写 `MC_PC`/`uc_sigmask`）；③ handler 返回地址须压 RegRAS/MemRAS（`pushRas` C1/C2/C3a/C3b），sigtramp 两指令编码用 `llvm-mc` 独立核对（`4c3c008b`/`7f000000`）；④ 内核 `do_prlimit` 的「升硬限需 CAP_SYS_RESOURCE」在 SE 按无特权拒绝 `EPERM`（与 QEMU 透传宿主一致），否则探针无法在真实内核上对照；⑤ `check-run-artifacts` 只认 `<TASK-ID>-<purpose>.(log|json|txt)`，临时 `.sh` 驱动须放仓库外。
**遗留问题**：① `functional/sem_open` 由 process info 转 simulator/loader：`sem_open` 需 `/dev/shm` 文件映射（mmap 文件映射归 `GEM5-028t`），失败后 guest 解引用 NULL，gem5 SE 平台页错误仍是 panic（不转 guest SIGSEGV，023t 同口径）；② `functional/sscanf_long` 转 time budget（直跑 430 s 通过，驱动预算 120 s）；③ 四个重应用（SIBsim4/lua/obsequi/sqlite3）转 time budget（SIBsim4 900 s 内完成 94% 输出，纯速度）；④ `unix-smail` 转 IPC（pipe2）、`lemon` 等同转 threads/futex（clone）；⑤ `RLIMIT_AS`/`STACK`/`CORE` 只保存/回读不强制（README 已披露）。

### 审阅记录 → 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `doSigprocmask` 复用同一个 8 B 缓冲：先写 old 再读 new ⇒ 「BLOCK 且查询旧掩码」时把旧掩码当新掩码（屏蔽不生效） | ✅已修 | old 写入独立 `oldRaw` | 探针 `blocked-not-delivered`/`blocked-pending-visible` 由 FAIL→PASS |
| F2 `allocGuestFd`/`dup3`/`fcntl(F_DUPFD)` 未受 `RLIMIT_NOFILE` 约束 ⇒ `rlimit-open-files` 不 EMFILE | ✅已修 | fd 分配按 `limits[RlimitNofile].cur` 截断 | 探针 `rlimit-nofile-enforced/count` PASS；代表例 ×3 pass |
| F3 `doSigreturn` 用 `1<<64` 构造 64 位掩码是 UB | ✅已修 | 删除该掩码校验，只校验 PC 对齐 | 该改动前后两次构建的 gem5.opt md5 相同（`2a7404c6…`），行为中性；探针 77/77 |
| F4 探针把 `orig` 复用于 DATA 后仍与 NOFILE 比较（探针自身缺陷） | ✅已修 | 独立 `nofile_orig`，NOFILE 降硬限测试移到最后 | 探针 `prlimit-self` PASS |
| F5 与真实内核对照时 `setrlimit` 降硬限后无法升回（EPERM） | ✅已修 | SE 按内核 `do_prlimit` 拒绝升硬限；探针断言 EPERM | guest/host 探针均 PASS |
| F6 `check-run-artifacts` A3 拒收 `.work/log/**` 下的临时 `.sh` | ✅已修 | 驱动脚本移出仓库工作区 | `make check` rc=0 |
| F7 页错误不转 guest `SIGSEGV`（空指针仍 panic） | ❌不修（越界，已披露） | README 已知限制 + 遗留① | 归属 SE 平台 `sim/faults.cc`（非本任务文件集）；`sem_open` 的真实缺口是文件映射（`GEM5-028t`），023t 同口径 |

判决：F1–F6 已修并有复验证据；F7 为 SE 平台既有行为（`sim/faults.cc`，非本任务文件集）、已登记遗留。状态 `待验收`。

### 审阅记录 → 第 1 轮 reviewer 验收

**判决：Accepted**（验收标准 1–6 全部经 reviewer 亲跑复核；无阻断项；6 条非阻断 finding 见末）

**重跑记录（reviewer 独立执行，真实退出码）**
1. **独立全量基线**（`GEM5-021t` 驱动 static，reviewer 自建 work/summary 目录）：`qemu_pass=587 gem5_pass=409 both_pass=409 blocked=178 gem5_only_fail=1 qemu_only_fail=0`；gaps = time budget 137 / threads 25 / IPC 9 / SysV 3 / simulator-loader 3 / exec 1；**signals、resource limits、process info 三桶 = 0**，且全部 blocked 的 `reason` 中不含三桶 syscall 号（17/129-132/134-136/139/160/163/164/169/172-179/261）；与 023t 基线逐例对比：10→pass、19+1→threads/futex、4+1+1→time budget、1→IPC、1→simulator/loader（与完成区数字逐项一致）
2. **bison 归因独立复现**：同一 ELF 用 `qemu-dadao … parse.y.in -v`，`2>&1` 合并输出 + `exit 0\n` 与 reference **逐字节相同**；gem5 stdout+stderr+tail 与 reference 同为 85401 B 但只差**一行位置**（`…shift/reduce conflict.` 1092→3442），**排序后行多重集 diff rc=0**；gem5 拼接输出与 QEMU 分离捕获拼接**逐字节相同** ⇒ 捕获模型差异、非能力回归
3. **门控逐条亲跑**：`build-gem5` rc=0、`check-patch-tree` rc=0（7 组件 **305 patches OK**）、`check-source-state` rc=0（gem5 **HEAD=1b16db4953f8 count=1 clean=True**）、`check-inst` rc=0（44/44）、`check-arch` rc=0（14/14）、`make check`(L1) rc=0（`repository checks (L1): PASS`、`check-run-artifacts: PASS`、`check-milestones-fresh` A1 核验 87 行）、`check-modules`(L2) rc=0（`module checks (L2): PASS`）
4. **里程碑行核对**：`| GEM5-024t | 待验收 | 2026-11-06 20:20（登记） | …409/178，三桶清零 |` 与任务书 `**状态**：待验收` 一致（A1/A5 通过）——023t 首轮的「表行未同步」未复现
5. **证据脚本重跑**：`bash run.sh` **rc=0，SUMMARY pass=33 fail=0**（0 条 FAIL 行）；`bash run.sh --inject` **rc=0，SUMMARY pass=16 fail=0**（`inject-case-blocked@135`、`inject-restore-md5`、还原后探针 77/77 且与宿主 PASS 集一致）
6. **reviewer 独立注入（与 engineer 不同注入点）**：把 `doSigaction` 的 handler 存成 `0` ⇒ 重建后 `regression/{sigreturn,sigaltstack}` 驱动 rc=1、JSON 全非 pass，探针 **rc=138**（末行 `PASS sigaction-install`，死于默认动作）；`cp` + `md5sum -c` 还原（`ae6fc63d…` 前后相同、源树 `count=1 clean=True`）→ 重建 rc=0 → 探针 fails=0、两代表例回 pass；**全程未用 git 还原**
7. **信号帧/sigtramp 独立探针（同 ELF 对照 qemu-dadao）**：`MAP_FIXED@0x0000400000000000` = gem5 **REFUSED/ENOMEM**（qemu OK，属 SE 8 GiB 窗口约定 ⇒ sigtramp 不可被覆盖）；handler 原地改写 `uc_mcontext.__gregs[0]`(MC_PC) 后**两引擎都以 rc=42 退出**（落空路径为 7）⇒ `sigreturn` 回读 guest 帧的 MC_PC 成立；sigtramp 编码 `llvm-mc` = `4c3c008b`/`7f000000` == `process.cc` 写入字节；地址与窗口/栈/MemRAS 两两不相交
8. **uname/身份同 ELF 双引擎**：gem5 与 qemu-dadao 输出**逐行相同**（`MACHINE=dadao`、`SYSNAME=Linux`、`RELEASE=6.8.0-147-generic`、nodename/sysinfo/getcwd/getpid 一致）⇒ `machine` 值与 QEMU 一致、无差异
9. **rlimit 同 ELF 双引擎（逐项）**：`NOFILE=42` 时 dup 停在 `maxfd=41 hits=39 errno=EMFILE` **两侧相同**；`cur=0/max=INF` 的 DATA workaround 两侧都放行 4 MB；`{10,1}` 反转对两侧都 EINVAL；AS=4 MB 时 16 MB 匿名映射 **SE 成功 / QEMU ENOMEM**、DATA=4 MB 时 8 MB 可写匿名映射 **SE 成功 / QEMU ENOMEM**、升 AS 硬限 **SE EPERM / QEMU 成功**、默认 STACK 读回 **SE INF / QEMU 8388608**
10. **完成区/快照**：完成区正文 5 行 ≤30、无具体运行期路径（仅 `.work/log/**` 通配）；审查前后 `git status -uall` 同为这 7 个文件、`md5sum -c` 其余 6 项 OK；未 commit/push

**约束核验**：不改测试用例/期望、不改 QEMU（status 无 `tests/**`、`tools/**`、`components/qemu/**`）；补丁由 `make_patch.py` 从源树导出且 `check-patch-tree` 断言⑥/⑨ 通过；帧布局取自 musl `arch/dadao/bits/signal.h`（128+1200、`uc_mcontext`@168、`__gregs[129]={pc,rd,rb}`、大端）；`JOBS=32` 单构建；临时产物均在 `.work/` 内。

**非阻断 findings（architect 收尾处置）**
- **G1（文档）**：README「QEMU user 同样不解释 guest rlimit」**不实**——锁定 QEMU 的 QEMU-084t（`linux-user/mmap.c`）在模拟器内保存并**强制** guest `RLIMIT_AS`/`RLIMIT_DATA`（`guest_rlimit_check_mmap`），且对这三项**不做**升硬限特权检查；完成区新发现④「与 QEMU 透传宿主一致」仅对非内存类（如 NOFILE）成立。事实（AS/STACK/CORE 只保存/回读）已披露，**理由须改写**。
- **G2（代码/披露）**：见重跑 9 的四项 QEMU↔SE 实测差异；语料无用例触达（基线无新增 `gem5_only_fail`）。建议 README 点名「RLIMIT_DATA 仅在 brk 强制、匿名 mmap 不挡」，并把 AS/硬限/STACK 默认读回三项登记为 QEMU↔SE 差异（或另立任务补强制）。
- **G3**：`doKill` 接受 `pid∈{0,-1,-pid}` 并投递 self；Linux `kill(-1)` 不含 caller，README「只接受 self（其余 ESRCH）」与代码不完全一致（语料只用 self）。
- **G4**：默认动作中 stop 系（`SIGTSTP/TTIN/TTOU`）在 SE 走 terminate（Linux 为 stop；README「其余终止」已如实描述）；内核 `sigaltstack` 接受 `SS_AUTODISARM(1<<31)`，SE 回 EINVAL（未披露，极冷门）。
- **G5（证据脚本）**：`check_baseline` 读**既有** baseline JSON、不自行重跑（023t 同款），已由本次 reviewer 独立全量复跑替代核对；`unix-smail-run-N` 断言 rc==1 是「期望非零」写法（脚本已注释）。
- **G6**：`probe-guest-host-agree` 排除 2 条 guest-only 断言（host glibc 帧序、动态 MINSIGSTKSZ）——排除项在脚本中点名且经核对确属 ABI 差异，非凑绿。

#### 收尾（architect，2026-11-07 03:13）

- 非阻断 G1 已改：README 删除「QEMU user 同样不解释 guest rlimit」的错误表述，改为「QEMU 在模拟器内强制 AS/DATA；SE 只在 brk 强制 DATA」并列出四项实测差异。
- G2 差异已登记（AS 不强制、STACK 默认读回 INF、升硬限 EPERM）；G3 `kill(-1)` 按 self 处理已写入 README；G4 stop 系终止、`SS_AUTODISARM → EINVAL` 已披露；G5/G6 仅记录。
- 基线：gem5 pass 399→409、blocked 188→178；signals/resource-limits/process-info 三桶清零；`qemu_only_fail=0`、`gem5_only_fail=1`（bison 捕获模型）。
- 判决 Accepted，状态置 `已验证`。
