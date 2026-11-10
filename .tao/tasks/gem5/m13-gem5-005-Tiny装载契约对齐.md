# m13-gem5-005: gem5 对齐 Tiny hmon 装载契约（BootROM 固定固件 + power 搬运）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-001`（Tiny hmon 已实现）+ `m13-gem5-004`（SE 修复）、`m12-spec-004`（契约已合入）
**可并行分片**：否（组件单写者）
**状态**：待开始

## 背景

`m12-spec-004` 已把 Tiny 的 hmon 装载改成：

- BootROM 是**固定固件镜像**（64 KiB：power 8K / hmon 8K / 保留 40K 全零 / 表 8K）
- power 校验 image index table → **逐 8 字节复制** hmon 段到 hmon SRAM `0x0fff_0000_0000` → 写向量（幂等）→ `trap cfx_hmon, 0x30001` → hmon `escape` 回 stub → 跳 `0xffff_ff01_0100`
- 宿主 loader **只装应用段**（`PT_LOAD` 只允许落 SRAM；向 BootROM 下发段或 `e_entry ≠ 0xffff_ff01_0100` ⇒ 显式失败）
- `crt` 与测试程序一起链接、整体落 SRAM
- `cg3 rc10`：初值 = 该 cfx 内部 SRAM 起始；写入忽略低 2 位
- `switch_run_mode`：Tiny 写入被忽略、保存值保持 3、读回保存值

`m13-gem5-001` 实现的是**旧的**「宿主直装 hmon 段」；`m12-chipyard-007` 已按新契约实现（BootROM 固件 + power 搬运）。

**用户裁定**：这条契约「先在 qemu 中验证，然后 gem5/chipyard 可共用」——gem5 以 QEMU 的结论为准——本任务即 gem5 侧的对齐（QEMU 侧由 `m13-qemu-002` 并行做，契约以其为准）。

## 目标

1. **装载路径**：gem5 的 Tiny 装载改为「固定 BootROM 固件 + 应用」两件；宿主不再向 BootROM 下发 `PT_LOAD`；`e_entry` 必须 = `0xffff_ff01_0100`；违规**显式失败**（非默默忽略）。
2. **镜像格式**：支持 `bootrom-image`（64 KiB 原样装入 `0xffff_ffff_0000`）；image index table 格式与 `§6.1` 一致（magic `DBOT`、version 1、count 1、`boot_magic=0x30001`）。
3. **power 行为**：若 gem5 以「执行固件」方式实现，需真实执行 power stub 的复制逻辑；若以「模型直接映射」方式实现，**必须**在日志/状态上等价（hmon 段落在 hmon SRAM、向量已写），并在任务书里说明选择与理由。
4. **`rc10` 与 `switch_run_mode`**：按 `spec-003/004` 口径对齐（写未对齐 ⇒ 掩掉低 2 位；Tiny 的 `switch_run_mode` 读回 3）。
5. **与 chipyard 共用**：用 `m12-chipyard-007` 的 BootROM 镜像与同一 app ELF，在 gem5 上跑通；给出逐字节对齐证据（hmon 在 SRAM 的内容、向量值、入口）。

## 非范围

- 不改 QEMU（`m13-qemu-002`）
- 不改 chipyard
- 不改 spec

## 验收标准

1. 新契约下 `power → hmon → app` 闭环在 gem5 上可观测（向量写入、`trap` magic、hmon 入口、`escape` 返回、跳入口）
2. 反例三条各 rc≠0 且报错具名：向 BootROM 下发 `PT_LOAD`、`e_entry ≠ 0xffff_ff01_0100`、BootROM 镜像非 64 KiB
3. 与 chipyard 共用同一 `bootrom.tiny.img` + 同一 app ELF：hmon SRAM 内容**逐字节相同**、入口/向量一致
4. `rc10` 未对齐写入 ⇒ 掩低 2 位；`switch_run_mode` 写 0 ⇒ 读回 3
5. 回归：`tests/inst` Tiny 子集 44/44、Vast 980/985 不变；`check-inst`/`check-arch-smoke`/L2 rc=0
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 组件单写者；补丁走 `make_patch`。
- 若 gem5 侧无法真实执行 power 固件（只做模型映射），**必须在任务书写明等价条件与限制**，不得静默降级。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
