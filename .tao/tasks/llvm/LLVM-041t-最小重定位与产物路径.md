# LLVM-041t: 最小重定位与产物路径

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-040t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-040t` 的 `.s`（含 `call <label>` / `br.* <label>` / `jump <label>`）；v5 MC 层 fixup 设施。
- **输出**：单 TU 自包含下分支/call/jump 段内标签的 PCRel `<<2` 就地解析（修复任何 emitter/AsmBackend 缺口）；`obj → raw binary` 产物路径；导出的补丁（若有改动）。
- **约束**：
  - **范围（用户裁定）**：「最小重定位」= **段内标签就地解析**的 PC 相对分支/call/jump（PCRel `<<2`）+ raw binary / 最小 linker script；**完整重定位**（`contract-elf.md §2–§4`、relocation 编号/溢出/松弛、LLD、`ISS-008`）→ **M4**，本任务**不得**扩 `contract-elf.md §2–§4`、不得实现 `getRelocType` 完整表。
  - **现状事实（实测）**：`MCTargetDesc/DADAOFixupKinds.h` 已定义 `DADAO_FK_PCRel_12/18/24`；`DADAOAsmBackend::applyFixup` 已对已解析值做 `Value >> 2` 并按位宽掩码写回；`DADAOMCCodeEmitter::getMachineOpValue` 对符号表达式按 `getFixupKindForInstr` 发 fixup；`DADAOELFObjectWriter::getRelocType` 返回 0（stub）。
  - **已知风险（0628 `DL-056b`）**：`llc` 产出的 `call <符号>` 可能**不发 fixup**，致 imm 留 0（call 打到 0）。必须实测并修：AsmPrinter/MCInstLower 的符号操作数（`MO_GlobalAddress`/`MO_MachineBasicBlock`）→ MCCodeEmitter 发出正确的 PCRel fixup 并就地解析。
  - **产物路径**：`.o`（`llvm-mc -filetype=obj`）→ `llvm-objcopy -O binary --only-section=.text` flat binary（`ADR-0003 §D5` / `contract-elf.md §6`）；如需要多段拼接，按 §5.1 对齐连续拼接。**不引入 LLD**。
  - 不回归 `LLVM-040t`（`.s`）；不回归 `make check-lit`（MC 的既有 fixup 测试）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-056b`（call 符号重定位）；现有 `tests/lit/MC/Dadao/*` 的 fixup 测试——只读溯源。

## 验收标准

1. `ninja -C .work/build/llvm llc llvm-mc llvm-objcopy` 退出 0。
2. `llc` → `.s`（含 `call callee` / `br.*`）→ `llvm-mc -filetype=obj` → obj；`llvm-objdump -d` 中 **call/branch 目标非 0**，且目标字节 = `(target - PC) >> 2`（逐条核对至少 call 与一个条件分支）。
3. 给出 obj → flat binary 的完整命令与 `llvm-objcopy` 退出 0；hexdump 首字与 `.s` 首指令字节一致。
4. 若 `llvm-mc` 对该 TU 产出**多余 relocation**（跨符号）——如实报告；本任务不实现跨符号重定位（→M4）。
5. 不回归 `LLVM-040t`/`make check-lit`；补丁导出且 `make check-patch-tree` 通过。
6. 一键证据脚本 `.work/evidence/LLVM-041t/run.sh`（规格同 `LLVM-033t`；反例注入：构造/改一条 call 使目标错位 → 预期 FAIL，再还原）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
