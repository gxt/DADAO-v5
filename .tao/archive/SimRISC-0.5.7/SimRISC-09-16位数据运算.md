# SimRISC16位数据运算指令

> **版本：0.5.7**（与 SimRISC-00 一致）
> **分类：16位数据运算** — .sw/.uw 运算 + rev.w（逐块反转）+ shl.w/rol.w（移位/循环移位）

## 1. 算术运算类指令

### 1.1 加减操作

OPC-wyde 子表中的 `add`/`sub` 提供 16 位加减运算，按符号类型分为两个变体：

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

### 1.2 比较操作 — 值语义

OPC-wyde 子表中的 `cmp.s`/`cmp.u`（后缀 `.sw`/`.uw`）提供 16 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.uw`/`cmp.sw` | 16 位 | `cmp.uw rdHB, rdHC, rdHD` | bits[15:0] |

**高位规则**：比较结果（−1/0/+1）**按 64 位扩展**写满目的寄存器——−1 ⇒ `0xFFFF_FFFF_FFFF_FFFF`（64 位全 1）、0 ⇒ `0`、+1 ⇒ `1`；`.sw`/`.uw` 结果相同（符号扩展与 64 位扩展在 −1/0/+1 上同值）。源操作数仍按上述位宽截断后比较。

例如 `cmp.sw rd1, rd2, rd3` 将 rd2 和 rd3 的低 16 位按有符号比较：rd2 < rd3 时 `rd1 = 0xFFFF_FFFF_FFFF_FFFF`，相等时 `rd1 = 0`，rd2 > rd3 时 `rd1 = 1`。

### 1.3 乘除操作

OPC-wyde 子表中的 `mul`/`div`/`rem` 提供 16 位乘除余运算。`mul` 后缀为 `.uw`/`.sw`；`div`/`rem` 后缀为 `.uw`/`.sw`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.uw`/`mul.sw`/`div.uw`/`div.sw`/`rem.uw`/`rem.sw` | 16 位 | `mul.uw rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：定值表见 SimRISC-04。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 wyde 对应的 −32768 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04。

### 1.4 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-09.idl` 生成，逐条如下：

<!-- IDL:add.sw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`add.sw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位有符号加（SimRISC-09 §1.1）：源取 rd[rdHC][15:0]/rd[rdHD][15:0]，溢出静默丢弃；
# 结果按 bit15 符号扩展写满 64 位
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
Bits<16> sum = $signed(src1) + $signed(src2);  # 结果宽 = 16 ⇒ 高 16 位丢弃
rd[rdHB] = {{48{sum[15]}}, sum};
```
<!-- IDL:add.sw_orrr_rd END -->

<!-- IDL:add.uw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`add.uw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位无符号加（SimRISC-09 §1.1）：源取 rd[rdHC][15:0]/rd[rdHD][15:0]，进位静默丢弃；
# 结果零扩展写满 64 位
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
Bits<16> sum = src1 + src2;                    # 结果宽 = 16 ⇒ 高 16 位丢弃
rd[rdHB] = {48'd0, sum};
```
<!-- IDL:add.uw_orrr_rd END -->

<!-- IDL:sub.sw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`sub.sw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位有符号减（SimRISC-09 §1.1）：源取 rd[rdHC][15:0]/rd[rdHD][15:0]，借位静默丢弃；
# 结果按 bit15 符号扩展写满 64 位
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
Bits<16> diff = $signed(src1) - $signed(src2); # 结果宽 = 16 ⇒ 高 16 位丢弃
rd[rdHB] = {{48{diff[15]}}, diff};
```
<!-- IDL:sub.sw_orrr_rd END -->

<!-- IDL:sub.uw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`sub.uw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位无符号减（SimRISC-09 §1.1）：源取 rd[rdHC][15:0]/rd[rdHD][15:0]，借位静默丢弃；
# 结果零扩展写满 64 位
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
Bits<16> diff = src1 - src2;                   # 结果宽 = 16 ⇒ 高 16 位丢弃
rd[rdHB] = {48'd0, diff};
```
<!-- IDL:sub.uw_orrr_rd END -->

<!-- IDL:cmp.sw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`cmp.sw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位有符号比较（SimRISC-09 §1.2）：源按 size 截断后有符号比较，
# 结果（−1/0/+1）按 64 位扩展写满目的寄存器
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
if ($signed(src1) < $signed(src2)) {
  rd[rdHB] = {64{1'b1}};
} else if (src1 == src2) {
  rd[rdHB] = 64'd0;
} else {
  rd[rdHB] = 64'd1;
}
```
<!-- IDL:cmp.sw_orrr_rd END -->

<!-- IDL:cmp.uw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`cmp.uw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位无符号比较（SimRISC-09 §1.2）：源按 size 截断后无符号比较，
# 结果（−1/0/+1）按 64 位扩展写满目的寄存器
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
if (src1 < src2) {
  rd[rdHB] = {64{1'b1}};
} else if (src1 == src2) {
  rd[rdHB] = 64'd0;
} else {
  rd[rdHB] = 64'd1;
}
```
<!-- IDL:cmp.uw_orrr_rd END -->

<!-- IDL:mul.sw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`mul.sw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位有符号乘（SimRISC-09 §1.3）：源取 rd[rdHC][15:0]/rd[rdHD][15:0]，积只保留低 16 位
# （补码乘法的低 16 位与无符号乘相同）；结果按 bit15 符号扩展写满 64 位
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
Bits<16> prod = src1 * src2;                   # 结果宽 = 16 ⇒ 高 16 位丢弃
rd[rdHB] = {{48{prod[15]}}, prod};
```
<!-- IDL:mul.sw_orrr_rd END -->

<!-- IDL:mul.uw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`mul.uw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位无符号乘（SimRISC-09 §1.3）：源取 rd[rdHC][15:0]/rd[rdHD][15:0]，积只保留低 16 位；
# 结果零扩展写满 64 位
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
Bits<16> prod = src1 * src2;                   # 结果宽 = 16 ⇒ 高 16 位丢弃
rd[rdHB] = {48'd0, prod};
```
<!-- IDL:mul.uw_orrr_rd END -->

<!-- IDL:div.sw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`div.sw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位有符号除（SimRISC-09 §1.3 + SimRISC-04 §1.4 定值表 div.sw 行，均不抛异常）：
# 除零 ⇒ 0xFFFF_FFFF_FFFF_FFFF；INT16_MIN ÷ −1 ⇒ 0xFFFF_FFFF_FFFF_8000；
# 其余 truncate-toward-zero（C99）：取 16 位绝对值做无符号除法，再按异号取负
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
if (src2 == 16'd0) {
  rd[rdHB] = 64'hFFFF_FFFF_FFFF_FFFF;
} else if (src1 == 16'h8000 && src2 == 16'hFFFF) {
  rd[rdHB] = 64'hFFFF_FFFF_FFFF_8000;
} else {
  Bits<16> ma = src1;
  if (src1[15] == 1'b1) {
    ma = 16'd0 - src1;                         # 16 位取负 = |src1|（|INT16_MIN| = 2^15 仍可容纳）
  }
  Bits<16> mb = src2;
  if (src2[15] == 1'b1) {
    mb = 16'd0 - src2;
  }
  Bits<16> quot = ma / mb;                     # 无符号除法：等于向零截断
  if (src1[15] != src2[15]) {
    quot = 16'd0 - quot;                       # 异号 ⇒ 商取负
  }
  rd[rdHB] = {{48{quot[15]}}, quot};           # 结果符号扩展写满 64 位
}
```
<!-- IDL:div.sw_orrr_rd END -->

<!-- IDL:div.uw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`div.uw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位无符号除（SimRISC-09 §1.3 + SimRISC-04 §1.4 定值表 div.uw 行）：
# 除零 ⇒ 0x0000_0000_0000_FFFF，不抛异常；无符号不存在溢出档
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
if (src2 == 16'd0) {
  rd[rdHB] = 64'h0000_0000_0000_FFFF;
} else {
  Bits<16> quot = src1 / src2;                 # 无符号除法，商向零截断
  rd[rdHB] = {48'd0, quot};                    # 结果零扩展写满 64 位
}
```
<!-- IDL:div.uw_orrr_rd END -->

<!-- IDL:rem.sw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`rem.sw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位有符号余（SimRISC-09 §1.3 + SimRISC-04 §1.4 定值表 rem.sw 行，均不抛异常）：
# 除零 ⇒ 被除数本身（符号扩展）；INT16_MIN % −1 ⇒ 0；
# 其余 truncate-toward-zero，余数符号 = 被除数符号（C99）
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
if (src2 == 16'd0) {
  rd[rdHB] = {{48{src1[15]}}, src1};
} else if (src1 == 16'h8000 && src2 == 16'hFFFF) {
  rd[rdHB] = 64'd0;
} else {
  Bits<16> ma = src1;
  if (src1[15] == 1'b1) {
    ma = 16'd0 - src1;                         # 16 位取负 = |src1|（|INT16_MIN| = 2^15 仍可容纳）
  }
  Bits<16> mb = src2;
  if (src2[15] == 1'b1) {
    mb = 16'd0 - src2;
  }
  Bits<16> rem = ma % mb;                      # 无符号余数（幅度 < |src2| ≤ 2^15）
  if (src1[15] == 1'b1) {
    rem = 16'd0 - rem;                         # 被除数为负 ⇒ 余数取负
  }
  rd[rdHB] = {{48{rem[15]}}, rem};             # 结果符号扩展写满 64 位
}
```
<!-- IDL:rem.sw_orrr_rd END -->

<!-- IDL:rem.uw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`rem.uw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位无符号余（SimRISC-09 §1.3 + SimRISC-04 §1.4 定值表 rem.uw 行）：
# 除零 ⇒ 被除数本身（零扩展），不抛异常；无符号不存在溢出档
Bits<16> src1 = rd[rdHC][15:0];                # 先读后写：两个源在任何写入之前捕获
Bits<16> src2 = rd[rdHD][15:0];
if (src2 == 16'd0) {
  rd[rdHB] = {48'd0, src1};
} else {
  Bits<16> rem = src1 % src2;                  # 无符号余数
  rd[rdHB] = {48'd0, rem};                     # 结果零扩展写满 64 位
}
```
<!-- IDL:rem.uw_orrr_rd END -->

## 2. Bit manipulating：位操作指令 — 值语义

OPC-wyde 子表中的 `shl.w`/`rol.w`/`shr.uw`/`shr.sw` 提供 16 位移位/循环移位操作。`shr` 分 `u`（逻辑）/`s`（算术）变体；`shl`/`rol` 符号无关、不带 `u`/`s` 后缀。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=15。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.w`/`rol.w`/`shr.sw`/`shr.uw` | 15 | 0-15 | `orrr`：`rdHD[3:0]`（高位忽略）；`orri`：`immu6[3:0]` |

运算公式：
```
shl.w:  rdHB[15:0]  = (rdHC[15:0] << shamt),  rdHB[63:16] = 0
rol.w:  rdHB[15:0]  = rol(rdHC[15:0], shamt), rdHB[63:16] = 0
shr.uw:  rdHB[15:0]  = (rdHC[15:0] >> shamt),  rdHB[63:16] = 0
shr.sw:  rdHB[15:0]  = (rdHC[15:0] >> shamt) with sign(15),  rdHB[63:16] = sign_extend(rdHC[15])
```

**立即数形式** `immu6 > N` 触发 ILLI；**寄存器形式**取 `rdHD[N:0]` 的低位（高位忽略，不抛 ILLI）。

**注**：`ext.uw`/`ext.sw`（16位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。

### 2.1 逐块反转 rev.w（orri 格式）

`rev.w` 对 64 位源寄存器**按 16 位块逐块反转**：每块（S = 16）按 `k` 位切成
`16/k` 个单元，反转单元顺序（单元内部位序不变），四个块一律同样处理。
操作数格式 `orri`：`rev.w rdHB, rdHC, immu6`。

- 合法 `k` = `{1,2,4,8}`（one-hot 且 `k < S = 16`）；非 one-hot 或 `k ≥ 16` 触发 **ILLI**（规则 `encode_onehot`）。
- `k=8` 即 `bswap16` 语义（须源高 48 位为 0）；`k=1` 只反转**块内**位序，**不是** 64 位整体位反序。
- 逐块反转的总述与伪代码见 SimRISC-04。

### 2.2 逻辑循环左移 rol.w（`orrr` / `orri` 格式）

`rol.w` 对源寄存器的 **低 16 位**做逻辑循环左移：`rdHB[15:0] = rol(rdHC[15:0], amount)`；
结果按值语义零扩展写满 64 位（`rdHB[63:16] = 0`）。符号无关、只有一个方向、不带 `u`/`s`
。

| 格式 | 旋转量 `amount` | 取值 |
|------|----------------|------|
| `orrr` | `rdHD[3:0]` | `0..15`（即对 16 取模） |
| `orri` | `immu6` | `0..15`；`immu6 > 15` ⇒ **ILLI** |

- `orrr` 的 `rdHD` 只有低 4 位参与（天然取模 16）；`orri` 的 `immu6` 是 6 位，**越界（`16..63`）触发 ILLI**（与 `shl.w` 的 `immu6 <= 15` 同口径）。
- 目的 `rdHB` 为 `rd0` ⇒ **ILLI**（规则 `dst_rd0`）；源 `rdHC` 可为 `rd0`（结果恒为 0）；`rdHB == rdHC` 允许。
- 格式：`orrr`（寄存器旋转量）/ `orri`（立即数旋转量），属 `OPC-wyde` 子表。
- 64 位语义与总述见 SimRISC-04。

```simrisc
rol.w   rdHB, rdHC, rdHD        @@ 16 位循环左移（旋转量 = rdHD[3:0]）
rol.w   rdHB, rdHC, immu6       @@ 16 位循环左移（immu6 0..15）
```

### 2.3 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-09.idl` 生成，逐条如下：

<!-- IDL:shl.w_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`shl.w_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > N=15 ⇒ ILLI（SimRISC-09 §2；附录 B encode_sbz「shl.w … shamt > 15」）
if (immu6 > 6'd15) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位左移（SimRISC-09 §2 公式 shl.w）：shamt = immu6[3:0]，块内左移、移出位丢弃，
# 结果零扩展写满 64 位（rd[rdHB][63:16] = 0）
Bits<4> shamt = immu6[3:0];
Bits<16> res = rd[rdHC][15:0] << shamt;        # 先读后写：源在任何写入之前捕获
rd[rdHB] = {48'd0, res};
```
<!-- IDL:shl.w_orri_rd END -->

<!-- IDL:shl.w_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`shl.w_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][3:0]（取 rdHD 号寄存器的低 4 位，天然对 16 取模，
#               rdHD 的更高位忽略、不抛 ILLI，§2）；
# 16 位左移、移出位丢弃，结果零扩展写满 64 位
Bits<4> shamt = rd[rdHD][3:0];
Bits<16> res = rd[rdHC][15:0] << shamt;        # 先读后写：源在任何写入之前捕获
rd[rdHB] = {48'd0, res};
```
<!-- IDL:shl.w_orrr_rd END -->

<!-- IDL:shr.uw_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`shr.uw_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > N=15 ⇒ ILLI（SimRISC-09 §2；附录 B encode_sbz「shr.uw … shamt > 15」）
if (immu6 > 6'd15) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位逻辑右移（§2 公式 shr.uw）：shamt = immu6[3:0]，高位补 0，结果零扩展写满 64 位
Bits<4> shamt = immu6[3:0];
Bits<16> res = rd[rdHC][15:0] >> shamt;        # 先读后写：源在任何写入之前捕获
rd[rdHB] = {48'd0, res};
```
<!-- IDL:shr.uw_orri_rd END -->

<!-- IDL:shr.uw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`shr.uw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][3:0]（取 rdHD 号寄存器的低 4 位，高位忽略、不抛 ILLI，§2）；
# 16 位逻辑右移、高位补 0，结果零扩展写满 64 位
Bits<4> shamt = rd[rdHD][3:0];
Bits<16> res = rd[rdHC][15:0] >> shamt;        # 先读后写：源在任何写入之前捕获
rd[rdHB] = {48'd0, res};
```
<!-- IDL:shr.uw_orrr_rd END -->

<!-- IDL:shr.sw_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`shr.sw_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > N=15 ⇒ ILLI（SimRISC-09 §2；附录 B encode_sbz「shr.sw … shamt > 15」）
if (immu6 > 6'd15) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位算术右移（§2 公式 shr.sw）：shamt = immu6[3:0]；块内右移、空位补 rd[rdHC][15]，
# 目的[63:16] = 符号扩展 rd[rdHC][15] ⇒ {48{val[15]}}
Bits<16> val = rd[rdHC][15:0];                 # 先读后写：源在任何写入之前捕获
Bits<4> shamt = immu6[3:0];
Bits<16> res = $signed(val) >>> shamt;
rd[rdHB] = {{48{val[15]}}, res};
```
<!-- IDL:shr.sw_orri_rd END -->

<!-- IDL:shr.sw_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`shr.sw_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][3:0]（取 rdHD 号寄存器的低 4 位，高位忽略、不抛 ILLI，§2）；
# 16 位算术右移、空位补 rd[rdHC][15]，目的[63:16] = 符号扩展 rd[rdHC][15]
Bits<16> val = rd[rdHC][15:0];                 # 先读后写：源在任何写入之前捕获
Bits<4> shamt = rd[rdHD][3:0];
Bits<16> res = $signed(val) >>> shamt;
rd[rdHB] = {{48{val[15]}}, res};
```
<!-- IDL:shr.sw_orrr_rd END -->

<!-- IDL:rev.w_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`rev.w_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# k 须 one-hot 且 k < S=16（SimRISC-09 §2.1 + SimRISC-04 §2.2.1；附录 B encode_onehot）
# ⇒ 合法仅 {1,2,4,8}；非 one-hot 或 k ≥ 16 ⇒ ILLI
if (immu6 != 6'd1 && immu6 != 6'd2 && immu6 != 6'd4 && immu6 != 6'd8) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位块内逐块反转（§2.1）：整 64 位源按 16 位块切分（4 块），每块按 k 位切成 16/k 个单元，
# 反转单元顺序、单元内部位序不变，四块一律同法处理（不是 64 位整体位反序，也不是 bswap16 专用）。
# 等价写法：按距离 8/4/2/1 依次交换单元（k=8 只做距离 8、k=1 四步全做）；
# 掩码在 16 位块内重复 ⇒ 交换不跨块
Bits<64> x = rd[rdHC];
if (immu6 == 6'd1) {
  x = ((x & 64'hAAAA_AAAA_AAAA_AAAA) >> 1) | ((x & 64'h5555_5555_5555_5555) << 1);
}
if (immu6 == 6'd1 || immu6 == 6'd2) {
  x = ((x & 64'hCCCC_CCCC_CCCC_CCCC) >> 2) | ((x & 64'h3333_3333_3333_3333) << 2);
}
if (immu6 == 6'd1 || immu6 == 6'd2 || immu6 == 6'd4) {
  x = ((x & 64'hF0F0_F0F0_F0F0_F0F0) >> 4) | ((x & 64'h0F0F_0F0F_0F0F_0F0F) << 4);
}
x = ((x & 64'hFF00_FF00_FF00_FF00) >> 8) | ((x & 64'h00FF_00FF_00FF_00FF) << 8);
rd[rdHB] = x;
```
<!-- IDL:rev.w_orri_rd END -->

<!-- IDL:rol.w_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`rol.w_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > 15 ⇒ ILLI（SimRISC-09 §2.2；附录 B encode_sbz「rol.w … shamt > 15」）
if (immu6 > 6'd15) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 16 位逻辑循环左移（§2.2）：shamt = immu6[3:0]，只一个方向，结果零扩展写满 64 位。
# 按位等价式：val 左移 s 位 与 val 右移 16-s 位 按位或；写成 {val,val} 右移 16-s 后取低 16 位，
# 使 s=0 时右移量 16 落在 32 位宽内（不出现对 16 位值右移 16 位）
Bits<16> val = rd[rdHC][15:0];                 # 先读后写：源在任何写入之前捕获
Bits<4> shamt = immu6[3:0];
Bits<32> dup = {2{val}};
Bits<32> shifted = dup >> (16 - shamt);
Bits<16> res = shifted[15:0];
rd[rdHB] = {48'd0, res};
```
<!-- IDL:rol.w_orri_rd END -->

<!-- IDL:rol.w_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`rol.w_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][3:0]（取 rdHD 号寄存器的低 4 位，天然对 16 取模，
#               rdHD 的更高位忽略、不抛 ILLI，§2.2）；
# 16 位逻辑循环左移、只一个方向，结果零扩展写满 64 位（同 orri 形式的算式）
Bits<16> val = rd[rdHC][15:0];                 # 先读后写：源在任何写入之前捕获
Bits<4> shamt = rd[rdHD][3:0];
Bits<32> dup = {2{val}};
Bits<32> shifted = dup >> (16 - shamt);
Bits<16> res = shifted[15:0];
rd[rdHB] = {48'd0, res};
```
<!-- IDL:rol.w_orrr_rd END -->

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

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
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.sw_orrr_rd`, `add.uw_orrr_rd`, `cmp.sw_orrr_rd`, `cmp.uw_orrr_rd`, `div.sw_orrr_rd`, `div.uw_orrr_rd`, `mul.sw_orrr_rd`, `mul.uw_orrr_rd`, `rem.sw_orrr_rd`, `rem.uw_orrr_rd`, `rev.w_orri_rd`, `rol.w_orri_rd`, `rol.w_orrr_rd`, `shl.w_orri_rd`, `shl.w_orrr_rd`, `shr.sw_orri_rd`, `shr.sw_orrr_rd`, `shr.uw_orri_rd`, `shr.uw_orrr_rd`, `sub.sw_orrr_rd`, `sub.uw_orrr_rd`（21 条）
* `encode_sbz`：SBZ 非零 → ILLI — `rol.w_orri_rd`, `shl.w_orri_rd`, `shr.sw_orri_rd`, `shr.uw_orri_rd`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `rev.w_orri_rd`（1 条）
<!-- LEGALITY_END -->
