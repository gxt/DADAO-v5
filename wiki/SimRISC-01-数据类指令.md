# SimRISC数据类指令

> **版本：0.5.1**（与 SimRISC-00 一致）

用户态指令

> **rd0 为目的寄存器约定**：仅双目的指令（add.uo/add.so/sub.uo/sub.so/mulu/muls 的 rrrr 格式）允许其中一个为 rd0（丢弃对应半结果，但不能同时为 rd0）。其余所有指令的目的为 rd0 时触发 **ILLI** 异常（单目的指令丢弃唯一结果无语义）。访存类指令（ld/st）同理触发 ILLI。

## 存取类指令

装入指令是把数据从存储器带进寄存器中，进行零扩展或符号扩展。存储指令是把寄存器中的数据放入存储器中。

操作数类型有两种，一种为：`rrii`，属于单load/store类型，地址计算公式为基址寄存器 + 立即数。
另一种操作数类型为：`rrri`，属于多load/store类型，地址计算公式为基址寄存器 + 数据寄存器。

### 存取RD寄存器

单load/store类指令如下：

```simrisc
ld.sb    rdha, rbhb, imms12
ld.ub    rdha, rbhb, imms12
ld.sw    rdha, rbhb, imms12
ld.uw    rdha, rbhb, imms12
ld.st    rdha, rbhb, imms12
ld.ut    rdha, rbhb, imms12
ld.o     rdha, rbhb, imms12

st.b     rdha, rbhb, imms12
st.w     rdha, rbhb, imms12
st.t     rdha, rbhb, imms12
st.o     rdha, rbhb, imms12
```

对齐要求：`ld.o`/`st.o` 需 8 字节对齐，`ld.st`/`st.t`/`ld.ut` 需 4 字节对齐，`ld.sw`/`st.w`/`ld.uw` 需 2 字节对齐，`ld.sb`/`st.b`/`ld.ub` 无对齐要求。未对齐触发 MALIGN 异常。

限制：`rdha` 为 `rd0` 时触发 ILLI 异常。

多load/store类指令如下：

```simrisc
ldm.sb   rdha, rbhb, rdhc, immu6
ldm.ub   rdha, rbhb, rdhc, immu6
ldm.sw   rdha, rbhb, rdhc, immu6
ldm.uw   rdha, rbhb, rdhc, immu6
ldm.st   rdha, rbhb, rdhc, immu6
ldm.ut   rdha, rbhb, rdhc, immu6
ldm.o    rdha, rbhb, rdhc, immu6

stm.b    rdha, rbhb, rdhc, immu6
stm.w    rdha, rbhb, rdhc, immu6
stm.t    rdha, rbhb, rdhc, immu6
stm.o    rdha, rbhb, rdhc, immu6
```

`ldm/stm`指令处理多个寄存器的读写操作。
`rdha`用来指定第一个寄存器，`rbhb+rdhc`用来指定地址，`immu6`为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。
`ldm/stm`指令存取8位/16位/32位的数据时，每个寄存器只存放一个数据，多个数据分别使用多个连续的寄存器。
例如：`stm.b rd16, rb2, rd0, 8` 是将`rd16 - rd23`这8个连续寄存器中的低8位数据，分别存放到以rb2为基址的8字节连续地址中。

限制如下：

- `rdha` 为 `rd0` 时触发 ILLI 异常
- `immu6` = 0 时触发 ILLI 异常
- `rdha + immu6 > 64`（超出 rd63）时触发 ILLI 异常，不环绕、不截断
- `ldm.o`/`stm.o`（64-bit）需 8 字节地址对齐；`ldm.st`/`stm.t`/`ldm.ut`（32-bit）需 4 字节对齐；`ldm.sw`/`stm.w`/`ldm.uw`（16-bit）需 2 字节对齐；`ldm.sb`/`stm.b`/`ldm.ub`（8-bit）无对齐要求。未对齐将触发 MALIGN 异常
- 当多寄存器读写的范围包括`rdhc`时，地址计算仍然按照原始的`rdhc`中的数据进行
- 装入类指令的源寄存器范围与目的寄存器范围可以重叠。硬件按序号递增逐对处理，每对先读后写。重叠时行为依赖顺序，使用者应避免在同一寄存器同时出现在源和目的中

## 赋值类指令

### 寄存器组之间块赋值

不同寄存器组或相同寄存器组之间，可以互相进行块传输，块传输过程中不进行数据类型的转换，保持64位二进制不变，但是必需是多个连续的寄存器。
操作数类型为 `orri`，指令如下：

```simrisc
rd2rd   rdhb, rdhc, immu6
```

以 `rd2rd` 为例，指令语义为，将 rdhc 开始的 immu6 个寄存器复制到 rdhb 开始的 immu6 个寄存器中。
immu6为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- `rdhb` 为 `rd0` 时触发 ILLI 异常（目的寄存器不可为 rd0）
- `rdhb + immu6 > 64` 时触发 ILLI 异常（超出 rd63）
- `rdhc + immu6 > 64` 时触发 ILLI 异常（源超出 rd63）
- 源和目的寄存器范围可以重叠。硬件按序号递增逐对处理，每对先读后写

### 立即数常数赋值：Immediate constant

立即数设置类指令直接用立即数对寄存器内的不同wyde进行赋值、或、与非、零扩展赋值。
由于立即数域为16位，因此，需要指定具体的wyde的位置，分别采用 `wp3/wp2/wp1/wp0`，对应 `MSW..LSW`。

操作数类型为 `rwii`，指令如下：

```simrisc
set.ow   rdha, wpN, immu16
set.zw   rdha, wpN, immu16
or.w     rdha, wpN, immu16
andn.w   rdha, wpN, immu16
```

由于rd寄存器为64位，而set.ow/set.zw指令只设置了其中16位，两者的区别在于set.ow指令则将其余48位置1，set.zw指令将其余48位置0。

`or.w` 指令：将 `rdha` 中由 `wpN` 指定的 wyde 替换为 `(rdha[wyde] | immu16)`，其余 wyde 保持不变。
`andn.w` 指令：将 `rdha` 中由 `wpN` 指定的 wyde 替换为 `(rdha[wyde] & ~immu16)`，其余 wyde 保持不变。

### 条件赋值：Conditional Assignment

第一类条件赋值指令需要先根据`rdha`的内容进行条件判断，然后分别将`rdhc`或`rdhd`赋值给`rdhb`，即 `if (rdha is negative/zero/positive) rdhb = rdhc; else rdhb = rdhd`。
操作数类型为 `rrrr`，指令如下：

```simrisc
csn     rdha, rdhb, rdhc, rdhd
csz     rdha, rdhb, rdhc, rdhd
csp     rdha, rdhb, rdhc, rdhd
```

第二类条件赋值指令需要先根据`rdha`与`rdhb`是否相等进行条件判断，如果条件成立则将`rdhd`的值赋值给`rdhc`，即 `if (rdha ==/!= rdhb) rdhc = rdhd`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cseq    rdha, rdhb, rdhc, rdhd
csne    rdha, rdhb, rdhc, rdhd
```

### 算术运算类指令

### 加减操作

加减操作需要两个源操作数，一个目的操作数。
操作数类型为 `rrrr`。
两个源操作数寄存器为`rdhc`和`rdhd`。
目的操作数可能超出64位，故采用两个寄存器存放目的操作数，即`rdha`和`rdhb`，`rdha`存放结果的高64位，`rdhb`存放结果的低64位。
硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

根据操作数的符号类型，`add`/`sub` 分为两个变体：

- **`add.uo`/`sub.uo`**（无符号）：源操作数按**零扩展**（ZX）至 128 位，适合无符号多字加法链，`rdha` 为进位/借位（0 或 1）。
- **`add.so`/`sub.so`**（有符号，默认）：源操作数按**符号扩展**（SX）至 128 位，适合有符号 128 位运算。

```simrisc
add.uo  rdha, rdhb, rdhc, rdhd    ; ZX，rdha = 进位
add.so  rdha, rdhb, rdhc, rdhd    ; SX，rdha = 高64位
sub.uo  rdha, rdhb, rdhc, rdhd    ; ZX，rdha = 借位
sub.so  rdha, rdhb, rdhc, rdhd    ; SX，rdha = 高64位
```

`rdha` 和 `rdhb` 均可为 `rd0`（丢弃对应部分的结果），但不能**同时**为 `rd0`，也不能为同一非 `rd0` 寄存器。违反上述任一规则触发 ILLI 异常。

MISC-byte/wyde/tetra/octa 子表中的 `add`/`sub`（后缀 `.b`/`.w`/`.t`/`.o`）提供四种固定位宽的加减运算。仅 size 范围内的低位参与运算，目的寄存器高位符号扩展。若结果溢出，溢出部分静默丢弃。操作数格式为 `orrr`，`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 位约束 |
|------|------|---------|--------|
| `add.b`/`sub.b` | 8 位 | `add.b rdhb, rdhc, rdhd` | bits[7:0] 参与运算 |
| `add.w`/`sub.w` | 16 位 | `add.w rdhb, rdhc, rdhd` | bits[15:0] 参与运算 |
| `add.t`/`sub.t` | 32 位 | `add.t rdhb, rdhc, rdhd` | bits[31:0] 参与运算 |
| `add.o`/`sub.o` | 64 位 | `add.o rdhb, rdhc, rdhd` | bits[63:0] 全 64 位 |

### 自增自减

自增自减指令需要两个源操作数，一个目的操作数。
操作数类型是 `rrii`，立即数为12位有符号数，虽然有位数限制，但是具有很好的便利性。
由于立即数采用补码的编码方式，无需区分加减操作。
具体指令如下：

```simrisc
addi    rdha, rdhb, imms12
```

注意，采用这种操作数类型的加法指令，无法判断是否溢出。
由于imms12为有符号数，该加法指令也隐含实现了减法指令。

### 比较操作

比较操作需要通过指令编码区分数据类型，对于整型，主要区分的是有符号数和无符号数。
比较操作会根据两个源操作数的比较结果，小于、等于、大于，分别设置目的操作数为-1、0、1。
后续的指令可以根据负数、非负数、零、非零、正数、非正数做出组合判断。

操作数类型为 `rrii`。
具体指令如下：

```simrisc
cmps    rdha, rdhb, imms12
cmpu    rdha, rdhb, immu12
```

MISC-byte/wyde/tetra/octa 子表中的 `cmp.s`/`cmp.u`（后缀 `.sb`/`.ub`/`.sw`/`.uw`/`.st`/`.ut`/`.so`/`.uo`）提供四种固定位宽的比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ub`/`cmp.sb` | 8 位 | `cmp.ub rdhb, rdhc, rdhd` | bits[7:0] |
| `cmp.uw`/`cmp.sw` | 16 位 | `cmp.uw rdhb, rdhc, rdhd` | bits[15:0] |
| `cmp.ut`/`cmp.st` | 32 位 | `cmp.ut rdhb, rdhc, rdhd` | bits[31:0] |
| `cmp.uo`/`cmp.so` | 64 位 | `cmp.uo rdhb, rdhc, rdhd` | bits[63:0] 全 64 位 |

例如 `cmp.sb rd1, rd2, rd3` 将 rd2 和 rd3 的低 8 位按有符号比较，结果写入 rd1。

### 乘除操作

乘除运算都是四个操作数，操作数类型为 `rrrr`。

无符号数的乘法mulu和有符号数的乘法muls，rdhc和rdhd为源操作数，形成16字节的运算结果，分别写入rdha和rdhb中，rdha存放结果的高64位，rdhb存放结果的低64位。硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

```simrisc
muls rdha, rdhb, rdhc, rdhd
mulu rdha, rdhb, rdhc, rdhd
```

`rdha` 和 `rdhb` 均可为 `rd0`（丢弃对应部分的结果），但不能**同时**为 `rd0`，也不能为同一非 `rd0` 寄存器。违反上述任一规则触发 ILLI 异常。

MISC-byte/wyde/tetra/octa 子表中的 `mul`/`div`/`rem` 提供四种固定位宽的乘除余运算。`mul` 后缀为 `.ub`/`.sb`/`.uw`/`.sw`/`.ut`/`.st`/`.o`（octa 乘法低 64 位与符号无关，无需区分 s/u）；`div`/`rem` 后缀为 `.ub`/`.sb`/`.uw`/`.sw`/`.ut`/`.st`/`.uo`/`.so`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ub`/`mul.sb`/`div.ub`/`div.sb`/`rem.ub`/`rem.sb` | 8 位 | `mul.ub rdhb, rdhc, rdhd` |
| `mul.uw`/`mul.sw`/`div.uw`/`div.sw`/`rem.uw`/`rem.sw` | 16 位 | `mul.uw rdhb, rdhc, rdhd` |
| `mul.ut`/`mul.st`/`div.ut`/`div.st`/`rem.ut`/`rem.st` | 32 位 | `mul.ut rdhb, rdhc, rdhd` |
| `mul.o`/`div.uo`/`div.so`/`rem.uo`/`rem.so` | 64 位 | `mul.o rdhb, rdhc, rdhd` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零**：触发 ILLI 异常。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出**：`div.s` 中各 size 对应的 INT_MIN ÷ −1 触发 ILLI 异常（byte: −128 ÷ −1，wyde: −32768 ÷ −1，tetra: −2147483648 ÷ −1，octa: −9223372036854775808 ÷ −1）。`div.u`/`rem.u` 不存在溢出。
- **fault 时寄存器**：精确异常，目的寄存器未写入（无副作用）。

## 逻辑运算类指令

### Logic operators：逻辑运算

逻辑运算指令需要两个源操作数，一个目的操作数。MISC-byte/wyde/tetra/octa 子表中的 `and`/`orr`/`xor`/`xnor`（后缀 `.b`/`.w`/`.t`/`.o`）提供四种固定位宽的逻辑运算。操作数格式为 `orrr`。

| 指令 | 位宽 | 汇编语法 | 操作范围 |
|------|------|---------|---------|
| `and.b`/`orr.b`/`xor.b`/`xnor.b` | 8 位 | `and.b rdhb, rdhc, rdhd` | bits[7:0] 参与运算，bits[63:8] 不变 |
| `and.w`/`orr.w`/`xor.w`/`xnor.w` | 16 位 | `and.w rdhb, rdhc, rdhd` | bits[15:0] 参与运算，bits[63:16] 不变 |
| `and.t`/`orr.t`/`xor.t`/`xnor.t` | 32 位 | `and.t rdhb, rdhc, rdhd` | bits[31:0] 参与运算，bits[63:32] 不变 |
| `and.o`/`orr.o`/`xor.o`/`xnor.o` | 64 位 | `and.o rdhb, rdhc, rdhd` | bits[63:0] 全 64 位参与运算 |

and指令为逻辑与运算，运算规则：全一为一，有零为零。即只有两个操作数都为1时，结果才为1，其他情况均为0；也可以说，只要有0，结果就为0。
orr指令为逻辑或运算，运算规则：全零为零，有一为一。即只有两个操作数都为0时，结果才为0，其他情况均为1；也可以说，只要有1，结果就为1。
xor指令为逻辑异或运算，运算规则：相异为一，相同为零。即两个操作数不一样时结果为1，两个操作数相同时结果为0。
xnor指令为逻辑同或运算，运算规则：相同为一，相异为零。与异或运算规则相反。即两个操作数值相同时结果为1，两个操作数不一样时结果为0。

以上四条逻辑运算指令在 size 范围外的高位（`.b`: bits[63:8]，`.w`: bits[63:16]，`.t`: bits[63:32]）保持目的寄存器原有值不变。

无需提供专门的not指令，可以采用xnor指令实现相同的功能。当rdhc或rdhd为rd0时，xnor指令实现了另一操作数的64位取反的操作，即逻辑非运算。逻辑非的运算规则：一变零，零变一。即操作数为1时结果为0，操作数为0时结果为1。

### Bit manipulating：位操作指令

位操作指令需要两个源操作数，一个目的操作数。

`shl` 是左移，`shr` 是右移，后缀中的 `s` 表示算术移位（符号扩展）、`u` 表示逻辑移位（零扩展）。MISC-byte/wyde/tetra/octa 子表中的 `shl`/`shr`（后缀 `.ub`/`.sb`/`.uw`/`.sw`/`.ut`/`.st`/`.uo`/`.so`）提供四种固定位宽的移位操作。移位量（shamt）取 `rdhd` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

```
shl.u: rdhb[N:0]   = (rdhc[N:0] << shamt)                // 左移，低位补零
shr.u: rdhb[N:0]   = (rdhc[N:0] >> shamt)                // 逻辑右移，高位补零
shr.s: rdhb[N:0]   = (rdhc[N:0] >> shamt) with sign(N)   // 算术右移，高位补 rdhc[N]
rdhb[63:N+1] = rdhb[63:N+1]                               // 高位不变
```

其中 N 由位宽决定。shamt 和 N 的对应关系如下：

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.ub`/`shr.sb`/`shr.ub` | 7 | 0-7 | hd[2:0]，hd[5:3] 应为零 |
| `shl.uw`/`shr.sw`/`shr.uw` | 15 | 0-15 | hd[3:0]，hd[5:4] 应为零 |
| `shl.ut`/`shr.st`/`shr.ut` | 31 | 0-31 | hd[4:0]，hd[5] 应为零 |
| `shl.uo`/`shr.so`/`shr.uo` | 63 | 0-63 | hd[5:0] 全有效 |

`shamt > N` 触发 ILLI。

`ext.s` 是符号扩展，`ext.u` 是零扩展。MISC-byte/wyde/tetra/octa 子表中的 `ext.s`/`ext.u`（后缀 `.sb`/`.ub`/`.sw`/`.uw`/`.st`/`.ut`/`.so`/`.uo`）提供四种固定位宽的扩展操作。操作数格式为 `orrr`（寄存器形式，hd=扩展起始位）和 `orri`（立即数形式，hd=immu6 扩展起始位）。语义与之前一致：

```
rdhb[hd:0]   = rdhc[hd:0]                               // 复制源低位
rdhb[N:hd+1] = sign/zero_extend(rdhc[hd])                // 符号/零扩展
rdhb[63:N+1] = rdhb[63:N+1]                              // 高位不变
```

其中 N 由位宽决定（byte→7, wyde→15, tetra→31, octa→63），hd 为扩展起始位，须满足 `hd ≤ N`，否则 ILLI。

| 指令 | N | 汇编语法 | 约束 |
|------|---|---------|------|
| `ext.ub`/`ext.sb` | 7 | `ext.ub rdhb, rdhc, rdhd` 或 `ext.ub rdhb, rdhc, immu6` | hd ≤ 7 |
| `ext.uw`/`ext.sw` | 15 | `ext.uw rdhb, rdhc, rdhd` 或 `ext.uw rdhb, rdhc, immu6` | hd ≤ 15 |
| `ext.ut`/`ext.st` | 31 | `ext.ut rdhb, rdhc, rdhd` 或 `ext.ut rdhb, rdhc, immu6` | hd ≤ 31 |
| `ext.uo`/`ext.so` | 63 | `ext.uo rdhb, rdhc, rdhd` 或 `ext.uo rdhb, rdhc, immu6` | hd ≤ 63 |
