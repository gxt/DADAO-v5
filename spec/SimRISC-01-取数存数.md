# SimRISC取数存数指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：取数存数**（38 条）— ld/st/ldm/stm（RD/RB/RA/RF 各形式）

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 取数存数（38 条）

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

用户态指令

## 存取类指令

装入指令是把数据从存储器带进寄存器中，进行零扩展或符号扩展。存储指令是把寄存器中的数据放入存储器中。

操作数类型有两种，一种为：`rrii`，属于单load/store类型，地址计算公式为基址寄存器 + 立即数。
另一种操作数类型为：`rrri`，属于多load/store类型，地址计算公式为基址寄存器 + 数据寄存器。

### 存取RD寄存器

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
- 当多寄存器读写的范围包括`rdHC`时，地址计算仍然按照原始的`rdHC`中的数据进行
- 装入类指令的源寄存器范围与目的寄存器范围可以重叠。硬件按序号递增逐对处理，每对先读后写。重叠时行为依赖顺序，使用者应避免在同一寄存器同时出现在源和目的中

### 存取RB寄存器

RB寄存器都是64位，因此不需要指定数据长度，共有4条指令如下：

```simrisc
ld.o     rbHA, [rbHB, imms12]
st.o     rbHA, [rbHB, imms12]

ldm.o    {rbHA:rbHA+immu6-1}, [rbHB, rdHC]
stm.o    {rbHA:rbHA+immu6-1}, [rbHB, rdHC]
```

限制如下：

- `ld.o`/`st.o` 和 `ldm.o`/`stm.o` 均需 8 字节地址对齐，未对齐触发 MALIGN 异常
- `ld.o`/`ldm.o` 指令的 `rbHA` 为 `rb0` 时触发 ILLI 异常（rb0 通用约定见 SimRISC-00）；`st.o`/`stm.o` 指令允许 `rbHA` 为 `rb0`（rb0 作为源寄存器读出 0）
- `immu6` = 0 时触发 ILLI 异常
- `rbHA + immu6 > 64`（超出 rb63）时触发 ILLI 异常
- 源和目的寄存器范围可以重叠。硬件按序号递增逐对处理，每对先读后写。重叠时行为依赖顺序，使用者应避免在同一寄存器同时出现在源和目的中
- 当多寄存器读写的范围包括`rbHB`时，地址计算仍然按照原始的`rbHB`中的数据进行

### 存取RA寄存器

RA寄存器都是64位，共有4条指令如下：

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

### 存取RF寄存器

RF寄存器分为tetra和octa两种情况，tetra为32位，octa为64位，对应单精和双精两种情况，共有8条指令如下：

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

> **注**：rf0 为目的寄存器时的特殊行为见 SimRISC-00（rf0 = FCSR，写只读位时静默忽略，rw 位正常写入）。