# m19-testcases-004: tests/arch Tiny 探针迁移（entry 0x2000、SP/EXIT/DUMP）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`、`m19-testcases-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待验收

## 背景

`m19-testcases-002` 只迁了 `tests/inst` 与 `tests/ee-tiny`。`tests/arch/**` 仍有 15 份 Tiny `.lds`/`.S` 按旧入口 `0xffffff010100`、旧 SP/EXIT/DUMP 展开；新几何下会装载/执行失败。

## 目标

1. 迁 `tests/arch/{hart,time,ptw,umon,pmem,cache}` 等 Tiny 探针的 `.lds`/`.S`：entry `0x2000`、SP `0x3F000`、EXIT `0x30`、DUMP `0x800`、signature `0x1000`（若该探针使用）。
2. 按新 `machine-tiny.inc` 重新生成/对齐常量；删除旧 `0x10100`、`0x7e...` 硬编码。
3. QEMU/gem5/chipyard 跑通代表探针；地址类 `cause_info`/CFXMEM 期望按新几何更新。
4. 不改 `tests/inst`/`tests/ee-tiny`（归 testcases-002）与 picolibc（另任务）。

## 验收（逐条贴真实 rc）

1. 15 份探针全部可构建；代表探针三平台跑通。
2. `entry=0x2000`、SP/EXIT/DUMP/signature 地址与 `runtime.yaml` 一致；无旧 `0x10100` 残留。
3. **可达 FAIL ≥2 路**：① 把某探针 entry 写回 0x10100 ⇒ 装载/执行红；② 把 EXIT 写回旧 `0x7e0000` ⇒ 退出/比对红。
4. `check-inst-asm`（arch 部分）/`check-tests-index` 真实 rc；基线红逐行对照。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/arch/**` 与必要索引；不改 QEMU/gem5/chipyard 源码；不接板；完成区不写具体 `.work/**` 路径。

## 待裁定

1. **验收 3② 的「旧 `0x7e0000`」不存在**：`git log -S 0x7e0000 -- tests/` 零命中，`0x7E0000` 只作为 `escape` ciii 编码 `0x7E000000` 的前缀出现（不是地址）。本任务按「EXIT 的旧值」处理：旧 `EXITB = ENTRY + 0x7800 = 0xffffff015800`，注入② 即用它判红。
2. **arch 索引进 `machine: vast` 未改**：15 份探针的 SRAM 地址按 Tiny 新几何迁移（RTL 的 `WumingVastConfig` 复用 Tiny 的 `sramBase/appEntry`），但 `tests/arch.yaml` 仍标 `machine: vast`，`run_arch.py` 仍是 Vast-only scope。几何已按 Tiny 对齐而索引用 Vast 名义——是否改写索引/驱动口径，超出本任务（“必要索引”仅指地址），请示。

## 完成区

**测试结果**：证据脚本（运行期证据目录 `run.sh`）rc=0，9 步全过：static 40/40、build 42/42（14 份可构建 + `mode_entry` KNOWN-RED）、baseline-red 2/2、注入①②各 4/4、`gen_machine_inc --check` rc=0、`check-tests-index` rc=0、`check-arch-self-test` rc=0。运行期三平台 **BLOCKED**（见下）。
**修改文件**：`tests/arch/`：`cache/{cache_rtl.lds,cache_rtl.S,cfx5_maint.lds,cfx5_maint.S,cfx5_regs.lds,gen_cfx5_maint_tables.py}`、`hart/{cfx15.lds,cfx15.S,escape_escalation.S,README.md,check_hart.py,check_escape_rtl.py}`、`pmem/{pmem.lds,pmem.S,pmem_dma.lds,pmem_dma.S,check_pmem_dma.py}`、`power/power_rtl.lds`、`ptw/{ptw_regs.lds,ptw_sig.lds,ptw_tlb.lds,ptw_walk.lds}`、`time/{time_rtl.lds,time_rtl.S,check_time_rtl.py}`、`umon/{cfx02_regs.lds,fence_rtl.lds,mode_entry.lds,mode_entry.S}`（15 份 `.lds` 全部 + 8 份 `.S`）；未改索引、未改 QEMU/gem5/chipyard。
**验收结果**：① 15 份探针全部可构建（`llvm-mc 609b72a8…` + `ld.lld 57d59894…`，逐份 rc=0；14 份 ELF `e_entry = 0xffffff002000` 且 `PT_LOAD` 落在 `[0xffffff002000, 0xffffff022000)`）——`mode_entry.S` 为**基线红**：M18 `escape` SBZ 语义使其 5 条 `escape cfxA, [excp_cause_ip, 0]` 汇编失败，错误集与基线 `5b5b4a41` **逐行相同**（2 行判据）。② entry/SP/EXIT/DUMP/signature 与 `runtime.yaml`+`machine-tiny.inc` 两侧逐项相等；`tests/arch` 旧几何字面量（`0xffffff010100/014000/015000/015800`）残留 **0**，`0x00FFFFFF010100`（cfx5_maint 无行 PA）同步改为 `0x00FFFFFF002000`（生成器 `MMIO_LINE` 同改）。③ 可达 FAIL 2 路（`inject-entry` 把 `ptw_regs.lds` 写回 `0xffffff010100` ⇒ build rc=1 ⇒ cp+md5 还原 ⇒ rc=0；`inject-exit` 把 `time_rtl.S` EXITB 写回 `0xffffff015800` ⇒ static rc=1 ⇒ 还原 ⇒ rc=0）。④ `make check-tests-index` rc=0（503 条、旧地址残留 0）；`make check-arch-self-test` rc=0；`make check-inst-asm` rc=2 且 **基线同红**（脚本 7c 逐行断言：当前与 base `5b5b4a41` 同为 `0/274 镜像通过`——已装 QEMU `e470dc56…` 仍按 `0xffff_ff01_0100` 装载，属 `m19-qemu-001` 未合入）。
**运行期 BLOCKED（不冒充通过）**：`qemu-system-dadao`（md5 `e470dc56…`，构建于 `m19-qemu-001` 之前）对本次镜像直接报 `e_entry 0xffffff002000 is not the fixed application entry 0xffffff010100` ⇒ 三平台跑通无法判定；chipyard/gem5 的 RTL 探针同样需要 `m19-chipyard-004` 的 Tiny 新几何。
**新发现/坑**：① 这些 “`WumingVastConfig`” RTL 探针实际跑在 `WumingVastAddressMap.sramBase/appEntry = Tiny 的值`（`DadaoConfigs.scala` 里直接别名），所以几何须跟 Tiny 走——README/注释里的 “Vast” 是配置名、不是地址图，易误判。② 新 `SIGNATURE`（`+0x1000`，0x800）容量 128 槽；`cfx15` H 模式 124 槽、`pmem` 96 槽均能装下，但已接近上限。③ `EXIT_BLOCK` 全局化后探针不再需要 `ENTRY+0x7800`；`tests/arch` 无探针用栈，`SP=0x3F000` 只由 crt0 设置（不属本任务范围）。④ 基线另有 2 处既存红（与本迁移无关）：`ptw/gen_ptw_sig_tables.py --selfcheck`（`expected-divergences.yaml` 残留 RTL 逐槽例外）与 `check_cfx5_maint.py --self-test`（需基线仿真日志）；均未改。
**遗留问题**：运行期三平台（QEMU/gem5/chipyard）待 `m19-qemu-001`/`m19-chipyard-004` 合入后由后续任务判定；`mode_entry.S` 的 `escape` 语法迁移属 M18 `escape` 语义链，未在本任务修（基线同红，已登记）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行复查 `git diff`（29 文件）+ 证据脚本；发现与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `verify.py _gen_inc` 对 `("cache_oracle", inc)` 两元组取 `spec[2]` ⇒ IndexError | ✅已修 | 按生成器种类分别取 inc 名 | `verify.py build` 42/42 |
| build 的第三条断言是 `e_entry==entry and size>0`（恒真，违反「禁恒真」） | ✅已修 | 改为解析 ELF program headers：每个 SRAM 内 `PT_LOAD` 必须落在 `[entry, entry+image_window)`；注入① 即触红 | 注入① rc=1；回绿 rc=0 |
| `cfx15.S` 的 `HMON_BASE` 默认值仍是旧 SRAM 地址 `0xffffff018000`（因 `.ifndef` 顺序实际不生效，但属残留） | ✅已修 | 改为规范值 `0x0fff00000000`（与 `perm_hypv.inc` 实际生效值一致，零行为变化） | `check-arch-self-test` rc=0 |
| `cfx5_maint` 的「无行 PA」`0x00FFFFFF010100` 与生成器 `MMIO_LINE` 未随几何迁移（探针/判据两侧成对） | ✅已修 | 两侧同改 `0x00FFFFFF002000`/`0x00FFFF_FF00_2000`；static 增 2 条断言（与真源 entry 比对） | static 40/40 |
| `escape_escalation.S`（与 `cfx15.lds` 同一链接布局）的 `EXITB` 仍是旧值，未在「15 份 .lds」清单内但属同批载体 | ✅已修 | `0xffffff015800` → `0xffffff000030` | build rc=0 |
| 新 `SIGNATURE` 只有 128 槽，`cfx15` H 模式 124 槽、`pmem` 96 槽是否越界 | ❌不修（已证不越界） | — | 各 `SIG_N`/`SIG_SLOTS` 现场读取：124×8=992 ≤ 0x800 |
| `ptw_sig.lds` 的页表 PA（0x7ff0_0000 等）与新 geometry 冲突？ | ❌不修（PA 段，非 SRAM 窗口） | — | `PT_LOAD 落在 image_window 内` 过滤后仍全绿 |
| 运行期三平台未判定 | ⏸延后 | — | 旧 QEMU 直接拒新 entry（日志见完成区） |
| `mode_entry.S` 汇编失败 | ⏸延后（基线同红、属 M18 escape 链） | — | baseline-red 判据：错误集逐行相同 |

### 第 1 轮 reviewer 验收（2026-11-28）

**重跑记录**（仓库根执行运行期证据目录内的 `run.sh`，reviewer 亲自跑 3 次）：
- 首跑 rc=0：`[PASS]` 92 / `[FAIL]` 0，52 s；与 engineer 归档的运行输出逐行 diff 仅差「第 9 步变更集」栏（改动已入 commit，`git status` 空）。
- **reviewer 独立第三路注入**：`tests/arch/cache/cache_rtl.lds` 首个 `. = 0xffffff002000` 改 `0xffffff010100`（md5 12199943… → aef19f90…）⇒ `run.sh` **rc=1**，FAIL 含 `cache_rtl: lds 基址`、`旧几何字面量残留数=1`、`cache_rtl: ELF e_entry`；`cp` 还原 md5 回 12199943… ⇒ 重跑 **rc=0、92/0**，输出与首跑逐行相同（diff rc=0）。
- 脚本自带两路注入在 reviewer 首跑内均真实判红再回绿：inject-entry（`ptw_regs.lds`→0x10100，build rc 0→1→0，md5 对账相等）、inject-exit（`time_rtl.S` EXITB→0xffffff015800，static rc 0→1→0）。
- 注入前后 `tests/arch` 全树 md5 快照 diff 为空；`run.sh`/`verify.py` md5 未变；`git status --porcelain -uall` 空。

**逐项核验**：
1. 地址：`runtime.yaml` entry 0xffffff002000 / sp 0xffffff03f000 / exit 0xffffff000030 / dump 0xffffff000800 / signature 0xffffff001000 / image_window 0x20000，与 `machine-tiny.inc` 逐项相等（static 10 条 + reviewer 读文件复核）；15 份 `.lds` 首个 `. = 0xffffff002000`；各 `.S` 的 ENTRY/SIG_BUF/EXITB 全为新值；派生段 0xffffff006000（+0x4000）/0xffffff007800（+0x5800）就位。旧字面量 `010100/014000/015000/015800/018000`（大小写不敏感、全 `tests/arch`）grep 命中 **0**；残留 `0x7E…` 均为 escape 编码非地址（待裁定 1 口径）。
2. 构建：15 份中 **14 份** rc=0、e_entry=0xffffff002000、PT_LOAD 落 `[0xffffff002000, 0xffffff022000)`；reviewer 另用 readelf 独立核 cfx15/cfx02_regs（Entry 0xffffff002000，LOAD VirtAddr 0x0000ffffff002000）。`mode_entry` 为基线红。
3. 基线红：reviewer 抽 `git show 5b5b4a41` 的 `mode_entry.S` 现场汇编 vs 当前：两者 rc=1、错误同 5 条、行:列 253/269/319/330/383:17 **逐行相同**（仅文件名前缀不同）。`check-inst-asm` 我方 rc=2、0/274，与运行期证据目录内归档的基线日志全文 diff 仅差 bootrom 路径一行（两侧 bootrom md5 同 ca988215…、qemu e470dc56…）；`check-tests-index` rc=0（503 条、旧地址残留 0）、`check-arch-self-test` rc=0、`gen_machine_inc --check` rc=0。
4. 运行期：旧 QEMU 报 `e_entry 0xffffff002000 is not the fixed application entry 0xffffff010100` ⇒ 脚本记 `[BLOCKED]`、完成区写「三平台 BLOCKED、不记 PASS」，未冒充通过。
5. 越界：commit 3228d831 = 29 个 `tests/arch/**` + 任务书自身；无 QEMU/gem5/chipyard/picolibc/`tests/inst`/`tests/ee-tiny` 改动；证据目录未被 git 跟踪。
6. 需裁定 2 属实：`tests/arch.yaml` 各条 `machine: vast`、`run_arch.py` 仅收 `vast`，已登记在任务书「待裁定」。

**非阻断 finding**：① 完成区验收结果首句「15 份探针全部可构建」与同句「14 份 ELF」措辞自相矛盾（事实 = 14 可构建 + `mode_entry` 基线红，其后已如实披露）——文档措辞，交 architect 收尾改；② `mode_entry` 的 escape KNOWN-RED 未进 `issues-m19.yaml`（主会话独占、工程师路径外），仅在任务书与 m18 任务书登记，建议 architect 决定是否补登。

**判决：Accepted** —— 验收命令块在 reviewer 自己的重跑下全绿（92 PASS、rc=0）、两路注入与独立第三路注入均判红且 `cp`+md5 还原回绿、基线红逐行相同、运行期如实 BLOCKED、无越界改动。


