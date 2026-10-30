# ADR-0046: CFX 寄存器实现裁剪与 usage profile

**状态**：Proposed
**日期**：2026-10-30
**关联**：ADR-0045（权限）、ADR-0043（启动）；`spec/DADAO-12` §3/§4

## Context（背景）

spec 为每个 cfx 定义 cg0–cg7（及 cfx0–cfx3 的 cg8/rc1），但具体 cfx 不需要全部实现。单用户态测试可以完全不做 S-mode 相关寄存器；Linux 路线才需要完整能力。现在预删 spec 定义，后面 Linux 可能又需要；需要区分“架构定义”和“实现裁剪”。

## Decision（决策）

- **D1 spec 保持完整**：cg0–cg7 及必要的 cfx 专有寄存器继续在 spec 定义；不因当前测试机不用而删除架构定义。
- **D2 实现可裁剪**：具体 cfx 可以只实现子集；未实现/不存在的 cg/rc 访问 → `CFXREG`；具体哪些 optional 由 implementation profile 决定。
- **D3 统计时机**：Linux 在目标/测试机启动并运行代表性负载后，统计各 cfx 实际访问的 cg/rc。
- **D4 profile 字段**：cfx name、cg、rc、用途、启动期/内核/驱动/用户态是否使用、Linux 版本/配置、建议 required/optional、证据。
- **D5 profile 只指导实现**：不修改架构语义、不删除 spec 正文；若某寄存器长期未使用，可标 optional，但仍保留定义。
- **D6 例外**：已有明确废弃的寄存器（如 cfxld/cfxst 删除后的 cg7 SRAM 控制）按独立 ADR/任务删除，不混入 profile。

## Rationale（理由）

架构定义与实现裁剪分离，避免单用户测试把 Linux 需要的能力删掉，也避免实现者被未使用寄存器拖累。Linux 实测 profile 比提前猜测可靠。

## Consequences（影响）

- 需要维护 `.tao/knowledge/cfx-register-usage.md` 统计表；
- 具体 cfx 实现可按 profile 省略 optional 寄存器；
- spec 不因 profile 变化而反复删改；
- 未实现寄存器必须明确 `CFXREG`，不能静默成功。

## 状态说明

方法已确认；usage 表待 Linux 启动后填充。
