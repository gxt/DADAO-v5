# IDL 语法子集盘点（12 册 + `lib/fp.idl`）

> **本册回答**：`idl/*.idl` **实际用到**了 UDB IDL 的哪些语法构造、各用多少次、首次出现在哪。
> M17 的 Python 前端（`m17-idl-002`）只按本册的口径实现；UDB 的 652 行 `idl.treetop` 全量语法
> **不**重写。宽度/符号派生规则见 [`width-rules.md`](width-rules.md)。
> **数字全部现场派生**：统计脚本 `idl/tools/idl_subset_stats.py`（`python3 idl/tools/idl_subset_stats.py` 打印，
> `--check` 校验本册）。改 `.idl` 后本册不同步 ⇒ `--check` 红。

## 1. 口径

- **扫描面**：`idl/SimRISC-01.idl`…`idl/SimRISC-12.idl` + `idl/lib/fp.idl` 共 13 个文件。
  `spec/SimRISC-*` 里围栏语言标记为 `idl` 的代码块是这 13 个文件的渲染结果
  （`idl/tools/idl_render.py --check` 保证逐字节相等），故不重复统计。
- **「次数」= 出现次数**（不是「行数」也不是「不同位置数」）：同一行出现两次算两次。
- **先抹「散文」再统计**：源码里有两处自然语言——`#` 到行尾的注释、以及 `description { … }`
  块（自由文本）。两者都会引述伪码（`` `+Inf` ``、`floor(…)`、`GF(2)`），按字面统计会把散文
  误计成语法，故一律先抹掉；只有 `S01`–`S03` 按原文统计（`S01`/`S02` 本身是注释，
  `S03` 是文件头）。
- **运算符计数前归一化**：`Bits<N>`、Verilog 定宽字面量与 `0x…` 先替换掉，避免 `Bits<64>`
  的 `<` 被当成比较、`` `<< `` 被当成逻辑左移（加宽运算单列）。
- **花括号按位置分类**：行首/表达式位置的 `{` 记作拼接或复制；`if (...) {`、`else {`、
  `body {`、`description {`、`function … {`、`enum … {` 这类语句块/声明块不计；
  嵌套的复制式（`{{N{a}}, b}`）逐层计。
- **operation 总数** 与 `contracts/opcodes.yaml` 的 `- id:` 条数**独立对账**（不从 IDL 自证）；
  另断言 `mode()` 次数 == `raise(` 次数、复制式 ⊆ 表达式花括号。
- 表内按**主题**分组，`S66` 是「无初值声明」补登的一类（编号在末尾，不代表章节顺序）。

## 2. 扫描面与规模

| 文件 | operation 数 |
| --- | ---: |
| `idl/SimRISC-01.idl` | 38 |
| `idl/SimRISC-02.idl` | 17 |
| `idl/SimRISC-03.idl` | 8 |
| `idl/SimRISC-04.idl` | 33 |
| `idl/SimRISC-05.idl` | 6 |
| `idl/SimRISC-06.idl` | 15 |
| `idl/SimRISC-07.idl` | 50 |
| `idl/SimRISC-08.idl` | 21 |
| `idl/SimRISC-09.idl` | 21 |
| `idl/SimRISC-10.idl` | 21 |
| `idl/SimRISC-11.idl` | 5 |
| `idl/SimRISC-12.idl` | 28 |

合计 **263** 条 operation；`idl/lib/fp.idl` 没有 operation（是语义库，含
108 个 `function` 声明）。

## 3. 文件结构与注释

| ID | 构造 | 次数 | 首个出处 |
| --- | --- | ---: | --- |
| S01 | operation 头 `# id:` | 263 | `idl/SimRISC-01.idl:1` |
| S02 | 注释行（源码行内含 `#`） | 1871 | `idl/SimRISC-01.idl:1` |
| S03 | `%version: 0.1` 文件头 | 1 | `idl/lib/fp.idl:1` |

- `# id: <instr-id>` 是**分块标记**：每个 operation 以它开头，id 与 `contracts/opcodes.yaml` 一致；
  `render.py` 按它切块并渲染进 `spec/`。
- 文件头（首个 `# id:` 之前）只允许空行与注释（`render.py` 断言 A）；`%version:` 只出现在
  `idl/lib/fp.idl`（库文件），12 册 operation 源没有版本头。

## 4. 类型、声明与枚举

| ID | 构造 | 次数 | 首个出处 |
| --- | --- | ---: | --- |
| S04 | 枚举声明 `enum X { … }` | 3 | `idl/lib/fp.idl:46` |
| S05 | 枚举成员引用 `Enum::Member` | 574 | `idl/SimRISC-01.idl:4` |
| S06 | `Bits<N>` 类型 | 1394 | `idl/SimRISC-01.idl:7` |
| S07 | `U32` 类型（= `Bits<32>`） | 27 | `idl/SimRISC-04.idl:238` |
| S08 | `Boolean` 类型 | 37 | `idl/SimRISC-07.idl:496` |
| S09 | 带初值的变量/常量声明行（`Bits<N>`/`U32`/`Boolean` + `=`） | 1100 | `idl/SimRISC-01.idl:7` |
| S66 | 无初值声明行（`Bits<N> x;`） | 46 | `idl/SimRISC-07.idl:646` |
| S10 | `function NAME { … }` 声明 | 108 | `idl/lib/fp.idl:92` |
| S11 | `?` 后缀谓词函数名（声明或调用） | 142 | `idl/SimRISC-07.idl:919` |

- `Bits<N>` 的 `N` **必须是编译期已知常量**（`spec/IDL-ISA语义描述语言与语义库.md` §1）；
  实际取值 21 种：1/3/4/5/6/7/8/11/12/14/16/20/23/26/32/48/52/64/65/128/192（`--json` 可复核；
  最常见 64 与 32）。
- 声明有两种形态：带初值（1100 行）与**无初值**（46 行，如 `Bits<32> mag;`，
  随后在 `if`/`else` 两支里各自赋值）。**没有**数组型局部变量：`rd[]`/`rb[]`/`rf[]`/`ra[]`/
  `fo[]`/`ft[]` 六个数组只由语义库 §4.2 声明，12 册 operation 里只出现**下标访问**。
- 12 册引用的枚举：`ExceptionCode`（`raise` 的异常码）与浮点库的 `FpFlag`/`RoundingMode`/
  `MulAddOp`（调用浮点/转换库时作实参）；`enum` **声明**只在 `idl/lib/fp.idl`（3 个）。
- `function` 声明只在 `idl/lib/fp.idl`（108 个）；12 册 operation 里只出现**调用**。
  `?` 后缀（`S11`）只用于谓词型函数（`is_sp_nan?` 等），`?` 是名字的一部分（不是运算符）。

## 5. 语句与控制流

| ID | 构造 | 次数 | 首个出处 |
| --- | --- | ---: | --- |
| S12 | `if (...)` 条件语句（含 `else if`） | 1109 | `idl/SimRISC-01.idl:3` |
| S13 | `else if (...)` 分支 | 131 | `idl/SimRISC-03.idl:13` |
| S14 | `else { … }` 分支 | 156 | `idl/SimRISC-01.idl:568` |
| S15 | `for (init; cond; step)` 循环 | 42 | `idl/SimRISC-01.idl:177` |
| S16 | `return` 语句 | 339 | `idl/lib/fp.idl:124` |
| S17 | `++` 自增（只出现在 `for` 步进） | 39 | `idl/SimRISC-01.idl:177` |
| S18 | 赋值/初始化语句行（`=`，不含 `==`/`<=`/`>=`/`!=`） | 2315 | `idl/SimRISC-01.idl:7` |
| S19 | 切片赋值行（左值含 `[msb:lsb]`） | 69 | `idl/SimRISC-01.idl:567` |
| S20 | 单比特赋值行（左值末段为单下标） | 4 | `idl/lib/fp.idl:1123` |

- 控制流只有 `if`/`else if`/`else` 与 `for`；**没有** `while`、`break`、`continue`、`switch`
  （「提前结束」用布尔标志，见 `SimRISC-12` 的 `ctlz`/`cttz`）。
- `for` 的三种写法都在用：`for (Bits<6> k = 6'd0; k < immu6; k++)`（块传送逐寄存器）、
  `for (U32 i = 0; i < 64; i++)`（逐位循环）、`for (Bits<7> k = 7'd0; k != 7'd64; k = k + 7'd1)`
  （位扫描）。步进既可能是 `++`（39 处）也可能是 `k = k + …`。
- 赋值左值有四种形态：局部变量、整寄存器元素 `rd[rdHA] = …`（数组元素下标可为表达式，
  如 `rd[rdHA + k]`）、切片 `rd[rdHC][31:0] = …`（69 行）、单比特
  `a_copy[22] = 1'b1`（4 行，全在 `idl/lib/fp.idl`）。
- **没有**复合赋值（`+=`/`|=`/`<<=` 等）⇒ 步进与累加一律写成 `x = x + …`。

## 6. 运算符与表达式

| ID | 构造 | 次数 | 首个出处 |
| --- | --- | ---: | --- |
| S21 | 加宽加 `` `+ `` | 24 | `idl/SimRISC-02.idl:122` |
| S22 | 加宽乘 `` `* `` | 6 | `idl/lib/fp.idl:1441` |
| S23 | 加宽左移 `` `<< `` | 14 | `idl/SimRISC-07.idl:48` |
| S24 | 逻辑左移 `<<` | 139 | `idl/SimRISC-04.idl:240` |
| S25 | 逻辑右移 `>>` | 94 | `idl/SimRISC-04.idl:313` |
| S26 | 算术右移 `>>>` | 8 | `idl/SimRISC-04.idl:351` |
| S27 | 相等比较 `==` / `!=` | 1060 | `idl/SimRISC-01.idl:3` |
| S28 | 大小比较 `<` `<=` `>` `>=` | 288 | `idl/SimRISC-01.idl:163` |
| S29 | 逻辑 `&&` / `\|\|` / `!` | 290 | `idl/SimRISC-01.idl:10` |
| S30 | 位运算 `&`、`\|`、`^`、`~` | 257 | `idl/SimRISC-03.idl:12` |
| S31 | 三目 `cond ? a : b` | 155 | `idl/SimRISC-04.idl:187` |
| S32 | 拼接/复制表达式（表达式位置的花括号，嵌套逐层计） | 386 | `idl/SimRISC-01.idl:11` |
| S33 | 复制 `{N{a}}`（`N` 为字面常量） | 73 | `idl/SimRISC-01.idl:29` |
| S34 | 位切片 `[msb:lsb]`（读与写左值） | 487 | `idl/SimRISC-01.idl:8` |
| S35 | 单比特取位/单下标取值 `[expr]` | 236 | `idl/SimRISC-01.idl:29` |
| S36 | 双重下标 `x[i][j]`（数组 + 切片/取位） | 221 | `idl/SimRISC-01.idl:567` |
| S37 | `$signed(...)` 有符号视图 | 119 | `idl/SimRISC-01.idl:7` |
| S38 | Verilog 定宽字面量（`6'd0`/`32'h…`/`1'b0`，含下划线分组） | 1580 | `idl/SimRISC-01.idl:3` |
| S39 | 有符号定宽字面量 `N'sd` / `N'sh` | 16 | `idl/lib/fp.idl:1095` |
| S67 | 有符号短字面量 `0s` | 32 | `idl/SimRISC-07.idl:34` |
| S68 | Boolean 字面量 `true` / `false` | 24 | `idl/SimRISC-07.idl:498` |
| S40 | C 风格十六进制字面量 `0x…` | 74 | `idl/lib/fp.idl:439` |

- 加宽运算写成「反引号 + 运算符」：`` `+ ``（24 处：`SimRISC-02`/`SimRISC-07` 的
  块传送范围上界 + `SimRISC-04` 的 65 位和）、`` `<< ``（14 处：`SimRISC-07` 尾数对齐 +
  `idl/lib/fp.idl` 的宽移位）、`` `* ``（6 处，全在 `idl/lib/fp.idl` 的精确乘积）。
  三者的规范出处不同，见 `width-rules.md` 的 `W06`/`W07`/`W08`。
- 比较与逻辑运算全部是**显式写法**：没有链式比较（`a < b < c`），条件必须为 `Boolean`
  （整数不隐式转布尔，语言规范 §1）。
- 三目只用于「选值」，两支同类型同宽（如 `(a[63] == 1'b1) ? -a : a`）；没有把三目当语句用。
- 字面量三族并用：Verilog 定宽（1580 处，占绝对多数）、C 十六进制（74 处，
  `idl/lib/fp.idl`）、有符号字面量 `0s`/`16'sd1`（48 处，`SimRISC-07` 与
  `idl/lib/fp.idl` 的有符号比较/常量）。有符号字面量的语义见语言规范册 §1.1（`width-rules.md` 的 `U04`）。

## 7. 数组访问、函数调用与语义库

| ID | 构造 | 次数 | 首个出处 |
| --- | --- | ---: | --- |
| S41 | 函数调用（不含 `if`/`for`/`return` 等关键字） | 1986 | `idl/SimRISC-01.idl:4` |
| S42 | `rd[]` 访问 | 539 | `idl/SimRISC-01.idl:14` |
| S43 | `rb[]` 访问 | 101 | `idl/SimRISC-01.idl:7` |
| S44 | `rf[]` 访问 | 106 | `idl/SimRISC-01.idl:656` |
| S45 | `ra[]` 访问 | 9 | `idl/SimRISC-01.idl:567` |
| S46 | `fo[]` 访问（`rf` 的 64 位视图） | 28 | `idl/SimRISC-07.idl:481` |
| S47 | `ft[]` 访问（`rf` 的低 32 位视图） | 35 | `idl/SimRISC-01.idl:658` |
| S48 | `raise(...)` | 377 | `idl/SimRISC-01.idl:4` |
| S49 | `mode()` | 377 | `idl/SimRISC-01.idl:4` |
| S50 | `ip()` | 336 | `idl/SimRISC-01.idl:4` |
| S51 | `read_memory(...)` | 34 | `idl/SimRISC-01.idl:14` |
| S52 | `write_memory(...)` | 16 | `idl/SimRISC-01.idl:117` |
| S53 | `is_naturally_aligned(...)` | 56 | `idl/SimRISC-01.idl:10` |
| S54 | `reservation_set(...)` / `reservation_clear_all()` | 24 | `idl/SimRISC-12.idl:14` |
| S55 | `store_conditional(...)` | 12 | `idl/SimRISC-12.idl:301` |
| S56 | `jump(...)` | 15 | `idl/SimRISC-06.idl:5` |
| S57 | `ras_push(...)` / `ras_pop()` / `ras_cnt()` | 3 | `idl/SimRISC-06.idl:91` |
| S58 | `cfx_*` 库调用 | 12 | `idl/SimRISC-11.idl:2` |
| S59 | 浮点库调用（`ft_*`/`fo_*`/`softfloat_*`/`is_sp_*`/`is_dp_*`） | 315 | `idl/SimRISC-07.idl:12` |

- 函数调用共 **1986** 处、**117** 个不同名字；调用形式只有
  `name(args)`（无方法调用、无具名参数、无默认值、无重载）。
- 12 册 operation 里可出现 6 个数组（`S42`–`S47` 是全部访问次数）：`rd`/`rb`/`rf`/`ra` 四组
  寄存器组 + `rf` 的两个数据视图 `fo`（64 位）/`ft`（32 位）。
- 指令级语义全部经这些库函数表达：异常（`raise`）、当前地址/模式（`ip`/`mode`）、访存
  （`read_memory`/`write_memory`）、对齐（`is_naturally_aligned`）、保留标记
  （`reservation_*`/`store_conditional`）、控制转移（`jump`/`ras_*`）、核芯功能扩展
  （`cfx_*`）、浮点（`ft_*`/`fo_*`/`softfloat_*` 与 `is_sp_*?`/`is_dp_*?` 谓词）。
- `raise` 的第三参有两种形态：非法类填 `ip()`（地址 = 当前指令），地址类填
  `{16'd0, ea}`（48 位故障地址零扩展成 64 位）；`mode()` 只作 `raise` 的 `from_mode`
  实参（脚本断言 `mode()` 次数 == `raise(` 次数）。`ip()` 另作 `jump` 的基址。

## 8. 不使用的构造（脚本断言次数为 0）

| ID | 构造 | 次数 | 首个出处 |
| --- | --- | ---: | --- |
| S60 | `while (...)` 循环（不使用） | 0 | — |
| S61 | `assert` / `sizeof`（不使用） | 0 | — |
| S62 | `struct` / `bitfield` / `tuple` / `include`（不使用） | 0 | — |
| S63 | `fetch_memory(...)`（不使用） | 0 | — |
| S64 | RISC-V 式 `X[…]` / `CSR[…]` / `$encoding`（不使用） | 0 | — |
| S65 | 变量作复制次数 `{N{a}}`（`N` 非字面常量，不使用） | 0 | — |

上表不是「大概没用」，而是**机械断言**：任何一项变成非零，`--check` 立即红（本册需同步更新）。
`spec/IDL-ISA语义描述语言与语义库.md` §1 已把这些列为「本版不需要，用到再引」。

## 9. 只出现少量次的构造：说明用途即可，不为它设计语法

- `ra[]`（9 处）：`SimRISC-01` 的 RA 存取/块赋值与 `SimRISC-02` 的 RA↔RD 块传送；
  写的是 `ra[6'd0][53:0]`（`RACNT`+`MRPTR` 元数据）或整寄存器。
- 单比特赋值（4 处）：`a_copy[22] = 1'b1` 一类——`idl/lib/fp.idl` 先把整寄存器赋给
  局部变量再改一位（NaN quiet 位 / 符号位），避开上游对「数组元素位切片」的 const-eval 缺陷
  （同库 `rm_to_mode` 的注释记录该缺陷与等价写法）。
- `>>>`（8 处）：`SimRISC-04` 的 `shr.so` 与 `SimRISC-08`/`SimRISC-09` 的窄位宽
  算术右移（`.o` 64 位与 `.t`/`.w` 32/16 位各两种形式）。
- 加宽乘（6 处）：`idl/lib/fp.idl` 的 `fo_mul`/`fo_muladd` 精确乘积（63+64 位与
  106 位积），配套 128/192 位中间量。
- `jump(`（15 处）：`SimRISC-06` 的全部控制转移；是**唯一**允许写 `rb0` 的通道。
- 访存：`read_memory(`（34 处）用于 `ld`/`ldm`/`lr`，`write_memory(`（16 处）
  用于 `st`/`stm`；`sc` 走 `store_conditional(`（12 处，12 条 = 4 宽度 × 3 序）。
- `cfx_*`（12 处）：`SimRISC-11` 的 5 条 operation（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`fence`）。
- `ras_*`（3 处）：`SimRISC-06` 的 `call`（压栈）与 `ret`（弹栈/读深度）。
- `%version`（1 处）：只有库文件有；operation 源没有。

## 10. 对 `m17-idl-002`（Python 解析器）的结论

- **必须覆盖**：`# id:` 分块、`#` 注释、`Bits<N>`/`U32`/`Boolean` 声明（含无初值形态）、
  `enum` + `Enum::Member`、`function`（`returns`/`arguments`/`description`/`body` 四段；
  `?` 后缀名）、`if`/`else if`/`else`、`for`、`return`、赋值（整/切片/单比特/数组元素左值）、
  `$signed`、`+ - * / %`、`<< >> >>>`、`` `+ ``/`` `<< ``/`` `* ``、比较、逻辑、位运算、
  三目、拼接/复制、切片/取位、数组下标、函数调用、Verilog 定宽/C 十六进制/有符号字面量。
- **不需要**：`while`/`assert`/`sizeof`/`struct`/`bitfield`/`tuple`/`include`/`fetch` 块/
  `$encoding`/`X[]`/`CSR[]`/复合赋值/变量作复制次数/多返回值/递归函数（库内不递归）。
- **宽度与符号**：不要按「64 位一把梭」实现，按 `width-rules.md` 的每条规则做类型推导；
  其中原 10 条「未定义」已由语言规范册 §1.1 定义（清单见 `width-rules.md` §8），
  实现按该节执行，不得自行按 UDB/RISC-V 语义补全。
