# LLVM-042m: M3 llvm 里程碑（Basic CodeGen 纯整数）

**模块**：llvm
**项目里程碑**：M3
**状态**：待开始
**目标**：DADAO LLVM 后端具备**纯整数 CodeGen**：`llc` 把标量整数/指针函数（IR）编译为 DADAO 汇编——GPRD/GPRB 双 bank 值类型、i64 算术/常数、标量 load/store、compare/branch、FrameIndex 消解 + spill/reload + prologue/epilogue、标量调用约定 + call/ret、AsmPrinter（MI→MCInt→`.s`）、最小重定位（段内标签 PCRel `<<2`）；`RA`/`RF` 仅保留不分配；GPRD/GPRB 在 MIR 全程存活；`.s` 可被 `llvm-mc` 汇编成 obj。
**关联任务**：`LLVM-033t`、`LLVM-034t`、`LLVM-035t`、`LLVM-036t`、`LLVM-037t`、`LLVM-038t`、`LLVM-039t`、`LLVM-040t`、`LLVM-041t`（9 个）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（新增 CodeGen 文件补丁）、`.work/evidence/LLVM-03{3..9}t/`、`.work/evidence/LLVM-041t/`
- `make check-patch-tree` 通过（含断言⑥ blob 一致性）；`make check-lit`（MC）不回归
- `llc --version` 含 dadao；`llc -march=dadao` 能对四类标量程序出 `.s`，无 `*_PSEUDO`；`llvm-mc -filetype=obj` 成功
- 跨模块影响：CC 期望值来自 `SPEC-097t` 合约；E2E 由 `INTEG-013m` 核验；无未处置项
- 取舍项按 `ADR-0018` 落地（C1 硬双类/C2 指针 i64 通吃/C4 栈溢出区/C5 返回 rb31+callee 扩展/C7 帧策略条件式/C9 DataLayout/C11 SelectionDAG/C13 无 subreg+大端窄访存/C14 RB 算术落 GPRB/C16 call Defs-RegMask）；C17（无标志位 compare-branch）落 `LLVM-037t` 约束

## 核验记录
（核验时由主会话/架构师填写：命令原样 + 退出码）
