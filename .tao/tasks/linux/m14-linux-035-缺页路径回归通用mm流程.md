# m14-linux-035: 缺页路径回归 Linux 通用流程（`handle_mm_fault` + rmap/LRU/page cache）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-025`（futex 与原子性）合入后派（linux 单写者）；本任务与 `026`–`029` 无文件冲突，但**建议排在 `026` 之前**（它是后续所有内存类能力的地基）
**可并行分片**：否
**预估**：评估 2–3 h；实施按评估结论另报（预计 1–3 天）
**档位**：大改
**状态**：待开始

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

## 阶段 2（实施，待阶段 1 结论）

按阶段 1 选定方案实施，最低要求：
1. 匿名页有 rmap：`folio_add_new_anon_rmap()` + `lru_cache_add_inactive_or_unevictable()`（含 **COW 路径**）；
2. 文件页走 page cache（`filemap_fault`），不再 `kernel_read` 直灌；
3. 不再有「PA 直通」旁路（除非阶段 1 证明不可避，并在代码注释与任务书写明 spec 依据）。

## 验收（阶段 2）

1. **N27 关闭**：匿名页上的 shared `FUTEX_WAIT`/`WAKE` 不再 `-EFAULT`（贴控制台原文）；`shared` futex 单进程内实测可用；
2. **rmap 遍历可跑**：`munmap`/`exit` 时 `try_to_unmap` 遍历我们的 PTE 不崩（给实测）；
3. **不回归**：k1（页表）/k2（中断）/k3（缺页）/k4（fork/COW/栈/切换/内核线程）/k5（syscall/clone/futex）全部 0 FAIL；
4. `check-patch-tree` linux 段 0 问题；从 base 全新 `apply_series` 可重放；合并态（`Process-07 §5a`）；
5. **可达 FAIL**：关掉 rmap 注册 ⇒ 第 1 条红（`cp`+md5 还原 + 重建）。

## 完成区

（待填）
