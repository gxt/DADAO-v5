# SimRISC指令系统

> **版本：0.5.1**

SimRISC名称有三重含义：

- 一是Simple RISC，顾名思义，其基础设计理念是“Simple is beautiful" + RISC
- 二是Simulated RISC，其设计初衷是基于教学目的，故完全基于模拟环境进行设计开发
- 三是Similar RISC，基于RISC而不局限于RISC，在很多设计想法上希望在RISC基础上进行探索和突破

## 指令设计

SimRISC中的每条指令都是四个字节，即32位。所有指令必须4字节对齐。取指时若 PC[1:0] ≠ 00，触发 IALIGN 异常。

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
- `c`：六位的cfxcode
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

以下三种格式含 `c`（cfxcode，6 位核芯功能扩展编码），cfxcode 始终在 `ha[5:0]`：

- `crrr`：cfxcode + 三个 6 位寄存器编号，cg 在 `hb`，rc 在 `hc`，rd 在 `hd`（cfx2rd/cfx2rc）
- `crii`：cfxcode + 6 位 rb 寄存器在 `hb` + 12 位立即数在 `hc[5:0]`+`hd[5:0]`（hc=高位, hd=低位，cfxld/cfxst）
- `ciii`：cfxcode + 18 位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]`（hb=高位, hc=中位, hd=低位，trap/escape）

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

为了支持浮点比较结果的判断，在浮点条件赋值指令中增加了两种条件判断：

| 助记符 | 条件 | 操作数个数 | 判断方法 |
| ---: | ---    | ---       | --- |
| `P1`  | 正数1   | 一个操作数 | 第0位为1，且[63..1]全为0      |
| `NP1` | 非正数1 | 一个操作数 | 第0位为0，或[63..1]不全为0    |

## SimRISC QFC

SimRISC 0.5.1版本的指令opcode布局如下。空白单元格表示 reserved（保留未分配），执行保留编码触发 UNDI 异常。

|           | xxxx-x000       | xxxx-x001       | xxxx-x010       | xxxx-x011       | xxxx-x100       | xxxx-x101       | xxxx-x110       | xxxx-x111     |
| ---       | ---             | ---             | ---             | ---             | ---             | ---             | ---             | ---           |
| 0000-0xxx | MISC-Norm       |                 |                 | MISC-RF         | MISC-byte       | MISC-wyde       | MISC-tetra      | MISC-octa     |
| 0000-1xxx |                 |                 |                 |                 |                 |                 |                 |               |
| 0001-0xxx |                 |                 |                 |                 |                 |                 |                 |               |
| 0001-1xxx | or.w-rd-rwii    | andn.w-rd-rwii  | set.zw-rd-rwii  | set.ow-rd-rwii  | or.w-rb-rwii    | andn.w-rb-rwii  | set.zw-rb-rwii  | set.w-rf-rwii |
| 0010-0xxx | add.uo-rd-rrrr  | add.so-rd-rrrr  | sub.uo-rd-rrrr  | sub.so-rd-rrrr  | mul.uo-rd-rrrr  | mul.so-rd-rrrr  | ftmadd-rrrr     | fomadd-rrrr   |
| 0010-1xxx | add.si-rd-rrii  | add.si-rb-rrii  | cmp.ui-rd-rrii  | cmp.si-rd-rrii  | rela.si-rb-riii |                 |                 |               |
| 0011-0xxx | cs.n-rd-rrrr    | cs.n-rf-rrrr    | cs.z-rd-rrrr    | cs.z-rf-rrrr    | cs.p-rd-rrrr    | cs.p-rf-rrrr    | cs.eq-rd-rrrr   | cs.ne-rd-rrrr |
| 0011-1xxx | br.n-riii       | br.nn-riii      | br.z-riii       | br.nz-riii      | br.p-riii       | br.np-riii      | br.eq-rrii      | br.ne-rrii    |
| 0100-0xxx | ld.ub-rd-rrii   | ld.uw-rd-rrii   | ld.ut-rd-rrii   | ld.sb-rd-rrii   | ld.sw-rd-rrii   | ld.st-rd-rrii   | ld.t-rf-rrii    | st.t-rf-rrii  |
| 0100-1xxx | st.b-rd-rrii    | st.w-rd-rrii    | st.t-rd-rrii    |                 |                 |                 |                 |               |
| 0101-0xxx | ld.o-rd-rrii    | st.o-rd-rrii    | ld.o-rb-rrii    | st.o-rb-rrii    | ld.o-ra-rrii    | st.o-ra-rrii    | ld.o-rf-rrii    | st.o-rf-rrii  |
| 0101-1xxx | ldm.ub-rd-rrri  | ldm.uw-rd-rrri  | ldm.ut-rd-rrri  | ldm.sb-rd-rrri  | ldm.sw-rd-rrri  | ldm.st-rd-rrri  | ldm.t-rf-rrri   | stm.t-rf-rrri |
| 0110-0xxx | stm.b-rd-rrri   | stm.w-rd-rrri   | stm.t-rd-rrri   |                 |                 |                 |                 |               |
| 0110-1xxx | ldm.o-rd-rrri   | stm.o-rd-rrri   | ldm.o-rb-rrri   | stm.o-rb-rrri   | ldm.o-ra-rrri   | stm.o-ra-rrri   | ldm.o-rf-rrri   | stm.o-rf-rrri |
| 0111-0xxx | jump-iiii       | jump-rrii       | call-iiii       | call-rrii       | ret-riii        |                 |                 | swym-iiii     |
| 0111-1xxx |                 |                 | cfx2rd-crrr     | cfx2rc-crrr     | cfxld-crii      | cfxst-crii      | trap-ciii       | escape-ciii   |

### MISC-Norm指令编码

空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000     | xxx-001     | xxx-010     | xxx-011     | xxx-100     | xxx-101     | xxx-110     | xxx-111     |
| ---       | ---         | ---         | ---         | ---         | ---         | ---         | ---         | ---         |
| 000-xxx   | illi-oiii   | fence-oiii  |             |             |             |             |             |             |
| 001-xxx   |             |             |             |             |             |             |             |             |
| 010-xxx   | lr_nn.o-orrr | lr_nr.o-orrr | lr_an.o-orrr | lr_ar.o-orrr |             |             |             |             |
| 011-xxx   | sc_nn.o-orrr | sc_nr.o-orrr | sc_an.o-orrr | sc_ar.o-orrr |             |             |             |             |
| 100-xxx   |             |             |             |             |             |             |             |             |
| 101-xxx   | rd2rd-orri  | rd2rb-orri  | rb2rd-orri  | rb2rb-orri  |             | cmp.uo-rb-orrr | add.so-rb-orrr | sub.so-rb-orrr |
| 110-xxx   |             | rd2rf-orri  | rf2rd-orri  | rf2rf-orri  |             |             | cs.p1-orrr   | cs.np1-orrr  |
| 111-xxx   |             | rd2ra-orri  | ra2rd-orri  |             |             |             |             |             |

### MISC-RF指令编码

空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000     | xxx-001     | xxx-010     | xxx-011     | xxx-100     | xxx-101     | xxx-110     | xxx-111     |
| ---       | ---         | ---         | ---         | ---         | ---         | ---         | ---         | ---         |
| 000-xxx   | ftcls-orri  | ft2fo-orri  |             |             |             |             | ftroot-orri | ftlog-orri  |
| 001-xxx   | focls-orri  | fo2ft-orri  |             |             |             |             | foroot-orri | folog-orri  |
| 010-xxx   | ftadd-orrr  | ftsub-orrr  | ftmul-orrr  | ftdiv-orrr  | ftrem-orrr  | ftsclb-orrr | ftsgnn-orrr | ftsgnj-orrr |
| 011-xxx   | foadd-orrr  | fosub-orrr  | fomul-orrr  | fodiv-orrr  | forem-orrr  | fosclb-orrr | fosgnn-orrr | fosgnj-orrr |
| 100-xxx   | ftqcmp-orrr | ftscmp-orrr |             |             |             |             |             |             |
| 101-xxx   | foqcmp-orrr | foscmp-orrr |             |             |             |             |             |             |
| 110-xxx   | ft2it-orri  | ft2io-orri  | ft2ut-orri  | ft2uo-orri  | it2ft-orri  | io2ft-orri  | ut2ft-orri  | uo2ft-orri  |
| 111-xxx   | fo2it-orri  | fo2io-orri  | fo2ut-orri  | fo2uo-orri  | it2fo-orri  | io2fo-orri  | ut2fo-orri  | uo2fo-orri  |

### MISC-byte指令编码

byte 位宽（8 位）指令，覆盖移位、扩展、逻辑、算术、比较、乘除等操作。指令名后缀 `.b` 表示 byte 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               | shl.ub-orrr   | shr.sb-orrr   | shr.ub-orrr   |               |
| 001-xxx   |               |               |               |               | shl.ub-orri   | shr.sb-orri   | shr.ub-orri   |               |
| 010-xxx   | ext.ub-orrr   | ext.sb-orrr   | ext.ub-orri   | ext.sb-orri   | and.b-orrr    | or.b-orrr    | xor.b-orrr    | xnor.b-orrr   |
| 011-xxx   |               |               |               |               |               |               |               |               |
| 100-xxx   | add.ub-orrr   | add.sb-orrr   | sub.ub-orrr   | sub.sb-orrr   | cmp.ub-orrr   | cmp.sb-orrr   |               |               |
| 101-xxx   | mul.ub-orrr   | mul.sb-orrr   |               |               | div.ub-orrr   | div.sb-orrr   | rem.ub-orrr   | rem.sb-orrr   |
| 110-xxx   |               |               |               |               |               |               |               |               |
| 111-xxx   |               |               |               |               |               |               |               |               |

### MISC-wyde指令编码

wyde 位宽（16 位）指令。指令名后缀 `.w` 表示 wyde 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               | shl.uw-orrr   | shr.sw-orrr   | shr.uw-orrr   |               |
| 001-xxx   |               |               |               |               | shl.uw-orri   | shr.sw-orri   | shr.uw-orri   |               |
| 010-xxx   | ext.uw-orrr   | ext.sw-orrr   | ext.uw-orri   | ext.sw-orri   | and.w-orrr    | or.w-orrr    | xor.w-orrr    | xnor.w-orrr   |
| 011-xxx   |               |               |               |               |               |               |               |               |
| 100-xxx   | add.uw-orrr   | add.sw-orrr   | sub.uw-orrr   | sub.sw-orrr   | cmp.uw-orrr   | cmp.sw-orrr   |               |               |
| 101-xxx   | mul.uw-orrr   | mul.sw-orrr   |               |               | div.uw-orrr   | div.sw-orrr   | rem.uw-orrr   | rem.sw-orrr   |
| 110-xxx   |               |               |               |               |               |               |               |               |
| 111-xxx   |               |               |               |               |               |               |               |               |

### MISC-tetra指令编码

tetra 位宽（32 位）指令。指令名后缀 `.t` 表示 tetra 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               | shl.ut-orrr   | shr.st-orrr   | shr.ut-orrr   |               |
| 001-xxx   |               |               |               |               | shl.ut-orri   | shr.st-orri   | shr.ut-orri   |               |
| 010-xxx   | ext.ut-orrr   | ext.st-orrr   | ext.ut-orri   | ext.st-orri   | and.t-orrr    | or.t-orrr    | xor.t-orrr    | xnor.t-orrr   |
| 011-xxx   |               |               |               |               |               |               |               |               |
| 100-xxx   | add.ut-orrr   | add.st-orrr   | sub.ut-orrr   | sub.st-orrr   | cmp.ut-orrr   | cmp.st-orrr   |               |               |
| 101-xxx   | mul.ut-orrr   | mul.st-orrr   |               |               | div.ut-orrr   | div.st-orrr   | rem.ut-orrr   | rem.st-orrr   |
| 110-xxx   |               |               |               |               |               |               |               |               |
| 111-xxx   |               |               |               |               |               |               |               |               |

### MISC-octa指令编码

octa 位宽（64 位）指令。指令名后缀 `.o` 表示 octa 位宽。
空白单元格为 reserved，执行保留编码触发 UNDI 异常。

|           | xxx-000       | xxx-001       | xxx-010       | xxx-011       | xxx-100       | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 000-xxx   |               |               |               |               | shl.uo-orrr   | shr.so-orrr   | shr.uo-orrr   |               |
| 001-xxx   |               |               |               |               | shl.uo-orri   | shr.so-orri   | shr.uo-orri   |               |
| 010-xxx   | ext.uo-orrr   | ext.so-orrr   | ext.uo-orri   | ext.so-orri   | and.o-orrr    | or.o-orrr    | xor.o-orrr    | xnor.o-orrr   |
| 011-xxx   |               |               |               |               |               |               |               |               |
| 100-xxx   |               |               |               |               | cmp.uo-orrr   | cmp.so-orrr   |               |               |
| 101-xxx   |               |               |               |               | div.uo-orrr   | div.so-orrr   | rem.uo-orrr   | rem.so-orrr   |
| 110-xxx   |               |               |               |               |               |               |               |               |
| 111-xxx   |               |               |               |               |               |               |               |               |
