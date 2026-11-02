# SimRISC32位数据运算指令

> **版本：0.5.6-rc**（与 SimRISC-00 一致）
> **分类：32位数据运算** — .st/.ut 运算 + rev.t（逐块反转）+ shl.t/rol.t（移位/循环移位）

## 1. 算术运算类指令

### 1.1 加减操作

OPC-tetra 子表中的 `add`/`sub` 提供 32 位加减运算，按符号类型分为两个变体：

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
shl.t   rdHB, rdHC, rdHD
shl.t   rdHB, rdHC, immu6
rol.t   rdHB, rdHC, rdHD
rol.t   rdHB, rdHC, immu6
shr.ut  rdHB, rdHC, rdHD
shr.ut  rdHB, rdHC, immu6
shr.st  rdHB, rdHC, rdHD
shr.st  rdHB, rdHC, immu6
```

### 1.2 比较操作 — 值语义

OPC-tetra 子表中的 `cmp.s`/`cmp.u`（后缀 `.st`/`.ut`）提供 32 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ut`/`cmp.st` | 32 位 | `cmp.ut rdHB, rdHC, rdHD` | bits[31:0] |

**高位规则**：比较结果（−1/0/+1）**按 64 位扩展**写满目的寄存器——−1 ⇒ `0xFFFF_FFFF_FFFF_FFFF`（64 位全 1）、0 ⇒ `0`、+1 ⇒ `1`；`.st`/`.ut` 结果相同（符号扩展与 64 位扩展在 −1/0/+1 上同值）。源操作数仍按上述位宽截断后比较。

例如 `cmp.st rd1, rd2, rd3` 将 rd2 和 rd3 的低 32 位按有符号比较：rd2 < rd3 时 `rd1 = 0xFFFF_FFFF_FFFF_FFFF`，相等时 `rd1 = 0`，rd2 > rd3 时 `rd1 = 1`。

### 1.3 乘除操作

OPC-tetra 子表中的 `mul`/`div`/`rem` 提供 32 位乘除余运算。`mul` 后缀为 `.ut`/`.st`；`div`/`rem` 后缀为 `.ut`/`.st`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ut`/`mul.st`/`div.ut`/`div.st`/`rem.ut`/`rem.st` | 32 位 | `mul.ut rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：定值表见 SimRISC-04。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 tetra 对应的 −2147483648 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04。

## 2. Bit manipulating：位操作指令 — 值语义

OPC-tetra 子表中的 `shl.t`/`rol.t`/`shr.ut`/`shr.st` 提供 32 位移位/循环移位操作。`shr` 分 `u`（逻辑）/`s`（算术）变体；`shl`/`rol` 符号无关、不带 `u`/`s` 后缀。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=31。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.t`/`rol.t`/`shr.st`/`shr.ut` | 31 | 0-31 | hd[4:0]，hd[5] 应为零 |

运算公式：
```
shl.t:  rdHB[31:0]  = (rdHC[31:0] << shamt),  rdHB[63:32] = 0
rol.t:  rdHB[31:0]  = rol(rdHC[31:0], shamt), rdHB[63:32] = 0
shr.ut:  rdHB[31:0]  = (rdHC[31:0] >> shamt),  rdHB[63:32] = 0
shr.st:  rdHB[31:0]  = (rdHC[31:0] >> shamt) with sign(31),  rdHB[63:32] = sign_extend(rdHC[31])
```

`shamt > N` 触发 ILLI。

**注**：`ext.ut`/`ext.st`（32位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。

### 2.1 逐块反转 rev.t（orri 格式）

`rev.t` 对 64 位源寄存器**按 32 位块逐块反转**：每块（S = 32）按 `k` 位切成
`32/k` 个单元，反转单元顺序（单元内部位序不变），两个块一律同样处理。
操作数格式 `orri`：`rev.t rdHB, rdHC, immu6`。

- 合法 `k` = `{1,2,4,8,16}`（one-hot 且 `k < S = 32`）；非 one-hot 或 `k ≥ 32` 触发 **ILLI**（规则 `encode_onehot`）。
- `k=8` 即 `bswap32` 语义（须源高 32 位为 0）；`k=1` 只反转**块内**位序，**不是** 64 位整体位反序。
- 逐块反转的总述与伪代码见 SimRISC-04。

### 2.2 逻辑循环左移 rol.t（`orrr` / `orri` 格式）

`rol.t` 对源寄存器的 **低 32 位**做逻辑循环左移：`rdHB[31:0] = rol(rdHC[31:0], amount)`；
结果按值语义零扩展写满 64 位（`rdHB[63:32] = 0`）。符号无关、只有一个方向、不带 `u`/`s`
。

| 格式 | 旋转量 `amount` | 取值 |
|------|----------------|------|
| `orrr` | `rdHD[4:0]` | `0..31`（即对 32 取模） |
| `orri` | `immu6` | `0..31`；`immu6 > 31` ⇒ **ILLI** |

- `orrr` 的 `rdHD` 只有低 5 位参与（天然取模 32）；`orri` 的 `immu6` 是 6 位，**越界（`32..63`）触发 ILLI**（与 `shl.t` 的 `immu6 <= 31` 同口径）。
- 目的 `rdHB` 为 `rd0` ⇒ **ILLI**（规则 `dst_rd0`）；源 `rdHC` 可为 `rd0`（结果恒为 0）；`rdHB == rdHC` 允许。
- 格式：`orrr`（寄存器旋转量）/ `orri`（立即数旋转量），属 `OPC-tetra` 子表。
- 64 位语义与总述见 SimRISC-04。

```simrisc
rol.t   rdHB, rdHC, rdHD        @@ 32 位循环左移（旋转量 = rdHD[4:0]）
rol.t   rdHB, rdHC, immu6       @@ 32 位循环左移（immu6 0..31）
```

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

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
| `rev.t` | `orri` | `rd` | `rev.t rdHB, rdHC, immu6` | `rev.t_orri_rd` |
| `rol.t` | `orri` | `rd` | `rol.t rdHB, rdHC, immu6` | `rol.t_orri_rd` |
| `rol.t` | `orrr` | `rd` | `rol.t rdHB, rdHC, rdHD` | `rol.t_orrr_rd` |
| `shl.t` | `orri` | `rd` | `shl.t rdHB, rdHC, immu6` | `shl.t_orri_rd` |
| `shl.t` | `orrr` | `rd` | `shl.t rdHB, rdHC, rdHD` | `shl.t_orrr_rd` |
| `shr.st` | `orri` | `rd` | `shr.st rdHB, rdHC, immu6` | `shr.st_orri_rd` |
| `shr.st` | `orrr` | `rd` | `shr.st rdHB, rdHC, rdHD` | `shr.st_orrr_rd` |
| `shr.ut` | `orri` | `rd` | `shr.ut rdHB, rdHC, immu6` | `shr.ut_orri_rd` |
| `shr.ut` | `orrr` | `rd` | `shr.ut rdHB, rdHC, rdHD` | `shr.ut_orrr_rd` |
| `sub.st` | `orrr` | `rd` | `sub.st rdHB, rdHC, rdHD` | `sub.st_orrr_rd` |
| `sub.ut` | `orrr` | `rd` | `sub.ut rdHB, rdHC, rdHD` | `sub.ut_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.st_orrr_rd`, `add.ut_orrr_rd`, `cmp.st_orrr_rd`, `cmp.ut_orrr_rd`, `div.st_orrr_rd`, `div.ut_orrr_rd`, `mul.st_orrr_rd`, `mul.ut_orrr_rd`, `rem.st_orrr_rd`, `rem.ut_orrr_rd`, `rev.t_orri_rd`, `rol.t_orri_rd`, `rol.t_orrr_rd`, `shl.t_orri_rd`, `shl.t_orrr_rd`, `shr.st_orri_rd`, `shr.st_orrr_rd`, `shr.ut_orri_rd`, `shr.ut_orrr_rd`, `sub.st_orrr_rd`, `sub.ut_orrr_rd`（21 条）
* `encode_sbz`：SBZ 非零 → ILLI — `rol.t_orri_rd`, `shl.t_orri_rd`, `shr.st_orri_rd`, `shr.ut_orri_rd`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `rev.t_orri_rd`（1 条）
<!-- LEGALITY_END -->
