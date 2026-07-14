# SimRISC数据类指令

> **版本：0.4.1**（与 SimRISC-00 一致）

用户态指令

> **rd0 为目的寄存器约定**：仅双目的指令（add/sub/mul/div）允许其中一个为 rd0（丢弃对应半结果，但不能同时为 rd0）。其余所有指令的目的为 rd0 时触发 **ILLI** 异常（单目的指令丢弃唯一结果无语义）。访存类指令（ld/st）同理触发 ILLI。

## 存取类指令

装入指令是把数据从存储器带进寄存器中，进行零扩展或符号扩展。存储指令是把寄存器中的数据放入存储器中。

操作数类型有两种，一种为：`rrii`，属于单load/store类型，地址计算公式为基址寄存器 + 立即数。
另一种操作数类型为：`rrri`，属于多load/store类型，地址计算公式为基址寄存器 + 数据寄存器。

### 存取RD寄存器

单load/store类指令如下：

```simrisc
ldbs    rdha, rbhb, imms12
ldbu    rdha, rbhb, imms12
ldws    rdha, rbhb, imms12
ldwu    rdha, rbhb, imms12
ldts    rdha, rbhb, imms12
ldtu    rdha, rbhb, imms12
ldo     rdha, rbhb, imms12

stb     rdha, rbhb, imms12
stw     rdha, rbhb, imms12
stt     rdha, rbhb, imms12
sto     rdha, rbhb, imms12
```

对齐要求：`ldo`/`sto` 需 8 字节对齐，`ldts`/`stt`/`ldtu` 需 4 字节对齐，`ldws`/`stw`/`ldwu` 需 2 字节对齐，`ldbs`/`stb`/`ldbu` 无对齐要求。未对齐触发 MALIGN 异常。

限制：`rdha` 为 `rd0` 时触发 ILLI 异常。

多load/store类指令如下：

```simrisc
ldmbs   rdha, rbhb, rdhc, immu6
ldmbu   rdha, rbhb, rdhc, immu6
ldmws   rdha, rbhb, rdhc, immu6
ldmwu   rdha, rbhb, rdhc, immu6
ldmts   rdha, rbhb, rdhc, immu6
ldmtu   rdha, rbhb, rdhc, immu6
ldmo    rdha, rbhb, rdhc, immu6

stmb    rdha, rbhb, rdhc, immu6
stmw    rdha, rbhb, rdhc, immu6
stmt    rdha, rbhb, rdhc, immu6
stmo    rdha, rbhb, rdhc, immu6
```

`ldm/stm`指令处理多个寄存器的读写操作。
`rdha`用来指定第一个寄存器，`rbhb+rdhc`用来指定地址，`immu6`为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。
`ldm/stm`指令存取8位/16位/32位的数据时，每个寄存器只存放一个数据，多个数据分别使用多个连续的寄存器。
例如：`stmb rd16, rb2, rd0, 8` 是将`rd16 - rd23`这8个连续寄存器中的低8位数据，分别存放到以rb2为基址的8字节连续地址中。

限制如下：

- `rdha` 为 `rd0` 时触发 ILLI 异常
- `immu6` = 0 时触发 ILLI 异常
- `rdha + immu6 > 64`（超出 rd63）时触发 ILLI 异常，不环绕、不截断
- `ldmo`/`stmo`（64-bit）需 8 字节地址对齐；`ldmts`/`stmt`（32-bit）需 4 字节对齐；`ldmws`/`stmw`（16-bit）需 2 字节对齐；`ldmb`/`stmb`（8-bit）无对齐要求。未对齐将触发 MALIGN 异常
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
由于立即数域为16位，因此，需要指定具体的wyde的位置，分别采用 `w3/w2/w1/w0`，对应 `MSW..LSW`。

操作数类型为 `rwii`，指令如下：

```simrisc
setow   rdha, ww, immu16
setzw   rdha, ww, immu16
orw     rdha, ww, immu16
andnw   rdha, ww, immu16
```

由于rd寄存器为64位，而setow/setzw指令只设置了其中16位，两者的区别在于setow指令则将其余48位置1，setzw指令将其余48位置0。

`orw` 指令：将 `rdha` 中由 `ww` 指定的 wyde 替换为 `(rdha[wyde] | immu16)`，其余 wyde 保持不变。
`andnw` 指令：将 `rdha` 中由 `ww` 指定的 wyde 替换为 `(rdha[wyde] & ~immu16)`，其余 wyde 保持不变。

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
计算过程将首先按照补码方式扩展两个源操作数为128位，然后进行加减操作，计算结果放入`rdha`和`rdhb`中。硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

具体指令如下：

```simrisc
add     rdha, rdhb, rdhc, rdhd
sub     rdha, rdhb, rdhc, rdhd
```

`rdha` 和 `rdhb` 均可为 `rd0`（丢弃对应部分的结果），但不能**同时**为 `rd0`，也不能为同一非 `rd0` 寄存器。违反上述任一规则触发 ILLI 异常。

操作数类型 `brrr` 的 `add`/`sub` 提供带位掩码的加减运算。`bmN` 指定有效位数，仅 bits[N:0] 参与运算，目的寄存器高位符号扩展。若结果溢出（超出 bits[N:0] 表示范围），溢出部分静默丢弃。`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

```simrisc
add     bmN, rdhb, rdhc, rdhd
sub     bmN, rdhb, rdhc, rdhd
```

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

另一种操作数类型为 `brrr`，增加位掩码参数 `bmN`（N=0..63），表示 bits[N:0] 参与比较。源操作数按 bmN 截断后比较，结果（-1/0/1）写入目的寄存器 bits[N:0]，高位符号扩展。`bm63` 表示全 64 位。`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

```simrisc
cmps    bmN, rdhb, rdhc, rdhd
cmpu    bmN, rdhb, rdhc, rdhd
```

例如 `cmps bm7, rd1, rd2, rd3` 将 rd2 和 rd3 的低 8 位按有符号比较，结果写入 rd1 的低 8 位，rd1[63:8] 按符号扩展。

### 乘除操作

乘除运算都是四个操作数，操作数类型为 `rrrr`。

无符号数的乘法mulu和有符号数的乘法muls，rdhc和rdhd为源操作数，形成16字节的运算结果，分别写入rdha和rdhb中，rdha存放结果的高64位，rdhb存放结果的低64位。硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

无符号数的除法divu指令和有符号数的divs指令，被除数、除数、商和余数分别占用一个寄存器。
其中，rdhc为被除数，rdhd为除数，rdha为余数，rdhb为商。

```simrisc
muls rdha, rdhb, rdhc, rdhd
mulu rdha, rdhb, rdhc, rdhd
divu rdha, rdhb, rdhc, rdhd
divs rdha, rdhb, rdhc, rdhd
```

`rdha` 和 `rdhb` 均可为 `rd0`（丢弃对应部分的结果），但不能**同时**为 `rd0`，也不能为同一非 `rd0` 寄存器。违反上述任一规则触发 ILLI 异常。

除法指令附加规则：

- **除数为零**：触发 ILLI 异常。
- **截断方向**：`divs` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号，即 `remainder = dividend − trunc(dividend / divisor) × divisor`。
- **溢出**：`divs` 中 INT64_MIN ÷ −1 触发 ILLI 异常（唯一溢出情况，结果超出 int64_t 范围）。`divu` 不存在溢出。
- **fault 时寄存器**：精确异常，`rdha`/`rdhb` 未写入（无副作用）。
- **操作数重叠**：rrrr 格式先读全部源操作数（`rdhc`/`rdhd`）再写结果（`rdha`/`rdhb`），源值在覆盖前已捕获，行为确定。

## 逻辑运算类指令

### Logic operators：逻辑运算

逻辑运算指令需要两个源操作数，一个目的操作数。操作数类型为 `orrr`。

```simrisc
and     rdhb, rdhc, rdhd
orr     rdhb, rdhc, rdhd
xor     rdhb, rdhc, rdhd
xnor    rdhb, rdhc, rdhd
```

and指令为逻辑与运算，运算规则：全一为一，有零为零。即只有两个操作数都为1时，结果才为1，其他情况均为0；也可以说，只要有0，结果就为0。
orr指令为逻辑或运算，运算规则：全零为零，有一为一。即只有两个操作数都为0时，结果才为0，其他情况均为1；也可以说，只要有1，结果就为1。
xor指令为逻辑异或运算，运算规则：相异为一，相同为零。即两个操作数不一样时结果为1，两个操作数相同时结果为0。
xnor指令为逻辑同或运算，运算规则：相同为一，相异为零。与异或运算规则相反。即两个操作数值相同时结果为1，两个操作数不一样时结果为0。

无需提供专门的not指令，可以采用xnor指令实现相同的功能。当rdhc或rdhd为rd0时，xnor指令实现了另一操作数的64位取反的操作，即逻辑非运算。逻辑非的运算规则：一变零，零变一。即操作数为1时结果为0，操作数为0时结果为1。

### Bit manipulating：位操作指令

位操作指令需要两个源操作数，一个目的操作数。

shlu是逻辑左移，shru是逻辑右移，shrs是算数右移；hd指定移动的位数。寄存器形式的移位量取 rdhd 的低 6 位（bits[5:0]），有效移位量为 0-63。
exts是符号扩展，extz是零扩展，hd 指定高位覆盖位数（hd = 64 − 待保留的低位字段宽度）。寄存器形式的位数取 rdhd 的低 6 位（bits[5:0]）。
其中，exts相当于先逻辑左移hd位，再算数右移hd位；extz相当于先逻辑左移hd位，再逻辑右移hd位。
例如：8 位符号扩展至 64 位用 `hd=56`，16 位用 `hd=48`，32 位用 `hd=32`。

操作数类型有两种，一种是 `orrr`，还有一种是 `orri`。

```simrisc
shlu    rdhb, rdhc, rdhd
shru    rdhb, rdhc, rdhd
shrs    rdhb, rdhc, rdhd

exts    rdhb, rdhc, rdhd
extz    rdhb, rdhc, rdhd

shlu    rdhb, rdhc, immu6
shru    rdhb, rdhc, immu6
shrs    rdhb, rdhc, immu6

exts    rdhb, rdhc, immu6
extz    rdhb, rdhc, immu6
```
