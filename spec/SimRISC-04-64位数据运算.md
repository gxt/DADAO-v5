# SimRISC64位数据运算指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：64位数据运算** — .so/.uo + add.si/cmp.si/cmp.ui + and.o/or.o/xor.o/xnor.o + rev.o（逐块反转）+ ctlz/cttz/ctpop（位扫描/位计数）+ shl.o/rol.o（移位/循环移位）+ clmul.o（无进位乘）

## 1. 算术运算类指令

### 1.1 加减操作

加减操作需要两个源操作数，一个目的操作数。
操作数类型为 `rrrr`。
两个源操作数寄存器为`rdHC`和`rdHD`。
目的操作数可能超出64位，故采用两个寄存器存放目的操作数，即`rdHA`和`rdHB`，`rdHA`存放结果的高64位，`rdHB`存放结果的低64位。
硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

根据操作数的符号类型，`add`/`sub` 分为两个变体：

- **`add.uo`/`sub.uo`**（无符号）：源操作数按**零扩展**（ZX）至 128 位，适合无符号多字加法链，`rdHA` 为进位/借位（0 或 1）。
- **`add.so`/`sub.so`**（有符号，默认）：源操作数按**符号扩展**（SX）至 128 位，适合有符号 128 位运算。

```simrisc
add.uo  {rdHA, rdHB}, rdHC, rdHD    @@ ZX，rdHA = 进位
add.so  {rdHA, rdHB}, rdHC, rdHD    @@ SX，rdHA = 高64位
sub.uo  {rdHA, rdHB}, rdHC, rdHD    @@ ZX，rdHA = 借位
sub.so  {rdHA, rdHB}, rdHC, rdHD    @@ SX，rdHA = 高64位
```

`rdHA` 和 `rdHB` 均可为 `rd0`（丢弃对应部分的结果），但不能**同时**为 `rd0`，也不能为同一非 `rd0` 寄存器。违反上述任一规则触发 ILLI 异常。

### 1.2 自增自减

自增自减指令需要一个寄存器和一个立即数，操作数类型为 `riii`。
立即数为18位有符号数，经过符号扩展后与寄存器执行加法，结果写回同一寄存器。
由于立即数采用补码的编码方式，无需区分加减操作。
具体指令如下：

```simrisc
add.si  rdHA, imms18
```

`add.si` 为全 64 位运算，无法单独通过结果判断溢出，用户可结合 `add.uo`/`add.so` 的 rrrr 形式获取进位/符号信息。

### 1.3 比较操作

比较操作需要通过指令编码区分数据类型，对于整型，主要区分的是有符号数和无符号数。
比较操作会根据两个源操作数的比较结果，小于、等于、大于，分别设置目的操作数为-1、0、1。
后续的指令可以根据负数、非负数、零、非零、正数、非正数做出组合判断。

操作数类型为 `rrii`。
具体指令如下：

```simrisc
cmp.si  rdHA, rdHB, imms12
cmp.ui  rdHA, rdHB, immu12
```

orrr 形式的比较指令（cmp.uo/cmp.so）如下：

```simrisc
cmp.uo  rdHB, rdHC, rdHD
cmp.so  rdHB, rdHC, rdHD
```

源操作数按 size 截断后比较，结果（-1/0/1）写入目的寄存器全 64 位。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

### 1.4 乘除操作

乘除运算都是四个操作数，操作数类型为 `rrrr`。

无符号数的乘法 `mul.uo` 和有符号数的乘法 `mul.so`，rdHC和rdHD为源操作数，形成16字节的运算结果，分别写入rdHA和rdHB中，rdHA存放结果的高64位，rdHB存放结果的低64位。硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

```simrisc
mul.so  {rdHA, rdHB}, rdHC, rdHD
mul.uo  {rdHA, rdHB}, rdHC, rdHD
```

`rdHA` 和 `rdHB` 均可为 `rd0`（丢弃对应部分的结果），但不能**同时**为 `rd0`，也不能为同一非 `rd0` 寄存器。违反上述任一规则触发 ILLI 异常。

64 位除余指令（orrr 格式）如下：

```simrisc
div.uo  rdHB, rdHC, rdHD
div.so  rdHB, rdHC, rdHD
rem.uo  rdHB, rdHC, rdHD
rem.so  rdHB, rdHC, rdHD
```

源操作数只取 size 范围内的低位，结果仅保留 size 位宽，高位按有符号（符号扩展）或无符号（零扩展）填充。操作数格式为 `orrr`，`rdHB` 不能为 `rd0`，否则触发 ILLI 异常。

除法指令附加规则（适用于 `div.s`/`div.u`/`rem.s`/`rem.u` 全部格式）：

- **除数为零 → 定值**（不触发异常）：见下方定值表。
- **截断方向**：`div.s`/`rem.s` 采用 truncate-toward-zero（C99 标准），余数符号 = 被除数符号。
- **溢出 → 定值**（不触发异常）：`div.s` 中各 size 对应的 INT_MIN ÷ −1 见下方定值表；`div.u`/`rem.u` 不存在溢出。
- **定值表**（按运算宽度取值，有符号变体符号扩展写满 64 位 / 无符号变体零扩展）：

| 指令 | 除零 ⇒ `rdHB` | 有符号溢出（INT_MIN ÷ −1）⇒ `rdHB` |
|------|---------------|--------------------------------------|
| `div.sb` | `0xFFFF_FFFF_FFFF_FFFF` | `0xFFFF_FFFF_FFFF_FF80` |
| `div.ub` | `0x0000_0000_0000_00FF` | 不适用 |
| `div.sw` | `0xFFFF_FFFF_FFFF_FFFF` | `0xFFFF_FFFF_FFFF_8000` |
| `div.uw` | `0x0000_0000_0000_FFFF` | 不适用 |
| `div.st` | `0xFFFF_FFFF_FFFF_FFFF` | `0xFFFF_FFFF_8000_0000` |
| `div.ut` | `0x0000_0000_FFFF_FFFF` | 不适用 |
| `div.so` | `0xFFFF_FFFF_FFFF_FFFF` | `0x8000_0000_0000_0000` |
| `div.uo` | `0xFFFF_FFFF_FFFF_FFFF` | 不适用 |
| `rem.sb`/`rem.sw`/`rem.st`/`rem.so` | 被除数（符号扩展写满 64 位） | `0` |
| `rem.ub`/`rem.uw`/`rem.ut`/`rem.uo` | 被除数（零扩展写满 64 位） | 不适用 |

### 1.5 无进位乘法

无进位乘法（carry-less multiplication，GF(2) 多项式乘）操作数类型为 `rrrr`，与 `mul.*` 同型：`rdHC`、`rdHD` 为源操作数，结果 128 位写入 `rdHA`（高 64 位）与 `rdHB`（低 64 位）。硬件先读全部源操作数再写结果，源被覆盖前其值已捕获，行为确定。

```simrisc
clmul.o  {rdHA, rdHB}, rdHC, rdHD
```

语义：把 `rdHC`、`rdHD` 各视为 64 位系数多项式（bit *i* = x^*i* 的系数），在 GF(2) 上相乘——每一位的贡献是「与」、各位结果之间是「异或」，**位间无进位**。例：`0b11 × 0b11` 在 GF(2) 上 = (x+1)² = x²+1 = `0b101`（= 5），而整数 `mul.uo` 得 9。

与 `mul.uo`/`mul.so` 的区别：操作数形状与双目的布局完全相同，但**不进位**、**无符号**（纯位运算，不设 `.u`/`.s` 变体），且**只有 `.o` 宽度**——无进位 ⇒ 窄宽度结果只是 64 位结果的低位子集，由结果掩码取得，故不设 `.t`/`.w`/`.b`。

`rdHA` 和 `rdHB` 均可为 `rd0`（丢弃对应部分的结果），但不能**同时**为 `rd0`，也不能为同一非 `rd0` 寄存器。违反上述任一规则触发 ILLI 异常。

单取高半或低半写 `{rdH, rd0}` / `{rd0, rdL}`（与 `mul.uo {rdH, rd0}` 取 `mulhu` 同型）；「反向」无进位乘 `clmulr(a, b) = rev(clmul(rev(a), rev(b)))` 用 `rev.o` 组合，不单设指令。

## 2. 逻辑运算类指令

### 2.1 Logic operators：逻辑运算

逻辑运算指令需要两个源操作数，一个目的操作数。OPC-octa 子表中的 `and`/`or`/`xor`/`xnor`（后缀 `.o`）提供 64 位逻辑运算。操作数格式为 `orrr`。

| 指令 | 位宽 | 汇编语法 | 操作范围 |
|------|------|---------|---------|
| `and.o`/`or.o`/`xor.o`/`xnor.o` | 64 位 | `and.o rdHB, rdHC, rdHD` | bits[63:0] 全 64 位参与运算 |

`and` 指令为逻辑与运算，运算规则：全一为一，有零为零。即只有两个操作数都为1时，结果才为1，其他情况均为0；也可以说，只要有0，结果就为0。
`or` 指令为逻辑或运算，运算规则：全零为零，有一为一。即只有两个操作数都为0时，结果才为0，其他情况均为1；也可以说，只要有1，结果就为1。
`xor` 指令为逻辑异或运算，运算规则：相异为一，相同为零。即两个操作数不一样时结果为1，两个操作数相同时结果为0。
`xnor` 指令为逻辑同或运算，运算规则：相同为一，相异为零。与异或运算规则相反。即两个操作数值相同时结果为1，两个操作数不一样时为0。

无需提供专门的not指令，可以采用xnor指令实现相同的功能。当rdHC或rdHD为rd0时，xnor指令实现了另一操作数的取反操作，即逻辑非运算。逻辑非的运算规则：一变零，零变一。即操作数为1时结果为0，操作数为0时结果为1。

### 2.2 Bit manipulating：位操作指令

移位/扩展指令需要两个源操作数，一个目的操作数。

位扫描与位计数（`ctlz`/`cttz`/`ctpop`）不属于移位/扩展语义，见 SimRISC-12 位扫描与位计数。

`shl` 是左移，`shr` 是右移，`rol` 是逻辑循环左移。`shr` 后缀中的 `s` 表示算术移位（符号扩展）、`u` 表示逻辑移位（零扩展）；`shl`/`rol` **符号无关**，不带 `u`/`s` 后缀。OPC-octa 子表中的 `shl.o`/`rol.o`/`shr.uo`/`shr.so` 提供 64 位移位/循环移位操作。移位量（shamt）取 `rdHD` 的低位（寄存器形式，`orrr`）或 `immu6` 的低位（立即数形式，`orri`）。

```
shl.o: rdHB[N:0]   = (rdHC[N:0] << shamt)                // 左移，低位补零
shr.u: rdHB[N:0]   = (rdHC[N:0] >> shamt)                // 逻辑右移，高位补零
shr.s: rdHB[N:0]   = (rdHC[N:0] >> shamt) with sign(N)   // 算术右移，高位补 rdHC[N]
rol.o: rdHB[N:0]   = rol(rdHC[N:0], shamt)               // 逻辑循环左移，位串旋转
```

**值语义通则**：所有移位/比较指令的结果均写满64位（零扩展或符号扩展），此前的「高位保留」语义已被值语义取代。64 位操作 N=63 自然写满；32/16/8 位操作的高位扩展规则见 SimRISC-08/09/10。

其中 N 由位宽决定。shamt 和 N 的对应关系如下：

| 指令 | N | 有效 shamt 范围 | shamt 位域 |
|------|---|----------------|-----------|
| `shl.o`/`rol.o`/`shr.so`/`shr.uo` | 63 | 0-63 | hd[5:0] 全有效 |

`shamt > N` 触发 ILLI。

`ext.s` 是符号扩展，`ext.u` 是零扩展。OPC-octa 子表中的 `ext.s`/`ext.u`（后缀 `.so`/`.uo`）提供 64 位扩展操作。操作数格式为 `orrr`（寄存器形式，hd=扩展起始位）和 `orri`（立即数形式，hd=immu6 扩展起始位）。语义如下：

```
rdHB[hd:0]   = rdHC[hd:0]                               // 复制源低位
rdHB[63:hd+1] = sign/zero_extend(rdHC[hd])               // 符号/零扩展（N=63，自然写满64位）
```

> **注**：64位 ext（N=63）自然写满64位。

其中 N 由位宽决定（octa→63），hd 为扩展起始位，须满足 `hd ≤ N`，否则 ILLI。

| 指令 | N | 汇编语法 | 约束 |
|------|---|---------|------|
| `ext.uo`/`ext.so` | 63 | `ext.uo rdHB, rdHC, rdHD` 或 `ext.uo rdHB, rdHC, immu6` | hd ≤ 63 |

64 位移位/扩展指令如下：

```simrisc
shl.o   rdHB, rdHC, rdHD        @@ 左移
shl.o   rdHB, rdHC, immu6       @@ 左移（立即数）
rol.o   rdHB, rdHC, rdHD        @@ 逻辑循环左移
rol.o   rdHB, rdHC, immu6       @@ 逻辑循环左移（立即数）
shr.uo  rdHB, rdHC, rdHD        @@ 逻辑右移
shr.uo  rdHB, rdHC, immu6       @@ 逻辑右移（立即数）
shr.so  rdHB, rdHC, rdHD        @@ 算术右移
shr.so  rdHB, rdHC, immu6       @@ 算术右移（立即数）

ext.uo  rdHB, rdHC, rdHD        @@ 零扩展
ext.uo  rdHB, rdHC, immu6       @@ 零扩展（立即数）
ext.so  rdHB, rdHC, rdHD        @@ 符号扩展
ext.so  rdHB, rdHC, immu6       @@ 符号扩展（立即数）

and.o   rdHB, rdHC, rdHD        @@ 逻辑与
or.o    rdHB, rdHC, rdHD        @@ 逻辑或
xor.o   rdHB, rdHC, rdHD        @@ 逻辑异或
xnor.o  rdHB, rdHC, rdHD        @@ 逻辑同或
```

#### 2.2.1 逐块反转 rev.o/rev.t/rev.w/rev.b（orri 格式）

`rev` 提供**逐块反转**能力，指令名后缀决定块大小 `S`：把 64 位源寄存器切成 `64/S`
个块，每块内部再按 `k` 位切分成 `S/k` 个**单元**，然后**反转单元顺序**
（单元内部位序不变）；**所有块一律同样处理**，不存在"块外更高位保持"或"清零"的例外。

| 指令 | 后缀 | 块大小 S | 块数 64/S | 合法 k（one-hot 且 k < S） |
|------|------|---------|----------|---------------------------|
| `rev.o` | octa | 64 | 1 | 1, 2, 4, 8, 16, 32 |
| `rev.t` | tetra | 32 | 2 | 1, 2, 4, 8, 16 |
| `rev.w` | wyde | 16 | 4 | 1, 2, 4, 8 |
| `rev.b` | byte | 8 | 8 | 1, 2, 4 |

操作数格式为 `orri`：`rev.X rdHB, rdHC, immu6`（目的 `rdHB`、源 `rdHC`、立即数 `k`）。
`rdHB` 的**全部 64 位**都是 `rdHC` 的逐块反转结果。

```
for i in 0 .. (64/S - 1):
    units = 把 in_block[i] 切成 S/k 个 k 位单元
    out_block[i] = 把 units 按下标倒序拼接
rdHB = out_block[0] .. out_block[64/S - 1]
```

例（`.w` + `k=4`）：每个 16 位块切成 4 个 4 位单元并翻转单元顺序；
故 `rdHC[63:16] == 0` 时 `rdHB[63:16] == 0`。

`k` 须为 **one-hot（2 的幂）且 `k < S`**（排除 `k = S` 恒等档）；非 one-hot
（`0`/`3`/`5`/`6`/…/`63`）或 `k ≥ S` 触发 **ILLI**（规则 `encode_onehot`）。
`rdHC` 允许为 `rd0`（读出 0）；`rdHB` 允许与 `rdHC` 相同（原地反转）；
`rdHB` 为目的，不得为 `rd0`（规则 `dst_rd0`）。

用途映射（供后端参考）：

- `bswap64`/`bswap32`/`bswap16` = `rev.o`/`rev.t`/`rev.w` + `k=8`；**前提**是源的
  高 `64 − S` 位为 0（否则其余块也会被逐字节反转）。
- `bitreverse`（64 位整体位反序）= `rev.o` + `k=1`。**注意**：`rev.t`/`rev.w` + `k=1`
  **不是** 64 位整体位反序，只反转各块内部的位序，不可误用。

```simrisc
rev.o   rdHB, rdHC, immu6       @@ 64 位逐块反转（k=8 → bswap64；k=1 → bitreverse）
rev.t   rdHB, rdHC, immu6       @@ 32 位块内反转（k=8 → bswap32，须源高 32 位为 0）
rev.w   rdHB, rdHC, immu6       @@ 16 位块内反转（k=8 → bswap16，须源高 48 位为 0）
rev.b   rdHB, rdHC, immu6       @@ 8 位块内反转（k ∈ {1,2,4}）
```

`rev.t`/`rev.w`/`rev.b` 的分册语义见 SimRISC-08/09/10；本节为逐块反转的总述。

#### 2.2.2 逻辑循环左移 rol.o（`orrr` / `orri` 格式）

`rol.o` 提供 **64 位逻辑循环左移**（把寄存器当作 64 位位串循环旋转）：
`rdHB[63:0] = rol(rdHC[63:0], amount)`。**只有一个方向**（左），**不分有符号/无符号**，
因此**不带 `u`/`s` 后缀**。

| 格式 | 旋转量 `amount` | 取值 |
|------|----------------|------|
| `orrr` | `rdHD[5:0]`（源寄存器低位） | `0..63`（即对 64 取模） |
| `orri` | `immu6` | `0..63`（全部合法） |

```
rol(x, n) = (x << n) | (x >> ((64 - n) & 63))     // n = 0 时结果为 x 本身
rdHB[63:0] = rol(rdHC[63:0], amount)
```

- **值语义**：结果写满 64 位；不存在「高位保留」。
- **旋转量取模（仅寄存器形态）**：`orrr` 的 `rdHD` 只有低 6 位参与，天然等价于 `amount mod 64`。
  `orri` 的 `immu6` 为 6 位，`0..63` 全部合法；**无越界值**（`immu6` 装不下 `≥64`）。
- **合法性**：目的 `rdHB` 为 `rd0` ⇒ **ILLI**（规则 `dst_rd0`）；源 `rdHC` 可为 `rd0`（读出 0，
  结果恒为 0）；`rdHB == rdHC` 允许（原地旋转）。
- **不另设反向指令**：`rol(x, (64 - n) mod 64)` 即反向旋转 ⇒ 一个方向足以表达双向。
- **格式**：`orrr`（寄存器旋转量）/ `orri`（立即数旋转量），属 `OPC-octa` 子表（见 SimRISC-00）。
- `rol.t`/`rol.w`/`rol.b` 的位宽/取模/越界口径分别见 SimRISC-08/09/10。

```simrisc
rol.o   rdHB, rdHC, rdHD        @@ 循环左移（旋转量 = rdHD[5:0]）
rol.o   rdHB, rdHC, immu6       @@ 循环左移（旋转量 = immu6，0..63）
```

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `add.si` | `riii` | `rd` | `add.si rdHA, imms18` | `add.si_riii_rd` |
| `add.so` | `rrrr` | `rd` | `add.so {rdHA, rdHB}, rdHC, rdHD` | `add.so_rrrr_rd` |
| `add.uo` | `rrrr` | `rd` | `add.uo {rdHA, rdHB}, rdHC, rdHD` | `add.uo_rrrr_rd` |
| `and.o` | `orrr` | `rd` | `and.o rdHB, rdHC, rdHD` | `and.o_orrr_rd` |
| `clmul.o` | `rrrr` | `rd` | `clmul.o {rdHA, rdHB}, rdHC, rdHD` | `clmul.o_rrrr_rd` |
| `cmp.si` | `rrii` | `rd` | `cmp.si rdHA, rdHB, imms12` | `cmp.si_rrii_rd` |
| `cmp.so` | `orrr` | `rd` | `cmp.so rdHB, rdHC, rdHD` | `cmp.so_orrr_rd` |
| `cmp.ui` | `rrii` | `rd` | `cmp.ui rdHA, rdHB, immu12` | `cmp.ui_rrii_rd` |
| `cmp.uo` | `orrr` | `rd` | `cmp.uo rdHB, rdHC, rdHD` | `cmp.uo_orrr_rd` |
| `div.so` | `orrr` | `rd` | `div.so rdHB, rdHC, rdHD` | `div.so_orrr_rd` |
| `div.uo` | `orrr` | `rd` | `div.uo rdHB, rdHC, rdHD` | `div.uo_orrr_rd` |
| `ext.so` | `orri` | `rd` | `ext.so rdHB, rdHC, immu6` | `ext.so_orri_rd` |
| `ext.so` | `orrr` | `rd` | `ext.so rdHB, rdHC, rdHD` | `ext.so_orrr_rd` |
| `ext.uo` | `orri` | `rd` | `ext.uo rdHB, rdHC, immu6` | `ext.uo_orri_rd` |
| `ext.uo` | `orrr` | `rd` | `ext.uo rdHB, rdHC, rdHD` | `ext.uo_orrr_rd` |
| `mul.so` | `rrrr` | `rd` | `mul.so {rdHA, rdHB}, rdHC, rdHD` | `mul.so_rrrr_rd` |
| `mul.uo` | `rrrr` | `rd` | `mul.uo {rdHA, rdHB}, rdHC, rdHD` | `mul.uo_rrrr_rd` |
| `or.o` | `orrr` | `rd` | `or.o rdHB, rdHC, rdHD` | `or.o_orrr_rd` |
| `rem.so` | `orrr` | `rd` | `rem.so rdHB, rdHC, rdHD` | `rem.so_orrr_rd` |
| `rem.uo` | `orrr` | `rd` | `rem.uo rdHB, rdHC, rdHD` | `rem.uo_orrr_rd` |
| `rev.o` | `orri` | `rd` | `rev.o rdHB, rdHC, immu6` | `rev.o_orri_rd` |
| `rol.o` | `orri` | `rd` | `rol.o rdHB, rdHC, immu6` | `rol.o_orri_rd` |
| `rol.o` | `orrr` | `rd` | `rol.o rdHB, rdHC, rdHD` | `rol.o_orrr_rd` |
| `shl.o` | `orri` | `rd` | `shl.o rdHB, rdHC, immu6` | `shl.o_orri_rd` |
| `shl.o` | `orrr` | `rd` | `shl.o rdHB, rdHC, rdHD` | `shl.o_orrr_rd` |
| `shr.so` | `orri` | `rd` | `shr.so rdHB, rdHC, immu6` | `shr.so_orri_rd` |
| `shr.so` | `orrr` | `rd` | `shr.so rdHB, rdHC, rdHD` | `shr.so_orrr_rd` |
| `shr.uo` | `orri` | `rd` | `shr.uo rdHB, rdHC, immu6` | `shr.uo_orri_rd` |
| `shr.uo` | `orrr` | `rd` | `shr.uo rdHB, rdHC, rdHD` | `shr.uo_orrr_rd` |
| `sub.so` | `rrrr` | `rd` | `sub.so {rdHA, rdHB}, rdHC, rdHD` | `sub.so_rrrr_rd` |
| `sub.uo` | `rrrr` | `rd` | `sub.uo {rdHA, rdHB}, rdHC, rdHD` | `sub.uo_rrrr_rd` |
| `xnor.o` | `orrr` | `rd` | `xnor.o rdHB, rdHC, rdHD` | `xnor.o_orrr_rd` |
| `xor.o` | `orrr` | `rd` | `xor.o rdHB, rdHC, rdHD` | `xor.o_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `add.si_riii_rd`, `and.o_orrr_rd`, `cmp.si_rrii_rd`, `cmp.so_orrr_rd`, `cmp.ui_rrii_rd`, `cmp.uo_orrr_rd`, `div.so_orrr_rd`, `div.uo_orrr_rd`, `ext.so_orri_rd`, `ext.so_orrr_rd`, `ext.uo_orri_rd`, `ext.uo_orrr_rd`, `or.o_orrr_rd`, `rem.so_orrr_rd`, `rem.uo_orrr_rd`, `rev.o_orri_rd`, `rol.o_orri_rd`, `rol.o_orrr_rd`, `shl.o_orri_rd`, `shl.o_orrr_rd`, `shr.so_orri_rd`, `shr.so_orrr_rd`, `shr.uo_orri_rd`, `shr.uo_orrr_rd`, `xnor.o_orrr_rd`, `xor.o_orrr_rd`（26 条）
* `dst_dual_same`：双目的同为 rd0 或同寄存器 → ILLI — `add.so_rrrr_rd`, `add.uo_rrrr_rd`, `clmul.o_rrrr_rd`, `mul.so_rrrr_rd`, `mul.uo_rrrr_rd`, `sub.so_rrrr_rd`, `sub.uo_rrrr_rd`（7 条）
* `encode_onehot`：immu6 非 one-hot 或 ≥ S → ILLI — `rev.o_orri_rd`（1 条）
<!-- LEGALITY_END -->
