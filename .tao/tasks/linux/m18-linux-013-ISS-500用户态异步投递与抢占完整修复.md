# m18-linux-013: 用户态异步投递与抢占完整修复（ISS-500）

**模块**：linux
**项目里程碑**：M18
**依赖**：无（前置：`ADR-0059` Accepted；实现与 `m18-linux-005` 串行，同写 linux 组件）
**可并行分片**：否
**预估**：6–8 h（标定：同档最近 5 件派单→合入实测最高 182 min；本任务改异常返回架构 + 新探针，按 2–3× 上限）
**档位**：大改（异步入口/返回路径 + 抢占与信号）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`ISS-500`【P2】：K6 之后用户态**收不到任何异步中断**。`dadao_enter_user()` 每次进用户态都把 `cfx_umon cg0 rc4` 写 `~0`，全仓无第二处写回；`dadao_user_entry_install()` 开机时清的 TIMER 位因此是死代码。用户态长循环里 `jiffies` 不走、timer wheel 不转、`sched_tick` 不跑；`sleep`/`nanosleep` 这类在内核阻塞的调用仍可被唤醒，但「忙循环 + `alarm`/信号/超时」与抢占调度失效。

现状来源：`m18-linux-004` 修 `ISS-498` 时同时屏蔽了 **supv 窗口行**与 **user 行**。注入证据只证明前者必要（只去 user 行 ⇒ 200/200 绿；两行都去 ⇒ 4/200 未进用户态）；user 行屏蔽的必要性未复现。「`jiffies` 滞后」是从 mask 状态+契约推出的，尚未端到端实测。

`entry_common.c` 头注释已指出完整方向：**给 tick 一个可切换的帧**（把异步帧移出静态 `.bss`），异步侧才能用 `irqentry_enter()`/`irqentry_exit()` 并跑 return-to-user 工作循环。用户 2026-11-22 裁定：**参考其它 ISA 完整修复**，不追认「用户态不投递」。

## 参考模型（方法，不复制代码）

- RISC-V：异常入口把 `sepc/sstatus` 与 GPR 存进软件 `pt_regs`；`handle_arch_irq()` 里 `irqentry_enter()` → 处理 → `irqentry_exit()`；返回用户前 `exit_to_user_mode_prepare()` 消费 `_TIF_NEED_RESCHED`/信号，再恢复寄存器 `sret`。
- ARM64：`el1_irq` 保存帧 → `irq_handler` → `irq_exit`；若返回 EL0，走 `exit_to_user_mode_prepare()`（抢占/信号）后 `eret`。
- x86：`idtentry_irq` 用 `irqentry_enter/exit`，`common_interrupt_return` 在返回用户前跑 work loop。
- DADAO 差异（必须解决的点）：异步帧在 `cfx_hart cg5`，`global_cfx_intr_mask` 由硬件保存、只能由 `escape` 恢复；handler 内直接 `schedule()` 会让该帧跨切换存活，其他任务期间 `cfx_hart` 异步被全局屏蔽 ⇒ 时间停摆。因此不能照搬「在 live frame 里 schedule」。

## 方案（待 ADR 逐条确认）

**早退帧（early escape）+ 软件帧 + 通用 irqentry**：

1. 用户态异步入口：GPR 捕获进**本任务** `task_pt_regs(current)`（不再跨任务共用静态 `.bss`）；保存 cause/cause_ip/cause_info 与 `status=user`。
2. 在 `cfx_hart cg5` 里把返回目标改成内核 trampoline：`rc0 = supv`、`rc1 = cfx_smon`、`rc3 = trampoline`（三者 spec 均标 RW），SP 用本任务内核栈；执行 `escape cfx_hart, [excp_cause_ip, 0]`。`escape` 恢复 `global_cfx_intr_mask`、释放硬件帧，硬件不再有 live 帧 ⇒ 后续可安全调度。
3. trampoline 以普通内核上下文运行：`irqentry_enter(regs)` → 计时/设备 handler → `irqentry_exit(regs, state)`；返回用户前的 `exit_to_user_mode_prepare()` 消费抢占与信号。
4. 通过既有 umon 入口把保存的寄存器帧交回用户态；`dadao_enter_user()` 只屏蔽 **supv 窗口行**，user 行按源位打开（不再 `~0`）。
5. 保留 `ISS-498` 的窗口保护：supv 行仍覆盖「用户寄存器已恢复、trap 未执行」的窗口；用户态投递走新的早退路径，不再依赖 live frame 直接进 C handler。

**必须验证的假设**（任一不成立 ⇒ 停下写「待裁定」，不得硬改契约）：

- spec `§5.2/§5.3`：`cfx_hart cg5 rc0/rc1/rc3` 可写、`escape` 按写入值恢复模式/cfx/目标；QEMU 与契约一致（`helper_cfx_escape` 已按 RW 实现，需实测）。
- 早退后 trampoline 运行在 `cfx_smon`/supv，页权限与内核正常路径一致（用 K5/K6 探针验证）。
- `irqentry_enter/exit` 在异步路径可用（`CONFIG_GENERIC_IRQ_ENTRY` 已开），调度后返回路径仍能恢复被中断用户帧。
- 用户态投递不再触发 `ISS-498`（启动稳定性长跑）。

## 验收（逐条贴真实 rc）

1. **ADR-0059 Accepted**，决策清单逐条落盘；实现与 ADR 一致。
2. **时间可见**：用户态忙循环（无 syscall）期间可观测 `jiffies` 推进——用 guest 探针读 `/proc/uptime`（`CONFIG_PROC_FS=y`，探针自行 mount）或等价内核导出；停 user 行恢复 ⇒ 该断言判红。
3. **抢占**：两个 CPU 密集用户任务并发时按 tick 轮转（记录切换次数/各自进度）；单任务忙循环 + `alarm()`/`SIGALRM` handler 不靠 syscall 也能被投递。
4. **`ISS-498` 不回归**：连续 **500** 次启动全部进入用户态（无 rc=124/1、无 `die-no-vma`），两次独立批次；修前/去 supv 行注入作为对照。
5. **可达 FAIL ≥3 路**（`cp`+md5 还原 + 重建）：① 去掉 user 行恢复 ⇒ 时间可见断言红；② 去掉 `irqentry_exit` 工作循环 ⇒ 信号/抢占断言红；③ 去掉 supv 窗口屏蔽 ⇒ 启动稳定性红（按频率披露）。
6. 不回归：`check-linux-k0`–`k6` 全 rc=0；`check-config-pins`、`check-patch-tree`（linux 段 0 problem）、`check-component-changelog`、`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. `ISS-500` 关闭；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`（`process.c`/`async_trap.S`/`time.c`/`entry_common.c`/`trap.S` 及必要头）、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues.yaml`、本任务书。
3. **不改** `spec/`、`.tao/contracts/`、`Makefile`、`components/qemu/**`、`components/musl/**`；语义/契约变更须先经用户确认。
4. 组件补丁经 `make_patch.py linux` 重导；不改版本号；术语「bank = 寄存器组」；大端/64 KiB 页/`IP=当前指令` 口径按 `MEMORY.md`。
5. 禁以「重试直到绿」掩盖竞态；启动稳定性按批次统计并披露频率。
6. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。

## 待裁定

- `ADR-0059` 的 decision 清单（早退帧写 cg5 三字段、`irqentry_enter/exit` 的调用点、user 行打开时机、是否保留单帧静态 staging）；用户逐条确认后 `Accepted` 才派单。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
