# SimRISC指令系统

> **版本：0.4.1**

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
- `r`：寄存器
- `i`：立即数（立即数域需要区分有符号数和无符号数）
- `w`：头两位为wyde-position，后四位为立即数
- `z`：未使用，应为零，（SBZ：Should Be Zero）

SimRISC没有在编码上进行过多的拆分，操作数类型简单而规整，用4个字母可以表示某条指令的操作数类型，其中也隐含了操作数位置和操作数个数：

- `iiii`：一个操作数，24位立即数
- `oiii`：一个操作数，18位立即数
- `orii`：两个操作数，其中一个寄存器，一个12位立即数
- `orri`：三个操作数，其中两个寄存器，一个6位立即数
- `orrr`：三个操作数，都是寄存器（ha 为 minor-opcode，目的寄存器在 hb；lro 的 hb 固定为 rd0，汇编仅需 hc/hd 两参数）
- `rrrr`：四个操作数，都是寄存器
- `rrri`：四个操作数，其中三个寄存器，一个6位立即数
- `rrii`：三个操作数，其中两个寄存器，一个12位立即数
- `riii`：两个操作数，其中一个寄存器，一个18位立即数
- `rwii`：一个寄存器，一个 wyde-position，和一个拆分为两段的 16 位无符号立即数
  - wyde-position 在 `hb[5:4]`，编码：`00=w0, 01=w1, 10=w2, 11=w3`
  - immu16 高 4 位在 `hb[3:0]`，中 6 位在 `hc[5:0]`，低 6 位在 `hd[5:0]`（hb→hc→hd 高位到低位）

以下三种格式含 `c`（cfxcode，6 位核芯功能扩展编码），cfxcode 始终在 `ha[5:0]`：

- `ciii`：cfxcode + 18 位立即数在 `hb[5:0]`+`hc[5:0]`+`hd[5:0]`（hb=高位, hc=中位, hd=低位，trap/escape）
- `crrr`：cfxcode + 三个 6 位寄存器编号，cg 在 `hb`，rc 在 `hc`，rd 在 `hd`（cfx2rd/cfx2rc）
- `crii`：cfxcode + 6 位 rb 寄存器在 `hb` + 12 位立即数在 `hc[5:0]`+`hd[5:0]`（hc=高位, hd=低位，cfxld/cfxst）

> 多域拼接立即数规则：hb→hc→hd 按高位到低位依次拼接。12 位立即数（rrii/orii/crii）由 hc（高 6 位）和 hd（低 6 位）组成。18 位立即数（riii/ciii/oiii）由 hb（高 6 位）、hc（中 6 位）、hd（低 6 位）组成。orri 格式的 6 位立即数在 `hd[5:0]`。

关于目的寄存器的位置，SimRISC中通常采用指令域中的第一个寄存器为目的寄存器。
将目的操作数放在前面，从而可以把立即数放在最后，并且立即数通常为最后一个源操作数，可以直观的从二进制上判断出立即数。
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

SimRISC 0.4.1版本的指令opcode布局如下。空白单元格表示 reserved（保留未分配），执行保留编码触发 UNDI 异常。

|               | xxxx-x000     | xxxx-x001     | xxxx-x010     | xxxx-x011     | xxxx-x100     | xxxx-x101     | xxxx-x110     | xxxx-x111     |
| ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           | ---           |
| 0000-0xxx     |               |               |               |               |               |               |               |               |
| 0000-1xxx     |               |               |               |               |               |               |               |               |
| 0001-0xxx     | MISC-Norm     |               | cmps-rrii     | cmpu-rrii     | orw-rwii      | andnw-rwii    | setzw-rwii    | setow-rwii    |
| 0001-1xxx     |               | addi-rrii     | add-rrrr      | sub-rrrr      | muls-rrrr     | mulu-rrrr     | divs-rrrr     | divu-rrrr     |
| 0010-0xxx     | csn-rrrr      | csn-rf-rrrr   | csz-rrrr      | csz-rf-rrrr   | csp-rrrr      | csp-rf-rrrr   | cseq-rrrr     | csne-rrrr     |
| 0010-1xxx     | brn-riii      | brnn-riii     | brz-riii      | brnz-riii     | brp-riii      | brnp-riii     | breq-rrii     | brne-rrii     |
| 0011-0xxx     | ldbs-rrii     | ldws-rrii     | ldts-rrii     | ldo-rrii      | ldmbs-rrri    | ldmws-rrri    | ldmts-rrri    | ldmo-rrri     |
| 0011-1xxx     | stb-rrii      | stw-rrii      | stt-rrii      | sto-rrii      | stmb-rrri     | stmw-rrri     | stmt-rrri     | stmo-rrri     |
| 0100-0xxx     | ldbu-rrii     | ldwu-rrii     | ldtu-rrii     | ldo-rb-rrii   | ldmbu-rrri    | ldmwu-rrri    | ldmtu-rrri    | ldmo-rb-rrri  |
| 0100-1xxx     | rela-riii     | addi-rb-rrii  |               | sto-rb-rrii   | orw-rb-rwii   | andnw-rb-rwii | setzw-rb-rwii | stmo-rb-rrri  |
| 0101-0xxx     | MISC-RF       |               | ldt-rf-rrii   | ldo-rf-rrii   | setw-rwii     |               | ldmt-rf-rrri  | ldmo-rf-rrri  |
| 0101-1xxx     | ftmadd-rrrr   | fomadd-rrrr   | stt-rf-rrii   | sto-rf-rrii   |               |               | stmt-rf-rrri  | stmo-rf-rrri  |
| 0110-0xxx     |               |               |               |               | jump-iiii     | jump-rrii     |               | ldmo-ra-rrri  |
| 0110-1xxx     |               |               |               |               | call-iiii     | call-rrii     | ret-riii      | stmo-ra-rrri  |
| 0111-0xxx     | MISC-AMO      |               | cfx2rd-crrr   | cfx2rc-crrr   | cfxld-crii    | cfxst-crii    | trap-ciii     | escape-ciii   |
| 0111-1xxx     |               |               |               |               |               |               |               |               |

### MISC-Norm指令编码

空白单元格为 reserved。

|           | xxx-000   | xxx-001   | xxx-010   | xxx-011   | xxx-100   | xxx-101       | xxx-110       | xxx-111       |
| ---       | ---       | ---       | ---       | ---       | ---       | ---           | ---           | ---           |
| 000-xxx   | swym-oiii |           |           |           |           |               |               |               |
| 001-xxx   | and-orrr  | orr-orrr  | xor-orrr  | xnor-orrr |           |               |               |               |
| 010-xxx   |           | shlu-orrr | shrs-orrr | shru-orrr | exts-orrr | extz-orrr     |               |               |
| 011-xxx   |           | shlu-orri | shrs-orri | shru-orri | exts-orri | extz-orri     |               |               |
| 100-xxx   |           |           |           |           | cmps-orrr | cmpu-orrr     |               |               |
| 101-xxx   | rd2rd-orri| rd2rb-orri| rb2rd-orri| rb2rb-orri|           | cmp-rb-orrr   | add-rb-orrr   | sub-rb-orrr   |
| 110-xxx   |           | rd2rf-orri| rf2rd-orri| rf2rf-orri|           |               | csp1-orrr     | csnp1-orrr    |
| 111-xxx   |           | rd2ra-orri| ra2rd-orri|           |           |               |               | unimp-oiii    |

### MISC-RF指令编码

空白单元格为 reserved。

|           | xxx-000   | xxx-001   | xxx-010   | xxx-011   | xxx-100   | xxx-101   | xxx-110   | xxx-111       |
| ---       | ---       | ---       | ---       | ---       | ---       | ---       | ---       | ---           |
| 000-xxx   | ftcls-orri | ft2fo-orri |           |           |           |           | ftroot-orri| ftlog-orri   |
| 001-xxx   | focls-orri | fo2ft-orri |           |           |           |           | foroot-orri| folog-orri   |
| 010-xxx   | ftadd-orrr | ftsub-orrr | ftmul-orrr | ftdiv-orrr | ftrem-orrr | ftsclb-orrr| ftsgnn-orrr| ftsgnj-orrr  |
| 011-xxx   | foadd-orrr | fosub-orrr | fomul-orrr | fodiv-orrr | forem-orrr | fosclb-orrr| fosgnn-orrr| fosgnj-orrr  |
| 100-xxx   | ftqcmp-orrr| ftscmp-orrr|           |           |           |           |           |               |
| 101-xxx   | foqcmp-orrr| foscmp-orrr|           |           |           |           |           |               |
| 110-xxx   | ft2it-orri | ft2io-orri | ft2ut-orri | ft2uo-orri | it2ft-orri | io2ft-orri | ut2ft-orri | uo2ft-orri   |
| 111-xxx   | fo2it-orri | fo2io-orri | fo2ut-orri | fo2uo-orri | it2fo-orri | io2fo-orri | ut2fo-orri | uo2fo-orri   |

### MISC-AMO指令编码

空白单元格为 reserved。

|           | xxx-000   | xxx-001   | xxx-010   | xxx-011   | xxx-100   | xxx-101   | xxx-110   | xxx-111       |
| ---       | ---       | ---       | ---       | ---       | ---       | ---       | ---       | ---           |
| 000-xxx   | fence-oiii|           |           |           |           |           |           |               |
| 001-xxx   |           |           |           |           |           |           |           |               |
| 010-xxx   |           |           |           |           |           |           |           |               |
| 011-xxx   |           |           |           |           |           |           |           |               |
| 100-xxx   | lro_nn-orrr| lro_nr-orrr| lro_an-orrr| lro_ar-orrr|           |           |           |               |
| 101-xxx   | sco_nn-orrr| sco_nr-orrr| sco_an-orrr| sco_ar-orrr|           |           |           |               |
| 110-xxx   |           |           |           |           |           |           |           |               |
| 111-xxx   |           |           |           |           |           |           |           |               |
