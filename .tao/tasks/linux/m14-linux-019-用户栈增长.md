# m14-linux-019: 用户栈增长（VM_GROWSDOWN 下方扩栈 / 越界不扩）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（execve 建 `VM_GROWSDOWN` 栈 VMA + 页故障通道）
**可并行分片**：否（`components/linux` 单写者；共享 `mm/fault.c` 分发点）
**并行组**：与 `m14-linux-018`（COW）**必须串行**（共享 `mm/fault.c` 的 `CFXPERM`/缺失分发点 / `mm/Makefile` / `Kconfig.debug`）；与 qemu/testcases 可并行
**预估**：3–4 h（单点语义：栈 VMA 下方扩展分支；复核 ≥3 路注入）
**档位**：中改（单点语义；复核 ≥3 路注入——高于中改下限 2，覆盖「栈底边界/上限/非栈 VMA/权限类/邻接」多反例）
**状态**：已验证

> **并入说明（2026-11-19）**：`m14-linux-017` 第 18 轮已按本任务书的 `S1`–`S6` 实现并交付（`fault.c` 的 `dadao_pf_grow_stack()`、`Kconfig.debug` 的 `CONFIG_DADAO_K4_STACK_SELFTEST`、`tools/linux/k4_stack_probe.py` 44 条断言），探针在 017 的第 31 轮与复核中 **44/44、rc=0**。本任务不再单独开工，判据由 `k4_stack_probe` 承接。

## 背景

`m14-linux-016` 的 `execve` 已创建 `VM_GROWSDOWN` 用户栈 VMA，但栈**扩展**（访问栈下方未映射页时向下扩 VMA）尚未实现。缺页地址落在 `VM_GROWSDOWN` VMA 的 `vm_start` 下方、且在允许范围（`stack_guard_gap` 与 `rlimit(RLIMIT_STACK)`）之内 ⇒ 扩 VMA（`expand_downwards`）、装 PTE、重试；否则不扩（走「无 VMA ⇒ 具名终止」）。

判据交接（退役册 `m14-linux-014`，K4 必须逐条落验收；`discussing.md` K4 交接清单）：
- `S1` 一页下沉成功；
- `S2` 连续下沉两次（VMA 大小 == 起始 + 2 页）；
- `S3` 超 `RLIMIT_STACK` 不扩（**须在无邻接 VMA 的布局下构造**，否则被 guard gap 遮蔽）；
- `S4` 非 `VM_GROWSDOWN` 不扩；
- `S5` 权限类不触发扩栈（VMA 不扩、扩栈计数 +0）；
- `S6` 邻接保护（下沉进入 `stack_guard_gap` 即停，不蚕食邻接 VMA；探针把 gap 设小到 gap 先于 limit 触发）。
- `RLIMIT_STACK` 由内核侧设/还原（`init_task` 默认 8 MiB = 128 页），断言用**现场读值**；`setrlimit` 的 syscall 面与继承归 **K5**。

DADAO 特有事实：
- **只有缺页类子原因参与扩栈**（`ADR-0056 D3` 的 `[16..23]`，典型 `DGPTRAP` = L1/L2 `P=0`）；权限类（`[24..30]`）**不得**触发扩栈——否则「往只读页写」被扩成新页、越权被吞。
- 页 64 KiB（`PAGE_SHIFT` 派生）；`stack_guard_gap` 通用默认 `256 * PAGE_SIZE`（16 MiB，按 64 KiB 页）。

## 目标

1. **`mm/fault.c` 增扩展分支**（在「找 VMA」失败后、具名终止前）：`addr < vma->vm_start` 且 `VM_GROWSDOWN`；扩展量满足 `addr + stack_guard_gap` 不侵入下一 VMA、扩展后不超 `rlimit(RLIMIT_STACK)` ⇒ `expand_downwards(vma, addr)` + 按需填充该页 + 返回 `DADAO_PF_RETRY`；否则照具名终止（打印 va / VMA 起止 / 上限值）。**只对缺页类子原因尝试**；权限类直接走终止分支。
2. **探针** `tools/linux/k4_stack_probe.py` + `CONFIG_DADAO_K4_STACK_SELFTEST`：execve 后访问栈 VMA 下方的页，断言见「验收 2」。
3. **计数/边界现场派生**：页大小、VMA 起止、`RLIMIT_STACK` 值全部打印；断言用增量与关系（`new_start == old_start - PAGE_SIZE`），不写死地址。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_stack_probe.py` rc=0，逐 case 打印；期望值现场派生（页大小 ← `.config`/契约、`RLIMIT_STACK` ← 探针读值）。
2. **探针 case（S1–S6，各一条可达 FAIL 断言）**：
   - `S1 一页下沉`：栈 VMA 下方 1 页访问 ⇒ VMA 扩到该页、PTE 装载、读回 0、handler 计数 +1。
   - `S2 连续下沉`：再往下 1 页 ⇒ 再扩（证明非一次性特例）；两次后 VMA 大小 == 起始大小 + 2 页（现场派生）。
   - `S3 超上限`：一次下沉超 `rlimit(RLIMIT_STACK)` ⇒ **不扩**（VMA 未变、handler 走终止分支、无页分配）；**在无邻接 VMA 布局下构造**。
   - `S4 非栈 VMA`：`VM_GROWSDOWN` 未设的 VMA 下方访问 ⇒ **不扩**（终止分支）。
   - `S5 权限类不触发扩栈`：栈 VMA 内**已映射只读页**写 ⇒ 走 `CFXPERM`+`NWPERM`；断言 **VMA 未被扩展**（`vm_start` 不变、扩栈计数 +0），**不**断言该页如何被处理（K4 起由 COW 处理，见 `018`）。
   - `S6 邻接保护`：栈 VMA 下方紧邻另一 VMA ⇒ 下沉进入 `stack_guard_gap` 即停（不蚕食邻接 VMA；探针把 gap 设小到 gap 先于 limit 触发）。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① 去掉 `VM_GROWSDOWN` 判定（任何 VMA 可扩）⇒ `S4` 红；② 去掉上限判定（无限扩）⇒ `S3` 红；③ 权限类也尝试扩栈 ⇒ `S5` 红；④（可选）去掉 `stack_guard_gap` 判定 ⇒ `S6` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k4_fork_probe.py`（016）、`k4_cow_probe.py`（018）rc=0；`make check-patch-tree` rc=0。
5. 完成区：VMA 扩展示意（起始/结束/页数）一行、`RLIMIT_STACK` 来源一行；≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-019/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/mm/{fault.c,Kconfig.debug,Makefile}.patch`、`components/linux/patches/arch/dadao/mm/k4_stack_selftest.c.patch`（新）、`components/linux/changelog.md`、`tools/linux/k4_stack_probe.py`。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 沿用 `fault.c` 的重试预算；扩栈失败路径必须可终止（不得无限重试）。
5. 语义以 `spec/DADAO-12 §2.2.6` + `contract-tlb` + `contract-see §6.1.1` 为准；`VM_GROWSDOWN`/`stack_guard_gap` 属 Linux 通用机制（`mm/mmap.c`），本任务只做**接入**，不重写通用逻辑。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. ~~**（待裁定 4）触发载体**~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环已并入 `016/017`，栈增长可用**真实用户进程**压栈越界触发；内核侧自检保留作补充。本任务 `S1–S6` 的「访问栈下方页」在**内核侧自检代码**（supv 访问）完成，不要求**用户态**触发（用户态触发依赖 U-mode 入口，见 016 待裁定 4）。若要求真实用户进程触发（栈压栈越界），须等 U-mode 入口。
2. **`RLIMIT_STACK` 取值**（退役 014 待裁定 1 遗留）：本任务沿用内核 `init_task` 默认 8 MiB（128 页），探针显式 set/restore、断言用现场读值；`setrlimit` syscall 面与继承归 K5——**不再待裁**（退役册已确认此方向）。

## 审阅记录

（待填）
