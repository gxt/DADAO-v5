# m14-linux-036: mm/缺页/页表 与主流 ISA 差异盘点（只读盘点）

**模块**：linux
**项目里程碑**：M14
**依赖**：无（**只读分析**：不占 linux 写者锁，可与在跑任务并行）
**可并行分片**：是（盘点任务彼此独立、只读）
**预估**：2–3 h
**档位**：小改（只读 + 写结论；不改任何代码）
**状态**：待验收

## 背景（用户 2026-11-20 裁定）

> 「M14，尽量按主流 ISA 的标准流程走」
> 「M14 中增加专门的任务，或者多个任务，分子系统把已经实现的内核代码，逐个和主流 isa 的实现进行对比，找出差异」
> 「是否立刻整改，我来定」

## 范围（**只读**，不改代码）

对比对象：仓库 Linux 源树的 `arch/riscv`（主）与 `arch/arm64`（参照）。
本任务只覆盖：`arch/dadao/mm/**`（`fault.c`/`cow.c`/`mmu.c`/`init.c`/`pgtable-generic` 相关）、`include/asm/{pgtable,pgtable-*,pgalloc,tlbflush,mmu_context,cacheflush,page}.h`，以及 `arch/riscv/mm/**`、`arch/arm64/mm/**` 的对应实现。

## 要做

逐个 hook / 机制判定属于哪一类，并给证据：

1. **缺失 hook**：上游有、我们没有（后果：功能不可用，或被迫走旁路）；
2. **语义不符**：有但行为不同（返回码 / 副作用 / 加锁 / 顺序）；
3. **旁路 vs 通用**：我们自造实现，上游走通用 `mm/`、`kernel/` 路径；
4. **Kconfig 缺口**：缺 `select` / `depends on`，导致本可复用的通用代码没编进来（`m14-linux-025` 的 `CLONE_BACKWARDS` 就是此类）。

**每条格式**：`arch/dadao/<file>:<line>` ↔ `arch/riscv/<file>:<line>`（必要时补 `arch/arm64`）/ 影响面 / 优先级（**P0** 阻塞当前在跑任务；**P1** 影响正确性；**P2** 仅形态差异）。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行），**每条带两侧 `文件:行号`**；
2. **覆盖现场派生**：列清「检查了哪些 hook / 机制」及条数（不写死），并说明如何枚举得到（命令或脚本口径）；
3. **抽查 5 条**：用 `sed -n '<行>p'` 贴出两侧原文，证明行号真实——**不许凭记忆**；
4. **不改任何代码**：改动集只含本任务书——**提交后**以 `git show --name-only HEAD` 只含本任务书且 `git status -uall` 为空判定；**未提交态**下 status 只列本任务书（不依赖裸 `git diff`：提交后为空会假 FAIL）。不占写者锁、不重建、不跑仿真。

## 盘点结论

**基线**：linux 源树 `7b20d05fd`（7.2.10）＋`c5f411a3a`（dadao 补丁态）；下文 dadao 行号取自该补丁态，`arch/arm64/mm/**` 作参照。035 已报的 5 条（`arch_vma_access_permitted` 恒真、入口缺 `lock_mm_and_find_vma`＋`handle_mm_fault`、`pte_modify` 清 D、`flush_tlb_*` 丢 A/D、`NR_PAGETABLE` 下溢）不重复，只在其旁标「深化／同族」。共 25 条。

### ① 缺失 hook（7 条）

- **[P1] uaccess／内核态故障无修复出口**：`arch/dadao/include/asm/uaccess.h:10`（generic 访问器，无异常表）＋`arch/dadao/mm/fault.c:726-737`（无 vma 即判死）↔ `arch/riscv/mm/fault.c:93-99`（`no_context`→`fixup_exception`）、`arch/riscv/mm/extable.c:82`。越界用户指针（不在任何 VMA 内）⇒ 停机而非 `-EFAULT`，任一 syscall 都能触发。
- **[P1] 用户态故障无信号出口**：`arch/dadao/mm/fault.c:722-776` 各 verdict → 用户态路径 `arch/dadao/kernel/traps.c:378-382`（`dadao_early_exit`）、supv 路径 `arch/dadao/kernel/traps.c:521`（`dadao_die`）↔ `arch/riscv/mm/fault.c:143-157`（`bad_area_nosemaphore`→`do_trap(SIGSEGV)`）、`arch/riscv/mm/fault.c:117-141`（`mm_fault_error`→OOM/SIGBUS/SIGSEGV）。与 039 交叉，本条只记 fault 侧。
- **[P1] L2 表分配绕过 `pte_alloc()`**：`arch/dadao/mm/fault.c:506-514`、`arch/dadao/mm/mmu.c:206-212` ↔ 通用 `mm/memory.c:451`（riscv 无 arch 覆盖）。三面后果：无 `pagetable_pte_ctor`（035 的 `NR_PAGETABLE` 下溢只是其一）、无 `ptlock_init`（`SPLIT_PTE_PTLOCKS` 时）、无 `__GFP_ACCOUNT`（开 memcg 时）。
- **[P2] A/D 的软件侧 hook 缺**：`arch/dadao/include/asm/pgtable.h:154-184`（无 `ptep_set_access_flags`／`ptep_test_and_clear_young`）↔ `arch/riscv/mm/pgtable.c:8-30`、`arch/riscv/mm/pgtable.c:32-39`。通用版只改 PTE 不失效条目，而 spec 要求「软件清 A/D 后必须显式失效」（`spec/DADAO-12-SEE-主管系统运行环境.md:251`）⇒ 硬件仍命中、PTE 的 A 恒为 0，该页被恒判为冷（与 035「flush 丢 A/D」同族，此处是 hook 侧）。
- **[P2] 无 perf／trace／kfence／kprobe 钩子**：`arch/dadao/mm/fault.c:692-831`（全函数）↔ `arch/riscv/mm/fault.c:294`（kprobe）、`arch/riscv/mm/fault.c:297-300`（trace）、`arch/riscv/mm/fault.c:341`（`perf_sw_event`）、`arch/riscv/mm/fault.c:108`（kfence）。
- **[P2] cache 维护 hook 全 no-op**：`arch/dadao/include/asm/cacheflush.h:9-22` ↔ `arch/riscv/include/asm/cacheflush.h:24-34`（`flush_dcache_folio`）、`arch/riscv/include/asm/cacheflush.h:82-86`（`flush_icache_range`）。**判据**：Vast 的 `cfx5`(cache) 未实现（`spec/Kaiwu-测试机运行环境.md:106`）⇒ 现在正确；但 `spec/DADAO-12-SEE-主管系统运行环境.md:597-605` 定义 `cfx_cache_{exist,enable,ctrl}`，将来有 cache 的实现（`cache_exist=1`）在 arch 侧无 hook 可接。
- **[P2] 无内核 W^X／只读化**：`arch/dadao/mm/init.c:44-53`（`paging_init` 只赋 `init_mm.pgd`，无 `mark_rodata_ro`／`set_memory_*`，grep 0 命中）↔ `arch/riscv/mm/init.c:751`、`arch/riscv/Kconfig:51`（`select ARCH_HAS_STRICT_KERNEL_RWX`）。

### ② 语义不符（7 条）

- **[P0] VMA 用完前已松 mmap 锁**：`arch/dadao/mm/fault.c:212-218`（`find_vma` 后 `mmap_read_unlock` 再返回指针）↔ `arch/riscv/mm/fault.c:382`（`lock_mm_and_find_vma` 持锁到 `arch/riscv/mm/fault.c:406`）。`dadao_pf_fill()`（`arch/dadao/mm/fault.c:452-570`）在**无 mmap 锁、也不持 `ptl`** 下 `set_pte`；并发 munmap 可释放该 L2 表 ⇒ UAF。**深化 035 第 2 条：不只缺 `lock_mm_and_find_vma`，是拿到 vma 后锁已放。**
- **[P0] 缺「读还是写」的判据**：`arch/dadao/mm/fault.c:44-50`（missing 类不区分 load/store，写只由第二次 NWPERM 推断）、`arch/dadao/mm/fault.c:453` ↔ `arch/riscv/mm/fault.c:343-346`（cause 直接给 `FAULT_FLAG_WRITE`／`FAULT_FLAG_INSTRUCTION`）。035 阶段 2 直接改 `handle_mm_fault(vma,addr,flags)` 时，首次 store 会被当读缺页（只读页）⇒ 每次写多一次缺页；`FAULT_FLAG_WRITE` 只能由「DGPTRAP＋VMA 可写」推断，**需 spec 裁定**。
- **[P1] `vm_get_page_prot()` 索引漏 `VM_SHARED`**：`arch/dadao/mm/init.c:39-42` ↔ 通用宏 `include/linux/pgtable.h:2493-2496`（riscv 用 `DECLARE_VM_GET_PAGE_PROT`：`arch/riscv/mm/init.c:377`）。`__S000`–`__S111` 恒不生效；现表与 `__P*` 相同故无当下症状，属陷阱。
- **[P2] PTE 构造不置 D／A**：`arch/dadao/mm/fault.c:342-353`（只有 `_PAGE_PRESENT|READ|FRAG_ALL`＋按需 W/X）↔ `arch/riscv/mm/fault.c:406`（走通用 `do_anonymous_page` 的 `pte_mkdirty/mk_young`）。D/A 只靠条目替换回写，`INVALID` 不回写（`spec/DADAO-12-SEE-主管系统运行环境.md:250`）⇒ `pte_dirty()` 基本恒假，`folio_mkclean`／回收判据偏（不同于 035 的 `pte_modify` 条）。
- **[P2] `switch_mm` 无 `prev == next` 短路**：`arch/dadao/mm/mmu.c:101-147` ↔ `arch/riscv/mm/context.c:323-324`；每次切换都做一次全 ASID 失效（`arch/dadao/mm/mmu.c:122-123`）。
- **[P2] 无 `mm_cpumask` 维护**：`arch/dadao/mm/mmu.c:101-147` ↔ `arch/riscv/mm/context.c:218`；SMP 后 `flush_tlb_mm` 到不了其它 hart（单 hart 现无害，是 shootdown 的缺口边界）。
- **[P2] 填表目标表的兜底**：`arch/dadao/mm/fault.c:405-411`（PTBR≠`mm->pgd` 就改填内核表）↔ riscv 由 `handle_mm_fault()` 从 vma 所属 mm 取表（`arch/riscv/mm/fault.c:350-362`）。把「表拿错了」变成静默成功（注释自证 measured）。

### ③ 旁路 vs 通用（3 条）

- **[P2] fork 的共享半重复实现**：`arch/dadao/mm/mmu.c:243-293`（逐 64 KiB PTE 重做 `copy_page_range`）↔ 通用 `mm/memory.c:1507`；`arch_dup_mmap` 在 `mm/mmap.c:1848` 于 `copy_page_range` 之后又扫一遍，重复写保护，靠 `dadao_cow_dup_writable==0` 兜；代价 O(范围/PAGE_SIZE)。随 035 阶段 2 消失。
- **[P2] 私有缺页计数**：`arch/dadao/mm/fault.c:288-303` ↔ 通用 `count_vm_event(PGFAULT)`（`mm/memory.c:6550`）；自造通道的缺页不进 `pgfault`（`/proc/vmstat` 只反映通用路径那几次）。
- **[P2] 启动建表手写**：`arch/dadao/mm/k1_pt.c:3-20` ↔ `arch/arm64/mm/mmu.c:513`（`__create_pgd_mapping`）、`arch/arm64/mm/mmu.c:1424`（`paging_init`）；没有通用 `create_mapping` 层可复用。

### ④ Kconfig 缺口（8 条）

- **[P0] 缺 `select LOCK_MM_AND_FIND_VMA`**：`arch/dadao/Kconfig:9-27`（无此项）↔ `arch/riscv/Kconfig:209`。`lock_mm_and_find_vma()` 整体在 `#ifdef CONFIG_LOCK_MM_AND_FIND_VMA` 内（`mm/mmap_lock.c:436`）⇒ **035 阶段 2 的入口改造缺前置**，且它内含「内核态缺页遇异常表不死锁」的处理（`mm/mmap_lock.c:438-451`），正是本机最缺的一段。
- **[P1] `select UACCESS_MEMCPY`**：`arch/dadao/Kconfig:15` —— ①-uaccess 条的根因（关掉异常表 uaccess）↔ riscv 不选它，走异常表（`arch/riscv/mm/extable.c:82`）。
- **[P2] 缺 `select ARCH_HAS_HW_PTE_YOUNG`**：`arch/dadao/Kconfig:11-22`（无）↔ `arch/riscv/Kconfig:37`；`arch_has_hw_pte_young()` 因此为假，影响 `mm/Kconfig:1435`（`LRU_GEN_WALKS_MMU` 依赖）与 `mm/memory.c:3586`（软件 A 位的双次缺页判据）。
- **[P2] 缺 `select ARCH_HAS_PTE_SPECIAL`**：`arch/dadao/Kconfig:11-22`（无）↔ `arch/riscv/Kconfig:48`；`VM_PFNMAP` 的 pfn 落在 RAM 内时 `vm_normal_page()` 会当正常页取引用。
- **[P2] 缺 `select ARCH_SUPPORTS_PER_VMA_LOCK`**：`arch/dadao/Kconfig:11-22`（无）↔ `arch/riscv/Kconfig:73`；`lock_vma_under_rcu()`（`mm/mmap_lock.c:296`）不可用，入口只能走 `lock_mm_and_find_vma`。
- **[P2] 缺 `select ARCH_WANT_DEFAULT_TOPDOWN_MMAP_LAYOUT`**：`arch/dadao/Kconfig:11-22`（无）↔ `arch/riscv/Kconfig:83`；用户 VA 自下而上分配，与主流 64 位默认相反（`HAVE_ARCH_MMAP_RND_BITS` 一并缺，无 ASLR 随机位宽）。
- **[P2] `select MMU_GATHER_NO_RANGE` 与能力不符**：`arch/dadao/Kconfig:14` ↔ contract-tlb TLB-23 支持 `range`（`.tao/contracts/contract-tlb.md:51`）；选它使 `tlb_flush()` 退化为 `flush_tlb_mm()`（`include/asm-generic/tlb.h:140-142`），每次 zap 全地址空间失效。
- **[P2] 缺 THP／hugetlb 选型**：`arch/dadao/Kconfig:11-22`（无）↔ `arch/riscv/Kconfig:149`（`HAVE_ARCH_TRANSPARENT_HUGEPAGE`）、`arch/riscv/Kconfig:68`（`ARCH_SUPPORTS_HUGETLBFS`）、`arch/riscv/Kconfig:85`（`ARCH_WANT_GENERAL_HUGETLB`）；512 MiB 超页只有启动期 `k1_pt` 能用，mm 侧无法复用。

### 覆盖与口径（现场派生）

- **① 可选 hook 全集**：取通用头 `#ifndef <hook>` 守卫（`include/linux/pgtable.h`、`include/linux/pgalloc.h`、`include/asm-generic/{pgtable-nopmd,mmu_context,tlb,cacheflush,pgalloc}.h`），按 MM/PT 前缀过滤并排除 `*_index`／`*_offset` 类。实测 **79 项**；dadao 定义 **6 项**、riscv **31 项**；riscv-only **26 项**，逐项判定入结论 3 项（其余 23 项为折叠层级／THP／通用兜底等价，清单见 `hooks-triage.txt`）。
- **② 能力开关全集**：同批头文件的 `__HAVE_ARCH_*`／`ARCH_IMPLEMENTS_*`。实测 **60 项**；dadao set **1 项**（`ARCH_IMPLEMENTS_FLUSH_DCACHE_PAGE`）、riscv **21 项**；riscv-only **20 项**，入结论 3 项（A/D 三条合并为 1 条），其余 THP／pud／通用等价。
- **③ 机制条目**：`arch/dadao/mm/` 全部 **10 个文件** ＋ `include/asm/{pgtable,pgalloc,tlbflush,mmu_context,cacheflush,page,mmu,tlb}.h` **8 个**头，逐一对照 riscv 同名件（`arch/riscv/mm/` 16 个文件、对应 6 个头）＋ arm64 的 `mmu.c`／`mmap.c`；启动建表、缺页入口、VMA 锁、ASID/switch_mm、pgd/pte 分配释放、TLB flush、cache、VA 布局 8 个机制组。
- **④ Kconfig 全集**：riscv `select` 全集 **271 项**、dadao **7 项**；差集中 MM 相关（`MMU|PTE|PAGE|HUGETLB|TRANSPARENT|VMA|TLB|PAGETABLE|MMAP|ZONE|MEMORY|CACHE|SPARSEMEM|NUMA`）**41 项**，逐项判定入结论 8 项（清单与理由见 `kconfig-triage.txt`）。
- **本段条目**：**25 条**（①7 ②7 ③3 ④8），全部带两侧 `文件:行号`；行号真实性与 5 条抽查由证据脚本现场校验。

## 完成区

**测试结果**：通过 35/35（证据脚本退出码 0；含 §8 两路注入自检）；失败项：无。

**修改文件**：`.tao/tasks/linux/m14-linux-036-mm缺页页表.md`（仅此一件；未改任何代码，`arch/` 零改动，未动 Linux 源树，不占写者锁、未重建、未跑仿真）。

**验收结果**：
- 覆盖现场派生（源树 HEAD `c5f411a3a`）：hook 全集 **79**／dadao 定义 6／riscv 31／riscv-only 26；能力开关 **60**／1／21／20；riscv `select` **271**、dadao 7、MM 差集 **41**；结论 **25** 条（①7 ②7 ③3 ④8），与各小节标题条数逐类相符。
- 行号真实性：**74** 个 `路径:行号` 全部可解析（文件存在＋行号在范围＋该行非空）；典型失败路径已实测（`arch/riscv/mm/extable.c:29` 原指向空行，被抓出并改正为 `:82`）。
- 5 条抽查（两侧 `sed -n '<行>p'` 原文）：uaccess `asm-generic/uaccess.h`(dadao:10)↔`if (fixup_exception(regs))`(riscv:98)；VMA 锁 `mmap_read_unlock(mm);`(dadao fault.c:217)↔`vma = lock_mm_and_find_vma(...)`(riscv:382)；读/写 `dadao_subcause_is_fetch(pos)`(dadao:453)↔`if (cause == EXC_STORE_PAGE_FAULT)`(riscv:343)；`select UACCESS_MEMCPY`(dadao Kconfig:15)↔`select LOCK_MM_AND_FIND_VMA`(riscv Kconfig:209)；`#define flush_icache_range(...) do { } while (0)`(dadao:17)↔`static inline void flush_icache_range(...)`(riscv:83)。
- 注入自检：结论里 `fault.c:212-218` → `:9212-9218` ⇒ refs 检查 FAIL；`cp` 还原后 md5 一致且回绿。§8 另有两路注入（见「返工 1」）。
- 改动集：`git show --name-only HEAD` 只含本任务书（`files=1 other=0`）；树状态为 clean（提交态）或仅本任务书（未提交态）——两种状态都回绿。

**新发现/坑**：
- **Kconfig `LOCK_MM_AND_FIND_VMA` 是 035 阶段 2 的硬前置**：`lock_mm_and_find_vma()` 整体在 `#ifdef CONFIG_LOCK_MM_AND_FIND_VMA`（`mm/mmap_lock.c:436`）内，dadao 未 select ⇒ 入口改造无法编译/链接；且该函数含「内核态缺页遇异常表不死锁」处理，正是本机缺的一段。
- 「缺页类不含读/写」是硬件契约（missing 只有 DGPTRAP），`FAULT_FLAG_WRITE` 只能由「DGPTRAP＋VMA 可写」推断——转通用路径前需用户裁定，不能照搬 riscv 的 cause 映射。
- A/D 两条独立陷阱：① 软件清 A 后须显式失效（`spec/DADAO-12 §4.5:251`），通用 `ptep_test_and_clear_young` 不失效；② `INVALID` 不回写 A/D（`:250`），而 `flush_tlb_page` 正是 INVALID。
- `vm_get_page_prot()` 覆写漏 `VM_SHARED` 位（通用宏用 4 位索引），本机表两半相同故暂无症状；Vast 未实现 `cfx5`，cacheflush 全 no-op 在**本机**正确，写成「架构无 cache」会在有 I-cache 的实现上静默错。

**返工 1（§8 提交后不回绿）**：原因＝旧 §8 断言 `git status` 恰有 1 项改动，architect 提交后树干净 ⇒ 假 FAIL。修法＝改为「`git show --name-only HEAD` 只含本任务书」＋「树状态为 clean（提交态）或仅本任务书（未提交态）」，去掉裸 `git diff` 依赖；`git diff --stat` 降为信息行。
复验＝① 真实工作树（未提交态）：`git.tree_state | OK uncommitted 但仅本任务书`，**35/35、rc=0**；② **提交态**复现：用同脚本＋同任务书在仓外合成两提交仓库（基线提交含 spec/契约、末提交仅任务书，链上每提交单一文件集）⇒ `git.tree_state | OK clean（提交态）`，**35/35、rc=0**（合成仓已删）；③ 注入两路实跑：范围检查换成根提交（含 `README.md`）⇒ `files=1 other=1 taskfile=0`、该检查红；树里加探针文件 ⇒ status 多 1 项、该检查红；删除后复原回绿。

**遗留问题**：无未完成项。本任务只出结论，25 条的整改去向（立即修／立任务／暂不修）由用户裁定。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `arch/riscv/mm/extable.c:29` 指向空行（凭印象写 `fixup_exception`） | ✅已修 | 改 `:82`（`bool fixup_exception(...)`） | refs 检查由 FAIL（EMPTY-CONTENT）转 PASS，resolved=74 bad=0 |
| `mm/Kconfig:1434` 差 1 行 | ✅已修 | 改 `:1435`（`depends on LRU_GEN && ARCH_HAS_HW_PTE_YOUNG`） | refs 解析通过；`sed -n 1435p` 原文核对 |
| `arch/arm64/mm/mmu.c:480` 实为 `__create_pgd_mapping_locked` | ✅已修 | 改 `:513`（`__create_pgd_mapping`） | `sed -n 513p` 原文核对 |
| riscv/mm 文件数写成 14 | ✅已修 | 改 16（含 Makefile 与 `cache-ops.c`） | `ls arch/riscv/mm | wc -l` = 16 |
| A2 把用户态故障出口记作 `dadao_die` | ✅已修 | 补用户态真路径 `traps.c:378-382`（`dadao_user_fault_from_umon`→`early_exit`），supv 路径单列 `:521` | 通读 `traps.c:355-393,395-521` |
| A1「任一 syscall 拿坏用户指针」表述过宽 | ✅已修 | 限定「越界（不在任何 VMA 内）的用户指针」 | `fault.c:726-737`（有 VMA 走 fill，无 VMA 才 die） |
| B4「`pte_dirty()` 恒假」未说明回写条件 | ✅已修 | 补「D/A 只靠条目替换回写；`INVALID` 不回写」＋spec 行号 | `spec/DADAO-12 §4.5:250` 原文 |
| 覆盖段称「8 个机制组」但只列 7 项 | ✅已修 | 补齐为 8 项（加 TLB flush） | 段落重读 |
| A/D 条原写「aging 恒年轻」，方向反了 | ✅已修 | 改「PTE 的 A 恒为 0、页面恒判为冷」 | spec `:243-251` 的 A_local/A_dirty 规则 |

判决：全部 finding 已修，无未修项 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-20，小改档）

**判决：Needs Revision** —— 唯一阻断 = 证据脚本第 8 节提交后不回绿（退出码/计数与完成区声明不一致）；**25 条结论与三条 P0 全部查实，结论内容无需返工**。

**重跑记录（我亲自执行运行期证据目录内的 `run.sh`）**：`RESULT: FAIL (2 failures)`，`EXIT=1`，`OK=32 / FAIL=2`（共 34 项）。失败项原文：
- `git.changed_files | FAIL expected=1 actual=0`
- `git.only_taskfile | FAIL`

根因：第 8 节断言 `git status -uall` 恰有 1 项改动，而 architect 已提交（HEAD `1ea215ca` 仅含本任务书）⇒ 树干净 ⇒ **假 FAIL**。违反 AGENTS「断言『某变更存在』须带 `$BASE..HEAD`、禁裸 `git diff`（提交后为空 ⇒ 假 FAIL）」「提交后仍须回绿」。完成区「通过 34/34（证据脚本退出码 0）」是提交前结果，**当前重跑不可复现**。

**修改建议（engineer 执行，不弱化断言）**：① `run.sh` §8 改断言「`git show --stat HEAD`（或建树基线..HEAD）只含本任务书」+「工作树 0 项改动」；② 任务书「验收 ④」措辞同步为「HEAD 只含本任务书」；③ 修完重跑，把真实 rc/计数写回完成区。

**独立反例注入（我做，非 engineer 自检）**：`cp` 备份任务书（md5 `c35357c39b9001b617cd66d96f8d6e9b`）→ 把 `arch/riscv/Kconfig:209` 注入为 `:9209` → 重跑同一脚本 ⇒ `refs | resolved=73 bad=1`、`refs.all_resolved FAIL`、`EXIT=1`；`cp` 还原 ⇒ md5 复为 `c35357c39b9001b617cd66d96f8d6e9b`、除上述 2 项 git 断言外全 OK、证据目录无临时残留。

**行号抽查（两侧 `sed -n '<行>p'` 两批共 45 处，P0/P1/P2 各 ≥2，全对）**：
- **[P0] VMA 松锁**：`arch/dadao/mm/fault.c:212/217/218` = `mmap_read_lock(mm);` / `mmap_read_unlock(mm);` / `return vma;` ↔ `arch/riscv/mm/fault.c:382` = `vma = lock_mm_and_find_vma(mm, addr, regs);`、`:406` = `fault = handle_mm_fault(vma, addr, flags, regs);`。
- **[P0] 缺 `select`**：`mm/mmap_lock.c:436` = `#ifdef CONFIG_LOCK_MM_AND_FIND_VMA`（`#endif` 在 550，`lock_mm_and_find_vma()` 定义于 496，在区间内；558 的同名函数属 `#else CONFIG_MMU` 支，dadao `config MMU def_bool y` 不编）；`arch/riscv/Kconfig:209` = `select LOCK_MM_AND_FIND_VMA`；`arch/dadao/Kconfig` 全文 102 行、grep `LOCK_MM_AND_FIND_VMA|PER_VMA_LOCK` = 0 命中 ⇒ 论断成立。
- **[P0] 缺页类不含读/写**：`arch/dadao/mm/fault.c:44` = 「The missing classes do not say read or write. DGPTRAP covers a load and a store alike」；`contract-see.md:129` = 「`DGPTRAP` … 数据读写：L1 `P = 0` 且 `SP = 0`，或 L2 `P = 0`」（缺页类子原因位 [48]–[55] 均无读/写位，方向只由 NRPERM[36]/NWPERM[37] 给）↔ `arch/riscv/mm/fault.c:343-346` = `if (cause == EXC_STORE_PAGE_FAULT) flags |= FAULT_FLAG_WRITE; else if (...) flags |= FAULT_FLAG_INSTRUCTION;`；`mm/memory.c` `handle_pte_fault` = `if (vmf->flags & (FAULT_FLAG_WRITE|FAULT_FLAG_UNSHARE)) … do_wp_page(...)` ⇒ 「handle_mm_fault 需 FAULT_FLAG_WRITE」成立。
- **[P0] fill 不持 `ptl`**：`grep -n "pte_offset_map_lock|spin_lock|ptl" arch/dadao/mm/fault.c` = **0 命中**；`set_pte` 位于 `dadao_pf_fill()` 内 520/541/556/567 行，调用点在 `dadao_pf_find_vma()` 松锁之后 ⇒ 成立。
- **[P1]**：`arch/dadao/mm/fault.c:726/737`、`arch/riscv/mm/fault.c:93/99`、`arch/riscv/mm/extable.c:82`；`arch/dadao/mm/init.c:39/42` ↔ `include/linux/pgtable.h:2493/2496`、`arch/riscv/mm/init.c:377`；`arch/dadao/Kconfig:15` = `select UACCESS_MEMCPY`；`arch/dadao/mm/fault.c:506/514` + `mm/memory.c:451` = `int __pte_alloc(struct mm_struct *mm, pmd_t *pmd)`。
- **[P2]**：`arch/dadao/include/asm/cacheflush.h:9/22` = `do { } while (0)` ↔ `arch/riscv/include/asm/cacheflush.h:24/82`；`arch/dadao/Kconfig:14` = `select MMU_GATHER_NO_RANGE if MMU` ↔ `include/asm-generic/tlb.h:140/142` + `.tao/contracts/contract-tlb.md:51`（TLB-23 `range`）；`arch/dadao/mm/fault.c:342/353` ↔ `arch/riscv/mm/fault.c:406`。

**覆盖数（我另写命令复算 4 个，全部相等）**：riscv `select` 唯一 **271**、dadao **7**、MM 差集 **41**、能力开关全集 **60**，与完成区逐个相符。hook 全集 79 = 通用头 126 个 `#ifndef` 守卫经「MM/PT 前缀过滤 + 排除 index/offset 类」得到；任务书只写了前半句 ⇒ 口径基本说清，建议补一句「并排除 index/offset 类」（**不阻断**）。

**约束核验**：① 不改代码 —— `git show --stat HEAD` 仅本任务书（1 file, +92/−2）、`git status -uall` 干净；Linux 源树 `git log --oneline -1` = `c5f411a3a dadao: linux patch series` 且 `status` 干净（只读未动）。② 门控 —— `make check-knowledge-refs` ⇒ `结果: PASS` `rc=0`；`make check-tasks` ⇒ `rc=0`（报告型：漏收尾 1 = 本任务在跑、待开工 17）。③ 本记录无运行期目录/宿主绝对路径，术语按「寄存器组」口径（未出现 bank 误译）。④ 快照对账 —— 审查前后 `git status --porcelain -uall` 均空、任务书 md5 与审查前一致。

**非阻断事实（供 architect 定夺）**：三条 P0 均为真 —— `m14-linux-035-缺页路径回归通用mm流程` 的入口改造若不先补 `select LOCK_MM_AND_FIND_VMA`，`lock_mm_and_find_vma()` 在 dadao 下无定义（CONFIG_MMU=y 不走 558 兜底）；缺页类无读写位 ⇒ `FAULT_FLAG_WRITE` 只能按「DGPTRAP＋VMA 可写」推断，属 spec 语义，须用户裁定。

**记录写入后门控**：`make check-knowledge-refs` ⇒ `结果: PASS`、`rc=0`；`make check-tasks` ⇒ `rc=0`。判决 **Needs Revision**（仅上述第 8 节回绿一项，返工范围 = 证据脚本 §8 + 验收 ④ 措辞 + 完成区计数，不动 25 条结论）。

### 第 2 轮 reviewer 验收（2026-11-20，只核阻断修复）

**判决：Accepted**（第 1 轮唯一阻断「§8 提交后假 FAIL」已修复，且由我在**提交态**复现回绿）

- **提交态回绿（我自己重跑，关键证据）**：HEAD `a8861f06`（`git show --name-only --format= HEAD` = 仅本任务书）＋树干净 ⇒ 运行期证据目录内 `run.sh` ⇒ `OK=35 / FAIL=0`、`RESULT: PASS (0 failures)`、`EXIT=0`；`scope[HEAD] files=1 other=0 taskfile=1` ⇒ `git.head_only_taskfile | OK expected=0 actual=0`、`git.tree_state | OK clean（提交态）`；`git.diffstat` 为信息行（提交态空）。
- **§8 仍能 FAIL（我自己复现一路，未提交、未用 `reset --hard`/`checkout -- .`）**：树里放探针文件 ⇒ `git.tree_state | FAIL 多余改动：?? <探针>`、`RESULT: FAIL (1 failures)`、`EXIT=1`；`rm` 探针后 `git status -uall` 为空、任务书 md5 复为 `cda3058f5f275346824f0e3e094c6720`（与注入前相等）。另一路（换含其它文件的提交）由脚本 `scope_of` 现场实跑：`scope[a08ebc82…] files=1 other=1 taskfile=0` ⇒ 该断言返回 1（可达 FAIL），`inject.git_scope | OK`。
- **结论未动**：`git diff HEAD~1 HEAD --stat` = 仅本任务书（+43/−16）；`盘点结论` 段 `diff` **仅 1 行差异** = 覆盖口径句补「并排除 `*_index`／`*_offset` 类」（我第 1 轮的**非阻断**建议，数字与判据未变）；25 条条目逐字相同，P0/P1/P2 = 3/5/17 = 25，三条 P0 原文与我第 1 轮查实内容一致。
- **完成区计数已同步**：`34/34` → `35/35（含 §8 两路注入自检）`，与我重跑的 35 项 OK、`EXIT=0` 一致。
- **写入本记录后**：`git status -uall` 只列本任务书 ⇒ 预期 `git.tree_state | OK uncommitted 但仅本任务书`（**设计预期，非缺陷**；按约束**未提交 git**，不产生新 commit）；`make check-knowledge-refs` 与 `make check-tasks` 均在本记录写入后实跑，`rc=0`。
- **约束核验**：未改任何代码（`git diff --stat` 只有本任务书；Linux 源树仍 `c5f411a3a`、只读干净）；本记录无运行期目录/宿主绝对路径；术语按「寄存器组」口径。
