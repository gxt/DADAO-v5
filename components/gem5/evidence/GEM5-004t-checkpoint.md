# GEM5-004t 阶段性 checkpoint：标量立即数与控制流

日期：2026-10-12。此页记录 `GEM5-004t` 的阶段性结果，**不是该任务验收**。

## 已实现与已验证

- 基于现有 `tests/vectors/isa/` 的输入和期望，新增 `or.w`、`andn.w`、`set.zw`、`set.ow`、`cmp.ui`、`cmp.si`，覆盖正常结果及 `rd0` 非法目的。
- 新增条件分支 `br.n/nn/z/nz/p/np/eq/ne`、RB 判零分支和 `jump` 的立即数／寄存器形式。fixture 可在 RAM `0xFC00_0000_0000` 放置指令，核对分支成立、不成立和 `rb0=PC`。
- `make build-gem5` 退出 0；`make test-gem5` 从 16 条增加到 **50 条运行用例**并退出 0。新增门控在实现前分别失败：立即数操作旧实现报 `ILLI`，控制流 fixture 缺少 RAM 指令加载地址参数。
- `make_patch.py gem5` 导出 33 个逐文件补丁；`check_patch_tree.py`、`--source-state`、`make fetch-gem5 apply-gem5` 均退出 0。gem5 组件源码为锁定基线加一提交 `34ed4483d85d99e91b05aea6b68ef50e1e85207f`，工作树干净。

原始构建和运行日志：`.work/log/gem5/GEM5-004t-scalar-*`、`GEM5-004t-control-*`。日志属仓库忽略的测试产物，本页保留可追溯结论。

## 下一步和验收边界

`GEM5-004t` 仍须实现 RD/RB/RA 访存、块操作、其余整数／地址运算、调用／返回与 RegRAS/MemRAS，并执行其规范反例和程序序列。`GEM5-005t` 的 ELF、ROM 启动、模式移交和 25 项 semihosting，以及 006–008 的 FP／全集成尚未完成。`check-gem5-full` 仍按预期失败，不能用本页的 50 条代表集替代全量验收。

仓库级非 gem5 阻断保持原状：`make check` 的已有知识引用悬空；`make check-modules` 缺少既有 `llvm-lit` 安装根。按用户授权，本轮未修改其他模块。
