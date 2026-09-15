# Independent Test Vectors

`tests/vectors/` 存放 M1 scope 的独立测试向量，作为 LLVM/QEMU/gem5 的**独立 oracle**。

- 向量**独立派生自锁定的规范与合约**（`spec/`、`.tao/knowledge/contract-isa.md`、
  `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、
  `.tao/knowledge/adr-0004-test-machine.md`），**不从 LLVM 汇编输出或 QEMU 运行结果生成**。
- 每条向量记录输入状态、编码字、期望输出状态/PC/异常，期望值可回溯到 `spec_cite`。
- 覆盖率主键为 `(insn, format)`（等价机器键 `(op, ha)`）；M1 scope 以
  `contracts/opcodes.yaml` 的 `excluded_m1 != true` 为唯一判据（178 条）。

## 文件

| 文件 | 说明 |
|------|------|
| `schema.md` | 向量 YAML 字段规范（含 `expected_pc`、class 定义、encoding 豁免、deferred 规则） |
| `inventory.md` | M1 覆盖矩阵（以 `(insn, format)` 为行，含 `format`/`file` 列与 deferred reason） |
| `isa/*.yaml` | 向量数据（由 `TESTCASES-003t`~`007t` 生成） |

## 校验

```
python3 tools/testcases/validate_vectors.py   # 或 make check
```

校验 schema 字段、class/fault 取值、编码 mask/value、`expected_pc`、`inventory`
同步与覆盖率；有错误时 `exit(1)` 并列出文件 + case 序号。
