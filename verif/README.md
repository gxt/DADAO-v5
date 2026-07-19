# verif/ — 验证工具

从合约生成机器可读数据，供差分验证工具使用。

## 文件说明

| 文件 | 内容 | 来源 |
|------|------|------|
| `opcodes.yaml` | 每条指令的编码字段、mask、value、变体 | 从 isa-spec.md 逐条提取 |
| `abi.yaml` | 参数寄存器编号、callee-saved 列表、DataLayout | 从 abi-spec.md 转写 |
| `legality_rules.yaml` | 非法编码组合、非对齐访问规则 | 从 isa-spec.md 异常条款提取 |
| `dadao_interp.py` | Python 黄金模型（独立 oracle） | 从 isa-spec.md 派生意 |
| `validate_interp.py` | 在测试向量上运行黄金模型并比对结果 | |
| `run_differential.py` | 四路差分（interp/QEMU/gem5/Sail） | |

## 验证原则

- `opcodes.yaml` 须自检：每条指令的 mask & value 唯一、同 mnemonic 的变体共享基名、无编码空间重叠
- 黄金模型必须从 Wiki 直接派生、由不同于 QEMU 作者的人写
- encoding layer 从 `opcodes.yaml` 生成/交叉校验（不造第三套编码真相）
