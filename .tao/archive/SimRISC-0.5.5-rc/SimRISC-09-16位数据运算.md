# SimRISC16位数据运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：16位数据运算**（21 条）— .sw/.uw 运算 + rev.w（逐块反转）+ shl.w/rol.w（移位/循环移位）

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 16位数据运算（21 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.sw` | `orrr` | `rd` | `add.sw rdHB, rdHC, rdHD` | `add.sw_orrr_rd` |
| `add.uw` | `orrr` | `rd` | `add.uw rdHB, rdHC, rdHD` | `add.uw_orrr_rd` |
| `cmp.sw` | `orrr` | `rd` | `cmp.sw rdHB, rdHC, rdHD` | `cmp.sw_orrr_rd` |
| `cmp.uw` | `orrr` | `rd` | `cmp.uw rdHB, rdHC, rdHD` | `cmp.uw_orrr_rd` |
| `div.sw` | `orrr` | `rd` | `div.sw rdHB, rdHC, rdHD` | `div.sw_orrr_rd` |
| `div.uw` | `orrr` | `rd` | `div.uw rdHB, rdHC, rdHD` | `div.uw_orrr_rd` |
| `mul.sw` | `orrr` | `rd` | `mul.sw rdHB, rdHC, rdHD` | `mul.sw_orrr_rd` |
| `mul.uw` | `orrr` | `rd` | `mul.uw rdHB, rdHC, rdHD` | `mul.uw_orrr_rd` |
| `rem.sw` | `orrr` | `rd` | `rem.sw rdHB, rdHC, rdHD` | `rem.sw_orrr_rd` |
| `rem.uw` | `orrr` | `rd` | `rem.uw rdHB, rdHC, rdHD` | `rem.uw_orrr_rd` |
| `rev.w` | `orri` | `rd` | `rev.w rdHB, rdHC, immu6` | `rev.w_orri_rd` |
| `rol.w` | `orri` | `rd` | `rol.w rdHB, rdHC, immu6` | `rol.w_orri_rd` |
| `rol.w` | `orrr` | `rd` | `rol.w rdHB, rdHC, rdHD` | `rol.w_orrr_rd` |
| `shl.w` | `orri` | `rd` | `shl.w rdHB, rdHC, immu6` | `shl.w_orri_rd` |
| `shl.w` | `orrr` | `rd` | `shl.w rdHB, rdHC, rdHD` | `shl.w_orrr_rd` |
| `shr.sw` | `orri` | `rd` | `shr.sw rdHB, rdHC, immu6` | `shr.sw_orri_rd` |
| `shr.sw` | `orrr` | `rd` | `shr.sw rdHB, rdHC, rdHD` | `shr.sw_orrr_rd` |
| `shr.uw` | `orri` | `rd` | `shr.uw rdHB, rdHC, immu6` | `shr.uw_orri_rd` |
| `shr.uw` | `orrr` | `rd` | `shr.uw rdHB, rdHC, rdHD` | `shr.uw_orrr_rd` |
| `sub.sw` | `orrr` | `rd` | `sub.sw rdHB, rdHC, rdHD` | `sub.sw_orrr_rd` |
| `sub.uw` | `orrr` | `rd` | `sub.uw rdHB, rdHC, rdHD` | `sub.uw_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 2. 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.sw_orrr_rd`, `add.uw_orrr_rd`, `cmp.sw_orrr_rd`, `cmp.uw_orrr_rd`, `div.sw_orrr_rd`, `div.uw_orrr_rd`, `mul.sw_orrr_rd`, `mul.uw_orrr_rd`, `rem.sw_orrr_rd`, `rem.uw_orrr_rd`, `rev.w_orri_rd`, `rol.w_orri_rd`, `rol.w_orrr_rd`, `shl.w_orri_rd`, `shl.w_orrr_rd`, `shr.sw_orri_rd`, `shr.sw_orrr_rd`, `shr.uw_orri_rd`, `shr.uw_orrr_rd`, `sub.sw_orrr_rd`, `sub.uw_orrr_rd`（21 条）
* `encode_sbz`：SBZ 非零 → ILLI — `rol.w_orri_rd`, `shl.w_orri_rd`, `shr.sw_orri_rd`, `shr.uw_orri_rd`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `rev.w_orri_rd`（1 条）
<!-- LEGALITY_END -->


## 3. 算术运算类指令

### 3.1 加减操作

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
shl.w   rdHB, rdHC, rdHD
shl.w   rdHB, rdHC, immu6
rol.w   rdHB, rdHC, rdHD
rol.w   rdHB, rdHC, immu6
shr.uw  rdHB, rdHC, rdHD
shr.uw  rdHB, rdHC, immu6
shr.sw  rdHB, rdHC, rdHD
shr.sw  rdHB, rdHC, immu6
```

#### 3.1.1 neg 伪指令（已删除）

上游 `SimRISC-0.5.4` 曾定义 `neg.w` 伪指令；v5 **删除**（`ADR-0013 D11`）。16 位取负（符号扩展至 64 位）**直接书写真实指令 `sub.sw rdHB, rd0, rdHC`**：

```simrisc
sub.sw  rd1, rd0, rd2        @@ rd1 = -rd2（低 16 位取负，符号扩展）
```

### 3.2 比较操作 — 值语义

MISC-wyde 子表中的 `cmp.s`/`cmp.u`（后缀 `.sw`/`.uw`）提供 16 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.uw`/`cmp.sw` | 16 位 | `cmp.uw rdHB, rdHC, rdHD` | bits[15:0] |

**SPEC-069t 高位规则**：比较结果 −1/0/+1 按后缀扩展写满64位——`.sw` ⇒ 结果符号扩展；`.uw` ⇒ 结果零扩展。

例如 `cmp.sw rd1, rd2, rd3` 将 rd2 和 rd3 的低 16 位按有符号比较，结果符号扩展写入 rd1。

### 3.3 乘除操作

MISC-wyde 子表中的 `mul`/`div`/`rem` 提供 16 位乘除余运算。`mul` 后缀为 `.uw`/`.sw`；`div`/`rem` 后缀为 `.uw`/`.sw`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.uw`/`mul.sw`/`div.uw`/`div.sw`/`rem.uw`/`rem.sw` | 16 位 | `mul.uw rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：见 §乘除操作定值表（SimRISC-04）。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 wyde 对应的 −32768 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04 §乘除操作定值表。

## 4. 逻辑运算类指令 — 已删除

### 4.1 Logic operators：逻辑运算 — 已删除

**SPEC-069t**：`and.w`/`or.w`/`xor.w`/`xnor.w` 已从指令集中删除。64 位逻辑运算见 SimRISC-04。

#### 4.1.1 not 伪指令（已删除）

**SPEC-069t**：`not.w` 已删除（窄位宽逻辑指令 `xnor.w` 已不存在）；v5 亦**不保留** `not.o`（`ADR-0013 D11`）。按位取反**直接书写真实指令 `xnor.o rd, rs, rd0`**（64 位）。

### 4.2 Bit manipulating：位操作指令 — 值语义

MISC-wyde 子表中的 `shl.w`/`rol.w`/`shr.uw`/`shr.sw` 提供 16 位移位/循环移位操作。`shr` 分 `u`（逻辑）/`s`（算术）变体；`shl`/`rol` 符号无关、不带 `u`/`s` 后缀（`ADR-0032 D3`）。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**SPEC-069t 值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=15。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.w`/`rol.w`/`shr.sw`/`shr.uw` | 15 | 0-15 | hd[3:0]，hd[5:4] 应为零 |

运算公式：
```
shl.w:  rdHB[15:0]  = (rdHC[15:0] << shamt),  rdHB[63:16] = 0
rol.w:  rdHB[15:0]  = rol(rdHC[15:0], shamt), rdHB[63:16] = 0
shr.uw:  rdHB[15:0]  = (rdHC[15:0] >> shamt),  rdHB[63:16] = 0
shr.sw:  rdHB[15:0]  = (rdHC[15:0] >> shamt) with sign(15),  rdHB[63:16] = sign_extend(rdHC[15])
```

`shamt > N` 触发 ILLI。

**SPEC-069t**：`ext.uw`/`ext.sw`（16位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。

#### 4.2.1 逐块反转 rev.w（orri 格式）

`rev.w` 对 64 位源寄存器**按 16 位块逐块反转**：每块（S = 16）按 `k` 位切成
`16/k` 个单元，反转单元顺序（单元内部位序不变），四个块一律同样处理。
操作数格式 `orri`：`rev.w rdHB, rdHC, immu6`。

- 合法 `k` = `{1,2,4,8}`（one-hot 且 `k < S = 16`）；非 one-hot 或 `k ≥ 16` 触发 **ILLI**（规则 `encode_onehot`）。
- `k=8` 即 `bswap16` 语义（须源高 48 位为 0）；`k=1` 只反转**块内**位序，**不是** 64 位整体位反序。
- 逐块反转的总述与伪代码见 SimRISC-04 §4.2.1。

#### 4.2.2 逻辑循环左移 rol.w（`orrr` / `orri` 格式）

`rol.w` 对源寄存器的 **低 16 位**做逻辑循环左移：`rdHB[15:0] = rol(rdHC[15:0], amount)`；
结果按值语义零扩展写满 64 位（`rdHB[63:16] = 0`）。符号无关、只有一个方向、不带 `u`/`s`
（`ADR-0032 D3`/`D4`）。

| 格式 | 旋转量 `amount` | 取值 |
|------|----------------|------|
| `orrr` | `rdHD[3:0]` | `0..15`（即对 16 取模） |
| `orri` | `immu6` | `0..15`；`immu6 > 15` ⇒ **ILLI** |

- `orrr` 的 `rdHD` 只有低 4 位参与（天然取模 16）；`orri` 的 `immu6` 是 6 位，**越界（`16..63`）触发 ILLI**（与 `shl.w` 的 `immu6 <= 15` 同口径）。
- 目的 `rdHB` 为 `rd0` ⇒ **ILLI**（规则 `dst_rd0`）；源 `rdHC` 可为 `rd0`（结果恒为 0）；`rdHB == rdHC` 允许。
- 编码：`rol.w` `orrr` = `010-001`、`orri` = `011-001`（`MISC-wyde`）。
- 64 位语义与总述见 SimRISC-04 §4.2.3。

```simrisc
rol.w   rdHB, rdHC, rdHD        @@ 16 位循环左移（旋转量 = rdHD[3:0]）
rol.w   rdHB, rdHC, immu6       @@ 16 位循环左移（immu6 0..15）
```

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- `shl` 去掉 `u` 后缀（`shl.w`）并迁编码 `010-000`/`011-000`；新增 `rol.w`（逻辑循环左移，编码 `010-001`/`011-001`）及 §4.2.2 语义。
- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- 新增 `rev.w`（逐块反转，orri，`§4.2.1`）。
- 伪指令集收缩：删除 `not.*`/`neg.*` 1:1 别名。
- 新增「合法性检查」章（生成区）。
- 窄位宽指令精简、高位规则统一为值语义；`div`/`rem` 定值语义。
- 正文改用新汇编格式；新增「汇编指令速查」章（生成区）。

### 0.5.4（2026-09-28）

- 本册自原《SimRISC 数据类指令》的算术 / 逻辑运算部分按 16 位拆出，独立成「16 位数据运算」分册。

### 0.5.2（2026-07-18）

- 指令名后缀统一为 `.uw`/`.sw`（wyde） 形；`add`/`sub`/`mul`/`div`/`rem`/`ext`/`sh` 按位宽与符号类型细分。

### 0.5.0（2026-07-15）

- 引入位掩码 `brrr` 格式；位掩码 `bN`→`bmN`→`bpN` 重命名。

### 0.4.1（2026-07-14）

- 初版：同步上游对应位宽的算术 / 逻辑运算指令。
