
# ABI

> **版本：0.9.3**（与 AEE 版本号一致，同步更新。基于 SimRISC 0.5.5 指令系统设计）

通过制定ABI，使得独立编译、汇编得到的代码，可以被正确链接、执行。手工编写的汇编代码，也应遵循ABI规范。

## 1. 寄存器规范

Dadao提供了四组64个64位寄存器，所有这些寄存器对于一个运行中的进程而言都是全局可见的。

### 1.1 RD寄存器（Data registers）

RD寄存器的约定如下：

| Name          | ABI Mnemonic  | Meaning           | Callee-saved ?    |
|   ---         | ---           | ---               | ---               |
| rd0           | rdzero        | Zero              | Immutable         |
| rd1           | rderrno       | error number      | -                 |
| rd2 - rd3     |               | reserved（调试/测试保留，编译器不得分配使用） | -                 |
| rd4 - rd7     |               | temporary regs    | No                |
| rd8 - rd15    | rdt0 - rdt7   | temporary regs    | No                |
| rd16 - rd31   | rda0 - rda15  | temporary regs    | No                |
| rd32 - rd63   |               | callee saved regs | Yes               |

### 1.2 RB寄存器（Base registers）

RB寄存器的约定如下：

| Name          | ABI Mnemonic  | Meaning               | Callee-saved ?    |
|   ---         | ---           | ---                   | ---               |
| rb0           | rbip          | instruction pointer   | -                 |
| rb1           | rbsp          | stack pointer         | Yes               |
| rb2           |               | frame pointer（无条件保留；`hasFP` 为真时为 FP，否则不分配；无 ABI 别名） | Yes |
| rb3           | rbtp          | thread pointer        | -                 |
| rb4 - rb7     |               | temporary regs        | No                |
| rb8 - rb15    | rbt0 - rbt7   | temporary regs        | No                |
| rb16 - rb31   | rba0 - rba15  | temporary regs        | No                |
| rb32 - rb63   |               | callee saved regs     | Yes               |

`rb0`（ABI 名 `rbip`）即 **`IP`**：读出为**当前正在执行的指令的地址**（**非**主流 ISA 的「下一条指令地址」口径；本 ISA **无 `±4` 流水偏移**），只读，任何指令以其为显式目的时触发 ILLI（见 `SimRISC-00`）。

`rb2` 是**帧指针（frame pointer）**，**无条件保留**：`hasFP` 为真时由 prologue 保存其旧值、
epilogue 恢复，并作为帧基址；`hasFP` 为假时不参与寄存器分配。
`rb2` **没有** ABI 助记别名。

`rb32`–`rb63` 是**连续的 callee-saved 池**，可整段用 `stm`/`ldm` 批量保存/恢复。

### 1.3 RF寄存器（Floating-point registers）

RF寄存器的约定如下：

| Name          | ABI Mnemonic  | Meaning               | Callee-saved ?    |
|   ---         | ---           | ---                   | ---               |
| rf0           |               | fp status regs        | -                 |
| rf1 - rf7     |               | temporary regs        | No                |
| rf8 - rf15    | rft0 - rft7   | temporary regs        | No                |
| rf16 - rf31   | rfa0 - rfa15  | temporary regs        | No                |
| rf32 - rf63   |               | callee saved regs     | Yes               |

### 1.4 RA寄存器（Return address registers）

RA寄存器的约定如下。高 16 位/低 48 位的详细定义见 SimRISC-00。

| Name          | ABI Mnemonic  | Meaning                                                    | Callee-saved |
|   ---         | ---           | ---                                                        | :---:        |
| ra0           |               | RAS control（低48位=0 时仅 RegRAS；≠0 时同时启用 MemRAS）       | —          |
| ra1 - ra62    |               | 返回地址栈 slot 1-62（call/ret 自动压栈/弹栈）                  | —          |
| ra63          | rasp          | RegRAS 栈顶（call/ret 操作的寄存器）                           | —          |

压栈溢出触发 RASOF 异常，弹栈下溢触发 RASUF 异常（详见 SimRISC-00）。

## 2. 数据表示

在Dadao中，我们使用术语`byte`表示8位的数据，`wyde`表示16位数据，`tetra`表示32位数据，`octa`表示64位数据。

### 2.1 Fundamental Types

DADAO 采用大端序（big-endian），多字节数据的最高有效字节存放在最低地址。

下表显示了ISO C中的标量类型和Dadao的标量类型对应关系：

|   Type            | C                     | sizeof    | Alignment | Dadao             |
|   ---             | ---                   | :---:     | :---:     | ---:              |
| Integral          | `_Bool`               | 1         | 1         | boolean           |
|                   | `char`                | 1         | 1         | signed byte       |
|                   | `signed char`         | 1         | 1         | signed byte       |
|                   | `unsigned char`       | 1         | 1         | unsigned byte     |
|                   | `short`               | 2         | 2         | signed wyde       |
|                   | `signed short`        | 2         | 2         | signed wyde       |
|                   | `unsigned short`      | 2         | 2         | unsigned wyde     |
|                   | `int`                 | 4         | 4         | signed tetra      |
|                   | `signed int`          | 4         | 4         | signed tetra      |
|                   | `enum`                | 4         | 4         | signed tetra      |
|                   | `unsigned int`        | 4         | 4         | unsigned tetra    |
|                   | `long`                | 8         | 8         | signed octa       |
|                   | `signed long`         | 8         | 8         | signed octa       |
|                   | `long long`           | 8         | 8         | signed octa       |
|                   | `signed long long`    | 8         | 8         | signed octa       |
|                   | `unsigned long`       | 8         | 8         | unsigned octa     |
|                   | `unsigned long long`  | 8         | 8         | unsigned octa     |
| Pointer           | `any-type *`          | 8         | 8         | unsigned octa     |
|                   | `any-type (*)()`      | 8         | 8         | unsigned octa     |
| Floating-point    | `float`               | 4         | 4         | single(IEEE-754)  |
|                   | `double`              | 8         | 8         | double(IEEE-754)  |

指向任何类型的空指针，即`NULL`，的值为`0`。

`size_t`类型的定义为`unsigned long long`。

### 2.2 Aggregates

聚合体（Aggregate）包括结构体（struct）和共用体（union），其内部的标量数据成员依照各自的规定对齐。

聚合体数据类型至少 8 字节对齐，采用 8 字节对齐方式。

16 字节值（如 binary128 浮点，见 §聚合类型参数 / §返回值）按 **16 字节**对齐；栈上的 16 字节值同样按 16 字节对齐（必要时跳过一个 8 字节槽位）。

聚合体数据可能需要填充来满足大小限制和对齐量限制。如果未指定填充内容，则默认填充 `0` 。

### 2.3 Array type

array 的起始地址按照 8 字节方式对齐。

数组的数据大小等于所有元素的数据大小之和。

## 3. 函数调用规范

本节描述标准的函数调用过程，包括栈帧的布局和参数传递等。

### 3.1 The Stack Frame

除了寄存器之外，每个函数都有一个属于自己的帧，该帧位于运行时的栈上。

栈从高地址向下增长。栈与帧的组织如下：

|  Position         | Contents                  | Frame     |
| ---               | ---                       | ---       |
| rb2 + 8n + 8      | memory argument octa n    |           |
| ...               | ...                       |           |
| rb2 + 8          | memory argument octa 0    | Previous  |
| rb2              | previous rb2 value        | Current   |
| rb2 - 8          | Saved regs or local vars  |           |
| ...               | ...                       |           |
| rbsp              | Saved regs or local vars  |           |

采用rb2作为帧指针是一种传统的用法，而实际上，可以采用rbsp直接访问帧上的数据；
这样做的好处在于函数的入口和出口可以缩减指令数量和访存行为，并且节省了一个寄存器。


### 3.2 传参：Parameter Passing

在参数值被计算出来后，这些参数值会放到寄存器中或压到栈上。

#### 3.2.1 参数寄存器：Parameter registers

Dadao使用以下寄存器传送参数，当参数超过寄存器数量时，使用栈传送。

- `rd16 - rd31`：数据参数寄存器
- `rb16 - rb31`：地址参数寄存器
- `rf16 - rf31`：浮点参数寄存器

三组参数寄存器各自独立计数，从 16 开始递增。参数按类型分配到对应 寄存器组，不共享槽位。例如 `read(int fd, void *buf, size_t count)` 的寄存器映射为：

| 参数 | 类型 | 寄存器 |
|------|------|--------|
| fd (int) | 标量 → rd | rd16 |
| buf (void *) | 指针 → rb | rb16 |
| count (size_t) | 标量 → rd | rd17 |

#### 3.2.2 标量参数：Scalar type parameter

标量参数传参时，按照如下规则转换后传递：

- 少于 8 字节的参数类型，例如_Bool，char，short，int，将类型提升到 8 字节后再传递，应保证符号位不变
- 参数类型为float，double，属于浮点型，参数传递时使用浮点寄存器，单精和双精浮点都使用单个寄存器存放相应数据
- 指针类参数传递时使用基址寄存器

#### 3.2.3 聚合类型参数：Aggregate parameter

聚合类型按以下规则传递，最多消耗 8 个寄存器槽位（64 字节）。

**HFA/HPA 递归判定流程**

1. **展开（flatten）**：递归展开聚合类型的所有嵌套 struct 成员，得到叶子字段列表。union 直接判定为不满足条件。
2. **同质检查**：HFA 要求所有叶子字段为同一浮点类型（float 或 double）；HPA 要求所有叶子字段为指针类型（指针指向的具体类型可以不同）。
3. **计数检查**：叶子字段总数 ≤ 8。

**同质浮点聚合（HFA, Homogeneous Floating-point Aggregate）**

满足 HFA 条件时，通过 RF bank 传递，每个叶子字段占 1 个 RF 槽位。

例如：
| 聚合类型 | 展开后 | 大小 | 传递方式 |
|---------|--------|------|---------|
| `struct { double x, y; }` | 2×double | 16B | RF16, RF17 |
| `struct { float a, b, c; }` | 3×float | 12B | RF16-18 |
| `struct { struct { double x,y; } a, b; }` | 4×double | 32B | RF16-19 |
| `struct { double a, b, c, d, e, f, g, h; }` | 8×double | 64B | RF16-23 |
| `struct { double x; }` | 1×double | 8B | RF16 |

以下情况不是 HFA：
| 聚合类型 | 原因 |
|---------|------|
| `struct { float f; void *p; }` | 混合类型（float + 指针） |
| `struct { float f; int i; }` | 混合类型（float + int） |
| `struct { double x; char c; }` | 含非浮点类型（char） |
| `union { float f; int i; }` | union 不展开 |
| `struct { double a,b,c,d,e,f,g,h,i; }` | 叶子字段 > 8 |

**同质指针聚合（HPA, Homogeneous Pointer Aggregate）**

满足 HPA 条件时，通过 RB bank 传递，每个叶子字段占 1 个 RB 槽位。

例如：
| 聚合类型 | 展开后 | 大小 | 传递方式 |
|---------|--------|------|---------|
| `struct { void *p, *q; }` | 2×void* | 16B | RB16, RB17 |
| `struct { int *a, *b, *c, *d; }` | 4×int* | 32B | RB16-19 |
| `struct { int *a, *b, *c, *d, *e, *f, *g, *h; }` | 8×int* | 64B | RB16-23 |
| `struct { struct { char *x; } a; char *b; }` | 2×char* | 16B | RB16, RB17 |
| `struct { int *p; void *q; }` | 2×指针 | 16B | RB16, RB17 |

以下情况不是 HPA：
| 聚合类型 | 原因 |
|---------|------|
| `struct { void *p; int i; }` | 混合类型（指针 + int） |
| `struct { int *a, *b, *c, *d, *e, *f, *g, *h, *i; }` | 叶子字段 > 8 |

**不满足 HFA/HPA 条件**：
- ≤ 64 字节：拆分为 1-8 个 8 字节块，放入 RD bank，**低地址块先入低号寄存器**（与 `ldm.o`/`stm.o` 寄存器号递增 = 地址递增一致）
- > 64 字节：通过指针引用（caller 在栈上分配临时空间，callee 通过 RB bank 中的指针访问）

**16 字节值：半字顺序与配对**

binary128 浮点、`__int128` 整数（其传参/返回当前未定义，若未来定义则沿用本序），以及大小恰为 16 字节、按上述规则归 RD 的聚合，均占**两个连续 8 字节槽**，遵循同一半字顺序：

- **高位半字在偶号（低号）槽，低位半字在奇号（高号）槽**。依据：大端下高位字节在低地址，而 `ldm.o`/`stm.o` 的寄存器号递增即地址递增（`SimRISC-01`），故低号槽装高半字时一条指令即可完成 16 字节搬运，无需交换。
- **配对必须自偶号槽起**：游标落在奇号槽时先跳过一个槽（该槽不承载本值）；所需槽位不足 ⇒ **整值走栈、不拆半**，游标既不跳过也不推进。
- 该顺序对参数寄存器（RD/RB/RF 各自的偶-奇对）、返回值寄存器（§返回值）与栈槽（最低地址 = 高半字）一致；栈上 16 字节值按 16 字节对齐（§栈溢出规则）。
- HFA/HPA 不受本条影响：其“每叶子 1 槽、按声明顺序递增”规则不变（叶子不合并为 16 字节值）。

#### 3.2.4 栈溢出规则

当某 bank 的可用寄存器槽位用完时，该 bank 的后续参数使用栈传递。

栈参数按**声明顺序从左到右**依次排列，8 字节对齐。三 bank 共享同一个栈增长方向，各组溢出参数连续紧凑存放。

溢出判定按 **bank 独立**（某 bank 槽位用尽只影响该 bank）；一旦参数进入栈传递，所有溢出参数按源声明中的**全局从左到右顺序**放入**同一个连续栈区**。

例如 `foo(int a1..a17, double* p1..p17)`：

| 参数 | bank | 位置 |
|------|------|------|
| a1 - a16 | RD | rd16 - rd31 |
| a17 | RD（溢出） | 栈（sp+0） |
| p1 - p16 | RB | rb16 - rb31 |
| p17 | RB（溢出） | 栈（sp+8） |

call 指令执行时 sp 必须 16 字节对齐（栈区起点 16 字节对齐；上段栈参数槽宽仍为 8 字节）。变参保存区每个保存槽 8 字节、按 8 字节槽宽排列（不要求 16 字节对齐）。

16 字节值（binary128 浮点、16 字节整数类聚合；`__int128` 的传参/返回当前未定义）占两个连续 8 字节栈槽，**16 字节对齐**（必要时跳过一个 8 字节槽位），**高半字在低地址**（与寄存器的偶-奇对同序，见 §聚合类型参数）。在 `call` 时 `sp` 16 字节对齐的前提下，栈上 16 字节值的**绝对地址无条件 16 字节对齐**。该参数所需两个槽位若超出所属 bank 的剩余槽位，则**整值使用栈传递、不拆半**，且不消耗该 bank 的槽位（其后参数仍按各 bank 独立计数继续分配）。

### 3.3 可变参数：Variable Arguments

`va_list` 是**七字段结构**（字段顺序固定，属 ABI 可观测事实），声明为长度为 1 的数组类型，使形参退化为指向该结构的指针，从而可按值传递与复制：

```c
typedef struct {
    uint64_t *rd_next;    /* 下一个可用 RD 参数槽（指向保存区） */
    uint64_t *rb_next;    /* 同上，RB */
    uint64_t *rf_next;    /* 同上，RF */
    int64_t   rd_left;    /* 本 bank 剩余可用槽数；0 = 已耗尽 */
    int64_t   rb_left;
    int64_t   rf_left;
    uint64_t *stack_next; /* 下一个栈溢出槽（= incoming_sp 起） */
} va_list[1];
```

七个字段均为 8 字节，共 56 字节、无填充。编译器、`va_list` 头文件与运行库三处必须逐字一致；`va_copy` 为逐字段复制，`va_end` 无动态资源（空操作）。

**寄存器保存区（callee 侧）**

变参函数在**自己的栈帧**内为每个参数 bank 分配寄存器保存区：自该 bank 的 `start`（命名参数占用后的下一个槽）至 31 连续存放，用 `stm.o` 一条指令保存一个 bank（RD / RB / RF 各一条）。命名参数已用尽某 bank（`start = 32`）时，该 bank 不分配保存区，其游标直接视为已耗尽。调用者**不写任何保存区**，只按 §传参 规则把参数放入寄存器或栈；寄存器耗尽的参数仍在 `incoming_sp` 起的连续栈区、按全局声明序存放。

**va_start(ap, last_named_arg)**

按命名参数在各 bank 的占用数初始化三游标与三剩余计数：`rd_next` / `rb_next` / `rf_next` 分别指向该 bank 保存区的首个可变参数槽，`rd_left` / `rb_left` / `rf_left` = `32 - start`；`stack_next` = `incoming_sp`（`rb2 + 8`）。

**va_arg(ap, type)**

1. 按 §聚合类型参数 分类确定 `type` 所属 bank 与槽数：HFA → RF（每叶子 1 槽）、HPA → RB（每叶子 1 槽）、其它与 union / 混合结构 → RD（每 8 字节块 1 槽）；`> 64` 字节的聚合只经间接指针传递。
2. 该 bank 的 `left` ≥ 本参数所需槽数（HFA/HPA 取整组叶子数；通用聚合取块数；16 字节值取 2 或 3，见第 4 步）⇒ 从该 bank 游标取，游标 += 槽数、`left` -= 槽数。
3. 否则从 `stack_next` 取，`stack_next` += 栈占用（标量 8 字节；16 字节值 16 字节；`> 16` 字节聚合取 `round_up(size, 8)`，按 `max(8, align)` 对齐补足）；**该 bank 的游标与 `left` 都不推进**，以免后续参数错位。
4. 16 字节值按 §聚合类型参数：高半字在偶号槽、低半字在奇号槽；游标在偶号槽时需 2 槽，在奇号槽时先跳 1 槽、需 3 槽；`left` 不足则**整值走栈**（不跳过、不推进）。
5. HFA/HPA 按叶子逐个还原（不按整块字节拼接）；`> 64` 字节聚合从指针按值复制。

**大端序 slot 布局**

8 字节 slot 内，N 字节类型的有效值**右对齐**（byte `8-N` 至 `7`），低地址字节（byte 0 至 `8-N-1`）为符号/零扩展位。

`int 0x11223344` 在 8B slot 中：
```
byte 0: 0x00  ← 符号扩展
byte 1: 0x00
byte 2: 0x00
byte 3: 0x00
byte 4: 0x11  ← int 值起点 (offset = 8 - sizeof(int) = 4)
byte 5: 0x22
byte 6: 0x33
byte 7: 0x44
```

**实参提升**（caller 端，C 标准）：

| 实参类型 | 提升为 |
|---------|--------|
| `char` / `short`（有/无符号）、`_Bool` | `int` |
| `float` | `double` |
| `int` / `long` / `long long` / 指针 / `double` | 不变 |

`va_arg` 必须使用**提升后**类型：`va_arg(ap, float)` 为未定义行为；`va_arg(ap, char)` 须写 `va_arg(ap, int)` 再截断。

**float 的寄存器表示**

RF 槽的**低 32 位**存放 binary32 值，高 32 位不作规定（32 位浮点存取只作用于低半，见 SimRISC-00 / SimRISC-01 / SimRISC-03）；32 位整数同样占低 32 位并由 caller 完成符号/零扩展。HFA 的 `float` 叶子亦占低 32 位。

**示例**

`foo(int a, double b, void* c, int d, /* 命名 4 个 */ int e, double f)`：

- 命名参数占用 `a → rd16`、`b → rf16`、`c → rb16`、`d → rd17`。
- callee 保存区 = `rd18–rd31`、`rf17–rf31`、`rb17–rb31`（三个 `stm.o`）。
- `va_start(ap, d)`：`rd_next` → 保存区首个 RD 槽、`rd_left = 14`；`rf_next` → 首个 RF 槽、`rf_left = 15`；`rb_next` → 首个 RB 槽、`rb_left = 15`；`stack_next` = `incoming_sp`。
- `va_arg(ap, int)` 取 `e`（RD 保存槽，`rd_left` → 13），`va_arg(ap, double)` 取 `f`（RF 保存槽，`rf_left` → 14）。

### 3.4 返回值：Returning of Values

Dadao 使用**固定返回寄存器组**存放返回值：整数 `rd8`、指针 `rb8`、浮点 `rf8`。返回寄存器区（`rd8-rd15` / `rb8-rb15` / `rf8-rf15`）与参数寄存器区（`rd16-rd31` / `rb16-rb31` / `rf16-rf31`）**互不重叠**。

#### 3.4.1 标量类型返回值：Scalar type return

- 当返回值为绝对地址时，采用rb8作为返回值寄存器
- 当返回值为浮点数时，采用rf8作为返回值寄存器
- 返回值为 16 字节浮点值（binary128）时，占**两个连续返回寄存器槽**：**高半字在偶号槽 `rf8`、低半字在奇号槽 `rf9`**（与 §聚合类型参数 的参数同序；配对必须自偶号槽起，不足则整值改用 sret、不拆半）
- 其它情况，采用rd8作为返回值寄存器

#### 3.4.2 多返回值

需要返回多个标量时，按**返回值声明顺序**、在同一 bank 内自 `8` 起**递增**分配返回寄存器：

- 第 1 个返回值：rd8（或 rb8/rf8，依类型而定）
- 第 2 个返回值：rd9
- 第 3 个返回值：rd10，依次至 rd15

> **混合类型多返回值**：按声明顺序扫描，每个值按其类型分配到对应 bank（整数→rd，指针/地址→rb，浮点→rf）。各 bank 独立计数、自各自 bank 的第 8 号寄存器起**递增**分配，互不干扰。返回值顺序（第 1 个 → rd8/rb8/rf8）属 **ABI 可观测语义**，调用方与被调方必须一致。
>
> **每 bank 上限 K = 8**：任一 bank 的返回值占用至多 8 个（`rd8-rd15` / `rb8-rb15` / `rf8-rf15`）；任一 bank 超过 8 个，或无法用上述规则承载时，改用 **sret（隐藏指针）** 模式（见下）。
>
> 例：`(int a, double* p, float f)` → a 为 rd8，p 为 rb8，f 为 rf8。
> 例：`(int x, int y, double* p)` → x 为 rd8，y 为 rd9，p 为 rb8。

#### 3.4.3 聚合类型返回值：Aggregate return

聚合类型的各成员同样按上述返回寄存器规则，依**声明顺序**占用返回寄存器（每 bank 自 8 起递增，各 bank 至多 8 个）。

当聚合类型（或多返回值整体）无法用返回寄存器承载时——任一 bank 的占用超过 8 个（超出 `rd8-rd15` / `rb8-rb15` / `rf8-rf15`），或无法按上述规则分配——采用 **hidden sret（structure return）模式**：

- caller 在栈上预分配返回值空间，将空间地址作为隐藏的第一个参数，通过 **RB16** 传入 callee
- callee 将聚合返回值写入 `sret_ptr` 指向的地址，返回时 `RB16` 仍保存该地址供 caller 读取
- sret 指针占用 **RB16**，其后地址参数自 **RB17** 起计数

例如 `struct Big make_big(int a)` 展开为：

```
void make_big(struct Big* sret_ptr, int a)
// sret_ptr → RB16
// a        → RD16
```

## 4. 系统调用规范

系统调用通过 `trap cfxha, immu18` 指令发起，其中 `cfxha` 指定目标核芯功能扩展，`immu18` 为硬件事务编号（功能编号）。

系统调用号存放在 RD15 寄存器中，参数使用 RD16 - RD31、RB16 - RB31 和 RF16 - RF31 传参，返回值放在 RD8 寄存器中。参数按类型分配到对应 寄存器组，三组寄存器各自独立计数。

`trap` 指令的 `immu18` 与 RD15 为两个独立层次：
- `immu18`：指令编码层的硬件事务编号，用于硬件异常分发，决定"是什么调用"
- RD15：软件调用约定层的系统调用号，作为附加参数传递具体子功能

两者互不覆盖，操作系统可根据 `immu18` 分类后再依 RD15 进一步分发。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.9.3（2026-10-26）

- 通用聚合（不满足 HFA/HPA）传参：≤ 64 字节拆为 8 字节块放入 RD bank 时，**低地址块先入低号寄存器**（与 `ldm.o`/`stm.o` 寄存器号递增 = 地址递增一致）；16 字节值的半字顺序与配对规则不变，HFA/HPA 不受影响。
- 栈溢出规则补消歧：溢出判定按 bank 独立；一旦进入栈传递，所有溢出参数按源声明的全局从左到右顺序放入同一个连续栈区。
- 寄存器布局重排：`rb2`=FP（无条件保留、无别名）、`rb3`=TP，`rb4`–`rb7` caller-saved，`rb32`–`rb63` 为连续 callee-saved 池（`rb63` 为普通成员）；`rd2`/`rd3` 保留，`rd4`–`rd7` caller-saved。
- 返回值契约收口：返回寄存器 `rd8`/`rb8`/`rf8`，按声明序每 bank 递增 K=8，超出者经 `rb16`（sret）。
- 系统调用 / semihosting 返回值统一为 `rd8`。
- 聚合传参收口：通用 / HFA / HPA 统一「最多 8 个寄存器槽位（64 字节）」，>64 B 走间接指针。
- 栈布局以 `rb2` 为界描述，移除 red zone。
- 寄存器表补 `rbip` 语义明文：`rb0`（`rbip`）即 **`IP`** = **当前正在执行的指令的地址**（非主流 ISA 的「下一条指令」口径；本 ISA 无 `±4` 流水偏移）。
- 可变参数 ABI 重定：`va_list` 由 `void*` 改为七字段结构（三 bank 游标 + 三剩余计数 + 栈游标）；寄存器保存区改由 callee 在入口用 `stm.o` 写入，调用者不再写整块保存区；`va_arg` 按类别 / 槽数 / 栈切换推进，bank 不足时整值取自栈且不推进该 bank 游标。
- 16 字节值（binary128 浮点、未来若定义的 128 位整数、16 字节整数类聚合）传参 / 返回：高半字在偶号槽、低半字在奇号槽，配对自偶号槽起，槽位不足则整值走栈（不拆半）；栈上高半字在低地址并按 16 字节对齐。
- `float` 占 RF 槽低 32 位（高 32 位不作规定）；32 位整数同样在低 32 位并由调用者完成符号 / 零扩展。
- 调用点 SP 对齐由 8 字节改为 16 字节：`call` 执行时 `sp` 必须 16 字节对齐；栈参数仍按 8 字节槽排列，16 字节值按 16 字节对齐（SP 16 字节对齐下其绝对地址无条件对齐）。
- 与上游 SimRISC 0.5.5 基线对齐。
- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- 汇编格式迁移新格式；`LD`/`ST`/`cs.`/`br.` 等指令名统一；伪指令迁回 SimRISC。

### 0.9.2（上游基线；导入日 2026-07-14，发布日不详）

- 上游 DADAO 应用程序二进制接口（ABI）基线（基于 SimRISC 0.4.1）。
