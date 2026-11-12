# ADR-0040: `ret` 将 `rb0` 高 16 位清零

**状态**：Accepted
**日期**：2026-10-29
**关联**：DADAO-v5 `8f669181`、SimRISC `0.5.6-rc`、冻结机器契约 `0.5.5`、`ADR-0009`、`ADR-0012`、`RTL-011t`

## Context（背景）

`ret` 从返回地址栈（Return Address Stack，RAS）取得低 48-bit
返回地址，但 `SimRISC-00/06` 没有完整规定 `ret` 后
`rb0[63:48]` 的取值。

现有正文和决策的边界如下：

- `SimRISC-00 §基址寄存器`规定 `rb0[63:48]` 初值为 0，并由控制流
  指令的硬件写入，但没有单列 `ret` 的更新公式。
- `SimRISC-06 §函数返回`规定 `ret` 从 RAS 弹出返回地址并跳转，
  没有说明高 16 位如何处理。
- `contract-isa.md §8.5`写“IP = 弹出的返回地址”，没有区分高低位。
- `ADR-0012 D8.3`明确排除 `ret`；D8.5 只规定文档归位；D8.7 只规定
  返回值作为地址使用时取低 48 位。
- QEMU（软件模拟器）参考实现 `QEMU-031t` 的
  `trans_ret_riii_ra` 采用 `zero_extend48(ra63[47:0])`，即高 16 位
  清零。
- 现有控制流向量只断言 `expected_pc`，没有直接断言 `ret` 后
  `rb0[63:48]`。

因此，本 ADR 记录 DADAO-v5 为 RTL（register-transfer level，寄存器
传输级）实现所选定的本地规范缺口处理方式，不把该选择声称为上游
正文已有明文。

## Decision（决策）

**D1：`ret` 使用零扩展的 48-bit 返回地址更新 `rb0`。**

成功弹栈并取得返回地址 `poppedReturnAddress` 后：

```text
rb0[47:0]  = poppedReturnAddress[47:0]
rb0[63:48] = 0
```

等价写法：

```text
rb0 = zero_extend48(poppedReturnAddress[47:0])
```

该规则：

1. 适用于 D2、D3、D4b-count1 和 D4b-countN 的成功弹栈路径；
2. 与 `ret` 的可选 RD（数据寄存器）返回值写回在同一提交边界生效；
3. 在 RASUF 或 MemRAS（内存返回地址栈）访问 fault 时不得生效；
4. 与当前 QEMU 参考实现保持 bit-exact（位级完全一致）；
5. 是 DADAO-v5 的本地实现决策，不修改 `spec/`，也不声明上游
   `SimRISC-00/06` 已明文规定该高位行为。

## Rationale（理由）

- 当前 QEMU 参考实现已经采用高 16 位清零；RTL 跟随它可以直接比较
  guest 可见状态，避免两个执行模型在 `rb0` 高位上分叉。
- RAS 条目只保存低 48-bit 返回地址，高 16 位是递归计数而不是
  地址内容，因此不能从 RA 条目恢复返回地址的高 16 位。
- 若保留“上一条指令的 `rb0[63:48]`”，`ret` 的结果会依赖非局部历史；
  清零则具有确定、可复现的语义。
- 地址总线只使用低 48 位；本决策保留这一取指语义，同时明确完整
  64-bit `rb0` 的结果。

被否方案：

- **保留旧高 16 位**：会与当前 QEMU 参考实现不一致，且产生非局部
  历史依赖。
- **直接从 RA 条目复制 64 位**：RA 条目高 16 位是递归计数，不是
  返回地址，语义错误。
- **等待上游正文后再定义**：会阻塞 RTL-011t；本 ADR 先固定项目实现，
  若上游以后给出不同规范，再用新 ADR 取代或修订。

## Consequences（影响）

- `RTL-011t` 的 `D1-CF-02` 从待决变为已冻结。
- RTL 中不得只更新 48-bit 取指地址寄存器而遗漏 64-bit `rb0` 高位的
  清零；需要显式保存或提交 `rb0[63:48] = 0`。
- 独立 oracle 和 Chisel（硬件构造语言）测试必须直接断言 ret 后完整
  64-bit `rb0`，不能只比较 `expected_pc`。
- D2、D3、D4b-count1、D4b-countN 和 fault 无提交路径都必须覆盖。
- 若上游规范后续明确规定不同行为，本 ADR 应标记 `Superseded` 或新增
  修订 ADR，不直接改写本决策。

## 状态说明

用户于 2026-10-29 确认采用与当前 QEMU 参考实现一致的方案，并授权创建
本 ADR 和 `RTL-011t` 任务书。确认内容为：

> `ret` 后将 `rb0[63:48]` 清零，即将弹出的 48-bit 返回地址零扩展到
> 64-bit 写入 `rb0`。

因此状态置为 `Accepted`。本 ADR 不修改上游规范正文。

## 参考

- `spec/SimRISC-00-指令系统设计.md`
- `spec/SimRISC-06-控制流.md`
- `.tao/contracts/contract-isa.md`
- `.tao/adr/adr-0009-qemu-harness-methodology.md`
- `.tao/adr/adr-0012-simrisc-0.5.4-update.md`
- `components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`
- `tools/testcases/generate_ctrl_jump_call_ret.py`
- `.tao/tasks/rtl/RTL-011t-控制流call-ret与RAS.md`
