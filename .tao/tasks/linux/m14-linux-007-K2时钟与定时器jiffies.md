# m14-linux-007: K2 时钟与定时器（`cfx_time` + `cfx_hart` TIMER → jiffies）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-006`（正式 trap 入口/分派骨架）、`m14-spec-005`（异步中断的内核入口口径 = `cfx_hart` `cg2 rc10`）
**可并行分片**：否（`components/linux` 单写者；且本任务是**共享 BootROM 固件**的唯一改动者）
**并行组**：与 `m14-linux-006`/`008`/`009` **必须串行**（同组件单写者；本任务还独占 `tests/shared/bootrom/k0/hmon.S`，K0/K1 门控读该文件 ⇒ 不得与任何改固件的任务并行）；`m14-spec-005` 必须先完成
**预估**：4–6 h
**档位**：大改（组件改 + 共享固件改 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：已验证

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

### 第 1 轮 engineer 自审

审查范围：本任务全部改动（固件 `hmon.S`/`README.md`；`arch/dadao` 5 个新文件 + 6 个改动；`tools/linux/k2_time_probe.py`；三个门控的配置切片；`changelog.md`/组件 `README.md`）。逐行审查 + 全门控实跑后的处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 源轴只写 `cfx_smon` 一行时只收到 1 个 tick（`escape` 只恢复运行模式，首次投递后 `inner_cfx_code` = 15） | ✅已修 | `irq.c` 同一位写 `cfx_smon` 与 `cfx_hart` 两行；固件源位 `{2}` → `{2,15}` | 注入 `only-smon-row` ⇒ rc=0x13、无 `K2 tick 2`；回绿 149/149 |
| F2 若用内核自打印的 `period` 当标尺，编程值改错时判据会自洽为绿 | ✅已修 | 探针用 `freq // hz` **派生** period 判间隔；另设 C2 断言「打印值 == 派生值」 | 注入 `period-doubled` ⇒ C4 红、还原后回绿 |
| F3 `HZ=250`（4 ms）下宿主抖动使「4× 实测偏差 ≤ period/2」不成立（实测首个 tick 偏差 0.69 ms） | ✅已修 | `defconfig` 加 `CONFIG_HZ_100`（10 ms：余量 5 ms、4× 上限 1.25 ms） | 交付实测偏差 62–85 µs，4×max = 341,376 ≤ 5,000,000 |
| F4 首读值判据写成 `first < period` 是错的（`time` 自复位起算，已走过一段启动） | ✅已修 | 改为 `0 < first < freq`（1 秒，现场派生） | C2 两镜像全绿 |
| F5 报告前未停表，理论上第 N+1 个 tick 会落进报告窗口 | ✅已修 | 等待结束即 `dadao_timer_stop()`，再打印/判定 | 149/149；停表控制（C5）仍绿 |
| F6 `cause = 0` 时 `__ffs(0)` 未定义 | ✅已修 | `dadao_async_die()` 显式 `cause ? __ffs(cause) : 0` | 编译 + 全门控绿 |
| F7 超时（hang）时 `subprocess.run` 丢掉已打印输出，注入现场为空 | ✅已修 | 探针改 `Popen` + `communicate(timeout)`，超时 kill 并保留输出 | 注入 `vector-to-smon` 现场含 `K2 time: arm`、rc=124 |
| F8 按任务书写「② 写成 `cfx_smon` 同名寄存器」会与同步向量冲突 → CFXESC 自锁（rc=124） | ❌不修（诚实观测，保留为注入 ②）＋新增注入 ⑥ | ② 断言 rc=124 + 无 tick；⑥ 用「同 cfx、错 mode 行」给出干净 `CFXMEM` 0xE1 | ② rc=124；⑥ rc=0xE1 + 具名行 |

判决：全部 finding 已处置，无未修项；状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（全部本人执行，`JOBS=32`，worktree 内相对路径）**：
- `bash <任务证据目录>/run.sh` ⇒ **rc=0，30/30 项全 PASS**：`k2_time_probe 149/149`、`--selfcheck 14/14`、`--inject 6/6`（6 路逐条「注入 md5 变 → 红 → 还原 md5 同 → 回绿」，含 `period-doubled ⇒ C4 红`、`hz-hardcoded ⇒ C2 printed hz 期望=100 实际=200`）、`check-linux-k0 **119/119**`、`check-linux-k1 **108/108**`、`k2_trap_probe 85/85`、apply-series already applied、make_patch 0 written、source-state count=1 clean、补丁树 0 problem、changelog PASS；控制台 3 条 tick、jiffies 逐次 +1、`after stop ticks=0`、`done` 各 1 次。
- **自设计注入 5 路**（`cp`+md5+重建，非其 6 路）：① `wait_ticks(N-1)` ⇒ rc=0、C3 红 4 项（3 vs 2）；② `K2_AXIS_GLOBAL_OPEN=0` ⇒ rc=19(0x13)、C1/C7 红 11 项；③ 删 `jiffies_64 += 1` ⇒ C3 jiffies 红 2 项；④ `dadao_read_time()` 返回常量 ⇒ rc=124 超时、C1 红 12 项；⑤ tick 采样写常量 ⇒ C3 单调 + C4 两断言（偏差、4×余量）全红；**5 路均还原 md5 相等、回绿 0 失败**。
- **固件 diff**：`hmon.S` 仅 2 hunk（源位 `~(1<<2)` → `~((1<<2)|(1<<15))` + `K2_TIME_PERM` 门控的 `OPEN_SUPV_REGS cfx_hart/cfx_time`）+ `README.md` 一句，三阶段未动；负例 ROM 落独立 `bootrom_noperm`，K0/K1 各自 `build_firmware` 无 defsym、切片均含 `DADAO_K2_TIME_STOP=n` ⇒ 拿到的固件与改前等价（119/119、108/108 实测）。
- **HZ/period**：内核用 `HZ`（`asm-generic/param.h` → `CONFIG_HZ`）、`period = freq / HZ` 现场派生；探针读 `.config CONFIG_HZ=100` 与打印值**断言**比对，写死注入真红（见上）。**异步入口**：`irq.c` 写 `cfx_hart` `cg2 rc10` 并回读、`async_trap.S` 读 `cfx_hart` `cg5` 帧、`escape cfx_hart,[excp_cause_ip,0]`；两轴（源轴 `cfx_smon`+`cfx_hart` 两行、全局轴 `cfx_smon` `cg8 rc1`）均开。**C4 两条均为断言**（selfcheck「+3 ms」位移单独翻「4×余量」条）。
- **未决 1 独立判断：成立** —— `spec/DADAO-12 §5.2` 步骤 5 只存 `prev_run_mode`、步骤 6 置 `inner_cfx_code`=目标，`§5.3` escape 只恢复 global mask/运行模式/IP（帧无 prev cfx）；QEMU `helper.c` 的 `cfx_enter` 置 `inner_cfx_code=target`、`do_escape` 不改，且源轴过滤读**当前 cfx** 的行 ⇒ 首投后当前 cfx=15，只开 `cfx_smon` 一行实测仅 1 tick。两行写法是必要且在「spec 字面（mode monitor 行）」读法下也无害的合理做法；替代（入口内 `trap` 切回 / 固件开 `cfx_intr_mask`）分别更险、且违 contract-syscall §8。
- **越界**：21 文件仅 `components/linux/**`+`tests/shared/bootrom/k0/**`+`tools/linux/**`+本任务书；`spec/`、`contracts/`、`.tao/contracts/`、`tests/inst/**`、`Makefile`、`components/qemu/**` 0 改动。**快照对账**：worktree `git status -uall` 干净、5 个目标文件 md5 与审查前一致、`.work/source/linux` 干净、主工作树 `master` 0 改动。
- **设计层提示（非阻断，供架构师）**：`spec/DADAO-12 §5.2` 步骤 3（源轴查 mode monitor 行）与 `ADR-0045 D3`/`contract-see §6.4`/QEMU（查当前 cfx 行）不一致；本实现两种读法下都成立，但 `m14-linux-008` 的 `local_irq_*` 口径取决于该裁定，建议另立 spec/contract 修订。
- **判决：Accepted**（验收命令块本人重跑全绿、硬约束无违反）。

## 完成区

**测试结果**：通过 30/30（运行期证据脚本，`run.sh` + `log/`）；门控真数：`check-linux-k0` 119/119、`check-linux-k1` 108/108、`k2_trap_probe` 85/85、`k2_time_probe` 149/149、`k2_time_probe --selfcheck` 14/14（9 组翻转 + 5 对照）、`--inject` 6/6、`check-patch-tree` 0 problem、`--source-state` linux count=1 clean、`check-component-changelog` PASS。失败项：无。

**修改文件**：`tests/shared/bootrom/k0/hmon.S`（`OPEN_SUPV_REGS` 源位 `{2}`→`{2,15}`、新增 `cfx_hart`/`cfx_time` 两个目标 + `K2_TIME_PERM` 负例开关）、`tests/shared/bootrom/k0/README.md`（1 句）；组件 `arch/dadao/`：新增 `kernel/time.c`、`kernel/irq.c`、`kernel/async_trap.S`、`include/asm/entry.h`、`include/asm/time.h`，改 `kernel/{setup.c,trap.S,Makefile}`、`include/asm/trap.h`、`Kconfig.debug`、`configs/defconfig`（+5 新补丁 = 68 份，`series` 同步）；`components/linux/{changelog.md,README.md}`；`tools/linux/k2_time_probe.py`（新增）、`tools/linux/{check_k0.py,check_k1.py,k2_trap_probe.py}`（配置切片各 +1 行 `DADAO_K2_TIME_STOP=n`）；本任务书。运行期证据：任务证据目录 `run.sh` + `log/`（不随仓库提交）。

**验收结果**：
1. 构建：`make_vmlinux.py`（`JOBS=32`）rc=0，`vmlinux` 5,347,408 B，`llvm-nm -u` 为空、代码跨度护栏绿（K0 门控内跑）；Vast 端到端 guest rc=0，控制台：`K2 time_init: freq=1000000000 hz=100 period=10000000 n_ticks=3 first=17344683` → `K2 irq: vec cfx_hart_supv_excp_vector=0x…415ec want=0x…415ec mode=2` → `K2 irq: mask cfx_smon_supv_cfx_intr_mask=0xffffffffffff7fff cfx_hart_supv_cfx_intr_mask=0xffffffffffff7fff cfx_smon_global_cfx_intr_mask=0xffffffffffff7fff cfxha=15 bit=0x8000` → `K2 time: arm period=10000000` → `K2 tick 1..3`（jiffies 逐次 +1）→ `K2 time: ticks=3 jiffies_delta=3` → `K2 time: after stop ticks=0` → `K2 time: done ticks=3`（各阶段 1 次、顺序由阶段表断言）。
2. 时钟口径：`freq` = 契约 `cfx_time_freq` = 1,000,000,000（契约 §3 现场解析）；`HZ` = `.config` 的 `CONFIG_HZ=100`（内核 `HZ` 宏即它，探针比对打印值）；`period = freq/HZ` = 10,000,000 counts（10 ms）现场派生；`N = 3` 写在内核 `DADAO_K2_TIME_TICKS` 并由 `time_init` 打印，探针以「输出声明值 + 下限 3」双读（不写死在门控）。余量 = `period/2` = 5,000,000 counts（半个周期，来自 period 本身），且判据要求 `4×实测最大偏差 ≤ 余量`；交付实测偏差分布：time 镜像 `[62,491, 74,754]`（mean 68,622 ns）、imask 镜像 `[69,063, 85,344]`（mean 77,203 ns），`4×max = 341,376` ≪ 5,000,000（14.6× 余裕）。
3. 探针检查 C0–C8 全 PASS（149/149，计数现场打印）：P1（freq/单调）、P2（tick 数/间隔/余量）、P3（`ctrl` 位语义 + `IMASK=1` 只挂起、释放恰好投递 1 次）、P4（关源轴、关全局轴**各一次独立运行**，各自 0 tick 且另一轴已放开）、P5（停表后 2 个周期内 0 tick）、P6（固件 `K2_TIME_PERM=0` 变体 ⇒ 首个 `cfx_time` 读即 `CFXPERM`，rc=0xE7=§7.1 supv+CFXPERM，ip == `time_init`）。
4. 可达 FAIL 注入 6 路（`cp` + md5 + 重建，逐条「红 → 还原 → 回绿」）：① `hz-hardcoded`（打印 hz 写成配置外常数 ⇒ C2 红，rc=0）；② `vector-to-smon`（异步向量写进 `cfx_smon` 同名寄存器 ⇒ 与同步向量冲突、首次投递 CFXESC 自锁，rc=124、无 tick，C1/C3 红）；③ `vector-user-row`（同 cfx 错 mode 行 ⇒ `cfx_hart` supv 向量仍 0 ⇒ 首次 tick 在 VA 0 取指 ⇒ 具名 `CFXMEM` 终止 rc=0xE1，C1/C3 红）；④ `no-mask-open`（两轴都不开 ⇒ rc=0x13、无 tick，C1/C3 红）；⑤ `period-doubled`（重挂周期 ×2 ⇒ tick 数仍 3 但间隔断言红，C4）；⑥ `only-smon-row`（只开 `cfx_smon` 一行 ⇒ 只 1 个 tick 后超时 rc=0x13，C1/C3 红）。映射任务书 ①–⑤：①→②/③，②→⑤，③→④/⑥，④→P4（case 2/3 独立运行），⑤→P6（固件变体）。
5. 固件回归：`check-linux-k0` 119/119、`check-linux-k1` 108/108（同一份 `hmon.S`，三阶段行为未改）；`k2_trap_probe` 85/85（GPR 引用宏重构后同步入口行为不变）。
6. 补丁纪律：`apply-series --component linux` 「already applied（base+1）」；`make_patch.py linux` 重导出 `0 written`（无 diff）；`check-patch-tree --source-state` linux count=1 clean；`check-patch-tree` 10 组 413 补丁 0 problem；`check-component-changelog` PASS。

**新发现/坑**：
1. **`escape` 不恢复 `inner_cfx_code`**（`spec/DADAO-12 §5.3`，帧内无 prev_cfx；QEMU 一致，`tools/testcases/arch/min_rom_probe_integ051t.py` 亦记该约定）：异步投递到 `cfx_hart` 后内核的「当前 cfx」就是 15。三处后果必须记住：① 源轴 mask 要写 `cfx_smon` **与** `cfx_hart` 两行（只一行只收 1 个 tick）；② 固件 `supv_cfxreg` 源位须同时放行 `{2,15}`，否则首投后读 `cfx_time` 即 `CFXPERM`；③ **`contract-see §6.4` 的实例表述「当前 cfx = cfx_smon」在首次异步投递后不成立** —— `m14-linux-008` 的 `local_irq_save/restore` 必须读写「当前 cfx」的 supv `rc4`（两行都写或按实际 cfx 选行），建议 spec 侧同笔修订该句。
2. **7.2.10 无 `xtime_update()`**：`do_timer()` 只在 `kernel/time/timekeeping.h`（内核内部头），其 jiffies 半边就是 `jiffies_64 += ticks`（负载均值半边要每 CPU 运行队列）⇒ K2 直接 `jiffies_64 += 1`；墙钟/`ktime_get` 仍依赖 clocksource（K4）。
3. **`HZ` 取值影响判据可达性**：`HZ=250`（4 ms）时本机首个 tick 偏差可达 0.69 ms，使「4× 实测 ≤ period/2」必红；改 `HZ=100`（10 ms）后余裕 14.6×。⇒ 余量口径必须与 HZ 一起选，别只调容差。
4. **异步向量误写到 `cfx_smon` 会与同步向量同名冲突**（同一 `cg2 rc10`）⇒ 首次投递 CFXESC 自锁、现场只剩 arm 行；想得到干净具名终止要用「同 cfx、错 mode 行」的变体（`cfx_hart cg0 rc10` ⇒ VA 0 取指 ⇒ `CFXMEM`）。
5. `k0.run_qemu` 固定带 `-d cpu`（配空 `-dfilter`）且超时会丢输出；验收要求命令行无 `-d` ⇒ 新探针自起 QEMU 并用 `Popen` 保超时现场。

**遗留问题**：① IPI 未实现（按 `contract-see §3` 只留 `dadao_async_die()` 的具名终止位置与注释）；② K4 升级点 = `time.c` 内五个函数体换 clocksource/clockevent + 补墙钟/`ktime_get` 基准，入口与 `dadao_timer_interrupt()` 调用点不动；③ `m14-linux-008` 需按 F1 的双行 IE 旋钮实现（本任务已完成两行 mask 的放行与首开）；④ `ISS-445` 未顺带（按待裁定 4，三阶段行为未改，另立任务）；⑤ 门控 `check-linux-k2`（`m14-linux-009`）尚未立册，本任务的 `k2_time_probe.py` 可直接作为其中 T 组；⑥ 余量判据在宿主负载极高时（>1.25 ms 抖动）会红，属真实告警，未放宽。

