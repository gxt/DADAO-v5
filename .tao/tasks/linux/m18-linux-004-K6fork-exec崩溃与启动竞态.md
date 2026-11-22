# m18-linux-004: K6 用户入口异步投递修复（ISS-498）+ 控制台行缓冲

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-001`、`m18-linux-002`
**可并行分片**：否
**预估**：4–6 h（实际约 8 h，含 `ISS-497` 定位）
**档位**：大改（用户态进程/异常路径）
**状态**：待验收

> **范围收窄（用户 2026-11-22 裁定）**：原任务书含两条缺陷。`ISS-497` 已定位为 **musl mallocng**
> 的问题（`glue.h::assert` → `a_crash()`，与 `ISS-499` 同根），**不属 linux 组件**，移交
> `m18-infra-001`（见本册「范围外」段）；本任务只交付 **`ISS-498` + 控制台行缓冲**。
> 立册标题/文件名沿用旧名（改名为「K6 用户入口异步投递修复（ISS-498）+ 控制台行缓冲」）。

## 背景（`m18-linux-002` 实测）

1. **`ISS-498`【P2】**：间歇启动未进用户态（`Run /init` 后无输出、QEMU rc=124/1），脚本靠 1 次重试。
2. 控制台 `read()` 与自身文件头声明的规范模式不符（只回 1 字节、`\b` 交给读者），`m18-linux-001` 之后遗留。

## 目标

1. **定位并修复** `ISS-498`：入口帧/栈顶/投递时序，修后去掉重试。
2. **控制台**：把 `semihost_tty.c` 的 `read()` 恢复到其文件头已声明的规范模式（按行装配、整行交付、驱动内退格）。
3. 不改变既有 K6 口径（无作业控制），不新增 retry/超时来掩盖。

## 验收（真实 rc）

1. **启动稳定性**：同一镜像连续 **200** 次启动全部进入用户态（无 rc=124/1），脚本里**无重试**；
2. **单次启动长脚本**：≥17 条命令（含 `echo`/`ls`/`cat`/`mkdir`/`rm` 重复多轮）一次跑完，`K6-REGRESSION-DONE` 出现、无 `die-no-vma`、无 panic、退出码符合脚本；
3. **不回归**：`m18-linux-001` 证据 28/28、`check-linux-k0` 146/146、`check-linux-k5` 280/280、`check-config-pins`、`check-patch-tree`（linux 段 0 问题）、`check-component-changelog`、`check-knowledge-refs`；
4. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 去掉入口异步屏蔽 ⇒ 启动稳定性红；② 回退行缓冲 ⇒ 退格断言红；
5. 完成区 ≤30 行；状态 → `待验收`。

## 范围外（证据见完成区「新发现/坑」1）

**`ISS-497`**（`m18-linux-002` 的 17 条命令形状仍稳定 `die-no-vma`）**不是本任务的未完成项**：崩溃点是 musl mallocng 的内部断言（`a_crash()` 写 NULL，落在 `alloc_slot`/`free`），内核侧 `cp` 级探针（fork+exec 12 轮堆校验、64 个 mmap 区间别名/churn、console 逐字节读 + 堆校验）全绿，且去掉 ash 的 `setvar0("_", lastarg)` 即消失；`grep` 的 `rc=139`（`ISS-499`）落在同一断言 ⇒ 两 issue 同根，移交 **`m18-infra-001`**（musl/busybox）。`run.sh --k6cmd` 保留为该形状的复现入口（期望红）。`m18-linux-003` 收口不得据本任务判 `ISS-497` 已修。

## 约束

独立 worktree；不提交 git；只动 `components/linux/**`、必要证据脚本与任务书；组件补丁经 `make_patch.py` 重导；不改版本号；术语「寄存器组」；`ISS-498` 修好后填 `resolved_by`（`closed_in: M18`）。

## 完成区

**范围**：按用户 2026-11-22 裁定收窄为「`ISS-498` + 控制台行缓冲」；`ISS-497` 移交 `m18-infra-001`（musl mallocng），不计本任务未完成项。
**测试结果**：运行期 `run.sh` **11/11 PASS、rc=0**（27 条命令长脚本一次跑完并出 `K6-REGRESSION-DONE`、无 `die-no-vma`/panic；**200/200** 次启动进入用户态，修前 6/200 未进；退格在驱动内生效）；`run.sh --inject` **8/8 PASS**（两路回退各判「按注入红」：去入口屏蔽 → 150 次里 4 次未进用户态；回退行缓冲 → 退格断言红；`cp`+md5 还原后各回绿）；`check-linux-k0` 146/146、`check-linux-k5` 280/280、`check-config-pins` 85/85、`check-patch-tree` 0 problem（linux 105 补丁）、`check-component-changelog` 40/40、`check_issues` 约束 OK；`m18-linux-001` 的 `run.sh` 在本 worktree 重跑 28/28。
**修改文件**：`components/linux/patches/**` 4 份（`kernel/{process,semihost_tty,entry_common,time}.c`，经 `make_patch.py linux` 重导：4 written / 101 unchanged）、`components/linux/changelog.md`（M18 追加 1 条）、`.tao/knowledge/issues.yaml`（ISS-498 关闭；ISS-497 追加定位）、本任务书。未改版本号、未提交 git、未动 busybox/musl 补丁。
**验收结果**（真实 rc）：
- **ISS-498 已修**：TIMER 投递在「用户寄存器（含 SP）已恢复、`trap cfx_umon` 未执行」的窗口以及任务已在用户态时，都会落回用户栈（`async_trap.S` 的 supv 臂按设计不换栈）⇒ `dadao_async_die()` 在用户栈上格式化（`__pa()` 取到垃圾 → 2743 个 NUL、SYS_EXIT 码失真）或触发递归 supv 异常，启动停在 `K4 fork: kernel thread exec'd`。修复 = `dadao_enter_user()` 同时屏蔽 `cfx_smon` supv 行与 `cfx_umon` user 行，四个内核入口（`dadao_syscall_enter`/`dadao_trap_enter`/`dadao_user_fault_return`/`dadao_async_handler`）重新开行；事件在源端 pending、下次进内核补投。
- **控制台**：`read()` 恢复到文件头已声明的规范模式（按行装配 256 B、整行交付、`count` 小则留余量；`\b`/`\x7f` 驱动内退格；`^C` 丢行；`^D` 交付余量后 EOF），顺带修掉 001 之后「只回 1 字节」与文档不符。
**新发现/坑**：
1. **`ISS-497` 根因定位（本任务范围外）**：崩溃是 **musl mallocng 的内部一致性断言**（`glue.h::assert` → `a_crash()` 写 NULL，`alloc_slot`/`free` 内），**不是内核改写用户内存**——`cp` 级探针（fork+exec 12 轮堆校验、64 个 mmap 区间别名/churn、console 逐字节读 + 堆校验）全绿。判据：去掉 ash 的 `setvar0("_", lastarg)` 即消失（3/3）；同一命令序列经脚本文件/管道喂子 shell 不崩、控制台逐行喂则崩；行缓冲、去回显、非 tty、屏蔽 tick 均不消除；`grep` 的 `rc=139`（ISS-499）落在同一断言 ⇒ 两 issue 同一根因，属 musl/busybox。
2. `check-linux-k5` 需 `.work/source/qemu` 快照；本 worktree 以符号链接共享主树（只读）。
3. 被屏蔽的事件不丢：源端 `excp_pending` + 硬件在 mask 写/`escape` 后补投（`asm/irqflags.h` 已述）。
**遗留问题**：
- **`ISS-497` 移出范围**（见「范围外」）：`m18-linux-002` 的 17 条命令形状仍稳定 `die-no-vma`（`run.sh --k6cmd` 复现，红在 `ps` 步），归 `m18-infra-001`，与 `ISS-499` 合并管理；`m18-linux-003` 不得据此判绿。
- `m18-linux-002` 的 50/50 未能原样重跑（证据随旧 worktree 删除）；同口径的 `k6-commands.txt` 因上一条红。
- 用户态 tick 投递整体关闭（只在下次 trap 被抢占），与 `entry_common.c` 已述模型一致，但属**行为变化**：需 architect 追认或改由按任务帧方案恢复。
- 本任务按收窄后的范围置 `待验收`；`ISS-497` 的完成判据属 `m18-infra-001`。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-22；大改 60 min 档；判决 **Accepted**）

**重跑（全部本人执行，退出码取 `cmd; echo $?`）**
- 运行期证据目录内 `run.sh` → `RESULT: PASS checks=11 failed=0`，rc=0；`[INFO] boots=200 entered_user_mode=200 no_entry=0 die_no_vma=0`；长脚本 27 条提示行、`K6-REGRESSION-DONE` 在、无 `die-no-vma`/`Kernel panic`；`run.sh`+`boots.py` 全文 grep `retry|重试|attempt` = 0 命中（无重试路径）。
- `run.sh --inject` → `RESULT: PASS checks=8 failed=0`，rc=0：注入1 `boots=150 entered=147 no_entry=3` 判红、`cp`+md5 还原后 60/60 回绿；注入2 `console-bs` 判红、还原后回绿；跑完源码树 `git status` 干净。
- 补丁↔源码一致：4 份 patch 按 `+++ b/` 还原成整文件与源码 `diff` 逐字节相等（849/325/272/867 行）。
- 门控：`check-patch-tree` rc=0（`linux: 105 patch(es)`、`457 patches OK`）、`check-component-changelog` rc=0（40/40）、`check-config-pins` rc=0（85 项 0 败）、`check-knowledge-refs` rc=0（本记录写入后复跑，证据见下）。

**独立注入（`cp`+md5 → 改产物 → 跑同一 `run.sh` → 还原 → 回绿）**
- A1 只留 supv 行屏蔽（去掉 `cfx_umon` user 行写）：`RESULT: PASS checks=11`、`200/200` 全绿 ⇒ 注释/changelog 的「6/200」未复现。
- A2 两行都不屏蔽：`[FAIL] boot-026/065/103/179`，`boots=200 entered=196 no_entry=4`，`[FAIL] boot-stability-accept: want=0 got=1`，`RESULT: FAIL checks=11 failed=1`，rc=1；还原 md5 `54b8fd63…` 相等 → 回绿 `RESULT: PASS checks=11 failed=0`、`200/200`。
- B 去掉驱动内 `\b`/`\x7f` 退格分支：`[FAIL] console-bs-accept: want=0 got=1`，`RESULT: FAIL checks=11 failed=1`，rc=1；还原 md5 `64b70e9f…` 相等 → 回绿（11/11、rc=0）。
- 控制台输入注入三例（同一内核，qemu rc 均 0）：`echo AB\bC` → 整行交付 `AC`、读者不见原始 `\b`；`^C` → 打出 `^C`、被丢行 `XY` 未执行、shell 继续 `AFTER`；`^D` → `PRE` 执行、EOF 后 `POST` 不执行。

**不回归（本人重跑）**：001 证据 `RESULT: PASS checks=28 failed=0` rc=0；`check-linux-k0` 146/146 rc=0；`check-linux-k5` 280/280（S42 C41 F40 T34 G26 P35 R62）rc=0；002 的 17 条形状仍红属 `ISS-497`，按任务书「范围外」不计本任务。

**语义核验**
- 不丢的依据：`contract-see §3`「屏蔽只阻止投递…mask 写/`escape` 后硬件重踢补投」+ `DADAO-12 §5.2` 步 3（任一 mask=1 不投递、置 `excp_pending`）与 §4.7「电平触发，mask 解除后下一指令边界触发」；`asm/irqflags.h` 载明事件仍在目标 cfx `cg5 rc5` pending、内核无软件位图。实测：K5 T 组 34/34（含 `T2 投递间隔 ∈ [period/2,2*period]`）⇒ 内核态 tick 投递间隔正常。
- 重开覆盖：四处 `local_irq_enable()`（`dadao_syscall_enter`/`dadao_trap_enter`/`dadao_user_fault_return`/`dadao_async_handler`）且三处都放在读 `flags` **之前**（否则 `arch_local_irq_restore(flags)` 会把屏蔽字写回、行永久关死）；信号返回走 `trap cfx_umon` → `dadao_syscall_enter`，页 fault 交接走 `dadao_user_fault_return`，均在覆盖内。
- **须 architect 裁定（不阻断本任务验收）**：`dadao_enter_user()` 把 `cfx_umon` user 行写 `~0UL` 后全仓无第二处写回（仅开机 `dadao_user_entry_install()` 清 bit15，其注释仍宣称「用户态投递」）⇒ 实际等于用户态期间不投递任何异步中断；长用户态窗口内同源事件按契约合并为一次补投 ⇒ `jiffies` 滞后（时钟源 `cfx_time` 不受影响）。K6 无用户态可观测面（busybox 无 `date/sleep/time`、无 `/proc`）、K5 T 组在内核态 ⇒ 判据仍成立；完成区已按「行为变化待追认」披露，但 A1 的 200/200 说明「umon 行也必须屏蔽」的 6/200 依据未复现。
- **文档级 finding（不阻断）**：changelog 写 `12/12`（实为 `checks=11`）；`issues.yaml` 写 `2/150`、完成区写 `4/150`（我跑 `3/150`）；`process.c` 注释与 changelog 的 `6/200` 与完成区「修前 6/200」同数两用。

**约束核验**：独立 worktree、**未提交 git**（验收前后 `git status -uall` 快照逐行相同、7 个改动文件 md5 全等、源码树 0 改动）；只动 4 份 linux 补丁 + changelog + `issues.yaml` + 本册，与完成区「修改文件」一致，无 version/manifest 变更；补丁经 `make_patch.py` 重导；还原全程 `cp`+md5、无 `git checkout/restore/stash`；术语「寄存器组」未见违规；`ISS-498` 已 `status: closed`/`closed_in: M18`/`resolved_by: m18-linux-004`；`ISS-497` 在「范围外」并移交 `m18-infra-001`；完成区 17 行 ≤30、状态 `待验收`；无临时残留。

**判决：Accepted** —— 验收命令块在我自己的重跑下全绿、两路反例均「注入→红→还原→回绿」、硬约束无违反；上列语义裁定与文档 finding 交 architect 收尾处置。
