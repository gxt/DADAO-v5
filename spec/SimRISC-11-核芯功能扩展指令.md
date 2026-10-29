# SimRISC核芯功能扩展指令

> **版本：0.5.6-rc**（与 SimRISC-00 一致）
> **分类：核芯功能扩展** — trap/escape/cfx2rd/cfx2rc/cfxld/cfxst/fence

## 1. 指令域与执行条件

`trap`/`escape`/`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst` 指令可以在任意运行模式下执行，具体是否允许由各核芯功能扩展的 cfx mask 寄存器和指令类型 cfx mask 寄存器控制。详细异常路由规则见 SEE。

核芯功能扩展指令用于访问各核芯功能扩展的寄存器与异常入口，为应用程序提供完备的运行环境，并用于资源管理和状态配置等功能。

一个32位的指令会被分解为5个部分：8/6/6/6/6，即op/ha/hb/hc/hd，其中ha专门用来指定核芯功能扩展编号。

指令中核芯功能扩展编号可以有两种写法：
- `cfx<cfxha>`：直接使用编号，如 `cfx63`、`cfx0`
- `cfx_<cfxname>`：使用名称，如 `cfx_power`、`cfx_umon`

汇编器对两种写法等价处理，均编码为 6 位的 cfxha。

## 2. 陷入指令

陷入指令用于将控制权转移到相应核芯功能扩展的异常向量地址。

操作数类型为：`ciii`

```simrisc
trap    cfxHA, immu18
```

其中，cfx_<cfxname> 指定核芯功能扩展名称；immu18指定具体功能编号。

## 3. 退出指令

退出指令用于退出当前的特权态，将控制权交还给陷入异常前的状态。

操作数类型为：`ciii`

```simrisc
escape  cfxHA, [excp_cause_ip, imms20]
```

其中，cfx_\<cfxname\> 指定核芯功能扩展名称；imms20 指定目标地址偏移（字节，须 `%4==0`；实际地址 = excp_cause_ip + imms20；编码层 `Addr = excp_cause_ip + (imms18 << 2)`）。

## 4. 寄存器传输指令

这类指令用于核芯功能扩展的寄存器与rd寄存器之间进行相互赋值。

操作数类型为：`crrr`

```simrisc
cfx2rd    cfxHA, cgHB, rcHC, rdHD
cfx2rc    cfxHA, cgHB, rcHC, rdHD
```

其中，cfx_<cfxname> 指定核芯功能扩展名称，cgHB和rcHC指定该核芯功能扩展的寄存器组和寄存器号。
cfx2rc 是将 rdHD 的值设置到 cfx_<cfxname>_cgHB_rcHC 中。
cfx2rd 是将 cfx_<cfxname>_cgHB_rcHC 的值设置到 rdHD 中。

读写不存在的 cfx_<cfxname>_cgHB_rcHC 组合时触发 CFXREG 异常；cfx_<cfxname> 为 reserved 核芯功能扩展（7-14、19-61）时触发 ILLI 异常；读写权限不匹配时，触发非法核芯功能扩展寄存器访问异常（CFXREG）。

> **注意**：cfx2rd/cfx2rc 的数据通路仅连接 rd 寄存器组。若需要将 rb 或 rf 寄存器的值写入核芯功能扩展寄存器，须先通过 `rb2rd rd, rb, 1` 或 `rf2rd rd, rf, 1` 中转至 rd 寄存器。汇编器提供 `set.rd rd, rs` 伪指令简化此操作（展开为 `rb2rd`/`rf2rd`/`rd2rd`）。

为简化汇编代码的编写，寄存器传输指令支持一种简化的操作数写法，将 `cfx_<cfxname>, cgHB, rcHC` 三个参数合并为 `cfx_⟨cfxname⟩_regname` 的形式，其中 `regname` 为寄存器名称（即 SEE 文档 regname 列中的名称）。汇编器会根据寄存器名称自动查找对应的 cg 和 rc 编号，展开为标准的三个操作数格式。

```simrisc
@@ 简化写法（推荐）
cfx2rd  cfx_umon_excp_cause_ip, rd2    @@ 读取 cfx_umon 的 excp_cause_ip
cfx2rc  cfx_power_ctrl, rd2             @@ 写入 cfx_power 的 power_ctrl

@@ 等价的标准写法
cfx2rd  cfx_umon, cg5, rc3, rd2
cfx2rc  cfx_power, cg8, rc1, rd2
```

这种简化写法使代码更具可读性，程序员无需记忆每个寄存器的cg和rc编号，直接通过寄存器名称即可定位目标寄存器。

## 5. SRAM块传输指令（待定）

> **待定**（deferred）：本组指令的语义尚未定稿，`cfxld`/`cfxst` 暂不启用。

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

## 6. 屏障指令

屏障指令用于约束本 hart 对所选 cfx 资源域的访问顺序。

操作数类型为：`ciii`

```simrisc
fence   cfxHA, immu18
```

其中，`cfxHA` 指定资源域：

- `cfx0` / `cfx_umon`：表示 **all cfx**（不是只作用于 umon 本地资源）；
- `cfx1`–`cfx63`：表示指定的 cfx。

`immu18` **整体书写，不拆成三段操作数**；其位域为：

| 字段 | 位 | 含义 |
| --- | --- | --- |
| `hb` | `immu18[17:12]` | SBZ，必须为 0 |
| `pred` | `immu18[11:6]` | 前序（predecessor）访问类型掩码 |
| `succ` | `immu18[5:0]` | 后序（successor）访问类型掩码 |

`pred`/`succ` 的位含义相同：

| 位 | 名称 | 访问类型 |
| --- | --- | --- |
| bit0 | `cr` | cfx memory read |
| bit1 | `cw` | cfx memory write |
| bit2 | `ci` | cfx IO input |
| bit3 | `co` | cfx IO output |
| bit4 | `mr` | system memory read |
| bit5 | `mw` | system memory write |

`pred = 0` 且 `succ = 0` 是合法的 no-op。

屏障只保证**本 hart** 对所选 cfx 的对应访问顺序/可见性；不跨 hart，不等待 DMA
完成，也不负责 TLB / icache 维护。

异常规则：

- `hb != 0` ⇒ ILLI；
- `cfxHA` 为保留核芯功能扩展（7–14、19–61）⇒ ILLI；
- 正常屏障不产生异常。

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfx2rc` | `crrr` | `cfx` | `cfx2rc cfxHA, cgHB, rcHC, rdHD` | `cfx2rc_crrr_cfx` |
| `cfx2rd` | `crrr` | `cfx` | `cfx2rd cfxHA, cgHB, rcHC, rdHD` | `cfx2rd_crrr_cfx` |
| `cfxld` | `crii` | `cfx` | `cfxld cfxHA, [rbHB, immu12]` | `cfxld_crii_cfx` |
| `cfxst` | `crii` | `cfx` | `cfxst cfxHA, [rbHB, immu12]` | `cfxst_crii_cfx` |
| `escape` | `ciii` | `cfx` | `escape cfxHA, [excp_cause_ip, imms20]` | `escape_ciii_cfx` |
| `fence` | `ciii` | `cfx` | `fence cfxHA, immu18` | `fence_ciii_cfx` |
| `trap` | `ciii` | `cfx` | `trap cfxHA, immu18` | `trap_ciii_cfx` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `encode_sbz`：SBZ 非零 → ILLI — `fence_ciii_cfx`（1 条）
* `encode_cfx_reserved`：保留 cfx（7-14、19-61）→ ILLI — `fence_ciii_cfx`（1 条）

**decode ILLI（未实现该语义的机器）：**
* `cfxld_crii_cfx`：decode ILLI
* `cfxst_crii_cfx`：decode ILLI
<!-- LEGALITY_END -->
