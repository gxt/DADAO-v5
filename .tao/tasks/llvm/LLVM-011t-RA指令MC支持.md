# LLVM-011t: RA 指令 MC 支持

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-009t`、`LLVM-005t`、`SPEC-002t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`.tao/knowledge/contract-isa.md` §4.9（RA 寄存器存取与块赋值）、§1.3.4（ra0–ra63）；`contracts/opcodes.yaml`（RA 指令编码）
- 输出：RA 指令的 TableGen def + AsmParser/CodeEmitter/Disassembler 支持 + lit 字节检查（补丁纳入 `components/llvm/patches/series`）
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

- `components/llvm/patches/` 中 RA 指令补丁：`DADAOInstrInfo.td` 的 RA 指令 def、AsmParser/CodeEmitter/Disassembler 支持。
- lit 字节级 CHECK（`llvm-mc` 汇编 → 字节与 `opcodes.yaml` 一致；`llvm-objdump -d` 反汇编 round-trip）。
- 补丁纳入 `components/llvm/patches/series`。

## 验收标准

1. `llvm-mc --triple=dadao-unknown-elf` 能汇编全部 RA 指令，字节与 `contracts/opcodes.yaml`/`contract-isa.md` 一致
2. `llvm-objdump -d` 能反汇编回规范文本（round-trip）
3. RA 指令的 lit 字节级 CHECK 0 failures
4. `make build-mc` 全绿；未越界改动非 RA 指令

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
