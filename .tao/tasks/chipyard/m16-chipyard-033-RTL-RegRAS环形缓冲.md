# m16-chipyard-033: RTL `WumingRegFile` RegRAS 改环形缓冲（去搬移）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：用户当前自行修复的 `escape`（`DIV-11`）先合入（同改 chipyard RTL）
**可并行分片**：否（同改 `components/chipyard`）
**预估**：4–8 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（用户 2026-11-25）

`spec/SimRISC-00 §2.4.3` / `ADR-0012 D7.5` 允许并推荐**环形缓冲 + 隐藏基准索引**；用户确认 RTL 不应使用搬移——`call`/`ret` 搬 62 个 64 位槽是直接的时序/面积代价。

现状：`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingRegFile.scala.patch` 中 `WumingRasOp.PUSH/SPILL` 做 `raNext(i) := ra(i+1)`（i=1..62）、`POP` 做 `raNext(i) := ra(i−1)`（i=2..63），每周期整体搬移。QEMU 的 `ras_base` + `ra_phys()` 是参考实现（`1 + (base + i) % 63`）。

## 统一环形约定（硬约束；用户 2026-11-25）

四平台必须用**同一套**隐藏布局，否则「全 64 槽按值比」会因窗口外残留不同而假红：

- 物理槽：`0` = `ra0` 元数据（`{SBZ,RACNT,MRPTR}`，不占窗口），`1..63` = 环形数据槽；
- 映射：`phys(i) = 1 + ((base + i) % 63)`，`i ∈ 1..63`；`base` 为 6 位隐藏基准（0..62，复位 0，不可架构访问）；
- 推进方向与 QEMU `ra_phys()` 一致：`call` 压栈 `base += 1`、`ret` 弹栈 `base −= 1`（模 63），写入/读出均经映射；
- 架构视图（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd` 与 trace/`-d cpu` 导出）一律按映射换算。

## 要做

1. 在 `WumingRegFile` 增加隐藏基准寄存器 `rasBase`（6 位，0..62，复位 0，**不可架构访问**）；
2. 逻辑→物理映射函数；**所有** `ra1..ra63` 的架构访问走映射：`raRead()`、通用 `read()` 的 RA 分支、写回口（`ld.o-ra`/`st.o-ra`）、`rd2ra`/`ra2rd` 块赋值、`io.rasTopCount/rasTopAddr/rasOldest`；
3. `PUSH/SPILL` 改为「`rasBase` 前进一格 + 写新栈顶」，`POP` 改为「`rasBase` 后退一格」；`FOLD/DEC/REFILL/CONSUME` 仅经映射读写，判定与提交语义不变；
4. 架构视图与改前逐例一致（`ra_i` 逻辑序、`ra0` 位域、RASOF/RASUF、MemRAS 溢出/回填）；
5. `WumingTiny`/`WumingVast` 两种配置均构建 rc=0，`%Error`=0；复跑 arch 探针（`arch-hart-001/002`）、`check-idl-full` 274。

## 不做

- 不改 `escape`/cfx/monitor 等其它 RTL；
- 不改 spec/契约/版本号；不改 QEMU/gem5/IDL。

## 约束

- 独立 `git worktree`；组件补丁按 `docs/Process-01`（改隔离源树 → `make_patch.py chipyard` 重导）；不提交 git；
- 只动 `components/chipyard/patches/generators/dadao-*/…/WumingRegFile.scala.patch`（必要时 `components/chipyard/{README.md,changelog.md}`、`tests/arch/hart/` 探针）+ 本任务书；完成区 ≤30 行。

## 验证

1. `check-patch-tree` chipyard 段 0 problem；Tiny/Vast 构建 rc=0；sim md5 记录；
2. RAS 相关 arch 探针全绿；`check-idl-full` 274/274（芯片侧与改前逐例一致）；
3. **可达 FAIL ≥2 路**：① `POP` 基准不后退 ⇒ 返回地址错/探针红；② 映射写成 `% 62` ⇒ 溢出/回绕用例红；`cp`+md5 还原重建回绿；
4. 综合资源对比（可选记录）：搬移逻辑消失后的 LUT/FF 变化；
5. `git status -uall` 仅允许文件 + 任务书。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
