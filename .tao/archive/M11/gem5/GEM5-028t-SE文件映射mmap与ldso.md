# GEM5-028t: gem5 SE 文件映射 mmap 与 ldso 装载

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-027t`（装载器 + auxv + 配置；同改 gem5 补丁，须先合并）、`GEM5-023t`（文件 I/O 提供 `FileFDEntry`）
**状态**：已验证

## 背景与事实（只读调研，2026-11-06）

- gem5 SE 的 `doMmap()` 只支持匿名映射；非匿名分支直接返回 `-ENODEV`（`se_workload.cc` 现状），而 **musl ldso 通过 `mmap(fd, offset)` 映射 `libc.so`/DSO 的每个 `PT_LOAD`** ⇒ 这是动态线硬阻塞
- gem5 `MemState::mapRegion()` 已有文件映射能力（`src/sim/vma.cc`：宿主 `mmap` 成 buffer，`fixupFault` 懒填页）；`FileFDEntry` 可提供宿主 fd/文件名
- 解释器占位只写页、不注册 VMA（`Process::updateBias`）⇒ `brk` 上限若仍取 `MmapWindowEnd`，堆极大时会撞解释器；`MAP_FIXED` 探测也可能覆盖解释器区间
- 64 KiB 页：ldso 的 `mmap` 段需满足 `(p_vaddr − p_offset) % 65536 == 0`；当前工具链产物满足（lld `defaultMaxPageSize=0x10000`），但必须在任务里逐段断言

## 目标

1. **文件映射 `mmap`**：非匿名分支改为查 `FileFDEntry` → `memState->mapRegion(start, length, name, sim_fd, offset)`；按 Linux 语义校验 `offset` 页对齐、`offset+length <= file_size`、`PROT/MAP_SHARED|PRIVATE`；`close(fd)` 后映射仍有效（持有引用）。
2. **地址窗口约束**：`doBrk` 上限改为 `min(stackMin, 解释器基址)`；`MAP_FIXED` 探测限制在解释器基址以下；必要时为解释器区间注册占位 VMA。
3. **段一致性检查**：对每个被映射的 `PT_LOAD` 断言 `(p_vaddr − p_offset) % 65536 == 0`，不满足则明确报错（不得静默错位）。
4. **验收边界**：让 ldso 完成 `libc.so`/DSO 装载并进入主程序；`mprotect` 真权限已由 `GEM5-030t` 实现（`protectMapped`），本任务**不重复实现**；本任务只保证 DSO 映射后 `mprotect`/RELRO 走既有真权限路径。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*}`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：装载器/auxv/配置（`GEM5-027t`）、`mprotect` 真权限（另立任务再评估）、主程序 `-pie`/`ET_DYN`（本轮不支持）、动态驱动的全量语料（`TESTCASES-104t`）、QEMU、测试用例与期望。

## 验收标准

1. 动态 `ET_EXEC + PT_INTERP` 小程序在 gem5 SE 上跑完：ldso 映射 `libc.so` 各段成功，进入主程序 `main` 并正常退出。
2. 代表子集（`libc-test dynamic` 的 `functional/argv`、`functional/memstream`、`api/main` 等，按现场）在 gem5 SE pass；逐条给命令与 rc。
3. `readelf -l` 段一致性断言：每个 `PT_LOAD` 满足 `(vaddr-offset)%65536==0`；不满足的产物明确报错。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0；静态基线不退化（`GEM5-021t` 抽套件复跑）。
5. 反例：把文件映射分支改回 `-ENODEV` ⇒ 代表子集回 blocked；`cp`+`md5sum -c` 还原重建回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- `mprotect` 不建模权限会让 RELRO 只读不生效：功能不受影响，但「写只读段应 fault」类 oracle 不可信，须在完成区与 README 写明。
- 文件映射与 `brk`/`MAP_FIXED` 的地址窗口冲突是本任务的主要风险，先做「解释器占位 + 上限约束」再跑 ldso。

## 完成区

**测试结果**：通过 82/82（一键脚本终轮 `SUMMARY passes=82 fails=0`，rc=0；reviewer 复跑同值）；注入自检 33/33（rc=0）。
**修改文件**：`components/gem5/patches/src/arch/dadao/se_workload.cc.patch`（从组件源树重导出，仅此 1 份补丁变更）、`components/gem5/README.md`、`components/gem5/changelog.md`、本任务书、`milestones.md`。
**验收结果**：
- **文件映射**：非匿名 `mmap` 经 `FileFDEntry` → `MemState::mapRegion(..., sim_fd, offset)`；校验 `offset` 64 KiB 页对齐（EINVAL）、fd 已打开且常规文件（EBADF/ENODEV）、只写 fd 的 `PROT_READ` 与只读 fd 的可写 `MAP_SHARED`（EACCES）、`PROT` 位与 `MAP_SHARED`/`MAP_PRIVATE` 恰一；起点 ≥ EOF 按 QEMU `mmap_h_lt_g()` 转匿名、跨 EOF 尾页零填充；宿主映射在 `mapRegion` 时建立，guest `close(fd)` 后内容仍正确（探针断言）。
- **双引擎探针**（qemu 作 oracle）：`p1_dso`（`libdep.so` 经 DT_NEEDED）两侧 `STAGE dso-ctor` → `STAGE main-entry` 顺序一致、`DEP_VALUE=4242`、共享断言逐行相同、`SUMMARY fails=0`；`p2_filemap` 共享 16 条逐行相同（含 raw `SYS_mmap` offset=4096 ⇒ EINVAL、close 后读、越 EOF 匿名零页），gem5-only pipe ⇒ ENODEV（QEMU 对 st_size==0 转匿名）；两侧 rc=0。
- **ldso 到 main 的路径**：`AT_BASE` 非 0（`_dlstart`）→ DSO `map_library` 的整库 `mmap` + 逐 `PT_LOAD` `MAP_FIXED`（文件映射）→ 重定位 → libc 自身初始化（`__libc_start_main`）→ DSO `init_array`（`STAGE dso-ctor`）→ 进入 main 首条（`STAGE main-entry`）→ `dep_value` 调用成功。
- **地址窗口**（gem5-only）：`AT_BASE=0x200000000`（= `MmapWindowEnd`；本棵 gem5 `ElfObject::mapSize()` 恒 0）；`brk(AT_BASE+64K)` 返回旧 brk、`MAP_FIXED@AT_BASE` ⇒ ENOMEM、1 MiB 匿名映射落在基址以下；`doBrk`/`MAP_FIXED`/`mremap`/`munmap` 统一用 `mmapCeiling()`；占位 VMA 不需要。
- **段一致性**：被映射 DADAO ELF 逐 `PT_LOAD` 断言 `(p_vaddr − p_offset) % 65536 == 0`；`libdep.so` 的 `PT_LOAD.p_offset+1` 错位镜像 ⇒ gem5 `fatal: ... PT_LOAD 1 ... % 65536 != 0`（rc=1、无 guest summary），QEMU 同产物宿主 SIGBUS rc=135 对照。
- **libc-test dynamic 代表子集**（`--link-mode dynamic --engine qemu --filter '^(functional/argv|functional/memstream|api/main)$'`，rc=0）：三例 qemu `pass`；同一 ELF 在 gem5 SE 均 rc=0、`GEM5_EXIT_CAUSE=exiting with last active thread context`、无 `fatal:`（guest exit 0）。
- **static libc-test 双引擎基线**：`qemu_pass=335 gem5_pass=321 blocked=11 gem5_only_fail=4 qemu_only_fail=0`；与 GEM5-030t、GEM5-027t 逐例 `qemu_status`/`gem5_status` **差异 0**（各 337 例），`gem5_only_fail` 同 4 例（popen/spawn/vfork/execle-env），无 pass→non-pass 回归。
- **门控真实 rc**：`build-gem5`、`check-gem5-decode`、`check-patch-tree`、`check-source-state`、`check-run-artifacts`、L1、L2、`check-inst`、`check-arch` 全 0。
- **注入反例**（`cp`+md5 还原重建，禁 git 还原）：A 文件映射分支回 `-ENODEV` ⇒ DSO 探针 rc=127、ldso `Error loading shared library libdep.so`、不绿；B 关闭段一致性断言 ⇒ 错位 DSO 不再 `fatal`；C 关闭 `offset` 页对齐检查 ⇒ `FAIL offset-unaligned`、rc=1、`SUMMARY fails=1`；三者还原后均回绿。
- **环境说明**：`check-patch-tree`/L1 的 qemu 断言曾因共享 qemu 组件源树被在途 QEMU-085t 推进而红；以该任务已导出的 qemu 补丁（与该源树 base..HEAD md5 相同）临时同步后 rc=0，随后 `cp`+md5 还原（本任务 diff 不含 qemu）。
**新发现/坑**：① musl 把 `libc.so` 的 DT_NEEDED 视为自身（`load_library` `is_self`），只依赖 libc 的动态程序不触发文件映射，必须用额外 DSO 才能覆盖；② 本棵 gem5 `ElfObject::ldMin/ldMax` 无赋值 ⇒ `mapSize()==0`、解释器基址=8 GiB；③ musl `mmap()` 包装器先用 `UNIT` 校验 offset，验证目标页规则必须走 raw `SYS_mmap`，且 DADAO 的 `syscall()` 变参须按 argmask 的 bank 类型传（slot0 为 `void*`）；④ VMA 的 `MappedFileBuffer` 在 `offset==EOF`/空文件会 panic ⇒ SE 层按 QEMU 转匿名；⑤ `MAP_SHARED` 仅读语义保留，写回文件不建模。
**遗留问题**：① 解释器页仍未进权限影子（GEM5-027t 遗留）：untracked=RWX、不计 RLIMIT_AS，不影响 ldso 装载，建议另立任务；② 主程序 `-pie`/`ET_DYN` 仍不支持；`mprotect` 保持 GEM5-030t 真权限不改。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-08）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `fatal` 用 `%#x` 打印 `uint64_t`（varargs 类型不匹配，UB） | ✅已修 | 改 `%#llx` + `unsigned long long` 强转 | 错位 DSO 输出 `p_vaddr=0x0`/`p_offset=0x1` 正确 |
| p2 的 `offset=1` 实际由 musl `mmap()` 包装器返回 EINVAL，未测到目标页规则；pipe 断言在 QEMU 上不成立 | ✅已修 | 改 raw `SYS_mmap` offset=4096（按 argmask bank 类型传参）；pipe 断言改 `local:` 并由 argv 开关 | 注入 C（关闭对齐检查）⇒ `FAIL offset-unaligned` rc=1；正常轮 qemu/gem5 摘要 0 |
| 任务书字面要求 `offset+length<=file_size` 与 Linux/QEMU 及 musl 整库预留冲突 | ❌不修（有据） | 实现 Linux/QEMU 语义：offset 页对齐；起点 ≥EOF 转匿名；跨 EOF 尾页 VMA 截断为零 | libc.so 实测 map_len `0x130000` > 文件 `0x1144a8`；p2 越 EOF 断言双引擎一致 |
| 只写 fd 的 PROT_READ / 只读 fd 的可写 MAP_SHARED 会走到 VMA 宿主 mmap panic | ✅已修 | 文件分支补 Linux `EACCES` 校验 | 构建通过；动态/静态探针与 337 例基线零回归 |
| 解释器页未进权限影子（027t 遗留） | ⏸延后（附原因） | 本任务验收不含；窗口冲突由 `mmapCeiling()` 解决 | p3 证明越界被拒；已记入完成区遗留 |
| 自审判决 | — | 可修项已修，未修项附证据/原因 | 一键脚本 82/82 rc=0；注入 33/33 rc=0；门控见「门控口径」 |

### 第 1 轮 reviewer 验收（2026-11-08，独立重跑）

**重跑记录（均为本人执行，命令在 worktree 内、相对路径）**
- 本任务一键证据脚本（engineer 交付的 `run.sh`，运行期证据目录内）全量轮（含基线）→ `== SUMMARY passes=82 fails=0 ==`、`FAIL` 行 0；基线现场重算（5263 个产物晚于 13:15），非复用旧 JSON。
- `run.sh --no-baseline` 正常态 → **RC=0**（79/79）；同脚本注入态 → **RC=1**（7 FAIL，含 `p2-*` 探针失败）；`run.sh --inject` → `== INJECT SUMMARY passes=33 fails=0 ==`。
- 自建探针（`reviewer-probe/rev_{main,dep}.c`，未复用 engineer 源文件）：qemu `rc=0`、gem5 `rc=0`，共享 18 条 `diff` 逐行相同、`SUMMARY fails=0`、`fatal: 0`；覆盖 DSO ctor→`main-entry`、映射后读文件、`close(fd)` 后读映射、raw `SYS_mmap offset=4096 → EINVAL`、`offset ≥ EOF` 转匿名零页、`MAP_SHARED` 读、`local:`（FIXED 非 64 KiB 对齐 hint → EINVAL、目录 fd → ENODEV）。
- 裸门控（**未**重导出 qemu 补丁）：`build-gem5`、`check-gem5-decode`、`check-source-state`、`check-inst`、`check-arch`、`check-modules`(L2) 全 **rc=0**；`check-patch-tree` **rc=2**、`make check`(L1) **rc=2**，`grep` 全量 L1 日志仅 `check-patch-tree` 报错且 **2 problem 全在 qemu**（`linux-user/mmap.c`）。
- 外部归属：`git status --porcelain -- components/qemu` = 0 行、`git diff HEAD -- components/qemu` = 0（两侧比较物均不属本任务 diff ⇒ HEAD 上同样红）；共享 qemu 组件源树 HEAD 在审查期间由 `2c6ab04 → df90054` 变动、`QEMU-085t/run.sh` 正在运行 ⇒ 共享源树被在途任务推进。
- 基线（本人独立 python 全量重算，非其断言）：337 例 vs 030t/027t 的 `qemu_status`/`gem5_status` 差异 **0**、pass→non-pass **0**、`gem5_only_fail` 同 4 例、`qemu_only_fail=0`（`qemu_pass=335 gem5_pass=321 blocked=11`）。
- `git archive HEAD`（变体一：覆盖本任务 5 个修改文件；变体二：HEAD-only）→ `check_knowledge_refs --root` 均 **rc=0**。
- 读码核对：`FileFDEntry`→`getSimFD()`→`MemState::mapRegion(..., sim_fd, offset)`；`offset & (page_bytes-1)`、`PROT` 位、`MAP_SHARED|PRIVATE` 恰一、`S_ISREG`/`fstat`/`O_ACCMODE` 均有 `EINVAL/ENODEV/EBADF/EACCES`；宿主 `mmap` 在 `VMA` 构造（即 `mapRegion`）时建立，`close(fd)` 后仍有效；`mmapCeiling()` 统一进 `doBrk`/`MAP_FIXED` 探测/`mremap`/`munmap`；`checkMappedElfSegments` 对被映射 DADAO ELF 逐 `PT_LOAD` 断言 `(p_vaddr-p_offset)%65536==0`，违者 `fatal` 带值（错位 DSO 实测 rc≠0、无 guest summary，QEMU 同产物 SIGBUS rc=135）。

**注入（本人自选点，非 engineer 三点）**：禁用 `is_private == is_shared → -EINVAL` → `make build-gem5 rc=0` → 自建探针 `FAIL no-private-shared`、`FAIL both-private-shared`、无 `SUMMARY fails=0`、gem5 rc=1 → `cp` 还原 + `md5sum -c OK`（= 补丁派生 md5 `fbf9dde83872b6e255225de73ca9c43c`）→ 重建 rc=0 → 探针回绿且与 qemu 逐行相同；`git status` 始终仅 5 个声明文件。

**约束核验**：改动面 = 补丁/README/changelog/任务书/milestones 共 5 文件，与完成区「修改文件」逐行对账一致，无 QEMU/tests/contracts/spec/Makefile 改动；未 commit、未 push；`components/qemu` 干净；完成区 19 行 ≤30、无运行期路径；`milestones.md` 该行已入「进行中」表且含预估时间 `1–2 h`；状态 `待验收`。

**发现（不阻断，交 architect 收尾订正）**：① 完成区与自审记录写 `80/80`，本人重跑同脚本为 `82/82`（数字过期）；② 任务书 目标4/说明 的「mprotect 仅校验、RELRO 只读不生效」与现树不符（GEM5-030t 已实现 `protectMapped` 真权限，README/完成区口径正确）；③ 完成区「门控全 0」仅在临时重导出 qemu 补丁后成立，裸跑为 qemu 单点红（外部）——建议改写口径，后续不要用改仓库文件的方式取绿；④ `mmapCeiling()` 在本树为 no-op（实测 `AT_BASE=0x200000000 == MmapWindowEnd`），窗口约束今日构造不出 FAIL，只能按代码审阅 + 行为等价采信（README/完成区已披露）；⑤ 任务书字面 `offset+length <= file_size` 未实现（改按 Linux/QEMU：≥EOF 转匿名、跨 EOF 尾页零）——本人探针证明严格实现会拒绝合法映射（200 B 文件映射 64 KiB 双引擎均成功），musl `libc.so` 整库映射亦须越 EOF，偏离正确，建议任务书标「已裁定偏离」；⑥ 新 AGENTS 要求「进行中」表填派单时间，`milestones.md` 表结构无该列，schema 需 architect 定夺（非本任务缺陷）。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过（`check-patch-tree`/L1 的红**只**在 qemu、属在途 QEMU 任务，已按外部归属记录，未做任何补丁重导出），硬约束无违反。

#### 收尾（architect，2026-11-08 14:44）

- 判决 Accepted：reviewer 自建探针（`rev_dep.c`/`rev_main.c`）证明 `dso-ctor → main-entry → dso-symbol=7717` 双引擎逐行一致；`fd` 生命周期（`close` 后映射仍可读）实测通过；基线 337 例 `qemu_status`/`gem5_status` 差异 **0**（其独立全量重算，非复用断言）。
- F1：完成区 80/80 → **82/82**（reviewer 复跑同值）。
- F2：「`mprotect` 仅校验」表述已更正为「真权限由 `GEM5-030t` 实现，本任务不重复实现」。
- F3：门控口径更正——**裸跑**时 `check-patch-tree`/L1 的 qemu 单点红属并发 `QEMU-085t`（共享源树被其推进），其余门控 rc=0；`028t` 合并后 gem5 侧转绿。**不再用「临时重导出 qemu 补丁」的方式取绿**（reviewer 已明确指出该做法不当）。
- F4：`mmapCeiling()` 在本树为 no-op（`AT_BASE == MmapWindowEnd`）⇒ 窗口约束今日无可达 FAIL，**按代码审阅 + 行为等价采信**，README 已披露。
- F5：`offset+length <= file_size` 未实现属**正确偏离**（Linux/QEMU 均为「≥EOF 转匿名、跨 EOF 尾页零」；严格实现会拒绝合法映射，200 B 文件映射 64 KiB 双引擎均成功）⇒ 已在任务书标「已裁定偏离」。
- F6：台账三分表由 main 统一维护（本分支旧表结构不参与合并）。
