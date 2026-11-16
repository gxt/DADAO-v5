# m14-linux-013: 写时复制（写只读页 ⇒ `CFXPERM`+`NWPERM` ⇒ 复制页 / 改 PTE / 失效）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-012`（页故障通道、子原因解码、VMA/PTE 判定、探针骨架）
**可并行分片**：否（`components/linux` 单写者）
**并行组**：与 `m14-linux-014` **必须串行**（共享 `mm/fault.c` 的分发点、`mm/Makefile`、`Kconfig.debug`）；与 `m14-qemu-005` 可并行（不同组件）
**预估**：4–5 h（代码量中等，风险在 PTE 改写与失效的成对性）
**档位**：大改（组件改 + 新复制路径 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

K3 的三项「内存」能力里，COW 是唯一会**改写既有 PTE** 的：写一个只读页 ⇒ 硬件报 `CFXPERM`，内核复制一页、把 PTE 指向新页并置可写、失效该 VA。两个既有事实决定形态：

- **子原因给的是 R/W/X 与 HSJU 的哪一位不符**（`ADR-0056 D3`）：写只读页是 `W=0` ⇒ **`[29] NWPERM`**（不是 `NRPERM`——`[28]` 是「读缺 `R`」）。`cause_info` 恒为**访存地址**（`ADR-0056 D4`）。
- **内核映射是 `G=1`，用户页是 `G=0`**：失效必须用 `ASID_ANY=0` + 当前 `mm->context.asid`，否则会顺带清掉 `G` 条目（`spec/DADAO-12 §4.5`）。
- K3 没有用户态 ⇒ COW 的验证不靠 `fork`：把**同一物理页**映射到两个 VA（都只读），写其一，断言「被写侧换了 PA、另一侧 PA 与内容不变」。

## 目标

1. **`mm/cow.c`**：`dadao_do_wp_page(mm, vma, addr, ptep, ptl)`
   - VMA 必须私有可写（`VM_WRITE && !VM_SHARED`），否则返回「不处理」（由 `fault.c` 判为真越权 ⇒ 具名终止）；
   - `page_count(p) == 1` ⇒ 就地升级（`pte_mkwrite` + `pte_mkdirty` + 失效），**不复制**（1 条断言，证明「独占页不复制」不是靠运气）；
   - 否则分配新页、复制整页（64 KiB，页大小从 `PAGE_SHIFT` 派生）、`set_pte` 指新页 + 可写 + dirty、原页 `put_page`、`update_mmu_cache`（`invalid|VA|ASID_ANY=0`）。
2. **`fault.c` 分发**（在 012 增加的分发点上）：`CFXPERM` 且子原因 `NWPERM`（+ `NRPERM` 仅当 VMA 可读而 PTE 不可读——本任务只需处理 `NWPERM`，其余照 012 的「真越权」终止）⇒ 交给 `dadao_do_wp_page`；处理成功 ⇒ 返回「重试该指令」。
3. **探针** `tools/linux/k3_cow_probe.py` + `CONFIG_DADAO_K3_COW_SELFTEST`：
   - `W1 共享页写入`：同一 PA 映射到 VA1/VA2（都只读）⇒ 写 VA1 成功；断言 VA1 的 PTE PA ≠ 原 PA、VA2 的 PTE PA == 原 PA、VA2 内容 == 写前内容、原 PA 内容未变。**建映射时引用计数必须与映射数一致**（显式 `get_page` 两次或等价），否则会落到「独占页」分支、整条断言失去意义——探针要打印 `page_count` 现场值佐证。
   - `W2 二次写`：再写 VA1 ⇒ **不再进 handler**（计数 +0）、内容一致。
   - `W3 独占页`：独占页（`page_count==1`）写 ⇒ 进一次 handler、**不复制**（PA 不变）、可写。
   - `W4 共享 VMA 写`：`VM_SHARED` VMA 内的只读页写 ⇒ **不**做 COW，走真越权分支（具名终止，cause 名 + sub 名正确）。
   - `W5 漏失效必红`：探针构建里可选关掉 `update_mmu_cache`（独立 case），断言「第二次写仍报 `NWPERM`」——这是为了证明失效是必需的（**不是**为了放行一个坏实现）。
4. **计数口径**：`alloc_pages` 次数、`handler` 次数、`put_page` 次数由探针现场打印（不写死绝对值，断言「增量 == 期望增量」，期望从 case 描述现场推）。

## 验收（逐条贴真实 rc）

1. `python3 tools/linux/k3_cow_probe.py` rc=0，逐 case 打印；期望值现场派生（页大小从 `.config`/契约、位号从 `contract-see §6.1`）。
2. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：
   - ① 不复制、只 `pte_mkwrite`（共享页被就地改成可写）⇒ `W1` 红（VA2 内容被改）；
   - ② 复制了但 PTE 仍指旧 PA ⇒ `W1` 红（VA1 写到的还是旧页）；
   - ③ 装好新 PTE 但不失效 ⇒ `W2`/`W5` 红（仍命中旧只读条目）；
   - ④ 失效用 `ASID_ANY=1`（顺带清掉 `G` 内核条目）⇒ 探针红（内核映射被清后下一次内核访问走步进或报错——须有一条断言能看见）；
   - ⑤ `page_count==1` 分支也复制 ⇒ `W3` 红（PA 变了）。
3. **不回归**：`make check-linux-k0/-k1/-k2` rc=0；`k3_page_probe.py` rc=0（012 的 case 不得被 COW 改坏）；`make check-patch-tree` rc=0。
4. 完成区：位号来源（`ADR-0056 D3` 的 `NWPERM`，并注明「骨架曾写 `NRPERM`，按 ADR 取 `NWPERM`——见待裁定 1」）；≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **预计改动文件**：`components/linux/patches/arch/dadao/mm/{cow.c,Makefile,fault.c}.patch`、`components/linux/patches/arch/dadao/kernel/Kconfig.debug.patch`、`components/linux/patches/arch/dadao/mm/k3_cow_selftest.c.patch`（新）、`components/linux/changelog.md`、`tools/linux/k3_cow_probe.py`。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp` + md5；注入后重建。
4. 所有的「重试」路径沿用 012 的重试上限；不得出现「COW 失败后无限重试」。
5. 语义以 `spec/DADAO-12 §2.2.5`/`§4.5` + `contract-tlb` 为准；**不得**用「Linux 通常这么写」替代契约（例如引用计数与 `page` 生命周期的实现细节可以自定，但 PTE 位与失效范围必须按 spec）。

## 待裁定

1. **子原因位号**：派单骨架写「写只读页 ⇒ `NRPERM`」，但 `ADR-0056 D3` 的位分配是 `[28] NRPERM`（读缺 `R`）、`[29] NWPERM`（写缺 `W`）⇒ 写只读页应为 **`NWPERM`**。本任务按 **`NWPERM`** 写；若用户本意是「权限类统一报 `NRPERM`」，则需改 `ADR-0056 D3`（17 位表）并同步 `spec`/`contract-see`/QEMU/探针四侧——**不建议**，因为那会让「读缺 R」与「写缺 W」不可区分。请主会话确认。
2. **共享页/独占页的验证载体**：K3 无 `fork`，用「同一 PA 两次映射」模拟共享。是否接受该形态（它证明的是 COW 的 PTE/复制语义，不证明 `fork` 的引用计数语义）？建议接受，`fork` 的引用计数归 K4。
3. **`W5`（漏失效必红）是否保留**：它要求一个「故意关掉失效」的探针镜像，属于**反例镜像**。建议保留（它是「失效必需」的唯一直接证据），但要登记为探针脚手架、不进里程碑镜像。

## 审阅记录

（待填）
