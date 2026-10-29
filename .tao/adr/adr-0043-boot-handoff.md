# ADR-0043: 启动与 SEE 交接

**状态**：Proposed
**日期**：2026-10-29
**关联**：ADR-0039（PTBR/PTW）、ADR-0040（PTE）、ADR-0042（cfxld/cfxst）；`spec/DADAO-12` §1/§2；任务（Step 5，待立）

## Context（背景）

复位后 PTW 关闭，pmem 还没有页表；如果启动路径能直通 pmem，就会破坏“内存窗口必须翻译”的约束。需要固定 power/hmon 的 SRAM 使用、第一张页表的建立方式、PTBR/`ptw_enable` 的时序以及交 supv 的边界。

## Decision（决策）

- **D1 复位**：复位后进入 hypv；`power` 内有 boot ROM + SRAM；`0xffff_ffff_0000` 只是跳板，不再跳 hmon 完成启动。
- **D2 hmon SRAM**：hmon 有一小块 SRAM，负责启动期同步异常；启动期不碰 pmem，不依赖页表。
- **D3 PTW 默认关**：复位 PTBR=0、`ptw_enable=0`；`high6=0` 的 CPU 访存直接 CFXMEM，不设“直通 pmem”的启动洞。
- **D4 第一张页表**：页表只在 pmem。初始化 pmem（start/size/attr）并保留页表区；用 `cfxld/cfxst` + PA 写入第一张页表；`fence cfx_pmem`；写 PTBR（PPN[55:16]）；置 `ptw_enable=1`。
- **D5 交接**：通过 VA 继续建完整页表，配置 smon/HSJU，交 smon/supv；不要求完整 HEE。
- **D6 资源边界**：页表、SRAM、pmem 不混用；hmon 启动异常处理不依赖 pmem；页表异常在 PTW 开启后进入 `cfx_ptw`。

## Rationale（理由）

启动期不直通 pmem，保证“所有内存访问都经页表”的架构约束没有例外；第一张页表用 PA DMA 写入，避免在 PTW 关闭时编造一个临时 VA 映射。hmon 只用 SRAM，保证 PTW 未就绪时仍能处理同步异常，但不需要完整 HEE。

## Consequences（影响）

- 启动代码必须先用 `cfxld/cfxst` + PA 建表，再开 PTW；不能在 PTW 关闭时访问 pmem。
- hmon SRAM 布局、页表保留区大小、power/hmon 边界仍需在 Step 5 落地前确定。
- 完整 HEE、设备直通、虚拟化不在此 ADR 范围。

## 状态说明

Step 5 待落地；本 ADR 保留 SRAM 布局/页表保留区/最小 HEE 归属为待定项。
