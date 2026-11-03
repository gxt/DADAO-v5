# ADR-0047: TileLink 自包含 CPU 子系统

**状态**：Accepted
**日期**：2026-11-02
**接受日期**：2026-11-02
**关联**：`RTL-012t`、`ADR-0004`、`ADR-0020`、`ADR-0043`

## Context（背景）

RTL-011t 已完成单周期 Core、RAM/BootROM 地址语义和统一内存端口，
但 Chipyard Tile 仍把 Core 内存端口固定为“请求接受、响应无效”。
该状态只能用于 elaboration（硬件展开），不能运行完整程序。

当前目标是一个只包含处理器核、TileLink（片上互联协议）、BootROM 和 RAM
的独立 CPU 子系统，不包含 UART（通用异步收发器）、GPIO、Timer、DMA
或 Chipyard SystemBus（系统总线）。

## Decision（决策）

- **D1 拓扑**：采用单客户端、单交叉开关、双管理器的自包含拓扑：

  ```text
  DADAOCore
    -> DADAOMemPort（统一请求/响应端口）
    -> DADAOTLAdapter（TileLink 适配器）
    -> TLXbar（TileLink 交叉开关）
    -> TLROM（启动只读存储器管理器）
    -> TLRAM（随机访问存储器管理器）
  ```

- **D2 协议子集**：只使用 TileLink-UL（Uncached Lightweight，
  无缓存轻量级事务）的 `Get`、`PutFullData`、`PutPartialData`、
  `AccessAckData` 和 `AccessAck`。不实现缓存一致性、原子操作和
  多客户端仲裁。

- **D3 数据宽度**：TileLink `beatBytes = 8`，与 Core 64-bit 数据宽度
  一致。支持 1/2/4/8-byte 访问。

- **D4 地址**：

  ```text
  BootROM = 0xFFFF_FFFF_0000, 64 KiB, read-only
  RAM     = 0xFC00_0000_0000, 16 MiB, read-write
  Reset   = 0xFFFF_FFFF_0000
  ```

- **D5 适配器**：Core 到 Adapter 之间每次只允许一个
  outstanding request（未完成事务），固定 `source = 0`。Adapter
  必须保持请求直到 A 通道完成握手，并保持响应直到 Core 接收。

- **D6 窄访存**：Adapter 根据地址低 3 bit 将 `wdata` 和 `wstrb`
  对齐到 TileLink beat（单拍数据）的 byte lane（字节通道）。
  Core 接收的 `rdata` 保持右对齐。

- **D7 错误映射**：Core 地址检查先产生
  `UNMAPPED`/`MALIGN`/`ILLI`。TileLink `denied` 映射为
  `ILLI`；不新增未冻结的 fault code。

- **D8 存储器**：BootROM 使用 `TLROM`，RAM 使用 `TLRAM`。
  BootROM 和 RAM 均作为真实 TileLink manager（管理器）连接，
  不再使用 `DADAOTestMemory` 作为最终集成内存。

- **D9 范围外**：UART、GPIO、Timer、DMA、Cache、一致性、
  多 hart、多 outstanding transaction 和外部 DRAM 均不在本 ADR
  范围内。

## Consequences（影响）

- CPU 子系统不依赖 Chipyard SystemBus 即可完成程序级验证。
- `DADAOTile` 不再把 Core 内存端口固定为无效响应，而通过真实
  TileLink client（客户端）连接。
- BootROM 内容必须由参数或镜像文件提供；测试可使用小型向量镜像。
- RAM 逻辑容量为 16 MiB，必须使用推断存储器而不是大量独立寄存器。
- 后续接入完整 SoC 时，可将内部 TLXbar/RAM/ROM 替换为 Chipyard
  SystemBus，而无需改变 Core 的 `DADAOMemPort` 逻辑边界。

## Verification（验证）

1. Adapter A/D 通道握手、背压和单事务状态测试。
2. BootROM 取指/load 成功、store 失败测试。
3. RAM 1/2/4/8-byte 读写和 `wstrb` 测试。
4. CPU 从 BootROM 启动并在 RAM 写回结果。
5. Core fault 与 TileLink denied 映射测试。
6. 全量回归、negative gate、YAML hash、RTL tree 和 Chipyard
   elaboration 必须通过。
