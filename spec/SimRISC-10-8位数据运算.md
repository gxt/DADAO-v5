# SimRISC8位数据运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：8位数据运算**（26 条）— .sb/.ub 运算

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 8位数据运算（18 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.sb` | `orrr` | `rd` | `add.sb rdHB, rdHC, rdHD` | `add.sb_orrr_rd` |
| `add.ub` | `orrr` | `rd` | `add.ub rdHB, rdHC, rdHD` | `add.ub_orrr_rd` |
| `cmp.sb` | `orrr` | `rd` | `cmp.sb rdHB, rdHC, rdHD` | `cmp.sb_orrr_rd` |
| `cmp.ub` | `orrr` | `rd` | `cmp.ub rdHB, rdHC, rdHD` | `cmp.ub_orrr_rd` |
| `div.sb` | `orrr` | `rd` | `div.sb rdHB, rdHC, rdHD` | `div.sb_orrr_rd` |
| `div.ub` | `orrr` | `rd` | `div.ub rdHB, rdHC, rdHD` | `div.ub_orrr_rd` |
| `mul.sb` | `orrr` | `rd` | `mul.sb rdHB, rdHC, rdHD` | `mul.sb_orrr_rd` |
| `mul.ub` | `orrr` | `rd` | `mul.ub rdHB, rdHC, rdHD` | `mul.ub_orrr_rd` |
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

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.sb_orrr_rd`, `add.ub_orrr_rd`, `cmp.sb_orrr_rd`, `cmp.ub_orrr_rd`, `div.sb_orrr_rd`, `div.ub_orrr_rd`, `mul.sb_orrr_rd`, `mul.ub_orrr_rd`, `rem.sb_orrr_rd`, `rem.ub_orrr_rd`, `shl.ub_orri_rd`, `shl.ub_orrr_rd`, `shr.sb_orri_rd`, `shr.sb_orrr_rd`, `shr.ub_orri_rd`, `shr.ub_orrr_rd`, `sub.sb_orrr_rd`, `sub.ub_orrr_rd`（18 条）
* `encode_sbz`：SBZ 非零 → ILLI — `shl.ub_orri_rd`, `shr.sb_orri_rd`, `shr.ub_orri_rd`（3 条）
<!-- LEGALITY_END -->


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
shl.ub  rdHB, rdHC, rdHD
shl.ub  rdHB, rdHC, immu6
shr.ub  rdHB, rdHC, rdHD
shr.ub  rdHB, rdHC, immu6
shr.sb  rdHB, rdHC, rdHD
shr.sb  rdHB, rdHC, immu6
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

### 比较操作 — 值语义

MISC-byte 子表中的 `cmp.s`/`cmp.u`（后缀 `.sb`/`.ub`）提供 8 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ub`/`cmp.sb` | 8 位 | `cmp.ub rdHB, rdHC, rdHD` | bits[7:0] |

**SPEC-069t 高位规则**：比较结果 −1/0/+1 按后缀扩展写满64位——`.sb` ⇒ 结果符号扩展；`.ub` ⇒ 结果零扩展。

例如 `cmp.sb rd1, rd2, rd3` 将 rd2 和 rd3 的低 8 位按有符号比较，结果符号扩展写入 rd1。

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

## 逻辑运算类指令 — 已删除

### Logic operators：逻辑运算 — 已删除

**SPEC-069t**：`and.b`/`or.b`/`xor.b`/`xnor.b` 已从指令集中删除。64 位逻辑运算见 SimRISC-04。

#### not 伪指令 — 已删除

**SPEC-069t**：`not.b` 已删除（窄位宽逻辑指令 `xnor.b` 已不存在）；仅保留 `not.o`（见 SimRISC-04）。

### Bit manipulating：位操作指令 — 值语义

MISC-byte 子表中的 `shl`/`shr`（后缀 `.ub`/`.sb`）提供 8 位移位操作。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**SPEC-069t 值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=7。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.ub`/`shr.sb`/`shr.ub` | 7 | 0-7 | hd[2:0]，hd[5:3] 应为零 |

运算公式：
```
shl.ub:  rdHB[7:0]   = (rdHC[7:0] << shamt),   rdHB[63:8]  = 0
shr.ub:  rdHB[7:0]   = (rdHC[7:0] >> shamt),   rdHB[63:8]  = 0
shr.sb:  rdHB[7:0]   = (rdHC[7:0] >> shamt) with sign(7),  rdHB[63:8] = sign_extend(rdHC[7])
```

`shamt > N` 触发 ILLI。

**SPEC-069t**：`ext.ub`/`ext.sb`（8位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。