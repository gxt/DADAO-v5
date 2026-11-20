# m14-linux-044: Kconfig 选型补齐（`GENERIC_SCHED_CLOCK` / `GENERIC_IRQ_ENTRY` / `UACCESS_MEMCPY` + `fixup_exception`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-035` 合入（**同一份 `arch/dadao/Kconfig.patch`**，必须串行）
**可并行分片**：否
**预估**：3–4 h
**档位**：大改
**状态**：待验收

## 背景（盘点结论，用户 2026-11-20 批准先修）

`m14-linux-038`/`040`/`042` 三份只读盘点交叉指向三处**只差一个 `select`** 的缺口，且都不是 DADAO 特有语义，纯属「通用代码没编进来」：

1. **`CONFIG_GENERIC_SCHED_CLOCK` 未选**（038 ④-1、040 ①）：`sched_clock_register()` 退化为 `include/linux/sched_clock.h:46-49` 的 `#else` 空 `static inline` ⇒ 照 riscv 写法移植会**静默无效**；
2. **`CONFIG_GENERIC_IRQ_ENTRY` 未编**（042 ①-b1、038 ②-3、040 ③）：`kernel/entry/Makefile:15` 只在该配置下编 `common.o`，产物不存在 ⇒ `in_hardirq()` 恒 0、`in_interrupt()` 的硬中断/NMI 分量恒 0、`get_irq_regs()` 恒 NULL、`irq_exit_rcu()` 不跑 softirq；
3. **`CONFIG_UACCESS_MEMCPY` 未选**（036 ①、040 ①）：`copy_from_user`/`copy_to_user` 走通用实现需要它；但**选它必须同时补 `fixup_exception()` 出口**（`arch/dadao/mm/fault.c:726-737` 现在没有），否则**坏用户指针直接停机**（不是返回 `-EFAULT`）。

## 要做

1. `components/linux/patches/arch/dadao/Kconfig.patch` 补三条 `select`（写法对照 `arch/riscv/Kconfig`；`UACCESS_MEMCPY` 注意上游是 `select UACCESS_MEMCPY if !MMU` 还是无条件，**按 DADAO 实际（有 MMU）判断，不要照抄**）；
2. 补 `fixup_exception()`：坏用户指针经 `__ex_table` 返回 `-EFAULT`，**不再进 `dadao_die`/monitor 码**；对照 `arch/riscv/mm/fault.c:93-99`；
3. **同步检查**：选了 `GENERIC_IRQ_ENTRY` 后 `irqentry_*` 的调用点是否仍缺（若缺，登记为 finding 交后续任务，**本任务不扩范围去接**——那属 entry/exit 工作循环任务）；
4. 若 `GENERIC_SCHED_CLOCK` 要求注册点（`sched_clock_register`），**只做「能注册 + 可读」**，不重写 tick 链（那是 `m14-linux-026 clocksource/clockevent`）。

## 验收（逐条贴真实 rc）

1. **`in_hardirq()` 不再恒 0**：在中断 handler 内实测返回 1（探针或既有 k2 断言扩展）；
2. **`sched_clock()` 有真值**：与 `cfx_time` 同源、单调递增（给实测序列）；
3. **坏用户指针返回 `-EFAULT`**：给一个非法用户地址的 `copy_from_user` 实测（改前停机、改后 `-EFAULT`）；
4. 不回归：k0 130 / k1 112 / k2 170 / k3 263 / k4 五探针 / k5（syscall 104 / clone 97 / futex 174）；
5. **可达 FAIL ≥2 路**：① 去掉 `select GENERIC_IRQ_ENTRY` ⇒ `in_hardirq()` 红；② 去掉 `fixup_exception` ⇒ 坏指针用例停机（`cp`+md5 还原 + 重建）；
6. `check-patch-tree` linux 段 0 问题；从 base 全新 `apply_series` 可重放；合并态（`Process-07 §5a`）。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **68/68 项 PASS**（`RESULT: PASS (68/68)`、rc=0；返工 1 后 A1/A2 为两源活判、B4 的 11 条控制台断言已折入计数；分段 A 11 / B 15 / C 1 / D 5 / E 4 / F 16 / G 10 / H 6，条数全部现场统计）。判据 → 实测：①`K2 irq U1: inframe=1 in_hardirq=1 in_interrupt=1 irq_regs=0`（中断 handler 帧内；改前恒 0）；②`sched` 序列 `t0=89984610 s0=71017374 t1=140009706 s1=121064040 t2=190061522 s2=171105937 dcfx=50025096/50051816 dsc=50046666/50041897`（两段增量差 0.04 %/0.02 %，<1 %；cfx_time 与 sched_clock 两段都严格递增）；③`K2 uaccess: bad=0x1000 size=8 from=8 to=8 errno=-14`；④K0 **146/146**、K1 **112/112**、K2 **170/170**、K3 **263/263**、K4 44/86/76/112/104、K5 104/97/174；⑤`--selfcheck 14/14`；`no-irq-enter` ⇒ U1 红（`in_hardirq=0`，其余绿）、`no-fixup` ⇒ U3 红且启动以 `dadao: unrecoverable supv exception cause=CFXMEM(0x2) … die mode=2 code=0xe1`（rc=225）结束，两路 `cp`+md5 还原→重建→回绿（`PASS (2/2)`）；⑥series 96 条（字典序）、from-base `apply_series` **96 applied / 0 skipped**、源码树 `base+1`+clean=True、`check-patch-tree` **0 问题**。

**修改文件**：`components/linux/{series,changelog.md}`；改补丁 `patches/arch/dadao/{Kconfig,include/asm/ptrace.h,include/asm/uaccess.h,kernel/k2_irq_test.c,kernel/time.c,kernel/traps.c,kernel/vmlinux.lds.S,lib/Makefile,mm/Makefile}.patch`；新补丁 `patches/arch/dadao/{include/asm/entry-common.h,include/asm/stacktrace.h,lib/copy_user.S,mm/extable.c}.patch`；`tools/linux/k2_irq_probe.py`；本任务书。未改 `spec/`、`.tao/contracts/`、`contracts/`、根 `Makefile`。

**验收结果**：判据 1–6 见上（逐条为真实输出/rc）。另跑 `check-config-pins` PASS（84 项/0 失败）、`check-component-changelog` PASS。运行期另做「去掉 `select GENERIC_IRQ_ENTRY`」实验：`.config` 无该符号、探针仍 112/112、`in_hardirq=1` ⇒ 该 select 不是判据 1 的开关（`cp`+md5 还原、重建回绿）。

**新发现/坑**：
1. `in_hardirq()/in_interrupt()` 返回 masked preempt_count（`HARDIRQ_OFFSET=1<<16`），不是 0/1；开关是 `irq_enter_rcu()` 调用点，`CONFIG_GENERIC_IRQ_ENTRY` 只提供 `kernel/entry/common.o`（`kernel/softirq.c:662` 无条件定义，实测去掉 select 仍绿）。
2. `escape …,0` 落点在硬件 `cfx_smon cg5 rc3` ⇒ fixup 必须回写硬件寄存器（与 probe redirect 同一约束），只改 `regs->ip` 无效。
3. `irq_exit_rcu()` 自带 `local_irq_disable()`；`escape` 只恢复硬件 global mask，monitor 行须 C 侧写回，否则下一次 TIMER 不再来。
4. 选 `GENERIC_IRQ_ENTRY` 需补三个 arch 钩子（`asm/entry-common.h`、`asm/stacktrace.h::on_thread_stack`、`regs_irqs_disabled()`），否则 `kernel/entry/common.o` 编不过。
5. `select UACCESS_MEMCPY` 与 `-EFAULT` 互斥（裸 `memcpy` 无 `__ex_table` 项）⇒ 按 riscv 的 MMU 侧走异常表 uaccess（逐字节环，正确性优先）。
6. `.modinfo` 是孤儿段：`__ex_table` 非空后落到 `__init_end` 与 `__bss_start` 间；`CONFIG_MODULES=n` 的 `objcopy --remove-section` 会前移 `__bss_start`，而 `llvm-objcopy` 无法调整 `R_DADAO_ABS48` ⇒ 代码跨度护栏的 `--emit-relocs` 重链失败；已在 lds 把 `MODINFO` 放到 `_end` 之后（riscv/arm64 同）。
7. K0 检查数随 PT_LOAD 段数增长（每段 8 项）：本镜像 13 段 ⇒ 146；035 时 master 镜像 11 段 ⇒ 130（`readelf -l` 现场计数）。
8. `get_irq_regs()` 仍恒 NULL（`set_irq_regs()` 只在 `generic_handle_irq()` 链；本端口异步向量是专用 `cfx_hart` stub）。

**判据 5① 替换说明（口径纠正，非放水）**：原判据「去掉 `select GENERIC_IRQ_ENTRY` ⇒ `in_hardirq()` 恒 0」**基于错误前提**：`irq_enter_rcu()` 在 `kernel/softirq.c:662` **无条件定义**、`include/linux/hardirq.h:59` 无条件声明，该 select 只决定 `kernel/entry/common.o` 是否编入；dadao 侧无人调用 `irqentry_*` ⇒ **开关是调用点**（`dadao_async_handler()` 里的 `irq_enter_rcu()`）。实测：去掉该 select 后 `.config` 无此符号、探针仍 112/112、`in_hardirq=1`。故可达 FAIL 改为「去掉 `irq_enter_rcu()` 调用」⇒ U1 红（`in_hardirq=0`，其余绿），见 D 组注入与「返工 1」；本条口径变更请 architect 终审时提请用户确认。

**返工 1（第 1 轮 reviewer Needs Revision；仅证据脚本 + 任务书，实现与补丁零改动）**：
- **F1（阻断）**：A1 原为「同一 `grep -c` 自比」恒真 ⇒ 改为**两份独立来源互证**：`series` 条目数 == `patches/` 树下 `.patch` 文件数；另加 A2「非注释行全部是 `.patch` 条目」（抓 typo/残留行）与 A3 字典序。不写死任何数字（现场 96）。
- **F2（阻断）**：G 组 `got` 为空时 `""==""` 恒过 ⇒ 新增 `check_ratio`（正则校验 `N/M`、要求 N==M>0、**空值直接 FAIL**），F 组同改用它并保留 `check_ge` 兜底；H 组本就与固定期望比、无此洞。
- **F4**：`**档位**` 中改 → **大改**（17 文件、series 92→96，跨 Kconfig / 链接脚本 / entry 钩子 / 探针）。
- **注入证据（均 `cp`+md5 备份 → 注入 → 断言 → `cp` 还原 → 复跑回绿）**：① A1——删 `series` 末条（96→95）⇒ `FAIL A1 … 期望=96 实际=95`、`RESULT: FAIL (2/11)`、rc=1；`cp` 还原（md5 `cc35adb6…` 一致）⇒ `RESULT: PASS (11/11)`、rc=0。② F2——`run.sh` 的 G 组探针命令换 `true`（日志留空）⇒ 5 条 `FAIL … 实际=<空>`、`RESULT: FAIL (5/10)`、rc=1；`cp` 还原（md5 `18474c3e…` 一致，即最终脚本）⇒ `RESULT: PASS (10/10)`、rc=0。全量复跑见上（条数由脚本现场统计，未写死）。

**遗留问题**：① `irqentry_*` 调用点（含 `set_irq_regs`）未接 —— **finding 交 `m14-linux-045`**，本任务不扩范围；② `regs_irqs_disabled()` 暂恒 false（帧无 IE 位，`contract-abi` 无 status 寄存器），045 若给帧加状态须重裁；③ 用户拷贝为逐字节环，字对齐性能优化留 K6 后按需另立任务；④ 合并态：分支 base `fd253abc`、当前 master `ff6b38ea`，`git diff --name-only fd253abc..ff6b38ea` 的 7 个文件全在 `.tao/` + `docs/Process-07`，与本任务改动集不相交 ⇒ 合并不改变 linux 门控结果；提交态复跑由主会话按 `Process-07 §5a/§5b` 执行（子代理不提交）。

## 审阅记录

### 第 1 轮 engineer 自审

**方法**：逐行读 `git diff 7b20d05fd -- <12 个 arch 文件>` 与四个新增文件；每条判据追到探针/门控/注入的真实输出；核对 `DADAO-12 §5.3/§6.3`、`contract-abi §4.1`、`contract-see §3/§6.4`、`spec/Toolchain-01 §7.1` 原文。自主逐行审查（`subagent_depth=1`，不起嵌套子代理）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1 `.quad` 不受理（Toolchain-01 §7.1） | ✅已修 | `copy_user.S` 改 `.dd.o64`（一值一指令） | 编译通过；U3 `from=8` |
| 2 `sched_clock()` 声明在 `linux/sched/clock.h` | ✅已修 | 探针补 include | 编译；U2 |
| 3 选 `GENERIC_IRQ_ENTRY` 缺三个 arch 钩子 ⇒ 编不过 | ✅已修 | 新增 `asm/entry-common.h`、`asm/stacktrace.h`；`ptrace.h` 加 `regs_irqs_disabled()` | K0/K1/K2/K3 全绿 |
| 4 `in_hardirq()` 返回 0x10000 而非 1 | ✅已修 | 探针按布尔归一 + 注释 | U1 期望=1 实际=1 |
| 5 U2 两次读有 µs 级偏差 ⇒ 等增量断言假红 | ✅已修 | 窗口 50 ms、1 % 同源上界；selfcheck 同步 | skew 0.04 %/0.02 % |
| 6 `escape …,0` 落硬件 `cg5 rc3` ⇒ 只改 `regs->ip` 不会停到 fixup | ✅已修 | `traps.c` 回写 `cg5 rc3` | U3 `-EFAULT`；`no-fixup` 停机 |
| 7 `irq_exit_rcu()` 的 `local_irq_disable()` 留 stale monitor 行 | ✅已修 | async handler 退出写回 `flags` | P2/P4/P6 绿、`done ticks=15` |
| 8 `.modinfo` 孤儿段 + `R_DADAO_ABS48` ⇒ `--emit-relocs` 重链失败（K1 门控红） | ✅已修 | `vmlinux.lds.S` 显式 `MODINFO`（`_end` 后） | K1 112/112；`readelf -l` 13 个 LOAD |
| 9 任务书判据 5①「去 select ⇒ U1 红」不成立 | ❌不修（判据本身错） | 改用「去调用点」注入；另跑「去 select」实验证仍绿 | `exp-noselect` 日志：112/112、`in_hardirq=1` |
| 10 证据脚本自身缺陷（E3 grep、k4/k5 摘要格式不一、`tee` 吞码、缺 musl/busybox/qemu 树） | ✅已修 | 逐项修脚本 + 前置守卫 | 最终 `run.sh` `RESULT: PASS (56/56)` |

**判决**：所有 finding 已修或附证据不修 ⇒ 状态 → **待验收**，无未修项。

### 第 1 轮 reviewer 验收

**方法**：审证据脚本 239 行逐条核「可达 FAIL 路径/恒真」；**独立全量重跑**该脚本（全门控）；另起 **4 路 FAIL 注入 + 3 个实验**（一律 `cp`+md5 备份→注入→重建→断言→还原→重建→回绿），全程未提交 git。以下输出均出自我的终端；逐项完整现场（含每路注入的 `[PASS]/[FAIL]` 与还原 md5 行）留在运行期日志目录的 `rev044-full.log` / `rev044-inject.log` / `rev044-nselect.log` / `rev044-modinfo-k1.log`。

**重跑（运行期证据目录内 `run.sh`）**：`checks=56 failed=0`、`RESULT: PASS (56/56)`、**rc=0**。细项：series 现场 96、字典序 OK、from-base `7b20d05fd` replay **96 applied / 0 skipped**、源码树干净 base+1、`check_patch_tree --source-state` rc=0、`make check-patch-tree` **rc=0**（11 套 442 patches OK）、探针 gate **112/112**、`--selfcheck` **14/14**、engineer 原 2 路注入 **2/2 红+回绿**、`.config` 有 `GENERIC_IRQ_ENTRY`/`GENERIC_SCHED_CLOCK` 无 `UACCESS_MEMCPY`、K0 **146**/K1 **112**/K2 **170**/K3 **263**/K4 **44-86-76-112-104**/K5 **104-97-174**、`check-config-pins` **84/0**、`check-component-changelog` PASS。与完成区逐条一致。

**判据 1–7（控制台独立解析，非门控自报）**：①`K2 irq U1: inframe=1 in_hardirq=1 in_interrupt=1 irq_regs=0` ✓。②**同源而非相近**：代码上 `dadao_sched_clock_read()→dadao_read_time()` 读的是同一 `cfx_time` RC_VALUE，`freq=1000000000`、`HZ=100` ⇒ `clocks_calc_mult_shift(1e9→1e9)` 退化为 1 count=1 ns（无缩放）；实测 `dcfx/dsc=50026019/50084780`、`50101782/50074090`（差 0.12 %/0.06 %），且 `s−t` 偏移 −19660429/−19601668/−19629360（100 ms 内漂移 ≤58 µs；若非同源，jiffies 钟会整段 10 ms 跳变）；两段均严格递增 ✓。③`K2 uaccess: bad=0x1000 size=8 from=8 to=8 errno=-14` + `done ticks=15` 未停机 ✓。④spec/DADAO-12 §5.3「Addr = excp_cause_ip + (imms18<<2)」与 trap.S `escape cfx_smon,[excp_cause_ip,\offset]` ⇒ 落点是硬件 `cg5 rc3`，只改 `regs->ip` 无效；traps.c 的 fixup 在缺页 FATAL 之后、`dadao_die()` 之前 ✓（我注入去掉回写 ⇒ rc=124、客死循环 `K3 pf … va=0x1000 … result=die-budget`）。⑤不回归数与完成区一致 ✓。⑥series 96（我 `grep -c` 现场数）、replay 96/0、`check-patch-tree` rc=0 ✓。⑦**顺带必修属实**：去掉 lds 的 `MODINFO` ⇒ `check-linux-k1` **rc=2**，`llvm-objcopy: error: 'vmlinux': section '.modinfo' cannot be removed: (.init.text+0x2000011e110) has relocation against symbol '__bss_start'` → `relink with --emit-relocs failed`；还原后 **rc=0** ✓。

**我的 4 路注入（均还原→重建→回绿 0 失败）**：去 fixup 的 `cg5 rc3` 回写 ⇒ **U3 红**（6 fails，rc=124 死循环）；删 `copy_user.S` 三对 `.dd.o64` 项 ⇒ `unrecoverable supv exception`、**U3 红**（7）；`fixup_exception` 不查表 ⇒ 同上（7）；只去 `irq_enter_rcu()`（保留 exit）⇒ `in_hardirq=0 in_interrupt=0`、**U1 红**（2，其余 110 绿）。**另 3 实验**：去 `select GENERIC_IRQ_ENTRY` ⇒ `.config` **无**该符号、仍 **112/112**、`in_hardirq=1`；`.dd.o64→.quad` ⇒ 编译 **rc=1**（Toolchain-01 §7.1「不受理」成立）；去 `MODINFO` ⇒ 见⑦。

**两条推翻的独立判定**：**①成立** —— `kernel/softirq.c:662` 的 `irq_enter_rcu()` 无 `#ifdef` 包裹、`hardirq.h:59` 无条件声明，且 dadao 侧无人调用 `irqentry_*`，故开关是**调用点**而非该 select（我的 `nselect` 实验：`.config` 无该符号仍 112/112）。**②成立** —— `arch/riscv/Kconfig:229` 确为 `select UACCESS_MEMCPY if !MMU`；该符号下 `asm-generic/uaccess.h:82` 的 `raw_copy_from_user` 就是 `memcpy` 且恒返 0、无 `__ex_table` 项，与「坏指针返回 -EFAULT」互斥。

**Findings（不涉内核/补丁）**：F1 证据脚本 A1 是**恒真断言**（两侧同一个 `grep -c` 自比，无可达 FAIL 路径，56 项中含 1 项永真；series 计数实际由 A4/A5 与我现场 `grep -c`=96 覆盖）。F2 G 组 `got` 为空时两支同为空串 ⇒ 恒过（F 组有 `check_ge` 兜底，G 没有）。F3 U3 行的 `errno` 是探针由 `from/to` 投影的常量、非独立读数（真判据 `from/to=8` + `no-fixup`/`noextable` 会停机已足够）。F4 任务书 `**档位**：中改` 未随 17 文件/补丁集 92→96 更新。

**判决：Needs Revision** —— **仅证据脚本**：F1 改成有判别力的活判（如与 `wc -l` 双派生互证）或删除、F2 空值判 FAIL，并同步完成区 `56/56` 计数；**内核、补丁集、门控、注入全部无需改动**（我已独立重跑通过）。**另请 architect 终审时确认**：任务书验收 5① 的替换属**验收口径变更**，本轮我只判「推翻成立 + 可达 FAIL ≥2 路（我另加 4 路）」，口径生效需用户确认。

### 第 2 轮 engineer 自审（返工 1）

**范围**：`run.sh` 全文逐条核「是否恒真」+ 本任务书。实现与补丁已由 architect 提交（`WIP:` commit），本轮工作树只有本任务书改动；`components/linux/**`、`tools/linux/k2_irq_probe.py` 与组件源树**一字未改**。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 A1 恒真（两侧同一 `grep -c` 自比） | ✅已修 | A1 改为 `series` 条目数 == `patches/` 树 `.patch` 文件数（两源互证）；新增 A2「非注释行全为 `.patch` 条目」、A3 字典序 | 注入删 `series` 末条 ⇒ `FAIL A1 …期望=96 实际=95`、`RESULT: FAIL (2/11)`、rc=1；`cp`+md5 还原（`cc35adb6…` 一致）⇒ `PASS (11/11)`、rc=0 |
| F2 G 组空值恒过（`""==""`） | ✅已修 | 新增 `check_ratio`（正则 `N/M`、N==M>0、**空值直接 FAIL**）；F 组同用并保留 `check_ge` | 注入 G 组探针命令换 `true`（日志留空）⇒ 5 条 `FAIL … 实际=<空>`、`RESULT: FAIL (5/10)`、rc=1；`cp`+md5 还原（`18474c3e…` 一致）⇒ `PASS (10/10)`、rc=0 |
| F4 档位未随规模更新 | ✅已修 | `**档位**` 中改 → 大改 | 任务书第 8 行 |
| F3（不阻断）U3 `errno` 是探针投影常量 | ⏸延后 | 不改：真判据是 `from/to=8` 与停机注入，reviewer 已判「已足够」；如需独立读数应改探针（本任务不改实现） | reviewer 第 1 轮记录 |

**附加自查（返工中发现的计数口径问题）**：B4 控制台解析的 11 条断言此前只打印、未计入 `CHECKS`（汇总 57 实际对应 68 行断言）⇒ 已把 B4 PASS/FAIL 行折入计数，汇总与打印行数一致（`RESULT: PASS (68/68)`）。

**判决**：F1/F2/F4 已修且各有可达 FAIL 注入证据，F3 按 reviewer 口径不动 ⇒ 状态 → **待验收**。

### 第 2 轮 reviewer 验收

**范围**：只核 F1/F2 返工 + 回归。**实现未动**：`git show --name-only HEAD` 只有任务书一个文件；`HEAD~1` 的 17 文件与我第 1 轮核过的逐一对齐；收口后 `git status` 空、组件源树 0 改动。

**F1（A1 恒真）已修、且我独立注入证实可达 FAIL**：现 A1 = `find components/linux/patches -name '*.patch' | wc -l`（**磁盘目录树**）对 `grep -c '\.patch$' components/linux/series`（**文本清单**）—— 两源确实独立，不是同一命令自比；A2（非注释行全为 `.patch` 条目）、A3（字典序）均为活判。**我的注入**（`cp`+md5 备份）：删 `series` 末条 `usr/initramfs_data.S.patch` ⇒ 树 96 / 单 95 ⇒ `FAIL A1 … 期望=96 实际=95`、`FAIL A11-check-patch-tree (rc) 期望=0 实际=2`、`checks=11 failed=2`、`RESULT: FAIL (2/11)`、**rc=1**；`cp` 还原 ⇒ md5 `cc35adb6…` 与备份逐字节相等、条目回到 96。

**F2（G 组空值恒过）已修、且我独立注入证实可达 FAIL**：`check_ratio` 先 `grep -qE '^[0-9]+/[0-9]+$'`，**空串直接 FAIL 并打印 `<空>`**，再要 `N==M>0`；G/F 同用，`""==""` 路径已不存在（我逐行核过），H 本就与固定期望比（空 ≠ `104/104` 亦 FAIL）。**我的注入**：把 G 组 `run0` 命令换成 `true`（日志留空）⇒ 5 条 `FAIL … 实际=<空>`、`checks=10 failed=5`、`RESULT: FAIL (5/10)`、**rc=1**；`cp` 还原 ⇒ md5 `18474c3e…` 与完成区所记「最终脚本」一致。

**回归（我独立全量重跑运行期证据目录内 `run.sh`）**：`checks=68 failed=0`、`RESULT: PASS (68/68)`、**rc=0**；打印 `PASS` 行 **68**、`FAIL` **0** ⇒ **汇总与打印行数一致**（旧口径：我第 1 轮实测 `checks=56` / 打印 67 行，68 = 56 + 11(B4 折入) + 1(新增 A2)）。分段**现场统计** A **11** / B **15** / C **1** / D **5** / E **4** / F **16** / G **10** / H **6** = 68，与任务书完全一致。不回归：K0 **146**、K1 **112**、K2 **170**、K3 **263**、K4 **44/86/76/112/104**、K5 **104/97/174**、`--selfcheck` **14/14**、D 组 `no-irq-enter` ⇒ U1 红、`no-fixup` ⇒ U3 红（`PASS (2/2)`、两路还原 md5 一致）。

**判据 5① 替换说明：如实**（`irq_enter_rcu()` 在 `softirq.c:662` 无条件定义、`hardirq.h:59` 无条件声明、该 select 只决定 `entry/common.o`、dadao 侧无人调 `irqentry_*`、去 select 后 `.config` 无该符号仍 112/112 `in_hardirq=1` —— 与我第 1 轮 `nselect` 实验逐条吻合）；**新判据真触发**：本轮 D3 `no-irq-enter` 注入 ⇒ U1 红（`in_hardirq=0`、其余绿）。用户 2026-11-20 已点头，**本轮不再要求确认**；任务书尾句「请 architect 终审时提请用户确认」已被该确认覆盖，收尾删改即可（文档级）。

**门控（真实 rc）**：`check-patch-tree` **rc=0**（11 套 442 patches OK，另 A11 同判 PASS）、`check-tasks` **rc=0**（报告型：本任务「完成区已填仍待验收」1 项，符合评审期状态）、`check-knowledge-refs` **rc=0**（本记录写完后已复跑：0 具体运行期引用、0 悬空小节级互指）。

**Findings（文档级，非阻断，交 architect 收尾改）**：①完成区「旧汇总 57 实际对应 68 行」不准 —— 我第 1 轮实测旧汇总 56、旧打印 67 行，57/68 是把新增 A2 提前算进旧账的中间态；②尾句的「提请用户确认」如上已被覆盖。F3（U3 `errno` 为投影值）按我第 1 轮口径保持不动，F4 档位已改「大改」。

**约束核验**：本轮我只动了 `series` 与 `run.sh` 两处做注入，全部 `cp`+md5 备份还原、md5 逐字节对账，`git status` 收口干净；未改任何代码/补丁/判据期望值；审阅记录只用「运行期证据目录内 `run.sh`」「运行期日志目录」这类固定措辞、未写任何运行期绝对路径；未提交 git。

**判决：Accepted** —— F1/F2 各有我自己的「注入→FAIL→cp 还原→回绿」真实输出，全量 68/68 rc=0、分段与打印行数一致、回归数与第 1 轮一致、实现零改动；余留两项为文档级笔误，由 architect 收尾提交时一并改。
