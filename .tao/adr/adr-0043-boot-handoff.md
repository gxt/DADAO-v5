# ADR-0043: 启动、power/hmon 分层与 SEE 交接

**状态**：Accepted（rev. 2026-11-02: `D1`/`D2`/`D3`/`D10`/`D12` 按 Tiny/Node 两 profile 就地修订）
**日期**：2026-10-30
**接受日期**：2026-10-31
**关联**：ADR-0039（PTBR/PTW）、ADR-0040（PTE）、ADR-0042（cfx_pmem）、ADR-0045（权限）；`spec/DADAO-12` §1/§2

## Context（背景）

复位后 PTW 关闭，pmem 还没有页表；启动路径不能直通 pmem。系统只有一份非易失 BootROM（cfx_power），hmon/smon 只有 SRAM；需要明确 power/hmon/smon 的分层、唯一 BootROM、启动 hart、镜像格式、第一张页表和交接方式。

## Decision（决策）

- **D1 唯一 BootROM（大小由平台 profile 规定）**：非易失启动源只有 `cfx_power`（cfx63）的 BootROM；hmon 没有独立 ROM。BootROM 自 `2^48` 向下，**大小 ≥64 KiB、由平台规范规定**：`Machine-v5-Tiny` 为 64 KiB（`0xffff_ffff_0000`–`0xffff_ffff_ffff`）、`Machine-v5-Node` 为 4 MiB（`0xffff_ffc0_0000`–`0xffff_ffff_ffff`）；复位向量两 profile 均为末 64 KiB 起点 `0xffff_ffff_0000`。`power` 不设 SRAM 属**本机约定**（非架构禁令）。
- **D2 BootROM 布局（`Machine-v5-Node`）**：偏移 0 放 image index table；其后放 ELF 镜像；最后 64 KiB（`0xffff_ffff_0000` 起）留给复位/启动代码。表项至少 `offset/size/type/flags`，ELF 提供 `e_entry`/`PT_LOAD`/BSS；表和镜像按 8/16 字节对齐。`Machine-v5-Tiny` 的 64 KiB BootROM **无 image index table**，全部为复位/启动 stub。
- **D3 镜像加载**：`Machine-v5-Node` 下 power 只把 hmon ELF 复制到 hmon SRAM；hmon 配好权限后把 smon ELF 复制到 smon SRAM；smon 再按需加载设备服务。Power 不设 SRAM 属本机约定，复制循环只用寄存器/无栈。`Machine-v5-Tiny` **无 power→hmon 复制链**：测试镜像由宿主 loader 按 `PT_LOAD` 装入 BootROM/SRAM，BootROM 内的启动 stub 直接跳应用入口。
- **D4 hmon SRAM**：hmon SRAM 固定 64 KiB，起始 `0x0fff_0000_0000`；H-mode 异常向量默认等于该起始地址；hmon 入口自己设置 `rbsp`。
- **D5 smon SRAM**：smon SRAM 64 KiB，起始 `0x0bff_0000_0000`；S-mode 异常向量默认等于该起始地址；smon 入口自己设置 `rbsp`。
- **D6 umon/jmon**：umon 无 SRAM，异常向量 `0x03ff_0000_0000`；jmon 当前不配 SRAM/代码，向量 `0x07ff_0000_0000`；当前不启用 U/J 异常处理代码。
- **D7 启动 hart**：当前单 hart，固定 hart0；多 hart 以后用 `boot_hart_id` 硬件选择，非 boot hart 保持 reset。
- **D8 power→hmon**：power 设置 hmon 的 H-mode 向量、权限和 `BOOT_HMON_MAGIC`，执行 `trap cfx_hmon, BOOT_HMON_MAGIC`；hmon 入口检查 `CFXTRAP` + magic，否则按普通异常处理。hmon 不依赖 pmem/PTW。
- **D9 hmon→smon**：hmon 设置 smon 的 S-mode 向量、栈由 smon 自己设置、开放所有运行期 cfx 权限（pmem/ptw/cache/uart/time/hart/llc/设备），不开放 hmon/power；执行 `trap cfx_smon, BOOT_SMON_MAGIC`。smon 入口检查 magic。
- **D10 第一张页表**：smon 用 cfx_pmem SRAM + DMA 把 64 KiB 全零页表页写到 PA 0（PTBR=0），在 L1 index `0x1000`–`0x1003` 写 4 个 512 MiB 超页 PTE：`VA 0x0200_0000_0000–0x0200_7fff_ffff → PA 0–2 GiB`；每项 `S=1,U=J=H=0,R=W=X=1,P=1,SP=1,SPF=0xFF`，A/D 硬件维护。
- **D11 PTW 开启**：smon 写 `cfx_ptw_ptbr=0`，再置 `cfx_ptw_enable=1`；写不隐含 TLB invalidate，TLB 复位为空；随后用 `VA 0x0200_0000_0000` 验证读写 PA 0。
- **D12 内核空间**：内核高半区从 `0x0200_0000_0000` 开始；低 2 TiB 为用户空间。第一版映射内核 2 GiB（4 个超页覆盖 PA `[0, 2 GiB)`），用户页表后置。`Machine-v5-Tiny` 不设内核空间与页表。
- **D13 分层/交接**：hmon 保留所有权、H-mode 异常、cg3、reset/撤销；smon 获得运行期资源管理；启动后 cfx_pmem 交 smon；hmon 不保留 DMA 启动权；poweroff/reset 由 smon 通过 hmon 的 trap 服务完成。
- **D14 park**：power 在 trap hmon 后进入 BootROM park/复位等待；hmon 在 trap smon 后进入 H-mode park/异常等待，不返回 power。
- **D15 权限模型**：按 ADR-0045 两轴模型；trap 进入目标 cfx 时自动保存并屏蔽 `global_cfx_intr_mask`，escape 恢复；本 ADR 不重复寄存器细节。

## Rationale（理由）

唯一 BootROM 保持启动源单一；power 只负责最小加载/授权；hmon 最小化，smon 负责页表、PTW 和设备。ELF 复用现有工具链，image index table 只做定位；内核高半区 + 单个超页 PTE 让最小页表只需一项即可启动。

## Consequences（影响）

- BootROM 大小由平台 profile 规定（Tiny 64 KiB / Node 4 MiB），power 不设 SRAM 属本机约定，hmon/smon 64 KiB、umon/jmon 无 SRAM 需同步地址表。
- image index table/ELF/BSS/对齐需要工具链生成和 hmon 加载器支持（`Machine-v5-Node`）；Tiny 由宿主 loader 直接按 `PT_LOAD` 装入。
- smon 需要 cfx_pmem DMA、cfx_ptw 寄存器、PTBR/PTW 初始化；hmon 需 trap magic/权限设置。
- `frame_active`、异步重入同 cfx、jmon 代码、用户态测试仍后置。

## 状态说明

已确认：唯一 BootROM（大小由平台 profile 规定）、power 不设 SRAM（本机约定）、hmon/smon 64 KiB、镜像复制链、trap magic、页表/PTW、超高区映射、park。帧管理、异步重入、jmon、用户态测试未定。

**接受记录**：用户 2026-10-31 确认 D1–D15 已讨论，ADR 转 `Accepted`；帧管理、异步重入、jmon、用户态测试仍不在本 ADR 范围。

## 修订

**rev. 2026-11-02（用户 2026-11-02 逐条确认，`SPEC-183t`）**：按 `Machine-v5-Tiny` / `Machine-v5-Node` 两 profile 就地修订启动与装载口径。

- `D1`：BootROM 大小由平台 profile 规定（Tiny 64 KiB / Node 4 MiB），复位向量均为 `0xffff_ffff_0000`（末 64 KiB 起点）；「power 不设 SRAM」改为**本机约定**（非架构禁令）。
- `D2`：image index table + ELF + 末 64 KiB 复位代码的布局限 `Machine-v5-Node`；Tiny 的 64 KiB BootROM 无 index table。
- `D3`：`Machine-v5-Tiny` 无 power→hmon 复制链，测试镜像由宿主 loader 装入 BootROM/SRAM。
- `D10`/`D12`：Node 第一张页表改为 L1 4 个 512 MiB 超页覆盖 PA `[0, 2 GiB)`（VA `0x0200_0000_0000`–`0x0200_7fff_ffff`），`SPF=0xFF`；`D11` 的 PTBR/PTW 开启与验证不变。
- **用户原话（经主会话转达）**：「Node：BootROM 4 MiB `0xffff_ffc0_0000`..、复位 `0xffff_ffff_0000`；PA RAM 2 GiB；hmon 建 L1 4×512 MiB 超页、`SPF=0xFF`、PTW/hypv；smon 路径保留」「不做双映射；不保留旧 Machine-01 几何」「用户已逐条确认 ADR-0004/0039/0040/0043 四项修订」；逐条口径见 `.tao/tasks/spec/SPEC-183t-Machine-v5-Tiny-Node规范收口.md`。
- **流程说明**：本次为经用户逐条确认的**就地修订**（`Process-03` 一般规则为「决策变更时新增 ADR 或标注 `Superseded`」，此处为经授权的例外；`**状态**` 行已标 `rev. 2026-11-02`）。
