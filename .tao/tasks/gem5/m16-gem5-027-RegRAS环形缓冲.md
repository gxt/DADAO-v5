# m16-gem5-027: gem5 RegRAS 改环形缓冲（去搬移）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m20-gem5-003` 合入（同改 `components/gem5/patches/.../exec/b5.cc.patch`，须等其释放写者）
**可并行分片**：否（同改 `components/gem5`）
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

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

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
