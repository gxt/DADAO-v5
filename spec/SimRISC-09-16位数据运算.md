# SimRISC16位数据运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：16位数据运算**（26 条）— .sw/.uw 运算

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 16位数据运算（26 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.sw` | `orrr` | `rd` | `add.sw rdHB, rdHC, rdHD` | `add.sw_orrr_rd` |
| `add.uw` | `orrr` | `rd` | `add.uw rdHB, rdHC, rdHD` | `add.uw_orrr_rd` |
| `and.w` | `orrr` | `rd` | `and.w rdHB, rdHC, rdHD` | `and.w_orrr_rd` |
| `cmp.sw` | `orrr` | `rd` | `cmp.sw rdHB, rdHC, rdHD` | `cmp.sw_orrr_rd` |
| `cmp.uw` | `orrr` | `rd` | `cmp.uw rdHB, rdHC, rdHD` | `cmp.uw_orrr_rd` |
| `div.sw` | `orrr` | `rd` | `div.sw rdHB, rdHC, rdHD` | `div.sw_orrr_rd` |
| `div.uw` | `orrr` | `rd` | `div.uw rdHB, rdHC, rdHD` | `div.uw_orrr_rd` |
| `ext.sw` | `orri` | `rd` | `ext.sw rdHB, rdHC, immu6` | `ext.sw_orri_rd` |
| `ext.sw` | `orrr` | `rd` | `ext.sw rdHB, rdHC, rdHD` | `ext.sw_orrr_rd` |
| `ext.uw` | `orri` | `rd` | `ext.uw rdHB, rdHC, immu6` | `ext.uw_orri_rd` |
| `ext.uw` | `orrr` | `rd` | `ext.uw rdHB, rdHC, rdHD` | `ext.uw_orrr_rd` |
| `mul.sw` | `orrr` | `rd` | `mul.sw rdHB, rdHC, rdHD` | `mul.sw_orrr_rd` |
| `mul.uw` | `orrr` | `rd` | `mul.uw rdHB, rdHC, rdHD` | `mul.uw_orrr_rd` |
| `or.w` | `orrr` | `rd` | `or.w rdHB, rdHC, rdHD` | `or.w_orrr_rd` |
| `rem.sw` | `orrr` | `rd` | `rem.sw rdHB, rdHC, rdHD` | `rem.sw_orrr_rd` |
| `rem.uw` | `orrr` | `rd` | `rem.uw rdHB, rdHC, rdHD` | `rem.uw_orrr_rd` |
| `shl.uw` | `orri` | `rd` | `shl.uw rdHB, rdHC, immu6` | `shl.uw_orri_rd` |
| `shl.uw` | `orrr` | `rd` | `shl.uw rdHB, rdHC, rdHD` | `shl.uw_orrr_rd` |
| `shr.sw` | `orri` | `rd` | `shr.sw rdHB, rdHC, immu6` | `shr.sw_orri_rd` |
| `shr.sw` | `orrr` | `rd` | `shr.sw rdHB, rdHC, rdHD` | `shr.sw_orrr_rd` |
| `shr.uw` | `orri` | `rd` | `shr.uw rdHB, rdHC, immu6` | `shr.uw_orri_rd` |
| `shr.uw` | `orrr` | `rd` | `shr.uw rdHB, rdHC, rdHD` | `shr.uw_orrr_rd` |
| `sub.sw` | `orrr` | `rd` | `sub.sw rdHB, rdHC, rdHD` | `sub.sw_orrr_rd` |
| `sub.uw` | `orrr` | `rd` | `sub.uw rdHB, rdHC, rdHD` | `sub.uw_orrr_rd` |
| `xnor.w` | `orrr` | `rd` | `xnor.w rdHB, rdHC, rdHD` | `xnor.w_orrr_rd` |
| `xor.w` | `orrr` | `rd` | `xor.w rdHB, rdHC, rdHD` | `xor.w_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

## 算术运算类指令

### 加减操作

MISC-wyde 子表中的 `add`/`sub` 提供 16 位加减运算，按符号类型分为两个变体：

- **`add.uw`/`sub.uw`**（无符号）：结果零扩展至 64 位，适合无符号运算。
- **`add.sw`/`sub.sw`**（有符号，默认）：结果符号扩展至 64 位，适合有符号运算。

仅 size 范围内的低位参与运算，溢出部分静默丢弃。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `add.uw`/`sub.uw` / `add.sw`/`sub.sw` | 16 位 | `add.uw rdHB, rdHC, rdHD` | 零扩展 / 符号扩展 |

```simrisc
add.uw  rdHB, rdHC, rdHD
add.sw  rdHB, rdHC, rdHD
sub.uw  rdHB, rdHC, rdHD
sub.sw  rdHB, rdHC, rdHD
cmp.uw  rdHB, rdHC, rdHD
cmp.sw  rdHB, rdHC, rdHD
mul.uw  rdHB, rdHC, rdHD
mul.sw  rdHB, rdHC, rdHD
div.uw  rdHB, rdHC, rdHD
div.sw  rdHB, rdHC, rdHD
rem.uw  rdHB, rdHC, rdHD
rem.sw  rdHB, rdHC, rdHD
and.w   rdHB, rdHC, rdHD
or.w    rdHB, rdHC, rdHD
xor.w   rdHB, rdHC, rdHD
xnor.w  rdHB, rdHC, rdHD
shl.uw  rdHB, rdHC, rdHD
shl.uw  rdHB, rdHC, immu6
shr.uw  rdHB, rdHC, rdHD
shr.uw  rdHB, rdHC, immu6
shr.sw  rdHB, rdHC, rdHD
shr.sw  rdHB, rdHC, immu6
ext.uw  rdHB, rdHC, rdHD
ext.uw  rdHB, rdHC, immu6
ext.sw  rdHB, rdHC, rdHD
ext.sw  rdHB, rdHC, immu6
```

#### neg 伪指令

`neg.w` 是汇编器提供的伪指令，用于对操作数进行 16 位取负操作（二进制补码）。

| 伪指令 | 展开形式 | 语义 |
|--------|----------|------|
| `neg.w rdHB, rdHC` | `sub.sw rdHB, rd0, rdHC` | 16 位取负，符号扩展至 64 位 |

示例：
```simrisc
neg.w   rd1, rd2        ; rd1 = -rd2（低 16 位取负，符号扩展）
```

### 比较操作

MISC-wyde 子表中的 `cmp.s`/`cmp.u`（后缀 `.sw`/`.uw`）提供 16 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.uw`/`cmp.sw` | 16 位 | `cmp.uw rdHB, rdHC, rdHD` | bits[15:0] |

例如 `cmp.sw rd1, rd2, rd3` 将 rd2 和 rd3 的低 16 位按有符号比较，结果写入 rd1。

### 乘除操作

MISC-wyde 子表中的 `mul`/`div`/`rem` 提供 16 位乘除余运算。`mul` 后缀为 `.uw`/`.sw`；`div`/`rem` 后缀为 `.uw`/`.sw`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.uw`/`mul.sw`/`div.uw`/`div.sw`/`rem.uw`/`rem.sw` | 16 位 | `mul.uw rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：见 §乘除操作定值表（SimRISC-04）。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 wyde 对应的 −32768 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04 §乘除操作定值表。

## 逻辑运算类指令

### Logic operators：逻辑运算

MISC-wyde 子表中的 `and`/`or`/`xor`/`xnor`（后缀 `.w`）提供 16 位逻辑运算。操作数格式为 `orrr`。

| 指令 | 位宽 | 汇编语法 | 操作范围 |
|------|------|---------|---------|
| `and.w`/`or.w`/`xor.w`/`xnor.w` | 16 位 | `and.w rdHB, rdHC, rdHD` | bits[15:0] 参与运算，bits[63:16] 不变 |

逻辑运算规则和逻辑非实现见 SimRISC-04。以上四条逻辑运算指令在 size 范围外的高位（bits[63:16]）保持目的寄存器原有值不变。

#### not 伪指令

| 伪指令 | 展开形式 | 操作范围 |
|--------|----------|----------|
| `not.w rdHB, rdHC` | `xnor.w rdHB, rdHC, rd0` | bits[15:0] 取反，bits[63:16] 不变 |

源和目的可为同一寄存器（原地取反）。

### Bit manipulating：位操作指令

MISC-wyde 子表中的 `shl`/`shr`（后缀 `.uw`/`.sw`）提供 16 位移位操作。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

移位语义和扩展语义见 SimRISC-04。其中 N=15。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.uw`/`shr.sw`/`shr.uw` | 15 | 0-15 | hd[3:0]，hd[5:4] 应为零 |

`shamt > N` 触发 ILLI。

`ext.s` 是符号扩展，`ext.u` 是零扩展。操作数格式为 `orrr`（寄存器形式，hd=扩展起始位）和 `orri`（立即数形式，hd=immu6 扩展起始位）。

| 指令 | N | 汇编语法 | 约束 |
|------|---|---------|------|
| `ext.uw`/`ext.sw` | 15 | `ext.uw rdHB, rdHC, rdHD` 或 `ext.uw rdHB, rdHC, immu6` | hd ≤ 15 |

> **注**：rd0 目的寄存器约定见 SimRISC-00。