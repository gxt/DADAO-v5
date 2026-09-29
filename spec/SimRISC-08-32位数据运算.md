# SimRISC32位数据运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：32位数据运算**（26 条）— .st/.ut 运算

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 32位数据运算（26 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.st` | `orrr` | `rd` | `add.st rdHB, rdHC, rdHD` | `add.st_orrr_rd` |
| `add.ut` | `orrr` | `rd` | `add.ut rdHB, rdHC, rdHD` | `add.ut_orrr_rd` |
| `and.t` | `orrr` | `rd` | `and.t rdHB, rdHC, rdHD` | `and.t_orrr_rd` |
| `cmp.st` | `orrr` | `rd` | `cmp.st rdHB, rdHC, rdHD` | `cmp.st_orrr_rd` |
| `cmp.ut` | `orrr` | `rd` | `cmp.ut rdHB, rdHC, rdHD` | `cmp.ut_orrr_rd` |
| `div.st` | `orrr` | `rd` | `div.st rdHB, rdHC, rdHD` | `div.st_orrr_rd` |
| `div.ut` | `orrr` | `rd` | `div.ut rdHB, rdHC, rdHD` | `div.ut_orrr_rd` |
| `ext.st` | `orri` | `rd` | `ext.st rdHB, rdHC, immu6` | `ext.st_orri_rd` |
| `ext.st` | `orrr` | `rd` | `ext.st rdHB, rdHC, rdHD` | `ext.st_orrr_rd` |
| `ext.ut` | `orri` | `rd` | `ext.ut rdHB, rdHC, immu6` | `ext.ut_orri_rd` |
| `ext.ut` | `orrr` | `rd` | `ext.ut rdHB, rdHC, rdHD` | `ext.ut_orrr_rd` |
| `mul.st` | `orrr` | `rd` | `mul.st rdHB, rdHC, rdHD` | `mul.st_orrr_rd` |
| `mul.ut` | `orrr` | `rd` | `mul.ut rdHB, rdHC, rdHD` | `mul.ut_orrr_rd` |
| `or.t` | `orrr` | `rd` | `or.t rdHB, rdHC, rdHD` | `or.t_orrr_rd` |
| `rem.st` | `orrr` | `rd` | `rem.st rdHB, rdHC, rdHD` | `rem.st_orrr_rd` |
| `rem.ut` | `orrr` | `rd` | `rem.ut rdHB, rdHC, rdHD` | `rem.ut_orrr_rd` |
| `shl.ut` | `orri` | `rd` | `shl.ut rdHB, rdHC, immu6` | `shl.ut_orri_rd` |
| `shl.ut` | `orrr` | `rd` | `shl.ut rdHB, rdHC, rdHD` | `shl.ut_orrr_rd` |
| `shr.st` | `orri` | `rd` | `shr.st rdHB, rdHC, immu6` | `shr.st_orri_rd` |
| `shr.st` | `orrr` | `rd` | `shr.st rdHB, rdHC, rdHD` | `shr.st_orrr_rd` |
| `shr.ut` | `orri` | `rd` | `shr.ut rdHB, rdHC, immu6` | `shr.ut_orri_rd` |
| `shr.ut` | `orrr` | `rd` | `shr.ut rdHB, rdHC, rdHD` | `shr.ut_orrr_rd` |
| `sub.st` | `orrr` | `rd` | `sub.st rdHB, rdHC, rdHD` | `sub.st_orrr_rd` |
| `sub.ut` | `orrr` | `rd` | `sub.ut rdHB, rdHC, rdHD` | `sub.ut_orrr_rd` |
| `xnor.t` | `orrr` | `rd` | `xnor.t rdHB, rdHC, rdHD` | `xnor.t_orrr_rd` |
| `xor.t` | `orrr` | `rd` | `xor.t rdHB, rdHC, rdHD` | `xor.t_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

## 算术运算类指令

### 加减操作

MISC-tetra 子表中的 `add`/`sub` 提供 32 位加减运算，按符号类型分为两个变体：

- **`add.ut`/`sub.ut`**（无符号）：结果零扩展至 64 位，适合无符号运算。
- **`add.st`/`sub.st`**（有符号，默认）：结果符号扩展至 64 位，适合有符号运算。

仅 size 范围内的低位参与运算，溢出部分静默丢弃。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `add.ut`/`sub.ut` / `add.st`/`sub.st` | 32 位 | `add.ut rdHB, rdHC, rdHD` | 零扩展 / 符号扩展 |

```simrisc
add.ut  rdHB, rdHC, rdHD
add.st  rdHB, rdHC, rdHD
sub.ut  rdHB, rdHC, rdHD
sub.st  rdHB, rdHC, rdHD
cmp.ut  rdHB, rdHC, rdHD
cmp.st  rdHB, rdHC, rdHD
mul.ut  rdHB, rdHC, rdHD
mul.st  rdHB, rdHC, rdHD
div.ut  rdHB, rdHC, rdHD
div.st  rdHB, rdHC, rdHD
rem.ut  rdHB, rdHC, rdHD
rem.st  rdHB, rdHC, rdHD
and.t   rdHB, rdHC, rdHD
or.t    rdHB, rdHC, rdHD
xor.t   rdHB, rdHC, rdHD
xnor.t  rdHB, rdHC, rdHD
shl.ut  rdHB, rdHC, rdHD
shl.ut  rdHB, rdHC, immu6
shr.ut  rdHB, rdHC, rdHD
shr.ut  rdHB, rdHC, immu6
shr.st  rdHB, rdHC, rdHD
shr.st  rdHB, rdHC, immu6
ext.ut  rdHB, rdHC, rdHD
ext.ut  rdHB, rdHC, immu6
ext.st  rdHB, rdHC, rdHD
ext.st  rdHB, rdHC, immu6
```

#### neg 伪指令

`neg.t` 是汇编器提供的伪指令，用于对操作数进行 32 位取负操作（二进制补码）。

| 伪指令 | 展开形式 | 语义 |
|--------|----------|------|
| `neg.t rdHB, rdHC` | `sub.st rdHB, rd0, rdHC` | 32 位取负，符号扩展至 64 位 |

示例：
```simrisc
neg.t   rd1, rd2        ; rd1 = -rd2（低 32 位取负，符号扩展）
```

### 比较操作

MISC-tetra 子表中的 `cmp.s`/`cmp.u`（后缀 `.st`/`.ut`）提供 32 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ut`/`cmp.st` | 32 位 | `cmp.ut rdHB, rdHC, rdHD` | bits[31:0] |

例如 `cmp.st rd1, rd2, rd3` 将 rd2 和 rd3 的低 32 位按有符号比较，结果写入 rd1。

### 乘除操作

MISC-tetra 子表中的 `mul`/`div`/`rem` 提供 32 位乘除余运算。`mul` 后缀为 `.ut`/`.st`；`div`/`rem` 后缀为 `.ut`/`.st`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ut`/`mul.st`/`div.ut`/`div.st`/`rem.ut`/`rem.st` | 32 位 | `mul.ut rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零**：触发 ILLI 异常。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出**：`div.s` 中 tetra 对应的 −2147483648 ÷ −1 触发 ILLI 异常。`div.u`/`rem.u` 不存在溢出。
- **fault 时寄存器**：精确异常，目的寄存器未写入（无副作用）。

## 逻辑运算类指令

### Logic operators：逻辑运算

MISC-tetra 子表中的 `and`/`or`/`xor`/`xnor`（后缀 `.t`）提供 32 位逻辑运算。操作数格式为 `orrr`。

| 指令 | 位宽 | 汇编语法 | 操作范围 |
|------|------|---------|---------|
| `and.t`/`or.t`/`xor.t`/`xnor.t` | 32 位 | `and.t rdHB, rdHC, rdHD` | bits[31:0] 参与运算，bits[63:32] 不变 |

逻辑运算规则和逻辑非实现见 SimRISC-04。以上四条逻辑运算指令在 size 范围外的高位（bits[63:32]）保持目的寄存器原有值不变。

#### not 伪指令

| 伪指令 | 展开形式 | 操作范围 |
|--------|----------|----------|
| `not.t rdHB, rdHC` | `xnor.t rdHB, rdHC, rd0` | bits[31:0] 取反，bits[63:32] 不变 |

源和目的可为同一寄存器（原地取反）。

### Bit manipulating：位操作指令

MISC-tetra 子表中的 `shl`/`shr`（后缀 `.ut`/`.st`）提供 32 位移位操作。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

移位语义和扩展语义见 SimRISC-04。其中 N=31。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.ut`/`shr.st`/`shr.ut` | 31 | 0-31 | hd[4:0]，hd[5] 应为零 |

`shamt > N` 触发 ILLI。

`ext.s` 是符号扩展，`ext.u` 是零扩展。操作数格式为 `orrr`（寄存器形式，hd=扩展起始位）和 `orri`（立即数形式，hd=immu6 扩展起始位）。

| 指令 | N | 汇编语法 | 约束 |
|------|---|---------|------|
| `ext.ut`/`ext.st` | 31 | `ext.ut rdHB, rdHC, rdHD` 或 `ext.ut rdHB, rdHC, immu6` | hd ≤ 31 |

> **注**：rd0 目的寄存器约定见 SimRISC-00。