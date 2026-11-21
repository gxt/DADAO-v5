# M14 归档（Archive）

> **归档日期**：2026-11-22 ｜ **范围**：M14 里程碑（2026-11-13 起，**2026-11-22 达成**）的全部任务书与相关记录 —— **Linux bring-up（K0–K5）**
> **归档判据**：任务书字段 `**项目里程碑**：M14`（**76** 册 = infra 5 / integ 1 / linux 44 / llvm 7 / qemu 7 / spec 9 / testcases 3；全部 **76 `已验证`**；`m14-linux-021` 为「已验证 + `> **已退役**` 注记」——未实施、正文由 `026` 接手）；任务流水冻结 **76** 条；`issues.yaml` `closed_in: M14` 关闭项 **10** 条（见 `issues-closed.md`，`tools/infra/archive_issues.py --check` 可复核）；`MEMORY.md` 纯 M14 行移除、摘要见 §4。
> **自归档说明**：`m14-integ-001`（本归档任务自身）按 `docs/Process-04 §4.1` 迁入 `integ/`；§1 `integ` 计数（1）与 §2 流水（76 行）均已含它。
> **退役说明**：`m14-linux-021`（clocksource/clockevent 接线）**未实施**，正文由 `m14-linux-026` 原样接手并落地 ⇒ 册内标 `> **已退役**` 注记（状态仍 `已验证`，与 `013/014/019` 同形；归档门控不放宽），见 §2 与 `m14-retrospective.md §5`。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m14-retrospective.md`，后续路线见 `.tao/knowledge/milestones-m15.md` / `milestones-m16.md` / `milestones-m18.md`。

## 1 任务清单（76 个，按模块）

| 模块 | 数量 |
|---|---|
| infra | 5 |
| integ | 1 |
| linux | 44 |
| llvm | 7 |
| qemu | 7 |
| spec | 9 |
| testcases | 3 |

> 任务书位于同目录下模块子目录（`git mv` 保留 `R` rename 历史）。模块目录按 M14 实际出现者建（`infra`/`integ`/`linux`/`llvm`/`qemu`/`spec`/`testcases`；M14 无 `chipyard`/`gem5` 册）——`linux` 自 M14 起在归档白名单内（用户 2026-11-15 裁定）。

## 2 任务流水（冻结）

> **冻结日期**：2026-11-22。74 条「已验证」行按活台账 `.tao/knowledge/milestones-m14.md`「已验证」表**原值**搬入（状态按任务书规范化；次序 = 完成时间倒序，与台账一致），另加 `m14-linux-021`（`已验证` + 已退役注记）与本归档任务（`已验证`）两行；台账文件随本归档删除。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| m14-integ-001 | 已验证 | 2026-11-22 | M14 归档（三件套 + 76 册迁入，含自归档） |
| m14-linux-021 | 已验证 | 2026-11-22 | **已退役**（未实施；正文由 `m14-linux-026` 原样接手落地） |
| m14-linux-029 | 已验证 | 2026-11-22 03:14 | K5 收口门控 `check-linux-k5`（280/280；K3 整体退役；§4a 退役台账） |
| m14-linux-028 | 已验证 | 2026-11-21 21:39 | 用户态 64 KiB ABI（`AT_PAGESZ`/`mmap` 对齐/ELF 段/`brk`；`mmap_base`+`mmap_min_addr` 页对齐；`ARCH_FORCE_MAX_ORDER=13`） |
| m14-testcases-007 | 已验证 | 2026-11-21 20:57 | M14 测试归位 `tests/unit/linux/`（26 个 probe/gate + 3 资产；构建工具留 `tools/linux`） |
| m14-linux-026 | 已验证 | 2026-11-21 18:51 | clocksource(`cfx_time`) + clockevent(`cfx_hart`) 通用框架（`time_init` 接线；探针 52/52；K2 time 组不退役） |
| m14-linux-027 | 已验证 | 2026-11-21 17:13 | 信号与退出面（SIGSEGV 投递 + `exit`/`exit_group` + `setrlimit(RLIMIT_STACK)` 继承；探针 157/157） |
| m14-infra-005 | 已验证 | 2026-11-21 16:32 | musl 信号帧 2048 B 四组 + `SA_RESTORER`/`__restore_rt` + `MINSIGSTKSZ` 2376（端到端 36/36） |
| m14-linux-046 | 已验证 | 2026-11-21 15:29 | 信号帧与投递（2048 B 四组/匿名 union；`rt_sigframe`/`rt_sigreturn`/`force_sig`；`SA_RESTORER`；探针 101；契约未改） |
| m14-linux-045 | 已验证 | 2026-11-21 04:26 | 通用 entry/exit 循环（TIF 消费 + syscall/irqentry；撤通用 hunk；series 98） |
| m14-llvm-007 | 已验证 | 2026-11-21 01:52 | DADAO `evaluateFixup` 回到 ELFObjectWriter 判据（同节 weak/global 发重定位；9 处改绑） |
| m14-linux-047 | 已验证 | 2026-11-21 01:32 | `sched_clock` 改绑后 S7 panic 根因修复（k4/k5 探针补 lazy-TLB 引用配对；arch 侧） |
| m14-linux-044 | 已验证 | 2026-11-20 15:16 | Kconfig 补齐（`GENERIC_SCHED_CLOCK`/`GENERIC_IRQ_ENTRY`/异常表 uaccess+`fixup_exception`；series 96） |
| m14-linux-035 | 已验证 | 2026-11-20 11:29 | 缺页路径回归通用 mm 流程（乙：rmap/LRU/filemap/权限闸；N27 与 GUP 修好；series 92） |
| m14-linux-038 | 已验证 | 2026-11-20 10:23 | 时间/时钟差异盘点（19 条；P0 5：clocksource/clockevent 未注册、tick 记账缺失） |
| m14-linux-041 | 已验证 | 2026-11-20 10:14 | 进程/线程与上下文切换差异盘点（19 条；`schedule_tail` 拿错 prev） |
| m14-linux-042 | 已验证 | 2026-11-20 10:03 | trap/异常/中断差异盘点（27 条；P0 1：user_mode 恒 0 威胁 035） |
| m14-linux-040 | 已验证 | 2026-11-20 09:53 | Kconfig/选型差异盘点（30 条；缺 select 16，含 TRACEHOOK/SECCOMP_FILTER/GENERIC_SCHED_CLOCK） |
| m14-linux-043 | 已验证 | 2026-11-20 09:45 | 启动/初始化差异盘点（19 条；早期 current=NULL、生产镜像走不到 rest_init） |
| m14-linux-039 | 已验证 | 2026-11-20 09:31 | 信号/退出差异盘点（29 条；P0 18：信号机制整体缺失） |
| m14-linux-037 | 已验证 | 2026-11-20 09:30 | syscall/ABI 差异盘点（25 条；entry/exit 工作项引用 0） |
| m14-linux-036 | 已验证 | 2026-11-20 09:28 | mm/缺页/页表差异盘点（25 条；P0 3 条） |
| m14-linux-025 | 已验证 | 2026-11-20 07:49 | futex 与原子性（`lr.t`/`sc.t`；WAIT 原子/WAKE 不丢；171/171） |
| m14-linux-024 | 已验证 | 2026-11-20 01:31 | 用户态 clone/线程（CLONE_BACKWARDS+SETTLS+THREAD；三处内核缺陷修复） |
| m14-linux-023 | 已验证 | 2026-11-19 22:40 | 用户态 syscall 闭环（C′：`__SC_LONG` + 内核 argmask 取参 + 五载体门控；`brk` 实测） |
| m14-linux-020 | 已验证 | 2026-11-19 17:07 | 内核线程（`kernel_thread` 钩子 + `kthreadd`/`kthread_create`；探针 110/110） |
| m14-linux-018 | 已验证 | 2026-11-19 15:32 | COW（复制旧内容/改 PTE/失效；W1–W5 86/86、5 路注入、eager-copy 反例纳入证据） |
| m14-linux-019 | 已验证 | 2026-11-19 12:25 | 已并入 m14-linux-017（栈增长 S1–S6 随 017 交付，`k4_stack_probe` 44/44） |
| m14-linux-017 | 已验证 | 2026-11-19 12:14 | 上下文切换/U-mode 帧往返（F55 rbtp、F59/F60 cfx 掩码按源 cfx、pgd 复制；S5+S7 绿 51/51） |
| m14-spec-009 | 已验证 | 2026-11-18 21:55 | `escape` 恢复 `inner_cfx_code`（cg5 rc1 `excp_prev_cfx_code`；注入删恢复行 ⇒ `CFXESC` 0x31） |
| m14-linux-031 | 已验证 | 2026-11-18 10:31 | initramfs 集成 busybox（`/init` 脚本 → `sh`；332116 B、确定性；QEMU 实跑等 K5） |
| m14-linux-030 | 已验证 | 2026-11-18 09:26 | K6 busybox 1.38.0 静态构建接入（官方源锁定、11 applet、无 PT_INTERP、幂等；证据 16/16） |
| m14-linux-016 | 已验证 | 2026-11-18 00:20 | 进程抽象 + fork/execve 基础 + kernel_thread/kthreadd + 最小 U-mode 入口（F5）；101/101、5 路注入、k0-k3 全绿 |
| m14-testcases-006 | 已验证 | 2026-11-17 21:53 | 固件：除 hmon 外 8 个已实现 cfx 的 supv 四轴放行 smon（含负例；bootrom b662183a） |
| m14-linux-022 | 已验证 | 2026-11-17 19:39 | 异常帧扩四组（rd/rb/ra/rf，2064B；ra/rf 用 ldm.o/stm.o；k2 170/170、10 路注入） |
| m14-spec-008 | 已验证 | 2026-11-17 16:02 | DADAO-13 §1/§2 并入 DADAO-12 §3.4/§4.4（只留引用）；Kaiwu 9 行同步；版本号未变 |
| m14-linux-015 | 已验证 | 2026-11-17 14:42 | K3 收口门控（B/M/F/C/T/X/R 263/263；§4a 退役 4 改限定语 0 删除；L3 check-arch rc=0） |
| m14-linux-012 | 已验证 | 2026-11-17 11:48 | 页故障通道 + 按需分页（子原因解码、共享零页换新页、ADWBFAIL/NONPTW 先于 VMA、重试上限；196/196、9 路注入） |
| m14-qemu-007 | 已验证 | 2026-11-17 08:26 | K14 长串/多分块覆盖（640B 跨 3 块）+ `cpu.c` 过时注释订正；K1 112/112、4 路注入 |
| m14-testcases-005 | 已验证 | 2026-11-17 07:41 | TLB 探针 15 例 29 检查（`sub_one_hot` 绝对位；三条目遇错即停 + 内存窗口 ILLI）；`check-arch` 15 成员绿 |
| m14-linux-010 | 已验证 | 2026-11-17 07:34 | IE 旋钮收敛为 monitor 单行（`ISS-455/454`）+ `contract-see §6.4` 去实例化；`SINGLE_ROW_PATCHES` 空表+two-row 反向注入 |
| m14-qemu-005 | 已验证 | 2026-11-17 02:49 | 页表异常子原因 18 位 + TLB 对齐（遇错即停三条目；`cause_check` 校验配对/恰一位；904/904） |
| m14-qemu-004 | 已验证 | 2026-11-17 00:52 | `SYS_READC`/`SYS_FLEN` 取字缓冲改按 PA（`ISS-452`；钩子 + 复用 `ptw_walk`；K1 111/111） |
| m14-qemu-003 | 已验证 | 2026-11-16 23:08 | 异步源轴 mask 改按当前运行模式 monitor 行（`ISS-455`）；C10 单行镜像先红后绿、156/156 |
| m14-linux-014 | 已验证 | 2026-11-16 22:05 | **已退役**（用户裁定栈增长归 K4：`VM_GROWSDOWN` 由 `execve` 创建，K3 无用户态；`S1`–`S6` 判据已交接） |
| m14-linux-013 | 已验证 | 2026-11-16 21:59 | **已退役**（用户裁定 COW 全归 K4：K3 无 `fork`/无文件 mmap、零页已在 012 用掉且不复制） |
| m14-qemu-006 | 已验证 | 2026-11-16 21:01 | Vast 同步异常单路由进 monitor（删 staged 模型；`ILLI` 的 `cause_info` 回读触发指令；28 oracle 按 spec 复推） |
| m14-linux-011 | 已验证 | 2026-11-16 19:41 | 内核页表原语与 TLB 维护（修 `pmd_*` 三处 VA→PA；`tlb_control` + 10 flush；`cause&0xffff`；k3_pt 116/116） |
| m14-spec-006 | 已验证 | 2026-11-16 16:59 | K3 的 TLB 规范与契约（`Kaiwu §3.1` 三条约定 + `contract-tlb` 43 条 + 13 条探针建议） |
| m14-spec-007 | 已验证 | 2026-11-16 16:23 | `cause_id` 子原因编码（wyde2=CFXPERM/wyde3=CFXMEM，18 位；两册 spec + 契约 + 锁） |
| m14-linux-009 | 已验证 | 2026-11-16 15:22 | K2 收口门控 `check-linux-k2`（B/E/T/M/S/X/R 七组 104 项；入 L2；ISS-457 两条断言） |
| m14-infra-004 | 已验证 | 2026-11-16 10:24 | 测试机改名 `Machine-v5`→`Kaiwu` + QEMU 串 `kaiwu-tiny/vast`（547 文件；spec 锁重算；旧名失效） |
| m14-linux-008 | 已验证 | 2026-11-16 08:25 | K2 中断使能与屏蔽（`irqflags` 按当前 cfx 两行旋钮、`time.c` 临界区；k2_irq 95/95、k2_time 151/151） |
| m14-linux-007 | 已验证 | 2026-11-16 06:35 | K2 时钟与定时器（`hmon` 放行 `cfx_hart`/`cfx_time` + `time.c`/`irq.c`/`async_trap.S`；HZ 现场派生、margin=period/2；time 探针 149/149） |
| m14-linux-006 | 已验证 | 2026-11-16 05:27 | K2 异常入口与 cause 分派（`trap.S` 全 GPR 保存 + 11 项表 + A′ 退出码分段；K0 119/119、K1 108/108、K2 85/85） |
| m14-qemu-002 | 已验证 | 2026-11-16 02:38 | semihosting 指针改按 PA（`SYS_WRITE0` 取串 + `SYS_OPEN` 无长度名经 target 钩子；K1 门控 +K14 6 条，108/108） |
| m14-spec-005 | 已验证 | 2026-11-15 23:55 | K2 内核侧异常/中断契约口径（`contract-see §6`：cause_info 11 项、帧无 prev_cfx、异步入口 `cfx_hart cg2 rc10`、IE 单旋钮 `cg2 rc4`） |
| m14-linux-005 | 已验证 | 2026-11-15 05:00 | K1 收口门控 `check-linux-k1`（102 项/4 路注入/入 L2）+ TLB 失效 ASID_ANY 修正（`0x2`→`0x12`） |
| m14-linux-004 | 已验证 | 2026-11-15 02:40 | K1 内核自建页表 + 写 PTBR（索引 4096/4 超页；PTE 逐位核对；负例与 4 路注入） |
| m14-linux-003 | 已验证 | 2026-11-15 00:30 | K1 早期启动到 `start_kernel`（Vast；自建栈、boot info 校验、semihosting 早控制台、开时钟前退出） |
| m14-llvm-006 | 已验证 | 2026-11-14 09:10 | 符号差判据统一（移到 `evaluateFixup`）+ 放行 `.set` 绝对值符号（lit 176/176） |
| m14-llvm-005 | 已验证 | 2026-11-14 08:10 | 标签差立即数报错 + ABS48 wyde 写回（`ISS-424` 关闭；lit 174/174） |
| m14-llvm-002 | 已验证 | 2026-11-14 06:20 | DADAO SSP 后端（`STACK_CHECK_GUARD`/`CHECK_FAIL`；guard 模式 fail-closed；9/9 + E2E 66） |
| m14-qemu-001 | 已验证 | 2026-11-14 05:40 | Vast 最小 smon（boot info 15 字段 + 1 超页 index 4096 + PTBR=0/ptw_enable=1 + VA 入口） |
| m14-llvm-004 | 已验证 | 2026-11-14 04:10 | DWARF 编号（256 寄存器）+ CFI（RA=ra63/255；`.eh_frame` absptr；修 `llvm-mc` abort） |
| m14-infra-003 | 已验证 | 2026-11-14 03:40 | K0 收口门控 `check-linux-k0`（119 项；K1–K13；10 路注入；入 L2） |
| m14-linux-002 | 已验证 | 2026-11-14 03:00 | `arch/dadao` 骨架出 vmlinux（56 补丁；跨度 3.06 MiB、REL26 余量 29.04 MiB） |
| m14-llvm-003 | 已验证 | 2026-11-14 02:30 | `-fpatchable-function-entry`（`swym 0` 槽；N=1/2/4、M 前置；lit 166/166） |
| m14-llvm-001 | 已验证 | 2026-11-14 01:00 | LLVM 工具族补齐（ar/ranlib/strip + link/config/profdata/size/cov；安装根 8 工具、功能断言 104 项） |
| m14-spec-004 | 已验证 | 2026-11-14 00:15 | `contract-syscall` 内核入口口径（放行/自配、cause_info 推导、clone/execve 留合约+musl） |
| m14-spec-003 | 已验证 | 2026-11-13 22:15 | 内核 VA 窗口改 `[2TiB,3TiB)`（spec/契约/YAML/检查器/ADR-0051 同笔；旧地址仅存作废段） |
| m14-infra-002 | 已验证 | 2026-11-13 21:02 | initramfs（确定性 newc）+ musl init + semihosting 退出闭环（证据 79/79） |
| m14-spec-002 | 已验证 | 2026-11-13 21:00 | 内核侧 syscall/errno/TLS 契约（0.10.0；§1 号表逐字不变） |
| m14-infra-001 | 已验证 | 2026-11-13 20:40 | 工具链缺口矩阵（8 行，gaps=6 blockers=0）+ `check-linux-toolchain` 门控 |
| m14-spec-001 | 已验证 | 2026-11-13 19:28 | 启动 ABI 契约（`Kaiwu §6.3`；ABI 地址=VA、M1 预建页表由 smon 建、boot info 15 字段） |
| m14-linux-001 | 已验证 | 2026-11-13 19:10 | Linux 补丁组件化（空系列首态 + 7 个 make 目标 + 路径解析；证据 69/69） |

## 3 终局证据

| 套件 | 结果 |
|---|---|
| K5 收口门控（`m14-linux-029`） | `make check-linux-k5` **rc=0、280/280**（S 42/42 C 41/41 F 40/40 T 34/34 G 26/26 P 35/35 R 62/62）；`--selfcheck` 8 次翻转全 PASS；`--all-inject` 316/316（6 路注入） |
| 阶段门控与 K0–K4 回归（`m14-linux-029` 现跑） | K0 146/146、K1 112/112、K2 170/170、k4 cow 86/86、switch 76/76、stack 44/44、kthread 112/112 全 rc=0 |
| 已知既有红（不代填绿） | `k4_fork_probe` F5 偶发挂死（`ISS-493`；A/B 各 5 跑：master 4/5 红、029 分支 4/5 红，同签名 ⇒ 既有）；`ISS-494`（kthread 竞态）登记 |
| K3 阶段整体退役 | `check-linux-k3` 与 `k3_*` 探针/自检随阶段退役（`m14-linux-029`；退役台账 `docs/Process-07 §4a.2`） |
| 内核与主流 ISA 差异盘点 | `components/linux/kernel-diff-vs-mainstream-isa.md`：八份（`m14-linux-036`–`043`）**195 条**；P0 口径不一（不可相加当紧急项） |
| 工具链缺口矩阵 | `docs/TestReports/M14-K0-toolchain-gaps.md`：8 行、**8/8 行「声明 == 实测」**、`gaps=2 (blockers=0)`（`make check-linux-toolchain`） |
| 归档门控（2026-11-22，本任务现跑） | `check-archive` **rc=0**；`check-milestones-fresh`（M15–M20 六册）rc=0 且 M14 不在列表；`check_issues` / `check-knowledge-refs` / `check-dirs` / `check-no-residue` rc=0 |
| L1 / L2 / L3 全量 | 本归档任务**不跑**测试/构建（硬约束）；M14 期未做里程碑级全量重跑 ⇒ **无该期全量 rc 记录，不代填** |

## 4 MEMORY 摘录（M14 时期）

| 项目 | 内容 |
|---|---|
| 收口 | M14 = **Linux bring-up**，K0–K5；`check-linux-k5` 280/280；K3 整体退役；**K6（shell/命令回归/门控）移 M18**，M14 不声称「能当 Linux 用」 |
| 内核 | 基线 Linux `7.2.10` + `arch/dadao`（补丁系列 103 条）；平台 = QEMU system **单核 Vast**；控制台 = **semihosting**；启动传参 = 固定 **boot info 15 字段**；内核 VA 窗口 `[2TiB,3TiB)`；**64 KiB 页 ABI** |
| 契约 | 启动 ABI（`Kaiwu §6.3`）+ `contract-syscall` / `contract-tlb`（43 条）/ `contract-see §6`；`cause_id` 18 位子原因；`escape` 恢复 `inner_cfx_code`（`cg5 rc1`） |
| 工具链 / 模拟器 | LLVM：ar/ranlib/strip、SSP、`-fpatchable-function-entry`、DWARF 256 寄存器 + CFI、符号差判据、同节 weak 发重定位；QEMU：smon 身份页表与交接、semihosting 按 PA、cause 子原因、Vast 同步异常单路由进 monitor |
| 测试 / 基础设施 | initramfs（确定性 newc）+ musl init；busybox 1.38.0 静态接入；M14 探针/门控归位 `tests/unit/linux/`；测试机整机名 `Kaiwu`（`ADR-0055`）；工具链缺口矩阵 + `check-linux-toolchain` |
| 判据演进 | `docs/Process-07 §4a`（阶段推进即退役过时判据）；门控 `CONFIG` 钉子（`ISS-470`）；既有偶发红**登记**而非重试（`ISS-493/494`）；自检/探针须有可达 FAIL |

> 摘录自 `.tao/knowledge/MEMORY.md` 的 M14 事实行（混合了后续里程碑内容的行只摘 M14 部分或整行不摘）。活 `MEMORY.md` 已移除纯 M14 滚动行（历史由本目录承载）。

## 5 指针

- 里程碑定义/达成：本目录 `README.md §1/§2`；后续路线 `.tao/knowledge/milestones-m15.md`（M15）、`milestones-m16.md`、`milestones-m17.md`、`milestones-m18.md`（K6）、`milestones-m19.md`、`milestones-m20.md`
- 里程碑回顾：本目录 `m14-retrospective.md`
- 关闭 issue 快照：本目录 `issues-closed.md`（10 条；`tools/infra/archive_issues.py --milestone M14 --check .tao/archive/M14/issues-closed.md` 可复核）
- 差异盘点索引：`components/linux/kernel-diff-vs-mainstream-isa.md`
- 遗留台账：`.tao/knowledge/issues.yaml`（M14 期 open 项已转 `M18`）、`.tao/knowledge/discussing.md`
- 归档规范：`docs/Process-04-里程碑归档规范.md`；门控：`tools/infra/check_archive.py`
- 跨文件引用说明：本归档**未更新**历史引用；凡引用 `.tao/tasks/**` 中 M14 任务书路径者，其内容现位于本目录（历史指针）。
