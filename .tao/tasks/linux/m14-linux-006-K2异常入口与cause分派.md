# m14-linux-006: K2 异常入口与 cause 分派（supv 同步异常；K2 启动边界翻转）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-005`（K1 收口：`cfx_smon.supv_excp_vector` 已由内核安装、`check-linux-k1` 已入 L2）；**另需 `m14-qemu-002` 先合入**（两者都改 `tools/linux/check_k1.py`：本任务改期望码/配置切片，qemu-002 加 semihosting-PA 断言 ⇒ 同文件串行，避免冲突）
**可并行分片**：否（`components/linux` 单写者；本任务是 K2 串行链的第一环）
**并行组**：**可与 `m14-spec-005` 同时跑**（不同文件域）；与 `m14-linux-007`/`008`/`009` **必须串行**（同一组件 `components/linux` 单写者；且 007 要改的 `arch/dadao` 文件与 006 的入口/traps 相交）
**预估**：4–6 h
**档位**：大改（组件改 + 构建/门控切片；复核须独立重跑 + ≥4 路注入）
**状态**：已验证

## 背景

K1 的 trap 入口是**一次性探针**，不是异常通道：`arch/dadao/kernel/k1_trap.S` 只保存 caller-saved 两 bank（`rd4–rd31`/`rb4–rb31`），`traps.c::dadao_k1_excp_handle()` 只认「`mm/k1_pt.c` 预先声明的那一次 `CFXMEM`」并一律 `escape … , 4`（跳过），其它 cause → 打印后 `SYS_EXIT`。K2 要求它变成正式通道：**读帧 → 按 cause 分派 → 可恢复者返回、不可恢复者具名终止**。

同时 K1 用 `CONFIG_DADAO_K1_EARLY_STOP`（`init/main.c` 首句）把内核停在 `start_kernel()` 入口；`kernel/setup.c` 的注释已写明「K2 关掉该选项，`setup_arch()` 接管」。若不翻转，K2 的时钟/中断无处落地。

两处硬事实决定本任务形态（都可机械核对）：

- **上游只给现场寄存器，不给通用寄存器**（`spec/DADAO-12 §5.2` 步骤 5、`spec/DADAO-12 §3.6`）：`cg5` 只有 `excp_prev_run_mode`/`excp_cause_id`/`excp_cause_ip`/`excp_cause_info`/`excp_pending`；入口若要用寄存器，**必须自己在第一条指令前保存**（`contract-syscall §8` 已把这条写成内核责任）。
- **`escape` 只能回到 `excp_cause_ip + {0, +4}`，且目标 cfx 恒为当前 cfx**（`spec/Kaiwu §4.2`、`spec/DADAO-12 §5.1`/`§5.3`）；`cg5 rc3`（`excp_cause_ip`）软件可写（`spec/DADAO-12 §3.6`）⇒ 需要「回到别处」时先改 `rc3` 再 `escape …, 0`。

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
4. **退出码分段合规（`spec/Kaiwu §7.1`；用户 2026-11-15 裁定「同意A'」）**
   - **按事件性质分段**，不是"全部迁到 guest 段"：
     - **自检失败**（内核自己发现状态不对：`head.S` 的 boot info magic/version/size 校验、`setup.c`、`k1_pt.c` 的页表安装前拒绝等）⇒ **guest 段 `0x01–0x7F`**，值 = 检查点序号；
     - **异常终止**（`dadao_die()`：未知 cause、未注册/不可恢复的同步异常）⇒ **monitor 段** `0xC0 | (mode<<4) | bit索引`；supv 期按 `§7.1` 的模式编码（`user=00`/`jail=01`/**`supv=10`**/`hypv=11`）即 **`0xE0 | bit`**（如 `CFXMEM` ⇒ `0xE1`、`ILLI` ⇒ `0xE8`、`MALIGN` ⇒ `0xEC`），位索引表取 `§7.1` 的 11 项；`0xD0–0xDF` 是 **jail** 段，不得用于 supv（**本条示例值于 2026-11-16 订正：`m14-linux-006` 实现时发现任务书原写 `0xD0|bit` 与 §7.1 模式编码冲突，按 spec 修正**）；
     - PASS 恒 `0x00`。
   - 现状 `0xE1–0xED`（`head.S`/`setup.c`/`traps.c`/`k1_pt.c`）落在 **`0xC0–0xFF`（monitor 段）却用于自检失败** ⇒ 按 `§7.1` 会被读成「`supv` 期某同步异常」，属语义误标 ⇒ 本次一并迁移；
   - 完成区给**旧 → 新**对照表（标明每条属"自检"还是"异常终止"）；同一变更内同步 `tools/linux/k1_boot_probe.py`、`tools/linux/check_k1.py`、`tools/linux/k1_pt_probe.py` 的期望码（K1 任务书历史记录**不改**，只在完成区披露）；
   - 新增码不得与 `0x00` 冲突、不得越过 `0x7F`（guest 段）/ 不得落在 `0x80–0xCF`（其它 cfx 段留给 cfx 路由）。
   - **表外 cause（复核阻断 1，2026-11-16 主会话裁定）**：`unknown cause` 属**异常终止**，必须走 `dadao_die()`（不得再用 `dadao_selfcheck(0x0f,…)` 落 guest 段——那会与"失败点序号"不可区分）；位索引取 `__ffs(cause) & 0xF`（机械派生，无新约定），控制台仍必须打印**原始** `cause=0x…`；`0x0f` 这个 guest 码从实现与门控期望里删除。
   - **`CFXTRAP`/`CFXESC` 的段（复核阻断 2，2026-11-16 裁定）**：按 `§7.1`「其它 cfx 段」编码 `0x80 | cfxHA`；K2 期内核运行在 `cfx_smon`（cfxHA=2）⇒ **`0x82`**；K4 起（用户态 cfx）需从路径取 cfxHA，本任务只在注释里预留。
   - **断言可达性（复核非阻断 3）**：`regs->ip`（即 `cg5 rc3` 写入）与**重入保护**各须有**可达 FAIL 的断言**（当前注入⑤⑥全绿 ⇒ 等于没有断言）：重入判据须把 `recursive…` 行纳入计数，`ip` 判据须能证明"写 rc3 后 `escape …0` 真的回到新 ip"。
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
3. 探针 P1–P5 全 PASS，计数现场打印；P3（未注册的 `CFXMEM` 终止）退出码 **∈ `0xE0–0xEF` 且等于 `0xE0|1` = `0xE1`**（supv 的 `CFXMEM`，模式位从 `excp_prev_run_mode` 现场读取），自检类失败码 **∈ `0x01–0x7F`** —— 两类逐条比对 `§7.1` 分段表；
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

1. ~~**退出码迁移是否在本任务做**~~ **已裁定（用户 2026-11-15 原话「同意A'」）**：按**事件性质**分段——自检失败 ⇒ guest 段 `0x01–0x7F`；异常终止 ⇒ monitor 段 `0xC0|(mode<<4)|bit`（supv ⇒ `0xE0|bit`）。本任务落地，"目标 4" 已按此改写（示例值 2026-11-16 按 §7.1 订正）。
2. **`unknown cause` 的注入手法**：`cg5 rc2` 是硬件只读（`spec/DADAO-12 §3.6` HW），要演示未知位需要实现侧测试钩子（编译期 `#ifdef` 探针）或由 QEMU 侧注入（超范围）。建议用一个**仅在探针构建里存在**的 `#ifdef` 钩子（不入默认 defconfig）；若不允许任何测试钩子，则 P4 改为「静态断言：名字表覆盖 11 项 + 默认分支打印 `unknown`」。
3. **`pt_regs` 是否含 `status`**：现有 `struct pt_regs` 有 `status` 字段，但本机无状态寄存器（`contract-abi`），建议保留字段、写 0，并在注释里写明「无硬件来源」——若 K4 需要真值，届时另定。**本任务按建议执行**（`ptrace.h` 注释 + `trap.S` 写 0）。
4. **【需裁定·口径冲突】supv 的 monitor 段编码**：裁定 1 与验收 3 的示例写「supv ⇒ `0xD0|bit`」（`CFXMEM`=`0xD1`），但裁定 1 同段的公式 `0xC0 | mode<<4 | bit` 与 `spec/Kaiwu §7.1` 的运行模式编码（`user`=00/**`jail`=01**/**`supv`=10**/`hypv`=11）一致给出 **`0xE0|bit`**（`CFXMEM`=`0xE1`）；`0xD0` 在 §7.1 里是 **jail**。本实现按「spec 为唯一真源 + 同一公式」取 `0xE1`，并把模式位从帧 `cfx_smon.excp_prev_run_mode` 现场读出（不写死）；k2 门控的期望值也从 §7.1 现场解析（`spec_exit_segments()`），不写死。**若确认要用 `0xD0`：改 `arch/dadao/kernel/traps.c::DADAO_EXIT_MONITOR` 一处即可（门控会随之按 §7.1 解析出 0xE1 而变红 ⇒ 须同时改 §7.1 或改门控的解析口径）**。倾向：保持 `0xE0|bit`（spec 一致），并把裁定文本的示例订正。
5. **表外 cause 的退出码**：monitor 段 `bit3:0` 只有 11 个合法位索引，表外原因（保留位/多位）无法编成 monitor 码 ⇒ 本实现按「内核自检失败」落 guest 段 `0x0f`（P4 断言即此）。若要求表外原因也归 monitor 段，需要新位索引（§7.1「新增原因不得改变既有索引」，需另立编号）。
6. **K2 边界位置**：落在 `setup_arch()` 末尾（`CONFIG_DADAO_K2_EARLY_STOP`），不是 `trap_init()`。理由：`trap_init()` 之前要有 `setup_per_cpu_areas()`/`parse_early_param()`/`setup_log_buf()` 等中间件可用，超出 K2（trap 入口 + cause 分派）范围；K3 接时钟时再前移。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查对象：`components/linux/patches/**` 下的 `trap.S`/`traps.c`/`k2_selftest.c`/`setup.c`/`head.S`/`k1_pt.c`/`ptrace.h`/`trap.h`、`tools/linux/*.py`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 入口帧错位一格：`stm.o {rd1:rd63}, [rb3, rd0]` 把 rd1 落到 `frame.rd[0]`（块传送首格是 offset 0），全帧整体偏移 ⇒ `rb[i]/ip` 全错 | ✅已修 | 改为 rd1/rd2/rd3 单条 `st.o` + `set.rd rd2, slot` 起块存 `{rd4:rd63}`；恢复侧对称（`ld.o rd1`、`ldm.o {rd4:rd63}`、`ld.o rd2/rd3`、最后 `ld.o rb3,[rb3,slot]` 自址） | P5 `gpr_cmp=126 marked=12 mismatches=0`（修前 `mismatches=12`，`rd2 have=0x3a3a want=0x2a2a` 正是错位实证）；注入①少存 bank 仍能红（`mismatches=4`） |
| F2 第三个数据参数错位：`dadao_trap_handler(regs, cause, info)` 的 `info` 应在 `rd17`，原实现把 `cause_info` 放 `rd18` ⇒ 探针匹配恒失败 | ✅已修 | `trap.S`：先 `rc3→rd17` 存 `frame.ip`，再 `rc4→rd17` 作第二数据参数 | 首轮 `cause=CFXMEM ... info=0x20000112ccc`（=ip，错）；修后 `info=0x20020000000`、K1 探针行与 K1 门控 108/108 |
| F3 `dadao_cause_index()` 多减 1（`__ffs` 已是 0 基）⇒ die 码恒 `0xE0` | ✅已修 | 去掉 `- 1` 并加注释 | P3 退出码 `0xE1`；注入④/②的分段断言均按 §7.1 现场解析 |
| F4 `current` 恒 NULL（SP 在 head.S 静态 early stack，栈底无 `thread_info`）⇒ `pr_notice()` 在 `vprintk_store` 取 `pid` 即 CFXMEM | ✅已修 | `head.S` 新增 `dadao_jump_on_stack()`，`dadao_start_kernel()` 结尾切到 init task 栈（`init_stack+THREAD_SIZE`，其栈底即 `init_thread_info`） | plain 镜像过 `setup_arch()` 到 K2 边界；`k1_boot_probe` P6 改为断言 SP 在 init 栈内（30/30） |
| F5 `bool default y` 与新默认镜像冲突：defconfig 删行仍会默认 y ⇒ K1 边界关不掉 | ✅已修 | `Kconfig.debug` 的 K1/K2 三个符号全改 `default n`，defconfig 显式开 `DADAO_K2_EARLY_STOP` | `make_defconfig` 后 `.config` 无 `CONFIG_DADAO_K1_EARLY_STOP=`；K2 边界到达 |
| F6 配置切片 `=n` 校验过严（依赖不满足时 Kconfig 不写该符号） | ✅已修 | `apply_config_lines()` 的 `=n` 断言按「无 `SYM=` 行」判定 | K0/K1 门控切片后仍 119/119、108/108 |
| F7 K1 探针无命中上限 ⇒ 注入③（偏移 4→0）变成 120 s 超时、无证据 | ✅已修 | `k1_pt.c` 探针 `max_hits = 2`（两次 peek 一次预期缺页）；`traps.c` 超限按自检点 `0x10` 具名终止 | 注入③ `rc=0x10` 且 `dadao: fault probe hit too often cause=CFXMEM` |
| F8 K1 工具（`k1_boot_probe`/`k1_pt_probe`）在默认镜像已变 K2 后会对着错的边界报 K1 失败 | ✅已修 | 两者启动即校验 `.config` 有 `K1_EARLY_STOP=y`，否则显式退出；`k1_pt_probe.rebuild()` 前先落 K1 切片 | K1 门控后 `k1_boot_probe` 30/30 + 负例 5/5×2、`k1_pt_probe` 58/58 + `--inject` 4/4 |
| F9 `check_k1 --inject` 的 `exit-code` 注入点因新增 K2 边界同款调用而不再唯一 | ✅已修 | 注入文本扩到「K1 done 打印行 + `dadao_early_exit(0)`」 | `check_k1 --inject` 4/4、`rc=0` |
| F10 静态帧被同 cfx 递归覆盖：递归/重入时 dump 显示的是**第二帧** | ⏸延后 | `traps.c` 在重入注释里写明「静态帧会被覆盖」，递归仍具名终止（`0x0e`） | 属 K4（可抢占/重入）范围，K2 单 hart 顺序执行下不触发 |
| F11 `pt_regs` 去掉 `ra[8]`（GPR 帧不含 RA bank） | ✅不修（有意） | 保存集合 = 任务书规定的 `rd1-rd63`/`rb1-rb63`；`ra` 由 `call`/`ret` 管理，非 GPR | 全仓无 `regs->ra[` 引用；`asm-offsets`/`copy_thread` 一致 |

判决：F1–F9 已修并复验，F10 有理由延后，F11 为有意设计 ⇒ 满足「所有 finding 已修或已说明」→ 状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（全部本人执行，`JOBS=32`）**：`run.sh` → `check-linux-k0 119/119 rc=0`、`check-linux-k1 108/108 rc=0`、`k2_trap_probe 53/53 rc=0`、`--selfcheck 10/10`、`run.sh --inject 4/4 rc=0`（`cp`+md5 还原后回绿 53/53）；P1 `hits=1 resumed=yes marker=0x5031`、P2 `hits=2 same_ip=yes`、P5 `frames=2 gpr_cmp=126 marked=12 mismatches=0`、P3 `rc=225=0xE1`（`die mode=2 code=0xe1`）、P4 `rc=15=0x0f`；`apply_series --component linux` ×2 = `base+1 跳过 rc=0`、`make_patch linux` = `0 written, 63 unchanged`、`git status` 空、`check-component-changelog rc=0`、`check-patch-tree` linux `63 patch(es)/0 assertion`、`--source-state linux OK`。（首轮 `--source-state`/`check-patch-tree` rc=1 只因 chipyard 并发脏树，复跑仍仅 chipyard 红、linux 0。）
**自设计注入 6 路**（`cp`+md5，逐路还原回绿 53/53；23 个改动文件 md5 与注入前快照逐个相同）：① traps.c 名表 `CFXMEM↔CFXPERM` 对调 → 50/53 红（C3/C5/C8）；② head.S `FAIL_MAGIC 0x01→0x81` → 52/53 红（C1）；③ trap.S `.Lresume_skip` 偏移 `4→0` → 20/48 红（C2/C5–C8，plain `rc=16=0x10`）；④ traps.c 模式位写死 `1` → 52/53 红（C8 期望 225 实际 209=`0xD1`，证「mode 必须从帧读」）；⑤ 删 trap.S `cg5 rc3→frame.ip` 两行 → **53/53 仍绿**；⑥ `if (dadao_trap_busy)` 改 `0&&` → **53/53 仍绿**。另复验完成区注入①类（删 `stm.o {rd4:rd63}` → `mismatches=8`、C7 红）与②类（放宽 probe 匹配 → 23/48 红）。
**入口/分段/切片核验**：`escape` 全仓仅 `trap.S` 宏两实例（`0`/`4`）；`rb0` 只出现在 `br/jump [rb0,label]` PC 相对编码、不作暂存；覆写 `rd2/rd3/rb3` 前先落 `cfx_smon` cg6 scratch / `rd2`（P5 marks 含 rd2/rd3、`mismatches=0` 佐证）；11 项名表与 `§7.1` 位索引逐项一致（门控现场解析 spec）；自检码 `0x01–0x10` 全在 guest 段；`defconfig` 无 `CONFIG_DADAO_K1_EARLY_STOP`，`check_k0`/`check_k1` 构建前各自 `apply_config_lines()`（不靠上次谁配过）。
**越界 0**：diff 仅 `components/linux/**` + `tools/linux/**` + 本任务书；`spec/`、`contracts/`、`.tao/contracts/`、`tests/`、`Makefile`、台账、`discussing.md` 未动；`git status -uall` 干净、md5 快照对账一致（本条记录为 reviewer 本轮唯一新增改动）。
**判决：Needs Revision**（1 条阻断 + 1 条架构师定夺 + 2 条非阻断发现）
1. **阻断·目标 4 未满足**：表外 cause 走 `dadao_selfcheck(0x0f,…)` 落 guest 段，实测 P4 `rc=15`，门控 C9 与 `run.sh` 把 `0x0f` 固化为期望 ⇒ 按 A'「异常终止 ⇒ monitor 段」本应分段可辨的事件，在 `$?` 上与自检失败不可区分（guest 段语义 = 失败点序号）。改法二选一、需裁定：(a) 表外 cause 改走 `dadao_die()`，`bit3:0 = __ffs(cause)&0xf`（`1<<5` ⇒ supv `0xE5`），C9 改判 monitor 段；(b) 架构师/用户把「表外 cause 落 guest `0x0f`」补进目标 4 并给新位索引口径，再复核。
2. **阻断·供架构师定夺（K2 不可达）**：`dadao_die()` 对 `CFXTRAP`/`CFXESC` 仍编 monitor 段，`spec/Kaiwu §7.1` 明确这两项按「其它 cfx」段 `0x80|cfxHA`；帧内无 prev_cfx ⇒「对应 cfx 的 cfxHA」现场不可推，需口径。
3. **非阻断**：(i) `regs->ip` 捕获与重入保护无可达 FAIL 断言（注入⑤⑥全绿）；C8「不重复进入」只数 `^dadao: un\w+` 行，重入行 `recursive…` 不匹配（rc 断言仍会因 `0x0e` 兜住）；(ii) `kernel_selfcheck_codes()` 不扫 `traps.c` 的 `0x0e/0x0f/0x10` 字面量，C1 静态分段只覆盖 4 个文件的 `#define`。
采信项：无——重跑项全部本人执行；完成区 119/108/53/10/4/63 与本人输出逐一相符。

### 第 2 轮 engineer 返工（按 2026-11-16 裁定 / 目标 4 新增三段）

审查意见来源：第 1 轮 reviewer（Needs Revision：1 阻断 + 1 待定夺 + 2 非阻断）+ 主会话在任务书「目标 4」补写的三条裁定。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（阻断）表外 cause 落 guest 段 `0x0f`，在 `$?` 上与自检失败不可区分 | ✅已修 | `traps.c`：未知 cause 改走 `dadao_die()`（异常终止），位索引 `__ffs(cause)&0xF` 机械派生；`0x0f` 从实现、门控期望、`run.sh` 全部删除；P4 注入钩子改 `cause = 1UL<<5`（单一保留位）；C9 改判「∈ monitor 段」且「== `0xC0|supv<<4|(__ffs(cause)&0xF)`」，并额外断言「不落 guest 段」 | unknown 镜像 rc=`229`=`0xE5`（cause 现场读为 `0x20`）；控制台仍有 `cause=unknown(0x20)` + `unknown cause=0x20 (not in the 11-item table)`；C9 三断言绿 |
| R2（阻断）`CFXTRAP`/`CFXESC` 仍编 monitor 段 | ✅已修 | 新增 `dadao_exit_code(cause)`：这两项走「其它 cfx」段 `0x80|cfxHA`（cfxHA 由 `cfx_smon cg4 rc0` **现场读** = 2），其余仍 `0xC0|(mode<<4)|index`；`dadao_die()` 与自检共用该函数；注释写明「K4 起用户态 cfx 需从异常路径取 cfxHA」 | P7 `exit-code trap=0x82 esc=0x82 cfxmem=0xe1 illi=0xe8`；cftrap 镜像 rc=`130`=`0x82` 且具名 `cause=CFXTRAP(0x1)`；cfxesc 镜像 rc=`130` 且 `cause=CFXESC(0x8)`；C11/C14 绿 |
| R3（非阻断 3）`regs->ip`（cg5 rc3）与重入保护无可达 FAIL 断言 | ✅已修 | ① 探针加 `redirect`：handler 先写 `cg5 rc3` 再返 RETRY，P8 的落点是一个函数（`&&label` 在本 target 不支持，与 `__builtin_return_address()` 折 0 同源）；② P9 把二次故障放进 report 回调（真在 handler 内），`fatal_lines()` 把 `recursive…` 行纳入计数 | P8 `landed=yes marker=0x600d`；注入⑤（删 rc3 写）⇒ `landed=yes` 消失、rc=`0x0f`、C12 红；注入⑥（去 busy 判断）⇒ `recursive` 行消失、rc=`0x0f`、C13 红；两条均还原回绿 85/85 |
| R4（非阻断 4）静态分段扫描不覆盖 `traps.c` 字面量 | ✅已修 | `kernel_selfcheck_codes()` 扩扫 `traps.c`；`traps.c` 的裸字面量 `0x10` 改为 `K2_FAIL_HIT_BUDGET` 宏（`0x0e`/`0x0f` 一并具名）；C1 增加「扫描覆盖 traps.c」断言 | 现场扫到 15 个自检码（含 `K2_FAIL_RECURSIVE=0x0e`、`K2_FAIL_HIT_BUDGET=0x0f`），全部 ∈ `0x01–0x7f` |

判决：R1–R4 全部修完并逐条复验（新增 3 组断言 C10/P6、C11/P7、C12/P8 与 C13 重入、C14 其它 cfx 段；门控 53→**85** 项，`--selfcheck` 10→**16** 组，`--inject` 4→**6** 路）⇒ 状态置 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-16）

**重跑（全部本人执行，`JOBS=32`）**：`run.sh` **12/12 PASS、`RUN_RC=0`** → `check-linux-k0 **119/119** rc=0`、`check-linux-k1 **108/108** rc=0`、`k2_trap_probe **85/85** rc=0`、`--selfcheck **16/16**`、`run.sh --inject 4/4 rc=0`（还原 md5 `9de1d0e3` 一致、回绿 85/85）；六镜像 rc：plain `0`、probe `225=0xE1`、unknown `229=0xE5`、reentry `14=0x0e`、cftrap/cfxesc `130=0x82`；控制台 `unrecoverable … cause=unknown(0x20)`+`unknown cause=0x20`+`die mode=2 code=0xe5`、`recursive supv exception … code=0xe`、`P7 exit-code trap=0x82 esc=0x82 cfxmem=0xe1 illi=0xe8`、`P8 landed=yes marker=0x600d`。**`k2_trap_probe --inject` 本人重跑 = `PASS (6/6 路注入按预期变红并还原)`、`RC=0`、42 PASS/0 FAIL**，与完成区一致。
**R1（异常终止不再落 guest）**：全仓退出点逐个核 —— `dadao_die()`→`dadao_exit_code()` 只产 `0x80|cfxHA` 或 `0xC0|(mode<<4)|idx`；guest 段只剩自检（`FAIL_*` 0x01–0x0c、`0x0d` bad policy、`K2_FAIL_RECURSIVE 0x0e`、`K2_FAIL_HIT_BUDGET 0x0f`、自检镜像 `0x7f`）；C9/C14 各带反向断言（不落 guest / 不落 monitor）。**唯一边界项**：重入判为自检 `0x0e`（任务书未规定其段；与 P3 的 `0xE1` 可区分）⇒ 记为判断说明，非阻断。✅
**R2**：cfxHA 是 `DADAO_CFX_READ(cfx_smon, CFX_CG_ID=4, CFX_RC_ID=0)` **现场读**（QEMU `cpu.c:320 r->cfx_id = cfxha`，实测 2）；位域手算 `0x80|(2&0x3f)=0b1000_0010`：bit7=1、bit6=0、bit5:0=2 ✅ 吻合 §7.1；注入 `CFX_RC_ID 0→1`（version=`0x10000`）⇒ C11/C14 期望 `0x82` 实际 `0x80` **红**，证明是活读、非写死 2。✅ **遗留**：spec 只写 `cfx_id`=「核芯功能扩展标识符」、未钉死 `== cfxHA`（QEMU 等式 + 实测支撑）→ 建议登记待裁定（非阻断）。
**R3（可达 FAIL）**：注入⑤删 `cg5 rc3` 写 ⇒ C12 `landed=?` 红；注入⑥`if(dadao_trap_busy)`→`0&&` ⇒ C13 `recursive` 缺失 + rc `14→15` 红；**自设计**：把 P9 二次故障挪出 handler（`k2_nested_fault` 不再解引用）⇒ C13 **四条全红**（`recursive` 缺、rc=127、终止行 0、`P9 FAIL` 行出现），证明判据挂在重入证据上、不依赖别的东西；`__ffs`→`cause&0xf` ⇒ C9 `0xe5→0xe0` 红。✅
**R4**：`kernel_selfcheck_codes()` 已含 `traps.c`（`FAIL|DADAO_TRAP_BAD_POLICY|K2_FAIL`，5 文件、15 个码）；注入 `K2_FAIL_HIT_BUDGET 0x0f→0xE1` ⇒ C1 `traps.c:K2_FAIL_HIT_BUDGET=225` **红**（84/85）。✅
**补丁纪律 / 越界**：`apply_series --component linux`×2 = `base+1 跳过 rc=0`；`make_patch linux` = `0 written,63 unchanged`；`check-patch-tree` **linux 0 problem**（63 patch；**8 条全属 chipyard 断言⑥/⑨**，本任务 diff 无 chipyard 文件 ⇒ 归 chipyard 侧，与「已合入」预期不符，报架构师）；`--source-state` 全绿含 `linux: OK`、rc=0；`check-component-changelog PASS`；`git status -uall` 空、22 文件 md5 快照一致；**越界 0**（仅 `components/linux/**`+`tools/linux/**`+本任务书）；K0/K1 各自 `apply_config_lines()` 且日志见 `config slice applied`（不靠上次）。**（第 1 次重试：上轮漏写本段，本轮补齐）**

**判决：Accepted** —— R1–R4 逐条以本人重跑/注入证实，门控真数 119/108/85/16/6 全对齐；未决 3 条非阻断：① `cfx_id==cfxHA` 未在 spec 钉死（建议待裁定）；② 重入 `0x0e` 归自检属判断说明；③ chipyard 8 条 assertion 归 chipyard/architect。

## 完成区

**测试结果**：`check-linux-k0` **119/119**、`check-linux-k1` **108/108**（其 `--inject` 4/4、`k1_boot_probe` 30/30 + 负例 5/5×2、`k1_pt_probe` 58/58 + `--inject` 4/4）；`k2_trap_probe` **85/85**（现场统计）、`--selfcheck` **16/16 组可翻转**、`--inject` **6/6 路**（重建 + `cp`/md5 还原 + 回绿）；运行期证据脚本 12/12 与 `--inject` 反例 4/4。L1 `make -k check`：`check-patch-tree`（8 条 chipyard）、`check-run-artifacts`（224 条全部 `.work/log/chipyard/**`）、`check-temp-dirs`（`/tmp/opencode/m14-linux-005` 2.6 h、`/tmp/opencode/check-install-tools` 2.3 h）三项红，均属**他任务**残留（本任务 0 条），其余全绿。

**修改文件**：
- 组件补丁（`components/linux/patches/**` + `series` + `changelog.md`，一文件一补丁）：改 `arch/dadao/{Kconfig.debug,configs/defconfig,include/asm/{ptrace,ptw,setup}.h,kernel/{Makefile,asm-offsets.c,head.S,setup.c,traps.c},mm/k1_pt.c}`；新增 `arch/dadao/include/asm/trap.h`、`arch/dadao/kernel/trap.S`、`arch/dadao/kernel/k2_selftest.c`；删除 `arch/dadao/kernel/k1_trap.S`。
- 工具：改 `tools/linux/{make_defconfig,check_k0,check_k1,k1_boot_probe,k1_pt_probe}.py`；新增 `tools/linux/k2_trap_probe.py`。

**验收结果**：
1. 配置切片：默认 `make_defconfig` 后无 `CONFIG_DADAO_K1_EARLY_STOP`、`CONFIG_DADAO_K2_EARLY_STOP=y`；K0/K1 各自构建前落自己的切片 ⇒ 119/119、108/108 不回归。
2. Vast 端到端（plain）：`SYS_EXIT(0)` 且为最后一行；阶段 bootinfo→stack→vector→table→install→switch→table-done→setup_arch→causes→channel→boundary 各 1 次、行号递增；边界前无 clock/timer/IRQ 痕迹；**未引入定时器**。
3. 探针（计数现场打印）：P1 `hits=1 resumed=yes marker=0x5031`；P2 `hits=2 same_ip=yes`；P5 `frames=2 gpr_cmp=126 marked=12 mismatches=0`；**P6** `cause=CFXTRAP hits=1 resumed=yes marker=0x5036`；**P7** `exit-code trap=0x82 esc=0x82 cfxmem=0xe1 illi=0xe8`；**P8** `landed=yes marker=0x600d`（写 `cg5 rc3` 后 `escape …,0` 落到新 ip）；P3 rc `0xE1`；P4 rc `0xE5`（`0xE0|(__ffs(0x20)&0xF)`，控制台保留原始 `cause=0x20`）；reentry rc `0x0e`（`recursive supv exception`，终止行 1 条）；cftrap/cfxesc rc `0x82`。
4. 注入 6 路（`cp`+md5 还原 + 重建回绿）：①少存一个 bank ⇒ P5 `mismatches`>0、C7 红；②任何 `CFXMEM` 放行 ⇒ P3 续跑、C8 红；③`escape` 偏移 4→0 ⇒ 命中预算耗尽（`hit too often`、rc `0x0f`）、C5 红；④自检码回 `0xE1` ⇒ C1 红；⑤**删 `cg5 rc3` 写入** ⇒ `landed=yes` 消失、rc `0x0f`、**C12 红**；⑥**去掉 `if (dadao_trap_busy)`** ⇒ `recursive` 行消失、rc `0x0f`、**C13 红**。
5. 补丁纪律：`apply_series --component linux` 幂等（`base+1` 跳过）、`make_patch linux` 二次导出 0 written（63 补丁）、`check-patch-tree` linux 段 **0 problem**、`--source-state` linux **OK**、`check-component-changelog` PASS。
6. 完成区无运行期路径；未改 `spec/`、`contracts/`、`tests/`、`Makefile`、台账、`discussing.md`。

**旧→新退出码（"自检"= guest 段 `0x01–0x7F`；"异常终止"= monitor 段 `0xC0|(mode<<4)|bit` 或其它 cfx 段 `0x80|cfxHA`）**：
`0xE1→0x01` magic｜`0xE2→0x02` version｜`0xE3→0x03` size（自检）；`0xE4→0x04` hart_id｜`0xE5→0x05` page_size_log2｜`0xE6→0x06` kernel_base｜`0xE7→0x07` image_range｜`0xE8→0x08` not_start_kernel（自检）；`0xEC→0x09` PT base｜`0xED→0x0a` PT entry｜`0xEE→0x0b` ptw off（自检）；新增 `0x0c` 探针注册失败、`0x0d` 未定义恢复策略、`0x0e` 重入、`0x0f` 探针超命中预算（自检）；`0xE9→0xE1` CFXMEM、`0xEA→0xE7` CFXPERM、其余 cause → `0xE0|bit`（**monitor 段**）；**表外 cause → `0xE0|(__ffs(cause)&0xF)`（monitor 段，例 `0x20→0xE5`）**；**`CFXTRAP`/`CFXESC` → `0x82`=`0x80|cfxHA(2)`（其它 cfx 段）**。

**新发现/坑**：
- 块传送首格是 offset 0：`stm.o {rd1:rd63}, [base, rd0]` 会把 rd1 写到 `frame.rd[0]`（整帧错位一格）；从非 0 槽起存要给非 0 index，`ldm` 的 base 不得落在传送范围内。
- `current` 由 SP 推导时，静态 early stack（栈底无 `thread_info`）会让 `pr_notice()` 直接 CFXMEM；进 `start_kernel()` 前必须切到 init task 栈。
- 本 target 不支持 `&&label`（与 `__builtin_return_address()` 折 0 同源）⇒ 需要「跳到新 ip」的探针只能落到**函数**符号。
- `Kconfig` `bool default y` 与「defconfig 删行」不等价；依赖不满足时 Kconfig 直接不写该符号 ⇒ 配置切片的 `=n` 断言按「无 `SYM=` 行」判。
- 探针必须带命中上限，否则「偏移/重定向写错」表现为超时而不是可报告的失败。

**遗留问题**：① **supv monitor 段编码仍需裁定**：裁定示例 `0xD0|bit`（=jail）与同段公式 + `spec/Kaiwu §7.1`（supv=10 ⇒ `0xE0|bit`）冲突；实现按 spec+公式（`0xE1`），模式位从帧现场读，门控期望从 §7.1 现场解析并打印该冲突（待裁定 4）。② K2 边界暂放 `setup_arch()` 末尾（待裁定 6）。③ `pt_regs.status` 无硬件来源写 0（待裁定 3）。④ L1 三项红均属他任务残留（chipyard 日志名/`m14-linux-005` 临时目录），未代删。
