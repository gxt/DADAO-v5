# SPEC-140t: musl TLS/线程指针硬依赖查证（`ADR-0025 D5`）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（`D5` = TLS/线程「先查证再定」）；`INFRA-076t`（musl 1.2.6 落点 = `.work/source/<name>/`，**只读**）；`SPEC-139t`（动态链接 ABI 契约，TLS 重定位候选面）；`contract-abi.md`（`rb3`=TP 寄存器约定）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定

- **用户裁定（2026-10-14，`ADR-0025` 议题 E，**原话 / 选项标签**）**：「**先查证再定（推荐）**」（⇒ 若 musl **硬依赖** TLS 则**自动纳入** M8）。
  - 来源：`ADR-0025` §Decision `D5` + §状态说明「逐条确认记录」表。
- **本任务只做「查证 + 给判据」**：**不写实现**、不改组件补丁、不改 `spec/` / `contracts/`。
- **落点选择说明**：本查证结论直接驱动 `ADR-0025 D5`（是否自动纳入 M8）与 `arch/dadao` 的 **ABI/TLS 最小面** ⇒ 归 **`spec` 模块**（`INFRA` 侧仅 `INFRA-076t` 取源/锁定，不含查证判定）。

## 查证对象 / 方法

- **对象**：musl **1.2.6**（tag `v1.2.6`，commit `9fa28ece…`），落点 `.work/source/<name>/`（`INFRA-076t` 交付；**只读**，本任务未改动，见「证据」§H）。
- **方法**：**源码链路逐条取证**（`文件:行` + 片段），从调用点回溯到 arch 支撑点；结论一律以源码行支撑，**不凭印象**。可复算断言固化为 `.work/evidence/<任务ID>/run.sh`。

## 结论（三种之一）

> **「musl 必须 TLS（线程指针 + 含 `struct pthread` 的 TLS/TCB 区，无条件、静态单线程亦不可省）」** —— 有硬证据。
> 精确口径（**事实**）：
> 1. **TP（线程指针）+ TCB/TLS 区 = 硬依赖**：musl 启动 **无条件** 建 TLS 并写 TP；写不上即 `a_crash()`。`errno` / `exit` / stdio 锁 / 取消点 syscall 全部经 `__pthread_self()`（由 TP 算出）访问 `struct pthread`。
> 2. **`TLS_*` 重定位 / TLS 槽（`REL_DTPMOD`/`DTPOFF`/`TPOFF`/`TLSDESC`）= 条件依赖**：仅在出现**编译期 `__thread` 访问**（LE/IE/GD）或**动态 TLS**（`ldso`）时才需要；**P1 静态最小面（无 `__thread`）不触发**。
> 3. **「无 TLS 配置/替代路径」= 不存在**：`configure` 无 TLS 开关；`SYSCALL_NO_TLS` 只服务 i386 的 `gs` 特例（见 §F `E22`/`E23`），**不是**通用「无 TLS」开关。

## 证据表（`文件:行` → 结论；**事实**）

> 路径相对 `.work/source/<name>/`（musl 1.2.6）。断言已固化进证据脚本（逐条可达 FAIL）。

### A. `errno` 无条件经 TP
| # | 文件:行 | 片段（要点） | 结论 |
|---|---|---|---|
| E1 | `src/errno/__errno_location.c:6` | `return &__pthread_self()->errno_val;` | `errno` 取址 = TP → TCB |
| E2 | `include/errno.h:16` | `#define errno (*__errno_location())` | 一切 `errno` 用法经 E1 |

### B. `__pthread_self` 由 TP 寄存器算出（无 fallback）
| # | 文件:行 | 片段（要点） | 结论 |
|---|---|---|---|
| E3 | `src/internal/pthread_impl.h:119`、`:122` | `#define __pthread_self() ((pthread_t)(__get_tp() - sizeof(struct __pthread) - TP_OFFSET))` / `…(pthread_t)__get_tp()`（`TLS_ABOVE_TP` 两支） | 宏，**无**「无 TP」分支 |
| E4 | `arch/riscv64/pthread_arch.h:4` | `__asm__("mv %0, tp")` | 每 arch **必须**提供 `pthread_arch.h::__get_tp()` |

### C. 启动期无条件建 TLS + 写 TP（失败即致命）
| # | 文件:行 | 片段（要点） | 结论 |
|---|---|---|---|
| E5 | `src/env/__libc_start_main.c:39` | `__init_tls(aux);`（`__init_libc` 内，**无 `if`**） | 启动无条件初始化 TLS |
| E6 | `src/env/__init_tls.c:148-150` | `/* Failure to initialize thread pointer is always fatal. */ if (__init_tp(__copy_tls(mem)) < 0) a_crash();` | 无 TP ⇒ 崩溃 |
| E7 | `src/env/__init_tls.c:18`、`:22` | `__set_thread_area(TP_ADJ(p))`；`__syscall(SYS_set_tid_address, …)` | 必须写 TP；需 `set_tid_address` 号 |
| E8 | `src/env/__init_tls.c:105-112`、`:133-146` | `if (tls_phdr) {…}`；否则用 `builtin_tls`；**随后仍** `__init_tp` | **无 PT_TLS 也须 TP**（TCB 本身在 TLS 区） |
| E9 | `src/thread/__set_thread_area.c:8` | `return -ENOSYS;`（通用回退） | 未覆盖 ⇒ E6 致命路径 |
| E10 | `src/thread/riscv64/__set_thread_area.s:4` | `mv tp, a0`（**纯寄存器写、非 syscall**） | 参考实现形态 |

### D. 取消点 syscall / 基本 I/O / `exit` 无条件经 TP
| # | 文件:行 | 片段（要点） | 结论 |
|---|---|---|---|
| E11 | `src/thread/pthread_cancel.c:10`、`:29`、`:33` | `__cancel()` / `self=__pthread_self()` / `__syscall_cp_asm(&self->cancel, …)` | 强符号 `__syscall_cp_c` 用 TP |
| E12 | `src/thread/__syscall_cp.c:13` | `weak_alias(sccp, __syscall_cp_c)` | 弱回退被 E11 强符号覆盖 |
| E13 | `src/unistd/read.c:6`、`src/unistd/write.c:6`、`src/unistd/close.c:16` | `syscall_cp(SYS_read,…)` / `syscall_cp(SYS_write,…)` / `__syscall_cp(SYS_close,…)` | **基本 I/O 即取消点** ⇒ 触达 TP |
| E14 | `src/exit/exit.c:38` | `int tid = __pthread_self()->tid;` | `exit` 无条件读 TP |
| E15 | `src/stdio/__lockfile.c:6` | `__pthread_self()->tid` | stdio 锁读 TP |

### E. ldso / 动态 TLS 关联
| # | 文件:行 | 片段（要点） | 结论 |
|---|---|---|---|
| E16 | `ldso/dynlink.c:1776`、`:1783` | `/* Setup early thread pointer in builtin_tls … */`；`__init_tp(__copy_tls((void *)builtin_tls))` | `__dls2b` **早期即写 TP** |
| E17 | `ldso/dynlink.c:2032` | `__init_tp(__copy_tls(initial_tls))` | `__dls3` 再设 TP（无条件） |
| E18 | `ldso/dynlink.c:498`、`:516` | `case REL_DTPMOD:` / `case REL_TLSDESC:`（`do_relocs`，另含 `REL_DTPOFF`/`REL_TPOFF`） | TLS 重定位处理 |
| E19 | `arch/riscv64/reloc.h:17`、`:20` | `#define REL_DTPMOD R_RISCV_TLS_DTPMOD64` / `#define REL_TLSDESC R_RISCV_TLSDESC`（另 `REL_DTPOFF`/`REL_TPOFF`） | 每 arch 须定义 TLS 重定位映射 |
| E20 | `src/ldso/riscv64/tlsdesc.s:17` | `ld t2,-8(tp) # t2=dtv` | TLSDESC 读 TP/DTV |
| E21 | `src/thread/__tls_get_addr.c:5` | `pthread_t self = __pthread_self();`（`self->dtv[…]`） | GD/动态 TLS 经 TP |

### F. 「能否无 TLS」查证（**不存在替代路径**）
| # | 文件:行 | 片段（要点） | 结论 |
|---|---|---|---|
| E22 | `src/env/__init_tls.c:1`、`ldso/dynlink.c:2` | `#define SYSCALL_NO_TLS 1`（仅 2 处**定义**） | 是「早期 syscall 不用 TLS stub」的局部宏 |
| E23 | `arch/i386/syscall_arch.h:6` | `#if SYSCALL_NO_TLS`（**全树唯一读取点**） | 仅 i386 `gs` 特例，**非**通用开关 |
| E24 | `configure`（全文件） | **无** TLS/thread 配置项（`grep` 空） | **无**「无 TLS」构建选项 |

### G. 运行期缺 arch 支撑时的链接/号表后果
| # | 文件:行 | 片段（要点） | 结论 |
|---|---|---|---|
| E25 | `arch/riscv64/bits/syscall.h.in:96` | `#define __NR_set_tid_address 96` | `__init_tp` 需该号（否则编译/映射缺） |
| E26 | `src/thread/*/syscall_cp.s` **18/18 arch** | 全 arch 均提供 `syscall_cp.s`（现场统计，不写死） | 端口 parity：须提供 |
| E27 | `src/thread/*/clone.s` **18/18 arch** | 全 arch 均提供 `clone.s`（现场统计，不写死） | 线程面 parity |
| E28 | `Makefile:28-29` | `REPLACED_OBJS = $(subst /$(ARCH)/,/,$(ARCH_OBJS))`；`ALL_OBJS = … $(filter-out $(REPLACED_OBJS), …)` | **arch 同名对象替换通用对象**（缺 arch 文件时用通用回退） |
| E29 | `src/thread/clone.c:6` | `return -ENOSYS;`（通用 `__clone` 桩） | `clone.s` **有回退**（缺 ⇒ 运行期 ENOSYS，非链接失败） |
| E30 | `src/thread/__unmapself.c:23` | `CRTJMP(do_unmap, stack);`（通用回退） | `__unmapself.s` **有回退** |
| E31 | `src/thread/syscall_cp.c`（**0 字节**） | 空文件（仅占位，被 arch 同名对象替换） | `syscall_cp.s` **无实质通用回退** |

### H. 落点只读核验（本任务未改 musl）
| # | 检查 | 值 |
|---|---|---|
| E32 | `.work/source/<name>/` `VERSION` | `1.2.6` |
| E33 | `rev-parse HEAD` | `9fa28ece…`（= 锁 commit） |
| E34 | `git status --porcelain` | **空**（未改动，只读查证） |
| E35 | `grep -rn '__thread ' src/ ldso/ include/ crt/` | 命中 **0**（musl 自身**无 `__thread` 关键字**用法；`__thread_list_lock` 非关键字） |

## arch/dadao 最小必需面（**候选 / 待定**，供后续 port 任务消费）

> 命名 = v5 现场口径（`rb3`=TP，`contract-abi.md §1.2`；`contracts/abi.yaml` `reserved_rb: [2,3]`）。**标「候选」者待 P0 契约 / ADR 定**。

1. **硬必需（P1 静态最小面即需）** —— 满足 §C/§B：
   - `arch/dadao/pthread_arch.h`：`__get_tp()`（读 **`rb3`**/rbtp；v5 已有跨 bank 指令 **`rb2rd`** 候选，`contracts/opcodes.yaml::rb2rd_orri_rb`）+ `TLS_ABOVE_TP` / `GAP_ABOVE_TP` / `DTP_OFFSET`（布局值**候选/待定**，见下「注」）+ `MC_PC`（**依赖 signal 帧 ABI，待定/`[OPEN]`**）。
   - `src/thread/dadao/__set_thread_area.s`：写 **`rb3`** = TP、返回 0（**纯寄存器写，非 syscall**；v5 无 `SYS_set_thread_area`）。跨 bank 写候选 **`rb2rb`**（`contracts/opcodes.yaml::rb2rb_orri_rb`）。
   - `arch/dadao/` 其余（`INFRA-076t` 清单）：`syscall_arch.h`（`__syscallN`）、`crt_arch.h`、`atomic_arch.h`、`kstat.h`、`bits/*`。
   - **syscall 号表**：`SYS_set_tid_address`（E25）须在映射契约内（`SPEC-138t` 面）。
2. **parity（全 18 arch 提供；**有通用回退** ⇒ 缺则降级，非必链接失败）** —— §D/§G：
   - `src/thread/dadao/syscall_cp.s`：`__syscall_cp_asm` + `__cp_begin`/`__cp_end`/`__cp_cancel`（取消点）。**通用回退 = `src/thread/syscall_cp.c`（**0 字节空文件**，E31）** ⇒ 若取消机制（`pthread_cancel.o`）入链，`__syscall_cp_asm` 未定义 ⇒ **链接失败**；是否入链由弱/强符号选中决定 —— **该点未在本机工具链实测 ⇒ 标「分析/待实测」**。
   - `src/thread/dadao/clone.s`（`__clone`）：**通用回退 = `src/thread/clone.c`（返回 `-ENOSYS`，E29）** ⇒ 缺则线程创建运行期失败（**非**链接失败）。
   - `src/thread/dadao/__unmapself.s`：**通用回退 = `src/thread/__unmapself.c`（E30）**。
   - **机理（事实）**：`Makefile` 的 `REPLACED_OBJS`（E28）——arch 同名对象**替换**同名通用对象。
3. **动态链接面（P2）**：`src/ldso/dadao/{tlsdesc.s, dlsym.s}` + `arch/dadao/reloc.h` 的 **TLS 重定位映射（候选）**：
   - **候选**（`REL_*`，v5 `R_DADAO_*` 编号/公式**待 P0 契约 + ADR 逐条确认**，参 `ADR-0019`/`ADR-0025` §Consequences）：`REL_DTPMOD`（动态 TLS 模块号）、`REL_DTPOFF`（模块内偏移）、`REL_TPOFF`（LE/IE 经 TP 偏移）、`REL_TLSDESC`（可选优化形态）；另 `REL_SYMBOLIC`/`REL_PLT`/`REL_RELATIVE`/`REL_COPY`（非 TLS，但 `reloc.h` 须齐）。
4. **`rb3`/TP 约定必需项（事实）**：`rb3` = TP（`contract-abi.md §1.2` 表 + `§4.5`），且 `rb3` 为 **reserved（编译器不得分配）**（`ADR-0018 C6`）——与「TP 由运行期/`__set_thread_area` 独占」一致。

> **注（事实 vs 待定）**：`TLS_ABOVE_TP`/`GAP_ABOVE_TP`/`DTP_OFFSET` **布局值**只影响「编译期 `__thread` 访问代码」与「动态 TLS 槽值」；musl **自身** 不生成 `__thread` 访问（`grep -rl '__thread ' src` 在 1.2.6 树内无命中）⇒ 对 **P1（无 `__thread`）无运行期后果**，但**必须选一套自洽值**使 `__init_tls.c` 的 `#ifdef TLS_ABOVE_TP` 分支可编译链接（**候选值**：对齐 riscv64 `TLS_ABOVE_TP` + `GAP_ABOVE_TP 0`，**待定**）。

## 影响判定（**标注「分析」**）

1. **对 `ADR-0025 D5` 的建议（分析）**：musl **硬依赖** TP+TCB/TLS ⇒ 按 `D5` 口径（「若硬依赖则自动纳入 M8」）**TLS/线程指针自动纳入 M8**。**范围界定（分析）**：纳入的是「**TP + TCB/TLS 区**（P1 即需）」与「**线程/取消点 arch 支撑**（parity）」；**完整的 `__thread`/TLS 重定位语义**随 **P2 动态链接** 走（其重定位类型**待 P0 契约逐条确认**，本任务**不代 decide**）。
2. **对 musl 移植范围（P1 静态）的影响（分析）**：P1 **不能**跳过 TP/TLS——`errno`/`exit`/stdio/`read`/`write` 均经 `__pthread_self()`。故 `arch/dadao/pthread_arch.h` + `__set_thread_area` + `rb3` 约定为 **P1 阻断项**；`syscall_cp.s`/`clone.s` 按「取消/线程机制是否入链」定。
3. **对 `llvm-test-suite` 通过面的影响（分析）**：`llvm-test-suite` 的 **free-standing 子集**不受影响（不经 musl）；一旦经 **musl（libc 测试面）** 运行，**线程类用例**（`pthread_*`、`__thread`）需 `clone.s` + TLS 重定位，属 **P2+**；**单线程 libc 用例**只需 TP/TCB。**具体通过面待 P1/P2 实现后实测**，本任务不给数。

## 验收标准

1. **证据表（§A–§H）逐条可复算**：证据脚本对每条 `文件:行` 断言片段命中；**任一不命中即非零退出**（条目数由脚本**现场统计**，不写死）。
2. **结构断言**：musl `VERSION=1.2.6` / `HEAD=9fa28ece…` / `status` 空；`__set_thread_area`、`__get_tp`、`__syscall_cp_asm` 支撑点存在；`configure` **无** TLS 配置项（`grep` 空）；`SYSCALL_NO_TLS` 读取点**仅** i386（现场统计）。
3. **可达 FAIL**：证据脚本 `--inject` 模式在**临时树**（`.work/source/<name>/` 的拷贝）上删/改一行 ⇒ 预期 FAIL；**真实树零改动**（`--inject` 不落真实树）⇒「回绿」= 重跑真实树 PASS。
4. **门控**：`make check` / `check-knowledge-refs` / `check-no-residue` / `check_issues.py` 各 **rc=0**（现场输出）。
5. 本任务书自包含（含用户原话、结论、证据、影响）；**不改** `spec/` / `contracts/` / 组件补丁 / `.work/source/<name>/`。

## 硬约束

1. 临时目录 `/tmp/opencode/<任务ID>/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`。
2. **不提交 git**；**禁** `git add -A`/`.`、`git checkout`/`restore`/`stash`。
3. **不改** `.work/source/<name>/` 内任何文件（只读查证）；**不改**他人任务书。
4. 文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
5. 事实与推测分开；证据不足处明写「证据不足」；结论须与真实输出逐条对齐。

## 完成区

**测试结果**：证据脚本 `--selfcheck` 三阶段全过 —— 阶段1 真实树 PASS **52/52**；阶段2 注入 **3** 处反例（1 line-evidence + 2 structural）**均可达 FAIL**；阶段3 回绿 PASS 52/52；脚本 rc=**0**。（断言计数由脚本**现场统计**，不写死。）
**修改文件**：
- 新增 `.tao/tasks/spec/SPEC-140t-musl-TLS硬依赖查证.md`（本任务书）
- 新增 `.work/evidence/SPEC-140t/run.sh`、`.work/log/spec/SPEC-140t-selfcheck.log`（`.work/` 已 gitignore，不入 git）
- **未改**：`.work/source/<name>/`（musl，只读）、`spec/`、`contracts/`、组件补丁、他人任务书、`.tao/knowledge/`
**验收结果**（真实输出/退出码）：
- `bash .work/evidence/SPEC-140t/run.sh --selfcheck` → **rc=0**（自检判定 4 项全 PASS；日志 见 `.work/log/<模块>/`）
- `make check`(L1) → **rc=0**（tail：`repository checks (L1): PASS`）
- `make check-knowledge-refs` → **rc=0**；`make check-no-residue` → **rc=0**；`python3 tools/infra/check_issues.py` → **rc=0**
- `.work/source/<name>/` `git status --porcelain` = **空**（只读查证，未改动）
**新发现/坑**：
1. musl **硬依赖「TP + 含 `struct pthread` 的 TCB/TLS 区」**（**非**仅 threads）：`errno`/`exit`/stdio 锁/`read`/`write`/`close` 全经 `__pthread_self()`；`__init_tls` **无条件** 调用、失败 `a_crash()` ⇒ **P1 静态单线程亦不可省**。
2. `TLS_*` 重定位（`REL_DTPMOD/DTPOFF/TPOFF/TLSDESC`）**条件依赖**（仅 `__thread`/动态 TLS 需要）——与「TP 必需」须**分开**表述，勿混。
3. musl **无**「无 TLS」配置开关；`SYSCALL_NO_TLS` 只服务 i386 `gs` 特例（全树唯一读取点 `arch/i386/syscall_arch.h:6`）。
4. musl `Makefile` 的 `REPLACED_OBJS`：**arch 同名对象替换通用对象** ⇒ `clone.s`/`__unmapself.s` 有通用回退（`-ENOSYS`/`CRTJMP`）；`syscall_cp.s` 的通用回退仅是 **0 字节空文件**。
5. `src/thread/syscall_cp.c` 上游即 **0 字节**（占位符，非损坏）。
6. 参考仓 `DADAO-0628` 用 **`rb4`**=TP；**v5 现场为 `rb3`**（`contract-abi §1.2`）——**不可照搬编号**。
**遗留问题**（均=任务书明示的「分析/待定」项，非缺陷）：
- `syscall_cp.s` 在「取消机制入链 ⇒ 是否链接失败」的判定 **未在本机工具链实测**（无 dadao musl port）⇒ 标 **分析/待实测**，归 P1 实现任务验证。
- `TLS_ABOVE_TP/GAP_ABOVE_TP/DTP_OFFSET` 布局值、TLS 重定位 `R_DADAO_*` 编号 = **候选/待 P0 契约 + ADR 逐条确认**（本任务不 decide）。
- `ADR-0025 D5` 是否「自动纳入 M8」= **建议**（见「影响判定 §1」），**待用户裁定**。

## 审阅记录

#### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：任务书全文 + `.work/evidence/SPEC-140t/run.sh`（逐行）。重点：结论是否被证据支撑、是否与事实/推测分离、断言是否可达 FAIL、计数是否写死。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 「`clone.s`/`__unmapself.s` 条件必需」未核 musl 的 arch/通用**替换**机制 | ✅已修 | 新增 §G `E28–E31`（`Makefile:28-29` `REPLACED_OBJS`；`clone.c:6`；`__unmapself.c:23`；`syscall_cp.c` 0B）+ 改 §3 item2 表述 | 脚本新增 4 条断言全 PASS（现场 PASS=52） |
| F2 「`syscall_cp.s` 未定义 ⇒ 链接失败」表述过强（未限定「取消机制入链」） | ✅已修 | §3 item2 限定条件 + 标「分析/待实测」 | 同上；任务书 §3 已含限定语 |
| F3 验收标准写死「34 条」计数 | ✅已修 | 改为「计数由脚本**现场统计**」 | 脚本现场统计 52（≠ 旧写死值）⇒ 写死值已消除 |
| F4 注入仅覆盖 line-evidence 一类 | ✅已修 | `build_inject_tree` 增 2 处 structural 注入（0B 占位、parity 计数） | 阶段2 检出 **3** 项 FAIL（1 line-evidence + 2 structural） |
| F5 §注「musl 无 `__thread`」为**引述**，未自证 | ✅已修 | 新增 `E35` + 脚本断言（`grep -rn '__thread '` = 0） | 脚本 `musl 自身无 __thread 访问（keyword）` PASS |
| F6 证据脚本「还原」如何体现（真实树零改动） | ✅已修（说明） | 脚本注释 + 自检阶段3「回绿」= 重跑真实树；**真实树全程未写** | 阶段1/3 计数一致 + `.work/source/<name>/` status 空 |

**判据**：无 `.tao/knowledge/` 更新（本任务只产结论+证据；沉淀归主会话 `/complete`）。所有 finding 已修 ⇒ 状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**抽检（≥10 条 `文件:行`，逐条亲读 musl 1.2.6 = `9fa28ece…`/`VERSION=1.2.6`/status 空，均已独立核）**：E1/E2（`__errno_location.c:6`、`errno.h:16`）、E3（`pthread_impl.h:119/122` 两支宏均经 `__get_tp()`、无「无 TP」分支）、E4（`riscv64/pthread_arch.h:4`）、E5/E6/E7/E8（`__libc_start_main.c:39` 无条件 `__init_tls(aux)`；`__init_tls.c:148-150` 失败 `a_crash()`；`:18` 写 TP、`:22` `SYS_set_tid_address`；`:105` `if (tls_phdr)`/`:145` `builtin_tls` 仍 `__init_tp`）、E9/E10（`__set_thread_area.c:8` `-ENOSYS` 回退；`riscv64/__set_thread_area.s:4` 纯寄存器写）、E11/E12（`pthread_cancel.c:10/29/33`；`__syscall_cp.c:13` 弱别名）、E13/E14/E15（`read/write.c:6`、`close.c:16`、`exit.c:38`、`__lockfile.c:6`）、E16/E18（`dynlink.c:1776/1783` 早写 TP、`:498` `REL_DTPMOD`/`:516` `REL_TLSDESC`）、E19/E20/E21、E22/E23/E24、E25、E28/E29/E30/E31 ⇒ **28 条全相符**，无 ✗。
**「无 TLS 配置」独立核**：`grep -nE 'tls|TLS|thread' configure` = **空（rc=1）**，configure 选项面（shared/static/optimize/wrapper/malloc）无 TLS 项 ✓；`SYSCALL_NO_TLS` 全树 = 2 定义（`dynlink.c:2`、`__init_tls.c:1`）+ **唯一读取点** `arch/i386/syscall_arch.h:6`（选 `int $128` vs `call *%%gs:16`，仅 i386 `gs` 特例）✓；「无 TP 回退/替代路径」grep 无命中 ✓。
**「条件依赖」核（≥3）**：`REL_DTPMOD/DTPOFF/TPOFF/TLSDESC` 仅现于 `ldso/dynlink.c` + `src/internal/dynlink.h` + 各 `arch/*/reloc.h`；`tlsdesc.s:17`（`ld t2,-8(tp)`）与 `__tls_get_addr.c:5` 均服务动态/GD TLS ✓；`grep -rn '__thread ' src/ ldso/ include/ crt/` = **0** ⇒ musl 自身不触发编译期 `__thread` ✓。「静态单线程亦不可省 TP/TCB」有据（E5 无条件 + E6 致命 + errno/exit/stdio/IO 经 TP），未夸大 ✓。
**最小必需面核**：`__get_tp()` 消费点 = `pthread_impl.h:119/122`（经 `pthread_impl.h:14` 无条件 `#include "pthread_arch.h"`，18/18 arch 均供）；`__set_thread_area`（E9 回退 `-ENOSYS` ⇒ E6 `a_crash`）+ `SYS_set_tid_address`（E7/E25）对应成立 ✓。回退核（亲验）：`Makefile:28-29` `REPLACED_OBJS`/`filter-out` = arch 同名对象替换通用对象；`clone.c:6` `-ENOSYS`、`__unmapself.c:23` `CRTJMP` 有实质回退，`syscall_cp.c` = **0B** 空占位（无实质回退）✓；parity 现场计数 arch=18、`syscall_cp.s`=18、`clone.s`=18 ✓。
**影响分析标注核**：§影响判定 3 条均带「（分析）」、布局值/重定位编号标「候选/待定」、`syscall_cp` 链接判定标「分析/待实测」、未给通过面数字 ✓。
**门控（亲跑，未 `tee`）**：`make check` rc=**0**（`repository checks (L1): PASS`）；`check-knowledge-refs` rc=**0**（0 悬空）；`check-no-residue` rc=**0**；`check_issues.py` rc=**0**。
**证据脚本审 + 重跑**：`.work/evidence/<任务ID>/run.sh` 逐条断言均有可达 FAIL 路径（`check_ev` 缺文件/不命中即 `bad`）；parity 计数现场统计、不写死；注入只写 `/tmp` 拷贝、真实树零写入 ✓。重跑 `--selfcheck` → **rc=0**（阶段1 PASS 52/52、阶段2 检出 3 FAIL、阶段3 回绿、阶段1/3 一致）。
**独立反例（reviewer 自注入，非 engineer 自检）**：`cp`+md5 备份 `exit.c`（md5=`06bf737528ef2d2be50c8a735ff98ae4`）→ 篡改 `:38` 为 `int tid = 0;` → 同脚本 `--check` **rc=1**（FAIL：`src/exit/exit.c:38` + `git status clean`）→ `cp` 还原，**md5 相等** + musl `status --porcelain` 空 → 回绿 `--check` **PASS=52 FAIL=0 rc=0**（禁用 `git checkout/restore/stash` ✓）。
**约束核验**：未改 musl 树（status 空）/ `spec/` / `contracts/` / 他人任务书 ✓；工作区快照对账：本任务零足迹（任务书 md5 前后均 `34beb30b…`），唯一快照差异 = `manifests/components.lock.toml` 在审查期间被**其他 actor** 提交（非本任务文件，reviewer 未动）✓。
**非阻断 finding**：N1 `E17` 结论「`__dls3` 再设 TP（无条件）」措辞过强——`dynlink.c:2032` 实位于 `if (initial_tls != builtin_tls)` 内（TP 已由 `:1783` 无条件建立，主结论不受影响）；建议改「条件性再设」。N2 上述并发快照差异（仅记录）。
**判决：Accepted**（验收命令块全部亲跑通过、硬约束无违反；无阻断项）。
