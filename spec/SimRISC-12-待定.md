# SimRISC待定指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：待定** — cfxld/cfxst

## 1. SRAM块传输指令

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

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfxld` | `crii` | `cfx` | `cfxld cfxHA, [rbHB, immu12]` | `cfxld_crii_cfx` |
| `cfxst` | `crii` | `cfx` | `cfxst cfxHA, [rbHB, immu12]` | `cfxst_crii_cfx` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

**decode ILLI（未实现该语义的机器）：**
* `cfxld_crii_cfx`：decode ILLI
* `cfxst_crii_cfx`：decode ILLI
<!-- LEGALITY_END -->
