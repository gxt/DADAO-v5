# m14-linux-012: 页故障通道 + 按需分页（`CFXMEM` 分发、匿名页/零页填充、按子原因分支）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-011`（页表原语 / `tlb_control` 封装 / L2 分配 / ASID）
**可并行分片**：否（`components/linux` 单写者）
**并行组**：**可**与 `m14-qemu-005` 并行（不同组件域）；但 **`cause & 0xffff` 的掩码改造必须与 `m14-qemu-005` 同批或更早**（QEMU 一开始填 `[63:48]/[47:32]`，未掩码的名表会把每次页表故障判成 `unknown cause` ⇒ K0–K2 门控全红）；与 `m14-linux-013`/`014`/`015` **必须串行**（`mm/fault.c`、`mm/Makefile`、`Kconfig.debug` 三处共享）
**预估**：6–8 h（新通道 + 子原因解码 + 探针镜像）
**档位**：大改（组件改 + 新故障通道 + 探针 + 重建；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

K2 的 `CFXMEM` 处理只有一条路：**预先注册的探针**命中即跳过，其余一律具名终止（`arch/dadao/kernel/traps.c` 的注册通道）。K3 要把它变成正式的**页故障通道**：

- 硬件侧（`spec/DADAO-12 §2.2.6` + `ADR-0056`）：未映射（L1 `P=0` / L2 `P=0` / SPF / GPF）与 A/D 回写失败 ⇒ `CFXMEM`；HSJU 或 R/W/X 不符 ⇒ `CFXPERM`；`cause_id[63:48]/[47:32]（wyde3/wyde2）` 给**子原因** one-hot：
  - 缺失类 `[16..23]` = `IGPTRAP` `ISPTRAP` `IGPFTRAP` `ISPFTRAP` `DGPTRAP` `DSPTRAP` `DGPFTRAP` `DSPFTRAP`；
  - 权限类 `[24..30]` = `NUPERM` `NJPERM` `NSPERM` `NHPERM`（HSJU 四位） / `NRPERM` `NWPERM` `NXPERM`（R/W/X）；
  - `[31] NCFXPERM`（cfx 访问被掩码拒绝）、`[32] ADWBFAIL`（A/D 回写失败）；
  - **其它 cause 的 `[63:16]` 必须为 0**。
- 内核侧：`CFXMEM`/`CFXPERM` 与「缺页 / COW / 越权」这些 **OS 概念无关**（用户 2026-11-16 口径）；如何解释由内核结合 VMA 与 PTE 自行判定——这就是本任务。
- K3 没有用户态（K4/K5 才有）⇒ 本任务的验证载体是**内核侧探针**（S-mode 用真实访存触发真实硬件异常，经入口分派回来），不造用户进程、不做 `fork`。

## 目标

1. **入口分派**（`kernel/traps.c`）：**先按 `cause_id[15:0]` 取大类**（`cause & 0xffff`，`dadao_cause_name()` 的整值查表必须改，否则 QEMU 一旦填子原因位，每一次页表故障都会被判成 `unknown cause`）；`[63:48]/[47:32]` 交给子原因解码；`[63:33]` 非 0 ⇒ 终止（保留区被触发）；然后 `CFXMEM`/`CFXPERM` 走 `dadao_do_page_fault(regs, cause, subcause, info)`；**保留** K1/K2 的注册探针通道且**优先级更高**（否则 K0–K2 门控会红）；未知/多位置 1 的子原因 ⇒ 具名终止（不得默认按缺页处理）。
2. **子原因解码**（新 `include/asm/cause-sub.h` 或在 `ptrace.h`）：位号 → 枚举，值必须与 `contract-see §6.1`（`m14-spec-007` 落地后）**逐位一致**，并与 `ADR-0056 D3` 一致；提供 `is_missing(sub)` / `is_perm(sub)` 两个判据函数（其余位号一律视为「不认识」⇒ 终止）。
3. **缺页路径**（新 `mm/fault.c`）：
   - `find_vma(mm, addr)`；无 VMA ⇒ 具名终止（K3 无信号；K4 起改 `SIGSEGV`，在完成区登记为遗留）；
   - VMA 存在且**缺页类**子原因 ⇒ 匿名分配一页（零页填充路径也要有：先尝试共享零页只读映射，写时再进 COW——与 013 共用同一判据），`set_pte` + `update_mmu_cache`（`invalid` + `VA` + 当前 ASID），返回「重试该指令」；
   - **权限类**子原因 ⇒ 不分配页、不重试（除 013 的 COW 分支），具名终止；
   - **`ADWBFAIL`** ⇒ 不分配、不重试（当缺页重试会**死循环**），打印 `cause_info`（= PTE 物理地址）后终止；
   - 每次进入打印一行统一格式（`cause`/`sub` 符号名/`va`/`vma`/结果），gate 解析；**禁止**在 handler 里用逐指令日志。
4. **`brk` 与匿名 VMA 边缘**：`sys_brk` 的 syscall 面**不在本任务**（K4/K5）；本任务只证明**匿名 VMA（含未来的 `brk` 段）的按需填充与边缘边界**：VMA 内未映射页 ⇒ 填充；VMA 外 ⇒ 不填。用 `vm_mmap`（或 arch 等价）建探针 VMA。
5. **探针** `tools/linux/k3_page_probe.py` + `CONFIG_DADAO_K3_PF_SELFTEST`（默认 n；case 0 = 关）：
   - `P1 首次访问`：VMA 内一页首次读 ⇒ 进 handler、分配、重试成功、读回 0；
   - `P2 二次访问`：同页再读/写 ⇒ **不再进 handler**（handler 计数 +0），且写后读回一致（PTE 可写）；
   - `P3 缺失子原因`：L1 `P=0`（`DGPTRAP`）、L2 `P=0`（`DGPTRAP`）、GPF 位=0（`DGPFTRAP`）三类分别断言**到了哪条分支**（不是只看「没崩」）；
   - `P4 取指缺失`：跳到未映射 IP ⇒ `CFXMEM` + `IGPTRAP`（探针以可恢复方式构造，或断言具名终止的 cause 名）；
   - `P5 权限类`：读 `R=0` 页 ⇒ `CFXPERM` + `NRPERM`，**不**分配页（分配计数不变）、**不**重试；
   - `P6 ADWBFAIL`：注入合成 cause（探针构建里改分派入参）⇒ 走 ADWBFAIL 分支：不分配、不重试、打印 PTE 地址；
   - `P7 无 VMA`：VMA 外地址 ⇒ 具名终止（含 VMA 边界 ±1 页两例）。
6. **子原因消费的最小断言集**：缺失类 8 位里至少各一条路径可达（`SPF`/`GPF`/`L1 P=0`/`L2 P=0` 四类必测，取指侧与数据侧各一），权限类 7 位里至少 `NRPERM`/`NWPERM`/`NSPERM` 三条可达；其余（`NJPERM`/`NHPERM`/`NXPERM`/`NCFXPERM`）由 `tests/arch` 探针覆盖、内核侧只在分派表里登记（不重复测）。

## 验收（逐条贴真实 rc）

1. `python3 tools/linux/k3_page_probe.py` rc=0；每个 case 打印一行（含 cause/sub 符号名），gate 现场解析；期望值来自契约（`contract-see §6.1` 的符号名 → 位号）与 `.config`，**禁写死**。
2. **大类-子原因并存**：探针打印**原始 `cause_id` 全 64 位**与「按 `[15:0]` 解析出的大类名 + `[63:48]/[47:32]` 子原因名」；两者必须同时正确（高位非 0 时大类仍是 `CFXMEM`/`CFXPERM`，不得落入 `unknown cause`）。`[63:33]` 非 0 的构造 ⇒ 走终止分支。
3. **≥4 路注入**（`cp`+md5 还原 + 重建回绿）：
   - ① `is_missing()` 把 `DGPFTRAP` 判成非缺失 ⇒ `P3` 红；
   - ② 缺页路径直接返回「重试」但**不分配/不装 PTE** ⇒ 进入重试循环 ⇒ 探针在**有限次数**内红（必须有循环上限，否则整机挂死——门控要用超时兜底并判 FAIL）；
   - ③ `ADWBFAIL` 当缺页处理 ⇒ `P6` 红（分配计数变了/无限重试）；
   - ④ 装 PTE 后**不** `invalid` ⇒ `P2` 红（同 VA 仍命中旧「未映射」条目 ⇒ 子原因重复出现，handler 计数 +1）；
   - ⑤ 无 VMA 却放行（返回重试）⇒ `P7` 红；
   - ⑥ 其它 cause 的高位不清零（复用上次子原因）⇒ 「非页表 cause 的 `[63:16]==0`」断言红。
4. **不回归**：`make check-linux-k0/-k1/-k2` rc=0（若 `-k2` 已落地）；`make check-patch-tree` rc=0。
5. 完成区：每个期望值来源、每类子原因「内核侧测到 / 由 arch 探针覆盖」的分工表（≤8 行）；遗留（K4 的 `SIGSEGV`、`fork`、`switch_mm`）逐条登记；≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **预计改动文件**：`components/linux/patches/arch/dadao/kernel/{traps.c,Kconfig.debug,Makefile}.patch`、`components/linux/patches/arch/dadao/mm/{fault.c,Makefile}.patch`（`fault.c` 新增）、`components/linux/patches/arch/dadao/include/asm/{cause-sub.h,ptrace.h,setup.h}.patch`、`components/linux/patches/arch/dadao/mm/k3_pf_selftest.c.patch`（新）、`components/linux/changelog.md`、`tools/linux/k3_page_probe.py`。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`（L2 接线归 015）。
3. 不提交 git；注入还原 `cp` + md5；注入后重建。
4. **handler 必须有重试上限**：任何「重试同一指令」的路径都要有次数上界（超界 ⇒ 具名终止，打印 va/cause），否则注入实验会把机器挂死、门控无法判定。
5. 语义以 `spec/DADAO-12 §2.2.6` + `contract-tlb` 为准；**不得**把「缺页/COW」写进规范用语之外的注释里当判据（内核注释可以解释，但断言必须落在硬件 cause/子原因与 VMA/PTE 上）。
6. 禁 `install-host`/`check-modules`；`JOBS=32`；禁边构建边跑批。

## 待裁定

1. **`CFXMEM` 非页表类子原因**（与 `m14-qemu-005` 待裁定 2 同）：段映射/未实现 cfx/SRAM 越界的 `CFXMEM` 子原因是 0 还是某一位。建议 0，并在 `is_missing()/is_perm()` 之外增加「不认识 ⇒ 终止」的兜底，使该问题不影响内核判定。
2. **零页策略**：是否引入**共享零页**（`ZERO_PAGE` 语义）还是每次分配清零页。建议：K3 直接分配零页（简单、可判），把共享零页 + 写时复制登记到 013（它本来就要 COW）。若用户要求 K3 就上共享零页，`P1`/`P2` 的期望要改（分配计数 + 一次 COW）。
3. **`P4` 取指缺失的构造**：跳到未映射 IP 是不可恢复的（IP 已错），探针只能断言「具名终止 + cause/sub 正确」而无法继续。是否接受「该 case 是终止型」（每个终止型 case 单独一个镜像，与 K2 的 P3/P4 同法）？

## 审阅记录

（待填）
