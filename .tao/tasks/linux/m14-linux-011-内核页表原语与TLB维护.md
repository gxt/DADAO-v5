# m14-linux-011: 内核页表原语 + `tlb_control`/ASID 封装 + 用户地址空间 L2 分配（`PAGE_SHIFT=16`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-spec-006`（TLB 契约，**硬依赖**）；`m14-linux-006`（K2 异常通道，已验证——本任务的探针要用它的可恢复故障通道）
**可并行分片**：否（`components/linux` 单写者；且构建树共享）
**并行组**：**可**与 `m14-testcases-005` 并行（不同文件域；本任务**不改** `Makefile`）；与 `m14-linux-012/013/014/015` **必须串行**（同一组件、同一构建树）
**预估**：4–5 h
**档位**：大改（组件改 + 新建原语面 + 重建；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

K1 只做了「建一张内核超页表并写 PTBR」，K2 只做了异常/时间/屏蔽；**页表与 TLB 的软件面基本是空的**（可核）：

- `arch/dadao/include/asm/ptw.h`：只有 `dadao_ptbr_read/write`、`dadao_ptw_enabled`、`dadao_tlb_invalidate_all()`（**硬编码 `0x12`** = `invalid|all|ASID_ANY`），没有 ASID/start/size 原语，也没有按 (op, scope, asid_any) 生成命令值的封装；
- `arch/dadao/include/asm/tlbflush.h`：10 个 `flush_tlb_*` 全是空函数体（注释写「K3 adds the CLEAN/FLUSH/INVALID calls」）；
- `arch/dadao/include/asm/pgtable.h`：只有 PTE 位与单页操作 + 折叠的 `pmd_*`；**没有** `pgd_offset`/`pte_offset_*` 这类索引助手，也没有「L1 表项安装」的正确实现（见下一条）；
- `arch/dadao/include/asm/pgalloc.h`：`pgd_alloc`/`pte_alloc_one` 走 `asm-generic`（够用），但 **`pmd_populate`/`pmd_populate_kernel` 写的是 `page_to_virt(pte) | _PAGE_PRESENT`** —— `page_to_virt()` 返回的是**内核 VA**，而硬件 L1 表项的 PPN 字段要的是 **PA**（`spec/DADAO-12 §2.2.2/§2.3`：页表访问用物理地址）。K0/K1 一直走超页路径、从未调用它，所以这个缺陷**未被暴露**；K3 一旦用它建二级表就会立刻错，属本任务必修项；
- `arch/dadao/include/asm/mmu.h`：`mm_context_t` 已有 `unsigned long asid` 字段但**无人分配、无人写入**；`mmu_context.h` 的 `switch_mm`/`activate_mm` 是空 stub（注释「K0: … lands with the smon hand-off (K1)」）；
- `mm/init.c`：`paging_init()` 只把 `swapper_pg_dir` 挂到 `init_mm.pgd`（注释「Growing/replacing the map is K3 work」）。

页大小已由 `CONFIG_PAGE_SIZE_64KB=y`（`arch/dadao/configs/defconfig`）给出 64 KiB，几何是 L1/L2 各 2^13 项、页内偏移 16 位（`spec/DADAO-12 §2.2.2`）——本任务只**断言**它与契约一致，不改几何。

## 目标

1. **`cfx_ptw` 寄存器原语补全**（`include/asm/ptw.h`）
   - 补 `cg12 rc1`（ASID，`[15:0]`，`[63:16]` 读 0）、`rc2`（addr start）、`rc3`（addr size）的读/写；
   - 新增命令封装：`dadao_tlb_control(op, scope, asid_any)`，其中 `op ∈ {NONE, CLEAN, INVALID, FLUSH}`、`scope ∈ {ALL, VA, RANGE}`（值与 `spec/DADAO-12 §4.5` 一致；**不得**在别处再出现裸魔数）；
   - 现有 `dadao_tlb_invalidate_all()` 改为用封装表达（行为不变：`invalid|all|ASID_ANY`），并在注释里写清「内核映射是 `G=1` ⇒ 内核范围失效必须 `ASID_ANY=1`」。
2. **`tlbflush.h` 落地**（替换空 stub）
   - `local_flush_tlb_all/mm/page/range/kernel_range` + 非 `local_` 版本映射到同一实现（单 hart，`ISS-459` 明确跨 hart 不在本版 ⇒ `smp_*` 一律走与本 hart 相同的路径，不新增 IPI 面）；
   - `tlb_mm`/`tlb_page`/`tlb_range` 的 ASID 维度：内核地址（`>= PAGE_OFFSET`）用 `ASID_ANY=1`；用户 mm 用 `mm->context.asid` 且 `ASID_ANY=0`（`G=0` 条目按 ASID 匹配、`G` 条目不被误伤——这是契约行为，注释写清来源）；
   - 注释必须写明：写 `PTBR`/`ASID`/`ptw_enable` **都不隐含失效**，所以 `switch_mm` 序列（K4）必须先写再显式失效。
3. **ASID 面**（`mmu.h` / `mmu_context.h`）
   - `mm->context.asid`（16 位，`mm_context_t` 字段已在，缺分配与写寄存器）：简单下一代分配（单调计数 + 环绕、0 保留给内核），并提供 `dadao_asid_write/read` 原语（写 `cg12 rc1`）；
   - `init_new_context` / `destroy_context` 最小实现；`switch_mm`/`activate_mm` **保持接口**（本任务不实现真正的切换，K4 落地）。
4. **页表原语**（`pgalloc.h` 修正 + `pgtable.h`）
   - **修 `pmd_populate`/`pmd_populate_kernel`**：必须写 **PA**（`__pa(...)`）而不是 `page_to_virt(...)`；L1 表项 = `P=1`、`SP=0`、PPN（PA[55:16]）、`_PAGE_S`；**非叶子条目 `SPF`/`G` 必须写 0**（`spec/DADAO-12 §2.2.5`「非叶 `G` 无意义、软件写 0」）；
   - 补 `pgd_offset`/`pgd_none`/`pgd_clear` 与 `pte_offset_kernel`（若 `asm-generic` 已提供则复用，不新造）；`pgd_alloc/pgd_free`/`pte_alloc_one/pte_free_one` 沿用 `asm-generic`（已够用，不重写）。
5. **`PAGE_SHIFT=16` 的机械断言**：值从构建 `.config`（`CONFIG_PAGE_SIZE_64KB`）派生，并与 `spec/DADAO-12 §2.2.2` 的偏移位宽一致；**用户态 API 影响只登记**（`AT_PAGESZ`=65536、`mmap` 对齐全 64 KiB、`ELF` 段对齐）——验收留 K5，本任务只在完成区写一行「已登记，K5 处理」。
6. **内核侧探针** `tools/linux/k3_pt_probe.py` + `CONFIG_DADAO_K3_PT_SELFTEST`（默认 n，只有探针镜像打开）
   - case 序列（每个 case 打印一行，gate 解析）：`alloc`（L2 表字段合规）→ `map`（新页可读写）→ `stale`（改 PTE 不失效 ⇒ 仍见旧映射）→ `inval_va`（`invalid|VA` ⇒ 见新映射）→ `ad_clean`（读后 `clean` ⇒ PTE 的 A 被回写、条目仍在）→ `flush`（`flush` ⇒ 再访问走步进）→ `asid_g`（`ASID_ANY=0` 不动 `G`；`ASID_ANY=1` 动）→ `ptbr_no_inval`（写 PTBR 同值 ⇒ 条目仍命中）。
   - 探针的**正例**（`map`/`stale`/`inval_va`/`ad_clean`/`flush`/`asid_g`/`ptbr_no_inval`）用原语**显式**建表 + 真实访存，**不**依赖页故障处理（那是 `m14-linux-012` 的交付）；**负例**（对未映射 VA 的一次访问）必须经**真实异常入口**分派、由 K2 的注册探针恢复，用来证明原语造出来的表条目的故障路径确实通到 `cfx_smon`。

## 验收（逐条贴真实 rc）

1. `python3 tools/linux/k3_pt_probe.py` rc=0，逐 case 打印；期望值**现场派生**（页大小/位号/ASID 位宽从契约与 `.config` 解析，禁写死）。
2. **≥4 路注入**（`cp`+md5 还原 + **重建**后回绿）：① `pmd_populate` 把非叶子 `SPF` 写成 `0xff` ⇒ 断言红（`spec` 要求写 0）；② `pmd_populate` 把 `__pa` 改回 `page_to_virt`（即修复前的写法）⇒ 「L1 表项 PPN == 表 PA」断言红；③ `local_flush_tlb_page` 去掉 `ASID_ANY=1`（内核页是 `G=1`，就会不被失效）⇒ `stale`/`flush` 组红；④ `invalid` 换成 `clean`（不删条目）⇒ `inval_va` 组红；⑤ `tlb_control` 的 `scope` 位段写成 `[4:3]` ⇒ 命令值断言红；⑥ `PAGE_SHIFT` 改 15（只在该注入构建里）⇒ 页大小断言红。
3. `make check-linux-k0` rc=0、`make check-linux-k1` rc=0（`check-linux-k2` 若已落地也 rc=0）；`make check-patch-tree` rc=0（一文件一补丁、无空 blob）；`make_patch` 幂等。
4. 内核构建 rc=0、命令行无 `-Werror` 豁免；`arch/dadao` 补丁集能按 `docs/Process-01` 重建。
5. 完成区：每个期望值标注来源（契约章节 / `.config` 键 / `llvm-nm`）；写明「用户态 API 影响已登记，K5 处理」；≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **预计改动文件**：`components/linux/patches/arch/dadao/include/asm/{ptw.h,tlbflush.h,tlb.h,mmu.h,mmu_context.h,pgtable.h,pgalloc.h}.patch`、`components/linux/patches/arch/dadao/mm/Makefile.patch`（仅当需要新增 C 侧助手）、`components/linux/patches/arch/dadao/kernel/{Makefile,Kconfig.debug}.patch`、`components/linux/patches/arch/dadao/mm/k3_pt_selftest.c.patch`（新）、`components/linux/changelog.md`、`tools/linux/k3_pt_probe.py`。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`（L2 接线归 `m14-linux-015`）。
3. 不提交 git；注入还原 `cp` + md5（禁 `git checkout/restore/stash`）；注入后必须**重建**再回绿。
4. 禁 `install-host`、禁 `check-modules`（会装共享安装根）；`JOBS=32`；禁边构建边跑批。
5. 语义一律以 `spec/DADAO-12 §2.2`/`§4.5` 与 `contract-tlb` 为准；**不得**用 RISC-V/x86 的 gup/`switch_mm` 经验补全 DADAO 特有行为（如 `ASID_ANY` 与 `G` 的关系、写 PTBR 不失效）。

## 待裁定

1. **`smp_*` 失效函数**：本版单 hart（`ISS-459`），`smp_*` 是保持「与 `local_*` 同实现且不新增 IPI」还是留空 stub（后续多 hart 再定）？建议**同实现**（空 stub 会让 K4/K5 在 SMP 机型上静默错）。
2. **ASID 分配策略**：单调计数（简单、会环绕）vs 位图回收。建议单调计数 + 环绕时 `flush all`（单 hart、无 SMP shootdown）；需要用户确认它是否够 K4/K5 用。
3. **`switch_mm` 是否本任务落地**：本任务只留接口（K4 才需要真正的地址空间切换）。若用户希望 K3 就把切换序列（写 ASID → 写 PTBR → 显式失效）写进代码，则本任务扩到含切换、K4 只做寄存器保存/恢复。

## 审阅记录

（待填）
