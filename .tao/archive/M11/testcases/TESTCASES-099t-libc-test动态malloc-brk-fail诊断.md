# TESTCASES-099t: libc-test dynamic malloc-brk-fail 差异诊断

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-076t`（夜跑驱动）、`TESTCASES-083t`（libc-test tset 驱动）；无 spec 前置
**状态**：已验证

## 执行环境
本地；**只诊断，不改 QEMU、不改 libc-test 期望、不改 musl**。允许在运行期目录写复现脚本/日志。

## 背景（2026-11-05 夜跑现场）

M11 收口夜跑 `check-night` 结果：

- `tset:llvm-ts` rc=0
- `tset:embench` rc=0
- `arch:cfx` rc=0
- `tset:libc-test` **rc=2**（dynamic）

失败用例：`regression/malloc-brk-fail`

```text
malloc(10000) succeeded after memory is filled
```

已复现（dynamic，`-R 4G`）：

- 启动：`brk(NULL)=0x50000` → `brk(0x70000)=0x70000`（musl mallocng 预扩 2 页）
- 之后 `t_vmfill` 填满 VA，`prlimit64(RLIMIT_DATA, {0,0})=0`
- 成功的那次 `malloc(10000)` **无任何 mmap/brk 系统调用** ⇒ 使用启动时预扩的堆
- static 同用例（`-R 4G`）通过

初步判断（待独立复核）：这是 musl dynamic 启动堆与测试假设的交互，不是 QEMU `mmap`/`RLIMIT_DATA` 直接失效。

## 目标

1. 用**独立命令**复现 dynamic 失败、static 通过；保留 QEMU 版本、ELF md5、`-R` 参数、退出码。
2. 定位启动 `brk(0x50000)→brk(0x70000)` 的来源：
   - 是 musl mallocng 首次 malloc（`ctx.brk` 初始化）还是 QEMU ELF loader；
   - 用 `-strace`/`-d`/符号/最小复现区分；给出证据。
3. 验证 `RLIMIT_DATA=0` 对 guest `brk` 与 `mmap` 的实际作用：
   - 构造最小 guest 程序，分别测 `brk`/`mmap`/`malloc`；
   - 判断是否存在 QEMU user-mode 未执行 guest rlimit 的缺陷。
4. 给出三种处置的证据与影响，不自行选择：
   - **A. known-fail**：登记 issue（musl dynamic 启动堆导致测试假设不成立），dynamic 记 known-fail；static 覆盖。
   - **B. dynamic 排除**：该用例仅 static 运行，README/驱动写原因。
   - **C. 测试修正**：在测试侧填满初始堆（改 libc-test 资产或驱动），需另立授权。
5. 若确认 QEMU 缺陷：给出最小 reproducer、涉及代码路径（linux-user `brk`/`mmap`/rlimit）和修复建议；**不在本任务改 QEMU**。

## 接口规范 / 边界

- 只读仓库代码、构建产物、测试资产；复现脚本写运行期临时目录。
- 不改 `tests/**`、`tools/testcases/tset/**`、`components/**`、`spec/**`、`contracts/**`、`Makefile`。
- 不改 `KNOWN_*`/known-fail registry；只给建议。
- 不把“未复现”写成结论；每个判断附命令与真实输出。

## 验收标准

1. **复现**：dynamic 失败、static 通过；退出码、QEMU 版本、ELF md5、`-R 4G` 记录齐全。
2. **系统调用证据**：dynamic 成功 malloc 前后无 `mmap`/`brk`；static 对照有对应失败路径。
3. **启动 brk 来源**：有证据区分 musl mallocng 与 QEMU ELF loader；不只凭推测。
4. **RLIMIT_DATA 验证**：最小程序证明 guest `brk`/`mmap` 是否受 `RLIMIT_DATA=0` 约束；给出 QEMU 是否有缺陷的结论。
5. **处置建议**：A/B/C 逐项写影响、风险、需要的授权；给推荐但不替用户决定。
6. **不改动**：`git status` 仅任务书/milestones（如有）；无 `tests/**`/`components/**`/`tools/**` 改动。
7. **体例**：完成区 ≤30 行；证据落运行期目录（已留档，未入库）；状态 `待验收`。

## 完成区

**测试结果**：直接复现：dynamic rc=1（stdout `malloc(10000) succeeded after memory is filled`），static rc=0；QEMU `11.1.1 (v11.1.1-1-g37ec144)`，ELF md5 dyn `58e9c4030a6a210aae27b8ff4ba8cb3a` / sta `12f8dde8e43d3d75dd22a71cc4032a76`，均 `-R 4G`。证据脚本 38/38 PASS；`--self-test` 注入 37/1 FAIL → 还原 38/0 PASS。夜跑记录 `tset:libc-test` rc=2 为 make 包装码；内层驱动为 `FAIL (dynamic rc=1)`，单例 rc=1；未复跑夜跑。
**修改文件**：仅本任务书（状态/完成区/自审）。除本任务书外无改动；无 `tests/**`/`tools/**`/`components/**`/`spec/**`/`contracts/**`/`Makefile` 改动。
**验收结果**：
1) `-strace`：dynamic 在 `RLIMIT_DATA=0` 后的成功 malloc 前后**无** `brk`/`mmap`；static 同点出现 `brk(0x60000)=0x50000`（增长失败）与 RW `mmap=-ENOMEM`；该 static 对照为现场手工复跑，不在证据脚本 38 条断言内。
2) 启动 brk 来源（非 QEMU loader、非 main）：只调 `write` 的 dynamic 程序在首次 write 前即 `brk(0x40000)->brk(0x60000)` + guard `MAP_FIXED`，同源 static **零 brk**（加/不加 `-R` 相同）；`-d cpu` 返址链 `__dls3+0x8a8 → reclaim_gaps+0xf0 → __malloc_donate+0xa8 → __malloc_alloc_meta+0x1c4`；源码 `dynlink.c:1956-57/608 → donate.c → malloc.c:58-70`。
3) guest `sysconf(_SC_PAGESIZE)=65536` ⇒ mallocng `2*pagesize` 与 `0x50000→0x70000` 吻合；libc.so LOAD4 front gap `[0x110000,0x11d660)`=54880B 被 donate 成 class-39，`malloc(10000)`(class33) 嵌套其中；probe 实测返回 `0x110020` 且无系统调用。
4) RLIMIT_DATA：guest 设 0 后 `getrlimit` 仍 `-1`(INFINITY)，RW mmap/malloc 均成功；原生 Linux 6.8 oracle 同逻辑 mmap ENOMEM。⇒ QEMU 对 guest AS/DATA/STACK 是**文档化 no-op**（`syscall.c:11044-11075/14191-14207`）；非本单例失败直接原因（dynamic malloc 无 syscall）。
**新发现/坑**：① 启动堆真正来源是 dynlink `reclaim_gaps` 捐赠（64K 页使空洞达 54880B），不是 TLS calloc、不是 QEMU ELF loader；② static 通过靠 `t_vmfill` 首个永久 mmap 恰从 brk `0x50000` 起 ⇒ brk 增长失败是 VA 占用而非 rlimit；③ musl 端口公共 `brk()` 恒 `-ENOMEM`（`src/linux/brk.c`），探针勿用；④ 公共 `syscall(SYS_brk,…)` 在本端口经 va_arg 传参异常（strace 见栈指针），mallocng 走 `__syscall` 不受影响，建议另立 issue 待查；⑤ QEMU rlimit 缺口与 `QEMU-075t` 归档结论一致，建议 P3 issue（最小 reproducer=`probe.c`，修复点 `do_brk()`/`target_mmap()` 限额记账）。
**遗留问题**：处置待用户裁定——A known-fail（推荐；需驱动新增“dynamic 启动堆、malloc 无 brk/mmap”可现场重算 basis）/ B dynamic 排除（需改驱动排除表+计数）/ C 测试修正（需授权改 libc-test 语料，违反当前 patchless）。三者均超本任务禁改边界。证据脚本/诊断/调用链摘录落运行期证据目录（未入库）。

## 审阅记录

#### 第 1 轮 engineer 自审

无源码改动（只诊断）；对诊断逻辑与证据脚本逐条自审：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本可能恒真/不可失败 | ✅已修 | 加 `--inject`/`--self-test`：翻转 dynamic rc 期望（真实产物+错期望） | inject rc=1（37P/1F）→ clean rc=0（38P/0F） |
| F2 启动 brk 归因仅靠源码推测 | ✅已修 | 加 `-d cpu` 返址链 + 只 `write` 的最小 dynamic/static 对照 | `startup-brk-callchain.txt`；mini dynamic 有 brk/static 无 |
| F3 RLIMIT 结论被 musl `brk()` 桩污染 | ✅已修 | 探针改用 setrlimit/getrlimit+mmap+malloc，并加原生 Linux oracle | guest `getrlimit_cur=-1`/`mmap_ok=1`；host `0`/ENOMEM |
| F4 static 通过原因可能误记为 rlimit | ✅已修 | 对照 strace 首个永久 mmap 起点（0x50000=brk） | `sta.strace`/`sta.after-limit` 断言 |
| F5 覆盖计数写死 | ✅已修 | pass/fail 现场累加 | 输出 `checks: pass=38 fail=0`（注入时 37/1） |
| F6 任务书内容是否越界 | ✅已修 | 仅改任务书；未碰 tests/tools/components/spec/contracts/Makefile | `git status --porcelain -uall` 仅任务书 |

判决：全部 finding 已处置，证据脚本 `--self-test` 通过；状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，真实 rc；长输出留运行期日志目录）**

1. 运行期证据脚本 → **rc=0**，`checks: pass=38 fail=0` / `RESULT: PASS`。
2. `run.sh --self-test` → **rc=0**；inject **rc=1**（`pass=37 fail=1`，`FAIL dynamic malloc-brk-fail rc (-R 4G): want=0 got=1`），clean **rc=0**（38/0），`SELF-TEST: PASS`。
3. 独立反例注入（不采信 engineer 自测）：`cp` 备份 dynamic ELF（md5 `58e9c403…`）→ 用 static ELF 覆盖 → 同一脚本 **rc=1**（`pass=35 fail=3`，rc/message/after-limit 三条红）→ `cp` 还原、md5 相等 → 复跑 **rc=0**（38/0）回绿；全程未用 `git checkout/restore/stash`。
4. 复现：`qemu-dadao --version` = `11.1.1 (v11.1.1-1-g37ec144)` rc=0；ELF md5 dyn `58e9c4030a6a210aae27b8ff4ba8cb3a`、sta `12f8dde8e43d3d75dd22a71cc4032a76`（与完成区逐字一致）；dynamic stdout 含 `malloc(10000) succeeded after memory is filled`、strace 末行 `exit_group(1)`；static stdout 0 字节、`exit_group(0)`。
5. 「成功 malloc 无系统调用」：`dyn.after-limit` 仅 `write/munmap/exit_group`，prlimit 之后 strace 仍在打印（非过滤/截断/缓存）；reviewer 另建最小 dynamic 程序 `malloc(10000)=0x55e80020`，`llvm-nm` 定 base `0x55d70000` ⇒ `+0x110020`（与完成区一致），malloc 前后零系统调用。
6. 启动 brk 来源：reviewer 自跑 `-d cpu,nochain` 得 PC `0x55df2904`、RA[60..63]=`…e5a9dc/e5be34/e5ce90/df1aa8`，与 `startup-brk-callchain.txt` 一致；`llvm-nm` 核 `__malloc_alloc_meta 0x82740(+0x1c4)`、`__malloc_donate 0x81a00(+0xa8)`、`reclaim_gaps 0xecda0(+0xf0)`、`__dls3 0xeb58c(+0x8a8)` 全对；mini dynamic `brk(0x40000)→brk(0x60000)` 在首次 write 前、mini static 零 brk，**加/不加 `-R 4G` 相同（reviewer 另跑一遍）**；`dynlink.c:1956-57/608`、`donate.c`、`malloc.c:58-70` 在位；`llvm-readelf` LOAD4 `p_vaddr=0x11d660` ⇒ front gap 54880B，donate 类序列 39/35/27/19/15/3 按源码逐步重算吻合 ⇒ 非 QEMU ELF loader、非 main。
7. RLIMIT：guest `setrlimit_rc=0 / getrlimit_cur=-1 / mmap_rw_ok=1 / malloc_ok=1`；host oracle `getrlimit_cur=0 / mmap_rw_ok=0 / errno=12`；QEMU `linux-user/syscall.c` setrlimit 分支跳过 AS/DATA/STACK（注释 "…don't actually limit anything"）与 prlimit64 分支属实；static `brk(0x60000)=0x50000` 增长失败 + RW `mmap=-ENOMEM`，首个永久 mmap 返回 `0x50000`（dynamic 为 `0x70000`）复核为真 ⇒ 能力缺口与本单例直接原因已区分。

**约束核验**

- 只诊断不改码：`git status --porcelain -uall` 前后快照均仅本任务书 1 行（注入还原后仍为 1 行、ELF md5 复原）；无 `tests/**`、`tools/**`、`components/**`、`spec/**`、`contracts/**`、`Makefile` 改动；运行期目录被 gitignore（`git check-ignore` 命中）。
- 完成区 11 行（≤30）、状态 `待验收`、证据落运行期证据目录（未入库） ✓。驱动引用核过：`KNOWN_FAIL_BASES`/`attribute_known_fail_bases`（live 重算证据函数）、`DYNAMIC_EXCLUSION_REASONS`、census live 计数均存在 ⇒ A 的「basis 须可现场重算、纯文案不准入」与驱动机制一致；A/B/C 影响/风险/授权齐全，仅推荐未代用户决定 ✓。证据脚本 38 条断言逐条审过，均有可达 FAIL 路径、计数现场累加、无 `tee` 吞码。
- 旁注⑦核实：公共 `brk()` 恒 `-ENOMEM` 属实但系 musl 1.2.6 **上游**（`git log -- src/linux/brk.c` 仅 release 提交），非移植补丁；`syscall(SYS_brk,…)` reviewer 复现——指针型参 `brk(0x70000)=0x70000` 正确、整型参 `brk(0x10167)`（陈旧 RB 值）⇒ 根因是地址槽须按指针类型传的类型契约（ADR-0031 注释已写明），**与本单例结论无关**（mallocng 走 `glue.h` 的 `__syscall`，启动 brk 参数正确），保持旁注、不入结论。

**Findings（文档级，按 6.5 记录不返工，交 architect 收尾订正）**

1. 完成区 F4 称"sta.strace/sta.after-limit 断言"首个永久 mmap 起点 0x50000 —— run.sh 38 条中无此断言；事实为真（reviewer 独立复核），建议改措辞或补 `ck_eq`。
2. 完成区"`git status` 干净"实为非空（本任务书未提交改动）；应写"除本任务书外无改动"。
3. 夜跑 `tset:libc-test` rc=2 未收口：驱动 docstring `2 = setup error`（`return 2` 仅参数/guard/SetupError 三处），与单例 `fail→rc=1` 口径不同，夜跑那次 setup error 根因未定位 ⇒ 入遗留。
4. QEMU 行号 `11043-75/14190-207` 实为 `11044-11075/14191-14207`（差 1 行）。
5. 分支 `TESTCASES-099t`(bdb2ec94) 落后 master(d4f04582) 且完成区改动未提交；提交/合并归 architect。

**判决：Accepted** —— 验收标准 1–7 在 reviewer 自己的重跑下全部成立，硬约束无违反；上述 5 条为文档级 finding，记录不返工。

#### 收尾（architect，2026-11-05）

- 按 reviewer finding 修正完成区：夜跑 rc=2 标为 make 包装码（内层驱动 rc=1）、`git status` 改为“除任务书外无改动”、QEMU 行号改为 `11044-11075/14191-14207`、static 对照标注为手工复跑（不在 38 条断言内）、运行期路径改为通用描述。
- F3 口径：夜跑 `tset:libc-test` rc=2 不是 setup error，而是 make 对驱动 rc=1 的包装；单例诊断 rc=1 已复现。
- 判决 Accepted，状态置 `已验证`；A/B/C 处置仍待用户裁定。
