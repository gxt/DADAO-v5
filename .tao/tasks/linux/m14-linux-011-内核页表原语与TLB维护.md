# m14-linux-011: 内核页表原语 + `tlb_control`/ASID 封装 + 用户地址空间 L2 分配（`PAGE_SHIFT=16`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-spec-006`（TLB 契约，**硬依赖**）；`m14-linux-006`（K2 异常通道，已验证——本任务的探针要用它的可恢复故障通道）
**可并行分片**：否（`components/linux` 单写者；且构建树共享）
**并行组**：**可**与 `m14-testcases-005` 并行（不同文件域；本任务**不改** `Makefile`）；与 `m14-linux-012/013/014/015` **必须串行**（同一组件、同一构建树）
**预估**：4–5 h
**档位**：大改（组件改 + 新建原语面 + 重建；复核须独立重跑 + ≥4 路注入）
**状态**：待验收

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

### 第 1 轮 engineer 自审（engineer，2026-11-16）

**范围**：本任务全部改动（12 份 `patches/**` + `series` + `changelog.md` + `tools/linux/k3_pt_probe.py`），逐文件读 diff，逐条对照 `contract-tlb` §4/§5/§6/§7 与 `spec/DADAO-12 §2.2.2/§2.2.3/§4.5`。判决：**可交付**（findings 全部处置）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `pmd_page_vaddr()` 把已含 `PA[55:16]` 的表项再右移 16 位 ⇒ `pte_offset_kernel()` 拿到的二级表地址被除 64 KiB。`pmd_populate` 修好后第一次自检即暴露（同一类「VA/PA/PPN 混淆」） | ✅已修 | `pgtable.h::pmd_page_vaddr` 去掉移位并写清「字段本身即 PA[55:16]」 | 修前 `K3 pt FAIL: l2_walk_pa=0x7ffd code=0x12`；修后 `alloc-walk ptep_pa=0x7ffd0000` 且 G3 10/10 |
| F2 `DADAO_CFX_WRITE` 无 `memory` clobber ⇒ 编译器可把 PTE 存放到失效命令之后（或把后续访问提到前面） | ✅已修（范围内写法） | `dadao_tlb_control()` 两侧加 `barrier()` + 引入 `<linux/compiler.h>`；`cfx.h` 未动（见遗留） | 全量重建通过；矩阵/`stale`/`inval_va` 行为不变 |
| F3 `pmd_leaf()` 恒返回 0，K1 装在 L1 的超页条目会被通用代码当成二级表指针 | ✅已修 | 改按 `_PAGE_SUPER` 判定并注明 K1 真在用 | 编译 + K0/K1/K2 门控全绿 |
| F4 `range` 助手在 `end <= start` 时仍下发 `size=0` ⇒ 硬件 `CFXREG`（TLB-24） | ✅已修 | 三个 range 助手提前 `return` | 自检 `empty_old=1`（不下发、条目保留、无异常） |
| F5 ASID 临时切换窗（写 ASID → 命令 → 还原）若被中断打断，处理器会带别人的 ASID | ⏸延后 | 头注释写明：当前只有 supv + G=1（跨 ASID 命中）故无害，K4 引入 G=0 用户页时决定是否关中断 | 无（K4 语义未定，已在完成区登记） |
| F6 任务书 §6 的 `alloc` 正例若照字面用 `virt_to_page()`/`pgd_alloc()`，在 `setup_arch()` 末尾会解引用尚不存在的 `mem_map` | ❌不修（按事实处置） | 自检改用 `pmd_populate_kernel()`（同一 `__dadao_l1_entry()`）；`pmd_populate()` 走同一修复点，注入打在该表达式上仍必红 | `--inject l1-write-va`、`l1-spf-nonzero` 两路各红且还原回绿 |
| F7 自检把 `cause` 结论打印放在断言之后 ⇒ 注入掩码时只看到失败行、看不到 `masked=unknown` 现场 | ✅已修 | `k3_pt_cause()` 改为「先打印再断言」 | `--inject cause-mask-off` 输出 `masked=unknown` + `code=0x1d` |

> F5/F6 的处置已分别写入完成区「遗留问题」与「新发现」；其余 finding 已修复并复验。

### 第 1 轮 reviewer 验收（reviewer，2026-11-16）

**重跑**（`JOBS=32`，`.work/evidence/m14-linux-011/run.sh`）：前 2 次 `--gates` 被并发会话（m14-qemu-006）同写共享 `.work/build/linux/.config` 打红（`make_defconfig: …did not survive olddefconfig`；K1 镜像混入 `CONFIG_DADAO_K2_SELFTEST_UNKNOWN=y` ⇒ guest `cause=unknown(0x20)` die），安静窗口第 3 次 **12/12 PASS**：`k3_pt_probe` **116/116**（G1 6/G2 7/G3 10/G4 17/G5 48/G6 6/G7 5/G8 1/G9 5/G10 11）、`check-linux-k0` **119/119**、k1 **108/108**、k2 **104/104**、`k2_trap/time/irq_probe` **85/85·151/151·97/97**；`--selfcheck` **9/9**；`--inject` **8/8**（每路 md5 变→红→`cp` 还原→重建→绿；`l1-write-va` 实测 `G3 PPN 期望=32765 实际=33587197`）；patch 树 md5 `55f65b37…` 不变、series **71**、`check-patch-tree` linux **0 problem**、`--source-state` linux `OK HEAD=64f82a081 count=1 clean=True`、`check-component-changelog` PASS。

**`pmd_*` 三处**：`__dadao_l1_entry() = __pa(table)|P|S`（非叶 `G/SPF`=0）；实测 `pte=0x400000007ffd0001`（PPN=0x7ffd=`l2_pa>>16`）、`alloc-walk ptep_pa=0x7ffd0000 ok=1` ⇒ `pmd_page_vaddr` 不再右移 ✓；`pmd_leaf` 按 `_PAGE_SUPER`(bit1=SP，§2.2.3) ✓。注入：`__pa`→内核 VA ⇒ `G3 PPN` 红；`pmd_page_vaddr` 右移回退 ⇒ G3 缺行 `alloc-walk` 红；两路均 `cp`+md5 还原回绿。

**`tlb_control` 逐条对契约**：TLB-19 `[1:0]/[3:2]/bit4` 值生成单点、无裸 `0x12` ✓；TLB-21/22 `none`=0 且无调用方传、不进范围判定 ✓；TLB-23 `all` 不写 start、`VA` 写 start 不写 size、`range` 写 start+size ✓；TLB-24 scope=11 不出现、`range` size=0 由两处 `end<=start` 早返挡下（注入去早返 ⇒ G4 红）✓；TLB-17/25/26 由 G5 矩阵（4 op×3 scope 行为+A/D；`m_invalid_va=0x16`、`m_clean_range=0x19`、`m_flush_all=0x13`、`m_none_all=0x10`）与 G7 实测 ✓；TLB-29/30 注释 + `ptbr_no_inval` ✓。

**10 个 `flush_tlb_*`**：内核地址 `ASID_ANY=1`、用户 mm 写 `mm->context.asid` 后 `ASID_ANY=0`（还原 ASID 不隐含失效）⇒ 与 contract-tlb TLB-25/26、`DADAO-12 §4.5`（`ASID_ANY=1` 含 `G=1`、`=0` 只动 `G=0`）一致；空 range 早返必要（`size=0` ⇒ `CFXREG`，TLB-24）；单 hart 与 `local_` 同实现、无 IPI（TLB-38）。

**`cause & 0xffff` 三处**：`dadao_cause_name()`、分派入口（`raw_cause` 只留表外诊断）、`dadao_exit_code()` 均掩到 `[15:0]`；G9 实测 `bare=CFXMEM sub=0x10010000000000 masked=CFXMEM exit_bare=exit_masked=0xe1 class=0x2`；注入去 name 掩码 ⇒ `masked=unknown`、G9 红。

**reviewer 自设计 7 路**（`cp`+md5+重建，全部还原回绿）：①`pmd_page_vaddr` 右移→G3 红；②`bit4` 反转→红（`inval_va` 缺行：`G=1` 条目未被失效；G7 因 guest 提前退出未跑到）；③`flush_tlb_page` scope `VA`→`RANGE`→G4 红（size=0 ⇒ CFXREG）；⑥scope `VA`→`ALL`→G4 红（不写 `tlb_start` ⇒ 后续 `clean|VA` 用陈旧 start ⇒ `clean_a_after=0x0`）；⑦去掉空 range 早返→G4 红（`ranges` 缺行）。**两路不红**：④`dadao_exit_code` 去掩码→rc=0（子原因恒在 bit≥32、`__ffs` 取最低位 ⇒ 对 `CFXMEM` 该掩码是 no-op）；⑤分派入口去掩码→rc=0（QEMU 未填子原因 wyde，`m14-qemu-005` 前置）。

**越界**：`git diff f714203d..c136e668` 仅 `components/linux/**` + `tools/linux/**` + 本任务书（18 文件）；`components/qemu`、`tests/**`、`spec/`、`.tao/contracts/**`、`Makefile` 0 改动。快照对账：审查前后 `git status -uall` 均空、122 个文件 md5 一致、HEAD 仍 `c136e668`（reviewer 未提交）；注入后 `--source-state` linux 仍 `clean=True count=1`。

**findings（不阻断）**：①G9「退出码分段」断言对 `dadao_exit_code` 掩码不敏感（建议补 `CFXTRAP|子原因` 用例）；②分派掩码在 qemu-005 落地前不可运行期触发；③`--selfcheck` 未覆盖 G1；④共享 `.work` + 各 worktree 自带 `.dadao/gate.lock` ⇒ 跨 worktree 无互斥（本轮 3 次 2 红），建议登记 infra issue；⑤`pmd_leaf` 注入因共享安装根 cfx 别名表缺失（外部 `install-host` 在途）构建失败未跑成，仅代码级核对；⑥QEMU `dadao_tlb_control_exec` 遇 A/D 回写失败即 `return`（TLB-37「其余条目照常处理」），属 qemu 任务域，转 architect。

**判决：Accepted** —— 验收命令块在 reviewer 自己的重跑下全部通过，硬约束（独立 worktree/不提交/`cp`+md5 还原/禁 `install-host`/`JOBS=32`/基线 `f714203d`）无违反；上述 ①–⑥ 为非阻断 finding。

## 完成区

**测试结果**：k3_pt_probe **116/116**（G1 6 / G2 7 / G3 10 / G4 17 / G5 48 / G6 6 / G7 5 / G8 1 / G9 5 / G10 11）；`--selfcheck` 9/9 组可翻转；`--inject` 8/8 路（每路：注入→重建→断言红→`cp`+md5 还原→重建→回绿；第 8 路 `page-any-off` 单独一轮）；不回归：check-linux-k0 119/119、k1 108/108、k2 104/104、k2_trap_probe 85/85、k2_time_probe 151/151、k2_irq_probe 97/97；补丁纪律：71 补丁、`make_patch` 幂等（重导出 md5 不变）、`--source-state` linux `OK clean=True count=1`、`check-patch-tree` linux 段 0 problem、`check-component-changelog` PASS。L1 `make -k check` 68/69 项绿，唯一红项 `check-milestones-fresh R1`（`m14-qemu-006` 有 worktree 未入台账，共享台账归主会话）——与本任务无关，未代改。失败原因：本任务项无。
**修改文件**：`components/linux/patches/arch/dadao/include/asm/{ptw,tlbflush,mmu,mmu_context,pgtable,pgalloc,setup,trap}.h.patch`；`arch/dadao/{Kconfig.debug,kernel/setup.c,kernel/traps.c,mm/Makefile}.patch`；新增 `arch/dadao/mm/{mmu.c,k3_pt_selftest.c}.patch`；`components/linux/{series,changelog.md}`；新增 `tools/linux/k3_pt_probe.py`；一键证据脚本与日志落运行期证据目录（不入仓）。
**验收结果**：
- `pmd_populate` 修复：L1 表项 `pte=0x400000007ffd0001`（P=1/SP=0/S=1/G=0/SPF=0，PPN=0x7ffd==`l2_pa>>16`）、`alloc-walk ptep_pa=0x7ffd0000`（`pmd_page_vaddr` 的同类缺陷一并修）；注入「表项写内核 VA（= 修复前 `page_to_virt` 的值）」⇒ `0x400002007ffd0001`、`K3 pt FAIL: l1_ppn=0x2007ffd code=0x12`、G3 红 → 还原回绿；注入「非叶子 SPF=0xff」⇒ `K3 pt FAIL: l1_SPF=0xff code=0x12`。
- TLB 面：矩阵 12/12（`m_invalid_va cmd=0x16`、`m_clean_range cmd=0x19`、`m_flush_all cmd=0x13` 等，命令值按 contract-tlb TLB-19 现场派生）+ `stale`（旧页）/`inval_va`（新页）/`ad_clean`（`a_before=0 a_after=1 d_after=0 kept_old=1`）/`flush`（`a=1 d=1 refill_new=1`）+ 4 个 `flush_tlb_*` 助手（kernel_range、vma-range、空 range 不下发、`mm`）+ `asid_g`（`any0_global_old=1 any0_local_new=1 any1_global_new=1`）+ `ptbr_no_inval`（`old=1`）；注入 `ASID_ANY` 位位移、scope 位段位移、`invalid`→`clean`、`local_flush_tlb_page` 丢 `ASID_ANY` 各得红（`K3 pt FAIL: inval_va_reads_new=… code=0x16`）。
- `cause & 0xffff`：`bare=CFXMEM sub=0x10010000000000 masked=CFXMEM exit_bare=0xe1 exit_masked=0xe1 class=0x2`；注入去掉掩码 ⇒ `masked=unknown`、`code=0x1d`、G9 红。掩码点三处：`dadao_cause_name()`、分派入口（先取 `cause_id[15:0]`，原始值只留给表外诊断）、`dadao_exit_code()` 分段。
- `PAGE_SHIFT` 断言：`K3 pt geom PAGE_SHIFT=16 PAGE_SIZE=0x10000 PTRS_PER_PTE=8192 PGDIR_SHIFT=29 PTE_BYTES=8` + `#if PAGE_SHIFT != 16`/`BUILD_BUG_ON`；注入断言改 15 ⇒ 构建失败（该路预期红）。
- 期望值来源：`spec/DADAO-12 §2.2.2/§2.2.3`、`contract-tlb` TLB-04/19/23/24/26/34、`spec/DADAO-13 §2`、镜像 `.config`、内核源标记常量，全部由 `tools/linux/k3_pt_probe.py` 现场解析，不写死；自检码 `K3_FAIL_*`=0x10–0x1e 全在 `spec/Kaiwu §7.1` guest 段。**用户态 API 影响（`AT_PAGESZ`=65536、`mmap` 64 KiB 对齐、ELF 段对齐）已登记，K5 处理。**
**新发现/坑**：① `pmd_page_vaddr()` 与 `pmd_populate` 同源的 VA/PA/PPN 混淆（表项已含 `PA[55:16]` 却又右移 16 位 ⇒ 二级表地址被除 64 KiB），K3 第一次建二级表即暴露（`l2_walk_pa=0x7ffd`），已修；② `DADAO_CFX_WRITE` 无 `memory` clobber ⇒ TLB 命令两侧加 `barrier()`，防 PTE 存被沉到失效之后；③ QEMU 目前不填子原因 wyde，本次掩码是 `m14-qemu-005` 的前置；④ 共享构建树会被并发会话改写 `.config`（K3 镜像里出现别的 K2 边界符号），G1 的镜像身份断言正是为此（三次重试见证据 rc 记录）。
**遗留问题**：待裁定 #1/#2/#3 已按任务书建议实现（`smp_*` 与 `local_*` 同实现、无 IPI；ASID 单调计数 + 环绕 `invalid all`；`switch_mm` 只留接口），**需用户确认是否够 K4/K5 用**。`cfx.h` 写宏缺 `memory` clobber（越界文件，未改，建议 K4 前统一处理）。L1 的 `check-milestones-fresh R1`（`m14-qemu-006` 台账行）属主会话。本任务无未完成项。
