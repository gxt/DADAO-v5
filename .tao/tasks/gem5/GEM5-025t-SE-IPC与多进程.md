# GEM5-025t: gem5 SE IPC 与多进程

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-024t`（信号/资源限制；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与事实（`GEM5-021t` gap inventory）

- **IPC/socket/pipe 6 例**：`pipe2`(59) 5 例（`functional/fscanf`、`popen`、`spawn`、`regression/daemon-failure`、`fgetwc-buffering`）+ `socket`(198) 1 例（`functional/socket`）
- **process creation/exec 1 例**：`execve`(221)（`regression/execle-env`）
- 其余 syscall 面（`fork`/`wait4`/`dup`/`close` 等）按现场补齐

## 目标

1. **pipe**：`pipe2`（含 `O_CLOEXEC`/`O_NONBLOCK`）、阻塞/EOF/`EPIPE`、与 `dup`/`fcntl` 协作；guest fd 表内 pipe 对象。
2. **socket（最小面）**：`socket`/`bind`/`connect`/`send`/`recv`/`shutdown`/`getsockname` 等按 `functional/socket` 实际调用；若语料只用 `AF_UNIX` 就只做该族，其它返回 `EAFNOSUPPORT`（如实登记）。
3. **多进程**：`fork`/`vfork`（SE 多 process 支持）、`execve`（按 `contract-syscall` 的 argv/envp/auxv 约定）、`wait4`；父进程等待与退出码传递。
4. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,...}`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：线程/futex/TLS（`GEM5-026t`）、动态链接（`GEM5-027t`）、文件 I/O/时钟/信号（前序任务）、QEMU、测试用例与期望。

## 验收标准

1. 基线复跑：IPC/socket/pipe 与 process creation 两桶 blocked 归零（或转真实失败并给最小复现）；`qemu_only_fail` 0；`gem5_only_fail` 不新增。
2. 代表案例（`popen`、`spawn`、`daemon-failure`、`socket`、`execle-env`）各 ≥3 次一致；pipe 读写/EOF/EPIPE 抽测。
3. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
4. 反例：把 `pipe2` 改回未实现 ⇒ 代表案例回 blocked；`cp`+`md5sum -c` 还原重建回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- `execve` 依赖 `GEM5-024t` 的 auxv/栈构造；若 `fork` 需要写时复制，先做最小可用（`fork` 复制地址空间）。
- `socket` 只做语料实际使用的最小族，其它显式 `EAFNOSUPPORT`/`ENOSYS`，不得静默成功。

## 完成区

**测试结果**：运行期证据脚本默认模式 **75/75 PASS**（冻结前后两次均为 `SUMMARY pass=75 fail=0`）、`--inject` **24/24 PASS**；独立 guest 探针 `forkprobe` **59/59**（×3 逐行一致）：pipe 阻塞读（handshake 保证空）/阻塞写（70 KB > 64 KiB 容量）/短读/EOF/`EPIPE`/默认 `SIGPIPE` 终止、`O_NONBLOCK`/`O_CLOEXEC`、`fcntl` 协作、fork+`wait4`（`WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`/`WNOHANG`/`ECHILD`）、DADAO 二进制 `execve`；`execprobe`/`forkloop`/`sigpipefork`/`mallocfork`/`enoexecprobe` 全绿。代表例 ×3 一致：`fscanf`/`fgetwc-buffering`/`socket`/`getpwnam_r-crash`/`getpwnam_r-errno`/`daemon-failure`/`fcntl`/`pthread_atfork-errno-clobber` pass；`popen`/`spawn`/`vfork`/`execle-env` 转真实失败（原因为 `ENOEXEC`，见遗留①）。基线 static 复跑 gem5 **pass 418 / blocked 164**（`GEM5-024t` 409/178），IPC/socket/pipe 与 process creation/exec **两桶 blocked = 0**、`qemu_only_fail = 0`；14 例迁出 blocked（9 转 pass、5 转 fail；净 −13 因 `Queens` 由 pass 抖成 blocked）。
**修改文件**：`components/gem5/patches/{configs/dadao/se.py, src/arch/dadao/{se_workload.cc,se_workload.hh,process.cc,process.hh,inst.cc}}.patch`（6 份重导出；其余 91 份 unchanged，共 97 份）、`components/gem5/README.md`、`components/gem5/changelog.md`、本任务书、`.tao/knowledge/milestones.md`。
**验收结果**：`build-gem5` PASS、`check-inst` 44/44 PASS、`check-arch` 14/14 PASS、`check-patch-tree`（7 组件 305 补丁 OK）、`check-source-state`（gem5 `HEAD=b54c7d2` count=1 clean=True）、L1 `make check` PASS、L2 `check-modules` PASS。源 `se_workload.cc` md5 `4f6e4cd501f7493f960d69129ac7eff6`；gem5.opt md5 基线 `45024dbc…`、注入还原重建后 `4aa94bec…`（gem5 内嵌编译时间，重建即变，仅标识；两次构建源码同一 commit）。反例：`case SysPipe2` 改为未实现 → 重建 ⇒ `regression/fgetwc-buffering` `blocked@59`（`inject-diff-nonempty` 非空）→ `cp`+`md5sum -c` 还原 → 重建 ⇒ 探针 59/59 回绿（未用 git 还原）。
**新发现/坑**：① 每个 `ThreadContext` 需要一个 `cpu.workload` 项（`numThreads == len(workload)`），而 `m5.instantiate()` 按 descendants 对同一 Process 反复调 `initState()`（8 TC ⇒ 8 次）⇒ `initState` 必须幂等，否则栈 `mapRegion` 断言；② `PCState::advance()` 是 `pc = npc; npc += 4`：`execve` 后须 `npc = entry`（否则首条指令被跳过），fork 子进程用 `PCState(trap+4)`（否则首条指令执行两次）；`SyscallRetryFault::invoke` 不动 PC ⇒ 天然重执行；③ `loader::createObjectFile` 对打不开的文件是 `fatal`（`ImageFileData`），`execve` 必须先 `stat` 再加载，否则 execvp 的 PATH 探测会 abort 整个仿真；④ `Process::clone` 的 `CLONE_*` 宏来自 `<sched.h>`，`src/sim/process.cc` 未 include ⇒ 恒为 0，不能按 flags 判断"是否真共享"，要比 `child->fds == process->fds`；⑤ 子进程 `rb1 = newsp`（musl `__clone` 把 func/arg 存新栈并读回，不设 SP 会在 `call func` 处跳到野地址）；⑥ 宿主 pipe/socket 的阻塞调用会阻塞**整个模拟器**（对端是另一 guest 进程）⇒ pipe 用 guest 对象 + `SyscallRetryFault`，socket 先 `poll(…,0)`；⑦ 宿主 `fcntl` 记录锁在单宿主进程内无法区分 guest 进程 ⇒ 需 guest 侧锁表；⑧ 引擎按 `DADAO SE: syscall <n> not implemented` **精确**正则分桶，文案插字会把 blocked 误归 `simulator/loader`（曾误伤 16 例 pthread）；⑨ `System::maxPID` 无类外定义，格式化传参 ODR-use ⇒ 链接失败；⑩ gem5 自带 `PipeFDEntry`，自定义 pipe 项须换名避免歧义。
**遗留问题**：① 6 例 `gem5_only_fail`（`popen`/`spawn`/`vfork`/`execle-env`/`unix-smail` + 既有 `bison`）中前 5 例同源：语料/guest 根无 DADAO `/bin/sh`、`echo`，`execve` 返回 `ENOEXEC`（不崩不静默；最小复现 `enoexecprobe`）；QEMU 之所以过是把宿主 x86-64 交给宿主内核执行。真正转绿需 SE 侧 guest root/路径重定向 + DADAO shell，超出本任务范围，建议随 `GEM5-028t`/`INTEG-059t` 裁定。② `llvm-ts lemon` 由 `clone@220`（threads/futex）转为页错误 panic（`pid=101, vaddr=0, pc=0x36374`，mallocng `enframe`），仍 blocked（simulator/loader），非 verdict 回归；SE 页错误不转 guest `SIGSEGV` 属既有平台边界，根因待查（诊断用临时 `warn` 已还原）。③ `CLONE_THREAD` 仍 `fatal`（`GEM5-026t`，threads/futex 20 例）。④ 无 `poll`/`select`/`epoll`、`sendmsg`/`recvmsg`、`waitid`；`SIGCHLD` 只置 pending 不排队；`kill` 唤醒阻塞 syscall 近似 ERESTARTSYS（非精确 `EINTR`）。⑤ 过程留痕：两次基线复跑作废（一次在 llvm-ts 阶段被重建打断、一次驱动被误杀），作废日志已覆盖，最终一次见运行期日志；`run.sh` 首版三处脚本缺陷（case 路径未 slug、无 `SUMMARY` 的探针断言、空桶计数未缺省 0）返工后 `75/75`，`--inject` 首跑因改脚本时仍在执行而中断，重跑 `24/24`。

### 审阅记录 → 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 fork 子进程未设 `rb1 = newsp` ⇒ musl `__clone` 从新栈读 func/arg 读到父栈垃圾，`popen` 在 `call func` 处页错误（vaddr=0） | ✅已修 | `doClone` 对 `newsp != 0` 写 `rb1` | `spawn` 由 abort 变 `posix_spawnp` 返回 `ENOEXEC`；探针 fork 全绿 |
| F2 `execve` 后 `npc = entry+4` ⇒ CPU 的 `advance()` 跳过新映像首条指令（`lemon`/`execprobe` 见 0x2019c 起跑） | ✅已修 | 新增 `entryState.npc(entryPoint)` | `execprobe` 由 abort 变 PASS（DADAO 子进程 exec 后 `execed`/退出 5） |
| F3 fork 子进程 `npc` 误设为 `trap+4` ⇒ 首条 fork 后指令执行两次 | ✅已修 | 改用 `PCState(trap+4)`（npc 自动 +4） | 59/59 探针 + 代表例 ×3 |
| F4 `stat` 缺失时 `createObjectFile` 直接 `fatal` ⇒ execvp 的 PATH 探测 abort 仿真 | ✅已修 | `doExecve` 先 `stat`（`ENOENT`/`EACCES`），再加载 | `spawn` 由 abort 变真实 `ENOEXEC` verdict |
| F5 `unique Process` 被 8 个 workload 项重复 `initState()` ⇒ 栈 `mapRegion` 断言 | ✅已修 | `initialStateBuilt` 幂等守卫 | `fscanf` 等单进程用例从 tick0 abort 变 PASS |
| F6 宿主 `fcntl` 记录锁在同一宿主进程内互相覆盖 ⇒ `functional/fcntl` 失败 | ✅已修 | guest 侧锁表 + `F_GETLK`/`F_SETLK`/`F_SETLKW` + 退出/close 释放 | `fcntl` 转 pass（×3 一致） |
| F7 `RLIMIT_NPROC` 未强制 ⇒ `pthread_atfork-errno-clobber`「fork succeeded despite rlimit」 | ✅已修 | `doClone` 按 live 进程数返回 `EAGAIN` | 该例转 pass（×3 一致） |
| F8 pipe 未区分读/写端、`F_GETFL` 丢访问模式（自审新发现，未被用例触达） | ✅已修 | 读写端 `EBADF`、访问模式入 entry | 重建后 59/59 探针 + 10 代表例 ×3 全绿 |
| F9 `SysClone` 的 `fatal` 文案插入 `(clone)` 破坏引擎分桶正则 ⇒ 16 例 pthread 被归 `simulator/loader` | ✅已修 | 文案改回 `syscall %d not implemented` | 复跑基线 threads/futex 20 / simulator/loader 4 |
| F10 自审：`DadaoPipeFDEntry` 与 gem5 `PipeFDEntry` 同名歧义、`System::maxPID` ODR-use、匿名命名空间声明跨作用域 | ✅已修 | 改名 / 打印 pid / 块移入匿名命名空间 | `build-gem5` 从链接失败变 PASS |

### 审阅记录 → 第 1 轮 reviewer 验收

**重跑记录（reviewer 独立执行，rc = 命令自身退出码；日志留运行期）**
- 门控：`make build-gem5` rc=0；`check-patch-tree` rc=0（7 组件 305 补丁 OK）；`check-source-state` rc=0（gem5 `HEAD=b54c7d2 count=1 clean=True`）；`check-inst` rc=0（44/44）；`check-arch` rc=0（14/14）；`make check` rc=0（L1）；`check-modules` rc=0（L2）。
- 运行期证据脚本独立重跑：`SUMMARY pass=75 fail=0`、exit 0（含 7 门控各自 rc=0、基线断言、11 代表例 ×3 逐条一致）。
- **独立全量基线**（运行期基线目录，gem5.opt md5 `a456c261…` 与门控/脚本同一二进制）：`qemu_pass=587 gem5_pass=417 blocked=165 gem5_only_fail=6 qemu_only_fail=0`；IPC/socket/pipe 与 process creation/exec 两桶**不在 gap_inventory ⇒ 0**；threads/futex 20、simulator/loader 4、SysV IPC 3、time budget 138。与工程侧 418/164 唯一差异 = `Stanford/Queens`（我这轮 120 s 超时；单跑 `pass seconds=119.76` ⇒ 预算抖动，非能力差异）；`gem5_only_fail` 6 行逐条同名同因。
- **独立注入①** `case SysPipe2`→`fatal`（`git diff --name-only`=1）→ 重建 rc=0 → `fscanf`/`daemon-failure`/`fgetwc-buffering` 三例 `blocked` 且理由含 `syscall 59 (pipe2) not implemented`，`functional/socket` 仍 PASS（反例非空且特异）→ `cp` 还原 + `md5sum -c`=OK + `git status` 干净（未用 git 还原）→ 重建 rc=0 → 三例回 PASS。
- **独立注入②** `doWait4` 状态写 `0xff` → `daemon-failure` **FAIL**（`child exited abnormally (signal 127)`）→ 同法还原重建 → 4/4 PASS。
- **自写探针**：socket 边界 6/6（AF_NETLINK/AF_KCM→`EAFNOSUPPORT(97)`、SOCK_SEQPACKET→`ESOCKTNOSUPPORT(94)`、三支持族建成）；fork 拷贝 `forkmem`（3 代顺序 fork + 堆/mmap 逐字节校验 + mallocng churn）3/3 PASS、`forkcow`（父 fork 后整体改写、子仍见旧图样 ⇒ 真拷贝非别名）3/3 PASS。
- **状态/体例**：任务书 `**状态**：待验收` == `milestones.md` 行 `待验收`，`check-milestones-fresh` rc=0；完成区 6 行（≤30）、0 条绝对路径。

**约束核验**：不改测试用例/期望（`git status` 无 `tests/`、`spec/`、`contracts/`）✓；不改 QEMU（`.work/source/qemu` 干净 `ff7aaea`）✓；未 commit/push（HEAD 仍 `b1176813`）✓；改动恰为声明的 10 个文件、6 份补丁重导出且 `check-patch-tree` OK ✓。

**判决：Accepted**（5 条验收标准全部在我自己的重跑下通过）。登记 finding（均不阻断，建议 architect 收尾时处置）：**F1** 完成区「13 例迁出（9 pass+4 fail）」实为**迁出 14 例 = 9 pass + 5 fail**（另 `Queens` pass→blocked 造成净 −13；unix-smail 漏计），文档数字笔误；**F2** `doPipeRead`/`doRecvfrom` 在 guest 缓冲 `EFAULT` 前已消费数据（Linux 不消费；与既有文件读同款模式，语料不可达）；**F3** socket fd 的 `read`/`write` 仍走宿主阻塞调用（会阻塞模拟器；语料只用 sendto/recvfrom/accept，README 未披露）；**F4** `wait4` 对「有其它子进程但目标非子进程」不返 `ECHILD` 而阻塞、`System::PIDs` 不回收（pid 永不复用）；**F5** `execve` 对「存在但不可读」的 ELF 因 `ImageFileData::fatal` 中止仿真（应 `EACCES`）；**F6** 完成区引用 `.work/…` 相对路径（其他任务书不引用，建议只写 `run.sh`/日志名）；**F7** 工程侧 `--inject 24/24` 未原样重跑（以两次独立注入覆盖其机制，记为证据缺口）。

#### 「6 例 gem5_only_fail」归因结论与建议（验收关键项）

**结论：归因成立——这 5 例不是 gem5 能力缺口，而是 QEMU 侧对照口径失真（宿主原生执行），建议按「对照口径问题」登记，不计入 gem5 能力欠账。** 证据（reviewer 亲自 `strace -f -e trace=execve` 跑 QEMU 侧）：`execle-env` → 宿主 `execve("/bin/sh", ["sh","-c","[ \"$VAR\" = abc ] …"], 1 var)=0`；`popen` → `execve("/bin/sh",["sh","-c","echo hello"])`；`spawn` → 在**宿主 PATH**上逐个 `execve`（`~/.qoder/entry/echo`、`~/.local/bin/echo`、`~/.opencode/bin/echo`…）；`vfork` → `/bin/sh -c "exit 0"` / `kill -9 $$`；`unix-smail` → `/bin/sh -c "/bin/lmail 'ALL'"`、`/bin/lmail`、`/bin/smail`。宿主 `/bin/sh`→dash 是 **x86-64 小端 ELF**，guest ELF 是 **DADAO(0xda0) 大端**（`file`/`readelf` 已核）；static 档 driver 的 qemu 命令**不带 `-L`**（仅 dynamic 档设 guest_root），故 guest 绝对路径落到宿主根；仓库内**不存在**任何 DADAO `sh`/`echo`/busybox。gem5 侧行为符合 Linux：非 DADAO 映像 → `ENOEXEC`（`errno=8` / `Exec format error`，5 例一致），最小复现 `enoexecprobe`。
**建议**：① 把这 5 行登记为**环境/guest root 缺口**（需 DADAO shell/echo + SE 路径重定向，随 `GEM5-028t`/`INTEG-059t` 裁定），并在对照口径上标注「QEMU 该行非同架构 baseline」；② 该 5 行保留在 `run.sh` 的 `documented` 白名单内（已按现场 JSON 断言，非写死通过）；③ 第 6 行 `bison` 是 `GEM5-023t` 既有捕获模型差异，与本任务无关。**不建议**为凑绿而给 gem5 加「宿主原生执行」旁路（会破坏 ADR-0048「SE 只与 QEMU user 对照」的前提）。

#### 收尾（architect，2026-11-07）

- 5 例 `gem5_only_fail`（`popen`/`spawn`/`vfork`/`execle-env`/`unix-smail`）经 reviewer `strace -f` 证实：QEMU 把 `execve` 交给宿主内核执行 **x86-64** 二进制（宿主 `/bin/sh`），属**非同架构 baseline**；SE 按 Linux 返回 `ENOEXEC` 正确。登记为**环境缺口**（guest 根无 DADAO shell），不计 gem5 能力欠账；不采纳「宿主原生执行」旁路。
- 第 6 行 `bison` 为既有 stdout/stderr 捕获模型差异。
- 收尾修订：完成区迁出数改 14（9 pass + 5 fail）；README 补 socket fd 阻塞、`wait4` 非子进程、pid 不复用、`execve` 不可读 ELF、`EFAULT` 先消费等限制，并写明环境缺口与 QEMU baseline 失真。
- `lemon` 页错误 panic 为既有平台边界（`GenericPageTableFault`），前后均 blocked，另立诊断任务定位。
- 基线：gem5 pass 409→418、blocked 178→164；IPC 与 process-creation 两桶清零；`qemu_only_fail=0`。
- 判决 Accepted，状态置 `已验证`。
