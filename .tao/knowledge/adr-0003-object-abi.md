# ADR-0003: SimRISC M1 Object ABI（ELF 头字段与段/流水线）

**状态**：Accepted（rev. 2026-09-13: `e_flags` 版本字段，见 `## 修订`）
**日期**：2026-09-13
**关联**：ADR-0001（greenfield 重建）、ADR-0002（构建编排）、ADR-0004（test machine，`SPEC-006t`）、`SPEC-005t`（本 ADR 任务）、`SPEC-007t`（ELF 合约，下游规范化）、`.tao/knowledge/contract-isa.md`（SimRISC 0.5.3）、`.tao/knowledge/contract-abi.md`（0.9.2）

## Context（背景）

DADAO-v5 的 M1 工具链需要产出并加载 ELF object。ELF 文件头中与架构相关的字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`）以及段加载语义在 v5 `spec/` 中**没有任何依据**：`SimRISC-00`~`04` 与 `DADAO-11`~`23` 均不含 ELF/object ABI 内容。因此本 ADR 是这些字段的**原始架构决策**，相关取值标记为「无 spec 依据，架构自定义」。

**术语说明——单翻译单元（TU）自包含**：TU（Translation Unit，翻译单元）是汇编器/编译器的单次输入单位，一个 TU 产出恰好一个 object（`.o`）。「自包含」指该单元内所有符号/标签都在本单元内定义并**就地解析**，不引用任何外部符号。自包含的直接后果是**不产生重定位（relocation）**——汇编器在汇编期即可算出全部标签地址，无需留待链接期回填的占位项；反之，一旦引用外部符号或跨单元/跨段地址，就必须保留重定位项，交由链接器（linker/LLD）在链接期回填。M1 工具链只有 MC（汇编器），既无 DADAO target linker（LLD）也无跨 object 链接步骤，**不消费重定位**，故 M1 要求单 TU 自包含：使 `.o` 可经 `objcopy` 抽段直接转为 flat binary 交给 QEMU，不依赖 linker。

M1 范围为单翻译单元（single TU）、freestanding、自包含：无跨 object 链接、无动态链接、无 TLS、无 target linker（LLD）。据此，本 ADR 只冻结 M1 实际需要的内容：

- **D1**：ELF 文件头固定字段；
- **D5**：段对齐、VA=PA 与端到端 artifact pipeline。

**`Deferred to M2`**：重定位类型表（D2）、重定位溢出策略（D3）、重定位松弛策略（D4）。M1 的 `.s` 标签在同一段内由汇编器就地解析，**不产生重定位**；M1 无 link 步骤，故 M1 不冻结任何重定位编号/公式/溢出/松弛策略，完整 relocation 由 M2 决策（另见 `LLVM-012t`）。

依赖 oracle：`.tao/knowledge/contract-isa.md`（0.5.3，指令格式/字段宽度/对齐/地址模型）与 `.tao/knowledge/contract-abi.md`（0.9.2，端序/指针宽度）。遗留 DADAO toolchain（`Dadao.def`/`ELF.h`）仅作**只读对照**，本 ADR **不采用**其重定位编号或公式；`EM_DADAO` 的取值沿用 legacy 命名以便生态识别，但其注册状态由本 ADR 明确为 project-custom（见 D1）。

## Decision（决策）

### D1 ELF 文件头固定字段

| 字段 | 冻结值 | 含义 |
|------|--------|------|
| `EI_CLASS` | `ELFCLASS64 = 2` | 64 位 ELF |
| `EI_DATA` | `ELFDATA2MSB = 2` | 大端 |
| `e_machine` | `EM_DADAO = 0x0DA0` | project-custom machine id |
| `e_flags` | `0x00000001` | 对象/ABI 格式版本 = 1（bits 0–7）；bits 8–31 保留为 0 |
| `EI_OSABI` | `ELFOSABI_NONE = 0` | freestanding，无 OS 专用 ABI |

逐项理由：

- **`EI_CLASS = ELFCLASS64 (2)`**：SimRISC 每个用户寄存器 64 位、机器字长 64 位 [contract-isa §1.1]；存储模型为 64 位地址空间（有效虚拟地址 48 位）[contract-isa §1.5]。指令字为 32 位 [contract-isa §2.1]，但寄存器/地址模型为 64 位，故使用 `Elf64_*` 结构（`Elf64_Ehdr` 等）。
- **`EI_DATA = ELFDATA2MSB (2)`**：SimRISC 指令字与数据均为大端序，多字节数据的最高有效字节存放在最低地址 [contract-isa §1.6][contract-isa §2.1]；ABI 基础数据布局亦为大端序 [contract-abi §1.7]。
- **`e_machine = EM_DADAO (0x0DA0)`**：**project-custom**。该值**未注册**于 IANA/SysV 公共 ELF registry，也**不存在于 LLVM 主线**；它仅存在于遗留 DADAO toolchain fork。M1 沿用该命名以保持项目生态内 machine identity 的连续，但**不声称已注册 upstream**。未正式注册带来的碰撞风险由 `e_flags` 版本字段缓解（见下）。
- **`e_flags = 0x00000001`**：**bits 0–7 为对象/ABI 格式版本号**（`e_flags[7:0]`），M1 取值为 **1**；后续每当对象/ABI 格式发生不兼容变化时递增。**bits 8–31 保留**，必须为 0。

  | 位 | 含义 |
  |----|------|
  | 0–7 | 对象/ABI 格式版本号（M1 = 1） |
  | 8–31 | Reserved（必须为 0） |

  consumer 必须按版本号与保留位决定是否接受 object：

  | `e_flags[7:0]` | 含义 | consumer 行为 |
  |---------------|------|--------------|
  | 0 | legacy DADAO object（无版本字段） | **拒绝**（非 M1） |
  | 1 | M1 对象/ABI 格式 | 接受 |
  | 2–255 | 未知/未来版本 | **拒绝**（consumer 无法解释） |
  | 任意（bits 8–31 ≠ 0） | 违反保留位约束 | **拒绝** |

  即 consumer 只接受 `e_machine = 0x0DA0` 且 `e_flags = 0x00000001`（版本 1、保留位全 0）的 object；遇到版本不匹配、未知版本或保留位非 0 一律报错。该字段既是 M1 namespace 与 legacy namespace 的机器可识别分界，又预留了后续 milestone/ABI 版本的编码空间（8 位版本字段的既有实践如 ARM EABI `EF_ARM_EABIMASK`、LoongArch ABI version）。
- **`EI_OSABI = ELFOSABI_NONE (0)`**：M1 为 freestanding 裸机测试环境，无 OS 专用 ABI 扩展，采用通用 System V 值。

### D5 段对齐、VA=PA 与端到端 artifact pipeline

#### 段最小对齐

| 段 | 最小对齐 | 理由 |
|----|---------|------|
| `.text` | 4 字节 | 每条指令 4 字节且必须 4 字节对齐 [contract-isa §2.1] |
| `.rodata` | 8 字节 | 64 位常量/指针的自然对齐；`ld.o`/`st.o` 要求 8 字节对齐 [contract-isa §4.1.1] |
| `.data` | 8 字节 | 同 `.rodata` |
| `.bss` | 8 字节 | 同 `.rodata` |

指针为 8 字节 [contract-abi §1.7]。段默认布局顺序为 `.text` → `.rodata` → `.data` → `.bss`；在满足各自最小对齐的前提下允许调整顺序。

#### VA=PA（freestanding 无 MMU）

M1 无 MMU、无页表，加载期不做地址重定位。段的虚拟地址（VMA）等于其物理加载地址（PA）；即段被放在哪个物理地址，就以该地址作为其有效虚拟地址。有效地址为 48 位，高 16 位在地址计算时被硬件忽略 [contract-isa §1.5]。

#### 唯一端到端 artifact pipeline（M1）

M1 采用 **raw / section extraction** 路径，**不引入 target linker（LLD）**、不产生 `ET_EXEC`、不做跨 object 链接：

```
1. 汇编/编译（单 TU）                          →  ET_REL object  (.o)
2. objcopy --only-section=.text -O binary  →  flat binary（.text 段原始字节）
3. QEMU test machine 将 flat binary 加载到 RAM 基址，并从该基址进入
```

- 步骤 1 的 `.o` 为单翻译单元、自包含；段内标签由汇编器就地解析，**不产生重定位**。
- 步骤 2 使用 `objcopy`（M1 用 `llvm-objcopy`）的**段提取**能力（`--only-section=.text` + `-O binary`），不经过静态链接；这是 M1 不依赖 LLD 的关键。M1 e2e 路径冻结提取 `.text`；其它可分配段（若后续 M1 用例需要）以同一机制提取，其对齐要求见上表。若 M1 用例需要 `.rodata`/`.data`，则以同一 `objcopy` 机制提取并按 8B 对齐**连续拼接**为单一 flat 镜像（拼接顺序沿用上表默认布局 `.text → .rodata → .data`）。
- 步骤 3 的 QEMU 消费的是 **flat binary，不是 ELF**；`e_entry` 不被 test machine 读取，入口固定为 flat binary 的加载基址（机器名、加载地址、命令行与 trampoline 由 ADR-0004（`SPEC-006t`）冻结）。因此本 ADR 不出现「test machine 跳到 `e_entry`」的表述。
- 本 pipeline 与 ADR-0004（`SPEC-006t`）的加载模型统一：ADR-0003 冻结 object → flat 的转换，ADR-0004 冻结 flat → QEMU 的加载/入口协议。

### D2/D3/D4 — `Deferred to M2`（登记，不冻结）

以下内容服务 M2，**不属 M1 规范性决策**。本 ADR 仅登记主题，不冻结编号/公式/策略：

- **D2 重定位类型表（`Deferred to M2`）**：M1 单 TU 自包含、无跨 object、无 link，汇编器就地解析标签，**不产生重定位**，故 M1 不定义任何重定位类型。M2 启用时的场景登记（格式/字段位置见 [contract-isa §2.3–§2.4]，分支/call/jump/rela 语义见 [contract-isa §4.7][contract-isa §5.2–§5.4]；字段宽度以 0.5.3 格式为准，不在本 ADR 冻结）：

  | 场景 | 0.5.3 指令格式 | 字段约束 |
  |------|---------------|----------|
  | 绝对 64-bit 数据地址 | 数据节 | 全 64 位 |
  | 绝对 64-bit 地址构造 | `set.zw` + `or.w`（rwii，wyde 位置选择器在 `hb[5:4]`） | 每次 16 位，位置由 wyde 选择器决定 |
  | PC 相对短程分支 | `br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np`（riii，imms18） | 18-bit 有符号字偏移 |
  | PC 相对双寄存器分支 | `br.eq`/`br.ne`（rrii，imms12） | 12-bit 有符号字偏移 |
  | PC 相对 call/jump（中程） | `call imms24`/`jump imms24`（iiii） | 24-bit 有符号字偏移 |
  | PC 相对地址加载 | `rela.si`（riii，imms18 << 12） | 30-bit 有效偏移，页号差 |

  > M2 冻结重定位编号时，须在 `e_flags[7:0] = 1`（M1 对象/ABI 格式版本）的 namespace 内独立编号，不得沿用 legacy `Dadao.def` 的编号或公式。
- **D3 重定位溢出策略（`Deferred to M2`）**：有界重定位溢出时报错（link-time error）还是截断/wrap，及各类型分别的策略，留 M2 冻结。
- **D4 重定位松弛策略（`Deferred to M2`）**：M1 无 link 步骤，松弛（relaxation）不适用；M1 是否/如何禁止 relaxation 的正式策略，留 M2 在引入 relocation 时冻结。

## Rationale（理由）

- **只冻结 M1 需要的最小集合**：M1 是单 TU、freestanding、自包含，既不产生重定位也不需要链接；冻结 D2/D3/D4 会引入没有消费者的规范，且过早固化难以随 M2 CodeGen 调整。因此 M1 只冻结 object 头字段（D1）与段/流水线（D5）。
- **64 位大端 ELF 由 ISA/ABI 决定，而非习惯**：`EI_CLASS`/`EI_DATA` 直接来自 64 位寄存器/地址模型与大端序规定 [contract-isa §1.1/§1.5/§1.6][contract-abi §1.7]。
- **沿用 `EM_DADAO` 但显式声明注册状态**：沿用可保持项目生态 machine identity 连续；但必须如实说明其未注册 upstream，并以 `e_flags[7:0] = 1`（8 位对象/ABI 格式版本字段）作为 M1 namespace 的机器可识别分界，避免同一 machine id 下新/旧 consumer 对 object 的静默误解释。
- **`e_flags` 用 8 位版本字段而非 1 位标志**：1 位标志只能区分「M1 vs legacy」二态，无法表达后续 milestone/ABI 格式的不兼容变化，会使后续版本被迫另择字段或产生静默误解释。采用 bits 0–7 版本号（M1 = 1，变化时递增）+ bits 8–31 保留，可在同一 `e_machine` 下表达版本演进，并让 consumer 以「未知版本即拒绝」的前向兼容规则处理未来对象；此做法与 ARM EABI（8 位版本掩码）、LoongArch（多位 ABI/对象版本）一致。
- **raw / section extraction 而非 LLD**：M1 没有 DADAO target linker，且单 TU 自包含；`objcopy --only-section=.text -O binary` 足以把 `.o` 转成 QEMU 可加载的 flat binary。此路径不把 Post-M2 的 LLD 变成 M1 必需依赖，也不产生 M1 无法解析的 `ET_EXEC`/重定位残留。
- **删除 `e_entry` 加载语义**：test machine 消费 flat binary 并从固定基址进入，`e_entry` 对 M1 加载无作用；保留「跳到 `e_entry`」表述会与 ADR-0004 的加载模型互斥。

## Consequences（影响）

- **命名空间**：`EM_DADAO = 0x0DA0` 为 project-custom（未在 IANA/SysV/LLVM 主线注册），存在与其它使用该值的私有工具链碰撞的风险；`e_flags[7:0]`（对象/ABI 格式版本）使 M1 object 可被机器识别，consumer 必须拒绝版本号 ≠ 1、版本未知或含非 0 保留位（bits 8–31）的 object。
- **不引入 LLD**：M1 pipeline 不依赖 target linker；不得默认 M1 已获得 DADAO LLD backend。M2 若需要多 object/重定位，再决策 linker 与 D2/D3/D4。
- **`e_entry` 仅作信息**：不被 M1 test machine 消费；入口由 ADR-0004 的加载模型冻结。
- **`.text` 自包含约束**：M1 的 `.text` 必须单 TU 自包含（段内标签就地解析、不产生重定位）；若使用绝对地址构造，其地址须与 ADR-0004 冻结的加载基址一致。
- **下游**：`SPEC-007t` 将本 ADR 的 D1+D5 规范化为 `contract-elf.md`（§1 + §5 + §6）；D2/D3/D4 在合约中标 `Deferred to M2`，不得在 M1 实现（`LLVM-006t` 明确不实现 ELF relocation）。
- **无 spec 依据**：v5 `spec/` 不含 ELF 内容，D1/D5 属架构自定义（ELF 结构常量取自 ELF 标准，具体取值由本 ADR 决策）；遗留 `Dadao.def`/`ELF.h` 仅作只读对照，不作为编号/公式来源。

## 状态说明

**Accepted（仅 D1/D5）**（2026-09-13；rev. 2026-09-13 `e_flags` 版本字段，见 `## 修订`）。**D2/D3/D4（重定位类型表/溢出策略/松弛策略）标 `Deferred to M2`，尚未决策**——M2 引入 relocation 时，另行经用户逐条确认后再冻结。决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策。评审确认项：D1 五字段冻结、D5 段/流水线与 ADR-0004 一致。

## 修订

**rev. 2026-09-13（用户决定）**：D1 的 `e_flags` 由「bit 0 = M1 ABI version 标志（1 位）」修订为「**bits 0–7 = 对象/ABI 格式版本号（M1 = 1）；bits 8–31 保留（必须为 0）**」。

- **动机**：原 1 位标志只能区分 M1 vs legacy（`e_flags = 0`）二态，**无法编码后续 milestone/ABI 版本**，前瞻性不足。
- **变更范围**：仅 `e_flags` 的语义及引用它的表述（D1 表/理由、D2 namespace 说明、Rationale、Consequences）；`EI_CLASS`/`EI_DATA`/`e_machine`/`EI_OSABI` 与 D5 均**不变**。
- **consumer 规则**：由「`e_flags = 0` 拒绝」扩展为「版本号（bits 0–7）≠ 1、版本未知，或保留位（bits 8–31）非 0 时拒绝」。
- **兼容性**：M1 的 `e_flags` 数值仍为 `0x00000001`（版本 1），已按原设计产出的 M1 object 无需改动。
- **流程说明**：本 ADR 于 2026-09-13 刚 `Accepted` 且尚无实现依赖，按用户明确决定**就地修订并加本修订说明**（`adr-authoring.md` 的一般规则为「不直接改写已 `Accepted` 的决策」，此处为经授权的例外；`**状态**` 行已标 `rev. 2026-09-13`）。
