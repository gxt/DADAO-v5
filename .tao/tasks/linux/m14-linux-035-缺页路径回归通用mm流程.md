# m14-linux-035: 缺页路径回归 Linux 通用流程（`handle_mm_fault` + rmap/LRU/page cache）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-025`（futex 与原子性）合入后派（linux 单写者）；本任务与 `026`–`029` 无文件冲突，但**建议排在 `026` 之前**（它是后续所有内存类能力的地基）
**可并行分片**：否
**预估**：评估 2–3 h；实施按评估结论另报（预计 1–3 天）
**档位**：大改
**状态**：待验收

## 背景（用户 2026-11-20 裁定）

> **「M14，尽量按主流 ISA 的标准流程走」**

现状与标准流程的偏离（已核）：
- `arch/dadao/mm/fault.c`（832 行）是**自定义缺页通道**：`find_vma()` + `dadao_pf_alloc_page()`（返回**物理地址**）+ `set_pte()`，**从不调用 `handle_mm_fault()`**；
- 因此**没有 `folio_add_new_anon_rmap()` / `lru_cache_add()`** ⇒ `folio->mapping == NULL`、`folio_test_anon()` 为假；
- 直接后果（`m14-linux-025` 实测）：`kernel/futex/core.c` 的 `if (unlikely(!mapping)) return -EFAULT;` 命中 ⇒ **匿名页上的 shared futex 恒 `-EFAULT`**（`discussing.md` N27）；
- 文件页也绕过 page cache：`dadao_pf_fill_from_file()` 用 `kernel_read()` 直接读进新页。
- **`get_user_pages_fast` 在文件映射页上停住**（`m14-linux-025` 第 2 轮返工实测，240 s 超时）：因为该页不是 page cache 页、也不在任何 `mapping` 上 ⇒ 走查 `!folio->mapping` 后无法推进。影响面不止 futex：**GUP / `vmsplice` / `O_DIRECT` / RDMA pin** 一类操作都会受影响。

这不是 DADAO 特有语义所必需——**PTE 编码、地址窗口、cfx 故障码**是 DADAO 特有的，但 rmap/LRU/page cache 是 `mm/` 通用机制。

## 阶段 1（评估，先交结论再动手）

1. **PTE 兼容性**：把 DADAO 的 PTE 编码（`dadao_pf_pte()` 等）与 Linux 通用 `pte_*`/`pmd_*`/`pud_*`/`pgd_*` 宏逐位对照，回答：
   - 现有编码能否用 `__pte()`/`pte_val()` 直接表达（即通用 `mm/` 代码能读懂）；
   - 差在哪：present/writable/user/accessed/dirty/特殊位；
   - 需不需要新增 arch 的 `pte_modify`/`pte_mkwrite` 等重载。
2. **通用路径可达性**：`do_page_fault()` 改成调 `handle_mm_fault(vma, addr, flags, &ctx)` 后，`do_anonymous_page`/`do_wp_page`/`do_fault`（含 `filemap_fault`）各需要哪些 arch 钩子（`pte_alloc`、`pmd_alloc`、`update_mmu_cache`、`flush_tlb_*`）；列出缺口清单。
3. **工作量与风险**：给出「全走通用」vs「arch 适配层 + 保留最小旁路（仅 DADAO 特有处）」两套方案的工作量、回归面、风险点，**给建议但不要自决**；若结论是「无法全走通用」，必须逐条写明卡在哪（spec 依据）。
4. 评估结论写进任务书「阶段 1 结论」段，**交 architect 转达用户**后再进入阶段 2。

## 阶段 1 结论（评估完成，未改实现；证据 = 运行期证据目录内 `run.sh`，59 条引用行逐条核对）

### 1 PTE 兼容性 —— **能**：现有编码可用 `__pte()/pte_val()` 表达，通用 `mm/` 读得懂

- 通用 PTE 接口已在 arch 实现并登记：`pte_none/present/write/dirty/young/user`、`pte_pfn/pfn_pte`、`pte_mkwrite_novma/wrprotect/mkdirty/mkclean/mkyoung/mkold`、`pte_modify`、`set_pte/pte_clear`、折叠 `pmd_*`（`arch/dadao/include/asm/pgtable.h:137-190,227-302`；`:268-285` 向通用头登记）。
- 位对照：present=`P`(0)、writable=`W`(6)、accessed=`A`(3)、dirty=`D`(2)——与 Linux 约定一致；user=`U`(**60**，`:142`）；通用不读的位 `R`(7)/`X`(5)/`G`(4)/frag[15:8]/HSJU[63:60]，语义无冲突。
- **不需新增任何 arch 重载**：`pte_mkwrite`（默认落到 `pte_mkwrite_novma`，`include/linux/pgtable.h:1051`）与 `pte_mkdirty`（已有）都无需新增；`pte_modify` 已存在、只需修语义（见下条 ①）。`bit[59:56]` 是 spec 保留位（`spec/DADAO-12:219,265`），**不可**征用为 `_PAGE_SPECIAL`，也不需要（未选 `CONFIG_ARCH_HAS_PTE_SPECIAL` ⇒ `pte_special()`≡0，`include/linux/mm.h:3445`；零页另由 `is_zero_pfn` 排除，`mm/memory.c:5310`）。
- 待补的是**语义**缺口（非位宽）：① `pte_modify()` 只保留 PFN（`:181`）⇒ `mprotect` 会清 D；② `flush_tlb_{page,range,mm}` 只用 `INVALID`（`asm/tlbflush.h:101,113`），而 `INVALID` 不回写 A/D（`spec/DADAO-12:251`）⇒ `pte_dirty/pte_young` 系统性漏报；③ 通道裸 `alloc_page` 建 L2（`mm/fault.c:509-512`）却由通用 `pte_free` 释放（`asm-generic/pgalloc.h:114`）⇒ `NR_PAGETABLE` 统计下溢。

### 2 通用路径可达性 —— **可达**；缺口 5 条，全在 arch/入口

- 已齐备：`pte_alloc_one/pte_free` + `pmd_populate`（`asm/pgalloc.h:61-65`）、折叠 `pmd_alloc`（`asm-generic/pgtable-nopmd.h:62`）、`update_mmu_cache`≡no-op（`pgtable.h:293-294`）、`ptep_set_access_flags/ptep_clear_flush`（`mm/pgtable-generic.c:70,97`）、`flush_cache_page`≡no-op（`asm/cacheflush.h:13`）。
- **A（必须补）**：`arch_vma_access_permitted()` 恒 true（`asm/mmu_context.h:98`）⇒ 入口须自判 VMA 权限；否则 RO VMA 的写会进 `do_wp_page`，`maybe_mkwrite` 不置 W（`mm/memory.c:5259`）⇒ 反复缺页。
- **B**：入口改 `lock_mm_and_find_vma()`（`mm/mmap_lock.c:496`）+ `handle_mm_fault()`（`mm/memory.c:6651`）+ `VM_FAULT_RETRY` 重试环，替代窗口查找与自造栈增长。
- **C**：`do_anonymous_page` 需 `folio_mk_pte`+`pte_mkwrite/pte_mkdirty`+`folio_add_new_anon_rmap`+`folio_add_lru_vma`+`set_ptes`（`mm/memory.c:5250-5268`）——已具备，**且该路径今天已在跑**（execve 的 argv/env 页经 `get_user_pages_remote`→`handle_mm_fault`，`fs/exec.c:166`；`pgtable.h:96-107` 有实测记录）。
- **D（file 页）**：ramfs 有 `read_folio`（`fs/libfs.c:1024`）、`mmap_prepare` 要求它非空（`mm/filemap.c:4046`）、`page_mkwrite`=`filemap_page_mkwrite`（`:3996`）⇒ `filemap_fault` 可行；`CONFIG_TMPFS=n` ⇒ rootfs 走 filemap 而非 shmem。
- **E（不可消除）**：通用无「present 但 GPF/SPF 未满」概念（`spec/DADAO-12 §2.2.3/§2.2.4`）⇒ 通用路径装 PTE 只能一律写满 frag，`frag-set`/`fill-super` 必须留在旁路。

### 3 两套方案（给建议，不自决）

- **甲 全走通用**：`mm/fault.c`(832 行，重写≈500)、删 `mm/cow.c`(210)、`mm/mmu.c`(−100)、`mmu_context.h`/`pgtable.h`/`tlbflush.h`/`mm/init.c`；**探针与门控必须重造**：`k3_pf_selftest.c`(897 行)+`k4_*_selftest.c`(1351 行)+`k3_page_probe.py`(110 项)+`check_k3.py`(174 项)+`k4_*_probe.py`(353 项)。估 3–5 天。
- **乙 适配层 + 只留「无 mm 探针窗口」旁路**：`fault.c` 加 ≈120 行通用臂（用户 VMA 走通用），窗口臂原样保留；删 `cow.c`/COW 钩子；修 `pte_modify`；`flush_tlb_*` 改 `FLUSH`。探针只对齐 k4 的 3–5 处 result 名，K3 不动。估 1–1.5 天。
- **若选甲，最大风险**：K3 的 9 个缺页镜像全部在 `current->mm == NULL` 下跑（`kernel/setup.c:299,303`），窗口臂是唯一入口（`fault.c:204-229`）⇒ **没有 mm 就没有「通用路径」**；甲实质等于退役/重写已收口的 K3 判据（263 项），且因缺口 E 仍留 fragment 旁路 ⇒「零旁路」做不到。
- **建议：乙**——阶段 2 的三条最低要求（匿名 rmap+LRU、文件走页缓存、用户映射无 PA 直通）乙全部满足；PA 直通可精确限定为 `vm_mm == NULL` 的探针窗口（K3 无进程，属 spec 判据载体，依 `spec/DADAO-12 §2.2.3/§2.2.4`）。**等用户选甲/乙后再进阶段 2。**

### 4 两个已知症状的机制（只定位）

- 匿名页 shared futex `-14`：`folio->mapping == NULL` ⇒ `kernel/futex/core.c:650` 分支 ⇒ `:666 return -EFAULT`；根因是通道页从未 `folio_add_new_anon_rmap()`，不是「匿名页」的固有属性。
- 文件映射页 GUP 停住：**不是锁，也不是 `page_mkwrite` 阻塞，而是 `__get_user_pages` 的无进展重试环**——MAP_SHARED 文件 VMA + 只读 PTE ⇒ `follow_page_pte` 对 `FOLL_WRITE` 返回 NULL ⇒ `faultin_page`（`mm/gup.c:1428`）→ `do_wp_page` 走 shared（`mm/memory.c:4292`）→ `filemap_page_mkwrite` 见 `folio->mapping != i_mapping`（页不在页缓存）→ `VM_FAULT_NOPAGE`（`mm/filemap.c:4005-4007`）→ `faultin_page` 返回 0 → `case 0: goto retry`（`mm/gup.c:1431-1432`）。futex 先试 `FOLL_WRITE`（`kernel/futex/core.c:601`），故 WAKE 也停在这一步（与「240 s 无输出」一致）。

### 5 影响面

- 被挡/半可用：shared futex（⇒ **029** 的 shared 用例）；GUP 族 `process_vm_readv/writev`、`ptrace`、`/proc/pid/mem`、`vmsplice`、`io_uring` 固定缓冲（`FOLL_LONGTERM` 还需 LRU/迁移）、`O_DIRECT` 用户缓冲（文件 MAP_SHARED 上一律命中 §4 重试环）；页缓存类 `splice/sendfile`、`msync`、ELF/共享库按需分页；回收/迁移/compaction（无 rmap ⇒ `try_to_unmap` 无对象、迁移 `-EAGAIN`）；`mlock` 本身不需 rmap，但 unevictable LRU 依赖 `folio_add_lru_vma`。
- 后续任务：026 不受影响；**027 受「权限闸」影响**（缺 `access_error` 等价判据 ⇒ SIGSEGV 退化为反复缺页）；028 不受阻；029 部分被挡；032–034 不依赖 rmap/GUP，但缺页路径一变须重跑基线。

## 裁定（用户 2026-11-20，原话）

> 「**乙，K3 是过渡，该退休则退休，不要纠结；不要一口吃个胖子，把执行路径挪到正轨并不是这一个任务的事**」

落实为：
1. **走乙**（用户 VMA 走通用 `handle_mm_fault`，`current->mm == NULL` 的探针窗口臂保留）；
2. **K3 是过渡形态**：不为「保住 K3 判据」做任何额外设计或折衷；窗口臂**原样保留即可**，将来随 K3 退役自然消失；
3. **本任务只做必要范围**（不要一口吃胖）：不追求「零旁路」，不为 `fragment/superpage` 在通用路径里造对应物，不动 `029`/`032`–`034` 的判据；执行路径的整体迁移由后续任务分步完成。

## 阶段 2（实施，待用户选定甲/乙）

按阶段 1 选定方案实施，最低要求：
1. 匿名页有 rmap：`folio_add_new_anon_rmap()` + `lru_cache_add_inactive_or_unevictable()`（含 **COW 路径**）；
2. 文件页走 page cache（`filemap_fault`），不再 `kernel_read` 直灌；
3. **PA 直通旁路收窄到 `current->mm == NULL` 的探针窗口**（阶段 1 已证明通用路径无对应物；K3 为过渡形态，不为其做额外设计，将来随 K3 退役）。

## 验收（阶段 2）

1. **N27 关闭**：匿名页上的 shared `FUTEX_WAIT`/`WAKE` 不再 `-EFAULT`（贴控制台原文）；`shared` futex 单进程内实测可用；
2. **rmap 遍历可跑**：`munmap`/`exit` 时 `try_to_unmap` 遍历我们的 PTE 不崩（给实测）；
3. **不回归**：k1（页表）/k2（中断）/k3（缺页）/k4（fork/COW/栈/切换/内核线程）/k5（syscall/clone/futex）全部 0 FAIL；
4. `check-patch-tree` linux 段 0 问题；从 base 全新 `apply_series` 可重放；合并态（`Process-07 §5a`）；
5. **可达 FAIL**：关掉 rmap 注册 ⇒ 第 1 条红（`cp`+md5 还原 + 重建）。

## 完成区

**测试结果**：`run.sh` 59/59 引用行通过（`RESULT anchors=59 failed=0 mismatch=0 rc=0`）；补丁集↔源码树一致性 mismatch=0；`--inject` 注入 1 条错 anchor ⇒ 如预期变红（`failed=1`，具名 `mm/memory.c:5250`）→ 还原（anchor md5 前后同为 `549b66dc…`）→ 回绿（`failed=0`）。首跑曾有 6 条 anchor 红（futex 行号偏 1–2、spec 路径基准错、k3/setup 行号偏），逐条修正后全绿——即检查器确有一条可达 FAIL 路径。

**修改文件**：仅本任务书（新增「阶段 1 结论」、完成区、审阅记录、状态）。其余产物（`run.sh`/`anchors.txt`/两次运行日志）只在运行期证据目录，未入仓；`components/linux/**`、`spec/**`、`.tao/contracts/**`、`tools/**` 一字未改；未提交 git。

**验收结果**：脚本现场统计（未写死）：K3 缺页镜像 9 个、`k3_page_probe` 110 项、`check_k3` 174 项、k4 探针合计 353 项；`fault.c` 832 行、`cow.c` 210 行、`k3_pf_selftest.c` 897 行、`k4_*_selftest.c` 1351 行。全部结论行均带「文件:行号」且经脚本核对（含上游 `mm/`、`fs/`、`kernel/futex/` 的 24 条）。

**新发现/坑**：
1. PTE 编码本身与通用一致（present 0 / W 6 / A 3 / D 2；user=U bit60），真正的缺口在语义层：`pte_modify` 丢 D、`flush_tlb_*` 用 `INVALID` 丢 A/D 回写（`contract-tlb` TLB-17）、通道裸建 L2 与通用 `pte_free` 的 ptdesc 记账不一致。
2. `bit[59:56]` 是 spec 保留位，**不能**征用为 `_PAGE_SPECIAL`；也不需要（`CONFIG_ARCH_HAS_PTE_SPECIAL` 未选 ⇒ `pte_special()`≡0，零页由 `is_zero_pfn` 单独排除）。
3. GUP 240 s 停住的真因不是锁/`page_mkwrite` 阻塞，而是 `__get_user_pages()` 的 `case 0: goto retry` 无进展环（`filemap_page_mkwrite` 对「不在页缓存的 folio」返回 `NOPAGE`）。
4. `handle_mm_fault()` 只在有 mm 时存在 ⇒「全走通用」与「K3 无进程探针」结构性冲突（9/9 镜像在 `current->mm == NULL` 下跑），这是甲方案的成本主项。
5. `arch_vma_access_permitted()` 恒 true：通用化后权限闸必须留在 arch 入口，否则 SIGSEGV 退化为反复缺页（影响 027）。
6. `arch_vma_access_permitted` / `pte_special` / `pte_protnone` / `pte_mkwrite` 都不是「缺函数」，而是「有恒等/默认实现」——查缺口要查语义，不能只 grep 符号存在性。

**遗留问题**：甲/乙待用户裁定（本任务不自决，未开工阶段 2）；阶段 2 的预计耗时按选定方案另报。

## 阶段 2 处理（含 `036`/`042` 的两条 P0 对接）

**① `036` P0-a：`select LOCK_MM_AND_FIND_VMA` 缺失 —— 已补。**
`arch/dadao/Kconfig` 增 `select LOCK_MM_AND_FIND_VMA`（`arch/riscv/Kconfig` 同形），`lock_mm_and_find_vma()` 的实现（`mm/mmap_lock.c` 的 `#ifdef CONFIG_LOCK_MM_AND_FIND_VMA` 段）因此真正编进来；入口用它做「拿 mmap 锁 + 查 VMA + 栈增长」，不再自己实现查找。

**② `036` P0-b：缺页类不分读/写 —— 按「不推断」实现，并**列为待裁定**。**
现状与证据：本端口保持「`DGPTRAP` → 先填**只读**页；写由随后的 `CFXPERM + NWPERM` 判」，`do_wp_page()` 确实被走到（`k4_cow` 的 `replace-zero → cow-copy → cow-write` 三行、86/86 绿），COW 语义正确；差别只是「首次写」多一次缺页。
未采用 `036` 的「`DGPTRAP` + VMA 可写 ⇒ 视为写缺页」推断，原因（**这是取舍，不是漏做**）：它会把**读**缺页也变成一次复制（私有可写 VMA 上的读会 COW，浪费一整页），并且与本端口既有判据冲突（`k4_cow`/`k4_stack`/`k4_fork` 共 10 余项断言 `fill-zero`）。**待用户裁定**：若采用该推断，需同时改写上述 `fill-zero` 判据，并接受「读缺页也复制」的语义降级。
另一条**未变**的语义边界：写**只读 VMA**（`VM_WRITE` 未置）仍是具名终止（`die-perm`），由 arch 入口的权限闸（`dadao_pf_vma_perm_denied()`）判定 —— 这是 `027` 的 SIGSEGV 前提。

**③ `042` P0：`user_mode()` 恒 0 —— 入口改为按分发路由取模式；帧位新增**待裁定**。**
核对结论：`struct pt_regs`（`asm/ptrace.h`）**没有**模式位 —— `ip` 是 `excp_cause_ip`、`status` 按 `contract-abi`/`contract-see §6.4` 恒写 0，硬件的 `excp_prev_run_mode`（`cfx_smon cg5`）没有被入口桩搬进帧。因此**不猜**（没有用 `ip < TASK_SIZE` 之类的推断），而是按**分发路由的事实**取值：`dadao_user_fault_from_umon()`（`cfx_umon` 交接）传 `from_user=true`，supv 向量传 `false`，`dadao_do_page_fault(..., from_user)` → `FAULT_FLAG_USER`。
`lock_mm_and_find_vma()` 内部仍依赖 `user_mode(regs)`（锁升级路径）：竞争时它会误判并走 `search_exception_tables()`（本端口 `__ex_table` 为空）。对策不是改 `user_mode()`，而是入口**不再依赖它**：①栈增长由 arch 的 `dadao_pf_grow_stack()`（同一份 generic `expand_stack_locked()`）补做；②其余「helper 返回 NULL」的场合用普通读锁重查一次（这两条都不改变判据，只在竞争/无异常表时把判决恢复成它本该有的结果）。
**待用户裁定**：给 `struct pt_regs` 新增 `prev_mode`（入口桩保存 `excp_prev_run_mode`，`asm-offsets`/`entry.h` 同步），让 `user_mode()` 有真值 —— 这是**帧布局（contract-syscall §8 / contract-see §6.2）变更**，不在本任务自决。

**④ `042` 附注：`CONFIG_GENERIC_IRQ_ENTRY` 未编** —— 不在本任务范围（属 026/中断类整改），未改。核对本任务验收：没有任何断言依赖 `in_interrupt()`/`get_irq_regs()`（缺页探针用的是「阻塞完成量 + 单 hart」的交接，`kernel/entry/common.o` 与软中断无关）；若后续回收路径要用它们，另立任务。

**⑤ K3 窗口臂的 PA 直通**（`vm_private_data` / `alloc_page` 表）：按裁定保留在 `current->mm == NULL` 的探针窗口臂，不为其做额外设计，随 K3 退役消失；**用户 VMA 已无 PA 直通**（探针改用 `vm_insert_page()`）。

## 阶段 2 完成区

**测试结果**（逐条真 rc，`--no-inject` 的口径注明）：`k0` 130/130、`k1` 112/112、`k2` 170/170、`k3` 263/263 全 PASS（`make check-linux-k0/-k1/-k2/-k3` rc=0）；`k4_fork` 104/104、`k4_cow` 86/86、`k4_stack` 44/44、`k4_switch` 76/76、`k4_kthread` 112/112；`k5_syscall` 104/104、`k5_clone` 97/97、`k5_futex` **174/174**（= 原 171 + 本次 3 项 shared 判据）。`check-patch-tree` linux 段 92 patch、0 问题；`check-index-blobs` 338/0；`check-component-changelog` PASS；从 base 全新 `git apply` 92/92 且与工作树 `diff -qr` 0 行。
**验收 1（N27）**：控制台原文 `K5 futex shared: wake=0 wait=-11 mapping=0x20004441449`（`mapping` 带 `PAGE_MAPPING_ANON` 低三位），即 shared `WAKE` 返 0、错值 `WAIT` 走到取值比较返 `-EAGAIN` —— 不再是 `-EFAULT`。
**验收 2（GUP 停住）**：`K4 cow gup: va=… read=1 mapping_ok=1` + `K4 cow gup-rw: ret=1`（ramfs 文件页、`FOLL_WRITE`），025 的 240 s 挂死场景不再复现；`K4 cow file: readback=…` 证明共享写回到页缓存。
**验收 3（rmap）**：`K4 cow rmap: after_fork=2 mapcount=2` / `rmap2: after_copy=1 mapcount=1`（`rmap_walk()` 走的就是 `try_to_unmap()` 的同一 walker），`munmap` 后 `refs=0`、PTE 清空。
**验收 5（可达 FAIL）**：证据脚本 `--inject` 把「零页写的 COW 解析」换回旧通道页 ⇒ `shared_wake_red=1`（-14）⇒ `cp`+md5 还原（`16cc7f7e…` 前后一致）⇒ 重建 ⇒ 137/137 回绿；另含「锚点检查注入必错条 ⇒ 变红」自检。
**修改文件**：`components/linux/{series,changelog.md}`、`components/linux/patches/arch/dadao/{Kconfig,include/asm/{mmu_context,page,pgtable,ptrace,tlbflush}.h,kernel/{traps,k4_switch_selftest,k5_clone_selftest,k5_futex_selftest,k5_syscall_selftest}.c,mm/{Makefile,fault,init,k4_cow_selftest,mmu}.c}`（删 `mm/cow.c{,.patch}`）、`tools/linux/{k4_cow_probe,k4_fork_probe,k5_futex_probe}.py`、本任务书。未动 `spec/`、`.tao/contracts/`、`tests/`、根 `Makefile`。
**新发现/坑**：① 通用臂必须按「表是不是 walker 用的那张」分流（K4 的 `F5` 用户段跑在内核表上，往 `mm->pgd` 填 walker 看不见）；② `protection_map` 的索引漏 `VM_SHARED` 会让私有可写映射一开始就可写（COW 失效、文件页被改），`DECLARE_VM_GET_PAGE_PROT` + `__P*` 只读才对；③ `copy_user_highpage()` 的参数是 `struct page *`，旧宏把页指针当内核 VA 传给 `memcpy`（第一次被通用 COW 用到时直接踩到映射窗口外）；④ 通用路径会 `folio_add_lru_vma()`，页在 per-CPU LRU 批次里多一份引用，引用计数判据要先 `lru_add_drain()`；⑤ 探针的 `lr/sc` 注入轮被 QEMU 超时打断时**会把源码改坏后不还原**，复跑前必须核组件源树 `git status`（本任务踩过一次，已 `cp` 还原并用补丁内容 md5 对账）。
**遗留问题**：三条**待用户裁定**（见「阶段 2 处理」②③⑤）：`DGPTRAP` 读写推断（未采用）、`struct pt_regs` 新增 `prev_mode` 帧位（`user_mode()` 才有真值）、K3 窗口臂 PA 直通随 K3 退役。`042` 的 `CONFIG_GENERIC_IRQ_ENTRY` 不属本任务。

## 阶段 2 审阅记录

### 第 1 轮 reviewer 验收（大改档：独立重跑 + 4 路反例注入；下列 rc 均为现场真实退出码）

**重跑记录（全部我本人执行，不采信完成区转述）**
- 运行期证据目录内的 `run.sh` rc=0（`ANCHORS passed=21 failed=0`、`RESULT gate_failed=0`）；其 `--inject` rc=0：`INJECT case rc=1` → `shared_wake_red=1` → `RESTORE md5 16cc7f7e… == 16cc7f7e…` → `RESTORE build rc=0` → 回绿 `137/137`。
- `make check-linux-k0` rc=0（130/130，含 apply-series 两跑幂等 + `补丁 92 个`）、`-k1` rc=0（112/112）、`-k2` rc=0（170/170）、`-k3` rc=0（263/263）。
- k4 探针 fork 104/104、cow 86/86、stack 44/44、switch 76/76、kthread 112/112 全 rc=0；k5 探针 syscall 104/104、clone 97/97、futex **174/174** 全 rc=0。
- `make check-patch-tree` rc=0（`linux: 92 patch(es)`，全仓 438 patches OK）；从 base 全新 `git apply` **92/92 成功、`diff -qr` 0 行**；`check-index-blobs` 338/0 rc=0；`check-component-changelog` PASS rc=0；`check-tasks` rc=0（报告型）。
- 验收 1（我本轮控制台原文）：`K5 futex shared: wake=0 wait=-11 mapping=0x20004441449`；`mapping & FOLIO_MAPPING_ANON(0x1)`（`include/linux/page-flags.h:711,718`）= 1 ⇒ anon 成立；`-11 = -EAGAIN`，非 `-EFAULT(-14)`。
- 验收 2（同轮 k4 cow 控制台）：`K4 cow gup: … read=1 mapping_ok=1 refs=4`、`K4 cow gup-rw: … ret=1`、`K4 cow file: readback=…`；cow 全链 **35 s** 跑完 ⇒ 025 的 240 s 挂死不复现（真跑，非读日志）。
- 验收 3：`after_fork=2 mapcount=2`、`after_copy=1 mapcount=1`、`w4: refs_before=1 refs_after=0 pte=0x0`；`mm/rmap.c:2402 try_to_unmap()` → `:2414 rmap_walk(folio,&rwc)` ⇒ walker 同源。

**我方 4 路独立注入（`cp`+md5 备份 → 重建 → 报红 → 还原 → 重建 → 回绿；未用 checkout/restore/stash/reset）**
1. 删 `wp_page_copy()` 的 `folio_add_new_anon_rmap` ⇒ `K5 futex shared: wake=-14 wait=-14 mapping=0x0`、rc=1、5 FAILED（正是 N27 旧症状）⇒ 还原 md5 `7e98d9e0…` 相等、回绿 137/137。
2. `filemap_page_mkwrite()` 恒走 `folio->mapping != mapping` 分支（即 025「页不在页缓存」的旧机制）⇒ 整机 rc=**124**（QEMU 超时）、`自检走到 done 行` 红 ⇒ 回绿 86/86。
3. `_PAGE_CHG_MASK` 只留 PFN ⇒ `modify-keeps-dirty` BAD、`K4 cow FAIL: …=0x0`、rc=1 ⇒ 回绿 86/86（首次注入误删整段致编译失败，判无效并重做）。
4. `dadao_pf_vma_perm_denied()` 恒 false ⇒ `W3: 分支 == die-perm … got='die-fault'`、rc=1 ⇒ 回绿 86/86。
（另 2 次尝试改 `do_anonymous_page`/`map_anon_folio_pte_nopf` 的 rmap **未变红**，属无效注入：该端口首写走 `wp_page_copy`；4 路有效注入还原后 md5 均相等、源码树 `git status` 干净。）

**约束核验**：① K3 窗口臂原样保留——`dadao_do_page_fault()` 仍按 `dadao_pf_mm_active(current->mm)` 分流，fault.c 补丁 diff 中删除行 **0 条**涉 window/frag/superpage，K3 263/263 绿；② 权限闸 `dadao_pf_vma_perm_denied()` 在 **arch**（`arch/dadao/mm/fault.c`），未下沉通用层；③ 未给 fragment/superpage 造通用对应物（用户 VMA 命中超页只 `die-super` 具名拒绝）；④ 改动 23 文件仅 `components/linux/**`、`tools/linux/**`、本任务书，`spec/`、`.tao/contracts/`、`tests/`、根 `Makefile` 未动，补丁集 93→92（`HEAD~1` 的 series = 93 行）；⑤ k5 三项 shared 是**新增非替换**（probe diff 只增 3 个 `expect_group`，selftest 仅删 1 行 PA 直通）；⑥ 两条顺带必修属实：`__P010/__P011/__P110/__P111` 由 `_PAGE_USER_RW(X)` 改只读 + `DECLARE_VM_GET_PAGE_PROT`（索引含 `VM_SHARED`），`page.h` 删除 `__HAVE_ARCH_COPY_USER_HIGHPAGE`（`struct page *` 被当内核 VA 传 `memcpy`）。

**两条未采纳建议的判定**：`DGPTRAP` 读写推断**不采纳成立**——`contract-see §6.1.1 [52]` 写明 DGPTRAP =「数据读写」，编码本身**不区分读写**（读写只在 `CFXPERM/NWPERM`）；按「VMA 可写 ⇒ 写缺页」会把**读**缺页误判成写，私有可写 VMA 上的读也复制、浪费页并撞 `fill-zero` 类判据；现「先填只读、写由 NWPERM 判」与通用语义等价（仅多一次缺页），非漏做。`user_mode()` 按分发路由取值**可接受但有残余**：恒 `return 0` ⇒ 不会出现「把内核当用户」的误判，锁竞争时 `lock_mm_and_find_vma()` 因本端口 `__ex_table` 为空返回 NULL，arch 已用「普通读锁重查」兜回（k4/k5 全绿）；残余是 ① 内核 bug 缺页少了 exception-table 防死锁闸、② supv 模式下用户 VMA 非法地址拿不到 `FAULT_FLAG_USER` ⇒ 无 SIGSEGV/-EFAULT 语义——二者源于既有「无异常表」缺口，**维持 `prev_mode` 帧位待裁定**，落地时须回看该分支。

**非阻断 finding（留 architect 收尾改）**：F1 证据脚本 ② 段只 grep 既有日志、不重跑门控（本 reviewer 已独立重跑补齐）；F2 完成区「新发现/坑②」把 COW 失效归因于「protection_map 索引漏 `VM_SHARED`」，实际直接原因是 `__P010/__P110` 被定义为可写（索引漏 `VM_SHARED` 影响的是共享映射取错半区），措辞不准；F3 k4 cow 探针「内核自评的每条 check 都 ok」在挂机时因无 BAD 行而 vacuous（由 `done 行`/rc 兜住）。

**判决：Accepted** —— 验收 1–5 与全部范围约束在我本人重跑下成立（真实 rc 见上）；三条 finding 均为文档措辞/脚本口径，不改代码行为、不改门控与计数，按「文档级小错」不阻断。

### 第 2 轮 engineer 自审

自主逐行审查了 `mm/fault.c` 的通用臂、`pgtable/tlbflush/mmu/init/page` 五处 arch 改动、四个探针的 `vm_insert_page` 改造与三个 host 探针的判据改动。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 通用臂把「成功」也当非 RETRY（`policy = result ? FATAL : RETRY` 与返回名约定相反）⇒ 每次填页都 `die` | ✅已修 | `policy` 由「名字是否属于 served 集合」判定，`fill-anon/cow-*` 计入 | `k4_cow` 从 `fill-zero` 起逐行推进到 86/86 |
| R2 `ptep_test_and_clear_young()` 写在 `asm/pgtable.h` ⇒ `struct vm_area_struct` 未定义 | ✅已修 | 改成 `extern dadao_ptep_test_and_clear_young()`（定义在 `mm/mmu.c`），`__HAVE_ARCH_*` 一并登记 | 全量编译 rc=0 |
| R3 `pte_modify()` 只保 PFN ⇒ `mprotect` 清 D（阶段 1 的 ①） | ✅已修 | `_PAGE_CHG_MASK`（PFN|D|A|G） | `K4 cow modify: in=… d=1 w=0` |
| R4 A/D 在 TLB 里、`invalid` 不回写 ⇒ rmap/回收读到假的 A/D（阶段 1 的 ②） | ✅已修 | `dadao_tlb_clean_addr()`（`clean|VA`）+ `ptep_get_and_clear()`/young 在读之前 CLEAN；`flush_tlb_*` 保持 `invalid` 并写明理由 | `K4 cow ad: d_before=1 young=1 d_after=1 a=0` |
| R5 用户 VMA 的二级表由裸 `alloc_page` 建（阶段 1 的 ③） | ✅已修 | 用户 VMA 走通用 `pte_alloc()`；裸建只剩窗口臂 | `pte=0x…ff89` 起的表由 generic 建，`munmap` 后无 ptdesc 记账异常 |
| R6 `vm_private_data` 的 PA 直通在用户 VMA 上失效 ⇒ k5 探针执行零页代码 | ✅已修 | 四个探针改 `vm_insert_page()`（先置 `VM_MIXEDMAP`、持写锁） | `k5_futex` 137/137、`k5_syscall` 62/62、`k5_clone` 72/72、`k4_switch` 52/52 |
| R7 `arch_dup_mmap` 钩子删除后，K4 fork 的 S4/S6 静态判据仍找旧符号 | ✅已修 | 判据改为「钩子返回 0、写半是 `handle_mm_fault`、`cow.c` 已删」，符号改查 `handle_mm_fault` | `k4_fork` 104/104 |
| R8 探针在无 mmap 锁下 `find_vma()` ⇒ rwsem WARNING | ✅已修 | `mmap_read_lock` 包住，之后再用 vma | 控制台无 WARNING |
| R9 `K4 cow w5` 的 `flush_va` 期望「故障地址」，通用路径按页失效 | ✅已修（判据按 TLB-23 收窄） | 内核侧与 host 侧都改为「失效 VA 落在故障页」，注释写明「页内偏移不参与匹配」 | `w5-flush-va` ok + host 检查 PASS |
| R10 新增的 shared-futex 判据挂在 F1 里 ⇒ `no-recheck` 注入轮被它先挂住（4 分钟超时、未具名） | ✅已修 | 判据移到最后一个用例（F7）的 handler | `174/174`，7 路注入全绿 |
| R11 证据脚本的锚点计数放在子 shell 里 ⇒ 恒 0（假绿） | ✅已修 | 改为当前 shell 计数，并加「注入必错 anchor ⇒ 必红」自检 | `ANCHORS passed=21 failed=0`；`--inject` 下 `failed=1` 变红后回绿 |
| R12 证据脚本的注入用 `result`/`info`（通用臂里没有这些名字）⇒ 编不过 | ✅已修 | 注入改为「零页写走旧 `dadao_pf_unshare_zero()`」，落在 `dadao_pf_vma_perm_denied()` 之前 | `INJECT build rc=0` → `shared_wake_red=1` → 还原回绿 |

判决：无未修 finding；验收 1/2/3/4/5 逐条有真输出，状态置 `待验收`（三条待用户裁定已隔离在「阶段 2 处理」②③⑤，不影响本任务判决）。

## 审阅记录

### 第 1 轮 engineer 自审

本轮无实现改动，自审对象是「结论是否被证据支撑」：逐条把结论里的每个断言回读代码、并用脚本把 59 条「文件:行号+子串」核对成可复跑的检查（脚本自身带 `--inject` 自检）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| S1 首跑 6 条 anchor 红（futex 650/666 写成 651/664、spec 按内核树解析、`case 6:` 与 `setup.c` 行号偏） | ✅已修 | 改正行号；anchor 支持 `repo:` 前缀解析仓库跟踪文件 | 现 59/59 通过、rc=0；`--inject` 仍能变红 |
| S2 初稿把「K3 无 mm」写成「mm 子系统未初始化」 | ✅已修 | 改为「K3 用例搬进 `dadao_k4_boundary()`（`setup.c:303`），但无进程 ⇒ `current->mm == NULL`（`setup.c:299` 现场打印 `mm=`）」 | 两处 anchor 核对 + `k4_boundary` 调用序列 |
| S3 初稿断言「甲 = 零旁路」 | ✅已修 | 撤回：fragment/superpage 无通用对应物 ⇒ 甲仍留旁路；结论改为「甲做不到零旁路」 | 缺口 E（`spec/DADAO-12 §2.2.3/§2.2.4`） |
| S4 「文件页可走 filemap」当时只是推测 | ✅已修 | 补证据：ramfs `read_folio`（`fs/libfs.c:1024`）、`mmap_prepare` 要求非空（`mm/filemap.c:4046`）、`page_mkwrite`（`:3996`）、`CONFIG_TMPFS=n` | 4 条 anchor 全绿 |
| S5 一度以为零页需要 `_PAGE_SPECIAL` | ✅已修 | 撤回：未选 `CONFIG_ARCH_HAS_PTE_SPECIAL` ⇒ `pte_special()`≡0 且 `vm_normal_page` 显式排除 `is_zero_pfn` | `include/linux/mm.h:3445`、`mm/memory.c:5310` anchor |
| S6 初稿把 GUP 停住归因「锁/`page_mkwrite` 阻塞」 | ✅已修 | 定位为 `__get_user_pages` 的 `case 0: goto retry` 无进展环（`gup.c:1428-1432` + `filemap.c:4005-4007`） | 4 条 anchor 全绿 |

判决：无未修 finding；结论与证据逐条对齐，状态置 `待验收`（等 architect 转达用户选甲/乙后再进阶段 2）。

