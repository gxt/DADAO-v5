# LLVM-029t: FP 编码层——60 条 `scope: fp` 指令汇编 / 反汇编

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：`SPEC-086t`（scope 口径）、`SPEC-087t`（FP 语义合约 / oracle 方案）、`SPEC-088t`（FP 合法性归并）——均须先 `已验证`。相关：`contracts/opcodes.yaml`（`scope: fp`，**编码唯一真源**）、`contracts/fp_semantics.yaml`、`docs/fp-oracle-design.md`、`LLVM-028t`（同类静态检查先例）。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。
> **范围边界**：本任务**只做编码层**（能汇编、能反汇编、字节正确、独立 oracle 验证）。**不含**汇编期静态合法性检查（归 `LLVM-030t`）、**不含** QEMU 执行、**不含** FP 值 oracle 实现（`GOLDEN-*`）、**不含** 向量/inventory（`TESTCASES-*`）、**不含** E2E。

---

## 0. 背景与目标

- **用户裁定（2026-10-03）**：FP 路线为**原生浮点**（否决 0628 的 soft-float libcall 路线）。
- **目标**：让 `scope: fp` 全部 **60 条**指令可被 `llvm-mc` 汇编、被 `llvm-objdump` 反汇编，且**编码字节正确**；编码正确性由**独立于 LLVM 的 oracle**（期望值派生自 `contracts/opcodes.yaml` 的 mask/value/字段布局，手算字节）验证。
- **现状**：`.td` 中 **0 条** FP 定义（`grep -n "rf\|fp\|float" DADAOInstrInfo.td` 零命中）；实测 `ftadd rf1, rf2, rf3` → `error: unrecognized instruction mnemonic`。M1 侧 MC 链路（AsmParser / MCCodeEmitter / MCInstPrinter / Disassembler）已完备。

---

## 1. 事实核实（本轮 architect 实测，file:line 为 `.work/source/llvm-project/` 内当前行号；执行时以重跑为准）

### 1.1 编码格式与寄存器类（均已具备，**无需改动**）

| 事项 | 位置 | 结论 |
|---|---|---|
| RF 寄存器类 `GPRF` | `lib/Target/DADAO/DADAORegisterInfo.td` L155–166 | **已存在**（`rf0`–`rf63`，`isAllocatable=0`，MC 用） |
| RF 寄存器 defs | 同上 L71–72 | `foreach i = 0-63 in def rf#i` |
| 6 种格式类 | `lib/Target/DADAO/DADAOInstrFormats.td` | `DADAORrii` L117、`DADAORrri` L98、`DADAORwii` L173、`DADAORrrr` L79、`DADAOOrrr` L192、`DADAOOrri` L210 —— FP 只用到这 6 种，**无需新增格式** |
| FormatKind 枚举 | `lib/Target/DADAO/DADAO.h` L40–50 | 已覆盖 FK_rrrr/rrri/rrii/rwii/orrr/orri |
| 编码器 RF 分支 | `MCTargetDesc/DADAOMCCodeEmitter.cpp` L105–106 | `getMachineOpValue` 已把 RF 寄存器 enum 3–66 映射为 6 位；通用编码器 `getBinaryCodeForInstr` L131 |
| 反汇编 RF 解码 | `Disassembler/DADAODisassembler.cpp` L74–76、L150–157 | `DecodeGPRFRegisterClass` **已实现并前向声明**（`-Wunused-function` 待 FP 引入后自然消解，见 `deferred.md`） |
| 寄存器名解析 | `AsmParser/DADAOAsmParser.cpp` L318–322 | `matchRegisterName` 已支持 `rf0`–`rf63` |

### 1.2 需要改动的 3 个源码文件（`file:line`）

1. **新建** `lib/Target/DADAO/DADAOInstrInfoFP.td`（**60 条 FP def**，见 §2.1 表）——**不改** `DADAOInstrInfo.td` 的 def 主体；仅在 `DADAOInstrInfo.td`末尾追加**一行** `include "DADAOInstrInfoFP.td"`（经既有 `DADAO.td` → `DADAOInstrInfo.td` include 链自动生效）。
   - 用户裁定（2026-10-03）：FP 定义**独立成册**，控制单文件规模（`INFRA-028t` 阈值），便于后续增删；`DADAOInstrInfo.td` 主体 153 条 def 不动。
2. `lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（1091 行）
   - L993–999：`matchAndEmitInstruction` 的「组 count 追加白名单」——`kRegGroup` 展开时只压入首寄存器并把 `GroupCount` 存进 `SavedGroupCount`，随后按 mnemonic 白名单把 count 作为最后一个操作数追加给匹配器。**白名单现含 `rd2rf`/`rf2rd`，但缺 22 条 FP 块指令**（`ft2fo`/`fo2ft`/`ft2ft`/`fo2fo`/`ft2it`/`ft2io`/`ft2ut`/`ft2uo`/`fo2it`/`fo2io`/`fo2ut`/`fo2uo`/`it2ft`/`io2ft`/`ut2ft`/`uo2ft`/`it2fo`/`io2fo`/`ut2fo`/`uo2fo`/`ftcls`/`focls`）⇒ 必须补入，否则这两个组操作数无法匹配。
   - `parseInstruction` L787–810 已按 `ldm.`/`stm.` 前缀处理 FP 的 `ldm.*`/`stm.*`；`parseRegGroup` L433–539 已支持 `{start:end}`。**无需改解析主流程**。
   - `matchRegisterName`/`isRegBankPrefix`（L318–334）已含 `rf`。
3. `MCTargetDesc/DADAOMCInstPrinter.cpp`（389 行）
   - L331–333：`FK_orri` 的**块渲染白名单**（`{dst:...}, {src:...}`）现含 `rd2rf`/`rf2rd`，**缺 22 条 FP 块指令** ⇒ 补入同一集合，否则反汇编会把块操作数渲染成标量。
   - `FK_rrri` L191–210（`ldm.`/`stm.`）、`FK_rrii` L250–259（`ld.`/`st.`）、`FK_rwii` L304–315（`set.w`）、`FK_rrrr` 的 `cs.*` L152–173 均按格式/mnemonic 通用处理，**FP 自动覆盖，无需改**。

### 1.3 ⚠️ 关键发现：`generate_instrinfo.py` / `validate_instrinfo.py` **已陈旧，不是真源**

- `DADAOInstrInfo.td` 头部虽写「Auto-generated … DO NOT EDIT MANUALLY」，但**实测二者不一致**：
  - 生成器 `tools/llvm/generate_instrinfo.py`（L30–34 只取 `scope=="m1"`）产出 def 名形如 `add_uo_rrrr_rd`/`ld_ub_rrii_rd`/`ext_uo_orrr_rd`，**152 条**；
  - 现行 `.td` def 名形如 `add_uo_rd`/`ld_ub_rd`/`ext_uo_orrr`，**153 条**（`grep -c "^def .*: DADAO"` 实测；生成器命名规则无法复现其简写）；
  - 直接运行生成器会**整体改名**，撞坏 `DADAOMCCodeEmitter.cpp` 的 `DADAO::br_eq_rd`/`DADAO::jump_iiii` 等引用 ⇒ **禁止运行生成器**。
- `tools/llvm/validate_instrinfo.py` **当前 EXIT≠0（155 errors，pre-existing）**：硬编码 178 defs（L131）、Check4「非 M1 不得定义」（L185–195，`load_excluded_opcodes` = `scope != m1`）、Check9「不得有 AsmParser」（L307–313，早已过期）。**不在 `make check` 内**（见 `Makefile` L224）。
- **结论（供用户拍板，见 §8）**：本任务**手工追加** 60 条 def，**不触碰**生成器/校验器；其陈旧问题登记 `deferred.md`，另立清理任务（不属本棒）。

### 1.4 独立 oracle 现状（本任务复用的两条链）

- `tools/llvm/check_lit_bytes.py`：遍历 `tests/lit/MC/Dadao/*.s` 的 `; OBJ:` 手写 4 字节，按 `(word & mask) == value` 在 `opcodes.yaml` 查唯一记录并比对 mnemonic（L54–56）；`N == 独立计数` 才 EXIT 0。**注意**：FP `orrr`/`orri` 的 `mask=0xFFFC0000` 只盖 op+opx，**不校验寄存器/count 字段**。
- `tools/llvm/test_encoding_oracle.py`：独立 `encode_*`（L16–50）按位运算算出**整字**期望值，跑 `llvm-mc` 取 `.text` 首字比对（L285–318）；结尾交叉校验 `unique oracle tests >= lit OBJ 行数`（L365–381）。**这才是字段级逐位独立验证**。
- `tools/integ/check_interface_alignment.py` L709 调用 `check_lit_bytes.py`；L729–777 的「lit format 族覆盖」只检查 **M1** format 集，FP 的 format 均属 M1 已有族（orri/orrr/rrrr/rrii/rrri/rwii），**不新增族、不破坏该断言**。

---

## 2. 设计

### 2.1 新建 60 条 FP def（`DADAOInstrInfoFP.td`；`DADAOInstrInfo.td` 仅 +1 行 include）

- 命名：`<id 去掉 '.'>'`（与 `contracts/opcodes.yaml` 的 id 一一对应，均以 `_rf` 结尾，与现有 153 个 def 名**无碰撞**）。例：`ftadd_orrr_rf`、`ld_t_rrii_rf`、`cs_n_rrrr_rf`、`set_w_rwii_rf`、`rd2rf_orri_rf`。
- operand 绑定**按 `fields` 声明顺序**（`role=dst` → `OutOperandList`，`role=src/imm/wyde_pos` → `InOperandList`；格式字段名用格式类的 `$ra/$rb/$rc/$rd/$imm6/$imm12/$imm16/$wp`）。
- `let op = 0xNN;`；MISC 类（orrr/orri）另 `let ha = 0xNN;`（opx）。**逐条取自 `contracts/opcodes.yaml`**（下表）。
- `let Pattern = [];`（与 M1 体例一致）。

**60 条清单**（`op`/`ha` 来自 `contracts/opcodes.yaml`；`<-dst`/`<-src` 为字段角色）：

| id | mnem | format | op | ha | fields |
|---|---|---|---|---|---|
| `ld.t_rrii_rf` | ld.t | rrii | 0x16 | - | rfha<-dst, rbhb<-src, imms12 |
| `ld.o_rrii_rf` | ld.o | rrii | 0x26 | - | rfha<-dst, rbhb<-src, imms12 |
| `st.t_rrii_rf` | st.t | rrii | 0x17 | - | rfha<-src, rbhb<-src, imms12 |
| `st.o_rrii_rf` | st.o | rrii | 0x27 | - | rfha<-src, rbhb<-src, imms12 |
| `ldm.t_rrri_rf` | ldm.t | rrri | 0x2E | - | rfha<-dst, rbhb<-src, rdhc<-src, immu6 |
| `ldm.o_rrri_rf` | ldm.o | rrri | 0x3E | - | rfha<-dst, rbhb<-src, rdhc<-src, immu6 |
| `stm.t_rrri_rf` | stm.t | rrri | 0x2F | - | rfha<-src, rbhb<-src, rdhc<-src, immu6 |
| `stm.o_rrri_rf` | stm.o | rrri | 0x3F | - | rfha<-src, rbhb<-src, rdhc<-src, immu6 |
| `set.w_rwii_rf` | set.w | rwii | 0x4F | - | rfha<-dst, wp, immu16 |
| `cs.eq_rrrr_rf` | cs.eq | rrrr | 0x5E | - | rdha<-src, rdhb<-src, rfhc<-dst, rfhd<-src |
| `cs.ne_rrrr_rf` | cs.ne | rrrr | 0x5F | - | rdha<-src, rdhb<-src, rfhc<-dst, rfhd<-src |
| `cs.n_rrrr_rf` | cs.n | rrrr | 0x61 | - | rdha<-src, rfhb<-dst, rfhc<-src, rfhd<-src |
| `cs.z_rrrr_rf` | cs.z | rrrr | 0x63 | - | rdha<-src, rfhb<-dst, rfhc<-src, rfhd<-src |
| `cs.p_rrrr_rf` | cs.p | rrrr | 0x65 | - | rdha<-src, rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftadd_orrr_rf` | ftadd | orrr | 0x44 | 0x10 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftsub_orrr_rf` | ftsub | orrr | 0x44 | 0x11 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftmul_orrr_rf` | ftmul | orrr | 0x44 | 0x12 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftdiv_orrr_rf` | ftdiv | orrr | 0x44 | 0x13 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftrem_orrr_rf` | ftrem | orrr | 0x44 | 0x14 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftsclb_orrr_rf` | ftsclb | orrr | 0x44 | 0x15 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftsgnn_orrr_rf` | ftsgnn | orrr | 0x44 | 0x16 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftsgnj_orrr_rf` | ftsgnj | orrr | 0x44 | 0x17 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `foadd_orrr_rf` | foadd | orrr | 0x44 | 0x18 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `fosub_orrr_rf` | fosub | orrr | 0x44 | 0x19 | rfhb<-dst, rfhc<-src, rfhd<-src |
| `fomul_orrr_rf` | fomul | orrr | 0x44 | 0x1A | rfhb<-dst, rfhc<-src, rfhd<-src |
| `fodiv_orrr_rf` | fodiv | orrr | 0x44 | 0x1B | rfhb<-dst, rfhc<-src, rfhd<-src |
| `forem_orrr_rf` | forem | orrr | 0x44 | 0x1C | rfhb<-dst, rfhc<-src, rfhd<-src |
| `fosclb_orrr_rf` | fosclb | orrr | 0x44 | 0x1D | rfhb<-dst, rfhc<-src, rfhd<-src |
| `fosgnn_orrr_rf` | fosgnn | orrr | 0x44 | 0x1E | rfhb<-dst, rfhc<-src, rfhd<-src |
| `fosgnj_orrr_rf` | fosgnj | orrr | 0x44 | 0x1F | rfhb<-dst, rfhc<-src, rfhd<-src |
| `ftqcmp_orrr_rf` | ftqcmp | orrr | 0x44 | 0x20 | rdhb<-dst, rfhc<-src, rfhd<-src |
| `ftscmp_orrr_rf` | ftscmp | orrr | 0x44 | 0x21 | rdhb<-dst, rfhc<-src, rfhd<-src |
| `foqcmp_orrr_rf` | foqcmp | orrr | 0x44 | 0x28 | rdhb<-dst, rfhc<-src, rfhd<-src |
| `foscmp_orrr_rf` | foscmp | orrr | 0x44 | 0x29 | rdhb<-dst, rfhc<-src, rfhd<-src |
| `ftcls_orri_rf` | ftcls | orri | 0x44 | 0x00 | rdhb<-dst, rfhc<-src, immu6 |
| `ft2fo_orri_rf` | ft2fo | orri | 0x44 | 0x01 | rfhb<-dst, rfhc<-src, immu6 |
| `ft2ft_orri_rf` | ft2ft | orri | 0x44 | 0x02 | rfhb<-dst, rfhc<-src, immu6 |
| `ftroot_orri_rf` | ftroot | orri | 0x44 | 0x06 | rfhb<-dst, rfhc<-src, immu6 |
| `focls_orri_rf` | focls | orri | 0x44 | 0x08 | rdhb<-dst, rfhc<-src, immu6 |
| `fo2ft_orri_rf` | fo2ft | orri | 0x44 | 0x09 | rfhb<-dst, rfhc<-src, immu6 |
| `fo2fo_orri_rf` | fo2fo | orri | 0x44 | 0x0A | rfhb<-dst, rfhc<-src, immu6 |
| `foroot_orri_rf` | foroot | orri | 0x44 | 0x0E | rfhb<-dst, rfhc<-src, immu6 |
| `ft2it_orri_rf` | ft2it | orri | 0x44 | 0x30 | rdhb<-dst, rfhc<-src, immu6 |
| `ft2io_orri_rf` | ft2io | orri | 0x44 | 0x31 | rdhb<-dst, rfhc<-src, immu6 |
| `ft2ut_orri_rf` | ft2ut | orri | 0x44 | 0x32 | rdhb<-dst, rfhc<-src, immu6 |
| `ft2uo_orri_rf` | ft2uo | orri | 0x44 | 0x33 | rdhb<-dst, rfhc<-src, immu6 |
| `it2ft_orri_rf` | it2ft | orri | 0x44 | 0x34 | rfhb<-dst, rdhc<-src, immu6 |
| `io2ft_orri_rf` | io2ft | orri | 0x44 | 0x35 | rfhb<-dst, rdhc<-src, immu6 |
| `ut2ft_orri_rf` | ut2ft | orri | 0x44 | 0x36 | rfhb<-dst, rdhc<-src, immu6 |
| `uo2ft_orri_rf` | uo2ft | orri | 0x44 | 0x37 | rfhb<-dst, rdhc<-src, immu6 |
| `fo2it_orri_rf` | fo2it | orri | 0x44 | 0x38 | rdhb<-dst, rfhc<-src, immu6 |
| `fo2io_orri_rf` | fo2io | orri | 0x44 | 0x39 | rdhb<-dst, rfhc<-src, immu6 |
| `fo2ut_orri_rf` | fo2ut | orri | 0x44 | 0x3A | rdhb<-dst, rfhc<-src, immu6 |
| `fo2uo_orri_rf` | fo2uo | orri | 0x44 | 0x3B | rdhb<-dst, rfhc<-src, immu6 |
| `it2fo_orri_rf` | it2fo | orri | 0x44 | 0x3C | rfhb<-dst, rdhc<-src, immu6 |
| `rd2rf_orri_rf` | rd2rf | orri | 0x40 | 0x3D | rfhb<-dst, rdhc<-src, immu6 |
| `io2fo_orri_rf` | io2fo | orri | 0x44 | 0x3D | rfhb<-dst, rdhc<-src, immu6 |
| `rf2rd_orri_rf` | rf2rd | orri | 0x40 | 0x3E | rdhb<-dst, rfhc<-src, immu6 |
| `ut2fo_orri_rf` | ut2fo | orri | 0x44 | 0x3E | rfhb<-dst, rdhc<-src, immu6 |
| `uo2fo_orri_rf` | uo2fo | orri | 0x44 | 0x3F | rfhb<-dst, rdhc<-src, immu6 |

- **块指令**（orri 中带 `immu6` 的 24 条，含 `rd2rf`/`rf2rd`）的汇编语法为 `{dst:...}, {src:...}`；标量 orri（`ftroot`/`foroot`）为 `rfHB, rfHC, immu6`（**不是**组）。
- **opex 冲突已核**：`orri@0x40` 的 fp opx（0x3D/0x3E）与 M1（0x18–0x1C/0x2C–0x2E/0x34–0x36）不相交；`orrr@0x44`/`orri@0x44` 的 fp opx 互不相交，且 M1 无 op=0x44 ⇒ TableGen 解码表无冲突（`validate-encoding` 已保证）。

### 2.2 AsmParser 组 count 白名单（L993–999）

把 L994–997 的 `Mnemonic == ...` 判断扩展为包含 22 条 FP 块 mnemonic（`rd2rf`/`rf2rd` 已在）。**加固（用户裁定 2026-10-03：FP 侧硬报错）**：当某指令的**两个操作数都是 `kRegGroup`** 时，校验两组 `getGroupCount()` **相等**，否则 `Error` 硬报错（语法共享单一 `immu6`；M1 `rd2rd` 现对不等 count 静默取末组，属 pre-existing，**本任务不改 M1 行为**，仅对 FP 块强制）。

### 2.3 MCInstPrinter 块渲染白名单（L331–333）

在 `MnemStr == "..."` 列表中加入同一 22 条 FP 块 mnemonic，使反汇编输出 `{rf4:rf6}, {rf8:rf10}` 形式。

### 2.4 lit 测试（新建 `tests/lit/MC/Dadao/fp-encoding.s`）

- 体例照 `rrii_alu.s`（强模板）：`RUN: %llvm_mc … -filetype=obj` + `RUN: %llvm_objdump -d --triple=dadao-unknown-elf … --check-prefix=OBJ` + `RUN: … -filetype=asm … --check-prefix=ASM`。
- **覆盖全部 60 条**：每条 1 行 `; OBJ:`（手写 4 字节，**不得**从 llvm-mc 复制）+ 1 行 `; ASM:`（round-trip）。字节手算自 §2.1 的 op/opx/字段布局（`word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd`）。
- 覆盖块形式（如 `ft2fo {rf4:rf6}, {rf8:rf10}`）、`cs.*-rf`、`set.w rf`、`ldm.*-rf`。

### 2.5 独立编码 oracle（`tools/llvm/test_encoding_oracle.py`，复用现有 `encode_*`）

- `REG` 字典补 `rf0`–`rf63`（至少覆盖用例用到的 rf 值）。
- `TESTS` 追加 **≥60 条 unique** FP 用例，`asm` 行与 §2.4 一致，期望 word 由 `encode_rrrr/rrri/rrii/rwii/orrr/orri` **独立算出**（`encode_orrr(op,ha,rb,rc,rd)`/`encode_orri(op,ha,rb,rc,imm6)` 已存在）。行尾交叉校验 `unique >= lit OBJ` 自动随动。
- **不得**从 `llvm-mc` 输出回填期望值（`docs/fp-oracle-design.md` 铁律；期望值只源自 `opcodes.yaml` 字段布局 + 手算）。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfoFP.td.patch` | **新建文件**（60 条 FP def） |
| 2 | `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch` | **仅 +1 行** `include "DADAOInstrInfoFP.td"` |
| 3 | `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch` | 组 count 白名单 +22 |
| 4 | `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCInstPrinter.cpp.patch` | 块渲染白名单 +22 |
| 5 | `tests/lit/MC/Dadao/fp-encoding.s` | 新建 lit（60 条） |
| 6 | `tools/llvm/test_encoding_oracle.py` | +rf 寄存器、+FP 用例 |
| 7 | `components/llvm-project/changelog.md` | 追加任务行（`Process-01 §10`） |
| 8 | `.work/evidence/LLVM-029t/run.sh` | 一键证据脚本（含 `--inject`） |
| 9 | `.work/log/llvm/LLVM-029t-*.log` | 构建/lit/oracle/check/注入完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tools/{spec,qemu,testcases}/**`、`components/qemu/**`、`tests/vectors/**`、`DADAORegisterInfo.td`（GPRF 已在）、`DADAOInstrFormats.td`、`DADAO.h`、`MCCodeEmitter.cpp`、`Disassembler/`、`tools/llvm/{generate_instrinfo,validate_instrinfo,gen_m1_asm,test_m1_asm}.py`、其它 lit。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `contracts/opcodes.yaml`（`scope: fp` 60 条：id/mnemonic/format/op/ha/mask/value/fields —— **编码期望值唯一来源，独立于 LLVM**）。
- `contracts/fp_semantics.yaml`（族/`legality_refs`，仅作旁证；本任务不实现合法性）。
- 现行 `.td` 的 6 种格式类与 M1 def 体例；`AsmParser` L993–999；`MCInstPrinter` L331–333。

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围；**失败即停，禁自动重试**；**禁止运行 `generate_instrinfo.py`**（陈旧，会改名撞坏引用）。
- **重建成本申报**：改 `.td` ⇒ `make prepare && make build-mc`（增量，预计 **5–15 分钟**；仅 `.td`/C++ 改动触发 TableGen + DADAO 目标重编译 + 重链 `llvm-mc`/`llvm-objdump`）。`JOBS` 默认 8，禁全核并行；长构建一次只跑一个。
- 临时目录 `/tmp/opencode/LLVM-029t/`；日志 `.work/log/llvm/`；证据 `.work/evidence/LLVM-029t/`。

---

## 6. 验收标准（可执行、可失败、含反例注入）

1. **构建**：`make prepare && make build-mc` EXIT 0（留 `.work/log/llvm/LLVM-029t-build.log`）。
2. **汇编**：§2.4 的 60 行全部 `llvm-mc --triple=dadao-unknown-elf -filetype=obj` EXIT 0。
3. **反汇编 round-trip**：`llvm-objdump -d --triple=dadao-unknown-elf` 对含 60 条的对象输出与 `; ASM:` 逐条一致（含块形式 `{rf4:rf6}, {rf8:rf10}`）。
4. **字节正确（独立 oracle）**：
   - `python3 tools/llvm/test_encoding_oracle.py` → 全部 PASS（含 ≥60 FP unique 用例；结尾 `unique >= lit OBJ lines`）。
   - `python3 tools/llvm/check_lit_bytes.py` → `N patterns OK`（N = 53 + 60 = 113，`N == 独立计数`）。
5. **lit**：`make check-lit` → 总数 **27→28**（新增 `fp-encoding.s`）全 PASS。
6. **`make check` 全绿**：`repository checks: PASS`（重点：`check-patch-tree` **68** patches OK、`check-interface` 80/80、`check-scope` PASS、`validate-encoding` PASS、`check-lit` 28/28）。
7. **不变量**：`contracts/opcodes.yaml`、`spec/**`、`tests/vectors/**`、QEMU 补丁**零改动**；`check-scope` 计数 152/60/15/227 不变；补丁数 **67→68**（3 改 —— `DADAOInstrInfo.td` 仅 +1 行 include / `AsmParser` / `MCInstPrinter` —— + **1 新建** `DADAOInstrInfoFP.td.patch`）。
8. **反例可失败（承重证明，逐一注入）**：
   - A：改某 FP def 的 `op`/`ha`（如 `ftadd` 的 `ha=0x10→0x11`）⇒ 重建后 oracle 对应用例 FAIL、lit FAIL；还原**并重建** ⇒ 回绿。
   - B：**删去** AsmParser 白名单中若干 FP 块 mnemonic ⇒ 对应块指令 `llvm-mc` 报错/无法匹配；还原重建回绿。
   - C：**删去** printer 白名单中若干 FP 块 mnemonic ⇒ 反汇编把块渲染成标量、`; ASM:` FAIL；还原重建回绿。
   - 每次注入须 `git -C .work/source/llvm-project diff --name-only` **非空**；还原后 `git status --porcelain` 干净且 sha256 复原。
9. **残留与越界**：`git status --untracked-files=all` 仅应改文件 + 本任务书；`check-no-residue` PASS；`git diff --name-only` 与 §3 对齐。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-029t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律（`spec/Process-01 §6/§8`，E1–E8）：动组件前先 `make check-source-state` 自检 **E1**（`.work/source/llvm-project` 干净 + HEAD=base+1）；**E2** 起点不干净须先收敛；**E3** 导出前校验 E1，不满足拒绝导出（补丁写 `/tmp`，含有效 hunk，无 0 行/空 blob）；**E4** 收敛为恰好 1 个 commit；**E5** `apply_series` 应用后自动 commit、重复应用幂等；**E6** `check-patch-tree` 断言⑦⑧⑨ + ⑥（应用产物 blob == 源树）；**E7** 改动前后各查一次 `--source-state`；**E8** 补丁为裸 `git diff`，本地 commit 永不推送上游。
7. 复杂命令输出留存 `.work/log/llvm/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/LLVM-029t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **60 条一次做完 vs 分批**：建议**一次做完**（编码实现共享 `.td`/AsmParser/printer 三文件，串行无并行收益；一次构建 5–15 分钟）。备选：按「标量 36 条」/「块 24 条」切两任务——若用户要求更小验收粒度可选，但会多一轮构建且第二任务依赖第一任务。
2. **`.td` 规模**：**已裁定（用户 2026-10-03）：新建 `DADAOInstrInfoFP.td`**（60 条 FP def 独立成册；`DADAOInstrInfo.td` 仅 +1 行 `include`）。补丁数 **67→68**（3 改 + 1 新建）；`DADAOInstrInfo.td` 主体 153 条 def 不动。
3. **`generate_instrinfo.py` 陈旧（§1.3）**：本任务手工追加、不修生成器。是否**另立清理任务**（让生成器/`validate_instrinfo.py` 可信）由用户裁定。
4. **块 count 相等检查**：**已裁定（用户 2026-10-03）**：对 FP 块「两个 `{start:end}` 组 count 不等」**硬报错**（§2.2）。M1 `rd2rd` 的静默取末组属 pre-existing，**本任务不改**；该 M1 行为差异登记 `deferred.md`。
5. **反汇编是否同棒**：建议**同棒**（编码与反汇编共享 printer 白名单，验证成本低、能证 round-trip）。若用户希望 LLVM-029t 只做「汇编→字节」，则 printer 改动移入独立任务——但会失去 round-trip 证据。**需用户裁定**。
6. **`decode: ILLI` 口径**：`check-scope` 断言 `scope!=m1 ⇒ decode=ILLI`。本任务**不改 `opcodes.yaml`**，故该断言保持绿；该字段语义（QEMU 解码 vs LLVM 解码）建议由 spec 侧澄清，但**不影响本任务**（见 §9 后续任务）。

---

## 9. 范围边界与后续任务（不在本棒）

- **不在本棒**：汇编期静态合法性（`dst_rf0`/`mreg_*`/`encode_fp_root_n`）→ **`LLVM-030t`**；FP 值 oracle 实现（`tools/golden/fp_ref.py`）→ **`GOLDEN-001t`** 起（按 `docs/fp-oracle-design.md`）；向量/inventory → **`TESTCASES-024t`**；QEMU FP decode/trans → **`QEMU-034t`**；FP E2E → **`INTEG-*`**；`opcodes.yaml` FP `rule_refs` 回填 + `dst_rf0`/`encode_fp_root_n` 翻 `active` + 重跑 `gen_legality_list`（`SimRISC-07` 生成区会变）→ **spec 侧任务（建议 `SPEC-089t`）**；`generate_instrinfo.py`/`validate_instrinfo.py` 陈旧清理 → 另立。

## 完成区

**测试结果**：全部通过（真实命令 + 退出码，日志见 `.work/log/llvm/LLVM-029t-*.log`）。
- `make prepare` EXIT=0（幂等跳过）；`make build-mc` EXIT=0（首次增量 **17s**，JOBS=8；`make prepare && make build-mc` 复跑 EXIT=0）
- 60 行全部汇编 EXIT=0；`llvm-objdump -d` round-trip 与 `; ASM:` 逐条一致（含块形式）→ `chk_asm60`：`insns=60 objcheck=0 asmcheck=0`
- 独立 oracle：`test_encoding_oracle.py` → `Results: 121 passed, 0 failed out of 121 tests`；交叉校验 `Cross-check OK: oracle tests (121) >= lit OBJ lines (113)`
- `check_lit_bytes.py` → `check_lit_bytes: 113 patterns OK`（N==独立计数）
- `make check-lit` → `Total Discovered Tests: 28`，`Passed: 28 (100.00%)`（新增 `fp-encoding.s`）
- `make check` EXIT=0，`repository checks: PASS`：`check-patch-tree: 2 component(s), 68 patches OK`、`check-interface 总计: 80 项 | PASS: 80 | FAIL: 0`、`validate_encoding: 227 条记录 OK`、`check-scope: PASS`（`m1 152 / fp 60 / excluded 15 / total 227`）
- 一键证据脚本 `.work/evidence/LLVM-029t/run.sh` 默认模式 **9/9 PASS，EXIT=0**
- `run.sh --inject` **4/4 反例** 均「注入→目标检查 FAIL→还原并重建→回绿」，**EXIT=0**

**修改文件**（净增行以**源文件增量**计；组件文件相对上游 base 均为新增，见「新发现 2」）：
- **新建** `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfoFP.td.patch`（源 `.td` **498 行**，`new file mode`，含有效 hunk `@@ -0,0 +1,498 @@`、非空 blob）
- 改 `.../DADAOInstrInfo.td.patch`（源 **+1** 行：末尾 `include "DADAOInstrInfoFP.td"`）
- 改 `.../AsmParser/DADAOAsmParser.cpp.patch`（源 **净 +30**：`isFPBlockMnemonic` 22 条 helper +15、块 count 相等加固 +14、追加白名单 +1（去 1 行））
- 改 `.../MCTargetDesc/DADAOMCInstPrinter.cpp.patch`（源 **净 +11**）
- **新建** `tests/lit/MC/Dadao/fp-encoding.s`（375 行，60 条 `; OBJ:` + 60 条 `; ASM:`）
- 改 `tools/llvm/test_encoding_oracle.py`（`REG` 补 rf；`TESTS` 61→**121** unique）
- 改 `components/llvm-project/changelog.md`（+1 行）、`components/llvm-project/series`（+1 行）
- 证据/日志（非 git）：`.work/evidence/LLVM-029t/{run.sh,gen_lit.py}`、`.work/log/llvm/LLVM-029t-*.log`
- 组件源树提交：`.work/source/llvm-project` HEAD = base + **1** commit（`406e4fa32`，clean）；补丁集 **67→68**（3 改 + 1 新建）

**验收结果**（真实输出节选）：
```
check-patch-tree: 2 component(s), 68 patches OK
4.Opcodes    LLVM lit ↔ opcodes.yaml    PASS   check_lit_bytes: 113 patterns OK
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
validate_encoding: 227 条记录 OK
[PASS] m1 计数: 期望=152 实际=152 / [PASS] fp 计数: 期望=60 实际=60
[PASS] excluded 计数: 期望=15 实际=15 / [PASS] total 计数: 期望=227 实际=227
check-scope: PASS
repository checks: PASS
Total Discovered Tests: 28   Passed: 28 (100.00%)
```
注入自检（`run.sh --inject`，各轮重建后复验）：
```
--- injection A-td-op-ha ---   injected files: .../DADAOInstrInfoFP.td
  [PASS] inject-A-td-op-ha: targeted check FAILED as expected (rc=1)
  [PASS] inject-A-td-op-ha: restored -> check PASS (rc=0)
--- injection B-asm-whitelist ---  [PASS] FAILED(rc=1) / restored PASS(rc=0)
--- injection C-printer-whitelist --- [PASS] FAILED(rc=1) / restored PASS(rc=0)
--- injection D-count-hardening ---  [PASS] FAILED(rc=1) / restored PASS(rc=0)
=== injection self-check done: FAILED=0 ===
```
还原证据：注入前 `git -C .work/source/llvm-project status --porcelain` 空；每轮注入后 `git diff --name-only` **非空**；还原后 `git status --porcelain` 空、`git diff` 空（byte 级复原）。还原后源文件 sha256：
```
b513caaaf...  DADAOInstrInfoFP.td
6ec708f4f...  DADAOInstrInfo.td
b7d65ffac...  AsmParser/DADAOAsmParser.cpp
c3627ce23...  MCTargetDesc/DADAOMCInstPrinter.cpp
cef80ea64...  .work/build/llvm/bin/llvm-mc
```
残留：`git status --untracked-files=all` 仅为本任务交付物 + 任务书；`make check-no-residue: PASS`。不变量：`contracts/`、`spec/**`、`tests/vectors/**`、`components/qemu/patches/**` **零改动**。

**新发现/坑**：
1. **任务书 §6.8 反例 A 的示例不可直接使用**：`ftadd` ha `0x10→0x11` 会与 `ftsub`（ha=0x11）冲突，`llvm-tblgen -gen-disassembler` 直接报 `error: Decoding conflict encountered`，**构建先失败**，oracle 无从判定（不满足「重建后 oracle/lit FAIL」）。本任务改用**未占用**的 `ha=0x0F`（op=0x44）作注入：构建成功、oracle 对应用例 FAIL、还原回绿。**建议**后续任务书给注入示例时选用未占用 opx。
2. **组件内 DADAO 文件相对上游 base 均为新增**，故 `DADAOInstrInfo.td.patch` 是整文件 `new file mode` 补丁（1305 行）；「仅 +1 行」指相对**上一版源文件**的增量。
3. **寄存器注释标签与枚举实际顺序不符**（`MCCodeEmitter.cpp`/`DADAODisassembler.cpp`）：实际枚举为 `ra0=3, rb0=67, rd0=131, rf0=195`（RD/RB/RA/RF 注释标签整体错位），但减法基数与 `DecodeGPRF/RF` 加法基数均正确，功能无误；本任务未改，供后续清理参考。
4. `DecodeGPRFRegisterClass` 此前因 FP 未引入而 `-Wunused-function`（`deferred.md`）；FP 引入后该警告自然消解。

**遗留问题**：
- 本任务范围内：**无**未完成项。
- 范围外（仅登记，不作本任务遗留）：`generate_instrinfo.py`/`validate_instrinfo.py` 陈旧 → 另立清理任务；M1 `rd2rd`/`rb2rb` 不等 count 静默取末组（pre-existing，本任务未改，实测 rc0）；FP 汇编期静态合法性 → `LLVM-030t`；FP 值 oracle → `GOLDEN-*`；QEMU FP → `QEMU-034t`。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：新建 `.td`（60 def 逐条核对 `op`/`ha`/operand class 对 `contracts/opcodes.yaml`）、`DADAOInstrInfo.td` include、AsmParser 两处改动、printer 白名单、lit（60 行）、oracle（+60 用例）、run.sh。

**逐条核对**：60 条 def 的 `op`（+`orrr/orri` 的 `ha`）、dst/src 银行与 `fields` role 一致；`orri` 块（24 条）vs 标量（`ftroot`/`foroot`）区分正确；`cs.eq/ne`（dst=`rc`）vs `cs.n/z/p`（dst=`rb`）一致；`ftqcmp/ftscmp/foqcmp/foscmp` 目的为 GPRD、`ftcls/focls/ft2it..` 同。lit 60 行字节由 `opcodes.yaml` 字段布局独立算出（**未**从 llvm-mc 回填，脚本留存 `.work/evidence/LLVM-029t/gen_lit.py`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书反例 A（ha 0x10→0x11）触发 `Decoding conflict`，构建失败而非 oracle FAIL | ✅已修 | run.sh 注入 A 改用未占用 `ha=0x0F`，并在脚本内注释披露 | `run.sh --inject` A：注入 FAIL(rc=1)→还原 PASS(rc=0) |
| F2 `DADAOInstrInfo.td` 首版 include 前多一空行（+2） | ✅已修 | 去空行，改 `}\ninclude ...` | source `git diff --stat` = `+1` |
| F3 run.sh 注入构建失败时未复验还原 | ✅已修 | 重构 `inject_round`：始终 restore+rebuild+复验 | `--inject` 4/4 均有 "restored -> check PASS" |
| F4 oracle `REG` 无 rf 项 | ✅已修 | 补 `rf0..rf20/rf63` | oracle 121/121 |
| F5 count 加固是否应含 `rd2rf`/`rf2rd` | ❌不修（判为正确） | 二者同属 FP 块，纳入相等检查；M1 `rd2rd`/`rb2rb` 明确排除 | 实测：`ft2fo`/`rd2rf` 不等 count rc=1；`rd2rd`/`rb2rb` 不等 count rc=0 |
| F6 双组检查之外的畸形形态（`{a,b}`/单组） | ❌不修 | 由 AsmMatcher 操作数数量不匹配报错兜底 | `chk_block_asm`/lit 覆盖正常形态，畸形形态失败 |

**判决**：全部 finding 已处置（4 修 + 2 保留且有据）；改动可交付，状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查范围**：按任务书 §6 验收标准逐条独立重跑；审核 engineer 证据脚本 `.work/evidence/LLVM-029t/run.sh`（+`gen_lit.py`）；独立注入反例。

---

**1. 汇编（60 行全部 EXIT=0）**
```
$ bash .work/evidence/LLVM-029t/run.sh 2>&1 | grep "fp-60-assemble"
  [PASS] fp-60-assemble-roundtrip (rc=0)
     expected=insns=60 objcheck=0 asmcheck=0 actual=insns=60 objcheck=0 asmcheck=0
```
独立验证：`make check-lit` 28/28 全 PASS，`fp-encoding.s` 60 条 `; OBJ:` + 60 条 `; ASM:` 行。

**2. 反汇编 round-trip**
```
$ echo "ftadd rf4, rf6, rf8" | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/fp.o -
$ llvm-objdump -d --triple=dadao-unknown-elf /tmp/fp.o
       0: 44 40 41 88  ftadd rf4, rf6, rf8
$ echo "ft2fo {rf4:rf6}, {rf8:rf10}" | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/fp2.o -
$ llvm-objdump -d --triple=dadao-unknown-elf /tmp/fp2.o
       0: 44 04 42 03  ft2fo {rf4:rf6}, {rf8:rf10}
```
块形式 `{rf4:rf6}, {rf8:rf10}` 渲染正确。脚本 `chk_asm60` 验证 insns=60、objcheck=0、asmcheck=0。

**3. 独立编码 oracle**
```
$ python3 tools/llvm/test_encoding_oracle.py
Results: 121 passed, 0 failed out of 121 tests
Cross-check OK: oracle tests (121) >= lit OBJ lines (113)
RC=0
```
- oracle 期望值来源审核：`encode_orrr(0x44, 0x10, 4, 6, 8)` 等硬编码常量直接取自 `contracts/opcodes.yaml` 的 op/ha 字段，**不从 llvm-mc 回填**。`gen_lit.py` 读 opcodes.yaml 计算 word，与 oracle 一致。无自证循环。
- `check_lit_bytes.py`：`check_lit_bytes: 113 patterns OK`，RC=0。

**4. lit/门控**
```
$ make check-lit 2>&1 | tail -3
Total Discovered Tests: 28
  Passed: 28 (100.00%)

$ make check 2>&1 | grep -E "check-patch-tree|check-interface|check-scope|validate_encoding|repository checks"
check-patch-tree: 2 component(s), 68 patches OK
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
validate_encoding: 227 条记录 OK
check-scope: PASS
repository checks: PASS
```
`check-scope` 计数：m1=152, fp=60, excluded=15, total=227 ✓

**5. 不变量**
```
$ git diff --name-only -- contracts/ spec/ tests/vectors/ components/qemu/
（空，零改动）
```

**6. 补丁与 E1–E8**
- `DADAOInstrInfoFP.td.patch`：`new file mode`、`@@ -0,0 +1,498 @@`、非空 blob ✓
- `DADAOInstrInfo.td.patch`：`git diff --stat` = `3 insertions(+), 2 deletions(-)` → 净 +1 行 ✓
- `AsmParser.cpp.patch`：`git diff --stat` = `33 insertions(+), 3 deletions(-)` → 净 +30 行 ✓
- `MCInstPrinter.cpp.patch`：`git diff --stat` = `14 insertions(+), 3 deletions(-)` → 净 +11 行 ✓
- `series`：`git diff` 显示 +1 行 `DADAOInstrInfoFP.td.patch` ✓
- 补丁总数：qemu 31 + llvm-project 37 = 68 ✓
- `.work/source/llvm-project`：`git status --porcelain` 空、HEAD=base+1 ✓

**7. count 不等加固**
```
# FP block unequal counts (3 vs 2) → hard error
$ echo "ft2fo {rf4:rf6}, {rf8:rf9}" | llvm-mc ... -filetype=obj -o /dev/null -
error: invalid 'ft2fo': source and destination register group counts differ
RC=1

# FP block equal counts (2 vs 2) → ok
$ echo "ft2fo {rf4:rf5}, {rf8:rf9}" | llvm-mc ... -filetype=obj -o /dev/null -
RC=0

# FP block equal counts (3 vs 3) → ok
$ echo "ft2fo {rf4:rf6}, {rf8:rf10}" | llvm-mc ... -filetype=obj -o /dev/null -
RC=0

# M1 rd2rd unequal counts → pre-existing, still passes
$ echo "rd2rd {rd4:rd6}, {rd8:rd12}" | llvm-mc ... -filetype=obj -o /dev/null -
RC=0
```
M1 `rd2rd` 行为未被改动（静默取末组，pre-existing）✓

**8. 脚本审计**

审核 `.work/evidence/LLVM-029t/run.sh`：
- **注入 A（op/ha）**：改 `ftadd` 的 `ha=0x10→0x0F`（未占用），锚点精确（`assert s.count(old) == 1`），非空、可还原 ✓
- **注入 B（AsmParser 白名单）**：`isFPBlockMnemonic(Mnemonic)` → `false`，精确替换，非空 ✓
- **注入 C（printer 白名单）**：逐条替换22个 FP mnemonic 为 `zzz_` 前缀，`assert n == 22`，非空 ✓
- **注入 D（count 加固）**：`if ((isFPBlockMnemonic(...)) &&` → `if (false &&`，禁用检查，非空 ✓
- 所有注入含 `restore_src` + `rebuild`；`inject_round` 结构：inject→check FAIL→restore→rebuild→check PASS ✓
- 脚本反例门控：`inject_round` 检查 `git diff --name-only` 非空（防空注入），exit code 捕获正确（`rc=$?`，非管道吞码）✓

重跑脚本：
```
$ bash .work/evidence/LLVM-029t/run.sh 2>&1
=== LLVM-029t evidence: default acceptance ===
  [PASS] source-clean-E1 (rc=0)
  [PASS] build-tools (rc=0)
  [PASS] fp-60-assemble-roundtrip (rc=0)
  [PASS] independent-oracle (rc=0)
  [PASS] lit-bytes-vs-opcodes (rc=0)
  [PASS] group-count-hardening (rc=0)
  [PASS] check-lit-28 (rc=0)
  [PASS] make-check (rc=0)
  [PASS] invariants-unchanged (rc=0)
=== done: FAILED=0 ===

$ bash .work/evidence/LLVM-029t/run.sh --inject 2>&1
--- injection A-td-op-ha ---
  [PASS] inject-A-td-op-ha: targeted check FAILED as expected (rc=1)
  [PASS] inject-A-td-op-ha: restored -> check PASS (rc=0)
--- injection B-asm-whitelist ---
  [PASS] inject-B-asm-whitelist: targeted check FAILED as expected (rc=1)
  [PASS] inject-B-asm-whitelist: restored -> check PASS (rc=0)
--- injection C-printer-whitelist ---
  [PASS] inject-C-printer-whitelist: targeted check FAILED as expected (rc=1)
  [PASS] inject-C-printer-whitelist: restored -> check PASS (rc=0)
--- injection D-count-hardening ---
  [PASS] inject-D-count-hardening: targeted check FAILED as expected (rc=1)
  [PASS] inject-D-count-hardening: restored -> check PASS (rc=0)
=== injection self-check done: FAILED=0 ===
```

**9. 独立注入（reviewer 自选，不用脚本自带注入）**

选择：改 `ftsub` 的 `ha` 从 `0x11` 到 `0x03`（op=0x44 的未占用 ha）。
```
$ sed -i 's/^  let ha = 0x11;$/  let ha = 0x03;/' .work/source/llvm-project/.../DADAOInstrInfoFP.td
$ git -C .work/source/llvm-project diff --name-only
llvm/lib/Target/DADAO/DADAOInstrInfoFP.td   ← 非空，注入有效

$ make build-mc  → EXIT=0（构建成功）

$ python3 tools/llvm/test_encoding_oracle.py
FAIL: ftsub rf4, rf6, rf8
  Expected: 44444188
  Encoding mismatch: expected 44444188, got 440c4188
Results: 121 passed, 1 failed out of 121 tests
RC=1

# 还原
$ git -C .work/source/llvm-project checkout -- llvm/lib/Target/DADAO/DADAOInstrInfoFP.td
$ git -C .work/source/llvm-project status --porcelain  → （空）
$ make build-mc  → EXIT=0
$ python3 tools/llvm/test_encoding_oracle.py  → 121 passed, 0 failed, RC=0
$ sha256sum .work/source/llvm-project/.../DADAOInstrInfoFP.td
b513caaafa2ebd2a33920d05c154048d4c4de2077f94f65e2806264aec9cdfac  ← 与注入前一致
```
注入有效（oracle 抓到 1 failed）、还原含重建、sha256 复原、`git status` 干净 ✓

**10. §6.8 披露判定**

独立实测：将 `ftadd` 的 `ha` 从 `0x10` 改为 `0x11`（与 `ftsub` 相同）：
```
$ make build-mc 2>&1 | tail -3
    01000100010001__________________  ftsub_orrr_rf
error: Decoding conflict encountered
ninja: build stopped: subcommand failed.
make: *** [Makefile:127: build-mc] Error 1
```
**确认**：`ftadd` ha `0x10→0x11` 确实与 `ftsub`（ha=0x11）冲突，TableGen 解码器报 `Decoding conflict`，构建直接失败，oracle 无法运行。engineer 改用未占用 `ha=0x0F` 的处理**合理**，脚本内有注释披露，**不需返工**。

**11. 残留与越界**
```
$ git status --untracked-files=all
  未跟踪文件：任务书（LLVM-029t/LLVM-030t）、新补丁、新 lit 文件 — 均为本任务交付物
$ make check-no-residue → PASS
```
无未披露越界。`git diff --name-only` 与 §3 交付物清单对齐。

**12. 完成区一致性**

| 完成区声明 | reviewer 核实 | 一致 |
|---|---|---|
| FP.td 498 行 | `wc -l` = 498 | ✓ |
| DADAOInstrInfo.td +1 行 | `git diff --stat` = +3/-2 → 净 +1 | ✓ |
| AsmParser 净 +30 | `git diff --stat` = +33/-3 → 净 +30 | ✓ |
| Printer 净 +11 | `git diff --stat` = +14/-3 → 净 +11 | ✓ |
| 补丁数 68 | qemu 31 + llvm 37 = 68 | ✓ |
| check-scope 152/60/15/227 | 实测一致 | ✓ |
| oracle 121/121 | 实测一致 | ✓ |
| check_lit_bytes 113 patterns OK | 实测一致 | ✓ |
| check-lit 28/28 | 实测一致 | ✓ |
| sha256 复原 | 4 个源文件 sha256 均与完成区一致 | ✓ |

---

**脚本审计结论**：`run.sh` 合格——4 个注入均非空、可还原、含重建；FAIL 路径可达；exit code 捕获正确（非管道吞码）；`inject_round` 含 `git diff --name-only` 非空校验（防空注入）。`gen_lit.py` 从 `contracts/opcodes.yaml` 独立计算期望字节，无自证循环。

**判决**：**Accepted** —— 全部12项验收标准在 reviewer 独立重跑下通过；脚本审计合格；独立注入 ftsub ha 0x11→0x03 确认 oracle 可失败且还原含重建后回绿；§6.8 披露合理（实测 ha 冲突确致构建失败）；无越界、无残留。
