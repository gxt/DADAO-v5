# DADAO Hypervisor Execution Environment

> **版本：0.1.4-rc**（与 HBI 版本号一致，同步更新。基于 SimRISC 0.5.5 指令系统设计）

本文档定义 DADAO 超管系统运行环境（Hypervisor Execution Environment, HEE）的体系结构规范。

## 1. cg3 - hypv mode 寄存器

每个核芯功能扩展中针对超管模式（hypv）有以下寄存器（cg=3）。这部分寄存器的读写，只有当前运行环境是 hypv 时才能进行，否则触发 CFXREG 异常。

| cg | rc | 寄存器名 | regname | 初始值 | 访问 | 说明 |
|----|----|---------|---------|--------|------|------|
| 3 | 0 | hypv cfxtrap cfx mask | cfx_⟨cfxname⟩_hypv_cfxtrap | `0xFFFF_FFFF_FFFF_FFF7`（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`） | RW | `trap`/`escape` 控制转移，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 1 | hypv cfxmem cfx mask | cfx_⟨cfxname⟩_hypv_cfxmem | 同上 | RW | 直接 `ld/st` 访问该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 2 | hypv cfxreg cfx mask | cfx_⟨cfxname⟩_hypv_cfxreg | 同上 | RW | `cfx2rd`/`cfx2rc` 访问，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 3 | hypv cfxexe cfx mask | cfx_⟨cfxname⟩_hypv_cfxexe | 同上 | RW | 直接跳转/取指进入该 cfx，0=允许，1=屏蔽。位索引=源 cfx；自身对应位忽略 |
| 3 | 4 | hypv cfx intr mask | cfx_⟨cfxname⟩_hypv_cfx_intr_mask | 全1 | RW | 异步中断来源 cfx 掩码，0=允许，1=屏蔽。按当前 cfx 过滤 |
| 3 | 8 | hypv switch run mode | cfx_⟨cfxname⟩_hypv_switch_run_mode | 3 (hypv) | RW | 从hypv陷入时切换的运行模式 |
| 3 | 9 | hypv switch cfx mask | cfx_⟨cfxname⟩_hypv_switch_cfx_mask | 全1 | RW | 从hypv陷入时采用的 per-hart 异常掩码，0=可触发，1=屏蔽 |
| 3 | 10 | hypv excp vector | cfx_⟨cfxname⟩_hypv_excp_vector | cfxha<<42 + 0x3ff_ffff_0000 | RW | 从hypv陷入时的异常向量入口地址 |
| 3 | 11 | hypv excp mask | cfx_⟨cfxname⟩_hypv_excp_cause_mask | 全1 | RW | 异常原因掩码，0=可触发，1=屏蔽 |
| 3 | 12 | hypv cg reg delegation | cfx_⟨cfxname⟩_hypv_cg_reg_deleg | 全1 | RW | cg访问授权，bit=0时允许supv访问。bit3固定为1 |

`rc0`–`rc3` 为四类同步来源 mask，`rc4` 为异步中断来源 mask；位索引=源 cfx，`0=允许`、`1=屏蔽`，自身只绕过 cfx 轴。`rc5`–`rc7` 保留，访问触发 `CFXREG`。`cfx0`–`cfx3` 的 `cg8`/`rc1` 为 `global_cfx_intr_mask`（见 SEE §3.1）。

## 2. cfx_hmon - hypervisor monitor

hmon 为 hypv 下的同步异常处理核芯功能扩展，处理 hypv 下的同步异常。hmon 核芯功能扩展的寄存器的读写，只有当前运行环境是 hypv 时才能进行，否则触发 CFXREG 异常。

| excp cause id | 名称      | 触发条件      | 是否可屏蔽 | excp cause info                |
| --------   | ------  | --------- | ---------- | ---------                   |
| `1 << 0`   | CFXTRAP | 功能调用      | 否 | 指令编码                        |
| `1 << 1`   | CFXMEM  | 访问核内地址空间或内部存储块故障 | 否 | 访存地址 |
| `1 << 2`   | CFXREG  | 非法核芯功能扩展寄存器访问 | 否 | 指令编码                        |
| `1 << 3`   | CFXESC  | escape 帧或目标错误 | 否 | 指令编码                        |
| `1 << 7`   | CFXPERM | cfx 两轴权限拒绝 | 否 | 访存地址或指令编码 |
| `1 << 8`   | ILLI    | 非法指令      | 否 | 指令编码                        |
| `1 << 9`   | UNDI    | 未定义指令     | 否 | 指令编码                        |
| `1 << 10`  | RASOF   | RAS上溢     | 否 | 准备压栈的返回地址                   |
| `1 << 11`  | RASUF   | RAS下溢     | 否 | 全零（无效）                      |
| `1 << 12`  | MALIGN  | 非对齐访存    | 否 | 访存地址                        |
| `1 << 13`  | IALIGN  | 取指未对齐    | 否 | IP 值                          |

## 3. 启动与引导移交

详见 HBI。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.1.4-rc（未发布）

- 版本号与 HBI 同步（HBI §3 补 `HBI_<name>_INIT` 不落在 semihosting 区 `0x3FF00–0x3FFFF` 的说明）。
- cg3 按两轴权限模型重排：`rc0`–`rc3` 为 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 四类同步来源 mask，`rc4` 为 `cfx_intr_mask`；删除 `hypv_global_version` 与 `hypv_global_cfx_mask`；mask 初值与 SEE 一致（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`，其余 `0xFFFF_FFFF_FFFF_FFF7`）。
- hmon 异常原因表新增 `CFXESC`（`1 << 3`）与 `CFXPERM`（`1 << 7`）。

### 0.1.3（2026-10-26）

- cg3 寄存器 `rc1`–`rc7` 初始值由全 1 改为全 0，删除 `cfx_power` 例外。
- 删除 FPEXCP 异常。
- 为 cg0–cg3 增加 `rc0` 版本号寄存器。
- 与上游 SimRISC 0.5.5 基线对齐。
- 版本号常量同步：`hypv_global_version` = 0.1.3。
- 汇编格式迁移新格式；术语 `cfxcode`→`cfxha`。
- 术语「储存块」→「存储块」。
- 正文术语 `PC` 统一为 **`IP`**（`IP` = 当前正在执行的指令的地址，见 SimRISC-00）：异常向量现场值一列。

### 0.1.2（上游基线；导入日 2026-07-14，发布日不详）

- 上游 DADAO 超管系统运行环境（HEE）基线（基于 SimRISC 0.4.1）。
