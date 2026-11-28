# m18-linux-029: 异步精确点残余（忙等 7/20，疑 QEMU `cg15 rc2` 在 `ret` 上口径）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-028`（主因 `CFXESC` 已修）、`m18-linux-007`（忙等复现器）
**可并行分片**：否（先诊断，可能牵涉 QEMU 模型）
**预估**：3–5 h（标定：同档 025/028 实做各约 5 h；本任务已有 7/20 复现器，定位为主）
**档位**：大改（异步精确点 + 可能 QEMU 模型）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`，本 worktree 自建）

## 背景

`m18-linux-028` 修掉主因（user 异步把捕获交接 `cfx_smon` 后不 escape ⇒ 任务被切出期间 `cfxha != inner_cfx_code` ⇒ `CFXESC`，且 escape 落在恢复用户 SP 之后 ⇒ semihosting 参数失效、静默自旋）。修后 `CFXESC` 0/3，但忙等探针仍有 **7/20** 红，签名不同：

- 任务用户帧 `ip` 落在**相邻函数体**（`worker+0x10`，即该函数 prologue 之后）；
- `SP` 仍是该任务自己的用户栈；
- `start`（该任务等待的共享变量）**未置位**；
- 无 die、无 `CFXESC`；QEMU monitor 显示 CPU 在 **user 模式**执行该 ip。

`ISS-m18-011` 记录该残余，并给出假设：QEMU 对**异步精确点**（`cg15 rc2` = 已提交指令之后的 `rb0`，“跳转即目标”）在 `ret`/间接跳转边界上的取值，与内核假设不一致。

## 目标

1. **先诊断、后改**：确认是「QEMU 模型取值与 spec 一致但内核假设错」还是「QEMU 与 spec 不一致」。判据 = 用 `spec/` 正文（`DADAO-12 §5.4`、`ADR-0064`）逐条比对 `cg15 rc2` 在 `ret`/间接跳转上的定义，并用最小 RTL/QEMU 对照实验（可用 `tests/arch` 或最小汇编）取实测值。
2. **可复现**：复用 `m18-linux-007` 落在运行期证据目录的忙等复现器（`probe/pthread_busywait.c` + `run_busywait.py`），修前 ≥7/20 红、同一签名。
3. **修复**：
   - 若判「QEMU 与 spec 不一致」⇒ 改 `components/qemu/**`（最小），并按 `m18-qemu-007/009/010` 的口径重导补丁；同时评估对 RTL/gem5 的影响（不改它们，登记差异）。
   - 若判「内核假设错」⇒ 改 `components/linux/patches/**`（最小）。
   - **若 spec 本身没定义清楚** ⇒ 停下写「待裁定」（现象、签名、两种口径、影响面），不要自行改 `spec/`/`.tao/contracts/`。
4. **不得放宽判据**：K2/K5/K6、LTP 两轮、`amb_window_probe`、soak 全部保持原判据。

## 验收（逐条贴真实 rc）

1. 诊断结论：spec 条文引用 + 实测值 + 判「QEMU 错 / 内核错」的依据；若落到 spec 缺口，任务书「待裁定」给出两种口径。
2. 修前 ≥7/20 红（同一签名）、修后 **0/≥20**；日志与现场快照落盘，每跑次独立目录。
3. **可达 FAIL ≥2 路**（`cp`+md5 还原 + 重建）：① 回退修复 ⇒ 复现；② 破坏守护/断言 ⇒ 探针红。
4. 不回归：K2 170/170、K5 285/285、K6 82/82、`run_suite.py --suite ltp` 两轮逐例一致、`amb_window_probe` 14/14、soak 窗口 0/≥1000 且静默自旋 0。
5. `ISS-m18-011` 闭合（`resolved_by` 指向本任务）；与 `ISS-m18-005/006/009` 的关系写清。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`、`components/qemu/patches/**`（仅在诊断判 QEMU 错时）、对应 `changelog.md`、`tests/unit/linux/**`、`tools/**` 中相关工具、`.tao/knowledge/issues-m18.yaml`、本任务书。不改 `Makefile`/`spec/`/`.tao/contracts/`/其它组件。
3. QEMU 用本 worktree 自建（记 md5）；不覆盖共享安装根。
4. 组件补丁按 `docs/Process-01` 重导；还原一律 `cp`+md5；还原后重建；同一时刻一个长跑批。
5. 禁「重试直到绿」；命中 `ISS-m18-005/006` 时单独计数记签名。

## 待裁定

无（诊断若指向 spec 缺口，按目标 3 在完成区前写入本节）。

## 完成区

**诊断判定**：**内核假设错**（QEMU 与 `spec/DADAO-12 §5.4` 一致、非 spec 缺口）。条文：§5.4「异步精确点 = 已提交指令之后的 `rb0`（跳转即目标）」、§5「精确异常」；实测：最小 `call`/`ret` 循环探针 151–159 个异步样本、49–52 个落在 `call+4` 返回点、`ret`/`ret+4` **0** 个；QEMU `-d exec` 轨迹坏轮次 `0x2a3b4 → 0x22104`（正常 `→ 0x2a3e8`），且坏轮次 sysret 处 `cfx_umon cg5 rc8=2(supv)`、`rc11=0xffff…ffff`（正常 `0 / 0xfffffffeffff7fff`）。根因：`cfx_umon cg5` 单帧出口意图跨睡眠被覆盖（`dadao_enter_user` 的 supv→user `trap` 写 rc8/rc9/rc11），umon 返回路径只重写 `rc10` ⇒ 回到 supv 执行用户代码，下一次 `trap cfx_umon` 用陈旧 supv 向量（某 worker `0x22104`）进用户。
**测试结果**：忙等探针 **修后 0/20 红**（20 启全 `BUSY end`、`qemu rc=0`；修前同签名 7–13/20）。`m18_async_ret_probe.py` 6/6（samples 151/162、`call+4` **实测 45–58**、`ret`/`ret+4` 0）。回归：K2 **170/170**、K5 **285/285**、K6 **82/82**、LTP 两轮逐例一致（各 PASS=14、20/20 checks，`results.json` diff 空）、`amb_window_probe` **14/14**。soak 修后累计 **1200** 启、窗口 **0/1200**：轮1 `--soak-strict` **rc=1**，3 个非窗口红如实列——boot92 `die=0xe4,pf-va=0x10,rc=228`（`ISS-m18-006`）、boot94 `die=0xe4,pf-va=0x0,rc=228`（新登 `ISS-m18-015`）、boot100 `rc=124,no-exit-row,no probe-cases-done,no-irq-row, kind=iss`（console 轮1 落共享 scratch 被并发覆盖、**不可复核**；按 `ISS-m18-004` 同形未证实登记、不作归因）；轮2 / reviewer 轮 / 返工轮各 **0/300**（`--soak-strict` rc=0，逐启 console 归档运行期证据目录 `soak-r3/log/`）。静态：`check-patch-tree` **rc=0**（qemu 源树按 Process-01 重放后 464 patches/0 problem）、`check-config-pins` 105/105、changelog/knowledge-refs/`check_issues`（011 closed、012/014/015 open）/`check-tests-index`/`check-dirs`/`check-no-residue` rc=0；`check-milestones-fresh` rc=2，唯一 VIOLATION = `m18-linux-031` 台账（非 029；029 行 A1/A6/R1 全过）。
**修改文件**：`components/linux/patches/arch/dadao/kernel/trap.S.patch`（重导：030 帧重构 + 029 四字出口意图）、`components/linux/changelog.md`、`tests/unit/linux/m18_async_ret_probe.py`（新）、`tests/unit/linux/amb_window_probe.py`、`tests/unit/linux/m45_entry_probe.py`（`AMB_SCRATCH`/`M45_QEMU` 环境口，默认不变）、`.tao/knowledge/issues-m18.yaml`、本任务书。
**验收结果**：证据目录 `run.sh` 实测 **PASS**（忙等 20 + ret 1 + 静态 5；`--soak N` 经 `AMB_SCRATCH` 把逐启 console 归档进本任务证据目录、`M45_QEMU` 钉本 worktree 构建）；`--inject revert` **2/8–7/12 红**（reviewer 7/12，同签名 `rc=124 frame_ip=0x22104` ＋ `die-no-vma vma=0x0-0x0`）、`--inject break` **4/8 红**；两路 `cp`+md5 还原（`cf9fb771…`）+ 重建后回绿。QEMU 本 worktree 自建重放后 md5 `fc68d9b7…`（重放前 `74fe4bc4…`）。
**新发现/坑**：① `cfx_umon cg5` 单帧不只 `rc10` 跨睡眠失效，`rc8/rc9/rc11` 同样；② `sigsegv` 子型是同一路径的次级表现；③ `-dfilter` 语法是 `start+size`，`-d exec` 是全局轨迹需按 TB 前驱分任务；④ 新增 `tests/unit/linux/*.py` 必须模块级声明 `CONFIG_PINS`；⑤ 逐启 console 必须落本任务证据目录（共享 scratch 会被并发会话覆盖）；⑥ 忙等/ret 探针会把 `.config` 的 `CONFIG_INITRAMFS_SOURCE` 复原为默认 cpio；⑦ **与 030 的补丁冲突/重导**：合并 master（030 的 `trap.S` 帧重构）时 `trap.S.patch` 整文件冲突；按 Process-01 E5 + m20-infra-003 用 `private_source.sh linux m18-linux-029` 建私有树、重放 master 补丁集（`--source-state linux` OK；`trap.S` 含 030 的 `DADAO_GPR_SAVE_STAGED_AT`/`rb32` 帧基址），再把 029 的 `DADAO_UMON_USER_EXIT_INTENT` 宏与 skip/retry 两站点叠加到 030 版（位于 `escape cfx_umon` 前，仅用 `rd2`，不碰 030 的 `rb32`/`rb3` 帧基址逻辑），`make_patch.py linux --source <私有树>` 重导（1 written / 104 unchanged），merge commit `e3b2ac3`；⑧ 新规：共享源树（`<work_root>/source/<c>`）只读，构建/导出走私有树（`DADAO_SOURCE_ROOT`/`DADAO_LINUX_SOURCE`/`DADAO_LINUX_BUILD`）。⑨ reviewer 第 3 轮 nit：`trap.S` skip 站点上方旧注释「Only `rc10` needs restoring — the other exit-intent fields are the same for every user trap」与紧随的四字重写自相矛盾，已在私有树改为「`rc8`-`rc11` are all rewritten below (`DADAO_UMON_USER_EXIT_INTENT`)…」，重导 `trap.S.patch`（注释-only，1 written/104 unchanged；md5 `7164f226…` → `50a72cc0…`，私有 `trap.S` `34f05a8c…` → `1022e584…`）；`check-patch-tree` linux 段 0、`linux-vmlinux` rc=0。
**遗留问题**：`ISS-m18-012`（`dadao_trap_busy` hart 全局跨睡眠）不同源、未动；`ISS-m18-005/006/015` 与 `ISS-m18-004` 族仍 open（soak 修后累计 1200 启仅轮1 3 红，频率 3/1200；本修复让用户态一致可抢占，可能略增既有 `die=0xe4` 族暴露率，属 006/015 处理范围）；对称的 `cfx_smon cg5` supv 返回路径同样只重写 `rc10`（已登 `ISS-m18-014`，`m18-linux-031` 并行处理）；`ISS-m18-009` 主因已由 028 修复。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`trap.S.patch`（`DADAO_UMON_USER_EXIT_INTENT` + 两站点）、`m18_async_ret_probe.py`、`issues-m18.yaml`；逐行核对四字出口意图的取值（user/umon/任务帧 ip/现场 umon 掩码）与 `escape cfx_umon` 的目标模式/掩码恢复，`cfx2rc` 写点不触发 `dadao_async_kick`、仍在 `DADAO_CLOSE_SUPV_ASYNC` 之前。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 残余是否真为 QEMU `cg15 rc2` | ✅已查清 | 不做假设；`-d exec` 轨迹 + sysret 出口意图实测 | 坏轮 `0x2a3b4→0x22104`、`esc_mode=2`；ret 探针 `ret`/`ret+4` 0/154 |
| F2 修法是否只治标 | ✅已修 | 根因是单帧出口意图，修在返回路径重写全部四字（不是只补 rc10） | 20/20 绿；两路注入均红 |
| F3 是否放宽判据 | ✅未放宽 | 忙等判据改「0 红」更严；K2/K5/K6/LTP/amb/soak 原判据 | 见完成区 |
| F4 可达 FAIL | ✅两路 | `--inject revert` / `--inject break`，均 cp+md5 还原+重建 | 2/8、4/8 红 → 回绿 |
| F5 新探针自身可失败 | ✅ | 断言 ret 存在、采样覆盖 `call+4`、`ret`/`ret+4` 为 0 | 修前若 QEMU 报 ret 即红；`CONFIG_PINS` 补声明后 config-pins 105/105 |
| F6 范围/提交 | ✅合规 | 只动任务书允许的 5 个文件；不提交 git | `git status` 仅上述文件 |

**判决**：F1–F6 已处置并有真实复验；状态 **待验收**。

### 第 2 轮 engineer 自审

**返工范围**：F1 披露/归因、F2 样本量、F3 qemu 重放、F4 台账注记、F5 数字、F6 console 归档。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 strict rc=1 未披露/归因错 | ✅已修 | 完成区如实写轮1 rc=1 与 3 红原始签名；boot94 `pf-va=0x0` 新登 `ISS-m18-015`；boot100 按 `ISS-m18-004` 同形**未证实**（console 不可复核，删“启动期挂起”说法） | `soak.log` 3 行、`check_issues` rc=0 |
| F2 修后 <1000 | ✅已补 | 再跑 300（`AMB_SCRATCH` 归档 300 console、`M45_QEMU` 钉本 worktree qemu `fc68d9b7…`） | 返工轮 4/4 rc=0；修后累计 1200、窗口 0/1200 |
| F3 patch-tree rc=2 | ✅已修 | qemu 源树 E5 重放（ad9a918→7daf36d）+ 重建 qemu | `check-patch-tree` rc=0（464/0） |
| F4 milestones-fresh | ✅已注 | 完成区记 rc=2、唯一 VIOLATION=`m18-linux-031`（非 029） | `r2-milestones-fresh.log` |
| F5 call+4 数字 | ✅已订 | 45–52（reviewer 45、本机 49/52） | 本轮 ret 162 样本、52 `call+4` |
| F6 console 归档 | ✅已修 | `amb_window_probe` 加 `AMB_SCRATCH`、`m45_entry_probe` 加 `M45_QEMU`（默认不变）；`run.sh --soak` 归档 | `soak-r3/log/` 300 份；默认 `run.sh` PASS |

**判决**：F1–F6 已修并有真实复验；状态 **待验收**。

### 第 3 轮 engineer 自审（合并 master / trap.S 重导）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 整文件补丁冲突 | ✅已修 | 不手工合并：取 master 侧补丁 → `private_source.sh` 私有树重放 → 叠加 029 delta → `make_patch` 重导（1 written/104 unchanged） | `trap.S.patch` 同时含 029 宏/两站点与 030 `DADAO_GPR_SAVE_STAGED_AT`/`rb32` |
| 030 帧基址被破坏 | ✅未破坏 | 029 宏只用 `rd2`、位于 `escape cfx_umon` 前，不碰 `rb32`/`rb3` 帧基址 | 私有树 `check-patch-tree` rc=0；K2 **170/170**、K6 **82/82** |
| 共享树写权（新规） | ✅合规 | apply/export/build 全在私有树；共享树未写 | `--source-state linux` OK（HEAD `9bd6ef7`、clean） |
| 029 修法仍有效 | ✅ | 合并后 `run.sh --inject revert` → 3/8 红；`cp`+md5 还原（`34f05a8c…`）后 2/2 绿 | `run.sh` 默认 PASS（忙等 0/20、ret 6/6） |

**判决**：合并/重导完成，两侧特性共存；状态 **待验收**。

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，真实 rc/输出）**
1. 运行期证据目录内 `run.sh`（20 启）→ **EXIT=1**：忙等 `0/20`、ret 探针 `6/6`（samples=151、`call+4` 覆盖 45、`ret/ret+4`=0）、`check-config-pins` `105/105`、changelog/knowledge-refs/`check_issues` `rc=0` 全 PASS；`check-patch-tree` **rc=2**（F3）⇒ `evidence: FAIL (1)`。
2. 注入①（我自写，非脚本内置）：两处 `DADAO_UMON_USER_EXIT_INTENT rd4` → `cfx2rc … rc10, rd4`（注入后 md5 `14c84221…`）→ 同一 `run.sh --boots 12` → **7/12 红、同签名**（6× `rc=124 frame_ip=0x22104` ＋ 1× `die-no-vma vma=0x0-0x0`）；`cp`+md5 还原（`cf9fb771…`，与注入前逐字节同）→ `run.sh --boots 4` 忙等 `0/4` 回绿。
3. 注入② `run.sh --inject break`（只删 `rc8` 写）→ **BREAK_EXIT=0**：`inject rc=1 pass=4/8` 红、`restore … OK`、`post-restore rc=0 pass=2/2` 绿、`evidence: PASS`。
4. 回归（本人）：`check-linux-k2` **170/170**、`check-linux-k5` **285/285**、`check-linux-k6` **82/82**、`run_suite --suite ltp` ×2 各 `PASS=14`+`20/20 checks` 且 `results.json` 逐例 **LTP-IDENTICAL**、`amb_window_probe` **14/14**、`--soak 300 --soak-strict` **EXIT=0**（窗口 `0/300`、静默自旋 `got=0`、`4/4 passed`）。
5. 门控（本人）：`check_issues rc=0`（011 closed/`resolved_by=m18-linux-029`、012 open、014 open）、`check_milestones_fresh rc=1`（F4）、`check-patch-tree` **linux 段 0**（F3）；changelog/knowledge-refs `rc=0`。
**约束核验**：5 文件与完成区一致（`git show --stat 5005fa760`）；QEMU/`spec`/`Makefile`/`.tao/contracts` 零改动；注入前后 `git status --porcelain -uall` 均空、5 文件 md5 逐一相同（`447f4af6…`/`852269fe…`/`d6d71ae5…`/`92a27659…`/`0cb915af…`）；`git log origin/master..HEAD`=2 ⇒ 未 push；状态 `待验收`；任务书无运行期路径；两次注入均 `cp`+md5 还原回绿。
**诊断判定（核心）**：spec `DADAO-12 §5.4（四）`「`async_cause_ip` = 提交后的 `rb0`，跳转即目标」＋§5.2 步4「`rc11` = 进入前运行模式 monitor 的 `cg15 rc3` 快照、`rc8` = 异常前运行模式」；我复跑 ret 探针 151 样本、45 落 `call+4`、`ret/ret+4`=0 ⇒ QEMU 与 spec 一致，**QEMU 假设排除**。真因我自证：`dadao_enter_user()` → `arch_local_irq_disable()` 置 supv 行 bit15|32 ⇒ `0xfffffffeffff7fff|0x100008000 = 0xffffffffffffffff`，随后 `dadao_umon_enter()` 的 `trap cfx_umon,0`（supv→user）按 §5.2 把 `rc8=2(supv)`/`rc9=smon`/`rc11=0xffff…` 写进单帧 `cfx_umon cg5`；修前只重写 `rc10` ⇒ 与坏轮次实测 `rc8=2 / rc11=0xffff…` 逐位吻合 ⇒ **「内核假设错」成立**。
**修法核对**：skip(333)/retry(342) 两处均调用、四字齐全、`rc11` 现场 `cfx2rd cfx_umon,cg15,rc3`（非常量）；`escape` 按 §5.3 步3 把 `rc11` 整字写回**目标行 = umon 自己那行** ⇒ 写回即原值、无遮蔽顺序问题；`rd2` 其后由 `DADAO_GPR_RESTORE_AT` 整文件恢复；全仓仅 2 处 `escape cfx_umon` 均已覆盖（`.Lumon_delegate` 尾走 `trap`、不用出口意图，非缺口）。
**判决：Needs Revision**（阻断两条，均在本任务自己的 soak 交付）
- **F1 阻断**：验收4「窗口 0/≥1000 **且静默自旋 0**」在轮1 未达成——运行期日志 soak 轮1 实录 `soak-strict: 静默自旋 0/300（窗口 0、handle_softirqs die 1）: want=0 got=2`、`soak.EXIT=1`；完成区只报「窗口 0/600」，未披露该 strict `rc=1`。归因亦不成立：boot94 `die=0xe4,pf-va=0x0`（脚本 `kind=other`，不在 `ISS-m18-006` 记录的 `pf-va=0x10/0x204002130f4` 集合，完成区却写 `pf-va=0x10`）；boot100 `rc=124` 按脚本 `rc==124 ⇒ kind=iss`（即静默自旋），其逐启 console 在共享临时 scratch（026 硬编码）已被并发会话覆盖，「启动期无 async 行」无法复核。**修法**：完成区如实写轮1 strict `rc=1`；两启按先例（`ISS-m18-006`/`007`）落 issue 或把 console 归档进运行期证据目录并给出签名判据，归因不符者改写。
- **F2 阻断**：修后 soak 累计 **600 < ≥1000**（我复跑 +300 ⇒ 900，仍差 ≥100；`m18-linux-025` 先例即「修后 0/1000」）。**修法**：再跑 ≥1 轮 `--soak 300 --soak-strict`，使修后累计 ≥1000 且 strict 全绿。
**非阻断 finding**：F3 `check-patch-tree` 在合并树 **rc=2**（qemu 段 8 problem、**linux 段 0**）——字节级比对证明本 worktree 的 qemu 运行期源树 HEAD diff == `5005fa76` 的补丁集、≠ `2ab401ec`（合并带入其它任务的 4 个 qemu 补丁而源树未重放）⇒ 环境/源树状态、非029 五文件；完成区「rc=0」系合并前实测、合并后未重跑 ⇒ 收尾前按 `docs/Process-01` 重放 qemu 后重跑，或在源树一致处重跑并更新完成区。F4 `check-milestones-fresh` **rc=1**：5 项 VIOLATION 全非029（`m18-linux-031` 台账待开始 ＋ m19 四项），029 行 A1/A6/R1 全过、在「进行中」。F5 ret 探针 `call+4` 我实测 45（完成区 49–52），断言为 `≥1` 非阻断。F6 逐启 console 落共享临时目录会被并发会话覆盖，建议红启 console 复制进证据目录。
**采信声明**：soak 轮1/轮2/基线与 `--inject break` 归档为他人所跑，我逐行核对其原始日志与 `*.EXIT`（`soak.EXIT=1`、`soak-fix-r2.EXIT=0`、`soak-baseline.EXIT=0`、`evidence-break.EXIT=0`）；其余数字均为我本人现场输出。

### 第 2 轮 reviewer 验收

**重跑记录（本人执行）**：① 证据目录内 `run.sh`（默认 20 启）→ **EXIT=0 / `evidence: PASS`**：忙等 **0/20**、ret **6/6**（samples=153、`call+4`=58、`ret/ret+4`=0）、`check-patch-tree` **rc=0**（`12 patch set(s), 464 patches OK`、problem 0）、config-pins/changelog/knowledge-refs/`check_issues` 全 rc=0；② K2 **170/170**、K5 **285/285**、K6 **82/82**、LTP ×2 各 EXIT=0 且 `results.json` 逐例 **LTP-IDENTICAL**（14/14）、`amb_window_probe` **14/14**；③ `make check-milestones-fresh` **rc=2**、唯一 VIOLATION = `m18-linux-031`（非 029），与完成区披露一致；`check_issues` 011 closed（`resolved_by=m18-linux-029`）/012/014/015 open；④ 证据抽验：证据目录 `soak-r3/log/` **300 份**（抽 `soak-1`/`soak-157` 均 `probe cases done`＋`M45 exit`）、`amb-r2/log/` **7 份**（抽 1 份完整）；返工轮归档 `窗口 0/300`、`soak-strict got=0`、`4/4 passed`、**EXIT=0**；QEMU 现 md5 `fc68d9b7…`、被测 `trap.S` 仍 `cf9fb771…`。
**F1 闭环**：完成区如实写「轮1 `--soak-strict` **rc=1**」并逐启贴原始签名；`ISS-m18-015` 内嵌的 `soak boot 94: RED (die=0xe4,pf-va=0x0,rc=228,…, kind=other)` 与归档日志**逐字一致**；boot100 按 `ISS-m18-004` 记「**同形未证实**、不作归因」并注明 console 不可复核 ⇒ 归因不再越界；逐启 console 已落本任务证据目录（300/7 份）⇒ **闭环**。
**F2 闭环**：修后累计 **1200** 启（轮1＋轮2＋reviewer 轮＋返工轮）、窗口 **0/1200**；轮2/reviewer 轮/返工轮三轮 strict **rc=0**，轮1 rc=1 已如实披露并按先例登记 ⇒ **闭环**。
**默认值核对**：`AMB_SCRATCH` 默认仍是原字面量共享 scratch、`M45_QEMU` 默认仍是 `toolchain_bin()/qemu-system-dadao` ⇒ **他人证据路径不变**；`run.sh` 默认模式断言逐行未变，仅新增 `--soak` 分支（FAIL 路径 = 探针 rc≠0）。
**范围**：`git status` 仅 5 文件（issues／任务书／changelog／两探针），`components/qemu`、`spec/`、`.tao/contracts`、`Makefile` **0 diff**；`origin/master..HEAD`=2 ⇒ 未 push；状态 `待验收`；`ISS-m18-011` 条目未被返工触碰、修法源树 md5 未变。
**判决：Accepted（第 2 轮）**
**非阻断 finding**：N1 完成区「修改文件」未列 `tests/unit/linux/amb_window_probe.py`、`tests/unit/linux/m45_entry_probe.py`（返工实际改动，均在硬约束2 允许的 `tests/unit/linux/**` 内、自审 F6 已披露）⇒ 收尾 staging 对账时补列；N2 `call+4` 完成区写 45–52、我本轮实测 **58**（上轮 45），断言为 `≥1` 非阻断，建议去掉上界改「实测 45–58」；N3 AGENTS「共享源树单写者／`replay_source.sh`」系 12:08 由 `m20-infra-003` 合入、晚于本轮 qemu 源树重放（`ad9a918→7daf36d`、重建 rc=0），不构成本任务违规，后续按新规则执行。
**采信声明**：soak 各轮与返工门控为归档，我逐行核对原始日志与 `*.EXIT`（`soak.EXIT=1`、`soak-fix-r2.EXIT=0`、`soak-baseline.EXIT=0`、`r2-soak-r3.EXIT=0`、`r2-build-qemu.EXIT=0`）；其余数字均为我本人现场输出。

### 第 3 轮 reviewer 确认

1. **共存**：`git diff master...HEAD -- components/linux/patches/arch/dadao/kernel/trap.S.patch` 只有 **+25 行 `DADAO_UMON_USER_EXIT_INTENT` 宏 ＋ skip/retry 两站点替换 ＋ index/hunk 头**，其余 1816 行与 master（030 重导版）逐行相同 ⇒ 030 的 `DADAO_GPR_SAVE_STAGED_AT cfx_smon` 与 `rb32` 帧基址段（`rb2rb {rb3},{rb32}`、`rb2rb {rb32},{rb3}`）**一行未丢**；029 宏体只用 `rd2`、`rc11` 现场 `cfx2rd cfx_umon,cg15,rc3,rd2`，两站点帧基址取自 `dadao_umon_frame` 的 `rb3`，**未触碰 `rb32`**。补丁 md5 = `7164f2260006f4bc4562be82b66fe705` ✓
2. **补丁↔私有树**：私有树 HEAD `9bd6ef7eb dadao: linux patch series`（base `7b20d05fd Linux 7.2.10` ＋1）、`git status` 空（clean）；其 `trap.S` md5 `34f05a8c…` = 证据快照 `trap.S.fixed` = `trap.S.fixed.sha`；以 `DADAO_SOURCE_ROOT`/`DADAO_LINUX_SOURCE`/`DADAO_LINUX_BUILD` 指向该私有树执行 `run.sh`，其内置 `check-patch-tree` **rc=0**（`12 patch set(s), 464 patches OK`、problem 0）✓
3. **行为未回退（本人重跑）**：证据目录内 `run.sh` 默认 20 启 → **EXIT=0 / `evidence: PASS`**，忙等 **0/20**、ret **6/6**（samples=160、`ret/ret+4`=0）、五项门控全 rc=0；`--inject revert` → **EXIT=0**，`inject rc=1 pass=3/8` 红 → `cp`+md5 还原（`34f05a8c…` 与注入前一致）→ `post-restore rc=0 pass=2/2` 绿 ⇒ 可达 FAIL 仍成立 ✓
4. **范围**：`git diff master...HEAD` = **7 文件**（`5005fa76` 的 5 ＋ 返工 2 探针），与完成区「修改文件」7 项一一对应；`issues-m18.yaml` 仅 011 关闭／新增 015／004、006 追加四处；无 qemu／spec／契约／`Makefile`／他任务文件；`git branch -r --contains e3b2ac34` 空 ⇒ **未 push**；状态 **`待验收`** ✓

**判决：维持 Accepted（第 3 轮确认）**
**非阻断 nit**：skip 站点上方沿用的旧注释仍写「Only `rc10` needs restoring — the other exit-intent fields are the same for every user trap」，与紧随其后的四字重写自相矛盾，建议收尾时改掉（纯注释，不影响行为）。
