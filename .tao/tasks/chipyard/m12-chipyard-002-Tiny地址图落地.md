# m12-chipyard-002: Tiny 地址图落地（48 位核内地址）

**模块**：chipyard
**项目里程碑**：M12
**状态**：待开始
**依赖**：`m12-chipyard-001`（骨架 + 补丁集）

## 背景与事实

- `spec/Machine-v5 §1.1`：Tiny 的 BootROM `0xffff_ffff_0000`（64 KiB，复位向量 = 起始）、SRAM `0xffff_ff00_0000`（8 MiB）；均为 **48 位核内地址**，Tiny **无 MMU、无 cfx**。
- `m12-chipyard-001` 实测：`xLen=64` + `useVM=false` ⇒ `BaseTile.maxPAddrBits=64`；但 **stock chipyard 地址图协商出 `paddrBits=32`** ⇒ 必须改地址图，不是改 `PAddrBits`。
- 相关平台已一致：QEMU 的 `dadao-tiny`（`m12-qemu-001`）与 gem5 FS 的 Tiny profile 用的就是这两个基址。

## 目标

1. 在 chipyard 侧把 BootROM 与 SRAM 放到 spec 规定的地址：
   - `WithBootROM`：地址 `0xffff_ffff_0000`、大小 64 KiB、`contentFileName` 指向 Tiny bootrom 镜像
   - SRAM/内存：地址 `0xffff_ff00_0000`、大小 8 MiB，作为可写主存（TL 从端口）；**不引入 cfx/PTW**
2. `usingVM = false`（无 MMU/TLB）；TL 协商出的 `addressBits` 必须 ≥ 48。
3. 复位向量 = `0xffff_ffff_0000`；核从 BootROM 起始取指。
4. 记录实现方式（改哪个 `AddressMap`/fragment、是否新增 fragment），并写入 `components/chipyard/README.md`。

## 验收标准

1. chipyard 生成的 `WumingTinyConfig` 中，`paddrBits`/`addressBits` **实测 ≥ 48**（打印协商值，禁止写死断言值以外的假设）
2. 生成的 `.dts`/`memmap` 中 BootROM 起始 = `0xffff_ffff_0000`、大小 64 KiB；SRAM 起始 = `0xffff_ff00_0000`、大小 8 MiB
3. Verilator 构建 rc=0（`server207`）；有界运行能从 `0xffff_ffff_0000` 取指（打印取指地址或等价证据）
4. 与 QEMU `dadao-tiny` 的同一最小镜像（放 BootROM）行为一致（退出码或等价可观测结果）
5. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
6. 一键证据脚本 `.work/evidence/m12-chipyard-002/run.sh`（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- BootROM 镜像内容与 `loadmem` 装载闭环（`m12-chipyard-003`）
- semihosting 应答者（`m12-chipyard-004`）
- 核内部指令实现（`005` 起）
- 修改 `spec/Machine-v5` 的地址图（**不授权**；以 spec 为准）

## 说明

- 若 chipyard 的 `AddressMap` 无法表达 `0xffff_ffff_0000`（如 TL 地址位宽或 mask 限制），**停下报告**并给出实测证据，不要自行改 spec 或缩小地址。
- 构建/运行在 `server207`（见 `.tao/knowledge/nodes.md`），仓库修改在主控机。
