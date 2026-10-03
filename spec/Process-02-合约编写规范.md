# 合约编写规范

Agent 不能直接读 spec/——它面向人类、存在歧义，需要归一化投影成精确的合约文档。

## 合约文件组织

| 文件 | 内容 | 状态 |
|------|------|------|
| `contract-isa.md` | 每条指令的编码、语义、异常，用 § 编号引用 spec/ | 现行 |
| `contract-abi.md` | 调用约定：参数寄存器、返回值、栈对齐 | 现行 |
| `contract-elf.md` | ELF 格式：machine ID、重定位类型、endian | 现行 |
| `contract-asm-list.md` | 指令全表（由 `tools/llvm/gen_asm_list.py` 机械生成，无来源头） | 现行（生成投影） |
| `contract-cfx-aliases.md` | cfx 别名表（由 `tools/spec/gen_cfx_aliases.py` 机械生成，无来源头） | 现行（生成投影） |
| `contract-asm.md` | 汇编语言（`spec/Toolchain-01`）的叙述合约 | **缺口** |
| `contract-sbi.md` | 系统二进制接口功能表（`spec/DADAO-22`） | **缺口** |
| `contract-exception.md` | 系统态异常模型（`spec/DADAO-13/23`；可标记 deferred） | **缺口** |
| `contract-mmu.md` | 地址转换模型（`spec/DADAO-12`；可标记 deferred） | **缺口** |

> **缺口**项为**已登记、尚未落盘**的叙述合约（决策 8：缺失即登记，不臆造）；四类型投影落点见 `spec/README.md` 投影表。

## 合约写法要点

- 每条指令独立一个 § 编号
- 编码字段用精确 bit 范围描述：`op[7:0]`、`ha[5:0]`
- 语义用伪代码或自然语言描述，不引用实现代码
- 异常条件用 if-then 明确列出（ILLI/MALIGN/UNDI 等）
- 每个规范性断言标注来源 spec/ 章节（如 `[SimRISC-01 §3.5]`）
- 附录放完整 opcode 表

## 版本管理

- 合约版本号与对应 spec/ 文档一致（如 SimRISC 0.5.4）；机械生成的 `contract-asm-list.md`/`contract-cfx-aliases.md` 无来源头，不参与版本表
- spec/ 更新后重算投影并过漂移门控（轻量修订流程，**不强制记 ADR**；仅「多方案取舍 / 外部契约 / 取向改变」才记，见 `spec/README.md`「规范修订流程」）
- 合约与 spec/ 冲突时阻断实现，按上述轻量修订流程对齐，不得由实现自行选择
