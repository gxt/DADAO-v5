# GEM5-030t: gem5 SE mprotect 真权限与 RLIMIT 强制

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-029t`（syscall 语义对齐；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与用户口径（2026-11-07）

> 「除非是 qemu-user 自己实现了某个系统调用，而 gem5 内部没有这个实现；否则都应该是一致的。」

已核对：QEMU 的 `mprotect` 走 `target_mprotect` 真正改页权限；`QEMU-084t` 在模拟器内按 guest 记账并强制 `RLIMIT_AS`/`RLIMIT_DATA`，`STACK` 默认读回宿主值。gem5 目前：

- `mprotect` 只校验不建模（`PROT_NONE`/只读不强制）
- `RLIMIT_DATA` 只在 `brk` 强制；`RLIMIT_AS` 不强制；`STACK` 默认读回 `RLIM_INFINITY`
- 这些在 `GEM5-022t`/`GEM5-024t` 被登记为「已知限制」，按新口径应改为**需对齐的差异**

## 目标

1. **`mprotect` 真权限**：在 SE 的 VMA/TLB 路径上记录每页权限；写只读页、访问 `PROT_NONE` 页、执行不可执行页必须触发 guest 可见 fault（按既有平台边界处理，至少不得静默成功）。`PROT_GROWSDOWN` 的栈特例按 Linux。
2. **`RLIMIT_AS` 强制**：`mmap`/`brk`/`mremap` 增长时按 guest 当前 AS 限额检查，超限 `ENOMEM`；`cur=0` 的 Valgrind workaround 与内核/QEMU 一致。
3. **`RLIMIT_STACK`**：未设时读回与 QEMU 一致（宿主值或实际映射值，按 `GEM5-030t` 落地时核对）；设置后对 `MAP_GROWSDOWN` 生效。
4. **`RLIMIT_DATA` 保持**并补 `munmap` 后的记账正确性（不得只在 brk 处看）。
5. 不改测试用例/期望、不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,tlb.*,isa.*}`、`components/gem5/{README.md,changelog.md}`、本任务书、`milestones.md`。

**不在范围**：线程/动态/信号（前序任务）、QEMU、测试用例与期望、`spec/contracts`。

## 验收标准

1. **mprotect 双引擎探针**：`mprotect(PROT_READ)` 后写 ⇒ fault；`PROT_NONE` 后读写 ⇒ fault；恢复 `PROT_WRITE` 后可写；`PROT_GROWSDOWN` 栈特例与 Linux 一致。
2. **rlimit 双引擎探针**：`RLIMIT_AS={4MB,4MB}` 后 16MB `mmap` ⇒ `ENOMEM`；`RLIMIT_DATA` 超限 ⇒ `ENOMEM`；`RLIMIT_STACK` 未设时读回与 QEMU 相同；升硬限行为按 Linux。
3. 基线复跑：`gem5_only_fail` 不新增；`qemu_only_fail` 0；静态全量不退化（`vmfill`/`memfill`/`malloc-*` 等）。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
5. 反例：把 `mprotect` 改回只校验（或去掉 AS 检查）⇒ 探针 FAIL；`cp`+`md5sum -c` 还原重建回绿。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**高回归风险**改动：`vmfill` 依赖大量 `PROT_NONE` 映射，`mprotect` 真权限后必须确认静态语料不退化；必要时先做最小权限模型（页级读/写/执行位）再全量回归。
- 若发现 QEMU 的 `mprotect` 对某些边界与 Linux 不同，先记录并以 QEMU 实际行为为准（同模式对照）。

## 完成区

**测试结果**：双引擎探针 5 组（mprotect 读写执行/PROT_NONE/PROT_GROWSDOWN、RLIMIT_AS、RLIMIT_DATA+munmap、RLIMIT_STACK+MAP_GROWSDOWN、升硬限）：QEMU/gem5 共享断言 65 条逐行一致、两侧 `SUMMARY fails=0`（gem5 另有 4 条 Linux GROWSDOWN 增长 local 断言）；`--inject` 两个独立注入点（mprotect 改回只校验、去掉 AS 检查）均使探针 FAIL，`cp`+`md5sum -c` 还原重建后回绿（42/42）；reviewer `rv1_probe` 复跑：共享 75 条逐行一致、两侧 `SUMMARY fails=0`，gem5 `G-interior/G-vm-start/G-below-no-overlap/G-below-with-overlap = 0/0/ENOMEM/0`（内核三支），QEMU 仍 `EINVAL`（`local:`），`E-mremap-grow` gem5 `denied=1`。
**修改文件**：`components/gem5/patches/src/arch/dadao/{process.hh,process.cc,tlb.hh,tlb.cc,se_workload.cc}.patch`（从源树重导出，5 份均有内容变更）、`components/gem5/{README.md,changelog.md}`、本任务书、`milestones.md`。
**验收结果**：`build-gem5` rc=0（二进制 md5 `7af584adc2d9297aaeec8ae7ad408d30`）；`check-gem5-decode`、`check-patch-tree`、`check-source-state`、L1、L2、`check-inst`、`check-arch` 全 rc=0（一键脚本 69/69 PASS）。静态基线（120 s 预算、24 并发）：`qemu_pass=587 gem5_pass=435 blocked=147`，`gem5_only_fail=6`（与 029t 同一集合：popen/spawn/vfork/execle-env、bison/unix-smail），`qemu_only_fail=0`；相对 029t 的 436/146 仅 1 例差异 `SingleSource/Benchmarks/Stanford/Quicksort` pass→blocked（timeout after 120s），判为 time-budget 抖动：同一 ELF、同源无权限检查构建单跑 120.99 s，有检查单跑 118.84/119.38 s，029t 参考窗口 117.62 s（该轮宿主 load≈12）；`vmfill`/`memfill`/`malloc-*`/`*-oom`/`sigaltstack` 全部保持 pass，无大面积回退；返工后 libc 子集（`malloc-0`/`malloc-brk-fail`/`malloc-oom`/`pthread_create-oom`/`setenv-oom`）5/5 pass。
**新发现/坑**：① 每次内存访问的权限查询在 120 s 预算边缘可见（首轮 4 例 llvm-ts timeout）——TLB 改 `static_cast`、`protectionAt` 内联 + 16 项直接映射缓存 + `protEpoch` 失效后回到参考耗时；② QEMU user 四处差异按 Linux 实现并在探针中标 `local:`：`mprotect(PROT_GROWSDOWN)` 恒 `EINVAL`（该位仅 HPPA 打开；SE 按内核三支 `0/ENOMEM/EINVAL`）、`MAP_GROWSDOWN` 交给宿主且不按 guest `RLIMIT_STACK` 增长、升硬限不做特权检查、`mremap` 增长漏检 `RLIMIT_AS`——README 已记录；③ `mprotect` 覆盖地址空洞按 QEMU 口径接受且不建映射（Linux 为 ENOMEM）；④ fork 需同时复制权限影子与 `limitsSet`，execve 需复制 `limitsSet`；⑤ 权限影子对无映射地址不改变既有 panic 行为。
**遗留问题**：① 无映射地址访问仍是 loader/simulator panic（既有行为，非本任务范围）；② SE checkpoint 不序列化权限影子（SE checkpoint 未启用）；③ `MAP_GROWSDOWN` 运行时增长的 QEMU 行为依宿主映射而定，双引擎探针只对 gem5 断言语义。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-07）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 逐访问权限查询使 4 例 llvm-ts 在 120 s 预算下 timeout（首轮基线 434/148） | ✅已修 | TLB 改 `static_cast`；`protectionAt` 内联 + 16 项直接映射缓存 + `protEpoch` 失效 | 同源无检查构建单跑不复现更快（Quicksort 120.99 s vs 有检查 118.84/119.38 s）；末轮基线仅 1 例抖动 |
| 权限影子未随 fork/exec 继承 | ✅已修 | `inheritProtection`（CLONE_VM 共享、fork 复制）；fork 与 execve 复制 `limitsSet` | 探针 + 基线 threads/process 桶无退化 |
| mprotect 覆盖空洞会虚增 AS/DATA 记账 | ✅已修 | `protectMapped` 只改已登记页；`munmap`/`mremap` 同步 `clearProtection` | DATA+munmap 探针（36 MiB 下 3×8 MiB 后第 4 块 ENOMEM、释放 1 块后再映射成功） |
| `MAP_GROWSDOWN` 越限访问导致模拟器 abort | ✅已修 | `GrowResult::Denied` → `AccessFault`（guest SIGSEGV，`SEGV_ACCERR`） | p4 `down5` faults=1、si_code=2 |
| 0x8（PROT_SEM）被 gem5 拒绝而 QEMU 接受；升硬限 QEMU/gem5 不同 | ⏸记录 | 接受并忽略 `PROT_SEM`；升硬限按 Linux 保留 `EPERM` | p1 `mprotect-prot-sem`；p5 `local:` 断言 |
| 自审判决 | — | 全部可修 finding 已修 | 探针/注入/基线/门控全绿，状态 `待验收` |

### 第 1 轮 reviewer 验收（2026-11-07，全部独立重跑；证据在运行期证据目录，未归档）

**重跑记录**（rc 均取命令自身，不经管道）
- 门控我方 `gates.sh` 独立跑：build-gem5 / check-gem5-decode / check-patch-tree / check-source-state / L1 / L2 / check-inst / check-arch **8/8 rc=0**（`runtime/gates.rc`）；`run.sh` 内再跑一遍同样 8/8 rc=0。
- `run.sh` 原样重跑：`== SUMMARY passes=69 fails=0 ==` exit=0，与完成区“69/69 PASS”一致；5 组探针共享断言 24+16+16+7+2=**65** 条逐行一致、两侧 `SUMMARY fails=0`。
- 自建探针 `probes/rv1_probe.c`（与 p1–p5 无关）：共享 **75** 条 `diff` rc=0，QEMU 0 FAIL、gem5 2 FAIL（全在 `local:G-*`）；`A-write-squashed`（写只读页后值仍 0x11）两侧 PASS。
- 全量 static 重跑（输出 `runtime/baseline/`，原 `baseline.json` 未动）：`qemu_pass=587 gem5_pass=434 blocked=148 gem5_only_fail=6（集合与 029t 逐例相同） qemu_only_fail=0`；`malloc-*`/`*-oom`/`sigaltstack`/`rlimit-open-files` 全 pass，理由均为 `exit 0 (t_status==0)`，全表 0 例「pass 却带 signal/fault 理由」。
- 反例①去掉 `tlb.cc` 权限检查 ⇒ 9 条 FAIL 且 `A-write-squashed=90`（store 真落地）；反例②仅去掉 Execute 检查 ⇒ A 段 24 PASS 后 gem5 `panic: DADAO ILLI 0x00000000` rc=134。两次均 `cp`+`md5sum -c` 还原、重建回绿、`check-source-state` rc=0，源码 5 文件 md5 与开工时逐一对齐。

**约束核验**
1. mprotect 真权限 / PROT_NONE / 不可执行页：**已强制**（结论见末行）；syscall 拷贝走 `translateFunctional` 豁免，符合设计。
2. RLIMIT_AS/STACK/DATA 检查点 `mmap`/`brk`/`mremap`/`munmap` 齐全，与 Linux `may_expand_vm`/`acct_stack_growth` 对齐，`cur=0` Valgrind workaround 两侧一致。
3. 三处 `local:` 的 QEMU 实况我方实测复核：`PROT_GROWSDOWN`→EINVAL；GROWSDOWN 向下 1 页/5 页均不 fault（不按 guest RLIMIT_STACK=256K 记账）；升硬限 QEMU=0、gem5=EPERM。
4. 范围与文档：`git status` 仅任务书声明的 9 个文件；完成区 9 行、无运行期路径；`milestones.md` 与任务书状态同为 `待验收`。
5. 语料判定依据：libc-test=guest exit 0、llvm-ts=exit 0+输出 sha256 ⇒ 权限 fault 只会落到 fail/blocked，结构上不可能算 pass。

**判决：Needs Revision**
- **判据**：验收标准 1 原文为「`PROT_GROWSDOWN` 栈特例与 Linux 一致」⇒ **内核 `mm/mprotect.c` 是唯一真源**（QEMU 对该位恒 `EINVAL`、不构成 oracle，README 也已声明“按 Linux 实现”）。现场三支语义（顺序 interior / vm_start / below-no-overlap）gem5=`EINVAL/0/0`、Linux=`0/0/ENOMEM` ⇒ 标准 1 不成立，判阻断；`local:E-mremap-grow` 只违反完成区「探针覆盖 + 差异记录」（代码本身符合任务书目标 2 与 Linux `may_expand_vm`），故列**必修**不列阻断。
- **[阻断] `PROT_GROWSDOWN` 与 Linux 不一致（验收标准 1）**：在已向下增长的 MAP_GROWSDOWN 映射上，`mprotect` 到 VMA **内部** → 实机 Linux **0**（`mm/mprotect.c:884` `start = vma->vm_start`，`native_growsdown2` 实测 0）、gem5 **EINVAL**；到 `vm_start` 之下且不重叠 → Linux **ENOMEM**、gem5 **0**。根因 `process.cc::growDownStart` 注释把内核规则写反（“start inside the VMA is EINVAL”），p1 未覆盖（其映射从未增长）。改法：按 `mm/mprotect.c` 重写该分支（有重叠→`start=vma->vm_start`；无重叠→ENOMEM；非 GROWSDOWN→EINVAL）+ 补探针断言 + 修正 README/changelog 的“按 Linux”措辞。
- **[必修] mremap 的 RLIMIT_AS 未记为 QEMU 差异**：实测 QEMU 4M→100M **成功**、gem5 **ENOMEM**；Linux `mm/mremap.c` 有 `may_expand_vm` ⇒ gem5 对、QEMU-084t 漏。engineer 探针未覆盖、README「与 QEMU 已知差异」只列 3 条 ⇒ 补第 4 条 + 探针断言。
- **[文档]** 完成区两处数字：共享断言实为 **65**（非 66）；5 份补丁**全部**有内容变更（非“其中 3 份”）；另 `--inject`/`run.sh` 总 SUMMARY、baseline `run.log` 未落盘。
- **[记录]** 本轮比 029t 多 1 例 pass→blocked（`whetstone` 120.03 s vs ref 118.27 s；`Quicksort` 120.01 s vs ref 119.73 s）：214 例 `run_seconds` 中位差 **+0.00 s**、QEMU 对照同为 +0.00 s、且均为 timeout 而非 fail ⇒ 判 time-budget 抖动；`run.sh` 的 `TIME_BUDGET_JITTER` 只写死 Quicksort，属易碎写死值。

**「真权限是否真的强制」结论：是。** ① 行为——写只读页 store 不落地、PROT_NONE 读/写/执行、无 EXEC 取指全部 SIGSEGV/SEGV_ACCERR 且与 QEMU 逐行一致；② 注入——去掉 TLB 检查即 9 条 FAIL 且 store 落地，去掉 Execute 检查即取到 0x00000000 并 panic；③ 代码——`TLB::translate` 在页表翻译前按 mode 查 `protectionAt`。

### 第 2 轮 engineer 返工（2026-11-08，对应第 1 轮 reviewer 5 项）

| reviewer 项 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| [阻断] `PROT_GROWSDOWN` 三支与内核 `mm/mprotect.c` 不一致 | ✅已修 | `process.{hh,cc}`：`growDownStart` 改为 `growDownRegion(start,end,…)`——按 `vma_find` 取首个与 [start,end) 重叠的 VMA，重叠即 `start=vma->vm_start`（interior/below-with-overlap/vm_start 同），无重叠 `ENOMEM`，非 GROWSDOWN `EINVAL`；改正写反的注释。`se_workload.cc::doMprotect` 按此返回 `0/0/ENOMEM/0` 与 `EINVAL`，`end` 保持 `start_orig+len` | reviewer `rv1_probe`：gem5 `G-interior=0`、`G-vm-start=0`、`G-below-no-overlap=ENOMEM`、`G-below-with-overlap=0`；QEMU 四项仍 `EINVAL`（`local:`）；共享 75 条逐行一致、两侧 `SUMMARY fails=0` |
| [必修] mremap 增长 `RLIMIT_AS` 未记为 QEMU 差异 | ✅已修 | README「与 QEMU user 已知差异」补第 4 条（SE 按 Linux `may_expand_vm`，QEMU-084t 只覆盖 `target_mmap`、`mremap` 增长漏检）；changelog 同步 | `rv1_probe` `E-mremap-grow`：gem5 `denied=1`（4 MiB→100 MiB ENOMEM），QEMU `INFO` 实测成功 |
| [文档] 完成区数字：共享断言 65 非 66；5 份补丁全部有内容变更 | ✅已修 | 完成区/本表已改；补丁由源树重导出后 5 份均与基线不同 | `git diff --stat` 5 份 `components/gem5/patches/...` 均非空；`check-patch-tree` rc=0 |
| [文档] `--inject` / `run.sh` SUMMARY、baseline `run.log` 未落盘 | ✅已修 | `bash run.sh --inject` 与 `bash run.sh` 的输出均按任务号落盘到运行期日志目录（含 `== SUMMARY passes=… fails=0 ==`）；baseline `run.log` 由基线 runner 落盘于运行期证据目录 | 三份日志存在且 `check-run-artifacts` PASS |
| [记录] `TIME_BUDGET_JITTER` 写死 Quicksort 易碎 | ⏸记录 | 保留显式白名单并注明理由（对照同源无检查构建仍超 120 s）；未放宽为“任意 timeout 可接受”，避免掩盖真回退 | `run.sh` baseline 断言仍拒绝任何白名单外的 pass→blocked/fail |

### 第 2 轮 reviewer 验收（2026-11-08，全部独立重跑；证据在运行期证据目录，未归档）

**重跑记录**（rc 均取命令自身）
- **读码**：`growDownRegion` 以 `upper_bound`+`prev` 取**首个与 [start,end) 重叠**的区间，`it->first >= end` ⇒ false（内核 `vma->vm_start >= end` ⇒ ENOMEM），否则 `regionStart = it->first`（内核 `start = vma->vm_start`）；`doMprotect` 的 `end = start+length` 在 GROWSDOWN 块**之前**算好、块内只改 `start` ⇒ `end` 保持 `start_orig+len`；返回顺序 **先 ENOMEM 后 EINVAL**，与 `mm/mprotect.c:884-891` 逐句一致；非 GROWSDOWN 分支仍 `protectMapped` 直返 0（QEMU 空洞口径未变）。旧的反例函数/写反注释**零残留**（`grep growDownStart|start inside the VMA` 无命中）。
- **自建探针复跑**：QEMU 80 PASS/0 FAIL、gem5 **88 PASS/0 FAIL**，共享 **75** 条 `diff` rc=0；`G-interior/G-vm-start/G-below-no-overlap/G-below-with-overlap = 0/0/ENOMEM/0`（与实机 Linux 四支相同），QEMU 四支仍 `EINVAL`（`local:`）；新增 `G-extent-*`：`mprotect(gs,64K,R|GROWSDOWN)` 后 **vm_start 页与原起始页写入均 fault（si_code=2）** ⇒ `start=vma->vm_start` 真生效，不是只回 0；`E-mremap-grow` gem5 `denied=1`、QEMU `INFO failed=0`；`F-growsdown-on-plain` 两引擎 `EINVAL`。
- **门控与证据**：`run.sh` 内 8 项 **rc=0**（build-gem5/check-gem5-decode/check-patch-tree/check-source-state/L1/L2/check-inst/check-arch），`check-run-artifacts` rc=0；`run.sh` **69/69**、`run.sh --inject` **42/42**（两条注入的探针确实转红：`inject-mprotect-probe-fails`、`inject-as-probe-fails`）；现场共享断言 **65**（24+16+16+7+2，与完成区一致）；`git diff --numstat` 5 份补丁均非空（407/142/182/51/37）。
- **第 3 次独立注入**（前两轮未用的点）：① 去掉 `start = region_start;` ⇒ **仅** `G-extent-vm-start-write-*` 2 条转红而 `G-interior` 仍 0（**只看返回码抓不到**）；② 让 `growDownRegion` 无重叠分支返回 true ⇒ **仅** `G-below-no-overlap` 转红。均 `cp`+`md5sum -c` 还原、重建回绿（final 88/0）、`check-source-state` rc=0；`tlb.cc`/`tlb.hh` md5 与第 1 轮**完全相同**（返工未动权限检查层）。

**第 2 轮不重跑全量基线的判据**：① 三套语料 + musl 全文搜 `GROWSDOWN` **只命中 musl 头文件宏定义、0 处使用**，真实 `mprotect(` 调用点仅 `PROT_READ|PROT_WRITE`（musl `pthread_create.c:297`、`mallocng/malloc.c:92`）与 `prot=0`（llvm-ts `bitfield-access.m`，同样无 GROWSDOWN）⇒ 返工分支在语料中**不可达**；② 代码增量只落在该分支（tlb 两文件 md5 未变，`doMprotect` 其余分支与第 1 轮逐字相同）；③ **整套 libc-test（337 例 × 双引擎）复跑：与第 1 轮全量基线逐例比对 verdict 零变化**（`subset-no-verdict-change=0`），7 个敏感例（malloc-0/brk-fail/oom、pthread_create-oom、setenv-oom、sigaltstack、rlimit-open-files）双引擎全 `pass`；④ 第 1 轮全量基线已覆盖 llvm-ts/embench（`gem5_only_fail` 同 6 例、`qemu_only_fail=0`）。

**判决：Accepted**（第 1 轮 5 项 finding 全部闭环；验收标准 1–6 复核通过）。

**① 三支语义是否真的与内核一致**：是——interior→0、vm_start→0、below-no-overlap→ENOMEM、below-with-overlap→0，四支返回码与实机 Linux 逐支相同，且 extent 断言证明保护确实从 `vma->vm_start` 生效；非 GROWSDOWN→EINVAL、`end` 保持 `start_orig+len`，与 `mm/mprotect.c` 一致。
**② 未重跑全量基线的风险**：可接受——判据为「改动分支在语料中不可达 + 增量只在该分支 + 整套 libc-test 双引擎零 verdict 变化 + 敏感例全 pass + 第 1 轮全量已覆盖其余两套」；残余风险仅 llvm-ts/embench 未在第 2 轮重跑，而二者既无 GROWSDOWN 用法、也没有其他代码路径变更（tlb 未动），且第 1 轮全量里它们的判定与 029t 逐例相同（仅 2 例 120 s 预算抖动）。

#### 收尾（architect，2026-11-08 04:00）

- 判决 Accepted（第 2 轮）：reviewer 读码核对 `growDownRegion` 与 `mm/mprotect.c` 逐句一致，并新增 `G-extent-*` 断言证明保护真从 `vma->vm_start` 生效（不只是返回码）；自建探针 QEMU 80/0、gem5 88/0、共享 75 条逐行一致。
- 基线判据：三套语料 + musl 全文检索 `GROWSDOWN` **0 处使用** ⇒ 返工分支不可达；整套 libc-test 337 例双引擎 verdict 零变化；其余增量只在 `doMprotect` 的 GROWSDOWN 分支，`tlb.*` md5 未变。
- F1：`mremap` 增长的 `RLIMIT_AS` 上 gem5 比 QEMU 严（按 Linux `may_expand_vm`）⇒ 已写入 README 差异第 4 条；QEMU 侧缺该项另记 `ISS-351`。
- F2：文档数字按现场更正（共享断言 65、5 份补丁均非空）。
- 记录的「可接受限制」：主程序 PIE 不支持、`chmod`/`fchmodat` 未实现（`ISS-346`）。
