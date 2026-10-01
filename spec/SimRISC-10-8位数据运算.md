# SimRISC8位数据运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：8位数据运算**（26 条）— .sb/.ub 运算

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 8位数据运算（26 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.sb` | `orrr` | `rd` | `add.sb rdHB, rdHC, rdHD` | `add.sb_orrr_rd` |
| `add.ub` | `orrr` | `rd` | `add.ub rdHB, rdHC, rdHD` | `add.ub_orrr_rd` |
| `and.b` | `orrr` | `rd` | `and.b rdHB, rdHC, rdHD` | `and.b_orrr_rd` |
| `cmp.sb` | `orrr` | `rd` | `cmp.sb rdHB, rdHC, rdHD` | `cmp.sb_orrr_rd` |
| `cmp.ub` | `orrr` | `rd` | `cmp.ub rdHB, rdHC, rdHD` | `cmp.ub_orrr_rd` |
| `div.sb` | `orrr` | `rd` | `div.sb rdHB, rdHC, rdHD` | `div.sb_orrr_rd` |
| `div.ub` | `orrr` | `rd` | `div.ub rdHB, rdHC, rdHD` | `div.ub_orrr_rd` |
| `ext.sb` | `orri` | `rd` | `ext.sb rdHB, rdHC, immu6` | `ext.sb_orri_rd` |
| `ext.sb` | `orrr` | `rd` | `ext.sb rdHB, rdHC, rdHD` | `ext.sb_orrr_rd` |
| `ext.ub` | `orri` | `rd` | `ext.ub rdHB, rdHC, immu6` | `ext.ub_orri_rd` |
| `ext.ub` | `orrr` | `rd` | `ext.ub rdHB, rdHC, rdHD` | `ext.ub_orrr_rd` |
| `mul.sb` | `orrr` | `rd` | `mul.sb rdHB, rdHC, rdHD` | `mul.sb_orrr_rd` |
| `mul.ub` | `orrr` | `rd` | `mul.ub rdHB, rdHC, rdHD` | `mul.ub_orrr_rd` |
| `or.b` | `orrr` | `rd` | `or.b rdHB, rdHC, rdHD` | `or.b_orrr_rd` |
| `rem.sb` | `orrr` | `rd` | `rem.sb rdHB, rdHC, rdHD` | `rem.sb_orrr_rd` |
| `rem.ub` | `orrr` | `rd` | `rem.ub rdHB, rdHC, rdHD` | `rem.ub_orrr_rd` |
| `shl.ub` | `orri` | `rd` | `shl.ub rdHB, rdHC, immu6` | `shl.ub_orri_rd` |
| `shl.ub` | `orrr` | `rd` | `shl.ub rdHB, rdHC, rdHD` | `shl.ub_orrr_rd` |
| `shr.sb` | `orri` | `rd` | `shr.sb rdHB, rdHC, immu6` | `shr.sb_orri_rd` |
| `shr.sb` | `orrr` | `rd` | `shr.sb rdHB, rdHC, rdHD` | `shr.sb_orrr_rd` |
| `shr.ub` | `orri` | `rd` | `shr.ub rdHB, rdHC, immu6` | `shr.ub_orri_rd` |
| `shr.ub` | `orrr` | `rd` | `shr.ub rdHB, rdHC, rdHD` | `shr.ub_orrr_rd` |
| `sub.sb` | `orrr` | `rd` | `sub.sb rdHB, rdHC, rdHD` | `sub.sb_orrr_rd` |
| `sub.ub` | `orrr` | `rd` | `sub.ub rdHB, rdHC, rdHD` | `sub.ub_orrr_rd` |
| `xnor.b` | `orrr` | `rd` | `xnor.b rdHB, rdHC, rdHD` | `xnor.b_orrr_rd` |
| `xor.b` | `orrr` | `rd` | `xor.b rdHB, rdHC, rdHD` | `xor.b_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

## 算术运算类指令

### 加减操作

MISC-byte 子表中的 `add`/`sub` 提供 8 位加减运算，按符号类型分为两个变体：

- **`add.ub`/`sub.ub`**（无符号）：结果零扩展至 64 位，适合无符号运算。
- **`add.sb`/`sub.sb`**（有符号，默认）：结果符号扩展至 64 位，适合有符号运算。

仅 size 范围内的低位参与运算，溢出部分静默丢弃。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 高位填充 |
|------|------|---------|---------|
| `add.ub`/`sub.ub` / `add.sb`/`sub.sb` | 8 位 | `add.ub rdHB, rdHC, rdHD` | 零扩展 / 符号扩展 |

```simrisc
add.ub  rdHB, rdHC, rdHD
add.sb  rdHB, rdHC, rdHD
sub.ub  rdHB, rdHC, rdHD
sub.sb  rdHB, rdHC, rdHD
cmp.ub  rdHB, rdHC, rdHD
cmp.sb  rdHB, rdHC, rdHD
mul.ub  rdHB, rdHC, rdHD
mul.sb  rdHB, rdHC, rdHD
div.ub  rdHB, rdHC, rdHD
div.sb  rdHB, rdHC, rdHD
rem.ub  rdHB, rdHC, rdHD
rem.sb  rdHB, rdHC, rdHD
and.b   rdHB, rdHC, rdHD
or.b    rdHB, rdHC, rdHD
xor.b   rdHB, rdHC, rdHD
xnor.b  rdHB, rdHC, rdHD
shl.ub  rdHB, rdHC, rdHD
shl.ub  rdHB, rdHC, immu6
shr.ub  rdHB, rdHC, rdHD
shr.ub  rdHB, rdHC, immu6
shr.sb  rdHB, rdHC, rdHD
shr.sb  rdHB, rdHC, immu6
ext.ub  rdHB, rdHC, rdHD
ext.ub  rdHB, rdHC, immu6
ext.sb  rdHB, rdHC, rdHD
ext.sb  rdHB, rdHC, immu6
```

#### neg 伪指令

`neg.b` 是汇编器提供的伪指令，用于对操作数进行 8 位取负操作（二进制补码）。

| 伪指令 | 展开形式 | 语义 |
|--------|----------|------|
| `neg.b rdHB, rdHC` | `sub.sb rdHB, rd0, rdHC` | 8 位取负，符号扩展至 64 位 |

示例：
```simrisc
neg.b   rd1, rd2        ; rd1 = -rd2（低 8 位取负，符号扩展）
```

### 比较操作

MISC-byte 子表中的 `cmp.s`/`cmp.u`（后缀 `.sb`/`.ub`）提供 8 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ub`/`cmp.sb` | 8 位 | `cmp.ub rdHB, rdHC, rdHD` | bits[7:0] |

例如 `cmp.sb rd1, rd2, rd3` 将 rd2 和 rd3 的低 8 位按有符号比较，结果写入 rd1。

### 乘除操作

MISC-byte 子表中的 `mul`/`div`/`rem` 提供 8 位乘除余运算。`mul` 后缀为 `.ub`/`.sb`；`div`/`rem` 后缀为 `.ub`/`.sb`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ub`/`mul.sb`/`div.ub`/`div.sb`/`rem.ub`/`rem.sb` | 8 位 | `mul.ub rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：见 §乘除操作定值表（SimRISC-04）。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 byte 对应的 −128 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04 §乘除操作定值表。

## 逻辑运算类指令

### Logic operators：逻辑运算

MISC-byte 子表中的 `and`/`or`/`xor`/`xnor`（后缀 `.b`）提供 8 位逻辑运算。操作数格式为 `orrr`。

| 指令 | 位宽 | 汇编语法 | 操作范围 |
|------|------|---------|---------|
| `and.b`/`or.b`/`xor.b`/`xnor.b` | 8 位 | `and.b rdHB, rdHC, rdHD` | bits[7:0] 参与运算，bits[63:8] 不变 |

逻辑运算规则和逻辑非实现见 SimRISC-04。以上四条逻辑运算指令在 size 范围外的高位（bits[63:8]）保持目的寄存器原有值不变。

#### not 伪指令

| 伪指令 | 展开形式 | 操作范围 |
|--------|----------|----------|
| `not.b rdHB, rdHC` | `xnor.b rdHB, rdHC, rd0` | bits[7:0] 取反，bits[63:8] 不变 |

源和目的可为同一寄存器（原地取反）。

### Bit manipulating：位操作指令

MISC-byte 子表中的 `shl`/`shr`（后缀 `.ub`/`.sb`）提供 8 位移位操作。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

移位语义和扩展语义见 SimRISC-04。其中 N=7。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.ub`/`shr.sb`/`shr.ub` | 7 | 0-7 | hd[2:0]，hd[5:3] 应为零 |

`shamt > N` 触发 ILLI。

`ext.s` 是符号扩展，`ext.u` 是零扩展。操作数格式为 `orrr`（寄存器形式，hd=扩展起始位）和 `orri`（立即数形式，hd=immu6 扩展起始位）。

| 指令 | N | 汇编语法 | 约束 |
|------|---|---------|------|
| `ext.ub`/`ext.sb` | 7 | `ext.ub rdHB, rdHC, rdHD` 或 `ext.ub rdHB, rdHC, immu6` | hd ≤ 7 |

> **注**：rd0 目的寄存器约定见 SimRISC-00。