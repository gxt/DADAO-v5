# SimRISC浮点运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：浮点运算 [deferred]**（46 条）— fo/ft 运算、格式转换、比较、符号位操作、条件赋值、分类

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 浮点运算（46 条）｜ **deferred** — 待浮点专门任务

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `fo2fo` | `orri` | `rf` | `fo2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2fo_orri_rf` |
| `fo2ft` | `orri` | `rf` | `fo2ft {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2ft_orri_rf` |
| `fo2io` | `orri` | `rf` | `fo2io {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2io_orri_rf` |
| `fo2it` | `orri` | `rf` | `fo2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2it_orri_rf` |
| `fo2uo` | `orri` | `rf` | `fo2uo {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2uo_orri_rf` |
| `fo2ut` | `orri` | `rf` | `fo2ut {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2ut_orri_rf` |
| `foadd` | `orrr` | `rf` | `foadd rfHB, rfHC, rfHD` | `foadd_orrr_rf` |
| `focls` | `orri` | `rf` | `focls rdHB, rfHC, immu6` | `focls_orri_rf` |
| `fodiv` | `orrr` | `rf` | `fodiv rfHB, rfHC, rfHD` | `fodiv_orrr_rf` |
| `folog` | `orri` | `rf` | `folog rfHB, rfHC, immu6` | `folog_orri_rf` |
| `fomul` | `orrr` | `rf` | `fomul rfHB, rfHC, rfHD` | `fomul_orrr_rf` |
| `foqcmp` | `orrr` | `rf` | `foqcmp rdHB, rfHC, rfHD` | `foqcmp_orrr_rf` |
| `forem` | `orrr` | `rf` | `forem rfHB, rfHC, rfHD` | `forem_orrr_rf` |
| `foroot` | `orri` | `rf` | `foroot rfHB, rfHC, immu6` | `foroot_orri_rf` |
| `fosclb` | `orrr` | `rf` | `fosclb rfHB, rfHC, rfHD` | `fosclb_orrr_rf` |
| `foscmp` | `orrr` | `rf` | `foscmp rdHB, rfHC, rfHD` | `foscmp_orrr_rf` |
| `fosgnj` | `orrr` | `rf` | `fosgnj rfHB, rfHC, rfHD` | `fosgnj_orrr_rf` |
| `fosgnn` | `orrr` | `rf` | `fosgnn rfHB, rfHC, rfHD` | `fosgnn_orrr_rf` |
| `fosub` | `orrr` | `rf` | `fosub rfHB, rfHC, rfHD` | `fosub_orrr_rf` |
| `ft2fo` | `orri` | `rf` | `ft2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2fo_orri_rf` |
| `ft2ft` | `orri` | `rf` | `ft2ft {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2ft_orri_rf` |
| `ft2io` | `orri` | `rf` | `ft2io {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2io_orri_rf` |
| `ft2it` | `orri` | `rf` | `ft2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2it_orri_rf` |
| `ft2uo` | `orri` | `rf` | `ft2uo {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2uo_orri_rf` |
| `ft2ut` | `orri` | `rf` | `ft2ut {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2ut_orri_rf` |
| `ftadd` | `orrr` | `rf` | `ftadd rfHB, rfHC, rfHD` | `ftadd_orrr_rf` |
| `ftcls` | `orri` | `rf` | `ftcls rdHB, rfHC, immu6` | `ftcls_orri_rf` |
| `ftdiv` | `orrr` | `rf` | `ftdiv rfHB, rfHC, rfHD` | `ftdiv_orrr_rf` |
| `ftlog` | `orri` | `rf` | `ftlog rfHB, rfHC, immu6` | `ftlog_orri_rf` |
| `ftmul` | `orrr` | `rf` | `ftmul rfHB, rfHC, rfHD` | `ftmul_orrr_rf` |
| `ftqcmp` | `orrr` | `rf` | `ftqcmp rdHB, rfHC, rfHD` | `ftqcmp_orrr_rf` |
| `ftrem` | `orrr` | `rf` | `ftrem rfHB, rfHC, rfHD` | `ftrem_orrr_rf` |
| `ftroot` | `orri` | `rf` | `ftroot rfHB, rfHC, immu6` | `ftroot_orri_rf` |
| `ftsclb` | `orrr` | `rf` | `ftsclb rfHB, rfHC, rfHD` | `ftsclb_orrr_rf` |
| `ftscmp` | `orrr` | `rf` | `ftscmp rdHB, rfHC, rfHD` | `ftscmp_orrr_rf` |
| `ftsgnj` | `orrr` | `rf` | `ftsgnj rfHB, rfHC, rfHD` | `ftsgnj_orrr_rf` |
| `ftsgnn` | `orrr` | `rf` | `ftsgnn rfHB, rfHC, rfHD` | `ftsgnn_orrr_rf` |
| `ftsub` | `orrr` | `rf` | `ftsub rfHB, rfHC, rfHD` | `ftsub_orrr_rf` |
| `io2fo` | `orri` | `rf` | `io2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `io2fo_orri_rf` |
| `io2ft` | `orri` | `rf` | `io2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `io2ft_orri_rf` |
| `it2fo` | `orri` | `rf` | `it2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `it2fo_orri_rf` |
| `it2ft` | `orri` | `rf` | `it2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `it2ft_orri_rf` |
| `uo2fo` | `orri` | `rf` | `uo2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `uo2fo_orri_rf` |
| `uo2ft` | `orri` | `rf` | `uo2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `uo2ft_orri_rf` |
| `ut2fo` | `orri` | `rf` | `ut2fo {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `ut2fo_orri_rf` |
| `ut2ft` | `orri` | `rf` | `ut2ft {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `ut2ft_orri_rf` |

<!-- ASSEMBLY_LIST_END -->

浮点格式的定义符合 IEEE754 标准。舍入模式由 rf0[17:16] 控制，异常标志在 rf0[4:0]。浮点指令执行后，异常状态位（NV/DZ/OF/UF/NX）由硬件设置，软件可通过读取 rf0 检查异常状态。

## 格式转换指令

格式转换指令包括不同格式之间以及同格式之间的数据转换，操作数类型为 `orri`，指令如下：

```simrisc
ft2fo   rfhb, rfhc, immu6
fo2ft   rfhb, rfhc, immu6

ft2ft   rfhb, rfhc, immu6          ; 浮点寄存器间搬移
fo2fo   rfhb, rfhc, immu6          ; 浮点寄存器间搬移

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

> **注**：rf0 为目的寄存器时的特殊行为见 SimRISC-00。浮点寄存器的读写（ld/st/ldm/stm 的 rf 形式、cs.*-rf、rd2rf/rf2rd、set.w-rf）见 SimRISC-01、SimRISC-02 和 SimRISC-03。