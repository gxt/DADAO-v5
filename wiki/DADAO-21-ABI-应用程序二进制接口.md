
# ABI

> **版本：0.9.2**（与 AEE 版本号一致，同步更新。基于 SimRISC 0.5.0 指令系统设计）

通过制定ABI，使得独立编译、汇编得到的代码，可以被正确链接、执行。手工编写的汇编代码，也应遵循ABI规范。

## 寄存器规范

Dadao提供了四组64个64位寄存器，所有这些寄存器对于一个运行中的进程而言都是全局可见的。

### RD寄存器（Data registers）

RD寄存器的约定如下：

| Name          | ABI Mnemonic  | Meaning           | Callee-saved ?    |
|   ---         | ---           | ---               | ---               |
| rd0           | rdzero        | Zero              | Immutable         |
| rd1           | rderrno       | error number      | -                 |
| rd2 - rd7     |               | reserved（编译器不得分配使用） | -                 |
| rd8 - rd15    | rdt0 - rdt7   | temporary regs    | No                |
| rd16 - rd31   | rda0 - rda15  | temporary regs    | No                |
| rd32 - rd63   |               | callee saved regs | Yes               |

### RB寄存器（Base registers）

RB寄存器的约定如下：

| Name          | ABI Mnemonic  | Meaning               | Callee-saved ?    |
|   ---         | ---           | ---                   | ---               |
| rb0           | rbip          | instruction pointer   | -                 |
| rb1           | rbsp          | stack pointer         | Yes               |
| rb2           | rbfp          | frame pointer         | Yes               |
| rb3           | rbgp          | global pointer        | -                 |
| rb4           | rbtp          | thread pointer        | -                 |
| rb5 - rb7     |               | reserved              | -                 |
| rb8 - rb15    | rbt0 - rbt7   | temporary regs        | No                |
| rb16 - rb31   | rba0 - rba15  | temporary regs        | No                |
| rb32 - rb63   |               | callee saved regs     | Yes               |

### RF寄存器（Floating-point registers）

RF寄存器的约定如下：

| Name          | ABI Mnemonic  | Meaning               | Callee-saved ?    |
|   ---         | ---           | ---                   | ---               |
| rf0           |               | fp status regs        | -                 |
| rf1 - rf7     |               | temporary regs        | No                |
| rf8 - rf15    | rft0 - rft7   | temporary regs        | No                |
| rf16 - rf31   | rfa0 - rfa15  | temporary regs        | No                |
| rf32 - rf63   |               | callee saved regs     | Yes               |

### RA寄存器（Return address registers）

RA寄存器的约定如下。高 16 位/低 48 位的详细定义见 AEE §返回地址栈。

| Name          | ABI Mnemonic  | Meaning                                                    | Callee-saved |
|   ---         | ---           | ---                                                        | :---:        |
| ra0           |               | RAS control（低48位=0 时仅 RegRAS；≠0 时同时启用 MemRAS）       | —          |
| ra1 - ra62    |               | 返回地址栈 slot 1-62（call/ret 自动压栈/弹栈）                  | —          |
| ra63          | rasp          | RegRAS 栈顶（call/ret 操作的寄存器）                           | —          |

压栈溢出触发 RASOF 异常，弹栈下溢触发 RASUF 异常（详见 AEE）。

## 数据表示

在Dadao中，我们使用术语`byte`表示8位的数据，`wyde`表示16位数据，`tetra`表示32位数据，`octa`表示64位数据。

### Fundamental Types

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

### Aggregates

聚合体（Aggregate）包括结构体（struct）和共用体（union），其内部的标量数据成员依照各自的规定对齐。

聚合体数据类型至少 8 字节对齐，采用 8 字节对齐方式。

聚合体数据可能需要填充来满足大小限制和对齐量限制。如果未指定填充内容，则默认填充 `0` 。

### Array type

array 的起始地址按照 8 字节方式对齐。

数组的数据大小等于所有元素的数据大小之和。

## 函数调用规范

本节描述标准的函数调用过程，包括栈帧的布局和参数传递等。

### The Stack Frame

除了寄存器之外，每个函数都有一个属于自己的帧，该帧位于运行时的栈上。

栈从高地址向下增长。栈与帧的组织如下：

|  Position         | Contents                  | Frame     |
| ---               | ---                       | ---       |
| rbfp + 8n + 8     | memory argument octa n    |           |
| ...               | ...                       |           |
| rbfp + 8          | memory argument octa 0    | Previous  |
| rbfp              | previous rbfp value       | Current   |
| rbfp - 8          | Saved regs or local vars  |           |
| ...               | ...                       |           |
| rbsp              | Saved regs or local vars  |           |
| rbsp - 128        |                           | Red zone  |

采用rbfp作为栈帧的frame pointer是一种传统的用法，而实际上，可以采用rbsp直接访问帧上的数据；
这样做的好处在于函数的入口和出口可以缩减指令数量和访存行为，并且节省了一个寄存器。

rbsp向下128字节的地方，被认为是保留的，不会被信号处理函数更改。
因此，函数可以使用这一区域存储那些不会跨越函数调用的临时数据。
尤其是对于叶节点函数，可以利用这一区域作为整个帧；从而无需在函数入口和出口调整rbsp的值。
这一区域也被称为red zone。

<!--
采用128字节的原因，在amd64-abi中的解释是：Locations within 128 bytes can be addressed using one-byte displacements.
-->

### 传参：Parameter Passing

在参数值被计算出来后，这些参数值会放到寄存器中或压到栈上。

#### 参数寄存器：Parameter registers

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

#### 标量参数：Scalar type parameter

标量参数传参时，按照如下规则转换后传递：

- 少于 8 字节的参数类型，例如_Bool，char，short，int，将类型提升到 8 字节后再传递，应保证符号位不变
- 参数类型为float，double，属于浮点型，参数传递时使用浮点寄存器，单精和双精浮点都使用单个寄存器存放相应数据
- 指针类参数传递时使用基址寄存器

#### 聚合类型参数：Aggregate parameter

聚合类型按以下规则传递，最多消耗 4 个寄存器槽位（32 字节）。

**HFA/HPA 递归判定流程**

1. **展开（flatten）**：递归展开聚合类型的所有嵌套 struct 成员，得到叶子字段列表。union 直接判定为不满足条件。
2. **同质检查**：HFA 要求所有叶子字段为同一浮点类型（float 或 double）；HPA 要求所有叶子字段为指针类型（指针指向的具体类型可以不同）。
3. **计数检查**：叶子字段总数 ≤ 4。

**同质浮点聚合（HFA, Homogeneous Floating-point Aggregate）**

满足 HFA 条件时，通过 RF bank 传递，每个叶子字段占 1 个 RF 槽位。

例如：
| 聚合类型 | 展开后 | 大小 | 传递方式 |
|---------|--------|------|---------|
| `struct { double x, y; }` | 2×double | 16B | RF16, RF17 |
| `struct { float a, b, c; }` | 3×float | 12B | RF16-18 |
| `struct { struct { double x,y; } a, b; }` | 4×double | 32B | RF16-19 |
| `struct { double x; }` | 1×double | 8B | RF16 |

以下情况不是 HFA：
| 聚合类型 | 原因 |
|---------|------|
| `struct { float f; void *p; }` | 混合类型（float + 指针） |
| `struct { float f; int i; }` | 混合类型（float + int） |
| `struct { double x; char c; }` | 含非浮点类型（char） |
| `union { float f; int i; }` | union 不展开 |
| `struct { double a,b,c,d,e; }` | 叶子字段 > 4 |

**同质指针聚合（HPA, Homogeneous Pointer Aggregate）**

满足 HPA 条件时，通过 RB bank 传递，每个叶子字段占 1 个 RB 槽位。

例如：
| 聚合类型 | 展开后 | 大小 | 传递方式 |
|---------|--------|------|---------|
| `struct { void *p, *q; }` | 2×void* | 16B | RB16, RB17 |
| `struct { int *a, *b, *c, *d; }` | 4×int* | 32B | RB16-19 |
| `struct { struct { char *x; } a; char *b; }` | 2×char* | 16B | RB16, RB17 |
| `struct { int *p; void *q; }` | 2×指针 | 16B | RB16, RB17 |

以下情况不是 HPA：
| 聚合类型 | 原因 |
|---------|------|
| `struct { void *p; int i; }` | 混合类型（指针 + int） |

**不满足 HFA/HPA 条件**：
- ≤ 32 字节：拆分为 1-4 个 8 字节块，放入 RD bank，高位块先入高寄存器
- > 32 字节：通过指针引用（caller 在栈上分配临时空间，callee 通过 RB bank 中的指针访问）

#### 栈溢出规则

当某 bank 的可用寄存器槽位用完时，该 bank 的后续参数使用栈传递。

栈参数按**声明顺序从左到右**依次排列，8 字节对齐。三 bank 共享同一个栈增长方向，各组溢出参数连续紧凑存放。

例如 `foo(int a1..a17, double* p1..p17)`：

| 参数 | bank | 位置 |
|------|------|------|
| a1 - a16 | RD | rd16 - rd31 |
| a17 | RD（溢出） | 栈（sp+0） |
| p1 - p16 | RB | rb16 - rb31 |
| p17 | RB（溢出） | 栈（sp+8） |

call 指令执行时 sp 必须 8 字节对齐。变参保存区同样 8 字节对齐。

### 可变参数：Variable Arguments

DADAO 采用 `va_list` 即为 `void*` 指针的极简实现，调用者在 call 指令前将所有参数按调用顺序依次写入栈上的连续保存区。

**保存区布局**

调用者按参数在调用点出现的顺序，将每个参数以 8 字节为单位依次写入保存区。保存区大小 = 总参数个数 × 8 字节。

三组参数寄存器（rd16-rd31 / rb16-rb31 / rf16-rf31）独立计数导致 callee 无法仅从寄存器重建声明顺序，保存区必须由调用者在调用点写入，不分区存放。

**栈布局顺序**

栈上参数区域按地址从低到高排列：**寄存器溢出参数区 → 局部变量 → varargs 保存区**。溢出区紧接寄存器参数槽位之后，保存区在最高地址，二者均为 8 字节对齐、连续紧凑存放。

**大于 8 字节的聚合变参**

聚合体 > 8 字节（如 16 字节 struct）按自然对齐（最大 8 字节）拆分为多个 8 字节单元，按字节序依次占用连续 slot。例如 16 字节 struct 占两个连续 slot，32 字节 struct 占四个连续 slot。callee 通过 `va_arg` 宏按原始类型大小逐 slot 读取并重组。

**大端序 slot 布局**

DADAO 为大端序。8 字节 slot 内，N 字节类型的有效值**右对齐**（byte `8-N` 至 `7`），低地址字节（byte 0 至 `8-N-1`）为符号/零扩展位。

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

| 实参类型 | 提升为 | 写入 slot 方式 |
|---------|--------|--------------|
| `char` / `short`（有/无符号） | `int`（32 位符号扩展后放 rd） | `*(uint64_t*)slot = rd_value` |
| `float` | `double`（64 位放 rf） | `*(double*)slot = rf_value` |
| `int` / `long` / `long long` | 64 位（符号/零扩展放 rd） | `*(uint64_t*)slot = rd_value` |
| 指针 | 64 位（放 rb） | `*(uint64_t*)slot = rb_value` |
| `double` | 不变（64 位放 rf） | `*(double*)slot = rf_value` |

**示例**

`foo(int a, double b, void* c, int d,  /* 命名 4 个 */  int e, double f)`：

```
sp + 0:   [a: 8B, byte0-3=0扩展, byte4-7=a值]  (rd16)
sp + 8:   [b: 8B, double 全64位]               (rf16)
sp + 16:  [c: 8B, 指针 全64位]                (rb16)
sp + 24:  [d: 8B, byte0-3=0扩展, byte4-7=d值]  (rd17)
sp + 32:  [e: 8B, 同 d]   ← va_start(ap, d) 指向此处
sp + 40:  [f: 8B, double]
```

- 保存区共 48 字节（6 × 8）。
- 命名参数同时装入对应参数寄存器，callee 可直接从寄存器访问命名参数。
- 若某参数根据传参规则应放入栈（寄存器槽用尽），该参数在保存区中的位置保持不变，同时也会被调用者压入 callee 可寻址的栈位置。

**va_list 定义**

```c
typedef void* va_list;
```

**va_start(ap, last_named_arg)**

`last_named_arg` 是第 N 个参数（从 1 计），保存区基址 = 调用点 sp：

```c
ap = (char*)sp + N * 8;
```

**va_arg(ap, type)**

大端序下 type 右对齐在 slot 末尾，从 `slot + (8 - sizeof(type))` 读取：

```c
#define va_arg(ap, type) \
    (*(type*)((char*)((ap += 8) - 8) + (8 - sizeof(type))))
```

- 统一 8 字节步进（无论 type 大小）。
- `va_arg(ap, int)` ≡ `*(int*)((char*)ap + 4)`（读 slot byte 4-7）。
- `va_arg(ap, long long)` ≡ `*(long long*)ap`（读全部 8 字节）。
- `va_arg(ap, char)` 需用 `va_arg(ap, int)` 再截断（C 标准提升规则）。

### 返回值：Returning of Values

Dadao中，通常采用最后一个参数寄存器存放返回值。
当需要多个返回值时，可以以参数寄存器的逆序提供多个返回值寄存器。

#### 标量类型返回值：Scalar type return

- 当返回值为绝对地址时，采用rb31作为返回值寄存器
- 当返回值为浮点数时，采用rf31作为返回值寄存器
- 其它情况，采用rd31作为返回值寄存器

#### 多返回值

需要返回多个标量时，按参数寄存器的逆序使用：

- 第 1 个返回值：rd31（或 rb31/rf31，依类型而定）
- 第 2 个返回值：rd30
- 第 3 个返回值：rd29，依次至 rd16

> **混合类型多返回值**：从声明顺序的最后一个返回值向前扫描，每个值按其类型分配到对应 bank（整数→rd，指针/地址→rb，浮点→rf）。各 bank 独立逆序分配，从各自 bank 的最高编号寄存器开始占用，互不干扰。同一 bank 内的多返回值连续占用递减编号。
>
> 例：`(int a, double* p, float f)` → a 为 rd31，p 为 rb31，f 为 rf31。
> 例：`(int x, int y, double* p)` → x 为 rd31，y 为 rd30，p 为 rb31。
>
> 聚合类型 > 64 位仍采用 sret 模式，不适用多返回值。

#### 聚合类型返回值：Aggregate return

长度大于 64 位的聚合类型，采用 **hidden sret（structure return）模式**：

- caller 在栈上预分配返回值空间，将空间地址作为隐藏的第一个参数，通过 **RB16** 传入 callee
- callee 将聚合返回值写入 `sret_ptr` 指向的地址，返回时 `RB16` 仍保存该地址供 caller 读取

例如 `struct Big make_big(int a)` 展开为：

```
void make_big(struct Big* sret_ptr, int a)
// sret_ptr → RB16
// a        → RD16
```

长度 ≤ 64 位的聚合类型，使用标量返回值规则（通过 RD31 返回）。

## 汇编兼容性

汇编器应提供以下兼容性支持：

### 伪指令（pseudo instructions）

汇编器需要提供以下伪指令的支持：

`nop`伪指令，含义为no operation，等价于`swym 0`。

`ret`伪指令，等价于`ret rd0, 0`。

`not`伪指令，等价于 `xnor rdhb, rdhc, rd0` 或 `xnor rdhb, rd0, rdhc`（源和目的可同可异，将 `rd0` 作为 `rdhd` 操作数实现对另一操作数的 64 位取反）。详细规则见 SimRISC-01 § 位操作指令。

`setrd`伪指令将64位立即数、symbol的绝对地址或另一个寄存器的值赋给`rdxx`寄存器。

```simrisc
setrd rdxx, imms64
setrd rdxx, symbol

setrd rdxx, rdyy
setrd rdxx, rbyy
setrd rdxx, rfyy
setrd rdxx, rayy
```

一个64位立即数由4个wyde组成，因此，64位立即数的设置通常会先用setzw/setow设置其中一个wyde，然后orw/andnw进行其它wyde的改动。
对于16位的short类型，可以转换为一条指令完成；对于32位的int类型，也只需要两条指令。

`setrb`伪指令将64位立即数、symbol的绝对地址或另一个rd或rb寄存器的值赋给`rbxx`寄存器。

```simrisc
setrb rbxx, immu64
setrb rbxx, symbol

setrb rbxx, rdyy
setrb rbxx, rbyy
```

rb寄存器的设置通常会先用setzw设置wyde 0，然后orw进行其它wyde的改动；或者先用setzw设置wyde 1或wyde 2，然后用addi指令进行加减操作。

`setrf`伪指令将64位立即数或另一个rd或rf寄存器的值赋给`rfxx`寄存器。

```simrisc
setrf rfxx, immu64

setrf rfxx, rdyy
setrf rfxx, rfyy
```

rf寄存器的设置采用setw指令，双精度浮点需要四条setw指令；由于单精度浮点数采用寄存器中的低32位，因此只需要w0和w1两条setw指令。

### 指导符（directives）

由于历史原因，汇编器中的word的定义并不一致，因此，Dadao采用了Knuth的MMIX中的数据长度定义，并在汇编器中额外定义了4个指导符：

- `.dd.b08`：8位数据，1个字节
- `.dd.w16`：16位数据，2个字节
- `.dd.t32`：32位数据，4个字节
- `.dd.o64`：64位数据，8个字节

注意：Dadao中的octa含义和gas中的.octa定义不一致。
Dadao中的octa是64位，即8字节，而gas中的.octa定义的数据是16字节（octa-word，而每个word是2字节）。
因此，不建议使用gas中的.octa。

### 汇编器选项

除了通用的选项之外，Dadao添加了以下选项：

- -multiple-to-single：将多寄存器指令转换为一系列的单寄存器指令；转换过程保持助记符（即opcode）不变

## 地址空间布局

应用程序建议使用不超过 32 个 PTBR，按需申请而非一次性分配。各 PTBR 按用途划分独立的虚拟地址空间区域：

| PTBR | 用途 | TLB 切换行为 |
|------|------|:--:|
| 0-15 | 进程私有：代码、数据、栈、堆、备用 | invalid |
| 16-31 | 共享库、动态链接、内核映射、共享内存 | **保留** |

进程切换时，仅 invalid 进程私有的 PTBR 对应的 TLB 集合。标记为"保留"的 PTBR 对应的 TLB 集合不做无效化处理，从而避免共享代码和内核映射的 TLB 抖动。

```simrisc
; 进程切换示例：invalid 已申请的私有 PTBR（最多 16 个）
setrd   rd2, 0                     ; 循环变量
cfx_tlb_inv_loop:
    ; 仅 invalid PTBR 0-15
    shlu    rd3, rd2, 42              ; rd3 = cfxcode << 42（构造 addr_start）
    cfx2rc  cfx_tlb_addr_start, rd3
    setrd   rd3, 0x40000000000     ; 0x40000000000（2^42） = 集合内全部 VA 空间
    cfx2rc  cfx_tlb_addr_size, rd3
    setrd   rd4, 2                 ; bit1 = invalid by addr range
    cfx2rc  cfx_tlb_control, rd4
    addi    rd2, rd2, 1
    setrd   rd3, 16
    cmps    rd5, rd2, rd3          ; rd5 = rd2 < rd3 ?
    brn     rd5, cfx_tlb_inv_loop
```

## 系统调用规范

系统调用通过 `trap cfxcode, immu18` 指令发起，其中 `cfxcode` 指定目标核芯功能扩展，`immu18` 为硬件事务编号（功能编号）。

系统调用号存放在 RD15 寄存器中，参数使用 RD16 - RD31、RB16 - RB31 和 RF16 - RF31 传参，返回值放在 RD31 寄存器中。参数按类型分配到对应 寄存器组，三组寄存器各自独立计数。

`trap` 指令的 `immu18` 与 RD15 为两个独立层次：
- `immu18`：指令编码层的硬件事务编号，用于硬件异常分发，决定"是什么调用"
- RD15：软件调用约定层的系统调用号，作为附加参数传递具体子功能

两者互不覆盖，操作系统可根据 `immu18` 分类后再依 RD15 进一步分发。
