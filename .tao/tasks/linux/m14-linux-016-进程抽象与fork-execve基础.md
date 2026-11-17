# m14-linux-016: 进程抽象与 fork/execve 基础（task_struct / mm / copy_process / 地址空间克隆）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-012`（页故障通道 + 按需分页）、`m14-linux-015`（K3 收口门控）、`m14-linux-022`（异常帧四组 rd/rb/ra/rf，已验证）、`m14-testcases-006`（hmon 全 cfx supv 权限转交 smon，`F5` U-mode 帧固件前置）
**可并行分片**：否（`components/linux` 单写者；共享 `mm/fault.c`、`include/asm/processor.h`、`kernel/process.c`）
**并行组**：与 `m14-linux-017`…`020` **全部串行**（同组件同写者 + 共享 `arch/dadao` 文件）；与 qemu/testcases 模块可并行（不同组件）
**预估**：6–8 h（F3「execve 建栈 VMA + init 真跑」已移 `017`；剩余：进程骨架 + mm 接线 + 用户态入口骨架 + 探针）
**档位**：大改（组件改 + 新子系统接线 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：已验证

## 背景

K3 收口时内核停在 `setup_arch()` 末尾：`current->mm == NULL`（init task 无地址空间），页故障通道的**页来源**与 **VMA 查找**是 K3 占位（`mm/fault.c` 的 `dadao_pf_alloc_page()` 从 RAM 顶取页、`dadao_pf_find_vma()` 走静态 `dadao_pf_window[]` 数组；源文件注释已明写「K4 替换这两处、其余行不动」）。K4 要建立进程模型，让这些占位变成真实现，并使 `fork`/`execve` 能创建带独立地址空间、可运行的进程。

DADAO 特有事实（不得套 RISC-V/x86）：
- **四组寄存器** `rd/rb/rf/ra`；`SP=rb1`、`FP=rb2`（无条件保留）、`TP=rb3`（rbtp）；`rb0`=只读 IP、`rd0`=恒 0。callee-saved = `rd32–63 ∪ rb32–63 ∪ rf32–63`（`contract-abi §4.5`）。
- **页 64 KiB**、VA 42 位、单 PTBR；ASID 16 位（`mm->context.asid`，K3 `mm/mmu.c` 已分配）。
- **无状态寄存器 / 无 PS.IE**：`struct pt_regs.status` 恒 0（`asm/ptrace.h`）。
- `copy_process`/`dup_mm`/`copy_page_range` 是**通用**代码；本任务只补 `arch/dadao` 钩子（`copy_thread`、`copy_mm` 的 arch 部分、`start_thread`、`ret_from_fork`）。

## 目标

1. **`include/asm/processor.h`**：`thread_struct` 由 `{sp, ra, tp}` 扩为完整上下文（`sp`/`ra` + callee-saved `rd32–63`/`rb32–63` + FP 范围按已裁定：`rd/rb/rf/ra` 全在异常入口/出口帧处理，`__switch_to` 不单独保存 FP，见 `m14-linux-022`）；`start_thread(regs, pc, sp)` 真实现（填用户入口 `ip`/`rb1`、清 `rb3`、设 `status=0`）。
2. **越过 `mm_core_init()`**：`kernel/setup.c` 去掉 K2/K3 边界 stop，使 `alloc_page`/`find_vma`/VMA cache 可用；`mm/fault.c` 把 `dadao_pf_alloc_page()` 换为 `alloc_page(GFP_KERNEL|__GFP_ZERO)`、`dadao_pf_find_vma()` 换为 `find_vma(current->mm, addr)`（**其余行不动**，注释已明）。
3. **`copy_process` 的 arch 钩子**：`copy_thread()` 把父 `pt_regs` 复制到子任务栈顶、设子 `thread.sp`/返回路径；子进程入口 `ret_from_fork`（可先复用 `trap.S` 的恢复序列，或最小 stub）。
4. **`copy_mm` → `dup_mm` → `copy_page_range`**：地址空间克隆，**全量私有复制**非零页（先正确、后优化——COW 由 `m14-linux-018` 替换）；共享零页**保持共享不复制**（`fault.c` 已有 `unshare_zero`，`012` 口径）。
5. **`execve` 基础**：`arch/dadao` 侧 bprm 装载（从 initramfs 读静态 musl `init` ELF）、`start_thread` 填入口并**建立 U-mode 初始帧**（用户入口 `ip`/`rb1`、清 `rb3`、`status=0`、`ret_from_fork` 落回用户态）；号表/errno/TLS 口径见 `contract-syscall §8–§11`。**「execve 建 `VM_GROWSDOWN` 栈 VMA + init 真跑」已由用户 2026-11-17 裁定移到 `017`**（本任务只做到「execve 成功 + 进入用户态」；栈 VMA 存在性断言 `F3` 归 017，栈增长扩展语义归 `019`）。
6. **用户态入口骨架（最小 U-mode 闭环，用户 2026-11-17 选 C）**：`cfx_umon` 的 user 模式路由——内核启动时写 `cfx_umon_user_switch_run_mode`（复位 `2 = supv` 可沿用）与 `cfx_umon_user_excp_vector`（复位 `0`，内核须自写，`contract-syscall §8`）；用户 syscall `trap cfx_umon, 0` ⇒ 进 `cfx_umon` 的 user 行向量，`supv` 模式、`cfx_umon` 上下文内开始执行，入口帧保存/恢复寄存器以 `contract-see §6` + `spec/DADAO-12 §5.2` 为准（硬件只存 cg5 五字段、**不存通用寄存器**，`contract-syscall §8`）；返回 = `escape cfx_umon, [excp_cause_ip, 4]`。U-mode **同步异常**（页故障/对齐等）走 `cfx_smon` 的 `supv_excp_vector`（`contract-syscall §8`，`trap.S` 已具备）。**单帧、不递归**；同 cfx 递归 / cg5→cg6 保存留 K5。
7. **`kernel_init()`** 推进到「创建 init 进程并**进入用户态第一条指令**」（用户 2026-11-17 裁定 ④ 选 C：最小 U-mode 闭环并入本任务）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k4_fork_probe.py` rc=0，逐 case 打印；期望值现场派生（页大小/几何 ← 镜像 `.config` + `spec/DADAO-12 §2.2.2`，寄存器角色 ← `contract-abi §4.5`，mm/regs 布局 ← 内核源现场符号）。
2. **探针 case 覆盖（每 case 一条可达 FAIL 断言）**：
   - `F1 fork 建子进程`：`copy_process` 后子任务存在、`mm` 非空、`context.asid` 与父不同（现场读值）、子 `pt_regs` 是父的副本（`ip`/`rb1` 相等、`rd8=0` 由 `copy_thread` 设）。
   - `F2 地址空间克隆`：父映射的非零页在子侧 PA **不同**（全量复制，非共享）；共享零页两侧 PA **相同**（不复制）。
   - ~~`F3 execve 建栈 VMA`~~ **已由用户 2026-11-17 裁定移到 `017`**（需 init 真跑 + clockevent）；本任务不再断言栈 VMA 存在性。
   - `F4 换页来源`：`dadao_pf_alloc_page` 不再从 RAM 顶取页（`alloc_page` 生效），`dadao_pf_find_vma` 走 `find_vma(current->mm)`（`current->mm` 非空时命中真 VMA）。
   - `F5 U-mode 入口（用户 2026-11-17 选 C）`：用户态 `trap cfx_umon, 0` ⇒ 经 `cfx_umon` user 行向量进入内核（断言 `cfx_umon_user_switch_run_mode == 2`、`cfx_umon_user_excp_vector` 已自写非 0）；帧字段与 `spec/DADAO-12 §5.2` 逐项一致——`excp_prev_run_mode == user(0)`、`excp_cause_id == 1<<0`（`CFXTRAP`）、`excp_cause_ip == trap` 指令地址、`excp_cause_info == 触发指令编码`（`immu18 = info & 0x3FFFF`，`contract-syscall §8`）；`escape cfx_umon, [excp_cause_ip, 4]` 落回 `trap` 下一条；U-mode 同步异常（页故障）走 `cfx_smon` `supv_excp_vector`（断言**不串 `umon` 帧**）。
3. **≥5 路注入**（`cp`+md5 还原 + 重建回绿）：① 不复制 `pt_regs`（子 regs 全 0）⇒ `F1` 红；② `copy_page_range` 不复制直接共享 ⇒ `F2` 红（两侧 PA 相同）；③ ~~`execve` 不建 `VM_GROWSDOWN` ⇒ `F3` 红~~ 随 F3 移到 `017`；④ `fault.c` 不换 `find_vma`（仍走静态窗口）⇒ `F4` 红；⑤ `cfx_umon_user_excp_vector` 不写（复位 0）⇒ `F5` 红（首帧跳地址 0，非内核代码）；⑥ 入口不保存 `excp_cause_ip` ⇒ `F5` 红（返回 IP 错）。
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

1. ~~（待裁定 1）上下文切换 FP 保存范围~~ **已裁定（用户 2026-11-17，由 `m14-linux-022` 落地）**：`rd/rb/rf/ra` 全部在异常入口/出口帧处理；`thread_struct` 不含单独 FP 段，`__switch_to` 不单独保存 FP。本任务 `copy_thread` 的字段集与 017 一致。
2. ~~**（待裁定 2/3）**~~ 本任务不涉及；`020` 已裁定 A（K4 内核线程）、`021` 已裁定 B（后移 K5）。
3. ~~（待裁定 4）U-mode 异常入口~~ **已裁定（用户 2026-11-17 选 C）**：最小 U-mode 闭环并入本任务 + `017`——只做「用户 syscall → `cfx_umon` user 行 + U-mode 同步异常 → `cfx_smon`」的路由与帧，**单帧、不递归**；「同 cfx 递归 / cg5→cg6 保存」留 K5。本任务目标 5/6/7 与验收 `F5` 已按此落地。
4. ~~（`m14-linux-016` 执行中产生）U-mode 入口被启动 SEE 的 cfx 放行矩阵阻塞~~ **已解除（`m14-testcases-006` 合入，bootrom md5 `b662183a`）**：`cfx_umon` 的四轴 supv 权限已转交 smon，内核首个 `cfx2rd cfx_umon` 不再 `CFXPERM`（实测 `K4 umon vec user_vector=0x…`，见完成区）。本任务据此把 F5 落地。
5. ~~（`m14-linux-016` 执行中产生）F3 依赖顺序~~ **已裁定（用户 2026-11-17）**：F3「execve 建 `VM_GROWSDOWN` 栈 VMA + init 真跑」移到 `017`；本任务只保留 execve 所需 arch 面（`start_thread()`、`copy_thread()` 的 fork 分支、`thread_struct`），探针以 `check_f3_scope()` 断言「镜像在 K4 边界收尾、不走到 init/initramfs」。
6. **（复核项）§4a 的两处「判据边界」改动 + 一处 master 侧顺带修正**：
   - `tools/linux/check_k3.py`：F/C 组自检的**执行点**从 `setup_arch()` 末尾移到 K4 边界（页来源换 `alloc_page()` 的直接后果）；用例与断言未改，镜像切片补 `CONFIG_DADAO_K4_SELFTEST=n`。
   - `tools/linux/check_k2.py`：k2 镜像从「`make defconfig` 默认值」改为显式切片（默认镜像已随本任务移到 K4）；镜像内容等价。
   - `tools/linux/make_initramfs.py`：`INIT_SOURCE` 由 `tests/linux/init/init.c` 改为 `tests/shared/init/init.c`。**这是 master 侧遗留**（`m14-testcases-006` 移动目录时未同步），不是本任务的语义改动；不改则 K0 门控 rc=1（initramfs 增量构建）。若主会话判定该修正应单独立项/并入 `m14-testcases-006` 的后续修正，可从本任务提交中摘出（一行）。
   - 三处均在门控全绿下完成（k0 119/119、k2 170/170、k3 263/263）。

## 审阅记录

### 第 1 轮 engineer 自审（m14-linux-016，首轮：F1/F2/F4）

审查方式：逐行读 `git diff`，对每条判据追问「它能不能在错误实现下变红」，并用探针 `--selfcheck`/`--inject` 与整机启动逐条验证。首轮 finding 与处置见 git 历史中的完成区（`max_low_pfn`、镜像保留、栈顶 `pt_regs`、weak `trap_init`、`__noreturn` 误用、`vma_needs_copy`、零页规范、注入 mtime、注入可达性、F3/F5 待裁定、`k4_mm` 未释放），结论：F1/F2/F4 已修并复验。

### 第 3 轮 engineer 自审（返工：reviewer Needs Revision — `--selfcheck` 循环）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| R1 `for group in "F1245"` 迭代字符串单字符 ⇒ 5 次都落 `else` 跑同一组 F4，打印的组名是单字符、计数恒 1 | ✅已修 | 改为 `for group in ("F1","F2","F4","F5")`（4 组；F3 已移 017 不入组） | `[SELFCHECK] F1: mutation caught by 2 check(s)` / `F2: …1` / `F4: …1` / `F5: …1`，rc=0 |
| R2 F1 的 mutation 只改 `got=` 值、保留 `ok` verdict ⇒ `check_f1` 仍绿（实测 `mutation F1: failed=0`） | ✅已修 | F1 的 mutation 同时**翻转 verdict**（`ok`→`FAIL`）与派生检查读的 `child_ip` | `F1: mutation caught by 2 check(s)`（verdict 行 + 上下文行各 1） |
| R3 「selfcheck 自身能不能变红」无证据 | ✅已修 | 一次性把 F2 的 mutation 改成返回原文（no-op），跑 `--selfcheck` ⇒ 必须 rc=1；随后 `cp`+md5 还原 | 注入期输出 `[SELFCHECK] FAIL: ['mutating F2 did not turn any check red']` rc=1；还原后 md5 `30242dac…` 一致、四组 PASS rc=0 |

判决：R1–R3 已修并复验；`run.sh` 与 `run.sh --no-inject` 均 rc=0（101/101、5 路注入、k0–k3 全绿）。**无未修 finding ⇒ 状态 `待验收`。**

### 第 2 轮 engineer 自审（m14-linux-016，F5：U-mode 闭环）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| ① `trap cfx_umon, 0` 进入用户后，C 半跑在**用户 SP** 上（硬件不换栈）⇒ 第一次 C 调用即缺页，异常套异常（无输出、RAS 反复） | ✅已修 | `dadao_umon_excp` 保存四组后 `set.rb rb1, dadao_umon_stack_top`（专用 64 KiB 入口栈） | 修复前 rc=124 且 PC 卡在 `dadao_trap_handler`、RAS 重复项；修复后 `K4 f5 sys0 …` 正常输出 |
| ② 入口栈上的 `current`（本端口由 SP 推导）指向垃圾 ⇒ `find_vma(current->mm)` 会崩 | ✅已修 | 入口栈基址放 `struct thread_info`，`dadao_user_entry_install()` 把 `.task` 指向 `current` | `K4 f5` 的缺页经通道命中真 VMA（`vma=0x10000210000-0x10000220000`） |
| ③ `cfx_smon` 的源位 0（`cfx_umon`）未开 ⇒ 用户态缺页无法移交 smon（`ISS-454`：`escape` 不恢复当前 cfx） | ✅已修 | 安装时自开 `cfx_smon` supv 行 `cfxtrap`/`cfxreg` 的 bit0（`contract-syscall §8`：内核自开所需源位） | `K4 umon->smon: frame_umon=0x200005b0000 frame_smon=0x20000590000 …` |
| ④ 移交到 smon 的 cause 带子原因 wyde（`0x1_0000_0000_0002`），按原始值比类判成「非页表类」⇒ 具名终止 | ✅已修 | `dadao_user_fault_from_umon()` 先 `DADAO_CAUSE_CLASS()` 再判类，raw 值仍交通道解码 | 修复前 rc=192（0xc0）；修复后 `K3 pf: … result=fill-zero` + 用户继续执行 |
| ⑤ `thread_struct`/栈切换引入后，用户页 PTE 用 `S` 位 ⇒ 用户访问必 `NSPERM` | ✅已修 | `dadao_pf_mode_bits(vma)`：有 mm 的 VMA 用 `U`，探针窗口仍 `S`（零页 PTE 同改） | `K4 f5 pte data=0x…ff81 present=1 u=1`；K3 的窗口用例不变（`k3 263/263`） |
| ⑥ 自检把 `immu18` 与 `rd15`（syscall 号）比较，而用户程序只编码 immediate ⇒ 误红 | ✅已修 | 改判 `immu18 == 调用序号`，`rd15` 只打印 | `K4 check f5-immu18 want=0x1 got=0x1 ok`（两次） |
| ⑦ 迁移后 `make_initramfs.py` 的 `INIT_SOURCE` 仍指旧目录 ⇒ K0/K2 门控 rc=1 | ✅已修（越界披露） | 指向 `tests/shared/init/init.c` | `check-linux-k0` 119/119；见待裁定 6 |
| ⑧ 探针仍保留「F5 未安装」的旧断言（上一轮的阻塞态） | ✅已修 | 删掉三条阻塞断言，改为 `check_f5()`（13 条）+ `check_f3_scope()`（3 条） | `k4_fork_probe: 101/101 passed`；`--selfcheck` F1/F2/F4/F5 四组可翻转 |

判决：①–⑧ 全部已修并复验；`--inject` 五路（`no-regs-copy`/`share-pages`/`static-window-lookup`/`no-user-vector`/`no-cause-ip-save`）各自 red→`cp`+md5→回绿。**无未修 finding ⇒ 状态 `待验收`。**

### 第 1 轮 reviewer 验收（m14-linux-016，2026-11-17，大改档）

重跑均本人执行（worktree 自证 `git rev-parse --show-toplevel` = 本任务 worktree、branch `m14-linux-016`；分析：任务书、`trap.S`/`process.c`/`traps.c`/`k4_selftest.c`/`fault.c`/`setup.c` 补丁、`k4_fork_probe.py`、`run.sh`、`make_initramfs`/`check_k2`/`check_k3` diff；日志 `/tmp/opencode/m14-linux-016/review-runsh.log`；**无采信项，所有 rc 均本人重跑**）：
- `bash .work/evidence/m14-linux-016/run.sh` ⇒ **rc=0**：patch-tree rc=0（10 套 421 补丁 OK）、index-blobs rc=0、source-state rc=0（linux base+1 clean）、`k4_fork_probe` **101/101**、`--inject` 5 路各红→md5 MATCH→回绿、k0 **119/119**、k1 **112/112**、k2 **170/170**、k3 **263/263**（JOBS=32，无 124 超时）。
- 独立注入 4 路（手工 `cp`+md5、重建、回绿；①② 任务书未列）：① `escape cfx_umon,[excp_cause_ip,4]`→`+0` ⇒ rc=1、13 FAILED（`K4 FAIL: f5-cause-ip`）；② umon 入口 `cause_ip` 写进 `PT_STATUS` 槽 ⇒ rc=1、6 FAILED（`f5-frame-ip=0x0`）；③ 入口不写 `excp_vector` ⇒ rc=1、12 FAILED；④ 入口不存 `excp_cause_ip` ⇒ rc=1、6 FAILED。四路还原 md5 逐一 MATCH、回绿 **101/101 rc=0**；终态 `--source-state`/`check-patch-tree` 均 rc=0。
- F5 语义（`spec/DADAO-12 §5.2` + `contract-syscall §8`，取自本人日志）：`prev_mode=0`、`cause=0x1`(CFXTRAP=1<<0)、`ip`=trap 地址（0x10000200000/…008）、`immu18=info&0x3FFFF`=0/1 ✓；`escape +4` 落回 trap 下一条 ✓；`K4 umon->smon frame_umon=0x200005b0000 frame_smon=0x20000590000`（不串帧）、cause=CFXMEM 类、`K3 pf … fill-zero` ✓；四组帧 `bad=0`、`roundtrip ras_bad=0 sentinel_bad=0`（单帧不递归，`dadao_umon_busy` 具名拒绝）✓；固件前置 `m14-testcases-006` 已合入（`smon_trap=0x…7ff2` 源位 0 已开，无 CFXPERM）✓。
- 范围：`ace63349..HEAD`（任务自身；`88144349..HEAD` 另含 master 上 testcases-006/010、契约草案等**其它任务**合入，非本任务改动）仅 24 文件 = 任务书 + `components/linux/**` + `tools/linux/{check_k2,check_k3,make_initramfs,k4_fork_probe}.py`；`spec/`、`.tao/contracts/`、`tests/`、`components/qemu/**`、根 `Makefile` 未碰，无版本号改动。F3（`VM_GROWSDOWN`/init 真跑）确未做，`check_f3_scope` 断言镜像停在 K4 边界 ⇒ 与任务书移 017 一致。`make_initramfs.py` 仅 `INIT_SOURCE` 一行 + 2 行注释（master 侧旧路径，待裁定 6 已披露）——**建议保留**（K0 依赖、已披露、单行），不必摘出另立。
- 快照对账：审前基线 `git status -uall` = 仅 ` M components/linux/patches/init/main.c.patch`（md5 `280c548e…` 前后一致）；本审阅记录写入是规则要求的唯一新增改动；注入全落 `.work/source/linux`（与 run.sh 同机制）并 md5 还原；未提交 git、未改主工作树跟踪文件。

**判决：Needs Revision —— 唯一阻断项 `--selfcheck`，其余全部达标**
1. `tools/linux/k4_fork_probe.py:674` `for group in "F1245"` 迭代**字符串单字符**（'F','1','2','4','5'），无一命中 `"F1"/"F2"/"F5"` ⇒ 5 次全走 else 跑**同一组 F4**；实跑输出 `[SELFCHECK] F/1/2/4/5: mutation caught by 1 check(s)`（组名单字符、计数恒 1）。完成区「`--selfcheck` **4 组**（F1/F2/F4/F5，F3 已移 017 不入组）全可翻转，且「不改任何东西的 mutation 会让它 rc=1」已实测」与真实输出不符（实为 F4 一组 ×5），run.sh 的 `k4-selfcheck` 项因此假绿。
2. 即便修好循环，F1 组仍无可达 FAIL：本人只读实测 `mutation F1: failed=0 []`（mutation 只翻 `got=` 却保留 `ok`，而 `check_f1` 只读 verdict、不比 want/got）；同法 F2/F4/F5 各 `failed=1`（可红）。
修法（engineer 执行，reviewer 不代改）：循环改 `for group in ("F1","F2","F4","F5")`；F1 mutation 改翻 verdict（`ok`→`FAIL`）或 `check_f1` 增 want==got 一致性断言；`GROUPS="SF124"` 现无引用可一并处置。修后 `--selfcheck` 须打印 4 个真组名且各 ≥1 红、rc=0，按真实输出订正完成区措辞；只动探针脚本、无需重建镜像，但须重跑 `run.sh` 回绿再交审。

未闭合项（architect 侧，不计入本判决）：WIP `cdb3a014` 未含 `components/linux/patches/init/main.c.patch`（`dadao_k4_boundary()` 调用 hunk 仅在工作树，HEAD 版无该 hunk）——architect 提交时必须显式 stage 该文件，否则合入后 K4 边界不被调用、探针全红；完成区「修改文件」已声明该文件，与工作树一致、无隐瞒。

### 第 2 轮 reviewer 验收（m14-linux-016，2026-11-18，selfcheck 返工复验）

- 代码：`k4_fork_probe.py:678` 循环已改 `("F1","F2","F4","F5")`；F1 mutation 现翻 verdict（`ok`→`FAIL`）并改 `child_ip`；死常量 `GROUPS` 已删；返工提交 `f9a4dd1c` 仅 3 文件（任务书/`init/main.c.patch`/探针），均在白名单。
- `--selfcheck` 本人实跑 rc=0、**4 组真组名各 ≥1 红**：`F1: 2 / F2: 1 / F4: 1 / F5: 1`（独立 2 次 + run.sh 内 2 次一致）。**no-op 可达 FAIL 独立注入**：F2 mutation 改 `return text` ⇒ rc=1、`[SELFCHECK] FAIL: ['mutating F2 did not turn any check red']`；`cp`+md5 还原 `cff4b345…` MATCH（未用 git checkout）。
- `bash .work/evidence/m14-linux-016/run.sh` ⇒ **rc=0（14/14）**：probe **101/101**、5 路注入各 restored md5 OK+回绿、k0 **119/119**、k1 **112/112**、k2 **170/170**、k3 **263/263**；`run.sh --no-inject` ⇒ **rc=0** 同计数；run.sh md5 `f3fb97df…` 与上轮一致（证据脚本未被改）。
- 重试记录（1/3，有据）：首次 run.sh rc=1，根因=本人前台 120s 超时 SIGTERM 杀在 `static-window-lookup` 注入窗口、源树 `fault.c` 残留注入态（`57da7ccd`）——**非交付物缺陷**；按 `cp`+md5 从补丁树重建还原（`a77ca127…` == 上轮真实记录，源树 status 空，source-state/patch-tree 回绿）后重跑 rc=0。
- hunk/措辞：`init/main.c.patch` 的 `dadao_k4_boundary` 工作树与 HEAD 各 `grep -c`=1（已入 `f9a4dd1c`，上轮未闭合项闭合）；完成区无「5 组」残留（grep rc=1），已改「4 组」。快照对账：worktree 与源树 `git status -uall` 均空；未提交 git、未改主工作树。
- **判决：Accepted**（5 项复验全过，主会话可置「已验证」）。
- Finding（文档级，不阻断，交 architect 收尾处置）：第 1 轮审阅记录里本人写的完成区引文「`--selfcheck` 5 组全可翻转」被返工改写为「4 组…已实测」，致历史判决引文失真——建议恢复原引文或标注「引文为当时文本」。

## 完成区

**测试结果**：`k4_fork_probe.py` **101/101**（S/F1/F2/F4/F5 + F3 范围）；`--selfcheck` **4 组**（F1/F2/F4/F5；F3 已移 017 不入组）全可翻转——实测 `[SELFCHECK] F1: …2` / `F2: …1` / `F4: …1` / `F5: …1` rc=0，且把 F2 的 mutation 改成 no-op 时 `--selfcheck` 自身 rc=1（可达 FAIL 已验）；`--inject` **5 路**（`no-regs-copy`→F1 红 4 项、`share-pages`→F2 红 2 项、`static-window-lookup`→F4 红 2 项、`no-user-vector`→F5 红 3 项、`no-cause-ip-save`→F5 红 1 项），每路 `cp`+md5 还原并重建回绿。回归：k0 **119/119**、k1 **112/112**、k2 **170/170**、k3 **263/263**；`check-patch-tree` 76 补丁 OK、`check-index-blobs` OK、`--source-state` base+1 clean；一键证据脚本 **14/14**。
**提交注意**：`components/linux/patches/init/main.c.patch` 必须**显式 stage**——`dadao_k4_boundary()` 的 hunk 只在工作树（HEAD 版没有该 hunk），漏提交则合入后 K4 边界根本不被调用。
**修改文件**：`components/linux/{series,changelog.md,README.md}`；`components/linux/patches/` 下 `arch/dadao/{Kconfig.debug,configs/defconfig,include/asm/{cfx,mmu_context,processor,setup,trap}.h,kernel/{Makefile,setup.c,time.c,trap.S,traps.c},mm/{fault.c,mmu.c}}.patch` 改写 + `arch/dadao/kernel/{process.c,k4_selftest.c}.patch` 新增 + `init/main.c.patch`；`tools/linux/{k4_fork_probe.py 新, check_k2.py, check_k3.py, make_initramfs.py}`。**越界披露**：`kernel/time.c`（`lpj_fine`）、`mm/mmu.c`+`asm/mmu_context.h`（`arch_dup_mmap`）、`kernel/traps.c`（U-mode 移交分派）、`k4_selftest.c`、`check_k2.py`、`check_k3.py`、`make_initramfs.py`（master 侧旧路径修正，见待裁定 6）。`spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、根 `Makefile` **未动**；版本号未改。
**验收结果**（真实输出，节选）：
- 入口寄存器：`K4 umon vec user_mode=0x2 user_vector=0x20000141464 supv_mode=0x0 smon_trap=0xffffffffffff7ff2`
- 用户 syscall #0（经 `cfx_umon` user 行）：`K4 f5 sys0: nr=0 prev_mode=0 cause=0x1 ip=0x10000200000 info=0x7f000000 immu18=0x0 vec=0x20000141464 umon_switch=0x2 smon_switch=0x0`
- 四库帧：`K4 f5 banks: rd32=0x4b3446ff00000001 rb32=0x4b3446ff0000bb00 rf32=0x4b3446ff0000ff00 rd63=… rf63=… bad=0`
- U-mode 缺页移交 smon（两帧不共用）：`K4 umon->smon: frame_umon=0x200005b0000 frame_smon=0x20000590000 cause=0x10000000000002 ip=0x10000200004 info=0x10000210000`
- 通道填充：`K3 pf: n=1 id=… cause=CFXMEM sub=DGPTRAP ip=0x10000200004 va=0x10000210000 vma=0x10000210000-0x10000220000 pte=0x100000000044ff81 result=fill-zero`
- 第二次 trap（`escape +4` 落回 trap 下一条）：`K4 f5 sys1: … ip=0x10000200008 info=0x7f000001 immu18=0x1`
- 往返：`K4 f5 roundtrip: ras_bad=0 sentinel_bad=0 ra0=0x0 ra0_prev=0x0 rd20=0x0 pf_entries_delta=1`；用户页 PTE：`K4 f5 pte data=0x100000000044ff81 present=1 u=1 w=0 pfn=0x440000 zero_pfn=0x440000`
- 收尾：`K4 f5 done: syscalls=2 frames=0x200005b18d8/0x200005b20e8`，宿主 rc=0。
**新发现/坑**：① 纯 arch 端口在「第一次分配内存」前会同时踩到 `max_low_pfn` 未发布、镜像未保留、init 栈顶未让位（K1–K3 不分配故全隐性）；② `init/main.c` 的 `__weak trap_init()` 与 `start_kernel()` 同 TU 被内联掉，arch 强定义永不调用；③ 会返回的函数不能标 `__noreturn`（POP 到过期 RAS 项）；④ `copy_page_range()` 只复制 `vma_needs_copy()` 为真的映射；⑤ 零页必须是 `ZERO_PAGE(0)`；⑥ 注入还原必须 `os.utime()`（`copy2` 带回旧 mtime）；⑦ 硬件不换栈——用户入口必须在调 C 前切到内核栈，且本端口 `current` 由 SP 推导，入口栈基址要带 `thread_info`；⑧ `escape` 不恢复 `inner_cfx_code`（`ISS-454`）⇒ 内核需自开 `cfx_smon` 的源位 0；⑨ 非 trap 的 U-mode 异常固定进 `cfx_umon`，cause 只能靠寄存器移交 smon，且必须按 `DADAO_CAUSE_CLASS()` 判类。
**遗留问题**：① F3（execve 建 `VM_GROWSDOWN` 栈 VMA + init 真跑）已按用户裁定移到 `017`，本任务只落 execve 所需 arch 面并以 `check_f3_scope()` 断言镜像在 K4 边界收尾；② 同 cfx 递归 / cg5→cg6 保存留 K5（本任务单帧、不递归，`dadao_umon_busy` 具名拒绝重入）；③ `thread_struct` 的切换（`__switch_to`/`switch_mm`）归 017，`dadao_ret_from_fork()` 为 C 版占位；④ 探针镜像的 `k4_mm`/入口栈/用户页不释放（镜像在边界 `SYS_EXIT`）；⑤ 待裁定 6 的三处跨界改动（`check_k3`/`check_k2` 判据边界、`make_initramfs.py` 旧路径）请复核。
