# SimRISC32位数据运算指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：32位数据运算**（26 条）— .st/.ut 运算

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 32位数据运算（18 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.st` | `orrr` | `rd` | `add.st rdHB, rdHC, rdHD` | `add.st_orrr_rd` |
| `add.ut` | `orrr` | `rd` | `add.ut rdHB, rdHC, rdHD` | `add.ut_orrr_rd` |
| `cmp.st` | `orrr` | `rd` | `cmp.st rdHB, rdHC, rdHD` | `cmp.st_orrr_rd` |
| `cmp.ut` | `orrr` | `rd` | `cmp.ut rdHB, rdHC, rdHD` | `cmp.ut_orrr_rd` |
| `div.st` | `orrr` | `rd` | `div.st rdHB, rdHC, rdHD` | `div.st_orrr_rd` |
| `div.ut` | `orrr` | `rd` | `div.ut rdHB, rdHC, rdHD` | `div.ut_orrr_rd` |
| `mul.st` | `orrr` | `rd` | `mul.st rdHB, rdHC, rdHD` | `mul.st_orrr_rd` |
| `mul.ut` | `orrr` | `rd` | `mul.ut rdHB, rdHC, rdHD` | `mul.ut_orrr_rd` |
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

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.st_orrr_rd`, `add.ut_orrr_rd`, `cmp.st_orrr_rd`, `cmp.ut_orrr_rd`, `div.st_orrr_rd`, `div.ut_orrr_rd`, `mul.st_orrr_rd`, `mul.ut_orrr_rd`, `rem.st_orrr_rd`, `rem.ut_orrr_rd`, `shl.ut_orri_rd`, `shl.ut_orrr_rd`, `shr.st_orri_rd`, `shr.st_orrr_rd`, `shr.ut_orri_rd`, `shr.ut_orrr_rd`, `sub.st_orrr_rd`, `sub.ut_orrr_rd`（18 条）
* `encode_sbz`：SBZ 非零 → ILLI — `shl.ut_orri_rd`, `shr.st_orri_rd`, `shr.ut_orri_rd`（3 条）
<!-- LEGALITY_END -->


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
shl.ut  rdHB, rdHC, rdHD
shl.ut  rdHB, rdHC, immu6
shr.ut  rdHB, rdHC, rdHD
shr.ut  rdHB, rdHC, immu6
shr.st  rdHB, rdHC, rdHD
shr.st  rdHB, rdHC, immu6
```

#### neg 伪指令（已删除）

上游 `SimRISC-0.5.4` 曾定义 `neg.t` 伪指令；v5 **删除**（`ADR-0013 D11`）。32 位取负（符号扩展至 64 位）**直接书写真实指令 `sub.st rdHB, rd0, rdHC`**：

```simrisc
sub.st  rd1, rd0, rd2        ; rd1 = -rd2（低 32 位取负，符号扩展）
```

### 比较操作 — 值语义

MISC-tetra 子表中的 `cmp.s`/`cmp.u`（后缀 `.st`/`.ut`）提供 32 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ut`/`cmp.st` | 32 位 | `cmp.ut rdHB, rdHC, rdHD` | bits[31:0] |

**SPEC-069t 高位规则**：比较结果 −1/0/+1 按后缀扩展写满64位——`.st` ⇒ 结果符号扩展；`.ut` ⇒ 结果零扩展。

例如 `cmp.st rd1, rd2, rd3` 将 rd2 和 rd3 的低 32 位按有符号比较，结果符号扩展写入 rd1。

### 乘除操作

MISC-tetra 子表中的 `mul`/`div`/`rem` 提供 32 位乘除余运算。`mul` 后缀为 `.ut`/`.st`；`div`/`rem` 后缀为 `.ut`/`.st`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ut`/`mul.st`/`div.ut`/`div.st`/`rem.ut`/`rem.st` | 32 位 | `mul.ut rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：见 §乘除操作定值表（SimRISC-04）。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 tetra 对应的 −2147483648 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04 §乘除操作定值表。

## 逻辑运算类指令

### Logic operators：逻辑运算 — 已删除

**SPEC-069t**：`and.t`/`or.t`/`xor.t`/`xnor.t` 已从指令集中删除。64 位逻辑运算见 SimRISC-04。

#### not 伪指令（已删除）

**SPEC-069t**：`not.t` 已删除（窄位宽逻辑指令 `xnor.t` 已不存在）；v5 亦**不保留** `not.o`（`ADR-0013 D11`）。按位取反**直接书写真实指令 `xnor.o rd, rs, rd0`**（64 位）。

### Bit manipulating：位操作指令 — 值语义

MISC-tetra 子表中的 `shl`/`shr`（后缀 `.ut`/`.st`）提供 32 位移位操作。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**SPEC-069t 值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=31。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.ut`/`shr.st`/`shr.ut` | 31 | 0-31 | hd[4:0]，hd[5] 应为零 |

运算公式：
```
shl.ut:  rdHB[31:0]  = (rdHC[31:0] << shamt),  rdHB[63:32] = 0
shr.ut:  rdHB[31:0]  = (rdHC[31:0] >> shamt),  rdHB[63:32] = 0
shr.st:  rdHB[31:0]  = (rdHC[31:0] >> shamt) with sign(31),  rdHB[63:32] = sign_extend(rdHC[31])
```

`shamt > N` 触发 ILLI。

**SPEC-069t**：`ext.ut`/`ext.st`（32位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。