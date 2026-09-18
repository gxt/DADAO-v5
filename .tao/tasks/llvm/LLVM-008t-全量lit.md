# LLVM-008t: 全量 lit

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-007t`、`SPEC-003t`
**状态**：待开始

> **重排说明（2026-09-18）**：原 `LLVM-007t`（CodeEmitter 修复 + 全量 lit）与原 `LLVM-008t`（反汇编器）交换编号，并将原 `LLVM-009t`（lit 字节级 CHECK）归并入本任务。
>
> **CodeEmitter 修复已在 `LLVM-006t` 完成**：`encodeInstruction()` 已调 `getBinaryCodeForInstr()`（非 stub）、Branch/Jump 的 PC-relative 已用 `MCFixup`（`DADAO_FK_PCRel_12/_18/_24`）+ `applyFixup`（`(target-current)>>2`，无 +4）实现，并有仓库 lit `tests/lit/MC/Dadao/basic-encoding.s` 覆盖非 0 偏移前向与后向分支。故本任务**不含 CodeEmitter 修复**，仅交付全量 lit 覆盖（含字节级 OBJ CHECK）。
>
> **`LLVM-009t` 归并理由**：原 `009t`（拆分 OBJ/ASM 前缀 + 字节级 OBJ CHECK）与原 `007t`（全量 lit）完全重叠——都是对 `tests/lit/MC/Dadao/*.s` 的扩充与校验。拆为两个任务会导致 `009t` 仅做"在已有文件上加 CHECK 行"的琐碎操作，无独立交付价值。合并后，一次性交付**带 OBJ/ASM 前缀 + 字节级 CHECK 的全量 lit**，减少任务数、消除重叠。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-007t` 的 Disassembler（`llvm-objdump -d` 可用）、`LLVM-006t` 的 AsmParser/MCCodeEmitter、`.tao/knowledge/contract-isa.md` §2、`contracts/opcodes.yaml`
- 输出：13+ 个 `tests/lit/MC/Dadao/*.s`（含 `OBJ:`/`ASM:` 前缀与字节级 `OBJ:` CHECK 行）、更新后的 `series`（保持 0001–0006）
- 约束：
  - `encodeInstruction` 必须调用 `getBinaryCodeForInstr()`，不得保留 stub（已在 `LLVM-006t` 验证，本任务复验）
  - 期望字节**手推**（从 `contract-isa.md §2.2` 公式 + `contracts/opcodes.yaml`），禁止从 `llvm-mc`/`llvm-objdump` 输出复制
  - 每个 lit 文件同时覆盖 `-filetype=obj`（`llvm-objdump -d` 字节级验证）与 `-filetype=asm`（round-trip）
  - `make build-mc` PASS；`llvm-lit tests/lit/MC/Dadao/` 0 failures
  - `triple-smoke.s` 不改
  - 不改 `.s` 的非注释指令行

## 背景（完整）

### 目标

交付全量 lit 测试文件，覆盖全部 M1 指令格式族，同时含 `OBJ:`（objdump 字节级）与 `ASM:`（asm round-trip）前缀与 CHECK 行，`llvm-lit tests/lit/MC/Dadao/` 0 failures。

### 设计理由

- 0628 `DL-010b` 交付的 lit 仅验证 `-filetype=asm` round-trip，未做字节级 `llvm-objdump -d` 校验。本任务按 RUN 模板覆盖两条路径，字节级 OBJ 检查能检测反汇编器/编码器缺陷。
- 字节级 OBJ 检查（原 `LLVM-009t` scope）：若 lit 只匹配助记符文本，字节→助记符映射错误（或空字节）也会通过；字节级 OBJ 检查才能暴露问题。

### 关键概念 / 数据

- **lit RUN 模板**：
  ```asm
  # RUN: llvm-mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
  # RUN: llvm-objdump -d %t | FileCheck %s --check-prefix=OBJ
  # RUN: llvm-mc --triple=dadao-unknown-elf -filetype=asm %s | FileCheck %s --check-prefix=ASM
  ```
- **CHECK 前缀约定**：
  - `# OBJ:` 行形如 `<hex bytes>{{.*}}<mnemonic>`（字节全大写、每字节 2 位 hex、空格分隔；`{{.*}}` 吸收空白）
  - `# ASM:` 行匹配 asm round-trip 输出
- **编码公式**：`word[31:0] = (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd`（op 查 `contracts/opcodes.yaml`）
- **字段映射**（按格式）：rrrr 四寄存器；rrii dest/src/imm；riii dest/imm18；orrr minor/dest/src1/src2；rrri dest/base/src/count；rwii dest/wyde-pos/imm；orri minor/dest/src/immu6
- **字节序**：DADAO 大端，`word = 0xXXXX` 在内存为 `XX XX XX XX`（MSB 左）
- **有符号立即数**：imms12/18/24 为 sign-extended；负数取补码低位
- **lit 文件清单**（0628 命名可参考，内容按 v5 重写）：`rrii_alu.s`、`rrrr.s`、`rrri.s`、`riii_branch.s`、`riii_ret.s`、`rrii_branch.s`、`rrii_load.s`、`rrii_store.s`、`iiii_jump.s`、`orrr.s`、`orri.s`、`rb_ops.s`、`rwii.s`，加 `triple-smoke.s`

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`（完整转述：背景、目标、修复、MCFixup、12 个 lit、约束、验收、Architecture Review）。
- DADAO-0628：`code-agent/tasks/DL-011b-lit-byte-checks.md`（字节级 CHECK 规则、改造格式、约束）。
- DADAO-0628：`tests/lit/MC/Dadao/`（文件命名与 lit 组织参考）。
- DADAO-0628：`components/llvm/patches/0005-dadao-asmparser.patch`（**仅参考命名/序号**，不复制正文）。

## 交付物

- 13+ 个 `tests/lit/MC/Dadao/*.s`：含 `OBJ:`/`ASM:` 前缀与字节级 `OBJ:` CHECK 行（`OBJ:` 行形如 `<hex bytes>{{.*}}<mnemonic>`）。
- `components/llvm-project/patches/series` 保持 0001–0006。
- （可选）若涉及补丁可重现性，更新 `components/llvm-project/patches/0006-dadao-disassembler.patch` 使 lit 更新纳入。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **指令集**：v5 M1 指令（`.b/.w/.t/.o`、`s`/`u`、MISC 子表）与 0.4.1 不同；lit 内容与期望字节按 `contract-isa.md` + `contracts/opcodes.yaml` 重写。
- **期望字节**：0628 任务示例字节有误（`addi rd8` 写成 `19 40 00 01`，应为 `19 20 00 01`）；v5 全部手推，**不得复制**。
- **`{{.*}}` 内建**：0628 N1 指出 OBJ 模式缺 `{{.*}}`，依赖单空格输出会静默 flake；v5 从一开始就带 `{{.*}}`。
- **补丁正文**：不复制 0628 的 0005 patch。
- **lit 命名**：沿用格式类别命名（rrii/rrrr/…）作组织参考，但内容按 0.5.3。

## 已知坑 / 结论

- **手推字节**：所有字节从公式 + `contracts/opcodes.yaml` 推导，禁止复制工具输出（否则无法检测工具 bug）。
- **`{{.*}}`**：吸收字节与助记符之间的空白，避免格式变化导致 flake。
- **不改指令行**：`.s` 中的实际指令行不修改。
- **保留 `triple-smoke.s` 不变**。
- **P1（0628 DL-010b N1）**：0628 的 lit 仅验证 `-filetype=asm` round-trip，未做字节级 `llvm-objdump -d` 校验；本任务按 RUN 模板覆盖两条路径。
- **AsmBackend 存根**：缺失导致注册崩溃（已在 `LLVM-006t` 验证）。
- **MCFixup**：Branch/Jump 超范围记录 fixup（自定义 `DADAO_FK_PCRel_12/_18/_24`，addend=0，无 +4 偏移）；已在 `LLVM-006t` 实现。
- **DataLayout 大端**：确认 `LLVM-003t` 的 DataLayout 含 `E`（大端）。
- **lit 需 build-llvm**：若 build 未完成，只交付 `.s` 文件并在完成区注明「lit 未运行」。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-011b-lit-byte-checks.md`
- DADAO-0628：`.work/DADAO-0628/tests/lit/MC/Dadao/`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§2.1/§2.2/§2.3）、`contracts/opcodes.yaml`

## 验收标准

1. `encodeInstruction()` 调用 `getBinaryCodeForInstr()`，无写 0 stub（复验 `LLVM-006t` 成果）
2. `make build-mc` PASS
3. `llvm-lit tests/lit/MC/Dadao/` 0 failures（编码文件 + triple-smoke）
4. 每个 lit 文件含 `--check-prefix=OBJ` 与 `--check-prefix=ASM` 两条 RUN
5. `OBJ:` 行形如 `<hex bytes>{{.*}}<mnemonic>`，字节手推（完成区给出推导依据）
6. 关键指令 `-filetype=obj` 字节等于独立手推值（至少覆盖 rrii/rrrr/riii/iiii/rwii/orrr/orri）
7. `triple-smoke.s` 未改
8. 未修改 `.s` 的非注释指令行
9. `series` 仍为 0001–0006

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
