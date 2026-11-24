# m16-chipyard-024: RTL 异步模型修订（cg9 七槽 + 掩码归 monitor + 源位图）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m18-spec-004`（spec/契约落地）合入；`m16-chipyard-021` 已合入（在其 cg9 上改）
**可并行分片**：否（同改 `components/chipyard`）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

`ADR-0061` 修订异步模型：来源掩码归 monitor、源身份统一 cfxha、`cg9` 精简 7 槽、两个位图软件只读、帧由 `escape` 结束。`m16-chipyard-021` 已实现 `cg8` + 16 槽 `cg9`（含 5 个掩码、cause id 17、`saved_global_intr_mask`），本任务把它改到新模型。

## 要做

1. **`cg9` 改 7 槽**（`DADAO-12 §4.7`）：
   - `rc0 prev_run_mode`、`rc1 prev_cfx`、`rc2 cause_ip`（= 提交后的 `rb0`）、`rc3 src_frame`（64b，**HW/RO**，位 = 源 cfxha，非 0 = 有效帧）、`rc4 src_pending`（64b，**HW/RO**，位 = 源 cfxha）、`rc5 excp_vector`、`rc6 switch_run_mode`（固定 supv=2）；`rc7–15` reserved ⇒ `CFXREG`。
   - 删除原 `rc3 cause_id` 的 17/18 语义、`rc4 saved_global_intr_mask`、`rc8–rc12` 五个掩码。
   - 读写属性按 `m18-spec-004` 落地结果：`src_frame`/`src_pending` 为 **HW/RO，软件写忽略、读回不变、不产生异常**（与 cycle/insn 的"写 ⇒ `CFXREG`"不同）。
2. **来源掩码移 monitor**：`cfx0`/`cfx1`/`cfx2`/`cfx3` 的 `cg8 rc1` 实现为"本运行模式异步来源掩码"（位 = 源 cfxha，复位全 1，`0=允许`/`1=屏蔽`）；投递时按 `inner_run_mode` 选行求值。删除 `cfx_hart` 侧掩码相关逻辑。
3. **仲裁**：同一指令边界把**所有** `pending && !masked` 的源一次性投进一帧：`src_frame` = 这些位的并集、`src_pending` 扣除这些位、`excp_async_num` +1；`src_frame != 0` 时新事件只置 pending（无嵌套）；**不要**逐源循环投递。
4. **pending 跟随源事件**：投递即清位；源被 ack（`timer_cmp` 重装 / `dma_status` W1C）后 pending 自动落；软件不写。
5. **`escape`**：保留 `imms18[1]` 帧选择位与 `{0,1,2}`/`3⇒ILLI`；`cg9` 帧有效 = `src_frame != 0`；合法返回时清 `src_frame`（释放），不改 `escape` 编码。
6. **探针**：`tests/arch/hart/cfx15.S` + `check_cfx15.py` 改到新模型（掩码写 hmon/smon/umon 的 `cg8 rc1` 放行 bit15、7 槽逐项、`src_pending`/`src_frame` 只读、ack 后 pending 落）；H/S/U 三模式。
7. **不回归**：Tiny 无 cfx15 不变；cfx3/4/5 既有语义与 020 的两轴判权不变。

## 不做

- 不做 cfx32/34（022/023）；
- 不改 `escape` 编码与工具链；
- 不改 QEMU/KERNEL/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；**失败路径短 timeout、禁长时间 `-d cpu` dump**（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cg9` 7 槽读写/保留（`rc7–15` ⇒ `CFXREG`）；`src_frame`/`src_pending` 只读行为符合 spec；
2. hmon/smon/umon 三模式各写自己的 `cg8 rc1` 放行 bit15 ⇒ TIMER 投 `cfx_hart`/supv；屏蔽 ⇒ 只置 pending、解除后投递；
3. `src_frame` 位 = 源 cfxha（15）、pending 同索引；ack 源（重装 `timer_cmp`）后 pending 落；
4. `escape imms18=2` 返回并释放；`3`/`[17:2]≠0` ⇒ `ILLI`；
5. **可达 FAIL ≥2**：注入"掩码留在 cfx_hart"或"pending 位记 17" ⇒ 红；`cp`+md5 还原并强制重建回绿；
6. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`：A 14/14、B 10/10、C 7/7、D 9/9、E 31/31（合计 **71/71，rc=0**）；`--inject` F **29/29，rc=0**（两路注入均红、`cp`+md5 还原并强制重建后回绿）。三模式（同一份 `cfx15.S`，汇编期 `TMODE=3/2/0`）：H **56 槽**、U/S 各 **16 槽**逐槽等于现场从 `spec/DADAO-12` §1/§3.1–§3.4/§4.1–§4.7/§5.1/§5.4、`ADR-0061`、`contract-see` §3/§6.1 与 `contracts/opcodes.yaml` 派生的期望；`cfx02_regs` 47 条、`cfx5_regs` 22 条在末版 Vast 上全绿；`mode_entry` 14/14/7 绿；Tiny `11-cfx` 5/5、`01-load-store` 38/38 与 020 的 pre-024 基线逐镜像字节相同。返工后另跑：`check_mode_env.py --selfcheck` **rc=0**（7 项 PASS）、`check_power.py --selfcheck` **rc=0**（13 项 PASS）、`run_arch.py --self-test` **rc=0（12 项全 PASS）**。
**修改文件**：组件源 3（`generators/dadao-gewu/.../GewuFile.scala`、`generators/dadao-wuming/.../common/{WumingCore,WumingParams}.scala`；base+1 `f7415b7`，重导 3 份补丁，`series` 仍 26 条）；`components/chipyard/{README.md,changelog.md}`；`tests/arch/hart/{cfx15.S,check_cfx15.py,README.md}`；`tests/arch/umon/{cfx02_regs.S,check_cfx02_regs.py,mode_entry.S,check_mode_entry.py,README.md}`；`tests/arch/common/check_mode_env.py`（返工：旧句 → 现行 `cg8 rc1` 异步掩码句）；`tests/arch/power/power_vast.py`（**越界披露**：`space_bits()` 用 `### 3.9` 当 §3.8 的结束标记，`m18-spec-004` 删掉 §3.9 后 `end < 0` ⇒ `SetupError`；改为下一章 `^## 4\.` 起点，1 行，现场解析风格不变）；`tests/arch/{README.md,expected-divergences.yaml}`；本任务书；运行期证据脚本（运行期证据目录内的 `run.sh`）。未改 spec/contracts/QEMU/gem5/工具链。
**验收结果**：① cg9 七槽：rc0/rc1/rc2 写全 1 读回 3/63/`0xFFFFFFFFFFFC`（48b、低 2 位 0）、rc3/rc4 写 PATTERN 读回 **0**（HW/RO、不报异常）、rc5 读回对齐、rc6 写 0 读回 2；rc7/rc8（原掩码）/rc15 ⇒ `CFXREG`（cause/指令编码/见证三槽）；cfx_hart 自身 `cg8 rc1` 仍 reserved。② 掩码：hmon/umon/smon 的 `cg8 rc1` 复位全 1、写放行 bit15（cfx3 因此新增该行；cfx3/4/5 其余行与 020 两轴判权未动）；**只屏蔽当前模式那一行** ⇒ 只置 pending（`0x8000`）不投递，放开后下一指令边界补投；另两行放行不生效（投递按运行模式取行）。③ 投递：`src_frame`/`src_pending` 位 = 源 cfxha **15**；投递后 pending = 0、`excp_async_num` = 1（一帧 +1）、prev_mode/prev_cfx = H 3/3、U 0/0、S 2/2；帧活动期再武装只置 pending（无嵌套）；重装 `timer_cmp` 后 pending = 0（源 ack）。④ `escape cfx_hart, [excp_cause_ip, 8]`（汇编层 imms20 = 8）返回并清 `src_frame`；hmon 行掩码保持放开值（不随 escape 保存/恢复）；`imms18 = 3` / `[17:2] ≠ 0` ⇒ `ILLI`。⑤ 注入①「投递不看当前运行模式 monitor 的 mask」⇒ U 探针红（masked 槽 0x0、witness 错位）；注入②「pending 位仍记旧宏 cause 17」⇒ 红（`0x20000`）。两路均 md5 `e4a14b2a…` 前后一致后强制重建回绿。⑥ 构建：Vast 全量 318 s（注入轮 294–300 s）、Tiny 99 s，elab/verilator rc=0、`%Error`=0；末版 sim md5 Vast `770213e5…`、Tiny `a97fea2d…`（只作记录，ISS-453）；环境 JDK `20.0.2-internal`、Verilator `5.020`。⑦ 门控：chipyard base+1 干净（`f7415b7`）、`check-patch-tree` chipyard 段 **0 problem**（26 patches）；**全局 22 problem = qemu 6 / gem5 4 / linux 2 / musl 10**，全部为 assertion ⑥/⑨「共享源树与补丁集不一致」且分布在本任务 diff **未触及**的 4 个组件（属既有基线红，`ISS-507` 只登记了 musl/gem5 子集）；`make_patch` 幂等（0 written）、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue` 均 rc=0。⑧ `mode_entry`（020 同步段）三模式仍全绿（槽 14/14/7），**DIV-10 条目已删除**；DIV-11 按实际状态改写（见遗留③），DIV-15 条目已删除。⑨ **§5.4(四) 精确点的静态门控（返工订正）**：`asyncTake = sExec && intr.valid` 是 `sExec` 分支**首条**，其后全为 `.elsewhen`（jump/`call`/`ret`/RAS/br/`escape`/cfx2/`lr`-`sc`/`ld`-`st`/`sTrap`/`sSlow`）；`execW0`/`w1En`/`scFailExec`/`fflags`/`gewu.io.wEn` 均含 `!asyncTake`；其余 `w0En` 分支只在 `sSlow`/`sCopy`/`sCls`/`sSemi`/`sMwait`/`sFpSlow`；多周期指令离开 `sExec` 后 `asyncTake` 恒 0。⇒ **取中断发生在指令 i 执行前、i 零架构副作用（store 未发出）**；`rb0` 读 `io.ip`，投递当拍 `ip` = 上一条提交后写入的下一指令地址 = `cause_ip`，`escape` 返回同一地址 ⇒ i **首次执行（非重放）**，与 `§5.4(四)`「cause_ip = 提交后的 rb0、不重放」一致。⑩ 返工复跑：`ONLY=A` rc=0（14/14）、`ONLY=C,D` rc=0（16/16）、`--inject` rc=0（29/29）；未改 RTL/探针源码，故不重建（`git -C .work/source/chipyard status` 干净、三文件 md5 与上轮一致）。⑪ **越界修复披露**：`tests/arch/power/power_vast.py:182` 的 `space_bits()` 以 `### 3.9` 作为 §3.8 小节的结束标记；`m18-spec-004` 已把 §3.9（cg9）整节删除并移入 §4.7 ⇒ `end < 0` 抛 `SetupError("spec/DADAO-12 §3.8 未找到")`（§3.8 本身与 `cg7 **全部只读**` 句仍在 L464/474）。改为下一章起点 `^## 4\.`（与 `### 3.8` 起点同为现场解析）；全仓仅此一处依赖 `### 3.9`（已 grep）。修后 `check_power --selfcheck` rc=0（cg7 位表 `{exists..OTHER, R,W,X,cacheable,shareable,volatile}`、`cfx_power` 块 0 `desc=0x5/start=0x3ff_ffc0_0000/size=0x400000/attr=0x5`、两组 expected 槽 28/3 均现场命中），`run_arch --self-test` **rc=0（12 PASS / 0 FAIL）**。
**新发现/坑**：① `src_frame`/`src_pending` 的"写忽略不报异常"必须留在 `writeOk` 集合里、只是不写状态；从 anyWrite 移除就变成 `CFXREG`（与 §4.7 冲突）。② `timer_cmp` 重写既是新 arming 又是源 ack：`timerSeen` 的清零必须与 pending 的清除在同一处写，否则无条件 `timerSeen := timerCond` 会覆盖 ack（实测踩到）。③ Tiny 保留旧寄存器面（`cg3 rc4` RW；`cg0`–`cg2 rc4` 与 cfx0–3 的 `cg8 rc1` 仍 `CFXREG`）是**有意**：`11-cfx/cfx2rc` 仍断言 `cg3 rc4` RW，改它属 testcases 域；异步模型整体由 `gp.hart` 门控（实测 Tiny 字节不变）。④ 工具链已支持 `escape …, 8`（imms20=8）并拒绝 12，`cfx15.S` 改用助记符。⑤ `m18-spec-004` 删 §3.9 造成的解析断链（本任务越界修复，1 行）：`tests/arch/power/power_vast.py` 以小节号 `### 3.9` 作 §3.8 的结束标记 ⇒ 删除后 `SetupError`；教训＝章节区段一律用「下一章 `^## <k>\.` 起点」作边界，勿依赖后续小节号存在。⑥ 共享源树旧态（`ISS-520` 类）：`.work/source/qemu` 仍是 pre-`m18-qemu-005` 内容（`cfx_mode_reg case4 → cfx_intr_mask`、`global_cfx_intr_mask`），而本仓补丁已有 `async_intr_mask` ⇒ `check-patch-tree` 的 qemu 6 条 ⑥/⑨ 由此而来；三方比对前需 `make fetch`/重放该组件补丁。
**遗留问题**：① 单源机器（只有 TIMER）上"一帧多源"的并集不可端到端观测；仲裁按位一次成型（无逐源循环），PMEM_DMA 由 `m16-chipyard-022` 接入同一 case 后观测。② 边界非幂等用例（`call`/`ret`/store 到期后返回）未加：精确点由 ⑨ 的静态门控覆盖，建议 022 接 PMEM_DMA 时补一条端到端用例。③ `DIV-11`：Tiny 侧 `WumingDecoder` 的 `withHart` 门控与「Tiny 按 §5.1 接受 `imms18 = 2`（无 cg9 帧 ⇒ `CFXESC`）」的编码用例未做（testcases/核心域）。④ 三方口径：Tiny/共享源树的 QEMU 侧寄存器面与 `ADR-0061` 对齐（`m18-qemu-005` 补丁已合并，源树待重放）属实现进度，不在本任务范围。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile.scala` 的 cg9 七槽（Reg 定义/行译码/读 mux/写块/保留 rc）、`intrMaskOpt`/`asyncIntrMaskOpt` 双形态、`isAsyncMask` 行、`maskData` 与 `commonRdata` 的 rc4 收口、异步投递（`timerCond`/`timerEvent`/`timerGate`/`asyncMaskByMode`/`asyncAllowed`/pending 更新/ack）、入口（`asyncSrcFrame := asyncAllowed`、`cause_ip` 对齐）、`escape`（`srcFrame != 0` 判据、释放、无掩码恢复）、计数（`excp_async_num`）；`WumingCore`/`WumingParams` 注释；探针七槽/掩码三行/补投/无嵌套/ack/释放/ILLI；两个 checker 的现场派生与 self-test；`mode_entry` 的异步段删除；DIV-10/11 与三份 README。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `commonRdata` 仍按 5 元素访问 `r.mask(e.mode)(4)`，4 元素 Vec 在展开期越界 | ✅已修 | 删内层 rc4 Mux，`rcIdx` 收到 `<= 3`；`isMask` 上限按 `asyncModel` 分档 | Vast elab rc=0；cfx02 47 条绿 |
| F2 无条件的 `timerSeen := timerCond` 会覆盖写块里的 ack 清零 ⇒ 重写 `timer_cmp` 后不再产生新事件 | ✅已修 | 改为 `when(timerAck) false .otherwise(timerCond)` | 探针 handler 的"再武装→pending 0x8000"槽绿 |
| F3 `intrMaskOpt.get` / `asyncIntrMaskOpt.get` 在另一档为 `None` 时仍会被 Scala 求值 | ✅已修 | 用 `if (asyncModel)` 分支 + 独立 `for (m <- asyncIntrMaskOpt)` 写块 | Tiny/Vast 双档 elab rc=0 |
| F4 放开掩码后紧接的 witness REC 会被补投抢走槽序 | ✅已修 | witness 前移到放开掩码**之前**（U/S） | umon/smon 16 槽全绿 |
| F5 S 模式下访问自身 `cg8`/`cg9` 受 `cg3 rc12` deleg bit8/9 约束，未放开会 CFXPERM | ✅已修 | `setup_s` 在 hypv 期先写 `cfx_smon cg3 rc12` | smon 16 槽全绿 |
| F6 证据脚本初版：E 段日志目录未建、`qemu`/`llvm-mc` 指向任务 worktree（不存在） | ✅已修 | 先 `mkdir -p`；`--qemu` 用 `$TOOL`；`.dadao` 整目录链到主仓库 | E 22/22 绿（含 Tiny 两册） |
| F7 `escape ..., 8` 的汇编缺口已由工具链闭合，仍用原始 `.dd.t32` 会漏编 | ✅已修 | 合法返回改用助记符；非法 3/4 仍用原始编码字；checker 增合法集断言 | `llvm-mc` rc=0；`escape ..., 12` 被拒（rc=1） |
| F8 Tiny 旧寄存器面是否该一并改 | ❌不修（有意保留，见"新发现/坑"③） | `intrMaskOpt` 仅在无 `cfx_hart` 的机器存在 | Tiny `11-cfx`/`01-load-store` 字节不变 |
| F9 `sExec` 边界投递会重放当前指令（与 §5.4(四) 字面不符） | ⏸延后（记入"遗留问题"②，属核心精化） | 未改（本任务不动核心时序） | 探针 cause_ip 落在等待循环区间 |

判决：F1–F7 已修并复验；F8 为有意的范围选择（附证据）；F9 为口径性缺口已显式登记。状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-23，全部本人重跑，不采信完成区）

**重跑记录**（仓库根执行运行期证据目录内的 `run.sh`，参数见各条；输出/退出码均为本人终端实测）：
- `ONLY=A` → **rc=0，14/14**：apply base+1、`check-patch-tree` chipyard 段 0 problem/26 patches、`make_patch` 幂等 0 written、index-blobs/tests-index/tasks/changelog/no-residue rc=0；**全局 `22 problem(s)`（qemu 6 / gem5 4 / linux 2 / musl 10），完成区写「全局 16 条全在 gem5/linux/musl」不符 ⇒ F4**。
- `ONLY=C,D` → **rc=0，16/16**：三镜像期望 56/16/16；H/U/S guest rc=0、stream 448/128/128 B、oracle rc=0。
- `ONLY=E` 第 1 次 → **rc=1，28/31**：`run_inst_tiny` 抛 `OSError: [Errno 28] No space left on device`（两镜像 0 B、输出少 1 个）＝**环境故障，非交付物**；第 2 次（重试 **1/3**，`df` 可用 16 G）→ **rc=0，31/31**（三个 checker self-test「未检出变异」=0、cfx02/cfx5 绿、mode_entry 14/14/7、`11-cfx` 5/5 与 020 基线逐镜像字节同、`01-load-store` 38/38）。
- `--inject` → **rc=0，29/29**：inj1「投递不看 monitor 掩码」红（`oracle rc=1`，slot00 期望 0x8000 实得 0x0）、inj2「pending 位记 17」红（0x20000）；两路 `cp` 备份 md5 `e4a14b2a…` 与源一致、还原后强制重建 rc=0、`stream == reference` 回绿。B 段未整跑（按指示优先静态+已有日志）：F 内 4 次强制重建 elab/verilator rc=0、`%Error`=0，末版 Vast `770213e5…`、Tiny `a97fea2d…`，与完成区一致。

**约束核验**：组件源树 `git status` 干净、三文件 md5 还原（`e4a14b2a…`/`c9d1a016…`/`6919fd67…`）；验收前后 `git status --porcelain -uall` 快照逐行相同（16 个改动文件 = 完成区「修改文件」）；全程未用 `git checkout/restore/stash`；未提交 git；本记录不含运行期路径。

**静态核验（cg9 七槽 / 掩码 / 仲裁）**：rc0–2 HW/RW，rc3/rc4 在 `anyWrite` 内但无写分支（写忽略、读回不变、不报异常），rc6 读恒 `2.U`，`rc7–15` 不入 `anyRead` ⇒ `CFXREG`；async 档 `maskRcMax=3`、`CommonEntry.isMask rc≤3` ⇒ `cg0–cg3 rc4` ⇒ `CFXREG`；`asyncIntrMaskOpt` 仅 4 处（定义 / `isAsyncMask`(ha≤3,cg8,rc1) / 读 / 软件写），trap·escape 无保存恢复，复位全 1，`asyncMaskByMode` 按 `runMode` 选行；`asyncAllowed = pendingNow & ~maskByMode & ~timerGate & timerSrcBit` 按位一次成型（无逐源循环），`asyncSrcFrame := asyncAllowed`、`pending &= ~(delivered|acked)`、`excp_async_num` 每 `ack&&valid` +1、`!asyncFrameLive` 防嵌套。

**重点 A＝误读（F1，须改措辞+给证据）**：`asyncTake = sExec && intr.valid`；sExec 首条 `when(asyncTake){intrAck; resvValid:=false; jumpFlush}`，其后全 `.elsewhen`（jump/call/ret/RAS/br/escape/cfx2/lr-sc/ld-st/fpSlow/trap/slow）；`execW0`/`w1En`/`scFailExec`/`fflags`/`gewu.io.wEn` 均含 `!asyncTake`；其余 `w0En` 分支需 sSlow/sCopy/sCls/sSemi/sMwait/sFpSlow；文件尾 2202–2274 的 `sExec when` 全为 printf；`retirePulse` 只在 `finish()`；多周期指令离开 sExec 后 `asyncTake` 恒 0 ⇒ **取中断当拍指令 i 零架构副作用（store 也未发出）**；`rb0` 读 `io.ip`，投递当拍 `ip` = 上一条提交后写入的下一指令地址 = `cause_ip`，与 §5.4(四)「cause_ip = 提交后的 rb0、不重放被中断指令」一致，escape 返回同一地址 ⇒ 该指令**首次**执行而非「重放」。完成区/遗留②「丢弃当前指令并重放、与『已提交』字面不符」应改写，并附上述静态门控清单（或一条边界非幂等用例）。

**重点 B＝真断（F2，阻断）**：`tests/arch/common/check_mode_env.py:144` 的旧句已不在 `contract-see §3` ⇒ `--selfcheck` **rc=1**（`contract-see §3 缺 global_cfx_intr_mask 初值句`），真实运行 `SetupError → return 2`，`run_arch.py --self-test` **rc=1**（`arch/common/check_mode_env.py rc=1`）。**master 同样复现（m18-spec-004 遗留，非本任务引入）**；`arch-umon-011` 为 `level: full`，不在 `check-arch-smoke` 代表集内 ⇒ 无门控红。要求 1 行改用 `check_cfx02_regs.py:84` 的现行句 + `--selfcheck` 复跑绿；`--self-test` 中 `check_power` 亦 master 已红（spec §3.8 句未命中），**验收只看 `check_mode_env` 项**。

**DIV 核验**：DIV-10 **删除与实际一致**（`mode_entry.S` 无异步段残留；README「例外修好 ⇒ 删条目」是既定收口法），完成区与 umon-README 写「关闭」属措辞（F5）；DIV-11 改写与 `WumingDecoder` 的 `withHart` 门控相符，但 reason「该册仍断言 `imms18 = 2` ⇒ ILLI」不准——册头明写只保留三平台可共同判定口径、case14 的 ILLI 来自 reserved cfxha（实测 `escape …, 12` rc=1、`, 8` rc=0）（F6）；**DIV-15 登记不合理（F7）**：Tiny 上 `cg0`–`cg2 rc4` 同样 `CFXREG`（只有 `cg3 rc4` 是 RW），且 QEMU `cfx_mode_reg` case4 仍返回 `cfx_intr_mask`（RW），并非「按 §3.1–§3.4 判 CFXREG」。

**判决：Needs Revision** —— 阻断项：**重点 B 的 1 行修复 + `--selfcheck` 自检复跑**；同一轮须改：**重点 A 完成区/遗留②措辞与可核证据**、F4/F5/F6/F7 文档订正。A/C/D/E/F 门控与两路注入在我本人重跑下全部通过（14+16+29+31 项 PASS，E 首轮 ENOSPC 已有据重试 1/3）。

### 第 2 轮 engineer 返工处置（reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| B 阻断：`check_mode_env.py:144` 仍匹配 contract-see §3 旧句 ⇒ `--selfcheck` rc=1、真实运行 SetupError、`run_arch --self-test` rc=1 | ✅已修 | 换现行句「`cfx0`–`cfx3` 的 `cg8 rc1`（异步来源掩码）初值全 1」（同 `check_cfx02_regs.py:84`）；同文件 docstring/错误串改名为 `cg8 rc1` 异步来源掩码 | `check_mode_env.py --selfcheck` **rc=0**（7 项 PASS）；`run_arch.py --self-test` rc=1 但该驱动项 **PASS**，唯一 FAIL 为 `arch/power/check_power.py`（其 `--selfcheck` 报 `spec/DADAO-12 §3.8 未找到`；`spec/` 本任务 0 改动 ⇒ 既有红） |
| A 误读：完成区/遗留②「丢弃指令并重放、与『已提交』字面不符」 | ✅已修（措辞 + 门控清单） | 完成区新增 ⑨：`asyncTake` 为 `sExec` 首条、其后全 `.elsewhen`；`execW0`/`w1En`/`scFailExec`/`fflags`/`gewu.io.wEn` 含 `!asyncTake`；`call/ret/RAS` 与 store（→`sMreq`）在其后；多周期不在 `sExec` ⇒ i 零副作用、`ip` 未改；`rb0` 读 `io.ip` ⇒ `cause_ip` = 上一条提交后的下一指令地址 ⇒ i **首次执行（非重放）**，与 §5.4(四) 一致；遗留②改为「边界非幂等用例未加」 | 逐项对源码：`WumingCore.scala` 929/971–977/1029/1518–1526/1839/2182–2183、`WumingRegFile.scala` 55–57/132/359；探针 cause_ip 落在等待循环区间 |
| F4 `check-patch-tree` 全局问题数写错（16 vs 22） | ✅已修 | ⑦ 改为「全局 **22** = qemu 6 / gem5 4 / linux 2 / musl 10，全为 assertion ⑥/⑨（共享源树与补丁集不一致）；本任务 diff 未触及这 4 个组件」 | 返工后 `ONLY=A` rc=0；日志逐段计数 6/4/2/10/0；`git diff --name-only` 中这 4 个组件 0 文件 |
| F5 `DIV-10` 措辞 | ✅已修 | 完成区 ⑧、`components/chipyard/README.md`、`tests/arch/umon/README.md` 统一为「条目已删除 / 随之删除」 | `grep DIV-10` 无「关闭」字样 |
| F6 `DIV-11` reason 不准 | ✅已修 | 重写 impact/reason/close_when：Tiny 保留 `imms18[17:1]` SBZ ⇒ 规范已合法的 `escape …, 8` 在 Tiny 仍 `ILLI`；`11-cfx/escape_ciii_cfx` **不受影响**（case 13/20 判 `imms18 = 3`、14/17/18 判 reserved cfxha，均不依赖 selector；册头 GAP ⑤ 已写明合法 cg9 路径不在该载体断言） | 逐行核对册头 34–41 与故障例 374–382、386–390；`escape …, 12` 汇编 rc=1、`, 8` rc=0 |
| F7 `DIV-15` 登记不合理 | ✅已修（删除条目） | 删 DIV-15；准确事实改记「新发现/坑」③⑤（Tiny 仅 `cg3 rc4` 为 RW，`cg0`–`cg2 rc4` 与 cfx0–3 `cg8 rc1` 仍 `CFXREG`；共享源树 qemu 仍 pre-`m18-qemu-005`） | `expected-divergences.yaml` 条目列表无 DIV-15、`yaml.safe_load` 通过 |

| 追加（用户指出，非既有红）`check_power` 的 `--selfcheck` 失败根因是 `m18-spec-004` 删 §3.9 断链 | ✅已修（越界 1 行，已披露） | `tests/arch/power/power_vast.py` 的 `space_bits()` 结束标记 `### 3.9` → 下一章 `^## 4\.` 起点（保持现场解析；全仓仅此一处依赖 `### 3.9`） | `check_power --selfcheck` **rc=0**（13 项 PASS，cg7 位表/块 0/expected 28/3 槽现场命中）；`run_arch.py --self-test` **rc=0（12 PASS / 0 FAIL）** |

判决：阻断项与 5 处订正全部处置；未改 RTL/探针源码 ⇒ 不重建（组件源树 `git status` 干净、`GewuFile.scala` md5 `e4a14b2a…` 与上轮一致）；追加的 `power_vast.py` 是纯 Python 判据。返工复跑：`ONLY=A` **rc=0（14/14）**、`ONLY=C,D` **rc=0（16/16）**、`--inject` **rc=0（29/29）**。状态 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-24，全部本人重跑，不采信完成区）

**三项自检**：`check_mode_env.py --selfcheck` **rc=0**（7 项 PASS，含「期望签名现场派生 8 槽」）；`check_power.py --selfcheck` **rc=0**（13 项 PASS，cg7 位表 / 块 0 `desc=0x5 start=0x3ff_ffc0_0000 size=0x400000 attr=0x5` / expected 28+3 槽现场命中）；`run_arch.py --self-test` **rc=0（12 PASS / 0 FAIL）**，两个驱动项均 PASS。

**`power_vast.py` 修复性质核验**：`space_bits()` 的结束标记改为 `re.search(r"^## 4\.", text[start:], re.M)` —— **取下一章起点、非写死小节号**（起点仍是 `### 3.8 cg7` 现场 `find`，`start<0 || end<0` 才抛）；`need` 9 项（exists/SRAM/ROM/MMIO/DRAM/OTHER/R/W/X）与 `cg7 **全部只读**` 句**均在 §3.8→`## 4.` 区段内实测命中**；全仓 grep `### 3.9` 仅剩该文件注释，无其它依赖。

**门控重跑**：`ONLY=A` **rc=0，14/14**（chipyard 段 0 problem / 26 patches；全局 **22 problem = qemu 6 / gem5 4 / linux 2 / musl 10 / chipyard 0**，与完成区⑦一致；`git diff --name-only` 对这 4 组件 **0 文件**）；`ONLY=C,D` **rc=0，16/16**（期望 56/16/16、stream 448/128/128 B）；`--inject` **rc=0，29/29**（inj1 红 slot00 `0x8000→0x0`、inj2 红 `0x20000`，`cp`+md5 `e4a14b2a…` 还原、强制重建 rc=0、`stream == reference` 回绿）。

**DIV 条目**：yaml `ids` 实测 **无 DIV-10、无 DIV-15**（12 条，`yaml.safe_load` 通过）；DIV-11 逐项核 —— reason 的 case 13/20 = `imms18 = 3`、14/17/18 = reserved cfx6/cfx6/cfx61（册 374–382 行实测一致；15/16/19 为 SBZ 类，同样不依赖 selector 合法路径），GAP⑤ 与册头一致；impact「Vast 帧空 ⇒ `CFXESC`」与 `GewuFile` 的 `escapeCg9Ok` 一致；`close_when` 合理。`umon/README`「条目随之删除」、`components/chipyard/README`「条目删除」均已无「关闭」字样。

**完成区 5 处订正落点**：⑦ 22 计数 ✓；⑧ 两条目已删 ✓；⑨ 门控清单与我第 1 轮逐行核对一致，且**完成区/新发现/遗留三段已无「丢弃当前指令 / 字面不符 / 会重放 / 后重放」**（`grep` rc=1），仅存正向的「首次执行（非重放）」与引 spec 的「不重放」；遗留② 已改为「边界非幂等用例未加」；「修改文件」18 项与 `git status` 逐一对上（含返工新增的 `check_mode_env.py`、`power_vast.py`）；RTL 补丁与探针 `diff --stat` 和第 1 轮逐字相同（534/26/15/265/220/87）⇒ 未改 RTL/探针源码。

**约束核验**：组件源树 `git status` 干净、三文件 md5 与第 1 轮一致（`e4a14b2a…`/`c9d1a016…`/`6919fd67…`）；末版 Vast sim `770213e5…`；验收前后本任务快照 18 个改动文件与「修改文件」清单一致；全程未用 `git checkout/restore/stash`；未提交 git；本记录不含运行期路径。

**finding（文档级，不阻断）**：第 2 轮处置表「复验证据」列有 3 处行号不准 —— `WumingRegFile.scala 359` 超出该文件长度（实测 246 行）、`WumingCore 1839` 与 `2182–2183` 落在注释行（store 的 `memStore :=` 在 1843、`gewu.io.wEn :=` 在 2186–2187）；完成区⑨ 本身不写行号、内容属实 ⇒ 建议 architect 收尾时顺手订正这三处行号。

**判决：Accepted** —— 三项自检、`ONLY=A`、`ONLY=C,D`、`--inject` 在我本人重跑下全绿；阻断项 B 与 5 处订正全部落地并复核通过；仅余上条文档级行号 finding，交 architect 收尾处理。
