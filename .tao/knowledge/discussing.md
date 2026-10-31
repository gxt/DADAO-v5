# 讨论项

> 讨论记录的单一落点；不承担任务流水，不写里程碑，不写编号。
> 任务成立后只追加「→ 已转 <任务号>」，状态仍以 `milestones.md` 为准。

## 生成器 OUT_DIR 修正

- 状态：待立项
- 结论：`generate_ctrl_jump_call_ret.py` / `generate_ctrl_br.py` 的 `OUT_DIR` 仍指旧 `tests/vectors/isa`，重跑不会更新 `tests/inst`
- 下一步：立 TESTCASES 任务，改生成器输出目录并验证三册 byte-identical

## LLVM 别名 stride

- 状态：已转任务
- 结论：cg7 数组别名需要 `format=2` + `array`/`stride`；`regs=1430` 按展开别名数
- 下一步：→ 已转 LLVM-141t（任务书在独立 worktree）

## escape 只允许 0/+4

- 状态：待立项
- 结论：`imms18[0]` 只允许 0/1，`imms18[17:1]` SBZ；汇编器拒绝非法值，QEMU 执行 ⇒ `ILLI`；`excp_cause_ip` 仍 RW，不构成任意返回安全边界
- 下一步：立 SPEC-180t，再做 LLVM/QEMU 同步

## QEMU 注释 7-14 与宏 6–14 不一致

- 状态：待立项
- 结论：`components/qemu/patches/target/dadao/helper.c.patch` 仅注释笔误，实现正确
- 下一步：可并入生成器/测试修正任务，或单独最小修

## reserved cfx 普通 ld/st 覆盖缺口

- 状态：待立项
- 结论：当前 `tests/inst` 没有 active 的 reserved cfx 普通 `ld/st` 向量，`CFXMEM` 语义只覆盖了取指/其他路径
- 下一步：评估是否新增向量；需确认不与现有 fault 优先级冲突

## M10 的 cfx 实现范围

- 状态：讨论中
- 结论：当前测试机只实现 umon/jmon/smon/hmon/ptw/pmem/power；cache/hart/llc/time/uart 未实现
- 下一步：定 M10 是否纳入这些 cfx，再拆任务

## U-mode / cg5 / 异步帧

- 状态：讨论中
- 结论：U-mode 的 cfx 目标不设 ISA 限制，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入尚未定
- 下一步：等 cg7 与 escape 收口后再讨论；不在当前通路任务内细化

## SBI 生产 provider / W1C

- 状态：后置
- 结论：当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段
- 下一步：不在 M10 通路任务内实现

## ADR 状态

- 状态：待处理
- 结论：ADR-0043/0045/0046 仍为 Proposed，对应实现已落地
- 下一步：逐条确认后转 Accepted；不擅自改状态
