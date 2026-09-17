# LLVM-006t: AsmParser 与 CodeEmitter

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-005t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-005t` 的指令 `def`/格式类/Operand 类型、`.tao/knowledge/contract-isa.md` §2–§5（字段/立即数/助记符）、`contracts/opcodes.yaml`
- 输出：`components/llvm-project/patches/0005-dadao-asmparser.patch`、更新后的 `series`
- 约束：`make build-mc` PASS；`encodeInstruction` 必须调用 TableGen 生成的 `getBinaryCodeForInstr()`（不得写 0 stub）；大端输出；期望字节独立手推，不从 LLVM 输出复制；不实现 Disassembler、不实现 ELF relocation

## 背景（完整）

### 目标

在指令格式 TableGen 基础上实现 DADAO 汇编器 MC 层：AsmParser（文本汇编 → `MCInst`）、MCCodeEmitter（`MCInst` → 大端字节）、MCInstPrinter（`MCInst` → 文本，为反汇编打基础）。完成后 `llvm-mc --triple=dadao-unknown-elf -filetype=obj -o out.o test.s` 能生成正确 ELF object。

### 设计理由

- 编码大端、固定 32 位，`encodeInstruction` 直接取 `getBinaryCodeForInstr()` 的结果并按大端写出。
- AsmParser 只做语法/范围检查；操作数语义合法性（rd0 目标限制等）不在汇编器层检查。

### 关键概念 / 数据

- **寄存器解析**：`rd0–rd63` → `DADAO::RD0`…`RD63`；`rb0–rb63` → `DADAO::RB0`…`RB63`；未识别报 ParseError。
- **立即数范围**（按 Operand 类型）：`imms12`、`immu12`、`imms18`、`immu16`、`immu6`、`imms24`、`immu18`、wyde-pos 等；越界报错拒绝。
- **指令解析**：`ParseInstruction` 读助记符 → `MatchInstructionImpl`（TableGen 生成）→ 按格式读操作数序列；报清晰错误（`invalid register`、`immediate out of range`、`expected ','`）。
- **MISC 同名助记符**：通过操作数数量/类型区分（AsmVariant）。
- **MCCodeEmitter**：`encodeInstruction()` 调 `getBinaryCodeForInstr(MI, Fixups, STI)`，`support::endian::write<uint32_t>(CB, Bits, llvm::endianness::big)`。需 `#define ENABLE_INSTR_PREDICATE_VERIFIER` + `#include "DADAOGenMCCodeEmitter.inc"`（参考 Lanai）。
- **Branch/Jump 相对偏移**：DADAO 的 PC 即 `rb0`，地址公式为 `Addr = rb0 + (imm << 2)`（`contract-isa.md` §5.2/§5.3/§5.4），**无 +4 流水线偏移**。编码时 `imms = (target_byte_addr - current_byte_addr) >> 2`（有符号）。`br.n/br.nn/br.z/br.nz/br.p/br.np`（imms18）、`br.eq/br.ne`（imms12）、`call imms24`/`jump imms24`（imms24）同理；超范围用 `MCFixup` 记录。fixup kind 须自定义（如 `DADAO_FK_PCRel_2`，addend=0），**不得用 `FK_PCRel_4`**（该 kind 含 +4 流水线偏移，不适用于 DADAO）。`rela.si` 的 imms18 为重定位（`<<12`，4KB 对齐），本任务作 PCRel 占位。
- **MCInstPrinter**：寄存器 `DADAO::RD8` → `"rd8"`；立即数有符号十进制；格式 `助记符\t操作数1, 操作数2, ...`。
- **注册**：`LLVMInitializeDADAOAsmParser()`（`RegisterMCAsmParser`）。
- **AsmBackend 存根**：`MCTargetDesc/DADAOAsmBackend.cpp`（缺失会导致注册崩溃）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-010a-llvm-asmparser.md`（完整转述：目标、AsmParser/CodeEmitter/InstPrinter、lit、约束、验收、Architecture Review 两轮含 P0）。
- DADAO-0628：`components/llvm/patches/0005-dadao-asmparser.patch`（**仅参考命名与顺序**，不复制正文）。
- DADAO-0628：`code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`（其修正结论见「已知坑」）。

## 交付物

- `components/llvm-project/patches/0005-dadao-asmparser.patch`：`AsmParser/DADAOAsmParser.cpp`、`AsmParser/CMakeLists.txt`、`MCTargetDesc/DADAOMCCodeEmitter.cpp`、`MCTargetDesc/DADAOMCInstPrinter.cpp`、`MCTargetDesc/DADAOAsmBackend.cpp`、顶层/MCTargetDesc CMakeLists 更新、AsmParser 注册。
- `components/llvm-project/patches/series`：追加 `0005-dadao-asmparser.patch`。
- lit 覆盖（可与 `LLVM-007t` 合并交付；本任务至少 1 个正面编码用例）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **助记符/操作数**：按 0.5.3 命名与 §2.3 格式（`add.si`、`set.zw`、`br.nz`、`ld.o`、`illi` 等），操作数顺序按 `contract-isa.md` §2.5。
- **期望字节**：必须从 `contract-isa.md §2.1/§2.2` 公式 + `contracts/opcodes.yaml` 独立手推。0628 任务中的示例字节是错的（见「已知坑」），**严禁照抄**。
- **格式类字段名**：`-gen-emitter` 要求格式类 `Inst` 字段与 `def` 的操作数名对齐；v5 按自身 TableGen 结构实现，不照搬 0628 的字段名重写补丁。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **P0（0628 DL-010a）**：`encodeInstruction()` 若为写 0 stub，`-filetype=obj` 会 SEGFAULT；必须调用 `getBinaryCodeForInstr()`。本任务须直接交付正确实现，避免把 stub 留到下一任务。
- **0628 任务示例字节错误（DL-010b 修正）**：`addi rd8, rd0, 1` 的期望被写成 `19 40 00 01`，实际 `19 40 00 01` 对应 `addi rd16`；正确为 `19 20 00 01`（ha=8）。v5 手推时以公式为准。
- **AsmBackend 存根必需**：0628 记录缺失 AsmBackend 导致注册崩溃。
- **MISC-Norm 重名助记符**：cmps/cmpu 等靠操作数签名区分，AsmParser 必须能区分。
- **大端**：必须 `llvm::endianness::big`，不得小端。
- **immu12 vs imms12**：`cmp.ut` 类用无符号立即数，其余 rrii 用有符号。
- **patch 05 紧接 04**：apply 顺序 01→02→03→04→05。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-010a-llvm-asmparser.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-009a-llvm-instrinfo.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§2–§5）、`contracts/opcodes.yaml`

## 验收标准

1. `components/llvm-project/patches/0005-dadao-asmparser.patch` 存在并追加到 `series`
2. `make build-mc` PASS
3. `echo "add.si rd8, rd0, 1" | llvm-mc --triple=dadao-unknown-elf -filetype=asm -` 正常回显（助记符与操作数）
4. `encodeInstruction()` 调用 `getBinaryCodeForInstr()`，`-filetype=obj` 不崩溃且首 4 字节等于独立手推值
5. 至少 1 个正面编码用例的期望字节来自 spec/opcodes.yaml 手推（不复制工具输出）
6. 未实现 Disassembler/ELF relocation

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
