# ADR-0043: 启动、power/hmon 分层与 SEE 交接

**状态**：Proposed
**日期**：2026-10-30
**关联**：ADR-0039（PTBR/PTW）、ADR-0040（PTE）、ADR-0042（cfx_pmem SRAM/DMA）；`spec/DADAO-12` §1/§2；任务（Step 5，待立）

## Context（背景）

复位后 PTW 关闭，pmem 还没有页表；启动路径不能直通 pmem。系统只有一份非易失 BootROM（cfx_power），hmon 只有 SRAM；需要明确 power/hmon/smon 的分层、启动 hart、第一张页表和交接方式。

## Decision（决策）

- **D1 唯一 BootROM**：非易失启动源只有 `cfx_power`（cfx63）的 BootROM；hmon 没有独立 ROM。power BootROM 把 hmon 镜像复制到 hmon SRAM，设置入口/栈/异常向量后跳转 hmon；hmon 不是独立上电启动。
- **D2 hmon 最小资源**：hmon 保留自身 cfx3、power cfx63 的复位/所有权、H-mode 异常入口、cg3；可只读 cfx_pmem/PTW 状态用于诊断；不保留普通 IO、cfx_pmem DMA 启动权、普通 pmem SRAM 数据访问。hmon SRAM 固定 **64 KiB**，独立于 power SRAM 和 pmem；布局必须包含代码/数据、启动参数、正常栈、独立的异常栈/紧急栈，禁止动态分配，保证异常/嵌套时仍有空间。
- **D3 单 hart**：当前固定 hart0 为 boot hart；其它 hart 后置。多 hart 以后用 `boot_hart_id` 硬件选择，非 boot hart 保持 reset。
- **D4 PTW 默认关**：复位 PTBR=0、`ptw_enable=0`；`addr[47:42]=0` 的 CPU 访存直接 CFXMEM，不设直通 pmem 的启动洞。
- **D5 第一张页表**：页表只在 pmem；用 `cfx_pmem` 的 64 KiB SRAM + DMA 写到 PA；DMA 完成/错误用 `dma_status`/`PMEM_DMA`；写 PTBR（PPN[55:16]），再置 `ptw_enable=1`。
- **D6 分层**：hmon 保留所有权/撤销/reset/H-mode 异常/cg3；smon 获得运行期资源管理权（cfx_pmem、cfx_ptw、cfx_cache、cfx_uart、cfx_time、cfx_hart）；启动结束后 cfx_pmem 管理权交 smon，hmon 不保留 DMA 启动权。
- **D7 交接**：hmon 配置 smon 的 masks/权限，`switch_run_mode=S`、`switch_cfx_mask=smon`、入口 PC；hmon 不退出，保留 H-mode 入口和撤销能力。跨层调用用 `trap/escape` 或 SBI 式接口，不共享 hmon SRAM。
- **D8 失败恢复**：smon 早期失败时，hmon 可清 mask、invalidate、reset；不要求 hmon 做正常 IO。

## Rationale（理由）

唯一 BootROM + hmon SRAM 保持启动源单一；power 负责加载 hmon，hmon 只做 HEE 最小职责；smon 管运行期资源，避免 HEE 变成第二套 OS。cfx_pmem DMA 解决 PTW 关闭时建表，不需要直通 pmem 或 cfxin/cfxout 指令。

## Consequences（影响）

- hmon SRAM 固定 64 KiB；代码/数据/正常栈/异常栈/紧急栈的精确布局待定。
- 第一张页表的建立顺序、hmon 入口参数、hmon 异常向量初始化待定。
- 多 hart、设备本地 DMA、完整 HEE、虚拟化后置。
- `cfx_pmem` 启动后由 smon 管理；hmon 只保留所有权/撤销和只读状态。

## 状态说明

已确认：唯一 BootROM、power 复制 hmon 镜像、单 hart hart0、hmon 最小资源、cfx_pmem 交接 smon、hmon 不保留 DMA 启动权。hmon SRAM 64 KiB 已定；入口参数/栈布局/第一张页表细节仍待定。
