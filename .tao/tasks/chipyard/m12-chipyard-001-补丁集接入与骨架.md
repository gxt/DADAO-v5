# m12-chipyard-001: chipyard 补丁集接入 + `dadao-wuming` 最小骨架

**模块**：chipyard
**项目里程碑**：M12
**状态**：待开始
**依赖**：`ADR-0024 D1` 已就地修订（2026-11-08，用户裁定 B）

## 目标

### A. 补丁集基础设施（首次把 chipyard 纳入 v5 补丁集）

1. `manifests/components.lock.toml` 的 chipyard 条目：去掉 `patchless = true` 及其注释，加 `patch_dir = "components/chipyard/patches"`、`patch_series = "components/chipyard/series"`；role 更新为「RTL SoC 仿真（Verilator）+ DADAO 核迁入目标」。
2. 新建 `components/chipyard/patches/**` + `series`，遵 `docs/Process-01`（一文件一补丁、newfiles 用 `new file mode`、`git apply` 可重放）。
3. 本任务只收**接入所需的第一批补丁**（见 B），不含核实现。

### B. 骨架（外壳方案 B：自写最小 Tile，不继承 `CoreParams`）

4. `generators/dadao-wuming/`：`build.sbt` + 最小 Scala 源
   - `WumingTile extends BaseTile`，**自己声明** TL master/slave 端口（`TLClientNode`/`TLIdentityNode`），**不继承 `CoreParams`**
   - `WumingCoreParams` 只保留本仓库需要的字段（无 misa/PMP/mtvec/断点/异常码等 RISC-V 语义）
   - core 内部先用**桩**（复位后执行固定行为，如写一个寄存器后自旋），目的是把接线与构建跑通
5. 顶层接线补丁：`build.sbt`（新增 `wuming` project 并加入 chipyard 依赖）、`common.mk`（BootROM 来源）、`generators/chipyard/.../PeripheralFragments.scala`（bootrom 文件名）、新增 `DadaoConfigs.scala` 定义 `WumingTinyConfig`
6. **不在本任务**：Tiny 地址图（48 位 BootROM/SRAM）与 `PAddrBits` 评估（`m12-002`）、BootROM 镜像与 loadmem 闭环（`m12-003`）、semihosting（`m12-004`）

## 验收标准

1. `make apply-series` + `check-source-state` + `check-patch-tree` rc=0（chipyard 首次被补丁树门控覆盖）
2. chipyard 侧 `sbt` 编译通过（`WumingTile` 与 `WumingTinyConfig` 可解析）；构建日志含 project 名
3. Verilator 生成/编译 `WumingTinyConfig` 通过（**在 `server207` 执行**；主控机不跑 chipyard 构建）
4. 产物可执行：跑一次（桩行为），不崩溃、退出码可控
5. **不改** `spec/`、`contracts/`、`tests/`
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 技术风险（必须在完成区给结论）

- **48 位物理地址 vs chipyard 默认 `PAddrBits=32`**：本任务只需骨架跑通（可暂用 32 位），但须实测记录「`PAddrBits` 能否设为 48 / 需要哪些配套参数」，作为 `m12-002` 的输入。
- **`BaseTile` 自写端口**：不与 `CoreParams` 绑定时，`BaseTile` 的哪些抽象成员必须实现（`HartidKey`/`TileVisibilityNodeKey`/中断节点）——逐项记录。

## 说明

- **构建与运行在 `server207`**，仓库修改在主控机；两机同步用 `make fetch`/`rsync`（中转文件不放 `/tmp`）。
- 参考实现 `.cache/refs/DADAO/SOC-chipyard/`（只读溯源，非执行依赖）：它走 `BaseTile + CoreParams`，本任务按方案 B **只借接线方式，不继承语义壳**。
- 补丁导出用 `tools/infra/make_patch.py`（或等价流程）；不直接改源树作为真源。
