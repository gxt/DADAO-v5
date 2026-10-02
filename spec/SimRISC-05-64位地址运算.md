# SimRISC64位地址运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：64位地址运算**（4 条）— add.si-rb/add.so-rb/cmp.uo-rb/sub.so-rb

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 64位地址运算（4 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.si` | `riii` | `rb` | `add.si rbHA, imms18` | `add.si_riii_rb` |
| `add.so` | `orrr` | `rb` | `add.so rbHB, rbHC, rdHD` | `add.so_orrr_rb` |
| `cmp.uo` | `orrr` | `rb` | `cmp.uo rdHB, rbHC, rbHD` | `cmp.uo_orrr_rb` |
| `sub.so` | `orrr` | `rb` | `sub.so rbHB, rbHC, rdHD` | `sub.so_orrr_rb` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `cmp.uo_orrr_rb`（1 条）
* `dst_rb0`：目的 rb0 → ILLI — `add.si_riii_rb`, `add.so_orrr_rb`, `sub.so_orrr_rb`（3 条）
<!-- LEGALITY_END -->


## 算术运算类指令

### 加减操作

针对rb寄存器的加减运算，操作数类型为 `orrr`。
两个源操作数寄存器为`rbHC`和`rdHD`，采用`rbHB`作为目的寄存器。
`add.so-rb`/`sub.so-rb` 执行二进制补码的 64 位加减法，全 64 位参与运算。地址计算仅在低 48 位有效，溢出丢弃。用户可通过 `rbHB` 的高 16 位（bits[63:48]）判断是否发生地址溢出，从而避免地址计算错误。
具体指令如下：

```simrisc
add.so  rbHB, rbHC, rdHD
sub.so  rbHB, rbHC, rdHD
```

### 自增自减

自增自减指令需要一个寄存器和一个立即数，操作数类型是 `riii`，立即数为18位有符号数，经过符号扩展后与寄存器执行加法，结果写回同一寄存器。
由于立即数采用补码的编码方式，无需区分加减操作。
具体指令如下：

```simrisc
add.si  rbHA, imms18
```

`add.si` 为全 64 位运算，用户可通过 `rbHA` 的高 16 位判断地址溢出。
由于imms18为有符号数，该加法指令也隐含实现了减法指令。
针对rb寄存器的add.si指令的重要性在于对栈指针的操作，在没有提供专门的push/pop类指令的情况下，栈指针需要通过显式的加减移动其位置。

### 比较操作

`cmp.uo-rb` 对两个操作数的**低 48 位**进行**无符号**比较，**比较结果 -1/0/1** 分别对应小于/等于/大于，写入目的寄存器。结果 -1/0/1 可以作为有符号数解读，但主要用于区分三种关系。
后续的指令可以根据负数、非负数、零、非零、正数、非正数做出组合判断。

操作数类型是`orrr`。
具体指令如下：

```simrisc
cmp.uo  rdHB, rbHC, rbHD
```

> **注**：rb0 通用约定（rb0 读出为当前指令的地址，只读，显式目的触发 ILLI）和 RB 高 16 位行为见 SimRISC-00。