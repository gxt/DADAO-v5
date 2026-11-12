# SimRISC浮点运算指令

> **版本：0.5.7-rc**（与 SimRISC-00 一致）
> **分类：浮点运算** — fo/ft 运算、格式转换、比较、符号位操作、条件赋值、分类、取整、最小最大值

**规范性引用**：本册的浮点数据格式、运算结果与异常语义以 **IEEE 754-2019** 为准——本册未写明的行为按 IEEE 754-2019 执行；本册与之冲突时，**以 IEEE 754-2019 为准**，唯一例外是本册**显式标注为有意偏离**并给出理由的条目。

舍入模式由 rf0[33:32] 控制，异常标志在 rf0[4:0]。浮点指令执行后，异常状态位（NV/DZ/OF/UF/NX）由硬件设置，软件可通过读取 rf0 检查异常状态。

## 1. 格式转换指令

格式转换指令在整型与浮点格式之间、以及同格式之间转换数据，操作数类型为 `orri`，每条指令一个目的、一个源。其中 it 表示32位有符号整数，io表示64位有符号整数，ut表示32位无符号整数，uo表示64位无符号整数，ft表示32位单精浮点数，fo表示64位双精浮点数。

低 6 位 `immu6` 的语义按「结果是否依赖舍入」分为三类，三者互斥：

| 类别 | 条数 | 指令 | `immu6` 语义 |
|---|---|---|---|
| 舍入方向六档 | 15 | `ft2it`/`ft2io`/`ft2ut`/`ft2uo`、`fo2it`/`fo2io`/`fo2ut`/`fo2uo`、`fo2ft`、`it2ft`/`io2ft`/`ut2ft`/`uo2ft`、`io2fo`/`uo2fo` | 舍入方向（§1.1） |
| 精确转换 | 3 | `ft2fo`、`it2fo`、`ut2fo` | SBZ，必须为 0（§1.2） |
| 复制 | 4 | `ft2ft`、`fo2fo`（`rd2rf`/`rf2rd` 同属此类，见 SimRISC-02） | 连续寄存器个数 1–63（§1.3） |

**读写顺序**：每条指令只访问一个目的与一个源（复制类为一段源窗口与一段目的窗口），硬件先读全部源再写目的，源与目的可为同一寄存器，行为确定。

### 1.1 舍入方向六档

结果依赖舍入的 15 条转换在 `immu6` 中显式携带舍入方向，取值为 6 位 one-hot（恰一位为 1），与取整指令的六档按位序一致：

| `immu6` | 舍入方向 | 读 `rf0[33:32]` |
|---|---|---|
| `0x01` | 就近取偶（RNE） | 否 |
| `0x02` | 就近、平局远离 0（RNA） | 否 |
| `0x04` | 向 0（RTZ） | 否 |
| `0x08` | 向 +∞（RUP） | 否 |
| `0x10` | 向 −∞（RDN） | 否 |
| `0x20` | 动态：按 `rf0[33:32]`（`00` RNE / `01` RTZ / `10` RDN / `11` RUP） | 是 |

- 5 个静态档**不受** `rf0[33:32]` 影响；**只有** `0x20` 读 `rf0[33:32]`。
- `immu6` 必须是上述六值之一；其他取值（含 `0x00`）⇒ ILLI。
- 方向是运算属性而非环境属性：同一指令在任何 `rf0` 取值下结果确定（`0x20` 除外，其语义即「跟随环境」）。

字段与格式：

| 指令 | 目的 | 源 |
|---|---|---|
| `ft2it`/`ft2io`/`ft2ut`/`ft2uo` | `rdHB`（ft→32/64 位有符号/无符号整数） | `rfHC`（ft） |
| `fo2it`/`fo2io`/`fo2ut`/`fo2uo` | `rdHB`（fo→32/64 位有符号/无符号整数） | `rfHC`（fo） |
| `it2ft`/`io2ft`/`ut2ft`/`uo2ft` | `rfHB`（ft） | `rdHC`（32/64 位有符号/无符号整数） |
| `io2fo`/`uo2fo` | `rfHB`（fo） | `rdHC`（64 位有符号/无符号整数） |
| `fo2ft` | `rfHB`（ft） | `rfHC`（fo） |

### 1.2 精确转换（SBZ）

`ft2fo`（f32→f64）、`it2fo`（int32→f64）、`ut2fo`（uint32→f64）的结果总能被目标格式精确表示，因此**不涉舍入**：低 6 位为 SBZ，必须为 0，非 0 ⇒ ILLI；不读 `rf0[33:32]`，不置 NX/OF/UF。字段为 `rfHB`（目的）与源（`ft2fo` 为 `rfHC`，`it2fo`/`ut2fo` 为 `rdHC`）。

### 1.3 复制

`ft2ft`、`fo2fo` 只在同类浮点寄存器之间搬移数据（64 位二进制不变，ft 只用低 32 位），`immu6` 指定连续搬移的寄存器个数（1–63）：

```simrisc
ft2ft   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}
fo2fo   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}
```

例如 `ft2ft {rf4:rf6}, {rf8:rf10}` 将 rf8→rf4、rf9→rf5、rf10→rf6。源范围与目的范围不可有任何交集（含完全重合），否则触发 ILLI 异常；无交集时按序号递增逐对进行，先读后写。本类不涉舍入，不置任何标志。限制：`immu6` = 0 ⇒ ILLI；任一起始寄存器 + `immu6` > 64 ⇒ ILLI。

### 1.4 异常与标志

转换族只实现「inexact 即报告」的形态：**结果 inexact 一律置 NX**，不提供「舍入但不置标志」的变体。

- **浮点→整数**（8 条）：有限值结果无法精确表示 ⇒ 置 NX；NaN/Inf/超出目标整型范围 ⇒ 返回整型饱和值（最大/最小）并置 **NV**，**不置 NX**。
- **整数→浮点**（8 条：6 条六档 + 精确的 `it2fo`/`ut2fo`）：精度损失 ⇒ 置 NX；结果超出目标格式范围 ⇒ ±Inf 并置 OF；结果 **tiny 且 inexact** ⇒ 按方向处理并置 UF（同时置 NX）。两条精确转换恒不置标志。
- **浮点→浮点**（`fo2ft` 六档 / `ft2fo` 精确）：`ft2fo` 为精确转换，不置标志；`fo2ft` 的下溢（结果 **tiny 且 inexact**）按方向处理并置 UF（同时置 NX）、NaN 传播 payload、sNaN 作为算术输入置 NV 并返回 qNaN；`fo2ft` 的**溢出**按下方「溢出」段处理。

**`fo2ft` 溢出（IEEE 754-2019 §7.4）**：溢出指以**无限指数范围**按所选方向舍入后的结果，其绝对值大于 ft 的最大有限值 `ft_max = (2 − 2^−23) × 2^127`（`0x7F7F_FFFF`）。结果形态由**舍入方向**决定；无论结果为 `±Inf` 还是 `±ft_max`，都置 **OF** 且置 **NX**：

| 舍入方向（`immu6` 档） | 正溢出（精确结果 > 0） | 负溢出（精确结果 < 0） |
|---|---|---|
| RNE（`0x01`） | `+Inf` | `−Inf` |
| RNA（`0x02`） | `+Inf` | `−Inf` |
| RTZ（`0x04`） | `+ft_max` | `−ft_max` |
| RUP（`0x08`，向 +∞） | `+Inf` | `−ft_max` |
| RDN（`0x10`，向 −∞） | `+ft_max` | `−Inf` |
| 动态（`0x20`） | 按 `rf0[33:32]` 取上表对应行（`00` RNE / `01` RTZ / `10` RDN / `11` RUP） | 同左列规则 |

- `+ft_max` = `0x7F7F_FFFF`、`−ft_max` = `0xFF7F_FFFF`；有限结果的**符号恒为精确结果的符号**，由舍入方向决定的是取最大有限值还是取无穷。
- 溢出与「结果变为 Inf」不等价：只有 RNE/RNA，以及 RUP 的正溢出、RDN 的负溢出，结果才是 `±Inf`；其余情形结果为**最大有限值**。

**异常标志口径（IEEE 754-2019 §7.5）**：`UF` 仅在结果 **tiny 且 inexact** 时置位——结果 tiny 但可精确表示时**不置** `UF`（也不置 `NX`）；`NX` 与 `UF` **相互独立**（inexact 但非 tiny ⇒ 只置 `NX`）。**tininess 检测点 = 舍入后**（after rounding：按目标格式舍入后再判结果是否小于最小正规数）。标志为 **sticky**（置位后保持到软件清零，见 `SimRISC-00 §浮点状态寄存器`）。

### 1.5 合法性

- 目的为 `rd` 组的 8 条浮点→整数：`rdHB` = `rd0` ⇒ ILLI（目的不可为 `rd0`）。
- 目的为 `rf` 组的 12 条（`fo2ft`/`ft2fo`/`ft2ft`/`fo2fo`、8 条整数→浮点）：`rfHB` = `rf0` ⇒ ILLI；`rf0` 作**源**合法（`fo2ft`/`ft2ft`/`fo2fo` 读出 FCSR 中的 qNaN 位型）。
- 18 条非复制类转换（15 条六档 + 3 条精确）**不是**块转换：`immu6` 不是个数 ⇒ 不存在 `immu6` = 0、起始 + `immu6` > 64、源/目的范围重叠三项限制；其 `immu6` 的合法取值分别见 §1.1（六档 one-hot，非 one-hot ⇒ ILLI）与 §1.2（SBZ，非 0 ⇒ ILLI）。
- 复制类（`ft2ft`/`fo2fo`）保留块转换的全部限制，见 §1.3。

> `附录 A` 的「汇编形式」列按编码几何机械派生，沿用了寄存器窗口记法；18 条非复制类转换的第三个域实为 `immu6` 的语义值（§1.1 舍入档 / §1.2 SBZ），不作窗口使用。

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
ftsclb  rfHB, rfHC, rdHD

foadd   rfHB, rfHC, rfHD
fosub   rfHB, rfHC, rfHD
fomul   rfHB, rfHC, rfHD
fodiv   rfHB, rfHC, rfHD
forem   rfHB, rfHC, rfHD
fosclb  rfHB, rfHC, rdHD
```

其中，rfHB为目的操作数，rfHC为第一个源操作数。除 `ftsclb`/`fosclb` 外，rfHD为第二个源操作数；`ftsclb`/`fosclb` 的第三个操作数为 `rdHD`（`rd` 组的**有符号 64 位整数指数**，非浮点寄存器；`rdHD = rd0` 表示指数 0）。硬件先读全部源操作数再写结果，源寄存器被目的覆盖前其值已捕获，行为确定。

`ftrem`/`forem` 为 IEEE 754 remainder 操作：结果 = `rfHC − n × rfHD`，n 为最接近 `rfHC/rfHD` 的整数，平局取偶数。`rfHC` 为 ±Inf、`rfHD` 为 ±0、任一源为 sNaN ⇒ 置 NV 并返回 qNaN；否则 `rfHD` 为 ±Inf（`rfHC` 有限）⇒ 返回 `rfHC`；qNaN 作输入 ⇒ 返回 qNaN（不置标志）。本操作结果精确，不置 NX/OF/UF。

`ftsclb`/`fosclb` 为 IEEE 754 scaleB 操作：计算 `rfHC × 2^rdHD`（`rdHD` 为整数指数），舍入模式由 rf0 控制。两种形式使用同一 `orrr` 编码，不新增 opcode；旧写法 `ftsclb rfHB, rfHC, rfHD` / `fosclb rfHB, rfHC, rfHD`（第三操作数为 `rf` 组）不再接受。NaN/Inf/溢出/下溢行为遵循 IEEE 754。

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
| `fo2ft` | `orri` | `rf` | `fo2ft rfHB, rfHC, immu6` | `fo2ft_orri_rf` |
| `fo2io` | `orri` | `rf` | `fo2io rdHB, rfHC, immu6` | `fo2io_orri_rf` |
| `fo2it` | `orri` | `rf` | `fo2it rdHB, rfHC, immu6` | `fo2it_orri_rf` |
| `fo2uo` | `orri` | `rf` | `fo2uo rdHB, rfHC, immu6` | `fo2uo_orri_rf` |
| `fo2ut` | `orri` | `rf` | `fo2ut rdHB, rfHC, immu6` | `fo2ut_orri_rf` |
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
| `fosclb` | `orrr` | `rf` | `fosclb rfHB, rfHC, rdHD` | `fosclb_orrr_rf` |
| `foscmp` | `orrr` | `rf` | `foscmp rdHB, rfHC, rfHD` | `foscmp_orrr_rf` |
| `fosgnj` | `orrr` | `rf` | `fosgnj rfHB, rfHC, rfHD` | `fosgnj_orrr_rf` |
| `fosgnn` | `orrr` | `rf` | `fosgnn rfHB, rfHC, rfHD` | `fosgnn_orrr_rf` |
| `fosub` | `orrr` | `rf` | `fosub rfHB, rfHC, rfHD` | `fosub_orrr_rf` |
| `ft2fo` | `orri` | `rf` | `ft2fo rfHB, rfHC, immu6` | `ft2fo_orri_rf` |
| `ft2ft` | `orri` | `rf` | `ft2ft {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `ft2ft_orri_rf` |
| `ft2io` | `orri` | `rf` | `ft2io rdHB, rfHC, immu6` | `ft2io_orri_rf` |
| `ft2it` | `orri` | `rf` | `ft2it rdHB, rfHC, immu6` | `ft2it_orri_rf` |
| `ft2uo` | `orri` | `rf` | `ft2uo rdHB, rfHC, immu6` | `ft2uo_orri_rf` |
| `ft2ut` | `orri` | `rf` | `ft2ut rdHB, rfHC, immu6` | `ft2ut_orri_rf` |
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
| `ftsclb` | `orrr` | `rf` | `ftsclb rfHB, rfHC, rdHD` | `ftsclb_orrr_rf` |
| `ftscmp` | `orrr` | `rf` | `ftscmp rdHB, rfHC, rfHD` | `ftscmp_orrr_rf` |
| `ftsgnj` | `orrr` | `rf` | `ftsgnj rfHB, rfHC, rfHD` | `ftsgnj_orrr_rf` |
| `ftsgnn` | `orrr` | `rf` | `ftsgnn rfHB, rfHC, rfHD` | `ftsgnn_orrr_rf` |
| `ftsub` | `orrr` | `rf` | `ftsub rfHB, rfHC, rfHD` | `ftsub_orrr_rf` |
| `io2fo` | `orri` | `rf` | `io2fo rfHB, rdHC, immu6` | `io2fo_orri_rf` |
| `io2ft` | `orri` | `rf` | `io2ft rfHB, rdHC, immu6` | `io2ft_orri_rf` |
| `it2fo` | `orri` | `rf` | `it2fo rfHB, rdHC, immu6` | `it2fo_orri_rf` |
| `it2ft` | `orri` | `rf` | `it2ft rfHB, rdHC, immu6` | `it2ft_orri_rf` |
| `uo2fo` | `orri` | `rf` | `uo2fo rfHB, rdHC, immu6` | `uo2fo_orri_rf` |
| `uo2ft` | `orri` | `rf` | `uo2ft rfHB, rdHC, immu6` | `uo2ft_orri_rf` |
| `ut2fo` | `orri` | `rf` | `ut2fo rfHB, rdHC, immu6` | `ut2fo_orri_rf` |
| `ut2ft` | `orri` | `rf` | `ut2ft rfHB, rdHC, immu6` | `ut2ft_orri_rf` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `focls_orri_rf`, `foqcmp_orrr_rf`, `foscmp_orrr_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftcls_orri_rf`, `ftqcmp_orrr_rf`, `ftscmp_orrr_rf`（14 条）
* `dst_rf0`：浮点目的 rf0 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `foadd_orrr_rf`, `fodiv_orrr_rf`, `fofma_rrrr_rf`, `fomax_orrr_rf`, `fomin_orrr_rf`, `fomul_orrr_rf`, `forem_orrr_rf`, `fornd_orri_rf`, `foroot_orri_rf`, `fosclb_orrr_rf`, `fosgnj_orrr_rf`, `fosgnn_orrr_rf`, `fosub_orrr_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`, `ftadd_orrr_rf`, `ftdiv_orrr_rf`, `ftfma_rrrr_rf`, `ftmax_orrr_rf`, `ftmin_orrr_rf`, `ftmul_orrr_rf`, `ftrem_orrr_rf`, `ftrnd_orri_rf`, `ftroot_orri_rf`, `ftsclb_orrr_rf`, `ftsgnj_orrr_rf`, `ftsgnn_orrr_rf`, `ftsub_orrr_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2fo_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2fo_orri_rf`, `ut2ft_orri_rf`（38 条）
* `mreg_zero`：immu6=0 → ILLI — `fo2fo_orri_rf`, `focls_orri_rf`, `ft2ft_orri_rf`, `ftcls_orri_rf`（4 条）
* `mreg_range_overflow`：起始+immu6>64 → ILLI — `fo2fo_orri_rf`, `focls_orri_rf`, `ft2ft_orri_rf`, `ftcls_orri_rf`（4 条）
* `mreg_range_overlap`：源/目的范围交集 → ILLI — `fo2fo_orri_rf`, `ft2ft_orri_rf`（2 条）
* `encode_sbz`：SBZ 非零 → ILLI — `ft2fo_orri_rf`, `it2fo_orri_rf`, `ut2fo_orri_rf`（3 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `fo2ft_orri_rf`, `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `fornd_orri_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftrnd_orri_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2ft_orri_rf`（17 条）
* `encode_fp_root_n`：ftroot/foroot n≠2 → ILLI — `foroot_orri_rf`, `ftroot_orri_rf`（2 条）
<!-- LEGALITY_END -->
