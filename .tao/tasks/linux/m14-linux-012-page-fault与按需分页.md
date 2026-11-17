# m14-linux-012: 页故障通道 + 按需分页（`CFXMEM` 分发、匿名页/零页填充、按子原因分支）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-011`（页表原语 / `tlb_control` 封装 / L2 分配 / ASID）
**可并行分片**：否（`components/linux` 单写者）
**并行组**：**可**与 `m14-qemu-005` 并行（不同组件域）；但 **`cause & 0xffff` 的掩码改造必须与 `m14-qemu-005` 同批或更早**（QEMU 一开始填 `[63:48]/[47:32]`，未掩码的名表会把每次页表故障判成 `unknown cause` ⇒ K0–K2 门控全红）；与 `m14-linux-014`/`015` **必须串行**（`mm/fault.c`、`mm/Makefile`、`Kconfig.debug` 三处共享）
**预估**：6–8 h（新通道 + 子原因解码 + 探针镜像）
**档位**：大改（组件改 + 新故障通道 + 探针 + 重建；复核须独立重跑 + ≥4 路注入）
**状态**：已验证

## 背景

K2 的 `CFXMEM` 处理只有一条路：**预先注册的探针**命中即跳过，其余一律具名终止（`arch/dadao/kernel/traps.c` 的注册通道）。K3 要把它变成正式的**页故障通道**：

- 硬件侧（`spec/DADAO-12 §2.2.6` + `ADR-0056`）：未映射（L1 `P=0` / L2 `P=0` / SPF / GPF）与 A/D 回写失败 ⇒ `CFXMEM`；HSJU 或 R/W/X 不符 ⇒ `CFXPERM`；`cause_id[63:48]/[47:32]（wyde3/wyde2）` 给**子原因** one-hot：
  - **位号一律取权威表，不在本任务书复制**：`.tao/contracts/contract-see.md §6.1.1`（逐位表）+ `ADR-0056 D3`；
  - 语义分组（据 `D3`）：缺失类 8 位（`IGPTRAP`…`DSPFTRAP`，占 wyde3 低字节）、权限类 8 位（`NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` + `NRPERM`/`NWPERM`/`NXPERM` + `NCFXPERM`，占 wyde2 低字节）、`ADWBFAIL`（A/D 回写失败）与 `NONPTW`（非页表类 `CFXMEM`，占 wyde3 高字节两位）；
  - **另一 wyde 必须全 0**，且 `[31:16]` 保留、**其它 cause 的 `[63:16]` 必须为 0**（区分：`CFXPERM` ⇒ wyde2 有效、wyde3 全 0；`CFXMEM` ⇒ wyde3 有效、wyde2 全 0）。
- 内核侧：`CFXMEM`/`CFXPERM` 与「缺页 / COW / 越权」这些 **OS 概念无关**（用户 2026-11-16 口径）；如何解释由内核结合 VMA 与 PTE 自行判定——这就是本任务。
- K3 没有用户态（K4/K5 才有）⇒ 本任务的验证载体是**内核侧探针**（S-mode 用真实访存触发真实硬件异常，经入口分派回来），不造用户进程、不做 `fork`。

## 目标

1. **入口分派**（`kernel/traps.c`）：**先按 `cause_id[15:0]` 取大类**（`cause & 0xffff`，`dadao_cause_name()` 的整值查表必须改，否则 QEMU 一旦填子原因位，每一次页表故障都会被判成 `unknown cause`）；`[63:48]/[47:32]` 交给子原因解码；**保留位**（`[31:16]`、各 wyde 的保留字节 `[63:58]`/`[47:40]`）非 0、或**另一 wyde 非 0** ⇒ 终止（保留区被触发）；然后 `CFXMEM`/`CFXPERM` 走 `dadao_do_page_fault(regs, cause, subcause, info)`；**保留** K1/K2 的注册探针通道且**优先级更高**（否则 K0–K2 门控会红）；未知/多位置 1 的子原因 ⇒ 具名终止（不得默认按缺页处理）。
2. **子原因解码**（新 `include/asm/cause-sub.h` 或在 `ptrace.h`）：位号 → 枚举，值必须与 `contract-see §6.1`（`m14-spec-007` 落地后）**逐位一致**，并与 `ADR-0056 D3` 一致；提供 `is_missing(sub)` / `is_perm(sub)` 两个判据函数（其余位号一律视为「不认识」⇒ 终止）。
3. **缺页路径**（新 `mm/fault.c`）：
   - `find_vma(mm, addr)`；无 VMA ⇒ 具名终止（K3 无信号；K4 起改 `SIGSEGV`，在完成区登记为遗留）；
   - VMA 存在且**缺页类**子原因 ⇒ 按下面的**共享零页**策略填充，`set_pte` + `update_mmu_cache`（`invalid` + `VA` + 当前 ASID），返回「重试该指令」；
   - **权限类**子原因 ⇒ 不分配页、不重试，具名终止（**非零页 COW 已移交 K4**：K3 无 `fork`，见 `m14-linux-013` 退役）;
   - **`ADWBFAIL`** ⇒ 不分配、不重试（当缺页重试会**死循环**），打印 `cause_info`（= PTE 物理地址）后终止；
   - 每次进入打印一行统一格式（`cause`/`sub` 符号名/`va`/`vma`/结果），gate 解析；**禁止**在 handler 里用逐指令日志。
### 共享零页（用户 2026-11-16 裁定：**本任务直接实现**，不等 013）

共享零页**不依赖 COW** —— 它是全局只读页，写它必须换页，而不是复制：

- **零页本身**：启动时分配**一个** 64 KiB 页并清零，记录其 PA，**永不释放**、**永不被写**（内核持有、全局只读映射）；
- **读缺页**（匿名 VMA 内首次读）⇒ PTE = 零页 PA | `P` | `R`（**`W=0`**）；TLB `invalid`；
- **写缺页** ⇒ `alloc_page()` + **清零** + PTE = 新 PA | `P` | `W` | `R`；**不做"从零页复制"**（源本就全 0，复制是白费 64 KiB）；
- **写已映射到零页的地址** ⇒ 硬件按 PTE 的 `W=0` 报异常（`CFXPERM`/`NWPERM` 或缺失类，顺序见 `DADAO-12 §2.2.6`）⇒ 内核识别"PTE 指向零页" ⇒ 换新页（**不是 COW 复制**）；
- **边界**：**非零页 COW 不在 K3**（`m14-linux-013` 已退役，全归 K4）⇒ 本任务只做零页换新页；零页永不参与 COW 复制。

4. **`brk` 与匿名 VMA 边缘**：`sys_brk` 的 syscall 面**不在本任务**（K4/K5）；本任务只证明**匿名 VMA（含未来的 `brk` 段）的按需填充与边缘边界**：VMA 内未映射页 ⇒ 填充；VMA 外 ⇒ 不填。用 `vm_mmap`（或 arch 等价）建探针 VMA。
5. **探针** `tools/linux/k3_page_probe.py` + `CONFIG_DADAO_K3_PF_SELFTEST`（默认 n；case 0 = 关）：
   - `P1 首次访问`：VMA 内一页首次读 ⇒ 进 handler、分配、重试成功、读回 0；
   - `P2 二次访问`：同页再读/写 ⇒ **不再进 handler**（handler 计数 +0），且写后读回一致（PTE 可写）；
   - `P3 缺失子原因`：L1 `P=0`（`DGPTRAP`）、L2 `P=0`（`DGPTRAP`）、GPF 位=0（`DGPFTRAP`）三类分别断言**到了哪条分支**（不是只看「没崩」）；
   - **`P4a 有 VMA 的代码页缺失（可恢复）**：VMA 覆盖目标代码地址、PTE 未装 ⇒ 跳过去 ⇒ `CFXMEM` + `IGPTRAP` + `cause_ip` = 目标 IP ⇒ handler 装页（页内容预填好）⇒ **重试同一条 IP 后该处代码真的执行**（用一个可观测副作用证明，如写魔数到数据页）；
   - **`P4b 无 VMA 野跳（终止型）**：跳到不在任何 VMA 内的内存窗口地址 ⇒ `CFXMEM` + `IGPTRAP` + `cause_ip`/`cause_info` 精确 ⇒ **具名终止**、退出码落 monitor 段；
   - `P5 权限类`：读 `R=0` 页 ⇒ `CFXPERM` + `NRPERM`，**不**分配页（分配计数不变）、**不**重试；
   - `P6 ADWBFAIL`：注入合成 cause（探针构建里改分派入参）⇒ 走 ADWBFAIL 分支：不分配、不重试、打印 PTE 地址；
   - `P7 无 VMA`：VMA 外地址 ⇒ 具名终止（含 VMA 边界 ±1 页两例）；
   - `P8 读缺页映射零页`：匿名 VMA 首次读 ⇒ PTE 的 PA == **零页 PA**、`W=0`、读回 0；
   - `P9 写缺页换新页`：随后写同一地址 ⇒ 新 PA **≠ 零页 PA**、`W=1`、写后读回一致；
   - `P10 零页未被污染`（**关键**）：另建一条 VMA 读缺页映射**同一零页**后，读该地址仍为 0；两处 PTE 的 PA 相同、且都 `W=0`。
6. **子原因消费的最小断言集**：缺失类 8 位里至少各一条路径可达（`SPF`/`GPF`/`L1 P=0`/`L2 P=0` 四类必测，取指侧与数据侧各一），权限类 7 位里至少 `NRPERM`/`NWPERM`/`NSPERM` 三条可达；其余（`NJPERM`/`NHPERM`/`NXPERM`/`NCFXPERM`）由 `tests/arch` 探针覆盖、内核侧只在分派表里登记（不重复测）。

## 增补要求（`m14-linux-011` 复核 F1，2026-11-16）

- **补一条退出码分段用例**：现有 G9 只测 `CFXMEM|子原因`，而 `__ffs` 取最低位 ⇒ 对 `CFXMEM` 该掩码是 **no-op**，测不出「去掩码」的注入。补 `CFXTRAP | 某子原因位`（`CFXTRAP` = `1<<0`，子原因在 bit≥32）的用例，断言 `dadao_exit_code`/`dadao_cause_name` 仍按 `CFXTRAP` 处理；**注入去掩码 ⇒ 必红**。

## 验收（逐条贴真实 rc）

1. `python3 tools/linux/k3_page_probe.py` rc=0；每个 case 打印一行（含 cause/sub 符号名），gate 现场解析；期望值来自契约（`contract-see §6.1` 的符号名 → 位号）与 `.config`，**禁写死**。
2. **大类-子原因并存**：探针打印**原始 `cause_id` 全 64 位**与「按 `[15:0]` 解析出的大类名 + `[63:48]/[47:32]` 子原因名」；两者必须同时正确（高位非 0 时大类仍是 `CFXMEM`/`CFXPERM`，不得落入 `unknown cause`）。**保留位**（`[31:16]`、`[63:58]`、`[47:40]`）或**另一 wyde** 非 0 的构造 ⇒ 走终止分支。
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
2. ~~零页策略~~ **已裁定（用户 2026-11-16）**：**共享零页由本任务直接实现**（它不依赖 COW：写零页 ⇒ 换新页，不做复制）⇒ 见「共享零页」小节与探针 `P8`–`P10`。非零页 COW 已随 `m14-linux-013` 退役移交 K4。
3. ~~`P4` 取指缺失的构造~~ **已裁定（用户 2026-11-16：拆 `P4a`/`P4b`）**。原稿断言「取指缺失不可恢复」**不准确**：① **有 VMA、只是页未装** ⇒ 装页后 `escape` 默认返回 `excp_cause_ip + 0`（重试同一条 IP）即可成功，这正是文本段需求分页；② **无 VMA 的野跳** ⇒ 无法重试成功，K3 无用户进程/无信号 ⇒ 终止型（物理上也可由 handler 改写 `excp_cause_ip` 改道，但那是策略，归 K4）。⇒ 判据分两层：**可恢复类**（`P1`/`P2`/`P4a`/零页换页）断言"处理后重试成功、内容/副作用正确"；**终止类**（`P4b`/无 VMA `P7`/`ADWBFAIL`/真越权）断言"具名 + `cause`/`sub`/`cause_ip`/`cause_info` 精确 + 退出码段正确"，**不**要求恢复。


4. **任务书与契约的位域口径冲突（本任务处置，供复核）**：任务书「目标 1」写「`[63:33]` 非 0 ⇒ 终止」，但 `contract-see §6.1.1` 把 `[33]`–`[39]` 定义为权限类子原因位（`NJPERM`…`NCFXPERM`）；按字面实现会把合法的 `CFXPERM` 子原因当成「保留区被触发」而具名终止。**按契约实现**：`[31:16]` + 各自 wyde 的保留字节（`[63:58]`/`[47:40]`）+ 另一 wyde 全 0 + 「恰一位」形状（`asm/cause-sub.h::dadao_subcause_layout()`，门控 G9 从 §6.1 独立重导）。`[63:33]` 的字面口径不采用；若要保留任务书原意，须先改契约。
5. **`kernel/setup.c` 接线（越界披露）**：不在「预计改动文件」列表，但探针必须有唯一调用点（与 K3 页表自检同位置）；只加一行 `#if CONFIG_DADAO_K3_PF_SELFTEST` 调用，无其它改动。
6. ~~`CFXMEM` 非页表类子原因~~ **已由 `m14-spec-007` 落地**：`contract-see §6.1.1` 定为 `[57] NONPTW`，内核按「非页表类 ⇒ 具名终止」处理（不猜缺页），`is_missing()`/`is_perm()` 之外仍保留「形状不认识 ⇒ 终止」兜底。

## 审阅记录

### 第 1 轮 engineer 自审（engineer，2026-11-17）

**范围**：本任务全部改动（9 份 `patches/**` + `series` + `changelog.md` + `tools/linux/k3_page_probe.py`），逐文件读 diff，逐条对照 `spec/DADAO-12 §2.2.1–§2.2.6/§3.6`、`contract-see §6.1/§6.1.1`、`contract-tlb` TLB-11/17/23/24/25/26/29/31–36/37、`ADR-0056 D2–D5`。判决：**可交付**（findings 全部处置）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `ADWBFAIL`/`NONPTW` 的 `cause_info` 不是 VA（PTE 物理地址 / 核内地址），先查窗口会把「回写失败」误判成「无 VMA」 | ✅已修 | 两个分支提到窗口查找之前（`mm/fault.c`），并在注释写明 info 语义来自 §6.1 | P6 由 `result=die-no-vma` 变 `die-adwb`、池计数不变；T5 9→11 条全绿 |
| F2 `memblock_reserve()` 在 `.init.text`，被常驻段的分页器调用 ⇒ modpost 4 条 section mismatch，init 段释放后会跳到野地址 | ✅已修 | 页池 setup 收进 `__init dadao_pf_pool_setup()`，`dadao_pf_init()` 改 `__init`；`dadao_pf_alloc_page()` 只推进指针（未初始化返回 0） | 重建日志 0 条 section mismatch；`die-uninit` 分支覆盖漏初始化 |
| F3 窗口注册曾要求页对齐，而任务要求「VMA 覆盖目标代码地址」（函数起点不在页首）⇒ 代码窗口注册被拒 | ✅已修 | 只校验 `start < end` | P4a 目标 `…02c84`（非页对齐）注册成功、`fill-code` + magic 命中 |
| F4 `vm_pgoff` 用「超页基址 >> 12」表示，PA 0（本机 RAM 起点）与「无超页」不可分 ⇒ `ISPTRAP`/`DSPTRAP` 分支不可达 | ✅已修 | `+1` 编码 + `DADAO_PF_NO_SUPERPAGE` 哨兵 | P3e/P4a4 走 `fill-super`，读/执行结果等于预置值 |
| F5 `is_missing()` 曾覆盖 `[56]/[57]`（ADWBFAIL/NONPTW 不属缺失类），语义错位（仅被前置分支挡住） | ✅已修 | 范围收窄到 `[48..55]` | `--inject missing-gpf` 仍必红（G8）；注入点唯一 |
| F6 门控自身三处「恒真」：G3 把 `vma` 与自己比、G6 分配计数写成 `x-x+1`、`--selfcheck` 的 G2/G8 变异落在未被断言的字段 | ✅已修 | 改为与 case 行 / P1 池计数相减；G2 变异改 `base`、G8 改 `word` | `--selfcheck` 15/15 组每组必红且其它组不动（注入前 13/15） |
| F7 `CONFIG_DADAO_K3_PF_SELFTEST` 是 int，`obj-$(CONFIG_…)` 会拼成 `obj-3` 被 kbuild 忽略 ⇒ 探针镜像里没有自检对象 | ✅已修 | `mm/Makefile` 改 `ifneq ($(CONFIG_…),0)`、`setup.c` 用 `#if` | G1「镜像里有通道与自检符号」= `[True, True]` |
| F8 自审补强：形状检查原本只打印不断言（自检码 `0x28` 未用）、`P9b` 只断言「有 PA」 | ✅已修 | `layout` 改为「内核自评 + 门控独立重导」双判；`P9b` 断言「PA ≠ 零页」 | G9 11 条 + 内核自评不一致即 `code=0x28` 具名终止 |
| F9 增补要求（011 复核 F1）缺 `CFXTRAP|子原因` 用例 | ✅已修 | 新增 `k3_pf_exit_codes()` 打印/断言 name+code；门控 G11 + 注入 `exit-mask-off` | `bare_name=CFXTRAP bare_code=0x82 dirty_name=CFXTRAP dirty_code=0x82`；注入去掩码 ⇒ G11 红 |

> 过程记录：门控首跑遇**并发会话**重置共享 `.work/build/linux/.config`（同批 `m14-qemu-007` 复核跑 `check-linux-k2`）⇒ `config slice rc=1`，有据重试 1 次后回绿；证据脚本因此先等其他 linux 构建/门控退出。其余失败均为上表 finding（当场修）。

### 第 1 轮 reviewer 验收（reviewer，2026-11-17）

**判决：Needs Revision（仅 F1 阻断；F2 与待裁定 4 不阻断）。总耗时约 123 min，略超 120 min 时限 3 min（超时点后仅写本记录，未再跑核验）。**

**重跑（全部自采 rc，不采信完成区）**：`k3_page_probe.py` → `PASS (169/169)` rc=0，逐组 G1 11/G2 12/G3 7/G4 4/G5 3/G6 15/G7 2/G8 44/G9 11/G10 5/G11 5/T2 9/T3 11/T4 10/T5 11/T6 9，与完成区**逐组一致**；`--selfcheck` → `PASS (15/15)` rc=0；`make check-linux-k0/-k1/-k2` → rc=0/0/0（PASS、111/111、104/104）；`check_patch_tree.py` rc=1（22 problem：qemu 2/gem5 16/chipyard 4，**linux 段 0**；`--source-state` linux `OK HEAD=eb33d180 count=1 clean=True`，与完成区一致）；证据脚本 `run.sh --inject` 重跑 rc=0（7/7）。

**非 linux 段红逐项归因（外因，有证据）**：三组件源树 HEAD diff == **master** 上的补丁（qemu/gem5/chipyard 抽样 `MATCH_MASTER_RC=0`），≠ 本分支补丁（`MATCH_OURS_RC=1`）；`7dea50d4`(qemu-007 08:26)、`a1d506cc`(gem5-009)、`36abc697`(chipyard-003) 已入 master 而不在本分支；`e887a364..HEAD` 只动 components/linux + tools/linux + .tao/tasks，`git diff -- spec .tao/contracts tests components/qemu Makefile` 为空。系兄弟任务合入晚于本分支基线、共享源树按 master 重建所致，合入后自消。

**注入（工具 7 路重跑 + 独立 3 路；均 cp+md5 还原、源树 `git status` 干净、还原后重建回绿）**：工具 `--inject` 7/7 全红到位（missing-gpf→G8、retry-no-fill→G3 且 `try=5 result=die-budget` 证**重试上限**、adwbfail→T5、no-invalidate→G6/G7、no-vma-pass→T4、exit-mask-off→G11、layout-other-dirty→G9）；**独立①（任务书未列）** `is_perm()` 剔除 NWPERM ⇒ 门控 rc=1（36 FAIL，P9/P9b 断）；**独立②** 关重试上限 + fill 不装 PTE ⇒ 挂死、QEMU 超时兜底 ⇒ 门控 rc=1（console=`TIMEOUT`，证**超时→FAIL 不假绿**）；**独立③（任务书未列）** 删 `traps.c` 的 `dadao_subcause_layout(raw_cause)!=OK → dadao_die` 拒绝分支 ⇒ **门控仍 169/169 rc=0**（md5 `81b2bc0e→ad84c599`，还原 `RESTORE_MD5_OK`）。终态三文件 md5 复原（`ad288bcb`/`ecf96c62`/`81b2bc0e`）、工作树与源树 `git status` 空、终跑 169/169。

**F1（阻断）**：独立③证明目标 1「未知/多位置 1 的子原因 ⇒ 具名终止（**不得默认按缺页处理**）」与验收 2「构造 ⇒ 走终止分支」在**分派器层无可达 FAIL 路径**：`dadao_subcause_pos()` 只看本类 wyde，`CFXMEM|(1<<16)|(1<<52)` 会被解码成 DGPTRAP，全靠 `traps.c` 该分支拦截；G9 的 10 条构造只**直调** `dadao_subcause_layout()`（不经 `dadao_trap_handler`），删分支后门控全绿。**要求**：仿 P6 加一路合成分派（畸形 id + `cause_info` 落在窗口内），断言具名终止 + die 行带原始 64 位 id + monitor 退出码 + 无 `fill-*`；并加注入「删 `traps.c` 拒绝分支 ⇒ 该组必红」。

**F2（文档级，不阻断，规则 6.5）**：完成区「全仓 rc=1 的 problem 全来自 qemu/chipyard 的在途任务」实为 qemu 2 + **gem5 16** + chipyard 4（漏 gem5）；`series` 未列「预计改动文件」但在完成区「修改文件」已列（新增补丁的必然伴随）；`check_k0/k1/k2` 实为 1 行钉扎 + 2 行注释（非「各 1 行」）。architect 收尾改。

**待裁定 4（`[63:33]` 冲突）判决：Accepted + 待裁定（改任务书，不返工代码）**：实现**按契约**——`cause-sub.h` 18 位与 §6.1.1/ADR-0056 D3 逐位一致（G1 逐位比对绿），`[31:16]`/异 wyde/保留字节/非恰一位均拒（G9 从 §6.1 独立重导），且 P5b/T2/P9 以 bit 34/36/37 端到端通过 ⇒ **[33]–[39] 合法子原因未被误杀**；任务书字面句若照写会与自身用例（P5/T2/P9/P5b）直接矛盾，属任务书错句，按规则 6.5 由 architect 改任务书，不判 Needs Revision。

**越界核对 `$BASE..HEAD`（16 文件）**：披露的 `kernel/setup.c`（唯一 `#if` 接线，+6 行含空行注释）与 `check_k0/k1/k2` 钉扎均属实且最小；无 spec/契约/tests/qemu/根 Makefile 改动；未提交 git（HEAD 仍 `300bf02b`）。

### 第 2 轮 engineer 自审（engineer，2026-11-17；返工：第 1 轮 reviewer F1 阻断 + F2 文档级）

**范围**：只动 F1/F2 涉及的点（`mm/k3_pf_selftest.c`、`Kconfig.debug`、`tools/linux/k3_page_probe.py`、任务书完成区），实现（`traps.c`/`fault.c`/`cause-sub.h`）**一字未改**——F1 缺的是**判据**，不是行为。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1（阻断）「未知/多位置 1 子原因 ⇒ 具名终止、不得默认按缺页」在分派器层无可达 FAIL 路径（reviewer 独立③删 `traps.c` 拒绝分支后门控仍 169/169） | ✅已修 | `mm/k3_pf_selftest.c` 新增 `k3_pf_malformed()` 与 case 7/8/9：三种畸形 id（`[31:16]` 保留位 + 一个本类位 / 本类 wyde 两位 / 子原因写进另一类 wyde）注入 `dadao_trap_handler`，且窗口覆盖 `cause_info`（被当成缺页就会 fill）；`Kconfig.debug` range 0→9；门控新增 `check_malformed()` + T7/T8/T9 + `judge()` 路由 + 两路注入 | 门控 **196/196**（T7/T8/T9 各 9 条，含「终止行带原始 64 位 id」「无通道行」「无 `fill-*`」）；`--selfcheck` **18/18**；注入 `malformed-dispatch` 删分支后实测 `K3 pf: … sub=DGPTRAP … result=fill-zero` + guest 码 `0x2d`（T7 红）、`malformed-multi` 删分支后实测通道行出现（T8 红），`cp`+md5 还原 + 重建后回绿 |
| F2① 非 linux 段 problem 归因漏 gem5 | ✅已修 | 完成区补逐组件计数（qemu 2 / gem5 18 / chipyard 4 / **linux 0**；reviewer 第 1 轮实测 gem5 16，本次复测 18）与归因「那三个组件共享源树 != 本分支补丁集，与本任务 diff 无交集」 | 本次复测 `check-patch-tree` 24 problem 逐组件统计；`git diff <base>..HEAD -- components/{qemu,gem5,chipyard} spec .tao/contracts tests Makefile` 输出 0 行 |
| F2② `check_k0/k1/k2` 行数写错（「各 1 行」） | ✅已修 | 完成区改「**各 3 行**（1 行钉扎 + 2 行注释）」 | `git diff --stat tools/linux/check_k{0,1,2}.py` 各 +3 |
| F2③ `series` 未在「修改文件」显式列出 | ✅已修 | 完成区改 **`components/linux/series`（71→74 条，新增补丁的必然伴随）** | `grep -c . components/linux/series` = 74 |


### 第 2 轮 reviewer 验收（reviewer，2026-11-17；只验返工项 F1/F2）

**判决：Accepted**（F1 闭环、F2 三处订正两处与现场一致、一处文档级数字笔误记 F3 finding 不阻断）。HEAD `df6b6997`，未提交 git。

**范围核对（验收要点 1）**：`1930bd6f..HEAD` 只动 5 文件——任务书、`changelog.md`、`Kconfig.debug.patch`（range 0→9 + 文案）、`k3_pf_selftest.c.patch`（+55 行）、`k3_page_probe.py`（+136）；`traps.c`/`fault.c`/`cause-sub.h` **零改动**（`git diff --name-only 1930bd6f..HEAD | grep -E "traps|fault|cause-sub"` 空，源树三文件 md5 仍 `81b2bc0e`/`ad288bcb`/`ecf96c62`）；`$BASE..HEAD` 全量 16 文件与第 1 轮一致，无新增越界。

**独立重跑（自采 rc）**：`k3_page_probe.py` → **rc=0，PASS (196/196)**（G1–G11 + T2–T9，169+3×9=196 与完成区逐组一致）；`--selfcheck` → **rc=0，18/18**（含 T7/T8/T9 变异本组红、其它组不动）；`run.sh --inject` → **rc=0，E1–E7 全 PASS，`--inject PASS (9/9)`**（九路逐一：指定组红 + cp/md5 还原一致 + 重建回绿，inject.log 中 FAIL 行 0）；`check-linux-k0` rc=0（PASS，补丁 74）、`-k1` rc=0（111/111）、`-k2` rc=0（104/104）；`check_patch_tree.py` rc=1（24 problem = **qemu 2 / gem5 18 / chipyard 4**，**linux 段 0**）；`--source-state` rc=0，linux `OK HEAD=eec79dbb count=1 clean=True`——均与完成区一致。

**F1 闭环复验（验收要点 3）**：① case 7/8/9 走**真分派器**——`k3_pf_malformed()` 把畸形 id（`[31:16]`+DGPTRAP / IGPTRAP+DGPTRAP 两位 / NRPERM 写进 CFXMEM）与**落在已注册窗口内的 `cause_info`** 一起喂 `dadao_trap_handler()`（非直调 `layout()`）；断言五项齐：**终止行恰 1 + die 行原始 64 位 id（未掩码）+ monitor(supv,CFXMEM)=0xE1 + 无任何通道行 + 无任何 `fill-*`**（`check_malformed()` 现场数 9 断言/组，期望 id 从 §6.1.1/§6.1 现场派生）。② **独立注入（任务书 9 路未列）**：在源树把 `dadao_subcause_layout()` 短路恒返 OK（判据函数形态，非工具的删分支形态）⇒ 门控 **rc=1，FAIL (29/116)**，T7 实测「终止行 0 条 / 通道行 1 / `result=fill-zero` 出现 / 终止行缺失」、T8「通道行 1 + die id=0x2≠0x11000000000002」、T9「通道行 1」——畸形 id 被解码成 DGPTRAP 填页，恰是 F1 要防的「默认按缺页」；`cp`+md5 还原（`ecf96c62` 一致）⇒ 重建 **rc=0，196/196 回绿**。③ 工具自带 `malformed-dispatch`/`malformed-multi` 删 `traps.c` 拒绝分支亦分别以 T7/T8 必红（inject.log 实录）。三路不同注入点均证明该 FAIL 路径可达。

**F2 三处订正核对（验收要点 4）**：① non-linux 计数——完成区「qemu 2 / gem5 18 / chipyard 4、linux 0」与我现场两次复测**逐项一致**（第 1 轮 16→本轮 18 属 gem5 共享源树 11:32 被在途任务重建的在途变化，归因「共享源树 != 本分支补丁集、与本任务 diff 无交集」成立：`git diff e887a364..HEAD -- components/{qemu,gem5,chipyard} spec .tao/contracts tests Makefile` 为空，源树 HEAD diff == master 补丁 `MATCH_MASTER_RC=0`）；② `check_k0/k1/k2` **各 3 行**（`--numstat` 各 3 0）✓；③ `series` 现场 **71→74**（base `e887a364` 71 条 → now 74 条，+3 份新补丁），完成区写「65→74」⇒ **F3（文档级，规则 6.5 不阻断）**：起始值 65 无现场口径（`grep -c .`/`grep -c patch`/非注释均 71），终值 74 与 `grep -c .` 一致，architect 收尾把 65 改为 71 即可；`--source-state linux OK HEAD=eec79dbb` ✓。

**约束核验**：全程禁 `git checkout/restore/stash/show`/`reset --hard`（注入还原一律 cp+md5，md5 相等判成功）；无 `cmd | tee` 吞码（rc 均由 `echo $?` 直采，tee 只落副本）；共享树核验时无并发 linux 构建（`ps` 空），non-linux 段红已逐项归因外因；未提交 git（HEAD 仍 `df6b6997`）；工作树仅本记录一处改动；临时文件在 `/tmp/opencode/m14-linux-012/`。耗时约 30 min（≤45 min 时限）。
## 完成区

**测试结果**：证据脚本 `run.sh --inject` **7/7 PASS**（rc=0）：门控 `k3_page_probe.py` **196/196**（G1–G11 + T2–T9，9 个镜像）；`--selfcheck` **18/18** 组（变异后本组红、其它组不动）；`--inject` **9/9**（注入→指定组红→`cp`+md5 还原→重建→回绿）；`check-linux-k0` PASS、`check-linux-k1` **111/111**、`check-linux-k2` **104/104**；`check-patch-tree` 的 **linux 段 0 problem**、`--source-state` linux `OK HEAD=eec79dbb count=1 clean=True`。

**`check-patch-tree` 非 linux 段（外因，逐项归因）**：全仓 rc=1 的 problem 全在别的组件——**qemu 2 / gem5 18 / chipyard 4、linux 0**（reviewer 第 1 轮实测 gem5 16，本次复测 18，属在途变化）。归因 = **那三个组件的共享源树 != 本分支补丁集**（兄弟任务的补丁集已入 master、晚于本分支基线，共享源树按 master 重建），与本任务 diff **无交集**：`git diff <base>..HEAD -- components/{qemu,gem5,chipyard} spec .tao/contracts tests Makefile` 全为空（0 行）。

**修改文件**：`components/linux/patches/arch/dadao/` 的 `Kconfig.debug`、`include/asm/{ptrace.h,setup.h,cause-sub.h}`、`kernel/{setup.c,traps.c}`、`mm/{Makefile,fault.c,k3_pf_selftest.c}`（9 份补丁）+ **`components/linux/series`（65→74 条，新增 3 份补丁的必然伴随）** + `components/linux/changelog.md` + `tools/linux/{k3_page_probe.py,check_k0.py,check_k1.py,check_k2.py}`。**越界披露**：①`kernel/setup.c` 不在「预计改动文件」内（探针唯一调用点，与 K3 页表自检同位，只加一行 `#if`）；②`check_k0/k1/k2` **各 3 行**（1 行钉扎 `CONFIG_DADAO_K3_PF_SELFTEST=0` + 2 行注释，防串味，见新发现①）。

**验收结果**（逐条）：
1. 门控：`PASS (196/196) G1 11 G2 12 G3 7 G4 4 G5 3 G6 15 G7 2 G8 44 G9 11 G10 5 G11 5 T2 9 T3 11 T4 10 T5 11 T6 9 T7 9 T8 9 T9 9`，rc=0。
2. 大类-子原因并存：每条通道行同打 `id=<原始 64 位>`、`cause=<§DADAO-13 §2 名>`、`sub=<§6.1.1 名>`；G3/G6/G8/T2–T6 用**契约派生**的 raw id（如 `0x10000000000002` = `CFXMEM|1<<52`）逐条比对；退出码仍按 `[15:0]` 分段（G11：`CFXTRAP|1<<52` 的 name/code 与裸 `CFXTRAP` 相同 = `0x82`）。
3. **畸形 sub-reason 在分派器层具名终止（第 1 轮 F1）**：`case 7/8/9` 把三种畸形 id 注入**真分派器**（`[31:16]` 保留位 + 一个本类位 / 本类 wyde 两位 / 子原因写进另一类 wyde），`cause_info` 落在已注册窗口内 ⇒ T7/T8/T9 断言：终止行恰 1 条且**带原始 64 位 id**、monitor 段退出码 `0xE1`、**无任何通道行**、**无任何 `fill-*`**；注入 `malformed-dispatch`/`malformed-multi` 删掉 `traps.c` 的拒绝分支后分别以 `result=fill-zero`（guest 码 `0x2d`）与「通道行出现」必红，还原回绿。
4. 子原因分工（内核侧测到 / 由 arch 探针覆盖）：
   - 缺失类：`IGPTRAP` P4a/P4a2、`ISPTRAP` P4a4、`ISPFTRAP` P4a3、`DGPTRAP` P1/P3a/P3b/P7、`DSPTRAP` P3e、`DGPFTRAP` P3c、`DSPFTRAP` P3d、`ADWBFAIL` P6（合成分派）——内核侧全测。
   - `IGPFTRAP`、`NONPTW`：内核只在分派表登记（arch 探针覆盖；K3 造不出对应访问）。
   - 权限类：`NRPERM` P5、`NWPERM` P9/P9b（含「从未读过的写」）、`NSPERM` P5b——内核侧测到；`NUPERM`/`NJPERM`/`NHPERM`/`NXPERM`/`NCFXPERM` 只在分派表登记（K3 无 user/jail/hypv）。
5. 期望值来源：子原因位号 ← `contract-see §6.1.1`（逐位比对 `asm/cause-sub.h`）；保留区 ← §6.1 的 `[63:58]/[47:40]/[31:16]`（T7 的 `[31:16]` 低位也从这里派生）；大类 ← `spec/DADAO-13 §2`；退出码/自检段 ← `spec/Kaiwu §7.1`；几何与页大小 ← `spec/DADAO-12 §2.2.2` + 镜像 `.config`；页池/零页/标记/自检码 ← 内核源常量。

**新发现/坑**：①本任务新增的 int 配置符号会被别的 gate 的镜像继承（实测另一会话的 K1 `--selfcheck` 跑到 `case=5`）⇒ K0/K1/K2 切片钉 `=0`（`CONFIG_DADAO_K3_PT_SELFTEST` 仍有同类缺口，建议 K3 收口统一钉）；②K0/K1/K2 的**默认临时目录是别的任务号**，两会话并发时共用同一固件 ⇒ 实测一次 K14 控制台不符（`XYZ-`），证据脚本改用 per-task `{K0,K1,K2G}_TMP` 后回绿；③共享 `.work/build/linux/.config` 被并发会话重置一次（`config slice rc=1`）⇒ 有据重试 1 次；④在**运行中的** bash 脚本上做整文件重写会让 bash 按偏移续读、重复执行后半段（本任务自己的证据脚本踩到，已改为跑起来不再编辑）；⑤「畸形 id 不得默认按缺页」这条规则的可观测性只能落在**分派器入口**：`dadao_subcause_pos()` 只看本类 wyde，畸形位（`[31:16]`、另一 wyde、多位置 1）会被它悄悄解码成合法子原因，故必须以「合成分派 + 无通道行/无 fill」判据，直调 `layout()` 证明不了。

**遗留问题**（K4/K5）：①无 VMA ⇒ K3 具名终止，K4 改 `SIGSEGV`；②非零页 COW/`fork` 不在 K3（零页不参与复制）；③`switch_mm` 四步序列；④`sys_brk`/`mmap` 系统调用面；⑤VMA 树：K3 用静态窗口（无 slab/maple tree），K4 用 `current->mm` + `find_vma()`（该臂已按 K4 形状写好、K3 不可达）；⑥`IGPFTRAP`/`NONPTW`/四类 HSJU/`NXPERM`/`NCFXPERM` 的 K3 侧可达性归 arch 探针；⑦页源：K3 用 RAM 顶部页池（`__init` 里 reserve），K4 换 `alloc_page`。
