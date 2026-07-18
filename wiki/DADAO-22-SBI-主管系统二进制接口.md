# SBI（主管系统二进制接口）

> **版本：0.7.1**（与 SEE 版本号一致，同步更新。基于 SimRISC 0.5.1 指令系统设计）

SBI 定义不同核芯功能扩展之间的功能调用。大部分功能调用在同一运行模式（主管模式）进行，仅少数需要访问特权硬件资源的服务才会提升到 H-mode 执行。

`trap cfxcode, immu18` 中 cfxcode 即为服务提供者，immu18 为功能编号。每个核芯功能扩展独立提供一组功能，按照实际需求进行调用。

## 1. 调用约定

**发起与返回**：调用方执行 `trap cfxcode, immu18` 陷入目标核芯功能扩展；被调方通过 `escape cfxcode, 1` 返回，跳转到 trap 指令的下一条指令（`excp_cause_ip + 4`）。

**参数传递**：与 ABI 传参规范一致（参见 `DADAO-21-ABI-应用程序二进制接口`）。

| 方向 | 寄存器 | 说明 |
|------|--------|------|
| 入参（数据） | rd16-rd31 | 标量参数，按参数顺序从 rd16 递增 |
| 入参（地址） | rb16-rb31 | 指针参数，按参数顺序从 rb16 递增 |
| 入参（浮点） | rf16-rf31 | 浮点参数，按参数顺序从 rf16 递增 |
| 出参（标量） | rd31 | 返回值：>=0 成功，<0 错误码 |
| 出参（地址） | rb31 | 当返回值为地址时使用 |
| 出参（浮点） | rf31 | 当返回值为浮点数时使用 |

三组参数寄存器独立计数，聚合类型参数与返回值遵循 ABI 的 HFA/HPA/sret 规则。

**错误码**：

| 值 | 名称 | 含义 |
|----|------|------|
| 0 | SBI_SUCCESS | 成功 |
| -1 | SBI_ERR_FAILED | 通用失败 |
| -2 | SBI_ERR_NOT_SUPPORTED | 功能不支持 |
| -3 | SBI_ERR_INVALID_PARAM | 参数无效 |
| -4 | SBI_ERR_NO_DEVICE | 设备不可用 |

**嵌套调用**：

硬件隔离每个核芯功能扩展的异常现场寄存器（cg5），因此调用不同核芯功能扩展（A→B→C）时无需额外保存——各核芯功能扩展的 `excp_prev_*` 和 `excp_cause_*` 独立不受影响。

仅在同一核芯功能扩展递归调用（如 B→B）时需要处理：进入 B 时应先将自身的 cg5 现场保存至暂存寄存器（cg6），返回前恢复。

调用方的参数寄存器（rd16-rd31、rb16-rb31、rf16-rf31）为临时寄存器，被嵌套调用可能修改。被调方如需在嵌套调用中保留这些值，应自行保存至栈或暂存寄存器（cg6）。

**被调方运行模式**：陷入后的实际运行模式由固件预先配置的 `cfx_⟨cfxname⟩_<mode>_switch_run_mode` 寄存器决定。

## 2. 用户态异常处理（umon / jmon）

umon（cfx0）为 user 模式的异常入口，处理用户态系统调用。系统调用遵循 ABI 约定的双层模型：`immu18` 为硬件事务编号（指令编码层），`rd15` 为软件系统调用号（功能分发层），参数和返回值与 ABI 传参规范一致（参见 `DADAO-21-ABI-应用程序二进制接口`）。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_UMON_SYSCALL | rd15 = nr | rd31 = result | 用户态系统调用分发 |
| 1 | SBI_UMON_GET_VERSION | — | rd31 = version | 返回 umon 版本号：当前 0.7.1 = `0x00070001`（`(major<<32)\|(minor<<16)\|patch`） |

jmon（cfx1）为 jail 模式的异常入口，处理受限用户态系统调用。jmon 与 umon 为独立上下文，immu18 各自编号互不冲突。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_JMON_SYSCALL | rd15 = nr | rd31 = result | 受限用户态系统调用分发 |
| 1 | SBI_JMON_GET_VERSION | — | rd31 = version | 返回 jmon 版本号：当前 0.7.1 = `0x00070001` |

## 3. 系统信息（smon）

cfx_smon 提供 SBI 版本查询和核芯功能扩展探测。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_SMON_GET_VERSION | — | rd31 = version | 返回 SBI 版本号：`(major<<32)\|(minor<<16)\|patch`，当前 0.7.1 = `0x00070001` |
| 1 | SBI_SMON_PROBE_CFX | rd16 = cfx | rd31 = func_map | 探测 cfx 支持的 SBI 功能位图（bit i = 1 表示 func i 可用）。若 cfx 硬件不存在则触发 CFXREG 异常；rd31=0 表示 cfx 存在但未实现任何 SBI 功能。实现上通过读取 `cfx_*_cfx_id` 寄存器验证存在性 |

### 初始化

```simrisc
; 设置 cfx_smon 的 supv 异常向量
setrd   rd2, cfx_smon_supv_excp_handler
cfx2rc  cfx_smon_supv_excp_vector, rd2

; 允许 cfx_smon 从 supv 触发
cfx2rd  cfx_smon_supv_global_cfx_mask, rd2
setrd   rd3, ~(1<<2)
and.o   rd2, rd2, rd3
cfx2rc  cfx_smon_supv_global_cfx_mask, rd2
```

异常入口处理：

```simrisc
cfx_smon_supv_excp_handler:
    cfx2rd  cfx_smon_excp_cause_id, rd2
    setrd   rd3, 1                                 ; CFXTRAP (1<<0)
    br.ne    rd2, rd3, cfx_smon_unknown

    cfx2rd  cfx_smon_excp_cause_info, rd2
    setrd   rd3, 0x3FFFF
    and.o   rd2, rd2, rd3
    setrd   rd3, 0
    br.eq    rd2, rd3, cfx_smon_get_version              ; func 0
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_smon_probe_cfx                ; func 1

cfx_smon_unknown:
    escape cfx_smon, 1
```

### 内部实现代码

```simrisc
cfx_smon_get_version:
    setrd   rd31, 0x00070001                        ; v0.7.1
    escape cfx_smon, 1

cfx_smon_probe_cfx:
    ; rd16 = cfx（调用方传入）
    ; 根据硬件实现返回目标 cfx 的功能位图
    setrd   rd31, 0                                 ; 占位
    escape cfx_smon, 1
```

### 功能调用示例

```simrisc
#define SBI_SMON_GET_VERSION  0
#define SBI_SMON_PROBE_CFX    1

; 获取 SBI 版本
trap    cfx_smon, SBI_SMON_GET_VERSION

; 探测 cfx_llc 的功能
setrd   rd16, 16
trap    cfx_smon, SBI_SMON_PROBE_CFX
```

## 4. 地址转换（cfx_ptw）

cfx_ptw 为地址转换部件，管理页表和 PTBR。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_PTW_SET_PTBR | rd16 = idx, rb16 = base | — | 设置第 idx 个 PTBR 的页表基地址。base 为 PA[63:16]（高 48 位），低 16 位强制为 0（64KiB 对齐）。调用前须已写入 pthi[idx] 和 pahi[idx] |
| 1 | SBI_PTW_GET_PTBR | rd16 = idx | rd31 = base | 读取第 idx 个 PTBR 的值 |
| 2 | SBI_PTW_SET_PTBR_PERM | rd16 = mode, rd17 = perm | — | 设置 mode=0(U)/1(J)/2(S)/3(H) 的 PTBR 权限位图（64 位，bit i=1 表示允许第 i 个 PTBR） |
| 3 | SBI_PTW_ENABLE_PTBR | rd16 = mask | — | 设置 PTBR 使能位图（64 位，bit i=1 表示 enable 第 i 个 PTBR） |
| 4 | SBI_PTW_SET_PTE | rd16 = ptbr_code, rd17 = level, rb16 = va, rd18 = pte | — | 设置 level 页表（1=L1, 2=L2）中 VA 对应索引的 PTE 为 pte |
| 5 | SBI_PTW_HANDLE_FAULT | rb16 = fault_addr, rd16 = cause | rd31 = page_mask | 处理页表异常。成功返回页面对齐掩码（如 0xFFFFFFFFFFFF0000 = 64KiB，0xFFFFFFFFE0000000 = 512MiB），失败返回 0 |
| 6 | SBI_PTW_SET_PTHI | rd16 = idx, rb16 = pthi | — | 设置第 idx 个 PTBR 的页表步进物理地址高 16 位（PA[63:48]） |
| 7 | SBI_PTW_SET_PAHI | rd16 = idx, rb16 = pahi | — | 设置第 idx 个 PTBR 的最终转换结果物理地址高 16 位（PA[63:48]） |

> **PTBR 与 pthi/pahi 的关系**：PTBR 存放页表基地址的高 48 位（bits[63:16]，低 16 位强制为 0）。`pthi[idx]`（cg10）提供**页表步进**时访问页表项的 PA[63:48]；`pahi[idx]`（cg11）提供**最终转换结果**物理地址的 PA[63:48]。调用 `SBI_PTW_SET_PTBR` 前须通过 `cfx2rc` 写入正确的 pthi/pahi 值。
>
> **页表访问**：cfx_ptw handler 通过正常虚拟地址访问 PTE。操作系统在启动阶段须将页表所在的物理区域映射到虚拟地址空间，handler 可直接对 PTE 所在虚拟地址执行 ld/st 来读写页表项，无需专门的物理内存直接访问机制。

### 初始化

> 初始化方式与其他 cfx 一致：探测 cfx_ptw 的存在性，设置异常向量并清除 global_cfx_mask 对应位（bit 4）。cfx_ptw 为 per-hart cfx，每个 hart 独立初始化。

cfx_ptw 的异常入口处理——页表步进异常由硬件直接路由至此，也可由其它 cfx（如 cfx_tlb）通过功能调用委托处理：

```simrisc
cfx_ptw_supv_excp_handler:
    cfx2rd  cfx_ptw_excp_cause_id, rd2

    ; CFXTRAP (1<<0) → SBI 功能调用分发
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_ptw_trap_dispatch

    ; 页缺失异常 → 委托 cfx_pmem 分配物理页，修复 PTE
    ; 具体处理根据 cause_id 分发

cfx_ptw_unknown:
    escape cfx_ptw, 1

cfx_ptw_trap_dispatch:
    cfx2rd  cfx_ptw_excp_cause_info, rd2
    setrd   rd3, 0x3FFFF
    and.o   rd2, rd2, rd3
    setrd   rd3, 0
    br.eq    rd2, rd3, cfx_ptw_set_ptbr              ; func 0
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_ptw_get_ptbr              ; func 1
    setrd   rd3, 2
    br.eq    rd2, rd3, cfx_ptw_set_ptbr_perm         ; func 2
    setrd   rd3, 3
    br.eq    rd2, rd3, cfx_ptw_enable_ptbr           ; func 3
    setrd   rd3, 4
    br.eq    rd2, rd3, cfx_ptw_set_pte               ; func 4
    setrd   rd3, 5
    br.eq    rd2, rd3, cfx_ptw_handle_fault           ; func 5
    setrd   rd3, 6
    br.eq    rd2, rd3, cfx_ptw_set_pthi               ; func 6
    setrd   rd3, 7
    br.eq    rd2, rd3, cfx_ptw_set_pahi               ; func 7
    escape cfx_ptw, 1

cfx_ptw_set_ptbr:
    ; rd16 = idx, rb16 = base（页表基地址高 48 位，低 16 位强制为 0）
    ; 调用前须已通过 cfx2rc 写入 cfx_ptw_pthi[idx] 和 cfx_ptw_pahi[idx]
    setrd   rd17, rb16                              ; rb→rd 中转（cfx2rc 源操作数须为 rd）
    shl.uo  rd16, rd16, 3                          ; idx × 8（每路 2 条指令 = 8 字节）
    setrd   rd3, cfx_ptw_ptbr_table
    add     rd0, rd3, rd3, rd16
    setrb   rb3, rd3                      ; rd→rb 中转
    jump    rb3, rd0, 0
cfx_ptw_ptbr_table:
    cfx2rc  cfx_ptw, 9, 0,  rd17 ; PTBR[0]
    escape cfx_ptw, 1
    cfx2rc  cfx_ptw, 9, 1,  rd17 ; PTBR[1]
    escape cfx_ptw, 1
    ; ... 共 64 路，rc 0-63 ...
    cfx2rc  cfx_ptw, 9, 63, rd17 ; PTBR[63]
    escape cfx_ptw, 1

cfx_ptw_get_ptbr:
    ; rd16 = idx，返回 rd31 = base
    shl.uo  rd16, rd16, 3
    setrd   rd3, cfx_ptw_get_ptbr_table
    add     rd0, rd3, rd3, rd16
    setrb   rb3, rd3                      ; rd→rb 中转
    jump    rb3, rd0, 0
cfx_ptw_get_ptbr_table:
    cfx2rd  cfx_ptw, 9, 0,  rd31 ; PTBR[0]
    escape cfx_ptw, 1
    cfx2rd  cfx_ptw, 9, 1,  rd31 ; PTBR[1]
    escape cfx_ptw, 1
    ; ... 共 64 路，rc 0-63 ...
    cfx2rd  cfx_ptw, 9, 63, rd31 ; PTBR[63]
    escape cfx_ptw, 1

cfx_ptw_set_ptbr_perm:
    ; rd16 = mode（0=U/1=J/2=S/3=H）, rd17 = perm（64 位权限位图）
    ; 通过跳转表将 rd17 写入对应 mode 的 cfx_ptw_*_perm 寄存器
    shl.uo  rd16, rd16, 3                          ; mode × 8（跳转表偏移，每路 2 条指令）
    setrd   rd3, cfx_ptw_perm_table
    add     rd0, rd3, rd3, rd16
    setrb   rb3, rd3                      ; rd→rb 中转
    jump    rb3, rd0, 0
cfx_ptw_perm_table:
    cfx2rc  cfx_ptw_user_perm, rd17               ; U-mode (0)
    escape cfx_ptw, 1
    cfx2rc  cfx_ptw_jail_perm, rd17               ; J-mode (1)
    escape cfx_ptw, 1
    cfx2rc  cfx_ptw_supv_perm, rd17               ; S-mode (2)
    escape cfx_ptw, 1
    cfx2rc  cfx_ptw_hypv_perm, rd17               ; H-mode (3)
    escape cfx_ptw, 1

cfx_ptw_enable_ptbr:
    ; rd16 = mask（64 位使能位图）
    cfx2rc  cfx_ptw_ptbr_enable, rd16
    escape cfx_ptw, 1

cfx_ptw_set_pte:
    ; rd16 = ptbr_code, rd17 = level（1=L1, 2=L2）, rb16 = va, rd18 = pte
    ; TODO: 读取 PTBR[ptbr_code]，按 level 计算 PTE 偏移，通过 OS 映射的虚拟地址写 PTE
    escape cfx_ptw, 1

cfx_ptw_handle_fault:
    ; rd16 = cause, rb16 = fault_addr（由调用方传入）
    ; ... 根据 cause 类型执行页表步进、pmem 分配、PTE 更新 ...
    escape cfx_ptw, 1

cfx_ptw_set_pthi:
    ; rd16 = idx, rb16 = pthi（PA[63:48] 用于页表步进）
    setrd   rd17, rb16                              ; rb→rd 中转
    shl.uo  rd16, rd16, 3
    setrd   rd3, cfx_ptw_set_pthi_table
    add     rd0, rd3, rd3, rd16
    setrb   rb3, rd3                      ; rd→rb 中转
    jump    rb3, rd0, 0
cfx_ptw_set_pthi_table:
    cfx2rc  cfx_ptw, 10, 0,  rd17 ; pthi[0]
    escape cfx_ptw, 1
    cfx2rc  cfx_ptw, 10, 1,  rd17 ; pthi[1]
    escape cfx_ptw, 1
    ; ... 共 64 路 ...
    cfx2rc  cfx_ptw, 10, 63, rd17 ; pthi[63]
    escape cfx_ptw, 1

cfx_ptw_set_pahi:
    ; rd16 = idx, rb16 = pahi（PA[63:48] 用于最终转换结果）
    setrd   rd17, rb16                              ; rb→rd 中转
    shl.uo  rd16, rd16, 3
    setrd   rd3, cfx_ptw_set_pahi_table
    add     rd0, rd3, rd3, rd16
    setrb   rb3, rd3                      ; rd→rb 中转
    jump    rb3, rd0, 0
cfx_ptw_set_pahi_table:
    cfx2rc  cfx_ptw, 11, 0,  rd17 ; pahi[0]
    escape cfx_ptw, 1
    cfx2rc  cfx_ptw, 11, 1,  rd17 ; pahi[1]
    escape cfx_ptw, 1
    ; ... 共 64 路 ...
    cfx2rc  cfx_ptw, 11, 63, rd17 ; pahi[63]
    escape cfx_ptw, 1
```

各 cfx 之间的委托关系：cfx_tlb 委托 cfx_ptw 处理页表异常（通过 SBI_PTW_HANDLE_FAULT），cfx_ptw 委托 cfx_pmem 申请物理页。

## 5. TLB管理（cfx_tlb）

cfx_tlb 为 TLB 管理部件，提供 TLB 无效化服务。

| immu18 | 名称 | 入参 | 说明 |
|--------|------|------|------|
| 0 | SBI_TLB_INVALIDATE | rb16 = start, rd16 = size | 使 TLB 中 [start, start+size) 范围的表项无效 |

### 初始化

```simrisc
; 设置 cfx_tlb 的 supv 异常向量，允许 supv 内核调用
setrd   rd2, cfx_tlb_supv_excp_handler
cfx2rc  cfx_tlb_supv_excp_vector, rd2

; 允许 cfx_tlb 从 supv 触发（清除 global_cfx_mask 对应位）
; 注：global_cfx_mask 是全局共享寄存器（此处通过 cfx_smon 访问），所有 cfx 的委托掩码集中于此
cfx2rd  cfx_smon_supv_global_cfx_mask, rd2
setrd   rd3, ~(1<<5)
and.o   rd2, rd2, rd3
cfx2rc  cfx_smon_supv_global_cfx_mask, rd2
```

异常入口处理——从 `excp_cause_info` 获取 trap 指令的 immu18 功能码并分发：

```simrisc
cfx_tlb_supv_excp_handler:
    cfx2rd  cfx_tlb_excp_cause_id, rd2

    ; CFXTRAP (1<<0) → SBI 功能调用
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_tlb_trap_dispatch

    ; 页表相关异常（TLB 命中时产生）→ 委托 cfx_ptw 处理
    setrd   rd3, 1<<12                               ; NXPERM
    br.eq    rd2, rd3, cfx_tlb_ptw_delegate
    setrd   rd3, 1<<13                               ; NWPERM
    br.eq    rd2, rd3, cfx_tlb_ptw_delegate
    setrd   rd3, 1<<14                               ; NRPERM
    br.eq    rd2, rd3, cfx_tlb_ptw_delegate
    setrd   rd3, 1<<18                               ; IGPFTRAP
    br.eq    rd2, rd3, cfx_tlb_ptw_delegate
    setrd   rd3, 1<<19                               ; ISPFTRAP
    br.eq    rd2, rd3, cfx_tlb_ptw_delegate
    setrd   rd3, 1<<22                               ; DGPFTRAP
    br.eq    rd2, rd3, cfx_tlb_ptw_delegate
    setrd   rd3, 1<<23                               ; DSPFTRAP
    br.eq    rd2, rd3, cfx_tlb_ptw_delegate

cfx_tlb_unknown:
    escape cfx_tlb, 1

cfx_tlb_trap_dispatch:
    cfx2rd  cfx_tlb_excp_cause_info, rd2
    setrd   rd3, 0x3FFFF
    and.o   rd2, rd2, rd3
    setrd   rd3, 0
    br.eq    rd2, rd3, cfx_tlb_invalidate              ; func 0
    escape cfx_tlb, 1

cfx_tlb_ptw_delegate:
    ; 委托 cfx_ptw 处理页表异常（通过 SBI_PTW_HANDLE_FAULT）
    cfx2rd  cfx_tlb_excp_cause_info, rd40            ; 故障地址（保存至 callee-saved rd40）
    setrb   rb16, rd40
    cfx2rd  cfx_tlb_excp_cause_id, rd16              ; 异常原因（cause_id）
    trap    cfx_ptw, SBI_PTW_HANDLE_FAULT
    ; 返回 rd31 = page_mask（成功：0xFFFF...掩码；失败：0）
    setrd   rd3, 0
    br.eq    rd31, rd3, cfx_tlb_ptw_fail              ; 修复失败 → 跳过
    ; 修复成功 → invalid 对应 TLB 表项，按实际页大小
    and.o   rd40, rd40, rd31                          ; 按掩码对齐至页面起始
    cfx2rc  cfx_tlb_addr_start, rd40
    not     rd16, rd31
    add.si    rd16, rd16, 1                             ; addr_size = ~mask + 1
    cfx2rc  cfx_tlb_addr_size, rd16
    setrd   rd2, 2
    cfx2rc  cfx_tlb_control, rd2                      ; bit1 = invalid by addr
    escape cfx_tlb, 0                                 ; 重试故障指令
cfx_tlb_ptw_fail:
    escape cfx_tlb, 1                                 ; 跳过故障指令
```

### 内部实现代码

分发后的功能实现——通过 cfx_tlb_control 触发操作，cfx_tlb_addr_start/size 指定地址范围：

```simrisc
cfx_tlb_invalidate:
    ; rb16 = start, rd16 = size（由调用方通过 trap 传入）
    cfx2rc  cfx_tlb_addr_size, rd16
    setrd   rd2, rb16                               ; rb→rd 中转（cfx2rc 源操作数须为 rd）
    cfx2rc  cfx_tlb_addr_start, rd2
    setrd   rd2, 1 << 1                              ; bit1 = invalid tlb by addr range
    cfx2rc  cfx_tlb_control, rd2
    escape cfx_tlb, 1
```

页表异常委托处理（`cfx_tlb_ptw_delegate`）由 cfx_ptw 完成页表步进，cfx_tlb 根据返回结果 invalid 或填充对应 TLB 表项。

### 功能调用示例

```simrisc
#define SBI_TLB_INVALIDATE  0

; 使虚拟地址 addr 对应的 64K 区域 TLB 表项无效
setrb   rb16, addr
setrd   rd16, 65536                              ; 64K
trap    cfx_tlb, SBI_TLB_INVALIDATE

; 使对应 ptbr 的所有 TLB 表项无效
setrb   rb16, 0
setrd   rd16, 0x40000000000                       ; 0x40000000000（2^42） = 集合内全部 VA 空间
trap    cfx_tlb, SBI_TLB_INVALIDATE
```

## 6. Cache管理（cfx_cache）

cfx_cache 为 Cache 管理部件，提供 I-Cache 和 D-Cache 的无效化和刷新。

| immu18 | 名称 | 入参 | 说明 |
|--------|------|------|------|
| 0 | SBI_CACHE_IC_INVALID | — | 无效化所有 I-Cache |
| 1 | SBI_CACHE_DC_INVALID | — | 无效化所有 D-Cache |
| 2 | SBI_CACHE_DC_FLUSH | — | 刷新所有 D-Cache（写回脏数据后无效化） |

> 初始化方式与其他 cfx 一致：通过 `trap cfx_smon, SBI_SMON_PROBE_CFX` 探测 cfx_cache 的存在性，设置异常向量并清除 global_cfx_mask 对应位（bit 6）。cfx_cache 为 per-hart cfx，每个 hart 独立初始化。

## 7. Hart管理（cfx_hart）

cfx_hart 为 Hart 管理部件，提供 hart ID。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_HART_GET_ID | — | rd31 = id | 返回当前 hart 编号 |

> 初始化方式与其他 cfx 一致：探测 cfx_hart 的存在性，设置异常向量并清除 global_cfx_mask 对应位（bit 15）。cfx_hart 为 per-hart cfx，每个 hart 独立初始化。

## 8. LLC管理（cfx_llc）

cfx_llc 为最后一级缓存管理部件，跨 hart 共享。

| immu18 | 名称 | 入参 | 说明 |
|--------|------|------|------|
| 0 | SBI_LLC_INVALID | — | 无效化所有 LLC |

> 初始化方式与其他 cfx 一致：探测 cfx_llc 的存在性，设置异常向量并清除 global_cfx_mask 对应位（bit 16）。cfx_llc 为 per-system cfx（跨 hart 共享），仅需初始化一次。

## 9. 物理存储器管理（cfx_pmem）

cfx_pmem 为存储器管理部件，S-mode 可查询 hypv 固件设置的物理存储器区域配置。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_PMEM_GET_PM_COUNT | — | rd31 = count | 返回 PM 区域总数 |
| 1 | SBI_PMEM_GET_PM_START | rd16 = idx | rd31 = start | 查询第 idx 个 PM 区域的起始地址 |
| 2 | SBI_PMEM_GET_PM_SIZE | rd16 = idx | rd31 = size | 查询第 idx 个 PM 区域的大小 |
| 3 | SBI_PMEM_GET_PM_ATTR | rd16 = idx | rd31 = attr | 查询第 idx 个 PM 区域的属性 |
| 4 | SBI_PMEM_ALLOC_PAGE | rd16 = size_hint | rd31 = ppn | 从 PM 区域分配物理页。成功返回 PPN（物理页号，>=0），失败返回 -1。由 cfx_ptw 委托调用 |
| 5 | SBI_PMEM_FREE_PAGE | rd16 = ppn | — | 释放物理页，由 cfx_ptw 委托调用 |

> 初始化方式与其他 cfx 一致：探测 cfx_pmem 的存在性，设置异常向量并清除 global_cfx_mask 对应位（bit 17）。cfx_pmem 的 PM 区域配置由 hypv 固件在 H-mode 初始化阶段完成（见 HBI §3）。

cfx_pmem 的异常入口处理：

```simrisc
cfx_pmem_supv_excp_handler:
    cfx2rd  cfx_pmem_excp_cause_id, rd2
    setrd   rd3, 1                                 ; CFXTRAP (1<<0)
    br.ne    rd2, rd3, cfx_pmem_unknown
    cfx2rd  cfx_pmem_excp_cause_info, rd2         ; func dispatch
    setrd   rd3, 0x3FFFF
    and.o   rd2, rd2, rd3
    setrd   rd3, 0
    br.eq    rd2, rd3, cfx_pmem_get_pm_count        ; func 0
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_pmem_get_pm_start        ; func 1
    setrd   rd3, 2
    br.eq    rd2, rd3, cfx_pmem_get_pm_size         ; func 2
    setrd   rd3, 3
    br.eq    rd2, rd3, cfx_pmem_get_pm_attr         ; func 3
    setrd   rd3, 4
    br.eq    rd2, rd3, cfx_pmem_alloc_page          ; func 4
    setrd   rd3, 5
    br.eq    rd2, rd3, cfx_pmem_free_page           ; func 5
cfx_pmem_unknown:
    escape cfx_pmem, 1

cfx_pmem_get_pm_count:
    cfx2rd  cfx_pmem_exist, rd31
    ; TODO: 遍历 cfx_pmem_exist 位图，统计置 1 的位数 = PM 区域数
    escape cfx_pmem, 1

cfx_pmem_get_pm_start:
    ; rd16 = idx, cfx_pmem_start[idx] 为索引数组
    ; TODO: 跳转表或 SRAM 实现动态索引
    escape cfx_pmem, 1

cfx_pmem_get_pm_size:
    ; rd16 = idx
    ; TODO: 同上
    escape cfx_pmem, 1

cfx_pmem_get_pm_attr:
    ; rd16 = idx
    ; TODO: 同上
    escape cfx_pmem, 1

cfx_pmem_alloc_page:
    ; rd16 = size_hint（0 = 自动选择最小的可用区域）
    ; 返回 rd31 = ppn（物理页号）或 -1（失败）
    ; TODO: 遍历 PM 区域，维护自由页链表，分配并返回 PPN
    escape cfx_pmem, 1

cfx_pmem_free_page:
    ; rd16 = ppn
    ; TODO: 将 PPN 归还到对应 PM 区域的自由页链表
    escape cfx_pmem, 1
```

## 10. 定时器/计数器（cfx_timer）

cfx_timer 为定时器/计数器，提供定时器服务。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_TIMER_SET_TIMER | rd16 = timeout | — | 设置定时器在 timeout（周期计数值）时触发中断 |
| 1 | SBI_TIMER_GET_TIME | — | rd31 = value | 返回定时器当前计数值 |

### 初始化

```simrisc
; 设置 cfx_timer 的 supv 异常向量
setrd   rd2, cfx_timer_supv_excp_handler
cfx2rc  cfx_timer_supv_excp_vector, rd2

; 允许 cfx_timer 从 supv 触发
cfx2rd  cfx_smon_supv_global_cfx_mask, rd2
setrd   rd3, ~(1<<18)                                ; cfx_timer = cfx18
and.o   rd2, rd2, rd3
cfx2rc  cfx_smon_supv_global_cfx_mask, rd2
```

异常入口处理：

```simrisc
cfx_timer_supv_excp_handler:
    cfx2rd  cfx_timer_excp_cause_id, rd2

    ; CFXTRAP (1<<0) → SBI 功能调用
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_timer_trap_dispatch

    ; TIMER (1<<10) → 定时器中断
    setrd   rd3, 1024
    br.eq    rd2, rd3, cfx_timer_int

cfx_timer_unknown:
    escape cfx_timer, 1

cfx_timer_trap_dispatch:
    cfx2rd  cfx_timer_excp_cause_info, rd2
    setrd   rd3, 0x3FFFF                            ; 掩码提取 immu18
    and.o   rd2, rd2, rd3
    setrd   rd3, 0
    br.eq    rd2, rd3, cfx_timer_set_timer               ; func 0
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_timer_get_time                ; func 1
    escape cfx_timer, 1
```

### 内部实现代码

```simrisc
cfx_timer_set_timer:
    ; rd16 = timeout（调用方传入）
    ; 写入计数值，设置为递减 one-shot 模式并启动
    cfx2rc  cfx_timer_regs[0], rd16
    setrd   rd2, 1                                      ; bit0=enable, bit1=one-shot, bit2=decrement
    cfx2rc  cfx_timer_ctrl, rd2
    escape cfx_timer, 1

cfx_timer_get_time:
    cfx2rd  cfx_timer_regs[0], rd31                    ; 返回值在 rd31，读取定时器当前计数值
    escape cfx_timer, 1

cfx_timer_int:
    ; 处理定时器中断
    escape cfx_timer, 0
```

### 功能调用示例

```simrisc
#define SBI_TIMER_SET_TIMER  0
#define SBI_TIMER_GET_TIME   1

; 设置定时器在 timeout 周期后触发
setrd   rd16, timeout
trap    cfx_timer, SBI_TIMER_SET_TIMER

; 读取当前周期计数
trap    cfx_timer, SBI_TIMER_GET_TIME
; 返回值在 rd31
```

## 11. 串口控制台（cfx_uart）

cfx_uart 为 UART 控制器，提供控制台输入输出。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | SBI_UART_PUTCHAR | rd16 = ch | — | 向控制台写入字符 ch |
| 1 | SBI_UART_GETCHAR | — | rd31 = ch | 从控制台读取字符。若无可用字符，返回 -1 |
| 2 | SBI_UART_WRITE | rb16 = buf, rd16 = len | rd31 = written | 向控制台写入 len 字节。返回实际写入字节数 |
| 3 | SBI_UART_READ | rb16 = buf, rd16 = len | rd31 = read | 从控制台读取最多 len 字节。返回实际读取字节数 |

### 初始化

```simrisc
; 设置 cfx_uart 的 supv 异常向量
setrd   rd2, cfx_uart_supv_excp_handler
cfx2rc  cfx_uart_supv_excp_vector, rd2

; 允许 cfx_uart 从 supv 触发
cfx2rd  cfx_smon_supv_global_cfx_mask, rd2
setrd   rd3, ~(1<<62)
and.o   rd2, rd2, rd3
cfx2rc  cfx_smon_supv_global_cfx_mask, rd2
```

异常入口处理：

```simrisc
cfx_uart_supv_excp_handler:
    cfx2rd  cfx_uart_excp_cause_id, rd2

    ; CFXTRAP (1<<0) → SBI 功能调用
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_uart_trap_dispatch

    ; UART 中断（1<<32..63）
    ; 通过 excp_pending 寄存器判断具体中断源并处理
    cfx2rd  cfx_uart_excp_pending, rd3
    ; 此处根据 pending 位处理对应 UART
    escape cfx_uart, 0

cfx_uart_trap_dispatch:
    cfx2rd  cfx_uart_excp_cause_info, rd2
    setrd   rd3, 0x3FFFF
    and.o   rd2, rd2, rd3
    setrd   rd3, 0
    br.eq    rd2, rd3, cfx_uart_putchar                 ; func 0
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_uart_getchar                 ; func 1
    setrd   rd3, 2
    br.eq    rd2, rd3, cfx_uart_write                   ; func 2
    setrd   rd3, 3
    br.eq    rd2, rd3, cfx_uart_read                    ; func 3

cfx_uart_unknown:
    escape cfx_uart, 1
```

### 内部实现代码

```simrisc
cfx_uart_putchar:
    ; rd16 = ch（调用方传入）
    cfx2rc  cfx_uart_uart0_regs[0], rd16              ; 写 UART 发送寄存器
    escape cfx_uart, 1

cfx_uart_getchar:
    ; 从 UART 接收寄存器读取字符
    cfx2rd  cfx_uart_uart0_regs[1], rd31
    escape cfx_uart, 1

cfx_uart_write:
    ; rb16 = buf, rd16 = len
    ; 循环写入 len 字节（此处省略循环实现）
    setrd   rd31, 0
    escape cfx_uart, 1

cfx_uart_read:
    ; rb16 = buf, rd16 = len
    ; 循环读取 len 字节（此处省略循环实现）
    setrd   rd31, 0
    escape cfx_uart, 1
```

### 功能调用示例

```simrisc
#define SBI_UART_PUTCHAR  0
#define SBI_UART_GETCHAR  1
#define SBI_UART_WRITE    2
#define SBI_UART_READ     3

; 写入字符 'A'
setrd   rd16, 65
trap    cfx_uart, SBI_UART_PUTCHAR

; 读取字符
trap    cfx_uart, SBI_UART_GETCHAR
; 返回值在 rd31
```

## 12. 系统控制（cfx_power）

cfx_power 为电源管理，提供关机和重启服务。`power_ctrl` 寄存器的默认访问权限为 hypv；HBI 引导代码（§3）将 `cfx_power_hypv_cg_reg_deleg` 设为 0 以委托给 supv，因此 supv 可直接通过 `cfx2rc`/`cfx2rd` 操作该寄存器。固件应将其 `switch_run_mode` 配置为 hypv 以确保安全隔离。

| immu18 | 名称 | 入参 | 说明 |
|--------|------|------|------|
| 0 | SBI_POWER_SHUTDOWN | — | 关闭系统电源，不返回 |
| 1 | SBI_POWER_HARD_RESET | — | 硬复位（冷复位），不返回 |
| 2 | SBI_POWER_SOFT_RESET | — | 软复位（热复位），不返回 |

### 初始化

```simrisc
; 设置 cfx_power 的 supv 异常向量
setrd   rd2, cfx_power_supv_excp_handler
cfx2rc  cfx_power_supv_excp_vector, rd2

; 允许 cfx_power 从 supv 触发（清除 global_cfx_mask 对应位）
cfx2rd  cfx_smon_supv_global_cfx_mask, rd2
setrd   rd3, ~(1<<63)
and.o   rd2, rd2, rd3
cfx2rc  cfx_smon_supv_global_cfx_mask, rd2
```

异常入口处理：

```simrisc
cfx_power_supv_excp_handler:
    cfx2rd  cfx_power_excp_cause_id, rd2

    ; CFXTRAP (1<<0) → SBI 功能调用
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_power_trap_dispatch

    ; POWEROFF (1<<8) → 硬件关机
    setrd   rd3, 256
    br.eq    rd2, rd3, cfx_power_shutdown

    ; HARD RESET (1<<9) → 硬件硬复位
    setrd   rd3, 512
    br.eq    rd2, rd3, cfx_power_hard_reset

    ; SOFT RESET (1<<10) → 软复位
    setrd   rd3, 1024
    br.eq    rd2, rd3, cfx_power_soft_reset

cfx_power_unknown:
    escape cfx_power, 1

cfx_power_trap_dispatch:
    cfx2rd  cfx_power_excp_cause_info, rd2
    setrd   rd3, 0x3FFFF                            ; 掩码提取 immu18
    and.o   rd2, rd2, rd3
    setrd   rd3, 0
    br.eq    rd2, rd3, cfx_power_shutdown                ; func 0
    setrd   rd3, 1
    br.eq    rd2, rd3, cfx_power_hard_reset              ; func 1
    setrd   rd3, 2
    br.eq    rd2, rd3, cfx_power_soft_reset              ; func 2
    escape cfx_power, 1
```

### 内部实现代码

```simrisc
cfx_power_shutdown:
    setrd   rd2, 1                                  ; bit0 = 关机
    cfx2rc  cfx_power_ctrl, rd2                   ; 不返回

cfx_power_hard_reset:
    setrd   rd2, 2                                  ; bit1 = 硬复位
    cfx2rc  cfx_power_ctrl, rd2                   ; 不返回

cfx_power_soft_reset:
    setrd   rd2, 4                                  ; bit2 = 软复位
    cfx2rc  cfx_power_ctrl, rd2                   ; 不返回
```

### 功能调用示例

```simrisc
#define SBI_POWER_SHUTDOWN     0
#define SBI_POWER_HARD_RESET   1
#define SBI_POWER_SOFT_RESET   2

; 关闭系统电源
trap    cfx_power, SBI_POWER_SHUTDOWN

; 硬复位
trap    cfx_power, SBI_POWER_HARD_RESET

; 软复位
trap    cfx_power, SBI_POWER_SOFT_RESET
```

## 13. 代码示例

### 示例：主管系统异常向量

cfx_umon、cfx_jmon、cfx_smon、cfx_hmon 为运行模式 monitor，配置方式同上（设置异常向量 + 清除 global_cfx_mask，允许当前运行模式同步异常进入对应 monitor）。

```simrisc
; ===== 系统初始化 =====
os_init:
    ; 设置cfx0的U-mode异常向量（从user陷入时跳转到cfx_umon_user_excp_handler）
    setrd   rd2, cfx_umon_user_excp_handler
    cfx2rc  cfx_umon_user_excp_vector, rd2

    ; 允许 U-mode 同步异常进入 cfx_umon（清除 global_cfx_mask bit 0）
    cfx2rd  cfx_smon_user_global_cfx_mask, rd2
    setrd   rd3, ~(1<<0)
    and.o   rd2, rd2, rd3
    cfx2rc  cfx_smon_user_global_cfx_mask, rd2
```

```simrisc
; ===== cfx0异常向量入口（U-mode） =====
cfx_umon_user_excp_handler:
    ; 读取异常原因
    cfx2rd  cfx_umon_excp_cause_id, rd2

    ; 判断异常类型并分发
    setrd   rd3, 1
    br.eq    rd2, rd3, syscall_handler               ; CFXTRAP (1<<0)
    setrd   rd3, 256
    br.eq    rd2, rd3, illi_handler                  ; ILLI (1<<8)
    setzw   rd3, wp2, 1                             ; rd3 = 1<<32
    br.eq    rd2, rd3, fpexcp_handler                ; FPEXCP (1<<32)
    ; 默认：未处理异常
    escape cfx_umon, 1
```

syscall_handler、illi_handler、fpexcp_handler 等具体处理函数由操作系统实现。

## 14. 扩展

新增硬件核芯功能扩展时，按其 cfxcode 在本文档中新增对应章节，定义 immu18 功能码表即可。保留 immu18 值 0x3FFFF（最大）用于将来可能的 "SBI 协议版本协商" 功能。
