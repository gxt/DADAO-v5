# m14-linux-043: 启动/初始化 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：2 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：待验收

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

第一批（`m14-linux-036`–`040`，mm/syscall/时间/信号/Kconfig）已交付并形成格式基线：**每条带两侧 `文件:行号` + 影响面 + P0/P1/P2**，覆盖数**现场派生**，抽查用 `sed -n` 贴原文。

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/kernel/{head.S,setup.c,init.c}`、`lib/`（内存清零/字符串）、`include/asm/setup.h`、`Kconfig` 的启动相关项；对比 `arch/riscv/kernel/{head.S,setup.c}`（主）与 `arch/arm64/kernel/{head.S,setup.c}`（参照）。重点：`earlycon`/`early_init_dt`、内存探测与 `meminfo`、`paging_init`、`setup_arch` 的分段职责、`init_task` 栈初始化。

## 要做

逐个 hook / 机制判定属于哪一类，并给证据：

1. **缺失 hook**：上游有、我们没有；
2. **语义不符**：有但行为不同（返回码 / 副作用 / 加锁 / 顺序 / 何时切栈）；
3. **旁路 vs 通用**：我们自造实现，上游走通用 `kernel/`、`mm/` 路径；
4. **Kconfig 缺口**：缺 `select` / `depends on` 导致通用代码没编进来。

**每条格式**：`arch/dadao/<file>:<line>` ↔ `arch/riscv/<file>:<line>`（必要时补 `arch/arm64`）/ 影响面 / 优先级（**P0** 阻塞在跑任务；**P1** 影响正确性；**P2** 仅形态差异）。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行），**每条带两侧 `文件:行号`**；
2. **覆盖现场派生**：列清检查了哪些 hook / 机制及条数（不写死），并写清枚举口径（命令）；
3. **抽查 ≥5 条**：用 `sed -n '<行>p'` 贴两侧原文，**不许凭记忆**；
4. **不改任何代码**：用 `git show --name-only HEAD` 与 `git status -uall` 判「只改了本任务书」（**不要用裸 `git diff`/`git status` 计数**——提交后会变空，`m14-linux-036` 已踩过）；
5. 不占写者锁、不重建、不跑仿真。

## 盘点结论

**基线**：linux 源树 `7b20d05fd`（7.2.10）＋`c5f411a3a`（dadao 补丁态；只读、树 clean）。下文 dadao/riscv/arm64 行号均取自该态。`arch/dadao/kernel/init.c` **不存在**（启动 C 代码在 `arch/dadao/kernel/setup.c`＋`arch/dadao/kernel/early_console.c`），故按实际文件面盘点。036 已报的「启动建表手写」不重复，只标同族。共 **19 条**（①6 ②6 ③4 ④3）；**无 P0**——本轮未发现阻塞在跑任务（`m14-linux-035`）的项。

### ① 缺失 hook（6 条）

- **[P2] `setup_initial_init_mm()` 未调用**：`arch/dadao/kernel/setup.c:209-266`（`setup_arch` 全函数无此调用）↔ `arch/riscv/kernel/setup.c:312`、`arch/arm64/kernel/setup.c:283`。`init_mm` 的 `start_code/end_code/end_data/brk` 唯一设置点是 `mm/init-mm.c:56-59` ⇒ 本机四项恒 0（这些字段现无消费者，症状潜伏）。
- **[P2] `memblock_allow_resize()` 未调用**：`arch/dadao/kernel/setup.c:214`（只有 `memblock_add`），全 arch 无该调用 ↔ `arch/riscv/mm/init.c:1356`。`memblock_can_resize` 保持 0（`mm/memblock.c:2141` 函数头、`:2143` 置 1）⇒ 此后任何 `memblock_add/reserve` 的扩容静默失败（`memblock_double_array` 走 -1 分支，区域丢失而非报错）。
- **[P2] `misc_mem_init()`（`early_memtest`＋`memblock_dump_all`）缺**：`arch/dadao/kernel/setup.c:266`（`setup_arch` 收尾）↔ `arch/riscv/kernel/setup.c:335`、`arch/riscv/mm/init.c:1361`。启动期无内存自检、无 memblock 布局转储。
- **[P2] `init_resources()`／`request_standard_resources()` 缺**：`arch/dadao/kernel/setup.c:209-266`（无 `iomem` 登记，`grep -rn "iomem_resource" arch/dadao/` 0 命中）↔ `arch/riscv/kernel/setup.c:337`、`arch/arm64/kernel/setup.c:348`。`/proc/iomem` 不含内核 code/data/bss 段。
- **[P2] `early_ioremap_setup()`／fixmap 缺**：`arch/dadao/include/asm/fixmap.h:10`（`FIX_NONE` 桩）↔ `arch/riscv/kernel/setup.c:316`＋`arch/riscv/Kconfig:111`（`select GENERIC_EARLY_IOREMAP`）。早期 I/O 映射与依赖它的 `earlycon`／`EARLY_PRINTK` 在架构层不可用。
- **[P2] `free_initmem()` 用 weak 默认**：`init/main.c:1562`（weak 版）↔ `arch/riscv/kernel/setup.c:374`。与 036「无内核 W^X」同族（`mark_rodata_ro` 在 `init/main.c:1550`，dadao 无定义）；此处只记 `__init` 段释放后不做 RO/NX。

### ② 语义不符（6 条）

- **[P1] 进 C 前没有任务栈 ⇒ 早期 `current` 为 NULL**：`arch/dadao/kernel/head.S:44`（`set.rb rb1, early_stack_top`；16 KiB `.bss` 栈，见 `arch/dadao/kernel/head.S:144-145`）＋`arch/dadao/kernel/setup.c:176`（此时才切到 `init_stack`）：`dadao_start_kernel` 的 C 代码（`memcpy`/`vsnprintf`/cfx 写）跑在无 `thread_info` 的栈上 ↔ `arch/riscv/kernel/head.S:286-287`（进 C 前 `sp = init_thread_union + THREAD_SIZE - PT_SIZE_ON_STACK`）。`current` = `current_thread_info()->task`（`arch/dadao/include/asm/current.h:13`、`arch/dadao/include/asm/thread_info.h:43`）⇒ 该窗口 `current` 不是 `&init_task`（本布局下 64 KiB 块基址落在 `.bss` 全零区，实测为 NULL）；任何 `printk`／`kmalloc`／`might_sleep` 即空指针。现靠「窗口内只调不碰 `current` 的函数」成立。
- **[P1] 启动保留区与 initramfs 区未 `memblock_reserve`**：`arch/dadao/kernel/setup.c:225`（只保留 `[__pa(_start), __pa(_end))`）↔ `arch/riscv/mm/init.c:291`（`reserve_initrd_mem()`）、`arch/riscv/mm/init.c:298`（`early_init_fdt_scan_reserved_mem()`）。契约 `.tao/contracts/contract-linux-boot.md:42` 要求「启动保留区 `[2 TiB, 2 TiB+128 KiB)` 与 initramfs 区在内核接管后须保留」；`memblock_free_all()`（`mm/mm_init.c:2744`）会把 PA `[0, 0x2_0000)`（首张页表页＋boot info 页）与 PA `[0x400_0000, 0x600_0000)`（32 MiB initramfs 上限）交给 buddy。`setup_arch` 还会二次解析该 boot info 页（`arch/dadao/kernel/setup.c:212`）。
- **[P1] 生产镜像走不到 `rest_init()`**：`init/main.c:1192` 插 `dadao_k4_boundary()`，其无 selftest 时无条件 `dadao_early_exit(0)`（`arch/dadao/kernel/setup.c:367`）；能继续的仅 `arch/dadao/kernel/setup.c:326`／`arch/dadao/kernel/setup.c:335`／`arch/dadao/kernel/setup.c:344`／`arch/dadao/kernel/setup.c:353`／`arch/dadao/kernel/setup.c:362` 五个 probe 分支 ↔ 上游同位置只有 `rest_init()`（`init/main.c:1195`）。时序对应：`mm_core_init_early()`（`init/main.c:1005`）→`mm_core_init()`（`init/main.c:1044`）→本钩子（`init/main.c:1192`）→`rest_init()`（`init/main.c:1195`），即「页分配器已就绪、尚未建第二个任务」这一段在上游没有 arch 出口，本机把它做成了分段点。defconfig（无 selftest）镜像必停 K4；跑 `/init` 的镜像必须开一个 probe，且判定权在 probe 的 syscall hook。
- **[P2] `paging_init()` 语义为空**：`arch/dadao/mm/init.c:44-53`（只 `init_mm.pgd = swapper_pg_dir`，而 `mm/init-mm.c:34` 已把该字段静态初始化为同一符号）↔ `arch/riscv/mm/init.c:1350-1357`（`setup_bootmem`＋`setup_vm_final`＋`memblock_allow_resize`）。启动建表实际在 `arch/dadao/kernel/setup.c:158`→`arch/dadao/mm/k1_pt.c`（036 已报「手写」；本条只记 `paging_init` 无职责）。
- **[P2] `trap_init()` 是死 hook**：`arch/dadao/kernel/setup.c:421`（空实现；`arch/dadao/kernel/setup.c:431-437` 注释自证 weak＋inline 使调用消失）↔ riscv 无 `trap_init`（向量在 `arch/riscv/kernel/head.S:303` 的 `call .Lsetup_trap_vector` 装）。实际安装点 `arch/dadao/kernel/setup.c:157`（`dadao_supv_vector_install()`，早于 `start_kernel`），语义正确但 hook 名存实亡。
- **[P2] 启动期失败只有 host 退出码**：`arch/dadao/kernel/head.S:94`（`jump [rb5, rd0, 0]`→`dadao_bootinfo_reject`）、`arch/dadao/kernel/early_console.c:184`（`SYS_EXIT`）⇒ boot info 不合格只回 `0x01`–`0x08`，无 printk／`panic`／栈回溯 ↔ `arch/riscv/kernel/setup.c:266`（`pr_err("No DTB passed to the kernel\n")`：先落日志再降级）。

### ③ 旁路 vs 通用（4 条）

- **[P1] 无 DT，自造 15 字段 boot info＋自造校验**：`arch/dadao/include/asm/setup.h:11-31`、`arch/dadao/kernel/setup.c:88-109`、`arch/dadao/kernel/head.S:68-82` ↔ `arch/riscv/kernel/setup.c:311`（`parse_dtb()`）、`arch/riscv/Kconfig:212-214`（`select OF/OF_EARLY_FLATTREE/OF_IRQ`）、`arch/arm64/kernel/setup.c:183`（`early_init_dt_scan`）。内存探测也只剩单块 `memblock_add`（`arch/dadao/kernel/setup.c:214`），无 `memory` 节点扫描（riscv 经 `arch/riscv/kernel/setup.c:258` 的 `early_init_dt_scan`）也无 `memblock_cap_memory_range`（`arch/riscv/mm/init.c:262`）；memory／cmdline／initrd／console 全由自造通道给，`of_*`、`/proc/device-tree`、`earlycon`、`reserve_mem` 等通用设施不可用。
- **[P1] initramfs 走「内建」旁路，契约的固件通道未接**：`arch/dadao/kernel/setup.c:123`（`initramfs_base/size` 只被打印；全 arch 无第二处使用）↔ 契约 `.tao/contracts/contract-linux-boot.md:73`、`.tao/contracts/contract-linux-boot.md:74`（`INITRAMFS-BASE`／`INITRAMFS-LIMIT`）。实际由 `CONFIG_INITRAMFS_SOURCE` 内建（`tools/linux/make_defconfig.py:325`）⇒ initramfs 绑定内核镜像，契约 §3.2 两字段无消费者，该 32 MiB 区亦未保留（见上节保留区条）。
- **[P2] 早期控制台自造，绕过 printk／earlycon**：`arch/dadao/kernel/early_console.c:68-71`（`SYS_WRITEC` 一字节一 trap，调用点在 `:71`）、`arch/dadao/kernel/early_console.c:153`（`dadao_early_printf`）、`arch/dadao/kernel/early_console.c:229`（`console_initcall` 注册 `semihost`）↔ `drivers/tty/serial/earlycon.c:249`（`early_param("earlycon", …)`）。`console_init()`（`init/main.c:1122`）之前 `printk` 无输出端（该窗口内 `panic` 静默），控制台不可换、不可关。
- **[P2] 分段点/selftest 是自造的 20 个 `CONFIG_DADAO_*`**：`arch/dadao/Kconfig.debug:11-393`（20 项，按里程碑 K1 1／K2 9／K3 2／K4 5／K5 3；其中 3 个是 `*_STOP` 分段点，其余 17 个是 selftest/case），分段点插进通用 `start_kernel`／`setup_arch`（`init/main.c:984`、`init/main.c:1192`、`arch/dadao/kernel/setup.c:248`）并以 `SYS_EXIT` 结束启动 ↔ 上游 `lib/Kconfig.debug:951`（`DEBUG_MEMORY_INIT`）、`CONFIG_KUNIT` 等只打印/自测、不改控制流。附带缺口：defconfig `CONFIG_EXPERT=y`（`arch/dadao/configs/defconfig:33`）而 `DEBUG_MEMORY_INIT` 默认 `!EXPERT`（`lib/Kconfig.debug:953`）⇒ 内存初始化自检默认关闭。

### ④ Kconfig 缺口（3 条）

- **[P1] `CMDLINE` 缺 `CMDLINE_FALLBACK/EXTEND/FORCE` choice（启动侧证据）**：`arch/dadao/Kconfig:94-100` ↔ `arch/riscv/Kconfig:1207-1248`（choice 在 `arch/riscv/Kconfig:1218`–`arch/riscv/Kconfig:1248`，`CMDLINE_FALLBACK` 起于 `arch/riscv/Kconfig:1226`）。证据链：7.2.10 里 `CONFIG_CMDLINE` 的唯一通用消费者是 `drivers/of/fdt.c:1133`（`#ifdef CONFIG_CMDLINE`，`CONFIG_OF=y` 才编），本 arch `CONFIG_OF=n`（`arch/dadao/configs/defconfig:38`）⇒ 该字符串**无消费者**；`boot_command_line`（`init/main.c:146`）在 `arch/dadao/` 无任何写入者（只有 `arch/dadao/kernel/setup.c:240` 的读）⇒ `parse_early_param()`（`init/main.c:1020`）与 `__setup` 永远收不到参数。`cmdline_base/size` 本身是契约保留字段（`.tao/contracts/contract-linux-boot.md:100`、`.tao/contracts/contract-linux-boot.md:101`），故缺的不是「读 boot info」，而是「内建命令行这条通用退路」。
- **[P2] 缺 `select OF/OF_EARLY_FLATTREE/OF_IRQ`**：`arch/dadao/Kconfig:9-26` ↔ `arch/riscv/Kconfig:212-214`。有意为之（无 DT），但同时关掉 `earlycon`／`initrd`／`reserve_mem` 三条通用通道。
- **[P2] `CONFIG_ARCH_SEMIHOSTING_CONSOLE` 无消费者**：`arch/dadao/Kconfig:80-86` 声明、`arch/dadao/configs/defconfig:10` 置 `y`，全树仅此两处（`grep -rn ARCH_SEMIHOSTING_CONSOLE` 2 命中）；`early_console.o` 恒编（`arch/dadao/kernel/Makefile:2`）⇒ 关掉该开关不改变任何行为 ↔ `drivers/tty/serial/earlycon-riscv-sbi.c:52`（`EARLYCON_DECLARE(sbi, early_sbi_setup)`：riscv 的控制台选择符号由驱动侧消费者兑现）。

## 覆盖与口径（现场派生）

- **① 通用启动序列的 arch 插入点**：`grep -nE "^[[:space:]]*(setup_arch|trap_init|init_IRQ|time_init|mm_core_init|mm_core_init_early|arch_cpu_finalize_init|arch_post_acpi_subsys_init|smp_prepare_boot_cpu|free_initmem|mark_rodata_ro|console_init|parse_early_param|rest_init|boot_init_stack_canary)\(" init/main.c` ⇒ 实测 **15**（`init/main.c:1004`–`init/main.c:1600`），逐个判定本 arch 提供/缺口。
- **② dadao 在通用代码里的注入点**：`grep -c dadao init/main.c` ⇒ **8**（`init/main.c:984`／`init/main.c:1192` 两个流程钩子，其余 6 处为 `kernel_init` 打印与 probe 调用）。riscv/arm64 在 `init/main.c` 内注入 **0**。
- **③ scope 文件逐函数核对**：`arch/dadao/kernel/head.S`（147 行）、`arch/dadao/kernel/setup.c`（455 行）、`arch/dadao/kernel/early_console.c`（229 行，启动控制台）、`arch/dadao/mm/init.c`（`setup_arch` 调用的 `paging_init`/`arch_zone_limits_init`）、`arch/dadao/kernel/Makefile`、`arch/dadao/include/asm/{setup,thread_info,current,fixmap,string}.h`、`arch/dadao/lib/`（2 文件）、`arch/dadao/Kconfig`（**15** 个 config）、`arch/dadao/Kconfig.debug`（**20** 个 config）、`arch/dadao/configs/defconfig`。
- **④ Kconfig 差集**：riscv `select` 行 **276**（去重 **271**，与 036 一致）；boot 相关过滤 `select (OF|OF_EARLY_FLATTREE|OF_IRQ|GENERIC_EARLY_IOREMAP)` ⇒ **5 行 / 4 个符号**（`OF` 在 `arch/riscv/Kconfig:212`、`arch/riscv/Kconfig:1349` 各一次），逐项判定入结论 2 条（DT 一组、early_ioremap 一条）。
- **⑤ 结论条数**：**19**（①6 ②6 ③4 ④3），全部带两侧 `文件:行号`；小节条数由脚本现场计数核对。
- **⑥ 核过不列条（8 项，判为等价/复用，非差异）**：字符串走上游 `lib/string.o`（`lib/Makefile:36`；`arch/dadao/include/asm/string.h:6` 为空守卫，riscv 另有手写件，属性能选择）；`arch/dadao/lib/delay.c` 与 `arch/riscv/lib/delay.c` 同构；`init_task` 栈顶偏移与 `task_pt_regs()` 一致（`arch/dadao/include/asm/processor.h:102`），`sizeof(struct pt_regs)=2064` 为 16 的倍数，满足 `.tao/contracts/contract-abi.md:134` 的 SP 16 B 对齐；`.bss` 清零与 riscv 同构（`arch/dadao/kernel/head.S:56-66` ↔ `arch/riscv/kernel/head.S:273-280`）；`arch_zone_limits_init`／`max_pfn`／`min_low_pfn` 语义等价（本机手填 vs riscv `setup_bootmem`）；`set_task_stack_end_magic`／`start_thread`／`flush_thread` 走上游通用；`*cmdline_p = boot_command_line` 与 riscv/arm64 同形（问题在命令行来源，不在赋值）；`GENERIC_CALIBRATE_DELAY`＋`loops_per_jiffy` 复用通用校准。

## 完成区

**测试结果**：通过 42/42（运行期证据目录内 `run.sh` 退出码 0，含 3 路注入自检）；失败项：无。

**修改文件**：`.tao/tasks/linux/m14-linux-043-启动初始化.md`（仅此一件；未改任何代码，Linux 源树只读未动）。

**验收结果**：
- 基线：Linux 源树 HEAD `c5f411a3a`（`7b20d05fd` 7.2.10＋dadao 补丁态），`status --porcelain -uall` **0** 项；全程未 `apply_series`/`reset`/`make`、未跑仿真。
- 结论：**19 条**（①6 ②6 ③4 ④3；P0/P1/P2 = **0/6/13**），`盘点结论` 段 **34 行**（≤80）；每条 `↔` 与 ≥2 个两侧 refs 由脚本校验。
- 覆盖现场派生：arch 插入点 **15**、dadao 注入 `init/main.c` **8**、riscv `select` **276 行/271 去重**、boot 相关 select **5 行/4 符号**、`arch/dadao/Kconfig` **15** config、`Kconfig.debug` **20** config；文档声明值与现场复算值逐项相等（`claim.coverage_numbers`）。
- refs 真实性：**115** 个 `文件:行号` 全部可解析（文件存在＋行号在范围＋该行非空），`bad=0`、`empty=0`。
- 抽查 7 条（脚本内 `sed -n '<行>p'` 两侧原文实跑）：①`arch/dadao/kernel/head.S:44` = `set.rb rb1, early_stack_top` ↔ `arch/riscv/kernel/head.S:287` = `addi sp, sp, -PT_SIZE_ON_STACK`；②`arch/dadao/kernel/setup.c:225` = `memblock_reserve((unsigned long)__pa(_start),` ↔ `arch/riscv/mm/init.c:291` = `reserve_initrd_mem();`；③`init/main.c:1192` = `dadao_k4_boundary();` ↔ `init/main.c:1195` = `rest_init();`；④`arch/dadao/Kconfig:94` = `config CMDLINE` ↔ `arch/riscv/Kconfig:1226` = `config CMDLINE_FALLBACK`（旁证 `drivers/of/fdt.c:1133` = `#ifdef CONFIG_CMDLINE`）；⑤`arch/dadao/kernel/setup.c:123` = `(unsigned long)boot_info.initramfs_base,` ↔ `contract-linux-boot.md:73`（`INITRAMFS-BASE` 行）；⑥`arch/dadao/mm/init.c:52` = `init_mm.pgd = swapper_pg_dir;` ↔ `arch/riscv/mm/init.c:1352` = `setup_bootmem();`；⑦`arch/dadao/kernel/setup.c:421` = `void __init trap_init(void)` ↔ `arch/riscv/kernel/head.S:303` = `call .Lsetup_trap_vector`。
- 注入 3 路（scratch 副本，原任务书 md5 前后一致）：ref 行号漂移→`refs.bad` FAIL；删一条结论→条数 FAIL；删一个 `↔`→arrow FAIL；三者 rc=1，未注入副本回绿。
- 改动集：`git show --name-only HEAD` = **4** 个文件（`.tao/knowledge/milestones-m14.md` ＋ 041/042/043 三本任务书，**不含代码目录**）；`git status --porcelain -uall` = **1** 项（本任务书）。

**新发现/坑**：
- `arch/dadao/kernel/init.c` **不存在**（实际启动 C 全在 `setup.c`＋`early_console.c`）；`arch/dadao/lib/` 无清零/字符串实现，字符串走通用 `lib/string.o`。
- 早期 `current` 为 NULL 是最尖锐的潜伏点：SP 先落在 16 KiB `.bss` 早期栈，跑完 `dadao_start_kernel` 的 C 才切 `init_stack` ⇒ 切栈前任何 `printk`/`kmalloc`/`might_sleep` 都空指针。
- `dadao_k4_boundary()` 让 defconfig 镜像结构性停在 `rest_init()` 之前；能走到 `/init` 的镜像必须带一个 probe——读 K6 现象前先看 `.config`，否则会误判「内核不会调度」。
- 契约 §2「启动保留区与 initramfs 区须保留」完全没落实（`memblock_reserve` 只保镜像）；`initramfs_base/size` 只有打印、无消费者。
- 反例坑：把「改一条结论的标题」当注入不成立（条数/refs/arrow 都不变）；反例必须改变被断言的性质（删整行／坏行号／删 `↔`）。

**遗留问题**：19 条的整改去向（立即修／立任务／暂不修）由用户裁定；本任务只出结论，未改代码、未占写者锁、未重建。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `arch/dadao/Kconfig.debug:11-394` 越界（文件 393 行） | ✅已修 | 改 `:11-393` | `refs.bad` 由 1 转 0（脚本实跑） |
| `arch/dadao/Kconfig:9-27` 的 `:27` 是空行 | ✅已修 | 改 `:9-26` | `refs.empty_content` 由 1 转 0 |
| ③-4 拆分数算错（写「4 个 `*_STOP`／6 个 K2 子项」） | ✅已修 | 改为按里程碑 K1 1／K2 9／K3 2／K4 5／K5 3，`grep -c "^config "` = 20 对账 | `cov.dadao_Kconfig_debug` = 20 且与文档声明相等 |
| `CONFIG_ARCH_SEMIHOSTING_CONSOLE` 条只有 dadao 侧、缺 `↔` | ✅已修 | 补 `drivers/tty/serial/earlycon-riscv-sbi.c:52`（`EARLYCON_DECLARE`）作上游对照 | `doc.bullets_without_arrow` 由 1 转 0 |
| 「`current == NULL`」表述与布局强绑定 | ✅已修 | 改为「不是 `&init_task`（本布局下 64 KiB 块基址落在 `.bss` 全零区，实测 NULL）」 | 重读 `head.S:44`＋`thread_info.h:43`＋`.bss` 清零段 |
| `arch/dadao/include/asm/string.h:5` 指向注释框首行 | ✅已修 | 改 `:6`（「K0 uses the generic C string routines」） | `sed -n 6p` 原文核对 |
| git 断言写死「HEAD 只含本任务书」（实际 HEAD 是批次提交，含台账＋3 本任务书） | ✅已修 | 改为「HEAD 只含 `.tao/tasks/` 与 `.tao/knowledge/`，且无代码目录」 | `git show --name-only HEAD` 4 文件、`head_no_code_files` = 0 |
| 注入 `drop-one-bullet` 只改标题、未被检出（假绿风险） | ✅已修 | 改为删整行（`CONFIG_ARCH_SEMIHOSTING_CONSOLE` 条） | 注入 rc=1，`inject.drop-one-bullet` PASS |
| 覆盖段缺「内存探测」与「K4 ↔ mm_core_init 时序」两处口径 | ✅已修 | ③-1 补单块 `memblock_add` 与 riscv `early_init_dt_scan`/`memblock_cap_memory_range` 对照；②-3 补 `mm_core_init_early`→`mm_core_init`→钩子→`rest_init` 的时序链 | 重读 `init/main.c:1005/1044/1192/1195`；`refs` 全解析 |
| initramfs 区 PA 写成 `[0x40_0000, 0x60_0000)`（差 4 位，实为 64 MiB 起） | ✅已修 | 改 `[0x400_0000, 0x600_0000)`（VA `0x0200_0400_0000` − `PAGE_OFFSET`） | 手算 0x0200_0400_0000−0x0200_0000_0000 = 0x400_0000；契约 §2 行 38 对账 |
| 命令串写成 `grep -rn CONFIG_ARCH_SEMIHOSTING_CONSOLE`（Kconfig 定义行无 `CONFIG_` 前缀，只有 1 命中） | ✅已修 | 改为 `grep -rn ARCH_SEMIHOSTING_CONSOLE` | 实跑 2 命中（`arch/dadao/Kconfig:80`、`arch/dadao/configs/defconfig:10`） |
| `arch/dadao/include/asm/fixmap.h:9` 指向 `enum` 行而非 `FIX_NONE` | ✅已修 | 改 `:10` | `sed -n 10p` = `FIX_NONE,` |

判决：全部 finding 已修，无未修项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收

- **重跑（我独立执行，不采信转述）**：运行期证据目录内的 `run.sh` ⇒ `RESULT: OK=42 FAIL=0`、`RESULT: PASS (0 failures)`、**退出码 0**；关键行 `refs.bad 0/0 rc=0`、`refs.resolved act=115`、`doc.items.total 19/19`、`doc.P1 6/6`、`doc.P2 13/13`、`claim.coverage_numbers exp=15 8 276 271 5 4 15 20` 与 act 相等、三路内置注入均 `rc=1` 被抓。
- **独立注入 1 路（改被测产物、同一脚本）**：结论段 `init/main.c:1192` → `:1992` ⇒ `RESULT: OK=41 FAIL=1`、`FAILED: refs.bad`、`BAD: init/main.c:1992(range 1774)`、**退出码 1**；`cp` 备份 + md5 复原（`3a1ef334…` 与注入前脚本记录值相等）⇒ 回绿 `OK=42`、**退出码 0**。
- **过程事故（如实登记，已在本轮闭合）**：备份误在主工作树取 `cp`，还原时把 45 行 master 版盖进任务书 ⇒ 以 `git show HEAD:<任务书> | md5sum` **先核**得 `3a1ef334…`（与注入前记录值逐字相等，且注入前 `git status -uall` 为 0 行、无未提交改动会被清）后 `cp` 复原 ⇒ `wc -l`=130、`git status --porcelain -uall` 0 行、`git diff --stat HEAD` 空、复跑 42/42 退出码 0。
- **抽查（我自己的 `sed -n '<行>p'`，两侧原文，≥8 条、P1/P2 各 ≥3，全部对上）**：
  - [P1] `arch/dadao/kernel/head.S:44` = `set.rb rb1, early_stack_top` ↔ `arch/riscv/kernel/head.S:286/287` = `la sp, init_thread_union + THREAD_SIZE` ／ `addi sp, sp, -PT_SIZE_ON_STACK`
  - [P1] `arch/dadao/kernel/setup.c:176` = `dadao_jump_on_stack((char *)init_stack + THREAD_SIZE -`（此时才切栈）；`setup.c:225` = `memblock_reserve((unsigned long)__pa(_start),` ↔ `arch/riscv/mm/init.c:291` = `reserve_initrd_mem();`、`:298` = `early_init_fdt_scan_reserved_mem();`
  - [P1] `contract-linux-boot.md:42` = 「启动保留区 … 与 initramfs 区 … **须保留**」；`:74` = `INITRAMFS-LIMIT` ≤32 MiB；`init/main.c:1192` = `dadao_k4_boundary();` ↔ `:1195` = `rest_init();`
  - [P1] `arch/dadao/Kconfig:94` = `config CMDLINE` ↔ `arch/riscv/Kconfig:1207/1218/1226` = `config CMDLINE`／`choice`／`config CMDLINE_FALLBACK`；`drivers/of/fdt.c:1133` = `#ifdef CONFIG_CMDLINE`
  - [P2] `arch/dadao/include/asm/fixmap.h:10` = `FIX_NONE,` ↔ `arch/riscv/Kconfig:111` = `select GENERIC_EARLY_IOREMAP`；`init/main.c:1562` = `void __weak free_initmem(void)` ↔ `arch/riscv/kernel/setup.c:374` = `void free_initmem(void)`
  - [P2] `arch/dadao/kernel/setup.c:421` = `void __init trap_init(void)`、`:431-437` 注释（weak+inline 使调用消失）逐行在位 ↔ `arch/riscv/kernel/head.S:303` = `call .Lsetup_trap_vector`；`mm/memblock.c:2141` = `void __init memblock_allow_resize(void)`（`:2143` 置 1，`arch/dadao/` 全 arch 0 命中）
- **四条关键 P1 查实**：
  ① **早期 `current` 为 NULL 成立**：`head.S:141-147` `.bss` 内 `early_stack` + `.zero 16384`；`System.map`（运行期构建产物，路径不入册）现场核算 `early_stack=0x0200_005f_0080`、`early_stack_top=…_4080`、`__bss_start=0x0200_005f_0000`、`init_task=0x0200_0052_2600` ⇒ `sp&~0xFFFF = 0x0200_005f_0000 = __bss_start` 落在 `head.S:56-66` 已清零的 `.bss` 内 ⇒ 切栈前 `current`（`current.h:13`＋`thread_info.h:43`）实为 NULL 且 ≠`&init_task`；`setup.c:176` 才切 `init_stack`；riscv 进 C 前已设 `sp`（上 ① 行核）。
  ② **保留区未 `memblock_reserve` 成立**：`grep -rn memblock_reserve arch/dadao/` 仅 `setup.c:225` 一处；契约 `:41/:42` 要求保留 `[0x0200_0000_0000,0x0200_0002_0000)`（=PA `[0,0x2_0000)`）与 initramfs 区，`:94` `ram_base=0x0200_0000_0000` 经 `setup.c:107` `__pa` ⇒ `memblock_add(0,…)`、`setup.c:235-237` `max_pfn` 覆盖全程、`mm/mm_init.c:2744` `memblock_free_all();` ⇒ PA `[0,0x2_0000)` 与 `[0x400_0000,0x600_0000)` 确会进 buddy。
  ③ **走不到 `rest_init()` 成立，且 023/024/025 都带 probe**：`init/main.c:1192` → `setup.c:284` `dadao_k4_boundary()`，五个 probe 分支（`grep -n '^\s*return;'` 现场 = 326/335/344/353/362）之外落到 `setup.c:367` `dadao_early_exit(0)`；defconfig 无任何 `CONFIG_DADAO_*SELFTEST`（grep 0 命中）、`Kconfig.debug` 各项 `default n` ⇒ defconfig 镜像必停 K4；三本跑通 `/init` 的镜像分别钉 `CONFIG_DADAO_K5_SYSCALL_SELFTEST=y`（`k5_syscall_probe.py:91`）、`_CLONE_=y`（`k5_clone_probe.py:103`）、`_FUTEX_=y`（`k5_futex_probe.py:115`）⇒ K5 确是靠 probe 撑起、判定权在 probe。
  ④ **`CMDLINE` 无消费者成立**：`arch/dadao/configs/defconfig:38` = `CONFIG_OF=n`；`grep -rn boot_command_line arch/dadao/` 仅 `setup.c:240`（读）；通用消费者仅 `drivers/of/fdt.c:1133`（依赖 OF），其余命中在它 arch 或 `_BOOL/_OVERRIDE/_PARTITION` 变体。
- **覆盖数抽验（我自己重跑 grep，非采信）**：`hooks=15`、`grep -c dadao init/main.c=8`、`arch/dadao/Kconfig=15`、`Kconfig.debug=20`（K1 1／K2 9／K3 2／K4 5／K5 3、`_STOP=3`）、riscv `select=276/271`、boot 相关 `5 行/4 符号` ⇒ 与文档声明逐项相等。
- **约束核验**：不改代码 ✓（`git diff --name-only master...HEAD` = 仅本任务书、代码目录 0 命中；工作树 `git status --porcelain -uall` 0 行；Linux 源树 `c5f411a3a`、`status -uall` 0 行、全程只读）；门控 `make check-knowledge-refs` rc=0、`make check-tasks` rc=0（两道均在**本记录写入后**重跑）；结论段 34 行 ≤80；术语合规（bank 一律作「寄存器组」，本记录无误译）；本记录无运行期路径；未提交 git。
- **非阻断 finding（文档级，交 architect 收尾改）**：① `head.S:144` 指栈标号、`.zero 16384` 实在 145；② `memblock.c:2141` 是 `memblock_allow_resize()` 函数头（赋值 2143、声明 172）；③ `early_console.c:68` 是 `dadao_early_write` 函数头（`SYS_WRITEC` 在 71）；④ 完成区「HEAD 4 文件／工作树 1 项」因 architect 分次提交变为 1 文件／0 项（时序差、非造假）。
- **判决：Accepted** —— 验收命令块在我自己的重跑下全部通过（证据脚本 42/42 退出码 0、两道门控退出码 0）、四条关键 P1 逐条查实、≥8 条抽查两侧原文全对、覆盖数现场重算一致、独立注入 FAIL→还原→回绿真实、不改代码约束守住。
