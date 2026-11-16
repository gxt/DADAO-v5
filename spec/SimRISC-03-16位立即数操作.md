# SimRISC16位立即数操作指令

> **版本：0.5.7-rc**（与 SimRISC-00 一致）
> **分类：16位立即数操作** — set.zw/set.ow/set.w/or.w/andn.w（rwii 格式）
> **伪指令**：`set.rd`/`set.rb`/`set.ft`/`set.fo` 见 `Toolchain-01 §6.2`。

## 1. 立即数常数赋值：RD 组

本章为 `rd` 寄存器组的 16 位立即数设置类指令（`rb` 组见 §2、`rf` 组见 §3）。

立即数设置类指令直接用立即数对寄存器内的不同wyde进行赋值、或、与非、零扩展赋值。
由于立即数域为16位，因此，需要指定具体的wyde的位置，分别采用 `wp3/wp2/wp1/wp0`，对应 `MSW..LSW`。

操作数类型为 `rwii`，指令如下：

```simrisc
set.ow   rdHA, wpN, immu16
set.zw   rdHA, wpN, immu16
or.w     rdHA, wpN, immu16
andn.w   rdHA, wpN, immu16
```

由于rd寄存器为64位，而set.ow/set.zw指令只设置了其中16位，两者的区别在于set.ow指令则将其余48位置1，set.zw指令将其余48位置0。

`or.w` 指令（rwii 格式）：将 `rdHA` 中由 `wpN` 指定的 wyde 替换为 `(rdHA[wyde] | immu16)`，其余 wyde 保持不变。

> **注意**：`or.w` 同时是 OPC-wyde 表的三寄存器逻辑 OR 指令（`or.w rdHB, rdHC, rdHD`），汇编器按操作数格式区分。
`andn.w` 指令：将 `rdHA` 中由 `wpN` 指定的 wyde 替换为 `(rdHA[wyde] & ~immu16)`，其余 wyde 保持不变。

## 2. 立即数常数赋值：RB 组

本章为 `rb` 寄存器组的 16 位立即数设置类指令（无 `set.ow` 变体）。

针对rb寄存器，提供了or.w/andn.w/set.zw指令，操作数类型为 `rwii`，指令如下：

```simrisc
set.zw  rbHA, wpN, immu16
or.w    rbHA, wpN, immu16
andn.w  rbHA, wpN, immu16
```

## 3. 立即数常数赋值：RF 组

本章为 `rf` 寄存器组的 16 位立即数设置类指令（`set.w`）。

针对rf寄存器，SimRISC提供了set.w指令，操作数类型为 `rwii` ，指令如下：

```simrisc
set.w    rfHA, wpN, immu16
```

`set.w` 指令只设置相应的16位，其余48位不变。
因此，32位单精浮点（tetra）需要两条指令设置立即数的值，64位双精浮点（octa）则需要四条指令。

> **注**：`set.w rf0, wpN, immu16` 合法；写入按 SimRISC-00 写语义（`wp2` 命中舍入模式、`wp0` 命中异常状态、`wp1`/`wp3` 完全写无效）。

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
