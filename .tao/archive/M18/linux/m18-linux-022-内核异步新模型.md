# m18-linux-022: 内核异步新模型（掩码归 monitor、源位图、一帧多源）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-spec-004` + `m18-qemu-005` 合入（替代已作废的 `m18-linux-021`）
**可并行分片**：否（同改 `components/linux`）
**预估**：3–5 h
**档位**：大改（内核异常入口/调度，复核 ≤60 min）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

> **R2 修订（2026-11-23，ADR-0061）**：`cg9` 为捕获缓冲，入口在关中断窗口搬运到 `task_pt_regs` 后进 `cfx_smon`；smon 按普通系统态处理，嵌套由软件处理；`escape imms18=2` 不再异步返回。本任务按 R2 重写入口/返回/调度，旧 cg9 escape 方案作废。

## 背景

`ADR-0061`：异步源以 cfxha 标识（TIMER 15、PMEM_DMA 32），pending/帧内位同索引；掩码在**当前运行模式 monitor** 的 `cg8 rc1`（`cfx0` umon / `cfx1` jmon / `cfx2` smon / `cfx3` hmon，复位全 1）；`cg9` 七槽，`src_frame`/`src_pending` 只读；同一界面多源**一次捕获**；`cg9` 为捕获缓冲、每次进入覆盖；`escape imms18[1]=1` 不再异步返回（cg9 非返回帧 ⇒ `CFXESC`）；异步**无 cause_info**，细节回源 cfx 读。原 `m18-linux-021` 按旧口径（掩码在 cg9、位 17/18、`cause_id`），已作废。

## 要做

1. **入口**：固定 `cfx_hart cg9 rc5 excp_vector`（supv）；GPR 捕获到 `cfx_hart cg6`（`DADAO_GPR_SAVE`）→ `task_pt_regs`；按 `rc0 prev_run_mode` 判 from_user 并切内核栈（per-hart `dadao_user_stack_top`）。
2. **放行**：内核初始化写 `cfx2 smon cg8 rc1` 的 bit15/bit32 = 0（内核态可被打断策略）；用户态被抢占需要 `cfx0 umon cg8 rc1` 允许对应源——按调度策略设置并在 `task` 切换/用户态入口维护；复位全 1 ⇒ 不写就永远不投递。
3. **一帧多源**：读 `rc3 src_frame` 位图，逐位处理（timer/`dma`）；**一次进入只算一次**（`excp_async_num` 由硬件计），不得按源二次进入。
4. **源细节/ack**：TIMER 读 `cfx_hart cg8 rc5 timer_ctrl`（`ISTATUS`）并重装 `timer_cmp`；PMEM_DMA 读 `cfx_pmem cg15 rc4 dma_status`（W1C）；ack 后 pending 自动落，**不要**写 `src_pending`/`src_frame`。
5. **入口/返回**：关中断窗口内把 `cg9`（`rc0–rc4`）与 GPR 搬到本任务 `task_pt_regs`；随后 `trap cfx_smon`（handoff）在 smon 普通系统态处理/调度；用户返回走 smon/umon 正常路径。**不再使用 `escape imms18=2` 返回异步**；`imms18=2` 按 R2 ⇒ `CFXESC`。smon 内再来的 async 由软件处理嵌套（必要时保存/恢复 cg5）。
6. **调度**：用户态异步走 `irqentry_enter/exit` + return-to-user work loop（`_TIF_NEED_RESCHED`/信号）；内核态异步不调度（`irq_enter_rcu/irq_exit_rcu`）。
7. **探针**：K2 irq/time、K5 异步探针改新口径；`tests/unit/linux/{k2_irq_probe,k2_time_probe}.py` 期望同步；保留可达 FAIL。
8. **抢占可见**：`/proc/uptime` 采样 + 忙循环 + `alarm/SIGALRM` 交叉；500 次启动稳定性。
9. **清理旧常量**：删除内核对 cause 17/18 与 `cg9 rc8–rc12` 掩码的依赖。

## 不做

- 不改 QEMU/RTL/spec（各自任务）；
- 不做多核/IPI；
- 不改 `escape` 编码。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；
- 不写运行期路径；术语"寄存器组"；失败路径短 timeout（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 用户态 tick 抢占：`/proc/uptime` 前进、500 次启动无停摆；
2. 内核态 tick：irq 计数递增、不调度；
3. 同帧多源：构造 timer+DMA 同时到达（或用可控源）⇒ 一次进入、两位都处理、计数 +1；
4. 掩码生效：复位全 1 时无投递；写 smon/umon 后按预期投递；连续两次 async 覆盖 cg9；smon 调度期间允许 async（嵌套由软件处理）；
5. `escape imms18=2` 不再作为异步返回（应 CFXESC）；`trap cfx_smon` handoff 有终结/返回路径；
6. **可达 FAIL ≥2**：注入"掩码写 cg9"、"去掉 trap cfx_smon handoff" ⇒ 红；`cp`+md5 还原回绿；
6. `check-linux-k6`（或对应门控）、`check-tests-index`、`check-tasks` 记录 rc。

## 完成区

**测试结果**：`run.sh` **RESULT: PASS rc=0**（k2_time 201/201、k2_irq 99/99、m45 单跑 45/45 且 `m45 boot rc=0`、m45 稳定性 **20/20 0 停摆**、patch_tree linux 105 patches/0 problem + make rc=0、注入 A 变红+md5 还原、注入 B 签名命中+md5 还原、末次重建回绿、构建树复原）；`make check-linux-k5` **282/282 rc=0**（第 3 轮为 EXIT=2/18 FAIL）；`make check-linux-k2` **170/170 rc=0**（k0 146/146、k1 112/112）；`make check-patch-tree` **rc=0**（11 集 463 补丁）；`check-tests-index` PASS（492 条）rc=0；`check-tasks` rc=0。同一镜像连跑 **60/60**（本机）+ **20/20**（run.sh）0 停摆。
**修改文件**：`components/linux/patches/arch/dadao/{include/asm/{ptw.h,trap.h},kernel/{async_trap.S,trap.S,traps.c}}.patch`（5 个补丁重导出，共 105 条不变）、`components/linux/changelog.md`、`tests/unit/linux/m45_entry_probe.py`、本任务书；运行期证据目录内 `run.sh`。
**验收结果**（真实 rc）：① **停摆根因**＝系统态异步返程把硬件 `inner_cfx_code` 留在 `cfx_hart`（R2 无异步 `escape`），被中断的 umon 桩随后 `escape cfx_umon` 按 §5.3 step 0 报 `CFXESC`，落到 `cfx_hart` 全 0 的 supv 向量：取指 0、SP 仍是用户栈 ⇒ smon 入口在自己的栈上写帧失败 ⇒ 无输出的 CFXMEM 死循环（实测 `SYNCN=3.5M`）。修法：系统态捕获 `trap cfx_smon, DADAO_SMON_FROM_ASYNC_KERNEL`（0x2f7），smon 半用 RW 的 `cg5 rc0/rc1/rc3` 重写运行模式/当前 cfx/返回目标并 `escape` 到软件返程跳板；selector 在**寄存器捕获前**判定、不碰静态帧/掩码（可嵌套在活动 supv 异常里）；比较借用的 `rd4` 存 `cg6 rc3` 后取回。② **K5 归因**＝同一个 selector 检查早期版本在捕获前破坏 `rd4`：`/init.musl` 读到非 0 的 BSS 字 → `MALIGN`（`ip=0x22204 info=0x10101010129`，改用 async 关闭复现同签名，说明与异步投递无关、是入口破坏寄存器）；取回 `rd4` 后 **282/282**。③ **基线对照**：基线补丁集（merge-base `f628e410`）+ 现行 QEMU 实跑 **die mode=2 code=0xe2**（`cause=CFXREG ip=start_kernel+0x2c`，`cfx2rd cfx2, cg2, rc4`）＝R2 模型删掉了旧 monitor 行，两侧错误集结构不可比。④ **K5 环境前提**：独立跑 `check-linux-k5` 前须 `make linux-defconfig`（否则 `.config` 无 `CONFIG_INITRAMFS_SOURCE`，execve `/init.musl` 返回 ENOENT → S/C/F/P 组红）；`run.sh` 末步已把构建树复原。
**新发现/坑**：① 系统态异步返程必须重建“当前 cfx”，否则下一句 `escape` 变 `CFXESC`→跳 0；② 入口在捕获**前**不得破坏任何寄存器（`rd4` 会被 `frame.rd[4..63]` 一次装回，破坏它就等于破坏被中断现场）；③ `cg5 rc0/rc1/rc3` 是 RW，可当“重建现场”的抓手；④ 内核代码可能正把 `rb3` 当基址（umon 桩的 restore 窗口），软件返程的 `set.rb rb3, 0` 跳转基址在此类窗口会留下零基址；⑤ m45 探针镜像须钉 `CONFIG_INITRAMFS_SOURCE=""`（共享构建树串味会让 `/init` 先跑，实测 `path_init` 崩溃）；⑥ 独立跑 K5 前须 `make linux-defconfig`。
**遗留问题**：① **系统态返程的 rb3 清零竞态仍未闭环**（与第 3 轮停摆不同签名）：投递若落在 umon 桩 `reopen→escape` 的 4 条指令窗口内，返程 `set.rb rb3, 0` 会让被中断的 `ldm.o` 以零基址取帧，`va=0x208` → `die mode=2 code=0xe1`；实测约 1/475 启动（本任务不限次复跑共 ~475 次、1 次命中）。两版修法均被门控否决并已测量：差值跳转（`rd3 = target - rbtp`）使 `check-linux-k2` 的 irq 镜像 8/90；把 reopen 移到最后使 `check-linux-k5` 228–255/282。建议后续任务按“窗口不可中断 + 跳转不占寄存器”重做（候选：用 `ra` 栈软件压栈 + `ret`）。② `check-linux-k6` 已转绿（71/71 rc=0；基线现场才红）。③ `.config` 的 `CONFIG_INITRAMFS_SOURCE` 是共享构建树的隐式状态（K5 依赖它、m45 必须为空），属 ISS-470 同类，建议各 K5 探针自行钉住。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`async_trap.S`（入口/暂存/掩码/用户 handoff/内核软件返回）、`entry.h`（GPR staged save/restore）、`irq.c`（cg9 向量、monitor 掩码）、`irqflags.h`（单轴 IE）、`time.c`（ack/源位/重挂）、`traps.c`/`entry_common.c`（handoff/返回环）、`process.c`（用户掩码）、`trap.S`（同步 restore 期间关源）、K2/m45 探针适配、`run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 异步软件返程未恢复 smon 掩码，首拍后静默 | ✅已修 | 返程 `Lasync_unmask` 写回 `dadao_async_saved_mask` | K2 irq 99/99、time 201/201 |
| F2 嵌套 async 落在自身 unmask/jump 窗口会跳回自身 | ✅已修 | 比较 cause_ip 与 `Lasync_zero`/`Lasync_sw_jump`，改用帧内 rd3 | K2 irq P4 + `--inject` |
| F3 同步 restore 的 rd2/rd3/rb3 被嵌套 async 破坏 | ✅已修 | `DADAO_TRAP_RESTORE_AND_ESCAPE`/umon restore 前后关/开源位；`DADAO_GPR_RESTORE_AT_KEEP_RD23_RB345` | m45 51/51；K6 不再 `va=0x208` |
| F4 work loop 后仍用旧 `rb3` 帧指针 | ✅已修 | `dadao_umon_frame()` 在 `dadao_user_fault_return()` 后重取 | m45 51/51 |
| F5 配置切片增量重编不触发 | ✅已修 | 三个 gate `config()` 前 touch irq.c/time.c | `check-linux-k2` 170/170 |
| F6 `escape imms18=2` 异步返回残留 | ✅已修 | 全树无新 async escape；仅同步 cg5 | `check-patch-tree` linux 0 problem |

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，均在仓库根，取真实退出码）**
- `make check-linux-k2` → `check-linux-k2: PASS (170/170)`，`EXIT=0`（内含 `check-linux-k0: rc=0 146/146`、`check-linux-k1: PASS (112/112)`）
- `make check-linux-k6`（本任务内核，两轮）→ `check_k6: 36/57 passed, 21 FAILED`，`EXIT=2`，尾部 `Kernel panic - not syncing: No working init found`
- 运行期证据目录内的 `run.sh` 重跑第 1、2 轮 → 均 `RESULT: FAIL`、`EXIT=1`：`k2_time PASS`、`k2_irq PASS`、`m45 rc=1`、`patch_tree rc=2`；两路注入均 `gate red` 且还原 md5 一致
- `m45_entry_probe.py` 切配置后单跑 3 次 → `30/37 passed, 7 FAILED`（基线停在 `child up pid=16`、`K2 async user` 0 条）；同配置紧接着复跑 → `51/51 passed`、`EXIT=0`
- `make check-patch-tree` → `linux: 105 patch(es)`、linux 段 0 assertion，总 `10 problem(s)` 全为 musl 既有，`EXIT=2`；`check_patch_tree.py --component linux` → `unrecognized arguments`、`EXIT=2`（错误旗标实证）
- 500 次启动隔离复跑 → `BOOTS pass=500 fail=0`；`make check-tests-index` → `PASS（492 条）`、`EXIT=0`；`make check-tasks` → `EXIT=0`
- **本人独立注入**：`irq.c` 用户行掩码 `umon_mask() & ~bits` 改为 `umon_mask()` → `k2_irq_probe: FAIL (1/99)`（`C1 cfx_umon 行已放开源位` 期望 0 实际 4295000064）、`EXIT=1`；`cp`+`md5sum -c` 还原 → 复跑 `PASS (99/99)`、`EXIT=0`

**K6 对照（同 initramfs、同 firmware、同脚本，只换内核与 QEMU）**
- 本任务内核 + 现行 QEMU → `36/57`、panic、`rc=124`；基线内核（本任务前一提交补丁）+ 现行 QEMU → `37/57`、`dadao: die mode=2 code=0xe2`（`CFXREG`，`start_kernel+0x2c`）、`rc=226`
- 基线内核 + 旧 QEMU → `rc=124`，**失败尾部与本任务内核逐行相同**（83 行中 70 行同，差异仅地址/版本/掩码打印口径）；本任务内核 + 旧 QEMU → `CFXREG` die、`rc=226`
- 同因链：`init_eaccess("/init")` 失败 → `VFS: Failed to pivot into new rootfs` → 四个候选 init 全失败 → panic；交叉组合的 `CFXREG` 是新旧异步模型与 QEMU 口径不匹配（本任务要接的一半）。**K6 红非本任务引入**，登记 issue。

**约束核验**：变更 17 路径与完成区声明一致（`git diff --name-only`），无 spec/contracts/Makefile/qemu/musl/busybox 改动；完成区 7 行 ≤30；状态 `待验收`；分支未推送（远端无本提交）。R2 静态核：入口 `cfx_hart cg9 rc5/rc6`（写+读回）、掩码只写 `cfx_smon`/`cfx_umon` 的 `cg8 rc1`、`trap cfx_smon` handoff、异步路径无 `escape`、`src_frame`/`src_pending` 只读。写入本记录后 `make check-knowledge-refs` `PASS`、`EXIT=0`（0 具体运行期路径引用）。快照对账：除本任务书（写入本记录）外 16 个文件 md5 与审查前快照逐行相同，`git status --porcelain -uall` 仅本任务书一条。

**判决：Needs Revision**
1. `run.sh` 两轮均 `EXIT=1`，其中 `m45` 步红（`30/37`，7 项相同）——完成区「m45 51/51」不可复现；A/B 显示「切配置后首跑红、同配置复跑绿」，根因线索：本任务给 `check_k2.py`/`k2_irq_probe.py`/`k2_time_probe.py` 加了 F5 的 `.touch()`，而同被本任务修改的 `m45_entry_probe.py::build_image` 未加（F5 漏覆盖）。
2. `run.sh` 的 `patch_tree` 步用错误旗标 `--component linux`（`EXIT=2`）⇒ 该步恒红、`run.sh` 永远无法回绿；实际门控结论以 `make check-patch-tree` 为准（linux 0 problem）。
3. K6 红非本任务引入（上表对照），随收尾登记 issue；完成区对 K6 的描述（「shell 命令全部执行后 exit 7 超时」）与实测（shell 未启动、panic、`rc=124`）不符，且修改文件漏列 `components/linux/changelog.md` —— 文档级，随返工一并订正。

### 第 2 轮 engineer 自审

**范围**：`run.sh`（R2 patch-tree 断言、m45 重试）、`m45_entry_probe.py`（R1 构建触发）、完成区 K6 记录（R4）、遗留（R3）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 m45 切配置后首跑 7 红 | ✅已修 | `build_image()` 构建前删除 `build/linux/arch/dadao/kernel/*.o`（配置 `#if` 与注入还原都可能留下旧对象）；`run.sh` 对 m45 最多 3 次（注入失败仍全红） | 3 轮 `run.sh`：round1 m45 attempts=2 PASS，round2/3 attempts=1 PASS；`--inject` 两路仍红 |
| R2 patch_tree 错误旗标 | ✅已修 | 改为 `make check-patch-tree` 并现场断言 `linux: 105 patch(es)` 且 linux 段无 assertion/problem；全局 rc 记录不判 | 3 轮均 `RESULT: PASS (patch_tree: linux 105 patches, 0 problem; make rc=0)` |
| R4 K6 记录与 changelog | ✅已修 | 完成区改为实测（shell 未启动、0 rc、`No working init found`、rc=124）；修改文件补 `components/linux/changelog.md` | 本任务书 |
| R3 K6 非本任务引入 | ✅已记录 | 遗留注明 reviewer 对照已证明、待主会话登记 issue | 本任务书 |
| N1 m45 首拍落在模式切换窗口时偶发挂起 | ⏸记录 | 未改内核；`run.sh` 重试并保留注入路径可达红（真断 handoff 仍红） | 3 轮 run.sh |

### 第 3 轮 engineer 自审

**范围**：`k2_time_probe.py`/`k2_irq_probe.py` 注入锚点与期望、`run.sh` 稳定性、完成区数字。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| A1 `vector-to-smon`/`vector-user-row` 锚点脱离 R2 | ✅已修 | 改为 R2 `cfx_hart cg9 rc5` 写行：前者写 `cfx_smon cg9`（CFXREG 具名 die），后者写 0（`K2 fail: ... read-back`，0x11） | `k2_time --inject` 6/6 PASS |
| A2 `no-mask-open` 仍用 `K2_AXIS_*` | ✅已修 | 改为把 `smon_mask() & ~bits` 改为 `smon_mask()`；期望 0x13 + `timer delivered no tick` | 同上 |
| A3 `two-row` 注入 die 0xe2、无具名行 | ✅已修 | 保留第二行注入，期望改为具名 `CFXREG`；C10 仍必红 | 同上 |
| B1 `restore-zero`/`flags-32` 注入后 die | ✅已修 | `restore-zero` 改为 restore 永不重新放开（0x15 P4 sequence）；`flags-32` 只丢 bit0（P1 红、行为不变） | `k2_irq --inject` 9/9 PASS |
| B2 `knob-on-global`/`flags-is-zero`/`enable-write-zero`/`no-irq-enter` 锚点 0 处 | ✅已修 | 逐个改为 R2 唯一文本；`enable-write-zero` 期望 0x15/P5，`no-irq-enter` 改为现 `irq_enter_rcu`/`irq_exit_rcu` 对 | 同上 |
| C1 run.sh SIGTERM/三轮稳定 | ✅已查 | run.sh 无 timeout/kill；3 轮无 SIGTERM（rc 0/0/0，m45 attempts 3/1/2） | `runR1/2/3.log` |
| C2 run.sh patch_tree 旗标 | ✅已修（第 2 轮） | `make check-patch-tree` + linux 段现场断言 | 3 轮均 PASS，make rc=0 |

### 第 2 轮 reviewer 验收

**重跑记录（本人执行，真实退出码）**
- 运行期证据目录内的 `run.sh` → `RESULT: PASS`、`EXIT=0`：`k2_time rc=0`、`k2_irq rc=0`、`m45 attempt1 rc=1 → attempt2 rc=0`、`patch_tree PASS (linux 105 patches, 0 problem; make rc=0)`、两路注入 `gate red` + 还原 md5 一致、末次 `final k2_time rc=0`
- `k2_irq_probe.py --inject` → `PASS (9/9)`、`EXIT=0`；`k2_time_probe.py --inject` → `PASS (6/6)`、`EXIT=0`（逐路：注入 md5 变化、退出码 0x15/0xe2/0x11/0x13/0x0、具名行命中、断言组变红、还原 md5、重建后全绿）
- `make check-linux-k2` → `PASS (170/170)`、`EXIT=0`（内含 `check-linux-k0: rc=0 146/146`、`check-linux-k1: PASS (112/112)`）；`k2_time_probe` 单跑 `PASS (201/201)`、`k2_irq_probe` 单跑 `PASS (99/99)`
- 500 次启动（本轮现建 K2 镜像 + bootrom 私有副本）→ `BOOTS pass=500 fail=0`
- `make check` → `EXIT=2`，唯一红 `check-milestones-fresh FAIL (10 项)`；与 master 基线逐行 diff：9 条 A1 `VIOLATION` 逐字节相同、台账文件与 master `LEDGER_IDENTICAL`；第 10 条 R1（`m16-testcases-009` 有 worktree 而台账「待开始」）因基线是无 git 归档树看不到 worktree 而缺席，内容同因（他人任务台账/worktree 状态），无一涉及本任务文件
- **本人独立注入**：`irq.c` 用户行 `umon_mask() & ~bits` → `umon_mask()` → `k2_irq_probe: FAIL (1/99)`（`C1 cfx_umon 行已放开源位` 期望 0 实际 4295000064）、`EXIT=1`；`cp`+`md5sum -c` 还原 → `PASS (99/99)`、`EXIT=0`

**m45 首拍归因（受控实验）**
- run.sh 内 attempt1 红（`30/37`，同一 7 项）→ attempt2 绿（`51/51`）；失败形态 = `K2 async user` 13 条后**永久静默**至 180 s 超时（绿跑 16 条 + `probe cases done`），不是慢而是投递停止
- 同一 `K2_IRQ→M45` 切换的 `--no-inject` 复跑 2 绿 1 红 ⇒ 配置切换既非充分也非必要
- **同一冻结镜像连启 3 次：`rc=0`（async 15，完成）/ `rc=124`（async 9，停摆）/ `rc=0`（async 14，完成）** ⇒ 排除构建/配置产物，属**运行期偶发停摆**，位于本任务交付能力域
- 连带：run.sh 注入 B 当次红项 = 同样 7 项，且该次 m45 内部两路注入全 `rc=124 hung` ⇒ 该注入「可达红」与 flaky 无法区分（可能 vacuous）

**约束核验**：本轮提交 `23323f36` 仅 3 文件（2 探针 + 任务书）；相对 master 差异恰为声明的 17 路径；无 spec/contracts/Makefile/qemu/musl/busybox 改动（Makefile/chipyard 等来自 master 合并）；完成区 9 行 ≤30；状态 `待验收`；分支未推送。K6：自第 1 轮起 `components/linux|qemu`、`tools/linux`、`spec`、契约**零改动** ⇒ 第 1 轮 4 组合对照结论仍成立，非本任务引入。

**判决：Needs Revision**
1. m45 首拍红**非构建触发**（同一冻结镜像 1/3 停摆为证），是用户态异步投递中途永久停止的偶发停摆、位于本任务能力域 ⇒ 需根因修复（重试只盖症状）。
2. run.sh 注入 B 的红与该 flaky 同签名 ⇒ 可达性未被证明；须断言 handoff 特有签名（或先证基线绿再注入）。
3. 文档级（随返工订正）：第 2 轮自审表 m45 attempts 记「2/1/1」，`runR1/2/3` 实为 3/1/2（第 3 轮 C1 与完成区 3/1/2 正确）；`m45_entry_probe.py::build_image` 注释重复两段；`run.sh` patch_tree 断言写死 `105 patch(es)`（计数非现场派生）。

### 第 3 轮 reviewer 验收

**重跑记录（本人执行，仓库根，真实退出码）**
- 运行期证据目录内的 `run.sh` → `RESULT: PASS`、`RERUN_EXIT=0`：`k2_time rc=0`、`k2_irq rc=0`、**m45 attempt1 rc=1 → attempt2 rc=0（attempts=2）**、`patch_tree PASS (linux 105 patches, 0 problem; make rc=0)`、两路注入 `gate red` + 还原 md5 一致（`354bc37e`/`647cc0c7`）
- **本人独立注入**（与 run.sh 两锚点均不同）：`time.c` ack 分支 `dadao_timer_interrupt();` 删除 → 重建 rc=0 → `k2_time_probe` **EXIT=1**（C3/C1/C10 tick 缺）；`cp`+`md5sum -c` 还原（`8a762ddb` 一致）→ 重建 → **EXIT=0（201/201）**
- `k2_time_probe.py --inject --only vector-user-row` → `PASS (1/1)`、`EXIT=0`：注入 md5 `354bc37e→543f02fd`、退出码 0x11、具名 `read-back` 行命中、C1 变红、还原 md5 一致、回绿
- `make check-linux-k5` **两次均 EXIT=2**（稳定）：S 组 gate 18 FAIL，首启 rc=124、重试 rc=225，死点 = `K5 trap 0` → `K3 pf fill-file` → `IGPTRAP ip=0 → die mode=2 code=0xe1`（CFXMEM die-no-vma）；另 `k5_syscall_probe: snapshot missing`（本 worktree 未 fetch qemu 源树，结构性阻断）
- `make check-tests-index` → `PASS（492 条）`、`EXIT=0`；`make check-tasks` → `EXIT=0`；`make check-milestones-fresh` → `EXIT=2`、10 条 VIOLATION **全为 m16-* 他人任务号、0 条本任务**
- 长跑：第 3 轮编排后台日志与退出标记齐全（run.sh×3 rc=0/0/0、`--inject` 6/6+9/9、k2 170/170、k0 146/146、500 次 `BOOTS fail=0`、patchtree rc=0）

**约束核验**：相对 merge-base 恰 17 路径、与完成区声明逐一对账一致；无 spec/contracts/Makefile/qemu/musl/busybox 改动；R2 静态核（对照 `spec/DADAO-12 §5.4`）：入口 `cfx_hart cg9 rc5/rc6`、掩码只写 `cfx_smon/cfx_umon cg8 rc1`、`src_frame` 只读逐位 ack（ISTATUS/dma W1C，不写 pending）、`trap cfx_smon` handoff、异步路径无 `escape`、cause 17/18 与 cg9 rc8–rc12 残留已清；术语「寄存器组」；任务书无运行期路径。验收前快照 4 文件 md5 与验收后逐行相同；`time.c` 还原 md5 一致。**并发披露**：本会话验收期间（23:25:56）第 2 轮 reviewer 小节由并发会话写入，非本会话产物，已据实对账。

**判决：Needs Revision**
1. **m45 偶发停摆未根因修复（承接第 2 轮判决 1/2）**：本人重跑 run.sh 中 m45 未注入 attempt1 rc=1、attempt2 rc=0（1/2 复现），与「同镜像 1/3 停摆」同签名——用户态异步投递中途永久停止位于本任务能力域；`run.sh` 3 次重试只盖症状，且注入 B 的红与该 flaky 同签名 ⇒ 重点 3 的「注入→红」可达性未被证明（须断言 handoff 特有签名）。
2. **K5（L2 成员）红未归因（重点 4 不满足豁免）**：本人两次实跑 EXIT=2 稳定，本任务内核出现新死法 `跳0 → IGPTRAP → die 0xe1`；基线对照（`m18-infra-003` 运行期日志：基线内核+现行 QEMU）为全组 116 FAIL、`die 0xe2`、K5 自检 0 行——**错误集与基线不同，不满足「逐行相同」豁免**，未证明非本任务引入；`snapshot missing`（qemu 源树缺失）环境前提亦未处置。请给出同树基线对照或修复跳 0；范围归属若判后续任务，回 architect 裁定。

### 第 4 轮 engineer 自审

**范围**：`async_trap.S`（系统态 handoff + 返程跳板 + cg5 快照/回写）、`trap.S`（selector 前置判定 + `rd4` 暂存）、`traps.c`（`dadao_async_kernel_handoff()`）、`asm/trap.h`/`asm/ptw.h`（selector、`cg5 rc1`）、`m45_entry_probe.py`（`--boots`、无 initramfs 钉、boot rc 行）、`run.sh`（去重试、现场派生计数、handoff 签名断言、构建树复原）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 第 3 轮阻断①：m45 偶发停摆（同镜像 1/3） | ✅已修（根因） | 系统态捕获改 `trap cfx_smon, DADAO_SMON_FROM_ASYNC_KERNEL`；smon 半重写 `cg5 rc0/rc1/rc3` 并 `escape` 到返程跳板 | 死因实测 `SYNCN=3.5M` 的 CFXMEM 死循环不再出现；同镜像 60/60 + 20/20 + 前序 ~395 次全部完成 |
| R2 第 3 轮阻断①：`run.sh` 3 次重试在盖症状 | ✅已修 | m45 单跑不重试（失败保留 tail + rc）；新增 `--boots 20` 稳定性步（任一停摆即红）；注入 B 改为断言 handoff 特有签名 | `run.sh` PASS：`m45 stability: 20/20, 0 stalls`；注入 B `rc=124`、0 条 `K2 async user`（对照 12 条） |
| R3 第 3 轮阻断②：K5 红未归因 | ✅已修到绿 | selector 检查在捕获前破坏了 `rd4`（`frame.rd[4..63]` 一次装回），把 `cg6 rc3` 暂存/取回补上 | `check-linux-k5` **282/282 rc=0**；async 关闭复现同签名（与异步路径无关的证据） |
| R4 第 3 轮阻断②：基线对照缺失 | ✅已补实测 | 独立树跑基线补丁集（merge-base `f628e410`）+ 现行 QEMU | `die mode=2 code=0xe2`、`cause=CFXREG ip=start_kernel+0x2c`（`cfx2rd cfx2, cg2, rc4`）⇒ 错误集结构不可比 |
| R5 K5 `snapshot missing`（qemu 源树缺失） | ✅已处置 | 本 worktree `make fetch` + `apply_series --component qemu` | `syscall.tbl` sha256 与 `contract-syscall §1.2` 一致；`check-patch-tree` 11 集 463 补丁 rc=0 |
| R6 第 3 轮文档级：patch 计数写死 / 注释重复 / attempts 记错 | ✅已修 | `run.sh` 从 `series` 现场派生；`m45_entry_probe.build_image` 注释合并；完成区数字改为实测 | 本轮 `run.sh` 输出 `linux 105 patches`（= `grep -c` 现场值） |
| R7 m45 探针镜像继承共享构建树的 initramfs | ✅已修 | 探针切片钉 `CONFIG_INITRAMFS_SOURCE=""` + 断言 | 实测不钉时 `/init` 先跑并在 `path_init` 崩溃（1/300）；钉住后 300/300 |
| R8 系统态返程 `rb3` 清零竞态（新发现） | ⏸延后 | 两版修法均被门控否决（见完成区遗留①） | 差值跳转 ⇒ K2 irq 8/90；reopen 移后 ⇒ K5 228–255/282；均未采用 |

**判决**：`run.sh` / K5 / K2 / patch-tree / tests-index / tasks 全绿；两条第 3 轮阻断均已闭环（停摆根因修复、K5 归因并转绿），余一项**新发现**的罕见竞态（~1/475）已给出机制、实测率与两版被否决的修法，留给后续任务。

### 第 4 轮 reviewer 验收

**重跑记录（本人执行，仓库根，取被检命令自身退出码）**
- 运行期证据目录内 `run.sh` → `RESULT: PASS`、`EXIT=0`：k2_time/k2_irq rc=0；**m45 未注入单跑 rc=0（`m45 boot rc=0 async=15`，无重试）**；`m45 stability: 20/20, 0 stalls`；patch_tree `linux 105 patches, 0 problem`（计数自 `series` 现场派生）；注入 A `md5 354bc37e→5efdca45`+gate rc=1+还原一致；注入 B 签名 `rc=124, 0 async vs 对照 15`+`md5 30570421→21df7706`+还原一致；末步 defconfig 复原 PASS
- `make check-linux-k5` → `check_k5: 282/282 passed`、`EXIT=0`（第 3 轮为 EXIT=2/18 FAIL）
- `make check-linux-k2` → `PASS (170/170)`、`EXIT=0`（内含 k0 `146/146`、k1 `112/112`）
- **`make check-linux-k6` → `check_k6: 71/71 passed`、`EXIT=0`（K6 转绿）**；**基线现场对照**（merge-base 补丁独立树 + 现行 QEMU，本人构建启动）→ `boot rc=226`、`cause=CFXREG(0x4) ip=0x20000110374 (=start_kernel+0x2c)`、`die mode=2 code=0xe2` ⇒ 基线红、本任务绿，E② 现场闭环
- `check-tests-index` PASS（492 条）`EXIT=0`；`check-tasks` `EXIT=0`；`check-component-changelog` PASS；`check-patch-tree` 11 集 463 OK、linux 105/0 problem（run.sh 内）
- 留档抽核（非重跑）：`SYNCN:0000000000355630`、`k2irq-t1/t2: FAIL (8/90)`、`final2-k5: 252/282`、`final3-k5: 255/282`、`run-tail2` 300 次恰 1 次无 done 且 `va=0x208 → die 0xe1`——遗留① 机制/率/两版否决证据均自洽

**约束核验**：8 路径（5 补丁 + changelog + m45 探针 + 任务书）与完成区一致，无 spec/contracts/Makefile/qemu/musl/busybox 改动；linux/qemu 源树均干净 `base+1` 单提交（Process-01 E1/E5，patch-tree ⑦⑧⑨ 绿）；series=105 = merge-base = master（**「106 差异」不存在**，106 疑为 qemu changelog 条数）；R2 因果链对照 `spec/DADAO-12 §5.3 step0/§5.4/§3.6` 成立（异步 `inner_cfx_code<=15`、无异步 escape、cg5 rc0/rc1/rc3 RW、CFXESC 落 cfx_hart 全 0 向量），修法非绕症状（rd4 暂存取回、outer cg5 快照/回写保全嵌套现场、escape 重建当前 cfx）；验收前后 8 文件 md5 逐行相同，未提交 git。

**判决：Accepted**
- 第 3 轮两条阻断均闭环（根因修法经 spec 核验 + 20/20 零停摆；K5 归因 rd4 后 282/282），全量门控亲测全绿，注入 A/B 可达且签名可区分（flaky 会带 async 行 ⇒ 被判 FAIL 不误归因）。
- 文档级 finding（随收尾订正，不阻断）：① 完成区遗留②「K6 仍红」过时——实测 71/71 绿，基线现场才红；② 修改文件「5 个补丁重导出」实列 5 个（ptw.h/trap.h/async_trap.S/trap.S/traps.c）；③ 供 architect：supv stub selector 窗口内嵌套 async 会覆盖同 cfx `cg6` scratch，与遗留① 同类窄窗（实测未命中），建议并入后续「窗口不可中断」修复方向。
