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
| m14-spec-007 | 2–3 h | `cause_id` 子原因编码落地（`DADAO-12 §3.6/§4.x/§2.2.6` + `contract-see §6.1` 扩列 + 锁重算） |
| m14-spec-006 | 3–4 h | K3 的 TLB 规范与契约（撤 `Kaiwu` 不定义句、新建 `contract-tlb`、8 条探针门控设计；只定义不实现） |
| m14-qemu-003 | 1.5–2 h | 异步源轴 mask 改按「当前运行模式 monitor」（`ISS-455`；QEMU 侧） |
| m14-qemu-004 | 1 h | `SYS_READC`/`SYS_FLEN` 取字缓冲改 PA（`ISS-452`，用户裁定「现在修」） |
| m14-linux-010 | 2–3 h | IE 旋钮收敛为 monitor 单行 + `contract-see §6.4` 口径修订（`ISS-455`/`ISS-454`） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m14-linux-009 | 2026-11-16 13:21 | 4–5 h | K2 收口门控 `check-linux-k2`（4 条口径 + 复用顺序/退出码断言；入 L2） |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
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
