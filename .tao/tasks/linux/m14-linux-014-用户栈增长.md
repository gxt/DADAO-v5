# m14-linux-014: 用户栈增长（栈 VMA 下方可扩范围 ⇒ 扩栈；越界 ⇒ 不扩）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-012`（页故障通道、子原因解码、VMA 判定）
**可并行分片**：否（`components/linux` 单写者）
**并行组**：与 `m14-linux-012`/`015` **必须串行**（共享 `mm/fault.c` 分发点 / `mm/Makefile` / `Kconfig.debug`）；与 `m14-qemu-005` 可并行（不同组件）。`m14-linux-013`（COW）已退役、全归 K4
**预估**：3–4 h
**档位**：中改（单点语义：栈 VMA 下方扩展分支；复核 ≥3 路注入——高于中改下限 2，用于覆盖「栈底边界 / 上限 / 非栈 VMA」三种反例）
**状态**：待开始

## 背景

K3 的三项内存能力里，栈增长是**唯一在 `fault.c` 里加分支**就能完成的：缺页地址落在 `VM_GROWSDOWN` VMA 的 `start` 下方、且在允许范围（`stack_guard_gap` 与 `rlimit(RLIMIT_STACK)`）之内 ⇒ 扩 VMA（`expand_downwards`）、装 PTE、重试；否则不扩（照 012 的「无 VMA ⇒ 具名终止」）。

两条事实决定判据边界：

- **只有缺页类子原因参与扩栈**（`ADR-0056 D3` 的 `[16..23]`，栈增长典型是 `DGPTRAP` = L1/L2 `P=0`）；权限类（`[24..30]`）**不得**触发扩栈——否则「往只读页写」会被扩成新页，越权被吞掉。
- K3 没有用户态 ⇒ 验证载体是内核侧探针：建一个 `VM_GROWSDOWN` 匿名 VMA，从 supv 访问其下方的页（真实硬件异常 → 入口 → handler）。

## 目标

1. **`mm/fault.c` 增加扩展分支**（在 012 的「找 VMA」失败后、具名终止前）：
   - 地址 `addr < vma->vm_start` 且 `vma->vm_flags & VM_GROWSDOWN`；
   - 扩展量在 `addr` 与 `vma->vm_start` 之间，且满足 `addr + stack_guard_gap` 不侵入下一个 VMA、扩展后 VMA 大小不超 `rlimit(RLIMIT_STACK)`；
   - 满足 ⇒ `expand_downwards(vma, addr)` + 按需填充该页（复用 012 的匿名填充）+ 返回「重试」；不满足 ⇒ 照 012 的语义具名终止（打印 va / VMA 起止 / 上限值）。
   - 只对**缺页类**子原因尝试；权限类直接走 012 的终止分支。
2. **探针** `tools/linux/k3_stack_probe.py` + `CONFIG_DADAO_K3_STACK_SELFTEST`：
   - `S1 一页下沉`：栈 VMA 下方 1 页访问 ⇒ VMA 扩到该页、PTE 装载、读回 0、handler 计数 +1；
   - `S2 连续下沉`：再往下 1 页 ⇒ 再扩（证明不是一次性特例）；两次扩展后 VMA 大小 == 起始大小 + 2 页（现场派生）；
   - `S3 超上限`：一次下沉超过 `rlimit(RLIMIT_STACK)` ⇒ **不扩**（VMA 未变、handler 走终止分支、无页分配）；
   - `S4 非栈 VMA`：`VM_GROWSDOWN` 未设的 VMA 下方访问 ⇒ **不扩**（012 的终止分支）；
   - `S5 权限类不触发扩栈`：一个 `VM_GROWSDOWN` VMA 内**已映射的只读页**写 ⇒ 走 `CFXPERM`+`NWPERM`；本条只断言 **VMA 未被扩展**（`vm_start` 不变、扩栈计数 +0），**不**断言该页如何被处理（K3 里已无 COW：`m14-linux-013` 退役 ⇒ 该页在 K3 只会落 012 的权限类终止分支；K4 起才由 COW 处理）。
   - `S6 邻接保护`：栈 VMA 下方紧邻另一个 VMA ⇒ 下沉进入 `stack_guard_gap` 就停（不蚕食邻接 VMA）。
3. **计数/边界现场派生**：页大小、VMA 起止、`RLIMIT_STACK` 值全部打印；断言用增量与关系（`new_start == old_start - PAGE_SIZE`），不写死地址。

## 验收（逐条贴真实 rc）

1. `python3 tools/linux/k3_stack_probe.py` rc=0，逐 case 打印；期望值现场派生（页大小从契约/`.config`，`RLIMIT_STACK` 从探针设置值）。
2. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：
   - ① 去掉 `VM_GROWSDOWN` 判定（任何 VMA 都可扩）⇒ `S4` 红；
   - ② 去掉上限判定（可无限扩）⇒ `S3` 红；
   - ③ 权限类也尝试扩栈 ⇒ `S5` 红；
   - ④（可选）去掉 `stack_guard_gap` 判定 ⇒ `S6` 红。
3. **不回归**：`make check-linux-k0/-k1/-k2` rc=0；`k3_page_probe.py`、`k3_cow_probe.py` rc=0；`make check-patch-tree` rc=0。
4. 完成区：`VMA` 扩展示意（起始/结束/页数）一行、`RLIMIT_STACK` 来源一行；≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **预计改动文件**：`components/linux/patches/arch/dadao/mm/{fault.c,Kconfig.debug,Makefile}.patch`、`components/linux/patches/arch/dadao/mm/k3_stack_selftest.c.patch`（新）、`components/linux/changelog.md`、`tools/linux/k3_stack_probe.py`。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp` + md5；注入后重建。
4. 沿用 012 的重试上限；扩栈失败路径必须可终止（不得无限重试）。
5. 语义以 `spec/DADAO-12 §2.2.6` + `contract-tlb` 为准；`VM_GROWSDOWN`/`stack_guard_gap` 属 Linux 通用机制（`mm/mmap.c`），本任务只做**接入**，不重写通用逻辑。

## 待裁定

1. **`RLIMIT_STACK` 取值**：K3 无用户态、无 `execve`，`rlimit` 由谁设定？建议：内核 `init_task` 的默认值（8 MiB）并在探针里显式 set/restore，断言用「现场读取的 rlimit 值」而不是常量。若用户希望 K3 就引入 `RLIMIT_STACK` syscall 面，则归 K4（本任务只登记）。
2. **`stack_guard_gap` 大小**：沿用通用默认（`256 * PAGE_SIZE` ⇒ 16 MiB，按 64 KiB 页）还是按 spec/机型定？建议沿用通用默认并打印现场值；若 16 MiB 的 gap 让探针的 VMA 布局太挤，可在探针里显式设置更小的 gap 并断言（需说明该值只影响探针）。
3. ~~`S5` 与 013 的边界~~ **已消解**：`m14-linux-013`（COW）已退役、全归 K4 ⇒ K3 里「已映射但只读」的页被写只会落 012 的权限类终止分支，扩栈分支**不得介入**（VMA 不扩）这一条判据不变，且不再有与 COW 判据互相蚕食的问题。K4 引入 COW 后须复核本条（届时栈页写应走 COW 而非终止）。

## 审阅记录

（待填）
