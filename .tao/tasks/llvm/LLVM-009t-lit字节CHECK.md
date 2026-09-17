# LLVM-009t: lit 字节级 CHECK

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-008t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-008t` 的 Disassembler 与含 `llvm-objdump -d` RUN 行的 lit 文件、`.tao/knowledge/contract-isa.md` §2、`contracts/opcodes.yaml`
- 输出：13+ 个 `tests/lit/MC/Dadao/*.s` 的 `OBJ:`/`ASM:` 前缀与字节级 CHECK 行
- 约束：期望字节手推，禁止从 `llvm-mc`/`llvm-objdump` 输出复制；不改 `.s` 的非注释指令行；`triple-smoke.s` 不改；lit 需 build-llvm 后运行

## 背景（完整）

### 目标

对全部含 objdump RUN 行的 lit 文件：
1. 拆分 CHECK 前缀：`# CHECK:` 拆为 `# OBJ:`（objdump 输出）与 `# ASM:`（asm round-trip 输出）。
2. 每条指令加字节级 `# OBJ: <hex bytes>{{.*}}<mnemonic>` 验证实际字节。
3. 字节依据 `contract-isa.md §2.2` 公式 + `contracts/opcodes.yaml` 手工计算。

### 设计理由

- 0628 `DL-011a` 引入 Disassembler 后，若 lit 只匹配助记符文本，字节→助记符映射错误（或空字节）也会通过；字节级 OBJ 检查才能检测反汇编器/编码器缺陷。

### 关键概念 / 数据

- **编码公式**：`word[31:0] = (op << 24) | (ha << 18) | (hb << 12) | (hc << 6) | hd`。
- **字段映射**（按格式）：rrrr 四寄存器；rrii dest/src/imm；riii dest/imm18；orrr minor/dest/src1/src2；rrri dest/base/src/count；rwii dest/wyde-pos/imm；orri minor/dest/src/immu6。
- **字节序**：DADAO 大端，`word = 0xXXXX` 在内存为 `XX XX XX XX`（MSB 左）。
- **有符号立即数**：imms12 为 sign-extended 12-bit；负数取补码低 12 位。
- **改造格式**：
  ```asm
  # RUN: llvm-mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
  # RUN: llvm-objdump -d %t | FileCheck %s --check-prefix=OBJ
  # RUN: llvm-mc --triple=dadao-unknown-elf -filetype=asm %s | FileCheck %s --check-prefix=ASM

  # OBJ: <hex bytes>{{.*}}<mnemonic>
  # ASM: <mnemonic>
  ```
  字节全大写、每字节 2 位 hex、空格分隔；`{{.*}}` 吸收空白。
- **目标文件**（0628 命名参考）：`rrii_alu.s`、`rrrr.s`、`rrri.s`、`riii_branch.s`、`riii_ret.s`、`rrii_branch.s`、`rrii_load.s`、`rrii_store.s`、`iiii_jump.s`、`orrr.s`、`orri.s`、`rb_ops.s`、`rwii.s`；`triple-smoke.s` 不改。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-011b-lit-byte-checks.md`（完整转述：背景、目标、字节计算规则、改造格式、约束、验收、Architecture Review）。
- DADAO-0628：`tests/lit/MC/Dadao/`（文件组织参考）。

## 交付物

- 13+ 个 `tests/lit/MC/Dadao/*.s`：拆分 `OBJ:`/`ASM:` 前缀，含字节级 OBJ CHECK 行。
- （可选）若涉及补丁可重现性，更新 `components/llvm/patches/0006-dadao-disassembler.patch` 使 lit 更新纳入。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **op/字节来源**：`contracts/opcodes.yaml`（256 条），不复制 0628 的字节值（0628 部分示例有误）。
- **助记符**：0.5.3 命名（`.b/.w/.t/.o`、`s`/`u`、MISC 子表），lit 文件内容按 v5 重写。
- **`{{.*}}` 内建**：0628 N1 指出 OBJ 模式缺 `{{.*}}`，依赖单空格输出会静默 flake；v5 从一开始就带 `{{.*}}`。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **手推字节**：所有字节从公式 + `opcodes.yaml` 推导，禁止复制工具输出（否则无法检测工具 bug）。
- **`{{.*}}`**：吸收字节与助记符之间的空白，避免格式变化导致 flake。
- **不改指令行**：`.s` 中的实际指令行不修改。
- **保留 `triple-smoke.s` 不变**。
- **lit 需 build-llvm**：若 build 未完成，只交付 `.s` 文件并在完成区注明「lit 未运行」。
- **DataLayout 大端**：确认 `LLVM-003t` 的 DataLayout 含 `E`（大端）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-011b-lit-byte-checks.md`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-011a-llvm-disassembler.md`
- DADAO-0628：`.work/DADAO-0628/tests/lit/MC/Dadao/`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§2.1/§2.2/§2.3）、`contracts/opcodes.yaml`

## 验收标准

1. 全部含 objdump RUN 行的 lit 文件含 `--check-prefix=OBJ` 与字节级 `OBJ:` 行
2. `OBJ:` 行形如 `<hex bytes>{{.*}}<mnemonic>`，字节手推（完成区给出推导依据）
3. `triple-smoke.s` 未改
4. `llvm-lit tests/lit/MC/Dadao/` 0 failures（若已 build）
5. 未修改 `.s` 的非注释指令行

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
