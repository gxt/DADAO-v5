# m14-linux-007: K2 时钟与定时器（`cfx_time` + `cfx_hart` TIMER → jiffies）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-006`（正式 trap 入口/分派骨架）、`m14-spec-005`（异步中断的内核入口口径 = `cfx_hart` `cg2 rc10`）
**可并行分片**：否（`components/linux` 单写者；且本任务是**共享 BootROM 固件**的唯一改动者）
**并行组**：与 `m14-linux-006`/`008`/`009` **必须串行**（同组件单写者；本任务还独占 `tests/shared/bootrom/k0/hmon.S`，K0/K1 门控读该文件 ⇒ 不得与任何改固件的任务并行）；`m14-spec-005` 必须先完成
**预估**：4–6 h
**档位**：大改（组件改 + 共享固件改 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

K1 结束时内核刻意**没有任何时钟与中断**（`check-linux-k1` 的 K13 反断言就在守这条）。K2 要接上时间：硬件侧 `cfx_time`（`cfxha 34`）只给**读数**，定时器在 `cfx_hart`（`cfxha 15`），`TIMER` 是可屏蔽异步源（`1 << 10`，`cause_info = 0`），已由契约冻结在 `contract-see §3`。

两件**必须显式处理**的落地事实：

1. **权限不是默认有的**：内核在 `supv`/`cfx_smon` 下要 `cfx2rd/cfx2rc` 到 `cfx_hart`/`cfx_time`，需**目标 cfx** 的两轴放行——`supv_cfxreg` 的「源 cfx = 2」位清 0 + `hypv_cg_reg_deleg` 对应 cg 位为 0（`spec/DADAO-12 §3.3`、`spec/DADAO-13 §1`）。按 `contract-syscall §8`「**固件只放行、入口寄存器内核自配**」，这两步放行属固件职责：现 `tests/shared/bootrom/k0/hmon.S` 的 `OPEN_SUPV_REGS` 只开了 `cfx_pmem`/`cfx_ptw`/`cfx_smon`，`cfx_hart`/`cfx_time` **未开** ⇒ 内核写 `cfx_hart` 会得 `CFXPERM`。
2. **异步中断不进 `cfx_smon`**：按 `contract-see §3`「统一异步中断仲裁」，`TIMER` **直接投递到目标 cfx（`cfx_hart`）**，入口 = `cfx_hart` 的 `supv_excp_vector`（`cg2 rc10`，复位 0 ⇒ **内核必须自己写**，否则中断一进就落到未映射地址）、目标模式取 `cfx_hart` 的 `supv_switch_run_mode`（`cg2 rc8`，复位 `2 = supv`）；返回 = `escape cfx_hart, [excp_cause_ip, 0]`（异步 `cause_ip` = 下一条指令地址，见 `spec/DADAO-12 §5.2` 步骤 5）。**这与 `m14-linux-006` 的同步入口是两个不同的向量与帧**，不可复用同一段「读 `cfx_smon` 帧」的代码。

## 范围

1. **固件放行（共享 BootROM，唯一改动者）**
   - `tests/shared/bootrom/k0/hmon.S`：`OPEN_SUPV_REGS` 增 `cfx_hart`、`cfx_time`（来源位 = 内核的 `inner_cfx_code` = 2；`hypv_cg_reg_deleg = 0x8`），并在注释里写明「K2 起内核需要读写这两个 cfx 的定时器/时间寄存器」；
   - `tests/shared/bootrom/k0/README.md` 同步一句（hmon 的放行清单）；
   - **不改变移交态**：`rb16`/`rb17`/`rb3`、boot info 页、`PTBR`/`ptw_enable`、`smon` 的建表与 `escape` 一律不动；
   - 回归：`make check-linux-k0`、`make check-linux-k1` 仍 rc=0（K1 的镜像索引表/BootROM 断言与固件阶段断言不得变红）。
2. **内核时间读数**（`arch/dadao/kernel/time.c` 新建）
   - `dadao_time_freq()` = `cfx_time` `cg10 rc0`；`dadao_read_time()` = `cg10 rc1`（64 位、自由运行、只读）；`time_init()` 打印 `freq` 与首读值；
   - 频率/单位口径以契约为准（`contract-see §3`：1 GHz、1 count = 1 ns），**不得**从实现反推；`cfx2rd` 一次读出整个 64 位值（`spec/DADAO-12 §4.10` 的 `cfx_time_value` 为 64 位寄存器），因此不存在「高低位两次读被中断撕裂」的问题——把这条不变量写进注释；
3. **定时器编程**（同文件或 `arch/dadao/kernel/timer.c`）
   - `dadao_timer_arm(unsigned long delta_counts)`：写 `cfx_hart` `cg8 rc4` = `now + delta`，随后写 `cg8 rc5` = `ENABLE | (IMASK=0)`（bit0/bit1 语义见 `spec/DADAO-12 §4.7`）；写 `cmp` 即取消旧 deadline 并清 `ISTATUS`/`TIMER` pending（`contract-see §3`）；
   - `dadao_timer_stop()`：`cmp = ~0` 或清 `ENABLE`；
   - `dadao_timer_status()`：读 `rc5` 解出 `ENABLE`/`IMASK`/`ISTATUS`（`ISTATUS` 是只读位，读回 = `ctrl[1:0] | ISTATUS << 2`）；
   - `HZ` 取内核已 source 的 `kernel/Kconfig.hz`，周期 = `freq / HZ`（现场派生，不写死常数）。
4. **异步入口（`cfx_hart` 向量）**
   - 新 asm 入口（建议 `arch/dadao/kernel/async_trap.S`；GPR 保存/恢复的写法与 `m14-linux-006` 的入口一致，可提取宏复用），从 `cfx_hart` `cg5 rc2/rc3/rc4` 读帧 → 构成 `pt_regs` → 调 C `dadao_async_handler(regs, cause, info)` → 返回后 `escape cfx_hart, [excp_cause_ip, 0]`（**只能 `, 0`**：异步帧的 `cause_ip` 已是下一条指令）；
   - `init_IRQ()` 内**先**写 `cfx_hart` `cg2 rc10`（内核 VA 的 4 字节对齐入口）并回读校验，**再**打开 mask（顺序错误 = 中断落到未映射向量 = 不可恢复，`spec/DADAO-12 §5.2` 步骤 7）；
   - 模式取 `cg2 rc8`：启动时读回应为 `2`（`supv`）；若不是，打印后终止（不静默继续）。
5. **tick 与出口**
   - `dadao_async_handler()`：`cause == 1<<10`（`TIMER`，`info` 必须为 0，非 0 ⇒ 打印后终止）→ 计一次 tick：更新 `jiffies`（**最小路径**：单点函数 `dadao_timer_interrupt()` 内 `xtime_update(1)`（或等价的 `jiffies_64` 递增 + 时间基准）+ 重新 `dadao_timer_arm(period)`；**不**引入 `clocksource`/`clockevent` 框架，见待裁定）；
   - 其它 cause 到本入口（`IPI` = `1<<8` 等）⇒ 打印 `unexpected async cause=…` 后终止（IPI 本阶段不实现，`contract-see §3` 已写「不实现 IPI/多 hart」）；
   - 出口：tick 达到 N（如 3，写进代码注释与探针期望，不写死在门控里）后打印每 tick 的 `time` 读数与累计数，`SYS_EXIT(0)`；`dadao_timer_stop()` 后退出，避免退出路径被中断打断。
6. **探针**（`tools/linux/k2_time_probe.py`）
   - P1 `freq` == 契约值、`rc1` 单调不减；
   - P2 tick 数 == N、相邻 tick 的 `time` 差 == `freq/HZ`（允许「指令边界投递」余量，给出上界推导：`spec/DADAO-12 §5`「中断在指令边界检查」）；
   - P3 `rc5` 的 `ENABLE`/`IMASK`/`ISTATUS` 位语义（含 `IMASK=1` 时只置 pending、不投递）；
   - P4 **两轴 mask 各自有效**：分别只清 `cfx_smon` `supv rc4` 的 bit15、只清 `cfx_smon` `global`（`cg8 rc1`）的 bit15，各跑一次 ⇒ 只有两者都清才 tick（证明两轴都在起作用，不能只靠一轴）；
   - P5 关闭路径：`stop` 后不再 tick（再等若干个周期，tick 计数不变）；
   - P6 权限负例：用 hmon 的**探针变体**（`k0.build_firmware` 已支持 `hmon_defs`，加一个「不开放行」的 `--defsym`）跑同一内核 ⇒ 首次读 `cfx_time`/写 `cfx_hart` 即 `CFXPERM`（证明「放行确实来自固件」而不是默认就有）；变体只存在于运行期，不落仓库。
7. **文档**：`components/linux/changelog.md` 一条；`tests/shared/bootrom/k0/README.md` 一句。

## 验收（逐条贴真实 rc 与输出）

1. `make build-linux JOBS=32`（或等价）rc=0；Vast 端到端 guest **rc=0**，输出含 `time_init`/首 tick/末 tick/退出标记，且**顺序正确、各阶段各出现 1 次**；
2. tick 的 `time` 读数与 `freq/HZ` 的偏差在**推导出的余量**内（完成区写清余量怎么来、为什么不是写死的容差）；
3. 探针 P1–P6 全 PASS（计数现场打印）；P4 的两轴各一次为**独立运行**（不是同一次运行里的两段）；
4. **可达 FAIL 注入 ≥4 路**（`cp` + md5 还原 + 重建）：① `cfx_hart` `cg2 rc10` 写成未映射 VA ⇒ 首次 tick 即不可恢复（具名退码、非 0）；② 周期改 0（`cmp = now`）⇒ tick 计数超出/时间差断言红；③ 把 `IMASK` 置 1 后不再清 ⇒ 无 tick（`rc5` 只有 pending）；④ 只开一轴 mask（清 `rc4` 不清 `global`）⇒ P4 红；⑤ 固件少开 `cfx_time` ⇒ `time_init` 读频率即 `CFXPERM`（P1 红）；
5. `make check-linux-k0` rc=0、`make check-linux-k1` rc=0（固件改动不回归）；
6. 补丁纪律：`make apply-series` 幂等、`make_patch.py linux` 重导出后再跑无 diff、`check-patch-tree` linux 段 0 问题、`--source-state` linux OK、`check-component-changelog` rc=0；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`spec/`/`contracts/`/`Makefile`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp` + md5。
4. 只改 `components/linux/**`、`tests/shared/bootrom/k0/**`（仅 `hmon.S` 的放行清单 + `README.md` 一句）、`tools/linux/**`、本任务书；**不改** `spec/`/`contracts/`/`components/qemu/**`/`Makefile`。
5. 只在 `qemu-system vast` 上验收；不引入 UART/cache/LLC/TLB 语义、不实现 IPI/SMP（`ADR-0052 D2`/`D6`）。
6. 探针与门控**不得**用 `-d` 逐指令日志；不得以「QEMU 这么实现」为期望值来源（`AGENTS.md`「Independent oracle」）。
7. **体积/链接约束**：K0 门控要求 `llvm-nm -u vmlinux` 为空、`make_vmlinux.py`/`check-code-range` 的代码跨度护栏成立；引入 `xtime_update`/`jiffies` 若拉入未定义符号或让护栏变红，**改产物不改判据**（不放宽护栏、不引入外部库），并在完成区贴「改前/改后跨度与余量」。
8. 若发现 QEMU 侧缺实现（`cfx_hart` supv 向量写、TIMER 投递、`escape` 恢复+重踢）⇒ **保留现场、停下报告**（不得改 QEMU，QEMU 属另一组件，另立任务）。

## 待裁定

1. **时间框架：最小路径 vs `clocksource`/`clockevent`**：建议**最小路径**（`dadao_timer_interrupt()` 单点 + `xtime_update`），因为 K2 的出口判据只到「时钟中断 → jiffies 前进」；K4（进程/上下文）需要 `clockevent` 时再升级。代价是 K4 有一处改造点 ⇒ 本任务须把「编程/确认/读数」收敛到 `arch/dadao/kernel/time.c` 的三个函数里，K4 只换实现不动入口。
2. **tick 数 N 与余量口径**：N（如 3）与「时间差余量」是**实现选择 + 判据形状**，需用户确认？建议：N 写进代码/探针、门控从输出的 tick 计数现场派生期望、余量按「一个 tick 周期的 1/2 且不小于交付时实测最大偏差的 4 倍」写死上限并在完成区贴实测分布。
3. **`HZ` 取值**：建议 `100`（10 ms 周期；`freq/HZ` = `10_000_000` counts）。若上游 `kernel/Kconfig.hz` 默认不同，以现场派生为准、不写死。
4. **ISS-445（K1 阶段顺序间接证据）是否顺带了结**：本任务会改 `hmon.S`，顺手加三阶段 semihosting 标记可一并关闭该 issue；但会新增 K1 输出行、动 K1 门控的「一次性行」断言 ⇒ 建议**不**顺带（另立任务），本任务只在 3 阶段行为不变的前提下改放行清单。

## 审阅记录

（待填）
