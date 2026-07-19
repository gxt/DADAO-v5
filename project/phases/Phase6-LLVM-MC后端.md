# Phase 6：LLVM MC 后端

> 对应 DADAO-0628 的 DL-007a~012a + DL-031a~039c（LLVM MC 补丁系列）

## 目标

创建 LLVM MC（Machine Code）后端，支持 DADAO 指令的汇编和反汇编。这是 Phase 10 CodeGen 的基础。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 1 | `contracts/isa/spec.md` | ISA 规范 |
| Phase 1 | `verif/opcodes.yaml` | 编码表 |
| Phase 1 | `verif/legality_rules.yaml` | 合法性规则 |
| Phase 4 | `contracts/abi/spec.md` | ABI 规范 |
| Phase 4 | `contracts/elf/spec.md` | ELF 规范 |
| Phase 5 | `manifests/components.lock.toml` | LLVM commit |
| Phase 5 | `.work/source/llvm/` | 已获取的 LLVM 源码 |
| DADAO-v5/wiki | `AGENTS.md` | 命名约定（/wpN/格式） |
| DADAO-0628 | `components/llvm/patches/` | 22 个参考补丁 |
| DADAO-0628 | `tests/lit/MC/Dadao/` | LIT 测试参考 |

## 输出文件

```
DADAO-v5/components/llvm/patches/
├── series                    # 补丁顺序
├── 0001-dadao-triple-registration.patch     # Triple: dadao-unknown-elf
├── 0002-dadao-target-skeleton.patch         # 目标骨架（DadaoTargetMachine等）
├── 0003-dadao-register-info.patch           # 寄存器描述 (.td + .cpp)
├── 0004-dadao-instrinfo.patch               # 指令信息表 (.td)
├── 0005-dadao-asmparser.patch               # 汇编器解析器
├── 0006-dadao-disassembler.patch            # 反汇编器
├── 0007-dadao-mccodeemitter.patch           # 编码发射器
├── 0008-dadao-mc-control-flow.patch         # 控制流指令 MC
├── ... 后续补丁按需拆解
```

## 子代理分解

这是一个大阶段，建议拆分为 3 个子阶段，每个子阶段可并行处理。

### Agent G1：Triple + 目标骨架 + 寄存器

**职责**：创建 LLVM Triple 注册、目标骨架、寄存器信息

**提示词**（可拆为 3 个子任务，每任务 1 个 agent）：

**子任务 G1a - Triple 注册**：
```
你是 DADAO-v5 的 LLVM 后端工程师。在 LLVM 中注册 DADAO triple。

基于 LLVM commit 和 DADAO-v5 规范，创建补丁 0001：

在 LLVM 源码中添加：
1. `llvm/include/llvm/TargetParser/Triple.h`：添加 `dadao` 架构枚举
2. `llvm/lib/TargetParser/Triple.cpp`：添加 `dadao` 到 Triple::getArchTypeName 等
3. 定义 Triple 为 `dadao-unknown-elf`（大端序）

EM_DADAO = 0x0DA0（参考 DADAO-0628/DL-001a）

参考 DADAO-0628 的 0001-dadao-triple-registration.patch，但基于当前 LLVM 版本的 API。
```

**子任务 G1b - 目标骨架**：
```
创建补丁 0002：DADAO 目标骨架

在 `llvm/lib/Target/Dadao/` 下创建：
1. `DadaoTargetMachine.cpp/h`：目标机器，DataLayout = "E-m:e-i64:64-n64-S64"
2. `DadaoSubtarget.cpp/h`：子目标定义
3. `Dadao.h`：目标头文件
4. `CMakeLists.txt`、`LLVMBuild.txt`：构建集成
5. `Dadao.td`：目标描述顶级文件
6. `DadaoRegisterInfo.td`：寄存器定义
   - RD 寄存器组（rd0-rd63，rd0=zero）
   - RB 寄存器组（rb0-rd63，rb0=rbip）
   - RF 寄存器组（rf0-rf63，rf0=FCSR）
   - RA 寄存器组（ra0-ra63，ra63=rasp）
```

**子任务 G1c - 寄存器信息**：
```
创建补丁 0003：寄存器信息 + 指令格式定义

在 `DadaoRegisterInfo.td` 中：
- 定义寄存器类（GPRD, GPRB, GPRF, GPRA）
- 子寄存器关系（如 i8 时使用 GPRD 的低 8 位）
- 寄存器别名

在 `DadaoInstrFormats.td` 中：
- 定义所有 12 种指令格式（rrrr/rrri/rrii/riii/iiii/rwii/orrr/orri/oiii/ciii/crrr/crii）
- 定义操作数字段（, cfxcode, wyde_pos, imm等）

参考 DADAO-0628 的 0003-dadao-register-info.patch 和 0004-dadao-instrinfo.patch。
```

### Agent G2：指令描述 + 汇编/反汇编

**职责**：创建指令信息和汇编/反汇编器

**提示词**：
```
你是 DADAO-v5 的 LLVM MC 工程师。创建指令描述、汇编器和反汇编器。

读取：project/contracts/isa-spec.md, verif/opcodes.yaml, AGENTS.md

创建补丁 0004-0008：

**补丁 0004：指令信息表（DadaoInstrInfo.td）**
从 opcodes.yaml 生成 TableGen 指令定义。每条指令一个 record：
```tablegen
class DadaoInst<dag outs, dag ins, string asmstr, list<dag> pattern>
    : Instruction;

let Predicates = [IsDadao] in {
  / add-rd-orrr: add , rdhb, rdhc, rdhd
  def ADD_RD_BRRR : DadaoInst<
    (outs GPRD:$rdhb),
    (ins :$, GPRD:$rdhc, GPRD:$rdhd),
    "add\t$, $rdhb, $rdhc, $rdhd",
    []>;
  / ... 全部 ~150+ 条指令
}
```

**补丁 0005：AsmParser**
- 解析 DADAO 汇编语法
- 处理所有指令格式（rrrr/rrri/rrii/riii/iiii/rwii/orrr/...）
- 处理特殊操作数（, wpN, cfxcode）
- 处理伪指令（nop, not, ret, setrd, setrb, setrf）
- 操作数验证（寄存器范围、立即数范围）

**补丁 0006：反汇编器（MCDisassembler）**
- 基于 opcodes.yaml 的 mask/value 反汇编
- 大端序 32 位指令解码
- 操作数格式化（寄存器编号、立即数符号扩展）

**补丁 0007：编码发射器（MCCodeEmitter）**
- 按指令格式编码 bits
- 操作数位域装配
- 与大端序一致

**补丁 0008：MC 控制流 + 杂项**
- 分支目标计算
- 重定位支持（R_DADAO_24, R_DADAO_PC_24）

参考 DADAO-0628 的对应补丁，但基于 SimRISC 0.5.1 的新编码表。
关键差异：
-brri 格式的  操作数（DADAO-0628 没有）
- 更多浮点指令
- cfx 指令族
- 地址类指令的格式变化
```

### Agent G3：LIT 测试

**职责**：创建 LLVM MC 的 LIT 测试

**提示词**：
```
你是 DADAO-v5 的 LLVM 测试工程师。创建 LLVM MC 后端的 LIT 测试。

创建 `tests/lit/MC/Dadao/` 目录（在仓库中，不在 LLVM 源码树中）。

测试文件列表：
1. `rrrr.s`：四寄存器格式指令
2. `rrri.s`：三寄存器+立即数格式
3. `rrii.s`：两寄存器+12位立即数
4. `riii.s`：一寄存器+18位立即数
5. `iiii.s`：24位立即数格式
6. `rwii.s`：wyde-position 格式
7. `orrr.s`  `orri.s`  `oiii.s`：minor-opcode 格式
8. `brrr.s`  `brri.s`： 格式（新增）
9. `ciii.s`  `crrr.s`  `crii.s`：cfx 格式（新增）
10. `pseudo.s`：伪指令（nop, not, ret, setrd, setrb）
11. `illegal.s`：非法编码和操作数

每个测试文件使用：
```asm
# RUN: llvm-mc --triple=dadao-unknown-elf %s | FileCheck %s
```

参考 DADAO-0628/tests/lit/MC/Dadao 的测试结构和格式。
注意 DADAO-v5 特有指令的测试。
```

## 阶段验证

- `llvm-mc --triple=dadao-unknown-elf` 可以汇编/反汇编基本指令
- LIT 测试全部通过（`make check-mc` 或类似）
- 汇编-反汇编往返测试：汇编一条指令 → 反汇编 → 汇编，结果一致

## 依赖关系

- 依赖 Phase 1（opcodes.yaml 编码表）
- 依赖 Phase 5（LLVM 组件已获取）
- 是 Phase 10（CodeGen）的前提
