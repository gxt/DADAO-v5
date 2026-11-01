# 讨论项

> 只记**当前未决/待裁定**事项；任务流水看 `.tao/knowledge/milestones.md`，历史与已落实项不在此保留。

## 待用户裁定：ADR

### ADR-0017 D10 与 LLVM-141t stride

- 状态：待用户裁定
- 结论：LLVM-141t 已实现 `rc = rcBase + N*stride`；`ADR-0017 D10` 仍写 `rc = rc_base + N`，属扩展，未静默改写
- 下一步：逐条确认后修订 D10 或另立 ADR；确认前不改 ADR

### SPEC-180t 的 ADR

- 状态：待用户裁定
- 结论：escape 合法偏移集 `{0,+4}` + `imms18[17:1]` SBZ ⇒ ILLI，按 `docs/Process-03` 命中外部契约变更/多方案/结论固化
- 下一步：逐条确认 decision 后再立 ADR；未确认前只保留为遗留

### ADR 状态

- `ADR-0043`/`0045`：已 `Accepted`
- `ADR-0046`：仍 `Proposed`，等 Linux 实测后再收口
- 下一步：不再改 0043/0045 的 decision；0046 保持 `Proposed`

## 待立项 / 后续

### M10 收尾

- 状态：任务书已全部 `已验证`（089 待 merge）；`check-night` 尚未跑
- 下一步：`check-night` **4/4 PASS** 后才建 `INTEG-052m` 并置 M10 里程碑

### M10 后的 cfx 范围

- 已实现：umon/jmon/smon/hmon/ptw/pmem/time/hart/power
- 后置：cache/llc/uart、PMEM 区域分配、IPI、多 hart
- 下一步：M10 收尾后按 Linux 需求拆任务

### U-mode / cg5 / 异步帧

- 状态：待讨论
- 结论：U-mode 的 cfx 目标不设 ISA 限制，由 OS 策略决定；cg5 单帧、同步/异步分离、递归/重入尚未定
- 下一步：等 cg7 与 escape 收口后再讨论

### SBI 生产 provider / W1C

- 状态：后置
- 结论：当前只有测试专用 provider；生产 provider、`DONE/ERROR` W1C、`WAIT` 属 Linux 集成阶段
- 下一步：不在 M10 通路内实现

### QEMU 注释 7-14 与宏 6–14 不一致

- 状态：待立项
- 结论：`components/qemu/patches/target/dadao/helper.c.patch` 仅注释笔误，实现正确
- 下一步：另立最小修或并入后续 QEMU 任务

### TESTCASES-089t 遗留

- `reserved.yaml` 是否拆册（当前同册承载「保留编码 ⇒ UNDI」与「reserved cfx 地址空间 ⇒ CFXMEM」两类语义）
- `trap`/`escape` → reserved cfx 的 active 向量仍 deferred（`TESTCASES-033t`）
- `tests/inst/README.md` M1 条数写 152、现场 156（文档漂移）

### 生成器/门控后续

- `--check` 是否入 Makefile 门控（L1/L2）未定；目前仅脚本自跑
- `tools/testcases/test_anti_forgery_008t.py` 仍引用旧 `tests/vectors/**`，疑似孤儿
- `tests/README.md` 的「生成器 `--check` 全部 byte-identical」措辞待与三生成器对齐

### CFX 审计保留的未决项

- IPI：只有接收端，没有发送服务/寄存器
- TLB：只有 invalid，没有 fill 机制
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致
- UART：实例号/索引语义未定义
- 下一步：确认哪些进入 M10 后/Linux 前任务；不恢复已删除的审计文件

## 下一里程碑入口（Linux）

- 兼容性缺口：`arch/dadao`、`llvm-ar/ranlib/strip`、`asm goto` 输出、栈保护、`.quad/.long/.short/.byte`、inline asm 约束、`-mcmodel=kernel`
- 入口判据：spike 清单归零或有规避法 + 工具链就位 + `arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux
- 详细兼容性记录不在此展开；按后续任务书落纸

## 现行约定（非讨论项）

- 任务流水体例由 `make check-milestones-fresh` 机械校验（状态一致 / 覆盖 / ≤120 字符 / 倒序 / 格式），不在本文复述。
