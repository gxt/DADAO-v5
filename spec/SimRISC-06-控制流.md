# SimRISC控制流指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：控制流**（15 条）— br.*/call/jump/ret

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 控制流（15 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `br.eq` | `rrii` | `rd` | `br.eq {rdHA, rdHB}?, [rb0, imms12i]` | `br.eq_rrii_rd` |
| `br.n` | `riii` | `rd` | `br.n {rdHA}?, [rb0, imms18i]` | `br.n_riii_rd` |
| `br.ne` | `rrii` | `rd` | `br.ne {rdHA, rdHB}?, [rb0, imms12i]` | `br.ne_rrii_rd` |
| `br.nn` | `riii` | `rd` | `br.nn {rdHA}?, [rb0, imms18i]` | `br.nn_riii_rd` |
| `br.np` | `riii` | `rd` | `br.np {rdHA}?, [rb0, imms18i]` | `br.np_riii_rd` |
| `br.nz` | `riii` | `rb` | `br.nz {rbHA}?, [rb0, imms18i]` | `br.nz_riii_rb` |
| `br.nz` | `riii` | `rd` | `br.nz {rdHA}?, [rb0, imms18i]` | `br.nz_riii_rd` |
| `br.p` | `riii` | `rd` | `br.p {rdHA}?, [rb0, imms18i]` | `br.p_riii_rd` |
| `br.z` | `riii` | `rb` | `br.z {rbHA}?, [rb0, imms18i]` | `br.z_riii_rb` |
| `br.z` | `riii` | `rd` | `br.z {rdHA}?, [rb0, imms18i]` | `br.z_riii_rd` |
| `call` | `iiii` | `ra` | `call [rb0, imms24i]` | `call_iiii_ra` |
| `call` | `rrii` | `ra` | `call [rbHA, rdHB, imms12i]` | `call_rrii_ra` |
| `jump` | `iiii` | `rb` | `jump [rb0, imms24i]` | `jump_iiii_rb` |
| `jump` | `rrii` | `rb` | `jump [rbHA, rdHB, imms12i]` | `jump_rrii_rb` |
| `ret` | `riii` | `ra` | `ret rdHA, imms18` | `ret_riii_ra` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 合法性检查

* `excp_ialign`（动态）：PC[1:0]≠0 → IALIGN
* `excp_rasof`（动态）：RAS 上溢 → RASOF
* `excp_rasuf`（动态）：RAS 下溢 → RASUF
<!-- LEGALITY_END -->


## 控制流指令

由于SimRISC的指令都是4字节，并且4字节对齐，因此，当采用立即数作为偏移地址参与计算时，都会将其左移2位，以增大该指令可跳转到的地址范围。rb0 读出为当前指令的地址，有效位宽为 48 位，rb0[63:48] 恒为 0。

### 条件跳转指令

条件跳转指令采用的都是相对地址。

第一类跳转指令的操作数类型为：`rrii`。前两个操作数为rd寄存器，根据两个寄存器的值是否相等进行判断，选择是否跳转。

```simrisc
br.eq    {rdHA, rdHB}?, [rb0, imms12i]
br.ne    {rdHA, rdHB}?, [rb0, imms12i]
```

跳转地址计算公式：`Addr = rb0 + (imms12 << 2)`。地址位宽为 48 位，不产生溢出。

> COD P226页指出，br.ne和br.eq这两条指令的占比为7.4%

第二类跳转指令的操作数类型为：`riii`。一个操作数为rd寄存器，根据该寄存器的值进行判断，选择是否跳转。

```simrisc
br.n     {rdHA}?, [rb0, imms18i]
br.nn    {rdHA}?, [rb0, imms18i]
br.z     {rdHA}?, [rb0, imms18i]
br.nz    {rdHA}?, [rb0, imms18i]
br.p     {rdHA}?, [rb0, imms18i]
br.np    {rdHA}?, [rb0, imms18i]
```

跳转地址计算公式：`Addr = rb0 + (imms18 << 2)`。地址位宽为 48 位，不产生溢出。

一个重要的特例是，当rdHA为rd0时，br.z的条件必为真，br.nz的条件必为假。

第三类跳转指令的操作数类型同样为 `riii`，但操作数为rb寄存器，根据rbHA是否为0进行判断：

```simrisc
br.z     {rbHA}?, [rb0, imms18i]
br.nz    {rbHA}?, [rb0, imms18i]
```

跳转地址计算方式与第二类一致。

### 无条件跳转指令

无条件跳转指令既支持相对地址，也支持绝对地址。

支持相对地址的操作数类型为：`iiii`。

```simrisc
jump    [rb0, imms24i]
```

跳转地址计算公式：`Addr = rb0 + (imms24 << 2)`。地址位宽为 48 位，不产生溢出。

支持绝对地址的操作数类型为：`rrii`

```simrisc
jump    [rbHA, rdHB, imms12i]
```

跳转地址计算公式：`Addr = rbHA + rdHB + (imms12 << 2)`。**地址位宽为 48 位，不产生溢出。**
其中，ha为基址寄存器，故为rb寄存器；hb为偏移地址，故为rd寄存器。

一个重要的特例是：当ha为rb0时，rdHB + (imms12 << 2)仍然是相对地址跳转。

### 函数调用

函数调用指令与无条件跳转指令类似，既支持相对地址，也支持绝对地址；区别在于函数调用指令会计算返回地址，并压入 `ra63`（RegRAS 栈顶）。`[63:48]` 为递归计数（首次压栈设为 1，递归调用递增），`[47:0]` 为返回地址。压/弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 SimRISC-00 §返回地址栈。

支持相对地址的操作数类型为： `iiii`。

```simrisc
call    [rb0, imms24i]
```

跳转地址计算公式： `Addr = rb0 + (imms24 << 2)`。地址位宽为 48 位，不产生溢出。

支持绝对地址的操作数类型为： `rrii`

```simrisc
call    [rbHA, rdHB, imms12i]
```

跳转地址计算公式：`Addr = rbHA + rdHB + (imms12 << 2)`。**地址位宽为 48 位，不产生溢出。**
其中，ha为基址寄存器，故为rb寄存器；hb为偏移地址，故为rd寄存器。

一个重要的特例是：当ha为rb0时，rdHB + (imms12 << 2)实际上也是相对地址跳转。

### 函数返回

函数返回指令ret从 `ra63`（RegRAS 栈顶）弹出返回地址（`[47:0]` 为返回地址，`[63:48]` 为递归计数），并跳转过去。弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 SimRISC-00 §返回地址栈。

ret指令增加了返回值的赋值功能，操作数类型为 `riii` ，即在函数返回的同时，修改一个rd寄存器的值为18位立即数（符号扩展至64位）；
通常，该寄存器为返回值寄存器，从而可以用一条ret指令实现C语言中的return 0或return -1。
无需设置返回值寄存器时，可以采用ret rd0, 0实现普通的ret指令。

操作数类型为： `riii`

```simrisc
ret     rdHA, imms18
```

#### return 伪指令

`return` 是汇编器提供的伪指令，用于无需设置返回值的函数返回，等价于 `ret rd0, 0`。

```simrisc
return                  ; 展开为 ret rd0, 0
```