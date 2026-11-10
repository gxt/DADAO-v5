# m12-chipyard-007: Tiny 的 `cfx_power` + `cfx3 hmon`（异常进向量）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-006`（设计）+ `m12-spec-004`（hmon 装载契约/rc10 口径）+ `m12-spec-003`（口径统一）——三者均已合入
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 用户裁定（2026-11-10 实现基线，R1–R16 + 补充）

- **R1 = C**：移位/位操作 2 拍、简单算术 1 拍；**以 1 GHz 时序可行**为约束
- **R2**：乘法周期可配（初值 3 拍），评测后再定；考虑面积
- **R3 = A**（radix-4），保留 radix-2 备选
- **R4 = A**：按 hardfloat 设计移植（不引入 Chisel 依赖）
- **R5**：预取缓冲 **8 beat（64 B，`FETCH_DEPTH=8`）**
- **取指与访存用两个 TileLink**（M12 就拆）：`IdRange(0,3)`，两个独立 `TLBundle` 与状态机
- **power SRAM（8 MiB）与 hmon SRAM（64 KiB）是两个不同 SRAM**
- **R7**：`ldm`/`stm` 整段预检 + **逐个元素精确重入**（整条指令可重执行，不记进度）；**中途总线拒绝 ⇒ 报当前运行模式 `CFXMEM`**
- **R8**：寄存器堆 2 读 2 写（做不到则保守 1 读 1 写并说明）
- R9–R12 = A（1 条/拍、`swym` 1 拍、M12 不流水、扩展 + 较大改动 005 核）
- **R13**：hmon 编入 BootROM，power 搬运（`Machine-v5 §6.1/§6.2`）
- **R14 = A**：新写最小 Tiny hmon handler（8 KiB 上限）
- **R15 = B**（当前版本无嵌套）、**R16 = B**（去掉硬件 `halted` 兜底）

### BootROM 固定固件布局（`Machine-v5 §6.2`）

| 偏移 | 内容 | 大小 |
|---|---|---|
| `0x0000`–`0x1FFF` | power 启动 stub | 8 KiB |
| `0x2000`–`0x3FFF` | hmon 运行段 | 8 KiB（校验阈值） |
| `0x4000`–`0xDFFF` | 保留区（必须全零） | 40 KiB |
| `0xE000`–`0xFFFF` | image index table | 8 KiB |

- `crt` **与测试程序一起链接**、整体落 SRAM；入口固定 `0xffff_ff01_0100`；宿主只装 SRAM。
- `cg3 rc10` 初值 = 该 cfx 内部 SRAM 起始；写入忽略低 2 位。

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，同 Vast，决策 2 = A）
- **无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **三平台 Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**（实现上仍只看 `immu18`，不判断 cfxha）
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon

## 目标

1. **`cfx_power`（cfx63）**：Tiny 的启动移交路径 `power → hmon`（与 Vast 同构），按 `DADAO-12 §5.2` 的 trap 移交语义。
2. **`cfx3 hmon`**：
   - hmon 寄存器组（`excp_cause`/`excp_vector`/四类同步 mask/`cfx_intr_mask`/`switch_run_mode`）
   - 同步异常（ILLI/UNDI/`CFXMEM`/`MALIGN`/`IALIGN`）进 hmon 向量：**IP 停留语义按 `DADAO-12 §5`**（IALIGN 时 IP 停在非法地址，不写回 `nextIp`）
   - hmon 可 `escape` 回测试本体（用户态/hypv 测试体）
3. **`trap` 区分**：`immu18` 区间判定 semihosting vs hmon；semihosting 统一用 `trap cfx_hmon`。
4. **地址图**：Tiny 增加 hmon SRAM `0x0fff_0000_0000`（64 KiB），与 BootROM/SRAM 并存。
5. **BootROM 固件与搬运**：power stub（≤8 KiB）校验 image index table（`§6.1` 格式、`count=1`、`boot_magic=0x30001`）→ 逐 8 字节复制 hmon 段到 hmon SRAM → 写向量（幂等）→ `trap cfx_hmon, 0x30001` → hmon `escape` 回 stub → power 跳 `0xffff_ff01_0100`。
6. **最小 hmon handler**（≤8 KiB）：入口即向量；分派 `CFXTRAP`/五类同步异常；算退出码 → `SYS_EXIT`；`escape +0/+4` 返回。
7. **双 TL 端口**：取指与访存各一个 `TLBundle`（`IdRange(0,3)`），取指缓冲 8 beat。
8. **回归**：bootrom 启动、loadmem、semihosting 闭环、005 的 273 例整数测试**全部不回归**。

## 验收标准

0. **BootROM 镜像可构建**：构建器产出恰好 64 KiB 镜像（布局符合上表），`boot_magic`/`offset`/`size`/`flags` 与 `§6.1` 一致
1. `cfx_power → hmon` 移交可观测（打印/断言移交前后的运行模式与 PC）
2. 五类同步异常各至少 3 例进 hmon 向量，`excp_cause` 正确
3. **IALIGN 时 IP 停在非法地址**（专门断言）
4. semihosting 的 `trap cfx_hmon` 与 `trap cfx63` 都能工作（`immu18` 判定不依赖 cfxha）
5. 005 的 273 例整数测试**零回归**（逐字节一致）
6. Verilator 构建 rc=0（**主控机**）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- QEMU/gem5 的 Tiny hmon（按用户决策，**排在 M13 前置**）
- 访存/控制流/FP（`008` 起）
- smon（Tiny 不实现）

## 说明

- 与 `006` 的设计定稿保持一致；若实现中发现设计需调整，**停下报告**（不要自行改设计）。
- **构建与调试在主控机**（用户 2026-11-10：chipyard 后续构建/调试一律主控机）；小规模仿真也在主控机。**长仿真才上节点**（且节点须自行构建，Verilator 产物机器相关，不跨机复制）。仓库修改在主控机；节点操作后 `make sync-node-repo`。
