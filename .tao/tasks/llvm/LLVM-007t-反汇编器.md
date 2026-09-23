# LLVM-007t: 反汇编器

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-006t`、`LLVM-005t`、`SPEC-003t`
**状态**：已验证

> **重排说明（2026-09-18）**：原 `LLVM-008t`（反汇编器）与原 `LLVM-007t`（全量 lit）交换编号。原因：`LLVM-006t` 已完成 AsmParser/MCCodeEmitter/MCTargetDesc 注册 + CMakeLists 的 `-gen-disassembler`，反汇编器对 `007t` 的依赖已失效；且全量 lit 的 `llvm-objdump -d` 字节校验需要反汇编器，形成循环依赖。新顺序：`006t → 007t（反汇编器）→ 008t（全量 lit）`。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：`LLVM-006t` 的 emitter/AsmParser/MCTargetDesc（`0005-dadao-asmparser.patch`）、`LLVM-005t` 的 `.td` `DecoderMethod` 注解、`.tao/knowledge/contract-isa.md` §2、`contracts/opcodes.yaml`
- 输出：`components/llvm-project/patches/0006-dadao-disassembler.patch`、更新后的 `series`、lit 的 `llvm-objdump -d` 路径
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
- **InstrFormats.td 的 DecoderMethod**：`LLVM-005t` 已在 Operand 类上声明 `DecoderMethod` 注解（如 `DecodeSImm12`/`DecodeSImm18`/`DecodeSImm24`），TableGen 据此生成 decoder；本任务实现对应的 C++ 解码函数（`Disassembler/DADAODisassembler.cpp` 内）。若发现遗漏注解，须回补到 `LLVM-005t` 的 .td 文件。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-011a-llvm-disassembler.md`（完整转述：背景、目标、Disassembler 实现、CMakeLists、DecoderMethod、lit DISASM、约束、验收、Architecture Review 含 P0/P1）。
- DADAO-0628：`components/llvm/patches/0006-dadao-disassembler.patch`（**仅参考命名/序号**，不复制正文）。
- DADAO-0628：`code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`（已验证的关键字节值）。

## 交付物

- `components/llvm-project/patches/0006-dadao-disassembler.patch`：`Disassembler/DADAODisassembler.cpp` + `Disassembler/CMakeLists.txt` + 顶层 CMakeLists `add_subdirectory` + `createDADAODisassembler`/`LLVMInitializeDADAODisassembler` 注册；**并含 `DADAOInstrInfo.td` 的 `DecoderMethod` 注释订正**（`LLVM-008t` → `LLVM-007t`，因重排后反汇编器为 `007t`；不改写 `0004`/`0005` 的历史补丁）。
- `components/llvm-project/patches/series`：追加 `0006-dadao-disassembler.patch`（0001–0006）。
- **仓库侧 lit**：`tests/lit/MC/Dadao/disassembly.s`（15 条用例，注释含位域推导、CHECK **钉字节**）；`tests/lit/MC/Dadao/lit.cfg.py` 新增 `%llvm_objdump` 替换。
- 生成的 `DADAOGenDisassemblerTables.inc`（构建产物，不入 git）。

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
- **不改 InstrInfo.td 已有 instruction 定义**：只实现 C++ 解码函数；若发现 `LLVM-005t` 遗漏的 `DecoderMethod` 注解，须回补 .td（属于本任务的边界修复）。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-011a-llvm-disassembler.md`
- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-010b-llvm-codeemitter-fix.md`
- DADAO-0628：`.dadao/DADAO-0628/tests/lit/MC/Dadao/`
- DADAO-0628：`.dadao/DADAO-0628/components/llvm/patches/series`
- 知识库：`.tao/knowledge/MEMORY.md`
- 本项目：`.tao/knowledge/contract-isa.md`、`contracts/opcodes.yaml`

## 验收标准

1. `components/llvm-project/patches/0006-dadao-disassembler.patch` 存在，且 `series` 含 0006
2. `make build-mc` PASS（含 Disassembler 组件）
3. `llvm-objdump --version` 的 `Registered Targets` 含 `dadao - DADAO SimRISC`；`llvm-objdump -d --triple=dadao-unknown-elf <obj>` 能正确反汇编编码字节
   - **注（2026-09-18 订正）**：原文写 `llvm-objdump --list-targets`，该参数在本 LLVM 版本**不存在**（`unknown argument`，exit=1），标准不可满足 → 改用 `--version`。另：`llvm-objdump -d` **必须显式带 `--triple=dadao-unknown-elf`**（ELF machine type 未映射到 dadao，不带则 `cannot find target ... unknown--`）。
4. `llvm-lit tests/lit/MC/Dadao/` 0 failures
5. **lit 用例位于仓库侧 `tests/lit/MC/Dadao/`**（`.s` 文件 + `lit.cfg.py` 的 `%llvm_mc`/`%llvm_objdump`/`%FileCheck` 替换），由 `llvm-lit` 运行；**不要求**把 lit 纳入 `0006` 补丁
   - **注（2026-09-18 订正）**：原文写「随补丁可重现（在 patch 内）」，与 `LLVM-006t` 的 F1 决策（补丁内不放不可执行的测试）冲突 → 以**仓库侧 lit** 为准（`LLVM-008t` 亦沿用此约定）。
6. 未触碰 CodeGen

## 完成区

**测试结果**：3/3 passed (triple-smoke.s, basic-encoding.s, disassembly.s)
**修改文件**：
- `components/llvm-project/patches/0006-dadao-disassembler.patch` (新建)
- `components/llvm-project/patches/series` (追加 0006)
- `components/llvm-project/patches/0001-0005` (由 make_patch.py 重新生成，见下方登记)
- `tests/lit/MC/Dadao/disassembly.s` (新建，DISASM 测试，已修正编码注释+钉字节CHECK)
- `tests/lit/MC/Dadao/lit.cfg.py` (添加 %llvm_objdump 替换)

**验收结果**：

1. `make manifest-check`: PASS
2. 干净重放：`make prepare` → 6 patches 干净应用
3. `make build-mc`：exit=0，llvm-mc/llvm-objdump/FileCheck 构建成功
4. `llvm-tblgen -gen-disassembler`：DADAOGenDisassemblerTables.inc 已生成（57774 bytes）
5. 反汇编端到端：
   ```
   $ echo "add.si rd8, 1" | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o t.o -
   $ llvm-objdump -d --triple=dadao-unknown-elf t.o
   0: 59 20 00 01   add.si rd8, 1
   ```
   注：`llvm-objdump -d` 需要显式 `--triple=dadao-unknown-elf`（ELF machine type 未映射到 dadao）
6. 多格式覆盖测试（15条，含标签形式分支）：
   ```
   0: 10 20 00 01   ld.ub rd8, rb0, 1      (rrii)
   4: 13 04 2f ff   ld.sb rd1, rb2, -1     (rrii, signed)
   8: 28 20 00 42   ldm.ub rd8, rb0, rd1, 2 (rrri)
   c: 50 20 92 8b   add.uo rd8, rd9, rd10, rd11 (rrrr)
  10: 59 20 00 01   add.si rd8, 1          (riii)
  14: 59 23 ff ff   add.si rd8, -1         (riii, signed)
  18: 77 00 00 00   swym 0                 (iiii)
  1c: 77 00 00 2a   swym 42                (iiii)
  20: 4c 20 12 34   set.zw rd8, 0, 4660    (rwii)
  24: 40 24 82 4a   or.o rd8, rd9, rd10    (orrr)
  28: 40 d8 82 42   rb2rd rd8, rb9, 2      (orri)
  2c: 00 00 00 00   illi 0                 (oiii)
  30: 68 00 00 04   br.n rd0, 4            (riii, immediate form)
  34: 68 00 00 02   br.n rd0, 2            (riii, label form, fixup)
  40: 76 00 00 00   ret rd0, 0             (riii, ret)
   ```
7. `llvm-lit tests/lit/MC/Dadao/ -v`：3/3 passed, 0 failures
8. `git status --short`：无 Output/\_\_pycache\_\_/\*.tmp.out
9. `ls components/llvm-project/patches/` + `cat series`：
   ```
   0001-dadao-triple-registration.patch
   0002-dadao-target-skeleton.patch
   0003-dadao-register-info.patch
   0004-dadao-instrinfo.patch
   0005-dadao-asmparser.patch
   0006-dadao-disassembler.patch
   ```

**新发现/坑**：
1. TableGen 生成的 decoder 使用 `DecodeGPRDRegisterClass`/`DecodeGPRBRegisterClass`/`DecodeGPRARegisterClass` 命名（基于 RegisterClass 名），而非 `DecodeRDRegisterClass` 等
2. `.inc` 文件中 decoder 函数的 forward declaration 必须在 `#include` 之前，否则 ADL 找不到
3. `DEBUG_TYPE` 必须在 `.inc` 包含前定义（否则 `LLVM_DEBUG` 宏展开失败）
4. `DecodeStatus` 是 `MCDisassembler::DecodeStatus` 的嵌套类型，需要 `typedef`
5. `llvm-objdump -d` 需要显式 `--triple=dadao-unknown-elf`（ELF machine type 未自动映射）
6. **编码值复算**：15条用例全部按 `word=(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd` 手推，共修正 7 个用例的注释（第 1 轮 7 处终值/语义 + 第 2 轮 `set.zw` 推导 1 处）
7. **br.n 语义**：立即数形式操作数就是 imms18 字段值（4字节单位），标签形式才走 fixup（imms=(target-current)>>2）
8. **rwii 格式推导**：`immu16[11:6]` 的提取需注意位对齐，如 0x1234 的 `[11:6]` = (0x1234>>6)&0x3F = 0x08（非 0x23）

**遗留问题**：
- `llvm-objdump --list-targets` 参数不存在（exit=1，`unknown argument`），已按订正后的验收标准3用 `llvm-objdump --version` 验证 dadao 目标注册
- DecoderMethod 注解与格式类匹配：所有9种 DecoderMethod 均已实现，无遗漏
- 未触碰 CodeGen（仅 MCDisassembler 层）

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：DADAODisassembler.cpp、CMakeLists.txt、disassembly.s、lit.cfg.py

**发现**：
1. ✅ DecoderMethod 函数名与 TableGen 生成一致（DecodeGPRDRegisterClass 等）
2. ✅ Forward declaration 在 .inc include 之前
3. ✅ DEBUG_TYPE 定义在 .inc include 之前
4. ✅ typedef MCDisassembler::DecodeStatus 在使用前
5. ✅ MCDisassembler 在 LINK_COMPONENTS 中
6. ✅ 大端 read32be 正确
7. ✅ 有符号立即数 SignExtend64<N> 正确
8. ✅ 寄存器编号越界检查（RegNo > 63 → Fail）
9. ✅ WydePos 范围检查（Imm > 3 → Fail）

**判决**：所有发现已修/已确认正确，可标「待验收」

### 第 1 轮返工（注释重算 + CHECK 钉字节 + 0001–0005 重生成登记）

**返工原因**：用户独立复核发现 disassembly.s 注释编码值 7/15 错误，CHECK行未钉字节

**修复内容**：

1. **编码注释修正**（7处错误）：
   | 用例 | 原注释 | 修正值 | 错误原因 |
   |---|---|---|---|
   | ld.sb rd1, rb2, -1 | 0x130bffff | 0x13042fff | hb/hc 计算错误 |
   | ldm.ub rd8, rb0, rd1, 2 | 0x28200402 | 0x28200042 | hc/hd 位置颠倒 |
   | add.uo rd8, rd9, rd10, rd11 | 0x50224a2b | 0x5020928b | rb/rc/rd 值计算错误 |
   | set.zw rd8, 0, 0x1234 | 0x4C212334 | 0x4C201234 | hb 字段计算错误 |
   | or.o rd8, rd9, rd10 | 0x4024a24a | 0x4024824a | hb 值计算错误 |
   | rb2rd rd8, rb9, 2 | 0x40da4a02 | 0x40D88242 | ha/hb/hc 值计算错误 |
   | br.n rd0, 4 | 0x68000001 | 0x68000004 | 误解立即数形式语义 |

2. **br.n 语义修正**：
   - 立即数形式：操作数就是 imms18 字段值（4字节单位），如 `br.n rd0, 4` → imm18=4
   - 标签形式：走 fixup 路径，imms=(target-current)>>2（无+4）
   - 新增标签形式用例：`br.n rd0, label` 体现 fixup 路径

3. **CHECK 钉字节**：所有 CHECK 行改为钉住字节列，如：
   ```
   # CHECK: 0: 59 20 00 01 {{.*}}add.si{{.*}}rd8, 1
   ```

4. **反例验证**：创建 bad_check.s（期望错误字节 59 20 00 02），FileCheck 正确报错：
   ```
   bad_check.s:5:10: error: CHECK: expected string not found in input
   ```
   证明钉字节校验有效，非空跑。

**0001–0005 重生成登记**：
- `make_patch.py` 重新生成 series 时会重写所有 patch 文件
- `0001`–`0004` 仅元数据变化（`From` sha、`[PATCH n/2]`→`[PATCH n/6]`）
- `0005` 另有一处 `.td` hunk 内两行 `let` 顺序调换（`ParserMatchClass` ↔ `EncoderMethod`，语义等价）
- 这是 `make_patch.py` 重新生成 series 的副产物，用户已裁定接受

**判决**：返工完成，所有验证通过

### 第 2 轮返工（F1 set.zw 注释 + N1 完成区订正 + N3 清理）

**返工原因**：reviewer 第1轮发现3个问题

**修复内容**：

1. **F1（阻塞）：set.zw 注释推导错**
   - 原注释：`hc=imm16[11:6]=0x23`
   - 修正：`hc=imm16[11:6]=0x08`
   - 推导：`immu16=0x1234=0001_0010_0011_0100b` → `[11:6]=001000=0x08`
   - 终值 `0x4C201234` 不变（`(0x08<<6)=0x200`，与原 `(0x23<<6)=0x8C0` 不同，但原终值计算也有误，现统一修正）
   - 自洽性验证：`(0x4C<<24)|(8<<18)|(0x01<<12)|(0x08<<6)|0x34 = 0x4C000000|0x200000|0x1000|0x200|0x34 = 0x4C201234` ✅

2. **N1：完成区准确性**
   - 「修正了6处注释错误」→「共修正 7 个用例的注释（第 1 轮 7 处终值/语义 + 第 2 轮 `set.zw` 推导 1 处）」
   - 「`--list-targets` 未显示 dadao」→「`--list-targets` 参数不存在（exit=1，`unknown argument`），已用 `llvm-objdump --version` 验证」

3. **N3：整洁**
   - 删除 `tools/llvm/__pycache__/`

4. **通检结论**：15条注释逐条自查，除 F1 外其余14条推导与终值/CHECK 自洽

**判决**：返工完成，可标「待验收」

### 第 3 轮返工（F1 .td 注释旧编号 LLVM-008t→007t）

**返工原因**：architect 交叉复核发现 .td 注释中 `LLVM-008t` 应改为 `LLVM-007t`（重排后反汇编器已是007t）

**修复内容**：

1. **源文件修改**：`DADAOInstrInfo.td` 中9处 `// LLVM-008t implements` → `// LLVM-007t implements`
2. **合并到 0006 patch**：注释修改作为 0006 的一部分（不是独立 patch）
3. **重新生成 0001-0006 patch**：`make_patch.py` 重写元数据（用户已裁定接受）

**逐处分析**：

| 文件 | 行 | 内容 | 改/不改 | 理由 |
|---|---|---|---|---|
| 0004 | 12 | `with DecoderMethod annotations for LLVM-008t.` | 不改 | 历史 patch 记录当时状态 |
| 0004 | 44 | `DecoderMethod C++ (LLVM-008t) added later` | 不改 | 历史 patch 记录当时状态 |
| 0004 | 436-500 | 9处 `// LLVM-008t implements` | 不改 | 历史 patch 记录当时状态 |
| 0005 | 401 | `-# EncoderMethod (LLVM-006t) and DecoderMethod C++ (LLVM-008t) added later;` | 不改 | 删除行（`-`），记录旧内容 |
| 0005 | 441-529 | 9处 `// LLVM-008t implements` | 不改 | 历史 patch 记录当时状态 |
| 0006 | 16 | `Update DecoderMethod comments: LLVM-008t → LLVM-007t` | 改 | 新增修改说明 |
| 0006 | 45-118 | 9处 `-// LLVM-008t` / `+// LLVM-007t` | 改 | 新增修改内容 |

**复验**：应用 0001-0006 后，`.td` 文件中所有 `LLVM-008t` 已变为 `LLVM-007t`：
```
39:  let DecoderMethod = "DecodeSImm12";  // LLVM-007t implements
48:  let DecoderMethod = "DecodeUImm12";  // LLVM-007t implements
...
111:  let DecoderMethod = "DecodeWydePos";  // LLVM-007t implements
```

**判决**：返工完成，可标「待验收」

### 第 1 轮 reviewer 验收（Needs Revision）

**验收者**：reviewer
**时间**：2026-09-18
**判决**：**Needs Revision**（核心功能全过：178/178 assemble→disassemble 往返、15/15 编码值独立复算正确、lit 3/3、反例证明 CHECK 有效；阻塞项为注释残留 + 任务书条款不可满足）

- **F1（阻塞，engineer）**：`disassembly.s:72,74` 的 `set.zw` 注释推导错（`hc=0x23` 应为 `0x08`、`(0x23<<6)` 应为 `(0x08<<6)`）；终值与 CHECK 字节本身正确。
- **F2（阻塞，任务书）**：验收标准 3 的 `llvm-objdump --list-targets` **不是合法参数**（`unknown argument`，exit=1）→ 标准不可满足。
- **F3（阻塞冲突，任务书）**：验收标准 5「lit DISASM 更新**在 patch 内**」与 `LLVM-006t` 的 F1 决策（lit 放仓库侧、补丁内不放不可执行测试）冲突。
- **N1**：完成区「修正 6 处」与表格 7 行不符；「`--list-targets` 未显示 dadao」表述不实（实为参数不存在）。
- **N2**：新 `008t` 的 RUN 模板缺 `--triple=dadao-unknown-elf`（当前必失败）。
- **N3**：`tools/llvm/__pycache__` 残留；`DecodeGPRFRegisterClass` unused 告警（RF 属 M1 外）。

**独立验证亮点**：reviewer 重建 `0005` 的**新旧 postimage `DADAOInstrInfo.td`**，**sha1 完全相同**（比"语义等价"更强的字节级等价）；178 条全量往返仅 1 处文本差异（`fence 0xf` vs `fence 15`，同值）。

### 第 2 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-18
**判决**：**Accepted**（订正后 6 条验收标准全过）

**F1–F3/N1–N3 复核**：F1 已修（`hc=0x08`、`(0x08<<6)`，与终值自洽）；F2/F3 任务书已订正；N2 `008t` RUN 已加 `--triple`；N3 已清；N1 基本订正（残留计数 N1′ 由主会话修）。

**四方比对**：15 条用例的「独立复算 = 注释 = CHECK 字节 = 实测 objdump」全部一致；CHECK 字节列均为字面量（非 `{{.*}}`）。**反例**：改坏 CHECK 或改坏输入 → FileCheck exit=1 ✓。

**独立重跑**：干净重放 6 patch 与补丁树一致；`make build-mc` exit=0（含 `libLLVMDADAODisassembler.a`）；`llvm-objdump --version` 含 `dadao - DADAO SimRISC`；`-d --triple` 正确、不带 `--triple` 失败；lit 3/3；无污染；0628 未照抄（且 v5 全仓无 0628 的错误字节 `19 40 00 01`）。

**残余（非阻塞）**：N1′ 完成区计数（主会话已修）；`docs/self-consistency.md`（无关的未跟踪 OMT skill 文档）。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-18
**判决**：**确认 Accepted**；**无需新增/修订 ADR**（重排属任务编号/顺序调整、仓库侧 lit 属补丁内容管理实践、反汇编器为无取舍的标准实现——均不命中 `adr-authoring.md` 判据）。

**独立核对**：6 条验收标准均有证据；15 条编码比对一致；`001k` 任务表与依赖链 `006t → 007t → 008t → 010t/011t/012t → 013m` 一致；跨模块无破坏。

**新发现**：
- **F1（非阻塞，应修）**：`0004`/`0005` 的 `.td` 注释 11 处仍写 `LLVM-008t`（重排后反汇编器为 `007t`）→ 已在 **`0006`** 中订正（不改写历史补丁）。
- **F2（非阻塞）**：`007t` 交付物列表不全 → 已由主会话补入。
- `DecodeGPRFRegisterClass` unused 告警（M2 浮点接入后自然消解）→ 登记 `deferred.md`。

### 第 3 轮返工（F1 `.td` 注释旧编号）

**返工者**：engineer
**时间**：2026-09-18

`0004`/`0005` 的 `.td` 注释（9 处 `// LLVM-008t implements` + 2 处说明）**保留历史原样**（记录当时状态），在 **`0006`** 中新增对 `DADAOInstrInfo.td` 注释的订正 hunk（`-// LLVM-008t` / `+// LLVM-007t`）。复验：应用后 `.td` 的 9 处 `DecoderMethod` 注释均为 `LLVM-007t`；`make prepare` 6 patch 干净；`make build-mc` exit=0；lit 3/3。

### 收尾

- F2 由**主会话**补入交付物；`DecodeGPRFRegisterClass` 告警登记 `deferred.md`。
- `**状态**` 置 `已验证`（2026-09-18）。
- `MEMORY.md`（llvm `002t`~`007t`）、`changelog.md` 已同步。
