# SimRISC系统类指令

> **版本：0.4.1**（与 SimRISC-00 一致）

## 空指令

当指令地址需要对齐或特意留出空白时，需要使用到空指令。

通常需要填空的是no-operation指令；虽然很多指令也具有no-operation的效果，但是一条专门的指令在编码和语义上更为直观。
SimRISC中，借鉴Knuth的创意，采用了swym助记符作为“划水”指令。

Swym一词参考Knuth的MMIX中的定义，含义为：sympathize with your machinery，Knuth是这样描述的：

> It does, however, keep the machine runnning smoothly, just as real-world swimming helps to keep programmers healthy.

此外，还有一些情况，是不希望指令流运行到这部分空白指令处，此时，需要的是能够引发异常的未定义指令。
SimRISC中，采用了unimp助记符作为未实现指令，即unimplemented instructions。

swym指令的操作数类型为 `iiii`，unimp指令的操作数类型为 `oiii`：

```simrisc
swym    0

unimp   0
```

说明如下：

- swym指令的后24位立即数并无特殊含义，用户可自行定义以用于语义的区分
- unimp指令的后18位立即数并无特殊含义
- swym 除 PC 自增外无任何架构副作用，等同于其他指令系统中的 nop 指令（汇编器提供 `nop` 伪指令，等价于 `swym 0`）
- unimp指令会引发非法指令异常。unimp 的 opcode 为 MISC-Norm 000-000，编码为全零时即为 32 位全零指令字。因此未初始化的指令内存（全零）将触发 ILLI 异常，便于在程序跑飞时快速捕获错误。

## 特权指令

用户态指令用于提供一个完备的应用程序运行环境，特权态指令用来进行资源管理和状态配置等功能。

特权态指令和用户态指令的指令域说明相类似。
一个32位的指令会被分解为5个部分：8/6/6/6/6，即op/ha/hb/hc/hd，其中ha专门用来指定核芯功能扩展编号。

指令中核芯功能扩展编号可以有两种写法：
- `cfx<cfxcode>`：直接使用编号，如 `cfx63`、`cfx0`
- `cfx_<cfxname>`：使用名称，如 `cfx_power`、`cfx_umon`

汇编器对两种写法等价处理，均编码为 6 位的 cfxcode。

除trap指令外，用户模式或监狱模式下执行其它特权指令，都会触发非法指令异常。

### 陷入指令

陷入指令用于将控制权转移到相应核芯功能扩展的异常向量地址。

操作数类型为：`ciii`

```simrisc
trap    cfx_<cfxname>, immu18
```

其中，cfx_<cfxname>指定核芯功能扩展名称；immu18指定具体功能编号。

### 退出指令

退出指令用于退出当前的特权态，将控制权交还给陷入异常前的状态。

操作数类型为：`ciii`

```simrisc
escape  cfx_<cfxname>, imms18
```

其中，cfx_<cfxname>指定核芯功能扩展名称；imms18指定目标地址偏移（指令字偏移，实际地址 = excp_cause_ip + (imms18 << 2)）。

### 寄存器传输指令

这类指令用于核芯功能扩展的寄存器与rd寄存器之间进行相互赋值。

操作数类型为：`crrr`

```simrisc
cfx2rd    cfx_<cfxname>, cghb, rchc, rdhd
cfx2rc    cfx_<cfxname>, cghb, rchc, rdhd
```

其中，cfx_<cfxname>指定核芯功能扩展名称，cghb和rchc指定该核芯功能扩展的寄存器组和寄存器号。
cfx2rc 是将 rdhd 的值设置到 cfx_<cfxname>_cghb_rchc 中。
cfx2rd 是将 cfx_<cfxname>_cghb_rchc 的值设置到 rdhd 中。

读写不存在的 cfx_<cfxname>_cghb_rchc 组合时触发 CFXREG 异常；cfx_<cfxname> 为 reserved 核芯功能扩展（7-14、19-61）时触发 ILLI 异常；读写权限不匹配时，触发非法核芯功能扩展寄存器访问异常（CFXREG）。

> **注意**：cfx2rd/cfx2rc 的数据通路仅连接 rd 寄存器组。若需要将 rb 或 rf 寄存器的值写入核芯功能扩展寄存器，须先通过 `setrd rdxx, rbyy` 或 `setrd rdxx, rfyy` 中转至 rd 寄存器。

为简化汇编代码的编写，寄存器传输指令支持一种简化的操作数写法，将 `cfx_<cfxname>, cghb, rchc` 三个参数合并为 `cfx_⟨cfxname⟩_regname` 的形式，其中 `regname` 为寄存器名称（即 SEE 文档 regname 列中的名称）。汇编器会根据寄存器名称自动查找对应的 cg 和 rc 编号，展开为标准的三个操作数格式。

```simrisc
; 简化写法（推荐）
cfx2rd  cfx_umon_excp_cause_ip, rd2    ; 读取 cfx_umon 的 excp_cause_ip
cfx2rc  cfx_power_ctrl, rd2             ; 写入 cfx_power 的 power_ctrl

; 等价的标准写法
cfx2rd  cfx_umon, 5, 3, rd2
cfx2rc  cfx_power, 8, 1, rd2
```

这种简化写法使代码更具可读性，程序员无需记忆每个寄存器的cg和rc编号，直接通过寄存器名称即可定位目标寄存器。

### SRAM块传输指令

这类指令用于核芯功能扩展的内部存储与内存之间的块传输，要求 64 字节对齐，并且是 64 字节的倍数。

操作数类型为：`crii`

```simrisc
cfxld    cfx_<cfxname>, rbhb, immu12
cfxst    cfx_<cfxname>, rbhb, immu12
```

其中：
- cfx_<cfxname> 指定核芯功能扩展名称。
- rbhb 指定内存地址，要求 64 字节对齐。
- 传输长度 = immu12 × 64 字节。
- 内部存储侧的目标块由 `cfx_⟨cfxname⟩_sram_block_sel`（cg7 rc0）选择，块内起始偏移由 `cfx_⟨cfxname⟩_sram_addr`（cg7 rc1）指定。`cfx_⟨cfxname⟩_sram_addr` 及内存侧 `rbhb` 均需 64 字节对齐。
- cfxld：将内存数据传输到核芯功能扩展的内部存储中。
- cfxst：将核芯功能扩展的内部存储数据传输到内存中。
- 若 cfx_<cfxname> 为 reserved 核芯功能扩展（7-14、19-61），触发 ILLI 异常。

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

操作数类型为：`orrr`。lro 指令的 hb（rdhb）固定为 rd0，汇编代码仅需两个操作数。若手工编码时 hb ≠ 0，触发 ILLI 异常。

```simrisc
lro_nn   rdhc, rbhd
lro_an   rdhc, rbhd
lro_nr   rdhc, rbhd
lro_ar   rdhc, rbhd

sco_nn   rdhb, rdhc, rbhd
sco_an   rdhb, rdhc, rbhd
sco_nr   rdhb, rdhc, rbhd
sco_ar   rdhb, rdhc, rbhd
```

o是 octa 的缩写，表示存取的数据是64位。
a是 acquire 的缩写，表示该指令后序所有访问存储的指令不得被重排到该指令之前执行。
r是 release 的缩写，表示该指令前序所有访问存储的指令不得被重排到该指令之后执行。
n表示没有对应的a或r的顺序限制。

lro 指令是从内存地址 rbhd 中加载内容到 rdhc 寄存器，然后在 rbhd 对应地址上设置保留标记（reservation set）。
sco 指令会先判断 rbhd 内存地址是否有设置保留标记，如果设置了，则把 rdhc 值正常写入到 rbhd 内存地址里，并把 rdhb 寄存器设置成 0，表示写入成功；如果 rbhd 内存地址没有设置保留标记，则不执行写入操作，并把 rdhb 寄存器设置成 1， 表示写入失败；不管成功还是失败，sco 指令都会把当前 hart 上的所有保留标记全部清除。

对于 lro/sco 指令，要求 rbhd 寄存器中的地址是按数据宽度对齐的，即8字节对齐，否则会触发 MALIGN 异常。

> **保留机制**（参考 RISC-V RV64A）：一条 lro 指令在 hart 上设置保留标记。sco 指令在保留标记仍在时写入内存并返回 0，否则不写入并返回非 0 值。sco 可能偶发性失败（spurious failure），软件应在循环中重试。以下事件清除 hart 上的保留标记：另一 hart 对保留地址的 store（或另一 hart 对保留地址所在 cache line 的 store，取决于平台实现的保留粒度）、当前 hart 执行另一条 lro 指令、异常或中断进入。如果 hart 在 lro 和 sco 之间执行了异常处理程序，sco 必定失败。保留标记的粒度由平台定义（可实现为精确地址或 cache line）。
