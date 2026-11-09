# m13-qemu-001: QEMU 的 Tiny `cfx_power` + `cfx3 hmon`（M13 前置）

**模块**：qemu
**项目里程碑**：M13
**依赖**：无（可与 `m12-chipyard-007` 并行；**验收要求三平台一致**）
**可并行分片**：否（组件单写者）
**状态**：待开始

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，决策 2 = A）；**无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**（实现上仍只看 `immu18`，不判断 cfxha）
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon
- **排期**：QEMU/gem5 侧排在 **M13 前置**；chipyard 侧在 M12（`m12-chipyard-007`）

## 目标

1. `cfx_power`（cfx63）：Tiny 启动移交 `power → hmon`（与 Vast 同构）。
2. `cfx3 hmon`：寄存器组（`excp_cause`/`excp_vector`/四类同步 mask/`cfx_intr_mask`/`switch_run_mode`）；同步异常（ILLI/UNDI/`CFXMEM`/`MALIGN`/`IALIGN`）进 hmon 向量。
3. **IALIGN 时 IP 停留在非法地址**（`DADAO-12 §5`），不写回 `nextIp`。
4. `trap` 区分：`immu18` 区间判定 semihosting vs hmon；semihosting 统一 `trap cfx_hmon`。
5. **地址图**：Tiny 增加 hmon SRAM `0x0fff_0000_0000`（64 KiB）。
6. **与 chipyard 一致**：同一 ELF 在 QEMU 与 chipyard 上的异常行为（`excp_cause`、IP 停留、退出码）逐条一致。

## 验收标准

1. `cfx_power → hmon` 移交可观测（运行模式与 PC）
2. 五类同步异常各至少 3 例进 hmon，`excp_cause` 正确
3. **IALIGN 时 IP 停在非法地址**（专门断言）
4. semihosting 的 `trap cfx_hmon` 与 `trap cfx63` 都能工作（`immu18` 判定不依赖 cfxha）
5. **与 chipyard 的三平台一致**（同一 ELF 逐条比对；chipyard 侧由 `m12-chipyard-007` 提供）
6. 现有 Tiny 测试零回归（`check-inst` / `check-arch` / tset 相关）
7. 构建/门控：`build-qemu` / `install-host` / `check-patch-tree` / `check-source-state` / L1 / L2 rc=0
8. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
9. 完成区 ≤30 行、无运行期路径

## 非范围

- 不改 chipyard 侧（`m12-chipyard-007`）
- 不实现 smon（Tiny 不实现）
- 不改 spec（`Machine-v5` 的 Tiny hmon 由 SPEC 任务先落地；本任务按 spec 实现）

## 说明

- **前置**：spec 的 Tiny hmon 修订必须先落地（见 M13 的 SPEC 任务），否则本任务无依据。
- 组件单写者；节点操作后 `make sync-node-repo`。
