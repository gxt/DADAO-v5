# Phase 3：Python Golden Model

> 对应 DADAO-0628 的 ADR-0009 M2a + DL-040b（golden model）

## 目标

创建从 wiki 规范直接派生的 Python ISA 模拟器（golden model），作为所有其他实现的独立 oracle。模型必须从 `contracts/isa/spec.md` + `opcodes.yaml` 派生语义，不复制 QEMU 或 LLVM 的实现逻辑。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 1 | `contracts/isa/spec.md` | ISA 语义规范 |
| Phase 1 | `verif/opcodes.yaml` | 编码表 |
| Phase 1 | `verif/legality_rules.yaml` | 合法性规则 |
| Phase 2 | `tests/vectors/schema.md` | 向量格式 |
| Phase 2 | `tests/vectors/isa/*.yaml` | 验证输入 |
| DADAO-v5/wiki | `DADAO-11-AEE-应用程序运行环境.md` | RAS 行为、r0 特殊语义 |
| DADAO-0628 | `verif/dadao_interp.py` | 参考实现（注意是 SimRISC 0.4.1） |
| DADAO-0628 | `verif/validate_interp.py` | 验证器参考 |
| DADAO-0628 | `code-agent/knowledge/05-harness-binary-protocol.md` | 测试协议 |

## 输出文件

```
DADAO-v5/verif/
├── dadao_interp.py          # Python golden model
├── validate_interp.py       # 向量验证器
└── run_differential.py      # 差分运行器（骨架，QEMU 完成后扩展）
```

## 子代理分解

### Agent D1：Python Golden Model 核心

**职责**：创建完整的 Python ISA 模拟器

**提示词**：
```
你是 DADAO-v5 的黄金模型工程师。从 wiki 规范创建 Python ISA 模拟器。

读取输入文件：
- DADAO-v5/contracts/isa/spec.md（ISA 语义）
- DADAO-v5/verif/opcodes.yaml（编码表）
- DADAO-v5/verif/legality_rules.yaml（合法性规则）
- DADAO-v5/wiki/DADAO-11-AEE-应用程序运行环境.md（RAS 行为）
- DADAO-0628/tools/dadao_interp.py（参考，不复制代码）

创建 `verif/dadao_interp.py`，包含：

1. **Fault 类**：所有异常类型
   - ILLI（非法指令）
   - UNDI（未定义编码）
   - MALIGN（非对齐访存）
   - IALIGN（取指未对齐）
   - RASOF（RAS 上溢）
   - RASUF（RAS 下溢）
   - FPEXCP（浮点异常，预留）
   - CFXREG（核芯功能扩展寄存器异常，预留）

2. **State 类**：架构状态
   - `rd[64]`, `rb[64]`, `rf[64]`, `ra[64]`（四组寄存器）
   - `mem`（字节数组，48 位地址空间 = 2^48 太大，用 dict 稀疏存储）
   - `pc`（当前程序计数器，48 位有效）
   - `rd0` 硬连线为 0（写忽略）
   - `rb0` = pc + 4（硬件维护、只读）
   - `rf0` = FCSR（浮点状态寄存器，含舍入模式和异常标志）
   - 复位状态：所有寄存器为 0，pc 为 0xFFFF_FFFF_0000

3. **decode()**：表驱动解码
   - 从 `opcodes.yaml` 加载 mask/value 表
   - 对输入 32 位 word 进行逐条匹配
   - 匹配到编码 → 返回 (mnemonic, format, operands)
   - 匹配不到 → 返回 UNDI

4. **check_legality()**：静态合法性检查
   - 对每条指令根据 `opcodes.yaml` 的 legality 规则检查
   - 规则包括：rd0/rb0 目的、immu6=0、range overflow、SBZ 等
   - 同时检查 opcodes.yaml 中未记录的隐含规则

5. **_exec_<mnemonic>()**：指令执行（核心）

   必须实现以下指令族：

   **RD 算术**（6 条）：
   - `add-rd-rrrr`：128 位加法，双目标（rdha=高64，rdhb=低64）
   - `sub-rd-rrrr`：128 位减法，双目标
   - `muls-rd-rrrr`  `mulu-rd-rrrr`：128 位乘法
   - `divs-rd-rrrr`  `divu-rd-rrrr`：64 位除法，双目标（rdha=余数，rdhb=商）
   - `addi-rd-rrii`：64 位加立即数（符号扩展 12 位）
   - `add-rd-orrr`  `sub-rd-orrr`：带  的加减
   - `muls-rd-orrr`  `mulu-rd-orrr`：带  的乘
   - `divs-rd-orrr`  `divu-rd-orrr`：带  的除
   - `rems-rd-orrr`  `remu-rd-orrr`：带  的取余

   **RD 比较**（4 条）：
   - `cmps-rd-rrii`  `cmpu-rd-rrii`：比较，结果 -1/0/1
   - `cmps-rd-orrr`  `cmpu-rd-orrr`：带  的比较

   **RD 逻辑**（4 条）：
   - `and-rd-orrr`  `orr-rd-orrr`  `xor-rd-orrr`  `xnor-rd-orrr`：按  操作，高位不变

   **RD 移位**（6 条）：
   - `shlu-rd-orrr`  `shrs-rd-orrr`  `shru-rd-orrr`：寄存器移位量
   - `shlu-rd-orri`  `shrs-rd-orri`  `shru-rd-orri`：立即数移位量

   **RD 扩展**（4 条）：
   - `exts-rd-orrr`  `extz-rd-orrr`：寄存器指定最高位
   - `exts-rd-orri`  `extz-rd-orri`：立即数指定最高位

   **RD 条件赋值**（5 条）：
   - `csn-rd-rrrr`  `csz-rd-rrrr`  `csp-rd-rrrr`：if (rdha N/Z/P) rdhb=rdhc else rdhb=rdhd
   - `cseq-rd-rrrr`  `csne-rd-rrrr`：if (rdha==/!=rdhb) rdhc=rdhd

   **RD 加载/存储**（12+12 条）：
   - `ldbs`  `ldbu`  `ldws`  `ldwu`  `ldts`  `ldtu`  `ldo`：单 load
   - `stb`  `stw`  `stt`  `sto`：单 store
   - `ldmbs`~`ldmo`、`stmb`~`stmo`：多 load/store

   **RB 操作**（12 条）：
   - `add-rb-orrr`  `sub-rb-orrr`：48 位加法，高 16 位不变
   - `addi-rb-rrii`：48 位加立即数
   - `cmp-rb-orrr`：48 位无符号比较
   - `rela-rb-riii`：PC 相对寻址（imms18 << 12 + PC[47:12]<<12）
   - `ldo-rb-rrii`  `sto-rb-rrii`：RB 存取
   - `ldmo-rb-rrri`  `stmo-rb-rrri`：RB 多存取
   - `setzw-rb-rwii`  `orw-rb-rwii`  `andnw-rb-rwii`：RB wyde 立即数

   **RA 操作**（6 条）：
   - `ldo-ra-rrii`  `sto-ra-rrii`  `ldmo-ra-rrri`  `stmo-ra-rrri`
   - `rd2ra-orri`  `ra2rd-orri`

   **RF 操作**（4 条）：
   - `ldt-rf-rrii`  `stt-rf-rrii`（单精 32 位）
   - `ldo-rf-rrii`  `sto-rf-rrii`（双精 64 位）
   - `ldmt-rf-rrri`  `stmt-rf-rrri`（多单精）
   - `ldmo-rf-rrri`  `stmo-rf-rrri`（多双精）
   - `rf2rd-orri`  `rd2rf-orri`  `rf2rf-orri`

   **控制流**（10 条）：
   - `brn`  `brnn`  `brz`  `brnz`  `brp`  `brnp`：单寄存器分支（riii）
   - `breq`  `brne`：双寄存器分支（rrii）
   - `jump-iiii`  `jump-rrii`：无条件跳转
   - `call-iiii`  `call-rrii`：函数调用 + RAS push
   - `ret-riii`：函数返回 + RAS pop + 返回值赋值

   **浮点转换**（20 条，先 skeleton，M3 填充语义）：
   - ft2fo/fo2ft/ft2it/.../uo2fo

   **浮点运算**（~20 条，先 skeleton，M3 填充语义）：
   - ftadd/ftsub/.../fosgnj

   **系统指令**：
   - `swym-iiii`：NOP
   - `illi-oiii`：触发 ILLI
   - `fence-oiii`：NOP（无模型需要）
   - `lro_*`  `sco_*`：LR-SC（skeleton）
   - `cfx2rd`  `cfx2rc`  `cfxld`  `cfxst`  `trap`  `escape`：skeleton

6. **RAS 实现**（关键——这是 DADAO 最重要最复杂的特性之一）：
   - push（call 时）：检查 ra63 引用计数，决定直接压栈/递归递增/移位压栈/MemRAS
   - pop（ret 时）：检查 ra63 引用计数，决定递减/移位弹栈/MemRAS
   - RASOF/RASUF 检查
   - MemRAS 支持（ra0 控制）

7. **RB 宽度模型**：
   - 寄存器物理 64 位，有效地址 48 位
   - 内存→RB/块复制→RB：全 64 位覆盖
   - RB 算术：仅 mod bits[47:0]，bits[63:48] 保持
   - RB 比较：仅比较低 48 位

8. **对齐检查**：
   - ldo/sto：8 字节对齐
   - ldts/stt/ldtu：4 字节对齐
   - ldws/stw/ldwu：2 字节对齐
   - ldbs/stb/ldbu：无要求

9. **step()  run()** 接口：
   - step()：取指 → 解码 → 合法性检查 → 执行 → 更新 PC
   - run(nsteps=1)：连续执行 N 步
   - run_until(addr)：执行到指定地址

实现原则：
- **从 spec.md 派生意，不从 DADAO-0628 复制代码**
- 每条 exec 函数标注对应的 spec 章节（如 `# spec.md §3.5`）
- 先读全部源操作数，再写结果（确定性行为）
- 所有 ILLI/MALIGN 检查在修改状态前完成（精确异常）

参考 DADAO-0628 的 dadao_interp.py 的架构风格但基于 SimRISC 0.5.3 重新实现。
```

### Agent D2：向量验证器

**职责**：创建 `validate_interp.py`

**提示词**：
```
你是 DADAO-v5 的验证工程师。创建 golden model 的向量验证器。

读取：
- DADAO-v5/verif/dadao_interp.py（刚创建的 golden model）
- DADAO-v5/tests/vectors/schema.md（向量格式）
- DADAO-v5/tests/vectors/isa/*.yaml（测试向量）

创建 `verif/validate_interp.py`，功能：

1. 加载所有 YAML 测试向量文件
2. 对每个向量：
   a. 从 input_state 初始化 State
   b. 从 encoding.word 解码指令
   c. 执行指令
   d. 比较实际结果 vs expected_state/expected_fault
3. 输出分类结果（类似 DADAO-0628 的实现）：
   - PASS：状态完全匹配
   - MISMATCH：状态不匹配
   - SKIP-unsupported：模型尚未实现的指令
   - SKIP-harness：需要 harness 环境的测试
4. 分支向量特殊处理：根据 branch_behavior 判断 taken/not_taken
5. call/ret 往返测试
6. 统计通过率报告

输出示例：
```
=== validate_interp ===
rd-arith.yaml:        42/45 PASS, 0 MISMATCH, 3 SKIP-unsupported, 0 SKIP-harness
control-flow.yaml:    28/30 PASS, 0 MISMATCH, 2 SKIP-unsupported, 0 SKIP-harness
...
TOTAL:                320/350 PASS, 0 MISMATCH, 30 SKIP-unsupported, 0 SKIP-harness
```

参考 DADAO-0628/tools/validate_interp.py 的实现风格。
```

### Agent D3：差分运行器骨架

**职责**：创建 `run_differential.py`（骨架，QEMU 完成后扩展）

**提示词**：
```
你是 DADAO-v5 的差分测试工程师。创建差分运行器的骨架版本。

读取：
- DADAO-0628/tools/run_differential.py（参考）

创建 `verif/run_differential.py`，初始功能：

1. 支持单模型运行（仅 golden model）
2. 读取 tests/vectors/isa/*.yaml 测试向量
3. 对每个向量，用 golden model 运行并记录结果
4. 结果格式标准化（JSON 序列化），便于后续 QEMU/gem5 列加入
5. 输出表格：AGREE  DIVERGE  SKIP

初始版本只有 golden model 一列，但数据结构设计为可扩展：
```python
results = {
    "vector_id": "...",
    "interp": {"state": {...}, "fault": None, "exit_code": 0},
    "qemu": None,      # 后续添加
    "gem5": None,      # 后续添加
    "sail": None,      # 后续添加
    "verdict": "REFERENCE"  # 只有一列时标注为 REFERENCE
}
```

参考 DADAO-0628 的 run_differential.py 对接。
```

## 阶段验证

- `validate_interp.py` 对 Phase 2 创建的向量运行，PASS 率 ≥ 90%（未实现指令标注 SKIP）
- 手动构造 5 个简单的汇编测试（直接调用 interp API），结果正确
- RAS push/pop 行为与 AEE §返回地址栈 流程完全一致

## 依赖关系

- 依赖 Phase 1（spec.md、opcodes.yaml）
- 依赖 Phase 2（测试向量）
- 是 Phase 6/7/8/9 差分验证的 oracle
