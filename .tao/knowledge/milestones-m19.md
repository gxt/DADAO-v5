# 项目里程碑

> **项目里程碑 = M19**（M19 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12–M18、M20 各另有分册）

> **本页只维护 M19 任务台账**：历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M19 定位（用户 2026-11-20）**：**FPGA-Tiny**（Genesys2 `XC7K325T`，无 DDR、裸机）——先把 **Vivado 流程 + 板上签名流回传 + 真实周期/资源实测** 打通；**第一次只上 wuming**（wuqing 归 M20 之后的机型）。**FPGA-Vast 归「未立册方向」，不预留里程碑号**。
> **前置**：`m16-chipyard-010`（I-Cache）完成；Vivado 装在部分节点（用户 2026-11-20，`nodes.md` 更新后按 `remote.py status` 选机；版本须锁进 `manifests/`）。
> **收口判据（草案）**：板上跑通 `tests/inst` 代表例 ≥10 且签名流与 QEMU 逐字节相等；资源（LUT/FF/BRAM/DSP）与周期实测报告落盘并回喂 gem5 周期表。
> **后续（未拆，见 `discussing.md`）**：板上周期/资源实测与 gem5 对照；wuqing 上 Tiny 的排期；FPGA-Vast 的前置清单（未立册方向）。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m19-gem5-003 | 2–4 h | `check_tiny_hmon` 迁新几何/hmon 数据区 0xC00 |
| m19-integ-001 | 4–8 h | 新几何下 QEMU/gem5/chipyard 三平台签名/退出一致性 |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m19-chipyard-004 | 2026-11-27 22:59 | 4–8 h | chipyard Tiny 配置迁移到新几何与 8K BootROM |
| m19-chipyard-003 | 2026-11-27 23:02 | 4–8 h | chipyard RTL 实现 `swym N`（12 位、1+N、原子）并补 Verilator 用例 |
| m19-testcases-005 | 2026-11-28 08:40 | 4–8 h | 启动固件 power/hmon 迁移：8 KiB ROM 可启动、hmon 数据槽定案 |
| m19-testcases-001 | 2026-11-28 08:39 | 2–4 h | `swym N` 测试程序：1/2/4096 拍、高位 ILLI、原子中断 |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m19-gem5-001 | 2026-11-28 08:52 | gem5 `swym N`：12 位、1+N、高位 ILLI、原子；reviewer Accepted |
| m19-gem5-002 | 2026-11-28 08:52 | gem5 Tiny profile 新 ROM/RAM/hmon/entry/DUMP/guard；reviewer Accepted |
| m19-infra-002 | 2026-11-28 08:52 | picolibc Tiny 地址图（entry 0x2000、SP 0x3F000、EXIT 0x30）；版本号未升 |
| m19-qemu-001 | 2026-11-28 08:52 | QEMU Tiny 新 ROM/RAM/hmon/entry/DUMP 与装载校验；reviewer Accepted |
| m19-spec-002 | 2026-11-28 08:52 | Tiny 新几何/启动 ABI：8K ROM、8K hmon、256K SRAM、entry 0x2000；reviewer Accepted |
| m19-testcases-002 | 2026-11-28 08:52 | ee-tiny/inst 新布局（entry 0x2000、signature 0x1000、DUMP 0x800、SP/MemRAS）；reviewer Accepted |
| m19-testcases-003 | 2026-11-28 08:52 | 宿主工具 DUMP 0x800/EXIT 0x30/BootROM 8 KiB 构建器；reviewer Accepted |
| m19-testcases-004 | 2026-11-28 08:52 | tests/arch 15 份探针迁 entry 0x2000/SP/EXIT/DUMP；运行期 BLOCKED 待合入后判 |
| m19-spec-001 | 2026-11-27 23:15 | swym N 语义：12 位、高位 SBZ/ILLI、1+N、原子；reviewer Accepted |
| m19-infra-001 | 2026-11-23 08:54 | 207/208 装 Vivado 2025.1（逐字节对账一致）+ `XILINXD_LICENSE_FILE` 三路口径 + 两节点综合 rc=0；208 写 35 MB/s = 写通 RAID5 的 IOPS 上限（非坏盘） |
