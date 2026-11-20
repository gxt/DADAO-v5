# SimRISC取数存数指令

> **版本：0.5.7-rc**（与 SimRISC-00 一致）
> **分类：取数存数** — ld/st/ldm/stm（RD/RB/RA/RF 各形式）

用户态指令

装入指令是把数据从存储器带进寄存器中，进行零扩展或符号扩展。存储指令是把寄存器中的数据放入存储器中。

操作数类型有两种，一种为：`rrii`，属于单load/store类型，地址计算公式为基址寄存器 + 立即数。
另一种操作数类型为：`rrri`，属于多load/store类型，地址计算公式为基址寄存器 + 数据寄存器。

## 1. 存取RD寄存器

单load/store类指令如下：

```simrisc
ld.sb    rdHA, [rbHB, imms12]
ld.ub    rdHA, [rbHB, imms12]
ld.sw    rdHA, [rbHB, imms12]
ld.uw    rdHA, [rbHB, imms12]
ld.st    rdHA, [rbHB, imms12]
ld.ut    rdHA, [rbHB, imms12]
ld.o     rdHA, [rbHB, imms12]

st.b     rdHA, [rbHB, imms12]
st.w     rdHA, [rbHB, imms12]
st.t     rdHA, [rbHB, imms12]
st.o     rdHA, [rbHB, imms12]
```

对齐要求：`ld.o`/`st.o` 需 8 字节对齐，`ld.st`/`st.t`/`ld.ut` 需 4 字节对齐，`ld.sw`/`st.w`/`ld.uw` 需 2 字节对齐，`ld.sb`/`st.b`/`ld.ub` 无对齐要求。未对齐触发 MALIGN 异常。

限制：`ld` 指令的 `rdHA` 为 `rd0` 时触发 ILLI 异常。（rd0 通用约定见 SimRISC-00）`st` 指令允许 `rdHA` 为 `rd0`（rd0 作为源寄存器读出 0）。

多load/store类指令如下：

```simrisc
ldm.sb   {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
ldm.ub   {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
ldm.sw   {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
ldm.uw   {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
ldm.st   {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
ldm.ut   {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
ldm.o    {rdHA:rdHA+immu6-1}, [rbHB, rdHC]

stm.b    {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
stm.w    {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
stm.t    {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
stm.o    {rdHA:rdHA+immu6-1}, [rbHB, rdHC]
```

`ldm/stm`指令处理多个寄存器的读写操作。
`rdHA`用来指定第一个寄存器，`[rbHB, rdHC]`用来指定地址，`immu6`为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。
`ldm/stm`指令存取8位/16位/32位的数据时，每个寄存器只存放一个数据，多个数据分别使用多个连续的寄存器。
例如：`stm.b {rd16:rd23}, [rb2, rd0]` 是将`rd16 - rd23`这8个连续寄存器中的低8位数据，分别存放到以rb2为基址的8字节连续地址中。

限制如下：

- `ldm` 指令的 `rdHA` 为 `rd0` 时触发 ILLI 异常；`stm` 指令允许 `rdHA` 为 `rd0`（rd0 作为源寄存器读出 0）
- `immu6` = 0 时触发 ILLI 异常
- `rdHA + immu6 > 64`（超出 rd63）时触发 ILLI 异常，不环绕、不截断
- `ldm.o`/`stm.o`（64-bit）需 8 字节地址对齐；`ldm.st`/`stm.t`/`ldm.ut`（32-bit）需 4 字节对齐；`ldm.sw`/`stm.w`/`ldm.uw`（16-bit）需 2 字节对齐；`ldm.sb`/`stm.b`/`ldm.ub`（8-bit）无对齐要求。未对齐将触发 MALIGN 异常
- **`ldm` 禁止索引寄存器落入传送范围**：RD 形式的传送范围在 RD 组、索引寄存器是同组的 `rdHC`；`rdHA <= rdHC < rdHA + immu6` 时触发 ILLI 异常（静态：在指令执行前判定，不产生任何元素的效果）。理由：`ldm` 逐元素写入传送范围内的寄存器，索引寄存器一旦被在先元素覆盖，后续元素的地址就取决于处理进度（与本节「部分生效」的中断点相关），结果不确定。
- **`stm` 允许索引寄存器落入传送范围**：`stm` 只读出传送范围内的寄存器、不写任何寄存器，地址全程由指令开始执行时的 `rdHC` 给出，与处理进度无关 ⇒ 行为确定，不触发异常。
- **基址寄存器不适用**：RD 形式的基址寄存器 `rbHB` 属于 RB 组，而传送范围在 RD 组，结构上不可能落入范围（RB 形式相反，见 §2）。

> **部分生效（不保证无副作用）**：§1–§4 的全部 `ldm`/`stm` 形式在处理多个元素时，若某个元素触发同步异常（如 `MALIGN`/`CFXMEM`/`CFXPERM`），**不保证**目的寄存器或内存未被修改——异常前已处理的元素可能已经生效，故这类指令**不是精确异常**；异常原因码仍须与触发元素一致，IP 仍指向该指令。实现可在执行前对全部元素做**整段预检**（任一检查失败即不产生副作用），表现为精确；这是**允许的更强行为**，软件**不得依赖**。
>
> **与部分生效相关的顺序约束**：地址寄存器凡与传送范围同组者，**不得**落入该范围（`ldm`，违反 ⇒ ILLI，见 §1/§2 的 `ldm` 禁令）；`stm` 不写寄存器、RA/RF 形式的地址寄存器与传送范围分属不同寄存器组（不被写入）⇒ 无论异常落在哪个元素，地址都不随已生效元素改变。（寄存器复制类块复制**不适用**本例外、保持精确，其源/目的重叠被禁止，见 SimRISC-02 与 DADAO-12 §5。）

### 1.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-01.idl` 生成，逐条如下：

<!-- IDL:ld.o_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.o_rrii_rd`**
```idl
# 目的 rd0 ⇒ ILLI（§1 限制：ld 的 rdHA 为 rd0；先于地址计算）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 64 位全宽计算
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(64, ea)) {          # .o 按数据宽度（8 字节）自然对齐
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

rd[rdHA] = read_memory(64, ea);               # 大端读：最低地址的字节是最高有效字节
```
<!-- IDL:ld.o_rrii_rd END -->

<!-- IDL:ld.sb_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.sb_rrii_rd`**
```idl
# 目的 rd0 ⇒ ILLI（§1 限制：ld 的 rdHA 为 rd0；先于地址计算）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# .sb 无对齐要求（§1 对齐要求）⇒ 不判 MALIGN；读 8 位后符号扩展至 64 位
# （s = 有符号、u = 无符号的指令名后缀约定见 SimRISC-00）
Bits<64> w = read_memory(8, ea);
Bits<8> v = w[7:0];
rd[rdHA] = {{56{v[7]}}, v};
```
<!-- IDL:ld.sb_rrii_rd END -->

<!-- IDL:ld.ub_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.ub_rrii_rd`**
```idl
# 目的 rd0 ⇒ ILLI（§1 限制：ld 的 rdHA 为 rd0；先于地址计算）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# .ub 无对齐要求（§1 对齐要求）⇒ 不判 MALIGN；零扩展由 read_memory 的 64 位零扩展给出
rd[rdHA] = read_memory(8, ea);
```
<!-- IDL:ld.ub_rrii_rd END -->

<!-- IDL:ld.sw_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.sw_rrii_rd`**
```idl
# 目的 rd0 ⇒ ILLI（§1 限制：ld 的 rdHA 为 rd0；先于地址计算）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(16, ea)) {          # .sw 需 2 字节对齐（§1 对齐要求）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 读 16 位后符号扩展至 64 位
Bits<64> w = read_memory(16, ea);
Bits<16> v = w[15:0];
rd[rdHA] = {{48{v[15]}}, v};
```
<!-- IDL:ld.sw_rrii_rd END -->

<!-- IDL:ld.uw_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.uw_rrii_rd`**
```idl
# 目的 rd0 ⇒ ILLI（§1 限制：ld 的 rdHA 为 rd0；先于地址计算）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(16, ea)) {          # .uw 需 2 字节对齐（§1 对齐要求）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 读 16 位后零扩展至 64 位（read_memory 已零扩展）
rd[rdHA] = read_memory(16, ea);
```
<!-- IDL:ld.uw_rrii_rd END -->

<!-- IDL:ld.st_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.st_rrii_rd`**
```idl
# 目的 rd0 ⇒ ILLI（§1 限制：ld 的 rdHA 为 rd0；先于地址计算）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(32, ea)) {          # .st 需 4 字节对齐（§1 对齐要求）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 读 32 位后符号扩展至 64 位
Bits<64> w = read_memory(32, ea);
Bits<32> v = w[31:0];
rd[rdHA] = {{32{v[31]}}, v};
```
<!-- IDL:ld.st_rrii_rd END -->

<!-- IDL:ld.ut_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.ut_rrii_rd`**
```idl
# 目的 rd0 ⇒ ILLI（§1 限制：ld 的 rdHA 为 rd0；先于地址计算）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(32, ea)) {          # .ut 需 4 字节对齐（§1 对齐要求）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 读 32 位后零扩展至 64 位（read_memory 已零扩展）
rd[rdHA] = read_memory(32, ea);
```
<!-- IDL:ld.ut_rrii_rd END -->

<!-- IDL:st.b_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.b_rrii_rd`**
```idl
# st 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0，§1 限制）⇒ 不判 ILLI
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# .b 无对齐要求（§1 对齐要求）⇒ 不判 MALIGN；只把源寄存器的低 8 位写入存储器
write_memory(8, ea, rd[rdHA]);
```
<!-- IDL:st.b_rrii_rd END -->

<!-- IDL:st.w_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.w_rrii_rd`**
```idl
# st 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0，§1 限制）⇒ 不判 ILLI
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(16, ea)) {          # .w 需 2 字节对齐（§1 对齐要求）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 只把源寄存器的低 16 位写入存储器
write_memory(16, ea, rd[rdHA]);
```
<!-- IDL:st.w_rrii_rd END -->

<!-- IDL:st.t_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.t_rrii_rd`**
```idl
# st 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0，§1 限制）⇒ 不判 ILLI
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(32, ea)) {          # .t 需 4 字节对齐（§1 对齐要求）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 只把源寄存器的低 32 位写入存储器
write_memory(32, ea, rd[rdHA]);
```
<!-- IDL:st.t_rrii_rd END -->

<!-- IDL:st.o_rrii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.o_rrii_rd`**
```idl
# st 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0，§1 限制）⇒ 不判 ILLI
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(64, ea)) {          # .o 需 8 字节对齐（§1 对齐要求）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 把源寄存器的整 64 位写入存储器
write_memory(64, ea, rd[rdHA]);
```
<!-- IDL:st.o_rrii_rd END -->

<!-- IDL:ldm.sb_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.sb_rrri_rd`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rd0 / 个数 0 / 越出 rd63 / 索引落入传送范围
if (rdHA == 6'd0) {                           # ldm 的 rdHA 为 rd0（§1 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rdHC >= rdHA && {1'b0, rdHC} < end_idx) { # 索引寄存器 rdHC 落入传送范围（执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .sb 逐元素无对齐要求 ⇒ 不判 MALIGN

# 第 k 个元素：读 8 位、符号扩展至 64 位后写入 rd[rdHA+k]；地址从 ea 起按 1 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  Bits<64> w = read_memory(8, ea);
  Bits<8> v = w[7:0];
  rd[rdHA + k] = {{56{v[7]}}, v};
  ea = ea + 48'd1;
}
```
<!-- IDL:ldm.sb_rrri_rd END -->

<!-- IDL:ldm.ub_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.ub_rrri_rd`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rd0 / 个数 0 / 越出 rd63 / 索引落入传送范围
if (rdHA == 6'd0) {                           # ldm 的 rdHA 为 rd0（§1 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rdHC >= rdHA && {1'b0, rdHC} < end_idx) { # 索引寄存器 rdHC 落入传送范围（执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .ub 逐元素无对齐要求 ⇒ 不判 MALIGN

# 第 k 个元素：读 8 位、零扩展至 64 位后写入 rd[rdHA+k]；地址从 ea 起按 1 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  rd[rdHA + k] = read_memory(8, ea);    # 零扩展由 read_memory 的 64 位零扩展给出
  ea = ea + 48'd1;
}
```
<!-- IDL:ldm.ub_rrri_rd END -->

<!-- IDL:ldm.sw_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.sw_rrri_rd`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rd0 / 个数 0 / 越出 rd63 / 索引落入传送范围
if (rdHA == 6'd0) {                           # ldm 的 rdHA 为 rd0（§1 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rdHC >= rdHA && {1'b0, rdHC} < end_idx) { # 索引寄存器 rdHC 落入传送范围（执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .sw 需 2 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(16, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：读 16 位、符号扩展至 64 位后写入 rd[rdHA+k]；地址从 ea 起按 2 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  Bits<64> w = read_memory(16, ea);
  Bits<16> v = w[15:0];
  rd[rdHA + k] = {{48{v[15]}}, v};
  ea = ea + 48'd2;
}
```
<!-- IDL:ldm.sw_rrri_rd END -->

<!-- IDL:ldm.uw_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.uw_rrri_rd`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rd0 / 个数 0 / 越出 rd63 / 索引落入传送范围
if (rdHA == 6'd0) {                           # ldm 的 rdHA 为 rd0（§1 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rdHC >= rdHA && {1'b0, rdHC} < end_idx) { # 索引寄存器 rdHC 落入传送范围（执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .uw 需 2 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(16, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：读 16 位、零扩展至 64 位后写入 rd[rdHA+k]；地址从 ea 起按 2 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  rd[rdHA + k] = read_memory(16, ea);    # 零扩展由 read_memory 的 64 位零扩展给出
  ea = ea + 48'd2;
}
```
<!-- IDL:ldm.uw_rrri_rd END -->

<!-- IDL:ldm.st_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.st_rrri_rd`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rd0 / 个数 0 / 越出 rd63 / 索引落入传送范围
if (rdHA == 6'd0) {                           # ldm 的 rdHA 为 rd0（§1 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rdHC >= rdHA && {1'b0, rdHC} < end_idx) { # 索引寄存器 rdHC 落入传送范围（执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .st 需 4 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(32, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：读 32 位、符号扩展至 64 位后写入 rd[rdHA+k]；地址从 ea 起按 4 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  Bits<64> w = read_memory(32, ea);
  Bits<32> v = w[31:0];
  rd[rdHA + k] = {{32{v[31]}}, v};
  ea = ea + 48'd4;
}
```
<!-- IDL:ldm.st_rrri_rd END -->

<!-- IDL:ldm.ut_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.ut_rrri_rd`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rd0 / 个数 0 / 越出 rd63 / 索引落入传送范围
if (rdHA == 6'd0) {                           # ldm 的 rdHA 为 rd0（§1 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rdHC >= rdHA && {1'b0, rdHC} < end_idx) { # 索引寄存器 rdHC 落入传送范围（执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .ut 需 4 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(32, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：读 32 位、零扩展至 64 位后写入 rd[rdHA+k]；地址从 ea 起按 4 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  rd[rdHA + k] = read_memory(32, ea);    # 零扩展由 read_memory 的 64 位零扩展给出
  ea = ea + 48'd4;
}
```
<!-- IDL:ldm.ut_rrri_rd END -->

<!-- IDL:ldm.o_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.o_rrri_rd`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rd0 / 个数 0 / 越出 rd63 / 索引落入传送范围
if (rdHA == 6'd0) {                           # ldm 的 rdHA 为 rd0（§1 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rdHC >= rdHA && {1'b0, rdHC} < end_idx) { # 索引寄存器 rdHC 落入传送范围（执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .o 需 8 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：读 64 位后写入 rd[rdHA+k]；地址从 ea 起按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  rd[rdHA + k] = read_memory(64, ea);
  ea = ea + 48'd8;
}
```
<!-- IDL:ldm.o_rrri_rd END -->

<!-- IDL:stm.b_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.b_rrri_rd`**
```idl
# stm 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0）、允许索引寄存器落入传送范围（§1 限制）⇒ 均不判 ILLI
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次（全程不变，与处理进度无关）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .b 逐元素无对齐要求 ⇒ 不判 MALIGN

# 第 k 个元素：取 rd[rdHA+k] 的低 8 位写到存储器；地址从 ea 起按 1 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(8, ea, rd[rdHA + k]);
  ea = ea + 48'd1;
}
```
<!-- IDL:stm.b_rrri_rd END -->

<!-- IDL:stm.w_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.w_rrri_rd`**
```idl
# stm 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0）、允许索引寄存器落入传送范围（§1 限制）⇒ 均不判 ILLI
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次（全程不变，与处理进度无关）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .w 需 2 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(16, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：取 rd[rdHA+k] 的低 16 位写到存储器；地址从 ea 起按 2 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(16, ea, rd[rdHA + k]);
  ea = ea + 48'd2;
}
```
<!-- IDL:stm.w_rrri_rd END -->

<!-- IDL:stm.t_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.t_rrri_rd`**
```idl
# stm 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0）、允许索引寄存器落入传送范围（§1 限制）⇒ 均不判 ILLI
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次（全程不变，与处理进度无关）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .t 需 4 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(32, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：取 rd[rdHA+k] 的低 32 位写到存储器；地址从 ea 起按 4 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(32, ea, rd[rdHA + k]);
  ea = ea + 48'd4;
}
```
<!-- IDL:stm.t_rrri_rd END -->

<!-- IDL:stm.o_rrri_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.o_rrri_rd`**
```idl
# stm 允许 rdHA 为 rd0（rd0 作为源寄存器读出 0）、允许索引寄存器落入传送范围（§1 限制）⇒ 均不判 ILLI
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rdHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rdHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次（全程不变，与处理进度无关）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];

# .o 需 8 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：取 rd[rdHA+k] 的整 64 位写到存储器；地址从 ea 起按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(64, ea, rd[rdHA + k]);
  ea = ea + 48'd8;
}
```
<!-- IDL:stm.o_rrri_rd END -->

## 2. 存取RB寄存器

RB寄存器都是64位，因此不需要指定数据长度，指令如下：

```simrisc
ld.o     rbHA, [rbHB, imms12]
st.o     rbHA, [rbHB, imms12]

ldm.o    {rbHA:rbHA+immu6-1}, [rbHB, rdHC]
stm.o    {rbHA:rbHA+immu6-1}, [rbHB, rdHC]
```

限制如下：

- `ld.o`/`st.o` 和 `ldm.o`/`stm.o` 均需 8 字节地址对齐，未对齐触发 MALIGN 异常
- `ld.o`/`ldm.o` 指令的 `rbHA` 为 `rb0` 时触发 ILLI 异常（rb0 通用约定见 SimRISC-00）；`st.o`/`stm.o` 指令允许 `rbHA` 为 `rb0`（rb0 作为源寄存器读出为当前指令的地址）
- `immu6` = 0 时触发 ILLI 异常
- `rbHA + immu6 > 64`（超出 rb63）时触发 ILLI 异常
- **`ldm.o` 禁止基址寄存器落入传送范围**：RB 形式的传送范围在 RB 组、基址寄存器是同组的 `rbHB`；`rbHA <= rbHB < rbHA + immu6` 时触发 ILLI 异常（静态：在指令执行前判定，不产生任何元素的效果；理由同 §1：写入传送范围会使后续元素的地址依赖处理进度）。
- **`stm.o` 允许基址寄存器落入传送范围**：`stm.o` 只读出传送范围内的寄存器、不写任何寄存器 ⇒ 地址与处理进度无关，行为确定。
- **索引寄存器不适用**：RB 形式的索引寄存器 `rdHC` 属于 RD 组，而传送范围在 RB 组，结构上不可能落入范围（RD 形式相反，见 §1）。

### 2.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-01.idl` 生成，逐条如下：

<!-- IDL:ld.o_rrii_rb BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.o_rrii_rb`**
```idl
# 目的 rb0 ⇒ ILLI（§2 限制：ld.o 的 rbHA 为 rb0；rb0 只读、读出为当前指令地址）
if (rbHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位（作访存基址取 rb[47:0]）

if (!is_naturally_aligned(64, ea)) {          # .o 需 8 字节对齐（§2 限制）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# RB 为整 64 位寄存器、装入为全 64 位操作（SimRISC-00：存取/复制为整 64 位，仅作基址时取低 48 位）
rb[rbHA] = read_memory(64, ea);
```
<!-- IDL:ld.o_rrii_rb END -->

<!-- IDL:st.o_rrii_rb BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.o_rrii_rb`**
```idl
# st.o 允许 rbHA 为 rb0（rb0 作为源寄存器读出当前指令地址，§2 限制）⇒ 不判 ILLI
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位（作访存基址取 rb[47:0]）

if (!is_naturally_aligned(64, ea)) {          # .o 需 8 字节对齐（§2 限制）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 源取出整 64 位（rb 全 64 位可读；rb0 读出 = IP）
write_memory(64, ea, rb[rbHA]);
```
<!-- IDL:st.o_rrii_rb END -->

<!-- IDL:ldm.o_rrri_rb BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.o_rrri_rb`**
```idl
# 静态检查（每项都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：目的 rb0 / 个数 0 / 越出 rb63 / 基址落入传送范围
if (rbHA == 6'd0) {                           # ldm.o 的 rbHA 为 rb0（§2 限制）
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rbHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rbHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}
if (rbHB >= rbHA && {1'b0, rbHB} < end_idx) { # 基址寄存器 rbHB 落入传送范围（同组；执行前判定，不产生任何元素的效果）
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引 rdHC 属 RD 组，结构上不可能落入 RB 传送范围 ⇒ 不判重叠
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# .o 需 8 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：读 64 位后写入 rb[rbHA+k]（全 64 位）；地址从 ea 起按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  rb[rbHA + k] = read_memory(64, ea);
  ea = ea + 48'd8;
}
```
<!-- IDL:ldm.o_rrri_rb END -->

<!-- IDL:stm.o_rrri_rb BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.o_rrri_rb`**
```idl
# stm.o 允许 rbHA 为 rb0（读出 IP）、允许基址寄存器落入传送范围（§2 限制）⇒ 均不判 ILLI
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rbHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rbHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次（全程不变，与处理进度无关）
# 基址哪怕落在传送范围内也只读一次 ⇒ 地址不随已生效元素改变（§2 明文允许该重叠）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# .o 需 8 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素：取 rb[rbHA+k] 的整 64 位写到存储器；地址从 ea 起按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(64, ea, rb[rbHA + k]);
  ea = ea + 48'd8;
}
```
<!-- IDL:stm.o_rrri_rb END -->

## 3. 存取RA寄存器

RA寄存器都是64位，指令如下：

```simrisc
ld.o     raHA, [rbHB, imms12]
st.o     raHA, [rbHB, imms12]

ldm.o    {raHA:raHA+immu6-1}, [rbHB, rdHC]
stm.o    {raHA:raHA+immu6-1}, [rbHB, rdHC]
```

限制如下：

- `ld.o`/`st.o` 和 `ldm.o`/`stm.o` 均需 8 字节地址对齐，未对齐触发 MALIGN 异常
- `raHA` 为 `ra0` 时不触发异常（ra0 可读写）
- `immu6` = 0 时触发 ILLI 异常
- `raHA + immu6 > 64` 时触发 ILLI 异常（超出 ra63）
- **基址/索引寄存器与传送范围的重叠：不适用**——传送范围在 RA 组，基址寄存器 `rbHB` 在 RB 组、索引寄存器 `rdHC` 在 RD 组，结构上不可能落入范围。

### 3.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-01.idl` 生成，逐条如下：

<!-- IDL:ld.o_rrii_ra BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.o_rrii_ra`**
```idl
# ra0 可读写（§3 限制：raHA 为 ra0 不触发异常）⇒ 无 ILLI 判定
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(64, ea)) {          # .o 需 8 字节对齐（§3 限制）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# ra1–ra63 按逻辑栈序编号（ra63 = 栈顶；物理环状缓冲与其指针对软件不可见）⇒ 直接读写逻辑第 raHA 条。
# 存取不做压栈/弹栈 ⇒ 无 RASOF/RASUF；ra0 = {[63:54] SBZ（写无效）, [53:48] RACNT, [47:0] MRPTR}
# ⇒ 写 ra0 时只写 [53:0]（RACNT 随数据写入，OS 借此恢复），[63:54] 保持原值
Bits<64> v = read_memory(64, ea);             # 大端读，整 64 位
if (raHA == 6'd0) {
  ra[6'd0][53:0] = v[53:0];
} else {
  ra[raHA] = v;
}
```
<!-- IDL:ld.o_rrii_ra END -->

<!-- IDL:st.o_rrii_ra BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.o_rrii_ra`**
```idl
# ra0 可读写（§3 限制）⇒ 无 ILLI 判定
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(64, ea)) {          # .o 需 8 字节对齐（§3 限制）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 源取逻辑第 raHA 条的整 64 位（ra0 读出 = {SBZ[63:54], RACNT[53:48], MRPTR[47:0]}）
write_memory(64, ea, ra[raHA]);
```
<!-- IDL:st.o_rrii_ra END -->

<!-- IDL:ldm.o_rrri_ra BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.o_rrri_ra`**
```idl
# 静态检查（都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：个数 0 / 越出 ra63（ra0 可读写 ⇒ 不判目的 0 号）
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, raHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # raHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；基址在 RB 组、索引在 RD 组，传送范围在 RA 组
# ⇒ 地址寄存器与传送范围结构上不可能重叠，不判重叠（§3 限制）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# .o 需 8 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素进逻辑第 raHA+k 条（ra63 = 栈顶；物理环状缓冲对软件不可见），ra0 只写 [53:0]；地址从 ea 起按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  Bits<6> idx = raHA + k;
  Bits<64> v = read_memory(64, ea);
  if (idx == 6'd0) {
    ra[6'd0][53:0] = v[53:0];
  } else {
    ra[idx] = v;
  }
  ea = ea + 48'd8;
}
```
<!-- IDL:ldm.o_rrri_ra END -->

<!-- IDL:stm.o_rrri_ra BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.o_rrri_ra`**
```idl
# 静态检查（都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：个数 0 / 越出 ra63（ra0 可读写 ⇒ 不判目的 0 号）
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, raHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # raHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
# ⇒ 地址寄存器与传送范围结构上不可能重叠，不判重叠（§3 限制）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# .o 需 8 字节对齐：起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定（§1「部分生效」注允许整段预检）
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素取逻辑第 raHA+k 条的整 64 位（ra0 读出含 RACNT/MRPTR）；地址从 ea 起按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(64, ea, ra[raHA + k]);
  ea = ea + 48'd8;
}
```
<!-- IDL:stm.o_rrri_ra END -->

## 4. 存取RF寄存器

RF寄存器分为tetra和octa两种情况，tetra为32位，octa为64位，对应单精和双精两种情况，指令如下：

```simrisc
ld.t    rfHA, [rbHB, imms12]
st.t    rfHA, [rbHB, imms12]
ld.o    rfHA, [rbHB, imms12]
st.o    rfHA, [rbHB, imms12]

ldm.t   {rfHA:rfHA+immu6-1}, [rbHB, rdHC]
stm.t   {rfHA:rfHA+immu6-1}, [rbHB, rdHC]
ldm.o   {rfHA:rfHA+immu6-1}, [rbHB, rdHC]
stm.o   {rfHA:rfHA+immu6-1}, [rbHB, rdHC]
```

对齐要求：`ld.o`/`st.o`/`ldm.o`/`stm.o` 需 8 字节对齐，`ld.t`/`st.t`/`ldm.t`/`stm.t` 需 4 字节对齐。未对齐触发 MALIGN 异常。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
- `rfHA + immu6 > 64`（超出 rf63）时触发 ILLI 异常
- **基址/索引寄存器与传送范围的重叠：不适用**（同 §3）——传送范围在 RF 组，基址寄存器 `rbHB` 在 RB 组、索引寄存器 `rdHC` 在 RD 组，结构上不可能落入范围。

> **注**：`rf0` 作**目的**合法（`ld.o`/`ldm.o`/`ld.t`/`ldm.t`），写入按 SimRISC-00 的写语义；`rf0` 作**源**（`st.o`/`st.t`/`stm.o`/`stm.t`）读出完整 64 位。
>
> **`ld.t`/`ldm.t` 的写入宽度**：单精装载**只写目的寄存器低 32 位，高 32 位保持原值**（不作符号扩展、也不零填）。因此 `ld.t`/`ldm.t` 写入 `rf0` 时，低 32 位中位于可写域的只有 `[4:0]`（异常状态）——只读 qNaN 位 `[31:22]` 与 SBZ `[21:5]` 保持原值，`[33:32]` 因不在写入宽度内同样保持原值。[SimRISC-00 §浮点状态寄存器]

### 4.1 形式化语义（IDL）

本节各指令的形式化语义由 `idl/SimRISC-01.idl` 生成，逐条如下：

<!-- IDL:ld.t_rrii_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.t_rrii_rf`**
```idl
# rf0 作目的合法（§4 注）⇒ 不判 ILLI；.t 需 4 字节对齐（§4 正文、附录 B excp_malign 与编码表 aligned(4) 三方一致）
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(32, ea)) {          # .t 需 4 字节对齐（§4）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 单精装载只写目的低 32 位、高 32 位保持原值（SimRISC-00 §2.3 总则 + §4 注）⇒ 走 ft 视图；
# rf0 = FCSR：低 32 位里可写域只有 [4:0]（异常状态），qNaN[31:22] 与 SBZ[21:5] 保持原值
Bits<64> w = read_memory(32, ea);
Bits<32> v = w[31:0];
if (rfHA == 6'd0) {
  rf[6'd0][4:0] = v[4:0];
} else {
  ft[rfHA] = v;
}
```
<!-- IDL:ld.t_rrii_rf END -->

<!-- IDL:st.t_rrii_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.t_rrii_rf`**
```idl
# rf0 作源合法（§4 注：读出完整 64 位）；.t 需 4 字节对齐（§4 正文、附录 B excp_malign 与编码表 aligned(4) 三方一致）
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(32, ea)) {          # .t 需 4 字节对齐（§4）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 单精存储取源寄存器的低 32 位写存储器（tetra）
write_memory(32, ea, rf[rfHA]);
```
<!-- IDL:st.t_rrii_rf END -->

<!-- IDL:ld.o_rrii_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ld.o_rrii_rf`**
```idl
# rf0 作目的合法（§4 注）⇒ 不判 ILLI；.o 需 8 字节对齐（§4 正文、附录 B excp_malign 与编码表 aligned(8) 三方一致）
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(64, ea)) {          # .o 需 8 字节对齐（§4）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# rf0 = FCSR（SimRISC-00 §2.3.1）：写 rf0 只更新 [33:32]（舍入模式）与 [4:0]（异常状态），
# 其余位（只读 qNaN 位、SBZ）写无效、保持原值；其余项整 64 位写入
Bits<64> v = read_memory(64, ea);
if (rfHA == 6'd0) {
  rf[6'd0][33:32] = v[33:32];
  rf[6'd0][4:0] = v[4:0];
} else {
  rf[rfHA] = v;
}
```
<!-- IDL:ld.o_rrii_rf END -->

<!-- IDL:st.o_rrii_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`st.o_rrii_rf`**
```idl
# rf0 作源合法（§4 注：读出完整 64 位）；.o 需 8 字节对齐（§4 正文、附录 B excp_malign 与编码表 aligned(8) 三方一致）
Bits<64> ea64 = rb[rbHB] + $signed(imms12);   # 地址公式（rrii）= 基址 + 符号扩展的 12 位立即数，64 位全宽
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

if (!is_naturally_aligned(64, ea)) {          # .o 需 8 字节对齐（§4）
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 源读出整 64 位（rf0 读出 = {qNaN, SBZ, 舍入模式, qNaN, SBZ, 异常状态}）
write_memory(64, ea, rf[rfHA]);
```
<!-- IDL:st.o_rrii_rf END -->

<!-- IDL:ldm.t_rrri_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.t_rrri_rf`**
```idl
# 静态检查（都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：个数 0 / 越出 rf63（rf0 可作目的 ⇒ 不判目的 0 号）
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rfHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rfHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；基址在 RB 组、索引在 RD 组，传送范围在 RF 组
# ⇒ 地址寄存器与传送范围结构上不可能重叠，不判重叠（§4 限制）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# 对齐：.t 需 4 字节对齐（§4 正文、附录 B excp_malign 与编码表 aligned(4) 三方一致）；起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定
if (!is_naturally_aligned(32, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素只写逻辑第 rfHA+k 条的低 32 位（高 32 位保持，SimRISC-00 §2.3）；rf0 只写 [4:0]；地址按 4 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  Bits<6> idx = rfHA + k;
  Bits<64> w = read_memory(32, ea);
  Bits<32> v = w[31:0];
  if (idx == 6'd0) {
    rf[6'd0][4:0] = v[4:0];
  } else {
    ft[idx] = v;
  }
  ea = ea + 48'd4;
}
```
<!-- IDL:ldm.t_rrri_rf END -->

<!-- IDL:stm.t_rrri_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.t_rrri_rf`**
```idl
# 静态检查（都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：个数 0 / 越出 rf63（rf0 可作源 ⇒ 不判目的 0 号）
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rfHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rfHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
# ⇒ 地址寄存器与传送范围结构上不可能重叠，不判重叠（§4 限制）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# 对齐：.t 需 4 字节对齐（同 ldm.t；§4 正文、附录 B excp_malign 与编码表 aligned(4) 三方一致）
if (!is_naturally_aligned(32, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素取 rf[rfHA+k] 的低 32 位，地址按 4 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(32, ea, rf[rfHA + k]);
  ea = ea + 48'd4;
}
```
<!-- IDL:stm.t_rrri_rf END -->

<!-- IDL:ldm.o_rrri_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`ldm.o_rrri_rf`**
```idl
# 静态检查（都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：个数 0 / 越出 rf63（rf0 可作目的 ⇒ 不判目的 0 号）
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rfHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rfHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；基址在 RB 组、索引在 RD 组，传送范围在 RF 组
# ⇒ 地址寄存器与传送范围结构上不可能重叠，不判重叠（§4 限制）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# 对齐：.o 需 8 字节对齐（§4 正文、附录 B excp_malign 与编码表 aligned(8) 三方一致）；起始地址对齐 + 步长 = 宽度 ⇒ 每个元素都对齐；循环前判定
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素整 64 位写入 rf[rfHA+k]；rf0 只写 [33:32] 与 [4:0]（SimRISC-00 §2.3.1）；地址按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  Bits<6> idx = rfHA + k;
  Bits<64> v = read_memory(64, ea);
  if (idx == 6'd0) {
    rf[6'd0][33:32] = v[33:32];
    rf[6'd0][4:0] = v[4:0];
  } else {
    rf[idx] = v;
  }
  ea = ea + 48'd8;
}
```
<!-- IDL:ldm.o_rrri_rf END -->

<!-- IDL:stm.o_rrri_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
**`stm.o_rrri_rf`**
```idl
# 静态检查（都 ⇒ ILLI，码相同 ⇒ 彼此先后不可观测）：个数 0 / 越出 rf63（rf0 可作源 ⇒ 不判目的 0 号）
if (immu6 == 6'd0) {                          # 个数为 0（有效范围 1~63）
  raise(ExceptionCode::Illegal, mode(), ip());
}
Bits<7> end_idx = {1'b0, rfHA} + {1'b0, immu6};
if (end_idx > 7'd64) {                        # rfHA + immu6 > 64：不环绕、不截断
  raise(ExceptionCode::Illegal, mode(), ip());
}

# 地址公式（rrri）= 基址 + 索引寄存器；索引在指令开始执行时读一次
# ⇒ 地址寄存器与传送范围结构上不可能重叠，不判重叠（§4 限制）
Bits<64> ea64 = rb[rbHB] + rd[rdHC];
Bits<48> ea = ea64[47:0];                     # 有效地址 = 低 48 位

# 对齐：.o 需 8 字节对齐（同 ldm.o；§4 正文、附录 B excp_malign 与编码表 aligned(8) 三方一致）
if (!is_naturally_aligned(64, ea)) {
  raise(ExceptionCode::Malign, mode(), {16'd0, ea});
}

# 第 k 个元素取 rf[rfHA+k] 的整 64 位，地址按 8 字节递增
for (Bits<6> k = 6'd0; k < immu6; k++) {
  write_memory(64, ea, rf[rfHA + k]);
  ea = ea + 48'd8;
}
```
<!-- IDL:stm.o_rrri_rf END -->

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `ld.o` | `rrii` | `ra` | `ld.o raHA, [rbHB, imms12]` | `ld.o_rrii_ra` |
| `ld.o` | `rrii` | `rb` | `ld.o rbHA, [rbHB, imms12]` | `ld.o_rrii_rb` |
| `ld.o` | `rrii` | `rd` | `ld.o rdHA, [rbHB, imms12]` | `ld.o_rrii_rd` |
| `ld.o` | `rrii` | `rf` | `ld.o rfHA, [rbHB, imms12]` | `ld.o_rrii_rf` |
| `ld.sb` | `rrii` | `rd` | `ld.sb rdHA, [rbHB, imms12]` | `ld.sb_rrii_rd` |
| `ld.st` | `rrii` | `rd` | `ld.st rdHA, [rbHB, imms12]` | `ld.st_rrii_rd` |
| `ld.sw` | `rrii` | `rd` | `ld.sw rdHA, [rbHB, imms12]` | `ld.sw_rrii_rd` |
| `ld.t` | `rrii` | `rf` | `ld.t rfHA, [rbHB, imms12]` | `ld.t_rrii_rf` |
| `ld.ub` | `rrii` | `rd` | `ld.ub rdHA, [rbHB, imms12]` | `ld.ub_rrii_rd` |
| `ld.ut` | `rrii` | `rd` | `ld.ut rdHA, [rbHB, imms12]` | `ld.ut_rrii_rd` |
| `ld.uw` | `rrii` | `rd` | `ld.uw rdHA, [rbHB, imms12]` | `ld.uw_rrii_rd` |
| `ldm.o` | `rrri` | `ra` | `ldm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_ra` |
| `ldm.o` | `rrri` | `rb` | `ldm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_rb` |
| `ldm.o` | `rrri` | `rd` | `ldm.o {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_rd` |
| `ldm.o` | `rrri` | `rf` | `ldm.o {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `ldm.o_rrri_rf` |
| `ldm.sb` | `rrri` | `rd` | `ldm.sb {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.sb_rrri_rd` |
| `ldm.st` | `rrri` | `rd` | `ldm.st {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.st_rrri_rd` |
| `ldm.sw` | `rrri` | `rd` | `ldm.sw {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.sw_rrri_rd` |
| `ldm.t` | `rrri` | `rf` | `ldm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `ldm.t_rrri_rf` |
| `ldm.ub` | `rrri` | `rd` | `ldm.ub {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.ub_rrri_rd` |
| `ldm.ut` | `rrri` | `rd` | `ldm.ut {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.ut_rrri_rd` |
| `ldm.uw` | `rrri` | `rd` | `ldm.uw {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `ldm.uw_rrri_rd` |
| `st.b` | `rrii` | `rd` | `st.b rdHA, [rbHB, imms12]` | `st.b_rrii_rd` |
| `st.o` | `rrii` | `ra` | `st.o raHA, [rbHB, imms12]` | `st.o_rrii_ra` |
| `st.o` | `rrii` | `rb` | `st.o rbHA, [rbHB, imms12]` | `st.o_rrii_rb` |
| `st.o` | `rrii` | `rd` | `st.o rdHA, [rbHB, imms12]` | `st.o_rrii_rd` |
| `st.o` | `rrii` | `rf` | `st.o rfHA, [rbHB, imms12]` | `st.o_rrii_rf` |
| `st.t` | `rrii` | `rd` | `st.t rdHA, [rbHB, imms12]` | `st.t_rrii_rd` |
| `st.t` | `rrii` | `rf` | `st.t rfHA, [rbHB, imms12]` | `st.t_rrii_rf` |
| `st.w` | `rrii` | `rd` | `st.w rdHA, [rbHB, imms12]` | `st.w_rrii_rd` |
| `stm.b` | `rrri` | `rd` | `stm.b {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.b_rrri_rd` |
| `stm.o` | `rrri` | `ra` | `stm.o {raHA:raHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_ra` |
| `stm.o` | `rrri` | `rb` | `stm.o {rbHA:rbHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_rb` |
| `stm.o` | `rrri` | `rd` | `stm.o {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_rd` |
| `stm.o` | `rrri` | `rf` | `stm.o {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `stm.o_rrri_rf` |
| `stm.t` | `rrri` | `rd` | `stm.t {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.t_rrri_rd` |
| `stm.t` | `rrri` | `rf` | `stm.t {rfHA:rfHA+immu6-1}, [rbHB, rdHC]` | `stm.t_rrri_rf` |
| `stm.w` | `rrri` | `rd` | `stm.w {rdHA:rdHA+immu6-1}, [rbHB, rdHC]` | `stm.w_rrri_rd` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `ld.o_rrii_rd`, `ld.sb_rrii_rd`, `ld.st_rrii_rd`, `ld.sw_rrii_rd`, `ld.ub_rrii_rd`, `ld.ut_rrii_rd`, `ld.uw_rrii_rd`, `ldm.o_rrri_rd`, `ldm.sb_rrri_rd`, `ldm.st_rrri_rd`, `ldm.sw_rrri_rd`, `ldm.ub_rrri_rd`, `ldm.ut_rrri_rd`, `ldm.uw_rrri_rd`（14 条）
* `dst_rb0`：目的 rb0 → ILLI — `ld.o_rrii_rb`, `ldm.o_rrri_rb`（2 条）
* `mreg_zero`：immu6=0 → ILLI — `ldm.o_rrri_ra`, `ldm.o_rrri_rb`, `ldm.o_rrri_rd`, `ldm.o_rrri_rf`, `ldm.sb_rrri_rd`, `ldm.st_rrri_rd`, `ldm.sw_rrri_rd`, `ldm.t_rrri_rf`, `ldm.ub_rrri_rd`, `ldm.ut_rrri_rd`, `ldm.uw_rrri_rd`, `stm.b_rrri_rd`, `stm.o_rrri_ra`, `stm.o_rrri_rb`, `stm.o_rrri_rd`, `stm.o_rrri_rf`, `stm.t_rrri_rd`, `stm.t_rrri_rf`, `stm.w_rrri_rd`（19 条）
* `mreg_range_overflow`：起始+immu6>64 → ILLI — `ldm.o_rrri_ra`, `ldm.o_rrri_rb`, `ldm.o_rrri_rd`, `ldm.o_rrri_rf`, `ldm.sb_rrri_rd`, `ldm.st_rrri_rd`, `ldm.sw_rrri_rd`, `ldm.t_rrri_rf`, `ldm.ub_rrri_rd`, `ldm.ut_rrri_rd`, `ldm.uw_rrri_rd`, `stm.b_rrri_rd`, `stm.o_rrri_ra`, `stm.o_rrri_rb`, `stm.o_rrri_rd`, `stm.o_rrri_rf`, `stm.t_rrri_rd`, `stm.t_rrri_rf`, `stm.w_rrri_rd`（19 条）
* `mreg_range_addr_overlap`：`ldm` 基址/索引落入传送范围 → ILLI — `ldm.o_rrri_rb`, `ldm.o_rrri_rd`, `ldm.sb_rrri_rd`, `ldm.st_rrri_rd`, `ldm.sw_rrri_rd`, `ldm.ub_rrri_rd`, `ldm.ut_rrri_rd`, `ldm.uw_rrri_rd`（8 条）
* `excp_malign`（动态）：未对齐访问 → MALIGN — `ld.o_rrii_ra`, `ld.o_rrii_rb`, `ld.o_rrii_rd`, `ld.o_rrii_rf`, `ld.st_rrii_rd`, `ld.sw_rrii_rd`, `ld.t_rrii_rf`, `ld.ut_rrii_rd`, `ld.uw_rrii_rd`, `ldm.o_rrri_ra`, `ldm.o_rrri_rb`, `ldm.o_rrri_rd`, `ldm.o_rrri_rf`, `ldm.st_rrri_rd`, `ldm.sw_rrri_rd`, `ldm.t_rrri_rf`, `ldm.ut_rrri_rd`, `ldm.uw_rrri_rd`, `st.o_rrii_ra`, `st.o_rrii_rb`, `st.o_rrii_rd`, `st.o_rrii_rf`, `st.t_rrii_rd`, `st.t_rrii_rf`, `st.w_rrii_rd`, `stm.o_rrri_ra`, `stm.o_rrri_rb`, `stm.o_rrri_rd`, `stm.o_rrri_rf`, `stm.t_rrri_rd`, `stm.t_rrri_rf`, `stm.w_rrri_rd`（32 条）
<!-- LEGALITY_END -->
