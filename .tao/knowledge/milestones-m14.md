# 项目里程碑

> **项目里程碑 = M14**（M14 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12/M13 已归档（`.tao/archive/M12/`、`M13/`））

> **本页只维护 M14 任务台账**：M11 及以前已归档（`.tao/archive/M11/`）；历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M14 定位（用户 2026-11-13）**：**Linux bring-up**。基线 Linux `7.2.10`；平台 = QEMU system 模式**单核**；控制台 = **semihosting**（不引入 UART、不新增 cfx）；initramfs = 静态 musl `init`；启动传参 = **固定 boot info 结构**（不引入设备树）；TLB 规范在 K3、K0 不定义；不引入 cache/LLC。参考实现（`DADAO` / `DADAO-0628`）只借鉴阶段划分与踩坑，`arch/dadao` 按当前冻结契约重写。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

- **派单即移入**：「待开始」表 = 尚未派单；**派单时**把该行移入「进行中」表并填**派单时间**（不引入新状态）。
- **派单时间**：`YYYY-MM-DD HH:MM`，派单动作发生时由主会话填写。
- **预估时间**：人工估值，只作参考；格式 `N h` / `N–M h` / `N 天` / `N–M 天` / `N min`。
- **完成时间**：`YYYY-MM-DD HH:MM`；「已验证」表按完成时间**倒序**（同时间按编号升序）。
- **一句改动**：≤120 字符，只作索引，细节在任务书。

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m14-linux-021 | 3–4 h | clocksource/clockevent 通用框架（**已后移 K5**，不派单，保留作交接材料） |


| m14-linux-032 | 3–4 h | K6 shell 启动（busybox sh + semihosting + 前台执行，无作业控制） |

| m14-linux-033 | 2–3 h | K6 基础命令回归（sh 内 5 条命令 + 退出码） |

| m14-linux-034 | 3–4 h | K6 收口门控 `check-linux-k6`（代表例 + §4a 退役） |
| m14-linux-023 | 4–6 h | 用户态 syscall 闭环（umon 入口+分发表+errno rd8 负值+TLS rb3 入口保存/恢复） |
| m14-linux-024 | 3–5 h | 用户 clone/线程（CLONE_VM/SETTLS/THREAD + TLS 用户面；子 rd8=0+父返 tid） |
| m14-linux-025 | 3–4 h | futex 与原子性（WAIT 原子/WAKE 不丢唤醒/用户 lr+sc 不跨 syscall） |
| m14-linux-026 | 3–4 h | clocksource(cfx_time)+clockevent(cfx_hart) 通用框架（原 021 后移） |
| m14-linux-027 | 4–6 h | 信号与退出（SIGSEGV 投递+信号帧 4 组+exit+setrlimit/RLIMIT_STACK 继承） |
| m14-linux-028 | 2–3 h | 用户态 64 KiB ABI（AT_PAGESZ=65536/mmap 对齐/ELF 段对齐/brk+mmap） |
| m14-linux-029 | 5–6 h | K5 收口门控 check-linux-k5（用户态闭环代表例+§4a 退役） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m14-linux-020 | 2026-11-19 15:32 | 2–3 h | 内核线程（`kernel_thread`/`kthreadd`/`kthread_create`） |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m14-linux-018 | 2026-11-19 15:32 | COW（复制旧内容/改 PTE/失效；W1–W5 86/86、5 路注入、eager-copy 反例纳入证据） |
| m14-linux-019 | 2026-11-19 12:25 | 已并入 m14-linux-017（栈增长 S1–S6 随 017 交付，`k4_stack_probe` 44/44） |
| m14-linux-017 | 2026-11-19 12:14 | 上下文切换/U-mode 帧往返（F55 rbtp、F59/F60 cfx 掩码按源 cfx、pgd 复制；S5+S7 绿 51/51） |
| m14-spec-009 | 2026-11-18 21:55 | `escape` 恢复 `inner_cfx_code`（cg5 rc1 `excp_prev_cfx_code`；注入删恢复行 ⇒ `CFXESC` 0x31） |
| m14-linux-031 | 2026-11-18 10:31 | initramfs 集成 busybox（`/init` 脚本 → `sh`；332116 B、确定性；QEMU 实跑等 K5） |
| m14-linux-030 | 2026-11-18 09:26 | K6 busybox 1.38.0 静态构建接入（官方源锁定、11 applet、无 PT_INTERP、幂等；证据 16/16） |
| m14-linux-016 | 2026-11-18 00:20 | 进程抽象 + fork/execve 基础 + kernel_thread/kthreadd + 最小 U-mode 入口（F5）；101/101、5 路注入、k0-k3 全绿 |
| m14-testcases-006 | 2026-11-17 21:53 | 固件：除 hmon 外 8 个已实现 cfx 的 supv 四轴放行 smon（含负例；bootrom b662183a） |
| m14-linux-022 | 2026-11-17 19:39 | 异常帧扩四组（rd/rb/ra/rf，2064B；ra/rf 用 ldm.o/stm.o；k2 170/170、10 路注入） |
| m14-spec-008 | 2026-11-17 16:02 | DADAO-13 §1/§2 并入 DADAO-12 §3.4/§4.4（只留引用）；Kaiwu 9 行同步；版本号未变 |
| m14-linux-015 | 2026-11-17 14:42 | K3 收口门控（B/M/F/C/T/X/R 263/263；§4a 退役 4 改限定语 0 删除；L3 check-arch rc=0） |
| m14-linux-012 | 2026-11-17 11:48 | 页故障通道 + 按需分页（子原因解码、共享零页换新页、ADWBFAIL/NONPTW 先于 VMA、重试上限；196/196、9 路注入） |
| m14-qemu-007 | 2026-11-17 08:26 | K14 长串/多分块覆盖（640B 跨 3 块）+ `cpu.c` 过时注释订正；K1 112/112、4 路注入 |
| m14-testcases-005 | 2026-11-17 07:41 | TLB 探针 15 例 29 检查（`sub_one_hot` 绝对位；三条目遇错即停 + 内存窗口 ILLI）；`check-arch` 15 成员绿 |
| m14-linux-010 | 2026-11-17 07:34 | IE 旋钮收敛为 monitor 单行（`ISS-455/454`）+ `contract-see §6.4` 去实例化；`SINGLE_ROW_PATCHES` 空表+two-row 反向注入 |
| m14-qemu-005 | 2026-11-17 02:49 | 页表异常子原因 18 位 + TLB 对齐（遇错即停三条目；`cause_check` 校验配对/恰一位；904/904） |
| m14-qemu-004 | 2026-11-17 00:52 | `SYS_READC`/`SYS_FLEN` 取字缓冲改按 PA（`ISS-452`；钩子 + 复用 `ptw_walk`；K1 111/111） |
| m14-qemu-003 | 2026-11-16 23:08 | 异步源轴 mask 改按当前运行模式 monitor 行（`ISS-455`）；C10 单行镜像先红后绿、156/156 |
| m14-linux-014 | 2026-11-16 22:05 | **已退役**（用户裁定栈增长归 K4：`VM_GROWSDOWN` 由 `execve` 创建，K3 无用户态；`S1`–`S6` 判据已交接） |
| m14-linux-013 | 2026-11-16 21:59 | **已退役**（用户裁定 COW 全归 K4：K3 无 `fork`/无文件 mmap、零页已在 012 用掉且不复制） |
| m14-qemu-006 | 2026-11-16 21:01 | Vast 同步异常单路由进 monitor（删 staged 模型；`ILLI` 的 `cause_info` 回读触发指令；28 oracle 按 spec 复推） |
| m14-linux-011 | 2026-11-16 19:41 | 内核页表原语与 TLB 维护（修 `pmd_*` 三处 VA→PA；`tlb_control` + 10 flush；`cause&0xffff`；k3_pt 116/116） |
| m14-spec-006 | 2026-11-16 16:59 | K3 的 TLB 规范与契约（`Kaiwu §3.1` 三条约定 + `contract-tlb` 43 条 + 13 条探针建议） |
| m14-spec-007 | 2026-11-16 16:23 | `cause_id` 子原因编码（wyde2=CFXPERM/wyde3=CFXMEM，18 位；两册 spec + 契约 + 锁） |
| m14-linux-009 | 2026-11-16 15:22 | K2 收口门控 `check-linux-k2`（B/E/T/M/S/X/R 七组 104 项；入 L2；ISS-457 两条断言） |
| m14-infra-004 | 2026-11-16 10:24 | 测试机改名 `Machine-v5`→`Kaiwu` + QEMU 串 `kaiwu-tiny/vast`（547 文件；spec 锁重算；旧名失效） |
| m14-linux-008 | 2026-11-16 08:25 | K2 中断使能与屏蔽（`irqflags` 按当前 cfx 两行旋钮、`time.c` 临界区；k2_irq 95/95、k2_time 151/151） |
| m14-linux-007 | 2026-11-16 06:35 | K2 时钟与定时器（`hmon` 放行 `cfx_hart`/`cfx_time` + `time.c`/`irq.c`/`async_trap.S`；HZ 现场派生、margin=period/2；time 探针 149/149） |
| m14-linux-006 | 2026-11-16 05:27 | K2 异常入口与 cause 分派（`trap.S` 全 GPR 保存 + 11 项表 + A′ 退出码分段；K0 119/119、K1 108/108、K2 85/85） |
| m14-qemu-002 | 2026-11-16 02:38 | semihosting 指针改按 PA（`SYS_WRITE0` 取串 + `SYS_OPEN` 无长度名经 target 钩子；K1 门控 +K14 6 条，108/108） |
| m14-spec-005 | 2026-11-15 23:55 | K2 内核侧异常/中断契约口径（`contract-see §6`：cause_info 11 项、帧无 prev_cfx、异步入口 `cfx_hart cg2 rc10`、IE 单旋钮 `cg2 rc4`） |
| m14-linux-005 | 2026-11-15 05:00 | K1 收口门控 `check-linux-k1`（102 项/4 路注入/入 L2）+ TLB 失效 ASID_ANY 修正（`0x2`→`0x12`） |
| m14-linux-004 | 2026-11-15 02:40 | K1 内核自建页表 + 写 PTBR（索引 4096/4 超页；PTE 逐位核对；负例与 4 路注入） |
| m14-linux-003 | 2026-11-15 00:30 | K1 早期启动到 `start_kernel`（Vast；自建栈、boot info 校验、semihosting 早控制台、开时钟前退出） |
| m14-llvm-006 | 2026-11-14 09:10 | 符号差判据统一（移到 `evaluateFixup`）+ 放行 `.set` 绝对值符号（lit 176/176） |
| m14-llvm-005 | 2026-11-14 08:10 | 标签差立即数报错 + ABS48 wyde 写回（`ISS-424` 关闭；lit 174/174） |
| m14-llvm-002 | 2026-11-14 06:20 | DADAO SSP 后端（`STACK_CHECK_GUARD`/`CHECK_FAIL`；guard 模式 fail-closed；9/9 + E2E 66） |
| m14-qemu-001 | 2026-11-14 05:40 | Vast 最小 smon（boot info 15 字段 + 1 超页 index 4096 + PTBR=0/ptw_enable=1 + VA 入口） |
| m14-llvm-004 | 2026-11-14 04:10 | DWARF 编号（256 寄存器）+ CFI（RA=ra63/255；`.eh_frame` absptr；修 `llvm-mc` abort） |
| m14-infra-003 | 2026-11-14 03:40 | K0 收口门控 `check-linux-k0`（119 项；K1–K13；10 路注入；入 L2） |
| m14-linux-002 | 2026-11-14 03:00 | `arch/dadao` 骨架出 vmlinux（56 补丁；跨度 3.06 MiB、REL26 余量 29.04 MiB） |
| m14-llvm-003 | 2026-11-14 02:30 | `-fpatchable-function-entry`（`swym 0` 槽；N=1/2/4、M 前置；lit 166/166） |
| m14-llvm-001 | 2026-11-14 01:00 | LLVM 工具族补齐（ar/ranlib/strip + link/config/profdata/size/cov；安装根 8 工具、功能断言 104 项） |
| m14-spec-004 | 2026-11-14 00:15 | `contract-syscall` 内核入口口径（放行/自配、cause_info 推导、clone/execve 留合约+musl） |
| m14-spec-003 | 2026-11-13 22:15 | 内核 VA 窗口改 `[2TiB,3TiB)`（spec/契约/YAML/检查器/ADR-0051 同笔；旧地址仅存作废段） |
| m14-infra-002 | 2026-11-13 21:02 | initramfs（确定性 newc）+ musl init + semihosting 退出闭环（证据 79/79） |
| m14-spec-002 | 2026-11-13 21:00 | 内核侧 syscall/errno/TLS 契约（0.10.0；§1 号表逐字不变） |
| m14-infra-001 | 2026-11-13 20:40 | 工具链缺口矩阵（8 行，gaps=6 blockers=0）+ `check-linux-toolchain` 门控 |
| m14-spec-001 | 2026-11-13 19:28 | 启动 ABI 契约（`Kaiwu §6.3`；ABI 地址=VA、M1 预建页表由 smon 建、boot info 15 字段） |
| m14-linux-001 | 2026-11-13 19:10 | Linux 补丁组件化（空系列首态 + 7 个 make 目标 + 路径解析；证据 69/69） |
