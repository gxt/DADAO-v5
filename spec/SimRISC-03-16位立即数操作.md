# SimRISC16位立即数操作指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：16位立即数操作**（8 条）— set.zw/set.ow/set.w/or.w/andn.w（rwii 格式）

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 16位立即数操作（8 条）

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
## 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `andn.w_rwii_rd`, `or.w_rwii_rd`, `set.ow_rwii_rd`, `set.zw_rwii_rd`（4 条）
* `dst_rb0`：目的 rb0 → ILLI — `andn.w_rwii_rb`, `or.w_rwii_rb`, `set.zw_rwii_rb`（3 条）

**scope: fp（decode ILLI，未实现）：**
* `set.w_rwii_rf`：decode ILLI
<!-- LEGALITY_END -->


## 立即数常数赋值：Immediate constant

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

> **注意**：`or.w` 同时是 MISC-wyde 表的三寄存器逻辑 OR 指令（`or.w rdHB, rdHC, rdHD`），汇编器按操作数格式区分。
`andn.w` 指令：将 `rdHA` 中由 `wpN` 指定的 wyde 替换为 `(rdHA[wyde] & ~immu16)`，其余 wyde 保持不变。

针对rb寄存器，提供了or.w/andn.w/set.zw指令，操作数类型为 `rwii`，指令如下：

```simrisc
set.zw  rbHA, wpN, immu16
or.w    rbHA, wpN, immu16
andn.w  rbHA, wpN, immu16
```

针对rf寄存器，SimRISC提供了set.w指令，操作数类型为 `rwii` ，指令如下：

```simrisc
set.w    rfHA, wpN, immu16
```

`set.w` 指令只设置相应的16位，其余48位不变。
因此，32位单精浮点（tetra）需要两条指令设置立即数的值，64位双精浮点（octa）则需要四条指令。

> **注**：`set.w rf0, wpN, immu16` 合法；写入按 SimRISC-00 写语义（`wp2` 命中舍入模式、`wp0` 命中异常状态、`wp1`/`wp3` 完全写无效）。

#### set.rd 伪指令

`set.rd` 不是硬件指令，而是汇编器提供的伪指令，用于将任意 64 位立即数加载到 rd 寄存器。汇编器将 `set.rd` 展开为 1~4 条 rwii 格式指令。

**策略**：先通过 `set.ow` 或 `set.zw` 设置一个 wyde 的初始值（同时确定其余位的状态：`set.ow` 置 1、`set.zw` 清 0），再用 `or.w` 和 `andn.w` 修正剩余 wyde。

> **重要**：`set.zw`/`set.ow` 会改变所有 64 位，不能连续使用多条来设置不同 wyde——后一条会覆盖前一条的结果。只能使用**一条** `set.zw` 或 `set.ow` 作为第一条指令，后续必须用 `or.w`（设 1）或 `andn.w`（清 0）逐 wyde 修正。

**常用模式示例**：

```simrisc
; 加载零 → set.zw 即可覆盖全 64 位
set.rd   rd1, 0                     ; 展开为 set.zw rd1, wp0, 0

; 加载全 1（-1）→ set.ow 一条指令全 64 位置 1
set.rd   rd1, -1                    ; 展开为 set.ow rd1, wp0, 0xFFFF

; 加载负数（利用 set.ow 将其余 48 位置 1 的特性，自动完成符号扩展）
set.rd   rd1, -42                   ; 展开为 set.ow rd1, wp0, 0xFFD6  (-42 的低 16 位)

; 加载位掩码（高位全 1 的低 16 位掩码）
set.rd   rd1, 0xFFFFFFFFFFFFFFF0    ; 展开为 set.ow rd1, wp0, 0xFFF0

; 加载 ~(1<<n) → set.ow 一条指令
set.rd   rd1, ~(1<<5)              ; 展开为 set.ow rd1, wp0, 0xFFDF

; 加载小正数（16 位以内）→ wp0 一条指令
set.rd   rd1, 42                    ; 展开为 set.zw rd1, wp0, 42
set.rd   rd1, 0x1234ABCD            ; 展开为：
                                    ;   set.zw rd1, wp1, 0x1234
                                    ;   or.w   rd1, wp0, 0xABCD

; 加载 64 位常数 → 分 4 个 wyde 依次设置
set.rd   rd1, 0xDEADBEEF_CAFEBABE  ; 展开为：
                                    ;   set.zw rd1, wp3, 0xDEAD
                                    ;   or.w   rd1, wp2, 0xBEEF
                                    ;   or.w   rd1, wp1, 0xCAFE
                                    ;   or.w   rd1, wp0, 0xBABE
```

**展开规则**：任意 64 位立即数最多 4 条指令即可实现（每 wyde 至多一条）。汇编器应优先选择指令数最少的展开方案，推荐策略：

1. 若 64 位全同（全 0 或全 1），1 条 `set.zw`/`set.ow`。
2. 若连续 wyde 值相同（如高 48 位全 0），填充初始 wyde 后 `or.w` 补充剩余差异。
3. 一般情况：`set.zw`/`set.ow` 设置一个基数 wyde，其余 wyde 用 `or.w` 设 1、`andn.w` 清 0。

**寄存器传值**：`set.rd rd, rs` 也可用于从 rb、rf、ra 寄存器传值至 rd，汇编器根据源寄存器类型展开为单条块赋值指令：

```simrisc
set.rd   rd5, rb3       ; 展开为 rb2rd {rd5}, {rb3}
set.rd   rd2, rf7       ; 展开为 rf2rd {rd2}, {rf7}
set.rd   rd8, rd3       ; 展开为 rd2rd {rd8}, {rd3}
set.rd   rd4, ra10      ; 展开为 ra2rd {rd4}, {ra10}
```

#### set.rb 伪指令

`set.rb` 是汇编器提供的伪指令，用于将立即数加载到 rb 寄存器，展开为 `set.zw-rb` 和 `or.w-rb` 的组合（rb 无 `set.ow` 变体，无需 `andn.w`）。

> **重要**：`set.zw` 会清零其余所有位，因此不能连续使用多条 `set.zw`。只能使用**一条** `set.zw` 作为第一条指令，后续用 `or.w`（设 1）或 `andn.w`（清 0）逐 wyde 修正。

```simrisc
; 加载零
set.rb   rb1, 0                      ; 展开为 set.zw rb1, wp0, 0

; 加载 48 位地址
set.rb   rb1, 0x123456789ABC         ; 展开为：
                                      ;   set.zw rb1, wp2, 0x1234
                                      ;   or.w  rb1, wp1, 0x5678
                                      ;   or.w  rb1, wp0, 0x9ABC
```

**寄存器传值**：`set.rb rb, rs` 也可用于从 rd 或 rb 寄存器传值至 rb，汇编器根据源寄存器类型展开为单条块赋值指令：

```simrisc
set.rb   rb5, rd3       ; 展开为 rd2rb {rb5}, {rd3}
set.rb   rb2, rb7       ; 展开为 rb2rb {rb2}, {rb7}
```

**注**：rb 高 16 位（bits[63:48]）可用于地址溢出检测。汇编器应优先通过 `set.zw` 加载地址值，利用其清零其余位的特性自动处理高 16 位。

### set.ft / set.fo 伪指令

`set.ft` 和 `set.fo` 是汇编器提供的伪指令，用于将立即数加载到 rf 寄存器，分别对应单精（tetra，32 位）和双精（octa，64 位）浮点格式。伪指令展开为 `set.w` 的组合。

```simrisc
; 加载单精浮点 1.0（0x3F800000）→ 只需设置低 32 位
set.ft   rf1, 0x3F800000             ; 展开为：
                                      ;   set.w rf1, wp1, 0x3F80
                                      ;   set.w rf1, wp0, 0x0000

; 加载双精浮点 1.0（0x3FF0000000000000）
set.fo   rf1, 0x3FF0000000000000     ; 展开为：
                                      ;   set.w rf1, wp3, 0x3FF0
                                      ;   set.w rf1, wp2, 0x0000
                                      ;   set.w rf1, wp1, 0x0000
                                      ;   set.w rf1, wp0, 0x0000

; 加载零 → 将 rd0（恒为 0）赋值给 rf
set.ft   rf1, 0                       ; 展开为 rd2rf {rf1}, {rd0}
set.fo   rf1, 0                       ; 展开为 rd2rf {rf1}, {rd0}
```

**寄存器传值**：`set.ft`/`set.fo` 也可用于从 rd 或 rf 寄存器传值至 rf，汇编器展开为 `rd2rf` 或 `ft2ft`/`fo2fo`：

```simrisc
set.ft   rf1, rd5       ; 展开为 rd2rf {rf1}, {rd5}
set.ft   rf1, rf2       ; 展开为 ft2ft {rf1}, {rf2}
set.fo   rf2, rf7       ; 展开为 fo2fo {rf2}, {rf7}
```

**注**：加载全零时汇编器自动使用 `rd2rf` 从 `rd0` 拷贝。