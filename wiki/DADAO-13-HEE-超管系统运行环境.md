# DADAO Hypervisor Execution Environment

> **版本：0.1.2**（与 HBI 版本号一致，同步更新。基于 SimRISC 0.4.1 指令系统设计）

本文档定义 DADAO 超管系统运行环境（Hypervisor Execution Environment, HEE）的体系结构规范。

## 1. cg3 - hypv mode 寄存器

每个核芯功能扩展中针对超管模式（hypv）有以下 12 个寄存器（cg=3）。这部分寄存器的读写，只有当前运行环境是 hypv 时才能进行，否则触发非法指令异常。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 3 | 1 | hypv global cfx mask | cfx_⟨cfxname⟩_hypv_global_cfx_mask | 全1 | RW | 全局核芯功能扩展掩码，0=可触发，1=屏蔽。自身 cfxcode 对应位硬件忽略 |
| 3 | 2 | hypv cfx2rd cfx mask | cfx_⟨cfxname⟩_hypv_cfx2rd_cfx_mask | 全1 | RW | cfx2rd 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 3 | 3 | hypv cfx2rc cfx mask | cfx_⟨cfxname⟩_hypv_cfx2rc_cfx_mask | 全1 | RW | cfx2rc 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 3 | 4 | hypv cfxld cfx mask | cfx_⟨cfxname⟩_hypv_cfxld_cfx_mask | 全1 | RW | cfxld 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 3 | 5 | hypv cfxst cfx mask | cfx_⟨cfxname⟩_hypv_cfxst_cfx_mask | 全1 | RW | cfxst 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 3 | 6 | hypv trap cfx mask | cfx_⟨cfxname⟩_hypv_trap_cfx_mask | 全1 | RW | trap 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 3 | 7 | hypv escape cfx mask | cfx_⟨cfxname⟩_hypv_escape_cfx_mask | 全1 | RW | escape 指令是否可从其他 cfx 执行，0=可，1=不可。自身 cfxcode 对应位硬件忽略 |
| 3 | 8 | hypv switch run mode | cfx_⟨cfxname⟩_hypv_switch_run_mode | 3 (hypv) | RW | 从hypv陷入时切换的运行模式 |
| 3 | 9 | hypv switch cfx mask | cfx_⟨cfxname⟩_hypv_switch_cfx_mask | 全1 | RW | 从hypv陷入时采用的异常掩码，0=可触发，1=屏蔽 |
| 3 | 10 | hypv excp vector | cfx_⟨cfxname⟩_hypv_excp_vector | cfxcode<<42 + 0x3ff_ffff_0000 | RW | 从hypv陷入时的异常向量入口地址。cfx_power（cfxcode=63）例外，复位值为 `0xFFFF_FFFF_0000`（见 SEE §2.1） |
| 3 | 11 | hypv excp mask | cfx_⟨cfxname⟩_hypv_excp_cause_mask | 全1 | RW | 异常原因掩码，0=可触发，1=屏蔽 |
| 3 | 12 | hypv cg reg delegation | cfx_⟨cfxname⟩_hypv_cg_reg_deleg | 全1 | RW | cg访问授权，bit=0时允许supv访问。bit3固定为1 |

`hypv global` 开头的寄存器为全局寄存器，即所有核芯功能扩展共享同一个寄存器。

## 2. cfx_hmon - hypervisor monitor

hmon 为 hypv 下的同步异常处理核芯功能扩展，处理 hypv 下的同步异常。hmon 核芯功能扩展的寄存器的读写，只有当前运行环境是 hypv 时才能进行，否则触发非法指令异常。

| excp cause id | 名称      | 触发条件      | 是否可屏蔽 | excp cause info                |
| --------   | ------  | --------- | ---------- | ---------                   |
| `1 << 0`   | CFXTRAP | 功能调用      | 否 | 指令编码                        |
| `1 << 1`   | CFXMEM  | 访问核内地址空间故障 | 否 | 访存地址                        |
| `1 << 2`   | CFXREG  | 非法核芯功能扩展寄存器访问 | 否 | 指令编码                        |
| `1 << 8`   | ILLI    | 非法指令      | 否 | 指令编码                        |
| `1 << 9`   | UNDI    | 未定义指令     | 否 | 指令编码                        |
| `1 << 10`  | RASOF   | RAS上溢     | 否 | 准备压栈的返回地址                   |
| `1 << 11`  | RASUF   | RAS下溢     | 否 | 全零（无效）                      |
| `1 << 12`  | MALIGN  | 非对齐访存    | 否 | 访存地址                        |
| `1 << 13`  | IALIGN  | 取指未对齐    | 否 | PC 值                          |
| `1 << 32`  | FPEXCP  | 浮点异常      | 可 | 异常结果（浮点运算部件给出，通常为qNaN或sNaN） |

## 3. 启动与引导移交

详见 HBI 文档 §3。
