# m18-linux-002: K6 基础命令回归（shell 内 5 条命令）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-001`
**可并行分片**：否
**预估**：2–3 h
**档位**：中改
**状态**：待验收

> **迁移说明**：本任务原为 `m14-linux-033`（M14），用户 2026-11-20 裁定 K6 移入 M18 ⇒ 改号 `m18-linux-002`，任务范围不变。

## 背景

K6 出口判据之一：`busybox sh` 启动后能执行 5 条命令并输出正确、`exit 0`。本任务把这些命令固化为可重复回归（脚本化 stdin + 逐条断言）。

## 目标

1. **回归脚本**：向 `busybox sh` 的标准输入喂脚本（`echo`/`ls`/`cat`/`mkdir`/`rm`），采集 stdout/stderr/退出码。
2. **逐条断言**：每条命令的输出与退出码；`mkdir`+`ls`+`rm` 的组合（创建→列出→删除）。
3. **可 FAIL**：改错期望/删命令 ⇒ 断言必红；`cp`+md5 还原。
4. **不依赖 `/proc`**：若 `ps` 保留在 applet 集，按「无 `/proc` 退化」断言（打印自身或空表），并把该口径写清。

## 验收（逐条贴真实 rc）

1. 脚本 5 条命令全部执行，逐条输出/退出码正确。
2. `mkdir`/`rm` 的文件系统效果经 `ls` 验证（创建后可见、删除后不可见）。
3. 回归脚本 rc=0；注入（改一条期望）⇒ 红；还原 ⇒ 绿。
4. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：回归脚本/证据脚本、`/init` 或 shell 输入脚本（若需）、本任务书。
3. **不改版本号**；不提交 git；`cp`+md5 还原。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

实现按「跑一次 → 读失败 → 改 → 复跑」推进；每条都在最终 `run.sh`/输入脚本上复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 区间断言把 tty 输入回显与内核轨迹算进输出（首轮 `a-empty-listing-lines` 期望 0 得 2、`c-ps-table-lines` 同因） | ✅已修 | `region_lines()` 过滤 `^K[0-9] `（内核轨迹）与 `^dadao# `（输入回显）；`ps` 区间期望改 1 行并加「无 `PID USER` 表头」否定断言 | `run.sh` 50/50 PASS |
| R2 `run_all` 每次清零计数，`--inject` 的三段判定被吞（首版 `inject-restored-green: got=13`） | ✅已修 | 三轮跑完再清零，只报注入判定；三段输出各落日志 | `--inject` 7/7 PASS |
| R3 `inject-names-failing-check` 抓的是引导日志而非断言输出 ⇒ 假红 | ✅已修 | 改抓 `inject-mutated.log`（断言输出） | 同上 |
| R4 引导偶发未进用户态（rc=124 或 1）会让门控随机红 | ✅已修 | `boot()` 仅在「日志无 `/init -> busybox sh`」时打印 1 次重试（照 `check_k5.py` 先例）；用户态已起则绝不重试 | `fin1` 出现 1 次 `[INFO] c: …retry 1/1` 后 50/50 PASS |
| R5 `b` 脚本加标记行后落到既存缺陷的必红形状（同源长脚本 5/5 红） | ✅已修(规避) | `b` 取 5/5 稳定形状，不再加行；缺陷本身登记「遗留问题」1 | 3 轮连续 50/50 PASS |
| R6 未覆盖 `grep`/`cp` 等其它 applet | ❌不修 | 任务范围只 5 条命令；guest `grep` 已坏，单列遗留 | 遗留第 3 条 |

未修 finding：R6（范围外，已登记）。**判决**：可交付（`待验收`），但遗留 1–3 为 K6 既有缺陷，需 architect 登记。

### 第 1 轮 reviewer 验收

**重跑（我在本 worktree 亲自执行，非采信完成区）**
- 运行期证据目录内 `run.sh` ⇒ `RESULT: PASS checks=50 failed=0`、`RC=0`（4 项 build＋3 次启动，每次启动含 001 等价 6 断言，echo/mkdir/ls/cat/rm 逐条与组合、ps 退化口径全 PASS）。
- `run.sh --inject` ⇒ `RESULT: PASS checks=7 failed=0`、`RC=0`（baseline 绿→改期望→红→`cp` 还原 md5 `ad7b6f1b…`→绿）。
- **独立注入（走与 engineer 不同的路径）**：`cp` 备份 `run.sh`（md5 `750b5c10…`）→ `sed` 把 `b-visible-listing-count` 期望 `1`→`2` → 重跑 ⇒ `[FAIL] b-visible-listing-count: want=2 got=1 rc=1`、`RESULT: FAIL checks=50 failed=1`、`RC=1`；`cp` 还原＋`md5sum -c` `OK` → 重跑 `RESULT: PASS checks=50 failed=0`、`RC=0`，备份已删。
- **长脚本独立复现**：把 `repro-die-no-vma.txt` 直接喂 QEMU ⇒ `RC=0`、`dadao# ` 行 17、`result=die-no-vma` 1 次、`K6-REGRESSION-DONE` 0 次，末段 `dadao# rm /k6r/k6r_f1` 后 `va=0x0 vma=0x0-0x0 … result=die-no-vma` ⇒ 缺陷真实可复现；本 worktree 除任务书无组件改动 ⇒ 即 001 合入产物同样复现，与披露一致。
- 门控：`make check-config-pins` `RC=0`（85 项 0 败）、`make check-patch-tree` `RC=0`（11 套 457 patch，linux 105、busybox 3）、`make check-run-artifacts` `RC=0`（`check-run-artifacts: PASS`）、`make check-knowledge-refs` `RC=0`（0 具体 `.work/**` 引用）。
- 披露证据核读：`repro-die-no-vma.log`（17 条命令后 `die-no-vma`）、`repro-guest-grep-segv.log`（`subst-grep-rc=139`）、`repro-boot-hang.log`（`Run /init` 后停在 `K4 fork: kernel thread exec'd`、`terminating on signal 15` ⇒ rc=124）均属实；`qemu-a/b/c.log` 区间人工核对：LS-EMPTY 区 0 行、PS 区恰 1 行 `ps: can't open '/proc'` 且无表头、`k6r_f1` 全日志恰 1 行。
- 可 FAIL：逐条断言均有可达 FAIL（注入实测红），无恒真/两支同果；`boot()` 重试仅在「日志无 `/init -> busybox sh`」时触发（用户态已起绝不重试），第二次仍红 ⇒ 不掩盖崩溃。

**约束核验**：① 独立 worktree、`git status --porcelain -uall` 前后均只 ` M .tao/tasks/linux/m18-linux-002-基础命令回归.md`（证据目录为 gitignore），任务书 md5 快照对账一致；② 未改版本号、未提交 git、未动组件补丁/applet 集（12 个）；③ 5 条命令覆盖：echo(a)、mkdir(a/b/c，含重复 rc1)、ls(a 空、b 有、删后 rc1)、cat(b)、rm(b 成功、c 不存在 rc1)，组合 mkdir→写→ls→rm→ls 在同一启动内 ⇒ 验收 1–3 达标，001 的 6 条启动断言每次启动都跑。

**关键判断（拆 3 段是否违规）**：002 验收口径是「5 条命令逐条＋mkdir/ls/rm 组合＋rc/注入」，**未要求单次长脚本**；长脚本必红属既有 P1，`ISS-497` 已在主树 `issues.yaml` 登记（P1、含修法方向与「003 收口不得用短脚本冒充单次通过」），完成区新发现 1 与遗留 2 明写「长脚本当前必红、拆段原因、不得替代」⇒ **拆段符合本任务验收口径，不算掩盖**，缺陷由 `ISS-497`／`m18-linux-003` 收口。`ISS-498`（启动间歇，1 次打印重试、第二次仍红）、`ISS-499`（guest grep SIGSEGV，断言改 `$?`＋标记区间）均已登记；绕开的只是「用 guest grep 当断言手段」，5 条命令本身的输出与退出码断言未被削弱。

**非阻断 finding（记档，不返工）**：① `b.txt` 已 17 行、正处缺陷阈值边缘，稳定性为经验值（遗留 3 已自陈）；② 完成区「连续 3 轮＋另 3 轮全绿」为 engineer 自报，我只采信自己重跑的 50/50 与 7/7。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过（50/50 `RC=0`、7/7 `RC=0`、4 门控 `RC=0`）、独立注入必红且点名对应断言、硬约束无违反、缺陷已登记 `ISS-497` 且披露完整。`make check-knowledge-refs`（本记录写入后复跑）`RC=0`。

## 完成区

**测试结果**：运行期证据目录 `run.sh` **50/50 PASS、rc=0**（连续 3 轮＋另 3 轮全绿）；`run.sh --inject` **7/7 PASS、rc=0**（绿→改一条期望→红→`cp` 还原＋md5 复原 `ad7b6f1b…`→绿）；`make check-config-pins` 85 项 rc=0；`make check-patch-tree` 11 个补丁集 457 patch rc=0（linux 105、busybox 3）。单轮 `run.sh` 约 36 s。
**修改文件**：本任务书；运行期证据目录内新增 `run.sh`（回归＋注入自检）、`a.txt`/`b.txt`/`c.txt`（三段 shell 输入）、`build_k6.py`（沿用 `m18-linux-001` 的 K6 镜像构建入口）与三份复现日志。**未改**版本号、未提交 git、未改组件补丁与 applet 集（仍 12 个）。
**验收结果**（真实 rc，逐条）：
- 5 条命令逐条断言：`echo hello-k6`→输出行 `hello-k6`＋`echo-rc=0`；`mkdir`→`mkdir-rc=0`＋重复创建 `mkdir-again-rc=1`＋`can't create directory`；`ls`→空目录区间 0 行＋`ls-empty-rc=0`，有文件时 `k6r_f1` 在整日志中恰 1 行，删除后区间 0 行＋`ls-gone-rc=1`＋`No such file or directory`；`cat`→输出行 `payload-k6`＋`cat-rc=0`；`rm`→`rm-rc=0`＋删不存在路径 `rm-missing-rc=1`＋`can't remove`。
- 组合（同一次启动内）：`mkdir /k6b` → `echo payload-k6 >` 写文件 → `ls` 可见 → `rm` → `ls` 不可见 → 对已删路径 `ls` 失败。控制台只有一条 chardev，stdout/stderr 在通道上合流；分离靠 shell 重定向（`> file 2>&1` 后 `cat`）。
- `ps` 退化口径（applet 集含 `ps`、镜像无 `/proc`；镜像清单仅 `bin/ dev/ init init.musl`）：stderr 打印 `ps: can't open '/proc'`、**不输出表头/行（空表）**、`ps-rc=0`；断言 `PS` 区间恰 1 行且无 `PID USER` 表头。
- 等价启动检查（`m18-linux-001` 项，每次启动都断言）：`/init -> busybox sh` 行、`dadao# ` 提示、`built-in shell (ash)` 横幅，且无 `Kernel panic`／`die-no-vma`／`recursive supv exception`。
- 注入：`a.txt` 的 `echo hello-k6`→`hello-K6` ⇒ `a-echo-output` FAIL、整轮 rc=1；`cp` 还原后 md5 相等、回绿。
**新发现/坑**：
1. **K6 既有缺陷（非本任务引入）**：脚本化 stdin 到约 17 条命令时，ash 在 fork+exec 处读 NULL（`result=die-no-vma`、`va=0x0`、ip 落在 busybox 文本段）⇒ shell 被杀、后续命令不执行；同一输入 5/5 确定复现，且在 `m18-linux-001` 已合并产物上同样复现（运行期证据目录 `repro-die-no-vma.txt` / `.log`）。本回归据此拆 3 段短启动才稳定。
2. **间歇启动未进用户态**：控制台停在 `Run /init …`／`K4 fork: kernel thread exec'd` 之后无输出，QEMU rc=124 或 1（`repro-boot-hang.log`）；按 `check_k5.py` 先例做 1 次打印重试，第二次仍红。
3. **guest `grep` 每次 SIGSEGV（rc=139）**，含无匹配的 `grep -q`（`repro-guest-grep-segv.log`）⇒ 断言不能用 guest grep，改用 `$?`＋标记区间；12 applet 中 `grep` 实际不可用。
4. `ls` 在 tty 上按列排版，断言须整行锚定/区间计数，子串匹配会漏判。
**遗留问题**：
- 上述 1–3 属 pre-existing K6 缺陷，需 architect 登记 issue／立后续任务；本任务只交付回归脚本，**不声称**缺陷已修。
- 「单次启动跑全部命令」的长脚本当前必红；`m18-linux-003` 收口门控须据此处置（先修或登记已知红），不得以短脚本通过替代。
- 回归的稳定性是经验值（当前形状连续多轮绿），输入脚本形状对缺陷触发敏感，后续改动须重跑 `run.sh` 与 `--inject` 两模式。
- 复现前提：`run.sh` 需已 prepare 的组件源树（linux/busybox/musl 补丁已应用）与 `.dadao`/`.cache`（本 worktree 用符号链接共享主树安装根与镜像，**只读**，未写共享安装根）；脚本自身重跑 busybox/initramfs/defconfig/vmlinux 后启动。
