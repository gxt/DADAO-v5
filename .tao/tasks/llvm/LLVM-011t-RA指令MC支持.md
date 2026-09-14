# LLVM-011t: RA 指令 MC 支持

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-009t`、`SPEC-002t`、`SPEC-003t`
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
