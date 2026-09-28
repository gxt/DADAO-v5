# SimRISC其它指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：其它**（6 条）— cfx2rc/cfx2rd/escape/illi/swym/trap

## 占位指令

当指令地址需要对齐或特意留出空白时，需要使用到占位指令。通常需要的占位指令是 no-operation 指令。SimRISC借鉴Knuth的创意，采用了 swym 助记符作为占位指令，可称之为"划水"指令。Swym一词参考Knuth的MMIX中的定义，含义为 sympathize with your machinery，Knuth是这样描述的：

> It does, however, keep the machine runnning smoothly, just as real-world swimming helps to keep programmers healthy.

操作数类型为 `oiii`：

```simrisc
swym    0
```

- `swym 0` 除 PC 自增外无任何架构副作用，等同于其它指令系统中的 nop 指令（汇编器提供 `nop` 伪指令，等价于 `swym 0`）
- `swym N` 可作为硬件时延指令，后18位立即数为时延参数：具体时延由硬件实现确定，其时延约为 `swym 0` 的 N+1 倍。
  - 硬件可设时延上限，N 超过阈值后时延不再增加。
  - 无论 N 取何值，指令仍为单条 32 位指令，不占用额外指令带宽。

#### nop 伪指令

`nop` 是汇编器提供的伪指令，用于占位或对齐，等价于 `swym 0`。

```simrisc
nop                     ; 展开为 swym 0
```

## 非法指令

SimRISC 采用 illi 助记符作为专门的非法指令，即 illegal instruction。

操作数类型为 `oiii`：

```simrisc
illi    0
```

- illi指令会引发 ILLI 异常，即非法指令异常。
- illi指令的后18位立即数并无特殊含义，完全由用户或软件自行定义，用户可通过操作系统的相关机制捕获该异常，并进行功能扩展。
  - 不建议用户或软件捕获并使用其它指令产生的非法指令异常做功能扩展，例如很多指令不允许目的操作数为 rd0，否则就会引发非法指令异常。
- illi 的 opcode 和 minor-opcode 均为全0，当参数也为0时，即为 32 位全零指令字。因此未初始化的指令内存（全零）将触发 ILLI 异常，便于在程序跑飞时快速捕获错误。

## 特权指令

用户态指令用于提供一个完备的应用程序运行环境，特权态指令用来进行资源管理和状态配置等功能。

特权态指令和用户态指令的指令域说明相类似。
一个32位的指令会被分解为5个部分：8/6/6/6/6，即op/ha/hb/hc/hd，其中ha专门用来指定核芯功能扩展编号。

指令中核芯功能扩展编号可以有两种写法：
- `cfx<cfxcode>`：直接使用编号，如 `cfx63`、`cfx0`
- `cfx_<cfxname>`：使用名称，如 `cfx_power`、`cfx_umon`

汇编器对两种写法等价处理，均编码为 6 位的 cfxcode。

trap/escape/cfx2rd/cfx2rc/cfxld/cfxst 指令可以在任意运行模式下执行，具体是否允许由各核芯功能扩展的 cfx mask 寄存器和指令类型 cfx mask 寄存器控制。详细异常路由规则见 SEE §5 异常进入流程。

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

> **注意**：cfx2rd/cfx2rc 的数据通路仅连接 rd 寄存器组。若需要将 rb 或 rf 寄存器的值写入核芯功能扩展寄存器，须先通过 `rb2rd rd, rb, 1` 或 `rf2rd rd, rf, 1` 中转至 rd 寄存器。汇编器提供 `set.rd rd, rs` 伪指令简化此操作（展开为 `rb2rd`/`rf2rd`/`rd2rd`）。

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