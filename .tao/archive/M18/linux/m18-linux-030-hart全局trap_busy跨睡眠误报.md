# m18-linux-030: hart 全局 `trap_busy` 跨睡眠误报递归（ISS-m18-012）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-028`（异步返回主因已修）、`m18-linux-007`（忙等复现器）
**可并行分片**：否（改 `components/linux`）
**预估**：2–3 h（标定：同档单点修复中位 86 min；本任务需复现 1/20 + 改守卫语义，取 1.5–2× 中位）
**档位**：中改（trap 守卫 + 缺页通道）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`，本 worktree 自建）

## 背景

`ISS-m18-012`（P1）：`traps.c:256 static volatile int dadao_trap_busy` 是**hart 全局**单标志。`dadao_trap_handler` 在 `:484` 置位后，`FROM_USER` 分支在**位仍为 1** 时调 `dadao_user_fault_from_umon` → `dadao_do_page_fault`（`mm/fault.c` 取 `mmap_read_lock`，**可睡眠**）；期间另一个任务以 `trap cfx_smon, FROM_USER` 到达，`:481` 判为递归 ⇒ `K2_FAIL_RECURSIVE` → `die mode=2 code=0xe`。

实测：`m18-linux-028` 的 20 启样本 **1/20**；签名 `ip=dadao_umon_excp+0x224`、`info=0x7f0802f5`，前一行是 `K4 umon->smon … ip=0x22110 info=0x8eb90`（缺页处理中）。与 `ISS-m18-011`（异步精确点残余）**不同源**。

## 目标

1. **复现**：用 `m18-linux-028` 的忙等探针（20 启级）取得 `1/20` 级样本，日志与现场落盘。
2. **修法**（只做最小、且**不得削弱递归检测**）：
   - 方向 A：把守卫改成**任务级**（`current` 上或 `thread_info`），hart 全局只保留“确实不可重入”的极小窗口；
   - 方向 B：进入可睡眠路径（分配/mmap 锁）前**显式清位/降级**，返回后恢复，并保证异步入口在该窗口仍安全；
   - 方向 C：二者结合。
   选择需给出依据（哪种能同时防真递归与跨任务误报），并在补丁注释写明。
3. **不得**用「遇到递归就 die 前加 retry」或「把 `K2_FAIL_RECURSIVE` 降级为 warn」掩盖。

## 验收（逐条贴真实 rc）

1. 修前：20 启 ≥1 次该签名（记录频率区间）；修后：20 启 **0 次**、且 100 启追加样本 0 次（样本数不足则写明）。
2. 现场证据：递归判定点、`dadao_trap_busy` 状态、睡眠点（`mmap_read_lock` 前后）的修前/修后对照。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现；② 构造**真递归**（例如在 `dadao_trap_handler` 内人为再触发一次同 hart 同步异常）⇒ 仍须被判定为递归（证明未削弱守卫）。
4. 不回归：K2 170/170、K5 285/285、K6 82/82、`run_suite.py --suite ltp` 两轮逐例一致、`amb_window_probe` 14/14、`--soak 300 --soak-strict` 窗口 0 且静默自旋 0。
5. 闭合 `ISS-m18-012`（`resolved_by` 指向本任务）；与 `ISS-m18-011` 的关系写明（不同源、各自独立）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`；每跑次独立目录。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues-m18.yaml`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. QEMU 用本 worktree 自建（记 md5）；不覆盖共享安装根。
4. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建；同一时刻一个长跑批。
5. 禁「重试直到绿」；命中 `ISS-m18-005/006` 时单独计数记签名。

## 待裁定

无。

## 完成区

**测试结果**：修前/修后都用 `m18-linux-028` 的忙等复现器（4 线程 × 20M 自旋，栈预驻留）：
- **修前**（pre-fix 源码 `cp`+md5，`traps.c` = `b5f16441…`，与 028 记录同值）：20 启 **0/20** → 按任务书扩到 **62 启**，**1/62** 命中 012 签名（boot-23：`recursive supv exception cause=CFXTRAP ip=dadao_umon_excp+0x224 info=0x7f0802f5 → die mode=2 code=0xe`，前一行是**另一任务**的 `K4 umon->smon`，`frame_smon=dadao_excp_save`）。样本：pass 27 / 011 残余 34（spin 30 + sigsegv 4）/ 012 **1**。
- **修后**：20 启 **0/20**、100 启追加 **0/100**（pass 50 / spin 48 / sigsegv 2）；`run.sh` 默认 20 启再测 **0/20**（pass 12 / spin 8）；合计 **140 启 0 次** 012 签名。011 残余率修前 55%（34/62）→ 修后 49%（69/140，spin 66 + sigsegv 3），同档 ⇒ 未触碰 011。
- **不回归**：K2 **170/170 rc=0**（`--qemu` 指本 worktree 自建 55cd680a）、K5 **285/285 rc=0**（门控脚本无 `--qemu` 参数，用安装根 e470dc56）、K6 **82/82 rc=0**、LTP 两轮 **PASS（14 PASS / 20/20 checks）逐例一致**（两轮 `results.json` 逐条 diff 为空）、`amb_window_probe` **14/14 rc=0**、`--soak 300 --soak-strict` **窗口 0/300、静默自旋 0、rc=0**。静态：`check-patch-tree` 12 组/464 补丁 0 problem、config-pins 101/101、changelog/knowledge-refs/check_issues 均 rc=0。
**修改文件**：`components/linux/patches/{arch/dadao/kernel/traps.c,arch/dadao/kernel/trap.S,arch/dadao/include/asm/processor.h,arch/dadao/include/asm/entry.h}.patch`、`components/linux/changelog.md`、`.tao/knowledge/issues-m18.yaml`、本任务书。
**验收结果**：可达 FAIL ≥2 路（`cp`+md5 还原 + 重建）：① **回退修复 ⇒ 复现**：`run.sh --inject revert --inject-boots 62` 把四份 pre-fix 源码放回（md5 校验）⇒ **PASS**，pre-fix 62 启 pass 31 / 012 **1**（boot-15：`ip=0x…51ba0`=`dadao_umon_excp+0x224`、`info=0x7f0802f5`、`sp`=**另一任务**的用户栈、`frame_smon=dadao_excp_save` → `die mode=2 code=0xe`）/ residual 30；`cp`+md5 还原后 3 启回绿（2 pass + 1 spin）。两轮独立 62 启样本各命中 1 次（合计 **2/124 ≈ 1/62**）；② **真递归仍判**：`run.sh --inject recursion` 构建 K2 **P9 reentry 镜像**（handler 内故障）⇒ `recursive supv exception` + `die mode=2 code=0xe`（rc=0x0e；先试过“注入 `trap cfx_smon` 嵌套”，守卫虽触发但该嵌套深度下 semihosting 报不出 die，属仪器限制、已弃用）；两路均在末尾 `cp`+md5 还原并回绿（revert 路 3 启、recursion 路 2 启；还原后又跑 3 启：2 pass / 1 个 011 残余 / 0 die）。**现场对照**：修前 supv 帧 = `dadao_excp_save`（0x200005f0000，hart 全局）→ 第二任务入口覆盖后判递归；修后帧 = 任务内核栈（`frame_smon = frame_umon-0x800`，如 `0x2002010f000`），120 启无该 die。
**新发现/坑**：① 第一个任务切换前 `current` 不可推导（early_stack 不是任务栈），守卫/帧判别不能用 `current`——改用**帧地址**（`&dadao_excp_save` ⇒ 单引导上下文）；② 帧基址必须 16 B 对齐（`call` 要求 `SP%16==0`），`SP-PT_REGS_SIZE` 不够；③ capture 之前只能碰 staged 寄存器（rd2/rd3/rb3），否则帧里存的是被改过的值；④ 012 在本机 ~1/62（20 启常 0），必须扩样；⑤ mmap 翻腾压力探针 3/3 先撞 `ISS-m18-011` 挂起（17k async 行），不能当 012 复现器；⑥ `dadao_in_frame` 只写不读（跨任务被清无影响）；⑦ 新 worktree 先 `make linux-initramfs`（要 busybox）再跑 K2/K5，否则 `No rule to make ... initramfs.cpio` 假红；⑧ 打印版“守卫值/睡眠点”trace 探针因 2/2 启先撞 `ISS-m18-011` 挂起、无故障样本，判据不可靠 ⇒ 未纳入交付（已删），改以两条 console 事实对照（见验收结果）；⑨ `k2_trap_probe.py` 的 C4 源码断言要求 `CFX_RC_ESCAPE_IP` 出现在 `trap.S`，而源树自某次改动起写 `rc10` 字面量（**pre-fix 同样不满足**）⇒ `escape_exit_intent_sources()` 在基线即抛 `SystemExit`，非本任务引入、未改该探针（不在本次范围）。
**遗留问题**：`ISS-m18-011` 残余（140 启：spin 66 + sigsegv 3）仍归 `m18-linux-029`，本任务未改异步返回路径、与 012 **不同源**；`check-temp-dirs` 红（其它任务的 5 个陈旧 `/tmp/opencode/*` 目录，非本次引入）。**reviewer findings（不阻断，Accepted）**：E1 收尾 `check-milestones-fresh` 红唯一因 `m18-linux-029` 未在本分支台账（并发环境，合并 master 后自愈）；E2 `--inject revert` 的「复现 012」判据实为「任意 die ≥1」，2/10 是 `0xe4` 误宽匹配 ⇒ 应改按签名精确匹配；E3 62/100 启 revert 假红率高（两轮 rc=1）⇒ 建议默认 ≥150 启或改用结构判据（静态帧行数）；E4 `k2_trap_probe` 的 `CFX_RC_ESCAPE_IP` 断言基线即 `SystemExit`（master 同样缺串，非本任务引入）。

## 审阅记录

### 第 1 轮 engineer 自审

范围：`traps.c`（守卫语义）、`trap.S`（supv 入口/出口帧）、`entry.h`（新宏）、`processor.h`（`trap_depth`）、证据脚本；逐行核对寄存器时序与上下文判别。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 首版无条件用 `current->thread.trap_depth`，引导早期（K1 ptw 探针第一次 supv 异常）`current` 不可推导（early_stack 无 thread_info）⇒ 在 `ld.o [0xd31,0]` 处 MALIGN、`die code=0xec` | ✅已修 | `dadao_trap_handler()` 用**帧地址**判上下文：`regs == &dadao_excp_save` 走 hart 全局单上下文标志，否则走任务计数 | 修前 console `cause=MALIGN ip=dadao_trap_handler+0x40`；修后 2/2 + 20/20 启无该异常 |
| F2 帧基址未 16 B 对齐（`call` 要求 SP%16==0，而被中断 SP 只在 call 点保证） | ✅已修 | `align_down(SP,16) - PT_REGS_SIZE`（`set.rd rd2,-16` + `and.o`） | 反汇编逐条核对 `set.ow rd2,wp0,0xfff0; and.o`，120 启无 MALIGN |
| F3 计算帧基址时用了未 staged 的 rd5/rd6，capture 会把这些错误值存进帧 | ✅已修 | 只用 rd2/rd3 + `cfx_smon cg6 rc3` 存“是否栈帧”一位，capture 后再读 | 反汇编核对 `cfx2rc scratch_regs[3]` 位于 capture 前、`cfx2rd` 在 call 前 |
| F4 帧基址要跨 C 半存活 | ✅已修 | callee-saved `rb32`；`DADAO_TRAP_RESTORE_AND_ESCAPE` 首条 `rb2rb {rb3},{rb32}` | 120 启帧地址正确（`frame_smon=frame_umon-0x800`） |
| F5 只改守卫不改帧：静态帧会被第二个任务入口覆盖，睡眠任务醒来用别人的寄存器 | ✅已修 | supv 帧按任务落内核栈（`dadao_excp_save` 只留第一个 switch 前） | 修前 die 前一行 `frame_smon=0x200005f0000`（静态）vs 修后 `0x2002010f000`（任务栈） |
| F6 028 探针 20 启 0 命中 | ✅按任务书扩样 | 追加 42 启（合计 62） | boot-23 命中，签名逐字段与 028 记录一致（`+0x224`/`0x7f0802f5`/`code=0xe`） |
| F7 自写 mmap 翻腾压力探针 3/3 先撞 011 挂起 | ❌弃用 | 删除该探针文件 | 3/3 `async≈5763`、`frame_ip=0x22104`；不作为交付 |
| F8 `run.sh --inject revert` 概率性（~1/62） | ⏸记录 | `--inject-boots` 默认 100、miss 如实 FAIL；证据目录另存 62 启样本 | 见 `repro-012/` |
| F9 `dadao_in_frame` 跨任务被清 | ❌不修 | — | grep：该变量只写不读 |
| F10 `check-temp-dirs` 红 | ⏸基线 | 其它任务的 5 个陈旧 `/tmp/opencode/*` | 日志只报其它任务目录 |
| F11 自审前取源码快照早于最后一次编辑，导致一次错误“还原” | ✅已修 | 用 `git diff | git apply -R` 精确回滚并核对 blob（`1a54426c1` == HEAD） | `git status` 空、`check-patch-tree` 464/0 |
| F12 两个改源码的证据脚本（trace pre/post）被并发启动，互相覆盖备份 ⇒ 工作树一度退回 pre-fix | ✅已修 | 用 `cp` 从 post 快照还原 4 文件 + md5 全 OK + blob == HEAD；此后**串行**执行改源码脚本 | `git status` 空、`check-patch-tree` 464/0、还原后 3 启（2 pass / 1 011 残余 / 0 die）；trace 仪器已弃用（见完成区坑⑧） |

**判决**：F1–F6、F11 已修并有复验；F7/F9 不采用/不修有依据；F8/F10 已记录。K2/K5/K6/LTP/amb/soak 全绿 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（命令 → 我自己的输出/退出码）**
1. 源树重建（按 `docs/Process-01`，只动运行期源树）：`make fetch` rc=0 → `apply_series.py --component linux/qemu/gem5/musl` = **linux 105 applied**、qemu 69、gem5 106、musl 26 → `make check-patch-tree` **rc=0，`12 patch set(s), 464 patches OK`**（重建前 12 problem 全落 016/009 文件，与派单描述一致）；`linux-defconfig` rc=0、`linux-vmlinux JOBS=32` rc=0、`build-musl` rc=0 后 `linux-initramfs` PASS。
2. 运行期证据目录内的 `run.sh`（20 启）**rc=0**：pass10 / **recursive 0** / residual10 / other0；随附静态 5 项（patch-tree、config-pins、changelog、knowledge-refs、check_issues）全 rc=0。
3. `run.sh --inject recursion` **rc=0**：`boot rc=0xe`、`K2 probe P9: first fault … handler faults`、`dadao: recursive supv exception …`、`dadao: die mode=2 code=0xe`；随后重建 rc=0、2 启 0 die ⇒ **真递归仍按名拒绝**。
4. `run.sh --inject revert`：`--inject-boots 62` **rc=1（0/62 漏检）**、`--inject-boots 100` **rc=1（0/100）**、`--inject-boots 150` **rc=0（10/150）**，其中 **8 启为精确 012 签名**（`ip=…51ba0`=`dadao_umon_excp+0x224`、`info=0x7f0802f5`、`die code=0xe`），另 2 启是无关 `unrecoverable supv exception … code=0xe4` 被宽匹配计入 ⇒ **修前复现由我独立取得**（我三轮 8/312 + 工程归档 2/124；命中率随宿主负载剧烈波动，两轮漏检按 2/2 有据重试记录）。
5. 现场对照（我统计 console）：修前轮静态帧 `dadao_excp_save` **1454 行**、修后 20 启 **0 行**（全部 `frame_umon-0x800`，如 `0x2002010f800→0x2002010f000`）⇒ 注入/还原与 per-task 帧均真实生效。
6. **独立注入→FAIL→还原→回绿**：把 `traps.c` 任务上下文分支改成恒真 ⇒ 同一 `run.sh --boots 3` **rc=1**（`012 签名 期望=0 实际=3`，另 `源树非交付态`、`check-patch-tree rc=2`）；`cp`+md5 还原（md5 回 `a231e07d…`、源树 `git status` 0 行）后同脚本 **rc=0**。
7. 回归（全部我亲跑）：`check-linux-k2` **170/170 rc=0**（`make` 走共享根 `e470dc56`）+ `check_k2.py --qemu` 自建 `55cd680a` **170/170 rc=0**；`check-linux-k5` **285/285 rc=0**；`check-linux-k6` **82/82 rc=0**；`run_suite.py --suite ltp` 两轮 **14 PASS / 20 checks / rc=0 且两轮逐例零差异**（`qemu_cmd` 均为自建 `55cd680a`）；`amb_window_probe` **14/14 rc=0**；`--soak 300 --soak-strict` **窗口 0/300、静默自旋 0、handle_softirqs die 0、rc=0**。
8. 静态门控：`check-patch-tree` rc=0（464 OK）、`check-config-pins` **101/101**、changelog / knowledge-refs / `check_issues` **rc=0**（012 `closed`+`resolved_by=m18-linux-030`、011 `open`）、`check-milestones-fresh` **首跑 rc=0 / 收尾 rc=2**（见 E1）；`check-temp-dirs` FAIL(5) 全为他任务目录（基线）。

**根因/修法核对（我读源码）**：① `trap_depth` 初始化来源 = `copy_thread()` 既有 `memset(t, 0, sizeof(*t))`（`t = &p->thread`），字段加在 `struct thread_struct` 内 ⇒ **process.c 无需改动**，新任务自 0 起（`INIT_TASK` 同为 0）；② 帧身份判别自洽：trap.S 以 `dadao_user_stack_top==0` 选静态帧、traps.c 以 `regs == &dadao_excp_save` 判 boot，同源同时刻无错配；非 boot 帧 = `align_down(SP,16)-PT_REGS_SIZE`（`PT_REGS_SIZE=2048` ⇒ 16 B 对齐，满足 `call` 的 SP 约束），`current`=SP&~(64K-1) 仍落在本任务内核栈；`rb32` 在 capture **之后**才存帧基址、出口首条 `rb2rb {rb3},{rb32}`、`DADAO_GPR_RESTORE_AT` 末尾从帧还原 rb3/rb32，cg6 rc3 的「栈帧」位不被 capture/`DADAO_SAVE_STATUS` 踩——逐宏核对自洽；③ 「首切换前仍用 hart 全局」**无竞争窗口**：`dadao_user_stack_top` 只由 `__switch_to`/`dadao_enter_user`/`start_thread` 写、从不回 0，首切换前只有 boot 一个上下文（user 缺页通道必经 user 任务 ⇒ 必已切换），故该例外不存在第二上下文可竞争（论证 + 160 启修后样本 0 误报）。

**QEMU 混用判定**：自建 `55cd680a` 与共享根 `e470dc56` 同为 QEMU 11.1.1、均支持 `-M kaiwu-vast`，差异仅 `m18-qemu-007`（cfx_jmon 移除）与 `m19-qemu-001`（Kaiwu-Tiny 几何），不触及 Vast 的 supv/async/trap 模型；两套各自跑出的 K2/K5/K6 全绿 ⇒ **混用不改变结论**。审查期间并行会话于 10:24 重装共享根（`e470dc56`→`c5a46ef7`）：我的 K2/K5 用前者、K6/amb/soak 用后者、LTP 钉自建，md5 均已记录。

**约束核验（任务书硬约束逐条）**：① 独立 worktree、我未做任何 git 提交、证据脚本即运行期证据目录内 `run.sh`、每跑次独立时间戳目录 —— 守住；② `git diff --name-only master...HEAD` = **恰好 7 文件**且与完成区声明逐项一致，无 `Makefile`/`spec/`/`.tao/contracts/`/其它组件 —— 守住；③ QEMU 全程用本 worktree 自建（md5 `55cd680a`），未写共享安装根（其 10:24 变更系他会话所为）—— 守住；④ 补丁与源树一致由 `check-patch-tree 464 OK` 证明，我的注入一律 `cp`+md5、还原后重建，长跑批严格串行 —— 守住；⑤ 无「重试直到绿」（两轮 revert 漏检按 2/2 有据记录、终轮命中即止），未见 005/006 族命中需单独计数 —— 守住。审前/审后 `git status --porcelain -uall` **均 0 行**、7 文件 md5 逐项未变；未 push（非 `origin/master` 祖先、远端无该分支）；状态 `待验收`、完成区 12 行。

**findings（不阻断）**：E1 `check-milestones-fresh` 收尾 **rc=2**，唯一 VIOLATION 是 `m18-linux-029`「有 worktree 但台账在待开始」——029 由**另一会话 08:41 派单**（主仓台账已把它移入进行中），本分支未改台账（0 文件），合并回 master 后自愈，首跑（029 worktree 出现前）rc=0；属并发环境，非本任务交付物缺陷。E2 `run.sh --inject revert` 的「复现 012」判据实为「任意 die ≥1」（我这轮 10 次里 2 次是 `code=0xe4` 也算过）⇒ 建议改签名特定匹配。E3 该判据在 62/100 启下假红率高（我两轮 rc=1）⇒ 建议默认 ≥150 启或并列结构判据（静态帧出现）。E4 `k2_trap_probe` 的 `CFX_RC_ESCAPE_IP` 断言在基线即 SystemExit（master 补丁同样缺该串，非本任务引入）；`check-temp-dirs` 红为他任务陈旧目录。

**判决：Accepted** —— 验收命令块在我自己的重跑下除 E1（并发台账、非本任务）外全绿、硬约束逐条守住、注入→FAIL→还原→回绿链条完整；终审仍归 architect。
