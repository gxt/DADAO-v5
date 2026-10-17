# ADR-0030: `long double` = IEEE binary128（四精度）

**状态**：Accepted（2026-10-17 定案：`D1`–`D8` 经用户**逐条确认** ✓ —— 确认表与用户原话见 `## 逐条确认表` / `## 状态说明`）
**日期**：2026-10-17
**决策者**：用户（**主张**与 `D1`–`D8` 均已裁定；2026-10-17 **逐条确认完毕** ✓ —— 见 `## 逐条确认表`）
**关联**：`ADR-0018`（`C4` 栈溢出区 / `C5` 返回值扩展 / `C9` DataLayout·`S128` / `C14` RB 银行语义）、`ADR-0027`（`D1` 只 `builtins`、`D5` 独立 compiler-rt 库）、`ADR-0025`（M8 范围）/ `ADR-0026`（动态链接）、`ISS-250`（`libc-test` 5 例 `_l` 偏 1.5–10 ulp）、`INFRA-079t`（compiler-rt builtins 全量）、`spec/DADAO-21`（`§2.1` 基本类型表 / `§3.2.1` 参数寄存器 / `§3.2.2` 标量参数 / `§返回值`）、`spec/Toolchain-01`（`§7.1` 数据指示符 / `§7.2` 对齐指示符）、`.tao/contracts/contract-abi.md`（`§4.1`/`§4.2`/`§4.4`/`§6.3`）

> **✅ 本文档已定案（`Accepted`，2026-10-17）**：`D1`–`D8` **已由用户逐条确认** ✓（用户原话（**逐字**，渠道 = 经主会话问答）：「**同意，与RISC-V64保持一致**」）⇒ **可作实现依据** ✓（`AGENTS.md`「ADR decision 逐条确认」；`docs/Process-03` 流程）。**本笔只改状态行 / 确认表 / 状态说明 + 少量状态注记，`D1`–`D8` 各条的决定 / 理由 / 被否正文一字未动** ✗。
> **边界（本笔）**：**未改** `spec/` ✗、**未改** `contracts/`（机器数据）✗、**未改** `.tao/contracts/**` ✗、**未改** `components/**` ✗、**未改**任何任务书 `**状态**` ✗、**未写实现代码** ✗。本 ADR **不承载规范正文**（`docs/Process-03`）：类型表 / 传参 / 返回 / 数据指示符的正文归 `spec/` 与 `contract-*.md`，本文件只记**决策 / 理由 / 被否方案 / 指向**。

## Context（背景）

### 用户裁定（原话，**逐字引录**；渠道 = 经主会话问答，2026-10-17）

> 「**long double : IEEE binary128**」

> 「**long double放M9；16字节参数和返回值问题，主流64位ISA都是怎么处理的？BTW，肯定不会用RB的两个连续槽，你又混乱了吧**」

（同日**第二条**：① 排期定向 **`M9`** ⇒ 落 `D7`；② **否决 `(b) RB 双槽`**（RB = **地址**寄存器）⇒ 落 `D2` 被否项；③ 追问「主流 64 位 ISA 怎么处理 16 B 参数/返回」 ⇒ 落 `D2` 的 psABI 对照表。）

**裁定范围（如实界定）**：第一条只裁定**格式**（`long double` = IEEE binary128）。第二条定向**排期 = `M9`**（`D7`）、否决 **`D2` 的 `(b)` 候选**；**仍未裁定**：参数/返回通道的**最终选定**（`D2`，本 ADR 只给单一推荐 `(a)`）、运算实现路径（`D3`）、常量表示（`D4`）、`spec/` 授权（`D8`）—— 这些均为待确认提案。（**2026-10-17 已逐条确认** ✓：`D2` = `(a)`、`D3`–`D8` 全部确认 —— 见 `## 逐条确认表`；上句为**起草时**状态记录，不改写 ✗。）

### 现状与缺口（逐条带依据）

1. **clang target 现状 = `long double` ≡ `double`**：`components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.h.patch:57-61` —— 注释「`long double` is absent from the spec's Fundamental Types table … keep it 64-bit (identical to `double`)」+ `LongDoubleWidth = LongDoubleAlign = 64;`；`LongDoubleFormat` 未覆写 ⇒ 取 clang `TargetInfo` 默认（IEEE double）⇒ `__SIZEOF_LONG_DOUBLE__=8`、`__LDBL_MANT_DIG__=53`。
2. **musl 侧现状 = 按 binary64 写死**：`.work/source/musl/arch/dadao/bits/float.h:1-32`（文件头注释明确「`__SIZEOF_LONG_DOUBLE__ == 8` … `long double` is identically `double`」；`LDBL_MANT_DIG 53` / `LDBL_MAX_EXP 1024` / `DECIMAL_DIG 17`）。
3. **缺口 = `ISS-250`（`open`，P2）**：`libc-test` 静态档 5 例失败（偏差 1.5–10 ulp，`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`），根因 = 本 target 精度低于 musl `_l` 的编写假设。**现状 issue 标题以「`long double` ≡ f64 vs `_l` 高精度」为口径**；本次裁定的后果见 `## 状态说明`（处置方向改为「待 binary128 实施后自然消失」）。
4. **musl `_l` 已就位 113 位分支**：`grep -rl "LDBL_MANT_DIG == 113" .work/source/musl/src/` = **53** 个文件（例：`src/math/acoshl.c:27`、`src/math/asinhl.c:35`、`src/math/lgammal.c:340`、`src/math/tgammal.c:275`）⇒ **库侧无需改写**，只需把 `bits/float.h` 常量换成 binary128。
5. **musl 已有 binary128 arch 模板**：`LDBL_MANT_DIG 113` 的 arch 共 **7** 个（`aarch64` / `loongarch64` / `mips64` / `mipsn32` / `riscv32` / `riscv64` / `s390x`）；`arch/aarch64/bits/float.h` 即完整 113 常量块（`LDBL_TRUE_MIN` … `DECIMAL_DIG 36`）⇒ 可逐字对齐，**不自造数值**。
6. **`spec/` 全文无 `long double`**：`grep -rni "long double" spec/` = **0** 行；`spec/DADAO-21-ABI-应用程序二进制接口.md:103-104` 基本类型表只有 `float`（4/4，single）/ `double`（8/8，double）两行；`:173`（`§3.2.2` 标量参数）只写「`float`，`double` … 单精和双精浮点都使用单个寄存器存放相应数据」；`:347`（`§返回值`）浮点返回「采用 `rf8`」（单寄存器口径）。
7. **数据指示符无 16 B 形式**：`spec/Toolchain-01-汇编语言.md:220-234`（`§7.1`）唯一集合 = `.dd.b08`/`.dd.w16`/`.dd.t32`/`.dd.o64`，并明文「**`.dd.128`（16 字节宽）暂不引入**」；唯一对齐指示符 = `.p2align N`（`:239`）。
8. **ABI 侧无可套用的现成通道**：`.tao/contracts/contract-abi.md §4.1` 三 bank 参数槽各 16 个（`rd16–rd31`/`rb16–rb31`/`rf16–rf31`，独立计数、不共享槽位）；`§6.3` 明文 **`i128` 传参/返回不支持**（用户 2026-10-08 裁定）⇒ binary128 **不能**套用 i128 约定（后者根本不存在）。
9. **ISA 侧存取形式齐备**：`spec/SimRISC-01-取数存数.md` 的 `ld.o`/`st.o`/`ldm.o`/`stm.o` **各有 `ra`/`rb`/`rd`/`rf` 四种形式**（如 `st.o_rrii_rb`、`stm.o_rrri_rf`）⇒ 无论 `D2` 选哪个 bank，16 B 值的装载/存储都不必先用跨 bank 搬运；`rd2rf`/`rf2rd` 块赋值亦在场（`spec/SimRISC-02-寄存器复制.md`）。
10. **栈对齐现状**：`contract-abi §2.2`（`call` 时 SP 仅 **8 B** 对齐）、`§4.3`（栈参数每槽 **8 B**、按全局声明序单栈区，`ADR-0018 C4`）；`§4.9`/`ADR-0018 C9`：DataLayout `S128`（栈对齐 16 B）已就位 ⇒ 16 B 值所需对齐**能力上可行**，但**ABI 槽位/对齐条款须新增**。
11. **LLVM 侧 `f128` 对齐默认即 16 B**：`llvm/lib/IR/DataLayout.cpp:190`（默认 `f128:128:128`）⇒ DataLayout 串**不必**新增 `f128` token；`S128` 已允许 16 B 栈对齐。clang `SuitableAlign` 现值 64（8 B），须在实施时评估是否 128（x86-64/aarch64 取 128）。
12. **compiler-rt 软浮点现成**：`compiler-rt/lib/builtins/CMakeLists.txt:217-240` 的 `GENERIC_TF_SOURCES`（`addtf3.c`/`subtf3.c`/`multf3.c`/`divtf3.c`/`extenddftf2.c`/… 一整套 `tf` 例程）；`ADR-0027 D1`/`D5` 已批 **builtins 全量 + 独立库（musl/picolibc 共用）**，落点 `INFRA-079t`（用户 2026-10-17 原话「既然要做，就做好；所以，要做，就把compiler-rt都做完」⇒ 全量范围已恢复）。
13. **无四精度硬件属主流做法**：RISC-V64 / ARM64 的 `long double` = binary128，均以 compiler-rt 软浮点实现，无专门硬件指令 ⇒ 本 ADR `D3` 与主流同向（`spec/SimRISC-07` 无 128 位浮点指令，现场 0 命中）。

### 命中 ADR 判据（`docs/Process-03`）

**高代价**（改 clang target + 后端 `f128` legalization + musl + compiler-rt 调用约定）、**跨模块 / 需一致**（spec / llvm / infra / testcases）、**多方案且需记录取舍**（`D2` 候选与被否方案、`D7` 排期）、**外部契约**（C 语义 / musl ABI / LLVM `f128`）⇒ 立本 ADR。

## Decision（决策）

> 每条含 **决定 / 理由 / 被否**。带 `⚠️ 待用户选定` 者为**尚未有裁定**的候选项，**本 ADR 不替用户选择**。（**2026-10-17 起已无待选项**：`D1`–`D8` 全部确认 ✓，见 `## 逐条确认表`。）

### D1 — 格式与尺寸：`long double` = binary128

- **决定**：`long double` = **IEEE 754-2008 binary128**，`sizeof` = **16 B**、对齐 **16 B**、`LDBL_MANT_DIG` = **113**、`LDBL_MAX_EXP` = **16384**、`DECIMAL_DIG` = **36**；目标预定义 `__SIZEOF_LONG_DOUBLE__=16` / `__LDBL_MANT_DIG__=113`（连带 `__LDBL_MAX_EXP__=16384`）。实现面 = clang `LongDoubleWidth`/`LongDoubleAlign` **64→128** + `LongDoubleFormat = IEEEquad`（`components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.h.patch:57-61` 的现状值**取代**）+ musl `arch/dadao/bits/float.h` 常量块换 binary128（连同 `LDBL_MIN_EXP` = −16381、`LDBL_DIG` = 33、`LDBL_MIN_10_EXP` = −4931、`LDBL_MAX_10_EXP` = 4932、`LDBL_TRUE_MIN`/`MIN`/`MAX`/`EPSILON`，**取 `.work/source/musl/arch/aarch64/bits/float.h` 同值、逐字一致**）。`DECIMAL_DIG` = 36（由 `1 + 113·log10 2` 向上取整独立核算）。
- **理由**：用户裁定；与 ARM64 / RISC-V64 / LoongArch64 的 musl ABI 同口径（可用同一常量块、同一 `_l` 分支）；`f128` 在 LLVM 默认 16 B 对齐（事实基线 11），与 `S128` 一致；`long double` 现状（clang 报 8 B / 53 位）是**目标事实**、不是裁定 —— 本次予以取代。
- **被否**：① **保持 `long double` ≡ `double`**（用户已裁定否；且与 Linux 主流 ABI 不一致 —— ARM64/RISC-V64 = binary128、x86-64 = 80 位；现状即 `ISS-250` 的根因）；② **80 位扩展精度**（x86 专有格式、无硬件、不可移植，且 `f80` 与 `S128`/`f128:128` 语义摩擦）；③ **「名义 16 B 但不做软浮点」**（`sizeof` 变 16 而运算精度仍 53 位 ⇒ 对外误导、契约与实现双谎，`_l` 仍错）。

### D2 — 参数与返回约定（**新 ABI 条款**）✅ **已确认 = `(a)` RF 双槽（与 RISC-V64 一致）**

- **决定（推荐案 `(a)`，仍待用户确认、本 ADR 不写成已决）**：binary128 的实参 / 返回值经 **RF bank 的偶-奇两个连续槽**传递（**低位半字在偶号槽**、**高位半字在奇号槽**）：
  - **参数**：`rf16/rf17`、`rf18/rf19`、…；**pair 必须从偶数号槽起** ⇒ `rf16` 已被单个 `float`/`double` 占用时，binary128 自 **`rf18`** 起（`rf17` 落奇号槽、不能作 pair 起点）；`rf16–rf31` 共 16 槽 ⇒ **整对计数后至多 8 个 binary128 实参**（`contract-abi §4.1` 三 bank 各自独立计数、从 16 递增）。
  - **寄存器不够 ⇒ 整个参数退栈**（**不拆半**：不允许低半字在 `rf31`、高半字在栈）；退栈值在栈上**按值占 16 B、16 B 对齐**（新增条款；`§4.3` 现为每槽 8 B、`§2.2` 仅要求 SP 8 B 对齐）。
  - **返回**：`rf8` + `rf9`（低位在 `rf8`、高位在 `rf9`；`§4.4` 返回寄存器区 `rf8–rf15`）。
  - **变参**：与具名参数同规则；`va_arg` 按偶-奇对取，`va_list` 的 RF 面偏移须**按对推进**（不得按单槽 +8）。
  - **共同前置**：大端半字顺序（高半字落低地址，见 `D4`）与 16 B 对齐须明文（`.p2align 4` / 帧槽对齐）。
  - **代价**：`rf16–rf31` 仅 16 个 64 位槽，整对计数 ⇒ 与 `float`/`double` 混用时更快耗尽；后端须新增 `f128` 成对载体 / 寄存器类（现状 RF 只有 64 位槽）；`rf0` = FCSR 不可用、`rf32–rf63` 为 callee-saved（保存面扩大）。
- **主流 64 位 ISA 的做法（一手 psABI；「内容溯源，非执行必需」）**：

| ABI | 16 B 浮点**参数** | 16 B 浮点**返回** | 依据 |
| --- | --- | --- | --- |
| **x86-64 System V** | **内存 / 栈**（分类 `X87`/`X87UP` ⇒ "passed in memory"） | **`%st0`** | x86-64 psABI `§3.2.3`；根因 = **x87 只有 80 位且为栈式** ⇒ 无 128 位寄存器可承载 |
| **AArch64 AAPCS64** | **单个 128 位 SIMD/FP 寄存器**（`q0`–`q7` 参数区） | **`q0`** | AAPCS64 参数 / 返回值规则（128 位浮点标量落**单**寄存器；单成员 HFA 走同一槽）—— 因 ARM64 **有 128 位 SIMD/FP 寄存器** |
| **RISC-V LP64D** | **`fa0`/`fa1` 偶-奇配对**，**低位在偶号槽** | **`fa0` + `fa1`** | RISC-V psABI（FLEN=64 下 128 位浮点按寄存器对传递 / 返回） |
| （MIPS64 / PPC64） | 同为 **FP 寄存器对** | 同 | 同族做法，**未逐条复核**（不作依据 ✗） |

- **我们的结论 = `(a)`（依据 = 与 RISC-V LP64D 同构）**：RF **全 64 位**（`contract-abi §1.4`：`rf0–rf63`；参数 `§4.1` `rf16–rf31`、返回 `§4.4` `rf8–rf15`）⇒ 本 target **无 128 位寄存器**（不同于 AArch64 的 `q`）、**也非 x87 栈式** ⇒ 通道只能在「**偶-奇寄存器对**」（主）与「**栈**」（仅在寄存器耗尽时兜底）之间取，**单寄存器承载不成立**。与 spec「浮点参数/返回走 RF」同向（`spec/DADAO-21:173` / `:347`），且 `ld.o`/`st.o`/`ldm.o`/`stm.o` 均有 RF 形式可直存（`spec/SimRISC-01`）⇒ 溢出路径零跨 bank 搬运。
- **被否**：
  - **(b) RB 双槽** —— **RB 是地址寄存器**（`ADR-0018 C14 D5`：RB **仅用于基址 / 绝对地址**）⇒ **不是传输 16 B 浮点值的通道**；且 `contract-abi §6.3` 明文 **`i128` 传参 / 返回不支持** ⇒ 连「整数 128 位值走两个 RB 槽」的既有约定都不存在。**`long double`（浮点）与 `__int128`（整数）不可混同**（用户原话：「肯定不会用RB的两个连续槽，你又混乱了吧」）。
  - **(c) 栈 / 内存（按值 16 B）** —— 能做但**最差**：每值 ≥2 条 64 位 `st`/`ld`、返回值须 `sret` 式隐藏指针、与 spec「浮点走 RF」口径最远、且须新增「16 B 槽 / 16 B 对齐」条款 ⇒ **仅作兜底**（寄存器耗尽时）。
  - **(d) 与 `double` 同（只传前 64 位）** —— **不可接受**（违背 `D1`）。
  - 另（沿用前稿被否）：**让实现自行决定**（不同版本/库会漂移 ⇒ 静默不互操作）；**把 binary128 当两个独立 64 位参数**（违反 C 语义、`va_arg` 断裂）。
- **理由**：各通道的代价结构不同（bank 语义 / 槽位预算 vs 内存往返 vs 条款量），且都**改变 ABI 可观测事实**（调用方/被调方必须一致），属用户裁定面；`ADR-0018` 的银行规则未含任何 128 位标量，不能由既有条款导出。

### D3 — 运算实现：compiler-rt 软浮点，不新增硬件

- **决定**：binary128 的**加/减/乘/除/比较/转换全部**走 **compiler-rt 软浮点**：`__addtf3`/`__subtf3`/`__multf3`/`__divtf3`、`__extenddftf2`/`__trunctf2`、比较 `__eqtf2`/`__netf2`/`__lttf2`/`__letf2`/`__gttf2`/`__getf2`/`__unordtf2`、整数↔binary128 转换（`__floatunditf`/`__floatditf`/`__fixtfsi`/`__fixunstfdi` …）；**并入已批准的 `INFRA-079t` 全量**（`ADR-0027 D1`/`D5`，用户 2026-10-17「把compiler-rt都做完」）；**不新增硬件**（`spec/SimRISC-07-浮点运算.md` 现无 128 位浮点指令）。后端做法 = 把 `f128` 运算 Lower 成 libcall，装载/存储/传参仍为 2×64 位。
- **理由**：`GENERIC_TF_SOURCES` 现成（事实基线 12）；RISC-V64/ARM64 同样无四精度硬件、同样靠 compiler-rt ⇒ 有成熟 oracle（上游 `compiler-rt/test/builtins`）；与 `ADR-0027 D5`「独立库、musl/picolibc 共用」天然一致。
- **被否**：① **新增四精度硬件指令**（成本极高、无先例、`SPEC-141t` 候选清单未含）；② **自写 soft-float**（重复 compiler-rt、失去上游 oracle 与维护面）；③ **只经 `double` 中转**（精度不达标 —— 即现状 `ISS-250`）。

### D4 — 常量与数据表示

- **决定**：16 B 字面量 / 常量池 = **两条 `.dd.o64`**（大端：**高半字在前**、落更低地址），对齐用 **`.p2align 4`**；**不引入 `.dd.128`**（`spec/Toolchain-01:234` 明文「暂不引入」）。与现有 `.rodata`/`.data` 装载路径一致（2 条 64 位 store 或 `stm.o`/`ldm.o` 的 `immu6=2`）。
- **理由**：数据指示符唯一集合不含 16 B 形式，新增须改 spec + MC + 生成器，收益为零；大端下「高半字在前」与 IEEE binary128 的 128 位内存序一致（`DADAO-21 §数据表示` 高位字节在低地址）。
- **被否**：① **新增 `.dd.128`**（须改 spec / MC / 生成器 / 向量，纯粹为省一行）；② **两条 `.dd.o64` 但低半字在前**（大端下与 128 位值顺序相反 ⇒ 静默错值，且无门控可自动发现）；③ **常量一律运行期拼装**（每次求值 2 条以上指令，且失去只读常量池）。

### D5 — 运行库与 libm（musl）

- **决定**：musl 侧只改 **`arch/dadao/bits/float.h` 常量块**（换 binary128，见 `D1`），**不改 `_l` 源码**；musl 的 `_l` 实现已有 `LDBL_MANT_DIG == 113` 分支（事实基线 4）⇒ 预期**自然转正**，`ISS-250` 的 5 例（`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`）应随之消失。验收 = 这 5 例通过 + musl `_l` 面整体不回归（不新增 `known-fail`/`excluded`）。
- **理由**：上游已按 113 位实现，改自身实现等于与 musl 分叉、并丢掉上游作为 oracle；7 个 arch 已有同型常量块可逐字对齐（事实基线 5）。
- **被否**：① **修 `_l` 按 binary64 语义收敛**（与用户裁定方向相反，且使 musl 与上游分叉）；② **按 binary128 重写 `_l`**（重复上游工作、失去对照）。

### D6 — QEMU

- **决定**：QEMU **译码 / 执行零改动**（无新指令；软浮点在库侧）；只须在集成测试覆盖 **16 B 值的装载/存储/传参路径**（2×64 位序列，含大端半字顺序）。若 `D2` 选 (c)（栈传参），同样**无 QEMU 改动**。
- **理由**：本 ADR 不改 ISA、不改编码；`qemu-system-dadao`/`qemu-dadao` 执行的都是既有 64 位指令。
- **被否**：① **在 QEMU 内实现四精度软浮点**（职责错位：QEMU 执行指令，四精度属 libc/compiler-rt）；② **为 binary128 新增指令**（同 `D3` 被否 ①）。

### D7 — 落地顺序与排期（**用户已定向 = `M9`**）

- **决定**：**单一方案**——`long double` = binary128 的落地排在 **`M9`**（原「(甲)/(乙)」两案**已废**）。`M8` 判据**剔除** `ISS-250` 的 5 例（转「由 `M9` binary128 覆盖」登记、不计入 `M8`）；binary128 落 `M9`（`INFRA-079t` 已批 builtins 全量 + 新立 clang target / 后端 `f128` / musl `float.h` 面任务）。**本笔已在 `milestones.md` 记注**（`M8` 快照 + `M9` 规划段）。
- **用户原话（逐字；渠道 = 经主会话问答，2026-10-17）**：「**long double放M9；16字节参数和返回值问题，主流64位ISA都是怎么处理的？BTW，肯定不会用RB的两个连续槽，你又混乱了吧**」
- **细则仍待确认（不写成已决）**：`M9` 内部顺序（与 `ror`/`rori`、TLS 的先后）、任务拆分粒度、`D2` 定案。
- **理由**：`M8` 主题 = 无内核 Linux 用户态栈；`5/367` 精度面不阻断该主题，而 binary128 波及 clang + 后端 + builtins + musl，是跨模块大活（`D3` 的 builtins 全量本身已在 `M8` 队列内，但 `f128` 通道与 `_l` 转正可后置）。
- **被否**：① **前移到 `M8` 收尾之前**（用户已定向 `M9`）；② **既不排 `M9` 也不计入 `M8`**（无归属 ⇒ 5 例长期红、且口径无人负责）；③ **在 `M8` 内把这 5 例直接归 `known-fail` 就算完成**（掩盖根因，与用户裁定方向相反）。

### D8 — `spec/` 授权与现场核对（**只读核对，不改册**）

- **决定**：本 ADR **不改 `spec/`**。实施时改册（`DADAO-21 §2.1` 增 `long double` 行、`§3.2.2`/`§返回值` 增 16 B 口径；`Toolchain-01 §7.1` 若需 16 B 指示符另议）**必须先取得用户原话授权**（`docs/Process-06`；`check-spec-readonly` 册锁 `sha256`）。
- **只读核对结果（现场原文 + 行号）**：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md:103-104`：`| Floating-point | float | 4 | 4 | single(IEEE-754) |` / `| | double | 8 | 8 | double(IEEE-754) |` —— **表内无 `long double` 行**。
  - 同文件 `:173`（`§3.2.2` 标量参数）原文：「参数类型为float，double，属于浮点型，参数传递时使用浮点寄存器，单精和双精浮点都使用单个寄存器存放相应数据」—— 只覆盖 **32/64 位单寄存器**。
  - 同文件 `:347`（`§返回值`）：「当返回值为浮点数时，采用rf8作为返回值寄存器」——**单寄存器**口径。
  - `spec/Toolchain-01-汇编语言.md:234`：「**`.dd.128`（16 字节宽）暂不引入**」（`:220-232` 为数据指示符唯一集合）。
  - `grep -rni "long double" spec/` = **0** 行（`spec/` 全文未出现该类型）。
- **理由**：`spec/` 现状对 `long double` **没有任何明文**（既非「=double」也非「binary128」）⇒ 本次裁定不产生 spec 正文冲突，但也**不能**由现有正文导出；`§3.2.2`/`§返回值` 的「单寄存器」句直接排除 16 B 值 ⇒ 一旦实施必须改册。
- **被否**：① **在 ADR 内写死规范正文**（`docs/Process-03`「ADR 不承载规范正文」）；② **未授权先改 `spec/`**（`docs/Process-06` + 门控）；③ **把「`spec/` 没写」当成「已默认 = binary128」**（无依据的推定）。

## Rationale（总述）

- **一致性**：`D1`/`D5` 让 clang 预定义与 musl 常量、`_l` 实现三者同口径（113 位），这是 `ISS-250` 消失的唯一路径；`D3`/`D4`/`D6` 让四精度只存在于**库**与**数据布局**，不污染 ISA。
- **最小代价**：不改 ISA（零 QEMU 改动、零编码/向量改动）、不改 DataLayout token（`f128` 默认 16 B 对齐）、不新增数据指示符；主要新工作量集中在 `D2`（ABI 条款）与后端 `f128` legalization。
- **可验证性**：或 oracle = compiler-rt 上游 `test/builtins` + musl 上游 `_l` 分支 + `libc-test` 语料自带期望；端序/半字顺序须有大端专门用例（`ADR-0027 D4` 同源要求）。

## Consequences（影响）

- **clang**：`clang/lib/Basic/Targets/DADAO.h`（`LongDoubleWidth`/`Align`/`Format`）；核对 `SuitableAlign`（现 64）是否随 16 B 标量调至 128；验收断言 `clang -dM -E --target=dadao-unknown-elf` 得 `__SIZEOF_LONG_DOUBLE__=16` / `__LDBL_MANT_DIG__=113` / `__LDBL_MAX_EXP__=16384`。
- **LLVM 后端**：`f128` 合法类型与 libcall lowering（`D3`）；2×64 位 load/store（`D4`）；调用约定按 `D2` 选定实现（CC/ISel）；`DataLayout` 串**不改**（`f128` 默认 `128:128`），若实测不符再议。
- **compiler-rt**：`GENERIC_TF_SOURCES` 全量入 `INFRA-079t`（`D3`）；独立库（`ADR-0027 D5`）供 musl/picolibc；driver 接线（`-print-libgcc-file-name` 落点）随该任务。
- **musl**：`arch/dadao/bits/float.h` 常量块（`D5`）；`_l` 源码不动；`ISS-250` 5 例。
- **契约**：`contract-abi` / `contract-fp` 须增 `long double` 口径（`D1`/`D2`），按 `docs/Process-02` 落笔。⚠️ **时序约束**：`check-spec-drift` 要求 contract 内引用的 `adr-XXXX-*.md` 状态为 `Accepted` ⇒ **`ADR-0030` 仍为 `Proposed` 期间，契约正文不得引用本 ADR**（否则 L1 红）；契约更新应在逐条确认之后。（**2026-10-17 起本 ADR 已 `Accepted` ⇒ 契约正文可引用本 ADR** ✓；契约更新归实施任务，本 ADR **不改契约** ✗。）
- **测试**：`libc-test` 5 例 + 大端半字顺序（双向可判别）+ 传参通道（`D2` 选定案）+ 边界值（`LDBL_MAX`/`LDBL_MIN`/subnormal/`NaN`/`±0`）+ 转换（int↔binary128、binary128↔binary64）；oracle 独立派生（不从 LLVM/QEMU 反推）。
- **性能**：四精度运算每次 libcall（软浮点固有），仅在用户显式使用 `long double` 时付出；`long double` 对齐 16 B 会略增相关聚合/帧的填充。
- **跨模块**：`llvm`（target/后端）+ `infra`（musl）+ `llvm`/`infra`（compiler-rt builtins）+ `testcases`（语料/向量）⇒ 实施须拆册串行（同改共享文件者不得并行）。

## 指向的规范章节（汇总）

- `spec/DADAO-21-ABI-应用程序二进制接口.md`：`§2.1` 基本类型表（`:103-104`，现无 `long double`）、`§3.2.1` 参数寄存器（`:150-157`）、`§3.2.2` 标量参数（`:173`）、`§返回值`（`:347`）；`§The Stack Frame`（栈布局）。
- `spec/Toolchain-01-汇编语言.md`：`§7.1` 数据指示符（`:220-234`）、`§7.2` 对齐指示符（`:239`）。
- `spec/SimRISC-01-取数存数.md`（`ld.o`/`st.o`/`ldm.o`/`stm.o` 的 `rb`/`rf` 形式）、`spec/SimRISC-02-寄存器复制.md`（`rb2rd`/`rd2rb`/`rd2rf`/`rf2rd`）。
- `.tao/contracts/contract-abi.md`：`§4.1`（参数寄存器，各 bank 16 槽）、`§4.2`（标量提升）、`§4.3`（栈溢出区，8 B/槽）、`§4.4`（返回值）、`§6.3`（`i128` 不支持）。
- `.tao/contracts/contract-fp.md`（浮点口径；现无 `long double` 条目）。
- `ADR-0018`（`C4`/`C5`/`C9`/`C14`）、`ADR-0027`（`D1`/`D5`）。

## 逐条确认表（`D1`–`D8`）

**确认日期** = 2026-10-17；**渠道** = 经主会话问答。**用户原话（逐字引录）**：

> 「**同意，与RISC-V64保持一致**」

（上下文：主会话把 `D1`–`D8` 逐条列出请其确认；`D2` = RF 双槽〔偶-奇、低位在偶号槽〕、返回 `rf8` + `rf9`、不够整值退栈 —— 即 **RISC-V64 同款**。）

| 条 | 内容 | 确认状态 |
| --- | --- | --- |
| `D1` | 格式与尺寸 = binary128（16 B / align 16 / 113 / 16384 / 36） | 已确认 ✓ |
| `D2` | 参数与返回通道：**`(a)` RF 双槽**（偶-奇对、低位在偶号槽、不足整退栈；返回 `rf8` + `rf9`）；被否 `(b)` RB 双槽 / `(c)` 栈（仅兜底）/ `(d)` 只传前 64 位 —— **与 RISC-V64 一致**（`fa0`+`fa1` 偶-奇对、低位在偶号槽、返回 `fa0`+`fa1`） | **已确认 `(a)` ✓（与 RISC-V64 一致）** |
| `D3` | 运算 = compiler-rt 软浮点，并入 `INFRA-079t`，不新增硬件 | 已确认 ✓ |
| `D4` | 常量 = `.dd.o64` ×2（高半字在前）+ `.p2align 4`，不引入 `.dd.128` | 已确认 ✓ |
| `D5` | musl 只改 `bits/float.h`，`_l` 自然转正，`ISS-250` 5 例消失 | 已确认 ✓ |
| `D6` | QEMU 零改动，仅覆盖 16 B 值装载/存储/传参路径 | 已确认 ✓ |
| `D7` | 排期：**单一 `M9`**（用户 2026-10-17 定向；甲/乙两案已废） | 已确认 ✓ |
| `D8` | 本 ADR 不改 `spec/`；实施改册须用户原话授权（现场原文/行号已录） | 已确认 ✓ |

- **`D1`–`D8` 全部确认** ✓（逐行见上表；无一条待确认）。`D2` 的确认解读 = 推荐案 `(a)` **RF 双槽**被采纳，且与 **RISC-V64**（`fa0`/`fa1` 偶-奇配对、低位在偶号槽）**同款**；`(b)` RB 双槽仍为被否项（RB = 地址寄存器）。

## 状态说明

**当前状态 = `Accepted`（2026-10-17 定案）**：`D1`–`D8` **逐条确认完毕** ✓（确认表 + 用户原话逐字见 `## 逐条确认表`）⇒ **可作实现依据** ✓；**规范正文仍不在本 ADR** ✗，落地归 `M9` 实施任务（本 ADR **不建任务、不实现** ✗）。

- **读法（定案笔）**：`D2` 决定正文（`:55`）与 `D7` 细则行（`:107`）中仍留起草笔的「待用户确认 / 不写成已决」措辞 —— **未改写** ✗（`AGENTS.md` 禁改已定 decision 正文）；**以 `## 逐条确认表` 为准**：`D2` = `(a)` **已确认** ✓、`D7` = `M9` **已确认** ✓；`M9` 内部顺序 / 任务拆分粒度属**实施细节**，由 `M9` 立册时定（非本 ADR 的 decision）。
- **2026-10-17 起草（`Proposed`）**：本文件为**提案**。用户仅裁定**主张**「`long double` : IEEE binary128」（原话逐字见 `## Context`）；`D1`–`D8` **均为提案**，未经逐条确认前不得视为 `Accepted`（`AGENTS.md`「ADR decision 逐条确认」）。**（历史记录；已于同日逐条确认 ⇒ 现 `Accepted`。）**
- **2026-10-17 修订（`D2`/`D7`；本笔）**：`D2` 由「三候选并列」改为「**单一推荐 `(a)` RF 双槽 + 两个被否（`(b)` RB 双槽 / `(c)` 栈，`(c)` 仅兜底）+ `(d)` 不可接受**」，并补**主流 64 位 ISA 的 psABI 对照表**；**`(b)` RB 双槽的立论错误已更正** = RB 是**地址**寄存器（`ADR-0018 C14 D5`），不是承载 16 B 浮点值的通道（`long double` 浮点 ≠ `__int128` 整数，不可混同）。`D7` 由「(甲)/(乙) 两案」改为**单一 `M9`**（引用户原话）。**其余 decision 未动**；`spec/` / `contracts/` 零改动；状态仍 `Proposed`。**（历史记录；当时状态已随后续定案笔改变。）**
- **转 `Accepted` 的条件**（**2026-10-17 条件已满足 ✓**）：`D1`–`D8` 逐条确认（其中 `D2` 须确认推荐 `(a)` 或改选；`D7` 已定向 `M9`、**细则**待确认）⇒ 本笔按用户确认（原话「**同意，与RISC-V64保持一致**」）改状态行为 `Accepted`；执行任务按确认结果另立（本 ADR **不建任务、不实现** ✗）。
- **与既有载体的一致性**：`ISS-250` **保持 `open`**（`status` 不改），仅追加「用户 2026-10-17 裁定 `long double` = IEEE binary128 ⇒ 处置方向改为『待 binary128 实施后自然消失』；**归 ADR（`ADR-0030`）**」〔**2026-10-17 追加**：`ADR-0030` 已 `Accepted` ⇒ 处置 = `M9` 实施 binary128，本 issue 待 `M9` 实现后复核关闭〕；`milestones.md` 的 `M8`/`M9` 注记为**方向记录**，口径真源 = 本 ADR（`Accepted`）+ 契约（实施时）。
- **历史口径**：`milestones.md` M8 快照第 5 条「`long double` ≡ `binary64`」是**当时现状记录**，本 ADR 不改写该历史表述，只在 `M8`/`M9` 段**追加**裁定与归属。
