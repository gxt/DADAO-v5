# GEM5-029t: gem5 SE syscall 语义对齐（QEMU 已实现项）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-026t`（线程/TLS；同改 gem5 补丁，须先合并）
**状态**：已验证

## 背景与用户口径（2026-11-07）

> 「除非是 qemu-user 自己实现了某个系统调用，而 gem5 内部没有这个实现；否则都应该是一致的。而 qemu-user 自己实现的系统调用，原理上也可以在 gem5 中实现一份，如果有这种情况出现，一定要和我说一声。」

已核对 QEMU 源码确有 handler（非透传）而 gem5 目前不等价的项：

- `nanosleep`：QEMU 真正睡眠并回写 `rem`；gem5 立即成功
- `wait4`：QEMU/Linux 在目标非子进程（但存在其它子进程）时返回 `ECHILD`；gem5 继续阻塞
- `execve`：QEMU 对存在但不可读的 ELF 返回 `EACCES`；gem5 经 loader 直接中止
- `pipe2`/`socket` 读：QEMU 先校验 guest 缓冲；gem5 在 `EFAULT` 前已消费数据
- `kill`/`tgkill`：QEMU 按进程组/全部进程；gem5 把 `pid∈{0,-1,-pid}` 当 self
- `sigaltstack`：QEMU/Linux 支持 `SS_AUTODISARM`；gem5 返回 `EINVAL`
- `faccessat`：QEMU/Linux 的 `AT_EMPTY_PATH` 返回 0；gem5 返回 `EINVAL`

## 目标

逐项对齐到 QEMU/Linux 语义（单进程/单线程范围内可实现的）：

1. `nanosleep`：按 guest 时钟推进（事件唤醒，不阻塞宿主），到期返回 0；被信号打断返回 `EINTR` 并回写 `rem`；`rem==NULL` 合法。
2. `wait4`：目标非子进程且有其它子进程 ⇒ `ECHILD`；pid 回收/复用按 Linux 基本规则（至少不无限增长）。
3. `execve`：不可读 ELF ⇒ `EACCES`；其它加载错误按 errno 返回，不 panic。
4. `pipe2`/`socket` 读：先验证 guest 缓冲可写，再消费；`EFAULT` 时数据不丢。
5. `kill`/`tgkill`：`pid>0` 查进程表；`pid==0` 发给同进程组；`pid==-1` 发给所有可发进程（含 self）；`tgkill` 校验 tgid。
6. `sigaltstack`：接受 `SS_AUTODISARM` 并按 Linux 语义处理；非法 flags 才 `EINVAL`。
7. `faccessat`：支持 `AT_EMPTY_PATH`（fd 有效时返回 0/`EACCES`），其余 flags 按 Linux。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,inst.cc}`、`components/gem5/{README.md,changelog.md}`、`components/qemu/patches/linux-user/{signal.c,dadao/signal.c}`（`SS_AUTODISARM`；**经用户 2026-11-07 裁定由「不在范围」扩展**）、`components/qemu/{series,changelog.md}`、本任务书、`milestones.md`。

**不在范围**：`mprotect` 真权限与 `RLIMIT_AS/STACK` 强制（`GEM5-030t`）、线程/futex（`GEM5-026t`）、动态链接（027/028）、测试用例与期望。

## 验收标准

1. 逐项双引擎探针（同 ELF 在 QEMU 与 gem5 SE 上）：7 项行为一致；每项至少含「正常路径 + 错误路径」两条断言。
2. 基线复跑：`gem5_only_fail` 不新增；`qemu_only_fail` 仍 0；相关 blocked 不退化。
3. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
4. 反例：任一项改回旧行为 ⇒ 对应探针 FAIL；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- `nanosleep` 在 SE 中用事件队列推进 guest 时钟，不阻塞宿主；与「立即返回」相比这是语义对齐，不是性能优化。
- 每项改动前先写双引擎探针，确认 QEMU 侧行为作为 oracle（不反推 gem5）。

## 用户裁定（2026-11-07，engineer 问答原文）

- **sigaltstack `SS_AUTODISARM`**：实测锁定版 QEMU v11.1.1 `target_restore_altstack()` 只接受 0/`SS_ONSTACK`/`SS_DISABLE`、对 `SS_AUTODISARM` 返回 `EINVAL`（探针实跑 errno=22），与任务书第 6 项冲突。用户裁定原话：**「先按 Linux 实现，同时给 QEMU 补 patch」** ⇒ gem5 按 Linux `SS_FLAG_BITS` 实现，`components/qemu` 补 `SS_AUTODISARM` 支持（范围由本裁定扩展，`components/qemu/{patches,series,changelog.md}` 列入完成区「修改文件」）。
- **execve 成功路径 oracle**：QEMU user-mode 把 guest `execve` 转发宿主，宿主无法执行 DADAO ELF（未注册 binfmt_misc）⇒ 同一 ELF 在 QEMU 返回 `ENOEXEC`。用户裁定原话：**「错误路径双引擎+成功路径 gem5-only（推荐）」** ⇒ 错误码三例（`ENOENT`/`EACCES`/`ENOEXEC`）双引擎逐行比对；成功路径（子进程 exec 有效 ELF 后 exit 7）只作 `local:` 断言（QEMU 侧记 INFO）。


## 完成区

**测试结果**：7 项各 1 个双引擎探针（同一 ELF，QEMU `-R 4G` 为 oracle）全绿：`p1_nanosleep` 16 / `p2_wait4` 16 / `p3_execve` 5 / `p4_read_eintr` 11 / `p5_kill` 19 / `p6_sigaltstack` 25 / `p7_faccessat` 14 条共享断言逐行一致、无 FAIL、两侧 `SUMMARY fails=0`；`local:` 断言（execve 成功路径、pid 回收）gem5 侧全 PASS。`nanosleep` 覆盖正常/零请求/`EINVAL`/`rem==NULL`/信号打断（elapsed+rem≈请求）/**非法 `rem` ⇒ `EFAULT`**/屏蔽 pending；反例：nanosleep 改回「立即成功」⇒ p1 的 elapsed/EINTR 两断言 FAIL；sigaltstack 改回「`SS_AUTODISARM` ⇒ `EINVAL`」⇒ p6 FAIL；`cp`+`md5sum -c` 还原重建后回绿（48 PASS / 0 FAIL）。
**修改文件**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,process.hh}.patch` + `series`/`README.md`/`changelog.md`；`components/qemu/patches/linux-user/{signal.c,dadao/signal.c}.patch` + `series`/`changelog.md`（用户裁定扩展范围）；本任务书 + `milestones.md`；证据 `run.sh`/`inject_src.py`/`probes/*`。
**验收结果**：`run.sh` 93 PASS / 0 FAIL（rc=0），`run.sh --inject` 48 PASS / 0 FAIL（rc=0）；`build-gem5`、`check-inst`、`check-arch`、`check-gem5-decode`、`check-patch-tree`、`check-source-state`、L1、L2 全 rc=0（终轮日志逐项 PASS）。static 基线复跑与 026t 基线 JSON 逐例比较：**无任何 case 回退**（enger 轮 434/148；reviewer 轮 436/146，差异 2 例为 `whetstone`/`Quicksort` 的 time-budget 抖动 blocked→pass；`gem5_only_fail` 6、`qemu_only_fail` 0、集合不变）——7 项均不在语料判定路径上，一致由专项探针证明。二进制 md5：`2f51f6a4…`（基线轮）、`dfe9146f…`（终轮探针+门控+反例，同一 clean 源重建；SCons 重链接使 build id 变化）。
**新发现/坑**：① QEMU dadao 的 `sigaltstack` 只存 size/sp、`target_restore_altstack` 无 `SS_AUTODISARM` 分支 ⇒ 补丁须同时改 `on_sig_stack`/`target_save_altstack`/交付 reset 三处，缺一处双引擎即分叉；② 宿主 pid 复用使 QEMU 侧 `kill(reaped,0)` 抖动 ⇒ 该类断言只能 `local:`；③ musl 的 `sigaltstack()` 包装器抢先返回 `EINVAL`(`SS_ONSTACK`)/`ENOMEM`(短栈)，验证内核规则须走裸 `SYS_sigaltstack`；④ `ProcessParams.pgid` 的 C++ 默认是 0（Python 默认 100）⇒ fork/execve 必须显式继承 `process->pgid()`，否则 `kill(0)`/`wait4(0)` 组口径全错；⑤ `wait4` 的 pid 释放点必须在「回收」而非「退出」（僵尸仍占 pid）；⑥ `.work/log/` 下自建文件须用 `check-…log` 或 `<任务号>-<用途>.(log|json|txt)`，否则 L1 `check-run-artifacts` 红。
**遗留问题**：无。`regression/execle-env`/`popen`/`spawn`/`vfork` 仍为 026t 已登记的环境缺口（无 guest DADAO `/bin/sh`），不在本任务范围。
**并发事故与处置（含重试）**：另一会话（GEM5-027t）曾在**共享**源树留下未提交改动并重链接二进制，首轮基线因此作废（未采信）；未触碰其改动、未用 git 还原，串行化后按 `build-gem5` → `run.sh --baseline` → `run.sh --inject` 重跑。过程中还处理了 4 个自身/环境问题并重跑：`grep -c` 期望值写错、`p2` 打印 pid 破坏跨引擎比对、`.work/log` 自建文件名不合 L1 规则、`nanosleep` 非法 `rem` 应 `EFAULT`（代码修正后重建并重导补丁）。一次会话因 `Internal Server Error` 中断（第 1 次异常，已重试）。本完成区结论全部来自最终一轮（过程见 `.work/log/GEM5-029t-concurrency.log`）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-07）

逐行审查 `se_workload.cc`/`process.hh` 改动（含未测输入与边界），结论如下。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| `nanosleep` 被信号打断且 `rem` 非法时返回 `EINTR`（Linux 先写 rem、失败即 `EFAULT`） | ✅已修 | `interruptNanosleep` 与「入口已 pending」两条路径按写结果选 `-EINTR`/`-EFAULT`；`p1` 增 `nanosleep-interrupted-bad-rem` 断言 | 双引擎 `p1` 16 条共享断言一致（`EFAULT`），`SUMMARY fails=0` |
| QEMU 侧 `SS_AUTODISARM` 需三处联动（`on_sig_stack`/`target_save_altstack`/交付 reset），只补一处会分叉 | ✅已修 | 三处齐改 + `dadao/signal.c` 的 `setup_ucontext` | `p6` 25 条共享断言一致；补丁前 QEMU 6 条 `EINVAL` 全部转绿 |
| `tkill` 仅在本进程内查 tid（Linux 允许任意 tid，按权限） | ⏸延后 | — | 语料与探针均不触达；本任务契约只要求 `kill`/`tgkill` 选目标，`tkill` 保持 024t 口径 |
| `kill(-1)` 把 self 计入（Linux 排除调用者线程组） | ❌不修 | — | 任务书第 5 项原文「含 self」；且发真信号会波及宿主进程组，无法构造安全双引擎探针 |
| `guestRangeWritable` 预先把整个请求范围的 VMA 页分配（即使读返回很少） | ❌不修 | — | 与内核 `copy_to_user` 同序；既有 `std::vector<uint8_t> data(count)` 已是 O(count)，未新增量级 |
| pid 释放在「回收」而非「退出」，与 execve 的 erase/insert 成对 | ✅复核 | — | `execve` 先 erase 自身 pid 再重建；僵尸已 `unregisterLiveProcess`，回收后释放不产生 pid 冲突；`p2` 全绿 |

判决：无未处置的必要 finding；反例自检（nanosleep/sigaltstack 回旧行为 ⇒ 对应探针 FAIL，`cp`+md5 还原后回绿）通过，状态可置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-07）

**重跑记录（reviewer 亲跑，真实 rc）**

- `./run.sh` → **rc=0，93 PASS / 0 FAIL**；7 个 `*-engines-agree` 全 PASS；`gate-build-gem5`/`check-inst`/`check-arch`/`check-patch-tree`/`check-source-state`/`L1`/`L2` 逐项 `expected=0 actual=0`；另跑 `check-gem5-decode` rc=0、`build-qemu` rc=0、`install-host` rc=0（安装根与构建树 `qemu-dadao` md5 同为 `a8eb3732…`）。
- **独立双引擎探针**（reviewer 自写 `review/probes/r_aligned.c`，52 条 `CHK`）：QEMU 与 gem5 **集合逐字相同**、两侧 `SUMMARY fails=0`。覆盖：nanosleep 推进 25 ms / `EINVAL` / 被信号打断 `EINTR`+`rem`>0+handler、wait4 非子进程与非进程组 `ECHILD`×3 + 回收状态、execve `ENOENT`/`EACCES`/`ENOEXEC`（不可读文件由探针以 mode 000 建、不经 chmod）、pipe+**readv**+socket 的 `EFAULT` 后数据完整、`kill(0/-1/<-1/未知/坏信号)`+子进程投递+`tgkill`/`tkill` 校验、`sigaltstack` AUTODISARM/未知位/裸 `SYS_sigaltstack` ONSTACK、`faccessat2` 五例+旧号空路径。
- **独立基线**（全量 static 三套件，`rc=0`）：`436 pass / 146 blocked / gem5_only_fail 6 / qemu_only_fail 0`；`gem5_only_fail` **集合**与 engineer 轮及 026t 完全相同；与 engineer 轮仅 2 例差异（llvm-ts `whetstone`、`Quicksort`：time budget 141→139，由 blocked 转 pass），3 例 `ipc_*` 仅 fatal `pc=` 变、判定不变，**无任何 case 回退**。
- **独立反例**（`review/inject.sh`，不复用 engineer 的 nanosleep/sigaltstack）：① 拆除 `read` 两处「先验证后消费」⇒ `pipe-read-after` 4→0、`pipe-data-intact` 1→0、`sock-read-after` 4→-1、`sock-data-intact` 1→0（探针 rc=1）；② `wait4` 的 `if (!anyMatch)` 改回 `process->children.empty()` ⇒ 探针在本应 `ECHILD` 处挂住（90 s `timeout` rc=124）。两次均 `cp` + `md5sum -c` 还原、`git diff --quiet` 通过、重建后探针 rc=0 回绿，`FAIL` 行数 0。
- **脚本审查**：`run.sh` 的每类断言（rc/共享计数/逐行 diff/local 计数/`SUMMARY` 计数/基线四项/门控 rc）均有可达 FAIL 路径，历史失败也证明其会红；门控 rc 不经管道。注入锚点 fail-closed（锚点缺失即报错）。
- **快照对账**：外层 `git status --porcelain -uall` md5 与审前一致 `8446fc71…`（reviewer 误建的一处临时文件已删）；`.work/source/gem5` = `e930bf2`、`.work/source/qemu` = `9765e57`，均 clean + base+1；改动集与完成区「修改文件」声明相符。

**约束核验**：验收1 ✅（7 项双引擎一致、每项 ≥2 断言，含正常+错误路径）；验收2 ✅（`gem5_only_fail` 不新增、`qemu_only_fail=0`、blocked 未升）；验收3 ✅（8 个门控 rc=0）；验收4 ✅（4 项反例可达 FAIL + `cp`/md5 还原回绿）；验收5 ✅（完成区 10 行、无运行期绝对路径、状态 `待验收` 与 `milestones.md` 一致，`check-milestones-fresh` PASS）。

**findings（均不阻断）**：① 任务书 `范围/非范围` 仍写「不在范围：QEMU」，与同书「用户裁定」节及实际 QEMU 改动冲突 ⇒ 落盘时补注「经用户 2026-11-07 裁定扩展」；② 完成区「与 026t 逐例 0 差异」只对当时那一轮成立（时间预算 bucket 复跑会抖，本轮 +2 pass），建议措辞加限定；③ 发现 `chmod`/`fchmodat` 在 gem5 SE 未实现（探针改为用 mode 000 创建文件绕开），与本任务 7 项无关，建议另立 issue；④ `tkill` 仅查本进程 tid、`kill(-1)` 含 self 与 Linux 的差异，已按任务书原文登记于自审。

**判决：Accepted** —— 7 项语义在 reviewer 自建探针与基线上独立复现，反例与门控均实测；QEMU 跨模块补丁另行给出结论。

#### 收尾（architect，2026-11-07 17:03）

- F1：范围/非范围已按用户 2026-11-07 裁定改为「QEMU `SS_AUTODISARM` 属在范围内（4 处补丁）」；落地 commit 说明显式点名 `components/qemu`。
- F2：完成区「逐例 0 差异」已改为「无 case 回退」，并注明 reviewer 轮 2 例 time-budget 抖动。
- F3：`chmod`/`fchmodat` 在 gem5 SE 未实现，登记 `ISS-346`（P3）。
- F4：`tkill`/`kill(-1)` 差异按任务书原文登记。
- 判决 Accepted（含 QEMU 补丁可接受结论），状态置 `已验证`。
