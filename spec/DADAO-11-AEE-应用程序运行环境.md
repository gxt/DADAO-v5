# DADAO Application Execution Environment

> **版本：0.9.4-rc**（与 ABI 版本号一致，同步更新。基于 SimRISC 0.5.5 指令系统设计）

应用程序运行环境：Application Execution Environment

## 1. 数据表示、寄存器模型、浮点状态寄存器、返回地址栈

详见 SimRISC-00。

## 2. 不同宽度数据的运算处理

SimRISC 提供 8/16/32/64-bit 四种位宽的运算指令（如 add.ub/add.uw/add.ut/add.uo）。小于 64-bit 的数据在 64-bit 寄存器中采用符号扩展或零扩展存储，运算后的低 N（N=8/16/32）位即为对应宽度的正确结果。

### 2.1 8/16/32 位运算

从内存加载时，`ld.sb`/`ld.ub`（8-bit）、`ld.sw`/`ld.uw`（16-bit）、`ld.st`/`ld.ut`（32-bit）分别完成符号扩展或零扩展至 64-bit。存储时，`st.b`/`st.w`/`st.t` 截取低 N 位写入内存。

**加减法**：结果产生 128-bit（rdha = 高 64 位，rdhb = 低 64 位），低 N 位天然正确。若不需要高 64 位，可将 `rdha` 设为 `rd0` 丢弃。

```simrisc
@@ 有符号 32-bit 加法
ld.st rd2, [rb1, x_offset] @@ 符号扩展加载
ld.st rd3, [rb1, y_offset]
add.so {rd0, rd4}, rd2, rd3 @@ rd4 = 低64位；rd0丢弃高64位
st.t rd4, [rb1, z_offset]
```

**移位**：`shr.u` 逻辑右移高位补 0，`shr.s` 算术右移高位补符号位。

```simrisc
@@ 无符号 32-bit 右移 3 位
ld.ut rd2, [rb1, x_offset] @@ 零扩展加载
shr.uo  rd2, rd2, 3

@@ 有符号 32-bit 右移 3 位
ld.st rd2, [rb1, x_offset] @@ 符号扩展加载
shr.so  rd2, rd2, 3
```

**溢出**：

- 8/16/32-bit 运算的溢出需软件自行判断。SimRISC 无硬件溢出标志。
- N-bit 有符号溢出检测：将结果做 N-bit 符号扩展后与原值比较，不相等即溢出。

```simrisc
@@ 有符号 32-bit 加法，检测溢出
add.so {rd0, rd3}, rd4, rd5 @@ rd3 = rd4 + rd5（低 64 位）
ext.so  rd2, rd3, 31           @@ rd2 = rd3 按 32-bit 符号扩展
cmp.so  rd2, rd2, rd3          @@ 比较扩展值与原值
br.nz {rd2}?, [rb0, overflow_handler] @@ 不相等 → 32-bit 溢出
```

## 3. 地址空间布局

地址转换使用单份 PTBR（`cfx_ptw_ptbr`）与 16 位 ASID（`cfx_ptw_tlb_asid`）：进程私有映射按各自的 ASID 区分，共享库/内核映射置为全局页（PTE 的 `G = 1`），在 ASID 之间复用。

进程切换时先按旧 ASID 显式 invalid 其非全局条目，再写入新 ASID；全局页不随进程切换失效，从而避免共享代码和内核映射的 TLB 抖动。

```simrisc
@@ 进程切换示例：先按旧 ASID 失效其全部非全局条目（写 ASID 不隐含失效）
set.rd   rd2, old_asid
cfx2rc  cfx_ptw_tlb_asid, rd2
set.rd   rd4, 0x02                 @@ op=invalid(10)、scope=all(00)、ASID_ANY=0（不碰全局页）
cfx2rc  cfx_ptw_tlb_control, rd4
@@ 再切到新 ASID（全局页跨 ASID 保留）
set.rd   rd2, new_asid
cfx2rc  cfx_ptw_tlb_asid, rd2
```

## 4. 汇编兼容性

汇编器应提供以下兼容性支持：

### 4.1 指导符（directives）

由于历史原因，汇编器中的word的定义并不一致，因此，Dadao采用了Knuth的MMIX中的数据长度定义，并在汇编器中额外定义了4个指导符：

- `.dd.b08`：8位数据，1个字节
- `.dd.w16`：16位数据，2个字节
- `.dd.t32`：32位数据，4个字节
- `.dd.o64`：64位数据，8个字节

注意：Dadao中的octa含义和gas中的.octa定义不一致。
Dadao中的octa是64位，即8字节，而gas中的.octa定义的数据是16字节（octa-word，而每个word是2字节）。
因此，不建议使用gas中的.octa。

### 4.2 汇编器选项

除了通用的选项之外，Dadao添加了以下选项：

- `-multiple-to-single`：将多寄存器指令转换为一系列的单寄存器指令；转换过程保持助记符（即指令名）不变

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.9.4-rc（未发布）

- §3 地址空间布局按单 PTBR + 16 位 ASID 收口：删除「32 个 PTBR / 按 PTBR 划分 TLB 集合」表述，进程切换示例改用 `cfx_ptw_tlb_asid` 与 `cfx_ptw_tlb_control`（op/scope/`ASID_ANY`）；全局页（PTE `G = 1`）跨 ASID 保留。

### 0.9.3（2026-10-26）

- 删除 8/16/32 位运算中的乘除法解释与示例（乘法结果宽度与除法前的 `ext.so` 扩展提示不再单列）。
- 删除 FPEXCP 异常（浮点按 IEEE 754 执行、经 `rf0` 轮询异常状态）。
- 地址空间布局 / 汇编兼容性内容并入本册（职责边界调整）。
- 与上游 SimRISC 0.5.5 基线对齐。
- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- 汇编格式迁移新格式；术语 `cfxcode`→`cfxha`。
- `LD`/`ST` 指令名统一后缀；`cs.`/`br.` 指令名加点；修正无后缀 `add` 为 `add.so`。
- 旧 `bp63` 语法更新为 MISC 表指令名；`ww`→`wpN` 残留修正。
- 0 号寄存器（`rd0`）约束补全；多项审查修复（溢出检测 / 跳转表 / pending / 引导 / 掩码 / 注释）。

### 0.9.2（上游基线；导入日 2026-07-14，发布日不详）

- 上游 DADAO 应用程序运行环境（AEE）基线（基于 SimRISC 0.4.1）。
