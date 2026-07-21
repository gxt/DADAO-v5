# SimRISC ISA 规范合约

> **版本：0.5.3** [SimRISC-00 §版本]

---

## §1 寄存器模型

### §1.1 寄存器组

DADAO 提供 4 组用户可见寄存器，每组 64 个，每个寄存器 64 位（机器字长）。[SimRISC-00 §寄存器]

| 组名 | 范围 | 用途 |
|------|------|------|
| 数据寄存器 (RD) | rd0–rd63 | 通用运算 |
| 基址寄存器 (RB) | rb0–rb63 | 地址计算 |
| 浮点寄存器 (RF) | rf0–rf63 | 浮点运算 |
| 返回地址栈 (RA) | ra0–ra63 | 函数调用/返回 |

### §1.2 寄存器编号编码

每组寄存器需 6 位编码（ha/hb/hc/hd[5:0]）。[SimRISC-00 §指令域说明]

### §1.3 特殊寄存器

#### §1.3.1 rd0

`rd0` 固定为 0，只读。[SimRISC-00 §数据寄存器]

- 作为目的寄存器时行为取决于指令格式：
  - rrrr 双目指令（add.uo/add.so/sub.uo/sub.so/mul.uo/mul.so）允许其中一个为 rd0（丢弃对应半结果），但不能同时为 rd0，也不能为同一非 rd0 寄存器 [SimRISC-01 §rd0 为目的寄存器约定]
  - `ret rd0, 0` 允许（无需设置返回值）[SimRISC-02 §函数返回]
  - 其余指令目的为 rd0 时触发 ILLI 异常 [SimRISC-01 §rd0 为目的寄存器约定]

#### §1.3.2 rb0

`rb0` 为程序计数器（PC），只读。任何指令以 rb0 为显式目的时触发 ILLI 异常。[SimRISC-02 §rb0 为目的寄存器约定]

- `rb0[63:48]` 恒为 0 [SimRISC-00 §基址寄存器]
- 硬件复位后 rb0 初值为 `cfx_power_hypv_excp_vector` [SimRISC-00 §基址寄存器]

#### §1.3.3 rf0

`rf0` 为浮点状态寄存器（FCSR）。[SimRISC-00 §浮点状态寄存器]

- 浮点运算指令的目的或任一源操作数为 rf0 时触发 ILLI 异常 [SimRISC-03 §rf0 为目的寄存器约定]
- rf ld/st 中 rf0 为目的时允许，写只读位时静默忽略，rw 位正常写入 [SimRISC-03 §rf0 为目的寄存器约定]

rf0 字段定义：[SimRISC-00 §浮点状态寄存器]

| 位域 | 属性 | 含义 |
|------|------|------|
| [63:51] | 只读 | fo 格式 Quiet NaN（0x7FF8_0000_0000_0000 的高 13 位） |
| [50:32] | SBZ | 应为零 |
| [31:22] | 只读 | ft 格式 Quiet NaN（0x7FC0_0000 的高 10 位） |
| [21:18] | SBZ | 应为零 |
| [17:16] | R/W | 舍入模式（Rounding Mode） |
| [15:5] | SBZ | 应为零 |
| [4:0] | R/W | 异常状态（Accrued Exception） |

舍入模式编码：[SimRISC-00 §浮点状态寄存器]

| 编码 | 助记符 | 含义 |
|------|--------|------|
| 00 | RNE | 向最近舍入，平局取偶 |
| 01 | RTZ | 向零舍入 |
| 10 | RDN | 向负无穷舍入 |
| 11 | RUP | 向正无穷舍入 |

异常状态位：[SimRISC-00 §浮点状态寄存器]

| 位 | 助记符 | 含义 |
|----|--------|------|
| 0 | NV | Invalid Operation |
| 1 | DZ | Divide by Zero |
| 2 | OF | Overflow |
| 3 | UF | Underflow |
| 4 | NX | Inexact |

浮点指令执行后，异常状态位（NV/DZ/OF/UF/NX）由硬件按 IEEE 754 标准设置到 rf0[4:0]。软件可通过读取 rf0 检查异常状态，并根据需要进行后续处理。浮点指令不会触发异常，始终按 IEEE 754 标准返回结果（如 NaN、Inf 等）。[SimRISC-00 §浮点状态寄存器]

#### §1.3.4 ra0–ra63

返回地址栈（Return Address Stack），后入先出。[SimRISC-00 §返回地址栈]

| 寄存器 | 高 16 位 | 低 48 位 |
|--------|----------|----------|
| ra0 | MemRAS 引用计数（压栈 +1，弹栈 -1，初始 0） | MemRAS 指针（0 = 仅 RegRAS） |
| ra1–ra62 | 返回地址引用计数（>0 有效，=0 无效） | 返回地址 |
| ra63 | 返回地址引用计数（>0 有效，=0 无效） | 当前返回地址（RegRAS 栈顶） |

- ra1–ra63 构成 RegRAS，ra63 为栈顶 [SimRISC-00 §返回地址栈]
- ra0 低 48 位为 0 时仅 RegRAS，最多 63 个返回地址；非 0 时存在 MemRAS [SimRISC-00 §返回地址栈]
- 异常进入和退出不改变 ra0–ra63 的内容 [SimRISC-00 §返回地址栈]

### §1.4 数据表示

基础数据类型：[SimRISC-00 §数据表示]

| 术语 | 缩写 | 位数 | 字节数 |
|------|------|------|--------|
| byte | b | 8 | 1 |
| wyde | w | 16 | 2 |
| tetra | t | 32 | 4 |
| octa | o | 64 | 8 |

浮点格式符合 IEEE 754 标准。[SimRISC-00 §原始数据类型]

### §1.5 存储模型

- 64 位地址空间，有效虚拟地址为 48 位 [SimRISC-00 §存储模型]
- 高 16 位（bits[63:48]）在地址计算时被硬件忽略 [SimRISC-00 §存储模型]
- 指令和数据均采用大端序 [SimRISC-00 §指令设计]

---

## §2 指令编码

### §2.1 指令格式

所有指令均为 32 位（4 字节），必须 4 字节对齐。取指时若 PC[1:0] ≠ 00，触发 IALIGN 异常。[SimRISC-00 §指令设计]

指令字采用大端序存储：bits[31:24] 在最低地址，bits[7:0] 在最高地址。[SimRISC-00 §指令设计]

指令分解为 5 个域：op[7:0] / ha[5:0] / hb[5:0] / hc[5:0] / hd[5:0]。[SimRISC-00 §指令域说明]

- op：操作码（major-opcode），指明指令功能和分类 [SimRISC-00 §指令域说明]
- ha/hb/hc/hd：操作数，通过不同寻址方式组合 [SimRISC-00 §指令域说明]
- 某些情况下 ha 或 ha+hb 作为 minor-opcode [SimRISC-00 §指令域说明]

### §2.2 操作数格式

操作数类型用 4 个字母表示：[SimRISC-00 §指令域说明]

| 格式 | 含义 | 立即数位置 |
|------|------|-----------|
| rrrr | 四个寄存器 | 无 |
| rrri | 三寄存器 + 6 位立即数 | hd[5:0] |
| rrii | 两寄存器 + 12 位立即数 | hc[5:0]+hd[5:0]（hc=高, hd=低） |
| riii | 一寄存器 + 18 位立即数 | hb[5:0]+hc[5:0]+hd[5:0]（hb=高, hc=中, hd=低） |
| iiii | 24 位立即数 | ha[5:0]+hb[5:0]+hc[5:0]+hd[5:0] |
| rwii | 一寄存器 + wyde-position + 16 位无符号立即数 | hb[5:4]=wp, hb[3:0]+hc[5:0]+hd[5:0]=immu16 |
| orrr | minor-opcode + 三寄存器 | ha[5:0]=minor-opcode |
| orri | minor-opcode + 两寄存器 + 6 位立即数 | ha[5:0]=minor-opcode, hd[5:0]=immu6 |
| oiii | minor-opcode + 18 位立即数 | ha[5:0]=minor-opcode, hb+hc+hd=immu18 |
| crrr | cfxcode + 三寄存器 | ha[5:0]=cfxcode |
| crii | cfxcode + 一寄存器 + 12 位立即数 | ha[5:0]=cfxcode, hb[5:0]=rb, hc+hd=immu12 |
| ciii | cfxcode + 18 位立即数 | ha[5:0]=cfxcode, hb+hc+hd=immu18 |

### §2.3 Wyde-Position 编码

rwii 格式中 hb[5:4] 指定 wyde 在 64 位数据中的位置：[SimRISC-00 §指令域说明]

| 编码 | 位置 | 对应位域 |
|------|------|---------|
| 00 | wp0 | bits[15:0]（LSW） |
| 01 | wp1 | bits[31:16] |
| 10 | wp2 | bits[47:32] |
| 11 | wp3 | bits[63:48]（MSW） |

### §2.4 数据位宽后缀

四种固定数据位宽通过指令名后缀区分：[SimRISC-00 §指令域说明]

| 后缀 | 位宽 |
|------|------|
| .b | byte（8 位） |
| .w | wyde（16 位） |
| .t | tetra（32 位） |
| .o | octa（64 位） |

有符号/无符号区分的指令后缀扩展为 .ub/.sb、.uw/.sw、.ut/.st、.uo/.so。[SimRISC-00 §指令域说明]

### §2.5 操作数顺序约定

SimRISC 通常将目的操作数放在最前面，然后是寄存器源操作数，立即数放在最后。[SimRISC-00 §指令域说明]

---

## §3 标量整数指令

### §3.1 算术运算

#### §3.1.1 加减法（128 位结果，rrrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| add.uo rdha, rdhb, rdhc, rdhd | ZX 至 128 位，rdha:rdhb = rdhc + rdhd，rdha 为进位 | [SimRISC-01 §加减操作] |
| add.so rdha, rdhb, rdhc, rdhd | SX 至 128 位，rdha:rdhb = rdhc + rdhd，rdha 为高 64 位 | [SimRISC-01 §加减操作] |
| sub.uo rdha, rdhb, rdhc, rdhd | ZX 至 128 位，rdha:rdhb = rdhc - rdhd，rdha 为借位 | [SimRISC-01 §加减操作] |
| sub.so rdha, rdhb, rdhc, rdhd | SX 至 128 位，rdha:rdhb = rdhc - rdhd，rdha 为高 64 位 | [SimRISC-01 §加减操作] |

异常条件：[SimRISC-01 §加减操作]
- rdha 和 rdhb 同时为 rd0 → ILLI
- rdha = rdhb 且非 rd0 → ILLI
- 硬件先读全部源操作数再写结果，源被覆盖前其值已捕获

#### §3.1.2 加减法（固定位宽，orrr 格式）

结果仅保留 size 位宽，高位按符号类型填充。[SimRISC-01 §加减操作]

| 指令 | 位宽 | 高位填充 |
|------|------|---------|
| add.ub/sub.ub | 8 位 | 零扩展 |
| add.sb/sub.sb | 8 位 | 符号扩展 |
| add.uw/sub.uw | 16 位 | 零扩展 |
| add.sw/sub.sw | 16 位 | 符号扩展 |
| add.ut/sub.ut | 32 位 | 零扩展 |
| add.st/sub.st | 32 位 | 符号扩展 |

异常条件：rdhb 为 rd0 → ILLI。[SimRISC-01 §加减操作]

#### §3.1.3 自增自减（riii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| add.si rdha, imms18 | rdha = rdha + sign_extend(imms18)，全 64 位运算 | [SimRISC-01 §自增自减] |

立即数为 18 位有符号数，符号扩展后与寄存器执行加法，结果写回同一寄存器。[SimRISC-01 §自增自减]

#### §3.1.4 乘法（rrrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| mul.uo rdha, rdhb, rdhc, rdhd | 无符号乘法，rdha:rdhb = rdhc × rdhd（128 位结果） | [SimRISC-01 §乘除操作] |
| mul.so rdha, rdhb, rdhc, rdhd | 有符号乘法，rdha:rdhb = rdhc × rdhd（128 位结果） | [SimRISC-01 §乘除操作] |

异常条件：同 add/sub（rdha/rdhb 不能同时为 rd0，不能为同一非 rd0 寄存器）。[SimRISC-01 §乘除操作]

#### §3.1.5 乘除余（固定位宽，orrr 格式）

| 指令 | 位宽 | 来源 |
|------|------|------|
| mul.ub/mul.sb | 8 位 | [SimRISC-01 §乘除操作] |
| mul.uw/mul.sw | 16 位 | [SimRISC-01 §乘除操作] |
| mul.ut/mul.st | 32 位 | [SimRISC-01 §乘除操作] |
| div.ub/div.sb | 8 位 | [SimRISC-01 §乘除操作] |
| div.uw/div.sw | 16 位 | [SimRISC-01 §乘除操作] |
| div.ut/div.st | 32 位 | [SimRISC-01 §乘除操作] |
| div.uo/div.so | 64 位 | [SimRISC-01 §乘除操作] |
| rem.ub/rem.sb | 8 位 | [SimRISC-01 §乘除操作] |
| rem.uw/rem.sw | 16 位 | [SimRISC-01 §乘除操作] |
| rem.ut/rem.st | 32 位 | [SimRISC-01 §乘除操作] |
| rem.uo/rem.so | 64 位 | [SimRISC-01 §乘除操作] |

异常条件：[SimRISC-01 §乘除操作]
- rdhb 为 rd0 → ILLI
- 除数为零 → ILLI
- div.s 中 INT_MIN ÷ −1（各 size 对应值）→ ILLI
- 截断方向：div.s/rem.s 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号
- fault 时目的寄存器未写入（精确异常）

### §3.2 比较操作

#### §3.2.1 立即数比较（rrii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| cmp.si rdha, rdhb, imms12 | 有符号比较，rdha = sign(cmp(rdhb, sign_extend(imms12))) | [SimRISC-01 §比较操作] |
| cmp.ui rdha, rdhb, immu12 | 无符号比较，rdha = sign(cmp(rdhb, zero_extend(immu12))) | [SimRISC-01 §比较操作] |

比较结果：小于 → −1，等于 → 0，大于 → 1，写入目的寄存器全 64 位。[SimRISC-01 §比较操作]

#### §3.2.2 寄存器比较（固定位宽，orrr 格式）

源操作数按 size 截断后比较，结果（−1/0/1）写入目的寄存器全 64 位。[SimRISC-01 §比较操作]

| 指令 | 位宽 | 比较范围 |
|------|------|---------|
| cmp.ub/cmp.sb | 8 位 | bits[7:0] |
| cmp.uw/cmp.sw | 16 位 | bits[15:0] |
| cmp.ut/cmp.st | 32 位 | bits[31:0] |
| cmp.uo/cmp.so | 64 位 | bits[63:0] |

异常条件：rdhb 为 rd0 → ILLI。[SimRISC-01 §比较操作]

### §3.3 逻辑运算（固定位宽，orrr 格式）

仅 size 范围内的低位参与运算，高位保持目的寄存器原有值不变。[SimRISC-01 §逻辑运算]

| 指令 | 位宽 | 运算范围 |
|------|------|---------|
| and.b/or.b/xor.b/xnor.b | 8 位 | bits[7:0]，bits[63:8] 不变 |
| and.w/or.w/xor.w/xnor.w | 16 位 | bits[15:0]，bits[63:16] 不变 |
| and.t/or.t/xor.t/xnor.t | 32 位 | bits[31:0]，bits[63:32] 不变 |
| and.o/or.o/xor.o/xnor.o | 64 位 | bits[63:0] 全部参与 |

运算规则：[SimRISC-01 §逻辑运算]
- and：全一为一，有零为零
- or：全零为零，有一为一
- xor：相异为一，相同为零
- xnor：相同为一，相异为零

### §3.4 位操作

#### §3.4.1 移位（orrr/orri 格式）

shl 为左移，shr 为右移。u=逻辑（零扩展），s=算术（符号扩展）。[SimRISC-01 §位操作指令]

| 指令 | N | 有效 shamt 范围 |
|------|---|----------------|
| shl.ub/shr.ub/shr.sb | 7 | 0–7 |
| shl.uw/shr.uw/shr.sw | 15 | 0–15 |
| shl.ut/shr.ut/shr.st | 31 | 0–31 |
| shl.uo/shr.uo/shr.so | 63 | 0–63 |

- shl.u: rdhb[N:0] = (rdhc[N:0] << shamt)，低位补零 [SimRISC-01 §位操作指令]
- shr.u: rdhb[N:0] = (rdhc[N:0] >> shamt)，高位补零 [SimRISC-01 §位操作指令]
- shr.s: rdhb[N:0] = (rdhc[N:0] >> shamt) with sign(N)，高位补符号位 [SimRISC-01 §位操作指令]
- rdhb[63:N+1] = rdhb[63:N+1]，高位不变 [SimRISC-01 §位操作指令]

立即数形式（orri）：shamt 取 immu6 的低位。[SimRISC-01 §位操作指令]

异常条件：shamt > N → ILLI。[SimRISC-01 §位操作指令]

#### §3.4.2 符号/零扩展（orrr/orri 格式）

| 指令 | N | 约束 | 来源 |
|------|---|------|------|
| ext.ub/ext.sb | 7 | hd ≤ 7 | [SimRISC-01 §位操作指令] |
| ext.uw/ext.sw | 15 | hd ≤ 15 | [SimRISC-01 §位操作指令] |
| ext.ut/ext.st | 31 | hd ≤ 31 | [SimRISC-01 §位操作指令] |
| ext.uo/ext.so | 63 | hd ≤ 63 | [SimRISC-01 §位操作指令] |

语义：[SimRISC-01 §位操作指令]
- rdhb[hd:0] = rdhc[hd:0]（复制源低位）
- rdhb[N:hd+1] = sign/zero_extend(rdhc[hd])（扩展）
- rdhb[63:N+1] = rdhb[63:N+1]（高位不变）

异常条件：hd > N → ILLI。[SimRISC-01 §位操作指令]

### §3.5 条件赋值

#### §3.5.1 单值条件赋值（rrrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| cs.n rdha, rdhb, rdhc, rdhd | if (rdha < 0) rdhb = rdhc else rdhb = rdhd | [SimRISC-01 §条件赋值] |
| cs.z rdha, rdhb, rdhc, rdhd | if (rdha == 0) rdhb = rdhc else rdhb = rdhd | [SimRISC-01 §条件赋值] |
| cs.p rdha, rdhb, rdhc, rdhd | if (rdha > 0) rdhb = rdhc else rdhb = rdhd | [SimRISC-01 §条件赋值] |

#### §3.5.2 双值条件赋值（rrrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| cs.eq rdha, rdhb, rdhc, rdhd | if (rdha == rdhb) rdhc = rdhd | [SimRISC-01 §条件赋值] |
| cs.ne rdha, rdhb, rdhc, rdhd | if (rdha != rdhb) rdhc = rdhd | [SimRISC-01 §条件赋值] |

### §3.6 立即数设置（rwii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| set.ow rdha, wpN, immu16 | rdha[wyde(wpN)] = immu16，其余 48 位置 1 | [SimRISC-01 §立即数常数赋值] |
| set.zw rdha, wpN, immu16 | rdha[wyde(wpN)] = immu16，其余 48 位清 0 | [SimRISC-01 §立即数常数赋值] |
| or.w rdha, wpN, immu16 | rdha[wyde(wpN)] = rdha[wyde(wpN)] \| immu16，其余不变 | [SimRISC-01 §立即数常数赋值] |
| andn.w rdha, wpN, immu16 | rdha[wyde(wpN)] = rdha[wyde(wpN)] & ~immu16，其余不变 | [SimRISC-01 §立即数常数赋值] |

注意：`or.w` 同时是 MISC-wyde 表的三寄存器逻辑 OR 指令，汇编器按操作数格式区分。[SimRISC-01 §立即数常数赋值]

### §3.7 块赋值（orri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| rd2rd rdhb, rdhc, immu6 | 将 rdhc 开始的 immu6 个寄存器复制到 rdhb 开始的 immu6 个寄存器 | [SimRISC-01 §寄存器组之间块赋值] |

异常条件：[SimRISC-01 §寄存器组之间块赋值]
- immu6 = 0 → ILLI
- rdhb 为 rd0 → ILLI
- rdhb + immu6 > 64 → ILLI
- rdhc + immu6 > 64 → ILLI
- 源和目的可重叠，硬件按序号递增逐对处理，每对先读后写

### §3.8 伪指令（标量整数）

| 伪指令 | 展开形式 | 来源 |
|--------|----------|------|
| not.b rdhb, rdhc | xnor.b rdhb, rdhc, rd0 | [SimRISC-01 §not 伪指令] |
| not.w rdhb, rdhc | xnor.w rdhb, rdhc, rd0 | [SimRISC-01 §not 伪指令] |
| not.t rdhb, rdhc | xnor.t rdhb, rdhc, rd0 | [SimRISC-01 §not 伪指令] |
| not.o rdhb, rdhc | xnor.o rdhb, rdhc, rd0 | [SimRISC-01 §not 伪指令] |
| neg.b rdhb, rdhc | sub.sb rdhb, rd0, rdhc | [SimRISC-01 §neg 伪指令] |
| neg.w rdhb, rdhc | sub.sw rdhb, rd0, rdhc | [SimRISC-01 §neg 伪指令] |
| neg.t rdhb, rdhc | sub.st rdhb, rd0, rdhc | [SimRISC-01 §neg 伪指令] |
| neg.o rdhb, rdhc | sub.so rd0, rdhb, rd0, rdhc | [SimRISC-01 §neg 伪指令] |
| set.rd rdxx, imm64 | set.zw/set.ow + or.w/andn.w（1–4 条） | [SimRISC-01 §set.rd 伪指令] |
| set.rd rdxx, rs | rb2rd/rf2rd/ra2rd/rd2rd | [SimRISC-01 §set.rd 伪指令] |

---

## §4 地址/内存指令

### §4.1 存取 RD 寄存器

#### §4.1.1 单 load/store（rrii 格式）

| 指令 | 语义 | 对齐要求 | 来源 |
|------|------|---------|------|
| ld.sb rdha, rbhb, imms12 | rdha = sign_extend(mem8[rbhb + imms12]) | 无 | [SimRISC-01 §存取RD寄存器] |
| ld.ub rdha, rbhb, imms12 | rdha = zero_extend(mem8[rbhb + imms12]) | 无 | [SimRISC-01 §存取RD寄存器] |
| ld.sw rdha, rbhb, imms12 | rdha = sign_extend(mem16[rbhb + imms12]) | 2 字节 | [SimRISC-01 §存取RD寄存器] |
| ld.uw rdha, rbhb, imms12 | rdha = zero_extend(mem16[rbhb + imms12]) | 2 字节 | [SimRISC-01 §存取RD寄存器] |
| ld.st rdha, rbhb, imms12 | rdha = sign_extend(mem32[rbhb + imms12]) | 4 字节 | [SimRISC-01 §存取RD寄存器] |
| ld.ut rdha, rbhb, imms12 | rdha = zero_extend(mem32[rbhb + imms12]) | 4 字节 | [SimRISC-01 §存取RD寄存器] |
| ld.o rdha, rbhb, imms12 | rdha = mem64[rbhb + imms12] | 8 字节 | [SimRISC-01 §存取RD寄存器] |
| st.b rdha, rbhb, imms12 | mem8[rbhb + imms12] = rdha[7:0] | 无 | [SimRISC-01 §存取RD寄存器] |
| st.w rdha, rbhb, imms12 | mem16[rbhb + imms12] = rdha[15:0] | 2 字节 | [SimRISC-01 §存取RD寄存器] |
| st.t rdha, rbhb, imms12 | mem32[rbhb + imms12] = rdha[31:0] | 4 字节 | [SimRISC-01 §存取RD寄存器] |
| st.o rdha, rbhb, imms12 | mem64[rbhb + imms12] = rdha[63:0] | 8 字节 | [SimRISC-01 §存取RD寄存器] |

异常条件：[SimRISC-01 §存取RD寄存器]
- rdha 为 rd0 → ILLI
- 未对齐 → MALIGN

#### §4.1.2 多 load/store（rrri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| ldm.sb/ldm.ub/ldm.sw/ldm.uw/ldm.st/ldm.ut/ldm.o rdha, rbhb, rdhc, immu6 | 从 rbhb+rdhc 地址加载 immu6 个连续寄存器 | [SimRISC-01 §存取RD寄存器] |
| stm.b/stm.w/stm.t/stm.o rdha, rbhb, rdhc, immu6 | 将 immu6 个连续寄存器存储到 rbhb+rdhc 地址 | [SimRISC-01 §存取RD寄存器] |

- rdha 指定第一个寄存器，immu6 指定寄存器个数（1–63） [SimRISC-01 §存取RD寄存器]
- 对齐要求同单 load/store [SimRISC-01 §存取RD寄存器]
- 当多寄存器读写的范围包括 rdhc 时，地址计算仍按原始 rdhc 值进行 [SimRISC-01 §存取RD寄存器]
- 硬件按序号递增逐对处理，每对先读后写 [SimRISC-01 §存取RD寄存器]

异常条件：[SimRISC-01 §存取RD寄存器]
- rdha 为 rd0 → ILLI
- immu6 = 0 → ILLI
- rdha + immu6 > 64 → ILLI
- 未对齐 → MALIGN

### §4.2 存取 RB 寄存器

| 指令 | 语义 | 来源 |
|------|------|------|
| ld.o rbha, rbhb, imms12 | rbha = mem64[rbhb + imms12]，全 64 位覆盖 | [SimRISC-02 §存取RB寄存器] |
| st.o rbha, rbhb, imms12 | mem64[rbhb + imms12] = rbha | [SimRISC-02 §存取RB寄存器] |
| ldm.o rbha, rbhb, rdhc, immu6 | 多寄存器加载 | [SimRISC-02 §存取RB寄存器] |
| stm.o rbha, rbhb, rdhc, immu6 | 多寄存器存储 | [SimRISC-02 §存取RB寄存器] |

异常条件：[SimRISC-02 §存取RB寄存器]
- 需 8 字节对齐，未对齐 → MALIGN
- rbha 为 rb0 → ILLI
- immu6 = 0 → ILLI
- rbha + immu6 > 64 → ILLI

### §4.3 存取 RA 寄存器

| 指令 | 语义 | 来源 |
|------|------|------|
| ld.o raha, rbhb, imms12 | raha = mem64[rbhb + imms12] | [SimRISC-02 §存取RA寄存器] |
| st.o raha, rbhb, imms12 | mem64[rbhb + imms12] = raha | [SimRISC-02 §存取RA寄存器] |
| ldm.o raha, rbhb, rdhc, immu6 | 多寄存器加载 | [SimRISC-02 §存取RA寄存器] |
| stm.o raha, rbhb, rdhc, immu6 | 多寄存器存储 | [SimRISC-02 §存取RA寄存器] |

异常条件：[SimRISC-02 §存取RA寄存器]
- 需 8 字节对齐，未对齐 → MALIGN
- raha 为 ra0 时不触发异常（ra0 可读写）
- immu6 = 0 → ILLI
- raha + immu6 > 64 → ILLI

### §4.4 存取 RF 寄存器

| 指令 | 语义 | 对齐要求 | 来源 |
|------|------|---------|------|
| ld.t rfha, rbhb, imms12 | rfha[31:0] = mem32[rbhb + imms12] | 4 字节 | [SimRISC-03 §存取RF寄存器] |
| st.t rfha, rbhb, imms12 | mem32[rbhb + imms12] = rfha[31:0] | 4 字节 | [SimRISC-03 §存取RF寄存器] |
| ld.o rfha, rbhb, imms12 | rfha = mem64[rbhb + imms12] | 8 字节 | [SimRISC-03 §存取RF寄存器] |
| st.o rfha, rbhb, imms12 | mem64[rbhb + imms12] = rfha | 8 字节 | [SimRISC-03 §存取RF寄存器] |
| ldm.t/stm.t rfha, rbhb, rdhc, immu6 | 多寄存器 32 位存取 | 4 字节 | [SimRISC-03 §存取RF寄存器] |
| ldm.o/stm.o rfha, rbhb, rdhc, immu6 | 多寄存器 64 位存取 | 8 字节 | [SimRISC-03 §存取RF寄存器] |

异常条件：[SimRISC-03 §存取RF寄存器]
- immu6 = 0 → ILLI
- rfha + immu6 > 64 → ILLI
- 未对齐 → MALIGN

### §4.5 RB 块赋值（orri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| rb2rd rdhb, rbhc, immu6 | RB→RD 块复制 | [SimRISC-02 §寄存器组之间块赋值] |
| rd2rb rbhb, rdhc, immu6 | RD→RB 块复制 | [SimRISC-02 §寄存器组之间块赋值] |
| rb2rb rbhb, rbhc, immu6 | RB→RB 块复制 | [SimRISC-02 §寄存器组之间块赋值] |
| ra2rd rdhb, rahc, immu6 | RA→RD 块复制 | [SimRISC-02 §寄存器组之间块赋值] |
| rd2ra rahb, rdhc, immu6 | RD→RA 块复制 | [SimRISC-02 §寄存器组之间块赋值] |

限制：rb/rf/ra 之间不能直接赋值，ra 与 ra 之间不能相互赋值。[SimRISC-02 §寄存器组之间块赋值]

异常条件：[SimRISC-02 §寄存器组之间块赋值]
- immu6 = 0 → ILLI
- rbhb 为 rb0 → ILLI（目的）
- 任一起始寄存器 + immu6 > 64 → ILLI

### §4.6 RF 块赋值（orri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| rf2rd rdhb, rfhc, immu6 | RF→RD 块复制 | [SimRISC-03 §寄存器组之间块赋值] |
| rd2rf rfhb, rdhc, immu6 | RD→RF 块复制 | [SimRISC-03 §寄存器组之间块赋值] |

异常条件：[SimRISC-03 §寄存器组之间块赋值]
- immu6 = 0 → ILLI
- 任一起始寄存器 + immu6 > 64 → ILLI

### §4.7 RB 立即数设置（rwii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| set.zw rbha, wpN, immu16 | rbha[wyde(wpN)] = immu16，其余 48 位清 0 | [SimRISC-02 §立即数常数赋值] |
| or.w rbha, wpN, immu16 | rbha[wyde(wpN)] \|= immu16，其余不变 | [SimRISC-02 §立即数常数赋值] |
| andn.w rbha, wpN, immu16 | rbha[wyde(wpN)] &= ~immu16，其余不变 | [SimRISC-02 §立即数常数赋值] |

注意：rb 无 `set.ow` 变体。[SimRISC-02 §set.rb 伪指令]

### §4.8 RB 算术运算（orrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| add.so rbhb, rbhc, rdhd | rbhb = rbhc + rdhd，二进制补码 64 位加法 | [SimRISC-02 §加减操作] |
| sub.so rbhb, rbhc, rdhd | rbhb = rbhc - rdhd，二进制补码 64 位减法 | [SimRISC-02 §加减操作] |

地址计算仅在低 48 位有效，溢出丢弃。高 16 位（bits[63:48]）为运算结果，可用于溢出检测。[SimRISC-02 §加减操作]

### §4.9 RB 自增自减（riii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| add.si rbha, imms18 | rbha = rbha + sign_extend(imms18)，全 64 位运算 | [SimRISC-02 §自增自减] |

用户可通过 rbha 的高 16 位判断地址溢出。[SimRISC-02 §自增自减]

### §4.10 RB 比较（orrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| cmp.uo rdhb, rbhc, rbhd | 无符号 64 位比较，rdhb = sign(cmp(rbhc, rbhd)) | [SimRISC-02 §比较操作] |

bits[63:48] 不影响比较运算。[SimRISC-02 §比较操作]

### §4.11 PC 相对寻址（riii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| rela.si rbha, imms18 | rbha = (PC & ~0xFFF) + sign_extend(imms18 << 12)，高 16 位保持不变 | [SimRISC-02 §PC相对寻址] |

- imms18 左移 12 位得到 30 位有符号数 [SimRISC-02 §PC相对寻址]
- PC 低 12 位清零得到 4KB 对齐基地址 [SimRISC-02 §PC相对寻址]
- 可处理偏移地址在 512MB 以内的 PC 相对寻址 [SimRISC-02 §PC相对寻址]

### §4.12 伪指令（地址/内存）

| 伪指令 | 展开形式 | 来源 |
|--------|----------|------|
| set.rb rbxx, imm64 | set.zw-rb + or.w-rb | [SimRISC-02 §set.rb 伪指令] |
| set.rb rbxx, rs | rd2rb/rb2rb | [SimRISC-02 §set.rb 伪指令] |

---

## §5 控制流

### §5.1 条件跳转

所有条件跳转使用相对地址，地址位宽为 48 位，不产生溢出。[SimRISC-02 §控制流指令]

#### §5.1.1 双寄存器比较跳转（rrii 格式）

| 指令 | 语义 | 地址计算 | 来源 |
|------|------|---------|------|
| br.eq rdha, rdhb, imms12 | if (rdha == rdhb) PC = rb0 + (imms12 << 2) | rb0 + sign_extend(imms12 << 2) | [SimRISC-02 §条件跳转指令] |
| br.ne rdha, rdhb, imms12 | if (rdha != rdhb) PC = rb0 + (imms12 << 2) | rb0 + sign_extend(imms12 << 2) | [SimRISC-02 §条件跳转指令] |

#### §5.1.2 单寄存器条件跳转（riii 格式）

| 指令 | 语义 | 地址计算 | 来源 |
|------|------|---------|------|
| br.n rdha, imms18 | if (rdha < 0) PC = rb0 + (imms18 << 2) | rb0 + sign_extend(imms18 << 2) | [SimRISC-02 §条件跳转指令] |
| br.nn rdha, imms18 | if (rdha >= 0) PC = rb0 + (imms18 << 2) | rb0 + sign_extend(imms18 << 2) | [SimRISC-02 §条件跳转指令] |
| br.z rdha, imms18 | if (rdha == 0) PC = rb0 + (imms18 << 2) | rb0 + sign_extend(imms18 << 2) | [SimRISC-02 §条件跳转指令] |
| br.nz rdha, imms18 | if (rdha != 0) PC = rb0 + (imms18 << 2) | rb0 + sign_extend(imms18 << 2) | [SimRISC-02 §条件跳转指令] |
| br.p rdha, imms18 | if (rdha > 0) PC = rb0 + (imms18 << 2) | rb0 + sign_extend(imms18 << 2) | [SimRISC-02 §条件跳转指令] |
| br.np rdha, imms18 | if (rdha <= 0) PC = rb0 + (imms18 << 2) | rb0 + sign_extend(imms18 << 2) | [SimRISC-02 §条件跳转指令] |

特例：rdha 为 rd0 时，br.z 条件必为真，br.nz 条件必为假。[SimRISC-02 §条件跳转指令]

#### §5.1.3 RB 条件跳转（riii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| br.z rbha, imms18 | if (rbha == 0) PC = rb0 + (imms18 << 2) | [SimRISC-02 §条件跳转指令] |
| br.nz rbha, imms18 | if (rbha != 0) PC = rb0 + (imms18 << 2) | [SimRISC-02 §条件跳转指令] |

### §5.2 无条件跳转

#### §5.2.1 相对跳转（iiii 格式）

| 指令 | 地址计算 | 来源 |
|------|---------|------|
| jump imms24 | PC = rb0 + (imms24 << 2) | [SimRISC-02 §无条件跳转指令] |

#### §5.2.2 绝对跳转（rrii 格式）

| 指令 | 地址计算 | 来源 |
|------|---------|------|
| jump rbha, rdhb, imms12 | PC = rbha + rdhb + (imms12 << 2) | [SimRISC-02 §无条件跳转指令] |

地址位宽为 48 位，不产生溢出。当 ha 为 rb0 时，为相对地址跳转。[SimRISC-02 §无条件跳转指令]

### §5.3 函数调用

函数调用指令会计算返回地址，并压入 ra63（RegRAS 栈顶）。高 16 位为引用计数（首次压栈设为 1，递归调用递增），低 48 位为返回地址。[SimRISC-02 §函数调用]

#### §5.3.1 相对调用（iiii 格式）

| 指令 | 地址计算 | 来源 |
|------|---------|------|
| call imms24 | PC = rb0 + (imms24 << 2) | [SimRISC-02 §函数调用] |

#### §5.3.2 绝对调用（rrii 格式）

| 指令 | 地址计算 | 来源 |
|------|---------|------|
| call rbha, rdhb, imms12 | PC = rbha + rdhb + (imms12 << 2) | [SimRISC-02 §函数调用] |

地址位宽为 48 位，不产生溢出。[SimRISC-02 §函数调用]

#### §5.3.3 压栈流程

以 ra63 为 RegRAS 栈顶。[SimRISC-00 §压栈流程]

1. 若 ra63 高 16 位全为 0（无效），新返回地址压入 ra63，高 16 位设为 0x0001
2. 若 ra63 高 16 位非全 0 且非全 1，且新返回地址与 ra63 低 48 位相等（递归调用），则 ra63 高 16 位 + 1
3. 否则移位压栈：
   - 新返回地址压入 ra63，高 16 位设为 0x0001
   - 原 ra63→ra62，原 ra62→ra61，……，原 ra2→ra1
   - 原 ra1 若有效：ra0 低 48 位为 0 时触发 RASOF；非 0 时压入 MemRAS

### §5.4 函数返回

ret 指令从 ra63 弹出返回地址（低 48 位），并跳转。[SimRISC-02 §函数返回]

| 指令 | 语义 | 来源 |
|------|------|------|
| ret rdha, imms18 | rdha = sign_extend(imms18)，PC = ra63 低 48 位 | [SimRISC-02 §函数返回] |

#### §5.4.1 弹栈流程

[SimRISC-00 §弹栈流程]

1. 若 ra63 高 16 位 > 0x0001，则高 16 位 − 1，低 48 位为返回地址
2. 若 ra63 高 16 位 = 0x0001，弹出低 48 位为返回地址，移位弹栈：
   - ra62→ra63，ra61→ra62，……，ra1→ra2，ra1 清 0
3. 若 ra63 高 16 位全为 0（无效）：
   - ra0 低 48 位为 0 → RASUF
   - ra0 低 48 位非 0 → 从 MemRAS 弹栈
     - 弹出内容高 16 位为 0 → RASUF
     - 高 16 位为 0x0001 → 低 48 位为返回地址
     - 高 16 位 > 0x0001 → 存入 ra63，高 16 位 − 1，低 48 位为返回地址

### §5.5 伪指令（控制流）

| 伪指令 | 展开形式 | 来源 |
|--------|----------|------|
| return | ret rd0, 0 | [SimRISC-02 §return 伪指令] |

---

## §6 浮点指令

浮点格式符合 IEEE 754 标准。舍入模式由 rf0[17:16] 控制，异常标志在 rf0[4:0]。[SimRISC-03 §版本]

### §6.1 浮点算术运算

#### §6.1.1 双源单目运算（orrr 格式）

硬件先读全部源操作数再写结果。[SimRISC-03 §S2D1]

| 指令 | 语义 | 来源 |
|------|------|------|
| ftadd rfhb, rfhc, rfhd | rfhb = rfhc + rfhd（单精） | [SimRISC-03 §S2D1] |
| ftsub rfhb, rfhc, rfhd | rfhb = rfhc - rfhd（单精） | [SimRISC-03 §S2D1] |
| ftmul rfhb, rfhc, rfhd | rfhb = rfhc × rfhd（单精） | [SimRISC-03 §S2D1] |
| ftdiv rfhb, rfhc, rfhd | rfhb = rfhc / rfhd（单精） | [SimRISC-03 §S2D1] |
| ftrem rfhb, rfhc, rfhd | rfhb = IEEE754 remainder(rfhc, rfhd)（单精） | [SimRISC-03 §S2D1] |
| ftsclb rfhb, rfhc, rfhd | rfhb = rfhc × 2^rfhd（单精，scaleB） | [SimRISC-03 §S2D1] |
| foadd rfhb, rfhc, rfhd | rfhb = rfhc + rfhd（双精） | [SimRISC-03 §S2D1] |
| fosub rfhb, rfhc, rfhd | rfhb = rfhc - rfhd（双精） | [SimRISC-03 §S2D1] |
| fomul rfhb, rfhc, rfhd | rfhb = rfhc × rfhd（双精） | [SimRISC-03 §S2D1] |
| fodiv rfhb, rfhc, rfhd | rfhb = rfhc / rfhd（双精） | [SimRISC-03 §S2D1] |
| forem rfhb, rfhc, rfhd | rfhb = IEEE754 remainder(rfhc, rfhd)（双精） | [SimRISC-03 §S2D1] |
| fosclb rfhb, rfhc, rfhd | rfhb = rfhc × 2^rfhd（双精，scaleB） | [SimRISC-03 §S2D1] |

异常条件：目的或任一源操作数为 rf0 → ILLI。[SimRISC-03 §rf0 为目的寄存器约定]

#### §6.1.2 融合乘加（rrrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| ftmadd rfha, rfhb, rfhc, rfhd | rfha = rfhb × rfhc + rfhd（单精 FMA） | [SimRISC-03 §S3D1] |
| fomadd rfha, rfhb, rfhc, rfhd | rfha = rfhb × rfhc + rfhd（双精 FMA） | [SimRISC-03 §S3D1] |

融合乘加为单次舍入（标准 FMA）。硬件先读全部源操作数再写结果。[SimRISC-03 §S3D1]

#### §6.1.3 单源单目运算（orri 格式）

| 指令 | 语义 | immu6 支持值 | 来源 |
|------|------|-------------|------|
| ftroot rfhb, rfhc, immu6 | rfhb = rootn(rfhc, immu6)（单精） | 2（平方根）、3（立方根） | [SimRISC-03 §S1D1] |
| foroot rfhb, rfhc, immu6 | rfhb = rootn(rfhc, immu6)（双精） | 2（平方根）、3（立方根） | [SimRISC-03 §S1D1] |
| ftlog rfhb, rfhc, immu6 | rfhb = log_base(rfhc)，base=immu6（单精） | 2（log2）、1（自然对数）、0（log10） | [SimRISC-03 §S1D1] |
| folog rfhb, rfhc, immu6 | rfhb = log_base(rfhc)，base=immu6（双精） | 2（log2）、1（自然对数）、0（log10） | [SimRISC-03 §S1D1] |

不支持的 immu6 值触发 ILLI 异常。[SimRISC-03 §S1D1]

### §6.2 浮点符号位操作（orrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| ftsgnj rfhb, rfhc, rfhd | rfhb = copySign(rfhc, rfhd)（单精） | [SimRISC-03 §浮点符号位操作指令] |
| fosgnj rfhb, rfhc, rfhd | rfhb = copySign(rfhc, rfhd)（双精） | [SimRISC-03 §浮点符号位操作指令] |
| ftsgnn rfhb, rfhc, rfhd | rfhb = copySign(rfhc, negate(rfhd))（单精） | [SimRISC-03 §浮点符号位操作指令] |
| fosgnn rfhb, rfhc, rfhd | rfhb = copySign(rfhc, negate(rfhd))（双精） | [SimRISC-03 §浮点符号位操作指令] |

特例：[SimRISC-03 §浮点符号位操作指令]
- rfhd = rf0 时：ftsgnj/fosgnj 实现 abs(rfhc)，ftsgnn/fosgnn 实现 −abs(rfhc)
- rfhc = rfhd 时：ftsgnj/fosgnj 实现 copy(rfhc)，ftsgnn/fosgnn 实现 negate(rfhc)

### §6.3 浮点比较（orrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| ftqcmp rdhb, rfhc, rfhd | 单精 Quiet Compare | [SimRISC-03 §浮点比较指令] |
| ftscmp rdhb, rfhc, rfhd | 单精 Signaling Compare | [SimRISC-03 §浮点比较指令] |
| foqcmp rdhb, rfhc, rfhd | 双精 Quiet Compare | [SimRISC-03 §浮点比较指令] |
| foscmp rdhb, rfhc, rfhd | 双精 Signaling Compare | [SimRISC-03 §浮点比较指令] |

比较结果（写入 rdhb）：[SimRISC-03 §浮点比较指令]
- 1：rfhc > rfhd
- 0：rfhc = rfhd
- −1：rfhc < rfhd
- NaN：unordered（Quiet Compare 为 qNaN，Signaling Compare 为 sNaN，符号位均为 0）

### §6.4 浮点条件赋值（rrrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| cs.n rdha, rfhb, rfhc, rfhd | if (rdha < 0) rfhb = rfhc else rfhb = rfhd | [SimRISC-03 §浮点条件赋值指令] |
| cs.z rdha, rfhb, rfhc, rfhd | if (rdha == 0) rfhb = rfhc else rfhb = rfhd | [SimRISC-03 §浮点条件赋值指令] |
| cs.p rdha, rfhb, rfhc, rfhd | if (rdha > 0) rfhb = rfhc else rfhb = rfhd | [SimRISC-03 §浮点条件赋值指令] |
| cs.eq rdha, rdhb, rfhc, rfhd | if (rdha == rdhb) rfhc = rfhd | [SimRISC-03 §浮点条件赋值指令] |
| cs.ne rdha, rdhb, rfhc, rfhd | if (rdha != rdhb) rfhc = rfhd | [SimRISC-03 §浮点条件赋值指令] |

当比较结果为 NaN 时，cs.eq 和 cs.ne 均执行 else 分支。[SimRISC-03 §浮点条件赋值指令]

### §6.5 浮点分类（orri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| ftcls rdhb, rfhc, 1 | 单精浮点分类 | [SimRISC-03 §浮点分类指令] |
| focls rdhb, rfhc, 1 | 双精浮点分类 | [SimRISC-03 §浮点分类指令] |

分类结果位（rdhb[9:0]，其余位清零）：[SimRISC-03 §浮点分类指令]

| 位 | 含义 |
|----|------|
| 0 | negativeInfinity |
| 1 | negativeNormal |
| 2 | negativeSubnormal |
| 3 | negativeZero |
| 4 | positiveZero |
| 5 | positiveSubnormal |
| 6 | positiveNormal |
| 7 | positiveInfinity |
| 8 | signalingNaN |
| 9 | quietNaN |

### §6.6 浮点格式转换（orri 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| ft2fo rfhb, rfhc, immu6 | 单精→双精 | [SimRISC-03 §格式转换指令] |
| fo2ft rfhb, rfhc, immu6 | 双精→单精 | [SimRISC-03 §格式转换指令] |
| ft2ft rfhb, rfhc, immu6 | 单精寄存器间搬移 | [SimRISC-03 §格式转换指令] |
| fo2fo rfhb, rfhc, immu6 | 双精寄存器间搬移 | [SimRISC-03 §格式转换指令] |
| ft2it/ft2io/ft2ut/ft2uo rdhb, rfhc, immu6 | 浮点→整数 | [SimRISC-03 §格式转换指令] |
| it2ft/io2ft/ut2ft/uo2ft rfhb, rdhc, immu6 | 整数→浮点 | [SimRISC-03 §格式转换指令] |
| fo2it/fo2io/fo2ut/fo2uo rdhb, rfhc, immu6 | 浮点→整数 | [SimRISC-03 §格式转换指令] |
| it2fo/io2fo/ut2fo/uo2fo rfhb, rdhc, immu6 | 整数→浮点 | [SimRISC-03 §格式转换指令] |

其中 it=32 位有符号整数，io=64 位有符号整数，ut=32 位无符号整数，uo=64 位无符号整数，ft=32 位单精浮点，fo=64 位双精浮点。[SimRISC-03 §格式转换指令]

- immu6 指定连续转换的寄存器数量（1–63） [SimRISC-03 §格式转换指令]
- 源和目的可重叠，按序号递增逐对进行，先读后写 [SimRISC-03 §格式转换指令]

浮点格式转换遵循 IEEE 754 标准：[SimRISC-03 §格式转换指令]
- 浮点→浮点溢出返回 ±Inf（设置 OF），下溢按舍入模式处理（设置 UF），NaN 传播 payload
- 整数→浮点转换可能 inexact（精度损失）
- 浮点→整数转换中 NaN/Inf/超出范围返回整型饱和值，设置 NV 标志
- sNaN 作为算术输入时设置 NV 并返回 qNaN

异常条件：[SimRISC-03 §格式转换指令]
- immu6 = 0 → ILLI
- 任一起始寄存器 + immu6 > 64 → ILLI

### §6.7 RF 立即数设置（rwii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| set.w rfha, wpN, immu16 | rfha[wyde(wpN)] = immu16，其余 48 位不变 | [SimRISC-03 §立即数常数赋值] |

### §6.8 伪指令（浮点）

| 伪指令 | 展开形式 | 来源 |
|--------|----------|------|
| set.ft rfxx, imm32 | set.w（2 条） | [SimRISC-03 §set.ft / set.fo 伪指令] |
| set.fo rfxx, imm64 | set.w（4 条） | [SimRISC-03 §set.ft / set.fo 伪指令] |
| set.ft rfxx, rs | rd2rf/ft2ft | [SimRISC-03 §set.ft / set.fo 伪指令] |
| set.fo rfxx, rs | rd2rf/fo2fo | [SimRISC-03 §set.ft / set.fo 伪指令] |

---

## §7 系统指令

### §7.1 占位指令（iiii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| swym 0 | 除 PC 自增外无任何架构副作用（等同于 nop） | [SimRISC-04 §占位指令] |
| swym N | 硬件时延指令，时延约为 swym 0 的 N+1 倍 | [SimRISC-04 §占位指令] |

- swym N 的后 24 位立即数为时延参数 [SimRISC-04 §占位指令]
- 硬件可设时延上限，N 超过阈值后时延不再增加 [SimRISC-04 §占位指令]
- 无论 N 取何值，指令仍为单条 32 位指令 [SimRISC-04 §占位指令]

### §7.2 非法指令（oiii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| illi 0 | 触发 ILLI 异常 | [SimRISC-04 §非法指令] |

- illi 的后 18 位立即数无特殊含义，由用户自行定义 [SimRISC-04 §非法指令]
- illi 的 opcode 和 minor-opcode 均为全 0，当参数也为 0 时即为 32 位全零指令字 [SimRISC-04 §非法指令]
- 未初始化的指令内存（全零）将触发 ILLI 异常 [SimRISC-04 §非法指令]

### §7.3 fence 指令（oiii 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| fence immu18 | 内存序屏障 | [SimRISC-04 §fence指令] |

低 4 位编码定义屏障类型：[SimRISC-04 §fence指令]

| 位 | 含义 | 说明 |
|----|------|------|
| bit0 | IO | 设备 I/O 访问串行化 |
| bit1 | W | 写屏障：前序写对后序写可见 |
| bit2 | R | 读屏障：前序读对后序读/写可见 |
| bit3 | RW | 读写屏障：前序读写对后序读写可见（全屏障） |

bits[17:4] 应为零（SBZ），非零值行为保留。[SimRISC-04 §fence指令]

### §7.4 LR-SC 指令（orrr 格式）

| 指令 | 语义 | 来源 |
|------|------|------|
| lr_nn.o rdhc, rbhd | Load Reserved（无顺序限制） | [SimRISC-04 §LR-SC指令] |
| lr_an.o rdhc, rbhd | Load Reserved（acquire） | [SimRISC-04 §LR-SC指令] |
| lr_nr.o rdhc, rbhd | Load Reserved（无顺序限制） | [SimRISC-04 §LR-SC指令] |
| lr_ar.o rdhc, rbhd | Load Reserved（acquire + release） | [SimRISC-04 §LR-SC指令] |
| sc_nn.o rdhb, rdhc, rbhd | Store Conditional（无顺序限制） | [SimRISC-04 §LR-SC指令] |
| sc_an.o rdhb, rdhc, rbhd | Store Conditional（acquire） | [SimRISC-04 §LR-SC指令] |
| sc_nr.o rdhb, rdhc, rbhd | Store Conditional（无顺序限制） | [SimRISC-04 §LR-SC指令] |
| sc_ar.o rdhb, rdhc, rbhd | Store Conditional（acquire + release） | [SimRISC-04 §LR-SC指令] |

- a=acquire，r=release，n=无顺序限制 [SimRISC-04 §LR-SC指令]
- o=octa（64 位数据） [SimRISC-04 §LR-SC指令]
- lr 的 hb（rdhb）固定为 rd0，汇编代码仅需两个操作数；若 hb ≠ 0 → ILLI [SimRISC-04 §LR-SC指令]
- lr 从 rbhd 地址加载到 rdhc，并设置保留标记 [SimRISC-04 §LR-SC指令]
- sc 在保留标记仍在时写入 rdhc 到 rbhd 地址，rdhb 设为 0（成功）；否则不写入，rdhb 设为 1（失败） [SimRISC-04 §LR-SC指令]
- sc 总是清除当前 hart 上所有保留标记 [SimRISC-04 §LR-SC指令]
- 要求 rbhd 中地址 8 字节对齐，否则 → MALIGN [SimRISC-04 §LR-SC指令]

保留机制：[SimRISC-04 §LR-SC指令]
- 一条 lr 在 hart 上设置保留标记
- sc 可能偶发性失败（spurious failure），软件应在循环中重试
- 以下事件清除保留标记：另一 hart 对保留地址的 store、当前 hart 执行另一条 lr、异常或中断进入

### §7.5 特权指令（crrr/crii/ciii 格式）

#### §7.5.1 陷入指令

| 指令 | 语义 | 来源 |
|------|------|------|
| trap cfxname, immu18 | 将控制权转移到 cfxname 的异常向量地址 | [SimRISC-04 §陷入指令] |

#### §7.5.2 退出指令

| 指令 | 语义 | 来源 |
|------|------|------|
| escape cfxname, imms18 | 退出当前特权态，目标地址 = excp_cause_ip + (imms18 << 2) | [SimRISC-04 §退出指令] |

#### §7.5.3 寄存器传输指令

| 指令 | 语义 | 来源 |
|------|------|------|
| cfx2rd cfxname, cghb, rchc, rdhd | 读 cfx 寄存器到 rdhd | [SimRISC-04 §寄存器传输指令] |
| cfx2rc cfxname, cghb, rchc, rdhd | 写 rdhd 到 cfx 寄存器 | [SimRISC-04 §寄存器传输指令] |

异常条件：[SimRISC-04 §寄存器传输指令]
- 读写不存在的 cfx 寄存器组合 → CFXREG
- cfxname 为 reserved（7–14、19–61）→ ILLI
- 读写权限不匹配 → CFXREG

#### §7.5.4 SRAM 块传输指令

| 指令 | 语义 | 来源 |
|------|------|------|
| cfxld cfxname, rbhb, immu12 | 内存→cfx 内部存储 | [SimRISC-04 §SRAM块传输指令] |
| cfxst cfxname, rbhb, immu12 | cfx 内部存储→内存 | [SimRISC-04 §SRAM块传输指令] |

- 要求 64 字节对齐，传输长度 = immu12 × 64 字节 [SimRISC-04 §SRAM块传输指令]
- cfxname 为 reserved（7–14、19–61）→ ILLI [SimRISC-04 §SRAM块传输指令]

### §7.6 伪指令（系统）

| 伪指令 | 展开形式 | 来源 |
|--------|----------|------|
| nop | swym 0 | [SimRISC-04 §nop 伪指令] |

---

## §8 NOP 与保留编码

### §8.1 NOP

`nop` 是汇编器伪指令，等价于 `swym 0`。[SimRISC-04 §nop 伪指令]

### §8.2 保留编码

QFC 表中空白单元格为 reserved（保留未分配）。执行保留编码触发 UNDI 异常。[SimRISC-00 §SimRISC QFC]

### §8.3 全零指令

32 位全零指令字（0x00000000）是 `illi 0`（opcode 和 minor-opcode 均为全 0），触发 ILLI 异常。[SimRISC-04 §非法指令]

---

## §9 异常总结

| 异常 | 触发条件 | 来源 |
|------|---------|------|
| ILLI | 非法指令、非法操作数约束违反 | [SimRISC-04 §非法指令] |
| MALIGN | 内存访问未对齐 | [SimRISC-01 §存取RD寄存器] |
| UNDI | 执行保留编码 | [SimRISC-00 §SimRISC QFC] |
| IALIGN | 取指时 PC[1:0] ≠ 00 | [SimRISC-00 §指令设计] |
| RASOF | RegRAS 压栈溢出（调用深度超过 63） | [SimRISC-00 §压栈流程] |
| RASUF | RegRAS 弹栈下溢（栈空时 ret） | [SimRISC-00 §弹栈流程] |
| CFXREG | 读写不存在的 cfx 寄存器或权限不匹配 | [SimRISC-04 §寄存器传输指令] |

ILLI 触发场景汇总：[SimRISC-01, SimRISC-02, SimRISC-03, SimRISC-04]
- 目的寄存器为 rd0（除 rrrr 双目指令允许一个为 rd0、ret rd0 0 允许外）
- 目的寄存器为 rb0
- 浮点运算指令的目的或任一源操作数为 rf0
- ldm/stm 的 rdha 为 rd0 或 immu6 = 0 或 rdha + immu6 > 64
- 块赋值的 immu6 = 0 或目的为 rd0/rb0 或起始 + immu6 > 64
- 移位量 shamt > N
- 扩展的 hd > N
- 除数为零
- div.s 中 INT_MIN ÷ −1
- add/sub rrrr 中 rdha 和 rdhb 同时为 rd0 或为同一非 rd0 寄存器
- illi 指令本身
- cfxname 为 reserved（7–14、19–61）
- lr 的 hb ≠ 0
- 不支持的 ftroot/foroot/ftlog/folog 的 immu6 值

---

## 附录 A：完整编码清单

### A.1 QFC 主表（op[7:0]）

| op | 格式 | insn | 助记符 |
|------|------|--------|
| 0000-0000 | oiii | illi | illi |
| 0000-0001 | oiii | fence | fence |
| 0000-0100 | orrr | lr_nn.o | lr_nn.o |
| 0000-0101 | orrr | lr_nr.o | lr_nr.o |
| 0000-0110 | orrr | lr_an.o | lr_an.o |
| 0000-0111 | orrr | lr_ar.o | lr_ar.o |
| 0000-1100 | orrr | sc_nn.o | sc_nn.o |
| 0000-1101 | orrr | sc_nr.o | sc_nr.o |
| 0000-1110 | orrr | sc_an.o | sc_an.o |
| 0000-1111 | orrr | sc_ar.o | sc_ar.o |
| 0001-0000 | rrii | ld.ub-rd | ld.ub |
| 0001-0001 | rrii | ld.uw-rd | ld.uw |
| 0001-0010 | rrii | ld.ut-rd | ld.ut |
| 0001-0011 | rrii | ld.sb-rd | ld.sb |
| 0001-0100 | rrii | ld.sw-rd | ld.sw |
| 0001-0101 | rrii | ld.st-rd | ld.st |
| 0001-0110 | rrii | ld.t-rf | ld.t |
| 0001-0111 | rrii | st.t-rf | st.t |
| 0001-1000 | rrii | st.b-rd | st.b |
| 0001-1001 | rrii | st.w-rd | st.w |
| 0001-1010 | rrii | st.t-rd | st.t |
| 0010-0000 | rrii | ld.o-rd | ld.o |
| 0010-0001 | rrii | st.o-rd | st.o |
| 0010-0010 | rrii | ld.o-rb | ld.o |
| 0010-0011 | rrii | st.o-rb | st.o |
| 0010-0100 | rrii | ld.o-ra | ld.o |
| 0010-0101 | rrii | st.o-ra | st.o |
| 0010-0110 | rrii | ld.o-rf | ld.o |
| 0010-0111 | rrii | st.o-rf | st.o |
| 0010-1000 | rrri | ldm.ub-rd | ldm.ub |
| 0010-1001 | rrri | ldm.uw-rd | ldm.uw |
| 0010-1010 | rrri | ldm.ut-rd | ldm.ut |
| 0010-1011 | rrri | ldm.sb-rd | ldm.sb |
| 0010-1100 | rrri | ldm.sw-rd | ldm.sw |
| 0010-1101 | rrri | ldm.st-rd | ldm.st |
| 0010-1110 | rrri | ldm.t-rf | ldm.t |
| 0010-1111 | rrri | stm.t-rf | stm.t |
| 0011-0000 | rrri | stm.b-rd | stm.b |
| 0011-0001 | rrri | stm.w-rd | stm.w |
| 0011-0010 | rrri | stm.t-rd | stm.t |
| 0011-1000 | rrri | ldm.o-rd | ldm.o |
| 0011-1001 | rrri | stm.o-rd | stm.o |
| 0011-1010 | rrri | ldm.o-rb | ldm.o |
| 0011-1011 | rrri | stm.o-rb | stm.o |
| 0011-1100 | rrri | ldm.o-ra | ldm.o |
| 0011-1101 | rrri | stm.o-ra | stm.o |
| 0011-1110 | rrri | ldm.o-rf | ldm.o |
| 0011-1111 | rrri | stm.o-rf | stm.o |
| 0100-0000 | — | MISC-AMO 子表 |
| 0100-0001 | — | MISC-octa 子表 |
| 0100-0010 | — | MISC-tetra 子表 |
| 0100-0011 | — | MISC-wyde 子表 |
| 0100-0100 | — | MISC-byte 子表 |
| 0100-0101 | — | MISC-RF 子表 |
| 0100-1000 | rwii | or.w-rd | or.w |
| 0100-1001 | rwii | andn.w-rd | andn.w |
| 0100-1010 | rwii | or.w-rb | or.w |
| 0100-1011 | rwii | andn.w-rb | andn.w |
| 0100-1100 | rwii | set.zw-rd | set.zw |
| 0100-1101 | rwii | set.ow-rd | set.ow |
| 0100-1110 | rwii | set.zw-rb | set.zw |
| 0100-1111 | rwii | set.w-rf | set.w |
| 0101-0000 | rrrr | add.uo-rd | add.uo |
| 0101-0001 | rrrr | add.so-rd | add.so |
| 0101-0010 | rrrr | sub.uo-rd | sub.uo |
| 0101-0011 | rrrr | sub.so-rd | sub.so |
| 0101-0100 | rrrr | mul.uo-rd | mul.uo |
| 0101-0101 | rrrr | mul.so-rd | mul.so |
| 0101-0110 | rrrr | ftmadd | ftmadd |
| 0101-0111 | rrrr | fomadd | fomadd |
| 0101-1001 | riii | add.si-rd | add.si |
| 0101-1010 | riii | rela.si-rb | rela.si |
| 0101-1011 | riii | add.si-rb | add.si |
| 0101-1100 | rrii | cmp.ui-rd | cmp.ui |
| 0101-1101 | rrii | cmp.si-rd | cmp.si |
| 0101-1110 | rrrr | cs.eq-rf | cs.eq |
| 0101-1111 | rrrr | cs.ne-rf | cs.ne |
| 0110-0000 | rrrr | cs.n-rd | cs.n |
| 0110-0001 | rrrr | cs.n-rf | cs.n |
| 0110-0010 | rrrr | cs.z-rd | cs.z |
| 0110-0011 | rrrr | cs.z-rf | cs.z |
| 0110-0100 | rrrr | cs.p-rd | cs.p |
| 0110-0101 | rrrr | cs.p-rf | cs.p |
| 0110-0110 | rrrr | cs.eq-rd | cs.eq |
| 0110-0111 | rrrr | cs.ne-rd | cs.ne |
| 0110-1000 | riii | br.n-rd | br.n |
| 0110-1001 | riii | br.nn-rd | br.nn |
| 0110-1010 | riii | br.z-rd | br.z |
| 0110-1011 | riii | br.nz-rd | br.nz |
| 0110-1100 | riii | br.p-rd | br.p |
| 0110-1101 | riii | br.np-rd | br.np |
| 0110-1110 | rrii | br.eq-rd | br.eq |
| 0110-1111 | rrii | br.ne-rd | br.ne |
| 0111-0000 | iiii | jump-iiii | jump-iiii |
| 0111-0001 | rrii | jump-rrii | jump-rrii |
| 0111-0010 | riii | br.z-rb | br.z |
| 0111-0011 | riii | br.nz-rb | br.nz |
| 0111-0100 | iiii | call-iiii | call-iiii |
| 0111-0101 | rrii | call-rrii | call-rrii |
| 0111-0110 | riii | ret | ret |
| 0111-0111 | iiii | swym | swym |
| 0111-1010 | crrr | cfx2rd | cfx2rd |
| 0111-1011 | crrr | cfx2rc | cfx2rc |
| 0111-1100 | crii | cfxld | cfxld |
| 0111-1101 | crii | cfxst | cfxst |
| 0111-1110 | ciii | escape | escape |
| 0111-1111 | ciii | trap | trap |

### A.2 MISC-octa 子表

| minor-opcode | 助记符 | 格式 |
|-------------|--------|------|
| 001-000 | and.o | orrr |
| 001-001 | or.o | orrr |
| 001-010 | xor.o | orrr |
| 001-011 | xnor.o | orrr |
| 010-000 | ext.uo | orrr |
| 010-001 | ext.so | orrr |
| 010-010 | shr.uo | orrr |
| 010-011 | shr.so | orrr |
| 010-100 | shl.uo | orrr |
| 011-000 | ext.uo | orri |
| 011-001 | ext.so | orri |
| 011-010 | shr.uo | orri |
| 011-011 | shr.so | orri |
| 011-100 | shl.uo | orri |
| 100-000 | add.so-rb | orrr |
| 101-000 | sub.so-rb | orrr |
| 101-001 | cmp.uo-rb | orrr |
| 101-010 | cmp.uo | orrr |
| 101-011 | cmp.so | orrr |
| 101-100 | rd2rd | orri |
| 101-101 | rd2ra | orri |
| 101-110 | ra2rd | orri |
| 110-100 | rb2rb | orri |
| 110-101 | rd2rb | orri |
| 110-110 | rb2rd | orri |
| 111-000 | div.uo | orrr |
| 111-001 | div.so | orrr |
| 111-010 | rem.uo | orrr |
| 111-011 | rem.so | orrr |
| 111-101 | rd2rf | orri |
| 111-110 | rf2rd | orri |

### A.3 MISC-tetra 子表

| minor-opcode | 助记符 | 格式 |
|-------------|--------|------|
| 001-000 | and.t | orrr |
| 001-001 | or.t | orrr |
| 001-010 | xor.t | orrr |
| 001-011 | xnor.t | orrr |
| 010-000 | ext.ut | orrr |
| 010-001 | ext.st | orrr |
| 010-010 | shr.ut | orrr |
| 010-011 | shr.st | orrr |
| 010-100 | shl.ut | orrr |
| 011-000 | ext.ut | orri |
| 011-001 | ext.st | orri |
| 011-010 | shr.ut | orri |
| 011-011 | shr.st | orri |
| 011-100 | shl.ut | orri |
| 100-000 | add.ut | orrr |
| 100-001 | add.st | orrr |
| 101-000 | sub.ut | orrr |
| 101-001 | sub.st | orrr |
| 101-010 | cmp.ut | orrr |
| 101-011 | cmp.st | orrr |
| 110-000 | mul.ut | orrr |
| 110-001 | mul.st | orrr |
| 111-000 | div.ut | orrr |
| 111-001 | div.st | orrr |
| 111-010 | rem.ut | orrr |
| 111-011 | rem.st | orrr |

### A.4 MISC-wyde 子表

| minor-opcode | 助记符 | 格式 |
|-------------|--------|------|
| 001-000 | and.w | orrr |
| 001-001 | or.w | orrr |
| 001-010 | xor.w | orrr |
| 001-011 | xnor.w | orrr |
| 010-000 | ext.uw | orrr |
| 010-001 | ext.sw | orrr |
| 010-010 | shr.uw | orrr |
| 010-011 | shr.sw | orrr |
| 010-100 | shl.uw | orrr |
| 011-000 | ext.uw | orri |
| 011-001 | ext.sw | orri |
| 011-010 | shr.uw | orri |
| 011-011 | shr.sw | orri |
| 011-100 | shl.uw | orri |
| 100-000 | add.uw | orrr |
| 100-001 | add.sw | orrr |
| 101-000 | sub.uw | orrr |
| 101-001 | sub.sw | orrr |
| 101-010 | cmp.uw | orrr |
| 101-011 | cmp.sw | orrr |
| 110-000 | mul.uw | orrr |
| 110-001 | mul.sw | orrr |
| 111-000 | div.uw | orrr |
| 111-001 | div.sw | orrr |
| 111-010 | rem.uw | orrr |
| 111-011 | rem.sw | orrr |

### A.5 MISC-byte 子表

| minor-opcode | 助记符 | 格式 |
|-------------|--------|------|
| 001-000 | and.b | orrr |
| 001-001 | or.b | orrr |
| 001-010 | xor.b | orrr |
| 001-011 | xnor.b | orrr |
| 010-000 | ext.ub | orrr |
| 010-001 | ext.sb | orrr |
| 010-010 | shr.ub | orrr |
| 010-011 | shr.sb | orrr |
| 010-100 | shl.ub | orrr |
| 011-000 | ext.ub | orri |
| 011-001 | ext.sb | orri |
| 011-010 | shr.ub | orri |
| 011-011 | shr.sb | orri |
| 011-100 | shl.ub | orri |
| 100-000 | add.ub | orrr |
| 100-001 | add.sb | orrr |
| 101-000 | sub.ub | orrr |
| 101-001 | sub.sb | orrr |
| 101-010 | cmp.ub | orrr |
| 101-011 | cmp.sb | orrr |
| 110-000 | mul.ub | orrr |
| 110-001 | mul.sb | orrr |
| 111-000 | div.ub | orrr |
| 111-001 | div.sb | orrr |
| 111-010 | rem.ub | orrr |
| 111-011 | rem.sb | orrr |

### A.6 MISC-RF 子表

| minor-opcode | 助记符 | 格式 |
|-------------|--------|------|
| 000-000 | ftcls | orri | orri |
| 000-001 | ft2fo | orri |
| 000-010 | ft2ft | orri |
| 000-110 | ftroot | orri | orri |
| 000-111 | ftlog | orri | orri |
| 001-000 | focls | orri | orri |
| 001-001 | fo2ft | orri |
| 001-010 | fo2fo | orri |
| 001-110 | foroot | orri | orri |
| 001-111 | folog | orri | orri |
| 010-000 | ftadd | orrr | orrr |
| 010-001 | ftsub | orrr | orrr |
| 010-010 | ftmul | orrr | orrr |
| 010-011 | ftdiv | orrr | orrr |
| 010-100 | ftrem | orrr | orrr |
| 010-101 | ftsclb | orrr | orrr |
| 010-110 | ftsgnn | orrr | orrr |
| 010-111 | ftsgnj | orrr | orrr |
| 011-000 | foadd | orrr | orrr |
| 011-001 | fosub | orrr | orrr |
| 011-010 | fomul | orrr | orrr |
| 011-011 | fodiv | orrr | orrr |
| 011-100 | forem | orrr | orrr |
| 011-101 | fosclb | orrr | orrr |
| 011-110 | fosgnn | orrr | orrr |
| 011-111 | fosgnj | orrr | orrr |
| 100-000 | ftqcmp | orrr | orrr |
| 100-001 | ftscmp | orrr | orrr |
| 101-000 | foqcmp | orrr | orrr |
| 101-001 | foscmp | orrr | orrr |
| 110-000 | ft2it | orri |
| 110-001 | ft2io | orri |
| 110-010 | ft2ut | orri |
| 110-011 | ft2uo | orri |
| 110-100 | it2ft | orri |
| 110-101 | io2ft | orri |
| 110-110 | ut2ft | orri |
| 110-111 | uo2ft | orri |
| 111-000 | fo2it | orri |
| 111-001 | fo2io | orri |
| 111-010 | fo2ut | orri |
| 111-011 | fo2uo | orri |
| 111-100 | it2fo | orri |
| 111-101 | io2fo | orri |
| 111-110 | ut2fo | orri |
| 111-111 | uo2fo | orri |

### A.7 MISC-AMO 子表

| minor-opcode | 助记符 | 格式 |
|-------------|--------|------|
| 000-000 | illi | oiii | oiii |
| 000-001 | fence | oiii | oiii |
| 010-000 | lr_nn.o | orrr |
| 010-001 | lr_nr.o | orrr |
| 010-010 | lr_an.o | orrr |
| 010-011 | lr_ar.o | orrr |
| 011-000 | sc_nn.o | orrr |
| 011-001 | sc_nr.o | orrr |
| 011-010 | sc_an.o | orrr |
| 011-011 | sc_ar.o | orrr |

---

## 附录 B：条件标志参考

### B.1 条件判断方法

SimRISC 不提供专门的标识位寄存器，根据数据寄存器所存放的数值来判断条件。[SimRISC-00 §标识位说明]

| 助记符 | 条件 | 操作数个数 | 判断方法 |
|--------|------|-----------|---------|
| N | 负数 | 1 | 第 63 位为 1 |
| NN | 非负数 | 1 | 第 63 位为 0 |
| Z | 零 | 1 | [63:0] 全为 0 |
| NZ | 非零 | 1 | [63:0] 不全为 0 |
| P | 正数 | 1 | 第 63 位为 0，且 [62:0] 不全为 0 |
| NP | 非正数 | 1 | 第 63 位为 1，或 [63:0] 全为 0 |
| EQ | 相等 | 2 | 所有位相等 |
| NE | 不相等 | 2 | 至少有一位不相等 |

### B.2 条件赋值与条件跳转对应关系

| 条件 | 条件赋值指令 | 条件跳转指令（rd） | 条件跳转指令（rb） |
|------|------------|-------------------|-------------------|
| 负数 (N) | cs.n | br.n | — |
| 非负数 (NN) | — | br.nn | — |
| 零 (Z) | cs.z | br.z | br.z |
| 非零 (NZ) | — | br.nz | br.nz |
| 正数 (P) | cs.p | br.p | — |
| 非正数 (NP) | — | br.np | — |
| 相等 (EQ) | cs.eq | br.eq | — |
| 不相等 (NE) | cs.ne | br.ne | — |

### B.3 浮点比较结果解读

浮点比较结果写入 rd 寄存器：[SimRISC-03 §浮点比较指令]

| 结果值 | 含义 | 条件判断 |
|--------|------|---------|
| 1 | rfhc > rfhd | cs.p 为真，进一步 cs.eq 与 1 比较确认 |
| 0 | rfhc = rfhd | cs.z 为真 |
| −1 | rfhc < rfhd | cs.n 为真 |
| NaN | unordered | cs.p 为真（NaN 按整型为正数），但不等于 1 |

要检测大于：先加载 1 到 rd，再与比较结果做 cs.eq。[SimRISC-03 §浮点条件赋值指令]

要检测不相等：直接用 cs.ne。[SimRISC-03 §浮点条件赋值指令]

要区分正数 1 与 NaN：确认 cs.p 为真后，检查结果是否为 1（bits[63:1]=0 且 bit0=1），否则为 NaN。[SimRISC-03 §浮点条件赋值指令]
