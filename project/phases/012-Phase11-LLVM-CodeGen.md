# Phase 11：LLVM CodeGen（基本代码生成）

> 对应 DADAO-0628 的 Phase 5（Basic CodeGen）+ DL-033a~063c 系列（CodeGen 补丁）

## 目标

在 LLVM MC 后端（Phase 6）基础上，实现 LLVM CodeGen 支持，使 LLVM 能够将标量整数和指针函数编译为 DADAO 指令。这是实现"从 C 到可执行"完整工具链的关键里程碑。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 1 | `contracts/isa/spec.md` | ISA 规范 |
| Phase 1 | `verif/opcodes.yaml` | 编码表 |
| Phase 4 | `contracts/abi/spec.md` | ABI 规范 |
| Phase 4 | `verif/abi.yaml` | ABI 事实 |
| Phase 6 | `components/llvm/patches/` | LLVM MC 补丁 |
| Phase 8 | `tests/lit/E2E/` | E2E 测试参考 |
| DADAO-0628 | `components/llvm/patches/0013~0022` | CodeGen 补丁参考 |
| DADAO-0628 | `tests/lit/E2E/` | E2E 测试参考 |

## 输出文件

```
DADAO-v5/components/llvm/patches/
├── (承接 Phase 6 的 MC 补丁，从 0013 开始)
├── 0013-dadao-codegen-skeleton.patch          # CodeGen 骨架（DAGToDAG, ISelLowering）
├── 0014-dadao-calling-conv.patch              # 调用约定
├── 0015-dadao-frame-lowering.patch            # 帧布局和栈操作
├── 0016-dadao-load-store-patterns.patch       # 加载/存储 DAG 模式
├── 0017-dadao-control-flow.patch              # 控制流 DAG 模式
├── 0018-dadao-integer-arithmetic.patch        # 整数运算 DAG 模式
├── 0019-dadao-compare-branch.patch            # 比较和分支 DAG 模式
├── 0020-dadao-shift-extend.patch              # 移位和扩展 DAG 模式
├── 0021-dadao-select-conditional.patch        # select → cs* 条件赋值
├── 0022-dadao-globals-relocations.patch       # 全局变量和重定位
├── 0023-dadao-sub-i64-types.patch             # sub-i64 类型支持
└── 0024-dadao-clang-targetinfo.patch          # clang 前端集成（下一里程碑）
```

## 子代理分解

### Agent L1：CodeGen 骨架 + 调用约定

**提示词**：
```
你是 DADAO-v5 的 LLVM CodeGen 工程师。创建 CodeGen 基础骨架和调用约定。

读取：
- DADAO-v5/contracts/abi/spec.md
- DADAO-v5/verif/abi.yaml
- DADAO-0628/components/llvm/patches/0013~0015（参考）

创建补丁 0013-0015：

**补丁 0013：CodeGen 骨架**
1. `DadaoISelLowering.cpp/h`：指令选择下降
   - setOperationAction 设置各操作的动作
   - setRegisterClass 等
   - DataLayout 对齐
2. `DadaoISelDAGToDAG.cpp/h`：DAG 到 DAG 指令选择
   - Select() 入口
   - 匹配 DAG 节点 → 机器指令
3. `DadaoInstrInfo.cpp/h`：指令信息
4. `DadaoRegisterInfo.cpp/h`：寄存器信息
   - 编码类（GPRD, GPRB 等）
   - 被调用者保存的寄存器列表

**补丁 0014：调用约定**
1. `DadaoCallingConv.td`：TableGen 调用约定定义
   - 参数传递规则（RD/RB/RF bank 独立计数）
   - 返回值规则
   - callee-saved 寄存器
2. `DadaoFrameLowering.cpp/h`：帧布局
   - SP 向下增长
   - 帧布局：内存参数 → rbfp → saved regs → 局部变量 → red zone
   - prologue/epilogue 插入

**补丁 0015：帧操作和栈访问**
- eliminateFrameIndex：FrameIndex → SP/FP 相对偏移
- 栈加载/存储指令选择
- SP 调整指令（addi-rb）

参考 DADAO-0628 的对应补丁，适配 DADAO-v5 的 ABI（注意 ABI 0.9.2 比 0.1.0 有更多细节）。
```

### Agent L2：运算指令 DAG 模式

**提示词**：
```
你是 DADAO-v5 的 LLVM CodeGen 模式匹配工程师。实现各类运算的 DAG 模式匹配。

创建补丁 0016-0021：

**补丁 0016：加载/存储模式**
- LD/ST 节点 → 对应 ldo/ldts/ldws/ldbs/sto/stt/stw/stb 指令
- 地址计算 → 基址+偏移（rrii 格式）
- 多寄存器加载/存储（rrri 格式）对于大型变量

**补丁 0017：控制流 DAG 模式**
- BR_CC → brn/brnn/brz/brnz/brp/brnp/breq/brne
- BR → jump
- CALL → call + RAS push
- RET → ret + RAS pop

**补丁 0018：整数运算 DAG 模式**
- ADD/SUB → add-rd/sub-rd（rrrr 或 brrr 格式）
- MUL/UDIV/SDIV → muls/mulu/divs/divu
- ADD immediate → addi-rd-rrii
- 注意 128 位结果的处理（双目标）

**补丁 0019：比较和分支**
- SETCC → cmps/cmpu（比较）
- BR_CC 与 SETCC 的组合优化
- 与条件分支的联合匹配

**补丁 0020：移位和扩展**
- SHL/SRL/SRA → shlu/shru/shrs（选择 brrr 或 brri 格式）
- SIGN_EXTEND/ZERO_EXTEND → exts/extz
- 按 bit position 选择合适的 bpN

**补丁 0021：条件赋值**
- SELECT/SELECT_CC → csn/csz/csp/cseq/csne
- 避免分支的条件执行
- 与 setcc 的组合优化
```

### Agent L3：全局变量 + sub-i64 + clang 集成

**提示词**：
```
你是 DADAO-v5 的 LLVM 前端集成工程师。实现全局变量、sub-i64 类型支持和 clang 集成。

创建补丁 0022-0024：

**补丁 0022：全局变量和重定位**
- GlobalAddress 节点 → rela + ldo/sto 组合
- 重定位类型：R_DADAO_24（call 24-bit）, R_DADAO_PC_24
- LLD 支持
- extern 全局符号处理

**补丁 0023：sub-i64 类型支持**
- i8/i16/i32 的窄加载/存储
- 类型提升：窄类型加载后 auto-sign/zero-extend
- 窄类型参数的 ABI 约定（符号扩展至 64 位）
- 类型转换链优化

**补丁 0024：clang 前端集成**（下一里程碑的起点）
- `clang/lib/Basic/Targets/Dadao.h/cpp`：TargetInfo
  - 类型大小和对齐
  - ABI 信息
- `clang/lib/Driver/ToolChains/Dadao.h/cpp`：ToolChain
  - 汇编器/链接器路径
  - 默认参数
- Triple 支持：dadao-unknown-elf

参考 DADAO-0628 的 0013~0022 补丁系列，特别是 0020（clang）和 0022（MC call reloc）。
适配 DADAO-v5 的 SimRISC 0.5.1 特性（如 brrr 格式的 bpN 对指令选择的影响）。
```

### Agent L4：CodeGen E2E 测试

**提示词**：
```
你是 DADAO-v5 的 CodeGen 测试工程师。创建 CodeGen 的端到端测试。

读取：
- DADAO-v5/tests/e2e/（已存在的 smoke 测试）
- DADAO-0628/tests/lit/E2E/（参考）

创建 E2E 测试：

1. **测试分类**：
   - `arr_sum.ll`：数组求和（加载/存储 + 算术 + 循环）
   - `bubble_sort.ll`：冒泡排序（比较 + 分支 + 交换）
   - `cond_abs.ll`：条件绝对值（select → cs*）
   - `factorial.ll`：阶乘（调用 + 返回 + RAS）
   - `fibonacci.ll`：斐波那契（递归调用）
   - `global_var.ll`：全局变量访问
   - `pointer_arg.ll`：指针传参
   - `nested_call.ll`：嵌套函数调用
   - `i8_add.ll`：8 位运算
   - `i16_cmp.ll`：16 位比较

2. **测试格式**（.test 文件）：
```lit
# RUN: llc -mtriple=dadao-unknown-elf %s -o %t.s
# RUN: llvm-mc -triple=dadao-unknown-elf %t.s -filetype=obj -o %t.o
# RUN: ld.lld -T %S/../../../tests/scripts/dadao.ld %t.o -o %t.elf
# RUN: qemu-system-dadao -M dadao-m1 -kernel %t.elf | FileCheck %s

; CHECK: exit code: 0
```

3. **测试原则**（严格执行）：
   - 所有 .s 文件必须来自 llc（编译器产物），禁止手写汇编替代
   - 测试必须是完整的端到端流程：IR → llc → .s → llvm-mc → .o → ld.lld → .elf → QEMU 执行
   - 验证退出码正确

参考 DADAO-0628/tests/lit/E2E/ 的 Inputs/ 和 *.test 文件结构。
```

## 阶段验证

- `llc -mtriple=dadao-unknown-elf` 可将 LLVM IR 编译为 DADAO 汇编
- 基本 C 函数（通过 clang 或手写 IR）编译后在 QEMU 中正确执行
- E2E 测试全部通过（arr_sum, factorial, fib 等）
- CodeGen ABI 一致性检查：llc 生成的代码符合 ABI 规范

## 依赖关系

- 依赖 Phase 6（LLVM MC 后端）
- 依赖 Phase 7（QEMU 执行验证）
- 依赖 Phase 8（集成测试框架）
- 依赖 Phase 4（ABI 规范）

## 后续里程碑

完成此阶段后，DADAO-v5 实现了完整的 M1+M2 功能：
- ✅ LLVM MC 汇编/反汇编
- ✅ QEMU 标量核心执行
- ✅ Python golden model
- ✅ 三路差分验证（interp/QEMU/gem5）
- ✅ Sail 形式化规范
- ✅ LLVM CodeGen 基本代码生成

下一步（延迟到下一里程碑）：
- clang 前端集成（已有 Phase 11 的 0024 补丁起点）
- 浮点指令完整实现
- 系统 QEMU（异常模型、MMU）
- Linux 内核支持
- musl libc 移植
- Chipyard 硬件实现
