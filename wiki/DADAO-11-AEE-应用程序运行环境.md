# DADAO Application Execution Environment

> **版本：0.9.2**（与 ABI 版本号一致，同步更新。基于 SimRISC 0.5.3 指令系统设计）

应用程序运行环境：Application Execution Environment

## 数据表示、寄存器模型、浮点状态寄存器、返回地址栈

详见 SimRISC-00 §数据表示、§寄存器、§浮点状态寄存器、§返回地址栈。

## 不同宽度数据的运算处理

SimRISC 提供 8/16/32/64-bit 四种位宽的运算指令（如 add.ub/add.uw/add.ut/add.uo）。小于 64-bit 的数据在 64-bit 寄存器中采用符号扩展或零扩展存储，运算后的低 N（N=8/16/32）位即为对应宽度的正确结果。

### 8/16/32 位运算

从内存加载时，`ld.sb`/`ld.ub`（8-bit）、`ld.sw`/`ld.uw`（16-bit）、`ld.st`/`ld.ut`（32-bit）分别完成符号扩展或零扩展至 64-bit。存储时，`st.b`/`st.w`/`st.t` 截取低 N 位写入内存。

**加减法**：结果产生 128-bit（rdha = 高 64 位，rdhb = 低 64 位），低 N 位天然正确。若不需要高 64 位，可将 `rdha` 设为 `rd0` 丢弃。

```simrisc
; 有符号 32-bit 加法
ld.st    rd2, rbsp, x_offset          ; 符号扩展加载
ld.st    rd3, rbsp, y_offset
add.so  rd0, rd4, rd2, rd3           ; rd4 = 低64位；rd0丢弃高64位
st.t     rd4, rbsp, z_offset
```

**乘除法**：乘法结果为 128-bit（`rdha` = 高 64 位，`rdhb` = 低 64 位）。32-bit 乘积取低 64 位即可。除法前须确保被除数和除数的高位正确扩展。

```simrisc
; 有符号 32-bit 乘法
ld.st    rd2, rbsp, x_offset
ld.st    rd3, rbsp, y_offset
mul.so    rd0, rd4, rd2, rd3           ; rd0丢弃高64位，rd4=低64位
st.t     rd4, rbsp, z_offset

; 有符号 32-bit 除法
ld.st    rd2, rbsp, x_offset
ld.st    rd3, rbsp, y_offset
div.st  rd4, rd2, rd3           ; 商写入目的寄存器 rd4
st.t     rd4, rbsp, z_offset
```

> 若操作数经过加减乘等运算后高位被污染，除法和乘法前需 `ext.s` 重新扩展。

**移位**：`shr.u` 逻辑右移高位补 0，`shr.s` 算数右移高位补符号位。

```simrisc
; 无符号 32-bit 右移 3 位
ld.ut    rd2, rbsp, x_offset          ; 零扩展加载
shr.uo  rd2, rd2, 3

; 有符号 32-bit 右移 3 位
ld.st    rd2, rbsp, x_offset          ; 符号扩展加载
shr.so  rd2, rd2, 3
```

**溢出**：

- 8/16/32-bit 运算的溢出需软件自行判断。SimRISC 无硬件溢出标志。
- N-bit 有符号溢出检测：将结果做 N-bit 符号扩展后与原值比较，不相等即溢出。

```simrisc
; 有符号 32-bit 加法，检测溢出
add.so  rd0, rd3, rd4, rd5           ; rd3 = rd4 + rd5（低 64 位）
ext.so  rd2, rd3, 31           ; rd2 = rd3 按 32-bit 符号扩展
cmp.so  rd2, rd2, rd3          ; 比较扩展值与原值
br.nz    rd2, overflow_handler        ; 不相等 → 32-bit 溢出
```

## 地址空间布局

应用程序建议使用不超过 32 个 PTBR，按需申请而非一次性分配。各 PTBR 按用途划分独立的虚拟地址空间区域：

| PTBR | 用途 | TLB 切换行为 |
|------|------|:--:|
| 0-15 | 进程私有：代码、数据、栈、堆、备用 | invalid |
| 16-31 | 共享库、动态链接、内核映射、共享内存 | **保留** |

进程切换时，仅 invalid 进程私有的 PTBR 对应的 TLB 集合。标记为"保留"的 PTBR 对应的 TLB 集合不做无效化处理，从而避免共享代码和内核映射的 TLB 抖动。

```simrisc
; 进程切换示例：invalid 已申请的私有 PTBR（最多 16 个）
set.rd   rd2, 0                     ; 循环变量
cfx_tlb_inv_loop:
    ; 仅 invalid PTBR 0-15
    shl.uo  rd3, rd2, 42              ; rd3 = PTBR 索引 << 42（构造 addr_start，VA[47:42]=PTBR 编号）
    cfx2rc  cfx_tlb_addr_start, rd3
    set.rd   rd3, 0x40000000000     ; 0x40000000000（2^42） = 集合内全部 VA 空间
    cfx2rc  cfx_tlb_addr_size, rd3
    set.rd   rd4, 2                 ; bit1 = invalid by addr range
    cfx2rc  cfx_tlb_control, rd4
    add.si    rd2, 1
    set.rd   rd3, 16
    cmp.so  rd5, rd2, rd3          ; rd5 = rd2 < rd3 ?
    br.n     rd5, cfx_tlb_inv_loop
```

## 汇编兼容性

汇编器应提供以下兼容性支持：

### 指导符（directives）

由于历史原因，汇编器中的word的定义并不一致，因此，Dadao采用了Knuth的MMIX中的数据长度定义，并在汇编器中额外定义了4个指导符：

- `.dd.b08`：8位数据，1个字节
- `.dd.w16`：16位数据，2个字节
- `.dd.t32`：32位数据，4个字节
- `.dd.o64`：64位数据，8个字节

注意：Dadao中的octa含义和gas中的.octa定义不一致。
Dadao中的octa是64位，即8字节，而gas中的.octa定义的数据是16字节（octa-word，而每个word是2字节）。
因此，不建议使用gas中的.octa。

### 汇编器选项

除了通用的选项之外，Dadao添加了以下选项：

- -multiple-to-single：将多寄存器指令转换为一系列的单寄存器指令；转换过程保持助记符（即opcode）不变
