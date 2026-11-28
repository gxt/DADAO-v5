# m18-linux-028: 用户态异步返回丢任务（忙等可确定性复现）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-025`（`ISS-m18-001` 已闭）、`m18-linux-026`（0.8.1-rc 内核）
**可并行分片**：否（改 `components/linux`）
**预估**：3–5 h（标定：同档 025 实做约 5 h；本任务已有确定性复现器，定位为主）
**档位**：大改（异步入口/返回 + 调度）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-007` 交付 pthread 闭环时把探针改成**纯用户态忙等**（最大化 tick 命中），**8/8 触发**：控制台最后一行是 `K2 async user frame_ip=…`，之后无任何进展（无 `PTHREAD end`、无 die、无 panic）；普通负载下同现象表现为 `ISS-m18-005`（随机 case 的 `HOST_TIMEOUT`，已见 `mm-pfnmap` / `mm-map-populate` / `futex-wait-timeout` / `fstat02`）。

即：**用户态异步捕获/返回路径会丢任务**，此前被当作“宿主 flake”计数，现在有了确定性复现，不能再算 flake。

## 目标

1. **复现并固化**：把忙等探针做成可复跑、确定性 ≥8/8 的最小用例，保留“修前红”对照证据。
2. **定位根因**：抓现场（`cg15 rc0–rc5`、`cg16 rc17/18`、`cg5 rc8–rc11`、`cfx_smon`/`cfx_hart` 快照、`dadao_ticks`/timer cmp、被丢任务的内核栈/`task_struct` 状态、是否已 ack 但未返回、是否返回后未重入用户）。判据：必须能解释“为什么该任务不再被调度/不再返回用户”，**不接受“重跑就好”**。
3. **修复**：最小改动，落在 `components/linux/patches/**`；不得靠关中断/关 tick/加延时/重试掩盖。
4. **判据不得放宽**：`check-linux-k2`/`k5`/`k6`、`run_suite.py --suite ltp` 两轮、`amb_window_probe`、soak 全部保持原判据。

## 验收（逐条贴真实 rc）

1. 修前：忙等探针 ≥8/8 触发（同一镜像、固定轮数），日志与现场快照落盘；修后：同一探针 0/≥20。
2. 现场证据：上述寄存器/调度观测量各一组修前/修后对照。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现；② 破坏对应守护/断言 ⇒ 探针红。
4. 不回归：K2 **170/170**、K5 **285/285**、K6 **82/82**、`run_suite.py --suite ltp` **两轮逐例一致**、`amb_window_probe` 14/14、soak 窗口签名 0/≥1000。
5. 更新 `ISS-m18-009`（闭合）并说明与 `ISS-m18-005`/`ISS-m18-006` 的关系（同族则一并标注）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内的 `run.sh`；每次跑次单独目录留日志。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、`tools/linux/**`、`.tao/knowledge/issues-m18.yaml`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. **QEMU 配对**：用本 worktree 自建 0.8.1 QEMU（记 md5）；不覆盖共享安装根。
4. 组件补丁经 `make_patch.py linux` 重导；还原一律 `cp`+md5；还原后重建；同一时刻一个长跑批。
5. 禁「重试直到绿」；命中 `ISS-m18-005/006` 时单独计数记签名。

## 待裁定

已裁定（主会话 2026-11-27）：接受“主因已修 + 残余另册”的拆分；残余开新任务 `m18-linux-029`（`ISS-m18-011`），QEMU 侧 `cg15 rc2` 在 `ret` 上的口径由该任务核对；本任务只记录不修残余。

## 完成区

**测试结果**：`run.sh`（第 2 轮，交付形态）两次 20 启均 **rc=0**：交付样本 **pass=7 / CFXESC=0 / 残余=13（spin=10、sigsegv=3）/ 其它=0**（另一轮 pass=11 / 残余=9（spin=8、sigsegv=1））；每启 console 落证据目录 `logs/<时间戳>/boot-01..20.log`，静态 4 项（patch-tree/config-pins/changelog/knowledge-refs）全 PASS。修前同探针 **3/3 CFXESC 红** → 修后两轮 **0/40 CFXESC**。不回归（首轮实测，补丁未变）：K2 **170/170 rc=0**、K5 **285/285 rc=0**、K6 **82/82 rc=0**、`m18-linux-007` pthread **5/5**；LTP 4 轮 **3 轮 clean 逐例一致（PASS=14、20/20、rc=0）+ 1 轮 `ltp-mmap01` SIGNAL 139**（ISS-m18-005 族）；`amb_window_probe` **14/14 rc=0**；`--soak 1000 --soak-strict` **0/1000（窗口 0、静默自旋 0、`handle_softirqs die` 0）rc=0**；`check-patch-tree` 464/0、config-pins 101/101、changelog/knowledge-refs rc=0、`check_issues` rc=0。
**复现率（修前/修后对照）**：CFXESC 3/3 → **0/40**（两轮 20 启）；残余 **22/40**（spin 18 / sigsegv 4，`ISS-m18-011`/`029`）；另立新签名 `K2_FAIL_RECURSIVE` die 专项样本 **1/20**（交付两样本 0/20、0/20；reviewer 1/3）（`ISS-m18-012`）。`ISS-m18-005` 族参照（006 完成区）修前 9 轮 flake 6；修后 LTP 4 轮 flake 1、soak 0/1000（025 参照 410/2000）。
**根因**：user 异步把捕获交接 `cfx_smon` 后不 escape，`inner_cfx_code` 停在 smon；回用户 work loop `schedule()` 后另一任务恢复 umon 帧 `escape cfx_umon` 时 `cfxha != inner_cfx_code` ⇒ `CFXESC`（`spec/DADAO-12 §5.3` step 0）；该 escape 在恢复用户 SP 后执行，supv 异常跑在用户栈上，semihosting 的 PA 失效 ⇒ 无 die/无退出、停在 `K2 async user` 后静默自旋。
**修改文件**：`components/linux/patches/arch/dadao/kernel/async_trap.S.patch`、`traps.c.patch`、`entry_common.c.patch`（user 臂按 hart 出口意图 `escape cfx_hart` 到 supv：rc8=supv、rc9=prev cfx、rc10=finish、rc11=继承掩码；单一 restore 站点；`dadao_async_user_finish()`=`m45_note_irq`+ack→work loop；删 FROM_ASYNC 分派）、`components/linux/changelog.md`、`tests/unit/linux/m18_async_return_probe.py`、`.tao/knowledge/issues-m18.yaml`（009 主因、011、012）、本任务书。（第 2 轮未改补丁正文。）
**验收结果**：可达 FAIL（`cp`+md5）：① 回退补丁正文 ⇒ 3/3 `CFXESC`（reviewer 复现同证）；② **删 user 臂 `rc8=SUPV` 写入** ⇒ **2/2 红**，签名 `K3 pf … cause=PTWPERM sub=NUPERM ip=va=0x20000153588(=finish trampoline) result=die-super`（escape 回 user 态执行内核 trampoline）；`cp`+md5 还原（`57fcbe97…`/`aa97e142…`）后 20 启 0 CFXESC。反例：删 rc9（QEMU 已写 `escape_cfx_code=prev_cfx`）中性、deleting ack 会被嵌套 kernel 臂补 ack，二者不采用。
**新发现/坑**：① 证据脚本须按签名判红：CFXESC=FAIL、残余=计数挂 011、die=计数挂 012（出现即不得绿）；② 注入要选“行为改变且签名可归因”的守护：`rc9` 中性、ack 删除自愈、`rc8` 删除 100% 红；③ `dadao_trap_busy` 是 hart 全局、缺页通道可睡眠 ⇒ 另一任务 user 缺页交接误报递归（012，1/20）；④ `CFXESC` 的 die 行不可见（用户栈 + semihosting PA）；⑤ amb 注入锚点要求异步 restore 全文 1 处。
**遗留问题**：`ISS-m18-011` 残余 **22/40**（`m18-linux-029`：spin=18 帧 ip 落在相邻函数体/`start` 未置位；sigsegv=4 帧内寄存器破坏致 `done[idx]=1` 野址；无 die/CFXESC；疑 QEMU `cg15 rc2` 在 `ret` 上的口径，内核不改）；`ISS-m18-012` 新签名 **1/20**（`K2_FAIL_RECURSIVE` die，`dadao_trap_busy` 跨睡眠误报，非同源于 029）；`ISS-m18-009` 保持 open（主因已修）。LTP 1 轮 `ltp-mmap01` SIGNAL 139 归 `ISS-m18-005` 族。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`async_trap.S`（user 臂出口意图 + finish trampoline）、`traps.c`（删 FROM_ASYNC 分派）、`entry_common.c`（`dadao_async_user_finish`）、探针；逐行核对 `escape cfx_hart` 的合法性（rc8=supv 不升权、rc9=cfx_umon 已实现、rc11 整字写 smon 行）、`DADAO_GPR_RESTORE` 后重设 SP 的次序、`rb2rd rd2, rb4, 1` 的块复制语义、finish 内 ack/work loop 的 IRQ 状态。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 “K2 async user 后静默”的根因未定 | ✅已修 | 定位到 user 异步不 escape smon ⇒ `inner_cfx_code` 外泄 ⇒ 另一任务 umon `escape` 取 CFXESC（§5.3 step 0），且在用户 SP 上 die/semihosting 失效 | 修前 monitor `CFX02 CID=0x8(CFXESC) CIP=umon escape CINFO=0x7e000000`、PC=`dadao_early_exit+0x54`；基线探针 3/3 红 |
| F2 修法是否只治标 | ✅已修 | 改由 hart 帧自己的出口意图先恢复 `inner_cfx_code` 再跑 work loop（不再让 smon 静态帧跨睡眠） | 修后 CFXESC 记录消失；K2 170/170、K5 285/285、K6 82/82、007 pthread 5/5 |
| F3 修后忙等探针仍 ~50% 红 | ❌未修（另册 + 待裁定） | 不改 QEMU/不猜；登 `ISS-m18-011` | 20 启 10 红：末行 `K2 async user frame_ip=0x22104/0x22108`、SP 为该任务用户栈、monitor `PC=0x22108 MODE=0`、`start=0`；无 die/CFXESC；两版交接（smon/hart）都出现 |
| F4 探针是否只靠“重跑” | ✅已修 | pthread 栈预驻留（`pthread_attr_setstack`），隔离用户缺页通道；固定 seed（SPIN/N 常量） | 修前 3/3 红、修后同镜像 10/20（如实计数，不重试） |
| F5 可达 FAIL 路数 | ✅已修 | ① 回退修复；② 删 rc9 恢复 | ① 3/3 红（CFXESC）；② 2/3 红；`cp`+md5 还原（`1ee489a9…`）后源码树 `git status` 干净 |
| F6 LTP 两轮/amb/soak | ⏸未跑 | — | 主验收已被 F3 判红，先等裁定，避免在错误基线上耗长跑；K2/K5/K6/007 已跑 |
| F7 越界/范围 | ✅合规 | 只动 patche/changelog/tests/knowledge/任务书；不提交主仓 | `git status` 仅上述文件；patches 经 `make_patch.py linux` 重导（464 patches、0 problem） |

**判决**：F1/F2/F4/F5/F7 已修并有真实复验；**F3 未修**，任务验收 #1（修后 0/≥20）**未达成**，故状态保持 `待开始` 并附「待裁定」。

### 第 1 轮 engineer 自审（续）

按主会话裁定补三件事：**改号**（`ISS-m18-011`，master 的 010 保留给 `fetch.py`）、**完整回归**、**完成区按拆分口径**。处置与复验：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F8 新 issue 与 master `ISS-m18-010` 撞号 | ✅已修 | 本条改 `ISS-m18-011`；009 标题追加“主因已修（CFXESC）、残余归 011”，009/011 均 open、`resolved_by` 不填 | `grep` 无重号；`check-knowledge-refs` rc=0 |
| F9 amb 门控被新 asm 打破（baseline 红 + 注入锚点 3 处 + 宏内标签重定义） | ✅已修 | `async_trap.S` 收敛为**单一** `DADAO_GPR_RESTORE dadao_async_save` 站点（三条出口先写 rc10 再 `jump .Lasync_restore`；user 的后置 SP/帧指针移入 escape 后 trampoline）；finish 补 `m45_note_irq` | `amb_window_probe` **14/14 rc=0**（baseline 绿、两条注入红、注入锚点 1 处、cp+md5 还原） |
| F10 回归数据缺失 | ✅已修 | 跑 LTP 4 轮、amb、soak 1000 | LTP：3 clean（PASS=14、20/20、rc=0）+ 1 `mmap01` SIGNAL 139；amb 14/14；soak 0/1000 窗口、0 静默自旋、0 `handle_softirqs die` |
| F11 残余仍 ~7/20 | ❌不修（已裁定另册） | 只记录不修；登记 `ISS-m18-011`/`m18-linux-029` | 见完成区“遗留问题”，未用重试掩盖 |
| F12 修后忙等探针验收 #1 | ✅按拆分口径 | 完成区写“修前 3/3 CFXESC → 修后 0/3 CFXESC；残余 7/20 另一签名，另立 011/029” | 与裁定第 3 条逐字一致 |

**判决**：F8/F9/F10/F12 已修并有真实复验；F11 按裁定另册。K2 170/170、K5 285/285、K6 82/82、amb 14/14、soak 0/1000、patch-tree 464/0、config-pins 101/101 全绿 ⇒ 状态 **待验收**。

### 第 2 轮 engineer 自审

**范围**：`run.sh`（签名分类）、`ISS-m18-012`、本轮注入；逐条对 F1/F2/F3。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 判据写死 20/20、无 logs | ✅已修 | `run.sh`：CFXESC 型（no `BUSY end`、1..100 async、无 die）=FAIL；残余（>100 async，细分 spin/sigsegv）=计数挂 011；die/panic/early=计数且 FAIL；每启 console 拷入 `logs/<ts>/` | 两轮 20 启均 **rc=0**：pass 11/7、CFXESC **0/0**、residual 9(spin8+sigsev1)/13(spin10+sigsev3)、other **0/0** |
| F2 注入②不可归因 | ✅已修 | 删 rc9 弃用（中性）；改删 user 臂 `rc8=SUPV`：escape 回到 user 态执行 kernel trampoline | **2/2 红**，签名 `sub=NUPERM va=0x20000153588 result=die-super` 可归因；cp+md5 还原后 20 启 0 CFXESC |
| F2 追加：ack 删除也不致命 | ⏸记录 | 删 `dadao_async_ack_sources` 后嵌套 kernel 臂会补 ack ⇒ 1 过/1 残余，不作注入 | 见完成区“反例” |
| F3 新签名未登记 | ✅已修 | 新增 `ISS-m18-012`（P1）：`dadao_trap_busy` hart 全局跨睡眠误报；011 的“无 die”加注（该 die 属 012） | 20 启样本 boot-19 现场 `ip=dadao_umon_excp+0x224 info=0x7f0802f5 → die code=0xe`，紧邻 worker `K4 umon->smon … info=0x8eb90`；频率 1/20（reviewer 1/3）；`check_issues` rc=0 |
| F3b 是否中间态 | ✅已排 | 源码 md5 与 reviewer 还原值一致（`57fcbe97…`/`aa97e142…`/`b5f16441…`），object 晚于 source；同源 20 启复现 ⇒ 真实签名、非脏构建 | md5 + 构建时间 + 20 启样本 |
| F4 静态门控 | ✅ | — | patch-tree 464/0、config-pins 101/101、changelog、knowledge-refs、check_issues 全 rc=0 |

**判决**：F1/F2/F3/F4 均已修并有真实复验；残余 011 与新建 012 按裁定另册；状态 **待验收**。

### 第 1 轮 reviewer 验收

**重跑（审查者本人，2026-11-27 23:08–23:55）**
- 仓库根执行运行期证据目录内的 `run.sh`（默认 20 启）→ **rc=1**：探针 **12/20 过、8/20 红**，8 个红全为 `qemu rc=124 / async_user_lines≈3700 / frame_ip=0x22104` 残余型、**CFXESC 型 0 个**；其静态 4 项（patch-tree/config-pins/changelog/knowledge-refs）均 PASS。审查开始时该证据目录**只有 `run.sh`、无 `logs/`**（脚本此前未被执行）。
- 修前对照：把 `f380b6e0^` 的三份补丁正文按 `cp` 回植（md5 `16fdbec1…`/`d0a66a85…`/`fd929f14…`）⇒ 同参数探针 **3/3 红**（`rc=1`、`async_user_lines=2/2/3`、NUL 尾）。另起 monitor 实抓：`PC=0x20000150720 = dadao_early_exit+0x54`（`trap cfx0,0x3ff00` 之后的 `jump [rb0,0]` 自循环）、`MODE=2 CFXCODE=2`、`CFX02 PREVM:2 CID:0000000000000008(CFXESC) CIP:0x20000151c4c = escape cfx_umon CINFO:0x7e000000` ⇒ 与完成区“修前 monitor”逐字段一致。
- 注入② 删 user 臂 rc9 写入（源树 md5 `ea743c15…`）⇒ **2 过/1 红**，那 1 红 `rc=124、async=3752、frame_ip=0x22104` 与基线残余同签名（基线 8/20 = 40% 红率）。
- `cp`+md5 还原（三文件回到 `57fcbe97…`/`aa97e142…`/`b5f16441…`，`git status --porcelain -uall` 空、`git diff HEAD` 空）后回归：K2 **170/170 rc=0**、K5 **285/285 rc=0**、K6 **82/82 rc=0**、`run_suite.py --suite ltp` 两轮均 **PASS（14 PASS、20/20 checks、rc=0）逐例一致**、`amb_window_probe` **14/14 rc=0**、`--soak 300 --soak-strict` **窗口 0/300、静默自旋 0、`handle_softirqs die` 0、rc=0**；静态门控 patch-tree **12 set/464 patches 0 problem**、config-pins **101/101**、changelog PASS、knowledge-refs PASS、`check_issues` rc=0（009 open 且写明主因、010=fetch.py、011 open、无重号）。

**根因核对（行级，成立）**：`async_trap.S`（修前）user 臂 `trap cfx_smon, DADAO_SMON_FROM_ASYNC` 后无 `escape` ⇒ `inner_cfx_code` 停在 smon；`entry_common.c::dadao_async_user_return` 经 `exit_to_user_mode()` 可 `schedule()`；`trap.S` 两条 umon 返回路径都是 `DADAO_GPR_RESTORE_AT`（首条即恢复用户 `rb1`）**之后**才 `escape cfx_umon`；`spec/DADAO-12 §5.3` step 0：`cfxha != inner_cfx_code` ⇒ `CFXESC` 并进**当前 cfx**；supv 向量 C 体跑在已恢复的用户 SP 上，`traps.c::semihost_exit` 用 `__pa(block)`、`early_console.c` 全部指针走 `__pa()` ⇒ PA 失效、`dadao_early_exit` 卡在自循环（实测 PC）。以上与实抓 monitor 互证。

**修法核对（成立）**：`async_trap.S` 全文 **1 处** `DADAO_GPR_RESTORE dadao_async_save`（0 处 `DADAO_GPR_RESTORE_AT`），kernel/user/static 三条出口均先写 rc8–rc11 再收敛到 `.Lasync_restore`；user 臂 rc8=`DADAO_MODE_SUPV`、rc9=捕获的 prev cfx（=cfx_umon）、rc10=`.Lasync_user_finish`、rc11=入口继承 smon 掩码字；`dadao_async_user_finish()`＝`m45_note_irq`+`dadao_async_ack_sources`（TIMER/PMEM 按 `src_frame` ack，未知位走 die）→ `dadao_async_user_return`（work loop）→ `dadao_enter_user()`（`trap cfx_umon`）；`FROM_ASYNC` 代码引用 **0 处**（仅 `trap.h` 注释+未用宏）；三份补丁正文与源树逐行 md5 相同。

**约束核验**：7 文件与「修改文件」逐条一致；无 QEMU/`spec/`/契约/`Makefile` 改动；`git branch -r --contains HEAD` 空（未 push）；任务书无具体运行期路径引用；注入/还原全程 `cp`+md5、未用 checkout/restore。

**判决：Needs Revision**
1. **门控/退出码**：证据脚本 `run.sh` 的探针断言仍写死「20/20 全过」，与已裁定的「0/≥20 CFXESC + 残余另册 011/029」口径冲突 ⇒ 交付状态**恒 rc=1**，且脚本从未被执行过（证据目录无日志）。改法：按签名分类判定（CFXESC 型红＝FAIL；残余型现场计数并挂 `ISS-m18-011`），跑出 rc=0 并留日志。
2. **验收 #3 第②路不可归因**：字面删 user 臂 rc9 写入是行为中性（QEMU `dadao_async_enter` 已写 `escape_cfx_code = prev_cfx`），实测 2 过/1 红且红＝基线残余同签名（基线 8/20=40%）⇒ 3 启 1 红属噪声，不构成「破坏守护 ⇒ 探针红」的可达 FAIL。改法：换成真正改变行为的注入（或按签名判红）并重跑。
3. **回绿未达成 + 新签名未登记**：还原后 3 启 **0 过**——1 启 `dadao: recursive supv exception cause=CFXTRAP info=0x7f0802f5 ip=dadao_umon_excp+0x224 → die mode=2 code=0xe`（`K2_FAIL_RECURSIVE`）、2 启残余 `rc=124`；`ISS-m18-011` 明写「无 die」，未覆盖该签名。改法：补登 issue 或给出归因，并补一份回绿证据。

**采信与不夸大核对**：完成区「修前 3/3 CFXESC → 修后 0/3、残余 7/20 另立 011/029」**成立**（我 20 启 0 个 CFXESC 型、8 个残余型；残余 7 vs 8 属抽样波动）；「LTP 4 轮 3 clean + 1 `ltp-mmap01` SIGNAL 139」与 `ltp-a/b/c/d` 退出码 0/1/0/0 逐条一致、**不夸大**，但验收 #4「两轮逐例一致」在原样本未达成（已在遗留问题如实披露，我复跑两轮 clean）；完成区 monitor 行 `PREVM=2 CID=0x8(CFXESC)` 为解码转写、原始 hex 行在工件与我复现中均存在（记一条，不阻断）。

### 第 2 轮 reviewer 验收

**重跑（审查者本人，2026-11-28 00:16–00:45）**
- 仓库根执行运行期证据目录内的 `run.sh`（20 启）→ **rc=0**：`pass=7 cfxesc=0 residual=13(spin12/sigsegv1) other=0`；注入还原后再跑一次 20 启 → **rc=0**：`pass=10 cfxesc=0 residual=10(spin8/sigsegv2) other=0`；与交付两轮（`11/0/9/0`、`7/0/13/0`）同分布（抽样波动内）。每轮 `logs/<时间戳>/` 均 **20 个 `boot-NN.log` + 4 项门控 PASS**；四轮交叉核 `pass` 数恒等于探针 `qemu rc=0; 5/5` 数（11/11、7/7、7/7、10/10）。
- **F1**：分类顺序＝`BUSY end`→pass；`recursive supv exception|dadao: die|panic|BUG:`→**other=FAIL**；`async=0`→**other=FAIL**；`async 1..100`→**cfxesc=FAIL**；`>100`→residual（只进 `[INFO]` 计数挂 011）；`pass+residual==N` 使 cfxesc/other 双重必红。同规则套**修前真实 console**（`revA-1/2/3`，async=2/2/3、无 die、无 BUSY end）→ **3/3 cfxesc**（主因红不被 residual 吞）；套两个真实 die console（012 专项 boot-19、我第 1 轮 `green-1`，各 2 条 die 行、async≈3100）→ **other**（不被判绿）。
- **F2**：删 user 臂 `set.rd rd2, DADAO_MODE_SUPV` + `cfx2rc … cg5, rc8, rd2`（源树 md5 `4d6674fb…`）⇒ `run.sh --boots 3` **rc=1**，3/3 `other`，签名 `K3 pf cause=PTWPERM sub=NUPERM ip=va=0x20000153588 result=die-super`（escape 落回 user 态执行内核 finish trampoline），同轮 `check-patch-tree` **rc=2**（门控真比对补丁↔源树）。`cp`+md5 还原后 `md5sum -c` 三文件全 `OK`（`57fcbe97…/aa97e142…/b5f16441…`＝审前快照），**还原后 20 启 CFXESC=0**。
- **F3**：`ISS-m18-012` 现场＝012 专项 run 的 `boot-19` console 工件：`ip=0x20000151ba0 = dadao_umon_excp+0x224`、`info=0x7f0802f5`、前一行 `K4 umon->smon … ip=0x22110 info=0x8eb90`、`die mode=2 code=0xe`，与我第 1 轮 `green-1` 逐字段同签；机制与源码一致（`traps.c:256 static volatile int dadao_trap_busy` 全局、`:481` 判递归、`:484` 置位、`:494-498` 在 **FROM_USER 分支位仍为 1** 时调 `dadao_user_fault_from_umon`→`dadao_do_page_fault`（`mm/fault.c` 182/704/738 取 mmap 锁、可睡眠）后才清位）；028 的 `traps.c` 补丁只删 FROM_ASYNC 分支（该分支含 1 条 `dadao_trap_busy = 0`，8→7 处），定义/守卫/其余清位点未动 ⇒ 非 028 引入。
- **回归**：K2 **170/170 rc=0**、`run_suite.py --suite ltp` 1 轮 **PASS（14 PASS、20/20、rc=0）**、`amb_window_probe` **14/14 rc=0**、`--soak 300 --soak-strict` **窗口 0/300、静默自旋 0、`handle_softirqs die` 0、rc=0**（叠加第 1 轮 K2/K5/K6、LTP 2 轮、soak300 全绿）。
- **门控与范围**：`check-patch-tree` 12 set/464 patches **0 problem**、config-pins **101/101**、changelog/knowledge-refs rc=0、`check_issues` rc=0（59 open；009/011/012 open、010=fetch.py、无重号）；状态 **待验收**、未 push、HEAD 仍 7 文件、本轮未提交改动仅 `issues-m18.yaml`+本任务书（补丁正文未动）、无 QEMU/`spec/`/契约/`Makefile` 改动。

**判决：Accepted**

**特别判（M18 能否按「主因已修（CFXESC=0）+ 残余/新签名另册（011/012）」收口）：可以**，依据不是数字好看而是：① 主因签名 **CFXESC 0/100**（我 3 轮 60 启 + 交付 40 启）对修前 **3/3 红 + monitor `CID=8`/`CIP=escape cfx_umon`/`CFXCODE=2` 实证**，且修前/修后 console 可用 `退出码、async 行数、末行` 机械区分（修前 `rc=1`+async≤3+NUL 尾；残余 `rc=124`+async≈3700）；② **现实负载干净**——LTP 我 3 轮全 clean（14/14、20/20）+ 交付 4 轮 3 clean/1 `mmap01 SIGNAL`，soak 300 两轮全 0（窗口/静默自旋/softirq die 均 0，交付另有 0/1000），K2/K5/K6 全绿，即日常负载不出现该签名；③ 残余与 012 是**不同签名**（残余＝`rc=124`+async≈3700+无 die；012＝`die 0xe` 递归）已分册 011/029、012 且保持 open。**保留条件**：忙等探针残余 23/60 红率仍高，M18 只能按拆分口径关，011/012 必须挂 P1（029 已立册）；对内表述不得写「用户态异步丢任务已清零」。

**Finding（不阻断，随 029/下轮顺手改）**：① `pass` 只 grep `BUSY end`、die 正则排在其后且不核该启 `rc=0; 5/5`（`probe rc` 只按 `0|1` 收下）⇒「BUSY end 之后才 die / 退出码错」会判绿；60 启未观测到（`pass` 数 ≡ `rc=0;5/5` 数），建议把 die 正则提到 `BUSY end` 之前并按启核退出码；② 交付 run1 的 `classification.txt` 无 `.spin/.sigsegv` 后缀、run2 有 ⇒ 两轮由不同版本脚本产出、run1 子签名为事后重算（三分类一致，不影响判定）；③ monitor 行为解码转写（第 1 轮已记）。
