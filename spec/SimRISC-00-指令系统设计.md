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
- `rb0` 为 PC，只读。任何指令以 rb0 为显式目的时触发 ILLI 异常。`rb0[63:48]` 恒为 0。硬件复位后 `rb0` 初值为 `cfx_power_hypv_excp_vector`（见 SEE §2.1）。

基址寄存器（RB）为 64 位，低 48 位（bits[47:0]）为有效地址。

各类操作对高 16 位（bits[63:48]）的处理规则如下：

| 操作类别 | 指令 | 高 16 位行为 |
|---------|------|-------------|
| 存取类指令 | `ld.o`/`ldm.o`/`st.o`/`stm.o`（内存→RB） | **全 64 位覆盖，bits[63:48] 正常读写** |
| 赋值类指令-寄存器 | `rd2rb`/`rb2rb`/`ra2rd`/`rd2ra` | **全 64 位覆盖，bits[63:48] 正常读写** |
| 赋值类指令-立即数 | `set.zw-rb`/`or.w-rb`/`andn.w-rb` | **全 64 位覆盖，bits[63:48] 正常读写，允许 wyde-pos=3** |
| 算术运算类指令-加减 | `add.so-rb`/`sub.so-rb`/`add.si-rb`/`rela.si` | 二进制补码 64 位全宽加减法，地址仅在低 48 位有效；**bits[63:48]**为运算结果，可用于溢出检测 |
| 算术运算类指令-比较 | `cmp.uo-rb` | 无符号 64 位比较，结果 -1/0/1 区分小于/等于/大于；**bits[63:48] 不影响比较运算** |
| 控制流指令-跳转 | `br*`/`jump` | 地址计算仅在低 48 位进行，溢出丢弃；**bits[63:48] 保持不变** |
| 控制流指令-函数支持 | `call`/`ret` | 地址计算仅在低 48 位进行，溢出丢弃；**bits[63:48] 做为引用计数** |

RB 的高 16 位尚未定义用途，初始值为全 0。软件不应依赖高 16 位的值。RA 寄存器的高 16 位另有定义（见 AEE §返回地址栈：ra0 为 MemRAS 引用计数，ra1–ra63 为返回地址引用计数）。

**存储模型**：SimRISC采用64位地址空间，有效虚拟地址为48位。高16位（bits[63:48]）在地址计算时被硬件忽略，寄存器存取时保持高16位原值不变。

### 浮点寄存器

浮点寄存器只能用于浮点类指令，简要说明如下：

- 浮点寄存器支持单精和双精两种格式：
  - ft：tetra-size（32位单精）
  - fo：octa-size（64位双精）
- rf寄存器字长64位，当存放单精32位数据时，只使用低32位，高32位不做特殊规定
- `rf0`为浮点状态寄存器，不应采用rf0作为普通的浮点寄存器参与运算

#### 浮点状态寄存器

`rf0`为浮点状态寄存器，具体定义如下：

- [63..51]: 0111 1111 1111 1（只读，写无效；其值为fo格式下的Quiet NaN，即符号位为0，E为全1，尾数最高位为1）
- [50..32]: SBZ（Should Be Zero）
- [31..22]: 0111 1111 11（只读，写无效；其值为ft格式下的Quiet NaN，即符号位为0，E为全1，尾数最高位为1）
- [21..18]: SBZ（Should Be Zero）
- [17..16]：舍入模式（Rounding Mode）
- [15..5]：SBZ（Should Be Zero）
- [4..0]：异常状态（Accured exception）

舍入模式定义如下：（舍入模式的设置单独放在wp1中，程序可以直接用setw指令进行设置）

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

### 返回地址栈

返回地址栈（Return Address Stack）专门用于支持函数的调用和返回，采用后入先出的方式，将函数的返回地址统一存放在单独可寻址的栈上，简要说明如下：

| 寄存器 | 高 16 位 | 低 48 位 |
|--------|----------|----------|
| ra0 | MemRAS 引用计数（压栈 +1，弹栈 -1，初始 0） | MemRAS 指针（0 = 仅 RegRAS） |
| ra1 - ra62 | 返回地址引用计数（>0 为有效，=0 为无效） | 返回地址 |
| ra63 | 返回地址引用计数（>0 为有效，=0 为无效） | 当前返回地址（RegRAS 栈顶） |

- `ra1 - ra63`：构成 RegRAS，`ra63` 为 RegRAS 的栈顶
- `ra0`：低48位有效，高16位记录 MemRAS 压栈/弹栈的次数（每次压栈 + 1，每次弹栈 - 1；初始值应为0）
  - 当 `ra0` 低48位为0时，只有一个RAS，即RegRAS；因此，最多在RegRAS中存放63个返回地址，（不考虑递归情况下）调用深度超过63时触发异常
  - 当 `ra0` 低48位不为0时，有两个RAS，RegRAS和MemRAS，MemRAS 是事先分配好的一段存储空间，`ra0` 为MemRAS的栈顶
  - MemRAS 的访存遵循地址转换和存储访问规则：若访存触发页缺失等异常，硬件保证精确异常（压栈/弹栈未执行，PC 指向 call/ret 指令），异常处理后可重新执行

RASOF/RASUF 均为精确异常：触发时 RA 寄存器保持异常前状态（push/pop 未提交），PC 指向触发异常的 call/ret 指令，异常处理程序恢复后可重试。

一个用户进程开始执行时，RegRAS 全部初始化为全零（`ra[63:48]=0`，所有条目无效），MemRAS 应做好分配，并设置 `ra0`。fork 子进程应复制父进程的全部 ra 寄存器。

在进程运行过程中，返回地址栈通常无需程序干预，可以利用 `call` 和 `ret` 指令的动态一一对应的关系实现正确的压栈、弹栈操作。

进程切换时，操作系统须保存和恢复全部 ra0-ra63 寄存器。

异常进入和退出不改变 ra0-ra63 的内容，异常 handler 中可正常使用 call/ret 指令。信号处理时的 RA 保存恢复由操作系统负责，规则与进程切换一致。

#### 压栈流程（call 指令）

以 `ra63` 为 RegRAS 栈顶，高 16 位为返回地址的引用计数（0 表示无效），低 48 位为返回地址。压栈分三种情况：

1. 若 `ra63` 高16位全为0（无效返回地址），则新的返回地址压入 `ra63`，高16位设为 0x0001
2. 若 `ra63` 高16位既不全为0 且不全为1，且新的返回地址 和 `ra63` 低48位相等（递归调用），则 `ra63` 高16位 + 1
3. 否则（新的返回地址 和 `ra63` 低48位不相等，或 `ra63` 高16位全为1），需要移位压栈：
   - 新的返回地址压入 `ra63`，高16位设为 0x0001
   - 原 `ra63` 压入 `ra62`，原 `ra62` 的内容如为有效地址，则压入 `ra61`，依次向下，直至原 `ra2` 的内容如为有效地址，则压入 `ra1`
   - 原 `ra1` 的内容如为有效地址，则：
      - 当 `ra0` 低48位为0时，只有一个RAS，即RegRAS，触发 **RASOF** 异常
      - 当 `ra0` 低48位不为0时，有两个RAS，则将 `ra1` 压入 MemRAS（`ra0` 低48位减 8，将 `ra1` 存入 `ra0` 地址；`ra0` 高16位为 16 位无符号计数，若当前计数为 0xFFFF 再加 1 则溢出，触发 **RASOF** 异常）

#### 弹栈流程（ret 指令）

弹栈也分为三种情况：

1. 若 `ra63` 高16位 > 0x0001，则 `ra63` 高16位 - 1，`ra63` 低48位内容作为返回地址
2. 若 `ra63` 高16位 = 0x0001，则弹出 `ra63` 的低48位内容作为返回地址，并进行移位弹栈：
   - 原 `ra62` 的内容如为有效地址，则存入 `ra63`，原 `ra61` 的内容如为有效地址，则存入 `ra62`，依次向下，直至原 `ra1` 的内容如为有效地址，则存入 `ra2`，`ra1` 清0
3. 若 `ra63` 高16位全为0（无效返回地址）：
   - 当 `ra0` 低48位为0时，只有一个RAS，即RegRAS，触发 **RASUF** 异常
   - 当 `ra0` 低48位不为0时，有两个RAS，则从 MemRAS 弹栈（读取 `ra0` 低48位地址的内容，`ra0` 低48位加 8；`ra0` 高16位为 16 位无符号计数，若当前计数为 0 再减 1 则溢出，触发 **RASUF** 异常）
     - 弹出的内容，若高16位为 0（无效返回地址），则触发 **RASUF** 异常
     - 弹出的内容，若高16位为 0x0001，则其低48位为返回地址
     - 弹出的内容，若高16位 > 0x0001，则将其存入 `ra63`，且高16位 - 1，低48位为返回地址

## 指令设计

SimRISC中的每条指令都是四个字节，即32位。所有指令必须4字节对齐。取指时若 PC[1:0] ≠ 00，触发 IALIGN 异常。

> **通用约束交叉引用**：MALIGN 对齐规则见各存取指令章节（SimRISC-01），除法溢出规则见各数据运算章节（SimRISC-04/08/09/10），`immu6 = 0` 触发 ILLI 见各多寄存器操作章节。

指令字采用**大端序**存储：bits[31:24] 在最低地址，bits[7:0] 在最高地址。数据端序同样为大端序（见 ABI §数据表示）。

### 指令域说明

通常，一个32位的指令会被分解为5个部分：8/6/6/6/6。
头8位是op，主要指明指令功能，隐含指令分类。
后面四个6位记为ha/hb/hc/hd，主要指明具体的操作数，包括格式和内容。

op是操作码，简称为opcode，或者称之为major-opcode。
某些情况下，ha或ha+hb也可作为opcode，或称为minor-opcode。
特殊情况下（后16位作为立即数时），hb的头两位用来指定wyde在64位数据中的位置。

ha/hb/hc/hd通过不同的寻址方式组合成操作数，h含义为hexagram，既是六，也是六十四。
操作数的寻址方式分别用以下几个字母表示：

- `o`：六位的minor-opcode
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

以下三种格式含 `o`（minor-opcode，6 位辅助操作码），minor-opcode 在 `ha[5:0]`：

- `orrr`：minor-opcode + 三个寄存器
- `orri`：minor-opcode + 两个寄存器 + 6 位立即数在 `hd[5:0]`
- `oiii`：minor-opcode + 18 位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]`（hb=高位6位, hc=中位6位, hd=低位6位）

SimRISC 提供四种固定数据位宽，通过指令名后缀 `.b`/`.w`/`.t`/`.o` 区分，分别对应 byte（8 位）、wyde（16 位）、tetra（32 位）、octa（64 位）。这四种位宽的指令分布在以下四个 minor-opcode 子表中：

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
| 0000-0xxx     | MISC-AMO             |                      |                      |                      |                      |                      |                      |                  |
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
| 0101-1xxx     |                      | add.si_riii_rd       | rela.si_riii_rb      | add.si_riii_rb       | cmp.ui_rrii_rd       | cmp.si_rrii_rd       | cs.eq_rrrr_rf        | cs.ne_rrrr_rf   |
| 0110-0xxx     | cs.n_rrrr_rd         | cs.n_rrrr_rf         | cs.z_rrrr_rd         | cs.z_rrrr_rf         | cs.p_rrrr_rd         | cs.p_rrrr_rf         | cs.eq_rrrr_rd        | cs.ne_rrrr_rd   |
| 0110-1xxx     | br.n_riii_rd         | br.nn_riii_rd        | br.z_riii_rd         | br.nz_riii_rd        | br.p_riii_rd         | br.np_riii_rd        | br.eq_rrii_rd        | br.ne_rrii_rd   |
| 0111-0xxx     | jump_iiii_rb         | jump_rrii_rb         | br.z_riii_rb         | br.nz_riii_rb        | call_iiii_ra         | call_rrii_ra         | ret_riii_ra          |                  |
| 0111-1xxx     |                      |                      | cfx2rd_crrr_cfx      | cfx2rc_crrr_cfx      | cfxld_crii_cfx       | cfxst_crii_cfx       | escape_ciii_cfx      | trap_ciii_cfx   |

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
| 100-xxx   | add.so_orrr_rb  |                 |               |               |               |               |               |               |
| 101-xxx   | sub.so_orrr_rb  | cmp.uo_orrr_rb  | cmp.uo_orrr_rd   | cmp.so_orrr_rd   | rd2rd_orri_rd    | rd2ra_orri_ra    | ra2rd_orri_ra    |               |
| 110-xxx   |                 |                 |               |               | rb2rb_orri_rb    | rd2rb_orri_rb    | rb2rd_orri_rb    |               |
| 111-xxx   | div.uo_orrr_rd     | div.so_orrr_rd     | rem.uo_orrr_rd   | rem.so_orrr_rd   |               | rd2rf_orri_rf    | rf2rd_orri_rf    |               |

### MISC-tetra指令编码

tetra 位宽（32 位）指令。指令名后缀 `.t` 表示 tetra 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               |               |               |               |               |
| 001-xxx   | and.t_orrr_rd    | or.t_orrr_rd     | xor.t_orrr_rd    | xnor.t_orrr_rd   |               |               |               |               |
| 010-xxx   | ext.ut_orrr_rd   | ext.st_orrr_rd   | shr.ut_orrr_rd   | shr.st_orrr_rd   | shl.ut_orrr_rd   |               |               |               |
| 011-xxx   | ext.ut_orri_rd   | ext.st_orri_rd   | shr.ut_orri_rd   | shr.st_orri_rd   | shl.ut_orri_rd   |               |               |               |
| 100-xxx   | add.ut_orrr_rd   | add.st_orrr_rd   |               |               |               |               |               |               |
| 101-xxx   | sub.ut_orrr_rd   | sub.st_orrr_rd   | cmp.ut_orrr_rd   | cmp.st_orrr_rd   |               |               |               |               |
| 110-xxx   | mul.ut_orrr_rd   | mul.st_orrr_rd   |               |               |               |               |               |               |
| 111-xxx   | div.ut_orrr_rd   | div.st_orrr_rd   | rem.ut_orrr_rd   | rem.st_orrr_rd   |               |               |               |               |

### MISC-wyde指令编码

wyde 位宽（16 位）指令。指令名后缀 `.w` 表示 wyde 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               |               |               |               |               |
| 001-xxx   | and.w_orrr_rd    | or.w_orrr_rd     | xor.w_orrr_rd    | xnor.w_orrr_rd   |               |               |               |               |
| 010-xxx   | ext.uw_orrr_rd   | ext.sw_orrr_rd   | shr.uw_orrr_rd   | shr.sw_orrr_rd   | shl.uw_orrr_rd   |               |               |               |
| 011-xxx   | ext.uw_orri_rd   | ext.sw_orri_rd   | shr.uw_orri_rd   | shr.sw_orri_rd   | shl.uw_orri_rd   |               |               |               |
| 100-xxx   | add.uw_orrr_rd   | add.sw_orrr_rd   |               |               |               |               |               |               |
| 101-xxx   | sub.uw_orrr_rd   | sub.sw_orrr_rd   | cmp.uw_orrr_rd   | cmp.sw_orrr_rd   |               |               |               |               |
| 110-xxx   | mul.uw_orrr_rd   | mul.sw_orrr_rd   |               |               |               |               |               |               |
| 111-xxx   | div.uw_orrr_rd   | div.sw_orrr_rd   | rem.uw_orrr_rd   | rem.sw_orrr_rd   |               |               |               |               |

### MISC-byte指令编码

byte 位宽（8 位）指令，覆盖移位、扩展、逻辑、算术、比较、乘除等操作。指令名后缀 `.b` 表示 byte 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               |               |               |               |               |
| 001-xxx   | and.b_orrr_rd    | or.b_orrr_rd     | xor.b_orrr_rd    | xnor.b_orrr_rd   |               |               |               |               |
| 010-xxx   | ext.ub_orrr_rd   | ext.sb_orrr_rd   | shr.ub_orrr_rd   | shr.sb_orrr_rd   | shl.ub_orrr_rd   |               |               |               |
| 011-xxx   | ext.ub_orri_rd   | ext.sb_orri_rd   | shr.ub_orri_rd   | shr.sb_orri_rd   | shl.ub_orri_rd   |               |               |               |
| 100-xxx   | add.ub_orrr_rd   | add.sb_orrr_rd   |               |               |               |               |               |               |
| 101-xxx   | sub.ub_orrr_rd   | sub.sb_orrr_rd   | cmp.ub_orrr_rd   | cmp.sb_orrr_rd   |               |               |               |               |
| 110-xxx   | mul.ub_orrr_rd   | mul.sb_orrr_rd   |               |               |               |               |               |               |
| 111-xxx   | div.ub_orrr_rd   | div.sb_orrr_rd   | rem.ub_orrr_rd   | rem.sb_orrr_rd   |               |               |               |               |

### MISC-RF指令编码

空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000     | xxx-001     | xxx-010     | xxx-011     | xxx-100     | xxx-101     | xxx-110     | xxx-111     |
| ---       | ---         | ---         | ---         | ---         | ---         | ---         | ---         | ---         |
| 000-xxx   | ftcls_orri_rf  | ft2fo_orri_rf  | ft2ft_orri_rf  |             |             |             | ftroot_orri_rf | ftlog_orri_rf  |
| 001-xxx   | focls_orri_rf  | fo2ft_orri_rf  | fo2fo_orri_rf  |             |             |             | foroot_orri_rf | folog_orri_rf  |
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
| `not.b` | `not.b rdHB, rdHC` | `xnor.b rdHB, rdHC, rd0` | 8 位按位取反 | SimRISC-10 §not 伪指令 |
| `not.w` | `not.w rdHB, rdHC` | `xnor.w rdHB, rdHC, rd0` | 16 位按位取反 | SimRISC-09 §not 伪指令 |
| `not.t` | `not.t rdHB, rdHC` | `xnor.t rdHB, rdHC, rd0` | 32 位按位取反 | SimRISC-08 §not 伪指令 |
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
