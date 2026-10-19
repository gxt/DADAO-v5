# SimRISC32位数据运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：32位数据运算**（21 条）— .st/.ut 运算 + rev.t（逐块反转）+ shl.t/ror.t（移位/循环移位）

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 32位数据运算（21 条）

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
| `ror.t` | `orri` | `rd` | `ror.t rdHB, rdHC, immu6` | `ror.t_orri_rd` |
| `ror.t` | `orrr` | `rd` | `ror.t rdHB, rdHC, rdHD` | `ror.t_orrr_rd` |
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
## 2. 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.st_orrr_rd`, `add.ut_orrr_rd`, `cmp.st_orrr_rd`, `cmp.ut_orrr_rd`, `div.st_orrr_rd`, `div.ut_orrr_rd`, `mul.st_orrr_rd`, `mul.ut_orrr_rd`, `rem.st_orrr_rd`, `rem.ut_orrr_rd`, `rev.t_orri_rd`, `ror.t_orri_rd`, `ror.t_orrr_rd`, `shl.t_orri_rd`, `shl.t_orrr_rd`, `shr.st_orri_rd`, `shr.st_orrr_rd`, `shr.ut_orri_rd`, `shr.ut_orrr_rd`, `sub.st_orrr_rd`, `sub.ut_orrr_rd`（21 条）
* `encode_sbz`：SBZ 非零 → ILLI — `ror.t_orri_rd`, `shl.t_orri_rd`, `shr.st_orri_rd`, `shr.ut_orri_rd`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `rev.t_orri_rd`（1 条）
<!-- LEGALITY_END -->


## 3. 算术运算类指令

### 3.1 加减操作

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
shl.t   rdHB, rdHC, rdHD
shl.t   rdHB, rdHC, immu6
ror.t   rdHB, rdHC, rdHD
ror.t   rdHB, rdHC, immu6
shr.ut  rdHB, rdHC, rdHD
shr.ut  rdHB, rdHC, immu6
shr.st  rdHB, rdHC, rdHD
shr.st  rdHB, rdHC, immu6
```

#### 3.1.1 neg 伪指令（已删除）

上游 `SimRISC-0.5.4` 曾定义 `neg.t` 伪指令；v5 **删除**（`ADR-0013 D11`）。32 位取负（符号扩展至 64 位）**直接书写真实指令 `sub.st rdHB, rd0, rdHC`**：

```simrisc
sub.st  rd1, rd0, rd2        @@ rd1 = -rd2（低 32 位取负，符号扩展）
```

### 3.2 比较操作 — 值语义

MISC-tetra 子表中的 `cmp.s`/`cmp.u`（后缀 `.st`/`.ut`）提供 32 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ut`/`cmp.st` | 32 位 | `cmp.ut rdHB, rdHC, rdHD` | bits[31:0] |

**SPEC-069t 高位规则**：比较结果 −1/0/+1 按后缀扩展写满64位——`.st` ⇒ 结果符号扩展；`.ut` ⇒ 结果零扩展。

例如 `cmp.st rd1, rd2, rd3` 将 rd2 和 rd3 的低 32 位按有符号比较，结果符号扩展写入 rd1。

### 3.3 乘除操作

MISC-tetra 子表中的 `mul`/`div`/`rem` 提供 32 位乘除余运算。`mul` 后缀为 `.ut`/`.st`；`div`/`rem` 后缀为 `.ut`/`.st`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ut`/`mul.st`/`div.ut`/`div.st`/`rem.ut`/`rem.st` | 32 位 | `mul.ut rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：见 §乘除操作定值表（SimRISC-04）。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 tetra 对应的 −2147483648 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04 §乘除操作定值表。

## 4. 逻辑运算类指令

### 4.1 Logic operators：逻辑运算 — 已删除

**SPEC-069t**：`and.t`/`or.t`/`xor.t`/`xnor.t` 已从指令集中删除。64 位逻辑运算见 SimRISC-04。

#### 4.1.1 not 伪指令（已删除）

**SPEC-069t**：`not.t` 已删除（窄位宽逻辑指令 `xnor.t` 已不存在）；v5 亦**不保留** `not.o`（`ADR-0013 D11`）。按位取反**直接书写真实指令 `xnor.o rd, rs, rd0`**（64 位）。

### 4.2 Bit manipulating：位操作指令 — 值语义

MISC-tetra 子表中的 `shl.t`/`ror.t`/`shr.ut`/`shr.st` 提供 32 位移位/循环移位操作。`shr` 分 `u`（逻辑）/`s`（算术）变体；`shl`/`ror` 符号无关、不带 `u`/`s` 后缀（`ADR-0032 D3`）。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**SPEC-069t 值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=31。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.t`/`ror.t`/`shr.st`/`shr.ut` | 31 | 0-31 | hd[4:0]，hd[5] 应为零 |

运算公式：
```
shl.t:  rdHB[31:0]  = (rdHC[31:0] << shamt),  rdHB[63:32] = 0
ror.t:  rdHB[31:0]  = ror(rdHC[31:0], shamt), rdHB[63:32] = 0
shr.ut:  rdHB[31:0]  = (rdHC[31:0] >> shamt),  rdHB[63:32] = 0
shr.st:  rdHB[31:0]  = (rdHC[31:0] >> shamt) with sign(31),  rdHB[63:32] = sign_extend(rdHC[31])
```

`shamt > N` 触发 ILLI。

**SPEC-069t**：`ext.ut`/`ext.st`（32位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。

#### 4.2.1 逐块反转 rev.t（orri 格式）

`rev.t` 对 64 位源寄存器**按 32 位块逐块反转**：每块（S = 32）按 `k` 位切成
`32/k` 个单元，反转单元顺序（单元内部位序不变），两个块一律同样处理。
操作数格式 `orri`：`rev.t rdHB, rdHC, immu6`。

- 合法 `k` = `{1,2,4,8,16}`（one-hot 且 `k < S = 32`）；非 one-hot 或 `k ≥ 32` 触发 **ILLI**（规则 `encode_onehot`）。
- `k=8` 即 `bswap32` 语义（须源高 32 位为 0）；`k=1` 只反转**块内**位序，**不是** 64 位整体位反序。
- 逐块反转的总述与伪代码见 SimRISC-04 §4.2.1。

#### 4.2.2 逻辑循环右移 ror.t（`orrr` / `orri` 格式）

`ror.t` 对源寄存器的 **低 32 位**做逻辑循环右移：`rdHB[31:0] = ror(rdHC[31:0], amount)`；
结果按值语义零扩展写满 64 位（`rdHB[63:32] = 0`）。符号无关、只有一个方向、不带 `u`/`s`
（`ADR-0032 D3`/`D4`）。

| 格式 | 旋转量 `amount` | 取值 |
|------|----------------|------|
| `orrr` | `rdHD[4:0]` | `0..31`（即对 32 取模） |
| `orri` | `immu6` | `0..31`；`immu6 > 31` ⇒ **ILLI** |

- `orrr` 的 `rdHD` 只有低 5 位参与（天然取模 32）；`orri` 的 `immu6` 是 6 位，**越界（`32..63`）触发 ILLI**（与 `shl.t` 的 `immu6 <= 31` 同口径）。
- 目的 `rdHB` 为 `rd0` ⇒ **ILLI**（规则 `dst_rd0`）；源 `rdHC` 可为 `rd0`（结果恒为 0）；`rdHB == rdHC` 允许。
- 编码：`ror.t` `orrr` = `010-001`、`orri` = `011-001`（`MISC-tetra`）。
- 64 位语义与总述见 SimRISC-04 §4.2.3。

```simrisc
ror.t   rdHB, rdHC, rdHD        @@ 32 位循环右移（旋转量 = rdHD[4:0]）
ror.t   rdHB, rdHC, immu6       @@ 32 位循环右移（immu6 0..31）
```

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- `shl` 去掉 `u` 后缀（`shl.t`）并迁编码 `010-000`/`011-000`；新增 `ror.t`（逻辑循环右移，编码 `010-001`/`011-001`）及 §4.2.2 语义。
- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- 新增 `rev.t`（逐块反转，orri，`§4.2.1`）。
- 伪指令集收缩：删除 `not.*`/`neg.*` 1:1 别名。
- 新增「合法性检查」章（生成区）。
- 窄位宽指令精简、高位规则统一为值语义；`div`/`rem` 定值语义。
- 正文改用新汇编格式；新增「汇编指令速查」章（生成区）。

### 0.5.4（2026-09-28）

- 本册自原《SimRISC 数据类指令》的算术 / 逻辑运算部分按 32 位拆出，独立成「32 位数据运算」分册。

### 0.5.2（2026-07-18）

- 指令名后缀统一为 `.ut`/`.st`（tetra） 形；`add`/`sub`/`mul`/`div`/`rem`/`ext`/`sh` 按位宽与符号类型细分。

### 0.5.0（2026-07-15）

- 引入位掩码 `brrr` 格式；位掩码 `bN`→`bmN`→`bpN` 重命名。

### 0.4.1（2026-07-14）

- 初版：同步上游对应位宽的算术 / 逻辑运算指令。
