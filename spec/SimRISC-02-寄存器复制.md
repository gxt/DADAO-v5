# SimRISC寄存器复制指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：寄存器复制**（18 条）— cs.*/ra2rd/rb2rb/rb2rd/rd2ra/rd2rb/rd2rd/rd2rf/rf2rd

## 赋值类指令

> **立即数常数赋值**（rwii 格式：set.zw/set.ow/set.w/or.w/andn.w 的 rd/rb/rf 形式，以及 set.rd/set.rb/set.ft/set.fo 伪指令）详见 SimRISC-03（16位立即数操作）。

### 寄存器组之间块赋值

不同寄存器组或相同寄存器组之间，可以互相进行块传输，块传输过程中不进行数据类型的转换，保持64位二进制不变，但是必需是多个连续的寄存器。
操作数类型为 `orri`，指令如下：

```simrisc
rd2rd   rdhb, rdhc, immu6

rb2rd   rdhb, rbhc, immu6
rd2rb   rbhb, rdhc, immu6
rb2rb   rbhb, rbhc, immu6

ra2rd   rdhb, rahc, immu6
rd2ra   rahb, rdhc, immu6

rf2rd   rdhb, rfhc, immu6
rd2rf   rfhb, rdhc, immu6
```

以 `rb2rd` 为例，指令语义为，将rbhc开始的immu6个寄存器复制到rdhb开始的immu6个寄存器中。
immu6为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。

限制如下：

- 根据语义，rb/rf/ra之间不能进行直接赋值，ra与ra之间不能进行相互赋值
- `immu6` = 0 时触发 ILLI 异常
- 目的寄存器不可为 0 号寄存器时触发 ILLI 异常（`rdhb` 不可为 `rd0`，`rbhb` 不可为 `rb0`）
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
- 源范围与目的范围有交集时触发 ILLI 异常（即不允许源和目的寄存器范围有任何重叠）

### 条件赋值：Conditional Assignment

第一类条件赋值指令需要先根据`rdha`的内容进行条件判断，然后分别将`rdhc`或`rdhd`赋值给`rdhb`，即 `if (rdha is negative/zero/positive) rdhb = rdhc; else rdhb = rdhd`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.n    rdha, rdhb, rdhc, rdhd
cs.z    rdha, rdhb, rdhc, rdhd
cs.p    rdha, rdhb, rdhc, rdhd
```

第二类条件赋值指令需要先根据`rdha`与`rdhb`是否相等进行条件判断，如果条件成立则将`rdhd`的值赋值给`rdhc`，即 `if (rdha ==/!= rdhb) rdhc = rdhd`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.eq   rdha, rdhb, rdhc, rdhd
cs.ne   rdha, rdhb, rdhc, rdhd
```

> **注**：rd0 目的寄存器约定见 SimRISC-00。

### 浮点条件赋值

第一类浮点条件赋值指令需要先根据`rdha`的内容进行条件判断，然后分别将`rfhc`或`rfhd`赋值给`rfhb`，即 `if (rdha is negative/zero/positive) rfhb = rfhc; else rfhb = rfhd`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.n    rdha, rfhb, rfhc, rfhd
cs.z    rdha, rfhb, rfhc, rfhd
cs.p    rdha, rfhb, rfhc, rfhd
```

第二类浮点条件赋值指令需要先判断`rdha`与`rdhb`是否相等，如果条件成立则将`rfhd`的值赋值给`rfhc`，即 `if (rdha ==/!= rdhb) rfhc = rfhd`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.eq   rdha, rdhb, rfhc, rfhd
cs.ne   rdha, rdhb, rfhc, rfhd
```

此类指令与浮点比较指令配合使用。浮点比较结果存放在 rd 寄存器中：`1`（大于）、`0`（等于）、`-1`（小于）、NaN（unordered）。当比较结果为 NaN 时，`cs.eq` 和 `cs.ne` 均执行 else 分支（NaN ≠ 1 且 NaN ≠ 0）。

若要检测比较结果是否为 1（大于），先将 1 加载到某个 rd 寄存器，再与比较结果做 `cs.eq`；若要检测是否不为 0（不相等），用 `cs.ne` 判断即可。若在已确认结果为正数（通过 `cs.p` 排除 0 和 -1）的前提下需进一步区分正数 1 与 NaN，检查结果是否为 1（bits[63:1]=0 且 bit0=1），否则为 NaN。