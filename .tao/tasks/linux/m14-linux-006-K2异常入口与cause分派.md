# m14-linux-006: K2 异常入口与 cause 分派（supv 同步异常；K2 启动边界翻转）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-005`（K1 收口：`cfx_smon.supv_excp_vector` 已由内核安装、`check-linux-k1` 已入 L2）；**另需 `m14-qemu-002` 先合入**（两者都改 `tools/linux/check_k1.py`：本任务改期望码/配置切片，qemu-002 加 semihosting-PA 断言 ⇒ 同文件串行，避免冲突）
**可并行分片**：否（`components/linux` 单写者；本任务是 K2 串行链的第一环）
**并行组**：**可与 `m14-spec-005` 同时跑**（不同文件域）；与 `m14-linux-007`/`008`/`009` **必须串行**（同一组件 `components/linux` 单写者；且 007 要改的 `arch/dadao` 文件与 006 的入口/traps 相交）
**预估**：4–6 h
**档位**：大改（组件改 + 构建/门控切片；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

K1 的 trap 入口是**一次性探针**，不是异常通道：`arch/dadao/kernel/k1_trap.S` 只保存 caller-saved 两 bank（`rd4–rd31`/`rb4–rb31`），`traps.c::dadao_k1_excp_handle()` 只认「`mm/k1_pt.c` 预先声明的那一次 `CFXMEM`」并一律 `escape … , 4`（跳过），其它 cause → 打印后 `SYS_EXIT`。K2 要求它变成正式通道：**读帧 → 按 cause 分派 → 可恢复者返回、不可恢复者具名终止**。

同时 K1 用 `CONFIG_DADAO_K1_EARLY_STOP`（`init/main.c` 首句）把内核停在 `start_kernel()` 入口；`kernel/setup.c` 的注释已写明「K2 关掉该选项，`setup_arch()` 接管」。若不翻转，K2 的时钟/中断无处落地。

两处硬事实决定本任务形态（都可机械核对）：

- **上游只给现场寄存器，不给通用寄存器**（`spec/DADAO-12 §5.2` 步骤 5、`spec/DADAO-12 §3.6`）：`cg5` 只有 `excp_prev_run_mode`/`excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_pending`；入口若要用寄存器，**必须自己在第一条指令前保存**（`contract-syscall §8` 已把这条写成内核责任）。
- **`escape` 只能回到 `excp_cause_ip + {0, +4}`，且目标 cfx 恒为当前 cfx**（`spec/Machine-v5 §4.2`、`spec/DADAO-12 §5.1`/`§5.3`）；`cg5 rc3`（`excp_cause_ip`）软件可写（`spec/DADAO-12 §3.6`）⇒ 需要「回到别处」时先改 `rc3` 再 `escape …, 0`。

## 范围

1. **K2 启动边界翻转（配置切片，必须不回归 K0/K1）**
   - `arch/dadao/configs/defconfig` 去掉 `CONFIG_DADAO_K1_EARLY_STOP`（默认 n，`start_kernel()` 恢复上游语义）；
   - **保留**该 Kconfig 符号与 `init/main.c` 的钩子（K1 门控仍要用它自己的镜像）；
   - 给 `tools/linux/make_defconfig.py` 增**显式配置切片**入口（如 `--extra-config CONFIG_X=y`，可重复）：在 `make defconfig` 之后写入 `.config`，再跑一次 `olddefconfig` 收敛依赖（写进生成的 `.config` 属运行期产物，不入组件）；
   - `tools/linux/check_k0.py`、`tools/linux/check_k1.py` 的构建步骤**先**用该入口把 `CONFIG_DADAO_K1_EARLY_STOP=y` 落进 `.config`、**再**做增量构建（二者都做增量构建且共用同一个 `.config`，**不得**依赖「上一次谁配过」；`make_vmlinux.py` 本身不写 `.config`）；
   - 断言：`make check-linux-k0`、`make check-linux-k1` **仍 rc=0**（K1 的 K13「无 init/IRQ/timer 痕迹」与 K12「退出行是最后一行」必须继续成立）。
2. **正式 trap 入口汇编**（`arch/dadao/kernel/` 内；`k1_trap.S` 升级或替换为 `trap.S`，`k1_pt.c` 的探针路径改为调用新入口的记录接口，不再自带一套）
   - 第一条指令前保存**除 `rd0`/`rb0` 外的全部通用寄存器**（`rd1–rd63`、`rb1–rb63`；`rd0` 硬连零、`rb0` 是只读 `IP`，二者不入帧），按 `spec/SimRISC-01 §1` 的块传送限制分块（8 B 对齐、合法寄存器区间），`rb2`（FP）/`rb3`（`rbtp`）属被保存对象；
   - 从 `cfx_smon` `cg5 rc2/rc3/rc4` 读 `cause_id`/`cause_ip`/`cause_info`，与保存的 GPR 一起构成 `struct pt_regs`（`arch/dadao/include/asm/ptrace.h`）；`regs->ip = cause_ip`；
   - 调 C：`dadao_trap_handler(struct pt_regs *regs, unsigned long cause, unsigned long info)`；返回值为「恢复策略」，asm 侧据此执行 `escape cfx_smon, [excp_cause_ip, 0]`（重试）或 `, 4`（跳过）——**只允许这两个偏移**；
   - 入口内**不得**用 `rb0` 做临时寄存器（它是只读 `IP`）；暂存优先用 `rd2`/`rd3`（`contract-abi` 的 ABI 保留、编译器不分配），若仍不足，先把 `rb2`（FP）/`rb3`（`rbtp`）落到已保存槽位再借用；
   - **保存区选择**：K1 用静态 `.bss` 保存区（SP 可能已坏，`m14-linux-004` 的复核已认可该理由）；本任务保持「静态槽位先落」的顺序，再在**已证明可用的栈**上建立 `pt_regs`，并在注释里写明何时可改为纯栈（K4 起需要可抢占/可重入时）。
3. **C 侧 cause 分派**（`arch/dadao/kernel/traps.c`）
   - 11 项 cause 的名字表（`CFXTRAP`/`CFXMEM`/`CFXREG`/`CFXESC`/`CFXPERM`/`ILLI`/`UNDI`/`RASOF`/`RASUF`/`MALIGN`/`IALIGN`），来源 `spec/DADAO-13 §2`；**未知 cause（保留位/多位置 1）单独一路**：打印 `unknown cause=0x…` 后终止；
   - 可恢复路径：K1 的「预先声明的 `CFXMEM` 探针」保持语义（命中即记录并跳过），接口收窄为一个显式注册函数（供 `mm/k1_pt.c`/后续 K3 用），**不得**把「`cause_info` 等于某个魔数」当默认放行条件；
   - 不可恢复路径：`dadao_die()` 打印 cause 名、`ip`、`info`、`PTBR`、SP 与寄存器 dump（`show_regs()` 已有）后经 semihosting `SYS_EXIT(非零)` 终止；**不得**让同一个不可恢复异常重复进入（无限递归）；
   - 与 `contract-syscall §8` 的分工保持一致：`supv` 期同步异常入口 = `cfx_smon_supv_excp_vector`；`CFXTRAP` 从 `cfx_umon` 进来的用户 syscall 入口属 K4/K5，**本任务不实现**（但名字表与分派骨架要能容纳 `CFXTRAP`，且不得把它当未知 cause）。
4. **退出码分段合规（`spec/Machine-v5 §7.1`；用户 2026-11-15 裁定「同意A'」）**
   - **按事件性质分段**，不是"全部迁到 guest 段"：
     - **自检失败**（内核自己发现状态不对：`head.S` 的 boot info magic/version/size 校验、`setup.c`、`k1_pt.c` 的页表安装前拒绝等）⇒ **guest 段 `0x01–0x7F`**，值 = 检查点序号；
     - **异常终止**（`dadao_die()`：未知 cause、未注册/不可恢复的同步异常）⇒ **monitor 段** `0xC0 | (mode<<4) | bit索引`；supv 期即 `0xD0 | bit`（如 `CFXMEM` ⇒ `0xD1`、`ILLI` ⇒ `0xD8`、`MALIGN` ⇒ `0xDC`），位索引表取 `§7.1` 的 11 项；
     - PASS 恒 `0x00`。
   - 现状 `0xE1–0xED`（`head.S`/`setup.c`/`traps.c`/`k1_pt.c`）落在 **`0xC0–0xFF`（monitor 段）却用于自检失败** ⇒ 按 `§7.1` 会被读成「`supv` 期某同步异常」，属语义误标 ⇒ 本次一并迁移；
   - 完成区给**旧 → 新**对照表（标明每条属"自检"还是"异常终止"）；同一变更内同步 `tools/linux/k1_boot_probe.py`、`tools/linux/check_k1.py`、`tools/linux/k1_pt_probe.py` 的期望码（K1 任务书历史记录**不改**，只在完成区披露）；
   - 新增码不得与 `0x00` 冲突、不得越过 `0x7F`（guest 段）/ 不得落在 `0x80–0xCF`（其它 cfx 段留给 cfx 路由）。
5. **探针**（`tools/linux/k2_trap_probe.py`，可复用 K1 探针的 boot/镜像工具）
   - P1 可恢复：注册一次 `CFXMEM` 探针 → 入口分类正确（打印 cause 名 + `ip`/`info`）→ 跳过 → 后续标记仍在；
   - P2 重试语义：同一次 fault 用 `, 0` 重试仍会再次进入（证明偏移生效，不靠假设）；
   - P3 不可恢复：未注册的 `CFXMEM`（如访问未映射 VA）→ 具名打印 + guest 段非零退出码，且**不重复进入**；
   - P4 未知 cause：注入一个非法 `cause_id`（`cg5 rc2` 是硬件只读，见待裁定 2；允许的最小手法 = 仅在探针构建里存在的 `#ifdef` 钩子，在分派前改写传入的 cause 值）→ 走 `unknown cause` 一路；
   - P5 帧完整性：入口保存/恢复前后 GPR 逐一相等（探针在 handler 内读 `pt_regs` 与故障现场对比）。
6. **门控与文档**：`components/linux/changelog.md` 一条；本任务**不**新建 L2 目标（K2 收口门控归 `m14-linux-009`）。

## 验收（逐条贴真实 rc 与输出）

1. `python3 tools/linux/make_defconfig.py`（或 `make linux-defconfig`）+ `make build-linux JOBS=32` rc=0；生成的 `.config` 中 `CONFIG_DADAO_K1_EARLY_STOP` **未设置**；
2. Vast 端到端：`bootrom-image` + `-kernel` 启动，guest 走到 K2 边界并 `SYS_EXIT(0)`（本任务的边界 = 入口/分派/退出码链路可用；时钟由 `m14-linux-007` 接上，**本任务不得**提前引入定时器）；
3. 探针 P1–P5 全 PASS，计数现场打印；P3（未注册的 `CFXMEM` 终止）退出码 **∈ `0xD0–0xDF` 且等于 `0xD0|1`**（supv 的 `CFXMEM`），自检类失败码 **∈ `0x01–0x7F`** —— 两类逐条比对 `§7.1` 分段表；
4. **可达 FAIL 注入 ≥4 路**（`cp` + md5 还原 + 重建）：① 入口少保存一个 bank（如不保存 `rd32–rd63`）⇒ P5 红；② 把可恢复判定改成「任何 `CFXMEM` 都放行」⇒ P3 红（不再终止）；③ 把 `escape` 偏移由 `4` 改 `0` ⇒ P1 红（死循环/重复进入）；④ 把某**自检**失败码改回 `0xE1`（或把 `dadao_die()` 的码写成 guest 段 `0x01`）⇒ 分段断言红；⑤（可选）删掉 `unknown cause` 分支 ⇒ P4 红；
5. `make check-linux-k0` rc=0、`make check-linux-k1` rc=0（**K1 不回归**，含其 4 路注入自身可跑）；
6. 补丁纪律：`make apply-series` 幂等、`python3 tools/infra/make_patch.py linux` 重导出后**再跑无 diff**、`check-patch-tree` **linux 段 0 问题**、`check-patch-tree --source-state` linux **OK**、`check-component-changelog` rc=0；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`spec/`/`contracts/`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`build-linux`/构建用 `JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp` + md5。
4. 只改 `components/linux/**`（`arch/dadao` 补丁 + `changelog.md`）、`tools/linux/**`、本任务书；**不改** `spec/`、`contracts/`（若发现契约缺口，写进「待裁定」并停在该处，不自行改契约）、`tests/`、`Makefile`。
5. 只在 `qemu-system vast` 上验收；不引入 UART/cache/LLC/TLB 语义（`ADR-0052 D6`）。
6. 段首事实以 `spec/` 为唯一真源；QEMU 现状只作交叉核对，冲突 => 停下报告（不回写实现）。

## 待裁定

1. ~~**退出码迁移是否在本任务做**~~ **已裁定（用户 2026-11-15 原话「同意A'」）**：按**事件性质**分段——自检失败 ⇒ guest 段 `0x01–0x7F`；异常终止 ⇒ monitor 段 `0xD0|bit`。本任务落地，"目标 4" 已按此改写。
2. **`unknown cause` 的注入手法**：`cg5 rc2` 是硬件只读（`spec/DADAO-12 §3.6` HW），要演示未知位需要实现侧测试钩子（编译期 `#ifdef` 探针）或由 QEMU 侧注入（超范围）。建议用一个**仅在探针构建里存在**的 `#ifdef` 钩子（不入默认 defconfig）；若不允许任何测试钩子，则 P4 改为「静态断言：名字表覆盖 11 项 + 默认分支打印 `unknown`」。
3. **`pt_regs` 是否含 `status`**：现有 `struct pt_regs` 有 `status` 字段，但本机无状态寄存器（`contract-abi`），建议保留字段、写 0，并在注释里写明「无硬件来源」——若 K4 需要真值，届时另定。

## 审阅记录

（待填）
