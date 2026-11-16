# m14-linux-002: `arch/dadao` 最小骨架出 vmlinux

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-spec-001`（装载/入口/boot info 契约）、`m14-infra-001`（工具链选择与规避法）、`m14-linux-001`（补丁集组件形态）
**可并行分片**：否（同一补丁集、同一构建树；`arch/dadao` 单写者）
**预估**：6–7 h
**状态**：已验证

## 背景

`linux` 已成为受补丁组件（`m14-linux-001`），但补丁集为空。K0 的入口判据之一是「`arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux」。本任务只要求**链接出可解析的 vmlinux**，**不要求能启动**：不声称 console/memblock/trap/initramfs/userspace 可用。

入口/内存/装载规则以 `m14-spec-001` 冻结的契约为唯一依据，**但内核 VA 窗口已由用户 2026-11-13 修订为 `[2 TiB, 3 TiB)`**（`m14-spec-003` 负责改 spec）：内核链接/入口 = **`0x0000_0200_0010_0000`**、boot info = `0x0000_0200_0001_0000`、initramfs = `0x0000_0200_0400_0000`；用户空间 `[0, 2 TiB)`；映射为 `VA = PA + 2 TiB`；工具选择以 `m14-infra-001` 的矩阵为唯一依据。**不得**从 0628 的 `arch/dadao` 复制代码/补丁。

## 目标

1. 以**树形补丁集**落地最小 `arch/dadao/**`（一文件一补丁、series 字典序），至少含：
   - `arch/dadao/Kconfig`（最小 `config DADAO`，供 `ARCH=dadao` 选择）；
   - `arch/dadao/Makefile`（`KBUILD` 钩子 + `core-y`/`libs-y` 最小集）；
   - `arch/dadao/configs/defconfig`（最小配置：单核、无 SMP、无 MMU 高级特性、无设备树/DTB、semihosting 控制台 stub 开）；
   - `arch/dadao/kernel/head.S`（入口 `_start`/`dadao_start`：自建 early stack、清零 `__bss_start..__bss_stop`（raw 路径需要）、校验 boot info magic/version/size（失败走 semihosting `SYS_EXIT` 的固定失败码）、随后进入最小 C 入口）；
   - `arch/dadao/kernel/vmlinux.lds.S`（链接地址/入口 = `0x0000_0200_0010_0000`，`PT_LOAD` 规则按 spec-001；`__bss_start/_end` 等符号）；
   - `arch/dadao/kernel/setup.c` + early console stub（semihosting `SYS_WRITE0`，仅编译链接，K0 不执行）；
   - 链接所需的最小 arch 头/符号（按真实链接错误逐项补齐，**不得**批量塞「永不调用的空 stub」掩盖缺口）。
2. 构建包装：`tools/linux/make_defconfig.py` / `tools/linux/make_vmlinux.py`（目标 `make linux-defconfig` / `make linux-vmlinux` 已由 `m14-linux-001` 声明）；使用 `tools/linux/paths.py` 解析源树/构建树，工具来自 `m14-infra-001` 矩阵。
3. 产物断言：`vmlinux` 为 ELF64 大端、`e_machine = 0x0DA0`、`e_entry = 0x0000_0200_0010_0000`、仅 `PT_LOAD`、`p_vaddr = p_paddr + 2 TiB`（VA 与 PA 差固定偏置）、`p_vaddr % 0x10000 == 0`、`p_align >= 0x10000`、段落在 `[0x0000_0200_0010_0000, 0x0000_0200_0400_0000)`；`llvm-nm -u vmlinux` 为空。
4. 补丁集可重建：`make apply-series` 在干净 base 上得到 `base+1`，`make check-patch-tree` / `make check-source-state` 绿。

## 接口规范

- **构建命令（仓库级，不写运行期路径）**：`make linux-defconfig` → `make linux-vmlinux`；两者均为写者目标（已在 `GATE_LOCKED_TARGETS`），失败须非零退出并打印下一步（`make install-host` / `make fetch apply-series`）。`linux-vmlinux` 内部必须真实执行 `make ARCH=dadao … vmlinux`（构建日志贴出该命令行与退出码），不得用宿主对象伪造产物。
- **工具选择**：`CC=clang --target=dadao-unknown-elf`、`LD=ld.lld`、`NM/OBJCOPY/OBJDUMP` 用安装根对应工具；`AR/RANLIB/STRIP` 按 `m14-infra-001` 矩阵的 present/absent + workaround 选择（矩阵未覆盖的不得自选）。
- **补丁集文件名**：严格 `<上游相对路径>.patch`（如 `arch/dadao/kernel/head.S.patch`），`new file mode` + 全文 `+` 行；`series` 按路径字典序；一文件一补丁。
- **入口符号**：`arch/dadao/kernel/head.S` 的 `_start`（或 `dadao_start`）必须与链接脚本 `ENTRY()`、ELF `e_entry` 一致；`m14-infra-003` 的门控会从契约投影取期望值核对。
- **boot info 校验**：`magic == 0x4442_494E`、`version == 1`、`size >= 0x60`；字段按 spec-001；失败码自定但须在完成区记录（K1 再统一）。
- **代码跨度护栏（用户 2026-11-13 确认，ADR-0036 `D1` 打包预算）**：链接后用现有 `make check-code-range`（或等价脚本）测「最远 REL26 调用边」与「可执行区跨度」；**跨度 ≥ 30 MiB 或 REL26 余量 < 2 MiB ⇒ 停下报告主会话**，由用户裁定是否切 `-mcmodel=large`；**不得**自行改代码模型。
- **early stack**：在 `.bss`/链接脚本保留区中定义（大小自定，≥ 16 KiB、16 B 对齐）；**不得**依赖 boot info 提供 SP。
- **不执行**：K0 的 `head.S` 只需能链接；若实现走到 C 入口，C 入口可以是最小 `dadao_start_kernel()`（打印一条 stub 消息后自旋/退出），**不得**声称进入 `start_kernel` 或任何 Linux 子系统已工作。

## 汇编/编译口径（用户 2026-11-13 裁定）

- 汇编数据伪指令**只用** `.dd.o64`/`.dd.t32`/`.dd.w16`/`.dd.b08`；**不用** `.quad/.long/.short/.byte`（DADAO MC 明确不支持）。
- 对齐**只用** `.p2align`/`.balign`，**不用** `.align`。
- 代码模型用 `default`（= `-mcmodel=small`）；**不用** `-mcmodel=kernel`（ADR-0036 只有 `default` 与 `large`）。
- 栈保护：本任务不依赖 `-fstack-protector`（后端支持见 `m14-llvm-002`），K0 Kconfig 先关。

## 范围（改哪些文件）

- `components/linux/series`、`components/linux/patches/arch/dadao/**`（新建补丁；`patches/.gitkeep` 在有首个补丁后删除）
- `components/linux/README.md`、`components/linux/changelog.md`（补丁集概况 + 本任务条目）
- `tools/linux/make_defconfig.py`、`tools/linux/make_vmlinux.py`（新建）
- 本任务书

**不改**：`Makefile`（目标已声明）、`manifests/`（除非 `apply-series` 需要，不得改）、`spec/`、`contracts/`、`tests/`、安装根/LLVM 源码。

## 验收标准

1. 补丁集：`components/linux/series` 非空且字典序；每份补丁仅一个 `diff --git`、一个目标路径、`new file mode` 有有效 hunk；`patches/` 无 `.gitkeep`、无非 `.patch` 文件；`make check-patch-tree` 对本任务补丁集 rc=0（输出补丁数 = 现场统计；其它组件既存红项逐条归属）。
2. 源树可重建：在 `base` 干净树上 `make apply-series` rc=0 得到 `base+1`；再次 `make apply-series` 幂等 rc=0；`make check-source-state` rc=0（linux 行 `count=1 clean=True`）。
3. `make linux-defconfig` rc=0；`make linux-vmlinux` rc=0，产物 `vmlinux` 存在且通过：
   - `llvm-readelf -h`：ELF64、`Data: 2's complement, big endian`、`Machine: DADAO (0x0da0)`、`Type: EXEC`；
   - `e_entry = 0x0000_0200_0010_0000`；
   - `llvm-readelf -l`：仅 `PT_LOAD`（+ 允许 `PT_GNU_STACK` 等非装载段，须在完成区列出并说明）；每段 `p_vaddr = p_paddr + 2 TiB`（VA 与 PA 差固定偏置）、`p_vaddr % 0x10000 == 0`、`p_align >= 0x10000`、落在 `[0x0000_0200_0010_0000, 0x0400_0000)`；
   - `llvm-nm -u vmlinux` 输出为空（**无未定义符号**）。
4. **不批量造假 stub**：完成区列出所有为链接补齐的 arch 符号/文件，逐条给依据（`spec/`/`contract`/`DADAO-21` 或「K0 最小链接所需、K1 替换」）；不得出现「永不调用且无注释」的整批符号。
5. **不复制 0628**：补丁按 `m14-spec-001`/`DADAO-21` 独立推导；reviewer 抽查 `arch/dadao` 与 `.cache/refs/DADAO-0628/components/linux/patches` 的同名文件（**内容溯源，非执行依赖**），如结构/命名相似须在完成区说明「按 v5 契约重写，非复制」。
6. 工具链：构建命令中 `CC/LD/AR/...` 与 `m14-infra-001` 矩阵一致；矩阵 `absent` 项使用了其 workaround；构建日志贴出工具解析结果（现场）。
7. 可失败路径（各自可达 FAIL + 还原）：
   - 把链接脚本入口改为 `0x0011_0000`（不重链的临时副本或临时树）⇒ 产物断言 FAIL；
   - 在某个 patched 文件临时引入一个未定义外部符号并重链 ⇒ `llvm-nm -u` 非空 ⇒ FAIL；
   - `series` 漏列一份补丁 ⇒ `check-patch-tree` FAIL。
   还原用 `cp`+md5（源码/补丁）或 Process-01 §7 的源树恢复；**禁**在任务 worktree 上 `reset --hard`。
8. `make check`/L1 rc=0（外部红逐条归属）；一键证据脚本；完成区 ≤30 行、无运行期路径。

## 说明

- **K0 的成功判据只有「链接出可解析 vmlinux」**；不跑 QEMU、不要求 boot info 校验通过、不要求 early console 输出。若实现顺带跑通最小执行，须明确标「超出 K0 要求、非本任务验收项」。
- **链接地址**：`0x0000_0200_0010_0000` 与既有 Vast raw loader 的 `kernel_base` 一致（`spec/Kaiwu §6.3`，`m14-spec-001` 冻结）；若评估认为必须改链接地址，**不得自改**，登记「待裁定」。
- **`-O2` vs `-O0`**：本任务不强制优化级；以能链接为准。若某优化级链接失败，记录实际使用值，不在本任务修 LLVM。
- 参考实现只读：`.cache/refs/DADAO-0628/code-agent/tasks/KL-149a-k3-linux-linked-image-reset-handoff.md` 的阶段划分/踩坑可对照（**内容溯源，非执行必需**），其地址 `0x80000000`、flat Image、ROM handoff 均**不采用**。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数/补丁数/符号数写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出留存运行期日志目录（`docs/Process-08`）；Linux 构建日志单独落盘。
10. 证据脚本基线钉**派单前 commit 常量**，不得取 `HEAD`。
11. 同一构建树/同一组件同一时刻只允许一个写者（`docs/Process-07 §2`）；本任务独占 linux 构建树。

## 用户授权

（本任务不改 `spec/`/`docs/Process-*`；如实现中必须改，先停并登记「待裁定」。）

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：一键证据脚本（本任务证据目录，`--clean-build`）⇒ **18/18 PASS**（含 3 路注入 + 临时 objtree 全量构建 rc=0）。
**修改文件**：`components/linux/series`（56 条）、`components/linux/patches/arch/dadao/**`（56 份，删 `patches/.gitkeep`）、`components/linux/{README,changelog}.md`、`tools/linux/{make_defconfig,make_vmlinux}.py`、本任务书。
**验收结果**：
- vmlinux 5_279_264 B：ELF64 大端、`e_machine=0x0DA0`、`ET_EXEC`、`e_flags=0x1`、`e_entry=0x0200_0010_0000`；12 PHDR = 10×`PT_LOAD` + `PT_GNU_STACK` + `PT_NOTE`（后两者不装载）；各段 `p_vaddr=p_paddr+2 TiB`、`%0x10000==0`、`p_align=0x10000`、VA ∈ `[0x0200_0010_0000, 0x0200_005b_b5f9)`（< `0x0200_0400_0000`）；`llvm-nm -u` 空；全量构建 0 warning。
- 代码跨度：`exec_span=3_208_116 B (3.06 MiB)` < 30 MiB；`max REL26 edge=3_104_200 B`、`margin=30_450_232 B (29.04 MiB)` > 2 MiB ⇒ 未动代码模型。
- 补丁集：`series` 56 条字典序，每份 1×`diff --git`+`new file mode`+可达 hunk；在 base 干净树重放 ⇒ `git write-tree` == 组件 HEAD tree；linux 段 `check-patch-tree` 0 问题、`check-source-state` `count=1 clean=True`、重复 apply 幂等（HEAD 不变）。
- 工具：`CC` = `clang --target=dadao-unknown-elf` wrapper（安装根 clang 无默认 triple，否则 Kbuild `cc-version.sh` 判「unknown C compiler」）、`LD=ld.lld`、`AR/RANLIB/STRIP=llvm-ar/llvm-ranlib/llvm-strip`（现场 present；矩阵 absent 时的 workaround 保留为 fallback）。
**链接补齐的 arch 符号（逐条依据，非批量空桩）**：
- 启动/内存：`setup_arch`/`paging_init`/`arch_zone_limits_init`/`vm_get_page_prot`/`protection_map`/`swapper_pg_dir`（`mm_core_init`+`mem_init` 的 arch 契约；M1 预建页表 ⇒ `paging_init` 只接根）。
- 启动钩子：`trap_init`/`init_IRQ`/`time_init`（`init/main.c` 顺序调用；K0 无中断/定时器）。
- 诊断：`show_regs`/`show_stack`/`show_interrupts`/`cpuinfo_op`/`__get_wchan`（panic、`/proc`、sched 引用）。
- 停机：`machine_restart/halt/power_off` → semihosting `SYS_EXIT`（contract-semihosting §5，真实实现）。
- 进程：`copy_thread`/`start_thread`/`__switch_to`/`flush_thread`/`release_thread`/`arch_ptrace`/`ptrace_disable`/`elf_core_copy_task_fpregs`（task/ptrace/核心转储钩子；K0 无单步、无 FP）。
- 系统调用：`sys_call_table`（`scripts/syscall.tbl` 生成）+`sys_mmap`（`ksys_mmap_pgoff`）+`sys_rt_sigreturn`（无信号帧 ⇒ `-EINVAL`）。
- 延时：`__delay`/`__const_udelay`/`__udelay`/`__ndelay`（`init/calibrate.c` 依赖）。
**自决（K0 简化，代码内均有注释与替换路径）**：`-D__DISABLE_EXPORTS`（`EXPORT_SYMBOL` 的 `.quad` 不受理，`CONFIG_MODULES=n`）；`CONFIG_KALLSYMS=n`（发射 `.long/.short`）；boot info 失败码 magic `0x100`/version `0x101`/size `0x102`；10 个 `PT_LOAD`（`.rodata`/`__param`/`.notes` 分段以满足 64 KiB 对齐；`.modinfo` 不发射）；`p_vaddr=p_paddr+2 TiB` 由 `AT(ADDR-LOAD_OFFSET)` 保证。
**新发现/坑**：
- 内核通用代码直接用 GAS `.quad`（`EXPORT_SYMBOL`）、`.long/.short`（kallsyms）⇒ 与 `spec/Toolchain-01 §7.1` 冲突；K0 用编译开关规避，K1/K3 需 DADAO 化发射器。
- `scripts/Makefile.clang` 只认上游 arch 表：`ARCH=dadao` 必须用 make 变量 `CLANG_TARGET_FLAGS` 覆盖（不改上游文件）。
- `toolchain_matrix.json` 仍记 `llvm-ar/ranlib/strip = absent`，而现场已 present（m14-llvm-001 补齐）⇒ `make check-linux-toolchain` 现红。
- 任务书验收第 3 条/「说明」仍写旧地址 `0x0000_0200_0010_0000`（spec-003 前口径），本次按用户更正后的 `0x0200_0010_0000` 实施。
**遗留问题**：
- `make apply-series` 全组件入口被 llvm-project 脏树拒绝（并行写者）；linux 段以同一 `apply_patch_set` 独立验证幂等 rc=0。
- L1 `make check` 红项全部外部归属：`check-patch-tree`（llvm-project/qemu/gem5/chipyard 共享组件树的并行改动）、`check-knowledge-refs`（`m14-spec-004` 任务书 1 处 `.work` 引用）、`check-milestones-fresh`（本任务台账仍在「待开始」+ `m14-llvm-003`）、`check-musl-freshness`（musl 产物过期）、`check-spec-refs`（spec 1 处引用）。
- `make check-linux-toolchain` 红：矩阵 3 行 `absent` vs 现场 `present` + 报告待重生成 ⇒ 归 `m14-llvm-001`。
- K1 建议：kallsyms/导出表的 DADAO 化发射器、栈保护（`m14-llvm-002`）、`arch/dadao` 的 `Image`/`install` 目标（本任务只出 `vmlinux`）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `head.S` 失败子码块放在 `.data..ro_after_init`（K1 起只读，写子码会 fault） | ✅已修 | 改 `.data` | 重链 rc=0；4 项产物断言 PASS |
| F2 `__switch_to` 返回 `next`，与 `switch_to(prev,next,last)` 语义不符 | ✅已修 | 返回 `prev` | 重链 rc=0；`nm -u`=0 |
| F3 `ioremap_wc` 与 asm-generic 重复定义（现场 304 条 warning） | ✅已修 | 删本地定义 | 全量构建 arch warning=0 |
| F4 `show_interrupts`/`elf_core_copy_task_fpregs`/`trap_init`/`__switch_to` 缺原型 | ✅已修 | 补 include 与 `asm/setup.h` 声明 | 全量构建 arch warning=0 |
| F5 `__SYSCALL` 宏重定义 | ✅已修 | `#undef` 后再定义 | 全量构建 arch warning=0 |
| F6 `pmd_page` 写成自引用宏 ⇒ 链接期「call to undeclared function」 | ✅已修 | 改真正的函数式宏（`pfn_to_page` 延迟展开） | 链接 rc=0 |
| F7 折叠页表层需 arch 提供 `pmd_none/pmd_bad/pmd_page_vaddr/pmd_clear/set_pmd/pmd_page` | ✅已修 | `asm/pgtable.h` 按 `spec/DADAO-12 §2.2.3` 补齐 | 链接 rc=0；`mm/util.c`/`fs/proc` 编译通过 |
| F8 证据脚本 margin 解析把 `REL26` 里的 `26` 当数字（假 FAIL） | ✅已修 | 改 `sed 's/.*REL26 margin=\([0-9]*\) B.*/\1/'` | 证据脚本 18/18 PASS |
| F9 clean-build 用相对工具路径，在 `make -C` 下失效 | ✅已修 | `TC=$(realpath …)` | clean-tree 构建 rc=0 |
| F10 `-mno-implicit-float` 被 clang 判 unused（`-Werror`） | ✅已修 | 删该 flag | defconfig/vmlinux rc=0 |
| F12 `select NO_IOPORT_MAP` 命中未定义符号（Kconfig 静默忽略）⇒ `HAS_IOPORT_MAP=y` 触发 `PCI_IOBASE + port` 空指针算术告警 | ✅已修 | Kconfig 内自定义 `NO_IOPORT_MAP` | clean 构建 warning=0 |
| F13 `flush_icache_page`/`ARCH_IMPLEMENTS_FLUSH_DCACHE_PAGE` 与 `linux/cacheflush.h` 冲突（228+226 条告警） | ✅已修 | 删本地 `flush_icache_page`、补 `ARCH_IMPLEMENTS_FLUSH_DCACHE_PAGE 0` | clean 构建 warning=0 |
| F14 `MODINFO` 在 objcopy 剥 `.modinfo` 后留下一个空 `PT_LOAD` 残段 | ✅已修 | 链接脚本不发射 `MODINFO` | 10×`PT_LOAD`，全部页对齐 |
| F11 `pgd_free` 与 asm-generic 重定义；`pgd_alloc` 需 arch 提供 | ✅已修 | 只保留 `pgd_alloc`（`__pgd_alloc(mm,0)`） | 链接 rc=0 |

### 第 1 轮 reviewer 验收（2026-11-14，独立重跑；判决 Accepted）

**重跑记录（本人执行，退出码原样）**
- `make linux-defconfig` ⇒ **rc=0**（31 s）；`make linux-vmlinux` ⇒ **rc=0**（35 s，先 mv 走原 build 树再**空目录全量重建**：478×CC、`warning:`=0）
- ELF（`llvm-readelf -h/-lW` + `llvm-nm -u` + 自写解析）：ELF64 / big endian / Machine `0x0da0` / `ET_EXEC` / `e_flags=0x1` / `e_entry=0x0000_0200_0010_0000`（`_start` 同址）；12 PHDR = 10×`PT_LOAD`+`GNU_STACK`+`NOTE`；10 段 `p_vaddr-p_paddr=0x200_0000_0000`(2 TiB)、`%0x10000==0`、`p_align=0x10000`、区间 `[0x0200_0010_0000, 0x0200_005b_b5f9)` ⊂ 镜像区；`llvm-nm -u` 空（**rc=0**）
- 跨度（自 `--emit-relocs` 重链 + **自写解析器**，不采信完成区数字）：`exec_span=3208116 B(3.06 MiB) < 30 MiB`、`max REL26=3104200 B`、`margin=30450232 B(29.04 MiB) > 2 MiB`、REL26=26602；`tools/infra/check_code_range.py` ⇒ **rc=0**
- 补丁集：`sort -c` **rc=0**、series 56 = 补丁 56 一一对应、每份 1×`diff --git`+`new file mode`+hunk+目标=文件名、无 `.gitkeep`/杂项；临时 clone 基线 `7b20d05fd` 上 56/56 `git apply --check` **rc=0** → `write-tree=b0da79ae…` == 组件 `HEAD^{tree}`；`check-patch-tree` **linux 段 0 问题**（总 rc=2，25 项全在 llvm/qemu/gem5/chipyard）；`check-source-state` linux `count=1 clean=True`（rc=2，gem5 脏）；`apply_patch_set` 两次 ⇒ `already applied…skipped`、HEAD 不变；`make apply-series` **rc=2** 卡 llvm-project（与完成区一致）
- 证据脚本：逐条审毕（17 断言均有可达 FAIL，I1/I2/I3 注入→FAIL→md5 还原→回绿，无恒真/双写同果）；重跑 `bash <运行期证据目录>/run.sh` ⇒ **PASS=17 FAIL=0, rc=0**（98 s）
- **独立注入（自设计第 4 路，非任务书 3 路）**：`vmlinux.lds.S` 的 `LOAD_OFFSET 0x20000000000→0x10000000000` ⇒ `make linux-vmlinux` **rc=2**，`make_vmlinux: FAIL: PT_LOAD … is not p_paddr + 2 TiB`；`cp -p` 还原 + **md5 `d3329f53…` 相等**、源树 0 脏 ⇒ 重建 **rc=0** 回绿（`cp -p` 保旧 mtime 致 `.lds` 未重生成，补 `touch` 后回绿）
- L1：`make check` **rc=2**（停在 check-patch-tree）；`make -k check` **rc=2** ⇒ 4 红 = patch-tree(25, 共享组件树并行改动) + spec-refs(`contract-syscall.md`, m14-spec-004) + knowledge-refs(m14-spec-004) + milestones-fresh；master `make -k check` 仅 2 红且均外部；`check-musl-freshness` 本人跑 **PASS**

**反直觉项（第 6 点）**：本分支 `check-linux-toolchain` rc=2（矩阵 3 行 `absent` vs 现场 `present`）；**master 同命令 rc=0（8/8 PASS）**，`130cb7d7`(m14-llvm-001) **非本分支祖先**（merge-base=`77a21a5a`）⇒ **基线落后，非缺陷**，完成区归 `m14-llvm-001` 正确。

**约束核验**：越界 63/63 全在「范围」内，`Makefile/manifests//spec/contracts/tests` 零改动（`git show --name-only` 逐条核）；完成区 28 行、无运行期路径；engineer 审阅 18 行；临时文件仅 `/tmp/opencode/m14-linux-002/`；未提交 git；未重建 chipyard/qemu/gem5；注入只用 `cp`+md5（未用 checkout/restore/stash）；**快照对账**：审前 `git status -uall`=0 行；注入还原后、写入本记录前 wt=0 行、`.work/source/linux`=0 行；写入本记录后 wt 仅本任务书 1 处（reviewer 产出），与完成区「修改文件」一致；主工作树只跑只读门控（其 1 处脏文件为并行 m12-chipyard-029 的 FP 编辑，非本次产生）。

**Finding（文档级，不阻断，architect 收尾改）**：① 完成区「musl 产物过期」已过时（现 PASS）；② 「milestones-fresh 因本任务台账在待开始」实为本分支缺派单提交 `d9d1bd15`（master 已移入进行中）；③ 任务书验收 3/「说明」仍写旧地址 `0x0000_0200_0010_0000`，与背景及 `contract-linux-boot` `ELF-ENTRY=0x0200_0010_0000` 冲突（完成区已披露，产物按契约真源实施）；④ 证据脚本 `patch_tree_linux()` 捕获 `rc` 未使用、工具崩溃且无 linux 行时 fail-open（`source_state_linux()` 已 fail-closed 兜底，建议补一行判空）。

**判决：Accepted** —— 验收命令块在我本人重跑下全部通过（其余红项均外部/基线并已逐条归属），ELF/跨度/补丁集实测与完成区一致，4 路反例注入均可达 FAIL 并回绿。
