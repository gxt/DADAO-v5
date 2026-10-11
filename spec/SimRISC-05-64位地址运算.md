# SimRISC64位地址运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：64位地址运算**（5 条）— add.si-rb/add.o/cmp.uo-rb/sub.o(bbd)/sub.o(dbb)

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 64位地址运算（5 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.o` | `orrr` | `bbd` | `add.o rbHB, rbHC, rdHD` | `add.o_orrr_bbd` |
| `add.si` | `riii` | `rb` | `add.si rbHA, imms18` | `add.si_riii_rb` |
| `cmp.uo` | `orrr` | `dbb` | `cmp.uo rdHB, rbHC, rbHD` | `cmp.uo_orrr_dbb` |
| `sub.o` | `orrr` | `bbd` | `sub.o rbHB, rbHC, rdHD` | `sub.o_orrr_bbd` |
| `sub.o` | `orrr` | `dbb` | `sub.o rdHB, rbHC, rbHD` | `sub.o_orrr_dbb` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 2. 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `cmp.uo_orrr_dbb`, `sub.o_orrr_dbb`（2 条）
* `dst_rb0`：目的 rb0 → ILLI — `add.o_orrr_bbd`, `add.si_riii_rb`, `sub.o_orrr_bbd`（3 条）
<!-- LEGALITY_END -->


## 3. 算术运算类指令

### 3.1 加减操作

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

### 3.2 自增自减

自增自减指令需要一个寄存器和一个立即数，操作数类型是 `riii`，立即数为18位有符号数，经过符号扩展后与寄存器执行加法，结果写回同一寄存器。
由于立即数采用补码的编码方式，无需区分加减操作。
具体指令如下：

```simrisc
add.si  rbHA, imms18
```

`add.si` 为全 64 位运算，结果完整保留 64 位（`rbHA[63:0]`）；**仅当以该结果访存时**取 `rbHA[47:0]`（低 48 位）为有效地址，用户可通过 `rbHA` 的高 16 位（bits[63:48]）判断地址溢出。
由于imms18为有符号数，该加法指令也隐含实现了减法指令。
针对rb寄存器的add.si指令的重要性在于对栈指针的操作，在没有提供专门的push/pop类指令的情况下，栈指针需要通过显式的加减移动其位置。

### 3.3 比较操作

`cmp.uo-rb` 对两个操作数的**整 64 位**进行**无符号**比较（`bits[63:48]` 参与），**比较结果 -1/0/1** 分别对应小于/等于/大于，写入目的寄存器。结果 -1/0/1 可以作为有符号数解读，但主要用于区分三种关系。
后续的指令可以根据负数、非负数、零、非零、正数、非正数做出组合判断。

操作数类型是`orrr`。
具体指令如下：

```simrisc
cmp.uo  rdHB, rbHC, rbHD
```

> **注**：rb0 通用约定（rb0 读出为当前指令的地址，只读，显式目的触发 ILLI）和 RB 高 16 位行为见 SimRISC-00。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- 标题章节号统一为 `N` / `N.M` / `N.M.K`；规范 / 文档一致性清理。
- 新增 `sub.o`（RB−RB→RD）；RB 算术三条指令改名并调整编码槽。
- `cmp.uo-rb` 改为整 64 位比较；RB / 控制流地址语义修正。
- 新增「合法性检查」章（生成区）；0 号寄存器作源操作数语义澄清。
- 正文改用新汇编格式；新增「汇编指令速查」章（生成区）。

### 0.5.4（2026-09-28）

- 本册自原《SimRISC 地址类指令》的地址算术部分拆出，独立成「64 位地址运算」分册；PC 相对寻址（`rela`）相关口径并入。

### 0.5.3（2026-07-19）

- `add.si` 改为 `riii` 格式、立即数 18 位、源=目的；opcode 调整。

### 0.5.2（2026-07-18）

- `add.so-rb`/`sub.so-rb`/`cmp.uo-rb` 重命名并更新溢出检测语义；`add.si` 溢出描述更新、`or.w` 双义注释。

### 0.5.0（2026-07-15）

- 地址算术引入位掩码 `brrr` 格式；`ww`→`wpN`（wyde position）重命名。

### 0.4.1（2026-07-14）

- 初版：同步上游地址算术指令（`add`/`sub`/`cmp`/`rela`）。
