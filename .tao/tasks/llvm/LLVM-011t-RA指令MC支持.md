# LLVM-011t: RA 指令 MC 支持

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-008t`、`LLVM-005t`、`SPEC-002t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节为**下发前预检**结论，优先级高于下文旧文本；冲突时以本节为准。

**P1 — 任务范围缩窄：TableGen/AsmParser/CodeEmitter/Disassembler 工作**已完成****（用户裁定「缩窄为 RA lit 补齐 + 验证」）：
- RA 指令 def **已存在**于 `DADAOInstrInfo.td`，由 **patch `0004`（= `LLVM-005t`）** 引入：`ld_o_ra`（op=0x24）/`st_o_ra`（0x25）/`ldm_o_ra`（0x3C）/`stm_o_ra`（0x3D）；`rd2ra`（ha=0x2D）/`ra2rd`（ha=0x2E）亦已定义
- ⇒ 原交付物「RA 指令补丁 + AsmParser/CodeEmitter/Disassembler 支持」**无需再做**；**本任务不改任何补丁**

**P2 — 消歧方案：已实现「方案 B」且与 spec 一致**：
- 实测 def 的 `AsmName` 为 `"ld.o"`（与 `ld.o-rd`/`ld.o-rb` **同名**），靠**寄存器类**（`GPRA` vs `GPRD`/`GPRB`）消歧 ⇒ **方案 B 已落地**
- `contract-isa §4.9` 的写法即 **`ld.o raha, rbhb, imms12`**（同一助记符 + RA 操作数）⇒ **方案 B 与 spec 一致**；原任务书「**推荐方案 A**（`ld.o-ra`）」**偏离 spec**，已作废
- 实测：`ld.o ra1, rb2, 0` 与 `ld.o rb1, rb2, 0` **均可汇编** ✓

**P3 — 删除错误的 `set.rd` 条**：原「`set.rd rd, ra` 伪指令展开为 `ra2rd`」**不成立**——`set.rd` **不在 `contracts/opcodes.yaml`**；spec（`DADAO-11-AEE`/`DADAO-22-SBI`）中的 `set.rd` 是「**装载立即数到 RD**」的伪指令（`set.rd rd2, 0`、`set.rd rd3, 0x40000000000`），与 RA↔RD 复制无关；实测 `set.rd` 不可汇编。**本任务不处理 `set.rd`**（且「助记符 1:1、不加 alias」原则下不应引入）。

**P4 — 实测基线（RA 已全可用，本任务须复验并固化）**：

| 指令 | 实测字节 | `opcodes.yaml` |
|---|---|---|
| `ld.o ra1, rb2, 0` | `24 04 20 00` | op=0x24 ✓ |
| `st.o ra1, rb2, 8` | `25 04 20 08` | op=0x25 ✓ |
| `ldm.o ra1, rb2, rd3, 2` | `3c 04 20 c2` | op=0x3C ✓ |
| `stm.o ra1, rb2, rd3, 2` | `3d 04 20 c2` | op=0x3D ✓ |
| `rd2ra ra1, rd2, 3` | `40 b4 10 83` | ha=0x2D ✓ |
| `ra2rd rd1, ra2, 3` | `40 b8 10 83` | ha=0x2E ✓ |

**反汇编 round-trip 全部一致** ✓（`llvm-objdump -d` 输出 `ld.o ra1, rb2, 0` 等）。

**P5 — 唯一真实缺口**：`tests/lit/MC/Dadao/` **无任何 RA 指令**（实测 `grep -v '^#' tests/lit/MC/Dadao/*.s | grep -c 'ra[0-9]'` = **0**）⇒ 本任务 = **补 RA lit**（沿用 `LLVM-008t` 的强模板 `--check-prefix=OBJ`+`=ASM`）+ **扩展独立 oracle**（`tools/llvm/test_encoding_oracle.py`，DRY）。


## 接口规范

- 输入：`.tao/knowledge/contract-isa.md` §4.9（RA 寄存器存取与块赋值）、§1.3.4（ra0–ra63）；`contracts/opcodes.yaml`（RA 指令编码）
- 输出：RA 指令的 TableGen def + AsmParser/CodeEmitter/Disassembler 支持 + lit 字节检查（补丁纳入 `components/llvm-project/patches/series`）
- 约束：Spec-first（编码以 `contract-isa.md`/`opcodes.yaml` 为准，不从实现反推）；助记符用 0.5.3 命名；只处理 RA 指令，不越界改其它指令

## 背景（完整）

### 目标

为 M1 的 **RA 相关指令**提供 LLVM MC 支持（汇编 / 编码 / 反汇编 / 字节级 lit 检查）：
`ld.o-ra`、`st.o-ra`（RA 单存取）、`ldm.o-ra`、`stm.o-ra`（RA 多存取）、`rd2ra`、`ra2rd`（RA↔RD 块赋值）；`set.rd rd, ra` 伪指令展开为 `ra2rd`。

### 设计理由

- RA 相关指令在 M1 范围（2026-09-12 范围变更，见 `.tao/knowledge/deferred.md`）。
- RA 是独立寄存器组（MemRAS/RegRAS），编码与操作数模型与 RD/RB 不同，**需专门任务与专门验证**，不并入 RD/RB 任务。

### 关键概念 / 数据

- RA 指令（`contract-isa.md` §4.9）：`ld.o-ra`/`st.o-ra`/`ldm.o-ra`/`stm.o-ra`/`rd2ra`/`ra2rd`。
- 编码/格式以 `contracts/opcodes.yaml` 的 `insn`/`format`/`op`/`mask`/`value`/`fields` 为准（RA 存取 op 0x24–0x25 等）。
- 助记符 0.5.3 命名（`.o` 后缀等）。

**同名助记符消歧**：`opcodes.yaml` 中 RA 存取指令的 `mnemonic` 字段与 RD/RB 变体相同（如 `ld.o-ra` 的 `mnemonic` = `ld.o`，与 `ld.o-rd`/`ld.o-rb` 同名）。AsmParser 的 `MatchInstructionImpl`（TableGen 生成）依赖 AsmString 区分指令，同名会导致匹配歧义。消歧方案（二选一，工程师实现时确定）：

- **方案 A（推荐）**：TableGen `def` 的 `AsmName` 使用 `insn` 字段全名（如 `ld.o-ra`），使汇编语法为 `ld.o-ra raha, rbhb, imms12`。优点：无歧义、与 opcodes.yaml 的 `insn` 1:1。代价：汇编文本多 `-ra` 后缀。
- **方案 B**：AsmName 用 `ld.o`（与 RD/RB 相同），在 `MatchInstructionImpl` 后通过 `MCInst` 操作数的寄存器 bank 类型（`GPRA` vs `GPRD`/`GPRB`）消歧。优点：汇编文本更自然。代价：需自定义 `MatchInstruction` 逻辑，复杂度高。

无论选哪种方案，汇编文本与 `llvm-objdump -d` 反汇编输出必须 round-trip 一致。

## 交付物

- **RA lit 文件**（`tests/lit/MC/Dadao/`，沿用 `LLVM-008t` 强模板 `--check-prefix=OBJ`+`=ASM`）：覆盖 `ld.o`/`st.o`/`ldm.o`/`stm.o` 的 RA 形式与 `rd2ra`/`ra2rd`，含 operand 边界（`ra0`、`ra63`、`immu6=0/63`）
- **扩展** `tools/llvm/test_encoding_oracle.py` 覆盖 RA 用例（独立字节 oracle，DRY）
- **不改** `components/llvm-project/patches/`（TableGen/AsmParser/CodeEmitter/Disassembler 已由 `005t`/`006t`/`007t` 完成）
- **不处理** `set.rd`（见 P3）

## 验收标准

1. `llvm-mc --triple=dadao-unknown-elf` 能汇编全部 6 条 RA 指令，字节与 `contracts/opcodes.yaml`/`contract-isa.md` 一致（**现在可跑**；须给逐条真实输出）
2. `llvm-objdump -d` 能反汇编回规范文本（round-trip，**现在可跑**；须给真实输出）
3. **RA lit 字节级 CHECK 0 failures**（**现在可跑**——这是本任务的**唯一真实缺口**，须新建 lit 文件）：`llvm-lit tests/lit/MC/Dadao/` 0 failures
4. `make build-mc` 全绿；**未越界改动非 RA 指令**；**未改任何补丁**（`git diff -- components/` 空）
5. **独立 oracle**：扩展 `tools/llvm/test_encoding_oracle.py` 覆盖 RA 用例，完成区给真实输出（`N passed / 0 failed`）；**不得**用「手推」或从 `llvm-mc` 输出复制期望字节
6. **覆盖核对**：RA lit 覆盖 6 条指令 + operand 边界（`ra0`/`ra63`/`immu6=0/63`）；逐条列出用例与归属文件
7. **反例门控**：任取一条 RA `OBJ:` 字节改错 1 位 → `llvm-lit` 必须 **FAIL**；还原（**含重建**）→ PASS
8. **未引入 alias**：确认 RA 指令的汇编语法为 `ld.o raha, ...`（方案 B，与 `contract-isa §4.9` 一致），**无** `ld.o-ra` 之类别名

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
