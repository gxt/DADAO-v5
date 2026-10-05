# SimRISC指令系统

> **版本：0.5.4**

SimRISC名称有三重含义：

- 一是Simple RISC，顾名思义，其基础设计理念是"Simple is beautiful" + RISC
- 二是Simulated RISC，其设计初衷是基于教学目的，故完全基于模拟环境进行设计开发
- 三是Similar RISC，基于RISC而不局限于RISC，在很多设计想法上希望在RISC基础上进行探索和突破

## 数据表示

64位计算机以0和1的模式，即二进制数字，来进行工作，而且通常一次处理64位，即机器字长64位。

8个二进制位，或2个十六进制数字的一个序列，被称为一个字节。

对于只考虑数据长度的术语定义，SimRISC采用了如下四种数据表示：

***基础数据类型***

| 术语   | 缩写 | 位数 | 字节数 |
| ---   | :---: | ---:      | ---:      |
| byte  | b     | 8-bit     | 1-byte    |
| wyde  | w     | 16-bit    | 2-byte    |
| tetra | t     | 32-bit    | 4-byte    |
| octa  | o     | 64-bit    | 8-byte    |

> 这四个术语的定义参考了Knuth在MMIX中的定义。

### 原始数据类型

现代处理器设计，通常是用指令opcode来区分数据类型。
SimRISC中目前接收如下数据类型：

- 四种定点类型，长度分别为：8bit、16bit、32bit、64bit
- 两种浮点类型，长度分别为：32bit、64bit
  - 浮点格式的定义符合IEEE754标准

## 寄存器

以一个程序员的观点看，用户可见寄存器有 4 组，每组 64 个寄存器（需 6 位编码），每个寄存器 64 位（即机器字长）：

- 数据寄存器 64 个：`rd0 - rd63`
- 基址寄存器 64 个：`rb0 - rb63`
- 浮点寄存器 64 个：`rf0 - rf63`
- 返回地址栈 64 个：`ra0 - ra63`

每组寄存器的 0 号寄存器都具有特殊功能，其操作可能受限。

### 数据寄存器

数据寄存器又可称为通用寄存器，主要用于各种运算，如下：

- 共64个数据寄存器，每个寄存器64位
- `rd0`固定为0，只读。作为目的寄存器时行为取决于指令格式：rrrr 双目的（add.uo/add.so/sub.uo/sub.so/mul.uo/mul.so）允许其中一个为 rd0（丢弃对应半结果），但不能**同时**为 rd0，也不能为同一非 rd0 寄存器；`ret rd0, 0` 允许（无需设置返回值）；其余指令目的为 rd0 时触发 ILLI 异常。

### 基址寄存器

基址寄存器又可称为地址寄存器，但是在SimRISC中只能用于基址，即绝对地址，简要说明如下：

- 共64个基址寄存器，每个寄存器64位，实际实现需保证48位地址空间
- `rb0` 读出为**当前指令的地址**（非下一条），只读。任何指令以 rb0 为显式目的时触发 ILLI 异常。`rb0[63:48]` 初值为 0，由控制流指令的硬件写入（见 §控制流指令）。硬件复位后 `rb0` 初值为 `cfx_power_hypv_excp_vector`（见 SEE §2.1）。

基址寄存器（RB）为 64 位，低 48 位（bits[47:0]）为有效地址。

各类操作对高 16 位（bits[63:48]）的处理规则如下：

| 操作类别 | 指令 | 高 16 位行为 |
|---------|------|-------------|
| 存取类指令 | `ld.o`/`ldm.o`/`st.o`/`stm.o`（内存→RB） | **全 64 位覆盖，bits[63:48] 正常读写** |
| 赋值类指令-寄存器 | `rd2rb`/`rb2rb` | **全 64 位覆盖，bits[63:48] 正常读写** |
| 赋值类指令-立即数 | `set.zw-rb`/`or.w-rb`/`andn.w-rb` | **全 64 位覆盖，bits[63:48] 正常读写，允许 wyde-pos=3** |
| 算术运算类指令-加减 | `add.o`/`sub.o`/`add.si-rb` | 二进制补码 64 位全宽加减法，结果完整保留 64 位；仅当以该值**访存**时硬件取 `rb[47:0]`（低 48 位）为有效地址，**bits[63:48]** 为运算结果，可用于地址溢出检测 |
| 算术运算类指令-比较 | `cmp.uo-rb` | **整 64 位**无符号比较（`bits[63:48]` **参与**），结果 -1/0/1 区分小于/等于/大于 |
| 控制流指令-跳转 | `br*`/`jump` | `rb0` 以 **64 位**参与地址计算；结果写回 `rb0`，取 **`rb0[47:0]`（低 48 位）**为下一条指令地址；**iiii 基址 = `rb0`；rrii 基址 = `rbHA`（仅读）**；`rb0[63:48]` 保留结果高 16 位并参与后续运算（见 §控制流指令） |
| 控制流指令-函数调用 | `call` | `rb0` 以 **64 位**参与地址计算；结果写回 `rb0`，取 **`rb0[47:0]`（低 48 位）**为下一条指令地址；**iiii 基址 = `rb0`；rrii 基址 = `rbHA`（仅读）**；`rb0[63:48]` 保留结果高 16 位并参与后续运算（见 §控制流指令；`ret` 见 §返回地址栈） |

RB 的高 16 位初值为全 0。`rb0[63:48]` 由控制流指令硬件写入（见 §控制流指令），参与后续运算（累积/传播），供溢出检测。

**存储模型**：SimRISC采用64位地址空间，有效虚拟地址为48位。RB 为整 64 位寄存器，存取/复制/立即数赋值等均为全 64 位操作（见上表）；**作访存基址时取 `rb[47:0]`（低 48 位）**为有效地址。控制流地址计算按 64 位全宽进行（见 §控制流指令）。

### 浮点寄存器

浮点寄存器只能用于浮点类指令，简要说明如下：

- 浮点寄存器支持单精和双精两种格式：
  - ft：tetra-size（32位单精）
  - fo：octa-size（64位双精）
- rf寄存器字长64位，当存放单精32位数据时，只使用低32位，高32位不做特殊规定
- `rf0`为浮点状态寄存器（FCSR）。它同时是单精、双精格式的qNaN，**可作浮点运算的源操作数**；又因其同时是状态寄存器，浮点运算执行后会更新其状态位（异常位），故 **`rf0`不可作浮点运算的目的操作数**

#### 浮点状态寄存器

`rf0`为浮点状态寄存器，具体定义如下：

- [63..51]: 0111 1111 1111 1（只读，写无效；其值为fo格式下的Quiet NaN，即符号位为0，E为全1，尾数最高位为1）
- [50..34]: SBZ（Should Be Zero）
- [33..32]：舍入模式（Rounding Mode）
- [31..22]: 0111 1111 11（只读，写无效；其值为ft格式下的Quiet NaN，即符号位为0，E为全1，尾数最高位为1）
- [21..5]：SBZ（Should Be Zero）
- [4..0]：异常状态（Accured exception）

舍入模式定义如下：（舍入模式的设置单独放在wp2中，程序可以直接用set.w指令进行设置）

| Rounding Mode | Mnemonic  | Meaning                           |
| :---:         | :---:     | ---                               |
| 00            | `RNE`     | Round to Nearest, ties to Even    |
| 01            | `RTZ`     | Round towards Zero                |
| 10            | `RDN`     | Round Down (towards -inf)         |
| 11            | `RUP`     | Round Up (towards +inf)           |

异常状态定义如下：

| Bit   | Mnemonic  | Meaning           |
| :---: | :---:     | ---               |
| 0     | `NV`      | Invalid Operation |
| 1     | `DZ`      | Divide by Zero    |
| 2     | `OF`      | Overflow          |
| 3     | `UF`      | Underflow         |
| 4     | `NX`      | Inexact           |

浮点指令执行后，异常状态位（NV/DZ/OF/UF/NX）由硬件按 IEEE 754 标准设置到 rf0[4:0]。软件可通过读取 rf0 检查异常状态，并根据需要进行后续处理。浮点指令不会触发异常，始终按 IEEE 754 标准返回结果（如 NaN、Inf 等）。

写 `rf0` 时**只更新** `[33..32]`（舍入模式）与 `[4..0]`（异常状态），其余位（只读 Quiet NaN 位、SBZ）**写无效、保持原值**。

### 返回地址栈

返回地址栈（Return Address Stack）专门用于支持函数的调用和返回，采用后入先出的方式，将函数的返回地址统一存放在单独可寻址的栈上，简要说明如下：

| 寄存器 | `[63:48]` | `[47:0]` |
|--------|-----------|----------|
| `ra0` | `[63:54]` = **SBZ**（写无效）；`[53:48]` = **`RACNT`**（RegRAS 有效条目数，0–63，初始 0） | **`MRPTR`**：MemRAS 下一个待弹出条目（栈顶）的字节地址（8 字节对齐）；**0 = 未启用 MemRAS** |
| `ra1`–`ra62` | **递归计数** | **返回地址** |
| `ra63` | **递归计数** | **返回地址**（`ra63` 恒为 RegRAS 栈顶） |

- `ra1`–`ra63`：构成 RegRAS（63 槽），`ra63` 为 RegRAS 栈顶。
- **有效性判据 = `RACNT`**（不看条目自身的值）：有效条目 = 自 `ra63` 起向下连续 `RACNT` 个（第 k 新 = `ra[64−k]`，栈底（最旧）= `ra[64−RACNT]`）；有效区之外的 `ra_i` 内容未定义（不参与栈语义；复位后全 0）。
- `ra0`：
  - `MRPTR == 0` 时只有一个 RAS（RegRAS），最多在 RegRAS 中存放 63 个返回地址，（不考虑递归情况下）调用深度超过 63 时触发 **RASOF** 异常。
  - `MRPTR != 0` 时有两个 RAS（RegRAS 和 MemRAS），MemRAS 是事先分配好的一段存储空间，`MRPTR` 为 MemRAS 栈顶地址。
  - MemRAS 的访存遵循地址转换和存储访问规则：若访存触发页缺失等异常，硬件保证精确异常（压栈/弹栈未执行，PC 指向 call/ret 指令），异常处理后可重新执行。
- **RASOF** 仅由「需溢出且 `MRPTR == 0`」触发；**MemRAS 越界（容量耗尽）不由硬件检测（交 OS）**。
- **精确异常**：压栈/弹栈**先完成全部 `RASOF`/`RASUF` 判定**（含 D4b 的 MemRAS 条目读取与内容判定），判定通过后才进行 RA 寄存器或 MemRAS 访存的任何修改；异常时 RA 寄存器与内存均保持原状。

一个用户进程开始执行时，RegRAS 全部初始化为全零（`RACNT = 0`，条目内容全 0），MemRAS 应做好分配，并设置 `ra0`。fork 子进程应复制父进程的全部 ra 寄存器。

在进程运行过程中，返回地址栈通常无需程序干预，可以利用 `call` 和 `ret` 指令的动态一一对应的关系实现正确的压栈、弹栈操作。

进程切换时，操作系统须保存和恢复全部 ra0–ra63 寄存器。

异常进入和退出不改变 ra0–ra63 的内容，异常 handler 中可正常使用 call/ret 指令。信号处理时的 RA 保存恢复由操作系统负责，规则与进程切换一致。

#### 压栈流程（call 指令）

压栈按以下情形处理：

- **C1** `RACNT == 0` → 压入新条目（递归计数 = 1、返回地址），`RACNT = 1`；
- **C2** `RACNT > 0` 且 返回地址 == `ra63[47:0]`（栈顶返回地址）且 `ra63[63:48] < 0xFFFF` → **递归折叠优先**：`ra63[63:48] += 1`，`RACNT` 不变；
- **C3** 其余：
  - **C3a** `RACNT < 63` → 压入新条目（递归计数 = 1），`RACNT += 1`；
  - **C3b** `RACNT == 63` → ① `MRPTR == 0` → **RASOF**；② `MRPTR −= 8` 并把**栈底（最旧）条目**（`ra[64−RACNT]`）写入 `MRPTR` 处；③ 压入新条目 ⇒ 出栈底一条、入栈顶一条，`RACNT` 保持 63。

#### 弹栈流程（ret 指令）

弹栈按以下情形处理：

- **D1** `RACNT > 0` 且 `ra63[63:48] == 0` → **RASUF**；
- **D2** `RACNT > 0` 且 `ra63[63:48] > 1` → 计数 −1，`RACNT` 不变；
- **D3** `RACNT > 0` 且 `ra63[63:48] == 1` → 弹出栈顶，`RACNT − 1`；
- **D4** `RACNT == 0` →
  - **D4a** `MRPTR == 0` → **RASUF**；
  - **D4b** 读 `MRPTR` 处条目并作判定（`MRPTR` 暂不修改）：递归计数 = 0 → **RASUF**、= 1 → 返回地址 = 条目低 48 且 `MRPTR += 8`、> 1 → 该条目压入成为栈顶（计数 −1）且 `MRPTR += 8`、`RACNT = 1`。

#### 实现注（非架构语义）

实现可用**环形缓冲 + 隐藏基准索引**避免压栈/弹栈时的数据搬移；`ra_i` 为软件可见（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd`），访问须按基准索引换算以与架构视图一致。

#### RA↔RD 块赋值

- `ra2rd`/`rd2ra` 在 RA 与 RD 之间进行全 64 位块赋值（含 RA 高 16 位：`ra0[53:48]` 为 `RACNT`，`ra1`–`ra63[63:48]` 为递归计数）。操作语义与异常条件见 SimRISC-02。

#### call / ret 在本节的说明

- **`call`**：计算返回地址并按上述 C1–C3b 流程压入 RAS（见 §压栈流程）。
- **`ret`**：从 RAS 弹出返回地址（来源**可能不是 `ra63`**，取决于 RAS 状态）并跳转；可能触发 **RASUF** 异常（见 §弹栈流程）。

## 指令设计

SimRISC中的每条指令都是四个字节，即32位。所有指令必须4字节对齐。取指时若 PC[1:0] ≠ 00，触发 IALIGN 异常。

> **通用约束交叉引用**：MALIGN 对齐规则见各存取指令章节（SimRISC-01），除法溢出规则见各数据运算章节（SimRISC-04/08/09/10），`immu6 = 0` 触发 ILLI 见各多寄存器操作章节。

指令字采用**大端序**存储：bits[31:24] 在最低地址，bits[7:0] 在最高地址。数据端序同样为大端序（见 ABI §数据表示）。

### 指令域说明

通常，一个32位的指令会被分解为5个部分：8/6/6/6/6。
头8位是op，主要指明指令功能，隐含指令分类。
后面四个6位记为ha/hb/hc/hd，主要指明具体的操作数，包括格式和内容。

op 是操作码，简称 opc（opcode 的简写），即头 8 位。
某些情况下，ha（6 位）也参与操作码，称为 opx（opcode-auxiliary 的简写）；opx 只可能是 ha。

ha/hb/hc/hd通过不同的寻址方式组合成操作数，h含义为hexagram，既是六，也是六十四。
操作数的寻址方式分别用以下几个字母表示：

- `o`：六位的 opx
- `c`：六位的cfxha
- `r`：寄存器
- `i`：立即数（立即数域需要区分有符号数和无符号数）
- `w`：头两位为wyde-position，后四位为立即数
- `z`：未使用，应为零，（SBZ：Should Be Zero）

SimRISC没有在编码上进行过多的拆分，操作数类型简单而规整，用4个字母可以表示某条指令的操作数类型，其中也隐含了操作数位置和操作数个数：

- `rrrr`：四个操作数，都是寄存器
- `rrri`：四个操作数，其中三个寄存器，一个6位立即数在 `hd[5:0]`
- `rrii`：三个操作数，其中两个寄存器，一个12位立即数在 `hc[5:0]`+`hd[5:0]`（hc=高位6位, hd=低位6位）
- `riii`：两个操作数，其中一个寄存器，一个18位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]`（hb=高位6位, hc=中位6位, hd=低位6位）
- `iiii`：一个操作数，24位立即数在 `ha[5:0]`+`hb[5:0]`+`hc[5:0]`+`hd[5:0]`

含 `wyde-position` 的一种特殊格式如下：

- `rwii`：一个寄存器，一个 wyde-position，和一个拆分为两段的 16 位无符号立即数
  - wyde-position 在 `hb[5:4]`，编码：`00=wp0, 01=wp1, 10=wp2, 11=wp3`
  - immu16 高 4 位在 `hb[3:0]`，中 6 位在 `hc[5:0]`，低 6 位在 `hd[5:0]`（hb→hc→hd 高位到低位）

以下三种格式含 `o`（opx，6 位辅助操作码），opx 在 `ha[5:0]`：

- `orrr`：opx + 三个寄存器
- `orri`：opx + 两个寄存器 + 6 位立即数在 `hd[5:0]`
- `oiii`：opx + 18 位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]`（hb=高位6位, hc=中位6位, hd=低位6位）

SimRISC 提供四种固定数据位宽，通过指令名后缀 `.b`/`.w`/`.t`/`.o` 区分，分别对应 byte（8 位）、wyde（16 位）、tetra（32 位）、octa（64 位）。这四种位宽的指令分布在以下四个 opx 子表中：

- `MISC-byte`：byte 位宽指令
- `MISC-wyde`：wyde 位宽指令
- `MISC-tetra`：tetra 位宽指令
- `MISC-octa`：octa 位宽指令

各子表内使用 `orrr`/`orri`/`oiii` 操作数格式。指令名后缀 `.b`/`.w`/`.t`/`.o` 与已有的存取指令后缀（`ldb`/`ldw`/`ld.t`/`ld.o`）一致。对有符号/无符号区分的指令（mul/div/rem/cmp/ext/shl/shr），后缀扩展为 `.ub`/`.sb`（byte）、`.uw`/`.sw`（wyde）、`.ut`/`.st`（tetra）、`.uo`/`.so`（octa），其中 `s` 表示有符号、`u` 表示无符号。

以下三种格式含 `c`（cfxha，6 位核芯功能扩展编码），cfxha 始终在 `ha[5:0]`：

- `crrr`：cfxha + 三个 6 位寄存器编号，cg 在 `hb`，rc 在 `hc`，rd 在 `hd`（cfx2rd/cfx2rc）
- `crii`：cfxha + 6 位 rb 寄存器在 `hb` + 12 位立即数在 `hc[5:0]`+`hd[5:0]`（hc=高位, hd=低位，cfxld/cfxst）
- `ciii`：cfxha + 18 位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]`（hb=高位, hc=中位, hd=低位，trap/escape）

SimRISC 通常将目的操作数放在最前面，然后是寄存器源操作数，从而可以把立即数放在最后，并且立即数通常为最后一个源操作数，可以直观的从二进制上判断出立即数。
其好处是便于调试，根据二进制可以直观地猜出部分指令内容。

### 标识位说明

SimRISC不提供专门的标识位寄存器，而是根据数据寄存器所存放的数值来判断是否满足条件，共有8种条件判断：

| 助记符 | 条件 | 操作数个数 | 判断方法 |
| ---: | ---    | ---       | --- |
| `N`  | 负数   | 一个操作数 | 第63位为1                    |
| `NN` | 非负数 | 一个操作数 | 第63位为0                    |
| `Z`  | 零    | 一个操作数 | [63..0]全为0                  |
| `NZ` | 非零  | 一个操作数 | [63..0]不全为0                |
| `P`  | 正数   | 一个操作数 | 第63位为0，且[62..0]不全为0      |
| `NP` | 非正数 | 一个操作数 | 第63位为1，或[63..0]全为0        |
| `EQ` | 相等   | 两个操作数 | 所有位数相等                     |
| `NE` | 不相等 | 两个操作数 | 至少有一位不相等                 |

## SimRISC QFC

SimRISC 0.5.4版本的指令opcode布局如下。空白单元格表示 reserved（保留未分配），执行保留编码触发 UNDI 异常。

|               | xxxx-x000            | xxxx-x001            | xxxx-x010            | xxxx-x011            | xxxx-x100            | xxxx-x101            | xxxx-x110            | xxxx-x111        |
| ---           | ---                  | ---                  | ---                  | ---                  | ---                  | ---                  | ---                  | ---              |
| 0000-0xxx     |                      |                      |                      |                      |                      |                      |                      |                  |
| 0000-1xxx     |                      |                      |                      |                      |                      |                      |                      |                  |
| 0001-0xxx     | ld.ub_rrii_rd        | ld.uw_rrii_rd        | ld.ut_rrii_rd        | ld.sb_rrii_rd        | ld.sw_rrii_rd        | ld.st_rrii_rd        | ld.t_rrii_rf         | st.t_rrii_rf    |
| 0001-1xxx     | st.b_rrii_rd         | st.w_rrii_rd         | st.t_rrii_rd         |                      |                      |                      |                      |                  |
| 0010-0xxx     | ld.o_rrii_rd         | st.o_rrii_rd         | ld.o_rrii_rb         | st.o_rrii_rb         | ld.o_rrii_ra         | st.o_rrii_ra         | ld.o_rrii_rf         | st.o_rrii_rf    |
| 0010-1xxx     | ldm.ub_rrri_rd       | ldm.uw_rrri_rd       | ldm.ut_rrri_rd       | ldm.sb_rrri_rd       | ldm.sw_rrri_rd       | ldm.st_rrri_rd       | ldm.t_rrri_rf        | stm.t_rrri_rf   |
| 0011-0xxx     | stm.b_rrri_rd        | stm.w_rrri_rd        | stm.t_rrri_rd        |                      |                      |                      |                      |                  |
| 0011-1xxx     | ldm.o_rrri_rd        | stm.o_rrri_rd        | ldm.o_rrri_rb        | stm.o_rrri_rb        | ldm.o_rrri_ra        | stm.o_rrri_ra        | ldm.o_rrri_rf        | stm.o_rrri_rf   |
| 0100-0xxx     | MISC-octa            | MISC-tetra           | MISC-wyde            | MISC-byte            | MISC-RF              |                      |                      |                  |
| 0100-1xxx     | or.w_rwii_rd         | andn.w_rwii_rd       | or.w_rwii_rb         | andn.w_rwii_rb       | set.zw_rwii_rd       | set.ow_rwii_rd       | set.zw_rwii_rb       | set.w_rwii_rf   |
| 0101-0xxx     | add.uo_rrrr_rd       | add.so_rrrr_rd       | sub.uo_rrrr_rd       | sub.so_rrrr_rd       | mul.uo_rrrr_rd       | mul.so_rrrr_rd       |                      |                  |
| 0101-1xxx     |                      | add.si_riii_rd       |                      | add.si_riii_rb       | cmp.ui_rrii_rd       | cmp.si_rrii_rd       | cs.eq_rrrr_rf        | cs.ne_rrrr_rf   |
| 0110-0xxx     | cs.n_rrrr_rd         | cs.n_rrrr_rf         | cs.z_rrrr_rd         | cs.z_rrrr_rf         | cs.p_rrrr_rd         | cs.p_rrrr_rf         | cs.eq_rrrr_rd        | cs.ne_rrrr_rd   |
| 0110-1xxx     | br.n_riii_rd         | br.nn_riii_rd        | br.z_riii_rd         | br.nz_riii_rd        | br.p_riii_rd         | br.np_riii_rd        | br.eq_rrii_rd        | br.ne_rrii_rd   |
| 0111-0xxx     | jump_iiii_rb         | jump_rrii_rb         | br.z_riii_rb         | br.nz_riii_rb        | call_iiii_ra         | call_rrii_ra         | ret_riii_ra          | MISC-AMO        |
| 0111-1xxx     |                      |                      | cfx2rd_crrr_cfx      | cfx2rc_crrr_cfx      | cfxld_crii_cfx       | cfxst_crii_cfx       | escape_ciii_cfx      | trap_ciii_cfx   |

> **`scope` 分区**（用户裁定 2026-10-03；2026-10-05 按实现状态更新）：`scope: fp`（主表 `MISC-RF` 子表 op=0x44 的 RF 运算/转换/比较/分类，及散见各表的 RF 存取形态，共 60 条）**语义已归一化于 `contract-fp.md`、执行层 60/60 已实现**（`QEMU-034t`~`038t`），不触发 decode ILLI。
> `scope: excluded`（特权 cfx：cfx2rd/cfx2rc/cfxld/cfxst/escape/trap）**未实现，decode ILLI**。

### MISC-AMO 指令编码

空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000      | xxx-001      | xxx-010      | xxx-011      | xxx-100      | xxx-101      | xxx-110      | xxx-111      |
| ---       | ---          | ---          | ---          | ---          | ---          | ---          | ---          | ---          |
| 000-xxx   | illi_oiii_imm | fence_oiii_imm | swym_oiii_imm |              |              |              |              |              |
| 001-xxx   |              |              |              |              |              |              |              |              |
| 010-xxx   | lr_nn.o_orrr_rd | lr_nr.o_orrr_rd | lr_an.o_orrr_rd | lr_ar.o_orrr_rd |              |              |              |              |
| 011-xxx   | sc_nn.o_orrr_rd | sc_nr.o_orrr_rd | sc_an.o_orrr_rd | sc_ar.o_orrr_rd |              |              |              |              |
| 100-xxx   |              |              |              |              |              |              |              |              |
| 101-xxx   |              |              |              |              |              |              |              |              |
| 110-xxx   |              |              |              |              |              |              |              |              |
| 111-xxx   |              |              |              |              |              |              |              |              |

### MISC-octa指令编码

octa 位宽（64 位）指令。指令名后缀 `.o` 表示 octa 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000         | xxx-001         | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---             | ---             | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |                 |                 |               |               |               |               |               |               |
| 001-xxx   | and.o_orrr_rd      | or.o_orrr_rd       | xor.o_orrr_rd    | xnor.o_orrr_rd   |               |               |               |               |
| 010-xxx   | ext.uo_orrr_rd     | ext.so_orrr_rd     | shr.uo_orrr_rd   | shr.so_orrr_rd   | shl.uo_orrr_rd   |               |               |               |
| 011-xxx   | ext.uo_orri_rd     | ext.so_orri_rd     | shr.uo_orri_rd   | shr.so_orri_rd   | shl.uo_orri_rd   |               |               |               |
| 100-xxx   |                 |                 |               |               |               |               |               |               |
| 101-xxx   |                 |                 | cmp.uo_orrr_rd   | cmp.so_orrr_rd   | rd2rd_orri_rd    | rd2ra_orri_ra    | ra2rd_orri_ra    |               |
| 110-xxx   | add.o_orrr_bbd   | sub.o_orrr_bbd   | cmp.uo_orrr_dbb | sub.o_orrr_dbb | rb2rb_orri_rb    | rd2rb_orri_rb    | rb2rd_orri_rb    |               |
| 111-xxx   | div.uo_orrr_rd     | div.so_orrr_rd     | rem.uo_orrr_rd   | rem.so_orrr_rd   |               | rd2rf_orri_rf    | rf2rd_orri_rf    |               |

### MISC-tetra指令编码

tetra 位宽（32 位）指令。指令名后缀 `.t` 表示 tetra 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               |               |               |               |               |
| 001-xxx   |               |               |               |               |               |               |               |               |
| 010-xxx   |               |               | shr.ut_orrr_rd   | shr.st_orrr_rd   | shl.ut_orrr_rd   |               |               |               |
| 011-xxx   |               |               | shr.ut_orri_rd   | shr.st_orri_rd   | shl.ut_orri_rd   |               |               |               |
| 100-xxx   | add.ut_orrr_rd   | add.st_orrr_rd   |               |               |               |               |               |               |
| 101-xxx   | sub.ut_orrr_rd   | sub.st_orrr_rd   | cmp.ut_orrr_rd   | cmp.st_orrr_rd   |               |               |               |               |
| 110-xxx   | mul.ut_orrr_rd   | mul.st_orrr_rd   |               |               |               |               |               |               |
| 111-xxx   | div.ut_orrr_rd   | div.st_orrr_rd   | rem.ut_orrr_rd   | rem.st_orrr_rd   |               |               |               |               |

> **SPEC-069t**：上表空单元格为已删除条目（共 8 条/子表：4 逻辑 + 2 ext×2 格式），其 opx 现为 reserved（UNDI）。

### MISC-wyde指令编码

wyde 位宽（16 位）指令。指令名后缀 `.w` 表示 wyde 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               |               |               |               |               |
| 001-xxx   |               |               |               |               |               |               |               |               |
| 010-xxx   |               |               | shr.uw_orrr_rd   | shr.sw_orrr_rd   | shl.uw_orrr_rd   |               |               |               |
| 011-xxx   |               |               | shr.uw_orri_rd   | shr.sw_orri_rd   | shl.uw_orri_rd   |               |               |               |
| 100-xxx   | add.uw_orrr_rd   | add.sw_orrr_rd   |               |               |               |               |               |               |
| 101-xxx   | sub.uw_orrr_rd   | sub.sw_orrr_rd   | cmp.uw_orrr_rd   | cmp.sw_orrr_rd   |               |               |               |               |
| 110-xxx   | mul.uw_orrr_rd   | mul.sw_orrr_rd   |               |               |               |               |               |               |
| 111-xxx   | div.uw_orrr_rd   | div.sw_orrr_rd   | rem.uw_orrr_rd   | rem.sw_orrr_rd   |               |               |               |               |

> **SPEC-069t**：上表空单元格为已删除条目（共 8 条/子表：4 逻辑 + 2 ext×2 格式），其 opx 现为 reserved（UNDI）。

### MISC-byte指令编码

byte 位宽（8 位）指令，覆盖移位、扩展、逻辑、算术、比较、乘除等操作。指令名后缀 `.b` 表示 byte 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               |               |               |               |               |
| 001-xxx   |               |               |               |               |               |               |               |               |
| 010-xxx   |               |               | shr.ub_orrr_rd   | shr.sb_orrr_rd   | shl.ub_orrr_rd   |               |               |               |
| 011-xxx   |               |               | shr.ub_orri_rd   | shr.sb_orri_rd   | shl.ub_orri_rd   |               |               |               |
| 100-xxx   | add.ub_orrr_rd   | add.sb_orrr_rd   |               |               |               |               |               |               |
| 101-xxx   | sub.ub_orrr_rd   | sub.sb_orrr_rd   | cmp.ub_orrr_rd   | cmp.sb_orrr_rd   |               |               |               |               |
| 110-xxx   | mul.ub_orrr_rd   | mul.sb_orrr_rd   |               |               |               |               |               |               |
| 111-xxx   | div.ub_orrr_rd   | div.sb_orrr_rd   | rem.ub_orrr_rd   | rem.sb_orrr_rd   |               |               |               |               |

> **SPEC-069t**：上表空单元格为已删除条目（共 8 条/子表：4 逻辑 + 2 ext×2 格式），其 opx 现为 reserved（UNDI）。

### MISC-RF指令编码

> 本子表 44 条均为 `scope: fp`——语义已归一化于 `contract-fp.md`，执行层已实现（`scope: fp` 共 60 条，`QEMU-034t`~`038t` 全部落地），不触发 decode ILLI。

空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000     | xxx-001     | xxx-010     | xxx-011     | xxx-100     | xxx-101     | xxx-110     | xxx-111     |
| ---       | ---         | ---         | ---         | ---         | ---         | ---         | ---         | ---         |
| 000-xxx   | ftcls_orri_rf  | ft2fo_orri_rf  | ft2ft_orri_rf  |             |             |             | ftroot_orri_rf |  |
| 001-xxx   | focls_orri_rf  | fo2ft_orri_rf  | fo2fo_orri_rf  |             |             |             | foroot_orri_rf |  |
| 010-xxx   | ftadd_orrr_rf  | ftsub_orrr_rf  | ftmul_orrr_rf  | ftdiv_orrr_rf  | ftrem_orrr_rf  | ftsclb_orrr_rf | ftsgnn_orrr_rf | ftsgnj_orrr_rf |
| 011-xxx   | foadd_orrr_rf  | fosub_orrr_rf  | fomul_orrr_rf  | fodiv_orrr_rf  | forem_orrr_rf  | fosclb_orrr_rf | fosgnn_orrr_rf | fosgnj_orrr_rf |
| 100-xxx   | ftqcmp_orrr_rf | ftscmp_orrr_rf |             |             |             |             |             |             |
| 101-xxx   | foqcmp_orrr_rf | foscmp_orrr_rf |             |             |             |             |             |             |
| 110-xxx   | ft2it_orri_rf  | ft2io_orri_rf  | ft2ut_orri_rf  | ft2uo_orri_rf  | it2ft_orri_rf  | io2ft_orri_rf  | ut2ft_orri_rf  | uo2ft_orri_rf  |
| 111-xxx   | fo2it_orri_rf  | fo2io_orri_rf  | fo2ut_orri_rf  | fo2uo_orri_rf  | it2fo_orri_rf  | io2fo_orri_rf  | ut2fo_orri_rf  | uo2fo_orri_rf  |

## 伪指令

汇编器提供以下伪指令，简化常用操作的编写。伪指令不是硬件指令，汇编器将其展开为一条或多条硬件指令。

| 伪指令 | 语法 | 展开形式 | 说明 | 详细定义 |
|--------|------|----------|------|----------|
| `nop` | `nop` | `swym 0` | 空操作，占位或对齐 | SimRISC-11 §nop 伪指令 |
| `return` | `return` | `ret rd0, 0` | 无返回值的函数返回 | SimRISC-06 §return 伪指令 |
| `not.o` | `not.o rdHB, rdHC` | `xnor.o rdHB, rdHC, rd0` | 64 位按位取反 | SimRISC-04 §not 伪指令 |
| `neg.b` | `neg.b rdHB, rdHC` | `sub.sb rdHB, rd0, rdHC` | 8 位取负，符号扩展 | SimRISC-10 §neg 伪指令 |
| `neg.w` | `neg.w rdHB, rdHC` | `sub.sw rdHB, rd0, rdHC` | 16 位取负，符号扩展 | SimRISC-09 §neg 伪指令 |
| `neg.t` | `neg.t rdHB, rdHC` | `sub.st rdHB, rd0, rdHC` | 32 位取负，符号扩展 | SimRISC-08 §neg 伪指令 |
| `neg.o` | `neg.o rdHB, rdHC` | `sub.so {rd0, rdHB}, rd0, rdHC` | 64 位取负 | SimRISC-04 §neg 伪指令 |
| `set.rd` | `set.rd rdxx, imm64` | `set.zw`/`set.ow` + `or.w`/`andn.w` | 加载 64 位立即数到 rd | SimRISC-03 §set.rd 伪指令 |
| `set.rd` | `set.rd rdxx, rs` | `rb2rd`/`rf2rd`/`ra2rd`/`rd2rd` | 从其他寄存器传值到 rd | SimRISC-03 §set.rd 伪指令 |
| `set.rb` | `set.rb rbxx, imm64` | `set.zw-rb` + `or.w-rb` | 加载立即数到 rb | SimRISC-03 §set.rb 伪指令 |
| `set.rb` | `set.rb rbxx, rs` | `rd2rb`/`rb2rb` | 从其他寄存器传值到 rb | SimRISC-03 §set.rb 伪指令 |
| `set.ft` | `set.ft rfxx, imm32` | `set.w`（2 条） | 加载单精浮点立即数 | SimRISC-03 §set.ft / set.fo 伪指令 |
| `set.fo` | `set.fo rfxx, imm64` | `set.w`（4 条） | 加载双精浮点立即数 | SimRISC-03 §set.ft / set.fo 伪指令 |
| `set.ft` | `set.ft rfxx, rs` | `rd2rf`/`ft2ft` | 从其他寄存器传值到 rf | SimRISC-03 §set.ft / set.fo 伪指令 |
| `set.fo` | `set.fo rfxx, rs` | `rd2rf`/`fo2fo` | 从其他寄存器传值到 rf | SimRISC-03 §set.ft / set.fo 伪指令 |
