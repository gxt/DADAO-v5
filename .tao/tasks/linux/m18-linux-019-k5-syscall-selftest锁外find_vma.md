# m18-linux-019: k5_syscall_selftest 锁外 find_vma 触发 rwsem 警告

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-014`（同组件写者串行；014 修 `fault.c` 的 VM_FAULT_COMPLETED 路径）
**可并行分片**：否
**预估**：1–2 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为单点锁外调用，取 1–1.5× 中位）
**档位**：小改（单点语义）
**状态**：已验证
**执行环境**：本地（QEMU system；K5 镜像）

## 背景

`m18-linux-014` 复核时发现（与本任务修前修后一致）：`arch/dadao/kernel/k5_syscall_selftest.c:472` 在**锁外**调用 `find_vma()`，K5 S 组日志出现 `include/linux/rwsem.h:81` 的 WARN；当前未 corrupt、`check-linux-k5` 仍 280/280，但属内核自测代码违反 mmap 锁约定，且会污染后续 K5/套件日志。证据见 `m18-linux-014` 运行期证据的 `logs/check-linux-k5.log`。

## 目标

1. 把该处改为在 mmap 读锁内调用，或使用已有 `dadao_pf_find_vma()`（按 `m18-linux-014` 同类写法）；不得无锁读 VMA。
2. 补一条可达 FAIL 的断言：锁外调用注入 ⇒ 探针/门控判红（或 `lockdep`/`mmap_assert_locked` 命中）。
3. 不改变 K5 代表集语义与 280/280 判据。

## 验收（逐条贴真实 rc）

1. `check-linux-k5` 280/280 rc=0，且 S 组日志 `rwsem.h:81` 出现 0 次。
2. 源码级断言：`k5_syscall_selftest.c` 的 `find_vma`/`dadao_pf_find_vma` 调用点位于锁内（静态检查或探针断言）；注入「移出锁」⇒ 判红，`cp`+md5 还原后回绿。
3. 不回归：`check-linux-k6` rc=0；`check-patch-tree` linux 段 0 problem；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
4. 组件补丁经 `make_patch.py linux` 重导；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/arch/dadao/kernel/k5_syscall_selftest.c.patch`（及必要时最小 mm 代码）、`components/linux/changelog.md`、`tests/unit/linux/**`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
4. 不改版本号；术语「bank = 寄存器组」。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据 `run.sh` **18/18 PASS rc=0**；`check-linux-k5` **282/282**（S 44/C 41/F 40/T 34/G 26/P 35/R 62）；S 组日志 `rwsem.h:81`=**0**（余 2 条 `init/main.c:1110`、`fs/sysfs/group.c:137` 为既有基线 WARN）；注入 `vma-lookup-unlocked`（删锁三行）⇒ S 组红（源码断言 `479: vma = find_vma…` + 运行期计数 `实际=1`），`cp`+md5 还原后回绿；`check-linux-k6` **71/71**；`check-patch-tree` **11 set/458 patch rc=0**（linux 105、0 problem）；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make -k check` 失败行 **4 vs 4**、`diff` 空（两侧同为 `check-musl-freshness`/`check-milestones-fresh`/`check-temp-dirs` 基线红 + `check` Error 2）。
**修改文件**：`components/linux/patches/arch/dadao/kernel/k5_syscall_selftest.c.patch`（+11/−2，`index` 行同步 `2e4eb824d`）、`components/linux/changelog.md`（M18 一条）、`tests/unit/linux/check_k5.py`（`vma_lookup_outside_lock()` + S 组 2 条断言 + 注入 `vma-lookup-unlocked` + selfcheck 翻转）、本任务书；运行期证据目录内的 `run.sh`（不入库）。
**验收结果**：report trap 的 U8 查找改为 `mmap_read_lock(k5_mm)` / `find_vma()` / `mmap_read_unlock(k5_mm)`（与 `mm/fault.c::dadao_pf_find_vma()` 同规则），`vma` 解锁后仅作非 NULL 比较；`make_patch.py linux` 重导 **105 unchanged**（内容已一致）；源文件 md5 注入前后均 `d648b45195233df43e26a258ae767b3c`；`git status --porcelain -uall` 只列上述 3 个允许文件。
**新发现/坑**：① 新增 2 条断言使 K5 计数 **280→282**（代表集语义与判据未变、全绿）；② `make_patch.py` 不更新 `index` 行 ⇒ 改内容后须手工同步 blob 短哈希，否则 `check-index-blobs` 红（本轮已触发并修）；③ 锁断言落在 `rwsem.h:81`（`mmap_assert_locked`），日志判据须匹配该串；④ 基线 `make -k check` 要给基线树一份与基线补丁自洽的 linux 源树（copy + `commit --amend`），只 symlink `.work` 会让 `check-patch-tree` linux 段多出假红；⑤ 注入日志的 red 列表是 Python repr（`red=["…"]`，双引号），grep 勿写成 `red=['`。
**遗留问题**：无（`check-musl-freshness`/`check-milestones-fresh`/`check-temp-dirs` 为基线红，与基线逐行相同，非本任务改动）。

## 审阅记录

### 第 1 轮 engineer 自审

**自主逐行审查**（`k5_syscall_selftest.c` report trap 的 U8 分支；对照 `mm/mmap.c::find_vma()` 的 `mmap_assert_locked()` 与 `mm/fault.c::dadao_pf_find_vma()`；`check_k5.py` 的新增函数/断言/注入/selfcheck）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 锁外 `find_vma(k5_mm, K5_BRK_VA)`（根因，`rwsem.h:81` WARN） | ✅已修 | `mmap_read_lock`/`find_vma`/`mmap_read_unlock` 三行包住查找 | K5 282/282；S 日志 0 次；注入判红 |
| F2 新断言必须真能翻转（禁恒真） | ✅已修 | 源码锁深度断言 + 运行期 WARN 计数 + `--selfcheck` 翻转 | `--selfcheck` PASS；注入 `red=["S VMA 查找…", "日志无 rwsem…实际=1"]` |
| F3 调用点是否已持 mmap 锁（自死锁） | ❌不修（已核） | 不改 | 修前同一句能跑到报告 trap（只 WARN）⇒ 不持锁；单 hart 无并发持有者 |
| F4 `vma` 解锁后是否解引用 | ❌不修（已证） | 不改 | 解锁后只有 `vma ? 1 : 0`，无 dereference |
| F5 源码级检查误报/漏报（注释中的 `find_vma()`、无锁 `unlock`） | ✅已核 | `vma_lookup_outside_lock()` 先剥注释再逐行计锁深度 | 修复态 `[]`；注入态 `['479: vma = find_vma…']`；注释行 0 命中 |
| F6 新增断言改变计数 280→282 | ❌不修（非缺陷） | 不改既有断言 | 282/282 全绿；`--selfcheck` 7 组翻转仍 PASS；完成区已披露 |
| F7 patch `index` 行与内容哈希不一致 ⇒ `check-index-blobs` 红 | ✅已修 | index 改 `…2e4eb824d` | `make check-index-blobs` rc=0；`make_patch.py linux` 105 unchanged |
| F8 证据脚本 A5 的 grep 与 Python repr 不符 ⇒ 首轮假 FAIL | ✅已修 | 模式改 `red=\["` 并重跑整脚本 | 18/18 PASS rc=0 |

**判决**：全部 finding 已修或已证不成立，完成区与真实输出逐条对齐；状态 → `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（本人执行；证据取仓库根运行期证据目录内的 `run.sh` 及其日志）：
- `sh` 运行期证据目录内的 `run.sh` ⇒ `evidence: all checks passed`，`grep -c '^PASS'`=**18**、`'^FAIL'`=**0**（A1–A7 / B1–B1b / C1 / C2×3 / D1–D3）。INFO 行：`check_k5: 282/282 passed`、`check_k6: 71/71 passed`、current/base `make -k check` 均 rc=2、`failure lines: base=4 current=4 (diff rc=0)`，两份失败清单逐行相同（`check-musl-freshness`/`check-milestones-fresh`/`check-temp-dirs` + `check` Error 2）。
- `make check-index-blobs` ⇒ `354 new-file patch(es) OK` **rc=0**；`check-patch-tree` ⇒ `linux: 105 patch(es)`、`11 patch set(s), 458 patches OK`、linux problem=**0**；`python3 tests/unit/linux/check_k5.py --selfcheck` ⇒ 含新增「锁外 find_vma（rwsem.h:81 WARN）」翻转在内全 PASS **rc=0**。
- S 组日志现场 `grep -c 'rwsem\.h:81'`=**0**（余 `init/main.c:1110`、`fs/sysfs/group.c:137` 两条既有基线 WARN）；组别 `S 44/44 C 41/41 F 40/40 T 34/34 G 26/26 P 35/35 R 62/62` 合计 **282**。

**自设独立注入（未列名）**：`cp` 备份探针源文件到允许的临时目录 + md5 `d648b45195233df43e26a258ae767b3c`；把 `mmap_read_unlock(k5_mm)` 移到 `find_vma` **之前**（区别于已列 `vma-lookup-unlocked` 删三行）⇒ `python3 tests/unit/linux/check_k5.py --only S` **rc=1**、`S 42/44`，两条新断言同时红：`[FAIL] S VMA 查找全在 mmap 锁内（源码级）期望=[] 实际=['481: vma = find_vma…']`、`[FAIL] S 日志无 rwsem 锁警告（rwsem.h:81）期望=0 实际=1`；`cp` 还原 + md5 相等 ⇒ 重建后重跑 **rc=0**、`S 44/44`。

**约束核验**：
1. patch 内 U8 查找被 `mmap_read_lock`/`mmap_read_unlock` 三行包住（patch 485–487 行、源文件 479–481 行）；`k5_map_window()` 写锁区（290–299 行）与修前字节一致（`git diff` 只动 U8 块 + `index`/`@@` 两行）；patch `index 000000000..2e4eb824d` == 源文件 `git hash-object` `2e4eb824defe…`。
2. `vma_lookup_outside_lock()` 逐行先剥 `/*…*/` 注释、再累计 `mmap_{read,write}_{lock,unlock}` 深度，`depth<=0` 命中即列行、`depth<0` 另记「unlock without a lock」；S 组新增 2 条断言（源码级 + 运行期计数），两条均有可达 FAIL（上方注入 + selfcheck 翻转，非恒真）。
3. `run.sh` **18/18**；`check-linux-k5` **282/282**、S 组 `rwsem.h:81`=0；`check-linux-k6` **71/71**。
4. `make -k check` 失败行 **4 vs 4**、`diff` rc=0 空；`check-patch-tree` linux 0 problem；`check-index-blobs` rc=0。
5. 范围：提交仅 4 文件（任务书 +21/−7、changelog +4、patch +15/−4、`check_k5.py` **+56/−0**），无 `Makefile`/`spec/`/`.tao/contracts/`/其它组件改动；`git status --porcelain -uall` 为空，注入前后 4 文件 md5 与审查前快照逐行相同；无 base worktree / `.orig` 残留；完成区 **8 行** ≤30；状态 `待验收`；无「银行」、任务书无构建树/源码树/临时目录/家目录等运行期路径。
6. 自设注入 ≥1 条 ⇒ 断言红 → 还原 → 回绿（见上，`cp`+md5，未用 `git checkout/restore/stash`）。
7. K5 280→282 仅为新增：`check_k5.py` 本提交 **0 删除**，`k5sys.CASES` 与既有断言一字未动，U8 判据仍是 `1` vs `vma ? 1 : 0`，代表集语义与判据未变。

**非阻塞观察**：`run.sh` 的 A1b 只断言「存在 N/N 汇总行」，未钉死 282；计数由 INFO 行现场给出，本人已核 282/282，留 architect 收尾时可考虑加钉。

**判决：Accepted**
