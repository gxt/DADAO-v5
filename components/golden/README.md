# M1 与 FP golden：用途、用法和当前边界

完整逐条定义见 [逐条指令 golden 说明](INSTRUCTION_REFERENCE.md)：按当前指令身份逐项说明操作数、计算步骤、异常、算例和依据；伪代码中使用的函数、常量与记号统一在「共同规则 §10」提前声明。

这个目录提供一个 **Python 单步参考模型**：输入一条机器指令和执行前状态，输出执行后状态或架构异常。当前覆盖原有整数、访存、寄存器传送、控制流，以及浮点合约中的 66 条 RF/FCSR 指令（含取整、最小/最大值与融合乘加）。

“golden”表示参考答案，**不表示这份程序已经证明完全正确**。本模型的语义依据是当前仓库的 SimRISC 规范及 ISA 合约，不是宿主机计算结果，也不是 QEMU/LLVM 的实现。浮点有限值运算使用独立整数/有理数 oracle；开放边界仍不能用于宣称完整 IEEE 754-2019 符合性。

## 先看这三个边界

1. **覆盖范围明确。** 66 条 `scope: fp` 指令已纳入；特权系统指令、原子指令和 `fence` 仍未实现，遇到这些已定义指令抛出 `Unsupported`，不会伪装成架构的 ILLI。
2. **只模拟指令效果。** 不模拟地址权限、MMU、ROM、设备和异常处理入口。内存是按字节存储的大端稀疏内存；没有预置的字节按 0 读取，这是测试模型约定，不是硬件保证。
3. **规范开放点不输出猜测答案。** `rootn(-0,2)` 与 `ftsclb/fosclb` 的 NaN/Inf/溢出/下溢边界按具体输入报 `SpecificationGap`；f2i 已按新规范对 finite inexact 置 NX。`sub.uo` 已按 ADR-0049 返回借位 0/1。详见 [设计说明](DESIGN.md#subuo-的借位语义)。

## 文件分工

| 文件 | 作用 |
| --- | --- |
| `dadao_interp_v5.py` | 译码、合法性检查和单步执行 |
| `fp_ref.py` | binary32/binary64 位级分类、精确有理数运算、显式舍入及异常标志 |
| `validate_interp_v5.py` | 读取仓库 YAML 向量，比较身份、异常、寄存器、内存和 PC |
| `test_interp_v5.py`、`test_fp_v5.py` | 从规范独立推导的整数与浮点模型边界测试；不调用 QEMU/LLVM |
| `test_validator_v5.py` | 故意给错身份、结果、PC 等，确认验证器确实能拒绝 |
| `check_golden.py` | 可复现的检查入口，含临时副本反例注入 |
| `DESIGN.md` | 最终实现规则、公式、例子、范围及待裁定项 |

## 在仓库根目录运行

需要 Python 3 和 PyYAML。下面命令都不编译 LLVM/QEMU。

```bash
# 译码 add.uo {rd1, rd2}, rd3, rd4
python3 -B ./components/golden/dadao_interp_v5.py 0x500420C4

# 检查模型及验证器（期望退出码 0）
python3 -B -m unittest discover -s components/golden -p 'test_*v5.py' -v

# 回放全部仓库 ISA 向量；有真实分歧时退出码为 1
python3 -B ./components/golden/validate_interp_v5.py

# 也可只回放一个文件
python3 -B ./components/golden/validate_interp_v5.py ./tests/inst/base/ctrl-ret.yaml

# 独立测试 + 反例注入（期望退出码 0）
python3 -B ./components/golden/check_golden.py
```

**全量回放当前无 FAIL。** 合并 `tests/inst` 与新 FP/scaleB 向量后，共回放 730 条：编码通过 173、执行通过 500、FAIL 0、跳过 57（5 deferred + 4 SKIP-scope + 48 machine），退出码 0。FP 的 fma/rnd/minmax 仍由独立单测覆盖；跳过项不计作验证通过。

## 已知不足

- **f2i 已按新规范实现**：finite inexact 置 NX，不再抛 `FPGap`；NaN/Inf/越界按当前实现饱和 + NV。NaN 的符号位与无符号 `-Inf` 饱和方向仍缺少独立向量。
- **scaleB 已改为 `rdHD` 整数指数**：`ftsclb/fosclb` 从 `rd` 组读 signed 64 位指数（`rd0=0`），`tests/inst/fp/scaleb.yaml` 已覆盖；旧 `rfHD` 路径不再接受。
- **FP 向量仍不完整**：`tests/inst/fp/` 只有 scaleb；fma/rnd/minmax 只有单测和 C 探针，没有共享 YAML。
- **门控已补**：新增 `check-golden`（单测 + `tests/inst` 回放 + `check_golden` + 生成器 `--check`），纳入 `make check`。
- **注入/审计**：`check_golden.py` 的模型注入仍只覆盖标量算术；`009t-audit.py` 对 `ctrl-br`、`ldm.o`、`shl.*` 有既存偏差。
- **范围外**：M9 标量（rev/rol/ctlz/cttz/ctpop/clmul/lr/sc）、特权/原子/fence/trap/cfx 和 MMU/权限/异常入口不在模型内。

## 未来扩展：i128/i256

`sub.uo` 的借位和 `add.uo` 的进位是 64 位多字运算的基元；i128/i256 应由多条 64 位加减链组合，不改变单条 `sub.uo` 的借位语义。`cmp` 结果写满 64 位，便于后续宽比较。

## 最小 API 示例

让 Python 能从 `components/golden` 导入模块后：

```python
from dadao_interp_v5 import run

state, fault = run(
    0x500420C4,
    {"rd": {"rd3": "0x3", "rd4": "0x4"}},
)
assert fault is None
assert state.rd[1] == 0  # 结果高 64 位
assert state.rd[2] == 7  # 结果低 64 位

# 成功后的状态可以直接作为下一步的输入。
next_state, fault = run(0x77880000, state=state)  # swym 0
```

默认执行地址为当前向量约定的 `0xFC0000000000`，不是芯片复位地址。

- 成功：`fault is None`；`state.pc` 和 `state.pc_next` 是下一条指令的低 48 位取指地址，`state.rb[0]` 保留完整 64 位控制流值。
- 架构异常：返回 `(原状态, 异常名称)`，本步不提交任何修改。
- 模型未实现：抛出 `Unsupported`；规范不足以确定答案：抛出 `SpecificationGap`。两者都不是架构异常。
- 输入格式错误：抛出 `ValueError`，例如超过 32 位的机器指令。不能依靠截断错误输入继续执行。

## 如何读验证结果

| 输出 | 实际证明了什么 |
| --- | --- |
| `PASS-encoding` | 指令身份与编码一致，静态操作数合法；**没有执行语义检查** |
| `PASS-execution` | 执行结果满足本条断言；异常用例还检查整份状态不变 |
| `FAIL` | 真正的不一致、无效输入或规范阻断，需要调查 |
| `SKIP-deferred` | 向量已明确暂缓，本次没有验证 |
| `SKIP-scope` | 指令超出本模型实现范围，本次没有验证 |
| `SKIP-machine` | 期望地址权限/映射异常，本模型无法验证 |

退出码 0 只说明所选输入中没有 FAIL 且至少有一个检查通过，不代表所有指令、所有输入已经穷尽验证。空文件、输入错误或全是跳过项都会非零退出。

课堂汇报可按三个问题展开：**我的参考答案从哪里来；哪些行为已被独立测试；哪些分歧和能力边界仍然存在。** 不应把编码通过数、跳过数或宿主机一致性当作语义正确性的证明。


i128 i256支持sub.uo
llvm binary128可以打开
加入ieee2019 浮点标准（精度）
浮点数
测试数据
