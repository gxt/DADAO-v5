# SimRISC16位立即数操作指令

> **版本：0.5.7-rc**（与 SimRISC-00 一致）
> **分类：16位立即数操作** — set.zw/set.ow/set.w/or.w/andn.w（rwii 格式）
> **伪指令**：`set.rd`/`set.rb`/`set.rf`/`set.ft`/`set.fo` 见 `Toolchain-01 §6.2`。

## 1. 立即数常数赋值：RD 组

本章为 `rd` 寄存器组的 16 位立即数设置类指令（`rb` 组见 §2、`rf` 组见 §3）。

立即数设置类指令直接用立即数对寄存器内的不同wyde进行赋值、或、与非、零扩展赋值。
由于立即数域为16位，因此，需要指定具体的wyde的位置，分别采用 `wp3/wp2/wp1/wp0`，对应 `MSW..LSW`。

`wpN` 选中的就是寄存器中 `[16*N+15 : 16*N]` 这 16 位（`wp0` = `[15:0]` LSW、`wp1` = `[31:16]`、`wp2` = `[47:32]`、`wp3` = `[63:48]` MSW），指令的 16 位 `immu16` 字段**整体**写入该 wyde；`set.ow`/`set.zw` 的「其余 48 位」即**未被选中的另外三个 wyde**。

操作数类型为 `rwii`，指令如下：

```simrisc
set.ow   rdHA, wpN, immu16
set.zw   rdHA, wpN, immu16
or.w     rdHA, wpN, immu16
andn.w   rdHA, wpN, immu16
```

由于rd寄存器为64位，而set.ow/set.zw指令只设置了其中16位，两者的区别在于set.ow指令则将其余48位置1，set.zw指令将其余48位置0。

<!-- IDL:set.ow_rwii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: set.ow_rwii_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# wpN 选中的 wyde 整体写 immu16，其余 48 位全 1（SimRISC-03 §1 set.ow）；
# 「其余 48 位」按整寄存器赋值表达（idl/README §3）
if (wpN == 2'd0) {
  rd[rdHA] = {48'hFFFF_FFFF_FFFF, immu16};
} else if (wpN == 2'd1) {
  rd[rdHA] = {32'hFFFF_FFFF, immu16, 16'hFFFF};
} else if (wpN == 2'd2) {
  rd[rdHA] = {16'hFFFF, immu16, 32'hFFFF_FFFF};
} else {
  rd[rdHA] = {immu16, 48'hFFFF_FFFF_FFFF};
}
```
<!-- IDL:set.ow_rwii_rd END -->

<!-- IDL:set.zw_rwii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: set.zw_rwii_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# wpN 选中的 wyde 整体写 immu16，其余 48 位全 0（SimRISC-03 §1 set.zw）；
# 「其余 48 位」按整寄存器赋值表达（idl/README §3）
if (wpN == 2'd0) {
  rd[rdHA] = {48'd0, immu16};
} else if (wpN == 2'd1) {
  rd[rdHA] = {32'd0, immu16, 16'd0};
} else if (wpN == 2'd2) {
  rd[rdHA] = {16'd0, immu16, 32'd0};
} else {
  rd[rdHA] = {immu16, 48'd0};
}
```
<!-- IDL:set.zw_rwii_rd END -->

`or.w` 指令（rwii 格式）：将 `rdHA` 中由 `wpN` 指定的 wyde 替换为 `(rdHA[wyde] | immu16)`，其余 wyde 保持不变。

> **注意**：`or.w` 同时是 OPC-wyde 表的三寄存器逻辑 OR 指令（`or.w rdHB, rdHC, rdHD`），汇编器按操作数格式区分。

<!-- IDL:or.w_rwii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: or.w_rwii_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# wpN 选中的 wyde 替换为 (旧 wyde | immu16)，其余 48 位不变；按 wyde 写用切片赋值（idl/README §3）
Bits<64> old = rd[rdHA];
if (wpN == 2'd0) {
  rd[rdHA][15:0] = (old[15:0] | immu16);
} else if (wpN == 2'd1) {
  rd[rdHA][31:16] = (old[31:16] | immu16);
} else if (wpN == 2'd2) {
  rd[rdHA][47:32] = (old[47:32] | immu16);
} else {
  rd[rdHA][63:48] = (old[63:48] | immu16);
}
```
<!-- IDL:or.w_rwii_rd END -->
`andn.w` 指令：将 `rdHA` 中由 `wpN` 指定的 wyde 替换为 `(rdHA[wyde] & ~immu16)`，其余 wyde 保持不变。

<!-- IDL:andn.w_rwii_rd BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: andn.w_rwii_rd
# 目的 rd0 ⇒ ILLI（附录 B dst_rd0）
if (rdHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# wpN 选中的 wyde（[16*N+15:16*N]，SimRISC-03 §1）替换为 (旧 wyde & ~immu16)，
# 其余 48 位不变；按 wyde 写用切片赋值（idl/README §3）
Bits<64> old = rd[rdHA];
if (wpN == 2'd0) {
  rd[rdHA][15:0] = (old[15:0] & ~immu16);
} else if (wpN == 2'd1) {
  rd[rdHA][31:16] = (old[31:16] & ~immu16);
} else if (wpN == 2'd2) {
  rd[rdHA][47:32] = (old[47:32] & ~immu16);
} else {
  rd[rdHA][63:48] = (old[63:48] & ~immu16);
}
```
<!-- IDL:andn.w_rwii_rd END -->

## 2. 立即数常数赋值：RB 组

本章为 `rb` 寄存器组的 16 位立即数设置类指令（无 `set.ow` 变体）。

针对rb寄存器，提供了or.w/andn.w/set.zw指令，操作数类型为 `rwii`，指令如下：

```simrisc
set.zw  rbHA, wpN, immu16
or.w    rbHA, wpN, immu16
andn.w  rbHA, wpN, immu16
```

<!-- IDL:andn.w_rwii_rb BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: andn.w_rwii_rb
# 目的 rb0 ⇒ ILLI（附录 B dst_rb0；rb0 读出为 IP，不得作普通目的）
if (rbHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# wpN 选中的 wyde（[16*N+15:16*N]，SimRISC-03 §1）替换为 (旧 wyde & ~immu16)，
# 其余 48 位不变；按 wyde 写用切片赋值（idl/README §3）
# （语义见 SimRISC-03 §1 andn.w；§2 把同名指令给 rb 组）
Bits<64> old = rb[rbHA];
if (wpN == 2'd0) {
  rb[rbHA][15:0] = (old[15:0] & ~immu16);
} else if (wpN == 2'd1) {
  rb[rbHA][31:16] = (old[31:16] & ~immu16);
} else if (wpN == 2'd2) {
  rb[rbHA][47:32] = (old[47:32] & ~immu16);
} else {
  rb[rbHA][63:48] = (old[63:48] & ~immu16);
}
```
<!-- IDL:andn.w_rwii_rb END -->

<!-- IDL:or.w_rwii_rb BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: or.w_rwii_rb
# 目的 rb0 ⇒ ILLI（附录 B dst_rb0）
if (rbHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# wpN 选中的 wyde 替换为 (旧 wyde | immu16)，其余 48 位不变；按 wyde 写用切片赋值
# （语义见 SimRISC-03 §1 or.w；§2 把同名指令给 rb 组）
Bits<64> old = rb[rbHA];
if (wpN == 2'd0) {
  rb[rbHA][15:0] = (old[15:0] | immu16);
} else if (wpN == 2'd1) {
  rb[rbHA][31:16] = (old[31:16] | immu16);
} else if (wpN == 2'd2) {
  rb[rbHA][47:32] = (old[47:32] | immu16);
} else {
  rb[rbHA][63:48] = (old[63:48] | immu16);
}
```
<!-- IDL:or.w_rwii_rb END -->

<!-- IDL:set.zw_rwii_rb BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: set.zw_rwii_rb
# 目的 rb0 ⇒ ILLI（附录 B dst_rb0）
if (rbHA == 6'd0) {
  raise(ExceptionCode::Illegal, mode(), ip());
}

# wpN 选中的 wyde 整体写 immu16，其余 48 位全 0；「其余 48 位」按整寄存器赋值表达
# （语义见 SimRISC-03 §1 set.zw；§2 把同名指令给 rb 组）
if (wpN == 2'd0) {
  rb[rbHA] = {48'd0, immu16};
} else if (wpN == 2'd1) {
  rb[rbHA] = {32'd0, immu16, 16'd0};
} else if (wpN == 2'd2) {
  rb[rbHA] = {16'd0, immu16, 32'd0};
} else {
  rb[rbHA] = {immu16, 48'd0};
}
```
<!-- IDL:set.zw_rwii_rb END -->

## 3. 立即数常数赋值：RF 组

本章为 `rf` 寄存器组的 16 位立即数设置类指令（`set.w`）。

针对rf寄存器，SimRISC提供了set.w指令，操作数类型为 `rwii` ，指令如下：

```simrisc
set.w    rfHA, wpN, immu16
```

`set.w` 指令只设置相应的16位，其余48位不变。
因此，32位单精浮点（tetra）需要两条指令设置立即数的值，64位双精浮点（octa）则需要四条指令。

> **注**：`set.w rf0, wpN, immu16` 合法；写入按 SimRISC-00 写语义（`wp2` 命中舍入模式、`wp0` 命中异常状态、`wp1`/`wp3` 完全写无效）。

<!-- IDL:set.w_rwii_rf BEGIN -->
<!-- 由 idl/render.py 生成，勿手改 -->
```idl
# id: set.w_rwii_rf
# wpN 选中的 wyde 整体写 immu16，其余 48 位保持；按 wyde 写用切片赋值（idl/README §3）
# rf0 = FCSR（SimRISC-00 §2.3.1）：写 rf0 只更新 [33:32]（舍入模式）与 [4:0]（异常状态），
# 其余位写无效、保持原值 ⇒ wp2 只写 [33:32]、wp0 只写 [4:0]、wp1/wp3 完全写无效（SimRISC-03 §3 注）
# rf 属「直接赋值/复制类」，不受「专用于浮点类指令」限制（SimRISC-00 §2.3）
if (rfHA == 6'd0) {
  if (wpN == 2'd2) {
    rf[6'd0][33:32] = immu16[1:0];
  } else if (wpN == 2'd0) {
    rf[6'd0][4:0] = immu16[4:0];
  }
  # wp1/wp3：完全写无效，不写
} else if (wpN == 2'd0) {
  rf[rfHA][15:0] = immu16;
} else if (wpN == 2'd1) {
  rf[rfHA][31:16] = immu16;
} else if (wpN == 2'd2) {
  rf[rfHA][47:32] = immu16;
} else {
  rf[rfHA][63:48] = immu16;
}
```
<!-- IDL:set.w_rwii_rf END -->

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `andn.w` | `rwii` | `rb` | `andn.w rbHA, wpN, immu16` | `andn.w_rwii_rb` |
| `andn.w` | `rwii` | `rd` | `andn.w rdHA, wpN, immu16` | `andn.w_rwii_rd` |
| `or.w` | `rwii` | `rb` | `or.w rbHA, wpN, immu16` | `or.w_rwii_rb` |
| `or.w` | `rwii` | `rd` | `or.w rdHA, wpN, immu16` | `or.w_rwii_rd` |
| `set.ow` | `rwii` | `rd` | `set.ow rdHA, wpN, immu16` | `set.ow_rwii_rd` |
| `set.w` | `rwii` | `rf` | `set.w rfHA, wpN, immu16` | `set.w_rwii_rf` |
| `set.zw` | `rwii` | `rb` | `set.zw rbHA, wpN, immu16` | `set.zw_rwii_rb` |
| `set.zw` | `rwii` | `rd` | `set.zw rdHA, wpN, immu16` | `set.zw_rwii_rd` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `andn.w_rwii_rd`, `or.w_rwii_rd`, `set.ow_rwii_rd`, `set.zw_rwii_rd`（4 条）
* `dst_rb0`：目的 rb0 → ILLI — `andn.w_rwii_rb`, `or.w_rwii_rb`, `set.zw_rwii_rb`（3 条）

**无附加合法性规则：**
* `set.w_rwii_rf`
<!-- LEGALITY_END -->
