# DADAO-v5 golden 模型（SimRISC 0.5.3，M1）

独立的 Python golden 参考模型 + 测试向量运行器。沿用 0628 模式
（`contracts/isa/spec.md` 定义 ISA，`dadao_interp.py` 为真值基准），
按 v5 合约（`.tao/knowledge/contract-isa.md`）重新实现。

| 文件 | 用途 |
|---|---|
| `dadao_interp_v5.py` | Golden 解释器。译码 ← `contracts/opcodes.yaml`；语义 ← contract-isa（每个处理函数都注明合约章节）。导出 `decode`、`check_legality`、`run`。 |
| `validate_interp_v5.py` | 在 `tests/vectors/isa/*.yaml` 上运行 golden。裁决桶：`PASS` / `FAIL` / `SKIP-deferred` / `SKIP-machine`。 |
| `DESIGN.md` | 0.4.1-vs-0.5.3 ISA 对比（§1）、全部设计决策 `D-v5-1`…`D-v5-16`（§2）、验证报告（§3）。 |
| `README.md` | 本文件，快速上手。 |

## 快速上手

```bash
cd tools/golden
python3 validate_interp_v5.py            # 全量：747 条向量
python3 validate_interp_v5.py ../../tests/vectors/isa/reg-arith.yaml   # 单个文件
python3 dadao_interp_v5.py 0x500420C4    # 译码一个指令字
```

期望结果：`TOTAL 747: PASS=696 FAIL=0 SKIP-deferred=8 SKIP-machine=43`。

## API 速览

```python
from dadao_interp_v5 import decode, run

rec, fields = decode(0x500420C4)   # -> ({'insn': 'add.uo-rd', ...}, {'rdha': 1, ...})
state, fault = run(0x500420C4, {'rd': {'rd3': '0x3', 'rd4': '0x4'}})
# 成功时 fault 为 None；state.rd / .rb / .ra / .rf / .pc_next 保存结果。
# 异常时 state 为精确的执行前快照。
```

## 独立性合约

golden 只读 `contracts/opcodes.yaml`（译码）与合约/规范正文（语义），
绝不读 QEMU、LLVM 或向量生成器——只有这样，`golden vs QEMU` 差分才不成循环论证。
