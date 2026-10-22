# SimRISC浮点运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：浮点运算**（46 条）— `scope: fp` 46 条（已实现）；fo/ft 运算、格式转换、比较、符号位操作、条件赋值、分类、取整
>
> **FP 范围总账（`scope: fp` 共 60 条）**：本册 46 条（MISC-RF 子表）+ SimRISC-01 取数存数 8 条（`ld.t`/`st.t`/`ld.o`/`st.o`/`ldm.t`/`stm.t`/`ldm.o`/`stm.o` 的 `-rf`）+ SimRISC-02 寄存器复制 5 条（`cs.n`/`cs.z`/`cs.p` 的 `-rf` 与 `rd2rf`/`rf2rd`）+ SimRISC-03 16位立即数操作 1 条（`set.w-rf`）。`scope` 表范围、`deferred` 表状态，二者正交（用户裁定 2026-10-03）。

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 浮点运算（46 条）｜ `scope: fp`（46 条，已实现）

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
## 2. 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `focls_orri_rf`, `foqcmp_orrr_rf`, `foscmp_orrr_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftcls_orri_rf`, `ftqcmp_orrr_rf`, `ftscmp_orrr_rf`（14 条）
* `dst_rf0`：浮点目的 rf0 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `foadd_orrr_rf`, `fodiv_orrr_rf`, `fomul_orrr_rf`, `forem_orrr_rf`, `fornd_orri_rf`, `foroot_orri_rf`, `fosclb_orrr_rf`, `fosgnj_orrr_rf`, `fosgnn_orrr_rf`, `fosub_orrr_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`, `ftadd_orrr_rf`, `ftdiv_orrr_rf`, `ftmul_orrr_rf`, `ftrem_orrr_rf`, `ftrnd_orri_rf`, `ftroot_orri_rf`, `ftsclb_orrr_rf`, `ftsgnj_orrr_rf`, `ftsgnn_orrr_rf`, `ftsub_orrr_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2fo_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2fo_orri_rf`, `ut2ft_orri_rf`（32 条）
* `mreg_zero`：immu6=0 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `focls_orri_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftcls_orri_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2fo_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2fo_orri_rf`, `ut2ft_orri_rf`（22 条）
* `mreg_range_overflow`：起始+immu6>64 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `fo2io_orri_rf`, `fo2it_orri_rf`, `fo2uo_orri_rf`, `fo2ut_orri_rf`, `focls_orri_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`, `ft2io_orri_rf`, `ft2it_orri_rf`, `ft2uo_orri_rf`, `ft2ut_orri_rf`, `ftcls_orri_rf`, `io2fo_orri_rf`, `io2ft_orri_rf`, `it2fo_orri_rf`, `it2ft_orri_rf`, `uo2fo_orri_rf`, `uo2ft_orri_rf`, `ut2fo_orri_rf`, `ut2ft_orri_rf`（22 条）
* `mreg_range_overlap`：源/目的范围交集 → ILLI — `fo2fo_orri_rf`, `fo2ft_orri_rf`, `ft2fo_orri_rf`, `ft2ft_orri_rf`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `fornd_orri_rf`, `ftrnd_orri_rf`（2 条）
* `encode_fp_root_n`：ftroot/foroot n≠2 → ILLI — `foroot_orri_rf`, `ftroot_orri_rf`（2 条）
<!-- LEGALITY_END -->


浮点格式的定义符合 IEEE754 标准。舍入模式由 rf0[33:32] 控制，异常标志在 rf0[4:0]。浮点指令执行后，异常状态位（NV/DZ/OF/UF/NX）由硬件设置，软件可通过读取 rf0 检查异常状态。

## 3. 格式转换指令

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

其中it表示32位有符号整数，io表示64位有符号整数，ut表示32位无符号整数，uo表示64位无符号整数，ft表示32位单精浮点数，fo表示64位双精浮点数。immu6 指定连续转换的寄存器数量（1-63）。例如 `ft2fo {rf4:rf6}, {rf8:rf10}` 将 rf8→rf4、rf9→rf5、rf10→rf6。源范围与目的范围不可有任何交集（含完全重合），否则触发 ILLI 异常（与 SimRISC-02 §寄存器组之间块赋值 一致）；无交集时转换按序号递增逐对进行，先读后写。

浮点格式转换遵循 IEEE 754 标准：浮点→浮点（fo2ft/ft2fo）溢出返回 ±Inf（设置 OF），下溢按舍入模式处理（设置 UF），NaN 传播 payload。整数→浮点转换可能 inexact（精度损失）。浮点→整数转换中 NaN/Inf/超出范围返回整型饱和值（最大/最小），设置 NV 标志。sNaN 作为算术输入时设置 NV 并返回 qNaN。舍入模式由 rf0[33:32] 控制，异常标志在 rf0[4:0]。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
- 源范围与目的范围有任何交集（含完全重合）时触发 ILLI 异常

## 4. 浮点运算指令

根据操作数不同，浮点运算类指令可以分为以下几种：

### 4.1 S2D1

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

### 4.2 S1D1

还有一种是一个源操作数，一个目的操作数，操作数类型为 `orri`。

```simrisc
ftroot  rfHB, rfHC, immu6

foroot  rfHB, rfHC, immu6
```

ftroot和foroot指令用来实现`rootn(x, n)`运算，其中 n 的值存放在 immu6 中。仅支持 n=2（平方根）；其他 n 值触发 ILLI 异常。

> 注意：`ftroot/foroot` 的运算基本等同于 `ftsqrt/fosqrt`，但是在 IEEE754-2019 中特意指出，`rootn(-0, 2)` 不等于 `squareRoot(-0)`，因此，对于 `rootn(-0, 2)` 的运算结果不做具体要求。

S1D1 指令硬件先读源操作数再写结果，源被覆盖前其值已捕获，行为确定。

### 4.3 取整（roundToIntegral）

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

> **范围**：本节 2 条为 `scope: fp`（`QEMU-072t`/`LLVM-125t` 落地后由 `SPEC-162t` 翻转）；语义按本节冻结。

## 5. 浮点符号位操作指令

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

## 6. 浮点比较指令

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

## 7. 浮点分类指令

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

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- 新增取整指令 `ftrnd`/`fornd`（MISC-RF，`immu6` one-hot 六档：TiesToEven/TiesToAway/TowardZero/TowardPositive/TowardNegative/Exact；`scope: excluded`，执行 ILLI）；misc-RF 子表 44→46 条（`scope: fp` 仍 44 条）；登记 `nearbyint` 无硬件变体（落动态档，NX 可能被置位）与 `rf0[33:32]` 不扩充（RMM 不支持）两项已知偏差。
- 浮点合法性规则（`rule_refs`）回填、归并与重叠禁则。
- `ftrnd`/`fornd` 执行语义与后端落地（QEMU/LLVM）后解除暂缓登记：`scope: excluded` → `scope: fp`（`decode: ILLI` 撤销，合法性 `dst_rf0` + `encode_onehot` 生效）；misc-RF 子表 46 条全部为 `scope: fp`，FP 范围总账 58 → 60 条（本册 44 → 46 条）。
- 引入 `scope: fp` 标注；本册 44 条 + 分布取数存数 / 寄存器复制 / 16 位立即数的 16 条，`scope: fp` 共 60 条。
- 新增「合法性检查」章（生成区）。
- 删除 `ftlog`/`folog`；`ftroot`/`foroot` 仅保留 n=2。
- `rf0` 位域与访问规则调整。
- 正文改用新汇编格式；`cls` 浮点分类指令改多寄存器渲染；新增「汇编指令速查」章（生成区）。
- `focls`/`ftcls` 分类位序改为 IEEE 754-2019 `class` 的类别顺序（bit0 sNaN、1 qNaN、2 -∞、3 -normal、4 -subnormal、5 -0、6 +0、7 +subnormal、8 +normal、9 +∞，与 LLVM `is.fpclass` 的 `FPClassTest` 一致）；**破坏性**：与 RISC-V `fclass` 位序不兼容。

### 0.5.4（2026-09-28）

- 本册由原《SimRISC 浮点类指令》整体演进而来（浮点存取 / 格式转换 / 浮点运算 / 符号位 / 比较 / 条件赋值 / 分类）。
- 删除 FPEXCP 异常（浮点按 IEEE 754 执行、经 `rf0` 轮询异常状态）；`set.ft`/`set.fo`/`set.rf` 伪指令归入本册。

### 0.5.3（2026-07-19）

- 删除 `rf2rf`、新增 `ft2ft`/`fo2fo`；删除 `cs.p1`/`cs.np1`、新增 `cs.eq-rf`/`cs.ne-rf`；`setrd`/`setrb`/`setrf` 改名为 `set.rd`/`set.rb`/`set.rf`。

### 0.5.2（2026-07-18）

- 浮点存取 / 立即数 / 条件赋值指令名后缀统一（`ld.t`/`st.t`/`set.w`/`cs.*-rf`）。

### 0.5.1（2026-07-17）

- 浮点转换指令寄存器组 / FPEXCP 口径等多项审查修复（`68ceb3f8`）。

### 0.5.0（2026-07-15）

- 浮点运算指令编码整理；`ww`→`wpN`（wyde position）重命名。

### 0.4.1（2026-07-14）

- 初版：同步上游浮点类指令（格式符合 IEEE 754，异常状态经 `rf0` 轮询）。
