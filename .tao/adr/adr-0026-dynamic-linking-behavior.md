# ADR-0026: 动态链接行为口径（无内核的 Linux 用户态栈）

**状态**：Accepted
**日期**：2026-10-14
**关联**：`ADR-0025`（M8 范围与 Linux 兼容路线；`D2` 无内核 / `D3` musl ldso / `D6` 顺序 / `D7` golden 对照）、`ADR-0019`（DADAO 重定位类型；本轮**就地追加 `D10`** 承载动态类型号 / 公式 / 语义）、`ADR-0021`（`ld/st` 符号偏移重定位：`R_DADAO_REL12`）、`ADR-0018`（`C6` `rbgp`/`rbtp` 保留不分配、`C7 D4` 访存形态选择）、`ADR-0003`（Object ABI；`ET_DYN`）、任务 `SPEC-139t`（动态链接 ABI 契约 → `.tao/contracts/contract-dynlink.md`）

> **本 ADR 已 `Accepted`（2026-10-14）**：`D1`–`D8` = 用户对动态链接**行为类**口径的逐条选择，经**主会话问答**取得并**逐条确认**（`AGENTS.md`「ADR decision 逐条确认」；`docs/Process-03`）。
> **ADR 不承载规范正文**（`docs/Process-03`）：本文件只记**决策 / 理由 / 被否方案**；**契约正文**归 `.tao/contracts/contract-dynlink.md`，**类型号 / 公式 / 语义**归 `ADR-0019 D10`。
> **载体分工**（来源 = `ADR-0025 Consequences` + `contract-dynlink.md §4.4` 裁定 4 = **混合 (c)**）：类型号 / 公式 / 语义 ⇒ **就地扩 `ADR-0019`（`D10`）**；行为类口径（`ld.so` 用法 / `PT_INTERP` / `DT_*` / 绑定时机 / 越界）⇒ **本 ADR**。

## Context（背景）

- M8 = 「**无内核的 Linux 用户态栈**」（`ADR-0025`）：`ld.so` 用 **musl 自带 ldso**（`ADR-0025 D3`），「内核 / 加载器侧」（auxv 注入、`PT_INTERP` 解释器装载、加载偏置分配、路径解析）由 **QEMU user-mode** 扮演（`ADR-0025 D2`/`D6`）。
- `SPEC-139t` 落 `.tao/contracts/contract-dynlink.md`（契约正文）；其中「类型号 / 公式 / 语义」与「行为类口径」的**规范正文载体**须 **architect 落地**（该契约 §4.4 裁定 4 = 混合 (c)）——本 ADR 承载后者。
- 约束：**不改** `spec/`（上游只读册）、`contracts/` 机器数据、既有组件补丁（`ADR-0025`）。
- **事实（musl `ldso` 行为）**：`ldso/dynlink.c` 已实现 `REL_NONE` 跳过（`continue`）、GNU / SysV **两套** hash、以及 `DT_RELR` / 版本段 / 延迟绑定的处理路径 ⇒ 本 ADR 只定**本项目发射 / 依赖哪些**，不新增 musl 行为。
- 命中 ADR 判据（`docs/Process-03`）：**外部依赖 / 契约**（musl ldso、ELF gABI、QEMU user-mode）、**跨模块 / 需一致**（spec / llvm / qemu / infra）、**把结论固化为约束**（行为口径须长期遵循）。

## Decision（决策）— 逐条（**用户已逐条确认，2026-10-14，经主会话问答**）

**D1 — 动态链接器 `ld.so` = musl 自带 ldso**
`PT_INTERP` 指向的程序 = **musl 自带 `ldso`**（沿用 `ADR-0025 D3`）；**不自写 loader**，实现侧**不得**以自写 loader 替代。**被否**：自写 `ld.so`（无必要的新组件、无额外收益）。

**D2 — `PT_INTERP` 字符串与构建接线**
- **`PT_INTERP` 字符串** = **`/lib/ld-musl-dadao.so.1`**——该路径为**符号链接 → `libc.so`**（主流 musl 安装做法）；写的是 **guest 视角路径**，由 **QEMU user-mode + guest root** 解析。
- **构建侧显式传** `-dynamic-linker /lib/ld-musl-dadao.so.1`（lld 无默认值）；**不改** lld 的默认值（由构建调用处显式给出，保持 lld 与上游一致）。**被否**：改 lld 默认 `-dynamic-linker`（污染上游默认、与「显式给出」重复）。

**D3 — Hash：仅 GNU hash**
**只发射 GNU hash**（`--hash-style=gnu`），**不**双发 SysV hash；musl `ldso` 两套 hash 均支持 ⇒ 只发 GNU 侧即可。**用户原话**：「只支持 GNU hash，无需提供 both」。**被否**：双发（`--hash-style=both`，冗余、无收益）。**【修订】**：本条**修订** `contract-dynlink.md §9` 早前记录的「双发」裁定（同次会话由用户重新裁定为「仅 GNU」）。

**D4 — 符号版本段 / `DT_RELR`：都不做**
- **不发射符号版本段**（不做符号版本化）；契约**留位**并写明**启用条件**（若启用，须一并定 `.gnu.version*` / `DT_VERNEED` / `DT_VERDEF` 完整约定）。
- **`DT_RELR` 默认关**（= `--pack-dyn-relocs=none`）；契约**留位**并写明**启用条件**（与 `ADR-0019 D10` 编号方案联动；启用时另定紧凑相对重定位编码）。
- **登记（已知限制）**：musl `ldso` **不支持** glibc 式**版本化符号解析**（只读 `DT_VERSYM` 用于 time64 映射）⇒ 第三方带版本段的库**以 musl 行为为准**（非 glibc 语义）。**被否**：本期纳入版本化（无场景、代价高）。

**D5 — GOT / TP 的访问口径**
- **GOT 语义**：GOT 的**模块内偏移固定**（= `DT_PLTGOT` 记的值；musl `ldso` 装载期读 `dso->got`）、**绝对地址不固定**（= **装载基址 `B`** + 模块内偏移）。
- **不固定 GOT 基址、不安排专用寄存器**：槽地址以 **`rb0`（PC）相对**定位——与 x86-64 / AArch64 / RISC-V 一致；**不采用** MIPS `$gp` / PPC `r2` 式「固定基址寄存器」做法（`rbgp` 保留不分配，`ADR-0018 C6`）。
- **访问（单指令）**：`rb0`(PC) 相对**单条访存**（`R_DADAO_REL12`，`imms12` ⇒ **±2 KiB**），偏移为**链接期常量**；**链接器保证槽的就近布局**（把 GOT 槽排布在访问点 ±2 KiB 内）。
- **超 ±2 KiB 的两段式**（不新增 ISA 指令、只加长不缩短）：由 `R_DADAO_ABS48` 序列把地址 / 偏移**算进 `rd`**，再以 **`ldm.o_rrri_rb`**（**目的 bank = `rb`**，`immu6 = 1` 当单寄存器用）**把值直接落 `rb`**；随后 **`jump rbX, rd0, 0`** 跳转。**跳转用途必须落 `rb`**——`jump-rrii` 基址**只能取 `rb`**，且**无「零 `rb`」**（`rb0` 不可作目的）⇒ 不能把值留在 `rd` 后直接跳。**用户原话**：「直接把相对偏移写进 `rdhc`，然后 `ldm {xx}, [rb0, rdhc]`，无需多一条 `rd2rb`」。**被否**：新增 ISA 指令（越权改 ISA）；以 relaxation 缩短序列（`ADR-0019 D7` 禁用）。
- **TP**：`rbtp` 的**方向与偏置**（`TLS_ABOVE_TP` / `TP_OFFSET` / `DTP_OFFSET` / `__get_tp`）归 **musl arch 宏**，**逐 arch 定值在 musl 移植任务**；契约**只记录该依赖**、不写死值。
- **icache 与绑定时机无关**：`JUMP_SLOT` 槽是**数据**（非代码）⇒ eager / lazy **均不**因绑定而需刷新 icache；只有「**写入或新映射代码**」的场景（`ifunc` resolver、`dlopen` 新映射段、JIT）才需刷新 icache。
- **【就地修订注记（2026-10-16，`ADR-0028` `D7`/`D8`；用户逐条确认）—— 原文不改 ✗，以本注记承载修订】** 本条上列「访问（单指令）」与「超 ±2 KiB 的两段式」**两条形态已修订**：
  1. **GOT 访问改 `R_DADAO_REL32`**：取 GOT 槽地址 = **`set.zw`/`or.w rdX, disp`（2 条）+ `ldm.o {rbT}, [rb0, rdX]`（1 条）= 3 条/次**（**不再**用单指令 `R_DADAO_REL12`）⇒ **取消「`.got` 必须贴访问点 ±2 KiB」的布局义务** ✓（`dispc = S − (ldm.o 地址)`，PC 相对、链接期常量；可达 **±2 GiB**）。
  2. **PLT 改内联形式**：条目 = **配对序列**（`set.zw`+`or.w`（`disp ≥ 0`）/ `set.ow`+`andn.w`（`disp < 0`））+ `ldm.o {rb4}, [rb0, rdX]` + `jump [rb4, rd0, 0]`（**3 条指令、无 8 字节数据槽、无 padding**）；`pltEntrySize` **24 → 16**、`pltDataOffset` 取消；**PLT 由链接器合成**（`writePlt` 自产编码）⇒ **自选配对、无 opcode 改写** ✓。
  3. **「超 ±2 KiB 两段式（`ABS48` 序列 + `ldm.o_rrri_rb` 落 `rb`）」已被替代** ✗（该路径在现有 ABI 下**不可实现**：链接器无可用 `rd`、ISA 无宽相对重定位类型 —— `ISS-230`）；本条「**不固定 GOT 基址 / PC 相对 / 不占 GP**」的**原则不变** ✓。
  [出处：`ADR-0028`（`Accepted`，2026-10-16）`D7`/`D8`；规范正文落 `.tao/contracts/contract-dynlink.md §3`；`ADR-0019 D11`]

**D6 — PLT 绑定时机：首版 eager（`BIND_NOW`）**
经 `DT_BIND_NOW` / `DF_BIND_NOW` 在**装载期**完成全部 PLT 绑定。**收益**：PLT / `.got.plt` **装载后即可只读** ⇒ 可做 **full `RELRO`**；且**槽内容装载后固定**（无「首次调用改写 GOT」的时序）。lazy（经 `DT_JMPREL` / `DT_PLTRELSZ` / `DT_PLTREL`）**留后续**（musl 两条都实现，本项目只钉**首版口径**）。**被否**：首版 lazy（PLT 需可写、无 full RELRO、时序更复杂）。

**D7 — 失败与越界策略（5 条）**
- **总则**：下述失败形态**只要求「必须报错、不得继续」**，**不改 musl 行为**；错误文案不作约束。
1. **48 位约束**：`S`（符号运行时地址）/ `B`（装载基址）/ 重定位**结果**若越出 **48 位**有效虚拟地址范围 ⇒ **装载期（ld.so / 加载器）报错**——**不截断、不 wrap**。
2. **未支持 / 未定义类型或结构**：遇**未支持或未定义**的重定位类型 / 结构（含某实现尚未实现的 `COPY` / `TLSDESC`，以及**未启用**的版本段 / `DT_RELR`）⇒ **显式报错，不静默**（不得静默跳过 / 静默出 0）。
3. **偏移与 TP 越界**：偏移类（`R_DADAO_TLS_DTPREL` / `R_DADAO_TLS_TPREL`）按**补码**（有符号）计算；`TP + TPOFF` 越界 ⇒ **报错**。
4. **lld 侧（链接期）**：**经 GOT 间接访问解决远处符号**（**无需 relaxation**）；`R_DADAO_REL12`（PC 相对**访存**）**直接形式**仍限 **±2 KiB** ⇒ 越界 ⇒ **链接期报错**；**relaxation 维持 `ADR-0019 D7` 禁用**。
   - **【就地修订注记（2026-10-16，`ADR-0028` `D3`/`D5`/`D8`）】** 「经 GOT 间接访问解决远处符号」的**具体通道已改**为 **`R_DADAO_REL32`**（**3 条/次**、±2 GiB），**非**本条原文隐含的「`REL12` 直接形式 / 越界即报错」单一路径；`R_DADAO_REL12`（PC 相对**访存**、`imms12`）**直接形式**仍限 **±2 KiB** ⇒ 越界 ⇒ 链接期报错（**不变** ✓）；**relaxation 维持 `ADR-0019 D7` 禁用** ✓（`ADR-0028` `D5` 维持）；`R_DADAO_REL32` 的**落点不符 / 越界** ⇒ **link-time error**（`ADR-0028` `D3`）。[出处：`ADR-0028`（`Accepted`，2026-10-16）`D3`/`D5`/`D8`；`ADR-0019 D11`]
5. **分层不互放宽**：静态越界 = link-time error（`ADR-0019 D6`）；动态越界按本条走**装载期报错**——两层**不互相放宽**。

**D8 — 来源与独立 oracle**
- **类型号 / 公式真源 = 契约**（`ADR-0019 D10` + `contract-dynlink.md`）；实现链路 = lld（`DADAO.def`）**发出** → musl（`arch/dadao/reloc.h`）**消费**，**契约 / lld / musl 三处必须一致**。
- **期望值独立派生**：从 **ELF gABI（System V ABI）** 通用语义 + **RISC-V + musl golden** 对照派生；**禁**从 v5 自身实现反推（`ADR-0025 D7`）。
- **归属**：对照 harness / 判据 / 回归门控 = **P4**（`ADR-0025 D6` 顺序之末）；本 ADR 只钉口径与禁止项。

## Rationale（理由）

- **不新增 loader（`D1`）**：与 `ADR-0025 D3`/`D4` 一致，复用 musl 生态，免自写 loader 的维护与正确性风险。
- **guest 视角 `PT_INTERP` + 显式 `-dynamic-linker`（`D2`）**：无内核下路径由 QEMU user-mode + guest root 解析（`ADR-0025 D2`）；不改 lld 默认值可保持「上游默认 = 上游行为」，本项目差异只在构建调用处。
- **仅 GNU hash（`D3`）**：musl `ldso` 两套都读 ⇒ 双发纯冗余；只发 GNU 侧更小、更快。
- **版本段 / `DT_RELR` 本期不做（`D4`）**：无场景（不版本化依赖），且 `DT_RELR` 与编号方案耦合（`ADR-0019 D10`）⇒ 留位 + 写明启用条件，避免静默约定。
- **PC 相对 + 不占用 GP（`D5`）**：`rbgp` 由 `ADR-0018 C6` 保留，x86-64/AArch64/RISC-V 均以 PC 相对 + 链接期偏移访问 GOT（`ADR-0021 D3`）；`ldm.o_rrri_rb` 路径复用既有 ISA（`ldm.o` 的 `rb` 目的形式、`immu6=1`），**只加长不缩短**、与 `ADR-0019 D7` 禁 relaxation 一致。
- **eager 绑定（`D6`）**：先得 **full RELRO**（PLT 只读）与「槽内容装载后固定」的简单性；lazy 留后续。
- **失败显式化（`D7`）**：静默跳过 / 静默出 0 会把错误推迟到运行期且不可归因；`ADR-0019` 的静态策略（`D6`、`D7`）在动态层保持同精神。
- **独立 oracle（`D8`）**：与 `ADR-0025 D7` 同口径——期望值不得来自 v5 自身实现（否则自证）。

## Consequences（影响）

- **待办（P2 / P1）**：
  1. **`DADAO.def` 重编号**（`ADR-0019 D10`：`NONE=0` / `ABS48` `0→6` / 新增 `7`–`13` / `NUM=14`）——**P2**；并**排查既有 ELF 产物 / 测试向量**中写死的类型字段（登记 issue 跟踪）。
  2. **`PT_INTERP` / `-dynamic-linker` 的构建接入**（构建显式传参 + 安装符号链接 `ld-musl-dadao.so.1 → libc.so`）——**P2**。
  3. **GOT 就近布局**（链接器保证 ±2 KiB）+ 两段式路径（`ABS48` + `ldm.o_rrri_rb`）——**P2**。**【就地修订注记（2026-10-16，`ADR-0028` `D8`）】**：本条**已修订** ✗ —— **布局义务取消**（GOT 访问改 `R_DADAO_REL32`、3 条/次）；**替代**待办 = `R_DADAO_REL32` 的 lld `relocate` + `writePlt` 重写（去槽、16 B）——归 `LLVM-094t` / `ISS-230` 的后续实现任务。[出处：`ADR-0028`（`Accepted`，2026-10-16）`D8`]
  4. **TP 宏**（`TLS_ABOVE_TP` / `TP_OFFSET` / `DTP_OFFSET` / `__get_tp`）——**P1**（musl 移植）。
- **契约同步**：`contract-dynlink.md` 的 Hash 口径（`§5`）、GOT / TP 访问口径（`§3`）、类型表编号（`§4.3`–`§4.4`）与来源标注随本 ADR 同步。
- **约束**：**不改** `spec/`（上游只读册）、`contracts/` 机器数据、组件补丁；实现阶段由后续 `t` 任务落（`ADR-0025`）。

## 风险 / 未决项

- **Hash 口径变更（`D3`）**：修订了早前「双发」记录 ⇒ 须确保 `contract-dynlink.md` 正文与 lld 调用处（`--hash-style=gnu`）一致，避免两处不一。
- **`DADAO.def` 改号（`ADR-0019 D10`）**：`ABS48` `0→6` 属**改号** ⇒ 契约 / lld / musl 三处同步前，**不要**发布依赖旧号值的产物（issue 跟踪）。
- **两段式路径（`D5`）**：GOT 就近布局与 `ldm.o_rrri_rb` 路径为**预留**，实现前需 LLVM 侧形态落地；越界仍以 `D7` 报错兜底（**非静默**）。**【就地修订注记（2026-10-16，`ADR-0028` `D5`/`D7`/`D8`）】**：本条**已修订** ✗ —— 两段式路径**已废弃**（在现有 ABI 下不可实现，`ISS-230`）⇒ 改由 **`R_DADAO_REL32`**（GOT 3 条/次、PLT 内联去槽）承载；「越界以 `D7` 报错兜底、**非静默**」的**精神不变** ✓（`REL32` 落点不符 / 越界 ⇒ link-time error）。[出处：`ADR-0028`（`Accepted`，2026-10-16）`D5`/`D7`/`D8`]

## 状态说明

**Accepted（2026-10-14）**：`D1`–`D8` = 用户逐条选择，已成立、无否决未处置。

**就地修订（2026-10-16，`ADR-0028` `D9`；用户逐条确认）**：`D5`（GOT/TP 访问口径）与 `D7`（失败与越界策略）**就地修订**——**注记承载、历史正文不改** ✗：① `D5` 的「GOT 访问（单指令 `R_DADAO_REL12`）」→ **`R_DADAO_REL32`（3 条/次）**、**取消 `.got` 贴 ±2 KiB 布局义务**；「PLT 形态」→ **内联去槽**（`pltEntrySize` **24 → 16**、`pltDataOffset` 取消、链接器合成 ⇒ 自选配对、无 opcode 改写）；「超 ±2 KiB 两段式（`ABS48` + `ldm.o_rrri_rb`）」**已废弃**（不可实现，`ISS-230`）。② `D7④` 的「经 GOT 间接访问解决远处符号」通道改 `REL32`；`REL12` 直接形式 ±2 KiB 越界报错、**禁 relaxation** 不变 ✓。修订依据 = `ADR-0028`（用户 2026-10-16 逐条确认 ⇒ `Proposed` → **`Accepted`**）；**原话**：「`REL32`，甲」/「可以」/「PLT 也改成这种方案」（**渠道** = 经主会话问答）。**边界**：`spec/` / `contracts/`（机器数据）**零改动**；实现归后续 `t` 任务（`ISS-230` 保持 `open`）。

**逐条确认记录**（2026-10-14，**经主会话问答**）：

| 项 | 用户选择（**原话 / 选项标签**） | 落为 |
|---|---|---|
| D1 | 「用 musl 自带 ldso（推荐）」（= `ADR-0025 D3`） | `D1` |
| D2 | `PT_INTERP = /lib/ld-musl-dadao.so.1`（符号链接 → `libc.so`；构建**显式传** `-dynamic-linker`） | `D2` |
| D3 | **原话**「只支持 GNU hash，无需提供 both」 | `D3` |
| D4 | 符号版本段 / `DT_RELR` **都不做** | `D4` |
| D5 | GOT 不固定基址、PC 相对；超 ±2 KiB 两段式——**原话**「直接把相对偏移写进 `rdhc`，然后 `ldm {xx}, [rb0, rdhc]`，无需多一条 `rd2rb`」 | `D5` |
| D6 | 首版 **eager（`BIND_NOW`）** | `D6` |
| D7 | 失败与越界 **5 条**（总则「必须报错、不得继续」+ **不改 musl 行为**） | `D7` |
| D8 | 类型号 / 公式真源 = 契约（契约 / lld / musl 三处一致）；期望值独立派生、**禁**自实现反推 | `D8` |

**变更流程**：决策变更时**新增 ADR 或标注 `Superseded`**；经授权的就地修订须用户逐条确认（`docs/Process-03`）。
