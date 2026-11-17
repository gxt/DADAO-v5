# DADAO Hypervisor Execution Environment

> **版本：0.1.4-rc**（与 HBI 版本号一致，同步更新。基于 SimRISC 0.5.5 指令系统设计）

本文档定义 DADAO 超管系统运行环境（Hypervisor Execution Environment, HEE）的体系结构规范。

## 1. cg3 - hypv mode 寄存器

本节正文见 SEE `§3.4 cg3 - hypv mode 寄存器`。

## 2. cfx_hmon - hypervisor monitor

本节正文见 SEE `§4.4 cfx_hmon - hypervisor monitor`；异常原因编码与 `cfx_umon` 同表（见 `§4.1 cfx_umon - user monitor`），`CFXMEM`/`CFXPERM` 的 `cause_info` 与子原因见 SEE `§3.6 cg5 - 异常现场寄存器`。

## 3. 启动与引导移交

详见 HBI。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开。

### 0.1.4-rc（未发布）

- 第 1、2 章正文并入 SEE：`cg3` 寄存器表与 `rc10` 初值/写入口径见 SEE `§3.4 cg3 - hypv mode 寄存器`，hmon 说明段见 SEE `§4.4 cfx_hmon - hypervisor monitor`；本册两节只保留引用，章节编号保留作锚点。依据原话：「请把 DADAO-13 的第一章第二章移动至 DADAO-12，DADAO-13 只保留个引用就行。」

- `cfx_⟨cfxname⟩_hypv_excp_vector`（`cg3 rc10`）**必须有初值 = 该 cfx 内部 SRAM 的起始地址**（无内部 SRAM 的 cfx 由平台/实现定义）；写入**忽略低 2 位**（`value[1:0] ← 0`，4 字节对齐落盘），不产生异常。

- 版本号与 HBI 同步（HBI §3 补 `HBI_<name>_INIT` 不落在 semihosting 区 `0x3FF00–0x3FFFF` 的说明）。
- cg3 按两轴权限模型重排：`rc0`–`rc3` 为 `cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` 四类同步来源 mask，`rc4` 为 `cfx_intr_mask`；删除 `hypv_global_version` 与 `hypv_global_cfx_mask`；mask 初值与 SEE 一致（hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`，其余 `0xFFFF_FFFF_FFFF_FFF7`）。
- hmon 异常原因表新增 `CFXESC`（`1 << 3`）与 `CFXPERM`（`1 << 7`）。
- `CFXPERM` 的 `excp cause info` 收敛为**地址**（不再有「或指令编码」第二种形态）：页表/`cfxmem` 权限拒绝 = 访存地址，`cfxexe` 拒绝 = 目标 IP，`cfxtrap`/`cfx2rd`/`cfx2rc` 拒绝 = 触发指令地址（与 `excp_cause_ip` 同值，见 SEE `§3.6`）；`CFXMEM` 的 `info` 口径不变。
- 删除无效屏蔽寄存器定义：`switch_cfx_mask`（`cg3` `rc9`）与 `excp_cause_mask`（`cg3` `rc11`）保留编号并标为 `reserved`（访问 ⇒ `CFXREG`）。

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
