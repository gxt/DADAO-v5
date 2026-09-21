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

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节为**下发前预检**结论，优先级高于下文旧文本；冲突时以本节为准。

**P1 — lit 文件范围（用户裁定「迁移 + 统一」）**：
- **新建 13 个格式族文件**（`rrii_alu.s`/`rrrr.s`/`rrri.s`/`riii_branch.s`/`riii_ret.s`/`rrii_branch.s`/`rrii_load.s`/`rrii_store.s`/`iiii_jump.s`/`orrr.s`/`orri.s`/`rb_ops.s`/`rwii.s`），统一用强模板（`--check-prefix=OBJ` + `--check-prefix=ASM`）
- **把现有 `disassembly.s` 的 15 组用例迁移进上述格式族文件，然后删除 `disassembly.s`**（不留重复）
- **把现有 `basic-encoding.s` 统一为强模板**（`readelf -x .text` + 默认前缀 → `llvm-objdump -d` + `OBJ:`/`ASM:`）
- **`triple-smoke.s` 不动**（任务书原约束）
- **覆盖不丢的硬要求**：迁移后「13 个文件的用例并集」⊇「原 `disassembly.s` 的 15 组 + 原 `basic-encoding.s` 的 4 组」，须**逐条**核对（列对照表），不得静默丢用例

**P2 — 必须排除的范围（依赖边界）**：
- **RA 操作形式不可用**：实测 `ld.o-ra`/`st.o-ra` → `error: invalid operand for instruction`（RA 单/多存取的 MC 支持属 **`LLVM-011t`**）⇒ 本任务的 lit **不得**包含 `ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra` 形式（`rd2ra`/`ra2rd` 可汇编，但字节/反汇编完整性属 `011t`，本任务**不纳入**）
- **系统指令助记符修正属 `LLVM-010t`**（依赖本任务）⇒ 本任务不承担 `010t` 的命名修正

**P3 — 字节核对的独立 oracle（复用优先）**：
- 任务书 #6「字节等于**独立手推值**」是**自证**（同一作者既写 CHECK 又算「独立」值），**不构成独立验证**
- **已有现成独立 oracle**：`tools/llvm/test_encoding_oracle.py`（`LLVM-006t` 交付；由 `contracts/opcodes.yaml` 的 mask/value + 公式**独立计算**并与 `llvm-mc` 输出比对；实测 **31 passed / 0 failed**，覆盖 9 格式 + 分支）
- ⇒ 本任务须**扩展**该 oracle 覆盖新增用例，并在完成区给出其真实输出（`N passed / 0 failed`）；**不得**用「手推」自证

**P4 — 实测环境与基线（可直接跑）**：
- **LLVM build 存在**：`.work/build/llvm/bin/{llvm-mc,llvm-lit,llvm-objdump,FileCheck}` ⇒ **lit 可跑**（任务书「若 build 未完成，只交付 .s 并注明」的兜底**不需要**）
- **当前 lit 基线**：`llvm-lit tests/lit/MC/Dadao/` = **3 tests / 3 passed**（`triple-smoke.s`/`basic-encoding.s`/`disassembly.s`）
- `make build-mc` 目标存在 ✓

**P5 — 实测语法（lit 必须用正确形式）**：
- `add.uo`（`orrr`）需 **4 个操作数**：`add.uo rd8, rd9, rd10, rd11`
- `illi` 需 **1 个操作数**：`illi 0`
- 其余已实测可汇编：`add.si`/`ld.ub`/`ld.sb`/`ldm.ub`/`set.zw`/`or.o`/`rb2rd`/`br.n`/`ret`/`swym`/`fence`/`stm.b`/`cs.n`

**P6 — 表述订正**：差异条「0628 示例字节有误（`addi rd8` 写成 `19 40 00 01`，应为 `19 20 00 01`）」中的「应为」值仍是 **0.4.1** 编码（v5 `add.si rd8, 1` = `0x59200001`，见 `basic-encoding.s`）——该条本意仅为「0628 有 bug、v5 须全部手推」，勿据此推 v5 字节。


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
  # RUN: llvm-objdump -d --triple=dadao-unknown-elf %t | FileCheck %s --check-prefix=OBJ
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

- **13 个** `tests/lit/MC/Dadao/*.s` 格式族文件（强模板：`--check-prefix=OBJ` + `--check-prefix=ASM`；`OBJ:` 行形如 `<hex bytes>{{.*}}<mnemonic>`）
- **`disassembly.s` 迁移完成后删除**；**`basic-encoding.s` 统一为强模板**；**`triple-smoke.s` 不动**
- **扩展后的** `tools/llvm/test_encoding_oracle.py`（独立字节 oracle，覆盖新增用例）
- `components/llvm-project/patches/series` 保持 0001–0006（**本任务不改补丁**）

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
3. `llvm-lit tests/lit/MC/Dadao/` **0 failures**（基线 3 tests/3 passed → 迁移后文件数增加、仍 0 failures）
4. **每个** lit 文件（除 `triple-smoke.s`）含 `--check-prefix=OBJ` 与 `--check-prefix=ASM` 两条 RUN
5. `OBJ:` 行形如 `<hex bytes>{{.*}}<mnemonic>`，字节来源为**独立 oracle**（见 #6）
6. **独立 oracle**：扩展并运行 `tools/llvm/test_encoding_oracle.py`，完成区给出真实输出（`N passed / 0 failed`，N ≥ 原 31 + 新增用例）；**不得**用「手推」自证
7. **覆盖不丢**：给出「13 文件用例并集 ⊇ 原 `disassembly.s` 15 组 + 原 `basic-encoding.s` 4 组」的**逐条对照表**
8. `disassembly.s` 已删除、`basic-encoding.s` 已统一为强模板、`triple-smoke.s` **未改**（`git diff`）
9. **未包含 RA 操作形式**（`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`）；未承担 `010t` 的命名修正
10. `series` 仍为 0001–0006；未改 `.s` 的非注释指令行（迁移除外——迁移即把指令行搬到新文件）
11. **反例门控**：任取一条 `OBJ:` 字节改错 1 位 → `llvm-lit` 必须 **FAIL**；还原 → PASS（证明字节 CHECK 真的生效，非恒真）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
