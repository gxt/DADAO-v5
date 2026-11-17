# m14-linux-016: 进程抽象与 fork/execve 基础（task_struct / mm / copy_process / 地址空间克隆）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-012`（页故障通道 + 按需分页）、`m14-linux-015`（K3 收口门控）、`m14-linux-022`（异常帧四组 rd/rb/ra/rf，已验证）
**可并行分片**：否（`components/linux` 单写者；共享 `mm/fault.c`、`include/asm/processor.h`、`kernel/process.c`）
**并行组**：与 `m14-linux-017`…`021` **全部串行**（同组件同写者 + 共享 `arch/dadao` 文件）；与 qemu/testcases 模块可并行（不同组件）
**预估**：7–9 h（代码量最大的一件：进程骨架 + mm 接线 + execve + 用户态入口骨架 + 探针）
**档位**：大改（组件改 + 新子系统接线 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：待开始

## 背景

K3 收口时内核停在 `setup_arch()` 末尾：`current->mm == NULL`（init task 无地址空间），页故障通道的**页来源**与 **VMA 查找**是 K3 占位（`mm/fault.c` 的 `dadao_pf_alloc_page()` 从 RAM 顶取页、`dadao_pf_find_vma()` 走静态 `dadao_pf_window[]` 数组；源文件注释已明写「K4 替换这两处、其余行不动」）。K4 要建立进程模型，让这些占位变成真实现，并使 `fork`/`execve` 能创建带独立地址空间、可运行的进程。

DADAO 特有事实（不得套 RISC-V/x86）：
- **四组寄存器** `rd/rb/rf/ra`；`SP=rb1`、`FP=rb2`（无条件保留）、`TP=rb3`（rbtp）；`rb0`=只读 IP、`rd0`=恒 0。callee-saved = `rd32–63 ∪ rb32–63 ∪ rf32–63`（`contract-abi §4.5`）。
- **页 64 KiB**、VA 42 位、单 PTBR；ASID 16 位（`mm->context.asid`，K3 `mm/mmu.c` 已分配）。
- **无状态寄存器 / 无 PS.IE**：`struct pt_regs.status` 恒 0（`asm/ptrace.h`）。
- `copy_process`/`dup_mm`/`copy_page_range` 是**通用**代码；本任务只补 `arch/dadao` 钩子（`copy_thread`、`copy_mm` 的 arch 部分、`start_thread`、`ret_from_fork`）。

## 目标

1. **`include/asm/processor.h`**：`thread_struct` 由 `{sp, ra, tp}` 扩为完整上下文（`sp`/`ra` + callee-saved `rd32–63`/`rb32–63` + FP 范围见**待裁定 1**）；`start_thread(regs, pc, sp)` 真实现（填用户入口 `ip`/`rb1`、清 `rb3`、设 `status=0`）。
2. **越过 `mm_core_init()`**：`kernel/setup.c` 去掉 K2/K3 边界 stop，使 `alloc_page`/`find_vma`/VMA cache 可用；`mm/fault.c` 把 `dadao_pf_alloc_page()` 换为 `alloc_page(GFP_KERNEL|__GFP_ZERO)`、`dadao_pf_find_vma()` 换为 `find_vma(current->mm, addr)`（**其余行不动**，注释已明）。
3. **`copy_process` 的 arch 钩子**：`copy_thread()` 把父 `pt_regs` 复制到子任务栈顶、设子 `thread.sp`/返回路径；子进程入口 `ret_from_fork`（可先复用 `trap.S` 的恢复序列，或最小 stub）。
4. **`copy_mm` → `dup_mm` → `copy_page_range`**：地址空间克隆，**全量私有复制**非零页（先正确、后优化——COW 由 `m14-linux-018` 替换）；共享零页**保持共享不复制**（`fault.c` 已有 `unshare_zero`，`012` 口径）。
5. **`execve` 基础**：`arch/dadao` 侧 bprm 装载（从 initramfs 读静态 musl `init` ELF）、建 **`VM_GROWSDOWN` 用户栈 VMA**、`start_thread` 填入口并**建立 U-mode 初始帧**（用户入口 `ip`/`rb1`、清 `rb3`、`status=0`、`ret_from_fork` 落回用户态）；号表/errno/TLS 口径见 `contract-syscall §8–§11`（本任务只做「能 execve 成功、栈 VMA 创建 + 进入用户态」，栈增长的**扩展**语义归 `019`）。
6. **用户态入口骨架（最小 U-mode 闭环，用户 2026-11-17 选 C）**：`cfx_umon` 的 user 模式路由——内核启动时写 `cfx_umon_user_switch_run_mode`（复位 `2 = supv` 可沿用）与 `cfx_umon_user_excp_vector`（复位 `0`，内核须自写，`contract-syscall §8`）；用户 syscall `trap cfx_umon, 0` ⇒ 进 `cfx_umon` 的 user 行向量，`supv` 模式、`cfx_umon` 上下文内开始执行，入口帧保存/恢复寄存器以 `contract-see §6` + `spec/DADAO-12 §5.2` 为准（硬件只存 cg5 五字段、**不存通用寄存器**，`contract-syscall §8`）；返回 = `escape cfx_umon, [excp_cause_ip, 4]`。U-mode **同步异常**（页故障/对齐等）走 `cfx_smon` 的 `supv_excp_vector`（`contract-syscall §8`，`trap.S` 已具备）。**单帧、不递归**；同 cfx 递归 / cg5→cg6 保存留 K5。
7. **`kernel_init()`** 推进到「创建 init 进程并**进入用户态第一条指令**」（用户 2026-11-17 裁定 ④ 选 C：最小 U-mode 闭环并入本任务）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_fork_probe.py` rc=0，逐 case 打印；期望值现场派生（页大小/几何 ← 镜像 `.config` + `spec/DADAO-12 §2.2.2`，寄存器角色 ← `contract-abi §4.5`，mm/regs 布局 ← 内核源现场符号）。
2. **探针 case 覆盖（每 case 一条可达 FAIL 断言）**：
   - `F1 fork 建子进程`：`copy_process` 后子任务存在、`mm` 非空、`context.asid` 与父不同（现场读值）、子 `pt_regs` 是父的副本（`ip`/`rb1` 相等、`rd8=0` 由 `copy_thread` 设）。
   - `F2 地址空间克隆`：父映射的非零页在子侧 PA **不同**（全量复制，非共享）；共享零页两侧 PA **相同**（不复制）。
   - `F3 execve 建栈 VMA`：execve 后 `current->mm` 有且仅一个 `VM_GROWSDOWN` VMA，`vm_start`/`vm_end` 现场打印、大小 ≥ 1 页；入口 `ip`/`rb1` 已由 `start_thread` 填。
   - `F4 换页来源`：`dadao_pf_alloc_page` 不再从 RAM 顶取页（`alloc_page` 生效），`dadao_pf_find_vma` 走 `find_vma(current->mm)`（`current->mm` 非空时命中真 VMA）。
   - `F5 U-mode 入口（用户 2026-11-17 选 C）`：用户态 `trap cfx_umon, 0` ⇒ 经 `cfx_umon` user 行向量进入内核（断言 `cfx_umon_user_switch_run_mode == 2`、`cfx_umon_user_excp_vector` 已自写非 0）；帧字段与 `spec/DADAO-12 §5.2` 逐项一致——`excp_prev_run_mode == user(0)`、`excp_cause_id == 1<<0`（`CFXTRAP`）、`excp_cause_ip == trap` 指令地址、`excp_cause_info == 触发指令编码`（`immu18 = info & 0x3FFFF`，`contract-syscall §8`）；`escape cfx_umon, [excp_cause_ip, 4]` 落回 `trap` 下一条；U-mode 同步异常（页故障）走 `cfx_smon` `supv_excp_vector`（断言**不串 `umon` 帧**）。
3. **≥5 路注入**（`cp`+md5 还原 + 重建回绿）：① 不复制 `pt_regs`（子 regs 全 0）⇒ `F1` 红；② `copy_page_range` 不复制直接共享 ⇒ `F2` 红（两侧 PA 相同）；③ `execve` 不建 `VM_GROWSDOWN` ⇒ `F3` 红；④ `fault.c` 不换 `find_vma`（仍走静态窗口）⇒ `F4` 红；⑤ `cfx_umon_user_excp_vector` 不写（复位 0）⇒ `F5` 红（首帧跳地址 0，非内核代码）；⑥ 入口不保存 `excp_cause_ip` ⇒ `F5` 红（返回 IP 错）。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0（**不跑 `check-modules`**：会装共享安装根）；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-016/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/include/asm/{processor,ptrace,thread_info}.h.patch`、`components/linux/patches/arch/dadao/kernel/{process.c,Makefile,setup.c}.patch`（process.c 新建）、`components/linux/patches/arch/dadao/mm/{fault.c,Makefile}.patch`（fault.c 仅换两处占位）、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,execve?}.patch`、`components/linux/changelog.md`、`tools/linux/k4_fork_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `spec/DADAO-12 §2.2/§3.6` + `contract-abi §4.5` + `contract-syscall §8–§11` + `contract-tlb` 为准；`copy_process`/`dup_mm` 的通用逻辑不重写，只补 arch 钩子。
5. 页来源替换后**不得**再依赖 `dadao_pf_pool_*` 静态池；`dadao_pf_init()` 的池初始化改为 `alloc_page` 就绪后的零页初始化。
6. **单帧、不递归（用户 2026-11-17 选 C）**：U-mode 入口用 cg5 单帧，**不实现同 cfx 递归**（`umon` 内再进 `umon` 的 cg5→cg6 保存留 K5）；用户 syscall 在 `supv` 下处理时，后续同步异常走 `cfx_smon` 帧（不同 cfx，天然分离），不触发 umon 递归。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. **（待裁定 1）上下文切换 FP 保存范围**：`thread_struct` 是否含 `rf32–63` 决定本任务 `copy_thread`/上下文保存的字段集。选项与建议见任务 `017` 待裁定 1；本任务先按「含 RF」的**保守上界**写字段（`copy_thread` 复制的字段集与 017 一致）。
2. **（待裁定 2/3）** 本任务不涉及，见 `020`/`021`。
3. ~~（待裁定 4）U-mode 异常入口~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环并入本任务 + `017`——只做「用户 syscall → `cfx_umon` user 行 + U-mode 同步异常 → `cfx_smon`」的路由与帧，**单帧、不递归**；「同 cfx 递归 / cg5→cg6 保存」留 K5。本任务目标 5/6/7 与验收 `F5` 已按此落地。

## 审阅记录

（待填）
