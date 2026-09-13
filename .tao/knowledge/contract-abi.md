# ABI 合约（M1 最小 ABI 事实）

> **版本：0.9.2** [DADAO-21 §版本][DADAO-11 §版本]
>
> **来源**：`spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）、`spec/DADAO-11-AEE-应用程序运行环境.md`（0.9.2）；指令语义与寄存器模型基础引用 `.tao/knowledge/contract-isa.md`（0.5.3）。
>
> **M1 范围**：最小 ABI 事实——寄存器角色、`SP=rb1`、栈向下增长 / `call` 时 SP 8B 对齐、`call`/`ret` 与 RegRAS 的关系。供 test machine（`SPEC-006t`）与 M1 集成使用。
>
> **`Deferred to M2`**：完整调用约定（参数寄存器分配、返回值、栈帧布局、三 bank 共享溢出区、prologue/epilogue）——服务 M2 BasicCodeGen；本合约**不提取**其规范内容（见 §4）。
>
> **`Excluded from M1`**：高级 ABI（varargs / HFA / HPA / 聚合传参 / 多返回值）与浮点 RF（见 §5）。
>
> **来源标注**：每条规范性断言句末以 `[DADAO-21 §章节名]` / `[DADAO-11 §章节名]` / `[SimRISC-0X §章节名]` 标注 spec/ 来源，不写行号；无来源的推论标 `[OPEN]`。
>
> **说明**：本合约由 spec/ 归一化投影而来，面向实现；与 spec/ 冲突时阻断实现，走变更流程（见 `.tao/knowledge/contract-authoring.md`）。

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
| rd2–rd7 | — | reserved（编译器不得分配使用） | `-` |
| rd8–rd15 | rdt0–rdt7 | temporary regs | No |
| rd16–rd31 | rda0–rda15 | temporary regs | No |
| rd32–rd63 | — | callee saved regs | Yes |

### §1.3 RB 寄存器角色

[DADAO-21 §寄存器规范 §RB寄存器]

| 寄存器 | ABI 名 | 角色 | Callee-saved |
|--------|--------|------|--------------|
| rb0 | rbip | instruction pointer（PC，只读） | `-` |
| rb1 | rbsp | stack pointer（SP） | Yes |
| rb2 | rbfp | frame pointer（FP） | Yes |
| rb3 | rbgp | global pointer | `-` |
| rb4 | rbtp | thread pointer | `-` |
| rb5–rb7 | — | reserved | `-` |
| rb8–rb15 | rbt0–rbt7 | temporary regs | No |
| rb16–rb31 | rba0–rba15 | temporary regs | No |
| rb32–rb63 | — | callee saved regs | Yes |

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
| RD | rd8–rd15、rd16–rd31、rd32–rd63 | [DADAO-21 §寄存器规范 §RD寄存器] |
| RB | rb8–rb15、rb16–rb31、rb32–rb63 | [DADAO-21 §寄存器规范 §RB寄存器] |
| RF | （无） | [contract-isa.md §6] |

**不可分配**：

| 寄存器 | 原因 | 来源 |
|--------|------|------|
| rd0 | 硬连零（Immutable） | [DADAO-21 §寄存器规范 §RD寄存器] |
| rd1 | Callee-saved 栏为 `-`，M1 保守不分配 | `[OPEN]` |
| rd2–rd7 | reserved（编译器不得分配使用） | [DADAO-21 §寄存器规范 §RD寄存器] |
| rb0 | PC | [DADAO-21 §寄存器规范 §RB寄存器] |
| rb1 | SP（帧管理专用） | [DADAO-21 §寄存器规范 §RB寄存器] |
| rb2 | FP（帧管理专用） | [DADAO-21 §寄存器规范 §RB寄存器] |
| rb3 | Callee-saved 栏为 `-`，M1 保守不分配 | `[OPEN]` |
| rb4 | Callee-saved 栏为 `-`，M1 保守不分配 | `[OPEN]` |
| rb5–rb7 | reserved | [DADAO-21 §寄存器规范 §RB寄存器] |
| ra0–ra63 | 由 `call`/`ret` 管理，非通用可分配 | [DADAO-21 §寄存器规范 §RA寄存器] |
| rf0–rf63 | `Excluded from M1` | [contract-isa.md §6] |

> `[OPEN]`：`rd1`/`rb3`/`rb4` 的 Callee-saved 分类在 spec 中为 `-`（未分类）。M1 冻结保守策略为**不分配**（non-allocatable）；其保存语义（caller-saved / callee-saved）**未冻结**，留 M2 前解决。[DADAO-21 §寄存器规范 §RD寄存器][DADAO-21 §寄存器规范 §RB寄存器]

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
- `FP = rb2`（`rbfp`）；帧指针的使用方式（可选）属完整调用约定，`Deferred to M2`（见 §4）。[DADAO-21 §函数调用规范 §The Stack Frame]

### §2.2 `call` 时 SP 对齐

- `call` 指令执行时 `sp` 必须 **8 字节对齐**。[DADAO-21 §传参 §栈溢出规则]
- M1 标量调用路径不涉及变参保存区；变参保存区对齐属 `Deferred to M2`（见 §4）。[DADAO-21 §传参 §栈溢出规则]

### §2.3 `call`/`ret` 与 RegRAS

- `call` 计算返回地址并压入 `ra63`（RegRAS 栈顶）；`ret` 从 `ra63` 弹出返回地址并跳转。[SimRISC-02 §函数调用][SimRISC-02 §函数返回]
- `ra63` 高 16 位为返回地址引用计数（首次压栈设为 1，递归调用递增），低 48 位为返回地址。[SimRISC-02 §函数调用]
- 正常 leaf / 非 leaf 函数调用**无需软件保存/恢复 RA 寄存器**（由硬件自动压/弹）。[DADAO-21 §寄存器规范 §RA寄存器]
- 完整压栈/弹栈流程（RegRAS/MemRAS、三分支、RASOF/RASUF 精确异常）见 `contract-isa.md §5.4–§5.6`，本合约不重复定义。[SimRISC-00 §压栈流程（call 指令）][SimRISC-00 §弹栈流程（ret 指令）]

---

## §3 M1 机器可读事实

M1 ABI 事实的机器可读形式见 `verif/abi.yaml`（`version: "0.9.2"`），其 M1 字段与本节 / §1 一致。其中 `registers` 表为逐寄存器分类的**权威来源**（`rb1`/`rb2` 依 spec 标 `callee_saved: true`）；`callee_saved` / `reserved_registers` 为便于消费者读取的**派生分类索引**——`callee_saved` 索引只给出各 bank 的**通用 callee-saved 块（32–63）**（对 `rd`/`rb` 与 `allocatable` 一致；**RF 整体 `Excluded from M1`、`allocatable.rf` 为空，其块仅作 spec 事实登记**），不含 SP/FP 等帧管理专用寄存器。`verif/abi.yaml` 中 `deferred_to_m2` / `excluded_from_m1` 节仅为 M2 参考与边界索引，**不属 M1 规范性事实**。

---

## §4 `Deferred to M2`（完整调用约定，本合约不提取）

以下内容服务 M2 BasicCodeGen，**不属 M1 规范性事实**。本合约仅登记主题与 spec/ 出处，**不提取其规范内容**：

| 主题 | spec/ 出处 | 状态 |
|------|-----------|------|
| 参数寄存器分配（三 bank 独立计数、从 16 开始、类型→bank、`read(fd,buf,count)` 示例） | [DADAO-21 §传参 §参数寄存器] | `Deferred to M2` |
| 标量参数提升（<8B → 8B，符号/零扩展） | [DADAO-21 §传参 §标量参数] | `Deferred to M2` |
| 三 bank 共享溢出区（按全局声明顺序、每槽 8B、`sp+0` 起） | [DADAO-21 §传参 §栈溢出规则] | `Deferred to M2` |
| 返回值（标量整数→rd31、指针→rb31、浮点→rf31） | [DADAO-21 §返回值 §标量类型返回值] | `Deferred to M2` |
| 栈帧布局（`rbfp+8n+8` … `rbsp`） | [DADAO-21 §函数调用规范 §The Stack Frame] | `Deferred to M2` |
| prologue/epilogue（SP-only 与 FP 两套对称、可汇编序列） | [DADAO-21 §函数调用规范] | `Deferred to M2` |
| 系统调用规范（`trap`、RD15 调用号、返回值 RD31） | [DADAO-21 §系统调用规范] | `Deferred to M2`（不属 M1 最小 ABI 事实） |

> 撰写 M2 内容时，指令助记符必须使用 0.5.3 命名（见 `contract-isa.md`），不得沿用 0.4.1 旧助记符。

---

## §5 `Excluded from M1`（高级 ABI，本合约不提取）

| 主题 | spec/ 出处 | 状态 |
|------|-----------|------|
| 可变参数（`va_list` / 保存区 / `va_start` / `va_arg`） | [DADAO-21 §可变参数] | `Excluded from M1` |
| HFA（同质浮点聚合，RF bank） | [DADAO-21 §传参 §聚合类型参数] | `Excluded from M1` |
| HPA（同质指针聚合，RB bank） | [DADAO-21 §传参 §聚合类型参数] | `Excluded from M1` |
| 聚合传参（≤32B 拆 RD 块 / >32B 间接指针） | [DADAO-21 §传参 §聚合类型参数] | `Excluded from M1` |
| 聚合返回值（hidden sret，指针经 rb16） | [DADAO-21 §返回值 §聚合类型返回值] | `Excluded from M1` |
| 多返回值 | [DADAO-21 §返回值 §多返回值] | `Excluded from M1`（spec 内部冲突，见 §6） |
| 浮点 RF（寄存器角色除外） | [contract-isa.md §6] | `Excluded from M1` |

---

## §6 `[OPEN]` 汇总

| # | 项 | 说明 | 来源 |
|---|----|------|------|
| 1 | `rd1`/`rb3`/`rb4` 的 Callee-saved 分类 | spec 栏为 `-`；M1 保守不分配，保存语义未冻结 | `[OPEN]` [DADAO-21 §寄存器规范] |
| 2 | 窄返回值扩展规则 | spec §返回值 未规定 callee 扩展 / caller 不截断；M1 不适用（返回值整体 `Deferred to M2`） | `[OPEN]` [DADAO-21 §返回值] |
| 3 | 多返回值声明顺序 | spec 声明顺序规则与示例存在内部冲突；M1 标 Excluded | `[OPEN]` [DADAO-21 §返回值 §多返回值] |
| 4 | red zone（128B） | v5 `spec/DADAO-21-ABI` 未提及；不属 M1 事实，留 M2 确认 | `[OPEN]`（无 spec 来源） |
| 5 | 帧指针省略策略 | spec 允许用 `rbsp` 直接访问帧（`rbfp` 可选）；M1 不规定 | `[OPEN]` [DADAO-21 §函数调用规范 §The Stack Frame] |

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
| §2.3 | `call`/`ret` 与 RegRAS | `SimRISC-02 §函数调用`、`§函数返回`；`contract-isa.md §5.4–§5.6` |
