# SimRISC待定指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：待定 [deferred]**（12 条）— cfxld/cfxst/fence/lr_*/sc_*/rela.si

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 待定（12 条）｜ **deferred** — 暂不归类，待必须启用时

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfxld` | `crii` | `cfx` | `cfxld cfxHA, [rbHB, immu12]` | `cfxld_crii_cfx` |
| `cfxst` | `crii` | `cfx` | `cfxst cfxHA, [rbHB, immu12]` | `cfxst_crii_cfx` |
| `fence` | `oiii` | `imm` | `fence immu18` | `fence_oiii_imm` |
| `lr_an.o` | `orrr` | `rd` | `lr_an.o rdHC, [rbHD]` | `lr_an.o_orrr_rd` |
| `lr_ar.o` | `orrr` | `rd` | `lr_ar.o rdHC, [rbHD]` | `lr_ar.o_orrr_rd` |
| `lr_nn.o` | `orrr` | `rd` | `lr_nn.o rdHC, [rbHD]` | `lr_nn.o_orrr_rd` |
| `lr_nr.o` | `orrr` | `rd` | `lr_nr.o rdHC, [rbHD]` | `lr_nr.o_orrr_rd` |
| `rela.si` | `riii` | `rb` | `rela.si rbHA, imms18` | `rela.si_riii_rb` |
| `sc_an.o` | `orrr` | `rd` | `sc_an.o rdHB, rdHC, [rbHD]` | `sc_an.o_orrr_rd` |
| `sc_ar.o` | `orrr` | `rd` | `sc_ar.o rdHB, rdHC, [rbHD]` | `sc_ar.o_orrr_rd` |
| `sc_nn.o` | `orrr` | `rd` | `sc_nn.o rdHB, rdHC, [rbHD]` | `sc_nn.o_orrr_rd` |
| `sc_nr.o` | `orrr` | `rd` | `sc_nr.o rdHB, rdHC, [rbHD]` | `sc_nr.o_orrr_rd` |

<!-- ASSEMBLY_LIST_END -->

## 原子指令

### fence指令

fence 指令对外部可见的访存请求,如设备 I/O 和内存访问等进行串行化。

操作数类型为：`oiii`

```simrisc
fence   immu18
```

`fence immu18` 的低 4 位按以下编码定义内存序屏障类型：

| 位 | 含义 | 说明 |
|----|------|------|
| bit0 | IO | 设备 I/O 访问串行化 |
| bit1 | W | 写屏障：前序写对后序写可见 |
| bit2 | R | 读屏障：前序读对后序读/写可见 |
| bit3 | RW | 读写屏障：前序读写对后序读写可见（全屏障） |

bits[17:4] 应为零（SBZ），非零值行为保留。

### LR-SC指令

LR 指令是 Load Reserved 的缩写，读取保留；SC 指令是 Store Conditional 的缩写，条件存储。设计参考 RISC-V RV64A 扩展（A 扩展）。

操作数类型为：`orrr`。lr 指令的 hb（rdHB）固定为 rd0，汇编代码仅需两个操作数。若手工编码时 hb ≠ 0，触发 ILLI 异常。

```simrisc
lr_nn.o   rdHC, [rbHD]
lr_an.o   rdHC, [rbHD]
lr_nr.o   rdHC, [rbHD]
lr_ar.o   rdHC, [rbHD]

sc_nn.o   rdHB, rdHC, [rbHD]
sc_an.o   rdHB, rdHC, [rbHD]
sc_nr.o   rdHB, rdHC, [rbHD]
sc_ar.o   rdHB, rdHC, [rbHD]
```

o是 octa 的缩写，表示存取的数据是64位。
a是 acquire 的缩写，表示该指令后序所有访问存储的指令不得被重排到该指令之前执行。
r是 release 的缩写，表示该指令前序所有访问存储的指令不得被重排到该指令之后执行。
n表示没有对应的a或r的顺序限制。

lr 指令是从内存地址 rbHD 中加载内容到 rdHC 寄存器，然后在 rbHD 对应地址上设置保留标记（reservation set）。
sc 指令会先判断 rbHD 内存地址是否有设置保留标记，如果设置了，则把 rdHC 值正常写入到 rbHD 内存地址里，并把 rdHB 寄存器设置成 0，表示写入成功；如果 rbHD 内存地址没有设置保留标记，则不执行写入操作，并把 rdHB 寄存器设置成 1， 表示写入失败；不管成功还是失败，sc 指令都会把当前 hart 上的所有保留标记全部清除。

对于 lr/sc 指令，要求 rbHD 寄存器中的地址是按数据宽度对齐的，即8字节对齐，否则会触发 MALIGN 异常。

> **保留机制**（参考 RISC-V RV64A）：一条 lr 指令在 hart 上设置保留标记。sc 指令在保留标记仍在时写入内存并返回 0，否则不写入并返回非 0 值。sc 可能偶发性失败（spurious failure），软件应在循环中重试。以下事件清除 hart 上的保留标记：另一 hart 对保留地址的 store（或另一 hart 对保留地址所在 cache line 的 store，取决于平台实现的保留粒度）、当前 hart 执行另一条 lr 指令、异常或中断进入。如果 hart 在 lr 和 sc 之间执行了异常处理程序，sc 必定失败。保留标记的粒度由平台定义（可实现为精确地址或 cache line）。

## PC相对寻址

PC相对寻址指令需要两个源操作数，一个目的操作数；其中一个源操作数为RB0寄存器，即PC值。
操作数类型是 `riii` ，立即数为18位有符号数，虽然有位数限制，但是具有很好的便利性。
由于立即数采用补码的编码方式，无需区分加减操作。
具体指令如下：

```simrisc
rela.si    rbHA, imms18
```

注意，采用这种操作数类型的加法指令，无法判断是否溢出。
由于imms18为有符号数，该加法指令也隐含实现了减法指令。

rela.si指令根据PC的偏移地址计算目标地址。
rela.si指令将一个18位有符号立即数左移12位，得到一个30位的有符号数，接着将PC地址的低12位清零，得到PC所在4KB对齐基地址；
然后将该基地址加上30位的有符号数，就得到了目标地址，最后将目标地址写入rbHA寄存器，**rbHA 的高 16 位保持不变**。

通常的使用场景是先通过rela.si获取一个基地址，然后再通过存取类指令或跳转类指令的偏移地址获取具体变量的地址。
采用rela.si指令可以处理偏移地址在512MB以内的PC相对寻址问题，对于更大范围的PC相对寻址，仍然需要采用显式的rb0参与寻址。

> **注**：rela.si 属于待定分类（deferred），暂列于此。

## SRAM块传输指令

这类指令用于核芯功能扩展的内部存储与内存之间的块传输，要求 64 字节对齐，并且是 64 字节的倍数。

操作数类型为：`crii`

```simrisc
cfxld    cfxHA, [rbHB, immu12]
cfxst    cfxHA, [rbHB, immu12]
```

其中：
- cfx_<cfxname> 指定核芯功能扩展名称。
- rbHB 指定内存地址，要求 64 字节对齐。
- 传输长度 = immu12 × 64 字节。
- 内部存储侧的目标块由 `cfx_⟨cfxname⟩_sram_block_sel`（cg7 rc0）选择，块内起始偏移由 `cfx_⟨cfxname⟩_sram_addr`（cg7 rc1）指定。`cfx_⟨cfxname⟩_sram_addr` 及内存侧 `rbHB` 均需 64 字节对齐。
- cfxld：将内存数据传输到核芯功能扩展的内部存储中。
- cfxst：将核芯功能扩展的内部存储数据传输到内存中。
- 若 cfx_<cfxname> 为 reserved 核芯功能扩展（7-14、19-61），触发 ILLI 异常。
