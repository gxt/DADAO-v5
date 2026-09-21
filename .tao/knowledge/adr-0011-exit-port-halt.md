# ADR-0011: Exit-Port 可靠 Halt 机制

**状态**：Accepted
**日期**：2026-09-21
**关联**：ADR-0004 D3（Exit Port 协议）/ D5.8（fault 退出码）、ADR-0009 D5（退出码协议）、`QEMU-022t`、`QEMU-015t`（发现该问题）

## Context（背景）

`QEMU-022t` 修复 `dadao_tr_tb_stop` 缺 `gen_update_pc` 的 TB 续接缺陷后，暴露出更深层的机制问题：

exit-port handler 当前用 `qemu_system_shutdown_request_with_code()` + `cpu_exit()` 请求退出，但 **vCPU 不会被立即停止**——写 exit port 后仍有执行窗口，后续 guest 指令（FAIL store、UNDI 终止符）**可以覆盖退出码**。

实测证据（reviewer 独立复现，`QEMU-022t` 审阅记录）：

- 最小复现（纯 fallthrough：`set.zw rd18,0; st.o rd18,exit,0; set.zw rd18,1; st.o rd18,exit,0`）在修复后 **40 次运行 → 35 次 `exit=0x00` / 5 次 `exit=0x01`**（不确定）。
- 修复前（回退到 `0007`）同一复现 **40/40 确定**（但那是死循环掩盖竞态的结果）。
- 既有探针回归出现**不确定假失败**：`008t` 3/10、`009t` 7/10、`010t` 2/3、`013t` 2/3 次出现 `exit=0x01`。
- 机制原因：`cpu_exit()` 置 `exit_request`，`cpu_handle_interrupt` 将其转为 `EXCP_INTERRUPT`，`cpu_handle_exception` 对该异常返回 false，**外层 `cpu_exec` 循环不会停止**。

ADR-0004 D3 已冻结「写 exit port → 取低字节 → 传播到 `$?`」，但**未指定 halt 机制的确定性保证**。退出码不确定将使 harness 的语义验证（`QEMU-021m` 要求全量语义 PASS）不可靠，故须补全该机制并冻结。

## Decision（决策）

**D1 — exit-port 写后立即 halt。** exit-port handler 必须在写入退出码后**立即停止 guest 执行**；机制采用 `cpu_loop_exit()`（`longjmp` 回到 `cpu_exec` 的 `setjmp` 点），此后**不再执行任何 guest 指令**。

**D2 — exit code 优先于后续 fault。** exit port 写入的退出码**优先于**后续 fault（UNDI/ILLI 等）产生的退出码；当 shutdown 已请求时，`dadao_cpu_do_interrupt` 跳过 fault 处理，**不覆盖**已锁定的退出码。

**D3 — 补丁不可分离。** TB 续接修复（`gen_update_pc`）与 exit-port 可靠 halt 必须作为**同一个补丁 `0008`** 交付。理由：前者单独应用会使既有回归变红（`QEMU-022t` 审阅记录 S1 实验：回退 exit-port 两处改动、仅保留 `translate.c` → 022t 探针全红、`008t` 16–20/38）；两者构成一个原子语义修复。

**D4 — 修订 ADR-0004 D3。** 在 ADR-0004 D3 的「QEMU 行为（机制级冻结）」段新增一条：**写入后立即停止 guest 执行**——exit-port handler 必须在写入退出码后强制 vCPU 返回主循环（`cpu_loop_exit`），不再执行后续 guest 指令。

## Rationale（理由）

**备选方案对比**（`QEMU-022t` architect 规划）：

| 方案 | 机制 | 确定性 | 结论 |
|------|------|--------|------|
| **A（采用）** | exit-port handler 加 `cpu_loop_exit()` | ✅ 首次写即锁定 | `longjmp` 原子性中断执行，唯一能保证「不再执行后续指令」 |
| B | `env->halted` + TB 边界 `EXCP_HLT` | ⚠️ 不立即生效 | `halted` 仅在 TB 边界检查，exit port 写于 TB 中段时后续指令仍可覆盖 |
| C | `cpu_exit()` + `EXCP_INTERRUPT` | ❌ 已证伪 | 即修复前的做法，reviewer 实测 40 次中 5 次错误 |

- **D1 选 A**：只有 `longjmp` 能保证「写入后零后续指令」；B 的检查点在 TB 边界，不能覆盖「exit port 非 TB 末条」的常见情形。
- **D2 必要性**：即便 D1 生效，异常进入路径仍可能在 shutdown 之后被触发（例如同一 TB 内的后续指令已被翻译执行）；显式守卫使「首次写即锁定」成为可依赖契约。
- **D3 必要性**：S1 实验证明两者耦合——`translate.c` 修复使 `env->pc` 前移，暴露了原本被死循环掩盖的 exit-code 竞态。分开交付则中间态不可验证。
- **D4 必要性**：ADR-0004 D3 是机制级冻结契约，本决策为其补全确定性要求，须在同一处留痕。

## Consequences（影响）

**正面**：
- 退出码**确定性**保证（首次写 exit port 即锁定），harness/探针语义验证可靠。
- 消除既有探针的**不确定假失败**（`008t`/`009t`/`010t`/`013t`）。
- 为 `QEMU-021m`（全量语义 PASS）提供确定性前提。

**负面 / 后续约束**：
- `0008` 补丁范围含 3 文件（`translate.c` + `hw/dadao/dadao-machine.c` + `target/dadao/helper.c`），超出原任务书「仅限 `dadao_tr_tb_stop`」的约束——该约束按 D3 修订。
- 所有依赖 exit port 的测试（harness、全部 `min_rom_probe_*`）均**假设**「首次写入即锁定」；新增测试不得依赖「后续写入可覆盖」的行为。
- `cpu_loop_exit()` 属 QEMU 内部 API（非公开 ABI），升级 QEMU baseline（ADR-0002/0008）时须复核其语义。

## 状态说明

**Accepted（2026-09-21）**：D1–D4 由用户**逐条确认**（全部保留）。提案来源：`QEMU-022t` architect 规划（`ses_f3ca1e6a1ffe…`）；问题由 `QEMU-022t` 第 1 轮 reviewer 发现并最小复现（`ses_f3cd22137ffe…`）。
