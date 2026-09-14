# Spec 冻结影响矩阵（Impact Matrix）

> **用途**：spec/ADR/合约章节发生变更时，据此快速定位需要回归的下游合约、机器可读文件与 M1 实现目标。逐节覆盖，未覆盖的章节即变更盲区。
>
> **冻结基线**：规范版本以 `README.md`「当前版本号」表为唯一来源（SimRISC 0.5.3 / AEE·ABI 0.9.2 / SEE·SBI 0.7.1 / HEE·HBI 0.1.2）；权威 artifact 为 `SPEC-002t`~`SPEC-009t` 的已 Accepted/已验证产出：`contract-isa.md`、`contracts/opcodes.yaml`、`contract-abi.md`、`contracts/abi.yaml`、`adr-0003-object-abi.md`、`adr-0004-test-machine.md`、`contract-elf.md`、`contracts/legality_rules.yaml`。
>
> **引用约定**：本矩阵只用章节号（`§N`、`§DN`、`§A.N`）与 ADR 决策点，**不写行号**。

## 列说明

| 列 | 含义 |
|----|------|
| 规格来源 | 归一化合约/ADR 的章节（行身份）；括号内为其上游 spec/ 来源章节 |
| 依赖此节的合约/文件 | 仓库内直接依赖该节的合约、机器可读数据与工具脚本 |
| 下游实现目标 | 需要实现该节规则的 M1 组件 |

## 实现目标标签（仅 M1）

| 标签 | 含义 |
|------|------|
| `LLVM MC` | `llvm` 模块的汇编器/反汇编器（AsmParser / CodeEmitter / MC 层） |
| `QEMU CPU` | `qemu` 模块的指令解码与执行语义（`target/dadao`） |
| `QEMU machine` | `qemu` 模块的测试机模型（内存映射、复位、exit port、fault→退出码、加载协议） |
| `vectors` | `testcases` 模块的独立测试向量（encoding/legality/semantic/boundary/overlap） |
| `harness` | 驱动 MC/QEMU 并断言 `$?` 的执行与集成脚本 |

**M1 外**（LLVM CodeGen、gem5、Sail）**不列为实现目标**，统一标 `Deferred（M1 外）`。合约中 `Deferred to M2` / `Excluded from M1` 的章节同样标 `Deferred（M1 外）`；但 `Excluded from M1` 的编码在 M1 机器上执行会触发 ILLI，该**机器行为**仍属 `QEMU CPU`。

---

## 1. ISA — `contract-isa.md`（来源 SimRISC-00..04）

### §1 寄存器模型

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §1.1 寄存器组`（SimRISC-00 §寄存器） | `contract-abi.md §1.1`；`contracts/opcodes.yaml`（字段 `bank`）；`contract-elf.md §1.2`（64 位字长依据） | LLVM MC、QEMU CPU |
| `contract-isa.md §1.2 寄存器编号编码`（SimRISC-00 §指令域说明） | `contracts/opcodes.yaml`（`fields[].bits`）；`tools/spec/validate_encoding.py` | LLVM MC、QEMU CPU |
| `contract-isa.md §1.3.1 rd0`（SimRISC-00 §数据寄存器；SimRISC-01 §rd0 为目的寄存器约定） | `contracts/legality_rules.yaml`（`rd_dest_rd0`、`dual_dest_*`）；`contract-abi.md §1.2`；`adr-0004 §D5.1` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §1.3.2 rb0`（SimRISC-00 §基址寄存器；SimRISC-02 §rb0 为目的寄存器约定） | `contracts/legality_rules.yaml`；`contract-abi.md §1.3`；`adr-0004 §D2.1`、`§D5.1` | LLVM MC、QEMU CPU、QEMU machine、vectors |
| `contract-isa.md §1.3.3 rf0（FCSR）`（SimRISC-00 §浮点状态寄存器） | `contract-abi.md §1.4`；`adr-0004 §D2.1`（复位常量） | QEMU machine（复位值）；FCSR 指令语义 `Deferred（M1 外）` |
| `contract-isa.md §1.3.4 ra0–ra63`（SimRISC-00 §返回地址栈） | `contract-isa.md §5.6`；`contract-abi.md §1.5`、`§2.3`；`contracts/legality_rules.yaml`；`adr-0004 §D2.1`、`§D5.5` | LLVM MC、QEMU CPU、QEMU machine、vectors |
| `contract-isa.md §1.4 数据表示`（SimRISC-00 §数据表示、§原始数据类型） | `contract-abi.md §1.7`；`contracts/abi.yaml`（`data_layout`）；`contract-elf.md §1.2` | LLVM MC、QEMU CPU |
| `contract-isa.md §1.5 存储模型`（SimRISC-00 §基址寄存器；SimRISC-02 §控制流指令） | `contract-elf.md §1.2`、`§5.2`；`contract-abi.md §1.7`；`adr-0004 §D1` | LLVM MC、QEMU CPU、QEMU machine |
| `contract-isa.md §1.6 端序`（SimRISC-00 §指令设计） | `contract-elf.md §1.2`；`contract-abi.md §1.7`；`contracts/abi.yaml`（`data_layout.endianness`） | LLVM MC、QEMU CPU |

### §2 指令编码

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §2.1 指令格式`（SimRISC-00 §指令设计） | `contract-elf.md §1.2`、`§5.1`；`contracts/opcodes.yaml`；`adr-0004 §D5.4` | LLVM MC、QEMU CPU、QEMU machine |
| `contract-isa.md §2.2 指令域`（SimRISC-00 §指令域说明） | `contracts/opcodes.yaml`；`tools/spec/validate_encoding.py` | LLVM MC、QEMU CPU |
| `contract-isa.md §2.3 操作数格式`（SimRISC-00 §指令域说明） | `contracts/opcodes.yaml`（`format`）；`contract-elf.md §2`（Deferred 场景登记） | LLVM MC、QEMU CPU |
| `contract-isa.md §2.4 Wyde-Position 编码`（SimRISC-00 §指令域说明） | `contracts/opcodes.yaml`；`contract-elf.md §2`（Deferred 场景登记） | LLVM MC、QEMU CPU |
| `contract-isa.md §2.5 数据位宽后缀`（SimRISC-00 §指令域说明） | `contracts/opcodes.yaml`（`mnemonic` 变体）；`tools/spec/generate_opcodes.py` | LLVM MC、vectors |
| `contract-isa.md §2.6 操作数顺序约定`（SimRISC-00 §指令域说明） | `contracts/opcodes.yaml`（`fields[].role`）；`contract-abi.md §4`（Deferred） | LLVM MC |
| `contract-isa.md §2.7 QFC 主表`（SimRISC-00 §SimRISC QFC） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml`（UNDI）；`tools/spec/check_qfc_coverage.py`；`adr-0004 §D5.2` | LLVM MC、QEMU CPU、QEMU machine、vectors |
| `contract-isa.md §2.8 MISC 子表机制`（SimRISC-00 §指令域说明、各 MISC 子表） | `contracts/opcodes.yaml`；`tools/spec/check_qfc_coverage.py`、`generate_opcodes.py` | LLVM MC、QEMU CPU |
| `contract-isa.md §2.9 保留编码`（SimRISC-00 §SimRISC QFC；SimRISC-04 §非法指令） | `contracts/legality_rules.yaml`；`adr-0004 §D5.2`、`§D5.1` | LLVM MC、QEMU CPU、vectors |

### §3 标量整数指令

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §3.1 算术运算`（§3.1.1 加减 rrrr、§3.1.2 加减固定位宽、§3.1.3 自增自减、§3.1.4 乘法 rrrr、§3.1.5 乘除余固定位宽）（SimRISC-01 §加减操作、§自增自减、§乘除操作） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml`（除零、`INT_MIN ÷ −1`）；`adr-0004 §D5.1` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §3.2 比较操作`（§3.2.1 立即数比较、§3.2.2 寄存器比较）（SimRISC-01 §比较操作） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §3.3 逻辑运算`（SimRISC-01 §Logic operators：逻辑运算） | `contracts/opcodes.yaml` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §3.4 位操作`（§3.4.1 移位、§3.4.2 符号/零扩展）（SimRISC-01 §Bit manipulating：位操作指令） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml`（`shamt > N`、`hd > N`）；`adr-0004 §D5.3`（SBZ） | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §3.5 条件赋值`（SimRISC-01 §条件赋值：Conditional Assignment） | `contracts/opcodes.yaml`；`contract-isa.md 附录 B.2` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §3.6 立即数设置`（SimRISC-01 §立即数常数赋值：Immediate constant） | `contracts/opcodes.yaml`；`contract-elf.md §2`（Deferred 地址构造登记） | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §3.7 块赋值 rd2rd`（SimRISC-01 §寄存器组之间块赋值） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §3.8 伪指令（标量整数）`（SimRISC-01 §set.rd 伪指令、§not 伪指令、§neg 伪指令；SimRISC-00 §伪指令） | `contracts/opcodes.yaml`（展开形式）；`contract-isa.md §3.1–§3.7` | LLVM MC（汇编器展开）、vectors |

### §4 地址/内存指令（RD/RB/RA）

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §4.1 存取 RD 寄存器`（§4.1.1 单 load/store、§4.1.2 多 load/store；SimRISC-01 §存取类指令、§存取RD寄存器） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml`（MALIGN/ILLI）；`contract-elf.md §5.1`（对齐）；`adr-0004 §D4`、`§D5.6` | LLVM MC、QEMU CPU、QEMU machine、vectors |
| `contract-isa.md §4.2 存取 RB 寄存器`（SimRISC-02 §存取RB寄存器） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml`；`contract-elf.md §5.1`；`adr-0004 §D4`、`§D5.6` | LLVM MC、QEMU CPU、QEMU machine、vectors |
| `contract-isa.md §4.3 块赋值`（SimRISC-02 §寄存器组之间块赋值） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §4.4 RB 立即数设置`（SimRISC-02 §立即数常数赋值：Immediate constant） | `contracts/opcodes.yaml`；`contract-isa.md §2.4` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §4.5 RB 算术运算`（§4.5.1 加减、§4.5.2 自增自减）（SimRISC-02 §加减操作、§自增自减） | `contracts/opcodes.yaml` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §4.6 RB 比较`（SimRISC-02 §比较操作） | `contracts/opcodes.yaml`；`contract-isa.md 附录 B` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §4.7 PC 相对寻址`（SimRISC-02 §PC相对寻址） | `contracts/opcodes.yaml`；`contract-elf.md §2`（Deferred `rela.si` 场景登记） | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §4.8 伪指令（地址/内存）`（SimRISC-02 §set.rb 伪指令） | `contracts/opcodes.yaml`（展开形式）；`contract-isa.md §4.4` | LLVM MC、vectors |
| `contract-isa.md §4.9 RA 寄存器存取与块赋值`（§4.9.1 单 load/store、§4.9.2 多 load/store、§4.9.3 RA↔RD 块赋值）（SimRISC-02 §存取RA寄存器、§寄存器组之间块赋值） | `contracts/opcodes.yaml`；`contracts/legality_rules.yaml`；`contract-abi.md §1.5`；`adr-0004 §D5.5` | LLVM MC、QEMU CPU、QEMU machine、vectors |

### §5 控制流

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §5.1 通用约定`（SimRISC-02 §控制流指令） | `contract-elf.md §2`（Deferred）；`adr-0004 §D6.4` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §5.2 条件跳转指令`（§5.2.1 双寄存器比较跳转、§5.2.2 单寄存器条件跳转、§5.2.3 RB 条件跳转）（SimRISC-02 §条件跳转指令） | `contracts/opcodes.yaml`；`contract-elf.md §2`（Deferred 分支场景登记）；`contract-isa.md 附录 B` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §5.3 无条件跳转指令`（SimRISC-02 §无条件跳转指令） | `contracts/opcodes.yaml`；`contract-elf.md §2`（Deferred）；`adr-0004 §D6.4`（trampoline 绝对跳转） | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §5.4 函数调用`（SimRISC-02 §函数调用） | `contract-abi.md §2.3`；`contracts/abi.yaml`（`call_ret`）；`adr-0004 §D5.5` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §5.5 函数返回`（SimRISC-02 §函数返回） | `contract-abi.md §2.3`；`contracts/abi.yaml`（`call_ret`）；`adr-0004 §D5.5` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §5.6 压栈/弹栈流程`（§5.6.1 压栈、§5.6.2 弹栈）（SimRISC-00 §压栈流程（call 指令）、§弹栈流程（ret 指令）） | `contract-abi.md §2.3`；`contracts/legality_rules.yaml`（RASOF/RASUF）；`adr-0004 §D5.5` | QEMU CPU、vectors |
| `contract-isa.md §5.7 伪指令（控制流）`（SimRISC-02 §return 伪指令） | `contracts/opcodes.yaml`（展开形式） | LLVM MC、vectors |

### §6 浮点指令 — Excluded from M1

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §6 浮点指令`（SimRISC-03 全部） | `contract-abi.md §1.4`、`§5`；`contracts/opcodes.yaml`（`excluded_m1`）；`adr-0004 §D5.1` | QEMU CPU（执行 RF 编码触发 ILLI）；浮点语义 `Deferred（M1 外）` |

### §7 系统指令（M1 所需）

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §7.1 占位指令 swym`（SimRISC-04 §占位指令） | `contracts/opcodes.yaml` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §7.2 非法指令 illi`（SimRISC-04 §非法指令） | `contracts/legality_rules.yaml`；`adr-0004 §D5.1`、`§D6.3` | LLVM MC、QEMU CPU、QEMU machine、vectors、harness |
| `contract-isa.md §7.3 fence 指令`（SimRISC-04 §fence指令） | `contracts/opcodes.yaml`；`adr-0004 §D5.3`（SBZ 字段） | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md §7.4 LR-SC 原子指令 — Excluded`（SimRISC-04 §LR-SC指令） | `contracts/opcodes.yaml`（`excluded_m1`）；`contracts/legality_rules.yaml`；`adr-0004 §D5.1` | QEMU CPU（执行即 ILLI）；原子语义 `Deferred（M1 外）` |
| `contract-isa.md §7.5 特权 cfx 系统指令 — Excluded`（SimRISC-04 §特权指令：§陷入指令、§退出指令、§寄存器传输指令、§SRAM块传输指令） | `contracts/opcodes.yaml`（`excluded_m1`）；`contracts/legality_rules.yaml`；`adr-0004 §D5.1` | QEMU CPU（执行即 ILLI）；特权语义 `Deferred（M1 外）` |
| `contract-isa.md §7.6 伪指令 nop`（SimRISC-04 §nop 伪指令） | `contracts/opcodes.yaml`（展开形式） | LLVM MC、vectors |

### §8 NOP 与保留编码

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §8.1 NOP`（SimRISC-04 §nop 伪指令） | `contracts/opcodes.yaml` | LLVM MC、vectors |
| `contract-isa.md §8.2 保留编码（UNDI）`（SimRISC-00 §SimRISC QFC） | `contracts/legality_rules.yaml`；`adr-0004 §D5.2` | QEMU CPU、QEMU machine、vectors、harness |
| `contract-isa.md §8.3 全零指令（ILLI）`（SimRISC-04 §非法指令） | `contracts/legality_rules.yaml`；`adr-0004 §D5.1` | QEMU CPU、QEMU machine、vectors、harness |

### §9 异常总结

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md §9.1 ILLI 触发场景`（SimRISC-01/02/04 各节） | `contracts/legality_rules.yaml`；`adr-0004 §D5.1` | QEMU CPU、QEMU machine、vectors、harness |
| `contract-isa.md §9.2 精确异常承诺`（SimRISC-00 §返回地址栈；SimRISC-01 §乘除操作） | `contracts/legality_rules.yaml`；`adr-0004 §D4`、`§D5.5` | QEMU CPU、QEMU machine、vectors |

### 附录 A / B

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-isa.md 附录 A.1–A.6 M1 指令编码清单`（SimRISC-00 §SimRISC QFC、各 MISC 子表） | `contracts/opcodes.yaml`；`tools/spec/validate_encoding.py`、`generate_opcodes.py`、`check_qfc_coverage.py` | LLVM MC、QEMU CPU、vectors |
| `contract-isa.md 附录 A.7 Excluded from M1 编码清单`（SimRISC-00 §SimRISC QFC、§MISC-AMO 指令编码、§MISC-octa指令编码） | `contracts/opcodes.yaml`（`excluded_m1`）；`contracts/legality_rules.yaml` | QEMU CPU（执行即 ILLI）；完整语义 `Deferred（M1 外）` |
| `contract-isa.md 附录 B 条件标志参考`（SimRISC-00 §标识位说明；SimRISC-01 §条件赋值；SimRISC-02 §条件跳转指令） | `contracts/opcodes.yaml`；`contract-isa.md 附录 B.3`（条件跳转特例） | LLVM MC、QEMU CPU、vectors |

---

## 2. ABI — `contract-abi.md`（来源 DADAO-11 AEE、DADAO-21 ABI）

### §1 寄存器角色（M1）

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-abi.md §1.1 寄存器组`（DADAO-21 §寄存器规范） | `contracts/abi.yaml`（`registers`）；`contract-isa.md §1.1` | LLVM MC、QEMU CPU、vectors |
| `contract-abi.md §1.2 RD 寄存器角色`（DADAO-21 §寄存器规范 §RD寄存器） | `contracts/abi.yaml`（`registers`）；`contract-isa.md §1.3.1` | LLVM MC、QEMU CPU、vectors |
| `contract-abi.md §1.3 RB 寄存器角色`（DADAO-21 §寄存器规范 §RB寄存器） | `contracts/abi.yaml`（`registers`）；`contract-isa.md §1.3.2`；`adr-0004 §D1`、`§D6.4`（SP） | LLVM MC、QEMU CPU、QEMU machine、vectors |
| `contract-abi.md §1.4 RF 寄存器角色`（DADAO-21 §寄存器规范 §RF寄存器） | `contracts/abi.yaml`（`allocatable.rf` 为空）；`contract-isa.md §6` | `Deferred（M1 外）`（M1 不分配/不存取/不运算 RF） |
| `contract-abi.md §1.5 RA 寄存器角色`（DADAO-21 §寄存器规范 §RA寄存器；DADAO-11 §返回地址栈） | `contract-isa.md §1.3.4`、`§5.6`；`contracts/abi.yaml` | LLVM MC、QEMU CPU、vectors |
| `contract-abi.md §1.6 可分配 / 不可分配集合`（DADAO-21 §寄存器规范） | `contracts/abi.yaml`（`allocatable`、`reserved_registers`） | LLVM MC |
| `contract-abi.md §1.7 基础数据布局`（DADAO-21 §数据表示） | `contracts/abi.yaml`（`data_layout`）；`contract-elf.md §1.2`、`§5.1` | LLVM MC、QEMU CPU、QEMU machine |

### §2 栈与调用（M1）

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-abi.md §2.1 栈指针与栈方向`（DADAO-21 §寄存器规范 §RB寄存器、§函数调用规范 §The Stack Frame） | `contracts/abi.yaml`（`stack`）；`adr-0004 §D1`、`§D6.4` | LLVM MC、QEMU CPU、QEMU machine、harness |
| `contract-abi.md §2.2 call 时 SP 对齐`（DADAO-21 §传参 §栈溢出规则） | `contracts/abi.yaml`（`stack.stack_alignment`） | LLVM MC、QEMU CPU、vectors |
| `contract-abi.md §2.3 call/ret 与 RegRAS`（DADAO-21 §寄存器规范 §RA寄存器；SimRISC-02 §函数调用、§函数返回） | `contract-isa.md §5.4–§5.6`；`contracts/abi.yaml`（`call_ret`）；`adr-0004 §D5.5` | LLVM MC、QEMU CPU、vectors |

### §3–§6 机器可读事实 / Deferred / Excluded / `[OPEN]`

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-abi.md §3 M1 机器可读事实`（DADAO-21 §寄存器规范、§数据表示、§函数调用规范） | `contracts/abi.yaml` | LLVM MC、QEMU CPU |
| `contract-abi.md §4 Deferred to M2（完整调用约定：传参 / 返回值 / 栈帧 / prologue-epilogue / 系统调用规范）`（DADAO-21 §传参、§返回值、§函数调用规范、§系统调用规范） | —（M1 不提取） | `Deferred（M1 外）` |
| `contract-abi.md §5 Excluded from M1（高级 ABI：varargs / HFA / HPA / 聚合 / 多返回值）`（DADAO-21 §可变参数、§传参 §聚合类型参数、§返回值） | —（M1 不提取） | `Deferred（M1 外）` |
| `contract-abi.md §6 [OPEN] 汇总`（DADAO-21 §寄存器规范、§返回值、§函数调用规范） | `contracts/abi.yaml`（`[OPEN]` 相关索引）；`.tao/knowledge/deferred.md` | 不列为目标（未冻结项，M1 保守不分配） |
| `contract-abi.md 附录 A 来源对照`（DADAO-21 §寄存器规范、§数据表示、§传参、§函数调用规范；DADAO-11 §返回地址栈） | `contract-abi.md §1`–`§2` | `—（溯源索引，非规范性）` |

---

## 3. ELF — `contract-elf.md`（来源 ADR-0003 §D1–§D5）

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `contract-elf.md §1.1–§1.2 ELF 文件头字段与依据`（ADR-0003 §D1） | `contract-isa.md §1.1`、`§1.5`、`§1.6`、`§2.1`；`contract-abi.md §1.7` | LLVM MC |
| `contract-elf.md §1.3 e_flags 对象/ABI 格式版本字段`（ADR-0003 §D1、§修订） | `—（consumer 接受/拒绝规则；由 MC/工具链消费）` | LLVM MC |
| `contract-elf.md §2 重定位类型（Deferred to M2）`（ADR-0003 §D2） | `contract-isa.md §2.3–§2.4`、`§4.7`、`§5.2–§5.4`（Deferred 场景登记） | `Deferred（M1 外）` |
| `contract-elf.md §3 重定位溢出策略（Deferred to M2）`（ADR-0003 §D3） | —（M1 不产生重定位） | `Deferred（M1 外）` |
| `contract-elf.md §4 重定位松弛（Deferred to M2）`（ADR-0003 §D4） | —（M1 无 link 步骤） | `Deferred（M1 外）` |
| `contract-elf.md §5 段对齐与 VA=PA`（ADR-0003 §D5） | `contract-isa.md §2.1`、`§4.1.1`、`§1.5`；`contract-abi.md §1.7`；`adr-0004 §D1`、`§D2.2` | LLVM MC、QEMU machine、harness |
| `contract-elf.md §6 端到端 artifact pipeline`（§6.1 唯一路径、§6.2 与 ADR-0004 §D2.2/§D2.3 统一、§6.3 M1 约束；ADR-0003 §D5、§Consequences） | `adr-0004 §D2.2`、`§D2.3`；`adr-0003 §Consequences`；`contract-elf.md §6.2` | LLVM MC、QEMU machine、harness |
| `contract-elf.md 附录 A 来源对照`（ADR-0003 §D1–§D5） | `contract-elf.md §1`–`§6` | `—（溯源索引，非规范性）` |

> ELF §2–§4（重定位）在 M1 为 `Deferred to M2`，**不得在 M1 实现**；`e_entry` 不被 M1 test machine 消费。

---

## 4. Test machine — ADR-0004 §D1–§D6（QEMU machine / harness）

| 规格来源 | 依赖此节的合约/文件 | 下游实现目标 |
|----------|-------------------|-------------|
| `adr-0004 §D1 内存映射` | `contract-isa.md §1.5`；`contract-elf.md §5.2`（VA=PA）；`contract-abi.md §2.1`（栈） | QEMU machine、vectors、harness |
| `adr-0004 §D2.1 硬件复位值（power-on reset）` | `contract-isa.md §1.3.1`、`§1.3.2`、`§1.3.3`、`§1.3.4`；`contract-abi.md §2.1` | QEMU machine、vectors |
| `adr-0004 §D2.2 加载方法与入口` | `contract-elf.md §6.1` | QEMU machine、harness |
| `adr-0004 §D2.3 唯一启动协议（双镜像）` | `contract-elf.md §6.2` | QEMU machine、harness |
| `adr-0004 §D3 Exit Port 协议` | `contract-elf.md §6.1`；`contract-isa.md §4.1.1`（`st.o`） | QEMU machine、harness、vectors |
| `adr-0004 §D4 MALIGN 可观测行为` | `contract-isa.md §4.1.1`、`§4.1.2`、`§4.2`、`§4.9`、`§9.2`；`contracts/legality_rules.yaml` | QEMU CPU、QEMU machine、vectors、harness |
| `adr-0004 §D5.1 ILLI 可观测行为` | `contract-isa.md §9.1`、`§6`、`§7.4`、`§7.5`；`contracts/legality_rules.yaml` | QEMU CPU、QEMU machine、vectors、harness |
| `adr-0004 §D5.2 UNDI 可观测行为` | `contract-isa.md §2.7`、`§2.9`、`§8.2`；`contracts/legality_rules.yaml` | QEMU CPU、QEMU machine、vectors、harness |
| `adr-0004 §D5.3 SBZ 字段非零 → ILLI` | `contract-isa.md §7.3`、`§3.4.1` | QEMU CPU、QEMU machine、vectors |
| `adr-0004 §D5.4 IALIGN 可观测行为` | `contract-isa.md §2.1` | QEMU CPU、QEMU machine、vectors、harness |
| `adr-0004 §D5.5 RASOF / RASUF 可观测行为` | `contract-isa.md §1.3.4`、`§5.6`、`§9.2`；`contracts/legality_rules.yaml` | QEMU CPU、QEMU machine、vectors、harness |
| `adr-0004 §D5.6 内存区域 × 访问种类/宽度矩阵（含 fault 优先级）` | `contract-isa.md §4.1`、`§4.2`、`§4.9`；`contracts/legality_rules.yaml` | QEMU machine、vectors、harness |
| `adr-0004 §D5.7 区分 fault 与正常 exit` | `contract-elf.md §6.1`；`contracts/legality_rules.yaml` | QEMU machine、vectors、harness |
| `adr-0004 §D5.8 Exit code 汇总` | `contract-isa.md §9`；`contracts/legality_rules.yaml` | QEMU machine、vectors、harness |
| `adr-0004 §D6.1 fault 如何 surface（fault → exit code）` | `contract-isa.md §9` | QEMU machine、harness |
| `adr-0004 §D6.2 语义测试 pattern` | `contract-isa.md §3`、`§4`、`§5`、`§7`；`contract-abi.md §2` | vectors、harness |
| `adr-0004 §D6.3 异常测试 pattern` | `contract-isa.md §9` | vectors、harness |
| `adr-0004 §D6.4 ROM trampoline` | `contract-elf.md §6.2`；`contract-isa.md §5.3`、`§4.4` | QEMU machine、vectors、harness |
| `adr-0004 §D6.5 三个入口时刻的状态（冻结）` | `contract-isa.md §1.3.2`；`contract-abi.md §2.1` | QEMU machine、vectors、harness |

---

## 覆盖对照

### SimRISC-00..04 → `contract-isa.md`

| spec/ 来源 | 覆盖的 `contract-isa.md` 节 |
|-----------|---------------------------|
| SimRISC-00 | §1.1、§1.3.1–§1.3.4、§1.4、§1.5、§1.6、§2.1–§2.9、§3.8、§5.6、§7.2–§7.5（编码位置）、§8.2、附录 A、附录 B |
| SimRISC-01 | §3.1–§3.8、§4.1 |
| SimRISC-02 | §4.2–§4.9、§5.1–§5.7 |
| SimRISC-03 | §6（全部 Excluded from M1）；rf0 寄存器模型见 §1.3.3（合约内来源标 SimRISC-00） |
| SimRISC-04 | §7.1–§7.6、§8.1、§8.3 |

### DADAO-11 / DADAO-21 → `contract-abi.md`

| spec/ 来源 | 覆盖的 `contract-abi.md` 节 |
|-----------|---------------------------|
| DADAO-21 | §1.1–§1.7、§2.1–§2.3、§3；§4（传参/返回值/栈帧/系统调用，Deferred）；§5（高级 ABI，Excluded） |
| DADAO-11 | §1.5（RA 高 16 位/低 48 位模型，来源 DADAO-11 §返回地址栈） |

### ADR-0003 → `contract-elf.md`

| ADR 决策点 | 覆盖的 `contract-elf.md` 节 |
|-----------|---------------------------|
| §D1（+ §修订） | §1（§1.1–§1.3） |
| §D2 | §2（Deferred to M2） |
| §D3 | §3（Deferred to M2） |
| §D4 | §4（Deferred to M2） |
| §D5 | §5、§6 |

### ADR-0004 → 实现目标

| ADR 决策点 | 覆盖内容 | 实现目标 |
|-----------|---------|---------|
| §D1 | 内存映射 | QEMU machine |
| §D2 | 复位向量与入口点（§D2.1–§D2.3） | QEMU machine |
| §D3 | Exit Port 协议 | QEMU machine、harness |
| §D4 | MALIGN 可观测行为 | QEMU CPU、QEMU machine |
| §D5 | ILLI/UNDI/SBZ/IALIGN/RASOF/RASUF（§D5.1–§D5.8） | QEMU CPU、QEMU machine |
| §D6 | 测试签名规范（§D6.1–§D6.5） | vectors、harness |
