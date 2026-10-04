# LLVM-040t: AsmPrinter（MI → MCInst → `.s`）

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-039t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-039t` 的完整 lowering（MIR 含 call/ret/帧/访存/算术）；v5 MC 层（AsmParser/InstPrinter/CodeEmitter 已工作）。
- **输出**：`DADAOAsmPrinter`（+ `DADAOMCInstLower`，如需要）使 `llc` 产出可被 `llvm-mc` 汇编的 `.s`（无伪指令残留）；导出的补丁。
- **约束**：
  - **必须**：实现 `AsmPrinter`（`emitInstruction`：MI→MCInst→`OutStreamer`），寄存器/立即数/符号/基本块操作数降低（符号/BasicBlock 用已有的 MCExpr 通路）；在 `LLVMInitializeDADAOTarget` 注册 AsmPrinter；`CMakeLists.txt` 接入新文件。
  - **伪指令展开**：`LLVM-035t`~`LLVM-039t` 若引入了伪指令（如 `ADD_PSEUDO`/`SUB_PSEUDO`/`RET_PSEUDO`/`CALL_PSEUDO_INDIRECT`/`LDO_FI` 等），实现 `expandPostRAPseudo`（`DADAOInstrInfo`）或等价 pass，使最终 `.s` 无 `*_PSEUDO`。
  - **寄存器名一致性**：AsmPrinter 输出的寄存器名/助记符必须与 `MCTargetDesc/DADAOAsmParser.cpp` 能对上的名字一致（如帧寄存器用 GPRB 可识别名 `rb1`，而非 dwarf 别名 `RBSP`）——**这正是 round-trip 验收要卡的**。
  - **`.s` 语法**：`;` 为注释（`ADR-0013`）；`#` 非法；wyde 位置**只能写作 `wp0`–`wp3`**（裸数字 0–3 属非法、须报错，`ISS-128`；C12）。注：本任务书旧表述「`wpN` 会被 AsmParser 静默忽略、须用数值位置」与 §5 判定**相反**，已按 §5 更正。
  - **范围**：叶函数与非叶函数（有 call）的完整 `.s` 发射。**不含**：`.data`/`.rodata` 全局发射（→M4）、重定位类型定义（→`LLVM-041t`）。
  - 不回归 `LLVM-033t`~`LLVM-039t` 的 MIR；不回归 `make check-lit`（MC 31/31）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-054a`（AsmPrinter + pseudo 替换）；M68k `M68kAsmPrinter.cpp`/`M68kMCInstLower.*`——只读溯源。

## 验收标准

1. `ninja -C .work/build/llvm llc llvm-mc` 退出 0。
2. `.s` 产出（真实输出）：
   - `define i64 @add(i64 %a,i64 %b){ %s=add i64 %a,%b  ret i64 %s }` → `llc -march=dadao` 出 `.s`，`grep -c PSEUDO` = 0；
   - `define i64 @ld(ptr %p){ %v=load i64,ptr %p  ret i64 %v }` → `.s` 无 pseudo；
   - caller/callee（`LLVM-039t` 的用例）→ `.s` 含 `call callee`、参数按 ABI 就位、无 pseudo。
3. `llvm-mc -triple=dadao -filetype=obj <.s>` 对以上每个 `.s` 退出 0（**不 grep，看 exit code**）。
4. `llvm-objdump -d` 反汇编回流能对上助记符（可选，作为 cross-check）。
5. 不回归 `make check-lit`；补丁导出且 `make check-patch-tree` 通过。
6. 一键证据脚本 `.work/evidence/LLVM-040t/run.sh`（规格同 `LLVM-033t`；反例注入：让 AsmPrinter 输出一个别名寄存器名/坏助记符 → 预期 `llvm-mc` 非零退出，再还原）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
