# ADR-0045: CFX 访问权限与两轴异常模型

**状态**：Accepted
**日期**：2026-10-30
**接受日期**：2026-10-31
**关联**：ADR-0039（地址空间）、ADR-0040（PTE）、ADR-0042（cfx_pmem）、ADR-0043（启动）；`spec/DADAO-12` §3/§5

## Context（背景）

DADAO 的资源按 cfx 划分，运行模式与 cfx 资源是两套正交权限。旧模型的 `global_cfx_mask` 只覆盖异常触发，不覆盖跨 cfx 的直接 `ld/st`，且 `cfx2rd/cfx2rc`、`cfxld/cfxst`、`trap/escape` 各自有独立 mask，数量多、语义分散。需要统一成“运行模式 + cfx 资源”的访问模型，并明确同步异常/异步中断的权限失败语义。

## Decision（决策）

- **D1 两轴授权**：最终允许 = 运行模式允许 AND cfx 资源允许。`self` 访问只绕过 cfx 轴，不绕过运行模式轴。
- **D2 同步权限分类**：每个 cfx 的 cg0–cg3 各保留 4 个 64 位来源 cfx mask：
  - `cfxtrap`（rc0）：trap/escape 控制转移；
  - `cfxmem`（rc1）：直接 `ld/st` 访问该 cfx 的 SRAM/MMIO；
  - `cfxreg`（rc2）：`cfx2rd`/`cfx2rc`；
  - `cfxexe`（rc3）：直接跳转/取指进入该 cfx。
  - 位索引 = 源 cfx；`0=允许`、`1=屏蔽`；默认全部屏蔽，self 由 cfx 轴例外放行。
- **D3 中断权限**：每个 cfx 的 cg0–cg3 rc4 为 `cfx_intr_mask`，64 位来源 cfx 掩码；cfx0/1/2/3（umon/jmon/smon/hmon）的 cg8/rc1 为 `global_cfx_intr_mask`，64 位，按当前 mode/monitor 过滤所有中断源。二者与 `excp_cause_mask` 都允许才投递，否则 pending；`0=允许`、`1=屏蔽`。
- **D4 初值**：power 与普通 cfx 的四类同步 mask 初值 `0xFFFF_FFFF_FFFF_FFF7`（只允许 hmon）；hmon 自身 `0x7FFF_FFFF_FFFF_FFF7`（允许 hmon + power），hmon 启动后把 power 位改回 1。`cfx_intr_mask` / `global_cfx_intr_mask` 默认全 1。
- **D5 删除旧寄存器**：删除 `global_version` 和旧 `global_cfx_mask`；同步来源过滤由四类 mask 取代，异步由 `cfx_intr_mask`/`global_cfx_intr_mask` 取代；异常进入不再检查旧 `global_cfx_mask`。
- **D6 同步异常**：`CFXTRAP=1<<0`、`CFXMEM=1<<1`、`CFXREG=1<<2` 保持；四个 monitor 增加 `CFXPERM=1<<7`（同步、不可屏蔽）；每个 cfx 增加 `CFXESC=1<<3`（同步、不可屏蔽）。
  - 权限拒绝 → `CFXPERM`，不是 ILLI；
  - escape 帧/目标错误 → `CFXESC`，不是 ILLI；
  - 判定顺序：reserved cfx → ILLI；权限 → CFXPERM；escape 帧 → CFXESC；有权但地址/寄存器非法 → CFXMEM/CFXREG。
- **D7 归属**：`CFXPERM` 进当前 mode 的 monitor（U/J/S/H → umon/jmon/smon/hmon）；`CFXESC` 进当前执行 escape 的 cfx。
- **D8 escape**：`escape cfxha` 的 `cfxha` 是当前 cfx，从当前 cfx 的异常帧取现场；返回 cfx/mode/IP 来自帧；立即数仍是编译期固定偏移；不支持任意地址跳转。失败在切换前处理，不先切 cfx/mode。
- **D9 trap 自动屏蔽**：trap 进入目标 cfx 时保存目标当前 mode 的 `global_cfx_intr_mask` 并置全 1；异步中断只 pending；目标可自行打开，但必须自行处理嵌套；escape 恢复保存值。
- **D10 U/J**：umon 不做 escape 检查的前提是 U-mode 禁止执行 escape；jmon 当前不配 SRAM/代码，仅保留向量地址。

## Rationale（理由）

两轴模型避免“某个模式天然能访问所有资源”；四个同步 mask 将寄存器、内存、执行、trap/escape 分开，权限拒绝不再伪装成 ILLI。`cfx_intr_mask` 与 `global_cfx_intr_mask` 分离来源过滤和模式级过滤；trap 自动屏蔽保证单帧不被异步中断覆盖。删除旧 `global_cfx_mask` 后，同步/异步各有明确替代。

## Consequences（影响）

- cg0–3 寄存器布局重排，旧 `global_version`/`global_cfx_mask`/`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst`/`trap`/`escape` mask 需要合并迁移。
- 异常原因表新增 `CFXPERM`/`CFXESC`，QEMU/OS/测试需同步。
- `escape` 的 `cfxha` 语义固定为当前 cfx，不再表示返回目标；返回目标来自帧。
- 帧管理/`frame_active`、异步重入同 cfx、jmon 代码、用户态测试仍待后续决定。

## 状态说明

本 ADR 只冻结权限模型和异常归属；`frame_active`、异步重入、jmon 代码/用户态测试不在本 ADR。

**接受记录**：用户 2026-10-31 确认 D1–D10 已讨论，ADR 转 `Accepted`；范围外项仍按上句后置。
