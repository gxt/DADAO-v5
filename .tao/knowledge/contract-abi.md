# ABI 合约（M1 最小 ABI + M3 标量调用约定）

> **版本：0.9.2** [DADAO-21 §版本][DADAO-11 §版本]
>
> **来源**：`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）、`spec/DADAO-11-AEE-应用程序运行环境.md`（0.9.2）；指令语义与寄存器模型基础引用 `.tao/knowledge/contract-isa.md`（0.5.4）；M3 调用约定的取舍项固化于 `.tao/adr/adr-0018-m3-codegen-choices.md`（`ADR-0018`，Accepted）。
>
> **范围**：M1 最小 ABI 事实（寄存器角色、`SP=rb1`、栈向下增长 / `call` 时 SP 8B 对齐、`call`/`ret` 与 RegRAS；§1–§3）+ **M3 标量调用约定**（非变参、非聚合：参数寄存器、标量提升、栈溢出区、返回值、callee-saved / CSR、栈帧布局、prologue/epilogue、`call` 的 `Defs`/RegMask；§4）+ **M6 口径**（多返回值/聚合返回 §6.1、聚合传参/HFA/HPA §6.4）。供 test machine（`SPEC-006t`）、M1/M3 集成、M3 BasicCodeGen（`LLVM-039t`）、聚合传参实现（`LLVM-062t`/`LLVM-066t`）使用。
>
> **`Excluded from M3`**：高级 ABI（varargs / 聚合返回 sret / 多返回值 / `i128`）与浮点 RF（整层）→ M4（见 §5）；**HFA / HPA / 聚合传参已由用户 2026-10-09 裁定于 M6 收口**（见 §6.4）。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-NN §章节名]` / `[SimRISC-XX §章节名]` 标注 spec/ 来源，不写行号；spec/ 未规定、由 M3 决策补足者标 `[ADR-0018（CX）]`；spec 未规定、由**用户逐条裁定**补足者标 `[spec-decision]`（M6，见 §6）。
>
> **说明**：本合约由 spec/ 归一化投影而来，面向实现；与 spec/ 冲突时阻断实现，走变更流程（见 `spec/Process-02-合约编写规范.md`）。

---

## §1 寄存器角色（M1）

### §1.1 寄存器组

DADAO 提供四组各 64 个、每个 64 位的用户寄存器，对运行中的进程全局可见。[DADAO-21 §寄存器规范]

| 组 | 范围 | M1 处置 |
|----|------|---------|
| RD（数据寄存器） | rd0–rd63 | M1 使用 |
| RB（基址寄存器） | rb0–rb63 | M1 使用 |
| RF（浮点寄存器） | rf0–rf63 | `Excluded from M1`：M1 不使用 RF；仅 rf0（FCSR）的寄存器模型/位布局属 `contract-isa.md §1.3.3` |
| RA（返回地址寄存器） | ra0–ra63 | M1 使用（由 `call`/`ret` 自动管理） |

### §1.2 RD 寄存器角色

[DADAO-21 §寄存器规范 §RD寄存器]

| 寄存器 | ABI 名 | 角色 | Callee-saved |
|--------|--------|------|--------------|
| rd0 | rdzero | 硬连零（Immutable，只读） | Immutable |
| rd1 | rderrno | error number | `-` |
| rd2–rd3 | — | reserved（调试/测试保留，编译器不得分配使用） | `-` |
| rd4–rd7 | — | temporary regs | No |
| rd8–rd15 | rdt0–rdt7 | temporary regs | No |
| rd16–rd31 | rda0–rda15 | temporary regs | No |
| rd32–rd63 | — | callee saved regs | Yes |

### §1.3 RB 寄存器角色

[DADAO-21 §寄存器规范 §RB寄存器]

| 寄存器 | ABI 名 | 角色 | Callee-saved |
|--------|--------|------|--------------|
| rb0 | rbip | instruction pointer（PC，读出为当前指令的地址，只读） | `-` |
| rb1 | rbsp | stack pointer（SP） | Yes |
| rb2 | rbgp | global pointer（GP） | `-` |
| rb3 | rbtp | thread pointer（TP） | `-` |
| rb4–rb7 | — | temporary regs | No |
| rb8–rb15 | rbt0–rbt7 | temporary regs | No |
| rb16–rb31 | rba0–rba15 | temporary regs | No |
| rb32–rb62 | — | callee saved regs | Yes |
| rb63 | rbfp | frame pointer（条件占用：`hasFP` 为真时为 FP，否则作通用 callee-saved 分配；恒 callee-saved） | Yes |

> `rb63` 的 FP 是**条件式**的：`hasFP` 为真时保留为 FP（prologue 保存旧 `rbfp`、epilogue 恢复），否则可作通用 callee-saved 寄存器由编译器分配。**`rb63` 恒为 callee-saved**。因 `rb63` 是 RB 组最高编号，`ldm`/`stm` 的 `immu6` 连续区间不能从 `rb63` 向上展开——批量保存 callee-saved 时须**排除 FP（`rb63`）**，或对 `rb63` **先保存再恢复**。[DADAO-21 §寄存器规范 §RB寄存器]

### §1.4 RF 寄存器角色（M1 不使用）

[DADAO-21 §寄存器规范 §RF寄存器]

| 寄存器 | ABI 名 | 角色 | Callee-saved |
|--------|--------|------|--------------|
| rf0 | — | fp status regs（FCSR） | `-` |
| rf1–rf7 | — | temporary regs | No |
| rf8–rf15 | rft0–rft7 | temporary regs | No |
| rf16–rf31 | rfa0–rfa15 | temporary regs | No |
| rf32–rf63 | — | callee saved regs | Yes |

> 上表仅为寄存器角色事实。RF 全部 `Excluded from M1`：M1 不分配、不存取、不运算 RF。[contract-isa.md §6]

### §1.5 RA 寄存器角色

[DADAO-21 §寄存器规范 §RA寄存器]

| 寄存器 | ABI 名 | 角色 | Callee-saved |
|--------|--------|------|--------------|
| ra0 | — | RAS control（低 48 位 = 0 时仅 RegRAS；≠ 0 时同时启用 MemRAS） | `—` |
| ra1–ra62 | — | 返回地址栈 slot 1–62（`call`/`ret` 自动压栈/弹栈） | `—` |
| ra63 | rasp | RegRAS 栈顶（`call`/`ret` 操作的寄存器） | `—` |

- 高 16 位 / 低 48 位的详细定义见 [DADAO-11 §返回地址栈]。[DADAO-21 §寄存器规范 §RA寄存器]
- RA 各寄存器 Callee-saved 栏均为 `—`，不属 caller/callee-saved 框架。[DADAO-21 §寄存器规范 §RA寄存器]
- 压栈溢出触发 **RASOF** 异常，弹栈下溢触发 **RASUF** 异常。[DADAO-21 §寄存器规范 §RA寄存器]

### §1.6 M1 可分配 / 不可分配集合

**可分配（M1 保守策略）**：

| 组 | 可分配范围 | 来源 |
|----|-----------|------|
| RD | rd4–rd7、rd8–rd15、rd16–rd31、rd32–rd63 | [DADAO-21 §寄存器规范 §RD寄存器] |
| RB | rb4–rb7、rb8–rb15、rb16–rb31、rb32–rb62；`rb63` 条件式（`hasFP` 为假时可分配，为真时保留为 FP） | [DADAO-21 §寄存器规范 §RB寄存器] |
| RF | （无） | [contract-isa.md §6] |

**不可分配**：

| 寄存器 | 原因 | 来源 |
|--------|------|------|
| rd0 | 硬连零（Immutable） | [DADAO-21 §寄存器规范 §RD寄存器] |
| rd1 | reserved（C6；spec 栏 `-`），M3 保留不分配 | [DADAO-21 §寄存器规范 §RD寄存器][ADR-0018（C6）] |
| rd2–rd3 | reserved（调试/测试保留，编译器不得分配使用） | [DADAO-21 §寄存器规范 §RD寄存器] |
| rb0 | PC | [DADAO-21 §寄存器规范 §RB寄存器] |
| rb1 | SP（帧管理专用） | [DADAO-21 §寄存器规范 §RB寄存器] |
| rb2 | GP（global pointer） | [DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C6）] |
| rb3 | TP（thread pointer） | [DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C6）] |
| ra0–ra63 | 由 `call`/`ret` 管理，非通用可分配 | [DADAO-21 §寄存器规范 §RA寄存器] |
| rf0–rf63 | `Excluded from M1` | [contract-isa.md §6] |

> `rd1`/`rb2`/`rb3` 的 Callee-saved 分类在 spec 中为 `-`（未分类）。M3 按 C6 将其与同类 `rd2–rd3` 一并归入 **reserved**（编译器不得分配），**不再作为未冻结的 `[OPEN]` 项**（见 §4.5/§6）。`rd2–rd3` 为 spec 明文 reserved，角色为**调试/测试保留**。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C6）]

### §1.7 基础数据布局（M1）

- 采用**大端序**（big-endian），多字节数据的最高有效字节存放在最低地址。[DADAO-21 §数据表示]
- 指针为 8 字节（`unsigned octa`）；`size_t` 定义为 `unsigned long long`。[DADAO-21 §数据表示]

> 完整标量类型表（`sizeof` / `Alignment` / Dadao 类型对应）见 `spec/DADAO-21-ABI §数据表示 §Fundamental Types`，不属 M1 最小 ABI 事实，本合约不提取。

---

## §2 栈与调用（M1）

### §2.1 栈指针与栈方向

- `SP = rb1`（`rbsp`）。[DADAO-21 §寄存器规范 §RB寄存器]
- 栈从高地址**向下增长**。[DADAO-21 §函数调用规范 §The Stack Frame]
- `rbsp` 位于当前帧低地址端（`rbsp` 为 saved regs / local vars 的下界）。[DADAO-21 §函数调用规范 §The Stack Frame]
- `FP = rb63`（`rbfp`，条件式）；帧指针的使用方式（可选）见 §4.7（M3 条件式策略）。[DADAO-21 §函数调用规范 §The Stack Frame]

### §2.2 `call` 时 SP 对齐

- `call` 指令执行时 `sp` 必须 **8 字节对齐**。[DADAO-21 §传参 §栈溢出规则]
- M3 标量调用路径不涉及变参保存区；变参保存区对齐属高级 ABI（→ M4，见 §5）。[DADAO-21 §传参 §栈溢出规则]

### §2.3 `call`/`ret` 与 RegRAS

- `call` 计算返回地址并压入 `ra63`（RegRAS 栈顶）；`ret` 从 `ra63` 弹出返回地址并跳转。[SimRISC-06 §函数调用][SimRISC-06 §函数返回]
- `ra63` 高 16 位为返回地址引用计数（首次压栈设为 1，递归调用递增），低 48 位为返回地址。[SimRISC-06 §函数调用]
- 正常 leaf / 非 leaf 函数调用**无需软件保存/恢复 RA 寄存器**（由硬件自动压/弹）。[DADAO-21 §寄存器规范 §RA寄存器]
- 完整压栈/弹栈流程（RegRAS/MemRAS、三分支、RASOF/RASUF 精确异常）见 `contract-isa.md §5.4–§5.6`，本合约不重复定义。[SimRISC-00 §压栈流程（call 指令）][SimRISC-00 §弹栈流程（ret 指令）]

---

## §3 机器可读事实

M1/M3 ABI 事实的机器可读形式见 `contracts/abi.yaml`（`version: "0.9.2"`），其字段与 §1 / §4 一致：

- `registers` 表为逐寄存器分类的**权威来源**（`rb1`/`rb63` 依 spec 标 `callee_saved: true`）。[DADAO-21 §寄存器规范]
- `callee_saved` / `reserved_registers` 为便于消费者读取的**派生分类索引**：`callee_saved` 给出各 bank 的**通用 callee-saved 块**（`rd`: 32–63；`rb`: 32–62，上界不含条件式 `rb63`；**RF 整体 `Excluded from M3`、`allocatable.rf` 为空，其块仅作 spec 事实登记**）；`reserved_registers` 依 M3 口径（C6）为 `rd1–rd3` / `rb2–rb3`。[DADAO-21 §寄存器规范][ADR-0018（C6）]
- `scalar_calling_convention` 为 §4 标量调用约定的 M3 机器可读投影。[DADAO-21 §函数调用规范][ADR-0018（C4）]
- `open_items` 为空（M3 的未决项已由用户逐条裁定于 M6 消解，见 §6）；`deferred_to_m4` 为 M3 范围外的高级 ABI 边界索引（见 §5）；其中 `hfa` / `hpa` / `aggregate_arguments` 已由用户 2026-10-09 裁定于 M6 收口（见 §6.4）。[DADAO-21 §返回值 §多返回值][DADAO-21 §传参 §聚合类型参数]

> 派生索引不新增规范性事实。[DADAO-21 §寄存器规范]

---

## §4 M3 标量调用约定（非变参）

> **范围**：本节只覆盖**非变参、非聚合**的标量调用约定——参数寄存器分配、标量参数提升、寄存器溢出栈区、返回值、callee-saved / CSR、栈帧布局、prologue/epilogue、`call` 的寄存器效果与 RegMask、栈对齐 / DataLayout。变参、HFA/HPA、聚合传参/返回、多返回值、sret、`i128`、RF 浮点、动态链接/TLS 均不在本节（见 §5）。[DADAO-21 §函数调用规范]

### §4.1 参数寄存器

- DADAO 使用以下寄存器传送参数，当参数超过寄存器数量时改用栈传送。[DADAO-21 §传参 §参数寄存器]
  - `rd16 - rd31`：数据参数寄存器。
  - `rb16 - rb31`：地址参数寄存器。
  - `rf16 - rf31`：浮点参数寄存器。
- 三组参数寄存器**各自独立计数，从 16 开始递增**；参数按类型分配到对应寄存器组，**不共享槽位**。[DADAO-21 §传参 §参数寄存器]
- 例：`read(int fd, void *buf, size_t count)` 的寄存器映射为 `fd`→`rd16`（标量→rd）、`buf`→`rb16`（指针→rb）、`count`→`rd17`（标量→rd）。[DADAO-21 §传参 §参数寄存器]
- M3 只使用 `rd`/`rb` 两组；`rf16–rf31` 属 RF，M3 整层 `Excluded`（→ M4）。[DADAO-21 §寄存器规范 §RF寄存器][ADR-0018（C1）]

### §4.2 标量参数提升

- 少于 8 字节的标量参数类型（如 `_Bool`、`char`、`short`、`int`）在传递前提升到 8 字节，且**保持符号位不变**。[DADAO-21 §传参 §标量参数]
- 指针类参数传递时使用基址寄存器（`rb16–rb31`）。[DADAO-21 §传参 §标量参数]
- 浮点类型（`float`/`double`）参数使用浮点寄存器（M3 `Excluded`，→ M4）。[DADAO-21 §传参 §标量参数]
- **M3 口径（C4）**：窄参数（`<8B`）的符号/零扩展由 **caller** 完成（按类型符号性），callee 可假定参数已 canonical 扩展、不再重扩展。[DADAO-21 §传参 §标量参数][ADR-0018（C4）]

### §4.3 寄存器溢出与栈溢出区

> 约定：`incoming_sp` 指 callee 入口时的 `rbsp`（即 `call` 执行后、callee 调整帧之前；与帧表 `rbfp + 8` 指同一位置）。[DADAO-21 §函数调用规范 §The Stack Frame]

- 当某 bank 的可用寄存器槽位用完时，该 bank 的**后续参数使用栈传递**。[DADAO-21 §传参 §栈溢出规则]
- 栈参数按**声明顺序从左到右**依次排列，8 字节对齐。[DADAO-21 §传参 §栈溢出规则]
- 三 bank **共享同一个栈增长方向**，各组溢出参数连续紧凑存放。[DADAO-21 §传参 §栈溢出规则]
- **M3 口径（C4）——全局声明序单栈区**：所有 bank 的溢出参数（不论 bank）按其在源**声明中的全局从左到右顺序**依次放入**同一个连续栈区**，每槽 **8 字节**；callee 视角自 `incoming_sp + 0` 起、逐槽 `+8`。[DADAO-21 §传参 §栈溢出规则][ADR-0018（C4）]
- 窄溢出参数同样由 **caller** 按 §4.2 规则扩展为 8B canonical 值后写入槽。[DADAO-21 §传参 §栈溢出规则][ADR-0018（C4）]
- spec `§栈溢出规则` 同句含「按声明顺序从左到右」与「各组溢出参数连续紧凑存放」两种读法；M3 取前者（全局声明序），已由用户判定固化（C4），**未在 spec 正文消歧**（建议补 spec 澄清句；本合约不改 `spec/`）。[DADAO-21 §传参 §栈溢出规则][ADR-0018（C4）]

### §4.4 返回值

- 返回值为**绝对地址**（指针）时，使用 `rb8` 作为返回值寄存器。[DADAO-21 §返回值 §标量类型返回值]
- 返回值为**浮点数**时，使用 `rf8`（M3 `Excluded`，→ M4）。[DADAO-21 §返回值 §标量类型返回值]
- 其它情况（标量整数）使用 `rd8` 作为返回值寄存器。[DADAO-21 §返回值 §标量类型返回值]
- 返回寄存器位于各 bank 低编号区（`rd8–rd15` / `rb8–rb15` / `rf8–rf15`），与参数寄存器区（`rd16–rd31` / `rb16–rb31` / `rf16–rf31`）**不重叠**。[DADAO-21 §返回值]
- **M3 口径（C5）**：
  - 指针返回**直接落 `rb8`**（不经 `rd8` 中转）。[DADAO-21 §返回值 §标量类型返回值][ADR-0018（C5）]
  - **窄返回扩展**：`<8B` 返回值由 **callee** 按 §4.2 的符号/零扩展规则扩展为 canonical 64 位后再 `ret`；**caller 不截断**（可假定 `rd8`/`rb8` 为 canonical 64 位）。[ADR-0018（C5）]
  - 多返回值与 `i128` 返回**不属 M3**（→ M4，见 §5/§6）。[DADAO-21 §返回值 §多返回值][ADR-0018（C5）]

### §4.5 callee-saved / caller-saved 与 CSR

- **callee-saved（被调用者保存）**：`rd32–rd63` 与 `rb32–rb62`；**`rb63` 恒 callee-saved**（条件式 FP，见 §4.7）。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器]
- **caller-saved（调用者保存 / temporary）**：`rd4–rd31` 与 `rb4–rb31`（`rd4–rd7`/`rb4–rb7` 为 spec temporary regs，与 `rd8–rd31`/`rb8–rb31` 连续）。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器]
- **CSR（callee-saved / call-preserved 寄存器集合，M3 口径，C6）**：`CSR = rd32–rd63 ∪ rb32–rb63`（含 `rb63`；供 `getCalleeSavedRegs` 与 `getCallPreservedMask` 使用）。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C6）]
- `SP`（`rb1`）**不属于 CSR**：spec 栏其 callee-saved 为 Yes（callee 必须保持其调用前后的值），但它由 prologue/epilogue 对称调整维护，**不列入通用 CSR 保存集合**。[DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C6）]
- **`rb63`（条件式 FP）恒 callee-saved**：`hasFP` 为真时保留为 FP，由 prologue/epilogue 保存/恢复旧 `rbfp`；否则作通用 callee-saved 由编译器分配。两种占用下跨 `call` 存活的值均须按 callee-saved 处置。[DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C7）]
- `rd1`/`rd2–rd3` / `rb2`/`rb3` 为 **reserved**（编译器不得分配）：`rd2–rd3` 由 spec 明文 reserved（**调试/测试保留**）；`rd1`（rderrno）、`rb2`（rbgp，GP）、`rb3`（rbtp，TP）spec 栏 callee-saved 为 `-`，M3 按 C6 一并**保留不分配**。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C6）]
- `rd0`（rdzero，硬连零 / Immutable）与 `rb0`（rbip，PC，只读）为**特殊寄存器**，不参与通用分配。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器]
- RA（`ra0–ra63`）由 `call`/`ret` 自动管理，不属 caller/callee-saved 框架（见 §2.3）。[DADAO-21 §寄存器规范 §RA寄存器]
- RF（`rf0–rf63`）整层 `Excluded from M3`（→ M4）。[DADAO-21 §寄存器规范 §RF寄存器][ADR-0018（C1）]

### §4.6 `call` 的寄存器效果与 RegMask（M3 口径，C16）

- `call` 指令的 `Defs`（显式定义）为**返回寄存器区间** `rd8–rd15`、`rb8–rb15`（整数/指针返回值区；浮点 `rf8–rf15` 在 M3 `Excluded`）：callee 经 `rd8–rd15`/`rb8–rb15` 返回标量/指针值，调用点须声明这些寄存器被写（单值用 `rd8`/`rb8`；多返回值/聚合按声明顺序自 `rd8`/`rb8` **递增**占用，至多 8 个/bank）。[DADAO-21 §返回值 §标量类型返回值][DADAO-21 §返回值 §多返回值][ADR-0018（C16）]
- 实现**必须**提供 `getCallPreservedMask`（preserved 集合含 `rb32–rb63`）并在 `LowerCall` 附 RegMask，使跨调用存活的 callee-saved（尤其**地址类** `rb32–rb63`）不被误 clobber。[ADR-0018（C16）]
- `ret` **不加 `Defs`**：返回值定义在 `CopyToReg` + glue 链上，`ret` 不额外声明定义。[ADR-0018（C16）]
- 调用者可依赖：跨 `call` 存活的值须置于 callee-saved（`rd32–rd63`/`rb32–rb63`）或由 caller 自行保存；caller-saved（`rd8–rd31`/`rb8–rb31`）可由 callee 自由 clobber。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器]

### §4.7 栈帧布局

栈从高地址**向下增长**；`rbsp` 位于当前帧低地址端（saved regs / local vars 的下界）。[DADAO-21 §函数调用规范 §The Stack Frame]

帧与栈的组织（高→低地址）如下：[DADAO-21 §函数调用规范 §The Stack Frame]

| Position | Contents | Frame |
|----------|----------|-------|
| `rbfp + 8n + 8` | memory argument octa n | Previous |
| … | … | … |
| `rbfp + 8` | memory argument octa 0 | Previous |
| `rbfp` | previous rbfp value | Current |
| `rbfp - 8` | Saved regs or local vars | Current |
| … | … | … |
| `rbsp` | Saved regs or local vars | Current |

- `rbfp` 为帧指针（`FP = rb63`）、`rbsp` 为栈指针（`SP = rb1`）；spec 允许直接用 `rbsp` 访问帧上数据（省一个寄存器与入口/出口指令）。[DADAO-21 §函数调用规范 §The Stack Frame]
- 参数溢出区（§4.3）位于 `rbfp + 8` 起（帧表 `memory argument octa 0`）；SP-only 下等价于入口 `rbsp + 0` 起。[DADAO-21 §函数调用规范 §The Stack Frame]
- **M3 口径（C7）**：
  - 帧指针策略取**标准条件式**：`hasFPImpl = DisableFramePointerElim ∨ hasVarSizedObjects ∨ isFrameAddressTaken ∨ hasStackRealignment`；条件不成立时默认 **SP-only**（`rbsp` 相对寻址），成立或有选项时启用 **FP = rb63**。[DADAO-21 §函数调用规范 §The Stack Frame][ADR-0018（C7）]
  - `getFrameRegister = hasFP ? rb63 : rb1`。[ADR-0018（C7）]
  - `rb63`（FP）**条件式保留**：`hasFP` 为真时保留为 FP（prologue 保存旧 `rbfp`、epilogue 恢复）；否则可作通用 callee-saved 分配。**`rb63` 恒 callee-saved**（见 §4.5）。[DADAO-21 §函数调用规范 §The Stack Frame][DADAO-21 §寄存器规范 §RB寄存器][ADR-0018（C7）]

### §4.8 prologue / epilogue

- **不变量**：
  - `call` 执行时 `sp`（`rbsp`）必须 **8 字节对齐**（见 §2.2）。[DADAO-21 §传参 §栈溢出规则]
  - callee 必须保存在本函数中修改的 callee-saved 寄存器（`rd32–rd63`/`rb32–rb63`），并在返回前恢复。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器]
  - 返回时 `rbsp` 必须恢复到入口值（对称释放）；RA 无需软件保存/恢复（RegRAS 自动）。[DADAO-21 §函数调用规范 §The Stack Frame][DADAO-21 §寄存器规范 §RA寄存器]
- **两套对称策略（M3 口径，C7）**：
  - **SP-only**（默认）：以 `rbsp` 相对访问 saved regs / local vars；入口按需下移 `rbsp`，出口对称上移；溢出参数在入口 `rbsp` 之上。[DADAO-21 §函数调用规范 §The Stack Frame][ADR-0018（C7）]
  - **FP**（条件成立或有选项时）：入口保存旧 `rbfp` 并令 `rbfp` 指向 saved-FP 槽，之后以 `rbfp` 为帧基址（`rbfp + 8n + 8` 访问溢出参数、`rbfp - 8n` 访问 saved regs / local vars）；出口先恢复 `rbsp`，再恢复旧 `rbfp`。[DADAO-21 §函数调用规范 §The Stack Frame][ADR-0018（C7）]
- 具体可汇编序列属实现（`LLVM-038t`/`LLVM-039t`），本合约不规定指令级写法。[ADR-0018（C7）]

### §4.9 栈对齐与 DataLayout（M3 口径，C9）

- spec 只要求 `call` 指令执行时 `sp`（`rbsp`）**8 字节对齐**（见 §2.2）。[DADAO-21 §传参 §栈溢出规则]
- M3 `DataLayout` 串为 `E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`（由 `LLVM-033t` 落地）。[ADR-0018（C9）]
- 两者**不矛盾**：`S128` 是 DataLayout 的**栈自然对齐上界**（16B），而 `call` 时 SP 8B 对齐是 spec 要求的**下界**——16B 对齐的 SP 必然满足 8B 对齐要求；本合约**不做 8/16 冲突裁定**，仅登记二事实。[DADAO-21 §传参 §栈溢出规则][ADR-0018（C9）]
- `S128` / `i128:128` / 省略 `a:` / 大端 `E` 为 C9 已判口径。[ADR-0018（C9）]

### §4.10 M3 覆盖与 M4 交接

- 本节覆盖的 M3 事实：参数寄存器（§4.1）、标量提升（§4.2）、栈溢出区（§4.3）、返回值（§4.4）、callee-saved / CSR（§4.5）、`call` 寄存器效果（§4.6）、帧布局（§4.7）、prologue/epilogue（§4.8）、栈对齐/DataLayout（§4.9）。[DADAO-21 §函数调用规范]
- 不在本节（→ M4）：变参、聚合返回 sret、多返回值、`i128`、RF 浮点、动态链接 / TLS、系统调用规范；**HFA/HPA、聚合传参**不属 M3、已由用户 2026-10-09 裁定于 **M6 收口**（见 §6.4）。[DADAO-21 §传参 §聚合类型参数][DADAO-21 §返回值 §多返回值]

---

## §5 `Excluded from M3`（高级 ABI，→ M4）

以下内容不属 M3 标量调用约定；除已由用户裁定于 **M6 收口**者（状态列注明，见 §6）外，顺延 M4：

| 主题 | spec/ 出处 | 状态 |
|------|-----------|------|
| 可变参数（`va_list` / 保存区 / `va_start` / `va_arg`） | [DADAO-21 §可变参数] | `Excluded from M3`（→ M4） |
| HFA（同质浮点聚合，RF bank；≤8 槽位/64B） | [DADAO-21 §传参 §聚合类型参数] | `Excluded from M3`（**M6 已定口径，见 §6.4**） |
| HPA（同质指针聚合，RB bank；≤8 槽位/64B） | [DADAO-21 §传参 §聚合类型参数] | `Excluded from M3`（**M6 已定口径，见 §6.4**） |
| 聚合传参（≤64B 拆 RD 块 / >64B 间接指针） | [DADAO-21 §传参 §聚合类型参数] | `Excluded from M3`（**M6 已定口径，见 §6.4**） |
| 聚合返回值（hidden sret，指针经 rb16） | [DADAO-21 §返回值 §聚合类型返回值] | `Excluded from M3`（M6 已定口径，见 §6.1） |
| 多返回值 | [DADAO-21 §返回值 §多返回值] | `Excluded from M3`（M6 已定口径，见 §6.1） |
| `i128` 传参 / 返回约定 | [DADAO-21 §返回值 §标量类型返回值] | `Excluded`（M6 裁定不支持，见 §6.3） |
| 浮点 RF（寄存器角色除外，整层） | [contract-isa.md §6][DADAO-21 §寄存器规范 §RF寄存器] | `Excluded from M3`（→ M4） |
| 动态链接 / TLS | （v5 spec 无） | `Excluded from M3`（→ M4） |
| 系统调用规范（`trap`、RD15 调用号、返回值 RD8） | [DADAO-21 §系统调用规范] | `Excluded from M3`（M3 freestanding 无 syscall；→ M4） |

---

## §6 契约收口（M6：原未决项消解，rev. 2026-10-09）

**M3 已判（不再列为未决项）**：`rd1`/`rb2`/`rb3` 分类 → reserved（C6，见 §4.5）；窄返回值扩展 → callee canonical / caller 不截断（C5，见 §4.4）；帧指针省略策略 → 条件式 `hasFPImpl` / 默认 SP-only（C7，见 §4.7）。[ADR-0018（C5）][ADR-0018（C6）][ADR-0018（C7）]

**原 §6 未决项（M6 已消解）**：#1 已由用户 2026-10-09 裁定并**写入 `spec/DADAO-21 §返回值`**（本任务同一变更内改册 + 同步只读锁），故直接引 spec；#2 / #3 在 M3 无 spec 依据，**由用户逐条裁定**，标 `[spec-decision]`。消解后口径冻结，供 `LLVM-062t` 实现**直接引用**。

| # | 项 | 结论（M6 口径） | 来源 |
|---|----|----------------|------|
| 1 | 多返回值 / 聚合返回 | 按**声明顺序**依次占用返回寄存器（第 1 个 → `rd8`/`rb8`/`rf8` 起**递增**：第 2 个 → `rd9`…）；**每 bank 上限 K=8**（`rd8–rd15`/`rb8–rb15`/`rf8–rf15`）；任一 bank 超 8（或无法承载）⇒ **`sret`**（隐藏指针经 `rb16`，其后地址参数自 `rb17` 起） | [DADAO-21 §返回值 §多返回值][DADAO-21 §返回值 §聚合类型返回值] |
| 2 | red zone（128B） | **不采用** | 用户 2026-10-08 裁定（v5 `spec/` 未提及）[spec-decision] |
| 3 | `i128` 传参 / 返回 | **不支持**（保持 `Excluded`） | 用户 2026-10-08 裁定；spec 未规定。[spec-decision] |

**M6 另收口（原 §5 高级 ABI 边界，非 §6 未决项）**：**聚合传参 / HFA / HPA**——用户 2026-10-09 裁定「B」后已写入 `spec/DADAO-21 §传参 §聚合类型参数`，口径见 **§6.4**。

### §6.1 多返回值 / 聚合返回值（原 #1）——`LLVM-062t` 实现依据

- **返回寄存器**：整数 `rd8`、指针 `rb8`、浮点 `rf8`（各 bank 低编号区 `rd8–rd15` / `rb8–rb15` / `rf8–rf15`），**与参数寄存器区（`rd16–rd31` / `rb16–rb31` / `rf16–rf31`）不重叠**。[DADAO-21 §返回值]
- **顺序（ABI 可观测语义）**：多返回值 / 聚合按**声明顺序**依次占用返回寄存器，各 bank **独立、自 8 递增**：第 1 个 → `rd8`（整数）/`rb8`（指针）/`rf8`（浮点），第 2 个 → `rd9`/`rb9`/`rf9`，依次类推。例：`(int x, int y, double* p)` ⇒ `x=rd8`、`y=rd9`、`p=rb8`；`(int a, double* p, float f)` ⇒ `a=rd8`、`p=rb8`、`f=rf8`。[DADAO-21 §返回值 §多返回值]
- **容量口径（K=8，每 bank 计数）**：任一 bank 的返回值占用**至多 8 个**（`rd8–rd15` / `rb8–rb15` / `rf8–rf15`）；**任一 bank 超过 8 个**，或无法用该规则承载 ⇒ **`sret`（隐藏指针）**。原「聚合总大小 ≤2 字 / >2 字（>64 位）」阈值表述**以本「每 bank K=8 计数」为准**（用户 2026-10-09 裁定「K=8」「最多 8 个寄存器」）。[DADAO-21 §返回值 §多返回值][DADAO-21 §返回值 §聚合类型返回值]
- **`sret` 隐藏指针位置**：作为**隐藏的第一个地址参数**经 **`rb16`** 传入 callee；callee 将返回值写入 `sret_ptr` 指向的地址，返回时 **`rb16` 仍保存该地址**供 caller 读取（⇒ 该隐藏参数占用 `rb16`，后续地址参数自 **`rb17`** 起计数）。[DADAO-21 §返回值 §聚合类型返回值]

### §6.2 red zone（128B）（原 #2）

- **结论**：**不采用** red zone。leaf 函数**不得**假定 `rbsp`（`rb1`）之下存在保留区；callee 除本函数已分配的帧空间外，不拥有 `rbsp` 之下的内存。[spec-decision]
- **来源**：用户 2026-10-08 裁定「不采用」（与其保持一致：v5 `spec/` 未提及）。v5 `spec/DADAO-21-ABI` / `DADAO-11-AEE` 全文无 `red zone` / 128B 保留区定义。[spec-decision]

### §6.3 `i128` 传参 / 返回（原 #3）

- **结论**：**不支持 `i128`**（保持 `Excluded`）。实现**不得**为 `i128` 生成传参 / 返回寄存器约定或 `sret` 约定；遇 `i128` 参数 / 返回值时应显式失败，不得静默降级。[spec-decision]
- **来源**：用户 2026-10-08 裁定「不支持」（保持 `Excluded`）。spec `§标量类型返回值` 未规定 `i128` 约定。[DADAO-21 §返回值 §标量类型返回值]
- **注**：`DataLayout` 的 `i128:128`（§4.9，C9）是**存储布局**事实，与传参 / 返回约定无关，不受本项影响。[ADR-0018（C9）]

### §6.4 聚合传参 / HFA / HPA（M6 口径，`LLVM-062t` / `LLVM-066t` 实现依据）

- **统一槽位上限（用户 2026-10-09 裁定「B」）**：聚合类型（含**通用聚合**、**HFA**、**HPA**）传参**最多消耗 8 个寄存器槽位（64 字节）**；超过上限即改用**间接指针**。[DADAO-21 §传参 §聚合类型参数]
  - **HFA**（同质浮点，全部叶子字段为同一浮点类型）：经 **RF bank** 传递，每个叶子字段占 **1 个 RF 槽位**，自 `rf16` 起递增；叶子字段总数 ≤ 8（占 `rf16–rf23`）。[DADAO-21 §传参 §聚合类型参数]
  - **HPA**（同质指针，全部叶子字段为指针类型，指向的具体类型可不同）：经 **RB bank** 传递，每个叶子字段占 **1 个 RB 槽位**，自 `rb16` 起递增；叶子字段总数 ≤ 8（占 `rb16–rb23`）。[DADAO-21 §传参 §聚合类型参数]
  - **通用聚合**（非 HFA/HPA，跨 bank）：`≤ 64 字节` ⇒ 拆分为 **1–8 个 8 字节块**放入 **RD bank**（高位块先入高寄存器）；**`> 64 字节` ⇒ 间接指针**（caller 在栈上分配临时空间，callee 经 RB bank 中的指针访问）。[DADAO-21 §传参 §聚合类型参数]
- **判定流程不变**：flatten（递归展开嵌套 struct；`union` 直接判定为不满足）、同质检查、计数检查（叶子字段总数 ≤ 8）。聚合对齐、`> 8B` 聚合变参的拆分规则不变（后二者不属本节）。[DADAO-21 §传参 §聚合类型参数]
- **与返回口径一致**：聚合返回同以「**每 bank 至多 8**」为容量口径（§6.1），聚合传参 8 槽位上限与其统一。[DADAO-21 §返回值 §多返回值][DADAO-21 §返回值 §聚合类型返回值]
- **实现归属**：通用（整数）聚合传参 → `LLVM-062t`；HFA / HPA（RF/RB）传参 → `LLVM-066t`。[DADAO-21 §传参 §聚合类型参数]
- **来源**：用户 2026-10-09 裁定原话「hfa/hpa也调整为：最多消耗 8个寄存器槽位（64字节）」+ 追问通用聚合后答「B，补充spec」（B = 通用/HFA/HPA 统一 8 槽位/64B）；已写入 `spec/DADAO-21 §传参 §聚合类型参数`（本任务同一变更内改册 + 同步只读锁 `sha256`）。[DADAO-21 §传参 §聚合类型参数]

---

## 附录 A：来源对照

| 本合约 § | 内容 | spec/ 来源 |
|----------|------|-----------|
| §1.1–§1.5 | 寄存器角色（RD/RB/RF/RA） | `DADAO-21-ABI §寄存器规范` |
| §1.5 | RA 高 16 位/低 48 位模型 | `DADAO-11-AEE §返回地址栈` |
| §1.6 | 可分配 / 不可分配集合 | `DADAO-21-ABI §寄存器规范` + `contract-isa.md §6` |
| §1.7 | 大端序 / 指针宽度 | `DADAO-21-ABI §数据表示` |
| §2.1 | SP/FP、栈向下增长 | `DADAO-21-ABI §寄存器规范`、`DADAO-21-ABI §函数调用规范 §The Stack Frame` |
| §2.2 | `call` 时 SP 8B 对齐 | `DADAO-21-ABI §传参 §栈溢出规则` |
| §2.3 | `call`/`ret` 与 RegRAS | `SimRISC-06 §函数调用`、`§函数返回`；`contract-isa.md §5.4–§5.6` |
| §3 | 机器可读事实（`contracts/abi.yaml`） | `DADAO-21-ABI §寄存器规范`、`§函数调用规范`；`ADR-0018`（C4/C6） |
| §4.1 | 参数寄存器分配（三 bank、独立计数、类型→bank） | `DADAO-21-ABI §传参 §参数寄存器` |
| §4.2 | 标量参数提升（<8B → 8B，符号/零扩展） | `DADAO-21-ABI §传参 §标量参数`；`ADR-0018`（C4） |
| §4.3 | 寄存器溢出 / 栈溢出区（全局声明序单栈区、每槽 8B） | `DADAO-21-ABI §传参 §栈溢出规则`；`ADR-0018`（C4） |
| §4.4 | 返回值（整数→rd8、指针→rb8；窄返回 callee 扩展） | `DADAO-21-ABI §返回值 §标量类型返回值`；`ADR-0018`（C5） |
| §4.5 | callee-saved / caller-saved / CSR | `DADAO-21-ABI §寄存器规范 §RD寄存器`、`§RB寄存器`；`ADR-0018`（C6/C7） |
| §4.6 | `call` `Defs` / `getCallPreservedMask` / `ret` | `ADR-0018`（C16）；`DADAO-21-ABI §返回值 §标量类型返回值` |
| §4.7 | 栈帧布局 / FP 策略 | `DADAO-21-ABI §函数调用规范 §The Stack Frame`；`ADR-0018`（C7） |
| §4.8 | prologue / epilogue（SP-only + FP 两套） | `DADAO-21-ABI §函数调用规范 §The Stack Frame`、`§传参 §栈溢出规则`；`ADR-0018`（C7） |
| §6.4 | 聚合传参 / HFA / HPA（统一 ≤8 槽位 / 64B；>64B 间接指针） | `DADAO-21-ABI §传参 §聚合类型参数` |
