# 讨论项

> 讨论记录的单一落点；不承担任务流水，不写里程碑，不写编号。
> 任务成立后只追加「→ 已转 <任务号>」，状态仍以 `milestones.md` 为准。

## 生成器 OUT_DIR 修正

- 状态：已转任务
- 结论：`generate_ctrl_jump_call_ret.py` / `generate_ctrl_br.py` 的 `OUT_DIR` 仍指旧 `tests/vectors/isa`，重跑不会更新 `tests/inst`
- 下一步：→ 已转 TESTCASES-087t

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

- 状态：0043/0045 已 Accepted；0046 仍 Proposed
- 结论：ADR-0043/0045 的决策已确认并收口；ADR-0046 等 Linux 实测后再收口
- 下一步：不再改 0043/0045 的 decision；0046 保持 Proposed

## 从 CFX 审计保留的未决项

- 状态：待立项
- IPI：只有接收端，没有发送服务/寄存器
- TLB：只有 invalid，没有 fill 机制
- `cfx_pmem_exist`：SEE 与 SBI 语义不一致
- UART：实例号/索引语义未定义
- 下一步：确认哪些进入 M10 后/Linux 前任务；不直接恢复已删除的审计文件

## 从 milestones.md 迁入的现行规则/规划

> 非历史内容，当前仍有效。

## 体例约定（硬约束）

1. **任务流水用表格**：列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**一句改动 ≤120 字符**（中文按 1 字符计）；细节写各任务书，本文只做**索引**（与 `lessons §1.4` 一致）。
2. **按完成时间倒序**（最新在上）；**未完成任务也必须列**，其时间列 = **登记时间**并加注 `（登记）`；同一时间按任务编号升序。
3. **状态以任务书头部「状态」字段为准**；本文与任务书不一致 ⇒ L1 门控 `check-milestones-fresh` 红。
4. **表格之后的当前进度 / M8 规划区 / 状态快照 / M9 规划须随任务与产物同步更新**；计数一律**现场派生**，不写死。

> 机械校验：`make check-milestones-fresh`（L1；状态一致 / 覆盖 / 长度 / 次序 / 格式五断言，`--self-test` 内置五类反例）。

## M10 规划（2026-10-26，用户裁定）

**当前里程碑 = CFX 完善与验证**；**Linux 内核支持推到下一里程碑**（本里程碑不排 Linux 任务）。

**Linux 7.2.10 × 当前 LLVM 兼容性评估**（architect 实测；源码 `.work/source/linux`）：
- 可用：64 位/大端代码生成、原子（LR/SC + fence，1/2/4/8B）、inline asm `r/m/i/n`、`asm goto`（无输出）、builtins（clz/ctz/popcount/bswap/overflow）、section/attribute、TLS、`default`/`large` code model、DWARF、`.S` 宏与 `.rept`、lld 内核式脚本（KEEP/PROVIDE/ALIGN/LONG/QUAD/ASSERT）/高地址/`R_DADAO_ABS48`、`llvm-readelf/nm/objdump/objcopy`。
- 缺口（阻断序）：① `arch/dadao` 不存在（首要）；② 缺 `llvm-ar`/`llvm-ranlib`/`llvm-strip`（`LLVM=1` 直调；GNU ar 可临时顶）；③ `asm goto` + 输出必现 SelectionDAGBuilder 断言（`CC_HAS_ASM_GOTO_OUTPUT` 探针失败）；④ 栈保护无法 lowering（`-mstack-protector-guard=global` 不支持）；⑤ 汇编器拒 `.quad/.long/.short/.byte`（只认 `.dd.*`；`CC_HAS_ASM_GOTO_TIED_OUTPUT` 探针失败）；⑥ inline asm 约束仅 `r/m/i/n`；⑦ `-mcmodel=kernel` 不支持（用 default/large）。
- **兼容性 spike（定义）**：一次性时间盒实验——在 `/tmp/opencode/M10-COMPAT/` 造**丢弃式**最小 `arch/dadao` 桩（仅够 Kconfig/头文件），用现有 clang/lld 编 20–30 个代表性 generic 文件 + Kconfig 探针，产出「编译器缺口 + 规避法」清单；**只做编译/链接、不运行**。与 QEMU **正交**：QEMU 是运行侧（机器模型/启动/设备/MMU），不参与 spike；spike 的桩不是端口交付物。
- **下一里程碑入口判据（建议）**：spike 清单归零或有规避法 + `llvm-ar/ranlib/strip` 就位 + `arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux。
