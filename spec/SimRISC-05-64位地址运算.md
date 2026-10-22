# SimRISC64位地址运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：64位地址运算** — add.si-rb/aip.si-rb/add.o/cmp.uo-rb/sub.o(bbd)/sub.o(dbb)

## 1. 加减操作

针对rb寄存器的加减运算，操作数类型为 `orrr`。
`bbd` 形态的两个源操作数寄存器为`rbHC`和`rdHD`，采用`rbHB`作为目的寄存器。
`add.o`/`sub.o` 执行二进制补码的 64 位加减法，全 64 位参与运算，结果完整保留 64 位（`rbHB[63:0]`）。加减本身不做地址截断；**仅当以该结果访存时**，硬件取 `rbHB[47:0]`（低 48 位）为有效地址，`rbHB[63:48]` 为地址计算的高 16 位、表示地址溢出。用户可通过 `rbHB` 的高 16 位（bits[63:48]）判断是否发生地址溢出，从而避免地址计算错误。
此外还有 `dbb` 形态的 `sub.o`：两个源操作数寄存器为`rbHC`和`rbHD`，目的寄存器为`rdHB`，执行二进制补码的 64 位减法（`rdHB = rbHC − rbHD`），全 64 位参与运算；**单条、无 `.s`/`.u` 变体**（64 位单目的结果位型与符号性无关）。
具体指令如下：

```simrisc
add.o  rbHB, rbHC, rdHD
sub.o  rbHB, rbHC, rdHD
sub.o  rdHB, rbHC, rbHD
```

## 2. 自增自减

自增自减指令需要一个寄存器和一个立即数，操作数类型是 `riii`，立即数为18位有符号数，经过符号扩展后与寄存器执行加法，结果写回同一寄存器。
由于立即数采用补码的编码方式，无需区分加减操作。
具体指令如下：

```simrisc
add.si  rbHA, imms18
```

`add.si` 为全 64 位运算，结果完整保留 64 位（`rbHA[63:0]`）；**仅当以该结果访存时**取 `rbHA[47:0]`（低 48 位）为有效地址，用户可通过 `rbHA` 的高 16 位（bits[63:48]）判断地址溢出。
由于imms18为有符号数，该加法指令也隐含实现了减法指令。
针对rb寄存器的add.si指令的重要性在于对栈指针的操作，在没有提供专门的push/pop类指令的情况下，栈指针需要通过显式的加减移动其位置。

## 3. 比较操作

`cmp.uo-rb` 对两个操作数的**整 64 位**进行**无符号**比较（`bits[63:48]` 参与），**比较结果 -1/0/1** 分别对应小于/等于/大于，写入目的寄存器。结果 -1/0/1 可以作为有符号数解读，但主要用于区分三种关系。
后续的指令可以根据负数、非负数、零、非零、正数、非正数做出组合判断。

操作数类型是`orrr`。
具体指令如下：

```simrisc
cmp.uo  rdHB, rbHC, rbHD
```

> **注**：rb0 通用约定（rb0 读出为当前指令的地址，只读，显式目的触发 ILLI）和 RB 高 16 位行为见 SimRISC-00。

## 4. IP 相对寻址

IP 相对寻址指令把**当前正在执行的指令的地址**（即 `IP` = `rb0` 读出值）与立即数的 **4 KiB 块偏移**相加，结果写回目的寄存器；操作数类型是 `riii`。

**术语**：本 ISA 的 `IP`（`rb0`/`rbip`）= **当前正在执行的指令的地址**，**不是**主流 ISA 的「下一条指令地址」口径；本 ISA **无 `±4` 流水偏移**，故本指令的基址即 `IP` 自身，无需任何修正项。

编码层立即数 `imms18` 为 18 位有符号数（范围 −131072..131071）、单位为 **4 KiB 块**：立即数**不**左移 2 位（其单位不是字节），而是左移 **12** 位；`IP` **低位不清零**（`auipc` 式），与目标之间不足 4 KiB 的余量由后续访存指令的立即数补齐。⇒ 可寻址范围 = `±2^17 × 2^12` = **±512 MiB**。

汇编层操作数按**字节**书写、字段名为 **`imms30`**（须为 4 KiB 整数倍；`imms18 = imms30 >> 12`，见 `Toolchain-01`）。
具体指令如下：

```simrisc
aip.si rbHA, imms30
```

**与 RISC-V `auipc` 的三点差异**（`auipc` 仅作**参照**，不可照搬）：① **操作数以字节为单位**（汇编层 `imms30`；`auipc` 的立即数以 4 KiB 块为单位）；② 结果写入 **RB 银行**（`rbHA`；`auipc` 写通用整数寄存器 `rd`）；③ 可达 **±512 MiB**。

`aip.si` 为全 64 位运算，结果完整保留 64 位（`rbHA[63:0]`）；**仅当以该结果访存时**取 `rbHA[47:0]`（低 48 位）为有效地址，用户可通过 `rbHA` 的高 16 位（bits[63:48]）判断地址溢出。
目的 `rbHA` 为 `rb0` 时触发 ILLI（`rb0` 读出为当前指令地址、只读，见上「注」与 SimRISC-00）。

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.o` | `orrr` | `bbd` | `add.o rbHB, rbHC, rdHD` | `add.o_orrr_bbd` |
| `add.si` | `riii` | `rb` | `add.si rbHA, imms18` | `add.si_riii_rb` |
| `aip.si` | `riii` | `rb` | `aip.si rbHA, imms30` | `aip.si_riii_rb` |
| `cmp.uo` | `orrr` | `dbb` | `cmp.uo rdHB, rbHC, rbHD` | `cmp.uo_orrr_dbb` |
| `sub.o` | `orrr` | `bbd` | `sub.o rbHB, rbHC, rdHD` | `sub.o_orrr_bbd` |
| `sub.o` | `orrr` | `dbb` | `sub.o rdHB, rbHC, rbHD` | `sub.o_orrr_dbb` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `cmp.uo_orrr_dbb`, `sub.o_orrr_dbb`（2 条）
* `dst_rb0`：目的 rb0 → ILLI — `add.o_orrr_bbd`, `add.si_riii_rb`, `aip.si_riii_rb`, `sub.o_orrr_bbd`（4 条）
<!-- LEGALITY_END -->
