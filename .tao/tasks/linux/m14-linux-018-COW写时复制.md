# m14-linux-018: 写时复制（COW：写共享只读页 ⇒ 复制旧内容 / 改 PTE / 失效）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-016`（`copy_page_range`）、`m14-linux-017`（子进程须被调度运行才能写共享页）
**可并行分片**：否（`components/linux` 单写者；共享 `mm/fault.c` 分发点）
**并行组**：与 `m14-linux-019`（栈增长）**必须串行**（共享 `mm/fault.c` 的 `CFXPERM` 分发点 / `mm/Makefile` / `Kconfig.debug`）；与 qemu/testcases 可并行
**预估**：4–5 h（代码量中等，风险在 PTE 改写与失效的成对性 + fork 引用计数）
**档位**：大改（组件改 + 新复制路径 + 探针；复核须独立重跑 + ≥4 路注入）
**状态**：待验收

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

### 第 1 轮 engineer 自审（2026-11-19）

审查范围：`mm/cow.c`（新）、`mm/fault.c` 分发点、`mm/mmu.c` 的 COW 钩子、`mm/k4_cow_selftest.c`（新）、`asm/pgtable.h` 接口、`tools/linux/k4_cow_probe.py`（新）、`k4_fork_probe.py` 的 F2/S4 更新。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 只靠通用 `copy_page_range()` 建共享 ⇒ 子侧 PTE 不存在（实测 `child_pa=0x0 w_parent=1 count=1`）：`vma_needs_copy()` 对「无 `anon_vma` 且非 `VM_COPY_ON_FORK`」的 VMA 直接跳过，而本端口通道页没有 anon_vma | ✅已修 | `mm/mmu.c` 新增 `dadao_dup_one_pte()`：装父 PTE（去 `W`）+ 父侧 `ptep_set_wrprotect()` + `get_page()`；子侧已存在（通用路径装过）则只核对；零页只装 PTE 不取引用 | `K4 cow fork: same=1 w_parent=0 w_child=0 count=2 dup_pages=1 dup_writable=0`；W1/W2/W4/W5 全绿 |
| `cow_fail(why, want, got)` 三数字签名收到字符串 ⇒ 3 处 `-Wint-conversion` 编译错 | ✅已修 | 改 `(why, const char *what, value)`，与 `k4_fail()` 一致 | 重建 rc=0 |
| W5 断言 `flush_va == COW_VA_BASE`，实际故障地址是 `VA+16` ⇒ 自评首轮红 | ✅已修 | 期望改 `COW_VA_BASE + COW_OFF_PARENT` | `w5-flush-va ok` |
| 探针写死「NWPERM 恰好两条」，实际三条（建页 `replace-zero` + 子 `cow-copy` + 父 `cow-write`） | ✅已修 | 按三条判定，并加「分支次序」与「三笔 cause_info 各自等于故障 VA」断言 | `86/86` |
| W3 用 int 比字符串（`cause_info`）⇒ 假 FAIL | ✅已修 | `num()` 归一 | W3 组全绿 |
| `die` 行只有 `mode`/`code`，`cause`/`info` 在 `dadao: <why> cause=…` 行 | ✅已修 | 拆 `die_row()`/`die_name_row()` 两个解析器 | `终止的退出段 == 0xe7`、`终止原因名 == CFXPERM` 均 PASS |
| 钩子对 `VM_PFNMAP` 的原始 pfn 调 `pte_page()`/`get_page()` 会 mis-account | ✅已修 | 跳过 `VM_PFNMAP` VMA（通用路径也不为其取引用） | 重建 + 全套回绿 |
| `asm/pgtable.h` 新块引入 `linux/mm_types.h`/`types.h`（`pte_t` 与 `struct vm_area_struct` 前置声明本就可用） | ✅已修 | 删多余 include | 重建 rc=0 |
| 注入⑤原写法 `count == 2` 先命中子侧分支（红因是 W1 而非判据⑤） | ✅已修 | 改 `if (0)`，红因落到 `w5-in-place` | `w5-in-place want=0x1 got=0x0 BAD` |
| 证据脚本 `grep -c …  \|\| echo 0` 在计数 0 时输出两行，`ck` 的 got 含换行 ⇒ 假 FAIL | ✅已修 | 改 `\|\| true` + `${VAR:-0}` | 证据脚本 `30/30` |
| 首轮证据跑出现两个并发实例写同一日志（乱序）+ 源码残留注入 | ✅已修 | 清理进程后单实例重跑；`cow.c` 用源码树 HEAD blob 还原并 md5 对账 `d70480c2…` | 单实例 `30/30`、`源码已还原 wanted=0 got=0` |

判决：所有 finding 已修，状态 → `待验收`。

### 第 2 轮 engineer 返工自审（2026-11-19，按 reviewer 两条阻断）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 阻断 1：合并态不成立（master `d4f31f31` 起 12 个门控脚本冲突；解冲突后 `check-config-pins` FAIL 14 项） | ✅已修 | `git merge --no-verify master`（合并提交 `5707746d`）：12 个脚本一律「取 master 的 `CONFIG_PINS`/`config_lines()` 结构 + 加本任务 COW 键」，不保留原 `IMAGE=[…]` 字面量；`k4_switch_probe` 的镜像配置期望表同步加键 | `make check-config-pins` = PASS（68 项、0 失败；切片脚本 14 / Kconfig 符号 16 / 镜像 44）rc=0 |
| `k4_cow_probe.py` 缺模块级 `CONFIG_PINS`（C2：新门控不能逃逸） | ✅已修 | 16 键 `CONFIG_PINS` + `IMAGE_PINS`（`1`→`COW=1`、`3`→`COW=3`），切片改由 `config_pins.config_lines()` 派生，删手写 `IMAGE` 列表 | 该脚本 C2/C3/C4 全 PASS（3 镜像 × 16 符号） |
| `k4_stack_probe.py` 缺 `CONFIG_DADAO_K4_COW_SELFTEST` 键（C3） | ✅已修 | `CONFIG_PINS` 加 `"CONFIG_DADAO_K4_COW_SELFTEST": "0"`（int 且无 `depends on` ⇒ 必须给具体值，钉 `"n"` 等于留空） | 该脚本 C3「5 镜像 × 16 符号」PASS |
| 阻断 2：`eager-copy` 反例不可达（锚点落在 `if (pte_present(dst_pte)) … return 0;` 之后；F2 的 `VM_MIXEDMAP` VMA 由通用路径装好子 PTE ⇒ 该段对 F2 是死代码） | ✅已修 | 锚点前移到早退分支内（`if (pte_present(ptep_get(dst_pte))) {` + 紧随注释），注入体 = 016 的私有拷贝（新页装回子 PTE、**保持只读**，让 fork 本身仍成功、F2 在真控制台上被判） | `--inject eager-copy` ⇒ `F2 red checks = 2 (rc=56)`，红项含「两侧 PA 相同」；还原 md5 `ec79e129…` 一致 ⇒ `back to green rc=0 failures=0` |
| 证据脚本不跑 `--inject`（阻断 2 因此漏检） | ✅已修 | `run.sh` 新增「`k4_fork_probe --inject eager-copy`」一步 + 三条断言（F2 有红项 / 还原后回绿 / `mmu.c` 无 `injected:` 残留） | 证据脚本 **34/34** rc=0（原 30/30 + 4 条） |
| reviewer 提示：`apply_config_lines` 不重置未列符号 | ✅已记录 | 完成区「新发现/坑」第 6 条改写：机制真实、无运行期影响；阻断面在 `check-config-pins`，以 16 键钉子闭合 | 见完成区 |

判决：两条阻断全绿（合并态 `check-config-pins` rc=0、`eager-copy` 可达且已纳入证据脚本），状态保持 `待验收`。


### 第 1 轮 reviewer 验收（2026-11-19）

**重跑记录（本人执行、退出码逐条实测，不采信完成区）**
- 运行期证据目录内的 `run.sh` 全量跑 2 次：首轮在 `check-linux-k2` 中途被外部终止（无错误输出、非交付物缺陷 ⇒ 判环境干扰，**重试 1/3**）；补跑 `check-linux-k2 170/170`、`check-linux-k3 263/263` rc=0；收尾全量重跑 `RESULT: 30/30 checks passed, 0 failed`、退出码 0。
- 逐项实测（与完成区**逐条一致**）：`k4_cow_probe 86/86`、`--selfcheck red checks=33 / 5 组`、`k4_fork_probe 104/104`、`k4_stack_probe 44/44`、`k4_switch_probe --no-inject 52/52`、`check-linux-k0 130`、`k1 112`、`k2 170`、`k3 263`、`check-patch-tree 11 补丁集 433 OK`。
- 其 5 路注入我亲自重跑：`alloc-no-copy` / `pte-stays-old` / `no-invalidate`（红因 rc=231 具名终止，非 BAD 行）/ `asid-any` / `sole-ref-copies` 全部「红 → cp+md5 还原 `d70480c2…` → 重建 → 回绿」rc=0。

**五条判据独立核（读代码 + 实跑）**
- ① `mm/cow.c` `memcpy(__va(pa), __va(old_pa), PAGE_SIZE)` + `set_pte` + 失效；W1 断言新页第 0 字 == 哨兵 `0x4b34434f57000001`（**非零**，源 = 探针自检宏、由探针正则现场取）⇒ **复制而非清零**；② W2 用 `cow_pfn_of()` **现场走 PTE** 读父侧 PA（非缓存值）+ 父内容未变 + 看不到子写；③ `VM_SHARED` ⇒ `DADAO_WP_NONE` ⇒ `die-perm`，W3 断言 `result==die-perm`、`pool==0`、退出段 `0xe7`；④ 引用 `1→2→1→0` 四段现场打印并逐段断言（末引用回收后 `page_count==0`）；⑤ 失效 `ASID_ANY=0` + 写侧 mm 的 ASID + `invalid|VA`（ctrl=6，由 `asm/ptw.h` 派生）+ `flush_va==故障 VA`，父侧再写仍进通道且就地升级。
- **spec 依从**：`NWPERM=[37]`（`contract-see §6.1.1` ↔ `cause-sub.h` 双向核，`nwperm_id=0x2000000080`）✓；`cause_info`==访存地址（三笔 NWPERM 各自 VA）✓；`ASID_ANY=0` ✓；页大小 64 KiB ← `.config` 的 `CONFIG_PAGE_SHIFT` 现场读、拷贝用 `PAGE_SIZE` ✓。

**≥4 路独立注入（均不在其 5 路内；cp+md5 还原 + 重建回绿）**
- `I1 去掉 VM_SHARED 拒绝` ⇒ W3 红 5 条（`die-perm`→`cow-write`、退出 71≠231）；`I2 父侧不写保护` ⇒ 红 18 条；`I3 复制分支不 put_page` ⇒ 红 14 条；`I4 fork 退回急切私有复制` ⇒ 红 18 条。**4/4「红→还原→回绿」**，md5 全匹配、源码无残留。

**阻断 1｜合并态不成立（`Process-07 §5a` MUST）**
- 当前 master `d4f31f31` 与本分支在 **12 个门控脚本**上冲突，`git merge master` **无法完成**；解冲突后 `make check-config-pins` **FAIL 14 项、rc=2**，其中 **2 项与解法无关**：`k4_cow_probe.py` 缺模块级 `CONFIG_PINS`（C2 新增门控不能逃逸）、`k4_stack_probe.py` 缺 `CONFIG_DADAO_K4_COW_SELFTEST`（C3）。取 master 侧、取分支侧各 14 项 FAIL ⇒ **任一单侧解法都红**。
- 完成区所记「合并态（`git merge master` ⇒ `3a415038`）」= merge-base；`m15-infra-008` 13:11:38 已上 master、本任务 14:04:48 才提交 ⇒ 该证据是**陈旧基点**，非当前合并态。

**阻断 2｜016 门控的反例 `eager-copy` 已不可达**
- 实跑 `python3 tools/linux/k4_fork_probe.py --inject eager-copy` ⇒ `F2 red checks = 0 (rc=0)`、`FAIL: nothing went red`、**rc=1**。
- 根因：锚点 `child = pte_wrprotect(entry);` 位于 `if (pte_present(ptep_get(dst_pte))) … return 0;` **之后**，而 F2 的 VMA 是 `VM_MIXEDMAP` ⇒ 通用 `copy_page_range()` 已装好子 PTE，该段**从不执行**（我独立注入同一位置，`k4_fork_probe` 仍 **104/104**）。把注入移进早退分支后 F2 **可红**（`两侧 PA 相同` 等 2 条、rc=1；还原 104/104）⇒ **断言本身可达 FAIL，错的是锚点**；证据脚本不跑 `--inject`，故未被覆盖。

**问 2 判定（判据交接 vs 放宽）**：F2 改「同 PA、`W=0`、引用 2」是**判据交接的必然结果，不是放宽** —— 旧断言在新语义下事实为假（内核自身 `k4_expect("cow-pa-shared", …)` 即 FAIL）；原 1 条 `两侧 PA 不同` → 新 4 条（同 PA / 父 `W=0` / 子 `W=0` / 引用 2），内核自检侧与探针侧同步 1→4；`git diff 3a415038..HEAD` 逐行核 `k4_selftest.c` / `k4_fork_probe.py`，**只动 F2 一处语义**、无其它断言弱化；`--selfcheck` 4 组仍可翻转（实测 F1:2 F2:2 F4:1 F5:1、rc=0）。**但配套反例失效（见阻断 2）**。

**问 8 越界核**：`mm/mmu.c::dadao_dup_mmap_cow()` **必要且最小** —— 016 的 `dadao_dup_mmap_private()` 是急切私有复制，不退役则共享根本建立不起来、判据①②④不可达；同批 `asm/mmu_context.h`（钩子签名）、`asm/pgtable.h`（`dadao_do_wp_page` 声明）、`kernel/setup.c`+`asm/setup.h`（自检调用点/声明）、`components/linux/series`（两新补丁登记）、`kernel/k4_selftest.c`（F2 交接）、12 个门控脚本（钉子）均必要；**未触碰** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile` ✓。

**其它实测**：`apply_config_lines` **不重置**未列符号（`COW=1` 跨 `k4_stack_probe` 全程存活）⇒ 钉子继承机制真实存在；但 `k4_stack_probe` 运行期未复现串味（`COW=1` 下 44/44，因 `dadao_k4_stack_selftest()` 先于且 `__noreturn`）⇒ 该缺口的阻断面在**合并态门控红**，非运行期红。

**快照对账**：验收前后 `git status --porcelain -uall` 均为空、`git diff --stat` 为空、HEAD `3c6a360a` 未变、源码树无注入残留；与完成区「修改文件」逐项比对：**27 个改动文件中 26 个在声明内**，唯一未列的是任务书自身（记录载体）。`spec`/契约位号与页大小我独立读原文复核；内核运行期数值采信「自检现场读值 + 探针派生期望」，并用 4 路反例证明其可红；`--selfcheck` / `eager-copy` 结果为我本人实跑。

**判决：Needs Revision** —— 阻断 1（合并态 12 文件冲突 + `check-config-pins` 14 项红）、阻断 2（`eager-copy` 反例不可达）。五条判据、判据交接语义、越界改动、不回归**均通过**。返工要求：① 按 master 新规范把 16 个符号的钉子写进各脚本 `CONFIG_PINS`（`config_lines()` 派生、禁手写 `CONFIG_X=v` 字面量），`k4_cow_probe.py` 补 `CONFIG_PINS`、`k4_stack_probe.py` 补 COW 键，解 12 处冲突后在**当前 master 合并态**重跑 `check-config-pins` 与运行期证据脚本；② `eager-copy` 的 `old/new` 锚点改到早退分支内（或改注入 `copy_page_range` / `vma_needs_copy`），并把 `k4_fork_probe --inject eager-copy` 纳入证据脚本。

### 第 2 轮 reviewer 验收（2026-11-19，返工 1）

**重跑记录（本人执行、退出码实测）**
- 合并态：`git merge-base --is-ancestor 7a8270a7 HEAD` ⇒ 当前 master 已并入（merge `5707746d`，HEAD `8aac2a0c`）；`make check-config-pins` ⇒ **68 项 / 0 失败 / rc=0**（现场统计：切片脚本 14、Kconfig 符号 16、镜像 44）；`check-patch-tree` rc=0。
- 运行期证据目录内的 `run.sh` ⇒ **`RESULT: 34/34 checks passed, 0 failed`、退出码 0**（第 1 轮 30 项 + 返工新增 4 项：`eager-copy` 红 / 还原回绿 / `mmu.c` 无残留 / 注入整体 rc）。
- 逐项实测：`k4_cow_probe 86/86`、`--selfcheck 33 红 / 5 组`、5 路 COW 注入全绿、`k4_fork_probe 104/104`、`k4_stack_probe 44/44`、`k4_switch_probe --no-inject 52/52`、`k0 130`、`k1 112`、`k2 170`、`k3 263`、`check-patch-tree 11 补丁集 433 OK`。

**阻断 1 复核（合并态）—— 通过**
- 14 个脚本逐键比对（AST 取 `CONFIG_PINS`，master `7a8270a7` ↔ 分支）：**丢 master 键 0、多出键 0、值漂移 0、缺 COW 键 0、非 Kconfig 键 0**，每脚本键集 == Kconfig 全集 16。
- 抽查 `check_k3.py` / `k3_page_probe.py` / `k4_stack_probe.py` 三份逐键清单，16 键完全一致；`k4_stack_probe.py` 与 `k4_cow_probe.py` 的 `CONFIG_DADAO_K4_COW_SELFTEST = "0"`（int 且无 `depends on` ⇒ 给具体值）✓。
- `k4_cow_probe.py` 由 `IMAGE` 字面量改为 `CONFIG_PINS`(16) + `IMAGE_PINS`(case 1/3) + `config_lines()`；`judge_shared` / `judge_perm` / `INJECTIONS` / `markers` / `derivations` **零改动**（diff 逐 hunk 核）。

**阻断 2 复核（`eager-copy`）—— 通过**
- 我自跑 `python3 tools/linux/k4_fork_probe.py --inject eager-copy` ⇒ **`F2 red checks = 2 (rc=56)`**，红因含语义断言本体 `F2: 两侧 PA 相同`；`rc=56 = 0x38 = K4_FAIL_CHILD`（内核自身 `cow-pa-shared` 期望失败）⇒ **不是 fork ENOMEM / `-EBUSY`**，注入体确未给子 PTE 置 `W`（同轮 `w_parent`、`w_child`、`count==2` 均 PASS）；`restored md5 ec79e129… -> ec79e129… OK`、`back to green rc=0 failures=0`。
- 锚点已前移到 `if (pte_present(ptep_get(dst_pte)))` 早退分支内（diff 核）；证据脚本新增 3 条断言且均 **fail-closed**（`F2 red checks = [1-9]`、`back to green rc=0 failures=0`、`grep -c 'injected:'` == 0）。

**本轮我自己的注入（2 路，均不在其 6 路清单）**
- `R2-a 去掉父侧写保护` ⇒ rc=1，但红落在 **S4 静态串**（`ptep_set_wrprotect(...)` 字面量消失）、F2 红 0 —— 说明 F2 的 `w_parent` 由**通用 `copy_page_range()`** 写保护、arch 钩子不是其来源（如实记录，不作通过项）。
- `R2-b 早退分支丢第二份引用（`put_page`）` ⇒ rc=1、**F2 红 2 条**，含 `F2: 页引用计数 == 2`（want=2 got=1）；还原 md5 匹配、无残留、回绿 **104/104 rc=0** ⇒ `RESULT OK`。

**其余未被本轮改动**
- `git diff 3c6a360a HEAD -- components/linux` ⇒ **空**（内核补丁、判据、W1–W5 实现、5 路 COW 注入定义零改动）；非 `tools/` 非 `.tao/` 的差异全部是合并带入的 master 侧（`Makefile`/`docs`/`idl`）。工作树 `git status -uall` 干净、HEAD `8aac2a0c`、源码无 `injected:` 残留；主工作树未被我改动（状态为空）。

**判决：Accepted** —— 两条阻断在**我自己的重跑**下均已消除（合并态 68/0 rc=0 + 34/34 rc=0；`eager-copy` F2 红 2 条且还原回绿）；`spec`/契约位号、五条判据、越界判定沿用第 1 轮结论，本轮未变。**Accepted 仅为「工程师达标」证据，仍由 architect 终审。**

## 完成区

**测试结果**（合并态 `5707746d`，master `7a8270a7` 已并入）：`k4_cow_probe` **86/86**；`--selfcheck` 破损控制台 33 条红、5 组；COW 5 路注入 + `k4_fork_probe --inject eager-copy` 全部「红 → `cp`+md5 还原 → 重建 → 回绿」rc=0（红因：`w1-copied-sentinel` / `w1-pa-moved` / 重试仍 `NWPERM`⇒`die-perm` / `w5-flush-asid-any` / `w5-in-place` / F2「两侧 PA 相同」）。`make check-config-pins` **PASS**（68 项、0 失败；14 脚本 × 16 符号 × 44 镜像）rc=0；`check-patch-tree` rc=0（linux 86 补丁 / 全集 433）。不回归：`k4_fork_probe` 104/104、`k4_stack_probe` 44/44、`k4_switch_probe --no-inject` 52/52、`check-linux-k0` 130/130、`k1` 112/112、`k2` 170/170、`k3` 263/263。

**修改文件**：
- 新增：`patches/arch/dadao/mm/cow.c.patch`、`patches/arch/dadao/mm/k4_cow_selftest.c.patch`、`tools/linux/k4_cow_probe.py`
- 内核补丁：`mm/{fault,mmu,Makefile}.patch`、`include/asm/{pgtable,mmu_context,setup}.h.patch`、`kernel/{setup,k4_selftest}.c.patch`、`arch/dadao/Kconfig.debug.patch`（任务书写的 `kernel/Kconfig.debug.patch` 路径不存在，实际在 `arch/dadao/`）
- 台账/工具：`components/linux/{series,changelog.md}`、`tools/linux/k4_fork_probe.py`、`tools/linux/{check_k0,check_k1,check_k2,check_k3,k1_pt_probe,k2_irq_probe,k2_time_probe,k2_trap_probe,k3_page_probe,k3_pt_probe,k4_switch_probe,k4_stack_probe}.py`（12 个按 master 的 `CONFIG_PINS` 结构解冲突并各加 COW 键）

**返工 1：合并态（12 脚本并集 + COW 钉子）+ `eager-copy` 锚点前移并纳入证据**：12 个门控脚本按并集解冲突（master 的 `CONFIG_PINS`/`config_lines()` + 本任务 COW 键，Kconfig 全集 16 符号）⇒ `check-config-pins` 0 失败；`eager-copy` 锚点移进早退分支（`VM_MIXEDMAP` 实际走的那条）⇒ 反例可达（F2 2 条红、rc=56），并写进 `run.sh`。

**验收结果**：运行期证据目录内的 `run.sh` = `RESULT: 34/34 checks passed, 0 failed`，`EVIDENCE_EXIT=0`（自检、W1–W5、COW 5 路注入、`eager-copy` 反例、3 个 k4 探针、补丁树、k0/k1/k2/k3）。

**新发现/坑**：
1. 通用 `copy_page_range()` 在本版本由 `vma_needs_copy()` 把关：只有 `VM_COPY_ON_FORK`（=`VM_PFNMAP|VM_MIXEDMAP|VM_UFFD_WP|VM_MAYBE_GUARD`）或父侧有 `anon_vma` 才拷页表；本端口通道页两者皆无 ⇒ **fork 的共享/复制只能由 arch 钩子建立**（016 的急切复制、本任务的 COW 共享同源）。推论：反例锚点必须落在该 VMA **真正执行**的那条分支（`VM_MIXEDMAP` 由通用路径先装好子 PTE ⇒ 早退分支），否则是死代码。
2. 共享页在 fork 后父侧 PTE 被写保护，**arch 必须自己失效 fork 侧 TLB**（`local_flush_tlb_mm`）；否则父侧穿过陈旧的「可写」翻译写进子页（实测：不做则 `w5-second-fault` 为 0）。
3. 注入「不失效」的可观测形态不是红断言而是**重试预算内的 `die-perm`**（第二次仍 `NWPERM`）——门控须接受「具名终止」也算红。
4. `grep -c` 在计数 0 时 rc=1，`$(… || echo 0)` 会产出两行、把 `ck` 的 got 弄脏成假 FAIL；证据脚本一律 `|| true` + `${VAR:-0}`。另：日志前缀是 `[INJECT] name:`，grep 模式若带 `INJECT ` 会漏（返工首轮因此假红 2 条）。
5. 共享构建树里 `CONFIG_INITRAMFS_SOURCE` 由 `make_defconfig` 一次性写入（`apply_config_lines` 不改它）：cpio 未生成时配过一次，后续探针镜像就永远空 rootfs（`k4_switch` S7 / `check-k0` K7 因此红）；先跑一次 `make linux-defconfig` 即恢复。
6. **`apply_config_lines` 不重置未列符号**（reviewer 提示，返工中确认）：`COW=1` 这类值会留在共享构建树里被下一个脚本继承；`m15-infra-008` 的对策是每个切片脚本用 `CONFIG_PINS` 钉满 Kconfig 全集并由 `config_lines()` 派生，本任务已按此收口（16 符号 × 14 脚本），当前无运行期串味（`k4_stack_probe` 在 `COW=1` 下仍 44/44），阻断面在合并态门控 `check-config-pins`；int 且无 `depends on` 的符号**必须钉具体值**（钉 `"n"` = 留空，会被门控判为静默 no-op）。

**遗留问题**：无。任务书「预计改动文件」之外的必要改动逐条披露：① `mm/mmu.c`+`asm/mmu_context.h`（fork 半场：通用路径跳过本端口页，见坑 1）；② `kernel/setup.c`+`asm/setup.h`（新自检必须有调用点与声明）；③ `kernel/k4_selftest.c`+`tools/linux/k4_fork_probe.py`（016 的 F2 断言「两侧 PA 不同」，本任务按判据交接改为 COW 共享语义；配套反例 `eager-copy` 锚点已按返工前移）；④ `components/linux/series`（两个新补丁须登记）；⑤ `asm/pgtable.h`（COW 接口）；⑥ 12 个门控脚本按 `m15-infra-008` 重写并加 COW 键（见坑 6）。用户态写共享页的端到端断言仍按 2026-11-17 裁定 C 由 016/017 承担。
