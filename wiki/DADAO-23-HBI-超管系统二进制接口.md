# HBI（超管系统二进制接口）

> **版本：0.1.2**（与 HEE 版本号一致，同步更新。基于 SimRISC 0.5.0 指令系统设计）

HBI 定义 H-mode（超管模式）核芯功能扩展提供的功能调用，供 S-mode 内核或其它核芯功能扩展请求需要 H-mode 权限的系统服务。

`trap cfxcode, immu18` 中 cfxcode 即为服务提供者，immu18 为功能编号。每个核芯功能扩展独立提供一组功能，按照实际需求进行调用。

## 1. 调用约定

与 SBI 调用约定一致（参见 SBI §1）。

## 2. 系统信息（cfx_hmon）

cfx_hmon 为 hypv 的 monitor，提供 HBI 版本查询和硬件信息。

| immu18 | 名称 | 入参 | 出参 | 说明 |
|--------|------|------|------|------|
| 0 | HBI_GET_VERSION | — | rd31 = version | 返回 HBI 版本号：`(major<<32)\|(minor<<16)\|patch`，当前 0.1.2 = `0x00010002` |

## 3. 启动与引导移交约定

硬件复位后：

1. 运行模式初始化为 hypv，`inner_cfx_code` 初始化为 cfx_power，`inner_cfx_mask` 初始化为全 1（当前运行掩码屏蔽所有核芯功能扩展；可通过 trap 或 escape 流程更新）
2. 所有 `global_cfx_mask` 初始化为全 1（所有核芯功能扩展被屏蔽，无法触发异常）
3. `inner_inst_pointer` 跳转到 `cfx_power_hypv_excp_vector` 指示的地址（初始值为 `0xffff_ffff_0000`，为 DDR 未初始化前硬件可直接执行指令的一段地址空间）

hypv 引导代码完成最小初始化后，按以下流程将控制权移交 supv 内核：

```simrisc
; 清除各 cfx 的 cg reg delegation，允许 supv 访问所有 cg（cg3 固定禁止，bit3 硬件忽略写入）
setrd   rd2, 0
cfx2rc  cfx_umon_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_jmon_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_smon_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_ptw_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_tlb_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_cache_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_hart_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_llc_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_pmem_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_timer_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_uart_hypv_cg_reg_deleg, rd2
cfx2rc  cfx_power_hypv_cg_reg_deleg, rd2

; 设置 cfx_power 的 excp_prev_run_mode 为 supv（值 2）
setrd   rd2, 2
cfx2rc  cfx_power_excp_prev_run_mode, rd2

; 设置 excp_prev_cfx_mask 为全 1（不允许任何核芯功能扩展发生异常）
setrd   rd2, -1
cfx2rc  cfx_power_excp_prev_cfx_mask, rd2

; 设置 excp_cause_ip 为 supv 入口物理地址（尚未开启 ptbr，应为物理地址）
setrd   rd2, target_addr
cfx2rc  cfx_power_excp_cause_ip, rd2

; 传递设备树或硬件信息指针（0 表示无）
setrb   rb16, fdt_addr

; 执行 escape 跳转到 supv 入口
escape cfx_power, 0
```

S-mode 内核入口通过 rb16 获取设备树指针。
