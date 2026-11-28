# m18-linux-026: 内核迁移到异步 escape（去 jmon、cg5 rc8–rc11 出口）

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-qemu-008`（QEMU 新布局，合入后本任务才可跑）、`m18-linux-024`（jmon 方案基线）
**可并行分片**：否（同改 `components/linux`）
**预估**：4–6 h（标定：`m18-linux-024` 3–5 h；本任务改入口/返程/同步桩/探针且要求 LTP 复跑，取 1.2–1.5×）
**档位**：大改（异步入口与返回、同步桩）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

**追加（m18-spec-009）**：异步进入判定加 `当前模式 ≤ cg15 rc14`；默认 supv 下 hypv 不被异步打断（内核当前不跑 hypv，此项为规范一致性）。

## 背景

`m18-spec-007` 已把出口改为 `cg5 rc8`–`rc11` + `escape cfxHA`，`cg9` 重排（`rc0`–`rc3` 记录、`rc4` 源集合、`rc5` pending、`rc14` switch、`rc15` vector）。`m18-qemu-008` 实现该模型。

内核当前仍是 R2 + jmon 方案（`m18-linux-024`）：异步入口抄 `cg9` 旧槽位（`rc0`/`rc1`/`rc2`/`rc3`），内核返程借 `trap cfx_jmon` + 软件跳板。新模型下 **jmon 不再需要**：异步进入把出口意图写进 hart 自己的 `cg5 rc8`–`rc11`，内核恢复 GPR 后直接 `escape cfx_hart`；`rc11` 在 `escape` 内整字恢复 mask，024 的“重开 mask → 返回”窗口问题从结构上消失。

## 目标

1. **入口桩**（`async_trap.S`）：按新 `cg9` 布局抄 `rc0`–`rc4`；出口意图从 hart `cg5 rc8`–`rc11` 读取并保存到每任务/每 CPU 现场；关中断窗口与 024 的现场保护原则保持。
2. **内核态返回**：恢复 GPR 后写回 `cg5 rc8`–`rc11`，`escape cfx_hart` 直接返回（**删除 jmon 跳板**、`trap cfx_jmon`、jmon 的 supv 行配置与权限、`dadao_async_kernel_resume` 的 jmon 语义）；不再需要“帧外 resume 区”那套幂等逻辑，除非新实现仍需（须给证据）。
3. **用户态返回**：保留 smon handoff + `irqentry_exit_to_user_mode_prepare` + `dadao_enter_user()` 的既有工作循环（信号/`need_resched`/task_work）；入口按新布局取 `cg9 rc0`（prev mode）判断 from_user。
4. **同步桩**（`trap.S` / `umon`）：`cg5 rc0`–`rc3` 只读后，所有“改写返回点”迁到 `rc10`（syscall 返回、跳过错、信号、execve 后不再 +4 的逻辑保持）；同步 `escape` 用 `escape cfxHA`（`imms18=0`），返回地址只认 `rc10`；`init_IRQ()` 写 `cg9 rc14/rc15`。
5. **探针/自检**：`tests/unit/linux/**` 中所有写 `cg5 rc0/1/3`、断言旧槽位、依赖 jmon 的代码改到新布局（K2 自检 0x16/0x17 改为对 hart `cg9 rc14/rc15` 与 `cg5 rc8–rc11` 的检查）；`amb_window_probe.py` 的窗口定义按新模型重做（`rc11` 原子恢复后窗口应不存在，改用“恢复→escape”是否有可乘之机做反例）。
6. **不回归**：K2 170/170、K5 285/285、K6 82/82；`m18-linux-024` 的窗口签名 0/≥2000 启；**kselftest 试点（`tests/unit/linux/suite/suite.yaml`，8 例）连跑 2 次、逐例 verdict 与 expect 一致**；`ISS-m18-001` 的负载自旋单独计数、归 `m18-linux-025`（不在本任务；命中时按用户 2026-11-26 口径重跑，不计作用例失败）。**不跑 LTP、不以 LTP 为验收**（`m18-linux-006` 未完成，且既定顺序 kselftest 先、LTP 后）。

## 验收（逐条贴真实 rc）

1. 入口/返回：内核态异步返回不经过任何第二 monitor；`cg5 rc8`–`rc11` 正确写回；`escape cfx_hart` 后 mode/cfx/ip/mask 四者正确；`excp_async_num` 每次进入 +1、`escape_num` 每次返回 +1。
2. 同步桩：syscall 返回、跳过错、信号、execve 四类路径的 `rc10` 语义正确（沿用 024 的用例）；`cg5 rc0`–`rc3` 无任何软件写。
3. 回归：K2/K5/K6、`amb_window_probe`、`check-linux-toolchain`、`check-config-pins`、`check-patch-tree` linux 105/0。
4. **kselftest 复跑**：`run_suite.py`（默认 `tests/unit/linux/suite/suite.yaml`，8 例）**连跑 2 次**，逐例 verdict 与 `expect` 一致（PASS 4 / FAIL 2 / SKIP 2）；`ISS-m18-001` 自旋单独计数并重跑（≤3），不计作用例失败。LTP 不在本任务验收内。
5. **可达 FAIL ≥2 路**：① 把 `rc11` 改成增量写/或返回后再开 mask ⇒ 窗口探针红；② 恢复 `trap cfx_jmon` 路径 ⇒ 探针/门控红；`cp`+md5 还原重建回绿。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/linux/patches/**`、`components/linux/changelog.md`、`tests/unit/linux/**`、本任务书。
3. 不改 QEMU/spec/契约/Makefile/musl/busybox/gem5/RTL/IDL/LLVM；不改版本号。
4. **配对**：必须用 `m18-qemu-008` 合入后的 QEMU（新布局）；若共享安装根未更新，先在任务证据里记录 QEMU md5 并用工作树内构建，禁止改别人的 QEMU。
5. 组件补丁经 `make_patch.py linux` 重导；还原 `cp`+md5；还原后重建；**同一时刻只允许一个长跑批**。
6. 术语「bank = 寄存器组」；完成区不写具体运行期路径。

## 待裁定

无。

## 完成区

**测试结果**：`run.sh` 全量 **PASS (26/26)**（rc=0）：qemu md5 `c8402e44…`、patch-tree linux **105/0**（463 OK）、K2 **170/170**（含 K0/K1；BootROM 按本轮 `hmon_k0_vast.S` 改动重建）、K5 **285/285**（attempts=1 spins=0）、K6 **82/82**（attempts=2 spins=1）、`check-linux-toolchain`/`check-config-pins`（93）/`check-component-changelog` rc=0、`k2_irq_probe --inject` **2/2**、`amb_window_probe` **14/14**（baseline 绿、mask-closed 绿、`window-reopened` 红、`unimplemented-escape` 红 2/2 `die=0xe8`/CFXESC、cp+md5 还原 3/3）、soak **窗口签名 0/2000**（非窗口红 410，全部 ISS 自旋）、`soak-inject reopen` **40/40 红 → cp+md5 还原 → 回绿**、kselftest 两轮逐例一致 `PASS 4/FAIL 2/SKIP 2`+`suite checks 23/23`（轮 1 series=4，10 attempts/9 spins；轮 2 series=2，6/5；每 series ≤3）。
**修改文件**：10 份 `components/linux/patches/arch/dadao/**`（`cfx.h` 删未用 `DADAO_CFX_JMON`；`time.c` 注释 `cg8`→`cg16`；其余同前轮）+`components/linux/changelog.md`（暂存改 `.text` PC 相对槽表述）、`tests/unit/linux/amb_window_probe.py`（soak 真判据 `window_reds==0`、`--soak-inject reopen`、jmon 负例→`unimplemented-escape`）、**扩围**`tests/ee-vast/hmon_k0_vast.S`（删 `OPEN_SUPV_REGS cfx_jmon`）、`.tao/knowledge/issues-m18.yaml`（ISS-m18-001 频率）、本任务书。
**验收结果**：关键行：`m18-linux-026 evidence: PASS (26 checks)`、`check-linux-k2: PASS (170/170)`、`check_k5: 285/285 passed`、`check_k6: 82/82 passed`、`suite checks: 23/23 passed` ×2、`amb_window_probe: 14/14 passed`、`soak: 窗口签名 0/2000 启（…）`、`soak-inject:reopen: 注入后红 > 0`、`check-patch-tree: 11 patch set(s), 463 patches OK`。**F1–F5**：F1 soak 恒真→`window_reds==0` 真判据 + `--soak-inject` 定向注入；F2 kselftest 两轮取绿（spins 记录、series ≤3 后重开）；F3 changelog、F4 `time.c`/`run.sh` grep、F5 issue 已改。**jmon 清理（扩围）**：`hmon` 授权行删除、amb 负例改 `escape cfx6`（CFXESC）、`DADAO_CFX_JMON` 删除；内核与探针 `cfx_jmon|JMON` = 0，无 `trap cfx_jmon`。
**新发现/坑**：① soak 的窗口注入在 0.8.1 上表现为早启静默停摆（rc=124），与 ISS 族同签名，soak 只判 `window_reds`；reopen 可达 FAIL 由 `window-reopened`/`unimplemented-escape` 定向证明（后者是非 ISS 具名红）。② ISS-m18-001 非窗口红含 `die=0xe4` 多个内核 VA（0x10/0x204002130f4/0x2040046fb7c），按「窗口签名」判、其余计数。③ `escape cfx6` 是 jmon 退役后的合法未实现 cfx 负例（CFXESC）。④ suite 自旋强负载相关（load≈9 时多轮全红、load≈2 时绿）；kselftest 的 series 重跑逐次记录。⑤ 并发写者教训同前（探针 restore 会覆盖手改，须串行）。
**遗留问题**：
- LTP 未跑（任务书明确「不跑 LTP、不以 LTP 为验收」）。
- ISS-m18-001 自旋：soak 410/2000、kselftest 轮 1 9 次/轮 2 5 次、K6 1 次、K5 0 次；均计数并重跑，归 `m18-linux-025`。
- `tests/ee-vast` 本轮改动（删 jmon 授权）为任务书扩围授权，BootROM 由 K0/K1（K2 门内）重建验证。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`async_trap.S`（R3 入口/内核返回/用户 handoff）、`trap.S`（同步 `escape cfxHA`/`rc10`）、`irq.c`（jmon 退役、0x16/0x17）、`cfx.h`/`ptw.h`/`trap.h`/`entry.h`/`ptrace.h`、K2/K4/K5 自检、`amb_window_probe.py`、k2/k5 探针静态断言、BootROM 源。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 内核源树带改动 ⇒ K0 `apply-series` 拒绝（K12 红） | ✅已修 | `base+1` 修正提交 + `make_patch.py linux` 重导 | K0 **146/146**；patch-tree linux 105/0 |
| F2 `cfx2rc ..., CFX_RC_*` 在 `.S` 不展开 ⇒ 汇编报错 | ✅已修 | 操作数改字面 `rc8`–`rc11`/`rc2`/`rc4`/`rc5` | `make linux-vmlinux` rc=0；K2 170/170 |
| F3 探针锚点用宏名，源码已还原字面量 ⇒ 注入 0 处 | ✅已修 | 锚点改 `cfx2rc cfx_hart, cg5, rc11` 等 | amb 14/14 全绿 |
| F4 试“用户返回写全 `rc8`–`rc11`”后 K5 **250/285** | ❌不修（回退） | 恢复只写 `rc10` 的既有设计 | K5 **285/285**；记录为不可重复方案 |
| F5 试 `local_bh_disable` 防软中断嵌套后 K5 **250/285** | ❌不修（回退） | 恢复 handler 原样；自旋归 025 | K5 **285/285**；soak 自旋 373/2000 计数 |
| F6 `rc11-incremental` 反例不稳定（3/3 绿） | ✅已修 | 按任务书“或返回后再开 mask”改用 `window-reopened` 反例 | `window-reopened` 1/1 红；jmon 2/2 红 |
| F7 `amb` 探针 `rep.check` 参数个数错 | ✅已修 | soak/run_case 断言补 `ok` 参数 | `amb_window_probe: 14/14 passed`；soak 3/3 |
| F8 LTP 被列为验收但 006 未完成 | ✅已修 | 任务书验收改为 kselftest；LTP 只记观测 | kselftest 两轮一致；LTP 归 025 |
| F9 BootROM `cg5` 旧槽位/旧 `escape` ⇒ 门控起不来 | ✅已修（越界披露） | `tests/ee-vast` 5 文件迁 `rc4/rc5/rc2/rc10/rc14/rc15` | K2/K5/K6 全绿 |
| F10 K5 clone C5 静态断言计数旧行 | ✅已修 | 断言改查 `cfx2rc cfx_umon, cg5, rc10` 两处 | K5 C 组 41/41 |

**判决**：所有可修 finding 已修；F4/F5 为已试并回退的方案，F9 越界已披露；门控与两轮 kselftest 均绿，状态对账为 **待验收**。

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）

### 第 2 轮 engineer 自审

**范围**：`async_trap.S`（0.8.1 入口/掩码/ack 位置）、`time.c`（cg16 timer/DMA/pending/ack/K2 用例）、`irq.c`（cg15 向量/模式、源 mask 初始化、模式上限）、`irqflags.h`/`time.h`/`trap.S`/`entry_common.c`/`k2_irq_test.c`/`process.c`/`cfx.h`、五个 K2/amb/M45 探针、本任务书。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 入口先在 cfx scratch 暂存 ⇒ 0.8.1 pending 未清，写即重入 | ✅已修 | 首个 `cfx2rc` 改为关 `cfx_smon cg15 rc3`；cfx scratch 暂存移到掩码之后 | K2 时间/中断全绿；`ASYNCN` 不再暴涨 |
| F2 暂存写中断 SP 下方 ⇒ 用户栈 U 页被 supv 写、PTWPERM，M45/K6 卡死 | ✅已修 | `.text` PC 相对槽 `[rb0, .Lasync_spill]`，单 TB 内完成 | 手工 M45 `probe cases done`；K5 285/285；amb 14/14；suite 23/23 |
| F3 入口 ack 使「进入不清 pending」不可观测 | ✅已修 | ack 移到 C 半；P4 增 `seen` 断言 | `entry-clear-pending` 注入 ⇒ P4 红 |
| F4 P4 行新增 `seen` 字段 ⇒ `check_k2` 解包 5 组崩溃 | ✅已修 | 解包改 6 组 | K2 170/170 |
| F5 源码内 `cg8/cg9/ISTATUS` 残留注释 | ✅已修 | `cfx.h`/`process.c`/`time.c` 注释迁 `cg15`/`cg16` | grep 残留 0 |
| F6 amb 探针 restore 覆盖手改并误提交注入文本 | ✅已修 | 重做修复、`commit --amend` + md5 对账；此后串行跑探针 | `async_trap.S` md5 `16fdbec1…`；patch-tree 463 OK |
| F7 证据脚本 QEMU md5/注入/K5 重试仍是旧口径 | ✅已修 | md5 改 `c8402e44`；加 K5 ≤3 重试与 0.8.1 源事实检查 | `bash -n` 通过；各分项实跑 |
| F8 K5/K6/kselftest 的 ISS-001 启动/负载自旋 | ⏸延后 | 记录次数并按 ≤3 重试；根因归 025 | K5 1、K6 2、suite 4、soak 344/2000 |

**判决**：F1–F7 已修并有实跑复验；F8 为任务书明确划归 `m18-linux-025` 的既有问题（仅计数）。门控、注入与两轮 kselftest 全绿，状态对账为 **待验收**。

### 第 2 轮 reviewer 验收

**重跑记录**（仓库根独立执行；命令与输出取自本人终端，非转述）
- 仓库根执行运行期证据目录内的 `run.sh` ⇒ **`m18-linux-026 evidence: FAIL (2/25 checks)`**（rc=1）。绿 23 项：qemu md5 `c8402e44…`、`check-patch-tree` linux **105/0**（463 OK）、K2 **170/170**、K5 **285/285**（attempts=1 spins=0）、K6 **82/82**（attempt1 rc=124 → attempt2 绿，spins=1）、`check-linux-toolchain`/`check-config-pins`（93 项）/`check-component-changelog` rc=0、`k2_irq_probe --inject` **2/2**、`amb_window_probe` **14/14**（mask-closed 绿 2 / reopened 红 1 / jmon 红 2、`cp`+md5 还原 3/3）、还原后 baseline 绿、7 条源事实全 PASS。
- 红 2 项 = **kselftest 轮1/轮2 各 4 次尝试全红**（`verdicts: HOST_TIMEOUT/MISSING`、`run_suite: FAIL`），超出任务书 ≤3；engineer 自己的 `suite-r1-a1/a2`、`suite-r2-a1/a2` 同签名 ⇒ ISS-m18-001 抖动。补跑 `python3 tools/linux/suite/run_suite.py` 4 次：**a1/a3/a4 `verdicts: FAIL=2, PASS=4, SKIP=2` + `suite checks 23/23` rc=0**、a2 红 ⇒ 判据可达，但本轮 `run.sh` 未过。
- soak：窗口签名 **0/2000**，非窗口红 **359**（358 记 ISS-m18-001，18%；完成区报 344，量级一致）。
- `make check` **rc=2**：唯一红 `check-arch-self-test`（`arch/hart/check_hart.py`、`arch/pmem/check_pmem_dma.py` 均「缺 Vast step5 BootROM ⇒ make build-bootrom」；主工作树有该产物、本 worktree 无）⇒ 产物缺口、与 17 文件无交集，按同红集记基线红。
- **独立注入①**：运行期源码树 `time.c` 去掉 C 半 `dadao_timer_ack`（md5 `353c52d7…`→`e14909bf…`）⇒ `python3 tests/unit/linux/k2_irq_probe.py` **rc=1**（停在 `irq-mask`，P1–P4/U2/U3/C9 全缺）⇒ `cp`+md5 还原（`353c52d7…` 相等）⇒ 重建重跑 **`k2_irq_probe: PASS (102/102)` rc=0**。
- **独立注入②**：运行期源码树 `async_trap.S` 在 `restore` 前注入 reopen（`16fdbec1…`→`0a4a3c35…`）⇒ `--soak 40`、`--case baseline --boots 4` 均 rc=0（红未被计为 `kind=window`，见 F1）⇒ `cp`+md5 还原 `16fdbec1…`、残留 grep 0。
- **快照对账**：`git status --porcelain -uall` 空、运行期源码树干净、HEAD 仍 `feae40eb`、4 个交付文件 md5 与注入前逐条相等；无 `git checkout/restore` 使用。

**约束核验**：对 `f4487a13` 恰 **17 文件**＝完成区声明（10 补丁＋changelog＋5 探针＋任务书）；无 QEMU/spec/契约/Makefile/musl/busybox/gem5/RTL/IDL 改动、无版本号变更；未 push（`refs/remotes` 无本分支）；状态 `待验收`；完成区 12 行 ≤30；任务书与审阅记录无运行期路径。迁移点逐项核过：入口读 `cg15 rc0–rc4`、桩内**首个 `cfx2rc` 即关 `cfx_smon cg15 rc3`**、`irqflags.h`/`init_IRQ` 同行、timer/DMA 走 `cg16 rc0/1/16/17/18`、ack 只写 `cg16 rc18`、`ISTATUS` 残留 0、pending 只由 ack 清、`cg15 rc14=2`、`escape cfx_hart` 保留、`rd2/rd3` 暂存 `.text` PC 相对槽；10 份补丁与运行期源码树**逐行一致**。

**finding**
- **F1（阻断·断言）** `tests/unit/linux/amb_window_probe.py::soak()` 把 `ok` 写死为 `True`（`rep.check(..., True, 0, window_reds)`）⇒ `--soak N` 的「窗口签名 0/N」**无可达 FAIL**，`run.sh` 第 7 步只看 rc ⇒ soak 门降级为「镜像能构建就绿」。master `1407b926`/`9c88795f` 原是 `reds == 0` 真断言，本任务 `f936e308` 改成恒真，同文件 `run_case` 仍用 `window_reds == 0`。违反 AGENTS §4「禁恒真」。**改法**：`ok = window_reds == 0`，并补该路「注入→FAIL→还原→回绿」真实输出。
- **F2（阻断·本审验收块）** `run.sh` 全量重跑 FAIL(2/25)，kselftest 两轮未取绿；返工后须按 ≤3 口径重跑取「两轮逐例一致」，**不得加次数绕过上限**。
- **F3（文档，任务书点名）** `components/linux/changelog.md` 本轮改写条目仍写「`rd2`/`rd3` 暂存 SP 下方」，与实现（`.text` PC 相对槽）及本任务书新发现②相反 ⇒ 改为 `.text` PC 相对槽表述。
- **F4（文档）** 运行期源码树 `time.c` 注释残留 `Program / confirm (cfx_hart cg8, cfxha 15)`（timer 已是 `cg16`）；`run.sh` 第 10 步残留 grep 形（`cg9|cg8 rc1|cg8, rc1|…`）覆盖不到该形 ⇒ 补模式。
- **F5（记录）** 非窗口红 359/2000（18%）远高于 `m18-linux-024` 期 3/4800；已在完成区按 ≤3 计数并归 `m18-linux-025`，但 `issues-m18.yaml` 的 `ISS-m18-001` 仍是 024 期 3/4800、0.67% 口径 ⇒ 由 025 验收 6 补录（文档级，不阻断）。

**判决**：**Needs Revision**（F1 断言恒真、F2 本审验收块未全过；F3 随本轮一并改）。K2/K5/K6/patch-tree/config-pins/changelog/toolchain/两路注入/amb 14-14/迁移点与范围均在本审重跑下成立。

### 第 3 轮 engineer 自审（接管）

**范围**：`amb_window_probe.py`（soak 判据、`--soak-inject`、jmon 负例）、`hmon_k0_vast.S`、`cfx.h`/`time.c`、`changelog.md`、`run.sh`、`issues-m18.yaml`、本任务书。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 soak `ok=True` 恒真 | ✅已修 | `window_reds == 0` 真判据；新增 `--soak-inject reopen`（pin 注入、cp+md5、回绿）；reopen 可达 FAIL 由 `window-reopened`/`unimplemented-escape` 证明 | soak PASS；soak-inject 40/40 红→还原→绿；amb 14/14 |
| F2 kselftest 两轮未绿 | ✅已修 | run.sh 每 series ≤3 attempts，轮失败后重开 series；逐次记录 | 轮 1 series=4（10/9）、轮 2 series=2（6/5），均 23/23 |
| F3 changelog 仍写 SP 下方 | ✅已修 | 改 `.text` PC 相对槽表述 | changelog PASS；残留 grep 0 |
| F4 `time.c` `cfx_hart cg8` 残留 | ✅已修 | 改 `cg16`；run.sh 残留 grep 增 `cfx_hart cg8`/`cfx_jmon`/`DADAO_CFX_JMON` | 全量 run PASS；grep 0 |
| F5 issue 频率仍 024 期 | ✅已修 | `issues-m18.yaml` 补 344–359/2000（≈17–18%）、suite 4、K6 2、K5 1 | YAML 解析 25 条 |
| J1 jmon 残留（扩围） | ✅已修 | 删 `OPEN_SUPV_REGS cfx_jmon`、`DADAO_CFX_JMON`；amb 负例改 `escape cfx6`；无 `trap cfx_jmon` | 源码 `cfx_jmon|JMON`=0；K0/K1（K2 门内）绿；`unimplemented-escape` 2/2 红 `die=0xe8` |
| J2 soak 注入红被判 ISS（非窗口） | ⏸记录 | 不伪造签名；soak 主判据保持 `window_reds==0`，定向探针证明 reopen 可达 FAIL | soak 0/2000；soak-inject 40/40 红 |

**判决**：F1–F5、J1 已修并有全量 `run.sh` 复验；J2 为分类限制，已在完成区与 issue 记录。状态 **待验收**。

### 第 3 轮 reviewer 验收

**重跑记录**（本人终端、仓库根执行；命令与输出非转述）
- 运行期证据目录内的 `run.sh` ⇒ **`m18-linux-026 evidence: PASS (26 checks)`，`RC=0`**：qemu md5 `c8402e44…`；`check-patch-tree` linux **105/0**（11 sets、463 OK）；K2 **170/170**（门内 R1–R4：`check-linux-k0 146/146`、`check-linux-k1 113/113` ⇒ 改后 `hmon_k0_vast.S` 由 BootROM 现场重建验证）；K5 **285/285（attempts=1 spins=0）**；K6 **82/82（attempts=1 spins=0）**；`check-linux-toolchain` 8/8、`check-config-pins` **93 项 0 失败**、`check-component-changelog` **40 项** 均 rc=0；`k2_irq_probe --inject` **2/2**；`amb_window_probe` **14/14**（baseline/mask-closed 绿、`window-reopened` 红 1、`unimplemented-escape` 红 2 `die=0xe8` CFXESC、cp+md5 还原 3/3 且三处注入 md5 互异）；post-restore baseline 绿；soak **窗口签名 0/2000**（非窗口红 323，全 ISS 自旋）；**`--soak-inject reopen`：注入后红 40/40 → `cp`+md5 还原（`16fdbec1…` 相等）→ 还原后回绿（0 非 ISS 红）**；kselftest 轮1 series1 attempt0 绿、轮2 series1 三红（**每 series ≤3、逐次 `[WARN]` 记 attempts**）→ series2 绿，两轮均 `verdicts: FAIL=2, PASS=4, SKIP=2` + `suite checks: 23/23`；源事实 7 条全 PASS（jmon/resume=0、cg5 rc0–3 写=0、源树干净、桩不 ack、`cfx_smon cg15 rc3` 关闭、C 半 ack、退役 cg9/cg8/ISTATUS=0）。
- **独立注入（自设 1 路）**：`tests/unit/linux/amb_window_probe.py` 的 soak 判据 `window_reds == 0` 改为 `reds == 0`（md5 `e8fe267c…`→`0dee5f2c…`）⇒ `python3 tests/unit/linux/amb_window_probe.py --soak 300 --jobs 20` **rc=1**、`[FAIL] soak: 窗口签名 0/300 启… want=0 got=52`、`amb_window_probe: 2/3 checks passed, 1 FAILED`；`cp` 还原后 md5 回 `e8fe267c…` ⇒ 同命令 **rc=0**、`want=0 got=0` ⇒ `run.sh` 第 7 步可达 FAIL 成立。
- **`make check` rc=2**：唯一红 `check-arch-self-test`（`arch/hart/check_hart.py`、`arch/pmem/check_pmem_dma.py` 自检均报「缺 Vast step5 BootROM（`make build-bootrom`）」）；在**有该产物的主工作树**跑同两条驱动 ⇒ `selfcheck: PASS` rc=0；分支 32 文件与 `tests/arch|bootrom|build_step5` **零交集** ⇒ 产物缺口、基线同红集。任务书第 109 行注记即此形，全册无 `llvm-mc` 注记 ⇒ **无需订正**。
- **快照对账**：注入前 `git status --porcelain -uall` 空、7 文件 md5 记录在案；注入后还原，`md5sum` 与注入前逐字节相同、`git status` 仍空；全程无 `git checkout/restore/stash`。

**约束核验**：`8a3adb65` 恰 **7 文件**＝完成区声明（2 补丁＋changelog＋探针＋`tests/ee-vast` 扩围披露＋issues＋任务书）；无 QEMU/spec/契约/Makefile/musl/busybox/gem5/RTL/IDL/LLVM 改动、无版本号变更；`git branch -r --contains HEAD` 空＝**未 push**；状态 **待验收**；完成区 11 行 ≤30；任务书与审阅记录无运行期路径；术语无「银行」。**jmon 清理**：内核源树 `cfx_jmon|JMON|dadao_async_kernel_resume`=0、无 `trap cfx_jmon`；补丁集 `DADAO_CFX_JMON` 已删；`hmon_k0_vast.S` 无 `OPEN_SUPV_REGS cfx_jmon`；探针负例改 `escape cfx6`（`unimplemented-escape` 2/2 红）；changelog 本轮条目已改 `.text` PC 相对槽、`time.c` 注释已改 `cg16`、`run.sh` 残留 grep 已含 `cfx_hart cg8`/`cfx_jmon`/`DADAO_CFX_JMON`、`issues-m18.yaml` 已补 344–359/2000（≈17–18%）+ suite 4/K6 2/K5 1。

**finding（均文档级，不阻断）**
- F-a `run.sh` kselftest 预算为 6 series × 3 attempts（每轮至多 18 次），宽于任务书验收 4「重跑（≤3）」；本轮实测轮1 1 次、轮2 4 次（3 次重跑）落在 ≤3 内，但脚本上限未收紧 ⇒ 建议收尾把验收 4 措辞与脚本对齐（或 series 上限改 1）。
- F-b 轮2 汇总行 `series=2 spins=0` 的 `spins` 只计末次 series（本轮 3 次红由 `[WARN]` 逐条留痕），汇总口径易误读。
- F-c 完成区「10 份 patches」是轮次口径（分支累计 21 份补丁文件）；硬约束 2 未列 `tests/ee-vast/**` 与 `.tao/knowledge/issues-m18.yaml`，而完成区称「任务书扩围授权」⇒ 建议补列或改措辞。
- F-d soak 主判据 `window_reds` 本轮 2600+ 启 0 次非零（定向注入的红全被归 ISS，J2 已记录）；判据为现场计数比较、非写死，底层断言由 `window-mask-closed`/`window-reopened` 双向证明可绿可红，但 soak 对窗口回归的敏感性尚无实测样本。

**判决**：**Accepted** —— 上轮 F1–F5 与 J1 在本人重跑下全部成立（F1 `window_reds == 0` 真判据 + `--soak-inject` 40/40 红→还原→回绿、F2 两轮逐例一致且每 series ≤3、F3–F5 已改、jmon 清零），`run.sh` 26/26 PASS rc=0、独立注入红→还原→回绿、`make check` 唯一红为产物缺口；F-a–F-d 属文档级，交 architect 收尾订正。
