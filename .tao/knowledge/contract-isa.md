# SimRISC ISA 规范合约（M1 范围）

> **版本：0.5.4** [SimRISC-00 §版本]
>
> **范围**：M1——标量整数 + 地址/内存 RD/RB/**RA** + 控制流（`call`/`ret`、RegRAS）+ 测试机所需系统/异常。
>
> **M1 范围外**（标 `Excluded from M1`，不提取其规范内容）：浮点（**RF 全部**：RF 寄存器存取与浮点运算，含 FCSR/rf0 的指令语义）、特权 cfx 系统指令（trap/escape/cfx2rd/cfx2rc/cfxld/cfxst）、LR-SC 原子指令。
>
> **来源标注**：每条规范性断言在句末以 `[SimRISC-XX §章节名]` 标注来源 spec/ 章节，不写行号。SimRISC-07 仅用于确认浮点边界。
>
> **说明**：本合约由 spec/ 归一化投影而来，面向实现；与 spec/ 冲突时阻断实现，走变更流程（见 `spec/Process-02-合约编写规范.md`）。

---

## §1 寄存器模型

### §1.1 寄存器组

SimRISC 提供 4 组用户可见寄存器，每组 64 个，每个寄存器 64 位（即机器字长）。[SimRISC-00 §寄存器]

| 组名 | 范围 | 用途 | M1 范围 |
|------|------|------|---------|
| 数据寄存器 (RD) | rd0–rd63 | 通用运算 | 是 |
| 基址寄存器 (RB) | rb0–rb63 | 地址计算 | 是 |
| 浮点寄存器 (RF) | rf0–rf63 | 浮点运算 | RF 存取与运算 Excluded from M1；仅 rf0（FCSR）寄存器模型/复位值保留（供 SPEC-006t，指令语义 Excluded） |
| 返回地址栈 (RA) | ra0–ra63 | 函数调用/返回 | 是（RegRAS/MemRAS 模型 + RA 存取/块赋值） |

### §1.2 寄存器编号编码

每组寄存器需 6 位编码，位于 ha/hb/hc/hd 的 `[5:0]`。[SimRISC-00 §指令域说明]

### §1.3 特殊寄存器

#### §1.3.1 rd0

- `rd0` 固定为 0，只读。[SimRISC-00 §数据寄存器]
- 作为目的寄存器时行为取决于指令格式：[SimRISC-00 §数据寄存器]
  - rrrr 双目的指令（`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so`）允许其中一个目的为 rd0（丢弃对应半结果），但不能**同时**为 rd0，也不能为同一非 rd0 寄存器。[SimRISC-00 §数据寄存器][SimRISC-00 §数据寄存器]
  - `ret rd0, 0` 允许（无需设置返回值）。[SimRISC-00 §数据寄存器][SimRISC-06 §函数返回]
  - 其余指令目的为 rd0 时触发 **ILLI** 异常。[SimRISC-00 §数据寄存器]

#### §1.3.2 rb0

- `rb0` 读出为**当前指令的地址**（非下一条），只读。任何指令以 rb0 为显式目的时触发 **ILLI** 异常。[SimRISC-00 §基址寄存器][ADR-0015 D1]
- `rb0[63:48]` 初值为 0，由控制流指令硬件写入（见 §8）。[ADR-0012 D8.4]
- 硬件复位后 `rb0` 初值为 `cfx_power_hypv_excp_vector`（见 SEE §2.1）。[SimRISC-00 §基址寄存器]

#### §1.3.3 rf0（浮点状态寄存器，FCSR）

rf0 为浮点状态寄存器（FCSR）。**FCSR 的指令语义（作为浮点操作数、读写约定）Excluded from M1**；此处仅保留 rf0 的**寄存器模型/位布局/复位值**（属 §1 寄存器模型，供 M1 测试机复位值 `SPEC-006t`）。[SimRISC-00 §浮点状态寄存器]

- `rf0` 可作浮点运算的**源操作数**（含 `ftsgnj`/`fosgnj` + `rfHD=rf0` 的 `abs()` 特例）；`rf0` **不可作浮点运算的目的操作数**（目的为 rf0 → ILLI）。[SimRISC-00 §浮点寄存器]

rf0 位域定义：[SimRISC-00 §浮点状态寄存器]

| 位域 | 属性 | 含义 |
|------|------|------|
| [63:51] | 只读 | fo 格式 Quiet NaN（符号位 0，E 全 1，尾数最高位 1） |
| [50:34] | SBZ | 应为零 |
| [33:32] | R/W | 舍入模式（Rounding Mode） |
| [31:22] | 只读 | ft 格式 Quiet NaN（符号位 0，E 全 1，尾数最高位 1） |
| [21:5] | SBZ | 应为零 |
| [4:0] | R/W | 异常状态（Accrued Exception） |

写 `rf0` 时**只更新** `[33:32]`（舍入模式）与 `[4:0]`（异常状态），其余位（只读 Quiet NaN 位、SBZ）**写无效、保持原值**。

舍入模式编码：[SimRISC-00 §浮点状态寄存器]

| 编码 | 助记符 | 含义 |
|------|--------|------|
| 00 | RNE | Round to Nearest, ties to Even |
| 01 | RTZ | Round towards Zero |
| 10 | RDN | Round Down (towards −inf) |
| 11 | RUP | Round Up (towards +inf) |

异常状态位：[SimRISC-00 §浮点状态寄存器]

| 位 | 助记符 | 含义 |
|----|--------|------|
| 0 | NV | Invalid Operation |
| 1 | DZ | Divide by Zero |
| 2 | OF | Overflow |
| 3 | UF | Underflow |
| 4 | NX | Inexact |

> 浮点指令的 rf0 作为操作数等约定见 §9（Excluded from M1）。

#### §1.3.4 ra0–ra63（返回地址栈）

返回地址栈（Return Address Stack）后入先出，将函数返回地址存放在单独可寻址的栈上。[SimRISC-00 §返回地址栈]

| 寄存器 | `[63:48]` | `[47:0]` |
|--------|-----------|----------|
| `ra0` | `[63:54]` = SBZ（写无效）；`[53:48]` = **`RACNT`**（RegRAS 有效条目数，0–63，初始 0） | **`MRPTR`**：MemRAS 下一个待弹出条目（栈顶）的字节地址（8 字节对齐）；0 = 未启用 MemRAS |
| `ra1`–`ra62` | **递归计数** | **返回地址** |
| `ra63` | **递归计数** | **返回地址**（RegRAS 栈顶） |

- `ra1`–`ra63` 构成 RegRAS（63 槽），`ra63` 为 RegRAS 栈顶。[SimRISC-00 §返回地址栈]
- **有效性判据 = `RACNT`**（不看条目自身的值）：有效条目 = 自 `ra63` 起向下连续 `RACNT` 个（第 k 新 = `ra[64−k]`，栈底 = `ra[64−RACNT]`）；有效区之外 `ra_i` 内容未定义（复位后全 0）。[ADR-0012 D7 §2]
- **`MRPTR == 0`** 时只有一个 RAS（RegRAS），最多存放 63 个返回地址；非 0 时有两个 RAS（RegRAS 与 MemRAS），`MRPTR` 为 MemRAS 栈顶地址。[SimRISC-00 §返回地址栈]
- MemRAS 的访存遵循地址转换和存储访问规则；若访存触发页缺失等异常，硬件保证精确异常（压栈/弹栈未执行，PC 指向 call/ret 指令），异常处理后可重新执行。[SimRISC-00 §返回地址栈]
- **RASOF** 仅由「需溢出且 `MRPTR == 0`」触发；**MemRAS 越界（容量耗尽）不由硬件检测（交 OS）**。[ADR-0012 D7 §7]
- RASOF/RASUF 均为精确异常：压栈/弹栈**先完成全部 `RASOF`/`RASUF` 判定**（含 D4b 的 MemRAS 条目读取与内容判定），判定通过后才进行 RA 寄存器或 MemRAS 访存的任何修改；异常时 RA 寄存器与内存均保持原状。[ADR-0012 D7 §6]
- 一个用户进程开始执行时，RegRAS 全部初始化为全零（`RACNT = 0`，条目内容全 0），MemRAS 应做好分配并设置 `ra0`；fork 子进程应复制父进程的全部 ra 寄存器。[SimRISC-00 §返回地址栈]
- 进程切换时操作系统须保存和恢复全部 ra0–ra63。[SimRISC-00 §返回地址栈]
- 异常进入和退出不改变 ra0–ra63 的内容；异常 handler 中可正常使用 call/ret。[SimRISC-00 §返回地址栈]
- `ra0` 作**目的**或**源**均**不触发**异常（可读写）。覆盖 `ld.o`/`st.o`/`ldm.o`/`stm.o`（SimRISC-01 §存取RA寄存器）与 `rd2ra`/`ra2rd`（SimRISC-02 §寄存器组之间块赋值）。

### §1.4 数据表示

基础数据类型：[SimRISC-00 §数据表示]

| 术语 | 缩写 | 位数 | 字节数 |
|------|------|------|--------|
| byte | b | 8-bit | 1-byte |
| wyde | w | 16-bit | 2-byte |
| tetra | t | 32-bit | 4-byte |
| octa | o | 64-bit | 8-byte |

- 四种定点类型（8/16/32/64 bit）与两种浮点类型（32/64 bit，IEEE 754）。[SimRISC-00 §原始数据类型]

### §1.5 存储模型

- SimRISC 采用 64 位地址空间，有效虚拟地址为 48 位。[SimRISC-00 §基址寄存器]
- RB 为整 64 位寄存器，存取/复制/立即数赋值等均为全 64 位操作；**作访存基址时取 `rb[47:0]`（低 48 位）**为有效地址；控制流地址计算按 64 位全宽进行（见 §8）。[SimRISC-00 §基址寄存器][ADR-0012 D8.1/D8.3]
- 实际实现需保证 48 位地址空间。[SimRISC-00 §基址寄存器]
- `rb0` 读出为当前指令的地址；`rb0` 以 64 位参与控制流地址计算，结果写回 `rb0`（见 §8）。[ADR-0012 D8.4]

### §1.6 端序

指令字采用大端序存储：bits[31:24] 在最低地址，bits[7:0] 在最高地址；数据端序同样为大端序。[SimRISC-00 §指令设计]

---

## §2 指令编码

### §2.1 指令格式

- 每条指令均为 4 字节（32 位），所有指令必须 4 字节对齐。[SimRISC-00 §指令设计]
- 取指时若 `PC[1:0] ≠ 00`，触发 **IALIGN** 异常。[SimRISC-00 §指令设计]
- 指令字采用大端序存储（见 §1.6）。[SimRISC-00 §指令设计]

### §2.2 指令域

一个 32 位指令分解为 5 个部分：8/6/6/6/6，即 op / ha / hb / hc / hd。[SimRISC-00 §指令域说明]

- `op`：操作码（opc），头 8 位，指明指令功能并隐含指令分类。[SimRISC-00 §指令域说明]
- `ha/hb/hc/hd`：各 6 位（hexagram），指明操作数（格式与内容）。[SimRISC-00 §指令域说明]
- 某些情况下 `ha`（6 位）也参与操作码，称为 `opx`（opcode-auxiliary），**只可能是 ha**。[SimRISC-00 §指令域说明]
- 后 16 位作为立即数时，`hb` 头两位用来指定 wyde 在 64 位数据中的位置（wyde-position 属操作数域，与操作码无关）。[SimRISC-00 §指令域说明]

操作数寻址方式字母：[SimRISC-00 §指令域说明]

- `o`：六位的 opx
- `c`：六位的 cfxha
- `r`：寄存器
- `i`：立即数（立即数域需要区分有符号数和无符号数）
- `w`：头两位为 wyde-position，后四位为立即数
- `z`：未使用，应为零（SBZ）

### §2.3 操作数格式

操作数类型用 4 个字母表示，隐含操作数位置和个数。[SimRISC-00 §指令域说明]

| 格式 | 含义 | 立即数位置 |
|------|------|-----------|
| `rrrr` | 四个操作数，都是寄存器 | 无 |
| `rrri` | 三个寄存器 + 6 位立即数 | `hd[5:0]` |
| `rrii` | 两个寄存器 + 12 位立即数 | `hc[5:0]`（高 6 位）+ `hd[5:0]`（低 6 位） |
| `riii` | 一个寄存器 + 18 位立即数 | `hb[5:0]`（高）+ `hc[5:0]`（中）+ `hd[5:0]`（低） |
| `iiii` | 一个操作数，24 位立即数 | `ha[5:0]`+`hb[5:0]`+`hc[5:0]`+`hd[5:0]` |

含 wyde-position 的特殊格式：[SimRISC-00 §指令域说明]

| 格式 | 含义 | 编码 |
|------|------|------|
| `rwii` | 一个寄存器 + wyde-position + 拆分为两段的 16 位无符号立即数 | wyde-position 在 `hb[5:4]`；immu16 高 4 位在 `hb[3:0]`、中 6 位在 `hc[5:0]`、低 6 位在 `hd[5:0]`（hb→hc→hd 高到低） |

含 opx（`o`，6 位，在 `ha[5:0]`）的格式：[SimRISC-00 §指令域说明]

| 格式 | 含义 |
|------|------|
| `orrr` | opx + 三个寄存器 |
| `orri` | opx + 两个寄存器 + 6 位立即数在 `hd[5:0]` |
| `oiii` | opx + 18 位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]` |

> cfxha（`c`）相关格式 `crrr`/`crii`/`ciii` 属特权 cfx 指令，Excluded from M1（见 §14.3）。

### §2.4 Wyde-Position 编码

`rwii` 格式中 `hb[5:4]` 指定 wyde 在 64 位数据中的位置：[SimRISC-00 §指令域说明]

| 编码 | 位置 | 对应位域 |
|------|------|---------|
| 00 | wp0 | bits[15:0]（LSW） |
| 01 | wp1 | bits[31:16] |
| 10 | wp2 | bits[47:32] |
| 11 | wp3 | bits[63:48]（MSW） |

### §2.5 数据位宽后缀

SimRISC 提供四种固定数据位宽，通过指令名后缀 `.b`/`.w`/`.t`/`.o` 区分，分别对应 byte/wyde/tetra/octa。[SimRISC-00 §指令域说明]

| 后缀 | 位宽 |
|------|------|
| `.b` | byte（8 位） |
| `.w` | wyde（16 位） |
| `.t` | tetra（32 位） |
| `.o` | octa（64 位） |

对有符号/无符号区分的指令（mul/div/rem/cmp/ext/shl/shr），后缀扩展为 `.ub`/`.sb`（byte）、`.uw`/`.sw`（wyde）、`.ut`/`.st`（tetra）、`.uo`/`.so`（octa），其中 `s` 表示有符号、`u` 表示无符号。[SimRISC-00 §指令域说明]

### §2.6 操作数顺序约定

SimRISC 通常将目的操作数放在最前面，然后是寄存器源操作数，立即数通常为最后一个源操作数。[SimRISC-00 §指令域说明]

### §2.7 QFC 主表（op[7:0]，M1 视图）

空白单元格表示 reserved（保留未分配），执行保留编码触发 **UNDI** 异常。[SimRISC-00 §SimRISC QFC]

| op[7:3]\op[2:0] | xxxx-x000 | xxxx-x001 | xxxx-x010 | xxxx-x011 | xxxx-x100 | xxxx-x101 | xxxx-x110 | xxxx-x111 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0000-0xxx | — | — | — | — | — | — | — | — |
| 0000-1xxx | — | — | — | — | — | — | — | — |
| 0001-0xxx | ld.ub-rd | ld.uw-rd | ld.ut-rd | ld.sb-rd | ld.sw-rd | ld.st-rd | ld.t-rf Excl. | st.t-rf Excl. |
| 0001-1xxx | st.b-rd | st.w-rd | st.t-rd | — | — | — | — | — |
| 0010-0xxx | ld.o-rd | st.o-rd | ld.o-rb | st.o-rb | ld.o-ra | st.o-ra | ld.o-rf Excl. | st.o-rf Excl. |
| 0010-1xxx | ldm.ub-rd | ldm.uw-rd | ldm.ut-rd | ldm.sb-rd | ldm.sw-rd | ldm.st-rd | ldm.t-rf Excl. | stm.t-rf Excl. |
| 0011-0xxx | stm.b-rd | stm.w-rd | stm.t-rd | — | — | — | — | — |
| 0011-1xxx | ldm.o-rd | stm.o-rd | ldm.o-rb | stm.o-rb | ldm.o-ra | stm.o-ra | ldm.o-rf Excl. | stm.o-rf Excl. |
| 0100-0xxx | MISC-octa | MISC-tetra | MISC-wyde | MISC-byte | MISC-RF Excl. | — | — | — |
| 0100-1xxx | or.w-rd | andn.w-rd | or.w-rb | andn.w-rb | set.zw-rd | set.ow-rd | set.zw-rb | set.w-rf Excl. |
| 0101-0xxx | add.uo-rd | add.so-rd | sub.uo-rd | sub.so-rd | mul.uo-rd | mul.so-rd | | |
| 0101-1xxx | — | add.si-rd | ~~rela.si-rb~~ UNDI | add.si-rb | cmp.ui-rd | cmp.si-rd | cs.eq-rf Excl. | cs.ne-rf Excl. |
| 0110-0xxx | cs.n-rd | cs.n-rf Excl. | cs.z-rd | cs.z-rf Excl. | cs.p-rd | cs.p-rf Excl. | cs.eq-rd | cs.ne-rd |
| 0110-1xxx | br.n-rd | br.nn-rd | br.z-rd | br.nz-rd | br.p-rd | br.np-rd | br.eq-rd | br.ne-rd |
| 0111-0xxx | jump-iiii | jump-rrii | br.z-rb | br.nz-rb | call-iiii | call-rrii | ret | MISC-AMO |
| 0111-1xxx | — | — | cfx2rd Excl. | cfx2rc Excl. | cfxld Excl. | cfxst Excl. | escape Excl. | trap Excl. |

> Excl. = `Excluded from M1`。`MISC-AMO` 子表中的 LR-SC 条目同属 Excluded from M1（见 §14.2）。[SimRISC-00 §SimRISC QFC]

### §2.8 MISC 子表机制

四种固定数据位宽指令分布在四个 opx 子表中，各子表内使用 `orrr`/`orri`/`oiii` 操作数格式：[SimRISC-00 §指令域说明]

| 子表 | op | 位宽 |
|------|-----|------|
| `MISC-byte` | 0100-0011 | byte |
| `MISC-wyde` | 0100-0010 | wyde |
| `MISC-tetra` | 0100-0001 | tetra |
| `MISC-octa` | 0100-0000 | octa |

- 各子表指令的 opx 在 `ha[5:0]`，与 op 共同确定指令。[SimRISC-00 §指令域说明]
- `MISC-AMO`（op = 0111-0111）承载 illi/fence 与 LR-SC 原子指令。[SimRISC-00 §MISC-AMO 指令编码]
- `MISC-RF`（op = 0100-0100）承载浮点指令，Excluded from M1。[SimRISC-00 §MISC-RF指令编码]

### §2.9 保留编码

- QFC 主表与各 MISC 子表的空白单元格为 reserved（保留未分配），执行保留编码触发 **UNDI** 异常。[SimRISC-00 §SimRISC QFC]
- 32 位全零指令字（0x00000000）：`MISC-AMO` 编码变更后，op = 0x00 在 QFC 主表为空白单元格（reserved），触发 **UNDI** 异常（不再是 `illi 0`）。`illi 0` 的新编码为 0x77000000。[SimRISC-11 §非法指令]

---

## §3 取数存数指令

> 范围：RD、RB、RA 寄存器组的 load/store 操作。RA 寄存器模型见 §1.3.4。寄存器复制（块赋值）见 §4；立即数设置见 §5。

### §3.1 存取 RD 寄存器

#### §3.1.1 单 load/store（rrii 格式）

地址计算公式为基址寄存器 + 立即数。[SimRISC-01 §存取类指令]

| 指令 | 语义 | 对齐要求 | 来源 |
|------|------|---------|------|
| `ld.sb rdha, rbhb, imms12` | `rdha = sign_extend(mem8[rbhb + imms12])` | 无 | [SimRISC-01 §存取RD寄存器] |
| `ld.ub rdha, rbhb, imms12` | `rdha = zero_extend(mem8[rbhb + imms12])` | 无 | [SimRISC-01 §存取RD寄存器] |
| `ld.sw rdha, rbhb, imms12` | `rdha = sign_extend(mem16[rbhb + imms12])` | 2 字节 | [SimRISC-01 §存取RD寄存器] |
| `ld.uw rdha, rbhb, imms12` | `rdha = zero_extend(mem16[rbhb + imms12])` | 2 字节 | [SimRISC-01 §存取RD寄存器] |
| `ld.st rdha, rbhb, imms12` | `rdha = sign_extend(mem32[rbhb + imms12])` | 4 字节 | [SimRISC-01 §存取RD寄存器] |
| `ld.ut rdha, rbhb, imms12` | `rdha = zero_extend(mem32[rbhb + imms12])` | 4 字节 | [SimRISC-01 §存取RD寄存器] |
| `ld.o rdha, rbhb, imms12` | `rdha = mem64[rbhb + imms12]` | 8 字节 | [SimRISC-01 §存取RD寄存器] |
| `st.b rdha, rbhb, imms12` | `mem8[rbhb + imms12] = rdha[7:0]` | 无 | [SimRISC-01 §存取RD寄存器] |
| `st.w rdha, rbhb, imms12` | `mem16[rbhb + imms12] = rdha[15:0]` | 2 字节 | [SimRISC-01 §存取RD寄存器] |
| `st.t rdha, rbhb, imms12` | `mem32[rbhb + imms12] = rdha[31:0]` | 4 字节 | [SimRISC-01 §存取RD寄存器] |
| `st.o rdha, rbhb, imms12` | `mem64[rbhb + imms12] = rdha[63:0]` | 8 字节 | [SimRISC-01 §存取RD寄存器] |

异常条件：[SimRISC-01 §存取RD寄存器]
- `ld`：`rdha` 为 `rd0` → **ILLI**（目的不可为 rd0）
- `st`：`rdha` 为 `rd0` **允许**（rd0 作源，读出 0）[ADR-0015 D2/D3]
- 未对齐 → **MALIGN**

#### §3.1.2 多 load/store（rrri 格式）

多 load/store 类指令地址计算公式为基址寄存器 + 数据寄存器。[SimRISC-01 §存取类指令]

| 指令 | 语义 | 来源 |
|------|------|------|
| `ldm.sb`/`ldm.ub`/`ldm.sw`/`ldm.uw`/`ldm.st`/`ldm.ut`/`ldm.o rdha, rbhb, rdhc, immu6` | 从 `rbhb + rdhc` 地址加载 immu6 个连续寄存器 | [SimRISC-01 §存取RD寄存器] |
| `stm.b`/`stm.w`/`stm.t`/`stm.o rdha, rbhb, rdhc, immu6` | 将 immu6 个连续寄存器存储到 `rbhb + rdhc` 地址 | [SimRISC-01 §存取RD寄存器] |

- `rdha` 指定第一个寄存器，`rbhb + rdhc` 指定地址，`immu6` 指定寄存器个数，有效范围 1–63。[SimRISC-01 §存取RD寄存器]
- 存取 8/16/32 位数据时，每个寄存器只存放一个数据，多个数据使用多个连续的寄存器。[SimRISC-01 §存取RD寄存器]
- 对齐要求同 §3.1.1（`ldm.o`/`stm.o` 8 字节，`ldm.st`/`stm.t`/`ldm.ut` 4 字节，`ldm.sw`/`stm.w`/`ldm.uw` 2 字节，`ldm.sb`/`stm.b`/`ldm.ub` 无）。[SimRISC-01 §存取RD寄存器]
- 当多寄存器读写范围包括 `rdhc` 时，地址计算仍按原始 `rdhc` 中的数据进行。[SimRISC-01 §存取RD寄存器]
- 装入类指令的源寄存器范围与目的寄存器范围可以重叠；硬件按序号递增逐对处理，每对先读后写。[SimRISC-01 §存取RD寄存器]

异常条件：[SimRISC-01 §存取RD寄存器]
- `ldm`：`rdha` 为 `rd0` → **ILLI**（目的不可为 rd0）
- `stm`：`rdha` 为 `rd0` **允许**（rd0 作源，读出 0）[ADR-0015 D3]
- `immu6 = 0` → **ILLI**
- `rdha + immu6 > 64`（超出 rd63）→ **ILLI**，不环绕、不截断
- 未对齐 → **MALIGN**

### §3.2 存取 RB 寄存器

RB 寄存器都是 64 位，不需指定数据长度。[SimRISC-01 §存取RB寄存器]

| 指令 | 语义 | 来源 |
|------|------|------|
| `ld.o rbha, rbhb, imms12` | `rbha = mem64[rbhb + imms12]`，全 64 位覆盖 | [SimRISC-01 §存取RB寄存器] |
| `st.o rbha, rbhb, imms12` | `mem64[rbhb + imms12] = rbha` | [SimRISC-01 §存取RB寄存器] |
| `ldm.o rbha, rbhb, rdhc, immu6` | 多寄存器加载（连续 RB） | [SimRISC-01 §存取RB寄存器] |
| `stm.o rbha, rbhb, rdhc, immu6` | 多寄存器存储（连续 RB） | [SimRISC-01 §存取RB寄存器] |

异常条件：[SimRISC-01 §存取RB寄存器]
- 需 8 字节地址对齐，未对齐 → **MALIGN**
- `ld.o`/`ldm.o`：`rbha` 为 `rb0` → **ILLI**（目的不可为 rb0）
- `st.o`/`stm.o`：`rbha` 为 `rb0` **允许**（rb0 作源，读出为当前指令的地址）[ADR-0015 D3]
- `immu6 = 0` → **ILLI**
- `rbha + immu6 > 64`（超出 rb63）→ **ILLI**
- 当多寄存器读写范围包括 `rbhb` 时，地址计算仍按原始 `rbhb` 中的数据进行。[SimRISC-01 §存取RB寄存器]

### §3.3 存取 RA 寄存器与 RA↔RD 块赋值

RA 寄存器都是 64 位，不需指定数据长度。RA 寄存器模型（ra0–ra63、RegRAS/MemRAS）见 §1.3.4。[SimRISC-01 §存取RA寄存器]

#### §3.3.1 单 load/store（rrii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `ld.o raha, rbhb, imms12` | `raha = mem64[rbhb + imms12]`，全 64 位覆盖 | [SimRISC-01 §存取RA寄存器] |
| `st.o raha, rbhb, imms12` | `mem64[rbhb + imms12] = raha` | [SimRISC-01 §存取RA寄存器] |

异常条件：[SimRISC-01 §存取RA寄存器]
- 需 8 字节地址对齐，未对齐 → **MALIGN**
- `raha` 为 `ra0` 时不触发异常（ra0 可读写）

#### §3.3.2 多 load/store（rrri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `ldm.o raha, rbhb, rdhc, immu6` | 多寄存器加载（连续 RA） | [SimRISC-01 §存取RA寄存器] |
| `stm.o raha, rbhb, rdhc, immu6` | 多寄存器存储（连续 RA） | [SimRISC-01 §存取RA寄存器] |

异常条件：[SimRISC-01 §存取RA寄存器]
- 需 8 字节地址对齐，未对齐 → **MALIGN**
- `raha` 为 `ra0` 时不触发异常（ra0 可读写）
- `immu6 = 0` → **ILLI**
- `raha + immu6 > 64`（超出 ra63）→ **ILLI**

#### §3.3.3 RA↔RD 块赋值（orri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `ra2rd rdhb, rahc, immu6` | 将 `rahc` 开始的 immu6 个 RA 复制到 `rdhb` 开始的 immu6 个 RD | [SimRISC-02 §寄存器组之间块赋值] |
| `rd2ra rahb, rdhc, immu6` | 将 `rdhc` 开始的 immu6 个 RD 复制到 `rahb` 开始的 immu6 个 RA | [SimRISC-02 §寄存器组之间块赋值] |

- `immu6` 存在 `hd` 位域，有效范围 1–63。[SimRISC-02 §寄存器组之间块赋值]
- 根据语义，rb/rf/ra 之间不能进行直接赋值，ra 与 ra 之间不能相互赋值（故仅有 `ra2rd`/`rd2ra`，无 `ra2ra`）。[SimRISC-02 §寄存器组之间块赋值]
- 异常条件：[SimRISC-02 §寄存器组之间块赋值]
  - `immu6 = 0` → **ILLI**
  - 任一起始寄存器 + immu6 > 64 → **ILLI**
  - `ra2rd` 的目的 `rdhb` 为 `rd0` → **ILLI**（目的不可为 rd0）。[SimRISC-00 §数据寄存器][SimRISC-00 §数据寄存器]
- 源和目的范围可以重叠；硬件按序号递增逐对处理，每对先读后写。[SimRISC-02 §寄存器组之间块赋值]

---

## §4 寄存器复制指令

> 范围：寄存器组内部和之间的块赋值操作，保持 64 位二进制不变。条件赋值（`cs.n`/`cs.z`/`cs.p`/`cs.eq`/`cs.ne`）见 §6.5。

### §4.1 RD 内部块赋值（orri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `rd2rd rdhb, rdhc, immu6` | 将 `rdhc` 开始的 immu6 个寄存器复制到 `rdhb` 开始的 immu6 个寄存器，保持 64 位二进制不变 | [SimRISC-02 §寄存器组之间块赋值] |

- `immu6` 存在 `hd` 位域，指定寄存器个数，有效范围 1–63。[SimRISC-02 §寄存器组之间块赋值]
- 异常条件：[SimRISC-02 §寄存器组之间块赋值]
  - `immu6 = 0` → **ILLI**
  - `rdhb` 为 `rd0` → **ILLI**（目的不可为 rd0）
  - `rdhb + immu6 > 64` → **ILLI**（超出 rd63）
  - `rdhc + immu6 > 64` → **ILLI**（源超出 rd63）
- 源和目的范围可以重叠；硬件按序号递增逐对处理，每对先读后写。[SimRISC-02 §寄存器组之间块赋值]

### §4.2 RB/RD 间块赋值（orri 格式）

不同/相同寄存器组之间可进行块传输，保持 64 位二进制不变，必须是多个连续寄存器。[SimRISC-02 §寄存器组之间块赋值]

| 指令 | 语义 | 来源 |
|------|------|------|
| `rb2rd rdhb, rbhc, immu6` | 将 `rbhc` 开始的 immu6 个 RB 复制到 `rdhb` 开始的 immu6 个 RD | [SimRISC-02 §寄存器组之间块赋值] |
| `rd2rb rbhb, rdhc, immu6` | 将 `rdhc` 开始的 immu6 个 RD 复制到 `rbhb` 开始的 immu6 个 RB | [SimRISC-02 §寄存器组之间块赋值] |
| `rb2rb rbhb, rbhc, immu6` | RB→RB 块复制 | [SimRISC-02 §寄存器组之间块赋值] |

- `immu6` 存在 `hd` 位域，有效范围 1–63。[SimRISC-02 §寄存器组之间块赋值]
- 根据语义，rb/rf/ra 之间不能进行直接赋值，ra 与 ra 之间不能相互赋值。[SimRISC-02 §寄存器组之间块赋值]
- 异常条件：[SimRISC-02 §寄存器组之间块赋值]
  - `immu6 = 0` → **ILLI**
  - `rbhb` 为 `rb0` → **ILLI**（目的不可为 rb0）
  - 任一起始寄存器 + immu6 > 64 → **ILLI**
- 源和目的范围可以重叠；硬件按序号递增逐对处理，每对先读后写。[SimRISC-02 §寄存器组之间块赋值]

---

## §5 16 位立即数操作

> 范围：16 位立即数设置类指令（`set.zw`/`set.ow`/`or.w`/`andn.w`），支持 RD 和 RB 寄存器组。块赋值见 §4。

### §5.1 RD 立即数设置（rwii 格式）

立即数设置类指令用 16 位立即数对寄存器内指定 wyde 赋值/或/与非；`wpN` 指定 wyde 位置（见 §2.4）。[SimRISC-03 §立即数常数赋值：Immediate constant]

| 指令 | 语义 | 来源 |
|------|------|------|
| `set.ow rdha, wpN, immu16` | `rdha[wyde(wpN)] = immu16`，其余 48 位置 1 | [SimRISC-03 §立即数常数赋值：Immediate constant] |
| `set.zw rdha, wpN, immu16` | `rdha[wyde(wpN)] = immu16`，其余 48 位清 0 | [SimRISC-03 §立即数常数赋值：Immediate constant] |
| `or.w rdha, wpN, immu16` | `rdha[wyde(wpN)] = rdha[wyde(wpN)] \| immu16`，其余 wyde 不变 | [SimRISC-03 §立即数常数赋值：Immediate constant] |
| `andn.w rdha, wpN, immu16` | `rdha[wyde(wpN)] = rdha[wyde(wpN)] & ~immu16`，其余 wyde 不变 | [SimRISC-03 §立即数常数赋值：Immediate constant] |

- `set.zw`/`set.ow` 会改变所有 64 位，不能连续使用多条来设置不同 wyde；只能使用一条 `set.zw`/`set.ow` 作为第一条，后续用 `or.w`/`andn.w` 逐 wyde 修正。[SimRISC-03 §set.rd 伪指令]
- 注意：`or.w` 同时是 MISC-wyde 表的三寄存器逻辑 OR 指令（`or.w rdhb, rdhc, rdhd`），汇编器按操作数格式区分。[SimRISC-03 §立即数常数赋值：Immediate constant]

### §5.2 RB 立即数设置（rwii 格式）

针对 RB 寄存器提供 `set.zw`/`or.w`/`andn.w`，操作数类型 `rwii`。[SimRISC-03 §立即数常数赋值：Immediate constant]

| 指令 | 语义 | 来源 |
|------|------|------|
| `set.zw rbha, wpN, immu16` | `rbha[wyde(wpN)] = immu16`，其余 48 位清 0 | [SimRISC-03 §立即数常数赋值：Immediate constant] |
| `or.w rbha, wpN, immu16` | `rbha[wyde(wpN)] = rbha[wyde(wpN)] \| immu16`，其余不变 | [SimRISC-03 §立即数常数赋值：Immediate constant] |
| `andn.w rbha, wpN, immu16` | `rbha[wyde(wpN)] = rbha[wyde(wpN)] & ~immu16`，其余不变 | [SimRISC-03 §立即数常数赋值：Immediate constant] |

- RB 无 `set.ow` 变体。[SimRISC-03 §set.rb 伪指令]
- `set.zw` 会清零其余所有位，不能连续使用多条；只能一条 `set.zw` 作为第一条，后续用 `or.w`/`andn.w` 逐 wyde 修正。[SimRISC-03 §set.rb 伪指令]
- RB 立即数设置全 64 位覆盖，bits[63:48] 正常读写，允许 wyde-pos=3。[SimRISC-00 §基址寄存器]

### §5.4 伪指令（立即数设置）

| 伪指令 | 展开形式 | 说明 | 来源 |
|--------|----------|------|------|
| `set.rd rdxx, imm64` | `set.zw`/`set.ow` + `or.w`/`andn.w`（1–4 条） | 加载 64 位立即数到 rd | [SimRISC-03 §set.rd 伪指令] |
| `set.rd rdxx, rs` | `rb2rd`/`rf2rd`/`ra2rd`/`rd2rd` | 从其他寄存器传值到 rd；M1 支持 `rb`/`rd`/`ra` 源（`rf` 源 Excluded） | [SimRISC-03 §set.rd 伪指令] |
| `set.rb rbxx, imm64` | `set.zw-rb` + `or.w-rb` | 加载立即数到 rb | [SimRISC-03 §set.rb 伪指令] |
| `set.rb rbxx, rs` | `rd2rb`/`rb2rb` | 从其他寄存器传值到 rb | [SimRISC-03 §set.rb 伪指令] |

`set.rd` 展开规则（汇编器应优先选择指令数最少的方案）：[SimRISC-03 §set.rd 伪指令]
1. 若 64 位全同（全 0 或全 1），1 条 `set.zw`/`set.ow`。
2. 若连续 wyde 值相同（如高 48 位全 0），填充初始 wyde 后 `or.w` 补充剩余差异。
3. 一般情况：`set.zw`/`set.ow` 设置一个基数 wyde，其余 wyde 用 `or.w` 设 1、`andn.w` 清 0。

> `set.rd rdxx, rs` 中源为 `rb` 时展开为 `rb2rd`（M1）、源为 `rd` 时展开为 `rd2rd`（M1）、源为 `ra` 时展开为 `ra2rd`（M1，见 §3.3.3）；源为 `rf` 展开 `rf2rd`，属 Excluded from M1（见 §9）。[SimRISC-03 §set.rd 伪指令]

- `set.rb` 展开为 `set.zw` 与 `or.w` 的组合（rb 无 `set.ow` 变体，无需 `andn.w`）。[SimRISC-03 §set.rb 伪指令]
- 汇编器应优先通过 `set.zw` 加载地址值，利用其清零其余位的特性自动处理高 16 位。[SimRISC-03 §set.rb 伪指令]

---

## §6 64 位数据运算指令

> 全部为 RD 寄存器组指令（64 位 octa 运算）；目的为 rd0 的通用约束见 §1.3.1。32/16/8 位运算分别见 §10/§11/§12。地址运算（RB）见 §7。

### §6.1 算术运算

#### §6.1.1 加减法（128 位结果，rrrr 格式）

加减操作两个源操作数为 `rdhc`/`rdhd`，目的为 `rdha`（结果高 64 位）与 `rdhb`（结果低 64 位）。硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。[SimRISC-04 §加减操作]

| 指令 | 语义 | 来源 |
|------|------|------|
| `add.uo rdha, rdhb, rdhc, rdhd` | 源零扩展（ZX）至 128 位，`rdha:rdhb = rdhc + rdhd`，`rdha` 为进位（0 或 1） | [SimRISC-04 §加减操作] |
| `add.so rdha, rdhb, rdhc, rdhd` | 源符号扩展（SX）至 128 位，`rdha:rdhb = rdhc + rdhd`，`rdha` 为高 64 位 | [SimRISC-04 §加减操作] |
| `sub.uo rdha, rdhb, rdhc, rdhd` | 源零扩展（ZX）至 128 位，`rdha:rdhb = rdhc − rdhd`，`rdha` 为借位（0 或 1） | [SimRISC-04 §加减操作] |
| `sub.so rdha, rdhb, rdhc, rdhd` | 源符号扩展（SX）至 128 位，`rdha:rdhb = rdhc − rdhd`，`rdha` 为高 64 位 | [SimRISC-04 §加减操作] |

异常条件：[SimRISC-04 §加减操作]
- `rdha` 与 `rdhb` 同时为 `rd0` → **ILLI**
- `rdha` 与 `rdhb` 为同一非 `rd0` 寄存器 → **ILLI**

#### §6.1.2 64 位加减法（orrr 格式）

`MISC-octa` 子表中的 `add`/`sub` 提供 64 位加减运算。[SimRISC-04 §加减操作]

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `div.uo`/`rem.uo` 的加减对应 | 64 位 | `add.uo rdhb, rdhc, rdhd`（MISC-octa） | 全 64 位参与 |

> 64 位固定位宽加减法由 MISC-octa 子表的 `orrr` 格式 `add`/`sub` 指令覆盖。完整的 64 位加减运算语义见 [SimRISC-04 §加减操作]。32/16/8 位加减法分别见 §10.1.1、§11.1.1、§12.1.1。

异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-04 §加减操作]

#### §6.1.3 自增自减（riii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `add.si rdha, imms18` | `rdha = rdha + sign_extend(imms18)`，全 64 位运算 | [SimRISC-04 §自增自减] |

- 立即数为 18 位有符号数，采用补码编码，无需区分加减操作。[SimRISC-04 §自增自减]
- 无法单独通过结果判断溢出；用户可结合 `add.uo`/`add.so` 的 rrrr 形式获取进位/符号信息。[SimRISC-04 §自增自减]

#### §6.1.4 乘法（rrrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `mul.uo rdha, rdhb, rdhc, rdhd` | 无符号乘法，`rdha:rdhb = rdhc × rdhd`（128 位结果） | [SimRISC-04 §乘除操作] |
| `mul.so rdha, rdhb, rdhc, rdhd` | 有符号乘法，`rdha:rdhb = rdhc × rdhd`（128 位结果） | [SimRISC-04 §乘除操作] |

- `rdha` 存放结果高 64 位，`rdhb` 存放结果低 64 位；硬件先读全部源操作数再写结果。[SimRISC-04 §乘除操作]
- 异常条件：`rdha` 与 `rdhb` 同时为 `rd0` → **ILLI**；`rdha` 与 `rdhb` 为同一非 `rd0` 寄存器 → **ILLI**。[SimRISC-04 §乘除操作]

#### §6.1.5 除余运算（orrr 格式）— 定值语义

`MISC-byte`/`MISC-wyde`/`MISC-tetra`/`MISC-octa` 子表中的 `div`/`rem` 提供 8/16/32/64 位除余运算。[SimRISC-04 §乘除操作]

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `div.ub`/`div.sb`/`rem.ub`/`rem.sb` | 8 位 | `div.ub rdhb, rdhc, rdhd` |
| `div.uw`/`div.sw`/`rem.uw`/`rem.sw` | 16 位 | `div.uw rdhb, rdhc, rdhd` |
| `div.ut`/`div.st`/`rem.ut`/`rem.st` | 32 位 | `div.ut rdhb, rdhc, rdhd` |
| `div.uo`/`div.so`/`rem.uo`/`rem.so` | 64 位 | `div.uo rdhb, rdhc, rdhd` |

- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-04 §乘除操作]
- `rdhd` 可以为 `rd0`（`rd0` 读出 0 ⇒ 除零 ⇒ 走定值语义）。[用户裁定 2026-10-01]

除法附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：[SimRISC-04 §乘除操作]
- **除数为零 → 定值**（不再触发 ILLI）。[用户裁定 2026-10-01]
- **有符号溢出（INT_MIN ÷ −1）→ 定值**（不再触发 ILLI）。[用户裁定 2026-10-01]
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **定值表**（按运算宽度取值，有符号变体符号扩展写满 64 位 / 无符号变体零扩展）：[用户裁定 2026-10-01]

| 指令 | 除零 ⇒ `rdhb` | 有符号溢出（INT_MIN ÷ −1）⇒ `rdhb` |
|------|---------------|--------------------------------------|
| `div.sb` | `0xFFFF_FFFF_FFFF_FFFF` | `0xFFFF_FFFF_FFFF_FF80` |
| `div.ub` | `0x0000_0000_0000_00FF` | 不适用 |
| `div.sw` | `0xFFFF_FFFF_FFFF_FFFF` | `0xFFFF_FFFF_FFFF_8000` |
| `div.uw` | `0x0000_0000_0000_FFFF` | 不适用 |
| `div.st` | `0xFFFF_FFFF_FFFF_FFFF` | `0xFFFF_FFFF_8000_0000` |
| `div.ut` | `0x0000_0000_FFFF_FFFF` | 不适用 |
| `div.so` | `0xFFFF_FFFF_FFFF_FFFF` | `0x8000_0000_0000_0000` |
| `div.uo` | `0xFFFF_FFFF_FFFF_FFFF` | 不适用 |
| `rem.sb`/`rem.sw`/`rem.st`/`rem.so` | 被除数（符号扩展写满 64 位） | `0` |
| `rem.ub`/`rem.uw`/`rem.ut`/`rem.uo` | 被除数（零扩展写满 64 位） | 不适用 |

- **扩展规则**：有符号变体（`div.s`/`rem.s`）结果按符号扩展写满 64 位；无符号变体（`div.u`/`rem.u`）结果按零扩展写满 64 位。

### §6.2 比较操作

#### §6.2.1 立即数比较（rrii 格式）

比较结果按小于/等于/大于分别设置目的寄存器为 −1/0/1，写入全 64 位。[SimRISC-04 §比较操作]

| 指令 | 语义 | 来源 |
|------|------|------|
| `cmp.si rdha, rdhb, imms12` | 有符号比较，`rdha = cmp(rdhb, sign_extend(imms12))` | [SimRISC-04 §比较操作] |
| `cmp.ui rdha, rdhb, immu12` | 无符号比较，`rdha = cmp(rdhb, zero_extend(immu12))` | [SimRISC-04 §比较操作] |

#### §6.2.2 64 位寄存器比较（orrr 格式）

源操作数按 size 截断后比较，结果（−1/0/1）写入目的寄存器全 64 位。[SimRISC-04 §比较操作]

| 指令 | 位宽 | 比较范围 |
|------|------|---------|
| `cmp.uo`/`cmp.so` | 64 位 | bits[63:0] 全 64 位 |

- 汇编语法：`cmp.uo rdhb, rdhc, rdhd`。[SimRISC-04 §比较操作]
- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-04 §比较操作]
- 32/16/8 位比较分别见 §10.2、§11.2、§12.2。

### §6.3 64 位逻辑运算（orrr 格式）

`MISC-octa` 子表中的 `and`/`or`/`xor`/`xnor` 提供 64 位逻辑运算。[SimRISC-04 §Logic operators：逻辑运算]

| 指令 | 位宽 | 操作范围 |
|------|------|---------|
| `and.o`/`or.o`/`xor.o`/`xnor.o` | 64 位 | bits[63:0] 全 64 位参与 |

运算规则：[SimRISC-04 §Logic operators：逻辑运算]
- `and`：全一为一，有零为零
- `or`：全零为零，有一为一
- `xor`：相异为一，相同为零
- `xnor`：相同为一，相异为零

> 无专门 not 指令；当 `rdhc` 或 `rdhd` 为 `rd0` 时，`xnor` 实现另一操作数取反。[SimRISC-04 §Logic operators：逻辑运算]

- 32/16/8 位逻辑运算分别见 §10.3、§11.3、§12.3。

### §6.4 位操作

#### §6.4.1 64 位移位（orrr / orri 格式）— 值语义

`shl` 为左移，`shr` 为右移；后缀 `u` 表示逻辑移位（零扩展），`s` 表示算术移位（符号扩展）。移位量（shamt）取 `rdhd` 的低位（orrr）或 `immu6` 的低位（orri）。[SimRISC-04 §Bit manipulating：位操作指令]

```
shl.u: rdhb[N:0]   = (rdhc[N:0] << shamt)                // 左移，低位补零
shr.u: rdhb[N:0]   = (rdhc[N:0] >> shamt)                // 逻辑右移，高位补零
shr.s: rdhb[N:0]   = (rdhc[N:0] >> shamt) with sign(N)   // 算术右移，高位补 rdhc[N]
```
[SimRISC-04 §Bit manipulating：位操作指令]

**SPEC-069t 值语义通则**：所有移位/比较指令的结果均写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。64 位操作 N=63 自然写满；32/16/8 位操作的高位扩展规则见 §10.4.1/§11.4.1/§12.4.1。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.uo`/`shr.uo`/`shr.so` | 63 | 0–63 | `hd[5:0]` 全有效 |
[SimRISC-04 §Bit manipulating：位操作指令]

异常条件：`shamt > N` → **ILLI**。[SimRISC-04 §Bit manipulating：位操作指令]

- 32/16/8 位移位分别见 §10.4.1、§11.4.1、§12.4.1。

#### §6.4.2 64 位符号/零扩展（orrr / orri 格式）

`ext.s` 为符号扩展，`ext.u` 为零扩展；`hd`（orrr）或 `immu6`（orri）为扩展起始位。[SimRISC-04 §Bit manipulating：位操作指令]

```
rdhb[hd:0]   = rdhc[hd:0]                               // 复制源低位
rdhb[63:hd+1] = sign/zero_extend(rdhc[hd])               // 符号/零扩展（N=63）
```
[SimRISC-04 §Bit manipulating：位操作指令]

> **SPEC-069t**：64位 ext（N=63）自然写满64位；32/16/8 位 ext 已删除（§10.4.2/§11.4.2/§12.4.2）。

| 指令 | N | 汇编语法 | 约束 |
|------|---|---------|------|
| `ext.uo`/`ext.so` | 63 | `ext.uo rdhb, rdhc, rdhd` 或 `ext.uo rdhb, rdhc, immu6` | hd ≤ 63 |
[SimRISC-04 §Bit manipulating：位操作指令]

异常条件：`hd > N` → **ILLI**。[SimRISC-04 §Bit manipulating：位操作指令]

- 32/16/8 位扩展分别见 §10.4.2、§11.4.2、§12.4.2。

### §6.5 条件赋值（rrrr 格式）

第一类根据 `rdha` 的值判断，将 `rdhc` 或 `rdhd` 赋给 `rdhb`：[SimRISC-02 §条件赋值：Conditional Assignment]

| 指令 | 语义 | 来源 |
|------|------|------|
| `cs.n rdha, rdhb, rdhc, rdhd` | `if (rdha < 0) rdhb = rdhc; else rdhb = rdhd` | [SimRISC-02 §条件赋值：Conditional Assignment] |
| `cs.z rdha, rdhb, rdhc, rdhd` | `if (rdha == 0) rdhb = rdhc; else rdhb = rdhd` | [SimRISC-02 §条件赋值：Conditional Assignment] |
| `cs.p rdha, rdhb, rdhc, rdhd` | `if (rdha > 0) rdhb = rdhc; else rdhb = rdhd` | [SimRISC-02 §条件赋值：Conditional Assignment] |

第二类根据 `rdha` 与 `rdhb` 是否相等判断，条件成立时将 `rdhd` 赋给 `rdhc`：[SimRISC-02 §条件赋值：Conditional Assignment]

| 指令 | 语义 | 来源 |
|------|------|------|
| `cs.eq rdha, rdhb, rdhc, rdhd` | `if (rdha == rdhb) rdhc = rdhd` | [SimRISC-02 §条件赋值：Conditional Assignment] |
| `cs.ne rdha, rdhb, rdhc, rdhd` | `if (rdha != rdhb) rdhc = rdhd` | [SimRISC-02 §条件赋值：Conditional Assignment] |

### §6.6 伪指令（64 位数据运算）

伪指令不是硬件指令，汇编器将其展开为一条或多条硬件指令。[SimRISC-00 §伪指令]

| 伪指令 | 展开形式 | 说明 | 来源 |
|--------|----------|------|------|
| `not.o rdhb, rdhc` | `xnor.o rdhb, rdhc, rd0` | 64 位按位取反 | [SimRISC-04 §not 伪指令] |
| `neg.o rdhb, rdhc` | `sub.so rd0, rdhb, rd0, rdhc` | 64 位取负 | [SimRISC-04 §neg 伪指令] |

---

## §7 64 位地址运算指令

> 范围：RB 寄存器组的算术运算和比较操作。RB 存取见 §3.2；RB 立即数设置见 §5.2。

### §7.1 RB 加减（orrr 格式）

针对 RB 的加减运算，操作数类型 `orrr`；两个源为 `rbhc` 和 `rdhd`，目的为 `rbhb`。[SimRISC-05 §加减操作]

| 指令 | 语义 | 来源 |
|------|------|------|
| `add.so rbhb, rbhc, rdhd` | 二进制补码 64 位加法，全 64 位参与运算 | [SimRISC-05 §加减操作] |
| `sub.so rbhb, rbhc, rdhd` | 二进制补码 64 位减法，全 64 位参与运算 | [SimRISC-05 §加减操作] |

- 地址计算仅在低 48 位有效，溢出丢弃；用户可通过 `rbhb` 的高 16 位（bits[63:48]）判断是否发生地址溢出。[SimRISC-05 §加减操作]

### §7.2 RB 自增自减（riii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `add.si rbha, imms18` | `rbha = rbha + sign_extend(imms18)`，全 64 位运算 | [SimRISC-05 §自增自减] |

- 立即数 18 位有符号，补码编码，无需区分加减。[SimRISC-05 §自增自减]
- 用户可通过 `rbha` 的高 16 位判断地址溢出。[SimRISC-05 §自增自减]
- 对栈指针的操作很重要；在没有专门 push/pop 指令的情况下，栈指针需通过显式加减移动。[SimRISC-05 §自增自减]

### §7.3 RB 比较（orrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| `cmp.uo rdhb, rbhc, rbhd` | **整 64 位**无符号比较，结果 −1/0/1 对应小于/等于/大于，写入 `rdhb` | [ADR-0012 D8.2][SimRISC-05 §比较操作] |

- 比较按**整 64 位**无符号；仅**作地址使用时**取低 48（见 D8.7）。[ADR-0012 D8.2]
- 后续指令可根据负数/非负数/零/非零/正数/非正数做出组合判断。[SimRISC-05 §比较操作]

---

## §8 控制流指令

### §8.1 通用约定

- SimRISC 指令都是 4 字节且 4 字节对齐；采用立即数作为偏移地址参与计算时，均将其左移 2 位以增大跳转范围。[SimRISC-06 §控制流指令]
- `rb0` 以 **64 位**参与地址计算；计算结果（64 位）**写回 `rb0`**，随后取 **`rb0[47:0]`（低 48 位）**作为下一条待执行指令的地址。[ADR-0012 D8.3]
- 条件跳转均采用相对地址。[SimRISC-06 §条件跳转指令]
- 跳转/调用地址计算按 64 位全宽进行；结果写回 `rb0`，取低 48 位为下一条地址；rrii 格式的 `rbHA` 仅读（不修改）。[ADR-0012 D8.3]

### §8.2 条件跳转指令

#### §8.2.1 双寄存器比较跳转（rrii 格式）

前两个操作数为 rd 寄存器，根据两者是否相等选择是否跳转。[SimRISC-06 §条件跳转指令]

| 指令 | 条件 | 地址计算 | 来源 |
|------|------|---------|------|
| `br.eq rdha, rdhb, imms12` | `rdha == rdhb` | `Addr = rb0 + (imms12 << 2)` | [SimRISC-06 §条件跳转指令] |
| `br.ne rdha, rdhb, imms12` | `rdha != rdhb` | `Addr = rb0 + (imms12 << 2)` | [SimRISC-06 §条件跳转指令] |

- 64 位地址计算 `Addr = rb0 + (imms12 << 2)`，结果写回 `rb0`，取低 48 位为下一条地址。[ADR-0012 D8.3]

#### §8.2.2 单寄存器条件跳转（riii 格式）

一个操作数为 rd 寄存器，根据该寄存器的值判断是否跳转。[SimRISC-06 §条件跳转指令]

| 指令 | 条件 | 地址计算 | 来源 |
|------|------|---------|------|
| `br.n rdha, imms18` | `rdha < 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |
| `br.nn rdha, imms18` | `rdha >= 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |
| `br.z rdha, imms18` | `rdha == 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |
| `br.nz rdha, imms18` | `rdha != 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |
| `br.p rdha, imms18` | `rdha > 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |
| `br.np rdha, imms18` | `rdha <= 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |

- 特例：`rdha` 为 `rd0` 时，`br.z` 条件必为真，`br.nz` 条件必为假。[SimRISC-06 §条件跳转指令]

#### §8.2.3 RB 条件跳转（riii 格式）

操作数为 rb 寄存器，根据 `rbha` 是否为 0 判断。[SimRISC-06 §条件跳转指令]

| 指令 | 条件 | 地址计算 | 来源 |
|------|------|---------|------|
| `br.z rbha, imms18` | `rbha == 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |
| `br.nz rbha, imms18` | `rbha != 0` | `Addr = rb0 + (imms18 << 2)` | [SimRISC-06 §条件跳转指令] |

- 跳转地址计算方式与 §8.2.2 一致。[SimRISC-06 §条件跳转指令]

### §8.3 无条件跳转指令

既支持相对地址，也支持绝对地址。[SimRISC-06 §无条件跳转指令]

| 指令 | 格式 | 地址计算 | 来源 |
|------|------|---------|------|
| `jump imms24` | iiii | `Addr = rb0 + (imms24 << 2)` | [SimRISC-06 §无条件跳转指令] |
| `jump rbha, rdhb, imms12` | rrii | `Addr = rbha + rdhb + (imms12 << 2)` | [SimRISC-06 §无条件跳转指令] |

- 跳转/调用地址计算按 64 位全宽进行；结果写回 `rb0`，取低 48 位为下一条地址；rrii 格式的 `rbHA` 仅读（不修改）。[ADR-0012 D8.3]
- `ha` 为基址寄存器（rb），`hb` 为偏移地址（rd）；当 `ha` 为 `rb0` 时，`rdhb + (imms12 << 2)` 仍是相对地址跳转。[SimRISC-06 §无条件跳转指令]

### §8.4 函数调用

函数调用与无条件跳转类似，但会计算返回地址并压入 `ra63`（RegRAS 栈顶）；`[63:48]` 为递归计数（首次压栈设为 1，递归调用递增），`[47:0]` 为返回地址。压栈流程见 §8.6。[SimRISC-06 §函数调用]

| 指令 | 格式 | 地址计算 | 来源 |
|------|------|---------|------|
| `call imms24` | iiii | `Addr = rb0 + (imms24 << 2)` | [SimRISC-06 §函数调用] |
| `call rbha, rdhb, imms12` | rrii | `Addr = rbha + rdhb + (imms12 << 2)` | [SimRISC-06 §函数调用] |

- 地址计算按 64 位全宽进行；结果写回 `rb0`，取低 48 位为下一条地址；rrii 格式的 `rbHA` 仅读（不修改）。[ADR-0012 D8.3]
- `ha` 为基址寄存器（rb），`hb` 为偏移地址（rd）；当 `ha` 为 `rb0` 时，`rdhb + (imms12 << 2)` 实际上也是相对地址跳转。[SimRISC-06 §函数调用]

### §8.5 函数返回

`ret` 从返回地址栈（RAS）弹出返回地址并跳转过去。返回地址来源**可能不是 `ra63`**（取决于 RAS 状态），可能触发 **RASUF** 异常。弹栈流程见 §8.6。[ADR-0012 D8.5]

| 指令 | 语义 | 来源 |
|------|------|------|
| `ret rdha, imms18` | 在返回的同时，修改 `rdha` 为 18 位立即数（符号扩展至 64 位），PC = 弹出的返回地址 | [SimRISC-06 §函数返回] |

- 通常该寄存器为返回值寄存器，可用一条 `ret` 实现 C 语言的 `return 0` 或 `return -1`。[SimRISC-06 §函数返回]
- 无需设置返回值寄存器时，采用 `ret rd0, 0` 实现普通 ret（`rdha` 为 rd0 允许）。[SimRISC-06 §函数返回]
- 弹栈流程见 §8.6。[SimRISC-00 §弹栈流程（ret 指令）]

### §8.6 压栈 / 弹栈流程（RegRAS / MemRAS）

压/弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 [SimRISC-00 §返回地址栈]。以下为概要。

#### §8.6.1 压栈流程（call 指令）

压栈按 C1/C2/C3a/C3b 四种情形处理：[SimRISC-00 §压栈流程]

- **C1** `RACNT == 0` → 压入新条目（递归计数 = 1、返回地址），`RACNT = 1`。
- **C2** `RACNT > 0` 且 返回地址 == `ra63[47:0]` 且 `ra63[63:48] < 0xFFFF` → **递归折叠优先**：`ra63[63:48] += 1`，`RACNT` 不变。
- **C3** 其余：**C3a** `RACNT < 63` → 压入新条目（递归计数 = 1），`RACNT += 1`；**C3b** `RACNT == 63` → ① `MRPTR == 0` → **RASOF**；② `MRPTR −= 8` 并把栈底条目写入 `MRPTR` 处；③ 压入新条目 ⇒ `RACNT` 保持 63。

#### §8.6.2 弹栈流程（ret 指令）

弹栈按 D1/D2/D3/D4a/D4b 五种情形处理：[SimRISC-00 §弹栈流程]

- **D1** `RACNT > 0` 且 `ra63[63:48] == 0` → **RASUF**。
- **D2** `RACNT > 0` 且 `ra63[63:48] > 1` → 计数 −1，`RACNT` 不变。
- **D3** `RACNT > 0` 且 `ra63[63:48] == 1` → 弹出栈顶，`RACNT − 1`。
- **D4** `RACNT == 0` → **D4a** `MRPTR == 0` → **RASUF**；**D4b** 读 `MRPTR` 处条目（`MRPTR` 暂不修改）：递归计数 = 0 → **RASUF**、= 1 → 返回地址 = 条目低 48 且 `MRPTR += 8`、> 1 → 该条目压入成为栈顶（计数 −1）且 `MRPTR += 8`、`RACNT = 1`。

### §8.7 伪指令（控制流）

| 伪指令 | 展开形式 | 说明 | 来源 |
|--------|----------|------|------|
| `return` | `ret rd0, 0` | 无返回值的函数返回 | [SimRISC-06 §return 伪指令] |

---

## §9 浮点运算指令 — Excluded from M1

浮点类指令（SimRISC-07）整体 **Excluded from M1**，本合约不提取其规范内容。[SimRISC-07 §版本]

- 范围：`ld.t`/`st.t`/`ld.o`/`st.o`/`ldm.t`/`stm.t`/`ldm.o`/`stm.o`（RF 存取）、`rf2rd`/`rd2rf`、`set.w`、格式转换、浮点算术/符号位/比较/条件赋值/分类指令、`set.ft`/`set.fo` 伪指令。
- 唯一例外：`rf0`（FCSR）的寄存器模型/位布局属 §1.3.3，M1 测试机复位值需要，已在 §1.3.3 提取。
- 浮点指令的 rf0 操作数约定（**目的**为 rf0 → ILLI；作**源**合法）等属浮点内容，M1 不提取。[SimRISC-00 §浮点寄存器]
- 完整浮点规范与编码留后续阶段（见 `.tao/knowledge/deferred.md`）。

---

## §10 32 位数据运算指令

> 范围：RD 寄存器组的 32 位（tetra）运算指令。64 位运算见 §6；16 位见 §11；8 位见 §12。

### §10.1 算术运算

#### §10.1.1 32 位加减法（orrr 格式）

`MISC-tetra` 子表中的 `add`/`sub` 提供 32 位加减运算，仅低 32 位参与运算，溢出部分静默丢弃，结果按符号类型扩展至 64 位。[SimRISC-08 §加减操作]

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `add.ut`/`sub.ut` | 32 位 | `add.ut rdhb, rdhc, rdhd` | 零扩展 |
| `add.st`/`sub.st` | 32 位 | `add.st rdhb, rdhc, rdhd` | 符号扩展 |

异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-08 §加减操作]

#### §10.1.2 32 位乘除余（orrr 格式）

`MISC-tetra` 子表中的 `mul`/`div`/`rem` 提供 32 位运算。[SimRISC-08 §乘除操作]

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ut`/`mul.st`/`div.ut`/`div.st`/`rem.ut`/`rem.st` | 32 位 | `mul.ut rdhb, rdhc, rdhd` |

- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-08 §乘除操作]
- 除法附加规则见 §6.1.5。

### §10.2 32 位比较（orrr 格式）— 值语义

源操作数按 size 截断后比较，结果（−1/0/1）写入目的寄存器全 64 位。[SimRISC-08 §比较操作]

| 指令 | 位宽 | 比较范围 |
|------|------|---------|
| `cmp.ut`/`cmp.st` | 32 位 | bits[31:0] |

- 汇编语法：`cmp.ut rdhb, rdhc, rdhd`。[SimRISC-08 §比较操作]
- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-08 §比较操作]
- **高位规则（SPEC-069t）**：比较结果 −1/0/+1 按后缀扩展写满64位——`.st` ⇒ 符号扩展；`.ut` ⇒ 零扩展。

### §10.3 32 位逻辑运算 — 已删除

**SPEC-069t**：`and.t`/`or.t`/`xor.t`/`xnor.t` 已从指令集中删除。64 位逻辑运算见 §6.3。

### §10.4 位操作

#### §10.4.1 32 位移位（orrr / orri 格式）— 值语义

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.ut`/`shr.ut`/`shr.st` | 31 | 0–31 | `hd[4:0]`，`hd[5]` 应为零 |
[SimRISC-08 §Bit manipulating：位操作指令]

运算公式（**SPEC-069t：值语义，写满64位**）：
```
shl.ut:  rdhb[31:0]  = (rdhc[31:0] << shamt)              // 左移，低位补零
         rdhb[63:32] = 0                                     // 高位零扩展
shr.ut:  rdhb[31:0]  = (rdhc[31:0] >> shamt)               // 逻辑右移，高位补零
         rdhb[63:32] = 0                                     // 高位零扩展
shr.st:  rdhb[31:0]  = (rdhc[31:0] >> shamt) with sign(31) // 算术右移，高位补 rdhc[31]
         rdhb[63:32] = sign_extend(rdhc[31])                 // 高位符号扩展
```

异常条件：`shamt > N` → **ILLI**。[SimRISC-08 §Bit manipulating：位操作指令]

#### §10.4.2 32 位符号/零扩展 — 已删除

**SPEC-069t**：`ext.ut`/`ext.st` 已从指令集中删除。64 位扩展见 §6.4.2。

### §10.5 伪指令（32 位数据运算）

| 伪指令 | 展开形式 | 说明 | 来源 |
|--------|----------|------|------|
| `neg.t rdhb, rdhc` | `sub.st rdhb, rd0, rdhc` | 32 位取负，符号扩展 | [SimRISC-08 §neg 伪指令] |

> **SPEC-069t**：`not.t` 已删除（窄位宽逻辑指令 `xnor.t` 已不存在）；仅保留 `not.o`（§6.6）。

---

## §11 16 位数据运算指令

> 范围：RD 寄存器组的 16 位（wyde）运算指令。64 位运算见 §6；32 位见 §10；8 位见 §12。

### §11.1 算术运算

#### §11.1.1 16 位加减法（orrr 格式）

`MISC-wyde` 子表中的 `add`/`sub` 提供 16 位加减运算，仅低 16 位参与运算，溢出部分静默丢弃，结果按符号类型扩展至 64 位。[SimRISC-09 §加减操作]

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `add.uw`/`sub.uw` | 16 位 | `add.uw rdhb, rdhc, rdhd` | 零扩展 |
| `add.sw`/`sub.sw` | 16 位 | `add.sw rdhb, rdhc, rdhd` | 符号扩展 |

异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-09 §加减操作]

#### §11.1.2 16 位乘除余（orrr 格式）

`MISC-wyde` 子表中的 `mul`/`div`/`rem` 提供 16 位运算。[SimRISC-09 §乘除操作]

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.uw`/`mul.sw`/`div.uw`/`div.sw`/`rem.uw`/`rem.sw` | 16 位 | `mul.uw rdhb, rdhc, rdhd` |

- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-09 §乘除操作]
- 除法附加规则见 §6.1.5。

### §11.2 16 位比较（orrr 格式）— 值语义

源操作数按 size 截断后比较，结果（−1/0/1）写入目的寄存器全 64 位。[SimRISC-09 §比较操作]

| 指令 | 位宽 | 比较范围 |
|------|------|---------|
| `cmp.uw`/`cmp.sw` | 16 位 | bits[15:0] |

- 汇编语法：`cmp.uw rdhb, rdhc, rdhd`。[SimRISC-09 §比较操作]
- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-09 §比较操作]
- **高位规则（SPEC-069t）**：比较结果 −1/0/+1 按后缀扩展写满64位——`.sw` ⇒ 符号扩展；`.uw` ⇒ 零扩展。

### §11.3 16 位逻辑运算 — 已删除

**SPEC-069t**：`and.w`/`or.w`/`xor.w`/`xnor.w` 已从指令集中删除。64 位逻辑运算见 §6.3。

### §11.4 位操作

#### §11.4.1 16 位移位（orrr / orri 格式）— 值语义

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.uw`/`shr.uw`/`shr.sw` | 15 | 0–15 | `hd[3:0]`，`hd[5:4]` 应为零 |
[SimRISC-09 §Bit manipulating：位操作指令]

运算公式（**SPEC-069t：值语义，写满64位**）：
```
shl.uw:  rdhb[15:0]  = (rdhc[15:0] << shamt)
         rdhb[63:16] = 0                                     // 高位零扩展
shr.uw:  rdhb[15:0]  = (rdhc[15:0] >> shamt)
         rdhb[63:16] = 0                                     // 高位零扩展
shr.sw:  rdhb[15:0]  = (rdhc[15:0] >> shamt) with sign(15)
         rdhb[63:16] = sign_extend(rdhc[15])                 // 高位符号扩展
```

异常条件：`shamt > N` → **ILLI**。[SimRISC-09 §Bit manipulating：位操作指令]

#### §11.4.2 16 位符号/零扩展 — 已删除

**SPEC-069t**：`ext.uw`/`ext.sw` 已从指令集中删除。64 位扩展见 §6.4.2。

### §11.5 伪指令（16 位数据运算）

| 伪指令 | 展开形式 | 说明 | 来源 |
|--------|----------|------|------|
| `neg.w rdhb, rdhc` | `sub.sw rdhb, rd0, rdhc` | 16 位取负，符号扩展 | [SimRISC-09 §neg 伪指令] |

> **SPEC-069t**：`not.w` 已删除（窄位宽逻辑指令 `xnor.w` 已不存在）；仅保留 `not.o`（§6.6）。

---

## §12 8 位数据运算指令

> 范围：RD 寄存器组的 8 位（byte）运算指令。64 位运算见 §6；32 位见 §10；16 位见 §11。

### §12.1 算术运算

#### §12.1.1 8 位加减法（orrr 格式）

`MISC-byte` 子表中的 `add`/`sub` 提供 8 位加减运算，仅低 8 位参与运算，溢出部分静默丢弃，结果按符号类型扩展至 64 位。[SimRISC-10 §加减操作]

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `add.ub`/`sub.ub` | 8 位 | `add.ub rdhb, rdhc, rdhd` | 零扩展 |
| `add.sb`/`sub.sb` | 8 位 | `add.sb rdhb, rdhc, rdhd` | 符号扩展 |

异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-10 §加减操作]

#### §12.1.2 8 位乘除余（orrr 格式）

`MISC-byte` 子表中的 `mul`/`div`/`rem` 提供 8 位运算。[SimRISC-10 §乘除操作]

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ub`/`mul.sb`/`div.ub`/`div.sb`/`rem.ub`/`rem.sb` | 8 位 | `mul.ub rdhb, rdhc, rdhd` |

- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-10 §乘除操作]
- 除法附加规则见 §6.1.5。

### §12.2 8 位比较（orrr 格式）— 值语义

源操作数按 size 截断后比较，结果（−1/0/1）写入目的寄存器全 64 位。[SimRISC-10 §比较操作]

| 指令 | 位宽 | 比较范围 |
|------|------|---------|
| `cmp.ub`/`cmp.sb` | 8 位 | bits[7:0] |

- 汇编语法：`cmp.ub rdhb, rdhc, rdhd`。[SimRISC-10 §比较操作]
- 异常条件：`rdhb` 为 `rd0` → **ILLI**。[SimRISC-10 §比较操作]
- **高位规则（SPEC-069t）**：比较结果 −1/0/+1 按后缀扩展写满64位——`.sb` ⇒ 符号扩展；`.ub` ⇒ 零扩展。

### §12.3 8 位逻辑运算 — 已删除

**SPEC-069t**：`and.b`/`or.b`/`xor.b`/`xnor.b` 已从指令集中删除。64 位逻辑运算见 §6.3。

### §12.4 位操作

#### §12.4.1 8 位移位（orrr / orri 格式）— 值语义

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.ub`/`shr.ub`/`shr.sb` | 7 | 0–7 | `hd[2:0]`，`hd[5:3]` 应为零 |
[SimRISC-10 §Bit manipulating：位操作指令]

运算公式（**SPEC-069t：值语义，写满64位**）：
```
shl.ub:  rdhb[7:0]   = (rdhc[7:0] << shamt)
         rdhb[63:8]  = 0                                     // 高位零扩展
shr.ub:  rdhb[7:0]   = (rdhc[7:0] >> shamt)
         rdhb[63:8]  = 0                                     // 高位零扩展
shr.sb:  rdhb[7:0]   = (rdhc[7:0] >> shamt) with sign(7)
         rdhb[63:8]  = sign_extend(rdhc[7])                  // 高位符号扩展
```

异常条件：`shamt > N` → **ILLI**。[SimRISC-10 §Bit manipulating：位操作指令]

#### §12.4.2 8 位符号/零扩展 — 已删除

**SPEC-069t**：`ext.ub`/`ext.sb` 已从指令集中删除。64 位扩展见 §6.4.2。

### §12.5 伪指令（8 位数据运算）

| 伪指令 | 展开形式 | 说明 | 来源 |
|--------|----------|------|------|
| `neg.b rdhb, rdhc` | `sub.sb rdhb, rd0, rdhc` | 8 位取负，符号扩展 | [SimRISC-10 §neg 伪指令] |

> **SPEC-069t**：`not.b` 已删除（窄位宽逻辑指令 `xnor.b` 已不存在）；仅保留 `not.o`（§6.6）。

---

## §13 其它指令

> 范围：占位指令 `swym`、非法指令 `illi`、NOP 伪指令、保留编码与全零指令。特权 cfx 指令与 LR-SC 原子指令见 §14（Excluded from M1）。

### §13.1 占位指令 swym（oiii 格式）

当指令地址需要对齐或特意留出空白时使用占位指令；SimRISC 采用 `swym`（参考 Knuth 的 MMIX）。[SimRISC-11 §占位指令]

| 指令 | 语义 | 来源 |
|------|------|------|
| `swym 0` | 除 PC 自增外无任何架构副作用（等同于 nop） | [SimRISC-11 §占位指令] |
| `swym N` | 硬件时延指令，后 18 位立即数为时延参数，时延约为 `swym 0` 的 N+1 倍 | [SimRISC-11 §占位指令] |

- 硬件可设时延上限，N 超过阈值后时延不再增加。[SimRISC-11 §占位指令]
- 无论 N 取何值，指令仍为单条 32 位指令，不占用额外指令带宽。[SimRISC-11 §占位指令]

### §13.2 非法指令 illi（oiii 格式）

SimRISC 采用 `illi` 作为专门的非法指令（illegal instruction）。[SimRISC-11 §非法指令]

| 指令 | 语义 | 来源 |
|------|------|------|
| `illi 0` | 引发 **ILLI** 异常 | [SimRISC-11 §非法指令] |

- `illi` 的后 18 位立即数无特殊含义，完全由用户/软件自定义，用户可通过操作系统机制捕获该异常并做功能扩展。[SimRISC-11 §非法指令]
- 不建议捕获其它指令产生的非法指令异常做功能扩展（例如很多指令不允许目的为 rd0，否则引发非法指令异常）。[SimRISC-11 §非法指令]
- `illi` 的 op = 0111-0111（0x77），`illi 0` 的编码为 0x77000000。MISC-AMO 编码变更后，32 位全零指令字（0x00000000）不再是 `illi 0`，而是保留编码，触发 **UNDI** 异常（见 §2.9）。[SimRISC-11 §非法指令]

### §13.3 伪指令 nop

| 伪指令 | 展开形式 | 说明 | 来源 |
|--------|----------|------|------|
| `nop` | `swym 0` | 空操作，占位或对齐 | [SimRISC-11 §nop 伪指令] |

### §13.4 保留编码（UNDI）

QFC 主表与各 MISC 子表的空白单元格为 reserved（保留未分配）；执行保留编码触发 **UNDI** 异常。[SimRISC-00 §SimRISC QFC]

### §13.5 全零指令（UNDI）

MISC-AMO 编码变更后，32 位全零指令字（0x00000000）的 op = 0x00 在 QFC 主表为空白单元格（reserved），触发 **UNDI** 异常（非 ILLI）。`illi 0` 的编码已变更为 0x77000000（op = 0x77）。[SimRISC-11 §非法指令][SimRISC-00 §SimRISC QFC]

> 注意：`illi` 指令本身（op=0x77）触发 ILLI（§13.2），而全零字（op=0x00，保留编码）触发 UNDI（§13.5/§13.4），二者不同。[SimRISC-11 §非法指令][SimRISC-00 §SimRISC QFC]

---

## §14 待定指令 — Excluded from M1

> 范围：fence 指令、LR-SC 原子指令、特权 cfx 系统指令。均 **Excluded from M1**，本合约不提取其完整规范内容。

### §14.1 fence 指令（oiii 格式）

`fence` 指令对外部可见的访存请求（如设备 I/O 和内存访问）进行串行化。[SimRISC-12 §fence指令]

| 指令 | 语义 | 来源 |
|------|------|------|
| `fence immu18` | 内存序屏障，低 4 位编码屏障类型 | [SimRISC-12 §fence指令] |

低 4 位屏障类型编码：[SimRISC-12 §fence指令]

| 位 | 含义 | 说明 |
|----|------|------|
| bit0 | IO | 设备 I/O 访问串行化 |
| bit1 | W | 写屏障：前序写对后序写可见 |
| bit2 | R | 读屏障：前序读对后序读/写可见 |
| bit3 | RW | 读写屏障：前序读写对后序读写可见（全屏障） |

- bits[17:4] 应为零（SBZ），非零值行为保留。[SimRISC-12 §fence指令]

### §14.2 LR-SC 原子指令 — Excluded from M1

`lr`/`sc` 原子指令（`lr_nn.o`/`lr_nr.o`/`lr_an.o`/`lr_ar.o`、`sc_nn.o`/`sc_nr.o`/`sc_an.o`/`sc_ar.o`）**Excluded from M1**，本合约不提取其规范内容。[SimRISC-12 §LR-SC指令]

- 完整语义/编码/保留机制留后续阶段（见 `.tao/knowledge/deferred.md`）。
- 编码位置：`MISC-AMO` 子表 ha = 010-xxx（lr）与 011-xxx（sc）。[SimRISC-00 §MISC-AMO 指令编码]

### §14.3 特权 cfx 系统指令 — Excluded from M1

以下特权态指令 **Excluded from M1**，本合约不提取其规范内容：[SimRISC-11 §特权指令]

| 指令 | 格式 | 来源 |
|------|------|------|
| `trap cfx_<cfxname>, immu18` | ciii | [SimRISC-11 §陷入指令] |
| `escape cfx_<cfxname>, imms18` | ciii | [SimRISC-11 §退出指令] |
| `cfx2rd`/`cfx2rc cfx_<cfxname>, cghb, rchc, rdhd` | crrr | [SimRISC-11 §寄存器传输指令] |
| `cfxld`/`cfxst cfx_<cfxname>, rbhb, immu12` | crii | [SimRISC-12 §SRAM块传输指令] |

- 涉及异常 **CFXREG**、cfx reserved 编号（7–14、19–61）等均属特权内容，M1 不提取。[SimRISC-11 §寄存器传输指令]
- 编码位置：op = 0111-1010 ~ 0111-1111（cfx2rd/cfx2rc/cfxld/cfxst/escape/trap）。[SimRISC-00 §SimRISC QFC]

---

## §15 异常总结

M1 范围内的异常：[SimRISC-00 §指令设计][SimRISC-00 §压栈流程（call 指令）][SimRISC-00 §弹栈流程（ret 指令）][SimRISC-01 §存取RD寄存器][SimRISC-11 §非法指令]

| 异常 | 触发条件 | 来源 |
|------|---------|------|
| **ILLI** | 非法指令/非法操作数约束违反（详见下方清单） | [SimRISC-11 §非法指令] |
| **MALIGN** | 内存访问未对齐（load/store、多 load/store、RB 存取、RA 存取） | [SimRISC-01 §存取RD寄存器][SimRISC-01 §存取RB寄存器][SimRISC-01 §存取RA寄存器] |
| **UNDI** | 执行保留编码（QFC 主表 / MISC 子表空白单元格） | [SimRISC-00 §SimRISC QFC] |
| **IALIGN** | 取指时 `PC[1:0] ≠ 00` | [SimRISC-00 §指令设计] |
| **RASOF** | RegRAS 满栈（`RACNT == 63`）且需溢出到 MemRAS 但 `MRPTR == 0` | [SimRISC-00 §压栈流程] |
| **RASUF** | `RACNT > 0` 且递归计数 == 0（D1）；或 `RACNT == 0` 且 `MRPTR == 0`（D4a）；或 MemRAS 条目递归计数 == 0（D4b） | [SimRISC-00 §弹栈流程] |

> CFXREG 异常仅由特权 cfx 指令产生，Excluded from M1，不列入本表。[SimRISC-11 §寄存器传输指令]

### §15.1 ILLI 触发场景（M1 汇总）

- 目的寄存器为 `rd0`（除 rrrr 双目的指令允许一个为 rd0、`ret rd0, 0` 允许外；`st`/`stm` 的源为 rd0 允许，见 ADR-0015 D2/D3）。[SimRISC-00 §数据寄存器]
- 目的寄存器为 `rb0`（`st.o`/`stm.o` 的源为 rb0 允许，见 ADR-0015 D1/D3）。[SimRISC-00 §基址寄存器]
- `ld`（RD）目的 `rdha` 为 `rd0`。[SimRISC-01 §存取RD寄存器]
- `ldm`（RD）`rdha` 为 `rd0`、`immu6 = 0`、或 `rdha + immu6 > 64`。[SimRISC-01 §存取RD寄存器]
- 块赋值（`rd2rd`/`rb2rd`/`rd2rb`/`rb2rb`）`immu6 = 0`、目的为 `rd0`/`rb0`、或起始寄存器 + immu6 > 64。[SimRISC-02 §寄存器组之间块赋值][SimRISC-02 §寄存器组之间块赋值]
- `ld.o`/`ldm.o`（RB）`rbha` 为 `rb0`、`immu6 = 0`、或 `rbha + immu6 > 64`。`st.o`/`stm.o`（RB）`rbha` 为 `rb0` 允许（见 ADR-0015 D1/D3）。[SimRISC-01 §存取RB寄存器]
- `ldm.o`/`stm.o`（RA）`immu6 = 0`、或 `raha + immu6 > 64`（超出 ra63）。[SimRISC-01 §存取RA寄存器]
- 块赋值（`ra2rd`/`rd2ra`）`immu6 = 0`、任一起始寄存器 + immu6 > 64、或 `ra2rd` 目的 `rdhb` 为 `rd0`。[SimRISC-02 §寄存器组之间块赋值][SimRISC-00 §数据寄存器]
- 移位量 `shamt > N`。[SimRISC-04/08/09/10 §Bit manipulating：位操作指令]
- 扩展起始位 `hd > N`。[SimRISC-04/08/09/10 §Bit manipulating：位操作指令]
- `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so` 中 `rdha` 与 `rdhb` 同时为 `rd0`，或为同一非 `rd0` 寄存器。[SimRISC-04 §加减操作][SimRISC-04 §乘除操作]
- 固定位宽算术/比较/乘除余指令 `rdhb` 为 `rd0`。[SimRISC-04/08/09/10 §加减操作][SimRISC-04/08/09/10 §比较操作][SimRISC-04/08/09/10 §乘除操作]
- `illi` 指令本身（op=0x77000000）。[SimRISC-11 §非法指令]

### §15.2 精确异常承诺

- `div`/`rem` 中 `rdhb` 为 `rd0` 触发 ILLI 时目的寄存器未写入（无副作用）。除数为零和有符号溢出（INT_MIN ÷ −1）不再触发异常，改为定值语义（见 §6.1.5）。[SimRISC-04/08/09/10 §乘除操作][用户裁定 2026-10-01]
- RASOF/RASUF 触发时 RA 寄存器保持异常前状态（push/pop 未提交），PC 指向触发异常的 call/ret 指令。[SimRISC-00 §返回地址栈]
- MemRAS 访存异常时硬件保证精确异常（压栈/弹栈未执行，PC 指向 call/ret 指令），异常处理后可重新执行。[SimRISC-00 §返回地址栈]

---

## 附录 A：M1 指令编码清单

### A.1 QFC 主表（op[7:0]，M1 指令）

| op (hex) | op (bits) | 格式 | insn | 助记符 | 来源 |
|----------|-----------|------|------|--------|------|
| 0x77 | 0111-0111 | — | MISC-AMO | （见 A.6） | [SimRISC-00 §SimRISC QFC] |
| 0x10 | 0001-0000 | rrii | ld.ub-rd | `ld.ub` | [SimRISC-00 §SimRISC QFC] |
| 0x11 | 0001-0001 | rrii | ld.uw-rd | `ld.uw` | [SimRISC-00 §SimRISC QFC] |
| 0x12 | 0001-0010 | rrii | ld.ut-rd | `ld.ut` | [SimRISC-00 §SimRISC QFC] |
| 0x13 | 0001-0011 | rrii | ld.sb-rd | `ld.sb` | [SimRISC-00 §SimRISC QFC] |
| 0x14 | 0001-0100 | rrii | ld.sw-rd | `ld.sw` | [SimRISC-00 §SimRISC QFC] |
| 0x15 | 0001-0101 | rrii | ld.st-rd | `ld.st` | [SimRISC-00 §SimRISC QFC] |
| 0x18 | 0001-1000 | rrii | st.b-rd | `st.b` | [SimRISC-00 §SimRISC QFC] |
| 0x19 | 0001-1001 | rrii | st.w-rd | `st.w` | [SimRISC-00 §SimRISC QFC] |
| 0x1A | 0001-1010 | rrii | st.t-rd | `st.t` | [SimRISC-00 §SimRISC QFC] |
| 0x20 | 0010-0000 | rrii | ld.o-rd | `ld.o` | [SimRISC-00 §SimRISC QFC] |
| 0x21 | 0010-0001 | rrii | st.o-rd | `st.o` | [SimRISC-00 §SimRISC QFC] |
| 0x22 | 0010-0010 | rrii | ld.o-rb | `ld.o` | [SimRISC-00 §SimRISC QFC] |
| 0x23 | 0010-0011 | rrii | st.o-rb | `st.o` | [SimRISC-00 §SimRISC QFC] |
| 0x24 | 0010-0100 | rrii | ld.o-ra | `ld.o` | [SimRISC-00 §SimRISC QFC] |
| 0x25 | 0010-0101 | rrii | st.o-ra | `st.o` | [SimRISC-00 §SimRISC QFC] |
| 0x28 | 0010-1000 | rrri | ldm.ub-rd | `ldm.ub` | [SimRISC-00 §SimRISC QFC] |
| 0x29 | 0010-1001 | rrri | ldm.uw-rd | `ldm.uw` | [SimRISC-00 §SimRISC QFC] |
| 0x2A | 0010-1010 | rrri | ldm.ut-rd | `ldm.ut` | [SimRISC-00 §SimRISC QFC] |
| 0x2B | 0010-1011 | rrri | ldm.sb-rd | `ldm.sb` | [SimRISC-00 §SimRISC QFC] |
| 0x2C | 0010-1100 | rrri | ldm.sw-rd | `ldm.sw` | [SimRISC-00 §SimRISC QFC] |
| 0x2D | 0010-1101 | rrri | ldm.st-rd | `ldm.st` | [SimRISC-00 §SimRISC QFC] |
| 0x30 | 0011-0000 | rrri | stm.b-rd | `stm.b` | [SimRISC-00 §SimRISC QFC] |
| 0x31 | 0011-0001 | rrri | stm.w-rd | `stm.w` | [SimRISC-00 §SimRISC QFC] |
| 0x32 | 0011-0010 | rrri | stm.t-rd | `stm.t` | [SimRISC-00 §SimRISC QFC] |
| 0x38 | 0011-1000 | rrri | ldm.o-rd | `ldm.o` | [SimRISC-00 §SimRISC QFC] |
| 0x39 | 0011-1001 | rrri | stm.o-rd | `stm.o` | [SimRISC-00 §SimRISC QFC] |
| 0x3A | 0011-1010 | rrri | ldm.o-rb | `ldm.o` | [SimRISC-00 §SimRISC QFC] |
| 0x3B | 0011-1011 | rrri | stm.o-rb | `stm.o` | [SimRISC-00 §SimRISC QFC] |
| 0x3C | 0011-1100 | rrri | ldm.o-ra | `ldm.o` | [SimRISC-00 §SimRISC QFC] |
| 0x3D | 0011-1101 | rrri | stm.o-ra | `stm.o` | [SimRISC-00 §SimRISC QFC] |
| 0x40 | 0100-0000 | — | MISC-octa | （见 A.2） | [SimRISC-00 §SimRISC QFC] |
| 0x41 | 0100-0001 | — | MISC-tetra | （见 A.3） | [SimRISC-00 §SimRISC QFC] |
| 0x42 | 0100-0010 | — | MISC-wyde | （见 A.4） | [SimRISC-00 §SimRISC QFC] |
| 0x43 | 0100-0011 | — | MISC-byte | （见 A.5） | [SimRISC-00 §SimRISC QFC] |
| 0x48 | 0100-1000 | rwii | or.w-rd | `or.w` | [SimRISC-00 §SimRISC QFC] |
| 0x49 | 0100-1001 | rwii | andn.w-rd | `andn.w` | [SimRISC-00 §SimRISC QFC] |
| 0x4A | 0100-1010 | rwii | or.w-rb | `or.w` | [SimRISC-00 §SimRISC QFC] |
| 0x4B | 0100-1011 | rwii | andn.w-rb | `andn.w` | [SimRISC-00 §SimRISC QFC] |
| 0x4C | 0100-1100 | rwii | set.zw-rd | `set.zw` | [SimRISC-00 §SimRISC QFC] |
| 0x4D | 0100-1101 | rwii | set.ow-rd | `set.ow` | [SimRISC-00 §SimRISC QFC] |
| 0x4E | 0100-1110 | rwii | set.zw-rb | `set.zw` | [SimRISC-00 §SimRISC QFC] |
| 0x50 | 0101-0000 | rrrr | add.uo-rd | `add.uo` | [SimRISC-00 §SimRISC QFC] |
| 0x51 | 0101-0001 | rrrr | add.so-rd | `add.so` | [SimRISC-00 §SimRISC QFC] |
| 0x52 | 0101-0010 | rrrr | sub.uo-rd | `sub.uo` | [SimRISC-00 §SimRISC QFC] |
| 0x53 | 0101-0011 | rrrr | sub.so-rd | `sub.so` | [SimRISC-00 §SimRISC QFC] |
| 0x54 | 0101-0100 | rrrr | mul.uo-rd | `mul.uo` | [SimRISC-00 §SimRISC QFC] |
| 0x55 | 0101-0101 | rrrr | mul.so-rd | `mul.so` | [SimRISC-00 §SimRISC QFC] |
| 0x59 | 0101-1001 | riii | add.si-rd | `add.si` | [SimRISC-00 §SimRISC QFC] |
| 0x5A | 0101-1010 | riii | ~~rela.si-rb~~ UNDI | ~~`rela.si`~~ | [SimRISC-00 §SimRISC QFC][ADR-0012 D5] |
| 0x5B | 0101-1011 | riii | add.si-rb | `add.si` | [SimRISC-00 §SimRISC QFC] |
| 0x5C | 0101-1100 | rrii | cmp.ui-rd | `cmp.ui` | [SimRISC-00 §SimRISC QFC] |
| 0x5D | 0101-1101 | rrii | cmp.si-rd | `cmp.si` | [SimRISC-00 §SimRISC QFC] |
| 0x60 | 0110-0000 | rrrr | cs.n-rd | `cs.n` | [SimRISC-00 §SimRISC QFC] |
| 0x62 | 0110-0010 | rrrr | cs.z-rd | `cs.z` | [SimRISC-00 §SimRISC QFC] |
| 0x64 | 0110-0100 | rrrr | cs.p-rd | `cs.p` | [SimRISC-00 §SimRISC QFC] |
| 0x66 | 0110-0110 | rrrr | cs.eq-rd | `cs.eq` | [SimRISC-00 §SimRISC QFC] |
| 0x67 | 0110-0111 | rrrr | cs.ne-rd | `cs.ne` | [SimRISC-00 §SimRISC QFC] |
| 0x68 | 0110-1000 | riii | br.n-rd | `br.n` | [SimRISC-00 §SimRISC QFC] |
| 0x69 | 0110-1001 | riii | br.nn-rd | `br.nn` | [SimRISC-00 §SimRISC QFC] |
| 0x6A | 0110-1010 | riii | br.z-rd | `br.z` | [SimRISC-00 §SimRISC QFC] |
| 0x6B | 0110-1011 | riii | br.nz-rd | `br.nz` | [SimRISC-00 §SimRISC QFC] |
| 0x6C | 0110-1100 | riii | br.p-rd | `br.p` | [SimRISC-00 §SimRISC QFC] |
| 0x6D | 0110-1101 | riii | br.np-rd | `br.np` | [SimRISC-00 §SimRISC QFC] |
| 0x6E | 0110-1110 | rrii | br.eq-rd | `br.eq` | [SimRISC-00 §SimRISC QFC] |
| 0x6F | 0110-1111 | rrii | br.ne-rd | `br.ne` | [SimRISC-00 §SimRISC QFC] |
| 0x70 | 0111-0000 | iiii | jump-iiii | `jump` | [SimRISC-00 §SimRISC QFC] |
| 0x71 | 0111-0001 | rrii | jump-rrii | `jump` | [SimRISC-00 §SimRISC QFC] |
| 0x72 | 0111-0010 | riii | br.z-rb | `br.z` | [SimRISC-00 §SimRISC QFC] |
| 0x73 | 0111-0011 | riii | br.nz-rb | `br.nz` | [SimRISC-00 §SimRISC QFC] |
| 0x74 | 0111-0100 | iiii | call-iiii | `call` | [SimRISC-00 §SimRISC QFC] |
| 0x75 | 0111-0101 | rrii | call-rrii | `call` | [SimRISC-00 §SimRISC QFC] |
| 0x76 | 0111-0110 | riii | ret | `ret` | [SimRISC-00 §SimRISC QFC] |

### A.2 MISC-octa 子表（op = 0x40，opx 在 ha[5:0]）

| opx | 助记符 | 格式 | 来源 |
|-------------|--------|------|------|
| 001-000 | `and.o` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 001-001 | `or.o` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 001-010 | `xor.o` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 001-011 | `xnor.o` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 010-000 | `ext.uo` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 010-001 | `ext.so` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 010-010 | `shr.uo` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 010-011 | `shr.so` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 010-100 | `shl.uo` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 011-000 | `ext.uo` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 011-001 | `ext.so` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 011-010 | `shr.uo` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 011-011 | `shr.so` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 011-100 | `shl.uo` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 100-000 | `add.so-rb` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 101-000 | `sub.so-rb` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 101-001 | `cmp.uo-rb` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 101-010 | `cmp.uo` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 101-011 | `cmp.so` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 101-100 | `rd2rd` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 101-101 | `rd2ra` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 101-110 | `ra2rd` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 110-100 | `rb2rb` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 110-101 | `rd2rb` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 110-110 | `rb2rd` | orri | [SimRISC-00 §MISC-octa指令编码] |
| 111-000 | `div.uo` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 111-001 | `div.so` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 111-010 | `rem.uo` | orrr | [SimRISC-00 §MISC-octa指令编码] |
| 111-011 | `rem.so` | orrr | [SimRISC-00 §MISC-octa指令编码] |

### A.3 MISC-tetra 子表（op = 0x41）

| opx | 助记符 | 格式 | 来源 |
|-------------|--------|------|------|
| 010-010 | `shr.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 010-011 | `shr.st` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 010-100 | `shl.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 011-010 | `shr.ut` | orri | [SimRISC-00 §MISC-tetra指令编码] |
| 011-011 | `shr.st` | orri | [SimRISC-00 §MISC-tetra指令编码] |
| 011-100 | `shl.ut` | orri | [SimRISC-00 §MISC-tetra指令编码] |
| 100-000 | `add.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 100-001 | `add.st` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 101-000 | `sub.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 101-001 | `sub.st` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 101-010 | `cmp.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 101-011 | `cmp.st` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 110-000 | `mul.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 110-001 | `mul.st` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 111-000 | `div.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 111-001 | `div.st` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 111-010 | `rem.ut` | orrr | [SimRISC-00 §MISC-tetra指令编码] |
| 111-011 | `rem.st` | orrr | [SimRISC-00 §MISC-tetra指令编码] |

> **SPEC-069t**：已删除 opx 0x08–0x0B（`and.t`/`or.t`/`xor.t`/`xnor.t`）与 0x10–0x11/0x18–0x19（`ext.ut`/`ext.st`），共 8 条。这些 opx 现为 reserved（UNDI）。

### A.4 MISC-wyde 子表（op = 0x42）

| opx | 助记符 | 格式 | 来源 |
|-------------|--------|------|------|
| 010-010 | `shr.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 010-011 | `shr.sw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 010-100 | `shl.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 011-010 | `shr.uw` | orri | [SimRISC-00 §MISC-wyde指令编码] |
| 011-011 | `shr.sw` | orri | [SimRISC-00 §MISC-wyde指令编码] |
| 011-100 | `shl.uw` | orri | [SimRISC-00 §MISC-wyde指令编码] |
| 100-000 | `add.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 100-001 | `add.sw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 101-000 | `sub.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 101-001 | `sub.sw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 101-010 | `cmp.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 101-011 | `cmp.sw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 110-000 | `mul.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 110-001 | `mul.sw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 111-000 | `div.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 111-001 | `div.sw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 111-010 | `rem.uw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |
| 111-011 | `rem.sw` | orrr | [SimRISC-00 §MISC-wyde指令编码] |

> **SPEC-069t**：已删除 opx 0x08–0x0B（`and.w`/`or.w`/`xor.w`/`xnor.w`）与 0x10–0x11/0x18–0x19（`ext.uw`/`ext.sw`），共 8 条。这些 opx 现为 reserved（UNDI）。

### A.5 MISC-byte 子表（op = 0x43）

| opx | 助记符 | 格式 | 来源 |
|-------------|--------|------|------|
| 010-010 | `shr.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 010-011 | `shr.sb` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 010-100 | `shl.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 011-010 | `shr.ub` | orri | [SimRISC-00 §MISC-byte指令编码] |
| 011-011 | `shr.sb` | orri | [SimRISC-00 §MISC-byte指令编码] |
| 011-100 | `shl.ub` | orri | [SimRISC-00 §MISC-byte指令编码] |
| 100-000 | `add.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 100-001 | `add.sb` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 101-000 | `sub.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 101-001 | `sub.sb` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 101-010 | `cmp.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 101-011 | `cmp.sb` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 110-000 | `mul.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 110-001 | `mul.sb` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 111-000 | `div.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 111-001 | `div.sb` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 111-010 | `rem.ub` | orrr | [SimRISC-00 §MISC-byte指令编码] |
| 111-011 | `rem.sb` | orrr | [SimRISC-00 §MISC-byte指令编码] |

> **SPEC-069t**：已删除 opx 0x08–0x0B（`and.b`/`or.b`/`xor.b`/`xnor.b`）与 0x10–0x11/0x18–0x19（`ext.ub`/`ext.sb`），共 8 条。这些 opx 现为 reserved（UNDI）。

### A.6 MISC-AMO 子表（op = 0x77，M1 条目）

| opx | 助记符 | 格式 | 来源 |
|-------------|--------|------|------|
| 000-000 | `illi` | oiii | [SimRISC-00 §MISC-AMO 指令编码] |
| 000-010 | `swym` | oiii | [SimRISC-00 §MISC-AMO 指令编码] |

> `fence`（000-001）与 LR-SC 条目（010-xxx / 011-xxx）Excluded from M1，见 A.7。[SimRISC-00 §MISC-AMO 指令编码]

### A.7 Excluded from M1 编码清单

| op (hex) / 位置 | insn | 助记符 | 类别 | 来源 |
|-----------------|------|--------|------|------|
| 0x16 | ld.t-rf | `ld.t` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x17 | st.t-rf | `st.t` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x26 | ld.o-rf | `ld.o` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x27 | st.o-rf | `st.o` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x2E | ldm.t-rf | `ldm.t` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x2F | stm.t-rf | `stm.t` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x3E | ldm.o-rf | `ldm.o` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x3F | stm.o-rf | `stm.o` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
| 0x44 | MISC-RF | （浮点子表） | 浮点 | [SimRISC-00 §MISC-RF指令编码] |
| 0x4F | set.w-rf | `set.w` | RF 立即数 | [SimRISC-00 §SimRISC QFC] |

| 0x5E | cs.eq-rf | `cs.eq` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
| 0x5F | cs.ne-rf | `cs.ne` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
| 0x61 | cs.n-rf | `cs.n` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
| 0x63 | cs.z-rf | `cs.z` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
| 0x65 | cs.p-rf | `cs.p` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
| 0x7A | cfx2rd | `cfx2rd` | 特权 cfx | [SimRISC-00 §SimRISC QFC] |
| 0x7B | cfx2rc | `cfx2rc` | 特权 cfx | [SimRISC-00 §SimRISC QFC] |
| 0x7C | cfxld | `cfxld` | 特权 cfx | [SimRISC-00 §SimRISC QFC] |
| 0x7D | cfxst | `cfxst` | 特权 cfx | [SimRISC-00 §SimRISC QFC] |
| 0x7E | escape | `escape` | 特权 cfx | [SimRISC-00 §SimRISC QFC] |
| 0x7F | trap | `trap` | 特权 cfx | [SimRISC-00 §SimRISC QFC] |
| MISC-octa 111-101 | rd2rf | `rd2rf` | RF 块赋值 | [SimRISC-00 §MISC-octa指令编码] |
| MISC-octa 111-110 | rf2rd | `rf2rd` | RF 块赋值 | [SimRISC-00 §MISC-octa指令编码] |
| MISC-AMO 000-001 | fence | `fence` | 待定指令 | [SimRISC-00 §MISC-AMO 指令编码] |
| MISC-AMO 010-xxx | lr_nn/lr_nr/lr_an/lr_ar | `lr_*.o` | LR-SC 原子 | [SimRISC-00 §MISC-AMO 指令编码] |
| MISC-AMO 011-xxx | sc_nn/sc_nr/sc_an/sc_ar | `sc_*.o` | LR-SC 原子 | [SimRISC-00 §MISC-AMO 指令编码] |

---

## 附录 B：条件标志参考

### B.1 条件判断方法

SimRISC 不提供专门的标识位寄存器，而是根据数据寄存器所存放的数值来判断是否满足条件，共有 8 种条件判断。[SimRISC-00 §标识位说明]

| 助记符 | 条件 | 操作数个数 | 判断方法 |
|--------|------|-----------|---------|
| `N` | 负数 | 一个操作数 | 第 63 位为 1 |
| `NN` | 非负数 | 一个操作数 | 第 63 位为 0 |
| `Z` | 零 | 一个操作数 | [63..0] 全为 0 |
| `NZ` | 非零 | 一个操作数 | [63..0] 不全为 0 |
| `P` | 正数 | 一个操作数 | 第 63 位为 0，且 [62..0] 不全为 0 |
| `NP` | 非正数 | 一个操作数 | 第 63 位为 1，或 [63..0] 全为 0 |
| `EQ` | 相等 | 两个操作数 | 所有位数相等 |
| `NE` | 不相等 | 两个操作数 | 至少有一位不相等 |
[SimRISC-00 §标识位说明]

### B.2 条件赋值与条件跳转对应关系

| 条件 | 条件赋值指令（RD） | 条件跳转指令（rd） | 条件跳转指令（rb） |
|------|-------------------|-------------------|-------------------|
| 负数 (N) | `cs.n` | `br.n` | — |
| 非负数 (NN) | — | `br.nn` | — |
| 零 (Z) | `cs.z` | `br.z` | `br.z` |
| 非零 (NZ) | — | `br.nz` | `br.nz` |
| 正数 (P) | `cs.p` | `br.p` | — |
| 非正数 (NP) | — | `br.np` | — |
| 相等 (EQ) | `cs.eq` | `br.eq` | — |
| 不相等 (NE) | `cs.ne` | `br.ne` | — |
[SimRISC-00 §标识位说明][SimRISC-02 §条件赋值：Conditional Assignment][SimRISC-06 §条件跳转指令]

### B.3 条件跳转特例

- `rdha` 为 `rd0` 时，`br.z` 条件必为真，`br.nz` 条件必为假。[SimRISC-06 §条件跳转指令]
- `br.z-rb`/`br.nz-rb` 依据 `rbha` 是否为 0 判断（rb 无对应的条件赋值指令）。[SimRISC-06 §条件跳转指令]

> 浮点比较结果的条件解读属浮点内容，Excluded from M1。[SimRISC-07 §浮点比较指令]
