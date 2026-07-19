# Phase 9：gem5 第二参考

> 对应 DADAO-0628 的 DG-001a~005a（gem5 系列）+ ADR-0010

## 目标

创建 DADAO 的 gem5 功能模型，作为第三路验证支线。gem5 与 golden model 和 QEMU 三方差分构成更强的验证链，暴露任何两方误读 spec 但一致继承的相关性误差。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 1 | `contracts/isa/spec.md` | ISA 规范 |
| Phase 1 | `verif/opcodes.yaml` | 编码表 |
| Phase 1 | `verif/legality_rules.yaml` | 合法性规则 |
| Phase 3 | `verif/dadao_interp.py` | Golden model 参考 |
| Phase 7 | `components/qemu/patches/` | QEMU 实现参考 |
| Phase 5 | `.work/source/gem5/` | gem5 源码 |
| DADAO-0628 | `components/gem5/patches/` | 9 个参考补丁 |

## 输出文件

```
DADAO-v5/components/gem5/patches/
├── series
├── 0001-dadao-arch-skeleton.patch      # gem5 DADAO 架构骨架
├── 0002-dadao-core-isa.patch           # ISA 执行
├── 0003-dadao-halt-regdump.patch       # 停机 + 寄存器转储
├── 0004-dadao-alu.patch                # ALU 指令
├── 0005-dadao-memory.patch             # 加载/存储
├── 0006-dadao-faults.patch             # 异常处理
├── 0007-dadao-controlflow-ras.patch    # 控制流 + RAS
├── 0008-dadao-se-stack-base.patch      # SE 模式栈
└── 0009-dadao-fixes.patch              # 修复 + 差分适配
```

## 子代理分解

### Agent J1：gem5 目标骨架 + ISA 译码

**提示词**：
```
你是 DADAO-v5 的 gem5 工程师。为 gem5 创建 DADAO 架构目标。

读取：
- DADAO-v5/contracts/isa/spec.md
- DADAO-v5/verif/opcodes.yaml
- DADAO-0628/components/gem5/patches/0001~0002（参考）

1. 创建补丁 0001：架构骨架
   - `src/arch/dadao/Arch.hh`：架构常量
   - `src/arch/dadao/Registers.hh`：寄存器定义
   - `src/arch/dadao/Types.hh`：类型定义
   - `src/arch/dadao/SConscript`：构建集成
   - `src/arch/dadao/Decoder.hh/cc`：译码器
   - `src/arch/dadao/Process.hh/cc`：进程管理

2. 创建补丁 0002：核心 ISA
   - 从 opcodes.yaml 生成译码表
   - 定义静态指令类（StaticInst）
   - 译码树实现
```

### Agent J2：gem5 指令执行

**提示词**：
```
你是 DADAO-v5 的 gem5 指令实现工程师。实现 DADAO 指令的 gem5 执行。

参考：
- DADAO-v5/contracts/isa/spec.md
- DADAO-0628/components/gem5/patches/0003~0009

创建补丁 0003-0009：

**补丁 0003：停机 + 寄存器转储**
- DADAHalt 指令实现（SE 模式下的 exit）
- dumpRegs() 方法，输出所有寄存器状态
- 对接 gem5 的 SE 模式 exit 协议

**补丁 0004：ALU 指令**
- RD 算术（add/sub/mul/div/rem + 各种格式）
- RD 逻辑（and/or/xor/xnor，brrr 格式的 ）
- RD 移位（shlu/shrs/shru）
- RD 扩展（exts/extz）
- RD 比较（cmps/cmpu）
- RD 条件赋值（csn/csz/csp/cseq/csne）

**补丁 0005：加载/存储**
- RD/RB/RA/RF 各 bank 的 ld/st 单/多
- 大端序支持
- 对齐检查 + MALIGN

**补丁 0006：异常处理**
- ILLI（非法指令/操作数）
- UNDI（保留编码）
- MALIGN（对齐错误）
- IALIGN（取指对齐）

**补丁 0007：控制流 + RAS**
- 条件分支（brn/brnn/brz/brnz/brp/brnp）
- 双寄存器分支（breq/brne）
- 跳转（jump）
- 调用（call）+ RAS push
- 返回（ret）+ RAS pop
- PC 相对计算

**补丁 0008：SE 模式栈基础**
- gem5 SE 模式的内存布局
- 栈初始化
- 系统调用存根（stub）

**补丁 0009：差分适配**
- 修复与 golden model 和 QEMU 的不一致
- 确保 gem5 在测试向量上与其他两方一致
```

### Agent J3：gem5 差分集成

**提示词**：
```
你是 DADAO-v5 的差分集成工程师。将 gem5 接入差分验证框架。

1. 创建 `tests/scripts/run_gem5_test.py`：
   - 调用 gem5.opt（或 gem5.fast）
   - 在 SE 模式下运行测试二进制
   - 解析输出（寄存器转储、退出码）
   - 标准化输出格式便于差分比对

2. 更新 `verif/run_differential.py`：
   - 添加第三列：gem5
   - 三路判决逻辑：
     - 3 AGREE → 全部一致
     - 2 AGREE + 1 DIVERGE → 多数一致，异常列
     - 3 DIVERGE → 全部不一致（大概率 spec 问题）

3. 创建 `scripts/check_qfc_coverage.py`：
   - 读取 opcodes.yaml 的 QFC 编码表
   - 对比三路实现分别覆盖了哪些指令
   - 输出覆盖矩阵（类似 inventory.md 但针对实现）

参考 DADAO-0628/DG-005a（gem5 e2e backend）的设计。
```

## 阶段验证

- gem5 SE 模式下可以运行基本测试
- 三路差分（interp/QEMU/gem5）在已有向量上 AGREE
- DIVERGE 情况都有合理解释（如某方尚未实现的指令）

## 依赖关系

- 依赖 Phase 3（golden model）
- 依赖 Phase 7（QEMU）
- 依赖 Phase 8（差分框架）
