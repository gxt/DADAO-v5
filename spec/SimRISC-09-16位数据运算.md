# SimRISC16位数据运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：16位数据运算**（26 条）— .sw/.uw 运算

## 算术运算类指令

### 加减操作

MISC-wyde 子表中的 `add`/`sub` 提供 16 位加减运算，按符号类型分为两个变体：

- **`add.uw`/`sub.uw`**（无符号）：结果零扩展至 64 位，适合无符号运算。
- **`add.sw`/`sub.sw`**（有符号，默认）：结果符号扩展至 64 位，适合有符号运算。

仅 size 范围内的低位参与运算，溢出部分静默丢弃。操作数格式为 `orrr`，`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `add.uw`/`sub.uw` / `add.sw`/`sub.sw` | 16 位 | `add.uw rdhb, rdhc, rdhd` | 零扩展 / 符号扩展 |

```simrisc
add.uw  rdhb, rdhc, rdhd
add.sw  rdhb, rdhc, rdhd
sub.uw  rdhb, rdhc, rdhd
sub.sw  rdhb, rdhc, rdhd
cmp.uw  rdhb, rdhc, rdhd
cmp.sw  rdhb, rdhc, rdhd
mul.uw  rdhb, rdhc, rdhd
mul.sw  rdhb, rdhc, rdhd
div.uw  rdhb, rdhc, rdhd
div.sw  rdhb, rdhc, rdhd
rem.uw  rdhb, rdhc, rdhd
rem.sw  rdhb, rdhc, rdhd
and.w   rdhb, rdhc, rdhd
or.w    rdhb, rdhc, rdhd
xor.w   rdhb, rdhc, rdhd
xnor.w  rdhb, rdhc, rdhd
shl.uw  rdhb, rdhc, rdhd
shl.uw  rdhb, rdhc, immu6
shr.uw  rdhb, rdhc, rdhd
shr.uw  rdhb, rdhc, immu6
shr.sw  rdhb, rdhc, rdhd
shr.sw  rdhb, rdhc, immu6
ext.uw  rdhb, rdhc, rdhd
ext.uw  rdhb, rdhc, immu6
ext.sw  rdhb, rdhc, rdhd
ext.sw  rdhb, rdhc, immu6
```

#### neg 伪指令

`neg.w` 是汇编器提供的伪指令，用于对操作数进行 16 位取负操作（二进制补码）。

| 伪指令 | 展开形式 | 语义 |
|--------|----------|------|
| `neg.w rdhb, rdhc` | `sub.sw rdhb, rd0, rdhc` | 16 位取负，符号扩展至 64 位 |

示例：
```simrisc
neg.w   rd1, rd2        ; rd1 = -rd2（低 16 位取负，符号扩展）
```

### 比较操作

MISC-wyde 子表中的 `cmp.s`/`cmp.u`（后缀 `.sw`/`.uw`）提供 16 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.uw`/`cmp.sw` | 16 位 | `cmp.uw rdhb, rdhc, rdhd` | bits[15:0] |

例如 `cmp.sw rd1, rd2, rd3` 将 rd2 和 rd3 的低 16 位按有符号比较，结果写入 rd1。

### 乘除操作

MISC-wyde 子表中的 `mul`/`div`/`rem` 提供 16 位乘除余运算。`mul` 后缀为 `.uw`/`.sw`；`div`/`rem` 后缀为 `.uw`/`.sw`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdhb` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.uw`/`mul.sw`/`div.uw`/`div.sw`/`rem.uw`/`rem.sw` | 16 位 | `mul.uw rdhb, rdhc, rdhd` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零**：触发 ILLI 异常。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出**：`div.s` 中 wyde 对应的 −32768 ÷ −1 触发 ILLI 异常。`div.u`/`rem.u` 不存在溢出。
- **fault 时寄存器**：精确异常，目的寄存器未写入（无副作用）。

## 逻辑运算类指令

### Logic operators：逻辑运算

MISC-wyde 子表中的 `and`/`or`/`xor`/`xnor`（后缀 `.w`）提供 16 位逻辑运算。操作数格式为 `orrr`。

| 指令 | 位宽 | 汇编语法 | 操作范围 |
|------|------|---------|---------|
| `and.w`/`or.w`/`xor.w`/`xnor.w` | 16 位 | `and.w rdhb, rdhc, rdhd` | bits[15:0] 参与运算，bits[63:16] 不变 |

逻辑运算规则和逻辑非实现见 SimRISC-04。以上四条逻辑运算指令在 size 范围外的高位（bits[63:16]）保持目的寄存器原有值不变。

#### not 伪指令

| 伪指令 | 展开形式 | 操作范围 |
|--------|----------|----------|
| `not.w rdhb, rdhc` | `xnor.w rdhb, rdhc, rd0` | bits[15:0] 取反，bits[63:16] 不变 |

源和目的可为同一寄存器（原地取反）。

### Bit manipulating：位操作指令

MISC-wyde 子表中的 `shl`/`shr`（后缀 `.uw`/`.sw`）提供 16 位移位操作。移位量（shamt）取 `rdhd` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

移位语义和扩展语义见 SimRISC-04。其中 N=15。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.uw`/`shr.sw`/`shr.uw` | 15 | 0-15 | hd[3:0]，hd[5:4] 应为零 |

`shamt > N` 触发 ILLI。

`ext.s` 是符号扩展，`ext.u` 是零扩展。操作数格式为 `orrr`（寄存器形式，hd=扩展起始位）和 `orri`（立即数形式，hd=immu6 扩展起始位）。

| 指令 | N | 汇编语法 | 约束 |
|------|---|---------|------|
| `ext.uw`/`ext.sw` | 15 | `ext.uw rdhb, rdhc, rdhd` 或 `ext.uw rdhb, rdhc, immu6` | hd ≤ 15 |

> **注**：rd0 目的寄存器约定见 SimRISC-00。