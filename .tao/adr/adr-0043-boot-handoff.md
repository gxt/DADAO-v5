# ADR-0043: 启动、power/hmon 分层与 SEE 交接

**状态**：Proposed
**日期**：2026-10-30
**关联**：ADR-0039（PTBR/PTW）、ADR-0040（PTE）、ADR-0042（cfx_pmem）、ADR-0045（权限）；`spec/DADAO-12` §1/§2

## Context（背景）

复位后 PTW 关闭，pmem 还没有页表；启动路径不能直通 pmem。系统只有一份非易失 BootROM（cfx_power），hmon/smon 只有 SRAM；需要明确 power/hmon/smon 的分层、唯一 BootROM、启动 hart、镜像格式、第一张页表和交接方式。

## Decision（决策）

- **D1 唯一 BootROM**：非易失启动源只有 `cfx_power`（cfx63）的 BootROM；hmon 没有独立 ROM。BootROM 256 KiB，范围从高地址向下 `0xffff_fffc_0000`–`0xffff_ffff_ffff`；复位向量保持 `0xffff_ffff_0000`。power 不设 SRAM。
- **D2 BootROM 布局**：偏移 0 放 image index table；其后放 ELF 镜像；最后 64 KiB（`0xffff_ffff_0000` 起）留给复位/启动代码。表项至少 `offset/size/type/flags`，ELF 提供 `e_entry`/`PT_LOAD`/BSS；表和镜像按 8/16 字节对齐。
- **D3 镜像加载**：power 只把 hmon ELF 复制到 hmon SRAM；hmon 配好权限后把 smon ELF 复制到 smon SRAM；smon 再按需加载设备服务。Power 不设 SRAM，复制循环只用寄存器/无栈。
- **D4 hmon SRAM**：hmon SRAM 固定 64 KiB，起始 `0x0fff_0000_0000`；H-mode 异常向量默认等于该起始地址；hmon 入口自己设置 `rbsp`。
- **D5 smon SRAM**：smon SRAM 64 KiB，起始 `0x0bff_0000_0000`；S-mode 异常向量默认等于该起始地址；smon 入口自己设置 `rbsp`。
- **D6 umon/jmon**：umon 无 SRAM，异常向量 `0x03ff_0000_0000`；jmon 当前不配 SRAM/代码，向量 `0x07ff_0000_0000`；当前不启用 U/J 异常处理代码。
- **D7 启动 hart**：当前单 hart，固定 hart0；多 hart 以后用 `boot_hart_id` 硬件选择，非 boot hart 保持 reset。
- **D8 power→hmon**：power 设置 hmon 的 H-mode 向量、权限和 `BOOT_HMON_MAGIC`，执行 `trap cfx_hmon, BOOT_HMON_MAGIC`；hmon 入口检查 `CFXTRAP` + magic，否则按普通异常处理。hmon 不依赖 pmem/PTW。
- **D9 hmon→smon**：hmon 设置 smon 的 S-mode 向量、栈由 smon 自己设置、开放所有运行期 cfx 权限（pmem/ptw/cache/uart/time/hart/llc/设备），不开放 hmon/power；执行 `trap cfx_smon, BOOT_SMON_MAGIC`。smon 入口检查 magic。
- **D10 第一张页表**：smon 用 cfx_pmem SRAM + DMA 把 64 KiB 全零页表页写到 PA 0（PTBR=0），在 L1 index `0x1000` 写一个 512 MiB 超页 PTE：`VA 0x0200_0000_0000–0x021f_ffff_ffff → PA 0–512 MiB`；`S=1,U=J=H=0,R=W=X=1,P=1,SP=1,SPF=0xFF`，A/D 硬件维护。
- **D11 PTW 开启**：smon 写 `cfx_ptw_ptbr=0`，再置 `cfx_ptw_enable=1`；写不隐含 TLB invalidate，TLB 复位为空；随后用 `VA 0x0200_0000_0000` 验证读写 PA 0。
- **D12 内核空间**：内核高半区从 `0x0200_0000_0000` 开始；低 2 TiB 为用户空间。第一版只映射内核 512 MiB，用户页表后置。
- **D13 分层/交接**：hmon 保留所有权、H-mode 异常、cg3、reset/撤销；smon 获得运行期资源管理；启动后 cfx_pmem 交 smon；hmon 不保留 DMA 启动权；poweroff/reset 由 smon 通过 hmon 的 trap 服务完成。
- **D14 park**：power 在 trap hmon 后进入 BootROM park/复位等待；hmon 在 trap smon 后进入 H-mode park/异常等待，不返回 power。
- **D15 权限模型**：按 ADR-0045 两轴模型；trap 进入目标 cfx 时自动保存并屏蔽 `global_cfx_intr_mask`，escape 恢复；本 ADR 不重复寄存器细节。

## Rationale（理由）

唯一 BootROM 保持启动源单一；power 只负责最小加载/授权；hmon 最小化，smon 负责页表、PTW 和设备。ELF 复用现有工具链，image index table 只做定位；内核高半区 + 单个超页 PTE 让最小页表只需一项即可启动。

## Consequences（影响）

- BootROM 256 KiB、power 无 SRAM、hmon/smon 64 KiB、umon/jmon 无 SRAM 需要同步地址表。
- image index table/ELF/BSS/对齐需要工具链生成和 hmon 加载器支持。
- smon 需要 cfx_pmem DMA、cfx_ptw 寄存器、PTBR/PTW 初始化；hmon 需 trap magic/权限设置。
- `frame_active`、异步重入同 cfx、jmon 代码、用户态测试仍后置。

## 状态说明

已确认：唯一 BootROM、power 无 SRAM、hmon/smon 64 KiB、镜像复制链、trap magic、页表/PTW、超高区映射、park。帧管理、异步重入、jmon、用户态测试未定。
