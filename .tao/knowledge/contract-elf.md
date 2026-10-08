# SimRISC M1 ELF 合约（Object ABI）

> **状态**：Accepted
>
> **来源**：`.tao/adr/adr-0003-object-abi.md`（ADR-0003，`SPEC-005t` 产出，Status: Accepted，rev. 2026-09-13 `e_flags`、rev. 2026-09-14 D2 登记补充、rev. 2026-10-06 M4 ELF 路径补充〔去 `FILEHDR PHDRS` / `p_align` 目标默认 64 KiB，`SPEC-112t`〕）。本合约的 M1 决策（D1 头字段 + D5 段对齐/VA=PA/artifact pipeline）是 ADR-0003 的归一化投影；**§2–§4（重定位）另有来源 `.tao/adr/adr-0019-dadao-relocation-types.md`（ADR-0019，Status: Accepted，用户 2026-10-05 逐条确认 D1–D8）与 `.tao/adr/adr-0021-ldst-symbol-reloc.md`（ADR-0021，Status: Accepted，2026-10-08 用户逐条确认 D1–D3；扩展 `ld/st` 符号偏移体系 `R_DADAO_REL12` + `R_DADAO_ABS12`，rev. 2026-10-09）**；**§5/§6 的加载/启动（ELF + raw-bin 双路径）并来源 `.tao/adr/adr-0004-test-machine.md`（ADR-0004，Status: Accepted，rev. 2026-10-06，用户逐条确认，`SPEC-107t`）§D2.2/§D2.3**。
>
> **引用**：指令格式/字段宽度/对齐/地址模型引用 `.tao/knowledge/contract-isa.md`（SimRISC 0.5.4）；端序/指针宽度引用 `.tao/knowledge/contract-abi.md`（0.9.2）。本合约不重复定义这些内容。
>
> **M1 范围**：§1 ELF 文件头字段、§5 段对齐与 VA=PA、§6 端到端 artifact pipeline（raw-bin 路径）。
>
> **M4 范围（§2–§4）**：§2 重定位类型、§3 重定位公式与溢出策略、§4 重定位松弛——由 `ADR-0019`（M4，Accepted，用户 2026-10-05 逐条确认 D1–D8）冻结为规范正文；`ld/st` 符号偏移体系 `R_DADAO_REL12`（`rb0`，PC 相对）+ `R_DADAO_ABS12`（`rb1–rb63`，基址相对）由 `ADR-0021` 扩展（Accepted，2026-10-08；rev. 2026-10-09 用户改判为双类型，逐条确认）。
>
> **M4 范围（§5/§6 加载/启动扩展，`SPEC-107t`）**：§5/§6 由 `ADR-0004`（rev. 2026-10-06，用户逐条确认）扩展为 **「ELF 路径 + 保留 raw-bin 路径」双路径**——新增 **ELF 加载**（读 `Ehdr`/`Phdr`、按 VA=PA 装载 `PT_LOAD` 段、跳 `e_entry`），**保留** raw-bin（`.o → objcopy .text → flat`、入口固定基址）。加载/启动约定归 `ADR-0004 §D2.2/§D2.3`。
>
> **来源标注**：每条规范性断言句末以 `[ADR-0003 §DN]`（§1/§5/§6）或 `[ADR-0019 §DN]`（§2–§4）标注来源决策点，§5/§6 的加载/启动路径另以 `[ADR-0004 §DN]`（或 `[ADR-0004 §修订 rev. 2026-10-06]`）标注；不写行号；引用合约时用 `contract-isa.md §N` / `contract-abi.md §N`。
>
> **说明**：本合约（§1/§5/§6）由 ADR-0003 归一化投影而来（§5/§6 的加载/启动双路径并由 ADR-0004 投影），§2–§4 由 ADR-0019 归一化投影而来，面向实现；与 ADR-0003（§1/§5/§6）、ADR-0004（§5/§6 加载/启动）或 ADR-0019（§2–§4）冲突时阻断实现，走变更流程（见 `spec/Process-02-合约编写规范.md`）。v5 `spec/` 不含 ELF 内容，D1/D5 属架构自定义（ELF 结构常量取自 ELF 标准，具体取值由 ADR-0003 决策）；遗留 `Dadao.def`/`ELF.h` 仅作只读对照，不作为编号/公式来源。[ADR-0003 §Context]

---

## §1 ELF 文件头字段

### §1.1 冻结字段

M1 ELF 使用 `Elf64_*` 结构（`Elf64_Ehdr` 等），头中与架构相关的字段冻结如下：[ADR-0003 §D1]

| 字段 | 冻结值 | 含义 |
|------|--------|------|
| `EI_CLASS` | `ELFCLASS64 = 2` | 64 位 ELF |
| `EI_DATA` | `ELFDATA2MSB = 2` | 大端 |
| `e_machine` | `EM_DADAO = 0x0DA0` | project-custom machine id |
| `e_flags` | `0x00000001` | 对象/ABI 格式版本 = 1（bits 0–7）；bits 8–31 保留为 0 |
| `EI_OSABI` | `ELFOSABI_NONE = 0` | freestanding，无 OS 专用 ABI |

### §1.2 逐字段含义与依据

- **`EI_CLASS = ELFCLASS64 (2)`**：SimRISC 每个用户寄存器 64 位、机器字长 64 位 [contract-isa.md §1.1]；存储模型为 64 位地址空间（有效虚拟地址 48 位）[contract-isa.md §1.5]。指令字为 32 位 [contract-isa.md §2.1]，但寄存器/地址模型为 64 位，故使用 `Elf64_*` 结构。[ADR-0003 §D1]
- **`EI_DATA = ELFDATA2MSB (2)`**：SimRISC 指令字与数据均为大端序，多字节数据的最高有效字节存放在最低地址 [contract-isa.md §1.6][contract-isa.md §2.1]；ABI 基础数据布局亦为大端序 [contract-abi.md §1.7]。[ADR-0003 §D1]
- **`e_machine = EM_DADAO (0x0DA0)`**：**project-custom**。该值**未注册**于 IANA/SysV 公共 ELF registry，也**不存在于 LLVM 主线**；它仅存在于遗留 DADAO toolchain fork。M1 沿用该命名以保持项目生态内 machine identity 的连续，但**不声称已注册 upstream**。未正式注册带来的碰撞风险由 `e_flags` 版本字段缓解（见 §1.3）。[ADR-0003 §D1]
- **`EI_OSABI = ELFOSABI_NONE (0)`**：M1 为 freestanding 裸机测试环境，无 OS 专用 ABI 扩展，采用通用 System V 值。[ADR-0003 §D1]

### §1.3 `e_flags` 对象/ABI 格式版本字段

`e_flags = 0x00000001`：**bits 0–7 为对象/ABI 格式版本号**（`e_flags[7:0]`），M1 取值为 **1**；后续每当对象/ABI 格式发生不兼容变化时递增。**bits 8–31 保留**，必须为 0。[ADR-0003 §D1][ADR-0003 §修订]

| 位 | 含义 |
|----|------|
| 0–7 | 对象/ABI 格式版本号（M1 = 1） |
| 8–31 | Reserved（必须为 0） |

consumer 必须按版本号与保留位决定是否接受 object：[ADR-0003 §D1][ADR-0003 §修订]

| `e_flags[7:0]` | 含义 | consumer 行为 |
|---------------|------|--------------|
| 0 | legacy DADAO object（无版本字段） | **拒绝**（非 M1） |
| 1 | M1 对象/ABI 格式 | 接受 |
| 2–255 | 未知/未来版本 | **拒绝**（consumer 无法解释） |
| 任意（bits 8–31 ≠ 0） | 违反保留位约束 | **拒绝** |

即 consumer 只接受 `e_machine = 0x0DA0` 且 `e_flags = 0x00000001`（版本 1、保留位全 0）的 object；遇到版本不匹配、未知版本或保留位非 0 一律报错。[ADR-0003 §D1][ADR-0003 §修订]

---

## §2 重定位类型

### §2.1 ELF 重定位记录类型

M4 ELF object 的重定位记录采用 **`SHT_RELA`**（`.rela.*` 段），每条记录携带**显式 `r_addend`**；否决 `SHT_REL`（隐式 addend）——`ABS48` 跨 3 条 wyde 指令构造一个地址，addend 无法就地表达。[ADR-0019 §D1]

### §2.2 类型与编号

重定位类型须在 `e_flags[7:0] = 1`（§1.3 对象/ABI 格式版本）的 **namespace 内独立编号**，**不复用** legacy `Dadao.def` 的编号/公式。[ADR-0019 §D2][ADR-0003 §D2]

| 编号 | 名 | 场景 | 编码字段 |
|------|----|------|----------|
| 0 | `R_DADAO_ABS48` | `set.zw` / `or.w` / `andn.w` 地址构造序列（≤ 3 片 wyde）**或数据绝对地址字段（8 字节）** | 3×`immu16`（按 `wyde-position` 分片）**或 8 字节字段** |
| 1 | `R_DADAO_REL26` | `call` / `jump`（iiii） | `imms24`（有效 26 位） |
| 2 | `R_DADAO_REL20` | `br.n` / `br.nn` / `br.z` / `br.nz` / `br.p` / `br.np`（riii） | `imms18`（有效 20 位） |
| 3 | `R_DADAO_REL14` | `br.eq` / `br.ne`（rrii） | `imms12`（有效 14 位） |
| 4 | `R_DADAO_REL12` | `ld.*` / `st.*`（rrii）访存符号偏移 `[rb0, sym]`（**`rb0` 基址**、PC 相对） | `imms12`（**字节**偏移、有效 12 位） |
| 5 | `R_DADAO_ABS12` | `ld.*` / `st.*`（rrii）访存符号偏移 `[rbN, sym]`（**`rb1–rb63` 基址**、基址相对） | `imms12`（**字节**偏移、有效 12 位） |
| 6 | `R_DADAO_NUM` | 类型计数（非实际重定位） | — |

相对类的**有效位宽 = 立即数位宽 + 2**（字偏移；`24+2=26` / `18+2=20` / `12+2=14`）；指令格式/字段位置见 [contract-isa.md §2.3–§2.4]，分支/call/jump 语义见 [contract-isa.md §4.7][contract-isa.md §5.2]。[ADR-0019 §D2]

`R_DADAO_REL12` / `R_DADAO_ABS12` 是上一条「+2」规则的**例外**：两者均服务访存的**字节**偏移（`ld/st` 有效地址 = 基址寄存器 + `imms12`，`imms12` 单位为**字节**、非字），故**不适用**「立即数位宽 + 2」的字偏移换算——其有效范围即 `imms12` 的**有符号 12 位**（`−2048..+2047`，约 ±2 KiB）。[ADR-0021 §D1][contract-isa.md §2.3]

`R_DADAO_REL12` / `R_DADAO_ABS12` 是 `ld/st` 符号偏移的**专用类型**（二者按基址寄存器区分，见下），**不得复用** `R_DADAO_REL20`——后者服务 `riii` 分支相对类（`imms18`、有效 20 位、字偏移），与访存的 `imms12`（字节偏移）**字段宽度与语义均不同**，复用会产出错误编码。[ADR-0021 §D2][contract-isa.md §2.3]

**两类型必须明确区分**（用户 2026-10-09 裁定）：ELF `RELA` 记录**无「基址寄存器」字段** ⇒ **由汇编器按访存基址寄存器自动选择类型**——基址为 **`rb0`** 选 `R_DADAO_REL12`，基址为 **`rb1–rb63`** 选 `R_DADAO_ABS12`。**不得**只用一个类型承载两种公式（否则 PC 相对与基址相对混淆 ⇒ 静默错值）；**linker 只看类型、不解码指令**。[ADR-0021 §D1][contract-isa.md §2.3]

### §2.3 挂载粒度与分片

reloc **逐指令**挂载（非逐段/逐符号）；多片时 linker 依**指令内的 `wyde-position`（`wp`，编码于 `hb[5:4]`）**判定该片对应地址的哪 16 位。[ADR-0019 §D5][contract-isa.md §2.4]

---

## §3 重定位公式与溢出策略

### §3.1 公式

`S` = 符号值（定义处地址）、`A` = addend（`r_addend`，显式）、`P` = 重定位处地址。[ADR-0019 §D3]

| 类型 | 公式 | 落点字段 |
|------|------|----------|
| `R_DADAO_REL26` / `R_DADAO_REL20` / `R_DADAO_REL14` | `field = (S + A − P) >> 2`（**字偏移**） | `imms24` / `imms18` / `imms12` |
| `R_DADAO_REL12` | `field = S + A − P`（**字节偏移**、`rb0` 基址、PC 相对；`P` = 该访存指令地址 = `rb0` 读出值） | `imms12` |
| `R_DADAO_ABS12` | `field = S + A`（**字节偏移**、`rb1–rb63` 基址） | `imms12` |
| `R_DADAO_ABS48` | `value = S + A`（48 位）；**指令**按 `wyde-position` 分片写入 3×`immu16`，**数据**写入 8 字节字段（**大端**、高 16 位 = 0） | 3×`immu16` / 8 字节字段 |

相对类公式为 `(S + A − P) >> 2`，即**字偏移**（`P` 为重定位处地址本身）。**v5 无 `− 4`**：不引入 `PC+4` 修正；这与 0628 的 `(val-4)>>2` 不同——v5 的 `rb0` 读出为**当前指令地址**（非下一条）[contract-isa.md §1.3.2]，故 `P` 无需再减 4。[ADR-0019 §D3]

`R_DADAO_REL12` 的符号为 **`rb0` 相对（PC 相对）**偏移：`ld/st rd, [rb0, sym]` 中 `rb0` 读出为**当前指令地址**（即 `P`，见 [contract-isa.md §1.3.2]），故 `field = S + A − P`（**字节、不 `>>2`**）。`R_DADAO_ABS12` 的符号为 **`rb1–rb63` 基址相对**偏移：`ld/st rd, [rbN, sym]` 中基址为通用基址寄存器 `rbN`（非 `rb0`），符号偏移即绝对字节量，故 `field = S + A`（**字节、不 `>>2`**）。两类型**字段宽度同为 `imms12`、公式不同**，由汇编器按基址寄存器自动选型（§2.2），**必须区分**。[ADR-0021 §D1][contract-isa.md §4.1.1][contract-isa.md §1.3.2]

**`rb0` 作访存基址的危险（规范只记危险；规避由 LLVM 定）**：`rb0` 读出为**当前指令的地址**，随取指推进而变（[contract-isa.md §1.3.2]/§8）⇒ 在**多指令形态**（`ADR-0018 §C7 D4` 形态②③④，见 §4）中以 `rb0` 为基址会发生**漂移**，取到的地址取决于该访存指令自身位置。**规范不指定、不硬性禁止**——**如何规避（先 `rb2rb` 拷出并做 ±k×4 修正、或避免以 `rb0` 作基址）由 LLVM 依实际情形决定**。[ADR-0021 §D1][ADR-0018 §C7 D4]

`R_DADAO_ABS48` 的**数据**形式（8 字节字段）：`value = S + A` 的 48 位地址按 **大端**存储，**高 16 位（`bits[63:48]`）填 0**（字段字节序为 `00 00 A5 A4 A3 A2 A1 A0`，`A5` = 地址 `bits[47:40]`）。指令形式与数据形式共享同一类型，由目标 section 是否含 `SHF_EXECINSTR` 区分。[ADR-0019 §D2][ADR-0019 §D3]

### §3.2 溢出策略

重定位结果越出目标字段可表示范围时，一律 **link-time error**（**不截断、不 wrap**）。[ADR-0019 §D6]

`R_DADAO_REL12` / `R_DADAO_ABS12` 的越界（符号偏移 `S + A − P` / `S + A` 超出 `imms12` 有符号 12 位范围，即 `−2048..+2047`）同样一律 **link-time error**——**不截断、不 wrap、不静默出 0**，且**不**另设更宽类型、**不**做汇编器序列化（超出即显式失败）。[ADR-0021 §D3][ADR-0019 §D6]

---

## §4 重定位松弛（Relaxation）

- **本期禁用 relaxation**（不缩短序列）：`R_DADAO_ABS48` **≤3 片**（DADAO 地址空间 48 位，最多 3 片）；**一律发射固定 max 3 片**，linker 只做原地补丁，不重排/不缩短。[ADR-0019 §D4][ADR-0019 §D7]
- `R_DADAO_REL12` / `R_DADAO_ABS12` 均为**单字段**就地补丁（一条访存指令的 `imms12`），**无多片、无 relaxation**；越界见 §3.2。[ADR-0021 §D3]
- **访存偏移形态由 LLVM 选择，reloc 层不越权**：大帧/大偏移访存用**哪一形态**（`ADR-0018 §C7 D4` 四形态——① `[sp, disp12]`、② `rb2rb` + `add.si`、③ `add.o tmprb, sp, tmp` + `[tmprb, disp]`、④ `ldm/stm [sp, tmp]`；rev. 2026-10-08）**由 LLVM 依实际情形选择**，规范**不指定**。reloc 层**不新增更宽类型、不做 relaxation**；`R_DADAO_REL12` / `R_DADAO_ABS12` 只服务「编译器选择**形态①**（单条访存、`imms12` 就地补丁）」的情形——其余形态按普通指令 + `R_DADAO_ABS48`/分支相对类组合构造地址，不依赖本体系。[ADR-0018 §C7 D4][ADR-0021 §D3]
- `RELA_PAGE` / `RELA_LO`（基址 `rb0` / 数据段相对寻址）**本期不实现、留后**。[ADR-0019 §D7]
- **不做 `ABS32`**：无 32-bit 数据/指针场景（地址空间为 48 位）。[ADR-0019 §D8]

---

## §5 段对齐与 VA=PA

### §5.1 段最小对齐

| 段 | 最小对齐 | 理由 |
|----|---------|------|
| `.text` | 4 字节 | 每条指令 4 字节且必须 4 字节对齐 [contract-isa.md §2.1][ADR-0003 §D5] |
| `.rodata` | 8 字节 | 64 位常量/指针的自然对齐；`ld.o`/`st.o` 要求 8 字节对齐 [contract-isa.md §4.1.1] |
| `.data` | 8 字节 | 同 `.rodata` |
| `.bss` | 8 字节 | 同 `.rodata` |

指针为 8 字节 [contract-abi.md §1.7]。[ADR-0003 §D5]

段默认布局顺序为 `.text` → `.rodata` → `.data` → `.bss`；在满足各自最小对齐的前提下允许调整顺序。[ADR-0003 §D5]

该最小对齐与默认布局顺序对 **raw-bin 段拼接**（§6.1.1）与 **M4 ELF `PT_LOAD` 段装载**（§6.1.2）**均适用**；M4 ELF 的段地址由链接脚本 `dadao.lds` 给出，须满足本表对齐。[ADR-0003 §D5][ADR-0004 §D2.2]

### §5.2 VA=PA（freestanding 无 MMU）

M1 无 MMU、无页表，加载期不做地址重定位。段的虚拟地址（VMA）等于其物理加载地址（PA）；即段被放在哪个物理地址，就以该地址作为其有效虚拟地址。有效地址为 48 位，高 16 位在地址计算时被硬件忽略 [contract-isa.md §1.5]。[ADR-0003 §D5]

VA=PA 规则同时适用于 **raw-bin 路径**（段连续拼接，§6.1.1）与 **M4 ELF 路径**（`PT_LOAD` 段按 `p_vaddr` 装载，§6.1.2）：ELF 段的加载地址即 `p_vaddr`（`VA=PA`），不另做加载期地址重定位。[ADR-0004 §D2.2]

### §5.3 `PT_LOAD` 段对齐（`p_align`）

M4 ELF 路径下 `PT_LOAD` 段的 `p_align` **目标默认 = 64 KiB**（`defaultMaxPageSize = 0x10000`；依据 DADAO 普通页 = 64 KiB，页内偏移 16 位 [DADAO-12 §2.2.2 普通页的地址转换]、`SBI_PTW_HANDLE_FAULT` 返回的页面对齐掩码 `page_mask`（如 `0xFFFFFFFFFFFF0000` = 64 KiB）[DADAO-22 §4. 地址转换（cfx_ptw）]）；**可被链接选项 `-z max-page-size` 覆写**——为**目标默认值，非硬编码不变式**。[ADR-0003 §修订 rev. 2026-10-06]

---

## §6 端到端 artifact pipeline

### §6.1 路径概览

本合约的 artifact pipeline **有两条路径并存**（`SPEC-107t` rev. 2026-10-06 起）：M1–M3 的 **raw-bin 路径**（§6.1.1）**保留不回归**，M4 起新增 **ELF 路径**（§6.1.2）。[ADR-0003 §D5][ADR-0004 §D2.2][ADR-0004 §D2.3]

#### §6.1.1 raw-bin 路径（M1–M3；保留）

M1 采用 **raw / section extraction** 路径，**不引入 target linker（LLD）**、不产生 `ET_EXEC`、不做跨 object 链接：[ADR-0003 §D5]

```
1. 汇编/编译（单 TU）                            →  ET_REL object  (.o)
2. llvm-objcopy --only-section=.text -O binary  →  flat binary（.text 段原始字节）
3. QEMU test machine 将 flat binary 加载到 RAM 基址，并从该基址进入
```

- **步骤 1——单 TU 自包含**：步骤 1 的 `.o` 为单翻译单元、自包含；段内标签由汇编器就地解析，**不产生重定位**。[ADR-0003 §D5] 术语「单 TU 自包含」指：TU（Translation Unit，翻译单元）是汇编器/编译器的单次输入单位，一个 TU 产出恰好一个 object（`.o`）；「自包含」指该单元内所有符号/标签都在本单元内定义并**就地解析**，不引用任何外部符号。自包含的直接后果是**不产生重定位**——汇编器在汇编期即可算出全部标签地址，无需留待链接期回填的占位项。[ADR-0003 §Context]
- **步骤 2——objcopy 段提取**：步骤 2 使用 `objcopy`（M1 用 `llvm-objcopy`）的**段提取**能力（`--only-section=.text` + `-O binary`），不经过静态链接；这是 M1 不依赖 LLD 的关键。M1 e2e 路径冻结提取 `.text`。[ADR-0003 §D5]
- **多段提取连续拼接**：其它可分配段（若后续 M1 用例需要）以同一机制提取，其对齐要求见 §5.1。若 M1 用例需要 `.rodata`/`.data`，则以同一 `objcopy` 机制提取并按 8B 对齐**连续拼接**为单一 flat 镜像（拼接顺序沿用 §5.1 默认布局 `.text` → `.rodata` → `.data`）。[ADR-0003 §D5]
- **步骤 3——raw-bin 路径消费 flat binary 而非 ELF**：raw-bin 路径下 QEMU 消费的是 **flat binary，不是 ELF**；`e_entry` 不被读取，入口固定为 flat binary 的加载基址。机器名、加载地址、命令行与 trampoline 由 ADR-0004（`SPEC-006t`）冻结。[ADR-0003 §D5] **不得把该 raw-bin 加载称为「ELF loader」**——raw-bin 路径不做 ELF 解析；M4 ELF 路径（§6.1.2）则**是**真正的 ELF 加载（解析 `Ehdr`/`Phdr`、跳 `e_entry`）。[ADR-0003 §D5][ADR-0004 §D2.2]

#### §6.1.2 ELF 路径（M4 起新增）

M4 起，跨 object 链接由 DADAO LLD（`ADR-0019`）完成，产出 **`ET_EXEC`** ELF（含 `SHT_RELA`/`R_DADAO_*` 重定位，见 §2–§4）；QEMU test machine 消费该 ELF：[ADR-0004 §D2.2][ADR-0004 §D2.3][ADR-0004 §修订 rev. 2026-10-06]

```
1. 汇编/编译（可多 TU）    →  ET_REL object(s) (.o)（含 SHT_RELA，见 §2–§4）
2. ld.lld -T dadao.lds     →  ET_EXEC ELF（e_machine=EM_DADAO(0x0DA0)、e_flags[7:0]=1）
3. QEMU test machine 解析 Elf64_Ehdr/Elf64_Phdr，按 VA=PA 装载 PT_LOAD 段，从 e_entry 进入
```

- **装载语义**：按 VA=PA（§5.2）将 **`PT_LOAD`** 段装入其 `p_vaddr` 对应区域（RAM/ROM，`ADR-0004 §D1`）；`p_filesz` 字节取自文件、`p_memsz − p_filesz` 的尾部（`.bss`）**零填充**；段的顺序/对齐见 §5.1。[ADR-0004 §D2.2]
- **入口**：取 ELF **`e_entry`**（不再固定为加载基址）。[ADR-0004 §D2.2]
- **头校验**：`EI_CLASS=ELFCLASS64`、`EI_DATA=ELFDATA2MSB`、`e_machine=EM_DADAO(0x0DA0)`、`e_flags[7:0]=1`（§1/§1.3）。[ADR-0004 §D2.2]
- **首段与文件偏移**：M4 裸机路径 `dadao.lds` **不使用 `FILEHDR PHDRS`**——ELF 头/程序头表**只存在于文件中、不进入 guest 内存**（加载器从**文件**解析 `Ehdr`/`Phdr`）；首个 `PT_LOAD` 从 `.text` 起（VA=PA），其 `p_offset` **不做要求**（**不要求为 0、也不禁止为 0**）。[ADR-0003 §修订 rev. 2026-10-06]
- **over-size / 畸形**：任一 `PT_LOAD` 段装载区间越出映射区域（RAM 16 MiB / ROM 64 KiB）、含 `.bss` 的 `p_memsz` 超限、或畸形 ELF ⇒ **启动加载阶段报错并非零退出**（工具/加载错误层，与 guest fault 分层）。[ADR-0004 §D2.3]

### §6.2 与 ADR-0004 的加载模型统一

本 pipeline 与 ADR-0004（`SPEC-006t`；`SPEC-107t` rev. 2026-10-06 调整后）的加载模型统一：ADR-0003 冻结 object → flat 的转换，ADR-0019 冻结 M4 重定位/ELF 链接，ADR-0004 冻结 QEMU 的加载/入口协议——**raw-bin 与 ELF 两条路径并存**。[ADR-0003 §D5][ADR-0004 §D2.2][ADR-0004 §修订 rev. 2026-10-06]

**raw-bin 路径（保留；M1–M3）**——双镜像（ROM trampoline blob 由 `-bios` 加载，测试 flat binary 由 `-kernel` 加载，**两者必须同时提供**）：[ADR-0004 §D2.3]

```
qemu-system-dadao -machine dadao-m1 -bios rom.bin -kernel test.bin
```

- 测试 flat binary 由 `-kernel` 加载到 RAM 基址 `0xffff_0000_0000`，入口固定为该基址；此路径下 QEMU 不做 ELF 解析、不读取 `e_entry`。[ADR-0004 §D2.2][ADR-0004 §D2.3]
- ROM trampoline blob 链接基址 `0xffff_ffff_0000`，上限 64 KiB。[ADR-0004 §D2.3]

**ELF 路径（M4 起新增）**——单 ELF（`-kernel image.elf`，入口取 `e_entry`，不使用外部 `-bios` ROM）：[ADR-0004 §D2.2][ADR-0004 §D2.3]

```
qemu-system-dadao -machine dadao-m1 -kernel image.elf
```

- QEMU 解析 `Elf64_Ehdr`/`Elf64_Phdr`，按 VA=PA（§5.2）装载 `PT_LOAD` 段（`p_filesz` 数据 + `.bss` 零填充），入口取 `e_entry`。[ADR-0004 §D2.2]
- 段装载越出映射区域（RAM 16 MiB / ROM 64 KiB）或畸形 ELF ⇒ 启动加载阶段报错并非零退出。[ADR-0004 §D2.3]

### §6.3 M1 / raw-bin 约束

- **`.text` 自包含约束**：raw-bin 路径（M1）的 `.text` 必须单 TU 自包含（段内标签就地解析、不产生重定位）；若使用绝对地址构造，其地址须与 ADR-0004 冻结的加载基址一致。[ADR-0003 §Consequences]
- **不引入 LLD（仅限 raw-bin 路径）**：M1 raw-bin pipeline 不依赖 target linker；M4 起 ELF 路径（§6.1.2）由 `ADR-0019` 决策并引入 DADAO LLD（`LLVM-056t`）。[ADR-0003 §Consequences]
- **`e_entry`**：raw-bin 路径下 `e_entry` 不被消费（入口固定为加载基址）；**M4 ELF 路径下 `e_entry` 被消费为入口**（§6.1.2/§6.2）。[ADR-0003 §Consequences][ADR-0004 §D2.2]
- **D2/D3/D4 不得在 M1 实现**：M1 不实现 ELF relocation（`LLVM-006t` 明确不实现）；M4 起由 `ADR-0019`（§2–§4）落地。[ADR-0003 §Consequences]

---

## 附录 A：来源对照

| 本合约 § | 内容 | 决策点 |
|----------|------|--------|
| §1 | ELF 文件头字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`） | `ADR-0003` §D1（含 `## 修订`） |
| §2 | 重定位类型（`SHT_RELA`、`R_DADAO_*` 编号、逐指令挂载；`R_DADAO_REL12`（`rb0`）/ `R_DADAO_ABS12`（`rb1–rb63`）= `ld/st` 符号偏移专用类型，按基址寄存器自动选型） | `ADR-0019` §D1–D2、§D5（+ `ADR-0021` §D1–D2） |
| §3 | 重定位公式与溢出策略（无 −4、link-time error；`REL12` = `S + A − P`（rb0/PC 相对）、`ABS12` = `S + A`（rb1–rb63 基址相对）字节偏移及越界；`ABS48` 数据 8B 字段） | `ADR-0019` §D3、§D6（+ `ADR-0021` §D1、§D3） |
| §4 | 重定位松弛（禁用 relaxation、不做 `ABS32`、`RELA_PAGE`/`RELA_LO` 留后） | `ADR-0019` §D4、§D7–D8 |
| §5 | 段对齐、VA=PA（raw-bin 与 ELF 路径均适用）、`PT_LOAD` 的 `p_align` 口径（目标默认 64 KiB、可覆写） | `ADR-0003` §D5（+ `ADR-0004` §D2.2 加载地址/VA=PA；`p_align` 并来自 `ADR-0003` §修订 rev. 2026-10-06） |
| §6 | 端到端 artifact pipeline（raw-bin 路径 + M4 ELF 路径）、单 TU 自包含、多段拼接、加载/启动协议、与 ADR-0004 一致 | `ADR-0003` §D5（+ §Context、§Consequences）；§6.1.2 去 `FILEHDR PHDRS` 来自 `ADR-0003` §修订 rev. 2026-10-06；§6.1.2/§6.2 的 ELF 加载与启动并来自 `ADR-0004` §D2.2/§D2.3（`## 修订` rev. 2026-10-06） |

> §2–§4 的重定位决策点来自 ADR-0019（`SPEC-105t`）与 ADR-0021（`SPEC-122t`/`SPEC-123t`，`R_DADAO_REL12` + `R_DADAO_ABS12`，rev. 2026-10-09），非 ADR-0003 决策。

> §6.1.1/§6.2 的 raw-bin 启动命令/镜像对来自 ADR-0004（`SPEC-006t`）§D2.2/§D2.3；§6.1.2/§6.2 的 ELF 加载/启动来自 ADR-0004 的 `## 修订` rev. 2026-10-06（`SPEC-107t`，用户逐条确认），均非 ADR-0003 决策。
