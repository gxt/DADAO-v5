# LLVM-095t: `R_DADAO_REL32` 端到端 + PLT 内联（GOT 3 条形态 / 布局义务取消）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`ADR-0028`（GOT/PLT 远距离取址；**`Accepted`**，2026-10-16 用户逐条确认 ⇒ **设计定案**）、`ADR-0019 D11`（就地追加：新类型 / 编号 / 公式 / 落点 / 负值同改 / 越界）、`ADR-0026 D5`·`D7`（就地修订：PLT 内联去槽 / GOT 3 条/次 / 取消 `.got` 贴 ±2 KiB 布局义务）、`ADR-0021 D1`（「汇编器按寄存器自动选类型」先例）；契约真源 = `.tao/contracts/contract-elf.md §2.2`（编号表：`14 = R_DADAO_REL32` / `15 = R_DADAO_NUM`）、`§3.1`（公式 + 记录形态 (甲) + 缺省非负与负值同改）、`§3.2`（越界 / 落点不符 ⇒ link-time error）、`§4`（固定 2 片、禁 relaxation）、`.tao/contracts/contract-dynlink.md §3`（GOT/PLT 形态、布局义务取消）；现场来源 = `LLVM-094t`（阶段 A/B/C，`待验收`）与 `ISS-230`；纪律 = `ISS-229`（L2/L3 串行）、`ISS-210`（改 MC 必 `install-host`）、`docs/Process-01`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 路线位置

- **路线 = `ADR-0025 D6` 的 `P2` 段的前置（生产者侧）**；本册 = `ADR-0028`（`Accepted`）的**实现落点**，**替代** `ADR-0026 D5` 原文的「超 ±2 KiB ⇒ `ABS48` 序列 + `ldm.o_rrri_rb` 两段式」（该路径在现有 ABI 下**不可实现**：链接器无可用 `rd`、ISA 无宽 PC 相对重定位类型；`ISS-230`，阶段 C 现场证据）。
- **依赖单向 `llvm → infra`**：本册产出被 `INFRA-085t`（`P2` 消费侧 + 构建）**消费**；本册落地后 `INFRA-085t` 文首「⛔ 阻塞」指针中**与 `.got` 可及性（GOT 取址）相关的部分解除**。
- **判据边界 = 能编 + 静态可核**（`readelf` / `llvm-readobj` + **独立解析**）：**不跑**（运行验证 = `P3`）。本册**不可**有任何「运行通过 / E2E 通过」叙述。

## 目标（交付物）

1. **新类型 `R_DADAO_REL32`（编号 `14`）/ `R_DADAO_NUM`（编号 `15`）端到端可用**：MC 侧发射（**一指令一条记录**、两条各带**补偿 addend**）→ lld 侧消费（**两条 wyde 落点**、`disp < 0` **两条同改**〔含 `~lo16`〕、落点不符 / 越界 ⇒ **link-time error**）。
2. **PLT 内联去槽**：条目由 24 B → **16 B**（配对序列 + `ldm.o` + `jump`；**无 8 字节数据槽、无 padding**）。
3. **GOT 取址改 3 条形态**：CodeGen **两处**（GOT 槽 / 跳转表基址）改为「配对序列 + `ldm.o`」。
4. **布局义务取消的正面证据**：lld **默认布局**下 `-shared` **链接成功**（旧行为 = `R_DADAO_REL12 out of range` rc=1）；**静态路径逐字节不回归**。

## 必须自包含的事实（现场已核；供执行，**勿重复查证**）

### 1 口径（逐条来自契约 / ADR 正文；执行时**照此**、不自拟）

1. **类型与编号**：新增 `R_DADAO_REL32` = **`14`**、`R_DADAO_NUM` = **`15`**（类型计数，由 `14` 顺延）；编号在 `e_flags[7:0] = 1` namespace 内、**全密无空档**。〔`ADR-0019 D11`；`contract-elf.md §2.2`〕
2. **值类**：**偏移类**（**有符号 / 补码、32 位、单位字节**）；**不适用**「有效位宽 = 立即数位宽 + 2」的字偏移换算 —— 与 `REL12` **同款例外**（名中数字 = **有效位宽**）；可达 **±2 GiB**。
3. **公式**：`disp = S + A − P`；**`P` 的基准 = 配对中「执行取数的那条 `ldm.o`」的地址**（`rb0` 读出**当前指令**地址、**无 `-4`**；`ADR-0019 D3`）。
4. **记录形态 (甲)**：**一个类型 + 两条记录**、**一指令一条记录**，两条各带**补偿 addend** —— **hi 记录**（落点 = 配对**首条**）取 **`A − 8`**；**lo 记录**（落点 = **次条**）取 **`A − 4`**。核算：`hi: S + (A−8) − P_hi = S + A − (P_hi+8)`；`lo: S + (A−4) − P_lo = S + A − (P_lo+4)`；由 `P_ldm.o = P_hi + 8 = P_lo + 4`（相邻两指令相差 **4 B**）⇒ 两条**各自独立**算得同一 `disp` ✓。**不引入配对机制**（无 hi/lo 两个类型、无回查配对）。
5. **落点**：**两条指令各一个 16 位 wyde** —— **hi16 → `wp1`**（首条）、**lo16 → `wp0`**（次条）；`wp` 编码于 `hb[5:4]`（`bits[17:16]`），与 `ABS48` 的指令形式**同形**。**执行顺序 = 地址顺序**：首条（`wp1`）在低地址、次条（`wp0`）紧随（`+4`）、`ldm.o` 再 `+4`。
6. **缺省非负**：发射侧（编译器 / 汇编器）**一律**发射**非负形** = `set.zw rdX, wp1, hi16` + `or.w rdX, wp0, lo16`。
7. **链接期 `disp < 0` ⇒ 两条同改**：① 首条 opcode `set.zw`-rd（`0x4C`）→ `set.ow`-rd（`0x4D`），立即数仍取 `disp[31:16]`；② 次条 opcode `or.w`-rd（`0x48`）→ `andn.w`-rd（`0x49`），**立即数取 `~disp[15:0]`**。寄存器 / `wp` 域**不变**。
8. **为何负值必须同改两条（必须理解，不是可选）**：`set.ow` 把**其余 48 位全置 1（含 `wp0`）**，而 `or.w` = `rd[wp] | imm` **只能置位、不能清零** ⇒ 次条若仍留 `or.w`，`wp0` 恒为 `0xFFFF`（**静默错值、不可归因**）；`andn.w` = `rd[wp] & ~imm`，取 `imm = ~lo16` ⇒ `0xFFFF & lo16 = lo16` ✓（`wp3`/`wp2` = 1 = 符号扩展 ✓）。非负形不受影响（`set.zw` 清 0 ⇒ `wp0` 初值 `0x0000` ⇒ `or.w` 得 `lo16` ✓）。四个 opcode 同在 `SimRISC-00` 的 `0100-1xxx` 行 ⇒ 各只动 8 位 opcode；**先例** = `R_DADAO_REL26` 把 `call-iiii`（`0x74`）改写为 `jump-iiii`（`0x70`）。
9. **越界 / 落点不符 ⇒ link-time error**：`disp` 超出 `−2³¹..2³¹−1` ⇒ **报错**（不截断、不 wrap）；落点**不是合法配对序列的成员** ⇒ **报错**（禁静默放行 —— 负值若按非负形静默处理会静默偏 **`+2³²`**）。
10. **固定 2 片**（32 位有符号），**不**按值变长、不缩短 / 加长；**不解禁 relaxation**。〔`ADR-0019 D7` / `D11`；`contract-elf.md §4`〕
11. **PLT 例外**：PLT 由**链接器合成**（`writePlt` 自产编码）⇒ **链接器自选配对、无 opcode 改写环节**（链接期已知符号）。`D2` 的改写机制**只服务**「编译器发射、链接期才知符号」的 GOT 路径。
12. **寄存器**：临时寄存器取**调用者保存**族（`rd4–rd7` / `rd16–rd31`；PLT 沿用 `rd5`）；**不使用** `rd0`（零）/ `rd1`（`rderrno`）/ `rd2`–`rd3`（调试 / 测试保留）⇒ **`spec/` 零改动**。
13. **PLT 形态**：条目 = 配对序列（`disp ≥ 0` ⇒ `set.zw`+`or.w`；`disp < 0` ⇒ `set.ow`+`andn.w`）+ `ldm.o {rb4}, [rb0, rdX]` + `jump [rb4, rd0, 0]`（**4 条指令 = 16 B**、**无数据槽、无 padding**）；`pltEntrySize` **24 → 16**、`pltDataOffset` **取消**；`pltHeaderSize` 保持 **0**（eager）、`gotPltHeaderEntriesNum` 保持 **2**、`DT_PLTGOT` 不变；`.got.plt` 槽仍由 `JUMP_SLOT`(7) 在装载期填充；`writeGotPlt` 仍写 0（eager，无 resolver 回指针）。
14. **GOT 访问形态（3 条/次）**：`set.zw`/`or.w rdX, disp`（2 条）+ `ldm.o {rbT}, [rb0, rdX]`（1 条）；`disp = S_slot − (ldm.o 地址)`；`S_slot` = 该符号的 **GOT 槽标签**（现状编译器自出的 `.Lgot.<n>` / 跳表槽）；`.got` 槽**内容**不变（8 字节 `R_DADAO_ABS48` **数据**字段 = 符号地址）；运行期取到的地址 = `rb0`（= `ldm.o` 自身地址）+ `rdX` = 槽地址 ✓。**取消**「`.got` 必须贴访问点 ±2 KiB」的**布局义务**（可达 ±2 GiB）。

### 2 源码锚点（现场行号；源码树 `.work/source/llvm-project`，**只读**）

1. `llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def`：现终到 `ELF_RELOC(R_DADAO_TLSDESC, 13)` + `ELF_RELOC(R_DADAO_NUM, 14)`（头注释编号表同述 `14 = type count`）⇒ **本册改这两处 + 注释**。
2. `lld/ELF/Arch/DADAO.cpp`：`pltEntrySize = 24`（L114）、`pltHeaderSize = 0`、`gotPltHeaderEntriesNum = 2`；`static constexpr unsigned pltDataOffset = 16`（L139）；`getRelExpr`（L158 起）；`writePlt`（L245–291）；`relocateInSection`（L294 起）；`relocate` / `relocateAlloc`（L468 起）。**另**：`iRelSymbolicRel = R_DADAO_NUM`（哨兵**随枚举自动跟随** 15，但**注释里写死 `NUM = 14`，须同步**）。
3. `relocateInSection` 的 `ABS48` **指令**路径已成先例：`uint32_t insn = read32be(loc); unsigned wp = (insn >> 16) & 0x3; insn = (insn & 0xFFFF0000u) | slice; write32be(loc, insn);`（保留 opcode / 寄存器 / `wp` 域）⇒ REL32 的**写回**同构。
4. `llvm/lib/Target/DADAO/DADAOISelDAGToDAG.cpp`：**PIC GOT 槽**分支 = L270–279（`getTargetGlobalAddress(..., DADAO::MO_GOT_ADDR)` + `getMachineNode(DADAO::ld_o_rb, ..., rb0, Sym)`）；**PIC 跳表基址**分支 = L351–357（`getTargetJumpTable(..., MO_GOT_ADDR)` + `ld_o_rb rb0, JTSlot`）。
5. `llvm/lib/Target/DADAO/DADAO.h`：`MO_GOT_ADDR = 1`（MachineOperand 目标标志）；`DADAOMCInstLower.cpp` L92/L104 把 `MO_GOT_ADDR` 映射到**槽标签**（`Printer.getGOTSlotSymbol(...)` / `getGOTSlotSymbolForJumpTable(...)`）；L46 注释说明「槽的数据字段已带 `sym + offset` ⇒ 指令操作数 = 裸槽标签」（⇒ `A_expr = 0`）。
6. `llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCCodeEmitter.cpp`：`isAddressConstructionInstr`（rwii `set.zw`/`or.w`/`andn.w` 的 **rd 与 rb 两个银行**）⇒ 现**一律**发 `DADAO_FK_ABS48`（L187–191）；`isLoadStoreInstr` ⇒ `FK_REL12`（base `rb0`）/ `FK_ABS12`（L205–210）。**注意**：`MCOperand` 里只有**表达式**（目标标志在 MC 层不可见）⇒ **类型判别只能靠指令 opcode / 操作数形态**。
7. `MCTargetDesc/DADAOFixupKinds.h`：`DADAO_FK_PCRel_12 = FirstTargetFixupKind` … `DADAO_FK_REL12` / `DADAO_FK_ABS12` / **`LastTargetFixupKind = DADAO_FK_ABS12`**。
8. `MCTargetDesc/DADAOAsmBackend.cpp`：`getFixupKindInfo` 的 `Infos[]` **按 `Kind − DADAO_FK_PCRel_12` 索引**（L49–81，`DADAO_FK_ABS48 = {…, 0, 16, 0}`）；`evaluateFixup` 的就地解析白名单 = `IsPCBranch`（`PCRel_12..PCRel_24`）与 `IsLdstPCRel`（**含 `DADAO_FK_REL12`**；同 section 标签会被**就地折叠**）（L88–130）；`applyFixup` 的 **早退边界 `Kind < PCRel_12 || Kind > DADAO_FK_ABS12 ⇒ return`**（L185 附近）与 `DADAO_FK_ABS48 ⇒ return`（不就地解析）（L196–200）。
9. `MCTargetDesc/DADAOELFObjectWriter.cpp::getRelocType`（L30–85）：fixup kind → `R_DADAO_*` 映射表；`needsRelocateWithSymbol` **仅 `ABS48` 返 true**。
10. `.td`（**指令已齐、无须新增 ISA 指令**）：`or_w_rd` op `0x48` / `andn_w_rd` op `0x49` / `set_zw_rd` op `0x4C` / `set_ow_rd` op `0x4D`（`DADAOInstrInfo.td` L727–768，`DADAORwii`，操作数 `wydepos:$wp, immu16:$imm16`）；`ldm_o_rb` op `0x3A`（`DADAORrri`：`outs GPRB:$ra`, `ins GPRB:$rb, GPRD:$rc, immu6:$imm6`，L483）；伪指令先例 `GLOBAL_ADDR`（`DADAOCodeGen.td` L309）在 `DADAOInstrInfo.cpp::expandPostRAPseudo`（L322 起）展开为 `set_zw_rb` + `or_w_rb` ×2（**同一符号逐指令**）。

### 3 编码常量（逐条现场核对；`op<<24 | rd<<18 | wp<<16 | immu16`）

| 指令 | 编码式 | 现场依据 |
|---|---|---|
| `set.zw rd8, wp0, 0x0` | `0x4C200000` | `tests/llvm/lit/MC/DADAO/m4-pseudo-set.s` |
| `or.w rd8, wp1, <sym>` | `0x48210000` | `tests/llvm/lit/MC/DADAO/m6-callconv.s` |
| `set.zw`-rd / `set.ow`-rd / `or.w`-rd / `andn.w`-rd | `0x4C` / `0x4D` / `0x48` / `0x49`（op 字节） | `DADAOInstrInfo.td` L727–768 |
| `ldm.o {rb4}, [rb0, rd5]`（`immu6 = 1`） | `0x3A000000 \| 4<<18 \| 5<<6 \| 1` | `lld/ELF/Arch/DADAO.cpp::writePlt` 现产 |
| `jump [rb4, rd0, 0]` | `0x71000000 \| 4<<18` | 同上 |
| `ld.o rd5, [rb0, 16]`（**将被移除**） | `0x20000000 \| 5<<18 \| 16` | 同上 |

### 4 现状字节形态（实测，供「改前 / 改后」对账）

- **PLT**（`.work/source/llvm-project/lld/ELF/Arch/DADAO.cpp::writePlt` + 094t 实测 `libtest.so`）：条目 **24 B** = `ld.o rd5,[rb0,16]` + `ldm.o {rb4},[rb0,rd5]` + `jump [rb4,rd0,0]` + **4 B padding** + **8 B 内嵌常量**（= `槽地址 − (条目+4)`）；`pltHeaderSize = 0`（eager）。现 `assert((pltEntryAddr % 8) == 0)`（新条目 16 B ⇒ 8 对齐仍成立 ⇒ 断言可保留）。
- **PIC GOT 取址**（现）：`ld.o rb, [rb0, <槽>]` = **1 条**（`R_DADAO_REL12`，`imms12` ±2 KiB）；`.got` 槽由 `DADAOAsmPrinter` 自出（每引用符号 / 跳表一 8 字节 `R_DADAO_ABS48` 数据槽）。
- **默认布局下的旧报错**（必须消失）：`ld.lld -shared` ⇒ `R_DADAO_REL12 out of range: 65596 is not in [-2048, 2047]; references section '.got'`（rc=1；实测 65552 / 65588 / 65596 B，`-z max-page-size=0x1000` ⇒ 4112 B 仍越界）。
- **`tests/scripts/dadao-dyn.lds`**（阶段 B 产物）：单段 RWX + `.got` **紧跟 `.text`**（文件头明写「为 ±2 KiB 可及性」）⇒ **该理由本册后不成立**，须同步。

### 5 构建 / 门控事实

- 构建：`make build-mc`（≈5 min）/ `make build-lld`（≈40 s）/ **`make install-host`（≈6 min）**；**改 MC / `.td` 后必须 `make install-host`**，否则门控 / lit 走**旧安装根**与旧生成物**自洽而假绿**（`ISS-210`）。
- **`install-host` / `build-*` / L2 / L3 与本任务之外的重建须串行**（`ISS-229`：共享安装根 / 构建树竞争 ⇒ 假 FAIL）；`JOBS=8`、**禁全核** `-j$(nproc)`。
- `tools/llvm/llvm-isa-backend-matrix.{md,tsv}` 是**派生投影**（生成器 `tools/llvm/gen_isa_coverage.py`）；改后端源码（行号 / 证据计数）会 **drift** ⇒ 须重生成，否则 L1 `check-isa-coverage` 报红（094t 先例）。
- 端序 = **大端**（`ELFDATA2MSB`）；`.work/**` 被 `.gitignore`（证据不入 git，留工作区）。

## 接口规范

- **输入**：`ADR-0028`（`Accepted`）/ `ADR-0019 D11` / `ADR-0026 D5`·`D7` / `ADR-0021`；`.tao/contracts/contract-elf.md`（`§2.2`/`§3.1`/`§3.2`/`§4`）、`.tao/contracts/contract-dynlink.md`（`§3`）（**均只读**）；`components/llvm-project/patches/**`（现状，只读）；`.work/source/llvm-project/**`（**只读**源码检出，现状取证）；`.dadao/cross-toolchain/**`（工具链 + sysroot，只读）。
- **输出**：
  1. **组件补丁**（树形 + 一文件一补丁，`docs/Process-01`；`check-patch-tree` 机械校验）：`components/llvm-project/patches/llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def.patch`、`.../lld/ELF/Arch/DADAO.cpp.patch`、`.../llvm/lib/Target/DADAO/**`（ISel / InstrInfo / MCInstLower / `.td` / `MCTargetDesc/DADAO{FixupKinds.h,AsmBackend.cpp,ELFObjectWriter.cpp,MCCodeEmitter.cpp}`、`DADAO.h`）——**只改必须改的**。
  2. **测试 / 脚本**：`tests/llvm/lit/MC/DADAO/**`（新类型 + 判别规则的 lit 用例；**按需**改写既有断言，见阶段 C 披露项）、`tests/scripts/dadao-dyn.lds`（布局义务理由同步）。
  3. **派生投影**：`tools/llvm/llvm-isa-backend-matrix.{md,tsv}` 重生成（`gen_isa_coverage.py`）。
  4. **变更记录**：`components/llvm-project/changelog.md` 按维护规则追加一条（M8）。
  5. **证据 / 日志**：`.work/evidence/<任务ID>/**`（一键证据 + 独立 oracle + 原始输出）、`.work/log/llvm/**`（二者 = `gitignore` 区，不入 git）。
  6. **本任务书**完成区 + 审阅记录（`milestones.md` 流水行由 architect / 主会话收尾维护，本册**不写**）。
- **约束**：最小改动、只碰任务范围；**不得**改 `spec/`（上游只读册，须用户事先授权）、`contracts/`（机器可读）、`.tao/contracts/**`（正文，须授权）；组件源一律 **git 基线**（只经 `patches/**`，**不得**直接改 `.work/source/**`）；**禁** `git add -A`、**禁** `git checkout/restore/stash`；**计数不写死**（现场派生）；**期望值独立**（`contract-dynlink.md §8`：**不从** LLVM / LLD / QEMU / 本仓工具反推）。

## 做（分阶段 A–D；每阶段各自可验收）

### 阶段 A —— 新类型 + lld 消费侧（`R_DADAO_REL32`）

1. `DADAO.def.patch`：加 `ELF_RELOC(R_DADAO_REL32, 14)`、`R_DADAO_NUM` 改 **`15`**；头注释编号表同步（`14 = REL32`、`15 = type count`）。
2. `lld/ELF/Arch/DADAO.cpp`：
   - `iRelSymbolicRel` 的**注释**按 `NUM = 15` 同步（哨兵值随枚举自动正确）。
   - `getRelExpr`：`R_DADAO_REL32` ⇒ **PC 相对**语义（`S + A − P`；本记录 `P` = 记录自身地址 —— 由 (甲) 的补偿 addend 保证两条记录得**同一个** `disp`）。**不得**被 `undefBranch` 特例吸收（其门控 = `REL26`/`REL20`/`REL14`）；符号是**已定义**的本地槽标签 ⇒ **不得**触发 PLT / 副本路径。
   - `relocateInSection` 新增 `R_DADAO_REL32` 分支（**逐条规则**）：
     1. **值域**：`val` 必须落 `int32`（`isInt<32>`），否则 `Err`（**link-time error**，不截断 / 不 wrap）；
     2. 读自身指令：`insn = read32be(loc)`、`wp = (insn >> 16) & 0x3`；
     3. **按 `disp` 符号设定**该条 opcode 与 16 位立即数（**幂等、逐条独立**）：
        - `wp == 1`（**hi**）：输入 opcode 须 ∈ {`set.zw`-rd `0x4C`, `set.ow`-rd `0x4D`}（`rd` 域须与配对次条**同值**）；输出 opcode = `disp < 0 ? 0x4D : 0x4C`；立即数 = `(disp >> 16) & 0xFFFF`；
        - `wp == 0`（**lo**）：输入 opcode 须 ∈ {`or.w`-rd `0x48`, `andn.w`-rd `0x49`}；输出 opcode = `disp < 0 ? 0x49 : 0x48`；立即数 = `disp < 0 ? (~disp & 0xFFFF) : (disp & 0xFFFF)`；
        - 其它 `wp` ⇒ `Err`（落点不符）；
        - **写回**：`insn = (insn & 0xFFFF0000u) | slice` + `write32be(loc, insn)`（保留 opcode 之外的寄存器 / `wp` 域，与 `ABS48` 指令路径同构）。
     4. **落点校验（配对）**：hi 记录的**下一条**指令（`loc + 4`）须是**同 `rd`** 的配对次条（`or.w`-rd / `andn.w`-rd 且 `wp == 0`）；lo 记录的**上一条**指令（`loc − 4`）须是**同 `rd`** 的配对首条（`set.zw`-rd / `set.ow`-rd 且 `wp == 1`）；不符 ⇒ `Err`。**跨指令读取须确认仍在同一 `InputSection` 内**（越界不得读、报错）。
   - 文件头注释的类型表 / `pltDataOffset` 注释随阶段 B 一并同步。
   - **注意**：REL32 **只在指令域**（`.text`）——不像 `ABS48` 有「数据 8 字节字段」的第二路径；`relocate`/`relocateAlloc` 的分派须保证该类型**不**落到数据路径。

### 阶段 B —— PLT 内联去槽

1. `writePlt` 重写为 **4 条指令 / 16 B**：配对序列（**链接器自选**：`disp ≥ 0` 发 `set.zw`+`or.w`；`disp < 0` 发 `set.ow`+`andn.w`，**无改写环节**）+ `ldm.o {rb4}, [rb0, rd5]`（`immu6 = 1`）+ `jump [rb4, rd0, 0]`；**无 padding / 无数据槽**。
   - `disp = sym.getGotPltVA(ctx) − (pltEntryAddr + 8)`（条目内 `ldm.o` 的地址 = 条目 `+8`）。
   - 编码（阶段 3 的编码式）：首条 = `op<<24 | 5<<18 | 1<<16 | hi16`（`op` = `0x4C` 或 `0x4D`）、次条 = `op<<24 | 5<<18 | 0<<16 | imm16`（`op` = `0x48` 或 `0x49`；负形 `imm16 = ~lo16`）。
2. `pltEntrySize` **24 → 16**；`pltDataOffset`（及其 `static_assert`）**删除**；`assert((pltEntryAddr % 8) == 0)` 保留（16 B 条目仍 8 对齐 ⇒ `ldm.o` 取 8 字节槽安全）。
3. **不动**：`pltHeaderSize`（0）、`gotPltHeaderEntriesNum`（2）、`writeGotPlt`（写 0）、`writeGotPltHeader`、`.got.plt` 的 `JUMP_SLOT` 机制。

### 阶段 C —— CodeGen GOT 取址 3 条形态（**两处**）

1. `DADAOISelDAGToDAG.cpp` **两处**（L270–279 GOT 槽、L351–357 跳表基址）：把「`ld_o_rb rb0, <槽>`」改为
   「**地址序列**（2 条 ⇒ 产出 **`rdX`** 临时）+ `ldm_o_rb {rbT}, [rb0, rdX], immu6 = 1`」。
   - **建议形态**：新增**伪指令**（如 `GOT_ADDR32 (outs GPRD:$off), (ins unknown:$sym)`，`DADAOCodeGen.td`）+ `expandPostRAPseudo` 展开为 `set_zw_rd $off, wp1, sym` + `or_w_rd $off, wp0, sym`（**与 `GLOBAL_ADDR` 同型**，`DADAOInstrInfo.cpp`）；`ldm.o` 复用既有 `ldm_o_rb`（op `0x3A`，`GPRB` dst / `GPRB` base / `GPRD` offset / `immu6`）⇒ **无须新增 ISA 指令、无须新 `.td` 指令**（只新增伪指令，仍须 `install-host`，`ISS-210`）。
   - ⚠️ **临时寄存器活性**：`rdX` **须由寄存器分配器分配**（伪指令输出 = vreg ⇒ 后 RA 展开时用它**已分配**的物理寄存器），**不得**硬编码 `rd5`（展开点可能正持活跃值 ⇒ **静默破坏**）；若确用固定 scratch，须**证明**展开点无跨序列活跃值（把证据写进完成区）。**不得**用 `rd0`–`rd3`。
2. ⚠️ **MC 侧类型判别（现状盲点，必须解决）**：`set.zw`/`or.w`/`andn.w` 的 **`rd` 银行 + 符号操作数**现由 `isAddressConstructionInstr` 映射为 **`R_DADAO_ABS48`**，而 REL32 的落点**也是同一组指令** ⇒ 两者冲突（`ABS48` = 绝对地址 `S + A`；`REL32` = PC 相对 `S + A − P`）。**必须新增可机械判定的判别规则**（实现选定 + 完成区写明**理由**与**可达 FAIL 证据**）：
   - **(i) 按目的寄存器族**（**推荐**）：**`rd` 银行 ⇒ `R_DADAO_REL32`**；**`rb` 银行 ⇒ `R_DADAO_ABS48`**（现状仓库 ABS48 的**指令形式只由 `rb` 银行使用**：`set.rb` / `GLOBAL_ADDR` / `JT_ADDR` 均 `rb`）；与 `ADR-0021 D1`「汇编器按寄存器自动选类型」**同构**。**连带面（须披露）**：既有 lit `tests/llvm/lit/MC/DADAO/m6-callconv.s`（L53–54 用 **`rd` 银行**断言 `R_DADAO_ABS48`）须改写为 **`rb` 银行**（保持其 ABS48 意图）——属**向量改写**、非契约变更。
   - **(ii) 按 `wp` + 配对形态**：`rd` 银行下 `set.zw wp1`（hi）/ `or.w`·`andn.w wp0`（lo）⇒ `REL32`；其余（ABS48 的 `set.zw wp0` 起步序列）⇒ `ABS48`（不动既有 lit，但规则更隐晦）。
   - **无论取哪条**：同一指令**不得**有两种类型解释（否则静默错值）；判别逻辑须有**可达 FAIL** 用例。
3. **MC 侧新增 fixup / 记录**（逐条）：
   - `DADAOFixupKinds.h`：新增 kind（hi / lo 两个，便于按记录落 addend）；**必须追加在 `DADAO_FK_ABS12` 之后**并同步 `LastTargetFixupKind`（`Infos[]` 按 `Kind − DADAO_FK_PCRel_12` 索引 ⇒ 顺序即契约）。
   - `DADAOAsmBackend`：`Infos[]` 追加 `{…, 0, 16, 0}`（**16 位 wyde**，与 `ABS48` 同型）；**显式处理**新 kind——⚠️ 现 `applyFixup` 的早退边界 `Kind > DADAO_FK_ABS12 ⇒ return` 会把新 kind **静默跳过**（既不发 reloc 也不写值）⇒ 必须放在该边界**之前**处理；⚠️ `evaluateFixup` 的就地解析白名单（`IsPCBranch` / `IsLdstPCRel`）**不得**纳入 REL32（`.Lgot.*` 若被判为同 section 就地折叠，`A − 8` / `A − 4` 补偿**只在链接期 `P` 已知时成立** ⇒ 就地折叠即**静默错值**）。
   - `DADAOELFObjectWriter::getRelocType`：新 kind ⇒ `ELF::R_DADAO_REL32`；`needsRelocateWithSymbol` 若被改写为 section 符号 + addend，须核**净效果不变**（不确定时按 `ABS48` 同法处理 + 留证）。
   - `DADAO.h` 增目标标志（如 `MO_GOT32_ADDR`）+ `DADAOMCInstLower` 映射（沿用 `MO_GOT_ADDR` 的**槽标签**路径）⇒ 供 `isAddressConstructionInstr` 之外的**新判别**使用。
   - ⚠️ **addend 补偿（形态 (甲)）**：**hi 记录 `r_addend = A_expr − 8`**、**lo 记录 `r_addend = A_expr − 4`**（`A_expr` = 符号表达式的常量部分；现状槽标签路径 `A_expr = 0` ⇒ 期望 `−8` / `−4`）。**候选路线**（须现场验证）：把常量写进 `MCSymbolRefExpr`（`sym + (−8)` / `sym + (−4)`，与 `.quad sym+N` 同路径）；**验证方式** = `llvm-readobj -r` 逐条读 `r_addend`。
4. **派生投影**：`python3 tools/llvm/gen_isa_coverage.py` 重生成 `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（否则 L1 `check-isa-coverage` drift 报红）。

### 阶段 D —— 测试与证据

1. **`tests/scripts/dadao-dyn.lds` 更新**：删除 / 改写「`.got` 必须紧跟 `.text`（±2 KiB）」的**理由与依赖**（布局义务已取消，`ADR-0026 D5` 修订 / `ADR-0028 D8`），保留 ET_DYN 段全集 + `PT_INTERP`/`PT_DYNAMIC`/`PT_GNU_RELRO` 口径；确认该脚本仍可被 `ld.lld` 接受（rc=0）。
2. **向量 / 产物排查**（现场机械 `grep` + 逐条留证）：写死 **`pltEntrySize = 24`** 的注释 / 文档、**旧 PLT 字节串**（`20140010` / `3a100141` / `71100000` 及「条目 `+16` 处 8 字节常量」）、**`NUM = 14`**（含 `lld/ELF/Arch/DADAO.cpp` 注释）、**`R_DADAO_ABS48` 在 `rd` 银行**的用法（阶段 C 判别规则的连带面）⇒ 仓库内**真源**同步（历史归档 `.tao/archive/**` **不得改**）。
3. **一键证据** `.work/evidence/<任务ID>/run.sh`（含 `--inject`；**自包含**：源 / 输入由脚本自建，**不依赖 `/tmp` 未留存文件**——`LLVM-094t` 阶段 C 第 1 轮 `run-a.sh` 教训；每条断言有**可达 FAIL** 路径；还原用 `cp` + md5 对账，**禁** `git checkout/restore/stash`；**禁**恒真断言 / 计数写死），覆盖：
   - **a 正 `disp` 路径**：`-shared`（**默认布局**）⇒ `ld.lld` **rc=0**；独立解析核 `.text` 序列 = `set.zw rdX, wp1, hi16` + `or.w rdX, wp0, lo16` + `ldm.o`；重定位表 **两条 `R_DADAO_REL32`**（`r_offset` 相差 4、`r_addend` = **−8 / −4**）；`hi16`/`lo16` 与 `disp = 槽VA − P_ldm` **逐条独立核算相等**；
   - **b 负 `disp` 路径**：构造 `S_slot < P_ldm`（槽位于访问点**之前**）⇒ 实测首条 opcode = **`0x4D`**（`set.ow`）、次条 = **`0x49`**（`andn.w`）且次条立即数 = **`~lo16`**（**逐字节**），**独立核算**逐条相等；并断言**不是** `set.zw`+`or.w`（**反例判别**）；
   - **c PLT 去槽**：`.plt` 尺寸 = **16 × 条目数**、每条 4 条指令（末条 `jump` 在条目 `+12`）、条目内**无** 8 字节常量；`pltEntrySize` 实测 = 16（由 `.plt` 尺寸 / 条目数**现场派生**，不写死）；
   - **d 默认布局可链接（布局义务取消的正面证据）**：**不用** `-T tests/scripts/dadao-dyn.lds` ⇒ `ld.lld -shared` **rc=0**（旧行为 = `R_DADAO_REL12 out of range` **rc=1** ⇒ **反例判别**可用）；`--print-map` 记 `.got` 与访问点距离 **> 2 KiB**（证明「越界距离下仍成功」）；
   - **e 错误路径（两条，各留可达 FAIL）**：① **落点不符**（如单独一条 `set.zw rdX, wp1, <sym>` 后接非同 `rd` / 非配对次条）⇒ rc=1 + 指定文案；② **越界**（用链接脚本把 `.got` 放到 `> 2 GiB` 处 ⇒ `disp` 超 `int32`）⇒ rc=1 + 越界文案；
   - **f 静态不回归**：6 例（`t` / `sw` × O0/O1/O2）剥 `.comment` 后 md5 与**基线**相同（基线**随证据留存**，**不得**依赖 `/tmp`）；
   - **g 门控**：见「验收标准 5」。
4. `components/llvm-project/changelog.md` 追加 M8 一条（按维护规则；摘要 + 缩进行）。

## 验收标准（逐条可判：命令 + 期望）

1. **类型可用**：`llvm-readobj -r <obj>` 对 `set.zw rdX, wp1, <sym>` + `or.w rdX, wp0, <sym>` 的配对**报两条 `R_DADAO_REL32 (14)`**、`r_addend` = **`-8` / `-4`**、`r_offset` 相差 **4**；`R_DADAO_NUM` = **15**（枚举查核 + `DADAO.def` 逐行）。
2. **lld 消费端**：`ld.lld -shared`（**默认布局**）**rc=0**，产物 `.text` 中两条指令的 wyde = `disp[31:16]` / `disp[15:0]`（**独立解析逐字节核**，`disp = 槽VA − P_ldm`）；`disp < 0` 时两条 opcode 实测 = `0x4D` / `0x49` 且次条立即数 = `~lo16`。
3. **PLT**：`.plt` 每条目 **16 B**、4 条指令、**无数据槽 / 无 padding**；`.got.plt` 仍由 `JUMP_SLOT`(7) 填充（`readelf -r` + 独立解析）。
4. **错误路径**：落点不符 / `disp` 越 `int32` ⇒ `ld.lld` **rc=1** + 指向该重定位的文案（**不静默**、不截断 / 不 wrap）。
5. **门控**（各留**自身** rc，**禁** `cmd | tee` 吞码）：`make check`（**L1**）、**`make check-modules`（L2，任务收尾，单独跑；`ISS-229` ⇒ 不与 L3 / 其它重建并发）**、`check-patch-tree`、`check-index-blobs`、`check-instrinfo`（**改 `.td` ⇒ 先 `make install-host`**）、`check-source-state`、`check-isa-coverage`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-knowledge-dir`、`check-component-changelog`、`python3 tools/infra/check_issues.py` 各 **rc=0**；`make check-full`（L3）在里程碑 / `/complete` 跑。
6. **证据**：`.work/evidence/<任务ID>/run.sh` **rc=0** 可跑通；`--inject` 全绿（每条断言有**可达 FAIL** 路径）；**独立 oracle**（自写 ELF64-BE 解析 + 手工公式，**不经** LLVM 读取器；期望值**不从** v5 自身实现反推）；**证据自包含**（不依赖 `/tmp` 未留存文件）。
7. **静态不回归**：6 例（`t` / `sw` × O0/O1/O2）剥 `.comment` 后对象 md5 与基线**相同**；`-fno-pic` 路径仍走 3 片 `ABS48`。
8. **大端**：`EI_DATA = ELFDATA2MSB`；至少 1 例 BE 敏感证据（两 wyde 的字节序）。
9. **越界 / 范围声明**：`git status --porcelain -uall` **无** `spec/`、`contracts/`、`.tao/contracts/**` 改动；改动面与完成区「修改文件」**逐条对齐**。

## 前置申报（**必读**）

- 本任务**必改 `components/**`（= 编译输入）** ⇒ 必须**单跑** `make install-host`（预计 **≈6 min**；`build-mc` ≈5 min / `build-lld` ≈40 s，视改动面）；**`JOBS=8`**、**禁全核**；**不得**与 `build-*` / L2 / L3 / 其它会话的重建**并发**（`ISS-229`）。
- **改 MC / `.td` 后必须 `make install-host`**（否则门控 / lit 读**旧安装根** ⇒ **假绿**；`ISS-210`）。
- 长任务（>10 min）由**主会话** `setsid nohup` 脱离 + 落 `XXX_EXIT=$rc`；**子代理不得在会话内等待长任务**。

## 不做项（显式）

1. **`qemu-user` / 动态链接的「运行」验证**（`P3`）✗；本册**不可**有「运行通过 / E2E」叙述。
2. **改 `spec/`**（含 `DADAO-21` 寄存器表）/ **改 `contracts/`（机器可读）** / **改 `.tao/contracts/**`（正文）** ✗。
3. **relaxation**（`ADR-0019 D7`）✗；**新增 ISA 指令** ✗（本册只新增伪指令 / fixup / 重定位类型）；**自写 `ld.so`** ✗。
4. **`ABS48` 两段式**（`ABS48` 序列 + `ldm.o_rrri_rb` 落 `rb`）✗ —— **已被 `ADR-0028` 替代**，不得作为实现路径。
5. **`rd2` / `rd3` 语义改动** ✗（`spec/` 保留；本册**不**使用）。
6. **`COPY` / `TLSDESC` / TLS / IFUNC** 的首版支持 ✗（维持 `LLVM-094t` 阶段 C 的**主动拒绝**）。
7. `ISS-222` / `ISS-223` 收口 ✗（撞上即登记 + 转出，**不得**静默跳过）。

## 下发前预检（architect，`AGENTS.md`「下发前预检（强制）」5 项）

1. **任务书内部一致** ✓：类型 / 编号（`REL32` = 14、`NUM` = 15）、公式与 `P` 基准、记录形态 (甲)（`A − 8` / `A − 4`）、落点（hi → `wp1` / lo → `wp0`）、缺省非负与负值同改、PLT（16 B / 无槽 / `disp = 槽VA − (条目+8)`）、GOT（3 条 / `disp = 槽VA − P_ldm`）与 §3 编码式**逐条自洽**（含 `P_hi + 8 = P_lo + 4 = P_ldm` 的核算）。
2. **验证手段的前置**（含跨任务门控载体 / 工具）**实际可用** ✓：`ld.lld` / `clang` / `llvm-readobj` / `llvm-objdump` / `llvm-mc` 均在安装根且已支持 DADAO（094t 阶段 A/B 实测）；`llvm-readobj -r` 现即按 `DADAO.def` 打印 `R_DADAO_*` 名（新类型加进 `DADAO.def` 后**自动**可打印 —— 已由 094t 的类型名打印实证）；`make {build-mc,build-lld,install-host}` target 在位；`tests/scripts/dadao-dyn.lds` 现状可被 `ld.lld` 接受；`.work/evidence/` 与 `.work/log/llvm/` 落点既有。**无前置缺失。**
3. **验收逐条**（见「验收标准」）：
   | 验收项 | 现在可跑？ | 说明 / 替代证据 |
   |---|---|---|
   | 1 类型可用（`llvm-readobj -r` 两条 `REL32` / addend） | **BLOCKED（实现依赖）** | 原因 = 新类型与 MC 发射尚未实现；**替代证据（前置可跑）** = 现状同类面已实证：`llvm-readobj -r` 现即打印 `R_DADAO_ABS48 (6)` / `REL12 (4)` 等名，`set.zw rb1, ext2` 现产 3 条记录（`ADR-0028` 「记录形态」节实测），⇒ 「一指令一条记录 + addend 随表达式」通道可用 |
   | 2 lld 消费端（`-shared` 默认布局 rc=0 + wyde 逐字节） | **BLOCKED（实现依赖）** | 原因 = lld `relocate` / `writePlt` 未实现；**替代证据** = **旧行为已可现场复现**（`ld.lld -shared` ⇒ `R_DADAO_REL12 out of range` rc=1），即**该断言的 FAIL 侧现在可跑**（反例基线在位） |
   | 3 PLT 16 B / 无槽 | **BLOCKED（实现依赖）** | 原因 = `writePlt` 未改；**替代证据** = 现状 24 B 形态已逐字节实测并留存（`.work/log/llvm/LLVM-094t-B-*.log`；`.work/**` = gitignore） |
   | 4 错误路径（落点不符 / 越界） | **BLOCKED（实现依赖）** | 原因同 2；构造手段（自定义 `lds` 把 `.got` 放高地址 / 手写非配对序列）**现在即已可用**（`llvm-mc` + `ld.lld -T`） |
   | 5 门控（L1/L2 + 各单项） | **现在可跑** | L1 与单项现均 rc=0（094t 阶段 E 末轮实测）；L2 待收尾单独跑（`ISS-229`） |
   | 6 证据脚本可失败 / 独立 oracle | **现在可跑（框架）** | 自写 ELF64-BE 解析器先例在位（`.work/evidence/LLVM-094t/{elfinfo,dyncheck,oracle_c}.py`）；断言数值待实现后填 |
   | 7 静态不回归 | **现在可跑** | 基线可由现状现场生成（6 例 × 剥 `.comment` md5），094t 同法已证 |
   | 8 大端 | **现在可跑** | `llvm-readobj -h` 现即报 `ELFDATA2MSB` |
   | 9 越界 / 范围声明 | **现在可跑** | `git status --porcelain -uall` 现场可判 |
4. **与 `contracts/`、`tests/vectors/` 一致** ✓：本册**不**改 `contracts/`（机器可读）与 `tests/vectors/**`；口径逐条取自 `.tao/contracts/contract-elf.md §2.2`/`§3.1`/`§3.2`/`§4` 与 `contract-dynlink.md §3`（现场核后**一致**：`REL32` = 14 / `NUM` = 15 / hi `A − 8`、lo `A − 4` / hi → `wp1`、lo → `wp0` / 越界与落点不符 ⇒ link-time error / 固定 2 片）；`tests/vectors/**` 内**无**写死 `REL32` / PLT 尺寸的条目（现场 `grep` 0 命中）。
5. **拟改文件 × `spec/` 清单** ✓：拟改面 = `components/llvm-project/patches/**`、`tests/llvm/lit/MC/DADAO/**`、`tests/scripts/dadao-dyn.lds`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（重生成）、`components/llvm-project/changelog.md`、本任务书；**`spec/` 命中数 = 0** ⇒ **无需用户授权**（`ADR-0028 D6`：不改 ISA、不动 `rd2`/`rd3` ⇒ `spec/` 零改动）。**例外提示**：若实现过程中发现**必须**改 `spec/`（如 `DADAO-21` 寄存器表 / 指令语义），**即刻停下报告**（`spec/` 改动须用户原话授权）。

## 完成区

### 阶段 A 验收复核（构建后，2026-10-16 下午）

> **本节取代上一节的「未构建 / 未跑」口径**（上一节写于 `install-host` 之前；现工具链已重建：`make install-host` **PASS** / `INSTALL_EXIT=0` / 安装根 `.dadao/cross-toolchain/bin/`，时间戳 `11:56–12:04`）。上一节其余内容（补丁导出、枚举核查、探针）经复核**仍成立**，本轮已重跑并留新日志。

**测试结果**：一键证据 `.work/evidence/LLVM-095t/stage-A/run.sh` **rc=0 · 92 PASS / 0 FAIL**（`RESULT: PASS`；日志 `.work/log/llvm/LLVM-095t-A2-run-stageA.log`）；三个 `--inject` 各 **rc=1**（注入→**实测红**→`cp`+md5 还原→回绿，同一次前台执行内闭合；日志 `LLVM-095t-A2-inject-*.log`）。第 1 轮两项探针重跑亦全绿（`gen_rel32_probe.py` 24/24、`rel32_model_check.py` 9 例，rc=0）。

**验收结果**（逐条真值，数字逐字来自当次输出）：

| 项 | 实测 | rc |
|---|---|---|
| 1 类型可用 | `llvm-readobj -r --expand-relocs` ⇒ `Type: R_DADAO_REL32 (14)` + `Addend: 0xFFFFFFFFFFFFFFF8 / …FC`；两条记录 `r_offset` 差 **4**；type 15 记录 ⇒ `Type: R_DADAO_NUM (15)`；`DADAO.def.patch` 逐行 = `14`/`15` | 0 |
| 2 发射侧 | `llvm-mc` 对 `set.zw rdX,wp1,<sym>`+`or.w rdX,wp0,<sym>` 现仍产 **`R_DADAO_ABS48 (6)`×2** ⇒ **归阶段 C**（如实标缺口，非本阶段缺陷） | 0 |
| 3a 正 disp | `-shared` **默认布局** rc=0；`disp=131208 (0x20088)` ⇒ `.text` 实测 `4c210002 48200088` = `disp>>16` / `disp&0xFFFF`，`rd`/`wp` 保留 | 0 |
| 3b `.got` 槽形态 | `-shared` 默认布局 rc=0；`disp=65544 (0x10008)` ⇒ `4c150001 48140008`（`rd5`）；**两例 disp 均 > 2 KiB**（旧 `REL12` 不可达） | 0 |
| 3c 负 disp | `disp=-16` ⇒ **逐字节** `4d21ffff4920000f` = `set.ow`+`andn.w`，次条立即数 = `~lo16`；反例判别：首/次 opcode 实测**非** `0x4C`/`0x48` | 0 |
| 3d 落点不符 | 邻接同 `rd` 不满足（`or.w rd9`）/ 单独 `set.zw` ⇒ `rc=1` + 文案指名 `R_DADAO_REL32` | 1 |
| 3e 越界 | `-T` 脚本把 `.data` 放 `0x90000000` ⇒ `R_DADAO_REL32 out of range: 2415915000 is not in [-2147483648, 2147483647]` | 1 |
| 3f 幂等 | 输入已是 sign 形 ⇒ 输出**逐字节不变**（正/负各 1）；输入为**反形**（`disp≥0` 却预置负形）⇒ 输出 = **sign 形**（证明由 `disp` 派生、非读旧 opcode） | 0 |
| 4 不回归 | 6 例（`t`/`sw` × O0/O1/O2）剥 `.comment` md5 **逐字节等于**基线（`baseline-pre-nocomment.md5`，生成于阶段 A 之前）；`-fno-pic` 仍 `ABS48`-in-`.text` 且无 `.got`；`make check`(L1) **rc=0**；`check-patch-tree` **rc=0** ⇒ `5 component(s), 147 patches OK`；`check-index-blobs` rc=0 | 0 |
| 8 大端 | 对象/产物 `EI_DATA=2`；两 16 位字段字节序 `48 20 00 88`（LE 会读 `88 00 20 48`） | 0 |
| 9 范围 | `git status --porcelain -uall` = **仍仅那 3 项**（本任务书 + 2 补丁）；`spec/`/`contracts/`/`.tao/contracts/` **0 命中** | — |

**修改文件**（本轮）：仅 `.work/evidence/LLVM-095t/stage-A/`（`run.sh`、`rel32elf.py`、`rel32oracle.py`、`README.md`、`baseline-pre-nocomment.md5`，均为 `gitignore` 区）＋ 本任务书。**未改** 组件源码 / 补丁 / `tests/` / `spec/` / `contracts/` / `.tao/contracts/`。

**新发现/坑**：① **`--inject` 须能真红**：`swap-addend` 用「对调补偿 addend」而非「翻期望常量」，实测 `lo16` 变 `48200084≠48200088`（差 4 = 补偿量）⇒ 证明断言与**补偿语义**绑定；② 手工构造 REL32 对象时**不能假定 `_start` 在 `.text` 偏移 0**（负 disp 用例把槽放前面 ⇒ 记录在 `0x8/0xC`）⇒ 补丁脚本改为按 `.rela.text` **记录序**打补丁（`patch-rel32-pair`），并对「单独 `set.zw`」用例按符号值定位；③ `-shared` 下符号若为 `.globl` ⇒ lld 报 `cannot be used against symbol; recompile with -fPIC`（`R_PC` 对可抢占符号）⇒ 探针槽标签须为**局部**符号（与真实 GOT 槽标签 `.Lgot.<n>` 一致）；④ `sed` 的 `0x\?` 在 GNU sed 4.9 **不生效** ⇒ 改 `\(0x\)\?`（教训：正则里的「可选」只在实测通过后才用）；⑤ `run.sh` 目录层级比 `LLVM-094t` 深一层 ⇒ `ROOT=$(cd …/../../../..)`（首跑 rc=2 已修）。

**遗留问题**：① **阶段 A 未覆盖项（如实列）**：**发射侧（MC）** —— 新 fixup kind（hi/lo）+ `A−8`/`A−4` 补偿 + `rd`⇒`REL32`/`rb`⇒`ABS48` 判别 + `Infos[]`/`LastTargetFixupKind`/`getRelocType` 连带面，**全部归阶段 C**；本轮 `.rel32.o` 系**打补丁**构造（只改记录，不动指令字节，已在 README 与 `T2` 明标）。② 阶段 B（PLT 内联去槽）/ D（`dadao-dyn.lds` 理由、派生投影重生成、`changelog.md` M8 一条）未做。③ 构建/L2/L3 归主会话（`ISS-229`）。④ 任务级 `**状态**` **保持 `待开始`**（A–D 未齐，标 `待验收` 会令「验收标准 1–9」跑不通）；是否改由主会话裁定。

### 阶段 A —— 原始记录（写于 `install-host` 之前；口径见上节复核）


**测试结果**：`make check-patch-tree` **rc=0** ⇒ `check-patch-tree: 5 component(s), 147 patches OK`；`make check-index-blobs` **rc=0** ⇒ `108 new-file patch(es) OK; 39 modification patch(es) skipped`。**未构建**（构建归主会话）⇒ 本笔三项**不需构建**的真实证据全绿：① `-fsyntax-only` 真实 TU `lld/ELF/Arch/DADAO.cpp` **rc=0**（log 0 字节 = 零诊断）＋ `llvm/lib/Object/ELF.cpp` **rc=0**；② 枚举核查（编译并运行）= `R_DADAO_REL32=14 R_DADAO_NUM=15 ABS48=6 REL12=4 TLSDESC=13` `rc=0`；③ 新分支**逐字抽取**（98 行）→ 独立 TU＋桩 → **24 用例 24 pass / 0 fail `rc=0`**；5 注入变体（`lo-stays-or-w`/`lo-no-complement`/`no-pair-check`/`no-range-check`/`no-exec-guard`）＋ `--inject` **全 `rc=1`**、还原后回绿 ⇒ 每条断言有可达 FAIL 路径。日志 = `.work/log/llvm/LLVM-095t-A-*.log`；脚本留存 = `.work/evidence/LLVM-095t/stage-A/`（README 含复现命令）。

**修改文件**：① `.work/source/llvm-project/llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def`（+24/−4，加 `REL32`=14、`NUM`→15、注释表）；② `.work/source/llvm-project/lld/ELF/Arch/DADAO.cpp`（+144/−9：`getRelExpr` 加 `REL32⇒R_PC`；`relocateInSection` 加 `REL32` 分支 + 私有 helper 增 `secBegin/secEnd` 默认参；`relocateAlloc` 传本段边界；`iRelSymbolicRel`/文件头注释同步）——二者为**组件源码**（就地改）；③ 导出补丁 `components/llvm-project/patches/{llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def,lld/ELF/Arch/DADAO.cpp}.patch`（85 / 623 行；`make_patch.py` = `2 written, 71 unchanged`；`series` 未变 ⇒ 73 项 / 全仓 **147**）；④ 本任务书。**组件 scratch 检出** `fb1ad9b1b → 996821495`（E1：worktree 干净 + `base..HEAD` 恰 1 commit）——**非** DADAO-v5 提交。

**阶段进度**：**A 已完成**（含自审，见「审阅记录」）；**B/C/D 未做**（PLT 内联去槽 / CodeGen 3 条形态 + MC fixup / 测试与证据）⇒ 任务级 `**状态**` **保持 `待开始`**：本册「验收标准」1–9 依赖 A–D ＋ 构建，本笔标 `待验收` 会令验收跑不通；是否改状态由主会话裁定。

**验收结果**（逐条，真值）：标准 1 **部分**——`DADAO.def` 逐行与枚举实值已核（`REL32=14`/`NUM=15`，现场输出见上），而 `llvm-readobj -r` 两条记录 / `r_addend` = `−8`/`−4` / `r_offset` 差 4 **未做**（依赖阶段 C 的 MC 发射）；标准 2/3/4/7/8 的 lld 消费侧代码已就位但**未跑**（需 `build-lld`）；标准 5 本笔范围门控 = `check-patch-tree`/`check-index-blobs` rc=0（L1/L2 **未跑**）；标准 9 = `git status --porcelain -uall` 仅列上述 2 补丁（本任务书外），`spec/`、`contracts/`、`.tao/contracts/` **0 命中**。

**新发现/坑**：① 组件 scratch 树**必须** amend 提交才满足 `check-patch-tree` 断言⑦⑧（`make_patch.py` 的 E1 检查也会拒导出）——本笔照 `docs/Process-01 §6.4`：显式列 2 个文件 `git add` + `git commit --amend --no-edit`（**未**用 `git add -A`）；② `reportRangeError(ctx,loc,rel,v,min,max)` 是 `checkInt` 的底层（声明在 `Target.h`，本文件已 include）⇒ 越界文案与既有 `REL26/REL12` 同型（`relocation R_DADAO_REL32 out of range: X is not in [...]`）；③ 自检探针首版 driver 把 `errorCount+rangeErrorCount` 与**陈旧** `lastError` 混判 ⇒ `no-pair-check` 变体**漏检**（假绿）；改 `resetDiag()`＋「对应计数器的诊断文本」匹配后 5 变体全捕获（**教训：错误断言必须绑定对应计数器的消息，不能只数 rc/计数**）；④ **契约空白**：`contract-elf.md §2.2/§3.1` **未记载**「同一组 `rd` 银行指令在 `REL32` 与 `ABS48` 之间如何判别」（`ABS48` 行未限制寄存器银行）——本笔处置 = 按任务书阶段 C 2(i)：**lld 侧以 opcode 集合判别**（本笔已落：`0x48/0x49/0x4C/0x4D` = `rd` 银行，`rb` 银行 `0x4A/0x4B/0x4E` ⇒ `Err`）；**MC 侧**判别（`rd`⇒`REL32` / `rb`⇒`ABS48`）**属阶段 C**，本笔未改 MC ⇒ `tests/llvm/lit/MC/DADAO/m6-callconv.s`（L53–54 `rd` 银行 + `@reloc R_DADAO_ABS48`）**未动**（改早了会令现行 MC 行为报红；须随阶段 C 一并改写）；未改 `spec/`/`contracts/`/`.tao/contracts/`（无授权）⇒ 建议阶段 C 落纸时回填该判别规则（`ADR-0021 D1` 同构先例）；⑤ 阶段 A **不含** PLT 内联 ⇒ `pltDataOffset`/`writePlt` 与其注释**未动**（阶段 B）。

**遗留问题**：① 阶段 B/C/D 全部未做（本笔范围外）；② 构建、`install-host`（`ISS-210`/`ISS-229`）、L1/L2 **未跑** ⇒ 归主会话/阶段 D；③ 阶段 D 待同步项：写死 `pltEntrySize = 24` 的注释与旧 PLT 字节串、写死 `NUM = 14` 的仓库内真源（本笔 grep：`tools/`/`tests/`/`contracts/` **0 命中**，`.tao/` 文档命中归阶段 D）、`tests/scripts/dadao-dyn.lds` 的 ±2 KiB 理由、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}` 重生成、`components/llvm-project/changelog.md` M8 一条（**本笔未加**，属阶段 D 项）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：`subagent_depth=1` ⇒ 无嵌套 reviewer，采**自主逐行审查**；本笔**无构建**可跑，故以三条**不需构建**的机械证据代替（`-fsyntax-only` 真实 TU / 编号枚举运行 / **逐字抽取**分支的 24 用例探针 + 5 变体注入 + `--inject`），并对**改动源码逐行**核对「值域 / 落点 / 改写 / 幂等 / 错误面」。
**判决**：finding 全部处置，**阶段 A 实现完成**（任务级状态见完成区「阶段进度」）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `relocateInSection` 私有 helper 需段边界（「配对读取不得越界」）——改签名有违「不改签名」惯例？ | ✅已修 | 新增 `secBegin`/`secEnd`，**带默认参 `= nullptr`** ⇒ `relocate()` 现有 4 参调用点**不变**；`relocateAlloc` 显式传 `[buf, buf+content().size())`（与 lld 自身 `bufEnd` 同式） | `-fsyntax-only` rc=0（零诊断）；探针 case 12（越界伙伴 ⇒ `Err`、落点未改） |
| F2 REL32 只存在指令形式，若落非可执行 section / 分派进数据路径 ⇒ 会按数据读 | ✅已修 | 分支首行守卫 `!isExec || !secBegin || !secEnd ⇒ Err`（**先判后退，不读内存**）；`getDynRel` 不给 REL32 动态类型（=0） | 探针 case 11（2 断言）、`no-exec-guard` 变体 rc=1 |
| F3 **探针假绿**：driver 用 `errorCount+rangeErrorCount` 与陈旧的 `lastError` 混判 ⇒ 「放宽 `pairWp` 校验」变体**未被捕获** | ✅已修 | driver 改 `resetDiag()` + 按**对应计数器**取文本匹配；补 case 14（hi 后接 `wp=1`）/case 15（lo 前驱非同族） | 5 变体全 rc=1（含 `no-pair-check`）；还原后 24/24 rc=0 |
| F4 越界（`|disp|` 超 `int32`）须报错、不截断/不 wrap | ✅已修 | `isInt<32>` 前置 + `reportRangeError(..., 32, ...)` 后 `return`（不写内存） | 探针 case 10/12（`2^31` 与 `−2^31−1`）+ `no-range-check` 变体 rc=1 |
| F5 判别规则（`rd`⇒REL32 / `rb`⇒ABS48）本笔落点 | ✅已修（lld 侧） | 见完成区「新发现/坑」④：ll**d 侧**以 opcode 集合判别（`0x48/0x49/0x4C/0x4D` 收，`rb` 银行 `0x4A/0x4B/0x4E` 拒）；**MC 侧判别属阶段 C**，`m6-callconv.s` 本笔未动 | 探针 case 9（`rb` 银行对 ⇒ `Err`）、case 8/15 |
| F6 `NUM` 14→15 的连带面（哨兵/注释/仓库内写死值） | ✅已修 | `iRelSymbolicRel = R_DADAO_NUM` 自动跟随；注释改 `D10/D11: R_DADAO_NUM = 15`；`DADAO.def` 头注释表改「`14 = REL32` / `15 = type count`」 | 枚举运行输出 `R_DADAO_NUM=15`；`git status` 无范围外文件；`NUM=14` 真源 grep 见完成区遗留③ |
| F7 「逐条独立 / 幂等」（禁跨记录状态） | ✅已修 | 输出 opcode 只由 `disp` 符号定、立即数只由 `disp` 定（不读旧 opcode 作依据）；`rd`/`wp` 原样保留（`insn & 0x00FF0000`） | 探针 case 7（只处理 lo 记录仍得同值）、case 8（重复施加字节不变）、`lo-stays-or-w`/`lo-no-complement` 变体 rc=1 |

#### 第 2 轮 engineer 自审（阶段 A 构建后验收复核）

**自审方式**：`subagent_depth=1` ⇒ 无嵌套 reviewer，采**自主逐行审查**。本轮有真实构建产物（安装根已重建）⇒ **全部结论改用「真跑真输出」**，并以**自写 ELF64-BE 解析器**（`rel32elf.py`）＋**契约 oracle**（`rel32oracle.py`）作独立判据 —— 期望值由 `disp = S + A − P_ldm` 与 `op<<24|rd<<18|wp<<16|imm16` **手推**，**不从 lld 输出反推**。
**判决**：finding 全部处置；阶段 A 的 lld 消费侧**真跑通过**（89 项 0 失败），发射侧如实归阶段 C；任务级状态见完成区。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| G1 「已装工具链是否含阶段 A 改动」未证 | ✅已证 | —（只加证据） | `llvm-readobj` 对 type 14 记录打印 `R_DADAO_REL32 (14)`、type 15 打印 `R_DADAO_NUM (15)`（枚举**在二进制内**生效） |
| G2 第 1 轮结论仅「不需构建」的证据（syntax-only / 探针），消费侧**未真跑** | ✅已修 | 新增 `rel32elf.py`（自写解析/打补丁）＋ `rel32oracle.py`（契约公式 oracle）＋ `run.sh`（T1–T11） | `run.sh` rc=0：正 disp `4c210002 48200088`、`.got` 形 `4c150001 48140008`、负 disp 逐字节 `4d21ffff4920000f` |
| G3 发射侧是否覆盖未判 | ✅已判（标缺口） | `T2` 断言 MC 现产 `ABS48 (6)`×2 | 实测 `6,6,` ⇒ **归阶段 C**；`.rel32.o` 的构造手段在 README/`T2` 明标 |
| G4 「负值同改两条」只在模型层验过，缺 lld 真字节 | ✅已修 | `T5` 逐字节 + 反例判别（opcode 非 `0x4C`/`0x48`） | `neg.bytes-byte-level` = `4d21ffff4920000f` rc=0 |
| G5 幂等 / 「由 `disp` 派生而非读旧 opcode」缺真判据 | ✅已修 | `T7`(b)：把输入预置成**反形**（`disp≥0` 却负形） | 输出 = sign 形 `4c21000248200088` rc=0（若读旧 opcode 会保留负形） |
| G6 错误路径的「预期 rc=1」可能恒真 | ✅已修 | `--inject fix-badpair`（改成合法配对 ⇒ rc=0）/ `--inject inrange`（大负 addend ⇒ 回 `int32` ⇒ rc=0） | 两次注入均**实测红**（`inj-fixpair.rc expect=1 actual=0` 等），还原后回绿 |
| G7 「补偿 addend」断言的判别力 | ✅已修 | `--inject swap-addend`：对调 `A−8`/`A−4` | `inj-swap.word1(lo16) expect=48200088 actual=48200084`（差 4）⇒ 变红；还原 md5 相同后回绿 |
| G8 静态不回归基线是否在**改动前**生成 | ✅已核 | 基线随证据留存（`baseline-pre-nocomment.md5`） | 6 例剥 `.comment` md5 **逐字节等于**该基线（生成于 `LLVM-094t` 阶段 C，**早于阶段 A**）→ 见 `T8` |
| G9 证据自包含 / 计数不写死 | ✅已修 | 探针源、打补丁、解析器、oracle、基线**全在证据目录**；补丁数 / 记录数 / `r_offset` 差**现场解析** | 首跑 `ROOT` 层级错 ⇒ rc=2 fail-fast（已修）；缺失输入 ⇒ `exit 2` |

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
