# LLVM-008t: 反汇编器

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-007t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-007t` 的 emitter/AsmParser、`.tao/knowledge/contract-isa.md` §2、`verif/opcodes.yaml`
- 输出：`components/llvm/patches/0006-dadao-disassembler.patch`、更新后的 `series`、lit 的 `llvm-objdump -d` 路径
- 约束：`make build-mc` PASS；`llvm-lit tests/lit/MC/Dadao/` 0 failures；`series` 必须包含 0006；lit DISASM 更新必须纳入补丁（可重现）；只涉及 MCDisassembler，不触碰 CodeGen

## 背景（完整）

### 目标

1. 新建 `DADAODisassembler.cpp`，实现 `getInstruction()` 及操作数解码方法。
2. 接入 TableGen `-gen-disassembler`，生成 `DADAOGenDisassemblerTables.inc`。
3. 更新 lit 文件增加 `llvm-objdump -d` 路径（字节级验证）。
4. `make build-mc` PASS，`llvm-lit tests/lit/MC/Dadao/` 0 failures。

### 设计理由

- 反汇编器是 MC 层完整闭环（汇编 → object → 反汇编 → 文本）的必要步骤，也是 0628 `DL-010b` 遗留的字节级测试债务的关闭手段。

### 关键概念 / 数据

- **文件**：`Disassembler/CMakeLists.txt`（`add_llvm_component_library`）、`Disassembler/DADAODisassembler.cpp`、顶层/MCTargetDesc CMakeLists 加 `add_subdirectory(Disassembler)` 与 `tablegen(... -gen-disassembler)`。
- **操作数解码**：`DecodeRDRegisterClass`/`DecodeRBRegisterClass`（RegNo ≥ 64 → Fail，`DADAO::RD0/RB0 + RegNo`）；有符号立即数模板 `DecodeSImm<N>`（`SignExtend64`）；cfxcode 解码。
- **getInstruction**：`Bytes.size() < 4` → Fail；`Size = 4`；`uint32_t Insn = support::endian::read32be(Bytes.data());`；`decodeInstruction(DecoderTable32, MI, Insn, Address, this, STI)`。
- **工厂注册**：`createDADAODisassembler` + `LLVMInitializeDADAODisassembler`（`RegisterMCDisassembler`）。
- **InstrFormats.td 的 DecoderMethod**：每个格式类操作数需 `DecoderMethod` 注解，TableGen 才能生成正确 decoder；有符号立即数（imms12/imms18/imms24）须显式设 `DecodeSImm12/18/24`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-011a-llvm-disassembler.md`（完整转述：背景、目标、Disassembler 实现、CMakeLists、DecoderMethod、lit DISASM、约束、验收、Architecture Review 含 P0/P1）。
- DADAO-0628：`components/llvm/patches/0006-dadao-disassembler.patch`（**仅参考命名/序号**，不复制正文）。
- DADAO-0628：`code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`（已验证的关键字节值）。

## 交付物

- `components/llvm/patches/0006-dadao-disassembler.patch`：Disassembler 组件 + CMakeLists + InstrFormats DecoderMethod + lit DISASM 更新。
- `components/llvm/patches/series`：追加 `0006-dadao-disassembler.patch`（0001–0006）。
- 生成的 `DADAOGenDisassemblerTables.inc`（构建产物）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **寄存器/立即数**：v5 RD/RB 枚举与立即数宽度（imms12/18/24、immu6/12/16/18）按 `contract-isa.md`；cfx 系统指令（crrr/crii/ciii）需 cfxcode 解码。
- **字节序**：大端 `read32be`（`contract-isa.md` §2.1）。
- **lit**：DISASM 期望字节按 v5 手推，不复制 0628 的字节值。
- **P0/P1 修复内建**：0628 的 P0（0006 未入 series）与 P1（lit DISASM 更新不在补丁内）在 v5 必须从一开始就避免（见「已知坑」）。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **P0（0628 DL-011a）**：patch 0006 未列入 `series`，反汇编器未构建，`llvm-objdump -d` 输出空。v5 必须确认 `series` 含 0006。
- **P1（0628 DL-011a）**：lit DISASM 更新在 patch 之外，reproducibility 受损。v5 必须把 lit 更新纳入 0006 patch（或独立 0007 patch），使 `git am` 后可重现。
- **DecoderMethod 缺失**：TableGen 默认 `createImm(bits)`（无符号原值），有符号立即数会解码错误；须显式设置。
- **注册顺序**：Disassembler 工厂须注册到 `getTheDADAOTarget()`。
- **不改 InstrInfo.td 已有 instruction 定义**：只加 DecoderMethod 注解。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-011a-llvm-disassembler.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`
- DADAO-0628：`.work/DADAO-0628/tests/lit/MC/Dadao/`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`、`verif/opcodes.yaml`

## 验收标准

1. `components/llvm/patches/0006-dadao-disassembler.patch` 存在，且 `series` 含 0006
2. `make build-mc` PASS（含 Disassembler 组件）
3. `llvm-objdump --list-targets` 含 dadao；`llvm-objdump -d` 能反汇编编码字节
4. `llvm-lit tests/lit/MC/Dadao/` 0 failures
5. lit DISASM 更新随补丁可重现（在 patch 内）
6. 未触碰 CodeGen

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
