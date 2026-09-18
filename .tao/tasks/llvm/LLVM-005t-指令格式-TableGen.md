# LLVM-005t: 指令格式 TableGen

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-004t`、`SPEC-003t`
**状态**：已验证

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-004t` 的寄存器类（`GPRD`/`GPRB`/`GPRF`/`GPRA`）、`.tao/knowledge/contract-isa.md` §2（编码/格式）、§3–§5（标量指令）、§7（系统指令）、`contracts/opcodes.yaml`（机器可读编码表）
- 输出：`components/llvm-project/patches/0004-dadao-instrinfo.patch`、更新后的 `components/llvm-project/patches/series`
- 约束：`make build-mc` 仍 PASS；不实现 AsmParser/Disassembler；pattern list 为空（CodeGen 属 M2）；op/ha 值逐条对照 `contracts/opcodes.yaml`，不从 LLVM 输出反推

## 背景（完整）

### 目标

在寄存器模型上用 LLVM TableGen 定义 DADAO M1 指令的编码格式类与指令 `def`，使后续 MC CodeEmitter 能将汇编 AST 节点转换为正确字节序列，并为 `LLVM-006t`（AsmParser）提供完整指令记录。本任务不实现 AsmParser、Disassembler、ELF relocation。

### 设计理由

- 指令编码集中定义在 `.td`，由 TableGen 生成 instr-info/emitter/decoder 表，避免手写重复映射。
- 编码结构固定（32 位、大端、5 域），用格式基类 + 每格式派生类表达。

### 关键概念 / 数据

**编码结构**（`contract-isa.md` §2.1）：32 位、4 字节对齐、大端；`bits[31:24]=op[7:0]`，`bits[23:18]=ha[5:0]`，`bits[17:12]=hb[5:0]`，`bits[11:6]=hc[5:0]`，`bits[5:0]=hd[5:0]`。TableGen `bits<32> Inst` 中 bit0 为 LSB。

**格式表**（`contract-isa.md` §2.3，M1 范围 9 种格式）：

> `crrr`/`crii`/`ciii` 三种格式属特权 cfx 指令（`contract-isa.md` §2.3 注、§7.5），**Excluded from M1**，本任务不实现。

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

**Wyde-Position**（§2.3）：`00`=wp0 bits[15:0]，`01`=wp1 bits[31:16]，`10`=wp2 bits[47:32]，`11`=wp3 bits[63:48]。

**MISC 子表**：op 为子表操作码（如 `0x00` AMO、`0x40` octa、`0x41` tetra、`0x42` wyde、`0x43` byte、`0x44` RF），ha 为 minor-op，用 `let ha = <minor_op>` 固定；逐条对照 `contracts/opcodes.yaml` 的 `mnemonic`/`format`/`op`/`value`。

**指令 def**：继承对应格式类，填 `op`、minor-op（如适用）、占位 asm 字符串、空 pattern；不填 `EncoderMethod`（`LLVM-006t` 添加）。

**Operand 类**：`imms12`/`immu12`/`imms18`/`immu16`/`immu6`/`imms24`/`immu18`/`wydepos` 等，**在本任务声明 `DecoderMethod`**（如 `DecodeSImm12`/`DecodeSImm18`/`DecodeSImm24`），C++ 函数体由 `LLVM-008t` 实现。TableGen `-gen-disassembler` 依赖此注解生成正确 decoder，故**注解必须在本任务写入 .td**，不可推迟到 `LLVM-008t`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-009a-llvm-instrinfo.md`（完整转述：目标、编码结构、13 格式类、指令 def、Operand 类、CMakeLists、约束、验收、Architecture Review）。
- DADAO-0628：`components/llvm/patches/0004-dadao-instrinfo.patch`（**仅参考命名与顺序**，不复制正文）。
- DADAO-0628：`contracts/isa/spec.md §2`、`components/qemu/patches/0003-dadao-decodetree.patch`（0.4.1 op 值，**不得照抄**，v5 用 `contracts/opcodes.yaml`）。

## 交付物

- `components/llvm-project/patches/0004-dadao-instrinfo.patch`：含 `DADAOInstrFormats.td`（格式基类 + 9 格式类）、`DADAOInstrInfo.td`（M1 指令 def + Operand 类）、**`DADAOInstrInfo.{h,cpp}`**（`#include` 生成的 `DADAOGenInstrInfo.inc`，使 `.inc` 真正参与编译；避免「生成物无人 include」的死代码）、`DADAO.td`（include）、`CMakeLists.txt`（`tablegen(... -gen-instr-info)` + 源文件）。
- `components/llvm-project/patches/series`：追加 `0004-dadao-instrinfo.patch`。
- 生成的 `DADAOGenInstrInfo.inc`（构建产物，不入 git）。
- **`tools/llvm/` 下的生成器与校验脚本**（口径已定，2026-09-18）：178 个 M1 指令 `def` 由脚本**从 `contracts/opcodes.yaml` 生成**（不手抄、不从 LLVM 输出反推），脚本须入库 `tools/llvm/`（依 `AGENTS.md`「生成器/脚本随产物保留」，不得只放 `/tmp`）；并提供一个**逐条对照 `opcodes.yaml` 的校验脚本**（核验验收标准 4 的 mnemonic/format/op 对应），同样入库。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **opcode 来源**：v5 逐条对照 `contracts/opcodes.yaml`（256 条），不得使用 0628 任务中的 op 表（0.4.1 QFC，如 `addi=0x19`/`add=0x1A` 等）。
- **格式类**：v5 按 `contract-isa.md §2.3` 的 9 种 M1 格式实现（`crrr`/`crii`/`ciii` 属特权 cfx，Excluded from M1）；0628 的 `F_ORII`/`F_RWII` 等命名仅作风格参考。
- **MISC 子表**：v5 为 MISC-byte/wyde/tetra/octa/RF/AMO，子表操作码与 minor-op 与 0.4.1 不同。
- **命名**：0.5.3 使用 `.b/.w/.t/.o` 与 `s`/`u` 后缀（如 `add.uo`/`add.so`、`mul.uw`/`mul.sw`、`set.zw`、`br.nz`、`illi`）。
- **M1 范围**：覆盖 `contracts/opcodes.yaml` 中 M1 标量核心（§3 标量整数、§4 地址/内存（RD/RB/**RA**）、§5 控制流、§7 系统指令中测试机所需）的全部指令；浮点 RF 全部按 M1 范围排除（是否定义占位由任务明确，不要求编码正确性）。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **`build-mc` 原只跑 `-gen-instr-info`（本任务暴露的根因，2026-09-18 补记）**：该 TableGen 调用**不需要** operand→`Inst` 位域绑定，因此 9 个格式类缺失绑定（`-gen-emitter`/`-gen-disassembler` 会失败）时门禁仍绿。本任务已把这两个 `tablegen()` 调用加入 `CMakeLists.txt`（只生成、不 include）使门禁覆盖。**教训（与 `LLVM-004t` 的 B3 同源）：验收门禁必须覆盖本任务依赖的全部 TableGen 后端**。
- **`excluded_m1` 78 条不定义（口径已定，2026-09-18）**：只定义 `contracts/opcodes.yaml` 的 **178 条 M1** 条目；`excluded_m1`（浮点 RF / 特权 cfx / LR-SC 共 78 条）**完全不定义 def**（无占位）。
- **178 个 `def` 由脚本从 `opcodes.yaml` 生成（口径已定，2026-09-18）**：脚本入库 `tools/llvm/`；另需校验脚本逐条核对 mnemonic/format/op。**不得**从 LLVM 输出反推 op/ha。
- **`DADAOInstrInfo.{h,cpp}` 必须建（口径已定，2026-09-18）**：否则生成的 `DADAOGenInstrInfo.inc` 无人 include，不会被编译（同 `LLVM-004t` F3「死代码」教训）。
- **`build-mc` 门禁已含 `LLVMDADAOCodeGen`（`LLVM-004t` 修复）**：本任务新增的 C++ 会被真实编译，`.td` 的合法性由 TableGen 运行把关。
- `make build-mc` 必须 PASS：新 TableGen 不引入 undefined symbol 或 build error。
- 不实现 AsmParser（`LLVM-006t`）、不实现 Disassembler（`LLVM-008t`）。
- 所有 `def` 的 pattern list 为 `[]`（CodeGen isel 属 M2）。
- MISC minor-op 用字面量固定，不用寄存器字段。
- `rwii` 位域精确：`hb{5:4}=wyde-pos`，`hb{3:0}:hc:hd=immu16`。
- patch 04 紧接 03：apply 顺序 01→02→03→04。
- 0628 完成区记录 `def` 总数与 `opcodes.yaml` 条目对齐（v5 以实际 M1 条目数为准：**178**）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-009a-llvm-instrinfo.md`
- DADAO-0628：`.work/DADAO-0628/components/llvm/patches/series`
- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-008a-llvm-reginfo.md`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§2–§5、§7）、`contracts/opcodes.yaml`

## 验收标准

1. `components/llvm-project/patches/0004-dadao-instrinfo.patch` 存在并追加到 `series`
2. `make build-mc` PASS，无新增错误
3. 构建产物含 `DADAOGenInstrInfo.inc`
4. 9 个格式类齐备（M1 范围，不含 `crrr`/`crii`/`ciii`）；M1 指令 `def` 与 `contracts/opcodes.yaml` 的 M1 条目逐条对应（mnemonic/format/op 一致）
5. `rwii` 位域与 §2.3 一致；MISC 子表 minor-op 用字面量固定
6. 未实现 AsmParser/Disassembler；pattern list 均为 `[]`
7. **`llvm-tblgen -gen-emitter` 与 `-gen-disassembler` 均 exit=0**，且 `CMakeLists.txt` 含这两个 `tablegen()` 调用（只生成 `.inc`、不 include），使 `build-mc` 门禁覆盖它们（防同类盲区复现；2026-09-18 追加）

## 完成区

**测试结果**：通过 8/8 + 篡改测试5/5
**修改文件**：
- `DADAOInstrFormats.td`：头注释修正（描述实际机制）
- `DADAOInstrInfo.td`：重新生成（注释同步）
- `generate_instrinfo.py`：注释模板修正
- `validate_instrinfo.py`：Check8 重写为按格式类分块解析
- `tools/llvm/__pycache__/`：已删除
- `0004-dadao-instrinfo.patch`：重新生成

**验收结果**：

1. `make manifest-check` — PASS
2. 干净重放 4 patch — PASS（reset→am 01-04）
3. `make build-mc` — **PASS**（719/719，exit=0，含4个tablegen）
4. 三个 TableGen 均 exit=0：
   ```
   -gen-instr-info: exit=0
   -gen-emitter: exit=0
   -gen-disassembler: exit=0
   ```
5. 生成物：`DADAOGenInstrInfo.inc` / `DADAOGenMCCodeEmitter.inc` / `DADAOGenDisassemblerTables.inc`
6. validate 0 errors；篡改测试 5/5 CAUGHT：
   ```
   Tamper1: ha=rb instead of ha=ra in DADAORrrr: CAUGHT
   Tamper2: deleted bits<2> wp in DADAORwii: CAUGHT
   Tamper3: imm16{15-13} instead of {15-12}: CAUGHT
   Tamper4: deleted hb{5-4}=wp: CAUGHT
   Tamper5: bits<4> rb instead of bits<6>: CAUGHT
   ALL TAMPER TESTS PASSED
   ```
7. `llvm-mc --version` 含 `dadao - DADAO SimRISC`
8. `git status --short`：无 `__pycache__`/`Output`/`*.tmp.out`

**新发现/坑**：
- `__pycache__` 在每次 `python3` 执行后都会重新生成，需在验证完成后手动删除

**遗留问题**：
- 无

## 审阅记录

### 第1轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `ops_str` 变量定义后未使用（死代码） | ✅已修 | 删除 `ops_str` 赋值行和对 `get_operand_types` 的调用 | `grep -n ops_str` 无结果 |
| `DADAOInstrFormats.td` 中 `let Inst{31-24}` 需 `field bits<32> Inst` 声明 | ✅已修 | 添加 `field bits<32> Inst;` | `make build-mc` PASS |
| 模板参数中不能用 `outs`/`ins` | ✅已修 | 改为 `let OutOperandList/InOperandList` 在 def body 中 | `make build-mc` PASS |
| `Target` 需要 `InstructionSet` | ✅已修 | 添加 `def DADAOInstrInfo : InstrInfo` 和 `let InstructionSet = ...` | `make build-mc` PASS |
| `DADAOGenInstrInfo.inc` 引用 `RegClassID` 枚举 | ✅已修 | `.h` 中 `#define GET_REGINFO_ENUM` 先 include register info | `make build-mc` PASS |
| `DADAOInstrInfo` 构造函数签名不匹配 | ✅已修 | 更新为 `(const TargetSubtargetInfo&, const TargetRegisterInfo&, ...)` | `make build-mc` PASS |
| 20个重复 insn 名称导致 def 被覆盖 | ✅已修 | `make_unique_names` 用 `(insn, format)` 元组作键 | validate: 178 defs, 0 errors |

### 第1轮 reviewer 验收（Needs Revision）

reviewer 发现：9个格式类**没有 operand→Inst 位域绑定**。基类有 `bits<6> ha/hb/hc/hd` 但 def 的操作数名（`$rdha`/`$rbhb`/`$wpN`/`$immu16`…）与字段名不同名，bits[23:0] 悬空。`-gen-instr-info` 不需要位域绑定所以 `build-mc` 没抓到。

### 第 1 轮返工（位域绑定 + 门禁）

**返工者**：engineer
**时间**：2026-09-18

- **9 个格式类补齐 operand→`Inst` 位域绑定**（`rrrr`: ha..hd=ra..rd；`rwii`: `ha=ra`、`hb{5-4}=wp`、`hb{3-0}=imm16{15-12}`、`hc=imm16{11-6}`、`hd=imm16{5-0}`；`oiii`: `hb/hc/hd=imm18{17-12}/{11-6}/{5-0}`，`ha` 为 minor-op 字面量；其余同理）。
- **`generate_instrinfo.py` 同步**：操作数名改用格式字段名（`$ra`/`$rb`/`$imm12`…），def 与格式类字段一致。
- **门禁**：`CMakeLists.txt` 新增 `-gen-emitter`/`-gen-disassembler` 两个 `tablegen()`（只生成，不 include）。
- 重新生成 `0004-dadao-instrinfo.patch`。
- 复验：`-gen-instr-info`/`-gen-emitter`/`-gen-disassembler` 三者 exit=0；`make build-mc` exit=0（`[1491/1491]`）；178 def 仍与 `opcodes.yaml` 一致。

### 第 2 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-18
**判决**：**Accepted**（6/6）

**独立重跑**：`make manifest-check` exit=0；回基线 + `make prepare`（4 patch）；`make build-mc` exit=0（`[1491/1491]`，含 4 个 tablegen）；三者 tblgen exit=0（193549/23473/57774 B）；`DADAOGenMCCodeEmitter.inc`/`DADAOGenDisassemblerTables.inc` 生成。

**独立验证（非采信 engineer）**：自写双脚本解析 9 格式类绑定 vs 从 §2.3 派生的位域模型 → 9/9 PASS；178 条逐条核对「def 操作数列表 == YAML 字段顺序/类型」且「YAML 字段 bit 范围 == 格式类绑定」→ PASS；`-print-records` 抽样（`or_w_rd`/`and_o`/`swym_iiii`/`illi`/`fence`/`ld_ub_rd`）确认字段落在正确 `Inst` 位；emitter 的 `InstBits[178]` 与 YAML `(op<<24)|(ha<<18)` 逐条比对 0 mismatch；**篡改副本法**验证 validator Check 8 有效（改坏绑定/删字段 → exit=1）。

**残余（非阻塞）**：M1 头注释仍描述废弃机制；M2 validator Check 8 为全文件正则（单类篡改不抓）；M3 `tools/llvm/__pycache__/` 未清理。

### 第 3 轮返工（M1 注释 / M2 validator 强化 / M3 清理）

| 项 | 处置 | 复验 |
|---|---|---|
| M1 | `DADAOInstrFormats.td` 头注释 + `generate_instrinfo.py` 模板改为如实描述（operand 名即字段名，TableGen 自动绑定） | grep 确认无废弃描述；重生成 `0004` |
| M2 | Check 8 改为**按格式类分块**解析并断言 `bits<>` 声明与 `let` 绑定（含 `hb{5-4}` 等子位段） | 篡改副本法 **5/5 CAUGHT**（`ha=rb`、删 `bits<2> wp`、`imm16{15-13}`、删 `hb{5-4}=wp`、`bits<4> rb`）；主会话独立复验「改真实绑定 → exit=1」 |
| M3 | 删除 `tools/llvm/__pycache__/` | `ls tools/llvm/` 仅 2 个 `.py` |

**复验**：`make build-mc` exit=0；三者 tblgen exit=0；validator 0 errors；178 def 一致；无污染。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-18
**判决**：**确认 Accepted**；**无需新增/修订 ADR**（门禁扩展属 ADR-0002 覆盖的构建编排实现细节）。

**独立核对**：6 条验收标准逐条通过；`-gen-emitter`/`-gen-disassembler` 可跑且 `.inc` 无人 include（不埋链接雷）；下游 `LLVM-006t`/`007t`/`008t` 引用与实际一致；`.inc` 未被 include、`DecoderMethod` C++ 体由 `008t` 承接（已确认）。

**新发现**：N1 任务书缺第 2 轮审阅记录/状态未置位；N2（=M1）头注释；N3 验收标准应显式加 emitter/disassembler exit=0；N4 已知坑应记门禁盲区根因 → 均已由主会话/engineer 处置。

### 收尾

- N3/N4 由**主会话**补入「验收标准 7」与「已知坑」（2026-09-18）。
- `**状态**` 置 `已验证`（2026-09-18）。
- `MEMORY.md`（llvm `002t`~`005t`）、`changelog.md` 已同步。
