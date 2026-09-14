# SimRISC M1 ELF 合约（Object ABI）

> **状态**：Accepted
>
> **来源**：`.tao/knowledge/adr-0003-object-abi.md`（ADR-0003，`SPEC-005t` 产出，Status: Accepted，rev. 2026-09-13 `e_flags`、rev. 2026-09-14 D2 登记补充）。本合约是 ADR-0003 的 M1 决策（D1 头字段 + D5 段对齐/VA=PA/artifact pipeline）的归一化投影。
>
> **引用**：指令格式/字段宽度/对齐/地址模型引用 `.tao/knowledge/contract-isa.md`（SimRISC 0.5.3）；端序/指针宽度引用 `.tao/knowledge/contract-abi.md`（0.9.2）。本合约不重复定义这些内容。
>
> **M1 范围**：§1 ELF 文件头字段、§5 段对齐与 VA=PA、§6 端到端 artifact pipeline。
>
> **`Deferred to M2`**：§2 重定位类型、§3 重定位溢出策略、§4 重定位松弛——M1 单 TU 自包含、不产生重定位、无 target linker（LLD）。
>
> **来源标注**：每条规范性断言句末以 `[ADR-0003 §DN]` 标注 ADR-0003 决策点，不写行号；引用合约时用 `contract-isa.md §N` / `contract-abi.md §N`。
>
> **说明**：本合约由 ADR-0003 归一化投影而来，面向实现；与 ADR-0003 冲突时阻断实现，走变更流程（见 `.tao/knowledge/contract-authoring.md`）。v5 `spec/` 不含 ELF 内容，D1/D5 属架构自定义（ELF 结构常量取自 ELF 标准，具体取值由 ADR-0003 决策）；遗留 `Dadao.def`/`ELF.h` 仅作只读对照，不作为编号/公式来源。[ADR-0003 §Context]

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

## §2 `Deferred to M2`：重定位类型

M1 为单 TU 自包含、无跨 object、无 link：汇编器就地解析段内标签，**不产生重定位**，故 **M1 不定义任何重定位类型，不冻结重定位编号/名称/字段位置/公式**。完整 relocation 由 M2 决策（另见 `LLVM-012t`）。[ADR-0003 §D2]

以下仅为 M2 启用时的**场景登记**（非 M1 规范性内容，不冻结编号/公式；格式/字段位置见 [contract-isa.md §2.3–§2.4]，分支/call/jump/rela 语义见 [contract-isa.md §4.7][contract-isa.md §5.2–§5.4]）：[ADR-0003 §D2]

| 场景 | 0.5.3 指令格式 | 字段约束 |
|------|---------------|----------|
| 绝对 64-bit 数据地址（**含** `set.zw`/`or.w` 构造的地址） | 数据节 / `set.zw`+`or.w`（rwii） | 64 位；数据节全 64 位；`set.zw`/`or.w` 每次 16 位（wyde 选择器在 `hb[5:4]`）。**不为 wyde 类指令单列「地址构造」场景** |
| PC 相对短程分支 | `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`（riii，imms18） | imms18 **字**偏移，重定位 `<<2`；有效字节范围 = 18+2 → ±2¹⁹（±512 KiB） |
| PC 相对双寄存器分支 | `br.eq`/`br.ne`（rrii，imms12） | imms12 字偏移 `<<2`；有效字节范围 = 12+2 → ±2¹³（±8 KiB） |
| PC 相对 call/jump（中程） | `call imms24`/`jump imms24`（iiii） | imms24 字偏移 `<<2`；有效字节范围 = 24+2 → ±2²⁵（±32 MiB） |
| PC 相对地址加载 | `rela.si`（riii，imms18 << 12） | imms18 **直接 `<< 12`**（12 位偏移，得 30 位有符号数）；PC 低 12 位清零得 **4KB 对齐**（**与页无关**）、无 `<<2` |

绝对地址（含 `set.zw`/`or.w` 构造）统一归入「绝对 64-bit 数据地址」，**不单列 wyde 类指令的地址构造场景**。**相对分支/call/jump** 的立即数均为**字偏移**，重定位须 **`<<2`**（字→字节），故**有效字节范围 = 立即数位宽 + 2 位**；**`rela.si` 例外**——其立即数直接 `<< 12`（12 位偏移），PC 低 12 位清零得 4KB 对齐，**与页无关、无 `<<2`**。[ADR-0003 §D2]

M2 冻结重定位编号时，须在 `e_flags[7:0] = 1`（M1 对象/ABI 格式版本）的 namespace 内独立编号，**不得沿用** legacy `Dadao.def` 的编号或公式。[ADR-0003 §D2]

---

## §3 `Deferred to M2`：重定位溢出策略

M1 不产生重定位，故不存在溢出策略。有界重定位溢出时报错（link-time error）还是截断/wrap，及各类型分别的策略，留 M2 冻结。[ADR-0003 §D3]

---

## §4 `Deferred to M2`：重定位松弛（Relaxation）

M1 无 link 步骤，松弛（relaxation）不适用。M1 是否/如何禁止 relaxation 的正式策略，留 M2 在引入 relocation 时冻结。[ADR-0003 §D4]

---

## §5 段对齐与 VA=PA

### §5.1 段最小对齐

| 段 | 最小对齐 | 理由 |
|----|---------|------|
| `.text` | 4 字节 | 每条指令 4 字节且必须 4 字节对齐 [contract-isa.md §2.1] |
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

| 本合约 § | 内容 | ADR-0003 决策点 |
|----------|------|-----------------|
| §1 | ELF 文件头字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`） | §D1（含 `## 修订`） |
| §2 | 重定位类型（`Deferred to M2`） | §D2 |
| §3 | 重定位溢出策略（`Deferred to M2`） | §D3 |
| §4 | 重定位松弛（`Deferred to M2`） | §D4 |
| §5 | 段对齐、VA=PA | §D5 |
| §6 | 端到端 artifact pipeline、单 TU 自包含、多段拼接、与 ADR-0004 一致 | §D5（+ §Context、§Consequences） |

> §6.2 的启动命令/镜像对来自 ADR-0004（`SPEC-006t`）§D2.2/§D2.3，非 ADR-0003 决策。
