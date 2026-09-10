# 合约编写规范

Agent 不能直接读 spec/——它面向人类、存在歧义，需要归一化投影成精确的合约文档。

## 合约文件组织

| 文件 | 内容 |
|------|------|
| `contract-isa.md` | 每条指令的编码、语义、异常，用 § 编号引用 spec/ |
| `contract-abi.md` | 调用约定：参数寄存器、返回值、栈对齐 |
| `contract-elf.md` | ELF 格式：machine ID、重定位类型、endian |
| `contract-sbi.md` | 系统二进制接口功能表 |
| `contract-exception.md` | 系统态异常模型（可标记 deferred） |
| `contract-mmu.md` | 地址转换模型（可标记 deferred） |

## 合约写法要点

- 每条指令独立一个 § 编号
- 编码字段用精确 bit 范围描述：`op[7:0]`、`ha[5:0]`
- 语义用伪代码或自然语言描述，不引用实现代码
- 异常条件用 if-then 明确列出（ILLI/MALIGN/UNDI 等）
- 每个规范性断言标注来源 spec/ 章节（如 `[SimRISC-01 §3.5]`）
- 附录放完整 opcode 表

## 版本管理

- 合约版本号与对应 spec/ 文档一致（如 SimRISC 0.5.3）
- spec/ 更新后走 ADR 变更流程，不能直接跟进
- 合约与 spec/ 冲突时阻断实现，走变更流程，不得由实现自行选择
