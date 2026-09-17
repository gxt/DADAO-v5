# LLVM-007t: CodeEmitter 修复与 lit

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-006t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-006t` 的 `0005-dadao-asmparser.patch`、`.tao/knowledge/contract-isa.md` §2、`contracts/opcodes.yaml`
- 输出：修订后的 `components/llvm/patches/0005-dadao-asmparser.patch`（序号不变）、全量 lit 文件 `tests/lit/MC/Dadao/*.s`、更新后的 `series`
- 约束：`encodeInstruction` 必须调用 `getBinaryCodeForInstr()`，不得保留 stub；期望字节手推；每个 lit 文件同时覆盖 `-filetype=obj` 与 `-filetype=asm`；`make build-mc` PASS；`llvm-lit tests/lit/MC/Dadao/` 0 failures

## 背景（完整）

### 目标

1. 修复/确认 `encodeInstruction()` 调用 TableGen 生成的 `getBinaryCodeForInstr()`，验证关键指令字节。
2. 交付全量 lit 测试文件，`llvm-lit tests/lit/MC/Dadao/` 0 failures。
3. 为 Branch/Jump 的 PC-relative 操作数补齐 `MCFixup` 占位。

### 设计理由

- 0628 `DL-010a` 交付的 emitter 是写 0 stub，`-filetype=obj` 崩溃；`-filetype=asm` 不经过 emitter 所以看似正常。本任务把 emitter 修正确认并补齐测试覆盖。
- 补丁序号保持 0005（替换原文件），避免 series 抖动。

### 关键概念 / 数据

- **emitter include**（参考 Lanai `LanaiMCCodeEmitter.cpp`）：
  ```cpp
  #define GET_INSTRINFO_ENUM
  #include "DADAOGenInstrInfo.inc"
  #define ENABLE_INSTR_PREDICATE_VERIFIER
  #include "DADAOGenMCCodeEmitter.inc"
  ```
  `encodeInstruction` 内 `uint32_t Bits = getBinaryCodeForInstr(MI, Fixups, STI);` 后大端写出。
- **getMachineOpValue**：寄存器注册值 + 立即数；遇 `MCExpr` 时创建 `MCFixup` 并返回 0（`DADAOFixupKinds.h` 声明 kind，须自定义 `DADAO_FK_PCRel_2`，addend=0；**不得用 `FK_PCRel_4`**，DADAO 无 +4 流水线偏移）。
- **lit 通用 RUN 模板**：
  ```asm
  # RUN: llvm-mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
  # RUN: llvm-objdump -d %t | FileCheck %s
  # RUN: llvm-mc --triple=dadao-unknown-elf -filetype=asm %s | FileCheck %s --check-prefix=ASM
  ```
- **lit 文件清单**（0628 命名可参考，内容按 v5 重写）：`rrii_alu.s`、`rrrr.s`、`rrri.s`、`riii_branch.s`、`riii_ret.s`、`rrii_branch.s`、`rrii_load.s`、`rrii_store.s`、`iiii_jump.s`、`orrr.s`、`orri.s`、`rb_ops.s`、`rwii.s`，加 `triple-smoke.s`。
- **期望字节手推**：`word[31:0] = (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd`，op 查 `contracts/opcodes.yaml`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`（完整转述：背景、目标、修复、MCFixup、12 个 lit、约束、验收、Architecture Review）。
- DADAO-0628：`components/llvm/patches/0005-dadao-asmparser.patch`（**仅参考命名/序号**，不复制正文）。
- DADAO-0628：`tests/lit/MC/Dadao/`（文件命名与 lit 组织参考）。

## 交付物

- 修订后的 `components/llvm/patches/0005-dadao-asmparser.patch`：emitter 调用 `getBinaryCodeForInstr()`、格式类字段名与操作数名对齐、AsmBackend 存根、MCFixup 占位。
- 全量 lit 文件（13 个编码文件 + `triple-smoke.s`）位于 `tests/lit/MC/Dadao/`。
- `components/llvm/patches/series` 保持 0001–0005。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **指令集**：v5 M1 指令（`.b/.w/.t/.o`、`s`/`u`、MISC 子表）与 0.4.1 不同；lit 内容与期望字节按 `contract-isa.md` + `contracts/opcodes.yaml` 重写。
- **期望字节**：0628 任务示例字节有误（`addi rd8` 写成 `19 40 00 01`，应为 `19 20 00 01`）；v5 全部手推，**不得复制**。
- **补丁正文**：不复制 0628 的 0005 patch。
- **lit 命名**：沿用格式类别命名（rrii/rrrr/…）作组织参考，但内容按 0.5.3。

## 已知坑 / 结论

- **P0（0628 DL-010a）**：emitter stub 导致 `-filetype=obj` SEGFAULT；本任务必须确认非 stub。
- **P1（0628 DL-010b N1）**：0628 的 lit 仅验证 `-filetype=asm` round-trip，未做字节级 `llvm-objdump -d` 校验；本任务按 RUN 模板覆盖两条路径，字节级 OBJ 前缀由 `LLVM-009t` 补齐。
- **AsmBackend 存根**：缺失导致注册崩溃。
- **MCFixup**：Branch/Jump 超范围记录 fixup（自定义 `DADAO_FK_PCRel_2`，addend=0，无 +4 偏移）；`rela.si` 本任务作 PCRel 占位，ELF relocation 不在本任务集。
- **patch 序号保持 0005**：替换原文件，series 不变。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-010a-llvm-asmparser.md`
- DADAO-0628：`.work/DADAO-0628/tests/lit/MC/Dadao/`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`、`contracts/opcodes.yaml`

## 验收标准

1. `encodeInstruction()` 调用 `getBinaryCodeForInstr()`，无写 0 stub
2. `make build-mc` PASS
3. 关键指令 `-filetype=obj` 首 4 字节等于独立手推值（至少覆盖 rrii/rrrr/riii/iiii/rwii/orrr/orri）
4. `llvm-lit tests/lit/MC/Dadao/` 0 failures（编码文件 + triple-smoke）
5. 每个 lit 文件含 `-filetype=obj` 与 `-filetype=asm` 两条 RUN
6. `series` 仍为 0001–0005

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
