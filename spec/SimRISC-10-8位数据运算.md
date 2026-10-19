# SimRISC8位数据运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：8位数据运算**（21 条）— .sb/.ub 运算 + rev.b（逐块反转）+ shl.b/ror.b（移位/循环移位）

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 8位数据运算（21 条）

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
| `rev.b` | `orri` | `rd` | `rev.b rdHB, rdHC, immu6` | `rev.b_orri_rd` |
| `ror.b` | `orri` | `rd` | `ror.b rdHB, rdHC, immu6` | `ror.b_orri_rd` |
| `ror.b` | `orrr` | `rd` | `ror.b rdHB, rdHC, rdHD` | `ror.b_orrr_rd` |
| `shl.b` | `orri` | `rd` | `shl.b rdHB, rdHC, immu6` | `shl.b_orri_rd` |
| `shl.b` | `orrr` | `rd` | `shl.b rdHB, rdHC, rdHD` | `shl.b_orrr_rd` |
| `shr.sb` | `orri` | `rd` | `shr.sb rdHB, rdHC, immu6` | `shr.sb_orri_rd` |
| `shr.sb` | `orrr` | `rd` | `shr.sb rdHB, rdHC, rdHD` | `shr.sb_orrr_rd` |
| `shr.ub` | `orri` | `rd` | `shr.ub rdHB, rdHC, immu6` | `shr.ub_orri_rd` |
| `shr.ub` | `orrr` | `rd` | `shr.ub rdHB, rdHC, rdHD` | `shr.ub_orrr_rd` |
| `sub.sb` | `orrr` | `rd` | `sub.sb rdHB, rdHC, rdHD` | `sub.sb_orrr_rd` |
| `sub.ub` | `orrr` | `rd` | `sub.ub rdHB, rdHC, rdHD` | `sub.ub_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 2. 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.sb_orrr_rd`, `add.ub_orrr_rd`, `cmp.sb_orrr_rd`, `cmp.ub_orrr_rd`, `div.sb_orrr_rd`, `div.ub_orrr_rd`, `mul.sb_orrr_rd`, `mul.ub_orrr_rd`, `rem.sb_orrr_rd`, `rem.ub_orrr_rd`, `rev.b_orri_rd`, `ror.b_orri_rd`, `ror.b_orrr_rd`, `shl.b_orri_rd`, `shl.b_orrr_rd`, `shr.sb_orri_rd`, `shr.sb_orrr_rd`, `shr.ub_orri_rd`, `shr.ub_orrr_rd`, `sub.sb_orrr_rd`, `sub.ub_orrr_rd`（21 条）
* `encode_sbz`：SBZ 非零 → ILLI — `ror.b_orri_rd`, `shl.b_orri_rd`, `shr.sb_orri_rd`, `shr.ub_orri_rd`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `rev.b_orri_rd`（1 条）
<!-- LEGALITY_END -->


## 3. 算术运算类指令

### 3.1 加减操作

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
shl.b   rdHB, rdHC, rdHD
shl.b   rdHB, rdHC, immu6
ror.b   rdHB, rdHC, rdHD
ror.b   rdHB, rdHC, immu6
shr.ub  rdHB, rdHC, rdHD
shr.ub  rdHB, rdHC, immu6
shr.sb  rdHB, rdHC, rdHD
shr.sb  rdHB, rdHC, immu6
```

#### 3.1.1 neg 伪指令（已删除）

上游 `SimRISC-0.5.4` 曾定义 `neg.b` 伪指令；v5 **删除**（`ADR-0013 D11`）。8 位取负（符号扩展至 64 位）**直接书写真实指令 `sub.sb rdHB, rd0, rdHC`**：

```simrisc
sub.sb  rd1, rd0, rd2        @@ rd1 = -rd2（低 8 位取负，符号扩展）
```

### 3.2 比较操作 — 值语义

MISC-byte 子表中的 `cmp.s`/`cmp.u`（后缀 `.sb`/`.ub`）提供 8 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ub`/`cmp.sb` | 8 位 | `cmp.ub rdHB, rdHC, rdHD` | bits[7:0] |

**SPEC-069t 高位规则**：比较结果 −1/0/+1 按后缀扩展写满64位——`.sb` ⇒ 结果符号扩展；`.ub` ⇒ 结果零扩展。

例如 `cmp.sb rd1, rd2, rd3` 将 rd2 和 rd3 的低 8 位按有符号比较，结果符号扩展写入 rd1。

### 3.3 乘除操作

MISC-byte 子表中的 `mul`/`div`/`rem` 提供 8 位乘除余运算。`mul` 后缀为 `.ub`/`.sb`；`div`/`rem` 后缀为 `.ub`/`.sb`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ub`/`mul.sb`/`div.ub`/`div.sb`/`rem.ub`/`rem.sb` | 8 位 | `mul.ub rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：见 §乘除操作定值表（SimRISC-04）。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 byte 对应的 −128 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04 §乘除操作定值表。

## 4. 逻辑运算类指令 — 已删除

### 4.1 Logic operators：逻辑运算 — 已删除

**SPEC-069t**：`and.b`/`or.b`/`xor.b`/`xnor.b` 已从指令集中删除。64 位逻辑运算见 SimRISC-04。

#### 4.1.1 not 伪指令（已删除）

**SPEC-069t**：`not.b` 已删除（窄位宽逻辑指令 `xnor.b` 已不存在）；v5 亦**不保留** `not.o`（`ADR-0013 D11`）。按位取反**直接书写真实指令 `xnor.o rd, rs, rd0`**（64 位）。

### 4.2 Bit manipulating：位操作指令 — 值语义

MISC-byte 子表中的 `shl.b`/`ror.b`/`shr.ub`/`shr.sb` 提供 8 位移位/循环移位操作。`shr` 分 `u`（逻辑）/`s`（算术）变体；`shl`/`ror` 符号无关、不带 `u`/`s` 后缀（`ADR-0032 D3`）。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**SPEC-069t 值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=7。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.b`/`ror.b`/`shr.sb`/`shr.ub` | 7 | 0-7 | hd[2:0]，hd[5:3] 应为零 |

运算公式：
```
shl.b:  rdHB[7:0]   = (rdHC[7:0] << shamt),   rdHB[63:8]  = 0
ror.b:  rdHB[7:0]   = ror(rdHC[7:0], shamt),  rdHB[63:8]  = 0
shr.ub:  rdHB[7:0]   = (rdHC[7:0] >> shamt),   rdHB[63:8]  = 0
shr.sb:  rdHB[7:0]   = (rdHC[7:0] >> shamt) with sign(7),  rdHB[63:8] = sign_extend(rdHC[7])
```

`shamt > N` 触发 ILLI。

**SPEC-069t**：`ext.ub`/`ext.sb`（8位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。

#### 4.2.1 逐块反转 rev.b（orri 格式）

`rev.b` 对 64 位源寄存器**按 8 位块逐块反转**：每块（S = 8）按 `k` 位切成
`8/k` 个单元，反转单元顺序（单元内部位序不变），八个块一律同样处理。
操作数格式 `orri`：`rev.b rdHB, rdHC, immu6`。

- 合法 `k` = `{1,2,4}`（one-hot 且 `k < S = 8`）；非 one-hot 或 `k ≥ 8`（含 `k = 8` 恒等档）触发 **ILLI**（规则 `encode_onehot`）。
- `rev.b` 无 `bswap` 对应档（`k=8` 即恒等，**非法**）；`k=1` 只反转**块内**位序，**不是** 64 位整体位反序。
- 逐块反转的总述与伪代码见 SimRISC-04 §4.2.1。

#### 4.2.2 逻辑循环右移 ror.b（`orrr` / `orri` 格式）

`ror.b` 对源寄存器的 **低 8 位**做逻辑循环右移：`rdHB[7:0] = ror(rdHC[7:0], amount)`；
结果按值语义零扩展写满 64 位（`rdHB[63:8] = 0`）。符号无关、只有一个方向、不带 `u`/`s`
（`ADR-0032 D3`/`D4`）。

| 格式 | 旋转量 `amount` | 取值 |
|------|----------------|------|
| `orrr` | `rdHD[2:0]` | `0..7`（即对 8 取模） |
| `orri` | `immu6` | `0..7`；`immu6 > 7` ⇒ **ILLI** |

- `orrr` 的 `rdHD` 只有低 3 位参与（天然取模 8）；`orri` 的 `immu6` 是 6 位，**越界（`8..63`）触发 ILLI**（与 `shl.b` 的 `immu6 <= 7` 同口径）。
- 目的 `rdHB` 为 `rd0` ⇒ **ILLI**（规则 `dst_rd0`）；源 `rdHC` 可为 `rd0`（结果恒为 0）；`rdHB == rdHC` 允许。
- 编码：`ror.b` `orrr` = `010-001`、`orri` = `011-001`（`MISC-byte`）。
- 64 位语义与总述见 SimRISC-04 §4.2.3。

```simrisc
ror.b   rdHB, rdHC, rdHD        @@ 8 位循环右移（旋转量 = rdHD[2:0]）
ror.b   rdHB, rdHC, immu6       @@ 8 位循环右移（immu6 0..7）
```

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- `shl` 去掉 `u` 后缀（`shl.b`）并迁编码 `010-000`/`011-000`；新增 `ror.b`（逻辑循环右移，编码 `010-001`/`011-001`）及 §4.2.2 语义。
- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- 新增 `rev.b`（逐块反转，orri，`§4.2.1`）。
- 伪指令集收缩：删除 `not.*`/`neg.*` 1:1 别名。
- 新增「合法性检查」章（生成区）。
- 窄位宽指令精简、高位规则统一为值语义；`div`/`rem` 定值语义。
- 正文改用新汇编格式；新增「汇编指令速查」章（生成区）。

### 0.5.4（2026-09-28）

- 本册自原《SimRISC 数据类指令》的算术 / 逻辑运算部分按 8 位拆出，独立成「8 位数据运算」分册。

### 0.5.2（2026-07-18）

- 指令名后缀统一为 `.ub`/`.sb`（byte） 形；`add`/`sub`/`mul`/`div`/`rem`/`ext`/`sh` 按位宽与符号类型细分。

### 0.5.0（2026-07-15）

- 引入位掩码 `brrr` 格式；位掩码 `bN`→`bmN`→`bpN` 重命名。

### 0.4.1（2026-07-14）

- 初版：同步上游对应位宽的算术 / 逻辑运算指令。
