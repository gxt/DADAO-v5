# m16-gem5-027: gem5 RegRAS 改环形缓冲（去搬移）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m20-gem5-003` 合入（同改 `components/gem5/patches/.../exec/b5.cc.patch`，须等其释放写者）
**可并行分片**：否（同改 `components/gem5`）
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-25）

`spec/SimRISC-00 §2.4.3` 与 `ADR-0012 D7.5` 明确：实现可用**环形缓冲 + 隐藏基准索引**避免压栈/弹栈时的数据搬移，`ra_i` 仍按架构视图可见。用户确认**不应使用搬移**（`call`/`ret` 每次搬 62 个 64 位条目，直接影响性能）。

现状：gem5 `exec/b5.cc` 的 `pushRas`/`popRas` 用 `ctx.writeInt(Bank::Ra, ...)` 循环整体挪动有效窗口（C3a/D3 等路径），与策略不符。QEMU 的 `ras_base` + `ra_phys()` 是现成参考实现。

## 统一环形约定（硬约束；用户 2026-11-25）

四平台必须用**同一套**隐藏布局，否则「全 64 槽按值比」会因窗口外残留不同而假红：

- 物理槽：`0` = `ra0` 元数据（`{SBZ,RACNT,MRPTR}`，不占窗口），`1..63` = 环形数据槽；
- 映射：`phys(i) = 1 + ((base + i) % 63)`，`i ∈ 1..63`；`base` 为 6 位隐藏基准（0..62，复位 0，不可架构访问）；
- 推进方向与 QEMU `ra_phys()` 一致：`call` 压栈 `base += 1`、`ret` 弹栈 `base −= 1`（模 63），写入/读出均经映射；
- 架构视图（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd` 与 trace/`-d cpu` 导出）一律按映射换算。

## 要做

1. 在 gem5 的 DADAO 寄存器面引入**隐藏基准索引** `rasBase`（0..62，非架构状态，复位 0；`ra0` 仍只暴露 `{SBZ,RACNT,MRPTR}`）；
2. 逻辑下标 → 物理槽映射（`1 + (rasBase + i) % 63`，`ra0` 不占槽，与 QEMU 一致），**所有** RA 架构访问走映射：`readInt/writeInt(Bank::Ra, …)`、`ld.o-ra`/`st.o-ra`、`rd2ra`/`ra2rd`、C3b 溢出源、`-d cpu` 状态导出；
3. `pushRas`/`popRas`：C1/C3a/D3 改为「写一个槽 + 基准 ±1」，删除搬移循环；C2/C3b/D2/D4b 的判定与提交顺序、精确异常语义**逐条不变**；
4. 序列化/checkpoint：若 RA 状态参与序列化，`rasBase` 一并存取，保证回放一致；
5. 复跑 gem5 侧回归：`tests/arch/hart` 的 RAS 探针、`run_arch --platforms gem5`、`check-idl-full`（四方 274）。

## 不做

- 不改 QEMU/RTL/IDL；
- 不改 spec/契约/版本号；不改 `ra0` 位域与 RASOF/RASUF 判据；
- 不顺手改 `b5.cc` 其它指令。

## 约束

- 独立 `git worktree`；组件补丁按 `docs/Process-01` 生成（`make_patch.py gem5`）；不提交 git；
- 只动 `components/gem5/patches/src/arch/dadao/**`（必要时 `components/gem5/changelog.md`）+ 本任务书；完成区 ≤30 行。

## 验证

1. `check-patch-tree` gem5 段 0 problem；重建 rc=0；
2. gem5 RAS 探针全绿；`check-idl-full` 的 gem5 侧与改前逐例一致（274 例签名槽 + 退出码）；
3. **可达 FAIL ①**：基准索引在 D3 不前进（等价恢复搬移前的半套逻辑）⇒ RAS 探针必红；`cp`+md5 还原重建回绿；
4. **可达 FAIL ②**：映射函数写错（`% 62`）⇒ 溢出/回绕用例必红；还原回绿；
5. 改后 `git status -uall` 仅允许文件 + 任务书。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 信号帧压栈 `se_workload.cc::pushRasReturn` 是第二个 RAS 生产者，不动会与核心布局分叉 | ✅已修 | 同一 `ras::phys` + base ±1，去掉搬移循环 | RAS 链例 15/15；idle 未覆盖信号路径，代码级审查 |
| `clone`/`fork` 复制物理 RA 槽但子 ISA 的 base 仍为 0 | ✅已修 | 两处复制后 `setRasBase(parent)` | 代码级审查；converge/clone 用例无回归 |
| `-d cpu` dump 直读物理槽 | ✅已修 | `traceInstruction` 按 `ras::phys(rasBaseIdx, i)` 逻辑视图打印（同 QEMU `cpu.c`） | 与 QEMU 输出逐行同式（代码对照） |
| checkpoint 只存线程寄存器物理槽、不存 base | ✅已修 | `ISA::serialize/unserialize` 存取 `rasBaseIdx` + 越界 panic | 编译通过；回放语义推演 |
| 测试 harness 直写 `ctx.ra[]` 绕过映射 | ✅已修 | 各 MockContext 加 `ringBase`/`raAt()`；b5 增「物理槽未搬移」与 base 62→0 回绕断言 | b5 1316 条 PASS、0 FAIL；注入②命中 C3b/wrap/D3 |
| C3b 的 MemRAS 写失败必须不提交 base | ✅已修 | `setRasBase` 放在 `writeMem` 成功之后（读底部用旧 base） | 既有 `call C3b write fault: RA state unchanged` 仍 PASS |

### 第 1 轮 reviewer 复核

- **重跑**：`make build-gem5 JOBS=32` rc=0（注入/还原各重建一次均 rc=0）；运行期证据目录内 `run.sh` 全量：首跑 274 例 rc=75（writer-guard 拒绝：共享源树有并发 llvm 写者，环境干扰非交付物缺陷），第 1/3 次有据重跑 **rc=0、44 PASS/0 FAIL**（b1–b7 rc=0 且 `[FAIL]` 0；converge `ids 263/263, boundary 1841/1841, failures 0`；RAS 探针 15/15 逐字节=改前；274 例 rc=0、逐字节=改前；两路临时树注入 md5 对账还原回绿）。`make check-idl-full` 脚本 rc=1：唯一 `[FAIL] escape_ciii_cfx`（chipyard:13 既有红）、四方 273/274、**gem5 侧 274/274**（改前日志同为该唯一红）。`make_patch.py gem5` rc=0（0 written/106 unchanged）。`check_patch_tree`：gem5 段 106 patch / **0 problem**（整体 4 problem 只在 llvm-project/musl，改前既有）。
- **环形约定**：`exec/common.hh::ras::phys` 与 QEMU `ra_phys` 同式（idx 0 → 槽 0；`1+(base+idx)%63`，QEMU 负值分支不可达），`kSlots=63`；base 0..62、复位 0（`clear`/`resetThread`）、仅 `setRasBase` 越界 panic，无架构写口；C3a/C3b `base+1`、D3 `base−1`（模 63）与 QEMU `helper.c` 逐条同序（C1/D4b 不动 base 亦同）。
- **语义不变**：diff 逐条核对 C1/C2/C3a/C3b/D1–D3/D4a/D4b 判定与提交顺序未变；RASOF/RASUF 先于任何写；C3b 底部用**旧 base** 读（=QEMU `ra_phys(env,1)`），`writeMem` 成功后才 `setRasBase`，失败零提交。
- **访问面/漏映射审计**：全仓 grep `Bank::Ra|int_reg::Ra|RaBase|ra[` —— `readInt/writeInt(Bank::Ra)` 统一换算（b1 `Target::Ra`/`ld.o-ra`/`st.o-ra`/`ldm/stm.o-ra`、b2、b5 的 `rd2ra`/`ra2rd`/C3b 源均经此口）；`-d cpu` `traceInstruction` RA[00..63] 按 phys；`SERIALIZE/UNSERIALIZE_SCALAR(rasBaseIdx)`+越界 panic；信号帧 `pushRasReturn`、clone/fork 复制 base、`resetThread`/`clear`/`copyRegsFrom` 同步。**无漏映射**：残留直写/直读仅槽 0（`process.cc` 写 ra0、`isa.cc` 读 ra0 头），`phys(base,0)=0` 恒等。
- **独立注入**（自选，非完成区两路）：C3a 不推进 base ⇒ b5 harness **5 FAIL**（rc=1）、gem5 探针 14/15、`call_iiii_ra` rc=12；`cp`+md5（`bd21d1e0…`）还原、重建 rc=0、探针 **15/15 rc=0**。另试坏 `phys()` 致 `-Werror` 编译红，亦按 md5（`1b77287c…`）还原，源树 `git status` 干净。
- **越界/快照**：`git status -uall` 前后均 17 行 = 15 份 patch + changelog + 本任务书，与完成区声明一致；106 份 patch md5 与开工快照逐文件相同（`make_patch` 幂等未改文件）。
- **`PASS_BASELINE` 过期属实**：现树实测 b1 2196 / b6 1414 / b7 2960 vs 表 2156/1384/2955，且本任务对 b1/b6/b7 的 diff **零新增 `check(`**（仅 `ra[]→raAt()` 替换）⇒ 改前即过期；b5 1316 vs 1292 为本任务 +24。`check_converge.py` 现 rc=1（4 红），未挂任何 Makefile 门控 ⇒ **建议另立 infra 任务重冻**（2196/1160/4318/3696/1316/1414/2960），本任务不实施。
- **判决：Accepted**（无阻断项；首跑失败为环境并发干扰，已按 1/3 有据重跑并记录）。

## 完成区

**测试结果**：`check_b1`–`check_b7` rc=0、`[FAIL] 0`（b5 1292→1316 条，含环形断言）；converge harness `ids 263/263, boundary 1841/1841, failures 0`；gem5 RAS 探针 `tests/inst/06-control-flow` 15/15 镜像（call/ret 链例 + 故障链 20 例）逐字节与改前相同；`check-idl-full` 273/274（唯一既有红 chipyard `escape_ciii_cfx`，改前同），gem5 侧 274/274 例 rc + 签名字节流与改前逐例相同。
**修改文件**：`components/gem5/patches/` 15 份（`exec/common.hh`、`exec/b5.{hh,cc}`、`exec/b1–b7_test.cc`、`exec/converge_test.cc`、`inst.cc`、`isa.{hh,cc}`、`se_workload.cc`）+ `components/gem5/changelog.md`；本任务书。源树本地 commit 修正为 base+1；`make_patch.py gem5` 15 written / 91 unchanged（共 106 份）。
**验收结果**：`build-gem5` rc=0（改前 md5 `6e9b68e7…`；改后各次重建 `66940094…`/`9138d503…`/`6fe31a8d…`，md5 随链接时间变化，不作语义判据）；`check_patch_tree` gem5 段 106 patch / **0 problem**（整体 rc=1 的 4 条 problem 在 llvm-project/musl，与本任务无关）；注入①（D3 不后退 base）⇒ `ret_riii_ra` 红 rc=4，注入②（`% 62`）⇒ b5 harness 6 红 + `call_iiii_ra` 红 rc=12，均 `cp`+md5 还原重建后 `15/15` 回绿（`run.sh --gem5-inject` 可复现）；证据 `run.sh` 全量 PASS（含临时树注入自检）。
**新发现/坑**：① RAS 生产者不止 `b5.cc`——信号帧 `pushRasReturn` 与 `clone`/`fork` 的 RA 复制也必须带 base，否则信号返回/子进程的 RA 逻辑视图错位；② `gem5.opt` md5 每次链接都变（内嵌编译时间），不能用 md5 判断「同一二进制」，语义判据只能用探针/逐字节；③ `check_converge.py` 的 `PASS_BASELINE` 改前已过期：纯净源树实测 b1 2196 / b6 1414 / b7 2960 vs 表 2156 / 1384 / 2955。
**遗留问题**：`tools/gem5/check_converge.py::PASS_BASELINE` 需重冻（b1 2196、b5 1316、b6 1414、b7 2960；b5 的 +24 来自本任务新增断言）。该文件超出本任务「只动 `arch/dadao/**`」范围，未改；建议另立 infra 任务。

