# m16-chipyard-028: RTL `cg9 rc6`（switch_run_mode）对齐：RW、复位 2、异步进入取该值

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m18-spec-006`（已合入：spec/契约改为「RW、复位 2 = supv；异步进入取该值」）；登记 `ISS-540`
**可并行分片**：否（与 `m16-gem5-026` 同改 `tests/arch/hart/` 与 `arch.yaml`，须等其合入；`components/chipyard` 本身空闲）
**预估**：2–3 h（标定：同档最近 5 件 RTL 任务派单→合入实测中位约 3.7 h（024 3h42、025 11h37、026 2h23、027 3h07、023 4h02）；本任务为单寄存器 2 位字段，取 0.5–0.8×）
**档位**：中改（RTL 单寄存器面）
**状态**：待验收
**执行环境**：本地（chipyard `WumingTiny/Vast` 构建与 sim）

> **归属（用户 2026-11-25）**：本任务是**平台差异修复**，归 **M16**，由 M16 会话派发；M18 的范围是 linux + qemu，不碰 chipyard。`ISS-540` 仅在 M18 册登记（由 `m18-spec-006` 引出），本任务只引用、不改其状态。

## 背景

`m18-spec-006` 已按用户裁定①把 `cg9 rc6`（`async_switch_run_mode`）口径定为：**RW、复位值 2（supv）、异步进入取该寄存器当前值**；QEMU 与 IDL 已是该行为。

RTL（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`）实测仍是“恒 supv”：

- 读 rc6：`Mux(rows.isAsyncSwitch, 2.U, …)`（≈:1352）——恒 2；
- 写 rc6：注释「accepted, ignored, reads return 2」（≈:1586）——写不落地；
- 异步进入：`runMode := 2.U`（≈:2000）——不取 rc6。

⇒ RTL 与 spec/QEMU/IDL 不一致（`ISS-540` 已登记），需补齐。

## 目标

1. RTL：`cg9 rc6` 改为 **RW 2 位、复位 2**；异步进入用该值作为 `runMode`，不再硬编码 2；写侧落地；`cg9` 仍是只读捕获缓冲的其它槽不变。
2. 探针：覆盖「写 rc6=0/1/3 后读回」「异步进入按 rc6 切换」「复位值 = 2」；Tiny/Vast 各跑通（如适用）。
3. 与 QEMU/IDL 同场景逐字节签名一致；不一致登记 `tests/arch/expected-divergences.yaml` 并说明。
4. 不回归：既有 M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem。

## 验收（逐条贴真实 rc）

1. chipyard `make verilog` + sim 构建 rc=0、`%Error`=0；sim md5 记录并注明环境。
2. 探针三组：复位 2、写 0/1/3 读回同值、异步进入 `runMode == rc6`；RTL 与 QEMU 同 ELF 签名一致。
3. **可达 FAIL ≥2 路**：① 读侧恢复 `Mux(isAsyncSwitch, 2.U, …)` ⇒ 写后读红；② 异步进入硬编码 `2.U` ⇒ rc6≠2 的进入用例红；`cp`+md5 还原并重建回绿。
4. 不回归：M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/chipyard/patches/**`（`GewuFile.scala.patch` 等 rc6 面）、`components/chipyard/changelog.md`、`tests/arch/**`（探针）、本任务书。
3. 不改 QEMU/gem5/LLVM/内核/spec/contracts；不改版本号；术语「bank = 寄存器组」。
4. 组件补丁经 `make_patch.py chipyard` 重导；生成断言用仓库生成器；还原 `cp`+md5；还原后重建。
5. 须等 M16 当前 chipyard 批次收口，避免同组件并发写；本任务由 M16 会话派单。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据脚本 `--base` 52/52 通过、`--inject` 13/13 通过；无失败。
**修改文件**：
- `components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch`（`cg9 rc6` 2 位寄存器；读/写/异步进入三处）
- `components/chipyard/changelog.md`（任务条目）
- `tests/arch/expected-divergences.yaml`（`DIV-18` 收窄：只剩 gem5，`close_when` 不动）
- 本任务书
（源树 `GewuFile.scala` 在隔离组件树改写后经 `make_patch.py chipyard` 重导；未提交 git）
**验收结果**：
- 构建：`make verilog CONFIG=WumingVastConfig -j32` + `make CONFIG=WumingVastConfig -j32` rc=0，`%Error`=0（组件源 `.conda-env` 的 PATH+RISCV，295 s）；sim md5 `309d119b39f088afbccfcc7957219506`。
- rc6 行为：复位读回 2；写 0/1/3 读回同值；异步进入 `runMode` = rc6 当前值（rc6=0 进 user、rc6=2 进 supv，由下一次进入的 `prev_run_mode` 证明），入口目标仍 `cfx_hart`。
- 探针：RTL `arch-hart-001` 89 槽、`arch-hart-002` S/U 各 40 槽逐槽绿；`run_arch --platforms qemu,chipyard` 三模式 PASS（gem5 待 `m16-gem5-025`）。
- 注入：① 读侧恢复恒 2 ⇒ 槽 18–20/84 红；② 进入恢复硬编码 2 ⇒ 槽 86 红；`cp`+md5 还原重建后回绿，sim md5 回 `309d119b…`（287/292/284 s）。
- 不回归：time/cache/pmem/ptw RTL 代表集、`mode_entry` H/S/U 两轴判权、Tiny `01-load-store` 38/38、`11-cfx` 4/5（`DIV-11`）。
- 门控：`check-patch-tree` chipyard 31 patches/0 problem、`--source-state` OK（HEAD=6ee049f，base+1）、`make_patch` 幂等（md5 `be8871…`）、index-blobs/tests-index/component-changelog/no-residue/`run_arch --self-test` rc=0。
**新发现/坑**：隔离树从主树 `cp -a` 后 `generated-src` 的 `.d` 仍含主树旧绝对路径（Verilator 警告可见），但 `make verilog` 已在本树重生成、行为按新 RTL（rc6=0 真进 user）；若要求日志零跨树路径需删 `generated-src` 全量重建（代价大）。chipyard classpath 缓存按 mtime 判定，`cp -p` 还原会不重编；全程 `cp`+`touch`。
**遗留问题**：无（gem5 的 rc6 对齐属 `m16-gem5-025`，`DIV-18` 已收窄保留）。

## 审阅记录

### 第 1 轮 engineer 自审
**意见（逐行审查改动）**：
1. 写侧 `io.wdata(gp.modeBits-1, 0)` 只落 2 位、读侧 `pad(dataBits)`，复位 `2.U(modeBits.W)`；与 spec「RW 2 位、复位 2」一致，`wdata` 高位被丢弃（探针写 3 读 3 验证）。
2. `runMode := r.asyncSwitch` 在 `for (r <- hartOpt)` 内，与 `curCfx := cfx_hart` 同拍；入口目标未变（hart-first），S/U 与 hmon 三模式探针均绿。
3. Tiny 无 `cfx_hart`（`hart=None`）⇒ 新寄存器不生成；Tiny 两套用例与基线一致。
4. 第一版补丁插入 `elsewhen` 时多了一个 `}`（读链括号），编译前自查修正；后续构建与探针证明链路完整。
5. 证据脚本 `--inject` 单独运行时补了「干净源树断言 + 当前 sim 作基线」，避免依赖先跑 `--base`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 读链括号多一个 `}` | ✅已修 | 删多余 `}`，恢复 `}.elsewhen(isAsyncSwitch)` | 构建 rc=0；`arch-hart-001` 89 槽绿 |
| `--inject` 单独运行缺基线 md5 | ✅已修 | 无 `base-sim-md5.txt` 时以干净源树的当前 sim 记录基线 | `bash -n` rc=0；`--inject` 13/13 通过 |
| 注入必须可达 FAIL | ✅已满足 | 两路注入均真重建并红后还原回绿 | 287/292/284 s；sim md5 回 `309d119b…` |

### 第 1 轮 reviewer 验收
**重跑（reviewer 亲自执行，仓库根运行期证据目录内 `run.sh`）**：
- `./run.sh --base` ⇒ `summary: 52/52 checks passed, 0 failed`，exit=0；`./run.sh --inject` ⇒ `summary: 14/14 checks passed, 0 failed`，exit=0（注入 A 294 s / B 289 s / 还原 288 s，`%Error`=0）。
- rc6 行为（静态+探针）：读侧 `regs.asyncSwitch.pad(dataBits)`、写侧 `elsewhen(isAsyncSwitch){asyncSwitch := wdata(modeBits-1,0)}`、`RegInit(2.U(modeBits.W))`（`modeBits=2`，`WumingParams.scala:278`）、进入 `runMode := r.asyncSwitch` 且 `curCfx := hart.cfxId` 不变；探针 `arch-hart-001/hmon` PASS 89 槽（复位=2、写 0/1/3 读回、`async rc6=0 → prev_run_mode=supv`、`async rc6=2 from user → prev_run_mode=user` 逐槽）、`arch-hart-002` smon/umon 各 40 槽 PASS；`--selfcheck` 现场派生 89/40/40 PASS。
- 三方：`run_arch --platforms qemu,chipyard` 三模式 rc=0，run.json `signature_equal=true`、槽数 qemu=chipyard=89/40/40；`cfx15.S` md5 与 master 逐字节同（`19169d88`，qemu-007 已合入）；`DIV-18` 现场解析 scope=[gem5]、status=active、close_when 保留。
- 注入（可达 FAIL）：run.sh 路 A ⇒ rc≠0 且槽 18/19/20/84 红（读恒 2）、路 B ⇒ rc≠0 且槽 86 红（进入硬编码），还原后 `PASS arch-hart-001/hmon（89 槽）`、sim md5 回 `309d119b39f088afbccfcc7957219506`。**reviewer 独立注入**（不经 run.sh，直接改被测源）：读侧恢复恒 2 ⇒ 重建 rc=0/`%Error`=0 ⇒ 探针 `probe_rc=1` 槽 18/19/20/84 红（expected 0/1/3/0, actual 全 2）⇒ `cp`+md5 还原（`07522f02…` 与 preinject 相等、源树 `git status` 空）⇒ 重建 rc=0/`%Error`=0、sim md5 `309d119b…`、探针 `probe_rc=0` PASS 89 槽。
- 补丁/源树：补丁重建文件 md5 `07522f02…` == 隔离组件树 `GewuFile.scala`；`check-patch-tree --source-state` ⇒ `chipyard: OK HEAD=6ee049fa39e1 count=1 clean=True expected=1`；`check-patch-tree` ⇒ `chipyard: 31 patch(es)` 0 problem（计数==series 行数）；`make_patch chipyard` rc=0、`0 written, 2 unchanged`、补丁集 md5 前后相同（独立复跑一次同样幂等）。
- 不回归（含于 52/52）：time/cache×2/pmem/ptw RTL 代表集、`mode_entry` TMODE=3/2/0 各 asm+sim+oracle 9 项、Tiny `01-load-store` 38/38、`11-cfx` 4/5（`report_red` 实测 rc=1，DIV-11 基线红）、index-blobs/tests-index/component-changelog/no-residue/`run_arch --self-test` rc=0。
- flake：本轮 cfx15 共约 10 次 RTL 运行 **0 次挂死**（全部证据日志 0 处挂死/超时），`ISS-m16-011` 未触发。
**约束核验**：改动仅 4 文件（任务书/changelog/GewuFile 补丁/DIV-18），与完成区「修改文件」一致；审前审后 `git status` 与 4 文件 md5 逐行/逐值相同；隔离组件树 `git status` 空、HEAD=6ee049f；Tiny 生成物无 `asyncSwitch`/`cfx_hart`、Vast 有（`hart=None ⇒ HartRegs` 不实例化）；未动 QEMU/gem5/spec/contracts、未升版本号；完成区 18 行≤30。
**finding（不阻断）**：① 完成区写 `--inject` 13/13，实际脚本 14 条检查、重跑 14/14（数字笔误）；② `GewuFile.scala` 注释仍留旧措辞「`cfx_hart` + the fixed supv entry」（紧邻新注释已改，代码行为正确）。
**判决：Accepted**（验收命令块在 reviewer 重跑下全绿、两路注入+独立注入均真红并回绿、约束无违反）。
