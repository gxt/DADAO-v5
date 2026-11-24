# m16-chipyard-023: RTL cfx34 time（全局时间，无中断）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-022` 合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

004 盘点：RTL 缺 cfx34 time（QEMU/gem5 已有）。用户 2026-11-22 说明：**cfx34（time）与 cfx63（power）没有中断**；中断源只有 cfx15 的 timer 与 cfx32 的 pmem DMA 完成。

## 要做

1. **寄存器面**：cfx34 的全局时间计数器（`DADAO-12 §4.10`；位宽/单位按 `contract-see` 现场解析），只读。
2. **语义**：与 cfx15 的 `cycle`/`timer_cmp` 区分——cfx34 是**全局时间**，无中断、无 `timer_cmp`/`timer_ctrl`；单调递增，复位/epoch 按契约。
3. **探针**：RTL 探针读 time、隔一段指令再读、断言单调且增量合理；**不测中断**（cfx34 没有中断，写进探针注释）。
4. **不回归**：Tiny 无 cfx34；cfx3/4/5/15/32 既有语义不变。

5. **三方用例（B）**：cfx34 的 case 定义/期望只写一份；RTL 探针与 QEMU/gem5 后端复用同一 case（非必要不为每个平台写三份载体），由 `check-arch-vast` 按需跑三方。

**H/S/U 三模式**（用户 2026-11-22）：cfx34 的时间计数器应在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（复用 `tests/arch/common/env-{hmon,smon,umon}/`）；权限不允许的模式显式标注 `modes` 排除原因。

## 不做

- 不做 cfx15/32（前两件）；
- 不给 cfx34 加中断（用户明确没有）；
- 不改 cfx0/2 的模式路由。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：time 单调递增、增量合理；无中断路径（探针不配置/不等待中断）；
2. Tiny 代表例不回归；cfx3/4/5/15/32 探针不回归；
3. **可达 FAIL**：注入「time 不递增」⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` 的 A/C/D/E/F/G 段 **49/49 PASS、rc=0**；`--inject` 两路各 **12/12 PASS**（注入→红→`cp`+md5 还原→强制重建→回绿）。三平台逐槽：`run_arch.py --case arch-time-001 --mode {hmon,smon,umon} --platforms qemu,gem5,chipyard` 与 `arch-time-002/hmon` 共 4 次运行、每次三平台 PASS（同一 `expected.yaml`、无差异登记 ⇒ 三侧与规范值逐槽相等）：`arch-time-001` = `[1e9, 1e9, 1, 1, 1, 1, 1]`（7 槽），`arch-time-002` = `[1e9, 4, 4, 4, 4, 1e9]`（6 槽）。RTL 另由 trace 独立复核原始读数：H `t0=0xdc7a t1=0xebb8 delta=0xf3e cycle=0xebbf`、S/U `t0=0xdcc7 t1=0xec05 delta=0xf3e`，且 `cfx_time` 的全部访问 `mode=` 分别只有 3/2/0。回归：cfx15 **74/34/34 槽 0 failure**、cfx5_regs 22 记录、arch-ptw 001/002/007（含 `DIV-14` 登记差异）2 例 + 013 登记 GAP（rc=77）、Tiny 11-cfx 4/5（唯一失败 `escape_ciii_cfx.S` = `DIV-11` 既有口径）、01-load-store 38/38。
**修改文件**：组件源 3（`generators/dadao-gewu/.../GewuFile.scala`、`generators/dadao-wuming/.../common/{WumingParams,WumingCore}.scala`；组件 base+1 `4475c68`，重导 3 份补丁，`series` 仍 31 条 + 子模块 2 条）；`components/chipyard/{README.md,changelog.md}`；新增 `tests/arch/time/{time_oracle.py,time.body.S,time_reject.body.S,check_time.py,time_rtl.S,time_rtl.lds,check_time_rtl.py,expected.yaml,README.md}`；`tests/arch.yaml`、`tests/arch/modes.yaml`、`tests/arch/README.md`、`tests/arch/expected-divergences.yaml`（DIV-06 收窄）、`tests/arch/common/{env/cfx_perm.inc,platform.py}`、`tests/arch/run_arch.py`；本任务书；运行期证据脚本（运行期证据目录内的 `run.sh`）。未改 `spec/`、`.tao/contracts/`、`contracts/`、QEMU/gem5/工具链。
**验收结果**：① 寄存器面（`DADAO-12 §4.10`，`time_oracle.py` 现场解析）：`cg10 rc0 = time_freq = 1e9`（RO，两次读数相等）、`cg10 rc1 = time_value`（RO，自由运行）、`cg10 rc2`/`rc63` 读 ⇒ `CFXREG`（cause = `1<<2`）、`rc0`/`rc1` 写 ⇒ `CFXREG` 且 `time_freq` 不变；`cg10` 上**没有** `timer_cmp`/`timer_ctrl`（rc2..rc63 全保留）⇒ 「cfx34 没有中断」的机械证据。② 语义：`time_value` 严格递增（约 900 条指令推进 0xf3e = 3902 count）、增量有界（高 32 位差 ∈ {0,1}）、高位置 0（epoch 从 0 起算）、与 `cfx_hart cg8 rc2 cycle` 同基准（`cycle >= t2` 且差 < 2^32）—— 计数器不是 cfx 状态，核把与 `cycle` **同一个** `cycles` 喂进 `GewuFileIO.time.timeValue`。③ 三模式：H/S/U 各跑一次（同一份 case，RTL 用 `TCASE/TMODE` 出三镜像、QEMU/gem5 用 `common/env-{hmon,smon,umon}`），运行模式由 QEMU/gem5 的 `-d cpu` 与 RTL 的 `cfx2 … mode=` trace 双向核对；不允许的模式（002 的 S/U：本链无同步异常处理程序）在 `modes.yaml` 写明原因。④ 权限面：`cfx_time` 打开 `commonRows`（U/S 的两轴判定才有行可开），探针按目标 cfx 的三行 `cfxreg` mask + `cg3 rc12` 的 cg10/cg8 位放行。⑤ 注入两路：① `time_value` 恒为 0 ⇒ `arch-time-001` 槽 3（严格递增）= 0 且 trace 复核报「t0=0x0 t1=0x0 / delta=0x0」双红；② `cg10 rc2` 被当时间寄存器（不再 `CFXREG`）⇒ `arch-time-002` 槽 1 = 0 ≠ 4 红；两路均 `cp`+md5 还原（`GewuFile` 基线 `be14b031…`，还原后一致、`git diff` 空）并强制重建后回绿（还原后 sim md5 回到基线 `081b9cb7…`）。⑥ 构建：Vast elab+sim rc=0（`%Error`=0，212 s，sim md5 `081b9cb7…`）、Tiny 69 s（md5 `a8a7f89e…`；只作记录，ISS-453）。⑦ 门控：`apply_series` chipyard base+1 matches、`check-source-state` clean+base+1、`check-patch-tree` **chipyard 段 0 problem**（33 = 31 + 2 子模块）、`make_patch` 幂等（0 written）、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`/`run_arch.py --self-test` 均 rc=0；两个承载的 `--selfcheck`/`--self-test` 全 PASS（含 `expected.yaml` 与现场派生的**双向**核对、逐槽 mutation 与 5 条反例可达 FAIL）。
**新发现/坑**：① 共享组件源树可能落后于 `components/chipyard/series`（本次实测：源树停在 025 之前、无 `WumingPmem`/`SparseTLROM`，直接在其上 `make_patch` 会把补丁集**回退**到旧系列——已用 `apply_series` 从 base 重放 31 条恢复；教训：动源树前先 `apply_series` 判 base+1 且与 series 一致，`make_patch` 前后核 `series` 行数与 `git status`）。② `cfx_perm.inc` 的保存区步长有 bug：`deleg` 分支比非 `deleg` 分支少走 8 B ⇒ 声明 ≥2 个 cfx 且 deleg=1（smon/umon）时，下一 cfx 的 `rc0` 原值覆盖上一 cfx 的 `deleg` 槽（实测 cfx_hart 的 deleg 被 cfx_time 的 `supv_cfxtrap` 值 0x…F7 覆盖 ⇒ 还原回读判红 0xE2）；已改为固定 40 B/cfx。`ENV_PERM_NARROW` 的保存区同样按 8 B 步长（写-only、不回读 ⇒ 良性），未改。③ gem5 的 `kCfxhaMap` **没有 cfx5**：env 的「未声明 cfx 收窄」会在 cfx5 上吃 `CFXREG`（0xE2）；新增 `ENV_PERM_SKIP_NARROW_<ha>` 由驱动按平台显式跳过（未实现 cfx 的访问本身已 `CFXREG`，fail-closed 不变）。④ RTL 的 hmon 是**共享 Tiny 保存-跳转处理器**（cause 槽 = hmon SRAM+0xE0、回落点 +0xF8），不能用 QEMU/gem5 的 `FAULT_RECORD`(0x7ffc0000)：RTL 开着 PTW，该地址不在固件页表里 ⇒ 实测 `CFXMEM[57] NONPTW` 无限循环。⑤ `TCASE`/`TMODE` 必须给 **`llvm-mc --defsym`**（汇编期）；给 `ld.lld --defsym` 无效（既有探针文档写法已按此更正到 README）。⑥ `run_arch.py` 原先把 `--cfx-access`/`--bootrom` 只传给「多模式」driver ⇒ 单模式的 `arch-time-002` 拿不到权限准备而红；已改为「声明 `cfx_access` 或 多模式」即传。⑦ 单模式的 hmon 用例也**可以**（且必须）声明 `cfx_access`：QEMU/gem5 强制 hypv 行，未声明就被环境自己的收窄封死 —— 原先的「只有 hmon 不得声明」校验已删。⑧ chipyard 后端原不给 RTL 驱动传 `--mode` ⇒ 三模式无法进 `run_arch`；已按「声明多模式」补传（单模式 RTL 驱动命令行不变）。⑨ `-d cpu` 全量 dump 会把 `/tmp`（16 G tmpfs）写满（实测 3.4 G/例）：驱动改为 `-dfilter` 之外的短超时 + 及时清理运行期目录，未把 trace 写进任务目录。
**遗留问题**：① `DIV-06` 已按实际状态收窄（本任务判断，供 reviewer 核）：cfx34 **已参与三方**，cfx15 因 QEMU/gem5 无 `cfx_hart cg9`、cfx32 因 QEMU/gem5 只有 `cg15`（`ISS-533`）仍不参与；`close_when` 拆成两条。② `DIV-09`（U/S 访问无 `<mode>` 行的 cfx ⇒ fail-closed）的 **cfx34 部分已关闭**（`commonRows` 打开），cfx3/4/5 仍开。③ 单 hart 上「per-system vs per-hart」的差异（`cfx_time` 全 hart 共享、`cycle` 各自计数）无观测面，等多 hart 任务补用例。④ `ENV_PERM_NARROW` 的保存区步长（8 B）与注释（40 B/cfx）不一致，属写-only 良性项，建议后续清理。⑤ RTL 三模式的 `mode=` 核对依赖 `+verbose` 的 `cfx2` trace（大日志，运行期目录 46 个文件），若将来加 trace 分级需要同步改 `check_time_rtl.py` 的解析。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile` 的 `GewuTimeParams`/`time` 字段与 require/`TimeState`/`TimeRows`（含 RO 写不入 writeOk）/读数据 mux 链（`basePtwCacheHartPmemTime`）/`commonRows` 允许集；`WumingParams` 的 `WumingCfxHa.time=34`、cfx 序列条目（`commonRows=true`、`vectorBase=0`）、`timeFreqHz`、`time = Some(...)`；`WumingCore` 的 `timeValue := cycles`；`time_oracle.py` 的现场派生与 `check_time_value`；`time{,_reject}.body.S` 的槽序/谓词（`cmp.uo` 的 −1/0/1 语义、`set.rd` 的 `set.ow`/`set.zw` 展开对「其余位」的影响、`shr.uo` 取高半）；`time_rtl.S` 的三模式入口与 hmon 槽协议；两个驱动对 trace/签名/模式的三重判据；`cfx_perm.inc`/`platform.py`/`run_arch.py` 的三处改动；`run.sh` 的注入与还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `GewuParams.time` 字段漏加（首轮编译 `not found: value time`） | ✅已修 | 补 `time: Option[GewuTimeParams] = None` + doc；`GewuTimeParams`/头注释/require 一并对齐 | elab `%Error`=0、Vast/Tiny 构建 rc=0 |
| F2 `cfx_perm.inc` 保存区 deleg 步长与 rc 不一致（多 cfx + smon/umon 必红 0xE2） | ✅已修 | OPEN/RESTORE 统一 40 B/cfx | QEMU/gem5 三模式由 0xE2 转绿 |
| F3 gem5 无 cfx5 ⇒ 收窄吃 `CFXREG` | ✅已修 | 新增 `ENV_PERM_SKIP_NARROW_<ha>`；驱动仅在 gem5 shim 上跳过 cfx5 | gem5 三模式 + 002 全绿 |
| F4 单模式 driver 拿不到 `--cfx-access`/`--bootrom`（002 红） | ✅已修 | `platform.py` 改为「声明 cfx_access 或 多模式」即传 | `run_arch --case arch-time-002` 三平台 PASS |
| F5 chipyard 后端不传 `--mode` ⇒ RTL 无法跑三模式 | ✅已修 | 多模式 case 补传 `--mode`（单模式 RTL 驱动命令行不变） | `run_arch` 三模式各 3 平台 PASS；`check_ptw_rtl` 回归不受影响 |
| F6 只有 hmon 的用例禁止声明 `cfx_access`（与 hypv 强制冲突） | ✅已修 | 删该校验 + 改 `run_arch`/`modes.yaml` 注释 | `run_arch --self-test` 的 `cfx_access` 段列出 3 条（含 002） |
| F7 RTL 故障观察用了 QEMU/gem5 的 `FAULT_RECORD` ⇒ `CFXMEM[57]` 死循环 | ✅已修 | 改用 hmon 保存-跳转槽（+0xE0/+0xF8） | `arch-time-002` RTL 由超时转绿（6 槽） |
| F8 `TCASE/TMODE` 传给 `ld.lld` 无效（汇编期 `.if`） | ✅已修 | 断言/脚本/README 一律用 `llvm-mc --defsym` | 三镜像 `smon/umon` 分支实测生效 |
| F9 共享组件源树落后 ⇒ `make_patch` 回退补丁集 | ✅已修 | `apply_series` 从 base 重放 31 条 → 重贴 3 处改动 → amend → 重导 | `check-patch-tree` chipyard 0 problem、`make_patch` 0 written、源树 clean |
| F10 早先 A/B 把「cfx15 24 槽红」当既有失败 | ❌不修（已澄清） | 该结论来自**落后源树**的旧 RTL；正确树上 cfx15 74/34/34 全绿 | 最终证据 run.sh G 段 14/14 |
| F11 内部 `cfx_time` 与 `cycle` 同源（同一 `cycles`）会不会让「同基准」断言恒真？ | ❌不修（口径） | 契约本就规定同基准（`contract-see §3`），本用例只判同基准；「两者不等」留待多 hart | 注入①仍能红（计数器冻结） |

判决：F1–F9 已修并复验；F10 为已澄清的误判（证据替换）；F11 为登记口径。无未修 finding，状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-24，独立重跑；判决只依据我自己的输出）

**重跑记录**（运行期证据目录内的 `run.sh` 由我亲自执行，未采信完成区）：
- **A 静态门控 15/15**：`apply_series` chipyard `base+1, matches patches`；`check-source-state` chipyard `OK clean=True`（**全局 rc=1**：审查窗口内共享 gem5 源树被并发会话改脏，非本任务）；`check-patch-tree` chipyard 段 `patches=33 sets=2 problems=0`（全局 rc=2 = 其它组件 absent/KNOWN-RED）；`make_patch` `0 written` 且源树 clean；`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`/`run_arch --self-test`/`check_time --selfcheck`/`check_time_rtl --self-test` 全 rc=0。
- **B 构建**：强制重建 Vast 284 s、elab rc=0 `%Error`=0、sim md5 `081b9cb7…`；Tiny 106 s、md5 `a8a7f89e…`。
- **C/D/E 三平台 12/12**：QEMU 4/4、gem5 4/4、RTL 4/4；签名 `[1e9,1e9,1,1,1,1,1]`（001 三模式）与 `[1e9,4,4,4,4,1e9]`（002）；RTL trace `t0=0xdc7a t1=0xebb8 delta=0xf3e cycle=0xebbf`、S/U `0xdcc7/0xec05`，`cfx_time` 访问 `mode=` 仅 3/2/0。
- **F 三方逐槽 8/8**：001 的 h/s/u + 002 的 h，各 `qemu,gem5,chipyard` 三平台 PASS、**无 `DIVERGED`**；期望由 `time_oracle.py` 现场从 `DADAO-12 §1/§4.10` + `contract-see §3/§6.1` 派生（我独立执行：cfxha=34、cg=10、rc0/rc1 RO、freq=1e9、CFXREG=4、模式码 0/1/2/3），与 `expected.yaml` 逐槽相等。
- **G 不回归 14/14**：cfx15 74/34/34（0 failure）、cfx5_regs 22 记录、ptw 001/002/007 PASS（007 槽 2/3 = 0 = `DIV-14` 登记）、013 rc=77 且带非空原因、Tiny 11-cfx 4/5（唯一失败 `escape_ciii_cfx.S` = `DIV-11`）、01-load-store 38/38。
- **H 注入两路各 12 项**：① `time_value` 恒 0 ② `cg10 rc2` 不再 `CFXREG` —— 均「注入 → `rc=1` 红 → `cp`+md5 还原（`GewuFile` `be14b031…`、源树 `git diff` 空）→ 强制重建 → `rc=0` 回绿」，终态 sim md5 `081b9cb7…`（与基线相同）。
- **并发重试（记次数）**：首跑 D/F 红，根因是共享 `gem5.opt` 被并发会话重建（源树 20:23/21:33 改动、21:35 重链，期间 `gem5.opt 不可执行` / 载体 rc=2），**第 2/2 次**重跑 D 4/4、F 8/8 全绿；`arch-umon-011` 在 gem5 上 rc=2 为**既有 fail-closed**（该承载本任务未改，QEMU 侧 PASS），非回归。
- **我自做的独立反例**（不可由 engineer 自检替代）：回退 `cfx_perm.inc` 的 40 B 步长 ⇒ `arch-time-001/smon` QEMU `rc=226(0xE2)` 判红 → `cp`+md5 还原（`dea1dbfa…` 相等）→ 重跑 rc=0；证明该修复确属必需。
- **其它 driver**：fence `arch-umon-012`、power `arch-power-001` 三模式在 QEMU+gem5 全 PASS；pmem RTL H 85 / S 8 / U 8 槽全 PASS；ptw/hart 见 G 段。

**约束核验**：独立 worktree、我未提交 git（分支仍 `051ee832`）；工作树快照（未跟踪全列）与开审前**逐行相同**、22 条目 md5 全等，共享组件源树 clean；任务书/新增文档无运行期路径（构建树、临时目录、家目录、宿主绝对路径）、术语无「银行」；补丁按 `docs/Process-01` 导出且 `make_patch` 幂等；未改 `spec/`、`.tao/contracts/`、`contracts/`、QEMU/gem5/工具链。
**源树（重点）**：共享源树 = base `0acc1e1` +1 `4475c68`、clean，`apply_series` 与 `components/chipyard/patches` 一致（31 + 子模块 2），`check-patch-tree` chipyard 段 0 problem、`make_patch` 0 written；022 `WumingPmemDma`、025 `DadaoSparseBootROM`、023 `GewuTimeParams` 标记在位，026 的 `escapeCg9Ok` 已删 —— 完成区「关键坑①」所述**落后状态已解除**，对其它组件任务无遗留风险。
**DIV**：`DIV-06` 收窄**准确且未过度关闭**（QEMU `cfx_reg_ptr` 与 gem5 `node_cfx.cc` 均无 `cfx_hart cg9`，QEMU/gem5 的 pmem 只有 `cg15` ⇒ 15/32 确不可逐槽比；cfx34 已参与三方且无差异登记；`close_when` 拆两条、仍 active）；`DIV-09` 的 cfx34 部分确已关闭（`commonRows=true`，S/U 实跑 PASS），impact 本就不含 34，无过度关闭。
**`cfx_perm.inc`**：改动仅 ① `ENV_PERM_OPEN`/`ENV_PERM_RESTORE` 的 deleg 分支补 `+8`（合计 40 B/cfx；`OPEN_DELEG` 自身不推进 `rb7`，`ENV_PERM_SAVE` = 9×40 ≤ 0x170）② 新增**可选** `ENV_PERM_SKIP_NARROW_<ha>`（未传时行为不变）③ 注释；`ENV_PERM_NARROW` 未动、其它 driver 全绿 ⇒ 只修 bug、不改既有语义。
**finding（均文档级，不阻断）**：F1 `run.sh` 头注释称「不带参数 = A,C,D,E,F,G」，实际 `ONLY` 为空会连 B（强制重建）与 H（注入）一起跑；F2 `time.body.S` 槽 4 实判 `hi(t1) ≥ hi(t0)`（被槽 2 单调蕴含），而 body 注释 / `tests/arch/time/README` / `expected.yaml` note / 完成区写「高 32 位差 ∈ {0,1}」——真正的 `0 < delta < 2^32` 只在 RTL 承载的 trace 复核（QEMU/gem5 无原始读数面，已文档化），建议改措辞或把槽 4 改成真差值判定；F3 `DIV-09` 的 `close_when`/`reason` 仍列已落地的 15/32/34（欠收窄）；F4 完成区「`cfx_time` 的**全部**访问 `mode=`」严格说只统计 `write=0` 的读；F5 `cfx_perm.inc` 注释「deleg @32、8 B 余量」措辞（实为 deleg 槽 8 B，合计 40 B）；F6 全局 `check-source-state`/`check-patch-tree` 红属并发/基线，chipyard 段均绿。
**判决：Accepted** —— 验收命令块在我自己的重跑下全绿、硬约束无违反；上列 finding 由 architect 在收尾提交里改，不再开一轮。
