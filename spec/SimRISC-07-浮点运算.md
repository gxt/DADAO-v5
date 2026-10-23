# SimRISC浮点运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：浮点运算** — fo/ft 运算、格式转换、比较、符号位操作、条件赋值、分类、取整、最小最大值

浮点格式的定义符合 IEEE754 标准。舍入模式由 rf0[33:32] 控制，异常标志在 rf0[4:0]。浮点指令执行后，异常状态位（NV/DZ/OF/UF/NX）由硬件设置，软件可通过读取 rf0 检查异常状态。

## 1. 格式转换指令

格式转换指令包括不同格式之间以及同格式之间的数据转换，操作数类型为 `orri`，指令如下：

```simrisc
ft2fo   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}
fo2ft   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}

ft2ft   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}          @@ 浮点寄存器间搬移
fo2fo   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}          @@ 浮点寄存器间搬移

ft2it   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
ft2io   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
ft2ut   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
ft2uo   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}

it2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
io2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
ut2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
uo2ft   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}

fo2it   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
fo2io   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
fo2ut   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
fo2uo   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}

it2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
io2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
ut2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
uo2fo   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
```

其中it表示32位有符号整数，io表示64位有符号整数，ut表示32位无符号整数，uo表示64位无符号整数，ft表示32位单精浮点数，fo表示64位双精浮点数。immu6 指定连续转换的寄存器数量（1-63）。例如 `ft2fo {rf4:rf6}, {rf8:rf10}` 将 rf8→rf4、rf9→rf5、rf10→rf6。源范围与目的范围不可有任何交集（含完全重合），否则触发 ILLI 异常（与 SimRISC-02 一致）；无交集时转换按序号递增逐对进行，先读后写。

浮点格式转换遵循 IEEE 754 标准：浮点→浮点（fo2ft/ft2fo）溢出返回 ±Inf（设置 OF），下溢按舍入模式处理（设置 UF），NaN 传播 payload。整数→浮点转换可能 inexact（精度损失）。浮点→整数转换中 NaN/Inf/超出范围返回整型饱和值（最大/最小），设置 NV 标志。sNaN 作为算术输入时设置 NV 并返回 qNaN。舍入模式由 rf0[33:32] 控制，异常标志在 rf0[4:0]。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
- 源范围与目的范围有任何交集（含完全重合）时触发 ILLI 异常

## 2. 浮点运算指令

根据操作数不同，浮点运算类指令可以分为以下几种：

### 2.1 S2D1

一种是两个源操作数，一个目的操作数，即操作数类型为 `orrr`：

```simrisc
ftadd   rfHB, rfHC, rfHD
ftsub   rfHB, rfHC, rfHD
ftmul   rfHB, rfHC, rfHD
ftdiv   rfHB, rfHC, rfHD
ftrem   rfHB, rfHC, rfHD
ftsclb  rfHB, rfHC, rfHD

foadd   rfHB, rfHC, rfHD
fosub   rfHB, rfHC, rfHD
fomul   rfHB, rfHC, rfHD
fodiv   rfHB, rfHC, rfHD
forem   rfHB, rfHC, rfHD
fosclb  rfHB, rfHC, rfHD
```

其中，rfHB为目的操作数，rfHC和rfHD分别为第一个源操作数和第二个源操作数。硬件先读全部源操作数再写结果，源寄存器被目的覆盖前其值已捕获，行为确定。

`ftrem`/`forem` 为 IEEE 754 remainder 操作（`rfHC − n × rfHD`，n 为最接近 `rfHC/rfHD` 的整数，平局取偶数）。除数为零、Inf 或 NaN 行为遵循 IEEE 754。

`ftsclb`/`fosclb` 为 IEEE 754 scaleB 操作：计算 `rfHC × 2^rfHD`（rfHD 取整数值），舍入模式由 rf0 控制。NaN/Inf/溢出/下溢行为遵循 IEEE 754。

### 2.2 S1D1

还有一种是一个源操作数，一个目的操作数，操作数类型为 `orri`。

```simrisc
ftroot  rfHB, rfHC, immu6

foroot  rfHB, rfHC, immu6
```

ftroot和foroot指令用来实现`rootn(x, n)`运算，其中 n 的值存放在 immu6 中。仅支持 n=2（平方根）；其他 n 值触发 ILLI 异常。

> 注意：`ftroot/foroot` 的运算基本等同于 `ftsqrt/fosqrt`，但是在 IEEE754-2019 中特意指出，`rootn(-0, 2)` 不等于 `squareRoot(-0)`，因此，对于 `rootn(-0, 2)` 的运算结果不做具体要求。

S1D1 指令硬件先读源操作数再写结果，源被覆盖前其值已捕获，行为确定。

### 2.3 取整（roundToIntegral）

取整指令把浮点值取整为整数值（仍以同格式浮点表示），操作数类型为 `orri`；此处 `immu6`
**不是**连续寄存器个数，而是**取整模式**（6 位 one-hot：恰一位为 1）：

```simrisc
ftrnd   rfHB, rfHC, immu6
fornd   rfHB, rfHC, immu6
```

`ftrnd` 作用于 ft（32 位）、`fornd` 作用于 fo（64 位）；`rfHB` 为目的操作数、`rfHC` 为源操作数。
六种操作与 IEEE 754-2019 §5.3.1 的 `roundToIntegral` 六档**按位序一一对应**：

| `immu6` | IEEE 754-2019 操作 | 取整方向 | 置 NX |
|---|---|---|---|
| `0x01` | `roundToIntegralTiesToEven` | 就近取偶（静态） | 不置 |
| `0x02` | `roundToIntegralTiesToAway` | 就近、平局远离 0（静态） | 不置 |
| `0x04` | `roundToIntegralTowardZero` | 向 0（静态） | 不置 |
| `0x08` | `roundToIntegralTowardPositive` | 向 +∞（静态） | 不置 |
| `0x10` | `roundToIntegralTowardNegative` | 向 −∞（静态） | 不置 |
| `0x20` | `roundToIntegralExact` | 读 `rf0[33:32]`（RNE/RTZ/RDN/RUP） | **结果 ≠ 输入时置 NX** |

共同规则（IEEE 754-2019 §5.9）：

- 5 个静态方向**不受** `rf0[33:32]` 影响；只有 `0x20` 读 `rf0[33:32]`（`00` RNE / `01` RTZ / `10` RDN / `11` RUP）。
- **只有 `0x20` 置 NX**（且仅当结果 ≠ 输入）；其余 5 档**不得**置 NX。
- sNaN 作输入 ⇒ 置 NV、返回 qNaN；qNaN 作输入 ⇒ 返回 qNaN（canonical 化）。
- `|x| ≥ 2^p`（ft: p = 24；fo: p = 53）⇒ **原样返回**（此时 x 已为整数；不得用「转整数再转回」实现）。
- `±0` 的符号位保留：`trunc(-0.5) = -0`、`floor(-0.0) = -0`（取整结果为 0 时沿用输入的符号）。
- Inf 原样返回；取整**不置** OF/UF。
- 结果格式与输入相同（不做 ft↔fo 转换）。
- 目的 `rfHB = rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`（读出 FCSR 中的 qNaN）。
- `immu6` 必须 one-hot（`0x01`/`0x02`/`0x04`/`0x08`/`0x10`/`0x20` 之一）；其他取值（含 `0x00`）⇒ ILLI。

> **已知偏差（`nearbyint`）**：IEEE 754 的 `nearbyint`（取整但不置 inexact）本 ISA **不提供**硬件变体
> ⇒ 后端只能落 `0x20`（动态方向）：**值正确**，但结果 ≠ 输入时 **NX 可能被置位**。可接受性依据：本 ISA
> 浮点指令不产生异常/陷阱，NX 仅为 `rf0[4:0]` 的**状态位**（软件可忽略）；`roundToIntegral` 族与
> `nearbyint` 的**值**语义一致，差异仅在 inexact 标志。
> **`rf0[33:32]` 不扩充**：只有 4 档（RNE/RTZ/RDN/RUP），**无** `roundTiesToAway`
> ⇒ C23 `fesetround(FE_TONEARESTFROMZERO)` **不支持**（可返回失败，符合 C 标准）；
> 「平局远离 0」仅由静态档 `0x02` 提供。另：请求方向已在 `rf0[33:32]` 内的 `nearbyint`
> 变体仍落 `0x20`，其 NX 置位与 IEEE 的 `nearbyint`（不置）不同，属同一偏差。

> **范围**：语义按本节冻结。

### 2.4 最小最大值（minimumNumber / maximumNumber）

最小/最大值指令从两个同格式浮点操作数中选出较小/较大者，操作数类型为 `orrr`：

```simrisc
ftmin   rfHB, rfHC, rfHD
ftmax   rfHB, rfHC, rfHD
fomin   rfHB, rfHC, rfHD
fomax   rfHB, rfHC, rfHD
```

`ftmin`/`ftmax` 作用于 ft（32 位）、`fomin`/`fomax` 作用于 fo（64 位）；`rfHB` 为目的操作数，
`rfHC` 为第一个源操作数、`rfHD` 为第二个源操作数。硬件先读全部源操作数再写结果，源被目的覆盖前
其值已捕获，行为确定（`rfHB` 可与 `rfHC`/`rfHD` 相同）。

语义为 IEEE 754-2019 §9.6 的 **`minimumNumber`/`maximumNumber`**（**严格版**，与 RISC-V
`FMIN.S`/`FMAX.S` 逐条一致；RISC-V 2.2 起由 754-2008 的 `minNum` 改为 201x 的 `minimumNumber`）。
六条边界如下（`min` 指 `ftmin`/`fomin`，`max` 指 `ftmax`/`fomax`）：

1. **有序**（`x < y` 或 `x > y`，按数值序比较）：`min` 返回较小者、`max` 返回较大者。
2. **`−0 < +0`**（IEEE 754-2019 §9.6 对 `±0` 的定序：两者符号不同时 `min` 为 `−0`、`max` 为 `+0`）：
   `min(+0, −0) = −0`、`max(+0, −0) = +0`——**不得**把 `±0` 视为"相等而任选"，也不得返回 `+0`
   作为 `min` 的结果。
3. **相等**（`x == y` 且同号；含 `+0/+0`、`−0/−0`、相同位型）：返回任一操作数（两者位型相同，
   结果唯一）。
4. **单 NaN**（一个操作数为 NaN、另一个为数；qNaN 与 **sNaN** 同论）：返回**那个数**（不传播
   NaN）。qNaN 作输入**不置**标志；**sNaN 作输入置 NV**（即使结果为数字）。
5. **双 NaN**（两个操作数均为 NaN，任意 qNaN/sNaN 组合）：返回 **canonical quiet NaN**
   （IEEE 754-2019 §6.2：符号位 0、payload 全零 ⇒ ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`，
   与 `rf0` 的复位 qNaN 位同源）；任一输入为 sNaN ⇒ 置 NV。
6. **标志与舍入**：本族**不涉舍入**（结果取某一输入的位型或其 canonical 化，不重新舍入），
   **不置 NX**；除「sNaN 作输入 ⇒ NV」外**不置**任何标志，也不置 OF/UF。Inf 按数值序参与比较
   （`min(+Inf, x) = x`、`max(−Inf, x) = x`）。

**禁止的实现（负向约束）**：

- **不得**实现为「返回第二个源操作数」（x86 `minss`/`maxss` 的遗留语义：单 NaN 返回第二源、
  双 NaN 返回第二源）——本族单 NaN 必须返回**数**、双 NaN 必须返回 **canonical qNaN**。
- **不得**按 IEEE 754-2008 `minNum`/`maxNum` 的宽松处实现（NaN 传播位置未定、可任选）。
- 不提供「NaN 传播版」`minimum`/`maximum`（IEEE 754-2019 §9.6 的另一函数）的硬件形态；需要时由
  软件/编译器以本族加显式 NaN 判断合成。也不提供 `minNumMag` 类变体，
  也不涉及整数 min/max。

合法性：

- 目的 `rfHB = rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`（读出 FCSR 中的 qNaN，见 §1）。
- `orrr` 单目的，源与目的允许重叠（先读后写，结果确定）。

> **范围**：语义按本节冻结。

### 2.5 融合乘加（fusedMultiplyAdd）

融合乘加把一次乘法与一次加法合并为**一次**运算，操作数类型为 `rrrr`（四个寄存器槽：一个目的、三个源）。
书写形式为 `ftfma rfHA, rfHB, rfHC, rfHD` 与 `fofma rfHA, rfHB, rfHC, rfHD`——四个操作数均为普通寄存器，
**不**使用花括号（本形态只有一个目的，与双目的/条件赋值的 `rrrr` 写法不同）。

`ftfma` 作用于 ft（32 位）、`fofma` 作用于 fo（64 位）；`rfHA` 为目的操作数，
`rfHB`/`rfHC` 为乘数与被乘数，`rfHD` 为加数。语义为 IEEE 754-2019 的
`fusedMultiplyAdd(rfHB, rfHC, rfHD)`。

**单次舍入**：`rfHB × rfHC` 的**精确积**（不先舍入）与 `rfHD` 相加，所得精确和
**只在最后舍入一次**，舍入模式由 `rf0[33:32]` 控制。因此本族**不等价于**「先
`ftmul`/`fomul` 再 `ftadd`/`foadd`」——后者在乘法结果处多舍入一次，可能给出不同结果。

> **反例（ft）**：`a = 1 + 2⁻²³`（`0x3F80_0001`）、`b = 1 − 2⁻²³`（`0x3F7F_FFFE`）、
> `c = −1`。精确积 `a × b = 1 − 2⁻⁴⁶`。`ftfma rf1, rf2, rf3, rf4`（`rf2 = a`、`rf3 = b`、
> `rf4 = c`）得 `−2⁻⁴⁶`（`0xA880_0000`，在 ft 中精确可表示）；而 `ftmul` 先把积舍入为
> `1`（`0x3F80_0000`），再 `ftadd` 得 `+0`。两者之差即「积被提前舍入」的损失。

**读写在先后**：目的 `rfHA` **允许**与任一源重叠（含与 `rfHB`/`rfHC`/`rfHD` 相同）；
硬件**先读**全部三个源操作数、再写结果，源被目的覆盖前其值已捕获，行为确定。
乘法可交换：`rfHB` 与 `rfHC` 互换结果不变；`rfHD` 是加数，**不可**与二者互换。

**特例与标志**（IEEE 754-2019 §7.2）：

- NaN：任一操作数为 qNaN ⇒ 返回 qNaN（canonical 化）；任一操作数为 **sNaN** ⇒ 置 **NV**、返回 qNaN。
- `0 × ±Inf`：即使加数 `rfHD` 为 qNaN，仍置 **NV**、返回 qNaN（「零乘无穷」无效运算优先于 NaN 传播）。
- `±Inf × 有限非零数` ⇒ 积为同号 Inf；与加数异号 Inf 相加（`Inf + (−Inf)`）⇒ 置 **NV**、返回 qNaN；同号 ⇒ 该 Inf。
- `±Inf` 作乘数、另一乘数为 `±0` 的情形按上一条 `0 × ±Inf` 处理；`Inf × Inf` ⇒ 积的符号按乘法符号规则取 `Inf`，再与加数按上一条合成。
- 精确和为零（积与加数互为相反数、`0 × 有限数 + ±0` 等）⇒ 依 IEEE 754-2019 §6.3 的零符号规则：舍入模式为 RDN 时取 `−0`，其余取 `+0`。
- 溢出 ⇒ 返回 `±Inf` 并置 **OF**；下溢 ⇒ 返回次正规数或 `±0` 并置 **UF**；单次舍入，故 **NX 最多置一次**。
- 本族**不触发陷阱**，只累积 `rf0[4:0]` 状态位；结果恒为 IEEE 754 值（含 NaN/Inf）。

合法性：

- 目的 `rfHA = rf0` ⇒ ILLI（`dst_rf0`）；源可为 `rf0`（读出 FCSR 中的 qNaN）。
- `rrrr` 单目的，三个源与目的允许重叠（先读后写，结果确定）；本族**不采用**双目的形态。

> **注**：本 ISA 不提供 `fmsub`/`fnmadd`/`fnmsub` 的独立编码；需要 `a × b − c` 等形态时，
> 先用 `ftsgnn`/`fosgnn` 对 `rfHD` 取负（符号位取反，逐位精确、不涉舍入）再执行本族，
> 结果与单条融合乘减逐位一致。

> **范围**：语义按本节冻结。

## 3. 浮点符号位操作指令

该类指令实现了浮点sign-injection指令，操作数类型为 `orrr`。

```simrisc
ftsgnj  rfHB, rfHC, rfHD
fosgnj  rfHB, rfHC, rfHD
ftsgnn  rfHB, rfHC, rfHD
fosgnn  rfHB, rfHC, rfHD
```

其中，rfHB为目的操作数，rfHC和rfHD为源操作数。
ftsgnj和fosgnj指令实现`copySign(rfHC, rfHD)`运算，即读取rfHC的除符号位之外的所有位数，和rfHD的符号位组合获得结果，写入rfHB。
ftsgnn和fosgnn指令是读取rfHC的除符号位之外的所有位数，和rfHD的符号位取反，组合获得结果，写入rfHB。

硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

该类指令的几个特例如下：

- 当rfHD为rf0时，ftsgnj和fosgnj实现了`abs(rfHC)`操作
- 当rfHD为rf0时，ftsgnn和fosgnn实现了`-abs(rfHC)`操作
- 当rfHC与rfHD相等时，ftsgnj和fosgnj实现了`copy(rfHC)`操作
- 当rfHC与rfHD相等时，ftsgnn和fosgnn实现了`negate(rfHC)`操作

## 4. 浮点比较指令

浮点比较运算，参与比较运算的两个浮点数存放在rfHC和rfHD中，比较结果存放在rdHB中。操作数类型为 `orrr`。

```simrisc
ftqcmp  rdHB, rfHC, rfHD
ftscmp  rdHB, rfHC, rfHD

foqcmp  rdHB, rfHC, rfHD
foscmp  rdHB, rfHC, rfHD
```

rdHB中的比较结果有四种情况：

- 1：`rfHC > rfHD`
- 0：`rfHC = rfHD`
- -1：`rfHC < rfHD`
- NaN：unordered，Quiet Compare的结果为qNaN（符号位为0），Signaling Compare的结果为sNaN（符号位为0）

由于qNaN和sNaN的二进制数据按整型看是正数，因此，可以用零和负数的条件立刻判断出Equal/NotEqual/Less/NotLess/LessEqual/GreaterUnordered六种关系，而当rdHB的结果为正数则需要进一步判断结果数据是否为1，才能得出Unordered和Greater分开进行判断的结果。

## 5. 浮点分类指令

浮点分类指令对浮点数进行判断分类，并将分类结果写入数据寄存器，操作数类型为 `orri`，指令如下：

```simrisc
ftcls   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
focls   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
```

其中 `immu6` 指定连续分类的寄存器数量（1–63），目的寄存器为 rd，源寄存器为 rf。例如 `focls {rd4:rd6}, {rf8:rf10}` 对 rf8、rf9、rf10 分类，结果分别写入 rd4、rd5、rd6。来源为 `rf`、目的为 `rd`，分属不同寄存器组、结构性不可能重叠；分类按序号递增逐对进行，先读后写。

对每个源寄存器的浮点数据，指令设置对应目的寄存器中的相应位，并将其他位清零：[63..10] 全部清零，分类结果仅使用 [9..0]。

| 类别位 | 含义 |
| ---   | ---               |
| 0     | signalingNaN      |
| 1     | quietNaN          |
| 2     | negativeInfinity  |
| 3     | negativeNormal    |
| 4     | negativeSubnormal |
| 5     | negativeZero      |
| 6     | positiveZero      |
| 7     | positiveSubnormal |
| 8     | positiveNormal    |
| 9     | positiveInfinity  |

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常

> **注**：浮点运算指令以 `rf0` 为**目的**操作数 → ILLI；`rf0` 可作**源**操作数（含 `ftsgnj`/`fosgnj` + `rfHD=rf0` 的 `abs()` 特例，见 §浮点符号位操作指令）。写语义见 SimRISC-00。浮点寄存器的读写（ld/st/ldm/stm 的 rf 形式、cs.*-rf、rd2rf/rf2rd、set.w-rf）见 SimRISC-01、SimRISC-02 和 SimRISC-03。

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `fo2fo` | `orri` | `rf` | `fo2fo {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2fo_orri_rf` |
| `fo2ft` | `orri` | `rf` | `fo2ft {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2ft_orri_rf` |
| `fo2io` | `orri` | `rf` | `fo2io {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2io_orri_rf` |
| `fo2it` | `orri` | `rf` | `fo2it {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2it_orri_rf` |
| `fo2uo` | `orri` | `rf` | `fo2uo {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2uo_orri_rf` |
| `fo2ut` | `orri` | `rf` | `fo2ut {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `fo2ut_orri_rf` |
| `foadd` | `orrr` | `rf` | `foadd rfHB, rfHC, rfHD` | `foadd_orrr_rf` |
| `focls` | `orri` | `rf` | `focls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `focls_orri_rf` |
| `fodiv` | `orrr` | `rf` | `fodiv rfHB, rfHC, rfHD` | `fodiv_orrr_rf` |
| `fofma` | `rrrr` | `rf` | `fofma rfHA, rfHB, rfHC, rfHD` | `fofma_rrrr_rf` |
| `fomax` | `orrr` | `rf` | `fomax rfHB, rfHC, rfHD` | `fomax_orrr_rf` |
| `fomin` | `orrr` | `rf` | `fomin rfHB, rfHC, rfHD` | `fomin_orrr_rf` |
| `fomul` | `orrr` | `rf` | `fomul rfHB, rfHC, rfHD` | `fomul_orrr_rf` |
| `foqcmp` | `orrr` | `rf` | `foqcmp rdHB, rfHC, rfHD` | `foqcmp_orrr_rf` |
| `forem` | `orrr` | `rf` | `forem rfHB, rfHC, rfHD` | `forem_orrr_rf` |
| `fornd` | `orri` | `rf` | `fornd rfHB, rfHC, immu6` | `fornd_orri_rf` |
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
| `ftcls` | `orri` | `rf` | `ftcls {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ftcls_orri_rf` |
| `ftdiv` | `orrr` | `rf` | `ftdiv rfHB, rfHC, rfHD` | `ftdiv_orrr_rf` |
| `ftfma` | `rrrr` | `rf` | `ftfma rfHA, rfHB, rfHC, rfHD` | `ftfma_rrrr_rf` |
| `ftmax` | `orrr` | `rf` | `ftmax rfHB, rfHC, rfHD` | `ftmax_orrr_rf` |
| `ftmin` | `orrr` | `rf` | `ftmin rfHB, rfHC, rfHD` | `ftmin_orrr_rf` |
| `ftmul` | `orrr` | `rf` | `ftmul rfHB, rfHC, rfHD` | `ftmul_orrr_rf` |
| `ftqcmp` | `orrr` | `rf` | `ftqcmp rdHB, rfHC, rfHD` | `ftqcmp_orrr_rf` |
| `ftrem` | `orrr` | `rf` | `ftrem rfHB, rfHC, rfHD` | `ftrem_orrr_rf` |
| `ftrnd` | `orri` | `rf` | `ftrnd rfHB, rfHC, immu6` | `ftrnd_orri_rf` |
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

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `focls_orri_rf`, `foqcmp_orrr_rf`, `foscmp_orrr_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftcls_orri_rf`, `ftqcmp_orrr_rf`, `ftscmp_orrr_rf`（14 条）
* `dst_rf0`：浮点目的 rf0 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `foadd_orrr_rf`, `fodiv_orrr_rf`, `fomax_orrr_rf`, `fomin_orrr_rf`, `fomul_orrr_rf`, `forem_orrr_rf`, `fornd_orri_rf`, `foroot_orri_rf`, `fosclb_orrr_rf`, `fosgnj_orrr_rf`, `fosgnn_orrr_rf`, `fosub_orrr_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`, `ftadd_orrr_rf`, `ftdiv_orrr_rf`, `ftmax_orrr_rf`, `ftmin_orrr_rf`, `ftmul_orrr_rf`, `ftrem_orrr_rf`, `ftrnd_orri_rf`, `ftroot_orri_rf`, `ftsclb_orrr_rf`, `ftsgnj_orrr_rf`, `ftsgnn_orrr_rf`, `ftsub_orrr_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2fo_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2fo_orri_rf`, `ut2ft_orri_rf`（36 条）
* `mreg_zero`：immu6=0 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `focls_orri_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftcls_orri_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2fo_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2fo_orri_rf`, `ut2ft_orri_rf`（22 条）
* `mreg_range_overflow`：起始+immu6>64 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `focls_orri_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftcls_orri_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2fo_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2fo_orri_rf`, `ut2ft_orri_rf`（22 条）
* `mreg_range_overlap`：源/目的范围交集 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `fornd_orri_rf`, `ftrnd_orri_rf`（2 条）
* `encode_fp_root_n`：ftroot/foroot n≠2 → ILLI — `foroot_orri_rf`, `ftroot_orri_rf`（2 条）

**decode ILLI（未实现该语义的机器）：**
* `fofma_rrrr_rf`：decode ILLI
* `ftfma_rrrr_rf`：decode ILLI
<!-- LEGALITY_END -->
