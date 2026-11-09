# GEM5-027t: gem5 SE 动态链接（装载器 + auxv + 配置）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-026t`（线程/TLS；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与事实

- gem5 SE 当前只接受 **静态 `ET_EXEC`**（`GEM5-014t`）；`configs/dadao/se.py --binary` 与 loader 均无 `ET_DYN`/`PT_INTERP` 路径
- `libc-test` / `llvm-ts` 的 **dynamic** 线在 QEMU user 上已全绿（libc 338 pass / llvm 214 pass），gem5 SE 尚无 dynamic 覆盖
- `ADR-0048 D4`：SE 最终覆盖完整 `tset`（静态先行，动态链接后补但不得降级）
- 参考：QEMU linux-user 的 `ET_DYN`/`PT_INTERP`/auxv/ldso 处理（只读参考，不复制代码）

## 目标

1. **loader**：放行 `ET_EXEC + PT_INTERP`（保留 `e_flags`/端序/段/入口校验）；复用 gem5 `ElfObject`/`Process::updateBias`/`interpImage`/`getStartPC`，不重写 loader。**主程序 PIE（`ET_DYN`）本轮不支持**（见「范围」）。
2. **auxv**：补 `AT_BASE`（=解释器装载基址）、`AT_FLAGS=0`、`AT_SECURE=0`、`AT_UID/EUID/GID/EGID`（**经用户 2026-11-08 裁定：取宿主 creds，原句为「显式 0」**）、`AT_EXECFN`；保留 `AT_PHDR/PHNUM/PHENT/ENTRY/PAGESZ/RANDOM/NULL`；与 QEMU 同 ELF 值一致。
3. **配置**：`configs/dadao/se.py` 增 `--interp-dir`（`m5.setInterpDir`，必须在 `Process()` 之前）与 `--redirect app=host`（`system.redirect_paths`，供 `/lib/ld-musl-dadao.so.1` 解析到 guest libc）。
4. **验收边界**：本轮只要求 ldso **能启动并越过 `_dlstart_c` 的 `AT_BASE` 分支**（PC 落解释器区间、无 fatal）；ldso 映射 DSO 的文件映射 `mmap` 归 `GEM5-028t`。
5. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{process.*,...}`、`components/gem5/patches/configs/dadao/se.py`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：文件映射 `mmap`/ldso 映射 DSO（`GEM5-028t`）、`mprotect` 真权限（保持已登记限制，另立任务再评估）、主程序 `-pie`/`ET_DYN`（本轮不支持，登记 backlog）、QEMU、测试用例与期望、矩阵。

## 验收标准

1. 动态 `ET_EXEC + PT_INTERP` 小程序在 gem5 SE 上能进入 ldso（PC 在解释器区间、越过 `AT_BASE` 分支），并打印 ldso 首条诊断。
2. auxv 探针逐项等于 QEMU 同 ELF：`AT_BASE/AT_PHDR/AT_ENTRY/AT_PAGESZ` 一致，`AT_SECURE` 为 0，`UID/EUID/GID/EGID` 与 QEMU **逐值相等**（原句为「`AT_SECURE/UID/EUID/GID/EGID` 显式为 0」；**经用户 2026-11-08 裁定修改**：四项改取宿主 creds），`AT_EXECFN` 正确。
3. 反例：`AT_BASE` 注 0 ⇒ ldso 走 static-PIE 分支失败（可达 FAIL）；`cp`+`md5sum -c` 还原重建回绿。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 事实依据（调研）：gem5 上游已有 `ET_DYN`/解释器装载/偏置/`getStartPC()`；DADAO 侧只需放行 `PT_INTERP` 并补 auxv/配置，不重写 loader。
- 解释器占位无 VMA（`updateBias` 只写页）⇒ `brk` 上限与 `MAP_FIXED` 需在 `GEM5-028t` 里一并约束，避免堆/固定映射撞解释器。
- `interp_dir` 时序：`ElfObject` 在 `Process` 构造时解析 `PT_INTERP`，`m5.setInterpDir` 必须先调用。

## 用户裁定（2026-11-08）

- **问题**：gem5 SE 启动 auxv 的 `AT_UID/EUID/GID/EGID` 口径——gem5 原实现恒 `0`，QEMU user 取宿主 `getuid()`/`geteuid()`/`getgid()`/`getegid()`，两侧不同源。
- **选项 A**：改 auxv 为宿主 creds（推荐）。
- **用户原话**：「A：改 auxv 为宿主 creds（推荐）」。

## 完成区

**测试结果**：双引擎 auxv 探针（动态 `ET_EXEC`+`PT_INTERP`，qemu 作 oracle）：共享 50 条断言逐行一致、两侧 `SUMMARY fails=0`（gem5 共 51 PASS，另 1 条 `local:AT_BASE`）；gem5 侧结构断言全 PASS（`AT_BASE=0x200000000` 处 ELF 魔数/`ET_DYN`/`PT_DYNAMIC`/`PT_LOAD` 成立），QEMU `0x55d70000` 同构；`AT_PHDR/PHNUM/PHENT/ENTRY` 现场与 ELF 头（`PT_PHDR.p_vaddr`/`e_phnum`/`e_phentsize`/`e_entry`）逐项对账、`AT_PAGESZ=0x10000`、`AT_FLAGS=0`（两侧绝对断言）、`AT_SECURE=0`、`AT_EXECFN==argv[0]`；身份字段 `AT_UID/EUID/GID/EGID` 两侧逐值相等（均宿主 creds `0x3e8`，用户 2026-11-08 裁定 A）；`--redirect /=<root>` 读到宿主文件。装载器拒绝面：ET_DYN PIE ⇒ qemu 跑通 `PIE-OK`、gem5 `fatal: only ET_EXEC ... ET_DYN/PIE is not implemented`；**静态 ET_EXEC 解释器**（`--interp-dir` 指向它）⇒ qemu 直接跑该 ELF 为 `PIE-OK`（control），gem5 rc=1 `fatal: PT_INTERP must name a position-independent (ET_DYN) interpreter; e_type=2 ...`，log 无页表 fault。反例 `AT_BASE` 注 0 ⇒ ldso 走 static-PIE 分支、gem5 在 VA 0 页表 fault（rc=134、无 `SUMMARY`），`cp`+`md5sum -c` 还原重建后回绿（注入自检 41/41 PASS）。
**修改文件**：`components/gem5/patches/src/arch/dadao/{process.cc,process.hh}.patch`、`components/gem5/patches/configs/dadao/se.py.patch`（从源树重导出）、`components/gem5/{README.md,changelog.md}`、本任务书、`milestones.md`。
**验收结果**：`build-gem5`、`check-gem5-decode`、`check-patch-tree`、`check-source-state`、L1、L2、`check-inst`、`check-arch` 全 rc=0（一键脚本带 `--baseline` 60/60 PASS（含 `check-run-artifacts`））。static libc-test（双引擎，24 并发、gem5 120 s 预算）：`qemu_pass=335 gem5_pass=321 blocked=11 gem5_only_fail=4 qemu_only_fail=0`，与 030t 同集合（popen/spawn/vfork/execle-env），逐例判定**零变化**（321 pass / 10 blocked / 4 fail / 1 known-fail / 1 known-fail-blocked 与 030t 完全一致）。
**新发现/坑**：① SE 配置按线程上下文重复列出同一 `Process`，基类 `Process::init()`（`updateBias()`）**不幂等**——每次把解释器再上移 8 GiB（64 上下文 ⇒ 512 GiB），dadao 侧加一次性 guard；② `p_filesz==0` 的 all-BSS `PT_LOAD` 是合法形态，gem5 会为其记录零长文件段，原「empty loadable segment」校验会误杀（改为跳过零长片）；③ musl `ldso` 把 `libc.*` 的 `DT_NEEDED` 视为自身（`load_library` 保留名单），故只依赖 libc 的动态程序不需要文件映射 `mmap`，本轮探针可跑完整程序（高于「越过 AT_BASE」最低边界）；④ `AT_UID/EUID/GID/EGID` 原为 gem5 `0` vs QEMU 宿主 id（不同源）；用户 2026-11-08 裁定「A：改 auxv 为宿主 creds」⇒ gem5 改 `::getuid()`/`::geteuid()`/`::getgid()`/`::getegid()`（与 SE `getuid` 系统调用同源），探针改为跨引擎逐值相等；⑤ `m5.setInterpDir` 的实际入口是 `m5.core.setInterpDir`（`from m5.core import setInterpDir`，同上游 `configs/common/FileSystemConfig.py`）；⑥ `ElfObject::relocate` 全树**无赋值**（恒 true）⇒ `relocatable()` 不能当「必须 ET_DYN」的判据（谓词无可达 FAIL 路径）；解释器类型须直接读 `elfType()`。
**遗留问题**：① 其它 DSO 的文件映射 `mmap` 归 `GEM5-028t`（当前 `mmap` 不做文件内容映射）；② 解释器页未进权限影子 `protMap`（`RLIMIT_AS` 记账不计它、其 RELRO `mprotect` 不生效），随 028t 一并注册；③ 主程序 `ET_DYN`/PIE 仍不支持（本轮显式 `fatal`，README 已记）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-08）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `Process::init()` 按上下文重复 64 次，`updateBias()` 非幂等 ⇒ 解释器落到 512 GiB、`AT_BASE` 指 8 GiB，首跑页表 fault | ✅已修 | dadao `Process::init()` 一次性 guard（`initialized`） | 探针 `AT_BASE=0x200000000`、ELF 魔数/PT_DYNAMIC 成立，程序跑到 `SUMMARY fails=0` |
| 合法 all-BSS `PT_LOAD`（`p_filesz==0`）触发「empty loadable segment」fatal | ✅已修 | 校验循环跳过零长文件片（`p_memsz==0` 本就不进 image） | 含零长 LOAD 的动态探针加载成功；ET_DYN 仍在 e_type 处 fatal |
| `AT_EXECFN` 需独立于 `argv[0]` 的字符串 | ✅已修 | 栈上新增 executable 字符串副本并写 `AT_EXECFN` | 两侧 `AT_EXECFN==argv[0]` 且为绝对路径 |
| QEMU 身份字段非 0、任务书要求 gem5 显式 0 | ⏸记录 | 不改任务口径；探针分 shared（关系式）与 `local:`（原始值） | 脚本断言 gem5 `0x0`、QEMU 宿主 id；README/changelog 记录差异 |
| `m5.setInterpDir` 属性不存在 | ✅已修 | 改 `from m5.core import setInterpDir` | 配置加载、`--interp-dir` 生效 |
| 自审判决 | — | 可修项已修 | 探针/注入/门控/基线全绿，状态 `待验收` |

### 第 1 轮 reviewer 验收（2026-11-08）

**重跑记录（全部本人执行，rc 取被检命令自身）**
1. 一键证据脚本 `run.sh --baseline` → `SUMMARY passes=49 fails=0` rc=0（8 门控逐条 `expected=0 actual=0`）；`run.sh --inject` → `INJECT SUMMARY passes=37 fails=0` rc=0、`INFO inject gem5-rc=134`、`inject-restored-md5`/`restore-gem5-green` PASS —— 与完成区 37/37、rc=134 一致（48=不带 `--baseline` 轮次、49=多 `baseline-run` 一项，非矛盾）。
2. **我的注入**（把 `validateElf` 里 `if (seg.size==0) continue` 还原成 `fatal_if`；`cp` 备份+`md5sum -c` 管理，未用 `git checkout/restore`）：`make build-gem5` rc=0 → `run.sh` **rc=1、`SUMMARY passes=26 fails=22`**（`auxv-gem5-rc/no-fatal/summary`、`gate-check-patch-tree/check-source-state/L1` 均 FAIL）→ 还原 md5 OK、重建 rc=0 → `run.sh` rc=0 `48/48` 回绿。
3. **自建探针（不复用）**：`r2_dyn.elf`（ET_EXEC+PT_INTERP、只依赖 libc）qemu rc=0 / gem5 rc=0，`R2-DYN-START…R2-DYN-DONE rc=0`、`AT_BASE=0x200000000`；`r2_need.elf`（多挂一个真实 DSO）qemu rc=0 / **gem5 rc=127** ⇒ 028t 的 DSO 映射能力未被提前；`r2_pie.elf`（ET_DYN）qemu rc=0 / gem5 rc=1 `fatal: only ET_EXEC … ET_DYN/PIE is not implemented`；静态控制 rc=0。
4. fresh `git archive` 树跑 `check_knowledge_refs --root` → **RC=1：3 条悬空全在 `GEM5-030t-SE-mprotect与rlimit强制.md`**（027t 自身 0 条）；基线按 engineer 落盘 JSON 与 030t 逐例比对：337 例 `gem5_status`/`qemu_status` 差异 **0**，`qemu_only_fail=0`、`gem5_only_fail` 同 4 例（popen/spawn/vfork/execle-env），`malloc-*`/`*-oom` 全 pass（`t_vmfill`/`t_memfill` 为用例内子测试，随用例零变化）。

**约束核验**：① 放行复用既有 `ElfObject`/`updateBias`/`interpImage`/`getStartPC`（读码，未重写装载器），`ET_DYN` 仍显式 `fatal`（实测）；② auxv 来源 `AT_BASE = getInterpreter() ? getBias() : 0`（静态 0）、`FLAGS/SECURE/UID…=0`、`AT_EXECFN` 独立栈串；`--interp-dir` 在 `process = Process()` **之前**、`--redirect` 落 `system.redirect_paths`（读码+实测生效）；③ `init()` guard 只挡进程级一次量 `updateBias+interpImage`，`execve`/`fork` 均新建 Process 对象再 `init()`，重复初始化不丢状态（读码+静态控制 rc=0+337 例零变化）；④ `p_memsz==0` 段在上游 `handleLoadableSegment` 即 warn 丢弃、**改前改后都进不了 `image.segments()`**（注入旧码对 0/0 段同样无 fatal，只误杀合法 all-BSS）；⑤ 完成区 5 行、无运行期路径，状态与 `milestones.md` 一致。

**阻断（Needs Revision）**：`fatal_if(!interp->relocatable(), …)` **恒不触发** —— `ElfObject::relocate` 全树只有声明 `bool relocate = true`、无任何赋值（`grep -rn relocate src/base/loader/`）。反例：`--interp-dir` 指向**静态 DADAO ET_EXEC** 解释器 → 该 fatal **0 次**、rc=134 `panic: Page table fault when accessing virtual address 0`；对照**静态 x86** 解释器 → `fatal: interpreter is not DADAO (x86_64)`（同块其它检查可达，唯此条不可达），即注释「absolute one would silently be started…」想防的行为仍会发生。修法（在范围内）：`process.cc` 内 `dynamic_cast<loader::ElfObject*>` 后按 `elfType() != ET_DYN` fatal（访问器已在 `elf_object.hh.patch`），或删该检查+注释并披露；改后须重建并重跑探针与注入。

**非阻断 finding**：① `run.sh` 对 `AT_FLAGS=0` 只有「存在 + 跨引擎相等」、无绝对断言（实测两侧均 0x0）；② fresh 树 3 条 `.work` 悬空属 030t 任务书，是新节点 L1 前置的既有缺口，需 architect 处理。

### 第 2 轮 engineer 返工（2026-11-08）

| reviewer finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| **阻断**：`fatal_if(!interp->relocatable(), …)` 恒不触发（`ElfObject::relocate` 全树无赋值）⇒ 静态 `ET_EXEC` 解释器仍静默进入 VA 0 panic | ✅已修 | `process.cc` 删 `relocatable()` 判据，改 `dynamic_cast<loader::ElfObject*>` + `elfType() != ET_DYN` fatal（保留 DADAO/大端检查），注释写明为何不用 `relocatable()`；README/changelog 记「解释器须 ET_DYN」 | 新增可达断言：`--interp-dir` 指向静态 `ET_EXEC` 解释器 ⇒ gem5 rc=1、`fatal: PT_INTERP must name a position-independent (ET_DYN) interpreter; e_type=2 ...`、log 无 `Page table fault`；同 ELF 直接跑 qemu rc=0 `PIE-OK`（control） |
| 非阻断：`AT_FLAGS=0` 只有「存在 + 跨引擎相等」，缺绝对断言 | ✅已修 | `run.sh` 增 `auxv-{gem5,qemu}-AT_FLAGS-abs` | 两侧均 `expected=0x0 actual=0x0` |
| 非阻断：fresh 树 3 条 `.work` 悬空在 030t 任务书 | ✅已核 | `git merge master`（含 `995a5813` 的 030t 记录清理） | 在跟踪树副本上 `check_knowledge_refs --root`：**0 悬空 PASS**（本册 0 条） |
| 重跑要求：`run.sh`（含 `--baseline`）、`--inject`、8 门控、static 双引擎逐例比对 | ✅已跑 | 重建（新 fatal 生效）后重跑 | `run.sh --baseline` **58/58 PASS rc=0**；`--inject` **39/39 PASS rc=0**（gem5 rc=134、无 `SUMMARY`；还原重建回绿）；8 门控全 rc=0；libc-test 337 例与 030t 判定差异 **0** |
| 自审判决 | — | 阻断项已修、非阻断项已处理 | 状态保持 `待验收` |

### 第 3 轮 engineer 返工（用户裁定，2026-11-08）

| 项 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 用户裁定「A：改 auxv 为宿主 creds（推荐）」 | ✅已改 | `process.cc` 的 `AT_UID/EUID/GID/EGID` 改 `::getuid()`/`::geteuid()`/`::getgid()`/`::getegid()`（与 SE `getuid` 系统调用同源）；探针四项由 `local:` 改 shared（保留 `UID==EUID`/`GID==EGID` 关系式）；`run.sh` 加跨引擎逐值 + 宿主值断言；README/changelog/验收标准第 2 条/完成区同步 | 两侧逐值相等且等于宿主 `0x3e8`：`auxv-{AT_UID,AT_EUID,AT_GID,AT_EGID}-cross-engine` 与 `auxv-gem5-*-host` 全 PASS；`run.sh --baseline` **60/60 PASS rc=0**；`--inject` **41/41 PASS rc=0**（`AT_BASE=0` 仍 rc=134 无 `SUMMARY`，还原重建回绿）；static libc-test 337 例与 030t 判定零差异 |
| 自审判决 | — | 四项已无 `local:` 兜底 | 状态保持 `待验收` |

### 第 2 轮 reviewer 验收（2026-11-08）

**重跑记录（全部本人执行，rc 取被检命令自身）**
1. `run.sh --baseline` → `SUMMARY passes=60 fails=0` **rc=0**；`run.sh --inject` → `INJECT SUMMARY passes=41 fails=0` **rc=0**（`inject gem5-rc=134`、还原 md5 OK、回绿）；还原后 `run.sh` → `59/59` rc=0。三轮里 8 门控逐条 `expected=0 actual=0`（`check-patch-tree: 7 component(s), 306 patches OK`，未受主控机并发任务波及；`check-source-state: gem5 OK HEAD=c7f7d85 count=1 clean`）。
2. **死码修复（读码 + 亲自造场景）**：新判据 `dynamic_cast<loader::ElfObject*>` + `elfType() != ET_DYN`。静态 DADAO `ET_EXEC` 解释器 ⇒ **rc=1、`fatal: … must name a position-independent (ET_DYN) interpreter; e_type=2 …`、`Page table fault` 计数 0**；对照静态 x86 解释器仍 `fatal: interpreter is not DADAO (x86_64)`；`ET_DYN` 主程序仍 `fatal: only ET_EXEC …`；静态控制 rc=0；`ET_DYN` 解释器（musl ldso）正常跑完 ⇒ 由不可达变为可达且不误杀。
3. **auxv 口径（自建探针 `r3_id.c`，不复用其探针）**：两侧均 `AT_UID=AT_EUID=AT_GID=AT_EGID=0x3e8`、`AT_SECURE=0x0`、`uid==euid`/`gid==egid` 成立、rc=0，与现场 `id -u`/`id -g` 一致；共享断言 **50 条 diff 为空**，`local:` 仅剩 `AT_BASE`（装载器选址），探针 `local_val` 只用于 `AT_BASE`、`run.sh` 对四项无 `local:` 兜底。
4. **独立注入（前几轮未用过的点）**：四项 `::getuid()` 等改 `0`（自洽错值）⇒ `run.sh` **rc=1、47/12**，恰为 `auxv-{AT_UID,AT_EUID,AT_GID,AT_EGID}-cross-engine`（`0x3e8` vs `0x0`）+ `auxv-gem5-*-host` 八条与 `auxv-engines-agree` 转红；`cp`+`md5sum -c` 还原、重建 rc=0、回绿 `59/59`。另注「只改 UID」⇒ 触发 musl `__libc_start_main` secure 分支（uid≠euid）→ `syscall 73 not implemented` fatal、rc=1，反证四项须同源一致。
5. **回归**：现场 libc-test 337 例与 030t 逐例 `gem5_status`/`qemu_status` 差异 **0**（`qemu_pass=335 gem5_pass=321 blocked=11`、`gem5_only_fail` 同 4 例、`qemu_only_fail=0`）。
6. fresh `git archive` 树 `check_knowledge_refs --root` → **RC=0 `PASS (0 悬空 …)`**；任务书全文（含完成区与各轮审阅记录）无临时目录、构建树、安装树、家目录、宿主绝对路径等运行期路径；完成区 5 行；`**状态**：待验收` 与 `milestones.md` 一致。
7. 裁定落纸：「**用户原话**：「A：改 auxv 为宿主 creds（推荐）」」原文在册；验收标准第 2 条已注明「**经用户 2026-11-08 裁定修改**：四项改取宿主 creds」。

**判决：Accepted** —— 阻断项已修且可达 FAIL 实测、auxv 四项真正跨引擎一致且无 `local:` 逃逸、用户裁定原样落纸、门控与基线全绿。

**非阻断 finding（建议 architect 收尾一并改）**：① 完成区写「gem5 共 51 PASS，另 1 条 `local:AT_BASE`」，实测 **51 = 50 shared + 1 local**（「另」易读成 52）；② 「目标 2」仍写 `AT_UID/EUID/GID/EGID=0`，与已裁定的验收标准 2 不一致（验收 2 已注明裁定，判据不受影响）。

#### 收尾（architect，2026-11-08 09:43）

- 判决 Accepted（第 2 轮）：reviewer 自建 `r3_id.c` 直读初始栈 auxv，两引擎四项均 `0x3e8`、`AT_SECURE=0`，与现场 `id -u/-g` 一致，且**无 `local:` 兜底**；死代码已换成可达的 `elfType() != ET_DYN` 判定（静态 `ET_EXEC` 解释器 ⇒ rc=1 明确 fatal、无页表 panic；`ET_DYN` 主程序仍显式拒绝）。
- 独立注入：把 auxv 四项改成自洽错值 `0` ⇒ 恰 8 条 cross-engine/host 断言与 `auxv-engines-agree` 转红；`cp`+md5 还原重建回绿。另证 `uid≠euid` 会触发 musl secure 分支 ⇒ 四项必须同源。
- 基线：libc-test 337 例与 `030t` 逐例 `gem5_status`/`qemu_status` 差异 0；`qemu_only_fail=0`。
- F1/F2：完成区数字措辞与「目标 2」按用户裁定更正（原句保留并注明修改来源）。
- 已知限制：主程序 PIE（`ET_DYN`）不支持；DSO 文件映射归 `GEM5-028t`。
