# m14-linux-018: 写时复制（COW：写共享只读页 ⇒ 复制旧内容 / 改 PTE / 失效）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（`copy_page_range`）、`m14-linux-017`（子进程须被调度运行才能写共享页）
**可并行分片**：否（`components/linux` 单写者；共享 `mm/fault.c` 分发点）
**并行组**：与 `m14-linux-019`（栈增长）**必须串行**（共享 `mm/fault.c` 的 `CFXPERM` 分发点 / `mm/Makefile` / `Kconfig.debug`）；与 qemu/testcases 可并行
**预估**：4–5 h（代码量中等，风险在 PTE 改写与失效的成对性 + fork 引用计数）
**档位**：大改（组件改 + 新复制路径 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

`m14-linux-016` 的 `copy_page_range` 先做**全量私有复制**（fork 后父子各自拥有独立页）。本任务把它换成**写时复制**：fork 时父子**共享**同一物理页、两侧 PTE 都置只读（父侧也改只读），任一写 ⇒ 硬件报 `CFXPERM` + `NWPERM`，内核复制一页、把写侧 PTE 指新页并置可写、失效该 VA；另一侧 PA 与内容**不变**。

判据交接（退役册 `m14-linux-013`，K4 必须逐条落验收；`discussing.md` K4 交接清单）：
- ① 写共享只读页 ⇒ **复制旧内容**（不是分配清零页）并改 PTE/失效；
- ② **非干扰**：另一引用方 PA 与内容不变；
- ③ `VM_SHARED` 页写 ⇒ **不**走 COW（真越权）；
- ④ `fork` 的引用计数与**末引用回收**；
- ⑤ COW 的失效成对性（不漏 `invalid`）。

DADAO 特有事实：
- 写只读页子原因 = **`[37] NWPERM`**（不是 `[36] NRPERM`，那是「读缺 R」），`cause_info` 恒为访存地址（`contract-see §6.1/§6.1.1`、`ADR-0056 D3/D4`）。
- 内核映射 `G=1`、用户页 `G=0`：失效必须 `ASID_ANY=0` + 当前 `mm->context.asid`，否则顺带清掉 `G` 条目（`spec/DADAO-12 §4.5`）。
- **共享零页不属本任务**（`m14-linux-012` 已用掉且不复制；写零页 ⇒ `fault.c` 的 `unshare_zero` 换新页）。本任务只处理**非零页**的共享。
- `fault.c` 现把「`CFXPERM` + `NWPERM` 且非零页」判为 `die-perm`（`m14-linux-012` 口径）；本任务在该分支**之前**插入 COW 分发点。

## 目标

1. **`copy_page_range` 改 COW**（`mm/` 通用路径的 arch 侧，或 `mm/memory.c` 的 `copy_pte_range` 换 `wp_page_copy` 语义）：共享非零页、父子 PTE 都置只读（`R` 保留、去 `W`）、`page` 引用计数 +1。
2. **`mm/cow.c`**（新）：`dadao_do_wp_page(mm, vma, addr, ptep)`：
   - VMA 须私有可写（`VM_WRITE && !VM_SHARED`），否则返回「不处理」（由 `fault.c` 判真越权 ⇒ 具名终止）；
   - `page_count(p) == 1` ⇒ 就地升级（`pte_mkwrite` + `pte_mkdirty` + 失效），**不复制**；
   - 否则分配新页、**复制旧页整 64 KiB 内容**（页大小从 `PAGE_SHIFT` 派生）、`set_pte` 指新页 + 可写 + dirty、原页 `put_page`、失效该 VA（`invalid|VA|ASID_ANY=0` + 当前 ASID）。
3. **`fault.c` 分发**（在 `CFXPERM` 分支、`unshare_zero` 之后）：`NWPERM` 且非零页共享 ⇒ 交 `dadao_do_wp_page`；成功 ⇒ 返回 `DADAO_PF_RETRY`（重试该指令）。
4. **探针** `tools/linux/k4_cow_probe.py` + `CONFIG_DADAO_K4_COW_SELFTEST`：fork 后子写共享页，断言见「验收 2」。
5. **计数口径**：`alloc_pages` 次数、handler 次数、`put_page` 次数现场打印（不写死绝对值，断言增量 == 期望增量）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_cow_probe.py` rc=0，逐 case 打印；期望值现场派生（页大小 ← `.config`/契约、位号 ← `contract-see §6.1.1`、失效编码 ← `contract-tlb TLB-19`）。
2. **探针 case（对应五条判据，各一条可达 FAIL 断言）**：
   - `W1 复制旧内容（判据①）`：fork 后子写共享只读页成功；断言「写侧 PTE PA ≠ 原 PA」且「新页内容 == 旧页内容（非零哨兵值，证明是**复制**不是清零）」。
   - `W2 非干扰（判据②）`：父侧 PTE PA == 原 PA、父读回内容 == 写前内容、原 PA 内容未变。
   - `W3 VM_SHARED 真越权（判据③）`：`VM_SHARED` VMA 内只读页写 ⇒ **不**走 COW，走真越权分支（具名终止，cause 名 + sub 名正确）。
   - `W4 引用计数与末引用回收（判据④）`：fork 后 `page_count == 2`（现场打印）；子 COW 后 `page_count` 减、父退出后**末引用回收**（`put_page` 到位，页回池/计数归零）。
   - `W5 失效成对（判据⑤）`：子写后父侧再写该页也须再 COW 一次（父侧只读 PTE 仍在）；可选反例镜像「关掉失效」⇒ 第二次写仍报 `NWPERM`（证明失效必需）。
3. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：① 复制时不清零（分配新页不拷贝旧内容）⇒ `W1` 红；② 复制了但 PTE 仍指旧 PA ⇒ `W1` 红（写到的还是旧页）；③ 装新 PTE 不失效 ⇒ `W2`/`W5` 红；④ 失效用 `ASID_ANY=1`（顺带清 `G`）⇒ 探针红（内核映射被清后下一次访问报错）；⑤ `page_count==1` 分支也复制 ⇒ 独占页 PA 变了（红）。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）、`k4_switch_probe.py`（017）rc=0；`make check-patch-tree` rc=0。
5. 完成区：位号来源（`ADR-0056 D3` 的 `NWPERM`）；≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-018/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/mm/{cow.c,fault.c,Makefile}.patch`（cow.c 新建）、`components/linux/patches/arch/dadao/kernel/Kconfig.debug.patch`、`components/linux/patches/arch/dadao/mm/k4_cow_selftest.c.patch`（新）、`components/linux/changelog.md`、`tools/linux/k4_cow_probe.py`。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 所有「重试」沿用 `fault.c` 的重试预算（`DADAO_PF_RETRY_BUDGET`），不得出现「COW 失败后无限重试」。
5. 语义以 `spec/DADAO-12 §2.2.5/§4.5` + `contract-tlb` + `contract-see §6.1.1` 为准；引用计数/`page` 生命周期实现细节可自定，但 PTE 位与失效范围必须按 spec（**不得**用「Linux 通常这么写」替代契约）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~**（待裁定 4）验证载体**~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环已并入 `016/017`（已验证/在途），COW 可用**真实用户进程**写共享页做端到端断言；内核侧自检仍保留作补充。本任务 fork 后子进程写共享页，子进程须被调度运行（`017` 已具备）；**「写」在子进程的内核侧自检代码完成即可**，不要求子进程在**用户态**写（用户态写依赖 U-mode 入口，见 016 待裁定 4）。若用户要求「真实用户进程写共享页」的端到端断言，须等 U-mode 入口（归 K4 则前置、归 K5 则后补）。
2. **（退役 013 待裁定 2 遗留）共享页/独占页载体**：本任务用真实 `fork` 产生共享（不再是「同一 PA 两次映射」的模拟），`fork` 引用计数语义由本任务 `W4` 覆盖，该遗留已消解、无需再裁。

## 审阅记录

（待填）
