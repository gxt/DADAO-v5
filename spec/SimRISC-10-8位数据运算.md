# SimRISC8位数据运算指令

> **版本：0.5.7-rc**（与 SimRISC-00 一致）
> **分类：8位数据运算** — .sb/.ub 运算 + rev.b（逐块反转）+ shl.b/rol.b（移位/循环移位）

## 1. 算术运算类指令

### 1.1 加减操作

OPC-byte 子表中的 `add`/`sub` 提供 8 位加减运算，按符号类型分为两个变体：

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
rol.b   rdHB, rdHC, rdHD
rol.b   rdHB, rdHC, immu6
shr.ub  rdHB, rdHC, rdHD
shr.ub  rdHB, rdHC, immu6
shr.sb  rdHB, rdHC, rdHD
shr.sb  rdHB, rdHC, immu6
```

<!-- IDL:add.sb_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: add.sb_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位有符号加（SimRISC-10 §1.1）：源取 rd[rdHC][7:0]/rd[rdHD][7:0]，溢出静默丢弃；
# 结果按 bit7 符号扩展写满 64 位
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
Bits<8> sum = $signed(src1) + $signed(src2);
rd[rdHB] = {{56{sum[7]}}, sum};
```
<!-- IDL:add.sb_orrr_rd END -->

<!-- IDL:add.ub_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: add.ub_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位无符号加（SimRISC-10 §1.1）：源取 rd[rdHC][7:0]/rd[rdHD][7:0]，进位静默丢弃；
# 结果零扩展写满 64 位
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
Bits<8> sum = src1 + src2;
rd[rdHB] = {56'd0, sum};
```
<!-- IDL:add.ub_orrr_rd END -->

<!-- IDL:sub.sb_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: sub.sb_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位有符号减（SimRISC-10 §1.1）：源取 rd[rdHC][7:0]/rd[rdHD][7:0]，借位静默丢弃；
# 结果按 bit7 符号扩展写满 64 位
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
Bits<8> diff = $signed(src1) - $signed(src2);
rd[rdHB] = {{56{diff[7]}}, diff};
```
<!-- IDL:sub.sb_orrr_rd END -->

<!-- IDL:sub.ub_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: sub.ub_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位无符号减（SimRISC-10 §1.1）：源取 rd[rdHC][7:0]/rd[rdHD][7:0]，借位静默丢弃；
# 结果零扩展写满 64 位
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
Bits<8> diff = src1 - src2;
rd[rdHB] = {56'd0, diff};
```
<!-- IDL:sub.ub_orrr_rd END -->

### 1.2 比较操作 — 值语义

OPC-byte 子表中的 `cmp.s`/`cmp.u`（后缀 `.sb`/`.ub`）提供 8 位比较运算。源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 | 比较范围 |
|------|------|---------|---------|
| `cmp.ub`/`cmp.sb` | 8 位 | `cmp.ub rdHB, rdHC, rdHD` | bits[7:0] |

**高位规则**：比较结果（−1/0/+1）**按 64 位扩展**写满目的寄存器——−1 ⇒ `0xFFFF_FFFF_FFFF_FFFF`（64 位全 1）、0 ⇒ `0`、+1 ⇒ `1`；`.sb`/`.ub` 结果相同（符号扩展与 64 位扩展在 −1/0/+1 上同值）。源操作数仍按上述位宽截断后比较。

例如 `cmp.sb rd1, rd2, rd3` 将 rd2 和 rd3 的低 8 位按有符号比较：rd2 < rd3 时 `rd1 = 0xFFFF_FFFF_FFFF_FFFF`，相等时 `rd1 = 0`，rd2 > rd3 时 `rd1 = 1`。

<!-- IDL:cmp.sb_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: cmp.sb_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位有符号比较（SimRISC-10 §1.2）：源按 size 截断后有符号比较，
# 结果（−1/0/+1）按 64 位扩展写满目的寄存器
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
if ($signed(src1) < $signed(src2)) {
  rd[rdHB] = {64{1'b1}};
} else if (src1 == src2) {
  rd[rdHB] = 64'd0;
} else {
  rd[rdHB] = 64'd1;
}
```
<!-- IDL:cmp.sb_orrr_rd END -->

<!-- IDL:cmp.ub_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: cmp.ub_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位无符号比较（SimRISC-10 §1.2）：源按 size 截断后无符号比较，
# 结果（−1/0/+1）按 64 位扩展写满目的寄存器
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
if (src1 < src2) {
  rd[rdHB] = {64{1'b1}};
} else if (src1 == src2) {
  rd[rdHB] = 64'd0;
} else {
  rd[rdHB] = 64'd1;
}
```
<!-- IDL:cmp.ub_orrr_rd END -->

### 1.3 乘除操作

OPC-byte 子表中的 `mul`/`div`/`rem` 提供 8 位乘除余运算。`mul` 后缀为 `.ub`/`.sb`；`div`/`rem` 后缀为 `.ub`/`.sb`。源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

| 指令 | 位宽 | 汇编语法 |
|------|------|---------|
| `mul.ub`/`mul.sb`/`div.ub`/`div.sb`/`rem.ub`/`rem.sb` | 8 位 | `mul.ub rdHB, rdHC, rdHD` |

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：定值表见 SimRISC-04。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中 byte 对应的 −128 ÷ −1 见定值表。`div.u`/`rem.u` 不存在溢出。
- **定值表**：详见 SimRISC-04。

<!-- IDL:mul.sb_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: mul.sb_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位有符号乘（SimRISC-10 §1.3）：源取 rd[rdHC][7:0]/rd[rdHD][7:0]，积只保留 8 位；
# 结果按 bit7 符号扩展写满 64 位
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
Bits<8> prod = $signed(src1) * $signed(src2);
rd[rdHB] = {{56{prod[7]}}, prod};
```
<!-- IDL:mul.sb_orrr_rd END -->

<!-- IDL:mul.ub_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: mul.ub_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位无符号乘（SimRISC-10 §1.3）：源取 rd[rdHC][7:0]/rd[rdHD][7:0]，积只保留 8 位；
# 结果零扩展写满 64 位
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
Bits<8> prod = src1 * src2;
rd[rdHB] = {56'd0, prod};
```
<!-- IDL:mul.ub_orrr_rd END -->

<!-- IDL:div.sb_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: div.sb_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位有符号除（SimRISC-10 §1.3）：除数为零、INT8_MIN ÷ −1 走定值表（SimRISC-04 §1.4，
# 不触发异常）：除零 ⇒ −1、溢出 ⇒ −128，均符号扩展写满 64 位；其余 truncate-toward-zero
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
if (src2 == 8'd0) {
  rd[rdHB] = {64{1'b1}};
} else if (src1 == 8'b1000_0000 && src2 == 8'b1111_1111) {
  rd[rdHB] = {{56{1'b1}}, 8'b1000_0000};
} else {
  Bits<8> quot = $signed(src1) / $signed(src2);
  rd[rdHB] = {{56{quot[7]}}, quot};
}
```
<!-- IDL:div.sb_orrr_rd END -->

<!-- IDL:div.ub_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: div.ub_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位无符号除（SimRISC-10 §1.3）：除数为零走定值表（SimRISC-04 §1.4，不触发异常）
# ⇒ 0xFF 零扩展写满 64 位；无符号无溢出档
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
if (src2 == 8'd0) {
  rd[rdHB] = {56'd0, 8'hFF};
} else {
  Bits<8> quot = src1 / src2;
  rd[rdHB] = {56'd0, quot};
}
```
<!-- IDL:div.ub_orrr_rd END -->

<!-- IDL:rem.sb_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: rem.sb_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位有符号余（SimRISC-10 §1.3）：除数为零、INT8_MIN ÷ −1 走定值表（SimRISC-04 §1.4，
# 不触发异常）：除零 ⇒ 被除数（符号扩展）、溢出 ⇒ 0，均写满 64 位；
# 其余 truncate-toward-zero，余数符号 = 被除数符号
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
if (src2 == 8'd0) {
  rd[rdHB] = {{56{src1[7]}}, src1};
} else if (src1 == 8'b1000_0000 && src2 == 8'b1111_1111) {
  rd[rdHB] = 64'd0;
} else {
  Bits<8> rem = $signed(src1) % $signed(src2);
  rd[rdHB] = {{56{rem[7]}}, rem};
}
```
<!-- IDL:rem.sb_orrr_rd END -->

<!-- IDL:rem.ub_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: rem.ub_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位无符号余（SimRISC-10 §1.3）：除数为零走定值表（SimRISC-04 §1.4，不触发异常）
# ⇒ 被除数零扩展写满 64 位；无符号无溢出档
Bits<8> src1 = rd[rdHC][7:0];
Bits<8> src2 = rd[rdHD][7:0];
if (src2 == 8'd0) {
  rd[rdHB] = {56'd0, src1};
} else {
  Bits<8> rem = src1 % src2;
  rd[rdHB] = {56'd0, rem};
}
```
<!-- IDL:rem.ub_orrr_rd END -->

## 2. Bit manipulating：位操作指令 — 值语义

OPC-byte 子表中的 `shl.b`/`rol.b`/`shr.ub`/`shr.sb` 提供 8 位移位/循环移位操作。`shr` 分 `u`（逻辑）/`s`（算术）变体；`shl`/`rol` 符号无关、不带 `u`/`s` 后缀。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

**值语义**：所有移位结果写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。

移位语义见 SimRISC-04。其中 N=7。

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.b`/`rol.b`/`shr.sb`/`shr.ub` | 7 | 0-7 | `orrr`：`rdHD[2:0]`（高位忽略）；`orri`：`immu6[2:0]` |

运算公式：
```
shl.b:  rdHB[7:0]   = (rdHC[7:0] << shamt),   rdHB[63:8]  = 0
rol.b:  rdHB[7:0]   = rol(rdHC[7:0], shamt),  rdHB[63:8]  = 0
shr.ub:  rdHB[7:0]   = (rdHC[7:0] >> shamt),   rdHB[63:8]  = 0
shr.sb:  rdHB[7:0]   = (rdHC[7:0] >> shamt) with sign(7),  rdHB[63:8] = sign_extend(rdHC[7])
```

**立即数形式** `immu6 > N` 触发 ILLI；**寄存器形式**取 `rdHD[N:0]` 的低位（高位忽略，不抛 ILLI）。

**注**：`ext.ub`/`ext.sb`（8位符号/零扩展）已从指令集中删除。64位扩展见 SimRISC-04。

> **注**：rd0 目的寄存器约定见 SimRISC-00。

<!-- IDL:shl.b_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: shl.b_orri_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > N=7 ⇒ ILLI（SimRISC-10 §2；附录 B encode_sbz = immu6[5:3] 须为 0）
if (immu6 > 6'd7) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位左移（§2 公式）：shamt = immu6[2:0]，块内左移、移出位丢弃，结果零扩展写满 64 位
Bits<3> shamt = immu6[2:0];
Bits<8> res = rd[rdHC][7:0] << shamt;
rd[rdHB] = {56'd0, res};
```
<!-- IDL:shl.b_orri_rd END -->

<!-- IDL:shl.b_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: shl.b_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][2:0]（取 rdHD 所指寄存器的低 3 位；高位忽略、不抛 ILLI，§2）；
# 8 位左移、移出位丢弃，结果零扩展写满 64 位
Bits<3> shamt = rd[rdHD][2:0];
Bits<8> res = rd[rdHC][7:0] << shamt;
rd[rdHB] = {56'd0, res};
```
<!-- IDL:shl.b_orrr_rd END -->

<!-- IDL:shr.ub_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: shr.ub_orri_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > N=7 ⇒ ILLI（SimRISC-10 §2；附录 B encode_sbz = immu6[5:3] 须为 0）
if (immu6 > 6'd7) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位逻辑右移（§2 公式）：shamt = immu6[2:0]，高位补 0，结果零扩展写满 64 位
Bits<3> shamt = immu6[2:0];
Bits<8> res = rd[rdHC][7:0] >> shamt;
rd[rdHB] = {56'd0, res};
```
<!-- IDL:shr.ub_orri_rd END -->

<!-- IDL:shr.ub_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: shr.ub_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][2:0]（取 rdHD 所指寄存器的低 3 位；高位忽略、不抛 ILLI，§2）；
# 8 位逻辑右移、高位补 0，结果零扩展写满 64 位
Bits<3> shamt = rd[rdHD][2:0];
Bits<8> res = rd[rdHC][7:0] >> shamt;
rd[rdHB] = {56'd0, res};
```
<!-- IDL:shr.ub_orrr_rd END -->

<!-- IDL:shr.sb_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: shr.sb_orri_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > N=7 ⇒ ILLI（SimRISC-10 §2；附录 B encode_sbz = immu6[5:3] 须为 0）
if (immu6 > 6'd7) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位算术右移（§2 公式）：shamt = immu6[2:0]；块内右移、高位补 rd[rdHC][7]，
# 目的[63:8] = 符号扩展 rd[rdHC][7] ⇒ {56{val[7]}}（shamt 移满时结果全为符号位）
Bits<8> val = rd[rdHC][7:0];
Bits<3> shamt = immu6[2:0];
Bits<8> res = $signed(val) >>> shamt;
rd[rdHB] = {{56{val[7]}}, res};
```
<!-- IDL:shr.sb_orri_rd END -->

<!-- IDL:shr.sb_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: shr.sb_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][2:0]（取 rdHD 所指寄存器的低 3 位；高位忽略、不抛 ILLI，§2）；
# 8 位算术右移、高位补 rd[rdHC][7]，目的[63:8] = 符号扩展 rd[rdHC][7]（同 orri 形式的算式）
Bits<8> val = rd[rdHC][7:0];
Bits<3> shamt = rd[rdHD][2:0];
Bits<8> res = $signed(val) >>> shamt;
rd[rdHB] = {{56{val[7]}}, res};
```
<!-- IDL:shr.sb_orrr_rd END -->

### 2.1 逐块反转 rev.b（orri 格式）

`rev.b` 对 64 位源寄存器**按 8 位块逐块反转**：每块（S = 8）按 `k` 位切成
`8/k` 个单元，反转单元顺序（单元内部位序不变），八个块一律同样处理。
操作数格式 `orri`：`rev.b rdHB, rdHC, immu6`。

- 合法 `k` = `{1,2,4}`（one-hot 且 `k < S = 8`）；非 one-hot 或 `k ≥ 8`（含 `k = 8` 恒等档）触发 **ILLI**（规则 `encode_onehot`）。
- `rev.b` 无 `bswap` 对应档（`k=8` 即恒等，**非法**）；`k=1` 只反转**块内**位序，**不是** 64 位整体位反序。
- 逐块反转的总述与伪代码见 SimRISC-04。

<!-- IDL:rev.b_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: rev.b_orri_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# k 须 one-hot 且 k < S=8（附录 B encode_onehot；k=8 恒等档非法）⇒ 否则 ILLI
if (immu6 != 6'd1 && immu6 != 6'd2 && immu6 != 6'd4) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 逐块反转（SimRISC-10 §2.1）：整 64 位源按 8 位块切分，每块按 k 位切成 8/k 个单元，
# 反转单元顺序、单元内部位序不变，八个块同法处理（k=1 只反转块内位序，不是 64 位整体反序）。
# 等价写法：块内按距离 1/2/4 依次交换单元（k=4 只做距离 4、k=2 做 2 与 4、k=1 三步全做）；
# 掩码按字节重复 ⇒ 交换不跨块。
Bits<64> x = rd[rdHC];
if (immu6 == 6'd1) {
  x = ((x & 64'hAAAA_AAAA_AAAA_AAAA) >> 1) | ((x & 64'h5555_5555_5555_5555) << 1);
}
if (immu6 == 6'd1 || immu6 == 6'd2) {
  x = ((x & 64'hCCCC_CCCC_CCCC_CCCC) >> 2) | ((x & 64'h3333_3333_3333_3333) << 2);
}
x = ((x & 64'hF0F0_F0F0_F0F0_F0F0) >> 4) | ((x & 64'h0F0F_0F0F_0F0F_0F0F) << 4);
rd[rdHB] = x;
```
<!-- IDL:rev.b_orri_rd END -->

### 2.2 逻辑循环左移 rol.b（`orrr` / `orri` 格式）

`rol.b` 对源寄存器的 **低 8 位**做逻辑循环左移：`rdHB[7:0] = rol(rdHC[7:0], amount)`；
结果按值语义零扩展写满 64 位（`rdHB[63:8] = 0`）。符号无关、只有一个方向、不带 `u`/`s`
。

| 格式 | 旋转量 `amount` | 取值 |
|------|----------------|------|
| `orrr` | `rdHD[2:0]` | `0..7`（即对 8 取模） |
| `orri` | `immu6` | `0..7`；`immu6 > 7` ⇒ **ILLI** |

- `orrr` 的 `rdHD` 只有低 3 位参与（天然取模 8）；`orri` 的 `immu6` 是 6 位，**越界（`8..63`）触发 ILLI**（与 `shl.b` 的 `immu6 <= 7` 同口径）。
- 目的 `rdHB` 为 `rd0` ⇒ **ILLI**（规则 `dst_rd0`）；源 `rdHC` 可为 `rd0`（结果恒为 0）；`rdHB == rdHC` 允许。
- 格式：`orrr`（寄存器旋转量）/ `orri`（立即数旋转量），属 `OPC-byte` 子表。
- 64 位语义与总述见 SimRISC-04。

```simrisc
rol.b   rdHB, rdHC, rdHD        @@ 8 位循环左移（旋转量 = rdHD[2:0]）
rol.b   rdHB, rdHC, immu6       @@ 8 位循环左移（immu6 0..7）
```

<!-- IDL:rol.b_orri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: rol.b_orri_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 立即数形式：immu6 > 7 ⇒ ILLI（SimRISC-10 §2.2；附录 B encode_sbz = immu6[5:3] 须为 0）
if (immu6 > 6'd7) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 8 位逻辑循环左移（§2.2）：shamt = immu6[2:0]，只一个方向，结果零扩展写满 64 位。
# 按位等价式：val 左移 s 位 与 val 右移 8-s 位 按位或；写成 {val,val} 右移 8-s 后取低 8 位，
# 使 s=0 时右移量 8 落在 16 位宽内（不出现对 8 位值右移 8 位）
Bits<8> val = rd[rdHC][7:0];
Bits<3> shamt = immu6[2:0];
Bits<16> dup = {2{val}};
Bits<16> shifted = dup >> (8 - shamt);
Bits<8> res = shifted[7:0];
rd[rdHB] = {56'd0, res};
```
<!-- IDL:rol.b_orri_rd END -->

<!-- IDL:rol.b_orrr_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: rol.b_orrr_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHB == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 寄存器形式：shamt = rd[rdHD][2:0]（取 rdHD 所指寄存器的低 3 位；天然对 8 取模，高位忽略不抛 ILLI，§2.2）；
# 8 位逻辑循环左移、只一个方向，结果零扩展写满 64 位（同 orri 形式的算式）
Bits<8> val = rd[rdHC][7:0];
Bits<3> shamt = rd[rdHD][2:0];
Bits<16> dup = {2{val}};
Bits<16> shifted = dup >> (8 - shamt);
Bits<8> res = shifted[7:0];
rd[rdHB] = {56'd0, res};
```
<!-- IDL:rol.b_orrr_rd END -->

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

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
| `rol.b` | `orri` | `rd` | `rol.b rdHB, rdHC, immu6` | `rol.b_orri_rd` |
| `rol.b` | `orrr` | `rd` | `rol.b rdHB, rdHC, rdHD` | `rol.b_orrr_rd` |
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
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.sb_orrr_rd`, `add.ub_orrr_rd`, `cmp.sb_orrr_rd`, `cmp.ub_orrr_rd`, `div.sb_orrr_rd`, `div.ub_orrr_rd`, `mul.sb_orrr_rd`, `mul.ub_orrr_rd`, `rem.sb_orrr_rd`, `rem.ub_orrr_rd`, `rev.b_orri_rd`, `rol.b_orri_rd`, `rol.b_orrr_rd`, `shl.b_orri_rd`, `shl.b_orrr_rd`, `shr.sb_orri_rd`, `shr.sb_orrr_rd`, `shr.ub_orri_rd`, `shr.ub_orrr_rd`, `sub.sb_orrr_rd`, `sub.ub_orrr_rd`（21 条）
* `encode_sbz`：SBZ 非零 → ILLI — `rol.b_orri_rd`, `shl.b_orri_rd`, `shr.sb_orri_rd`, `shr.ub_orri_rd`（4 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `rev.b_orri_rd`（1 条）
<!-- LEGALITY_END -->
