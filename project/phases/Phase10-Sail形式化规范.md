# Phase 10：Sail 形式化规范

> 对应 DADAO-0628 的 ADR-0011 + SL-001a~003a（Sail 系列）

## 目标

创建 DADAO 的 Sail 形式化可执行规范。Sail 模型从 wiki 规范直接派生，作为第四路验证支线和未来的权威可执行 spec。这是四路差分（interp/QEMU/gem5/Sail）的最终拼图。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 1 | `contracts/isa/spec.md` | ISA 规范 |
| Phase 1 | `verif/opcodes.yaml` | 编码表 |
| Phase 3 | `verif/dadao_interp.py` | Golden model（作为语义参考，不复制代码） |
| Phase 8 | `tests/vectors/isa/*.yaml` | 验证向量 |
| Phase 8 | `verif/run_differential.py` | 差分框架 |
| DADAO-v5/wiki | 11 份文档 | 规范 ground truth |
| DADAO-0628 | `sail/` | Sail 参考实现 |

## 输出文件

```
DADAO-v5/sail/
├── .gitignore
├── build.sh                    # Sail 构建脚本（sail -c → gcc → dadao_sail_sim）
├── dadao.sail_project          # Sail 项目文件
├── dadao_types.sail            # 类型定义
├── dadao_state.sail            # 状态定义（寄存器 + 内存）
├── dadao_insts.sail            # 指令语义（核心）
├── dadao_main.sail             # 顶层 step 循环
└── c_harness/
    ├── dadao_externs.h         # 外部函数声明
    └── dadao_harness.c         # C 仿真器 harness
```

## 子代理分解

### Agent K1：Sail 环境 + 类型和状态

**提示词**：
```
你是 DADAO-v5 的 Sail 工程师。建立 Sail 开发环境并创建类型和状态定义。

1. 安装 Sail（如果未安装）：
   - 从 https://github.com/riscv/sail 获取
   - 按照 README 安装 opam, sail

2. 创建 `dadao_types.sail`：
```sail
/ DADAO 基本类型
type word = bits(32)    / 指令字
type xlen = bits(64)    / 64 位架构
type address = bits(48) / 有效地址

/ 异常类型
union clause ast = Fault : {
    ILLI, UNDI, MALIGN, IALIGN,
    RASOF, RASUF,
    CFXTRAP, CFXMEM, CFXREG
}

/ 条件标志
union clause ast = Condition : {
    N, NN, Z, NZ, P, NP, EQ, NE
}
```

3. 创建 `dadao_state.sail`：
```sail
/ 寄存器状态
register rd : vector(64, dec, xlen)  / 数据寄存器
register rb : vector(64, dec, xlen)  / 基址寄存器
register rf : vector(64, dec, xlen)  / 浮点寄存器
register ra : vector(64, dec, xlen)  / 返回地址栈
register PC : xlen                    / 程序计数器

/ rd0 硬连线为零
function rd0() -> xlen = ZERO

/ rb0 = PC + 4
function rb0() -> xlen = PC + 4

/ 异常状态寄存器
register cur_excp : option(Fault)
```

4. 创建 `dadao.sail_project`：
```
module dadao_types
module dadao_state
module dadao_insts
module dadao_main
```

5. 创建 `build.sh`：sail -c → gcc → 生成 `dadao_sail_sim`

参考 DADAO-0628/sail 的文件结构，但基于 SimRISC 0.5.3 规范重写。
```

### Agent K2：Sail 指令语义

**提示词**：
```
你是 DADAO-v5 的 Sail 指令语义工程师。用 Sail 语言表达 DADAO 指令语义。

读取：
- DADAO-v5/contracts/isa/spec.md
- DADAO-v5/verif/opcodes.yaml
- DADAO-v5/wiki/SimRISC-01~04
- DADAO-0628/sail/dadao_insts.sail（参考）

创建 `dadao_insts.sail`，实现核心指令的语义。

架构模式（以 add-rd-rrrr 为例）：
```sail
/ 从 opcodes.yaml 生成编码子句
mapping clause encdec = (0x1A @ 0x0C @ 0x40 @ 0x42) <-> add_rd_rrrr(rdha, rdhb, rdhc, rdhd)
    if { /* 编码约束 * }

/ 指令语义
function clause execute(add_rd_rrrr(rdha, rdhb, rdhc, rdhd)) = {
    / ILLI 检查：rdha == rd0 且 rdhb == rd0 → ILLI
    / ILLI 检查：rdha == rdhb 且 rdha != rd0 → ILLI
    let val_rdhc = Rd(rdhc);
    let val_rdhd = Rd(rdhd);
    let result_128 = EXTEND128(val_rdhc, signed) + EXTEND128(val_rdhd, signed);
    
    / 写结果（先读再写）
    if rdha != 0 then Rd(rdha) = result_128[127..64];  / 高 64 位
    if rdhb != 0 then Rd(rdhb) = result_128[63..0];    / 低 64 位
}
```

优先实现（形成最小闭环）：
1. **基础算术**：addi-rd-rrii, add-rd-rrrr, sub-rd-rrrr（32 条中的第一子集）
2. **加载/存储**：ldo-rd-rrii, sto-rd-rrii（内存访问 + MALIGN）
3. **控制流**：brz-riii, jump-iiii, call-iiii, ret-riii（分支 + RAS）
4. **fault 探针**：保留编码 UNDI

这个初始子集（约 6-8 条）足以验证 Sail 工具链能否正常工作，
并与其他三路进行差分对齐（参考 ADR-0011 的彩排切片策略）。

后续迭代扩展到全量指令。
```

### Agent K3：Sail C Harness + 差分集成

**提示词**：
```
你是 DADAO-v5 的 Sail 集成工程师。创建 Sail 的 C harness 并接接到差分框架。

1. 创建 `c_harness/dadao_externs.h`：
   - 声明外部函数（寄存器读写、内存读写）
   - 初始化接口

2. 创建 `c_harness/dadao_harness.c`：
   - 测试向量的加载和执行
   - 寄存器状态转储
   - 退出码处理
   - 内存模型（稀疏页表或线性映射）

3. 创建 `tests/scripts/run_sail_test.py`：
   - 调用 dadao_sail_sim
   - 解析输出（寄存器状态、退出码、异常信息）
   - 标准化为差分框架可用的格式

4. 更新 `verif/run_differential.py`：
   - 添加第四列：sail
   - 四路判决逻辑：
     - 4 AGREE → 全部一致
     - 3 AGREE + 1 DIVERGE → 异常列需修复
     - 2+ DIVERGE → 分析偏差模式

5. 输出四路差分报告：
```
=== run_differential (4-way) ===
向量: rd-arith/add/semantic-1
  interp: rd3=0x3  qemu: rd3=0x3  gem5: rd3=0x3  sail: rd3=0x3
  判决: AGREE (4/4)
---
总计: 198/200 AGREE, 0 DIVERGE, 2 SKIP
```

参考 DADAO-0628/sail/c_harness 和 run_sail_test.py。
```

## 阶段验证

- Sail → C 模拟器可编译运行
- Sail 在彩排切片（6-8 指令）上与 interp/QEMU/gem5 差分 AGREE
- `run_differential` 四路输出完整

## 依赖关系

- 依赖 Phase 3（golden model）
- 依赖 Phase 7（QEMU）
- 依赖 Phase 8（差分框架）
- 依赖 Phase 9（gem5）
