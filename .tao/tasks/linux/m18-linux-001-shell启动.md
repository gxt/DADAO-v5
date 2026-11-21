# m18-linux-001: K6 shell 启动（busybox sh + semihosting 控制台 + 前台执行）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m14-linux-031`、K5 收口（syscall/信号/ABI）
**可并行分片**：否
**预估**：3–4 h
**档位**：大改（用户态闭环端到端）
**状态**：已验证

> **迁移说明**：本任务原为 `m14-linux-032`（M14），用户 2026-11-20 裁定 K6 移入 M18 ⇒ 改号 `m18-linux-001`，任务范围不变。

## 背景

K6 首版**只做前台执行**：`busybox sh` 在 QEMU system 下启动，经 semihosting 控制台读写，能执行内建与简单 applet；**不实现作业控制**（无 TTY/job control）。

## 目标

1. **启动路径**：内核 → `/init`（busybox）→ `sh`，控制台走 semihosting（`SYS_WRITE0`/`SYS_READC` 等）。
2. **进程面**：`fork`/`execve`（外部 applet）、`wait4`、退出码；`SIGCHLD` 回收。
3. **信号面**：`SIGINT`/`SIGTERM` 等基本投递与默认动作（与 `027` 衔接）；不实现 `SIGTSTP`/作业控制。
4. **标准 IO**：`stdin`/`stdout`/`stderr` 与 semihosting 的映射；管道（`|`）与重定向（`>`/`<`）按 busybox 实现能力评估，未支持项写明。

## 验收（逐条贴真实 rc）

1. `busybox sh` 启动并输出可识别提示/命令回显。
2. `echo hello` 输出正确、退出码 0；`false` 退出码非 0。
3. 外部 applet（如 `ls`）经 `execve` 运行并返回；`wait4` 收到正确状态。
4. 信号：`kill -TERM` 投递到子进程并触发默认动作（或 busybox 处理）。
5. 不做作业控制的口径写进完成区（哪些命令不支持、原因）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：busybox 配置/补丁（若需）、`/init` 脚本、内核信号/syscall 补丁（若需，逐条披露）、本任务书。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

实现按「跑一次 → 读失败 → 改 → 复跑」推进；下面每条都在最终源码/产物上复验：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `start_thread()` 重写 exec 帧后，syscall 的 `+4` 仍加到新 entry IP ⇒ busybox `_start` 第一条指令被跳过、SP=0 | ✅已修 | `entry_common.c` 保存 `entry_ip`，仅 `regs->ip == entry_ip` 时加 4 | `sh -c` 的 `echo HELLO`/`ls` 正常；交互 `hello` 输出 |
| exec 后首个用户异常仍用共享入口栈，`dadao_user_stack_top` 未更新 | ✅已修 | `start_thread()` 写 `dadao_user_stack_top = task_stack_page(current)+THREAD_SIZE` | `K4 fork: ... sp=...` 与 `task_pt_regs` 一致；无递归 |
| 用户缺页交接在静态 supv 帧上睡眠，另一任务取异常触发 `recursive supv exception` | ✅已修 | fork 时在 `arch_dup_mmap()` 里 `dadao_fork_stack()` 预复制私有可写页（孩子私有、父亲恢复可写；按 PFN 确认已分离才恢复） | 交互/`-c` 全程无 `recursive`；`check-linux-k5` 280/280 |
| SIGCHLD 处理函数的信号帧往返使 shell 在 `wait4` 后 SIGSEGV | ✅已修 | busybox `shell/ash.c.patch`：不装 SIGCHLD 处理函数（`SIG_DFL`，不自动回收），`wait4` 同步等待 | `false-rc=1`、`ls-rc=0`、`term-rc=143`、`int-rc=130` |
| 控制台按行返回短读，ash 读完一行即退出 | ✅已修 | `semihost_tty.c` 每次 `read` 返回 1 字符（`SYS_READC`）+ 回显/CR→NL/Ctrl-C/Ctrl-D | 交互 9 条命令逐条执行、`K6-DONE`、`exit 7` |
| initramfs 无 `/dev/console`、无 `kill` applet | ✅已修 | `make_initramfs.py` 生成 `dev/console`（c 240 0）与 `bin/kill`；busybox `CONFIG_KILL=y` | `initramfs-console-node`/`initramfs-kill-link` PASS |
| 证据脚本从 `.work` 软链推导根落到主工作树 | ✅已修 | `run.sh` 用 `pwd -L` 逻辑路径推导 worktree 根 | `RESULT: PASS checks=24 failed=0` |

未修 finding：无（功能面）；已知边界见完成区「遗留问题」。

**判决**：可交付（`待验收`）。

### 第 1 轮 reviewer 验收

**重跑**（仓库根执行运行期证据目录内的 `run.sh`）：`RESULT: PASS checks=24 failed=0`、`EXIT=0`，24 行逐条 [PASS]（含 `qemu-pid1-exit-code: 7`）。控制台抽读：`dadao# echo hello`→`hello`、`echo-rc=0`、`false`→`false-rc=1`、`ls /`→`bin dev init init.musl`+`ls-rc=0`、`kill -TERM`→`Terminated`+`term-rc=143`、`kill -INT`→`int-rc=130`、`K6-DONE`、`exit 7`→QEMU rc=7。管道/重定向脚本未覆盖 ⇒ 本人另起一次 QEMU 复跑：`echo hi | cat`→`hi`、`pipe-rc=0`；`echo abc > /x`+`cat /x`→`abc`、`redir-rc=0`；`exit 0`→rc=0（完成区该两条数字为真）。

**独立注入 2 路**（`cp`+md5 备份 → 改被测产物 → 重跑同一 `run.sh` → `cp` 回 + md5 相等 → 重建回绿）：
① 去掉 exec 成功路径的 `+4` 判据（`entry_common.c` 两处守卫改回无条件）⇒ `RESULT: FAIL checks=24 failed=10`、`EXIT=1`：`qemu-pid1-exit-code: want=7 got=0`、8 条 console 全缺、`no-die-no-vma` 红；内核尾部 `sh: out of memory`（首指令被跳过、SP=0 的既定症状）。
② 去掉 fork 预复制（`arch_dup_mmap()` 改回空转）⇒ `RESULT: FAIL checks=24 failed=10`、`EXIT=1`：`qemu-pid1-exit-code: want=7 got=14`、8 条 console 全缺、`no-recursive-supv` 红（日志 `die mode=2 code=0xe`）。
两路还原后被测源码树 `git status` 为空、md5 与注入前逐位相等；复跑均 `24/24 PASS、EXIT=0`。⇒ 脚本无恒真项，两条否定断言与 console 组均有可达 FAIL。

**不回归（本人重跑，取被检命令自身退出码）**：`check-linux-k0` **146/146、rc=0**；`check-linux-k5` **280/280、rc=0**（S42 C41 F40 T34 G26 P35 R62）；`check-config-pins` 85 项 rc=0；`check-component-changelog` 40 项 rc=0；`check-source-state` rc=0（linux/busybox `OK count=1 clean=True`）；`check-patch-tree` rc=2 且 8 条问题**全在 musl**，linux `105 patch(es)`、busybox `3 patch(es)`、linux/busybox 断言 0；`check-manifests-guard` rc=2 仅 `milestones-m14.md` 缺失（M14 归档既有）；`check-knowledge-refs` rc=0（本记录写入后已复跑）。

**补丁真源与范围**：`tools/infra/make_patch.py linux|busybox` 重导 → `0 written, 105 unchanged` / `0 written, 3 unchanged`，108 个补丁重导前后 md5 全等、`git status` 与开工快照逐行相同 ⇒ 非手改；`git status` 19 项与完成区「修改文件」逐项对上，**未改版本号**、未提交。

**约束核验**：独立 worktree ✓；范围 = busybox 配置/补丁 + 内核 console/signal/syscall 补丁 + `make_initramfs.py`（完成区已越界披露）+ 本任务书 ✓；`cp`+md5 还原 ✓；完成区 6 行 ≤30 ✓、`**状态**`=`待验收` ✓；「不做作业控制」清单（`jobs/fg/bg/&`、`SIGTSTP`、`kill %N`、无 `/proc`、无行编辑）+ 留到 K6 后续已写明 ✓；`ASH_JOB_CONTROL` 未开、`CONFIG_KILL=y`（12 applet 现场清点）、`dev/console c 240 0`、`bin/kill -> busybox` ✓；`semihost_tty` 只做前台（`TIOCSPGRP` 收下即忽略、无 TTY 作业控制、无 `TIOCGSID`）✓；`ash.c.patch` 不装 SIGCHLD 处理函数、同步 `wait4` 与口径一致 ✓；fork 预复制仅限「私有 + 可写 + 已 present」且按 PFN 分离才恢复父页可写，**未**关闭需求分页/COW 缺页路径 ✓。

**Finding（均不阻断，交 architect 收尾处置）**：F1 `run.sh` 未覆盖管道/重定向（本人已独立复跑证实）⇒ 建议并入脚本；F2 `console-hello`/`console-K6-DONE` 可由输入回显单独满足（输入含该字面量），非恒真但区分度弱 ⇒ 建议锚定输出行；F3 `busybox-applet-count` 期望值 `12` 写死，与 `m14-linux-030` 返工口径「期望由 `config.min` 派生」不一致；F4 注释陈旧：`mmu_context.h` 中 `arch_dup_mmap` 上方仍写「Nothing is left for the arch…port-side COW」，与新增 eager 预复制矛盾，`fault.c` 两段 K6 注释重复且标题不一致；F5 隐含前提：`+4` 仅在 `regs->ip == entry_ip` 时加，依赖「dispatch 只在 exec 成功时改写 ip」，后续新增 SKIP 改写路径须复核（K5 280 未见回归）。

**判决**：**Accepted**（验收命令块本人重跑全绿、约束无违反；交 architect 终审）。

### 第 2 轮 engineer 自审（复核 Accepted 的 5 条 finding）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `run.sh` 未覆盖管道/重定向 | ✅已修 | `input.txt` 加 `echo hi | cat` / `echo abc > /x; cat /x`；`run.sh` 断言输出行 `hi`/`abc` 与 `pipe-rc=0`/`redir-rc=0`，复用同一次 QEMU 启动 | `RESULT: PASS checks=28 failed=0`；缺这两条时对应 rc/输出断言必红 |
| F2 `hello`/`K6-DONE` 只匹配输入回显 | ✅已修 | 新增 `line_is()`（`grep -x`）锚定输出整行；输入回显为 `dadao# echo hello`，不匹配 `^hello$` | 负例日志只含 `dadao# echo hello`/`dadao# echo K6-DONE` 时两条均 rc=1；正常日志 rc=0 |
| F3 applet 计数写死 12 | ✅已修 | 从 `components/busybox/config.min` 现场派生：`enabled - infra`（`STATIC/BUSYBOX/FEATURE_VERSION` 为非 applet），打印派生值 | `enabled=15 infra=3 expected=12 actual=12`，`busybox-applet-count` PASS |
| F4 `arch_dup_mmap` 注释与 eager 预复制矛盾；`fault.c` K6 注释重复 | ✅已修 | 改写 `mmu_context.h` 的 arch hook 段（generic COW 仍在，K6 只加 eager 步骤）；合并 `fault.c` 两段 K6 注释为一段 | 源树 clean base+1；`check-patch-tree --source-state` OK |
| F5 `+4` 判据的后续约束未记录 | ✅已修 | 完成区「遗留问题」加：`+4` 依赖 dispatch 只在 exec 成功时改 `regs->ip`，新增 SKIP 改写路径须复核 | 本任务书该行 |

未修 finding：无。功能代码本轮未改（仅注释/证据脚本 + 任务书）。

### 第 2 轮 reviewer 窄复核

**重跑**（仓库根执行运行期证据目录内的 `run.sh`）：`RESULT: PASS checks=28 failed=0`、`EXIT=0`（28 [PASS] / 0 [FAIL]）；新增断言 = `line_is` 锚定的 `hello`/`hi`/`abc`/`K6-DONE` 与 `pipe-rc=0`/`redir-rc=0`。
**F1 负例**（`cp` 备份 `input.txt` → 删掉 5 行管道/重定向输入 → 重跑同一脚本）⇒ `RESULT: FAIL checks=28 failed=4`、`EXIT=1`，红项恰为 `console-pipe-output`/`console-pipe-rc`/`console-redir-output`/`console-redir-rc`；`cp` 回 + md5 相等后复跑回绿。
**F2 负例**（我自建「只含输入回显」日志，直接抽取 `run.sh` 内的 `contains`/`line_is` 函数体执行）⇒ `old-contains-hello` [PASS]、`line_is-hello`/`line_is-K6-DONE` 均 [FAIL]、`failed=2`、脚本 `exit=1` ⇒ 输入回显不再能满足，整行锚定生效。
**F3**：现场复算 `enabled=15 infra=3 expected=12 actual=12`（`grep -cE` 从 `config.min` 派生，无字面 `12`）；备注（不阻断）：`SH_IS_ASH`（非 applet）恰与无独立符号的 `sh` applet 抵消，未来新增非 applet 符号会使期望虚高而**假红**，方向安全。
**F4/F5**：`make_patch.py linux` 重导 `0 written, 105 unchanged`、105 个补丁 md5 全等；与第 1 轮备份逐文件 diff **仅 2 个文件且全部为注释行**（`mmu_context.h` arch hook 段改写、`fault.c` 重复注释合并），**功能代码未变**；任务书「遗留问题」已写入 `+4` 依赖「dispatch 只在 exec 成功时改写 `regs->ip`」的后续复核约束。
**不重跑**：`check-linux-k5`/`check-linux-k0` 本轮未重跑（功能代码未变，仅注释/证据脚本/任务书；第 1 轮 280/280、146/146 采信）。另跑 `check-source-state` rc=0（linux/busybox `OK count=1 clean=True`）。
**判决**：**Accepted**（本记录写入后复跑 `check-knowledge-refs` rc=0）。

## 完成区

**测试结果**：证据 `run.sh` **28/28 PASS、rc=0**（新增管道/重定向两条验收与输出行锚定）；`make check-linux-k5` **280/280、rc=0**（S 42/42 C 41/41 F 40/40 T 34/34 G 26/26 P 35/35 R 62/62）；`make check-linux-k0` **146/146、rc=0**；`check-config-pins` 85 项 rc=0；`check-component-changelog` 40 项 rc=0；`check-patch-tree` linux 段 105 patch(es)、assertion 0（全局 rc=2 全在 musl，属其它任务）；`check-source-state` linux/busybox 均 `OK count=1 clean=True`；`check-knowledge-refs` rc=0；`check-manifests-guard` rc=2 仅因 `.tao/knowledge/milestones-m14.md` 缺失（M14 归档既有，与本任务无关）。
**修改文件**：`components/linux/patches/**`（改 8：Kconfig、mmu_context、setup.h、kernel/Makefile、early_console、entry_common、setup.c、mm/fault；新增 `kernel/semihost_tty.c.patch`、`kernel/exit.c.patch`，series 105）、`components/linux/{series,changelog.md}`；`components/busybox/{config.min,series,README.md,changelog.md}`、新增 `patches/shell/ash.c.patch`；`tools/linux/make_initramfs.py`（越界披露：`/dev/console`、`bin/kill`、`/init` 的 PATH/PS1，属启动路径必需）；本任务书。**未改**版本号。
**验收结果**（真实 rc）：交互启动输出 `dadao# ` 与命令回显；`echo hello`→`hello`、`echo-rc=0`；`false`→`false-rc=1`；`ls /`→`ls-rc=0`（外部 applet 经 execve、wait4）；`/bin/sh -c '/bin/kill -TERM $$'`→`term-rc=143`；`kill -INT`→`int-rc=130`；`echo hi | cat`→输出行 `hi`、`pipe-rc=0`；`echo abc > /x; cat /x`→输出行 `abc`、`redir-rc=0`；`K6-DONE`；`exit 7` → QEMU 进程 rc=7。注入 `make_initramfs.py --inject applet` → rc=1 且点名 `bin/sh`，重建回 rc=0。
**不做作业控制的口径**：`ASH_JOB_CONTROL=n`，无 `jobs/fg/bg/&`/`SIGTSTP`；`kill %N` 不可用，信号用外部 `/bin/kill` 的 PID 形式；无 `/proc`（`ps` 退化为自身/空表）；无行编辑/补全。原因：K6 首版只做前台执行，内核尚无作业控制/终端会话语义；SIGINT/SIGTERM 默认动作已可用。
**新发现/坑**：① exec 成功路径不能套用 syscall `+4`（`entry_ip` 判据）；② exec 后必须显式设 `dadao_user_stack_top`；③ 静态 supv 帧不可跨睡眠，用户缺页路径不能走会睡眠的通用 COW（fork 时预复制）；④ ash 以短读为 EOF（控制台须按字符返回）；⑤ SIGCHLD 处理函数帧往返尚未闭环，K6 用同步 `wait4`；⑥ `check-manifests-guard` 报 `.tao/knowledge/milestones-m14.md` 缺失，为 M14 归档既有问题，非本任务。
**遗留问题**：作业控制/`SIGTSTP` 与异步 SIGCHLD 处理留 K6 后续；`+4` 判据依赖“dispatch 只在 exec 成功时改写 `regs->ip`”，后续新增 SKIP 改写路径须复核此判据；`ps` 无 `/proc`；K4 `k4_fork` F5（`ISS-493`）既有偶发不作本任务 blocker。
