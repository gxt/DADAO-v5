# LLVM-006t: AsmParser 与 CodeEmitter

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-005t`、`SPEC-003t`
**状态**：已验证

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

- `components/llvm-project/patches/0005-dadao-asmparser.patch`：`AsmParser/DADAOAsmParser.cpp`、`AsmParser/CMakeLists.txt`、`MCTargetDesc/DADAOMCCodeEmitter.cpp`、`MCTargetDesc/DADAOMCInstPrinter.cpp`、`MCTargetDesc/DADAOAsmBackend.cpp`、**`MCTargetDesc/DADAOFixupKinds.h`**（`DADAO_FK_PCRel_12/_18/_24`）、`MCTargetDesc/DADAOMCTargetDesc.{h,cpp}` 注册、顶层/MCTargetDesc CMakeLists 更新、`DADAOInstrInfo.td` 的 `ParserMatchClass`/`PrintMethod`。
- `components/llvm-project/patches/series`：追加 `0005-dadao-asmparser.patch`（顺序 01→05）。
- **仓库侧 lit**：`tests/lit/MC/Dadao/basic-encoding.s`（覆盖 `add.si` 正面编码 + **非 0 偏移前向分支** + **后向分支**；`llvm-lit tests/lit/MC/Dadao/` 应 2/2 PASS）。**注**：补丁内**不再**携带 `llvm/test/MC/Dadao/` 用例（其 RUN2 依赖 Disassembler，属 `LLVM-007t`；已删，避免提交不可执行的测试）。
- **`tools/llvm/` 入库脚本**：`gen_m1_asm.py`（从 `contracts/opcodes.yaml` 派生 178 条合法汇编行）、`test_m1_asm.py`（178 条全量可汇编）、`test_encoding_oracle.py`（**解析 `.text` 段**、按 `(op, ha, fields)` 独立重算编码并比对）。
- **不含** `DADAOSubtarget.td`（首轮曾加入，经复核为死文件——无任何 `.td` include 它——已删除）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

- **助记符/操作数**：按 0.5.3 命名与 §2.3 格式（`add.si`、`set.zw`、`br.nz`、`ld.o`、`illi` 等），操作数顺序按 `contract-isa.md` §2.5。
- **期望字节**：必须从 `contract-isa.md §2.1/§2.2` 公式 + `contracts/opcodes.yaml` 独立手推。0628 任务中的示例字节是错的（见「已知坑」），**严禁照抄**。
- **格式类字段名**：`-gen-emitter` 要求格式类 `Inst` 字段与 `def` 的操作数名对齐；v5 按自身 TableGen 结构实现，不照搬 0628 的字段名重写补丁。
- **不复制 0.4.1 补丁正文/编码数据**。

## 已知坑 / 结论

- **`applyFixup` 的 `Data` 已含 fixup 偏移（B1 根因，2026-09-18 补记）**：`MCAssembler` 传入的 `Data` **已经**是 `Contents.data() + Fixup.getOffset()`；若再写 `Data[Fixup.getOffset()…]` 会**偏移加两次**（写到 `2*offset`，只在 offset 0 碰巧正确）。正确写法是 `Data[0..3]`（对齐 Lanai）。本任务首轮犯过此错，由 reviewer 用「分支在非 0 偏移」用例抓出。
- **PCRel fixup 必须按位宽掩码（B2 根因，2026-09-18 补记）**：不同格式的立即数字段宽度不同（`br.eq/ne` = imms12、`br.n/…` = imms18、`call`/`jump` = imms24）。若用统一掩码（如 `0x3FFFF`）会截断 imms24、或污染 imms12 的寄存器字段。本任务用 3 个 fixup kind（`DADAO_FK_PCRel_12/_18/_24`）+ `MCCodeEmitter` 按格式选择。
- **P0（0628 DL-010a）**：`encodeInstruction()` 若为写 0 stub，`-filetype=obj` 会 SEGFAULT；必须调用 `getBinaryCodeForInstr()`。本任务须直接交付正确实现，避免把 stub 留到下一任务。
- **0628 任务示例字节错误（DL-010b 修正）**：`addi rd8, rd0, 1` 的期望被写成 `19 40 00 01`，实际 `19 40 00 01` 对应 `addi rd16`；正确为 `19 20 00 01`（ha=8）。v5 手推时以公式为准。
- **AsmBackend 存根必需**：0628 记录缺失 AsmBackend 导致注册崩溃。
- **MISC-Norm 重名助记符**：cmps/cmpu 等靠操作数签名区分，AsmParser 必须能区分。
- **大端**：必须 `llvm::endianness::big`，不得小端。
- **immu12 vs imms12**：`cmp.ut` 类用无符号立即数，其余 rrii 用有符号。
- **patch 05 紧接 04**：apply 顺序 01→02→03→04→05。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-010a-llvm-asmparser.md`
- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`
- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-009a-llvm-instrinfo.md`
- DADAO-0628：`.dadao/DADAO-0628/components/llvm/patches/series`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`（§2–§5）、`contracts/opcodes.yaml`

## 验收标准

1. `components/llvm-project/patches/0005-dadao-asmparser.patch` 存在并追加到 `series`
2. `make build-mc` PASS
3. `echo "add.si rd8, 1" | llvm-mc --triple=dadao-unknown-elf -filetype=asm -` 正常回显（助记符与操作数）
   - **注（2026-09-18 订正）**：原文写 `add.si rd8, rd0, 1`（3 操作数）为**笔误**——`add.si` 是 `riii`（寄存器 + imms18），正确写法 `add.si rd8, 1`。
4. `encodeInstruction()` 调用 `getBinaryCodeForInstr()`，`-filetype=obj` 不崩溃且首 4 字节等于独立手推值
5. 至少 1 个正面编码用例的期望字节来自 spec/opcodes.yaml 手推（不复制工具输出）
6. 未实现 Disassembler/ELF relocation
7. **178 条 M1 指令全部可汇编**（`tools/llvm/test_m1_asm.py`：逐条从 `opcodes.yaml` 派生合法汇编行并 `-filetype=obj`，全绿）
8. **带标签分支编码正确**：`imms=(target-current)>>2`（**无 +4**），含**非 0 偏移前向**与**后向**；fixup kind 按位宽（`DADAO_FK_PCRel_12/_18/_24`）正确掩码，**不得**截断 imms24 或污染 imms12 的寄存器字段；由仓库 lit `tests/lit/MC/Dadao/basic-encoding.s` 覆盖

## 完成区

**测试结果**：通过 全部（F1/F3 两项返工 + 7 项复验全部 PASS）。

**修改文件**：
- `components/llvm-project/patches/0005-dadao-asmparser.patch`（重新生成：F1 删除补丁内 test file；F3 订正 9 个 EncoderMethod 注释；更新 diffstat）

Patch 内容（11个文件）：
- `AsmParser/DADAOAsmParser.cpp`（新文件：汇编器解析器）
- `AsmParser/CMakeLists.txt`（新文件）
- `MCTargetDesc/DADAOAsmBackend.cpp`（新文件：含3种 fixup kind 的 applyFixup）
- `MCTargetDesc/DADAOFixupKinds.h`（新文件：PCRel_12/PCRel_18/PCRel_24）
- `MCTargetDesc/DADAOMCCodeEmitter.cpp`（新文件：按指令格式选择 fixup kind）
- `MCTargetDesc/DADAOMCInstPrinter.cpp`（新文件：反汇编打印器）
- `MCTargetDesc/DADAOMCTargetDesc.cpp`（修改：注册新组件）
- `MCTargetDesc/DADAOMCTargetDesc.h`（修改：声明新函数）
- `MCTargetDesc/CMakeLists.txt`（修改：添加新源文件）
- `CMakeLists.txt`（修改：添加 TableGen 调用）
- `DADAOInstrInfo.td`（修改：添加 AsmParserMatchClass + 订正 EncoderMethod 注释）

**验收结果**：

```
# manifest-check
manifest validation: PASS

# 回基线 + prepare
apply-series: llvm-project applied 5 patches

# build-mc
build-mc: PASS

# F1 复验
grep "llvm-objdump" 0005.patch → exit=1（未找到）
llvm-lit tests/lit/MC/Dadao/ -v → 2/2 PASS

# F3 复验
grep "EncoderMethod" 0005.patch → 9 对 -/+ 行

# 回归编码
add.si rd8, 1 → 59200001 ✓
Forward branch → 68000001 ✓
Backward branch → 6803ffff ✓
call large offset → 74040001 ✓
br.eq → 6e000001 ✓
178/178 可汇编 ✓
oracle 31/31 ✓
```

**新发现/坑**：
1. LLVM TableGen 的 `Operand` 类字段名是 `ParserMatchClass`，不是 `AsmParserMatchClass`
2. TableGen 生成的 `.inc` 文件中的成员函数带有类限定符（如 `ClassName::func()`），不能在类定义内部 include
3. `MCExpr::print()` 是私有方法，不能在 InstPrinter 中直接调用
4. `MCAsmBackend::applyFixup()` 不是 const 方法，签名需精确匹配
5. `getMachineOpValue()` 需要将 LLVM 寄存器枚举值转换为硬件编码（不同 bank 有不同偏移）
6. 需要注册 `MCSubtargetInfo` 和 `MCInstrInfo`，否则 llvm-mc 会崩溃
7. `PrintMethod` 字段必须设置为 `"printOperand"`，否则生成的打印代码为空操作
8. MCAssembler 传给 applyFixup 的 Data 已经是 `Contents.data() + Fixup.getOffset()`，不能再加 Offset（Lanai 用 Data[0..3]）
9. ELF 文件是大端的，解析时需要检测 ei_data 字节确定字节序
10. unified diff 中 context→deletion+addition 不改变 hunk header 计数
11. `br.eq` 是 rrii 格式（3 操作数），`call` 有 rrii 和 iiii 两种格式

**遗留问题**：无

## 审阅记录

### 第 1 轮返工（分支 fixup + 全量可汇编）

**背景**：首轮交付后，主会话独立复核发现：① `DADAOAsmBackend::applyFixup` 是空 stub（任务书「接口规范」要求分支偏移用 `MCFixup` + 自定义 `DADAO_FK_PCRel_2`）；② `illi` 无法汇编。另主会话一度误报 `br.n 2` 失败——实为**语法错误**（`br.n` 是 `riii`：寄存器 + imms18，正确写法 `br.n rd0, 2`）。

**返工者**：engineer（会话两次中断，产出部分落盘；清尾由主会话完成）
**时间**：2026-09-18

| 项 | 处置 | 复验 |
|---|---|---|
| `applyFixup` 空 stub | 新增 `MCTargetDesc/DADAOFixupKinds.h` + `DADAOAsmBackend` 的 `getFixupKindInfo`/`applyFixup`（`DADAO_FK_PCRel_2`，addend=0；`imms=(target-current)>>2`，**无 +4**） | `br.n rd0, target` → `applyFixup Value=4`、`Inst 68000000→68000001`（= `(4-0)>>2=1`）✓ |
| `illi` 无法汇编 | 修 AsmParser/`AsmString` 解析 | `illi 0` rc=0 ✓ |
| 验证不足 | 新增入库脚本 `tools/llvm/gen_m1_asm.py` + `test_m1_asm.py`（178 条全量可汇编）+ `test_encoding_oracle.py`（独立重算编码，不从 LLVM 输出反推） | **178/178 可汇编**、**oracle 31/31**（9 格式 + 分支类）✓ |
| 工作区残留 | engineer 调试期加入的 6 行 `fprintf(stderr,"DEBUG: …")` **未入补丁**，致工作区与补丁不一致 → 主会话 `git checkout --` 恢复 | `grep -c DEBUG:` 工作区 = 0；worktree `git status` 干净（与补丁一致）✓ |
| `__pycache__` | 主会话清理 | `tools/llvm/` 仅 5 个 `.py` ✓ |

**复验（清尾后）**：`make build-mc` exit=0；`test_m1_asm.py` 178/178；`test_encoding_oracle.py` 31/31；`add.si rd8, 1` 首 4 字节仍 `5920 0001`（回归）✓。

**新增验收（本轮追加）**：178 条 M1 **全部可汇编**；**带标签分支编码正确**（fixup 生效，无 +4）。

**engineer 会话中断说明**：两次 `task` 返回空结果；按 `AGENTS.md`「子代理返回异常处理」核对落盘后，由主会话完成清尾（恢复工作区、清 pycache、补本记录），未自行重试实现。

### 第 2 轮返工（applyFixup 双偏移/掩码 + lit 真跑）

**背景**：reviewer 发现 applyFixup 存在双偏移写址（B1）和位宽掩码恒为18位（B2）两个阻塞问题，以及若干非阻塞问题（B3-B6）。

**返工者**：engineer
**时间**：2026-09-18

| 项 | 处置 | 复验 |
|---|---|---|
| **B1：applyFixup 双偏移** | 根因：MCAssembler 传入的 `Data` 已是 `Contents.data() + Fixup.getOffset()`，原代码又用 `Data[Offset]` 取指 → 偏移加两次。修法：像 Lanai 那样用 `Data[0..3]`（相对 Data 起点）。 | B1 测试1（前向分支 offset=4）：`77000000 68000001 77000000` ✓<br>B1 测试2（后向分支）：`77000000 6803ffff` ✓<br>B1 测试3（offset=0 回归）：`68000001 77000000` ✓ |
| **B2：位宽掩码恒 0x3FFFF** | 根因：所有 PCRel fixup 统一用18位掩码，导致24位立即数（call/jump）被截断、12位立即数（br.eq/br.ne）污染寄存器字段。修法：定义3个 fixup kind（`DADAO_FK_PCRel_12`/`_18`/`_24`），MCCodeEmitter 按指令格式选择，applyFixup 按 kind 取正确掩码。 | B2 测试1（call 大偏移）：`74040001` ✓（imms24=0x40001）<br>B2 测试2（br.eq）：`6e000001` ✓（imms12=1） |
| **B3：lit 用例未生效** | 在仓库 `tests/lit/MC/Dadao/basic-encoding.s` 新增 lit 用例，覆盖 add.si 编码 + 非0偏移分支 + 后向分支。使用 `readelf -x .text` + FileCheck。 | `llvm-lit tests/lit/MC/Dadao/ -v` → 2/2 PASS ✓ |
| **B4：DADAOSubtarget.td 死文件** | 从补丁中删除。`-gen-subtarget` 仍生成空 `DADAOGenSubtargetInfo.inc`，build-mc 正常。 | `make build-mc` PASS ✓ |
| **B5：__pycache__ 清理** | 清理 `tools/llvm/__pycache__`、`tools/testcases/__pycache__`、`tools/spec/__pycache__`、`tools/infra/__pycache__`。 | `git status --short` 无 __pycache__ ✓ |
| **B6：IsResolved/Value==0** | 在 applyFixup 开头显式检查：`!IsResolved` 时直接返回（M1 无 reloc 支持）；`Value==0` 时直接返回（零偏移无需修补）。 | 逻辑已验证，无行为变化 |
| **oracle 方法学** | `parse_elf_text_section()` 现在正确解析 ELF（支持大端），按偏移比对 .text 段内容，不再在整份 ELF 中搜索4字节。 | `test_encoding_oracle.py` 31/31 PASS ✓ |

**fixup kind 设计选择**：采用方案①（定义多个 fixup kind），理由：
1. MCCodeEmitter 在 `getMachineOpValue` 时已知指令格式，可直接选择正确的 fixup kind
2. applyFixup 按 kind 取掩码，逻辑清晰
3. 符合 LLVM 标准做法（Lanai 等后端均按 fixup kind 区分位宽）

### 第 3 轮返工（F1 补丁内不可执行 lit + F3 注释订正）

**背景**：用户裁定「全修」，两项：
- **F1**：补丁内 `llvm/test/MC/Dadao/basic-encoding.s` 含不可执行的 RUN2（`llvm-objdump -d` 需 Disassembler，属 LLVM-008t）
- **F3**：`0004` 的 `.td` 注释 `EncoderMethod = "" // LLVM-006t adds` 与实现不符（编码由 C++ `getMachineOpValue()` 完成，非 EncoderMethod）

**返工者**：engineer
**时间**：2026-09-18

| 项 | 处置 | 复验 |
|---|---|---|
| **F1：补丁内不可执行 lit** | 删除 `0005` 补丁中的 `llvm/test/MC/Dadao/basic-encoding.s` 整个 diff section（含 RUN1+RUN2、CHECK/OBJ 行、create mode）。仓库侧 `tests/lit/MC/Dadao/basic-encoding.s` 已覆盖「≥1 个正面编码用例」要求。 | `grep -n "llvm-objdump" 0005.patch` → exit=1（未找到）✓<br>仓库侧 `tests/lit/MC/Dadao/basic-encoding.s` 仍在 ✓<br>`llvm-lit tests/lit/MC/Dadao/ -v` → 2/2 PASS ✓ |
| **F3：EncoderMethod 注释订正** | 在 `0005` 补丁的 `DADAOInstrInfo.td` hunk 中，将9个 Operand 类型的 `let EncoderMethod = "";  // LLVM-006t adds` 从 context 行改为 `-`/`+` 对：`-  // LLVM-006t adds` / `+  // Handled by C++ getMachineOpValue()`。不改 `0004`。同时更新 diffstat：`38 +-` → `56 +-`；总计 `11 files changed, 854 insertions(+), 61 deletions(-)`。 | `grep -n "EncoderMethod" 0005.patch` → 9 对 `-`/`+` 行，旧注释仅出现在 `-` 行，新注释在 `+` 行 ✓ |
| **diffstat 更新** | 文件数12→11（删 test file），插入869→854（-24 test + +9 comment），删除52→61（+9 comment）。hunk header `@@ -17,79 +17,99 @@` 不变（context→deletion+addition 不改计数）。 | python 验证 hunk old=79/new=99 ✓ |

**F3 落地方式说明**：0005 补丁本身修改 `DADAOInstrInfo.td`（添加 `ParserMatchClass`、修改 `PrintMethod`），该 hunk 的 context 行包含 `EncoderMethod` 注释。将9个 context 行改为 deletion+addition 对即可订正注释，不需额外 hunk。

**复验（全量）**：

```
# 1. manifest-check
$ make manifest-check
manifest validation: PASS

# 2. 回基线 → prepare（5 patch 干净应用）
$ make clean-work && make prepare
apply-series: llvm-project applied 5 patches

# 3. build-mc
$ make build-mc
build-mc: PASS

# 4. F1 复验
$ grep -rn "llvm-objdump" components/llvm-project/patches/0005-dadao-asmparser.patch
(exit=1, not found)

$ llvm-lit tests/lit/MC/Dadao/ -v
PASS: DADAO-MC :: triple-smoke.s (1 of 2)
PASS: DADAO-MC :: basic-encoding.s (2 of 2)
Testing Time: 0.03s — 2 Passed, 0 Failed

# 5. F3 复验
$ grep -n "EncoderMethod" components/llvm-project/patches/0005-dadao-asmparser.patch
401:-# EncoderMethod (LLVM-006t) ... (CMakeLists.txt deletion, OK)
439:-  let EncoderMethod = "";  // LLVM-006t adds
440:+  let EncoderMethod = "";  // Handled by C++ getMachineOpValue()
... (9 pairs total)

# 6. 回归
$ echo "add.si rd8, 1" | llvm-mc -filetype=obj | readelf -x .text
0x00000000 59200001  ✓

# Forward branch (br.n at +4 → label at +8): 68000001 ✓
# Backward branch (br.n at +4 → label at 0): 6803ffff ✓
# call large offset: call 0x040001 → 74040001 ✓
# br.eq: br.eq rd0, rd0, 1 → 6e000001 ✓

$ python3 tools/llvm/test_m1_asm.py
Results: 178 passed, 0 failed — All M1 instructions assembled successfully!

$ python3 tools/llvm/test_encoding_oracle.py
Results: 31 passed, 0 failed — All encoding tests passed!

# 7. git status
$ git status --short
(无 Output/、__pycache__、*.tmp.out)
$ git diff --stat
2 files changed, 160 insertions(+), 2 deletions(-)
(仅 .tao task file + series 修改)
```

**新发现/坑**：
1. `br.eq` 是 rrii 格式（3 操作数：`br.eq ra, rb, imm12`），不是 riii（2 操作数）。`call` 有 rrii 和 iiii 两种格式。
2. `call 0x040001` 直接用立即数产生 `74040001`；PC-relative `call label` 用 fixup 产生 `74000001` 等。
3. unified diff 中 context→deletion+addition 不改变 hunk header 计数（old/new 各+0）。

**遗留问题**：无

### 第 1 轮 reviewer 验收（Needs Revision）

**验收者**：reviewer
**时间**：2026-09-18
**判决**：**Needs Revision**

**独立重跑**：6 条主验收标准满足；但本轮新增验收「带标签分支编码正确」**不成立**：
- **B1（阻塞）** `applyFixup` 写址**双偏移**（`Data[Fixup.getOffset()…]`，而 `Data` 已含偏移）→ 分支不在 offset 0 时立即数写到下一条指令；后向分支写到界外。
- **B2（阻塞）** 掩码恒 `& 0x3FFFF`（18 位）→ `call`/`jump`（imms24）截断、`br.eq/ne`（imms12）污染 `hb` 寄存器字段。
- **B3** 补丁内 `test/MC/Dadao/basic-encoding.s` 未生效（仓库 lit 只发现 `triple-smoke.s`；上游 test 树未配置）→「≥1 正面编码用例」未被任何被执行的测试约束。
- **B4** `DADAOSubtarget.td` 是死文件（无 `.td` include 它）。
- **B5** `tools/llvm/__pycache__` 仍在（完成区「仅 5 个 .py」不实）。
- **B6** `applyFixup` 未处理 `IsResolved`/`Value==0`。
- **oracle 方法学**偏弱（`expected_bytes in data` 整份 ELF 搜字节，而非解析 `.text`）。

### 第 2 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-18
**判决**：**Accepted**（6/6 + 178 全可汇编 + 带标签分支正确）

**B1–B6 复核**：B1 已改 `Data[0..3]`（reviewer 自写 13 例 harness：off0/4/8、back4/8、自跳零，13/13 与手推一致）；B2 已改 3 个 fixup kind + 按格式选择（`call`→`74040001`、`jump`→`70040001`、`br.eq` 负值→`6e000fff`，寄存器字段未被污染）；B3 仓库 lit 新增 `basic-encoding.s` 且 **2/2 PASS**；B4 已删；B5 基本满足；B6 已显式处理；oracle 已改为 `parse_elf_text_section()` 按 `.text` 偏移比对（篡改法证明有效）。

**独立重跑**：干净重放 5 patch 与补丁树逐字节一致、无 `DEBUG:`；`make build-mc` exit=0；`add.si rd8, 1` 的 `.text` = `59200001`（独立手推同值）；**reviewer 自写脚本 178/178**；独立 oracle 20/20；13 条 fixup 边界用例全对；`llvm-lit` 2/2；无污染；0628 未照抄。

**新发现（非阻塞）**：① 补丁内旧 lit 仍在且 RUN2 依赖 Disassembler；② 越界立即数静默截断；③ 未定义符号静默为 0；④ 非分支符号操作数落入 default 分支；⑤ `getFixupKindInfo` TargetSize 恒 32；⑥ `__pycache__` 磁盘残留；⑦ repo lit 依赖系统 `readelf`。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-18
**判决**：**确认 Accepted**；**无需新增/修订 ADR**（fixup kind 设计属单模块实现细节，遵循 LLVM 标准做法；ADR-0007 覆盖注册通道、ADR-0002 覆盖构建编排）。

**独立核对**：6 条 + 新增两项通过；跨文件一致性（`DADAOSubtarget.td` 无残留、补丁内/仓库两套 lit 的关系、`LLVM-007t`/`008t` 表述）；跨模块无影响。

**新发现**：
- **F1（应修）** 补丁内 lit 的 RUN2 用 `llvm-objdump -d`（需 Disassembler，`LLVM-008t`）→ 补丁含**不可执行测试**。
- **F2** `LLVM-007t` 的 scope 已过时（CodeEmitter 修复已在 `LLVM-006t` 完成）。
- **F3** `0004` 的 `.td` 注释写 `EncoderMethod`「LLVM-006t adds」，实际由 C++ `getMachineOpValue()` 完成。
- **F4（应登记）** `rela.si` 落入 `getFixupKindForInstr` default → `PCRel_18` + `>>2`，但 `rela.si` 公式是 `imms18 << 12` → **M2 会错**。
- ②③④⑤⑥⑦ 属能力缺口/M1 限制 → deferred/不修。

### 第 3 轮返工（F1 补丁内不可执行 lit + F3 注释订正）

**返工者**：engineer
**时间**：2026-09-18

| 项 | 处置 | 复验 |
|---|---|---|
| F1 | **删除**补丁内 `llvm/test/MC/Dadao/basic-encoding.s` 整个 diff section（含 RUN1+RUN2）——仓库侧 `tests/lit/MC/Dadao/basic-encoding.s` 已覆盖「≥1 正面编码用例」 | `grep -c "llvm-objdump" 0005.patch` = 0；`llvm-lit tests/lit/MC/Dadao/ -v` 2/2 PASS |
| F3 | 在 **`0005`** 补丁的 `DADAOInstrInfo.td` hunk 中把 context 行 `// LLVM-006t adds` 改为 `-`/`+` 对 → `// Handled by C++ getMachineOpValue()`（**不改写 `0004`**） | `grep -n "EncoderMethod" 0005.patch` → 9 对 `-`/`+` 行 |

**回归复验**：`make prepare`（5 patch）→ `make build-mc` exit=0；`add.si rd8, 1` = `59200001`；前向 `68000001`；后向 `6803ffff`；`call` 大偏移 `74040001`；`br.eq` `6e000001`；178/178；oracle 通过；lit 2/2；worktree 干净、无污染。

### 收尾

- F1/F3 由 engineer 修复；**F2** 由主会话更新 `LLVM-007t` scope；**F4 与 ②③** 登记 `deferred.md`；⑤⑥⑦ 不修（有理由，见交叉复核）。
- 任务书「交付物」补入 `DADAOFixupKinds.h`/仓库 lit/`tools/llvm/` 脚本并注明 `DADAOSubtarget.td` 已删；「验收标准」新增 7/8 并订正第 3 条笔误；「已知坑」补 B1/B2 根因。
- `**状态**` 置 `已验证`（2026-09-18）。
- `MEMORY.md`（llvm `002t`~`006t`）、`changelog.md` 已同步。

### 补记（2026-09-18 重排）

**CodeEmitter 修复已在本任务完成**：原 `LLVM-007t`（CodeEmitter 修复 + 全量 lit）中的「CodeEmitter 修复」部分——`encodeInstruction()` 调用 `getBinaryCodeForInstr()`（非 stub）、`DADAO_FK_PCRel_12/_18/_24` fixup kind + `applyFixup`（`(target-current)>>2`，无 +4）——**全部在本任务（LLVM-006t）的 0005 补丁中实现并验证**。经 2026-09-18 重排，原 `LLVM-007t` 已拆分：CodeEmitter 修复归入本任务（已完成），全量 lit 归入新 `LLVM-008t`。原 `LLVM-008t`（反汇编器）重编号为 `LLVM-007t`。原 `LLVM-009t`（lit 字节级 CHECK）归并入新 `LLVM-008t`。
