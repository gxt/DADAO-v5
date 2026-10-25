# SimRISC指令系统

> **版本：0.5.6-rc**

SimRISC名称有三重含义：

- 一是Simple RISC，顾名思义，其基础设计理念是"Simple is beautiful" + RISC
- 二是Simulated RISC，其设计初衷是基于教学目的，故完全基于模拟环境进行设计开发
- 三是Similar RISC，基于RISC而不局限于RISC，在很多设计想法上希望在RISC基础上进行探索和突破

## 1. 数据表示

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

### 1.1 原始数据类型

现代处理器设计，通常是用指令 opc 来区分数据类型。
SimRISC中目前接收如下数据类型：

- 四种定点类型，长度分别为：8bit、16bit、32bit、64bit
- 两种浮点类型，长度分别为：32bit、64bit
  - 浮点格式的定义符合IEEE754标准

## 2. 寄存器

以一个程序员的观点看，用户可见寄存器有 4 组，每组 64 个寄存器（需 6 位编码），每个寄存器 64 位（即机器字长）：

- 数据寄存器 64 个：`rd0 - rd63`
- 基址寄存器 64 个：`rb0 - rb63`
- 浮点寄存器 64 个：`rf0 - rf63`
- 返回地址栈 64 个：`ra0 - ra63`

每组寄存器的 0 号寄存器都具有特殊功能，其操作可能受限。

### 2.1 数据寄存器

数据寄存器又可称为通用寄存器，主要用于各种运算，如下：

- 共64个数据寄存器，每个寄存器64位
- `rd0`固定为0，只读。作为目的寄存器时行为取决于指令格式：rrrr 双目的（add.uo/add.so/sub.uo/sub.so/mul.uo/mul.so）允许其中一个为 rd0（丢弃对应半结果），但不能**同时**为 rd0，也不能为同一非 rd0 寄存器；`ret rd0, 0` 允许（无需设置返回值）；其余指令目的为 rd0 时触发 ILLI 异常。

### 2.2 基址寄存器

基址寄存器又可称为地址寄存器，但是在SimRISC中只能用于基址，即绝对地址，简要说明如下：

- 共64个基址寄存器，每个寄存器64位，实际实现需保证48位地址空间
- `rb0` 读出为**当前正在执行的指令的地址**（**非下一条**），只读。`rb0` 即 **`IP`**（ABI 名 `rbip`；下文正文一律用 `IP` 指它）——**`IP` 的定义 = 当前正在执行的指令的地址**，**不是**主流 ISA 的「下一条指令地址」口径；本 ISA **无 `±4` 流水偏移**，`riii`/`rrii`/`iiii` 格式的指令的立即数基址即 `IP` 自身（如 `aip.si` 的 `imms18` 以该指令自身地址为基）。任何指令以 rb0 为显式目的时触发 ILLI 异常。`rb0[63:48]` 初值为 0，由控制流指令的硬件写入（见 SimRISC-06）。硬件复位后 `rb0` 初值为 `cfx_power_hypv_excp_vector`（见 SEE）。

基址寄存器（RB）为 64 位，低 48 位（bits[47:0]）为有效地址。

**存储模型**：SimRISC采用64位地址空间，有效虚拟地址为48位。RB 为整 64 位寄存器，存取/复制/立即数赋值等均为全 64 位操作；**作访存基址时取 `rb[47:0]`（低 48 位）**为有效地址。控制流地址计算按 64 位全宽进行（见 SimRISC-06）。

### 2.3 浮点寄存器

浮点寄存器只能用于浮点类指令，简要说明如下：

- 浮点寄存器支持单精和双精两种格式：
  - ft：tetra-size（32位单精）
  - fo：octa-size（64位双精）
- rf寄存器字长64位，当存放单精32位数据时，只使用低32位，高32位不做特殊规定
- `rf0`为浮点状态寄存器（FCSR）。它同时是单精、双精格式的qNaN，**可作浮点运算的源操作数**；又因其同时是状态寄存器，浮点运算执行后会更新其状态位（异常位），故 **`rf0`不可作浮点运算的目的操作数**

#### 2.3.1 浮点状态寄存器

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

浮点指令执行后，异常状态位（NV/DZ/OF/UF/NX）由硬件按 IEEE 754 标准设置到 rf0[4:0]。**标志为 sticky（累积）**：置位后保持为 1，直到软件写 `rf0` 清零；硬件不会自动清除。`UF` 与 `NX` **相互独立**：`UF` 仅在结果 tiny **且** inexact 时置位（tininess 检测点 = 舍入后，见 `SimRISC-07 §格式转换指令`）⇒ `UF` 置位时 `NX` 必同时置位；反之不成立（inexact 但非 tiny ⇒ 只置 `NX`）。软件可通过读取 rf0 检查异常状态，并根据需要进行后续处理。浮点指令不会触发异常，始终按 IEEE 754 标准返回结果（如 NaN、Inf 等）。

写 `rf0` 时**只更新** `[33..32]`（舍入模式）与 `[4..0]`（异常状态），其余位（只读 Quiet NaN 位、SBZ）**写无效、保持原值**。

### 2.4 返回地址栈

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
  - MemRAS 的访存遵循地址转换和存储访问规则：若访存触发页缺失等异常，硬件保证精确异常（压栈/弹栈未执行，IP 指向 call/ret 指令），异常处理后可重新执行。
- **RASOF** 仅由「需溢出且 `MRPTR == 0`」触发；**MemRAS 越界（容量耗尽）不由硬件检测（交 OS）**。
- **精确异常**：压栈/弹栈**先完成全部 `RASOF`/`RASUF` 判定**（含 D4b 的 MemRAS 条目读取与内容判定），判定通过后才进行 RA 寄存器或 MemRAS 访存的任何修改；异常时 RA 寄存器与内存均保持原状。

一个用户进程开始执行时，RegRAS 全部初始化为全零（`RACNT = 0`，条目内容全 0），MemRAS 应做好分配，并设置 `ra0`。fork 子进程应复制父进程的全部 ra 寄存器。

在进程运行过程中，返回地址栈通常无需程序干预，可以利用 `call` 和 `ret` 指令的动态一一对应的关系实现正确的压栈、弹栈操作。

进程切换时，操作系统须保存和恢复全部 ra0–ra63 寄存器。

异常进入和退出不改变 ra0–ra63 的内容，异常 handler 中可正常使用 call/ret 指令。信号处理时的 RA 保存恢复由操作系统负责，规则与进程切换一致。

#### 2.4.1 压栈流程（call 指令）

压栈按以下情形处理：

- **C1** `RACNT == 0` → 压入新条目（递归计数 = 1、返回地址），`RACNT = 1`；
- **C2** `RACNT > 0` 且 返回地址 == `ra63[47:0]`（栈顶返回地址）且 `ra63[63:48] < 0xFFFF` → **递归折叠优先**：`ra63[63:48] += 1`，`RACNT` 不变；
- **C3** 其余：
  - **C3a** `RACNT < 63` → 压入新条目（递归计数 = 1），`RACNT += 1`；
  - **C3b** `RACNT == 63` → ① `MRPTR == 0` → **RASOF**；② `MRPTR −= 8` 并把**栈底（最旧）条目**（`ra[64−RACNT]`）写入 `MRPTR` 处；③ 压入新条目 ⇒ 出栈底一条、入栈顶一条，`RACNT` 保持 63。

#### 2.4.2 弹栈流程（ret 指令）

弹栈按以下情形处理：

- **D1** `RACNT > 0` 且 `ra63[63:48] == 0` → **RASUF**；
- **D2** `RACNT > 0` 且 `ra63[63:48] > 1` → 计数 −1，`RACNT` 不变；
- **D3** `RACNT > 0` 且 `ra63[63:48] == 1` → 弹出栈顶，`RACNT − 1`；
- **D4** `RACNT == 0` →
  - **D4a** `MRPTR == 0` → **RASUF**；
  - **D4b** 读 `MRPTR` 处条目并作判定（`MRPTR` 暂不修改）：递归计数 = 0 → **RASUF**、= 1 → 返回地址 = 条目低 48 且 `MRPTR += 8`、> 1 → 该条目压入成为栈顶（计数 −1）且 `MRPTR += 8`、`RACNT = 1`。

#### 2.4.3 实现注（非架构语义）

实现可用**环形缓冲 + 隐藏基准索引**避免压栈/弹栈时的数据搬移；`ra_i` 为软件可见（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd`），访问须按基准索引换算以与架构视图一致。

#### 2.4.4 RA↔RD 块赋值

- `ra2rd`/`rd2ra` 在 RA 与 RD 之间进行全 64 位块赋值（含 RA 高 16 位：`ra0[53:48]` 为 `RACNT`，`ra1`–`ra63[63:48]` 为递归计数）。操作语义与异常条件见 SimRISC-02。

#### 2.4.5 call / ret 在本节的说明

- **`call`**：计算返回地址并按上述 C1–C3b 流程压入 RAS（见 §压栈流程）。
- **`ret`**：从 RAS 弹出返回地址（来源**可能不是 `ra63`**，取决于 RAS 状态）并跳转；可能触发 **RASUF** 异常（见 §弹栈流程）。

## 3. 指令设计

SimRISC中的每条指令都是四个字节，即32位。所有指令必须4字节对齐。取指时若 IP[1:0] ≠ 00，触发 IALIGN 异常。

> **通用约束交叉引用**：MALIGN 对齐规则见各存取指令章节（SimRISC-01），除法溢出规则见各数据运算章节（SimRISC-04/08/09/10），`immu6 = 0` 触发 ILLI 见各多寄存器操作章节。

指令字采用**大端序**存储：bits[31:24] 在最低地址，bits[7:0] 在最高地址。数据端序同样为大端序（见 ABI）。

### 3.1 指令域说明

通常，一个32位的指令会被分解为5个部分：8/6/6/6/6。
头8位是opc，主要指明指令功能，隐含指令分类。
后面四个6位记为ha/hb/hc/hd，主要指明具体的操作数，包括格式和内容。

opc 是操作码（opcode 的简写），即头 8 位。
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

- `OPC-byte`：byte 位宽指令
- `OPC-wyde`：wyde 位宽指令
- `OPC-tetra`：tetra 位宽指令
- `OPC-octa`：octa 位宽指令

各子表内使用 `orrr`/`orri`/`oiii` 操作数格式。指令名后缀 `.b`/`.w`/`.t`/`.o` 与已有的存取指令后缀（`ldb`/`ldw`/`ld.t`/`ld.o`）一致。对有符号/无符号区分的指令（mul/div/rem/cmp/ext/shr），后缀扩展为 `.ub`/`.sb`（byte）、`.uw`/`.sw`（wyde）、`.ut`/`.st`（tetra）、`.uo`/`.so`（octa），其中 `s` 表示有符号、`u` 表示无符号。**符号无关**的指令（`shl`/`rol`/`rev`/`ctpop`/`ctlz`/`cttz`）**不带 `u`/`s` 后缀**。

以下三种格式含 `c`（cfxha，6 位核芯功能扩展编码），cfxha 始终在 `ha[5:0]`：

- `crrr`：cfxha + 三个 6 位寄存器编号，cg 在 `hb`，rc 在 `hc`，rd 在 `hd`（cfx2rd/cfx2rc）
- `crii`：cfxha + 6 位 rb 寄存器在 `hb` + 12 位立即数在 `hc[5:0]`+`hd[5:0]`（hc=高位, hd=低位，cfxld/cfxst）
- `ciii`：cfxha + 18 位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]`（hb=高位, hc=中位, hd=低位，trap/escape）

SimRISC 通常将目的操作数放在最前面，然后是寄存器源操作数，从而可以把立即数放在最后，并且立即数通常为最后一个源操作数，可以直观的从二进制上判断出立即数。
其好处是便于调试，根据二进制可以直观地猜出部分指令内容。

### 3.2 标识位说明

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

## 4. SimRISC QFC

SimRISC 的指令 opc 布局如下。空白单元格表示 reserved（保留未分配）。

|           | xxxx-x000      | xxxx-x001      | xxxx-x010       | xxxx-x011       | xxxx-x100      | xxxx-x101      | xxxx-x110       | xxxx-x111     |
| ---       | ---            | ---            | ---             | ---             | ---            | ---            | ---             | ---           |
| 0000-0xxx |                |                |                 |                 |                |                |                 |               |
| 0000-1xxx |                |                |                 |                 |                |                |                 |               |
| 0001-0xxx | ld.ub_rrii_rd  | ld.uw_rrii_rd  | ld.ut_rrii_rd   | ld.sb_rrii_rd   | ld.sw_rrii_rd  | ld.st_rrii_rd  | ld.t_rrii_rf    | st.t_rrii_rf  |
| 0001-1xxx | st.b_rrii_rd   | st.w_rrii_rd   | st.t_rrii_rd    |                 |                |                |                 |               |
| 0010-0xxx | ld.o_rrii_rd   | st.o_rrii_rd   | ld.o_rrii_rb    | st.o_rrii_rb    | ld.o_rrii_ra   | st.o_rrii_ra   | ld.o_rrii_rf    | st.o_rrii_rf  |
| 0010-1xxx | ldm.ub_rrri_rd | ldm.uw_rrri_rd | ldm.ut_rrri_rd  | ldm.sb_rrri_rd  | ldm.sw_rrri_rd | ldm.st_rrri_rd | ldm.t_rrri_rf   | stm.t_rrri_rf |
| 0011-0xxx | stm.b_rrri_rd  | stm.w_rrri_rd  | stm.t_rrri_rd   |                 |                |                |                 |               |
| 0011-1xxx | ldm.o_rrri_rd  | stm.o_rrri_rd  | ldm.o_rrri_rb   | stm.o_rrri_rb   | ldm.o_rrri_ra  | stm.o_rrri_ra  | ldm.o_rrri_rf   | stm.o_rrri_rf |
| 0100-0xxx | OPC-octa       | OPC-tetra      | OPC-wyde        | OPC-byte        | OPC-RF         |                |                 | OPC-MISC      |
| 0100-1xxx | or.w_rwii_rd   | andn.w_rwii_rd | or.w_rwii_rb    | andn.w_rwii_rb  | set.zw_rwii_rd | set.ow_rwii_rd | set.zw_rwii_rb  | set.w_rwii_rf |
| 0101-0xxx | add.uo_rrrr_rd | add.so_rrrr_rd | sub.uo_rrrr_rd  | sub.so_rrrr_rd  | mul.uo_rrrr_rd | mul.so_rrrr_rd | clmul.o_rrrr_rd |               |
| 0101-1xxx |                | add.si_riii_rd | aip.si_riii_rb  | add.si_riii_rb  | cmp.ui_rrii_rd | cmp.si_rrii_rd | ftfma_rrrr_rf   | fofma_rrrr_rf |
| 0110-0xxx | cs.n_rrrr_rd   | cs.n_rrrr_rf   | cs.z_rrrr_rd    | cs.z_rrrr_rf    | cs.p_rrrr_rd   | cs.p_rrrr_rf   | cs.eq_rrrr_rd   | cs.ne_rrrr_rd |
| 0110-1xxx | br.n_riii_rd   | br.nn_riii_rd  | br.z_riii_rd    | br.nz_riii_rd   | br.p_riii_rd   | br.np_riii_rd  | br.eq_rrii_rd   | br.ne_rrii_rd |
| 0111-0xxx | jump_iiii_rb   | jump_rrii_rb   | br.z_riii_rb    | br.nz_riii_rb   | call_iiii_ra   | call_rrii_ra   | ret_riii_ra     |               |
| 0111-1xxx |                |                | cfx2rd_crrr_cfx | cfx2rc_crrr_cfx | cfxld_crii_cfx | cfxst_crii_cfx | escape_ciii_cfx | trap_ciii_cfx |

### 4.1 OPC-MISC 指令编码

空白单元格为 reserved（保留未分配）。

|         | xxx-000         | xxx-001         | xxx-010         | xxx-011         | xxx-100         | xxx-101         | xxx-110         | xxx-111         |
| ---     | ---             | ---             | ---             | ---             | ---             | ---             | ---             | ---             |
| 000-xxx | lr.o.nn_orrr_rd | lr.t.nn_orrr_rd | lr.w.nn_orrr_rd | lr.b.nn_orrr_rd | lr.o.an_orrr_rd | lr.t.an_orrr_rd | lr.w.an_orrr_rd | lr.b.an_orrr_rd |
| 001-xxx | lr.o.ar_orrr_rd | lr.t.ar_orrr_rd | lr.w.ar_orrr_rd | lr.b.ar_orrr_rd |                 |                 |                 |                 |
| 010-xxx | sc.o.nn_orrr_rd | sc.t.nn_orrr_rd | sc.w.nn_orrr_rd | sc.b.nn_orrr_rd | sc.o.nr_orrr_rd | sc.t.nr_orrr_rd | sc.w.nr_orrr_rd | sc.b.nr_orrr_rd |
| 011-xxx | sc.o.ar_orrr_rd | sc.t.ar_orrr_rd | sc.w.ar_orrr_rd | sc.b.ar_orrr_rd |                 |                 |                 |                 |
| 100-xxx | fence_oiii_imm  |                 | swym_oiii_imm   |                 |                 | ctpop_orri_rd   | ctlz_orri_rd    | cttz_orri_rd    |
| 101-xxx |                 |                 |                 |                 |                 |                 |                 |                 |
| 110-xxx |                 |                 |                 |                 |                 |                 |                 |                 |
| 111-xxx |                 |                 |                 |                 |                 |                 |                 |                 |

### 4.2 OPC-octa指令编码

octa 位宽（64 位）指令。指令名后缀 `.o` 表示 octa 位宽。
空白单元格为 reserved（保留未分配）。

|         | xxx-000        | xxx-001        | xxx-010         | xxx-011        | xxx-100       | xxx-101       | xxx-110       | xxx-111 |
| ---     | ---            | ---            | ---             | ---            | ---           | ---           | ---           | ---     |
| 000-xxx |                |                |                 |                |               |               |               |         |
| 001-xxx | and.o_orrr_rd  | or.o_orrr_rd   | xor.o_orrr_rd   | xnor.o_orrr_rd | rev.o_orri_rd |               |               |         |
| 010-xxx | shl.o_orrr_rd  | rol.o_orrr_rd  | shr.uo_orrr_rd  | shr.so_orrr_rd |               |               |               |         |
| 011-xxx | shl.o_orri_rd  | rol.o_orri_rd  | shr.uo_orri_rd  | shr.so_orri_rd |               |               |               |         |
| 100-xxx | ext.uo_orrr_rd | ext.so_orrr_rd |                 |                |               |               |               |         |
| 101-xxx | ext.uo_orri_rd | ext.so_orri_rd | cmp.uo_orrr_rd  | cmp.so_orrr_rd | rd2rd_orri_rd | rd2ra_orri_ra | ra2rd_orri_ra |         |
| 110-xxx | add.o_orrr_bbd | sub.o_orrr_bbd | cmp.uo_orrr_dbb | sub.o_orrr_dbb | rb2rb_orri_rb | rd2rb_orri_rb | rb2rd_orri_rb |         |
| 111-xxx | div.uo_orrr_rd | div.so_orrr_rd | rem.uo_orrr_rd  | rem.so_orrr_rd |               | rd2rf_orri_rf | rf2rd_orri_rf |         |

### 4.3 OPC-tetra指令编码

tetra 位宽（32 位）指令。指令名后缀 `.t` 表示 tetra 位宽。
空白单元格为 reserved（保留未分配）。

|         | xxx-000        | xxx-001        | xxx-010        | xxx-011        | xxx-100       | xxx-101 | xxx-110 | xxx-111 |
| ---     | ---            | ---            | ---            | ---            | ---           | ---     | ---     | ---     |
| 000-xxx |                |                |                |                |               |         |         |         |
| 001-xxx |                |                |                |                | rev.t_orri_rd |         |         |         |
| 010-xxx | shl.t_orrr_rd  | rol.t_orrr_rd  | shr.ut_orrr_rd | shr.st_orrr_rd |               |         |         |         |
| 011-xxx | shl.t_orri_rd  | rol.t_orri_rd  | shr.ut_orri_rd | shr.st_orri_rd |               |         |         |         |
| 100-xxx | add.ut_orrr_rd | add.st_orrr_rd |                |                |               |         |         |         |
| 101-xxx | sub.ut_orrr_rd | sub.st_orrr_rd | cmp.ut_orrr_rd | cmp.st_orrr_rd |               |         |         |         |
| 110-xxx | mul.ut_orrr_rd | mul.st_orrr_rd |                |                |               |         |         |         |
| 111-xxx | div.ut_orrr_rd | div.st_orrr_rd | rem.ut_orrr_rd | rem.st_orrr_rd |               |         |         |         |

> **注**：上表空白单元格 = reserved（保留未分配）。

### 4.4 OPC-wyde指令编码

wyde 位宽（16 位）指令。指令名后缀 `.w` 表示 wyde 位宽。
空白单元格为 reserved（保留未分配）。

|         | xxx-000        | xxx-001        | xxx-010        | xxx-011        | xxx-100       | xxx-101 | xxx-110 | xxx-111 |
| ---     | ---            | ---            | ---            | ---            | ---           | ---     | ---     | ---     |
| 000-xxx |                |                |                |                |               |         |         |         |
| 001-xxx |                |                |                |                | rev.w_orri_rd |         |         |         |
| 010-xxx | shl.w_orrr_rd  | rol.w_orrr_rd  | shr.uw_orrr_rd | shr.sw_orrr_rd |               |         |         |         |
| 011-xxx | shl.w_orri_rd  | rol.w_orri_rd  | shr.uw_orri_rd | shr.sw_orri_rd |               |         |         |         |
| 100-xxx | add.uw_orrr_rd | add.sw_orrr_rd |                |                |               |         |         |         |
| 101-xxx | sub.uw_orrr_rd | sub.sw_orrr_rd | cmp.uw_orrr_rd | cmp.sw_orrr_rd |               |         |         |         |
| 110-xxx | mul.uw_orrr_rd | mul.sw_orrr_rd |                |                |               |         |         |         |
| 111-xxx | div.uw_orrr_rd | div.sw_orrr_rd | rem.uw_orrr_rd | rem.sw_orrr_rd |               |         |         |         |

> **注**：上表空白单元格 = reserved（保留未分配）。

### 4.5 OPC-byte指令编码

byte 位宽（8 位）指令，覆盖移位、扩展、逻辑、算术、比较、乘除等操作。指令名后缀 `.b` 表示 byte 位宽。
空白单元格为 reserved（保留未分配）。

|         | xxx-000        | xxx-001        | xxx-010        | xxx-011        | xxx-100       | xxx-101 | xxx-110 | xxx-111 |
| ---     | ---            | ---            | ---            | ---            | ---           | ---     | ---     | ---     |
| 000-xxx |                |                |                |                |               |         |         |         |
| 001-xxx |                |                |                |                | rev.b_orri_rd |         |         |         |
| 010-xxx | shl.b_orrr_rd  | rol.b_orrr_rd  | shr.ub_orrr_rd | shr.sb_orrr_rd |               |         |         |         |
| 011-xxx | shl.b_orri_rd  | rol.b_orri_rd  | shr.ub_orri_rd | shr.sb_orri_rd |               |         |         |         |
| 100-xxx | add.ub_orrr_rd | add.sb_orrr_rd |                |                |               |         |         |         |
| 101-xxx | sub.ub_orrr_rd | sub.sb_orrr_rd | cmp.ub_orrr_rd | cmp.sb_orrr_rd |               |         |         |         |
| 110-xxx | mul.ub_orrr_rd | mul.sb_orrr_rd |                |                |               |         |         |         |
| 111-xxx | div.ub_orrr_rd | div.sb_orrr_rd | rem.ub_orrr_rd | rem.sb_orrr_rd |               |         |         |         |

> **注**：上表空白单元格 = reserved（保留未分配）。

### 4.6 OPC-RF指令编码

> 取整 `ftrnd_orri_rf`/`fornd_orri_rf` 与最小/最大值 `ftmin_orrr_rf`/`ftmax_orrr_rf`/`fomin_orrr_rf`/`fomax_orrr_rf` 见 SimRISC-07。

空白单元格为 reserved（保留未分配）。

|         | xxx-000        | xxx-001        | xxx-010       | xxx-011       | xxx-100       | xxx-101        | xxx-110        | xxx-111        |
| ---     | ---            | ---            | ---           | ---           | ---           | ---            | ---            | ---            |
| 000-xxx | ftcls_orri_rf  | ft2fo_orri_rf  | ft2ft_orri_rf | ftrnd_orri_rf |               |                | ftroot_orri_rf |                |
| 001-xxx | focls_orri_rf  | fo2ft_orri_rf  | fo2fo_orri_rf | fornd_orri_rf |               |                | foroot_orri_rf |                |
| 010-xxx | ftadd_orrr_rf  | ftsub_orrr_rf  | ftmul_orrr_rf | ftdiv_orrr_rf | ftrem_orrr_rf | ftsclb_orrr_rf | ftsgnn_orrr_rf | ftsgnj_orrr_rf |
| 011-xxx | foadd_orrr_rf  | fosub_orrr_rf  | fomul_orrr_rf | fodiv_orrr_rf | forem_orrr_rf | fosclb_orrr_rf | fosgnn_orrr_rf | fosgnj_orrr_rf |
| 100-xxx | ftqcmp_orrr_rf | ftscmp_orrr_rf |               |               |               |                | ftmin_orrr_rf  | ftmax_orrr_rf  |
| 101-xxx | foqcmp_orrr_rf | foscmp_orrr_rf |               |               |               |                | fomin_orrr_rf  | fomax_orrr_rf  |
| 110-xxx | ft2it_orri_rf  | ft2io_orri_rf  | ft2ut_orri_rf | ft2uo_orri_rf | it2ft_orri_rf | io2ft_orri_rf  | ut2ft_orri_rf  | uo2ft_orri_rf  |
| 111-xxx | fo2it_orri_rf  | fo2io_orri_rf  | fo2ut_orri_rf | fo2uo_orri_rf | it2fo_orri_rf | io2fo_orri_rf  | ut2fo_orri_rf  | uo2fo_orri_rf  |

## 5. 伪指令

> **伪指令集的权威定义在 `spec/Toolchain-01-汇编语言.md`**。伪指令**不是**硬件指令，由汇编器在前端展开为一条或多条真实硬件指令；**反汇编器只输出真实硬件指令**，不输出伪指令。

本版仅保留「ISA 无法直接表达、需多指令合成」的合成型伪指令（`set.rd`/`set.rb`/`set.ft`/`set.fo`，各有「立即数」与「寄存器」两种源形式）；逐条语法、展开规则与示例见 `Toolchain-01`（`set.*` 的 wyde 级展开示例见 SimRISC-03）。

## 6. 异常规则

### 6.1 非法指令（ILLI）

ILLI（illegal instruction，非法指令）异常由**非法操作数、非法条件**或**已定义但本机器未实现的编码**触发；SimRISC 0.5.4 **不再**提供专门的非法指令助记符。

- 已定义编码但操作数/字段非法时触发 ILLI，例如很多指令不允许目的操作数为 `rd0`、SBZ 字段非零、多寄存器指令 `immu6 = 0` 等。
- `cfxld`/`cfxst`、LR-SC 原子（`lr`/`sc`）与 `fence` 的已定义编码，在未实现该语义的机器上执行时触发 ILLI。

### 6.2 保留编码（UNDI）

保留编码（QFC 主表 / MISC 子表空白单元格）触发 UNDI 异常，而非 ILLI；32 位全零指令字亦为保留编码，触发 UNDI 异常。

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.5.6-rc（未发布）

- 修正窄位宽比较 `cmp.{ut,uw,ub}` 的 −1 扩展：原文「结果零扩展」为错误，现统一按 **64 位扩展**写满目的寄存器（−1 ⇒ 64 位全 1、0 ⇒ 0、+1 ⇒ 1），与 `.st`/`.sw`/`.sb` 同值；源操作数仍按位宽截断后比较。
- `SimRISC QFC` 布局说明去掉版本号限定（布局表随版本演进，不再绑定单一版本号）。

### 0.5.5（2026-10-24）

本版含编码不兼容变更（`OPC-MISC` 编码迁移等）。

- 新增融合乘加 `ftfma`/`fofma`（`rrrr`：1 目的 + 3 源；乘加不中间舍入，只舍入一次）。
- 新增取整 `ftrnd`/`fornd`（六档取整，`immu6` one-hot）与最小/最大值 `ftmin`/`ftmax`/`fomin`/`fomax`（`minimumNumber`/`maximumNumber` 语义：单 NaN 返回数字、双 NaN 得 canonical qNaN、`-0 < +0`、sNaN 触发 NV、不涉舍入不置 NX）；六条均转为可执行（不再按 ILLI 解码），`dst_rf0` 与 `encode_onehot` 合法性生效。
- 新增无进位乘 `clmul.o`（`rrrr` 双目的，`rdHA` 高 / `rdHB` 低）、`rol.o`/`rol.t`/`rol.w`/`rol.b`（逻辑循环左移）与 `rev.o`/`rev.t`/`rev.w`/`rev.b`（逐块反转）；新增无位宽后缀的 `ctlz`/`cttz`/`ctpop`（位扫描 / 位计数）与 `sub.o`（RB−RB→RD）；RB 算术三条（`add.o`/`sub.o` 的 `bbd` 形态、`cmp.uo` 的 `dbb` 形态）同时改名并调整编码槽。
- 恢复 64 位 IP 相对寻址指令并定名 **`aip.si`**（`riii`）：`rbHA = IP + (imms18 << 12)`，`IP` 取该指令自身地址、不清低位；操作数按字节计（汇编层 `imms30`、编码层 `imms18 = imms30 >> 12`），结果写 RB 银行，可达 ±512 MiB（即与 `auipc` 的三点差异）。
- 删除 `ftlog`/`folog`，`ftroot`/`foroot` 仅保留 n=2；删除浮点条件赋值 `cs.eq_rrrr_rf`/`cs.ne_rrrr_rf`（仅留 `cs.n`/`cs.z`/`cs.p` 的 rf 变体，判「比较结果为 1」改用 `sub` + `cs.z`）；删除 `illi`；伪指令收缩为需多指令合成的合成型（`set.*`），去掉 1:1 别名。
- `OPC-MISC` 编码面定稿（`opc = 0x47`）：`lr`/`sc` 为 `<lr|sc>.<b|w|t|o>.<nn|an|ar|nr>` 共 24 条（`lr` 占 `000`/`001`、`sc` 占 `010`/`011`，删 `lr.*.nr` 与 `sc.*.an`）；`fence` 占 `100-000`（`ha = 0x20`，`immu18` 拆为 `fm`/`pred`/`succ`）；`swym` 占 `100-010`；`ctpop`/`ctlz`/`cttz` 占 `100-101`/`100-110`/`100-111`。
- 位宽子表重排：`ext.uo`/`ext.so` 迁 `100-000`/`100-001`（`orrr`）与 `101-000`/`101-001`（`orri`）；`shl` 四位宽变体去 `u` 后缀并迁 `010-000`/`011-000`；`rol` 占 `010-001`/`011-001`；`rev` 在各子表占 `001-100`。
- 浮点与整型编码定稿：`ftfma`/`fofma` 占 `0101-1110`/`0101-1111`，`clmul.o` 占 `0101-0110`；`ftrnd`/`fornd` 占 `000-011`/`001-011`（`OPC-RF`），`ftmin`/`ftmax`/`fomin`/`fomax` 占 `100-110`/`100-111`/`101-110`/`101-111`（`OPC-RF`）；`trap`/`escape`/`cfx2rc`/`cfx2rd` 重新划分编码归属，`ret rd0` 收为 `imms18 = 0` 合法性约束。
- `cmp.uo`-rb 改为整 64 位比较；RB 与控制流地址语义修正；窄位宽指令精简，高位处理统一为值语义。
- `lr`/`sc` 对齐口径按数据宽度自然对齐（`.b`=1 / `.w`=2 / `.t`=4 / `.o`=8 字节），不满足触发 MALIGN。
- 浮点状态寄存器 `rf0` 位域与访问规则调整；0 号寄存器作源操作数的语义澄清、各寄存器组 0 号寄存器用途措辞定稿。
- `focls`/`ftcls` 分类位序改为 IEEE 754-2019 `class` 的类别顺序（破坏性：与 RISC-V `fclass` 位序不兼容）；浮点异常标志口径补齐——`UF` 仅在结果 tiny 且 inexact 时置位、tininess 检测点在舍入后、标志 sticky，且 `UF ⇒ NX`。
- 术语统一：`major-op`/`minor-op` → `opc`/`opx`，`PC` → `IP`（`IP` 为当前正在执行的指令的地址，无 `±4` 流水偏移）。
- 文档结构：原子指令（`fence`/`lr`·`sc`）并入其它指令册，核芯功能扩展册收 `trap`/`escape`/`cfx2rd`/`cfx2rc`（`cfxld`/`cfxst` 待定），非法指令与保留编码总规则并入设计册；标题章节号统一为 `N` / `N.M` / `N.M.K`，新增汇编指令速查与合法性检查两个附录。

### 0.5.4（2026-09-28）

- 手册重组为 13 个分册：指令系统设计 / 取数存数 / 寄存器复制 / 16 位立即数操作 / 64 位数据运算 / 64 位地址运算 / 控制流 / 浮点运算 / 32 位数据运算 / 16 位数据运算 / 8 位数据运算 / 其它 / 待定。
- 伪指令自 ABI 迁回 SimRISC 各册，并新增伪指令汇总表；新增 `neg.b/w/t/o`（取负）与 `not.b/w/t/o`（取反）伪指令。
- 删除 FPEXCP 异常（浮点按 IEEE 754 执行、经 `rf0` 轮询异常状态）。
- 职责边界调整：数据表示 / 寄存器 / 返回地址栈移入指令系统设计册。
- 目录 `wiki/` 重命名为 `spec/`。

### 0.5.3（2026-07-19）

- QFC 重排：`OPC-MISC` 移到 `x000`、`OPC-RF` 位于 `0100-0100`；`jump`/`call`/`ret` 编码 +2、`trap`/`escape` 对调；`illi` 移入 `OPC-octa`。
- `setrd`/`setrb`/`setrf` 改名为 `set.rd`/`set.rb`/`set.rf`。
- `add.si` 改为 `riii` 格式、立即数 18 位、源=目的；`opc` 调整。

### 0.5.2（2026-07-18）

- 删除 `bpN`/`brrr`/`brri`，改用 `OPC-byte`/`OPC-wyde`/`OPC-tetra`/`OPC-octa` 四种固定位宽子表。
- 指令名后缀统一为 `.ub`/`.sb`/`.uw`/`.sw`/`.ut`/`.st`/`.uo`/`.so`；存取指令名统一为 `ld.*`/`st.*` 后缀形。
- `add`/`sub` `rrrr` 拆分为 `add.uo`/`add.so`/`sub.uo`/`sub.so`；`addi`→`add.si`；`cmps`/`cmpu`→`cmp.si`/`cmp.ui`；`orr`→`or`。
- `cs.`/`br.` 指令名加点、条件后缀统一；浮点存取 / 立即数 / 条件赋值指令名后缀统一。
- `rwii` 指令名改为 `or.w`/`andn.w`/`set.ow`/`set.zw`/`set.w`；新增 `setrd`/`setrb`/`setrf` 伪指令定义。
- `ld.o`/`st.o` 用于 RB/RA/RF 全 64 位存取；`swym` 改 `iiii` 格式、`unimp`→`illi`。
- 修复 `lr`/`sc` 描述不一致；`fence` 编码整理。

### 0.5.1（2026-07-17）

- 编码表重排（常规表 / `jump` / `call` / `ret` / `OPC-MISC` 移入新表）；`ld`/`st` 宽度对齐、`stm`/`ldm` 连续排列。
- QFC 重构：`OPC-MISC` 并入常规表、`exts`/`extz` 移 `0001` 行、`swym` 移 `0111`。
- 新增 `ld.o`/`st.o`-ra 形式，RA 存取对齐补全；存取对齐要求（`ldm`/`stm`）移入限制列表。
- `RASUP`→`RASUF`；特权模型与 SEE 对齐，删冗余 ILLI 声明。
- `rd0` 为目的寄存器的约定收窄：仅 `add`/`sub`/`mul` 的 `rrrr` 双目的格式允许其中一个为 `rd0`。

### 0.5.0（2026-07-15）

- 新增 `brrr` 格式（`cmps`/`cmpu`/`add`/`sub`/`muls`/`mulu`）；删除 `cmps`/`cmpu`-`orrr`。
- 位掩码 `bN`→`bmN`→`bpN`（bit position）重命名；`ww`→`wpN`（wyde position）重命名，16 位立即数按 `wp0`–`wp3` 定位。
- 格式分组整理（r/rw/o/b/c 分类）；删除 `orii`、`oiii` 补 18 位分配；`swym` 改 `iiii` 格式、`unimp`→`illi`。
- `divs`/`divu` 改为 `rem` 余数语义；浮点运算指令编码整理。

### 0.4.1（2026-07-14）

- 初版：自 DADAO.wiki 同步 SimRISC 指令系统设计（数据表示 / 寄存器 / 指令设计 / QFC / 伪指令）。
