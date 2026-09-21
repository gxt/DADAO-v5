# LLVM-008t: 全量 lit

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-007t`、`SPEC-003t`
**状态**：已验证

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
- ~~**系统指令助记符修正属 `LLVM-010t`**（依赖本任务）⇒ 本任务不承担 `010t` 的命名修正~~（`010t` 已于 2026-09-21 关闭；实测 `swym`/`illi` 本任务已覆盖、`fence` 入 `deferred`）

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

**测试结果**：通过 16/16 lit；57/0 oracle；反例门控 PASS
**修改文件**：
- `tests/lit/MC/Dadao/basic-encoding.s`（统一为强模板 OBJ+ASM；补回 `add.si rd8, -1`）
- `tests/lit/MC/Dadao/disassembly.s`（已删除）
- `tests/lit/MC/Dadao/rrii_alu.s`（新建：cmp.ui/cmp.si）
- `tests/lit/MC/Dadao/rrii_branch.s`（新建：br.eq）
- `tests/lit/MC/Dadao/rrii_load.s`（新建：ld.ub/ld.sb）
- `tests/lit/MC/Dadao/rrii_store.s`（新建：st.b）
- `tests/lit/MC/Dadao/rrri.s`（新建：ldm.ub）
- `tests/lit/MC/Dadao/rrrr.s`（新建：add.uo/add.so）
- `tests/lit/MC/Dadao/riii_branch.s`（新建：br.n/br.nn/br.z/br.nz/br.p/br.np + label fixup）
- `tests/lit/MC/Dadao/riii_ret.s`（新建：ret）
- `tests/lit/MC/Dadao/iiii_jump.s`（新建：jump/call/swym）
- `tests/lit/MC/Dadao/orrr.s`（新建：or.o）
- `tests/lit/MC/Dadao/orri.s`（新建：ext.uo）
- `tests/lit/MC/Dadao/rb_ops.s`（新建：rb2rd/rd2rd）
- `tests/lit/MC/Dadao/rwii.s`（新建：set.zw）
- `tests/lit/MC/Dadao/oiii.s`（新建：illi）
- `tools/llvm/test_encoding_oracle.py`（扩展：31→57 测试用例）

**验收结果**：

### 1. `make build-mc` PASS
```
build-mc: PASS
```

### 2. `llvm-lit tests/lit/MC/Dadao/` 0 failures
```
-- Testing: 16 tests, 16 workers --
PASS: DADAO-MC :: rrii_alu.s (1 of 16)
PASS: DADAO-MC :: rrii_store.s (2 of 16)
PASS: DADAO-MC :: rrii_load.s (3 of 16)
PASS: DADAO-MC :: basic-encoding.s (4 of 16)
PASS: DADAO-MC :: rb_ops.s (5 of 16)
PASS: DADAO-MC :: riii_ret.s (6 of 16)
PASS: DADAO-MC :: rwii.s (7 of 16)
PASS: DADAO-MC :: rrrr.s (8 of 16)
PASS: DADAO-MC :: iiii_jump.s (9 of 16)
PASS: DADAO-MC :: triple-smoke.s (10 of 16)
PASS: DADAO-MC :: rrri.s (11 of 16)
PASS: DADAO-MC :: riii_branch.s (12 of 16)
PASS: DADAO-MC :: rrii_branch.s (13 of 16)
PASS: DADAO-MC :: oiii.s (14 of 16)
PASS: DADAO-MC :: orri.s (15 of 16)
PASS: DADAO-MC :: orrr.s (16 of 16)

Testing Time: 0.08s

Total Discovered Tests: 16
  Passed: 16 (100.00%)
  Failed:  0 (0.00%)
```

### 3. 独立 oracle 输出
```
Results: 57 passed, 0 failed out of 57 tests
All encoding tests passed!
```

### 4. 覆盖对照表（脚本生成，逐条比对）

比对脚本：
```python
# 提取原 disassembly.s / basic-encoding.s 指令行（git show HEAD:），
# 与新文件并集逐条比对。脚本见 .work/log/llvm/LLVM-008t-coverage-check.log
```

真实输出：
```
=== 原 disassembly.s 指令行 (逐条) ===
   1. [FOUND] ld.ub rd8, rb0, 1
   2. [FOUND] ld.sb rd1, rb2, -1
   3. [FOUND] ldm.ub rd8, rb0, rd1, 2
   4. [FOUND] add.uo rd8, rd9, rd10, rd11
   5. [FOUND] add.si rd8, 1
   6. [FOUND] add.si rd8, -1
   7. [FOUND] swym 0
   8. [FOUND] swym 42
   9. [FOUND] set.zw rd8, 0, 0x1234
  10. [FOUND] or.o rd8, rd9, rd10
  11. [FOUND] rb2rd rd8, rb9, 2
  12. [FOUND] illi 0
  13. [FOUND] br.n rd0, 4
  14. [FOUND] br.n rd0, label
  15. [FOUND] swym 0
  16. [FOUND] swym 0
  17. [FOUND] ret rd0, 0

=== 原 basic-encoding.s 指令行 (逐条) ===
   1. [FOUND] add.si rd8, 1
   2. [FOUND] add.si rb1, 1
   3. [FOUND] swym 0
   4. [FOUND] br.n rd0, L1
   5. [FOUND] L1: swym 0
   6. [FOUND] L2: swym 0
   7. [FOUND] br.n rd0, L2

=== 缺失项总数: 0 ===
```

### 5. 反例门控
```
注入: sed 's/59 23 ff ff/59 23 ff fe/' basic-encoding.s → FAIL (1/1)
还原: sed 's/59 23 ff fe/59 23 ff ff/' basic-encoding.s → PASS (1/1)
git diff basic-encoding.s → 仅显示模板+add.si rd8,-1 的正常改动（注入已还原）
```

### 6. 排除项核对
```
grep 'ld.o-ra|st.o-ra|ldm.o-ra|stm.o-ra|rd2ra|ra2rd' tests/lit/MC/Dadao/*.s
→ 无匹配（正确：不含 RA 操作形式）
```

### 7. 约束核对
- `triple-smoke.s` git diff → 空（未修改）✓
- `series` → 0001–0006（未改）✓
- 每个 lit 文件（除 triple-smoke.s）OBJ=1 ASM=1 ✓

**新发现/坑**：
- `ext.uo` 在 `contracts/opcodes.yaml` 中有两个**不同 insn 条目**（非歧义）：`ext.uo` orrr（ha=0x10，4 寄存器）和 `ext.uo` orri（ha=0x18，3 操作数 + immu6），按 format 区分。本任务仅用 orri 变体（`ext.uo rd8, rd0, 1`）
- asm round-trip 对 label 形式的分支输出 `br.n rd0, ?`（非数字），ASM CHECK 需用 `{{.*}}` 通配符
- `llvm-objdump` 需通过 `make build-mc` 构建（ninja 目标包含 `llvm-objdump`）
- `add.si rd8, -1`（imms18 符号扩展路径）初版遗漏，修订后补回 basic-encoding.s

**遗留问题**：无

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-21）

**审查对象**（未提交产出）：`tests/lit/MC/Dadao/` 14 个新文件 + `basic-encoding.s`（改）+ `disassembly.s`（删）+ `tools/llvm/test_encoding_oracle.py`（扩展）。
日志留存：`.tao/logs/LLVM-008t-review-*.log`、`.work/log/llvm/LLVM-008t-review-*.log`。

#### 1. 覆盖逐条核对（脚本化，零缺失）

脚本：`/tmp/opencode/LLVM-008t/coverage_check.py`（从 `git show HEAD:` 提取原两文件的指令行，去注释/去 label，与新 15 文件并集逐条多重集比对）。
真实输出（节选，完整见 `LLVM-008t-review-coverage.log`）：

```
=== 原 disassembly.s 指令行 (逐条) ===
   ... 17 条全部 [FOUND]
--- disassembly.s 缺失项: 0 / 17 ---
=== 原 basic-encoding.s 指令行 (逐条) ===
   ... 7 条全部 [FOUND]
--- basic-encoding.s 缺失项: 0 / 7 ---
=== basic-encoding.s 4 场景核对 ===
  [FOUND] 场景1 add.si rd8,1 ... / [FOUND] 场景2 add.si rb1,1 ...
  [FOUND] 场景3 前向分支 fixup (br.n rd0, L1) / [FOUND] 场景4 后向分支 fixup (br.n rd0, L2)
=== 缺失项总数: 0 (disassembly 0 + basic 0) ===
=== 4 场景全部保留: True ===
COVERAGE_EXIT=0
```

- 原 `disassembly.s` 17 条指令行、原 `basic-encoding.s` 7 条指令行，并集比对 **缺失 0**；`basic-encoding.s` 4 场景全保留。
- `add.si rd8, -1` 已补回：`basic-encoding.s:20-26`，`OBJ:` 行为 `# OBJ: {{[0-9a-f]+:}} 59 23 ff ff{{.*}}add.si{{.*}}rd8, -1`（与主会话预期一致）。

#### 2. lit + oracle（重跑）

```
$ .work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/
Total Discovered Tests: 16
  Passed: 16 (100.00%)   Failed: 0 (0.00%)
LIT_EXIT=0
```

```
$ python3 tools/llvm/test_encoding_oracle.py
Results: 57 passed, 0 failed out of 57 tests
All encoding tests passed!
ORACLE_EXIT=0
```
与完成区数字 **一致**。

#### 3. 字节来源独立性（抽验 7 条，亲自从 opcodes.yaml 算）

脚本：`/tmp/opencode/LLVM-008t/byte_check.py`（word 由 `contracts/opcodes.yaml` 的 value + 字段 bits 独立计算，不读 lit 期望值，仅作对照）。含负立即数。

```
add.si rd8, -1   : 计算 0x5923FFFF -> 59 23 ff ff  | lit 59 23 ff ff  [MATCH]  (imms18=-1=0x3FFFF)
ld.ub rd8, rb0, 1: 计算 0x10200001 -> 10 20 00 01  | lit 10 20 00 01  [MATCH]
add.uo rd8,rd9,rd10,rd11: 计算 0x5020928B -> 50 20 92 8b | lit 50 20 92 8b [MATCH]
set.zw rd8,0,0x1234: 计算 0x4C201234 -> 4c 20 12 34 | lit 4c 20 12 34 [MATCH]
or.o rd8,rd9,rd10 : 计算 0x4024824A -> 40 24 82 4a  | lit 40 24 82 4a  [MATCH]
ext.uo rd8,rd0,1  : 计算 0x40608001 -> 40 60 80 01  | lit 40 60 80 01  [MATCH]
rb2rd rd8,rb9,2   : 计算 0x40D88242 -> 40 d8 82 42  | lit 40 d8 82 42  [MATCH]
=== 抽验 7 条，全部一致: True ===  (BYTE_EXIT=0)
```
手算示例（`add.si rd8, -1`）：`value=0x59000000` + `rd8<<18=0x200000` + `imms18(-1)=0x3FFFF` = **0x5923FFFF** → 大端字节 `59 23 ff ff`。

#### 4. 反例门控（注入在临时树，仓库零污染）

为不改 `tests/lit/`，将 `lit.cfg.py` + `basic-encoding.s` 复制到 `/tmp/opencode/LLVM-008t/inject/`，注入 1 位错误：
```
--- diff（与仓库原件）
< # OBJ: ... 59 23 ff ff{{.*}}add.si{{.*}}rd8, -1
> # OBJ: ... 59 23 ff fe{{.*}}add.si{{.*}}rd8, -1
# llvm-lit /tmp/opencode/LLVM-008t/inject/
FAIL: DADAO-MC :: basic-encoding.s (1 of 1)     INJECT_LIT_EXIT=1
# 还原（copy 回原件，diff 空）
PASS: DADAO-MC :: basic-encoding.s (1 of 1)     RESTORE_LIT_EXIT=0
```
还原证据：`diff` 为空；仓库原件与临时副本 `sha256` 相同（`4d9b8be0...`）；`git status` 无任何注入残留。
（注：本任务注入位于 lit 输入 `.s`，由 `llvm-lit` 直接读取，无需重建二进制。）

**oracle 反例门控**（自证 oracle 能被证伪）：复制 oracle 并将 `add.uo ... hd 11` 改为 `12` → `56 passed, 1 failed out of 57`，`ORACLE_INJECT_EXIT=1`；原文件未改。

#### 5. 排除项

```
$ grep -rnE 'ld\.o-ra|st\.o-ra|ldm\.o-ra|stm\.o-ra|rd2ra|ra2rd' tests/lit/MC/Dadao/
（无匹配，grep_exit=1）
```

#### 6. 约束核验（逐条）

- `encodeInstruction()` 调 `getBinaryCodeForInstr()`（`DADAOMCCodeEmitter.cpp:131`），无写 0 stub ✓
- `make build-mc` → `ninja: no work to do.` / `build-mc: PASS`，`MAKE_BUILD_MC_EXIT=0` ✓
- `triple-smoke.s` 未改：`git diff` 空、`git status` 无该文件 ✓
- `series` = 0001–0006（未改）✓；`components/` `git status` 空 ✓；`contracts/`、`spec/` 未改 ✓
- 15 个非 smoke 文件**逐文件**均有 `--check-prefix=OBJ` 与 `--check-prefix=ASM`（每文件 RUN=3）✓
- OBJ 行均为 `<hex×4>{{.*}}<mnemonic>`，无空 ASM 行、无恒真模式 ✓
- 落盘范围（`git status`）：仅任务书 + 3 个 tracked（basic-encoding.s / disassembly.s 删除 / oracle）+ 14 新文件；未改验收标准文本（任务书 diff 仅「状态」与「完成区」）。

#### 7. 完成区核对

- 「16/16 lit、57/0 oracle、反例门控 PASS」与我的重跑**逐条一致** ✓
- 「缺失项：0」与我的脚本输出一致 ✓
- `ext.uo` 描述已更正为「orrr(ha=0x10) 与 orri(ha=0x18) 两个不同 insn，非歧义」——经 `opcodes.yaml` 核对属实（`0x40400000>>18=0x10`、`0x40600000>>18=0x18`）✓
- 「asm round-trip 对 label 分支输出 `br.n rd0, ?`」经实测属实（`llvm-mc -filetype=asm riii_branch.s` 输出 `br.n rd0, ?`）✓
- 「add.si rd8, -1 初版遗漏、修订后补回」属实 ✓
- 无转述/夸大/自相矛盾。

#### 8. 非阻断观察（不影响判定）

- 新建 14 个文件（P1 列 13 + 额外的 `oiii.s`）：`oiii.s` 是承载 `illi 0`（`disassembly.s` 迁移项）所必需，属覆盖要求，不构成违规。
- oracle `TESTS` 共 57 条，但**去重后仅 50 条**（`add.si rd8,1`/`add.si rb1,1`/`ret rd0,0`/`call 1`/`jump 1`/`ext.uo rd8,rd0,1`/`illi 0` 各被重复登记 1 次）；真正 unique 新增 19 条。未丢失任何原作用例、未弱化断言，`N=57 ≥ 31+新增` 仍成立，故**不阻断**；建议后续去重使 N 反映真实覆盖，但不必为本任务返工。

#### 判决

**Accepted**。验收命令块在本人独立重跑下全部通过（lit 16/16、oracle 57/57、coverage 0 缺失、字节抽验 7/7、反例门控 FAIL→PASS、`make build-mc` PASS、排除项与约束全守）；完成区与真实输出逐条对齐。建议主会话将任务状态置为 `已验证`，交由架构师终审。
