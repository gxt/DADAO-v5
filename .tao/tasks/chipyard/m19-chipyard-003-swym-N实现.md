# m19-chipyard-003: chipyard 实现 swym N（12 位、1+N 拍、原子）

**模块**：chipyard
**项目里程碑**：M19
**依赖**：`m19-spec-001`（语义与契约）
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

当前 `WumingCore` 把 `fence`/`swym` 都当 1 拍 no-op，`swym N` 的 N 被忽略。用户 2026-11-27 定：N=12 位、`immu18[17:12]` SBZ（非零 ILLI）、总时延 1+N、原子（执行期间不取中断）。这条会作为后续流水线/超标量“长延迟原子指令”的基线。

## 目标

1. 解码/合法性：`immu18[17:12]` 非零 ⇒ `ILLI`；`N = immu18[11:0]`。
2. `WumingCore` 增加 `swym` 多拍状态：`swym 0` 仍 1 拍；`swym N` 数 N 个额外拍，总 1+N。
3. **原子**：`swym` 执行期间不检查/不取中断；完成后回到正常指令边界再取。
4. 更新 trace/cycle 口径与 `contracts/wuming-cycles.yaml` 派生；不改其它指令语义。
5. Verilator 仿真可测：N=0/1/4095 的周期与高位 ILLI。

## 验收（逐条贴真实 rc）

1. `make build-chipyard`（或等价）rc=0；Verilator 跑通新增用例。
2. 周期：N=0 ⇒ 1 拍、N=1 ⇒ 2 拍、N=4095 ⇒ 4096 拍（trace/cycle 实测）；`immu18[17:12] != 0` ⇒ ILLI。
3. **原子性**：构造 `swym` 期间到达的 pending 中断，确认不中途进入，完成后才取；若 Tiny 当前无可用中断源，须在任务书披露并给出替代验证（如 gem5 对照 + RTL 静态检查）。
4. **可达 FAIL ≥2 路**：① 计数器少一拍/多一拍 ⇒ 周期用例红；② 去掉高位 SBZ ⇒ ILLI 用例红。
5. `check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。

## 约束

独立 `git worktree`；**不提交 git**；只动 `dadao-wuming` 核/测试与必要补丁；不改 QEMU/gem5；不接板；完成区不写具体 `.work/**` 路径。
