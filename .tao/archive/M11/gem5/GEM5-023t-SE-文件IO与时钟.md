# GEM5-023t: gem5 SE 文件 I/O 与时钟

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-022t`（已验证：brk/mmap 已落地）、`INTEG-058t`（转换编码迁移；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与事实（`GEM5-022t` 后基线）

- gem5 SE static tset：pass 361 / blocked 217；`heap/VMA` 桶已清零
- 剩余缺口排序：**time budget 80**（非能力）、**文件 I/O 66**、**时钟 29**、信号 22、resource limits 7、IPC 6、threads 4、进程创建/信息各 1
- 代表案例（来自 `GEM5-021t` 基线）：`libc-test:functional/{fopen,fread,fdopen,openat,...}`、`stdio/*`、`printf` 家族；时钟类 `time()`/`clock()`/`clock_gettime`
- 当前 SE syscall 表已含 `brk/mmap/munmap/mremap/mprotect`（`GEM5-022t`）

## 目标

1. **文件 I/O**：实现 static tset 实际需要的 syscall 面（以基线 `reason` 里的 syscall 名为准），至少覆盖：
   - `openat`、`close`、`read`、`write`（既有）、`pread64`、`lseek`、`fstat`/`newfstatat`、`getdents64`、`dup`/`dup3`、`fcntl`（仅 tset 用到的命令）、`statfs`、`utimensat`、`readlinkat`、`unlinkat`、`mkdirat`（按需要）；
   - guest fd 表与宿主 fd 转发；`O_*` 标志、`EACCES/ENOENT/EBADF/EISDIR/ENOTDIR` 等错误码与 Linux 一致；
   - 目录遍历（`getdents64`）与 `stat` 结构体布局按 `contract-syscall`（大端、64 KiB 页）。
2. **时钟**：`clock_gettime`（CLOCK_REALTIME/MONOTONIC/PROCESS_CPUTIME_ID）、`gettimeofday`、`time`、`nanosleep`、`clock_getres`；时间源与 `TICKFREQ=1e9` 口径一致（`GEM5-019t`），不得与既有 `m5` 时钟冲突。
3. 不改测试用例与期望；不改 QEMU 语义。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh,process.*,...}`（按现场）、`components/gem5/changelog.md`、`components/gem5/README.md`（能力边界）、本任务书、`milestones.md`。

**不在范围**：信号、线程/futex、IPC（后续任务）；`convert_f2i`（`INTEG-058t`）；QEMU；测试用例与期望；`docs/TestReports/M11-三平台一致矩阵.md`。

## 验收标准

1. 基线复跑（`GEM5-021t` 驱动，static）：文件 I/O 与时钟两桶 blocked 归零（或转真实失败并给最小复现与归属）；`qemu_only_fail` 仍 0；`gem5_only_fail` 不新增（除已登记的 f2i 类）。
2. 代表案例（`functional/fopen`、`stdio/*`、`time` 类）各跑 ≥3 次结果一致。
3. `check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、`build-gem5`、L1 rc=0。
4. 反例：把 `openat` 改回未实现 ⇒ 代表案例回 blocked；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 先按基线 `reason` 统计真正用到的 syscall，再实现；不做「全 syscall 表」。
- 文件系统侧只做 SE 需要的最小语义（无权限模型时按宿主权限透传），限制写进 README。
- 与 `INTEG-058t` 串行：两者都改 `components/gem5`，必须等其合并后再开。

## 完成区

**测试结果**：`run.sh` 默认 20/20 PASS、`--inject` 22/22 PASS；双引擎探针 72/72（guest 与宿主逐项相同）；代表 7 例 ×3 全 pass 且一致；基线 static 复跑 gem5_pass 399 / blocked 188（022t 361/217），file I/O 与 time/clocks 两桶 blocked=0、other=0、qemu_only_fail=0；gem5_only_fail=1（bison，见遗留①）。门控 `check-patch-tree`/`check-source-state`/`check-inst`/`check-arch`/`make check`/`check-modules`/`build-gem5` 全 rc=0。
**修改文件**：`components/gem5/patches/src/arch/dadao/se_workload.cc.patch`、`components/gem5/README.md`、`components/gem5/changelog.md`、本任务书。
**验收结果**：证据 = 本任务证据目录的 `run.sh`、`run-default.log`、`run-inject.log` 与基线汇总；最终 gem5.opt md5 `bb2386e5ed20ec342b7237374d143e24`；源树 `HEAD=ba33d74 count=1 clean=True`。
**基线 syscall 统计（022t JSON reason）**：file I/O 66 = openat 42 + read 17 + newfstatat 3 + utimensat 1 + dup 1 + lseek 1 + statfs 1；时钟 29 = clock_gettime；other 1 = readv。实现面另按现场补 `faccessat/faccessat2`、`getdents64` 等。
**新发现/坑**：① `fcntl` 的锁指针按 musl `__dadao_argmask` 在 RD 银行（rd18），不是 rb16；② `read`/`stat` 等 copy_to_user 必须用默认（NextPage）代理，`Never` 会让惰性堆的大缓冲 EFAULT（drop3/uuencode/pcompress2 曾因此输出 0）；③ `getdents64` 只按 64 位宿主同宽做原地换序；④ REALTIME/gettimeofday/time 走宿主、MONOTONIC/CPU 走 `floor(curTick×1e9/Frequency)`，已写 README。
**遗留问题**：① `llvm-ts:bison` 新增唯一 `gem5_only_fail`：参考输出按 QEMU `2>&1` 交织，SE 分别捕获 stdout/stderr 后拼接，差异仅 stderr 行位置（字节多重集相同），非文件/时钟能力；② `sem_close-unmap`/`flockfile-list` 现落到 simulator/loader：前者需文件映射 mmap（022t 遗留③），后者为测试自定义 malloc 返回未对齐指针触 DADAO MALIGN；③ time budget 80→131（drop3/uuencode/pcompress2 现运行真实数据后超 120s，非能力）。

### 审阅记录 → 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `fcntl` 锁指针取 rb16，实际 musl argmask 为全 RD | ✅已修 | `doFcntl` 统一取 rd18 | 探针 `fcntl-setlk/getlk/unlock` 由 FAIL→PASS；72/72 |
| F2 `writeGuestBlob` 用 Never，惰性堆大 buffer 读回 EFAULT | ✅已修 | 改默认 NextPage（copy_to_user 语义） | 新增 `big-read-lazy-heap`；drop3/uuencode/pcompress2 由输出 0 转为真实运行（超时） |
| F3 `faccessat` 缺失（file I/O/other 桶） | ✅已修 | 新增 `faccessat`(48)+`faccessat2`(439) | 探针 3 条 PASS；基线两桶 0 |
| F4 bison 输出顺序差异 | ❌不修（非能力） | 无 | 同一 ELF 用 QEMU 分离捕获后拼接同样 diff，`2>&1` 合并则与参考逐字节相同；判定为驱动输出捕获模型 |
| F5 64 位宿主 dirent/stat 布局假设 | ⏸延后（已披露） | README 已知限制 | 探针 getdents64/stat 字段逐项与宿主一致 |
| F6 sem_close-unmap / flockfile-list 新暴露 | ⏸延后（越界） | 无 | 分别归文件映射 mmap、测试未对齐 malloc（simulator/loader） |

判决：F1–F3 已修，F4–F6 有明确归属/披露，无未处置的能力 finding。状态 `待验收`。

### 审阅记录 → 第 1 轮 reviewer 验收

**判决：Needs Revision**（阻断 1 条 = L1 门控 rc≠0；验收标准 1/2/4/5 与其余门控经 reviewer 亲跑复核通过）

**重跑记录（reviewer 独立执行，真实退出码）**
1. **独立全量基线**（`GEM5-021t` 驱动 static，reviewer 自建工作目录、自算聚合）：`qemu_pass=587 gem5_pass=399 blocked=188 both_pass=399 qemu_only_fail=0 gem5_only_fail=1`；gaps = time budget 131 / signals 27 / IPC 8 / limits 7 / threads 5 / process info 4 / SysV 3 / simulator-loader 2 / exec 1；**file I/O=0、time/clocks=0、other=0**，逐案扫 blocked `reason` 中属 file/clock 的号（23/24/25/34/35/43/48/56/57/61/62/63/65/67/78/79/80/88/439 与 101/113/114/169/1062）= **0**
2. **bison 归因独立复现**：同 ELF 用 QEMU 分离捕获（stdout/stderr 分文件）再拼接 ⇒ 与参考 diff（`1092d1091` / `3442a3442`，同一行 stderr 位置）；QEMU `2>&1` 合并 ⇒ **与参考逐字节相同 diff rc=0**；gem5 `combined.out` 的 diff 与之同构（多一处 driver 追加的 `exit 0`，排序后仅差该行）⇒ 归因成立
3. **reviewer 自写独立探针**（非 engineer 的 fsclock.c，双端编译对比）：gem5 **97 PASS / 0 FAIL**（含 12 项字节级断言：`stat` 128B 大端 asm-generic（mode@16/size@48/blksize@56/atime@72+80）、`statfs` 120B（f_bsize@8）、`dirent64` ino/off/reclen 大端 + reclen 8 对齐）；host glibc **85 PASS + 12 SKIP / 0 FAIL**；两侧 value 级 PASS 集合一致；errno 矩阵（ENOENT/EBADF/ENOTDIR/EISDIR/EEXIST/EINVAL/EACCES 系）逐条与宿主同值；`close` 后 EBADF、`dup` 共享 offset、`dup3` EINVAL 矩阵、stdout 关闭/恢复、路径无宿主前缀（readlinkat 输出 `target_name`）、`readlinkat`/`mkdirat`/`unlinkat`/`getdents64`/`faccessat`/`utimensat(NULL=futimens)`/lazy-heap 400 KB 大块 read 全过；无 fatal/panic
4. **门控亲跑**：`check-patch-tree` rc=0（305 patches）、`check-source-state` rc=0（gem5 `HEAD=ba33d74 count=1 clean=True`）、`check-inst` rc=0（44/44）、`check-arch` rc=0（14/14）、`check-modules` rc=0、`build-gem5` rc=0；**`make check`（L1）rc=2**
5. **engineer 脚本重跑**：`run.sh` 默认 **rc=1，19 PASS / 1 FAIL**（`FAIL gate-check expected=0 actual=2`，与我同根因）；`run.sh --inject` **rc=0，22/22 PASS**（注入→`blocked@56`→`cp`+`md5sum -c`→重建回绿）
6. **reviewer 独立注入**（不同注入点：`doOpenat` 打开失败改 `return 0` 静默成功）：重建后我的探针 **4 FAIL**（`openat-enoent/dirfd-notdir/file-as-dir/eexist-dir`，rc=4）；`cp`+`md5sum -c` 还原（`OK`，源树 `DIRTY=0`）→ 重建 → **97 PASS / 0 FAIL**，PASS 集与注入前逐字节相同（全程未用 git 还原）
7. **time budget 核实**：80→131（+51），**51/51 全部原为 file/clock 阻塞**、pass→non-pass 回归 **0**、libc 无新增 timeout；`uuencode` 600 s 预算 **pass**（219 s，输出逐字节匹配）；`pcompress2` 1280 s 跑完但暴露为 fail = **stderr 两行顺序**（源码 `fprintf(stderr,"Compile date…")`，与 bison 同构，非能力）；`drop3` 1500 s 仍超时（QEMU 5.85 s，纯速度）
8. **代表案例**：7 例 ×3 全 pass 且三次一致（run.sh `representative-consistent`）；**快照对账**：审查前后 `git status` 同为 4 文件、未提交；完成区 21 行 ≤30、全文无运行期路径

**阻断（返工指名）**：`.tao/knowledge/milestones.md` L18 `GEM5-023t` 表状态仍为 `待开始`，任务书已 `待验收` ⇒ `check-milestones-fresh` A1 `VIOLATION` ⇒ L1 `make check` **rc=2**，验收标准 3（L1 rc=0）不满足；完成区「门控全 rc=0」基于 21:33 的旧状态（改状态在 21:43 之后未复跑）。**返工**：同步该流水行状态为 `待验收`（本任务书范围含 `milestones.md`），重跑 `make check` 确认 rc=0，并重跑 `run.sh` 门控段使证据与当前树一致；只动此一处。

**非阻断 findings（architect 定夺，可随返工处理）**
- G1 `changelog.md` 写「探针 63/63」、完成区写「72/72」——轮次不同导致数字不一致（文档级）
- G2 `faccessat` 带 `AT_EMPTY_PATH`：Linux 实测 rc=0、SE 回 `-EINVAL`（校验比 Linux 严；`access()` 走 flag=0 不触发；README 未披露）
- G3 `pcompress2` 长预算暴露为 fail（stderr 顺序，与 bison 同类）；完成区 time budget 归因只写「超时」，未覆盖此情形
- G4 完成区「最终 gem5.opt md5」在任何重建后即变（`__TIME__`/build-id，022t F5 已知）——md5 仅作标识，源 md5 才是判据
- G5 `nanosleep` 立即返回（实测 240 ns vs 宿主 50 ms 真睡）——README 已披露，非静默；musl `readdir` 依赖 `d_off`（`telldir/seekdir` 未测，tset 未用）作观察项

### 审阅记录 → 第 2 轮 reviewer 验收

**判决：Accepted**（阻断项已修并经 reviewer 亲跑复核；G1/G2/G3 已处置且表述与实测一致）

**重跑记录（reviewer 独立执行，真实退出码）**
1. **L1**：`make check` **rc=0**，末行 `repository checks (L1): PASS`，`check-milestones-fresh` 无 `VIOLATION`（阻断项消除）
2. **`bash run.sh`**：**rc=0，SUMMARY pass=20 fail=0**，`PASS gate-check expected=0 actual=0`；`probe-guest-host-agree=identical`、`representative-consistent runs=3 cases=7 all_pass=True`、`baseline-file-io/clock/no-unexpected-gem5-only-fail` 全 0
3. **其余门控**：`check-patch-tree` rc=0（305 patches）、`check-source-state` rc=0（gem5 `HEAD=ba33d74 count=1 clean=True`）、`check-inst` rc=0、`check-arch` rc=0、`build-gem5` rc=0
4. **G1 复核**：`changelog.md` 已为「探针 **72/72**」，与完成区「72/72」一致；`grep 63/63` 仅命中 GEM5-004t/005t 的 **B4 条目**（`63 条指令`断言计数），与本任务无关 ⇒ 已修复
5. **G2 复核**（reviewer 探针复测，`patch` md5 未变）：guest `faccessat(AT_EMPTY_PATH)` **rc=-1 errno=22**，宿主对照 **rc=0** ⇒ README「返回 `-EINVAL`（比 Linux 严；musl `access()` 不触发）」与实测一致；探针仍 **97 PASS / 0 FAIL**
6. **G3 复核**（bison 两种捕获方式各重跑一次，QEMU rc=0）：**(a)** 分离捕获再拼接 ⇒ 与参考 **diff rc=1**，差异仍是同一行（`1092d1091`/`3442a3442`）；**(b)** `2>&1` 合并 ⇒ **diff rc=0 逐字节相同**；**(c)** 除 driver 追加行外排序多重集相同 ⇒ README「输出捕获口径…属捕获模型差异、非文件 I/O 能力」表述成立
7. **改动范围核对**：`git status` 共 5 文件 = `milestones.md`（仅 L18 一行 `待开始→待验收`）、`changelog.md`（GEM5-023t 条目）、`README.md`（G2/G3 + 文件 I/O/时钟段）、任务书（完成区+两轮审阅）、`se_workload.cc.patch` —— **patch md5 `99646150e83e49d4b17304a189d7f51a` 与第 1 轮逐字节相同**，源树 `DIRTY=0`、源文件 md5 `da2afcb0…` 通过 `md5sum -c` ⇒ **无任何代码/语义改动**，未触 `tests/**`、`tools/**`、`components/qemu/**`
8. **沿用第 1 轮有效证据**（代码 patch 未变，无需重跑全量）：独立基线 `399/188`、file I/O=0、time/clocks=0、`qemu_only_fail=0`、`gem5_only_fail=1`（bison 归因已复现）；独立注入 4 FAIL→`cp`+`md5sum -c`→回绿；完成区 10 行 ≤30、全文无运行期路径；全程未 commit

**遗留（不阻断，architect 收尾处置）**：G4 `gem5.opt` md5 仅作标识（重建即变）；G5 `nanosleep` 立即返回与 musl `readdir` 的 `d_off` 依赖均已披露/作观察；`pcompress2` 长预算暴露的 stderr 行序已由 G3 的 README 口径覆盖。

#### 收尾（architect，2026-11-06）

- 首轮唯一阻断（流水表状态未同步）已修；L1 与 `run.sh` 复跑 rc=0，patch md5 与第 1 轮逐字节相同（无代码改动）。
- 非阻断：changelog 探针数改 72/72；README 补 `faccessat AT_EMPTY_PATH → EINVAL` 与 stdout/stderr 捕获口径。
- 基线：gem5 pass 361→399、blocked 217→188；文件 I/O 与 time/clocks 两桶 blocked=0；`qemu_only_fail=0`；`gem5_only_fail=1`（bison，捕获模型）。
- 遗留：time budget 80→131（非能力）；`sem_close-unmap` 归文件映射、`flockfile-list` 归未对齐访问；`nanosleep` 立即返回、`getdents64` 依赖 64 位宿主布局。
- 判决 Accepted（第 2 轮），状态置 `已验证`。
