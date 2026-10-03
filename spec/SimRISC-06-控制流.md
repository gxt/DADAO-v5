# SimRISC控制流指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：控制流**（15 条）— br.*/call/jump/ret

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 控制流（15 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `br.eq` | `rrii` | `rd` | `br.eq {rdHA, rdHB}?, [rb0, imms14]` | `br.eq_rrii_rd` |
| `br.n` | `riii` | `rd` | `br.n {rdHA}?, [rb0, imms20]` | `br.n_riii_rd` |
| `br.ne` | `rrii` | `rd` | `br.ne {rdHA, rdHB}?, [rb0, imms14]` | `br.ne_rrii_rd` |
| `br.nn` | `riii` | `rd` | `br.nn {rdHA}?, [rb0, imms20]` | `br.nn_riii_rd` |
| `br.np` | `riii` | `rd` | `br.np {rdHA}?, [rb0, imms20]` | `br.np_riii_rd` |
| `br.nz` | `riii` | `rb` | `br.nz {rbHA}?, [rb0, imms20]` | `br.nz_riii_rb` |
| `br.nz` | `riii` | `rd` | `br.nz {rdHA}?, [rb0, imms20]` | `br.nz_riii_rd` |
| `br.p` | `riii` | `rd` | `br.p {rdHA}?, [rb0, imms20]` | `br.p_riii_rd` |
| `br.z` | `riii` | `rb` | `br.z {rbHA}?, [rb0, imms20]` | `br.z_riii_rb` |
| `br.z` | `riii` | `rd` | `br.z {rdHA}?, [rb0, imms20]` | `br.z_riii_rd` |
| `call` | `iiii` | `ra` | `call [rb0, imms26]` | `call_iiii_ra` |
| `call` | `rrii` | `ra` | `call [rbHA, rdHB, imms14]` | `call_rrii_ra` |
| `jump` | `iiii` | `rb` | `jump [rb0, imms26]` | `jump_iiii_rb` |
| `jump` | `rrii` | `rb` | `jump [rbHA, rdHB, imms14]` | `jump_rrii_rb` |
| `ret` | `riii` | `ra` | `ret rdHA, imms18` | `ret_riii_ra` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 合法性检查

* `dst_rd0_nonzero`：ret 目的 rd0 时 imms18≠0 → ILLI — `ret_riii_ra`（1 条）
* `excp_ialign`（动态）：PC[1:0]≠0 → IALIGN
* `excp_rasof`（动态）：RAS 上溢 → RASOF
* `excp_rasuf`（动态）：RAS 下溢 → RASUF
<!-- LEGALITY_END -->


## 控制流指令

由于SimRISC的指令都是4字节，并且4字节对齐，因此，当采用立即数作为偏移地址参与计算时，都会将其左移2位，以增大该指令可跳转到的地址范围。`rb0` 以 **64 位**全宽参与地址计算；计算结果（64 位）**写回 `rb0`**，随后取 **`rb0[47:0]`（低 48 位）**作为下一条待执行指令的地址。

### 条件跳转指令

条件跳转指令采用的都是相对地址。

第一类跳转指令的操作数类型为：`rrii`。前两个操作数为rd寄存器，根据两个寄存器的值是否相等进行判断，选择是否跳转。

```simrisc
br.eq    {rdHA, rdHB}?, [rb0, imms14]
br.ne    {rdHA, rdHB}?, [rb0, imms14]
```

跳转地址计算公式：`Addr = rb0 + (imms12 << 2)`（64 位计算），结果写回 `rb0`，取低 48 位为下一条地址。

> COD P226页指出，br.ne和br.eq这两条指令的占比为7.4%

第二类跳转指令的操作数类型为：`riii`。一个操作数为rd寄存器，根据该寄存器的值进行判断，选择是否跳转。

```simrisc
br.n     {rdHA}?, [rb0, imms20]
br.nn    {rdHA}?, [rb0, imms20]
br.z     {rdHA}?, [rb0, imms20]
br.nz    {rdHA}?, [rb0, imms20]
br.p     {rdHA}?, [rb0, imms20]
br.np    {rdHA}?, [rb0, imms20]
```

跳转地址计算公式：`Addr = rb0 + (imms18 << 2)`（64 位计算），结果写回 `rb0`，取低 48 位为下一条地址。

一个重要的特例是，当rdHA为rd0时，br.z的条件必为真，br.nz的条件必为假。

第三类跳转指令的操作数类型同样为 `riii`，但操作数为rb寄存器，按**整 64 位**判零（与 `-rd` 变体一致；`-rb`/`-rd` 区别仅在寄存器组）：

```simrisc
br.z     {rbHA}?, [rb0, imms20]
br.nz    {rbHA}?, [rb0, imms20]
```

跳转地址计算方式与第二类一致。

### 无条件跳转指令

无条件跳转指令既支持相对地址，也支持绝对地址。

支持相对地址的操作数类型为：`iiii`。

```simrisc
jump    [rb0, imms26]
```

跳转地址计算公式：`Addr = rb0 + (imms24 << 2)`（64 位计算），结果写回 `rb0`，取低 48 位为下一条地址。

支持绝对地址的操作数类型为：`rrii`

```simrisc
jump    [rbHA, rdHB, imms14]
```

跳转地址计算公式：`Addr = rbHA + rdHB + (imms12 << 2)`（64 位计算），结果写回 `rb0`，取低 48 位为下一条地址。`rbHA` **仅读**（不修改）。
其中，ha为基址寄存器，故为rb寄存器；hb为偏移地址，故为rd寄存器。

一个重要的特例是：当ha为rb0时，rdHB + (imms12 << 2)仍然是相对地址跳转。

### 函数调用

函数调用指令与无条件跳转指令类似，既支持相对地址，也支持绝对地址；区别在于函数调用指令会计算返回地址，并压入 `ra63`（RegRAS 栈顶）。`[63:48]` 为递归计数（首次压栈设为 1，递归调用递增），`[47:0]` 为返回地址。压/弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 SimRISC-00 §返回地址栈。

支持相对地址的操作数类型为： `iiii`。

```simrisc
call    [rb0, imms26]
```

跳转地址计算公式： `Addr = rb0 + (imms24 << 2)`（64 位计算），结果写回 `rb0`，取低 48 位为下一条地址。

支持绝对地址的操作数类型为： `rrii`

```simrisc
call    [rbHA, rdHB, imms14]
```

跳转地址计算公式：`Addr = rbHA + rdHB + (imms12 << 2)`（64 位计算），结果写回 `rb0`，取低 48 位为下一条地址。`rbHA` **仅读**（不修改）。
其中，ha为基址寄存器，故为rb寄存器；hb为偏移地址，故为rd寄存器。

一个重要的特例是：当ha为rb0时，rdHB + (imms12 << 2)实际上也是相对地址跳转。

### 函数返回

函数返回指令 `ret` 从返回地址栈（RAS）弹出返回地址并跳转过去。返回地址来源**可能不是 `ra63`**（取决于 RAS 状态），可能触发 **RASUF** 异常。弹栈判定与 `RACNT`/`MRPTR` 的完整流程见 SimRISC-00 §返回地址栈。

ret指令增加了返回值的赋值功能，操作数类型为 `riii` ，即在函数返回的同时，修改一个rd寄存器的值为18位立即数（符号扩展至64位）；
通常，该寄存器为返回值寄存器，从而可以用一条ret指令实现C语言中的return 0或return -1。
无需设置返回值寄存器时，可以采用ret rd0, 0实现普通的ret指令。

**（硬约束）**`ret rdHA, imms18` 中，当 `rdHA == rd0` 时，`imms18` **MUST** 为 0；否则该指令**非法**：汇编期须**硬报错**（LLVM，`Error` 级，汇编失败并返回非零退出码，**不得**降为 warning），运行期执行该非法编码触发 **ILLI** 异常（测试机退出码 `0x88`，QEMU）。

操作数类型为： `riii`

```simrisc
ret     rdHA, imms18
```

#### return 伪指令

`return` 是汇编器提供的伪指令，用于无需设置返回值的函数返回，等价于 `ret rd0, 0`。

```simrisc
return                  ; 展开为 ret rd0, 0
```