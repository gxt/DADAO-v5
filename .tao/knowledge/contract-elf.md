# SimRISC M1 ELF 合约（Object ABI）

> **状态**：Accepted
>
> **来源**：`.tao/adr/adr-0003-object-abi.md`（ADR-0003，`SPEC-005t` 产出，Status: Accepted，rev. 2026-09-13 `e_flags`、rev. 2026-09-14 D2 登记补充）。本合约的 M1 决策（D1 头字段 + D5 段对齐/VA=PA/artifact pipeline）是 ADR-0003 的归一化投影；**§2–§4（重定位）另有来源 `.tao/adr/adr-0019-dadao-relocation-types.md`（ADR-0019，Status: Accepted，用户 2026-10-05 逐条确认 D1–D8）**。
>
> **引用**：指令格式/字段宽度/对齐/地址模型引用 `.tao/knowledge/contract-isa.md`（SimRISC 0.5.4）；端序/指针宽度引用 `.tao/knowledge/contract-abi.md`（0.9.2）。本合约不重复定义这些内容。
>
> **M1 范围**：§1 ELF 文件头字段、§5 段对齐与 VA=PA、§6 端到端 artifact pipeline。
>
> **M4 范围（§2–§4）**：§2 重定位类型、§3 重定位公式与溢出策略、§4 重定位松弛——由 `ADR-0019`（M4，Accepted，用户 2026-10-05 逐条确认 D1–D8）冻结为规范正文。
>
> **来源标注**：每条规范性断言句末以 `[ADR-0003 §DN]`（§1/§5/§6）或 `[ADR-0019 §DN]`（§2–§4）标注来源决策点，不写行号；引用合约时用 `contract-isa.md §N` / `contract-abi.md §N`。
>
> **说明**：本合约（§1/§5/§6）由 ADR-0003 归一化投影而来，§2–§4 由 ADR-0019 归一化投影而来，面向实现；与 ADR-0003（§1/§5/§6）或 ADR-0019（§2–§4）冲突时阻断实现，走变更流程（见 `spec/Process-02-合约编写规范.md`）。v5 `spec/` 不含 ELF 内容，D1/D5 属架构自定义（ELF 结构常量取自 ELF 标准，具体取值由 ADR-0003 决策）；遗留 `Dadao.def`/`ELF.h` 仅作只读对照，不作为编号/公式来源。[ADR-0003 §Context]

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
| 0 | `R_DADAO_ABS48` | `set.zw` / `or.w` / `andn.w` 地址构造序列（≤ 3 片 wyde） | 3×`immu16`（按 `wyde-position` 分片） |
| 1 | `R_DADAO_REL26` | `call` / `jump`（iiii） | `imms24`（有效 26 位） |
| 2 | `R_DADAO_REL20` | `br.n` / `br.nn` / `br.z` / `br.nz` / `br.p` / `br.np`（riii） | `imms18`（有效 20 位） |
| 3 | `R_DADAO_REL14` | `br.eq` / `br.ne`（rrii） | `imms12`（有效 14 位） |
| 4 | `R_DADAO_NUM` | 类型计数（非实际重定位） | — |

相对类的**有效位宽 = 立即数位宽 + 2**（字偏移；`24+2=26` / `18+2=20` / `12+2=14`）；指令格式/字段位置见 [contract-isa.md §2.3–§2.4]，分支/call/jump 语义见 [contract-isa.md §4.7][contract-isa.md §5.2]。[ADR-0019 §D2]

### §2.3 挂载粒度与分片

reloc **逐指令**挂载（非逐段/逐符号）；多片时 linker 依**指令内的 `wyde-position`（`wp`，编码于 `hb[5:4]`）**判定该片对应地址的哪 16 位。[ADR-0019 §D5][contract-isa.md §2.4]

---

## §3 重定位公式与溢出策略

### §3.1 公式

`S` = 符号值（定义处地址）、`A` = addend（`r_addend`，显式）、`P` = 重定位处地址。[ADR-0019 §D3]

| 类型 | 公式 | 落点字段 |
|------|------|----------|
| `R_DADAO_REL26` / `R_DADAO_REL20` / `R_DADAO_REL14` | `field = (S + A − P) >> 2`（**字偏移**） | `imms24` / `imms18` / `imms12` |
| `R_DADAO_ABS48` | `value = S + A`（48 位，按 `wyde-position` 分片写入 3×`immu16`） | 3×`immu16` |

相对类公式为 `(S + A − P) >> 2`，即**字偏移**（`P` 为重定位处地址本身）。**v5 无 `− 4`**：不引入 `PC+4` 修正；这与 0628 的 `(val-4)>>2` 不同——v5 的 `rb0` 读出为**当前指令地址**（非下一条）[contract-isa.md §1.3.2]，故 `P` 无需再减 4。[ADR-0019 §D3]

### §3.2 溢出策略

重定位结果越出目标字段可表示范围时，一律 **link-time error**（**不截断、不 wrap**）。[ADR-0019 §D6]

---

## §4 重定位松弛（Relaxation）

- **本期禁用 relaxation**（不缩短序列）：`R_DADAO_ABS48` **≤3 片**（DADAO 地址空间 48 位，最多 3 片）；**一律发射固定 max 3 片**，linker 只做原地补丁，不重排/不缩短。[ADR-0019 §D4][ADR-0019 §D7]
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

### §5.2 VA=PA（freestanding 无 MMU）

M1 无 MMU、无页表，加载期不做地址重定位。段的虚拟地址（VMA）等于其物理加载地址（PA）；即段被放在哪个物理地址，就以该地址作为其有效虚拟地址。有效地址为 48 位，高 16 位在地址计算时被硬件忽略 [contract-isa.md §1.5]。[ADR-0003 §D5]

---

## §6 端到端 artifact pipeline

### §6.1 唯一路径（M1）

M1 采用 **raw / section extraction** 路径，**不引入 target linker（LLD）**、不产生 `ET_EXEC`、不做跨 object 链接：[ADR-0003 §D5]

```
1. 汇编/编译（单 TU）                            →  ET_REL object  (.o)
2. llvm-objcopy --only-section=.text -O binary  →  flat binary（.text 段原始字节）
3. QEMU test machine 将 flat binary 加载到 RAM 基址，并从该基址进入
```

- **步骤 1——单 TU 自包含**：步骤 1 的 `.o` 为单翻译单元、自包含；段内标签由汇编器就地解析，**不产生重定位**。[ADR-0003 §D5] 术语「单 TU 自包含」指：TU（Translation Unit，翻译单元）是汇编器/编译器的单次输入单位，一个 TU 产出恰好一个 object（`.o`）；「自包含」指该单元内所有符号/标签都在本单元内定义并**就地解析**，不引用任何外部符号。自包含的直接后果是**不产生重定位**——汇编器在汇编期即可算出全部标签地址，无需留待链接期回填的占位项。[ADR-0003 §Context]
- **步骤 2——objcopy 段提取**：步骤 2 使用 `objcopy`（M1 用 `llvm-objcopy`）的**段提取**能力（`--only-section=.text` + `-O binary`），不经过静态链接；这是 M1 不依赖 LLD 的关键。M1 e2e 路径冻结提取 `.text`。[ADR-0003 §D5]
- **多段提取连续拼接**：其它可分配段（若后续 M1 用例需要）以同一机制提取，其对齐要求见 §5.1。若 M1 用例需要 `.rodata`/`.data`，则以同一 `objcopy` 机制提取并按 8B 对齐**连续拼接**为单一 flat 镜像（拼接顺序沿用 §5.1 默认布局 `.text` → `.rodata` → `.data`）。[ADR-0003 §D5]
- **步骤 3——flat binary 而非 ELF**：步骤 3 的 QEMU 消费的是 **flat binary，不是 ELF**；`e_entry` 不被 test machine 读取，入口固定为 flat binary 的加载基址。机器名、加载地址、命令行与 trampoline 由 ADR-0004（`SPEC-006t`）冻结。[ADR-0003 §D5] **不得把 QEMU 的 flat binary 加载称为「ELF loader」**——M1 test machine 不做 ELF 解析。[ADR-0003 §D5][ADR-0004 §D2.2]

### §6.2 与 ADR-0004 的加载模型统一

本 pipeline 与 ADR-0004（`SPEC-006t`）的加载模型统一：ADR-0003 冻结 object → flat 的转换，ADR-0004 冻结 flat → QEMU 的加载/入口协议。[ADR-0003 §D5]

ADR-0004 冻结的唯一启动协议为**双镜像**（ROM trampoline blob 由 `-bios` 加载，测试 flat binary 由 `-kernel` 加载，**两者必须同时提供**）：[ADR-0004 §D2.3]

```
qemu-system-dadao -machine dadao-m1 -bios rom.bin -kernel test.bin
```

- 测试 flat binary 由 `-kernel` 加载到 RAM 基址 `0xffff_0000_0000`，入口固定为该基址；QEMU 不做 ELF 解析、不读取 `e_entry`。[ADR-0004 §D2.2][ADR-0004 §D2.3]
- ROM trampoline blob 链接基址 `0xffff_ffff_0000`，上限 64 KiB。[ADR-0004 §D2.3]

### §6.3 M1 约束

- **`.text` 自包含约束**：M1 的 `.text` 必须单 TU 自包含（段内标签就地解析、不产生重定位）；若使用绝对地址构造，其地址须与 ADR-0004 冻结的加载基址一致。[ADR-0003 §Consequences]
- **不引入 LLD**：M1 pipeline 不依赖 target linker；不得默认 M1 已获得 DADAO LLD backend。M2 若需要多 object/重定位，再决策 linker 与 §2/§3/§4。[ADR-0003 §Consequences]
- **`e_entry` 仅作信息**：不被 M1 test machine 消费；入口由 ADR-0004 的加载模型冻结。[ADR-0003 §Consequences]
- **D2/D3/D4 不得在 M1 实现**：M1 不实现 ELF relocation（`LLVM-006t` 明确不实现）。[ADR-0003 §Consequences]

---

## 附录 A：来源对照

| 本合约 § | 内容 | 决策点 |
|----------|------|--------|
| §1 | ELF 文件头字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`） | `ADR-0003` §D1（含 `## 修订`） |
| §2 | 重定位类型（`SHT_RELA`、`R_DADAO_*` 编号、逐指令挂载） | `ADR-0019` §D1–D2、§D5 |
| §3 | 重定位公式与溢出策略（无 −4、link-time error） | `ADR-0019` §D3、§D6 |
| §4 | 重定位松弛（禁用 relaxation、不做 `ABS32`、`RELA_PAGE`/`RELA_LO` 留后） | `ADR-0019` §D4、§D7–D8 |
| §5 | 段对齐、VA=PA | `ADR-0003` §D5 |
| §6 | 端到端 artifact pipeline、单 TU 自包含、多段拼接、与 ADR-0004 一致 | `ADR-0003` §D5（+ §Context、§Consequences） |

> §2–§4 的重定位决策点来自 ADR-0019（`SPEC-105t`），非 ADR-0003 决策。

> §6.2 的启动命令/镜像对来自 ADR-0004（`SPEC-006t`）§D2.2/§D2.3，非 ADR-0003 决策。
