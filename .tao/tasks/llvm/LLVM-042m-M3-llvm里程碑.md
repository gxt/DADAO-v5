# LLVM-042m: M3 llvm 里程碑（Basic CodeGen 纯整数）

**模块**：llvm
**项目里程碑**：M3
**状态**：里程碑
**目标**：DADAO LLVM 后端具备**纯整数 CodeGen**：`llc` 把标量整数/指针函数（IR）编译为 DADAO 汇编——GPRD/GPRB 双 bank 值类型、i64 算术/常数（含 `ptr−ptr` → 新增指令 `sub.o`）、标量 load/store、compare/branch、FrameIndex 消解 + spill/reload + prologue/epilogue、标量调用约定 + call/ret、AsmPrinter（MI→MCInt→`.s`）、最小重定位（段内标签 PCRel `<<2`）；`RA`/`RF` 仅保留不分配；GPRD/GPRB 在 MIR 全程存活；`.s` 可被 `llvm-mc` 汇编成 obj。
**关联任务**：`LLVM-033t`、`LLVM-034t`、`LLVM-043t`、`LLVM-035t`、`LLVM-036t`、`LLVM-037t`、`LLVM-038t`、`LLVM-039t`、`LLVM-040t`、`LLVM-041t`、`LLVM-047t`、`LLVM-048t`、`LLVM-049t`（13 个）

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出是否存在：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（新增 CodeGen 文件补丁）、`.work/evidence/LLVM-03{3..9}t/`、`.work/evidence/LLVM-041t/`、`.work/evidence/LLVM-043t/`
- `make check-patch-tree` 通过（含断言⑥ blob 一致性）；`make check-lit`（MC）不回归
- `llc --version` 含 dadao；`llc -march=dadao` 能对四类标量程序出 `.s`，无 `*_PSEUDO`；`llvm-mc -filetype=obj` 成功
- **新增指令 `sub.o_orrr_dbb`**：`LLVM-043t` 的 MC 往返（`llvm-mc`↔`llvm-objdump`）与 `test_encoding_oracle.py` 通过；`LLVM-035t` 的 `ptr−ptr` ISel 选出该指令（MIR 证据）
- 跨模块影响：CC 期望值来自 `SPEC-097t` 合约；新指令编码来自 `SPEC-100t`（`adr-0012 D9`）；三条既有 RB 算术指令改名/改编码（`add.o_orrr_bbd`/`sub.o_orrr_bbd`/`cmp.uo_orrr_dbb`）来自 `SPEC-101t`（跨组件，含 MC `.td`）；E2E 由 `INTEG-013m` 核验；无未处置项
- 取舍项按 `ADR-0018` 落地（C1 硬双类/C2 指针 i64 通吃/C4 栈溢出区/C5 返回 rb31+callee 扩展/C7 帧策略条件式/C9 DataLayout/C11 SelectionDAG/C13 无 subreg+大端窄访存/C14 RB 算术落 GPRB/C16 call Defs-RegMask）；C17（无标志位 compare-branch）落 `LLVM-037t` 约束；**新增指令 `sub.o_orrr_dbb`（C14 D4 `ptr−ptr` 终态）与三条既有 RB 算术指令改名/改编码按 `adr-0012 D9` 落地**（`SPEC-101t`/`SPEC-100t`/`LLVM-043t`/`LLVM-035t`）

## 核验记录（主会话 2026-10-05）

- 关联任务（13）全部 `**状态**：已验证`（`.work/log/m3-closure/assoc-status.log`）。
- 产出存在：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（含 `DADAOCallingConv.td.patch`、`DADAOMCInstLower.*`、`DADAOAsmPrinter.*`）；`.work/evidence/LLVM-03{3..9}t/`、`LLVM-040t/041t/043t/047t/048t/049t/`。
- `llc --version | grep -i dadao` → **EXIT=0**（输出含 `dadao`）。
- `make check-patch-tree` → **EXIT=0**（`80 patches OK`）。
- `make check-lit`（MC）→ **EXIT=0**（34/34）。
- `make check` → **EXIT=0**（`repository checks: PASS`）。
- **新增指令 `sub.o_orrr_dbb`**：`LLVM-043t` MC 往返 + `test_encoding_oracle.py` 通过；`LLVM-035t` `ptr−ptr` ISel 选出该指令（MIR 证据）；E2E 由 `INTEG-013m` 核验（`ptr_diff_pos/neg` = 7/249）。
- 跨模块影响：CC 期望值来自 `SPEC-097t`；新指令编码 `SPEC-100t`；三条 RB 算术改名/改编码 `SPEC-101t`；E2E `INTEG-013m`；**无未处置项**。
- 取舍项按 `ADR-0018`（C1/C2/C4/C5/C7/C9/C11/C13/C14/C16）+ `LLVM-037t` C17 落地；`adr-0012 D9` 已落地。
- 追加（原列表未列，已在 M3 内验收）：`LLVM-047t`（有符号窄扩展 C4）、`LLVM-048t`（C14 指针算术直选）、`LLVM-049t`（MC `br.z/br.nz` bank 修复，由 `INTEG-012t` E2E 发现）。
- **结论：置 `里程碑`。**
