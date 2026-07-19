# 合约编写规范

Agent 不能直接读 Wiki——Wiki 是给人看的，有歧义。需要把 Wiki 内容归一化投影成精确的合约文档。

## 合约文件组织

| 文件 | 内容 |
|------|------|
| `isa-spec.md` | 每条指令的编码、语义、异常，用 § 编号引用 Wiki |
| `abi-spec.md` | 调用约定：参数寄存器、返回值、栈对齐 |
| `elf-spec.md` | ELF 格式：machine ID、重定位类型、endian |
| `sbi-spec.md` | 系统二进制接口功能表 |
| `exception-contract.md` | 系统态异常模型（可标记 deferred） |
| `mmu-contract.md` | 地址转换模型（可标记 deferred） |

## 合约写法要点

- 每条指令独立一个 § 编号
- 编码字段用精确 bit 范围描述：`op[7:0]`、`ha[5:0]`
- 语义用伪代码或自然语言描述，不引用实现代码
- 异常条件用 if-then 明确列出（ILLI/MALIGN/UNDI 等）
- 每个规范性断言标注来源 Wiki 章节（如 `[SimRISC-01 §3.5]`）
- 附录放完整 opcode 表

## 版本管理

- 合约版本号与对应 Wiki 文档一致（如 SimRISC 0.5.3）
- Wiki 更新后走 ADR 变更流程，不能直接跟进
- 合约与 Wiki 冲突时阻断实现，走变更流程，不得由实现自行选择
