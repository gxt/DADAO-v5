# SimRISC取数存数指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：取数存数**（38 条）— ld/st/ldm/stm（RD/RB/RA/RF 各形式）

用户态指令

## 存取类指令

装入指令是把数据从存储器带进寄存器中，进行零扩展或符号扩展。存储指令是把寄存器中的数据放入存储器中。

操作数类型有两种，一种为：`rrii`，属于单load/store类型，地址计算公式为基址寄存器 + 立即数。
另一种操作数类型为：`rrri`，属于多load/store类型，地址计算公式为基址寄存器 + 数据寄存器。

### 存取RD寄存器

单load/store类指令如下：

```simrisc
ld.sb    rdha, rbhb, imms12
ld.ub    rdha, rbhb, imms12
ld.sw    rdha, rbhb, imms12
ld.uw    rdha, rbhb, imms12
ld.st    rdha, rbhb, imms12
ld.ut    rdha, rbhb, imms12
ld.o     rdha, rbhb, imms12

st.b     rdha, rbhb, imms12
st.w     rdha, rbhb, imms12
st.t     rdha, rbhb, imms12
st.o     rdha, rbhb, imms12
```

对齐要求：`ld.o`/`st.o` 需 8 字节对齐，`ld.st`/`st.t`/`ld.ut` 需 4 字节对齐，`ld.sw`/`st.w`/`ld.uw` 需 2 字节对齐，`ld.sb`/`st.b`/`ld.ub` 无对齐要求。未对齐触发 MALIGN 异常。

限制：`ld` 指令的 `rdha` 为 `rd0` 时触发 ILLI 异常。（rd0 通用约定见 SimRISC-00）`st` 指令允许 `rdha` 为 `rd0`（rd0 作为源寄存器读出 0）。

多load/store类指令如下：

```simrisc
ldm.sb   rdha, rbhb, rdhc, immu6
ldm.ub   rdha, rbhb, rdhc, immu6
ldm.sw   rdha, rbhb, rdhc, immu6
ldm.uw   rdha, rbhb, rdhc, immu6
ldm.st   rdha, rbhb, rdhc, immu6
ldm.ut   rdha, rbhb, rdhc, immu6
ldm.o    rdha, rbhb, rdhc, immu6

stm.b    rdha, rbhb, rdhc, immu6
stm.w    rdha, rbhb, rdhc, immu6
stm.t    rdha, rbhb, rdhc, immu6
stm.o    rdha, rbhb, rdhc, immu6
```

`ldm/stm`指令处理多个寄存器的读写操作。
`rdha`用来指定第一个寄存器，`rbhb+rdhc`用来指定地址，`immu6`为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。
`ldm/stm`指令存取8位/16位/32位的数据时，每个寄存器只存放一个数据，多个数据分别使用多个连续的寄存器。
例如：`stm.b rd16, rb2, rd0, 8` 是将`rd16 - rd23`这8个连续寄存器中的低8位数据，分别存放到以rb2为基址的8字节连续地址中。

限制如下：

- `ldm` 指令的 `rdha` 为 `rd0` 时触发 ILLI 异常；`stm` 指令允许 `rdha` 为 `rd0`（rd0 作为源寄存器读出 0）
- `immu6` = 0 时触发 ILLI 异常
- `rdha + immu6 > 64`（超出 rd63）时触发 ILLI 异常，不环绕、不截断
- `ldm.o`/`stm.o`（64-bit）需 8 字节地址对齐；`ldm.st`/`stm.t`/`ldm.ut`（32-bit）需 4 字节对齐；`ldm.sw`/`stm.w`/`ldm.uw`（16-bit）需 2 字节对齐；`ldm.sb`/`stm.b`/`ldm.ub`（8-bit）无对齐要求。未对齐将触发 MALIGN 异常
- 当多寄存器读写的范围包括`rdhc`时，地址计算仍然按照原始的`rdhc`中的数据进行
- 装入类指令的源寄存器范围与目的寄存器范围可以重叠。硬件按序号递增逐对处理，每对先读后写。重叠时行为依赖顺序，使用者应避免在同一寄存器同时出现在源和目的中

### 存取RB寄存器

RB寄存器都是64位，因此不需要指定数据长度，共有4条指令如下：

```simrisc
ld.o     rbha, rbhb, imms12
st.o     rbha, rbhb, imms12

ldm.o    rbha, rbhb, rdhc, immu6
stm.o    rbha, rbhb, rdhc, immu6
```

限制如下：

- `ld.o`/`st.o` 和 `ldm.o`/`stm.o` 均需 8 字节地址对齐，未对齐触发 MALIGN 异常
- `ld.o`/`ldm.o` 指令的 `rbha` 为 `rb0` 时触发 ILLI 异常（rb0 通用约定见 SimRISC-00）；`st.o`/`stm.o` 指令允许 `rbha` 为 `rb0`（rb0 作为源寄存器读出 0）
- `immu6` = 0 时触发 ILLI 异常
- `rbha + immu6 > 64`（超出 rb63）时触发 ILLI 异常
- 源和目的寄存器范围可以重叠。硬件按序号递增逐对处理，每对先读后写。重叠时行为依赖顺序，使用者应避免在同一寄存器同时出现在源和目的中
- 当多寄存器读写的范围包括`rbhb`时，地址计算仍然按照原始的`rbhb`中的数据进行

### 存取RA寄存器

RA寄存器都是64位，共有4条指令如下：

```simrisc
ld.o     raha, rbhb, imms12
st.o     raha, rbhb, imms12

ldm.o    raha, rbhb, rdhc, immu6
stm.o    raha, rbhb, rdhc, immu6
```

限制如下：

- `ld.o`/`st.o` 和 `ldm.o`/`stm.o` 均需 8 字节地址对齐，未对齐触发 MALIGN 异常
- `raha` 为 `ra0` 时不触发异常（ra0 可读写）
- `immu6` = 0 时触发 ILLI 异常
- `raha + immu6 > 64` 时触发 ILLI 异常（超出 ra63）

### 存取RF寄存器

RF寄存器分为tetra和octa两种情况，tetra为32位，octa为64位，对应单精和双精两种情况，共有8条指令如下：

```simrisc
ld.t    rfha, rbhb, imms12
st.t    rfha, rbhb, imms12
ld.o    rfha, rbhb, imms12
st.o    rfha, rbhb, imms12

ldm.t   rfha, rbhb, rdhc, immu6
stm.t   rfha, rbhb, rdhc, immu6
ldm.o   rfha, rbhb, rdhc, immu6
stm.o   rfha, rbhb, rdhc, immu6
```

对齐要求：`ld.o`/`st.o`/`ldm.o`/`stm.o` 需 8 字节对齐，`ld.t`/`st.t`/`ldm.t`/`stm.t` 需 4 字节对齐。未对齐触发 MALIGN 异常。

限制如下：

- `immu6` = 0 时触发 ILLI 异常
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
- `rfha + immu6 > 64`（超出 rf63）时触发 ILLI 异常

> **注**：rf0 为目的寄存器时的特殊行为见 SimRISC-00（rf0 = FCSR，写只读位时静默忽略，rw 位正常写入）。