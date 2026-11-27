# m16-chipyard-020: RTL cfx0/2 模式进入路由（B）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-019`（A：cfx0/2 寄存器面与权限）合入
**可并行分片**：否
**预估**：6–8 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定：先 A 再做 B）

`m16-chipyard-019` 只补了 cfx0/2 的寄存器面与权限。RTL 的同步异常仍**固定进 hmon**（`WumingParams.scala.patch:154` 的 `monitor = 0`），没有“U-mode → cfx0”“S-mode → cfx2”的路由，也没有 user/supv 模式下的 `switch_run_mode`、异常帧与向量。本任务补这条主控制流。

## 要做

1. **模式进入路由**：按 `DADAO-12 §5.2` 与 `contract-see`：
   - U-mode 同步异常 → cfx0 umon；
   - S-mode 同步异常 → cfx2 smon；
   - H-mode 仍 → cfx3 hmon（现有）。
2. **`switch_run_mode`**：从 user/supv 陷入时按 `<mode>_switch_run_mode` 切换运行模式；与 `trap`/`escape` 的目标 cfx 组合对齐。
3. **异常帧**：`inner_run_mode`、`inner_excp_cause_*`、`inner_excp_ip`、`prev_cfx` 等按 `§5.2` 保存/恢复；`escape` 恢复语义与 QEMU/gem5 一致。
4. **异步中断**：单 hart 的 timer/pmem 中断按当前模式进入对应 monitor（与 M16 的中断源范围一致；不含 UART/IPI/多核）。
5. **用例**：U-mode/S-mode 同步异常进入、帧字段、`switch_run_mode`、`trap`/`escape` 三方（QEMU/gem5/RTL）签名一致。

6. **HSU（运行模式）**（用户 2026-11-22：HSU 纳入、J 不纳入）：U/S/H 三种模式的进入与权限检查；J-mode 不测，写入未覆盖项。

7. **三方用例（B）**：cfx0/2 的 case 定义/期望只写一份；RTL 探针与 QEMU/gem5 后端复用同一 case（非必要不为每个平台写三份载体），由 `check-arch-vast` 按需跑三方。

**H/S/U 三模式**（用户 2026-11-22）：本任务本身就是把 U/S 路由做稳；验收必须覆盖 `hmon`/`smon`/`umon` 三种模式下的异常进入、`switch_run_mode`、异常帧，不能只验 hypv/hmon。

**两轴 `cfxreg` 强制判定**（承接 019 遗留①）：019 只落存储面与 `readOk/writeOk` 行判；本任务必须补上 `CFXPERM` 强制——U/S 下访问 cfx0/2 时按目标 cfx 的 `<mode>_cfxreg` 掩码 + `cg3 rc12` deleg 判权；未写 deleg/未开放掩码 ⇒ `CFXPERM|NCFXPERM`。与 `m16-testcases-017` 的 env 掩码准备配合，不能留成两任务互指的空档。

## 不做

- 不改 cfx0/2 的寄存器行/权限（019）；
- 不改 cfx3/4/5 的既有语义；
- 不加多核/IPI/UART/J-mode。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 改 `WumingCore` 主控制流，必须逐步验证；重建每次约 30 分钟，证据脚本记录耗时与环境；
- 术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. U-mode 同步异常进入 cfx0、S-mode 进入 cfx2、H-mode 仍进 cfx3；帧字段（cause/info/ip/prev_cfx/run_mode）逐项；
2. `switch_run_mode` 与 `trap`/`escape` 组合；异常返回后状态正确；
3. 单 hart timer/pmem 中断进入对应 monitor；
4. 三方同一 ELF 签名逐槽一致；不一致登记 `expected-divergences.yaml`；
5. **可达 FAIL**：注入「U-mode 仍进 hmon」⇒ 用例红；注入「switch_run_mode 不生效」⇒ 红；`cp`+md5 还原并强制重建后回绿；
6. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## ADR-0060 调整（2026-11-23，后于本任务实现）

`ADR-0060` 将异步投递改为 **hart-first**（`cfx_hart cg9`），取代本任务实现时的 monitor-first。因此：

- **本任务验收只计同步部分**：U/S 进入路由、`switch_run_mode`、同步异常帧、两轴 `CFXPERM|NCFXPERM`、`trap`/`escape(cg5)`；
- **异步部分移交**：TIMER/PMEM_DMA 的投递、pending、mask、`escape` 选 cg9 由 `m16-chipyard-021`（cg9 基础设施 + TIMER）与 `022`（PMEM 完成）按 hart-first 实现；本任务的 monitor-first 异步代码不再作为验收依据；
- `DIV-08`（monitor pending）已删除（monitor-first 作废）；`DIV-07`（hypv 不强制）改为 **temporary**，`close_when` = RTL 交付链改为 `cfx_hmon` 源，**待用户确认**；
- reviewer F4（`escape` 清入口 monitor 无可达 FAIL）/F5（hypv 异步未实现）随 021/022 的 hart-first 用例补。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`（A–F）**PASS=53 / FAIL=0**、rc=0；`run.sh --inject`（G）**PASS=31 / FAIL=0**、rc=0。三模式探针（同一份 `mode_entry.S`，链接期 `--defsym TMODE=0/2/3`）在 Vast 上 H/U/S 各跑一次：guest rc=0，签名 **112 / 168 / 112 B**（14 / 21 / 14 槽）逐槽等于现场从 `spec/DADAO-12` §1/§3.1/§3.4/§4.7/§4.9/§5.2–§5.3 与 `contract-see §3/§6.1.1` 派生的期望；`--self-test` 21/14/14 条槽 mutation + 2 截断 + 1 多槽全部被判红、0 漏检。注入①「去掉模式路由」⇒ U 异常仍进 hmon，guest rc=**226（0xE2）**、oracle rc=1；注入②「忽略 `switch_run_mode`」⇒ U 体在 hypv 跑、guest rc=**227（0xE3）**、oracle rc=1；两路均 `cp`+md5 还原（`fd76f30b…` 前后相同）并强制重建后回绿。Tiny `11-cfx` 5/5、`01-load-store` 38/38 与 019 的 pre-020 基线逐镜像**字节差 0**。
**修改文件**：组件源 3（`generators/dadao-gewu/.../GewuFile.scala`、`generators/dadao-wuming/.../common/{WumingCore,WumingParams}.scala`；提交为 base+1 `144df173` 并重导 3 份补丁，`make_patch.py chipyard` 幂等 0 written，`series` 仍 26 条）；`components/chipyard/{README.md,changelog.md}`；新增 `tests/arch/umon/{mode_entry.S,mode_entry.lds,check_mode_entry.py}`；`tests/arch/{README.md,expected-divergences.yaml,umon/README.md}`；本任务书。未改 QEMU/gem5/spec/契约，未改 019 的寄存器行。
**验收结果**：① 三模式进入：U/S 同步异常分别进 cfx0/cfx2、H 进 cfx3（帧 `prev_run_mode`/`prev_cfx`/`cause`/`cause_ip`/`cause_info` 逐项）；`trap` 目标组合（U→smon、H→umon）与 `escape` 恢复（重写 `excp_cause_ip` 后回编译期固定点）通过。② `switch_run_mode`：U 体 `cg3` 读在 U 下 `CFXREG`（handler 在 hypv 跑）、S 体 `cg3` 读在 S 下 `CFXPERM`（deleg bit3 恒 1）——两处同时证明第 6 步生效。③ 两轴判权：U 下 cfx5（无 U 行）⇒ `CFXPERM|NCFXPERM = 0x8000000080`；U 下 cfx_smon（U 行已开）⇒ 可读；S 下 cfx_umon（supv 行未开）与自身 cg3（deleg）⇒ 各一次 `CFXPERM`。④ 异步 monitor-first：TIMER（U，源 cfxha 15）与 PMEM_DMA（S，源 32）各一次；屏蔽期 pending 保留、放开后投递并消费。⑤ 构建：Vast 全量 **320 s**（注入 313/313/311/320 s）、Tiny **101–105 s**，`%Error`=0；Vast sim md5 `3573aaf4…`、Tiny `545e4328…`（只作记录，ISS-453）；环境 JDK `20.0.2-internal`、conda gcc `13.2.0`、Verilator `5.020`、`RISCV` 指向组件 `.conda-env/riscv-tools`。⑥ 门控：`apply_series`/`check-source-state` chipyard clean+base+1（`HEAD=144df173`）、`check-patch-tree` chipyard 段 **0 problem**（26 patches）、`make_patch` 幂等、`check-index-blobs`/`check-tests-index`/`check-tasks` 均 rc=0。
**新发现/坑**：① `savedMon` 存了序列下标而非 cfx 编号 ⇒ `escape` 把错误 monitor 的 `global_cfx_intr_mask` 还原成 0，U 异步被永久屏蔽；改为存 `modeHa(1,0)`。② 异步投递只在 `sFreq` 检查会漏：`continueAt` 快路径直接进 `sExec`；改在 `sExec` 也检查，并把 `asyncTake` 加进写回/`wEn`/FP flags/`sc` 的闸门。③ `sFreq` 投递拍仍驱动旧 `ip` 的需求取指 A 通道（`atDemand` 与状态无关）⇒ 重定向后的取指与在飞请求复用 source 0，触发 TileLink “A channel re-used a source ID” 并卡死；改为 `jumpFlush`（清队列重取）+ 该拍关 `atDemand`/`pfWanted`。④ `frameLive` 按**入口模式** monitor 置位，而 `escape` 只清目标 cfx ⇒ U `trap cfx_smon` 返回后 umon 的异步永久阻塞；加 `savedIdx` 并在 `escape` 清入口 monitor。⑤ `finish(gewu.io.redirect.target)` 经 `entrySel` 形成组合环；拆出独立 `escapeTarget` 输出。⑥ 探针签名缓冲原先与 `.data` 同址（0x4000），`SIG_BEGIN`/槽写把 `mode_word/exp_ip/phase` 清零；移到 0x5000。⑦ 判据自检的「多一槽」用例原先写成截断到 `len+1`（等于完整流，恒真）；改为真加一槽。
**遗留问题**：① hypv 行不强制两轴判权（任务书口径「U/S 判权」；固定 BootROM 以 cfx_power 跑测试体，强制会让既有探针整体不可达）⇒ `DIV-07`。② 异步 pending 记在 monitor 的 `cg5 rc5`（§5.2 措辞），QEMU 记在源 cfx ⇒ `DIV-08`；硬件源 cfx15/cfx32 归 `m16-chipyard-021`/`022`。③ U/S 访问无 `<mode>` 行的 cfx（3/4/5/63…）fail-closed ⇒ `DIV-09`，随 021–023 的模式行落地解除。④ 019 的 `cfx02_regs` 仍只跑 hmon（hypv 不强制下继续全绿）；三模式 QEMU env 补跑归 `m16-testcases-017`。⑤ 本探针未登记 `tests/arch.yaml`（chipyard 后端仍 fail-closed，与 016/017/019 同口径）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile` 的 `modeSel/entrySel/perModeVector/perModeSwitch`、两轴判权（`targetMask/delegDenied/modeEnforced`）、异步 arbiter（pending/两级掩码/`frameLive`/ack 消费）、帧与 `escape` 的 save/restore；`WumingCore` 的 `jumpFlush`/`asyncTake`/`atDemand` 闸门、通用 `trap` 路由、CFXPERM 分支、`sExec`/`sFreq` 双边界；`WumingParams.modeEntry`；探针 14/21/14 槽、handler phase 分派、`SET_CAUSEIP` 恢复；checker 的现场派生与 self-test。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `savedMon` 存下标 ⇒ `escape` 还原错 monitor 的 global mask，U 异步被永久屏蔽（实测 global 读回 0） | ✅已修 | 存 `modeHa(1,0)`（cfx 编号） | U/S 模式全绿；global mask 读回全 1 |
| F2 异步只在 `sFreq` 检查，`continueAt` 快路径漏投递 | ✅已修 | `sExec` 也检查 + `asyncTake` 闸门（写回/`wEn`/FP flags/`sc`） | U/S 异步槽全绿；sync 路径不变 |
| F3 投递拍仍发旧 `ip` 的需求取指 ⇒ TileLink source 复用、卡死 | ✅已修 | `jumpFlush` + 该拍关 `atDemand`/`pfWanted` | 三模式无 TL 断言、无 max-cycles |
| F4 `frameLive` 入口 monitor 在 `escape` 后不清 ⇒ 后续异步阻塞 | ✅已修 | `savedIdx` + `escape` 清入口 monitor | 三模式全绿 |
| F5 `finish(redirect.target)` 组合环 | ✅已修 | 独立 `escapeTarget` 输出 | Vast/Tiny elaboration `%Error`=0 |
| F6 探针用 `escape +4` 会落进 fail 检测指令 | ✅已修 | handler 改写 `cg5 rc3` 后 `escape 0`（同固件 hmon） | 三条 resume 路径槽值正确 |
| F7 签名缓冲与 `.data` 同址，互相清零 | ✅已修 | `SIG_BUF=0x…5000`、`EXITB=0x…5800` | H/U/S 流长度与槽值正确 |
| F8 self-test 的「多一槽」用例恒真 | ✅已修 | 改为真加一槽 | 21/14/14 + 3 类变异 0 漏检 |
| F9 hypv 行不强制 / 异步 pending 在 monitor / 无模式行 cfx fail-closed | ⏸延后（口径性，登记 DIV-07/08/09） | 文档 + `expected-divergences.yaml` | 任务书「U/S 下判权」口径；后续任务解除 |

判决：F1–F8 已修并复验；F9 为任务书口径与后续任务依赖，已显式登记（非代码缺陷）。状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑**（仓库根执行运行期证据目录内的 `run.sh`，全部为本人真实输出）
- `ONLY=A,C,D,E` → `summary: PASS=35 FAIL=0`，rc=0（A 门控 13 / C 镜像 7 / D 三模式 9 / E self-test 6）。
- `ONLY=F` → `PASS=8 FAIL=0`，rc=0：11-cfx 5/5、01-load-store 38/38、逐镜像字节差 0、Tiny sim md5 `545e4328…` 批内不变。
- `--inject` → `PASS=31 FAIL=0`，rc=0：inj1 guest rc=226/oracle 1、inj2 guest rc=227/oracle 1，还原 md5 `fd76f30b…` 一致、重建回绿。
- 事后 `ONLY=A` → `PASS=13 FAIL=0`，rc=0（注入后无残留）。本人 A/C/D/E+F=43，加 B 段 10 项 = 完成区 53；G=31 与完成区一致。
- B 段按父任务口径不强制全量重建；其非重建断言现场核：Vast/Tiny sim 存在 10.2/11.4 MB（>5 MB）、md5 `3573aaf4…`/`545e4328…` 与完成区一致，工程师 4 份 elab 日志 `%Error`=0；本人 4 次强制重建 322/319/314/317 s 均 elab rc=0、verilator rc=0、`%Error`=0。

**独立注入**（`cp`+md5 备份；未用 checkout/restore/stash）
- ① hypv 强制判权（`modeEnforced` 去掉 `runMode =/= hypvMode`）：重建后 `ONLY=D` rc=**1**、`PASS=0 FAIL=9`（三模式 guest rc=134、stream 0 字节）；还原 md5 `fd76f30b…` 相等，重建后 rc=**0**、`PASS=9 FAIL=0`。
- ② 异步源 cfxha 位（`HART_HA` 15→14）：重建后 rc=**1**、`PASS=8 FAIL=1`（仅 `umon: oracle rc`）；还原 md5 相等，重建后 rc=**0**、`PASS=9 FAIL=0`。加脚本自带 2 路，共 4 路「红→还原→回绿」。

**约束核验**：独立 worktree、未提交 git；`git status` 与逐文件 md5 **前后逐行一致**，组件源树 clean、`apply_series` base+1 matches patches；改动 = 完成区声明的 9 改 + 3 新；补丁 26 条、`make_patch` 幂等 0 written、`check-patch-tree` chipyard 段 0 problem（全局 rc=2 的 10 条全在 musl，既有 KNOWN-RED）；期望现场派生自 spec/合约 + `llvm-nm` 取 `cause_ip`，非同源自比；无运行期路径、术语「寄存器组」。

**三模式/判权/异步**：同一 `mode_entry.S` TMODE=0/2/3 → 112/168/112 B（14/21/14 槽）逐槽通过；U→cfx0、S→cfx2、H→cfx3 进入路由、帧 5 字段、`switch_run_mode`（U 下 `CFXREG`、S 下 `CFXPERM`）、`trap` 目标（U→smon、H→umon）、`escape` 回编译期固定点全绿；两轴判权 self 只绕 cfx 轴、`trap` 只查 `<mode>_cfxtrap`、U/S 访问无 `<mode>` 行 fail-closed，均与 RTL 一致；异步 monitor-first（pending 取当前模式 monitor `cg5 rc5`）、TIMER 先于 PMEM_DMA、掩码按源 cfxha（15/32）、`frameLive` 防嵌套、`escape` 经 `savedIdx` 清入口 monitor 均在码中落实。

**finding**
1. **DIV-07 与规范不一致，须交用户确认**：`DADAO-12 §3.4` 明列 `hypv cfxreg cfx mask`，`§5.2（一）（五）` 对 `<mode>_cfxreg` 无 hypv 豁免，`contract-see §3`「任意运行模式执行、由来源 mask 控制」⇒ hypv 不判权是**真实偏离**。登记本身正确；但 `kind: permanent` 定性过强——根因是本 profile 固定 BootROM 以 `cfx_power` 在 hypv 交付测试体（注入①三模式全红即佐证该理由），属平台交付链差异，开放 hypv 行掩码即可解除；现有 `user_ruling` 只覆盖任务书「U/S 下判权」的范围，**不等于**对「永久偏离规范」的确认。建议改 conditional/补 `close_when` 并交用户裁定。
2. **DIV-08 方向存疑**：`DADAO-12 §5.2（三）步骤 3` 明文「置 **monitor** 的 `excp_pending`（cg5 rc5）」，RTL 与规范一致；DIV-08 却以 QEMU（记源 cfx）为对齐方向（`close_when` 写「按源 cfx 对齐」）⇒ 交架构师确认哪侧为准。DIV-09 判 temporary 合理（能力缺口，随 021–023 解除）。
3. **完成区 md5 笔误**：`GewuFile.scala` 实测与脚本记录均为 `fd76f30b…`，完成区写 `fd76f30b…`（sim md5 `3573aaf4…`/`545e4328…` 属实）。文档级，不阻断。
4. **F4（`escape` 清入口 monitor）无可达 FAIL**：现有用例不存在「escape 自非入口 monitor 后再投递异步」的路径（H 无异步、U `trap cfx_smon` 后 handler 直接 `done_ok` 不 escape）⇒ 该修复缺证据，建议补一条用例。
5. **H（hypv）异步投递未实现**：`intrArb` 要求 `modeIsCommon`，hmon 无 common face、无 `cg5 rc5` pending ⇒ hypv 下永不投递；三模式硬要求只列「异常进入/switch_run_mode/异常帧」、验收条目 3 未点名 H ⇒ 不阻断，建议随 021/022 源 cfx 一并补。

**判决：Accepted**——验收命令块在本人重跑下全部通过、硬约束无违反、注入红/绿证据完整；finding 1–2 属规范与口径差异，按边界交架构师与用户终审，不改判工程师交付。
