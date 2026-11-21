# m14-linux-023: 用户态 syscall 闭环（umon 入口 + 分发表 + errno + TLS 用户面）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（最小 U-mode 入口骨架）、`m14-linux-017`（init 真跑 + 最小 clockevent）、`m14-linux-020`（kernel_thread/kthreadd）——均为 **K4 收口**前置
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/trap.S`/`syscalls.c`/`process.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：4–6 h（syscall 分发/返回路径 + errno + TLS 入口保存恢复）
**档位**：大改（syscall 闭环核心路径 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：已验证

## 背景

`016` 做了最小 U-mode 入口骨架（`cfx_umon` user 行路由 + 单帧），`017` 做到「init 真跑」（`kernel_init` → initramfs `/init`）。本任务让静态 musl `init` 能**发起 syscall 并正确返回**，形成「用户态 → trap → 内核 → escape → 用户态」闭环。`syscall_table.c` 的分发表已由 K0 建好（asm-generic 号表）；本任务补齐**入口参数解析 / 分派 / 返回 / errno / TLS**。

DADAO 特有事实（`contract-syscall §2/§3/§8/§9/§10`，**不得偏离**）：
- 用户 syscall = `trap cfx_umon, 0`（`SBI_UMON_SYSCALL`）；`rd15 = nr`、参数 `rd16–31`/`rb16–31`/`rf16–31`（三组独立计数、自 16 起）、返回 `rd8`（`§3`）。
- 入口帧：硬件只存 cg5 **六**字段（`excp_prev_run_mode`/`excp_prev_cfx_code`/`excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_pending`；第 2 项由 `m14-spec-009` 于 2026-11-18 加入，`contract-syscall §8` 同笔更新），**不存通用寄存器**；`excp_cause_id == 1<<0`（`CFXTRAP`）、`immu18 = excp_cause_info & 0x3FFFF`（`§8` 合约内推导）。
- **errno = `rd8` 负值（`-errno`），`[-4095, -1]`**；不支持返回 `-ENOSYS`、参数错返回对应负值；**不用 `rd1`**（`§9`）；内部重启码（`ERESTARTSYS` 等）不得外泄。
- **TLS**：`rb3 = rbtp`（thread pointer），保留不分配、跨 syscall 保持 ⇒ 入口保存、返回恢复（`§10`）。
- 返回 = `escape cfx_umon, [excp_cause_ip, 4]`（落回 `trap` 下一条）；`escape` 的 `cfxha` 必须 = 当前 cfx（`cfx_umon`），帧/目标错 ⇒ `CFXESC`。

## 目标

1. **umon 入口完整**：`kernel/trap.S` 的 umon 向量接 syscall 路径——保存用户态 `pt_regs`（4 组 rd/rb/ra/rf，`m14-linux-022` 帧布局）、按 `rd15` 查 `sys_call_table` 分派、返回前恢复。
2. **参数/返回**：`arch/dadao` 侧 `syscall_get_nr`/`syscall_get_arguments`/`syscall_set_return_value`（`asm/syscall.h`）落地——`nr=rd15`、参数从 `rd16/rb16` 起、返回值写 `rd8`（`§3`）。
3. **errno**：错误路径写 `rd8 = -errno`（`[-4095,-1]`）；`-ENOSYS`/`-EINVAL` 等；`ERESTARTSYS` 类内部码在返回用户态前转 `-errno` 或重试（`§9`）。
4. **TLS 用户面**：入口保存 `rb3`、返回恢复；`execve` 清 0（实现点见**待裁定 1**）；`rb3` 不作传参/临时（`§10`）。
5. **返回用户态**：`ret_from_syscall` 恢复用户态寄存器、`escape cfx_umon, [excp_cause_ip, 4]` 落回；`TIF_*` 工作（reschedule/signal）预留钩子（信号归 `027`）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_syscall_probe.py` rc=0，逐 case 打印；期望值现场派生（号表 ← `contract-syscall §1.2` 锁定快照、寄存器 ← `contract-abi §4`、errno ← `contract-syscall §9`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `U1 write 往返`：用户态 `write(fd, buf, n)` ⇒ 经 umon 分发、返回 `n`（非负）、输出正确。
   - `U2 exit 往返`：`exit(0)` ⇒ 正常退出（宿主 rc=0 / `SYS_EXIT(0)`）。
   - `U3 errno 形态`：不支持号返回 `-ENOSYS`、参数错返回 `-EINVAL`（`rd8` 负值、∈ `[-4095,-1]`，**非** `rd1`）。
   - `U4 TLS 保持`：`rb3` 跨多次 syscall 不变（现场哨兵值）；`write` 返回后 `rb3` 仍 = 入口值。
   - `U5 帧字段`：`excp_cause_id == 1<<0`、`excp_prev_run_mode == user(0)`、`excp_cause_ip == trap` 地址、`immu18 == info & 0x3FFFF`（`§8`）。
3. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：① 不恢复 `rb3` ⇒ `U4` 红；② 返回写 `rd1` 而非 `rd8` ⇒ `U3` 红；③ `immu18` 解析错（取错位段）⇒ `U5` 红；④ 错误返回 `-1` 而非 `-errno` ⇒ `U3` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）、`k4_switch_probe.py`（017）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-023/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{trap.S,syscalls.c,process.c}.patch`、`components/linux/patches/arch/dadao/include/asm/{syscall.h,ptrace.h}.patch`、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k5_syscall_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k5_syscall_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §2/§3/§8/§9/§10` + `contract-abi §4` 为准；**不得**套 RISC-V `a0–a7`/x86 寄存器约定；`rd15` 是号、`rd16/rb16` 起参数、`rd8` 返回。
5. 单帧、不递归（同 cfx 嵌套留 K5，`016` 口径）；`escape` 后补投由硬件完成（`contract-see §6.5`）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~**`execve` 清 0 的实现点**~~ **已裁定（用户 2026-11-17，选 A）**：**内核 `execve`/`start_thread` 清 `rbtp = 0`**（对齐 x86-64 `loadsegment(fs,0)` / ARM64 `tpidr_el0=0`；RISC-V/MIPS 是内核不清、由 libc 校准的反例）。`m14-linux-016` 的 `start_thread` 已实现；本任务只负责把它写成验收断言（`execve` 后用户态首条指令处 `rb3 == 0`）并加注入（改回不清 ⇒ 红）。musl 侧不重复清。

## 审阅记录

### 第 1 轮 engineer 自审（逐行、自主）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 表项实为 `__se_sys_*`（`__SC_LONG` 把每个参数压成 `long` 顺序传），与按类型分库的用户 ABI 不符 | ✅已修 | 新增 `asm/syscall_wrapper.h` + `select ARCH_HAS_SYSCALL_WRAPPER`，`sys_<name>` 保留声明类型 | 修前 `write` 返回 0（count 落在 rd18=0）；修后 U1 返回 12、文件 12 字节内容一致 |
| F2 `asm/syscall_table.h` 的 include guard 让「先声明、再建表」两趟包含的第二趟失效 ⇒ 表项全落 `sys_ni_syscall` | ✅已修 | 去掉该头的 include guard（与 arch/riscv 同形） | 修前 ELF 里 `sys_call_table[64] == sys_ni_syscall`、`write` 返回 -ENOSYS；修后探针静态断言表槽 == `sys_*` 符号 |
| F3 用户缓冲区用 `vm_private_data` 供货 ⇒ 读到全零（`mm/fault.c` 只在**取指**读该字段） | ✅已修 | 缓冲区改文件后备（`/k5msg` + `fill-file`），产物再与源文件比对 | 修前 `u1_file_content` 全错（0xfff）；修后 0 |
| F4 运行态 `schedule()` 在无 tick 镜像里不会轮转（vruntime 冻结） | ✅已修 | 交接改为阻塞在完成量 `k5_child_exit`，不依赖 tick | 修前 10000 次 `schedule()` 子任务未运行；修后 `rounds=0`、连续两轮 49/49 |
| F5 `kernel_wait4()` 带不回状态（`put_user` 拒内核地址；`WNOWAIT` 不在其白名单） | ✅已修 | 改 `exit_state == EXIT_ZOMBIE` + `exit_code` 轮询（不 reap） | U2 三条断言 ok |
| F6 C 半与 post 各写一次 `rd8` | ❌不修 | post 需按 §9 归约后再写（重启码→`-EINTR`），两次同值且语义清楚 | U3/U6 ok |
| F7 `syscall_get_arguments()` 只能给数据库前 6 槽 | ⏸记录 | 头注释写明：M14 未开 audit/trace，混合类参数须按库读帧 | — |
| F8 一次被强杀的后台运行把注入残留在源码树（`rd[1] =`） | ✅已修 | 复原 + 新增静态断言「rd1 不参与 syscall 路径」，该断言当场抓到残留 | 复原后 md5 == 注入前记录值；断言转 ok |
| F9 注入轮次的「桩未变」检查比对了 `immu18` 立即数 | ✅已修 | 只比对 trap 位置（`immu18` 的错位正是注入要制造的现象） | 全量复跑 79/79 |

**判决**：9 条 finding 全部有处置（6 修 + 1 判不修并说明 + 1 记录 + 1 修后复验），无未修项；`run.sh` 15/15 PASS ⇒ 可标「待验收」。自审另核对：`dadao_call_syscall` 只碰 caller-saved 参数库与保留寄存器（`rb3`/`rd2`/`rb5`），`dadao_umon_busy` 只护分派窗（系统调用本体可睡眠/换任务），探针静态断言与 `run.sh` 的计数均现场派生、无恒真项。

### 第 1 轮 reviewer 验收（大改档：独立重跑 + 4 路注入，2026-11-19）

**重跑记录（我自己的命令与真实退出码）**
1. 运行期证据目录内 `run.sh`：首跑在 `check-linux-k3` 阶段被外部杀掉（19:34 中断，非交付物缺陷，有据重跑 1 次）；后台重跑 `./run.sh gates k4 tree` ⇒ `SUMMARY checks=11 fails=0`、`RC=0`：`check-linux-k0/-k1/-k2/-k3` 均 rc=0；`k4_fork 104/104`、`k4_cow 86/86`、`k4_stack 44/44`、`k4_switch 76/76`、`k4_kthread 110/110`；`check-config-pins` rc=0（76 项 0 失败，切片脚本 16 个 / Kconfig 符号 18 个，15 个既有门控脚本均补 `CONFIG_DADAO_K5_SYSCALL_SELFTEST=n`）。
2. `python3 tools/linux/k5_syscall_probe.py`（跑齐其 5 路注入）⇒ `k5_syscall_probe: 79/79 passed`、0 FAIL、注入 `red=5 green=5` 且每路 `cp`+md5 对账一致；控制台 29 条 `K5 check` 全 `ok`、`K5 exit: ... code=0`；完成区所贴 `u1_write_ret want=0xc got=0xc ok`、`u3_range_enosys want=-38 got=-38`、`u4_user_rb3 want=0x4b35544c53000001`、`u7_exec_rbtp_zero want=0x0 got=0x0` 与我这次输出逐字一致（非转述）。
3. **U5 的 trap 列表确为现场派生**：`stub oracle (from the built image): [(0x0,0x0),(0x10,0x0),(0x1c,0x0),(0x40,0x0),(0x48,0x1),(0x50,0x2aaa),(0x5c,0x2aab),(0x68,0x0)]` —— 取构建产物 `.rodata` 字节交 `llvm-mc --disassemble` 解码，非写死。
4. **我的 4 路注入**（前两路不在其 5 路内）：① `dadao_call_syscall` 数据参数库整体 +1 格（`write` 的 count 改从帧 rd18 取）⇒ `RC=1`，红 `u1_write_ret/u1_file_bytes/u3_mmap_einval`、宿主 rc=99；② 返回 `escape cfx_umon,[excp_cause_ip,4]`→`0` ⇒ `RC=1`（`28/42 passed, 14 FAILED`，U1–U7 断言全缺、退出观察行缺失）；③④ `result-to-rd1`、`no-rb3-restore` 在我重跑的其 5 路中各自红 → `cp`+md5 → 重建 → 回绿。①②首次还原后仍红：我用 `cp -p` 保留了旧 mtime、make 未重编（reviewer 侧过程问题，非交付物缺陷）；`touch` 后重建 ⇒ `RC=0`、`k5_syscall_probe: 49/49 passed`、0 FAIL，`trap.S` md5 == 注入前 `45c30809…`。
5. **合并态（`Process-07 §5a`）**：`git merge --no-commit master` rc=0（15 文件，与本任务 32 文件零重叠）⇒ `make check-config-pins` rc=0（76/0）、`make check-patch-tree` rc=2（**8 项全在 chipyard**，gem5 的 10 项随合并消失）；`git merge --abort` rc=0，HEAD 仍 `e97c0716`、`git status` 0 行、15 文件 md5 与合并前逐一相等。

**约束核验（逐条）**
- 证据脚本审计：`run.sh` 每条 `report()` 捕获被检命令**自身**退出码（无 `| tee` 吞码）、覆盖数 `grep -c` 现场计数且 `>=60`、注入按 `red>=4 && green>=4` 计数、`selfcheck` 无红项即 rc=1 ⇒ 各断言有可达 FAIL 路径；唯一收窄是 `check-patch-tree` 改判「linux 问题数=0」而非门控 rc（完成区已披露）——与验收 4 的字面 `rc=0` 不一致，见失败 1。
- 契约硬点 1–4 全守住：`rd15`=号、`rd16–31`/`rb16–31` 分库、返回 `rd8`、errno ∈ `[-4095,-1]`、`rd1` 全程哨兵 `0x4b354552524e4f31` 不变；`trap cfx_umon,0` 入口、硬件只存 cg5、通用寄存器由软件补齐；`immu18 = info & DADAO_IMMU18_MASK(0x3ffff)`；返回 `escape cfx_umon,[excp_cause_ip,4]`（cfxha = 当前 cfx）；`rb3` 入口存 `frame.rb[3]`、返回末位 `ld.o rb3,[rb3,PT_RB_BASE+3*8]`，7 条 trap 的 rb3 恒 `0x4b35544c53000001`；`ERESTART*` → `-EINTR`（U6 `0xfffffffffffffffc`）。
- `dadao_call_syscall` 成立：`rb16–31`/`rd16–31`/`rb5` 为 caller-saved、`rb3`/`rd2` reserved（contract-abi §4.5/§4.6）⇒ 装回后 `call` 合法且 C 侧不可能在 rb3 留值；`ra` 由 `call/ret` 管、`rf` 与 CSR（rd32–63/rb32–63/rf32–63）由内核 callee 自存、用户侧由 `DADAO_GPR_RESTORE_AT` 整体还原；`set.rb rb3,0` 只在调用窗内、返回路径从帧重载 ⇒ 无错误恢复。
- 去 `__SC_LONG` 的 ①③ 成立：`select ARCH_HAS_SYSCALL_WRAPPER` 只写在 `config DADAO`、头文件在 `arch/dadao/`，改动全落本架构；asm 入口没有更小做法（类型分库无法按位置重建），typed→`__se_sys` 的重排 shim 体量相当、只多保留 32 位消毒，取舍等价。
- 范围与纪律：32 文件全在 `components/linux`/`tools/linux`/任务书；未触 `spec/`、`.tao/contracts/`、`tests/`、`components/qemu/`、`Makefile`；`components/linux/series` 未列入硬约束 2 的预计清单（补丁登记必需、完成区已披露）⇒ 判非越界；全程无提交（HEAD `e97c0716` 未变）。
- 文档小错（不阻断，交 architect 收尾改）：任务书「cg5 **五**字段」按 contract-syscall §8（2026-11-18 `m14-spec-009`）应为**六**项（增 `excp_prev_cfx_code`）。

**阻断项（关键决策②不成立，需裁定）**
- `sys_<name>` 保留类型后与 musl **只对一半**：musl `__dadao_argmask` 对其自列的「例外族」按**用户态原型**放地址参数，内核却把这些参数声明成 `unsigned long`/`long` ⇒ 按类型分库落 `rd16+`。逐条对过内核声明的错位 **15 个号**：`brk/mmap/munmap/mprotect/mremap/mlock/munlock/mlock2/madvise/msync/mincore/remap_file_pages/ioctl/ptrace/semctl`（例：`mm/mmap.c: SYSCALL_DEFINE1(brk, unsigned long, brk)` ↔ musl `case SYS_brk → 0x01` = rb16；`fs/ioctl.c: … unsigned long, arg` ↔ musl `0x04` = rb16）。
- **活的受害例**：MVP init 的 `brk`（`tests/shared/init/init.c` 以 `syscall(SYS_brk,(void*)addr)` 调用）——musl 送 rb16、`rd16=0`，内核恒读 0 ⇒ 增长失效、init 将以 exit 4 失败；当前 `/init` 已换成 busybox 脚本，故无门控暴露。
- **覆盖缺口**：`tools/qemu/check_syscall_abi.py` 只比 musl/QEMU/gem5/syscall_cp 四个载体、**不含内核**；k5 探针的用户桩是手写寄存器布局、看不到 musl 形状 ⇒ 该错位今天任何门控都抓不到。
- 待裁定：改内核声明（地址参数改指针类型）还是改 musl 例外族，以及是否补「musl argmask ↔ 内核 `SYSCALL_DEFINE` 类型」门控。

**判决：Needs Revision**
- 失败 1：验收 4 的 `make check-patch-tree rc=0` —— 我的重跑 rc=2、合并态仍 rc=2（剩 chipyard 8 项；归因：那 4 个补丁文件正是本分支与并行任务分支 `m16-chipyard-006`(`edcc5113`) 的全部差异，共享源码被其占用；linux 89 补丁 0 问题）⇒ 验收块未在我重跑下全绿。
- 失败 2：关键决策②（`sys_<name>` 声明原型与 musl 侧调用形状一致）不成立，见上；硬约束 4「语义以 contract-syscall §3 为准」在**系统层**未满足。
- 次要 finding（交 architect 收尾改）：`immu18-wrong-mask` 注入命中的是 process.c **第一处**（K5 观察块）而非分派处，分派位段解析无运行期判据（静态断言仅查文本存在）；「cg5 五字段」应为六；`series` 未列入预计清单。
- 其余全通过：探针 79/79、4 路注入红→还原→回绿、k0–k3 与 k4×5 不回归、`check-config-pins` 76/0、合并态除 chipyard 外 0 问题、U5 现场派生、无越界、无提交、审阅记录无运行期路径。


### 第 2 轮 engineer 自审（返工 1：C′）

**返工依据**：第 1 轮 reviewer「Needs Revision」+ 用户裁定 C′（2026-11-19，原话「可以」）：恢复内核通用链 `__SC_LONG`、入口按 argmask 取参、内核纳入 `check_syscall_abi.py` 作第 4 载体。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 失败 2（阻断）：`sys_<name>` 保留声明类型 ⇒ `brk`/`mmap`/`ioctl`/`ptrace`/`semctl` 等 18 个号的**地址参数落进数据库**，与 musl 的 argmask 不一致（受害者：`/init.musl` 的 `brk` 读到 `rd16=0`，增长失效、exit 4） | ✅已修（C′） | `asm/syscall_wrapper.h` 改回通用链（`__SC_LONG`→`__se_sys_*`→`__SC_CAST`→`__do_sys_*`），入口 `sys_<name>(regs)` 用 `dadao_syscall_arg(regs, i)` 按 argmask 取位置参数；新增 `kernel/syscall_argmask.c`（173 行，`[nr] = mask, /* name */`）；`trap.S` 的 `dadao_call_syscall` 退化为「帧在 `rb16`、`rb3=0`、`call`、`ret`」 | 实测 `/init.musl` 输出 `init: pid=1`、`init: brk +65536 ok`、`K5 init: exit=0`；U8 五项 ok（`mm->brk` 与新建 VMA 同时核） |
| R2 覆盖缺口：`check_syscall_abi.py` 不含内核载体 ⇒ 该错位任何门控都抓不到 | ✅已修 | 该门控新增「内核行」解析（`[nr] = mask, /* name */`）+ 与 musl 非零行集合逐号比对 + 行注释↔号一致 + 掩码 1..6 位 + 入口宽度常量；`run.sh` 新增 `abi` 阶段并做**门控级注入**（只改内核 `[214]` 一行 ⇒ 红，`cp`+md5 还原 ⇒ 回绿） | `check-syscall-abi` 86/86；注入后 rc=2（红）、还原后 md5 `d98077c9…` 一致、回绿 rc=0 |
| R3 次要：`immu18-wrong-mask` 注入命中的是第一处（观察块）而非分派处 | ✅已修 | `process.c` 把 `immu18` 解析收敛到**一处**（分派入口、K5 观察块之前），观察与分派读同一值 ⇒ 注入必然命中分派位段 | 注入后 `u5_trap_immu18` 红、还原后回绿 |
| R4 次要：任务书「cg5 五字段」应为六 | ✅已修 | 背景段改为**六**字段并注明 `excp_prev_cfx_code`（`m14-spec-009`，2026-11-18） | 本轮门控与 `contract-syscall §8` 对齐 |
| R5 次要：`series` 未列入预计改动清单 | ✅披露 | `components/linux/series` 属补丁登记必需（一文件一补丁），已在完成区列出 | `check-patch-tree` linux 90 补丁 0 问题 |
| R6 自审发现：被强杀的后台运行会把注入残留在源码树（本轮两次：`rd[1]`、`[222]`） | ✅已修 | 复原后重生成补丁并 `--amend`；流程上加「amend 前先 `git status` 核对」；探针的静态断言（`rd1 不参与 syscall 路径`）与门控的 md5 对账各自抓到过一次 | 源码树 `git status` 0 行、`base+1`；`check-patch-tree` linux 0 问题 |

**判决**：R1–R6 全部处置（6 修/披露），无未修项；`run.sh` 19/19 PASS（含 7 路注入与门控级注入）⇒ 可标「待验收」。

### 第 2 轮 reviewer 验收（返工 C′：大改档，独立重跑 + 2 路注入，2026-11-19）

**重跑（我自己的命令与真实退出码）**
1. 运行期证据目录内 `run.sh`（probe/gates/k4/abi/tree 五阶段）⇒ **`SUMMARY checks=19 fails=0`、`RUNSH_RC=0`**：`probe-all` rc=0、`probe-check-count checks=104 fails=0`、`probe-injections red=7 green=7`；`check-linux-k0/-k1/-k2/-k3` 全 rc=0；`k4_fork 104/104`、`k4_cow 86/86`、`k4_stack 44/44`、`k4_switch 76/76`、`k4_kthread 110/110`；`check-syscall-abi` rc=0（`86/86`）、其门控级注入 `actual=2`、还原 md5 `d98077c9…` 一致且回绿 rc=0；`check-config-pins` 76 项 0 失败；`check-patch-tree` `linux: 90 patch(es)`、`linux_problems=0`。
2. `python3 tools/linux/k5_syscall_probe.py` ⇒ **`k5_syscall_probe: 104/104 passed`**、0 FAIL；7 路注入红项精确到 case：`argmask-brk`→`u8_brk_grow/mm/vma`、`argmask-mmap`→`u3_mmap_einval`、`no-rb3-restore`→`u4_*`、`result-to-rd1`→`u3_rd1_sentinel/u6_*`、`immu18-wrong-mask`→`u5_trap_immu18`、`errno-minus-one`→`u3_range_enosys`、`exec-keeps-rbtp`→`u7_exec_rbtp_zero`（宿主 rc 99–104），每路 `cp`+md5 还原后回绿。
3. **brk 端到端（返工判据，我这次跑出的控制台原文）**：`K5 check u8_brk_read want=0x10000500000 got=0x10000500000 ok`、`u8_brk_grow want=0x10000510000 got=0x10000510000 ok`、`u8_brk_recheck`/`u8_brk_mm` 同值 ok、`u8_brk_vma want=0x1 got=0x1 ok`；随后 `K5 init: enter /init.musl pid=1` → `init: pid=1` → **`init: brk +65536 ok`** → **`K5 init: exit=0`**；34 条 `K5 check` 全 ok、0 FAIL。
4. 内核 argmask 非零行**我现场数 = 173**，与门控 `173 equal / 0 unequal` 一致；抽验 `[29]=0x04 ioctl`、`[117]=0x0c ptrace`、`[191]=0x08 semctl`、`[214]=0x01 brk`、`[222]=0x01 mmap` 与 musl 同号同值。
5. 合并态：分支已 `merge master`（`cfc04cbc` ⊇ `80afb692`）；master 其后仅 `cffd63d6`（4 个 `.tao` 文档文件，无门控输入）⇒ 无影响。

**我的 2 路注入**（均不在其 7 路内；`cp`+md5 还原）
- ① 内核表 `[29] = 0x04`→`0x00`（门控级）：`python3 tools/qemu/check_syscall_abi.py` ⇒ **rc=1**、`[FAIL] kernel routing mask 29 ioctl: musl=0x04 kernel=0x00` + `173 equal actual=1 unequal` + `masks are 1..6 bits wide ['29: 0x00']`、`84/86`；`make check-syscall-abi` ⇒ **rc=2**；还原 ⇒ md5 OK、**rc=0、`86/86`**。
- ② `dadao_syscall_arg()` 的 `addr_before = hweight32(…)` → `addr_before = i`（`hweight32` 留在注释里，静态文本断言不背锅，红只能来自运行期）：`--no-inject` ⇒ **rc=1**、`57/62 passed, 5 FAILED`，红 `u1_write_ret`/`u1_file_bytes`（write 的 buf 落 rb17）+ U8 三行 init 输出缺失 + 宿主 rc=97（U1 失败即中止）；`cp`+md5+`touch` 重建 ⇒ **rc=0、`62/62 passed`、0 FAIL**。

**约束核验（C′ 四条逐条独立验）**
- ① 通用链已恢复：`syscall_wrapper.h` 为 `__SC_LONG → __se_sys_* → __SC_CAST → __do_sys_*`，入口 `sys_<name>(const struct pt_regs *regs)`；`dadao_syscall_arg(regs,i)` = 位 i 置位取 `rb[16+hweight32(mask&(2^i-1))]`、否则取 `rd[16+i-该 popcount]`，与 contract-syscall §3「三组各自自 16 起、按类型分库」等价；`trap.S` 的 `dadao_call_syscall` 已退化为「帧在 rb16、rb3=0、call、ret」，不再装回参数库。
- ② 内核表 173 行与 musl/QEMU/gem5/`syscall_cp.s` 逐号一致（门控 docstring 已明列内核作第五载体）；文档列的例外族（`brk`/`mmap`/`munmap`/`mprotect`/`ioctl`/`ptrace`/`semctl`…）按用户态原型置位。
- ③ 门控可 FAIL 且我复现：见注入①（脚本 rc=1 / `make` rc=2 / 还原 rc=0）。
- ④ U8 五项 + 端到端两行输出见重跑 3；init 阶段的 `write`/`exit_group` 走探针 shim（本镜像 initramfs 无 `/dev/console`，完成区已披露），而 U1/U2 覆盖真实 `sys_write`/`sys_exit_group` ⇒ 不构成绕过。
- 契约硬点不变量仍守住：`rd15` 号、返回 `rd8`、`rd1` 全程哨兵不变、`immu18 = info & 0x3FFFF` 已收敛为**单点解析**（process.c 第 526 行，观察块与分派共用 ⇒ 第 1 轮 R3 已消）、`escape cfx_umon,[excp_cause_ip,4]`、`rb3` 入存返复、`ERESTART*`→`-EINTR`。
- 范围/纪律：本任务 34 文件（31 改 + 3 新），未触 `Makefile`/`components/qemu/**`；`tools/qemu/check_syscall_abi.py`（验收 3 要求的门控扩展）与 `components/linux/series`（补丁登记）均在完成区披露；HEAD `4e4a7daf` 未变、我全程无提交；linux 源码树 `git status` 0 行、注入残留已清。

**判决：Accepted**
- 第 1 轮两个失败项均已消：musl↔内核 15 个号的错位由 C′ 修复并有端到端实测（`init: brk +65536 ok`）+ 五载体门控守住；`check-patch-tree` **linux 段 90 补丁 0 问题**（全仓 rc=2 归属见下）。
- 验收 1–5 全绿（104/104、U1–U8、7 路注入、k0–k3 + k4×5 不回归、config-pins 76/0、完成区 30 行无运行期路径）；我的 2 路注入红→还原→重建→回绿。
- 记 finding 交 architect 收尾改（均不阻断）：① 完成区/第 2 轮自审写「8 项全在 chipyard」，我实测全仓 **15 项 = chipyard 8 + gem5 7**（gem5 源码树 7 个文件 22:19–22:20 被并行任务改脏，`assertion ⑦ worktree is not clean`），linux 仍 0 问题；② `run.sh` 的 `foreign=` 正则 `[a-z]+` 漏掉含数字的组件名（`gem5`），只报出 chipyard；③ 措辞三处：完成区标题「四载体门控」、第 2 轮自审「第 4 载体」、门控 docstring「The three tables must agree」——实际为五载体。

## 完成区

**返工 1（C′：恢复 `__SC_LONG` + argmask 取参 + 四载体门控）+ `brk` 实测**

**测试结果**：运行期证据目录内的 `run.sh` **19/19 检查 PASS、rc=0**（合并态，含 `abi` 阶段）：k5 探针 104/104、7 路注入全「红 → `cp`+md5 还原 → 回绿」；`check-linux-k0` 130/130、`k1` 112/112、`k2` 170/170、`k3` 263/263；`k4_fork` 104/104、`k4_cow` 86/86、`k4_stack` 44/44、`k4_switch` 76/76、`k4_kthread` 110/110；`check-syscall-abi` 86/86 **且其内核行单独注入 ⇒ rc=2 红、还原 ⇒ 回绿**；`check-config-pins` 76 项 0 失败；`check-patch-tree` linux 90 补丁 0 问题（外组件 chipyard 8 项为他任务在途）。

**修改文件**（34 项：31 改 + 3 新）：
- 组件补丁（12 改 + 3 新）：`arch/dadao/{Kconfig,Kconfig.debug}.patch`、`include/asm/{setup.h,syscall.h,syscall_table.h,syscall_wrapper.h}.patch`、`kernel/{Makefile,process.c,setup.c,syscall_table.c,syscalls.c,trap.S,k5_syscall_selftest.c}.patch` + 新 `kernel/syscall_argmask.c.patch`
- `components/linux/{series,changelog.md}`
- `tools/qemu/check_syscall_abi.py`（内核作第 5 个比对载体）+ `tools/linux/k5_syscall_probe.py`（新；U8/init/argmask 静态核对/7 路注入）+ 15 个既有门控脚本的 `CONFIG_PINS` 补 `CONFIG_DADAO_K5_SYSCALL_SELFTEST`
- 本任务书（状态/裁定段/两轮自审/完成区）

**验收结果**（真实输出摘录）：
- `k5_syscall_probe: 104/104 passed`；`u8_brk_read want=0x10000500000 got=…`、`u8_brk_grow want=0x10000510000 got=…`、`u8_brk_recheck`、`u8_brk_mm`、`u8_brk_vma want=0x1 got=0x1` 全 ok
- **`brk` 实测（返工判据）**：控制台 `init: pid=1` / **`init: brk +65536 ok`** / `K5 init: exit=0` —— 真 `/init.musl` 经真分派跑完，`brk` 走 `rb16` 并成功增长一页
- 注入：`argmask-brk`→`u8_brk_grow/mm/vma` 红；`argmask-mmap`→`u3_mmap_einval` 红；`no-rb3-restore`→`u4_*`；`result-to-rd1`→`u3_rd1_sentinel/u6_*`；`immu18-wrong-mask`→`u5_trap_immu18`；`errno-minus-one`→`u3_range_enosys`；`exec-keeps-rbtp`→`u7_exec_rbtp_zero`；每路还原后无红项且宿主 rc=0
- `check-syscall-abi`：`kernel routing: same number set as musl (non-zero rows)` ok、`173 equal / 0 unequal`、`86/86 checks passed`；注入后 `rc=2`
- `check-patch-tree: linux: 90 patch(es)`，无 linux 问题行

**新发现/坑**：
- **argmask 是入口唯一可用的路由信息**：`__SC_LONG` 把参数展平成位置序列，而本端口按类型分库，槽位只能由「第 i 个位置是不是地址」决定 ⇒ 该表须是**内核自有**的一份拷贝、与 musl/QEMU/`syscall_cp.s`（及既有 gem5 拷贝）逐号一致；18 个「内核原型写成 `unsigned long`」的号只能按用户态原型置位。另：`asm/syscall_table.h` 带 include guard 会让「先声明、再建表」的两趟包含静默失效（表项全落 `sys_ni_syscall`、所有 syscall 返回 `-ENOSYS`），只能靠从 ELF 读 `sys_call_table[nr]` 抓到。
- 运行态 `schedule()` 在无 tick 镜像里不会轮转（`sched_clock()` 是 jiffies 基，独立时钟源属 m14-linux-021）⇒ 多任务探针必须**阻塞交接**。`mm/fault.c` 只在**取指**分支读 `vm_private_data` ⇒ 数据页用文件后备。`kernel_wait4()` 带不回状态（`put_user` 拒内核地址、`WNOWAIT` 不在白名单）⇒ 读 `exit_state`/`exit_code`。
- `brk` 的增长路径要求「要新增的页原本没有 VMA」，否则 `sys_brk()` 走 early-exit（探针把数据窗口末尾放在初始 break 上）；让 `/init.musl` 的输出上屏还需给 `write` 一个 shim（本镜像 initramfs 无 `/dev/console`）。
- **被强杀的后台运行会把注入残留**（本轮两次），`md5`/静态断言各自抓到一次；收尾前必须先 `git status` 核对源码树再 `--amend`。

**遗留问题**：
- `check-patch-tree` 全仓 rc=2：linux 段 0 问题；8 项全在 **chipyard**（他任务在共享工作根里的在途状态，按 mtime/归属判、不代删不凑绿）。`run.sh` 按组件统计后判 PASS。
- `syscall_get_arguments()` 只给数据库前 6 槽（M14 未开 audit/trace；混合类参数须按库读帧，已写进头注释）。
- `ERESTART*` 的真重试、`clone`/`futex` 用户面验证属 027/后续；本任务只保证内部码不外泄。
- `execve` 后 `rb3 == 0` 以 `task_pt_regs()` 帧为准（未进入新映像）；新映像真正跑起来由 init/busybox 任务覆盖（本轮已让 `/init.musl` 跑到 `exit_group`）。
