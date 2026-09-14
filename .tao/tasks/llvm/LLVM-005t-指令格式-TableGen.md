# LLVM-005t: 指令格式 TableGen

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-004t`、`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-004t` 的寄存器类（`GPRD`/`GPRB`/`GPRF`/`GPRA`）、`.tao/knowledge/contract-isa.md` §2（编码/格式）、§3–§5（标量指令）、§7（系统指令）、`contracts/opcodes.yaml`（机器可读编码表）
- 输出：`components/llvm/patches/0004-dadao-instrinfo.patch`、更新后的 `components/llvm/patches/series`
- 约束：`make build-mc` 仍 PASS；不实现 AsmParser/Disassembler；pattern list 为空（CodeGen 属 M2）；op/ha 值逐条对照 `contracts/opcodes.yaml`，不从 LLVM 输出反推

## 背景（完整）

### 目标

在寄存器模型上用 LLVM TableGen 定义 DADAO M1 指令的编码格式类与指令 `def`，使后续 MC CodeEmitter 能将汇编 AST 节点转换为正确字节序列，并为 `LLVM-006t`（AsmParser）提供完整指令记录。本任务不实现 AsmParser、Disassembler、ELF relocation。

### 设计理由

- 指令编码集中定义在 `.td`，由 TableGen 生成 instr-info/emitter/decoder 表，避免手写重复映射。
- 编码结构固定（32 位、大端、5 域），用格式基类 + 每格式派生类表达。

### 关键概念 / 数据

**编码结构**（`contract-isa.md` §2.1）：32 位、4 字节对齐、大端；`bits[31:24]=op[7:0]`，`bits[23:18]=ha[5:0]`，`bits[17:12]=hb[5:0]`，`bits[11:6]=hc[5:0]`，`bits[5:0]=hd[5:0]`。TableGen `bits<32> Inst` 中 bit0 为 LSB。

**格式表**（`contract-isa.md` §2.2，v5 共 12 种）：

| 格式 | 含义 | 立即数位置 |
|------|------|-----------|
| `rrrr` | 四寄存器 | 无 |
| `rrri` | 三寄存器 + 6 位立即数 | `hd[5:0]` |
| `rrii` | 两寄存器 + 12 位立即数 | `hc[5:0]+hd[5:0]`（hc 高、hd 低） |
| `riii` | 一寄存器 + 18 位立即数 | `hb[5:0]+hc[5:0]+hd[5:0]` |
| `iiii` | 24 位立即数 | `ha+hb+hc+hd` |
| `rwii` | 一寄存器 + wyde-position + 16 位无符号立即数 | `hb[5:4]=wp`，`hb[3:0]+hc+hd=immu16` |
| `orrr` | minor-opcode + 三寄存器 | `ha[5:0]=minor-op` |
| `orri` | minor-opcode + 两寄存器 + 6 位立即数 | `ha=minor-op`，`hd=immu6` |
| `oiii` | minor-opcode + 18 位立即数 | `ha=minor-op`，`hb+hc+hd=immu18` |
| `crrr` | cfxcode + 三寄存器 | `ha=cfxcode` |
| `crii` | cfxcode + 一寄存器 + 12 位立即数 | `ha=cfxcode`，`hb=rb`，`hc+hd=immu12` |
| `ciii` | cfxcode + 18 位立即数 | `ha=cfxcode`，`hb+hc+hd=immu18` |

**Wyde-Position**（§2.3）：`00`=wp0 bits[15:0]，`01`=wp1 bits[31:16]，`10`=wp2 bits[47:32]，`11`=wp3 bits[63:48]。

**MISC 子表**：op 为子表操作码（如 `0x00` AMO、`0x40` octa、`0x41` tetra、`0x42` wyde、`0x43` byte、`0x44` RF），ha 为 minor-op，用 `let ha = <minor_op>` 固定；逐条对照 `contracts/opcodes.yaml` 的 `mnemonic`/`format`/`op`/`value`。

**指令 def**：继承对应格式类，填 `op`、minor-op（如适用）、占位 asm 字符串、空 pattern；不填 `EncoderMethod`（`LLVM-006t` 添加）。

**Operand 类**：`imms12`/`immu12`/`imms18`/`immu16`/`immu6`/`imms24`/`immu18`/`wydepos` 等，声明 `DecoderMethod`（函数体在 `LLVM-008t` 实现）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-009a-llvm-instrinfo.md`（完整转述：目标、编码结构、13 格式类、指令 def、Operand 类、CMakeLists、约束、验收、Architecture Review）。
- DADAO-0628：`components/llvm/patches/0004-dadao-instrinfo.patch`（**仅参考命名与顺序**，不复制正文）。
- DADAO-0628：`contracts/isa/spec.md §2`、`components/qemu/patches/0003-dadao-decodetree.patch`（0.4.1 op 值，**不得照抄**，v5 用 `contracts/opcodes.yaml`）。

## 交付物

- `components/llvm/patches/0004-dadao-instrinfo.patch`：含 `DADAOInstrFormats.td`（格式基类 + 12 格式类）、`DADAOInstrInfo.td`（M1 指令 def + Operand 类）、`DADAO.td`（include）、`CMakeLists.txt`（`tablegen(... -gen-instr-info)`）。
- `components/llvm/patches/series`：追加 `0004-dadao-instrinfo.patch`。
- 生成的 `DADAOGenInstrInfo.inc`（构建产物）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **opcode 来源**：v5 逐条对照 `contracts/opcodes.yaml`（256 条），不得使用 0628 任务中的 op 表（0.4.1 QFC，如 `addi=0x19`/`add=0x1A` 等）。
- **格式类**：v5 按 `contract-isa.md §2.2` 的 12 格式实现（含 `crrr`/`crii`/`ciii` 系统格式）；0628 的 `F_ORII`/`F_RWII` 等命名仅作风格参考。
- **MISC 子表**：v5 为 MISC-byte/wyde/tetra/octa/RF/AMO，子表操作码与 minor-op 与 0.4.1 不同。
- **命名**：0.5.3 使用 `.b/.w/.t/.o` 与 `s`/`u` 后缀（如 `add.uo`/`add.so`、`mul.uw`/`mul.sw`、`set.zw`、`br.nz`、`illi`）。
- **M1 范围**：覆盖 `contracts/opcodes.yaml` 中 M1 标量核心（§3 标量整数、§4 地址/内存（RD/RB/**RA**）、§5 控制流、§7 系统指令中测试机所需）的全部指令；浮点 RF 全部按 M1 范围排除（是否定义占位由任务明确，不要求编码正确性）。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- `make build-mc` 必须 PASS：新 TableGen 不引入 undefined symbol 或 build error。
- 不实现 AsmParser（`LLVM-006t`）、不实现 Disassembler（`LLVM-008t`）。
- 所有 `def` 的 pattern list 为 `[]`（CodeGen isel 属 M2）。
- MISC minor-op 用字面量固定，不用寄存器字段。
- `rwii` 位域精确：`hb{5:4}=wyde-pos`，`hb{3:0}:hc:hd=immu16`。
- patch 04 紧接 03：apply 顺序 01→02→03→04。
- 0628 完成区记录 `def` 总数与 `opcodes.yaml` 条目对齐（v5 以实际 M1 条目数为准）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-009a-llvm-instrinfo.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-008a-llvm-reginfo.md`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§2–§5、§7）、`contracts/opcodes.yaml`

## 验收标准

1. `components/llvm/patches/0004-dadao-instrinfo.patch` 存在并追加到 `series`
2. `make build-mc` PASS，无新增错误
3. 构建产物含 `DADAOGenInstrInfo.inc`
4. 12 个格式类齐备；M1 指令 `def` 与 `contracts/opcodes.yaml` 的 M1 条目逐条对应（mnemonic/format/op 一致）
5. `rwii` 位域与 §2.3 一致；MISC 子表 minor-op 用字面量固定
6. 未实现 AsmParser/Disassembler；pattern list 均为 `[]`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
