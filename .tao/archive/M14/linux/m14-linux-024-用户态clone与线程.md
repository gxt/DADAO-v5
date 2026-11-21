# m14-linux-024: 用户态 clone/线程（CLONE_VM / CLONE_SETTLS / CLONE_THREAD + TLS 用户面）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-023`（syscall 闭环）、`m14-linux-020`（kernel_thread/copy_process 共享路径）、`m14-linux-016`（copy_process/dup_mm）
**可并行分片**：否（`components/linux` 单写者；共享 `kernel/process.c`/`syscalls.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：3–5 h（`clone` 是 `fork` 的 flag 扩展 + TLS 设置）
**档位**：大改（用户可见 clone 语义 + TLS；复核 ≥4 路注入）
**状态**：已验证

## 背景

`020` 只做内核线程（`kernel_thread`，`CLONE_FS|CLONE_FILES`、`mm == NULL`），把用户态 `clone` 交接给 K5（判据见 `020`「K5 交接判据」段）。本任务补用户态 `clone` 的完整语义。

DADAO 特有事实（`contract-syscall §10/§11`，**不得偏离**）：
- `rb3 = rbtp`（TP）；`clone` 含 `CLONE_SETTLS` 时子线程 `rb3/rbtp = tls` 参数、父不变。
- **「双返回」归用户态 wrapper（musl `clone`/`pthread_create`）**：内核只保证「子线程从 syscall 返回处开始执行时 `rd8 = 0`、其余寄存器现场 = 父现场副本（除返回寄存器与架构约定差异）」，父线程返回子 tid；内核**不实现两次返回**（`§10`）。
- `clone` 原子可见：子现场 = 父现场副本、`rd8 = 0`、子 `rbtp` 按 §10 设；不得让子看到半初始化 TCB（`§11`）。
- `lr`/`sc` 保留标记**异常/中断进入即清** ⇒ `lr…sc` 不能跨任何 syscall（`§11`）。

## 目标

1. **`clone` syscall 完整**（`kernel/syscalls.c` 或通用表 `clone` 号）：解析 `flags`/`stack`/`tls`/`ptid`/`ctid`（`rd16–31`/`rb16–31`，`§3`），交 `copy_process`；返回父侧 = 子 tid、子侧 = `rd8 = 0`。
2. **`CLONE_VM`**：共享父 `mm`（不 `dup_mm`），`mm->mm_users++`、`context.asid` **相同**（不新分配）。
3. **`CLONE_SETTLS`**：子线程 `rb3/rbtp = tls` 参数、父不变（`copy_thread` 的 TLS 分支）。
4. **`CLONE_THREAD`**：同线程组（`tgid` 共享）；`CLONE_FS/FILES/SIGHAND` 用户可见共享语义。
5. **TLS 用户面**：入口保存/返回恢复 `rb3`（`023` 已做）；`execve` 清 0（实现点见 `023` 待裁定 1）；`initial-exec`/`local-exec` 分工（TP 方向/偏置归 musl arch 宏，本任务不决定，`§10`）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_clone_probe.py` rc=0，逐 case 打印；期望值现场派生（`CLONE_*` 位 ← `include/uapi/linux/sched.h` 锁定源、TLS ← `contract-syscall §10`）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `C1 CLONE_VM 共享地址空间`：clone 后子线程 `mm == 父 mm`（`mm_users` 增）、`context.asid` 相同（与 `fork` 对照：`fork` 的 `mm`/asid 不同）。
   - `C2 CLONE_SETTLS`：子线程 `rb3/rbtp == tls` 参数、父 `rb3` 不变（现场哨兵值）。
   - `C3 子入口 rd8=0 + 父返 tid`：父侧 `clone` 返回子 tid（非 0）、子侧 `rd8 == 0`（**双返回归 musl wrapper**，内核只保证这两点）。
   - `C4 CLONE_THREAD`：子线程与父同 `tgid`（线程组）；`CLONE_FS/FILES/SIGHAND` 共享（现场断言指针相同）。
   - `C5 TLS 保持`：子线程 `rbtp` 跨 syscall 不变（`023` 口径）。
3. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：① `CLONE_VM` 仍 `dup_mm` ⇒ `C1` 红（mm/asid 不同）；② `CLONE_SETTLS` 不设子 `rb3` ⇒ `C2` 红；③ 子入口不置 `rd8=0` ⇒ `C3` 红；④ `CLONE_THREAD` 不共享 `tgid` ⇒ `C4` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_syscall_probe.py`（023）、`k4_kthread_probe.py`（020）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-024/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{process.c,syscalls.c}.patch`、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k5_clone_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k5_clone_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `contract-syscall §10/§11` + `DADAO-21 §4` + `contract-abi §4.5` 为准；`copy_process` 通用逻辑不重写，只补 arch 钩子；**「双返回」不得在内核实现**。
5. `clone` 原子可见：子现场 = 父副本、`rd8=0`、子 `rbtp` 按 §10 设（`§11`）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~**`execve` 清 0 实现点**~~ **已裁定（用户 2026-11-17 选 A）**：内核 `start_thread` 清 `rbtp=0`（`023` 同口径）；本任务 TLS 用户面做「入口保存/返回恢复 + `clone` SETTLS」，不重复清 0。
2. ~~**pthread 类测试的载体**~~ **已裁定（用户 2026-11-17，选 A）**：本任务用**内核侧 clone 自检**（`k5_clone_probe.py`：`CLONE_VM` 共享 mm/asid、`CLONE_SETTLS` 子 `rb3=tls`、`CLONE_THREAD` `tgid`、子入口 `rd8=0`）；**真实 musl `pthread_create` 端到端留 `029` 收口门控**做代表例（与 015 的「门控只跑代表例」口径一致）。

## 审阅记录

### 第 1 轮 engineer 自审（逐行、自主）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 **同 cfx 的 cg5 只有一份**：在 handler 里睡过的任务醒来时 `escape` 取的是别人入口写的 `excp_cause_ip` ⇒ 父任务被送回子任务的 park 指令、整机挂死 | ✅已修 | `trap.S` 两条返回路径在 restore 前把本任务帧的 `ip` 写回 `cfx_umon cg5 rc3`（`escape` 的 0/+4 语义不变） | 修前：C1 全绿后 180 s 超时；修后 11 条 trap 全按序、`K5 clone done` 出现 |
| F2 入口栈顶停在 `cfx_umon cg6 rc1`，而 `DADAO_GPR_SAVE` 正用 cg6 rc0/rc1 暂存用户 `rd2`/`rd3` ⇒ 入口把用户 `rd3` 当 SP（首版把 `sc` 结果放 `rd3`，SP=1） | ✅已修 | 新增 `dadao_user_stack_top`（`__switch_to()`/`dadao_enter_user()` 写、入口 `set.rb`+`ld.o` 读）；`cfx.h` 的 cg6 说明改为实况 | 修前第 1 条 trap 后挂死；修后入口按任务栈工作 |
| F3 子任务从 `trap` 处进入会重跑 `clone`（无限分支） | ✅已修 | `dadao_ret_from_fork()` 的用户子任务分支 `ip += 4`；`copy_thread()` 保持纯拷贝（016 的 F1 判据不动） | 子任务 rd8=0 后直接进 `getpid`（trap 4），无重复 clone |
| F4 `clone` 未选 `CONFIG_CLONE_BACKWARDS` ⇒ `tls` 从第 5 槽取（0），与 musl 第 4 槽不符 | ✅已修 | `arch/dadao/Kconfig` 增 `select CLONE_BACKWARDS` | 注入 ⑤ 删该行 ⇒ C2 红；恢复后绿 |
| F5 用户程序首次触碰匿名页会缺页，缺页进入即清保留标记 ⇒ `lr;sc` 对照用例测的是缺页 | ✅已修 | 桩在 `lr` 前先 `st.o rd0,[rb5]` 触碰一次 | `atom_sc_immediate` 由 0x1 转 0x0 |
| F6 非 leader 线程退出后不留僵尸（`exit_notify` 直接释放）⇒ `EXIT_ZOMBIE` 判据恒假 | ✅已修 | 判据改「tid 已不是任务」（`clone_thread_gone`） | want=0x0 got=0x0 |
| F7 注入 `child-rd8` 只表现为超时（不可归因） | ✅已修 | 钩子加「非父任务走到父路径 ⇒ `c3_child_took_parent_path`」具名判据 | 注入时该行 FAIL、宿主按 FAIL 段退出 |
| F8 被强杀的注入轮次把 `select CLONE_BACKWARDS` 留在源码树（还原未执行） | ✅已修 | 用该轮 `.orig` `cp` 复原 + md5 对账；`finally` 还原路径不变 | 实文件 md5 == 注入前 `f3594610…`；事后从 base 重跑 `apply-series` 91/91 |
| F9 gate 常量解析：`#define` 值含 C 表达式/`UL` 后缀时解析失败 | ✅已修 | 只解析整数字面量；代码页地址改读探针自己的 `stub=… code=` 行 | cases 组 72/72 |
| F10 证据脚本 `${p}_probe` 被 shell 当 `p_probe`（`set -u` 即退出）；`K5 check` 计数读了 gate 的 stdout 而非控制台 | ✅已修 | 循环变量改 `${p}`；`K5C_TMP` 指到证据目录、从控制台日志现场计数 | 全量 `SUMMARY checks=22 fails=0` |
| F11 `CASES` 漏 `clone_thread_gone` ⇒ 计数差 1（37 vs 38） | ✅已修 | 补入 C3 名单 | 现场核对：declared 38 == console 38、无重复 |

**判决**：11 条 finding 全有处置（全修），无未修项 ⇒ 可标「待验收」。范围披露：`arch/dadao/Kconfig`（`CLONE_BACKWARDS`）、`include/asm/{cfx,setup}.h`、`kernel/{setup.c,Makefile}`、`tools/linux/k4_kthread_probe.py`（S5 负例随本任务收窄）、15 个门控脚本的 `CONFIG_PINS`（新符号钉 `n`）——均在本任务语义范围内，非「顺手优化」。

### 第 1 轮 reviewer 验收

- **重跑（我独立执行，仓库根）**：运行期证据目录内的 `run.sh` → `SUMMARY checks=22 fails=0`、退出码 **0**（gate 4 / inject 5 / regress 9 / tree 3 全 PASS）；`python3 tools/linux/k5_clone_probe.py --no-inject` → `k5_clone_probe: 72/72 passed` rc=0、0 条 `[FAIL]`。
- **抽查断言来源（两侧不同源，非恒真）**：`c1_thread_mm_shared` guest 侧 `child->mm == k5c_parent->mm` + `asid`/`mm_users`，host 侧解析 `K5 clone child:` 控制台行；`c2_child_rb3` guest 侧 `regs->rd[28]` vs `k5c_tls_arg`、host 侧用 `trap.S` 现场解析的 `K5C_TLS`；`exec_entry_ip` guest 侧读 initramfs 内 ELF、host 侧用 `parse_newc` 现场读 `e_entry`。
- **5 路注入（我的重跑，逐路红→还原→回绿）**：`clone-vm-dup` → `c1_thread_mm_shared/asid/mm_users` 红 rc=113；`clone-set-tls`、`clone-backwards` → `c2_child_rb3`+`c5_*` 红 rc=119；`child-rd8` → `c3_child_took_parent_path` 红 rc=124；`clone-thread-group` → `c4_child_getpid` 红 rc=116；每路 md5 对账一致、还原重建回绿、0 FAIL。
- **我方新增第 6 路注入**：删 `dadao_ret_from_fork()` 用户分支的 `regs->ip += DADAO_INSN_BYTES;` → `29/48 passed, 19 FAILED` rc=**1**（`c3_child_took_parent_path`、trap 计数 clone=3、宿主 124）；`cp` 还原后 md5 与注入前一致 → 重建 `72/72 passed` rc=0、组件源树干净。
- **不回归（我重跑）**：`check-linux-k0` 130/130、k1 112/112、k2 170/170、k3 263/263（均 rc=0）；`k4_fork` 104、`k4_cow` 86、`k4_stack` 44、`k4_switch` 76、`k4_kthread` 112、`k5_syscall` 62 全 0 FAIL；`check-config-pins` 80 项 0 失败（17 脚本 / 19 符号 / 47 镜像）；`check-patch-tree` rc=0（linux 91 补丁、438 patches OK、无 linux 段问题）；`check-syscall-abi` 86/86 rc=0。
- **补丁树**：从 base 全新克隆按 `series` 逐条 `git apply` → **91/91 应用、0 失败**，提交后工作树 0 改动，且树哈希与组件源树 base+1 完全相同（`3bd7ca669…`）。
- **6 个语义检查点（逐个核，均在我重跑输出中）**：C1 子 `mm`/`asid` == 父、`mm_users` 父+1，同程序 fork 对照 `mm`/`asid` 不同且父计数不变；C2 子 `rb3` == `tls` 参数、父两次 clone 后仍哨兵、fork 子继承哨兵；C3 子入口 `rd8 = 0`（且第二次 trap 仍 0）、帧拷贝哨兵与父相等、父返子 tid 非 0 且两次 clone tid 不同；C4 `tgid`/`group_leader`/`fs`/`files`/`sighand` 共享、线程 `getpid` == 组 pid，fork 子全反；C5 子帧 `rb3` == `tls` 且跨 `getpid` 后不变；A 正对照 `atom_sc_immediate`（spec 成功值）+ 负例 `atom_sc_after_syscall`（spec 失败值），两值由 `SimRISC-12 §1` 现场解析；X `exec_ok = 0`、`exec_rbtp_zero = 0`、`exec_entry_ip` == 镜像内 ELF `e_entry`。
- **三处真缺陷修法（在 diff 中、是代码不是注释）**：① `trap.S` 两条 umon 返回路径 restore 前各一次 `cfx2rc cfx_umon, cg5, rc3, rd4`（静态断言计数 == 2，我 grep 到 2 处）；② 新增 `dadao_user_stack_top`，`__switch_to()`/`dadao_enter_user()` 写、入口 `set.rb`+`ld.o` 读，`trap.S` 中已无 `cfx2rd cfx_umon, cg6, rc1, rd3`；③ `dadao_ret_from_fork()` 用户分支 `regs->ip += DADAO_INSN_BYTES;`（第 6 路注入证明其行为后果）。
- **约束核验**：提交的 29 文件与完成区一致，未碰 `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`；注入还原只用 `cp`+md5（无 `checkout/restore/stash/reset --hard`）；审查前后两次 `git status --porcelain -uall` 均空、HEAD 未变；我未提交 git；术语用「寄存器组」。
- **发现（非阻断，文档级数字笔误）**：完成区写「15 个门控脚本」补 `CONFIG_DADAO_K5_CLONE_SELFTEST=n`，现场 `grep -rl` 实为 **16** 个（`check-config-pins` 现场统计 17 脚本 / 19 符号 / 47 镜像）——请 architect 收尾时一并改。
- **判决：Accepted** —— 我方重跑 `SUMMARY checks=22 fails=0`（rc=0）、6 路注入（含 1 路新增）全部「红 → `cp`+md5 还原 → 重建 → 回绿」、不回归与补丁树全绿，硬约束无违反。

## 完成区

**测试结果**：`k5_clone_probe.py` **72/72**（cases：38 条内核断言 + 34 条 gate 断言，全部现场派生）；`--selfcheck` 破损控制台判红；5 路注入「红 → `cp`+md5 还原 → 重建 → 回绿」⇒ 全量 **97/97**。不回归：`check-linux-k0` 130/130、`-k1` 112/112、`-k2` 170/170、`-k3` 263/263；`k4_fork` 104/104、`k4_cow` 86/86、`k4_stack` 44/44、`k4_switch` 76/76、`k4_kthread` 112/112、`k5_syscall` 62/62；`check-config-pins` 80 项 0 失败（17 脚本 / 19 符号 / 47 镜像）；`check-patch-tree` rc=0（linux 91 补丁 0 问题）；`check-syscall-abi` rc=0。
**修改文件**：`components/linux/patches/arch/dadao/{Kconfig,Kconfig.debug,include/asm/{cfx,setup}.h,kernel/{Makefile,process.c,setup.c,trap.S}}.patch`、`components/linux/patches/arch/dadao/kernel/k5_clone_selftest.c.patch`（新）、`components/linux/series`、`components/linux/changelog.md`、`tools/linux/k5_clone_probe.py`（新）、`tools/linux/k4_kthread_probe.py`、15 个门控脚本的 `CONFIG_PINS`（补 `CONFIG_DADAO_K5_CLONE_SELFTEST=n`）。
**验收结果**：① 逐 case 打印（真实控制台）：`K5 check c1_thread_mm_shared want=0x1 got=0x1 ok`、`c2_child_rb3 want=0x4b3543544c530001 got=…`、`c3_child_rd8_zero want=0x0 got=0x0 ok`、`c4_child_getpid want=0x10 got=0x10 ok`、`c5_child_rb3_after_syscall want=…got=…ok`、`atom_sc_immediate want=0x0 got=0x0 ok`、`atom_sc_after_syscall want=0x1 got=0x1 ok`、`exec_rbtp_zero want=0x0 got=0x0 ok`；宿主 rc=0、末行 `K5 clone selftest: done`。② 注入 5 路逐路 `[PASS] INJECT … ⇒ 红` + `还原（cp + md5 对账）` + `还原后回绿`。③ 全量证据脚本 `SUMMARY checks=22 fails=0`（组：gate/inject/regress/tree）。④ 序列可复现：从 base 全新克隆 `apply-series --component linux` 91/91 应用并提交、树干净（base+1）。⑤ 证据运行在**合并态**（分支已含 master 的 `b38a150d` 之后提交）。
**新发现/坑**：① 同 cfx 的 **cg5 只有一份**，任何在 handler 里睡过的任务都必须返回前写回自己的 `excp_cause_ip`（§8「同 cfx 须先保存 cg5」由**跨任务**触发）；② **cg6 rc0/rc1 不能停放跨入口状态**（入口保存序列自己要用）；③ 用户首次触碰匿名页/零页必缺页，而**缺页进入即清保留标记** ⇒ 原子性用例必须先触碰页；④ 非 leader 线程退出**不留僵尸**；⑤ 运行态任务仍不让出 CPU（020 结论）⇒ 交接只能靠阻塞。
**遗留问题**：无未修项。外部现场：`check-patch-tree` 首次全量跑时为红（12 项全在 **gem5**——共享的组件源码树正被并行任务改动），linux 组件 0 问题；把不参与本任务的 gem5 共享树移出本工作树后该门控 rc=0（qemu/musl 共享树仍保留并同样 0 问题，本任务的门控需要它们）。
