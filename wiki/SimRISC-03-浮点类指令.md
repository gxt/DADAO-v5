# SimRISC浮点类指令

> **版本：0.5.1**（与 SimRISC-00 一致）

浮点格式的定义符合 IEEE754 标准。舍入模式由 rf0[17:16] 控制，异常标志在 rf0[4:0]，FPEXCP 触发条件见 AEE §浮点。

> **rf0 为目的寄存器约定**：rf0 = FCSR。rf ld/st 中 rf0 为目的时允许，写只读位时静默忽略，rw 位正常写入。浮点运算指令的目的或任一源操作数为 rf0 时触发 **ILLI** 异常（rf0 为控制和状态寄存器，不可作为普通浮点操作数参与运算）。

## 存取RF寄存器

RF寄存器分为tetra和octa两种情况，tetra为32位，octa为64位，对应单精和双精两种情况，共有8条指令如下：

```simrisc
ld.t    rfha, rbhb, imms12
st.t    rfha, rbhb, imms12
ld.o    rfha, rbhb, imms12
st.o    rfha, rbhb, imms12

ldm.t   rfha, rbhb, rdhc, immu6
stm.t   rfha, rbhb, rdhc, immu6
ldm.o   rfha, rbhb, rdhc, immu6
stm.o   rfha, rbhb, rdhc, immu6
```

对齐要求：`ld.o`/`st.o`/`ldm.o`/`stm.o` 需 8 字节对齐，`ld.t`/`st.t`/`ldm.t`/`stm.t` 需 4 字节对齐。未对齐触发 MALIGN 异常。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
- `rfha + immu6 > 64`（超出 rf63）时触发 ILLI 异常

## 寄存器组之间块赋值

不同寄存器组或相同寄存器组之间，可以互相进行块传输，块传输过程中不进行数据类型的转换，保持64位二进制不变，但是必需是多个连续的寄存器。
操作数类型为 `orri`，指令如下：

```simrisc
rf2rd   rdhb, rfhc, immu6
rd2rf   rfhb, rdhc, immu6
rf2rf   rfhb, rfhc, immu6
```

指令语义为，将hc开始的immu6个寄存器复制到hb开始的immu6个寄存器中。
immu6为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常

## 立即数常数赋值：Immediate constant

针对rf寄存器，SimRISC提供了set.w指令，操作数类型为 `rwii` ，指令如下：

```simrisc
set.w    rfha, wpN, immu16
```

set.w指令只设置相应的16位，其余48位不变。
因此，32位单精浮点需要两条指令设置立即数的值，而64位双精浮点则需要四条指令进行设置。

## 格式转换指令

格式转换指令是不同格式的数据之间的转换，操作数类型为 `orri`，指令如下：

```simrisc
ft2fo   rfhb, rfhc, immu6
fo2ft   rfhb, rfhc, immu6

ft2it   rdhb, rfhc, immu6
ft2io   rdhb, rfhc, immu6
ft2ut   rdhb, rfhc, immu6
ft2uo   rdhb, rfhc, immu6

it2ft   rfhb, rdhc, immu6
io2ft   rfhb, rdhc, immu6
ut2ft   rfhb, rdhc, immu6
uo2ft   rfhb, rdhc, immu6

fo2it   rdhb, rfhc, immu6
fo2io   rdhb, rfhc, immu6
fo2ut   rdhb, rfhc, immu6
fo2uo   rdhb, rfhc, immu6

it2fo   rfhb, rdhc, immu6
io2fo   rfhb, rdhc, immu6
ut2fo   rfhb, rdhc, immu6
uo2fo   rfhb, rdhc, immu6
```

其中it表示32位有符号整数，io表示64位有符号整数，ut表示32位无符号整数，uo表示64位无符号整数，ft表示32位单精浮点数，fo表示64位双精浮点数。immu6 指定连续转换的寄存器数量（1-63）。例如 `ft2fo rf4, rf8, 3` 将 rf8→rf4、rf9→rf5、rf10→rf6。源和目的寄存器范围可以重叠，转换按序号递增逐对进行，先读后写。重叠时行为依赖顺序，使用者应避免在同一寄存器同时出现在源和目的中。

浮点格式转换遵循 IEEE 754 标准：浮点→浮点（fo2ft/ft2fo）溢出返回 ±Inf（设置 OF），下溢按舍入模式处理（设置 UF），NaN 传播 payload。整数→浮点转换可能 inexact（精度损失）。浮点→整数转换中 NaN/Inf/超出范围返回整型饱和值（最大/最小），设置 NV 标志。sNaN 作为算术输入时设置 NV 并返回 qNaN。舍入模式由 rf0[17:16] 控制，异常标志在 rf0[4:0]。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常

## 浮点运算指令

根据操作数不同，浮点运算类指令可以分为以下几种：

### S2D1

一种是两个源操作数，一个目的操作数，即操作数类型为 `orrr`：

```simrisc
ftadd   rfhb, rfhc, rfhd
ftsub   rfhb, rfhc, rfhd
ftmul   rfhb, rfhc, rfhd
ftdiv   rfhb, rfhc, rfhd
ftrem   rfhb, rfhc, rfhd
ftsclb  rfhb, rfhc, rfhd

foadd   rfhb, rfhc, rfhd
fosub   rfhb, rfhc, rfhd
fomul   rfhb, rfhc, rfhd
fodiv   rfhb, rfhc, rfhd
forem   rfhb, rfhc, rfhd
fosclb  rfhb, rfhc, rfhd
```

其中，rfhb为目的操作数，rfhc和rfhd分别为第一个源操作数和第二个源操作数。硬件先读全部源操作数再写结果，源寄存器被目的覆盖前其值已捕获，行为确定。

`ftrem`/`forem` 为 IEEE 754 remainder 操作（`rfhc − n × rfhd`，n 为最接近 `rfhc/rfhd` 的整数，平局取偶数）。除数为零、Inf 或 NaN 行为遵循 IEEE 754。

`ftsclb`/`fosclb` 为 IEEE 754 scaleB 操作：计算 `rfhc × 2^rfhd`（rfhd 取整数值），舍入模式由 rf0 控制。NaN/Inf/溢出/下溢行为遵循 IEEE 754。

### S3D1

第二类浮点运算指令的操作数类型为`rrrr`：

```simrisc
ftmadd  rfha, rfhb, rfhc, rfhd
fomadd  rfha, rfhb, rfhc, rfhd
```

其中，rfha为目的操作数，其余三个为源操作数，实现`fusedMultiplyAdd(rfhb, rfhc, rfhd)`运算，即$rfha = rfhb \times rfhc + rfhd$。融合乘加为单次舍入（标准 FMA）。硬件先读全部源操作数再写结果。

### S1D1

还有一种是一个源操作数，一个目的操作数，操作数类型为 `orri`。

```simrisc
ftroot  rfhb, rfhc, immu6
ftlog   rfhb, rfhc, immu6

foroot  rfhb, rfhc, immu6
folog   rfhb, rfhc, immu6
```

ftroot和foroot指令用来实现`rootn(x, n)`运算，其中 n 的值存放在 immu6 中。支持的 n 值：`2`（平方根）、`3`（立方根）。不支持的 n 值触发 ILLI 异常。

> 注意：当 n=2 时，`ftroot/foroot` 的运算基本等同于 `ftsqrt/fosqrt`，但是在 IEEE754-2019 中特意指出，`rootn(-0, 2)` 不等于 `squareRoot(-0)`，因此，对于 `rootn(-0, 2)` 的运算结果不做具体要求。

ftlog和folog指令用来实现对数运算，底（base）存放在 immu6 中。支持的底值：`2`（log2）、`e`（自然对数，immu6=1 约定）、`10`（log10，immu6=0 约定）。不支持的底值触发 ILLI 异常。

S1D1 指令硬件先读源操作数再写结果，源被覆盖前其值已捕获，行为确定。

## 浮点符号位操作指令

该类指令实现了浮点sign-injection指令，操作数类型为 `orrr`。

```simrisc
ftsgnj  rfhb, rfhc, rfhd
fosgnj  rfhb, rfhc, rfhd
ftsgnn  rfhb, rfhc, rfhd
fosgnn  rfhb, rfhc, rfhd
```

其中，rfhb为目的操作数，rfhc和rfhd为源操作数。
ftsgnj和fosgnj指令实现`copySign(rfhc, rfhd)`运算，即读取rfhc的除符号位之外的所有位数，和rfhd的符号位组合获得结果，写入rfhb。
ftsgnn和fosgnn指令是读取rfhc的除符号位之外的所有位数，和rfhd的符号位取反，组合获得结果，写入rfhb。

硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

该类指令的几个特例如下：

- 当rfhd为rf0时，ftsgnj和fosgnj实现了`abs(rfhc)`操作
- 当rfhd为rf0时，ftsgnn和fosgnn实现了`-abs(rfhc)`操作
- 当rfhc与rfhd相等时，ftsgnj和fosgnj实现了`copy(rfhc)`操作
- 当rfhc与rfhd相等时，ftsgnn和fosgnn实现了`negate(rfhc)`操作

## 浮点比较指令

浮点比较运算，参与比较运算的两个浮点数存放在rfhc和rfhd中，比较结果存放在rdhb中。操作数类型为 `orrr`。

```simrisc
ftqcmp  rdhb, rfhc, rfhd
ftscmp  rdhb, rfhc, rfhd

foqcmp  rdhb, rfhc, rfhd
foscmp  rdhb, rfhc, rfhd
```

rdhb中的比较结果有四种情况：

- 1：`rfhc > rfhd`
- 0：`rfhc = rfhd`
- -1：`rfhc < rfhd`
- NaN：unordered，Quiet Compare的结果为qNaN（符号位为0），Signaling Compare的结果为sNaN（符号位为0）

由于qNaN和sNaN的二进制数据按整型看是正数，因此，可以用零和负数的条件立刻判断出Equal/NotEqual/Less/NotLess/LessEqual/GreaterUnordered六种关系，而当rdhb的结果为正数则需要进一步判断结果数据是否为1，才能得出Unordered和Greater分开进行判断的结果。

## 浮点条件赋值指令

第一类浮点条件赋值指令需要先根据`rdha`的内容进行条件判断，然后分别将`rfhc`或`rfhd`赋值给`rfhb`，即 `if (rdha is negative/zero/positive) rfhb = rfhc; else rfhb = rfhd`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.n    rdha, rfhb, rfhc, rfhd
cs.z    rdha, rfhb, rfhc, rfhd
cs.p    rdha, rfhb, rfhc, rfhd
```

第二类浮点条件赋值指令需要先判断`rdhb`的内容是否为`1`，如果条件成立则将`rfhd`的值赋值给`rfhc`，即 `if (rdhb ==/!= 1) rfhc = rfhd`。
操作数类型为 `orrr`，指令如下：

```simrisc
cs.p1   rdhb, rfhc, rfhd
cs.np1  rdhb, rfhc, rfhd
```

注意：第二类浮点条件赋值指令中判断的是否为正数1，需要判断其余63位是否为0，对应了浮点比较指令中`rfhc > rfhd`的比较结果。

## 浮点分类指令

对浮点数进行判断分类，并将分类结果写入数据寄存器。
操作数类型为`orri`，指令如下：

```simrisc
ftcls   rdhb, rfhc, 1
focls   rdhb, rfhc, 1
```

根据rfhc的浮点数据分类，该指令设置rdhb中的相应位，并将其他位清零，包括[63..10]全部清零。

| 类别位 | 含义 |
| ---   | ---               |
| 0     | negativeInfinity  |
| 1     | negativeNormal    |
| 2     | negativeSubnormal |
| 3     | negativeZero      |
| 4     | positiveZero      |
| 5     | positiveSubnormal |
| 6     | positiveNormal    |
| 7     | positiveInfinity  |
| 8     | signalingNaN      |
| 9     | quietNaN          |
