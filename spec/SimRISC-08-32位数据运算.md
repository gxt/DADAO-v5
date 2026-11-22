# SimRISC32位数据运算指令

> **版本：0.5.7**（与 SimRISC-00 一致）
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

### 1.4 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-08.idl` 生成，逐条如下：

<!-- IDL:add.ut_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`add.ut_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.1：仅低 32 位参与、进位静默丢弃；无符号 ⇒ 结果零扩展写满 64 位
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
Bits<32> sum = a + b;                         # 32 位和，进位丢弃
rd[rdHB] = {32'd0, sum};
```
<!-- IDL:add.ut_orrr_rd END -->

<!-- IDL:add.st_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`add.st_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.1：仅低 32 位参与、溢出静默丢弃；有符号 ⇒ 结果符号扩展写满 64 位
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
Bits<32> sum = a + b;                         # 32 位和，进位丢弃
rd[rdHB] = {{32{sum[31]}}, sum};              # 按和的 bit31 符号扩展
```
<!-- IDL:add.st_orrr_rd END -->

<!-- IDL:sub.ut_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`sub.ut_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.1：仅低 32 位参与、借位静默丢弃；无符号 ⇒ 结果零扩展写满 64 位
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
Bits<32> diff = a - b;                        # 32 位差，借位丢弃
rd[rdHB] = {32'd0, diff};
```
<!-- IDL:sub.ut_orrr_rd END -->

<!-- IDL:sub.st_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`sub.st_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.1：仅低 32 位参与、溢出静默丢弃；有符号 ⇒ 结果符号扩展写满 64 位
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
Bits<32> diff = a - b;                        # 32 位差，借位丢弃
rd[rdHB] = {{32{diff[31]}}, diff};            # 按差的 bit31 符号扩展
```
<!-- IDL:sub.st_orrr_rd END -->

<!-- IDL:cmp.ut_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`cmp.ut_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.2：源按低 32 位截断后作无符号比较，
# 结果 −1/0/+1 按 64 位写满目的寄存器（−1 ⇒ 64 位全 1）
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
if (a < b) {
  rd[rdHB] = {64{1'b1}};
} else if (a == b) {
  rd[rdHB] = 64'd0;
} else {
  rd[rdHB] = 64'd1;
}
```
<!-- IDL:cmp.ut_orrr_rd END -->

<!-- IDL:cmp.st_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`cmp.st_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.2：源按低 32 位截断后作有符号比较，
# 结果 −1/0/+1 按 64 位写满目的寄存器（−1 ⇒ 64 位全 1；.st/.ut 结果同值）
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
if ($signed(a) < $signed(b)) {
  rd[rdHB] = {64{1'b1}};
} else if (a == b) {
  rd[rdHB] = 64'd0;
} else {
  rd[rdHB] = 64'd1;
}
```
<!-- IDL:cmp.st_orrr_rd END -->

<!-- IDL:mul.ut_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`mul.ut_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.3：源只取低 32 位，结果只保留低 32 位（乘积高位丢弃）；
# 无符号 ⇒ 零扩展写满 64 位
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
Bits<32> prod = a * b;                        # 结果宽 = 两操作数最大宽 ⇒ 高 32 位丢弃
rd[rdHB] = {32'd0, prod};
```
<!-- IDL:mul.ut_orrr_rd END -->

<!-- IDL:mul.st_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`mul.st_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.3：源只取低 32 位，结果只保留低 32 位（乘积高位丢弃）；
# 有符号 ⇒ 符号扩展写满 64 位（低 32 位与无符号乘结果相同）
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
Bits<32> prod = a * b;                        # 结果宽 = 两操作数最大宽 ⇒ 高 32 位丢弃
rd[rdHB] = {{32{prod[31]}}, prod};
```
<!-- IDL:mul.st_orrr_rd END -->

<!-- IDL:div.ut_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`div.ut_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.3 + SimRISC-04 §1.4 定值表（div.ut 行）：除零 ⇒ 0x0000_0000_FFFF_FFFF，
# 不抛异常；无符号不存在溢出。除零须先判，IDL 的除法不定义除零行为
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
if (b == 32'd0) {
  rd[rdHB] = 64'h0000_0000_FFFF_FFFF;
} else {
  Bits<32> quot = a / b;                      # 无符号除法，商向零截断
  rd[rdHB] = {32'd0, quot};                   # 结果零扩展写满 64 位
}
```
<!-- IDL:div.ut_orrr_rd END -->

<!-- IDL:div.st_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`div.st_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.3 + SimRISC-04 §1.4 定值表（div.st 行）：
# 除零 ⇒ 0xFFFF_FFFF_FFFF_FFFF；INT32_MIN ÷ −1 ⇒ 0xFFFF_FFFF_8000_0000；均不抛异常
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
if (b == 32'd0) {
  rd[rdHB] = 64'hFFFF_FFFF_FFFF_FFFF;
} else if (a == 32'h8000_0000 && b == 32'hFFFF_FFFF) {
  rd[rdHB] = 64'hFFFF_FFFF_8000_0000;
} else {
  # 商向零截断（SimRISC-08 §1.3）：取 32 位绝对值做无符号除法，再按异号取负
  Bits<32> ma = a;
  if (a[31] == 1'b1) {
    ma = 32'd0 - a;                           # 32 位取负 = |a|（|INT32_MIN| = 2^31 仍可容纳）
  }
  Bits<32> mb = b;
  if (b[31] == 1'b1) {
    mb = 32'd0 - b;
  }
  Bits<32> quot = ma / mb;                    # 无符号除法：等于向零截断
  if (a[31] != b[31]) {
    quot = 32'd0 - quot;                      # 异号 ⇒ 商取负
  }
  rd[rdHB] = {{32{quot[31]}}, quot};          # 结果符号扩展写满 64 位
}
```
<!-- IDL:div.st_orrr_rd END -->

<!-- IDL:rem.ut_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`rem.ut_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.3 + SimRISC-04 §1.4 定值表（rem.ut 行）：除零 ⇒ 被除数本身，
# 零扩展写满 64 位，不抛异常；无符号不存在溢出
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
if (b == 32'd0) {
  rd[rdHB] = {32'd0, a};
} else {
  Bits<32> rem = a % b;                       # 无符号余数
  rd[rdHB] = {32'd0, rem};                    # 结果零扩展写满 64 位
}
```
<!-- IDL:rem.ut_orrr_rd END -->

<!-- IDL:rem.st_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`rem.st_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §1.3 + SimRISC-04 §1.4 定值表（rem.st 行）：
# 除零 ⇒ 被除数本身（符号扩展写满 64 位）；INT32_MIN % −1 ⇒ 0；均不抛异常
Bits<32> a = rd[rdHC][31:0];                  # 先读后写：两个源在任何写入之前捕获
Bits<32> b = rd[rdHD][31:0];
if (b == 32'd0) {
  rd[rdHB] = {{32{a[31]}}, a};
} else if (a == 32'h8000_0000 && b == 32'hFFFF_FFFF) {
  rd[rdHB] = 64'd0;
} else {
  # 余数符号 = 被除数符号（SimRISC-08 §1.3，C99）：
  # |余数| = |a| % |b|，再按被除数符号取负
  Bits<32> ma = a;
  if (a[31] == 1'b1) {
    ma = 32'd0 - a;                           # 32 位取负 = |a|（|INT32_MIN| = 2^31 仍可容纳）
  }
  Bits<32> mb = b;
  if (b[31] == 1'b1) {
    mb = 32'd0 - b;
  }
  Bits<32> rem = ma % mb;                      # 无符号余数（幅度 < |b| ≤ 2^31）
  if (a[31] == 1'b1) {
    rem = 32'd0 - rem;                         # 被除数为负 ⇒ 余数取负
  }
  rd[rdHB] = {{32{rem[31]}}, rem};             # 结果符号扩展写满 64 位
}
```
<!-- IDL:rem.st_orrr_rd END -->

## 2. Bit manipulating：位操作指令 — 值语义

OPC-tetra 子表中的 `shl.t`/`rol.t`/`shr.ut`/`shr.st` 提供 32 位移位/循环移位操作。`shr` 分 `u`（逻辑）/`s`（算术）变体；`shl`/`rol` 符号无关、不带 `u`/`s` 后缀。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=31。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.t`/`rol.t`/`shr.st`/`shr.ut` | 31 | 0-31 | `orrr`：`rdHD[4:0]`（高位忽略）；`orri`：`immu6[4:0]` |

运算公式：
```
shl.t:  rdHB[31:0]  = (rdHC[31:0] << shamt),  rdHB[63:32] = 0
rol.t:  rdHB[31:0]  = rol(rdHC[31:0], shamt), rdHB[63:32] = 0
shr.ut:  rdHB[31:0]  = (rdHC[31:0] >> shamt),  rdHB[63:32] = 0
shr.st:  rdHB[31:0]  = (rdHC[31:0] >> shamt) with sign(31),  rdHB[63:32] = sign_extend(rdHC[31])
```

**立即数形式** `immu6 > N` 触发 ILLI；**寄存器形式**取 `rdHD[N:0]` 的低位（高位忽略，不抛 ILLI）。

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

### 2.3 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-08.idl` 生成，逐条如下：

<!-- IDL:shl.t_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`shl.t_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2 公式（orrr）：rd[rdHB][31:0] = rd[rdHC][31:0] << shamt，rd[rdHB][63:32] = 0
# 寄存器形式 shamt = rd[rdHD][4:0]（高位忽略，天然对 32 取模，不抛 ILLI）
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = rd[rdHD][4:0];
Bits<32> res = lo << sh;                       # 32 位左移，移出位丢弃
rd[rdHB] = {32'd0, res};                       # 值语义：零扩展写满 64 位
```
<!-- IDL:shl.t_orrr_rd END -->

<!-- IDL:shl.t_orri_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`shl.t_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式 immu6 > N（N = 31）⇒ ILLI（SimRISC-08 §2；附录 B encode_sbz：immu6[5] 为 SBZ 位）
if (immu6 > 6'd31) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2 公式（orri）：rd[rdHB][31:0] = rd[rdHC][31:0] << shamt，rd[rdHB][63:32] = 0
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = immu6[4:0];
Bits<32> res = lo << sh;                       # 32 位左移，移出位丢弃
rd[rdHB] = {32'd0, res};                       # 值语义：零扩展写满 64 位
```
<!-- IDL:shl.t_orri_rd END -->

<!-- IDL:shr.ut_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`shr.ut_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2 公式（orrr）：rd[rdHB][31:0] = rd[rdHC][31:0] >> shamt（逻辑右移），rd[rdHB][63:32] = 0
# 寄存器形式 shamt = rd[rdHD][4:0]（高位忽略，天然对 32 取模，不抛 ILLI）
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = rd[rdHD][4:0];
Bits<32> res = lo >> sh;                       # 逻辑右移：高位补 0
rd[rdHB] = {32'd0, res};                       # 值语义：零扩展写满 64 位
```
<!-- IDL:shr.ut_orrr_rd END -->

<!-- IDL:shr.ut_orri_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`shr.ut_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式 immu6 > N（N = 31）⇒ ILLI（SimRISC-08 §2；附录 B encode_sbz：immu6[5] 为 SBZ 位）
if (immu6 > 6'd31) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2 公式（orri）：rd[rdHB][31:0] = rd[rdHC][31:0] >> shamt（逻辑右移），rd[rdHB][63:32] = 0
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = immu6[4:0];
Bits<32> res = lo >> sh;                       # 逻辑右移：高位补 0
rd[rdHB] = {32'd0, res};                       # 值语义：零扩展写满 64 位
```
<!-- IDL:shr.ut_orri_rd END -->

<!-- IDL:shr.st_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`shr.st_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2 公式（orrr）：rd[rdHB][31:0] = rd[rdHC][31:0] >> shamt，高位补符号位 rd[rdHC][31]，
# rd[rdHB][63:32] = 符号扩展自 rd[rdHC][31] ⇒ 整 64 位 = 低 32 位结果的符号扩展
# 寄存器形式 shamt = rd[rdHD][4:0]（高位忽略，天然对 32 取模，不抛 ILLI）
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = rd[rdHD][4:0];
Bits<32> res = $signed(lo) >>> sh;             # 算术右移：高位补 rd[rdHC][31]
rd[rdHB] = {{32{res[31]}}, res};                # 算术右移保持 bit31 ⇒ 高 32 位即 rd[rdHC][31] 的符号扩展
```
<!-- IDL:shr.st_orrr_rd END -->

<!-- IDL:shr.st_orri_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`shr.st_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式 immu6 > N（N = 31）⇒ ILLI（SimRISC-08 §2；附录 B encode_sbz：immu6[5] 为 SBZ 位）
if (immu6 > 6'd31) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2 公式（orri）：rd[rdHB][31:0] = rd[rdHC][31:0] >> shamt，高位补符号位 rd[rdHC][31]，
# rd[rdHB][63:32] = 符号扩展自 rd[rdHC][31] ⇒ 整 64 位 = 低 32 位结果的符号扩展
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = immu6[4:0];
Bits<32> res = $signed(lo) >>> sh;             # 算术右移：高位补 rd[rdHC][31]
rd[rdHB] = {{32{res[31]}}, res};                # 算术右移保持 bit31 ⇒ 高 32 位即 rd[rdHC][31] 的符号扩展
```
<!-- IDL:shr.st_orri_rd END -->

<!-- IDL:rev.t_orri_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`rev.t_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 合法 k = {1,2,4,8,16}（one-hot 且 k < S = 32）；其余 ⇒ ILLI（附录 B encode_onehot）
if (immu6 != 6'd1 && immu6 != 6'd2 && immu6 != 6'd4 && immu6 != 6'd8 && immu6 != 6'd16) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2.1 + SimRISC-04 §2.2.1：64 位源按 32 位块（S = 32）分块，
# 每块按 k 位切成 32/k 个单元，反转单元顺序、单元内位序不变；两块同样处理。
# concat 的首元素落在最高位 ⇒ 元素按低位单元在前书写即为「单元倒序」。
Bits<32> l = rd[rdHC][31:0];
Bits<32> h = rd[rdHC][63:32];
Bits<32> rl;
Bits<32> rh;
if (immu6 == 6'd16) {
  rl = {l[15:0], l[31:16]};
  rh = {h[15:0], h[31:16]};
} else if (immu6 == 6'd8) {
  rl = {l[7:0], l[15:8], l[23:16], l[31:24]};
  rh = {h[7:0], h[15:8], h[23:16], h[31:24]};
} else if (immu6 == 6'd4) {
  rl = {l[3:0], l[7:4], l[11:8], l[15:12],
        l[19:16], l[23:20], l[27:24], l[31:28]};
  rh = {h[3:0], h[7:4], h[11:8], h[15:12],
        h[19:16], h[23:20], h[27:24], h[31:28]};
} else if (immu6 == 6'd2) {
  rl = {l[1:0], l[3:2], l[5:4], l[7:6], l[9:8], l[11:10], l[13:12], l[15:14],
        l[17:16], l[19:18], l[21:20], l[23:22], l[25:24], l[27:26], l[29:28], l[31:30]};
  rh = {h[1:0], h[3:2], h[5:4], h[7:6], h[9:8], h[11:10], h[13:12], h[15:14],
        h[17:16], h[19:18], h[21:20], h[23:22], h[25:24], h[27:26], h[29:28], h[31:30]};
} else {                             # k = 1：块内 32 位位序整体反转
  rl = {l[0], l[1], l[2], l[3], l[4], l[5], l[6], l[7], l[8], l[9], l[10], l[11], l[12], l[13], l[14], l[15],
        l[16], l[17], l[18], l[19], l[20], l[21], l[22], l[23], l[24], l[25], l[26], l[27], l[28], l[29], l[30], l[31]};
  rh = {h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], h[8], h[9], h[10], h[11], h[12], h[13], h[14], h[15],
        h[16], h[17], h[18], h[19], h[20], h[21], h[22], h[23], h[24], h[25], h[26], h[27], h[28], h[29], h[30], h[31]};
}
# 两块一律同样处理 ⇒ 结果 = {高块反转, 低块反转}（SimRISC-04 §2.2.1：rdHB 全 64 位都是结果）
rd[rdHB] = {rh, rl};
```
<!-- IDL:rev.t_orri_rd END -->

<!-- IDL:rol.t_orrr_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`rol.t_orrr_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2.2 公式（orrr）：rd[rdHB][31:0] = 低 32 位循环左移（旋转量 shamt），rd[rdHB][63:32] = 0
# 循环左移：左移 n 位 与 右移 (32 − n) mod 32 位相或；只有一个方向（左）
# 寄存器形式 shamt = rd[rdHD][4:0]（高位忽略，天然对 32 取模，不抛 ILLI）
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = rd[rdHD][4:0];
Bits<5> inv = 5'd0 - sh;                       # (32 − n) mod 32，n = 0 时亦成立
Bits<32> res = (lo << sh) | (lo >> inv);        # 32 位循环左移
rd[rdHB] = {32'd0, res};                       # 值语义：零扩展写满 64 位
```
<!-- IDL:rol.t_orrr_rd END -->

<!-- IDL:rol.t_orri_rd BEGIN -->
<!-- 本块由 IDL 源生成，禁手改；生成器见 `idl/tools/` -->
**`rol.t_orri_rd`**
```idl
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式 immu6 > N（N = 31）⇒ ILLI（SimRISC-08 §2；附录 B encode_sbz：immu6[5] 为 SBZ 位）
if (immu6 > 6'd31) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# SimRISC-08 §2.2 公式（orri）：rd[rdHB][31:0] = 低 32 位循环左移（旋转量 shamt），rd[rdHB][63:32] = 0
# 循环左移：左移 n 位 与 右移 (32 − n) mod 32 位相或；只有一个方向（左）
Bits<32> lo = rd[rdHC][31:0];                 # 先读后写：源在任何写入之前捕获
Bits<5> sh = immu6[4:0];
Bits<5> inv = 5'd0 - sh;                       # (32 − n) mod 32，n = 0 时亦成立
Bits<32> res = (lo << sh) | (lo >> inv);        # 32 位循环左移
rd[rdHB] = {32'd0, res};                       # 值语义：零扩展写满 64 位
```
<!-- IDL:rol.t_orri_rd END -->

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
