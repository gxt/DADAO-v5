# ADR-0019: DADAO M4 重定位类型（RELA）

**状态**：Accepted
**日期**：2026-10-05
**关联**：`ADR-0003`（Object ABI / artifact pipeline）、`contract-elf.md §2–§4`（重定位，原 `Deferred`）、`.tao/knowledge/milestones.md`（M4 = ELF 文件支持 + LLD 链接）、`DADAO-0628`（只读参考，`components/llvm/patches/0014/0015/0025`）、`LLVM-041t`（M3 最小重定位：段内 PCRel 就地解析）

> **提醒**：本 ADR 只记**决策/理由/被否方案**；重定位的**规范正文**（编号/公式的表）归 `contract-elf.md §2–§4`，由后续 spec 任务落笔。

## Context（背景）

- M3 为**单 TU 自包含**：段内标签由汇编器**就地解析**（`LLVM-041t` 的 `evaluateFixup`），**不产生重定位**；`contract-elf §2–§4` 的「重定位类型/溢出/松弛」一直是 `Deferred`。
- M4 引入 **LLD + 完整 ELF**（多 TU、跨 section、外部符号），**必须**冻结 relocation 类型（编号/公式/溢出/松弛）。
- 约束（`contract-elf §2`）：须在 **`e_flags[7:0] = 1`** 的 namespace 内独立编号，**不得沿用** legacy `Dadao.def` 的编号/公式。
- 硬事实：**v5 的 `rb0` 读出为当前指令地址（非 PC+4）**（`SimRISC-00 §基址寄存器`）⇒ 相对类公式**无 `-4`**（与 0628 的 `(val-4)>>2` 不同）。地址构造指令为 `set.zw`/`or.w`/`andn.w`（`rwii`：`immu16` + `wyde-position wp0–wp3`）。DADAO 有效虚拟地址 = **48 位**。
- 参考：`DADAO-0628` 采用 **RELA**，集 = `R_DADAO_32/CALL24/BRANCH18/BRANCH12/RELA_PAGE/RELA_LO/ABS64`；公式含 `-4`（其 PC 约定与 v5 不同）。

## Decision（决策）

**D1 — ELF 记录类型 = RELA（显式 addend）**
采用 `SHT_RELA`（`.rela.*`，`r_addend` 显式）。否决 REL（隐式 addend）。

**D2 — 重定位类型集**（在 `e_flags[7:0]=1` namespace 内编号；不复用 legacy）：

| 编号 | 名 | 场景 | 编码字段 |
|---|---|---|---|
| 0 | `R_DADAO_ABS48` | **绝对 48 位地址**：`set.zw`/`or.w` 序列（≤3 片 wyde）**或数据字段（8 字节）** | 3×`immu16`（按 wyde-position）**或 8 字节数据字段** |
| 1 | `R_DADAO_REL26` | `call` / `jump`（iiii） | imms24（有效 26 位） |
| 2 | `R_DADAO_REL20` | `br.n/nn/z/nz/p/np`（riii） | imms18（有效 20 位） |
| 3 | `R_DADAO_REL14` | `br.eq` / `br.ne`（rrii） | imms12（有效 14 位） |
| 4 | `R_DADAO_NUM` | 计数 | — |

**D3 — 公式**（v5 **无 `-4`**；`S`=符号值、`A`=addend、`P`=重定位处地址）
- `REL26/REL20/REL14`：`field = (S + A − P) >> 2`（字偏移）。
- `ABS48`：`value = S + A`（48 位）；**指令**按 wyde-position 分片写入 3×`immu16`，**数据**写入 8 字节字段（绝对地址，**不区分指令与数据**）。

**D4 — `ABS48` 片数与发射策略**：DADAO 地址空间 **48 位** ⇒ **指令**发射 **3 片** wyde（**一律固定 max 3 片**，禁用 relaxation，见 D7）；**数据**为 **8 字节字段**（单条 reloc）。

**D5 — reloc 挂载粒度**：**指令**逐条挂 reloc（Q1-(b)），linker 依**指令内 wyde-position（`wp`）**判定分片；**数据**为**单条 8 字节字段 reloc**。

**D6 — 溢出策略**：越界 ⇒ **link-time error**（不截断、不 wrap）。

**D7 — relaxation**：**本期禁用**（不缩短序列）。`RELA_PAGE`/`RELA_LO`（基址 `rb0`/数据段相对寻址）**留后**，本期不实现。

**D8 — 不做 `ABS32`**：无 32-bit 数据/指针场景。

**D9 — 未定义弱符号（PC 相对分支/call）**
**未定义弱**符号的 PC 相对分支/call 重定位（`R_DADAO_REL26` / `R_DADAO_REL20` / `R_DADAO_REL14`）**不**按 `D6` 报越界，而**解析为「本位自循环」**——重定位结果取该重定位处自身（目标 = `P + A`，指令自跳自身）；其中 `R_DADAO_REL26` 的落点为 `call-iiii`（`0x74`）时**改写为 `jump-iiii`（`0x70`）**（`call` 会压入 RegRAS 返回地址、而永不存在的 callee 无人弹出 ⇒ 外层 `ret` 弹出陈旧条目、破坏返回链），落点为 `jump-iiii`（`0x70`）时保持 `jump`。**边界（不放宽）**：未定义**强**符号仍按未定义符号报错；已定义但**远距**（越界）的强符号仍按 `D6` 报 link-time error。**`--noinhibit-exec`**：该 flag 下 LLD 本就把未定义符号降为 warning，未定义**强**符号随本决策**同族**处理（落自循环）——该 flag 自身口径未改。**暂不纳入**：`R_DADAO_REL12`（PC 相对**访存**）的未定义弱情形**不**适用本决策，保持 `D6` 严格报错。**边界（防御分支）**：`R_DADAO_REL26` 落点指令**既非 `call-iiii`（`0x74`）也非 `jump-iiii`（`0x70`）**时 ⇒ **link-time error（显式报错）**——**不放行、不自循环**。**理由**：该落点组合不在本决策语义覆盖内（"自循环"仅对分支/call 有意义）；显式失败优于静默产出错误控制流；本批 **0 例**暴露。**被否**：(a) 一律按自循环处理（对非分支落点语义无意义）；(b) 静默放行（不可接受）。**规范正文**归 `contract-elf.md §3.3`（本 ADR 不含正文，`docs/Process-03`）。[出处：`LLVM-085t`（实现依据，`已验证`）；`contract-elf.md §3.2`/`§3.3`；`spec/SimRISC-06`（控制流：`call`/`jump`/`br.*`；内容溯源，非执行依赖）]

**D10 — 动态重定位类型集与最终编号（就地追加；含 `D2` 编号的就地修订注记）**
**（a）编号表（最终，全密无空档）**——在既有 `e_flags[7:0] = 1` namespace 内重排为：

| 编号 | 名 | 场景 | 备注 |
|---|---|---|---|
| 0 | `R_DADAO_NONE` | **no-op**（占位，**不参与动态段语义**） | musl `ldso` 已 `REL_NONE → continue`（加载期跳过） |
| 1 | `R_DADAO_REL26` | 同 `D2` | 不变 |
| 2 | `R_DADAO_REL20` | 同 `D2` | 不变 |
| 3 | `R_DADAO_REL14` | 同 `D2` | 不变 |
| 4 | `R_DADAO_REL12` | 同 `D2` / `ADR-0021` | 不变 |
| 5 | `R_DADAO_ABS12` | 同 `D2` / `ADR-0021` | 不变 |
| 6 | `R_DADAO_ABS48` | **数据 / GOT 槽**（8 字节字段）**或**地址构造 3 片 wyde | **由 `0` 改为 `6`（改号）** |
| 7 | `R_DADAO_JUMP_SLOT` | PLT 的 GOT 槽（8 字节字段） | 新增（动态） |
| 8 | `R_DADAO_RELATIVE` | 相对重定位（8 字节字段） | 新增（动态） |
| 9 | `R_DADAO_COPY` | 运行期副本（`memcpy(副本, S, st_size)`） | 新增（动态）；**不发射**——lld 遇即报错 |
| 10 | `R_DADAO_TLS_DTPMOD` | 模块 TLS id（8 字节槽） | 新增（TLS） |
| 11 | `R_DADAO_TLS_DTPREL` | 模块内偏置 | 新增（TLS） |
| 12 | `R_DADAO_TLS_TPREL` | TP 相对偏置 | 新增（TLS） |
| 13 | `R_DADAO_TLSDESC` | TLS 描述符（**两格**） | 新增（TLS）；**不发射** |
| 14 | `R_DADAO_NUM` | 类型计数（非实际重定位） | **冻结值 = 14** |

**就地修订注记（`D2`）**：本表把 `D2` 的 `ABS48 = 0` 改为 `ABS48 = 6`、`R_DADAO_NUM` 由 `4` 顺延为 `14`，并**引入** `R_DADAO_NONE = 0`；`D2` 的 `REL26 = 1` … `ABS12 = 5` **不变**。此为对已 `Accepted` 的 `D2` 的**就地修订**（用户 2026-10-14 逐条确认）——**不改写 `D1`/`D2` 历史文字**，以免篡改历史结论。**用户原话**：「增加 `R_DADAO_NONE`，编号 0，`R_DADAO_ABS48` 改为 6」。

**（b）值类规则**：**偏移类**（`REL26`/`REL20`/`REL14`/`REL12`/`TLS_DTPREL`/`TLS_TPREL`）⇒ **补码（有符号）加法**，名**不带位宽后缀**；**基址 / 绝对地址类**（`ABS48`/`JUMP_SLOT`/`RELATIVE` 的 `S`/`B` 及其结果）⇒ **无符号 48 位**，名**带 `48` 后缀**。

**（c）公式**（`S`/`A`/`P`/`B` 定义同 `D3`；`DTPOFF`/`TPOFF`/`tls_id` 同 `contract-dynlink.md §1.4`）：
- `ABS48`（**数据 / GOT 槽**）：`value = S + A`（**无符号 48 位**，8 字节槽、高 16 位 = 0）。
- `JUMP_SLOT`：`value = S + A`（**无符号 48 位**）。
- `RELATIVE`：`value = B + A`（**无符号 48 位**）。
- `COPY`：`memcpy(副本, S, st_size)`（**不发射**；lld 遇 `COPY` ⇒ **报错**）。
- `TLS_DTPMOD`：**定义该符号的模块**的 `tls_id`（**加载器分配、≥1**，容纳于 8 字节槽）。
- `TLS_DTPREL`：`DTPOFF(sym) + A`（**补码**）。
- `TLS_TPREL`：`TPOFF(sym) + A`（**补码、可负**）。
- `TLSDESC`：**两格**——格① resolver 地址（**基址**）、格② `arg`（由 resolver 约定）；**不发射**。

**（d）影响面（改号 ⇒ 必须同步；实际代码改动属 P2）**：`ABS48` 由 `0` 改 `6` 属**改号**，须同步：**①** `llvm/…/BinaryFormat/ELFRelocs/DADAO.def`（lld / 生产者侧 `R_DADAO_*` 枚举）；**②** `contract-elf.md §2.2`（静态类型与编号表）；**③** 本 ADR 的 `D2`（已按上「就地修订注记」处置）；并**排查既有 ELF 产物 / 测试向量**中可能写死的类型字段。**`DADAO.def` 的实际重编号与产物排查 = P2 工作**（登记为 issue；**本 ADR 不改代码**）。

**（e）`NUM` 语义**：`R_DADAO_NUM` 保持「**类型计数**」语义，其**冻结值随本表定为 `14`**（= 类型总数 ⇒ 类型号必须**密集无空档**）。[出处：`contract-dynlink.md §4.3`–`§4.4`（类型集 / 编号 / 公式）、`§9` 裁定清单（裁定 1/2）；行为类口径见 `ADR-0026`]

## Rationale（理由）

- **RELA（D1）**：`ABS48` 跨 3 条 wyde 指令构造一个地址，**addend 无法「原地」表达**（分片在 3×16 位里、有歧义）；显式 addend 干净、且与全部 64 位 ISA（x86-64/AArch64/RISC-V/PPC64/s390x）及 0628 一致。
- **命名（D2）**：相对类用 **`REL`**（PPC64 风格，不用 `PC`；AArch64 用 `PREL`，二选一），位宽用**有效位宽**（`24+2=26`/`18+2=20`/`12+2=14`，与 `contract-elf §2`「有效字节范围 = 立即数位宽 + 2 位」一致）。
- **ABS48（D4）**：地址空间 48 位 ⇒ 3 片足够，不必 ABS64。
- **(b) 逐指令（D5）**：v5 的 `DADAOFixupKinds`/`applyFixup` 本就是**逐指令**机制，天然贴合；且是将来启用 relaxation 的**结构前置**。
- **一律 max 3 片（D4+D7）**：汇编期地址未知 ⇒ 只能发 max；禁用 relaxation ⇒ 片数固定、linker 只做原地补丁，**实现最简**。代价：每符号地址占 3 条指令（代码略大，本期可接受）。
- **未定义弱符号取重定位处自身（D9）**：picolibc 的**可选平台钩子**（`_user_strerror` / `gettimeofday` / `arc4random_*`）以**弱符号**声明、调用处带 `&sym == 0` 守卫 ⇒ 必须**可链接**；而 ELF 弱符号值为 0，DADAO 映像位于 `0xFC00_0000_0000`，「到 0 的距离」远超 26 位字段、任何 veneer/thunk 也无法到达地址 0 ⇒ 学 RISC-V 等相对寻址 ISA 的**同类惯例**，把目标取为**重定位处自身**（自循环）。`call` 会压 RegRAS 而按弱符号语义 callee 永不存在 ⇒ 改写为非调用的 `jump`（不压栈），避免返回链失衡。

## Consequences（影响）

- **LLVM MC/ELF**：`DADAOELFObjectWriter` 的 `HasRelocationAddend_` 由 `false` 改 **`true`**；实现 `getRelocType`（4 类）；`DADAOFixupKinds`/`MCCodeEmitter`/`AsmBackend` 发对应 fixup；`llvm/include/llvm/BinaryFormat/ELF.h` 增 `R_DADAO_*` 枚举。
- **LLD**：`lld/ELF/Arch/DADAO.cpp` 实现 4 类 `relocate`；`Target.{cpp,h}` 注册；`getRelExpr` 支持 `R_PC`/`R_ABS`。
- **spec**：`contract-elf.md §2–§4` 由 `Deferred` 转正文（**另立 spec 任务**；本 ADR 不含正文）。
- **代码膨胀**：每符号地址 3 片；未来启用 relaxation 可优化（依赖 D5 结构）。
- **不采用**：legacy `Dadao.def` 编号/公式（`contract-elf §2` 明令）。

## 被否方案（记录）

- **REL（隐式 addend）**：多 wyde 地址构造无法原地携带 addend。
- **`ABS64`**：地址空间仅 48 位；无需 64 位绝对地址（纯常量 materialize 不走 reloc）。
- **`PC*` 命名**：改 `REL*`（避免 PC 字面）。
- **本期 relaxation**：需 linker 重排 + 修 PC 偏移，复杂度高，留后。
- **`ABS32`**：无场景。
- **未定义弱（D9）**：(a) **报错不动**——阻塞上述可选平台钩子，picolibc test 无法链接；(b) **解析为 0 但不改 `call`**——`call` 照压 RegRAS、callee 不存在无人弹出 ⇒ 外层 `ret` 弹出陈旧条目、返回链失衡；(c) **前端改语义**（在 clang/汇编层改写调用点）——全局生效、且非链接期职责 ✗。

## 状态说明

`Accepted` — 用户 **2026-10-05 逐条确认**。确认记录：

- **D1** RELA（`SHT_RELA`）✅
- **D2** 类型集 ✅（`ABS48=0` / `REL26=1` / `REL20=2` / `REL14=3` / `NUM=4`；用户修订：ABS48 编号取 0）
- **D3** 公式（v5 无 −4）✅
- **D4** ABS48 ≤3 片 + 一律发射 max 3 片 ✅
- **D5** 逐指令挂 reloc（依 `wyde-position` 分片）✅
- **D6** 溢出 ⇒ link-time error ✅
- **D7** 本期禁用 relaxation；`RELA_PAGE/LO` 留后 ✅
- **D8** 不做 ABS32 ✅
- **D9** 未定义弱符号（PC 相对分支/call）⇒ **本位自循环** + `call-iiii`(0x74) → `jump-iiii`(0x70)；未定义**强** / 已定义**远距强** 不放宽；`--noinhibit-exec` 下未定义强同族；`R_DADAO_REL12` 暂不纳入 ✅（**2026-10-12 追加**）；**边界（防御分支）**：`REL26` 非 `call-iiii`/`jump-iiii` 落点 ⇒ **link-time error**（不放行、不自循环）✅（**2026-10-13 追加 ⑥**）
- **D10** 动态重定位类型集与最终编号（`NONE=0` / `ABS48` `0→6` / 新增 `7`–`13` / `NUM=14`；偏移类补码、基址·绝对类无符号 48 位）✅（**2026-10-14 追加**；含 `D2` 编号的**就地修订注记**）

> 实现前须先落 `contract-elf.md §2–§4` 正文（另立 spec 任务）；本 ADR 不含规范正文（`docs/Process-03`）。

- 2026-10-06：**D2/D3/D4/D5 就地澄清**（用户逐条确认）：`ABS48` 为**绝对 48 位地址**，**不区分指令与数据**——指令路径 = 3 片 wyde（固定 max 3）；数据路径 = 8 字节字段（单条 reloc）。依据 `LLVM-052t`（`.dd.o64 <sym>` 数据绝对地址）+ 用户裁定原话「ABS48 是绝对地址，不区分指令和数据；…REL12 可以放在 M4 之后」。
- 2026-10-12：**追加 `D9`（未定义弱符号）**（用户逐条确认）——「未定义弱符号的 PC 相对分支/call 解析为**本位自循环** + `call`→`jump` 改写（免 RegRAS 失衡）」的口径固化为决策；规范正文落 `contract-elf.md §3.3`。依据 `LLVM-085t`（实现，`已验证`）。**用户原话/选项标签**：「（C）`ADR-0019` 加 D9 + `contract-elf` 正文（推荐）」；**渠道**：经主会话问答取得（2026-10-12）。
- 2026-10-13：**`D9` 追加 ⑥ 边界（防御分支）**——用户原话「确认，照此写入（推荐）」（经主会话问答）；规范正文同步落 `contract-elf.md §3.3`。见 `SPEC-137t`、关闭 `ISS-201`。
- 2026-10-14：**追加 `D10`（动态重定位类型集与最终编号）**（用户逐条确认）——`R_DADAO_NONE = 0`（no-op）、`R_DADAO_ABS48` 由 `0` **改为 `6`**（改号）、动态类型 `7`–`13`、`R_DADAO_NUM` 冻结为 `14`；**用户原话**：「增加 `R_DADAO_NONE`，编号 0，`R_DADAO_ABS48` 改为 6」（**渠道**：经主会话问答，2026-10-14）。规范正文落 `contract-dynlink.md §4.3`–`§4.4`；行为类口径另立 `ADR-0026`。**影响面**：`DADAO.def`（lld 生产者）重编号 + `contract-elf.md §2.2` 同步 + 既有产物 / 向量排查 = **P2 工作**（登记 issue；见 `D10`(d)）。`D2` 的历史文字**不改**（修订以 `D10`「就地修订注记」承载）。
